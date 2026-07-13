"use client";

import { ResourceManager, FieldConfig } from "@/components/ResourceManager";
import { Badge } from "@/components/ui/Badge";
import { useOptions } from "@/lib/hooks";
import { Produto } from "@/lib/types";

const FORMA_FARMACEUTICA_OPTIONS = [
  "comprimido",
  "capsula",
  "xarope",
  "pomada",
  "gel",
  "creme",
  "solucao",
  "suspensao",
  "injetavel",
  "spray",
  "adesivo",
  "po",
  "supositorio",
  "colirio",
].map((v) => ({ value: v, label: v }));

const VIA_ADMINISTRACAO_OPTIONS = [
  "oral",
  "topica",
  "injetavel",
  "retal",
  "oftalmica",
  "nasal",
  "inalatoria",
  "sublingual",
  "otologica",
  "vaginal",
].map((v) => ({ value: v, label: v }));

const UNIDADE_CONCENTRACAO_OPTIONS = ["mg", "g", "ml", "mcg", "ui", "pct"].map((v) => ({ value: v, label: v }));

const TARJA_OPTIONS = [
  { value: "isento", label: "Isento (MIP)" },
  { value: "amarela", label: "Amarela" },
  { value: "vermelha", label: "Vermelha" },
  { value: "preta", label: "Preta" },
];

const tarjaColor: Record<string, "green" | "yellow" | "red" | "slate"> = {
  isento: "green",
  amarela: "yellow",
  vermelha: "red",
  preta: "red",
};

export default function ProdutosPage() {
  const principiosAtivos = useOptions("/principios-ativos", "nome");
  const fabricantes = useOptions("/fabricantes", "nome");

  const fields: FieldConfig[] = [
    { name: "nome_comercial", label: "Nome comercial", type: "text", required: true },
    { name: "fabricante_id", label: "Fabricante", type: "select", required: true, options: fabricantes },
    { name: "principio_ativo_id", label: "Princípio ativo", type: "select", options: principiosAtivos },
    { name: "codigo_barras", label: "Código de barras (EAN)", type: "text" },
    { name: "registro_anvisa", label: "Registro ANVISA", type: "text" },
    { name: "forma_farmaceutica", label: "Forma farmacêutica", type: "select", required: true, options: FORMA_FARMACEUTICA_OPTIONS },
    { name: "via_administracao", label: "Via de administração", type: "select", required: true, options: VIA_ADMINISTRACAO_OPTIONS },
    { name: "concentracao_valor", label: "Concentração", type: "decimal", required: true, step: "0.001" },
    { name: "concentracao_unidade", label: "Unidade", type: "select", required: true, options: UNIDADE_CONCENTRACAO_OPTIONS },
    { name: "quantidade_embalagem", label: "Unidades por embalagem", type: "integer", required: true },
    { name: "tarja", label: "Tarja", type: "select", required: true, options: TARJA_OPTIONS },
    { name: "tipo_liberacao", label: "Tipo de liberação", type: "text", placeholder: "imediata" },
    { name: "preco_tabela", label: "Preço de tabela (R$)", type: "decimal", required: true },
    { name: "custo_medio", label: "Custo médio (R$)", type: "decimal" },
    { name: "ativo", label: "Ativo", type: "checkbox" },
  ];

  return (
    <ResourceManager<Produto>
      title="Produtos"
      description="Catálogo de medicamentos e produtos vendidos pela farmácia."
      endpoint="/produtos"
      createFields={fields}
      editFields={fields}
      columns={[
        { key: "nome_comercial", label: "Nome comercial" },
        { key: "forma_farmaceutica", label: "Forma" },
        {
          key: "concentracao_valor",
          label: "Concentração",
          render: (p) => `${p.concentracao_valor} ${p.concentracao_unidade}`,
        },
        {
          key: "tarja",
          label: "Tarja",
          render: (p) => <Badge color={tarjaColor[p.tarja]}>{p.tarja}</Badge>,
        },
        { key: "preco_tabela", label: "Preço (R$)", render: (p) => `R$ ${p.preco_tabela}` },
        {
          key: "ativo",
          label: "Status",
          render: (p) => <Badge color={p.ativo ? "green" : "slate"}>{p.ativo ? "Ativo" : "Inativo"}</Badge>,
        },
      ]}
    />
  );
}
