# -*- coding: utf-8 -*-
r"""M-D1 — O DOCUMENTO E LIDO SEMPRE QUE A PERGUNTA E DE APOLICE. BLOCO D.

🔴 **A regra que este guarda existe para proteger cabe em uma linha:**

```
a pergunta e SOBRE APOLICE?  ->  o documento oficial e lido. Ponto.
```

E *"sobre apolice"* e decidido pelo **DESTINO DA CHAMADA**, nunca pelo texto.

📊 **O defeito medido, em 14/09/2026, com o comando ao lado** (§8.1):

```python
policy_document_evidence_requested(pergunta, explicit=False)
   q1 "[CPF]"                                          False
   q2 "Sim! Fazendo o favor! [CPF]"                     False   <- pedia FRANQUIA
   q3 "...tem direito a carro reserva em caso de pane"  False
   q4..q7                                               True
```

**3 das 7 perguntas REAIS do chat nao casavam palavra nenhuma** — e duas delas
eram exatamente sobre franquia e sobre o que a apolice cobre. O PDF nao era
lido justamente onde ele era a unica fonte.

```
 [GD1a] AS 7        as 7 perguntas do corpus pela TOOL REAL -> leitura pedida em 7 de 7
 [GD1b] O ANTES     as mesmas 7 pela palavra-chave -> 4 de 7 (e o guarda MEDE quais falham)
 [GD1c] O CONTROLE  "quantos clientes eu tenho?" -> 0 de 1, e o caminho que le o
                    documento NAO roda (CLAUDE.md §9.2)
 [GD1d] O PAR       `explicit=False` continua funcionando por palavra para os OUTROS
                    chamadores — a funcao nao virou `return True`
```

⚠️ **O teste chama o MOTOR** (CLAUDE.md §9.4): `_arun` da tool REAL, com o
provider DUBLADO capturando o que a tool pede, e
`_maybe_attach_official_policy_document_evidence` de producao no controle.
Nenhum regex sobre o codigo-fonte decide nada aqui.

⛔ SEGURANCA: `SEM_REDE=1`, sem banco, sem API, sem PII (o corpus ja tem
`[CPF]`/`[CNPJ]`/`[NOME]` no lugar dos dados).

Rodar (de dentro de `backend/`):
    PYTHONIOENCODING=utf-8 python tests/test_o_documento_e_lido_sempre_que_a_pergunta_e_de_apolice.py
    ... --so GD1c   ·   ... --medir   ·   ... --mutar [M-D1a]
"""
from __future__ import annotations

import asyncio
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import types

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # .../backend
TESTES = os.path.join(RAIZ, "tests")
CORPUS = os.path.join(TESTES, "corpus", "perguntas_do_chat", "2026-09-09_10.json")
#: ⚠️ O harness da trava de rede e o do M-B1, nao o do M-A2: este guarda roda
#: `asyncio.run`, e no Windows o `ProactorEventLoop` abre um socketpair de
#: LOOPBACK para o proprio pipe. A trava do M-A2 recusa qualquer `connect` e
#: derruba o laco antes da primeira assercao; a do M-B1 libera 127.0.0.1 e
#: continua recusando a rede de verdade (divergencia D-B-g do BLOCO B).
HARNESS = os.path.join(TESTES, "test_vencida_nunca_vira_opcao.py")

if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
os.environ["SEM_REDE"] = "1"
os.environ.setdefault("POLICY_INTELLIGENCE_V2", "true")
os.environ.setdefault("BACKEND_INTERNAL_API_KEY", "chave-de-teste-sem-rede")

PASS = 0
FAIL = 0
MEDIDAS: dict = {}

#: ⛔ SINTETICO. O locator real nunca entra num arquivo de teste.
LOCATOR = {"provider": "infocap", "codfil": "1", "nosnum": "999001"}

