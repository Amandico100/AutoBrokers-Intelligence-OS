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
import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from app.comercial.cbim import (
    ENDORSEMENT,
    NEW,
    RENEWAL,
    UNAVAILABLE,
    UNKNOWN,
    CommissionFact,
    FactSet,
    Money,
    PolicyFact,
    ProducerAssignmentFact,
    Provenance,
    RenewalFact,
    interpretar_dinheiro,
    policy_ref,
    producer_ref,
)
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
        raise RecusaDeContaCompartilhada(
            "conexão compartilhada com outra corretora — decisão F-094-07. "
            "Duas corretoras ativas apontam para a MESMA conta do provider, e "
            "a leitura da segunda mostraria a carteira da primeira. A leitura "
            "foi recusada e nenhum Artifact é publicado.")
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


def impressao_da_rota(linhas: List[Dict[str, Any]]) -> str:
    """`sha256` das chaves ORDENADAS da primeira linha — o mesmo do censo.

    📊 É a forma exata de `infocap-schema-fingerprints.json`
    (`sha256_das_chaves_ordenadas`): 20 chaves em `/documentos_bi`, 33 em
    `/renovacoes`. Comparar com o censo é como o BLOCO C descobre DRIFT sem
    esperar um cron (a proposta pedia um monitor agendado; §6 o recusou).
    """
    for linha in linhas:
        if isinstance(linha, dict) and linha:
            chaves = ",".join(sorted(linha.keys()))
            return hashlib.sha256(chaves.encode("utf-8")).hexdigest()
    return ""


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


def _cancelada(linha: Dict[str, Any]) -> bool:
    return str(linha.get("cancelado") or "").strip().upper() in ("T", "S", "TRUE", "1")


# ==========================================================================
# O adapter
# ==========================================================================
class InfocapAnalyticsProvider:
    """Implementa `BrokerageAnalyticsProvider` sobre a CorpAPI da InfoCap."""

    provider_key = PROVIDER_KEY

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
        conn = decisao.get("selected_connection")
        if not conn:
            raise FalhaDoProvider(
                "a corretora não tem uma conexão InfoCap utilizável "
                f"(status: {decisao.get('status')})")
        return conn

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
                   .update({"last_used_at": datetime.now().isoformat()})
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

        lote = self._traduzir(company_id, producao, renovacoes, correlacao)
        lote.provenance = Provenance(
            connection_id=conexao_id,
            correlation_id=correlacao,
            fetched_at=datetime.now(),
            fingerprint=lote.fingerprints.get("__combinado__", ""),
            account_fingerprint=impressao,
        )
        if db is not None and conexao_id:
            await self._marcar_uso(db, company_id=company_id, connection_id=conexao_id)
        return lote

    # ------------------------------------------------------------ tradução
    def _traduzir(self, company_id: str, producao: List[Dict[str, Any]],
                  renovacoes: List[Dict[str, Any]],
                  correlacao: str) -> FactSet:
        """Linha crua → fato canônico. É AQUI que a InfoCap deixa de existir."""
        lote = FactSet(company_id=company_id, provider_key=PROVIDER_KEY)
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
                status="cancelada" if _cancelada(x) else "vigente",
                provider_key=PROVIDER_KEY,
            ))
            acumulado.setdefault(ref, {})["accrued"] = _dinheiro(
                x.get("val_c"), "comissão apropriada", ref)

        # --- renovações: a base POLICY_VALID_TO -----------------------------
        vistos_venc: set = set()
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
                lote.assignments.append(ProducerAssignmentFact(
                    policy_ref=ref,
                    producer_ref=pref,
                    producer_label=rotulo,
                    # 🔴 O rótulo da InfoCap vai para `role_source` e NUNCA
                    # decide `actor_type`: quem decide é o mapa versionado por
                    # corretora (BLOCO F).
                    role_source=str(p.get("agente") or "").strip(),
                    share=float(share.amount) if share is not None else None,
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
        lote.fingerprints = {k: v for k, v in
                             (("/documentos_bi", fp_prod), ("/renovacoes", fp_renov))
                             if v}
        lote.fingerprints["__combinado__"] = hashlib.sha256(
            f"{fp_prod}|{fp_renov}".encode("utf-8")).hexdigest()[:16]
        return lote

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
