# -*- coding: utf-8 -*-
r"""M-A4 — A SEGUNDA CORRETORA NAO VE A PRIMEIRA. **Guarda CANONICO.**

⚖️ Nao conta no teto de 12 guardas: `CLAUDE.md` §7 exige *"teste automatico de
isolamento com dois tenants reais"* de **todo contrato novo**.

```
RLS + filtro obrigatorio no repository/service
    + constraints e foreign keys
    + teste automatico de isolamento com dois tenants reais
```

🔴 **E o filtro e conferido no CODIGO, nao na RLS.** O backend usa *service
role*: uma RLS sem policy nao protege nada contra erro de filtro no codigo.

```
 [G4a] CONEXAO    a `archived` NUNCA e escolhida -- com o resolver REAL
 [G4b] LEITURA    o tenant B nunca devolve linha do tenant A
 [G4c] CACHE      a chave do `/itens` tem `company_id` E `connection_id`
 [G4d] DOCUMENTO  a chave do documento oficial tambem tem as duas
 [G4e] PII        nada do que a porta devolve carrega nome, CPF ou numero
```

📊 **A fixture modela o que a corretora piloto TEM**, medido no BLOCO 0:

```
tenant A   3 conexoes `archived` (uma com `invalid_credentials`) + 1 `connected`
tenant B   1 conexao `connected`
```

⚠️ A parte do `connection_id` **nao e cross-tenant** — e FRESCOR dentro do mesmo
tenant: trocar a conexao ativa nao invalidava o cache, e por ate 180 s o
corretor continuava lendo o que a conexao antiga devolveu. Chave sem
`company_id` seria BLOCKER; chave sem `connection_id` e ESSENCIAL. **Este gate
mede as duas**, e diz qual e qual.

⛔ SEGURANCA: `SEM_REDE=1`, nenhuma chamada HTTP, nenhum banco. As conexoes sao
FIXTURE; nenhuma credencial, nenhum `base_url` real, nenhum id de producao.

Rodar (de dentro de `backend/`):
    PYTHONIOENCODING=utf-8 python tests/test_a_segunda_corretora_nao_ve_a_primeira.py
    ... --so G4c   ·   ... --medir   ·   ... --mutar [M-A4a]
"""
from __future__ import annotations

import asyncio
import io
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import types

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
os.environ.setdefault("POLICY_INTELLIGENCE_V2", "true")
os.environ["SEM_REDE"] = "1"

_CONNECT = socket.socket.connect
_CONNECT_EX = socket.socket.connect_ex


def _proibir(self, *a, **k):  # noqa: ANN001
    raise RuntimeError("SPEC-EXTRA-001.1: SEM_REDE=1. Destino: %r" % (a[0] if a else None,))


def _bloquear_a_rede():
    socket.socket.connect = _proibir       # type: ignore[assignment]
    socket.socket.connect_ex = _proibir    # type: ignore[assignment]


def _devolver_a_rede():
    socket.socket.connect = _CONNECT       # type: ignore[assignment]
    socket.socket.connect_ex = _CONNECT_EX  # type: ignore[assignment]


PASS = 0
FAIL = 0
MEDIDAS: dict = {}


def _p(texto):
    try:
        print(texto)
    except UnicodeEncodeError:
        cod = getattr(sys.stdout, "encoding", None) or "ascii"
        print(texto.encode(cod, "replace").decode(cod, "replace"))


