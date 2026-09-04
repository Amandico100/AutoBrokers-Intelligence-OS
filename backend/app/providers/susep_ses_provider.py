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

## 🔴 O elo que FECHOU em 04/09/2026 — P-094.1-SIGLA-SEGURADORA

A carteira da corretora **não** traz o nome da seguradora: traz a **SIGLA**.
📊 O dicionário de campos diz, sobre `/documentos_bi.seguradora`: *"sigla da
seguradora EMISSORA; decodifica por `/seguradoras.abreviatura`"* — e o mapa
versionado é indexado pelo **nome canônico** (`porto`, `allianz`), que é a chave
de `portals`. 📊 Medido nesta peça: `coenti_de("Porto Seguro")` → `05886`, e
`coenti_de("PORT")` → **UNKNOWN**.

✅ **O conserto:** o mapa versionado ganhou uma seção `siglas`, construída a
partir das **61 entradas do censo `/seguradoras` da corretora piloto** — uma por
igualdade de nome COMPLETO com o censo público, treze por decisão explícita
revisada por gente, cada uma com o critério escrito ao lado. 📊 A cobertura de
prêmio da carteira viva subiu de **12,35%** para **83,86%** (R$ 21.814.941,56 em
3.861 linhas de 2025). O que não casou sai `UNKNOWN` **com o nome listado no
arquivo**, para a próxima revisão.

⚠️ E a seção é um ARQUIVO, não uma regra: 📊 inventar `PORT → porto` por
derivação funcionaria até a primeira corretora cuja instalação usa outra sigla —
e aí publicaria o número de outra empresa. Cada linha é uma decisão datada.

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
    "ler_agregado", "ler_manifesto", "mapa_de_seguradoras",
    "mapa_de_siglas", "coenti_de",
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
_SIGLAS_EM_MEMORIA: Optional[Dict[str, Any]] = None


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


def mapa_de_siglas(caminho: str = "") -> Dict[str, Any]:
    """`{SIGLA: {coenti, nome_no_sistema_de_gestao, criterio}}` — o elo que
    faltava, e ele e um ARQUIVO REVISADO.

    🔴 SPEC-094.1, conserto de 04/09/2026 (**P-094.1-SIGLA-SEGURADORA**).
    📊 A carteira nao traz o nome da seguradora: traz a SIGLA (`PORT`, `ALLI`,
    `TMAR`, `LIBE`, `BRAD`…), e o mapa canonico era indexado pelo nome
    (`porto`, `allianz`). Medido antes do conserto: **12,35%** do premio da
    carteira casava com uma entidade; depois, **83,86%**.

    ⛔ Uma sigla so entra no arquivo por igualdade de nome COMPLETO com o nome
    da entidade no censo publico, ou por DECISAO EXPLICITA de gente, escrita ao
    lado com o criterio. Nunca por derivacao de string em runtime.
    """
    global _SIGLAS_EM_MEMORIA
    if caminho:
        with io.open(caminho, encoding="utf-8") as f:
            return dict(json.load(f).get("siglas") or {})
    if _SIGLAS_EM_MEMORIA is None:
        try:
            with io.open(CAMINHO_DO_MAPA, encoding="utf-8") as f:
                _SIGLAS_EM_MEMORIA = dict(json.load(f).get("siglas") or {})
        except Exception as exc:  # noqa: BLE001
            logger.warning("[SES] mapa de siglas ausente (%s)",
                           type(exc).__name__)
            _SIGLAS_EM_MEMORIA = {}
    return _SIGLAS_EM_MEMORIA


def coenti_de(nome: Any, *, mapa: Optional[Dict[str, Any]] = None,
              siglas: Optional[Dict[str, Any]] = None) -> str:
    """O `coenti` desta seguradora — ou `UNKNOWN`. ⛔ **Nunca um palpite.**

    As tres tentativas, todas por IGUALDADE, e ela para na primeira que casar:

    ```
    1  a SIGLA, no mapa de siglas revisado     "PORT"        -> 05886
    2  a CHAVE canonica do mapa                "porto"       -> 05886
    3  o NOME COMPLETO normalizado             "PORTO SEGURO COMPANHIA DE
                                                SEGUROS GERAIS" -> 05886
    ```

    🔴 **O casamento PARCIAL foi removido em 04/09/2026, e a remocao e a peca.**
    📊 O defeito medido: a regra anterior comparava PALAVRAS. `"PORTO SEGURO
    SAUDE"` compartilha `PORTO` e `SEGURO` com a entrada da Porto de AUTO, e
    recebia o `coenti` **05886** — o da seguradora de automovel. A
    sinistralidade publicada seria a de outra empresa, num numero que o dono
    leva para uma negociacao de reajuste.

    ⚠️ Um nome que nao casa por igualdade sai `UNKNOWN`, e `UNKNOWN` e uma
    STRING: `None` some numa comparacao e vira "nao filtrou nada"; a palavra
    atravessa o pacote e chega escrita ao leitor. A metrica que a recebe sai
    INDISPONIVEL, e nunca zero (M2).
    """
    tabela = mapa if mapa is not None else mapa_de_seguradoras()
    das_siglas = siglas if siglas is not None else mapa_de_siglas()
    alvo = _sem_acento(nome).strip()
    if not alvo:
        return UNKNOWN

    # 1 — a SIGLA. Ela vem primeiro porque e o que a carteira REALMENTE traz.
    linha = das_siglas.get(alvo)
    if isinstance(linha, dict):
        return str(linha.get("coenti") or UNKNOWN)

    if not tabela:
        return UNKNOWN

    # 2 — a chave canonica, na forma em que ela e escrita no arquivo.
    chave_direta = alvo.lower().replace(" ", "_").replace("-", "_")
    if chave_direta in tabela:
        return str(tabela[chave_direta].get("coenti") or UNKNOWN)

    # 3 — o nome COMPLETO da entidade, sem acento e com espaco colapsado.
    #     ⛔ Igualdade, e nada mais: um nome que casa com DUAS entradas nao e
    #     um empate a desempatar, e sim uma pergunta sem resposta.
    inteiro = " ".join(alvo.split())
    casados = [chave for chave, linha in tabela.items()
               if " ".join(_sem_acento(linha.get("noenti_susep")).split()) == inteiro]
    if len(casados) == 1:
        return str(tabela[casados[0]].get("coenti") or UNKNOWN)
    return UNKNOWN


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
    tabela = mapa_de_seguradoras()
    feixe = MarketFactSet(
        provider_key=PROVIDER_KEY, fonte=objeto,
        competencia_final=str(competencia_final or ""),
        # 🔴 O mapa e o casador VIAJAM com o feixe. É o que permite à fórmula
        # cruzar carteira × mercado sem nunca importar este arquivo — o
        # acoplamento que a mutação M1 existe para pegar.
        mapa={chave: str(linha.get("coenti") or UNKNOWN)
              for chave, linha in tabela.items()},
        resolver=coenti_de)
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
