"use client";

import { useCallback, useState } from "react";
import { AtendimentoPanel } from "@/components/atendimento/AtendimentoPanel";
import { useIdleReset } from "@/lib/useIdleReset";

// Cada totem físico atende uma filial fixa, configurada no deploy daquele
// tablet — nunca escolhida na tela (evita expor a lista de filiais/clientes
// numa interface pública, ver FilialClienteSelector).
const FILIAL_ID = process.env.NEXT_PUBLIC_TOTEM_FILIAL_ID ?? "";

const TIMEOUT_INATIVIDADE_MS = 60_000;
// Tempo pro cliente ler a confirmação de venda antes da tela resetar sozinha.
const DELAY_APOS_VENDA_MS = 6_000;

export default function TotemPage() {
  // Trocar a key força o React a desmontar e remontar o AtendimentoPanel
  // inteiro — garante que nenhum estado do cliente anterior (mensagens,
  // input, sessão) sobrevive pro próximo, sem precisar resetar campo a campo.
  const [sessaoKey, setSessaoKey] = useState(0);
  const resetar = useCallback(() => setSessaoKey((k) => k + 1), []);

  useIdleReset(TIMEOUT_INATIVIDADE_MS, resetar, [sessaoKey]);

  function onVendaConfirmada() {
    setTimeout(resetar, DELAY_APOS_VENDA_MS);
  }

  // Falha visível no deploy, não silenciosa no atendimento: sem isto, o
  // totem renderiza normal e só quebra quando um cliente de verdade tenta
  // conversar — com um erro genérico de admin ("Selecione a filial...") que
  // não faz sentido numa tela sem seletor nenhum. Melhor travar aqui, com
  // uma mensagem que aponta o problema real pra quem for configurar o
  // tablet.
  if (!FILIAL_ID) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-2 bg-white p-6 text-center">
        <h1 className="text-xl font-semibold text-red-600">Totem não configurado</h1>
        <p className="max-w-md text-sm text-slate-500">
          A variável de ambiente NEXT_PUBLIC_TOTEM_FILIAL_ID não foi definida para este tablet. Configure-a com o
          ID da filial e reinicie o app antes de liberar o atendimento.
        </p>
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col gap-4 bg-white p-6">
      <div className="text-center">
        <h1 className="text-3xl font-semibold tracking-tight text-slate-900">Atendimento Farmacêutico</h1>
        <p className="text-base text-slate-500">Toque no microfone ou digite sua dúvida para começar.</p>
      </div>
      <AtendimentoPanel
        key={sessaoKey}
        modoTotem
        filialIdFixa={FILIAL_ID}
        onVendaConfirmada={onVendaConfirmada}
      />
    </div>
  );
}
