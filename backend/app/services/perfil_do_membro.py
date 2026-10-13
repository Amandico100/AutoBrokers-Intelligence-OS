# -*- coding: utf-8 -*-
"""SPEC-131-B G3 — o MEU perfil na corretora: o WhatsApp de trabalho, a ausência (férias) e a situação da equipe.

    ler_perfil(db, company_id, user_id)                          o que a tela "Meu perfil" mostra
    gravar_whatsapp_trabalho(db, company_id, user_id, *, numero, confirmo, por_user_id)
    remover_whatsapp_trabalho(db, company_id, user_id, *, por_user_id)
    criar_ausencia(db, company_id, *, user_id, substituto_user_id, de, ate, por_user_id)
    apagar_ausencia(db, company_id, *, ausencia_id, por_user_id)
    situacao_da_equipe(db, company_id)                           a coluna SITUAÇÃO de Personalização → Equipe

D-131-41: o "Meu WhatsApp de trabalho" é SÓ o número, confirmado pela própria pessoa, gravado no MEMBRO
(`company_members.whatsapp_trabalho_e164` + `whatsapp_trabalho_confirmado_em`, por corretora). ⛔ Nada em
`integrations`, nenhum pareamento: o número de ATENDIMENTO da corretora e o do QUEM COBRA MENOS são outros e não mudam.
Só a própria pessoa grava o dela (nem o admin grava o número de outra pessoa).
D-131-08: a ausência aponta OUTRA pessoa ATIVA da MESMA corretora (`membro_ausencias`, CHECKs no banco também). O cálculo
continua no Agger do dono; o aviso vai ao substituto (`qual_agger.substituto_ativo`, o leitor). A pessoa cria a dela; o
admin da corretora pode criar a de outra pessoa.
🔴 TODA leitura e escrita filtra `company_id` (CLAUDE.md §7 — o backend usa service role). ⛔ Nenhum número de telefone
vai para log; o número só volta para a PRÓPRIA pessoa.
"""
from __future__ import annotations

import logging
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

TABELA_AUSENCIAS = "membro_ausencias"
_UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
#: 💭 uma ausência cobre no máximo isto de dias (férias longas viram duas); evita um "até 2099" por engano
DURACAO_MAXIMA_DIAS = 180
#: o dia é o de Brasília (o mesmo fuso fixo dos robôs e de `qual_agger._hoje`)
_FUSO = timezone(timedelta(hours=-3))


class Recusa(Exception):
    """O pedido foi recusado — a mensagem é para quem pediu, em português, sem dado sensível."""


def _dados(r: Any) -> List[Dict[str, Any]]:
    return list(getattr(r, "data", None) or [])


def _t(db: Any, tabela: str) -> Any:
    cliente = db if hasattr(db, "table") else getattr(db, "client", db)
    return cliente.table(tabela)


def _uuid(v: Any, oque: str = "id") -> str:
    s = str(v or "").strip().lower()
    if not _UUID.match(s):
        raise Recusa(f"{oque} inválido")
    return s


def _hoje() -> date:
    return datetime.now(_FUSO).date()


def _data(v: Any, oque: str) -> date:
    try:
        return date.fromisoformat(str(v or "").strip()[:10])
    except ValueError:
        raise Recusa(f"Data {oque} inválida — use o calendário.") from None


# ---------------------------------------------------------------------------------------------------------------------
# quem é quem (sempre por company_id)
# ---------------------------------------------------------------------------------------------------------------------
def _membros_ativos(db: Any, company_id: str) -> List[Dict[str, str]]:
    """`[{user_id, nome}]` dos membros ATIVOS desta corretora — o leitor que a tela da equipe já usa."""
    from app.services.sistema_de_gestao import dono as DONO

    return DONO.membros_ativos(db, company_id)


def _e_membro_ativo(db: Any, company_id: str, user_id: str) -> bool:
    from portal_worker.multicalculo import robos as ROB

    return ROB.membro_ativo(db, company_id, user_id)


def _e_admin(db: Any, company_id: str, user_id: str) -> bool:
    from portal_worker.multicalculo import conta_do_robo as CR

    linhas = _dados(_t(db, "company_members").select("user_id, company_id, role, is_owner, status")
                    .eq("company_id", company_id).eq("user_id", user_id).eq("status", "active").limit(1).execute())
    linhas = [v for v in linhas if str(v.get("company_id")).lower() == company_id
              and str(v.get("user_id")).lower() == user_id and v.get("status") == "active"]
    return bool(linhas) and bool(linhas[0].get("is_owner") or linhas[0].get("role") in CR.PAPEIS_DE_ADMIN)


