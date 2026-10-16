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


# ======================================================================================================================
# SPEC-129-C — as opções de RE (D-129C-03): Condomínio 16 · Residencial 2 · Empresarial 18
# ======================================================================================================================
# 🔴 NENHUM valor segurado fixo: a BÁSICA (incêndio) vem do PEDIDO (`risco.valor_basica`) — 📊 a Básica do condomínio vai
# de R$ 2,5 mi a R$ 115 mi nos 15 negócios lidos (AGREGADO-POR-RAMO §2); um pacote fixo seria errado para quase todos.
# A opção varia só as coberturas EXTRAS e a ASSISTÊNCIA:
#   · "padrao"    = as coberturas TÍPICAS do ramo: as que a corretora mandou em >= 8 dos 15 negócios lidos (metade+),
#                   no valor MEDIANO medido (📊 AGREGADO-POR-RAMO §2, n = 15 por ramo), e a assistência da maioria;
#   · "economica" ("mais em conta") = só as ESSENCIAIS — as mandadas em >= 13 dos 15 (~85 %) — MAIS toda RC (terceiros
#                   intactos, o mesmo princípio do auto, D-129B-08) e a assistência BÁSICA.
#   📊 o "mais em conta" que as corretoras fazem no Agger é exatamente "tirar acessórias e baixar a assistência"
#      (AGREGADO §2 "Padrão x mais em conta": assistência 2->1, tirar roubo/vendaval/vazamento/RC...).
# 💭 ESCALA: as coberturas de PATRIMÔNIO (não as de RC) escalam com a Básica ABAIXO da Básica mediana do ramo:
#   valor = mediana * min(1, básica / básica_mediana). Por quê: as recusas de RE mais comuns são de LIMITE relativo à
#   Básica (📊 AGREGADO §1 "limite máximo para roubo é #% da cobertura básica", "LMI de despesas fixas acima do permitido
#   (#% da cobertura incêndio)"; 📊 gravacao_empresarial_2: aluguel 240 mil sobre Básica 800 mil -> Allianz "supera o
#   máximo permitido (120.000,00)" e Mapfre "supera o Limite Máximo") — a proporção da mediana é a que as seguradoras
#   aceitaram. A RC não escala (não é % da Básica). O canário (F3) mede se a regra segura.
# ⚠️ Os códigos de ASSISTÊNCIA do RE são OUTROS (📊 formulario_*.json, os 3 ramos): Não 0 · Básica 1 · Intermediária 2 ·
#    Completa 3 — no auto Completa = 1 e Básica = 4. Não misture as tabelas.
ASSISTENCIA_RE: Mapping[str, int] = {"nao": 0, "basica": 1, "intermediaria": 2, "completa": 3}

# As chaves de COBERTURA de cada ramo — as da seção "Coberturas" de cada formulário que vão a `configuracoes`
# (📊 formulario_<ramo>.json `campos[].caminho_no_corpo`), menos `valorDeNovo` e `imovelObjetoSegurado` (são do RISCO,
# no contrato). Empresarial: + `responsabilidadeCivilOperacoes` (📊 gravacao_empresarial_1/2: sempre igual a
# `responsabilidadeCivil`, "RC Operações"); o `isGuardaVeiculoValor` da tela não tem caminho medido (fica fora).
# O robô aplica SÓ estas em `configuracoes`.
CHAVES_DE_COBERTURA_RE: Mapping[int, Tuple[str, ...]] = {
    16: ("assist24hs", "isDanosIncendioRaioExplosao", "isDanosIncendioRaioExplosaoCond", "isValorCondominio",
         "isValorSindico", "isDanosEletricos", "isDanosVendaval", "isDanosImpactoVeiculo", "isDanosRoubo",
         "rouboCondomino", "isDanosPortoes", "isDanosMorais", "vidros", "isDanosDesmoronamento", "isDanosAluguel",
         "isDanosVazamentoTanquesTubulacoes", "anunciosLuminosos", "tumultoGreveLockOut", "isDanosAlagamento",
         "isDanosDespesasFixas", "equipamentos", "isEmpregador", "isVGFuncionarios", "garagista", "garagistaExclusiva",
         "chuveiroSprinkler", "placasSolares"),
    2: ("assist24hs", "isDanosIncendioRaioExplosao", "isDanosEletricos", "isDanosEquipamentosEletronicos",
        "isDanosRegistrosDocumentos", "isDanosVendaval", "isDanosImpactoVeiculo", "isDanosAluguel", "isDanosRoubo",
        "responsabilidadeCivil", "isDanosAlagamento", "isDanosDesmoronamento", "vidros", "isDanosMorais",
        "tumultoGreveLockOut", "placasSolares", "bike", "isDanosVazamentoTanquesTubulacoes"),
    18: ("assist24hs", "isDanosIncendioRaioExplosao", "isDanosEletricos", "isDanosVendaval", "isDanosImpactoVeiculo",
         "isDanosAluguel", "isDanosRoubo", "rouboFurtoDeValores", "vidros", "isDanosVazamentoTanquesTubulacoes",
         "isDanosDespesasFixas", "equipamentos", "anunciosLuminosos", "isEmpregador", "isDanosMorais",
         "responsabilidadeCivil", "responsabilidadeCivilOperacoes", "recomposicaoDocumentos", "tumultoGreveLockOut",
         "isDanosDesmoronamento", "chuveiroSprinkler", "fidelidade", "placasSolares", "isDanosAlagamento",
         "lucroCessante", "isDanosContaminacaoDeterioracao"),
}
CHAVE_DA_BASICA = "isDanosIncendioRaioExplosao"
# 🔴 Conserto 129-C (juiz B2, D-129C-03 nota 88): a Básica de RE vem SÓ do pedido — o AJUSTE de cobertura (recálculo)
# nunca a muda. Antes o robô e o montador aplicavam a Básica do ajuste em `configuracoes` enquanto a porta gravava a do
# pedido: o banco dizia uma Básica e o Agger calculava outra. Estas são as chaves que o ajuste PODE mudar (o gêmeo em
# montador.js `aplicarAjusteRE` recusa a Básica também, mesmo que alguém a ponha na lista).
CHAVES_DO_AJUSTE_RE: Mapping[int, Tuple[str, ...]] = {
    r: tuple(k for k in ks if k != CHAVE_DA_BASICA) for r, ks in CHAVES_DE_COBERTURA_RE.items()}

