"use client";

import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { FieldWrapper, SelectInput, TextInput } from "@/components/ui/Field";
import { useOptions } from "@/lib/hooks";
import { AnaliseEstoqueResponse } from "@/lib/types";

export default function AnaliseEstoquePage() {
  const filiais = useOptions("/filiais", "nome");
  const [filialId, setFilialId] = useState("");
  const [diasVencimento, setDiasVencimento] = useState("60");
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [resultado, setResultado] = useState<AnaliseEstoqueResponse | null>(null);

  async function rodarAnalise() {
    setLoading(true);
    setErro(null);
    setResultado(null);
    try {
      const data = await api.post<AnaliseEstoqueResponse>("/agentes/analise-estoque", {
        filial_id: filialId || null,
        dias_vencimento: Number(diasVencimento),
      });
      setResultado(data);
    } catch (err) {
      setErro(err instanceof ApiError ? err.detail : "Falha ao rodar a análise de estoque.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Análise de Estoque</h1>
        <p className="text-sm text-slate-400">
          Dispara o fluxo Agente Gerente de Estoque → Agente Financeiro: identifica produtos vencendo, propõe
          descontos com base em giro real de vendas, e exige aprovação financeira por margem antes de valer.
        </p>
      </div>

      <div className="flex flex-wrap items-end gap-4 rounded-xl border border-slate-200 bg-white p-5 shadow-lg">
        <div className="w-56">
          <FieldWrapper label="Filial (opcional)" htmlFor="filial">
            <SelectInput id="filial" value={filialId} onChange={(e) => setFilialId(e.target.value)}>
              <option value="">Todas as filiais</option>
              {filiais.map((f) => (
                <option key={f.value} value={f.value}>
                  {f.label}
                </option>
              ))}
            </SelectInput>
          </FieldWrapper>
        </div>
        <div className="w-40">
          <FieldWrapper label="Dias até vencer" htmlFor="dias">
            <TextInput
              id="dias"
              type="number"
              min={1}
              value={diasVencimento}
              onChange={(e) => setDiasVencimento(e.target.value)}
            />
          </FieldWrapper>
        </div>
        <Button onClick={rodarAnalise} disabled={loading}>
          {loading ? "Analisando..." : "Rodar Análise"}
        </Button>
      </div>

      {loading && (
        <div className="rounded-lg border border-blue-500/20 bg-blue-500/10 px-4 py-3 text-sm text-blue-700">
          Os agentes estão raciocinando com o LLM (busca de dados reais + Chain-of-Thought). Isso pode levar de 20s a
          1 minuto — não feche esta página.
        </div>
      )}

      {erro && <div className="rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-700">{erro}</div>}

      {resultado && (
        <div className="flex flex-col gap-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <Kpi label="Propostas geradas" value={resultado.propostas_geradas} />
            <Kpi label="Aprovadas" value={resultado.aprovadas} color="green" />
            <Kpi label="Rejeitadas" value={resultado.rejeitadas} color="red" />
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-lg">
            <h2 className="mb-2 text-sm font-semibold text-slate-700">Resumo do Orquestrador</h2>
            <p className="text-sm text-slate-400">{resultado.resumo}</p>
          </div>

          {resultado.decisoes.length > 0 && (
            <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-lg">
              <table className="min-w-full divide-y divide-slate-200 text-sm">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Decisão</th>
                    <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Margem resultante</th>
                    <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Justificativa (Financeiro)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {resultado.decisoes.map((d) => (
                    <tr key={d.precificacao_id}>
                      <td className="px-4 py-2.5">
                        <Badge color={d.aprovado ? "green" : "red"}>{d.aprovado ? "Aprovado" : "Rejeitado"}</Badge>
                      </td>
                      <td className="px-4 py-2.5 text-slate-600">
                        {d.margem_resultante !== null ? `${d.margem_resultante.toFixed(2)}%` : "—"}
                      </td>
                      <td className="px-4 py-2.5 text-slate-400">{d.justificativa}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <p className="text-xs text-slate-500">
            {resultado.log_auditoria_ids.length} registro(s) gravado(s) em logs_auditoria.{" "}
            <a href="/auditoria" className="text-red-600 hover:text-red-500">
              Ver na trilha de auditoria
            </a>
          </p>
        </div>
      )}
    </div>
  );
}

function Kpi({ label, value, color }: { label: string; value: number; color?: "green" | "red" }) {
  const valueColor = color === "green" ? "text-emerald-600" : color === "red" ? "text-red-600" : "text-slate-900";
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-lg">
      <p className="text-sm text-slate-400">{label}</p>
      <p className={`mt-1 text-3xl font-semibold ${valueColor}`}>{value}</p>
    </div>
  );
}
