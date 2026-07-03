# SPEC-017 — Atendente Externo Inteligente no Smith: WhatsApp Evolution multi-tenant + Playbooks de Corredor

> Status: **APROVADA PELO FOUNDER (2026-07-03) — EM EXECUÇÃO**
> Onda: 2 · Executor: Fable (esforço alto) · Branch: `feat/spec-017-attendant`
> Programa: `docs/canon/FABLE_RECOVERY_PROGRAM.md` (D1/D2/D5) · Baseline: main pós-SPEC-016.1
> Materiais privados de descoberta: worktree de auditoria `docs/` (V7, intake, cérebro antigo) — NUNCA commitados, NUNCA viram fixture com PII.

---

## 1. Missão

O segurado chama no WhatsApp da corretora e é atendido **de ponta a ponta, sem humano**:

```text
ENTRADA (WhatsApp da corretora, via Evolution)
→ LEVANTAMENTO humanizado (frases curtas, espera o cliente concluir)
→ IDENTIFICAÇÃO + APÓLICE (motor SPEC-016: InfoCap → documento oficial → política de assistência)
→ ELEGIBILIDADE confirmada ("tem chaveiro sim — Assistência 24h Completo")
→ ACIONAMENTO da seguradora (playbook do corredor, ex.: WhatsApp Allianz 24h)
→ CAPTURA de protocolo/senha/agendamento
→ RETORNO ao cliente com instruções
→ ACOMPANHAMENTO até encerrar (prestador foi? resolveu?)
→ HANDOFF humano APENAS: sinistro, risco à vida, caso complexo, cliente pede humano
```

O atendente é **inteligente como o Chat Principal** — mesmo cérebro Smith, papel
`external_customer_attendant` — nunca uma máquina de menu. Guardas determinísticos
impõem o que ele NÃO pode fazer (prometer cobertura sem evidência, enviar para
fora sem gate); a conversa é dele.

## 2. Decisões de arquitetura (Founder aprovou)

| # | Decisão |
|---|---|
| S17-1 | **Canal**: Evolution API (grátis, QR code por corretora) como provider padrão; Z-API/uazapi suportados pelo mesmo seam. Transplante seletivo do V7 (`services/whatsapp/` providers+registry, webhook token por integração, dedup Redis, buffer atômico). NÃO é upgrade V7. |
| S17-2 | **QR code no Dashboard → Personalização → Conectores** (card WhatsApp da corretora): conectar, status ao vivo, reconectar. Decisão de UX: conector é conexão; identidade do atendente fica em Personalização → Atendente. |
| S17-3 | **Alerta de desconexão** (exigência do Founder): ao desconectar, mensagem IMEDIATA de WhatsApp para número/grupo de alerta configurado pela corretora (NUNCA o próprio número de atendimento; NUNCA e-mail), enviada pela **instância-plataforma de alertas do AutoBrokers** (número global próprio) + banner vermelho no dashboard. Watchdog: eventos de status do Evolution + verificação periódica (worker). |
| S17-4 | **Corredores = PLAYBOOKS DE DADOS versionados** (galeria global → ativação por corretora), não código por corredor. Subcorredor = variação de coleta dentro do playbook. Seed v1: Allianz Residencial (eletricista, chaveiro, encanador/hidráulica, eletrodomésticos, desentupimento) minerado do cérebro antigo + conversa real. |
| S17-5 | **Acionamento**: a conversa corretora↔seguradora acontece pelo MESMO número da corretora (como a atendente humana faz). Fase URA = respostas determinísticas por âncora de menu (sem LLM). Fase humana da seguradora = LLM com guard + resumo do caso. Extração de protocolo/senha/agendamento por âncoras. |
| S17-6 | **Gate de seguradora real**: flag `INSURER_DISPATCH_LIVE` (default OFF) + aprovação por caso. OFF = dry-run completo (sequência exata de mensagens gerada, logada, "pronto para enviar"). Só liga com autorização do Founder + corretora avisada. Testes com o número do Founder NÃO enviam nada à seguradora. |
| S17-7 | **Conhecimento**: atendente usa RAG global curado (plataforma) + RAG privado da corretora (upload via Dashboard → Conhecimento, já existente) + playbooks + apólice (SPEC-016). Muda o escopo RAG do papel attendance para incluir global curado. |
| S17-8 | **Identidade configurável por corretora** (D5): nome, avatar, tom, horário, mensagem fora de horário, número/grupo de alerta, autonomia. Fim do hard-code "Even" (rotas de rename, slugs de exibição). Papel canônico `external_customer_attendant` (alias técnico `attendance` mantido no banco). |
| S17-9 | **Humanização** (exigência do Founder): mensagens CURTAS (1–3 frases), sem textão exceto listas/checklists; **buffer de entrada com debounce** (junta mensagens do cliente e responde uma vez — mecanismo do V7 `buffer_processor`); divisor de saída (respostas longas viram 2–3 balões); tom minerado das conversas reais da Resulta (cérebro antigo 04_CONVERSA_COM_CLIENTE + intake). |
| S17-10 | **Atendimento/handoff**: máquina de estados do V7 adaptada (7 estados, RPC transacional, sessões, timeline, SLA opcional) sobre nossos casos; handoff gera dossiê (já existe base TS a portar). |
| S17-11 | Migrations: **expand-only** (novas tabelas/colunas; nada destrutivo), cada uma com APPLY→VERIFY→ROLLBACK documentado no PR. |