#: 📊 As perguntas que a palavra-chave NAO pegava, medidas em 14/09/2026.
#:    Elas sao o motivo de o gatilho ter deixado de ser por texto.
CEGAS_PARA_A_PALAVRA = ("q1", "q2", "q3")


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
        _p("  [FALHOU] %s" % nome + ("\n         %s" % str(detalhe)[:700] if detalhe else ""))
    return bool(cond)


def medir(chave, valor):
    MEDIDAS[chave] = valor
    return valor


def _carregar(nome, caminho):
    spec = importlib.util.spec_from_file_location(nome, caminho)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nome] = mod
    spec.loader.exec_module(mod)   # type: ignore[union-attr]
    return mod


_HA = _carregar("_harness_md1", HARNESS)


def corpus():
    return json.load(io.open(CORPUS, encoding="utf-8"))


# ===========================================================================
# O DUBLE — so a VIAGEM e falsa; a tool, a porta e o gatilho sao os de producao
# ===========================================================================
def _stubar_o_banco():
    """`create_async_supabase_client` dublado — a tool nao abre conexao aqui.

    ⚠️ O modulo REAL e preservado e so a funcao e trocada (o mesmo cuidado do
    M-B3): substituir o modulo inteiro derruba o gate rodado sozinho.
    """
    try:
        import app.core.database as banco
    except Exception:  # noqa: BLE001
        banco = types.ModuleType("app.core.database")
        sys.modules["app.core.database"] = banco

    async def _sem_banco(*a, **k):
        return None

    banco.create_async_supabase_client = _sem_banco        # type: ignore[attr-defined]
    if not hasattr(banco, "get_supabase_client"):
        banco.get_supabase_client = lambda *a, **k: None   # type: ignore[attr-defined]


def _pack_minimo():
    return {
        "coverage_sections": [{"label": "Cobertura de teste", "amount": "R$ 1.000,00"}],
        "policy_status": "ativo",
        "valid_from": "01/01/2026",
        "valid_to": "01/01/2027",
        "policy_locator": dict(LOCATOR),
    }


class _ProviderQueAnota:
    """O provider que ANOTA o que a tool pediu. Nada mais e falsificado."""

    provider_key = "infocap"

    def __init__(self):
        self.pedidos = []

    async def lookup(self, **kw):
        self.pedidos.append(("lookup", kw.get("document_evidence_requested")))
        return {
            "ok": True, "status": "found", "documents_count": 1,
            "selected": {"policy_number": "900000000000001", "insurer_key": "HDI",
                         "product": "RESI", "valid_from": "01/01/2026",
                         "valid_to": "01/01/2027", "policy_status": "ativo"},
            "matches": [{"policy_number": "900000000000001"}],
            "policy_evidence_pack": _pack_minimo(),
        }

    async def detail(self, **kw):
        self.pedidos.append(("detail", kw.get("document_evidence_requested")))
        return {"ok": True, "status": "found",
                "selected": {"policy_number": "900000000000001", "product": "RESI"},
                "policy_evidence_pack": _pack_minimo()}

    async def vehicle(self, **kw):
        return {"ok": False}


def chamar_a_tool(user_query, *, papel="core", policy_ref=None):
    """A TOOL REAL, com a porta apontada para o provider que anota."""
    _stubar_o_banco()
    from app.agents.tools import infocap_tool as tool_mod
    from app.providers import policy_data_provider as porta

    provider = _ProviderQueAnota()
    original = porta.get_policy_data_provider
    porta.get_policy_data_provider = lambda *a, **k: provider   # type: ignore[assignment]
    try:
        ferramenta = tool_mod.InfocapPolicyLookupTool(
            company_id="tenant-de-teste", agent_role=papel)
        asyncio.run(ferramenta._arun(
            document=(None if policy_ref else "[CPF]"),
            policy_ref=policy_ref,
            user_query=user_query,
        ))
    finally:
        porta.get_policy_data_provider = original   # type: ignore[assignment]
    return provider.pedidos


