# -*- coding: utf-8 -*-
"""Os presets de cobertura do multicálculo — SPEC-129-B D-129B-08 (💭 RASCUNHO, D-MC-54).

A PORTA resolve as coberturas de cada opção com estes presets e grava em `multicalculo_calculos.coberturas`;
o robô só aplica o que recebe. A 130-A troca os presets depois do portão de preço.

🔴 Por que o motor manda as coberturas EXPLÍCITAS: 📊 o "pacote Prata" é configuração de CADA conta do Agger
(MEDICOES §E-pacotes: AF franquia reduzida/RCF 200-200-20/APP 5 mil × RES franquia normal/RCF 0) — o mesmo
pedido sem coberturas explícitas sairia com coberturas diferentes em cada corretora.

Os CÓDIGOS são os do corpo do `calcularV2`, medidos (CLAUDE.md §9.5: cada constante diz por que está certa):
    📊 AF "Prata" (05/10 M1, laudo §M1 "franquia reduzida, vidros completos, reserva 15 d, assistência completa")
       = tipoFranquia 1 · vidros 2 · carroReserva 2 · assist24hs 1  (corpo de 6 `calcularV2` da 128, raw/autofleet)
    📊 RES "Prata" (MEDICOES: "franquia normal, assistência básica, vidros básico, reserva 7 d")
       = tipoFranquia 2 · vidros 1 · carroReserva 1 · assist24hs 4   (1 `calcularV2` da 128, raw/resulta)
    ⚠️ os códigos NÃO são ordinais: assistência COMPLETA = 1 e BÁSICA = 4 (as opções da tela são
       Não · Básica · Intermediária · Completa, opcoes_auto.txt). Não "corrija" para a ordem da tela.
"""
from __future__ import annotations

from typing import Dict, Mapping

PADRAO = "padrao"
ECONOMICA = "economica"

# As 15 chaves de cobertura que o APP escolhe (📊 laudo M0a: 23 chaves só existem no pedido; estas são as de
# cobertura). O montador aplica exatamente estas sobre cada item da seguradora.
CHAVES_DE_COBERTURA = (
    "tipoCobertura", "tipoFranquia", "isDanosMateriais", "isDanosCorporais", "isDanosMorais", "isAppMorte",
    "isBlindagemValor", "carroReserva", "carroReservaAr", "vidros", "assist24hs", "despesasExtra",
    "protecaoPneuRodas", "reparoRapido", "valorDeNovo",
)

_PADRAO: Dict[str, object] = {
    "tipoCobertura": 1,          # 📊 o tipo usado no M1 ao vivo (201, 26 ofertas) — não mexer sem medir
    "tipoFranquia": 1,           # REDUZIDA (📊 AF Prata)
    "isDanosMateriais": 200000,  # RCF danos materiais R$ 200 mil (D-129B-08)
    "isDanosCorporais": 200000,  # RCF danos corporais R$ 200 mil
    "isDanosMorais": 20000,      # RCF danos morais R$ 20 mil
    "isAppMorte": 5000,          # APP R$ 5 mil
    "isBlindagemValor": 0,
    "carroReserva": 2,           # 15 DIAS (📊 AF Prata)
    "carroReservaAr": False,
    "vidros": 2,                 # COMPLETO (📊 AF Prata). ⚠️ Allianz recusa SEM vidros (MEDICOES E5)
    "assist24hs": 1,             # COMPLETA (📊 AF Prata — código 1, não 3)
    "despesasExtra": False,
    "protecaoPneuRodas": False,
    "reparoRapido": False,
    "valorDeNovo": 0,
}

# A econômica mexe SÓ no que barateia sem tirar proteção de terceiros: 📊 as maiores alavancas medidas são
# vidros (até −27,6 %) e franquia (até −18,1 %) (MEDICOES E5). RCF/APP ficam INTACTOS (D-129B-08): 📊 com RCF 0
# a Bradesco e a Aliro recusaram ("DMO obrigatória", "contratar LMI RCF").
_ECONOMICA: Dict[str, object] = dict(
    _PADRAO,
    tipoFranquia=2,              # NORMAL (📊 RES Prata)
    vidros=1,                    # BÁSICO (📊 RES Prata) — não "0": sem vidros a Allianz recusa
    carroReserva=1,              # 7 DIAS (📊 RES Prata)
    assist24hs=4,                # BÁSICA (📊 RES Prata — código 4)
)

PRESETS: Mapping[str, Mapping[str, object]] = {PADRAO: _PADRAO, ECONOMICA: _ECONOMICA}

# O AJUSTE do corretor (`contrato.Ajuste`) → a chave de cobertura que ele troca. 🔴 O GÊMEO em Python de
# `CAMPO_DO_AJUSTE` do `montador.js` (o robô aplica lá, na página): a porta usa este para gravar em
# `calculos.coberturas` o que o recálculo VAI mandar — sem ele, `coberturas` do ajuste guardava `{"franquia": …}`,
# uma chave que o montador não conhece (F4, costura). `test_spec129b_o_fio` confere que os dois dizem o mesmo.
# `percentual_fipe` mexe no AUTOMÓVEL (`pctAjuste`), não no item de cobertura: fica fora.
CAMPO_DO_AJUSTE: Mapping[str, str] = {
    "comissao": "percComissao", "desconto": "percDesconto", "assistencia": "assist24hs",
    "carro_reserva": "carroReserva", "vidros": "vidros", "franquia": "tipoFranquia", "cobertura": "tipoCobertura",
}
# Os RÓTULOS que viram código no ajuste — só os MEDIDOS (os mesmos dos presets acima, §9.5):
#   📊 franquia reduzida 1 · normal 2 (AF Prata × RES Prata) · vidros básico 1 · completo 2 ·
#   📊 carro reserva 7 dias 1 · 15 dias 2 · assistência completa 1 · básica 4 (NÃO ordinal: ver o topo)
VALORES_DO_AJUSTE: Mapping[str, Mapping[str, int]] = {
    "franquia": {"reduzida": 1, "normal": 2},
    "vidros": {"basico": 1, "completo": 2},
    "carro_reserva": {"7": 1, "7 dias": 1, "15": 2, "15 dias": 2},
    "assistencia": {"completa": 1, "basica": 4},
}


def coberturas_de(opcao: str) -> Dict[str, object]:
    """Uma CÓPIA do preset (quem recebe pode alterar sem contaminar o próximo pedido)."""
    if opcao not in PRESETS:
        raise ValueError(f"opção sem preset: {opcao!r} (há: {', '.join(PRESETS)})")
    return dict(PRESETS[opcao])