# A Básica MEDIANA de cada ramo (📊 AGREGADO §2: condomínio 14 mi · residencial 550 mil · empresarial 2 mi)
BASICA_MEDIANA: Mapping[int, int] = {16: 14_000_000, 2: 550_000, 18: 2_000_000}
# (chave, mediana medida, em quantos dos 15 negócios lidos, é RC — não escala). 📊 AGREGADO-POR-RAMO §2, linha a linha.
# Ficam de fora as de >= 8/15 SEM mediana medida (condomínio desmoronamento 8/15; empresarial impacto e vazamento 8/15):
# sem número medido, nenhum valor inventado.
TIPICAS_RE: Mapping[int, Tuple[Tuple[str, int, int, bool], ...]] = {
    16: (("isDanosEletricos", 52_000, 15, False), ("isDanosImpactoVeiculo", 50_000, 15, False),
         ("vidros", 15_000, 15, False), ("isValorCondominio", 300_000, 15, True), ("isValorSindico", 300_000, 15, True),
         ("isDanosVendaval", 84_000, 15, False), ("isDanosPortoes", 30_000, 15, False),
         ("isDanosMorais", 50_000, 14, True), ("tumultoGreveLockOut", 20_000, 13, False),
         ("isDanosRoubo", 10_000, 13, False), ("isDanosAluguel", 300_000, 11, False),
         ("isDanosVazamentoTanquesTubulacoes", 70_000, 11, False),
         ("isDanosIncendioRaioExplosaoCond", 1_600_000, 11, False)),
    2: (("isDanosEletricos", 25_000, 13, False), ("isDanosVendaval", 50_000, 13, False),
        ("responsabilidadeCivil", 50_000, 12, True), ("isDanosAluguel", 36_000, 10, False),
        ("isDanosRoubo", 37_500, 10, False), ("isDanosVazamentoTanquesTubulacoes", 20_000, 9, False),
        ("vidros", 20_000, 9, False)),
    18: (("isDanosEletricos", 30_000, 15, False), ("responsabilidadeCivil", 125_000, 12, True),
         ("responsabilidadeCivilOperacoes", 125_000, 12, True), ("vidros", 10_000, 11, False),
         ("isDanosAluguel", 90_000, 10, False), ("isDanosVendaval", 100_000, 10, False),
         ("isDanosRoubo", 30_000, 10, False)),
}
TIPICA_MIN = 8        # >= 8 de 15 = metade+ -> "padrão"
ESSENCIAL_MIN = 13    # >= 13 de 15 ~ 85 % -> "mais em conta" (+ toda RC)
# A assistência de cada opção (📊 AGREGADO §2): condomínio Completa 3 em 8 de 15 (Básica em 7) · residencial
# Intermediária 2 em 10 de 15 · empresarial Básica 1 em 15 de 15. "Mais em conta" = Básica 1 nos três.
ASSISTENCIA_DA_OPCAO_RE: Mapping[int, Mapping[str, int]] = {
    16: {PADRAO: ASSISTENCIA_RE["completa"], ECONOMICA: ASSISTENCIA_RE["basica"]},
    2: {PADRAO: ASSISTENCIA_RE["intermediaria"], ECONOMICA: ASSISTENCIA_RE["basica"]},
    18: {PADRAO: ASSISTENCIA_RE["basica"], ECONOMICA: ASSISTENCIA_RE["basica"]},
}
# As opções do RE e a ORDEM do disparo no mesmo negócio (a padrão abre; a "mais em conta" é a versão seguinte).
ORDEM_RE: Tuple[str, ...] = (PADRAO, ECONOMICA)

