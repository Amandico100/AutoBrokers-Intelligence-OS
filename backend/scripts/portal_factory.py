#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Portal Capability Factory — a ferramenta de engenharia da SPEC-075 §17.

O que ela é, e o que ela NÃO é
==============================
Ela **audita** o registro de journeys e **gera esqueleto**. Ela não executa
journey, não faz login, não publica Tool, não libera capability, não escreve no
banco e não comita. Um runtime paralelo é exatamente o que a CLAUDE.md §5
proíbe — e a tentação de "já que estou aqui, deixa eu só rodar" é como ele
nasce.

E ela **não edita o registro sozinha**
======================================
🔴 `scaffold-portal` e `scaffold-journey` IMPRIMEM o bloco que precisa entrar em
`portal_worker/journeys/__init__.py`. Quem cola é uma pessoa.

Gerador que reescreve arquivo de código cria divergência silenciosa: no dia em
que ele reordenar um dicionário, tocar um comentário ou perder uma entrada que
alguém escreveu à mão, o diff sai grande demais para alguém ler de verdade — e o
registro é justamente o arquivo onde uma linha errada faz o worker chamar a
função errada em produção. Imprimir custa um `Ctrl+V`. Reescrever custa confiança.

Os cinco comandos
=================
    audit       o registro bate com o código, os fixtures e os testes?
    matrix      o que a casa sabe fazer, por operação de negócio
    validate    o registro é COERENTE consigo mesmo?
    scaffold-portal    esqueleto de um portal novo
    scaffold-journey   esqueleto de uma capacidade nova em portal conhecido

`audit` e `validate` saem com código **diferente de zero** quando encontram
problema real. Um comando de auditoria que sempre sai 0 não é gate: é enfeite —
ele passa a fazer parte do CI como uma linha verde que nunca teve como ficar
vermelha (CLAUDE.md §9.3: um guarda que não tem como falhar não guarda nada).

A diferença entre ERRO e AVISO, escrita antes de ser usada
==========================================================
    ERRO   quebra ou pode quebrar EXECUÇÃO: módulo que não importa, função que
           não existe, journey material sem prova offline, host livre.
           → sai 1.
    AVISO  dívida que alguém precisa ver, e que não derruba nada hoje.
           → sai 0.

Fora do escopo desta versão
===========================
A §17.1 lista também `replay --portal --journey --case`. Ele depende da árvore
de fixtures da §19.1 (`backend/tests/fixtures/portal_worker/<portal>/<journey>/
<caso>/`), que **ainda não existe neste repositório** — os fixtures de hoje são
módulos Python planos. Um `replay` que não tem o que reproduzir seria um comando
que sempre responde "nada a fazer", e isso é pior que a ausência dele: vira uma
prova falsa de cobertura. Fica registrado como pendência, não como stub.

As checagens que dependem de BANCO (portal em `portals` sem journey, tool sem
release publicada, release com schema `{}`, portal account órfão) também ficam
fora: este script não abre conexão. O que dá para conferir só com o código, ele
confere; o que não dá, ele **diz que não conferiu** em vez de dar verde.

USO
===
    python backend/scripts/portal_factory.py audit
    python backend/scripts/portal_factory.py matrix [--markdown|--json]
    python backend/scripts/portal_factory.py validate [--portal K] [--journey J]
    python backend/scripts/portal_factory.py scaffold-portal  --portal-key K \\
        --operation OP [--journey-key J] [--effect-class C] [--write]
    python backend/scripts/portal_factory.py scaffold-journey --portal-key K \\
        --journey-key J --operation OP [--effect-class C] [--write]
