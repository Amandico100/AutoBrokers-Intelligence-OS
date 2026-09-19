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
(`backend/app/data/seguradora-coenti.json` — dentro do pacote desde a
SPEC-EXTRA-001.5.1; em `docs/` sobrou um ponteiro), com os candidatos
avaliados ao lado de cada escolha.

## 🔴 O elo que FECHOU em 04/09/2026 — P-094.1-SIGLA-SEGURADORA

A carteira da corretora **não** traz o nome da seguradora: traz a **SIGLA**.
📊 O dicionário de campos diz, sobre `/documentos_bi.seguradora`: *"sigla da
seguradora EMISSORA; decodifica por `/seguradoras.abreviatura`"* — e o mapa
versionado é indexado pelo **nome canônico** (`porto`, `allianz`), que é a chave
de `portals`. 📊 Medido nesta peça **em 03/09/2026, ANTES do conserto de igualdade**:
`coenti_de("Porto Seguro")` → `05886`, e `coenti_de("PORT")` → **UNKNOWN**.
⚠️ Hoje (04/09/2026) as duas pontas trocaram de lado **por desenho**:
`coenti_de("PORT")` → `05886`, porque a sigla entrou no arquivo revisado; e
`coenti_de("Porto Seguro")` → **UNKNOWN**, porque o casamento parcial foi
removido e nenhuma entidade do censo se chama exatamente *"Porto Seguro"*. O
número desta linha continua valendo como MEDIÇÃO DATADA do que motivou a seção
abaixo — e nunca como descrição do comportamento de hoje.

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
import hashlib
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
    "_conferir_a_ingestao",
    "mapa_de_siglas", "coenti_de",
    "mapa_de_ramos", "cogrupo_de", "nomes_dos_grupos",
    "CAMINHO_DO_MAPA_DE_RAMOS",
    "FalhaDoCenso",
]

PROVIDER_KEY = "susep_ses"

#: 🔴 A resposta de quem não casou. Ela é uma STRING e não `None` de propósito:
#: `None` some numa comparação (`if coenti:`) e vira "não filtrou nada"; a
#: palavra atravessa o pacote inteiro e chega escrita ao leitor.
UNKNOWN = "UNKNOWN"

PREFIXO = "susep/ses"
CHAVE_DO_MANIFESTO = f"{PREFIXO}/manifest.json"

#: 🔴 ONDE OS CATÁLOGOS MORAM — DENTRO DO PACOTE (SPEC-EXTRA-001.5.1, A-bis/E3).
#:
#: `backend/app/data/`. É `app/`, logo é **código**, logo entra no `COPY . .` do
#: `backend/Dockerfile`. 📊 19/09/2026, na cópia que reproduz o contêiner (só
#: `backend/`): os três mapas vinham **vazios** com `[SES] mapa … ausente
#: (FileNotFoundError)`, e `familia_de_acionamento("itau")` devolvia `UNKNOWN` em
#: vez de `porto` — no **caminho vivo do acionamento** (`infocap_tool.py:856`),
#: sem 500 e sem erro. É o mesmo defeito que desligou a Skill de cobertura (D1):
#: dado de runtime morando em `docs/`, que não viaja na imagem.
#:
#: ⚠️ O de `docs/canon/providers/susep/` continua existindo como **PONTEIRO** de
#: cinco linhas — mesma decisão da fatia 1 (ponteiro 88 × cópia com guarda 72):
#: uma fonte só, divergência impossível em vez de detectável depois.
_NO_PACOTE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "data")

_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

#: O caminho histórico, a partir da raiz do REPOSITÓRIO. Continua sendo
#: procurado (uma árvore antiga ainda pode ter o dado ali), mas só DEPOIS do
#: pacote: deixar o `docs/` na frente faria a árvore de desenvolvimento ler um
#: arquivo e produção outro — a cegueira do CLAUDE.md §9.1, uma casa adiante.
_NO_DOCS = os.path.join(_RAIZ, "docs", "canon", "providers", "susep")


def _catalogo(nome: str) -> str:
    """O primeiro caminho que EXISTE, o do pacote primeiro. Nenhum → o do pacote.

    ⚠️ Devolver o do pacote quando nenhum existe é de propósito: é ele que tem de
    existir, e é o nome dele que a mensagem de erro precisa citar.
    """
    for pasta in (_NO_PACOTE, _NO_DOCS):
        caminho = os.path.join(pasta, nome)
        if os.path.isfile(caminho):
            return caminho
    return os.path.join(_NO_PACOTE, nome)


