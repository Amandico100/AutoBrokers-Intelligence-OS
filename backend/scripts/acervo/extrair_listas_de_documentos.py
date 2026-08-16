"""Extrai as listas de documentos do BRUTO — sem destilar, sem perder item.

    python backend/scripts/acervo/extrair_listas_de_documentos.py
    python backend/scripts/acervo/extrair_listas_de_documentos.py --gravar

SOMENTE LEITURA do acervo. `--gravar` escreve os `.jsonl` de cartas em
`backend/scripts/acervo/cartas/<seguradora>/documentos_*.jsonl`, que
`publicar_cartas.py` depois publica. Nao toca no banco nem no Qdrant.

POR QUE ESTE ARQUIVO EXISTE — SPEC-072 BLOCO 2
==============================================
📊 A destilacao em prosa PERDE item de lista, e isso e medido: o nucleo comum de
documentos cai de 12/16 no texto bruto para 5/16 nas cartas destiladas. "Dados
bancarios" saiu de 0/4 para 3/3 — as tres seguradoras exigem, e nenhuma carta
destilada de auto registrou.

    Corolario da SPEC-072 §3.4: NAO DESTILE A LISTA. EXTRAIA A SECAO INTEIRA.

Entao aqui nao ha modelo. E extracao deterministica: o que sai da carta e o que
estava no contrato, reorganizado — nunca reescrito por um LLM que pode "resumir"
tres documentos em dois.

🔴 CINCO FATOS DO BRUTO QUE MUDARAM O DESENHO — medidos em 15/08/2026
=====================================================================
Eles nao estavam na SPEC, e cada um invalidava uma premissa dela.

① O `ramo` JA VEM PRONTO no campo `texto`, no cabecalho
  `[Seguradora · ramo · Produto · vigencia · SUSEP]`. Cobertura 100%.
  📊 Um mapa `caminho -> ramo` cobriria 19% e erraria o resto. Nao infira.

② O CHUNKER PARTE AS LISTAS AO MEIO. Nenhum `corpo` passa de 2.181 chars, e
  📊 18 das 253 secoes comecam num marcador que nao e `a)` nem `1)` — ou seja,
  no meio da lista. A lista de 41 itens da Porto Auto esta em TRES pedacos.
  **A unidade de trabalho nao e o pedaco; e a CORRIDA `(docid, caminho,
  indice consecutivo)`.** 253 pedacos -> 129 corridas.

③ `faceta=='documento'` E UM CENSO INCOMPLETO. Costurando os vizinhos de mesmo
  caminho, 253 -> 📊 311 pedacos (+58, +79.904 chars). E a matriz
  documento x situacao da Allianz Auto — a fonte mais proxima do que esta SPEC
  quer no acervo inteiro — esta em pedacos com `faceta=None`.

④ NA YELUM O `caminho` MENTE. O titulo folha e cabecalho de tabela arrastado da
  pagina anterior do PDF. 📊 Quando caminho e corpo classificam a mesma secao,
  **concordam 0 vezes e discordam 12**: o caminho diz `DESMORONAMENTO` onde o
  corpo diz `QUEBRA DE VIDROS`. Para yelum, a situacao sai da CAIXA ALTA inicial
  do corpo, jamais do caminho.

⑤ A YELUM NAO TEM MARCADOR DE ITEM. 📊 128 das 139 secoes tem zero marcador — e
  uma tabela achatada em prosa corrida. A heuristica de "fronteira de
  maiuscula" foi medida contra a verdade de allianz+porto e **erra 107% na
  mediana**: "RG, CPF ou CNH do segurado" vira 3 itens. Nao serve de gate.

O QUE ISSO FAZ COM O GATE
=========================
A SPEC pede "contar os itens na origem e na carta; divergencia = falha". Isso e
mensuravel onde HA marcador — 📊 59 das 253 (23%). Nas outras 194 nao existe
item delimitado para contar, e inventar um contador seria fabricar o gate.

Entao sao DOIS invariantes, e o segundo e mais forte que o primeiro:

    COM marcador   itens na origem == soma dos itens nas cartas
    SEMPRE         o texto limpo da origem e reconstruivel a partir das cartas
                   (nenhum caractere descartado alem do ruido declarado)

O segundo vale para 100% das corridas e nao depende de heuristica nenhuma.

E O TETO DE 1.800
=================
📊 Costurado, so 92 das 129 corridas cabem em 1.800. A maior tem 27.914 chars.
A lista completa da Porto residencial tem 67 itens em 6.274 chars.

    P-170 ja tinha decidido: "partir em duas cartas, NAO ENCURTAR. Encurtar uma
    lista de documentos e entregar meia lista, que e pior que nenhuma."

Entao a corrida vira N cartas de ate 1.800, partidas SEMPRE em fronteira de item
(ou de paragrafo, onde nao ha item) e nunca no meio de um. Cada parte diz qual e
e quantas sao.
"""

