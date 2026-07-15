const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api/v1";
const TOKEN_KEY = "farmacia_mas_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  window.localStorage.removeItem(TOKEN_KEY);
}

// LLM-05: sem isso um crew.kickoff() lento no backend deixa o cliente
// esperando indefinidamente, sem nenhum feedback — o backend já tem seu
// próprio timeout (CREW_TIMEOUT_SECONDS), mas o fetch do navegador não tem
// limite embutido nenhum.
const REQUEST_TIMEOUT_MS = Number(process.env.NEXT_PUBLIC_REQUEST_TIMEOUT_MS ?? 100000);

export class ApiError extends Error {
  status: number;
  detail: string;
  // QA: erro por campo (422 de validação do Pydantic) — permite o form
  // mostrar a mensagem embaixo do campo certo em vez de só um banner
  // genérico no topo. Ausente em erros de negócio (409/403/...), que não
  // têm um campo específico associado.
  fieldErrors?: Record<string, string>;

  constructor(status: number, detail: string, fieldErrors?: Record<string, string>) {
    super(detail);
    this.status = status;
    this.detail = detail;
    this.fieldErrors = fieldErrors;
  }
}

export class ApiTimeoutError extends Error {
  constructor() {
    super("A solicitação demorou demais para responder. Tente novamente em instantes.");
  }
}

interface ValidationErrorItem {
  loc?: (string | number)[];
  msg?: string;
}

// O FastAPI devolve `detail` como string em erros de negócio (HTTPException),
// mas como uma LISTA de objetos {loc, msg, type} em erros de validação (422).
// Sem isso, um 422 vira um objeto sendo renderizado direto no JSX e quebra a UI.
function stringifyDetail(detail: unknown): string | undefined {
  if (detail == null) return undefined;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return (detail as ValidationErrorItem[])
      .map((item) => {
        const field = item.loc?.[item.loc.length - 1];
        return field ? `${field}: ${item.msg}` : item.msg;
      })
      .filter(Boolean)
      .join("; ");
  }
  return JSON.stringify(detail);
}

// Mesma lista de erros de validação, mas indexada por campo (último item de
// `loc`, que pula o "body" inicial) — undefined quando `detail` não é essa
// forma (409 de negócio, string simples, etc.), nunca um objeto vazio.
function extractFieldErrors(detail: unknown): Record<string, string> | undefined {
  if (!Array.isArray(detail)) return undefined;
  const map: Record<string, string> = {};
  for (const item of detail as ValidationErrorItem[]) {
    const field = item.loc?.[item.loc.length - 1];
    if (typeof field === "string" && item.msg) {
      map[field] = item.msg;
    }
  }
  return Object.keys(map).length > 0 ? map : undefined;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  const token = getToken();

  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      ...init,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(init?.headers ?? {}),
      },
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new ApiTimeoutError();
    }
    throw err;
  } finally {
    clearTimeout(timeoutId);
  }

  // Token ausente/expirado: derruba a sessão local e manda pro login, exceto
  // quando a própria tentativa de login é que devolveu 401 (credenciais erradas).
  if (response.status === 401 && path !== "/auth/login") {
    clearToken();
    if (typeof window !== "undefined") window.location.href = "/login";
  }

  if (!response.ok) {
    let detail = response.statusText;
    let fieldErrors: Record<string, string> | undefined;
    try {
      const body = await response.json();
      detail = stringifyDetail(body.detail) ?? detail;
      fieldErrors = extractFieldErrors(body.detail);
    } catch {
      // corpo nao era JSON, mantem statusText
    }
    throw new ApiError(response.status, detail, fieldErrors);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => request<T>(path, { method: "GET" }),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body) }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
  delete: (path: string) => request<void>(path, { method: "DELETE" }),
};
