"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { TextInput } from "@/components/ui/Field";
import { ProdutoSugerido } from "@/lib/types";

// QA-05: quantidade era fixa em 1 no payload de confirmação — agora é
// editável por produto sugerido, validada no frontend (inteiro 1-999) antes
// de habilitar o botão de confirmar.
const QUANTIDADE_MIN = 1;
const QUANTIDADE_MAX = 999;

export function ProdutoSugeridoCard({
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
    <div className="flex items-center justify-between gap-4 rounded-lg border border-slate-200 bg-slate-50 px-4 py-2">
      <div>
        <p className="text-sm font-medium text-slate-700">{produto.nome_comercial}</p>
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
