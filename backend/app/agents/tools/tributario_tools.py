import dataclasses
import uuid
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from crewai.tools import BaseTool
from imap_tools import AND, MailBox, MailMessageFlags
from nfelib.nfe.bindings.v4_0.nfe_v4_00 import Nfe
from nfelib.nfe.bindings.v4_0.proc_nfe_v4_00 import NfeProc
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from xsdata.exceptions import ParserError
from xsdata.formats.dataclass.parsers import XmlParser

from app.agents.config import AgentRole, get_agent_settings
from app.agents.db_sync import agent_session
from app.models.enums import StatusItemNfeEnum
from app.models.nota_fiscal_entrada import NotaFiscalEntrada, NotaFiscalEntradaItem

_ASSUNTOS_NFE = ("nf-e", "nfe", "nota fiscal")


class LerEmailNFesTool(BaseTool):
    name: str = "ler_emails_nfe"
    description: str = (
        "Conecta ao email corporativo via IMAP e busca emails NÃO LIDOS cujo assunto "
        "contenha 'NF-e', 'NFe' ou 'Nota Fiscal' e que tenham anexo .xml. Não recebe "
        "parâmetros. Devolve uma lista de {'email_uid', 'filename', 'xml_raw'} — um item "
        "por anexo XML encontrado (um email pode ter mais de um XML anexado)."
    )
    role: AgentRole = AgentRole.TRIBUTARIO

    def _run(self) -> list[dict[str, str]]:
        settings = get_agent_settings()
        if not (settings.nfe_email_host and settings.nfe_email_user and settings.nfe_email_password):
            raise RuntimeError(
                "NFE_EMAIL_HOST/NFE_EMAIL_USER/NFE_EMAIL_PASSWORD não configurados no "
                "ambiente — não é possível ler a caixa de entrada de NF-e."
            )

        encontrados: list[dict[str, str]] = []
        with MailBox(settings.nfe_email_host).login(settings.nfe_email_user, settings.nfe_email_password) as mailbox:
            for msg in mailbox.fetch(AND(seen=False), mark_seen=False):
                assunto = (msg.subject or "").lower()
                if not any(termo in assunto for termo in _ASSUNTOS_NFE):
                    continue
                anexos_xml = [a for a in msg.attachments if a.filename and a.filename.lower().endswith(".xml")]
                if not anexos_xml:
                    continue
                for anexo in anexos_xml:
                    encontrados.append(
                        {
                            "email_uid": msg.uid,
                            "filename": anexo.filename,
                            "xml_raw": anexo.payload.decode("utf-8", errors="replace"),
                        }
                    )
                # Marca como lido assim que os XMLs deste email foram extraídos com
                # sucesso — não espera o resto do pipeline (parsear/identificar/salvar)
                # terminar. Trade-off deliberado do Bloco 1: se executar_crew tiver que
                # dar retry (LLM-04), a segunda tentativa não vai reencontrar este email
                # como não lido — uma falha DEPOIS deste ponto (ex.: salvar_nota_entrada
                # falhando) perde esse XML da rodada atual; recuperação é manual
                # (remarcar o email como não lido). Aceitável para o piloto.
                mailbox.flag([msg.uid], MailMessageFlags.SEEN, True)
        return encontrados


def _to_decimal(valor: Any) -> Decimal:
    if valor is None or valor == "":
        return Decimal("0")
    try:
        return Decimal(str(valor))
    except InvalidOperation:
        return Decimal("0")


def _primeira_variante_nao_nula(objeto: Any) -> Any | None:
    """PIS/COFINS/ICMS no XSD da NF-e são uniões de dezenas de variantes por
    CST (ICMS00, ICMS10, ICMSST, ... — só uma vem preenchida por item). Em
    vez de listar manualmente todas as variantes possíveis, pega a primeira
    não-None — cada variante que carrega alíquota usa os mesmos nomes de
    campo (pPIS/vPIS, pCOFINS/vCOFINS, vICMSST)."""
    if objeto is None:
        return None
    for campo in dataclasses.fields(objeto):
        valor = getattr(objeto, campo.name)
        if valor is not None:
            return valor
    return None


