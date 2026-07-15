"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Sidebar } from "@/components/Sidebar";
import { getToken } from "@/lib/api";

const ROTAS_PUBLICAS = ["/login"];

function subscribeNoop() {
  return () => {};
}

// localStorage não existe no servidor — useSyncExternalStore é a forma
// correta de ler uma fonte externa dessas sem gerar hydration mismatch:
// o snapshot do servidor (segundo argumento) é sempre "sem token", e o
// React reconcilia sozinho a troca pro valor real assim que hidrata,
// sem precisar de um efeito "mounted" pra isso.
function useTemToken(): boolean {
  return useSyncExternalStore(
    subscribeNoop,
    () => getToken() !== null,
    () => false,
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const publica = ROTAS_PUBLICAS.includes(pathname);
  const temToken = useTemToken();
  const autenticado = publica || temToken;
  const [menuAberto, setMenuAberto] = useState(false);

  // Le o localStorage direto (nao o `temToken` do render) de proposito:
  // efeito so roda no cliente, entao nunca tem a ambiguidade de SSR que
  // useSyncExternalStore existe pra resolver no render. Usar `temToken`
  // aqui reabre exatamente esse problema: o efeito agendado pelo primeiro
  // render (o da reconciliacao de hidratacao, com temToken ainda "false")
  // dispara um redirect pra /login mesmo com token valido no storage.
  useEffect(() => {
    if (!publica && getToken() === null) {
      router.replace("/login");
    }
  }, [pathname, publica, router]);

  if (publica) {
    return <>{children}</>;
  }

  if (!autenticado) {
    return null;
  }

  return (
    <div className="flex h-full min-h-screen w-full">
      <Sidebar mobileOpen={menuAberto} onCloseMobile={() => setMenuAberto(false)} />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center gap-3 border-b border-white/[0.06] bg-[#08090e] px-4 py-3 lg:hidden">
          <button
            onClick={() => setMenuAberto(true)}
            aria-label="Abrir menu"
            className="rounded-md p-1.5 text-slate-300 hover:bg-white/[0.06]"
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={1.6}
              strokeLinecap="round"
              strokeLinejoin="round"
              className="h-5 w-5"
              aria-hidden="true"
            >
              <path d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <span className="text-sm font-semibold tracking-tight text-white">Farmácia MAS</span>
        </header>
        <main className="flex-1 overflow-y-auto p-4 lg:p-8">
          <div className="mx-auto w-full max-w-6xl">{children}</div>
        </main>
      </div>
    </div>
  );
}
