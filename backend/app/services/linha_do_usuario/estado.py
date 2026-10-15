"""SPEC-131-0-B2 · L1 — a linha do usuário NO BANCO: quem é o dono, em que estado está, e o evento de conexão.

Contrato com as outras fatias (SPEC §5):

    linha_da_instancia(db, instance_name) -> {integration_id, company_id, owner_user_id, jid, lid, ...} | None
    linha_do_dono(db, company_id, user_id, *, incluir_inativa=False) -> dict | None
    registrar_conexao(db, integration, evento)     o webhook (L2) e o pareamento chamam ao CONECTAR
    registrar_desconexao(db, integration, motivo)  o webhook (L2) e o Desconectar chamam ao CAIR

A CHAVE — `LINHA_DO_USUARIO_LIGADA` (o ponto ÚNICO é `ligada_para(user_id)`; todo chamador passa o DONO/a pessoa):

    ausente / vazia / "0" / lixo             DESLIGADA para todos (falha fechada): o bloco some, nada se pareia (nem o
                                             Evolution é chamado), o webhook só conta e cala, nenhum aviso sai
    "1" / "true" / "on" / "sim" ...          LIGADA para TODAS as pessoas de todas as corretoras (como antes)
    "<uuid>,<uuid>"                          LIGADA SÓ para esses user_id (vírgula, ponto e vírgula ou espaço; maiúsculas
                                             e espaços normalizados) — o 1º teste de uma pessoa pela TELA DE VERDADE
    ⛔ um item que não é uuid derruba a LISTA INTEIRA (ninguém): um erro de digitação nunca liga gente por engano.

🔴 Toda consulta filtra `company_id` (quando a pergunta é de uma corretora), `purpose='linha_do_usuario'` e o DONO no
código — o backend usa service role e RLS sem policy não protege nada contra erro de filtro (CLAUDE.md §7). E o
resultado é conferido de novo em Python (`_mesma`): um dublê ou um filtro esquecido não vira vazamento.
⛔ Telefone só mascarado fora do banco; o token da instância nunca sai daqui pelas funções públicas.
"""
from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

PURPOSE = "linha_do_usuario"
PROVEDOR = "evolution-go"
ESTADOS = ("nao_conectada", "aguardando_qr", "conectada", "desconectada", "limite", "desligada")

#: 💭 até a M3 (memória/CPU por instância no KVM2) ser medida — a SPEC §2.1 manda trocar pelo número medido.
MAX_LINHAS_PADRAO = 20

FRASE_LIMITE = ("Estamos no limite de conexões de WhatsApp neste momento. Tente de novo mais tarde — "
                "a equipe do AutoBrokers já sabe.")
FRASE_DESLIGADA = "Conectar o seu WhatsApp ainda não está disponível."

#: a pessoa ESCOLHEU sair (o botão) → a tela mostra "não conectado", não a faixa de "seu WhatsApp desconectou".
MOTIVOS_DA_PESSOA = frozenset({"desconectada_pelo_usuario", "cancelada_pelo_usuario"})
#: depois destes a sessão não volta sozinha: a linha deixa de ser ativa (sai do teto e do webhook).
MOTIVOS_DEFINITIVOS = MOTIVOS_DA_PESSOA | frozenset({
    "re_pair_required", "loggedout", "logged_out", "removida_do_aparelho", "numero_ja_conectado",
})

_CAMPOS = ("id, company_id, owner_user_id, provider, purpose, instance_id, identifier, is_active, channel_status, "
           "paired_phone_e164, paired_jid, linha_jid, linha_lid, linha_conectada_em, linha_desconectada_em, "
           "linha_motivo, descartadas_total, last_seen_at, created_at, token")
_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_MOTIVO = re.compile(r"[^a-z0-9_]+")
_LIGADO = frozenset({"1", "true", "sim", "on", "yes", "ligado", "ligada"})
_SEPARADOR = re.compile(r"[\s,;]+")
CHAVE_LIGADA = "LINHA_DO_USUARIO_LIGADA"


class Recusa(ValueError):
    """Um pedido que não se faz (a frase vai para a pessoa, nunca dado de outra)."""


# ---------------------------------------------------------------------------------------------------------------------
# as chaves
# ---------------------------------------------------------------------------------------------------------------------
def _quem_esta_ligado() -> Optional[frozenset]:
    """None = TODOS (um valor de `_LIGADO`) · frozenset = SÓ esses user_id (vazio = ninguém). Ver o cabeçalho."""
    bruto = str(os.getenv(CHAVE_LIGADA) or "").strip().lower()
    if bruto in _LIGADO:
        return None
    itens = [x for x in _SEPARADOR.split(bruto) if x]
    if not itens or not all(_UUID.match(x) for x in itens):
        return frozenset()          # ausente, "0", "abc", ou um item torto no meio → ninguém
    return frozenset(itens)