"""
from __future__ import annotations

import argparse
import ast
import importlib
import inspect
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

# --------------------------------------------------------------------------
# Onde as coisas moram. Tudo derivado de `__file__`, para o script rodar de
# qualquer diretório — inclusive de dentro do contêiner, onde o cwd é outro.
# --------------------------------------------------------------------------
ERRO = "ERRO"
AVISO = "AVISO"

DIR_FIXTURES_CANONICO = "portal_worker"       # SPEC-075 §19.1
DOC_MATRIZ = "docs/generated/portal-capability-matrix.md"   # SPEC-075 §22

# Tokens que não identificam portal nenhum: aparecem em quase todo nome.
_TOKENS_GENERICOS: Set[str] = {
    "corretor", "corretora", "portal", "portais", "seguros", "seguradora",
    "test", "tests", "fixture", "fixtures", "py", "json", "html", "init",
    "pycache", "com", "br", "web", "api", "app",
}

_NOMES_DE_ALLOWLIST = ("HOSTS_PERMITIDOS", "HOSTS_ALLOWLIST", "ALLOWED_HOSTS",
                       "HOSTS_APROVADOS")
_FUNCOES_DE_ALLOWLIST = ("_host_permitido", "host_permitido",
                         "exigir_host_permitido", "_url_permitida",
                         "url_permitida", "_exigir_host")


def _raiz() -> Path:
    """A raiz do repositório: `backend/scripts/portal_factory.py` → dois acima."""
    return Path(__file__).resolve().parents[2]


def _backend() -> Path:
    return _raiz() / "backend"


def _preparar_import() -> None:
    """`backend/` no `sys.path`, para `portal_worker` e `tests.fixtures` resolverem.

    Fica em função, e não no import: a CLAUDE.md pede módulo sem efeito colateral
    de carga, e um `sys.path.insert` no topo de um script é efeito colateral em
    qualquer processo que só quisesse importar uma função daqui.
    """
    alvo = str(_backend())
    if alvo not in sys.path:
        sys.path.insert(0, alvo)


def _saida_utf8() -> None:
    """O console do Windows abre em cp1252 e este script imprime `🔴` e `→`.

    📊 Medido em 02/08/2026 (`backend/tests/run_all.py`): sem `PYTHONIOENCODING`,
    oito testes verdes viravam vermelhos no `print`, não na asserção. O mesmo
    `UnicodeEncodeError` derrubaria esta CLI no meio de um relatório — e um gate
    que morre na impressão mente na direção errada.
    """
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass


# ==========================================================================
# Achados — a unidade de saída dos comandos que reprovam
# ==========================================================================
@dataclass
class Achado:
    nivel: str      # ERRO | AVISO
    alvo: str       # a chave `portal.journey`, ou o escopo global
    texto: str

    @property
    def reprova(self) -> bool:
        return self.nivel == ERRO


def _imprimir_achados(achados: Sequence[Achado], titulo: str) -> int:
    """Imprime agrupado por nível e devolve quantos ERROs havia."""
    erros = [a for a in achados if a.reprova]
    avisos = [a for a in achados if not a.reprova]
    print()
    print("=" * 78)
    print(f"  {titulo}")
    print("=" * 78)
    if erros:
        print(f"\n  🔴 {len(erros)} ERRO(S) — isto reprova\n")
        for a in erros:
            print(f"    X  {a.alvo}")
            for linha in _quebrar(a.texto, 68):
                print(f"          {linha}")
    if avisos:
        print(f"\n  {len(avisos)} AVISO(S) — dívida visível, não reprova\n")
        for a in avisos:
            print(f"    !  {a.alvo}")
            for linha in _quebrar(a.texto, 68):
                print(f"          {linha}")
    if not achados:
        print("\n  nada a apontar.\n")
    return len(erros)


def _quebrar(texto: str, largura: int) -> List[str]:
    palavras = str(texto).split()
    linhas: List[str] = []
    atual = ""
    for p in palavras:
        if len(atual) + len(p) + 1 > largura and atual:
            linhas.append(atual)
            atual = p
        else:
            atual = f"{atual} {p}".strip()
    if atual:
        linhas.append(atual)
    return linhas or [""]


# ==========================================================================
# Leitura do código-fonte — AST, nunca regex sobre o arquivo cru
#
# 🔴 Regex sobre o fonte confunde COMENTÁRIO com CONSTANTE. `vidros_lanternas`
# cita `https://vistoria.mobi/...` num comentário que explica um host que a
# journey NÃO usa; uma varredura textual contaria isso como host declarado e a
# auditoria daria verde por causa de um comentário. AST só enxerga o que o
# interpretador enxerga.
# ==========================================================================
def _arvore(caminho: Path) -> Optional[ast.Module]:
    try:
        return ast.parse(caminho.read_text(encoding="utf-8"), filename=str(caminho))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return None


def _constantes_str(arv: ast.Module) -> Dict[str, List[str]]:
    """Nome de constante de módulo → strings que ela contém.

    Cobre `X = "…"`, `X: T = "…"`, `X = ("a", "b")` e f-strings simples cujas
    partes variáveis já são constantes conhecidas (`BASE_API = f"https://{HOST}/x"`).
    """
    tabela: Dict[str, List[str]] = {}

    def literais(no: ast.AST) -> List[str]:
        if isinstance(no, ast.Constant) and isinstance(no.value, str):
            return [no.value]
        if isinstance(no, (ast.Tuple, ast.List, ast.Set)):
            saida: List[str] = []
            for elt in no.elts:
                saida.extend(literais(elt))
            return saida
        if isinstance(no, ast.JoinedStr):
            montado = ""
            for parte in no.values:
                if isinstance(parte, ast.Constant) and isinstance(parte.value, str):
                    montado += parte.value
                elif isinstance(parte, ast.FormattedValue) and isinstance(parte.value, ast.Name):
                    vizinho = tabela.get(parte.value.id) or [""]
                    montado += vizinho[0]
                else:
                    montado += "?"
            return [montado]
        return []

    for no in arv.body:
        alvos: List[str] = []
        valor: Optional[ast.AST] = None
        if isinstance(no, ast.Assign):
            valor = no.value
            alvos = [t.id for t in no.targets if isinstance(t, ast.Name)]
        elif isinstance(no, ast.AnnAssign) and isinstance(no.target, ast.Name):
            valor = no.value
            alvos = [no.target.id]
        if valor is None or not alvos:
            continue
        achadas = literais(valor)
        if achadas:
            for nome in alvos:
                tabela[nome] = achadas
    return tabela


_RE_HOST = re.compile(r"https?://([A-Za-z0-9._\-]+)")


def _hosts_do_modulo(caminho: Path) -> Tuple[List[str], bool, bool]:
    """`(hosts declarados, tem allowlist fechada, tem host sem TLS)`."""
    arv = _arvore(caminho)
    if arv is None:
        return [], False, False
    tabela = _constantes_str(arv)
    hosts: Set[str] = set()
    sem_tls = False
    for valores in tabela.values():
        for v in valores:
            for m in _RE_HOST.finditer(v):
                hosts.add(m.group(1).lower())
            if v.startswith("http://"):
                sem_tls = True
    fechada = any(n in tabela for n in _NOMES_DE_ALLOWLIST)
    if not fechada:
        for no in ast.walk(arv):
            if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)) and \
                    no.name in _FUNCOES_DE_ALLOWLIST:
                fechada = True
                break
    return sorted(hosts), fechada, sem_tls


def _irmaos_importados(caminho: Path) -> Set[str]:
    """Módulos de `portal_worker.journeys` que este arquivo importa, em qualquer nível."""
    arv = _arvore(caminho)
    if arv is None:
        return set()
    saida: Set[str] = set()
    for no in ast.walk(arv):
        if isinstance(no, ast.ImportFrom) and (no.module or "").startswith(
                "portal_worker.journeys"):
            resto = (no.module or "")[len("portal_worker.journeys"):].strip(".")
            if resto:
                saida.add(resto.split(".")[0])
            else:
                for a in no.names:
                    saida.add(a.name)
        elif isinstance(no, ast.Import):
            for a in no.names:
                if a.name.startswith("portal_worker.journeys."):
                    saida.add(a.name.split(".")[3] if len(a.name.split(".")) > 3
                              else a.name.split(".")[-1])
    return {s for s in saida if s and s.isidentifier()}


def _allowlist_na_cadeia(caminho: Path, vistos: Optional[Set[Path]] = None) -> bool:
    """A allowlist fechada pode morar num módulo irmão (o caso do portal de vidros).

    `vidros_lanternas` → `vidros_apifirst` → `vidros_api`, que é quem tem o
    `HOSTS_PERMITIDOS`. Parar no primeiro arquivo diria "sem allowlist" sobre a
    única journey do repositório que tem a allowlist mais rigorosa — um falso
    positivo que ensinaria a ignorar o aviso.
    """
    vistos = vistos if vistos is not None else set()
    if caminho in vistos or not caminho.exists():
        return False
    vistos.add(caminho)
    _, fechada, _ = _hosts_do_modulo(caminho)
    if fechada:
        return True
    for irmao in _irmaos_importados(caminho):
        if _allowlist_na_cadeia(caminho.parent / f"{irmao}.py", vistos):
            return True
    return False


def _entrypoints_do_arquivo(caminho: Path) -> List[str]:
    """`async def f(page, params, evidence)` de nível de módulo — a assinatura de journey."""
    arv = _arvore(caminho)
    if arv is None:
        return []
    saida: List[str] = []
    for no in arv.body:
        if not isinstance(no, ast.AsyncFunctionDef):
            continue
        nomes = [a.arg for a in no.args.args]
        if len(nomes) >= 3 and nomes[0] == "page" and nomes[1] == "params" and \
                nomes[2] == "evidence":
            saida.append(no.name)
    return saida


# ==========================================================================
# Fixtures e testes — casamento por TOKEN de caminho, e o motivo de não ser
# por conteúdo
#
# 📊 Medido em 16/08/2026 neste repositório: procurar a palavra `allianz` DENTRO
# dos fixtures acha `tests/fixtures/vidros/maxpar_apolices.py`, que lista nomes
# de seguradoras num catálogo do portal de vidros. Pelo conteúdo, a Allianz
# "tem fixture"; ela não tem. Casar por caminho erra menos, e erra para o lado
# seguro — deixa de encontrar em vez de inventar.
# ==========================================================================
def _tokens(texto: str) -> Set[str]:
    brutos = re.split(r"[^a-z0-9]+", str(texto or "").lower())
    return {t for t in brutos if len(t) >= 3 and t not in _TOKENS_GENERICOS}


def _casam(a: Set[str], b: Set[str]) -> bool:
    """Dois conjuntos de token se reconhecem por prefixo (mínimo 3 letras).

    O prefixo existe por um caso real: o portal é `tokiomarine_corretor` e o
    fixture é `tokio_inadimplentes.py`. Igualdade estrita diria "sem fixture"
    sobre um fixture que está lá.
    """
    for x in a:
        for y in b:
            if x == y or x.startswith(y) or y.startswith(x):
                return True
    return False


@dataclass
class Provas:
    """O que existe fora do código para sustentar uma journey."""
    fixtures: List[str] = field(default_factory=list)
    fixture_por_journey: bool = False     # árvore canônica da §19.1
    testes: List[str] = field(default_factory=list)
    teste_por_journey: bool = False       # o arquivo cita a journey, não só o portal


def _mapa_de_fixtures() -> List[Tuple[Path, Set[str]]]:
    base = _backend() / "tests" / "fixtures"
    saida: List[Tuple[Path, Set[str]]] = []
    if not base.exists():
        return saida
    for f in sorted(base.rglob("*")):
        if not f.is_file() or "__pycache__" in f.parts or f.suffix == ".pyc":
            continue
        rel = f.relative_to(base)
        saida.append((f, _tokens(str(rel))))
    return saida


def _mapa_de_testes() -> List[Tuple[Path, str]]:
    base = _backend() / "tests"
    saida: List[Tuple[Path, str]] = []
    if not base.exists():
        return saida
    for f in sorted(base.glob("test_*.py")):
        try:
            saida.append((f, f.read_text(encoding="utf-8", errors="replace").lower()))
        except OSError:
            continue
    return saida


def _provas_da_journey(portal_key: str, journey_key: str,
                       fixtures: Sequence[Tuple[Path, Set[str]]],
                       testes: Sequence[Tuple[Path, str]]) -> Provas:
    p = Provas()
    base_fx = _backend() / "tests" / "fixtures"
    canonico = base_fx / DIR_FIXTURES_CANONICO / portal_key / journey_key
    if canonico.is_dir() and any(canonico.rglob("*")):
        p.fixture_por_journey = True
        p.fixtures = [str(x.relative_to(base_fx)) for x in sorted(canonico.rglob("*"))
                      if x.is_file()]
    else:
        alvo = _tokens(portal_key)
        p.fixtures = [str(f.relative_to(base_fx)) for f, toks in fixtures
                      if _casam(alvo, toks)]

    for caminho, corpo in testes:
        if portal_key.lower() not in corpo:
            continue
        p.testes.append(caminho.name)
        if journey_key.lower() in corpo:
            p.teste_por_journey = True
    return p


# ==========================================================================
# audit — SPEC-075 §17.2
# ==========================================================================
def cmd_audit(args: argparse.Namespace) -> int:
    _preparar_import()
    from portal_worker import journeys as R  # noqa: N812

    dir_journeys = _backend() / "portal_worker" / "journeys"
    fixtures = _mapa_de_fixtures()
    testes = _mapa_de_testes()
    achados: List[Achado] = []

    print()
    print("=" * 78)
    print("  AUDITORIA DO REGISTRO DE JOURNEYS — SPEC-075 §17.2")
    print(f"  raiz: {_raiz()}")
    print("=" * 78)
    print()
    print(f"  {'journey':<40} {'operação':<24} {'efeito':<21} "
          f"{'mód':<4} {'fn':<4} {'fix':<5} {'tst':<5} {'host':<5}")
    print("  " + "-" * 112)

    for chave in sorted(R.JOURNEYS):
        d = R.JOURNEYS[chave]
        alvo = chave

        # ---- o módulo importa? -------------------------------------------
        modulo = None
        col_mod = "ok"
        try:
            modulo = importlib.import_module(d.module)
        except Exception as e:  # noqa: BLE001
            col_mod = "X"
            achados.append(Achado(
                ERRO, alvo,
                f"o módulo `{d.module}` não importa ({type(e).__name__}: {e}). "
                "O registro aponta para código que não existe nesta imagem — "
                "`get_journey()` devolve None e o worker grava 'journey "
                "desconhecida' em produção."))

        # ---- a função existe, e é async? ---------------------------------
        col_fn = "ok"
        funcao = getattr(modulo, d.function, None) if modulo is not None else None
        if modulo is None:
            col_fn = "-"
        elif funcao is None:
            col_fn = "X"
            achados.append(Achado(
                ERRO, alvo,
                f"`{d.module}.{d.function}` não existe. O mapa nomeia uma função "
                "que o módulo não define."))
        elif not inspect.iscoroutinefunction(funcao):
            col_fn = "X"
            achados.append(Achado(
                ERRO, alvo,
                f"`{d.function}` não é `async def`. O worker faz `await` na "
                "journey; uma função síncrona estoura no `await` em tempo de "
                "execução, e só lá."))
        else:
            nomes = list(inspect.signature(funcao).parameters)
            if nomes[:3] != ["page", "params", "evidence"]:
                col_fn = "!"
                achados.append(Achado(
                    AVISO, alvo,
                    f"assinatura fora do contrato: {nomes[:3]} em vez de "
                    "['page', 'params', 'evidence']."))

        # ---- provas: fixture e teste -------------------------------------
        pr = _provas_da_journey(d.portal_key, d.journey_key, fixtures, testes)
        if pr.fixture_por_journey:
            col_fix = "ok"
        elif pr.fixtures:
            col_fix = "ok*"
        else:
            col_fix = "X"
            nivel = ERRO if d.e_material else AVISO
            achados.append(Achado(
                nivel, alvo,
                "sem fixture. " + (
                    "🔴 A journey é `material_side_effect`: sem caso gravado não "
                    "há como provar, offline, que ela PARA na fronteira em "
                    "dry-run — e a única forma de testar passa a ser criar coisa "
                    "de verdade na seguradora (SPEC-075 §19.5)."
                    if d.e_material else
                    "Leitura sem fixture ainda pode ser conferida contra o portal, "
                    "mas o teste passa a depender de rede e de credencial.")))

        if pr.teste_por_journey:
            col_tst = "ok"
        elif pr.testes:
            col_tst = "ok*"
            achados.append(Achado(
                AVISO, alvo,
                f"há teste que cita o portal ({', '.join(pr.testes[:3])}) mas "
                f"nenhum cita `{d.journey_key}`. A cobertura pode ser do portal "
                "vizinho e ninguém saberia."))
        else:
            col_tst = "X"
            achados.append(Achado(
                ERRO, alvo,
                "nenhum teste cita este portal. Journey registrada e não provada "
                "é uma linha do mapa que só é conferida em produção."))

        # ---- host allowlistado (§20.2) -----------------------------------
        arquivo = dir_journeys / f"{d.module.rsplit('.', 1)[-1]}.py"
        hosts, _fechada_aqui, sem_tls = _hosts_do_modulo(arquivo)
        fechada = _allowlist_na_cadeia(arquivo)
        col_host = str(len(hosts)) if hosts else "X"
        if not hosts:
            achados.append(Achado(
                ERRO, alvo,
                f"`{arquivo.name}` não declara host nenhum como constante de "
                "módulo. Sem host declarado a journey é um cliente HTTP de URL "
                "livre — descoberta virando autorização, que é o que a §20.1 "
                "proíbe."))
        elif not fechada:
            col_host = f"{len(hosts)}!"
            achados.append(Achado(
                AVISO, alvo,
                f"declara {len(hosts)} host(s) ({', '.join(hosts[:3])}) mas não "
                "tem allowlist FECHADA (nem `HOSTS_PERMITIDOS`, nem função que "
                "recuse host de fora). Constante não é guarda: ela documenta "
                "para onde se pretende ir, não impede ir para outro lugar."))
        if sem_tls:
            achados.append(Achado(
                ERRO, alvo,
                f"`{arquivo.name}` declara host em `http://` sem TLS. Credencial "
                "de corretora não trafega em claro."))

        print(f"  {chave:<40} {d.business_operation:<24} {d.effect_class:<21} "
              f"{col_mod:<4} {col_fn:<4} {col_fix:<5} {col_tst:<5} {col_host:<5}")

    print("  " + "-" * 112)
    print("   ok  provado no nível da journey   ·   ok*  provado só no nível do "
          "PORTAL   ·   X  ausente")
    print("   host  quantidade de hosts declarados; `!` = declarados sem "
          "allowlist fechada")

    achados.extend(_orfaos_de_codigo(dir_journeys, R))
    achados.extend(_divergencia_de_doc(R))

    erros = _imprimir_achados(achados, "RESULTADO DA AUDITORIA")
    print()
    print("  NÃO CONFERIDO por este comando (exige banco, e ele não abre conexão):")
    print("    · portal em `portals` sem journey registrada")
    print("    · tool `portal.*` sem release publicada, ou release com schema `{}`")
    print("    · `effect_class` da journey divergente da declarada na tool")
    print("    · portal account apontando para portal não registrado")
    print("    · fixture com padrão de segredo/PII (§19.3)")
    print("  Silêncio aqui não é aprovação — é ausência de medição.")
    print()
    print(f"  veredito: {erros} erro(s), "
          f"{len([a for a in achados if not a.reprova])} aviso(s)")
    print()
    return 1 if erros else 0


def _orfaos_de_codigo(dir_journeys: Path, R: Any) -> List[Achado]:
    """Função com assinatura de journey escrita e NÃO registrada.

    O worker só alcança o que está no mapa. Uma capacidade escrita fora dele é
    trabalho que existe e que ninguém consegue pedir — e costuma ser descoberta
    quando alguém reescreve a mesma coisa.
    """
    registrados = {(d.module, d.function) for d in R.JOURNEYS.values()}
    achados: List[Achado] = []
    for arquivo in sorted(dir_journeys.glob("*.py")):
        if arquivo.name == "__init__.py":
            continue
        modulo = f"portal_worker.journeys.{arquivo.stem}"
        for nome in _entrypoints_do_arquivo(arquivo):
            if (modulo, nome) in registrados:
                continue
            achados.append(Achado(
                AVISO, f"{arquivo.stem}.{nome}",
                "tem assinatura de journey (`async def (page, params, evidence)`) "
                "e não está em `JOURNEYS`. Ou é um auxiliar que empresta a "
                "assinatura — e vale um comentário dizendo isso — ou é uma "
                "capacidade que o worker não consegue chamar."))
    return achados


def _divergencia_de_doc(R: Any) -> List[Achado]:
    """A matriz publicada bate com o registro? (§22.2 — o `.md` é GERADO.)"""
    doc = _raiz() / DOC_MATRIZ
    if not doc.exists():
        return [Achado(
            AVISO, DOC_MATRIZ,
            "a matriz de capacidades ainda não foi gerada. Enquanto ela não "
            "existir, a documentação do que a casa sabe fazer mora só na cabeça "
            "de quem leu o registro. Gere com `portal_factory.py matrix "
            "--markdown`.")]
    try:
        corpo = doc.read_text(encoding="utf-8", errors="replace")
    except OSError as e:  # noqa: BLE001
        return [Achado(AVISO, DOC_MATRIZ, f"não deu para ler: {e}")]
    faltando = [c for c in sorted(R.JOURNEYS) if c not in corpo]
    if not faltando:
        return []
    return [Achado(
        ERRO, DOC_MATRIZ,
        f"a matriz publicada não menciona {len(faltando)} journey(s) do registro "
        f"({', '.join(faltando[:5])}). Duas afirmações 'atuais' opostas sobre o "
        "que a casa sabe fazer é o defeito que a §22.3 manda corrigir, não "
        "conviver.")]


# ==========================================================================
# matrix — SPEC-075 §22
# ==========================================================================
def _linhas_da_matriz(R: Any) -> List[Dict[str, Any]]:
    fixtures = _mapa_de_fixtures()
    testes = _mapa_de_testes()
    linhas: List[Dict[str, Any]] = []
    for chave in sorted(R.JOURNEYS):
        d = R.JOURNEYS[chave]
        pr = _provas_da_journey(d.portal_key, d.journey_key, fixtures, testes)
        linhas.append({
            "portal": d.portal_key,
            "journey": d.journey_key,
            "business_operation": d.business_operation,
            "effect_class": d.effect_class,
            "requires_account": d.requires_account,
            "supports_resume": d.supports_resume,
            "supports_discovery": d.supports_discovery,
            "contract_version": d.contract_version,
            "fixtures": len(pr.fixtures),
            "fixture_por_journey": pr.fixture_por_journey,
            "testes": len(pr.testes),
            "teste_por_journey": pr.teste_por_journey,
            "description": d.description,
        })
    return linhas


_AVISO_DE_GERADO = (
    "GERADO — NÃO EDITAR MANUALMENTE\n"
    "fonte: `backend/portal_worker/journeys/__init__.py` (registro) + contagem "
    "de fixtures e testes no repositório\n"
    "comando: `python backend/scripts/portal_factory.py matrix --markdown`"
)


def cmd_matrix(args: argparse.Namespace) -> int:
    _preparar_import()
    from portal_worker import journeys as R  # noqa: N812

    matriz = R.matriz_de_capacidades()
    linhas = _linhas_da_matriz(R)

    if args.json:
        print(json.dumps({"operacoes": matriz, "journeys": linhas},
                         ensure_ascii=False, indent=2))
        return 0

    if args.markdown:
        print(f"<!--\n{_AVISO_DE_GERADO}\n-->\n")
        print("# Matriz de capacidades de portal\n")
        print("## Por operação de negócio\n")
        print("| operação | efeito | portais | journeys |")
        print("| --- | --- | --- | --- |")
        for op in sorted(matriz):
            b = matriz[op]
            print(f"| `{op}` | `{b['effect_class']}` | {len(b['portais'])} — "
                  f"{', '.join(b['portais'])} | {len(b['journeys'])} |")
        print("\n## Por journey\n")
        print("| portal | journey | operação | efeito | conta | resume | "
              "discovery | contrato | fixtures | testes |")
        print("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        for L in linhas:
            print(f"| `{L['portal']}` | `{L['journey']}` | "
                  f"`{L['business_operation']}` | `{L['effect_class']}` | "
                  f"{'sim' if L['requires_account'] else 'não'} | "
                  f"{'sim' if L['supports_resume'] else 'não'} | "
                  f"{'sim' if L['supports_discovery'] else 'não'} | "
                  f"{L['contract_version']} | "
                  f"{L['fixtures']}{'' if L['fixture_por_journey'] else '*'} | "
                  f"{L['testes']}{'' if L['teste_por_journey'] else '*'} |")
        print("\n`*` na contagem: a prova foi encontrada no nível do PORTAL, não "
              "no da journey.\n")
        print("### Colunas que a §22.1 pede e que este comando NÃO preenche\n")
        print("`readiness state`, `score`, `last canary`, `live eligible`, "
              "`blocking reason` e `negative cases` vêm de evidência de canário "
              "e de manifesto de teste (§21), não do registro. Escrevê-las aqui "
              "com um palpite seria inventar número — e número ilustrativo que "
              "perde a marca vira 'achado do produto' (CLAUDE.md §12.1). "
              "Ficam de fora até existir a fonte.")
        return 0

    print()
    print("=" * 78)
    print("  MATRIZ DE CAPACIDADES — o que a casa sabe fazer, por operação")
    print("=" * 78)
    for op in sorted(matriz):
        b = matriz[op]
        print()
        print(f"  {op}   [{b['effect_class']}]")
        print(f"    {len(b['portais'])} portal(is): {', '.join(b['portais'])}")
        for j in b["journeys"]:
            d = R.JOURNEYS[j]
            print(f"      · {j:<44} {d.description or '(sem descrição)'}")
    print()
    print("  " + "-" * 74)
    print("  Um portal novo que implemente uma operação JÁ listada não cria "
          "Tool,")
    print("  nem Skill, nem Auxiliar: ele só acrescenta uma linha ao registro.")
    print()
    print(f"  {len(matriz)} operação(ões) · "
          f"{len({d.portal_key for d in R.JOURNEYS.values()})} portal(is) · "
          f"{len(R.JOURNEYS)} journey(s)")
    print()
    return 0


# ==========================================================================
# validate — a coerência do registro consigo mesmo
# ==========================================================================
_RE_CHAVE = re.compile(r"^[a-z][a-z0-9_]*$")


def cmd_validate(args: argparse.Namespace) -> int:
    _preparar_import()
    from portal_worker import journeys as R  # noqa: N812

    try:
        from portal_worker.guardrails import CLASSES_VALIDAS
        fonte_das_classes = "portal_worker.guardrails (SPEC-073)"
    except Exception:  # noqa: BLE001
        CLASSES_VALIDAS = R.FORCA_DA_CLASSE
        fonte_das_classes = "portal_worker.journeys (fallback)"

    alvos = {c: d for c, d in R.JOURNEYS.items()
             if (not args.portal or d.portal_key == args.portal)
             and (not args.journey or d.journey_key == args.journey)}

    print()
    print("=" * 78)
    print("  COERÊNCIA DO REGISTRO — SPEC-075 §9.1/§9.3")
    print(f"  {len(alvos)} de {len(R.JOURNEYS)} journey(s) no escopo · "
          f"classes de efeito lidas de {fonte_das_classes}")
    print("=" * 78)

    if args.portal and not alvos:
        print(f"\n  🔴 portal `{args.portal}` não existe no registro.")
        print(f"  portais conhecidos: "
              f"{', '.join(sorted({d.portal_key for d in R.JOURNEYS.values()}))}")
        return 1

    achados: List[Achado] = []

    for chave, d in sorted(alvos.items()):
        # 1) a CHAVE é derivável dos campos — e isto é o mais grave da lista.
        #
        # 🔴 O worker resolve por `f"{portal_key}.{journey}"` do JOB, não pelos
        # campos da definição. Uma chave que não bate com `portal_key`/
        # `journey_key` cria uma journey que só é alcançável pelo apelido: os
        # metadados (efeito, resume, operação) descrevem uma coisa e a execução
        # pede outra.
        esperada = f"{d.portal_key}.{d.journey_key}"
        if chave != esperada:
            achados.append(Achado(
                ERRO, chave,
                f"a chave do mapa é `{chave}` mas os campos dizem `{esperada}`. "
                "Quem procura pelos campos não acha; quem acha pela chave lê "
                "metadado de outra journey."))

        # 2) formato das chaves
        for nome, valor in (("portal_key", d.portal_key), ("journey_key", d.journey_key)):
            if not _RE_CHAVE.match(valor or ""):
                achados.append(Achado(
                    AVISO, chave,
                    f"`{nome}` = {valor!r} foge do formato `snake_case` minúsculo. "
                    "A chave viaja em job, log e URL; maiúscula e hífen viram "
                    "duas grafias da mesma coisa."))

        # 3) operação conhecida
        if d.business_operation not in R.OPERACOES_CONHECIDAS:
            achados.append(Achado(
                ERRO, chave,
                f"`business_operation` = {d.business_operation!r} não está em "
                "`OPERACOES_CONHECIDAS`. O Work OS pede resultado pela operação; "
                "uma operação fora da lista é uma capacidade que ninguém "
                "consegue pedir pelo nome."))

        # 4) classe de efeito válida
        if d.effect_class not in CLASSES_VALIDAS:
            achados.append(Achado(
                ERRO, chave,
                f"`effect_class` = {d.effect_class!r} não é classe válida "
                f"({', '.join(CLASSES_VALIDAS)}). `normalizar_classe()` trataria "
                "isso como MATERIAL por segurança — o que é o certo, e também "
                "significa que uma leitura passaria a exigir approval sem "
                "ninguém entender por quê."))

        # 5) o módulo é do lugar certo
        if not d.module.startswith("portal_worker.journeys."):
            achados.append(Achado(
                AVISO, chave,
                f"`module` = {d.module!r} está fora de `portal_worker.journeys`. "
                "Journey mora junto do registro para que mapa e código andem no "
                "mesmo commit (§9.1)."))

        # 6) contrato e descrição
        if not str(d.contract_version or "").strip():
            achados.append(Achado(
                AVISO, chave, "`contract_version` vazia: não há como dizer que "
                "o formato de saída mudou sem quebrar quem consome."))
        if not str(d.description or "").strip():
            achados.append(Achado(
                AVISO, chave, "sem `description`. É o texto que a tela de admin "
                "e a matriz mostram; vazio, a capacidade fica anônima."))

        # 7) material sem retomada declarada
        if d.e_material and not d.supports_resume:
            achados.append(Achado(
                AVISO, chave,
                "é `material_side_effect` e declara `supports_resume=False`. "
                "Um job que morreu depois do POST precisa de alguém que saiba "
                "retomar sem repetir — senão a alternativa vira retry cego, que "
                "é o defeito que a SPEC-073 existe para fechar."))

    # 8) AMBIGUIDADE — duas journeys do mesmo portal para a mesma operação.
    #
    # 🔴 Este é o achado silencioso da lista. `journey_para_operacao()` devolve a
    # de `journey_key` MENOR por ordem alfabética quando há empate. Não há erro,
    # não há log: o Gateway pede a operação e recebe a journey que ganhou no
    # alfabeto. Se as duas fizerem coisas diferentes — e elas fazem, senão não
    # seriam duas — o desempate é uma decisão de produto tomada pelo `sorted()`.
    por_par: Dict[Tuple[str, str], List[str]] = {}
    for chave, d in sorted(alvos.items()):
        por_par.setdefault((d.portal_key, d.business_operation), []).append(chave)
    for (portal, op), chaves in sorted(por_par.items()):
        if len(chaves) < 2:
            continue
        achados.append(Achado(
            ERRO, f"{portal} · {op}",
            f"{len(chaves)} journeys disputam a mesma operação neste portal "
            f"({', '.join(chaves)}). `journey_para_operacao()` escolhe "
            f"`{sorted(chaves)[0]}` por ordem alfabética, sem avisar ninguém. "
            "Quem decide qual é a certa é uma pessoa, não o `sorted()`."))

    # 9) o par de compatibilidade continua respondendo o mesmo
    if not args.portal and not args.journey:
        via_operacao = R.portais_com_operacao(R.OP_BILLING_OVERDUE_LIST)
        via_legado = R.portais_com_cobranca()
        if via_operacao != via_legado:
            achados.append(Achado(
                ERRO, "compatibilidade",
                f"`portais_com_cobranca()` = {via_legado} difere de "
                f"`portais_com_operacao('{R.OP_BILLING_OVERDUE_LIST}')` = "
                f"{via_operacao}. O Cobrador usa a primeira e o Work OS usa a "
                "segunda: uma seguradora sairia da varredura para um dos dois."))

    erros = _imprimir_achados(achados, "RESULTADO DA VALIDAÇÃO")
    print()
    print(f"  veredito: {erros} erro(s), "
          f"{len([a for a in achados if not a.reprova])} aviso(s)")
    print()
    return 1 if erros else 0


# ==========================================================================
# Os gabaritos do scaffold
#
# 🔴 Um scaffold que gera código SEM as proteções ensina o erro. Quem parte de
# um esqueleto assume que o esqueleto está certo — e a allowlist, o guard e o
# checkpoint são exatamente as três coisas que ninguém acrescenta depois, porque
# depois o código "já funciona".
# ==========================================================================
_G_CABECALHO = '''# -*- coding: utf-8 -*-
"""Journey @@PORTAL_KEY@@ — @@OPERACAO@@.

