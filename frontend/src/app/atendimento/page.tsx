"use client";

import { useState } from "react";
import { api, ApiError, ApiTimeoutError } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { FieldWrapper, SelectInput, TextInput } from "@/components/ui/Field";
import { useOptions } from "@/lib/hooks";
import { ChatAtendimentoResponse, ProdutoSugerido } from "@/lib/types";

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
  const [filialId, setFilialId] = useState("");
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

  async function confirmarCompra(produto: ProdutoSugerido) {
    if (!filialId || !sessaoId) return;
    setLoading(true);
    setErro(null);
    try {
      const resp = await api.post<ChatAtendimentoResponse>("/chat/atendimento", {
        sessao_id: sessaoId,
        filial_id: filialId,
        mensagem: `Confirmo a compra de ${produto.nome_comercial}.`,
        confirmar_compra: true,
        produto_id: produto.produto_id,
        quantidade: 1,
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
        <h1 className="text-2xl font-semibold text-slate-900">Atendimento (Avatar)</h1>
        <p className="text-sm text-slate-500">
          Converse com o Farmacêutico Clínico virtual — ele só sugere MIPs reais do catálogo, verifica estoque e
          busca substitutos quando necessário.
        </p>
      </div>

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

      <div className="rounded-lg border border-slate-200 bg-white">
        <button
          type="button"
          onClick={() => setPerfilAberto((v) => !v)}
          className="flex w-full items-center justify-between px-4 py-2 text-sm font-medium text-slate-700"
        >
          Perfil clínico (opcional — preencha o que souber)
          <span className="text-slate-400">{perfilAberto ? "▲" : "▼"}</span>
        </button>
        {perfilAberto && (
          <div className="grid grid-cols-2 gap-3 border-t border-slate-100 px-4 py-3 sm:grid-cols-4">
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
              <label className="flex items-center gap-1.5 text-sm text-slate-700">
                <input type="checkbox" checked={gestante} onChange={(e) => setGestante(e.target.checked)} />
                Gestante
              </label>
              <label className="flex items-center gap-1.5 text-sm text-slate-700">
                <input type="checkbox" checked={lactante} onChange={(e) => setLactante(e.target.checked)} />
                Lactante
              </label>
            </div>
          </div>
        )}
      </div>

      <div className="flex flex-1 flex-col overflow-y-auto rounded-lg border border-slate-200 bg-white p-5">
        {mensagens.length === 0 && (
          <div className="flex flex-1 items-center justify-center text-center text-sm text-slate-400">
            💊 Descreva um sintoma ou peça um produto para começar a conversa.
          </div>
        )}
        <div className="flex flex-col gap-4">
          {mensagens.map((msg) => (
            <ChatBubble key={msg.id} msg={msg} onConfirmar={confirmarCompra} disabled={loading} />
          ))}
          {loading && (
            <div className="max-w-md self-start rounded-lg bg-slate-100 px-4 py-2 text-sm text-slate-500">
              O Avatar está pensando...
            </div>
          )}
        </div>
      </div>

      {erro && <div className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">{erro}</div>}

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
          disabled={loading}
        />
        <Button type="submit" disabled={loading}>
          Enviar
        </Button>
      </form>
    </div>
  );
}

function ChatBubble({
  msg,
  onConfirmar,
  disabled,
}: {
  msg: ChatMessage;
  onConfirmar: (produto: ProdutoSugerido) => void;
  disabled: boolean;
}) {
  const isUser = msg.role === "user";
  return (
    <div className={`flex flex-col ${isUser ? "items-end" : "items-start"}`}>
      <div
        className={`max-w-lg rounded-lg px-4 py-2 text-sm ${
          isUser ? "bg-emerald-600 text-white" : "bg-slate-100 text-slate-800"
        }`}
      >
        {msg.text}
      </div>
      {/* CLIN-06: disclaimer sempre em destaque visual separado — nunca dentro
          do balão de resposta, pra não se misturar com o texto do "avatar". */}
      {!isUser && msg.disclaimer && (
        <div className="mt-1 max-w-lg rounded-md border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs text-amber-800">
          {msg.disclaimer}
        </div>
      )}
      {msg.vendaId && (
        <p className="mt-1 text-xs text-emerald-600">Venda registrada: {msg.vendaId}</p>
      )}
      {msg.produtos && msg.produtos.length > 0 && (
        <div className="mt-2 flex flex-col gap-2">
          {msg.produtos.map((p) => (
            <div
              key={p.produto_id}
              className="flex items-center justify-between gap-4 rounded-lg border border-slate-200 bg-white px-4 py-2"
            >
              <div>
                <p className="text-sm font-medium text-slate-800">{p.nome_comercial}</p>
                <p className="text-xs text-slate-500">
                  {p.disponivel ? "Disponível em estoque" : "Sem estoque"} · R$ {p.preco.toFixed(2)}
                </p>
                <p className="text-xs text-slate-400">{p.motivo_sugestao}</p>
              </div>
              <Button
                variant="secondary"
                disabled={disabled || !p.disponivel}
                onClick={() => onConfirmar(p)}
              >
                Confirmar compra
              </Button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
