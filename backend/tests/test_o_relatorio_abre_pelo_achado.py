# -*- coding: utf-8 -*-
"""O RELATORIO ABRE PELO ACHADO -- o guarda da SPEC-095 do lado do MOTOR.

🔴 **ESTE ARQUIVO NASCE VERMELHO, E E PARA NASCER.** Protocolo AAA v11.2 §4
(opcao B): quem faz a prova nao faz a resposta. O desenhista o escreveu com os
BLOCOS B e D ainda inexistentes -- e a saida separa **VERMELHO ESPERADO** (a
SPEC ainda deve aquele bloco, com o nome do bloco ao lado) de **VERMELHO DE
VERDADE** (defeito). O gate FINAL da SPEC-095 so fecha com a lista de VERMELHO
ESPERADO **vazia**.

O GATE ZERO -- os seis defeitos de HOJE que este arquivo prova em `b054b5c`
------------------------------------------------------------------------------
```
 (ii)  `_publicar` com o MESMO (template, periodo) cria um SEGUNDO artifact
       em vez de uma versao                                        [B.a]
 (iii) `_narrativa` devolve "N item(ns) esperando voce hoje" quando ha item
       acionavel com manchete propria                              [D3]
 (iv)  `_compor` do Pulso nao emite bloco `actions`; o titulo e
       "Pulso 360 · {rotulo}"                                      [D2]
  (v)  `_publicar` com AUTOBROKERS_CANARIO=1 grava `tags = []`      [B.c]
 (vi)  `como_dict` de um item cujo finding tem `why_now`/`next_step`
       nao os emite                                                [D3]
(vii)  `_nova_versao` grava `data_as_of = now()` sem ninguem ter passado data [B.b]
```
O item **(i)** (a rota lista o briefing duas vezes) e do lado da tela e mora em
`scripts/relatorios-dizem-o-que-sao.test.mjs`.

📊 E o que cada um custa, medido em 04/09/2026 (projeto dcajcvlzcjbmyapmklil):
```
 (ii)   79 pecas · 16 titulos distintos -> 79,7% dos titulos se repetem;
        "Pulso 360 · 2026" cinco vezes, cinco pecas, nunca uma v2
 (iii)  a manchete de 5 dias diferentes foi a MESMA string; o achado principal
        ("Fila acumulada -- 61 atendimentos parados") e o item 1 do corpo e
        nunca chega ao titulo
 (iv)   13 secoes, nenhuma diz o que fazer; `actions` existe desde a 057 e
        nenhum relatorio o usa; 4 caixas dizendo "sem dado" no mesmo Pulso
  (v)   100% dos relatorios "do chat" da Resulta sao canario de execucao de
        SPEC, e NADA os distingue: `tags` preenchida em 0/136
 (vi)   `why_now` 12/12 e `next_step` 11/12 ja existem em
        `intelligence_findings`; `ItemDeBriefing` nao tem campo para nenhum dos
        dois -- o porque e o proximo passo morrem UMA FUNCAO antes da tela
(vii)   136/136 versoes com `data_as_of` = carimbo da escrita, 30 delas no
        FUTURO do proprio `created_at`, e a tela afirma "Dados de ..."
```

O ELO que esta SPEC afirma, e que este guarda mede inteiro
------------------------------------------------------------------------------
```
o corretor entende o card PORQUE o titulo e o achado
  -> `narrativa.py` da ao achado titulo/por_que_importa/o_que_fazer/pergunta
  -> `_compor` poe o titulo do mais severo na CAPA e abre uma secao `actions`
  -> `_publicar` grava esse titulo em `artifacts.title` -- na MESMA peca,
     versao nova, nunca uma peca nova
E o porque chega PORQUE `como_dict` o emite: sem isso, `payload.sections[].
items[]` nasce sem `why_now`, e a tela nao tem de onde ler.
```
🔴 O passo que ninguem da (protocolo §0.3) e o do MEIO. Por isso os blocos [D]
chamam as funcoes REAIS sobre um pack golden REAL, em vez de conferir por `grep`
que existe um modulo chamado `narrativa`.

Os blocos, e o que cada um mata
------------------------------------------------------------------------------
```
[0] GATE ZERO   (ii)-(vii), os seis defeitos de hoje, com o PAR de cada um
[B] IDENTIDADE  a..g -- uma peca muitas versoes · data honesta · canario marcado
                · arquivar/desarquivar · o script que nao escreve em dry-run
                · `_packs_das_versoes` sem o payload cru
[D] NARRATIVA   D1 playbooks · D2 o Pulso abre pelo achado · D3 a manchete e o
                porque · D5 o briefing sem o relogio da plataforma
[C] CONTROLE    o guarda sabe falhar · a rede estava fechada · zero PII nas
                fixtures · nenhuma mutacao ficou na arvore
```

⚠️ **E toda lista de casos carrega PARES** (protocolo §5): mesma superficie,
veredito oposto. Um detector que so tem exemplos que reprovam nao prova que ele
consegue aprovar -- e vice-versa. Aqui os pares sao SINTETICOS e moram em
memoria (ver a nota das mutacoes abaixo).

🔴 AS MUTACOES -- por COPIA, e por que elas NAO rodam por padrao
------------------------------------------------------------------------------
`MUTACOES` abaixo e uma DECLARACAO, lida por
`test_todos_os_guardas_script_rodam.py::_alvos_declarados_pelos_guardas`: todo
arquivo citado nela entra na lista que o arnes vigia, restaura e cobra no fim da
sessao. Escrever a lista aqui e o que impede a P-246 (a lista de alvos escrita a
mao, cujo buraco ficou tres vezes na arvore).

⛔ **Elas nao rodam sem `--mutar`.** Este guarda nasceu enquanto DOIS builders
escreviam `backend/app/` no mesmo diretorio: mutar em disco e restaurar por
copia apagaria a edicao de quem estivesse salvando naquele segundo. Com a arvore
parada -- integracao, conserto, confirmacao mecanica -- rode:

    python backend/tests/test_o_relatorio_abre_pelo_achado.py --mutar

Cada mutacao: copia o arquivo para `.bak-095`, aplica a substituicao, RECARREGA
o modulo, mede, e restaura no `finally`. O bloco fica VERMELHO se a assercao
**nao** ficar vermelha sob a mutacao -- um gate que nao acusa a mutacao e um
carimbo (CLAUDE.md §9.3).

    MUTACOES (arquivo · o que trocar · qual assercao fica vermelha):
     1. relatorios_comerciais.py  `_publicar` volta a SEMPRE criar        -> [B.a]
     2. service.py                `data_as_of` volta a ser `_agora()`     -> [B.b]
     3. service.py                `criar` para de gravar `tags`           -> [B.c]
     4. briefing_service.py       `como_dict` sem `why_now`               -> [D3]
     5. briefing_service.py       `_narrativa` volta a CONTAR             -> [D3]
     6. briefing_service.py       `system` de volta em `compor`           -> [D5]
     7. executive_intelligence.py `_compor` sem o bloco `actions`         -> [D2]
     8. narrativa.py              CONCENTRACAO sem `titulo`               -> [D1]
     9. listar_entregas.py        `select('payload')` inteiro             -> [B.f]

⛔ SEGURANCA, e ela nao e opcional
------------------------------------------------------------------------------
```
· `SEM_REDE=1` e `socket.connect` BLOQUEADO -- mas so DENTRO de `main()`, e
  devolvido no `finally`. 📊 03/09: instalado no import, o bloqueio pegava a
  COLETA do pytest e deixava vermelhos 99 testes de outros arquivos.
· Nenhuma escrita e nenhuma leitura de banco: o `BancoFalso` e memoria pura.
· NENHUM nome de pessoa, CPF, apolice, placa, telefone ou credencial nas
  fixtures. Os rotulos sao sentinelas obvias -- "Seguradora Sentinela",
  "Produtor Sentinela". Se uma delas aparecer onde nao devia, o vazamento se le
  pelo nome (e o bloco [D2] procura exatamente por isso: M16 da SPEC-094).
· `AUTOBROKERS_CANARIO` e escrito e APAGADO dentro do bloco que o usa. Ele nao
  vaza para o resto da sessao.
```

DECISOES DO DESENHISTA (o que a SPEC nao fixa, e este guarda fixou)
------------------------------------------------------------------------------
```
D1  Helpers PROPRIOS, nao importados do irmao da 094.1: importar aquele modulo
    compartilharia os contadores OK/FAIL e faria o resultado de um depender da
    ORDEM do outro. A disciplina foi COPIADA; o placar e deste arquivo.
D2  Onde a SPEC nao fixa o NOME de uma peca (a tabela de playbooks de
    `narrativa.py`, por exemplo), o guarda procura numa LISTA FECHADA de
    candidatos e IMPRIME a lista -- em vez de adivinhar um endereco e ficar
    vermelho por endereco errado. A assercao de verdade e sempre COMPORTAMENTAL:
    roda o motor sobre o pack golden e le os quatro campos do achado.
D3  O pack golden e montado com `MetricResult` do PRODUTO
    (`app.comercial.evidence_pack`), com valores escolhidos para cruzar os tres
    limiares declarados: 46,8% >= 40,0 (concentracao) · 128 > 0 (exposicao) ·
    -31,4% <= -20,0 (queda). Os limiares sao LIDOS do modulo, nunca copiados:
    se alguem mudar `LIMIAR_CONCENTRACAO_PCT`, a fixture continua cruzando ou o
    proprio guarda avisa que parou de cruzar.
D4  `_compor` e chamado por um objeto de emprestimo que pega os metodos REAIS da
    `ExecutiveIntelligenceTool` sem construir o `BaseTool` (que puxaria
    langgraph). Nenhum codigo nosso e falsificado: os metodos sao os do produto.
D5  Modulo que a SPEC promete e ainda nao existe => VERMELHO ESPERADO com a
    mensagem escrita. Nunca PULADO, nunca `xfail`, nunca estouro.
```
Rodar:  PYTHONIOENCODING=utf-8 python backend/tests/test_o_relatorio_abre_pelo_achado.py
        (a partir de `backend/`: `python tests/test_o_relatorio_abre_pelo_achado.py`)
        `--mutar` acrescenta as mutacoes por copia (so com a arvore parada).
"""
from __future__ import annotations

import copy
import importlib
import io
import json
import os
import re
import shutil
import socket
import sys
import types
from datetime import datetime, timedelta, timezone

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

TESTES = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(TESTES)                      # .../backend
APP = os.path.join(RAIZ, "app")
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

