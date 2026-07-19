"use client";

import { useEffect, useState } from "react";
import { api, ApiError, ApiTimeoutError, postComRetryEmTimeout } from "@/lib/api";
import { useReconhecimentoVoz, useSintese } from "@/lib/useVoz";
import { ChatAtendimentoResponse, Cliente, ProdutoSugerido } from "@/lib/types";

export const AVISO_IA_TEXTO =
  "Este atendimento é realizado por inteligência artificial. Seus dados de saúde serão usados " +
  "exclusivamente para sugerir medicamentos isentos de prescrição e serão tratados conforme nossa " +
  "Política de Privacidade.";

export interface ChatMessage {
  id: string;
  role: "user" | "avatar" | "sistema";
  text: string;
  produtos?: ProdutoSugerido[];
  vendaId?: string | null;
  // CLIN-06: renderizado separado do texto da resposta, nunca misturado.
  disclaimer?: string;
}

interface UseAtendimentoChatOptions {
  // Totem: filial fixa do tablet (via config de deploy), sem seletor na
  // tela — ver AtendimentoPanel/FilialClienteSelector.
  filialIdFixa?: string;
  // Totem: dispara logo após uma venda ser confirmada, pra a tela poder
  // resetar pro próximo cliente depois de um tempo de leitura.
  onVendaConfirmada?: () => void;
}

