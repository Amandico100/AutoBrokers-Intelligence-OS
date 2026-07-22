# SPEC-038 — ATLAS: plano DEFINITIVO (Observador + fábrica de mapas de URA)

> Fase 2 (força máxima) — Fable, 18/07/2026. Sucede o RASCUNHO (mesmo diretório),
> que contém a fundamentação e os fatos verificados no código-fonte do GO.
> STATUS: plano aprovável — NADA construído até liberação explícita do founder.

## DECISÕES DO FOUNDER (18/07 — cravadas)

- **D1 Números:** dos WhatsApps de trabalho da corretora. **WhatsApp Business
  pode parear normalmente por QR. Algumas contas podem exigir passkey por
  decisão server-side.** Corretoras futuras podem variar → checklist
  pré-pareamento obrigatório (abaixo).
- **D2 Histórico:** IMPORTAR via HistorySync, com duas condições absolutas:
  (a) qualidade — as IAs não podem se confundir na análise (merge conservador:
  histórico só contribui arestas de alta confiança; ambíguo = descartado, nunca
  chutado); (b) **os celulares ficam INTACTOS — nada é apagado/alterado/lido**.
- **D3 Automação:** Atlas auto-atualiza SEMPRE; playbooks auto-aplicam SÓ se
  passarem no Simulador; founder é acordado apenas em mudança estrutural
  (dado novo exigido, app nativo, seguradora nova).
- **D4 HDI:** teste ativo do Cartógrafo ADIADO — o Observador captura um HDI
  real de atendente com risco zero. Cartógrafo fica armado para lacunas.

## GARANTIA "MODO COFRE" (a resposta técnica ao D2b — por construção)

O pareamento é um **aparelho companheiro somente-leitura por decisão nossa**:
1. A rota observer **não possui caminho de envio** (o handler não recebe
   `send`; é estruturalmente mudo — não é uma flag, é ausência de código).
2. Advanced settings da instância observer (existem no GO, verificado):
   `readMessages=false` (NUNCA marca as mensagens dela como lidas),
   `alwaysOnline=false` (NUNCA aparece online no lugar dela),
   `rejectCall=false` (NUNCA rejeita ligações dela),
   `ignoreGroups=true`, `ignoreStatus=true`.
3. HistorySync é **cópia por protocolo** — ler o histórico não move nem apaga
   nada no telefone (mesmo mecanismo do WhatsApp Web ao conectar).
4. Nenhuma API de delete/edit/label é chamada em instância observer (lint de
   arquitetura: o módulo observer não importa nenhum cliente de escrita).

## PESQUISA BUSINESS/PASSKEY (18/07 — atualiza a D1; fontes verificadas)

**Diagnóstico corrigido:** o bloqueio que o founder viu NÃO é "Business não
pareia". O que existe é o **travamento por PASSKEY** — decisão **server-side,
POR CONTA** (bucket A/B da Meta + conta ter passkey + sinal de risco). A
"senha" que apareceu era a cerimônia de passkey (WebAuthn). Fatos:
1. Apps Business SEM o travamento pareiam por QR normalmente (WhatsApp Web
   funciona em Business — mesmo mecanismo).
2. A **Evolution API v2 (antiga) NÃO suporta a cerimônia** — issue #2618
   aberta, sem correção. Beco sem saída lá.
3. O **Evolution GO 0.7.2+ IMPLEMENTOU a cerimônia completa** (guia
   `passkey-pairing.md` + extensão `passkey-helper/` no repo): eventos
   `PairPasskeyRequest/Confirmation`, endpoints `/passkey-ceremony/{token}`,
   extensão Chromium que roda em web.whatsapp.com. Requisitos: env
   `PASSKEY_PUBLIC_URL` no GO, extensão instalada no Chrome/Edge, e a DONA da
   conta presente (biometria/celular por perto), ~2 min, UMA vez. Sem bypass
   headless (confirmado por pesquisa independente citada no guia). Recurso
   novo, "não validado ponta a ponta" pela comunidade — tratar como
   experimental até o nosso primeiro sucesso.
4. **Plano C — conversão oficial Business→Messenger** (FAQ oficial do
   WhatsApp): mesmo celular, mesmo número, fluxo dentro do app
   (Configurações → Conta → Mudar para o WhatsApp Messenger), transfere os
   dados da conta/conversas; PERDE ferramentas comerciais (catálogo,
   etiquetas, respostas rápidas, mensagens automáticas). Fazer backup antes;
   JAMAIS desinstalar antes de migrar.

**Estratégia em cascata por atendente:** (A) tentar QR normal no GO — pode
simplesmente funcionar, Business ou não; (B) se pedir passkey → cerimônia do
GO com a atendente presente; (C) último recurso → conversão oficial para
Messenger (decisão da corretora; perde ferramentas Business).

## CHECKLIST PRÉ-PAREAMENTO (por número, no onboarding)