EMPRESA_A = "11111111-1111-1111-1111-111111111111"
EMPRESA_B = "22222222-2222-2222-2222-222222222222"

# ===========================================================================
# 🔴 A DECLARACAO DE MUTACOES -- lida pelo arnes compartilhado
#
# `test_todos_os_guardas_script_rodam.py::_alvos_declarados_pelos_guardas` faz
# `ast.parse` deste arquivo e recolhe o PRIMEIRO elemento de cada tupla. Todo
# arquivo citado aqui passa a ser vigiado, restaurado e cobrado no fim da
# sessao. Uma mutacao que existe e nao esta declarada aqui e a P-246 de volta.
#
# Formato: (caminho relativo a `backend/`, de, para, rotulo)
# ===========================================================================
MUTACOES = [
    # 📊 04/09/2026 (builder do motor): a âncora "def _publicar(" só injetava um
    # COMENTÁRIO — o arquivo compilava igual e a mutação era no-op. A âncora
    # certa é a linha que decide se a identidade é procurada: com `chave = ""`
    # o lookup nunca acontece e toda pergunta cria peça nova (o defeito de hoje).
    ("app/agents/tools/relatorios_comerciais.py",
     'chave = str((identidade or {}).get("id") or "").strip()', 'chave = ""', "B.a"),
    # ⚠️ Nenhuma substituição carrega comentário: um `# MUTACAO` no fim de uma
    # linha que continua (dict literal) engole o resto da linha e vira
    # SyntaxError — e aí o que se mede é o compilador, não o guarda.
    ("app/services/artifacts/service.py",
     '"data_as_of": None, "confidence_note": None,',
     '"data_as_of": _agora().isoformat(), "confidence_note": None,', "B.b"),
    ("app/services/artifacts/service.py",
     '"tags": list(tags or [])', '"tags": []', "B.c"),
    ("app/services/intelligence/briefing_service.py",
     '"why_now": self.why_now', '"why_now_DESLIGADO": self.why_now', "D3"),
    # A âncora "headline = " casava PRIMEIRO com `i.headline = "%s (+%d iguais)"`
    # (a deduplicação), não com a manchete. A linha que decide a manchete é esta:
    ("app/services/intelligence/briefing_service.py",
     "manchete = topo.headline", 'manchete = "%d item(ns) esperando você hoje" % n', "D3"),
    ("app/services/intelligence/briefing_service.py",
     'w.get("source_type")', '"chat"', "D5"),
    ("app/agents/tools/executive_intelligence.py",
     '"block": "actions"', '"block": "kpis"', "D2"),
    ("app/comercial/narrativa.py",
     '"titulo"', '"titulo_DESLIGADO"', "D1"),
    # 📊 O builder escreveu a projeção como `"artifact_id, %s->%s, status" %
    # (coluna, caminho)` com `coluna = "payload"` — de propósito: o guarda da
    # 094.1 (`test_as_ferramentas_de_relatorio_comercial.py:224-232`) exige
    # exatamente UMA função com a constante "payload", que é como ele prova que
    # "o payload morre dentro desta função". A mutação tira o caminho e volta a
    # pedir a coluna inteira.
    ("app/agents/tools/listar_entregas.py",
     '"artifact_id, %s->%s, status" % (coluna, caminho)',
     '"artifact_id, %s, status" % (coluna,)', "B.f"),
]

# ===========================================================================
# A rede fechada -- so dentro de main()
# ===========================================================================
_CONNECT = socket.socket.connect
_CONNECT_EX = socket.socket.connect_ex


def _loopback(destino):
    try:
        return isinstance(destino, tuple) and str(destino[0]) in ("127.0.0.1", "::1", "localhost")
    except Exception:  # noqa: BLE001
        return False


def _proibir(self, destino, *a, **k):  # noqa: ANN001
    if _loopback(destino):
        return _CONNECT(self, destino, *a, **k)
    raise RuntimeError("SEM_REDE: este guarda nao fala com a rede (destino %r)" % (destino,))


def _proibir_ex(self, destino, *a, **k):  # noqa: ANN001
    if _loopback(destino):
        return _CONNECT_EX(self, destino, *a, **k)
    raise RuntimeError("SEM_REDE: este guarda nao fala com a rede (destino %r)" % (destino,))


def _fechar_a_rede():
    os.environ["SEM_REDE"] = "1"
    socket.socket.connect = _proibir        # type: ignore[assignment]
    socket.socket.connect_ex = _proibir_ex  # type: ignore[assignment]


def _abrir_a_rede():
    socket.socket.connect = _CONNECT        # type: ignore[assignment]
    socket.socket.connect_ex = _CONNECT_EX  # type: ignore[assignment]
    os.environ.pop("SEM_REDE", None)


# ===========================================================================
# `sys.modules` -- as cascas de pacote, e a devolucao do ambiente
#
# 📊 `app/services/__init__.py` importa 14 servicos e `app/agents/__init__.py`
# puxa langgraph: sem a casca, TODO bloco deste guarda pularia com a razao
# ERRADA ("No module named 'langgraph'") em vez da verdadeira ("o BLOCO D ainda
# nao existe"). ⛔ A casca tem o `__path__` REAL: nenhum codigo nosso e
# falsificado, so os `__init__` deixam de rodar.
# ===========================================================================
_AUSENTE = object()
_ORIGINAIS: dict = {}
_NO_INICIO: set = set()


def _fotografar():
    global _NO_INICIO
    if not _NO_INICIO:
        _NO_INICIO = set(sys.modules)


def _guardar(nome):
    if nome not in _ORIGINAIS:
        _ORIGINAIS[nome] = sys.modules.get(nome, _AUSENTE)


def _cascas():
    for sub in ("api", "services", "agents", "comercial", "core", "providers", "tasks"):
        nome = "app." + sub
        atual = sys.modules.get(nome)
        if atual is not None and getattr(atual, "__file__", None) is None:
            continue
        casca = types.ModuleType(nome)
        casca.__path__ = [os.path.join(APP, sub)]
        casca.__package__ = nome
        _guardar(nome)
        sys.modules[nome] = casca
    for nome, caminho in (
        ("app.agents.tools", os.path.join(APP, "agents", "tools")),
        ("app.services.artifacts", os.path.join(APP, "services", "artifacts")),
        ("app.services.intelligence", os.path.join(APP, "services", "intelligence")),
        ("app.comercial.metricas", os.path.join(APP, "comercial", "metricas")),
    ):
        atual = sys.modules.get(nome)
        if atual is not None and getattr(atual, "__file__", None) is None:
            continue
        casca = types.ModuleType(nome)
        casca.__path__ = [caminho]
        casca.__package__ = nome
        _guardar(nome)
        sys.modules[nome] = casca


def _restaurar_sys_modules():
    """Uma suite cujo resultado depende da ORDEM nao mede nada (CLAUDE.md §9.3)."""
    for nome in sorted(sys.modules):
        if nome in _NO_INICIO or nome in _ORIGINAIS:
            continue
        if nome == "app" or nome.startswith("app."):
            _ORIGINAIS[nome] = _AUSENTE
    for nome, anterior in list(_ORIGINAIS.items()):
        if anterior is _AUSENTE:
            sys.modules.pop(nome, None)
        else:
            sys.modules[nome] = anterior
    _ORIGINAIS.clear()


def _abrir_o_ambiente():
    _fotografar()
    try:
        _guardar("app")
        import app  # noqa: F401
        _cascas()
    except Exception:  # noqa: BLE001
        pass


# ===========================================================================
# O placar
#
# 🔴 Tres verbos, e a diferenca entre eles e o que impede tanto o carimbo
# quanto o alarme falso:
#
#   certo()    assercao de verdade. Vermelho aqui e DEFEITO, exit code 1.
#   devendo()  a SPEC-095 ainda nao entregou este bloco. Imprime VERMELHO
#              ESPERADO com o bloco devedor ao lado, CONTA, e o gate final da
#              SPEC so fecha com esta lista VAZIA. O exit code NAO e 1 -- porque
#              dois builders rodam a suite inteira o tempo todo, em paralelo, e
#              um vermelho permanente apagaria a diferenca entre "a SPEC ainda
#              deve o BLOCO D" e "alguem quebrou o produto" (mesma decisao, e
#              mesma razao, de `test_a_fabrica_de_relatorios.py`).
#   par()      a entrada que o guarda TEM de reprovar. Verde aqui e o guarda
#              anunciando que nao guarda nada.
# ===========================================================================
OK = FAIL = 0
PULADOS: list = []
ESPERADOS: list = []
JA_PODEM_VIRAR: list = []


def _p(texto):
    try:
        print(texto)
    except UnicodeEncodeError:
        cod = getattr(sys.stdout, "encoding", None) or "ascii"
        print(texto.encode(cod, "replace").decode(cod, "replace"))


def certo(cond, rotulo, detalhe=""):
    global OK, FAIL
    if cond:
        OK += 1
        _p("  [ok] %s" % rotulo)
    else:
        FAIL += 1
        _p("  [FALHOU] %s" % rotulo + ("\n         %s" % str(detalhe)[:600] if detalhe else ""))
    return bool(cond)


def devendo(cond, rotulo, bloco, detalhe=""):
    global OK, FAIL
    if cond:
        OK += 1
        _p("  [ok] %s" % rotulo)
        JA_PODEM_VIRAR.append("%s   [era devendo('%s')]" % (rotulo, bloco))
    else:
        FAIL += 1
        ESPERADOS.append("%s   (esperado ate %s)" % (rotulo, bloco))
        _p("  VERMELHO-ESPERADO %s   (ate %s)" % (rotulo, bloco)
           + ("\n         %s" % str(detalhe)[:600] if detalhe else ""))
    return bool(cond)


def par(cond_reprovou, rotulo, detalhe=""):
    """A linha de controle. `cond_reprovou` e True quando o guarda ACUSOU."""
    global OK, FAIL
    if cond_reprovou:
        OK += 1
        _p("  [ok] PAR %s -- o guarda acusou" % rotulo)
    else:
        FAIL += 1
        _p("  [FALHOU] PAR %s -- o guarda NAO acusou; ele nao guarda nada" % rotulo
           + ("\n         %s" % str(detalhe)[:400] if detalhe else ""))
    return bool(cond_reprovou)


def pular(rotulo, razao):
    PULADOS.append(rotulo)
    _p("  --   PULADO %s\n         %s" % (rotulo, razao))


def rel(caminho):
    try:
        return os.path.relpath(caminho, RAIZ).replace("\\", "/")
    except Exception:  # noqa: BLE001
        return caminho


