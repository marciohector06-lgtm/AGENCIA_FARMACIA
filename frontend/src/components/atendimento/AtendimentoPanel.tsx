"use client";

import { Button } from "@/components/ui/Button";
import { FieldWrapper, TextInput } from "@/components/ui/Field";
import { Modal } from "@/components/ui/Modal";
import { AVISO_IA_TEXTO, useAtendimentoChat } from "@/lib/useAtendimentoChat";
import { AvatarFarmaceutica, EstadoAvatar } from "@/components/AvatarFarmaceutica";
import { ChatBubble } from "@/components/atendimento/ChatBubble";
import { FilialClienteSelector } from "@/components/atendimento/FilialClienteSelector";
import { MicIcon, SpeakerIcon, StopIcon } from "@/components/atendimento/icons";

interface AtendimentoPanelProps {
  // Totem: esconde seletor de filial/cliente, checkbox de auto-envio — o
  // resto (chat, voz, consentimento, disclaimer) é o mesmo hook e os mesmos
  // componentes usados em /atendimento.
  modoTotem?: boolean;
  // Obrigatório quando modoTotem=true — filial fixa configurada no deploy
  // daquele tablet, nunca escolhida na tela.
  filialIdFixa?: string;
  onVendaConfirmada?: () => void;
}

export function AtendimentoPanel({ modoTotem = false, filialIdFixa, onVendaConfirmada }: AtendimentoPanelProps) {
  const {
    filialId,
    setFilialId,
    clienteId,
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
    autoEnvio,
    setAutoEnvio,
    micSuportado,
    gravando,
    falando,
    alternarGravacao,
    pararFala,
    enviarMensagem,
    confirmarCompra,
  } = useAtendimentoChat({ filialIdFixa, onVendaConfirmada });

  const tamanhoMic = modoTotem ? "h-24 w-24" : "h-14 w-14";
  const tamanhoIconeMic = modoTotem ? "h-11 w-11" : "h-6 w-6";

  // Prioridade pedida: ouvindo > pensando > falando > esperando — ex.: se o
  // cliente começa a falar bem no instante em que a resposta anterior ainda
  // está sendo lida, "ouvindo" vence visualmente.
  const estadoAvatar: EstadoAvatar = gravando ? "ouvindo" : loading ? "pensando" : falando ? "falando" : "esperando";

  return (
    <div className="flex h-full flex-1 flex-col gap-4">
      {modoTotem && <AvatarFarmaceutica estado={estadoAvatar} />}

      {!modoTotem && (
        <FilialClienteSelector
          filialId={filialId}
          setFilialId={setFilialId}
          clienteId={clienteId}
          setClienteId={setClienteId}
          filialDisabled={mensagens.length > 0}
        />
      )}

      <div className="rounded-xl border border-slate-200 bg-white shadow-lg">
        <button
          type="button"
          onClick={() => setPerfilAberto((v) => !v)}
          className={`flex w-full items-center justify-between px-4 py-2 font-medium text-slate-700 ${
            modoTotem ? "text-lg py-3" : "text-sm"
          }`}
        >
          Perfil clínico (opcional — preencha o que souber)
          <span className="text-slate-500">{perfilAberto ? "▲" : "▼"}</span>
        </button>
        {perfilAberto && (
          <div className="grid grid-cols-2 gap-3 border-t border-slate-200 px-4 py-3 sm:grid-cols-4">
            <div className="col-span-2 sm:col-span-2">
              <FieldWrapper label="Medicamentos em uso (separados por vírgula)" htmlFor="medicamentos-em-uso">
                <TextInput
                  id="medicamentos-em-uso"
                  placeholder="ex.: varfarina, losartana"
                  value={medicamentosEmUso}
                  onChange={(e) => setMedicamentosEmUso(e.target.value)}
                />
              </FieldWrapper>
            </div>
            <FieldWrapper label="Idade" htmlFor="idade-cliente">
              <TextInput
                id="idade-cliente"
                type="number"
                min={0}
                max={130}
                value={idade}
                onChange={(e) => setIdade(e.target.value)}
              />
            </FieldWrapper>
            <div className="flex items-end gap-4 pb-2">
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
        )}
      </div>

      <div
        className={`flex flex-1 flex-col overflow-y-auto rounded-xl border border-slate-200 bg-white shadow-lg ${
          modoTotem ? "p-8" : "p-5"
        }`}
      >
        {mensagens.length === 0 && (
          <div
            className={`flex flex-1 items-center justify-center text-center text-slate-500 ${
              modoTotem ? "text-2xl" : "text-sm"
            }`}
          >
            Descreva um sintoma ou peça um produto para começar a conversa.
          </div>
        )}
        <div className="flex flex-col gap-4">
          {mensagens.map((msg) => (
            <ChatBubble key={msg.id} msg={msg} onConfirmar={confirmarCompra} disabled={loading || precisaConsentimento} />
          ))}
          {loading && (
            <div className="max-w-md self-start rounded-lg bg-slate-100 px-4 py-2 text-sm text-slate-400">
              O Avatar está pensando...
            </div>
          )}
        </div>
      </div>

      {erro && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-700">{erro}</div>
      )}

      {/* Banner de "Parar leitura" — visibilidade máxima de propósito (totem:
          o cliente não pode esperar o áudio terminar pra fazer a próxima
          pergunta). Cor deliberadamente fora da paleta branco/vermelho do
          resto da interface, pra ficar inconfundível. */}
      {falando && (
        <div className="flex items-center justify-between gap-3 rounded-xl border-2 border-slate-900 bg-slate-900 px-4 py-2.5 text-white shadow-lg">
          <span className="flex items-center gap-2 text-sm font-medium">
            <SpeakerIcon className="h-5 w-5 animate-pulse" />
            O Avatar está falando...
          </span>
          <button
            type="button"
            onClick={pararFala}
            aria-label="Parar leitura em voz alta"
            className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-white text-slate-900 shadow-md transition-transform hover:scale-105"
          >
            <StopIcon className="h-6 w-6" />
          </button>
        </div>
      )}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          enviarMensagem();
        }}
        className="flex gap-2"
      >
        <TextInput
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ex: estou com dor de cabeça e febre, o que vocês têm?"
          disabled={loading || precisaConsentimento}
          className={modoTotem ? "py-4 text-lg" : undefined}
        />
        {/* Fallback gracioso: se o navegador não suporta SpeechRecognition
            (ex.: Firefox), o botão nem aparece — só o campo de texto normal. */}
        {micSuportado && (
          <button
            type="button"
            onClick={alternarGravacao}
            disabled={loading || precisaConsentimento}
            aria-label={gravando ? "Parar gravação" : "Falar com o Avatar"}
            title={gravando ? "Parar gravação" : "Falar com o Avatar"}
            className={`flex ${tamanhoMic} shrink-0 items-center justify-center rounded-full text-white shadow-sm transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
              gravando ? "animate-pulse bg-red-600" : "bg-slate-700 hover:bg-slate-800"
            }`}
          >
            <MicIcon className={tamanhoIconeMic} />
          </button>
        )}
        <Button
          type="submit"
          disabled={loading || precisaConsentimento}
          className={modoTotem ? "px-6 text-lg" : undefined}
        >
          Enviar
        </Button>
      </form>

      {/* No totem o auto-envio fica sempre desligado e sem controle na tela
          — nunca dispara sem um toque explícito em "Enviar" (ver comentário
          no hook). */}
      {micSuportado && !modoTotem && (
        <label className="-mt-2 flex items-center gap-1.5 self-start text-xs text-slate-500">
          <input type="checkbox" checked={autoEnvio} onChange={(e) => setAutoEnvio(e.target.checked)} />
          Enviar automaticamente 1.5s após parar de falar
        </label>
      )}

      {/* LGPD-03: primeira interação com um cliente identificado que ainda
          não consentiu — bloqueia o chat até aceitar (a garantia real é o
          403 do backend; isto é só a UX). O totem nunca identifica cliente,
          então nunca cai aqui. */}
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
    </div>
  );
}
