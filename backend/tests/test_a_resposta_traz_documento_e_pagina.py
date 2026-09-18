# -*- coding: utf-8 -*-
r"""🔴 M-B2 · A RESPOSTA TRAZ DOCUMENTO E PÁGINA — sobre as 30 perguntas REAIS.

SPEC-EXTRA-001.5 · BLOCO B, GATE B ① e ②. O acervo é `tests/corpus/
perguntas_de_cobertura_2026-09-17.json`: 30 perguntas de gente, tiradas de
`public.messages` em 17/09/2026, com a PII removida pelo redator da casa.

🔴 **PELO MOTOR, NÃO PELO REGEX** (CLAUDE.md §9.4). O que roda aqui é
`compose_policy_answer_with_meta` — o mesmo ponto que `infocap_tool.py:722`
chama no chat do corretor e no WhatsApp. Um teste que chamasse
`responder_cobertura` direto provaria que a Skill funciona e **não** que alguém
a usa; foi exatamente esse o defeito das 72 asserções verdes de 21/08/2026.

O que se afirma:

```
① toda pergunta do acervo devolve UM dos cinco estados (ou a falha declarada)
② toda resposta com `origem='base'` traz DOCUMENTO e PÁGINA — no campo e no TEXTO
③ a linha de CONTROLE: "quantas parcelas faltam?" NÃO consulta a base
   (contado por chamadas de tabela, não lido no texto da resposta)
④ e o CONTROLE do controle: as perguntas do acervo CONSULTARAM a base — senão
   ③ passaria por vácuo
```

⚠️ **DIVERGÊNCIA DECLARADA, não silenciada** (CLAUDE.md §11). A SPEC escreve
GATE B ① como *"todo estado != `nao_sabemos_ainda` traz documento e página"*.
Medido aqui: o **fallback** de §6.4 (`origem='regra_generica'`) devolve
`coberto` e **não tem** documento nem página — ele é regra de mercado escrita em
código, não linha de condição geral. Exigir fonte dele seria exigir que ele
inventasse uma.

A regra que este guarda impõe, e que é a que protege o segurado:

```
origem='base'           -> documento e página OBRIGATÓRIOS, no campo e no texto
origem='regra_generica' -> fonte VAZIA, e o texto TEM de dizer que é padrão de
                           mercado e NÃO o contrato dele  (asserção [1b])
```

Um fallback que saísse sem essa ressalva seria o "sim" errado de volta, com
outro nome.
"""
from __future__ import annotations

import json
import re
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "tests"))

from base_de_planos_em_memoria import BaseEmMemoria  # noqa: E402

from app.services.policy_answer_composer import (  # noqa: E402
    compose_policy_answer_with_meta,
)
from app.services.skills.cobertura_e_assistencia import ESTADOS, FALHA  # noqa: E402

OK = FAIL = 0