CAMINHO_DO_MAPA = _catalogo("seguradora-coenti.json")
#: 🔴 SPEC-094.1, rodada 3. O SEGUNDO mapa versionado: `ramo da corretora ->
#: grupo de ramo da SUSEP`. Ele é irmão do primeiro e existe pela mesma razão —
#: 📊 comparar a Porto de TODOS os ramos (0,507244) com uma carteira de auto
#: (0,580149) erra por 7,3 p.p. num número de negociação de reajuste.
CAMINHO_DO_MAPA_DE_RAMOS = _catalogo("ramo-cogrupo.json")


def _secao_do_catalogo(caminho: str, secao: str) -> Dict[str, Any]:
    """A seção pedida do catálogo — ou `{}`, **gritando em ERROR**.

    🔴 POR QUE ERROR, E POR QUE NÃO UMA EXCEÇÃO (SPEC-EXTRA-001.5.1, A-bis)
    ======================================================================
    Era `logger.warning("… ausente")` e um `{}` — e um mapa vazio NÃO quebra
    nada: `familia_de_acionamento` só passa a devolver `UNKNOWN` para todo mundo,
    `cogrupo_de` idem. 📊 Em produção isso durou desde que o arquivo existe, sem
    500 e sem ninguém ver. **Degradar em silêncio é o defeito**, e a diferença
    entre `WARNING` e `ERROR` é a diferença entre uma linha que ninguém procura e
    uma que o alerta pega.

    ⛔ E NÃO se levanta exceção: este módulo é lido no caminho vivo do
    acionamento (`infocap_tool.py:856`). Derrubar o atendimento porque um
    catálogo de análise sumiu trocaria um defeito silencioso por um pior.
    A resposta continua sendo `UNKNOWN` — o que muda é que ela grita.

    ⚠️ Um PONTEIRO (o arquivo de `docs/`, que hoje só diz onde o dado mora) cai
    aqui como "seção vazia" e recebe o mesmo tratamento: nunca é carregado como
    se fosse catálogo.
    """
    try:
        with io.open(caminho, encoding="utf-8") as f:
            bruto = json.load(f)
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "[SES] catálogo AUSENTE: seção %r de %s (%s). Procurado em %s e em %s. "
            "Sem ele, familia_de_acionamento/coenti_de/cogrupo_de respondem "
            "UNKNOWN para TUDO — e isso não levanta erro em lugar nenhum.",
            secao, os.path.basename(caminho), type(exc).__name__, _NO_PACOTE, _NO_DOCS)
        return {}
    dados = dict((bruto.get(secao) or {}) if isinstance(bruto, dict) else {})
    if not dados:
        logger.error(
            "[SES] catálogo SEM DADO: %s existe mas a seção %r está vazia ou "
            "ausente (é um ponteiro? o dado mora em %s). Recusado: um mapa vazio "
            "faria UNKNOWN para TUDO, em silêncio.",
            caminho, secao, _NO_PACOTE)
        return {}
    return dados


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
_RAMOS_EM_MEMORIA: Optional[Dict[str, Any]] = None


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
        _MAPA_EM_MEMORIA = _secao_do_catalogo(CAMINHO_DO_MAPA, "seguradoras")
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
        _SIGLAS_EM_MEMORIA = _secao_do_catalogo(CAMINHO_DO_MAPA, "siglas")
    return _SIGLAS_EM_MEMORIA


