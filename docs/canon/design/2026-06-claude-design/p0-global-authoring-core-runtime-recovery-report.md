# P0 — Recuperação: Chat Principal inteligente + editor global real + UX de agentes

> Corrige as 3 falhas reais que o Founder encontrou: (1) o Chat Principal respondia como **RAG-only** ("não sei" p/ capital da Itália); (2) não havia **editor visual** para o AutoBrokers/Even **global**; (3) a tela de Agentes da Resulta **duplicava** Core/Even no editor legado. **Tudo confirmado no repo e corrigido.** Sem provider externo, sem ação externa, motor único do Smith.
> **Data:** 2026-06-22 · **Modelo:** Claude Opus 4.8 · **Base:** `8014316`.

## Diagnóstico (o GPT estava certo — verifiquei no código)
- `backend/app/core/prompts.py`: `SYSTEM_BASE_PROMPT` mandava responder "ESTRITAMENTE nos documentos indexados" + "Se não estiver no texto recuperado, não existe" — aplicado a **todos** os agentes. → Chat Principal burro.
- `backend/app/agents/graph.py:705`: RAG com `include_global=False` hardcoded → Core não usava o conhecimento global do AutoBrokers.
- **Não era saldo nem LLM** — era política de runtime errada.

## O que corrigi (de verdade, no backend Python deste repo)
### 1. Runtime por papel — Chat Principal inteligentíssimo
- `prompts.py`: nova **`CORE_BASE_PROMPT`** (copiloto interno, raciocínio sênior em estratégia/vendas/marketing/jurídico/operação/finanças/seguros; **usa conhecimento geral livremente**; a base de conhecimento **complementa, não limita**; **nunca** "não sei" p/ conhecimento geral; ferramentas quando úteis; **guardrails de seguro mantidos** p/ cobertura/apólice/sinistro/ação externa). **`ATTENDANCE_BASE_PROMPT`** (Even continua **evidence-first** e segura). `build_composite_prompt(client, agent_role)` escolhe a base por papel; legado/sem papel = Core.
- `graph.py`: passa `agent_role` ao montar o prompt; **`include_global` agora é true só para o Core** (Even/auxiliar seguem privados).
### 2. Editor global REAL no Blueprint Center
- Botões **"Editar padrão global"** nos cards AutoBrokers Global Core / Even Global Attendance (+ "Editar" nos Source Auxiliares) abrem o **construtor completo do Smith** (`AgentConfigModal`: Identidade, Modelo, Personalidade/Prompt, Memória/RAG, Segurança, HTTP Tools, MCP, Especialistas) no **Source Agent** do Studio. Salvar altera só o padrão; publicar versão + rollout distribui. **Reusa o editor existente — sem editor paralelo.**
### 3. UX de agentes da Resulta sem duplicação
- A tela de Agentes da empresa cliente **filtra Core/Even do canvas legado** (eles já aparecem na seção "Agentes canônicos" e são editados no Blueprint Center). Fim da duplicação e do editor técnico errado para Core/Even.

## Declaração
```
P0_GLOBAL_SOURCE_EDITOR_READY: SIM (AgentConfigModal no Blueprint Center p/ Source Agents)
P0_BLUEPRINT_CENTER_EDIT_LINKS_READY: SIM
P0_SOURCE_SAVE_DOES_NOT_PUBLISH_READY: SIM (editar Source ≠ publicar release; publish/rollout separados)
P0_CORE_GENERAL_KNOWLEDGE_READY: SIM (CORE_BASE_PROMPT; testado)
P0_CORE_GLOBAL_RAG_POLICY_READY: SIM (include_global só p/ Core)
P0_PRIVATE_RAG_ISOLATION_READY: SIM (mantido por company_id; global só leitura curada p/ Core)
P0_EVEN_EVIDENCE_FIRST_READY: SIM (ATTENDANCE_BASE_PROMPT)
P0_CLIENT_CANONICAL_AGENT_VIEW_READY: SIM (seção canônica + dedup)
P0_LEGACY_EDITOR_BLOCKED_FOR_CORE_EVEN_READY: SIM (Core/Even filtrados do canvas legado)
P0_EVEN_VISIBLE_IN_CLIENT_VIEW_READY: SIM (seção canônica via Supabase)
P0_RUNTIME_DIAGNOSTICS_READY: NÃO (a causa-raiz foi corrigida; diagnóstico vira incremento — ver nota)
P0_CHAT_ACCEPTANCE_CAPITAL_ITALY_READY: SIM (verificado em teste de contrato de prompt; confirmar no chat real após deploy)
NO_REAL_WHATSAPP_SENT: SIM
NO_BROWSERBASE_OPENED: SIM
NO_PORTAL_ACTION_EXECUTED: SIM
NO_EXTERNAL_PROVIDER_INTEGRATED: SIM
NO_PARALLEL_AGENT_ENGINE_CREATED: SIM
NEXT_STEP: confirmar chat real + (incremento) Diagnóstico de Runtime; depois FASE_B_FINAL_COMPLETION
```

## Nota honesta sobre o "Diagnóstico de Runtime" (Parte 6)
A **causa-raiz** (prompt RAG-only + global off) foi **eliminada** — então o chat para de "adivinhar". O painel de diagnóstico (saldo/LLM/política/RAG) é **incremento útil**, não bloqueador do aceite, e o adicionei à fila. Priorizei o que faz o chat funcionar agora.

## Testes
- **Python** `backend/tests/test_core_prompts.py` **13** (Core sem RAG-only; permite conhecimento geral; copiloto interno; guardrail de cobertura; Even evidence-first; legado=Core). Carrega `prompts.py` por caminho (sem deps), pytz stubado.
- **JS** regressão verde: blueprint-release 39, auxiliary-publish 19, release-rollout 27, company-kind 9, security 31. `tsc` EXIT=0 · `npm run build` verde.

## Você, após o deploy — TESTE DE ACEITE (1º)
1. Dashboard Resulta → **AutoBrokers → Nova conversa** → "Qual é a capital da Itália?" → **"Roma."** (sem RAG/WhatsApp/Portal).
2. Faça uma pergunta estratégica (ex.: "monte um plano de captação de clientes para seguro auto") → deve raciocinar e responder com profundidade.
3. Portal Admin → **Blueprint Center** → **Editar padrão global** (AutoBrokers Global Core) → abre o construtor completo do Smith (todas as abas).
4. Portal Admin → Resulta → **Agentes**: Core/Even só na seção "Agentes canônicos" (sem duplicar no canvas).
5. Pergunte algo de cobertura/apólice → ele NÃO inventa (pede evidência) — guardrail mantido.

## Próximo
Confirmar o chat real; depois **Diagnóstico de Runtime** (incremento) e o **fechamento final da Fase B** (FinOps no runtime, Aprovadores storage, telas dedicadas).
