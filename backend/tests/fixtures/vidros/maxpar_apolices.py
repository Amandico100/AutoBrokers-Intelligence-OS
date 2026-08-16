# -*- coding: utf-8 -*-
"""Preflight de apólice — `GET /apolices` e o 400 de cobertura ausente.

ORIGEM
------
APOLICE_OK ............. YELUM har entry 120, status 200  (Seguradora=LIBERTY)
APOLICE_OK_PORTO ....... PORTO har entry 128, status 200  (Seguradora=PORTO)
COVERAGE_ABSENT_PORTO .. PORTO RODA SEM COBERTURA har entry 86, status **400**
                         Corpo LITERAL — não contém PII.

APOLICE_NAO_ENCONTRADA e APOLICE_AMBIGUA são **SINTÉTICAS**: não ocorrem em
nenhum dos três HARs. Construídas a partir do schema de `APOLICE_OK`, virando a
flag correspondente. Marcadas aqui para ninguém as citar como medição.

SANITIZAÇÃO: CPF, nome, placa, chassi e apólice substituídos por sintéticos de
mesmo formato. Telefones são 0800 público da seguradora. Descrição do veículo é
dado de domínio, preservada.

🔴 O QUE ESTE ARQUIVO PROVA
===========================
Que `coverage_absent` é detectável **antes de qualquer escrita**. No HAR da
Porto o fluxo inteiro tem 96 entries e apenas 2 chamadas de API; a segunda
devolve 400 e **nenhum atendimento nasce**. O gate de preflight é o que separa
"consultar" de "criar".
"""
from __future__ import annotations

APOLICE_OK = {
    "ApoliceNaoEncontrada": False,
    "MaisDeUmaApoliceEncontrada": False,
    "NomeSegurado": "CLIENTE DE TESTE",
    "NomeSocial": None,
    "Placa": "Q***A91",
    "Apolice": "******999999999",
    "NumeroDaApolice": "055309999999999",
    "DescricaoVeiculo": "COMPASS LIMITED 2.0 4X2 16V AUT.",
    "Chassi": "9BW*******T004251",
    "TelefoneSeguradora": "0800 777 3311",
    "Movimento": "I",
    "CodigoSeguradora": 56,
    "ApoliceFrotaAllianz": False,
}

APOLICE_OK_PORTO = {
    "ApoliceNaoEncontrada": False,
    "MaisDeUmaApoliceEncontrada": False,
    "NomeSegurado": "CLIENTE DE TESTE",
    "NomeSocial": None,
    "Placa": "Q***A91",
    "Apolice": "******9999999",
    "NumeroDaApolice": "0553099999999",
    "DescricaoVeiculo": "KIA SPORTAGE EX 2.0 16V 142CV AUT.",
    "Chassi": "9BW*******T004251",
    "TelefoneSeguradora": "11 3337-6786",
    "Movimento": None,
    "CodigoSeguradora": 128,
    "ApoliceFrotaAllianz": False,
}

# SINTÉTICA — schema de APOLICE_OK com a flag virada.
APOLICE_NAO_ENCONTRADA = {
    "ApoliceNaoEncontrada": True,
    "MaisDeUmaApoliceEncontrada": False,
    "NomeSegurado": None, "NomeSocial": None, "Placa": None, "Apolice": None,
    "NumeroDaApolice": None, "DescricaoVeiculo": None, "Chassi": None,
    "TelefoneSeguradora": "0800 777 3311", "Movimento": None,
    "CodigoSeguradora": 56, "ApoliceFrotaAllianz": False,
}

# SINTÉTICA — idem.
APOLICE_AMBIGUA = {
    "ApoliceNaoEncontrada": False,
    "MaisDeUmaApoliceEncontrada": True,
    "NomeSegurado": None, "NomeSocial": None, "Placa": None, "Apolice": None,
    "NumeroDaApolice": None, "DescricaoVeiculo": None, "Chassi": None,
    "TelefoneSeguradora": "0800 777 3311", "Movimento": None,
    "CodigoSeguradora": 56, "ApoliceFrotaAllianz": False,
}

COVERAGE_ABSENT_PORTO_STATUS = 400
COVERAGE_ABSENT_PORTO = {
    "Message": ("A apólice do veículo informado não possui cláusula de "
                "Roda, Pneu e Suspensão contratada"),
    "Tipo": "RegraDeNegocioExcecao",
}

# SINTÉTICA — mesma classe de exceção, outra regra. Existe para provar que o
# classificador NÃO trata `RegraDeNegocioExcecao` como sinônimo de
# `coverage_absent`: `Tipo` é enum ABERTO, e regra nova tem de parar, não passar.
OUTRA_REGRA_DE_NEGOCIO = {
    "Message": "Atendimento indisponível para este produto no momento",
    "Tipo": "RegraDeNegocioExcecao",
}
