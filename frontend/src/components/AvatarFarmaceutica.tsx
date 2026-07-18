"use client";

import Image from "next/image";
import { useEffect, useState } from "react";

export type EstadoAvatar = "esperando" | "ouvindo" | "pensando" | "falando";

const INTERVALO_BOCA_MS = 150;
const QUADROS = ["esperando", "ouvindo", "pensando", "boca_fechada", "boca_aberta"] as const;

interface AvatarFarmaceuticaProps {
  estado: EstadoAvatar;
  // "cover" (padrão): preenche o container cortando o que exceder — usado no
  // modo fullscreen, onde a foto ocupa a tela toda. "contain": mostra a
  // imagem inteira sem cortar — usado no modo cartoon, onde o personagem
  // tem fundo limpo e precisa aparecer inteiro (corpo visível) dentro de um
  // container menor. Quem decide o tamanho/posição desse container é sempre
  // quem chama este componente (TotemFullscreenLayout / TotemCartoonLayout),
  // nunca este arquivo — ele só cuida do crossfade entre os 5 quadros.
  objectFit?: "cover" | "contain";
}

// Todos os 5 quadros ficam empilhados (position: absolute, mesmo lugar) e a
// troca de estado só alterna qual tem opacity-100 — dá o crossfade suave sem
// o "pisca" que trocar o src de uma única <img> causaria, e sem esperar a
// imagem carregar no meio da troca (todas já estão na página,
// pré-carregadas).
export function AvatarFarmaceutica({ estado, objectFit = "cover" }: AvatarFarmaceuticaProps) {
  const [bocaAberta, setBocaAberta] = useState(false);

  // Reseta a boca assim que o estado deixa de ser "falando" — ajuste durante
  // o render (não em efeito) para não disparar um render em cascata.
  const [estadoAnterior, setEstadoAnterior] = useState(estado);
  if (estado !== estadoAnterior) {
    setEstadoAnterior(estado);
    if (estado !== "falando") setBocaAberta(false);
  }

  useEffect(() => {
    if (estado !== "falando") return;
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
    <div className={`absolute inset-0 ${estado === "esperando" ? "animate-respirar" : ""}`}>
      {QUADROS.map((quadro) => (
        <Image
          key={quadro}
          src={`/avatar/${quadro}.png`}
          alt="Farmacêutica virtual"
          fill
          priority={quadro === "esperando"}
          sizes="100vw"
          className={`${objectFit === "cover" ? "object-cover" : "object-contain"} transition-opacity duration-200 ${
            quadro === quadroAtivo ? "opacity-100" : "opacity-0"
          }`}
        />
      ))}
    </div>
  );
}
