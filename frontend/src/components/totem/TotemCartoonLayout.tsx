"use client";

import { Button } from "@/components/ui/Button";
import { TextInput } from "@/components/ui/Field";
import { AvatarFarmaceutica, EstadoAvatar } from "@/components/AvatarFarmaceutica";
import { CheckIcon, KeyboardIcon, MicIcon, PhoneIcon, UserIcon } from "@/components/atendimento/icons";
import { AVISO_IA_TEXTO } from "@/lib/useAtendimentoChat";
import { TotemLayoutProps } from "./types";

const LABEL_ESTADO: Partial<Record<EstadoAvatar, string>> = {
  ouvindo: "Ouvindo...",
  pensando: "A Ana está analisando... isso pode levar alguns segundos",
  falando: "Falando...",
};

// Retrato empilhado: personagem ilustrado (fundo limpo, object-contain — não
// corta o corpo) ocupa a faixa de cima; conversa/cards ficam embaixo, em
// fundo claro. Pensado pro tablet em pé no balcão (ver avatarConfig.ts —
// modo "cartoon"). Mesmos dados/handlers do modo fullscreen, só o desenho
// muda — nenhuma lógica aqui.
export function TotemCartoonLayout({
  estadoAvatar,
  bocaAberta,
  ultimaMensagem,
  legendaVisivel,
  erro,
  produtosSugeridos,
  loading,
  precisaConsentimento,
  confirmarCompra,
  mostrarTeclado,
  setMostrarTeclado,
  input,
  setInput,
  enviarMensagem,
  micSuportado,
  gravando,
  temTextoPendente,
  tocarMic,
  abrirPerfilClinico,
  onFalarComFarmaceutico,
}: TotemLayoutProps) {
  return (
    <div className="relative flex h-screen w-screen flex-col overflow-hidden bg-white">
      {/* Cantos discretos — ícone escuro sobre fundo claro (inverso do modo
          fullscreen, que usa branco sobre foto escura). */}
      <button
        type="button"
        onClick={abrirPerfilClinico}
        aria-label="Perfil clínico (opcional)"
        title="Perfil clínico (opcional)"
        className="absolute left-4 top-4 z-20 flex h-11 w-11 items-center justify-center rounded-full bg-slate-100 text-slate-600 hover:bg-slate-200"
      >
        <UserIcon className="h-5 w-5" />
      </button>
      <button
        type="button"
        onClick={onFalarComFarmaceutico}
        aria-label="Falar com farmacêutico"
        title="Falar com farmacêutico"
        className="absolute right-4 top-4 z-20 flex items-center gap-1.5 rounded-full bg-slate-100 px-3.5 py-2 text-xs text-slate-600 hover:bg-slate-200"
      >
        <PhoneIcon className="h-4 w-4" />
        Falar com farmacêutico
      </button>

      {/* Personagem — ~45% da altura, object-contain pra mostrar o corpo
          inteiro sem cortar (a imagem já vem com fundo branco/limpo, então
          funde com o bg-white do container sem precisar de máscara). */}
      <div className="relative h-[45%] w-full shrink-0 pt-14">
        <AvatarFarmaceutica estado={estadoAvatar} objectFit="contain" bocaAbertaExterna={bocaAberta} />
      </div>

      {/* Conversa/cards — faixa de baixo, fundo claro. */}
      <div className="flex flex-1 flex-col items-center gap-4 overflow-y-auto px-6 pb-4 pt-2 text-center">
        <div>
          <p className="text-xl font-semibold text-slate-900 sm:text-2xl">Ana — Farmacêutica</p>
          {LABEL_ESTADO[estadoAvatar] && (
            <p className="mt-1 text-sm font-medium text-slate-500">{LABEL_ESTADO[estadoAvatar]}</p>
          )}
        </div>

        {/* Ondas de som — só quando ouvindo. */}
        {estadoAvatar === "ouvindo" && (
          <div className="flex h-6 items-end gap-1" aria-hidden="true">
            {[0, 1, 2, 3, 4].map((i) => (
              <span
                key={i}
                className="animate-onda-som w-1.5 origin-bottom rounded-full bg-slate-700"
                style={{ height: "100%", animationDelay: `${i * 0.12}s` }}
              />
            ))}
          </div>
        )}

        {/* Spinner discreto — só quando pensando. */}
        {estadoAvatar === "pensando" && (
          <div
            className="h-6 w-6 animate-spin rounded-full border-2 border-slate-200 border-t-slate-600"
            aria-hidden="true"
          />
        )}

        {/* Legenda (erro tem prioridade) ou card de sugestão de produto. */}
        {erro ? (
          <p className="max-w-md rounded-lg bg-red-50 px-4 py-2 text-sm text-red-700">{erro}</p>
        ) : produtosSugeridos.length > 0 ? (
          <div className="flex w-full max-w-sm flex-col gap-2 rounded-2xl border border-slate-200 bg-white p-4 text-left shadow-md">
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
          ultimaMensagem && (
            <p className="line-clamp-3 max-w-md text-base text-slate-800 sm:text-lg">{ultimaMensagem.text}</p>
          )
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
            />
            <Button type="submit" disabled={loading || precisaConsentimento}>
              Enviar
            </Button>
          </form>
        )}

        <div className="mt-auto flex items-center gap-6 pt-2">
          <button
            type="button"
            onClick={() => setMostrarTeclado((v) => !v)}
            aria-label={mostrarTeclado ? "Esconder teclado" : "Digitar em vez de falar"}
            title={mostrarTeclado ? "Esconder teclado" : "Digitar em vez de falar"}
            className="flex h-11 w-11 items-center justify-center rounded-full bg-slate-100 text-slate-600 hover:bg-slate-200"
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
              className={`flex h-20 w-20 shrink-0 items-center justify-center rounded-full text-white shadow-lg transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
                gravando
                  ? "animate-pulse bg-red-600"
                  : temTextoPendente
                    ? "bg-emerald-600"
                    : "bg-slate-800 hover:bg-slate-900"
              }`}
            >
              {temTextoPendente ? <CheckIcon className="h-9 w-9" /> : <MicIcon className="h-9 w-9" />}
            </button>
          )}
        </div>
      </div>

      <p className="bg-slate-50 px-4 py-1.5 text-center text-[11px] leading-tight text-slate-500">
        {AVISO_IA_TEXTO}
      </p>
    </div>
  );
}
