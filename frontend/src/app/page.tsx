"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import { Estoque, Produto, LogAuditoria } from "@/lib/types";

interface Kpis {
  produtosAtivos: number;
  posicoesComSaldo: number;
  logsRecentes: LogAuditoria[];
}

export default function DashboardPage() {
  const [kpis, setKpis] = useState<Kpis | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        // Teto de paginação do backend (SEC-07) é 100 — ver
        // app/api/v1/pagination.py. KPIs aqui são uma contagem aproximada
        // sobre a primeira página, não uma contagem exata da tabela inteira.
        const [produtos, estoque, logs] = await Promise.all([
          api.get<Produto[]>("/produtos?limit=100"),
          api.get<Estoque[]>("/estoque?limit=100"),
          api.get<LogAuditoria[]>("/auditoria?limit=8"),
        ]);
        setKpis({
          produtosAtivos: produtos.filter((p) => p.ativo).length,
          posicoesComSaldo: estoque.filter((e) => e.quantidade_atual > 0).length,
          logsRecentes: logs,
        });
      } catch (err) {
        setErro(
          err instanceof ApiError
            ? err.detail
            : "Não foi possível conectar ao backend. Confirme que a API está rodando em " +
                (process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api/v1") +
                ".",
        );
      }
    }
    load();
  }, []);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-white">Dashboard</h1>
        <p className="text-sm text-slate-400">Visão geral da operação e das decisões dos agentes de IA.</p>
      </div>

      {erro && <div className="rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">{erro}</div>}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <KpiCard label="Produtos ativos" value={kpis?.produtosAtivos ?? "—"} />
        <KpiCard label="Posições de estoque com saldo" value={kpis?.posicoesComSaldo ?? "—"} />
        <KpiCard label="Últimas decisões auditadas" value={kpis?.logsRecentes.length ?? "—"} />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-white/10 bg-[#0b0d13] p-5 shadow-lg shadow-black/20">
          <h2 className="mb-3 text-sm font-semibold text-slate-200">Ações rápidas</h2>
          <div className="flex flex-col gap-2">
            <Link href="/agentes/analise-estoque" className="text-sm font-medium text-emerald-400 hover:text-emerald-300">
              Rodar Análise de Estoque (Gerente → Financeiro)
            </Link>
            <Link href="/atendimento" className="text-sm font-medium text-emerald-400 hover:text-emerald-300">
              Abrir o Atendimento (Avatar)
            </Link>
            <Link href="/auditoria" className="text-sm font-medium text-emerald-400 hover:text-emerald-300">
              Ver trilha de auditoria completa
            </Link>
          </div>
        </div>

        <div className="rounded-xl border border-white/10 bg-[#0b0d13] p-5 shadow-lg shadow-black/20">
          <h2 className="mb-3 text-sm font-semibold text-slate-200">Decisões recentes dos agentes</h2>
          {!kpis && <p className="text-sm text-slate-500">Carregando...</p>}
          {kpis && kpis.logsRecentes.length === 0 && (
            <p className="text-sm text-slate-500">Nenhuma decisão registrada ainda.</p>
          )}
          <ul className="flex flex-col gap-2">
            {kpis?.logsRecentes.map((log) => (
              <li key={log.id} className="border-b border-white/[0.06] pb-2 text-sm last:border-0">
                <p className="text-slate-300">{log.decisao_tomada}</p>
                <p className="text-xs text-slate-500">
                  {log.agente_nome} · {new Date(log.criado_em).toLocaleString("pt-BR")}
                </p>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

function KpiCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl border border-white/10 bg-[#0b0d13] p-5 shadow-lg shadow-black/20">
      <p className="text-sm text-slate-400">{label}</p>
      <p className="mt-1 text-3xl font-semibold text-white">{value}</p>
    </div>
  );
}
