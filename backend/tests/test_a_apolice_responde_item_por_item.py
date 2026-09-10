# -*- coding: utf-8 -*-
r"""🔴 A apólice responde ITEM POR ITEM — cobertura, franquia e prêmio de cada uma.

📊 **Medido em 09-10/09/2026**, no chat do painel da Resulta Seguros (agente
core, `channel='web'`), com a atendente da corretora ao lado do Founder:

```
corretor  "veja a apolice do segurado <CNPJ> quero saber as franquias
           das coberturas contratadas"
agente    "a InfoCap/documento não me retornou a lista completa de coberturas
           com suas franquias individuais"          ← 15 coberturas existiam
corretor  "Preciso das coberturas especificas contratadas"
agente    "A única cobertura com valor e franquia explícitos que veio da fonte
           foi: Danos Elétricos"                     ← 1 de 15
corretor  "queroo que traga o detalhamento item a item de cada cobertura...
           Vc precisa trazer isso de algum jeito"
agente    "a InfoCap não trouxe o detalhamento item a item (...) ela retornou
           apenas o Limite Máximo de Garantia (LMG) global"  ← 6 existiam
```

🔴 **A fonte tinha tudo, e ninguém tinha perguntado a ela.** 📊 Medido ao vivo
na CorpAPI da Resulta em 10/09/2026 (somente leitura):

```
GET /documento?nosnum=&codfil=   prêmios e parcelas — NENHUMA cobertura
GET /itens?nosnum=&codfil=       itens[].garantias[] = garantia · impseg (LMI)
                                 · premio · taxa · valfran · franquia
                                 15 garantias no condomínio Allianz
                                  6 garantias no residencial HDI
```

O conector lia só o `/documento`. `_COVERAGE_LIST_KEYS` já continha `garantias`
— a lista simplesmente **nunca chegava lá**, porque mora em outro endpoint.

⚠️ E o corolário do §9.4 do CLAUDE.md: este guarda chama o **MOTOR**
(`_build_evidence_pack`, `_normalize_coverage_items`, `_build_llm_briefing`)
sobre a resposta **REAL** da CorpAPI gravada em fixture (mascarada), nunca um
regex reimplementado sobre o mesmo texto.
"""
from __future__ import annotations

import asyncio
import io
import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.environ.setdefault("POLICY_INTELLIGENCE_V2", "true")

PASS = 0
FAIL = 0
FALHAS = []


def check(nome, condicao, detalhe=None):
    global PASS, FAIL
    if condicao:
        PASS += 1
        print(f"  [ok] {nome}")
    else:
        FAIL += 1
        FALHAS.append((nome, detalhe))
        print(f"  [X] {nome}" + (f": {detalhe}" if detalhe else ""))


FIXTURE = os.path.join(RAIZ, "tests", "fixtures", "infocap_itens_garantias_masked.json")
ITENS_REAIS = json.load(io.open(FIXTURE, encoding="utf-8"))["itens"]

# `/documento` real da mesma apólice (só os campos que o pack usa) — mascarado.
DOCUMENTO_REAL = {
    "codfil": 1,
    "nosnum": 999001,
    "numapo": "900000000000001",
    "seguradora": "ALLI",
    "ramo": "COND",
    "inivig": "25/08/2026",
    "fimvig": "25/08/2027",
    "cancelado": "F",
    "preliq": 24960.60,
    "preadi": 0.0,
    "preiof": 1842.09,
    "pretot": 26802.69,
    "prepri": 4467.12,
    "numpar": 6,
    "forma_pag": "Boleto Bancário",
    "tabela_itens": "PACOTE",
}

from app.api import infocap_connector as CN  # noqa: E402
from app.agents.tools.infocap_tool import InfocapPolicyLookupTool  # noqa: E402
from app.services.policy_answer_composer import compose_policy_answer_with_meta  # noqa: E402
from app.services.policy_document_evidence_service import build_document_plain_text  # noqa: E402

PERGUNTA = "quais as coberturas contratadas, com franquia e premio de cada uma?"