## 3. Fluxo Allianz Residencial (fonte: conversa real de 22.800 linhas — resumo canônico)

```text
URA (menus numerados, respostas determinísticas):
  saudação → "1-Auto 2-Residência..." → 2 → "1-Residencial 2-Auto c/ resid." → 1
  → CPF do titular → confirmar endereço (opção 1) → nº da residência
  → telefone contato (confirmar/adicionar) → tipo de serviço:
    1 = casa (encanador/eletricista/chaveiro) · 2 = eletrodomésticos · 3 = outros
FASE HUMANA (LLM guiada + guard):
  especialista se apresenta → confirmar titular/endereço/telefone
  → descrever problema (aparelho/marca/idade/sintoma OU serviço da casa)
  → agendamento por período (manhã 9-13 / tarde 13-18, a partir do próx. dia útil)
ÂNCORAS DE CAPTURA:
  "O número da assistência é <N>" → protocolo
  "senha de acesso ... 4 últimos números do telefone" → senha
  "agendada para o dia <D>, entre <H1> e <H2>" → agendamento
  regra fixa: maior de 18 anos no local
RETORNO AO CLIENTE: agendamento + senha + regra dos 18 anos (padrão da atendente real)
Dados mínimos (levantamento): CPF titular · confirmação de endereço + nº ·
  telefone de contato (+nome se terceiro) · subserviço · descrição do problema ·
  período preferido. (Matriz completa por subserviço: cérebro antigo MATRIZ_DADOS.)
Sinistro (9 menções na conversa) → HANDOFF humano sempre (v1).
```

## 4. Componentes e mudanças

### 4.1 Backend — canal (transplante V7, adaptado)
- `backend/app/services/whatsapp/` (novo pacote): `providers/{base,evolution,zapi,uazapi}.py`, `registry.py`, `models.py`, `service.py` — instância por tenant, sem fallback silencioso.
- `backend/app/api/whatsapp_webhook.py`: `POST /api/v1/webhook/{provider}/{token}` — tenant por hash HMAC do token, fail-closed, dedup por messageId (Redis SET NX), rate-limit.
- Buffer de turnos: Redis RPUSH por conversa + flush após janela de silêncio (`ATTENDANT_BUFFER_SECONDS`, default 8s) → um turno do Smith por rajada de mensagens.
- Tabela `whatsapp_integrations` (expand): provider, instance_ref, webhook_token_hash, status, alert_target (número/grupo), last_seen_at.
- Watchdog worker (Celery beat): status da instância; em `disconnected` → alerta S17-3 + evento.
- Evolution API: serviço próprio no EasyPanel (container oficial), multi-instância (uma instância por corretora), credenciais da instância no Vault.

### 4.2 Backend — atendente no Smith
- Papel `external_customer_attendant` (alias `attendance`): prompt base humanizado novo (substitui ATTENDANCE_BASE_PROMPT; tom das conversas reais; frases curtas; espera raciocínio; nunca promete sem evidência; nunca inventa protocolo).
- RAG do papel: privado da corretora + global curado (ajuste em `graph.py` `_rag_include_global`).
- Tools do papel (por capability): `attendance_case` (caso/slots/estado — lógica pura portada do TS como ferramenta), `infocap_policy_lookup` (role view attendance: evidência mínima por caso), `knowledge_base_search`, `request_human_agent` (handoff → sessões), `insurer_dispatch` (S17-5/S17-6).
- Saída: divisor de balões (máx ~300 chars por mensagem, listas mantidas inteiras).

### 4.3 Playbooks
- Tabela `corridor_playbooks` (global, versionada, JSON: ura_steps com âncoras→respostas, required_slots por subserviço, anchors de captura, regras de segurança, handoff_triggers, contact_ref) + `tenant_corridor_activations` (reuso do existente).
- Seed `allianz-residencial-whatsapp@v1` gerado do material real (sem PII).
- Autoria/edição futura no Blueprint Studio (Onda 4); v1 = seed por código/SQL expand.

