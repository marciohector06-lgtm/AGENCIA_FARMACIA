"use client";

import { useState } from "react";
import { ResourceManager, FieldConfig } from "@/components/ResourceManager";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { FieldWrapper, SelectInput, TextArea } from "@/components/ui/Field";
import { api, ApiError } from "@/lib/api";
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

  const baseFields: FieldConfig[] = [
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
    { name: "tipo_liberacao", label: "Tipo de liberação", type: "text", placeholder: "imediata" },
    { name: "preco_tabela", label: "Preço de tabela (R$)", type: "decimal", required: true },
    { name: "custo_medio", label: "Custo médio (R$)", type: "decimal" },
    { name: "ativo", label: "Ativo", type: "checkbox" },
  ];

  // Tarja só entra na criação. Depois de cadastrado, mudar tarja é sempre via
  // o endpoint privilegiado PATCH /produtos/{id}/tarja (ver TarjaModal abaixo)
  // — nunca pelo PATCH genérico (SEC-06).
  const createFields: FieldConfig[] = [
    ...baseFields.slice(0, 10),
    { name: "tarja", label: "Tarja", type: "select", required: true, options: TARJA_OPTIONS },
    ...baseFields.slice(10),
  ];

  return (
    <ResourceManager<Produto>
      title="Produtos"
      description="Catálogo de medicamentos e produtos vendidos pela farmácia."
      endpoint="/produtos"
      createFields={createFields}
      editFields={baseFields}
      isRowEditable={(p) => p.origem === "manual"}
      renderRowExtra={(p, reload) => <TarjaAction produto={p} onChanged={reload} />}
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
        {
          key: "origem",
          label: "Origem",
          render: (p) => <Badge color={p.origem === "manual" ? "blue" : "slate"}>{p.origem}</Badge>,
        },
      ]}
    />
  );
}

function TarjaAction({ produto, onChanged }: { produto: Produto; onChanged: () => Promise<void> }) {
  const [open, setOpen] = useState(false);
  const [tarja, setTarja] = useState(produto.tarja);
  const [motivo, setMotivo] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function salvar(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setErro(null);
    try {
      await api.patch(`/produtos/${produto.id}/tarja`, { tarja, motivo });
      setOpen(false);
      setMotivo("");
      await onChanged();
    } catch (err) {
      setErro(err instanceof ApiError ? err.detail : "Falha ao alterar tarja");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <button onClick={() => setOpen(true)} className="text-sm font-medium text-amber-600 hover:text-amber-700">
        Tarja
      </button>
      {open && (
        <Modal
          title={`Alterar tarja — ${produto.nome_comercial}`}
          onClose={() => setOpen(false)}
          footer={
            <>
              <Button variant="secondary" onClick={() => setOpen(false)}>
                Cancelar
              </Button>
              <Button form="tarja-form" type="submit" disabled={submitting}>
                {submitting ? "Salvando..." : "Salvar"}
              </Button>
            </>
          }
        >
          <form id="tarja-form" onSubmit={salvar} className="flex flex-col gap-4">
            <p className="text-xs text-slate-500">
              Endpoint privilegiado e auditado — decide se o agente atendente pode enxergar este produto.
            </p>
            {erro && <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{erro}</div>}
            <FieldWrapper label="Nova tarja" htmlFor="nova-tarja" required>
              <SelectInput id="nova-tarja" value={tarja} onChange={(e) => setTarja(e.target.value as Produto["tarja"])}>
                {TARJA_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </SelectInput>
            </FieldWrapper>
            <FieldWrapper label="Motivo" htmlFor="motivo-tarja" required>
              <TextArea id="motivo-tarja" rows={3} required minLength={10} value={motivo} onChange={(e) => setMotivo(e.target.value)} />
            </FieldWrapper>
          </form>
        </Modal>
      )}
    </>
  );
}
