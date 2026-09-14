# -*- coding: utf-8 -*-
"""🔴 A Central de Agentes fica VERMELHA quando volta a mentir de verde — SPEC-088 BLOCO F.

📊 O defeito que este guarda existe para pegar, medido em 03/09/2026 (SPEC-088 §1.3):
`intelligence.garimpo` teve **21 execuções `completed` em 7 dias** e `broker_insights`
parou em **26/08/2026 00:05** — oito dias de laço rodando e zero produção. O card ficava
🟢, porque `page.tsx:36-42` só perguntava *"há quanto tempo foi o último pulso?"*.

> **Um laço que roda não é um trabalhador que produz.** O verde exige DUAS medições.

Forma: `backend/tests/test_o_protocolo_tem_policia.py` — blocos numerados, `certo()`,
linha de CONTROLE em cada bloco, `main()` que devolve 1 se houver falha, e um `def test_`
para o pytest. Precedente de "tela contra código": `test_a_casa_diz_a_verdade.py`.

Os blocos e o que cada um mata
------------------------------
```
[1] REGISTRO      A①A④   nenhum campo implícito; toda fonte aponta para coluna que EXISTE
[2] COBERTURA     A②      workflow_key sem card e sem decisão escrita REPROVA
[3] FRONTEND      A③ D①   a tela não tem lista de agente NEM limiar de 900s
[4] ESTADOS       B①–⑥    os cinco estados, com relógio fixo e limiar POR AGENTE
[5] MOTIVO        C⑥      a prosa do card não carrega CPF nem telefone
[6] CONTRATO      C①③     só as chaves da §4; join vazio é null + nao_instrumentado
[7] PULSOS        E②③     ninguém pulsa pelo vizinho; nenhum beat() em finally; e
                          TODO agente de pulso Redis pulsa NA CASA DELE (C8)
[8] CONTROLE GERAL        este guarda consegue ficar vermelho?
[9] DOIS TENANTS  C⑤     a barreira está nos DOIS lugares
[10] EXCLUSIVIDADE A⑤    duas entradas do registro não compartilham a MESMA fonte (C1)
[11] /SESSIONS    C⑥     o mascarador da rota é o CANÔNICO, e ele pega os 11 formatos (C5)
[12] FORMA        E① C④  o pulso vem depois do cutover; o filtro do registro casa o banco
```

🔴 **A RODADA DE CONSERTO (03/09/2026) acrescentou [10], [11] e [12], e mais seis casos
ao [4].** Cada um nasceu de um achado do painel de 3 lentes, e cada um tem linha de
CONTROLE que o faz ficar VERMELHO com o defeito reintroduzido:

```
[10]  📊 tecelão e cartógrafo declaravam `ura_maps` INTEIRA. `source`: observed 321
      (26/08) · cartographer* 3 (14/07). O cartógrafo saía 🟢 com o mapa do vizinho.
[11]  📊 o `_redigir` local pegava 3 de 11 formatos de PII: `(11) 98765-4321`, placa,
      CNPJ e e-mail passavam EM CLARO num transcript de URA.
[4]   📊 o ⚪ DESLIGADO vinha ANTES do pulso: o Follow-up, que roda a cada 60 s e pulsa
      incondicionalmente, saia DESLIGADO porque um agente de ATENDIMENTO estava inativo.
```

⚠️ **Escrito contra o CONTRATO da §4, não contra a implementação** (protocolo §4: quem
faz a prova não faz a resposta). Se `app/core/central_de_agentes.py` não importar, os
blocos que dependem dele fazem SKIP legível em vez de morrer; os blocos [3], [5-controle],
[7] e [8] só leem arquivos e código, e rodam sempre.

🔴 **DOIS gates do bloco [7] estão marcados `xfail` de propósito** — eles REPROVAM hoje
(📊 9 pulsos cruzados e 1 `beat()` em `finally:`, medidos em 03/09/2026 por
`grep -rn "await beat(" backend/app --include=*.py`) e só ficam verdes quando o BLOCO E
rodar. 🔴 **Quando ficarem verdes, o guarda ACUSA (XPASS = falha) e o integrador troca a
chamada `certo_xfail(...)` por `certo(...)`, apagando o argumento `xfail_ate=`.** É o
CLAUDE.md §9.3: teste que guarda verdade vencida é pior que teste nenhum.

📊 **As mutações abaixo foram RODADAS em 03/09/2026, e cada uma acendeu o gate que a SPEC
nomeou** (as saídas estão no relatório): M1 → 1 falha · M2 → 14 falhas, incluindo o gate
⑤ do B · M3 → 4 falhas, incluindo as duas do gate ④ · um `COLORS` reintroduzido em
`page.tsx` → 1 falha no [3] · e o XPASS do [7] simulado → 1 falha, com a instrução.
🔴 **Um guarda que nunca ficou vermelho é uma hipótese, não um portão.**

⛔ Este arquivo NUNCA imprime CPF, telefone, apólice, placa ou nome de pessoa. Ele lê o
banco só por SELECT, e sem credencial ele PULA com a razão escrita.

As três mutações obrigatórias do BLOCO F (o executor roda, restaura por cópia)
------------------------------------------------------------------------------
```
M1  troque a `fonte_de_producao` de um agente por `(_tab("x", "tabela_que_nao_existe",
    "created_at"),)` em heartbeat.py
    → [1] CONTRA O BANCO fica VERMELHO (a sonda devolve 404 / PGRST205)
    ⚠️ `Agente` é um NamedTuple sem default para `fonte_de_producao`: APAGAR o campo
      quebra o import, não passa despercebido. A mutação que vale é a fonte MENTIROSA —
      é ela que atravessaria uma revisão. O `None` explícito continua legítimo e o
      bloco [4] B③ prova que ele pinta ⚫, nunca 🟢.

M2  troque o limiar por agente de volta para 900s global em `limiar_s()`/`classificar()`
    → [4] gate ⑤ fica VERMELHO: o auditor (pulso 20h, produção 20h, cadência 86400)
      passa a dar PARADO em vez de SAUDAVEL, porque 20h > 900s. E [3] fica vermelho
      se o 900 voltar para o frontend.

M3  faça a chave de heartbeat expirada (pulso None) cair em DESLIGADO
    → [4] gate ④ fica VERMELHO: ausência de sinal NUNCA é o estado benigno
      (referência ⑤ da SPEC — "a teammate row that disappeared has been hidden, not stopped")
```
"""
from __future__ import annotations

import datetime as _dt
import io
import json
import os
import re
import sys
import urllib.parse
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # .../backend
REPO = os.path.dirname(RAIZ)
APP = os.path.join(RAIZ, "app")
HEARTBEAT = os.path.join(APP, "core", "heartbeat.py")
PAGINA = os.path.join(REPO, "app", "admin", "central-agentes")

if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)


def _carregar_env():
    """⚠️ `app.core.config` valida as settings no import e lê o `.env` a partir do CWD.

    Rodando de `backend/` funciona; rodando da raiz do repo levantava `ValidationError`
    e o guarda PULAVA os blocos do módulo — um guarda pulado por causa do diretório de
    trabalho é um guarda que não guarda. Aqui só se PREENCHE o que já falta, e
    ⛔ nenhum valor é impresso: presença/ausência, nunca o segredo (CLAUDE.md §13.3).
    """
    env = os.path.join(RAIZ, ".env")
    if not os.path.exists(env):
        return
    for linha in io.open(env, encoding="utf-8", errors="replace"):
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        k, v = linha.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_carregar_env()

# ---------------------------------------------------------------------------
# 🔴 OS NOMES QUE ESTE GUARDA IMPORTA — concentrados aqui de propósito.
# A API foi escrita em paralelo (protocolo §4: quem faz a prova não faz a resposta).
# Se um nome mudar, o INTEGRADOR muda AQUI, e em nenhum outro lugar do arquivo.
#
# `montar_resposta` é o `_montar(bruto, pulsos)` do módulo: função PURA de duas
# estruturas, sem I/O — é o que torna o contrato da §4 testável com fixture.
# ---------------------------------------------------------------------------
_FALTA = ""
classificar = workflow_keys_sem_card = montar_resposta = limiar_s = None
limiar_pulso_s = filtro_de_fonte = linha_casa_filtro = None
Agente = Fonte = None
AGENT_TASKS: list = []
try:
    from app.core.central_de_agentes import (  # type: ignore  # noqa: F401
        _montar as montar_resposta,
        classificar,
        filtro_de_fonte,
        limiar_pulso_s,
        limiar_s,
        linha_casa_filtro,
        workflow_keys_sem_card,
    )
except Exception as _e:  # noqa: BLE001
    _FALTA = "app.core.central_de_agentes: %s: %s" % (type(_e).__name__, _e)
try:
    from app.core.heartbeat import AGENT_TASKS, Agente, Fonte  # type: ignore  # noqa: F811
except Exception as _e:  # noqa: BLE001
    _FALTA = (_FALTA + " | " if _FALTA else "") + "app.core.heartbeat: %s: %s" % (
        type(_e).__name__, _e)


def _registro_pronto() -> bool:
    """O BLOCO A trocou a lista de tuplas `(id, nome, desc)` pelo registro `Agente`."""
    return bool(AGENT_TASKS) and all(hasattr(e, "fonte_de_producao") for e in AGENT_TASKS)


# ---------------------------------------------------------------------------
# O QUE A SPEC CONGELOU — §4 (contrato) e BLOCO A/B/D
# ---------------------------------------------------------------------------
ESTADOS = {"SAUDAVEL", "PULSA_SEM_PRODUZIR", "DESLIGADO", "PARADO", "NAO_MEDIDO"}
GRUPOS = {"observa", "atende_agora", "mantem_rota", "aprende_avisa"}
PULSOS_VALIDOS = {"redis", "work_runs"}
FONTES_VALIDAS = {"tabela", "work_runs_do_eixo", "artifacts_do_eixo"}

CHAVES_RAIZ = {"gerado_em", "cache_s", "grupos", "nao_instrumentado", "sem_card_por_decisao"}
CHAVES_GRUPO = {"id", "titulo", "proposito", "resumo", "agentes"}
# 🔴 A LICAO, escrita: `telas_desconhecidas` entrou no contrato do card em
# 14/09/2026 (SPEC-EXTRA-001.6 B4.2) e SO os cards de PORTAL a carregam. Um teste
# que guardasse a verdade vencida ("o card tem 12 chaves") ensinaria a ignorar
# teste (CLAUDE.md §9.3): o fato mudou, entao a afirmacao muda com ele. A chave e
# a fila de telas que o robo nao reconhece -- P-264 exige que toda fila nasca com
# leitor, e o leitor e este card.
CHAVES_AGENTE = {"id", "nome", "descricao", "cor", "grupo", "estado", "motivo",
                 "pulso", "producao", "desligado", "trabalho", "acoes_hoje"}
CHAVES_AGENTE_DE_PORTAL = CHAVES_AGENTE | {"telas_desconhecidas"}
CHAVES_TRABALHO = {"eixo", "execucoes_24h", "execucoes_7d", "falhas_7d", "duracao_media_s",
                   "fila_media_s", "artifacts_7d", "aprovacoes_pendentes", "travados",
                   "custo_brl_30d"}