def mapa_de_ramos(caminho: str = "") -> Dict[str, Any]:
    """`{ABREVIATURA: {cogrupo, grupo_ses, criterio, ...}}` — o mapa do RAMO.

    🔴 SPEC-094.1, rodada 3 de conserto (**P-094.1-RAMO-COGRUPO**). 📊 O defeito
    que ele fecha: `claims.loss_ratio_vs_market` agrupava o mercado **só por
    `coenti`**, então uma carteira de automóvel era comparada com a
    sinistralidade da seguradora inteira — vida, saúde, patrimonial e auto
    somados. Medido em 04/09/2026 na base pública, Porto Seguro (05886),
    202601–202606: **0,580149** no grupo 05 contra **0,507244** em todos os
    ramos. **7,3 pontos percentuais** de diferença, num número que o dono leva
    para uma negociação de reajuste.

    ⛔ A chave é a **ABREVIATURA**, e não o nome nem o código: 📊 é o que a
    carteira traz de verdade (`/documentos_bi.ramo` = `AUTO`, `RESI`, `COND` —
    34 valores distintos em 3.272 linhas de 2025). A cobertura medida desse
    lote é **90,43%**; os 8 rótulos que ficaram fora estão no arquivo, com o
    motivo escrito, para a próxima revisão.

    ⚠️ E ele é um ARQUIVO, nunca uma regra: derivar `AUTO -> 05` por string
    funcionaria até a primeira corretora cuja instalação usa outra abreviatura
    — e aí publicaria a sinistralidade de outro grupo de ramo, sem travar.
    """
    global _RAMOS_EM_MEMORIA
    if caminho:
        with io.open(caminho, encoding="utf-8") as f:
            return dict(json.load(f).get("ramos") or {})
    if _RAMOS_EM_MEMORIA is None:
        _RAMOS_EM_MEMORIA = _secao_do_catalogo(CAMINHO_DO_MAPA_DE_RAMOS, "ramos")
    return _RAMOS_EM_MEMORIA


_FAMILIAS_EM_MEMORIA: Optional[Dict[str, Any]] = None


def mapa_de_familias_de_acionamento(caminho: str = "") -> Dict[str, Any]:
    """`{familia: {nomes_no_sistema_de_gestao, corredor, criterio}}` — a seção
    `familias_de_acionamento` do mesmo arquivo revisado.

    🔴 SPEC-EXTRA-001.1 BLOCO C §5.4. Este conhecimento morava no BRIEFING da
    tool (`infocap_tool.py`, item 5 do bloco do segurado: *"Liberty e Yelum são
    a MESMA seguradora… Itaú = grupo Porto"*). **No prompt ele vale só enquanto
    o modelo obedecer.**

    ⚠️ Isto **não é** o mapa de entidade SUSEP. Identidade (`coenti`) e
    **acionamento** (qual corredor abre o chamado) são perguntas diferentes:
    📊 a sigla `ITAU` é `coenti` UNKNOWN e, ainda assim, aciona pelo corredor
    `porto`. Juntar as duas publicaria o número de outra empresa.
    """
    global _FAMILIAS_EM_MEMORIA
    if caminho:
        with io.open(caminho, encoding="utf-8") as f:
            return dict(json.load(f).get("familias_de_acionamento") or {})
    if _FAMILIAS_EM_MEMORIA is None:
        _FAMILIAS_EM_MEMORIA = _secao_do_catalogo(
            CAMINHO_DO_MAPA, "familias_de_acionamento")
    return _FAMILIAS_EM_MEMORIA


