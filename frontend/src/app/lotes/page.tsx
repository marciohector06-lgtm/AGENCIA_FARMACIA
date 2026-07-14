"use client";

import { ResourceManager, FieldConfig } from "@/components/ResourceManager";
import { Badge } from "@/components/ui/Badge";
import { useOptions } from "@/lib/hooks";
import { Lote } from "@/lib/types";

const STATUS_OPTIONS = ["disponivel", "reservado", "vencido", "bloqueado", "devolvido"].map((v) => ({
  value: v,
  label: v,
}));

const statusColor: Record<string, "green" | "yellow" | "red" | "slate" | "blue"> = {
  disponivel: "green",
  reservado: "blue",
  vencido: "red",
  bloqueado: "red",
  devolvido: "slate",
};

export default function LotesPage() {
  const produtos = useOptions("/produtos", "nome_comercial");

  const createFields: FieldConfig[] = [
    { name: "produto_id", label: "Produto", type: "select", required: true, options: produtos },
    { name: "numero_lote", label: "Número do lote", type: "text", required: true },
    { name: "data_fabricacao", label: "Data de fabricação", type: "date", required: true },
    { name: "data_validade", label: "Data de validade", type: "date", required: true },
    { name: "quantidade_recebida", label: "Quantidade recebida", type: "integer", required: true },
    { name: "custo_unitario", label: "Custo unitário (R$)", type: "decimal", required: true },
  ];

  const editFields: FieldConfig[] = [
    { name: "status", label: "Status", type: "select", required: true, options: STATUS_OPTIONS },
  ];

  return (
    <ResourceManager<Lote>
      title="Lotes"
      description="Lotes recebidos por produto, com validade e status. Apenas o status pode ser alterado após o recebimento."
      endpoint="/lotes"
      createFields={createFields}
      editFields={editFields}
      isRowEditable={(l) => l.origem === "manual"}
      columns={[
        { key: "numero_lote", label: "Nº do lote" },
        { key: "data_validade", label: "Validade" },
        { key: "quantidade_recebida", label: "Qtd. recebida" },
        {
          key: "status",
          label: "Status",
          render: (l) => <Badge color={statusColor[l.status] ?? "slate"}>{l.status}</Badge>,
        },
        {
          key: "origem",
          label: "Origem",
          render: (l) => <Badge color={l.origem === "manual" ? "blue" : "slate"}>{l.origem}</Badge>,
        },
      ]}
    />
  );
}
