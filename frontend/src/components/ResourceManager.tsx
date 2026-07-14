"use client";

import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { FieldWrapper, SelectInput, TextArea, TextInput } from "@/components/ui/Field";

export interface FieldOption {
  value: string;
  label: string;
}

export interface FieldConfig {
  name: string;
  label: string;
  type: "text" | "number" | "decimal" | "integer" | "date" | "select" | "checkbox" | "textarea";
  required?: boolean;
  options?: FieldOption[];
  placeholder?: string;
  step?: string;
}

export interface ColumnConfig<T> {
  key: string;
  label: string;
  render?: (item: T) => React.ReactNode;
}

interface ResourceManagerProps<T extends { id: string }> {
  title: string;
  description?: string;
  endpoint: string;
  columns: ColumnConfig<T>[];
  createFields: FieldConfig[];
  editFields?: FieldConfig[];
  allowDelete?: boolean;
  allowCreate?: boolean;
  // FASE 0: registros de origem != 'manual' são gerenciados por um ERP e o
  // backend rejeita PATCH/DELETE neles (409) — escondemos as ações em vez de
  // deixar o usuário tomar um erro.
  isRowEditable?: (item: T) => boolean;
  renderRowExtra?: (item: T, reload: () => Promise<void>) => React.ReactNode;
}

type FormValues = Record<string, string | boolean>;

function buildInitialValues(fields: FieldConfig[]): FormValues {
  const values: FormValues = {};
  for (const field of fields) {
    values[field.name] = field.type === "checkbox" ? true : "";
  }
  return values;
}

function coerceValue(field: FieldConfig, raw: string | boolean): unknown {
  if (field.type === "checkbox") return Boolean(raw);
  if (field.type === "number" || field.type === "integer") return Number(raw);
  return raw;
}

// Campos de texto/select vazios são OMITIDOS do payload (não enviados como
// null): o backend tem campos com default != None (ex.: pais_origem="Brasil",
// tipo_liberacao="imediata") que rejeitam null explícito com 422. Omitir a
// chave deixa o Pydantic aplicar o default do próprio campo.
function serialize(fields: FieldConfig[], values: FormValues): Record<string, unknown> {
  const payload: Record<string, unknown> = {};
  for (const field of fields) {
    const raw = values[field.name];
    if (field.type !== "checkbox" && raw === "") continue;
    payload[field.name] = coerceValue(field, raw);
  }
  return payload;
}