class ParsearNFeTool(BaseTool):
    name: str = "parsear_nfe"
    description: str = (
        "Extrai os dados estruturados de um XML de NF-e (aceita tanto o processo "
        "autorizado 'nfeProc' quanto uma 'NFe' avulsa). Recebe xml_raw (string). Devolve "
        "um dicionário com chave_acesso, numero_nota, serie, cnpj_emitente, nome_emitente, "
        "cnpj_destinatario, data_emissao, valor_total e uma lista 'itens' — cada item com "
        "ncm, descricao_produto, numero_lote, data_validade, quantidade, custo_unitario, "
        "valor_total_item, v_icms_st, p_pis, v_pis, p_cofins, v_cofins."
    )
    role: AgentRole = AgentRole.TRIBUTARIO

    def _run(self, xml_raw: str) -> dict[str, Any]:
        xml_bytes = xml_raw.encode("utf-8")
        parser = XmlParser()
        try:
            inf = parser.from_bytes(xml_bytes, NfeProc).NFe.infNFe
        except ParserError:
            # Nem todo email traz o processo completo (NFe + protocolo de
            # autorização) — às vezes é só a NFe.
            inf = parser.from_bytes(xml_bytes, Nfe).infNFe

        chave_acesso = (inf.Id or "").removeprefix("NFe")

        itens: list[dict[str, Any]] = []
        for det in inf.det:
            prod = det.prod
            rastro = prod.rastro[0] if prod.rastro else None

            pis_variante = _primeira_variante_nao_nula(det.imposto.PIS)
            cofins_variante = _primeira_variante_nao_nula(det.imposto.COFINS)
            icms_variante = _primeira_variante_nao_nula(det.imposto.ICMS)

            quantidade = _to_decimal(prod.qCom).to_integral_value(rounding=ROUND_HALF_UP)

            itens.append(
                {
                    "ncm": prod.NCM,
                    "descricao_produto": prod.xProd,
                    "numero_lote": rastro.nLote if rastro else None,
                    "data_validade": date.fromisoformat(rastro.dVal) if rastro and rastro.dVal else None,
                    "quantidade": int(quantidade),
                    "custo_unitario": str(_to_decimal(prod.vUnCom)),
                    "valor_total_item": str(_to_decimal(prod.vProd)),
                    "v_icms_st": str(_to_decimal(getattr(icms_variante, "vICMSST", None))),
                    "p_pis": str(_to_decimal(getattr(pis_variante, "pPIS", None))),
                    "v_pis": str(_to_decimal(getattr(pis_variante, "vPIS", None))),
                    "p_cofins": str(_to_decimal(getattr(cofins_variante, "pCOFINS", None))),
                    "v_cofins": str(_to_decimal(getattr(cofins_variante, "vCOFINS", None))),
                }
            )

        return {
            "chave_acesso": chave_acesso,
            "numero_nota": inf.ide.nNF,
            "serie": inf.ide.serie,
            "cnpj_emitente": inf.emit.CNPJ,
            "nome_emitente": inf.emit.xNome,
            "cnpj_destinatario": inf.dest.CNPJ if inf.dest else None,
            "data_emissao": datetime.fromisoformat(inf.ide.dhEmi) if inf.ide.dhEmi else None,
            "valor_total": str(_to_decimal(inf.total.ICMSTot.vNF)),
            "itens": itens,
        }


class IdentificarProdutosTool(BaseTool):
    name: str = "identificar_produto"
    description: str = (
        "Tenta identificar, no cadastro de produtos, o item de uma NF-e — primeiro por NCM "
        "(mais confiável), e só se não achar, por nome aproximado (ILIKE). Recebe ncm "
        "(pode ser None) e descricao_produto. Devolve {'produto_id': '<uuid>', "
        "'nome_comercial': '...'} se encontrar, ou {'produto_id': None, 'nome_comercial': "
        "None} se não encontrar nenhum candidato — nesse caso o item NÃO deve ser "
        "cadastrado automaticamente, fica marcado para conferência humana."
    )
    role: AgentRole = AgentRole.TRIBUTARIO

    def _run(self, ncm: str | None, descricao_produto: str) -> dict[str, str | None]:
        with agent_session(self.role) as session:
            row = None
            if ncm:
                row = session.execute(
                    text("SELECT id, nome_comercial FROM produtos WHERE ncm = :ncm AND ativo = true LIMIT 1"),
                    {"ncm": ncm},
                ).first()
            if row is None and descricao_produto and descricao_produto.strip():
                row = session.execute(
                    text(
                        "SELECT id, nome_comercial FROM produtos "
                        "WHERE nome_comercial ILIKE :nome AND ativo = true LIMIT 1"
                    ),
                    {"nome": f"%{descricao_produto.strip()}%"},
                ).first()
            if row is None:
                return {"produto_id": None, "nome_comercial": None}
            return {"produto_id": str(row.id), "nome_comercial": row.nome_comercial}


