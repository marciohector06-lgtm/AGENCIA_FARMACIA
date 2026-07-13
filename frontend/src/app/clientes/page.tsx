"use client";

import { ResourceManager } from "@/components/ResourceManager";
import { Cliente } from "@/lib/types";

const fields = [
  { name: "nome", label: "Nome", type: "text" as const, required: true },
  { name: "cpf", label: "CPF", type: "text" as const },
  { name: "data_nascimento", label: "Data de nascimento", type: "date" as const },
  { name: "telefone", label: "Telefone", type: "text" as const },
  { name: "email", label: "E-mail", type: "text" as const },
];

export default function ClientesPage() {
  return (
    <ResourceManager<Cliente>
      title="Clientes"
      description="Cadastro de clientes atendidos pela farmácia."
      endpoint="/clientes"
      allowDelete
      createFields={fields}
      editFields={fields}
      columns={[
        { key: "nome", label: "Nome" },
        { key: "cpf", label: "CPF" },
        { key: "telefone", label: "Telefone" },
        { key: "email", label: "E-mail" },
      ]}
    />
  );
}
