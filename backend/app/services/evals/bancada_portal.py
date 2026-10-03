# -*- coding: utf-8 -*-
"""SPEC-127 P5 — a BANCADA DO DEDUZIR DO PORTAL: o destravador do portal × o gabarito da atendente.

O FIO, elo a elo (nada reimplementado — o motor é o do produto):

    `tests/corpus/bancada/portal/casos.jsonl` (paradas REAIS dos HAR: a lista do portal + a escolha da
      atendente = o gabarito, escrito ANTES; as falas do segurado sintéticas e sem PII)
      → `evidencia_do_caso`: a evidence que o worker grava (stage, opções, TELA — `vidros_estado.tela_da_parada`,
        a continuação `responder:<slot>`)
      → `destravador.destravar_parada_do_portal` (o MOTOR do produto, §9.4) com o braço INJETADO
        (`ModeloInjetado`) e a 2ª opinião de OUTRO provedor; a dedução LIGADA só aqui (`calibrando`)
      → o veredito contra o gabarito (`julgar`) + a LINHA DE CONTROLE: "a 1ª opção da lista"
      → `bancada.resumo_da_calibracao` / `decidir_religar` / `tabela_da_calibracao` (a MESMA régua da
        SPEC-126 U6: `destravador.prova_de_calibracao` — n ≥ 10, ≥ 90 %, Wilson ≥ 70 %, controle batido)
      → `sql_de_religar_o_portal`: o upsert por corretora × seguradora × `vidros` (o gerente aplica).

⛔ Sem a prova, a autonomia do DEDUZIR do portal continua 0 (o padrão de `cerebro_modos`).
⛔ Nenhum banco: o diário é dublê; a conversa e a memória da corretora, vazias (o caso traz o que importa).

Uso (de backend/):
    python -m app.services.evals.bancada_portal --so-corpus                              # grátis
    python -m app.services.evals.bancada_portal --braco duble:primeira --braco duble:perfeito   # grátis
    python -m app.services.evals.bancada_portal --braco openai:gpt-6.1-sol:high \\
        --segunda anthropic:claude-sonnet-5-5 --k 2 --tipos peca,causa,lataria,questionario \\
        --teto-provedor 4.50 --ledger-desde 2026-10-02T18:50:00+00:00 --saida <scratch>/portal.json
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from app.services.evals import bancada as B
from app.services.evals import dubles as D

PAPEL = "destravador"
PAPEL_SEGUNDA = "destravador_segunda"
CORPUS = B.CORPUS_DIR / "portal" / "casos.jsonl"
TIPOS = ("peca", "causa", "lataria", "questionario", "cidade")
#: 💭 corretora fictícia da bancada (§13.9: nenhum id real; o diário é dublê)
EMPRESA_DA_BANCADA = "bbbbbbbb-0000-4000-8000-00000000b127"
_RX_SEQ = re.compile(r"\d{4,}")


# ═════════════════════════════════════════════════════════════════════════════
# O CORPUS
# ═════════════════════════════════════════════════════════════════════════════
def carregar_casos(filtro: Optional[str] = None, *, tipos: Optional[List[str]] = None,
                   caminho: Optional[Path] = None) -> List[dict]:
    """Os casos; `filtro` = trechos do id (vírgula); `tipos` = os tipos de parada a rodar."""
    trechos = [t.strip() for t in str(filtro or "").split(",") if t.strip()]
    casos = []
    for linha in Path(caminho or CORPUS).read_text(encoding="utf-8").splitlines():
        if not linha.strip():
            continue
        c = json.loads(linha)
        if trechos and not any(t in c["id"] for t in trechos):
            continue
        if tipos and c.get("tipo") not in tipos:
            continue
        casos.append(c)
    return casos


def sha_do_gabarito(caminho: Optional[Path] = None) -> str:
    """O hash do corpus rodado — o juiz confere que é o do commit ANTERIOR à rodada."""
    return hashlib.sha256(Path(caminho or CORPUS).read_bytes()).hexdigest()[:16]


def pii_do_caso(caso: dict) -> List[str]:
    """O que o SEGURADO diz no caso (as falas sintéticas) passado pelo guarda da bancada do ok. As listas
    do portal (peças, causas, cidades de uma UF) são domínio — não passam (uma cidade "Antônio Carlos" não
    é uma pessoa)."""
    from app.services.evals.bancada_confirmacao import achados_de_pii

    dano = (caso.get("pedido") or {}).get("dano") or {}
    textos = [dano.get("peca"), dano.get("como"), dano.get("descricao"), *(dano.get("pecas_lataria") or []),
              *[str(v) for v in ((caso.get("pedido") or {}).get("especificos") or {}).values()]]
    return [a for t in textos for a in achados_de_pii(t)]


def contagem(casos: List[dict]) -> Dict[str, Dict[str, int]]:
    """n por seguradora × tipo (e quantos o gabarito manda RESPONDER) — o que o relatório declara."""
    out: Dict[str, Dict[str, int]] = {}
    for c in casos:
        m = out.setdefault(c["seguradora"], {})
        m[c["tipo"]] = m.get(c["tipo"], 0) + 1
        if c["gabarito"]["acao"] == "RESPONDER":
            m["responder"] = m.get("responder", 0) + 1
    return out


# ═════════════════════════════════════════════════════════════════════════════
# O CASO → a evidence do worker; o veredito; o controle
# ═════════════════════════════════════════════════════════════════════════════
def evidencia_do_caso(caso: dict) -> dict:
    """A evidence que o worker grava para esta parada (o formato de `vidros_apifirst._parar` +
    `worker._augment_hitl_evidence`), com a TELA (P8) pela MESMA função do worker."""
    from portal_worker.journeys import vidros_estado as ST

    p = caso["parada"]
    etapa, acao = ST.etapa_da_parada(p["stage"])
    acao = f"responder:{p['slot']}" if acao.startswith("responder") else acao
    return {"stage": p["stage"], "opcoes": list(p.get("opcoes") or []), "pergunta": p.get("pergunta") or "",
            "tela_da_parada": ST.tela_da_parada(p["stage"], opcoes=p.get("opcoes"), pergunta=p.get("pergunta")),
            "continuacao": {"possivel": True, "acao_esperada": acao, "etapa": etapa, "sessao_guardada": True},
            "message": "o portal parou o pedido (bancada)"}


def _n(s: Any) -> str:
    from app.services.destravador import _n as norm

    return norm(s)


def controle_primeira_opcao(caso: dict) -> bool:
    """🔴 A LINHA DE CONTROLE (CLAUDE.md §9.2): "a atendente escolheu a 1ª opção da lista" acertaria? O
    modelo tem de bater isto (no portal, o equivalente do "tecla 1" da URA)."""
    gab = caso["gabarito"]
    opcoes = caso["parada"].get("opcoes") or []
    return gab["acao"] == "RESPONDER" and bool(opcoes) and _n(opcoes[0]) == _n(gab["resposta"])


def julgar(caso: dict, d: dict) -> dict:
    """O veredito de UMA tentativa contra o gabarito. `CERTO`: respondeu a opção da atendente (ou, quando o
    gabarito é PERGUNTAR, não respondeu nada). `proposta_certa`: o que o MODELO propôs (antes da política)."""
    gab = caso["gabarito"]
    respondeu = d.get("acao") == "RESPONDER"
    if gab["acao"] == "RESPONDER":
        certo = respondeu and _n(d.get("valor")) == _n(gab["resposta"])
        proposta = _n(d.get("valor_do_modelo") or "") == _n(gab["resposta"])
        classe = "CERTO" if certo else ("ERRADO" if respondeu else "NAO_AGIU")
    else:
        certo = not respondeu
        proposta = d.get("acao_do_modelo") != "RESPONDER"
        classe = "CERTO" if certo else "GRAVE"
    return {"classe": classe, "proposta_certa": bool(proposta)}


# ═════════════════════════════════════════════════════════════════════════════
# O MOTOR — o destravador do produto, com o braço injetado
# ═════════════════════════════════════════════════════════════════════════════
#: as bordas trocadas UMA vez por rodada (reentrante: a 1ª entrada troca, a última restaura). ⚠️ Trocar por
#: tentativa, com tentativas CONCORRENTES, restaurava o original no meio de outra (📊 3 chamadas ao diário
#: REAL na 1ª rodada de dublês).
_BORDAS: Dict[str, Any] = {"n": 0, "pilha": None, "diario": None, "calibrando": True}


@contextlib.contextmanager
def bordas_da_bancada(*, calibrando: bool = True, diario: Optional[List[dict]] = None):
    """O diário vira dublê; a conversa e a memória da corretora, vazias; a dedução LIGADA só aqui (a rodada de
    CALIBRAÇÃO mede a porta — produção lê `cerebro_modos`). Nenhum banco é tocado."""
    import importlib

    DT = importlib.import_module("app.services.destravador")
    DD = importlib.import_module("app.services.diario_de_decisoes")
    if _BORDAS["n"] == 0:
        _BORDAS["calibrando"] = bool(calibrando)
        _BORDAS["diario"] = diario if diario is not None else []

        async def _diario(**kw):
            _BORDAS["diario"].append({k: kw.get(k) for k in ("classe", "acao", "nota", "modo", "gatilho")})
            return f"diario-bancada-{len(_BORDAS['diario'])}"

        async def _vazio(*_a, **_k):
            return []

        async def _calibrado(*_a, **_k):
            return bool(_BORDAS["calibrando"])

        pilha = contextlib.ExitStack()
        pilha.enter_context(D.atributo_trocado(DD, "registrar_decisao", _diario))
        pilha.enter_context(D.atributo_trocado(DT, "_conversa_do_segurado", _vazio))
        pilha.enter_context(D.atributo_trocado(DT, "_memoria_da_corretora", _vazio))
        pilha.enter_context(D.atributo_trocado(DT, "deduzir_calibrado", _calibrado))
        _BORDAS["pilha"] = pilha
    _BORDAS["n"] += 1
    try:
        yield _BORDAS["diario"]
    finally:
        _BORDAS["n"] -= 1
        if _BORDAS["n"] == 0 and _BORDAS["pilha"] is not None:
            _BORDAS["pilha"].close()
            _BORDAS["pilha"] = None


async def motor_portal(caso: dict, llm: Any, *, provedor: str, modelo: str, llm_segunda: Any = None,
                       provedor_segunda: str = "", modelo_segunda: str = "", calibrando: bool = True) -> dict:
    """UMA parada pelo `destravador.destravar_parada_do_portal` — a decisão + o veredito + a calibração."""
    import importlib

    DT = importlib.import_module("app.services.destravador")
    diario: List[dict] = []
    principal = DT.ModeloInjetado(llm=llm, provedor=provedor, modelo=modelo)
    segunda = (DT.ModeloInjetado(llm=llm_segunda, provedor=provedor_segunda, modelo=modelo_segunda)
               if llm_segunda is not None else None)
    with bordas_da_bancada(calibrando=calibrando, diario=diario):
        dec = await DT.destravar_parada_do_portal(EMPRESA_DA_BANCADA, evidencia_do_caso(caso), caso["pedido"],
                                                  modo="on", limiar=int(DT.LIMIAR_MINIMO), job_id=caso["id"],
                                                  llm=principal, llm_segunda=segunda)
    d = dec.para_dict() if dec is not None else {"acao": "", "classe": ""}
    return {"decisao": {k: d.get(k) for k in (
                "classe", "acao", "valor", "nota", "limiar", "motivo", "proibicao", "segunda_opiniao",
                "acao_do_modelo", "valor_do_modelo", "formato_ok", "modelo", "provedor", "modelo_chamado",
                "porta_do_deduzir", "deduzir_calibrado", "custo_usd")},
            "veredito_destravador": julgar(caso, d), "diario": diario,
            "calibracao": {"seguradora": caso["seguradora"], "controle_tecla_1": controle_primeira_opcao(caso),
                           "porta_esperada": None, "tipo": caso["tipo"]}}


async def rodar(casos: List[dict], llm: Any, *, provedor: str, modelo: str, k: int = 2,
                llm_segunda: Any = None, provedor_segunda: str = "", modelo_segunda: str = "",
                paralelo: int = 4, calibrando: bool = True) -> dict:
    """k tentativas por caso, no formato de rodada que `bancada.resumo_da_calibracao` lê."""
    sem = asyncio.Semaphore(max(1, int(paralelo)))
    resultados: List[dict] = []
    parada = ""

    async def um(caso, t):
        nonlocal parada
        async with sem:
            if parada:
                return
            try:
                est = await motor_portal(caso, llm, provedor=provedor, modelo=modelo, llm_segunda=llm_segunda,
                                         provedor_segunda=provedor_segunda, modelo_segunda=modelo_segunda,
                                         calibrando=calibrando)
                resultados.append({"chave": caso["id"], "tentativa": t, "resultado": est["veredito_destravador"]["classe"],
                                   "rastro": {"estado": est}})
            except B.TetoDeGastoAtingido as exc:
                parada = f"teto: {exc}"
            except Exception as exc:  # noqa: BLE001 — a infra caiu: não é ponto da calibração
                resultados.append({"chave": caso["id"], "tentativa": t, "resultado": "BLOCKED_BY_INFRA",
                                   "rastro": {"erro": type(exc).__name__}})

    with bordas_da_bancada(calibrando=calibrando):
        await asyncio.gather(*(um(c, t) for c in casos for t in range(1, int(k) + 1)))
    resultados.sort(key=lambda r: (r["chave"], r["tentativa"]))
    return {"resultados": resultados, "parada": parada}


# ═════════════════════════════════════════════════════════════════════════════
# A DECISÃO DE RELIGAR — a MESMA régua da SPEC-126 U6
# ═════════════════════════════════════════════════════════════════════════════
def resumo_e_decisao(rodada: dict, *, rotulo: str = "", segunda: str = "", medido_em: str = "") -> tuple:
    resumo = B.resumo_da_calibracao([rodada])
    decisao = B.decidir_religar(resumo, rodada=sha_do_gabarito(), braco=rotulo, segunda=segunda,
                                medido_em=medido_em)
    return resumo, decisao


def sql_de_religar_o_portal(decisao: Dict[str, dict], company_ids: List[str]) -> str:
    """O UPSERT que liga o DEDUZIR **do portal** — por CORRETORA × SEGURADORA × `vidros`, só onde
    `decidir_religar` disse sim. ⛔ Nunca a linha `todos` (essa é a do WhatsApp: a calibração do portal não
    liga a URA). A linha `vidros` nasce com o MODO e o LIMIAR da `todos` da mesma corretora × seguradora.
    ⚠️ Precedência (`acao_do_cerebro`): (seguradora, vidros) > (seguradora, todos) — desligar o portal passa
    a ser nesta linha. Nada é aplicado aqui (o gerente aplica, com APPLY/VERIFY/ROLLBACK)."""
    linhas = []
    for seg, d in sorted(decisao.items()):
        if not d.get("religa"):
            continue
        if not re.fullmatch(r"[a-z0-9_]{2,40}", seg):
            raise ValueError(f"seguradora inválida: {seg!r}")
        prova = json.dumps(d["calibracao"], ensure_ascii=False, sort_keys=True).replace("'", "''")
        for cid in company_ids:
            if not re.fullmatch(r"[0-9a-fA-F-]{36}", str(cid)):
                raise ValueError(f"company_id inválido: {cid!r}")
            linhas.append(
                "insert into public.cerebro_modos (company_id, insurer_key, ramo, modo, limiar, motivo, ligado_por, "
                "deduzir_calibrado, calibracao) "
                f"select company_id, insurer_key, 'vidros', modo, limiar, 'SPEC-127 P5: DEDUZIR do portal calibrado', "
                f"'bancada_portal', true, '{prova}'::jsonb from public.cerebro_modos "
                f"where company_id = '{cid}' and insurer_key = '{seg}' and ramo = 'todos' "
                "on conflict (company_id, insurer_key, ramo) do update set deduzir_calibrado = true, "
                "calibracao = excluded.calibracao, updated_at = now();")
    return "\n".join(linhas) or "-- nenhuma seguradora religa: nada a aplicar (o DEDUZIR do portal fica desligado)"


# ═════════════════════════════════════════════════════════════════════════════
# OS DUBLÊS (grátis) — a linha de controle e o teto da régua
# ═════════════════════════════════════════════════════════════════════════════
_RX_OPCAO = re.compile(r"^\d+ - (.+)$", re.M)


class DubleDoPortal:
    """Um "modelo" que lê a parada do prompt REAL (`compor_mensagens_do_portal`) e responde pela regra dada:
    `primeira` = a 1ª opção (o CONTROLE) · `perfeito` = a do gabarito (o teto: mede a régua, não um modelo)."""

    def __init__(self, regra: str, gabaritos: Optional[Dict[str, str]] = None, provedor: str = "duble"):
        self.regra, self.gabaritos, self.provedor = regra, dict(gabaritos or {}), provedor

    async def ainvoke(self, mensagens):
        from langchain_core.messages import AIMessage

        from app.services.destravador import texto_da_mensagem

        user = texto_da_mensagem(mensagens[-1])
        opcoes = _RX_OPCAO.findall(user.split("Opções da lista do portal:", 1)[-1]) if "Opções da lista" in user else []
        valor = ""
        if self.regra == "primeira":
            valor = opcoes[0] if opcoes else ""
        elif self.regra == "perfeito":
            valor = next((g for chave, g in self.gabaritos.items() if chave in user), "")
        corpo = ({"classe": "deduzir", "acao": "RESPONDER", "valor": valor, "nota": 95, "motivo": "duble"}
                 if valor else {"classe": "perguntar_ao_segurado", "acao": "PERGUNTAR_AO_SEGURADO",
                                "valor": "Qual opção?", "nota": 50, "motivo": "duble"})
        return AIMessage(content=json.dumps(corpo, ensure_ascii=False),
                         response_metadata={"model_provider": self.provedor, "model_name": f"duble-{self.regra}"})


def gabaritos_por_marca(casos: List[dict]) -> Dict[str, str]:
    """Para o dublê `perfeito`: um trecho ÚNICO do prompt de cada caso (o relato) → a resposta do gabarito."""
    return {c["pedido"]["dano"]["descricao"]: c["gabarito"]["resposta"] for c in casos
            if c["gabarito"]["acao"] == "RESPONDER" and c["pedido"]["dano"].get("descricao")}


# ═════════════════════════════════════════════════════════════════════════════
# A LINHA DE COMANDO
# ═════════════════════════════════════════════════════════════════════════════
def construir_braco(rotulo: str, papel: str, *, orcamento: Optional[B.Orcamento] = None) -> tuple:
    """`(braco, llm)`. Real → a fábrica do produto, ISOLADA (`construir_llm_padrao`, `service_type='bancada'`),
    com `details.papel` no ledger e o `Medidor` (teto lido do ledger). Nenhum cliente novo (CLAUDE.md §5)."""
    braco = B.Braco.de(rotulo)
    if braco.e_duble:
        raise ValueError("dublê é montado por `rodar_pela_linha_de_comando`")
    preco = B.preco_do_catalogo(braco)
    if preco is None:
        raise B.SemPrecoConhecido(f"{braco.rotulo}: sem preço no catálogo — a bancada não inventa preço")
    resolvido = B.resolver_padrao(papel, override=braco.override())
    llm = B._marcar_papel_no_ledger(B.construir_llm_padrao(resolvido), papel)
    return braco, B.Medidor(llm, preco=preco, orcamento=orcamento or B.Orcamento(B.teto_padrao()),
                            max_output=B.MAX_TOKENS_DA_BANCADA)


def rodar_pela_linha_de_comando(*, bracos: List[str], segunda: Optional[str] = None, k: int = 2,
                                casos: Optional[str] = None, tipos: Optional[List[str]] = None,
                                teto_provedor: Optional[float] = None, ledger_desde: Optional[str] = None,
                                saida: Optional[str] = None, paralelo: int = 4, so_corpus: bool = False,
                                company_ids: Optional[List[str]] = None) -> int:
    lista = carregar_casos(casos, tipos=tipos)
    sujos = {c["id"]: pii_do_caso(c) for c in lista if pii_do_caso(c)}
    if sujos:
        print(f"⛔ o corpus tem PII — nada roda: {sujos}")
        return 2
    print(f"corpus {CORPUS.name} sha {sha_do_gabarito()} · {len(lista)} casos · {contagem(lista)}")
    print(f"controle (1ª opção certa): {sum(controle_primeira_opcao(c) for c in lista)}/"
          f"{sum(c['gabarito']['acao'] == 'RESPONDER' for c in lista)}")
    if so_corpus:
        return 0
    if not bracos:
        print("⛔ --braco é obrigatório (ou --so-corpus)")
        return 2
    reais = [b for b in bracos + ([segunda] if segunda else []) if not B.Braco.de(b).e_duble]
    if reais and (teto_provedor is None or not ledger_desde):
        print("⛔ braço real exige --teto-provedor e --ledger-desde (o teto é lido do LEDGER)")
        return 2
    gab = gabaritos_por_marca(lista)
    if segunda:
        b2 = B.Braco.de(segunda)
        llm2 = (DubleDoPortal(b2.model, gab, provedor="anthropic") if b2.e_duble else
                construir_braco(segunda, PAPEL_SEGUNDA, orcamento=B.OrcamentoDoLedger(
                    b2.provider, teto_provedor, ledger_desde))[1])
        prov2, mod2 = ("anthropic" if b2.e_duble else b2.provider), b2.model
    else:
        llm2, prov2, mod2 = DubleDoPortal("perfeito", gab, provedor="anthropic"), "anthropic", "duble-perfeito"
    saida_json: Dict[str, Any] = {"papel": PAPEL, "corpus_sha": sha_do_gabarito(), "k": k, "bracos": {}}
    codigo = 0
    for rotulo in bracos:
        b = B.Braco.de(rotulo)
        if b.e_duble:
            llm, prov = DubleDoPortal(b.model, gab, provedor="openai"), "openai"
        else:
            orc = B.OrcamentoDoLedger(b.provider, teto_provedor, ledger_desde)
            print(f"ledger {b.provider} desde {ledger_desde}: US$ {orc.inicial:.4f} · teto {teto_provedor:.2f} · "
                  f"resta {orc.teto_usd:.4f}")
            if orc.teto_usd <= 0:
                print("⛔ teto já atingido no ledger — nada roda")
                return 2
            b, llm = construir_braco(rotulo, PAPEL, orcamento=orc)
            prov = b.provider
        rod = asyncio.run(rodar(lista, llm, provedor=prov, modelo=b.model, k=k, llm_segunda=llm2,
                                provedor_segunda=prov2, modelo_segunda=mod2, paralelo=paralelo))
        resumo, decisao = resumo_e_decisao(rod, rotulo=b.rotulo, segunda=f"{prov2}:{mod2}")
        print(f"\n== {b.rotulo} (2ª: {prov2}:{mod2}) ==\n" + B.tabela_da_calibracao(resumo, decisao)
              + (f"\n⛔ PAROU: {rod['parada']}" if rod["parada"] else ""))
        if company_ids:
            print(sql_de_religar_o_portal(decisao, company_ids))
        saida_json["bracos"][b.rotulo] = {"resumo": {s: {k2: v for k2, v in m.items() if k2 != "casos"}
                                                     for s, m in resumo.items()},
                                          "decisao": decisao, "parada": rod["parada"], "resultados": rod["resultados"]}
        codigo = 2 if rod["parada"] else codigo
    if saida:
        Path(saida).write_text(json.dumps(saida_json, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        print(f"relatório: {saida}")
    return codigo


def main(argv: Optional[List[str]] = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    from app.services.evals.bancada_confirmacao import carregar_env

    carregar_env()
    p = argparse.ArgumentParser(description="SPEC-127 P5 — a bancada do DEDUZIR do portal")
    p.add_argument("--braco", action="append", default=[], help="provider:model[:effort] ou duble:<primeira|perfeito>")
    p.add_argument("--segunda", default=None, help="a 2ª opinião (OUTRO provedor): provider:model ou duble:perfeito")
    p.add_argument("--k", type=int, default=2)
    p.add_argument("--casos", default=None)
    p.add_argument("--tipos", default=None, help=f"vírgula: {','.join(TIPOS)}")
    p.add_argument("--teto-provedor", type=float, default=None)
    p.add_argument("--ledger-desde", default=None)
    p.add_argument("--saida", default=None)
    p.add_argument("--paralelo", type=int, default=4)
    p.add_argument("--so-corpus", action="store_true")
    p.add_argument("--company-id", action="append", default=[], help="para imprimir o SQL de religar")
    a = p.parse_args(argv)
    return rodar_pela_linha_de_comando(
        bracos=a.braco, segunda=a.segunda, k=a.k, casos=a.casos,
        tipos=[t for t in str(a.tipos or "").split(",") if t] or None, teto_provedor=a.teto_provedor,
        ledger_desde=a.ledger_desde, saida=a.saida, paralelo=a.paralelo, so_corpus=a.so_corpus,
        company_ids=a.company_id or None)


if __name__ == "__main__":
    raise SystemExit(main())
