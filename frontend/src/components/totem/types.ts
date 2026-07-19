import { ChatMessage } from "@/lib/useAtendimentoChat";
import { EstadoAvatar } from "@/components/AvatarFarmaceutica";
import { ProdutoSugerido } from "@/lib/types";

// Contrato comum entre TotemFullscreenLayout e TotemCartoonLayout — os dois
// recebem exatamente os mesmos dados/handlers (tudo já derivado por
// TotemAvatarExperience a partir de useAtendimentoChat), só decidem
// diferente como desenhar isso na tela. Nenhum dos dois chama o hook
// diretamente.
export interface TotemLayoutProps {
  estadoAvatar: EstadoAvatar;
  // Lip-sync real via ElevenLabs (ver useSintese em src/lib/useVoz.ts) —
  // repassado direto pra AvatarFarmaceutica, ver bocaAbertaExterna lá.
  bocaAberta: boolean | null;
  ultimaMensagem: ChatMessage | undefined;
  legendaVisivel: boolean;
  erro: string | null;
  produtosSugeridos: ProdutoSugerido[];
  loading: boolean;
  precisaConsentimento: boolean;
  confirmarCompra: (produto: ProdutoSugerido, quantidade: number) => void;
  mostrarTeclado: boolean;
  setMostrarTeclado: (updater: boolean | ((v: boolean) => boolean)) => void;
  input: string;
  setInput: (v: string) => void;
  enviarMensagem: (textoFalado?: string) => void;
  micSuportado: boolean;
  gravando: boolean;
  temTextoPendente: boolean;
  tocarMic: () => void;
  abrirPerfilClinico: () => void;
  onFalarComFarmaceutico: () => void;
}
