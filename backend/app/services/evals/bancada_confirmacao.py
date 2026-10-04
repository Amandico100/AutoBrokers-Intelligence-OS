# -*- coding: utf-8 -*-
"""SPEC-126 U2 (parte A) — a BANCADA DO "OK": o classificador da confirmação × o gabarito.

Mede, sobre `tests/corpus/bancada/confirmacao/casos.jsonl` (gabarito escrito ANTES de rodar):

    falso ok        gabarito ≠ ok  e  a decisão = ok      → META: 0 (SPEC-126 G2)
    ok aceito       gabarito = ok  e  a decisão = ok      → META: ≥ 95 % (no combinado)

para TRÊS decisões, lado a lado:
    regex        `insurer_dispatch_tool.confirmacao_comprovada` — o MOTOR de hoje, importado (§9.4)
    classificador `app.atendimento.confirmacao.classificar_confirmacao` — o MESMO prompt/leitura/
                 política de produção, com o braço da bancada injetado
    combinado    regex E classificador (`decisao_combinada`) — o portão da parte B

k tentativas por caso (padrão 3); concordância das k; latência p50/p90; timeouts; custo.

🔴 REUSA a bancada (`services/evals/bancada.py`): `Braco`, `resolver_padrao` (override da bancada),
   `construir_llm_padrao` (a fábrica do produto, ISOLADA: `service_type='bancada'`, `company_id`
   NULO, sem o relógio de produção), `_marcar_papel_no_ledger` (`details.papel='confirmacao'`),
   `Medidor` + `OrcamentoDoLedger` (teto por provedor LIDO DO LEDGER, relido a cada 10 reservas —
   a rodada PARA SOZINHA antes de estourar). Nenhum cliente novo (CLAUDE.md §5).

Uso (de backend/):
    python -m app.services.evals.bancada_confirmacao --so-regex                       # grátis
    python -m app.services.evals.bancada_confirmacao --braco duble:regex --braco duble:sempre_ok
    python -m app.services.evals.bancada_confirmacao --braco openai:<modelo>:medium --k 3 \
        --teto-provedor 2.85 --ledger-desde 2026-10-02T18:50:00+00:00 --saida <scratch>/conf.json
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import hashlib
import json
import re
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from app.atendimento import confirmacao as C
from app.services.evals import bancada as B

PAPEL = C.PAPEL
CORPUS = B.CORPUS_DIR / "confirmacao" / "casos.jsonl"
GABARITOS = C.LEITURAS

# ═════════════════════════════════════════════════════════════════════════════
# O CORPUS e o guarda de PII
# ═════════════════════════════════════════════════════════════════════════════
#: constante_justificada: os primeiros nomes mais comuns do Brasil (IBGE, censo 2010 — o topo das
#: duas listas) + apelidos. O corpus é MASCARADO/sintético: nenhum nome de pessoa entra (CLAUDE.md
#: §13.9; o card da 126: "nunca imprimir nome de pessoa").
NOMES_COMUNS = frozenset("""
maria jose ana joao antonio francisco carlos paulo pedro lucas luiz marcos luis gabriel rafael daniel
marcelo bruno eduardo felipe raimundo rodrigo manoel mateus andre fernando fabio leonardo gustavo
guilherme leandro tiago anderson ricardo marcio jorge alexandre roberto edson diego vitor sergio claudio
matheus thiago geraldo adriano luciano julio renato alex vinicius rogerio samuel ronaldo mario flavio
igor douglas davi manuel jefferson cicero victor miguel robson mauricio danilo henrique caio reginaldo
joaquim benedito gilberto alan nelson cristiano elias wilson valdir emerson luan david renan severino
fabricio mauro jonas gilmar jean fabiano wesley diogo adilson jair alessandro everton osvaldo gilson
willian joel silvio helio maicon reinaldo pablo artur arthur vagner valter celso ivan cleiton vanderlei
vicente milton domingos wagner sandro moises edilson ademir adao evandro cesar valmir murilo juliano
francisca antonia adriana juliana marcia fernanda patricia aline sandra camila amanda bruna jessica
leticia julia luciana vanessa mariana gabriela vitoria larissa claudia beatriz luana sonia renata
eliane josefa simone natalia cristiane carla debora rosangela jaqueline daniela aparecida marlene
terezinha raimunda andreia fabiana lucia raquel angela rafaela joana luzia elaine daiane tatiane
cristina carolina regina rita vera
ze zezinho tiao chico juca nando dudu
""".split())

#: dígitos em sequência ≥ 4 = CPF, telefone, apólice, CEP, placa antiga — nunca no corpus
_RX_DIGITOS = re.compile(r"\d{4,}")


def _sem_acento(s: Any) -> str:
    return unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()


def achados_de_pii(texto: Any) -> List[str]:
    """O que no texto parece PII: sequência de ≥ 4 dígitos ou um nome comum. **PURA.**"""
    t = str(texto or "")
    achados = [f"digitos:{len(m.group(0))}" for m in _RX_DIGITOS.finditer(t)]
    achados += [f"nome:{w}" for w in re.findall(r"[a-z]+", _sem_acento(t)) if w in NOMES_COMUNS]
    return achados


def pii_do_caso(caso: dict) -> List[str]:
    """Todo texto do caso (pergunta, falas, pedido) passado pelo guarda."""
    textos = [caso.get("pergunta")] + list(caso.get("falas") or [])
    textos += [v for v in (caso.get("pedido") or {}).values()]
    return [a for t in textos for a in achados_de_pii(t)]


def carregar_casos(filtro: Optional[str] = None, *, caminho: Optional[Path] = None) -> List[dict]:
    """Os casos do corpus; `filtro` = trechos do id ou da armadilha, separados por vírgula."""
    arq = Path(caminho or CORPUS)
    trechos = [t.strip() for t in str(filtro or "").split(",") if t.strip()]
    casos = []
    for linha in arq.read_text(encoding="utf-8").splitlines():
        if not linha.strip():
            continue
        caso = json.loads(linha)
        if trechos and not any(t in caso["id"] or t == caso.get("armadilha") for t in trechos):
            continue
        casos.append(caso)
    return casos


def sha_do_gabarito(caminho: Optional[Path] = None) -> str:
    """O hash do corpus rodado — o juiz confere que é o do commit ANTERIOR à rodada."""
    return hashlib.sha256(Path(caminho or CORPUS).read_bytes()).hexdigest()[:16]


# ═════════════════════════════════════════════════════════════════════════════
# AS TRÊS DECISÕES
# ═════════════════════════════════════════════════════════════════════════════
def regex_aceita(caso: dict) -> bool:
    """A regex de HOJE pelo motor do portão — `confirmacao_comprovada`, nunca reimplementada."""
    from app.agents.tools.insurer_dispatch_tool import confirmacao_comprovada

    falas = [("agente", caso["pergunta"])] + [("segurado", f) for f in caso.get("falas") or []]
    return bool(confirmacao_comprovada(falas, caso.get("pedido"))["comprovada"])


def decisao_combinada(regex_ok: bool, leitura: str) -> bool:
    """🔴 O portão da SPEC-126 §3.1 (2): só aciona se a regex E o classificador disserem ok — pela
    regra do PRÓPRIO portão (`insurer_dispatch_tool.decisao_do_portao`), nunca reimplementada (§9.4)."""
    from app.agents.tools.insurer_dispatch_tool import decisao_do_portao

    return bool(decisao_do_portao({"comprovada": bool(regex_ok)}, {"leitura": leitura})["comprovada"])


# ═════════════════════════════════════════════════════════════════════════════
# OS DUBLÊS (linha de controle sem custo — CLAUDE.md §9.2)
# ═════════════════════════════════════════════════════════════════════════════
_RX_BLOCO = re.compile(r"<<<(.*?)>>>", re.S)


def _pergunta_e_falas(mensagens: list) -> tuple:
    texto = str(getattr(mensagens[-1], "content", "") or "")
    blocos = _RX_BLOCO.findall(texto)
    return (blocos[0] if blocos else ""), blocos[1:]


class DubleDaConfirmacao:
    """Um classificador de mentira: `decidir(pergunta, falas) -> leitura`. Responde no formato do
    contrato (`{"leitura","trecho"}`), com o trecho = a 1ª fala (o ok é ancorado nas falas)."""

    def __init__(self, decidir: Callable[[str, List[str]], str], nome: str = "duble"):
        self.decidir = decidir
        self.model_name = nome

    async def ainvoke(self, mensagens, config=None, **_k):
        from langchain_core.messages import AIMessage

        pergunta, falas = _pergunta_e_falas(mensagens)
        leitura = self.decidir(pergunta, falas)
        return AIMessage(content=json.dumps({"leitura": leitura, "trecho": falas[0] if falas else ""},
                                            ensure_ascii=False),
                         usage_metadata={"input_tokens": 0, "output_tokens": 0, "total_tokens": 0})


def _pela_regex_da_fala(pergunta: str, falas: List[str]) -> str:
    from app.agents.tools.insurer_dispatch_tool import _resposta_do_segurado

    leituras = [_resposta_do_segurado(f, pergunta) for f in falas]
    if "nao" in leituras:
        return "nao"
    return "ok" if "sim" in leituras else "outra_coisa"


@contextlib.contextmanager
def classificador_duble_na_borda(decidir: Optional[Callable[[str, List[str]], str]] = None):
    """Para TESTES: troca a BORDA do classificador — a chamada ao modelo do papel `confirmacao`
    (`llm_factory.invocar_com_reserva`) — por um `DubleDaConfirmacao`. Os outros papéis seguem a função
    original; o prompt, a leitura do JSON, o trecho e o portão continuam os de produção (§9.4).

    Padrão = diz OK para TUDO: num teste que espera "não acionou", quem decide continua sendo a regex.
    Devolve a lista das chamadas (uma por tentativa de acionamento que a regex deixou passar)."""
    from app.factories import llm_factory as LF

    original = LF.invocar_com_reserva
    duble = DubleDaConfirmacao(decidir or (lambda _p, _f: "ok"), "duble:borda")
    chamadas: List[dict] = []

    async def _borda(papel, mensagens, **kw):
        if papel != PAPEL:
            return await original(papel, mensagens, **kw)
        chamadas.append({"papel": papel, **kw})
        return await duble.ainvoke(mensagens)

    LF.invocar_com_reserva = _borda
    try:
        yield chamadas
    finally:
        LF.invocar_com_reserva = original


DUBLES: Dict[str, Callable[[], DubleDaConfirmacao]] = {
    # o que a regex de hoje diria fala a fala — a linha de CONTROLE do pipeline
    "regex": lambda: DubleDaConfirmacao(_pela_regex_da_fala, "duble:regex"),
    # o BURRO: diz ok para tudo — o falso ok TEM de aparecer no classificador
    "sempre_ok": lambda: DubleDaConfirmacao(lambda p, f: "ok", "duble:sempre_ok"),
    # o MUDO: nunca ok — o ok aceito TEM de ir a zero
    "nunca_ok": lambda: DubleDaConfirmacao(lambda p, f: "outra_coisa", "duble:nunca_ok"),
}


# ═════════════════════════════════════════════════════════════════════════════
# A RODADA
# ═════════════════════════════════════════════════════════════════════════════
async def rodar(casos: List[dict], llm: Any, *, k: int = 3, timeout_s: float = C.TETO_DA_CHAMADA_S,
                paralelo: int = 4, custo: Optional[Callable[[], float]] = None) -> dict:
    """Roda o classificador k vezes por caso. Para SOZINHA no teto (`TetoDeGastoAtingido` dentro
    do `Medidor` vira `erro:TetoDeGastoAtingido` no classificador — a tentativa é descartada).
    Devolve `{"resultados": [...], "parada": str|None}`."""
    sem = asyncio.Semaphore(max(1, int(paralelo)))
    estado: Dict[str, Any] = {"parada": None}
    regex = {c["id"]: regex_aceita(c) for c in casos}

    async def uma(caso: dict, t: int) -> Optional[dict]:
        async with sem:
            if estado["parada"]:
                return None
            inicio = time.perf_counter()
            r = await C.classificar_confirmacao(caso["pergunta"], caso.get("falas") or [],
                                                company_id=None, llm=llm, timeout_s=timeout_s)
            ms = int((time.perf_counter() - inicio) * 1000)
            if r["motivo"] == "erro:TetoDeGastoAtingido":
                estado["parada"] = estado["parada"] or "teto_usd"
                return None
            return {"id": caso["id"], "tentativa": t, "gabarito": caso["gabarito"],
                    "armadilha": caso.get("armadilha"), "origem": caso.get("origem"),
                    "leitura": r["leitura"], "motivo": r["motivo"], "trecho": r["trecho"],
                    "regex_ok": regex[caso["id"]],
                    "combinado_ok": decisao_combinada(regex[caso["id"]], r["leitura"]),
                    "latencia_ms": ms}

    # o custo é o do MEDIDOR, antes × depois da rodada inteira (em paralelo, o delta por
    # tentativa misturaria as chamadas umas das outras)
    c0 = custo() if custo else 0.0
    tarefas = [uma(c, t) for t in range(1, int(k) + 1) for c in casos]
    resultados = [r for r in await asyncio.gather(*tarefas) if r is not None]
    resultados.sort(key=lambda r: (r["id"], r["tentativa"]))
    gasto = round((custo() if custo else 0.0) - c0, 6)
    return {"resultados": resultados, "parada": estado["parada"], "custo_usd": gasto}


def _pct(a: int, b: int) -> Optional[float]:
    return round(100.0 * a / b, 1) if b else None


def _percentil(valores: List[int], p: float) -> Optional[int]:
    if not valores:
        return None
    v = sorted(valores)
    return v[min(len(v) - 1, int(round(p * (len(v) - 1))))]


def _decisoes(r: dict) -> Dict[str, bool]:
    return {"regex": bool(r["regex_ok"]), "classificador": r["leitura"] == "ok",
            "combinado": bool(r["combinado_ok"])}


def calcular_metricas(resultados: List[dict]) -> dict:
    """Falso ok e ok aceito por decisão (regex · classificador · combinado), por TENTATIVA e por
    CASO (um caso só é seguro se NENHUMA das k tentativas deu falso ok). **PURA.**"""
    m: Dict[str, Any] = {"tentativas": len(resultados)}
    por_caso: Dict[str, List[dict]] = {}
    for r in resultados:
        por_caso.setdefault(r["id"], []).append(r)
    ok_t = [r for r in resultados if r["gabarito"] == "ok"]
    nok_t = [r for r in resultados if r["gabarito"] != "ok"]
    casos_ok = {i: rs for i, rs in por_caso.items() if rs[0]["gabarito"] == "ok"}
    casos_nok = {i: rs for i, rs in por_caso.items() if rs[0]["gabarito"] != "ok"}
    for d in ("regex", "classificador", "combinado"):
        falsos = [r for r in nok_t if _decisoes(r)[d]]
        aceitos = [r for r in ok_t if _decisoes(r)[d]]
        casos_falsos = sorted(i for i, rs in casos_nok.items() if any(_decisoes(r)[d] for r in rs))
        casos_aceitos_em_todas = [i for i, rs in casos_ok.items() if all(_decisoes(r)[d] for r in rs)]
        m[d] = {
            "falso_ok_tentativas": len(falsos), "nao_ok_tentativas": len(nok_t),
            "falso_ok_casos": len(casos_falsos), "nao_ok_casos": len(casos_nok),
            "falso_ok_ids": casos_falsos,
            "falso_ok_armadilhas": sorted({r["armadilha"] for r in falsos}),
            "ok_aceito_tentativas": len(aceitos), "ok_tentativas": len(ok_t),
            "ok_aceito_pct": _pct(len(aceitos), len(ok_t)),
            "ok_aceito_em_todas_k_casos": len(casos_aceitos_em_todas), "ok_casos": len(casos_ok),
            "ok_recusado_ids": sorted(i for i in casos_ok if i not in casos_aceitos_em_todas),
        }
    certas = sum(1 for r in resultados if r["leitura"] == r["gabarito"])
    m["classificador"]["acerto_3_classes_pct"] = _pct(certas, len(resultados))
    m["classificador"]["concordancia_k_pct"] = _pct(
        sum(1 for rs in por_caso.values() if len({r["leitura"] for r in rs}) == 1), len(por_caso))
    motivos: Dict[str, int] = {}
    for r in resultados:
        chave = r["motivo"].split(":")[0] if r["motivo"].startswith(("erro:", "saida_invalida:")) \
            else r["motivo"]
        motivos[chave] = motivos.get(chave, 0) + 1
    m["motivos"] = motivos
    lat = [r["latencia_ms"] for r in resultados if r["motivo"] == "modelo"]
    m["latencia_ms"] = {"p50": _percentil(lat, 0.5), "p90": _percentil(lat, 0.9),
                        "max": max(lat) if lat else None}
    return m


def metricas_so_da_regex(casos: List[dict]) -> dict:
    """A regex de hoje sozinha, SEM chamar modelo (grátis): o ponto de partida da parte B."""
    rs = [{"id": c["id"], "tentativa": 1, "gabarito": c["gabarito"], "armadilha": c.get("armadilha"),
           "leitura": "outra_coisa", "motivo": "sem_modelo", "trecho": "", "regex_ok": regex_aceita(c),
           "combinado_ok": False, "latencia_ms": 0} for c in casos]
    return calcular_metricas(rs)["regex"]


def tabela(rotulo: str, m: dict) -> str:
    linhas = [f"── {rotulo} · {m['tentativas']} tentativas ──",
              f"{'decisão':<14} {'falso ok (tent.)':>17} {'falso ok (casos)':>17} {'ok aceito (tent.)':>19} "
              f"{'ok em todas k':>14}"]
    for d in ("regex", "classificador", "combinado"):
        x = m[d]
        linhas.append(f"{d:<14} {x['falso_ok_tentativas']:>7}/{x['nao_ok_tentativas']:<9} "
                      f"{x['falso_ok_casos']:>7}/{x['nao_ok_casos']:<9} "
                      f"{x['ok_aceito_tentativas']:>6}/{x['ok_tentativas']:<4} ({x['ok_aceito_pct']}%) "
                      f"{x['ok_aceito_em_todas_k_casos']:>6}/{x['ok_casos']}")
    cl = m["classificador"]
    linhas.append(f"classificador: acerto 3 classes {cl['acerto_3_classes_pct']}% · concordância das k "
                  f"{cl['concordancia_k_pct']}% · motivos {m['motivos']}")
    linhas.append(f"latência (só respostas do modelo) p50 {m['latencia_ms']['p50']} ms · p90 "
                  f"{m['latencia_ms']['p90']} ms · máx {m['latencia_ms']['max']} ms")
    for d in ("classificador", "combinado"):
        if m[d]["falso_ok_ids"]:
            linhas.append(f"🔴 falso ok {d}: {m[d]['falso_ok_ids']} · armadilhas {m[d]['falso_ok_armadilhas']}")
    return "\n".join(linhas)


# ═════════════════════════════════════════════════════════════════════════════
# O BRAÇO e a linha de comando
# ═════════════════════════════════════════════════════════════════════════════
def construir_braco(rotulo: str, *, orcamento: Optional[B.Orcamento] = None,
                    max_saida: Optional[int] = None) -> tuple:
    """`(braco, llm_medido)`. Dublê → `DUBLES[nome]`. Real → a fábrica do produto, isolada
    (`construir_llm_padrao`), com `details.papel='confirmacao'` no ledger e o `Medidor` (teto).

    `max_saida`: o teto de saída com que o braço é CONSTRUÍDO **e** o que a reserva do teto em US$ usa (os
    dois juntos — a reserva nunca fica abaixo do que a chamada pode gastar). Sem ele, `MAX_TOKENS_DA_BANCADA`
    (8192): 📊 04/10, numa Sonnet 5.5 isso reserva US$ 0,08 por chamada e um teto de US$ 0,05 não deixava
    rodar NENHUMA (a resposta do classificador mede ~60 tokens de saída)."""
    braco = B.Braco.de(rotulo)
    if braco.e_duble:
        if braco.model not in DUBLES:
            raise ValueError(f"dublê desconhecido {braco.model!r} (use {sorted(DUBLES)})")
        return braco, DUBLES[braco.model]()
    preco = B.preco_do_catalogo(braco)
    if preco is None:
        raise B.SemPrecoConhecido(f"{braco.rotulo}: sem preço no catálogo — a bancada não inventa preço")
    resolvido = B.resolver_padrao(PAPEL, override=braco.override())
    teto_saida = int(max_saida or B.MAX_TOKENS_DA_BANCADA)
    if teto_saida == B.MAX_TOKENS_DA_BANCADA:
        base = B.construir_llm_padrao(resolvido)
    else:  # a MESMA fábrica e o mesmo isolamento de `construir_llm_padrao`, só com o teto de saída menor
        from app.factories.llm_factory import LLMFactory

        base = B.isolar_do_produto(LLMFactory.criar_de_resolvido(
            resolvido, callbacks=[], company_id=None, agent_id=None,
            service_type=B.SERVICE_TYPE_DA_BANCADA, max_tokens=teto_saida))
    llm = B._marcar_papel_no_ledger(base, PAPEL)
    return braco, B.Medidor(llm, preco=preco, orcamento=orcamento or B.Orcamento(B.teto_padrao()),
                            max_output=teto_saida)


def _orcamento_do_ledger(provedor: str, teto: float, desde: str, ledger_papel: Optional[str]):
    if ledger_papel:
        from app.core.database import get_supabase_client

        cli = get_supabase_client()
        return B.OrcamentoDoLedger(provedor, teto, desde,
                                   ler=lambda p, d: B.gasto_do_ledger_do_papel(p, d, ledger_papel, cliente=cli))
    return B.OrcamentoDoLedger(provedor, teto, desde)


def rodar_pela_linha_de_comando(*, bracos: List[str], k: int = 3, casos: Optional[str] = None,
                                teto_provedor: Optional[float] = None, ledger_desde: Optional[str] = None,
                                ledger_papel: Optional[str] = None, saida: Optional[str] = None,
                                por_caso: bool = False, timeout_s: float = C.TETO_DA_CHAMADA_S,
                                paralelo: int = 4, so_regex: bool = False,
                                max_saida: Optional[int] = None) -> int:
    lista = carregar_casos(casos)
    sujos = {c["id"]: pii_do_caso(c) for c in lista if pii_do_caso(c)}
    if sujos:
        print(f"⛔ o corpus tem PII — nada roda: {sujos}")
        return 2
    print(f"corpus {CORPUS.name} sha {sha_do_gabarito()} · {len(lista)} casos "
          f"(ok {sum(c['gabarito'] == 'ok' for c in lista)} · não-ok {sum(c['gabarito'] != 'ok' for c in lista)})")
    if so_regex:
        x = metricas_so_da_regex(lista)
        print(f"regex de hoje: falso ok {x['falso_ok_casos']}/{x['nao_ok_casos']} {x['falso_ok_ids']} "
              f"{x['falso_ok_armadilhas']} · ok aceito {x['ok_aceito_tentativas']}/{x['ok_tentativas']} "
              f"· ok recusado {x['ok_recusado_ids']}")
        return 0
    if not bracos:
        print("⛔ --braco é obrigatório (ou --so-regex)")
        return 2
    reais = [b for b in bracos if not B.Braco.de(b).e_duble]
    if reais and (teto_provedor is None or not ledger_desde):
        print("⛔ braço real exige --teto-provedor e --ledger-desde (o teto é lido do LEDGER)")
        return 2
    saida_json: Dict[str, Any] = {"papel": PAPEL, "corpus_sha": sha_do_gabarito(), "k": k,
                                  "timeout_s": timeout_s, "commit": B._commit(), "bracos": {}}
    codigo = 0
    for rotulo in bracos:
        orc = None
        if not B.Braco.de(rotulo).e_duble:
            orc = _orcamento_do_ledger(B.Braco.de(rotulo).provider, teto_provedor, ledger_desde, ledger_papel)
            print(f"ledger {B.Braco.de(rotulo).provider} desde {ledger_desde}: US$ {orc.inicial:.4f} · "
                  f"teto {teto_provedor:.2f} · resta {orc.teto_usd:.4f}")
            if orc.teto_usd <= 0:
                print("⛔ teto já atingido no ledger — nada roda")
                return 2
        braco, llm = construir_braco(rotulo, orcamento=orc, max_saida=max_saida)
        custo = (lambda l=llm: float(l.estado["custo"])) if isinstance(llm, B.Medidor) else None
        rod = asyncio.run(rodar(lista, llm, k=k, timeout_s=timeout_s, paralelo=paralelo, custo=custo))
        m = calcular_metricas(rod["resultados"])
        print(tabela(braco.rotulo, m) + f"\ncusto da rodada (Medidor): US$ {rod['custo_usd']:.5f}"
              + (f"\n⛔ PAROU: {rod['parada']}" if rod["parada"] else ""))
        if por_caso:
            for r in rod["resultados"]:
                print(f"  {r['id']} t{r['tentativa']} gab={r['gabarito']:<11} leu={r['leitura']:<11} "
                      f"regex={'ok' if r['regex_ok'] else '--'} comb={'OK' if r['combinado_ok'] else '--'} "
                      f"{r['latencia_ms']} ms {r['motivo']} · {r['armadilha']}")
        saida_json["bracos"][braco.rotulo] = {"metricas": m, "parada": rod["parada"],
                                              "custo_usd": rod["custo_usd"],
                                              "resultados": rod["resultados"]}
        if rod["parada"]:
            codigo = 2
    if saida:
        Path(saida).write_text(json.dumps(saida_json, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"relatório: {saida}")
    return codigo


import app as _pacote_app  # noqa: E402

#: A raiz de `backend/` sai do PACOTE `app`, não de contar níveis a partir deste arquivo — o mesmo
#: desenho de `bancada.CORPUS_DIR` (guarda `test_o_vocabulario_viaja_na_imagem`: `parents[n]` de
#: cabeça quebra quando o arquivo muda de lugar). Só serve ao `.env` da execução local da bancada.
_BACKEND = Path(_pacote_app.__file__).resolve().parent.parent


def carregar_env(caminho: Optional[Path] = None) -> bool:
    """O `.env` do backend, como `scripts/bancada.py` faz. 📊 a 1ª rodada da U2a por `python -m` morreu com
    `OPENAI_API_KEY ausente`: o `-m` não passa pelo script que o carrega. `override=False`: o ambiente de
    quem chama vence. ⛔ Nenhuma chave é impressa."""
    try:
        from dotenv import load_dotenv
    except ImportError:  # pragma: no cover
        return False
    return bool(load_dotenv(str(caminho or (_BACKEND / ".env")), override=False))


def main(argv: Optional[List[str]] = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    carregar_env()
    p = argparse.ArgumentParser(description="SPEC-126 U2a — a bancada do 'ok' (classificador × gabarito)")
    p.add_argument("--braco", action="append", default=[], help="provider:model[:effort] ou duble:<regex|sempre_ok|nunca_ok>")
    p.add_argument("--k", type=int, default=3)
    p.add_argument("--casos", default=None, help="trechos do id ou nome da armadilha, separados por vírgula")
    p.add_argument("--teto-provedor", type=float, default=None, help="US$ ACUMULADO do provedor, lido do ledger")
    p.add_argument("--ledger-desde", default=None, help="início da conta do ledger (ISO 8601)")
    p.add_argument("--ledger-papel", default=None, help="conta só as linhas da bancada com details.papel = este")
    p.add_argument("--saida", default=None, help="JSON local com as tentativas e as métricas")
    p.add_argument("--por-caso", action="store_true")
    p.add_argument("--timeout-s", type=float, default=C.TETO_DA_CHAMADA_S, help="padrão: o de produção")
    p.add_argument("--paralelo", type=int, default=4)
    p.add_argument("--so-regex", action="store_true", help="só a regex de hoje, sem modelo (grátis)")
    p.add_argument("--max-saida", type=int, default=None,
                   help="teto de saída do braço E da reserva do teto em US$ (padrão: MAX_TOKENS_DA_BANCADA)")
    a = p.parse_args(argv)
    return rodar_pela_linha_de_comando(
        bracos=a.braco, k=a.k, casos=a.casos, teto_provedor=a.teto_provedor, ledger_desde=a.ledger_desde,
        ledger_papel=a.ledger_papel, saida=a.saida, por_caso=a.por_caso, timeout_s=a.timeout_s,
        paralelo=a.paralelo, so_regex=a.so_regex, max_saida=a.max_saida)


if __name__ == "__main__":
    raise SystemExit(main())
