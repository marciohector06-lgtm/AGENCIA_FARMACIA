"use client";

import { useState } from "react";
import { ResourceManager, FieldConfig } from "@/components/ResourceManager";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { FieldWrapper, SelectInput, TextArea, TextInput } from "@/components/ui/Field";
import { api, ApiError } from "@/lib/api";
import { useOptions } from "@/lib/hooks";
import { Estoque } from "@/lib/types";

export default function EstoquePage() {
  const filiais = useOptions("/filiais", "nome");
  const lotes = useOptions("/lotes", "numero_lote");

  const createFields: FieldConfig[] = [
    { name: "filial_id", label: "Filial", type: "select", required: true, options: filiais },
    { name: "lote_id", label: "Lote", type: "select", required: true, options: lotes },
    { name: "quantidade_atual", label: "Quantidade atual (entrada inicial)", type: "integer", required: true },
    { name: "quantidade_reservada", label: "Quantidade reservada", type: "integer", required: true },
    { name: "localizacao_gondola", label: "Localização na gôndola", type: "text" },
  ];

  // SEC-11: quantidade_atual/quantidade_reservada saíram daqui de propósito —
  // depois de criada, a posição de estoque só muda via "Movimentar" (POST
  // /estoque/{id}/movimentar, motivo obrigatório).
  const editFields: FieldConfig[] = [{ name: "localizacao_gondola", label: "Localização na gôndola", type: "text" }];

  return (
    <ResourceManager<Estoque>
      title="Estoque"
      description="Posição de estoque por filial e lote. Quantidade muda só por movimentação registrada."
      endpoint="/estoque"
      createFields={createFields}
      editFields={editFields}
      isRowEditable={(e) => e.origem === "manual"}
      renderRowExtra={(e, reload) => <MovimentarAction estoque={e} onChanged={reload} />}
      columns={[
        { key: "quantidade_atual", label: "Qtd. atual" },
        { key: "quantidade_reservada", label: "Qtd. reservada" },
        {
          key: "quantidade_disponivel",
          label: "Qtd. disponível",
          render: (e) => e.quantidade_atual - e.quantidade_reservada,
        },
        { key: "localizacao_gondola", label: "Gôndola" },
        {
          key: "origem",
          label: "Origem",
          render: (e) => <Badge color={e.origem === "manual" ? "blue" : "slate"}>{e.origem}</Badge>,
        },
      ]}
    />
  );
}

function MovimentarAction({ estoque, onChanged }: { estoque: Estoque; onChanged: () => Promise<void> }) {
  const [open, setOpen] = useState(false);
  const [tipo, setTipo] = useState<"entrada" | "ajuste">("entrada");
  const [delta, setDelta] = useState("");
  const [motivo, setMotivo] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const editavel = estoque.origem === "manual";

  async function salvar(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setErro(null);
    try {
      await api.post(`/estoque/${estoque.id}/movimentar`, { tipo, quantidade_delta: Number(delta), motivo });
      setOpen(false);
      setDelta("");
      setMotivo("");
      await onChanged();
    } catch (err) {
      setErro(err instanceof ApiError ? err.detail : "Falha ao registrar movimentação");
    } finally {
      setSubmitting(false);
    }
  }

  if (!editavel) return null;

  return (
    <>
      <button onClick={() => setOpen(true)} className="text-sm font-medium text-red-600 hover:text-red-500">
        Movimentar
      </button>
      {open && (
        <Modal
          title={`Movimentar estoque — ${estoque.quantidade_atual} unid. atuais`}
          onClose={() => setOpen(false)}
          footer={
            <>
              <Button variant="secondary" onClick={() => setOpen(false)}>
                Cancelar
              </Button>
              <Button form="movimentar-form" type="submit" disabled={submitting}>
                {submitting ? "Salvando..." : "Salvar"}
              </Button>
            </>
          }
        >
          <form id="movimentar-form" onSubmit={salvar} className="flex flex-col gap-4">
            {erro && <div className="rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2 text-sm text-red-700">{erro}</div>}
            <FieldWrapper label="Tipo" htmlFor="tipo-mov" required>
              <SelectInput id="tipo-mov" value={tipo} onChange={(e) => setTipo(e.target.value as "entrada" | "ajuste")}>
                <option value="entrada">Entrada</option>
                <option value="ajuste">Ajuste</option>
              </SelectInput>
            </FieldWrapper>
            <FieldWrapper label="Quantidade (negativo para saída)" htmlFor="delta-mov" required>
              <TextInput id="delta-mov" type="number" required value={delta} onChange={(e) => setDelta(e.target.value)} />
            </FieldWrapper>
            <FieldWrapper label="Motivo" htmlFor="motivo-mov" required>
              <TextArea id="motivo-mov" rows={3} required minLength={10} value={motivo} onChange={(e) => setMotivo(e.target.value)} />
            </FieldWrapper>
          </form>
        </Modal>
      )}
    </>
  );
}
