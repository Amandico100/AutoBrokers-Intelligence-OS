# -*- coding: utf-8 -*-
"""Os presets de cobertura do multicálculo — SPEC-129-B D-129B-08 (💭 RASCUNHO, D-MC-54).

A PORTA resolve as coberturas de cada opção com estes presets e grava em `multicalculo_calculos.coberturas`;
o robô só aplica o que recebe. A 130-A troca os presets depois do portão de preço.

🔴 Este arquivo é a ÚNICA fonte do CORPO do Agger por opção (SPEC-130-A F4). A config comercial da corretora
(`app/services/multicalculo/config.py`, `calculo_por_papel`) só ESCOLHE qual cálculo alimenta cada papel da
proposta — nunca repete um código de cobertura (os códigos são medidos e NÃO ordinais; ver abaixo).

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

from typing import Dict, Mapping, Tuple

PADRAO = "padrao"
ECONOMICA = "economica"
COMPLETA_MAIS = "completa_mais"
MINIMA = "minima"

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

# A COMPLETA+ (D-MC-69 / D-130A-09): a padrão (D-MC-65 — franquia reduzida, vidros completos, reserva 15 d,
# assistência completa: a "franquia reduzida" da completa+ JÁ é da padrão) + PEQUENOS REPAROS. Uma chave só muda.
#   📊 `reparoRapido` é booleano no corpo do `calcularV2`: `true` aparece 49× em `tests/fixtures/agger/gravacao_r1.json`
#      (`grep -o '"reparoRapido":true' … | wc -l`, 06/10), eco do pedido de uma conta real; a padrão manda `false`.
_COMPLETA_MAIS: Dict[str, object] = dict(
    _PADRAO,
    reparoRapido=True,           # PEQUENOS REPAROS (D-MC-69: "completa+ com franquia reduzida e pequenos reparos")
)

# A MÍNIMA — o "mínimo do mínimo" (SPEC-130-A.1 D-130A1-05): a econômica SEM carro reserva. Uma chave só muda.
# Só o canal a pede (`porta.OPCOES_DO_CANAL`); ela mostra a maior economia e NUNCA é a recomendada (comparacao.opcoes).
#   📊 `carroReserva: 0` ↔ "Não contratar" (tests/fixtures/agger/vivo_conta_b.json, medido 07/10 pelo builder F3):
#      o cálculo #4 do acervo variou UM fator só (carroReserva 0; o resto igual ao #6) → 112 itens de seguradora com 0
#      nas rodadas; as 90 ofertas que devolveram `coberturas.carroReserva` dizem TODAS "Não contratar" (13 seguradoras)
#      e 16/16 seguradoras devolveram oferta (nenhuma recusou o 0). `test_spec130a1_minima` reconta isto no acervo.
#      ⚠️ "Não" (102×, Azul por Assinatura) e "Não desejo contratar" (52×, Bradesco) vieram com o código 2: é a
#      seguradora sem carro reserva naquele produto, não a resposta ao 0 (a comparação lê os três como 0 dias).
#   📊 efeito no menor preço por seguradora (#4 × #6): de −0,3 % a −6,9 % em 10 de 13; iguais em 2; Zurich +1,4 %.
#   Vidros FICAM básicos (sem vidros a Allianz recusa — acima) e terceiros/APP intactos (RCF 0 → recusas — acima).
#   Franquia "majorada" NÃO entra: o código 4 aparece no acervo, mas o rótulo dele não foi medido (§9.5).
#   A comissão é a NORMAL: nenhum preset carrega `percComissao` (ela vem da conta / da negociação).
_MINIMA: Dict[str, object] = dict(
    _ECONOMICA,
    carroReserva=0,              # SEM CARRO RESERVA (📊 0 → "Não contratar", 90/90 ofertas)
)

PRESETS: Mapping[str, Mapping[str, object]] = {PADRAO: _PADRAO, ECONOMICA: _ECONOMICA, COMPLETA_MAIS: _COMPLETA_MAIS,
                                               MINIMA: _MINIMA}

# A ORDEM do disparo no MESMO negócio (D-129B-03): a padrão ABRE o negócio (versão 1); a econômica, a completa+ e a
# mínima são versões seguintes dele, nesta ordem (a mínima por ÚLTIMO das opções: é a que o canal pode dispensar). O
# motor ordena por aqui (o ajuste do corretor vem depois de todas) e a porta aceita exatamente estas opções
# (`porta.OPCOES` — o teste confere que as duas listas dizem o mesmo).
ORDEM: Tuple[str, ...] = (PADRAO, ECONOMICA, COMPLETA_MAIS, MINIMA)

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