def _primeiro_nome(nome: str) -> str:
    return (nome or "").strip().split(" ")[0] or "Sem nome"


# ---------------------------------------------------------------------------------------------------------------------
# o WhatsApp de trabalho (D-131-41)
# ---------------------------------------------------------------------------------------------------------------------
#: 🔴 a MESMA regra do CHECK `ck_company_members_whatsapp_e164` (migration 20261014_01): +55, DDD sem zero, celular
#: com 9 + 8 dígitos ou fixo começando em 2–5 com 8 dígitos. O Python e o banco nunca discordam (RT-P3/J-P3).
_E164_DO_BRASIL = re.compile(r"^\+55[1-9][1-9](9[0-9]{8}|[2-5][0-9]{7})$")


def _nacional_de(texto: Any) -> Optional[str]:
    """Os dígitos NACIONAIS (DDD + número) de um texto de telefone — ou None quando ele é de OUTRO país. "+55 …",
    "0055 …", "55 11 9…" (12–13 dígitos), "011 3333-4444" (o 0 de longa distância) e "11 9…" são do Brasil;
    "+1 …", "+351 …", "001 …" não são (e nunca viram um número brasileiro de DDD trocado)."""
    bruto = str(texto or "").strip()
    digitos = re.sub(r"\D", "", bruto)
    if not digitos:
        return None
    if bruto.startswith("+"):
        return digitos[2:] if digitos.startswith("55") else None
    if digitos.startswith("00"):
        return digitos[4:] if digitos.startswith("0055") else None
    if len(digitos) in (12, 13) and digitos.startswith("55"):
        return digitos[2:]
    return digitos[1:] if digitos.startswith("0") else digitos


def e164_do_brasil(texto: Any) -> Optional[str]:
    """"+55DDDNÚMERO" quando o texto é um número do Brasil válido pela regra do banco — senão None. A régua ÚNICA do
    produto para número de WhatsApp: o de trabalho (aqui) e o do cliente no envio (`api.renovacoes`)."""
    nacional = _nacional_de(texto)
    numero = f"+55{nacional}" if nacional else ""
    return numero if _E164_DO_BRASIL.match(numero) else None


def normalizar_whatsapp(texto: Any) -> str:
    """O número em E.164 do Brasil. Aceita "+55 (11) 9…", "5511…" ou "11 9…" (sem país → Brasil). Recusa, com a frase
    de correção, tudo o que o CHECK do banco recusaria (RT-P3: nunca um 500): outro país, DDD inválido, tamanho
    errado, celular sem o 9, fixo que não começa em 2–5."""
    bruto = str(texto or "").strip()
    digitos = re.sub(r"\D", "", bruto)
    if not digitos:
        raise Recusa("Digite o número do WhatsApp em que você atende os clientes.")
    numero = e164_do_brasil(bruto)
    if numero:
        return numero
    nacional = _nacional_de(bruto)
    if nacional is None:
        raise Recusa("Use um número do Brasil: +55, o DDD e o número, por exemplo +55 (11) 9 1234-5678. "
                     "Se faltou o 55, coloque-o depois do +.")
    ddd = nacional[:2]
    if len(nacional) not in (10, 11) or len(ddd) < 2 or "0" in ddd:
        raise Recusa("Confira o DDD e o número: no Brasil são 2 dígitos de DDD e 8 ou 9 do número.")
    if len(nacional) == 11:
        raise Recusa("Celular no Brasil começa com 9 depois do DDD. Confira o número.")
    raise Recusa("Este número não parece um WhatsApp. Celular tem 9 dígitos depois do DDD, começando com 9; "
                 "telefone fixo tem 8, começando de 2 a 5.")


def _so_a_propria_pessoa(user_id: str, por_user_id: Any) -> None:
    if str(por_user_id or "").strip().lower() != user_id:
        raise Recusa("Só a própria pessoa grava o WhatsApp de trabalho dela.")


def gravar_whatsapp_trabalho(db: Any, company_id: Any, user_id: Any, *, numero: Any, confirmo: Any,
                             por_user_id: Any, agora: Optional[datetime] = None) -> Dict[str, Any]:
    """Grava o número no MEMBRO desta corretora, com a hora da confirmação. Exige `confirmo is True` (a pessoa
    confirma que é o WhatsApp em que atende os clientes) e que quem pede seja a própria pessoa, membro ativo."""
    cid, uid = _uuid(company_id, "company_id"), _uuid(user_id, "user_id")
    _so_a_propria_pessoa(uid, por_user_id)
    if confirmo is not True:
        raise Recusa("Confirme que este é o WhatsApp em que você atende os clientes.")
    e164 = normalizar_whatsapp(numero)
    if not _e_membro_ativo(db, cid, uid):
        raise Recusa("Você não está ativo na equipe desta corretora.")
    quando = (agora or datetime.now(timezone.utc)).isoformat()
    feito = _dados(_t(db, "company_members")
                   .update({"whatsapp_trabalho_e164": e164, "whatsapp_trabalho_confirmado_em": quando})
                   .eq("company_id", cid).eq("user_id", uid).execute())
    if not feito:
        raise Recusa("Não achei o seu cadastro nesta corretora.")
    return {"numero": e164, "confirmado_em": quando, "confirmado": True}


