# -*- coding: utf-8 -*-
"""O conector público SUSEP SES — SPEC-094.1 · BLOCO B. **Ele só lê o MinIO.**

🔴 **Não existe cliente HTTP neste arquivo, e é a propriedade central dele.**
Quem vai à fonte é a Rotina (`app/services/susep_ses_ingest.py`), no worker, sob
lease com heartbeat, uma vez por semana. Aqui só se lê o **agregado** que ela
gravou — 💭 poucos MB — e a razão está medida: o arquivo público tem **571 MB**,
e abri-lo no caminho quente do chat significaria meio giga de I/O por pergunta.

```
Rotina semanal  →  agrega  →  MinIO (susep/ses/<ano>.csv)  →  ESTE conector  →  MarketFactSet
   worker                         bytes                         leitura            registry
```

## Por que ele não tem credencial, e por que isso importa

📊 A base é pública: sem login, sem chave, sem contrato (censo do BLOCO 0). Ele
é o **molde do conector público** que ANS, BACEN e FIPE vão seguir — e a
diferença para um conector com credencial está escrita em
`CAMADAS-DE-CONEXAO.md`. Um conector público que ganhasse um `resolver` de
conexão convidaria o próximo a ganhar também.

## O mapa `seguradora → coenti` é VERSIONADO, e nunca recalculado em runtime

🔴 **Nome não é chave.** 📊 O censo mediu: buscar o token `SEGUROS` devolveu
**284 candidatos** e `SURA` devolveu **130** (casa dentro de "ASSURANCE"). O
desempate que funcionou foi *prêmio de auto > 0 no trimestre* — uma medição, não
uma regra de string. Por isso o mapa é um arquivo revisado por gente
(`docs/canon/providers/susep/seguradora-coenti.json`), com os candidatos
avaliados ao lado de cada escolha.

## 🔴 O elo que ainda não fecha, medido em 03/09/2026 — P-094.1-SIGLA-SEGURADORA

A carteira da corretora **não** traz o nome da seguradora: traz a **SIGLA**.
📊 O dicionário de campos diz, sobre `/documentos_bi.seguradora`: *"sigla da
seguradora EMISSORA; decodifica por `/seguradoras.abreviatura`"* — e o mapa
versionado é indexado pelo **nome canônico** (`porto`, `allianz`), que é a chave
de `portals`. 📊 Medido nesta peça: `coenti_de("Porto Seguro")` → `05886`, e
`coenti_de("PORT")` → **UNKNOWN**.

⚠️ Consequência, escrita antes que alguém a descubra num relatório: enquanto
`/seguradoras` não for lida, o cruzamento carteira × mercado devolve
**UNAVAILABLE por mapa** na fonte piloto. Isso é o comportamento CERTO (M2) e um
resultado VAZIO ao mesmo tempo — as duas coisas, juntas. O conserto é uma rota a
mais no adapter (`/seguradoras`, sigla → nome), não uma tabela de palpites aqui:
📊 inventar `PORT → porto` funcionaria até a primeira corretora cuja instalação
usa outra sigla, e aí publicaria o número de outra empresa.

🔴 **E o que não casa sai `UNKNOWN`, nunca omitido e nunca zero (M2).** 📊 Há
**11 entidades "SUL AMERICA"** e nenhuma tem prêmio de auto no trimestre medido:
escolher pelo nome seria publicar o número de outra empresa. *"A sua seguradora
sinistra 0% acima do mercado"* é uma frase que o dono usaria numa negociação de
reajuste — e ela seria falsa.
"""
from __future__ import annotations

import csv
import io
import json
import logging
import os
import unicodedata
from typing import Any, Dict, List, Optional

from app.comercial.cbim import MarketFact, MarketFactSet

logger = logging.getLogger(__name__)

__all__ = [
    "PROVIDER_KEY", "UNKNOWN", "PREFIXO", "CHAVE_DO_MANIFESTO",
    "ler_agregado", "ler_manifesto", "mapa_de_seguradoras", "coenti_de",
    "FalhaDoCenso",
]

PROVIDER_KEY = "susep_ses"

#: 🔴 A resposta de quem não casou. Ela é uma STRING e não `None` de propósito:
#: `None` some numa comparação (`if coenti:`) e vira "não filtrou nada"; a
#: palavra atravessa o pacote inteiro e chega escrita ao leitor.
UNKNOWN = "UNKNOWN"

PREFIXO = "susep/ses"
CHAVE_DO_MANIFESTO = f"{PREFIXO}/manifest.json"

_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
CAMINHO_DO_MAPA = os.path.join(_RAIZ, "docs", "canon", "providers", "susep",
                               "seguradora-coenti.json")


class FalhaDoCenso(RuntimeError):
    """O agregado do mercado não está no MinIO, ou está com outra forma.

    ⚠️ Tipo próprio para que a métrica consiga dizer *"o censo do mercado ainda
    não rodou"* — que é uma afirmação sobre NÓS — em vez de deixar o leitor
    achar que a seguradora não tem sinistro.
    """


