# -*- coding: utf-8 -*-
"""`pytest tests/` volta a funcionar — P-183, segunda metade.

📊 **O defeito, medido em 24/08/2026 por um auditor externo:**

```
$ python -m pytest tests/ --collect-only -q
INTERNALERROR> File ".../test_a_arvore_do_pneu_decide_o_reboque.py", line 395
INTERNALERROR>   sys.exit(1 if FAIL else 0)
INTERNALERROR> SystemExit: 0
no tests collected in 0.47s
```

🔴 **`pytest tests/` não coletava zero: ele ABORTAVA A SESSÃO INTEIRA.** A causa
é que **60 arquivos chamam `sys.exit()` em nível de módulo** — o `import` que o
coletor faz executa o guarda, o `SystemExit` sobe, e o pytest morre no primeiro.

⚠️ **E o pior era o efeito colateral:** com a sessão morta, os arquivos que
**são** pytest de verdade também nunca rodavam. 📊 Três deles guardam **35
asserções**, e **cinco estavam VERMELHAS** — inclusive *"a régua devolve 102
numa escala de 100"* e *"o replay não acha NENHUMA órfã funcional"*.

## O universo real de `tests/`, medido

```
279  arquivos test_*.py
  6  com `def test_`      →  o pytest roda, e agora consegue
273  sem `def test_`      →  rodam como PROCESSO, pelo meta-guarda
       151 com `main()`   →  o que a primeira versão pegava
       122 sem `main()`   →  asserções em nível de módulo. 🔴 Ficavam de fora.
```

## O que este arquivo faz, e é uma linha de ideia

**Tira os 273 da coleta padrão do pytest** — `collect_ignore`. Eles continuam
rodando, como processo, por `test_todos_os_guardas_script_rodam.py`. O pytest
para de importá-los, para de morrer, e **passa a rodar os 6 que são dele**.

⚠️ **Por que `collect_ignore` e não `pytest_collect_file`:** 🔴 aquele hook é
**aditivo** — o coletor padrão continua tentando importar o mesmo arquivo, e o
`SystemExit` derruba tudo do mesmo jeito. Tentado, medido, descartado.

🔴 **E a regra de exclusão é a MESMA função de descoberta do meta-guarda**,
importada daqui. Duas listas que precisam concordar e são escritas separado
divergem — é o defeito nº 1 deste projeto, e não vai ser reintroduzido por um
arquivo que existe para consertar exatamente isso.
"""
from __future__ import annotations

from pathlib import Path

_PASTA = Path(__file__).parent
_META = _PASTA / "test_todos_os_guardas_script_rodam.py"


def _sem_funcao_de_teste(caminho: Path) -> bool:
    """Cópia mínima da regra do meta-guarda — sem importá-lo.

    ⚠️ Importar o meta-guarda daqui criaria um ciclo na coleta. A regra é curta
    o bastante para caber duas vezes, e 🔴 **o guarda contra a divergência é o
    `test_a_exclusao_bate_com_a_descoberta` do próprio meta-guarda**, que
    compara as duas listas e falha se elas discordarem.
    """
    if caminho.resolve() == _META.resolve():
        return False
    try:
        fonte = caminho.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    if fonte.startswith("def test_"):
        return False
    return not any(m in fonte for m in
                   ("\ndef test_", "\nasync def test_", "\nclass Test"))


collect_ignore = sorted(
    p.name for p in _PASTA.glob("test_*.py") if _sem_funcao_de_teste(p)
)


# ---------------------------------------------------------------------------
# O DIARIO DA BATERIA — 🔴 o passo 2º do `PROTOCOLO-AUTOBROKERS-AAA.md` §10
# ---------------------------------------------------------------------------
# O protocolo manda consertar a bateria em três passos, nesta ordem:
#
#     1º  a trava      (o processo solto que muta a árvore compartilhada)
#     2º  🔴 MEDIR QUANTAS VEZES ela roda de fato numa SPEC
#     3º  só então os gates por nível
#
# ⚠️ **E o 2º nunca foi feito.** 📊 O custo POR RODADA está medido com três
# pontos (19m01 · 16m26 · 14m46 → 16m44 ±13%). O **número de rodadas** não:
# `9–14` é 💭 estimativa, e "13 commits × 16m44 = 3h37" é aritmética sobre um
# chute — 🔴 **commit não é rodada.** Um commit pode não rodar a bateria, e uma
# rodada pode não virar commit.
#
# É a `CLAUDE.md` §12.1 exatamente onde dói: um número 💭 ilustrativo citado
# como 📊 medido — e desta vez por quem escreveu a regra.
#
# Este arquivo faz UMA coisa: **toda rodada de pytest deixa uma linha.** Na
# próxima SPEC o 2º passo deixa de ser opinião, e o 3º passa a ser decidível.
#
# ⚠️ **Ele NUNCA pode quebrar a suíte.** Um diário que derruba a bateria que ele
# mede é pior que diário nenhum — por isso todo o corpo vive num `except`
# largo, e a falha dele é silenciosa de propósito.