def remover_whatsapp_trabalho(db: Any, company_id: Any, user_id: Any, *, por_user_id: Any) -> Dict[str, Any]:
    cid, uid = _uuid(company_id, "company_id"), _uuid(user_id, "user_id")
    _so_a_propria_pessoa(uid, por_user_id)
    _t(db, "company_members").update({"whatsapp_trabalho_e164": None, "whatsapp_trabalho_confirmado_em": None}) \
        .eq("company_id", cid).eq("user_id", uid).execute()
    return {"numero": None, "confirmado_em": None, "confirmado": False}


def _whatsapp_do_membro(db: Any, company_id: str, user_id: str) -> Dict[str, Any]:
    try:
        linhas = _dados(_t(db, "company_members")
                        .select("user_id, company_id, whatsapp_trabalho_e164, whatsapp_trabalho_confirmado_em")
                        .eq("company_id", company_id).eq("user_id", user_id).limit(1).execute())
    except Exception as exc:  # noqa: BLE001 — antes da migration da G1 as colunas não existem
        logger.warning("[PERFIL] WhatsApp de trabalho ilegível (%s)", type(exc).__name__)
        return {"numero": None, "confirmado_em": None, "confirmado": False, "disponivel": False}
    linhas = [x for x in linhas if str(x.get("company_id")).lower() == company_id
              and str(x.get("user_id")).lower() == user_id]
    m = linhas[0] if linhas else {}
    numero = m.get("whatsapp_trabalho_e164")
    confirmado_em = m.get("whatsapp_trabalho_confirmado_em")
    return {"numero": numero, "confirmado_em": confirmado_em, "confirmado": bool(numero and confirmado_em),
            "disponivel": True}


# ---------------------------------------------------------------------------------------------------------------------
# a ausência (D-131-08)
# ---------------------------------------------------------------------------------------------------------------------
def _ausencias(db: Any, company_id: str, *, coluna: str, user_id: str, desde: date) -> List[Dict[str, Any]]:
    linhas = _dados(_t(db, TABELA_AUSENCIAS).select("id, company_id, user_id, substituto_user_id, de, ate")
                    .eq("company_id", company_id).eq(coluna, user_id).gte("ate", desde.isoformat()).execute())
    return sorted([x for x in linhas if str(x.get("company_id")).lower() == company_id
                   and str(x.get(coluna)).lower() == user_id and str(x.get("ate") or "")[:10] >= desde.isoformat()],
                  key=lambda x: str(x.get("de")))


def _cruza(ausencia: Dict[str, Any], d0: date, d1: date) -> bool:
    return str(ausencia.get("de"))[:10] <= d1.isoformat() and str(ausencia.get("ate"))[:10] >= d0.isoformat()


def quem_eu_cubro_hoje(db: Any, company_id: Any, user_id: Any, *, hoje: Optional[date] = None) -> List[str]:
    """J-P6: os `user_id` desta corretora cuja ausência ATIVA hoje tem `user_id` como substituto — as renovações deles
    entram no "Minhas" de quem cobre (D-131-08). Filtro `company_id` no banco e de novo aqui."""
    cid, uid = _uuid(company_id, "company_id"), _uuid(user_id, "user_id")
    dia = (hoje or _hoje()).isoformat()
    linhas = _dados(_t(db, TABELA_AUSENCIAS).select("id, company_id, user_id, substituto_user_id, de, ate")
                    .eq("company_id", cid).eq("substituto_user_id", uid).lte("de", dia).gte("ate", dia).execute())
    return sorted({str(a.get("user_id")).lower() for a in linhas
                   if str(a.get("company_id")).lower() == cid and str(a.get("substituto_user_id")).lower() == uid
                   and str(a.get("de"))[:10] <= dia <= str(a.get("ate"))[:10] and a.get("user_id")})