⚠️ ESQUELETO GERADO por `backend/scripts/portal_factory.py`. Nada aqui foi
medido. Enquanto houver `TODO`, esta journey não está pronta para rodar contra
o portal real.

O que ela faz para a corretora
==============================
TODO: uma frase sobre o RESULTADO de negócio, não sobre a tela. Quem ler isto
daqui a seis meses precisa saber o que a corretora ganha, não onde fica o botão.

A cadeia, com os corpos reais
=============================
TODO: cada requisição na ordem em que acontece, com os campos que importam, do
jeito que você MEDIU na captura — não do jeito que você espera que seja.

Como marcar número aqui (CLAUDE.md §12.1)
=========================================
    📊  medido: exige data, fonte e o comando/query que produziu o número
    💭  ilustrativo: exemplo ou hipótese, nunca citável como fato

Este esqueleto não escreve nenhum 📊 de propósito. Número de exemplo que perde a
marca atravessa seis documentos como se fosse medição.

O que este arquivo NÃO faz
==========================
Ele não decide nada de negócio. A journey é determinística: recebe `params`,
navega, lê, devolve `JourneyResult`. Quem decide é o Smith.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlsplit

from portal_worker.journeys import JourneyResult
'''

_G_IMPORT_GUARD = '''from portal_worker.guardrails import (
    MATERIAL_SIDE_EFFECT,
    PortalActionGuard,
    motivo_de_bloqueio,
    pode_repetir_com_seguranca,
)
'''

_G_HOSTS = '''

