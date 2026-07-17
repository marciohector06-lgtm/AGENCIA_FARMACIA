"use client";

import Image from "next/image";
import { useEffect, useState } from "react";

export type EstadoAvatar = "esperando" | "ouvindo" | "pensando" | "falando";

const INTERVALO_BOCA_MS = 150;
const QUADROS = ["esperando", "ouvindo", "pensando", "boca_fechada", "boca_aberta"] as const;

interface AvatarFarmaceuticaProps {
  estado: EstadoAvatar;
}

// Todos os 5 quadros ficam empilhados (position: absolute, mesmo lugar) e a
// troca de estado só alterna qual tem opacity-100 — dá o crossfade suave
// pedido (transition-opacity) sem o "pisca" que trocar o src de uma única
// <img> causaria, e sem esperar a imagem carregar no meio da troca (todas já
// estão na página, pré-carregadas).
export function AvatarFarmaceutica({ estado }: AvatarFarmaceuticaProps) {
  const [bocaAberta, setBocaAberta] = useState(false);

  useEffect(() => {
    if (estado !== "falando") {
      setBocaAberta(false);
      return;
    }
    // Placeholder de "está falando" — alterna boca aberta/fechada num
    // intervalo fixo, sem relação com o áudio real. Lip-sync de verdade
    // entraria aqui: trocar este setInterval por quadros escolhidos a partir
    // da análise do áudio da síntese de voz (ex.: amplitude ou visemas do
    // useSintese em useVoz.ts) em vez de um piscar genérico.
    const timer = setInterval(() => setBocaAberta((v) => !v), INTERVALO_BOCA_MS);
    return () => clearInterval(timer);
  }, [estado]);

  const quadroAtivo = estado === "falando" ? (bocaAberta ? "boca_aberta" : "boca_fechada") : estado;

  return (
    <div className="relative mx-auto h-56 w-56 shrink-0 sm:h-72 sm:w-72">
      {QUADROS.map((quadro) => (
        <Image
          key={quadro}
          src={`/avatar/${quadro}.png`}
          alt="Farmacêutica virtual"
          fill
          priority={quadro === "esperando"}
          sizes="(min-width: 640px) 288px, 224px"
          className={`rounded-full object-cover shadow-lg transition-opacity duration-200 ${
            quadro === quadroAtivo ? "opacity-100" : "opacity-0"
          }`}
        />
      ))}
    </div>
  );
}