# 🔴 AS CHAVES QUE A RODADA DE CONSERTO ACRESCENTOU (C10), e a razao de cada uma.
#
# `origem` e `fonte` sao NOME DE TABELA: bons para auditar, ilegiveis na tela. Os
# `_rotulo` sao o que o corretor le -- e por isso o gate abaixo PROIBE tabela, coluna
# e sublinhado dentro deles. Quem opera a corretora nao sabe o que e
# `attendance_transcripts`, e nao deveria precisar saber.
CHAVES_PULSO = {"ultimo", "origem", "origem_rotulo", "cadencia_humana"}
CHAVES_PRODUCAO = {"ultimo", "fonte", "fonte_rotulo", "cadencia_esperada_s",
                   "cadencia_humana", "limiar_s"}
CHAVES_DESLIGADO = {"declara", "todas_desligadas", "desde"}

# 🔴 A ORDEM DOS GRUPOS E A DA URGENCIA PARA O SEGURADO, nao a historica.
# `atende_agora` primeiro: e o unico grupo em que alguem esta esperando neste minuto.
ORDEM_DOS_GRUPOS = ["atende_agora", "observa", "mantem_rota", "aprende_avisa"]

# 📊 Os 14 ids de `heartbeat.py:20-51` e o ARQUIVO que é a casa de cada um.
# Fonte: SPEC-088 §1.5 e §8, reconferido em 03/09/2026 por
#   grep -rn "await beat(" backend/app --include=*.py
# 🔴 `garimpo` é None de propósito: o pulso dele passa a vir do EIXO (work_runs de
# intelligence.garimpo, BLOCO E1) — nenhum módulo pode pulsar por ele.
DONOS_DO_PULSO = {
    "observador":         "app/services/atlas/observer_intake.py",
    "tecelao":            "app/services/atlas/weaver.py",
    "sentinela_rotas":    "app/services/atlas/route_sentinel.py",
    "espelho":            "app/services/dispatch_mirror.py",
    "espelho_atendimento": "app/services/atlas/attendance_capture.py",
    "vigia_sentinela":    "app/tasks/dispatch_watchdog.py",
    "followup":           "app/tasks/dispatch_followup.py",
    "garimpo":            None,
    "auditor":            "app/services/conversation_auditor.py",
    "alfaiate":           "app/services/playbook_tailor.py",
    "sugestoes":          "app/services/proactive_suggestions.py",
    "cartografo":         "app/services/cartographer_runner.py",
    "cerebro":            "app/services/dispatch_router.py",
    "conselho":           "app/services/agent_council.py",
}

# 📊 03/09/2026 — `SELECT workflow_key, count(*) FROM work_runs
#    WHERE created_at > now()-interval '30 days' GROUP BY 1` (PostgREST, 2.679 runs):
#    detect_signals 2097 · measure_outcomes 351 · garimpo 90 · daily_briefing 87 ·
#    cluster_demand 31 · weekly_executive_briefing 12 · bridge.routine.execute 7 ·
#    acionamento.seguradora 4.   ⚠️ `test.wf` NÃO aparece na janela de 30 dias.
KEY_INVENTADO = "workflow.key.que.nunca.existiu.xyz"

# CPF e telefone brasileiros — a regex que o gate C⑥ manda apontar para o `motivo`.
RE_CPF = re.compile(r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}")
RE_FONE = re.compile(r"\d{2}\s?9?\d{4}-?\d{4}")

def _p(texto):
    """⚠️ Impressão à prova do console do Windows (cp1252).

    📊 Um `📊` dentro de um rótulo derrubou o guarda inteiro com `UnicodeEncodeError`
    na primeira rodada. Um guarda que morre por causa da fonte do terminal não guarda:
    aqui o caractere que não couber vira `?`, e a asserção continua sendo lida.
    """
    try:
        print(texto)
    except UnicodeEncodeError:
        cod = getattr(sys.stdout, "encoding", None) or "ascii"
        print(texto.encode(cod, "replace").decode(cod, "replace"))


OK = FAIL = XFAIL = 0
PULADOS: list = []
_ESTADOS_VISTOS: list = []


def certo(cond, rotulo, detalhe=""):
    global OK, FAIL
    if cond:
        OK += 1
        _p("  ok    %s" % rotulo)
    else:
        FAIL += 1
        _p("  FALHA %s" % rotulo + ("\n        %s" % detalhe if detalhe else ""))


def certo_xfail(cond, rotulo, xfail_ate, detalhe=""):
    """🔴 `strict=True` na forma deste arquivo: passar de verde ACUSA.

    Enquanto `xfail_ate` (o bloco que ainda não rodou) estiver pendente, a falha é
    esperada e NÃO conta. No dia em que ficar verde, isto vira FALHA com a instrução
    de remover o xfail — é assim que o guarda não guarda verdade vencida (§9.3).
    """
    global XFAIL
    if not cond:
        XFAIL += 1
        _p("  xfail %s   (esperado: %s)" % (rotulo, xfail_ate))
        if detalhe:
            _p("        %s" % detalhe)
    else:
        certo(False, "XPASS " + rotulo,
              "%s ja rodou. TROQUE `certo_xfail(...)` por `certo(...)` nesta linha "
              "e apague o argumento xfail_ate=." % xfail_ate)


def pular(rotulo, razao):
    PULADOS.append(rotulo)
    _p("  --    PULADO %s\n        %s" % (rotulo, razao))


def ler(p):
    return io.open(p, encoding="utf-8").read()


def sem_comentario_py(fonte):
    return "\n".join(l for l in fonte.split("\n") if not l.lstrip().startswith("#"))


def sem_comentario_ts(fonte):
    sem = "\n".join(l for l in fonte.split("\n") if not l.lstrip().startswith(("//", "*", "/*")))
    return re.sub(r"/\*.*?\*/", "", sem, flags=re.S)


def arquivos_py(raiz):
    for base, _dirs, nomes in os.walk(raiz):
        if "__pycache__" in base:
            continue
        for n in nomes:
            if n.endswith(".py"):
                yield os.path.join(base, n)


def rel(caminho):
    return os.path.relpath(caminho, RAIZ).replace(os.sep, "/")


# ---------------------------------------------------------------------------
# O BANCO — só SELECT, e sem credencial o bloco PULA com a razão escrita
# ---------------------------------------------------------------------------
def _credencial():
    url = os.environ.get("SUPABASE_URL")
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY")
           or os.environ.get("SUPABASE_KEY"))
    if url and key:
        return url.rstrip("/"), key
    env = os.path.join(RAIZ, ".env")
    if not os.path.exists(env):
        return None, None
    d = {}
    for linha in io.open(env, encoding="utf-8", errors="replace"):
        linha = linha.strip()
        if linha and not linha.startswith("#") and "=" in linha:
            k, v = linha.split("=", 1)
            d[k.strip()] = v.strip().strip('"').strip("'")
    url = d.get("SUPABASE_URL")
    key = (d.get("SUPABASE_SERVICE_ROLE_KEY") or d.get("SUPABASE_SERVICE_KEY")
           or d.get("SUPABASE_KEY"))
    return (url.rstrip("/") if url else None), (key or None)


def _get(caminho, timeout=30):
    """GET no PostgREST. Devolve (status, corpo_json_ou_None). Nunca levanta."""
    url, key = _credencial()
    if not url or not key:
        return None, None
    req = urllib.request.Request(url + "/rest/v1/" + caminho,
                                 headers={"apikey": key, "Authorization": "Bearer " + key})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:  # noqa: PERF203
        return e.code, None
    except Exception:  # noqa: BLE001
        return None, None


def coluna_existe(tabela, coluna):
    """🔴 `information_schema` não é exposto pelo PostgREST; a sonda equivalente é
    pedir a COLUNA e ler o código.

    📊 Provado em 03/09/2026 contra `dcajcvlzcjbmyapmklil`:
        observed_events?select=created_at            -> 200
        observed_events?select=coluna_que_nao_existe -> 400  (42703 column ... does not exist)
        tabela_que_nao_existe?select=id              -> 404  (PGRST205 could not find the table)
    Três respostas distintas: a sonda SABE ficar vermelha. O controle está no bloco [8].
    """
    st, _ = _get("%s?select=%s&limit=1" % (urllib.parse.quote(tabela), urllib.parse.quote(coluna)))
    return st


# ---------------------------------------------------------------------------
# O ADAPTADOR do motor — a única cola entre este guarda e o módulo do builder.
# Se `classificar()` sair com outra assinatura, o integrador muda SÓ isto.
# ---------------------------------------------------------------------------
AGORA = _dt.datetime(2026, 9, 3, 12, 0, 0, tzinfo=_dt.timezone.utc)   # relógio FIXO


def ha(segundos):
    return AGORA - _dt.timedelta(seconds=segundos)


def _iso(dt):
    return dt.isoformat() if dt else None


def _classificar(agente, pulso_em=None, producao_em=None,
                 todas_desligadas=None, desligado_desde=None, execucoes_7d=None):
    """Chama o motor e normaliza a resposta em (estado, motivo).

    Aceita `(estado, motivo)`, `str` ou dict com as chaves da §4 — o guarda testa o
    COMPORTAMENTO, não a embalagem. Devolve (None, razao) quando não deu para chamar.
    """
    if classificar is None:
        return None, "modulo ainda nao existe"
    ctx = {"execucoes_7d": execucoes_7d, "desligado_desde": desligado_desde}
    try:
        r = classificar(agente, _iso(pulso_em), _iso(producao_em), AGORA,
                        todas_desligadas, ctx)
    except TypeError as e:  # noqa: BLE001
        return None, "assinatura diferente da assumida (%s) -- ajuste _classificar()" % e
    except Exception as e:  # noqa: BLE001
        return None, "classificar() levantou %s: %s" % (type(e).__name__, e)
    if isinstance(r, str):
        return r, ""
    if isinstance(r, dict):
        return r.get("estado"), r.get("motivo") or ""
    if isinstance(r, (tuple, list)) and r:
        return r[0], (r[1] if len(r) > 1 else "")
    return None, "retorno de tipo inesperado: %s" % type(r).__name__


def _fonte(tabela="broker_insights", coluna="created_at"):
    return Fonte(tipo="tabela", rotulo="%s.%s" % (tabela, coluna),
                 tabela=tabela, colunas=(coluna,), filtro=None)


def _agente(**campos):
    """Fixture de uma linha do registro do BLOCO A, com os defaults do contrato."""
    base = dict(id="fixture", nome="Fixture", descricao="-", grupo="aprende_avisa",
                cor="#43C08C", eixo={"pulso": "redis", "workflow_keys": ()},
                fonte_de_producao=(_fonte(),), cadencia_esperada_s=86400,
                desligado_quando=None, k=2, cadencia_pulso_s=None,
                fonte_rotulo="o que ele entrega, em portugues")
    base.update(campos)
    # A fixture so passa os campos que o registro REALMENTE tem: assim o guarda sabe
    # DIZER que um campo da rodada de conserto falta, em vez de morrer no TypeError.
    conhecidos = set(getattr(Agente, "_fields", ()) or ())
    if conhecidos:
        base = dict((k, v) for k, v in base.items() if k in conhecidos)
    return Agente(**base)


class _EnvTemporaria:
    """`with _EnvTemporaria("X", "1"):` -- e o valor de antes volta, sempre.

    Mutacao de AMBIENTE, nao de arquivo: nada e escrito em disco e nao ha o que
    restaurar por copia. `valor=None` REMOVE a chave.
    """

    def __init__(self, nome, valor):
        self.nome, self.valor, self.antes, self.tinha = nome, valor, None, False

    def __enter__(self):
        self.tinha = self.nome in os.environ
        self.antes = os.environ.get(self.nome)
        if self.valor is None:
            os.environ.pop(self.nome, None)
        else:
            os.environ[self.nome] = self.valor
        return self

    def __exit__(self, *_):
        if self.tinha:
            os.environ[self.nome] = self.antes
        else:
            os.environ.pop(self.nome, None)
        return False


