# -*- coding: utf-8 -*-
"""O canal de cotação ao consumidor (Quem Cobra Menos no WhatsApp) — SPEC-133-A.

A porta de entrada (F1): `entrada.turno` (filtros → estado → conversa → envio), `repositorio` (convidados, limite,
anti-laço, consentimento, lead, estado CIFRADO) e `envio.enviar` (balões pela integração do CANAL).
A conversa e a cotação (F2): `conversa.responder`, `cotacao.disparar`.

⚠️ Sem imports aqui de propósito: `app.api.webhook` importa `canal.repositorio`/`canal.entrada` de forma tardia, e um
import ansioso daqui puxaria `conversa`/`cotacao` (e o Work OS) para dentro do webhook de TODAS as corretoras.
"""
