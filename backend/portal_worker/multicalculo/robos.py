# -*- coding: utf-8 -*-
"""Os robôs do multicálculo — SPEC-129-B U4 (F3).

Um ROBÔ é uma linha de `portal_accounts` com `portal_key='agger'` e `robo_estado` não nulo
(as 16 contas de hoje têm `robo_estado` nulo: não são robôs e este módulo não as vê).

    escolher(supa, corretora_id, origem)  → a conta, JÁ COM A LEASE no banco, ou None
    renovar(supa, conta, dono)            → a batida da lease; False = perdi o robô
    liberar(supa, conta, dono)            → solta a lease SÓ se ainda for minha
    marcar_estado(supa, conta, estado)    → ocupada · pausado · bloqueado (com o porquê no chamador)
    dentro_da_janela(janela, agora)       → a conta pode trabalhar agora?

🔴 Por que NÃO `app/services/portals/resolver.resolver_conta`: ele recusa quando a corretora tem
mais de uma conta do portal ("ambígua") — e mais de um robô por corretora é exatamente o RODÍZIO.

🔴 Por que a lease mora no BANCO e não em `leases.LeaseDePortal` (D-129B-10): 📊 sem Redis,
`LeaseDePortal.adquirir` devolve `True` (`leases.py:415-419`) — concede a conta a todo mundo.
Para um login de sessão ÚNICA (o Agger derruba a sessão anterior) isso é a colisão inteira.
Aqui a lease é um CAS em `portal_accounts.robo_dono/robo_batida_em`: só ganha quem acha a linha
SEM dono ou com a batida VENCIDA — o banco decide, um ganha (molde: `worker._tentar_claim` e
Kubernetes Lease — dono + duração + renovação).

Síncrono de propósito: o motor chama por `asyncio.to_thread` (o supabase-py é bloqueante e o
laço do portal não pode esperar o do multicálculo — G8).
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, Optional

logger = logging.getLogger("portal_worker.multicalculo")

PORTAL_KEY = "agger"

ATIVO = "ativo"
PAUSADO = "pausado"
BLOQUEADO = "bloqueado"
OCUPADA = "ocupada"
TESTE = "teste"
ESTADOS = (ATIVO, PAUSADO, BLOQUEADO, OCUPADA, TESTE)

# 💭 60 cálculos por hora por login (D-129B-07): um cálculo do Agger leva 📊 40 s–7 min (A-PROVA-DO-AGGER)
# e o robô faz UM grupo por vez; 60/h só é atingido por um laço descontrolado, nunca por uso normal. A coluna
# `robo_teto_por_hora` (1–600) vence este padrão, conta por conta.
TETO_PADRAO_POR_HORA = 60

# A lease vence em 90 s e a batida é a cada 20 s (ver motor.BATIDA_S): o dono perde QUATRO batidas
# seguidas antes de outro motor poder assumir — uma pausa de GC ou um PostgREST lento não trocam o dono,
# um processo morto troca em ≤ 90 s.
LEASE_VENCE_S = 90

# A janela é escrita no horário de Brasília. Fuso FIXO −03:00 (o Brasil não tem horário de verão desde
# 2019) em vez de `zoneinfo`: a imagem slim do worker pode não ter `tzdata`, e janela que levanta exceção
# fecharia o robô em silêncio.
FUSO_DA_JANELA = timezone(timedelta(hours=-3))

_DIAS = ("seg", "ter", "qua", "qui", "sex", "sab", "dom")   # weekday() 0..6
_RE_HORA = re.compile(r"^\s*(\d{1,2}):(\d{2})\s*$")


def _iso(t: datetime) -> str:
    return t.astimezone(timezone.utc).isoformat()


def _ts(valor: Any) -> Optional[datetime]:
    if valor is None or valor == "":
        return None
    if isinstance(valor, datetime):
        return valor if valor.tzinfo else valor.replace(tzinfo=timezone.utc)
    try:
        t = datetime.fromisoformat(str(valor).strip().replace("Z", "+00:00").replace(" ", "T", 1))
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def _agora() -> datetime:
    return datetime.now(timezone.utc)


# ==========================================================================
# A janela
# ==========================================================================
def _dias(spec: Any) -> Optional[set]:
    """`["seg","ter"]` · `[0,1]` · `"seg-sex"` · `"seg,qua,sex"` → {0,1,...}. Ilegível → None."""
    if isinstance(spec, (list, tuple)):
        saida = set()
        for d in spec:
            if isinstance(d, int) and not isinstance(d, bool) and 0 <= d <= 6:
                saida.add(d)
            elif str(d).strip().lower()[:3] in _DIAS:
                saida.add(_DIAS.index(str(d).strip().lower()[:3]))
            else:
                return None
        return saida
    texto = str(spec or "").strip().lower()
    if not texto:
        return None
    saida = set()
    for parte in texto.split(","):
        parte = parte.strip()
        if "-" in parte:
            a, _, b = parte.partition("-")
            a, b = a.strip()[:3], b.strip()[:3]
            if a not in _DIAS or b not in _DIAS:
                return None
            i, j = _DIAS.index(a), _DIAS.index(b)
            saida.update(range(i, j + 1) if i <= j else list(range(i, 7)) + list(range(0, j + 1)))
        elif parte[:3] in _DIAS:
            saida.add(_DIAS.index(parte[:3]))
        else:
            return None
    return saida


def _minutos(hhmm: Any) -> Optional[int]:
    m = _RE_HORA.match(str(hhmm or ""))
    if not m:
        return None
    h, mi = int(m.group(1)), int(m.group(2))
    if h > 24 or mi > 59 or (h == 24 and mi):
        return None
    return h * 60 + mi


def dentro_da_janela(janela: Any, agora: Optional[datetime] = None) -> bool:
    """A conta pode trabalhar AGORA?

    `None` = sem janela = sempre (só conta `ativo`; `teste` sem janela é proibido pelo CHECK do banco e,
    se chegar aqui, `conta_elegivel` recusa). Formatos aceitos (💭 a costura confere com o
    `multicalculo_robo.py cadastrar --janela`): `{"dias": "seg-sex", "inicio": "07:00", "fim": "20:00"}`
    (dias também como lista de nomes ou de 0..6) ou o texto `"seg-sex,07:00-20:00"`.

    🔴 Janela ILEGÍVEL = FORA da janela. Falhar aberto aqui poria a conta de uma PESSOA para trabalhar
    no horário dela.
    """
    if janela is None:
        return True
    if isinstance(janela, str):
        texto = janela.strip()
        if "," not in texto:
            return False
        dias_txt, _, horas = texto.rpartition(",")
        inicio, _, fim = horas.partition("-")
        janela = {"dias": dias_txt, "inicio": inicio, "fim": fim}
    if not isinstance(janela, dict):
        return False
    dias = _dias(janela.get("dias"))
    ini, fim = _minutos(janela.get("inicio")), _minutos(janela.get("fim"))
    if not dias or ini is None or fim is None or ini == fim:
        return False
    local = (agora or _agora()).astimezone(FUSO_DA_JANELA)
    m = local.hour * 60 + local.minute
    if ini < fim:
        return local.weekday() in dias and ini <= m < fim
    # janela que atravessa a meia-noite (ex.: 22:00-06:00): a parte da madrugada é do dia ANTERIOR
    if m >= ini:
        return local.weekday() in dias
    if m < fim:
        return (local.weekday() - 1) % 7 in dias
    return False


# ==========================================================================
# Elegibilidade
# ==========================================================================
def conta_elegivel(conta: Dict[str, Any], origem: str, agora: datetime, *, canario: bool) -> tuple:
    """(True, "") ou (False, motivo). Pura: o teto por hora e a lease ficam em `escolher`."""
    estado = conta.get("robo_estado")
    if estado not in ESTADOS:
        return False, "não é robô"
    if estado in (PAUSADO, BLOQUEADO):
        return False, estado
    if estado == OCUPADA:
        ate = _ts(conta.get("robo_ocupada_ate"))
        if ate is not None and ate > agora:
            return False, "ocupada"
    if estado == TESTE:
        # 🔴 D-129B-04: a conta de PESSOA só serve a pedido de TESTE, e só no canário.
        if origem != "teste" or not canario:
            return False, "conta de teste só atende pedido de teste no canário"
        if conta.get("robo_janela") is None:
            return False, "conta de teste sem janela"
    if not dentro_da_janela(conta.get("robo_janela"), agora):
        return False, "fora da janela"
    if not conta.get("secret_encrypted"):
        return False, "sem senha"
    return True, ""


def teto_da_conta(conta: Dict[str, Any]) -> int:
    try:
        n = int(conta.get("robo_teto_por_hora") or 0)
    except (TypeError, ValueError):
        n = 0
    return n if 1 <= n <= 600 else TETO_PADRAO_POR_HORA


def calculos_na_ultima_hora(supa, *, company_id: str, account_id: Optional[str] = None,
                            agora: Optional[datetime] = None) -> int:
    """Cálculos que JÁ saíram (`disparado_em` na última hora) desta corretora — e desta conta."""
    desde = _iso((agora or _agora()) - timedelta(hours=1))
    q = (supa.table("multicalculo_calculos").select("id")
         .eq("company_id", company_id).gte("disparado_em", desde))
    if account_id:
        q = q.eq("account_id", account_id)
    return len(q.execute().data or [])


# ==========================================================================
# A escolha + a lease
# ==========================================================================
def candidatos(supa, corretora_id: str) -> list:
    """As contas-robô do Agger DESTA corretora, a menos usada primeiro (a batida mais antiga) —
    é o que faz o rodízio girar em vez de gastar sempre o mesmo login."""
    r = (supa.table("portal_accounts")
         .select("id, company_id, portal_key, account_label, username, secret_encrypted, robo_estado, "
                 "robo_teto_por_hora, robo_janela, robo_ocupada_ate, robo_dono, robo_batida_em")
         .eq("company_id", corretora_id).eq("portal_key", PORTAL_KEY)
         .order("robo_batida_em").order("id").execute())
    return [c for c in (r.data or []) if c.get("robo_estado") is not None]


def adquirir(supa, conta: Dict[str, Any], dono: str, agora: datetime,
             lease_s: int = LEASE_VENCE_S) -> bool:
    """CAS da lease: grava `robo_dono=dono` SÓ se a linha está sem dono ou com a batida vencida.
    A linha voltou = é minha. Nada voltou = outro motor está nela."""
    if not dono:
        return False
    vencida = _iso(agora - timedelta(seconds=lease_s))
    # `robo_dono.eq.<eu>`: a sessão ociosa deste MESMO motor (ele segurou a lease para reaproveitar o
    # login). Dois grupos do mesmo motor no mesmo robô o motor impede antes (`ignorar`).
    dono_q = '"' + str(dono).replace('"', "") + '"'
    r = (supa.table("portal_accounts")
         .update({"robo_dono": dono, "robo_batida_em": _iso(agora)})
         .eq("id", conta["id"]).eq("company_id", conta["company_id"])
         .or_(f"robo_dono.is.null,robo_dono.eq.{dono_q},robo_batida_em.is.null,robo_batida_em.lt.{vencida}")
         .execute())
    return bool(r.data)


def escolher(supa, corretora_id: str, origem: str, *, dono: str, agora: Optional[datetime] = None,
             quantos: int = 1, canario: bool = False, lease_s: int = LEASE_VENCE_S,
             ignorar: Iterable[str] = ()) -> Optional[Dict[str, Any]]:
    """A conta-robô que vai rodar `quantos` cálculos desta corretora — com a lease JÁ tomada — ou None.

    Percorre as candidatas (a menos usada primeiro); a ocupada por outro motor perde o CAS e a próxima
    é tentada. `ocupada` com o prazo vencido volta a `ativo` ao ser tomada."""
    agora = agora or _agora()
    pulo = set(ignorar or ())
    for conta in candidatos(supa, corretora_id):
        if conta["id"] in pulo:
            continue
        ok, _motivo = conta_elegivel(conta, origem, agora, canario=canario)
        if not ok:
            continue
        feitos = calculos_na_ultima_hora(supa, company_id=corretora_id, account_id=conta["id"], agora=agora)
        if feitos + max(1, int(quantos)) > teto_da_conta(conta):
            logger.warning("[MC] robô %s no teto por hora (%s)", conta["id"], teto_da_conta(conta))
            continue
        if not adquirir(supa, conta, dono, agora, lease_s):
            continue
        if conta.get("robo_estado") == OCUPADA:
            (supa.table("portal_accounts").update({"robo_estado": ATIVO, "robo_ocupada_ate": None})
             .eq("id", conta["id"]).eq("company_id", corretora_id).eq("robo_dono", dono)
             .eq("robo_estado", OCUPADA).execute())
            conta = {**conta, "robo_estado": ATIVO, "robo_ocupada_ate": None}
        return {**conta, "robo_dono": dono, "robo_batida_em": _iso(agora)}
    return None


def renovar(supa, conta: Dict[str, Any], dono: str, agora: Optional[datetime] = None) -> bool:
    """A batida. `False` = a lease não é mais minha: o chamador PARA de usar a sessão."""
    r = (supa.table("portal_accounts").update({"robo_batida_em": _iso(agora or _agora())})
         .eq("id", conta["id"]).eq("company_id", conta["company_id"]).eq("robo_dono", dono).execute())
    return bool(r.data)


def liberar(supa, conta: Dict[str, Any], dono: str) -> None:
    """Solta a lease SÓ se ainda for minha — liberar a lease de outro é o bug clássico do lock."""
    try:
        (supa.table("portal_accounts").update({"robo_dono": None, "robo_batida_em": None})
         .eq("id", conta["id"]).eq("company_id", conta["company_id"]).eq("robo_dono", dono).execute())
    except Exception as exc:  # noqa: BLE001 — a lease vence sozinha em LEASE_VENCE_S
        logger.warning("[MC] não consegui soltar o robô %s (%s)", conta.get("id"), type(exc).__name__)


def marcar_estado(supa, conta: Dict[str, Any], estado: str, *, agora: Optional[datetime] = None,
                  ocupada_min: Optional[int] = None) -> None:
    if estado not in ESTADOS:
        raise ValueError(f"estado de robô desconhecido: {estado!r}")
    patch: Dict[str, Any] = {"robo_estado": estado}
    if estado == OCUPADA:
        patch["robo_ocupada_ate"] = _iso((agora or _agora()) + timedelta(minutes=int(ocupada_min or 30)))
    (supa.table("portal_accounts").update(patch)
     .eq("id", conta["id"]).eq("company_id", conta["company_id"]).execute())


def conta_publica(conta: Dict[str, Any]) -> Dict[str, Any]:
    """O que a sessão recebe da conta: tudo, MENOS o segredo cifrado e a lease."""
    return {k: v for k, v in conta.items()
            if k not in ("secret_encrypted", "robo_dono", "robo_batida_em")}


__all__: tuple = (
    "PORTAL_KEY", "ESTADOS", "ATIVO", "PAUSADO", "BLOQUEADO", "OCUPADA", "TESTE",
    "TETO_PADRAO_POR_HORA", "LEASE_VENCE_S", "dentro_da_janela", "conta_elegivel", "teto_da_conta",
    "calculos_na_ultima_hora", "candidatos", "adquirir", "escolher", "renovar", "liberar",
    "marcar_estado", "conta_publica",
)

