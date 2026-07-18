# SPEC-038 (RASCUNHO) — ATLAS: o Observador e a fábrica de mapas de URA

> Fase 1 (arsenal/rascunho) — Fable, 18/07/2026, força máxima. NADA construído
> ainda. Este documento é a base do plano definitivo. Decisão do founder que
> origina tudo: parear os WhatsApps dos atendentes HUMANOS das corretoras
> (Resulta e AutoFleet já combinados), com os atendentes AutoBrokers DESLIGADOS,
> e um Observador silencioso mapeando TODAS as rotas de TODAS as seguradoras a
> partir do tráfego real — até termos todos os mapas, para sempre atualizados.

## 0. FATOS VERIFICADOS NO CÓDIGO-FONTE DO GO (18/07 — base de tudo)

1. **Não existe evento "SendMessage" no handler** (o Opus errou o mecanismo).
   O handler emite `Message` para `*events.Message` — e no multi-device do
   WhatsApp, o que a atendente digita NO CELULAR chega ao aparelho pareado como
   `Message` com `Info.IsFromMe=true`. Já assinamos MESSAGE ⇒ **os dois lados
   da conversa já chegam ao nosso webhook hoje**. O bloqueio é NOSSO: o
   normalizador descarta `from_me` (skip). O Observador precisa de uma rota
   que capture ambos os lados. (SEND_MESSAGE do GO ≈ envios feitos pela
   própria API — irrelevante para observar humanos.)
2. **`HistorySync` existe e é encaminhado ao webhook** (`case *events.HistorySync`,
   subscribe HISTORY_SYNC). Ao parear um celular, o WhatsApp empurra o
   histórico recente ⇒ bootstrap de rotas do passado NO DIA ZERO. Profundidade
   limitada (WhatsApp decide; não é o histórico completo).
3. **`TemporaryBan` é um evento** — dá para monitorar risco de banimento em
   tempo real (Vigia deve assinar/alertar).
4. Interativos: listas/botões/nativeFlow chegam com o protobuf completo
   (validado ao vivo 14/07). `_interactive_from_message` já extrai
   `flow_token`/`flow_id`/rows/ids.
5. **Incerteza honesta que resta:** o eco do `nfm_reply` (a RESPOSTA do
   formulário nativo preenchido no celular) para aparelhos pareados NÃO é
   garantido — flows E2E podem responder fora do chat. Verificável só na
   prática (Onda 0). Se ecoar = Pedra de Roseta do app nativo (replicamos por
   código). Se não ecoar, o Observador ainda mapeia TUDO até a tela, e o
   experimento de travessia fica com o Cartógrafo.

## 1. VISÃO — o produto interno "ATLAS"

**Atlas de Rotas AutoBrokers**: o mapa vivo, versionado e auto-atualizável de
todos os WhatsApps de todas as seguradoras, em todos os ramos e serviços,
construído passivamente a partir dos atendimentos humanos reais (multi-
corretora) e complementado cirurgicamente pelo Cartógrafo. Inteligência 100%
AutoBrokers (admin-only; corretoras usufruem via atendentes/playbooks, nunca
veem). Analogia de negócio: Google Maps — carros próprios (Cartógrafo) +
celulares dos usuários (Observador multi-corretora); cada corretora nova é um
sensor que preenche as lacunas em que ela é forte (ex.: Resulta →
Allianz residencial; outra → Bradesco auto). Tesla shadow mode: a frota observa
humanos dirigindo antes de o autopilot assumir. Task/process mining (Celonis):
reconstruir o processo a partir dos logs do trabalho real.

## 2. PIPELINE (determinístico primeiro — qualidade E custo)

```
[celulares pareados] → GO (MESSAGE fromMe+in / HISTORY_SYNC / CONNECTION)
   → Rota observer no webhook (NUNCA responde; purpose="observer")
   → FILTRO DE BORDA (allowlist de números de seguradora; resto DESCARTADO)
   → observed_events (bruto, por corretora, cifrado)          [Etapa 0 CAPTURA]
   → sessões por (corretora × número seguradora × janela)     [Etapa 1 SESSIONIZAÇÃO]
   → TECELÃO: telas normalizadas/templatizadas + arestas
     (tela A --resposta/clique do humano--> tela B) → merge no
     Atlas versionado com proveniência                        [Etapa 2 TECELAGEM]
   → SENTINELA DE ROTAS: diff observado × Atlas → drift       [Etapa 3 VIGÍLIA]
   → ALFAIATE v2: playbooks auto-atualizados; gate do
     SIMULADOR antes de aplicar; escala p/ founder só se
     estrutural                                               [Etapa 4 COSTURA]
   → Even/Cérebro consomem; GARIMPO v2 minera a parte 1
     (cliente↔corretora); AUDITOR v2 marca atendimentos-ouro  [Etapa 5 CONSUMO]
   → Página ATLAS no admin (visual, cores, filtros, faltas)   [Etapa 6 VISUAL]
```