# --------------------------------------------------------------------------
# O mapa versionado
# --------------------------------------------------------------------------
_MAPA_EM_MEMORIA: Optional[Dict[str, Any]] = None


def mapa_de_seguradoras(caminho: str = "") -> Dict[str, Any]:
    """`{chave_canonica: {coenti, noenti_susep, auto_ativo_em_202606, nota}}`.

    ⚠️ Lido uma vez por processo. Não é cache de dado vivo: é um arquivo do
    repositório, e ele só muda quando alguém commita uma revisão.
    """
    global _MAPA_EM_MEMORIA
    if caminho:
        with io.open(caminho, encoding="utf-8") as f:
            return dict(json.load(f).get("seguradoras") or {})
    if _MAPA_EM_MEMORIA is None:
        try:
            with io.open(CAMINHO_DO_MAPA, encoding="utf-8") as f:
                _MAPA_EM_MEMORIA = dict(json.load(f).get("seguradoras") or {})
        except Exception as exc:  # noqa: BLE001
            logger.warning("[SES] mapa de seguradoras ausente (%s)",
                           type(exc).__name__)
            _MAPA_EM_MEMORIA = {}
    return _MAPA_EM_MEMORIA


def _sem_acento(texto: Any) -> str:
    bruto = unicodedata.normalize("NFKD", str(texto or ""))
    return "".join(c for c in bruto if not unicodedata.combining(c)).upper()


def _palavras(texto: Any) -> List[str]:
    limpo = "".join(c if c.isalnum() else " " for c in _sem_acento(texto))
    # ⚠️ As palavras que não distinguem NINGUÉM saem: 📊 "SEGUROS" casa 284
    # entidades. Deixá-las na comparação faria qualquer nome casar com qualquer
    # seguradora — que é como um mapa por nome nasce errado.
    genericas = {"SEGUROS", "SEGURADORA", "SEGURO", "CIA", "COMPANHIA", "S",
                 "A", "SA", "DE", "DA", "DO", "E", "GERAIS", "LTDA", "BRASIL"}
    return [p for p in limpo.split() if p and p not in genericas]


def coenti_de(nome: Any, *, mapa: Optional[Dict[str, Any]] = None) -> str:
    """O `coenti` desta seguradora — ou `UNKNOWN`. ⛔ Nunca um palpite.

    A ordem das tentativas é do mais forte para o mais fraco, e ela para na
    primeira que casar:

    ```
    1  a CHAVE canônica do mapa           `porto` -> 05886
    2  as palavras da chave               "Porto Seguro" -> porto
    3  as palavras do nome no SES         "PORTO SEGURO COMPANHIA..." -> porto
    ```

    🔴 Um nome que case com DUAS entradas devolve `UNKNOWN`. Empate não é
    escolha: 📊 é exatamente o caso da `sulamerica` (11 entidades), e resolver
    empate pela ordem do dicionário é publicar o número de outra empresa.
    """
    tabela = mapa if mapa is not None else mapa_de_seguradoras()
    if not tabela:
        return UNKNOWN
    alvo = _sem_acento(nome).strip()
    if not alvo:
        return UNKNOWN

    chave_direta = alvo.lower().replace(" ", "_").replace("-", "_")
    if chave_direta in tabela:
        return str(tabela[chave_direta].get("coenti") or UNKNOWN)

    tokens = set(_palavras(alvo))
    if not tokens:
        return UNKNOWN
    candidatos = set()
    for chave, linha in tabela.items():
        if set(_palavras(chave.replace("_", " "))) & tokens:
            candidatos.add(chave)
            continue
        if set(_palavras(linha.get("noenti_susep") or "")) & tokens:
            candidatos.add(chave)
    if len(candidatos) != 1:
        return UNKNOWN
    return str(tabela[candidatos.pop()].get("coenti") or UNKNOWN)


# --------------------------------------------------------------------------
# A leitura do agregado
# --------------------------------------------------------------------------
#: Os nomes que o agregado pode usar para a mesma coisa. 🔴 A lista existe
#: porque a coluna é a MESMA em qualquer forma: o ingestor escreve o nome do
#: campo do SES (`premio_ganho`), e um agregado escrito por outra ferramenta usa
#: o nome curto. Aceitar os dois custa uma linha; recusar um deles faria o
#: leitor depender de quem escreveu, e não do que está escrito.
_ALIAS = {
    "coenti": ("coenti", "entidade"),
    "damesano": ("damesano", "competencia", "mes"),
    "coramo": ("coramo", "ramo"),
    "premio_ganho": ("premio_ganho", "premio"),
    "sinistro_ocorrido": ("sinistro_ocorrido", "sinistro"),
    "estorno": ("estorno",),
}


def _campo(linha: Dict[str, Any], nome: str) -> Any:
    for alias in _ALIAS[nome]:
        if alias in linha:
            return linha[alias]
    return None


