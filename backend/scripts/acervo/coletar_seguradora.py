# -*- coding: utf-8 -*-
"""Coleta o acervo VIGENTE de uma seguradora inteira. SPEC-070 §9, passos 1 a 6.

    NA SUA MAQUINA (so mostra; recusa gravar, e diz por que):
        python backend/scripts/acervo/coletar_seguradora.py --seguradora porto
        python backend/scripts/acervo/coletar_seguradora.py --seguradora porto --diagnostico

    NO CONTEINER de producao, que e o unico lugar onde isto grava:
        cd /app && python scripts/acervo/coletar_seguradora.py --seguradora porto
        cd /app && python scripts/acervo/coletar_seguradora.py --seguradora porto --aplicar

⚠️ O caminho MUDA entre os dois, e a diferenca ja custou uma ida ao terminal em
08/08/2026. `backend/Dockerfile` faz `WORKDIR /app` + `COPY . .` a partir de
`backend/`: o conteudo de `backend/` **vira** o `/app`, e la dentro nao existe
pasta chamada `backend`. Um comando com `backend/` no meio devolve
`No such file or directory` — que parece deploy faltando e nao e.


POR QUE ISTO PRECISA EXISTIR
============================
O LOTE 0 construiu tres pecas e nao ligou nenhuma:

    susep_rep2.py       pergunta ao registro oficial qual versao vale hoje
    insurance_corpus.py extrai, limpa, corta por secao, etiqueta e indexa
    acervo_arquivo.py   guarda o PDF e o texto no MinIO

Cada uma sabe fazer a sua parte e nenhuma sabe a ordem. Este script e a ordem.

📊 O numero que justifica tudo (SPEC-070 §1): **12 de 13 documentos indexados
sao versoes revogadas**. O condominio da Porto e de dezembro/2012 e o vigente e
de dezembro/2025. O agente responde a partir do texto velho com a autoridade de
um documento oficial, e ninguem percebe: um contrato revogado tem o logotipo
certo, a linguagem certa e o numero de processo certo.


O QUE ELE FAZ, NA ORDEM DA §9
=============================
1. **Descobre os produtos** — catalogo OData da SUSEP, filtrado por `entnome` e
   pelos ramos de varejo. 📊 31.871 produtos no dump; 261 da Porto.
2. **Acha a versao vigente** de cada um, no REP2.
3. **Baixa o PDF** e guarda o original e o texto no MinIO.
4. **Extrai e parte** com o motor da §4 (PyMuPDF, limpeza, corte por secao,
   cabecalho por pedaco).
5. **Indexa** no Qdrant, `namespace: normative`, com o payload da §5.3 — e a
   versao anterior do mesmo produto sai do indice (D-Acervo-02) e continua no
   banco e no MinIO.
6. **Exporta os pedacos** para `.jsonl`, em pacotes, para os subagentes que
   escrevem as cartas.

Os passos 3 a 5 nao sao reimplementados aqui: quem os faz e
`InsuranceCorpusService.ingerir()`, que ja e o unico dono desse trabalho. O
CLAUDE.md §5 proibe motor paralelo, e com razao — dois caminhos de ingestao
divergiriam em silencio, e o silencioso e o que ninguem conserta.


🔴 A REGRA QUE NAO SE NEGOCIA — §3.2.1
======================================
    VIGENTE = situacao "Passivel de comercializacao"
              + versao com Data de Fim de Comercializacao VAZIA

O script imprime, para CADA documento, a ficha de conferencia da §3.2.1. **Se
qualquer linha nao puder ser preenchida com o que veio do registro oficial, o
documento NAO ENTRA.** Ele pula e registra, em vez de indexar com duvida.

E ha um caso em que a peca de baixo sabe escolher e este script NAO PODE
deixar: quando duas versoes estao com a Data de Fim vazia, `interpretar_consulta`
devolve a de inicio mais recente e escreve `2_versoes_em_aberto` no motivo. A
§3.2.1 item 3 e explicita — *"NAO ESCOLHA. Pare e registre `indeterminado`.
Duas vigentes e defeito da fonte, nao escolha sua."* Entao aqui isso e recusa.

    Um lote incompleto e honesto vale mais que um acervo que mente com
    confianca.


ONDE O PROGRESSO MORA — E POR QUE NAO E NUM ARQUIVO
====================================================
⚠️ 📊 08/08/2026: o arquivo de progresso do `reindexar_acervo.py` morreu num
deploy e custou **109 minutos** de retrabalho. Uma rodada reindexou 12.058 de
12.063 cartas; o EasyPanel recriou o conteiner; a rodada seguinte imprimiu
`ja reindexadas ...... 0` e refez tudo. Nao foi defeito do script — foi o lugar
errado para guardar a memoria: **um arquivo dentro de algo que e apagado por
desenho.**

Aqui o progresso nao precisa nem de coluna nova. Ele **ja e um fato do banco**:

    uma versao aberta (`superseded_at is null`) em
    `normative_document_versions` cujo `susep_version_id` e o id de download
    que a SUSEP acabou de devolver  ⇒  este documento ja foi coletado NESTA
    versao.

Isso e melhor que uma marca: uma marca pode dizer "feito" sobre um trabalho que
nao terminou. Esta condicao so existe se a linha da versao foi gravada, e a
linha da versao so e gravada depois de o indice aceitar os pedacos
(`insurance_corpus.ingerir`). Nenhum deploy apaga, e nenhuma retomada refaz o
que ja esta la.


CUSTO
=====
Embedding com `text-embedding-3-small`. 📊 Medido no CG144 da Porto (auto):
484 pedacos, 485.524 caracteres ≈ 137 mil tokens ≈ **US$ 0,003 por documento**.
O `--aplicar` imprime a estimativa e espera confirmacao antes de gastar.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

AQUI = Path(__file__).resolve()
BACKEND = AQUI.parents[2]
sys.path.insert(0, str(BACKEND))

PASTA_LOTES = AQUI.parent / "lotes"

# 150 pedacos por pacote. O numero saiu de uma medicao, nao de gosto.
#
# 📊 Ensaio real sobre o CG144 da Porto (auto, 484 pedacos, 08/08/2026): a
# linha do `.jsonl` tem 1.365 bytes em media e 1.294 de mediana. Com 150
# linhas os quatro pacotes sairam com
#
#     241 KB · 189 KB · 197 KB · 54 KB      💭 ≈ 67k · 52k · 55k · 15k tokens
#
# — cada um cabe numa leitura so do subagente e ainda sobra janela para ele
# escrever as cartas. O arquivo inteiro (660 KB, 💭 ~180k tokens) nao caberia.
# 📊 A campanha anterior usou 70 conversas por pacote pelo mesmo motivo, e
# conversa de atendimento e bem mais curta que clausula de contrato.
PEDACOS_POR_PACOTE = 150

CUSTO_POR_MILHAO = 0.02          # text-embedding-3-small
CHARS_POR_TOKEN = 3.55           # 📊 485.524 chars / ~137k tokens no CG144


# ---------------------------------------------------------------------------
# Quem e quem
# ---------------------------------------------------------------------------
#
# A chave da esquerda e o `insurer_key` — o mesmo vocabulario de
# `insurance_corpus.SEGURADORAS` e o mesmo que o filtro de busca casa na raiz
# do payload. Inventar um slug novo aqui esconderia o documento novo de toda
# pergunta feita sobre a companhia.
#
# ⚠️ O casamento com o catalogo e por SUBSTRING do `entnome`, e o script imprime
# os nomes que casaram antes de fazer qualquer coisa. Substring e barata e erra
# para os dois lados; o que a torna honesta e ser VISIVEL. `--entnome` manda
# mais que esta tabela quando ela errar.

SEGURADORAS: dict[str, tuple[str, tuple[str, ...]]] = {
    "porto": ("Porto Seguro", ("PORTO SEGURO",)),
    "allianz": ("Allianz Seguros", ("ALLIANZ",)),
    # Liberty virou Yelum em 2024; produto antigo continua registrado no nome
    # antigo, e as duas pistas apontam para a mesma companhia.
    "yelum": ("Yelum Seguradora", ("YELUM", "LIBERTY")),
    "hdi": ("HDI Seguros", ("HDI",)),
    "bradesco": ("Bradesco Seguros", ("BRADESCO",)),
    "tokio": ("Tokio Marine", ("TOKIO MARINE",)),
    "mapfre": ("Mapfre", ("MAPFRE",)),
    "azul": ("Azul Seguros", ("AZUL SEGUROS", "AZUL COMPANHIA")),
    "zurich": ("Zurich", ("ZURICH",)),
    "alfa": ("Alfa Seguradora", ("ALFA SEGURADORA",)),
    "sura": ("Sura", ("SURA",)),
    "suhai": ("Suhai Seguradora", ("SUHAI",)),
}

# 📊 O catalogo separa por `tipoproduto`, e a separacao e util: capitalizacao,
# previdencia e sobrevivencia (VGBL/PGBL) nao tem condicao geral de cobertura
# no sentido que o corretor pergunta. Da Porto, 92 dos 261 produtos sao disso.
TIPOS_DE_SEGURO = ("PLANO DE SEGURO DE DANOS", "PLANO DE SEGURO DE PESSOAS")

# O ramo vem numerado da SUSEP (§5.2) e e assim que ele e lido. A coluna da
# direita e o nosso `product_line`, que e o que a busca ja filtra — os dois
# convivem: o oficial vai para as notas e para o `.jsonl`, o nosso para o
# payload.
#
# ⚠️ `fianca` da SPEC §9 chega aqui como `garantia` porque e esse o valor que
# 📊 o documento de fianca locaticia da Porto ja tem em `normative_documents`.
# Trocar o vocabulario agora orfanaria o que esta indexado.
#
# 🔴 A terceira coluna existe por causa de um erro que a primeira rodada real
# cometeu na minha frente. `RISCOS DIVERSOS` sozinho parecia significar
# "equipamentos" — e 📊 no catálogo da Porto ele traz `CG Aluguel Garantido`,
# `CG Proteção Imobiliária II` e `CG RISCOS DIVERSOS EVENTOS`, que são seguro
# de aluguel, de imóvel e de evento. Os três entrariam no acervo etiquetados
# `equipamentos`, e a pergunta sobre o celular quebrado receberia a condição
# geral de um seguro de festa.
#
# 📊 O ramo que de fato identifica é `01 | RISCOS DIVERSOS` **com subramo
# EQUIPAMENTOS** — 110 produtos no dump inteiro. O subramo é obrigatório
# quando a terceira coluna não está vazia.
RAMOS_DE_VAREJO: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    ("auto", ("AUTOMÓVEL", "AUTOMOVEL", "COBERTURAS - AUTO", "CARTA VERDE"), ()),
    ("residencial", ("COMPREENSIVO RESIDENCIAL", "RESIDENCIAL"), ()),
    ("condominio", ("COMPREENSIVO CONDOMÍNIO", "CONDOMÍNIO", "CONDOMINIO"), ()),
    ("empresarial", ("COMPREENSIVO EMPRESARIAL", "COMPREENSIVO INDUSTRIAL",
                     "EMPRESARIAL"), ()),
    ("vida", ("VIDA (INDIVIDUAL)", "VIDA (COLETIVO)", "VIDA - CAPITAL GLOBAL"), ()),
    ("garantia", ("FIANÇA LOCATÍCIA", "FIANCA LOCATICIA"), ()),
    ("equipamentos", ("RISCOS DIVERSOS",), ("EQUIPAMENTO",)),
    ("equipamentos", ("GARANTIA ESTENDIDA",), ()),
)

SITUACAO_VIVA = "passível de comercialização"

# 🔴 §3.2.1 item 3. `interpretar_consulta` escolhe a de inicio mais recente e
# deixa o aviso no motivo; aqui o aviso vira RECUSA. A peca de baixo pode
# preferir devolver algo; o lote nao pode preferir indexar algo.
_DUAS_ABERTAS = re.compile(r"^\d+_versoes_em_aberto$")


# ---------------------------------------------------------------------------
# O que sabemos sobre um produto
# ---------------------------------------------------------------------------

ENTRA = "entra"
PULA = "pula"


@dataclass
class Produto:
    processo: str
    entnome: str
    ramo_oficial: str
    subramo: str
    product_line: str
    consulta: Any = None                     # susep_rep2.ConsultaProduto
    nosso: Optional[dict] = None             # linha de normative_documents
    veredito: str = PULA
    motivo: str = "nao_consultado"
    ficha: list[tuple[str, str]] = field(default_factory=list)
    faltando: list[str] = field(default_factory=list)

    @property
    def nome(self) -> str:
        partes = [self.ramo_oficial]
        if self.subramo and self.subramo.upper() not in self.ramo_oficial.upper():
            partes.append(self.subramo)
        return " / ".join(p for p in partes if p)


# ---------------------------------------------------------------------------
# As portas
# ---------------------------------------------------------------------------

def _banco():
    """A MESMA leitura de credencial que os scripts vizinhos usam.

    Nao uma segunda: `exportar._credenciais` ja resolve `.env` ao lado do
    script e cai no ambiente, e e o caminho que `reindexar_acervo.py` reusa.
    Uma copia daqui envelheceria sozinha — e a que ninguem olha e sempre a que
    mente. Ela imprime presenca e o prefixo do host, nunca o valor.
    """
    sys.path.insert(0, str(BACKEND / "scripts" / "destilacao_max"))
    from exportar import _credenciais  # noqa: E402 — vizinho, nao pacote

    url, key = _credenciais()
    from supabase import create_client

    return create_client(url, key)


def _portas(exigir_indice: bool) -> tuple[bool, list[str]]:
    """Confere as portas ANTES de gastar. Nunca exibe segredo — so presenca.

    Pedido certo: em producao nao se descobre que falta uma variavel de
    ambiente no meio do quinto documento, com o quarto ja meio indexado.
    """
    print("== as portas ==\n")
    problemas: list[str] = []

    try:
        db = _banco()
        n = (db.table("normative_documents").select("id", count="exact")
             .limit(1).execute()).count
        print(f"  [ok] Supabase ........ {n} documentos no catalogo normativo")
    except Exception as exc:  # noqa: BLE001
        print(f"  [X]  Supabase ........ {type(exc).__name__}: {exc}")
        problemas.append("supabase")

    for nome, variaveis in (("Qdrant", ("QDRANT_HOST", "QDRANT_URL")),
                            ("OpenAI", ("OPENAI_API_KEY",)),
                            ("MinIO", ("MINIO_ENDPOINT", "MINIO_URL"))):
        presente = any((os.getenv(v) or "").strip() for v in variaveis)
        marca = "ok" if presente else ("X" if exigir_indice else "!")
        print(f"  [{marca}] {nome:<12} ... {'configurado' if presente else 'AUSENTE'}"
              "  (presenca, o valor nao e exibido)")
        if not presente and exigir_indice and nome != "MinIO":
            problemas.append(nome.lower())
        if not presente and nome == "MinIO" and exigir_indice:
            print("       ⚠️ sem MinIO o PDF nao e arquivado e os pedacos nao "
                  "podem ser exportados depois — a ingestao segue, a exportacao nao")

    try:
        import fitz  # noqa: F401

        print("  [ok] PyMuPDF ......... presente  (§4.1: nunca PyPDF2)")
    except Exception:  # noqa: BLE001
        print("  [X]  PyMuPDF ......... AUSENTE — sem ele o PDF vira uma linha so")
        problemas.append("pymupdf")

    print()
    return (not problemas), problemas


# ---------------------------------------------------------------------------
# Passo 1 — descobrir os produtos
# ---------------------------------------------------------------------------

def _ramo_de_varejo(ramo: str, subramo: str = "") -> Optional[str]:
    """O `product_line` deste produto, ou `None` quando não é de varejo."""
    alvo, sub = (ramo or "").upper(), (subramo or "").upper()
    for nossa, pistas, exige_sub in RAMOS_DE_VAREJO:
        if not any(p in alvo for p in pistas):
            continue
        if exige_sub and not any(s in sub for s in exige_sub):
            continue
        return nossa
    return None


def descobrir(catalogo, entnomes: tuple[str, ...], *,
              so_ramo: str = "") -> list[Produto]:
    """§9 passo 1 — os produtos de varejo desta seguradora, do catalogo oficial."""
    achados: list[Produto] = []
    vistos: set[str] = set()
    for linha in catalogo.linhas:
        nome = (linha.get("entnome") or "").upper()
        if not any(p in nome for p in entnomes):
            continue
        if (linha.get("tipoproduto") or "").upper() not in TIPOS_DE_SEGURO:
            continue
        nossa = _ramo_de_varejo(linha.get("ramo") or "", linha.get("subramo") or "")
        if not nossa or (so_ramo and nossa != so_ramo):
            continue
        processo = (linha.get("numeroprocesso") or "").strip()
        if not processo or processo in vistos:
            continue
        vistos.add(processo)
        achados.append(Produto(
            processo=processo,
            entnome=(linha.get("entnome") or "").strip(),
            ramo_oficial=(linha.get("ramo") or "").strip(),
            subramo=(linha.get("subramo") or "").strip(),
            product_line=nossa,
        ))
    return achados


# ---------------------------------------------------------------------------
# Passo 2 — a versao vigente, e a ficha que decide se ela entra
# ---------------------------------------------------------------------------

def _nossos_documentos(db, insurer_key: str) -> dict[str, list[dict]]:
    """O que ja temos, indexado pelo processo NORMALIZADO.

    📊 3 de 31 processos gravados nao casam com o formato canonico — um com
    ponto a mais, dois sem o digito verificador. Comparar strings cruas faria
    o CG140 da Porto (`15414.100.233/2004-59`) parecer um produto que nunca
    tivemos, e o script criaria um documento paralelo ao que ja existe. Duas
    linhas para o mesmo contrato e como a versao nova deixa de substituir a
    velha em vez de aposenta-la.
    """
    from app.services.knowledge.susep_rep2 import normalizar_processo

    linhas = (db.table("normative_documents").select(
        "id, insurer_key, insurer_name, product_line, doc_kind, title, "
        "susep_process, version_label, effective_from, status, chunk_count, "
        "source_url")
        .eq("insurer_key", insurer_key).execute()).data or []
    mapa: dict[str, list[dict]] = {}
    for linha in linhas:
        chave = normalizar_processo(linha.get("susep_process"))
        if chave:
            mapa.setdefault(chave, []).append(linha)
    return mapa


def _o_que_tinhamos(docs: list[dict]) -> str:
    if not docs:
        return "nada"
    partes = []
    for d in docs:
        rotulo = d.get("version_label") or d.get("title") or "sem rotulo"
        data = d.get("effective_from") or "sem vigencia"
        partes.append(f"{rotulo} ({data}, {d.get('chunk_count') or 0} pedacos)")
    return " · ".join(partes)


def montar_ficha(p: Produto) -> None:
    """🔴 A conferencia obrigatoria da §3.2.1, linha a linha.

    Cada linha tem uma origem declarada. As seis primeiras vem do REGISTRO
    OFICIAL; so a ultima ("o que tinhamos") e fato nosso, e por isso "nada" e
    um preenchimento valido nela e em nenhuma outra.

    O que esta funcao produz nao e um relatorio: e o veredito. `faltando` nao
    vazio significa que o documento nao entra — e o motivo fica escrito, com o
    nome do campo que faltou.
    """
    from app.services.knowledge import susep_rep2 as rep2

    c = p.consulta
    ficha: list[tuple[str, str]] = []
    faltando: list[str] = []

    def linha(rotulo: str, valor: Optional[str], obrigatorio: bool = True) -> None:
        texto = (valor or "").strip()
        ficha.append((rotulo, texto or "(nao veio do registro)"))
        if obrigatorio and not texto:
            faltando.append(rotulo)

    linha("produto", f"{p.nome} (processo {p.processo})")

    if c is None:
        linha("situação", None)
        p.ficha, p.faltando = ficha, faltando + ["consulta"]
        p.veredito, p.motivo = PULA, "nao_consultado"
        return

    situacao = (c.situacao or "").strip()
    ficha.append(("situação", situacao or "(nao veio do registro)"))
    if situacao.lower() != SITUACAO_VIVA:
        faltando.append("situação")

    vig = c.vigente
    linha("versão baixada", vig.arquivo if vig else None)
    linha("início", vig.inicio if vig else None)

    # 🔴 A linha que o olho pula. Fim PREENCHIDO nao e um campo faltando — e
    # uma versao REVOGADA, e ela nao entra de jeito nenhum. Por isso a
    # conferencia e pelo contrario do resto da ficha.
    fim = (vig.fim or "").strip() if vig else ""
    ficha.append(("fim", "(vazio)" if not fim else f"🔴 {fim} — REVOGADA"))
    if fim:
        faltando.append("fim (a versao escolhida tem Data de Fim)")

    total = len(c.versoes or ())
    ficha.append(("total de versões", str(total) if total else "(nao veio do registro)"))
    if not total:
        faltando.append("total de versões")

    ficha.append(("o que tínhamos", _o_que_tinhamos(p.nosso or [])))

    # E os motivos que nao cabem numa linha da ficha.
    if c.estado == rep2.PRODUTO_MORTO:
        faltando.append(f"produto morto ({c.motivo})")
    elif c.estado == rep2.INDETERMINADO:
        faltando.append(f"indeterminado ({c.motivo})")
    if vig and not vig.download_id:
        faltando.append("id de download")
    if c.motivo and _DUAS_ABERTAS.match(c.motivo):
        # §3.2.1 item 3 — duas vigentes e defeito da fonte, nao escolha nossa.
        faltando.append(f"{c.motivo} — a §3.2.1 proibe escolher")
    if c.divergencia_negrito:
        ficha.append(("⚠️ divergência",
                      "o portal marcou OUTRA linha em negrito; a Data de Fim "
                      "vazia manda, e a divergência fica registrada"))

    p.ficha, p.faltando = ficha, faltando
    p.veredito = ENTRA if not faltando else PULA
    p.motivo = "" if not faltando else "; ".join(faltando)


def imprimir_ficha(p: Produto) -> None:
    print(f"\n  ── {p.product_line} · {p.processo} "
          f"{'✅ ENTRA' if p.veredito == ENTRA else '⛔ NAO ENTRA'}")
    for rotulo, valor in p.ficha:
        pontos = "." * max(2, 20 - len(rotulo))
        print(f"     {rotulo} {pontos} {valor}")
    if p.faltando:
        print(f"     ⛔ pulado: {p.motivo}")


# ---------------------------------------------------------------------------
# Passo 3 a 5 — baixar, partir, indexar (quem faz e o `insurance_corpus`)
# ---------------------------------------------------------------------------

def _documento_alvo(p: Produto) -> tuple[Optional[dict], Optional[str]]:
    """Qual linha de `normative_documents` este produto atualiza. Ou nenhuma.

    🔴 A identidade de um documento e o PROCESSO SUSEP, nunca a URL. A URL de
    download do REP2 carrega o id da VERSAO (`.../DownloadConsultaPublica/508497`)
    e muda a cada revisao — `registrar()` faz upsert por `source_url`, entao
    usa-la como identidade criaria uma linha nova a cada versao. E duas linhas
    para o mesmo contrato significam que a versao nova deixa de aposentar a
    velha: as duas ficam abertas, as duas ficam no indice, e a busca passa a
    devolver as duas com a mesma autoridade. E o defeito que a D-Acervo-02
    existe para impedir, reconstruido pela porta dos fundos.

    Quando o processo casa com MAIS DE UMA linha nossa (📊 a Azul tem condicoes
    gerais e manual do segurado sob o mesmo processo), a preferencia e
    `condicoes_gerais`. Se ainda assim sobrar mais de uma, o script **nao
    escolhe** — mesma disciplina da §3.2.1: ambiguidade da fonte nao vira
    decisao nossa.
    """
    candidatos = [d for d in (p.nosso or []) if d.get("product_line") == p.product_line] \
        or list(p.nosso or [])
    if not candidatos:
        return None, None
    gerais = [d for d in candidatos if d.get("doc_kind") == "condicoes_gerais"]
    escolha = gerais or candidatos
    if len(escolha) > 1:
        return None, (f"{len(escolha)} documentos nossos casam com o processo "
                      f"{p.processo} — nao escolho")
    return escolha[0], None


def _ja_coletado(db, documento_id: str, download_id: str) -> Optional[dict]:
    """O progresso, lido do BANCO. Ver o cabecalho deste arquivo.

    Uma versao ABERTA cujo `susep_version_id` e o id que a SUSEP acabou de
    devolver significa: este documento ja foi coletado nesta versao. A linha so
    existe se o indice aceitou os pedacos, entao ela nao pode dizer "feito"
    sobre trabalho que nao terminou.
    """
    linhas = (db.table("normative_document_versions")
              .select("id, version, susep_version_id, qdrant_doc_id, "
                      "effective_from, version_label, chunk_count, "
                      "text_storage_ref, superseded_at")
              .eq("document_id", documento_id)
              .is_("superseded_at", "null").execute()).data or []
    for linha in linhas:
        if str(linha.get("susep_version_id") or "") == str(download_id):
            return linha
    return None


def _versao_aberta(db, documento_id: str) -> Optional[dict]:
    linhas = (db.table("normative_document_versions")
              .select("id, version, susep_version_id, qdrant_doc_id, "
                      "effective_from, version_label, chunk_count")
              .eq("document_id", documento_id)
              .is_("superseded_at", "null")
              .order("version", desc=True).limit(1).execute()).data or []
    return linhas[0] if linhas else None


def coletar_um(p: Produto, *, insurer_key: str, insurer_nome: str, db,
               servico) -> dict:
    """Passos 3 a 5 de UM documento. Devolve o que aconteceu, sem levantar."""
    from app.services.knowledge.susep_rep2 import URL_DOWNLOAD, normalizar_processo

    processo = normalizar_processo(p.processo) or p.processo
    vig = p.consulta.vigencia_para_o_acervo()
    if not vig:
        return {"ok": False, "motivo": "sem vigencia do registro"}
    download_id = vig["susep_version_id"]
    url = f"{URL_DOWNLOAD}/{download_id}"

    alvo, ambiguo = _documento_alvo(p)
    if ambiguo:
        return {"ok": False, "motivo": ambiguo}

    if alvo:
        ja = _ja_coletado(db, alvo["id"], download_id)
        if ja:
            return {"ok": True, "pulado": "ja coletado nesta versao",
                    "documento_id": alvo["id"], "versao": ja}
        # A URL passa a apontar para o REGISTRO OFICIAL. O site da seguradora
        # vira conferencia (§3.4): 📊 HDI 500, Allianz 403, Tokio 200 com 1 KB.
        db.table("normative_documents").update({
            "source_url": url,
            "susep_process": processo,
            "version_label": vig["version_label"],
            "notes": f"ramo oficial SUSEP: {p.ramo_oficial}",
        }).eq("id", alvo["id"]).execute()
        documento_id = alvo["id"]
    else:
        novo = servico.registrar(
            insurer_key=insurer_key, insurer_name=insurer_nome,
            product_line=p.product_line, doc_kind="condicoes_gerais",
            title=f"{insurer_nome} {p.product_line} — {vig['version_label'] or p.nome}",
            source_url=url, susep_process=processo,
            version_label=vig["version_label"],
            effective_from=vig["effective_from"],
            notes=f"ramo oficial SUSEP: {p.ramo_oficial}")
        documento_id = novo.get("id")
        if not documento_id:
            return {"ok": False, "motivo": "registro nao devolveu id"}

    resultado = asyncio.run(servico.ingerir(documento_id, vigencia_susep=vig))
    resultado["documento_id"] = documento_id
    if resultado.get("ok"):
        resultado["versao"] = _versao_aberta(db, documento_id)
    return resultado


# ---------------------------------------------------------------------------
# Passo 6 — exportar os pedacos para os subagentes
# ---------------------------------------------------------------------------

def exportar_pedacos(p: Produto, documento_id: str, versao: dict, *,
                     insurer_key: str, insurer_nome: str,
                     por_pacote: int, pasta: Path) -> dict:
    """Os pedacos do documento viram `.jsonl`, em pacotes que cabem numa leitura.

    🔴 Este passo nao esta obvio na SPEC e sem ele o lote nao fecha. Os
    subagentes que escrevem as cartas rodam FORA do conteiner, na sessao do
    Founder — eles nao alcancam Qdrant nem Postgres. Recebem um arquivo e
    devolvem outro (§10.1).

    O texto sai do MinIO, e nao de um download novo. Duas razoes:

      · e o MESMO texto que foi indexado, entao o `unit_id` da linha N do
        `.jsonl` e o endereco do ponto N no indice — nao uma aproximacao;
      · e a prova de que o arquivamento funcionou. 📊 `storage_ref` estava
        preenchido em 0 de 29 antes do LOTE 0; se o MinIO falhar, isto avisa
        agora, e nao no dia em que a URL de origem morrer.
    """
    from app.services.knowledge.acervo_arquivo import ler_texto
    from app.services.knowledge.insurance_corpus import pedacos_detalhados

    numero = int(versao.get("version") or 0)
    qdrant_doc_id = versao.get("qdrant_doc_id") or f"norm-{documento_id}-v{numero}"
    texto = ler_texto(documento_id, numero)
    if not texto:
        return {"ok": False, "motivo": "o texto nao voltou do MinIO — "
                "rode de novo com --so-exportar quando ele estiver de pe"}

    doc = {"id": documento_id, "insurer_key": insurer_key,
           "insurer_name": insurer_nome, "product_line": p.product_line,
           "doc_kind": "condicoes_gerais",
           "title": versao.get("version_label") or p.nome}
    susep = p.processo
    vigencia = versao.get("effective_from")
    detalhados = pedacos_detalhados(doc, texto, susep, vigencia, qdrant_doc_id)
    if not detalhados:
        return {"ok": False, "motivo": "o texto guardado nao produziu pedacos"}

    bruto = re.sub(r"\.pdf$", "", versao.get("version_label") or p.product_line,
                   flags=re.I)
    rotulo = re.sub(r"[^a-z0-9]+", "-", bruto.lower()).strip("-")
    pasta.mkdir(parents=True, exist_ok=True)
    arquivos: list[dict] = []
    for k in range(0, len(detalhados), por_pacote):
        fatia = detalhados[k:k + por_pacote]
        nome = (f"{insurer_key}_{p.product_line}_v{numero}_{rotulo[:40]}"
                f"__pacote_{k // por_pacote + 1:02d}.jsonl")
        caminho = pasta / nome
        with caminho.open("w", encoding="utf-8") as fh:
            for item in fatia:
                fh.write(json.dumps({
                    "unit_id": item["unit_id"],
                    "caminho": item["caminho"],
                    "faceta": item["faceta"],
                    "seguradora": insurer_key,
                    "ramo": p.product_line,
                    "documento": versao.get("version_label") or p.nome,
                    "vigencia": _data_br(vigencia),
                    "susep_process": susep,
                    "texto": item["texto"],
                }, ensure_ascii=False) + "\n")
        arquivos.append({"arquivo": nome, "pedacos": len(fatia),
                         "bytes": caminho.stat().st_size})

    # O manifesto e o que fecha o circuito de volta: o subagente devolve
    # `unit_id_origem` por carta (§10.4), e quem grava a carta precisa dos dois
    # uuids para preencher `source_document_id` e `source_version_id`
    # (migration 03). Pedir isso ao subagente linha a linha seria transporte
    # puro — 📊 250 mil tokens para 85 mil de trabalho real, em 29/07.
    manifesto = {
        "seguradora": insurer_key, "ramo": p.product_line,
        "susep_process": susep, "documento": versao.get("version_label"),
        "vigencia": vigencia, "document_id": documento_id,
        "version_id": versao.get("id"), "version": numero,
        "qdrant_doc_id": qdrant_doc_id, "pedacos": len(detalhados),
        "pacotes": arquivos,
    }
    (pasta / f"{insurer_key}_{p.product_line}_v{numero}__MANIFESTO.json").write_text(
        json.dumps(manifesto, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "pedacos": len(detalhados), "pacotes": arquivos,
            "manifesto": manifesto}


def _data_br(iso: Optional[str]) -> str:
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", str(iso or ""))
    return f"{m.group(3)}/{m.group(2)}/{m.group(1)}" if m else ""


# ---------------------------------------------------------------------------
# O maestro
# ---------------------------------------------------------------------------

def levantar(args, db) -> tuple[list[Produto], Any]:
    """Passos 1 e 2 — o que existe la fora, o que temos aqui, e o que entra."""
    from app.services.knowledge import susep_rep2 as rep2

    nome_oficial, entnomes = SEGURADORAS[args.seguradora]
    if args.entnome:
        entnomes = tuple(e.strip().upper() for e in args.entnome.split("|") if e.strip())

    print(f"== {nome_oficial} ({args.seguradora}) ==\n")
    print("passo 1 — o catalogo oficial da SUSEP")
    catalogo = rep2.carregar_catalogo()
    print(f"  {len(catalogo):,} produtos · origem {catalogo.origem}"
          f"{' de ' + str(catalogo.baixado_em) if catalogo.origem == 'cache' else ''}")
    if catalogo.origem == "cache":
        print("  ⚠️ ISTO E CACHE, nao a resposta de hoje. O endpoint ja mudou de "
              "caminho uma vez; confira antes de concluir que um produto sumiu.")

    produtos = descobrir(catalogo, entnomes, so_ramo=args.ramo)
    casaram = sorted({p.entnome for p in produtos})
    print(f"  entnome casou com: {', '.join(casaram) or '(nenhum)'}")
    print(f"  {len(produtos)} produtos de varejo "
          f"({', '.join(sorted({p.product_line for p in produtos})) or '-'})")
    if args.limite:
        produtos = produtos[:args.limite]
        print(f"  --limite {args.limite}: consultando so os {len(produtos)} primeiros")
    if not produtos:
        return [], catalogo

    nossos = _nossos_documentos(db, args.seguradora)
    print(f"  ja temos {sum(len(v) for v in nossos.values())} documento(s) desta "
          f"seguradora no acervo\n")

    print(f"passo 2 — a versao vigente de cada um, no REP2 "
          f"(💭 ~{len(produtos) * 2.3:.0f}s)")
    cliente = rep2.Rep2Client()
    for i, p in enumerate(produtos, 1):
        alvo = rep2.normalizar_processo(p.processo) or p.processo
        p.nosso = nossos.get(alvo, [])
        p.consulta = cliente.consultar(alvo)
        montar_ficha(p)
        if i < len(produtos):
            time.sleep(args.pausa)   # portal publico e gratuito; nao o martele
        print(f"  {i:>3}/{len(produtos)}  {p.product_line:<13} {alvo}  "
              f"{p.consulta.estado}"
              f"{'' if p.veredito == ENTRA else '  ⛔'}")
    return produtos, catalogo


def resumir(produtos: list[Produto]) -> tuple[list[Produto], list[Produto]]:
    entram = [p for p in produtos if p.veredito == ENTRA]
    pulam = [p for p in produtos if p.veredito != ENTRA]

    print("\n" + "=" * 74)
    print("A FICHA DE CONFERENCIA — §3.2.1")
    print("=" * 74)
    for p in produtos:
        imprimir_ficha(p)

    print("\n" + "=" * 74)
    print(f"ENTRAM {len(entram)} · NAO ENTRAM {len(pulam)}")
    print("=" * 74)
    for p in entram:
        antes = _o_que_tinhamos(p.nosso or [])
        estado = "🆕 nao tinhamos" if antes == "nada" else f"↻ tinhamos: {antes}"
        print(f"  ✅ {p.product_line:<13} {p.consulta.vigente.arquivo[:52]:<52} "
              f"{p.consulta.vigente.inicio}")
        print(f"     {estado}")
    for p in pulam:
        print(f"  ⛔ {p.product_line:<13} {p.processo}  {p.motivo[:90]}")
    return entram, pulam


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Coleta o acervo VIGENTE de uma seguradora (SPEC-070 §9)")
    ap.add_argument("--seguradora", required=True, choices=sorted(SEGURADORAS),
                    help="a chave da seguradora (o mesmo `insurer_key` da busca)")
    ap.add_argument("--diagnostico", action="store_true",
                    help="as portas + o levantamento; nao baixa nem grava nada")
    ap.add_argument("--aplicar", action="store_true",
                    help="baixa, indexa e exporta. So funciona no conteiner")
    ap.add_argument("--so-exportar", action="store_true",
                    help="nao indexa; so refaz os `.jsonl` do que ja esta no acervo")
    ap.add_argument("--sim", action="store_true", help="nao pergunta antes de gastar")
    ap.add_argument("--ramo", default="", help="so este product_line")
    ap.add_argument("--entnome", default="",
                    help="nomes de entidade separados por | — manda mais que a "
                         "tabela SEGURADORAS quando ela errar")
    ap.add_argument("--limite", type=int, default=0, help="so os N primeiros produtos")
    ap.add_argument("--pausa", type=float, default=0.5,
                    help="segundos entre consultas ao REP2")
    ap.add_argument("--pacote", type=int, default=PEDACOS_POR_PACOTE,
                    help="pedacos por arquivo `.jsonl`")
    ap.add_argument("--saida", default="", help="pasta dos `.jsonl`")
    args = ap.parse_args()

    escreve = args.aplicar or args.so_exportar

    # 🔴 A RECUSA. Indexar metade de uma seguradora e pior que nao indexar
    # nada: o indice fica com dois criterios convivendo e ninguem sabe qual
    # documento esta sob qual. E sem OPENAI_API_KEY nao ha embedding — o
    # processo morreria no primeiro documento, depois de ja ter mexido no banco.
    if args.aplicar and not (os.getenv("QDRANT_HOST") or os.getenv("QDRANT_URL")):
        print("RECUSADO: QDRANT_HOST/QDRANT_URL nao existe neste ambiente.")
        print("Sem indice nao ha o que escrever, e o banco ficaria dizendo")
        print("`ingested` sobre pedacos que nao existem em lugar nenhum.")
        print("Rode isto DENTRO do conteiner de producao (smith-worker/smith-api).")
        return 2
    if args.aplicar and not os.getenv("OPENAI_API_KEY"):
        print("RECUSADO: OPENAI_API_KEY nao existe neste ambiente.")
        print("Sem embedding o documento e baixado, o banco e atualizado e o")
        print("indice fica vazio — o pior estado possivel, porque e silencioso.")
        return 2

    ok_portas, problemas = _portas(exigir_indice=escreve)
    if args.diagnostico and not ok_portas:
        print("Alguma porta fechada. O levantamento abaixo continua valendo — "
              "ele so le.\n")
    if escreve and not ok_portas:
        print(f"RECUSADO: portas fechadas: {', '.join(problemas)}")
        return 2

    db = _banco()
    produtos, _catalogo = levantar(args, db)
    if not produtos:
        print("\nNenhum produto de varejo encontrado. Confira `--entnome`.")
        return 1
    entram, _pulam = resumir(produtos)

    if args.diagnostico:
        print("\n(--diagnostico: nada foi baixado, nada foi escrito)")
        return 0
    if not escreve:
        chars = len(entram) * 485_524   # 📊 media medida no CG144 da Porto
        print(f"\nO QUE --aplicar FARIA: baixar, indexar e exportar {len(entram)} "
              f"documento(s)")
        print(f"custo estimado de embedding ... US$ "
              f"{chars / CHARS_POR_TOKEN / 1_000_000 * CUSTO_POR_MILHAO:.3f}"
              "   (💭 estimativa sobre o tamanho medido do CG144)")
        print("\n(nada foi escrito — use --aplicar)")
        return 0
    if not entram:
        print("\nNada a coletar.")
        return 0
    if not args.sim:
        print(f"\nBaixar, indexar e exportar {len(entram)} documento(s)? [s/N] ",
              end="")
        if (input().strip().lower() or "n") != "s":
            print("cancelado.")
            return 0

    from app.core.database import get_supabase_client
    from app.services.knowledge.insurance_corpus import InsuranceCorpusService

    nome_oficial, _ = SEGURADORAS[args.seguradora]
    servico = InsuranceCorpusService(get_supabase_client())
    pasta = Path(args.saida) if args.saida else (PASTA_LOTES / args.seguradora)

    print("\n" + "=" * 74)
    print("PASSOS 3 A 6")
    print("=" * 74)
    feitos = falhos = exportados = 0
    t0 = time.time()
    for p in entram:
        print(f"\n▸ {p.product_line} · {p.processo}")
        try:
            if args.so_exportar:
                alvo, ambiguo = _documento_alvo(p)
                if not alvo:
                    print(f"  ⛔ {ambiguo or 'nao esta no acervo — rode --aplicar'}")
                    falhos += 1
                    continue
                r = {"ok": True, "documento_id": alvo["id"],
                     "versao": _versao_aberta(db, alvo["id"])}
            else:
                r = coletar_um(p, insurer_key=args.seguradora,
                               insurer_nome=nome_oficial, db=db, servico=servico)
        except Exception as exc:  # noqa: BLE001 — um documento ruim nao para o lote
            print(f"  X  {type(exc).__name__}: {exc}")
            falhos += 1
            continue

        if not r.get("ok"):
            print(f"  ⛔ {r.get('motivo')}")
            falhos += 1
            continue
        if r.get("pulado"):
            print(f"  ↷ {r['pulado']} (v{(r.get('versao') or {}).get('version')})")
        else:
            feitos += 1
            print(f"  ✅ v{r.get('versao') and r['versao'].get('version')} · "
                  f"{r.get('chunks')} pedacos · vigencia {r.get('vigencia')} "
                  f"({r.get('vigencia_fonte')}) · original "
                  f"{'guardado' if r.get('arquivado') else 'NAO guardado'}")

        versao = r.get("versao")
        if not versao:
            print("  ⚠️ sem linha de versao — nao da para exportar")
            continue
        e = exportar_pedacos(p, r["documento_id"], versao,
                             insurer_key=args.seguradora, insurer_nome=nome_oficial,
                             por_pacote=args.pacote, pasta=pasta)
        if e.get("ok"):
            exportados += 1
            print(f"  📦 {e['pedacos']} pedacos em {len(e['pacotes'])} pacote(s) "
                  f"→ {pasta}")
            for a in e["pacotes"]:
                print(f"       {a['arquivo']}  {a['pedacos']} linhas "
                      f"({a['bytes'] / 1024:.0f} KB)")
        else:
            print(f"  ⚠️ pedacos NAO exportados: {e.get('motivo')}")

    print("\n" + "=" * 74)
    print(f"indexados {feitos} · exportados {exportados} · falhos {falhos} · "
          f"{time.time() - t0:.0f}s")
    print("O progresso esta no BANCO (versao aberta com o `susep_version_id` da "
          "SUSEP).\nRodar de novo pula o que ja foi e retenta o resto.")
    if falhos:
        print("\n⚠️ Documento pulado NAO e documento em dia. Leia os motivos "
              "acima antes\n   de marcar o lote como concluido na §7 da SPEC.")
    return 1 if falhos and not feitos else 0


if __name__ == "__main__":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    sys.exit(main())