from __future__ import annotations

import argparse
import collections
import gzip
import json
import os
import re
import sys
from pathlib import Path

AQUI = Path(__file__).resolve()
BACKEND = AQUI.parents[2]
PEDACOS = AQUI.parent / "pedacos"
CARTAS = AQUI.parent / "cartas"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(BACKEND))

MIN_CARACTERES = 40
MAX_CARACTERES = 1800
try:  # a regua e a de `curadoria_cartas`; o fallback existe so fora do backend
    from app.services.curadoria_cartas import (MAX_CARACTERES,  # noqa: F811
                                               MIN_CARACTERES)
except Exception:  # noqa: BLE001
    pass


# ─────────────────────────────────────────────────────────────────────────────
# 1. O RUIDO — o que o PDF injeta no meio da lista
# ─────────────────────────────────────────────────────────────────────────────
# 🔴 Isto NAO e cosmetica: o rodape da Allianz aparece ENTRE o item `e)` e o
# `f)`, e um contador de itens que nao o remova conta o rodape como conteudo e
# quebra a fronteira de particao no lugar errado.
_RUIDO = (
    re.compile(r"Allianz Seguros S\.?A.*?Classifica[çc][ãa]o Allianz:\s*P[ÚU]BLICO",
               re.I | re.S),
    # ⚠️ E o rodape SOZINHO: quando o chunker corta no meio dele, so a cauda
    # sobra e o regex acima — que exige o prefixo "Allianz Seguros S.A" — nao
    # alcanca. Aparecia no comeco de cartas da Allianz.
    re.compile(r"Classifica[çc][ãa]o Allianz:\s*P[ÚU]BLICO", re.I),
    re.compile(r"P\s*r\s*oc\s*esso\s+SUSEP\s*:?\s*[\d./-]+", re.I),
    re.compile(r"P[áa]gina\s+\d+\s*(?:/|de)\s*\d+", re.I),
    re.compile(r"Condi[çc][õo]es v[áa]lidas para seguros com in[íi]cio de vig[êe]ncia"
               r".{0,80}", re.I),
    re.compile(r"CNPJ:?\s*\d{2,3}[.\s]?\d{3}[.\s]?\d{3}/\d{4}-?\d{2}", re.I),
)


def limpar(corpo: str) -> str:
    """Tira o que o PDF injetou, preservando tudo o que e conteudo."""
    t = corpo or ""
    for rx in _RUIDO:
        t = rx.sub(" ", t)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n\n", t)
    return t.strip()


# ─────────────────────────────────────────────────────────────────────────────
# 2. OS ITENS — tres formatos incompativeis, e um deles nao existe
# ─────────────────────────────────────────────────────────────────────────────
# ⚠️ `[a-z]{1,2}\)` e nao `[a-z]\)`: a Porto chega a `aa)`, `bb)`, `ee)`. Um
# regex de uma letra so subconta a maior lista do acervo.
_ITEM_ALFA = re.compile(r"(?m)^\s*([a-z]{1,2})\)\s+")
_ITEM_NUM = re.compile(r"(?m)^\s*(\d{1,2})[).]\s+")
_ITEM_BULLET = re.compile(r"(?m)^\s*[•▪◦●·]\s+")


def itens_de(texto: str, minimo: int = 2) -> list:
    """As fronteiras de item, ou [] quando a secao nao tem marcador.

    Devolve lista de (posicao_inicial, rotulo). Vazia significa "esta secao nao
    tem item delimitado" — e isso e 📊 74% delas. Nao invente fronteira: a
    heuristica de maiuscula erra 107% na mediana (medido contra allianz+porto).

    🔴 `minimo` EXISTE POR CAUSA DE UM OFF-BY-ONE QUE O TESTE PEGOU.
    Para DETECTAR lista, `minimo=2` e o certo: um `a)` sozinho no meio de um
    paragrafo nao e lista, e contar como se fosse encheria o acervo de falsa
    estrutura. Mas para CONTAR os itens de uma PARTE ja recortada de uma lista
    conhecida, 2 e errado — a ultima parte muitas vezes leva um item so, e ele
    era contado como zero.

    📊 O teste mediu: 4 dos 32 blocos com lista divergiam, sempre por
    EXATAMENTE 1 (41->40, 25->24, 22->21, 17->16). Era sempre a ultima parte.
    """
    for rx in (_ITEM_ALFA, _ITEM_NUM, _ITEM_BULLET):
        achados = [(m.start(), m.group(0).strip()) for m in rx.finditer(texto)]
        if len(achados) >= minimo:
            return achados
    return []