# O AJUSTE do corretor no RE (`contrato.TIPOS_DE_AJUSTE_RE`). Comissão/desconto vão no ITEM; assistência e cobertura em
# `configuracoes` — 🔴 o GÊMEO do ramo RE de `aplicarAjuste` no montador.js (o teste confere que dizem o mesmo).
CAMPO_DO_AJUSTE_RE: Mapping[str, str] = {"comissao": "percComissao", "desconto": "percDesconto",
                                          "assistencia": "assist24hs"}
VALORES_DO_AJUSTE_RE: Mapping[str, Mapping[str, int]] = {"assistencia": ASSISTENCIA_RE}


def _arredonda(v: float) -> int:
    return int(round(v / 100.0)) * 100


def coberturas_re(ramo: int, opcao: str, valor_basica: float,
                  extras: "Mapping[str, float] | None" = None) -> Dict[str, object]:
    """As coberturas de `configuracoes` da opção — TODAS as chaves do ramo, explícitas (zero = não contratada), a Básica
    do PEDIDO e a assistência da opção. `extras` (do pedido: a apólice anterior / o cliente) VENCE a opção."""
    if ramo not in CHAVES_DE_COBERTURA_RE:
        raise ValueError(f"ramo sem coberturas de RE: {ramo!r}")
    if opcao not in ORDEM_RE:
        raise ValueError(f"opção sem preset no RE: {opcao!r} (há: {', '.join(ORDEM_RE)})")
    if isinstance(valor_basica, bool) or not isinstance(valor_basica, (int, float)) or valor_basica <= 0:
        raise ValueError("a Básica do pedido é obrigatória e > 0 (D-129C-03)")
    chaves = CHAVES_DE_COBERTURA_RE[ramo]
    saida: Dict[str, object] = {k: 0 for k in chaves}
    saida[CHAVE_DA_BASICA] = valor_basica
    saida["assist24hs"] = ASSISTENCIA_DA_OPCAO_RE[ramo][opcao]
    fator = min(1.0, float(valor_basica) / BASICA_MEDIANA[ramo])
    minimo = TIPICA_MIN if opcao == PADRAO else ESSENCIAL_MIN
    for chave, mediana, n, rc in TIPICAS_RE[ramo]:
        if n >= minimo or (opcao == ECONOMICA and rc):
            saida[chave] = mediana if rc else _arredonda(mediana * fator)
    for k, v in (extras or {}).items():
        if k not in chaves or k == "assist24hs":
            raise ValueError(f"cobertura desconhecida no ramo {ramo}: {k!r}")
        saida[k] = v
    return saida


# ======================================================================================================================
# SPEC-131-A F2 — AS OPÇÕES DA RENOVAÇÃO (D-MC-69 · laudo I3 §1.3): "anterior" · "franquia_reduzida" · "completa_mais"
# ======================================================================================================================
# 🔴 Para quem JÁ é cliente as comerciais descrevem "igual ao ano passado + melhorias" (📊 ESTRATEGIA-COMERCIAL §1.1/§1.4,
#    n = 4): ninguém descreve "o mais barato possível". Por isso ⛔ a econômica e a mínima NUNCA entram numa renovação
#    (mutação 7 da SPEC-131-A): `PROIBIDAS_NA_RENOVACAO` é recusada aqui, na config e no pedido.
# 🔴 O `anterior` NÃO tem preset FIXO em `PRESETS`: ele é MONTADO da ficha de cada apólice. Sem as coberturas da ficha,
#    a porta recusa a opção (`PresetIndisponivel`) — nunca a padrão disfarçada de "igual ao ano passado". Pelo mesmo
#    motivo `PRESETS`/`ORDEM` (QCM e cotação) não mudam: a renovação tem a SUA ordem do disparo, abaixo.
ANTERIOR = "anterior"
FRANQUIA_REDUZIDA = "franquia_reduzida"
#: o CÓDIGO da franquia NORMAL (obrigatória) no `calcularV2`. 🔴 Por que 2: 📊 RES "Prata" (topo deste arquivo, 1 corpo
#: da 128) = tipoFranquia 2 "franquia normal"; a escada medida é normal 2 < reduzida 1 (`ESCADA_AUTO`); e a ficha que diz
#: "normal/obrigatória" já vira 2 (`_codigo_da_franquia`). É o valor do `anterior` quando a ficha NÃO diz a franquia.
FRANQUIA_NORMAL = 2
#: a ORDEM do disparo no mesmo negócio da renovação: o `anterior` ABRE (versão 1); as outras são versões dele
OPCOES_DA_RENOVACAO: Tuple[str, ...] = (ANTERIOR, FRANQUIA_REDUZIDA, COMPLETA_MAIS)
PROIBIDAS_NA_RENOVACAO = frozenset({ECONOMICA, MINIMA})


class OpcaoProibidaNaRenovacao(ValueError):
    """Uma renovação pediu a econômica ou a mínima (ou uma opção que não existe na renovação)."""