# ===========================================================================
# [GD1a] AS 7 — pela tool, o documento e pedido em 7 de 7
# ===========================================================================
def gate_GD1a():
    _p("\n[GD1a] AS 7 -- as perguntas REAIS do chat, pela TOOL, pedem o documento")
    perguntas = corpus()["perguntas"]
    pediram = []
    for pergunta in perguntas:
        pedidos = chamar_a_tool(pergunta["texto"])
        pedido = any(valor is True for _origem, valor in pedidos)
        if pedido:
            pediram.append(pergunta["id"])
        check("[GD1a] %s (%s) -> leitura documental PEDIDA"
              % (pergunta["id"], (pergunta.get("contexto") or "")[:46]), pedido, pedidos)
    medir("perguntas_que_pedem_o_documento", "%d/%d" % (len(pediram), len(perguntas)))
    check("[GD1a] 🔴 7 de 7 (o acervo media 4 de 7 pela palavra-chave)",
          len(pediram) == len(perguntas) == 7, pediram)

    # 🔴 O OUTRO caminho da tool: quando ja existe `policy_ref`, quem e chamado
    #    e `detail` — e ele tambem tem de pedir o documento.
    pedidos = chamar_a_tool("me detalhe essa apolice", policy_ref="infocap:1:999001")
    medir("caminho_do_detail", pedidos)
    check("[GD1a] 🔴 e o caminho do `detail` (policy_ref) tambem pede",
          pedidos and pedidos[0][0] == "detail" and pedidos[0][1] is True, pedidos)

    # 🔴 E vale para TODOS os papeis: o segurado nao recebe menos apolice que o
    #    corretor — o que muda e a REDACAO (§6.3).
    for papel in ("core", "attendance", "insured_external"):
        pedidos = chamar_a_tool("[CPF]", papel=papel)
        check("[GD1a] papel %r tambem pede o documento" % papel,
              any(valor is True for _o, valor in pedidos), (papel, pedidos))


# ===========================================================================
# [GD1b] O ANTES — quantas a PALAVRA-CHAVE pegava, e quais nao
# ===========================================================================
def gate_GD1b():
    _p("\n[GD1b] O ANTES -- a mesma pergunta, pela palavra-chave que decidia ate 14/09")
    from app.services.policy_document_evidence_service import (
        policy_document_evidence_requested,
    )

    perguntas = corpus()["perguntas"]
    por_palavra = {q["id"]: policy_document_evidence_requested(q["texto"], False)
                   for q in perguntas}
    cegas = sorted(qid for qid, valor in por_palavra.items() if not valor)
    medir("perguntas_pela_palavra_chave", "%d/%d" % (sum(por_palavra.values()), len(perguntas)))
    medir("perguntas_cegas_para_a_palavra", cegas)
    check("[GD1b] 📊 a palavra-chave pega 4 de 7 — nao 7", sum(por_palavra.values()) == 4,
          por_palavra)
    check("[GD1b] 🔴 e as cegas sao q1 (so o CPF), q2 (pedia FRANQUIA) e q3 (carro reserva)",
          tuple(cegas) == CEGAS_PARA_A_PALAVRA, cegas)

    # 🔴 O ELO: a MESMA pergunta que a palavra nao pega e pedida pela TOOL.
    #    Duas medicoes certas nao fazem uma causa certa — esta e a terceira.
    for qid in CEGAS_PARA_A_PALAVRA:
        texto = next(q["texto"] for q in perguntas if q["id"] == qid)
        pedidos = chamar_a_tool(texto)
        check("[GD1b] 🔴 O ELO: %s — False pela palavra, True pelo DESTINO" % qid,
              por_palavra[qid] is False and any(v is True for _o, v in pedidos),
              (por_palavra[qid], pedidos))