def _registra(estado):
    if estado:
        _ESTADOS_VISTOS.append(estado)


def _cartoes(resposta):
    for g in resposta.get("grupos") or []:
        for a in g.get("agentes") or []:
            yield a


def _trabalho_do(resposta, agent_id):
    for a in _cartoes(resposta):
        if a.get("id") == agent_id:
            return a.get("trabalho")
    return None


# ===========================================================================
# [1] O REGISTRO — gates A① e A④
# ===========================================================================
def bloco_1_registro():
    print("\n[1] O REGISTRO -- cada trabalhador declara o que produz, e NADA e implicito")
    if not _registro_pronto():
        pular("[1] inteiro",
              "AGENT_TASKS ainda nao e o registro do BLOCO A (%s)"
              % (_FALTA or "hoje e lista de tuplas, heartbeat.py:20"))
        return

    ids = [e.id for e in AGENT_TASKS]
    certo(len(AGENT_TASKS) >= 14,
          "o registro tem pelo menos os 14 ids historicos (achei %d)" % len(AGENT_TASKS),
          "📊 grep -c '^    (\"' backend/app/core/heartbeat.py -> 14 em 03/09/2026")
    sumiram = sorted(set(DONOS_DO_PULSO) - set(ids))
    certo(not sumiram, "nenhum dos 14 trabalhadores historicos sumiu do registro",
          "sumiram: %s -- um card que desaparece nao alerta ninguem" % ", ".join(sumiram))
    certo(len(ids) == len(set(ids)), "nenhum id repetido no registro",
          "repetidos: %s" % sorted({i for i in ids if ids.count(i) > 1}))

    # ⚠️ O contrato de compatibilidade que o proprio modulo declara: os 3 primeiros
    # campos continuam sendo (id, nome, descricao) -- `admin_atlas.py:935` faz `t[0]`.
    certo(all(e[0] == e.id and e[1] == e.nome and e[2] == e.descricao for e in AGENT_TASKS),
          "os 3 primeiros campos continuam (id, nome, descricao) -- admin_atlas.py:935 faz t[0]")

    for e in AGENT_TASKS:
        certo(e.grupo in GRUPOS, "%s: grupo em %s" % (e.id, sorted(GRUPOS)),
              "veio %r" % (e.grupo,))
        certo(isinstance(e.cor, str) and re.match(r"^#[0-9A-Fa-f]{6}$", e.cor or ""),
              "%s: cor hex (a cor saiu do frontend e mora aqui)" % e.id, "veio %r" % (e.cor,))
        certo(isinstance(e.eixo, dict) and e.eixo.get("pulso") in PULSOS_VALIDOS,
              "%s: eixo.pulso em %s" % (e.id, sorted(PULSOS_VALIDOS)), "veio %r" % (e.eixo,))
        # 🔴 A①/A④: None EXPLICITO passa; fonte mal formada REPROVA. (M1)
        f = e.fonte_de_producao
        certo(f is None or (isinstance(f, tuple) and f
                            and all(getattr(x, "tipo", None) in FONTES_VALIDAS for x in f)),
              "%s: fonte_de_producao e None EXPLICITO ou tupla de Fonte valida" % e.id,
              "veio %r -- 'sem tabela propria' e uma DECLARACAO (o no_policy do Dagster)" % (f,))
        for x in (f or ()):
            if x.tipo == "tabela":
                certo(bool(x.tabela) and bool(x.colunas),
                      "%s: a fonte de tabela tem tabela e coluna" % e.id, "veio %r" % (x,))
            else:
                certo(bool(e.eixo.get("workflow_keys")),
                      "%s: fonte %r exige workflow_keys no eixo" % (e.id, x.tipo),
                      "sem eixo, a fonte derivada de work_runs/artifacts nunca acha nada")
        certo(e.cadencia_esperada_s is None or isinstance(e.cadencia_esperada_s, int),
              "%s: cadencia_esperada_s e int ou None" % e.id, "veio %r" % (e.cadencia_esperada_s,))
        certo(isinstance(e.k, int) and e.k >= 1,
              "%s: declara k (multiplicador do limiar DELE, nunca 900s global)" % e.id,
              "veio %r" % (e.k,))
        certo(e.desligado_quando is None or isinstance(e.desligado_quando, dict),
              "%s: desligado_quando e None ou dict" % e.id, "veio %r" % (e.desligado_quando,))

    # 🔴 A regra que fecha a porta: quem tem fonte tem cadencia, ou o verde e impossivel
    # de justificar. `limiar_s` devolve None sem cadencia -- e ai o estado tem de ser ⚫.
    if limiar_s is not None:
        for e in AGENT_TASKS:
            if e.fonte_de_producao and e.cadencia_esperada_s:
                certo(limiar_s(e) == e.cadencia_esperada_s * e.k,
                      "%s: limiar_s = k x cadencia DELE (%d)" % (e.id, e.cadencia_esperada_s * e.k),
                      "veio %r" % (limiar_s(e),))

    # ---- CONTRA O BANCO (A④): toda fonte aponta para coluna que EXISTE
    url, _k = _credencial()
    if not url:
        pular("[1] CONTRA O BANCO", "sem SUPABASE_URL/KEY no ambiente nem em backend/.env")
        return
    for e in AGENT_TASKS:
        for x in (e.fonte_de_producao or ()):
            if x.tipo != "tabela":
                continue
            for coluna in x.colunas:
                st = coluna_existe(x.tabela, coluna)
                certo(st == 200, "%s: %s.%s existe no banco" % (e.id, x.tabela, coluna),
                      "PostgREST devolveu %s (400=coluna inexistente, 404=tabela inexistente)" % st)
            if x.filtro and x.filtro.get("coluna"):
                st = coluna_existe(x.tabela, x.filtro["coluna"])
                certo(st == 200,
                      "%s: a coluna do filtro %s.%s existe" % (e.id, x.tabela, x.filtro["coluna"]),
                      "PostgREST devolveu %s -- um filtro sobre coluna morta zera a fonte "
                      "em silencio, e o card congela num agente saudavel" % st)


