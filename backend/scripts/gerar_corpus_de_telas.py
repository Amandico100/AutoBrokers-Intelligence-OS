"""O corpus de telas reais — SPEC-083 §6 e Bloco A.

```
backend/tests/corpus/telas_reais/<seguradora>-<ramo>.jsonl
backend/tests/corpus/telas_reais/INDICE.md
```

**Por que versionado, e não consultado no teste** (§6.6):
1. o teste roda **sem banco** — em CI e na máquina de quem escreve corredor
2. o corpus é **prova datada**: se a URA mudar, ele continua sendo o que
   justificou aquele passo
3. o gate não depende de rede

🔴 **A decisão multi-tenant, registrada** (§6.2): o corpus é **global por
seguradora+ramo**. `company_id` fica como metadado de proveniência e o replay o
ignora. Decisão do Founder: *"a seguradora faz a MESMA pergunta para todas as
corretoras. O que muda entre elas são os DADOS."* Coerente com
`O-ATLAS-E-UM-SO-E-E-DE-TODAS.md`.

Uso:
    python backend/scripts/gerar_corpus_de_telas.py --todas [--dry-run]
    python backend/scripts/gerar_corpus_de_telas.py --seguradora allianz
    python backend/scripts/gerar_corpus_de_telas.py --auditar-pii
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import os
import subprocess
import sys
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import higiene_do_corpus as H          # noqa: E402
import padroes_de_ramo as PR           # noqa: E402
import regua_motor as M                # noqa: E402
import zonas_do_acervo as Z            # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESTINO = os.path.join(RAIZ, "tests", "corpus", "telas_reais")

# 🔴 O teto de sessões, com a correção do Founder (decisão A3, 21/08/2026).
#
# ⚠️ O problema medido: a SPEC-083 §6.5 fixava **5 sessões por (seguradora,
#    ramo)** — e `allianz-residencial` tem **6 subserviços**. A escolha gulosa por
#    diversidade Jaccard não garante cobertura por serviço, então uma rota podia
#    receber ZERO sessões e sair `SEM_CORPUS` **por amostragem, não por ausência**
#    — o desfecho que a SPEC-084 §7.2 proíbe por nome.
#
# **A decisão:** 1 sessão por serviço primeiro, depois diversidade. O teto sobe
# quando os serviços passam de 5.
TETO_BASE_DE_SESSOES = 5
TETO_DE_BYTES_POR_ARQUIVO = 500 * 1024

# 🔴 O FILTRO ② DA SPEC-084 §2.5.2 — a fala humana que a fronteira não pega.
#
# A `FRONTEIRAS` corta a partir do anúncio de transferência. Sobra a fala humana
# que aparece ANTES dela, ou em sessão sem transferência nenhuma.
#
# ⚠️ **ANCORADO EM `^…$`, NUNCA EM PREFIXO** — e essa palavra custou uma versão
# inteira da SPEC-084. 📊 O padrão em prefixo rejeitava:
#
# ```
#   "certo! por favor digite o *cpf* ou *cnpj* do(a) titular da apolice..."   78 ses
#   "certo, neste caso qual e o nome da pessoa que esta no local?"            40 ses
#   "ok, agora selecione o endereco onde esta o veiculo..."                   19 ses
#                                                    ... 267 telas distintas
# ```
#
# 🔴 **A primeira é a tela do CPF da Allianz — o nó de maior retorno do acervo.**
#    O guarda da v2 nunca ficava vermelho; o da v3 nunca ficaria verde.
#
# 📊 E o alvo verdadeiro sobrevive ao aperto: `"ok"` sozinho e `"um momento"`
#    sozinho somam **63 sessões** — humano, e ainda pegos pelo `^…$`.
#
# ⚠️ Este filtro NASCEU de um guarda vermelho: `test_o_corpus_nao_tem_falas_de_gente`
#    acusou 1 linha (`"ok"` em `allianz-residencial`) numa geração em que o
#    gerador ainda não o aplicava. **O teste conferia o corpus e nada o produzia.**
import re as _re  # noqa: E402
FALA_DE_GENTE = _re.compile(
    r"^(ok|certo|perfeito|prontinho|um momento|mais um momento|com quem falo|"
    r"ajudo em algo mais|mais alguma duvida|bom dia tudo bem|obrigad[oa])[!.,?]?$")


# ─────────────────────────────────────────────────────────────────────────────
# `sessao_chegou_ao_fim` — o `DECIDE:` #1 da SPEC-083 §2.4, e NADA MAIS.
#
# 🔴 Ele NASCE AQUI, no Bloco A, e o Bloco C o IMPORTA. A versão anterior da SPEC
#    mandava escolher *"a mais recente COM DESFECHO"* no Bloco A e definia
#    "desfecho" no Bloco C — uma circularidade no mesmo lugar de onde a antiga
#    saiu.
# ─────────────────────────────────────────────────────────────────────────────
def sessao_chegou_ao_fim(playbook: Dict[str, Any], telas: List[str]) -> bool:
    """A sessão chegou ao protocolo? — pelo MOTOR, nunca por regex do script.

    `DECIDE:` ≥1 tela em que `extract_capture_anchors` devolve `protocol`,
    **ou** `detect_finalize_anchor` casou e a sessão seguiu ≥1 tela depois.

    🔴 Exige o MOTOR e não a presença do padrão. 📊 Razão medida: a
    `_ANCORA_DE_PROTOCOLO` tem o ramo `o\\.?s\\.?`, que casa o **artigo "os"**
    seguido de dígitos. Em yelum, 31 das 38 sessões "com protocolo" casam **só**
    pelos ramos largos. `extract_capture_anchors` devolve o grupo capturado, que
    é o que distingue os dois.
    """
    for i, tela in enumerate(telas):
        if M.extract_capture_anchors(playbook, tela).get("protocol"):
            return True
        if M.detect_finalize_anchor(playbook, tela) and i < len(telas) - 1:
            return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# A ESCOLHA DAS SESSÕES — sem ambiguidade, e determinística.
# ─────────────────────────────────────────────────────────────────────────────
def _jaccard(a: Set[str], b: Set[str]) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / max(1, len(a | b))


def escolher_sessoes(
    candidatas: List[Tuple[Any, str, Set[str], bool, Optional[str]]],
    teto: int,
) -> Tuple[List[Any], List[str]]:
    """`[(sid, wa_ts, telas_norm, chegou_ao_fim, servico)]` -> `(escolhidas, notas)`.

    A ordem, e cada passo existe por um motivo medido:

    ```
    1. COBERTURA POR SERVIÇO — a mais recente de CADA serviço presente.
       ⚠️ Sem isto, uma rota sai `SEM_CORPUS` por amostragem (decisão A3).
    2. a mais recente COM DESFECHO, se ainda não entrou
    3. o resto: guloso por JACCARD sobre o conjunto de telas, escolhendo a cada
       passo a sessão de MENOR similaridade máxima contra as já escolhidas
    4. empate -> a mais recente vence (determinístico, NUNCA sorteio)
    ```

    📊 **CONTROLE:** rodar duas vezes tem de dar o MESMO conjunto. Corpus que muda
    entre execuções faz a nota mudar sem nada mudar na rota.
    """
    notas: List[str] = []
    porrecencia = sorted(candidatas, key=lambda c: (c[1], str(c[0])), reverse=True)
    escolhidas: List[Any] = []
    vistas: Dict[Any, Set[str]] = {}

    # 1 · cobertura por serviço
    ja_coberto: Set[str] = set()
    for sid, _ts, telas, _fim, servico in porrecencia:
        if servico and servico not in ja_coberto and len(escolhidas) < teto:
            escolhidas.append(sid)
            vistas[sid] = telas
            ja_coberto.add(servico)
            notas.append(f"cobertura de servico: {servico} -> {str(sid)[:8]}")

    # 2 · a mais recente com desfecho
    com_fim = [c for c in porrecencia if c[3]]
    if com_fim and com_fim[0][0] not in escolhidas and len(escolhidas) < teto:
        sid = com_fim[0][0]
        escolhidas.append(sid)
        vistas[sid] = com_fim[0][2]
        notas.append(f"mais recente COM DESFECHO -> {str(sid)[:8]}")
    elif com_fim:
        notas.append(f"A#1 satisfeito pela sessao que a selecao garantiu "
                     f"({str(com_fim[0][0])[:8]})")

    # 3 · diversidade gulosa
    restantes = [c for c in porrecencia if c[0] not in escolhidas]
    while restantes and len(escolhidas) < teto:
        melhor = None
        melhor_sim = 2.0
        for c in restantes:
            sim = max((_jaccard(c[2], v) for v in vistas.values()), default=0.0)
            # 4 · empate -> a mais recente vence. `restantes` já está por
            #     recência decrescente, e `<` (não `<=`) preserva a primeira.
            if sim < melhor_sim:
                melhor_sim, melhor = sim, c
        if melhor is None:
            break
        escolhidas.append(melhor[0])
        vistas[melhor[0]] = melhor[2]
        restantes.remove(melhor)
        notas.append(f"diversidade (jaccard max {melhor_sim:.2f}) -> {str(melhor[0])[:8]}")

    # ⚠️ O efeito colateral que a ferramenta DECLARA, em vez de esconder: a
    #    seleção GARANTE que a mais recente com desfecho entre no corpus, e o
    #    eixo A depois pergunta se alguma sessão do corpus teve desfecho.
    #    A amostra é escolhida para passar no item que ela alimenta.
    return escolhidas, notas


# ─────────────────────────────────────────────────────────────────────────────
# A GERAÇÃO
# ─────────────────────────────────────────────────────────────────────────────
def _commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=RAIZ,
            stderr=subprocess.DEVNULL).decode().strip()
    except Exception:  # noqa: BLE001
        return "?"


def carregar_acervo(seguradoras: Iterable[str]) -> Dict[str, Dict[Any, List[Dict[str, Any]]]]:
    acervo: Dict[str, Dict[Any, List[Dict[str, Any]]]] = {}
    for seg in seguradoras:
        por_sessao: Dict[Any, List[Dict[str, Any]]] = collections.defaultdict(list)
        for e in M.eventos_observados(seguradora=seg):
            por_sessao[e.get("session_id")].append(e)
        acervo[seg] = dict(por_sessao)
    return acervo


def gerar(seguradoras: List[str], *, dry_run: bool = False) -> Dict[str, Any]:
    """Roda os 6 passos do Bloco A e devolve o relatório."""
    # 🔴 O CONTROLE VEM PRIMEIRO. Sem ele, tudo o que vier depois é inválido.
    marcas = M.controle_do_mascarador()

    acervo = carregar_acervo(seguradoras)
    rel: Dict[str, Any] = {
        "gerado_em": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "commit": _commit(),
        "marcas_de_corretora": marcas,
        "arquivos": {}, "recusadas": [], "avisos": [], "por_seguradora": {},
    }

    # PASSO 3 (levantado antes, porque NÃO é decisão local à tela — §CA-064):
    # a lista de esqueletos cujo vocativo é DADO.
    #
    # 🔴 SEMPRE sobre o ACERVO INTEIRO, nunca sobre o recorte de `--seguradora`.
    #    ⚠️ Achado na primeira execução: com `--seguradora allianz` o levantamento
    #    devolveu **0 esqueletos**, porque as 7 famílias de vocativo vivem em
    #    porto, azul, hdi e yelum. Rodar por seguradora produziria um
    #    mascaramento DIFERENTE de rodar `--todas` — e o corpus deixaria de ser
    #    reprodutível, que é o CONTROLE do passo 4 (*"rodar duas vezes tem de dar
    #    o MESMO conjunto"*). O custo é uma leitura a mais do acervo; o benefício
    #    é a máscara não depender de quem chamou o script.
    acervo_para_vocativo = (acervo if set(seguradoras) == set(M.seguradoras())
                            else carregar_acervo(M.seguradoras()))
    todos_os_textos = [e.get("text") or ""
                       for ses in acervo_para_vocativo.values()
                       for evs in ses.values() for e in evs
                       if e.get("direction") == "in"]
    esq_dado, esq_duvidoso = H.levantar_vocativos(todos_os_textos)
    rel["vocativos"] = {"dado": len(esq_dado), "duvidoso": len(esq_duvidoso)}

    for seg, sessoes in acervo.items():
        pb_por_ramo = {}
        for ramo in PR.ramos_de(seg):
            ref = M.resolve_playbook_ref(seg, ramo)
            pb_por_ramo[ramo] = M.get_playbook(ref) if ref else None

        por_ramo: Dict[str, List[Tuple[Any, str, Set[str], bool, Optional[str], List[Dict]]]] = \
            collections.defaultdict(list)
        contagem = collections.Counter()

        for sid, eventos in sessoes.items():
            if not Z._tem_sessao(sid):
                contagem["ORFAO_sessao"] += 1
                continue
            ordenados = sorted(eventos, key=lambda x: x.get("wa_timestamp") or "")
            pares = [(e.get("direction"), Z.norm_para_classificar(e.get("text") or ""))
                     for e in ordenados]

            # PASSO 0 · o RAMO, pela cascata de dois níveis
            ramo, nivel = PR.classificar_ramo(seg, pares)
            contagem[f"ramo:{ramo}"] += 1
            contagem[f"nivel:{nivel.split(':')[0]}"] += 1
            # 🔴 Os três estados que NÃO viram corpus, e são coisas diferentes:
            #    `indefinido`   a sessão não decidiu (quase toda curta)
            #    `ambos`        colisão -> algum padrão cita cardápio (PADRAO_DE_CARDAPIO)
            #    `sem_escolha`  a sessão é longa e legítima, mas NÃO É DE ASSISTÊNCIA
            #                   (📊 cartão de crédito, sinistro RE, contratação)
            if ramo in ("indefinido", "ambos", "sem_escolha"):
                if ramo == "ambos":
                    rel["avisos"].append(
                        f"PADRAO_DE_CARDAPIO {seg}/{str(sid)[:8]}: {nivel}")
                continue

            # PASSO 1 · só `direction='in'`, e só `zona='URA'`
            linhas: List[Dict[str, Any]] = []
            vistos: Set[str] = set()
            for e, zona, _motivo in Z.zonas(ordenados, seg):
                if e.get("direction") != "in":
                    continue
                contagem[f"zona:{zona}"] += 1
                if zona != "URA":
                    continue
                bruto = Z.limpar_invisiveis(e.get("text") or "")
                if not bruto.strip():
                    continue
                n = M._norm(bruto)

                # PASSO 1b · a direção invertida (defeito de ingestão)
                if Z.direcao_invertida(n):
                    contagem["DIRECAO_INVERTIDA"] += 1
                    continue

                # PASSO 1c · o filtro ② — fala humana que a fronteira não pegou
                if FALA_DE_GENTE.match(n.strip()):
                    contagem["FALA_DE_GENTE"] += 1
                    continue

                # PASSO 2 · dedup por (session_id, _norm(text)). 🔴 O timestamp
                #           NÃO entra: 📊 metade dos eventos de uma sessão é
                #           repetição do mesmo texto, e a tokio tem 36,3% de
                #           duplicata exata.
                if n in vistos:
                    contagem["dedup"] += 1
                    continue
                vistos.add(n)

                # PASSO 3 · mascarar (§6.4 + CA-062 + CA-064)
                pb = pb_por_ramo.get(ramo)
                limpo, marcas_ap = H.higienizar(pb or {}, bruto, esq_dado)
                if marcas_ap["senha_preservada"]:
                    contagem["senha_preservada"] += 1
                if marcas_ap["vocativo_mascarado"]:
                    contagem["vocativo_mascarado"] += 1

                sujeira = H.auditar_pii(limpo)
                if sujeira:
                    # 🔴 RECUSAR só o que sobrar sujo depois da máscara — e a
                    #    recusa vai para o INDICE.md com sessão e motivo.
                    #    *"some do arquivo, não do registro."*
                    rel["recusadas"].append(
                        {"seguradora": seg, "ramo": ramo, "session_id": str(sid)[:8],
                         "motivo": ",".join(sorted({s.split(":")[0] for s in sujeira}))})
                    contagem["RECUSADA"] += 1
                    continue

                linhas.append({
                    "session_id": str(sid)[:8],
                    "wa_timestamp": e.get("wa_timestamp"),
                    "company_id": str(e.get("company_id") or "")[:8],
                    "text": limpo,
                })

            if not linhas:
                continue
            pb = pb_por_ramo.get(ramo)
            fim = sessao_chegou_ao_fim(pb, [l["text"] for l in linhas]) if pb else False
            por_ramo[ramo].append(
                (sid, max(l["wa_timestamp"] or "" for l in linhas),
                 {l["text"] for l in linhas}, fim, None, linhas))

        rel["por_seguradora"][seg] = dict(contagem)

        # PASSO 4 · a escolha, e PASSO 5 · gravar
        for ramo, candidatas in por_ramo.items():
            pb = pb_por_ramo.get(ramo)
            n_servicos = len((pb or {}).get("subservices") or {})
            teto = max(TETO_BASE_DE_SESSOES, n_servicos)
            escolhidas, notas = escolher_sessoes(
                [(c[0], c[1], c[2], c[3], c[4]) for c in candidatas], teto)
            mapa = {c[0]: c[5] for c in candidatas}
            linhas = [l for sid in escolhidas for l in mapa[sid]]
            linhas.sort(key=lambda l: (l["wa_timestamp"] or "", l["session_id"]))

            nome = f"{seg}-{ramo}.jsonl"
            corpo = "\n".join(json.dumps(l, ensure_ascii=False) for l in linhas) + "\n"
            rel["arquivos"][nome] = {
                "linhas": len(linhas), "bytes": len(corpo.encode("utf-8")),
                "sessoes_no_corpus": [str(s)[:8] for s in escolhidas],
                "sessoes_candidatas": len(candidatas),
                "teto": teto, "subservices": n_servicos,
                "chegou_ao_fim": sum(1 for c in candidatas if c[3]),
                "notas_da_selecao": notas,
            }
            if len(corpo.encode("utf-8")) > TETO_DE_BYTES_POR_ARQUIVO:
                rel["avisos"].append(f"TETO_DE_BYTES estourado em {nome}")
            if not dry_run:
                os.makedirs(DESTINO, exist_ok=True)
                with open(os.path.join(DESTINO, nome), "w", encoding="utf-8") as fh:
                    fh.write(corpo)
    return rel


def escrever_indice(rel: Dict[str, Any]) -> str:
    """`INDICE.md` — 🔴 o que SAI do corpus fica registrado. Nunca silêncio."""
    L: List[str] = []
    L.append("# Corpus de telas reais — ÍNDICE\n")
    L.append(f"> Gerado em **{rel['gerado_em']}** · commit `{rel['commit']}`")
    L.append(f"> 📊 `marcas_de_corretora()` = **{rel['marcas_de_corretora']}** "
             f"(o CONTROLE da SPEC-084 §2.5.1.3 — se fosse 0, a geração teria "
             f"rodado sem banco e o corpus **não estaria mascarado**)\n")
    L.append("🔴 Este arquivo existe porque a SPEC-083 §7 proíbe pular em "
             "silêncio: *\"truncar calado lê-se como 'cobrimos tudo'\"*.\n")
    L.append("## Os arquivos\n")
    L.append("| arquivo | linhas | KB | sessões no corpus | candidatas | teto | subserviços | c/ desfecho |")
    L.append("|---|---:|---:|---|---:|---:|---:|---:|")
    for nome, d in sorted(rel["arquivos"].items()):
        L.append(f"| `{nome}` | {d['linhas']} | {d['bytes']/1024:.0f} | "
                 f"{' '.join(d['sessoes_no_corpus'])} | {d['sessoes_candidatas']} | "
                 f"{d['teto']} | {d['subservices']} | {d['chegou_ao_fim']} |")
    L.append("\n## Por que cada sessão entrou\n")
    for nome, d in sorted(rel["arquivos"].items()):
        L.append(f"**`{nome}`**")
        for n in d["notas_da_selecao"]:
            L.append(f"- {n}")
        L.append("")
    L.append("## Linhas RECUSADAS — sujeira que sobrou depois da máscara\n")
    if rel["recusadas"]:
        L.append("| seguradora | ramo | sessão | motivo |")
        L.append("|---|---|---|---|")
        for r in rel["recusadas"]:
            L.append(f"| {r['seguradora']} | {r['ramo']} | `{r['session_id']}` | {r['motivo']} |")
    else:
        L.append("_nenhuma_")
    L.append("\n## Contagens por seguradora\n")
    L.append("| seguradora | " + " | ".join(
        sorted({k for d in rel["por_seguradora"].values() for k in d})) + " |")
    chaves = sorted({k for d in rel["por_seguradora"].values() for k in d})
    L.append("|---" * (len(chaves) + 1) + "|")
    for seg, d in sorted(rel["por_seguradora"].items()):
        L.append(f"| {seg} | " + " | ".join(str(d.get(k, 0)) for k in chaves) + " |")
    if rel["avisos"]:
        L.append("\n## Avisos\n")
        for a in rel["avisos"]:
            L.append(f"- {a}")
    L.append(f"\n## Vocativos\n\n📊 esqueletos com ≥3 cabeças distintas "
             f"(= DADO, mascarado): **{rel['vocativos']['dado']}** · "
             f"com exatamente 2 (= `NOME_DUVIDOSO`, **não** mascarado "
             f"automaticamente, fica para leitura humana): "
             f"**{rel['vocativos']['duvidoso']}**\n")
    return "\n".join(L) + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Gera o corpus de telas reais (SPEC-083 Bloco A)")
    ap.add_argument("--todas", action="store_true")
    ap.add_argument("--seguradora")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--auditar-pii", action="store_true")
    a = ap.parse_args(argv)

    if a.auditar_pii:
        return auditar(DESTINO)

    segs = [a.seguradora] if a.seguradora else M.seguradoras()
    rel = gerar(segs, dry_run=a.dry_run)
    if not a.dry_run:
        os.makedirs(DESTINO, exist_ok=True)
        with open(os.path.join(DESTINO, "INDICE.md"), "w", encoding="utf-8") as fh:
            fh.write(escrever_indice(rel))
    print(escrever_indice(rel))
    return 0


def auditar(destino: str) -> int:
    """🔴 O VERIFY que CONSEGUE falhar (SPEC-083 Bloco A).

    A v1 da SPEC usava `grep -cE '[0-9]{11}'`. Ele **não casa**
    `+55 (47) 99627-4743` — a maior sequência de dígitos ali tem CINCO.
    Devolvia 0 com quatro telefones no arquivo.
    """
    total = sujas = 0
    achados: List[str] = []
    for nome in sorted(os.listdir(destino)):
        if not nome.endswith(".jsonl"):
            continue
        for i, linha in enumerate(open(os.path.join(destino, nome), encoding="utf-8"), 1):
            if not linha.strip():
                continue
            total += 1
            d = json.loads(linha)
            if d.get("direction") not in (None, "in"):
                achados.append(f"{nome}:{i} DIRECAO != in")
                sujas += 1
                continue
            s = H.auditar_pii(d.get("text") or "")
            if s:
                sujas += 1
                achados.append(f"{nome}:{i} {d['session_id']} -> {','.join(s[:3])}")
    print(f"auditoria de PII: {total} linhas, {sujas} sujas")
    for a in achados[:40]:
        print("  " + a)
    return 1 if sujas else 0


if __name__ == "__main__":
    raise SystemExit(main())