# ─────────────────────────────────────────────────────────────────────────────
# 3. A SITUACAO — e ela sai de lugares diferentes em cada seguradora
# ─────────────────────────────────────────────────────────────────────────────
_SITUACOES = (
    ("perda_total", r"INDENIZA[ÇC][ÃA]O INTEGRAL|PERDA TOTAL"),
    ("roubo_furto", r"\bROUBO\b|\bFURTO\b|SUBTRA[ÇC][ÃA]O"),
    ("vidros", r"QUEBRA DE VIDROS|\bVIDROS\b|P[ÁA]RA-BRISA"),
    ("rcf_terceiros", r"\bRCF\b|RESPONSABILIDADE CIVIL|DANOS? MATERIAIS DE TERCEIROS"),
    ("morte_invalidez", r"\bMORTE\b|[ÓO]BITO|INVALIDEZ|\bIFPD\b|\bIPTA\b|\bAPP\b|\bDMH\b"),
    ("incendio", r"INC[ÊE]NDIO|QUEIMADA|QUEDA DE RAIO|EXPLOS[ÃA]O|FUMA[ÇC]A"),
    ("natureza", r"ALAGAMENTO|INUNDA[ÇC][ÃA]O|VENDAVAL|DESMORONAMENTO|GRANIZO"),
    ("colisao", r"COLIS[ÃA]O|INDENIZA[ÇC][ÃA]O PARCIAL|PERDA PARCIAL"),
    ("danos_eletricos", r"DANOS EL[ÉE]TRICOS|VAZAMENTO"),
    ("pj_frota", r"PESSOA JUR[ÍI]DICA|\bFROTA\b|EMPREGADOR|M[ÁA]QUINAS E EQUIP"),
    # ⚠️ "qualquer sinistro" e nao so "qualquer TIPO de sinistro": a melhor carta
    # do acervo inteiro — a lista de 52 itens da Porto — abre com "Em
    # decorrencia de QUALQUER SINISTRO, podera ser solicitado um ou varios
    # documentos a seguir" e estava caindo em `sem_situacao` por causa de duas
    # palavras no regex.
    # 🔴 `geral` NAO E O RESTO — E A LISTA QUE VALE PARA TODO SINISTRO
    # -------------------------------------------------------------------------
    # 📊 A primeira versao deixou 78 de 145 cartas em `sem_situacao`, e ao LER a
    # evidencia que o extrator viu, 3 em cada 4 diziam a mesma coisa:
    #
    #     "16.8. Documentos a Ser Entregues"
    #     "CLAUSULA 20. DOCUMENTOS NECESSARIOS EM CASO DE SINISTRO"
    #     "Em funcao do evento poderao ser solicitados os seguintes documentos:"
    #
    # Isso NAO e ausencia de situacao: e a lista GERAL, a que vale para qualquer
    # evento — e e a mais util de todas, porque e a que o segurado recebe antes
    # de se saber o que houve. Rotula-la como "sem situacao" escondia justamente
    # a carta mais entregavel do acervo.
    ("geral", r"DOCUMENTOS? B[ÁA]SICOS?|DOCUMENTOS? NECESS[ÁA]RIOS?|"
               r"documentos? a ser(?:em)? entregue|qualquer (?:tipo de )?sinistro|"
               r"EM TODOS OS CASOS|B[ÁA]SICA SIMPLES|B[ÁA]SICA AMPLA|"
               r"em decorr[êe]ncia de qualquer|para todos os sinistros|"
               r"em fun[çc][ãa]o do evento|documentos? (?:necess[áa]rios?|"
               r"para) (?:a )?regula[çc][ãa]o|rela[çc][ãa]o de documentos"),
)
_RX_SIT = [(nome, re.compile(rx, re.I)) for nome, rx in _SITUACOES]

# A CAIXA ALTA que abre o corpo da Yelum — e o nome real da cobertura.
_CAPS_INICIAL = re.compile(r"^([A-ZÀ-Ú][A-ZÀ-Ú0-9 ,./()–—-]{12,120})(?=\s)")