- Etapas 0/1 e o núcleo da 2: **código puro, zero LLM** (~90% do volume).
- LLM por camada (custo): **Haiku 4.5** = equivalência de telas com hash
  diferente, templating de variáveis ambíguas, classificação de drift
  cosmético×estrutural. **Sonnet 5** = conflitos de merge, patch de playbook,
  digests de escalada. **Fable/Opus sob demanda** = protocolo do app nativo,
  onboarding de seguradora nova, conflitos profundos. Processamento em LOTE
  (por sessão encerrada + consolidação noturna), nunca por mensagem.

## 3. MODELO DE DADOS (evolução, não ruptura)

- `observed_events` (novo): tenant-scoped; direction, counterparty→insurer_key,
  type, texto, interactive_payload (protobuf JSON), media METADADOS (sem bytes
  por padrão), message_id, session_hint, ts. Retenção proposta: 90 dias.
- `observed_sessions` (novo): corretora, insurer, janela, resultado inferido
  (concluído/abandonado/transferido-humano), ramo/serviço inferidos PELA ROTA
  (labels dos menus; número não basta — Porto atende auto+resi+vida no mesmo).
- `ura_maps` (evolui): + `source` (observed|explored|merged), versão,
  proveniência por aresta (corretora-sensor, contagem de observações,
  first/last seen), `confidence` (aresta confirmada ≥2 observações; 1x fica
  marcada "vista 1 vez"), status por nó (completo/parcial/drift/app_form/desconhecido).
- **Separação sagrada (política do conhecimento global):** a ESTRUTURA
  (telas templatizadas {NOME}/{PLACA}/{PROTOCOLO}, rótulos, arestas) é global
  AutoBrokers; o CONTEÚDO (transcritos com PII) fica isolado por corretora e
  NUNCA entra no Atlas nem no RAG.

## 4. ELENCO DE AGENTES (auditoria dos atuais + novos)

| Agente | Papel no ATLAS | Mudança | LLM |
|---|---|---|---|
| **Observador** (novo) | Captura passiva multi-instância; filtro de borda; NUNCA envia | criar | nenhum |
| **Tecelão** (novo) | Sessioniza, templatiza, tece arestas, faz merge no Atlas ("o agente que edita as rotas") | criar | Haiku→Sonnet |
| **Sentinela de Rotas** (novo) | Drift: diff contínuo observado×Atlas; dispara atualização | criar | Haiku |
| **Alfaiate v2** | Auto-patch de playbooks a partir do Atlas + respostas humanas reais; passa no Simulador antes de aplicar | promover (central) | Sonnet |
| **Simulador** | Vira o GATE de qualidade: replay do playbook novo contra o mapa novo; só aplica se passar | promover | Sonnet |
| **Cartógrafo** | Rebaixado a cirúrgico: lacunas da lista "o que falta", seguradora sem tráfego, experimento de travessia — sempre com liberação | rebaixar | (motor código) |
| **Even/atendentes** | Consumidores dos playbooks; DESLIGADOS por corretora em modo observação (flag por corretora: observe_only/hybrid/full) | flag de modo | — |
| **Espelho** | Mantém (dispatches nossos); código reaproveitado pelo Observador | manter | — |
| **Vigia** | ESTENDER: saúde das instâncias observer (queda→alerta re-parear) + evento TemporaryBan | estender | — |
| **Sentinela (dispatch)** | Sem mudança (só acionamentos nossos) | manter | — |
| **Cérebro v2** | Sem mudança; ganha mapas muito mais ricos | manter | Sonnet |
| **Auditor v2** | ESTENDER: pontua atendimentos HUMANOS; marca transcritos-ouro p/ treinar a Even | estender | Haiku/Sonnet |
| **Garimpo v2** | ESTENDER: minera a PARTE 1 (cliente↔corretora): FAQs, dados voluntários vs perguntados, gaps da Even, sugestões de rotina | estender | Haiku/Sonnet |
| **Descobridor** (novo, leve) | Número desconhecido com cara de URA/bot no celular observado → candidato a seguradora nova → 1 clique do founder p/ entrar no registry | criar | Haiku |

## 5. PÁGINA ATLAS (admin-only — o pedido visual do founder)

