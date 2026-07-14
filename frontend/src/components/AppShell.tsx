"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Sidebar } from "@/components/Sidebar";
import { getToken } from "@/lib/api";

const ROTAS_PUBLICAS = ["/login"];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const publica = ROTAS_PUBLICAS.includes(pathname);
  // Leitura síncrona (não é estado): getToken() devolve null no SSR e o
  // valor real assim que hidrata no cliente, sem precisar de um efeito só
  // pra guardar algo que já dá pra derivar direto do localStorage.
  const autenticado = publica || getToken() !== null;

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
      <Sidebar />
      <main className="flex-1 overflow-y-auto p-8">
        <div className="mx-auto w-full max-w-6xl">{children}</div>
      </main>
    </div>
  );
}
