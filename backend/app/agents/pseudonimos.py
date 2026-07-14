import uuid

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.integrations.sync import _backend_session

# LGPD-04: única leitura/escrita de pseudonimos_titular no sistema — sempre
# via app_backend (_backend_session), nunca por uma role de agente (RLS/GRANT
# da migration 0002_lgpd_04... só concede acesso a app_backend).


def pseudonimo_id_for_cliente(cliente_id: uuid.UUID) -> uuid.UUID:
    """Get-or-create do pseudônimo ATIVO de um titular. Reaproveitado entre
    sessões/mensagens enquanto não for revogado; depois de revogado, a
    próxima chamada cria um pseudônimo novo (o titular "recomeça" a
    pseudonimizar seu histórico clínico a partir dali)."""
    session = _backend_session()
    try:
        row = session.execute(
            text("SELECT pseudonimo_id FROM pseudonimos_titular WHERE cliente_id = :cid AND revogado_em IS NULL"),
            {"cid": str(cliente_id)},
        ).first()
        if row is not None:
            return row.pseudonimo_id

        try:
            novo_id = session.execute(
                text("INSERT INTO pseudonimos_titular (cliente_id) VALUES (:cid) RETURNING pseudonimo_id"),
                {"cid": str(cliente_id)},
            ).scalar_one()
            session.commit()
            return novo_id
        except IntegrityError:
            # Corrida: outra chamada concorrente já criou o pseudônimo ativo
            # deste cliente (garantido pelo índice único parcial da migration
            # 0002 — idx_pseudonimos_titular_cliente_ativo).
            session.rollback()
            row = session.execute(
                text("SELECT pseudonimo_id FROM pseudonimos_titular WHERE cliente_id = :cid AND revogado_em IS NULL"),
                {"cid": str(cliente_id)},
            ).first()
            if row is None:
                raise
            return row.pseudonimo_id
    finally:
        session.close()


def revogar_pseudonimo_titular(cliente_id: uuid.UUID) -> int:
    """LGPD-04 (DELETE /clientes/{id}/dados-clinicos): marca o pseudônimo
    ativo do titular como revogado E desliga cliente_id — não basta carimbar
    revogado_em, isso sozinho deixaria a ligação em claro na mesma linha. As
    linhas de logs_auditoria/sessoes_chat_mensagens que apontam pra esse
    pseudonimo_id continuam existindo (append-only intocado), só deixam de
    ser resolvíveis a um titular.

    Devolve quantas linhas foram revogadas (0 = não havia pseudônimo ativo
    pra esse cliente_id).
    """
    session = _backend_session()
    try:
        resultado = session.execute(
            text(
                "UPDATE pseudonimos_titular SET revogado_em = now(), cliente_id = NULL "
                "WHERE cliente_id = :cid AND revogado_em IS NULL"
            ),
            {"cid": str(cliente_id)},
        )
        session.commit()
        return resultado.rowcount
    finally:
        session.close()
