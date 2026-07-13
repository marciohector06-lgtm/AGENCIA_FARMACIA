"use client";

import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { Badge } from "@/components/ui/Badge";
import { SelectInput } from "@/components/ui/Field";
import { LogAuditoria, TipoDecisao } from "@/lib/types";

const TIPO_DECISAO_OPTIONS: { value: TipoDecisao; label: string }[] = [
  { value: "sugestao_similar", label: "Sugestão de similar" },
  { value: "ajuste_preco", label: "Ajuste de preço" },
  { value: "alerta_estoque", label: "Alerta de estoque" },
  { value: "aprovacao_compra", label: "Aprovação de compra" },
  { value: "bloqueio_venda", label: "Bloqueio de venda" },
  { value: "recomendacao_giro", label: "Recomendação de giro" },
  { value: "resolucao_conflito", label: "Resolução de conflito" },
];

const tipoColor: Record<string, "green" | "red" | "yellow" | "blue" | "slate"> = {
  sugestao_similar: "blue",
  ajuste_preco: "yellow",
  alerta_estoque: "yellow",
  aprovacao_compra: "green",
  bloqueio_venda: "red",
  recomendacao_giro: "slate",
  resolucao_conflito: "blue",
};

export default function AuditoriaPage() {
  const [logs, setLogs] = useState<LogAuditoria[]>([]);
  const [tipoFiltro, setTipoFiltro] = useState("");
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [expandido, setExpandido] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setErro(null);
      try {
        const query = tipoFiltro ? `?tipo_decisao=${tipoFiltro}&limit=100` : "?limit=100";
        const data = await api.get<LogAuditoria[]>(`/auditoria${query}`);
        setLogs(data);
      } catch (err) {
        setErro(err instanceof ApiError ? err.detail : "Falha ao carregar auditoria.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [tipoFiltro]);

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Auditoria</h1>
        <p className="text-sm text-slate-500">
          Toda decisão autônoma dos agentes — o quê, por quê, com quais dados, e quando.
        </p>
      </div>

      <div className="w-64">
        <SelectInput value={tipoFiltro} onChange={(e) => setTipoFiltro(e.target.value)}>
          <option value="">Todos os tipos de decisão</option>
          {TIPO_DECISAO_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </SelectInput>
      </div>

      {erro && <div className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">{erro}</div>}

      <div className="flex flex-col gap-2">
        {loading && <p className="text-sm text-slate-400">Carregando...</p>}
        {!loading && logs.length === 0 && <p className="text-sm text-slate-400">Nenhum registro encontrado.</p>}
        {logs.map((log) => (
          <div key={log.id} className="rounded-lg border border-slate-200 bg-white p-4">
            <div className="flex flex-wrap items-center gap-2">
              <Badge color={tipoColor[log.tipo_decisao] ?? "slate"}>{log.tipo_decisao}</Badge>
              <span className="text-sm font-medium text-slate-700">{log.agente_nome}</span>
              <span className="text-xs text-slate-400">({log.agente_tipo})</span>
              <span className="ml-auto text-xs text-slate-400">
                {new Date(log.criado_em).toLocaleString("pt-BR")}
              </span>
            </div>
            <p className="mt-2 text-sm text-slate-700">{log.decisao_tomada}</p>
            {log.justificativa && <p className="mt-1 text-sm text-slate-500">Justificativa: {log.justificativa}</p>}
            <button
              onClick={() => setExpandido(expandido === log.id ? null : log.id)}
              className="mt-2 text-xs font-medium text-emerald-600 hover:underline"
            >
              {expandido === log.id ? "Ocultar dados base" : "Ver dados base (JSON)"}
            </button>
            {expandido === log.id && (
              <pre className="mt-2 overflow-x-auto rounded-md bg-slate-50 p-3 text-xs text-slate-600">
                {JSON.stringify(log.dados_base, null, 2)}
              </pre>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
