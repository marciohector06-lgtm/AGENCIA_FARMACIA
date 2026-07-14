"use client";

import { ResourceManager } from "@/components/ResourceManager";
import { Badge } from "@/components/ui/Badge";
import { Filial } from "@/lib/types";

const fields = [
  { name: "nome", label: "Nome", type: "text" as const, required: true },
  { name: "cnpj", label: "CNPJ", type: "text" as const },
  { name: "endereco", label: "Endereço", type: "text" as const },
  { name: "cidade", label: "Cidade", type: "text" as const },
  { name: "uf", label: "UF", type: "text" as const },
  { name: "ativo", label: "Ativo", type: "checkbox" as const },
];

export default function FiliaisPage() {
  return (
    <ResourceManager<Filial>
      title="Filiais"
      description="Lojas físicas da rede."
      endpoint="/filiais"
      allowDelete
      createFields={fields}
      editFields={fields}
      isRowEditable={(f) => f.origem === "manual"}
      columns={[
        { key: "nome", label: "Nome" },
        { key: "cidade", label: "Cidade" },
        { key: "uf", label: "UF" },
        {
          key: "ativo",
          label: "Status",
          render: (f) => <Badge color={f.ativo ? "green" : "slate"}>{f.ativo ? "Ativa" : "Inativa"}</Badge>,
        },
        {
          key: "origem",
          label: "Origem",
          render: (f) => <Badge color={f.origem === "manual" ? "blue" : "slate"}>{f.origem}</Badge>,
        },
      ]}
    />
  );
}