### 4.4 Dispatch engine (acionamento)
- `backend/app/services/insurer_dispatch_service.py`: máquina por caso — abre conversa com contato da seguradora (mesmo número da corretora), executa ura_steps (matcher de âncora → resposta), fase humana via LLM restrita (contexto = dossiê do caso + playbook; guard: só dados do caso, nunca inventar), captura âncoras, persiste protocolo/senha/agendamento no caso, timeout/fallback → handoff com dossiê.
- Estados: `preparing → ready_to_send → (gate) sending → ura → human_phase → captured → confirmed_to_client → monitoring → closed | handoff`.
- Dry-run (gate OFF): tudo até `ready_to_send` com transcript simulado das mensagens que SERIAM enviadas.

### 4.5 Frontend
- Dashboard → Personalização → Conectores: card WhatsApp (QR code, status ao vivo, reconectar, número/grupo de alerta).
- Dashboard → Personalização → Atendente: identidade (nome/avatar/tom/horário/mensagem de ausência/autonomia).
- Atendimentos: casos alimentados pelo novo runtime (fila/casos/conversas existentes), timeline de eventos, botão assumir (claim) e devolver à IA.
- Portal Admin: remoção dos hard-codes "Even" (rename forçado, rotas core-even → rótulo neutro "Atendente"), galeria de playbooks (leitura v1).

### 4.6 O que morre (após paridade)
- Runtime conversacional TS (`lib/attendance/runtime-*`, message-router como cérebro): substituído; helpers puros úteis portados como tools. Remoção física na Onda 3 após paridade comprovada.

## 5. Fases de execução (uma branch, entregas incrementais testáveis)

```text
P1  Canal: transplante whatsapp/ + webhook token + dedup + buffer + migration
    expand + Evolution no EasyPanel + QR no dashboard + alerta de desconexão.
    Teste: conectar o número de teste do Founder, mandar "oi", receber resposta
    do atendente Smith. Watchdog: desconectar → alerta chega.
P2  Atendente: prompt humanizado + buffer de turnos + divisor de balões +
    knowledge global/tenant + identidade configurável (fim do Even) + handoff
    básico com estados. Teste: conversa humanizada completa via WhatsApp real.
P3  Apólice no atendimento: infocap role view por caso + política de assistência
    ("tem chaveiro?" → confirma na apólice antes de prometer). Teste E2E stub.
P4  Playbook engine + seed Allianz Residencial + dispatch DRY-RUN ponta a ponta:
    caso real simulado gera a sequência exata de mensagens p/ Allianz + captura
    de âncoras num stub de seguradora. Teste: golden do fluxo completo.
P5  Acompanhamento/encerramento + dossiê handoff + SLA opcional + suíte E2E
    completa (WhatsApp stub + seguradora stub) + teste real corretora↔cliente
    com o número do Founder (SEM seguradora real).
P6  [GATE FOUNDER] Acionamento real Allianz com aprovação por caso → depois
    autonomia progressiva. Não bloqueia ondas seguintes.
```

## 6. Testes e aceite

- Offline: suíte atual 100% + novas suítes (webhook auth/dedup, buffer, playbook matcher de âncoras, dispatch dry-run golden do caso Marinéia sintetizado, humanização — tamanho de balões, guard de promessas).
- E2E stub: WhatsApp fake (inbound/outbound) + Allianz fake (URA scriptada da conversa real) → caso completo entrada→protocolo→retorno→encerramento sem humano.
- Real (número do Founder): conexão QR, conversa humanizada, consulta de apólice, dry-run de acionamento com transcript exibido. **Nada enviado a seguradora real.**
- Aceite Founder: (1) conversa "parece a Saionara"; (2) frases curtas, espera rajada; (3) elegibilidade confirmada na apólice; (4) dry-run gera exatamente a sequência que a atendente humana mandaria; (5) alerta de desconexão chega; (6) handoff com dossiê ao pedir humano/sinistro.

## 7. Riscos e mitigação

| Risco | Mitigação |
|---|---|
| Evolution instável / número banido | watchdog + alerta S17-3; provider seam permite trocar p/ Z-API por tenant; boas práticas anti-ban (sem burst, número dedicado no piloto) |
| URA da Allianz mudar texto dos menus | âncoras por regex tolerante + `unknown_step` → pausa + handoff com dossiê (nunca responde às cegas) |
| LLM prometer o que não pode | guard de atendimento (sem promessa sem evidência; sem protocolo inventado — protocolo só de âncora capturada) |
| PII | mascaramento em logs (padrão existente); transcript seguradora fica no caso, não em log |
| Mensagens fora de ordem/duplicadas | dedup por messageId + buffer com janela |
| Cliente responde durante acionamento | duas conversas independentes por caso (cliente e seguradora); o atendente informa "estou acionando, te retorno já" |

## 8. Rollback

- Flag por tenant: canal WhatsApp só ativa com integração conectada; desligar a integração volta ao estado atual (sem atendimento externo).
- `INSURER_DISPATCH_LIVE` OFF instantâneo.
- Migrations expand-only: rollback = ignorar tabelas novas.
- Runtime TS antigo permanece no repo até paridade (não referenciado pelo novo caminho).
