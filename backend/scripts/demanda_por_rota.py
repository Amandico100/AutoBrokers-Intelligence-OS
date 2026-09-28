# -*- coding: utf-8 -*-
"""`demanda_por_rota.py` — QUANTAS conversas reais existem **POR ROTA**.

> ## Um número de demanda que serve para dez rotas não é a demanda de nenhuma delas.

```bash
# medir no banco e gravar o retrato datado (precisa de credencial)
cd backend && python scripts/demanda_por_rota.py --medir --gravar

# a via INDEPENDENTE, offline: contar as sessões do corpus versionado
cd backend && python scripts/demanda_por_rota.py --do-corpus

# as duas lado a lado -- é a LINHA DE CONTROLE da medição
cd backend && python scripts/demanda_por_rota.py --comparar
```

## 🔴 POR QUE ESTE ARQUIVO EXISTE — três defeitos na mesma coluna

📊 Medido em 27/09/2026, no HEAD `f9b7204`:

```
(a) A BUSCA É POR SERVIÇO, NÃO POR ROTA
    medir_rota.py:275  ->  d = demanda.get(n.rota.servico, 0)
    medir_rota.py:446  ->  demanda = {s: e for s, e, _c in PS.DEMANDA_MEDIDA}
    `("guincho", 72, 197)` é o total de SETE seguradoras. As dez linhas de
    guincho mostravam 72 -- e NENHUMA rota tem 72. Foi esta linha que fez o
    Founder perguntar "como pode ter 72 pedidos e não ter o corredor?".

(b) SINGULAR × PLURAL ZERA A BUSCA
    o playbook e o classificador escrevem `eletrodomesticos` e `vidros`;
    a tabela escreve `eletrodomestico` e `vidro`.
      demanda.get("eletrodomesticos") -> nada -> 0     (9 sessões medidas)
      demanda.get("vidros")           -> nada -> 0     (1 sessão medida)
      demanda.get("maquina_de_lavar") -> nada -> 0     (5 sessões, AUSENTE da tabela)
    ⇒ rotas COM demanda apareciam com ZERO, como se ninguém pedisse.
    🔴 CLAUDE.md §12.1: o nome errado é a CAUSA. Conserta-se o campo.

(c) O RETRATO É DE 21/08/2026
    `padroes_de_servico.py:843` diz isso no próprio comentário. Soma dos
    ESCOLHIDO = 160; o acervo etiquetado hoje tem 185 sessões.
    ⇒ re-medir, não só re-chavear.
```

## A FONTE, e por que é esta

`observed_events` — é o que a SPEC-119 §5 F5① manda. A sessão é a unidade:
**uma conversa do segurado com a URA da seguradora** conta 1, por mais telas
que tenha. A rota de uma sessão sai dos MESMOS motores que constroem o corpus,
nunca de string:

```
ramo     padroes_de_ramo.classificar_ramo(seg, pares)
serviço  padroes_de_servico.servico_da_sessao(seg, pares, playbook)
```

⚠️ **Medir com um motor e aplicar com outro é medir outra coisa** (CLAUDE.md
§9.4, o corolário do dialeto). É por isso que o serviço aqui sai do mesmo
`servico_da_sessao` que etiqueta o corpus: assim a chave da demanda **não pode**
divergir do nome que o playbook usa. Foi exatamente essa divergência que
produziu o defeito (b).

## 🔴 ZERO MEDIDO E ZERO NÃO MEDIDO NÃO SÃO A MESMA COISA

```
número      a rota TEM tantas conversas etiquetadas no acervo
—           o retrato NÃO cobre esta rota  (nunca 0, e NUNCA o número global)
```

E a coluna vizinha é obrigatória para quem lê: por `(seguradora, ramo)` o
retrato também guarda quantas sessões ficaram **sem etiqueta**. Uma rota com
`—` numa seguradora que tem 7 sessões sem etiqueta não é "ninguém pediu" —
é "não sabemos", e são coisas diferentes.

## A LINHA DE CONTROLE (CLAUDE.md §9.2)

`--comparar` mede a mesma coisa por dois caminhos independentes:

```
BANCO    observed_events, classificado agora
CORPUS   os arquivos versionados de tests/corpus/telas_reais/, contando
         session_id distintos por (seguradora, ramo, servico)
```

🔴 **O banco tem de ser ≥ o corpus em toda rota**, porque o corpus é um
recorte dele. Uma rota em que o corpus tenha MAIS sessões que o banco é prova
de que um dos dois caminhos está quebrado — e é isso que a comparação existe
para pegar. A diferença legítima é a cota por rota da geração do corpus.

⚠️ E o CONTROLE de que a medição rodou COM banco é
`regua_motor.controle_do_mascarador()` (8 marcas em 27/09/2026). Sem ele, uma
leitura sem credencial devolveria zero em tudo e o retrato sairia dizendo que
ninguém liga para seguradora nenhuma — com exit 0.
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import glob
import json
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: 🔴 Onde o retrato datado mora. O caminho é citado na aba do painel, então
#: mudá-lo exige `grep` do valor antigo (protocolo §0.4).
CAMINHO_DO_RETRATO = os.path.join(
    RAIZ, "docs", "canon", "reports", "DEMANDA-POR-ROTA.json")

CORPUS = os.path.join(BACKEND, "tests", "corpus", "telas_reais")

#: 🔴 O rótulo de "não medido". Nunca `0`, nunca o número global.
NAO_MEDIDO = "—"


def _commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=RAIZ,
            stderr=subprocess.DEVNULL).decode().strip()
    except Exception:  # noqa: BLE001
        return "?"


def chave(seguradora: str, ramo: str, servico: str) -> str:
    """A chave da rota. 🔴 Os TRÊS eixos — é o conserto do defeito (a)."""
    return f"{seguradora}/{ramo}/{servico}"


# ═════════════════════════════════════════════════════════════════════════════
# O RETRATO
# ═════════════════════════════════════════════════════════════════════════════
class Retrato:
    """O que foi medido, quando, com que comando, e por onde conferir.

    🔴 Um retrato sem data é exatamente a "informação antiga que confunde" que
    o Founder pediu para tirar da página (SPEC-119 §5 F5, gate G10).
    """

    def __init__(self, dados: Dict[str, Any]):
        self.dados = dados

    # ── o que a régua consome ────────────────────────────────────────────────
    def de(self, seguradora: str, ramo: str, servico: str) -> Optional[int]:
        """As sessões desta ROTA, ou `None` se o retrato não a cobre."""
        return self.dados.get("por_rota", {}).get(
            chave(seguradora, ramo, servico))

    def rotulo(self, seguradora: str, ramo: str, servico: str) -> str:
        """O que se IMPRIME. 🔴 `—` quando não há retrato para a rota."""
        v = self.de(seguradora, ramo, servico)
        return NAO_MEDIDO if v is None else str(v)

    def sem_etiqueta(self, seguradora: str, ramo: str) -> int:
        """Sessões de `(seguradora, ramo)` que o classificador não etiquetou.

        🔴 É a coluna que impede ler `—` como "ninguém pediu".
        """
        return int(self.dados.get("sem_etiqueta", {}).get(
            f"{seguradora}/{ramo}", 0))

    # ── proveniência, para a página ──────────────────────────────────────────
    @property
    def medido_em(self) -> str:
        return str(self.dados.get("medido_em", "?"))

    @property
    def fonte(self) -> str:
        return str(self.dados.get("fonte", "?"))

    @property
    def comando(self) -> str:
        return str(self.dados.get("comando", "?"))

    @property
    def carimbo(self) -> str:
        """Uma linha que a página pode imprimir inteira, com data e fonte."""
        return (f"📊 demanda medida em {self.medido_em} · fonte `{self.fonte}` · "
                f"`{self.comando}`")

    @property
    def rotas_sem_corredor(self) -> Dict[str, int]:
        """🔴 Serviços que o segurado PEDE e para os quais não há playbook.

        📊 `carro_reserva` em 27/09/2026: 126 telas no corpus, 8 sessões, e
        `grep -c carro_reserva app/services/corridor_playbooks.py` -> **0**.
        Um serviço com demanda e sem corredor não pode ficar invisível só
        porque a régua itera as rotas que EXISTEM.
        """
        return dict(self.dados.get("sem_corredor", {}))


def carregar(caminho: str = CAMINHO_DO_RETRATO) -> Optional[Retrato]:
    """O retrato gravado, ou `None`. ⚠️ Ausência NUNCA vira zero."""
    try:
        with open(caminho, encoding="utf-8") as fh:
            return Retrato(json.load(fh))
    except (OSError, ValueError):
        return None


def gravar(retrato: Retrato, caminho: str = CAMINHO_DO_RETRATO) -> str:
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as fh:
        json.dump(retrato.dados, fh, ensure_ascii=False, indent=1, sort_keys=True)
        fh.write("\n")
    return caminho


# ═════════════════════════════════════════════════════════════════════════════
# A VIA 1 — o BANCO
# ═════════════════════════════════════════════════════════════════════════════
def medir(seguradoras: Optional[List[str]] = None) -> Retrato:
    """Conta sessões DISTINTAS por rota em `observed_events`.

    🔴 O CONTROLE VEM PRIMEIRO: `controle_do_mascarador()` levanta se a
    medição estiver rodando sem banco. Um retrato de zeros com exit 0 é o
    pior resultado possível.
    """
    import padroes_de_ramo as PR          # noqa: E402
    import padroes_de_servico as PSV      # noqa: E402
    import regua_motor as M               # noqa: E402
    import zonas_do_acervo as Z           # noqa: E402
    from gerar_corpus_de_telas import RAMOS_EM_ESCOPO   # noqa: E402

    marcas = M.controle_do_mascarador()

    segs = seguradoras or M.seguradoras()
    por_rota: Dict[str, Set[Any]] = collections.defaultdict(set)
    sem_etiqueta: Dict[str, Set[Any]] = collections.defaultdict(set)
    fora_de_escopo: Dict[str, int] = collections.defaultdict(int)
    nao_decidiu: Dict[str, int] = collections.defaultdict(int)
    eventos = 0
    sessoes = 0

    for seg in segs:
        pb_por_ramo = {}
        for ramo in PR.ramos_de(seg):
            ref = M.resolve_playbook_ref(seg, ramo)
            pb_por_ramo[ramo] = M.get_playbook(ref) if ref else None

        por_sessao: Dict[Any, List[Dict[str, Any]]] = collections.defaultdict(list)
        for e in M.eventos_observados(seguradora=seg):
            por_sessao[e.get("session_id")].append(e)
            eventos += 1

        for sid, evs in por_sessao.items():
            sessoes += 1
            ordenados = sorted(evs, key=lambda x: x.get("wa_timestamp") or "")
            pares = [(x.get("direction"),
                      Z.norm_para_classificar(x.get("text") or ""))
                     for x in ordenados]
            ramo, _nivel = PR.classificar_ramo(seg, pares)
            if ramo in ("indefinido", "ambos", "sem_escolha"):
                nao_decidiu[seg] += 1
                continue
            if ramo not in RAMOS_EM_ESCOPO:
                fora_de_escopo[f"{seg}/{ramo}"] += 1
                continue
            servico, _nsrv = PSV.servico_da_sessao(
                seg, pares, pb_por_ramo.get(ramo))
            if not servico:
                sem_etiqueta[f"{seg}/{ramo}"].add(sid)
                continue
            por_rota[chave(seg, ramo, servico)].add(sid)

    # 🔴 Os serviços COM demanda e SEM corredor. `M.rotas()` só conhece o que
    #    tem playbook, então sem esta volta eles desapareceriam da página.
    declaradas = {chave(r.seguradora, r.ramo, r.servico) for r in M.rotas()}
    sem_corredor = {k: len(v) for k, v in por_rota.items() if k not in declaradas}

    agora = dt.datetime.now(dt.timezone.utc)
    return Retrato({
        "medido_em": agora.date().isoformat(),
        "medido_em_iso": agora.isoformat(timespec="seconds"),
        "commit": _commit(),
        "fonte": "observed_events",
        "comando": "cd backend && python scripts/demanda_por_rota.py --medir --gravar",
        "unidade": "sessões distintas (uma conversa do segurado com a URA = 1)",
        "controle": {"marcas_de_corretora": marcas},
        "acervo": {"sessoes": sessoes, "eventos": eventos,
                   "seguradoras": len(segs)},
        "por_rota": {k: len(v) for k, v in sorted(por_rota.items())},
        "sem_etiqueta": {k: len(v) for k, v in sorted(sem_etiqueta.items())},
        "fora_de_escopo": dict(sorted(fora_de_escopo.items())),
        "nao_decidiu": dict(sorted(nao_decidiu.items())),
        "sem_corredor": dict(sorted(sem_corredor.items())),
    })


# ═════════════════════════════════════════════════════════════════════════════
# A VIA 2 — o CORPUS versionado (offline, independente do banco)
# ═════════════════════════════════════════════════════════════════════════════
def do_corpus() -> Dict[str, int]:
    """Sessões distintas por rota, lidas dos arquivos versionados.

    🔴 É a via INDEPENDENTE da §5② do protocolo: o número publicado é
    reconferido por um caminho que não é o que o produziu.
    """
    por_rota: Dict[str, Set[str]] = collections.defaultdict(set)
    for caminho in sorted(glob.glob(os.path.join(CORPUS, "*.jsonl"))):
        base = os.path.basename(caminho)[: -len(".jsonl")]
        seg, _, ramo = base.partition("-")
        with open(caminho, encoding="utf-8") as fh:
            for linha in fh:
                linha = linha.strip()
                if not linha:
                    continue
                d = json.loads(linha)
                srv = d.get("servico")
                if not srv:
                    continue
                por_rota[chave(seg, ramo, srv)].add(d.get("session_id"))
    return {k: len(v) for k, v in sorted(por_rota.items())}


def comparar(retrato: Retrato) -> Tuple[str, bool]:
    """As duas vias lado a lado. 🔴 `banco >= corpus` em TODA rota."""
    banco = retrato.dados.get("por_rota", {})
    corpus = do_corpus()
    todas = sorted(set(banco) | set(corpus))
    L = ["=== A LINHA DE CONTROLE: duas vias, a mesma coisa ===",
         f"retrato de {retrato.medido_em} · fonte {retrato.fonte}", "",
         f"{'rota':44s} {'BANCO':>6s} {'CORPUS':>7s}  situação"]
    ok = True
    for k in todas:
        b = banco.get(k)
        c = corpus.get(k)
        if b is None:
            sit = "🔴 no CORPUS e NAO no banco — uma das vias esta quebrada"
            ok = False
        elif c is None:
            sit = "⚠️ so no banco (a rota nao entrou no corpus)"
        elif b < c:
            sit = f"🔴 banco < corpus por {c - b} — IMPOSSIVEL, o corpus e recorte"
            ok = False
        elif b == c:
            sit = "✅ igual"
        else:
            sit = f"⚠️ banco tem +{b - c} (cota da geracao do corpus)"
        L.append(f"{k:44s} {str(b if b is not None else '—'):>6s} "
                 f"{str(c if c is not None else '—'):>7s}  {sit}")
    L.append("")
    L.append(f"CONTROLE: {'✅ VERDE' if ok else '🔴 VERMELHO'} — "
             f"{len(todas)} rota(s) conferida(s)")
    return "\n".join(L), ok


def imprimir(retrato: Retrato) -> str:
    L = [f"=== DEMANDA POR ROTA — retrato de {retrato.medido_em} ===",
         retrato.carimbo,
         f"acervo: {retrato.dados['acervo']['sessoes']} sessões · "
         f"{retrato.dados['acervo']['eventos']} eventos · "
         f"controle marcas_de_corretora = "
         f"{retrato.dados['controle']['marcas_de_corretora']}", ""]
    L.append(f"{'rota':44s} {'sessões':>8s}")
    for k, v in sorted(retrato.dados["por_rota"].items(),
                       key=lambda kv: (-kv[1], kv[0])):
        L.append(f"{k:44s} {v:8d}")
    L.append("")
    L.append("🔴 SEM ETIQUETA — por (seguradora, ramo). Uma rota `—` aqui "
             "não é 'ninguém pediu', é 'não sabemos'")
    for k, v in sorted(retrato.dados["sem_etiqueta"].items(),
                       key=lambda kv: (-kv[1], kv[0])):
        L.append(f"  {k:30s} {v:4d}")
    if retrato.rotas_sem_corredor:
        L.append("")
        L.append("🔴 DEMANDA SEM CORREDOR — o segurado pede e não há playbook")
        for k, v in sorted(retrato.rotas_sem_corredor.items(),
                           key=lambda kv: (-kv[1], kv[0])):
            L.append(f"  {k:40s} {v:4d} sessão(ões)")
    return "\n".join(L)


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--medir", action="store_true", help="ler o banco")
    p.add_argument("--gravar", action="store_true",
                   help=f"gravar em {CAMINHO_DO_RETRATO}")
    p.add_argument("--do-corpus", action="store_true",
                   help="a via offline, independente do banco")
    p.add_argument("--comparar", action="store_true",
                   help="as duas vias lado a lado (linha de controle)")
    p.add_argument("--seguradora", action="append",
                   help="limitar a medição (padrão: todas)")
    a = p.parse_args(argv)

    if a.do_corpus:
        for k, v in sorted(do_corpus().items(), key=lambda kv: (-kv[1], kv[0])):
            print(f"{k:44s} {v:4d}")
        return 0

    if a.medir:
        r = medir(a.seguradora)
        print(imprimir(r))
        if a.gravar:
            print()
            print(f"gravado: {gravar(r)}")
        if a.comparar:
            print()
            texto, ok = comparar(r)
            print(texto)
            return 0 if ok else 1
        return 0

    r = carregar()
    if r is None:
        print(f"🔴 sem retrato em {CAMINHO_DO_RETRATO}. "
              f"Rode com `--medir --gravar` de dentro de `backend/`.",
              file=sys.stderr)
        return 2
    if a.comparar:
        texto, ok = comparar(r)
        print(texto)
        return 0 if ok else 1
    print(imprimir(r))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
