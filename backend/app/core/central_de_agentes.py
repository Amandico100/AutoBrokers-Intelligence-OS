"""A Central de Agentes diz a verdade — o leitor de PRODUÇÃO e de TRABALHO (SPEC-088 B+C).

O `heartbeat.py` responde *"o laço pulsou?"*. Este módulo responde as duas perguntas que
faltavam: *"o trabalho aconteceu?"* e *"quanto trabalho, com que resultado?"*.

```
🟢 SAUDAVEL             PRODUZIU dentro de k × cadência DELE (o pulso velho vira aviso
                        no motivo, não muda a cor: produzir é o fim, pulsar é o meio)
🟡 PULSA_SEM_PRODUZIR   o laço roda e a produção passou do limiar        ← o Garimpo hoje
⚪ DESLIGADO            mudo dos DOIS lados **e** `desligado_quando` verdadeiro — seja o
                        fato do banco (`agents_attendance_all_inactive`) ou a chave de
                        ambiente (`env_falso`, o gatilho do Founder no Alfaiate)
🔴 PARADO               devia pulsar na cadência DELE e não pulsa — inclui chave EXPIRADA
⚫ NAO_MEDIDO           sem fonte declarada, ou sem cadência declarada
```

🔴 **A ORDEM DE DECISÃO É `produção → pulso → declaração`, nesta ordem.** O contrário —
que era o código até 03/09/2026 — deixava o ⚪ vencer a evidência de trabalho: 📊 o
Follow-up roda a cada 60 s e pulsa incondicionalmente, e saía ⚪ DESLIGADO porque um
agente de ATENDIMENTO estava inativo. ⚪ é "não olhe para mim", e é a cor mais cara
para pintar em quem está trabalhando.

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

# 🔴 O TETO DO SERVIDOR É 1.000 LINHAS, E ELE NÃO AVISA.
#
# ⚠️ `.limit(2000)` não devolve 2.000: o PostgREST manda 1.000 e cala
# (`backend/tests/test_ninguem_pede_mais_de_mil_linhas_de_novo.py`). Era o que estava
# escrito em `artifacts` e `approval_requests` — e o efeito ali não é "faltam linhas":
# é `aprov_confiavel` decidido sobre um recorte, e `artifacts_7d` menor do que a verdade
# num painel cujo propósito inteiro é não mentir.
_PAGINA = 1000
# 📊 03/09/2026: work_runs 2.679 linhas em 30 dias · artifacts 118 · approval_requests 8.
# Os tetos têm folga de 2× a 6× sobre o medido, e quando estouram o campo entra em
# `nao_instrumentado` em vez de sair menor em silêncio.
_PAGINAS_WORK_RUNS = 6
_PAGINAS_ARTIFACTS = 4
_PAGINAS_APROVACOES = 2

#: 🔴 O PISO DO LIMIAR DE PULSO, e ele existe por causa do cache desta mesma rota.
#:
#: ⚠️ 📊 O Vigia pulsa a cada 20 s (`buffer_processor.py:113`); 20 × k=2 = 40 s. A
#: resposta fica 60 s no Redis (`CACHE_S`), então um card calculado no fim da janela
#: leria um pulso de até 60 s e o chamaria de morto. **Um limiar menor que o cache mede
#: o cache, não o agente.** 2 × 60 s é o piso.
_PISO_LIMIAR_PULSO_S = 2 * CACHE_S


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
    # ⚠️ Abaixo de um minuto o arredondamento MENTE: `cadencia_humana(20)` dizia
    # "1 minuto" para o laço do Vigia, que roda a cada 20 s — e é justamente o agente
    # cujo relógio o operador precisa reconhecer para saber se 40 s de silêncio é muito.
    if segundos < 60:
        return f"{int(segundos)} segundos"
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
    """k × cadência de PRODUÇÃO dele. `None` sem cadência — e aí não se inventa uma."""
    if not agente.cadencia_esperada_s:
        return None
    return int(agente.cadencia_esperada_s) * int(agente.k or 2)


def limiar_pulso_s(agente: Agente) -> Optional[int]:
    """k × cadência do LAÇO dele, com o piso do cache. `None` = o pulso não expira.

    🔴 Este é o conserto C3 da rodada de painel. Antes só existia o limiar de PRODUÇÃO,
    e quem não tinha cadência de produção não tinha limiar nenhum: o card ficava ⚫ NÃO
    MEDIDO mesmo com o laço morto há uma semana. 📊 Era o caso do Vigia/Sentinela — o
    agente que atende quem está esperando neste minuto **não conseguia ficar vermelho**.

    ⚠️ A ordem de fallback importa: `cadencia_pulso_s` primeiro (é o relógio do laço),
    `cadencia_esperada_s` depois (quando pulso e produção são a mesma coisa, como nos
    agentes cujo pulso É o eixo de `work_runs`). Sem nenhuma das duas, `None` — e um
    pulso que não expira nunca vira 🔴 por engano.
    """
    cadencia = getattr(agente, "cadencia_pulso_s", None) or agente.cadencia_esperada_s
    if not cadencia:
        return None
    return max(_PISO_LIMIAR_PULSO_S, int(cadencia) * int(agente.k or 2))


def _env_ligada(chave: str) -> bool:
    """⛔ NÃO é um leitor novo: delega ao único da casa (`core.feature_flags`)."""
    try:
        from app.core.feature_flags import env_ligada

        return env_ligada(str(chave))
    except Exception:  # noqa: BLE001
        return False


def condicao_desligado(agente: Agente, desligado_flag: Optional[bool],
                       contexto: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
    """`(o fato de desligamento vale?, a razão em prosa)` — puro, sem I/O de banco.

    Duas formas declaráveis, e nenhuma delas é uma frase solta no motivo:

      `{"agents_attendance_all_inactive": True}`  o fato vem do banco (`agents`)
      `{"env_falso": "ALFAIATE_AUTO_APPLY"}`      o fato vem da chave de ambiente

    🔴 A segunda é o conserto C7: 📊 `playbook_tailor.py:145` corta o Alfaiate antes do
    pulso quando `ALFAIATE_AUTO_APPLY` está ausente — e ela não está em config nenhuma.
    O card dizia 🔴 PARADO, e o operador procurava defeito onde havia decisão do Founder.
    """
    ctx = contexto or {}
    declarado = agente.desligado_quando or {}
    if not declarado:
        return False, ""
    chave = declarado.get("env_falso")
    if chave:
        if _env_ligada(str(chave)):
            return False, ""
        return True, "desligado pela chave %s" % chave
    if declarado.get("agents_attendance_all_inactive"):
        if not desligado_flag:
            return False, ""
        inativas, total = ctx.get("attendance_inativas"), ctx.get("attendance_total")
        if inativas is not None and total:
            return True, ("atendimento inativo em %d de %d corretoras"
                          % (int(inativas), int(total)))
        return True, "atendimento inativo em todas as corretoras"
    return False, ""


# --------------------------------------------------------------------------- #
# 🔴 BLOCO B — a classificação, pura e testável com fixture
# --------------------------------------------------------------------------- #
def classificar(agente: Agente, pulso_iso: Any, producao_iso: Any, agora: datetime,
                desligado_flag: Optional[bool], contexto: Optional[Dict[str, Any]] = None
                ) -> Tuple[str, str]:
    """Devolve `(estado, motivo)`. Sem I/O de banco — o guarda a roda com fixture.

    🔴 A ORDEM MUDOU NA RODADA DE CONSERTO, E A ORDEM ERA O DEFEITO.

    Antes, o ⚪ DESLIGADO era o primeiro portão: bastava `desligado_quando` valer para o
    card ficar cinza — **mesmo com o laço pulsando e produzindo neste minuto**. 📊 O
    Follow-up roda a cada 60 s (`buffer_processor.py:103`) e pulsa incondicionalmente ao
    fim da varredura (`dispatch_followup.py:371`), independente de qualquer agente de
    atendimento estar ativo. Chamar isso de "desligado" é a mesma classe de mentira que
    esta SPEC existe para matar, só que com a cor trocada -- e ⚪ é "não olhe para mim",
    a cor mais cara para pintar em quem está trabalhando.

    ⛔ **Evidência de trabalho vence declaração de desligamento.** A nova ordem:

    ```
    1. produziu dentro de k × cadência DELE          → 🟢 SAUDAVEL
                                                       (e se o pulso estiver velho, o
                                                        motivo DIZ isso — produzir é o fim,
                                                        pulsar é só o meio)
    2. senão, pulsou dentro do limiar de PULSO       → 🟡 PULSA_SEM_PRODUZIR (com fonte
                                                          E cadência declaradas)
                                                       ⚫ NAO_MEDIDO (sem uma das duas)
    3. senão — mudo dos dois lados:
         `desligado_quando` declarado e verdadeiro   → ⚪ DESLIGADO
         sem fonte e sem cadência de pulso           → ⚫ NAO_MEDIDO
         senão                                       → 🔴 PARADO
    ```

    ⚠️ O ⚪ continua existindo, e continua sendo o certo para quem está **mudo dos dois
    lados** com um motivo declarado — 📊 o Cérebro v2, que só decide quando a seguradora
    responde. O que morreu foi o ⚪ vencer o pulso.
    """
    ctx = contexto or {}
    desligado, razao_desligado = condicao_desligado(agente, desligado_flag, ctx)

    tem_fonte = bool(agente.fonte_de_producao)
    limiar_prod = limiar_s(agente)
    limiar_pulso = limiar_pulso_s(agente)

    pulso = parse_iso(pulso_iso)
    producao = parse_iso(producao_iso)
    idade_pulso = (agora - pulso).total_seconds() if pulso else None
    idade_prod = (agora - producao).total_seconds() if producao else None
    pulso_ok = (limiar_pulso is not None and idade_pulso is not None
                and idade_pulso <= limiar_pulso)
    prod_ok = (limiar_prod is not None and idade_prod is not None
               and idade_prod <= limiar_prod)

    # 🔴 O motivo é frase de produto (DS-001 §6.7): usa o rótulo HUMANO da fonte quando o
    # registro o declara; o técnico (`tabela.coluna (…)`) fica só em `producao.fonte`.
    # 📊 03/09: o juiz de confirmação leu "produziu em a produção dele (tecidos da
    # observação)" na tela — o filtro do frontend trocava o nome técnico e deixava o
    # parêntese órfão. A fonte da frase tem de nascer humana, não ser traduzida depois.
    rotulos = (getattr(agente, "fonte_rotulo", None)
               or " e ".join(f.rotulo for f in (agente.fonte_de_producao or ())))
    cad = cadencia_humana(agente.cadencia_esperada_s)
    execs = ctx.get("execucoes_7d")
    prefixo = (f"{int(execs)} execuções completas em 7 dias; " if execs else "")

    # ---- 1. A PRODUÇÃO É A VERDADE ---------------------------------------- #
    if tem_fonte and prod_ok:
        if pulso_ok:
            return "SAUDAVEL", (f"{prefixo}pulsou há {idade_humana(idade_pulso)}; "
                                f"produziu {rotulos} há {idade_humana(idade_prod)}; "
                                f"cadência esperada {cad}")
        # 🔴 Produziu, mas o pulso está velho ou ausente. Continua VERDE — o trabalho
        # chegou ao fim — e o motivo carrega o aviso em vez de esconder.
        aviso = (f"o pulso do laço está velho ({idade_humana(idade_pulso)})"
                 if idade_pulso is not None
                 else "o pulso do laço não está registrado")
        return "SAUDAVEL", (f"{prefixo}produziu {rotulos} há {idade_humana(idade_prod)}; "
                            f"cadência esperada {cad}; {aviso}")

    # ---- 2. O LAÇO ESTÁ VIVO ---------------------------------------------- #
    if pulso_ok:
        if tem_fonte and agente.cadencia_esperada_s:
            quanto = (f"última produção em {data_curta(producao)} ({idade_humana(idade_prod)})"
                      if producao else f"nunca produziu {rotulos}")
            return "PULSA_SEM_PRODUZIR", (
                f"{prefixo}pulsou há {idade_humana(idade_pulso)}; {quanto}; "
                f"cadência esperada {cad}, limiar {idade_humana(limiar_prod)}")
        falta = ("sem tabela própria de produção" if not tem_fonte
                 else f"fonte declarada ({rotulos}) e cadência esperada não declarada")
        return "NAO_MEDIDO", (f"pulsa há {idade_humana(idade_pulso)}; "
                              f"produção não medida — {falta}")

    # ---- 3. MUDO DOS DOIS LADOS ------------------------------------------- #
    if desligado:
        desde = ctx.get("desligado_desde")
        quando = f"desde {data_curta(parse_iso(desde))}" if desde else "sem registro de quando"
        return "DESLIGADO", f"{razao_desligado}; {quando}"

    if not tem_fonte and limiar_pulso is None:
        return "NAO_MEDIDO", ("sem tabela própria de produção e sem cadência de laço — "
                              "nenhum card verde sai daqui")
    if not tem_fonte:
        sem_pulso = (f"sem pulso há {idade_humana(idade_pulso)}" if idade_pulso is not None
                     else "sem pulso registrado (chave ausente ou expirada)")
        return "PARADO", (f"{sem_pulso}; sem tabela própria de produção; "
                          f"o laço devia pulsar a cada "
                          f"{cadencia_humana(getattr(agente, 'cadencia_pulso_s', None) or agente.cadencia_esperada_s)}, "
                          f"limiar {idade_humana(limiar_pulso)}")
    if not agente.cadencia_esperada_s and limiar_pulso is None:
        return "NAO_MEDIDO", (f"fonte declarada ({rotulos}) e cadência esperada não declarada")

    sem_pulso = (f"sem pulso há {idade_humana(idade_pulso)}"
                 if idade_pulso is not None else "sem pulso registrado (chave ausente ou expirada)")
    quanto = (f"última produção em {data_curta(producao)} ({idade_humana(idade_prod)})"
              if producao else f"nunca produziu {rotulos}")
    limiar_txt = (f"cadência esperada {cad}, limiar {idade_humana(limiar_prod)}"
                  if limiar_prod is not None
                  else f"cadência de laço {cadencia_humana(getattr(agente, 'cadencia_pulso_s', None))}, "
                       f"limiar {idade_humana(limiar_pulso)}")
    return "PARADO", f"{sem_pulso}; {quanto}; {limiar_txt}"


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


def _paginar(consulta, paginas: int) -> Tuple[List[Dict[str, Any]], bool]:
    """Lê `paginas` × 1.000 linhas. Devolve `(linhas, estourou_o_teto)`.

    🔴 `estourou` é a metade que faltava. Um teto que corta em silêncio produz o mesmo
    defeito que o `.limit(2000)` produzia: um número menor que a verdade, com cara de
    verdade. Quando a última página volta CHEIA, quem chama põe o campo em
    `nao_instrumentado` — a mesma regra do custo e das aprovações (§4).
    """
    linhas: List[Dict[str, Any]] = []
    for pagina in range(max(1, int(paginas))):
        inicio = pagina * _PAGINA
        lote = _seguro(lambda i=inicio: consulta(i, i + _PAGINA - 1), [])
        linhas.extend(lote)
        if len(lote) < _PAGINA:
            return linhas, False
    return linhas, True


def _vazio(agora: datetime, leitura_indisponivel: bool = False) -> Dict[str, Any]:
    return {"agora": agora, "attendance": [], "runs": [], "artefatos": [], "aprovacoes": [],
            "producoes": {}, "custo_instrumentado": False, "truncado": (),
            "leitura_indisponivel": leitura_indisponivel,
            "portal_contas": [], "portal_jobs": [], "portais": []}


def _ler_tudo_sincrono() -> Dict[str, Any]:
    """Todas as consultas de uma vez, numa thread só. Só SELECT — nada aqui escreve."""
    agora = datetime.now(timezone.utc)

    # 🔴 O CLIENTE TAMBÉM PODE FALHAR, e ele estava FORA da rede de segurança.
    #
    # ⚠️ `get_supabase_client()` valida settings e abre conexão: sem `SUPABASE_URL`, com
    # chave vencida ou com o Postgres fora do ar, ele LEVANTA — e a exceção subia pela
    # thread até a rota, que devolvia 500. **A Central de Agentes é a tela que se abre
    # justamente quando alguma coisa está errada**; ser a primeira a cair é o pior
    # comportamento possível. Agora a falha vira cards 🔴 PARADO / ⚫ NÃO MEDIDO com
    # "leitura indisponível" escrito no motivo.
    def _cliente():
        from app.core.database import get_supabase_client

        return get_supabase_client().client

    cli = _seguro(_cliente, None)
    if cli is None:
        logger.warning("[CENTRAL-088] cliente Supabase indisponível — a tela sai cinza, "
                       "com o motivo escrito, e nunca 500")
        return _vazio(agora, leitura_indisponivel=True)

    d30 = (agora - timedelta(seconds=_JANELA_30D)).isoformat()
    truncado: List[str] = []

    # ---- agents: o fato do ⚪ DESLIGADO ------------------------------------ #
    attendance = _seguro(lambda: cli.table("agents")
                         .select("agent_role, is_active, desligado_em")
                         .eq("agent_role", "attendance").execute().data or [], [])

    # ---- work_runs 30d: o eixo do TRABALHO, paginado ---------------------- #
    runs, estourou = _paginar(
        lambda a, b: cli.table("work_runs")
        .select("id, workflow_key, status, created_at, started_at, "
                "finished_at, unblock_state")
        .gte("created_at", d30).order("created_at", desc=True)
        .range(a, b).execute().data or [],
        _PAGINAS_WORK_RUNS)
    if estourou:
        truncado.append("trabalho")

    # ---- custo: existe UM run com custo > 0 em toda a tabela? ------------- #
    # 📊 03/09/2026: zero em 3.494 runs → `custo_brl_30d` é null e "custo" entra
    # em `nao_instrumentado`. Zero que vem de coluna nunca escrita não é zero (P-088-CUSTO).
    custo_instrumentado = _seguro(
        lambda: bool(cli.table("work_runs").select("id").gt("cost_actual_brl", 0)
                     .limit(1).execute().data or []), False)

    # ---- artifacts 30d: a entrega, ligada por work_run_id ----------------- #
    # 🔴 Era `.limit(2000)`, e 2.000 nunca chegariam: o servidor manda 1.000 e cala.
    artefatos, estourou = _paginar(
        lambda a, b: cli.table("artifacts").select("work_run_id, created_at")
        .gte("created_at", d30).order("created_at", desc=True)
        .range(a, b).execute().data or [],
        _PAGINAS_ARTIFACTS)
    if estourou:
        truncado.append("artifacts")

    # ---- approval_requests: e a honestidade do join ----------------------- #
    # ⚠️ Aqui o recorte era pior que faltar linha: `aprov_confiavel` é um `all()` sobre
    # a tabela INTEIRA. Decidido sobre 1.000 de N, ele responde outra pergunta.
    aprovacoes, estourou = _paginar(
        lambda a, b: cli.table("approval_requests").select("status, work_run_id")
        .order("created_at", desc=True).range(a, b).execute().data or [],
        _PAGINAS_APROVACOES)
    if estourou:
        truncado.append("aprovacoes")

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

    # ---- portais das seguradoras: saúde da conta + os jobs de 7 dias ------ #
    # 🔴 SPEC-EXTRA-001.6 B3.4-2. Agregado da PLATAFORMA: a Central é
    # master-admin e mostra contagens por PORTAL, nunca por corretora — nenhum
    # `company_id`, nenhum nome de cliente, nenhuma credencial sai daqui.
    d7 = (agora - timedelta(seconds=_JANELA_7D)).isoformat()
    portal_contas = _seguro(lambda: cli.table("portal_accounts")
                            .select("portal_key, health, updated_at")
                            .execute().data or [], [])
    # ⚠️ `tela:evidence->tela` traz o objeto INTEIRO da tela (texto redigido,
    # hash, url, caminho do print) — é ele que alimenta a fila de telas
    # desconhecidas. Sem esta coluna o card teria a frase e nenhum dado atrás
    # dela, que é a `tela_cega` outra vez, do lado do leitor.
    portal_jobs = _seguro(lambda: cli.table("portal_jobs")
                          .select("portal_key, journey, status, finished_at, "
                                  "evidence->>message, tela:evidence->tela")
                          .in_("journey", list(_JOURNEYS_DE_ACESSO))
                          .gte("created_at", d7)
                          .order("finished_at", desc=True)
                          .limit(_PAGINA).execute().data or [], [])
    portais = _seguro(lambda: cli.table("portals").select("key, name")
                      .execute().data or [], [])

    return {"agora": agora, "attendance": attendance, "runs": runs, "artefatos": artefatos,
            "aprovacoes": aprovacoes, "producoes": producoes,
            "custo_instrumentado": custo_instrumentado,
            "truncado": tuple(truncado), "leitura_indisponivel": False,
            "portal_contas": portal_contas, "portal_jobs": portal_jobs,
            "portais": portais}


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


# As duas journeys que dizem algo sobre o ACESSO ao portal. `abrir_atendimento`
# (vidros) fica fora: o desfecho dele não é veredito sobre a credencial.
_JOURNEYS_DE_ACESSO = ("login_check", "cobranca_sweep")

GRUPO_DOS_PORTAIS = ("portais_seguradoras", "PORTAIS DAS SEGURADORAS",
                     "o robô consegue entrar, e quando não consegue diz por quê")

# 💭 A cor do losango. Não é estado (o estado tem cor própria): é identidade.
_COR_DO_PORTAL = "#6E8BC0"


def _nome_do_portal(chave: str, nomes: Dict[str, str]) -> str:
    """O nome que uma pessoa lê. ⚠️ `allianz_corretor` não é nome de seguradora:
    é chave de tabela, e a Central proíbe chave na tela (SPEC-088 §4 / C10)."""
    bruto = str(chave or "").strip()
    if nomes.get(bruto):
        return str(nomes[bruto])
    limpo = bruto.replace("_corretor", "").replace("_", " ").strip()
    return limpo.title() or "Portal"


# ---------------------------------------------------------------------------
# A FILA DE TELAS DESCONHECIDAS — uma CONSULTA com LEITOR, nunca uma tabela nova
# ---------------------------------------------------------------------------
# 🔴 P-264 é a prova de que fila sem leitor não é fila: 📊 `select count(*) from
# tela_cega` → 2 linhas em 13/09/2026, e `grep -rn tela_cega backend --include=*.py`
# não acha NENHUM leitor fora do escritor e dos testes, desde 26/08. Uma tabela
# nasceu, alguém escreveu nela, e ninguém nunca leu.
#
# Por isso esta fila não é tabela (CLAUDE.md §5): é um AGRUPAMENTO sobre
# `portal_jobs`, e os dois leitores nascem no mesmo dia — este card e a linha do
# relatório da rotina (`billing_collection.telas_novas_do_dia`).
# Nota da proposta §9 B4.2: consulta com leitor 90 × tabela nova com leitor 70 ×
# tabela nova sem leitor 0 (proibido).
TETO_DE_TELAS_LIDAS = 500
JANELA_DE_TELAS_DIAS = 30
TAMANHO_DA_AMOSTRA_DE_TELA = 120
#: Os desfechos que POSSIVELMENTE são tela desconhecida. `done` fica fora: a tela
#  do sucesso é o dashboard logado, e ela não é um mistério a resolver.
STATUS_DE_TELA_DESCONHECIDA = ("needs_human", "failed")


def _amostra_de_tela(texto: Any, limite: int = TAMANHO_DA_AMOSTRA_DE_TELA) -> str:
    """O pedaço do texto da tela que vai para os olhos de alguém — redigido.

    ⚠️ O texto já nasce redigido no worker (`_registrar_tela`). Ele passa aqui de
    novo porque esta função também lê jobs GRAVADOS ANTES desta SPEC, e porque a
    regra de `redaction.py` é *na dúvida, mascare*. Se o redator não estiver
    disponível, a amostra sai VAZIA — nunca crua.
    """
    bruto = " ".join(str(texto or "").split())
    if not bruto:
        return ""
    try:
        from portal_worker.redaction import redigir_texto

        bruto = redigir_texto(bruto)
    except Exception:  # noqa: BLE001
        return ""
    return bruto[:limite]


def telas_desconhecidas(jobs: List[Dict[str, Any]], *,
                        company_id: Optional[str] = None,
                        agora: Optional[datetime] = None,
                        janela_dias: int = JANELA_DE_TELAS_DIAS,
                        teto: int = TETO_DE_TELAS_LIDAS,
                        tamanho_da_amostra: int = TAMANHO_DA_AMOSTRA_DE_TELA
                        ) -> Dict[str, Dict[str, Any]]:
    """PURA: as telas que o robô não reconheceu, agrupadas por PORTAL e por HASH.

    Equivale a:

        select portal_key, evidence->'tela'->>'hash' as tela, count(*) as vezes,
               max(finished_at) as ultima, min(evidence->'tela'->>'texto') as amostra
          from portal_jobs
         where company_id = :company_id and status in ('needs_human','failed')
           and evidence->'tela'->>'hash' is not null
         group by 1,2 order by vezes desc;

    🔴 `company_id` não é opcional por comodidade: quando ele vem, o filtro é NO
    CÓDIGO (CLAUDE.md §7 — o backend usa service role, e RLS sem policy não
    protege contra erro de filtro aqui). Quando ele NÃO vem, é porque quem chama
    é a Central de Agentes, que é master-admin e agrega por PORTAL.

    ⚠️ 14/09/2026 — E ESTE PARÁGRAFO DIZIA UMA COISA FALSA. Ele afirmava que
    "nenhum identificador de corretora entra na saída". 📊 Medido sobre as 6
    telas reais do acervo: a `amostra` traz a RAZÃO SOCIAL da corretora em 4
    delas — porque o texto da tela do portal é o texto da tela do portal, e o
    portal escreve o nome de quem está logado nela. O que a saída **não**
    carrega é o `company_id`; o TEXTO pode trazer a razão social, e por isso
    esta é uma superfície **master-admin**, não uma saída anônima
    (`P-E0016-AMOSTRA-PODE-TRAZER-RAZAO-SOCIAL`). O `redigir_texto` de
    `_amostra_de_tela` tira documento e telefone; nome de empresa, não.
    """
    alvo = str(company_id or "").strip()
    limite = None
    if agora is not None and janela_dias:
        limite = agora - timedelta(days=int(janela_dias))

    por_portal: Dict[str, Dict[str, Dict[str, Any]]] = {}
    lidos = 0
    for j in (jobs or []):
        if lidos >= teto:
            break
        if str(j.get("status") or "") not in STATUS_DE_TELA_DESCONHECIDA:
            continue
        if alvo and str(j.get("company_id") or "") != alvo:
            continue
        tela = j.get("tela")
        if not isinstance(tela, dict):
            evidencia = j.get("evidence")
            tela = evidencia.get("tela") if isinstance(evidencia, dict) else None
        if not isinstance(tela, dict):
            continue
        assinatura = str(tela.get("hash") or "").strip()
        if not assinatura:
            continue
        quando = parse_iso(j.get("finished_at"))
        if limite is not None and quando is not None and quando < limite:
            continue
        lidos += 1
        portal = str(j.get("portal_key") or "").strip() or "?"
        grupo = por_portal.setdefault(portal, {})
        linha = grupo.setdefault(assinatura, {"hash": assinatura, "vezes": 0,
                                              "ultima": None, "amostra": "", "prova": ""})
        linha["vezes"] += 1
        if quando and (linha["ultima"] is None or quando > linha["ultima"]):
            linha["ultima"] = quando
        if not linha["amostra"]:
            linha["amostra"] = _amostra_de_tela(tela.get("texto"), tamanho_da_amostra)
        if not linha["prova"] and tela.get("prova"):
            linha["prova"] = str(tela.get("prova"))[:300]

    saida: Dict[str, Dict[str, Any]] = {}
    for portal, telas in por_portal.items():
        # A mais frequente primeiro: é a que mais custa deixar sem entender.
        ordenadas = sorted(telas.values(), key=lambda t: (-int(t["vezes"]), str(t["hash"])))
        for linha in ordenadas:
            linha["ultima"] = _iso(linha["ultima"])
        saida[portal] = {"distintas": len(ordenadas),
                         "mais_frequente": dict(ordenadas[0]) if ordenadas else None,
                         "telas": ordenadas}
    return saida


def frase_das_telas_desconhecidas(dados: Optional[Dict[str, Any]]) -> str:
    """"3 telas que eu não reconheço — a mais frequente vista 12×". Vazio = nada.

    ⛔ Linha que diz "0 telas desconhecidas" é ruído: ela ocupa a mesma altura da
    que importa e ensina o olho a pular a região inteira.
    """
    distintas = int((dados or {}).get("distintas") or 0)
    if distintas <= 0:
        return ""
    substantivo = "telas que eu não reconheço" if distintas > 1 else "tela que eu não reconheço"
    vezes = int(((dados or {}).get("mais_frequente") or {}).get("vezes") or 0)
    if vezes <= 1:
        return "%d %s" % (distintas, substantivo)
    return "%d %s — a mais frequente vista %d×" % (distintas, substantivo, vezes)


def grupo_dos_portais(contas: List[Dict[str, Any]], jobs: List[Dict[str, Any]],
                      agora: datetime, nomes: Optional[Dict[str, str]] = None
                      ) -> Optional[Dict[str, Any]]:
    """PURA: um card por portal presente em `portal_accounts`.

    🔴 Por que este grupo existe (SPEC-EXTRA-001.6 B3.4). 📊 Medido em
    13/09/2026: a Allianz gastou ≈100 s/dia por 25 dias para produzir a mesma
    linha de falha, e **nenhuma tela dizia**. `portal_accounts.health` estava
    `unknown` nas 16 contas porque a coluna não tinha escritor; agora o worker
    escreve, e aqui ela vira card.

    ⛔ Sem PII e sem corretora: o card é por PORTAL, agregando as contas de
    todas as empresas. A saúde mostrada é a PIOR das contas — um portal com uma
    conta `ok` e uma `credencial_recusada` tem cobrança que não sai.
    """
    # ⚠️ Import local: `app.services.saude_do_portal` importa o vocabulário de
    # `portal_worker`, e a Central não pode depender disso para SUBIR — ela é a
    # tela que se abre justamente quando algo está fora do ar.
    from app.services.saude_do_portal import (ESTADO_NA_CENTRAL, pior_saude,
                                              rotulo_e_acao)

    linhas = [c for c in (contas or []) if str(c.get("portal_key") or "").strip()]
    if not linhas:
        return None
    nomes = nomes or {}

    por_portal: Dict[str, Dict[str, Any]] = {}
    for c in linhas:
        chave = str(c.get("portal_key")).strip()
        alvo = por_portal.setdefault(chave, {"saudes": [], "quando": None,
                                             "total": 0, "done": 0, "motivo": None,
                                             "ultima": None, "hoje": 0})
        alvo["saudes"].append(c.get("health"))
        quando = parse_iso(c.get("updated_at"))
        if quando and (alvo["quando"] is None or quando > alvo["quando"]):
            alvo["quando"] = quando

    for j in (jobs or []):
        chave = str(j.get("portal_key") or "").strip()
        if chave not in por_portal:
            continue
        if str(j.get("journey") or "") not in _JOURNEYS_DE_ACESSO:
            continue
        alvo = por_portal[chave]
        alvo["total"] += 1
        terminou = parse_iso(j.get("finished_at"))
        if str(j.get("status")) == "done":
            alvo["done"] += 1
        if terminou and (agora - terminou).total_seconds() <= 86400:
            alvo["hoje"] += 1
        if terminou and (alvo["ultima"] is None or terminou > alvo["ultima"]):
            alvo["ultima"] = terminou
        if str(j.get("status")) != "done" and alvo["motivo"] is None:
            # ⚠️ A mensagem é texto que veio do PORTAL. Ela passa pelo redator
            # antes de virar tela: `evidence.message` da MAPFRE traz o CPF do
            # corretor em claro no print, e texto de portal não é confiável.
            bruto = str(j.get("message") or "").strip()
            if bruto:
                try:
                    from portal_worker.redaction import redigir_texto

                    bruto = redigir_texto(bruto)
                except Exception:  # noqa: BLE001
                    bruto = ""
            alvo["motivo"] = bruto[:180] or None

    # 🔴 A fila de telas desconhecidas (B4.2), agregada por PORTAL. Sem
    # `company_id`: a Central é master-admin e o card já é da plataforma — e
    # `_ler_tudo_sincrono` de propósito nem seleciona a coluna, para não haver o
    # que vazar.
    fila_de_telas = telas_desconhecidas(jobs, agora=agora)

    cartoes: List[Dict[str, Any]] = []
    for chave in sorted(por_portal):
        dados = por_portal[chave]
        saude = pior_saude(dados["saudes"])
        # A última verificação é a do JOB (quando o robô de fato entrou); sem job
        # no período, o carimbo da conta é o que existe — e ele é honesto:
        # `updated_at` muda quando a saúde muda.
        verificado = dados["ultima"] or dados["quando"]
        rot = rotulo_e_acao(saude, _iso(verificado))
        partes = [rot["rotulo"]]
        if rot["acao"]:
            partes.append(rot["acao"])
        if dados["total"]:
            partes.append("%d de %d entradas concluíram nos últimos 7 dias"
                          % (dados["done"], dados["total"]))
        else:
            partes.append("nenhuma entrada registrada nos últimos 7 dias")
        if dados["motivo"]:
            partes.append("última falha: " + dados["motivo"])
        # 🔴 O LEITOR da fila (P-264). Sem esta frase o agrupamento seria mais
        # uma `tela_cega`: dado gravado que ninguém abre.
        telas = fila_de_telas.get(chave) or {"distintas": 0, "mais_frequente": None}
        frase_das_telas = frase_das_telas_desconhecidas(telas)
        if frase_das_telas:
            partes.append(frase_das_telas)
        cartoes.append({
            "id": "portal_" + chave,
            "nome": _nome_do_portal(chave, nomes),
            "descricao": "entrada no portal da seguradora (login e busca de boletos)",
            "cor": _COR_DO_PORTAL,
            "grupo": GRUPO_DOS_PORTAIS[0],
            "estado": ESTADO_NA_CENTRAL.get(saude, "NAO_MEDIDO"),
            "motivo": " · ".join(partes),
            "pulso": {"ultimo": _iso(verificado), "origem": "work_runs",
                      "origem_rotulo": "as execuções",
                      "cadencia_humana": cadencia_humana(86400)},
            "producao": {"ultimo": _iso(dados["ultima"]),
                         "fonte": "portal_jobs.finished_at",
                         "fonte_rotulo": "as entradas no portal",
                         "cadencia_esperada_s": 86400,
                         "cadencia_humana": cadencia_humana(86400),
                         "limiar_s": 2 * 86400},
            "desligado": {"declara": False, "todas_desligadas": None, "desde": None},
            "trabalho": {
                "eixo": None,
                "execucoes_24h": dados["hoje"],
                "execucoes_7d": dados["total"],
                "falhas_7d": dados["total"] - dados["done"],
                "duracao_media_s": None, "fila_media_s": None,
                "artifacts_7d": None, "aprovacoes_pendentes": None,
                "travados": 0, "custo_brl_30d": None,
            },
            "acoes_hoje": dados["hoje"],
            # A fila em forma de dado, para a tela poder abrir o print da mais
            # frequente. `mais_frequente` traz `prova` = o caminho no cofre.
            "telas_desconhecidas": {"distintas": telas.get("distintas") or 0,
                                    "mais_frequente": telas.get("mais_frequente")},
        })

    gid, titulo, proposito = GRUPO_DOS_PORTAIS
    return {"id": gid, "titulo": titulo, "proposito": proposito,
            "resumo": resumo_do_grupo([c["estado"] for c in cartoes]),
            "agentes": cartoes}


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
    truncado = tuple(bruto.get("truncado") or ())
    linhas_aprov = bruto["aprovacoes"]
    # ⚠️ Um `all()` sobre um recorte não é um `all()`: se a leitura estourou o teto, o
    # join não é confiável POR CONSTRUÇÃO, e não por causa do que se leu.
    aprov_confiavel = (bool(linhas_aprov) and "aprovacoes" not in truncado
                       and all(a.get("work_run_id") for a in linhas_aprov))
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
    # 🔴 O teto que estourou é uma medição que não foi feita, e ela sai NOMEADA — a mesma
    # regra do custo. Um número menor que a verdade com cara de verdade é o defeito desta SPEC.
    for campo in truncado:
        if campo not in nao_instrumentado:
            nao_instrumentado.append(campo)
    leitura_indisponivel = bool(bruto.get("leitura_indisponivel"))
    if leitura_indisponivel and "leitura" not in nao_instrumentado:
        nao_instrumentado.append("leitura")
    artifacts_truncado = "artifacts" in truncado

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
                "artifacts_7d": (None if artifacts_truncado
                                 else sum(int(art_7d.get(k, 0)) for k in chaves)),
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
        if leitura_indisponivel:
            # ⛔ Nunca 500, e nunca um cinza mudo: o motivo DIZ que o número não existe.
            motivo = (motivo + " ⚠️ leitura indisponível: o banco não respondeu nesta "
                               "rodada e nenhum número desta tela foi medido")

        cad_pulso = getattr(agente, "cadencia_pulso_s", None) or agente.cadencia_esperada_s

        por_grupo.setdefault(agente.grupo, []).append({
            "id": agente.id, "nome": agente.nome, "descricao": agente.descricao,
            "cor": agente.cor, "grupo": agente.grupo,
            "estado": estado, "motivo": motivo,
            # 🔴 `origem` e `fonte` são NOME DE TABELA — bons para auditar, ilegíveis na
            # tela. Os `_rotulo` são o que o corretor lê, e por isso ⛔ não carregam
            # tabela, coluna nem `_`: quem opera a corretora não sabe o que é
            # `attendance_transcripts`, e não deveria precisar saber.
            "pulso": {"ultimo": _iso(pulso), "origem": origem,
                      "origem_rotulo": ("as execuções" if origem == "work_runs"
                                        else "o próprio laço"),
                      "cadencia_humana": cadencia_humana(cad_pulso)},
            "producao": {"ultimo": _iso(producao),
                         "fonte": " ∪ ".join(rotulos) if rotulos else None,
                         "fonte_rotulo": getattr(agente, "fonte_rotulo", None),
                         "cadencia_esperada_s": agente.cadencia_esperada_s,
                         "cadencia_humana": cadencia_humana(agente.cadencia_esperada_s),
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

    # 🔴 O grupo dos portais entra DEPOIS dos quatro históricos: a ordem da
    # tela é a da urgência para o segurado, e o card do portal é do trabalho de
    # fundo. Ele só aparece quando existe conta de portal — grupo vazio na tela
    # é ruído, e ruído se ignora.
    grupo_portais = grupo_dos_portais(
        list(bruto.get("portal_contas") or []),
        list(bruto.get("portal_jobs") or []),
        agora,
        {str(p.get("key")): str(p.get("name") or "")
         for p in (bruto.get("portais") or []) if p.get("key")},
    )
    if grupo_portais:
        grupos.append(grupo_portais)

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


# =========================================================================== #
# SPEC-EXTRA-001.8 §10 (BLOCO F) — O ATENDIMENTO, POR CORRETORA
# =========================================================================== #
#
# 📊 Hoje esta Central responde *"o agente X produziu?"*, nunca *"a corretora Y
# foi atendida em quanto tempo?"*. Este bloco acrescenta a segunda pergunta ao
# MESMO JSON da rota que já existe.
#
# ⛔ **A declaração da linha 25 deste arquivo continua valendo: zero migration,
# zero tabela nova.** Tudo aqui sai do que já é escrito:
#   · `em_execucao`/`em_espera`/`ultimo_motivo`/`expiradas`/`timeouts`
#     do HASH `isolamento_escopo:{escopo}` (`message_buffer_service.py:87-97`)
#   · `p95`/`mediana`/`turnos` de `messages.payload->'turn'->>'total_ms'`
#     (`webhook.montar_turno_do_atendimento`, §5.1) cruzado com
#     `conversations.company_id`
#   · `breaker` de `relogio_do_modelo.estado_do_breaker`
#   · a tradução escopo→corretora de `integrations(id, company_id)` — a MESMA
#     fonte que `webhook.py:814-821` usa para resolver o tenant de uma mensagem
#     (`integration_service.get_integration_by_id` → `integration["company_id"]`)
#
# 🔴 **O AGRUPAMENTO POR CORRETORA É NO CÓDIGO, e ele é o coração do gate.** O
# backend usa service role: RLS sem filtro no código não protege nada
# (CLAUDE.md §7). Os tempos de A e os de B nunca se somam, e é
# `agrupar_turnos_por_corretora` — PURA, e por isso conferível — quem garante.
#
# ⛔ Nada de conteúdo de conversa atravessa: contagens, estados, ids e tempos.

#: 24 h para os TEMPOS. ⚠️ Não vale para os contadores do Redis — ver `_JANELA`.
_JANELA_DOS_TEMPOS_S = 24 * 3600

#: Quantas páginas de 1.000 linhas por leitura. 📊 Folga sobre o volume de
#: atendimento de um dia; estourar vira `aviso`, nunca um número menor com cara
#: de verdade (a mesma regra de `_paginar`).
_PAGINAS_MENSAGENS = 6
_PAGINAS_CONVERSAS = 4

#: 🔴 O NOME NÃO PODE MENTIR SOBRE O QUE GUARDA (CLAUDE.md §12.1).
#:
#: A proposta da SPEC chamava o campo de `expiradas_24h`. 📊 Ele NÃO é uma
#: janela deslizante de 24 h: `registrar_ocupacao` faz `HINCRBY` e renova o TTL
#: **a cada escrita** (`message_buffer_service.py:730-736`), então o acumulado
#: só zera quando a corretora passa 24 h inteiras sem falar. Uma corretora ativa
#: carrega o número desde sempre. O campo se chama `expiradas_acumuladas`, e o
#: `janela` abaixo diz isso por escrito.
_JANELA = {
    "tempos": "as últimas 24 horas de respostas (contadas pela hora da mensagem)",
    "contadores": ("acumulado desde a primeira mensagem — ele só volta a zero "
                   "depois de 24 horas inteiras sem nenhum atendimento nesta "
                   "corretora"),
}

#: A linha das integrações que não se conseguiu ligar a nenhuma corretora.
#: ⛔ Elas NUNCA somem em silêncio: um escopo sem dono na tela é uma corretora
#: cujo atendimento ninguém está vendo.
SEM_CORRETORA = "__sem_corretora__"


def percentil(valores: List[int], fracao: float) -> Optional[int]:
    """O percentil por interpolação linear — **PURA**. Sem amostra, `None`.

    ⛔ `None` não é 0: "nenhuma resposta nas últimas 24 h" e "respostas
    instantâneas" são fatos opostos, e um zero no lugar do vazio faria a tela
    dizer que a corretora mais lenta é a mais rápida.
    """
    limpos = sorted(int(v) for v in (valores or []) if v is not None)
    if not limpos:
        return None
    if len(limpos) == 1:
        return limpos[0]
    pos = (len(limpos) - 1) * max(0.0, min(1.0, float(fracao)))
    baixo = int(pos)
    alto = min(baixo + 1, len(limpos) - 1)
    peso = pos - baixo
    return int(round(limpos[baixo] * (1 - peso) + limpos[alto] * peso))


def agrupar_turnos_por_corretora(
    mensagens: List[Dict[str, Any]], conversas: List[Dict[str, Any]],
) -> Dict[str, List[int]]:
    """`company_id` → os `total_ms` dos turnos DELA — **PURA**.

    🔴 É aqui que uma corretora deixa de contaminar a outra. O `total_ms` de uma
    mensagem só entra na lista da corretora cuja conversa a contém; mensagem de
    conversa desconhecida é DESCARTADA, nunca atribuída a alguém.
    """
    empresa_da_conversa = {
        str(c.get("id") or ""): str(c.get("company_id") or "")
        for c in (conversas or []) if c.get("id") and c.get("company_id")
    }
    saida: Dict[str, List[int]] = {}
    for linha in (mensagens or []):
        empresa = empresa_da_conversa.get(str(linha.get("conversation_id") or ""))
        if not empresa:
            continue
        turno = ((linha.get("payload") or {}).get("turn") or {})
        bruto = turno.get("total_ms")
        if bruto is None or isinstance(bruto, bool):
            continue
        try:
            saida.setdefault(empresa, []).append(int(bruto))
        except (TypeError, ValueError):
            continue
    return saida


def _ler_atendimento_sincrono() -> Dict[str, Any]:
    """Os SELECTs do bloco, numa thread só. ⛔ Só leitura, e nenhum texto."""
    corte = (datetime.now(timezone.utc)
             - timedelta(seconds=_JANELA_DOS_TEMPOS_S)).isoformat()

    def _cliente():
        from app.core.database import get_supabase_client

        return get_supabase_client().client

    cli = _seguro(_cliente, None)
    if cli is None:
        return {"indisponivel": True, "integracoes": [], "empresas": {},
                "mensagens": [], "conversas": [], "truncado": False}

    # ⚠️ O teto do servidor é 1.000 linhas e ele NÃO avisa
    # (`test_ninguem_pede_mais_de_mil_linhas_de_novo.py`). Uma lista de
    # integrações cortada em silêncio viraria corretora sem dono na tela — por
    # isso o corte entra em `truncado`, e a tela diz que não viu tudo.
    integracoes = _seguro(
        lambda: cli.table("integrations").select("id, company_id")
        .limit(_PAGINA).execute().data or [], [])
    empresas_cortadas = len(integracoes) >= _PAGINA
    empresas = {
        str(c.get("id")): str(c.get("company_name") or "")
        for c in _seguro(
            lambda: cli.table("companies").select("id, company_name")
            .limit(_PAGINA).execute().data or [], [])
    }
    # 🔴 UMA leitura para TODAS as corretoras, nunca uma por corretora: N+1
    # contra produção dentro de uma rota que a tela recarrega a cada 20 s é
    # exatamente o custo que o cache de 60 s existe para não pagar.
    mensagens, estourou_m = _paginar(
        lambda i, j: (cli.table("messages").select("conversation_id, payload")
                      .eq("role", "assistant").gte("created_at", corte)
                      .order("created_at", desc=True).range(i, j).execute().data or []),
        _PAGINAS_MENSAGENS)
    conversas, estourou_c = _paginar(
        lambda i, j: (cli.table("conversations").select("id, company_id")
                      .gte("last_message_at", corte)
                      .order("last_message_at", desc=True).range(i, j).execute().data or []),
        _PAGINAS_CONVERSAS)
    return {"indisponivel": False, "integracoes": integracoes, "empresas": empresas,
            "mensagens": mensagens, "conversas": conversas,
            "truncado": bool(estourou_m or estourou_c or empresas_cortadas)}


async def _contadores_por_escopo() -> Optional[Dict[str, Dict[str, Any]]]:
    """Os HASHes `isolamento_escopo:*`. 🔴 `None` = Redis fora; `{}` = ninguém na fila.

    A diferença importa: sem Redis a tela tem de dizer "não sei", e não "zero".
    """
    try:
        from app.core.redis import get_async_redis_client
        from app.services.message_buffer_service import CONTADORES_PREFIXO

        redis = await get_async_redis_client()
        saida: Dict[str, Dict[str, Any]] = {}
        async for chave in redis.scan_iter(match=f"{CONTADORES_PREFIXO}:*"):
            texto = chave.decode() if isinstance(chave, (bytes, bytearray)) else str(chave)
            escopo = texto.split(":", 1)[1] if ":" in texto else ""
            if not escopo:
                continue
            bruto = await redis.hgetall(texto)
            saida[escopo] = {
                (k.decode() if isinstance(k, (bytes, bytearray)) else str(k)):
                (v.decode() if isinstance(v, (bytes, bytearray)) else v)
                for k, v in dict(bruto or {}).items()
            }
        return saida
    except Exception as erro:  # noqa: BLE001
        logger.warning("[CENTRAL-001.8] contadores indisponíveis (%s)",
                       type(erro).__name__)
        return None


async def _estado_dos_breakers() -> Optional[Dict[str, str]]:
    """`{provedor: "fechado"|"aberto"|"meio_aberto"}` — `None` quando não dá para ler."""
    try:
        from app.core.relogio_do_modelo import PROVEDORES, estado_do_breaker

        return {p: str((await estado_do_breaker(p)).get("estado") or "")
                for p in PROVEDORES}
    except Exception as erro:  # noqa: BLE001
        logger.warning("[CENTRAL-001.8] breaker indisponível (%s)", type(erro).__name__)
        return None


def _cota_declarada() -> Optional[int]:
    """A cota por corretora que o processador de fato aplica.

    ⛔ O default NÃO é reescrito aqui. Duas grafias do mesmo número é como uma
    das duas nasce errada (CLAUDE.md §5): o valor vem de
    `buffer_processor._COTA_PADRAO`, e quando ele não puder ser lido o campo sai
    `None` — "não medido" — em vez de um 4 inventado.
    """
    try:
        from app.tasks.buffer_processor import _COTA_PADRAO, _env_int

        return int(_env_int("WHATSAPP_COTA_POR_CORRETORA", _COTA_PADRAO))
    except Exception:  # noqa: BLE001
        return None


def _inteiro(bruto: Any) -> Optional[int]:
    if bruto is None or isinstance(bruto, bool):
        return None
    try:
        return int(bruto)
    except (TypeError, ValueError):
        return None


def montar_atendimento_por_corretora(
    *, bruto: Dict[str, Any], contadores: Optional[Dict[str, Dict[str, Any]]],
    breaker: Optional[Dict[str, str]], cota: Optional[int],
) -> List[Dict[str, Any]]:
    """O bloco `atendimento_por_corretora` — **PURA** (recebe tudo já lido).

    Ser pura é o que permite ao guarda montar duas corretoras sintéticas e
    conferir cada número contra uma contagem feita à mão (CLAUDE.md §9.4).
    """
    empresa_da_integracao = {
        str(i.get("id") or ""): str(i.get("company_id") or "")
        for i in (bruto.get("integracoes") or []) if i.get("id")
    }
    nomes = dict(bruto.get("empresas") or {})
    tempos = agrupar_turnos_por_corretora(
        list(bruto.get("mensagens") or []), list(bruto.get("conversas") or []))

    # ① os contadores do Redis, SOMADOS por corretora — uma corretora pode ter
    #    várias integrações de WhatsApp, e a fila dela é a soma delas.
    fila: Dict[str, Dict[str, Any]] = {}
    sem_redis = contadores is None
    for escopo, campos in dict(contadores or {}).items():
        # ⛔ Integração desconhecida NÃO some: vira a linha `SEM_CORRETORA`.
        empresa = empresa_da_integracao.get(escopo) or SEM_CORRETORA
        alvo = fila.setdefault(empresa, {
            "em_execucao": 0, "em_espera": 0, "expiradas": 0, "timeouts": 0,
            "motivo": "", "motivo_em": "", "integracoes": 0,
        })
        alvo["integracoes"] += 1
        for campo, chave in (("em_execucao", "em_execucao"), ("em_espera", "em_espera"),
                             ("expiradas", "expiradas"), ("timeouts", "timeouts")):
            alvo[campo] += _inteiro(campos.get(chave)) or 0
        quando = str(campos.get("ultimo_motivo_em") or "")
        if campos.get("ultimo_motivo") and quando >= alvo["motivo_em"]:
            alvo["motivo"], alvo["motivo_em"] = str(campos["ultimo_motivo"]), quando

    linhas: List[Dict[str, Any]] = []
    for empresa in sorted(set(fila) | set(tempos)):
        dela = fila.get(empresa) or {}
        medidos = tempos.get(empresa) or []
        aviso = ""
        if sem_redis:
            aviso = ("não consegui ler a fila de atendimento agora — os tempos "
                     "abaixo continuam medidos")
        elif bruto.get("truncado"):
            aviso = "há mais respostas nas últimas 24 h do que coube nesta leitura"
        linhas.append({
            "company_id": None if empresa == SEM_CORRETORA else empresa,
            "nome": (nomes.get(empresa) or "")
                    if empresa != SEM_CORRETORA else "",
            "sem_corretora": empresa == SEM_CORRETORA,
            "integracoes": _inteiro(dela.get("integracoes")),
            "em_execucao": None if sem_redis else _inteiro(dela.get("em_execucao")) or 0,
            "em_espera": None if sem_redis else _inteiro(dela.get("em_espera")) or 0,
            "cota": cota,
            "turnos_24h": len(medidos),
            "mediana_ms_24h": percentil(medidos, 0.5),
            "p95_ms_24h": percentil(medidos, 0.95),
            "ultimo_motivo_de_espera": None if sem_redis else (dela.get("motivo") or ""),
            # 🔴 `acumuladas`, não `_24h` — ver `_JANELA` acima.
            "expiradas_acumuladas": None if sem_redis else _inteiro(dela.get("expiradas")) or 0,
            "timeouts_acumulados": None if sem_redis else _inteiro(dela.get("timeouts")) or 0,
            "breaker": breaker,
            "janela": _JANELA,
            "aviso": aviso,
        })
    return linhas


async def atendimento_por_corretora() -> List[Dict[str, Any]]:
    """O bloco pronto para o JSON da rota. ⛔ Nunca levanta: a Central é a tela
    que se abre quando alguma coisa está errada — ser a primeira a cair é o pior
    comportamento possível."""
    try:
        bruto = await asyncio.to_thread(_ler_atendimento_sincrono)
        return montar_atendimento_por_corretora(
            bruto=bruto,
            contadores=await _contadores_por_escopo(),
            breaker=await _estado_dos_breakers(),
            cota=_cota_declarada(),
        )
    except Exception as erro:  # noqa: BLE001
        logger.warning("[CENTRAL-001.8] atendimento por corretora indisponível (%s)",
                       type(erro).__name__)
        return []


async def calcular_estado() -> Dict[str, Any]:
    """O contrato da §4 da SPEC-088, calculado do zero (sem cache)."""
    pulsos_lista = await read_all()
    pulsos = {p["id"]: p for p in pulsos_lista}
    bruto = await asyncio.to_thread(_ler_tudo_sincrono)
    estado = _montar(bruto, pulsos)
    # SPEC-EXTRA-001.8 §10 — o mesmo JSON, uma chave a mais. ⛔ Nenhuma rota
    # nova: `admin_spec034.agents_status` continua sendo a única porta, e
    # continua `require_master_admin`.
    estado["atendimento_por_corretora"] = await atendimento_por_corretora()
    return estado


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
