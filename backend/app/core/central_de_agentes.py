"""A Central de Agentes diz a verdade — o leitor de PRODUÇÃO e de TRABALHO (SPEC-088 B+C).

O `heartbeat.py` responde *"o laço pulsou?"*. Este módulo responde as duas perguntas que
faltavam: *"o trabalho aconteceu?"* e *"quanto trabalho, com que resultado?"*.

```
🟢 SAUDAVEL             pulsou E produziu dentro de k × cadência DELE
🟡 PULSA_SEM_PRODUZIR   o laço roda e a produção passou do limiar        ← o Garimpo hoje
⚪ DESLIGADO            declarado em `desligado_quando` E o fato vale no banco
🔴 PARADO               devia pulsar na cadência dele e não pulsa — inclui chave EXPIRADA
⚫ NAO_MEDIDO           sem fonte declarada, ou sem cadência declarada
```

⛔ **Zero migration, zero tabela nova.** A produção sai de `max(coluna)` das tabelas que os
agentes já escrevem; o trabalho sai de `work_runs` e das três tabelas já indexadas por
`work_run_id`. O estado é calculado na leitura, com **uma** chave de cache no Redis (60s).

⛔ **Nada de conteúdo atravessa** (SPEC-088 §3 ⑦): contagens, estados, ids e timestamps.
O `motivo` é prosa gerada por template fixo — só números, datas e nomes de tabela. Nenhum
campo de conversa é interpolado em lugar nenhum deste arquivo.

Duas metades, de propósito:
  · `classificar()` e as auxiliares de formato são **puras** — o guarda as roda com fixture;
  · `carregar_estado()` faz o I/O (Supabase + Redis) e o cache.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.core.heartbeat import (AGENT_TASKS, GRUPOS, SEM_CARD_POR_DECISAO, Agente,
                                agente_por_id, read_all, workflow_keys_sem_card)

logger = logging.getLogger(__name__)

CACHE_KEY = "spec088:central:v1"
CACHE_S = 60

ESTADOS = ("SAUDAVEL", "PULSA_SEM_PRODUZIR", "DESLIGADO", "PARADO", "NAO_MEDIDO")

_JANELA_30D = 30 * 86400
_JANELA_7D = 7 * 86400
_JANELA_24H = 86400

# Teto de páginas de `work_runs` (1.000 linhas por página). 📊 2.679 linhas em 30 dias
# em 03/09/2026 — três páginas hoje, seis de folga.
_PAGINAS_WORK_RUNS = 6
_PAGINA = 1000


# --------------------------------------------------------------------------- #
# Puro: tempo, formato e filtro
# --------------------------------------------------------------------------- #
def parse_iso(valor: Any) -> Optional[datetime]:
    """Aceita o que o Postgres e o Redis devolvem; None quando não dá para ler."""
    if not valor:
        return None
    if isinstance(valor, datetime):
        return valor if valor.tzinfo else valor.replace(tzinfo=timezone.utc)
    s = str(valor).strip()
    if not s:
        return None
    s = s.replace(" ", "T")
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    s = re.sub(r"([+-]\d{2})$", r"\1:00", s)
    # microssegundos com mais de 6 dígitos derrubam o fromisoformat de algumas versões
    s = re.sub(r"(\.\d{6})\d+", r"\1", s)
    try:
        dt = datetime.fromisoformat(s)
    except Exception:  # noqa: BLE001
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z") if dt else None


def idade_humana(segundos: float) -> str:
    """`8 dias`, `6 h`, `35 min`, `12s` — só número e unidade."""
    s = max(0.0, float(segundos))
    if s < 90:
        return f"{int(s)}s"
    if s < 5400:
        return f"{int(round(s / 60))} min"
    if s < 172800:
        return f"{int(round(s / 3600))} h"
    return f"{int(round(s / 86400))} dias"


def cadencia_humana(segundos: Optional[int]) -> str:
    if not segundos:
        return "não declarada"
    if segundos % 86400 == 0:
        n = segundos // 86400
        return "1 dia" if n == 1 else f"{n} dias"
    if segundos % 3600 == 0:
        n = segundos // 3600
        return "1 hora" if n == 1 else f"{n} horas"
    n = max(1, segundos // 60)
    return "1 minuto" if n == 1 else f"{n} minutos"


def data_curta(dt: Optional[datetime]) -> str:
    return dt.astimezone(timezone.utc).strftime("%d/%m") if dt else "nunca"


def linha_casa_filtro(linha: Dict[str, Any], filtro: Optional[Dict[str, Any]]) -> bool:
    """O MESMO filtro que a fonte declara, aplicado a uma linha já em memória.

    🔴 É por aqui que o console `/admin/insights` passa a ler o registro em vez de ter
    a string `"garimpo"` escrita no código (📊 o banco só tem `garimpo_v3`).
    """
    if not filtro:
        return True
    valor = linha.get(str(filtro.get("coluna") or ""))
    alvo = filtro.get("valor")
    op = str(filtro.get("op") or "eq")
    if valor is None:
        return False
    if op == "eq":
        return str(valor) == str(alvo)
    if op == "in":
        return str(valor) in {str(v) for v in (alvo or ())}
    if op == "like":
        padrao = "^" + re.escape(str(alvo)).replace("%", ".*").replace("_", ".") + "$"
        return re.match(padrao, str(valor)) is not None
    return False


def filtro_de_fonte(agent_id: str, tabela: str) -> Optional[Dict[str, Any]]:
    """O filtro que o trabalhador `agent_id` declara sobre `tabela` (ou None)."""
    a = agente_por_id(agent_id)
    for f in (a.fonte_de_producao or ()) if a else ():
        if f.tipo == "tabela" and f.tabela == tabela:
            return f.filtro
    return None


def limiar_s(agente: Agente) -> Optional[int]:
    """k × cadência DELE. `None` quando não há cadência declarada — e aí não se inventa uma."""
    if not agente.cadencia_esperada_s:
        return None
    return int(agente.cadencia_esperada_s) * int(agente.k or 2)


# --------------------------------------------------------------------------- #
# 🔴 BLOCO B — a classificação, pura e testável com fixture
# --------------------------------------------------------------------------- #
def classificar(agente: Agente, pulso_iso: Any, producao_iso: Any, agora: datetime,
                desligado_flag: Optional[bool], contexto: Optional[Dict[str, Any]] = None
                ) -> Tuple[str, str]:
    """Devolve `(estado, motivo)`. Sem I/O — o guarda a roda com fixture.

    A ordem importa e é a dos gates da SPEC-088 BLOCO B:
      1. ⚪ DESLIGADO só para quem DECLARA `desligado_quando` e cujo fato vale no banco.
         Quem não declara **nunca** fica ⚪ — a dúvida paga do lado de quem alerta (ref. ⑤).
      2. ⚫ NAO_MEDIDO quando falta fonte ou falta cadência. Nunca 🟢 (o `no_policy` do Dagster).
      3. as duas medições, contra k × cadência DELE — nunca contra um limiar global de 900s.
    """
    ctx = contexto or {}

    if agente.desligado_quando and desligado_flag:
        inativas, total = ctx.get("attendance_inativas"), ctx.get("attendance_total")
        desde = ctx.get("desligado_desde")
        quando = f"desde {data_curta(parse_iso(desde))}" if desde else "sem registro de quando"
        if inativas is not None and total:
            return "DESLIGADO", (f"atendimento inativo em {int(inativas)} de {int(total)} "
                                 f"corretoras; {quando}")
        return "DESLIGADO", f"atendimento inativo em todas as corretoras; {quando}"

    if not agente.fonte_de_producao:
        return "NAO_MEDIDO", "sem tabela própria de produção — nenhum card verde sai daqui"
    if not agente.cadencia_esperada_s:
        rotulos = " ∪ ".join(f.rotulo for f in agente.fonte_de_producao)
        return "NAO_MEDIDO", f"fonte declarada ({rotulos}) e cadência esperada não declarada"

    limiar = int(limiar_s(agente) or 0)
    pulso = parse_iso(pulso_iso)
    producao = parse_iso(producao_iso)
    idade_pulso = (agora - pulso).total_seconds() if pulso else None
    idade_prod = (agora - producao).total_seconds() if producao else None
    pulso_ok = idade_pulso is not None and idade_pulso <= limiar
    prod_ok = idade_prod is not None and idade_prod <= limiar

    cad = cadencia_humana(agente.cadencia_esperada_s)
    rotulos = " ∪ ".join(f.rotulo for f in agente.fonte_de_producao)
    execs = ctx.get("execucoes_7d")
    prefixo = (f"{int(execs)} execuções completas em 7 dias; " if execs else "")

    if pulso_ok and prod_ok:
        return "SAUDAVEL", (f"{prefixo}pulsou há {idade_humana(idade_pulso)}; "
                            f"produziu em {rotulos} há {idade_humana(idade_prod)}; "
                            f"cadência esperada {cad}")
    if pulso_ok and not prod_ok:
        quanto = (f"última produção em {data_curta(producao)} ({idade_humana(idade_prod)})"
                  if producao else f"nunca produziu em {rotulos}")
        return "PULSA_SEM_PRODUZIR", (f"{prefixo}pulsou há {idade_humana(idade_pulso)}; "
                                      f"{quanto}; cadência esperada {cad}, "
                                      f"limiar {idade_humana(limiar)}")
    sem_pulso = (f"sem pulso há {idade_humana(idade_pulso)}"
                 if idade_pulso is not None else "sem pulso registrado (chave ausente ou expirada)")
    quanto = (f"última produção em {data_curta(producao)} ({idade_humana(idade_prod)})"
              if producao else f"nunca produziu em {rotulos}")
    return "PARADO", (f"{sem_pulso}; {quanto}; cadência esperada {cad}, "
                      f"limiar {idade_humana(limiar)}")


_PLURAL = {
    "PULSA_SEM_PRODUZIR": ("pulsa sem produzir", "pulsam sem produzir"),
    "DESLIGADO": ("desligado", "desligados"),
    "PARADO": ("parado", "parados"),
    "NAO_MEDIDO": ("não medido", "não medidos"),
}


def resumo_do_grupo(estados: List[str]) -> str:
    """`3 de 8 saudáveis · 1 pulsa sem produzir · 2 não medidos` — o que se lê em 3 segundos."""
    total = len(estados)
    saudaveis = sum(1 for e in estados if e == "SAUDAVEL")
    partes = [f"{saudaveis} de {total} saudáveis" if total != 1
              else f"{saudaveis} de 1 saudável"]
    for estado in ("PULSA_SEM_PRODUZIR", "PARADO", "DESLIGADO", "NAO_MEDIDO"):
        n = sum(1 for e in estados if e == estado)
        if n:
            sing, plur = _PLURAL[estado]
            partes.append(f"{n} {sing if n == 1 else plur}")
    return " · ".join(partes)


# --------------------------------------------------------------------------- #
# I/O — uma leitura por tabela, tudo dentro do cache de 60s
# --------------------------------------------------------------------------- #
def _seguro(fn, padrao):
    try:
        return fn()
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[CENTRAL-088] leitura falhou ({type(e).__name__})")
        return padrao


def _aplicar_filtro(q, filtro: Optional[Dict[str, Any]]):
    if not filtro:
        return q
    col, op, val = str(filtro.get("coluna")), str(filtro.get("op") or "eq"), filtro.get("valor")
    if op == "eq":
        return q.eq(col, val)
    if op == "like":
        return q.like(col, str(val))
    if op == "in":
        return q.in_(col, list(val or ()))
    return q


def _max_coluna(cli, tabela: str, coluna: str, filtro: Optional[Dict[str, Any]]) -> Optional[datetime]:
    """`max(coluna)` da tabela que o agente JÁ escreve. Uma linha, um índice, sem varredura.

    ⚠️ `ORDER BY col DESC` no Postgres é NULLS FIRST: sem o `is not null` a consulta
    devolveria uma linha nula e o agente pareceria nunca ter produzido.
    """
    def _ler():
        q = _aplicar_filtro(cli.table(tabela).select(coluna), filtro)
        try:
            q = q.not_.is_(coluna, "null")
        except Exception:  # noqa: BLE001
            pass
        return q.order(coluna, desc=True).limit(1).execute().data or []

    linhas = _seguro(_ler, [])
    return parse_iso(linhas[0].get(coluna)) if linhas else None


def _ler_tudo_sincrono() -> Dict[str, Any]:
    """Todas as consultas de uma vez, numa thread só. Só SELECT — nada aqui escreve."""
    from app.core.database import get_supabase_client

    cli = get_supabase_client().client
    agora = datetime.now(timezone.utc)
    d30 = (agora - timedelta(seconds=_JANELA_30D)).isoformat()

    # ---- agents: o fato do ⚪ DESLIGADO ------------------------------------ #
    attendance = _seguro(lambda: cli.table("agents")
                         .select("agent_role, is_active, desligado_em")
                         .eq("agent_role", "attendance").execute().data or [], [])

    # ---- work_runs 30d: o eixo do TRABALHO, paginado ---------------------- #
    runs: List[Dict[str, Any]] = []
    for pagina in range(_PAGINAS_WORK_RUNS):
        inicio = pagina * _PAGINA
        lote = _seguro(lambda i=inicio: cli.table("work_runs")
                       .select("id, workflow_key, status, created_at, started_at, "
                               "finished_at, unblock_state")
                       .gte("created_at", d30)
                       .order("created_at", desc=True)
                       .range(i, i + _PAGINA - 1).execute().data or [], [])
        runs.extend(lote)
        if len(lote) < _PAGINA:
            break

    # ---- custo: existe UM run com custo > 0 em toda a tabela? ------------- #
    # 📊 03/09/2026: zero em 3.494 runs → `custo_brl_30d` é null e "custo" entra
    # em `nao_instrumentado`. Zero que vem de coluna nunca escrita não é zero (P-088-CUSTO).
    custo_instrumentado = _seguro(
        lambda: bool(cli.table("work_runs").select("id").gt("cost_actual_brl", 0)
                     .limit(1).execute().data or []), False)

    # ---- artifacts 30d: a entrega, ligada por work_run_id ----------------- #
    artefatos = _seguro(lambda: cli.table("artifacts").select("work_run_id, created_at")
                        .gte("created_at", d30).limit(2000).execute().data or [], [])

    # ---- approval_requests: e a honestidade do join ----------------------- #
    aprovacoes = _seguro(lambda: cli.table("approval_requests")
                         .select("status, work_run_id").limit(2000).execute().data or [], [])

    # ---- as fontes de produção, uma consulta por (tabela, coluna, filtro) -- #
    producoes: Dict[str, Optional[datetime]] = {}
    vistos: set = set()
    for agente in AGENT_TASKS:
        for f in agente.fonte_de_producao or ():
            if f.tipo != "tabela":
                continue
            for coluna in f.colunas:
                chave = _chave_fonte(f.tabela, coluna, f.filtro)
                if chave in vistos:
                    continue
                vistos.add(chave)
                producoes[chave] = _max_coluna(cli, f.tabela or "", coluna, f.filtro)

    return {"agora": agora, "attendance": attendance, "runs": runs, "artefatos": artefatos,
            "aprovacoes": aprovacoes, "producoes": producoes,
            "custo_instrumentado": custo_instrumentado}


def _chave_fonte(tabela: Optional[str], coluna: str, filtro: Optional[Dict[str, Any]]) -> str:
    """A identidade de uma consulta de fonte: tabela + coluna + filtro declarado.

    ⚠️ Nada de `str.format()` aqui: o filtro serializado tem chaves `{}` e o format
    as leria como campo de substituição.
    """
    return f"{tabela}|{coluna}|{json.dumps(filtro, sort_keys=True, default=str)}"


def _agregar_runs(runs: List[Dict[str, Any]], agora: datetime) -> Dict[str, Dict[str, Any]]:
    """Por `workflow_key`: contagens, durações, travados e o último `completed`."""
    por_chave: Dict[str, Dict[str, Any]] = {}
    for r in runs:
        chave = str(r.get("workflow_key") or "")
        if not chave:
            continue
        d = por_chave.setdefault(chave, {
            "execucoes_24h": 0, "execucoes_7d": 0, "execucoes_30d": 0, "falhas_7d": 0,
            "travados": 0, "duracoes": [], "filas": [], "ultimo_completed": None,
            "ids_completed": set(), "ids": set(),
        })
        criado = parse_iso(r.get("created_at"))
        idade = (agora - criado).total_seconds() if criado else None
        d["execucoes_30d"] += 1
        d["ids"].add(str(r.get("id")))
        if idade is not None and idade <= _JANELA_24H:
            d["execucoes_24h"] += 1
        if idade is not None and idade <= _JANELA_7D:
            d["execucoes_7d"] += 1
            if str(r.get("status")) == "failed":
                d["falhas_7d"] += 1
        if str(r.get("unblock_state") or "") == "travado":
            d["travados"] += 1
        iniciado, terminado = parse_iso(r.get("started_at")), parse_iso(r.get("finished_at"))
        # ⚠️ Diferença negativa é relógio, não trabalho: 📊 `acionamento.seguradora` tem
        # `fila_s = -0,2`. Ela é ANCORADA em zero, não DESCARTADA — descartar deixava o
        # campo `null`, e `null` no contrato quer dizer "não instrumentado". Um run que
        # existe nunca some da média.
        if iniciado and terminado:
            d["duracoes"].append(max(0.0, (terminado - iniciado).total_seconds()))
        if criado and iniciado:
            d["filas"].append(max(0.0, (iniciado - criado).total_seconds()))
        if str(r.get("status")) == "completed":
            d["ids_completed"].add(str(r.get("id")))
            if terminado and (d["ultimo_completed"] is None or terminado > d["ultimo_completed"]):
                d["ultimo_completed"] = terminado
    return por_chave


def _media(valores: List[float]) -> Optional[float]:
    return round(sum(valores) / len(valores), 1) if valores else None


def _montar(bruto: Dict[str, Any], pulsos: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    agora: datetime = bruto["agora"]
    runs = bruto["runs"]
    por_chave = _agregar_runs(runs, agora)
    run_para_chave = {str(r.get("id")): str(r.get("workflow_key") or "") for r in runs}

    # artifacts por workflow_key (7d e 30d) — o 30d serve à FONTE do briefing
    art_7d: Dict[str, int] = {}
    art_ultimo: Dict[str, datetime] = {}
    for a in bruto["artefatos"]:
        chave = run_para_chave.get(str(a.get("work_run_id") or ""))
        if not chave:
            continue  # 📊 P-088-ARTIFACTS: 33 de 118 sem work_run_id — entrega órfã
        criado = parse_iso(a.get("created_at"))
        if criado and (agora - criado).total_seconds() <= _JANELA_7D:
            art_7d[chave] = art_7d.get(chave, 0) + 1
        if criado and (chave not in art_ultimo or criado > art_ultimo[chave]):
            art_ultimo[chave] = criado

    # 🔴 aprovações: o join só é honesto se TODA linha existente tiver work_run_id.
    # 📊 03/09/2026: 8 linhas, 0 com work_run_id (2º escritor `billing_collection.py:789`
    # não passa o id) → o join dá zero estrutural. Zero de join que não casa é `null`.
    linhas_aprov = bruto["aprovacoes"]
    aprov_confiavel = bool(linhas_aprov) and all(a.get("work_run_id") for a in linhas_aprov)
    pendentes: Dict[str, int] = {}
    if aprov_confiavel:
        for a in linhas_aprov:
            if str(a.get("status")) != "pending":
                continue
            chave = run_para_chave.get(str(a.get("work_run_id") or ""))
            if chave:
                pendentes[chave] = pendentes.get(chave, 0) + 1

    # ⚪ o fato do DESLIGADO — agregado da plataforma, sem dado por corretora
    attendance = bruto["attendance"]
    inativas = sum(1 for a in attendance if a.get("is_active") is False)
    total_att = len(attendance)
    todas_desligadas = bool(attendance) and inativas == total_att
    desligados_em = [parse_iso(a.get("desligado_em")) for a in attendance if a.get("desligado_em")]
    desligado_desde = max([d for d in desligados_em if d], default=None)

    nao_instrumentado: List[str] = []
    if not bruto["custo_instrumentado"]:
        nao_instrumentado.append("custo")
    if not aprov_confiavel:
        nao_instrumentado.append("aprovacoes")

    por_grupo: Dict[str, List[Dict[str, Any]]] = {g[0]: [] for g in GRUPOS}

    for agente in AGENT_TASKS:
        chaves = tuple(agente.eixo.get("workflow_keys") or ())

        # ---- produção: max() de todas as fontes declaradas ----------------- #
        producao: Optional[datetime] = None
        rotulos: List[str] = []
        for f in agente.fonte_de_producao or ():
            rotulos.append(f.rotulo)
            candidatos: List[Optional[datetime]] = []
            if f.tipo == "tabela":
                for coluna in f.colunas:
                    candidatos.append(
                        bruto["producoes"].get(_chave_fonte(f.tabela, coluna, f.filtro)))
            elif f.tipo == "work_runs_do_eixo":
                candidatos = [por_chave.get(k, {}).get("ultimo_completed") for k in chaves]
            elif f.tipo == "artifacts_do_eixo":
                candidatos = [art_ultimo.get(k) for k in chaves]
            for c in candidatos:
                if c and (producao is None or c > producao):
                    producao = c

        # ---- pulso: Redis OU work_runs, nunca os dois competindo ----------- #
        origem = str(agente.eixo.get("pulso") or "redis")
        pulso_redis = pulsos.get(agente.id, {})
        if origem == "work_runs":
            candidatos_pulso = [por_chave.get(k, {}).get("ultimo_completed") for k in chaves]
            pulso = max([c for c in candidatos_pulso if c], default=None)
        else:
            pulso = parse_iso(pulso_redis.get("last_run"))

        # ---- trabalho: só para quem tem eixo ------------------------------- #
        trabalho = None
        execucoes_24h = 0
        if chaves:
            somas = [por_chave.get(k, {}) for k in chaves]
            execucoes_24h = sum(int(s.get("execucoes_24h") or 0) for s in somas)
            duracoes = [v for s in somas for v in (s.get("duracoes") or [])]
            filas = [v for s in somas for v in (s.get("filas") or [])]
            trabalho = {
                "eixo": list(chaves),
                "execucoes_24h": execucoes_24h,
                "execucoes_7d": sum(int(s.get("execucoes_7d") or 0) for s in somas),
                "falhas_7d": sum(int(s.get("falhas_7d") or 0) for s in somas),
                # ⚠️ duração e fila são da janela de 30 DIAS (a mesma do BLOCO 0 ④ da
                # SPEC), não de 7: com 7 dias um agente que roda 4× por mês não teria média.
                "duracao_media_s": _media(duracoes),
                "fila_media_s": _media(filas),
                "artifacts_7d": sum(int(art_7d.get(k, 0)) for k in chaves),
                "aprovacoes_pendentes": (sum(int(pendentes.get(k, 0)) for k in chaves)
                                         if aprov_confiavel else None),
                "travados": sum(int(s.get("travados") or 0) for s in somas),
                # 📊 sum(cost_actual_brl) = 0 em 100% dos runs → null, nunca 0 (P-088-CUSTO)
                "custo_brl_30d": None,
            }

        contexto = {
            "execucoes_7d": (trabalho or {}).get("execucoes_7d"),
            "attendance_inativas": inativas, "attendance_total": total_att,
            "desligado_desde": _iso(desligado_desde),
        }
        estado, motivo = classificar(agente, _iso(pulso), _iso(producao), agora,
                                     todas_desligadas, contexto)

        por_grupo.setdefault(agente.grupo, []).append({
            "id": agente.id, "nome": agente.nome, "descricao": agente.descricao,
            "cor": agente.cor, "grupo": agente.grupo,
            "estado": estado, "motivo": motivo,
            "pulso": {"ultimo": _iso(pulso), "origem": origem},
            "producao": {"ultimo": _iso(producao),
                         "fonte": " ∪ ".join(rotulos) if rotulos else None,
                         "cadencia_esperada_s": agente.cadencia_esperada_s,
                         "limiar_s": limiar_s(agente)},
            "desligado": {"declara": bool(agente.desligado_quando),
                          "todas_desligadas": (todas_desligadas if agente.desligado_quando else None),
                          "desde": (_iso(desligado_desde) if agente.desligado_quando else None)},
            "trabalho": trabalho,
            "acoes_hoje": (execucoes_24h if origem == "work_runs"
                           else int(pulso_redis.get("actions_today") or 0)),
        })

    grupos = []
    for gid, titulo, proposito in GRUPOS:
        cartoes = por_grupo.get(gid, [])
        grupos.append({"id": gid, "titulo": titulo, "proposito": proposito,
                       "resumo": resumo_do_grupo([c["estado"] for c in cartoes]),
                       "agentes": cartoes})

    # 🔴 Um agente cujo grupo não está em GRUPOS NÃO pode sumir em silêncio — é a
    # §1.6 da SPEC-088 reconstruída (a lista que não sabe do agente novo é a que
    # mente). Ele sai num grupo sintético que o frontend pinta de vermelho.
    conhecidos = {g[0] for g in GRUPOS}
    for gid in sorted(set(por_grupo) - conhecidos):
        cartoes = por_grupo[gid]
        logger.warning("central_de_agentes: %d agente(s) com grupo desconhecido %r", len(cartoes), gid)
        grupos.append({"id": gid, "titulo": "SEM GRUPO", "proposito": "grupo desconhecido: %s" % gid,
                       "resumo": resumo_do_grupo([c["estado"] for c in cartoes]),
                       "agentes": cartoes})

    orfas = workflow_keys_sem_card(sorted(por_chave.keys()))
    if orfas:
        # Não derruba a rota: o gate ② do BLOCO A é do guarda. Aqui fica o rastro.
        logger.warning(f"[CENTRAL-088] workflow_key sem card nem decisão: {orfas}")

    return {
        "gerado_em": _iso(agora), "cache_s": CACHE_S,
        "grupos": grupos,
        "nao_instrumentado": nao_instrumentado,
        "sem_card_por_decisao": [{"workflow_key": k, "motivo": m} for k, m in SEM_CARD_POR_DECISAO],
    }


async def calcular_estado() -> Dict[str, Any]:
    """O contrato da §4 da SPEC-088, calculado do zero (sem cache)."""
    pulsos_lista = await read_all()
    pulsos = {p["id"]: p for p in pulsos_lista}
    bruto = await asyncio.to_thread(_ler_tudo_sincrono)
    return _montar(bruto, pulsos)


async def carregar_estado() -> Dict[str, Any]:
    """A resposta da rota, com UMA chave de cache de plataforma (60s).

    📊 A tela recarrega a cada 20s: sem o cache seriam ~20 consultas × 3/min contra
    produção. Sem Redis, calcula direto — o cache é otimização, não dependência.
    """
    try:
        from app.core.redis import get_async_redis_client

        redis = await get_async_redis_client()
        cru = await redis.get(CACHE_KEY)
        if cru:
            return json.loads(cru.decode() if isinstance(cru, (bytes, bytearray)) else cru)
    except Exception as e:  # noqa: BLE001
        logger.debug(f"[CENTRAL-088] cache indisponível: {type(e).__name__}")

    estado = await calcular_estado()

    try:
        from app.core.redis import get_async_redis_client

        redis = await get_async_redis_client()
        await redis.set(CACHE_KEY, json.dumps(estado), ex=CACHE_S)
    except Exception as e:  # noqa: BLE001
        logger.debug(f"[CENTRAL-088] cache não gravado: {type(e).__name__}")
    return estado