def situacao_de(seguradora: str, caminho: str, corpo: str):
    """Qual sinistro esta secao atende. `(situacao, fonte)`; `None` e comum.

    🔴 A FONTE MUDA POR SEGURADORA, e ignorar isso produz carta com o nome
    errado. 📊 Na yelum, caminho e corpo discordam 12 vezes e concordam ZERO —
    o titulo folha e cabecalho de tabela arrastado da pagina anterior do PDF.
    """
    if seguradora == "yelum":
        m = _CAPS_INICIAL.match((corpo or "").strip())
        alvo, fonte = (m.group(1) if m else ""), "corpo(caps)"
    else:
        alvo, fonte = (caminho or ""), "caminho"
    for nome, rx in _RX_SIT:
        if rx.search(alvo):
            return nome, fonte, alvo.strip()[:90]
    # Segunda tentativa: o comeco do corpo, que as vezes nomeia a cobertura.
    for nome, rx in _RX_SIT:
        if rx.search((corpo or "")[:150]):
            return nome, "corpo(inicio)", (corpo or "")[:90]
    return None, fonte, alvo.strip()[:90]


# ─────────────────────────────────────────────────────────────────────────────
# 4. AS CORRIDAS — costurar o que o chunker partiu
# ─────────────────────────────────────────────────────────────────────────────
def carregar(seguradora: str) -> list:
    arq = PEDACOS / f"{seguradora}_pedacos.jsonl.gz"
    with gzip.open(arq, "rt", encoding="utf-8") as f:
        return [json.loads(l) for l in f]


def _indice(unit_id: str) -> int:
    return int(unit_id.rsplit("#", 1)[-1])


def _doc(unit_id: str) -> str:
    return unit_id.rsplit("#", 1)[0]


def _ramo(pedaco: dict) -> str:
    """O ramo vem do cabecalho de `texto`, nunca do caminho (fato ①)."""
    cab = (pedaco.get("texto") or "").split("\n", 1)[0]
    partes = [p.strip() for p in cab.strip("[]").split("·")]
    return partes[1].lower() if len(partes) > 1 else "outro"


def corridas(pedacos: list) -> list:
    """Agrupa em corridas `(doc, caminho)` com indices CONSECUTIVOS.

    🔴 Inclui vizinhos de `faceta` diferente quando eles continuam a MESMA
    secao (fato ③): a matriz da Allianz Auto tem cabecalho com
    `faceta='documento'` e corpo com `faceta=None`, e separa-los perde a matriz.
    O criterio de pertencer e caminho identico + indice consecutivo, nao faceta.
    """
    por_chave = collections.defaultdict(list)
    for p in pedacos:
        por_chave[(_doc(p["unit_id"]), p.get("caminho") or "")].append(p)

    saida = []
    for (doc, caminho), ps in por_chave.items():
        ps.sort(key=lambda x: _indice(x["unit_id"]))
        atual = [ps[0]]
        for anterior, seguinte in zip(ps, ps[1:]):
            if _indice(seguinte["unit_id"]) == _indice(anterior["unit_id"]) + 1:
                atual.append(seguinte)
            else:
                saida.append((doc, caminho, atual))
                atual = [seguinte]
        saida.append((doc, caminho, atual))
    return saida


def corridas_de_documento(pedacos: list) -> list:
    """So as corridas que CONTEM ao menos um pedaco `faceta='documento'`.

    O censo comeca na faceta e termina na corrida: a faceta diz ONDE olhar, a
    corrida diz ATE ONDE ler (fato ③).
    """
    return [c for c in corridas(pedacos)
            if any((p.get("faceta") or "").lower() == "documento" for p in c[2])]


# ─────────────────────────────────────────────────────────────────────────────
# 5. A CARTA — e a particao que P-170 mandou fazer
# ─────────────────────────────────────────────────────────────────────────────
_ROTULO_SIT = {
    "perda_total": "indenização integral (perda total)",
    "roubo_furto": "roubo ou furto", "vidros": "quebra de vidros",
    "rcf_terceiros": "danos a terceiros", "morte_invalidez": "morte ou invalidez",
    "incendio": "incêndio, raio ou explosão", "natureza": "vendaval, alagamento ou desmoronamento",
    "colisao": "colisão", "danos_eletricos": "danos elétricos ou vazamento",
    "pj_frota": "pessoa jurídica", "geral": "qualquer sinistro",
}
_NOME_SEG = {"allianz": "Allianz", "porto": "Porto Seguro", "yelum": "Yelum"}

