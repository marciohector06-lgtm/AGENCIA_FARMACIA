"use client";

/**
 * Voz no atendimento (Nível 2). Reconhecimento de voz (fala -> texto) é só
 * frontend, API nativa do navegador:
 *
 * SUPORTE DE NAVEGADOR (documentado aqui de propósito, ver restrição da
 * tarefa):
 * - Reconhecimento de voz (fala -> texto, `SpeechRecognition`):
 *     Chrome/Edge (desktop e Android) — suporte completo, via
 *     `webkitSpeechRecognition` (nunca saiu do prefixo, mesmo nas versões
 *     recentes). Firefox NUNCA implementou essa API — não existe standard
 *     nem prefixado, não é uma questão de versão. Safari (desktop/iOS) tem
 *     suporte parcial e historicamente instável. Testado manualmente nesta
 *     implementação em: Chrome (Windows). Onde não há suporte, `suportado`
 *     volta `false` e a página não deve renderizar o botão de microfone —
 *     cai pro campo de texto normal, sem nenhum erro exibido.
 *
 * Síntese de voz (texto -> fala) usa a API da ElevenLabs via /api/tts (rota
 * server-side em src/app/api/tts/route.ts — a chave nunca chega ao
 * navegador). Se a chamada falhar por qualquer motivo (rede, chave ausente,
 * cota da ElevenLabs esgotada, etc.), cai automaticamente pro
 * `SpeechSynthesis` nativo do navegador, mesmo usado antes desta integração
 * — nunca fica muda.
 */

import { useCallback, useEffect, useRef, useState } from "react";

const SILENCIO_AUTO_ENVIO_MS = 1500;

interface UseReconhecimentoVozOptions {
  // Disparado a cada evento de reconhecimento (parcial ou final) — usado
  // pra preencher o campo de texto em tempo real, o cliente vê e pode
  // corrigir antes de mandar.
  onTextoAtualizado?: (texto: string) => void;
  // Disparado 1.5s depois do último resultado reconhecido, sem nenhum novo
  // resultado nesse intervalo — só o chamador decide se isso vira um envio
  // automático (ver toggle "autoEnvio" na página).
  onSilencio?: (texto: string) => void;
}

export function useReconhecimentoVoz({ onTextoAtualizado, onSilencio }: UseReconhecimentoVozOptions = {}) {
  const [suportado, setSuportado] = useState(false);
  const [gravando, setGravando] = useState(false);
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const silencioTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    // Detecção de suporte do navegador só pode rodar no client — feito em
    // efeito (não no render) de propósito, pra servidor e 1º render do
    // client baterem (ambos "false") e não gerar mismatch de hidratação.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSuportado(typeof window !== "undefined" && !!(window.SpeechRecognition ?? window.webkitSpeechRecognition));
  }, []);

  const limparTimerSilencio = useCallback(() => {
    if (silencioTimerRef.current) {
      clearTimeout(silencioTimerRef.current);
      silencioTimerRef.current = null;
    }
  }, []);

  const iniciar = useCallback(() => {
    const Ctor = window.SpeechRecognition ?? window.webkitSpeechRecognition;
    if (!Ctor) return;

    const recognition = new Ctor();
    recognition.lang = "pt-BR";
    recognition.continuous = true;
    recognition.interimResults = true;

    recognition.onresult = (event) => {
      // continuous=true mantém TODOS os resultados da sessão em
      // event.results — reconstrói o texto inteiro a cada evento em vez de
      // acumular manualmente, mais simples e sem risco de duplicar trecho.
      let final = "";
      let parcial = "";
      for (let i = 0; i < event.results.length; i++) {
        const resultado = event.results[i];
        const transcript = resultado[0]?.transcript ?? "";
        if (resultado.isFinal) {
          final += `${transcript} `;
        } else {
          parcial += transcript;
        }
      }
      const textoCompleto = (final + parcial).trim();
      onTextoAtualizado?.(textoCompleto);

      limparTimerSilencio();
      silencioTimerRef.current = setTimeout(() => {
        onSilencio?.(textoCompleto);
      }, SILENCIO_AUTO_ENVIO_MS);
    };

    recognition.onerror = () => {
      setGravando(false);
    };

    recognition.onend = () => {
      setGravando(false);
      limparTimerSilencio();
    };

    recognitionRef.current = recognition;
    recognition.start();
    setGravando(true);
  }, [limparTimerSilencio, onSilencio, onTextoAtualizado]);

  const parar = useCallback(() => {
    recognitionRef.current?.stop();
    limparTimerSilencio();
    setGravando(false);
  }, [limparTimerSilencio]);

  useEffect(() => {
    return () => {
      recognitionRef.current?.abort();
      limparTimerSilencio();
    };
  }, [limparTimerSilencio]);

  return { suportado, gravando, iniciar, parar };
}