`/admin/atlas`: cards premium por seguradora (reusar o padrão com monograma) →
abas por ramo → árvores por serviço. Cores: 🟢 completa validada (≥N passagens
ponta a ponta) · 🟡 parcial (lista explícita do que falta: "não vimos: Bateria,
Táxi") · 🔴 drift aguardando validação · 🟣 fronteira de app nativo · ⚪ nunca
observado. Filtros: seguradora/ramo/serviço/status/fonte/corretora-sensor/
frescor. % de cobertura por seguradora e global. Clique no nó → texto da tela
(sem PII), variantes, última vez vista, quantas sessões passaram. **Feed "O QUE
FALTA"**: lista priorizada e legível para o founder repassar às atendentes
("se pegar um chaveiro da Porto, é ouro — não temos essa rota"). Render:
árvore hierárquica (estilo dagre) — mais legível que grafo livre para rotas.

## 6. ONBOARDING POR CORRETORA (o processo dos 15–30 dias)

Admin → "Nova corretora → Modo Observação": parear números (oficial +
atendentes), consentimento assinado (LGPD), card de status do observer
(conectado, eventos hoje, sessões capturadas), delta de cobertura ("esta
corretora já contribuiu X rotas novas"). D0: parear (+histórico se aprovado) →
D1–D30: atendentes humanos normais, Even OFF, Observador ON → revisão de
cobertura → ligar Even (hybrid) já com playbooks costurados do tráfego DELES.
Heatmap: qual corretora preenche qual lacuna (Resulta→Allianz resi etc.).

## 7. BARREIRAS E RISCOS (o que o founder pode não estar vendo)

1. **Privacidade do celular pessoal da atendente** (A MAIOR): o aparelho
   pareado vê TODAS as conversas dela (mãe, amigos). Mitigação inegociável:
   filtro de borda por allowlist de números de seguradora — o resto é
   DESCARTADO na primeira linha (nunca armazenado/logado; só contadores) +
   consentimento assinado por atendente. Preferir números corporativos.
2. **Limite de ~4 aparelhos vinculados** por WhatsApp — atendente que já usa
   Web+tablet pode não ter slot. Checar por atendente.
3. **HistorySync é parcial** — bootstrap ajuda mas não traz tudo; expectativa.
4. **Risco de banimento** — mecanismo idêntico ao WhatsApp Web (baixo, não
   zero; whatsmeow é não-oficial). Monitorar TemporaryBan; rollout gradual.
5. **Eco do nfm_reply incerto** (fato 0.5) — pode não sincronizar. Onda 0.
6. **Sessões entrelaçadas**: a atendente toca 2 clientes na MESMA conversa com
   a seguradora → sessionização por marcadores de saudação da URA + protocolo
   + janelas; aceitar reparo raro via UI.
7. **Números de seguradora fora do registry** seriam descartados pelo filtro →
   Descobridor (item 4) para não perder rotas em silêncio.
8. **Envenenamento do Atlas** por sessões ruins → confiança por contagem
   (aresta ≥2 observações = confirmada) + proveniência.
9. **Duplicidade no número oficial da Resulta** (Even + observação no MESMO
   número): NÃO criar segunda instância — o webhook já recebe tudo; o
   Observador é um TAP no fluxo existente (fork), nunca um segundo consumidor.
10. **LGPD**: corretora = controladora, nós = operadores; consentimentos;
    retenção 90d bruto / estrutura para sempre (sem PII).
11. **Atlas nunca exposto a corretora** (require_master_admin em tudo).

## 8. PERGUNTAS ABERTAS AO FOUNDER (com recomendação)

- Q1 Celulares: pessoais ou corporativos? → REC: corporativo onde der; pessoal
  só com filtro-allowlist + termo de consentimento da atendente.
- Q2 Importar HistorySync no pareamento? → REC: SIM (bootstrap dia zero), com
  o mesmo filtro; precisa do teu OK por ser retroativo.
- Q3 Política de auto-aplicação: Atlas = automático sempre; playbooks =
  automático SÓ se passar no Simulador; te acordamos em mudança estrutural/app
  nativo/seguradora nova. → REC: aprovar exatamente assim.
- Q4 Teste HDI do Cartógrafo: fazer agora ou aguardar o Observador pegar um
  HDI real da atendente? → REC (mudei de posição): AGUARDAR — em dias uma
  atendente cruza o app nativo de verdade e nos entrega a resposta com risco
  ZERO; o Cartógrafo fica armado para lacunas depois.
- Q5 Retenção do bruto: 90 dias? → REC: sim.
- Q6 Observar também números de parceiros (guinchos/oficinas)? → REC: fase 2;
  começar só seguradoras.
- Q7 Nomes: sistema ATLAS; agentes Observador/Tecelão/Sentinela de Rotas/
  Descobridor. → REC: aprovar.

## 9. SEQUÊNCIA DE CONSTRUÇÃO PROPOSTA (para o plano definitivo)

- **Onda 0 — Spike de verificação (1 dia, risco zero):** parear UM celular de
  teste como observer; confirmar na prática: fromMe chega, protobuf interativo
  completo, shape do HistorySync, eco (ou não) do nfm_reply. Fatos GO/NO-GO.
- **Onda 1 — Captura:** multi-instância GO (create/pair por número observado),
  rota observer no webhook (mudo por construção), filtro de borda,
  observed_events + scrub de PII.
- **Onda 2 — Tecelão:** sessionização, templating forte, merge versionado no
  Atlas com proveniência/confiança.
- **Onda 3 — Página Atlas** no admin (visual, cores, filtros, "o que falta").
- **Onda 4 — Auto-atualização:** Sentinela de Rotas + Alfaiate v2 + gate do
  Simulador + alertas ao founder só no estrutural.
- **Onda 5 — Onboarding kit** por corretora + Garimpo v2 (parte 1) + Auditor
  v2 (transcritos-ouro p/ Even).
- **Onda 6 — App nativo:** replicar por código o payload capturado do
  formulário (se ecoar) OU experimento Cartógrafo com a referência que tivermos.