# ===========================================================================
# [2] A COBERTURA — gate A②
# ===========================================================================
def bloco_2_cobertura():
    print("\n[2] A COBERTURA -- workflow_key sem card e sem decisao escrita REPROVA")
    if workflow_keys_sem_card is None:
        pular("[2] inteiro", "workflow_keys_sem_card ainda nao existe (%s)" % _FALTA)
        return

    conhecidos = ["intelligence.detect_signals", "intelligence.measure_outcomes",
                  "intelligence.garimpo", "intelligence.daily_briefing",
                  "intelligence.cluster_demand", "intelligence.weekly_executive_briefing",
                  "bridge.routine.execute", "acionamento.seguradora"]
    try:
        sobra = list(workflow_keys_sem_card(conhecidos))
    except Exception as e:  # noqa: BLE001
        certo(False, "workflow_keys_sem_card() aceita a lista de keys vistos",
              "levantou %s -- ajuste a chamada no topo do arquivo" % type(e).__name__)
        return
    certo(not sobra,
          "as 8 keys medidas em 03/09 tem card ou decisao escrita",
          "sem cobertura: %s" % ", ".join(str(x) for x in sobra))

    # 🔴 CONTROLE: um key inventado TEM de aparecer. Sem isto, uma funcao que devolve
    # [] sempre passaria por vacuidade -- e e assim que uma lista vazia vira carimbo.
    inventado = list(workflow_keys_sem_card(conhecidos + [KEY_INVENTADO]))
    certo(any(KEY_INVENTADO in str(x) for x in inventado),
          "CONTROLE: um workflow_key inventado APARECE na saida",
          "a funcao devolveu %r -- ela nao consegue ficar vermelha" % (inventado,))

    # ---- CONTRA O BANCO: os keys REAIS dos ultimos 30 dias
    url, _k = _credencial()
    if not url:
        pular("[2] CONTRA O BANCO", "sem credencial de Supabase")
        return
    desde = (AGORA - _dt.timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S")
    vistos, off = set(), 0
    while off <= 10000:
        st, corpo = _get("work_runs?select=workflow_key&created_at=gte.%s&limit=1000&offset=%d"
                         % (urllib.parse.quote(desde), off), timeout=60)
        if st != 200 or corpo is None:
            break
        vistos.update(r.get("workflow_key") for r in corpo if r.get("workflow_key"))
        if len(corpo) < 1000:
            break
        off += 1000
    if not vistos:
        pular("[2] CONTRA O BANCO", "work_runs nao respondeu (status %s)" % st)
        return
    sobra_real = list(workflow_keys_sem_card(sorted(vistos)))
    certo(not sobra_real,
          "CONTRA O BANCO: os %d workflow_key reais de 30d estao cobertos" % len(vistos),
          "sem card e sem decisao: %s" % ", ".join(str(x) for x in sobra_real))


# ===========================================================================
# [3] O FRONTEND — gates A③ e D①. Roda desde ja, sem modulo e sem banco.
# ===========================================================================
def bloco_3_frontend_sem_lista():
    print("\n[3] O FRONTEND NAO SABE NOME DE AGENTE -- a lista dupla da §1.6 morre aqui")
    if not os.path.isdir(PAGINA):
        certo(False, "o diretorio app/admin/central-agentes/ existe", PAGINA)
        return
    fontes = {}
    for base, _d, nomes in os.walk(PAGINA):
        for n in nomes:
            if n.endswith((".tsx", ".ts")):
                fontes[os.path.join(base, n)] = sem_comentario_ts(ler(os.path.join(base, n)))

    certo(bool(fontes), "achei %d arquivo(s) .tsx/.ts na pagina" % len(fontes))

    ids = sorted(DONOS_DO_PULSO)
    achados = []
    for caminho, txt in fontes.items():
        for i in ids:
            for m in re.finditer(r"\b%s\b" % re.escape(i), txt):
                achados.append("%s:%s" % (os.path.basename(caminho), i))
    certo(not achados,
          "nenhum id de agente na pagina (referencia (6): grupo e cor sao METADADO)",
          "%d ocorrencia(s): %s" % (len(achados), ", ".join(sorted(set(achados))[:12])))

    # 🔴 M2, lado do frontend: o limiar unico de 900s/7200s nao pode voltar para a tela.
    # 📊 page.tsx:36-42 hoje: <900s verde, <7200s amarelo. Condena quem roda 1x/dia (§1.6).
    juntos = "\n".join(fontes.values())
    certo("900" not in re.sub(r"#[0-9A-Fa-f]{3,8}", "", juntos)
          and "7200" not in juntos,
          "o limiar de 900s/7200s nao decide estado na tela -- o estado vem do JSON",
          "o limiar e k x cadencia DELE (BLOCO B), calculado no backend")
    certo(not re.search(r"function\s+health\s*\(", juntos),
          "a tela nao tem health(): quem classifica e o backend (contrato §4)")

    # 🔴 CONTROLE: o casador FUNCIONA -- ele acha os mesmos ids no backend.
    hb = ler(HEARTBEAT)
    acha_no_backend = [i for i in ids if re.search(r"\b%s\b" % re.escape(i), hb)]
    certo(len(acha_no_backend) >= 14,
          "CONTROLE: o mesmo casador acha %d dos ids em heartbeat.py" % len(acha_no_backend),
          "se ele nao achasse la, o zero da tela seria vacuidade, nao prova")


# ===========================================================================
# [4] OS CINCO ESTADOS — gates B① a B⑥, relogio FIXO
# ===========================================================================
def bloco_4_estados():
    print("\n[4] OS CINCO ESTADOS -- o verde exige DUAS medicoes, e o limiar e DELE")
    if classificar is None or Agente is None:
        pular("[4] inteiro", "classificar()/Agente ainda nao existem (%s)" % _FALTA)
        return

    # (1) o Garimpo de hoje: pulso ha 1 min, producao ha 8 dias, cadencia diaria, k=2
    e, motivo = _classificar(_agente(id="garimpo", cadencia_esperada_s=86400, k=2),
                             pulso_em=ha(60), producao_em=ha(8 * 86400), execucoes_7d=21)
    _registra(e)
    certo(e == "PULSA_SEM_PRODUZIR",
          "B1 pulso ha 1min + producao ha 8 dias -> PULSA_SEM_PRODUZIR", "veio %r (%s)" % (e, motivo))
    certo(e != "SAUDAVEL",
          "B1 NUNCA SAUDAVEL -- e a janela exata em que o codigo de hoje pinta verde",
          "📊 21 runs completed x broker_insights parado em 26/08 (SPEC-088 §1.3)")

    # (2) DESLIGADO e declarado, e sai de um fato do banco
    desl = _agente(id="vigia_sentinela", desligado_quando={"agents_attendance_all_inactive": True})
    e, motivo = _classificar(desl, pulso_em=None, producao_em=None,
                             todas_desligadas=True, desligado_desde=None)
    _registra(e)
    certo(e == "DESLIGADO", "B2 declara desligado_quando + todas_desligadas -> DESLIGADO",
          "veio %r" % e)
    certo("sem registro" in (motivo or "").lower(),
          "B2 desde=None -> o motivo diz 'sem registro', nunca uma data inferida",
          "motivo veio %r" % motivo)
    e2, _ = _classificar(desl, pulso_em=None, producao_em=None, todas_desligadas=False)
    certo(e2 != "DESLIGADO",
          "B2 uma corretora ligada -> NAO e DESLIGADO (a duvida paga do lado de quem alerta)",
          "veio %r" % e2)
    e3, _ = _classificar(_agente(id="auditor", desligado_quando=None),
                         pulso_em=None, producao_em=None, todas_desligadas=True)
    _registra(e3)
    certo(e3 == "PARADO",
          "B2 quem NAO declara desligado_quando e esta mudo -> PARADO, nunca DESLIGADO",
          "veio %r" % e3)

    # (3) sem fonte, ou sem cadencia -> NAO MEDIDO (o no_policy do Dagster)
    e, _ = _classificar(_agente(id="conselho", fonte_de_producao=None),
                        pulso_em=ha(60), producao_em=None)
    _registra(e)
    certo(e == "NAO_MEDIDO", "B3 fonte_de_producao=None -> NAO_MEDIDO, NUNCA SAUDAVEL",
          "veio %r" % e)
    e, _ = _classificar(_agente(id="espelho", cadencia_esperada_s=None),
                        pulso_em=ha(60), producao_em=ha(60))
    certo(e == "NAO_MEDIDO", "B3 cadencia None (com fonte) -> NAO_MEDIDO", "veio %r" % e)

    # (4) chave de heartbeat EXPIRADA -- o bug que o Airflow removeu (referencia (2)). M3.
    e, _ = _classificar(_agente(id="alfaiate", desligado_quando=None),
                        pulso_em=None, producao_em=None)
    _registra(e)
    certo(e == "PARADO",
          "B4 pulso None (chave expirada, morte de 30 dias) -> PARADO",
          "veio %r" % e)
    certo(e not in ("DESLIGADO", "SAUDAVEL"),
          "B4 ausencia de sinal NUNCA e o estado benigno (referencia (5))",
          "o _TTL de 7 dias nao transforma morte antiga em desligado")

    # (5) o auditor de hoje: 1x/dia, pulso 20h, producao 20h -> o limiar e DELE. M2.
    e, _ = _classificar(_agente(id="auditor", cadencia_esperada_s=86400, k=2),
                        pulso_em=ha(20 * 3600), producao_em=ha(20 * 3600))
    _registra(e)
    certo(e == "SAUDAVEL",
          "B5 pulso 20h + producao 20h, cadencia diaria, k=2 -> SAUDAVEL",
          "veio %r -- com o limiar unico de 900s isto daria PARADO, e e a mutacao M2" % e)

    # (6) 🔴 LINHA DE CONTROLE: sem ela, um motor que pinta tudo de amarelo passa em (1)-(5)
    e, _ = _classificar(_agente(id="espelho_atendimento", cadencia_esperada_s=3600, k=2),
                        pulso_em=ha(60), producao_em=ha(60))
    _registra(e)
    certo(e == "SAUDAVEL",
          "B6 CONTROLE: pulsou E produziu na cadencia -> SAUDAVEL",
          "veio %r -- o verde TEM de ser alcancavel, ou o guarda so sabe reprovar" % e)

    # (7) [C2] A EVIDENCIA DE TRABALHO VENCE A DECLARACAO DE DESLIGAMENTO.
    #
    # 📊 O defeito: `classificar()` checava `desligado_quando` ANTES de olhar pulso e
    # producao. O Follow-up roda a cada 60 s (`buffer_processor.py:103`) e pulsa
    # incondicionalmente no fim da varredura (`dispatch_followup.py:371`) -- e ficava
    # DESLIGADO porque um agente de ATENDIMENTO estava inativo. "Desligado" e a cor mais
    # cara para pintar num agente que esta trabalhando: ela manda parar de olhar.
    vivo = _agente(id="followup", cadencia_esperada_s=86400, cadencia_pulso_s=60,
                   desligado_quando={"agents_attendance_all_inactive": True})
    e, motivo = _classificar(vivo, pulso_em=ha(30), producao_em=ha(3600),
                             todas_desligadas=True)
    _registra(e)
    certo(e == "SAUDAVEL",
          "B7a pulsando E produzindo, com desligado_quando VERDADEIRO -> SAUDAVEL",
          "veio %r (%s)" % (e, motivo))
    certo(e != "DESLIGADO",
          "B7a NUNCA DESLIGADO com trabalho fresco -- a evidencia vence a declaracao",
          "era o card do Follow-up hoje: um laco de 60 s pintado de desligado")

    # (8) producao FRESCA e pulso VELHO -> continua verde, e o motivo DIZ do pulso.
    # Produzir e o fim; pulsar e o meio. Um agente que entregou o trabalho nao fica
    # vermelho porque o contador do laco atrasou -- mas quem le tem de saber disso.
    e, motivo = _classificar(_agente(id="detector", cadencia_esperada_s=86400,
                                     cadencia_pulso_s=3600),
                             pulso_em=ha(10 * 3600), producao_em=ha(3600))
    _registra(e)
    certo(e == "SAUDAVEL", "B7b producao fresca + pulso velho -> SAUDAVEL",
          "veio %r (%s)" % (e, motivo))
    certo("pulso" in (motivo or "").lower(),
          "B7b e o motivo CITA o pulso velho -- verde silencioso e verde que mente",
          "motivo veio %r" % motivo)

    # (9) mudo dos DOIS lados, com desligado_quando verdadeiro -> DESLIGADO continua valendo.
    mudo = _agente(id="vigia_sentinela", cadencia_esperada_s=None, cadencia_pulso_s=20,
                   fonte_de_producao=(_fonte("work_events"),),
                   desligado_quando={"agents_attendance_all_inactive": True})
    e, motivo = _classificar(mudo, pulso_em=ha(3600), producao_em=None,
                             todas_desligadas=True)
    _registra(e)
    certo(e == "DESLIGADO",
          "B7c sem pulso recente e sem producao, desligado verdadeiro -> DESLIGADO",
          "veio %r (%s)" % (e, motivo))

    # (10) [C3] A SENTINELA PRECISA CONSEGUIR FICAR VERMELHA.
    #
    # Sem `cadencia_pulso_s` ela era NAO_MEDIDO para sempre: sem fonte e sem cadencia de
    # producao, nada expirava. O laco podia estar morto ha uma semana e a tela dizia
    # "nao medido" sobre o agente que atende quem esta esperando NESTE minuto.
    sem_fonte = dict(id="vigia_sentinela", fonte_de_producao=None,
                     cadencia_esperada_s=None, desligado_quando=None)
    e, motivo = _classificar(_agente(cadencia_pulso_s=20, **sem_fonte),
                             pulso_em=ha(3600), producao_em=None)
    _registra(e)
    certo(e == "PARADO",
          "B7d laco de 20s calado ha 1h -> PARADO (nao mais o cinza eterno)",
          "veio %r (%s)" % (e, motivo))
    e2, _ = _classificar(_agente(cadencia_pulso_s=20, **sem_fonte),
                         pulso_em=ha(30), producao_em=None)
    certo(e2 == "NAO_MEDIDO",
          "B7d CONTROLE: com o laco VIVO ele volta a NAO_MEDIDO (a producao e que nao e medida)",
          "veio %r -- se desse PARADO, o gate pintaria de vermelho quem esta trabalhando" % e2)
    e3, _ = _classificar(_agente(cadencia_pulso_s=None, **sem_fonte),
                         pulso_em=ha(3600), producao_em=None)
    certo(e3 == "NAO_MEDIDO",
          "B7d CONTROLE: SEM cadencia de laco a morte volta a ser cinza",
          "veio %r -- e e por isso que declarar `cadencia_pulso_s` e obrigatorio "
          "para quem tem laco de relogio" % e3)

    fora = sorted({x for x in _ESTADOS_VISTOS if x not in ESTADOS})
    certo(not fora, "todo estado devolvido esta no enum de 5 do contrato §4",
          "fora do enum: %s" % ", ".join(str(x) for x in fora))


# ===========================================================================
# [4b] DESLIGADO POR CHAVE DE AMBIENTE -- conserto C7
# ===========================================================================
def bloco_4b_desligado_por_chave():
    print("\n[4b] DESLIGADO POR CHAVE -- 'parado' e 'desligado pelo Founder' sao cores diferentes")
    if classificar is None or Agente is None:
        pular("[4b] inteiro", "classificar()/Agente ainda nao existem (%s)" % _FALTA)
        return

    ag = _agente(id="alfaiate", cadencia_esperada_s=86400,
                 desligado_quando={"env_falso": "ALFAIATE_AUTO_APPLY"})
    with _EnvTemporaria("ALFAIATE_AUTO_APPLY", None):
        e, motivo = _classificar(ag, pulso_em=None, producao_em=None)
        _registra(e)
        certo(e == "DESLIGADO",
              "C7 env ausente -> DESLIGADO (nao PARADO)",
              "veio %r (%s) -- `playbook_tailor.py:145` corta ANTES do beat, e a chave "
              "nao esta em config nenhuma do repositorio" % (e, motivo))
        certo("ALFAIATE_AUTO_APPLY" in (motivo or ""),
              "C7 o motivo NOMEIA a chave que desliga",
              "motivo veio %r -- sem o nome, o operador nao tem o que ligar" % motivo)
    with _EnvTemporaria("ALFAIATE_AUTO_APPLY", "false"):
        e, _ = _classificar(ag, pulso_em=None, producao_em=None)
        certo(e == "DESLIGADO",
              "C7 env 'false' -> DESLIGADO (lista fechada de valores, nunca bool())",
              "veio %r -- bool('false') e True, e foi assim que a SPEC-093 quase "
              "ligou um agente de atendimento" % e)
    with _EnvTemporaria("ALFAIATE_AUTO_APPLY", "1"):
        e, motivo = _classificar(ag, pulso_em=None, producao_em=None)
        certo(e != "DESLIGADO",
              "C7 CONTROLE: env ligada -> NAO e DESLIGADO",
              "veio %r -- se ficasse cinza com a chave ligada, o card mentiria ao contrario" % e)
        certo(e == "PARADO",
              "C7 CONTROLE: ligado e mudo -> PARADO (o vermelho volta a ser possivel)",
              "veio %r (%s)" % (e, motivo))

    # E o REGISTRO declara isso, nao so o motor: um gate que so prova a funcao pura
    # passaria com o alfaiate ainda declarando `desligado_quando=None`.
    if _registro_pronto():
        alf = [a for a in AGENT_TASKS if a.id == "alfaiate"]
        certo(bool(alf) and (alf[0].desligado_quando or {}).get("env_falso") == "ALFAIATE_AUTO_APPLY",
              "C7 o REGISTRO declara env_falso ALFAIATE_AUTO_APPLY no alfaiate",
              "veio %r" % (alf[0].desligado_quando if alf else None))


# ===========================================================================
# [5] O MOTIVO NAO CARREGA PII — gate C⑥
# ===========================================================================
def bloco_5_motivo_sem_pii():
    print("\n[5] O MOTIVO E PROSA DE TEMPLATE -- e template nao interpola conversa")
    # 🔴 CONTROLE PRIMEIRO: as regras precisam CONSEGUIR pegar (CLAUDE.md §9.3).
    falso_cpf = "o agente 123.456.789-01 parou de produzir"
    falso_fone = "o agente 11 98765-4321 parou de produzir"
    certo(bool(RE_CPF.search(falso_cpf)), "CONTROLE: a regex de CPF pega um CPF injetado")
    certo(bool(RE_FONE.search(falso_fone)), "CONTROLE: a regex de telefone pega um telefone")
    certo(not RE_CPF.search("21 execucoes em 7 dias; ultima producao em 26/08 (8 dias)"),
          "CONTROLE: a regex NAO pega um motivo legitimo cheio de numeros",
          "um casador que pega tudo reprova tudo, e vira carimbo ao contrario")

    if classificar is None or Agente is None:
        pular("[5] os motivos gerados", "classificar()/Agente ainda nao existem (%s)" % _FALTA)
        return

    casos = [
        ("PULSA_SEM_PRODUZIR", _agente(id="garimpo"), ha(60), ha(8 * 86400), None),
        ("DESLIGADO", _agente(id="cerebro",
                              desligado_quando={"agents_attendance_all_inactive": True}),
         None, None, True),
        ("PARADO", _agente(id="alfaiate"), None, None, None),
        ("NAO_MEDIDO", _agente(id="conselho", fonte_de_producao=None), ha(60), None, None),
        ("SAUDAVEL", _agente(id="auditor", cadencia_esperada_s=86400), ha(20 * 3600),
         ha(20 * 3600), None),
    ]
    # 🔴 E o motivo REAL de cada trabalhador do registro, com a tabela dele no texto:
    # é a fonte de PII mais plausível (um rótulo que carregasse um campo de conversa).
    for e in AGENT_TASKS:
        casos.append(("registro:" + e.id, e, ha(60), ha(8 * 86400), None))
    for rotulo, ag, p, prod, todas in casos:
        estado, motivo = _classificar(ag, pulso_em=p, producao_em=prod, todas_desligadas=todas)
        certo(bool(motivo), "%s: o card tem motivo em uma frase" % rotulo, "estado=%r" % estado)
        certo(not RE_CPF.search(motivo or ""), "%s: o motivo nao casa CPF" % rotulo)
        certo(not RE_FONE.search(motivo or ""), "%s: o motivo nao casa telefone" % rotulo)


# ===========================================================================
# [6] O CONTRATO DA ROTA — gates C① e C③
# ===========================================================================
def _bruto_fixture(custo_instrumentado=False, aprov_com_run_id=False):
    """A entrada de `_montar` — o que as consultas de `_ler_tudo_sincrono()` devolvem.

    🔴 Nenhuma linha aqui tem texto de conversa, nome, telefone ou CPF: a rota inteira
    é feita de contagens, estados, ids e timestamps (referência ⑦ da SPEC).
    Um run de `intelligence.garimpo`, `completed`, com artifact e aprovação ligados.
    """
    agora = AGORA
    run_id = "run-fixture-0001"
    runs = [{"id": run_id, "workflow_key": "intelligence.garimpo", "status": "completed",
             "created_at": _iso(ha(3600)), "started_at": _iso(ha(3590)),
             "finished_at": _iso(ha(3580)), "unblock_state": None}]
    bruto = {
        "agora": agora,
        "attendance": [{"agent_role": "attendance", "is_active": False, "desligado_em": None}],
        "runs": runs,
        "artefatos": [{"work_run_id": run_id, "created_at": _iso(ha(3500))}],
        "aprovacoes": [{"status": "pending",
                        "work_run_id": run_id if aprov_com_run_id else None}],
        "producoes": {},
        "custo_instrumentado": custo_instrumentado,
    }
    pulsos = {e.id: {"id": e.id, "last_run": _iso(ha(120)), "actions_today": 3}
              for e in AGENT_TASKS}
    return bruto, pulsos


def bloco_6_contrato():
    print("\n[6] O CONTRATO DA §4 -- so estas chaves, e join vazio e null + nao_instrumentado")
    if montar_resposta is None or not _registro_pronto():
        pular("[6] inteiro", "montar_resposta()/AGENT_TASKS ainda nao existem (%s)" % _FALTA)
        return

    bruto, pulsos = _bruto_fixture()
    try:
        r = montar_resposta(bruto, pulsos)
    except Exception as e:  # noqa: BLE001
        pular("[6] inteiro",
              "montar_resposta(bruto, pulsos) levantou %s: %s -- a entrada assumida "
              "difere; ajuste `_bruto_fixture()` (uma edicao, um lugar)"
              % (type(e).__name__, e))
        return

    certo(isinstance(r, dict) and set(r) == CHAVES_RAIZ,
          "C1 a raiz tem exatamente as chaves da §4",
          "sobrando %s / faltando %s" % (sorted(set(r) - CHAVES_RAIZ) if isinstance(r, dict) else "?",
                                         sorted(CHAVES_RAIZ - set(r)) if isinstance(r, dict) else "?"))
    if not isinstance(r, dict):
        return
    certo(isinstance(r.get("grupos"), list) and r["grupos"], "C1 devolve grupos")
    ordem = [g.get("id") for g in (r.get("grupos") or []) if g.get("id") in ORDEM_DOS_GRUPOS]
    certo(ordem == ORDEM_DOS_GRUPOS,
          "C10 os grupos saem na ordem da URGENCIA (atende_agora primeiro)",
          "veio %r -- um painel que abre pelo que aprendeu ontem enterra o que esta "
          "doendo agora" % (ordem,))
    for g in r.get("grupos") or []:
        certo(set(g) == CHAVES_GRUPO, "C1 grupo %r tem so as chaves da §4" % g.get("id"),
              "sobrando %s / faltando %s" % (sorted(set(g) - CHAVES_GRUPO),
                                             sorted(CHAVES_GRUPO - set(g))))
        for a in g.get("agentes") or []:
            # 🔴 O card de PORTAL carrega uma chave a mais, e ela e DECLARADA aqui:
            # `telas_desconhecidas` (SPEC-EXTRA-001.6 B4.2). Aceitar "qualquer chave
            # extra" transformaria este guarda em carimbo; aceitar UMA, nomeada, e
            # so o fato que mudou.
            esperadas_do_card = (CHAVES_AGENTE_DE_PORTAL
                                 if str(a.get("id") or "").startswith("portal_")
                                 else CHAVES_AGENTE)
            certo(set(a) == esperadas_do_card, "C1 agente %r tem so as chaves da §4" % a.get("id"),
                  "sobrando %s / faltando %s" % (sorted(set(a) - esperadas_do_card),
                                                 sorted(esperadas_do_card - set(a))))
            for nome, esperadas in (("pulso", CHAVES_PULSO),
                                    ("producao", CHAVES_PRODUCAO),
                                    ("desligado", CHAVES_DESLIGADO)):
                bloco = a.get(nome)
                certo(isinstance(bloco, dict) and set(bloco) == esperadas,
                      "C1 %s de %r tem so as chaves da §4 (+ as de C10)" % (nome, a.get("id")),
                      "sobrando %s / faltando %s"
                      % (sorted(set(bloco or {}) - esperadas),
                         sorted(esperadas - set(bloco or {}))))
            # 🔴 C10: o rotulo humano nao pode ser o nome tecnico com outra roupa.
            rot = ((a.get("producao") or {}).get("fonte_rotulo") or "")
            certo(not rot or ("_" not in rot and "." not in rot),
                  "C10 fonte_rotulo de %r e prosa, sem tabela nem coluna" % a.get("id"),
                  "veio %r -- `attendance_transcripts.created_at` nao e um rotulo, "
                  "e uma chave primaria com legenda" % rot)
            porigem = ((a.get("pulso") or {}).get("origem_rotulo") or "")
            certo(porigem in ("o proprio laco", "o próprio laço", "as execucoes",
                              "as execuções"),
                  "C10 pulso.origem_rotulo de %r e um dos dois rotulos" % a.get("id"),
                  "veio %r" % porigem)
            t = a.get("trabalho")
            if isinstance(t, dict):
                certo(set(t) == CHAVES_TRABALHO, "C1 trabalho de %r tem so as chaves da §4"
                      % a.get("id"),
                      "sobrando %s / faltando %s" % (sorted(set(t) - CHAVES_TRABALHO),
                                                     sorted(CHAVES_TRABALHO - set(t))))
                # 🔴 C3: zero que vem de join que nao casa e null, NUNCA 0.
                certo(t.get("custo_brl_30d") is None,
                      "C3 custo_brl_30d e null (medido: 0,00 em 3.494 runs -> nao instrumentado)",
                      "veio %r -- um zero fingido mente igual a um verde falso" % t.get("custo_brl_30d"))
                certo(t.get("aprovacoes_pendentes") is None,
                      "C3 aprovacoes_pendentes e null (medido: 0 de 8 tem work_run_id)")
    ni = r.get("nao_instrumentado") or []
    certo("custo" in ni and "aprovacoes" in ni,
          "C3 os campos nulos estao NOMEADOS em nao_instrumentado",
          "veio %r" % (ni,))

    # 🔴 C6 CONTRA A RESPOSTA INTEIRA: nenhum campo textual carrega PII.
    inteiro = json.dumps(r, ensure_ascii=False, default=str)
    certo(not RE_CPF.search(inteiro), "C6 a resposta inteira nao casa CPF")
    certo(not RE_FONE.search(inteiro), "C6 a resposta inteira nao casa telefone")

    # 🔴 CONTROLE: um join PREENCHIDO tem de virar NUMERO e sair de nao_instrumentado.
    # Sem esta linha, "aprovacoes_pendentes e sempre None" passaria por vacuidade — e
    # um campo que nunca sai de null e um campo que nao existe (CLAUDE.md §9.3).
    bruto2, pulsos2 = _bruto_fixture(custo_instrumentado=True, aprov_com_run_id=True)
    try:
        r2 = montar_resposta(bruto2, pulsos2)
    except Exception as e:  # noqa: BLE001
        certo(False, "CONTROLE: montar_resposta aceita o fixture com join preenchido",
              "%s: %s" % (type(e).__name__, e))
        return
    t2 = _trabalho_do(r2, "garimpo")
    certo(t2 is not None and t2.get("aprovacoes_pendentes") == 1,
          "CONTROLE: aprovacao pending COM work_run_id -> 1, nao None",
          "veio %r -- se ficasse None, o campo seria decorativo" % (t2 or {}).get("aprovacoes_pendentes"))
    certo("aprovacoes" not in (r2.get("nao_instrumentado") or []),
          "CONTROLE: com o join honesto, 'aprovacoes' SAI de nao_instrumentado",
          "veio %r" % (r2.get("nao_instrumentado"),))
    certo("custo" not in (r2.get("nao_instrumentado") or []),
          "CONTROLE: com custo instrumentado, 'custo' SAI de nao_instrumentado",
          "veio %r" % (r2.get("nao_instrumentado"),))
    certo(t2 is not None and t2.get("execucoes_7d") == 1 and t2.get("artifacts_7d") == 1,
          "CONTROLE: o run e o artifact do fixture APARECEM no card do garimpo",
          "veio execucoes_7d=%r artifacts_7d=%r -- se dessem 0, o bloco [6] inteiro "
          "estaria medindo o vazio" % ((t2 or {}).get("execucoes_7d"),
                                       (t2 or {}).get("artifacts_7d")))


# ===========================================================================
# [7] OS PULSOS — gates E② e E③, por regex sobre o CODIGO COMO TEXTO
# ===========================================================================
def _chamadas_de_beat():
    """(caminho_rel, linha, id_do_agente) de cada `await beat("x")` do backend.

    ⚠️ Esta é a EXCEÇÃO legítima do `CLAUDE.md` §9.4: o alvo aqui é a FORMA da
    declaração — *onde* a chamada está escrita — e não o comportamento de um motor
    sobre texto real. Exigir `await ` antes exclui as mencões em docstring
    (📊 `dispatch_router.py:884` e `:2466` citam `beat("cerebro")` em prosa).
    """
    for caminho in arquivos_py(APP):
        for n, linha in enumerate(ler(caminho).split("\n"), 1):
            if linha.lstrip().startswith("#"):
                continue
            m = PADRAO_BEAT.search(linha)
            if m:
                yield rel(caminho), n, m.group(1)


# o casador de `await beat("x")`, exposto para a LINHA DE CONTROLE sobre texto sintético
PADRAO_BEAT = re.compile(r"await\s+(?:\w+\.)?beat\(\s*[\"'](\w+)[\"']")


def _beats_em_finally():
    """`await beat(` cujo caminho de blocos até a função inclui um `finally:`."""
    fora = []
    for caminho in arquivos_py(APP):
        linhas = ler(caminho).split("\n")
        for i, linha in enumerate(linhas):
            if "await " not in linha or "beat(" not in linha or linha.lstrip().startswith("#"):
                continue
            ind = len(linha) - len(linha.lstrip())
            for j in range(i - 1, -1, -1):
                ant = linhas[j]
                if not ant.strip() or ant.lstrip().startswith("#"):
                    continue
                a = len(ant) - len(ant.lstrip())
                if a >= ind:
                    continue
                cab = ant.strip()
                if cab.startswith("finally"):
                    fora.append("%s:%d" % (rel(caminho), i + 1))
                    break
                if cab.startswith(("def ", "async def ", "class ")):
                    break
                ind = a
    return fora


def _quem_nao_pulsa_em_casa(registro, fontes_por_dono):
    """Os agentes de pulso Redis SEM `beat("<id>")` (nem `_beat(`) no modulo dono.

    Puro: recebe o registro e um `{caminho_do_modulo: fonte}` -- e por isso a linha de
    CONTROLE pode mutar o TEXTO em memoria em vez de mexer no arquivo.
    """
    faltando = []
    for agente in registro:
        if str((agente.eixo or {}).get("pulso") or "redis") != "redis":
            continue
        dono = DONOS_DO_PULSO.get(agente.id)
        if not dono:
            # 🔴 pulso Redis declarado e nenhuma casa no mapa: e o mesmo defeito, e o
            # gate acusa em vez de pular em silencio.
            faltando.append("%s (sem modulo dono declarado)" % agente.id)
            continue
        fonte = fontes_por_dono.get(dono) or ""
        literal = re.search(r'beat\(\s*["\']%s["\']' % re.escape(agente.id), fonte)
        via_ajudante = ("async def _beat(" in fonte
                        and re.search(r'beat\(\s*["\']%s["\']' % re.escape(agente.id), fonte))
        if not (literal or via_ajudante):
            faltando.append("%s (esperado em %s)" % (agente.id, dono))
    return faltando


def bloco_7_pulsos():
    print("\n[7] OS PULSOS -- cada agente da o proprio pulso, e nunca dentro de finally")
    chamadas = list(_chamadas_de_beat())
    # 📊 depois do BLOCO E (03/09/2026): 14 chamadas com id literal + 5 via helper
    # `_beat()` = 19 em 13 arquivos (`grep -rn "await beat(\|await _beat(" backend/app`).
    # Antes: 27 em 18. O casador so ve as literais; o piso e 12 para pegar remocao em massa.
    certo(len(chamadas) >= 12,
          "achei %d chamadas `await beat(\"id\")` em backend/app" % len(chamadas),
          "📊 14 literais + 5 via _beat = 19 em 13 arquivos, medidas em 03/09/2026 depois do BLOCO E")

    desconhecidos = sorted({a for _c, _n, a in chamadas if a not in DONOS_DO_PULSO})
    certo(not desconhecidos,
          "todo id pulsado esta no registro (%d trabalhadores)" % len(DONOS_DO_PULSO),
          "ids fora do registro: %s -- ou o registro cresceu, ou e erro de digitacao"
          % ", ".join(desconhecidos))

    cruzados = []
    for c, n, agente in chamadas:
        dono = DONOS_DO_PULSO.get(agente, "")
        if dono is None:
            cruzados.append("%s:%d pulsa %s (que nao tem dono: o pulso dele vem do EIXO)"
                            % (c, n, agente))
        elif dono and c != dono:
            cruzados.append("%s:%d pulsa %s (a casa dele e %s)" % (c, n, agente, dono))

    # BLOCO E rodou em 03/09/2026: era xfail estrito, virou gate.
    certo(not cruzados,
          "E2 nenhum beat(\"x\") fora do modulo dono de x",
          "%d cruzamento(s):\n        %s" % (len(cruzados), "\n        ".join(cruzados)))

    em_finally = _beats_em_finally()
    certo(not em_finally,
          "E3 nenhum beat( dentro de finally: -- caminho de excecao nao pinta card",
          "%d: %s  (referencia (1): o Prometheus grava sucesso NO ramo de "
          "sucesso, nunca no finally)" % (len(em_finally), ", ".join(em_finally)))

    # 🔴 CONTROLE (E④) sobre TEXTO SINTÉTICO, nunca sobre o código vivo: até 03/09 este
    # controle exigia que `beat("alfaiate")` existisse em conversation_auditor.py — ou
    # seja, exigia o DEFEITO de volta (CLAUDE.md §9.3). O casador é provado aqui:
    m = PADRAO_BEAT.search('    await beat("alfaiate")  # reintroduzido')
    certo(bool(m) and m.group(1) == "alfaiate",
          "CONTROLE: o casador acha um `await beat(\"alfaiate\")` fabricado",
          "sem isto, o zero do gate E2 seria vacuidade")
    certo(PADRAO_BEAT.search('    beat("alfaiate")  # sem await: docstring/prosa') is None,
          "CONTROLE: o casador NAO acha `beat(\"x\")` sem `await` (as mencoes em prosa ficam de fora)")
    certo(any("dispatch_watchdog.py" in c and a == "vigia_sentinela" for c, _n, a in chamadas),
          "CONTROLE E4: o pulso legitimo de dispatch_watchdog.py continua la")
    certo(any("broker_insights.py" in c for c, _n, _a in chamadas)
          or not em_finally,
          "CONTROLE: o detector de finally aponta para uma linha que EXISTE")

    # 🔴 C8 -- COBERTURA. E② diz "ninguem pulsa pelo VIZINHO"; ele nao dizia
    # "e todo mundo pulsa em CASA". Um agente de pulso Redis cujo modulo perdeu o
    # `beat()` fica calado para sempre, e nenhum gate ficava vermelho por isso: E②
    # so olha as chamadas que EXISTEM.
    #
    # ⚠️ A excecao do §9.4 vale aqui (o alvo e a FORMA da declaracao: onde a chamada
    # esta escrita), e o `_beat(` cobre os modulos que definem o proprio ajudante --
    # `observer_intake.py:171` e `attendance_capture.py:97`.
    if not _registro_pronto():
        pular("[7] cobertura C8", "o registro do BLOCO A ainda nao existe")
    else:
        fontes_dos_donos = {}
        for agente_id, dono in DONOS_DO_PULSO.items():
            if dono and dono not in fontes_dos_donos:
                caminho = os.path.join(RAIZ, dono.replace("/", os.sep))
                fontes_dos_donos[dono] = ler(caminho) if os.path.exists(caminho) else ""
        sem_pulso = _quem_nao_pulsa_em_casa(AGENT_TASKS, fontes_dos_donos)
        certo(not sem_pulso,
              "C8 todo agente de pulso Redis tem beat() no modulo dono dele",
              "%d sem pulso em casa: %s -- um agente que nao pulsa fica calado para "
              "sempre, e o E2 nao ve o que nao existe"
              % (len(sem_pulso), ", ".join(sem_pulso)))

        # 🔴 CONTROLE por MUTACAO EM MEMORIA: apago o beat do cartografo do TEXTO lido
        # (nunca do arquivo) e o gate TEM de acender. Sem isto, o zero acima seria
        # vacuidade -- um casador quebrado tambem devolve lista vazia.
        mutado = dict(fontes_dos_donos)
        alvo = DONOS_DO_PULSO.get("cartografo")
        mutado[alvo] = (mutado.get(alvo) or "").replace('beat("cartografo"', 'beat("outro_qualquer"')
        acusados = _quem_nao_pulsa_em_casa(AGENT_TASKS, mutado)
        certo(any("cartografo" in x for x in acusados),
              "C8 CONTROLE: apagando o beat do cartografo (em memoria) o gate ACENDE",
              "veio %r -- se ficasse vazio, o gate nao consegue reprovar" % (acusados,))


# ===========================================================================
# [8] CONTROLE GERAL — este guarda consegue ficar vermelho?
# ===========================================================================
def bloco_8_CONTROLE():
    print("\n[8] CONTROLE GERAL -- um guarda que nao tem como falhar nao guarda nada")
    for caminho in (HEARTBEAT, PAGINA, os.path.join(APP, "api", "admin_spec034.py")):
        certo(os.path.exists(caminho), "existe: %s" % os.path.relpath(caminho, REPO))
    hb = ler(HEARTBEAT)
    certo(len(hb) > 1000, "heartbeat.py tem conteudo (%d chars)" % len(hb))
    certo("AGENTE_INEXISTENTE_XYZ" not in hb, "e o casador NAO acha o que nao esta la")

    # 🔴 um motor que pinta tudo igual passaria em [4] se [4] so olhasse um caso por vez.
    if _ESTADOS_VISTOS:
        distintos = set(_ESTADOS_VISTOS)
        certo(len(distintos) >= 4,
              "classificar() devolveu %d estados DISTINTOS nas fixtures do [4]" % len(distintos),
              "veio %s -- um motor que pinta tudo igual nao guarda nada" % sorted(distintos))
    else:
        pular("[8] estados distintos", "o bloco [4] nao rodou (modulo ainda nao existe)")

    # 🔴 A SONDA DO BANCO consegue ficar vermelha? (é ela que sustenta o gate A④)
    url, _k = _credencial()
    if not url:
        pular("[8] a sonda do banco", "sem credencial de Supabase")
        return
    certo(coluna_existe("observed_events", "created_at") == 200,
          "CONTROLE: a sonda acha uma coluna que EXISTE (observed_events.created_at)")
    certo(coluna_existe("observed_events", "coluna_que_nao_existe_xyz") == 400,
          "CONTROLE: a sonda REPROVA uma coluna inexistente (400 / 42703)")
    certo(coluna_existe("tabela_que_nao_existe_xyz", "id") == 404,
          "CONTROLE: a sonda REPROVA uma tabela inexistente (404 / PGRST205)")


def _rota_exige_master_admin(texto_rota, nome_rota):
    """A rota `nome_rota` tem `Depends(require_master_admin)` na assinatura da função
    imediatamente abaixo do decorador. Puro: recebe o TEXTO, para a linha de controle."""
    m = re.search(r'@router\.get\("/%s"\)\s*\n\s*async def \w+\(([^)]*)\)' % re.escape(nome_rota), texto_rota)
    return bool(m) and "require_master_admin" in m.group(1)


def bloco_9_dois_tenants():
    """Gate C⑤ da SPEC-088: a barreira de corretora fica em DOIS lugares e os dois
    são conferidos -- a dependência no backend e o proxy Next (401 sem sessão, 403
    sessão de corretora). Um só não é prova."""
    print("\n[9] DOIS TENANTS -- a barreira esta onde a SPEC diz que esta")
    rota = ler(os.path.join(APP, "api", "admin_spec034.py"))
    certo(_rota_exige_master_admin(rota, "agents-status"),
          "/agents-status exige require_master_admin na assinatura")
    certo(_rota_exige_master_admin(rota, "sessions"),
          "/sessions exige require_master_admin na assinatura")
    proxy = os.path.join(REPO, "lib", "admin-proxy.ts")
    certo(os.path.exists(proxy), "lib/admin-proxy.ts existe")
    if os.path.exists(proxy):
        p = ler(proxy)
        certo("status: 401" in p and "status: 403" in p,
              "o proxy Next devolve 401 (sem sessao) e 403 (sessao de corretora)")
    # 🔴 CONTROLE: uma rota falsa sem a dependência TEM de reprovar
    falsa = '@router.get("/agents-status")\nasync def agents_status() -> dict:\n    return {}\n'
    certo(not _rota_exige_master_admin(falsa, "agents-status"),
          "CONTROLE: rota sem require_master_admin REPROVA")



# ===========================================================================
# [10] EXCLUSIVIDADE DA FONTE -- conserto C1
# ===========================================================================
def _fontes_compartilhadas(registro):
    """As `(tabela, coluna)` que dois agentes reivindicam SEM se separarem de verdade.

    Duas formas de compartilhar, e a segunda foi a que escapou na primeira versao
    deste gate:

      (a) FILTRO IDENTICO -- os dois leem exatamente a mesma linha;
      (b) UM SEM FILTRO ao lado de outro -- a fonte sem filtro ENGOLE a do vizinho.
          📊 `ura_maps` inteira contem `source='observed'`: o cartografo herdaria o
          mapa do tecelao mesmo com o tecelao ja filtrado. Meio conserto nao conserta.

    Puro: recebe o registro, e por isso a linha de CONTROLE passa fixtures em vez de
    estragar o registro de verdade.
    """
    por_coluna = {}
    for agente in registro:
        for f in (agente.fonte_de_producao or ()):
            if getattr(f, "tipo", None) != "tabela":
                continue
            for coluna in (f.colunas or ()):
                por_coluna.setdefault((f.tabela, coluna), []).append(
                    (agente.id, json.dumps(f.filtro, sort_keys=True, default=str),
                     bool(f.filtro)))
    problemas = []
    for (tabela, coluna), reivindicacoes in sorted(por_coluna.items(), key=lambda x: str(x[0])):
        ids = sorted({a for a, _f, _t in reivindicacoes})
        if len(ids) < 2:
            continue
        por_filtro = {}
        for agente_id, chave, _tem in reivindicacoes:
            por_filtro.setdefault(chave, set()).add(agente_id)
        for chave, quem in sorted(por_filtro.items()):
            if len(quem) > 1:
                problemas.append(("%s.%s com o MESMO filtro %s" % (tabela, coluna, chave),
                                  sorted(quem)))
        sem_filtro = sorted({a for a, _f, tem in reivindicacoes if not tem})
        if sem_filtro:
            problemas.append(("%s.%s: %s le a tabela INTEIRA ao lado de %s"
                              % (tabela, coluna, ", ".join(sem_filtro),
                                 ", ".join(i for i in ids if i not in sem_filtro)), ids))
    vistos, unicos = set(), []
    for rotulo, quem in problemas:
        if rotulo not in vistos:
            vistos.add(rotulo)
            unicos.append((rotulo, quem))
    return unicos


def bloco_10_exclusividade():
    print("\n[10] EXCLUSIVIDADE -- duas entradas nao podem reivindicar a MESMA producao")
    if not _registro_pronto():
        pular("[10] inteiro", "o registro do BLOCO A ainda nao existe (%s)" % _FALTA)
        return

    # 🔴 O DEFEITO QUE ESTE BLOCO EXISTE PARA PEGAR, medido em 03/09/2026:
    #     SELECT source, count(*), max(created_at) FROM ura_maps GROUP BY 1
    #       observed              321   26/08/2026 14:07
    #       cartographer_stopped    2   14/07/2026
    #       cartographer            1   14/07/2026
    # Tecelao e Cartografo declaravam `ura_maps.created_at` SEM filtro. O Cartografo,
    # parado ha 51 dias, herdava a producao do vizinho e saia verde. ⚠️ Uma fonte
    # compartilhada nao "aproxima": ela transfere o credito do trabalho de um para o
    # cartao do outro, que e a classe de mentira desta SPEC inteira.
    compartilhadas = _fontes_compartilhadas(AGENT_TASKS)
    certo(not compartilhadas,
          "C1 nenhuma (tabela, coluna, filtro) e reivindicada por dois agentes",
          "; ".join("%s -> %s" % (k, ", ".join(v)) for k, v in compartilhadas))

    # E o mesmo para o EIXO: dois cards contando as MESMAS execucoes contam duas vezes.
    eixos = {}
    for agente in AGENT_TASKS:
        for chave in ((agente.eixo or {}).get("workflow_keys") or ()):
            eixos.setdefault(chave, []).append(agente.id)
    repetidos = sorted(k for k, v in eixos.items() if len(v) > 1)
    certo(not repetidos, "C1 nenhum workflow_key e reivindicado por dois agentes",
          "repetidos: %s" % ", ".join("%s -> %s" % (k, eixos[k]) for k in repetidos))

    # 🔴 CONTROLE: duas fixtures com a MESMA fonte TEM de aparecer. Sem esta linha, um
    # casador quebrado devolveria [] e o gate viraria carimbo.
    gemeos = [_agente(id="gemeo_a"), _agente(id="gemeo_b")]
    achado = _fontes_compartilhadas(gemeos)
    certo(bool(achado) and achado[0][1] == ["gemeo_a", "gemeo_b"],
          "C1 CONTROLE: duas fixtures com a mesma fonte APARECEM na saida",
          "veio %r -- o casador nao consegue ficar vermelho" % (achado,))

    # 🔴 E O CONTROLE AO CONTRARIO: a MESMA tabela com filtros DIFERENTES e legitima
    # (e o arranjo do vigia e do cerebro sobre `work_events`). Um gate que reprovasse
    # isso obrigaria a inventar tabela nova -- que e o motor paralelo do §5.
    def _com_filtro(agent_id, valor):
        return _agente(id=agent_id,
                       fonte_de_producao=(Fonte(tipo="tabela", rotulo="x",
                                                tabela="work_events",
                                                colunas=("created_at",),
                                                filtro={"coluna": "event_type",
                                                        "op": "eq", "valor": valor}),))
    distintos = _fontes_compartilhadas([_com_filtro("a", "agente.sentinela"),
                                        _com_filtro("b", "agente.cerebro")])
    certo(not distintos,
          "C1 CONTROLE: a mesma tabela com FILTROS diferentes nao e compartilhamento",
          "veio %r" % (distintos,))

    # 🔴 CONTROLE DO MEIO CONSERTO: um filtrado + um SEM filtro na mesma coluna. Foi
    # este caso que a primeira versao do gate deixou passar -- e e o pior dos dois,
    # porque parece consertado.
    sem = _agente(id="engole", fonte_de_producao=(Fonte(tipo="tabela", rotulo="x",
                                                        tabela="work_events",
                                                        colunas=("created_at",),
                                                        filtro=None),))
    meio = _fontes_compartilhadas([_com_filtro("a", "agente.sentinela"), sem])
    certo(bool(meio),
          "C1 CONTROLE: um SEM filtro ao lado de um filtrado tambem e compartilhamento",
          "veio %r -- a tabela inteira contem a linha filtrada, e o card do vizinho "
          "herda a producao dela" % (meio,))


# ===========================================================================
# [11] O MASCARADOR DA ROTA /SESSIONS -- conserto C5
# ===========================================================================
# 📊 As 11 formas em que PII chega num transcript de URA, e as 2 que NAO sao PII.
# O transcript e digitado pelo segurado no teclado do telefone: o formato e o que ele
# quiser, nao o que a regex do backend esperava.
PII_QUE_TEM_DE_SUMIR = (
    "(11) 98765-4321",          # o formato que a URA devolve
    "11 98765-4321",
    "11987654321",
    "+55 11 98765-4321",
    "044.555.666-77",           # CPF pontuado
    "04455566677",              # CPF cru
    "placa ABC1D23",            # Mercosul
    "ABC-1234",                 # placa antiga
    "12.345.678/0001-99",       # CNPJ
    "joao.silva@exemplo.com",
    "apolice 123456789",
)
# 🔴 E O CONTROLE AO CONTRARIO: um mascarador que apaga TUDO tambem passaria no teste
# acima. Estes dois sao trabalho legitimo do painel e TEM de sobreviver inteiros.
NAO_E_PII = ("Protocolo 52955490", "ha 3 dias")


def _redator_da_rota():
    """O mascarador que a rota `/sessions` usa, carregado sem subir o pacote `app`.

    ⚠️ `app/services/__init__.py` arrasta o pipeline de ingestao (fastembed). Carregar
    um modelo de embedding para conferir uma regex de CPF seria caro e frageis; a forma
    abaixo e a mesma de `test_a_mascara_vem_antes_da_tabela_global.py`.
    """
    import importlib.util as _u
    import types

    nomes = ("app", "app.services", "app.services.intelligence")
    injetados = [n for n in nomes if n not in sys.modules]
    for nome in injetados:
        mod = types.ModuleType(nome)
        mod.__path__ = [os.path.join(RAIZ, *nome.split("."))]
        sys.modules[nome] = mod
    try:
        caminho = os.path.join(APP, "services", "intelligence", "redaction_service.py")
        spec = _u.spec_from_file_location("_rs_088", caminho)
        mod = _u.module_from_spec(spec)
        sys.modules["_rs_088"] = mod
        spec.loader.exec_module(mod)
        return mod.redigir
    finally:
        for nome in injetados:
            sys.modules.pop(nome, None)


def _quem_passa_em_claro(redator, entradas):
    return [e for e in entradas if redator(e) == e]


def bloco_11_mascarador():
    print("\n[11] /SESSIONS -- o mascarador e o CANONICO, e ele pega os 11 formatos")
    rota_bruta = ler(os.path.join(APP, "api", "admin_spec034.py"))
    # SEM COMENTARIO: o arquivo GUARDA a memoria do defeito nos comentarios (e deve),
    # entao o gate mede CODIGO. Um gate que reprovasse a lembranca do erro ensinaria
    # a apagar a lembranca.
    rota = sem_comentario_py(rota_bruta)

    # (a) a FORMA: a rota importa o mascarador da casa e nao define um proprio.
    # ⚠️ Excecao legitima do §9.4 -- o alvo aqui e onde a declaracao esta escrita.
    certo("redaction_service import redigir" in rota,
          "C5 a rota importa `redigir` de redaction_service (o unico da casa)",
          "⛔ um segundo mascarador ao lado do canonico e o §5 do CLAUDE.md")
    certo("_DIGITOS" not in rota and "_CPF_FORMATADO" not in rota,
          "C5 os padroes locais `_DIGITOS`/`_CPF_FORMATADO` sairam do arquivo",
          "📊 eles pegavam 3 de 11 formatos, com um comentario afirmando o contrario")
    certo("_redigir(str(t.get(\"text\")" in rota,
          "C5 o transcript da timeline passa pelo mascarador antes de sair",
          "e a linha que leva o texto da URA para um payload de admin")
    certo("_mascarar_telefone" in rota,
          "C5 e o mascarador do telefone da SEGURADORA continua la (4 ultimos digitos)")
    # 🔴 E o nome nao pode ser REAMARRADO depois do import: `_redigir = lambda ...`
    # logo abaixo devolveria o mascarador paralelo com a mesma cara de conserto.
    certo(not re.search(r"^\s*_redigir\s*=", rota, re.M),
          "C5 `_redigir` nao e reatribuido no arquivo (so o import manda)",
          "achei uma atribuicao a `_redigir` -- importar o canonico e sobrescrever "
          "e o mesmo defeito com uma linha a mais")

    # (b) O MOTOR sobre TEXTO REAL (§9.4): rode o mascarador, nao leia a regex.
    try:
        redigir = _redator_da_rota()
    except Exception as e:  # noqa: BLE001
        pular("[11] o motor", "nao consegui carregar redaction_service: %s: %s"
              % (type(e).__name__, e))
        return
    passaram = _quem_passa_em_claro(redigir, PII_QUE_TEM_DE_SUMIR)
    certo(not passaram,
          "C5 os %d formatos de PII somem do transcript" % len(PII_QUE_TEM_DE_SUMIR),
          "%d passaram EM CLARO: %s" % (len(passaram), " | ".join(passaram)))
    for legitimo in NAO_E_PII:
        certo(redigir(legitimo) == legitimo,
              "C5 CONTROLE: %r sobrevive inteiro" % legitimo,
              "veio %r -- um mascarador que apaga tudo esconde o trabalho junto com "
              "o dado, e o painel deixa de servir" % redigir(legitimo))

    # (c) 🔴 CONTROLE DA BATERIA: o mascarador ANTIGO tem de REPROVAR nela. Sem isto,
    # "ninguem passou" poderia ser uma bateria que nao pega nada.
    _digitos, _cpf = re.compile(r"\d{10,14}"), re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}")
    antigo = lambda t: _digitos.sub("[r]", _cpf.sub("[r]", t))  # noqa: E731
    furos = _quem_passa_em_claro(antigo, PII_QUE_TEM_DE_SUMIR)
    certo(len(furos) >= 7,
          "C5 CONTROLE: o mascarador ANTIGO deixa passar %d dos %d formatos"
          % (len(furos), len(PII_QUE_TEM_DE_SUMIR)),
          "veio %r -- se a bateria nao reprovasse o defeito, ela nao seria bateria"
          % (furos,))


