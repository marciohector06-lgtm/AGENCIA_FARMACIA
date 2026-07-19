"use client";

import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import {
  ConfirmarEntradaResponse,
  NotaFiscalEntrada,
  NotaFiscalEntradaDetalhe,
  ProcessarNFeEmailResponse,
  StatusNfeEntrada,
} from "@/lib/types";

const STATUS_BADGE: Record<StatusNfeEntrada, { label: string; color: "yellow" | "green" | "red" }> = {
  aguardando_confirmacao: { label: "🟡 Aguardando confirmação", color: "yellow" },
  confirmada: { label: "✅ Confirmada", color: "green" },
  cancelada: { label: "❌ Cancelada", color: "red" },
};

function formatarMoeda(valor: number): string {
  return valor.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function formatarData(iso: string): string {
  return new Date(iso).toLocaleString("pt-BR");
}

export default function NotasEntradaPage() {
  const [notas, setNotas] = useState<NotaFiscalEntrada[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  const [processando, setProcessando] = useState(false);
  const [resultadoProcessamento, setResultadoProcessamento] = useState<ProcessarNFeEmailResponse | null>(null);

  const [notaSelecionada, setNotaSelecionada] = useState<NotaFiscalEntradaDetalhe | null>(null);
  const [carregandoDetalhe, setCarregandoDetalhe] = useState(false);
  const [confirmando, setConfirmando] = useState(false);
  const [erroModal, setErroModal] = useState<string | null>(null);

  async function carregarNotas() {
    setCarregando(true);
    setErro(null);
    try {
      const data = await api.get<NotaFiscalEntrada[]>("/notas-entrada");
      setNotas(data);
    } catch (err) {
      setErro(err instanceof ApiError ? err.detail : "Falha ao carregar as notas de entrada.");
    } finally {
      setCarregando(false);
    }
  }

  useEffect(() => {
    let active = true;
    async function load() {
      setCarregando(true);
      setErro(null);
      try {
        const data = await api.get<NotaFiscalEntrada[]>("/notas-entrada");
        if (active) setNotas(data);
      } catch (err) {
        if (active) setErro(err instanceof ApiError ? err.detail : "Falha ao carregar as notas de entrada.");
      } finally {
        if (active) setCarregando(false);
      }
    }
    load();
    return () => {
      active = false;
    };
  }, []);

  async function processarEmailsAgora() {
    setProcessando(true);
    setErro(null);
    setResultadoProcessamento(null);
    try {
      const data = await api.post<ProcessarNFeEmailResponse>("/agentes/processar-nfe-email", {});
      setResultadoProcessamento(data);
      await carregarNotas();
    } catch (err) {
      setErro(err instanceof ApiError ? err.detail : "Falha ao processar os emails de NF-e.");
    } finally {
      setProcessando(false);
    }
  }

  async function abrirDetalhe(notaId: string) {
    setCarregandoDetalhe(true);
    setErroModal(null);
    setNotaSelecionada(null);
    try {
      const data = await api.get<NotaFiscalEntradaDetalhe>(`/notas-entrada/${notaId}`);
      setNotaSelecionada(data);
    } catch (err) {
      setErro(err instanceof ApiError ? err.detail : "Falha ao carregar os detalhes da nota.");
    } finally {
      setCarregandoDetalhe(false);
    }
  }

  async function confirmarChegada() {
    if (!notaSelecionada) return;
    setConfirmando(true);
    setErroModal(null);
    try {
      await api.post<ConfirmarEntradaResponse>(`/notas-entrada/${notaSelecionada.id}/confirmar`, {});
      setNotaSelecionada(null);
      await carregarNotas();
    } catch (err) {
      setErroModal(err instanceof ApiError ? err.detail : "Falha ao confirmar a entrada.");
    } finally {
      setConfirmando(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Notas de Entrada</h1>
          <p className="text-sm text-slate-400">
            NF-e recebidas por email pelo Agente Tributário. Confirmar a chegada aplica a entrada em estoque — antes
            disso, nada muda em lotes ou estoque.
          </p>
        </div>
        <Button onClick={processarEmailsAgora} disabled={processando}>
          {processando ? "Processando..." : "Processar emails agora"}
        </Button>
      </div>

      {processando && (
        <div className="rounded-lg border border-blue-500/20 bg-blue-500/10 px-4 py-3 text-sm text-blue-700">
          O Agente Tributário está lendo a caixa de entrada e processando os XMLs (LLM real). Isso pode levar até um
          minuto — não feche esta página.
        </div>
      )}

      {resultadoProcessamento && (
        <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-700">
          {resultadoProcessamento.notas_processadas} nota(s) processada(s). {resultadoProcessamento.resumo}
        </div>
      )}

      {erro && <div className="rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-700">{erro}</div>}

      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-lg">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Número</th>
              <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Emitente</th>
              <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Data</th>
              <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Valor total</th>
              <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Status</th>
              <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-slate-500"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {carregando && (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-slate-400">
                  Carregando...
                </td>
              </tr>
            )}
            {!carregando && notas.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-slate-400">
                  Nenhuma nota de entrada ainda. Clique em &quot;Processar emails agora&quot; para buscar novas NF-e.
                </td>
              </tr>
            )}
            {notas.map((nota) => (
              <tr key={nota.id}>
                <td className="px-4 py-2.5 text-slate-700">
                  {nota.numero_nota}/{nota.serie}
                </td>
                <td className="px-4 py-2.5 text-slate-700">{nota.nome_emitente}</td>
                <td className="px-4 py-2.5 text-slate-400">{formatarData(nota.data_emissao)}</td>
                <td className="px-4 py-2.5 text-slate-700">{formatarMoeda(nota.valor_total)}</td>
                <td className="px-4 py-2.5">
                  <Badge color={STATUS_BADGE[nota.status].color}>{STATUS_BADGE[nota.status].label}</Badge>
                </td>
                <td className="px-4 py-2.5 text-right">
                  <Button variant="secondary" onClick={() => abrirDetalhe(nota.id)} disabled={carregandoDetalhe}>
                    Ver produtos
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {notaSelecionada && (
        <Modal
          title={`Nota ${notaSelecionada.numero_nota}/${notaSelecionada.serie} — ${notaSelecionada.nome_emitente}`}
          onClose={() => setNotaSelecionada(null)}
          footer={
            notaSelecionada.status === "aguardando_confirmacao" ? (
              <>
                <Button variant="secondary" onClick={() => setNotaSelecionada(null)}>
                  Fechar
                </Button>
                <Button onClick={confirmarChegada} disabled={confirmando}>
                  {confirmando ? "Confirmando..." : "✓ Confirmar chegada"}
                </Button>
              </>
            ) : (
              <Button variant="secondary" onClick={() => setNotaSelecionada(null)}>
                Fechar
              </Button>
            )
          }
        >
          <div className="flex flex-col gap-4">
            {erroModal && (
              <div className="rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2 text-sm text-red-700">
                {erroModal}
              </div>
            )}
            <div className="flex flex-wrap gap-4 text-sm text-slate-600">
              <span>Chave: {notaSelecionada.chave_acesso}</span>
              <span>CNPJ emitente: {notaSelecionada.cnpj_emitente}</span>
              <Badge color={STATUS_BADGE[notaSelecionada.status].color}>
                {STATUS_BADGE[notaSelecionada.status].label}
              </Badge>
            </div>
            <div className="overflow-x-auto rounded-lg border border-slate-200">
              <table className="min-w-full divide-y divide-slate-200 text-xs">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-3 py-2 text-left font-semibold uppercase tracking-wide text-slate-500">Produto</th>
                    <th className="px-3 py-2 text-left font-semibold uppercase tracking-wide text-slate-500">NCM</th>
                    <th className="px-3 py-2 text-left font-semibold uppercase tracking-wide text-slate-500">Qtd.</th>
                    <th className="px-3 py-2 text-left font-semibold uppercase tracking-wide text-slate-500">Custo unit.</th>
                    <th className="px-3 py-2 text-left font-semibold uppercase tracking-wide text-slate-500">Lote</th>
                    <th className="px-3 py-2 text-left font-semibold uppercase tracking-wide text-slate-500">Validade</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {notaSelecionada.itens.map((item) => (
                    <tr key={item.id}>
                      <td className="px-3 py-2 text-slate-700">
                        {item.produto_id ? (
                          item.descricao_produto
                        ) : (
                          <span className="flex flex-col gap-1">
                            <span>{item.descricao_produto}</span>
                            <Badge color="yellow">⚠️ Produto não encontrado no cadastro</Badge>
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-2 text-slate-400">{item.ncm}</td>
                      <td className="px-3 py-2 text-slate-600">{item.quantidade}</td>
                      <td className="px-3 py-2 text-slate-600">{formatarMoeda(item.custo_unitario)}</td>
                      <td className="px-3 py-2 text-slate-400">{item.numero_lote ?? "—"}</td>
                      <td className="px-3 py-2 text-slate-400">
                        {item.data_validade ? new Date(item.data_validade).toLocaleDateString("pt-BR") : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-xs text-slate-500">
              Itens sem produto identificado não bloqueiam a confirmação, mas não entram em estoque automaticamente —
              cadastre o produto e reprocesse manualmente se necessário.
            </p>
          </div>
        </Modal>
      )}
    </div>
  );
}
