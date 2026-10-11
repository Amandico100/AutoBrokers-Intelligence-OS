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

# SPEC-131-0 A · F3 (D-131-0-05/29) — DE QUEM é a conta (`portal_accounts.uso`, migration 20261011_04). É o eixo
# "pessoa ou robô" do motor (o `robo_estado` diz só se ela pode trabalhar AGORA):
#   GLOBAL  o robô DEDICADO da corretora: entra no rodízio de `candidatos` (o Quem Cobra Menos e quem não tem Agger)
#   MEMBRO  o Agger de uma PESSOA da equipe (`dono_user_id`): NUNCA no rodízio — só quando o cálculo EXIGE esta conta
#           (`somente`), de um pedido com serviço de pessoa (cotação ou renovação), e só enquanto a dona é membro ATIVO
#           da corretora. O robô entra, calcula e SAI (logout sempre); sessão ativa = a pessoa está usando.
#   TESTE   o login de pessoa do canário: só pedido `teste` no canário (como a conta `robo_estado='teste'`)
GLOBAL = "global"
MEMBRO = "membro"
USO_TESTE = "teste"
USOS = (GLOBAL, MEMBRO, USO_TESTE)
#: os serviços que podem usar o Agger de uma pessoa (o Quem Cobra Menos e o legado `servico=None` NUNCA)
SERVICOS_DA_PESSOA = ("cotacao", "renovacao")

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
    """A conta pode COMEÇAR um trabalho agora? (SPEC-129-C F0: a janela vale para começar — nunca para matar um
    cálculo em andamento, nem para impedir a retomada ou a continuação de um pedido que já começou; ver
    `conta_elegivel(continuacao=...)`.)

    `None` = sem janela = SEMPRE, 24×7, sem nenhum minuto de fora (é a representação da conta GLOBAL "Agger da
    corretora", D-129C-01 — uma janela "seg-dom 00:00-23:59" NÃO é sempre: deixa 23:59–00:00 de fora toda noite) (só
    conta `ativo`; `teste` sem janela é proibido pelo CHECK do banco e,
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
def conta_elegivel(conta: Dict[str, Any], origem: str, agora: datetime, *, canario: bool,
                   continuacao: bool = False, servico: Optional[str] = None, somente: Optional[str] = None,
                   dono_ativo: Optional[bool] = None) -> tuple:
    """(True, "") ou (False, motivo). Pura: o teto por hora e a lease ficam em `escolher`.

    `continuacao` (SPEC-129-C F0, Founder 11/10: *"pode travar durante uma execução"*): o trabalho já COMEÇOU — a
    retomada da leitura de um cálculo `calculando`, ou a econômica que entra no negócio já aberto pelo mesmo pedido.
    A janela vale só para COMEÇAR: numa conta de ROBÔ (`ativo`) a continuação não espera a janela reabrir (o pedido
    ficaria parado a noite inteira, ou expiraria). A conta `teste` (login de PESSOA) obedece à janela SEMPRE — fora
    dela é o horário da pessoa.

    SPEC-131-0 A · F3 (§5.1 da SPEC): a conta `uso='membro'` (o Agger de uma PESSOA) só serve quando o cálculo a EXIGE
    (`somente` = ela), o pedido tem serviço de pessoa (`servico` cotação/renovação — o legado e o Quem Cobra Menos
    NUNCA) e a dona é membro ATIVO desta corretora (`dono_ativo`, reconferido no banco por `membro_ativo` na hora da
    escolha). Qualquer dúvida → inelegível (fail-closed). A conta `uso='teste'` só serve ao canário."""
    estado = conta.get("robo_estado")
    if estado not in ESTADOS:
        return False, "não é robô"
    uso = conta.get("uso")
    if uso not in USOS:
        return False, "conta sem dono definido (uso)"
    if uso == MEMBRO:
        if somente is None or str(somente) != str(conta.get("id")):
            return False, "o Agger de uma pessoa só calcula o que foi pedido nele"
        if servico not in SERVICOS_DA_PESSOA:
            return False, "o Agger de uma pessoa não atende este serviço"
        if not conta.get("dono_user_id") or dono_ativo is not True:
            return False, "a dona deste Agger não está ativa na corretora"
    if uso == USO_TESTE and (origem != "teste" or not canario):
        return False, "conta de teste só atende pedido de teste no canário"
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
    if not (continuacao and estado != TESTE) and not dentro_da_janela(conta.get("robo_janela"), agora):
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
def candidatos(supa, corretora_id: str, *, somente: Optional[str] = None) -> list:
    """As contas-robô do Agger DESTA corretora, a menos usada primeiro (a batida mais antiga) —
    é o que faz o rodízio girar em vez de gastar sempre o mesmo login.

    🔴 SPEC-131-0 A · F3: o rodízio é SÓ das contas da corretora (`uso` global) e do canário (`teste`). O Agger de uma
    PESSOA (`membro`) só aparece quando é ELE o pedido (`somente` = o id dele) — nunca por sorteio."""
    r = (supa.table("portal_accounts")
         .select("id, company_id, portal_key, account_label, username, secret_encrypted, robo_estado, "
                 "robo_teto_por_hora, robo_janela, robo_ocupada_ate, robo_dono, robo_batida_em, uso, dono_user_id")
         .eq("company_id", corretora_id).eq("portal_key", PORTAL_KEY)
         .order("robo_batida_em").order("id").execute())
    return [c for c in (r.data or []) if c.get("robo_estado") is not None
            and (c.get("uso") in (GLOBAL, USO_TESTE)
                 or (c.get("uso") == MEMBRO and somente is not None and str(c.get("id")) == str(somente)))]


def membro_ativo(supa, company_id: str, user_id: Any) -> bool:
    """A pessoa é membro ATIVO DESTA corretora (`company_members.status='active'`) E o usuário dela está ativo
    (`users_v2.status='active'`, sem `deleted_at`)? Qualquer falha de leitura = NÃO (fail-closed — D-131-0-29: a conta
    de uma pessoa só vale enquanto ela é da equipe). Filtra `company_id` sempre (CLAUDE.md §7)."""
    if not company_id or not user_id:
        return False
    try:
        vinc = (supa.table("company_members").select("user_id, company_id, status")
                .eq("company_id", str(company_id)).eq("user_id", str(user_id)).eq("status", "active")
                .limit(1).execute())
        if not [v for v in (vinc.data or []) if str(v.get("company_id")) == str(company_id)
                and str(v.get("user_id")) == str(user_id) and v.get("status") == "active"]:
            return False
        usr = supa.table("users_v2").select("id, status, deleted_at").eq("id", str(user_id)).limit(1).execute()
        linhas = [u for u in (usr.data or []) if str(u.get("id")) == str(user_id)]
        return bool(linhas) and linhas[0].get("status") == "active" and not linhas[0].get("deleted_at")
    except Exception as exc:  # noqa: BLE001
        logger.warning("[MC] não consegui conferir a dona de um Agger (%s) — a conta não é usada", type(exc).__name__)
        return False


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
             ignorar: Iterable[str] = (), somente: Optional[str] = None,
             continuacao: bool = False, servico: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """A conta-robô que vai rodar `quantos` cálculos desta corretora — com a lease JÁ tomada — ou None.

    Percorre as candidatas (a menos usada primeiro); a ocupada por outro motor perde o CAS e a próxima
    é tentada. `ocupada` com o prazo vencido volta a `ativo` ao ser tomada — por CAS: se o Founder a
    pausou nesse meio tempo, ela NÃO volta e a lease é devolvida (conserto 129-B, red B1).

    `somente` (conserto 129-B, juiz P11): o grupo já tem negócio aberto numa conta — só ELA serve. A
    econômica nunca abre negócio novo noutra conta; sem ela livre, o grupo espera.

    `continuacao` (SPEC-129-C F0): o trabalho já começou — a janela não o segura (ver `conta_elegivel`).

    `servico` (SPEC-131-0 A · F3): o do pedido. Com `somente` = a conta EXIGIDA pelo cálculo (`conta_exigida_id`), só
    ela serve — nunca outra, nem a da corretora. O Agger de uma pessoa reconfere a dona AQUI, no banco, a cada escolha."""
    agora = agora or _agora()
    pulo = set(ignorar or ())
    for conta in candidatos(supa, corretora_id, somente=somente):
        if conta["id"] in pulo or (somente is not None and str(conta["id"]) != str(somente)):
            continue
        dono_ativo = (membro_ativo(supa, corretora_id, conta.get("dono_user_id"))
                      if conta.get("uso") == MEMBRO else None)
        ok, _motivo = conta_elegivel(conta, origem, agora, canario=canario, continuacao=continuacao,
                                     servico=servico, somente=somente, dono_ativo=dono_ativo)
        if not ok:
            continue
        feitos = calculos_na_ultima_hora(supa, company_id=corretora_id, account_id=conta["id"], agora=agora)
        if feitos + max(1, int(quantos)) > teto_da_conta(conta):
            logger.warning("[MC] robô %s no teto por hora (%s)", conta["id"], teto_da_conta(conta))
            continue
        if not adquirir(supa, conta, dono, agora, lease_s):
            continue
        if conta.get("robo_estado") == OCUPADA:
            r = (supa.table("portal_accounts").update({"robo_estado": ATIVO, "robo_ocupada_ate": None})
                 .eq("id", conta["id"]).eq("company_id", corretora_id).eq("robo_dono", dono)
                 .eq("robo_estado", OCUPADA).lt("robo_ocupada_ate", _iso(agora)).execute())
            if not r.data:
                # o estado mudou entre a leitura e o CAS (o Founder pausou, o gatilho da senha pausou):
                # a conta NÃO é usada e a lease volta
                liberar(supa, conta, dono)
                continue
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


# 🔴 As transições que o MOTOR pode fazer (conserto 129-B, red B1). Cada uma é um CAS com o estado de ORIGEM:
# o motor grava só se a conta AINDA está no estado em que ele a leu. `pausado` e `bloqueado` NUNCA saem daqui —
# só o comando do Founder (`comando_robo religar`) os desfaz. Sem isto, o motor que leu `ativo` antes da pausa do
# Founder (ou do gatilho de senha trocada) gravava `ocupada` por cima — e 30 min depois a conta voltava a `ativo`.
#   ativo → ocupada ............ uma pessoa entrou com o login do robô (SessaoOcupada)
#   ativo|ocupada|teste → bloqueado   senha recusada (1 tentativa). `teste` entra: login de pessoa recusado
#                                     também nunca se retenta
#   teste → pausado ............ a conta de PESSOA estava em uso, ou o login dela não teve desfecho (D-129B-04)
#   ocupada → ativo ............ só em `escolher`, com o prazo vencido (o CAS de lá também confere o prazo)
# SPEC-131-0 A · F3: o Agger de uma PESSOA (`uso='membro'`) vive em `ativo` e usa as MESMAS transições — a diferença é
# do motor, por USO: sessão ativa → `ocupada` 30 min e o cálculo volta (na 3ª, falha com o motivo); senha recusada →
# `bloqueado` na 1ª e o cálculo FALHA (nenhuma outra conta serve a ele). Nunca `pausado` pelo motor (só `teste`): quem
# pausa o Agger de uma pessoa é ela ou o admin, pela tela.
TRANSICOES_DO_MOTOR: Dict[str, tuple] = {
    OCUPADA: (ATIVO,),
    BLOQUEADO: (ATIVO, OCUPADA, TESTE),
    PAUSADO: (TESTE,),
}


def marcar_estado(supa, conta: Dict[str, Any], estado: str, *, agora: Optional[datetime] = None,
                  ocupada_min: Optional[int] = None) -> bool:
    """CAS do estado da conta, a partir do estado em que o motor a LEU (`conta['robo_estado']`).
    Devolve se gravou. Transição fora de `TRANSICOES_DO_MOTOR` → `ValueError` (nada é gravado)."""
    if estado not in ESTADOS:
        raise ValueError(f"estado de robô desconhecido: {estado!r}")
    de = conta.get("robo_estado")
    if de not in TRANSICOES_DO_MOTOR.get(estado, ()):
        raise ValueError(f"o motor não faz a transição {de!r} → {estado!r}")
    patch: Dict[str, Any] = {"robo_estado": estado}
    if estado == OCUPADA:
        patch["robo_ocupada_ate"] = _iso((agora or _agora()) + timedelta(minutes=int(ocupada_min or 30)))
    r = (supa.table("portal_accounts").update(patch)
         .eq("id", conta["id"]).eq("company_id", conta["company_id"]).eq("robo_estado", de).execute())
    if not r.data:
        logger.warning("[MC] robô %s mudou de estado por fora (não era mais %s) — %s não gravado",
                       conta.get("id"), de, estado)
        return False
    return True


def conta_publica(conta: Dict[str, Any]) -> Dict[str, Any]:
    """O que a sessão recebe da conta: tudo, MENOS o segredo cifrado e a lease."""
    return {k: v for k, v in conta.items()
            if k not in ("secret_encrypted", "robo_dono", "robo_batida_em")}


__all__: tuple = (
    "PORTAL_KEY", "ESTADOS", "ATIVO", "PAUSADO", "BLOQUEADO", "OCUPADA", "TESTE",
    "GLOBAL", "MEMBRO", "USO_TESTE", "USOS", "SERVICOS_DA_PESSOA", "membro_ativo",
    "TETO_PADRAO_POR_HORA", "LEASE_VENCE_S", "dentro_da_janela", "conta_elegivel", "teto_da_conta",
    "calculos_na_ultima_hora", "candidatos", "adquirir", "escolher", "renovar", "liberar",
    "marcar_estado", "conta_publica", "TRANSICOES_DO_MOTOR",
)

