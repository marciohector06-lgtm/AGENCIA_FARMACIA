"use client";

import { useEffect, useSyncExternalStore } from "react";
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

  useEffect(() => {
    if (!publica && !temToken) {
      router.replace("/login");
    }
  }, [pathname, publica, temToken, router]);

  if (publica) {
    return <>{children}</>;
  }

  if (!autenticado) {
    return null;
  }

  return (
    <div className="flex h-full min-h-screen w-full">
      <Sidebar />
      <main className="flex-1 overflow-y-auto p-8">
        <div className="mx-auto w-full max-w-6xl">{children}</div>
      </main>
    </div>
  );
}