_DIARIO = Path(__file__).resolve().parent.parent / ".diario-da-bateria.jsonl"
_COMECO: dict = {}


def pytest_sessionstart(session):  # noqa: D401
    """Guarda o instante e o alvo. Silencioso em qualquer erro."""
    try:
        import time

        _COMECO["t"] = time.time()
        # 🔴 O ALVO distingue bateria INTEIRA de rodada de um arquivo só — é
        # exatamente essa diferença que o 3º passo precisa para decidir.
        alvo = [a for a in getattr(session.config, "args", []) or []]
        _COMECO["alvo"] = " ".join(alvo) if alvo else "(tudo)"
    except Exception:
        pass


def pytest_sessionfinish(session, exitstatus):  # noqa: D401
    """Uma linha por rodada: quando, quanto, sobre o quê, e em que commit."""
    try:
        import json
        import os
        import subprocess
        import time
        from datetime import datetime, timezone

        if "t" not in _COMECO:
            return

        # 🔴 UMA COLETA NAO E UMA RODADA. Medido em 25/08: um
        # `pytest tests/ --collect-only` entrou no diario como rodada de 4,4s
        # com 595 "coletados" — e uma linha dessas na media destroi exatamente
        # o numero que este arquivo existe para produzir. `CLAUDE.md` §12.1: o
        # defeito nao e o numero errado, e o numero errado com marca de medido.
        if getattr(session.config.option, "collectonly", False):
            return

        segundos = round(time.time() - _COMECO["t"], 1)

        try:
            commit = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True, text=True, timeout=5,
                cwd=str(Path(__file__).resolve().parent.parent),
            ).stdout.strip() or "?"
        except Exception:
            commit = "?"

        linha = {
            "quando": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "segundos": segundos,
            "alvo": _COMECO.get("alvo", "?"),
            "commit": commit,
            "saida": int(exitstatus),
            "coletados": getattr(session, "testscollected", None),
            "falhas": getattr(session, "testsfailed", None),
            # ⚠️ CI e máquina do executor têm relógios diferentes; sem isto as
            # duas populações somam e a média não descreve nenhuma das duas.
            "onde": "ci" if os.environ.get("CI") else "local",
        }
        with open(_DIARIO, "a", encoding="utf-8") as f:
            f.write(json.dumps(linha, ensure_ascii=False) + "\n")
    except Exception:
        # 🔴 De propósito. Ver o cabeçalho.
        pass


# ---------------------------------------------------------------------------
# 🔴 SPEC-123 F5a — A TRAVA DO BANCO REAL: durante os testes, ninguém ESCREVE nele
# ---------------------------------------------------------------------------
# O porquê, o como e a lista do que é escrita: `tests/trava_do_banco_real.py` (um lugar só).
# Aqui: (1) instala no processo do pytest; (2) põe `tests/_sitecustomize` no PYTHONPATH e liga
# `AUTOBROKERS_TRAVA_DO_BANCO=1`, para que TODO processo Python filho (os guardas-script que o
# meta-guarda roda, e `test_o_caso_se_explica_sozinho` é um deles) suba com a trava; (3) o
# marcador `@pytest.mark.banco_real` libera o teste — e o filho dele (`AUTOBROKERS_TRAVA_DO_BANCO=0`).
import os as _os
import sys as _sys

import pytest as _pytest

_sys.path.insert(0, str(_PASTA))
import trava_do_banco_real as _trava  # noqa: E402

_sys.path.remove(str(_PASTA))

EscritaNoBancoRealBloqueada = _trava.EscritaNoBancoRealBloqueada
_sql_escreve = _trava.sql_escreve
_TROCAS_DO_BANCO: list = []
_ENV_ANTES: dict = {}


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "banco_real: o teste PODE escrever no banco real (SPEC-123 F5a — explícito e revisável)")
    _TROCAS_DO_BANCO.extend(_trava.instalar())
    for chave in ("PYTHONPATH", _trava.ENV):
        _ENV_ANTES[chave] = _os.environ.get(chave)
    pasta = str(_PASTA / "_sitecustomize")
    _os.environ["PYTHONPATH"] = pasta + ((_os.pathsep + _ENV_ANTES["PYTHONPATH"])
                                          if _ENV_ANTES["PYTHONPATH"] else "")
    _os.environ[_trava.ENV] = "1"