# Acima disto a carta deixa de ser lista e vira capitulo fatiado. Ver o
# comentario em `_carta_de_bloco`.
MAX_PARTES = 4
_NAO_PARTICIONAVEIS: list = []
_SEM_DOCUMENTO: list = []


def partir(corpo: str, teto: int) -> list:
    """Parte o texto em pedacos de ate `teto`, SEMPRE em fronteira de item.

    🔴 P-170: "partir em duas cartas, NAO ENCURTAR. Encurtar uma lista de
    documentos e entregar meia lista, que e pior que nenhuma." Entao aqui nao ha
    truncagem: o texto inteiro sai, repartido.

    A fronteira e o item quando ha marcador, e o paragrafo quando nao ha. Nunca
    o caractere: cortar "CNH do condu|tor" produz duas cartas erradas em vez de
    uma certa.
    """
    if len(corpo) <= teto:
        return [corpo]
    marcas = [pos for pos, _ in itens_de(corpo)]
    if len(marcas) < 2:
        marcas = [m.start() for m in re.finditer(r"\n\n", corpo)]
    marcas = [0] + [m for m in marcas if m > 0] + [len(corpo)]
    marcas = sorted(set(marcas))

    partes, inicio = [], 0
    while inicio < len(corpo):
        cabe = [m for m in marcas if inicio < m <= inicio + teto]
        fim = max(cabe) if cabe else min(len(corpo), inicio + teto)
        partes.append(corpo[inicio:fim].strip())
        inicio = fim
    return [p for p in partes if p]


# 🔴 A CORRIDA GIGANTE NAO E UMA LISTA — SAO VARIAS, EMPILHADAS
# =============================================================================
# A primeira versao deste extrator partia a corrida por TAMANHO e produzia
# "parte 17 de 19". Isso e inutil para o segurado e e o sintoma de um erro de
# leitura: 📊 a maior corrida da Yelum tem 27.914 chars porque ela e o CAPITULO
# de documentos inteiro — dentro dele estao `BASICA SIMPLES – INCENDIO, QUEDA DE
# RAIO...`, `QUEBRA DE VIDROS...`, `DANOS ELETRICOS...`, cada um com a SUA lista.
#
# A fronteira certa nao e o caractere nem o item: e a COBERTURA. Partir ali
# resolve dois defeitos de uma vez — some a carta "parte 17 de 19", e a situacao
# deixa de ser desconhecida, porque cada bloco traz o proprio titulo.
# ⚠️ O regex tem de parar ANTES da primeira palavra Capitalizada-minuscula, e a
# primeira versao nao parava: a classe `[A-ZÀ-Ú0-9 ...]` incluia o espaco, entao
# `QUEIMADAS EM ZONAS RURAIS Apresentar` casava ate o `A` de `Apresentar` e a
# lookahead por `[A-Z][a-z]` falhava contra `presentar`. Resultado: 13 blocos de
# cobertura viravam ZERO, e a corrida de 27.914 chars era partida por tamanho em
# "parte 17 de 19".
#
# Agora ele casa TOKENS inteiros em caixa alta (2 ou mais) e para na primeira
# palavra que comeca frase.
_BLOCO_DE_COBERTURA = re.compile(
    r"(?m)^\s*((?:[A-ZÀ-Ú0-9][A-ZÀ-Ú0-9,./()\-–—]*\s+){2,})(?=[A-ZÀ-Ú][a-zà-ú])")


def blocos_de_cobertura(corpo: str) -> list:
    """Parte o texto nos titulos de cobertura em CAIXA ALTA. `[(titulo, corpo)]`.

    Devolve `[("", corpo)]` quando nao ha titulo — a corrida e uma coisa so.
    """
    marcas = [(m.start(), m.group(1).strip()) for m in _BLOCO_DE_COBERTURA.finditer(corpo)]
    # Um titulo so, no comeco, nao parte nada: e o titulo da secao inteira.
    if len(marcas) < 2:
        return [("", corpo)]
    # 🔴 BLOCO CURTO NAO SE DESCARTA — ELE GRUDA NO ANTERIOR.
    # A primeira versao fazia `if len(trecho) >= MIN_CARACTERES` e jogava fora o
    # resto. 📊 O teste pegou: 5 de 32 corridas perdiam item, e uma perdia 88%
    # do texto (1.972 -> 231 chars). Um titulo de cobertura seguido de duas
    # linhas nao e ruido — e o comeco da lista da cobertura seguinte, e jogar
    # fora e exatamente o defeito que este bloco existe para impedir.
    saida = []
    for (pos, titulo), (fim, _) in zip(marcas, marcas[1:] + [(len(corpo), "")]):
        trecho = corpo[pos:fim].strip()
        if not trecho:
            continue
        if len(trecho) < MIN_CARACTERES and saida:
            anterior_titulo, anterior = saida[-1]
            saida[-1] = (anterior_titulo, anterior + "\n\n" + trecho)
        else:
            saida.append((titulo, trecho))
    # E o que vem ANTES do primeiro titulo tambem e conteudo.
    if marcas and marcas[0][0] > 0:
        cabeca = corpo[:marcas[0][0]].strip()
        if cabeca and saida:
            saida[0] = (saida[0][0], cabeca + "\n\n" + saida[0][1])
    return saida or [("", corpo)]


