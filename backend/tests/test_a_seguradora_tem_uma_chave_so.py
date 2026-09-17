# -*- coding: utf-8 -*-
r"""🔴 M-A1 · A SEGURADORA TEM UMA CHAVE SÓ — e é a de CONHECIMENTO.

SPEC-EXTRA-001.5 · BLOCO A. O que este guarda existe para impedir são dois
defeitos que chegam ao segurado pelo mesmo caminho:

```
1. a mesma seguradora arquivada sob duas chaves
   "tokio", "tokio_marine" e "tokio marine" viram três bases diferentes, e a
   pergunta cai na que está vazia -> "não sabemos ainda" com o dado na mão

2. 🔴 a chave do CORREDOR usada para arquivar CONHECIMENTO
   `para="corredor"` aplica `_OPERADO_POR` ({"itau": "porto"}) — é a pergunta
   "por onde eu ACIONO". Arquivar com ela põe a condição geral do ITAÚ sob
   PORTO, e o agente passa a responder regra da Porto a segurado do Itaú.
```

⚠️ E o terceiro, que é o silencioso: 📊 `normalize_insurer_key` devolve **o
primeiro token** para o que não conhece — `"seguradora_xyz"` → `"seguradora"`
(`corridor_playbooks.py:8262`). Gravar isso não dá erro nenhum: dá uma base
cheia de chaves que ninguém consegue achar depois.

🔴 **O guarda chama o MOTOR** (CLAUDE.md §9.4): `chave_de_conhecimento` e
`normalize_insurer_key` de verdade, nunca um regex sobre a mesma tabela.
"""
from __future__ import annotations

import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from app.services.corridor_playbooks import (  # noqa: E402
    _INSURER_ALIASES,
    normalize_insurer_key,
)
from app.services.knowledge import assistance_plans_base as B  # noqa: E402

OK = FAIL = 0