def conferir_opcoes_da_renovacao(opcoes) -> Tuple[str, ...]:
    """A lista de opções de uma renovação, conferida: 1 a 3, sem repetição, só `OPCOES_DA_RENOVACAO`. ⛔ econômica e
    mínima → `OpcaoProibidaNaRenovacao` (a guarda que a mutação 7 tem de deixar vermelha)."""
    lista = tuple(opcoes or ())
    proibidas = sorted(set(lista) & PROIBIDAS_NA_RENOVACAO)
    if proibidas:
        raise OpcaoProibidaNaRenovacao(f"opção proibida numa renovação: {', '.join(proibidas)}")
    fora = sorted(set(lista) - set(OPCOES_DA_RENOVACAO))
    if fora or not 1 <= len(lista) <= 3 or len(set(lista)) != len(lista):
        raise OpcaoProibidaNaRenovacao(f"as opções da renovação são 1 a 3 de: {', '.join(OPCOES_DA_RENOVACAO)}")
    return lista


# A ESCADA "para cima" de cada CÓDIGO (do pior ao melhor) — os mesmos códigos MEDIDOS do topo deste arquivo (§9.5):
#   📊 franquia normal 2 < reduzida 1 · vidros básico 1 < completo 2 · reserva sem 0 < 7 d 1 < 15 d 2 ·
#   📊 assistência básica 4 < completa 1 (NÃO ordinal). Booleano: False < True. Valor em R$: o número.
ESCADA_AUTO: Mapping[str, Tuple[int, ...]] = {
    "tipoFranquia": (2, 1), "vidros": (1, 2), "carroReserva": (0, 1, 2), "assist24hs": (4, 1),
}


def _nivel(chave: str, valor: object) -> float:
    escada = ESCADA_AUTO.get(chave)
    if escada is not None:
        return float(escada.index(valor)) if valor in escada else -1.0
    if isinstance(valor, bool):
        return 1.0 if valor else 0.0
    return float(valor) if isinstance(valor, (int, float)) else -1.0


def maior(chave: str, a: object, b: object) -> object:
    """O MELHOR dos dois valores de uma chave de cobertura (para cima, nunca para baixo)."""
    return b if _nivel(chave, b) > _nivel(chave, a) else a