def ler(caminho):
    return io.open(caminho, encoding="utf-8", errors="replace").read()


def existe(relativo):
    return os.path.exists(os.path.join(RAIZ, relativo))


def modulo(nome, bloco):
    """Importa um modulo do produto. Ausente ou quebrado => VERMELHO ESPERADO.

    🔴 Nunca estoura e nunca pula: um `ImportError` engolido em silencio faria o
    bloco inteiro sumir da saida, e o executor leria a ausencia como aprovacao.
    """
    try:
        return importlib.import_module(nome)
    except Exception as exc:  # noqa: BLE001
        certo(False, "o modulo %s importa" % nome,
                "%s: %s" % (type(exc).__name__, str(exc)[:200]))
        return None


def atributo(mod, nomes, bloco, onde):
    """O primeiro dos `nomes` que existir. Imprime a lista quando nenhum existe."""
    if mod is None:
        return "", None
    for n in nomes:
        f = getattr(mod, n, None)
        if f is not None:
            return n, f
    certo(False, "%s existe em %s" % (" | ".join(nomes), onde),
            "nenhum destes nomes existe: %s" % ", ".join(nomes))
    return "", None


# ===========================================================================
# O BANCO FALSO -- memoria pura, com os filtros APLICADOS
#
# 🔴 Ele APLICA `.eq/.is_/.in_/.gte/.contains`, em vez de so registra-los. E a
# diferenca entre provar que `_publicar` escreveu a consulta da identidade e
# provar que a SEGUNDA chamada ACHOU a peca da primeira -- que e o [B.a]
# inteiro. Filtro registrado e nao aplicado deixaria o bloco verde com duas
# pecas no banco.
# ===========================================================================
def _valor(linha, coluna):
    """`subject_ref->>id` e `payload->evidence_pack->>pack_id` navegam o objeto."""
    if "->" not in coluna:
        return linha.get(coluna)
    partes = [p.strip().strip("'\"") for p in re.split(r"->>|->", coluna)]
    v = linha
    for p in partes:
        if not isinstance(v, dict):
            return None
        v = v.get(p)
    return v


def _ultimo_segmento(coluna):
    return [p.strip().strip("'\"") for p in re.split(r"->>|->", coluna)][-1]


def _casa(linha, pred):
    op, coluna, valor = pred["op"], pred["coluna"], pred.get("valor")
    v = _valor(linha, coluna)
    if op == "eq":
        return str(v) == str(valor)
    if op == "neq":
        return str(v) != str(valor)
    if op == "is":
        # `.is_(col, "null")` manda a STRING "null" -- e chave ausente e nula.
        return v is None if valor in (None, "null", "NULL") else v is valor
    if op == "in":
        return str(v) in {str(x) for x in (valor or [])}
    if op == "gte":
        return v is not None and str(v) >= str(valor)
    if op == "lte":
        return v is not None and str(v) <= str(valor)
    if op == "contains":
        alvo = valor if isinstance(valor, (list, tuple)) else [valor]
        return all(x in (v or []) for x in alvo)
    if op == "not":
        return not _casa(linha, {"op": pred["sub"], "coluna": coluna, "valor": valor})
    return True


class _Resposta:
    def __init__(self, data, count=None):
        self.data = data
        self.count = count


class _Consulta:
    def __init__(self, banco, tabela):
        self.banco = banco
        self.tabela = tabela
        self.op = "select"
        self.colunas = ""
        self.registro = None
        self.preds: list = []
        self.limite = None
        self.um = False

    # --- leitura ---------------------------------------------------------
    def select(self, colunas="*", **k):
        self.op = "select"
        self.colunas = str(colunas)
        self.opcoes = dict(k)
        return self

    # --- escrita ---------------------------------------------------------
    def insert(self, registro, **k):
        self.op = "insert"
        self.registro = registro
        return self

    def update(self, registro, **k):
        self.op = "update"
        self.registro = registro
        return self

    def upsert(self, registro, **k):
        self.op = "upsert"
        self.registro = registro
        return self

    def delete(self, **k):
        self.op = "delete"
        return self

    # --- filtros ---------------------------------------------------------
    def eq(self, c, v):
        self.preds.append({"op": "eq", "coluna": c, "valor": v}); return self

    def neq(self, c, v):
        self.preds.append({"op": "neq", "coluna": c, "valor": v}); return self

    def is_(self, c, v):
        self.preds.append({"op": "is", "coluna": c, "valor": v}); return self

    def in_(self, c, v):
        self.preds.append({"op": "in", "coluna": c, "valor": v}); return self

    def gte(self, c, v):
        self.preds.append({"op": "gte", "coluna": c, "valor": v}); return self

    def lte(self, c, v):
        self.preds.append({"op": "lte", "coluna": c, "valor": v}); return self

    def contains(self, c, v):
        self.preds.append({"op": "contains", "coluna": c, "valor": v}); return self

    def not_(self, c, sub, v):
        self.preds.append({"op": "not", "sub": sub, "coluna": c, "valor": v}); return self

    @property
    def not_op(self):
        return self

    def order(self, *a, **k):
        return self

    def limit(self, n):
        self.limite = n; return self

    def maybe_single(self):
        self.um = True; return self

    def single(self):
        self.um = True; return self

    # --- execucao --------------------------------------------------------
    def _filtradas(self):
        linhas = [l for l in self.banco.dados.get(self.tabela, [])
                  if all(_casa(l, p) for p in self.preds)]
        if self.limite is not None:
            linhas = linhas[: self.limite]
        return linhas

    def _projetar(self, linhas):
        lista = [c.strip() for c in self.colunas.split(",") if c.strip()]
        if not lista or "*" in lista:
            return [dict(l) for l in linhas]
        # 🔴 Como o PostgREST projeta: a coluna volta pelo ULTIMO segmento.
        return [{_ultimo_segmento(c): _valor(l, c) for c in lista} for l in linhas]

    def execute(self):
        self.banco.consultas.append(
            {"tabela": self.tabela, "op": self.op, "colunas": self.colunas,
             "preds": list(self.preds)})
        if self.op == "select":
            linhas = self._projetar(self._filtradas())
            if self.um:
                # 🔴 `maybe_single()` sobre zero linhas devolve `data=None`, e nao
                # estoura. O primeiro `criar` de uma corretora sem `brand_profiles`
                # passa por aqui: um IndexError faria o guarda acusar o BANCO FALSO
                # em vez do produto.
                return _Resposta(linhas[0] if linhas else None, count=len(linhas))
            return _Resposta(linhas, count=len(linhas))
        if self.op in ("insert", "upsert"):
            regs = self.registro if isinstance(self.registro, list) else [self.registro]
            saida = []
            for r in regs:
                linha = dict(r)
                linha.setdefault("id", "%s-%d" % (self.tabela[:4], self.banco.proximo()))
                self.banco.dados.setdefault(self.tabela, []).append(linha)
                self.banco.escritas.append((self.tabela, self.op, dict(linha)))
                saida.append(dict(linha))
            return _Resposta(saida)
        if self.op == "update":
            tocadas = []
            for linha in self._filtradas():
                linha.update(self.registro)
                tocadas.append(dict(linha))
            self.banco.escritas.append((self.tabela, "update", dict(self.registro)))
            return _Resposta(tocadas)
        if self.op == "delete":
            self.banco.escritas.append((self.tabela, "delete", None))
            return _Resposta([])
        return _Resposta([])


class BancoFalso:
    def __init__(self, dados=None):
        self.dados = copy.deepcopy(dados or {})
        self.escritas: list = []
        self.consultas: list = []
        self._n = 0

    def proximo(self):
        self._n += 1
        return self._n

    def table(self, nome):
        return _Consulta(self, nome)

    # o codigo do produto as vezes recebe o wrapper e faz `.client`
    @property
    def client(self):
        return self

    def escritas_em(self, tabela, op=None):
        return [e for e in self.escritas if e[0] == tabela and (op is None or e[1] == op)]


# ===========================================================================
# O PACK GOLDEN -- tres achados e duas metricas indisponiveis
#
# ⛔ `Seguradora Sentinela` e um nome de SEGURADORA (permitido pela §2 das
# travas). `Produtor Sentinela` e uma SENTINELA DE VAZAMENTO, nao uma pessoa: se
# ele aparecer no pack serializado, no sinal ou no titulo, o M16 da SPEC-094
# quebrou. Nenhum CPF, telefone, apolice ou placa em lugar nenhum.
# ===========================================================================
PRODUTOR_REF = "prod-ref-0001"
ROTULO_SENTINELA = "Produtor Sentinela"
PERIODO = {"inicio": "2026-01-01", "fim": "2026-09-04"}


def golden(ep):
    """`(metricas, anteriores)` que cruzam os TRES limiares declarados.

    🔴 Os limiares sao LIDOS do modulo. Se alguem mudar `LIMIAR_CONCENTRACAO_PCT`
    de 40 para 60, esta fixture para de cruzar -- e o bloco [D1] diz isso, em vez
    de ficar verde medindo zero achado.
    """
    M = ep.MetricResult
    concentracao = round(ep.LIMIAR_CONCENTRACAO_PCT + 6.8, 1)     # 46,8 >= 40,0
    queda_pct = ep.LIMIAR_QUEDA_PCT - 11.4                         # -31,4 <= -20,0
    base = max(ep.PISO_DE_COMISSAO_PARA_QUEDA * 20, 10000.0)       # 10.000 >= 500
    agora_comissao = round(base * (1.0 + queda_pct / 100.0), 2)

    metricas = [
        M(metric_id="commission.broker_accrued", version=1, value=482000.0,
          unit="BRL", period=dict(PERIODO), time_basis="accrual", coverage=1.0),
        M(metric_id="mix.insurer", version=1, value=concentracao, unit="pct",
          period=dict(PERIODO), time_basis="accrual", coverage=1.0,
          breakdown=({"rotulo": "Seguradora Sentinela", "pct": concentracao},
                     {"rotulo": "Seguradora Vizinha", "pct": 21.0})),
        M(metric_id="renewal.exposure", version=1, value=128, unit="count",
          period=dict(PERIODO), time_basis="event", coverage=1.0,
          breakdown=({"faixa": "ja vencidas", "apolices": 37},
                     {"faixa": "vence em 30 dias", "apolices": 91})),
        M(metric_id="producer.performance", version=1, value=4, unit="count",
          period=dict(PERIODO), time_basis="accrual", coverage=0.62,
          breakdown=({"producer_ref": PRODUTOR_REF, "comissao": agora_comissao},)),
        # 📊 duas INDISPONIVEIS: hoje cada uma vira um `callout` inteiro, e um
        # Pulso sem funil, sem mercado e sem repasse imprime quatro caixas
        # dizendo que nao ha dado.
        M(metric_id="quotes.funnel", version=1, value=ep.UNAVAILABLE, unit="count",
          period=dict(PERIODO), time_basis="event"),
        M(metric_id="market.loss_ratio", version=1, value=ep.UNAVAILABLE, unit="ratio",
          period=dict(PERIODO), time_basis="accrual"),
    ]
    anteriores = [
        M(metric_id="producer.performance", version=1, value=4, unit="count",
          period={"inicio": "2025-01-01", "fim": "2025-09-04"}, time_basis="accrual",
          coverage=0.62,
          breakdown=({"producer_ref": PRODUTOR_REF, "comissao": base},)),
    ]
    return metricas, anteriores


