# -*- coding: utf-8 -*-
"""Carrega na base de planos o que um LEITOR (agente do plano, não a API) escreveu lendo as condições gerais.

SPEC-EXTRA-001.5.2 · 20/09/2026. Rodar de dentro de `backend/`:

```
PYTHONIOENCODING=utf-8 python scripts/carregar_destilacao_de_planos.py scripts/destilacao_planos/tokio.json            # ENSAIO
PYTHONIOENCODING=utf-8 python scripts/carregar_destilacao_de_planos.py scripts/destilacao_planos/*.json --gravar      # vira `proposto`
PYTHONIOENCODING=utf-8 python scripts/carregar_destilacao_de_planos.py ... --gravar --publicar --revisor <uuid> \\
        --reprovadas scripts/destilacao_planos/_reprovadas.json                                                        # publica o que passou
```

🔴 POR QUE EXISTE: o extrator do produto chama a API da Anthropic (crédito próprio) e, medido em 20/09, acha a cláusula
de planos por texto em 4 de 27 documentos. Um leitor lendo a página acerta o que o regex não acerta — foi assim que o
gabarito de 19/09 nasceu. Este script é o cano desse leitor.

⛔ NÃO é um segundo escritor nem um segundo publicador (CLAUDE.md §5): quem escreve é `BASE.propor_plano`/`propor_servico`,
quem confere é `assistance_plans_conferente.conferir_linha`, quem publica é `BASE.publicar_servico` (com revisor). Este
arquivo lê JSON, FILTRA, chama e conta.

🔴 AS TRÊS PENEIRAS, nesta ordem — e nenhuma promove nada sozinha:
  1. MÁQUINA  o `trecho` tem de existir na PÁGINA citada (o conferente de produção, mesma régua). Não existe → a linha NÃO entra.
  2. LEITOR 2 um segundo agente, que não escreveu, confere linha a linha e devolve as REPROVADAS (`--reprovadas`). Reprovada não publica.
     📊 20/09: o parecer do conferente fica GRAVADO ao lado da linha mas NÃO barra a publicação — em 118 linhas certas de HDI/Yelum ele
     disse DIVERGE em 72 (implica com nome de produto e com tabela). As que ele marca em `plano`/`coberto` vão ao LEITOR 2 com prioridade.
  3. GENTE    `--publicar` exige `--revisor`: o uuid da pessoa que responde pelas linhas. Sem ele, recusa antes do banco.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from collections import Counter
from typing import Any, Dict, List, Optional

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))

try:  # o mesmo .env dos outros scripts
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(AQUI), ".env"))
except Exception:  # noqa: BLE001
    pass

from app.services.knowledge import assistance_plans_base as BASE  # noqa: E402
from app.services.knowledge import assistance_plans_conferente as CONF  # noqa: E402
from app.services.knowledge import assistance_plans_extractor as X  # noqa: E402


def chave_da_linha(doc: Dict[str, Any], s: Dict[str, Any]) -> str:
    """A identidade de uma linha do JSON — é o que o LEITOR 2 usa para reprovar."""
    return "%s|%s|%s" % (str(doc.get("doc8") or str(doc.get("documento_id"))[:8]), s.get("plano"), s.get("servico"))


def paginas_do_documento(documento_id: str, pasta_do_acervo: Optional[str], db: Any, minio: Any) -> Dict[int, str]:
    """As páginas — do despejo local (o MESMO `BASE.texto_das_paginas`, já rodado) ou do MinIO."""
    if pasta_do_acervo:
        pasta = os.path.join(pasta_do_acervo, str(documento_id)[:8])
        if os.path.isdir(pasta):
            paginas = {}
            for nome in os.listdir(pasta):
                if nome.startswith("p") and nome.endswith(".txt"):
                    paginas[int(nome[1:-4])] = open(os.path.join(pasta, nome), encoding="utf-8").read()
            if paginas:
                return paginas
    lidas = BASE.texto_das_paginas(documento_id, db=db, minio=minio)
    return {int(k): v for k, v in (lidas.paginas or {}).items()} if lidas.ok else {}


def niveis(planos: List[Dict[str, Any]]) -> Dict[str, int]:
    """`nivel` é obrigatório e único por produto. Declarado vence; o resto ocupa os números livres, na ordem do documento."""
    usados, saida = set(), {}
    for p in planos:
        n = p.get("nivel")
        if isinstance(n, int) and n >= 1 and n not in usados:
            saida[p["nome"]] = n
            usados.add(n)
    livre = 1
    for p in planos:
        if p["nome"] in saida:
            continue
        while livre in usados:
            livre += 1
        saida[p["nome"]] = livre
        usados.add(livre)
    return saida


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("arquivos", nargs="+")
    ap.add_argument("--acervo", default=os.environ.get("ACERVO_DESPEJADO"), help="pasta do despejo página a página (opcional)")
    ap.add_argument("--gravar", action="store_true")
    ap.add_argument("--publicar", action="store_true")
    ap.add_argument("--revisor")
    ap.add_argument("--reprovadas", help="JSON do LEITOR 2: {\"reprovadas\": [{\"chave\": \"doc8|plano|servico\", \"motivo\": \"...\"}]}")
    ap.add_argument("--apenas", help="só as linhas cuja chave `doc8|plano|servico` contém este texto (recarga dirigida)")
    ap.add_argument("--relatorio", default=os.path.join(AQUI, "destilacao_planos", "_resultado.json"))
    a = ap.parse_args(argv)

    if a.publicar and not (a.gravar and a.revisor):
        print("⛔ --publicar exige --gravar e --revisor <uuid>: sem gente que responda pela linha, nada sobe.")
        return 2
    reprovadas = {}
    if a.reprovadas and os.path.exists(a.reprovadas):
        for r in json.load(open(a.reprovadas, encoding="utf-8")).get("reprovadas", []):
            reprovadas[str(r.get("chave"))] = str(r.get("motivo") or "")
    if a.publicar and not a.reprovadas:
        print("⛔ --publicar exige --reprovadas: a 2ª peneira (o leitor que NÃO escreveu) é obrigatória.")
        return 2

    db = X._cliente()
    minio = None
    conta = Counter()
    resultado: List[Dict[str, Any]] = []

    caminhos: List[str] = []
    for padrao in a.arquivos:
        caminhos.extend(sorted(glob.glob(padrao)) or [padrao])
    for caminho in caminhos:
        if os.path.basename(caminho).startswith("_"):
            continue
        dados = json.load(open(caminho, encoding="utf-8"))
        for doc in dados.get("documentos", []):
            did = str(doc["documento_id"])
            linha_doc = (db.table("normative_documents").select(
                "id, insurer_key, insurer_name, product_line, title, susep_process, content_hash, effective_from, created_at"
            ).eq("id", did).execute().data or [None])[0]
            if not linha_doc:
                conta["documento_desconhecido"] += 1
                print("  ⚠ documento fora da base normativa: %s" % did[:8])
                continue
            if minio is None and not a.acervo:
                from app.services.minio_service import get_minio_service

                minio = X._MinioComCache(get_minio_service())
            paginas = paginas_do_documento(did, a.acervo, db, minio)
            if not paginas:
                conta["documento_sem_paginas"] += 1
                continue
            vigencia = X.vigencia_do_documento(did, linha_doc, db)
            if not vigencia:
                conta["documento_sem_vigencia"] += 1
                continue
            planos = [p for p in doc.get("planos", []) if p.get("nome")]
            nomes = [p["nome"] for p in planos]
            nivel_de = niveis(planos)
            produto = str(doc.get("produto") or linha_doc.get("title") or "")[:120]
            plano_id: Dict[str, str] = {}

            for s in doc.get("servicos", []):
                chave = chave_da_linha(doc, s)
                if a.apenas and a.apenas not in chave:
                    continue
                conta["lidas"] += 1
                reg = {"chave": chave, "insurer": linha_doc.get("insurer_key"), "ramo": linha_doc.get("product_line"),
                       "produto": produto, "plano": s.get("plano"), "servico": s.get("servico"), "coberto": s.get("coberto"),
                       "pagina": s.get("pagina")}
                resultado.append(reg)
                if s.get("plano") not in nomes:
                    reg["estado"] = "descartada:plano_fora_da_lista"
                    conta[reg["estado"]] += 1
                    continue
                # ① MÁQUINA: o trecho existe NAQUELA página? (o conferente de produção, a mesma régua)
                para_conferir = dict(s, produto=produto)
                try:
                    v = CONF.conferir_linha(para_conferir, paginas, nomes)
                    campos, motivos, veredito = dict(v.campos), list(v.motivos), v.veredito
                except Exception as exc:  # noqa: BLE001
                    campos, motivos, veredito = {}, ["o conferente falhou: %s" % type(exc).__name__], "NAO_CONSEGUI"
                reg.update(veredito=veredito, campos=campos, motivos=motivos[:3])
                if campos.get("trecho") != "ok" or campos.get("pagina") == "diverge":
                    reg["estado"] = "descartada:trecho_nao_esta_na_pagina"
                    conta[reg["estado"]] += 1
                    continue
                if not a.gravar:
                    reg["estado"] = "ensaio:entraria"
                    conta[reg["estado"]] += 1
                    continue
                try:
                    if s["plano"] not in plano_id:
                        p = next(x for x in planos if x["nome"] == s["plano"])
                        # 📊 20/09: 3 planos bateram na chave única (seguradora, ramo, produto, NÍVEL, vigência) contra um plano
                        # que já existia. O nível pedido vale se estiver livre NO BANCO; senão, o próximo livre acima do maior.
                        ocupados = {int(r["nivel"]) for r in (db.table(BASE.TABELA_PLANOS).select("nivel")
                                    .eq("insurer_key", str(linha_doc.get("insurer_key") or "")).eq("ramo", str(linha_doc.get("product_line") or ""))
                                    .eq("produto", produto).eq("vigencia_inicio", vigencia).execute().data or []) if r.get("nivel")}
                        if int(nivel_de[s["plano"]]) in ocupados:
                            nivel_de[s["plano"]] = max(ocupados | set(nivel_de.values())) + 1
                        linha_plano = BASE.propor_plano(
                            insurer=str(linha_doc.get("insurer_key") or ""), ramo=str(linha_doc.get("product_line") or ""),
                            produto=produto, plano=s["plano"], nivel=int(nivel_de[s["plano"]]), vigencia_inicio=vigencia,
                            documento_id=did, pagina=int(p.get("pagina") or s["pagina"]),
                            content_hash=str(linha_doc.get("content_hash") or ""), confianca="alta",
                            susep_process=linha_doc.get("susep_process"), db=db)
                        plano_id[s["plano"]] = str(linha_plano.get("id"))
                    un = s.get("limite_unidade") if s.get("limite_unidade") in BASE.UNIDADES else None
                    linha = BASE.propor_servico(
                        plano_id=plano_id[s["plano"]], servico=str(s["servico"]), coberto=str(s["coberto"]),
                        documento_id=did, pagina=int(s["pagina"]), trecho=str(s["trecho"]),
                        limite_valor=s.get("limite_valor") if un else None, limite_unidade=un,
                        limite_texto=s.get("limite_texto"), carencia_dias=s.get("carencia_dias"), condicao=s.get("condicao"),
                        confianca=s.get("confianca") if s.get("confianca") in BASE.CONFIANCAS else "media",
                        caminho_da_clausula="%s › %s" % (produto, s["plano"]), db=db)
                    sid = str(linha.get("id"))
                    BASE.anotar_conferencia(sid, veredito, campos, motivos, s.get("pagina"), db=db)
                    reg.update(servico_id=sid, estado="proposto")
                    conta["proposto"] += 1
                except Exception as exc:  # noqa: BLE001 — o contrato e o banco também recusam, e é de propósito
                    reg["estado"] = "recusada_pelo_contrato:%s" % type(exc).__name__
                    reg["erro"] = str(exc)[:160]
                    conta[reg["estado"]] += 1
                    continue
                # ② LEITOR 2 e ③ GENTE
                if a.publicar:
                    if chave in reprovadas:
                        reg["estado"] = "proposto:reprovada_pelo_leitor_2"
                        reg["motivo_do_leitor_2"] = reprovadas[chave]
                        conta[reg["estado"]] += 1
                    else:
                        try:
                            BASE.publicar_servico(sid, a.revisor, db=db)
                            reg["estado"] = "publicado"
                            conta["publicado"] += 1
                        except Exception as exc:  # noqa: BLE001
                            reg["estado"] = "proposto:publicacao_recusada:%s" % type(exc).__name__
                            reg["erro"] = str(exc)[:160]
                            conta[reg["estado"]] += 1

    os.makedirs(os.path.dirname(a.relatorio), exist_ok=True)
    json.dump({"conta": dict(conta), "linhas": resultado}, open(a.relatorio, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n  %s" % ("GRAVADO" if a.gravar else "ENSAIO — nada foi escrito"))
    for k, n in sorted(conta.items(), key=lambda kv: -kv[1]):
        print("    %-48s %d" % (k, n))
    print("  relatório: %s" % a.relatorio)
    return 0


if __name__ == "__main__":
    sys.exit(main())