# ===========================================================================
# [GD1c] O CONTROLE — a pergunta que NAO e de apolice nao le documento
# ===========================================================================
def gate_GD1c():
    _p("\n[GD1c] O CONTROLE -- 'quantos clientes eu tenho?' nao le o documento")
    from app.services.policy_document_evidence_service import (
        policy_document_evidence_requested,
    )

    controle = corpus()["controle"][0]
    check("[GD1c] 🔴 a pergunta de controle NAO casa palavra nenhuma",
          policy_document_evidence_requested(controle["texto"], False) is False,
          controle["texto"])

    # 🔴 E o caminho de producao que LE o documento nao roda. Isto e o MOTOR:
    #    `_maybe_attach_official_policy_document_evidence`, o unico ponto do
    #    sistema que anexa evidencia documental a um pack.
    from app.api.infocap_connector import (
        _maybe_attach_official_policy_document_evidence as ANEXAR,
    )

    def _payload(texto, explicit):
        return types.SimpleNamespace(
            user_query=texto, document_evidence_requested=explicit,
            force_document_evidence_refresh=False)

    def _pack():
        return {"policy_locator": dict(LOCATOR),
                "official_document_source_available": True}

    async def _rodar(texto, explicit):
        return await ANEXAR(
            pack=_pack(), detail_envelope={}, payload=_payload(texto, explicit),
            company_id="tenant-de-teste", token="", auth_cookies=None)

    sem_pedido = asyncio.run(_rodar(controle["texto"], False))
    medir("controle_leu_documento", "official_policy_document_evidence" in sem_pedido)
    check("[GD1c] 🔴 0 de 1: o pack volta SEM leitura documental nenhuma",
          "official_policy_document_evidence" not in sem_pedido, sorted(sem_pedido))

    # 🔴 O PAR que da direito a conclusao (CLAUDE.md §9.5): com o pedido do
    #    DESTINO, o MESMO caminho passa da porteira. Sem este par, "nao leu"
    #    tanto poderia ser o gatilho quanto um `return` mais acima.
    com_pedido = asyncio.run(_rodar(controle["texto"], True))
    check("[GD1c] 🔴 PAR: com o pedido do destino, o MESMO caminho segue adiante",
          "official_policy_document_evidence" in com_pedido, sorted(com_pedido))
    check("[GD1c] e sem candidato de documento ele diz `source_unavailable` — "
          "nunca inventa cobertura",
          (com_pedido.get("official_policy_document_evidence") or {}).get("document_status")
          == "source_unavailable", com_pedido.get("official_policy_document_evidence"))


# ===========================================================================
# [GD1d] O PAR — a funcao por palavra CONTINUA existindo, e continua discriminando
# ===========================================================================
def gate_GD1d():
    _p("\n[GD1d] O PAR -- `explicit=False` continua por PALAVRA, para os outros chamadores")
    from app.services.policy_document_evidence_service import (
        policy_document_evidence_requested,
    )

    # ⚠️ A funcao NAO virou `return True`: outros chamadores dependem dela.
    check("[GD1d] PAR-A: 'qual a franquia dessa apolice?' -> True",
          policy_document_evidence_requested("qual a franquia dessa apolice?", False) is True)
    check("[GD1d] PAR-B: 'qual e a vigencia da apolice?' -> False (pergunta operacional)",
          policy_document_evidence_requested("qual e a vigencia da apolice?", False) is False)
    check("[GD1d] PAR-C: 'quantos clientes eu tenho?' -> False",
          policy_document_evidence_requested("quantos clientes eu tenho?", False) is False)
    check("[GD1d] 🔴 e `explicit=True` vence sempre — e o caminho do DESTINO",
          policy_document_evidence_requested("quantos clientes eu tenho?", True) is True)

    # 📊 O que torna "ler sempre" barato: a chave do cache documental.
    from app.services.policy_document_evidence_service import policy_document_cache_key

    a = policy_document_cache_key("empresa-1", LOCATOR, "hash-1", "conexao-1")
    b = policy_document_cache_key("empresa-1", LOCATOR, "hash-1", "conexao-1")
    c = policy_document_cache_key("empresa-2", LOCATOR, "hash-1", "conexao-1")
    check("[GD1d] 🔴 a segunda leitura da MESMA apolice cai na MESMA chave de cache "
          "(e por isso 'ler sempre' nao custa uma consulta a mais)", a == b, (a, b))
    check("[GD1d] ⛔ e a chave de outra corretora e OUTRA", a != c, (a, c))


