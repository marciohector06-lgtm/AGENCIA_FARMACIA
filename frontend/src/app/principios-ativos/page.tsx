"use client";

import { ResourceManager } from "@/components/ResourceManager";
import { PrincipioAtivo } from "@/lib/types";

const fields = [
  { name: "nome", label: "Nome", type: "text" as const, required: true },
  { name: "nome_dcb", label: "Nome DCB", type: "text" as const },
  { name: "classe_terapeutica", label: "Classe terapêutica", type: "text" as const, required: true },
  { name: "mecanismo_acao", label: "Mecanismo de ação", type: "textarea" as const },
  { name: "contraindicacoes_gerais", label: "Contraindicações gerais", type: "textarea" as const },
];

export default function PrincipiosAtivosPage() {
  return (
    <ResourceManager<PrincipioAtivo>
      title="Princípios Ativos"
      description="Base clínica usada pelo Agente Atendente para sugerir MIPs — nunca inventada, sempre consultada aqui."
      endpoint="/principios-ativos"
      createFields={fields}
      editFields={fields}
      columns={[
        { key: "nome", label: "Nome" },
        { key: "nome_dcb", label: "DCB" },
        { key: "classe_terapeutica", label: "Classe terapêutica" },
      ]}
    />
  );
}
