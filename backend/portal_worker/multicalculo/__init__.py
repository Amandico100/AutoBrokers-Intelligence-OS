# -*- coding: utf-8 -*-
"""O contrato do cálculo multisseguradora — SPEC-128 U2.

Mora no worker porque a imagem do worker copia só `backend/portal_worker`
(`portal_worker/Dockerfile`) e o worker não importa `app.*`. O adaptador do
motor (129-B) vive aqui; a porta da API importa os TIPOS deste pacote.

    contrato.py      os tipos: PedidoDeCalculoAuto · Ajuste · Oferta ·
                     RespostaDaSeguradora · RodadaDoCalculo · Evento
    leitor_agger.py  ler_rodada(json) → RodadaDoCalculo ·
                     eventos_entre(a, b) → [Evento] · a LISTA BRANCA de
                     caminhos que o gerador de fixtures também usa

Puro: sem rede, sem banco, sem import de `app.*`.
🔴 Ninguém do produto chama isto ainda — por desenho: quem liga é o adaptador
da 129-B (pendência de costura da SPEC-128).
"""
