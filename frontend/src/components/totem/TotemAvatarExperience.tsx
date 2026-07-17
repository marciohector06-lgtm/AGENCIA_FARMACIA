"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { FieldWrapper, TextInput } from "@/components/ui/Field";
import { Modal } from "@/components/ui/Modal";
import { AVISO_IA_TEXTO, useAtendimentoChat } from "@/lib/useAtendimentoChat";
import { AvatarFarmaceutica, EstadoAvatar } from "@/components/AvatarFarmaceutica";
import { CheckIcon, KeyboardIcon, MicIcon, PhoneIcon, UserIcon } from "@/components/atendimento/icons";

const DURACAO_LEGENDA_MS = 7_000;

interface TotemAvatarExperienceProps {
  filialIdFixa: string;
  onVendaConfirmada?: () => void;
}

const LABEL_ESTADO: Partial<Record<EstadoAvatar, string>> = {
  ouvindo: "Ouvindo...",
  pensando: "Pensando...",
  falando: "Falando...",
};

// Tela cheia, estilo videochamada: a foto da farmacêutica ocupa 100% da
// tela, mensagens viram legenda temporária (não histórico de chat), e o mic
// é o único controle principal. Toda a lógica (voz, LGPD, guardrails,
// confirmação de compra) vem de useAtendimentoChat — a mesma usada pelo
// painel administrativo em /atendimento; só a casca visual é outra.
export function TotemAvatarExperience({ filialIdFixa, onVendaConfirmada }: TotemAvatarExperienceProps) {
  const {
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
    micSuportado,
    gravando,
    falando,
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

  // Legenda mostra só o último turno (não o histórico inteiro) e some
  // sozinha depois de alguns segundos — mas só começa a contar depois que
  // ela termina de falar, senão a legenda podia sumir no meio da fala.
  useEffect(() => {
    if (!ultimaMensagem) return;
    setLegendaVisivel(true);
    if (falando) return;
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

  if (aguardandoHumano) {
    return (
      <div className="relative h-screen w-screen overflow-hidden bg-slate-950">
        <AvatarFarmaceutica estado="esperando" />
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

  return (
    <div className="relative h-screen w-screen overflow-hidden bg-slate-950">
      <AvatarFarmaceutica estado={estadoAvatar} />

      {/* Gradiente escuro só na faixa de baixo — dá contraste pro texto sem
          escurecer o rosto dela. */}
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-2/3 bg-gradient-to-t from-black/85 via-black/40 to-transparent" />

      {/* Cantos discretos, sempre visíveis. */}
      <button
        type="button"
        onClick={() => setPerfilAberto(true)}
        aria-label="Perfil clínico (opcional)"
        title="Perfil clínico (opcional)"
        className="absolute left-4 top-4 z-20 flex h-11 w-11 items-center justify-center rounded-full bg-black/30 text-white/80 backdrop-blur-sm hover:bg-black/45"
      >
        <UserIcon className="h-5 w-5" />
      </button>
      <button
        type="button"
        onClick={() => {
          pararFala();
          setAguardandoHumano(true);
        }}
        aria-label="Falar com farmacêutico"
        title="Falar com farmacêutico"
        className="absolute right-4 top-4 z-20 flex items-center gap-1.5 rounded-full bg-black/30 px-3.5 py-2 text-xs text-white/80 backdrop-blur-sm hover:bg-black/45"
      >
        <PhoneIcon className="h-4 w-4" />
        Falar com farmacêutico
      </button>

      {/* Nome + status + legenda + controles, tudo sobre o gradiente. Fica
          num único container em flex-col âncorado embaixo (não dois
          elementos separados com bottom-0 cada) pra não sobrepor com o
          disclaimer, que é o último item do mesmo flow. */}
      <div className="absolute inset-x-0 bottom-0 z-10 flex flex-col">
      <div className="flex flex-col items-center gap-4 px-6 pb-6 text-center">
        <div>
          <p className="text-xl font-semibold text-white sm:text-2xl">Ana — Farmacêutica</p>
          {LABEL_ESTADO[estadoAvatar] && (
            <p className="mt-1 text-sm font-medium text-white/70">{LABEL_ESTADO[estadoAvatar]}</p>
          )}
        </div>

        {/* Ondas de som — só quando ouvindo. */}
        {estadoAvatar === "ouvindo" && (
          <div className="flex h-6 items-end gap-1" aria-hidden="true">
            {[0, 1, 2, 3, 4].map((i) => (
              <span
                key={i}
                className="animate-onda-som w-1.5 origin-bottom rounded-full bg-white"
                style={{ height: "100%", animationDelay: `${i * 0.12}s` }}
              />
            ))}
          </div>
        )}

        {/* Spinner discreto — só quando pensando. */}
        {estadoAvatar === "pensando" && (
          <div
            className="h-6 w-6 animate-spin rounded-full border-2 border-white/30 border-t-white"
            aria-hidden="true"
          />
        )}

        {/* Legenda (erro tem prioridade) ou card de sugestão de produto —
            nunca os dois ao mesmo tempo: o card já é a resposta dela sobre o
            produto, não precisa repetir como legenda também. */}
        {erro ? (
          <p className="max-w-md rounded-lg bg-red-900/70 px-4 py-2 text-sm text-red-100">{erro}</p>
        ) : produtosSugeridos.length > 0 ? (
          <div className="flex w-full max-w-sm flex-col gap-2 rounded-2xl bg-white p-4 text-left shadow-xl">
            {produtosSugeridos.map((produto) => (
              <div key={produto.produto_id} className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-slate-900">{produto.nome_comercial}</p>
                  <p className="text-xs text-slate-500">
                    {produto.disponivel ? "Disponível" : "Sem estoque"} · R$ {produto.preco.toFixed(2)}
                  </p>
                </div>
                <Button
                  disabled={loading || precisaConsentimento || !produto.disponivel}
                  onClick={() => confirmarCompra(produto, 1)}
                >
                  Confirmar compra
                </Button>
              </div>
            ))}
          </div>
        ) : (
          legendaVisivel &&
          ultimaMensagem && <p className="line-clamp-3 max-w-md text-base text-white sm:text-lg">{ultimaMensagem.text}</p>
        )}

        {/* Campo de texto — escondido por padrão, só aparece tocando no
            ícone de teclado. Voz é o principal num totem touch. */}
        {mostrarTeclado && (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              enviarMensagem();
              setMostrarTeclado(false);
            }}
            className="flex w-full max-w-sm gap-2"
          >
            <TextInput
              autoFocus
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Digite sua dúvida..."
              disabled={loading || precisaConsentimento}
              className="bg-white"
            />
            <Button type="submit" disabled={loading || precisaConsentimento}>
              Enviar
            </Button>
          </form>
        )}

        <div className="flex items-center gap-6">
          <button
            type="button"
            onClick={() => setMostrarTeclado((v) => !v)}
            aria-label={mostrarTeclado ? "Esconder teclado" : "Digitar em vez de falar"}
            title={mostrarTeclado ? "Esconder teclado" : "Digitar em vez de falar"}
            className="flex h-11 w-11 items-center justify-center rounded-full bg-black/30 text-white/80 backdrop-blur-sm hover:bg-black/45"
          >
            <KeyboardIcon className="h-5 w-5" />
          </button>

          {micSuportado && (
            <button
              type="button"
              onClick={tocarMic}
              disabled={loading || precisaConsentimento}
              aria-label={
                temTextoPendente ? "Enviar" : gravando ? "Parar e enviar" : "Falar com a farmacêutica"
              }
              title={temTextoPendente ? "Enviar" : gravando ? "Parar e enviar" : "Falar com a farmacêutica"}
              className={`flex h-24 w-24 shrink-0 items-center justify-center rounded-full text-white shadow-xl transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
                gravando ? "animate-pulse bg-red-600" : temTextoPendente ? "bg-emerald-600" : "bg-white/20 backdrop-blur-sm hover:bg-white/30"
              }`}
            >
              {temTextoPendente ? <CheckIcon className="h-10 w-10" /> : <MicIcon className="h-11 w-11" />}
            </button>
          )}
        </div>
      </div>

      <p className="bg-black/70 px-4 py-1.5 text-center text-[11px] leading-tight text-white/60">
        {AVISO_IA_TEXTO}
      </p>
      </div>

      {/* Perfil clínico — opcional, agora em modal em vez de seção inline
          (a lógica/campos são os mesmos de sempre). */}
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
    </div>
  );
}
