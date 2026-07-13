"use client";

import { ResourceManager } from "@/components/ResourceManager";
import { Badge } from "@/components/ui/Badge";
import { Fabricante } from "@/lib/types";

const fields = [
  { name: "nome", label: "Nome", type: "text" as const, required: true },
  { name: "cnpj", label: "CNPJ", type: "text" as const },
  { name: "registro_anvisa", label: "Registro ANVISA", type: "text" as const },
  { name: "pais_origem", label: "País de origem", type: "text" as const, placeholder: "Brasil" },
  { name: "ativo", label: "Ativo", type: "checkbox" as const },
];

export default function FabricantesPage() {
  return (
    <ResourceManager<Fabricante>
      title="Fabricantes"
      description="Laboratórios e fornecedores dos produtos."
      endpoint="/fabricantes"
      allowDelete
      createFields={fields}
      editFields={fields}
      columns={[
        { key: "nome", label: "Nome" },
        { key: "pais_origem", label: "País" },
        { key: "registro_anvisa", label: "Registro ANVISA" },
        {
          key: "ativo",
          label: "Status",
          render: (f) => <Badge color={f.ativo ? "green" : "slate"}>{f.ativo ? "Ativo" : "Inativo"}</Badge>,
        },
      ]}
    />
  );
}