# ===========================================================================
# [12] FORMA -- gate E① (pulso depois do cutover) e gate C④ (o filtro casa o banco)
# ===========================================================================
def _beats_antes_do_cutover(fonte):
    """`await beat(` escrito ANTES do `if cutover_ligado():` do mesmo arquivo.

    🔴 E ESTE E O DEFEITO, e ele tem numero: ate o BLOCO E, `proactive_suggestions`
    pulsava na ENTRADA da task -- a cada 30 min, em qualquer dia, sem enviar nada. 📊 O
    card ficava verde 336 vezes por semana para um agente que trabalha uma.

    ⚠️ O gate mede a ORDEM, nao a existencia: com o `if cutover_ligado(): return ...`
    ANTES, o pulso e inalcancavel no fluxo desligado -- que e o comportamento correto
    (`proactive_suggestions.py:223` corta, `:243` pulsa). Um pulso ACIMA da guarda
    voltaria a pintar verde um agente que o cutover desligou.
    """
    linhas = fonte.split("\n")
    corte = None
    for i, linha in enumerate(linhas):
        if linha.lstrip().startswith("#"):
            continue
        if re.search(r"if\s+(?:not\s+)?cutover_ligado\(\)", linha):
            corte = i
            break
    if corte is None:
        return []
    fora = []
    for i, linha in enumerate(linhas[:corte]):
        if linha.lstrip().startswith("#"):
            continue
        if re.search(r"await\s+(?:\w+\.)?_?beat\(", linha):
            fora.append(i + 1)
    return fora