# ---------------------------------------------------------------------------
print("\n[1] A cobertura vem ITEM A ITEM, com limite, franquia e prêmio")
# ---------------------------------------------------------------------------
pack = CN._build_evidence_pack(
    DOCUMENTO_REAL, None, None, True, envelope={"documento": [DOCUMENTO_REAL]}, items=ITENS_REAIS
)
secoes = pack.get("coverage_sections") or []

check("todas as 15 coberturas da fonte chegam ao pack (não 1, não 0)",
      len(secoes) == 15, f"vieram {len(secoes)}")
check("nenhuma cobertura chega sem rótulo humano",
      all(str(s.get("label") or "").strip() for s in secoes))
check("o LIMITE (impseg) vem em cada cobertura, formatado em R$",
      sum(1 for s in secoes if str(s.get("amount") or "").startswith("R$")) == 15,
      [s.get("amount") for s in secoes])
check("a FRANQUIA vem por cobertura — e as 7 que têm franquia real aparecem",
      sum(1 for s in secoes if s.get("deductible") and s.get("deductible") != "sem franquia") == 7,
      [s.get("deductible") for s in secoes])
check("o PRÊMIO vem por cobertura",
      sum(1 for s in secoes if str(s.get("premium") or "").startswith("R$")) == 15)

danos = next((s for s in secoes if "DANOS EL" in str(s.get("label"))), {})
check("Danos Elétricos: limite R$ 100.000,00 · franquia '20 - R$ 4.000,00' · prêmio R$ 4.803,67",
      danos.get("amount") == "R$ 100.000,00"
      and danos.get("deductible") == "20 - R$ 4.000,00"
      and danos.get("premium") == "R$ 4.803,67",
      danos)

check("a fonte da cobertura fica escrita (é /itens.garantias, não o /documento)",
      pack.get("coverage_source") == "infocap:/itens.garantias", pack.get("coverage_source"))
check("com cobertura estruturada, o pack PARA de dizer que ela está ausente",
      pack.get("structured_coverage_absent") is False
      and pack.get("coverage_evidence_status") == "structured_coverage_available")
check("o prêmio da apólice vem com nome humano (preliq não é 'o prêmio')",
      (pack.get("premium_summary") or {}).get("total_premium", {}).get("value") == "R$ 26.802,69"
      and (pack.get("premium_summary") or {}).get("net_premium", {}).get("label") == "Prêmio líquido")

# 🔴 E o guarda de dentro: o mesmo /documento SEM os itens não pode inventar
# cobertura — a ausência continua sendo ausência (linha de CONTROLE, §9.2).
pack_sem_itens = CN._build_evidence_pack(
    DOCUMENTO_REAL, None, None, True, envelope={"documento": [DOCUMENTO_REAL]}, items=[]
)
check("CONTROLE: sem /itens, o pack continua honesto (zero cobertura, nada inventado)",
      not (pack_sem_itens.get("coverage_sections") or [])
      and pack_sem_itens.get("structured_coverage_absent") is True)


# ---------------------------------------------------------------------------
print("\n[2] O briefing que chega à LLM lista as 15, com franquia e prêmio")
# ---------------------------------------------------------------------------
resultado = {
    "ok": True,
    "status": "found",
    "selected": {"policy_number": "900000000000001", "insurer_key": "alli", "product": "cond",
                 "valid_from": "25/08/2026", "valid_to": "25/08/2027"},
    "policy_evidence_pack": pack,
}
meta = compose_policy_answer_with_meta(question=PERGUNTA, result=resultado)
briefing = InfocapPolicyLookupTool._build_llm_briefing(resultado, meta, PERGUNTA)

check("o briefing traz o bloco de coberturas item a item",
      "coberturas_item_a_item" in briefing)
# `all()` sobre lista vazia é True: as duas checagens abaixo exigem a CONTAGEM
# antes do conteúdo, senão um pack vazio passaria por elas (§9.3 do CLAUDE.md).
check("as 15 coberturas aparecem NOMEADAS no briefing",
      len(secoes) == 15 and all(str(s.get("label")) in briefing for s in secoes),
      [s.get("label") for s in secoes if str(s.get("label")) not in briefing])