def linha_de_acionamento(nome_ou_sigla: Any, *,
                         mapa: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """A linha inteira do catálogo desta seguradora — ou `None`.

    ⛔ **Igualdade sobre o nome/sigla, sem acento e sem caixa. Nada mais.**
    Nenhum prefixo, nenhum `startswith`, nenhuma derivação: 📊 o censo da
    SPEC-094.1 mediu `SURA` casando dentro de `ASSURANCE` e o token `SEGUROS`
    devolvendo 284 candidatos. Cada linha aqui é uma decisão datada, com o
    critério escrito ao lado dela no arquivo.
    """
    tabela = mapa if mapa is not None else mapa_de_familias_de_acionamento()
    alvo = _sem_acento(nome_ou_sigla).strip()
    if not alvo or not tabela:
        return None
    for familia, linha in tabela.items():
        if not isinstance(linha, dict):
            continue
        nomes = {_sem_acento(n).strip() for n in (linha.get("nomes_no_sistema_de_gestao") or [])}
        nomes.add(_sem_acento(familia).strip())
        if alvo in nomes:
            devolvida = dict(linha)
            devolvida.setdefault("corredor", familia)
            devolvida["familia"] = familia
            return devolvida
    return None


def familia_de_acionamento(nome_ou_sigla: Any, *,
                           mapa: Optional[Dict[str, Any]] = None) -> str:
    """A família de acionamento desta seguradora — ou `"UNKNOWN"`.

    ⚠️ `UNKNOWN` é STRING, como em `coenti_de`/`cogrupo_de`: quem recebe deixa a
    seguradora **como ela veio**, e nunca inventa um corredor.
    """
    linha = linha_de_acionamento(nome_ou_sigla, mapa=mapa)
    if not linha:
        return UNKNOWN
    return str(linha.get("familia") or linha.get("corredor") or UNKNOWN)


def nomes_dos_grupos(caminho: str = "") -> Dict[str, str]:
    """`{"05": "Automovel", ...}` — 📊 os 22 grupos de `ses_gruposramos.csv`."""
    alvo = caminho or CAMINHO_DO_MAPA_DE_RAMOS
    return {str(k): str(v) for k, v in
            _secao_do_catalogo(alvo, "grupos_ses").items()}


def cogrupo_de(ramo: Any, *, mapa: Optional[Dict[str, Any]] = None) -> str:
    """O grupo de ramo da SUSEP deste ramo da corretora — ou `"UNKNOWN"`.

    ⛔ **Igualdade sobre a abreviatura, e nada mais.** Nenhum casamento parcial,
    nenhum prefixo, nenhuma derivação: o defeito que o casamento por palavras
    causou no mapa de seguradoras (`"PORTO SEGURO SAUDE"` recebendo o `coenti`
    da Porto de AUTO) é exatamente o mesmo aqui, com o mesmo custo.

    ⚠️ `UNKNOWN` é STRING. A métrica que a recebe deixa o ramo FORA da
    comparação e escreve o motivo — nunca o conta como zero (M2).
    """
    tabela = mapa if mapa is not None else mapa_de_ramos()
    alvo = _sem_acento(ramo).strip()
    if not alvo or not tabela:
        return UNKNOWN
    linha = tabela.get(alvo)
    if not isinstance(linha, dict):
        # ⚠️ A carteira pode trazer a abreviatura com espaço interno colapsado
        # ("RD E" -> "RD  E"). Colapsar é normalização, e não adivinhação.
        linha = tabela.get(" ".join(alvo.split()))
    if not isinstance(linha, dict):
        return UNKNOWN
    return str(linha.get("cogrupo") or UNKNOWN)


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
    "ilegiveis": ("ilegiveis",),
    "linhas": ("linhas",),
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


def _conferir_a_ingestao(manifesto: Dict[str, Any], objeto: str,
                         corpo: bytes) -> None:
    """A ingestao terminou, e este e o arquivo que ela gravou? Senao, LEVANTA.

    🔴 SPEC-094.1, conserto de 04/09/2026. Duas perguntas, e as duas eram
    silencio antes:

    ```
    a ingestao TERMINOU?    o manifesto so ganha `completo: true` no fim, depois
                            de todos os anos gravados. Sem a marca, o que esta
                            no armazenamento pode ser metade de um ano — e
                            metade de um ano tem CSV valido e conta errada.
    e o arquivo e ESTE?     o `sha256` de cada objeto viaja no manifesto. Um
                            agregado antigo que sobrou de uma ingestao anterior
                            le sem erro e publica o mercado de outro mes.
    ```

    ⛔ As duas falhas viram `FalhaDoCenso`, que a metrica traduz em
    INDISPONIVEL — nunca em sinistralidade zero. E as duas sao afirmacoes sobre
    NOS, e nunca sobre a seguradora.
    """
    if not manifesto:
        raise FalhaDoCenso(
            "nao ha manifesto de ingestao no armazenamento: a Rotina semanal "
            "nao terminou (ou nunca rodou). INDISPONIVEL por ingestao "
            "incompleta — e isto e uma afirmacao sobre NOS")
    if not bool(manifesto.get("completo")):
        raise FalhaDoCenso(
            "o manifesto existe e NAO esta marcado como completo: a ultima "
            "ingestao parou no meio. INDISPONIVEL por ingestao incompleta — "
            "somar um ano gravado pela metade publicaria a sinistralidade do "
            "mercado a partir de um pedaco dele")
    esperados = {str(x.get("objeto") or ""): str(x.get("sha256") or "")
                 for x in (manifesto.get("objetos") or [])
                 if isinstance(x, dict)}
    marca = esperados.get(objeto)
    if not marca:
        raise FalhaDoCenso(
            "o objeto %r nao esta entre os que a ultima ingestao gravou "
            "(%d ano(s)): INDISPONIVEL. Ler um agregado que sobrou de uma "
            "ingestao anterior publica o mercado de outro mes"
            % (objeto, len(esperados)))
    real = hashlib.sha256(corpo).hexdigest()
    if real != marca:
        raise FalhaDoCenso(
            "o agregado %r nao confere com o `sha256` do manifesto "
            "(%s... != %s...): INDISPONIVEL. O arquivo mudou depois da "
            "ingestao, ou a ingestao nao chegou ao fim"
            % (objeto, real[:12], marca[:12]))


def ler_agregado(ano: Any, minio: Any = None, *,
                 competencia_final: str = "",
                 manifesto: Optional[Dict[str, Any]] = None,
                 conferir: bool = True) -> MarketFactSet:
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
    if conferir:
        _conferir_a_ingestao(
            manifesto if manifesto is not None else ler_manifesto(minio),
            objeto, bruto)
    tabela = mapa_de_seguradoras()
    feixe = MarketFactSet(
        provider_key=PROVIDER_KEY, fonte=objeto,
        competencia_final=str(competencia_final or ""),
        # 🔴 O mapa e o casador VIAJAM com o feixe. É o que permite à fórmula
        # cruzar carteira × mercado sem nunca importar este arquivo — o
        # acoplamento que a mutação M1 existe para pegar.
        mapa={chave: str(linha.get("coenti") or UNKNOWN)
              for chave, linha in tabela.items()},
        resolver=coenti_de,
        # 🔴 O casador de RAMO viaja junto, pelo mesmo motivo que o de nome:
        # `comercial/metricas/` nunca importa este arquivo (mutação M1).
        resolver_de_ramo=cogrupo_de,
        mapa_de_ramo={chave: str(linha.get("cogrupo") or UNKNOWN)
                      for chave, linha in mapa_de_ramos().items()},
        nomes_de_grupo=nomes_dos_grupos())
    ilegiveis = 0
    valores_ilegiveis = 0
    # 🔴 SPEC-094.1, conserto de 04/09/2026 — a CELULA DUPLICADA vira AVISO.
    # 📊 O defeito: o leitor somava tudo o que viesse. Duas linhas da mesma
    # `(entidade, competencia, ramo)` — um agregado gravado duas vezes, uma
    # ingestao repetida, um `append` em vez de `put` — dobravam o premio e o
    # sinistro daquela celula em silencio. A sinistralidade continuava
    # plausivel, porque as duas pontas dobravam juntas.
    vistas: Dict[tuple, int] = {}
    duplicadas = 0
    for linha in _linhas_do_objeto(bruto):
        coenti = str(_campo(linha, "coenti") or "").strip()
        damesano = str(_campo(linha, "damesano") or "").strip()
        coramo = str(_campo(linha, "coramo") or "").strip()
        if not coenti or not damesano:
            ilegiveis += 1
            continue
        chave = (coenti, damesano, coramo)
        if chave in vistas:
            duplicadas += 1
            continue
        vistas[chave] = 1
        sinistro = _float(_campo(linha, "sinistro_ocorrido"))
        marcado = str(_campo(linha, "estorno") or "").strip().upper() in ("T", "TRUE", "1")
        try:
            nao_lidos = int(str(_campo(linha, "ilegiveis") or 0) or 0)
        except (TypeError, ValueError):
            nao_lidos = 0
        valores_ilegiveis += nao_lidos
        feixe.facts.append(MarketFact(
            coenti=coenti, damesano=damesano, coramo=coramo,
            premio_ganho=_float(_campo(linha, "premio_ganho")),
            sinistro_ocorrido=sinistro,
            # 🔴 O negativo e estorno de provisao, e a marca sobrevive a
            # travessia: quem grava pode nao a ter escrito, mas o sinal do
            # numero nao mente.
            estorno=marcado or sinistro < 0,
            ilegiveis=nao_lidos))
    if ilegiveis:
        feixe.warnings.append(
            f"{ilegiveis} celula(s) do agregado sem entidade ou competencia: "
            f"fora da conta, e declaradas — nunca somadas como zero")
    if duplicadas:
        feixe.warnings.append(
            f"🔴 {duplicadas} celula(s) DUPLICADA(S) no agregado (mesma "
            f"entidade, competencia e ramo): a repetida ficou FORA da conta. "
            f"Somar as duas dobraria premio e sinistro juntos, e a "
            f"sinistralidade continuaria plausivel — que e a forma silenciosa "
            f"de errar")
    if valores_ilegiveis:
        feixe.warnings.append(
            f"{valores_ilegiveis} valor(es) da base publica vieram ILEGIVEIS e "
            f"ficaram FORA da soma: o premio ganho do mercado e um PISO, e a "
            f"confianca do numero sai rebaixada — nunca contados como zero")
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