def criar_ausencia(db: Any, company_id: Any, *, user_id: Any, substituto_user_id: Any, de: Any, ate: Any,
                   por_user_id: Any, hoje: Optional[date] = None) -> Dict[str, Any]:
    """Cria a ausência de `user_id` com OUTRA pessoa ativa da MESMA corretora cobrindo. Recusa: a própria pessoa como
    substituta · alguém de fora/inativo · período invertido, já passado ou longo demais · sobreposição com outra
    ausência da mesma pessoa · quem pede não é a pessoa nem admin desta corretora."""
    cid = _uuid(company_id, "company_id")
    uid = _uuid(user_id, "user_id")
    sub = _uuid(substituto_user_id, "substituto")
    por = _uuid(por_user_id, "quem pede")
    if por != uid and not _e_admin(db, cid, por):
        raise Recusa("Só a própria pessoa, ou um administrador da corretora, marca a ausência dela.")
    if sub == uid:
        raise Recusa("Escolha OUTRA pessoa para cobrir a sua ausência.")
    d0, d1 = _data(de, "de início"), _data(ate, "do último dia fora")
    dia = hoje or _hoje()
    if d1 < d0:
        raise Recusa("O último dia fora é antes do dia de saída.")
    if d1 < dia:
        raise Recusa("Este período já passou.")
    if (d1 - d0).days + 1 > DURACAO_MAXIMA_DIAS:
        raise Recusa(f"Uma ausência vai até {DURACAO_MAXIMA_DIAS} dias. Para mais, marque duas.")
    if not _e_membro_ativo(db, cid, uid):
        raise Recusa("Esta pessoa não está ativa na equipe desta corretora.")
    if not _e_membro_ativo(db, cid, sub):
        raise Recusa("Quem vai cobrir precisa ser uma pessoa ativa da equipe desta corretora.")
    for a in _ausencias(db, cid, coluna="user_id", user_id=uid, desde=dia):
        if _cruza(a, d0, d1):
            raise Recusa("Já existe uma ausência marcada neste período. Apague a outra antes.")
    # RT-P5: quem cobre não pode estar FORA no mesmo período (A fora com B cobrindo e B fora com A cobrindo: o aviso
    # iria a quem está de férias, e ninguém cuidaria das renovações)
    for a in _ausencias(db, cid, coluna="user_id", user_id=sub, desde=dia):
        if _cruza(a, d0, d1):
            raise Recusa("Quem vai cobrir também está fora nestes dias. Escolha outra pessoa.")
    linha = {"company_id": cid, "user_id": uid, "substituto_user_id": sub, "de": d0.isoformat(),
             "ate": d1.isoformat(), "criado_por": por}
    criada = _dados(_t(db, TABELA_AUSENCIAS).insert(linha).execute())
    return {**linha, "id": (criada[0].get("id") if criada else None)}


def apagar_ausencia(db: Any, company_id: Any, *, ausencia_id: Any, por_user_id: Any) -> Dict[str, Any]:
    cid = _uuid(company_id, "company_id")
    aid = _uuid(ausencia_id, "ausência")
    por = _uuid(por_user_id, "quem pede")
    linhas = [x for x in _dados(_t(db, TABELA_AUSENCIAS).select("id, company_id, user_id").eq("company_id", cid)
                                .eq("id", aid).limit(1).execute())
              if str(x.get("company_id")).lower() == cid and str(x.get("id")).lower() == aid]
    if not linhas:
        raise Recusa("Esta ausência não existe nesta corretora.")
    if str(linhas[0].get("user_id")).lower() != por and not _e_admin(db, cid, por):
        raise Recusa("Só a própria pessoa, ou um administrador da corretora, apaga a ausência dela.")
    _t(db, TABELA_AUSENCIAS).delete().eq("company_id", cid).eq("id", aid).execute()
    return {"apagada": aid}


