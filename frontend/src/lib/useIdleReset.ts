"use client";

import { useEffect, useRef } from "react";

const EVENTOS_ATIVIDADE = ["pointerdown", "pointermove", "keydown", "touchstart"] as const;

// Totem: qualquer toque/tecla do cliente conta como atividade e adia o
// reset; o callback só dispara depois de `timeoutMs` sem nenhum desses
// eventos. `deps` permite rearmar o timer do zero quando a sessão muda (ex.:
// depois de um reset manual, pra não herdar a contagem antiga).
export function useIdleReset(timeoutMs: number, onIdle: () => void, deps: unknown[] = []) {
  const onIdleRef = useRef(onIdle);
  useEffect(() => {
    onIdleRef.current = onIdle;
  });

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;

    function reiniciarTimer() {
      clearTimeout(timer);
      timer = setTimeout(() => onIdleRef.current(), timeoutMs);
    }

    reiniciarTimer();
    EVENTOS_ATIVIDADE.forEach((evento) => window.addEventListener(evento, reiniciarTimer));

    return () => {
      clearTimeout(timer);
      EVENTOS_ATIVIDADE.forEach((evento) => window.removeEventListener(evento, reiniciarTimer));
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [timeoutMs, ...deps]);
}