def _float(v: Any) -> float:
    s = str(v if v is not None else "").strip()
    if not s:
        return 0.0
    try:
        return float(s.replace(".", "").replace(",", ".")) if "," in s else float(s)
    except (TypeError, ValueError):
        return 0.0


def _linhas_do_objeto(bruto: bytes) -> List[Dict[str, Any]]:
    """As linhas do agregado, seja ele CSV ou JSON.

    🔴 A forma que a Rotina grava é **CSV** — pequeno, streamável, com o
    cabeçalho do contrato. O JSON é aceito porque é a MESMA tabela com as
    mesmas colunas, e um leitor que só aceitasse um byte-format obrigaria quem
    quisesse conferir a conta a escrever um gravador de CSV antes.

    ⚠️ E a decisão é por CONTEÚDO, não por extensão: um `.csv` com JSON dentro
    é um defeito de quem gravou, e adivinhar pelo nome esconderia isso.
    """
    texto = bruto.decode("utf-8", errors="replace").lstrip("﻿").strip()
    if not texto:
        return []
    if texto[0] in "[{":
        dado = json.loads(texto)
        if isinstance(dado, dict):
            dado = dado.get("linhas") or dado.get("celulas") or []
        return [x for x in dado if isinstance(x, dict)]
    leitor = csv.DictReader(io.StringIO(texto), delimiter=";")
    return [dict(x) for x in leitor]


def ler_agregado(ano: Any, minio: Any = None, *,
                 competencia_final: str = "") -> MarketFactSet:
    """O `MarketFactSet` de UM ano, lido do MinIO. ⛔ **Nunca da rede.**

    `minio` é injetável para que a prova rode sem infraestrutura; em produção
    nasce de `MinioService()`, que é quem sabe o bucket e as credenciais.

    🔴 O feixe é de PLATAFORMA e **não carrega `company_id`**: a estatística
    pública é a mesma para todas as corretoras, e uma cópia por casa é a
    primeira porta para elas divergirem.
    """
    if minio is None:
        from app.services.minio_service import MinioService

        minio = MinioService()

    objeto = f"{PREFIXO}/{ano}.csv"
    try:
        corpo = minio.download_file(objeto)
    except Exception as exc:  # noqa: BLE001
        raise FalhaDoCenso(
            f"o agregado do mercado de {ano} nao esta no armazenamento "
            f"({objeto}): a Rotina semanal ainda nao rodou "
            f"({type(exc).__name__}). Isto e uma afirmacao sobre NOS, e nunca "
            f"sobre a sinistralidade da seguradora") from exc

    bruto = corpo.read() if hasattr(corpo, "read") else bytes(corpo or b"")
    feixe = MarketFactSet(provider_key=PROVIDER_KEY, fonte=objeto,
                          competencia_final=str(competencia_final or ""))
    ilegiveis = 0
    for linha in _linhas_do_objeto(bruto):
        coenti = str(_campo(linha, "coenti") or "").strip()
        damesano = str(_campo(linha, "damesano") or "").strip()
        coramo = str(_campo(linha, "coramo") or "").strip()
        if not coenti or not damesano:
            ilegiveis += 1
            continue
        sinistro = _float(_campo(linha, "sinistro_ocorrido"))
        marcado = str(_campo(linha, "estorno") or "").strip().upper() in ("T", "TRUE", "1")
        feixe.facts.append(MarketFact(
            coenti=coenti, damesano=damesano, coramo=coramo,
            premio_ganho=_float(_campo(linha, "premio_ganho")),
            sinistro_ocorrido=sinistro,
            # 🔴 O negativo é estorno de provisão, e a marca sobrevive à
            # travessia: quem grava pode não a ter escrito, mas o sinal do
            # número não mente.
            estorno=marcado or sinistro < 0))
    if ilegiveis:
        feixe.warnings.append(
            f"{ilegiveis} celula(s) do agregado sem entidade ou competencia: "
            f"fora da conta, e declaradas — nunca somadas como zero")
    if not feixe.facts:
        feixe.warnings.append(
            f"o agregado {objeto} respondeu e nao tem celula nenhuma: "
            f"INDISPONIVEL por acervo, e nunca sinistralidade zero")
    return feixe


def ler_manifesto(minio: Any = None) -> Dict[str, Any]:
    """O manifesto da última ingestão: `sha256`, `Last-Modified`, competência.

    🔴 É ele que sustenta o ponteiro do Evidence Pack — 📊 a base fecha em
    **202606**, e quem lê em setembro está comparando com junho. Um cruzamento
    que esconde a defasagem responde certo sobre o mês errado.
    """
    if minio is None:
        from app.services.minio_service import MinioService

        minio = MinioService()
    try:
        corpo = minio.download_file(CHAVE_DO_MANIFESTO)
        bruto = corpo.read() if hasattr(corpo, "read") else bytes(corpo or b"")
        return json.loads(bruto.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        logger.info("[SES] manifesto ausente (%s)", type(exc).__name__)
        return {}
