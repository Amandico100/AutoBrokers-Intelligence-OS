# -*- coding: utf-8 -*-
"""O adapter InfoCap — SPEC-094 BLOCO B. **A única peça que fala InfoCap.**

🔴 Este é o ÚNICO módulo, fora de `app/comercial/fonte_infocap.py`, autorizado
a saber que existe `nosnum`, `val_c`, `inivig`, `fimvig`, `codfil` ou
`prod_docs`. O guarda mede isso por `grep`:

```
grep -rn "nosnum\\|val_c\\|inivig\\|fimvig\\|codfil" backend/app/comercial/ backend/app/agents/tools/ \\
  | grep -v fonte_infocap.py | grep -v infocap_analytics_provider.py     →  0
```

Ele **envolve** `FonteInfocap`; não a reescreve. Autenticação, retry, fatiamento
por ano, cache e semântica de erro continuam lá — 📊 sete armadilhas medidas em
18/08/2026 que ninguém quer redescobrir (`fonte_infocap.py:18-64`). O que muda
aqui é só a TRADUÇÃO: linha crua → fato canônico.

## As quatro decisões que este arquivo carrega, e o número de cada uma

**1. Ilegível vira `UNAVAILABLE`, com warning.** ⛔ Este módulo **não usa
`_num()`** para dinheiro. 📊 `fonte_infocap._num(None)` devolve `0.0`
(`:514-530`, SPEC §1.5) — e um `0.0` que atravessa a fronteira é
indistinguível de "a corretora não ganhou nada". Aqui usa-se
`cbim.interpretar_dinheiro`, que devolve `None` para ilegível, e o `None` vira
`UNAVAILABLE` **mais um warning com o `correlation_id`** — que é a
recomendação literal da [ACL da AWS][acl] (`Int32.TryParse` devolve
`BadRequest`, não `0`).

**2. O repasse soma TODOS os `prod_docs`.** 📊 O censo mediu, na mesma apólice,
`ordem 1 = 4%` e `ordem 2 = 15%`: **`ordem == 1` não é o maior repasse.** A 081
usa só a ordem 1 — e está certa para o que ela faz, que é dizer *quem vendeu*.
Está errada para dizer *quanto saiu*. Somar só a ordem 1 subestimaria o repasse
e inflaria a contribuição pós-repasse, que é um número que o dono lê.

**3. A conexão é a autoridade, não o nome da corretora.** 📊 Nesta máquina não
existe nenhuma variável `CORP_INFOCAP_*` (SPEC §1.4): o caminho por nome
**não funciona** localmente e o caminho pela conexão funciona. E o resolver por
conexão **já existia** (`infocap_connector.py:725-757`, 4 chamadas do conector
de atendimento) — escrever um segundo seria motor paralelo (CLAUDE.md §5).

**4. 🔴 Conta compartilhada RECUSA.** 📊 As conexões `connected` da Amandus e da
Resulta descriptografam para o MESMO login e devolvem carteira idêntica ao
centavo. Ver `RecusaDeContaCompartilhada` e a decisão **F-094-07**.

[acl]: https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/acl.html
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import unicodedata
import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.comercial.cbim import (
    ACTIVE,
    CANCELLED,
    CLAIM_CLOSED,
    CLAIM_CLOSED_DENIED,
    CLAIM_CLOSED_PAID,
    POP_CANCELLATIONS,
    POP_CLAIMS,
    POP_CUSTOMERS,
    POP_POLICIES,
    POP_QUOTES,
    STATUS_DE_APOLICE,
    CLAIM_OPEN,
    CLAIM_UNKNOWN,
    ENDORSEMENT,
    NEW,
    RENEWAL,
    UNAVAILABLE,
    UNKNOWN,
    ClaimFact,
    CommissionFact,
    CustomerPortfolioFact,
    FactSet,
    Money,
    PolicyFact,
    ProducerAssignmentFact,
    Provenance,
    QuoteFact,
    RenewalFact,
    claim_ref,
    customer_ref,
    interpretar_dinheiro,
    policy_ref,
    producer_ref,
    quote_ref,
    status_de_apolice,
)
from app.comercial.manifesto import SEM_AMOSTRA
from app.core.feature_flags import env_ligada
from app.providers.brokerage_analytics_provider import (
    FalhaDoProvider,
    RecusaDeContaCompartilhada,
    register_brokerage_analytics_provider,
)

logger = logging.getLogger(__name__)

PROVIDER_KEY = "infocap"

#: Onde o censo do BLOCO 0 mora. É arquivo versionado de propósito: o mesmo
#: mecanismo do mapa de produtor, e o mesmo motivo — 📊 a única coluna `jsonb`
#: de `companies` é `acionamento_profile`, que é outra coisa.
_CENSO = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))),
    "docs", "canon", "providers", "infocap")
#: ⚠️ Quem LÊ o censo é `app/comercial/manifesto.py` (BLOCO C). Este caminho
#: fica aqui só como referência de onde o arquivo mora — o adapter não abre JSON.
_MANIFESTO_JSON = os.path.join(_CENSO, "infocap-capability-manifest.json")


# ==========================================================================
# 🔴 O GATE DE CONTA COMPARTILHADA — P1 cross-tenant do censo (F-094-07)
# ==========================================================================
#
# `account_fingerprint → company_id`, por PROCESSO. Não é cache e não é
# persistência: é a memória de quem já leu por esta conta nesta instância.
#
# ⚠️ E ele é deliberadamente pequeno. Um gate perfeito exigiria uma tabela e
# uma migration; este pega o caso REAL medido — duas corretoras servidas pelo
# mesmo `smith-api` — e para a segunda. O que ele não pega (dois contêineres)
# está na pendência P-094-CONTA-COMPARTILHADA, que é do Founder e é P1.
_CONTAS_EM_USO: Dict[str, str] = {}


def _e_cliente_sincrono(obj: Any) -> bool:
    """É o `Client` SÍNCRONO do supabase-py? 🔴 Um `await` sobre ele levanta."""
    try:
        from supabase import Client as _ClienteSincrono
    except Exception:  # noqa: BLE001
        return False
    return isinstance(obj, _ClienteSincrono)


def _tem_table(obj: Any) -> bool:
    """O objeto é um CLIENTE CRU — `.table(...)` nele mesmo, sem `.client`?"""
    return callable(getattr(obj, "table", None))


def _agora_utc() -> str:
    """O instante, em UTC e COM fuso escrito. 🔴 Nunca `datetime.now()` cru.

    📊 Achado pelo juiz em 03/09/2026, na peça viva: o mesmo relatório gravou
    `artifacts.created_at = 23:03:58Z` e `tenant_connections.last_used_at =
    20:05:07Z` — três horas NO PASSADO para um uso que acabara de acontecer.
    A coluna é `timestamptz`; `datetime.now()` devolve a hora LOCAL do
    contêiner **sem fuso**, e o Postgres lê o que chega sem fuso como se já
    fosse UTC. O relógio da telemetria passa a discordar do relógio da entrega,
    e quem for depurar "esta conexão foi usada?" lê a hora errada.
    """
    return datetime.now(timezone.utc).isoformat()


def impressao_da_conta(login: str) -> str:
    """`sha256(login)[:12]`. 🔴 NUNCA o login — presença, nunca o valor."""
    return hashlib.sha256(str(login or "").strip().lower().encode("utf-8")).hexdigest()[:12]


def registrar_conta(account_fingerprint: str, company_id: str) -> None:
    """Marca a conta como em uso por esta corretora — ou RECUSA.

    O par (fingerprint, company_id) é idempotente: a mesma corretora relendo a
    mesma conta passa sempre. Corretora **diferente** na mesma conta para.
    """
    fp = str(account_fingerprint or "").strip()
    empresa = str(company_id or "").strip()
    if not fp or not empresa:
        return
    dono = _CONTAS_EM_USO.get(fp)
    if dono and dono != empresa:
        # 🔴 O LOG NOMEIA AS DUAS CORRETORAS E O FINGERPRINT TRUNCADO.
        #
        # 📊 Achado pela lente do dado, 03/09/2026: a regra em vigor é *"o
        # primeiro que chega ganha"*. Se a Amandus lê primeiro, a Resulta é
        # recusada até o processo reiniciar — e a recusa dizia apenas "conexão
        # compartilhada com outra corretora", sem dizer QUAL. Quem atende o
        # chamado não tinha como saber onde mexer, e o suporte pediria os logs
        # de dois tenants para descobrir o que o gate já sabia.
        #
        # ⛔ `company_id` é identificador de tenant, e não dado de pessoa. O
        # LOGIN nunca aparece: só a impressão dele, truncada.
        logger.error(
            "[094] conta compartilhada RECUSADA: fingerprint %s… ja em uso por "
            "company_id=%s; pedido por company_id=%s (F-094-07)",
            fp[:8], dono, empresa)
        raise RecusaDeContaCompartilhada(
            "conexão compartilhada com outra corretora — decisão F-094-07. "
            "Duas corretoras ativas apontam para a MESMA conta do provider "
            f"(impressão {fp[:8]}…), e esta conta já está sendo lida pela "
            f"corretora {dono}. A leitura da corretora {empresa} mostraria a "
            "carteira da primeira, então foi recusada e nenhum Artifact é "
            "publicado. ⚠️ Quem chegou primeiro ganha a conta até o processo "
            "reiniciar: a resolução definitiva é a decisão F-094-07 "
            "(P-094-CONTA-COMPARTILHADA).")
    _CONTAS_EM_USO[fp] = empresa


def esquecer_contas() -> None:
    """Zera a memória de contas. Para testes — e só para testes."""
    _CONTAS_EM_USO.clear()


def contas_em_uso() -> Dict[str, str]:
    return dict(_CONTAS_EM_USO)


# ==========================================================================
# A chave de cache — 🔴 company_id E connection_id, sempre os dois
# ==========================================================================
def chave_de_cache(company_id: str, connection_id: str) -> str:
    """O rótulo que vai para `FonteInfocap._get` e entra na chave do Redis.

    🔴 Os DOIS pedaços são obrigatórios, e cada um paga uma dívida:

    ```
    company_id     sem ele, duas corretoras pedindo o mesmo período leriam a
                   carteira uma da outra — cross-tenant por cache, a forma mais
                   silenciosa desse defeito (é a mutação M11)
    connection_id  a corretora que troca a conexão da InfoCap precisa ler a
                   fonte NOVA, e não a resposta guardada pela conexão velha
    ```
    """
    empresa = str(company_id or "").strip()
    conexao = str(connection_id or "").strip()
    if not empresa:
        raise ValueError(
            "chave de cache sem company_id: seria cross-tenant por cache (M11)")
    return f"{empresa}:{conexao}"


# ==========================================================================
# Traduções puras — a fronteira, e nada além dela
# ==========================================================================
_RE_ISO = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")
_RE_BR = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})")


def _data(v: Any) -> Optional[date]:
    """`2025-03-14` ou `14/03/2025` → `date`. Ilegível → `None`.

    📊 A InfoCap devolve as duas formas, em campos diferentes da mesma resposta
    (`calculos._mes_de:456-471` já registrava isso). `None` aqui é honesto:
    uma vigência que não se consegue ler não entra em período nenhum.
    """
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v or "").strip()
    m = _RE_ISO.match(s)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    m = _RE_BR.match(s)
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            return None
    return None


#: 🔴 O SEPARADOR NÃO É DETALHE. Ver `impressao_da_rota`.
SEPARADOR_DA_IMPRESSAO = "|"


def impressao_da_rota(linhas: List[Dict[str, Any]]) -> str:
    """`sha256` das chaves ORDENADAS da primeira linha — o mesmo do censo.

    📊 É a forma exata de `infocap-schema-fingerprints.json`
    (`sha256_das_chaves_ordenadas`): 20 chaves em `/documentos_bi`, 33 em
    `/renovacoes`. Comparar com o censo é como o BLOCO C descobre DRIFT sem
    esperar um cron (a proposta pedia um monitor agendado; §6 o recusou).

    🔴 **O SEPARADOR É `|`, E ISSO NÃO É ESTILO.**

    📊 Achado pelo canário do BLOCO G, 03/09/2026. Esta função juntava as
    chaves com `,`; o censo as juntou com `|`. As MESMAS 20 chaves davam
    `57f3fa24…` aqui e `3437d553…` no arquivo — então **toda leitura viva era
    lida como drift de schema**, o manifesto marcava `DEGRADED`, e as 14
    métricas saíam INDISPONÍVEL. Com todos os gates verdes: nenhum teste
    comparava a impressão CALCULADA com a impressão MEDIDA; comparavam-se
    impressões calculadas entre si, que batiam perfeitamente.

    É a §9.3 do CLAUDE.md na forma mais cara: *um padrão medido com uma
    ferramenta e aplicado com outra é um padrão sobre outra coisa*. E o
    sintoma não era erro — era um relatório inteiro dizendo INDISPONÍVEL, que
    é a resposta que esta SPEC ensinou o produto a dar quando não sabe.

    ⚠️ Quem mudar este separador tem de remedir o censo inteiro. O guarda que
    fecha a porta está em `test_o_canario_do_pulso_360.py`: a impressão de uma
    linha com as chaves do censo TEM de bater com o `sha256` do arquivo.

    🔴 **E A AMOSTRA É A UNIÃO, NÃO A PRIMEIRA LINHA.**

    📊 Achado pela lente do dado, 03/09/2026. A versão anterior lia as chaves da
    PRIMEIRA linha e parava. Uma API que só manda o campo quando ele tem valor —
    e esta manda: `prod_docs` some quando a apólice não tem produtor — produz
    linhas com conjuntos de chaves diferentes na mesma resposta. Então a
    impressão passava a depender de QUAL apólice veio primeiro, que depende da
    ordenação, que depende do parâmetro `ordem`. Duas leituras honestas do mesmo
    período davam impressões diferentes, e o drift acusaria mudança de schema
    onde houve mudança de ordenação.

    A união das chaves de todas as linhas é estável para o mesmo conjunto de
    campos, seja qual for a ordem — e continua acusando o campo que apareceu ou
    sumiu, que é o que o drift existe para ver.

    ⚠️ Com linhas homogêneas — que é o caso das duas rotas do censo — a união é
    igual à primeira linha, e a impressão medida continua sendo a mesma.

    🔴 Lista VAZIA devolve `SEM_AMOSTRA`, e não `""`. Uma rota sem linhas não
    tem schema a comparar; omiti-la do mapa a tornaria indistinguível de uma
    rota que ninguém leu, e é dessa confusão que nasce o zero de consolação.
    """
    chaves: set = set()
    houve_linha = False
    for linha in linhas:
        if isinstance(linha, dict) and linha:
            houve_linha = True
            chaves.update(linha.keys())
    if not houve_linha:
        return SEM_AMOSTRA
    junta = SEPARADOR_DA_IMPRESSAO.join(sorted(chaves))
    return hashlib.sha256(junta.encode("utf-8")).hexdigest()


def _tipo_do_documento(linha: Dict[str, Any]) -> str:
    """`NEW` · `RENEWAL` · `ENDORSEMENT` · `UNKNOWN`.

    🔴 `ENDORSEMENT` existe para poder ser EXCLUÍDO da contagem (mutação M5).
    📊 A chamada de produção já filtra `tipo_doc=A` na REQUISIÇÃO — sem isso
    viriam 3.272 documentos dos quais só 1.680 são apólice. O teste aqui é o
    cinto de segurança: se a requisição mudar, o fato continua honesto.

    📊 `nosnum_ren` aponta a apólice ANTERIOR: preenchido = renovação, vazio =
    negócio novo. 963 de 1.680 em 2025 (57,3%, censo).
    """
    tipo = str(linha.get("tipdoc") or "").strip().upper()
    if tipo and tipo != "A":
        return ENDORSEMENT
    if str(linha.get("nosnum_ren") or "").strip():
        return RENEWAL
    if tipo == "A":
        return NEW
    return NEW if "nosnum_ren" in linha else UNKNOWN


#: 🔴 SPEC-094.1 · BLOCO A. As CINCO rotas novas, medidas no censo v2.1
#: (`INFOCAP-CORPAPI-CENSUS-v2.md` §v2.1 §A), com os parametros que as fizeram
#: responder. Elas moram AQUI, num lugar so, pelo motivo de sempre: duas copias
#: dos parametros divergem no primeiro dia em que uma delas ganha um campo.
ROTA_SINISTROS = "/sinistros"
ROTA_ANDAMENTO = "/negocios_andamento"
ROTA_EM_CALCULO = "/em_calculo"
ROTA_FINALIZADOS = "/negocios_finalizados"
ROTA_RENOVACOES = "/renovacoes"
ROTA_DOCUMENTO = "/documento"

#: 🔴 SPEC-094.1, conserto de 04/09/2026. O teto da paginacao, escrito.
#: 📊 `/sinistros` tem 5.729 registros medidos; 20 paginas de 1.000 cobrem a
#: base inteira com folga. O laco PARA na primeira pagina curta — o teto so
#: existe para que uma rota que devolva sempre cheia nao gire para sempre, e
#: quando ele e alcancado o lote sai com aviso de TRUNCAMENTO.
LINHAS_POR_PAGINA = 1000
TETO_DE_PAGINAS = 20

#: 💭 Quantos rotulos distintos de situacao cabem num aviso. Cinco informam o
#: tamanho do problema; a lista inteira seria despejo dentro do pack.
TETO_DE_ROTULOS = 5

#: A etapa do funil, por rota. 📊 As TRES exigem `status` (sem ele, HTTP 500 nas
#: tres); com ele, `/em_calculo` e `/negocios_finalizados` devolvem **404, que e
#: VAZIO** e nao erro.
ETAPA_DA_ROTA = {
    ROTA_ANDAMENTO: "EM_ANDAMENTO",
    ROTA_EM_CALCULO: "EM_CALCULO",
    ROTA_FINALIZADOS: "FINALIZADO",
}

#: 🔴 SPEC-094.1, conserto de 04/09/2026 — a data de UM negocio sai da chave que
#: a rota TEM, e nao de uma chave unica escolhida por uma das tres.
#:
#: 📊 O defeito: `created_at` vinha so de `inivig`. Essa chave existe em
#: `/negocios_andamento` (30 chaves medidas) e **nao existe** em
#: `/negocios_finalizados` (22 chaves, sem ela) — entao TODO negocio finalizado
#: nascia sem data, e a formula do funil, que recorta pela data, o descartava.
#: A etapa FINALIZADO — a que responde "quantos eu fechei" — desaparecia do
#: funil inteiro, sem um aviso.
#:
#: ⚠️ A ordem e do mais especifico para o mais generico, e ela PARA na primeira
#: chave presente com data legivel.
CHAVES_DE_DATA_DO_NEGOCIO = ("inivig", "datemi", "data", "datinc", "dat_neg",
                             "data_negocio", "dtemissao", "prox_aten_data",
                             "produto_fimvig", "fimvig")

#: 🔴 Os campos de `/sinistros` que sao PII e **nao atravessam a fronteira**.
#: 📊 Censo v2.1 §A3: `segurado` e `responsavel` sao nome de pessoa, `placa` e
#: placa de veiculo e `numapo` e numero de apolice na seguradora. A lista existe
#: escrita para que o proximo leitor veja o que foi DESCARTADO de proposito — e
#: para que o guarda consiga conferir que ela nao encolheu.
PII_DE_SINISTRO = ("segurado", "responsavel", "placa", "numapo", "cliente",
                   "nome_busca", "cic", "fone", "email")


#: 🔴 SPEC-094.1, conserto de 04/09/2026 — as marcas do desfecho, SEM ACENTO.
#:
#: 📊 O defeito medido: a regra comparava marcas sem acento (`analis`) contra o
#: rotulo CRU da fonte. `"Em Análise"` tem acento no `a` de `Análise`, entao
#: `"analis" in "em análise"` e **falso** — e o sinistro caia em UNKNOWN, sumia
#: da contagem de abertos e nao gerava aviso nenhum. Era o CLAUDE.md §9.4 na
#: forma classica: o padrao medido num texto e aplicado a outro.
#:
#: ⚠️ E `negado`/`indeferido` iam para CLOSED junto com `pago`: a indenizacao de
#: um sinistro NEGADO entrava na soma do que a seguradora pagou.
MARCAS_NEGADO = ("negad", "indeferi", "recusad", "improced", "nao indeniz")
MARCAS_PAGO = ("pago", "paga", "liquid", "indeniz")
MARCAS_ENCERRADO = ("encerr", "finaliz", "cancel", "arquiv", "conclu")
MARCAS_ABERTO = ("abert", "andamento", "analis", "avis", "regula", "pendent",
                 "aguard", "vistori", "tramit", "sinistr")


def _sem_acento(texto: Any) -> str:
    """Minusculas e sem acento. 🔴 A normalizacao acontece ANTES das marcas."""
    bruto = unicodedata.normalize("NFKD", str(texto or ""))
    return "".join(c for c in bruto if not unicodedata.combining(c)).strip().lower()


def _situacao_do_sinistro(linha: Dict[str, Any]) -> str:
    """`OPEN` · `CLOSED_PAID` · `CLOSED_DENIED` · `CLOSED` · `UNKNOWN`.

    A ordem das clausulas nao e arbitraria, e cada uma existe por um defeito:

    ```
    o rotulo diz NEGADO/INDEFERIDO   -> CLOSED_DENIED, e ele vence a data
    o rotulo diz PAGO/LIQUIDADO      -> CLOSED_PAID
    o rotulo diz ABERTO/EM ANALISE   -> OPEN
    tem data de encerramento         -> CLOSED  (encerrou; nao se sabe o desfecho)
    o rotulo diz ENCERRADO/ARQUIVADO -> CLOSED
    qualquer outra coisa             -> UNKNOWN (nunca CLOSED por descarte)
    ```

    🔴 `CLOSED` generico NAO soma indenizacao: "encerrado" nao e "pago", e a
    diferenca e dinheiro que o dono levaria para uma conversa com a seguradora.

    ⚠️ O rotulo de NEGADO vence a data de encerramento porque ele e a
    informacao mais especifica: um caso negado tambem tem data de encerramento,
    e deixar a data decidir apagaria o desfecho.
    """
    rotulo = _sem_acento(linha.get("situacao"))
    if rotulo:
        for marca in MARCAS_NEGADO:
            if marca in rotulo:
                return CLAIM_CLOSED_DENIED
        for marca in MARCAS_PAGO:
            if marca in rotulo:
                return CLAIM_CLOSED_PAID
        for marca in MARCAS_ABERTO:
            if marca in rotulo:
                return CLAIM_OPEN
    if _data(linha.get("datenc")) is not None:
        return CLAIM_CLOSED
    if rotulo:
        for marca in MARCAS_ENCERRADO:
            if marca in rotulo:
                return CLAIM_CLOSED
    return CLAIM_UNKNOWN


def _cancelada(linha: Dict[str, Any]) -> bool:
    return str(linha.get("cancelado") or "").strip().upper() in ("T", "S", "TRUE", "1")



# ==========================================================================
# A ESCOLHA DA CONEXÃO — o resolver que JÁ EXISTE, exposto por um nome só
# ==========================================================================
def escolher_conexao(candidatos: List[Dict[str, Any]], *,
                     company_id: str = "",
                     connection_id: Optional[str] = None,
                     base_url_padrao: str = "") -> Optional[Dict[str, Any]]:
    """A conexão utilizável entre as candidatas — ou `None`.

    🔴 **Não decide nada.** Ela delega a `_resolve_infocap_connection_candidates`
    (`infocap_connector.py:668-720`), que é a regra que o conector de atendimento
    já usa em produção. Escrever um segundo critério de escolha seria motor
    paralelo (CLAUDE.md §5) — e um motor paralelo de *escolha de credencial* é a
    pior variedade: os dois funcionariam, escolheriam conexões diferentes, e a
    diferença apareceria como "a carteira mudou".

    📊 O que a regra existente já faz, e que esta SPEC precisa:
    filtra `company_id` · exclui `archived`/`inactive`/`revoked` · exclui health
    `invalid_credentials` · exige credencial e base_url · e **recusa** quando
    sobra mais de uma elegível, em vez de pegar a primeira.

    ⚠️ Devolve `None` — e não a primeira arquivada — quando nada serve. Uma
    corretora sem conexão viva precisa ouvir isso, não receber dado velho.
    """
    from app.api.infocap_connector import _resolve_infocap_connection_candidates

    if not base_url_padrao:
        try:
            from app.core.config import settings
            base_url_padrao = getattr(settings, "INFOCAP_BASE_URL", "") or ""
        except Exception:  # noqa: BLE001
            base_url_padrao = ""
    decisao = _resolve_infocap_connection_candidates(
        list(candidatos or []),
        company_id=company_id,
        requested_connection_id=connection_id,
        provider_default_base_url=base_url_padrao)
    return decisao.get("selected_connection")


# ==========================================================================
# A TRADUÇÃO a partir das dataclasses da 081
# ==========================================================================
def fonte_da_081():
    """`(FonteInfocap, FalhaDaInfocap, anos_de_vencimento_para)` — POR ESTA porta.

    🔴 SPEC-094 · mutação **M12**: *fora deste arquivo, ninguém importa
    `fonte_infocap`*. As duas tools da 081 continuam precisando da leitura
    daquela peça — 📊 o guarda [1] roda `_montar` de verdade e troca só a
    fronteira externa, e um wrapper que deixasse de usá-la deixaria de ser
    wrapper. O que muda é POR ONDE elas a pegam: por esta função, que mora no
    único arquivo com o direito de falar o dialeto do provider.

    Não é indireção decorativa. É a diferença entre *"o agente de relatório
    conhece um sistema de gestão"* e *"o agente de relatório pede a leitura ao
    adapter, e o adapter é quem conhece"*. A segunda troca de provider sem
    reescrever a tool; a primeira, não.

    ⚠️ Import tardio, como o de `_abrir`: `fonte_infocap` é carregado quando
    alguém for LER, e não na montagem do grafo.
    """
    from app.comercial.fonte_infocap import (FalhaDaInfocap, FonteInfocap,
                                             anos_de_vencimento_para)

    return FonteInfocap, FalhaDaInfocap, anos_de_vencimento_para


def traduzir(apolices: Any = (), mapa: Any = None, vencimentos: Any = (),
             *, company_id: str = "", correlation_id: str = "") -> FactSet:
    """`Apolice` / `ProdutorDaApolice` / `Vencimento` → CBIM.

    🔴 É a MESMA fronteira de `_traduzir`, uma porta adiante. `_traduzir` recebe
    a linha crua da API; esta recebe as dataclasses que a 081 já montou — e é
    por ela que os wrappers do Raio-X e do Radar (BLOCO F) passam a alimentar o
    registry sem refazer a leitura.

    ⚠️ E ela herda uma dívida, escrita aqui para não ser esquecida: as
    dataclasses da 081 guardam dinheiro em `float`, já passado por `_num`, que
    📊 devolve `0.0` para ausente. Quem entra por esta porta **não consegue**
    distinguir "R$ 0,00" de "a fonte não expôs" — a distinção só existe na
    porta de baixo. Por isso o caminho de produção do Pulso 360 usa `fatos()`,
    e esta função serve a paridade e aos wrappers.
    """
    lote = FactSet(company_id=company_id, provider_key=PROVIDER_KEY)
    correlacao = correlation_id or uuid.uuid4().hex[:16]
    acumulado: Dict[str, Dict[str, Any]] = {}
    por_origem: Dict[str, str] = {}

    for a in (apolices or ()):
        origem = str(getattr(a, "policy_ref", "") or "")
        if not origem:
            continue
        ref = policy_ref(company_id, PROVIDER_KEY, origem)
        por_origem[origem] = ref
        lote.policies.append(PolicyFact(
            policy_ref=ref, source_ref=origem,
            insurer=str(getattr(a, "seguradora", "") or "").strip(),
            branch=str(getattr(a, "ramo", "") or "").strip(),
            valid_from=_data(getattr(a, "valid_from", None)),
            valid_to=_data(getattr(a, "valid_to", None)),
            premium=interpretar_dinheiro(getattr(a, "premio", None)) or UNAVAILABLE,
            kind=RENEWAL if getattr(a, "e_renovacao", False) else NEW,
            status="vigente", provider_key=PROVIDER_KEY))
        acumulado.setdefault(ref, {})["accrued"] = (
            interpretar_dinheiro(getattr(a, "comissao", None)) or UNAVAILABLE)

    for origem, p in (mapa or {}).items():
        ref = por_origem.get(str(origem)) or policy_ref(
            company_id, PROVIDER_KEY, str(origem))
        rotulo = str(getattr(p, "rotulo", None) or getattr(p, "nome", "") or "").strip()
        if not rotulo:
            continue
        lote.assignments.append(ProducerAssignmentFact(
            policy_ref=ref, producer_ref=producer_ref(company_id, rotulo),
            producer_label=rotulo, role_source="",
            share=float(getattr(p, "percentual", 0.0) or 0.0), order=1))
        repasse = interpretar_dinheiro(getattr(p, "repasse", None))
        if repasse is not None:
            acumulado.setdefault(ref, {})["repasse"] = repasse

    for v in (vencimentos or ()):
        origem = str(getattr(v, "policy_ref", "") or "")
        if not origem:
            continue
        ref = por_origem.get(origem) or policy_ref(company_id, PROVIDER_KEY, origem)
        rotulo = str(getattr(v, "produtor", "") or "").strip()
        lote.renewals.append(RenewalFact(
            policy_ref=ref, valid_to=_data(getattr(v, "valid_to", None)),
            producer_ref=producer_ref(company_id, rotulo) if rotulo else "",
            status_source=str(getattr(v, "tipdoc", "") or ""),
            dias_a_vencer=int(getattr(v, "dias_a_vencer", 0) or 0),
            premium=interpretar_dinheiro(getattr(v, "premio", None)) or UNAVAILABLE,
            insurer=str(getattr(v, "seguradora", "") or "").strip(),
            branch=str(getattr(v, "ramo", "") or "").strip()))

    for ref, partes in acumulado.items():
        lote.commissions.append(CommissionFact(
            policy_ref=ref,
            broker_commission_accrued=partes.get("accrued", UNAVAILABLE),
            producer_repasse=partes.get("repasse", UNAVAILABLE),
            received=UNAVAILABLE, provider_key=PROVIDER_KEY))
    lote.warnings.append(
        "[%s] traduzido a partir das dataclasses da 081: dinheiro ausente já "
        "chegou aqui como 0.0 e não é distinguível de zero" % correlacao)
    return lote


# ==========================================================================
# O adapter
# ==========================================================================
class InfocapAnalyticsProvider:
    """Implementa `BrokerageAnalyticsProvider` sobre a CorpAPI da InfoCap."""

    provider_key = PROVIDER_KEY

    def __init__(self, company_id: str = "", supabase: Any = None,
                 db: Any = None, connection_id: Optional[str] = None) -> None:
        """O provider pode nascer **ligado a uma corretora**, ou solto.

        ⚠️ Os dois modos existem porque há dois chamadores: o registry global,
        que resolve o provider por chave e passa `company_id` em cada chamada, e
        um caller que já sabe de quem está falando. `supabase` e `db` são o
        mesmo argumento com os dois nomes que esta casa usa — recusar um deles
        só produziria um `TypeError` a mais para alguém depurar.
        """
        self.company_id = str(company_id or "")
        self.db = supabase if supabase is not None else db
        self.connection_id = connection_id

    # ------------------------------------------------------------ conexão
    async def _resolver(self, *, company_id: str, db: Any = None,
                        connection_id: Optional[str] = None,
                        slug: Optional[str] = None) -> Dict[str, Any]:
        """A conexão do tenant, pelo resolver que JÁ EXISTE.

        🔴 Reusa `_resolve_infocap_connection` de `infocap_connector.py:725-757`
        — o mesmo que o conector de atendimento usa em 4 chamadas. Ele já faz o
        que esta SPEC precisa e mais um pouco:

        ```
        📊 filtra por company_id                    (o escopo do tenant)
        📊 exclui `archived`/`inactive`/`revoked`   (a Resulta tem 3 arquivadas)
        📊 exclui health `invalid_credentials`      (uma das 3 tem exatamente isso)
        📊 exige encrypted_secret_ref e base_url
        📊 recusa se sobrar mais de UMA elegível    (`ambiguous_connection`)
        ```

        O import é preguiçoso: `infocap_connector.py` tem 4.253 linhas e puxa
        FastAPI — o mesmo padrão de `policy_data_provider.py:74`.
        """
        if db is None:
            raise FalhaDoProvider(
                "sem acesso ao banco não há como resolver a conexão da corretora")
        from app.api.infocap_connector import _resolve_infocap_connection

        decisao = await _resolve_infocap_connection(
            db, company_id=company_id, requested_connection_id=connection_id or None)
        conn = decisao.get("selected_connection")   # mesma regra de `escolher_conexao`
        if not conn:
            raise FalhaDoProvider(
                "a corretora não tem uma conexão InfoCap utilizável "
                f"(status: {decisao.get('status')})")
        return conn

    @staticmethod
    async def _banco_do_resolver(db: Any) -> Any:
        """O objeto que o resolver de conexão sabe usar. 🔴 O ELO do BLOCO F.

        📊 Medido pelo juiz em 03/09/2026, na primeira execução REAL pelo chat:
        `RELATORIO_FALHOU · Motivo interno: AttributeError`. As duas metades
        estavam certas e o encaixe não:

        ```
        graph.py:563          passa `real_supabase_client` — o `Client` CRU, SINCRONO
        ferramenta_do_pulso_360   desembrulha de novo (`getattr(supabase, "client", …)`)
        _resolve_infocap_connection  faz `await db.client.table(...)`
        ```

        O `Client` cru não tem `.client`, e o `.execute()` dele não é
        aguardável. O guarda anterior não via porque o fake dele expõe
        `.client` e responde a `await` — ele media a PEÇA, e não o ELO
        (CLAUDE.md §9.4).

        🔴 A decisão é ter DOIS objetos, e não um: `self.supabase` continua
        cru porque o `ArtifactService` é SÍNCRONO e é ele quem publica a peça;
        quem fala com o resolver é um `AsyncSupabaseClient`. Forçar um só
        obrigaria a reescrever um dos dois lados — e o outro lado é o caminho
        pelo qual a Cobrança publica hoje.

        ⚠️ A fábrica é a que a casa já usa (`portal_tool.py:342`,
        `infocap_tool.py:144`): `create_async_supabase_client()`, mesma URL e
        mesma chave de serviço, sem ler `.env` de novo. Objeto que já fala o
        dialeto assíncrono passa INTACTO — inclusive o fake de um guarda.
        """
        if db is None:
            return None
        interno = getattr(db, "client", None)
        if interno is not None and not _e_cliente_sincrono(interno):
            return db
        if interno is not None or _tem_table(db):
            from app.core.database import create_async_supabase_client

            logger.debug("[094] cliente sincrono recebido: abrindo o "
                         "AsyncSupabaseClient que o resolver exige")
            return await create_async_supabase_client()
        return db

    def _credencial(self, conn: Dict[str, Any]) -> Tuple[str, str, str, str]:
        """`(login, senha, base_url, aplicacao)` — em memória, nunca em log.

        🔴 `encrypted_secret_ref` é o CIPHERTEXT, não uma referência: o nome
        mente (CLAUDE.md §12.1, pendência P-094-SECRET-REF). Descriptografado
        pelo caminho do produto — `get_encryption_service().decrypt`, o mesmo
        de `infocap_connector.py:966`.
        """
        from app.core.config import settings
        from app.services.encryption_service import get_encryption_service

        config = conn.get("connection_config") if isinstance(
            conn.get("connection_config"), dict) else {}
        base_url = str(config.get("base_url")
                       or getattr(settings, "INFOCAP_BASE_URL", "") or "").rstrip("/")
        cipher = conn.get("encrypted_secret_ref")
        if not cipher:
            raise FalhaDoProvider("a conexão não guarda credencial")
        try:
            creds = json.loads(get_encryption_service().decrypt(cipher))
        except Exception as exc:  # noqa: BLE001
            # ⛔ `exc` pode carregar o texto decifrado em alguns backends.
            # Só o TIPO vai ao log.
            raise FalhaDoProvider(
                f"não foi possível decifrar a credencial ({type(exc).__name__})") from exc
        login = str(creds.get("username") or creds.get("email") or "")
        senha = str(creds.get("password") or creds.get("senha") or "")
        aplicacao = str(creds.get("aplicacao") or config.get("infocap_aplicacao") or "0")
        if not login or not senha:
            raise FalhaDoProvider("a credencial da conexão está incompleta")
        return login, senha, base_url, aplicacao

    async def _marcar_uso(self, db: Any, *, company_id: str, connection_id: str) -> None:
        """`UPDATE tenant_connections SET last_used_at = now()` — uma coluna, uma linha.

        🔴 📊 O escritor NOVO e declarado desta SPEC. Antes dele:
        `grep -rn last_used_at --include=*.py` → **0 escritores**, e a coluna
        estava NULL nas 6 conexões (§1.4). Uma coluna que ninguém escreve não
        é telemetria, é decoração.

        🔴 `company_id` vai no filtro **junto** com o `id`. O backend usa
        service role: a RLS não protege contra um `id` errado vindo do código
        (CLAUDE.md §7). Com os dois, um id de outro tenant atualiza zero linhas.

        ⚠️ Nunca derruba a leitura. Um relatório que não sai porque a
        telemetria falhou é um defeito absurdo — a mesma regra do cache.
        """
        try:
            await (db.client.table("tenant_connections")
                   .update({"last_used_at": _agora_utc()})
                   .eq("id", connection_id)
                   .eq("company_id", company_id)
                   .execute())
        except Exception as exc:  # noqa: BLE001
            logger.debug("[094] last_used_at nao gravado (%s)", type(exc).__name__)

    # -------------------------------------------------------------- fonte
    async def _abrir(self, *, company_id: str, db: Any = None,
                     connection_id: Optional[str] = None,
                     slug: Optional[str] = None) -> Tuple[Any, str, str, Any]:
        """`(fonte, connection_id, account_fingerprint, db)` — já com o gate."""
        from app.comercial.fonte_infocap import FonteInfocap

        if env_ligada("COMERCIAL_RESOLVER_LEGADO"):
            # 🔴 O caminho VELHO, por NOME da corretora, atrás de bandeira e com
            # log. 📊 Ele não funciona nesta máquina: não existe nenhuma
            # `CORP_INFOCAP_*` em `backend/.env` (§1.4). Fica porque desligar um
            # caminho de produção sem uma volta é como se apaga um incidente na
            # frente do cliente. Pendência P-094-LEGADO.
            logger.warning(
                "[094] RESOLVER LEGADO LIGADO (COMERCIAL_RESOLVER_LEGADO): a "
                "credencial vem de CORP_INFOCAP_* por NOME da corretora, e nao "
                "da conexao do tenant. Pendencia P-094-LEGADO.")
            fonte = FonteInfocap.para_empresa(slug or "")
            impressao = impressao_da_conta(getattr(fonte, "_login_email", ""))
            registrar_conta(impressao, company_id)
            return fonte, "", impressao, db

        # 🔴 UMA normalização, aqui, e o objeto normalizado segue para o
        # `_marcar_uso` junto com a conexão. Normalizar duas vezes abriria dois
        # clientes; normalizar depois deixaria o UPDATE com o objeto errado.
        db = await self._banco_do_resolver(db)
        conn = await self._resolver(company_id=company_id, db=db,
                                    connection_id=connection_id, slug=slug)
        conexao_id = str(conn.get("id") or "")
        login, senha, base_url, aplicacao = self._credencial(conn)

        # 🔴 O gate ANTES de qualquer chamada. Recusar depois de ler já teria
        # trazido a carteira da outra corretora para dentro do processo.
        impressao = impressao_da_conta(login)
        registrar_conta(impressao, company_id)

        fonte = FonteInfocap(login=login, senha=senha, aplicacao=aplicacao,
                             base_url=base_url,
                             rotulo=chave_de_cache(company_id, conexao_id))
        return fonte, conexao_id, impressao, db

    # ------------------------------------------------------------- leitura
    async def fatos(self, *, company_id: str, inicio: date, fim: date,
                    venc_inicio: Optional[date] = None,
                    venc_fim: Optional[date] = None,
                    incluir_producao: bool = True,
                    incluir_renovacoes: bool = True,
                    db: Any = None, connection_id: Optional[str] = None,
                    slug: Optional[str] = None,
                    correlation_id: Optional[str] = None,
                    fonte: Any = None) -> FactSet:
        """Uma leitura, um `correlation_id`, uma `Provenance`.

        🔴 **A janela de vencimento é MAIOR que a de produção, de propósito.**
        📊 `/documentos_bi` filtra `inivig` e `/renovacoes` filtra `fimvig`; a
        interseção de 2025 com 2025 é de **2,8%** (100 de 3.536), porque apólice
        anual que COMEÇA em 2025 TERMINA em 2026. Pedir o mesmo ano nos dois
        deixaria 97% da produção sem produtor conhecido — é a razão de
        `anos_de_vencimento_para` existir na 081, e ela continua valendo.

        `fonte` injetável existe para o teste com fixture. Em produção é `None`
        e a fonte nasce da conexão.
        """
        company_id = company_id or getattr(self, "company_id", "")
        db = db if db is not None else getattr(self, "db", None)
        connection_id = connection_id or getattr(self, "connection_id", None)
        correlacao = correlation_id or uuid.uuid4().hex[:16]
        conexao_id = ""
        impressao = ""
        if fonte is None:
            fonte, conexao_id, impressao, db = await self._abrir(
                company_id=company_id, db=db, connection_id=connection_id, slug=slug)

        v_ini = venc_inicio or date(inicio.year - 1, 1, 1)
        v_fim = venc_fim or date(fim.year + 2, 12, 31)

        producao: List[Dict[str, Any]] = []
        renovacoes: List[Dict[str, Any]] = []
        if incluir_producao:
            producao = await asyncio.to_thread(fonte.producao_crua, inicio, fim)
        if incluir_renovacoes:
            renovacoes = await asyncio.to_thread(fonte.renovacoes_cruas, v_ini, v_fim)

        # 🔴 A rota que NÃO foi lida não entra no mapa de impressões, e a rota
        # lida entra mesmo vazia. As duas coisas são diferentes: "não perguntei"
        # não pode virar "perguntei e não veio nada", que é o que autoriza o
        # registry a bloquear a métrica dependente.
        rotas_lidas = tuple(
            r for r, ligada in (("/documentos_bi", incluir_producao),
                                ("/renovacoes", incluir_renovacoes)) if ligada)
        lote = self._traduzir(company_id, producao, renovacoes, correlacao,
                              rotas_lidas=rotas_lidas)
        lote.provenance = Provenance(
            connection_id=conexao_id,
            correlation_id=correlacao,
            fetched_at=datetime.now(timezone.utc),
            fingerprint=lote.fingerprints.get("__combinado__", ""),
            account_fingerprint=impressao,
        )
        if db is not None and conexao_id:
            await self._marcar_uso(db, company_id=company_id, connection_id=conexao_id)
        return lote

    # ------------------------------------------------------------ tradução
    def _traduzir(self, company_id: str, producao: List[Dict[str, Any]],
                  renovacoes: List[Dict[str, Any]],
                  correlacao: str,
                  rotas_lidas: Tuple[str, ...] = ("/documentos_bi",
                                                  "/renovacoes")) -> FactSet:
        """Linha crua → fato canônico. É AQUI que a InfoCap deixa de existir."""
        lote = FactSet(company_id=company_id, provider_key=PROVIDER_KEY)
        # 🔴 A populacao da CARTEIRA foi lida — e so ela. `cancellations`,
        # `claims`, `quotes` e `customers` sao rotas PROPRIAS, e quem as le e
        # quem as marca (SPEC-094.1, conserto de 04/09/2026).
        lote.populacoes_lidas.add(POP_POLICIES)
        acumulado: Dict[str, Dict[str, Any]] = {}

        def _dinheiro(valor: Any, campo: str, ref: str) -> Any:
            """`Money` ou `UNAVAILABLE` **com warning**. Nunca `0.0`."""
            m = interpretar_dinheiro(valor)
            if m is None:
                lote.warnings.append(
                    f"[{correlacao}] valor ilegível em {campo} "
                    f"(apólice {ref[:8]}…): INDISPONÍVEL, não zero")
                return UNAVAILABLE
            return m

        # --- produção: a base POLICY_VALID_FROM -----------------------------
        vistos: set = set()
        for x in producao:
            origem = str(x.get("nosnum") or "").strip()
            if not origem:
                continue
            ref = policy_ref(company_id, PROVIDER_KEY, origem)
            if ref in vistos:
                # 🔴 A fronteira do ano civil é onde a mesma apólice apareceria
                # em duas fatias. Deduplicar aqui é mais barato que descobrir um
                # total inflado depois (`calculos.ranking_por_produtor:136-139`).
                continue
            vistos.add(ref)
            lote.policies.append(PolicyFact(
                policy_ref=ref,
                source_ref=origem,
                insurer=str(x.get("seguradora") or "").strip(),
                branch=str(x.get("ramo") or "").strip(),
                valid_from=_data(x.get("inivig")),
                valid_to=_data(x.get("fimvig")),
                premium=_dinheiro(x.get("pretot"), "prêmio", ref),
                kind=_tipo_do_documento(x),
                # 🔴 SPEC-094.1 A.1: o vocabulario do CBIM, e nao dois
                # literais soltos em portugues. Quem escreve as duas pontas da
                # comparacao tem de ser a MESMA funcao.
                status=status_de_apolice(_cancelada(x)),
                provider_key=PROVIDER_KEY,
            ))
            acumulado.setdefault(ref, {})["accrued"] = _dinheiro(
                x.get("val_c"), "comissão apropriada", ref)

        # --- renovações: a base POLICY_VALID_TO -----------------------------
        vistos_venc: set = set()
        vistas_atribuicoes: set = set()
        for x in renovacoes:
            origem = str(x.get("nosnum") or "").strip()
            if not origem:
                continue
            ref = policy_ref(company_id, PROVIDER_KEY, origem)
            if str(x.get("tipdoc") or "").strip().upper() != "A" or _cancelada(x):
                continue

            # 🔴 TODOS os `prod_docs`, não só `ordem == 1`.
            docs = [p for p in (x.get("prod_docs") or []) if isinstance(p, dict)]
            repasse_total: Optional[Money] = None
            repasse_ilegivel = False
            direto_ref = ""
            for p in docs:
                rotulo = str(p.get("produtor") or "").strip()
                if not rotulo:
                    continue
                pref = producer_ref(company_id, rotulo)
                ordem = p.get("ordem")
                try:
                    ordem = int(str(ordem)) if ordem is not None else None
                except (TypeError, ValueError):
                    ordem = None
                if ordem == 1 and not direto_ref:
                    direto_ref = pref
                share = interpretar_dinheiro(p.get("per_r"))
                participacao = float(share.amount) if share is not None else None
                if participacao is not None and not (0.0 <= participacao <= 100.0):
                    # ⚠️ Participação fora de 0–100 não é participação. Ela NÃO
                    # é corrigida nem descartada — o repasse é o `val_r`, e não
                    # um produto do percentual — mas quem lê precisa saber que o
                    # cadastro tem uma linha impossível.
                    lote.warnings.append(
                        f"[{correlacao}] participação fora de 0–100% na apólice "
                        f"{ref[:8]}… ({participacao:g}%): o repasse foi somado "
                        f"pelo valor, não pelo percentual, mas o cadastro tem "
                        f"uma linha que não fecha")
                # 🔴 DEDUPE. 📊 Achado pela lente do dado, 03/09/2026: a janela de
                # vencimento é de QUATRO anos civis (`anos_de_vencimento_para`), e
                # a mesma apólice a vencer aparece na fatia de cada ano em que a
                # API a devolve. As apólices já eram deduplicadas (`vistos_venc`);
                # os ASSIGNMENTS não eram, e o mesmo produtor da mesma apólice
                # entrava 4×. `montar_contexto` os usa para decidir quem é o
                # produtor principal e quantos produtores a apólice tem — e
                # "quatro produtores" numa apólice de um produtor é uma afirmação
                # errada sobre a corretora.
                assinatura = (ref, pref, ordem)
                if assinatura in vistas_atribuicoes:
                    continue
                vistas_atribuicoes.add(assinatura)
                lote.assignments.append(ProducerAssignmentFact(
                    policy_ref=ref,
                    producer_ref=pref,
                    producer_label=rotulo,
                    # 🔴 O rótulo da InfoCap vai para `role_source` e NUNCA
                    # decide `actor_type`: quem decide é o mapa versionado por
                    # corretora (BLOCO F).
                    role_source=str(p.get("agente") or "").strip(),
                    share=participacao,
                    order=ordem,
                ))
                valor = interpretar_dinheiro(p.get("val_r"))
                if valor is None:
                    repasse_ilegivel = True
                    continue
                repasse_total = valor if repasse_total is None else repasse_total + valor

            if repasse_total is not None:
                acumulado.setdefault(ref, {})["repasse"] = repasse_total
            elif docs and repasse_ilegivel:
                lote.warnings.append(
                    f"[{correlacao}] repasse ilegível na apólice {ref[:8]}…: "
                    f"INDISPONÍVEL, não zero")

            if ref in vistos_venc:
                continue
            vistos_venc.add(ref)
            dias = x.get("dias_a_vencer")
            try:
                dias = int(float(str(dias))) if dias is not None and str(dias) != "" else None
            except (TypeError, ValueError):
                dias = None
            lote.renewals.append(RenewalFact(
                policy_ref=ref,
                valid_to=_data(x.get("fimvig")),
                producer_ref=direto_ref,
                status_source=str(x.get("renovacao_situacao")
                                  or x.get("situacao_txt") or "").strip(),
                dias_a_vencer=dias,
                premium=_dinheiro(x.get("pretot"), "prêmio a vencer", ref),
                insurer=str(x.get("seguradora") or "").strip(),
                branch=str(x.get("ramo") or "").strip(),
            ))

        # --- a comissão, das duas pontas ------------------------------------
        #
        # 🔴 Uma apólice pode ter só um dos dois lados: `broker_commission_accrued`
        # vem de `/documentos_bi` e `producer_repasse` de `/renovacoes`, e as
        # populações são quase disjuntas. O lado que falta é UNAVAILABLE — é
        # por isso que `contribution.after_repasse` só existe sobre a INTERSEÇÃO.
        for ref, partes in acumulado.items():
            lote.commissions.append(CommissionFact(
                policy_ref=ref,
                broker_commission_accrued=partes.get("accrued", UNAVAILABLE),
                producer_repasse=partes.get("repasse", UNAVAILABLE),
                received=UNAVAILABLE,   # 📊 medido: a rota não existe (403-SigV4)
                provider_key=PROVIDER_KEY,
            ))

        fp_prod = impressao_da_rota(producao)
        fp_renov = impressao_da_rota(renovacoes)
        # 🔴 As duas rotas LIDAS entram sempre, mesmo vazias — marcadas
        # `SEM_AMOSTRA`. É essa entrada que permite ao registry responder
        # "fonte sem linhas no período" em vez de "0,0 com confiança HIGH".
        medidas = {"/documentos_bi": fp_prod, "/renovacoes": fp_renov}
        lote.fingerprints = {r: medidas[r] for r in rotas_lidas
                             if medidas.get(r)}
        lote.fingerprints["__combinado__"] = hashlib.sha256(
            f"{fp_prod}|{fp_renov}".encode("utf-8")).hexdigest()[:16]
        return lote

    # ================================================================
    # SPEC-094.1 · BLOCO A — as CINCO rotas que existiam e ninguem lia
    # ================================================================
    #
    # 🔴 Cada uma devolve um **FactSet recorte**, e nao uma lista solta como
    # `policies()` / `renewals()`. A diferenca nao e estetica: aqueles quatro sao
    # recortes do MESMO lote de duas rotas, ja lido; estes cinco leem uma rota
    # PROPRIA, com janela propria. Devolver a lista crua jogaria fora justamente
    # o que o registry precisa para distinguir **"a rota veio vazia"** de **"a
    # rota nao foi lida"** — que e a diferenca entre UNAVAILABLE e um zero com
    # confianca alta (`registry._rotas_do_lote`).

    @staticmethod
    def _linhas_da_rota(fonte: Any, rota: str, params: Dict[str, Any],
                        chave: str) -> List[Dict[str, Any]]:
        """As linhas cruas de UMA rota. ⚠️ Sem interpretacao nenhuma.

        🔴 Reusa `FonteInfocap._get` e `._linhas` de proposito (CLAUDE.md §5).
        Elas carregam autenticacao, retry, a chave de cache com o rotulo do
        tenant (cross-tenant por cache e o defeito mais silencioso que existe) e
        a regra de que **404 e VAZIO, nao erro** — 📊 exatamente o que o censo
        v2.1 §A4 mediu em `/em_calculo` e `/negocios_finalizados`. Um segundo
        cliente HTTP aqui seria motor paralelo, e o primeiro sintoma seria uma
        corretora lendo a carteira da outra.
        """
        return fonte._linhas(fonte._get(rota, params), chave)

    def _marcar_fingerprints(self, lote: FactSet, medidas: Dict[str, Any]) -> None:
        """Grava as rotas LIDAS em `fingerprints` — vazias inclusive.

        🔴 `impressao_da_rota` devolve `SEM_AMOSTRA` para lista vazia, e e
        essa entrada que autoriza o registry a responder *"fonte sem linhas no
        periodo"* em vez de `0,0` com confianca HIGH. Rota que nao foi lida NAO
        entra: "nao perguntei" nao pode virar "perguntei e nao veio nada".
        """
        for rota, linhas in medidas.items():
            lote.fingerprints[rota] = impressao_da_rota(linhas)
        lote.fingerprints["__combinado__"] = hashlib.sha256(
            "|".join(f"{r}={lote.fingerprints[r]}"
                     for r in sorted(medidas)).encode("utf-8")).hexdigest()[:16]

    async def _lote_de_rota(self, *, company_id: str, db: Any,
                            connection_id: Optional[str], slug: Optional[str],
                            correlation_id: Optional[str],
                            fonte: Any) -> Tuple[FactSet, Any, str, str, Any]:
        """`(lote vazio, fonte, correlacao, impressao, db)` — o preambulo comum."""
        company_id = company_id or getattr(self, "company_id", "")
        db = db if db is not None else getattr(self, "db", None)
        connection_id = connection_id or getattr(self, "connection_id", None)
        correlacao = correlation_id or uuid.uuid4().hex[:16]
        conexao_id = ""
        impressao = ""
        if fonte is None:
            fonte, conexao_id, impressao, db = await self._abrir(
                company_id=company_id, db=db, connection_id=connection_id,
                slug=slug)
        lote = FactSet(company_id=company_id, provider_key=PROVIDER_KEY)
        lote.provenance = Provenance(
            connection_id=conexao_id, correlation_id=correlacao,
            fetched_at=datetime.now(timezone.utc), fingerprint="",
            account_fingerprint=impressao)
        return lote, fonte, correlacao, impressao, db

    def _selar(self, lote: FactSet, impressao: str) -> FactSet:
        if lote.provenance is not None:
            lote.provenance = Provenance(
                connection_id=lote.provenance.connection_id,
                correlation_id=lote.provenance.correlation_id,
                fetched_at=lote.provenance.fetched_at,
                fingerprint=lote.fingerprints.get("__combinado__", ""),
                account_fingerprint=impressao)
        return lote

    # ------------------------------------------------------------ sinistros
    async def claims(self, *, company_id: str, inicio: date, fim: date,
                     db: Any = None, connection_id: Optional[str] = None,
                     slug: Optional[str] = None,
                     correlation_id: Optional[str] = None,
                     fonte: Any = None) -> FactSet:
        """Os SINISTROS do periodo, pela data de OCORRENCIA. 📊 1,10 s / 90 dias.

        🔴 `tipo_data=oco` prende `datoco`, e isso foi MEDIDO, nao lido na doc:
        📊 42/42 sinistros dentro da janela, com o minimo exatamente no primeiro
        dia dela (censo v2.1 §A3). A base temporal desta populacao e
        `CLAIM_OCCURRED_DATE` — nem inicio nem fim de vigencia.

        ⛔ `segurado`, `responsavel`, `placa` e `numapo` sao DESCARTADOS AQUI, na
        fronteira. Nao ha filtro depois: o que nao entra nao vaza. `claim_ref` e
        hash de `numsin` (M16).
        """
        lote, fonte, correlacao, impressao, db = await self._lote_de_rota(
            company_id=company_id, db=db, connection_id=connection_id,
            slug=slug, correlation_id=correlation_id, fonte=fonte)
        # 🔴 SPEC-094.1, conserto de 04/09/2026 — PAGINACAO.
        #
        # 📊 A leitura anterior pedia `pagina=1` e parava. O censo mediu 42
        # sinistros em 90 dias e concluiu que "coube numa pagina" — mas a rota
        # tem **5.729 registros**, e uma pergunta sobre o ano inteiro passa do
        # teto sem avisar ninguem. Uma populacao truncada em silencio nao trava:
        # ela devolve um numero MENOR, com confianca alta (CLAUDE.md §9.5).
        linhas: List[Dict[str, Any]] = []
        truncou = False
        for pagina in range(1, TETO_DE_PAGINAS + 1):
            pedaco = await asyncio.to_thread(
                self._linhas_da_rota, fonte, ROTA_SINISTROS, {
                    "data_inicial": inicio.strftime("%d/%m/%Y"),
                    "data_final": fim.strftime("%d/%m/%Y"),
                    "tipo_data": "oco",
                    "qtd_pag": LINHAS_POR_PAGINA,
                    "pagina": pagina,
                }, "sinistros")
            linhas.extend(pedaco)
            if len(pedaco) < LINHAS_POR_PAGINA:
                break
        else:
            truncou = True
        if truncou:
            lote.warnings.append(
                f"[{correlacao}] a leitura de sinistros parou no teto de "
                f"{TETO_DE_PAGINAS} pagina(s) ({len(linhas)} linha(s)): a "
                f"populacao pode estar TRUNCADA, e um total truncado e menor "
                f"que o verdadeiro — nunca apresentar como o numero do periodo")
        self._traduzir_sinistros(lote, linhas, correlacao)
        lote.populacoes_lidas.add(POP_CLAIMS)
        self._marcar_fingerprints(lote, {ROTA_SINISTROS: linhas})
        return self._selar(lote, impressao)

    def _traduzir_sinistros(self, lote: FactSet, linhas: List[Dict[str, Any]],
                            correlacao: str) -> None:
        # 🔴 SPEC-094.1, conserto de 04/09/2026 — o dedupe PREFERE a linha que
        # tem data de ocorrencia.
        #
        # 📊 O defeito: `if ref in vistos: continue` ficava com a PRIMEIRA linha
        # de cada sinistro, na ordem em que a rota devolveu. Quando a duplicata
        # sem `datoco` vinha primeiro, o sinistro nascia com `occurred_at=None` e
        # **sumia de todas as metricas** — que recortam a populacao pela data de
        # ocorrencia. O caso existe, ninguem o conta, e nada trava.
        vistos: Dict[str, int] = {}
        for x in linhas:
            origem = str(x.get("numsin") or "").strip()
            documento = str(x.get("nosnum") or "").strip()
            if not origem and not documento:
                continue
            ref = claim_ref(lote.company_id, PROVIDER_KEY,
                            origem or f"doc:{documento}")
            if ref in vistos:
                anterior = lote.claims[vistos[ref]]
                if (getattr(anterior, "occurred_at", None) is not None
                        or _data(x.get("datoco")) is None):
                    continue
                # ⚠️ A guardada nao tem data e esta TEM: a nova vence. A posicao
                # e reaproveitada para o dedupe continuar sendo por REFERENCIA,
                # e nao por ordem de chegada.
                fora = vistos.pop(ref)
                lote.claims.pop(fora)
                for chave, pos in list(vistos.items()):
                    if pos > fora:
                        vistos[chave] = pos - 1
            vistos[ref] = len(lote.claims)
            indenizacao = interpretar_dinheiro(x.get("valind"))
            franquia = interpretar_dinheiro(x.get("franquia"))
            if indenizacao is None and x.get("valind") is not None:
                lote.warnings.append(
                    f"[{correlacao}] indenizacao ilegivel no sinistro "
                    f"{ref[:8]}...: INDISPONIVEL, nao zero")
            lote.claims.append(ClaimFact(
                policy_ref=(policy_ref(lote.company_id, PROVIDER_KEY, documento)
                            if documento else ""),
                claim_ref=ref,
                status=_situacao_do_sinistro(x),
                occurred_at=_data(x.get("datoco")),
                reported_at=_data(x.get("datavi")),
                closed_at=_data(x.get("datenc")),
                indemnity=indenizacao if indenizacao is not None else UNAVAILABLE,
                deductible=franquia if franquia is not None else UNAVAILABLE,
                insurer=str(x.get("cia") or "").strip(),
                branch=str(x.get("ramo") or "").strip(),
                provider_key=PROVIDER_KEY))
        orfaos = len([c for c in lote.claims if not c.policy_ref])
        if orfaos:
            lote.warnings.append(
                f"[{correlacao}] {orfaos} sinistro(s) sem documento de origem: "
                f"eles contam na populacao e NAO entram na juncao com a "
                f"carteira — a cobertura da metrica diz quanto")
        # 🔴 SPEC-094.1, conserto de 04/09/2026 — o UNKNOWN passa a FALAR.
        #
        # 📊 Antes ele sumia: o sinistro nao era aberto, nao era encerrado, nao
        # entrava em contagem nenhuma e nao gerava uma linha de aviso. Um caso
        # que existe e que o software nao consegue classificar tem de aparecer —
        # senao o total do dono encolhe sem explicacao.
        #
        # ⛔ E o aviso leva os ROTULOS DISTINTOS, nunca a linha: `situacao` e
        # texto livre da corretora, e o teto existe para que um campo mal
        # preenchido nao vire despejo dentro do pack.
        desconhecidos = [c for c in lote.claims
                         if getattr(c, "status", "") == CLAIM_UNKNOWN]
        if desconhecidos:
            rotulos = sorted({str(x.get("situacao") or "").strip()
                              for x in linhas
                              if str(x.get("situacao") or "").strip()})
            amostra = ", ".join(rotulos[:TETO_DE_ROTULOS]) or "(campo vazio)"
            lote.warnings.append(
                f"[{correlacao}] {len(desconhecidos)} sinistro(s) com situacao "
                f"nao reconhecida: eles NAO entram em aberto nem em encerrado, e "
                f"o total do periodo os inclui na populacao. {len(rotulos)} "
                f"valor(es) distinto(s) na fonte: {amostra}")

    # ---------------------------------------------------------------- funil
    async def quotes(self, *, company_id: str, inicio: date, fim: date,
                     db: Any = None, connection_id: Optional[str] = None,
                     slug: Optional[str] = None,
                     correlation_id: Optional[str] = None,
                     fonte: Any = None) -> FactSet:
        """O FUNIL — as tres rotas, cada uma com a sua etapa.

        🔴 As tres exigem `status`. 📊 Sem ele as tres devolvem **HTTP 500**;
        com ele, `/em_calculo` e `/negocios_finalizados` devolvem **404 = VAZIO**
        e `/negocios_andamento` devolveu **1** negocio em 2025 inteiro. O 500 era
        parametro faltando, e nao rota quebrada (censo v2.1 §A4).

        🔴 `motivo_perda` **nao vem no GET**: nao esta entre as 30 chaves
        medidas. `QuoteFact.lost_reason` nasce UNAVAILABLE por CAPACIDADE, e a
        metrica `quotes.lost_reasons@1` escreve o porque no envelope.
        """
        lote, fonte, correlacao, impressao, db = await self._lote_de_rota(
            company_id=company_id, db=db, connection_id=connection_id,
            slug=slug, correlation_id=correlation_id, fonte=fonte)
        base = {"dtini": inicio.strftime("%d/%m/%Y"),
                "dtfim": fim.strftime("%d/%m/%Y"),
                "texto": "", "qtd_pag": 1000, "pag": 1,
                "ordem": "codigo", "orientacao": "asc",
                # 🔴 A chave vazia BASTA, e e ela que muda 500 em 200/404.
                "status": ""}
        medidas: Dict[str, Any] = {}
        for rota in (ROTA_ANDAMENTO, ROTA_EM_CALCULO, ROTA_FINALIZADOS):
            linhas = await asyncio.to_thread(
                self._linhas_da_rota, fonte, rota, dict(base), "negocios")
            medidas[rota] = linhas
            self._traduzir_funil(lote, linhas, ETAPA_DA_ROTA[rota], correlacao)
        lote.populacoes_lidas.add(POP_QUOTES)
        self._marcar_fingerprints(lote, medidas)
        if not lote.quotes:
            lote.warnings.append(
                f"[{correlacao}] as tres rotas do funil RESPONDERAM e o acervo "
                f"esta VAZIO no periodo: a corretora nao usa o CRM da fonte. "
                f"INDISPONIVEL por acervo, e nunca 'zero cotacoes'")
        return self._selar(lote, impressao)

    @staticmethod
    def _data_do_negocio(linha: Dict[str, Any]) -> Optional[date]:
        """A data deste negocio, pela primeira chave que a rota TEM.

        ⚠️ Ela nao inventa data: quando nenhuma das chaves existe, devolve
        `None` — e o negocio entra assim mesmo, com aviso. Um negocio sem data
        que some da contagem e pior que um negocio sem data contado: o primeiro
        muda o total em silencio.
        """
        for chave in CHAVES_DE_DATA_DO_NEGOCIO:
            if chave in linha:
                quando = _data(linha.get(chave))
                if quando is not None:
                    return quando
        return None

    def _traduzir_funil(self, lote: FactSet, linhas: List[Dict[str, Any]],
                        etapa: str, correlacao: str) -> None:
        sem_data = 0
        for x in linhas:
            origem = str(x.get("codigo") or "").strip()
            if not origem:
                continue
            premio = interpretar_dinheiro(x.get("val_premio"))
            quando = self._data_do_negocio(x)
            if quando is None:
                sem_data += 1
            lote.quotes.append(QuoteFact(
                quote_ref=quote_ref(lote.company_id, PROVIDER_KEY,
                                    f"{etapa}:{origem}"),
                stage=etapa,
                created_at=quando,
                closed_at=_data(x.get("produto_fimvig")),
                expected_premium=premio if premio is not None else UNAVAILABLE,
                branch=str(x.get("ramo") or "").strip(),
                # ⛔ NAO existe leitura de motivo de perda. Escrever aqui um
                # `""` faria "sem motivo" parecer "motivo vazio".
                lost_reason=UNAVAILABLE,
                provider_key=PROVIDER_KEY))
        if sem_data:
            # 🔴 O aviso e por ETAPA, porque e assim que o defeito aparece:
            # uma rota inteira sem a chave de data derruba uma etapa do funil.
            lote.warnings.append(
                f"[{correlacao}] {sem_data} negocio(s) da etapa {etapa} sem "
                f"nenhuma data legivel entre as chaves que a rota expoe: eles "
                f"CONTAM na etapa (a janela da consulta ja os recortou) e nao "
                f"entram em nenhum corte por data")

    # -------------------------------------------------------- cancelamentos
    async def cancellations(self, *, company_id: str, inicio: date, fim: date,
                            db: Any = None,
                            connection_id: Optional[str] = None,
                            slug: Optional[str] = None,
                            correlation_id: Optional[str] = None,
                            fonte: Any = None) -> FactSet:
        """A carteira do periodo COM os cancelados dentro. 🔴🔴 Leia isto antes.

        📊 `cancelado=T` **NAO** e "so os cancelados": e "inclua os
        cancelados". O censo v2.1 §A7 mediu, em 2025: **3.861 linhas = 3.536 com
        `cancelado='F'` + 325 com `cancelado='T'`**, e as 3.536 sao exatamente as
        do controle-ouro.

        ⛔ Quem tratar o parametro como recorte publica **a carteira inteira
        como cancelada** — e o numero RESPONDE, nao trava (CLAUDE.md §9.5). O
        estado sai do CAMPO `cancelado` de CADA LINHA, por `status_de_apolice`, e
        a taxa e `T ÷ (T+F)` sobre esta mesma populacao.
        """
        lote, fonte, correlacao, impressao, db = await self._lote_de_rota(
            company_id=company_id, db=db, connection_id=connection_id,
            slug=slug, correlation_id=correlation_id, fonte=fonte)
        linhas = await asyncio.to_thread(
            self._linhas_da_rota, fonte, ROTA_RENOVACOES, {
                "dt_ini": inicio.strftime("%d/%m/%Y"),
                "dt_fim": fim.strftime("%d/%m/%Y"),
                "qtd_pag": 5000, "pag": 1, "ordem": "nosnum",
                "orientacao": "asc", "texto": "",
                # 🔴 T = INCLUA os cancelados. Ver a docstring.
                "cancelado": "T", "resgates": "F",
            }, "renovacoes")
        self._traduzir_cancelamentos(lote, linhas, correlacao)
        lote.populacoes_lidas.add(POP_CANCELLATIONS)
        self._marcar_fingerprints(lote, {ROTA_RENOVACOES: linhas})
        return self._selar(lote, impressao)

    def _traduzir_cancelamentos(self, lote: FactSet,
                                linhas: List[Dict[str, Any]],
                                correlacao: str) -> None:
        vistos: set = set()
        for x in linhas:
            origem = str(x.get("nosnum") or "").strip()
            if not origem:
                continue
            ref = policy_ref(lote.company_id, PROVIDER_KEY, origem)
            if ref in vistos:
                continue
            vistos.add(ref)
            premio = interpretar_dinheiro(x.get("pretot"))
            # 🔴 SPEC-094.1, conserto de 04/09/2026 — esta populacao vai para
            # `cancellations`, e NAO para `policies`.
            #
            # 📊 O defeito: a taxa de cancelamento lia `policies`, que na
            # pergunta real e o lote da PRODUCAO — lido com o parametro do
            # cancelado em "F", isto e, sem uma unica apolice cancelada dentro.
            # A taxa publicada era 0,0% com confianca alta, sobre uma carteira
            # com 325 canceladas em 3.861 (8,42%). O numero respondia.
            #
            # ⚠️ E a base temporal desta rota e o FIM da vigencia. Fundi-la em
            # `policies` misturaria dois recortes de tempo na mesma lista.
            lote.cancellations.append(PolicyFact(
                policy_ref=ref, source_ref=origem,
                insurer=str(x.get("seguradora") or "").strip(),
                branch=str(x.get("ramo") or "").strip(),
                valid_from=_data(x.get("inivig")),
                valid_to=_data(x.get("fimvig")),
                premium=premio if premio is not None else UNAVAILABLE,
                kind=_tipo_do_documento(x),
                status=status_de_apolice(_cancelada(x)),
                provider_key=PROVIDER_KEY))
        cancelados = len([p for p in lote.cancellations if p.status == CANCELLED])
        sem_estado = len([p for p in lote.cancellations
                          if p.status not in STATUS_DE_APOLICE])
        lote.warnings.append(
            f"[{correlacao}] populacao com cancelados INCLUIDOS: "
            f"{cancelados} cancelada(s) em {len(lote.cancellations)} — a taxa e "
            f"sobre esta populacao, e o parametro `cancelado` da fonte INCLUI, "
            f"nao filtra ({sem_estado} sem estado legivel)")

    # ---------------------------------------------------- carteira x cliente
    async def customer_links(self, *, company_id: str, inicio: date, fim: date,
                             db: Any = None,
                             connection_id: Optional[str] = None,
                             slug: Optional[str] = None,
                             correlation_id: Optional[str] = None,
                             fonte: Any = None) -> FactSet:
        """O que cada CLIENTE tem — a materia-prima do cross-sell.

        🔴 A fonte e a rota em LOTE, e nao `/cliente_ligacoes`. 📊 O censo mediu
        `/cliente_ligacoes?codigo=` — **uma chamada por cliente**; com ~2,4 mil
        clientes seria uma varredura por pergunta. `/renovacoes` ja devolve
        `codcli` + `ramo` + `nosnum` no mesmo lote em que a carteira vem, e e a
        rota que o manifesto lista em `contacts.customer`. A ligacao por cliente
        fica registrada em **P-094.1-CLIENTE-LIGACOES**, para quando a pergunta
        for sobre UM cliente.

        ⛔ `cliente`, `cic`, `fone` e `email` sao PII e ficam na fronteira:
        `customer_ref` e hash de `codcli` (M16). Cross-sell nao precisa saber
        quem e o cliente.
        """
        lote, fonte, correlacao, impressao, db = await self._lote_de_rota(
            company_id=company_id, db=db, connection_id=connection_id,
            slug=slug, correlation_id=correlation_id, fonte=fonte)
        linhas = await asyncio.to_thread(
            self._linhas_da_rota, fonte, ROTA_RENOVACOES, {
                "dt_ini": inicio.strftime("%d/%m/%Y"),
                "dt_fim": fim.strftime("%d/%m/%Y"),
                "qtd_pag": 5000, "pag": 1, "ordem": "nosnum",
                "orientacao": "asc", "texto": "",
                "cancelado": "F", "resgates": "F",
            }, "renovacoes")
        self._traduzir_clientes(lote, linhas, correlacao)
        lote.populacoes_lidas.add(POP_CUSTOMERS)
        self._marcar_fingerprints(lote, {ROTA_RENOVACOES: linhas})
        return self._selar(lote, impressao)

    def _traduzir_clientes(self, lote: FactSet, linhas: List[Dict[str, Any]],
                           correlacao: str) -> None:
        por_cliente: Dict[str, Dict[str, Any]] = {}
        sem_cliente = 0
        for x in linhas:
            codigo = str(x.get("codcli") or "").strip()
            origem = str(x.get("nosnum") or "").strip()
            if not codigo:
                sem_cliente += 1
                continue
            ref = customer_ref(lote.company_id, PROVIDER_KEY, codigo)
            balde = por_cliente.setdefault(ref, {"apolices": [], "ramos": []})
            if origem:
                balde["apolices"].append(
                    policy_ref(lote.company_id, PROVIDER_KEY, origem))
            ramo = str(x.get("ramo") or "").strip()
            if ramo:
                balde["ramos"].append(ramo)
        for ref, balde in por_cliente.items():
            lote.customers.append(CustomerPortfolioFact(
                customer_ref=ref,
                policy_refs=tuple(dict.fromkeys(balde["apolices"])),
                branches=tuple(dict.fromkeys(balde["ramos"])),
                provider_key=PROVIDER_KEY))
        if sem_cliente:
            lote.warnings.append(
                f"[{correlacao}] {sem_cliente} documento(s) sem codigo de "
                f"cliente: eles nao entram no cross-sell e a cobertura diz "
                f"quanto — nao sao clientes de um produto so")

    # ------------------------------------------------- pendencia de emissao
    async def issuance_status(self, *, company_id: str, inicio: date, fim: date,
                              db: Any = None,
                              connection_id: Optional[str] = None,
                              slug: Optional[str] = None,
                              correlation_id: Optional[str] = None,
                              fonte: Any = None) -> FactSet:
        """🔴 UNAVAILABLE **por CUSTO MEDIDO** — e o lote diz por que.

        📊 `sit_acompanhamento_txt` existe em UMA rota so: `/documento?nosnum=`,
        que e **uma chamada por apolice**. As 17 chaves de `/documentos` (a rota
        em lote, `periodo=datinc`) NAO o trazem, e `/documentos_bi` tambem nao.
        Com 1.680 apolices no ano do controle-ouro, a pendencia de emissao
        custaria 1.680 requisicoes por pergunta.

        ⛔ E por isso este metodo **nao chama nada**: ele devolve o lote com
        `fingerprints` VAZIO. Marcar `/documento` como lida-e-vazia seria mentir
        na direcao mais cara — "perguntei e nao veio nada" autoriza o registry a
        afirmar sobre o periodo, e ninguem perguntou. Rota nao lida nao entra no
        mapa.

        Registrado em **P-094.1-ISSUANCE**: a rota existe, o campo existe, e o
        que falta e um lote. Nao e "ainda nao olhamos".
        """
        lote, fonte, correlacao, impressao, db = await self._lote_de_rota(
            company_id=company_id, db=db, connection_id=connection_id,
            slug=slug, correlation_id=correlation_id, fonte=fonte)
        lote.fingerprints = {}
        # ⛔ E `populacoes_lidas` fica VAZIA: ninguem perguntou. Marcar aqui
        # autorizaria a formula a afirmar sobre o periodo.
        lote.warnings.append(
            f"[{correlacao}] pendencia de emissao INDISPONIVEL por custo: "
            f"`sit_acompanhamento_txt` so existe em {ROTA_DOCUMENTO}, que e uma "
            f"chamada POR APOLICE (P-094.1-ISSUANCE). A rota em lote nao traz o "
            f"campo — e isto e uma afirmacao sobre a FONTE, nunca sobre a "
            f"corretora ter zero pendencias")
        return self._selar(lote, impressao)

    # -------------------------------------------------- os recortes do lote
    async def policies(self, *, company_id: str, inicio: date, fim: date,
                       time_basis: str = "POLICY_VALID_FROM",
                       **kw: Any) -> List[PolicyFact]:
        lote = await self.fatos(company_id=company_id, inicio=inicio, fim=fim, **kw)
        return lote.policies

    async def producer_assignments(self, *, company_id: str, inicio: date,
                                   fim: date, **kw: Any) -> List[ProducerAssignmentFact]:
        lote = await self.fatos(company_id=company_id, inicio=inicio, fim=fim, **kw)
        return lote.assignments

    async def commissions(self, *, company_id: str, inicio: date, fim: date,
                          **kw: Any) -> List[CommissionFact]:
        lote = await self.fatos(company_id=company_id, inicio=inicio, fim=fim, **kw)
        return lote.commissions

    async def renewals(self, *, company_id: str, inicio: date, fim: date,
                       **kw: Any) -> List[RenewalFact]:
        lote = await self.fatos(company_id=company_id, inicio=inicio, fim=fim, **kw)
        return lote.renewals

    # ------------------------------------------------------- capacidades
    async def capabilities(self, *, company_id: str = "", **kw: Any) -> Dict[str, str]:
        """O que a InfoCap consegue entregar — do CENSO, não de palpite.

        📊 `docs/canon/providers/infocap/infocap-capability-manifest.json`, 51
        rotas medidas em 03/09/2026: SUPPORTED 9 · PARTIAL 6 · UNKNOWN 3 ·
        UNAVAILABLE 1. O BLOCO C põe um tipo em volta disto (drift, cobertura,
        `source_refs`); aqui devolve-se o mapa cru, que é o que o port promete.
        """
        from app.comercial.manifesto import carregar_manifesto

        return carregar_manifesto(PROVIDER_KEY).estados()

    async def manifesto(self, *, company_id: str = "",
                        lote: Any = None, **kw: Any) -> Any:
        """O manifesto do censo, JÁ com o drift desta leitura marcado.

        🔴 É aqui que o BLOCO C encosta no BLOCO B: o adapter é quem tem os
        fingerprints medidos (`FactSet.fingerprints`), e o manifesto é quem
        sabe qual capacidade depende de qual rota. Nenhum dos dois consegue
        detectar drift sozinho.
        """
        from app.comercial.manifesto import carregar_manifesto

        manifesto = carregar_manifesto(PROVIDER_KEY)
        if lote is not None and getattr(lote, "fingerprints", None):
            avisos = manifesto.conferir_drift(lote.fingerprints)
            lote.warnings.extend(avisos)
        return manifesto


register_brokerage_analytics_provider(InfocapAnalyticsProvider())