- [ ] Tentativa 1: QR normal no GO (funciona p/ Business sem travamento).
- [ ] Se pedir passkey: GO 0.7.2+, env `PASSKEY_PUBLIC_URL`, extensão
      `passkey-helper` no Chrome/Edge, atendente presente c/ celular (2 min).
- [ ] Último recurso: migração oficial Business→Messenger (backup antes).
- [ ] Slot de aparelho vinculado livre (limite ~4: Web/tablet contam).
- [ ] Termo de consentimento da atendente assinado (LGPD; corretora=controladora).
- [ ] Número das seguradoras que ela usa conferidos no registry (senão o filtro
      de borda descartaria — Descobridor cobre o residual).
- [ ] Confirmar com a atendente: nada muda no uso do celular dela.

## ARQUITETURA DE EXECUÇÃO (arquivos e mudanças — nível implementação)

### Onda 0 — SPIKE de verificação (DECISÃO 18/07: no número do founder, já pareado)
Sem chip novo: usa o **554796274743** (pessoal do founder, JÁ pareado no GO como
canal de teste — nada em produção real). Proteções para o número pessoal:
- O filtro de borda vale DESDE O PRIMEIRO EVENTO: só conversas com números de
  seguradora do registry são processadas; amigos/grupos/status = descartados na
  primeira linha (só contadores). Nenhuma automação nova sobre as mensagens dele.
- Even continua limitada à allowlist atual (só responde ao 7463).
Verificações:
- [ ] `Message` com `IsFromMe=true` chega no webhook (founder digita no aparelho).
- [ ] Protobuf interativo completo chega (founder abre a URA da Yelum/HDI e navega).
- [ ] **Eco de resposta interativa** SEM risco: testar numa SELEÇÃO DE LISTA
      inicial do menu (nunca no formulário final) + saída educada — se o clique
      de lista ecoa, temos o mecanismo; o nfm_reply do formulário final será
      capturado depois, do tráfego real das atendentes (risco zero de acionar).
- [ ] Shape real do `HistorySync`: assinar HISTORY_SYNC + testar
      `POST /chat/history-sync` (endpoint existente no GO) OU re-parear.
- [ ] Modo cofre: mensagens NÃO marcadas como lidas / sem "online" indevido.
Saída: relatório GO/NO-GO por item + ajuste fino do plano.

### Onda 1 — CAPTURA (código puro)
- `backend/app/services/atlas/observer_intake.py` (novo): handler mudo;
  filtro de borda (allowlist = insurer_registry + extras por corretora; DROP
  do resto com contador-somente); resolve counterparty→insurer_key; grava
  `observed_events`; correlaciona `session_hint`.
- `backend/app/api/webhook.py`: na rota `evolution-go/{token}`, se
  `integration.purpose == "observer"` → `observer_intake.handle()` e retorna
  (ANTES de normalizador/buffer/Even — caminho quente do atendimento intocado).
- `backend/app/api/whatsapp_channel.py`: setup multi-instância observer —
  `POST /instance/create` (global key, token nosso por instância,
  advancedSettings do modo cofre) + `/instance/connect` com
  `subscribe: ["MESSAGE","CONNECTION","HISTORY_SYNC"]` + webhookUrl token
  próprio; integração `purpose="observer"`, `agent_id=NULL`.
- Migração SQL: `observed_events` + `observed_sessions` (tenant-scoped, RLS
  service-only), índices por (company_id, insurer_key, wa_timestamp).
- HistorySync: mesmo intake com `source='history_sync'` (D2: merge conservador).
- Vigia: inclui instâncias observer no health (queda → alerta re-parear;
  evento `TemporaryBan` → alerta imediato ao grupo).

### Onda 2 — TECELÃO (sessões → mapa)
- `backend/app/services/atlas/sessionizer.py`: corta sessões por
  (corretora × número seguradora): janela de silêncio >2h OU saudação de URA;
  detecta entrelaçamento (2 clientes na mesma conversa) por protocolo/menus.
- `backend/app/services/atlas/templater.py`: PII → placeholders {CPF} {PLACA}
  {NOME} {ENDERECO} {PROTOCOLO} {DATA} (regex determinístico; Haiku só p/
  resíduo ambíguo). REUSA `normalize_screen_text`/`node_hash`/`parse_options`
  do cartographer + `_interactive_from_message` do inbound.
- `backend/app/services/atlas/weaver.py`: constrói arestas
  (tela_A --resposta/clique humano--> tela_B) e faz MERGE versionado em
  `ura_maps` (+colunas: source, version, provenance jsonb, coverage jsonb,
  confidence por aresta: confirmada ≥2 observações; 1x = "vista 1 vez").
  Conflito de merge → Sonnet com contexto das variantes; sem resolução →
  fila de revisão (nunca corrompe o ativo).
- Ramo/serviço inferidos PELA ROTA (labels), não pelo número.
- Job: processamento por sessão encerrada + consolidação noturna (cron).

