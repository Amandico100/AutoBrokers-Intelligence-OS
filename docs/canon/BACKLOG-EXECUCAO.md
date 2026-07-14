# BACKLOG DE EXECUÇÃO — consolidado vivo (atualizado 2026-07-14)

> Fonte única do que FALTA, varrido das SPECs 020-036. Atualizar a cada entrega.
> Legenda: 🔑 = depende do founder · 🤖 = Fable executa · 📅 = pós-testes

## 1. 🔑 NA MÃO DO FOUNDER (destrava o resto)
- [ ] Confirmar números divergentes com as atendentes (Bradesco 21 4004-2702? · HDI 11 99524-8188? · Tokio 11 99578-6546? · Yelum 11 3206-1414?) → Fable atualiza o Registro em 1 min.
- [ ] Número/chip exclusivo do CARTÓGRAFO (nunca produção) → estágio 1 do runbook GO.
- [ ] Apólices de teste no formato combinado (seguradora EMISSORA, ramo, CPF, nome, placa/CEP, nº, vigência) — ideal 2 por seguradora × ramo.
- [ ] Iniciar o chat RAG paralelo (kit: PROMPT-NOVO-CHAT-RAG.md) e popular a Biblioteca Global.
- [ ] RETESTES de atendimento: Porto (bateria fim-a-fim), Azul (do zero — teste-chave), Zurich (inaugural). Vidros E2E depois.
- [ ] Yelum reteste (~15/07, janela de 72h da URA).
- [ ] Stripe REAL (chaves produção) → destrava auto-provisioning de corretora pós-assinatura.
- [ ] Verificar no grupo de suporte se os dossiês/alertas do Vigia chegam (validação em incidente real).

## 2. 🤖 FABLE — pendências técnicas das SPECs
### SPEC-034 (harness)
- [ ] Fiação do Cartógrafo com a instância Evolution GO dedicada (motor pronto; falta número 🔑) + primeiro mapa real (Porto) + ativação.
- [ ] Evolution GO estágio 2 (número do atendente de teste) ANTES dos retestes; estágio 3 (produção) 📅.
- [ ] Ligar LLM-judge amostrado do Auditor (AUDITOR_LLM/SAMPLE) após ~1 semana de dados heurísticos 📅.
- [ ] GEPA/DSPy nos prompts (caso Nubank) — só depois do Auditor estabilizar 📅.
- [ ] ACL dono vs funcionário (§6.6-A: papéis + guard fail-closed no financeiro InfoCap) — antes de escalar nº de corretoras 📅.
- [ ] Graduar corredores validados p/ finalize LIVE (DISPATCH_FINALIZE_LIVE_PLAYBOOKS) conforme retestes passarem.
### SPEC-035/036 (admin/dashboard)
- [ ] Reskin fino das páginas legadas mantidas (companies/conversations/finops internos) no DS novo — cosmético, sem pressa.
- [ ] SPEC-022 fatia final: página de detalhe por seguradora com 3 abas embutidas (Canais/Portais/Corredores) + campo de logo.
- [ ] **Página "Tarefas executadas" + mensagem semanal de valor** (pedido do founder na reorg/SPEC-032): lista de TUDO que os agentes fizeram (51 atendimentos, 86 cobranças, X follow-ups...) + msg de sábado à corretora "olha quanta coisa fizemos por você" — infra pronta (heartbeats/scorecards/insights contam tudo); falta a página + o compositor da mensagem.
- [ ] Painel semanal/digest p/ o founder (nota média, deflexão, intervenções da Sentinela) — dados já gravados.
- [ ] Memórias v2: cadeado por plano ATIVO (gating real), painel com resumo do conteúdo, conectores de e-mail (Gmail/Outlook) alimentando a camada pessoal.
- [ ] Auto-provisioning assinatura→empresa+dashboard (bloqueado por Stripe 🔑).
### SPECs anteriores (varridas, não esquecer)
- [ ] SPEC-032: arquitetura tarefas/conversas WhatsApp (multi-número por função S17-12; UI de propósito por número).
- [ ] SPEC-021: metering/planos de consumo (Camada aprendizado JÁ adiantada pelo Auditor).
- [ ] SPEC-024/025: vidros ponta a ponta — candidato forte: portal abraseuatendimento (11 seguradoras) via Playwright/API-first (SPEC-033).
- [ ] SPEC-020/023B: pendências de portais/cobrança listadas na 023B (revisar quando voltar à cobrança).
- [ ] Sinistro por WhatsApp (founder adiou 13/07 — futuro).
- [ ] IA de Sugestões: pesquisa semanal profunda (novas leis, benchmarking entre corretoras) como evolução do conteúdo.

## 3. 📅 Ordem recomendada
1. Founder entrega itens 🔑 (números, apólices, confirmações) → fiação Cartógrafo + GO estágio 2.
2. RETESTES (Porto/Azul/Zurich) com dashboard ao vivo.
3. Graduação de corredores p/ LIVE + semana de sombra dos agentes → 1º digest.
4. Página Tarefas Executadas + mensagem semanal de valor (retenção!).
5. Vidros E2E + SPEC-022 final + reskin.
6. Stripe real → auto-provisioning → escala comercial.