interface UseSinteseOptions {
  rate?: number;
}

interface AlignmentData {
  characters: string[];
  character_start_times_seconds: number[];
  character_end_times_seconds: number[];
}

const VOGAIS = new Set(["a", "e", "i", "o", "u", "á", "à", "â", "ã", "é", "ê", "í", "ó", "ô", "õ", "ú"]);

function ehVogal(caractere: string | undefined): boolean {
  return !!caractere && VOGAIS.has(caractere.toLowerCase());
}

export function useSintese({ rate = 0.9 }: UseSinteseOptions = {}) {
  const [suportado, setSuportado] = useState(false);
  const [falando, setFalando] = useState(false);
  // Estado real de abertura de boca, derivado do alinhamento por caractere
  // que a ElevenLabs devolve junto do áudio (visema aproximado: vogal =
  // boca aberta, consoante/espaço/pontuação = boca fechada), sincronizado
  // contra o tempo de reprodução real do áudio. null quando não há
  // sincronismo real disponível (fallback de SpeechSynthesis, ou entre uma
  // fala e outra) — nesse caso quem decide o quadro é o timer placeholder
  // de AvatarFarmaceutica, sem mudança de comportamento.
  const [bocaAberta, setBocaAberta] = useState<boolean | null>(null);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const rafRef = useRef<number | null>(null);
  // Geração em vez de um simples boolean "cancelado": falar() pode ser
  // chamado de novo antes do loop assíncrono anterior perceber que foi
  // parado (ex.: cliente aperta o mic no meio de uma fala) — um boolean
  // reiniciado no novo falar() faria o loop antigo, que ainda checa esse
  // mesmo boolean, achar que não foi cancelado.
  const geracaoRef = useRef(0);

  useEffect(() => {
    // Mesmo motivo do useReconhecimentoVoz acima: detecção de suporte só no
    // client, feita em efeito para servidor e 1º render baterem.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSuportado(typeof window !== "undefined");
  }, []);

  const pararVisemas = useCallback(() => {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
    setBocaAberta(null);
  }, []);

  // Fallback nativo do navegador — mesmo comportamento de antes desta
  // integração, só que agora encapsulado numa Promise (resolve quando a
  // fila de utterances passadas termina) pra falar() conseguir aguardar a
  // conclusão antes de seguir pro próximo texto, igual ao caminho ElevenLabs.
  const falarComSpeechSynthesis = useCallback(
    (textos: string[]): Promise<void> => {
      return new Promise((resolve) => {
        if (typeof window === "undefined" || !("speechSynthesis" in window)) {
          resolve();
          return;
        }
        const validos = textos.filter((t) => t && t.trim().length > 0);
        if (validos.length === 0) {
          resolve();
          return;
        }
        validos.forEach((texto, index) => {
          const utterance = new SpeechSynthesisUtterance(texto);
          utterance.lang = "pt-BR";
          utterance.rate = rate;
          if (index === validos.length - 1) {
            utterance.onend = () => resolve();
            utterance.onerror = () => resolve();
          }
          window.speechSynthesis.speak(utterance);
        });
      });
    },
    [rate],
  );

  // Chama /api/tts (proxy server-side pra ElevenLabs, ver route.ts) e toca o
  // áudio devolvido, sincronizando bocaAberta contra o alinhamento por
  // caractere. Devolve false se a chamada falhar por qualquer motivo (rede,
  // chave ausente, cota esgotada) — falar() cai pro SpeechSynthesis nesse
  // caso, texto por texto.
  const falarComElevenLabs = useCallback(
    async (texto: string, minhaGeracao: number): Promise<boolean> => {
      let resp: Response;
      try {
        resp = await fetch("/api/tts", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ texto }),
        });
      } catch {
        return false;
      }
      if (!resp.ok) return false;

      let data: { audioBase64?: string; alignment?: AlignmentData | null };
      try {
        data = await resp.json();
      } catch {
        return false;
      }
      if (!data.audioBase64) return false;
      if (geracaoRef.current !== minhaGeracao) return true; // já foi parado, mas foi ElevenLabs (não cai pro fallback)

      const audio = new Audio(`data:audio/mpeg;base64,${data.audioBase64}`);
      audioRef.current = audio;
      const alignment = data.alignment ?? null;

      await new Promise<void>((resolve) => {
        const finalizar = () => {
          pararVisemas();
          resolve();
        };

        if (alignment && alignment.characters.length > 0) {
          const atualizarVisema = () => {
            if (geracaoRef.current !== minhaGeracao) return;
            const t = audio.currentTime;
            const { characters, character_start_times_seconds, character_end_times_seconds } = alignment;
            let idx = -1;
            for (let i = 0; i < characters.length; i++) {
              if (t >= character_start_times_seconds[i] && t < character_end_times_seconds[i]) {
                idx = i;
                break;
              }
            }
            setBocaAberta(idx >= 0 ? ehVogal(characters[idx]) : false);
            rafRef.current = requestAnimationFrame(atualizarVisema);
          };
          rafRef.current = requestAnimationFrame(atualizarVisema);
        }

        audio.onended = finalizar;
        audio.onerror = finalizar;
        audio.play().catch(finalizar);
      });

      return true;
    },
    [pararVisemas],
  );

  // Fala uma sequência de textos em ordem (disclaimer, depois a resposta),
  // um de cada vez — tenta ElevenLabs primeiro, cai pro SpeechSynthesis
  // nativo só para aquele texto específico se a chamada falhar.
  const falar = useCallback(
    (textos: string[]) => {
      const minhaGeracao = ++geracaoRef.current;
      const validos = textos.filter((t) => t && t.trim().length > 0);
      if (validos.length === 0) return;

      setFalando(true);
      (async () => {
        for (const texto of validos) {
          if (geracaoRef.current !== minhaGeracao) return;
          const tocouComElevenLabs = await falarComElevenLabs(texto, minhaGeracao);
          if (geracaoRef.current !== minhaGeracao) return;
          if (!tocouComElevenLabs) {
            await falarComSpeechSynthesis([texto]);
            if (geracaoRef.current !== minhaGeracao) return;
          }
        }
        setFalando(false);
      })();
    },
    [falarComElevenLabs, falarComSpeechSynthesis],
  );

  const pararFala = useCallback(() => {
    geracaoRef.current++; // invalida qualquer loop assíncrono de falar() em andamento
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
    pararVisemas();
    setFalando(false);
  }, [pararVisemas]);

  useEffect(() => {
    return () => {
      // Ref (não DOM node) lido no valor mais atual de propósito no
      // unmount — a preocupação de "staleness" da regra não se aplica aqui.
      // eslint-disable-next-line react-hooks/exhaustive-deps
      geracaoRef.current++;
      audioRef.current?.pause();
      if (typeof window !== "undefined" && "speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    };
  }, []);

  return { suportado, falando, bocaAberta, falar, pararFala };
}
