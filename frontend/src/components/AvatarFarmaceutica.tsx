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
  // Lip-sync real (ElevenLabs, ver useSintese em src/lib/useVoz.ts): quando
  // presente (não-null/undefined), substitui o timer placeholder abaixo —
  // vem do alinhamento por caractere devolvido junto do áudio, sincronizado
  // contra o tempo de reprodução real. Ausente (undefined) ou null (sem
  // áudio com alinhamento disponível no momento, ex.: fallback de
  // SpeechSynthesis) mantém o piscar de intervalo fixo de sempre.
  bocaAbertaExterna?: boolean | null;
}

// Todos os 5 quadros ficam empilhados (position: absolute, mesmo lugar) e a
// troca de estado só alterna qual tem opacity-100 — dá o crossfade suave sem
// o "pisca" que trocar o src de uma única <img> causaria, e sem esperar a
// imagem carregar no meio da troca (todas já estão na página,
// pré-carregadas).
export function AvatarFarmaceutica({ estado, objectFit = "cover", bocaAbertaExterna }: AvatarFarmaceuticaProps) {
  const [bocaAbertaPlaceholder, setBocaAbertaPlaceholder] = useState(false);
  // Lip-sync real (ElevenLabs) disponível: usa direto, sem rodar o timer
  // placeholder abaixo. undefined (prop nem passada, ex.: AtendimentoPanel
  // não usa Avatar) ou null (sem alinhamento disponível agora, ex.: fallback
  // de SpeechSynthesis) mantém o piscar de intervalo fixo de sempre.
  const temSincronismoReal = bocaAbertaExterna !== undefined && bocaAbertaExterna !== null;

  // Reseta a boca assim que o estado deixa de ser "falando" — ajuste durante
  // o render (não em efeito) para não disparar um render em cascata.
  const [estadoAnterior, setEstadoAnterior] = useState(estado);
  if (estado !== estadoAnterior) {
    setEstadoAnterior(estado);
    if (estado !== "falando") setBocaAbertaPlaceholder(false);
  }

  useEffect(() => {
    if (estado !== "falando" || temSincronismoReal) return;
    // Placeholder de "está falando" — alterna boca aberta/fechada num
    // intervalo fixo, sem relação com o áudio real. Usado só quando não há
    // sincronismo real disponível (ver bocaAbertaExterna acima).
    const timer = setInterval(() => setBocaAbertaPlaceholder((v) => !v), INTERVALO_BOCA_MS);
    return () => clearInterval(timer);
  }, [estado, temSincronismoReal]);

  const bocaAberta = temSincronismoReal ? bocaAbertaExterna : bocaAbertaPlaceholder;
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