# ---------------------------------------------------------------------------------------------------------------------
# as leituras das telas
# ---------------------------------------------------------------------------------------------------------------------
def ler_perfil(db: Any, company_id: Any, user_id: Any, *, hoje: Optional[date] = None) -> Dict[str, Any]:
    """O que a tela "Meu perfil" mostra: o MEU WhatsApp de trabalho, as MINHAS ausências (de hoje em diante), as que eu
    cubro, e a lista das OUTRAS pessoas ativas desta corretora (para escolher quem cobre)."""
    cid, uid = _uuid(company_id, "company_id"), _uuid(user_id, "user_id")
    dia = hoje or _hoje()
    pessoas = _membros_ativos(db, cid)
    nomes = {p["user_id"]: p["nome"] for p in pessoas}
    try:
        minhas = _ausencias(db, cid, coluna="user_id", user_id=uid, desde=dia)
        cubro = _ausencias(db, cid, coluna="substituto_user_id", user_id=uid, desde=dia)
        ausencia_disponivel = True
    except Exception as exc:  # noqa: BLE001 — antes da migration da 131-A a tabela não existe
        logger.warning("[PERFIL] ausências ilegíveis (%s)", type(exc).__name__)
        minhas, cubro, ausencia_disponivel = [], [], False

    def _linha(a: Dict[str, Any], quem: str) -> Dict[str, Any]:
        outro = str(a.get(quem) or "").lower()
        de, ate = str(a.get("de"))[:10], str(a.get("ate"))[:10]
        return {"id": a.get("id"), "de": de, "ate": ate, "user_id": outro,
                "nome": nomes.get(outro, "Pessoa fora da equipe"), "ativa": de <= dia.isoformat() <= ate}

    return {
        "whatsapp_trabalho": _whatsapp_do_membro(db, cid, uid),
        "ausencias": [_linha(a, "substituto_user_id") for a in minhas],
        "cubro": [_linha(a, "user_id") for a in cubro],
        "pessoas": [p for p in pessoas if p["user_id"] != uid],
        "ausencia_disponivel": ausencia_disponivel,
        "duracao_maxima_dias": DURACAO_MAXIMA_DIAS,
    }


def situacao_da_equipe(db: Any, company_id: Any, *, hoje: Optional[date] = None) -> Dict[str, Any]:
    """A coluna SITUAÇÃO de cada pessoa ativa: o Agger dela (o retrato do serviço único das contas, sem login nem
    senha), o WhatsApp de trabalho confirmado (sim/não — o NÚMERO não sai daqui) e a ausência ativa hoje."""
    from portal_worker.multicalculo import conta_do_robo as CR

    cid = _uuid(company_id, "company_id")
    dia = (hoje or _hoje()).isoformat()
    equipe = CR.aggers_da_equipe(db, cid).get("pessoas") or []
    zap: Dict[str, Optional[bool]] = {}
    try:
        for m in _dados(_t(db, "company_members")
                        .select("user_id, company_id, whatsapp_trabalho_e164, whatsapp_trabalho_confirmado_em")
                        .eq("company_id", cid).execute()):
            if str(m.get("company_id")).lower() == cid:
                zap[str(m.get("user_id")).lower()] = bool(m.get("whatsapp_trabalho_e164")
                                                          and m.get("whatsapp_trabalho_confirmado_em"))
    except Exception as exc:  # noqa: BLE001 — antes da migration da G1
        logger.warning("[PERFIL] situação: WhatsApp de trabalho ilegível (%s)", type(exc).__name__)
        zap = {}
    fora: Dict[str, Dict[str, Any]] = {}
    try:
        for a in _dados(_t(db, TABELA_AUSENCIAS).select("id, company_id, user_id, substituto_user_id, de, ate")
                        .eq("company_id", cid).lte("de", dia).gte("ate", dia).execute()):
            if str(a.get("company_id")).lower() == cid and str(a.get("de"))[:10] <= dia <= str(a.get("ate"))[:10]:
                fora[str(a.get("user_id")).lower()] = a
    except Exception as exc:  # noqa: BLE001
        logger.warning("[PERFIL] situação: ausências ilegíveis (%s)", type(exc).__name__)
    nomes = {str(p["user_id"]).lower(): p.get("nome") or "Sem nome" for p in equipe}
    pessoas = []
    for p in equipe:
        uid = str(p["user_id"]).lower()
        ag = p.get("agger") or {}
        aus = fora.get(uid)
        pessoas.append({
            "user_id": uid, "nome": p.get("nome"), "primeiro_nome": _primeiro_nome(p.get("nome") or ""),
            "funcoes": list(p.get("funcoes") or []),
            "agger": {"situacao": ag.get("situacao"), "rotulo": ag.get("rotulo"), "conectado": bool(ag.get("conectado"))},
            "whatsapp_trabalho_confirmado": zap.get(uid) if zap else None,
            "ausencia": ({"ate": str(aus.get("ate"))[:10],
                          "substituto": _primeiro_nome(nomes.get(str(aus.get("substituto_user_id")).lower(), ""))}
                         if aus else None),
        })
    return {"pessoas": pessoas}


__all__ = ("Recusa", "e164_do_brasil", "normalizar_whatsapp", "quem_eu_cubro_hoje", "gravar_whatsapp_trabalho", "remover_whatsapp_trabalho", "criar_ausencia",
           "apagar_ausencia", "ler_perfil", "situacao_da_equipe", "DURACAO_MAXIMA_DIAS", "TABELA_AUSENCIAS")
