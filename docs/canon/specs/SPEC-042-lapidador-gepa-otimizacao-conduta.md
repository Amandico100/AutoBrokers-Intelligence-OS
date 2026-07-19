# SPEC-042 — Lapidador: otimização reflexiva de conduta (padrão GEPA/DSPy)

> Aprovada pelo founder em 19/07/2026. Executada pelo chat líder após a
> SPEC-040. Referências: GEPA (Genetic-Pareto, gepa-ai/gepa), DSPy, caso
> Nubank/Decagon (LLM-judge otimizado: 68,9%→88,9% de acurácia; +37pp NPS).

## O que é (em linguagem humana)

O GEPA é o padrão de "otimização reflexiva": em vez de um humano reescrever
prompts no olho, o sistema pega o FEEDBACK TEXTUAL das falhas reais ("re-pediu
CPF", "repetiu mensagem", "cliente frustrado"), reflete sobre ele com um
modelo forte, propõe uma versão MELHOR do playbook, e uma avaliação decide se
a nova versão supera a atual. Uma frase de feedback vale mais que uma nota:
"você confundiu X com Y" ensina; "nota 0,5" não.

## Como encaixa na nossa arquitetura (SEM estrutura paralela)

O Lapidador é o Alfaiate na sua forma final — ele NÃO cria caminho novo:
produz DRAFTS de conduct_playbooks (tabela da Onda 3) que passam pelo GATE da
Onda 4 (checks determinísticos + juiz nunca-regredir + Conselho opcional).
Auto-evolução com rede dupla: o Lapidador propõe, o gate decide, o rollback
protege, a Sentinela de Regressão vigia o resultado em produção.

## Pipeline (v1, sem dependência nova — o padrão GEPA na nossa stack)

1. **Coleta de feedback** (determinística, grátis): sessões destiladas com
   nota baixa + flags do Auditor (conversation_scorecards) + flags das
   sessões, por (ramo, serviço). Feedback = texto, não número.
2. **Reflexão** (modelo FORTE, DISTILLER_STRONG_MODEL): recebe o playbook
   ATIVO + o feedback de falhas + as condutas douradas → propõe o candidato
   otimizado (JSON no schema do playbook), explicando o que mudou e por quê.
3. **Seleção** (o gate da Onda 4 é o nosso Pareto): o candidato só assume se
   o juiz o pontuar >= atual. Reprovado = descartado com registro.
4. **Cadência**: semanal (madrugada) quando houver feedback novo suficiente
   (env LAPIDADOR_MIN_FEEDBACK, default 5) + gatilho manual
   `POST /api/admin/atlas/espelho/optimize`.

## Fase 2 (registrada, não executada agora)

- Otimizar o PRÓPRIO LLM-judge (calibração estilo Nubank) quando houver
  massa de scorecards com revisão humana.
- Biblioteca gepa/dspy formal se o volume justificar (hoje: nossa stack).
- Estender o padrão ao Chat Principal (prompts de estratégia) pós-testes.

## Custo

Reflexão = 1 chamada forte por (ramo, serviço) por semana COM feedback novo
(~R$0,50-0,80 cada). Sem feedback novo = zero. Rastreado no FinOps.