franquias_reais = [s["deductible"] for s in secoes
                   if s.get("deductible") and s["deductible"] != "sem franquia"]
check("cada franquia real aparece no briefing (e há 7 delas)",
      len(franquias_reais) == 7 and all(str(f) in briefing for f in franquias_reais),
      franquias_reais)
check("o prêmio total da apólice aparece no briefing", "R$ 26.802,69" in briefing)
check("a instrução manda LISTAR TODAS — não resumir a uma",
      "LISTE TODAS" in briefing)

texto_composer = str(meta.get("text") or "")
check("o rascunho seguro (composer) também lista cobertura com franquia e prêmio",
      "DANOS ELÉTRICOS" in texto_composer and "franquia 20 - R$ 4.000,00" in texto_composer,
      texto_composer[:400])


# ---------------------------------------------------------------------------
print("\n[3] Quando existe PDF da apólice, ele vira TEXTO — e chega ao briefing")
# ---------------------------------------------------------------------------
PAGINAS = [
    {"page_number": 1, "content": "APOLICE DE SEGURO CONDOMINIO\nCondicoes Particulares\n"
                                  "Consulte as condicoes gerais em https://exemplo.invalido/cg.pdf"},
    {"page_number": 2, "content": "Clausula Particular de Patrimonio Tombado.\n"
                                  "Franquia de vendaval: 20% dos prejuizos, minimo R$ 2.500,00.\n"
                                  "CNPJ do segurado 11.222.333/0001-44"},
]
texto = build_document_plain_text(PAGINAS)
check("o texto integral do PDF é montado página a página",
      "[pagina 1]" in texto and "[pagina 2]" in texto, texto[:200])
check("a franquia escrita em PROSA (que nenhuma tabela captura) sobrevive no texto",
      "minimo R$ 2.500,00" in texto)
check("URL do documento nunca vaza no texto",
      "https://" not in texto and "[url-redigida]" in texto)
check("CNPJ do segurado é redigido no texto do documento",
      "11.222.333/0001-44" not in texto and "[documento-redigido]" in texto)

pack_com_doc = dict(pack)
pack_com_doc["official_policy_document_evidence"] = {
    "ok": True, "document_status": "evidence_ready", "document_text": texto, "evidence_items": [],
}
resultado_doc = {**resultado, "policy_evidence_pack": pack_com_doc}
meta_doc = compose_policy_answer_with_meta(question=PERGUNTA, result=resultado_doc)
briefing_doc = InfocapPolicyLookupTool._build_llm_briefing(resultado_doc, meta_doc, PERGUNTA)
check("o TEXTO da apólice oficial chega ao briefing da LLM",
      "TEXTO DA APOLICE OFICIAL" in briefing_doc and "minimo R$ 2.500,00" in briefing_doc)
check("CONTROLE: sem documento, o briefing não anuncia texto de apólice que não tem",
      "TEXTO DA APOLICE OFICIAL" not in briefing)

briefing_cliente = InfocapPolicyLookupTool._build_llm_briefing(
    resultado_doc, meta_doc, PERGUNTA, client_facing=True
)
check("o SEGURADO no WhatsApp não recebe o documento inteiro despejado",
      "TEXTO DA APOLICE OFICIAL" not in briefing_cliente)


# ---------------------------------------------------------------------------
print("\n[4] Corretora A nunca vê apólice da corretora B")
# ---------------------------------------------------------------------------
CORRETORA_A = "aaaaaaaa-0000-0000-0000-00000000000a"
CORRETORA_B = "bbbbbbbb-0000-0000-0000-00000000000b"

ITENS_DA_B = [{"item": 1, "garantias": [
    {"garantia": "COBERTURA EXCLUSIVA DA CORRETORA B", "impseg": 999.0, "premio": 9.0, "franquia": "0"}
]}]


class _Resp:
    def __init__(self, payload):
        self.status_code = 200
        self._payload = payload

    def json(self):
        return self._payload