def check(nome, cond, detalhe=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        _p("  [ok] %s" % nome)
    else:
        FAIL += 1
        _p("  [FALHOU] %s" % nome + ("\n         %s" % str(detalhe)[:500] if detalhe else ""))
    return bool(cond)


def medir(chave, valor):
    MEDIDAS[chave] = valor
    return valor


# ===========================================================================
# A FIXTURE DAS DUAS CORRETORAS
# ===========================================================================
#
# ⛔ Ids OPACOS de fixture. Nenhum id de producao, nenhum `base_url` real,
#    nenhum segredo — `encrypted_secret_ref` e um rotulo, nao uma referencia.
EMPRESA_A = "empresa-a-de-fixture"
EMPRESA_B = "empresa-b-de-fixture"
CONEXAO_A_VIVA = "conexao-a-viva"
CONEXAO_B_VIVA = "conexao-b-viva"

TEMPLATE = {"slug": "infocap"}


def _conexao(cid, empresa, status, *, health="healthy", arquivada=False, segredo=True):
    return {
        "id": cid,
        "company_id": empresa,
        "status": status,
        "health_status": health,
        "metadata": ({"archived": True} if arquivada else {}),
        "encrypted_secret_ref": ("vault://rotulo-de-fixture" if segredo else None),
        "connection_config": {"base_url": "https://exemplo.invalido"},
        "connector_templates": TEMPLATE,
    }


CONEXOES = [
    # 📊 tenant A: 3 arquivadas (uma com credencial invalida) + 1 viva
    _conexao("conexao-a-arquivada-1", EMPRESA_A, "archived", arquivada=True, segredo=False),
    _conexao("conexao-a-arquivada-2", EMPRESA_A, "archived", arquivada=True, segredo=False),
    _conexao("conexao-a-arquivada-3", EMPRESA_A, "archived", health="invalid_credentials",
             arquivada=True),
    # 🔴 A QUARTA E SINTETICA, e existe por uma razao: nas tres medidas acima o
    #    arquivamento NAO e o unico filtro que as exclui (duas nao tem segredo,
    #    a terceira tem credencial invalida). Com so essas tres, desligar o
    #    filtro de arquivamento nao mudaria NADA — e o gate ficaria verde sobre
    #    um filtro que poderia ter sido apagado. Esta conexao e arquivada e
    #    PERFEITA em tudo o mais: ela isola o filtro que se quer medir.
    _conexao("conexao-a-arquivada-perfeita", EMPRESA_A, "archived", arquivada=True),
    _conexao(CONEXAO_A_VIVA, EMPRESA_A, "connected"),
    # 📊 tenant B: 1 viva
    _conexao(CONEXAO_B_VIVA, EMPRESA_B, "connected"),
]

#: Os dois packs sao DIFERENTES de proposito: se a leitura de B devolvesse a
#: linha de A, este rotulo apareceria — e ele nao existe em lugar nenhum de B.
ROTULO_SO_DE_A = "COBERTURA EXCLUSIVA DA CORRETORA A"
ROTULO_SO_DE_B = "COBERTURA EXCLUSIVA DA CORRETORA B"


def _documento(empresa):
    rotulo = ROTULO_SO_DE_A if empresa == EMPRESA_A else ROTULO_SO_DE_B
    nosnum = 111001 if empresa == EMPRESA_A else 222002
    return {
        "codfil": 1, "nosnum": nosnum, "numapo": "900000000000%d" % (1 if empresa == EMPRESA_A else 2),
        "seguradora_abrev": "HDI", "ramo_abrev": "RESI",
        "inivig": "01/01/2026", "fimvig": "01/01/2027", "cancelado": "F",
        "preliq": 100.0, "pretot": 110.0, "numpar": 1, "forma_pag": "Boleto Bancário",
        "parcelas": [{"parc": 1, "datvenc": "10/01/2026", "vlvenc": 110.0,
                      "forma_pagamento": "Boleto Bancário"}],
    }, [{"item": 1, "garantias": [
        {"garantia": rotulo, "impseg": 1000.0, "premio": 100.0, "franquia": None}]}]


def _pack_de(empresa):
    from app.api import infocap_connector as CN  # noqa: PLC0415
    doc, itens = _documento(empresa)
    return CN._build_evidence_pack(doc, None, None, True,
                                   envelope={"documento": [doc]}, items=itens)


# ===========================================================================
# [G4a] CONEXAO — a `archived` NUNCA e escolhida (resolver REAL)
# ===========================================================================
def gate_G4a():
    _p("\n[G4a] CONEXAO -- a `archived` NUNCA e escolhida (com o resolver REAL)")
    from app.api.infocap_connector import (  # noqa: PLC0415
        _resolve_infocap_connection_candidates,
    )

    a = _resolve_infocap_connection_candidates(
        CONEXOES, company_id=EMPRESA_A, requested_connection_id=None,
        provider_default_base_url="https://exemplo.invalido")
    escolhida = (a.get("selected_connection") or {}).get("id")
    medir("conexao_escolhida_a", escolhida or "NENHUMA")
    check("[G4a] A: entre 4 arquivadas e 1 viva, escolhe a VIVA",
          escolhida == CONEXAO_A_VIVA, a.get("summary"))
    check("[G4a] A: e o resumo CONTA as 4 inativas (nao as esconde)",
          (a.get("summary") or {}).get("inactive_connection_count") == 4,
          a.get("summary"))
    check("[G4a] 🔴 e SO UMA e elegivel: a arquivada-mas-perfeita nao entra "
          "(se entrasse, seriam 2 e a escolha viraria `ambiguous_connection`)",
          (a.get("summary") or {}).get("eligible_connection_count") == 1,
          a.get("summary"))

    b = _resolve_infocap_connection_candidates(
        CONEXOES, company_id=EMPRESA_B, requested_connection_id=None,
        provider_default_base_url="https://exemplo.invalido")
    escolhida_b = (b.get("selected_connection") or {}).get("id")
    medir("conexao_escolhida_b", escolhida_b or "NENHUMA")
    check("[G4a] 🔴 B: a resolucao de B escolhe a conexao DE B -- as 4 de A nao "
          "entram no escopo",
          escolhida_b == CONEXAO_B_VIVA, b.get("summary"))
    check("[G4a] B: e o escopo de B tem 1 conexao, nao 5",
          (b.get("summary") or {}).get("total_infocap_connections") == 1,
          b.get("summary"))

    # 🔴 O PAR que prova que o resolver CONSEGUE recusar: uma empresa sem
    #    conexao nenhuma nao pode herdar a de ninguem.
    c = _resolve_infocap_connection_candidates(
        CONEXOES, company_id="empresa-c-sem-conexao", requested_connection_id=None,
        provider_default_base_url="https://exemplo.invalido")
    check("[G4a] PAR: uma corretora SEM conexao nao recebe a de ninguem",
          (c.get("selected_connection") or {}).get("id") is None, c.get("summary"))

    # 🔴 E o PAR-B: pedir explicitamente a conexao ARQUIVADA tambem nao a traz.
    d = _resolve_infocap_connection_candidates(
        CONEXOES, company_id=EMPRESA_A, requested_connection_id="conexao-a-arquivada-1",
        provider_default_base_url="https://exemplo.invalido")
    check("[G4a] PAR-B: pedir a conexao ARQUIVADA pelo id tambem nao a escolhe",
          (d.get("selected_connection") or {}).get("id") is None, d.get("summary"))


# ===========================================================================
# [G4b] LEITURA — o tenant B nunca devolve linha do tenant A
# ===========================================================================
class _ProviderDublado:
    """O `InfoCapProvider` com o CONECTOR dublado por `company_id`.

    ⚠️ O que e falso e SO a chamada HTTP: o pack e montado pelo motor real
    (`_build_evidence_pack`), e a traducao e a de producao. O dublê responde
    packs DIFERENTES por empresa — e e isso que torna o vazamento visivel.
    """

    def __init__(self):
        from app.providers.infocap_policy_provider import InfoCapProvider  # noqa: PLC0415
        self._real = InfoCapProvider()
        self.chamadas = []

    provider_key = "infocap"

    def capacidades(self):
        return self._real.capacidades()

    async def lookup(self, *, company_id, **kw):
        self.chamadas.append(("lookup", company_id))
        pack = _pack_de(company_id)
        return {"ok": True, "status": "found", "documents_count": 1,
                "matches": [{"policy_locator_ref": "infocap:1:%s" % pack.get("policy_ref"),
                             "insurer_key": "HDI", "product": "RESI",
                             "valid_from": "01/01/2026", "valid_to": "01/01/2027",
                             "cancelled": False, "policy_status": "ativo"}],
                "policy_evidence_pack": pack}

    async def detail(self, *, company_id, policy_ref, **kw):
        self.chamadas.append(("detail", company_id, policy_ref))
        return {"ok": True, "status": "found", "policy_evidence_pack": _pack_de(company_id)}

    async def detalhar_apolice(self, *, company_id, apolice_ref, **kw):
        from app.providers.infocap_policy_provider import (  # noqa: PLC0415
            apolice_reconciliada_do_pack,
        )
        bruto = await self.detail(company_id=company_id, policy_ref=apolice_ref)
        return apolice_reconciliada_do_pack(bruto["policy_evidence_pack"],
                                            apolice_ref=apolice_ref)

    async def listar_apolices(self, *, company_id, cliente_ref, **kw):
        from app.providers.infocap_policy_provider import (  # noqa: PLC0415
            lista_de_apolices_do_lookup,
        )
        bruto = await self.lookup(company_id=company_id)
        return lista_de_apolices_do_lookup(bruto, cliente_ref=cliente_ref)


def _rodar(corrotina):
    _devolver_a_rede()   # no Windows, criar o loop usa `socketpair` local
    try:
        laco = asyncio.new_event_loop()
    finally:
        _bloquear_a_rede()
    try:
        return laco.run_until_complete(corrotina)
    finally:
        laco.close()


def gate_G4b():
    _p("\n[G4b] LEITURA -- o tenant B nunca devolve linha do tenant A")
    provider = _ProviderDublado()

    a = _rodar(provider.detalhar_apolice(company_id=EMPRESA_A, apolice_ref="infocap:1:111001"))
    b = _rodar(provider.detalhar_apolice(company_id=EMPRESA_B, apolice_ref="infocap:1:222002"))

    rotulos_a = {c.rotulo for c in a.coberturas}
    rotulos_b = {c.rotulo for c in b.coberturas}
    medir("vazou_de_a_para_b", 1 if (rotulos_a & rotulos_b) else 0)
    check("[G4b] A ve a cobertura de A", ROTULO_SO_DE_A in rotulos_a, rotulos_a)
    check("[G4b] B ve a cobertura de B", ROTULO_SO_DE_B in rotulos_b, rotulos_b)
    check("[G4b] 🔴 B NAO ve nenhuma linha de A", not (rotulos_a & rotulos_b),
          rotulos_a & rotulos_b)

    lista_b = _rodar(provider.listar_apolices(company_id=EMPRESA_B, cliente_ref="ref-opaca-b"))
    check("[G4b] a LISTAGEM de B tambem nao traz linha de A",
          all(ROTULO_SO_DE_A not in str(i) for i in lista_b.itens), lista_b.itens)
    check("[G4b] e toda operacao recebeu o `company_id` explicitamente "
          "(nenhuma deduziu o tenant de contexto global)",
          all(len(c) >= 2 and c[1] in (EMPRESA_A, EMPRESA_B) for c in provider.chamadas),
          provider.chamadas)


# ===========================================================================
# [G4c] CACHE — a chave do `/itens` tem `company_id` E `connection_id`
# ===========================================================================
class _RedisDeMentira:
    """Guarda as chaves que o conector pediu. Nunca devolve nada de cache."""

    def __init__(self):
        self.lidas = []
        self.escritas = []
        self.armazenado = {}

    async def get(self, chave):
        self.lidas.append(chave)
        return self.armazenado.get(chave)

    async def setex(self, chave, _ttl, valor):
        self.escritas.append(chave)
        self.armazenado[chave] = valor


class _RespostaHttp:
    status_code = 200

    def __init__(self, corpo):
        self._corpo = corpo

    def json(self):
        return self._corpo


class _ClienteDeMentira:
    def __init__(self, corpo):
        self._corpo = corpo
        self.pedidos = []

    async def get(self, caminho, params=None, headers=None):
        self.pedidos.append((caminho, params))
        return _RespostaHttp(self._corpo)


def _chave_do_itens(empresa, conexao, redis):
    """Roda `_fetch_policy_items` DE VERDADE, com o Redis dublado em memoria."""
    from app.api import infocap_connector as CN  # noqa: PLC0415

    casca = types.ModuleType("app.core.redis")

    async def _get_async_redis_client():
        return redis

    casca.get_async_redis_client = _get_async_redis_client
    anterior = sys.modules.get("app.core.redis")
    sys.modules["app.core.redis"] = casca
    try:
        cliente = _ClienteDeMentira({"itens": [{"item": 1, "garantias": [
            {"garantia": "X", "impseg": 1.0, "premio": 1.0}]}]})
        _rodar(CN._fetch_policy_items(
            cliente, {}, itens_path="/itens", codfil=1, nosnum=999,
            company_id=empresa, connection_id=conexao))
    finally:
        if anterior is None:
            sys.modules.pop("app.core.redis", None)
        else:
            sys.modules["app.core.redis"] = anterior
    return redis.lidas[-1] if redis.lidas else ""


def gate_G4c():
    _p("\n[G4c] CACHE -- a chave do `/itens` tem `company_id` E `connection_id`")
    redis = _RedisDeMentira()
    chave_a = _chave_do_itens(EMPRESA_A, CONEXAO_A_VIVA, redis)
    chave_b = _chave_do_itens(EMPRESA_B, CONEXAO_B_VIVA, redis)
    # 📊 Mesmo TENANT, conexao diferente: e o caso de FRESCOR (ESSENCIAL).
    chave_a2 = _chave_do_itens(EMPRESA_A, "conexao-a-nova", redis)

    medir("chave_itens_separa_tenant", 1 if chave_a != chave_b else 0)
    medir("chave_itens_separa_conexao", 1 if chave_a != chave_a2 else 0)
    check("[G4c] 🔴 BLOCKER: duas corretoras dao chaves DIFERENTES",
          chave_a and chave_b and chave_a != chave_b, (chave_a, chave_b))
    check("[G4c] ESSENCIAL: a MESMA corretora com outra conexao tambem da chave "
          "diferente (o cache de 180 s deixa de servir a conexao antiga)",
          chave_a and chave_a2 and chave_a != chave_a2, (chave_a, chave_a2))
    check("[G4c] e a chave NAO carrega o `company_id` em claro (e hash)",
          EMPRESA_A not in chave_a, chave_a)

    # 🔴 O PROBE QUE ISOLA O `company_id`. Sem ele, apagar o `company_id` da
    #    chave passaria VERDE: as duas corretoras do teste tambem tem conexoes
    #    diferentes, e a chave continuaria diferente pelo motivo ERRADO. Duas
    #    corretoras nunca compartilham conexao na vida real — e e exatamente por
    #    isso que so um caso patologico consegue medir a metade certa.
    mesma_conexao_a = _chave_do_itens(EMPRESA_A, "conexao-compartilhada", redis)
    mesma_conexao_b = _chave_do_itens(EMPRESA_B, "conexao-compartilhada", redis)
    medir("chave_itens_isola_company", 1 if mesma_conexao_a != mesma_conexao_b else 0)
    check("[G4c] 🔴 BLOCKER isolado: com a MESMA conexao, duas corretoras ainda "
          "dao chaves diferentes (o `company_id` esta mesmo na chave)",
          mesma_conexao_a != mesma_conexao_b, (mesma_conexao_a, mesma_conexao_b))

    # 🔴 O PAR: a MESMA corretora com a MESMA conexao reencontra a MESMA chave —
    #    senao "chaves diferentes" seria um contador aleatorio, e o cache nunca
    #    acertaria.
    chave_a3 = _chave_do_itens(EMPRESA_A, CONEXAO_A_VIVA, _RedisDeMentira())
    check("[G4c] PAR: mesma corretora + mesma conexao = MESMA chave "
          "(a chave e estavel, nao aleatoria)", chave_a == chave_a3, (chave_a, chave_a3))
    check("[G4c] e o cache foi ESCRITO na mesma chave que foi lida",
          chave_a in redis.escritas, redis.escritas[:3])


# ===========================================================================
# [G4d] DOCUMENTO — a chave do documento oficial tambem tem as duas
# ===========================================================================
def gate_G4d():
    _p("\n[G4d] DOCUMENTO -- a chave do documento oficial tem as duas partes")
    from app.services.policy_document_evidence_service import (  # noqa: PLC0415
        policy_document_cache_key,
    )
    locator = {"provider": "infocap", "codfil": "1", "nosnum": "999"}
    a = policy_document_cache_key(EMPRESA_A, locator, "hash-de-fixture", CONEXAO_A_VIVA)
    b = policy_document_cache_key(EMPRESA_B, locator, "hash-de-fixture", CONEXAO_B_VIVA)
    a2 = policy_document_cache_key(EMPRESA_A, locator, "hash-de-fixture", "conexao-a-nova")
    a3 = policy_document_cache_key(EMPRESA_A, locator, "hash-de-fixture", CONEXAO_A_VIVA)

    medir("chave_documento_separa_tenant", 1 if a != b else 0)
    medir("chave_documento_separa_conexao", 1 if a != a2 else 0)
    check("[G4d] 🔴 BLOCKER: duas corretoras dao chaves DIFERENTES", a != b, (a, b))
    check("[G4d] ESSENCIAL: a mesma corretora com outra conexao tambem", a != a2, (a, a2))
    check("[G4d] PAR: mesma corretora + mesma conexao = MESMA chave", a == a3)
    # 🔴 O MESMO probe isolador do G4c, pela mesma razao.
    compartilhada_a = policy_document_cache_key(EMPRESA_A, locator, "hash-de-fixture",
                                                "conexao-compartilhada")
    compartilhada_b = policy_document_cache_key(EMPRESA_B, locator, "hash-de-fixture",
                                                "conexao-compartilhada")
    medir("chave_documento_isola_company",
          1 if compartilhada_a != compartilhada_b else 0)
    check("[G4d] 🔴 BLOCKER isolado: com a MESMA conexao, duas corretoras ainda "
          "dao chaves diferentes",
          compartilhada_a != compartilhada_b, (compartilhada_a, compartilhada_b))
    check("[G4d] e a chave nao carrega `company_id` nem o locator em claro",
          EMPRESA_A not in a and "999" not in a.replace("hash-de-fixture", ""), a)

    # ⚠️ Expand-first: sem `connection_id` a chave mantem a FORMA antiga, para
    #    que o que ja foi escrito continue encontravel (CLAUDE.md §8).
    velha = policy_document_cache_key(EMPRESA_A, locator, "hash-de-fixture")
    check("[G4d] sem `connection_id`, a chave mantem a forma antiga (expand-first)",
          velha.startswith("policydoc:") and ":infocap:" in velha
          and velha != a, velha)


# ===========================================================================
# [G4e] PII — nada do que a porta devolve carrega pessoa
# ===========================================================================
RE_CPF = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
RE_CNPJ = re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b")
RE_TELEFONE = re.compile(r"\b\d{2}9?\d{8}\b")


def gate_G4e():
    _p("\n[G4e] PII -- nada do que a porta devolve carrega pessoa")
    provider = _ProviderDublado()
    a = _rodar(provider.detalhar_apolice(company_id=EMPRESA_A, apolice_ref="infocap:1:111001"))
    texto = repr(a)
    achados = (RE_CPF.findall(texto) + RE_CNPJ.findall(texto) + RE_TELEFONE.findall(texto))
    medir("pii_na_apolice", len(achados))
    check("[G4e] a `Apolice` devolvida nao tem CPF, CNPJ nem telefone", not achados, achados)

    # 🔴 O PAR: os detectores CONSEGUEM achar. Sem isto, "0 achados" tanto pode
    #    ser limpeza quanto regex quebrada.
    check("[G4e] PAR: os detectores acham num texto sintetico",
          bool(RE_CPF.search("123.456.789-00"))
          and bool(RE_CNPJ.search("12.345.678/0001-90"))
          and bool(RE_TELEFONE.search("47999998888")))

    # ⚠️ O que ATRAVESSA de proposito e o locator OPACO — e ele nao e um numero
    #    humano de apolice: quem o le nao sabe (e nao pode saber) o que ele guarda.
    from app.providers.policy_data_provider import parse_policy_locator_ref  # noqa: PLC0415
    check("[G4e] o `apolice_ref` e o locator opaco, e ele PARSEIA como locator",
          parse_policy_locator_ref(a.apolice_ref) is not None, a.apolice_ref)
    check("[G4e] PAR: um numero humano de apolice NAO parseia como locator "
          "(nunca vira ref)",
          parse_policy_locator_ref("900000000000001") is None)


GATES = {"G4a": gate_G4a, "G4b": gate_G4b, "G4c": gate_G4c,
         "G4d": gate_G4d, "G4e": gate_G4e}


# ===========================================================================
# AS MUTACOES
# ===========================================================================
MUTACOES = [
    # M-A4a: a chave do `/itens` perde o `company_id` -> CROSS-TENANT.
    ("M-A4a", "app/api/infocap_connector.py",
     '        f"infocap:itens:{_short_hash(str(company_id))}:"',
     '        f"infocap:itens:"',
     "G4c"),
    # M-A4b: a chave do `/itens` perde o `connection_id` -> FRESCOR.
    ("M-A4b", "app/api/infocap_connector.py",
     '        f"{_short_hash(str(connection_id))}:{codfil}:{nosnum}"',
     '        f"{codfil}:{nosnum}"',
     "G4c"),
    # M-A4c: a chave do documento perde o `company_id`.
    ("M-A4c", "app/services/policy_document_evidence_service.py",
     '    company_hash = _short_hash(company_id, 16)',
     '    company_hash = "todos"',
     "G4d"),
    # M-A4d: a chave do documento perde o `connection_id`.
    ("M-A4d", "app/services/policy_document_evidence_service.py",
     '    conexao = f"{_short_hash(connection_id, 12)}:" if str(connection_id or "").strip() else ""',
     '    conexao = ""',
     "G4d"),
    # M-A4e: a conexao ARQUIVADA volta a ser elegivel -> o corretor le pela
    #        credencial invalida, e o sintoma e "a InfoCap nao respondeu".
    ("M-A4e", "app/api/infocap_connector.py",
     "    eligible = [\n"
     "        conn for conn in scoped\n"
     "        if not _is_inactive_connection(conn)",
     "    eligible = [\n"
     "        conn for conn in scoped\n"
     "        if True",
     "G4a"),
]


def _rodar_gate(gate):
    return subprocess.run(
        [sys.executable, os.path.abspath(__file__), "--so", gate, "--medir"],
        cwd=RAIZ, capture_output=True, text=True, timeout=900,
        env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"},
    )


def rodar_mutacoes(filtro=None):
    _p("\n[MUT] MUTACOES POR COPIA -- cada uma em SUBPROCESSO. A arvore precisa estar parada.")
    vermelhas = verdes = 0
    for mid, relativo, de, para, gate in MUTACOES:
        if filtro and mid != filtro:
            continue
        caminho = os.path.join(RAIZ, relativo)
        original = io.open(caminho, encoding="utf-8").read()
        if de not in original:
            _p("  [FALHOU] %s: a ancora nao existe em %s -- mutacao NAO aplicada "
               "NAO e mutacao passada" % (mid, relativo))
            verdes += 1
            continue
        base = _rodar_gate(gate)
        backup = tempfile.NamedTemporaryFile(delete=False, suffix=".bak-0011").name
        shutil.copyfile(caminho, backup)
        try:
            io.open(caminho, "w", encoding="utf-8", newline="\n").write(
                original.replace(de, para, 1))
            r = _rodar_gate(gate)
            falhas = [l.strip() for l in (r.stdout or "").splitlines() if "[FALHOU]" in l]
            if base.returncode == 0 and r.returncode != 0 and falhas:
                vermelhas += 1
                _p("  [ok] %s deixa %s VERMELHO: %s" % (mid, gate, falhas[0][:180]))
            else:
                verdes += 1
                _p("  [FALHOU] %s NAO deixou %s vermelho (base rc=%s, mutado rc=%s)\n%s"
                   % (mid, gate, base.returncode, r.returncode, (r.stdout or r.stderr)[-900:]))
        finally:
            shutil.copyfile(backup, caminho)
            os.unlink(backup)
            assert io.open(caminho, encoding="utf-8").read() == original, \
                "restauracao falhou em " + relativo
    _p("\n  PLACAR DAS MUTACOES: %d vermelhas - %d verdes" % (vermelhas, verdes))
    return verdes == 0


def main():
    args = sys.argv[1:]
    if "--mutar" in args:
        i = args.index("--mutar")
        filtro = args[i + 1] if len(args) > i + 1 and args[i + 1].startswith("M-") else None
        return 0 if rodar_mutacoes(filtro) else 1

    so = args[args.index("--so") + 1] if "--so" in args else None
    calado = "--medir" in args
    if not calado:
        _p("=" * 78)
        _p("  M-A4 -- A SEGUNDA CORRETORA NAO VE A PRIMEIRA  (guarda CANONICO, CLAUDE.md §7)")
        _p("=" * 78)
    _bloquear_a_rede()
    try:
        for gid, fn in GATES.items():
            if so and gid != so:
                continue
            try:
                fn()
            except Exception as exc:  # noqa: BLE001
                import traceback
                check("%s EXPLODIU (defeito do guarda ou do produto)" % gid, False,
                      "%s: %s\n%s" % (type(exc).__name__, exc, traceback.format_exc()[-900:]))
    finally:
        _devolver_a_rede()

    for chave, valor in sorted(MEDIDAS.items()):
        print("MEDIDA %s %s" % (chave, valor))
    if not calado:
        _p("\n" + "=" * 78)
        _p("  %d assercoes verdes - %d vermelhas" % (PASS, FAIL))
        _p("=" * 78)
    return 1 if FAIL else 0


def test_a_segunda_corretora_nao_ve_a_primeira():
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