class SalvarNotaEntradaTool(BaseTool):
    name: str = "salvar_nota_entrada"
    description: str = (
        "Grava a nota fiscal de entrada e seus itens no banco, sempre com status "
        "'aguardando_confirmacao' — NUNCA altera lotes, estoque ou movimentacoes_estoque "
        "(isso só acontece depois que um operador humano confirmar a chegada pelo painel "
        "administrativo). Recebe 'nota' (dict com chave_acesso, numero_nota, serie, "
        "cnpj_emitente, nome_emitente, cnpj_destinatario, data_emissao, valor_total, "
        "xml_raw) e 'itens' (lista de dicts no formato devolvido por parsear_nfe, cada um "
        "já com 'produto_id' preenchido a partir de uma chamada a identificar_produto — "
        "produto_id=None para itens não identificados, eles ainda assim são salvos para "
        "conferência manual). Se cnpj_destinatario não corresponder a nenhuma filial ativa "
        "cadastrada, ou se a chave_acesso já tiver sido processada antes, devolve um "
        "dicionário com 'erro' em vez de salvar de novo."
    )
    role: AgentRole = AgentRole.TRIBUTARIO

    @staticmethod
    def _resolver_filial(session, cnpj_destinatario: str | None) -> uuid.UUID | None:
        if not cnpj_destinatario:
            return None
        row = session.execute(
            text("SELECT id FROM filiais WHERE cnpj = :cnpj AND ativo = true"),
            {"cnpj": cnpj_destinatario},
        ).first()
        return row.id if row is not None else None

    @staticmethod
    def _nota_existente(session, chave_acesso: str) -> uuid.UUID | None:
        row = session.execute(
            text("SELECT id FROM notas_fiscais_entrada WHERE chave_acesso = :chave"),
            {"chave": chave_acesso},
        ).first()
        return row.id if row is not None else None

    def _run(self, nota: dict[str, Any], itens: list[dict[str, Any]]) -> dict[str, Any]:
        with agent_session(self.role) as session:
            existente_id = self._nota_existente(session, nota["chave_acesso"])
            if existente_id is not None:
                return {
                    "nota_id": str(existente_id),
                    "itens_salvos": 0,
                    "erro": None,
                    "aviso": "chave_acesso já havia sido processada anteriormente — nada foi duplicado",
                }

            filial_id = self._resolver_filial(session, nota.get("cnpj_destinatario"))
            if filial_id is None:
                return {
                    "nota_id": None,
                    "itens_salvos": 0,
                    "erro": "filial_nao_identificada",
                    "aviso": (
                        f"Nenhuma filial ativa cadastrada com CNPJ '{nota.get('cnpj_destinatario')}' "
                        "(campo dest/CNPJ da NF-e) — nota NÃO foi salva."
                    ),
                }

            data_emissao = nota["data_emissao"]
            if isinstance(data_emissao, str):
                data_emissao = datetime.fromisoformat(data_emissao)

            nota_obj = NotaFiscalEntrada(
                filial_id=filial_id,
                chave_acesso=nota["chave_acesso"],
                numero_nota=str(nota["numero_nota"]),
                serie=str(nota["serie"]),
                cnpj_emitente=nota["cnpj_emitente"],
                nome_emitente=nota["nome_emitente"],
                data_emissao=data_emissao,
                valor_total=_to_decimal(nota["valor_total"]),
                xml_raw=nota["xml_raw"],
            )
            session.add(nota_obj)
            try:
                session.flush()
            except IntegrityError:
                # Corrida real (duas chamadas processando o mesmo email em paralelo):
                # o índice único de chave_acesso ganhou de nós — devolve a linha que
                # venceu em vez de estourar 500.
                session.rollback()
                existente_id = self._nota_existente(session, nota["chave_acesso"])
                if existente_id is not None:
                    return {
                        "nota_id": str(existente_id),
                        "itens_salvos": 0,
                        "erro": None,
                        "aviso": "chave_acesso já processada (corrida concorrente)",
                    }
                raise

            for item in itens:
                produto_id = item.get("produto_id")
                data_validade = item.get("data_validade")
                if isinstance(data_validade, str) and data_validade:
                    data_validade = date.fromisoformat(data_validade)
                elif not data_validade:
                    data_validade = None

                session.add(
                    NotaFiscalEntradaItem(
                        nota_id=nota_obj.id,
                        produto_id=uuid.UUID(produto_id) if produto_id else None,
                        ncm=item.get("ncm") or "",
                        descricao_produto=item["descricao_produto"],
                        numero_lote=item.get("numero_lote"),
                        data_validade=data_validade,
                        quantidade=int(item["quantidade"]),
                        custo_unitario=_to_decimal(item["custo_unitario"]),
                        valor_total_item=_to_decimal(item["valor_total_item"]),
                        v_icms_st=_to_decimal(item.get("v_icms_st")),
                        p_pis=_to_decimal(item.get("p_pis")),
                        v_pis=_to_decimal(item.get("v_pis")),
                        p_cofins=_to_decimal(item.get("p_cofins")),
                        v_cofins=_to_decimal(item.get("v_cofins")),
                        status_produto=(
                            StatusItemNfeEnum.identificado if produto_id else StatusItemNfeEnum.nao_encontrado
                        ),
                    )
                )
            session.flush()
            return {"nota_id": str(nota_obj.id), "itens_salvos": len(itens), "erro": None, "aviso": None}