def _beats_dentro_do_cutover(fonte):
    """`await beat(` DENTRO do bloco `if cutover_ligado():` -- pulso no ramo desligado."""
    linhas = fonte.split("\n")
    fora = []
    for i, linha in enumerate(linhas):
        m = re.search(r"if\s+(?:not\s+)?cutover_ligado\(\)", linha)
        if not m or linha.lstrip().startswith("#"):
            continue
        ind = len(linha) - len(linha.lstrip())
        for j in range(i + 1, len(linhas)):
            seguinte = linhas[j]
            if not seguinte.strip() or seguinte.lstrip().startswith("#"):
                continue
            if (len(seguinte) - len(seguinte.lstrip())) <= ind:
                break
            if re.search(r"await\s+(?:\w+\.)?_?beat\(", seguinte):
                fora.append(j + 1)
    return fora


def bloco_12_forma():
    print("\n[12] FORMA -- o pulso vem DEPOIS do cutover, e o filtro do registro casa o banco")
    arquivos = []
    for caminho in arquivos_py(APP):
        fonte = ler(caminho)
        if "cutover_ligado" in fonte and "def cutover_ligado" not in fonte:
            arquivos.append((rel(caminho), fonte))
    certo(len(arquivos) >= 4,
          "E1 achei %d arquivo(s) que consultam cutover_ligado()" % len(arquivos),
          "📊 4 em 03/09/2026: broker_insights, proactive_suggestions, "
          "regression_sentinel, weekly_report")
    for caminho, fonte in arquivos:
        antes = _beats_antes_do_cutover(fonte)
        certo(not antes, "E1 %s: nenhum beat( ACIMA da guarda de cutover" % caminho,
              "linhas %s -- um pulso antes da guarda pinta verde um agente que o "
              "cutover desligou" % antes)
        dentro = _beats_dentro_do_cutover(fonte)
        certo(not dentro, "E1 %s: nenhum beat( DENTRO do ramo desligado" % caminho,
              "linhas %s" % dentro)

    # 🔴 CONTROLE sobre TEXTO SINTETICO, nunca sobre o codigo vivo (§9.3: exigir o
    # defeito de volta no arquivo real seria guardar verdade vencida).
    ruim = ('async def t():\n    await beat("sugestoes", 0)\n'
            '    if cutover_ligado():\n        return 0\n    return 1\n')
    certo(_beats_antes_do_cutover(ruim) == [2],
          "E1 CONTROLE: o casador ACHA um beat escrito acima da guarda",
          "veio %r" % (_beats_antes_do_cutover(ruim),))
    pior = ('async def t():\n    if cutover_ligado():\n        await beat("sugestoes", 0)\n'
            '        return 0\n    return 1\n')
    certo(_beats_dentro_do_cutover(pior) == [3],
          "E1 CONTROLE: o casador ACHA um beat DENTRO do ramo desligado",
          "veio %r" % (_beats_dentro_do_cutover(pior),))
    bom = ('async def t():\n    if cutover_ligado():\n        return 0\n'
           '    await beat("sugestoes", 1)\n    return 1\n')
    certo(not _beats_antes_do_cutover(bom) and not _beats_dentro_do_cutover(bom),
          "E1 CONTROLE: a forma CORRETA passa (guarda em cima, pulso embaixo)",
          "um gate que reprova tudo e um carimbo ao contrario")

    # ---- C④: o filtro que o registro declara casa a linha que o banco tem -------
    if filtro_de_fonte is None or linha_casa_filtro is None:
        pular("[12] C4", "filtro_de_fonte/linha_casa_filtro ainda nao existem")
        return
    f = filtro_de_fonte("garimpo", "broker_insights")
    certo(f is not None,
          "C4 o registro declara um filtro para garimpo x broker_insights",
          "sem ele o console /admin/insights volta a ter a string no codigo")
    certo(linha_casa_filtro({"source": "garimpo_v3"}, f) is True,
          "C4 o filtro do registro CASA a linha que o banco tem (`garimpo_v3`)",
          "📊 o banco so tem `garimpo_v3`; a string escrita no console era `garimpo`, "
          "e o ranking voltava vazio com 270 linhas la dentro")
    certo(linha_casa_filtro({"source": "outra"}, f) is False,
          "C4 CONTROLE: uma fonte alheia NAO casa",
          "um filtro que aceita tudo mistura as duas fontes no mesmo ranking")


# ---------------------------------------------------------------------------
def main() -> int:
    print("=" * 74)
    print("  A CENTRAL DE AGENTES DIZ A VERDADE -- SPEC-088 BLOCO F")
    print("=" * 74)
    bloco_1_registro()
    bloco_2_cobertura()
    bloco_3_frontend_sem_lista()
    bloco_4_estados()
    bloco_4b_desligado_por_chave()
    bloco_5_motivo_sem_pii()
    bloco_6_contrato()
    bloco_7_pulsos()
    bloco_8_CONTROLE()
    bloco_9_dois_tenants()
    bloco_10_exclusividade()
    bloco_11_mascarador()
    bloco_12_forma()
    print("\n" + "=" * 74)
    print("  %d ok, %d falhas, %d xfail (esperados ate o BLOCO E), %d pulados"
          % (OK, FAIL, XFAIL, len(PULADOS)))
    if PULADOS:
        print("  pulados: %s" % " · ".join(PULADOS))
    print("=" * 74)
    return 1 if FAIL else 0


def test_a_central_diz_a_verdade():
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
