"use client";

import { SelectInput } from "@/components/ui/Field";
import { useOptions } from "@/lib/hooks";

interface FilialClienteSelectorProps {
  filialId: string;
  setFilialId: (id: string) => void;
  clienteId: string;
  setClienteId: (id: string) => void;
  filialDisabled: boolean;
}

// Só é montado no painel administrativo (/atendimento) — busca as listas de
// filiais e clientes nos endpoints administrativos /filiais e /clientes. O
// totem nunca renderiza este componente, então nunca chama essas rotas.
export function FilialClienteSelector({
  filialId,
  setFilialId,
  clienteId,
  setClienteId,
  filialDisabled,
}: FilialClienteSelectorProps) {
  const filiais = useOptions("/filiais", "nome");
  const clientes = useOptions("/clientes", "nome");

  return (
    <div className="flex gap-3">
      <div className="w-64">
        <SelectInput value={filialId} onChange={(e) => setFilialId(e.target.value)} disabled={filialDisabled}>
          <option value="">Selecione a filial...</option>
          {filiais.map((f) => (
            <option key={f.value} value={f.value}>
              {f.label}
            </option>
          ))}
        </SelectInput>
      </div>
      <div className="w-64">
        {/* QA-05: opcional — atendimento anônimo continua funcionando sem
            selecionar um cliente. */}
        <SelectInput value={clienteId} onChange={(e) => setClienteId(e.target.value)}>
          <option value="">Cliente não identificado</option>
          {clientes.map((c) => (
            <option key={c.value} value={c.value}>
              {c.label}
            </option>
          ))}
        </SelectInput>
      </div>
    </div>
  );
}
