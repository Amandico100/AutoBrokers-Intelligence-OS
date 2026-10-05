# -*- coding: utf-8 -*-
"""O multicálculo do lado do smith-api — SPEC-129-B U2 (a PORTA).

    porta.py        MulticalculoProvider: calcular · consultar · recalcular · cancelar · capacidades
    pedido.py       PedidoDeCalculo (saneado) · de_apolice (a renovação a partir da ficha da InfoCap)
    repositorio.py  o acesso a multicalculo_* (migration 20261005_01), SEMPRE com o filtro do solicitante

A porta só ENFILEIRA (`multicalculo_calculos` é a fila, D-129B-01). Quem calcula é o motor do portal-worker
(`portal_worker/multicalculo/motor.py`). Os TIPOS do cálculo vêm de `portal_worker/multicalculo/contrato.py`
(um catálogo só). Nenhum cliente de modelo (LLM) mora aqui (§8 da SPEC: custo de modelo zero).
"""
from app.services.multicalculo.pedido import PedidoDeCalculo, de_apolice  # noqa: F401
from app.services.multicalculo.porta import (  # noqa: F401
    Andamento,
    ChaveAusente,
    MulticalculoProvider,
    NaoAutorizado,
    NaoEncontrado,
    OrigemRecusada,
    PedidoAberto,
    PedidoIncompleto,
    PerfilIncompleto,
    PresetIndisponivel,
)