# ==========================================================================
# Hosts — allowlist FECHADA (SPEC-075 §20.2)
#
# 🔴 Descoberta NÃO é autorização. O Profiler ver `POST /alguma-coisa` significa
# "existe uma chamada candidata"; nunca "pode chamar em produção". Sem esta
# lista, a journey é um cliente HTTP de URL livre, e um parâmetro mal validado
# alcança qualquer host da internet.
#
# 🔴 E allowlist por substring não é allowlist, é sugestão:
#
#     "@@HOST_TODO@@" in "@@HOST_TODO@@.evil.com"   ->   True
#
# A comparação abaixo é por host EXATO ou subdomínio, nunca por `in`.
# ==========================================================================
HOSTS_PERMITIDOS: Tuple[str, ...] = (
    "@@HOST_TODO@@",          # TODO: o host real, medido na captura
)

BASE = "https://@@HOST_TODO@@"
LOGIN_URL = BASE + "/TODO"


class HostNaoPermitido(RuntimeError):
    """Tentativa de sair da allowlist. Nunca vira warning — vira parada."""


def _host_permitido(url: Any) -> bool:
    # 🔴 Os DOIS lados descem para minúsculas, e isto não é zelo: `urlsplit(…)
    # .hostname` já devolve minúsculo, então uma única maiúscula digitada em
    # `HOSTS_PERMITIDOS` faz a comparação NUNCA casar — e a allowlist passa a
    # recusar o próprio portal, com a mensagem "host fora da allowlist" apontando
    # para o host que está escrito na lista. É um dia inteiro de depuração.
    host = (urlsplit(str(url or "")).hostname or "").lower()
    for bruto in HOSTS_PERMITIDOS:
        permitido = str(bruto).strip().lower()
        if permitido and (host == permitido or host.endswith("." + permitido)):
            return True
    return False


