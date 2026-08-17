# -*- coding: utf-8 -*-
"""Portal Intelligence Lab — SPEC-077.

Instrumentos de ENGENHARIA que vivem dentro da Portal Capability Factory da
SPEC-075. Nada aqui é Skill de negócio, nada aqui aparece para o corretor, e
nada aqui roda no caminho de um acionamento.

🔴 Por que o Lab mora em `app/services/portals/` e NÃO em `portal_worker/`
==========================================================================
O `Dockerfile` do portal-worker copia só `backend/portal_worker`. O que mora
aqui **não entra na imagem do worker** — e é exatamente o que se quer: análise
offline de tráfego não tem por que viajar junto com o Chromium.

A exceção é o `DeepTrace`, que observa uma página ao vivo e por isso mora em
`portal_worker/deep_trace.py`. A regra é simples: **o que observa fica com quem
navega; o que analisa fica com quem tem tempo.**

O que este pacote NÃO é
=======================
Não é um segundo runtime. Não é uma segunda Factory. Não é um segundo redator
(usa `portal_worker.redaction`). Não é um segundo registry de journeys.
Não depende do `browse` CLI, de Node, de Stagehand nem de Browserbase.
"""