def pacote_golden(ep, findings, metricas):
    """O `EvidencePack` REAL do produto -- nao um dublê dele.

    🔴 `_compor` chama `pacote.serializar()` e o pack carrega `provenance`,
    `coverage` e `freshness`. Um dublê com tres atributos passaria a compor e
    estouraria no quarto -- e o vermelho seria do GUARDA, nao do produto. O
    objeto de verdade custa uma linha e mede a coisa certa.
    """
    return ep.EvidencePack(
        company_id=EMPRESA_A, period=dict(PERIODO),
        compare_period={"inicio": "2025-01-01", "fim": "2025-09-04"},
        metrics=list(metricas), findings=list(findings),
        coverage={"minima": 0.62}, freshness="2026-09-04T02:54:00",
        provenance={"provider_key": "infocap", "lido_em": "2026-09-04T02:54:00Z"},
        pack_id="pack-sentinela-095")


class PeriodoFalso:
    rotulo = "2026"
    inicio = "2026-01-01"
    fim = "2026-09-04"


# ===========================================================================
# BLOCO 0 -- GATE ZERO: os seis defeitos de HOJE, com o PAR de cada um
# ===========================================================================
def bloco_0_gate_zero(ctx):
    _p("\n[0] GATE ZERO -- os seis defeitos que a SPEC-095 promete matar")

    # ---- (ii) `_publicar` cria uma peca nova a cada pergunta ---------------
    rc = ctx["relatorios_comerciais"]
    if rc is None or not hasattr(rc, "_publicar"):
        certo(False, "(ii) _publicar existe",
                "app.agents.tools.relatorios_comerciais._publicar nao pode ser lido")
    else:
        assinatura = getattr(rc._publicar, "__code__", None)
        nomes = list(assinatura.co_varnames[: assinatura.co_argcount + assinatura.co_kwonlyargcount]) if assinatura else []
        certo("identidade" in nomes,
                "(ii) `_publicar` aceita `identidade=` -- a peca tem identidade, e a "
                "pergunta repetida vira VERSAO",
                "parametros de hoje: %s. 📊 79 pecas / 16 titulos distintos: o "
                "\"Pulso 360 · 2026\" existe 5 vezes, e nunca houve uma v2." % ", ".join(nomes))
        certo("data_sources" in nomes and "data_as_of" in nomes,
                "(ii/vii) `_publicar` aceita `data_sources=` e `data_as_of=`",
                "📊 `artifact_versions.data_sources = []` em 5/5 Pulsos: `_publicar` "
                "desenha o bloco `sources` na composicao e nao o passa ao `criar`.")

    # ---- (vii) `data_as_of` = now() ---------------------------------------
    svc = ctx["service"]
    if svc is None:
        certo(False, "(vii) ArtifactService pode ser lido")
    else:
        fonte_svc = ler(os.path.join(APP, "services", "artifacts", "service.py"))
        carimbo = re.search(r'"data_as_of":\s*_agora\(\)', fonte_svc)
        certo(carimbo is None,
                "(vii) `_nova_versao` NAO carimba `data_as_of` com a hora da escrita",
                "📊 136/136 versoes tem `data_as_of` = carimbo da escrita, e 30 delas "
                "estao no FUTURO do proprio `created_at` (desvio de relogio por "
                "processo). A tela imprime \"Dados de ...\" em cima disso.")
        criar = getattr(getattr(svc, "ArtifactService", None), "criar", None)
        cod = getattr(criar, "__code__", None)
        nomes = list(cod.co_varnames[: cod.co_argcount + cod.co_kwonlyargcount]) if cod else []
        certo("data_as_of" in nomes and "tags" in nomes and "confidence_note" in nomes,
                "(v/vii) `criar` aceita `tags=`, `data_as_of=` e `confidence_note=`",
                "parametros de hoje: %s" % ", ".join(nomes))

    # ---- (v) o canario nao se declara --------------------------------------
    certo(existe("scripts/canario_095.py"),
            "(v) `backend/scripts/canario_095.py` existe -- o canario roda o caminho REAL",
            "📊 `test_o_canario_do_pulso_360.py` substitui `rel._publicar` por um "
            "capturador: ele NUNCA executa o `_publicar` real, e exportar a variavel "
            "ali seria decorativo. Quem a exporta e o script novo.")

    # ---- (iii) e (vi) o briefing -------------------------------------------
    bs = ctx["briefing_service"]
    if bs is None:
        certo(False, "(iii/vi) briefing_service pode ser lido")
    else:
        item = getattr(bs, "ItemDeBriefing", None)
        campos = set(getattr(item, "__dataclass_fields__", {}) or {}) if item else set()
        certo({"why_now", "next_step"} <= campos,
                "(vi) `ItemDeBriefing` tem `why_now` e `next_step`",
                "📊 `intelligence_findings`: `why_now` preenchido em 12/12 e "
                "`next_step` em 11/12. `ItemDeBriefing` nao tem campo para nenhum "
                "dos dois -- o porque e o proximo passo morrem UMA FUNCAO antes da "
                "tela. Campos de hoje: %s" % ", ".join(sorted(campos)))
        if item is not None and {"why_now", "next_step"} <= campos:
            d = item(item_type="finding", section="precisa_de_voce",
                     headline="Fila acumulada", summary="61 atendimentos parados",
                     why_now="a fila cresceu 40% em 24h",
                     next_step="comecar pelos parados ha mais de 48h").como_dict(1)
            certo(d.get("why_now") and d.get("next_step"),
                    "(vi) `como_dict` EMITE why_now e next_step",
                    "o campo existe na dataclass e nao sai no jsonb: chaves emitidas "
                    "= %s" % ", ".join(sorted(d)))

        narrativa = getattr(bs, "_narrativa", None)
        if narrativa is None:
            certo(False, "(iii) `_narrativa` existe")
        else:
            acionaveis = ctx["acionaveis"](bs)
            manchete, _resumo = narrativa("daily_operational", acionaveis, [], [], 0, [])
            certo(manchete == acionaveis[0].headline,
                    "(iii) a manchete E o achado principal, nao a CONTAGEM",
                    "manchete de hoje: %r · headline do item 1: %r. 📊 A mesma string "
                    "(\"2 item(ns) esperando voce hoje\") foi a manchete de 5 dias "
                    "diferentes." % (manchete, acionaveis[0].headline))

    # ---- (iv) o Pulso nao diz o que fazer ----------------------------------
    blocos, erro = ctx["compor_pulso"]()
    if erro:
        certo(False, "(iv) `_compor` do Pulso roda", erro)
    else:
        tipos = [b.get("block") for b in blocos]
        certo("actions" in tipos,
                "(iv) o Pulso tem a secao \"O que importa agora\" (bloco `actions`)",
                "📊 13 secoes, nenhuma diz o que fazer. O bloco `actions` existe em "
                "`blocks.py:298` desde a SPEC-057 e nenhum relatorio o usa. Blocos "
                "de hoje: %s" % ", ".join(tipos))
        capa = (blocos[0].get("props") or {}) if blocos else {}
        titulo = str(capa.get("title") or "")
        certo(not titulo.startswith("O período inteiro") and "Pulso 360 · " not in titulo,
                "(iv) a CAPA do Pulso e o achado, nao o rotulo do periodo",
                "capa de hoje: %r. 📊 `executive_intelligence.py:1539` grava "
                "`titulo=\"Pulso 360 · %%s\"` e `subtitulo=\"O periodo inteiro, com a "
                "fonte de cada numero\"` FIXOS." % titulo)


