"use client";

import { useEffect, useState } from "react";
import { api, ApiError, ApiTimeoutError } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { FieldWrapper, SelectInput, TextInput } from "@/components/ui/Field";
import { Modal } from "@/components/ui/Modal";
import { useOptions } from "@/lib/hooks";
import { ChatAtendimentoResponse, Cliente, ProdutoSugerido } from "@/lib/types";

const AVISO_IA_TEXTO =
  "Este atendimento é realizado por inteligência artificial. Seus dados de saúde serão usados " +
  "exclusivamente para sugerir medicamentos isentos de prescrição e serão tratados conforme nossa " +
  "Política de Privacidade.";

interface ChatMessage {
  id: string;
  role: "user" | "avatar" | "sistema";
  text: string;
  produtos?: ProdutoSugerido[];
  vendaId?: string | null;
  // CLIN-06: renderizado separado do texto da resposta, nunca misturado.
  disclaimer?: string;
}

export default function AtendimentoPage() {
  const filiais = useOptions("/filiais", "nome");
  const clientes = useOptions("/clientes", "nome");
  const [filialId, setFilialId] = useState("");
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

  function pushMessage(msg: ChatMessage) {
    setMensagens((prev) => [...prev, msg]);
  }

  // LGPD-03: toda vez que um cliente é selecionado, checa se ele já
  // consentiu. Atendimento anônimo (clienteId vazio) nunca passa por aqui.
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

  async function enviarMensagem() {
    if (!filialId) {
      setErro("Selecione a filial de atendimento antes de conversar com o Avatar.");
      return;
    }
    if (!input.trim()) return;

    const texto = input.trim();
    setInput("");
    setErro(null);
    pushMessage({ id: crypto.randomUUID(), role: "user", text: texto });
    setLoading(true);

    try {
      const resp = await api.post<ChatAtendimentoResponse>("/chat/atendimento", {
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
      const resp = await api.post<ChatAtendimentoResponse>("/chat/atendimento", {
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

  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-white">Atendimento (Avatar)</h1>
        <p className="text-sm text-slate-400">
          Converse com o Farmacêutico Clínico virtual — ele só sugere MIPs reais do catálogo, verifica estoque e
          busca substitutos quando necessário.
        </p>
      </div>

      <div className="flex gap-3">
        <div className="w-64">
          <SelectInput
            value={filialId}
            onChange={(e) => setFilialId(e.target.value)}
            disabled={mensagens.length > 0}
          >
            <option value="">Selecione a filial...</option>
            {filiais.map((f) => (
              <option key={f.value} value={f.value}>
                {f.label}
              </option>
            ))}
          </SelectInput>
        </div>
        <div className="w-64">
          {/* QA-05: opcional — atendimento anônimo continua funcionando sem
              selecionar um cliente. */}
          <SelectInput value={clienteId} onChange={(e) => setClienteId(e.target.value)}>
            <option value="">Cliente não identificado</option>
            {clientes.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </SelectInput>
        </div>
      </div>

      <div className="rounded-xl border border-white/10 bg-[#0b0d13] shadow-lg shadow-black/20">
        <button
          type="button"
          onClick={() => setPerfilAberto((v) => !v)}
          className="flex w-full items-center justify-between px-4 py-2 text-sm font-medium text-slate-200"
        >
          Perfil clínico (opcional — preencha o que souber)
          <span className="text-slate-500">{perfilAberto ? "▲" : "▼"}</span>
        </button>
        {perfilAberto && (
          <div className="grid grid-cols-2 gap-3 border-t border-white/[0.06] px-4 py-3 sm:grid-cols-4">
            <div className="col-span-2 sm:col-span-2">
              <FieldWrapper label="Medicamentos em uso (separados por vírgula)" htmlFor="medicamentos-em-uso">
                <TextInput
                  id="medicamentos-em-uso"
                  placeholder="ex.: varfarina, losartana"
                  value={medicamentosEmUso}
                  onChange={(e) => setMedicamentosEmUso(e.target.value)}
                />
              </FieldWrapper>
            </div>
            <FieldWrapper label="Idade" htmlFor="idade-cliente">
              <TextInput
                id="idade-cliente"
                type="number"
                min={0}
                max={130}
                value={idade}
                onChange={(e) => setIdade(e.target.value)}
              />
            </FieldWrapper>
            <div className="flex items-end gap-4 pb-2">
              <label className="flex items-center gap-1.5 text-sm text-slate-300">
                <input type="checkbox" checked={gestante} onChange={(e) => setGestante(e.target.checked)} />
                Gestante
              </label>
              <label className="flex items-center gap-1.5 text-sm text-slate-300">
                <input type="checkbox" checked={lactante} onChange={(e) => setLactante(e.target.checked)} />
                Lactante
              </label>
            </div>
          </div>
        )}
      </div>

      <div className="flex flex-1 flex-col overflow-y-auto rounded-xl border border-white/10 bg-[#0b0d13] p-5 shadow-lg shadow-black/20">
        {mensagens.length === 0 && (
          <div className="flex flex-1 items-center justify-center text-center text-sm text-slate-500">
            Descreva um sintoma ou peça um produto para começar a conversa.
          </div>
        )}
        <div className="flex flex-col gap-4">
          {mensagens.map((msg) => (
            <ChatBubble key={msg.id} msg={msg} onConfirmar={confirmarCompra} disabled={loading || precisaConsentimento} />
          ))}
          {loading && (
            <div className="max-w-md self-start rounded-lg bg-white/[0.05] px-4 py-2 text-sm text-slate-400">
              O Avatar está pensando...
            </div>
          )}
        </div>
      </div>

      {erro && <div className="rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">{erro}</div>}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          enviarMensagem();
        }}
        className="flex gap-2"
      >
        <TextInput
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ex: estou com dor de cabeça e febre, o que vocês têm?"
          disabled={loading || precisaConsentimento}
        />
        <Button type="submit" disabled={loading || precisaConsentimento}>
          Enviar
        </Button>
      </form>

      {/* LGPD-03: primeira interação com um cliente identificado que ainda
          não consentiu — bloqueia o chat até aceitar (a garantia real é o
          403 do backend; isto é só a UX). */}
      {precisaConsentimento && (
        <Modal
          title="Antes de continuar"
          onClose={() => setClienteId("")}
          footer={
            <Button onClick={aceitarConsentimento} disabled={enviandoConsentimento}>
              {enviandoConsentimento ? "Registrando..." : "Estou de acordo"}
            </Button>
          }
        >
          <p className="text-sm text-slate-300">{AVISO_IA_TEXTO}</p>
        </Modal>
      )}
    </div>
  );
}

function ChatBubble({
  msg,
  onConfirmar,
  disabled,
}: {
  msg: ChatMessage;
  onConfirmar: (produto: ProdutoSugerido, quantidade: number) => void;
  disabled: boolean;
}) {
  const isUser = msg.role === "user";
  return (
    <div className={`flex flex-col ${isUser ? "items-end" : "items-start"}`}>
      <div
        className={`max-w-lg rounded-lg px-4 py-2 text-sm ${
          isUser ? "bg-emerald-500 text-slate-950" : "bg-white/[0.06] text-slate-200"
        }`}
      >
        {msg.text}
      </div>
      {/* CLIN-06: disclaimer sempre em destaque visual separado — nunca dentro
          do balão de resposta, pra não se misturar com o texto do "avatar". */}
      {!isUser && msg.disclaimer && (
        <div className="mt-1 max-w-lg rounded-md border border-amber-500/20 bg-amber-500/10 px-3 py-1.5 text-xs text-amber-300">
          {msg.disclaimer}
        </div>
      )}
      {msg.vendaId && (
        <p className="mt-1 text-xs text-emerald-400">Venda registrada: {msg.vendaId}</p>
      )}
      {msg.produtos && msg.produtos.length > 0 && (
        <div className="mt-2 flex flex-col gap-2">
          {msg.produtos.map((p) => (
            <ProdutoSugeridoCard key={p.produto_id} produto={p} disabled={disabled} onConfirmar={onConfirmar} />
          ))}
        </div>
      )}
    </div>
  );
}

// QA-05: quantidade era fixa em 1 no payload de confirmação — agora é
// editável por produto sugerido, validada no frontend (inteiro 1-999) antes
// de habilitar o botão de confirmar.
const QUANTIDADE_MIN = 1;
const QUANTIDADE_MAX = 999;

function ProdutoSugeridoCard({
  produto,
  disabled,
  onConfirmar,
}: {
  produto: ProdutoSugerido;
  disabled: boolean;
  onConfirmar: (produto: ProdutoSugerido, quantidade: number) => void;
}) {
  const [quantidadeInput, setQuantidadeInput] = useState("1");
  const quantidade = Number(quantidadeInput);
  const quantidadeValida =
    Number.isInteger(quantidade) && quantidade >= QUANTIDADE_MIN && quantidade <= QUANTIDADE_MAX;

  return (
    <div className="flex items-center justify-between gap-4 rounded-lg border border-white/10 bg-white/[0.03] px-4 py-2">
      <div>
        <p className="text-sm font-medium text-slate-200">{produto.nome_comercial}</p>
        <p className="text-xs text-slate-500">
          {produto.disponivel ? "Disponível em estoque" : "Sem estoque"} · R$ {produto.preco.toFixed(2)}
        </p>
        <p className="text-xs text-slate-600">{produto.motivo_sugestao}</p>
      </div>
      <div className="flex items-center gap-2">
        <TextInput
          type="number"
          min={QUANTIDADE_MIN}
          max={QUANTIDADE_MAX}
          step={1}
          value={quantidadeInput}
          onChange={(e) => setQuantidadeInput(e.target.value)}
          disabled={disabled || !produto.disponivel}
          className="w-20"
          aria-label={`Quantidade de ${produto.nome_comercial}`}
        />
        <Button
          variant="secondary"
          disabled={disabled || !produto.disponivel || !quantidadeValida}
          onClick={() => onConfirmar(produto, quantidade)}
        >
          Confirmar compra
        </Button>
      </div>
    </div>
  );
}
