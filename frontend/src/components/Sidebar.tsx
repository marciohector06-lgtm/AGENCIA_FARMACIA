"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { SVGProps } from "react";
import { clearToken } from "@/lib/api";

type IconKey =
  | "dashboard"
  | "produtos"
  | "principios"
  | "fabricantes"
  | "estoque"
  | "lotes"
  | "filiais"
  | "clientes"
  | "agente"
  | "auditoria"
  | "atendimento"
  | "notasEntrada";

const ICON_PATHS: Record<IconKey, string> = {
  dashboard: "M4 5h6v6H4V5Zm10 0h6v10h-6V5ZM4 15h6v4H4v-4Z",
  produtos: "M4 8.5 12 4l8 4.5v7L12 20l-8-4.5v-7Zm0 0 8 4.5m0 0 8-4.5M12 13v7",
  principios: "M10 3h4M9 3v5.2L4.8 16a2 2 0 0 0 1.8 3h10.8a2 2 0 0 0 1.8-3L15 8.2V3",
  fabricantes: "M4 21V9l5-3v3l5-3v3l5 3v9H4Zm4-4h2m4 0h2M8 13h2m4 0h2",
  estoque: "M4 7h16M4 7v11a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1V7M4 7l2-3h12l2 3M9 12h6",
  lotes: "M4 6h16v4H4V6Zm1 4h14v9a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1v-9Zm4 4h6",
  filiais: "M12 21s7-6.1 7-11a7 7 0 1 0-14 0c0 4.9 7 11 7 11Zm0-8a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z",
  clientes: "M9 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6Zm7 1a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5ZM3 20a6 6 0 0 1 12 0M15 14a5 5 0 0 1 6 6h-6",
  agente: "M12 3v3m0 12v3m9-9h-3M6 12H3m14.5-6.5-2 2m-9 9-2 2m0-13 2 2m9 9 2 2M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z",
  auditoria: "M12 3 4 6v6c0 4.5 3.4 7.7 8 9 4.6-1.3 8-4.5 8-9V6l-8-3Zm-2.5 9 1.8 1.8L14.8 10",
  atendimento: "M4 5h16v10H8l-4 4V5Z",
  notasEntrada: "M7 3h8l4 4v14H7V3Zm8 0v4h4M9 12h6M9 16h6M9 8h2",
};

function Icon({ name, ...props }: { name: IconKey } & SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.6}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...props}
    >
      <path d={ICON_PATHS[name]} />
    </svg>
  );
}

const NAV_GROUPS = [
  {
    title: "Visão geral",
    items: [{ href: "/", label: "Dashboard", icon: "dashboard" as IconKey }],
  },
  {
    title: "Catálogo",
    items: [
      { href: "/produtos", label: "Produtos", icon: "produtos" as IconKey },
      { href: "/principios-ativos", label: "Princípios Ativos", icon: "principios" as IconKey },
      { href: "/fabricantes", label: "Fabricantes", icon: "fabricantes" as IconKey },
    ],
  },
  {
    title: "Operação",
    items: [
      { href: "/estoque", label: "Estoque", icon: "estoque" as IconKey },
      { href: "/lotes", label: "Lotes", icon: "lotes" as IconKey },
      { href: "/filiais", label: "Filiais", icon: "filiais" as IconKey },
      { href: "/clientes", label: "Clientes", icon: "clientes" as IconKey },
    ],
  },
  {
    title: "Agentes de IA",
    items: [
      { href: "/agentes/analise-estoque", label: "Análise de Estoque", icon: "agente" as IconKey },
      { href: "/notas-entrada", label: "Notas de Entrada", icon: "notasEntrada" as IconKey },
      { href: "/auditoria", label: "Auditoria", icon: "auditoria" as IconKey },
      { href: "/atendimento", label: "Atendimento (Avatar)", icon: "atendimento" as IconKey },
    ],
  },
];

interface SidebarProps {
  mobileOpen: boolean;
  onCloseMobile: () => void;
}

export function Sidebar({ mobileOpen, onCloseMobile }: SidebarProps) {
  const pathname = usePathname();
  const router = useRouter();

  function sair() {
    clearToken();
    onCloseMobile();
    router.replace("/login");
  }

  return (
    <>
      {/* Backdrop: so existe (e so intercepta clique) no mobile, com o menu aberto. */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/60 lg:hidden"
          onClick={onCloseMobile}
          aria-hidden="true"
        />
      )}
      <aside
        className={`fixed inset-y-0 left-0 z-40 flex h-screen w-64 shrink-0 flex-col border-r border-slate-200 bg-white transition-transform duration-200 ease-out lg:static lg:translate-x-0 ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center gap-2.5 px-5 py-6">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-red-500 to-red-600 text-sm font-bold text-white shadow-lg shadow-red-500/20">
            M
          </div>
          <div>
            <p className="text-sm font-semibold tracking-tight text-slate-900">Farmácia MAS</p>
            <p className="text-xs text-slate-500">Painel de gestão</p>
          </div>
          <button
            onClick={onCloseMobile}
            aria-label="Fechar menu"
            className="ml-auto rounded-md p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-700 lg:hidden"
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={1.6}
              strokeLinecap="round"
              strokeLinejoin="round"
              className="h-4 w-4"
              aria-hidden="true"
            >
              <path d="M18 6 6 18M6 6l12 12" />
            </svg>
          </button>
        </div>
        <nav className="flex-1 overflow-y-auto px-3 pb-6">
          {NAV_GROUPS.map((group) => (
            <div key={group.title} className="mb-5">
              <p className="mb-1.5 px-3 text-[11px] font-semibold uppercase tracking-wider text-slate-600">
                {group.title}
              </p>
              <ul className="flex flex-col gap-0.5">
                {group.items.map((item) => {
                  const active = pathname === item.href;
                  return (
                    <li key={item.href}>
                      <Link
                        href={item.href}
                        onClick={onCloseMobile}
                        className={`group relative flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-colors ${
                          active ? "bg-slate-100 text-slate-900" : "text-slate-400 hover:bg-slate-100 hover:text-slate-900"
                        }`}
                      >
                        {active && (
                          <span className="absolute left-0 top-1/2 h-4 w-[3px] -translate-y-1/2 rounded-full bg-red-500" />
                        )}
                        <Icon
                          name={item.icon}
                          className={`h-4 w-4 shrink-0 ${active ? "text-red-600" : "text-slate-500 group-hover:text-slate-600"}`}
                        />
                        {item.label}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </nav>
        <div className="border-t border-slate-200 px-3 py-3">
          <button
            onClick={sair}
            className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-900"
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={1.6}
              strokeLinecap="round"
              strokeLinejoin="round"
              className="h-4 w-4 shrink-0"
              aria-hidden="true"
            >
              <path d="M15 17l5-5-5-5M20 12H9M12 19H6a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h6" />
            </svg>
            Sair
          </button>
        </div>
      </aside>
    </>
  );
}