def checar(cond, rotulo, detalhe=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok    {rotulo}")
    else:
        FAIL += 1
        print(f"  FALHA \U0001F534 {rotulo}" + (f"\n        {detalhe}" if detalhe else ""))


print("\n[1] a mesma seguradora, escrita de três jeitos, dá UMA chave")
grafias = ("tokio", "tokio_marine", "tokio marine", "Tokio Marine", "TOKIO MARINE")
chaves = {g: B.chave_de_conhecimento(g) for g in grafias}
checar(len(set(chaves.values())) == 1 and set(chaves.values()) == {"tokio"},
       "🔴 as 5 grafias de Tokio Marine dão a MESMA chave, e é `tokio`",
       repr(chaves))

# CONTROLE do bloco: o motor CONSEGUE devolver chaves diferentes — senão o de
# cima passaria por vácuo (bastaria a função devolver sempre a mesma coisa).
checar(B.chave_de_conhecimento("porto") != B.chave_de_conhecimento("tokio"),
       "🔴 CONTROLE: o motor CONSEGUE devolver chaves diferentes",
       f"porto={B.chave_de_conhecimento('porto')} tokio={B.chave_de_conhecimento('tokio')}")

print("\n[2] 🔴 O PAR DE CONTROLE — `para=` muda a resposta, e é para isso que serve")
itau_corredor = normalize_insurer_key("itau", para="corredor")
itau_conhec = normalize_insurer_key("itau", para="conhecimento")
checar(itau_corredor == "porto",
       "por onde se ACIONA o Itaú: `para='corredor'` → porto (_OPERADO_POR)",
       f"veio {itau_corredor!r}")
checar(itau_conhec == "itau",
       "🔴 de QUEM é a regra: `para='conhecimento'` → itau, NÃO porto",
       f"veio {itau_conhec!r}")
checar(itau_corredor != itau_conhec,
       "🔴 e os dois são DIFERENTES — o par prova que a escolha do `para=` importa")
checar(B.chave_de_conhecimento("itau") == "itau",
       "a BASE arquiva a carta do Itaú sob `itau` — a carta não some sob Porto",
       f"veio {B.chave_de_conhecimento('itau')!r}")

print("\n[3] a desconhecida NÃO entra, e a recusa LISTA o valor")
for bruto in ("seguradora_xyz", "Seguradora XYZ", "prestadora do bairro", ""):
    try:
        gravado = B.chave_de_conhecimento(bruto)
        checar(False, f"🔴 {bruto!r} foi ACEITO como seguradora",
               f"gravaria {gravado!r} — 📊 é o primeiro token, não uma seguradora")
    except B.SeguradoraDesconhecida as exc:
        msg = str(exc)
        checar(bruto in msg or (bruto == "" and "''" in msg),
               f"{bruto!r} recusado E o valor aparece na mensagem",
               msg)
        checar(exc.valor is not None and isinstance(exc.valor, str),
               f"{bruto!r}: o valor é STRING, nunca None (susep_ses_provider.py:92-95)")

# 🔴 a prova de que a recusa não é um "recusa tudo": o que É seguradora passa.
checar(B.chave_de_conhecimento("HDI Seguros") == "hdi",
       "🔴 CONTROLE: `hdi` PASSA — 📊 tem 8 documentos no corpus e está FORA das "
       "61 siglas da carteira; o critério não pode ser o censo")

print("\n[4] o critério de 'conhecida' é UM, e é verificável")
conhecidas = B.seguradoras_conhecidas()
checar(conhecidas == frozenset(_INSURER_ALIASES.values()),
       "o critério é `set(_INSURER_ALIASES.values())` — a lista viva, não uma cópia",
       f"{len(conhecidas)} chaves")
checar("hdi" in conhecidas and "susep" not in conhecidas,
       "🔴 `hdi` está dentro e `susep` fora — 📊 susep é o REGULADOR e aparece em "
       "`select distinct insurer_key from normative_documents`",
       f"hdi={'hdi' in conhecidas} susep={'susep' in conhecidas}")

print("\n[5] 🔴 A VARREDURA — a base NUNCA pede a chave do corredor")
FONTE = os.path.join(RAIZ, "app", "services", "knowledge", "assistance_plans_base.py")
with open(FONTE, encoding="utf-8") as fh:
    fonte = fh.read()


def _paras_das_CHAMADAS(codigo: str) -> list:
    """Os `para=` das CHAMADAS de verdade — por AST, não por regex sobre o texto.

    ⚠️ Um `grep` simples aqui fica vermelho pelo motivo errado: o docstring do
    módulo **cita** `para="corredor"` para explicar por que ele não serve. Prosa
    não executa. Quem decide o que o produto faz é a CHAMADA — e a chamada é um
    nó da árvore, não uma linha de texto.
    """
    import ast

    achados = []
    for no in ast.walk(ast.parse(codigo)):
        if not isinstance(no, ast.Call):
            continue
        alvo = no.func.attr if isinstance(no.func, ast.Attribute) else getattr(no.func, "id", "")
        if "normalize" not in str(alvo):
            continue
        for kw in no.keywords:
            if kw.arg == "para" and isinstance(kw.value, ast.Constant):
                achados.append(kw.value.value)
    return achados


chamadas = _paras_das_CHAMADAS(fonte)
checar(bool(chamadas) and set(chamadas) == {"conhecimento"},
       "🔴 toda CHAMADA com `para=` em assistance_plans_base.py é 'conhecimento'",
       f"encontradas: {chamadas}")
# 🔴 CONTROLE: a varredura CONSEGUE acusar. Sem isto, a linha acima ficaria
#    verde também se ela não enxergasse chamada nenhuma.
_mutada = fonte.replace('para="conhecimento"', 'para="corredor"')
checar("corredor" in _paras_das_CHAMADAS(_mutada),
       "🔴 CONTROLE: com `para=\"corredor\"` na CHAMADA, a varredura FICA VERMELHA",
       f"na cópia mutada ela vê: {_paras_das_CHAMADAS(_mutada)}")
# 🔴 CONTROLE 2: e a prosa do docstring, que CITA "corredor", NÃO conta.
checar('para="corredor"' in fonte,
       "🔴 CONTROLE 2: o arquivo CITA `para=\"corredor\"` no docstring — e mesmo "
       "assim a varredura acima fica verde, porque prosa não é chamada")

print()
print("=" * 74)
print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
print("=" * 74)
sys.exit(1 if FAIL else 0)
