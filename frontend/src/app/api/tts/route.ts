import { NextRequest, NextResponse } from "next/server";

/**
 * Proxy server-side pra síntese de voz via ElevenLabs — nunca expõe
 * ELEVENLABS_API_KEY ao navegador (sem NEXT_PUBLIC_, só existe aqui, no
 * processo Next server). O client (useSintese em src/lib/useVoz.ts) chama
 * esta rota, nunca a API da ElevenLabs diretamente.
 */

const ELEVENLABS_BASE_URL = "https://api.elevenlabs.io/v1";
const MODEL_ID = "eleven_multilingual_v2";

interface ElevenLabsVoice {
  voice_id: string;
  name: string;
  labels?: Record<string, string>;
  verified_languages?: { language: string; accent?: string | null; locale?: string | null }[];
}

interface ElevenLabsVoicesResponse {
  voices: ElevenLabsVoice[];
}

interface AlignmentData {
  characters: string[];
  character_start_times_seconds: number[];
  character_end_times_seconds: number[];
}

interface ElevenLabsTtsResponse {
  audio_base64: string;
  alignment: AlignmentData | null;
  normalized_alignment: AlignmentData | null;
}

// Só consultado quando ELEVENLABS_VOICE_ID não está configurado — resultado
// cacheado em memória pela vida do processo (a lista de vozes da conta não
// muda durante uma execução, e cada chamada extra é uma requisição a mais
// pra ElevenLabs que a conta pode nem ter permissão de fazer — ver
// resolverVoiceId).
let vozResolvidaCache: string | null = null;

// Escolhe a melhor voz feminina em pt-BR disponível na conta: prioriza
// verified_languages (mais confiável — a ElevenLabs testou aquela voz
// naquele idioma) e usa os labels (gender/accent/description) como sinal
// secundário, já que "labels" é um mapa livre sem chaves garantidas.
function pontuarVoz(voz: ElevenLabsVoice): number {
  let pontos = 0;
  const labels = voz.labels ?? {};
  const idiomasVerificados = voz.verified_languages ?? [];

  if (idiomasVerificados.some((l) => l.language?.toLowerCase().startsWith("pt"))) pontos += 10;
  if (idiomasVerificados.some((l) => (l.locale ?? "").toLowerCase().includes("br"))) pontos += 4;

  const textoBusca = `${labels.language ?? ""} ${labels.accent ?? ""} ${labels.description ?? ""} ${voz.name}`.toLowerCase();
  if (textoBusca.includes("brazil") || textoBusca.includes("português") || textoBusca.includes("portuguese")) {
    pontos += 6;
  }
  if ((labels.gender ?? "").toLowerCase() === "female") pontos += 5;

  return pontos;
}

async function resolverVoiceId(): Promise<string> {
  const configurado = process.env.ELEVENLABS_VOICE_ID;
  if (configurado) return configurado;
  if (vozResolvidaCache) return vozResolvidaCache;

  const resp = await fetch(`${ELEVENLABS_BASE_URL}/voices`, {
    headers: { "xi-api-key": process.env.ELEVENLABS_API_KEY ?? "" },
  });
  if (!resp.ok) {
    throw new Error(`GET /v1/voices falhou (${resp.status}) — configure ELEVENLABS_VOICE_ID pra pular esta chamada`);
  }
  const data = (await resp.json()) as ElevenLabsVoicesResponse;
  if (!data.voices || data.voices.length === 0) {
    throw new Error("Conta ElevenLabs sem nenhuma voz disponível");
  }

  const melhor = [...data.voices].sort((a, b) => pontuarVoz(b) - pontuarVoz(a))[0];
  vozResolvidaCache = melhor.voice_id;
  return melhor.voice_id;
}

export async function POST(request: NextRequest) {
  const apiKey = process.env.ELEVENLABS_API_KEY;
  if (!apiKey) {
    return NextResponse.json({ erro: "ELEVENLABS_API_KEY não configurada" }, { status: 503 });
  }

  let texto: string | undefined;
  try {
    const body = (await request.json()) as { texto?: string };
    texto = body.texto;
  } catch {
    return NextResponse.json({ erro: "corpo da requisição inválido" }, { status: 400 });
  }
  if (!texto || !texto.trim()) {
    return NextResponse.json({ erro: "texto vazio" }, { status: 400 });
  }

  try {
    const voiceId = await resolverVoiceId();
    const resp = await fetch(`${ELEVENLABS_BASE_URL}/text-to-speech/${voiceId}/with-timestamps?output_format=mp3_44100_128`, {
      method: "POST",
      headers: {
        "xi-api-key": apiKey,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        text: texto,
        model_id: MODEL_ID,
        voice_settings: { stability: 0.5, similarity_boost: 0.75 },
      }),
    });

    if (!resp.ok) {
      const detalhe = await resp.text();
      return NextResponse.json({ erro: `ElevenLabs ${resp.status}: ${detalhe}` }, { status: 502 });
    }

    const data = (await resp.json()) as ElevenLabsTtsResponse;
    return NextResponse.json({ audioBase64: data.audio_base64, alignment: data.alignment });
  } catch (err) {
    return NextResponse.json({ erro: err instanceof Error ? err.message : "erro desconhecido" }, { status: 502 });
  }
}
