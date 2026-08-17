# -*- coding: utf-8 -*-
"""Gera `docs/generated/portal-capability-matrix.md` — SPEC-075 Bloco M.

    python backend/scripts/gerar_matriz_de_portais.py

## Por que este arquivo existe, e por que ele é pequeno

O Bloco L (`app/services/portals/prontidao.py`) sabe **pontuar** uma journey a
partir de sinais, e é puro de propósito: sem disco, sem banco, sem rede — para
poder ser testado sem infraestrutura.

O Bloco I (`scripts/portal_factory.py`) sabe **auditar** o repositório.

Faltava quem ligasse um ao outro. Sem essa ligação, `matriz_markdown()` roda sem
sinal nenhum e publica um documento em que **todas as 14 journeys aparecem com
score 0** — o que é tecnicamente correto (ausência de medição é falta de prova)
e praticamente inútil: um relatório em que tudo é zero não distingue a journey
que ninguém testou daquela que tem fixture, replay e teste verde.

## 🔴 O que este gerador NÃO faz: inventar sinal

Ele preenche **apenas** o que o repositório prova sozinho, olhando arquivos:

    fixtures            existe fixture para este portal?
    testes_verdes       existe arquivo de teste que cita este portal?
    caminho_primario    a journey usa API-first, DOM, adaptive ou visão?
    casos_negativos     o teste exercita caso negativo?

Todo o resto — isolamento de tenant provado, idempotência provada, canário
verde, aprovação de lançamento — fica **ausente**, e ausente conta como não
provado. Isso não é limitação: é a única postura honesta. Nenhum arquivo no
disco prova que uma journey foi exercitada contra o portal real sem vazar dado
entre corretoras. Só um canário prova, e canário não se deduz de `ls`.

📊 Por isso o documento gerado hoje mostra score baixo em tudo. Ele não está
dizendo que as journeys são ruins — está dizendo quanta prova existe. A coluna
que muda quando alguém mede é a que faz o documento valer.
"""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
BACKEND = RAIZ / "backend"
SAIDA = RAIZ / "docs" / "generated" / "portal-capability-matrix.md"

sys.path.insert(0, str(BACKEND))
for _n in ("app", "app.services", "app.services.portals"):
    _m = sys.modules.setdefault(_n, types.ModuleType(_n))
    _m.__path__ = [str(BACKEND / _n.replace(".", "/"))]

_sp = importlib.util.spec_from_file_location(
    "app.services.portals.prontidao",
    BACKEND / "app" / "services" / "portals" / "prontidao.py")
PR = importlib.util.module_from_spec(_sp)
sys.modules["app.services.portals.prontidao"] = PR
_sp.loader.exec_module(PR)

from portal_worker.journeys import JOURNEYS  # noqa: E402

FIXTURES = BACKEND / "tests" / "fixtures"
TESTES = BACKEND / "tests"


def _prefixo(portal_key: str) -> str:
    """`tokiomarine_corretor` → `tokio`, `vidros_lanternas` → `vidros`.

    📊 O prefixo curto existe porque os nomes não batem: o portal é
    `tokiomarine_corretor` e a fixture é `tokio_inadimplentes.py`. Igualdade
    estrita diria "sem fixture" sobre uma fixture que está lá.
    """
    base = portal_key.replace("_corretor", "").replace("_lanternas", "")
    return base[:5] if len(base) > 5 else base


def _tem_arquivo(diretorio: Path, prefixo: str) -> bool:
    if not diretorio.exists():
        return False
    for p in diretorio.rglob("*"):
        if "__pycache__" in p.parts:
            continue
        if p.is_file() and prefixo and prefixo in p.name.lower():
            return True
        if p.is_dir() and prefixo and prefixo in p.name.lower():
            return True
    return False


def _caminho_primario(definicao) -> str:
    """Lê o MÓDULO da journey para saber como ela navega.

    Não é heurística sobre o nome: procura o import do cliente de API dentro do
    próprio arquivo. Uma journey que fala com endpoint REST é `api`; as demais
    dependem do DOM.
    """
    try:
        rel = definicao.module.replace(".", "/") + ".py"
        fonte = (BACKEND / rel).read_text(encoding="utf-8", errors="ignore")
    except Exception:  # noqa: BLE001
        return ""
    if "vidros_apifirst" in fonte or "_api(" in fonte or "_fetch_json" in fonte:
        return "api"
    if "page." in fonte or "querySelector" in fonte:
        return "dom"
    return ""


def sinais_medidos(definicao) -> dict:
    """Só o que o disco prova. O resto fica ausente, e ausente é não-provado."""
    pref = _prefixo(definicao.portal_key)
    tem_fixture = _tem_arquivo(FIXTURES, pref)
    tem_teste = _tem_arquivo(TESTES, pref)
    sinais = {}
    if tem_fixture:
        sinais["fixtures"] = True
    if tem_teste:
        sinais["testes_verdes"] = True
        # 🔴 "tem teste" NÃO é "tem caso negativo". Marcar os dois juntos
        # inflaria o score com uma prova que ninguém deu.
    caminho = _caminho_primario(definicao)
    if caminho:
        sinais["caminho_primario"] = caminho
    return sinais


def main() -> int:
    # `matriz_markdown` recebe os sinais POR CHAVE e faz a avaliação por dentro.
    # Montar as avaliações aqui e passá-las prontas duplicaria a lógica de
    # pontuação — e duas pontuações divergem no primeiro dia em que alguém
    # muda um peso e esquece a outra.
    sinais = {chave: sinais_medidos(d) for chave, d in JOURNEYS.items()}

    md = PR.matriz_markdown(sinais, gerado_em="2026-08-16")
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(md, encoding="utf-8")

    linhas = PR.matriz_linhas(sinais)
    print(f"gerado: {SAIDA.relative_to(RAIZ)}")
    print(f"  {len(linhas)} journeys")
    for r in sorted(linhas, key=lambda x: -x.get("score_bruto", 0))[:3]:
        print(f"  {r['chave']}: bruto {r.get('score_bruto')} / "
              f"operacional {r.get('score')} "
              f"({r.get('blocker') or 'sem blocker'})")
    print()
    print("Score baixo aqui NAO significa journey ruim: significa POUCA PROVA.")
    print("Nenhum arquivo no disco prova isolamento de tenant nem canario real.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
