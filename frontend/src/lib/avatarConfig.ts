export type AvatarMode = "fullscreen" | "cartoon";

// Modo visual do avatar do totem — trocar aqui é a única mudança de código
// necessária pra alternar entre os dois formatos. Os arquivos em
// public/avatar/ (esperando.png, ouvindo.png, pensando.png, boca_fechada.png,
// boca_aberta.png) têm os mesmos nomes nos dois modos; só o conteúdo/estilo
// da imagem precisa combinar com o modo escolhido:
//   - "fullscreen": foto realista, rosto próximo, preenche a tela toda.
//   - "cartoon": personagem ilustrado, fundo limpo/branco, corpo visível —
//     ver TotemCartoonLayout.tsx (layout empilhado: personagem em cima,
//     conversa embaixo).
export const AVATAR_MODE: AvatarMode = "cartoon";
