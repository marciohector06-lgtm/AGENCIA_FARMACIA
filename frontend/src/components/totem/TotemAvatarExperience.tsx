"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { FieldWrapper, TextInput } from "@/components/ui/Field";
import { Modal } from "@/components/ui/Modal";
import { AVISO_IA_TEXTO, useAtendimentoChat } from "@/lib/useAtendimentoChat";
import { AVATAR_MODE } from "@/lib/avatarConfig";
import { AvatarFarmaceutica, EstadoAvatar } from "@/components/AvatarFarmaceutica";
import { TotemFullscreenLayout } from "./TotemFullscreenLayout";
import { TotemCartoonLayout } from "./TotemCartoonLayout";

const DURACAO_LEGENDA_MS = 7_000;

interface TotemAvatarExperienceProps {
  filialIdFixa: string;
  onVendaConfirmada?: () => void;
}

// Dono de todo o estado (voz, LGPD, guardrails, confirmação de compra —
// tudo vem de useAtendimentoChat, o mesmo hook usado por /atendimento).
// Só decide QUAL layout desenhar isso (AVATAR_MODE, ver avatarConfig.ts);
// o desenho em si fica inteiramente em TotemFullscreenLayout ou
// TotemCartoonLayout, que nunca tocam o hook diretamente.
export function TotemAvatarExperience({ filialIdFixa, onVendaConfirmada }: TotemAvatarExperienceProps) {
  const {
    setClienteId,
    precisaConsentimento,
    enviandoConsentimento,
    aceitarConsentimento,
    mensagens,
    input,
    setInput,
    loading,
    erro,
    perfilAberto,
    setPerfilAberto,
    medicamentosEmUso,
    setMedicamentosEmUso,
    gestante,
    setGestante,
    lactante,
    setLactante,
    idade,
    setIdade,
    micSuportado,
    gravando,
    falando,
    bocaAberta,
    alternarGravacao,
    pararFala,
    enviarMensagem,
    confirmarCompra,
  } = useAtendimentoChat({ filialIdFixa, onVendaConfirmada });

  const [mostrarTeclado, setMostrarTeclado] = useState(false);
  const [aguardandoHumano, setAguardandoHumano] = useState(false);
  const [legendaVisivel, setLegendaVisivel] = useState(false);

  const estadoAvatar: EstadoAvatar = gravando ? "ouvindo" : loading ? "pensando" : falando ? "falando" : "esperando";
  const ultimaMensagem = mensagens[mensagens.length - 1];
  const produtosSugeridos = ultimaMensagem?.role === "avatar" ? (ultimaMensagem.produtos ?? []) : [];

  // Mostra a legenda assim que chega um turno novo — ajuste durante o
  // render (não em efeito) para não disparar um render em cascata.
  const [mensagemAnterior, setMensagemAnterior] = useState(ultimaMensagem);
  if (ultimaMensagem !== mensagemAnterior) {
    setMensagemAnterior(ultimaMensagem);
    if (ultimaMensagem) setLegendaVisivel(true);
  }

  // Some sozinha depois de alguns segundos — mas só começa a contar depois
  // que ela termina de falar, senão a legenda podia sumir no meio da fala.
  useEffect(() => {
    if (!ultimaMensagem || falando) return;
    const timer = setTimeout(() => setLegendaVisivel(false), DURACAO_LEGENDA_MS);
    return () => clearTimeout(timer);
  }, [ultimaMensagem, falando]);

  // Tap único no mic: idle -> grava; gravando -> para de gravar E já manda
  // (o cliente ouve a transcrição ao vivo enquanto fala, então "parar" já é
  // a confirmação explícita — não precisa de um botão de enviar separado).
  // Se ainda sobrou texto gravado sem enviar por algum motivo, o botão vira
  // um "confirmar" (CheckIcon) até ser tocado.
  const temTextoPendente = !gravando && !loading && input.trim() !== "";

  function tocarMic() {
    if (temTextoPendente) {
      enviarMensagem();
      return;
    }
    alternarGravacao();
  }

  function onFalarComFarmaceutico() {
    pararFala();
    setAguardandoHumano(true);
  }

  if (aguardandoHumano) {
    // Estado raro/simples — mantido igual nos dois modos, sempre no formato
    // "tela cheia" (não vale a pena um cartoon-specific pra isto).
    return (
      <div className="relative h-screen w-screen overflow-hidden bg-slate-950">
        <AvatarFarmaceutica estado="esperando" objectFit="cover" />
        <div className="absolute inset-0 bg-black/60" />
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-6 px-8 text-center">
          <p className="text-2xl font-semibold text-white sm:text-3xl">
            Um momento, o farmacêutico já vem até você.
          </p>
          <button
            type="button"
            onClick={() => setAguardandoHumano(false)}
            className="rounded-full bg-white/15 px-5 py-2 text-sm text-white/90 backdrop-blur-sm hover:bg-white/25"
          >
            Voltar ao atendimento por IA
          </button>
        </div>
        <p className="absolute inset-x-0 bottom-0 bg-black/70 px-4 py-2 text-center text-xs text-white/70">
          {AVISO_IA_TEXTO}
        </p>
      </div>
    );
  }

  const Layout = AVATAR_MODE === "cartoon" ? TotemCartoonLayout : TotemFullscreenLayout;

  return (
    <>
      <Layout
        estadoAvatar={estadoAvatar}
        bocaAberta={bocaAberta}
        ultimaMensagem={ultimaMensagem}
        legendaVisivel={legendaVisivel}
        erro={erro}
        produtosSugeridos={produtosSugeridos}
        loading={loading}
        precisaConsentimento={precisaConsentimento}
        confirmarCompra={confirmarCompra}
        mostrarTeclado={mostrarTeclado}
        setMostrarTeclado={setMostrarTeclado}
        input={input}
        setInput={setInput}
        enviarMensagem={enviarMensagem}
        micSuportado={micSuportado}
        gravando={gravando}
        temTextoPendente={temTextoPendente}
        tocarMic={tocarMic}
        abrirPerfilClinico={() => setPerfilAberto(true)}
        onFalarComFarmaceutico={onFalarComFarmaceutico}
      />

      {/* Perfil clínico — opcional, em modal (mesmos campos de sempre). */}
      {perfilAberto && (
        <Modal title="Perfil clínico (opcional)" onClose={() => setPerfilAberto(false)}>
          <div className="flex flex-col gap-3">
            <FieldWrapper label="Medicamentos em uso (separados por vírgula)" htmlFor="totem-medicamentos-em-uso">
              <TextInput
                id="totem-medicamentos-em-uso"
                placeholder="ex.: varfarina, losartana"
                value={medicamentosEmUso}
                onChange={(e) => setMedicamentosEmUso(e.target.value)}
              />
            </FieldWrapper>
            <FieldWrapper label="Idade" htmlFor="totem-idade">
              <TextInput
                id="totem-idade"
                type="number"
                min={0}
                max={130}
                value={idade}
                onChange={(e) => setIdade(e.target.value)}
              />
            </FieldWrapper>
            <div className="flex gap-4">
              <label className="flex items-center gap-1.5 text-sm text-slate-600">
                <input type="checkbox" checked={gestante} onChange={(e) => setGestante(e.target.checked)} />
                Gestante
              </label>
              <label className="flex items-center gap-1.5 text-sm text-slate-600">
                <input type="checkbox" checked={lactante} onChange={(e) => setLactante(e.target.checked)} />
                Lactante
              </label>
            </div>
          </div>
        </Modal>
      )}

      {/* LGPD-03: o totem nunca identifica cliente (clienteId sempre vazio),
          então isto nunca renderiza na prática — mantido por completude, a
          garantia real é o 403 do backend. */}
      {precisaConsentimento && (
        <Modal
          title="Antes de continuar"
          onClose={() => setClienteId("")}
          footer={
            <Button onClick={aceitarConsentimento} disabled={enviandoConsentimento}>
              {enviandoConsentimento ? "Registrando..." : "Estou de acordo"}
            </Button>
          }
        >
          <p className="text-sm text-slate-600">{AVISO_IA_TEXTO}</p>
        </Modal>
      )}
    </>
  );
}