def checar(cond, rotulo, detalhe=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok    {rotulo}")
    else:
        FAIL += 1
        print(f"  FALHA \U0001F534 {rotulo}" + (f"\n        {detalhe}" if detalhe else ""))


CORPUS = os.path.join(RAIZ, "tests", "corpus", "perguntas_de_cobertura_2026-09-17.json")
with open(CORPUS, "r", encoding="utf-8") as fh:
    ACERVO = json.load(fh)
PERGUNTAS = ACERVO["perguntas"]


def _pack(ramo: str, produto: str, plano: str, nivel: int) -> dict:
    """Um evidence pack sintético — a FORMA é a de `_sample_pack` da SPEC-016."""
    return {
        "source": "infocap",
        "policy_ref": "999001",
        "insurer_detected": "hdi",
        "product_detected": produto,
        "line_kind_detected": ramo,
        "policy_status": "ativa",
        "active_now": True,
        "valid_from": "2026-01-01",
        "valid_to": "2027-01-01",
        "coverage_sections": [{"label": "Assistência 24h", "amount": None}],
        "structured_coverage_available": True,
        "structured_coverage_absent": False,
        "installments": [],
        "limitations": [],
        # a vaga do BLOCO C: a identificação do plano contratado
        "assistance_plan": {"plano": plano, "nivel": nivel, "estado": "contratado"},
    }


def _result(pack: dict) -> dict:
    return {
        "ok": True, "status": "found",
        "selected": {
            "insurer_key": pack["insurer_detected"], "product": pack["product_detected"],
            "policy_number": "1234567890", "numapo": "1234567890",
            "holder_name": "Cliente Sintetico", "policy_status": "ativa",
            "active_now": True, "valid_from": "2026-01-01", "valid_to": "2027-01-01",
        },
        "policy_evidence_pack": pack,
    }


#: 🔴 Uma base com linha publicada para PARTE dos serviços, de propósito. Se
#: todos tivessem linha, `nao_sabemos_ainda` nunca apareceria e a asserção ②
#: nunca seria exercida no ramo que interessa. Se nenhum tivesse, ② passaria
#: por vácuo — nenhum estado != nao_sabemos_ainda para conferir.
db = BaseEmMemoria()
AUTO = db.plano(insurer_key="hdi", ramo="auto", produto="Auto Perfil",
                plano="Essencial", nivel=1, documento_id="doc-hdi-auto", pagina=9)
AUTO_TOP = db.plano(insurer_key="hdi", ramo="auto", produto="Auto Perfil",
                    plano="Completo", nivel=2, documento_id="doc-hdi-auto", pagina=9)
RESI = db.plano(insurer_key="hdi", ramo="residencial", produto="Residencial Total",
                plano="Essencial", nivel=1, documento_id="doc-hdi-resi", pagina=7)
db.servico(AUTO, "carro_reserva", "nao", documento_id="doc-hdi-auto", pagina=23)
db.servico(AUTO_TOP, "carro_reserva", "sim", documento_id="doc-hdi-auto", pagina=24,
           limite_valor=7, limite_unidade="dias")
db.servico(AUTO, "guincho", "sim", documento_id="doc-hdi-auto", pagina=25,
           limite_valor=200, limite_unidade="km")
db.servico(AUTO, "vidros", "condicionado", documento_id="doc-hdi-auto", pagina=26,
           condicao="só com a cobertura de vidros contratada")
db.servico(AUTO, "granizo", "sim", documento_id="doc-hdi-auto", pagina=31)
db.servico(RESI, "eletricista", "sim", documento_id="doc-hdi-resi", pagina=12)
# 🔴 `taxi`, `chaveiro` e `encanador` NÃO têm linha: são o lado
# `nao_sabemos_ainda` da medição, e é o que impede a asserção ① de ser trivial.

RAMO_DA_CATEGORIA = {
    "carro_reserva": ("auto", "Auto Perfil", "Essencial", 1),
    "granizo": ("auto", "Auto Perfil", "Essencial", 1),
    "chaveiro_e_taxi": ("auto", "Auto Perfil", "Essencial", 1),
    "vidros": ("auto", "Auto Perfil", "Essencial", 1),
    "guincho": ("auto", "Auto Perfil", "Essencial", 1),
    "residencia": ("residencial", "Residencial Total", "Essencial", 1),
}

print(f"\n[0] o acervo: {len(PERGUNTAS)} perguntas reais, "
      f"{len({p['categoria'] for p in PERGUNTAS})} categorias")
checar(len(PERGUNTAS) == 30, "são 30 perguntas", str(len(PERGUNTAS)))

print("\n[1] as 30, PELO MOTOR (`compose_policy_answer_with_meta`)")
contagem: dict = {}
sem_estado, sem_fonte, servico_errado, genericas_sem_ressalva = [], [], [], []
for item in PERGUNTAS:
    ramo, produto, plano, nivel = RAMO_DA_CATEGORIA[item["categoria"]]
    meta = compose_policy_answer_with_meta(
        question=item["pergunta"], result=_result(_pack(ramo, produto, plano, nivel)),
        db=db, atendente="Regina")
    cob = meta.get("cobertura")
    if not isinstance(cob, dict) or cob.get("estado") not in (ESTADOS + (FALHA,)):
        sem_estado.append((item["pergunta"][:60], cob))
        continue
    estado = cob["estado"]
    contagem[estado] = contagem.get(estado, 0) + 1
    if cob.get("servico") != item["servico_esperado"]:
        servico_errado.append((item["pergunta"][:60], cob.get("servico"),
                               item["servico_esperado"]))
    if cob.get("origem") == "base":
        pagina = cob.get("pagina")
        tem_no_texto = pagina is not None and ("p. %s" % pagina) in str(meta.get("text") or "")
        if not (cob.get("documento_id") and pagina and tem_no_texto):
            sem_fonte.append((item["pergunta"][:60], estado, cob.get("documento_id"),
                              pagina, str(meta.get("text") or "")[:90]))
    elif cob.get("origem") == "regra_generica":
        low = str(meta.get("text") or "").lower()
        if cob.get("documento_id") or cob.get("pagina") or "padrao de mercado" not in low.replace("ã", "a").replace("é", "e"):
            genericas_sem_ressalva.append((item["pergunta"][:60], cob.get("documento_id"),
                                           cob.get("pagina"), str(meta.get("text") or "")[:100]))

print("      📊 estados: " + " · ".join(f"{k}={v}" for k, v in sorted(contagem.items())))
checar(not sem_estado,
       "🔴 ① as 30 devolvem UM dos cinco estados (ou a falha declarada)",
       repr(sem_estado[:3]))
checar(not servico_errado,
       "o serviço identificado é o esperado em todas as 30",
       repr(servico_errado[:3]))
checar(not sem_fonte,
       "🔴 ② toda resposta da BASE traz documento e página — no CAMPO e no "
       "TEXTO que o segurado lê",
       repr(sem_fonte[:2]))
checar(not genericas_sem_ressalva,
       "🔴 ②b e toda resposta do FALLBACK sai SEM fonte e COM a ressalva de que "
       "é padrão de mercado, não o contrato dele",
       repr(genericas_sem_ressalva[:2]))

print("\n[2] 🔴 CONTROLE do bloco: a medição CONSEGUE distinguir")
checar(len(contagem) >= 3,
       "🔴 CONTROLE: as 30 produziram pelo menos TRÊS estados diferentes — "
       "a asserção ② não passou por vácuo",
       repr(sorted(contagem)))
checar(contagem.get("nao_sabemos_ainda", 0) > 0,
       "e `nao_sabemos_ainda` aparece: serviço sem linha publicada continua sendo "
       "lacuna, não 'não'", repr(contagem))

print("\n[3] 🔴 A LINHA DE CONTROLE (GATE B ②): pergunta que não é de cobertura")
db_controle = BaseEmMemoria()
meta_c = compose_policy_answer_with_meta(
    question="quantas parcelas faltam?",
    result=_result(_pack("auto", "Auto Perfil", "Essencial", 1)), db=db_controle)
checar(db_controle.chamadas_de_tabela == [],
       "🔴 'quantas parcelas faltam?' NÃO consulta a base de planos — zero "
       "chamadas de tabela", repr(db_controle.chamadas_de_tabela))
checar(meta_c.get("cobertura") is None,
       "e não produz veredito de cobertura nenhum", repr(meta_c.get("cobertura")))
checar("parcela" in str(meta_c.get("text") or "").lower(),
       "a resposta continua sendo a de parcelas — o caminho antigo não foi tocado",
       str(meta_c.get("text") or "")[:120])

print("\n[4] 🔴 CONTROLE do controle: as perguntas do acervo CONSULTARAM a base")
db_prova = BaseEmMemoria()
db_prova.plano(insurer_key="hdi", ramo="auto", produto="Auto Perfil",
               plano="Essencial", nivel=1)
compose_policy_answer_with_meta(
    question=PERGUNTAS[0]["pergunta"],
    result=_result(_pack("auto", "Auto Perfil", "Essencial", 1)), db=db_prova)
checar(bool(db_prova.chamadas_de_tabela),
       "🔴 CONTROLE: uma pergunta de cobertura DE FATO consulta a base — "
       "sem isto, o [3] ficaria verde mesmo com a Skill desligada",
       repr(db_prova.chamadas_de_tabela[:3]))

print("\n[5] BLOCO E — a mesma fonte chega ao REGISTRO, e sem PII")
from app.services.skills.invocation_recorder import _resumo_da_saida  # noqa: E402
from app.services.portals.replay import varredura_de_pii  # noqa: E402

meta_reg = compose_policy_answer_with_meta(
    question="o CPF 529.982.247-25 tem carro reserva?",
    result=_result(_pack("auto", "Auto Perfil", "Essencial", 1)), db=db)
retorno_da_tool = {"content": meta_reg["text"], "data": {}, "found": True,
                   "cobertura": meta_reg.get("cobertura")}
resumo = _resumo_da_saida(retorno_da_tool)
origem = resumo.get("cobertura") or {}
checar(origem.get("estado") == "nao_coberto" and origem.get("insurer_key") == "hdi",
       "🔴 o registro carrega o ESTADO e a seguradora canônica", repr(origem))
checar(origem.get("documento_id") and origem.get("pagina")
       and origem.get("documento") == "presente",
       "🔴 e o documento e a página — o documento como PRESENÇA, nunca conteúdo",
       repr(origem))
achados = varredura_de_pii(resumo)
checar(not achados,
       "🔴 varredor de PII sobre o `input_summary`/saída do registro: ZERO achados",
       repr([(a.tipo, a.caminho) for a in achados[:3]]))
# 🔴 CONTROLE: o varredor CONSEGUE acusar. A pergunta CRUA, com o mesmo CPF
#    fictício, deixa-o vermelho — é assim que se sabe que o verde acima vale.
sujo = varredura_de_pii({"pergunta": "o CPF 529.982.247-25 tem carro reserva?"})
checar(bool(sujo),
       "🔴 CONTROLE: com a pergunta CRUA no resumo, o varredor fica VERMELHO",
       repr([(a.tipo, a.caminho) for a in sujo[:3]]))
# 🔴 O CPF INTEIRO, não os três primeiros dígitos.
#
# 📊 18/09/2026: esta linha procurava `"529"` — e o `documento_id` do duplo é um
# `uuid4()`, que contém "529" por acaso em ~1 rodada de cada 5. O guarda ficava
# vermelho sem nenhum defeito, e um guarda que falha sozinho ensina a ignorar
# guarda (CLAUDE.md §9.3). O que se quer afirmar é que o CPF não vazou — então é
# o CPF que se procura, com e sem pontuação.
_CPF = "529.982.247-25"
_bruto = json.dumps(resumo, ensure_ascii=False)
checar(_CPF not in _bruto and _CPF.replace(".", "").replace("-", "") not in _bruto
       and not re.search(r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}", _bruto),
       "🔴 e o CPF da pergunta não aparece em lugar nenhum do registro "
       "(nem formatado, nem em 11 dígitos)",
       _bruto[:160])
# 🔴 CONTROLE: a mesma busca ACHA o CPF quando ele está lá.
checar(_CPF in json.dumps({"pergunta": "o CPF %s tem carro reserva?" % _CPF}),
       "🔴 CONTROLE: a busca CONSEGUE achar o CPF quando ele existe no dicionário")

print()
print("=" * 74)
print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
print("=" * 74)
sys.exit(1 if FAIL else 0)
