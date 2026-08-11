"""Pergunta a mesma coisa quatro vezes, mudando UM fator. Nao julga nada.

    NO CONTEINER:
        cd /app && python scripts/acervo/medir_o_rag.py

    so as 6 primeiras, para ver se esta funcionando antes de gastar 15 minutos:
        cd /app && python scripts/acervo/medir_o_rag.py --limite 6

⚠️ O caminho no conteiner NAO tem `backend/` — o Dockerfile faz `WORKDIR /app`
+ `COPY . .` a partir de `backend/`.

O QUE ELE RESPONDE
------------------
Uma pergunta so: **o RAG melhora a resposta, ou nao?** E, se melhora, qual
metade dele esta pagando — o contrato ou a carta destilada.

Para isso a MESMA pergunta e respondida quatro vezes, variando **um fator por
vez** (CLAUDE.md §9.2), com a linha de controle embutida no proprio desenho:

    A  sem RAG        o modelo sozinho          ← o CONTROLE
    B  so contrato    namespace `normative`
    C  so cartas      namespace `cards`+`canon`
    D  os dois        exatamente como esta no ar hoje

O braco A e o que da direito a conclusao. Sem ele, uma resposta boa no D se
credita ao RAG quando podia ser so o modelo sabendo de seguros — e ai se
constroi em cima de uma causa que nao era.

O QUE ELE **NAO** FAZ
---------------------
Nao julga, nao pontua, nao compara. So pergunta e grava. O julgamento acontece
depois, por quem nao escreveu nem as perguntas nem este script, lendo as
respostas **embaralhadas e sem saber de que braco vieram**.

Misturar as duas coisas seria escrever o gabarito e a prova com a mesma mao.

NAO E UM SEGUNDO MOTOR DE BUSCA — CLAUDE.md §5
----------------------------------------------
Usa `qdrant.search_similar` e `build_global_search_kwargs`, que sao as mesmas
funcoes que `search_service._execute_search` chama em producao. O que muda
entre os bracos e **so o valor de `namespace`** — o mesmo parametro que
`ORCAMENTO_GLOBAL` ja varia hoje a cada pergunta.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

AQUI = os.path.dirname(os.path.abspath(__file__))
PERGUNTAS = os.path.join(AQUI, "teste_rag", "perguntas.json")
SAIDA = os.path.join(AQUI, "teste_rag", "respostas.json")

# Os quatro bracos. `None` = nao busca nada.
#
# As COTAS sao as de producao (`knowledge_scope.COTA_FINAL`): 3 vagas para
# contrato e 3 para carta. Nos bracos de fonte unica a cota da fonte ausente
# NAO e redistribuida — B recebe 3 trechos de contrato, nao 6. Dar 6 ao B
# mudaria dois fatores de uma vez (a fonte E o tamanho do contexto), e ai
# nenhuma diferenca medida teria dono.
BRACOS = (
    ("A", "sem_rag", None, 0),
    ("B", "so_contrato", ["normative"], 3),
    ("C", "so_cartas", ["cards", "canon"], 3),
    ("D", "contrato_e_cartas", "AMBOS", 6),
)

# O MESMO prompt nos quatro. Se ele mudasse entre os bracos, a diferenca medida
# seria do prompt, nao do RAG.
SISTEMA = (
    "Voce e o AutoBrokers, o assistente de uma corretora de seguros brasileira. "
    "Responde ao corretor ou ao segurado com precisao e sem enrolacao.\n\n"
    "REGRAS:\n"
    "1. Se houver TRECHOS DE REFERENCIA abaixo, responda com base neles e diga "
    "de onde tirou.\n"
    "2. Se NAO houver trecho, ou se os trechos nao responderem a pergunta, diga "
    "que nao tem o documento — nao complete com conhecimento geral de seguros.\n"
    "3. Nunca invente numero, prazo, percentual ou nome de cobertura.\n"
    "4. Se a pergunta pede dado da APOLICE de um cliente especifico, explique "
    "que isso esta na apolice dele, nao nas condicoes gerais.\n"
    "5. Responda em portugues do Brasil, direto, no maximo 8 linhas."
)


def _texto_do_chunk(r: Dict[str, Any]) -> str:
    for k in ("content", "text", "chunk_text", "page_content"):
        v = (r or {}).get(k)
        if v:
            return str(v)
    return str((r or {}).get("metadata", {}).get("text") or "")


def buscar(search, company: str, pergunta: str, namespace, cota: int) -> List[Dict]:
    """Uma ida ao Qdrant, com o filtro do braco. Mesma funcao da producao."""
    from app.services.knowledge_scope import (
        build_global_search_kwargs, seguradora_da_pergunta)

    if not namespace or cota <= 0:
        return []

    dense = search.embeddings.embed_query(pergunta)
    try:
        sparse = list(search.sparse_model.embed([pergunta]))[0]
    except Exception:  # noqa: BLE001
        sparse = None

    da_pergunta = seguradora_da_pergunta(pergunta)
    faixas = ([["normative"], ["cards", "canon"]] if namespace == "AMBOS"
              else [list(namespace)])
    por_faixa = max(1, cota // len(faixas))

    saida: List[Dict] = []
    for faixa in faixas:
        try:
            r = search.qdrant.search_similar(
                company_id=company, query_embedding=dense,
                sparse_embedding=sparse, top_k=por_faixa, score_threshold=0.0,
                **build_global_search_kwargs(carrier_slug=da_pergunta,
                                             namespace=faixa))
            saida.extend(r or [])
        except Exception as exc:  # noqa: BLE001
            print("    ⚠️ busca %s falhou (%s: %s)"
                  % ("+".join(faixa), type(exc).__name__, exc))
    return saida


def responder(llm, pergunta: str, chunks: List[Dict]) -> str:
    from langchain_core.messages import HumanMessage, SystemMessage

    if chunks:
        partes = []
        for i, c in enumerate(chunks, 1):
            ns = (c.get("namespace") or "?")
            partes.append("[%d · %s] %s" % (i, ns, _texto_do_chunk(c)[:1200]))
        usuario = ("TRECHOS DE REFERENCIA:\n%s\n\nPERGUNTA: %s"
                   % ("\n\n".join(partes), pergunta))
    else:
        usuario = "PERGUNTA: %s\n\n(Nenhum trecho de referencia disponivel.)" % pergunta

    r = llm.invoke([SystemMessage(content=SISTEMA), HumanMessage(content=usuario)])
    return (getattr(r, "content", "") or "").strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limite", type=int, default=0,
                    help="so as N primeiras perguntas (para conferir antes)")
    ap.add_argument("--modelo", default="gpt-4o-mini")
    ap.add_argument("--saida", default=SAIDA)
    args = ap.parse_args()

    if not os.path.exists(PERGUNTAS):
        print("Nao achei %s" % PERGUNTAS)
        return 1
    with open(PERGUNTAS, encoding="utf-8") as f:
        banco = json.load(f)
    perguntas = banco.get("perguntas") or []
    if args.limite:
        perguntas = perguntas[:args.limite]
    if not perguntas:
        print("Nenhuma pergunta no arquivo.")
        return 1

    try:
        from langchain_openai import ChatOpenAI
        from app.core.config import settings
        from app.services.search_service import SearchService
    except Exception as exc:  # noqa: BLE001
        print("Nao consegui carregar o app (%s: %s)." % (type(exc).__name__, exc))
        print("Este comando roda DENTRO do conteiner: cd /app && python "
              "scripts/acervo/medir_o_rag.py")
        return 1

    company = (os.getenv("GLOBAL_KNOWLEDGE_COMPANY_ID") or "").strip() \
        or "autobrokers-global"
    search = SearchService()
    llm = ChatOpenAI(model=args.modelo, temperature=0,
                     api_key=settings.OPENAI_API_KEY)

    print("=" * 72)
    print("MEDIR O RAG — %d perguntas × %d bracos = %d respostas"
          % (len(perguntas), len(BRACOS), len(perguntas) * len(BRACOS)))
    print("=" * 72)

    linhas: List[Dict[str, Any]] = []
    comeco = time.time()
    for n, p in enumerate(perguntas, 1):
        print("\n[%d/%d] %s · %s" % (n, len(perguntas), p.get("id"),
                                     (p.get("pergunta") or "")[:64]))
        for rotulo, nome, namespace, cota in BRACOS:
            t0 = time.time()
            try:
                chunks = buscar(search, company, p["pergunta"], namespace, cota)
                texto = responder(llm, p["pergunta"], chunks)
                erro = None
            except Exception as exc:  # noqa: BLE001
                chunks, texto, erro = [], "", "%s: %s" % (type(exc).__name__, exc)
                print("    ⛔ %s falhou — %s" % (rotulo, erro))
            linhas.append({
                "id": p.get("id"), "braco": rotulo, "config": nome,
                "pergunta": p.get("pergunta"), "resposta": texto,
                "erro": erro,
                "trechos_recuperados": len(chunks),
                # de que namespace veio cada trecho — para conferir depois que
                # o braco B recebeu mesmo so contrato, e o C so carta
                "namespaces": sorted({str(c.get("namespace") or "?")
                                      for c in chunks}),
                "seguradoras_nos_trechos": sorted(
                    {str(c.get("insurer_key")) for c in chunks
                     if c.get("insurer_key")}),
                "segundos": round(time.time() - t0, 1),
            })
            print("    %s %-18s %d trecho(s) · %d chars · %.1fs"
                  % (rotulo, nome, len(chunks), len(texto),
                     time.time() - t0))

    os.makedirs(os.path.dirname(args.saida), exist_ok=True)
    with open(args.saida, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"versao": banco.get("versao"), "modelo": args.modelo,
                   "perguntas": len(perguntas), "respostas": linhas},
                  f, ensure_ascii=False, indent=1)

    falhas = sum(1 for x in linhas if x["erro"])
    vazias = sum(1 for x in linhas if not x["erro"] and not x["resposta"])
    print("\n" + "=" * 72)
    print("  respostas geradas : %d" % len(linhas))
    print("  falhas            : %d" % falhas)
    print("  vazias            : %d" % vazias)
    print("  tempo             : %.0f s" % (time.time() - comeco))
    print("  arquivo           : %s" % args.saida)

    # CONTROLE: o braco B tem de ter recebido SO contrato, e o C SO carta. Se
    # os dois virem tudo, os quatro bracos sao o mesmo experimento repetido —
    # e o teste inteiro nao mede nada.
    def _ns(braco):
        return sorted({n for x in linhas if x["braco"] == braco
                       for n in x["namespaces"]})
    print("-" * 72)
    print("  CONTROLE B (so contrato) viu: %s" % (_ns("B") or "nada"))
    print("  CONTROLE C (so cartas)   viu: %s" % (_ns("C") or "nada"))
    print("  CONTROLE A (sem rag)     viu: %s" % (_ns("A") or "nada"))
    if _ns("B") == _ns("C"):
        print("  ⛔ B e C receberam o MESMO material — o filtro de namespace "
              "nao esta separando, e a comparacao nao vale.")
    print("=" * 72)
    print("\nMande o arquivo `respostas.json` — o julgamento acontece fora "
          "daqui,\ncom as respostas embaralhadas e sem dizer de que braco "
          "cada uma veio.")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