def ligada_para(user_id: Any) -> bool:
    """A linha está ligada para ESTA pessoa? O ponto ÚNICO da chave — tela (estado/conectar/qr), webhook (o DONO da
    integração), envio, boas-vindas e avisos passam por aqui. Pessoa sem id válido → False."""
    lista = _quem_esta_ligado()
    if lista is None:
        return True
    return str(user_id or "").strip().lower() in lista


def ligada() -> bool:
    """Existe ALGUÉM com a linha ligada? (todos, ou uma lista não vazia). Para decidir por pessoa: `ligada_para`."""
    lista = _quem_esta_ligado()
    return lista is None or bool(lista)


def max_linhas() -> int:
    """`LINHA_DO_USUARIO_MAX_LINHAS` — o teto de linhas conectadas NO SERVIDOR. Valor inválido → o padrão."""
    bruto = str(os.getenv("LINHA_DO_USUARIO_MAX_LINHAS") or "").strip()
    try:
        valor = int(bruto)
    except ValueError:
        return MAX_LINHAS_PADRAO
    return valor if valor >= 0 else MAX_LINHAS_PADRAO


# ---------------------------------------------------------------------------------------------------------------------
# miúdos
# ---------------------------------------------------------------------------------------------------------------------
def _t(db: Any, tabela: str) -> Any:
    cliente = db if hasattr(db, "table") else getattr(db, "client", db)
    return cliente.table(tabela)


def _dados(r: Any) -> List[Dict[str, Any]]:
    return [x for x in list(getattr(r, "data", None) or []) if isinstance(x, dict)]


def _uuid(v: Any, oque: str = "id") -> str:
    s = str(v or "").strip().lower()
    if not _UUID.match(s):
        raise Recusa(f"{oque} inválido")
    return s


def _mesma(a: Any, b: str) -> bool:
    return str(a or "").strip().lower() == b


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


def _e_linha(row: Dict[str, Any]) -> bool:
    return str(row.get("purpose") or "") == PURPOSE and str(row.get("provider") or PROVEDOR) == PROVEDOR


def _publica(row: Dict[str, Any]) -> Dict[str, Any]:
    """A linha na forma do contrato — SEM token. O número vai cru só para o backend (a API mascara)."""
    return {
        "integration_id": row.get("id"),
        "company_id": row.get("company_id"),
        "owner_user_id": row.get("owner_user_id"),
        "instance_name": row.get("instance_id") or row.get("identifier"),
        "jid": row.get("linha_jid") or row.get("paired_jid"),
        "lid": row.get("linha_lid"),
        "numero_e164": row.get("paired_phone_e164"),
        "ativa": row.get("is_active") is True,
        "channel_status": row.get("channel_status"),
        "conectada_em": row.get("linha_conectada_em"),
        "desconectada_em": row.get("linha_desconectada_em"),
        "motivo": row.get("linha_motivo"),
        "descartadas_total": int(row.get("descartadas_total") or 0),
    }


# ---------------------------------------------------------------------------------------------------------------------
# leituras
# ---------------------------------------------------------------------------------------------------------------------
def _linhas_do_dono(db: Any, cid: str, uid: str) -> List[Dict[str, Any]]:
    linhas = _dados(_t(db, "integrations").select(_CAMPOS)
                    .eq("company_id", cid).eq("provider", PROVEDOR).eq("purpose", PURPOSE)
                    .eq("owner_user_id", uid).order("created_at", desc=True).limit(10).execute())
    # a conferência de novo, em Python: um filtro esquecido não vira a linha de outra pessoa
    return [x for x in linhas if _e_linha(x) and _mesma(x.get("company_id"), cid) and _mesma(x.get("owner_user_id"), uid)]


def linha_crua_do_dono(db: Any, company_id: Any, user_id: Any, *, incluir_inativa: bool = False
                       ) -> Optional[Dict[str, Any]]:
    """A linha do dono COMO ESTÁ NO BANCO (com o token cifrado) — só para o pareamento falar com o provedor.
    A ativa vence; sem ativa, a mais recente (se `incluir_inativa`)."""
    cid, uid = _uuid(company_id, "company_id"), _uuid(user_id, "user_id")
    linhas = _linhas_do_dono(db, cid, uid)
    ativa = next((x for x in linhas if x.get("is_active") is True), None)
    if ativa or not incluir_inativa:
        return ativa
    return linhas[0] if linhas else None


