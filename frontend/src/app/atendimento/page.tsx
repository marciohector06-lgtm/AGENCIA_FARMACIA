"use client";

import { AtendimentoPanel } from "@/components/atendimento/AtendimentoPanel";

export default function AtendimentoPage() {
  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Atendimento (Avatar)</h1>
        <p className="text-sm text-slate-400">
          Converse com o Farmacêutico Clínico virtual — ele só sugere MIPs reais do catálogo, verifica estoque e
          busca substitutos quando necessário.
        </p>
      </div>
      <AtendimentoPanel />
    </div>
  );
}