def carta_de(corrida, teto: int) -> list:
    """Uma corrida vira uma ou mais cartas. Devolve dicts prontos para o .jsonl."""
    doc, caminho, ps = corrida
    corpo_todo = limpar("\n\n".join(p.get("corpo") or "" for p in ps))
    if len(corpo_todo) < MIN_CARACTERES:
        return []
    saida = []
    for titulo, corpo in blocos_de_cobertura(corpo_todo):
        saida.extend(_carta_de_bloco(corrida, titulo, corpo, teto))
    return saida


# 🔴 `faceta='documento'` MARCA SECAO QUE NAO E LISTA DE DOCUMENTO
# =============================================================================
# Achado ao LER as cartas geradas, nao ao contar: a "lista de documentos" da
# Yelum equipamentos que saiu na primeira rodada era a lista de OBRIGACOES do
# segurado — "Prestar todas as informacoes", "Tomar as providencias", "Aguardar
# o comparecimento do representante". Nenhum documento. A faceta rotulou a
# secao inteira de "procedimentos em caso de sinistro", e ali dentro ha um
# trecho sobre documentos e outro sobre conduta.
#
# 📊 O subagente ja tinha medido a saida: das 253, **199 (78,7%) citam ao menos
# um nome de documento e 54 nao citam nenhum** — e observou que as 54 "sao as
# secoes de procedimento/prazo, nao de documento — bom sinal de filtro".
#
# Entao o portao e o vocabulario: uma carta que promete lista de documentos tem
# de NOMEAR documentos. Duas citacoes distintas, nao uma — "apolice" sozinha
# aparece em clausula de conduta.
# ⚠️ SÓ NOME DE DOCUMENTO. `apresentar`, `declaracao` e `copia de` estavam aqui
# e sao verbo e forma, nao documento — com eles, `18.9. A Seguradora podera
# contestar o Segurado…` e `18.13. Em hipotese alguma o valor indenizavel…`
# passavam pelo portao como se fossem lista de documentos. Um portao que deixa
# passar clausula de conduta nao esta guardando nada.
_VOCAB_DOC = re.compile(
    r"\bCNH\b|carteira nacional de habilita|\bCRLV\b|\bCRV\b|\bDUT\b|ATPV|"
    r"\bRG\b|\bCPF\b|c[ée]dula de identidade|"
    r"comprovante de (?:resid[êe]ncia|endere[çc]o|rendimento)|"
    r"boletim de ocorr[êe]ncia|nota fiscal|notas fiscais|or[çc]amento|"
    r"laudo|certid[ãa]o|contrato social|procura[çc][ãa]o|dados banc[áa]rios|"
    r"carta de aviso|aviso de sinistro|prontu[áa]rio|atestado|escritura|"
    r"conta de (?:energia|[áa]gua|luz)|contrato de loca[çc][ãa]o|"
    r"carteira de trabalho|formul[áa]rio|recibo|termo de quita[çc][ãa]o|"
    r"\bfotos?\b|filmagem|invent[áa]rio|alvar[áa]|ap[óo]lice|"
    r"registro de (?:im[óo]vel|ativo)|matr[íi]cula do im[óo]vel|"
    r"cart[ãa]o do CNPJ|\bIPTU\b|\bCAT\b|planta baixa|memorial descritivo", re.I)


def nomeia_documentos(texto: str) -> int:
    """Quantos nomes DISTINTOS de documento o texto cita."""
    return len({m.group(0).lower() for m in _VOCAB_DOC.finditer(texto or "")})