def linha_do_dono(db: Any, company_id: Any, user_id: Any, *, incluir_inativa: bool = False) -> Optional[Dict[str, Any]]:
    """A linha desta pessoa NESTA corretora (forma pública, sem token) — ou None."""
    row = linha_crua_do_dono(db, company_id, user_id, incluir_inativa=incluir_inativa)
    return _publica(row) if row else None


def linha_da_instancia(db: Any, instance_name: Any) -> Optional[Dict[str, Any]]:
    """A linha ATIVA desta instância — ou None (instância de outro purpose, inativa ou sem dono: o webhook cala)."""
    nome = str(instance_name or "").strip()
    if not nome:
        return None
    linhas = _dados(_t(db, "integrations").select(_CAMPOS)
                    .eq("instance_id", nome).eq("provider", PROVEDOR).eq("purpose", PURPOSE)
                    .eq("is_active", True).limit(2).execute())
    linhas = [x for x in linhas if _e_linha(x) and str(x.get("instance_id") or "") == nome
              and x.get("is_active") is True and x.get("owner_user_id") and x.get("company_id")]
    if len(linhas) != 1:
        # nenhuma, ou DUAS linhas ativas com o mesmo nome (o banco não deixa; se deixasse, na dúvida ninguém)
        return None
    return _publica(linhas[0])


def contar_linhas_ativas(db: Any, *, exceto_dono: Optional[str] = None) -> int:
    """Quantas linhas estão ATIVAS no servidor (todas as corretoras — o teto é do servidor, não da corretora).
    Só a contagem sai daqui. A linha do próprio dono não conta contra ele (reconectar não ocupa vaga nova)."""
    linhas = _dados(_t(db, "integrations").select("id, owner_user_id, purpose, provider, is_active")
                    .eq("provider", PROVEDOR).eq("purpose", PURPOSE).eq("is_active", True).execute())
    dono = str(exceto_dono or "").strip().lower()
    return sum(1 for x in linhas if _e_linha(x) and x.get("is_active") is True
               and not (dono and _mesma(x.get("owner_user_id"), dono)))


def teto_cheio(db: Any, user_id: Any) -> bool:
    return contar_linhas_ativas(db, exceto_dono=str(user_id or "")) >= max_linhas()


def membro_ativo(db: Any, company_id: Any, user_id: Any) -> bool:
    cid, uid = _uuid(company_id, "company_id"), _uuid(user_id, "user_id")
    linhas = _dados(_t(db, "company_members").select("company_id, user_id, status")
                    .eq("company_id", cid).eq("user_id", uid).limit(1).execute())
    return any(_mesma(x.get("company_id"), cid) and _mesma(x.get("user_id"), uid)
               and str(x.get("status") or "active") == "active" for x in linhas)


def ativa_em_outra_corretora(db: Any, company_id: Any, user_id: Any) -> bool:
    """A MESMA pessoa já tem linha ativa noutra corretora? (D-1310B2-02: a linha mora onde foi pareada.)
    Só o sim/não sai daqui — nenhum dado da outra corretora."""
    cid, uid = _uuid(company_id, "company_id"), _uuid(user_id, "user_id")
    linhas = _dados(_t(db, "integrations").select("company_id, owner_user_id, purpose, provider, is_active")
                    .eq("provider", PROVEDOR).eq("purpose", PURPOSE).eq("owner_user_id", uid)
                    .eq("is_active", True).execute())
    return any(_e_linha(x) and _mesma(x.get("owner_user_id"), uid) and x.get("is_active") is True
               and not _mesma(x.get("company_id"), cid) for x in linhas)


# ---------------------------------------------------------------------------------------------------------------------
# o estado que a tela mostra — PURO (as leituras de fora entram como argumentos)
# ---------------------------------------------------------------------------------------------------------------------
def _resposta(estado: str, *, numero: Any = None, desde: Any = None, motivo: Any = None) -> Dict[str, Any]:
    from app.services.whatsapp.numero_pareado import mascarar

    return {"estado": estado, "numero_mascarado": mascarar(numero) if numero else None,
            "desde": desde or None, "motivo": motivo or None}


