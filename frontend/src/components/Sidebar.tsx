"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_GROUPS = [
  {
    title: "Visão geral",
    items: [{ href: "/", label: "Dashboard" }],
  },
  {
    title: "Catálogo",
    items: [
      { href: "/produtos", label: "Produtos" },
      { href: "/principios-ativos", label: "Princípios Ativos" },
      { href: "/fabricantes", label: "Fabricantes" },
    ],
  },
  {
    title: "Operação",
    items: [
      { href: "/estoque", label: "Estoque" },
      { href: "/lotes", label: "Lotes" },
      { href: "/filiais", label: "Filiais" },
      { href: "/clientes", label: "Clientes" },
    ],
  },
  {
    title: "Agentes de IA",
    items: [
      { href: "/agentes/analise-estoque", label: "Análise de Estoque" },
      { href: "/auditoria", label: "Auditoria" },
      { href: "/atendimento", label: "Atendimento (Avatar)" },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-screen w-64 shrink-0 flex-col border-r border-slate-200 bg-slate-900 text-slate-200">
      <div className="flex items-center gap-2 px-5 py-5">
        <div>
          <p className="text-sm font-semibold text-white">Farmácia MAS</p>
          <p className="text-xs text-slate-400">Painel de gestão</p>
        </div>
      </div>
      <nav className="flex-1 overflow-y-auto px-3 pb-6">
        {NAV_GROUPS.map((group) => (
          <div key={group.title} className="mb-5">
            <p className="mb-1 px-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              {group.title}
            </p>
            <ul className="flex flex-col gap-0.5">
              {group.items.map((item) => {
                const active = pathname === item.href;
                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      className={`block rounded-md px-2 py-1.5 text-sm transition-colors ${
                        active
                          ? "bg-emerald-600 text-white"
                          : "text-slate-300 hover:bg-slate-800 hover:text-white"
                      }`}
                    >
                      {item.label}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>
    </aside>
  );
}