def _carta_de_bloco(corrida, titulo: str, corpo: str, teto: int) -> list:
    doc, caminho, ps = corrida
    seg = ps[0]["_seg"]
    ramo = _ramo(ps[0])

    # O PORTAO DE PERTINENCIA. Ver o comentario acima.
    distintos = nomeia_documentos(corpo)
    if distintos < 2:
        _SEM_DOCUMENTO.append({
            "seguradora": seg, "ramo": ramo, "caminho": caminho[:90],
            "chars": len(corpo), "nomes_citados": distintos,
            "unit_ids": [p["unit_id"] for p in ps],
            "amostra": corpo[:120],
        })
        return []

    # O titulo do bloco vence o caminho e o inicio do corpo: ele E a cobertura.
    if titulo:
        sit, fonte, evidencia = None, "bloco(caps)", titulo[:90]
        for nome, rx in _RX_SIT:
            if rx.search(titulo):
                sit = nome
                break
        if sit is None:
            sit, fonte, evidencia = situacao_de(seg, caminho, corpo)
    else:
        sit, fonte, evidencia = situacao_de(seg, caminho, corpo)
    rotulo = _ROTULO_SIT.get(sit, "sinistro")
    nome = _NOME_SEG.get(seg, seg)

    cabecalho = f"Documentos que a {nome} pede para {rotulo}"
    if ramo and ramo != "outro":
        cabecalho += f" no seguro {ramo}"

    # o cabecalho e o rodape de parte custam caracteres — desconte-os do teto
    reserva = len(cabecalho) + 60
    partes = partir(corpo, max(200, teto - reserva))

    # 🔴 "PARTE 17 DE 18" NAO E ENTREGAVEL — 15/08/2026
    # -------------------------------------------------------------------------
    # P-170 manda partir em vez de encurtar, e esta certa. Mas partir uma
    # corrida de 26.000 chars em 18 pedacos produz 18 cartas que ninguem
    # consegue usar: o segurado que pergunta "quais documentos" nao recebe uma
    # lista, recebe um capitulo fatiado.
    #
    # 📊 Duas corridas da Yelum (26.002 e 25.581 chars) nao tem fronteira de
    # cobertura detectavel — o PDF achatou a tabela sem deixar titulo. Elas NAO
    # viram carta: vao para o diagnostico com os `unit_id`, para seccionamento
    # manual.
    #
    # E a razao de registrar em vez de publicar e a mesma das 13 truncadas:
    # **nao completar por deducao, e nao entregar meia coisa como se fosse
    # inteira.** Uma carta que existe e esta errada e pior que uma que falta,
    # porque a que falta aparece na contagem.
    if len(partes) > MAX_PARTES:
        _NAO_PARTICIONAVEIS.append({
            "seguradora": seg, "ramo": ramo, "caminho": caminho,
            "chars": len(corpo), "partes_necessarias": len(partes),
            "itens": len(itens_de(corpo)),
            "unit_ids": [p["unit_id"] for p in ps],
            "motivo": "sem fronteira de cobertura detectavel; "
                      f"exigiria {len(partes)} cartas",
        })
        return []

    saida = []
    for n, parte in enumerate(partes, 1):
        de = f" (parte {n} de {len(partes)})" if len(partes) > 1 else ""
        texto = f"{cabecalho}{de}: {parte}"
        if len(texto) > MAX_CARACTERES:      # cinto e suspensorio
            texto = texto[:MAX_CARACTERES].rsplit(" ", 1)[0]
        if len(texto) < MIN_CARACTERES:
            continue
        saida.append({
            "texto": texto,
            "faceta": "documento",
            "unit_id_origem": ps[0]["unit_id"],
            "caminho": caminho,
            "_seguradora": seg, "_ramo": ramo, "_situacao": sit or "sem_situacao",
            "_fonte_situacao": fonte, "_evidencia": evidencia,
            "_parte": n, "_de": len(partes),
            "_itens_origem": len(itens_de(corpo)),
            # `minimo=1`: a parte ja veio de uma lista detectada — ver `itens_de`
            "_itens_parte": len(itens_de(parte, minimo=1)),
            "_pedacos": [p["unit_id"] for p in ps],
        })
    return saida