function FieldInput({
  field,
  value,
  onChange,
}: {
  field: FieldConfig;
  value: string | boolean;
  onChange: (value: string | boolean) => void;
}) {
  if (field.type === "select") {
    return (
      <SelectInput
        id={field.name}
        required={field.required}
        value={value as string}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">Selecione...</option>
        {field.options?.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </SelectInput>
    );
  }
  if (field.type === "textarea") {
    return (
      <TextArea
        id={field.name}
        required={field.required}
        rows={3}
        value={value as string}
        onChange={(e) => onChange(e.target.value)}
      />
    );
  }
  if (field.type === "checkbox") {
    return (
      <input
        id={field.name}
        type="checkbox"
        checked={value as boolean}
        onChange={(e) => onChange(e.target.checked)}
        className="h-4 w-4 rounded border-white/20 bg-white/[0.03] text-emerald-500 focus:ring-emerald-500/40"
      />
    );
  }
  const inputType = field.type === "number" || field.type === "integer" || field.type === "decimal"
    ? "number"
    : field.type === "date"
      ? "date"
      : "text";
  return (
    <TextInput
      id={field.name}
      type={inputType}
      step={field.type === "decimal" ? (field.step ?? "0.01") : field.type === "integer" ? "1" : undefined}
      required={field.required}
      placeholder={field.placeholder}
      value={value as string}
      onChange={(e) => onChange(e.target.value)}
    />
  );
}

export function ResourceManager<T extends { id: string }>({
  title,
  description,
  endpoint,
  columns,
  createFields,
  editFields,
  allowDelete = false,
  allowCreate = true,
  isRowEditable = () => true,
  renderRowExtra,
}: ResourceManagerProps<T>) {
  const [items, setItems] = useState<T[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const [showCreate, setShowCreate] = useState(false);
  const [createValues, setCreateValues] = useState<FormValues>(() => buildInitialValues(createFields));

  const [editItem, setEditItem] = useState<T | null>(null);
  const [editValues, setEditValues] = useState<FormValues>({});

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<T[]>(endpoint);
      setItems(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Falha ao carregar dados");
    } finally {
      setLoading(false);
    }
  }, [endpoint]);

  useEffect(() => {
    queueMicrotask(load);
  }, [load]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setFormError(null);
    try {
      await api.post(endpoint, serialize(createFields, createValues));
      setShowCreate(false);
      setCreateValues(buildInitialValues(createFields));
      await load();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.detail : "Falha ao criar registro");
    } finally {
      setSubmitting(false);
    }
  }

  function openEdit(item: T) {
    if (!editFields) return;
    const values: FormValues = {};
    for (const field of editFields) {
      const current = (item as unknown as Record<string, unknown>)[field.name];
      values[field.name] = field.type === "checkbox" ? Boolean(current) : current == null ? "" : String(current);
    }
    setEditValues(values);
    setEditItem(item);
    setFormError(null);
  }

  async function handleEdit(e: React.FormEvent) {
    e.preventDefault();
    if (!editItem || !editFields) return;
    setSubmitting(true);
    setFormError(null);
    try {
      await api.patch(`${endpoint}/${editItem.id}`, serialize(editFields, editValues));
      setEditItem(null);
      await load();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.detail : "Falha ao atualizar registro");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(item: T) {
    if (!confirm(`Remover "${(item as unknown as Record<string, unknown>)[columns[0].key]}"?`)) return;
    try {
      await api.delete(`${endpoint}/${item.id}`);
      await load();
    } catch (err) {
      alert(err instanceof ApiError ? err.detail : "Falha ao remover registro");
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-white">{title}</h1>
          {description && <p className="text-sm text-slate-400">{description}</p>}
        </div>
        {allowCreate && (
          <Button onClick={() => setShowCreate(true)}>
            + Novo
          </Button>
        )}
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</div>
      )}

      <div className="overflow-x-auto rounded-xl border border-white/10 bg-[#0b0d13] shadow-lg shadow-black/20">
        <table className="min-w-full divide-y divide-white/[0.06] text-sm">
          <thead className="bg-white/[0.02]">
            <tr>
              {columns.map((col) => (
                <th key={col.key} className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                  {col.label}
                </th>
              ))}
              {(editFields || allowDelete || renderRowExtra) && <th className="px-4 py-2.5" />}
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04]">
            {loading && (
              <tr>
                <td colSpan={columns.length + 1} className="px-4 py-6 text-center text-slate-500">
                  Carregando...
                </td>
              </tr>
            )}
            {!loading && items.length === 0 && (
              <tr>
                <td colSpan={columns.length + 1} className="px-4 py-6 text-center text-slate-500">
                  Nenhum registro encontrado.
                </td>
              </tr>
            )}
            {!loading &&
              items.map((item) => (
                <tr key={item.id} className="transition-colors hover:bg-white/[0.03]">
                  {columns.map((col) => (
                    <td key={col.key} className="px-4 py-2.5 text-slate-300">
                      {col.render ? col.render(item) : String((item as unknown as Record<string, unknown>)[col.key] ?? "—")}
                    </td>
                  ))}
                  {(editFields || allowDelete || renderRowExtra) && (
                    <td className="px-4 py-2.5 text-right whitespace-nowrap">
                      {renderRowExtra?.(item, load)}
                      {editFields && isRowEditable(item) && (
                        <button
                          onClick={() => openEdit(item)}
                          className="ml-3 text-sm font-medium text-emerald-400 hover:text-emerald-300"
                        >
                          Editar
                        </button>
                      )}
                      {allowDelete && isRowEditable(item) && (
                        <button
                          onClick={() => handleDelete(item)}
                          className="ml-3 text-sm font-medium text-red-400 hover:text-red-300"
                        >
                          Excluir
                        </button>
                      )}
                    </td>
                  )}
                </tr>
              ))}
          </tbody>
        </table>
      </div>

      {showCreate && (
        <Modal
          title={`Novo em ${title}`}
          onClose={() => setShowCreate(false)}
          footer={
            <>
              <Button variant="secondary" onClick={() => setShowCreate(false)}>
                Cancelar
              </Button>
              <Button form="create-form" type="submit" disabled={submitting}>
                {submitting ? "Salvando..." : "Salvar"}
              </Button>
            </>
          }
        >
          <form id="create-form" onSubmit={handleCreate} className="flex flex-col gap-4">
            {formError && <div className="rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2 text-sm text-red-300">{formError}</div>}
            {createFields.map((field) => (
              <FieldWrapper key={field.name} label={field.label} htmlFor={field.name} required={field.required}>
                <FieldInput
                  field={field}
                  value={createValues[field.name]}
                  onChange={(v) => setCreateValues((prev) => ({ ...prev, [field.name]: v }))}
                />
              </FieldWrapper>
            ))}
          </form>
        </Modal>
      )}

      {editItem && editFields && (
        <Modal
          title={`Editar em ${title}`}
          onClose={() => setEditItem(null)}
          footer={
            <>
              <Button variant="secondary" onClick={() => setEditItem(null)}>
                Cancelar
              </Button>
              <Button form="edit-form" type="submit" disabled={submitting}>
                {submitting ? "Salvando..." : "Salvar"}
              </Button>
            </>
          }
        >
          <form id="edit-form" onSubmit={handleEdit} className="flex flex-col gap-4">
            {formError && <div className="rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2 text-sm text-red-300">{formError}</div>}
            {editFields.map((field) => (
              <FieldWrapper key={field.name} label={field.label} htmlFor={field.name} required={field.required}>
                <FieldInput
                  field={field}
                  value={editValues[field.name]}
                  onChange={(v) => setEditValues((prev) => ({ ...prev, [field.name]: v }))}
                />
              </FieldWrapper>
            ))}
          </form>
        </Modal>
      )}
    </div>
  );
}
