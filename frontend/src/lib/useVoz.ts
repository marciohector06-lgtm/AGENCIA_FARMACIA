"use client";

/**
 * Voz no atendimento (Nível 2) — só frontend, nenhuma chamada nova ao
 * backend. Duas APIs nativas do navegador, sem custo e sem dependência:
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
 * - Síntese de voz (texto -> fala, `SpeechSynthesis`):
 *     Padrão bem estabelecido — funciona em Chrome, Edge, Firefox e Safari.
 *     A voz/sotaque pt-BR disponível depende do sistema operacional do
 *     usuário, fora do nosso controle.
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

export function useSintese({ rate = 0.9 }: UseSinteseOptions = {}) {
  const [suportado, setSuportado] = useState(false);
  const [falando, setFalando] = useState(false);

  useEffect(() => {
    setSuportado(typeof window !== "undefined" && "speechSynthesis" in window);
  }, []);

  // Fala uma sequência de textos em ordem (disclaimer, depois a resposta) —
  // a fila nativa do navegador já processa em ordem, não precisa encadear
  // manualmente por onend.
  const falar = useCallback(
    (textos: string[]) => {
      if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
      window.speechSynthesis.cancel(); // nunca empilha em cima de uma fala anterior
      const validos = textos.filter((t) => t && t.trim().length > 0);
      if (validos.length === 0) return;

      validos.forEach((texto, index) => {
        const utterance = new SpeechSynthesisUtterance(texto);
        utterance.lang = "pt-BR";
        utterance.rate = rate;
        if (index === 0) utterance.onstart = () => setFalando(true);
        if (index === validos.length - 1) {
          utterance.onend = () => setFalando(false);
          utterance.onerror = () => setFalando(false);
        }
        window.speechSynthesis.speak(utterance);
      });
    },
    [rate],
  );

  const pararFala = useCallback(() => {
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
    setFalando(false);
  }, []);

  useEffect(() => {
    return () => {
      if (typeof window !== "undefined" && "speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  return { suportado, falando, falar, pararFala };
}