# ─────────────────────────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gravar", action="store_true",
                    help="escreve os .jsonl de cartas (senao so mede)")
    args = ap.parse_args()

    segs = sorted(p.name.split("_")[0] for p in PEDACOS.glob("*_pedacos.jsonl.gz"))
    print("=" * 78)
    print("BLOCO 2 — extracao das listas de documentos do BRUTO")
    print("=" * 78)
    print(f"  seguradoras com bruto: {segs}")

    todas, por_seg = [], {}
    for seg in segs:
        ps = carregar(seg)
        for p in ps:
            p["_seg"] = seg
        cs = corridas_de_documento(ps)
        n_doc = sum(1 for p in ps if (p.get("faceta") or "").lower() == "documento")
        n_costurado = sum(len(c[2]) for c in cs)
        cartas = [c for corr in cs for c in carta_de(corr, MAX_CARACTERES)]
        por_seg[seg] = (n_doc, len(cs), n_costurado, cartas)
        todas.extend(cartas)
        print(f"\n  {seg}")
        print(f"    pedacos faceta='documento' ....... {n_doc:5d}")
        print(f"    corridas costuradas .............. {len(cs):5d}")
        print(f"    pedacos apos costura ............. {n_costurado:5d}  "
              f"(+{n_costurado - n_doc} vizinhos que a faceta nao via)")
        print(f"    CARTAS geradas ................... {len(cartas):5d}")

    print("\n" + "=" * 78)
    print("O NUMERO QUE PROVA A SPEC — tamanho das cartas de lista")
    print("=" * 78)
    tam = sorted(len(c["texto"]) for c in todas)
    if tam:
        print(f"  cartas geradas ......... {len(tam):5d}")
        print(f"  tamanho ................ min={tam[0]}  p50={tam[len(tam)//2]}  "
              f"p90={tam[int(len(tam)*.9)]}  max={tam[-1]}")
        print(f"  acima de 1.000 chars ... {sum(1 for t in tam if t > 1000):5d}  "
              f"({100*sum(1 for t in tam if t>1000)/len(tam):.0f}%)")
        print(f"  acima de 1.800 chars ... {sum(1 for t in tam if t > 1800):5d}  "
              f"(tem de ser ZERO)")
        print(f"\n  LINHA DE BASE (a carta de documento de hoje, medida no banco):")
        print(f"    tema documentacao ... p50 = 225")
        print(f"    do acervo ........... p50 = 443")
        print(f"    faceta=documento .... p50 = 489")

    print("\n  --- por situacao ---")
    c = collections.Counter((x["_seguradora"], x["_situacao"]) for x in todas)
    sits = sorted({s for _, s in c})
    print(f"    {'situacao':26s} " + " ".join(f"{s[:8]:>9s}" for s in segs))
    for s in sits:
        print(f"    {s:26s} " + " ".join(f"{c[(g, s)]:9d}" for g in segs))

    print("\n  --- multi-parte (P-170: partir, nunca encurtar) ---")
    multi = collections.Counter(x["_de"] for x in todas)
    for k in sorted(multi):
        print(f"    cartas em {k:2d} parte(s): {multi[k]:5d}")

    print("\n  --- NAO PARTICIONAVEIS (registradas, nao publicadas) ---")
    if not _NAO_PARTICIONAVEIS:
        print("    nenhuma")
    for r in _NAO_PARTICIONAVEIS:
        print(f"    {r['seguradora']:8s} {r['ramo']:12s} {r['chars']:6d} chars, "
              f"exigiria {r['partes_necessarias']:2d} cartas — {r['caminho'][:52]}")
    print(f"    >>> {len(_NAO_PARTICIONAVEIS)} corridas, "
          f"{sum(r['chars'] for r in _NAO_PARTICIONAVEIS):,d} chars fora, "
          f"por decisao explicita")

    print("\n  --- BARRADAS POR NAO NOMEAR DOCUMENTO (portao de pertinencia) ---")
    print(f"    {len(_SEM_DOCUMENTO)} blocos citam menos de 2 nomes de documento")
    for r in _SEM_DOCUMENTO[:6]:
        print(f"    {r['seguradora']:8s} {r['nomes_citados']}x  {r['amostra'][:78]!r}")

    if args.gravar:
        print("\n" + "=" * 78)
        print("GRAVANDO")
        print("=" * 78)
        for seg in segs:
            cartas = por_seg[seg][3]
            if not cartas:
                continue
            destino = CARTAS / seg / "documentos_CARTAS.jsonl"
            destino.parent.mkdir(parents=True, exist_ok=True)
            with destino.open("w", encoding="utf-8") as f:
                for c in cartas:
                    f.write(json.dumps({k: v for k, v in c.items()
                                        if not k.startswith("_")},
                                       ensure_ascii=False) + "\n")
            print(f"  {destino.relative_to(BACKEND)}  ({len(cartas)} cartas)")
        with (CARTAS / "_bloco2_diagnostico.json").open("w", encoding="utf-8") as f:
            json.dump(todas, f, ensure_ascii=False, indent=1)
        print(f"  cartas/_bloco2_diagnostico.json  (com os campos _* de auditoria)")
    else:
        print("\n  (nada gravado — use --gravar)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