### Onda 3 — PÁGINA ATLAS (admin-only)
- `app/admin/atlas/page.tsx` (+ `AtlasClient.tsx`): cards premium por
  seguradora (padrão existente) → abas por ramo → árvore SVG hierárquica por
  serviço (layout por profundidade; sem lib externa). Cores: 🟢 completa
  validada · 🟡 parcial (com lista "não vimos: X, Y") · 🔴 drift · 🟣 app
  nativo · ⚪ nunca visto. Filtros (seguradora/ramo/serviço/status/fonte/
  corretora-sensor/frescor) + % cobertura + clique-no-nó (tela sem PII,
  variantes, last_seen, nº sessões).
- **Feed "O QUE FALTA"**: endpoint + card priorizado (para repassar às
  atendentes). API: `app/api/admin (proxy) → backend /api/admin/atlas/*`
  (require_master_admin em TUDO — corretora nunca vê).

### Onda 4 — AUTO-ATUALIZAÇÃO (D3)
- `backend/app/services/atlas/route_sentinel.py`: diff contínuo observado ×
  Atlas ativo → `route_drift` (cosmético×estrutural — Haiku; evidência
  antes/depois); Atlas: aplica sempre (verdade observada, versão nova).
- Alfaiate v2 (`playbook_tailor.py` estendido): patch do playbook a partir do
  drift + respostas humanas reais → **GATE: ura_simulator replay contra o mapa
  novo** → passou = aplica + registra em Atividades; estrutural/reprovado =
  alerta ao founder com diff pronto (1 clique).
- Escalada: app nativo mudou / seguradora nova / dado novo exigido → grupo
  WhatsApp (caminho do Vigia, já validado).

### Onda 5 — ONBOARDING + MINERAÇÃO
- Admin "Modo Observação" por corretora: parear números (QR), checklist
  pré-pareamento, status (conectado/eventos hoje/sessões), delta de cobertura
  ("contribuiu X rotas novas"), flag de modo (observe_only|hybrid|full → Even).
- Garimpo v2: minera PARTE 1 (cliente↔corretora no número oficial): FAQs,
  dados voluntários vs perguntados, gaps da Even → knowledge cards + sugestões.
- Auditor v2: pontua atendimentos humanos; transcritos-ouro → treino da Even.
- Descobridor: número não-registrado com padrão de URA → proposta 1-clique.

### Onda 6 — APP NATIVO (a Pedra de Roseta)
- Se o eco do nfm_reply confirmar (Onda 0/observação real): replicar o payload
  por código no provider GO (send_flow_reply) → validar num acionamento de
  teste → Even cruza a tela sozinha. Se não ecoar: experimento Cartógrafo
  usando o mapa completo até a tela (com liberação do founder).

## CUSTO (estimativa honesta)
- Captura/sessões/arestas: R$0 (código).
- Haiku (classificações em lote): ~centavos/dia no volume atual.
- Sonnet (merges/patches): acionado por evento (drift/conflito) — poucos/semana.
- Total esperado: **< R$1/dia** na fase Resulta+AutoFleet. Escala linear e barata.

## MÉTRICAS DE SUCESSO
- % cobertura por seguradora×ramo×serviço (meta: HDI/Porto/Allianz auto >90%
  em 30 dias de observação nas 2 corretoras).
- Nº de rotas novas/semana por corretora-sensor (efeito rede visível).
- Drift detectado→playbook atualizado sem humano (tempo de ciclo).
- Zero mensagens enviadas por instâncias observer (invariante auditável).
- Payload do nfm_reply capturado (sim/não — destrava Onda 6).

## EXECUÇÃO EM BLOCOS (DECISÃO 18/07 — founder pediu blocos maiores; minha divisão)

Ondas consolidadas em 4 BLOCOS — cada um termina com verificação real e
checkpoint do founder (a qualidade não cede: o gate é por bloco, não por onda):

- **BLOCO A — Fundação + Prova (Ondas 0+1 juntas):** construir a captura
  (branch observer no webhook, observed_events, multi-instância modo cofre,
  HISTORY_SYNC) e RODAR o spike no 4743 na sequência imediata — a infra da O1
  é justamente o instrumento de medição da O0. Entrega: relatório GO/NO-GO +
  captura viva funcionando.
- **BLOCO B — Fábrica + Atlas (Ondas 2+3):** Tecelão completo + página
  /admin/atlas, validados com as sessões reais capturadas no Bloco A.
- **BLOCO C — Vida própria (Ondas 4+5):** auto-atualização (Sentinela de
  Rotas + Alfaiate v2 + gate Simulador) + kit de onboarding + Garimpo/Auditor
  v2 + Descobridor. Ao fim: parear a PRIMEIRA atendente real.
- **BLOCO D — App nativo (Onda 6):** replicar o payload capturado.

Ordem de liberação: aprovar plano → BLOCO A → relatório → BLOCO B → founder vê
o Atlas → BLOCO C → 1ª atendente real → BLOCO D.