def pytest_unconfigure(config):
    _trava.desinstalar(_TROCAS_DO_BANCO)
    _TROCAS_DO_BANCO.clear()
    for chave, valor in _ENV_ANTES.items():
        if valor is None:
            _os.environ.pop(chave, None)
        else:
            _os.environ[chave] = valor


@_pytest.fixture(autouse=True)
def _trava_do_banco_real(request):
    """Só o teste MARCADO `banco_real` escreve. O padrão é a trava fechada."""
    marcado = request.node.get_closest_marker("banco_real") is not None
    _trava.TRAVA.liberado = marcado
    antes = _os.environ.get(_trava.ENV)
    if marcado:
        _os.environ[_trava.ENV] = "0"
    try:
        yield
    finally:
        _trava.TRAVA.liberado = False
        if antes is None:
            _os.environ.pop(_trava.ENV, None)
        else:
            _os.environ[_trava.ENV] = antes


# ---------------------------------------------------------------------------
# 🔴 SPEC-123 F5a · P-121-28 — o que um ARQUIVO de teste troca, ele devolve
# ---------------------------------------------------------------------------
# 📊 P-121-28: `test_a_janela_esta_ligada_nos_portoes` troca `attendance_agent_active` e não
# devolve; `test_spec116_f3a_quem_escreve_pede_papel` troca `sys.modules["app.core.database"]`
# JÁ NA COLETA; `test_spec123_atendimento_segunda_chance` instala pacotes `app.*` de mentira na
# coleta (📊 30/09: coletado antes dos outros, 7 arquivos da SPEC-123 caíram com
# "module 'app' has no attribute '__file__'"). A falha muda com a ORDEM e esconde regressão real.
#
# O que se fotografa: `sys.modules` (nome → objeto) e o `__dict__` de cada módulo `app`/`app.*`.
#   · na COLETA de cada arquivo: foto antes do import; o que o import TROCOU (módulo substituído,
#     módulo de mentira novo, atributo de `app.*`) vira o DELTA do arquivo, e a foto volta — o
#     próximo arquivo coleta num mundo limpo;
#   · na EXECUÇÃO do arquivo (fixture de módulo, autouse): foto, o DELTA dele de volta (ele roda
#     no mundo que montou), e no fim a foto volta — inclusive o que os testes trocaram sem devolver.
# ⚠️ Na COLETA, módulo REAL novo (importado do disco) FICA: tirá-lo faria cada arquivo reimportar o
# produto (📊 `import openai` leva minutos aqui) — só sai o de MENTIRA (`__spec__` nulo). Na EXECUÇÃO,
# sai também o `app.*` real que os testes importaram (pode ter nascido amarrado a um dublê); o de
# terceiros (openai, langchain…) fica.
_NADA = object()
_DELTAS: dict = {}
_FOTOS_DA_COLETA: dict = {}


def _do_app(nome: str) -> bool:
    return nome == "app" or nome.startswith("app.")


def _de_mentira(mod) -> bool:
    return (mod is not None and getattr(mod, "__spec__", None) is None
            and _do_app(str(getattr(mod, "__name__", "") or "")))


def _foto() -> dict:
    mods = dict(_sys.modules)
    attrs = {}
    for nome, mod in mods.items():
        if _do_app(nome) and mod is not None:
            try:
                attrs[nome] = (mod, dict(vars(mod)))
            except TypeError:
                pass
    return {"mods": mods, "attrs": attrs}


def _diferenca(antes: dict) -> dict:
    """O que mudou desde `antes`: módulos trocados/sumidos, de mentira novos, atributos de `app.*`."""
    agora = _sys.modules
    trocados = {n: m for n, m in agora.items() if n in antes["mods"] and antes["mods"][n] is not m}
    sumidos = [n for n in antes["mods"] if n not in agora]
    novos_de_mentira = {n: m for n, m in agora.items() if n not in antes["mods"] and _de_mentira(m)}
    atributos = {}
    for nome, (mod, velho) in antes["attrs"].items():
        if agora.get(nome) is not mod:
            continue
        novo = vars(mod)
        mud = {k: v for k, v in novo.items() if velho.get(k, _NADA) is not v}
        fora = [k for k in velho if k not in novo]
        if mud or fora:
            atributos[nome] = (mod, mud, fora)
    return {"trocados": trocados, "sumidos": sumidos, "novos_de_mentira": novos_de_mentira,
            "atributos": atributos}