GATES = {
    "GD1a": gate_GD1a,
    "GD1b": gate_GD1b,
    "GD1c": gate_GD1c,
    "GD1d": gate_GD1d,
}


# ===========================================================================
# AS MUTACOES — por COPIA, em SUBPROCESSO. A arvore precisa estar parada.
# ===========================================================================
MUTACOES = [
    # (a) o gatilho por PALAVRA-CHAVE de volta na tool -> q1/q2/q3 ficam False.
    ("M-D1a", "app/agents/tools/infocap_tool.py",
     "                policy_number=policy_number or None,\n"
     "                user_query=user_query,\n"
     "                document_evidence_requested=_LER_SEMPRE_O_DOCUMENTO,",
     "                policy_number=policy_number or None,\n"
     "                user_query=user_query,\n"
     "                document_evidence_requested=bool(document_evidence_requested),",
     "GD1a"),
    # (b) `return True` no topo de `policy_document_evidence_requested` -> o
    #     CONTROLE fica True, e o guarda que exige "7 de 7" passaria mentindo.
    ("M-D1b", "app/services/policy_document_evidence_service.py",
     '    if explicit:\n        return True\n    normalized = _strip_accents(question or "")',
     '    if explicit:\n        return True\n    return True\n'
     '    normalized = _strip_accents(question or "")',
     "GD1c"),
    # (c) o caminho do `detail` (policy_ref) ficando de fora -> a pergunta que
    #     chega com a apolice ja escolhida volta a nao ler o PDF.
    ("M-D1c", "app/agents/tools/infocap_tool.py",
     "                    policy_ref=str(policy_ref),\n"
     "                    user_query=user_query,\n"
     "                    document_evidence_requested=_LER_SEMPRE_O_DOCUMENTO,",
     "                    policy_ref=str(policy_ref),\n"
     "                    user_query=user_query,\n"
     "                    document_evidence_requested=False,",
     "GD1a"),
]


def _rodar(gate):
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
        caminho = os.path.normpath(os.path.join(RAIZ, relativo))
        original = io.open(caminho, encoding="utf-8").read()
        if de not in original:
            _p("  [FALHOU] %s: a ancora nao existe em %s -- mutacao NAO aplicada "
               "NAO e mutacao passada" % (mid, relativo))
            verdes += 1
            continue
        base = _rodar(gate)
        backup = tempfile.NamedTemporaryFile(delete=False, suffix=".bak-0011d1").name
        shutil.copyfile(caminho, backup)
        try:
            io.open(caminho, "w", encoding="utf-8", newline="\n").write(
                original.replace(de, para, 1))
            r = _rodar(gate)
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
        _p("  M-D1 -- O DOCUMENTO E LIDO SEMPRE QUE A PERGUNTA E DE APOLICE")
        _p("=" * 78)
    _HA._bloquear_a_rede()
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
        _HA._devolver_a_rede()

    for chave, valor in sorted(MEDIDAS.items()):
        print("MEDIDA %s %s" % (chave, valor))
    if not calado:
        _p("\n" + "=" * 78)
        _p("  %d assercoes verdes - %d vermelhas" % (PASS, FAIL))
        _p("=" * 78)
    return 1 if FAIL else 0


def test_o_documento_e_lido_sempre_que_a_pergunta_e_de_apolice():
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
