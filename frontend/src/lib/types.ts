export type Tarja = "isento" | "amarela" | "vermelha" | "preta";

export type FormaFarmaceutica =
  | "comprimido"
  | "capsula"
  | "xarope"
  | "pomada"
  | "gel"
  | "creme"
  | "solucao"
  | "suspensao"
  | "injetavel"
  | "spray"
  | "adesivo"
  | "po"
  | "supositorio"
  | "colirio";

export type ViaAdministracao =
  | "oral"
  | "topica"
  | "injetavel"
  | "retal"
  | "oftalmica"
  | "nasal"
  | "inalatoria"
  | "sublingual"
  | "otologica"
  | "vaginal";

export type UnidadeConcentracao = "mg" | "g" | "ml" | "mcg" | "ui" | "pct";
export type StatusLote = "disponivel" | "reservado" | "vencido" | "bloqueado" | "devolvido";
export type StatusAprovacao = "proposto" | "aprovado" | "rejeitado" | "auto_aprovado";
export type TipoDecisao =
  | "sugestao_similar"
  | "ajuste_preco"
  | "alerta_estoque"
  | "aprovacao_compra"
  | "bloqueio_venda"
  | "recomendacao_giro"
  | "resolucao_conflito"
  | "alteracao_tarja";
export type TipoMovimentacao = "entrada" | "venda" | "ajuste" | "sincronizacao_erp";

// FASE 0: presente em produtos/lotes/estoque/filiais. origem='manual' é
// editável pela API; qualquer outra origem (ex.: 'mock') é gerenciada por um
// ERP e somente leitura por aqui.
export interface OrigemErp {
  id_externo: string | null;
  origem: string;
  sincronizado_em: string | null;
}

export interface Filial extends OrigemErp {
  id: string;
  nome: string;
  cnpj: string | null;
  endereco: string | null;
  cidade: string | null;
  uf: string | null;
  ativo: boolean;
}

export interface Fabricante {
  id: string;
  nome: string;
  cnpj: string | null;
  registro_anvisa: string | null;
  pais_origem: string;
  ativo: boolean;
}

export interface Cliente {
  id: string;
  nome: string;
  cpf: string | null;
  data_nascimento: string | null;
  telefone: string | null;
  email: string | null;
}

export interface PrincipioAtivo {
  id: string;
  nome: string;
  nome_dcb: string | null;
  classe_terapeutica: string;
  mecanismo_acao: string | null;
  contraindicacoes_gerais: string | null;
}

export interface Produto extends OrigemErp {
  id: string;
  principio_ativo_id: string | null;
  fabricante_id: string;
  nome_comercial: string;
  codigo_barras: string | null;
  registro_anvisa: string | null;
  forma_farmaceutica: FormaFarmaceutica;
  via_administracao: ViaAdministracao;
  concentracao_valor: string;
  concentracao_unidade: UnidadeConcentracao;
  quantidade_embalagem: number;
  tarja: Tarja;
  tipo_liberacao: string;
  preco_tabela: string;
  custo_medio: string | null;
  ativo: boolean;
}

export interface Lote extends OrigemErp {
  id: string;
  produto_id: string;
  numero_lote: string;
  data_fabricacao: string;
  data_validade: string;
  quantidade_recebida: number;
  custo_unitario: string;
  status: StatusLote;
}

export interface Estoque extends OrigemErp {
  id: string;
  filial_id: string;
  lote_id: string;
  quantidade_atual: number;
  quantidade_reservada: number;
  localizacao_gondola: string | null;
}

export interface MovimentacaoEstoque {
  id: string;
  estoque_id: string;
  tipo: TipoMovimentacao;
  quantidade_delta: number;
  quantidade_resultante: number;
  motivo: string;
  venda_id: string | null;
  criado_em: string;
}

export interface LogAuditoria {
  id: string;
  agente_id: string;
  agente_nome: string;
  agente_tipo: string;
  tipo_decisao: TipoDecisao;
  entidade_afetada: string;
  entidade_id: string | null;
  principio_ativo_id: string | null;
  decisao_tomada: string;
  dados_base: Record<string, unknown>;
  justificativa: string | null;
  confianca: number | null;
  sessao_id: string | null;
  criado_em: string;
}

export interface PrecificacaoHistorico {
  id: string;
  produto_id: string;
  produto_nome: string;
  lote_id: string | null;
  preco_anterior: string;
  preco_novo: string;
  margem_resultante: string | null;
  motivo: string;
  proposto_por_agente_id: string;
  proposto_por_nome: string;
  aprovado_por_agente_id: string | null;
  aprovado_por_nome: string | null;
  status_aprovacao: StatusAprovacao;
  aprovado_em: string | null;
  created_at: string;
}

export interface DecisaoPrecificacaoResumo {
  precificacao_id: string;
  aprovado: boolean;
  margem_resultante: number | null;
  justificativa: string;
}

export interface AnaliseEstoqueResponse {
  propostas_geradas: number;
  aprovadas: number;
  rejeitadas: number;
  decisoes: DecisaoPrecificacaoResumo[];
  resumo: string;
  log_auditoria_ids: string[];
}

export interface ProdutoSugerido {
  produto_id: string;
  nome_comercial: string;
  disponivel: boolean;
  preco: number;
  motivo_sugestao: string;
}

export interface ChatAtendimentoResponse {
  sessao_id: string;
  resposta: string;
  produtos_sugeridos: ProdutoSugerido[];
  venda_id: string | null;
  log_auditoria_id: string | null;
  // CLIN-06: texto fixo, gerado deterministicamente pelo backend (nunca pelo LLM).
  disclaimer: string;
}
