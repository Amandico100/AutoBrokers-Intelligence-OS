#!/usr/bin/env python3
"""Publica no RAG as cartas destiladas das Condições Gerais — com lastro.

O QUE ESTE SCRIPT FAZ
=====================
`coletar_seguradora.py` traz o PDF vigente da SUSEP, corta em pedaços e indexa
o CONTRATO. Isso responde "o que a apólice diz", em linguagem de apólice.

Um subagente Opus 5 lê esses pedaços e escreve CARTAS: a mesma regra em
português de WhatsApp, uma ideia por carta. Este script pega as cartas prontas
e as publica — no banco e no índice.

    PDF vigente → pedaços (contrato)  → namespace `normative`
                → cartas (destilado)  → namespace `cards`      ← aqui

Os dois convivem de propósito (SPEC-070 §6): a carta responde rápido e o
contrato prova. `knowledge_scope.COTA_FINAL` reserva vaga para cada um.

O QUE ESTE SCRIPT **NÃO** FAZ
=============================
Não destila. Destilar é trabalho de leitura, não de código — e é feito por
subagente com as 8 regras da SPEC-070 §10. Este script transporta e carimba.

POR QUE A PROCEDÊNCIA IMPORTA
=============================
📊 Em 08/08/2026, 12 dos 13 documentos do acervo eram versões REVOGADAS — o
condomínio da Porto era o de 2012. As cartas que saíssem dali seriam
convincentes e erradas, e nada no índice permitiria descobrir de onde vieram.

Por isso toda carta daqui grava três campos que a carta de conversa não tem:

    source_document_id   qual contrato
    source_version_id    qual VERSÃO do contrato
    source_unit_id       qual trecho, exatamente

E é o que torna possível a regra do §3.2.1: quando a versão é substituída, as
cartas dela saem do índice junto — em vez de continuar respondendo com a
redação de 2012 pelo resto da vida.

⚠️ CAMINHO DENTRO DO CONTÊINER
==============================
O Dockerfile faz `WORKDIR /app` e `COPY . .` de dentro de `backend/`. Então:

    no repositório:  backend/scripts/acervo/publicar_cartas.py
    no contêiner:           scripts/acervo/publicar_cartas.py

USO
===
    python scripts/acervo/publicar_cartas.py --seguradora porto --seco
    python scripts/acervo/publicar_cartas.py --seguradora porto
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

# Qualquer letra acentuada do português. Ver `_conferir`.
_RE_ACENTO = re.compile(r"[áàâãéêíóôõúüçÁÀÂÃÉÊÍÓÔÕÚÜÇ]")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

FACETAS = {"escopo", "exclusao", "limite", "franquia", "prazo", "documento", "definicao"}

# Uma carta é uma ideia. Menos que isso não afirma nada; mais que isso é o
# pedaço do contrato copiado, e para isso já existe o namespace `normative`.
MIN_CARACTERES = 40
MAX_CARACTERES = 900

# 🔴 EXCETO A LISTA DE DOCUMENTOS, QUE É LONGA PORQUE A EXIGÊNCIA É LONGA.
#
# 📊 Achado no ensaio seco da Porto: 2 das 1.121 cartas foram recusadas por
# tamanho, e as duas são `documento` — o que a fiança exige para acionar danos
# ao imóvel (940) e o que o vida exige para invalidez por acidente (952).
#
# O teto de 900 existe para impedir que alguém cole o pedaço do contrato e
# chame de carta. Uma lista de documentos não é isso: é **uma** ideia — "o que
# você precisa juntar" — e ela só serve inteira. Cortada ao meio, manda a
# família reunir metade dos papéis e descobrir o resto na recusa.
#
# `documento` é a única faceta com essa natureza. `escopo` e `exclusao` longos
# continuam sendo contrato copiado, e continuam recusados.
MAX_CARACTERES_DOCUMENTO = 1200


def _diretorio_das_cartas(seguradora: str) -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "cartas", seguradora)


def _documento_do_unit_id(unit_id: str) -> Optional[str]:
    """`norm-<document_id>-v2#0042` → `norm-<document_id>-v2`.

    O `unit_id` carrega o `qdrant_doc_id` inteiro antes do `#`, e é assim que a
    carta encontra sozinha o documento de onde saiu — sem o subagente precisar
    saber o que é um UUID de versão.
    """
    if not unit_id or "#" not in unit_id:
        return None
    return unit_id.split("#", 1)[0]


def _mapa_das_versoes(seguradora: str) -> Dict[str, Dict[str, Any]]:
    """qdrant_doc_id → {document_id, version_id, product_line}, só das VIGENTES.

    🔴 `superseded_at is null` não é detalhe. Se uma carta apontar para uma
    versão já substituída, ela é conhecimento vencido entrando como novo — o
    defeito exato que a SPEC-070 existe para impedir. Melhor recusar a carta.
    """
    from app.core.database import get_supabase_client

    db = get_supabase_client()
    docs = (db.client.table("normative_documents")
            .select("id, product_line").eq("insurer_key", seguradora).execute().data or [])
    por_documento = {d["id"]: d.get("product_line") for d in docs}
    if not por_documento:
        return {}

    versoes = (db.client.table("normative_document_versions")
               .select("id, document_id, qdrant_doc_id, superseded_at")
               .in_("document_id", list(por_documento)).is_("superseded_at", "null")
               .execute().data or [])
    mapa: Dict[str, Dict[str, Any]] = {}
    for v in versoes:
        chave = v.get("qdrant_doc_id")
        if not chave:
            continue
        mapa[chave] = {"document_id": v["document_id"], "version_id": v["id"],
                       "product_line": por_documento.get(v["document_id"])}
    return mapa


def _ler_cartas(seguradora: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    pasta = _diretorio_das_cartas(seguradora)
    arquivos = sorted(glob.glob(os.path.join(pasta, "*_CARTAS.jsonl")))
    if not arquivos:
        return [], [f"nenhum arquivo *_CARTAS.jsonl em {pasta}"]

    cartas: List[Dict[str, Any]] = []
    queixas: List[str] = []
    for caminho in arquivos:
        nome = os.path.basename(caminho)
        with open(caminho, encoding="utf-8") as arquivo:
            for numero, linha in enumerate(arquivo, 1):
                linha = linha.strip()
                if not linha:
                    continue
                try:
                    d = json.loads(linha)
                except Exception as exc:  # noqa: BLE001
                    queixas.append(f"{nome}:{numero} JSON inválido ({type(exc).__name__})")
                    continue
                d["_arquivo"] = nome
                d["_linha"] = numero
                cartas.append(d)
    return cartas, queixas


def _conferir(carta: Dict[str, Any], versoes: Dict[str, Dict[str, Any]]) -> Optional[str]:
    """Devolve o MOTIVO da recusa, ou None se a carta pode ser publicada."""
    texto = " ".join(str(carta.get("texto") or "").split())
    if not texto:
        return "sem texto"
    if len(texto) < MIN_CARACTERES:
        return f"curta demais ({len(texto)} caracteres)"

    # 🔴 CARTA LONGA EM PORTUGUÊS SEM UM ÚNICO ACENTO É ENCODING QUEBRADO.
    #
    # 📊 Achado no LOTE 2 (Allianz), 09/08/2026: quatro destiladores gravaram o
    # arquivo por heredoc de shell. O terminal deste ambiente usa cp1252, e o
    # texto chegou assim:
    #
    #     "No Allianz Condominio a cobertura Basica de Incendio e obrigatoria"
    #
    # Ninguém percebe lendo rápido — a frase continua compreensível. Mas o RAG
    # percebe: a busca é híbrida e o BM25 casa por TERMO EXATO. `condomínio`
    # digitado pelo corretor não casa com `condominio` gravado na carta, e a
    # resposta certa deixa de aparecer sem que nada acuse.
    #
    # A régua é o TAMANHO: uma carta de 200+ caracteres sobre seguro sempre tem
    # `apólice`, `condomínio`, `veículo`, `indenização`, `é`, `não`, `até`.
    # Zero acentos nesse tamanho não é estilo, é defeito. Abaixo disso pode ser
    # uma frase curta legítima sem acento nenhum, e aí não acuso.
    if len(texto) >= 200 and not _RE_ACENTO.search(texto):
        return ("sem nenhum acento em %d caracteres — encoding quebrado "
                "(grave com Write/UTF-8, não por heredoc de shell)" % len(texto))

    faceta = str(carta.get("faceta") or "").strip()
    if faceta not in FACETAS:
        return f"faceta desconhecida: {faceta!r}"

    teto = MAX_CARACTERES_DOCUMENTO if faceta == "documento" else MAX_CARACTERES
    if len(texto) > teto:
        return f"longa demais ({len(texto)} caracteres) — é pedaço de contrato, não carta"

    unit_id = str(carta.get("unit_id_origem") or "").strip()
    if not unit_id:
        return "sem unit_id_origem — a carta não sabe voltar ao contrato"
    doc = _documento_do_unit_id(unit_id)
    if not doc:
        return f"unit_id_origem malformado: {unit_id!r}"
    if doc not in versoes:
        # Ou o subagente inventou o endereço, ou a versão já foi substituída
        # desde a destilação. Os dois casos publicam conhecimento sem lastro.
        return f"unit_id_origem não aponta para versão VIGENTE: {doc}"

    # 🔴 A verificação de PII é a mesma do destilador de conversa. Não porque
    # se espere nome de pessoa numa condição geral — mas porque um caminho de
    # publicação sem essa rede é um caminho por onde ela pode entrar depois.
    #
    # `valor_e_conhecimento=True` é a ÚNICA diferença, e ela é justificada pela
    # origem: este script só lê PDF baixado do registro da SUSEP, onde a cifra
    # descreve o produto. 📊 Sem isso, 36 das 716 cartas da Porto (5,0%) seriam
    # recusadas — e são justamente as de `limite`, as mais consultadas.
    from app.services.attendance_distiller import _card_pii_clean

    if not _card_pii_clean(texto, valor_e_conhecimento=True):
        return "a verificação de dado pessoal recusou o texto"
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Publica as cartas destiladas do acervo")
    ap.add_argument("--seguradora", required=True, help="chave da seguradora, ex.: porto")
    ap.add_argument("--seco", action="store_true",
                    help="confere tudo e NÃO grava nada — sempre rode isto antes")
    args = ap.parse_args()

    seguradora = args.seguradora.strip().lower()
    print("=" * 72)
    print(f"PUBLICAR CARTAS DO ACERVO — {seguradora.upper()}"
          + ("   [ENSAIO SECO — nada será gravado]" if args.seco else ""))
    print("=" * 72)

    versoes = _mapa_das_versoes(seguradora)
    if not versoes:
        print(f"  X   nenhuma versão VIGENTE de {seguradora} no banco — rode "
              f"`coletar_seguradora.py` antes")
        return 1
    print(f"  versões vigentes no banco: {len(versoes)}")
    for chave, v in sorted(versoes.items(), key=lambda kv: kv[1]["product_line"] or ""):
        print(f"    {v['product_line']:<14} {chave}")

    cartas, queixas = _ler_cartas(seguradora)
    for q in queixas:
        print(f"  X   {q}")
    if not cartas:
        return 1
    print(f"\n  cartas lidas: {len(cartas)}")

    from app.services.curadoria_cartas import assunto_da_carta

    aprovadas: List[Dict[str, Any]] = []
    recusadas: Dict[str, int] = {}
    vistos: set = set()
    repetidas = 0

    for carta in cartas:
        motivo = _conferir(carta, versoes)
        if motivo:
            recusadas[motivo.split("(")[0].strip()] = recusadas.get(
                motivo.split("(")[0].strip(), 0) + 1
            print(f"  X   {carta['_arquivo']}:{carta['_linha']} — {motivo}")
            continue

        texto = " ".join(str(carta["texto"]).split())
        card_hash = hashlib.md5(texto.lower().encode("utf-8")).hexdigest()
        if card_hash in vistos:
            repetidas += 1
            continue
        vistos.add(card_hash)

        unit_id = str(carta["unit_id_origem"]).strip()
        v = versoes[_documento_do_unit_id(unit_id)]
        aprovadas.append({
            "card_hash": card_hash,
            "card_text": texto,
            "category": assunto_da_carta(texto),
            "ramo": v["product_line"],
            "insurer_key": seguradora,
            "status": "published",
            # A procedência fica no banco E no `pii_check`, que é o campo que
            # já guarda "como esta carta foi verificada". `origem: acervo`
            # distingue no olho a carta que veio de contrato da que veio de
            # conversa — elas têm confiabilidades diferentes.
            "pii_check": {"deterministic": True, "origem": "acervo",
                          "faceta": carta["faceta"]},
            "source_count": 1,
            "source_document_id": v["document_id"],
            "source_version_id": v["version_id"],
            "source_unit_id": unit_id,
            "_faceta": carta["faceta"],
        })

    print(f"\n  aprovadas: {len(aprovadas)}   repetidas descartadas: {repetidas}")
    if recusadas:
        print("  recusadas por motivo:")
        for motivo, quantas in sorted(recusadas.items(), key=lambda kv: -kv[1]):
            print(f"    {quantas:>4}  {motivo}")

    porcentagem = 100.0 * len(aprovadas) / max(len(cartas), 1)
    print(f"  aproveitamento: {porcentagem:.1f}%")

    if args.seco:
        print("\n  ENSAIO SECO — nada foi gravado. Rode sem `--seco` para publicar.")
        return 0 if aprovadas else 1

    # ------------------------------------------------------------------ #
    from app.core.database import get_supabase_client
    from app.services.attendance_distiller import publish_card_sync

    db = get_supabase_client()
    gravadas = 0
    indexadas = 0
    falhas: List[str] = []

    print("\n  gravando e publicando…")
    for i, linha in enumerate(aprovadas, 1):
        faceta = linha.pop("_faceta")
        try:
            res = (db.client.table("knowledge_cards")
                   .upsert(linha, on_conflict="card_hash").execute())
            card_id = (res.data or [{}])[0].get("id")
        except Exception as exc:  # noqa: BLE001
            falhas.append(f"banco: {type(exc).__name__} — {linha['card_text'][:60]}")
            continue
        if not card_id:
            falhas.append(f"sem id de volta — {linha['card_text'][:60]}")
            continue
        gravadas += 1

        # 🔴 O índice só recebe o que o banco JÁ aceitou. Ao contrário, uma
        # falha no banco deixaria o vetor no Qdrant sem dono — impossível de
        # despublicar depois, porque `despublicar_carta_sync` procura por
        # `card-<id>` e não haveria id.
        ok = publish_card_sync({"id": card_id, "card_text": linha["card_text"],
                                "insurer_key": linha["insurer_key"], "ramo": linha["ramo"],
                                "category": linha["category"],
                                "source_unit_id": linha["source_unit_id"],
                                "faceta": faceta})
        if ok:
            indexadas += 1
        else:
            falhas.append(f"índice recusou — {linha['card_text'][:60]}")
            # O banco diz `published` e o índice não tem o vetor: é a mentira
            # que o §12.1 manda consertar no campo, não no texto.
            db.client.table("knowledge_cards").update(
                {"status": "qdrant_pendente"}).eq("id", card_id).execute()

        if i % 50 == 0:
            print(f"    {i}/{len(aprovadas)}  banco {gravadas}  índice {indexadas}")

    print("\n" + "=" * 72)
    print(f"  gravadas no banco : {gravadas}")
    print(f"  publicadas no RAG : {indexadas}")
    if falhas:
        print(f"  FALHAS            : {len(falhas)}")
        for f in falhas[:10]:
            print(f"    - {f}")
        if len(falhas) > 10:
            print(f"    … e mais {len(falhas) - 10}")
    print("=" * 72)
    return 0 if indexadas and not falhas else 1


if __name__ == "__main__":
    sys.exit(main())
