"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError, setToken } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { FieldWrapper, TextInput } from "@/components/ui/Field";

interface TokenResponse {
  access_token: string;
  token_type: string;
}

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setErro(null);
    try {
      const resp = await api.post<TokenResponse>("/auth/login", { email, senha });
      setToken(resp.access_token);
      router.replace("/");
    } catch (err) {
      setErro(err instanceof ApiError ? err.detail : "Não foi possível entrar. Tente novamente.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm rounded-2xl border border-white/10 bg-[#0b0d13] p-8 shadow-2xl shadow-black/40">
        <div className="mb-6 flex flex-col items-center gap-2 text-center">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-400 to-emerald-600 text-base font-bold text-slate-950 shadow-lg shadow-emerald-500/20">
            M
          </div>
          <h1 className="text-lg font-semibold tracking-tight text-white">Farmácia MAS</h1>
          <p className="text-sm text-slate-400">Entre com sua conta de operador</p>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {erro && <div className="rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2 text-sm text-red-300">{erro}</div>}
          <FieldWrapper label="E-mail" htmlFor="email" required>
            <TextInput
              id="email"
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </FieldWrapper>
          <FieldWrapper label="Senha" htmlFor="senha" required>
            <TextInput
              id="senha"
              type="password"
              autoComplete="current-password"
              required
              value={senha}
              onChange={(e) => setSenha(e.target.value)}
            />
          </FieldWrapper>
          <Button type="submit" disabled={loading} className="mt-2 w-full">
            {loading ? "Entrando..." : "Entrar"}
          </Button>
        </form>
      </div>
    </div>
  );
}