def calcular_estado(linha: Optional[Dict[str, Any]], *, esta_ligada: bool, sem_vaga: bool,
                    tentativa_pendente: Optional[bool], ao_vivo: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """`linha` na forma pública (ou None) · `tentativa_pendente` None = não deu para saber (Redis fora) ·
    `ao_vivo` = o `data` do `/instance/status` (ou None). Só o SIM do provedor é lido: `LoggedIn:false` mente
    depois de um restart dele, então nunca derruba o que o banco gravou.

    `desde`: a data da CONEXÃO; em `desconectada` (e na saída que a pessoa escolheu) a data da DESCONEXÃO."""
    if not esta_ligada:
        return _resposta("desligada")
    sem_linha = "limite" if sem_vaga else "nao_conectada"
    if not linha:
        return _resposta("aguardando_qr" if tentativa_pendente else sem_linha)
    if not linha.get("ativa"):
        motivo = linha.get("motivo")
        if motivo in MOTIVOS_DA_PESSOA or not linha.get("conectada_em"):
            # escolheu sair, ou nunca chegou a conectar: a tela volta ao "Conectar meu WhatsApp"
            return _resposta(sem_linha, motivo=motivo)
        return _resposta("desconectada", numero=linha.get("numero_e164"),
                         desde=linha.get("desconectada_em"), motivo=motivo)
    logado = bool((ao_vivo or {}).get("LoggedIn") or (ao_vivo or {}).get("loggedIn"))
    status = str(linha.get("channel_status") or "")
    if status == "connected" or (logado and linha.get("conectada_em")):
        return _resposta("conectada", numero=linha.get("numero_e164"), desde=linha.get("conectada_em"))
    if status == "connecting" or not status:
        if tentativa_pendente is False and not logado:
            # a tentativa morreu (TTL) sem conectar: a tela oferece o botão de novo
            return _resposta(sem_linha)
        return _resposta("aguardando_qr")
    # ativa mas caída (o celular sem internet, o socket fechou): a faixa da desconexão, com a data dela
    return _resposta("desconectada", numero=linha.get("numero_e164"),
                     desde=linha.get("desconectada_em") or linha.get("conectada_em"), motivo=linha.get("motivo"))


# ---------------------------------------------------------------------------------------------------------------------
# o evento de conexão (o webhook — L2 — e o pareamento chamam)
# ---------------------------------------------------------------------------------------------------------------------
def _lid_de(payload: Any, _prof: int = 0) -> Optional[str]:
    """O primeiro `…@lid` do evento (o identificador opaco do WhatsApp). Nunca se deduz telefone dele."""
    if _prof > 4:
        return None
    if isinstance(payload, str):
        return payload if payload.endswith("@lid") else None
    if isinstance(payload, dict):
        valores = list(payload.values())
    elif isinstance(payload, list):
        valores = payload[:20]
    else:
        return None
    for v in valores:
        achado = _lid_de(v, _prof + 1)
        if achado:
            return achado
    return None


def _linha_viva(db: Any, integration: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Relê a linha do evento — filtrada por id, corretora, purpose e DONO."""
    iid = str((integration or {}).get("id") or (integration or {}).get("integration_id") or "").strip()
    cid = str((integration or {}).get("company_id") or "").strip().lower()
    uid = str((integration or {}).get("owner_user_id") or "").strip().lower()
    if not (iid and cid and uid) or str((integration or {}).get("purpose") or PURPOSE) != PURPOSE:
        return None
    linhas = _dados(_t(db, "integrations").select(_CAMPOS)
                    .eq("id", iid).eq("company_id", cid).eq("purpose", PURPOSE).eq("owner_user_id", uid)
                    .limit(1).execute())
    linhas = [x for x in linhas if str(x.get("id")) == iid and _mesma(x.get("company_id"), cid)
              and _mesma(x.get("owner_user_id"), uid) and _e_linha(x)]
    return linhas[0] if linhas else None


def _atualizar(db: Any, row: Dict[str, Any], campos: Dict[str, Any]) -> None:
    (_t(db, "integrations").update(campos)
     .eq("id", row["id"]).eq("company_id", row["company_id"]).eq("purpose", PURPOSE)
     .eq("owner_user_id", row["owner_user_id"]).execute())


def registrar_conexao(db: Any, integration: Dict[str, Any], evento: Any) -> Dict[str, Any]:
    """A linha CONECTOU: grava o número, o JID e/ou o LID e o "conectada desde" (só na transição).

    `evento` = o corpo cru do webhook, o envelope v2 ou o `/instance/status` — o JID é procurado onde o provedor
    costuma pô-lo (`numero_pareado.jid_pareado`) e o LID em qualquer `…@lid`. Silêncio do provedor não apaga o que
    ele já disse. Linha inativa (a pessoa desconectou) NÃO ressuscita por evento.
    """
    from app.services.whatsapp.numero_pareado import identidade_pareada, mascarar

    row = _linha_viva(db, integration)
    if not row:
        return {"ok": False, "motivo": "nao_e_linha_do_usuario"}
    if row.get("is_active") is not True:
        return {"ok": False, "motivo": "linha_inativa"}
    agora = _agora()
    jid, telefone = identidade_pareada(evento if isinstance(evento, dict) else {})
    lid = _lid_de(evento)
    campos: Dict[str, Any] = {"channel_status": "connected", "last_seen_at": agora,
                              "linha_desconectada_em": None, "linha_motivo": None}
    if row.get("channel_status") != "connected" or not row.get("linha_conectada_em"):
        campos["linha_conectada_em"] = agora
    if jid and telefone:
        campos.update({"linha_jid": jid, "paired_jid": jid, "paired_phone_e164": telefone, "paired_at": agora})
    if lid:
        campos["linha_lid"] = lid
    try:
        _atualizar(db, row, campos)
    except Exception as exc:  # noqa: BLE001
        if "uq_integrations_linha_por_numero" in str(exc) or "23505" in str(exc):
            # o MESMO WhatsApp já está ativo noutra linha: esta não sobe (o banco recusou; nada de duas sessões)
            logger.warning("[LINHA] numero %s ja conectado noutra linha — esta fica desconectada",
                           mascarar(telefone))
            _atualizar(db, row, {"is_active": False, "channel_status": "disconnected",
                                 "linha_desconectada_em": agora, "linha_motivo": "numero_ja_conectado"})
            return {"ok": False, "motivo": "numero_ja_conectado"}
        raise
    if telefone:
        logger.info("[LINHA] conectada: %s", mascarar(telefone))
    return {"ok": True, "conectada_em": campos.get("linha_conectada_em") or row.get("linha_conectada_em"),
            "jid": bool(jid), "lid": bool(lid)}


def registrar_conexao_da_instancia(db: Any, company_id: Any, owner_user_id: Any, instance_name: Any,
                                   evento: Any) -> Dict[str, Any]:
    """O mesmo `registrar_conexao`, achando a linha pela instância DESTE dono nesta corretora (o pareamento chama)."""
    cid, uid = _uuid(company_id, "company_id"), _uuid(owner_user_id, "owner_user_id")
    nome = str(instance_name or "").strip()
    row = next((x for x in _linhas_do_dono(db, cid, uid)
                if x.get("is_active") is True and str(x.get("instance_id") or "") == nome), None)
    if not row:
        return {"ok": False, "motivo": "nao_e_linha_do_usuario"}
    return registrar_conexao(db, row, evento)


def registrar_desconexao(db: Any, integration: Dict[str, Any], motivo: Any) -> Dict[str, Any]:
    """A linha CAIU (ou a pessoa saiu): `linha_desconectada_em` + `linha_motivo`; nada do histórico é apagado.

    Motivo definitivo (`MOTIVOS_DEFINITIVOS`) → a linha deixa de ser ativa (sai do teto e o webhook a ignora).
    Durante o pareamento (`connecting`) só a PESSOA encerra — um evento do provedor no meio do QR (ex.: o logout
    forçado do QRTimeout) não derruba a tentativa: quem cuida dela é o `qr()`, que renova.
    Idempotente: linha já inativa não tem a data da primeira desconexão sobrescrita.
    """
    row = _linha_viva(db, integration)
    if not row:
        return {"ok": False, "motivo": "nao_e_linha_do_usuario"}
    m = _MOTIVO.sub("_", str(motivo or "").strip().lower()).strip("_")[:64] or "desconhecido"
    if row.get("is_active") is not True:
        return {"ok": True, "ja_estava": True}
    if row.get("channel_status") == "connecting" and m not in MOTIVOS_DA_PESSOA:
        return {"ok": True, "ignorado": "pareamento_em_andamento"}
    definitiva = m in MOTIVOS_DEFINITIVOS
    campos: Dict[str, Any] = {"channel_status": "disconnected", "linha_desconectada_em": _agora(),
                              "linha_motivo": m}
    if definitiva:
        campos["is_active"] = False
    _atualizar(db, row, campos)
    return {"ok": True, "definitiva": definitiva, "motivo": m}


__all__ = [
    "PURPOSE", "ESTADOS", "Recusa", "FRASE_LIMITE", "FRASE_DESLIGADA", "MAX_LINHAS_PADRAO",
    "CHAVE_LIGADA", "ligada", "ligada_para", "max_linhas", "linha_da_instancia", "linha_do_dono", "linha_crua_do_dono",
    "contar_linhas_ativas", "teto_cheio", "membro_ativo", "ativa_em_outra_corretora", "calcular_estado",
    "registrar_conexao", "registrar_conexao_da_instancia", "registrar_desconexao",
]