// Lógica de atendimento compartilhada entre /atendimento (admin) e /totem
// (cliente): consentimento LGPD, envio de mensagem, confirmação de compra e
// integração com voz. A diferença de invólucro (com/sem seletores de
// filial/cliente, layout) fica inteiramente no componente que usa este hook.
export function useAtendimentoChat({ filialIdFixa, onVendaConfirmada }: UseAtendimentoChatOptions = {}) {
  const [filialId, setFilialId] = useState(filialIdFixa ?? "");
  // QA-05: identificação do cliente é opcional — atendimento anônimo
  // continua funcionando sem selecionar nada aqui.
  const [clienteId, setClienteId] = useState("");
  // LGPD-03: null = anônimo (nenhum consentimento a checar) ou ainda
  // carregando; false = precisa mostrar o aviso antes de liberar o chat.
  const [consentimentoDado, setConsentimentoDado] = useState<boolean | null>(null);
  const [enviandoConsentimento, setEnviandoConsentimento] = useState(false);
  const [sessaoId, setSessaoId] = useState<string | null>(null);
  const [mensagens, setMensagens] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  // CLIN-04: perfil clínico opcional — nunca obrigatório pra conversar.
  const [perfilAberto, setPerfilAberto] = useState(false);
  const [medicamentosEmUso, setMedicamentosEmUso] = useState("");
  const [gestante, setGestante] = useState(false);
  const [lactante, setLactante] = useState(false);
  const [idade, setIdade] = useState("");

  // Voz (Nível 2) — entrada por fala e saída por voz, só frontend (ver
  // src/lib/useVoz.ts). Desligado por padrão no envio automático: no totem
  // o cliente pode estar conversando com alguém do lado com o mic aberto,
  // nunca dispara sem confirmação explícita dele.
  const [autoEnvio, setAutoEnvio] = useState(false);
  const {
    suportado: micSuportado,
    gravando,
    iniciar: iniciarGravacao,
    parar: pararGravacao,
  } = useReconhecimentoVoz({
    onTextoAtualizado: (texto) => setInput(texto),
    onSilencio: (texto) => {
      if (autoEnvio && texto.trim()) {
        pararGravacao();
        enviarMensagem(texto);
      }
    },
  });
  const { falando, bocaAberta, falar, pararFala } = useSintese({ rate: 0.9 });

  function pushMessage(msg: ChatMessage) {
    setMensagens((prev) => [...prev, msg]);
  }

  function alternarGravacao() {
    // Requisito: se o agente estiver falando quando o cliente clica no mic,
    // para a fala IMEDIATAMENTE antes de gravar — senão o microfone capta a
    // própria voz do agente e cria um loop.
    if (falando) pararFala();
    if (gravando) {
      pararGravacao();
    } else {
      iniciarGravacao();
    }
  }

  // LGPD-03: toda vez que um cliente é selecionado, checa se ele já
  // consentiu. Atendimento anônimo (clienteId vazio) nunca passa por aqui —
  // é o caso do totem, que nunca seta clienteId.
  useEffect(() => {
    let active = true;
    queueMicrotask(() => {
      if (!active) return;
      setConsentimentoDado(null);
      if (!clienteId) return;
      api
        .get<Cliente>(`/clientes/${clienteId}`)
        .then((cliente) => {
          if (active) setConsentimentoDado(cliente.consentimento_dado);
        })
        .catch(() => {
          if (active) setConsentimentoDado(null);
        });
    });
    return () => {
      active = false;
    };
  }, [clienteId]);

  async function aceitarConsentimento() {
    setEnviandoConsentimento(true);
    try {
      await api.post(`/clientes/${clienteId}/consentimento`, {});
      setConsentimentoDado(true);
    } catch {
      setErro("Não foi possível registrar o consentimento agora. Tente novamente.");
    } finally {
      setEnviandoConsentimento(false);
    }
  }

  const precisaConsentimento = clienteId !== "" && consentimentoDado === false;

  function perfilClinicoPayload() {
    return {
      medicamentos_em_uso: medicamentosEmUso
        .split(",")
        .map((m) => m.trim())
        .filter(Boolean),
      gestante,
      lactante,
      idade: idade ? Number(idade) : null,
    };
  }

  async function enviarMensagem(textoFalado?: string) {
    if (!filialId) {
      setErro("Selecione a filial de atendimento antes de conversar com o Avatar.");
      return;
    }
    const texto = (textoFalado ?? input).trim();
    if (!texto) return;

    setInput("");
    setErro(null);
    pushMessage({ id: crypto.randomUUID(), role: "user", text: texto });
    setLoading(true);

    try {
      // Retry único em timeout do cliente (ver postComRetryEmTimeout em
      // api.ts) — o crew pode legitimamente levar perto do limite do
      // timeout, uma segunda tentativa antes de mostrar erro evita um falso
      // negativo por uma resposta só um pouco mais lenta que o normal.
      const resp = await postComRetryEmTimeout<ChatAtendimentoResponse>("/chat/atendimento", {
        sessao_id: sessaoId,
        filial_id: filialId,
        cliente_id: clienteId || undefined,
        mensagem: texto,
        confirmar_compra: false,
        ...perfilClinicoPayload(),
      });
      setSessaoId(resp.sessao_id);
      pushMessage({
        id: crypto.randomUUID(),
        role: "avatar",
        text: resp.resposta,
        produtos: resp.produtos_sugeridos,
        disclaimer: resp.disclaimer,
      });
      falar([resp.disclaimer, resp.resposta]);
    } catch (err) {
      if (err instanceof ApiTimeoutError) {
        setErro(err.message);
      } else {
        setErro(err instanceof ApiError ? err.detail : "O Avatar não conseguiu responder agora.");
      }
    } finally {
      setLoading(false);
    }
  }

  async function confirmarCompra(produto: ProdutoSugerido, quantidade: number) {
    if (!filialId || !sessaoId) return;
    setLoading(true);
    setErro(null);
    try {
      // Retry seguro aqui mesmo mutando uma venda: o backend protege por
      // idempotency_key (sessão + produto + lote + quantidade — ver
      // _idempotency_key_venda em service.py), uma segunda tentativa idêntica
      // nunca duplica a compra.
      const resp = await postComRetryEmTimeout<ChatAtendimentoResponse>("/chat/atendimento", {
        sessao_id: sessaoId,
        filial_id: filialId,
        cliente_id: clienteId || undefined,
        mensagem: `Confirmo a compra de ${quantidade}x ${produto.nome_comercial}.`,
        confirmar_compra: true,
        produto_id: produto.produto_id,
        quantidade,
      });
      pushMessage({
        id: crypto.randomUUID(),
        role: "avatar",
        text: resp.resposta,
        vendaId: resp.venda_id,
        disclaimer: resp.disclaimer,
      });
      falar([resp.disclaimer, resp.resposta]);
      onVendaConfirmada?.();
    } catch (err) {
      if (err instanceof ApiTimeoutError) {
        setErro(err.message);
      } else {
        setErro(err instanceof ApiError ? err.detail : "Não foi possível confirmar a compra.");
      }
    } finally {
      setLoading(false);
    }
  }

  return {
    filialId,
    setFilialId,
    clienteId,
    setClienteId,
    precisaConsentimento,
    enviandoConsentimento,
    aceitarConsentimento,
    mensagens,
    input,
    setInput,
    loading,
    erro,
    perfilAberto,
    setPerfilAberto,
    medicamentosEmUso,
    setMedicamentosEmUso,
    gestante,
    setGestante,
    lactante,
    setLactante,
    idade,
    setIdade,
    autoEnvio,
    setAutoEnvio,
    micSuportado,
    gravando,
    falando,
    bocaAberta,
    alternarGravacao,
    pararFala,
    enviarMensagem,
    confirmarCompra,
  };
}