def exigir_host_permitido(url: str) -> str:
    """Devolve a URL, ou levanta. Chamar ANTES de qualquer navegação ou request.

    Levantar é proposital: host fora da allowlist é erro de programação nosso,
    não condição de portal. Degradar para `needs_human` esconderia o defeito
    atrás de uma fila humana.
    """
    if not _host_permitido(url):
        alvo = urlsplit(str(url or "")).hostname or url
        raise HostNaoPermitido(f"host fora da allowlist: {alvo}")
    return url


async def _ir_para(page, url: str, **kw) -> None:
    await page.goto(exigir_host_permitido(url), **kw)
'''

_G_LOGIN = '''

# ==========================================================================
# login_check — a porta. `read_only` sempre.
# ==========================================================================
async def login_check(page, params: Dict[str, Any],
                      evidence: Dict[str, Any]) -> JourneyResult:
    """Confere se a credencial ainda entra. Não lê dado de negócio."""
    usuario = str(params.get("username") or "").strip()
    senha = str(params.get("password") or "")
    if not usuario or not senha:
        return JourneyResult(status="failed",
                             message="username/password ausentes para @@PORTAL_KEY@@")

    await _ir_para(page, LOGIN_URL, wait_until="domcontentloaded", timeout=90000)

    if await _dentro_do_portal(page):
        # Sessão reaproveitada não é login novo, e a diferença aparece na
        # evidência: sem isso, uma credencial já expirada passa despercebida
        # enquanto o cookie durar.
        evidence["session_reused"] = True
        return JourneyResult(status="done",
                             captured={"logged_in": True,
                                       "portal": "@@PORTAL_KEY@@"})

    # TODO: preencher e submeter. Três coisas que MEDIR antes de escrever:
    #   1. o portal é lento de forma intermitente? (uma recarga costuma salvar
    #      a corrida — desistir na primeira tentativa transforma lentidão em
    #      "não consegui entrar")
    #   2. existe MFA, captcha ou troca de senha obrigatória? cada um é um
    #      `needs_human` diferente, com mensagem própria
    #   3. como o portal diz "senha errada"? distinguir credencial inválida de
    #      portal fora do ar é o que evita desconectar a corretora à toa
    raise NotImplementedError("TODO: login de @@PORTAL_KEY@@")


async def _dentro_do_portal(page) -> bool:
    """TODO: um sinal ESTÁVEL de sessão viva.

    Nome do corretor, item de menu privado, endpoint que só responde logado.
    Não use a URL: redirecionamento de SPA mente, e mente para o lado otimista.
    """
    raise NotImplementedError("TODO: sinal de sessão de @@PORTAL_KEY@@")
'''

_G_JOURNEY_LEITURA = '''

# ==========================================================================
# @@JOURNEY_KEY@@ — @@OPERACAO@@   [@@EFFECT_CLASS@@]
#
# Esta journey NÃO cria nada no mundo. Se, ao escrevê-la, você precisar de um
# POST que confirma, agenda, cancela ou envia algo à seguradora, ela deixou de
# ser leitura: mude `effect_class` no registro e refaça com o gabarito material
# (`portal_factory.py scaffold-journey --effect-class material_side_effect`).
#
# 🔴 Semântica vence verbo HTTP: exportar relatório é POST e é leitura; um GET
# que dispara e-mail ao segurado não é.
# ==========================================================================
async def @@JOURNEY_KEY@@(page, params: Dict[str, Any],
                          evidence: Dict[str, Any]) -> JourneyResult:
    """TODO: o que esta journey DEVOLVE, em uma frase."""
    entrada = await login_check(page, params, evidence)
    if entrada.status != "done":
        return entrada
    evidence["logged_in"] = True

    # TODO: navegar, ler, extrair. Use `_ir_para()`/`exigir_host_permitido()`
    # em toda URL — inclusive nas montadas com parâmetro vindo de `params`.
    itens: List[Dict[str, Any]] = []

    # 🔴 Item que você não conseguiu ler NÃO some: ele é RETIDO, com o motivo
    # escrito, e vai para a fila humana. Descartar em silêncio é como uma
    # cobrança deixa de existir sem ninguém decidir isso.
    retidos: List[Dict[str, Any]] = []

    evidence["@@JOURNEY_KEY@@"] = {"lidos": len(itens), "retidos": len(retidos)}
    return JourneyResult(
        status="done",
        captured={"items": itens, "retained": retidos},
        message=f"{len(itens)} item(ns) lido(s), {len(retidos)} retido(s)")
'''

_G_JOURNEY_MATERIAL = '''

# ==========================================================================
# @@JOURNEY_KEY@@ — @@OPERACAO@@   [material_side_effect]
#
# 🔴 ESTA JOURNEY CRIA COISA NO MUNDO, no nome de um segurado real. As quatro
# regras abaixo não são estilo; cada uma existe por um dano já observado:
#
#   1. RETOMADA ANTES DE TUDO. Um job que morreu DEPOIS do POST volta para a
#      fila e recomeça do passo 1 — e cria um SEGUNDO pedido na seguradora. O
#      segurado descobre quando dois prestadores aparecem.
#   2. SEM `confirm`, PARA NA FRONTEIRA. A journey vai até a tela de
#      confirmação e devolve `needs_human`. Quem libera é o caminho governado
#      (gate do agente / approval), nunca um default.
#   3. CHECKPOINT ANTES DO POST, não depois. `guard.before()` grava
#      `phase=armed` no banco ANTES de a ação acontecer: se o processo morrer
#      no clique, o banco já sabe que havia um clique em curso.
#   4. RESPOSTA PERDIDA É `unknown`, NÃO FALHA. `failed` técnico não significa
#      "não aconteceu nada". Sem protocolo e sem certeza, é `needs_human` com
#      dossiê — jamais um retry.
# ==========================================================================
def _guard_do(params: Dict[str, Any]) -> PortalActionGuard:
    """O guard do runtime — e, sem ele, uma porta FECHADA.

    🔴 Fail-CLOSED de propósito. `guard.armar()` só persiste `phase=armed` se
    tiver um checkpoint durável; um guard construído solto não tem nenhum. Com
    `material_liberado=True` e sem runtime, o POST sairia sem que o banco
    soubesse que havia um POST em curso — o `maybe_committed` sem ninguém para
    reconciliar. Em produção o worker sempre injeta `params["_runtime"]`, mas
    "sempre" é uma suposição sobre outro módulo, e fronteira material não se
    apoia em suposição.
    """
    rt = params.get("_runtime")
    g = getattr(rt, "guard", None)
    if g is not None:
        return g
    return PortalActionGuard(material_liberado=False)


async def _checkpoint(params: Dict[str, Any], patch: Dict[str, Any]) -> None:
    rt = params.get("_runtime")
    if rt is not None and hasattr(rt, "checkpoint"):
        await rt.checkpoint(patch)


async def @@JOURNEY_KEY@@(page, params: Dict[str, Any],
                          evidence: Dict[str, Any]) -> JourneyResult:
    """TODO: o que esta journey CRIA, em uma frase."""
    # ---- 1. retomada: o mundo já sabe de alguma coisa? -------------------
    if not pode_repetir_com_seguranca(evidence):
        return JourneyResult(
            status="needs_human",
            captured={"reconciliar": True},
            message=("retomada bloqueada: " + motivo_de_bloqueio(evidence)))

    entrada = await login_check(page, params, evidence)
    if entrada.status != "done":
        return entrada
    evidence["logged_in"] = True

    guard = _guard_do(params)
    # 🔴 Nomear a ação não é redundante com liberar o efeito material. Liberar
    # responde "pode haver um efeito material aqui"; nomear responde "pode ser
    # ESTE". Numa tela com "Confirmar", "Agendar" e "Cancelar", só a segunda
    # pergunta impede o clique certo na hora errada. Rótulos alternativos vão
    # separados por `|`; a comparação ignora acento.
    guard.acao_material_esperada = "TODO|confirmar"

    # TODO: preencher o formulário até a fronteira. Preencher é `reversible_ui`
    # e pode acontecer sempre; o que não pode é enviar.

    # ---- 2. sem liberação, para AQUI e devolve o que viu -----------------
    if not bool(params.get("confirm")):
        return JourneyResult(
            status="needs_human",
            captured={"pronto_para_confirmar": True,
                      # TODO: tudo que a pessoa precisa para decidir sem
                      # reabrir o portal (resumo, valor, franquia, prazo).
                      "resumo": {}},
            message="pronto na tela de confirmação; falta a liberação explícita")

    chave = _chave_de_idempotencia(params)

    # ---- 3. checkpoint ANTES do efeito -----------------------------------
    # `before()` avalia E arma: para `MATERIAL_SIDE_EFFECT` permitido ele grava
    # `phase=armed` antes de retornar. Se levantar `AcaoBloqueada`, deixe subir
    # — recusa é resposta correta, e engoli-la aqui vira efeito sem autorização.
    await guard.before(action="@@JOURNEY_KEY@@",
                       action_class=MATERIAL_SIDE_EFFECT,
                       details={"idempotency_key": chave})

    try:
        resposta = await _enviar(page, params)   # TODO
    except Exception as e:  # noqa: BLE001
        # 🔴 A exceção NÃO prova que nada aconteceu: o pedido pode ter chegado e
        # a resposta ter se perdido. `unknown` é o estado honesto, e é o único
        # em que a tentação de "tenta de novo" é forte e errada.
        await guard.incerto(motivo=f"{type(e).__name__} durante o envio")
        await _checkpoint(params, {"@@JOURNEY_KEY@@": {"fase": "unknown"}})
        return JourneyResult(
            status="needs_human",
            captured={"reconciliar": True, "idempotency_key": chave},
            message=("o envio saiu e a resposta se perdeu; reconciliar no "
                     "portal antes de qualquer nova tentativa"))

    await guard.submetido()

    protocolo = _protocolo_de(resposta)          # TODO
    if not protocolo:
        # 🔴 Sem prova autoritativa, o desfecho é incerto — nunca `done` e nunca
        # `failed`. Dizer "não abriu" para o cliente aqui é o pior dos dois erros.
        await guard.incerto(motivo="resposta sem protocolo")
        return JourneyResult(
            status="needs_human",
            captured={"reconciliar": True, "idempotency_key": chave},
            message="enviado, sem protocolo na resposta: conferir no portal")

    await guard.confirmado(receipt=protocolo)
    await _checkpoint(params, {"@@JOURNEY_KEY@@": {"protocolo": protocolo}})
    return JourneyResult(status="done",
                         captured={"protocolo": protocolo},
                         message=f"protocolo {protocolo}")


