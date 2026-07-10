# SPEC-032 — Tarefas Realizadas, Conversas unificadas e Arquitetura de canais WhatsApp

**Autor**: Fable 5 (líder técnico) · 2026-07-10 · **Status**: PLANEJADA (executar junto/apos o REORG SPEC-022)
**Origem**: pedidos do founder em 2026-07-10 + riscos que eu (líder) adiciono. NADA aqui cria motor paralelo.

## A. Página "Tarefas Realizadas" (global)
Um lugar único com TUDO que os agentes fizeram: cobranças, atendimentos, rotinas, relatórios, acionamentos.
- **Fonte de dados**: já existe quase tudo — `routine_runs` (rotinas/auxiliares), `portal_jobs` (portais),
  sessões de atendimento (conversations), sessões de dispatch (acionamentos), relatórios do Chat Principal.
  Criar uma VIEW/endpoint `activity_feed` que normaliza: {tipo, agente, título, resumo, status, quando, link_detalhe}.
- **UI**: página "Tarefas" no menu. Filtros por TIPO (Atendimento | Auxiliar X | Cobrança | Relatório | Acionamento)
  e por período. Clique no item → drawer com o resumo do que foi feito (não JSON cru).
- **Futuro (não construir agora, mas não fechar portas)**: rotina semanal "sábado 9h" que agrega o feed e manda
  ao corretor o relatório-vitrine: "55 atendimentos, 32 cotações, 8 cobranças…" — vira UMA rotina normal do
  motor SPEC-019 (sem estrutura nova).

## B. Execuções por auxiliar (modal, não poluição inline)
- Remover a lista de resultados espremida embaixo do card do auxiliar (hoje ilegível).
- Botão "Ver execuções" no card → modal com lista (data, status, resumo curto). Clique no item → detalhe
  (o mesmo componente de detalhe do feed global — construir UMA vez, usar nos dois lugares).

## C. Conversas — onde ficam e como se organizam
- Hoje: card "Conversas" dentro de Atendimentos (só conversas do atendente) + espelho de dispatch.
- Alvo: página **"Conversas"** própria no menu (não dentro de Atendimentos), com abas/filtros:
  **Atendimento** (segurados) · **Seguradoras** (dispatches, espelho read-only) · **Auxiliares** (mensagens
  enviadas por rotinas: boletos, relatórios) · futuro: Leads.
- O histórico do Chat Principal continua página própria (é outro contexto: founder↔plataforma).
- Auxiliares hoje não têm espelho de conversa: registrar envios das rotinas (boleto/relatório) numa
  timeline consultável (tabela leve `outbound_log`: canal, para, tipo, rotina, quando, status). Isso também
  alimenta o feed de Tarefas e a auditoria anti-bloqueio.

## D. Arquitetura de canais WhatsApp (o buraco mais embaixo)
Problema real: HOJE um único número (QR Evolution) faz atendimento E rotinas E boletos E relatórios.
Riscos: mistura de contexto (inbound de cliente vs. resposta de URA vs. "ok" de relatório), volume/ban,
identidade confusa, e o webhook precisa adivinhar quem é quem.

**Decisão recomendada (multi-instância por PAPEL):**
1. Tabela `channels` por corretora: {instance_id Evolution, papel: atendimento | operacional | notificacoes,
   phone, status}. O webhook resolve o papel pela instância — roteamento determinístico, sem adivinhação.
2. Dashboard → Conectores: botões separados "WhatsApp Atendimento" (QR), "WhatsApp Auxiliares" (QR),
   "WhatsApp Oficial (Meta)". Corretora pequena pode usar 1 número para tudo (papel combinado) — mas o
   padrão recomendado é separar atendimento (inbound de clientes) do operacional (boletos/relatórios/URA).
3. **Rotinas por usuário**: rotina ganha `owner_user_id` + `deliver_to` (telefone do usuário). Envios de
   rotina saem SEMPRE pela instância "operacional". Cada usuário da corretora vê/gerencia as próprias rotinas.
4. **Anti-bloqueio** (obrigatório no motor de envio): rate-limit por número (fila com espaçamento 20-60s),
   warm-up de número novo (volume crescente), rodapé pedindo interação ("responde com um 👍 pra confirmar
   que recebeu"), opt-out respeitado, e NUNCA disparar dezenas de boletos num número recém-pareado.
5. **Telegram** como canal alternativo para rotinas INTERNAS (relatórios ao dono/funcionários): sem risco de
   ban e grátis — oferecer escolha por rotina (whatsapp | telegram). Cliente final continua WhatsApp.
6. **Chatwoot**: avaliado e NÃO recomendado agora — traria inbox multi-atendente pronto, mas duplica UI e
   seam de mensagens (contra a regra "sem estrutura paralela"). Nossa página Conversas evolui no lugar.

## E. Riscos que o founder ainda não viu (adiciono como líder)
1. **Debounce de digitação**: o atendente responde antes de o cliente terminar (visto no teste). Implementar
   buffer por conversa no webhook: agrega mensagens por ~10s (ou até parar de digitar) antes de invocar o
   agente; responde ao CONJUNTO. Também dedup de webhooks repetidos da Evolution (message_id).
2. **Janela de 24h da Meta** (canal oficial): mensagens fora da janela exigem template aprovado — o motor de
   rotinas precisa saber em qual canal está para não falhar silenciosamente.
3. **Identidade**: mensagens de auxiliares devem se apresentar ("Sou o assistente da {corretora}") — nunca
   parecer um humano que depois não responde.
4. **Auditoria**: todo envio automático logado (outbound_log) — LGPD, disputa com cliente, e debug.
5. **Reconexão**: instância Evolution cai silenciosamente → healthcheck por instância + alerta no dashboard
   ("WhatsApp Auxiliares desconectado há 2h") + retry de fila.
6. **Multi-tenant**: tudo acima por corretora (channels, filas, limites) — nada global.

## F. Ordem de execução
1. (agora, já feito em 2026-07-10) qualidade do atendente + corredores + modelo.
2. REORG SPEC-022 + este SPEC-032 juntos: menu novo (Tarefas, Conversas), modal de execuções, channels.
3. Anti-bloqueio/debounce entram com o motor de envio unificado (outbound_log) — pré-requisito para escalar cobrança.