# ===========================================================================
# BLOCO B -- IDENTIDADE
# ===========================================================================
def bloco_B_identidade(ctx):
    _p("\n[B] IDENTIDADE -- uma peca, muitas versoes; a data do dado e a do dado")

    rc = ctx["relatorios_comerciais"]
    svc = ctx["service"]

    # ---- B.a · duas perguntas iguais = UMA peca, DUAS versoes --------------
    if rc is None or not hasattr(rc, "_publicar"):
        certo(False, "[B.a] duas publicacoes com a mesma identidade => 1 peca, 2 versoes", "`_publicar` nao pode ser lido")
    else:
        identidade = {"kind": "periodo", "id": "2026", "label": "2026",
                      "produtor": "autobrokers.chat"}
        banco, erro = ctx["publicar_duas_vezes"](identidade, identidade)
        if erro:
            certo(False, "[B.a] duas publicacoes com a mesma identidade => 1 peca, 2 versoes", erro)
        else:
            pecas = banco.escritas_em("artifacts", "insert")
            versoes = banco.escritas_em("artifact_versions", "insert")
            certo(len(pecas) == 1 and len(versoes) == 2,
                    "[B.a] duas perguntas iguais => 1 insert em `artifacts`, 2 em `artifact_versions`",
                    "hoje: %d peca(s) e %d versao(oes). 📊 E por isso que o \"Pulso 360 · "
                    "2026\" existe 5 vezes na Resulta e `max(version)` nunca passou de 1."
                    % (len(pecas), len(versoes)))
            atual = (banco.dados.get("artifacts") or [{}])[0]
            certo(int(atual.get("current_version") or 0) == 2,
                    "[B.a] `current_version` chega a 2",
                    "current_version = %r" % atual.get("current_version"))
            fontes = [v for _t, _o, v in versoes if v.get("data_sources")]
            certo(len(fontes) == len(versoes) and all(f["data_sources"] for f in fontes),
                    "[B.a] toda versao grava `data_sources` nao vazio",
                    "📊 `artifact_versions.data_sources = []` em 5/5 Pulsos: a "
                    "composicao desenha o bloco `sources` e nao passa `data_sources=` "
                    "ao `criar`.")

            # PAR -- identidades DIFERENTES tem de continuar criando duas pecas.
            outra = dict(identidade); outra["id"] = "2025"; outra["label"] = "2025"
            banco2, erro2 = ctx["publicar_duas_vezes"](identidade, outra)
            if erro2:
                pular("PAR [B.a] identidades diferentes", erro2)
            else:
                par(len(banco2.escritas_em("artifacts", "insert")) == 2,
                    "[B.a] identidades DIFERENTES criam duas pecas",
                    "o colapso engoliu duas pecas que sao de periodos diferentes")

            # PAR -- identidade VAZIA nao pode colapsar. 📊 `subject_ref->>'id' = ''`
            # casa 6 Pulsos, 14 Raio-X e 14 Radares legados na Resulta: colapsar por
            # ela juntaria peca de template e periodo diferentes numa so.
            vazia = {"kind": "chat", "id": "", "label": "", "produtor": "autobrokers.chat"}
            banco3, erro3 = ctx["publicar_duas_vezes"](vazia, vazia)
            if erro3:
                pular("PAR [B.a] identidade vazia", erro3)
            else:
                par(len(banco3.escritas_em("artifacts", "insert")) == 2,
                    "[B.a] identidade VAZIA nao colapsa (E6)",
                    "duas publicacoes com `id` vazio viraram UMA peca -- 📊 na Resulta "
                    "isso casaria 34 pecas legadas de tres templates diferentes")

    # ---- B.b · a data do dado e a do dado ---------------------------------
    if svc is None:
        certo(False, "[B.b] `data_as_of` NULL quando ninguem sabe a data")
    else:
        banco = BancoFalso({"artifacts": [], "brand_profiles": []})
        s = svc.ArtifactService(banco)
        try:
            s.criar(company_id=EMPRESA_A, title="t", template_key="executive.pulse360",
                    payload={}, composition=[], kind="report", origin="chat")
            sem = banco.escritas_em("artifact_versions", "insert")[-1][2]
            certo("data_as_of" not in sem or sem.get("data_as_of") is None,
                    "[B.b] sem data passada => `data_as_of` NULL",
                    "gravou data_as_of = %r (e o carimbo da ESCRITA, nao a data do "
                    "dado)" % sem.get("data_as_of"))
        except TypeError as exc:
            certo(False, "[B.b] sem data passada => `data_as_of` NULL",
                    "criar() ainda nao aceita a chamada: %s" % str(exc)[:200])
        except Exception as exc:  # noqa: BLE001
            certo(False, "[B.b] `criar` roda contra o BancoFalso",
                  "%s: %s" % (type(exc).__name__, str(exc)[:200]))

        # PAR -- com data passada, ela chega ao banco inteira.
        corte = datetime(2026, 9, 4, 2, 54, tzinfo=timezone.utc)
        banco = BancoFalso({"artifacts": [], "brand_profiles": []})
        s = svc.ArtifactService(banco)
        try:
            s.criar(company_id=EMPRESA_A, title="t", template_key="executive.pulse360",
                    payload={}, composition=[], kind="report", origin="chat",
                    data_as_of=corte)
            com = banco.escritas_em("artifact_versions", "insert")[-1][2]
            gravado = str(com.get("data_as_of") or "")
            certo(gravado.startswith("2026-09-04T02:54"),
                    "[B.b] com data passada => a data PASSADA, e nao a de agora", "gravou %r" % gravado)
            par(not gravado.startswith(datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")),
                "[B.b] a data gravada nao e a hora da escrita",
                "a data passada foi ignorada e o carimbo voltou")
        except TypeError:
            certo(False, "[B.b] com data passada => a data PASSADA",
                    "`criar` ainda nao tem o parametro `data_as_of`")
        except Exception as exc:  # noqa: BLE001
            certo(False, "[B.b] `criar` com data roda", "%s: %s" % (type(exc).__name__, str(exc)[:200]))

    # ---- B.c · o canario se declara ---------------------------------------
    if rc is not None and hasattr(rc, "_publicar"):
        anterior = os.environ.get("AUTOBROKERS_CANARIO")
        try:
            os.environ["AUTOBROKERS_CANARIO"] = "1"
            banco, erro = ctx["publicar_uma_vez"]({"kind": "periodo", "id": "2026",
                                                   "label": "2026", "produtor": "autobrokers.chat"})
            if erro:
                certo(False, "[B.c] com AUTOBROKERS_CANARIO=1 a peca nasce com tags=['canario']", erro)
            else:
                peca = (banco.escritas_em("artifacts", "insert") or [(None, None, {})])[-1][2]
                certo("canario" in (peca.get("tags") or []),
                        "[B.c] com AUTOBROKERS_CANARIO=1 a peca nasce com tags=['canario']",
                        "tags = %r. 📊 100%% dos relatorios \"do chat\" da Resulta sao "
                        "canario de execucao de SPEC e NADA os distingue: `tags` "
                        "preenchida em 0/136." % (peca.get("tags"),))
        finally:
            if anterior is None:
                os.environ.pop("AUTOBROKERS_CANARIO", None)
            else:
                os.environ["AUTOBROKERS_CANARIO"] = anterior

        # PAR -- sem a variavel, a peca da corretora NAO nasce marcada.
        os.environ.pop("AUTOBROKERS_CANARIO", None)
        banco, erro = ctx["publicar_uma_vez"]({"kind": "periodo", "id": "2026",
                                               "label": "2026", "produtor": "autobrokers.chat"})
        if erro:
            pular("PAR [B.c] sem a variavel", erro)
        else:
            peca = (banco.escritas_em("artifacts", "insert") or [(None, None, {})])[-1][2]
            par("canario" not in (peca.get("tags") or []),
                "[B.c] sem a variavel a peca NAO e marcada",
                "toda peca esta nascendo com a tag de canario -- a biblioteca inteira "
                "sumiria da lista")

    # ---- B.d · arquivar e desarquivar -------------------------------------
    if svc is not None:
        Servico = getattr(svc, "ArtifactService", None)
        tem = Servico is not None and hasattr(Servico, "arquivar") and hasattr(Servico, "desarquivar")
        if not tem:
            certo(False, "[B.d] `arquivar` / `desarquivar` existem",
                    "📊 arquivados = 0 em 3 corretoras: a coluna `archived_at` existe e "
                    "nunca teve escritor. A limpeza do B.4 e `archived_at`, nunca DELETE.")
        else:
            banco = BancoFalso({"artifacts": [{"id": "a1", "company_id": EMPRESA_A,
                                               "archived_at": None, "status": "ready",
                                               "title": "peca", "tags": ["canario"]}],
                                "artifact_events": []})
            s = Servico(banco)
            try:
                s.arquivar(EMPRESA_A, "a1", motivo="canário de execução de SPEC — SPEC-095 B.4")
                linha = banco.dados["artifacts"][0]
                eventos = [e for e in banco.escritas_em("artifact_events", "insert")
                           if e[2].get("event_type") == "artifact.archived"]
                certo(linha.get("archived_at") and eventos,
                        "[B.d] `arquivar` grava `archived_at` E o evento com o motivo",
                        "archived_at=%r · eventos=%d -- sem o evento o ROLLBACK do B.4 "
                        "nao tem por onde achar as 35 pecas"
                        % (linha.get("archived_at"), len(eventos)))
                certo(linha.get("status") == "ready",
                        "[B.d] arquivar NAO mexe no `status` da peca",
                        "status virou %r" % linha.get("status"))
                s.desarquivar(EMPRESA_A, "a1")
                par(banco.dados["artifacts"][0].get("archived_at") is None,
                    "[B.d] `desarquivar` devolve a peca",
                    "a peca continuou arquivada depois do desarquivar -- a limpeza "
                    "seria irreversivel na pratica")
            except TypeError as exc:
                certo(False, "[B.d] `arquivar` / `desarquivar` com a assinatura da SPEC", "assinatura recusou a chamada: %s" % str(exc)[:200])
            except Exception as exc:  # noqa: BLE001
                certo(False, "[B.d] `arquivar` roda", "%s: %s" % (type(exc).__name__, str(exc)[:200]))

    # ---- B.e · o script da limpeza nao escreve em --dry-run ----------------
    certo(existe("scripts/arquivar_relatorios_de_teste_095.py"),
            "[B.e] `backend/scripts/arquivar_relatorios_de_teste_095.py` existe",
            "📊 esperado: Resulta 34 · AutoFleet 1 · Amandus 0 candidatos, listados "
            "por corretora/template/dia -- sem titulo e sem id inteiro.")
    if existe("scripts/arquivar_relatorios_de_teste_095.py"):
        fonte_script = ler(os.path.join(RAIZ, "scripts", "arquivar_relatorios_de_teste_095.py"))
        certo("--dry-run" in fonte_script or "dry_run" in fonte_script,
                "[B.e] o script tem `--dry-run` (e ele e o PADRAO)")
        certo(not re.search(r"\.delete\(\)", fonte_script),
                "[B.e] o script NUNCA apaga -- so `archived_at`",
                "achei `.delete()` no script: a limpeza e reversivel por decisao da §2")
        certo("canario" in fonte_script,
                "[B.e] o script pula peca com `tags @> {canario}`",
                "as pecas do canario desta SPEC se arquivam sozinhas (F(f)); arquiva-las "
                "de novo aqui misturaria as duas contagens do VERIFY")

    # ---- B.f · o pack_id sem o payload cru (E4) ----------------------------
    le = ctx["listar_entregas"]
    if le is None or not hasattr(le, "_packs_das_versoes"):
        certo(False, "[B.f] `_packs_das_versoes` pode ser lido")
    else:
        banco = BancoFalso({"artifact_versions": [{
            "artifact_id": "a1", "company_id": EMPRESA_A, "status": "published",
            "payload": {"evidence_pack": {"pack_id": "pack-sentinela-095"},
                        "rotulos_de_produtor": {PRODUTOR_REF: ROTULO_SENTINELA}},
        }]})
        saida = le._packs_das_versoes(banco, EMPRESA_A, ["a1"])
        consulta = next((c for c in banco.consultas if c["tabela"] == "artifact_versions"), {})
        colunas = str(consulta.get("colunas") or "")
        certo("payload->evidence_pack->>pack_id" in colunas,
                "[B.f] a consulta pede `payload->evidence_pack->>pack_id`, nunca `payload`",
                "select de hoje: %r. 📊 64.246 bytes por versao, 5.890 deles em "
                "`rotulos_de_produtor` -- e o nome do produtor nao pode sair do "
                "Artifact do tenant (M16 da SPEC-094)." % colunas)
        certo(saida.get("a1") == "pack-sentinela-095",
              "[B.f] o pack_id continua chegando",
              "a funcao devolveu %r -- o dublê projeta a coluna pelo ULTIMO segmento, "
              "como o PostgREST faz" % (saida,))
        # 🔴 O PAR mede o DETECTOR, nao repete a assercao acima: a mesma regra
        # aplicada as duas formas do select, com veredito OPOSTO. Repetir a
        # assercao aqui daria dois vermelhos pelo mesmo fato e zero prova de que
        # a regra sabe aprovar.
        def paga_o_payload_inteiro(sel):
            return re.search(r"(^|,)\s*payload\s*(,|$)", sel) is not None

        par(paga_o_payload_inteiro("artifact_id, payload, status"),
            "[B.f] o detector acha o `payload` inteiro quando ele esta la",
            "o detector nao acusa nem o select de hoje -- ele nao guarda nada")
        par(not paga_o_payload_inteiro(
                "artifact_id, payload->evidence_pack->>pack_id, status"),
            "[B.f] o detector NAO acusa o caminho estreito (veredito oposto)",
            "o detector acusa tambem a forma certa -- ele reprovaria o conserto")


# ===========================================================================
# BLOCO D -- A NARRATIVA
# ===========================================================================
CANDIDATOS_PLAYBOOK = ("PLAYBOOKS", "PLAYBOOK_POR_KIND", "POR_KIND", "NARRATIVAS",
                       "POR_ACHADO", "PLAYBOOK")
CAMPOS_DO_ACHADO = ("titulo", "por_que_importa", "o_que_fazer", "pergunta")


def bloco_D_narrativa(ctx):
    _p("\n[D] A NARRATIVA -- o relatorio abre pelo achado e diz o que fazer")

    ep = ctx["evidence_pack"]
    nar = ctx["narrativa"]

    # ---- D1 · todo kind que vira sinal tem playbook ------------------------
    if nar is None:
        certo(False, "[D1] `app/comercial/narrativa.py` existe e importa",
                "📊 `evidence_pack.py:684` e `:712` escrevem o achado SEM numero e SEM "
                "sujeito, DE PROPOSITO (o nome fica no Artifact) -- certo para o modelo, "
                "inutil para o dono.")
    else:
        nome, tabela = atributo(nar, CANDIDATOS_PLAYBOOK, "BLOCO D.1", "narrativa.py")
        if tabela is not None:
            _p("      tabela de playbooks: `%s` (%d entradas)"
               % (nome, len(tabela) if hasattr(tabela, "__len__") else -1))
            faltando = [k for k in ep.FINDINGS_QUE_VIRAM_SINAL if k not in tabela]
            certo(not faltando,
                    "[D1] todo kind de FINDINGS_QUE_VIRAM_SINAL tem playbook", "sem playbook: %s" % ", ".join(faltando))
            par(bool(ep.FINDINGS_QUE_VIRAM_SINAL),
                "[D1] ha kind para conferir",
                "FINDINGS_QUE_VIRAM_SINAL esta vazio -- o guarda passaria por vacuidade")

    # ---- D1b · o motor sobre o pack golden ---------------------------------
    metricas, anteriores = golden(ep)
    achados = ep.achar_findings(metricas, anteriores)
    kinds = [a.get("kind") for a in achados]
    _p("      pack golden -> %d achado(s): %s" % (len(achados), ", ".join(kinds)))
    certo({ep.CONCENTRACAO, ep.EXPOSICAO_DE_RENOVACAO, ep.QUEDA_DE_PRODUTOR} <= set(kinds),
          "[D1] o pack golden cruza os TRES limiares declarados",
          "cruzou so %s -- a fixture parou de exercer os limiares (eles sao lidos do "
          "modulo, entao alguem mudou o valor ou a regra)" % ", ".join(kinds))

    quatro = [a for a in achados
              if a.get("vira_sinal") and all(str(a.get(c) or "").strip() for c in CAMPOS_DO_ACHADO)]
    certo(len(quatro) == len([a for a in achados if a.get("vira_sinal")]),
            "[D1] todo achado que vira sinal tem titulo · por_que_importa · o_que_fazer · pergunta",
            "com os quatro campos: %d de %d. Campos do 1o achado: %s"
            % (len(quatro), len([a for a in achados if a.get("vira_sinal")]),
               ", ".join(sorted(achados[0])) if achados else "-"))

    # O titulo carrega o NUMERO do achado. 💭 A copy e do builder; o guarda
    # confere a FORMA (numero, quatro campos, zero nome), nunca a frase.
    numeros = {ep.CONCENTRACAO: "valor_pct", ep.EXPOSICAO_DE_RENOVACAO: "apolices",
               ep.QUEDA_DE_PRODUTOR: "delta_pct"}
    sem_numero = []
    for a in achados:
        campo = numeros.get(a.get("kind"))
        titulo = str(a.get("titulo") or "")
        if campo is None or not titulo:
            continue
        valor = a.get(campo)
        formas = {str(valor), str(abs(valor)) if isinstance(valor, (int, float)) else str(valor)}
        formas |= {f.replace(".", ",") for f in list(formas)}
        formas |= {str(int(abs(valor))) if isinstance(valor, (int, float)) else str(valor)}
        if not any(f and f in titulo for f in formas):
            sem_numero.append("%s: %r nao contem %r" % (a.get("kind"), titulo, valor))
    certo(not sem_numero and bool([a for a in achados if a.get("titulo")]),
            "[D1] o titulo do achado contem o NUMERO dele",
            "; ".join(sem_numero) or "nenhum achado tem `titulo` para conferir")

    # ⛔ ZERO nome de pessoa no pack e no sinal (M16 da SPEC-094).
    texto = json.dumps(achados, ensure_ascii=False, default=str)
    certo(ROTULO_SENTINELA not in texto and "rotulos_de_produtor" not in texto,
          "[D1] nenhum nome de produtor no achado",
          "a sentinela %r vazou para o pack" % ROTULO_SENTINELA)
    par(ROTULO_SENTINELA in json.dumps({"rotulos_de_produtor": {PRODUTOR_REF: ROTULO_SENTINELA}},
                                       ensure_ascii=False),
        "[D1] o detector de nome CONSEGUE achar a sentinela",
        "o detector nao acha a sentinela nem quando ela esta la -- ele nao guarda nada")

    # ---- D2 · o Pulso abre pelo achado -------------------------------------
    blocos, erro = ctx["compor_pulso"]()
    if erro:
        certo(False, "[D2] `_compor` do Pulso roda sobre o pack golden", erro)
    else:
        tipos = [b.get("block") for b in blocos]
        acoes = [b for b in blocos if b.get("block") == "actions"]
        certo(len(acoes) == 1,
                "[D2] existe UMA secao `actions` -- \"O que importa agora\"", "blocos: %s" % ", ".join(tipos))
        if acoes:
            itens = (acoes[0].get("props") or {}).get("items") or []
            viram_sinal = [a for a in achados if a.get("vira_sinal")]
            certo(len(itens) == len(viram_sinal),
                    "[D2] um item de acao por achado que vira sinal (%d)" % len(viram_sinal), "a secao tem %d item(ns)" % len(itens))
        capa = (blocos[0].get("props") or {}) if blocos else {}
        mais_severo = next((a for a in achados if a.get("vira_sinal")), {})
        certo(str(capa.get("title") or "") == str(mais_severo.get("titulo") or "<sem-titulo>"),
                "[D2] a CAPA e o titulo do achado mais severo",
                "capa=%r · achado=%r" % (capa.get("title"), mais_severo.get("titulo")))

        # As INDISPONIVEIS colapsam numa linha, em vez de uma caixa cada.
        callouts = [b for b in blocos if b.get("block") == "callout"]
        indisponiveis = [m for m in metricas if m.indisponivel]
        certo(len(callouts) == 0,
                "[D2] metrica indisponivel NAO vira um `callout` cada (%d indisponiveis)"
                % len(indisponiveis),
                "%d callout(s). 📊 As secoes 4, 8, 9, 10, 11 e 12 tem o ramo: um Pulso "
                "sem funil, sem mercado e sem repasse imprime QUATRO caixas dizendo que "
                "nao ha dado." % len(callouts))
        prosa = [b for b in blocos if b.get("block") == "prose"]
        certo(any("não deu para medir" in json.dumps(b, ensure_ascii=False) for b in prosa),
                "[D2] o que nao deu para medir e UMA linha",
                "%d bloco(s) `prose`, nenhum com a linha unica" % len(prosa))

        # ⛔ M16 -- o pack serializado nao carrega nome nem o mapa de rotulos.
        composicao = json.dumps(blocos, ensure_ascii=False, default=str)
        certo("rotulos_de_produtor" not in composicao,
              "[D2] a composicao nao carrega o MAPA de rotulos de produtor",
              "`rotulos_de_produtor` apareceu na composicao")

        # PAR -- pack SEM achado: a capa cai para a comissao, nao para uma frase vazia.
        vazio, erro2 = ctx["compor_pulso"](sem_achado=True)
        if erro2:
            pular("PAR [D2] pack sem achado", erro2)
        else:
            capa_vazia = str(((vazio[0] if vazio else {}).get("props") or {}).get("title") or "")
            par(capa_vazia != "" and capa_vazia != str(mais_severo.get("titulo") or ""),
                "[D2] pack SEM achado nao repete o titulo do pack COM achado",
                "capa do pack vazio = %r" % capa_vazia)

    # ---- D3 · a manchete e o achado; o porque chega ------------------------
    bs = ctx["briefing_service"]
    if bs is not None and hasattr(bs, "_narrativa"):
        acionaveis = ctx["acionaveis"](bs)
        manchete, resumo = bs._narrativa("daily_operational", acionaveis, [], [], 0, [])
        certo(manchete == acionaveis[0].headline,
                "[D3] a manchete e a headline do item de maior prioridade", "manchete=%r" % manchete)
        # N = os que FICARAM na peca (E2), nunca o tamanho da lista inteira.
        certo(("e mais %d" % (len(acionaveis) - 1)) in resumo or (len(acionaveis) == 1),
                "[D3] o resumo diz \"e mais N ponto(s)\" com N = o que FICOU",
                "resumo=%r · acionaveis=%d. 📊 `:269` corta em `max_itens` e `:314` conta "
                "a lista INTEIRA: hoje a manchete promete pontos que a peca nao contem."
                % (resumo, len(acionaveis)))
        # 🔴 E2 -- com M = 0 a frase de trabalhos SOME. 📊 Depois do D.5, M = 0 em
        # 5 de 5 dias medidos: a promessa de "20 trabalhos prontos" era o relogio.
        certo("trabalho(s)" not in manchete and "trabalho(s) pronto" not in resumo,
                "[D3] com ZERO trabalho pedido, a frase de trabalhos NAO aparece (E2)", "manchete=%r · resumo=%r" % (manchete, resumo))
        par("trabalho" in bs._narrativa("daily_operational", acionaveis,
                                        [{"id": "w1", "outcome_title": "Cobranca"}],
                                        [], 0, [])[1],
            "[D3] com trabalho pedido a frase VOLTA",
            "a frase sumiu tambem quando ha trabalho -- o guarda nao distingue os dois casos")

        # O ramo semanal mantem a forma dele, com a mesma regra do M.
        m_semanal, r_semanal = bs._narrativa("weekly_executive", acionaveis, [], [], 0, [])
        certo("0 trabalho(s)" not in m_semanal and "0 trabalho(s)" not in r_semanal,
                "[D3] o ramo `weekly_executive` tambem esconde \"0 trabalho(s)\" (E2)", "manchete=%r" % m_semanal)

    # ---- D5 · o briefing sem o relogio da plataforma -----------------------
    if bs is not None and hasattr(bs, "compor"):
        # 📊 40 de 41 itens `work_run`/`result` dos 5 ultimos briefings da Resulta
        # vem de Work Run `system` -- 70,2% de todos os 57 itens do briefing.
        relogio = [{"id": "s%d" % n, "outcome_title": "Procurar o que mudou na operação",
                    "status": "completed", "progress_percent": 0,
                    "result_summary": "0 regra(s) executada(s)", "source_type": "system",
                    "finished_at": "2026-09-04T02:00:00Z"} for n in range(4)]
        # 🔴 Os dois pedidos sao DIFERENTES de proposito. Iguais, a deduplicacao
        # do D.5 os colapsaria e o guarda mediria DOIS fatores num numero so --
        # e um "1 de 6" nao diria se o filtro comeu demais ou se o colapso
        # funcionou (CLAUDE.md §9.2: varie UM fator por vez). O colapso tem
        # medicao propria, logo abaixo.
        pedidos = [
            {"id": "c0", "outcome_title": "Cobrança Feita rodou", "status": "completed",
             "progress_percent": 100, "result_summary": "2 boletos baixados",
             "source_type": "chat", "finished_at": "2026-09-04T07:00:00Z"},
            {"id": "c1", "outcome_title": "Radar de renovações gerado", "status": "completed",
             "progress_percent": 100, "result_summary": "128 apólices na janela",
             "source_type": "routine", "finished_at": "2026-09-04T07:30:00Z"},
        ]
        try:
            spec = bs.compor(
                company_id=EMPRESA_A, briefing_type="daily_operational",
                findings=[], recomendacoes=[], trabalhos_em_curso=[],
                resultados=relogio + pedidos, outcomes=[], faltando=[],
                period_start=datetime(2026, 9, 4, tzinfo=timezone.utc),
                period_end=datetime(2026, 9, 4, 8, tzinfo=timezone.utc))
            resultados = [i for i in spec.itens if i.item_type == "result"]
            certo(len(resultados) == 2,
                    "[D5] `compor` deixa passar so o que a corretora PEDIU (2 de 6)",
                    "%d item(ns) de resultado. 📊 6 dos 14 itens do briefing de 04/09 "
                    "eram o MESMO Work Run `intelligence.detect_signals` repetido."
                    % len(resultados))
            par(len(bs.compor(
                    company_id=EMPRESA_A, briefing_type="daily_operational",
                    findings=[], recomendacoes=[], trabalhos_em_curso=[],
                    resultados=pedidos, outcomes=[], faltando=[],
                    period_start=datetime(2026, 9, 4, tzinfo=timezone.utc),
                    period_end=datetime(2026, 9, 4, 8, tzinfo=timezone.utc),
                ).itens) > 0,
                "[D5] sem nenhum `system`, os pedidos continuam aparecendo",
                "o filtro comeu tambem o que a corretora pediu")

            # Deduplicacao por chave DECLARADA (§3 ③): (outcome_title, status).
            iguais = [dict(pedidos[0]), dict(pedidos[0])]
            iguais[1]["id"] = "c9"
            spec2 = bs.compor(
                company_id=EMPRESA_A, briefing_type="daily_operational",
                findings=[], recomendacoes=[], trabalhos_em_curso=[],
                resultados=iguais, outcomes=[], faltando=[],
                period_start=datetime(2026, 9, 4, tzinfo=timezone.utc),
                period_end=datetime(2026, 9, 4, 8, tzinfo=timezone.utc))
            dois_iguais = [i for i in spec2.itens if i.item_type == "result"]
            certo(len(dois_iguais) == 1 and "+1" in (dois_iguais[0].headline
                                                       + dois_iguais[0].summary),
                    "[D5] dois Work Runs iguais viram UM item com \"(+1 iguais)\"",
                    "%d item(ns): %s. 📊 35,1%% dos itens dentro do MESMO briefing sao "
                    "copia exata (20 de 57)."
                    % (len(dois_iguais), [i.headline for i in dois_iguais]))
        except TypeError as exc:
            certo(False, "[D5] `compor` aceita work_runs com `source_type`",
                    "a chamada foi recusada: %s" % str(exc)[:200])
        except Exception as exc:  # noqa: BLE001
            certo(False, "[D5] `compor` roda", "%s: %s" % (type(exc).__name__, str(exc)[:250]))


# ===========================================================================
# BLOCO C -- CONTROLE: o guarda sabe falhar, e a arvore ficou limpa
# ===========================================================================
def bloco_C_controle(ctx):
    _p("\n[C] CONTROLE -- o guarda sabe falhar, e nada ficou para tras")

    par(True, "o placar CONSEGUE reprovar", "")
    certo(os.environ.get("SEM_REDE") == "1",
          "a rede estava fechada durante a medicao",
          "SEM_REDE=%r" % os.environ.get("SEM_REDE"))
    try:
        socket.socket().connect(("198.51.100.7", 80))
        certo(False, "o bloqueio de rede esta em pe", "uma conexao externa passou")
    except RuntimeError:
        certo(True, "o bloqueio de rede esta em pe")
    except Exception as exc:  # noqa: BLE001
        certo(False, "o bloqueio de rede esta em pe",
              "a conexao falhou por outra razao (%s) -- o bloqueio pode nao estar ativo"
              % type(exc).__name__)

    certo(os.environ.get("AUTOBROKERS_CANARIO") is None,
          "`AUTOBROKERS_CANARIO` nao vazou para o resto da sessao",
          "a variavel ficou como %r" % os.environ.get("AUTOBROKERS_CANARIO"))

    sobrando = [rel(os.path.join(RAIZ, c)) for c, *_ in MUTACOES
                if os.path.exists(os.path.join(RAIZ, c + ".bak-095"))]
    certo(not sobrando, "nenhuma copia `.bak-095` ficou na arvore",
          "sobraram: %s" % ", ".join(sobrando))

    # ⛔ Nenhuma fixture deste arquivo carrega dado de pessoa.
    fonte_do_guarda = ler(os.path.abspath(__file__))
    proibidos = re.findall(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b|\b\d{11}\b|\b55\d{10,11}\b",
                           fonte_do_guarda)
    certo(not proibidos, "nenhum CPF/telefone nas fixtures deste guarda",
          "achei: %s" % proibidos[:3])
    # 🔴 A amostra e MONTADA em runtime, e nao escrita como literal. Escrita
    # inteira, ela apareceria na FONTE deste arquivo -- e a assercao acima, que
    # varre a propria fonte, acusaria a LINHA DE CONTROLE como se fosse fixture.
    # 📊 Aconteceu na primeira rodada deste guarda, 04/09/2026: um vermelho de
    # verdade apontando para o proprio guarda. Um guarda que se auto-acusa ensina
    # a ignorar o guarda.
    amostra = ".".join(["123", "456", "789"]) + "-01"
    par(bool(re.findall(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b", amostra)),
        "o detector de CPF CONSEGUE achar um CPF",
        "o detector nao acha um CPF nem quando ele esta la")

    # E todo arquivo que este guarda declara mutar precisa existir: uma entrada
    # morta em `MUTACOES` e uma mutacao que nao aplica, e mutacao que nao aplica
    # NAO e mutacao passada (CLAUDE.md §9.5).
    fantasmas = [c for c, *_ in MUTACOES if not existe(c)]
    certo(not fantasmas, "todo arquivo declarado em MUTACOES existe",
            "ainda nao existem: %s" % ", ".join(sorted(set(fantasmas))))


# ===========================================================================
# As mutacoes por COPIA -- so com `--mutar`
# ===========================================================================
def rodar_mutacoes(ctx):
    _p("\n[M] MUTACOES POR COPIA -- a arvore precisa estar parada")
    for caminho, de, para, rotulo in MUTACOES:
        alvo = os.path.join(RAIZ, caminho)
        if not os.path.exists(alvo):
            pular("mutacao %s (%s)" % (rotulo, caminho), "o arquivo ainda nao existe")
            continue
        original = ler(alvo)
        if de not in original:
            pular("mutacao %s (%s)" % (rotulo, caminho),
                  "a ancora %r nao existe -- mutacao que nao aplica NAO e mutacao passada"
                  % de[:60])
            continue
        backup = alvo + ".bak-095"
        shutil.copyfile(alvo, backup)
        try:
            io.open(alvo, "w", encoding="utf-8").write(original.replace(de, para, 1))
            antes = FAIL
            try:
                ctx["remedir"](rotulo)
                ficou_vermelho = FAIL > antes
            except RuntimeError as exc:
                if "MUTACAO_QUEBROU_O_MODULO" not in str(exc):
                    raise
                _p("        o arquivo mutado NAO carrega (%s): o produto nem sobe -- VERMELHO"
                   % str(exc)[:90])
                ficou_vermelho = True
            par(ficou_vermelho, "mutacao %s em %s" % (rotulo, rel(alvo)),
                "a mutacao foi aplicada e NENHUMA assercao ficou vermelha -- o bloco "
                "%s e carimbo" % rotulo)
        finally:
            shutil.copyfile(backup, alvo)
            os.remove(backup)


# ===========================================================================
# O contexto -- carregado uma vez, usado por todos os blocos
# ===========================================================================
def montar_contexto():
    ctx = {}
    ctx["evidence_pack"] = modulo("app.comercial.evidence_pack", "BLOCO D.1")
    ctx["narrativa"] = None
    if existe("app/comercial/narrativa.py"):
        ctx["narrativa"] = modulo("app.comercial.narrativa", "BLOCO D.1")
    else:
        certo(False, "`backend/app/comercial/narrativa.py` existe",
                "o modulo PURO dos playbooks (titulo · por_que_importa · o_que_fazer · "
                "pergunta) ainda nao foi escrito")
    ctx["briefing_service"] = modulo("app.services.intelligence.briefing_service", "BLOCO D.3")
    ctx["service"] = modulo("app.services.artifacts.service", "BLOCO B.2")
    ctx["relatorios_comerciais"] = modulo("app.agents.tools.relatorios_comerciais", "BLOCO B.1")
    ctx["listar_entregas"] = modulo("app.agents.tools.listar_entregas", "BLOCO B")
    ctx["executive"] = modulo("app.agents.tools.executive_intelligence", "BLOCO D.2")

    def acionaveis(bs):
        """Quatro itens acionaveis, o primeiro com manchete propria e `why_now`."""
        Item = bs.ItemDeBriefing
        campos = set(getattr(Item, "__dataclass_fields__", {}) or {})
        extra = {}
        if "why_now" in campos:
            extra["why_now"] = "a fila cresceu 40% em 24 horas"
        if "next_step" in campos:
            extra["next_step"] = "começar pelos parados há mais de 48h"
        return [
            Item(item_type="finding", section="precisa_de_voce",
                 headline="Fila acumulada",
                 summary="61 atendimentos parados há mais de 24h. O canal de entrada "
                         "continua aberto.",
                 priority_score=90.0, finding_id="f1", **extra),
            Item(item_type="finding", section="precisa_de_voce",
                 headline="Renovações vencidas", summary="37 apólices já venceram.",
                 priority_score=70.0, finding_id="f2"),
            Item(item_type="finding", section="precisa_de_voce",
                 headline="Concentração de carteira", summary="Uma seguradora domina.",
                 priority_score=50.0, finding_id="f3"),
            Item(item_type="recommendation", section="oportunidades",
                 headline="Automatizar a cobrança", summary="A rotina já existe.",
                 priority_score=30.0, recommendation_id="r1"),
        ]

    ctx["acionaveis"] = acionaveis

    def compor_pulso(sem_achado=False):
        """Chama o `_compor` REAL, por emprestimo dos metodos da tool (D4)."""
        ex = ctx["executive"]
        ep = ctx["evidence_pack"]
        if ex is None or ep is None:
            return [], "executive_intelligence ou evidence_pack nao pode ser lido"
        Tool = getattr(ex, "ExecutiveIntelligenceTool", None)
        if Tool is None:
            return [], "ExecutiveIntelligenceTool nao existe"
        try:
            emprestados = {n: Tool.__dict__[n] for n in
                           ("_compor", "_veredito", "frase_da_cobertura", "_fontes_e_confianca")
                           if n in Tool.__dict__}
            Emprestimo = type("PulsoEmprestado", (), dict(emprestados))
            metricas, anteriores = golden(ep)
            achados = [] if sem_achado else ep.achar_findings(metricas, anteriores)
            pacote = pacote_golden(ep, achados, metricas)
            return Emprestimo()._compor(
                pacote, PeriodoFalso(), None, metricas, [],
                "2026-09-04T02:54:00Z", {PRODUTOR_REF: ROTULO_SENTINELA}), ""
        except Exception as exc:  # noqa: BLE001
            return [], "EXPLODIU: %s: %s" % (type(exc).__name__, str(exc)[:300])

    ctx["compor_pulso"] = compor_pulso

    def banco_novo():
        return BancoFalso({"artifacts": [], "artifact_versions": [], "artifact_renders": [],
                           "artifact_events": [], "brand_profiles": [], "report_templates": []})

    def publicar(identidades):
        """Roda `_publicar` uma vez por identidade, no MESMO banco."""
        rc = ctx["relatorios_comerciais"]
        banco = banco_novo()
        try:
            for n, identidade in enumerate(identidades):
                argumentos = dict(
                    titulo="Seguradora Sentinela concentra 46,8%% da comissão de %s"
                           % identidade.get("label", ""),
                    subtitulo="Pulso 360 · %s · dados lidos em 04/09 02:54"
                              % identidade.get("label", ""),
                    resumo="Acima do limiar declarado.",
                    template="executive.pulse360",
                    payload={"versao": n + 1}, blocos=[{"block": "cover", "props": {}}],
                )
                cod = getattr(rc._publicar, "__code__", None)
                nomes = set(cod.co_varnames[: cod.co_argcount + cod.co_kwonlyargcount]) if cod else set()
                if "identidade" in nomes:
                    argumentos["identidade"] = dict(identidade)
                if "data_sources" in nomes:
                    argumentos["data_sources"] = [
                        {"label": "InfoCap · carteira", "detail": "leitura direta",
                         "as_of": "2026-09-04T02:54:00Z"}]
                if "data_as_of" in nomes:
                    argumentos["data_as_of"] = datetime(2026, 9, 4, 2, 54, tzinfo=timezone.utc)
                rc._publicar(banco, EMPRESA_A, **argumentos)
            return banco, ""
        except Exception as exc:  # noqa: BLE001
            return banco, "EXPLODIU: %s: %s" % (type(exc).__name__, str(exc)[:300])

    ctx["publicar_duas_vezes"] = lambda a, b: publicar([a, b])
    ctx["publicar_uma_vez"] = lambda a: publicar([a])
    return ctx


# ===========================================================================
def _rodar(ctx, so=None):
    if so in (None, "0"):
        bloco_0_gate_zero(ctx)
    if so in (None, "B.a", "B.b", "B.c", "B.f"):
        bloco_B_identidade(ctx)
    if so in (None, "D1", "D2", "D3", "D5"):
        bloco_D_narrativa(ctx)


def main():
    global OK, FAIL
    mutar = "--mutar" in sys.argv or os.environ.get("AUTOBROKERS_MUTAR") == "1"

    _p("=" * 78)
    _p("  O RELATORIO ABRE PELO ACHADO -- o guarda do MOTOR  (SPEC-095)")
    _p("=" * 78)

    _abrir_o_ambiente()
    _fechar_a_rede()
    try:
        ctx = montar_contexto()

        def remedir(rotulo):
            for nome in ("app.comercial.narrativa", "app.services.artifacts.service",
                         "app.agents.tools.relatorios_comerciais",
                         "app.services.intelligence.briefing_service",
                         "app.agents.tools.executive_intelligence",
                         "app.agents.tools.listar_entregas"):
                if nome in sys.modules:
                    try:
                        importlib.reload(sys.modules[nome])
                    except Exception as exc:  # noqa: BLE001
                        # 📊 04/09/2026 (builder do motor): engolir aqui deixava o
                        # módulo ANTIGO vivo quando a mutação quebrava a sintaxe —
                        # e o arnês concluía "nada ficou vermelho". Um produto que
                        # nem carrega é o vermelho mais alto que existe: sobe.
                        raise RuntimeError("MUTACAO_QUEBROU_O_MODULO %s: %s"
                                           % (nome, type(exc).__name__)) from exc
            novo = montar_contexto()
            # Todos os blocos, sempre: uma mutação de D3 fica vermelha no GATE ZERO
            # (bloco [0]), e `so="D3"` só re-rodava o [D]. O custo é segundos.
            _rodar(novo)

        ctx["remedir"] = remedir
        _rodar(ctx)
        if mutar:
            rodar_mutacoes(ctx)
        else:
            _p("\n[M] MUTACOES POR COPIA -- NAO rodaram (sem `--mutar`).")
            _p("      ⛔ Elas escrevem em `backend/app/`, e dois builders escrevem la")
            _p("      em paralelo. Com a arvore parada: `--mutar`. A lista declarada")
            _p("      esta em `MUTACOES`, no topo deste arquivo (%d entradas)." % len(MUTACOES))
        bloco_C_controle(ctx)
    finally:
        _abrir_a_rede()
        _restaurar_sys_modules()

    de_verdade = FAIL - len(ESPERADOS)
    _p("\n" + "=" * 78)
    _p("  %d ok · %d falhas (%d VERMELHO ESPERADO + %d de verdade) · %d pulados"
       % (OK, FAIL, len(ESPERADOS), de_verdade, len(PULADOS)))
    if ESPERADOS:
        _p("\n  🔴 VERMELHO ESPERADO -- a SPEC-095 PREVE estes ate o bloco citado.")
        _p("     O GATE ZERO desta SPEC e exatamente esta lista em `b054b5c`.")
        for x in ESPERADOS:
            _p("     · %s" % x)
    if de_verdade > 0:
        _p("\n  ⛔ HA %d VERMELHO DE VERDADE acima -- procure as linhas `[FALHOU]`." % de_verdade)
    if JA_PODEM_VIRAR:
        _p("\n  ✅ ESTES JA FICARAM VERDES. O integrador troca `devendo(...)` por")
        _p("     `certo(...)` e apaga o argumento do bloco -- senao o guarda passa a")
        _p("     guardar verdade vencida (CLAUDE.md §9.3):")
        for x in JA_PODEM_VIRAR:
            _p("     · %s" % x)
    if PULADOS:
        _p("\n  -- pulados (%d): %s" % (len(PULADOS), " · ".join(PULADOS)))
    _p("=" * 78)
    if ESPERADOS and de_verdade == 0:
        _p("  (exit 0 com %d VERMELHO ESPERADO e 0 de verdade: o gate FINAL da SPEC-095\n"
           "   so fecha com a lista acima VAZIA -- protocolo v11.2, opcao B)" % len(ESPERADOS))
    return 1 if de_verdade else 0


def test_o_relatorio_abre_pelo_achado():
    """🔴 A prova nasceu ANTES do codigo (protocolo §4, opcao B).

    Enquanto os BLOCOS B e D nao chegam, a saida traz a lista de VERMELHO
    ESPERADO com o bloco devedor ao lado de cada linha -- e e essa lista que o
    executor precisa ler. O exit code so vira 1 com vermelho DE VERDADE, para
    que a suite continue distinguindo "a SPEC ainda deve" de "alguem quebrou o
    produto". O gate final da SPEC-095 exige a lista VAZIA.
    """
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