def _chave_de_idempotencia(params: Dict[str, Any]) -> str:
    """TODO: identidade SEMÂNTICA do pedido, sem PII bruta.

    É o que permite reconhecer "isto já foi feito" numa retomada. Componha dos
    campos que definem o pedido (documento hasheado, placa hasheada, data,
    tipo), nunca do `job_id` — o job muda a cada tentativa e a chave passaria a
    concordar com toda repetição.
    """
    raise NotImplementedError("TODO: chave de idempotência de @@JOURNEY_KEY@@")


async def _enviar(page, params: Dict[str, Any]) -> Any:
    """TODO: a ÚNICA chamada/clique que materializa o pedido."""
    raise NotImplementedError("TODO: envio de @@JOURNEY_KEY@@")


def _protocolo_de(resposta: Any) -> str:
    """TODO: extrair a prova autoritativa. String vazia = não houve prova."""
    raise NotImplementedError("TODO: protocolo de @@JOURNEY_KEY@@")
'''

_G_TESTE = '''# -*- coding: utf-8 -*-
"""TODO: renomeie este arquivo para a FRASE que ele prova.

A casa nomeia teste pelo que ele segura, em português — `test_a_cobranca_
alcanca_todas_as_seguradoras.py`, não `test_@@PORTAL_KEY@@_contract.py`. O nome
genérico veio do gabarito porque o gabarito não sabe o que você vai provar.

O que estes testes seguram
==========================
    [1] o registro       a journey está no mapa, com a operação e o efeito
                         que ela realmente tem
    [2] o contrato       o módulo importa e a função é `async`
    [3] a allowlist      host de fora é RECUSADO — provado CHAMANDO
@@BLOCO_DOC_MATERIAL@@
🔴 CLAUDE.md §9.3: um guarda que não tem como falhar não guarda nada. Por isso
[3] prova os dois lados — que um host permitido PASSA e que um de fora NÃO
passa. Um teste que só verifica o caso feliz aprovaria uma allowlist vazia.
"""
from __future__ import annotations

import asyncio
import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

PASS = FAIL = 0


def check(nome, condicao, extra=""):
    global PASS, FAIL
    if condicao:
        PASS += 1
        print("  [ok] " + nome)
    else:
        FAIL += 1
        print("  [FALHOU] " + nome + ("  " + str(extra)[:220] if extra else ""))


from portal_worker.journeys import (                       # noqa: E402
    JOURNEYS, get_definition, get_journey, journey_para_operacao)
from portal_worker.journeys import @@MODULO_CURTO@@ as J   # noqa: E402

CHAVE = "@@CHAVE@@"


# ==========================================================================
print("\\n[1] O REGISTRO — o mapa diz o que esta journey é")
# ==========================================================================
d = get_definition("@@PORTAL_KEY@@", "@@JOURNEY_KEY@@")
check("a journey está no registro", d is not None)
check("a chave bate com os campos", d is not None and d.chave == CHAVE, d)
check("a operação de negócio é a esperada",
      d is not None and d.business_operation == "@@OPERACAO@@",
      d.business_operation if d else None)
check("a classe de efeito é a esperada",
      d is not None and d.effect_class == "@@EFFECT_CLASS@@",
      d.effect_class if d else None)
check("a operação resolve para ESTA journey neste portal",
      (journey_para_operacao("@@PORTAL_KEY@@", "@@OPERACAO@@") or d) is d)
check("entrar no mapa não desmarcou ninguém", len(JOURNEYS) >= 1, len(JOURNEYS))


# ==========================================================================
print("\\n[2] O CONTRATO — o registro aponta para código que existe")
# ==========================================================================
fn = get_journey("@@PORTAL_KEY@@", "@@JOURNEY_KEY@@")
check("get_journey() resolve", fn is not None)
check("é uma corrotina", fn is not None and inspect.iscoroutinefunction(fn))
check("a assinatura é (page, params, evidence)",
      fn is not None and
      list(inspect.signature(fn).parameters)[:3] == ["page", "params", "evidence"],
      list(inspect.signature(fn).parameters) if fn else None)


# ==========================================================================
print("\\n[3] A ALLOWLIST — e ela precisa CONSEGUIR recusar")
# ==========================================================================
permitido = "https://" + J.HOSTS_PERMITIDOS[0] + "/qualquer/caminho"
check("host da allowlist passa", J._host_permitido(permitido))
check("subdomínio do host permitido passa",
      J._host_permitido("https://sub." + J.HOSTS_PERMITIDOS[0] + "/x"))
# 🔴 O caso que derruba allowlist por substring: o host permitido aparece
# INTEIRO dentro de um domínio de terceiro.
check("sufixo malicioso é RECUSADO",
      not J._host_permitido("https://" + J.HOSTS_PERMITIDOS[0] + ".evil.com/x"))
check("host de fora é RECUSADO", not J._host_permitido("https://evil.com/x"))
try:
    J.exigir_host_permitido("https://evil.com/x")
    check("exigir_host_permitido levanta", False, "não levantou")
except J.HostNaoPermitido:
    check("exigir_host_permitido levanta", True)
@@BLOCO_TESTE_MATERIAL@@

print("\\n" + "=" * 66)
print(f"  {PASS} asserções verdes · {FAIL} vermelhas")
print("=" * 66)
sys.exit(1 if FAIL else 0)
'''

_G_TESTE_DOC_MATERIAL = '''    [4] a fronteira      sem `confirm`, a journey PARA antes de criar nada
    [5] a retomada       evidência de efeito em curso impede repetir

'''

_G_TESTE_MATERIAL = '''

# ==========================================================================
print("\\n[4] A FRONTEIRA — sem liberação, nada é criado")
# ==========================================================================
# 🔴 Este é o teste que impede o segundo atendimento pago. Ele precisa CONSEGUIR
# falhar: se `_enviar()` for chamado sem `confirm`, a asserção abaixo vira
# vermelha, e é para isso que a sentinela existe.
_ENVIOU = {"sim": False}


async def _sentinela(page, params):
    _ENVIOU["sim"] = True
    return {"protocolo": "NUNCA-DEVERIA-SAIR"}


_original = J._enviar
J._enviar = _sentinela
try:
    ev = {}
    # TODO: um `page` de mentira que chegue até a fronteira, e params reais
    #       sem `confirm`. Enquanto o TODO estiver aqui, este bloco NÃO prova
    #       nada — e é por isso que ele começa vermelho.
    check("TODO: exercitar a journey sem confirm", False,
          "escreva o page falso e os params do caso real")
    check("nada foi enviado sem confirm", not _ENVIOU["sim"])
finally:
    J._enviar = _original


# ==========================================================================
print("\\n[5] A RETOMADA — efeito em curso não se repete")
# ==========================================================================
from portal_worker.guardrails import (                     # noqa: E402
    CHAVE_EFEITO, FASE_SUBMITTED, pode_repetir_com_seguranca)

ev_submetido = {CHAVE_EFEITO: {"name": "@@JOURNEY_KEY@@",
                               "phase": FASE_SUBMITTED}}
check("evidência de envio em curso BLOQUEIA a repetição",
      not pode_repetir_com_seguranca(ev_submetido))
# A linha de controle: sem evidência nenhuma, repetir é permitido. Sem ela, a
# asserção acima passaria mesmo se a função devolvesse False para tudo.
check("CONTROLE: sem evidência, repetir é permitido",
      pode_repetir_com_seguranca({}))
