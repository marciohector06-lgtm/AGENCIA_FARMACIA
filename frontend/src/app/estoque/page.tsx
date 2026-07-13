"use client";

import { ResourceManager, FieldConfig } from "@/components/ResourceManager";
import { useOptions } from "@/lib/hooks";
import { Estoque } from "@/lib/types";

export default function EstoquePage() {
  const filiais = useOptions("/filiais", "nome");
  const lotes = useOptions("/lotes", "numero_lote");

  const createFields: FieldConfig[] = [
    { name: "filial_id", label: "Filial", type: "select", required: true, options: filiais },
    { name: "lote_id", label: "Lote", type: "select", required: true, options: lotes },
    { name: "quantidade_atual", label: "Quantidade atual", type: "integer", required: true },
    { name: "quantidade_reservada", label: "Quantidade reservada", type: "integer", required: true },
    { name: "localizacao_gondola", label: "Localização na gôndola", type: "text" },
  ];

  const editFields: FieldConfig[] = [
    { name: "quantidade_atual", label: "Quantidade atual", type: "integer", required: true },
    { name: "quantidade_reservada", label: "Quantidade reservada", type: "integer", required: true },
    { name: "localizacao_gondola", label: "Localização na gôndola", type: "text" },
  ];

  return (
    <ResourceManager<Estoque>
      title="Estoque"
      description="Posição de estoque por filial e lote."
      endpoint="/estoque"
      createFields={createFields}
      editFields={editFields}
      columns={[
        { key: "quantidade_atual", label: "Qtd. atual" },
        { key: "quantidade_reservada", label: "Qtd. reservada" },
        {
          key: "quantidade_disponivel",
          label: "Qtd. disponível",
          render: (e) => e.quantidade_atual - e.quantidade_reservada,
        },
        { key: "localizacao_gondola", label: "Gôndola" },
      ]}
    />
  );
}