class _ClienteFalso:
    """Dublê do httpx: devolve as garantias que a credencial DAQUELA corretora vê."""

    def __init__(self, payload):
        self.payload = payload
        self.chamadas = 0

    async def get(self, path, params=None, headers=None):
        self.chamadas += 1
        return _Resp(self.payload)


class _RedisFalso:
    def __init__(self):
        self.dados = {}

    async def get(self, chave):
        return self.dados.get(chave)

    async def setex(self, chave, ttl, valor):
        self.dados[chave] = valor


redis_falso = _RedisFalso()
import app.core.redis as REDIS_MOD  # noqa: E402

_original = REDIS_MOD.get_async_redis_client


async def _fake_redis():
    return redis_falso


REDIS_MOD.get_async_redis_client = _fake_redis
try:
    cliente_a = _ClienteFalso({"itens": ITENS_REAIS})
    itens_a = asyncio.run(CN._fetch_policy_items(
        cliente_a, {}, itens_path="/itens", codfil=1, nosnum=999001, company_id=CORRETORA_A))
    cliente_b = _ClienteFalso({"itens": ITENS_DA_B})
    itens_b = asyncio.run(CN._fetch_policy_items(
        cliente_b, {}, itens_path="/itens", codfil=1, nosnum=999001, company_id=CORRETORA_B))

    rotulos_b = [g.get("garantia") for i in itens_b for g in i.get("garantias") or []]
    check("a corretora B recebe SÓ o que a credencial dela devolveu",
          rotulos_b == ["COBERTURA EXCLUSIVA DA CORRETORA B"], rotulos_b)
    check("o cache da A (mesmo codfil/nosnum) NÃO responde pela B",
          cliente_b.chamadas == 1, f"chamadas da B ao provider: {cliente_b.chamadas}")
    check("nenhuma cobertura da A atravessa para a B",
          not any("INCÊNDIO" in str(r) for r in rotulos_b))

    # CONTROLE: o cache existe mesmo — a MESMA corretora não repete a chamada.
    cliente_a2 = _ClienteFalso({"itens": []})
    itens_a2 = asyncio.run(CN._fetch_policy_items(
        cliente_a2, {}, itens_path="/itens", codfil=1, nosnum=999001, company_id=CORRETORA_A))
    check("CONTROLE: a mesma corretora reaproveita o cache (a trava é o tenant, não a falta de cache)",
          cliente_a2.chamadas == 0 and len(itens_a2) == len(itens_a))
finally:
    REDIS_MOD.get_async_redis_client = _original


# ---------------------------------------------------------------------------
print("\n[5] A instrução do modelo diz o que a ferramenta faz — e o que é proibido")
# ---------------------------------------------------------------------------
from app.core import prompts as PROMPTS  # noqa: E402

fonte_prompt = io.open(os.path.join(RAIZ, "app", "core", "prompts.py"), encoding="utf-8").read()
linha = next((l for l in fonte_prompt.splitlines() if "infocap_policy_lookup" in l and "Coberturas" in l), "")

check("a instrução cita COBERTURA, FRANQUIA e PRÊMIO na mesma regra",
      all(termo in linha.lower() for termo in ("cobertura", "franquia", "prêmio")), linha[:200])
check("a instrução proíbe dizer 'não consigo buscar' antes de chamar a ferramenta",
      "não consigo buscar essa informação" in linha and "PROIBIDO" in linha, linha[:200])
check("a instrução manda listar TODAS as coberturas, não a primeira",
      "todas as N" in linha, linha[:200])

descricao = InfocapPolicyLookupTool.model_fields["description"].default if hasattr(
    InfocapPolicyLookupTool, "model_fields") else InfocapPolicyLookupTool.description
descricao = str(descricao)
check("a própria descrição da ferramenta anuncia cobertura item a item, franquia e prêmio",
      "COBERTURAS ITEM A ITEM" in descricao and "FRANQUIA" in descricao and "PREMIO" in descricao,
      descricao[:200])


print(f"\n{'='*70}\nPASS={PASS}  FAIL={FAIL}")
for nome, detalhe in FALHAS:
    print(f"  FALHOU: {nome} -> {detalhe}")
sys.exit(1 if FAIL else 0)