def _mil_acima(valor: object) -> int:
    """R$ arredondado para CIMA ao milhar 💭 (o passo que o Agger aceita em RCF/APP não foi medido; o milhar nunca
    fica abaixo do que o cliente tinha)."""
    v = float(valor)
    return int(-(-v // 1000) * 1000)


# O RÓTULO da ficha (já normalizado por `policy_data_provider.normalizar_rotulo`) → a chave do Agger, no AUTO.
# 📊 o que está medido: as linhas "Casco", "Danos Materiais", "Danos Corporais" (Sura AUTO, régua F5 da 130-B,
#    `test_spec130b_costura`). 💭 o resto (morais, APP, vidros, reserva, assistência, a palavra da franquia) é a
#    grafia comum das apólices — ⚠️ P-130B-12 continua: o mapa precisa ser medido contra as fichas AUTO da bancada.
#    Rótulo que nenhuma regra lê não vira nada: fica o preset completo e a marca "não conferido".
def _tem(texto: str, *palavras: str) -> bool:
    ps = set(texto.split())
    return all(p in ps for p in palavras)


def _codigo_da_franquia(texto: str):
    if _tem(texto, "reduzida"):
        return 1
    if any(_tem(texto, p) for p in ("normal", "obrigatoria", "basica", "majorada", "ampliada")):
        return 2            # majorada/ampliada é PIOR que a normal: para cima, a normal (o código 4 não foi medido)
    return None


def _dias(texto: str):
    import re as _re

    m = _re.search(r"(\d{1,3})\s*dias?\b", texto)
    return int(m.group(1)) if m else None


def ler_coberturas_auto(linhas) -> Tuple[Dict[str, object], Tuple[str, ...]]:
    """As coberturas que a ficha DIZ, como chaves do Agger: ({chave: valor}, chaves acima do maior código medido).

    `linhas` = [(rótulo normalizado, limite em R$ ou None, texto da franquia normalizado ou None)]. A mesma chave lida
    duas vezes (cadastro e documento) fica com a MAIOR. Carro reserva acima de 15 dias → 15 dias (o maior código medido)
    e a chave volta em `acima` (o pedido a marca "não conferido": nunca abaixo calado)."""
    lidas: Dict[str, object] = {}
    acima = set()

    def por(chave: str, valor: object) -> None:
        lidas[chave] = maior(chave, lidas[chave], valor) if chave in lidas else valor

    for rotulo, limite, franquia in linhas or ():
        r = str(rotulo or "")
        tem_valor = isinstance(limite, (int, float)) and not isinstance(limite, bool) and limite > 0
        if _tem(r, "franquia") or _tem(r, "casco") or _tem(r, "colisao"):
            cod = _codigo_da_franquia(f"{r} {franquia or ''}")
            if cod is not None:
                por("tipoFranquia", cod)
        if _tem(r, "danos", "materiais") and tem_valor:
            por("isDanosMateriais", _mil_acima(limite))
        elif _tem(r, "danos", "corporais") and tem_valor:
            por("isDanosCorporais", _mil_acima(limite))
        elif _tem(r, "danos", "morais") and tem_valor:
            por("isDanosMorais", _mil_acima(limite))
        elif (_tem(r, "app") or _tem(r, "acidentes", "pessoais")) and not _tem(r, "invalidez") and tem_valor:
            por("isAppMorte", _mil_acima(limite))
        elif _tem(r, "vidros"):
            if _tem(r, "completo") or _tem(r, "completa"):
                por("vidros", 2)
            elif _tem(r, "basico") or _tem(r, "basica"):
                por("vidros", 1)
        elif _tem(r, "reserva") or _tem(r, "carro", "extra"):
            dias = _dias(r)
            if dias is not None:
                if dias > 15:
                    acima.add("carroReserva")
                por("carroReserva", 1 if dias <= 7 else 2)
        elif _tem(r, "assistencia") or _tem(r, "assitencia"):
            if _tem(r, "completa") or _tem(r, "intermediaria"):
                por("assist24hs", 1)            # intermediária → completa (para cima: o código dela não foi medido)
            elif _tem(r, "basica"):
                por("assist24hs", 4)
    return lidas, tuple(sorted(acima))


def _sem_repetidas(por_opcao: Dict[str, Dict[str, object]]) -> Dict[str, Dict[str, object]]:
    """Duas opções com as MESMAS coberturas são um cálculo pago duas vezes: a de trás cede o lugar."""
    saida: Dict[str, Dict[str, object]] = {}
    for o, cob in por_opcao.items():
        if not any(cob == ja for ja in saida.values()):
            saida[o] = cob
    return saida


def coberturas_da_renovacao_auto(lidas: Mapping[str, object], opcoes=OPCOES_DA_RENOVACAO
                                 ) -> Tuple[Dict[str, Dict[str, object]], Tuple[str, ...]]:
    """O corpo de cada opção da renovação de AUTO: ({opção: coberturas}, as chaves do `anterior` NÃO conferidas).

    · anterior          = o preset completo (`padrao`) com o que a ficha DIZ por cima (igual ou maior, nunca menor);
                          a franquia que a ficha NÃO diz = a NORMAL (`FRANQUIA_NORMAL`), não conferida (conserto C2);
    · franquia_reduzida = o anterior com `tipoFranquia` REDUZIDA — se a ficha PROVA que já era reduzida, CEDE o lugar;
    · completa_mais     = o MELHOR de (anterior, padrão) chave a chave + pequenos reparos (D-MC-69)."""
    pedidas = conferir_opcoes_da_renovacao(opcoes)
    desconhecidas = sorted(set(lidas) - set(CHAVES_DE_COBERTURA))
    if desconhecidas:
        raise ValueError(f"cobertura fora do corpo do Agger: {', '.join(desconhecidas)}")
    anterior = dict(_PADRAO)
    # 🔴 conserto C2 (red P3 · juiz P1: 📊 0 de 5 pedidos do canário com a 3ª opção): a ficha que NÃO diz a franquia não
    # herda a REDUZIDA do preset — o `anterior` leva a NORMAL (a obrigatória), marcada não conferida, e a
    # `franquia_reduzida` volta a ser opção PRÓPRIA. Ela só cede o lugar quando a ficha PROVA que já era reduzida.
    anterior["tipoFranquia"] = FRANQUIA_NORMAL
    anterior.update(lidas)
    nao_conferidas = tuple(k for k in CHAVES_DE_COBERTURA if k not in lidas)
    todas: Dict[str, Dict[str, object]] = {
        ANTERIOR: anterior,
        FRANQUIA_REDUZIDA: dict(anterior, tipoFranquia=_PADRAO["tipoFranquia"]),
        COMPLETA_MAIS: dict({k: maior(k, anterior[k], _PADRAO[k]) for k in CHAVES_DE_COBERTURA}, reparoRapido=True),
    }
    return _sem_repetidas({o: todas[o] for o in pedidas}), nao_conferidas


# O GRUPO do catálogo de rótulos (`app/providers/rotulos_de_cobertura.json`, medido na 130-B) → a chave do Agger no RE,
# por ramo. 🔴 Por que está certo (§9.5): cada chave é a da seção "Coberturas" do formulário do ramo
# (`CHAVES_DE_COBERTURA_RE`, 📊 formulario_<ramo>.json) com o MESMO nome da cobertura do grupo. A Básica e a
# assistência ficam fora (a Básica é `risco.valor_basica`; a assistência é da opção). ⚠️ "equipamentos" do condomínio e
# do empresarial NÃO é o grupo `equipamentos_eletronicos` (não medido) — fica fora. Rótulo sem grupo não vira nada
# (P-130B-12 continua para os rótulos fora do catálogo).
CHAVE_DO_GRUPO_RE: Mapping[int, Mapping[str, str]] = {
    16: {"rc_condominio": "isValorCondominio", "rc_sindico": "isValorSindico", "rc_danos_morais": "isDanosMorais",
         "rc_portoes": "isDanosPortoes", "incendio_bens_condominos": "isDanosIncendioRaioExplosaoCond",
         "vidros": "vidros", "roubo_furto_de_bens": "isDanosRoubo", "tumultos": "tumultoGreveLockOut",
         "vendaval": "isDanosVendaval", "ruptura_de_tubulacoes": "isDanosVazamentoTanquesTubulacoes"},
    2: {"rc_familiar": "responsabilidadeCivil", "rc_danos_morais": "isDanosMorais", "vidros": "vidros",
        "roubo_furto_de_bens": "isDanosRoubo", "equipamentos_eletronicos": "isDanosEquipamentosEletronicos",
        "tumultos": "tumultoGreveLockOut", "vendaval": "isDanosVendaval",
        "ruptura_de_tubulacoes": "isDanosVazamentoTanquesTubulacoes"},
    18: {"rc_danos_morais": "isDanosMorais", "vidros": "vidros", "roubo_furto_de_bens": "isDanosRoubo",
         "tumultos": "tumultoGreveLockOut", "vendaval": "isDanosVendaval",
         "ruptura_de_tubulacoes": "isDanosVazamentoTanquesTubulacoes"},
}


def extras_re_da_ficha(ramo: int, linhas) -> Dict[str, float]:
    """`linhas` = [(grupo do catálogo ou None, limite em R$)] → as `extras` do RE ({chave do Agger: R$}); a mesma chave
    duas vezes fica com a MAIOR."""
    mapa = CHAVE_DO_GRUPO_RE.get(int(ramo), {})
    saida: Dict[str, float] = {}
    for grupo, limite in linhas or ():
        chave = mapa.get(str(grupo or ""))
        if chave and isinstance(limite, (int, float)) and not isinstance(limite, bool) and limite > 0:
            saida[chave] = max(float(limite), saida.get(chave, 0.0))
    return saida


def coberturas_da_renovacao_re(ramo: int, valor_basica: float, extras: "Mapping[str, float] | None",
                               opcoes=OPCOES_DA_RENOVACAO) -> Dict[str, Dict[str, object]]:
    """O corpo de cada opção da renovação de RE (a Básica é a do PEDIDO, já reajustada pela config):
    · anterior          = as coberturas típicas do ramo com as da ficha por cima (`extras` VENCEM a opção);
    · franquia_reduzida = ⛔ não existe toggle de franquia medido no RE → a TÍPICA do ramo (laudo I3 §1.3, nota 62);
    · completa_mais     = o melhor de (anterior, típica) chave a chave + assistência COMPLETA (💭 laudo I3 §1.3)."""
    pedidas = conferir_opcoes_da_renovacao(opcoes)
    tipica = coberturas_re(ramo, PADRAO, valor_basica)
    anterior = coberturas_re(ramo, PADRAO, valor_basica, extras=dict(extras or {}))
    mais = {k: max(anterior[k], tipica[k]) for k in anterior}
    mais["assist24hs"] = ASSISTENCIA_RE["completa"]
    todas = {ANTERIOR: anterior, FRANQUIA_REDUZIDA: tipica, COMPLETA_MAIS: mais}
    return _sem_repetidas({o: todas[o] for o in pedidas})


# ======================================================================================================================
# SPEC-129-D — as opções da VIDA INDIVIDUAL (91). 🔴 A FORMA vem do corpo GRAVADO ao vivo (📊 BLOCO 0 M6, 16/10,
# tests/fixtures/agger_ramos/vida_calcularV2_corpo.json) e dos códigos do JS da tela (vida_formulario.json).
# ======================================================================================================================
# 🔴 NENHUM capital fixo: o capital da Morte é SEMPRE o do pedido (a apólice na renovação, o corretor na cotação nova) —
#    capital é escolha do segurado (SUSEP, "seguro de vida"); um padrão seria declarar por ele.
# As opções (§4 da SPEC):
#   · "padrao"   = o capital da Morte + as coberturas do pedido (a apólice / o corretor), e SÓ elas;
#   · "economica" ("mais em conta") = SÓ a Morte, com o MESMO capital — nunca capital menor sem o corretor pedir;
#   · "anterior" (renovação) = o que a apólice tem (as mesmas regras da padrão: as coberturas vêm da ficha).
# 🔴 Por que TODA cobertura vai EXPLÍCITA (zero = não contratada) e nunca "ausente = o padrão da tela": 📊 a TELA copia o
#    capital da Morte para Morte acidental e IPA (`controlerCampos.REPLICAR_COBERTURAS`): na gravação a pessoa digitou só a
#    Morte (R$ 100.000) e o corpo saiu com `isAppMorteAcidental 100000` e `isAppInvalidez 100000`. O "mais em conta" tem
#    de mandar MA = 0 e IPA = 0 — o robô nunca repete o que a tela faz.
#: a chave do CAPITAL da Morte nas coberturas de uma opção (o nome que a porta grava em `multicalculo_calculos.coberturas`)
CAPITAL_DA_VIDA = "capital_morte"
#: as coberturas EXTRAS de vida — as chaves de `configuracoes` do corpo gravado (📊 vida_calcularV2_corpo.json) que são
#: coberturas, com o rótulo da TELA (vida_formulario.json `campos[].rotulo`) ao lado:
CHAVES_DE_COBERTURA_VIDA: Tuple[str, ...] = (
    "isAppMorteAcidental",            # "Morte acidental" — R$
    "isAppInvalidez",                 # "Invalidez permanente (IPA)" — R$
    "isInvalidezDoenca",              # "Invalidez por doença (IFPD)" — R$
    "isDespesasMedicasHospitalares",  # "Diária de Internação Hospitalar (DIH)" — R$ por diária
    "DIT",                            # "Diária de Incapacidade Temporária (DIT)" → configuracoes.DIT.valor — R$ por diária
    "isDoencasGravesGrupo",           # "Doenças graves" → configuracoes.isDoencasGravesGrupo.valor — R$
    "funeral",                        # "Assistência funeral" → configuracoes.funeral.tipo — o TIPO (abaixo), não R$
)
#: 📊 os códigos da "Assistência funeral" do JS da tela (vida_formulario.json `codigos_do_js.assistFuneral`): 0 Sem
#: Assistência (o padrão da tela) · 1 Individual · 2 Familiar. A tela não tem CAPITAL de funeral (`funeral.valor` null no
#: corpo gravado): o valor da extra `funeral` é o TIPO.
FUNERAL_VIDA: Mapping[str, int] = {"sem assistencia": 0, "individual": 1, "familiar": 2}
#: as opções da vida e a ORDEM do disparo no mesmo negócio (a padrão abre; a "mais em conta" é a versão seguinte)
ORDEM_VIDA: Tuple[str, ...] = (PADRAO, ECONOMICA)


def coberturas_vida(opcao: str, capital: float, extras: "Mapping[str, float] | None" = None) -> Dict[str, float]:
    """As coberturas de UM cálculo de vida: {"capital_morte": R$, <extra>: valor}. `padrao`/`anterior` = o capital e as
    extras do pedido; `economica` = SÓ o capital (as extras ficam ZERADAS no corpo por `configuracoes_de_vida`)."""
    if isinstance(capital, bool) or not isinstance(capital, (int, float)) or capital <= 0:
        raise ValueError("o capital da Morte é obrigatório e > 0 (vem do pedido)")
    base = {CAPITAL_DA_VIDA: float(capital)}
    if opcao in (PADRAO, ANTERIOR):
        return {**base, **{str(k): float(v) for k, v in (extras or {}).items()}}
    if opcao == ECONOMICA:
        return base
    raise ValueError(f"opção {opcao!r} não existe na vida (há: {PADRAO}, {ECONOMICA}, {ANTERIOR})")


def _valor_do_corpo(v: float):
    """R$ como o corpo gravado leva (📊 `isAppMorte 100000`, `rendaMensal 8000`: número inteiro quando é inteiro)."""
    f = float(v)
    return int(f) if f.is_integer() else round(f, 2)


def configuracoes_de_vida(coberturas: Mapping[str, object]) -> Dict[str, object]:
    """A parte de COBERTURAS de `cotacao.configuracoes` de vida, TODAS explícitas (zero = não contratada), no formato do
    corpo gravado. Chave fora de `CHAVES_DE_COBERTURA_VIDA` (e do capital) → ValueError: nada é descartado calado."""
    cob = dict(coberturas or {})
    capital = cob.pop(CAPITAL_DA_VIDA, None)
    if isinstance(capital, bool) or not isinstance(capital, (int, float)) or capital <= 0:
        raise ValueError("cobertura sem o capital da Morte")
    desconhecidas = sorted(set(cob) - set(CHAVES_DE_COBERTURA_VIDA))
    if desconhecidas:
        raise ValueError(f"cobertura desconhecida na vida: {', '.join(desconhecidas)}")
    for k, v in cob.items():
        if isinstance(v, bool) or not isinstance(v, (int, float)) or v < 0:
            raise ValueError(f"cobertura de vida com valor inválido: {k}")
    tipo_funeral = cob.get("funeral", 0)
    if tipo_funeral not in set(FUNERAL_VIDA.values()):
        raise ValueError("assistência funeral sem código medido (0 · 1 · 2)")

    def r(chave: str):
        return _valor_do_corpo(cob.get(chave, 0))

    # 📊 a ORDEM e a forma das chaves do corpo gravado (`configuracoes` da entrada 3)
    return {
        "funeral": {"tipo": int(tipo_funeral), "valor": None},
        "isAppMorte": _valor_do_corpo(capital),
        "isAppMorteAcidental": r("isAppMorteAcidental"),
        "isAppInvalidez": r("isAppInvalidez"),
        "isDespesasMedicasHospitalares": r("isDespesasMedicasHospitalares"),
        "isInvalidezDoenca": r("isInvalidezDoenca"),
        "DIT": {"qtdDiarias": None, "valor": r("DIT")},
        "isDoencasGravesGrupo": {"qtdDoencas": None, "valor": r("isDoencasGravesGrupo")},
    }


# O RÓTULO da apólice (InfoCap `/itens.garantias` ou a linha do PDF lida pela ficha única) → a extra de vida. 🔴 Por que
# cada regra (§9.5): 📊 BLOCO 0 M2, os nomes das 15 garantias de VIND lidas na InfoCap: ASSISTÊNCIA FUNERAL 4 · INVALIDEZ
# POR DOENÇA 3 · MORTE ACIDENTAL 2 · MORTE NATURAL 2 · INVALIDEZ POR ACIDENTE 2 · CONJUGÊ-MORTE 1 · INVALIDEZ FUNC PER
# P/DOEN 1 — e o rótulo do campo da TELA de cada extra (acima). Cada regra casa a MESMA cobertura pelas palavras dela:
#   "morte" + "acidental/acidente"  → Morte acidental (a "Morte natural ou acidental" é a BÁSICA: não é extra)
#   "invalidez" + "acidente"        → IPA (a tela: "Invalidez permanente (IPA)" = por acidente)
#   "invalidez" + "doenca/doen"     → IFPD (a tela: "Invalidez por doença (IFPD)"; 📊 "INVALIDEZ FUNC PER P/DOEN")
#   "diaria" + "incapacidade"       → DIT · "diaria" + "internacao/hospitalar" → DIH · "doencas graves" → doenças graves
#   "funeral" + "familiar"/"individual" → o TIPO 2/1. ⚠️ "ASSISTÊNCIA FUNERAL" SOZINHA não diz qual dos dois: fica FORA
#   (escolher seria decidir pelo cliente). "auxílio funeral" é reembolso em R$, não a assistência: fica FORA.
# 💭 DIT/DIH/doenças graves: rótulos da TELA, não medidos na InfoCap (0 linhas no BLOCO 0) — o canário confere.
# ⛔ FORA sempre: a morte/invalidez de OUTRA pessoa (cônjuge, filhos) — o formulário individual não tem esse campo.
# O que nenhuma regra casa volta como SOBRA (o corretor confere: a apólice tem algo que o pedido não leva).
_OUTRA_PESSOA = frozenset({"conjuge", "conjuges", "filho", "filhos", "filha", "filhas", "dependente", "dependentes"})


def _palavras_do_rotulo(rotulo: object) -> set:
    import re as _re
    import unicodedata as _u

    s = "".join(c for c in _u.normalize("NFKD", str(rotulo or "")) if not _u.combining(c)).lower()
    return set(_re.sub(r"[^a-z0-9]+", " ", s).split())


def _extra_do_rotulo(rotulo: object):
    """(chave, valor-fixo) da extra que o rótulo É, ou None. valor-fixo só no funeral (o tipo)."""
    p = _palavras_do_rotulo(rotulo)
    if p & _OUTRA_PESSOA:
        return None
    if "funeral" in p:
        if "auxilio" in p:
            return None
        if "familiar" in p:
            return ("funeral", FUNERAL_VIDA["familiar"])
        if "individual" in p:
            return ("funeral", FUNERAL_VIDA["individual"])
        return None
    acidente = bool(p & {"acidental", "acidente", "acidentes"})
    if "morte" in p and acidente and not (p & {"natural", "qualquer"}):
        return ("isAppMorteAcidental", None)
    if "invalidez" in p and acidente:
        return ("isAppInvalidez", None)
    if "invalidez" in p and (p & {"doenca", "doencas", "doen"}):
        return ("isInvalidezDoenca", None)
    if p & {"diaria", "diarias"} and "incapacidade" in p:
        return ("DIT", None)
    if p & {"diaria", "diarias"} and (p & {"internacao", "hospitalar"}):
        return ("isDespesasMedicasHospitalares", None)
    if (p & {"doencas", "doenca"}) and (p & {"graves", "grave"}):
        return ("isDoencasGravesGrupo", None)
    return None


def coberturas_de_vida_da_ficha_com_sobra(linhas) -> Tuple[Dict[str, float], Tuple[str, ...]]:
    """`linhas` = [(rótulo, capital)] (sem a Morte do segurado — o app a tira antes) → ({extra: valor}, rótulos que NÃO
    viraram extra). A mesma extra com dois valores diferentes não escolhe nenhum: as duas linhas voltam como sobra."""
    achadas: Dict[str, list] = {}
    sobra = []
    for rotulo, capital in linhas or ():
        tem_valor = isinstance(capital, (int, float)) and not isinstance(capital, bool) and capital > 0
        extra = _extra_do_rotulo(rotulo)
        if extra is None or (extra[1] is None and not tem_valor):
            sobra.append(str(rotulo))
            continue
        chave, fixo = extra
        achadas.setdefault(chave, []).append((str(rotulo), fixo if fixo is not None else float(capital)))
    saida: Dict[str, float] = {}
    for chave, lidas in achadas.items():
        valores = {v for _r, v in lidas}
        if len(valores) == 1:
            saida[chave] = valores.pop()
        else:
            sobra += [r for r, _v in lidas]
    return saida, tuple(sobra)


def coberturas_de_vida_da_ficha(linhas) -> Dict[str, float]:
    """O mapa que o app (V2, `pedido._extras_de_vida_da_ficha`) chama: só as extras. A SOBRA (o aviso ao corretor) está
    em `coberturas_de_vida_da_ficha_com_sobra`."""
    return coberturas_de_vida_da_ficha_com_sobra(linhas)[0]
