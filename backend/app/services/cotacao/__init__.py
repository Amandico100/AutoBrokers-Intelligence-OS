# -*- coding: utf-8 -*-
"""A COTAÇÃO RÁPIDA pelo chat — SPEC-132-B (fatia B1).

    pedido_da_conversa   o que o corretor disse (+ a placa, + a apólice anexada) → `PedidoDeCalculo` e o que FALTA
    confirmacao          o `confirmacao_id` de uso único (30 min) entre o resumo e o "sim"
    workflow             o Work Run `cotacao.chat`: espera o motor, publica, ESCREVE a resposta na MESMA conversa
    resposta             as frases e a tabela que o corretor lê no chat

⛔ Nada aqui calcula: o cálculo é da PORTA (`multicalculo.porta.MulticalculoProvider`) e do motor (CLAUDE.md §5).
"""