'''

_G_MANIFESTO = {
    "portal_key": "@@PORTAL_KEY@@",
    "journey_key": "@@JOURNEY_KEY@@",
    "operation_key": "@@OPERACAO@@",
    "captured_at": "TODO-AAAA-MM-DD",
    "source": "TODO: founder_har_sanitized | profiler | captura_manual",
    "pii": "removed",
    "secrets": "removed",
    "effect": "@@EFEITO_CURTO@@",
    "expected_state": "success",
}


def _aplicar(gabarito: str, subs: Dict[str, str]) -> str:
    """Substitui `@@CHAVE@@`, em PASSES, até nada mais mudar.

    📊 16/08/2026 — o passe único deixou `@@JOURNEY_KEY@@` cru dentro do teste
    gerado para journey material. O motivo: uma das substituições injeta OUTRO
    gabarito (`BLOCO_TESTE_MATERIAL`), e o bloco injetado chega depois de
    `JOURNEY_KEY` já ter sido trocada — o texto novo nunca vê o seu turno.

    Depender da ordem do dicionário consertaria hoje e quebraria na próxima
    substituição aninhada que alguém acrescentasse. O laço não depende de ordem
    nenhuma. O teto de 5 existe para que um gabarito que se referencie a si
    mesmo pare, em vez de girar para sempre.
    """
    saida = gabarito
    for _ in range(5):
        antes = saida
        for k, v in subs.items():
            saida = saida.replace(f"@@{k}@@", v)
        if saida == antes:
            break
    return saida


# ==========================================================================
# scaffold — §17.3 e §17.4
# ==========================================================================
def _gate_da_operacao(R: Any, operacao: str, effect_class: Optional[str]) -> Tuple[bool, str]:
    """§17.4 — a pergunta que impede a inflação de catálogo.

    Antes de gerar código, a máquina responde: **esta operação já existe em
    outro portal?** Se sim, o onboarding é só uma journey — a Tool, a Skill e a
    Capability já existem, e criar novas duplicaria o catálogo por causa de um
    nome. Se não, é `capability_gap`, e gap novo exige classificação de risco
    ANTES de virar Tool.
    """
    conhecida = operacao in R.OPERACOES_CONHECIDAS
    portais = R.portais_com_operacao(operacao)
    linhas: List[str] = []
    linhas.append("")
    linhas.append("-" * 78)
    linhas.append("  GATE DA OPERAÇÃO — SPEC-075 §17.4")
    linhas.append("-" * 78)
    if conhecida and portais:
        b = R.matriz_de_capacidades().get(operacao, {})
        linhas.append(f"  `{operacao}` JÁ EXISTE em {len(portais)} portal(is): "
                      f"{', '.join(portais)}")
        linhas.append(f"  efeito já registrado para a operação: "
                      f"{b.get('effect_class', '?')}")
        linhas.append("")
        linhas.append("  → REUTILIZAR a Tool, a Skill e a Capability existentes.")
        linhas.append("    Implemente SOMENTE a journey. Uma seguradora nova não")
        linhas.append("    cria Auxiliar novo nem Tool nova: ela acrescenta um")
        linhas.append("    portal que já sabe fazer uma operação conhecida.")
        linhas.append("")
        linhas.append("    Não crie tool por seguradora (§11.3). Se você estiver")
        linhas.append("    prestes a escrever `portal.<seguradora>.<coisa>`, pare.")
        return True, "\n".join(linhas)

    linhas.append(f"  `{operacao}` NÃO existe em portal nenhum: é um "
                  "**capability_gap**.")
    linhas.append(f"  operações registradas hoje: "
                  f"{', '.join(R.OPERACOES_CONHECIDAS)}")
    linhas.append("")
    if not effect_class:
        linhas.append("  🔴 PARADO. Gap novo exige classificação de risco ANTES de")
        linhas.append("     gerar código. Repita o comando com `--effect-class`:")
        linhas.append("")
        linhas.append("       read_only ............ login · navegar · filtrar ·")
        linhas.append("                              listar · baixar PDF · exportar")
        linhas.append("       reversible_ui ........ preencher campo ainda não")
        linhas.append("                              enviado · abrir dropdown")
        linhas.append("       material_side_effect . criar · agendar · cancelar ·")
        linhas.append("                              alterar pagamento · enviar")
        linhas.append("")
        linhas.append("     🔴 Semântica vence verbo HTTP: exportar relatório é")
        linhas.append("        POST e é `read_only`; um GET que dispara e-mail ao")
        linhas.append("        segurado não é.")
        linhas.append("")
        linhas.append("     Este gate é a diferença entre um catálogo que cresce")
        linhas.append("     com o produto e um que cresce com cada sinônimo.")
        return False, "\n".join(linhas)

    linhas.append(f"  classificação de risco declarada: `{effect_class}`")
    linhas.append("")
    linhas.append("  → REGISTRAR a proposta antes de criar Tool. Cole em")
    linhas.append("    `docs/canon/PENDENCIAS.md` (CLAUDE.md §11.1):")
    linhas.append("")
    linhas.append(f"      capability_gap: `{operacao}`")
    linhas.append(f"      efeito proposto: {effect_class}")
    linhas.append("      o que destrava: revisão técnica + decisão de quem")
    linhas.append("        autoriza o efeito (🧑 Founder se houver custo ou")
    linhas.append("        contato com segurado; 🤖 execução se for leitura)")
    linhas.append("      o que custa esquecer: journey pronta e inalcançável —")
    linhas.append("        código no ar que nenhum Auxiliar consegue pedir")
    linhas.append("")
    linhas.append("  E acrescente a constante em `journeys/__init__.py`:")
    linhas.append("")
    linhas.append(f"      OP_{_const_da_operacao(operacao)} = \"{operacao}\"")
    linhas.append("")
    linhas.append("      OPERACOES_CONHECIDAS: Tuple[str, ...] = (")
    linhas.append("          ...,")
    linhas.append(f"          OP_{_const_da_operacao(operacao)},")
    linhas.append("      )")
    return True, "\n".join(linhas)


def _const_da_operacao(operacao: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", str(operacao).upper()).strip("_")


def _bloco_do_registro(portal_key: str, journey_key: str, operacao: str,
                       effect_class: str, com_login: bool,
                       modulo: str) -> str:
    op_const = f"OP_{_const_da_operacao(operacao)}"
    material = effect_class == "material_side_effect"
    linhas: List[str] = []
    linhas.append("")
    linhas.append("-" * 78)
    linhas.append("  COLE ISTO EM `backend/portal_worker/journeys/__init__.py`")
    linhas.append("-" * 78)
    linhas.append("  🔴 A factory NÃO edita o registro. Gerador que reescreve")
    linhas.append("     arquivo de código cria divergência silenciosa, e este é")
    linhas.append("     o arquivo em que uma linha errada faz o worker chamar a")
    linhas.append("     função errada em produção. Cole você, e leia o diff.")
    linhas.append("")
    linhas.append("  Dentro de `JOURNEYS: Dict[str, JourneyDefinition] = {`:")
    linhas.append("")
    if com_login:
        linhas.append(f'    "{portal_key}.login_check": JourneyDefinition(')
        linhas.append(f'        portal_key="{portal_key}", journey_key="login_check",')
        linhas.append("        business_operation=OP_PORTAL_LOGIN_CHECK,")
        linhas.append(f'        module="{modulo}", function="login_check",')
        linhas.append("        effect_class=READ_ONLY,")
        linhas.append('        description="TODO: confere se a credencial ainda entra"),')
    linhas.append(f'    "{portal_key}.{journey_key}": JourneyDefinition(')
    linhas.append(f'        portal_key="{portal_key}", journey_key="{journey_key}",')
    linhas.append(f"        business_operation={op_const},")
    linhas.append(f'        module="{modulo}", function="{journey_key}",')
    linhas.append(f"        effect_class={effect_class.upper()},")
    if material:
        linhas.append("        supports_resume=True,")
    linhas.append('        description="TODO: o resultado, em uma frase"),')
    linhas.append("")
    if com_login and effect_class == "read_only" and \
            operacao == "billing.overdue.list" and journey_key == "cobranca_sweep":
        linhas.append("  ⚠️ ATENÇÃO: `login_check` + `cobranca_sweep` com esses")
        linhas.append("     metadados é exatamente o que o helper `_cobranca()` já")
        linhas.append("     escreve. Use-o em vez das duas entradas acima:")
        linhas.append("")
        linhas.append(f'    **_cobranca("{portal_key}", "{modulo}"),')
        linhas.append("")
        linhas.append("     Duas linhas copiadas com os mesmos metadados são duas")
        linhas.append("     linhas que podem divergir; o helper não pode.")
        linhas.append("")
    linhas.append("  Depois, prove que o registro continua coerente:")
    linhas.append("")
    linhas.append("    python backend/scripts/portal_factory.py validate "
                  f"--portal {portal_key}")
    linhas.append("    python backend/scripts/portal_factory.py audit")
    return "\n".join(linhas)


def _gerar(portal_key: str, journey_key: str, operacao: str, effect_class: str,
           com_login: bool) -> Dict[str, str]:
    """`{caminho relativo: conteúdo}` — nada é escrito aqui."""
    material = effect_class == "material_side_effect"
    modulo_curto = portal_key
    subs = {
        "PORTAL_KEY": portal_key,
        "JOURNEY_KEY": journey_key,
        "OPERACAO": operacao,
        "EFFECT_CLASS": effect_class,
        "EFEITO_CURTO": "material" if material else "read",
        "HOST_TODO": f"TODO-{portal_key.replace('_', '-')}.com.br",
        "MODULO_CURTO": modulo_curto,
        "CHAVE": f"{portal_key}.{journey_key}",
        "BLOCO_DOC_MATERIAL": _G_TESTE_DOC_MATERIAL if material else "",
        "BLOCO_TESTE_MATERIAL": _G_TESTE_MATERIAL if material else "",
    }

    modulo = _G_CABECALHO
    if material:
        modulo += _G_IMPORT_GUARD
    modulo += _G_HOSTS
    if com_login:
        modulo += _G_LOGIN
    modulo += _G_JOURNEY_MATERIAL if material else _G_JOURNEY_LEITURA

    manifesto = json.dumps(
        json.loads(_aplicar(json.dumps(_G_MANIFESTO, ensure_ascii=False), subs)),
        ensure_ascii=False, indent=2)

    return {
        f"backend/portal_worker/journeys/{modulo_curto}.py": _aplicar(modulo, subs),
        f"backend/tests/test_{portal_key}_portal_contract.py": _aplicar(_G_TESTE, subs),
        (f"backend/tests/fixtures/{DIR_FIXTURES_CANONICO}/{portal_key}/"
         f"{journey_key}/caso_feliz/manifest.json"): manifesto + "\n",
    }


def _conferir_que_compila(arquivos: Dict[str, str]) -> List[str]:
    """O gabarito gera Python VÁLIDO e sem placeholder órfão? Provado, não lido.

    🔴 Um scaffold que gera arquivo com erro de sintaxe queima a confiança na
    primeira tentativa — e a pessoa passa a escrever tudo à mão, que é
    exatamente o que a factory existe para evitar. A conferência roda sempre, e
    falhar aqui é bug DESTE script, não do usuário.
    """
    problemas: List[str] = []
    for nome, corpo in arquivos.items():
        # Placeholder que sobrou é sintaxe VÁLIDA em comentário e em string —
        # `compile()` não o vê. Foi assim que `@@JOURNEY_KEY@@` chegou inteiro
        # ao teste gerado, com o arquivo compilando. Quem pegou foi a medição.
        for numero, linha in enumerate(corpo.splitlines(), 1):
            if "@@" in linha:
                problemas.append(f"{nome}: linha {numero}: placeholder não "
                                 f"substituído — {linha.strip()[:70]}")
        if not nome.endswith(".py"):
            continue
        try:
            compile(corpo, nome, "exec")
        except SyntaxError as e:
            problemas.append(f"{nome}: linha {e.lineno}: {e.msg}")
    return problemas


def _scaffold(args: argparse.Namespace, com_login: bool) -> int:
    _preparar_import()
    from portal_worker import journeys as R  # noqa: N812

    portal_key = str(args.portal_key or "").strip()
    operacao = str(args.operation or "").strip()
    journey_key = str(getattr(args, "journey_key", "") or "").strip()

    if not _RE_CHAVE.match(portal_key):
        print(f"\n  🔴 `--portal-key {portal_key!r}` foge do formato snake_case "
              "minúsculo. A chave viaja em job, log e URL.")
        return 2

    existentes = R.journeys_do_portal(portal_key)
    if com_login and existentes:
        print(f"\n  🔴 o portal `{portal_key}` JÁ está no registro com "
              f"{len(existentes)} journey(s): "
              f"{', '.join(d.journey_key for d in existentes)}")
        print("     Para acrescentar uma capacidade a ele, use "
              "`scaffold-journey`.")
        print("     Gerar o módulo de novo sobrescreveria journeys que já foram")
        print("     medidas contra o portal real.")
        return 2
    if not com_login and not existentes:
        print(f"\n  🔴 o portal `{portal_key}` não existe no registro.")
        print("     Para um portal novo, use `scaffold-portal` — ele gera "
              "também o `login_check`,")
        print("     que é o par sem o qual não existe 'portal conectado'.")
        print(f"     portais conhecidos: "
              f"{', '.join(sorted({d.portal_key for d in R.JOURNEYS.values()}))}")
        return 2

    if not journey_key:
        journey_key = re.sub(r"[^a-z0-9]+", "_", operacao.lower()).strip("_") or "TODO"
    if not _RE_CHAVE.match(journey_key):
        print(f"\n  🔴 `--journey-key {journey_key!r}` foge do formato snake_case.")
        return 2

    chave = f"{portal_key}.{journey_key}"
    if chave in R.JOURNEYS:
        print(f"\n  🔴 `{chave}` já existe no registro. Escolha outra "
              "`--journey-key`,")
        print("     ou edite a journey existente — duas entradas para a mesma")
        print("     capacidade é como o mapa passa a mentir.")
        return 2

    print()
    print("=" * 78)
    print(f"  SCAFFOLD — {chave}")
    print(f"  operação: {operacao}")
    print("=" * 78)

    prossegue, texto_do_gate = _gate_da_operacao(R, operacao, args.effect_class)
    print(texto_do_gate)
    if not prossegue:
        return 2

    effect_class = args.effect_class
    if not effect_class:
        b = R.matriz_de_capacidades().get(operacao, {})
        effect_class = b.get("effect_class", "read_only")
        print()
        print(f"  efeito herdado da operação já registrada: `{effect_class}`")
        print("  (use `--effect-class` para declarar outro — e, se for MAIS")
        print("   FORTE, a divergência entre portais é uma decisão, não um")
        print("   detalhe.)")

    arquivos = _gerar(portal_key, journey_key, operacao, effect_class, com_login)

    problemas = _conferir_que_compila(arquivos)
    if problemas:
        print("\n  🔴 BUG NESTE SCRIPT: o gabarito gerou Python inválido.")
        for p in problemas:
            print(f"     {p}")
        print("     Nada foi impresso nem escrito. Conserte o gabarito.")
        return 1
    print()
    print(f"  ✔ os {len([n for n in arquivos if n.endswith('.py')])} arquivos "
          "Python gerados COMPILAM (conferido com `compile()`, não por leitura)")

    print(_bloco_do_registro(portal_key, journey_key, operacao, effect_class,
                             com_login, f"portal_worker.journeys.{portal_key}"))

    print()
    print("-" * 78)
    print("  O QUE ESTE COMANDO NÃO FEZ — e não vai fazer (§17.3)")
    print("-" * 78)
    print("    · não guardou senha nem tocou no Vault")
    print("    · não criou o portal no banco")
    print("    · não publicou Tool, Skill nem capability")
    print("    · não comitou nada")
    print("    · não fez login real em portal nenhum")
    print("  Esqueleto é o começo do trabalho, não a entrega.")

    if args.write:
        return _escrever(arquivos)

    for nome, corpo in arquivos.items():
        print()
        print("=" * 78)
        print(f"  ARQUIVO: {nome}")
        print("=" * 78)
        print(corpo)
    print()
    print("  (rode de novo com `--write` para gravar estes arquivos; arquivo")
    print("   existente NUNCA é sobrescrito.)")
    print()
    return 0


def _escrever(arquivos: Dict[str, str]) -> int:
    raiz = _raiz()
    print()
    print("-" * 78)
    print("  GRAVANDO")
    print("-" * 78)
    conflito = False
    for nome in arquivos:
        if (raiz / nome).exists():
            print(f"    X  {nome}  — JÁ EXISTE")
            conflito = True
    if conflito:
        print()
        print("  🔴 nada foi gravado. Sobrescrever arquivo existente é como se")
        print("     apaga uma journey medida contra o portal real; a factory não")
        print("     tem como saber o que havia ali.")
        return 2
    for nome, corpo in arquivos.items():
        destino = raiz / nome
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(corpo, encoding="utf-8")
        print(f"    +  {nome}")
    print()
    print("  Nenhum destes arquivos está no registro ainda: cole o bloco acima")
    print("  em `journeys/__init__.py` e rode `validate` + `audit`.")
    print()
    return 0


def cmd_scaffold_portal(args: argparse.Namespace) -> int:
    return _scaffold(args, com_login=True)


def cmd_scaffold_journey(args: argparse.Namespace) -> int:
    return _scaffold(args, com_login=False)


# ==========================================================================
# CLI
# ==========================================================================
_CLASSES = ("read_only", "reversible_ui", "material_side_effect")


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="portal_factory",
        description=("Portal Capability Factory (SPEC-075 §17) — audita o "
                     "registro de journeys e gera esqueleto. Não executa "
                     "journey, não publica nada, não edita o registro."),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=("`audit` e `validate` saem com código != 0 quando encontram "
                "problema real:\nsão gates, e um gate que sempre sai 0 é "
                "enfeite."))
    sub = p.add_subparsers(dest="comando", required=True)

    a = sub.add_parser("audit", help="o registro bate com código, fixtures e testes?")
    a.set_defaults(func=cmd_audit)

    m = sub.add_parser("matrix", help="o que a casa sabe fazer, por operação")
    m.add_argument("--markdown", action="store_true",
                   help="tabela em Markdown, com o cabeçalho de GERADO (§22.2)")
    m.add_argument("--json", action="store_true",
                   help="a mesma matriz em JSON, para consumo de máquina")
    m.set_defaults(func=cmd_matrix)

    v = sub.add_parser("validate", help="o registro é coerente consigo mesmo?")
    v.add_argument("--portal", default="", help="limita a um portal")
    v.add_argument("--journey", default="", help="limita a uma journey_key")
    v.set_defaults(func=cmd_validate)

    sp = sub.add_parser("scaffold-portal",
                        help="esqueleto de um portal NOVO (com login_check)")
    sp.add_argument("--portal-key", required=True,
                    help="a chave do portal, em snake_case (ex.: `porto_corretor`)")
    sp.add_argument("--operation", required=True,
                    help="a operação de negócio (ex.: `billing.overdue.list`)")
    sp.add_argument("--journey-key", default="",
                    help="opcional; por padrão deriva da operação")
    sp.add_argument("--effect-class", choices=_CLASSES, default="",
                    help="obrigatório quando a operação ainda não existe (§17.4)")
    sp.add_argument("--write", action="store_true",
                    help="grava os arquivos; nunca sobrescreve")
    sp.set_defaults(func=cmd_scaffold_portal)

    sj = sub.add_parser("scaffold-journey",
                        help="esqueleto de uma capacidade em portal EXISTENTE")
    sj.add_argument("--portal-key", required=True, help="portal já registrado")
    sj.add_argument("--journey-key", required=True,
                    help="🔴 nome de CAPACIDADE, não de trabalho: o que o robô "
                         "SABE FAZER (`listar_parcelas_em_atraso`), não para que "
                         "estamos usando hoje")
    sj.add_argument("--operation", required=True, help="a operação de negócio")
    sj.add_argument("--effect-class", choices=_CLASSES, default="",
                    help="obrigatório quando a operação ainda não existe (§17.4)")
    sj.add_argument("--write", action="store_true",
                    help="grava os arquivos; nunca sobrescreve")
    sj.set_defaults(func=cmd_scaffold_journey)
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    _saida_utf8()
    args = _parser().parse_args(list(argv) if argv is not None else None)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