def _devolver(antes: dict, *, tirar_novos_do_app: bool = False) -> None:
    """Volta ao mundo da foto: trocado volta, sumido volta, de mentira novo sai, e os atributos de
    `app.*` voltam (o acrescentado sai — salvo submódulo REAL registrado em `sys.modules`).
    `tirar_novos_do_app` (fim da EXECUÇÃO de um arquivo): sai também o módulo `app.*` REAL que os
    testes importaram — ele pode ter nascido amarrado a um dublê (📊 `test_a_atendente_fala_e_o_robo_cala`
    importa `app.api.webhook` com o banco falso já instalado, e o webhook guarda o cliente no topo)."""
    agora = _sys.modules
    for nome in [n for n, m in list(agora.items()) if n not in antes["mods"]
                 and (_de_mentira(m) or (tirar_novos_do_app and _do_app(n)))]:
        agora.pop(nome, None)
    for nome, mod in antes["mods"].items():
        if agora.get(nome, _NADA) is not mod:
            agora[nome] = mod
    for nome, (mod, velho) in antes["attrs"].items():
        if agora.get(nome) is not mod:
            continue
        d = vars(mod)
        for k in [k for k in list(d) if k not in velho]:
            v = d[k]
            if getattr(v, "__spec__", None) is not None and agora.get(f"{nome}.{k}") is v:
                continue            # submódulo real importado depois: legítimo
            d.pop(k, None)
        for k, v in velho.items():
            if d.get(k, _NADA) is not v:
                d[k] = v


def _aplicar(delta: dict) -> None:
    agora = _sys.modules
    for nome in delta.get("sumidos") or []:
        agora.pop(nome, None)
    agora.update(delta.get("trocados") or {})
    for nome, mod in (delta.get("novos_de_mentira") or {}).items():
        agora.setdefault(nome, mod)     # como o `if nome not in sys.modules` de quem o instalou
    for _nome, (mod, mud, fora) in (delta.get("atributos") or {}).items():
        d = vars(mod)
        d.update(mud)
        for k in fora:
            d.pop(k, None)


#: Módulos `app.*` importados DURANTE a coleta de um arquivo: o `__dict__` logo depois de o módulo
#: terminar de executar (o estado PRÍSTINO). 📊 `test_spec116_f3a_quem_escreve_pede_papel` é o
#: primeiro a importar `app.core.database` e, na linha seguinte, troca `get_supabase_client` —
#: sem esta foto não há "antes" para devolver.
_PRISTINOS: dict = {}
_COLETANDO = {"ativo": False}


class _FotografoDoImport:
    """Meta path finder: durante a COLETA, embrulha o `exec_module` de cada `app.*` para fotografar
    o módulo assim que ele termina de executar. Fora da coleta, não faz nada."""

    def find_spec(self, fullname, path=None, target=None):
        if not _COLETANDO["ativo"] or not _do_app(fullname):
            return None
        import importlib.machinery as _maq

        spec = _maq.PathFinder.find_spec(fullname, path, target)
        loader = getattr(spec, "loader", None)
        original = getattr(loader, "exec_module", None)
        if spec is None or original is None:
            return spec

        def exec_module(module, _original=original, _nome=fullname):
            _original(module)
            _PRISTINOS.setdefault(_nome, (module, dict(vars(module))))

        try:
            loader.exec_module = exec_module
        except Exception:  # noqa: BLE001
            pass
        return spec


_sys.meta_path.insert(0, _FotografoDoImport())


def pytest_collectstart(collector):
    if isinstance(collector, _pytest.Module):
        try:
            _FOTOS_DA_COLETA[collector.nodeid] = _foto()
            _PRISTINOS.clear()
            _COLETANDO["ativo"] = True
        except Exception:  # noqa: BLE001 — a fotografia nunca derruba a coleta
            pass


def pytest_collectreport(report):
    antes = _FOTOS_DA_COLETA.pop(report.nodeid, None)
    if antes is None:
        return
    _COLETANDO["ativo"] = False
    try:
        for nome, (mod, d) in list(_PRISTINOS.items()):
            if nome not in antes["attrs"] and _sys.modules.get(nome) is mod:
                antes["attrs"][nome] = (mod, d)     # o "antes" de quem nasceu nesta coleta
        _PRISTINOS.clear()
        delta = _diferenca(antes)
        if any(delta.values()):
            _DELTAS[report.nodeid] = delta
        _devolver(antes)
    except Exception:  # noqa: BLE001
        pass


@_pytest.fixture(autouse=True, scope="module")
def _o_arquivo_devolve_o_que_trocou(request):
    antes = _foto()
    no = request.node if isinstance(request.node, _pytest.Module) else request.node.getparent(_pytest.Module)
    delta = _DELTAS.get(getattr(no, "nodeid", ""))
    if delta:
        _aplicar(delta)
    try:
        yield
    finally:
        _devolver(antes, tirar_novos_do_app=True)
