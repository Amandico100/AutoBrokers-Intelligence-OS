# FABLE RECOVERY PROGRAM — Programa Mestre de Recuperação e Produção

> Status: **ATIVO — documento vivo único do programa**
> Data: 2026-07-02
> Líder técnico: Fable (Claude) · Direção de negócio: Founder
> Baseline auditado: `e7c5044` · Auditoria completa entregue em 2026-07-02
> Regra de ouro: **um cérebro, uma autoridade, uma fonte de credencial, zero gambiarra.**

---

## 1. Visão arquitetural alvo

### 1.1 O princípio: UM cérebro

**Decisão do Founder, ratificada pelo líder técnico: o AutoBrokers tem UM único cérebro — o Smith/LangGraph (Python).**

Não existe "segundo cérebro em TypeScript". O runtime determinístico de `lib/attendance/` entra em **rota de aposentadoria como cérebro**: sua lógica pura (slots, corredores, playbooks, guardrails, action engine) será **portada para Python** como ferramentas e políticas determinísticas do Smith. O TypeScript/Next.js fica apenas com o que é dele por natureza:

- **UI** (Dashboard, Portal Admin);
- **borda de canal** (normalização de webhook WhatsApp, autenticação de rotas, proxies);
- **nada de decisão conversacional, nada de LLM, nada de motor de fluxo.**

Divergência registrada: o GPT propôs manter o runtime TS como "camada de workflow" por tempo indeterminado. **Rejeitado.** Camada de workflow com lógica de decisão conversacional É um segundo cérebro com outro nome. A lógica é pura (sem I/O) e o porte para Python é mecânico e testável — não há razão técnica para manter dois donos da conversa.

### 1.2 Topologia alvo (modelo Claude/Anthropic)

```text
CANAIS (bordas finas, sem inteligência)
  Web chat · WhatsApp (Z-API, depois Meta/Evolution) · E-mail · Voz (futuro)
        │  normalização + autenticação + entrega
        ▼
SMITH / LANGGRAPH (cérebro único, Python)
  ┌──────────────────────────────────────────────────────────────┐
  │ 4 papéis (role views) sobre o MESMO motor:                   │
  │   core                        → Chat Principal do corretor   │
  │   external_customer_attendant → atendente externo (segurado) │
  │   auxiliary                   → rotinas/automações           │
  │   subagent                    → especialistas delegados      │
  │                                                              │
  │ Cada papel difere APENAS em:                                 │
  │   prompt base · capabilities · DTOs por papel ·              │
  │   output guards determinísticos · orçamento/modelo           │
  │ Inteligência NUNCA é podada por papel; o que muda é          │
  │ AUTORIDADE (o que pode fazer) e EVIDÊNCIA (o que pode        │
  │ afirmar), imposta por guard determinístico — não por         │
  │ burrice induzida.                                            │
  └──────────────────────────────────────────────────────────────┘
        │
        ▼
GOVERNANÇA (uma autoridade)
  Capability Registry (banco) = ÚNICA autoridade de tool/ação
  tenant_connections + Vault  = ÚNICA fonte de credencial
  Policies versionadas        = regras de negócio governadas
        │
        ▼
FERRAMENTAS E CONECTORES (execução)
  PolicyDataProvider (InfoCap hoje, Quiver/Segfy amanhã — mesma porta)
  Knowledge/RAG · Documentos/MinIO/Qdrant · Web search · MCPs ·
  HTTP tools · WhatsApp send · Portal Action Engine (Browserbase+HITL)
```

### 1.3 Multi-provider desde já (InfoCap não é a fonte única)

Decisão do Founder: InfoCap é a conexão piloto, **não** a arquitetura. O contrato canônico vira uma **porta** (`PolicyDataProvider`) com a InfoCap como primeira implementação:

- `PolicyLocator` generalizado: `<provider>:<ref-parts>` (hoje `infocap:<codfil>:<nosnum>`; amanhã `quiver:<...>`);
- status canônicos, DTOs por papel, identity gate e cache documental são **do contrato**, não da InfoCap;
- capability alvo: `policy.<provider>.read` (migração de nomes na Onda 3);
- Quiver/Segfy NÃO serão implementados agora — mas nenhuma linha nova pode assumir "InfoCap" onde o contrato deveria falar "provider".

## 2. Taxonomia canônica

| Termo | Definição canônica no AutoBrokers |
|---|---|
| **Capability** | Permissão funcional governada no banco (Registry). Única autoridade de disponibilidade de tool/ação. |
| **Connector** | Conexão por corretora em `tenant_connections` + segredo no Vault. Única fonte de credencial. |
| **Tool** | Ferramenta executável anexada ao grafo Smith. Só entra com capability ativa (pós-Onda 3). |
| **HTTP Tool** | Tool declarada em banco que chama API externa. Execução, nunca autoridade. |
| **MCP** | Protocolo de ferramenta externa. Execução, nunca login, nunca autoridade. |
| **Skill** | Procedimento versionado que ensina um papel a executar bem uma tarefa (análogo às skills do Claude). |
| **Playbook** | Skill determinística de acionamento externo (canal, mensagem, campos, fallback, escalada). |
| **Smith** | O motor LangGraph: estado, checkpoint, tools, guards, memória. Invisível ao cliente. |
| **Agent** | Instância configurada de um papel para uma corretora (linha em `agents`). |
| **Subagent** | Agente especialista chamado por delegação (`delegate_to_subagent`). |
| **Channel** | Borda de entrada/saída (web, whatsapp, email, voz). Sem inteligência. |
| **Role View** | Projeção de dados/autoridade por papel (DTO Core ≠ DTO atendente ≠ DTO auxiliar). |
| **Routine (Auxiliar)** | Agente `auxiliary` + gatilho (manual/cron/evento) + contrato de permissões + execuções auditáveis. Análogo ao Claude Rotinas. |
| **Portal Action** | Ação em portal de seguradora via SessionRef/Browserbase com preflight, HITL e protocolo. |
| **Policy (política)** | Regra de negócio versionada e auditável (ex.: `residential_24h_standard_v1`). Nunca inferência solta de LLM. |

## 3. Mapa de runtimes — atual → alvo

| Peça | Hoje | Alvo | Onda |
|---|---|---|---|
| Chat Principal | Smith (Python) ✅ | Smith, com contexto anafórico e Policy Facts | 1 |
| Atendente externo | Runtime TS determinístico + LLM fallback castrado | Smith papel `external_customer_attendant` com guardrails portados | 2 |
| Corredores/slots/playbooks | TS puro em `lib/attendance/` | Módulos Python determinísticos (tools + guards do Smith) | 2 |
| Action Engine | TS dry-run | Python, dry-run → HITL real | 2/5 |
| Auxiliares | 2 endpoints hard-coded, LLM direto | Engine de rotinas sobre o Smith + scheduler | 4 |
| WhatsApp | Borda TS + simulação | Borda TS fina → Smith; envio real com HITL | 2 |
| Voz | n8n legado | Congelada; migra para backend próprio | 3 |
| Autoridade de tools | 4 mecanismos concorrentes | Registry único | 3 |
| UCP/Shopify | Montado no grafo | REMOVIDO | 1.5 |

## 4. Decision Ledger (único — não criar ADRs separados)

| # | Decisão | Decisor | Status | Observação |
|---|---|---|---|---|
| D1 | Smith/LangGraph é o cérebro ÚNICO de todos os papéis | Founder + Fable | **APROVADA** | Substitui a ambiguidade "TS como workflow layer" do GPT |
| D2 | Runtime TS de atendimento: lógica pura portada p/ Python; TS vira borda+UI; nada apagado antes do porte validado | Fable | **APROVADA** | Porte mecânico, funções puras, com testes espelho |
| D3 | P0/P0.1 identidade InfoCap congelados, irreversíveis | Founder | **VIGENTE** | |
| D4 | R1C.2: stash NUNCA aplicado inteiro; minerar em 3 fatias (Facts → Assistance Profile → Composer) dentro da SPEC-016 | Founder | **APROVADA** | |
| D5 | Papel canônico `external_customer_attendant`; identidade (nome/avatar/tom/horário/canais/autonomia/handoff) 100% configurável por corretora; "Even" vira apenas dado de exemplo | Founder | **APROVADA** | Executa na Onda 2 junto do atendente (não em fase isolada) |
| D6 | E-commerce (UCP/Shopify/Storefront) fora do roadmap; remoção total em batch dedicado e reversível | Founder | **APROVADA** | Onda 1.5, paralela à SPEC-016, executável por Codex |
| D7 | Política global `residential_24h_standard_v1`: residencial + assistência 24h confirmada ⇒ eletricista, chaveiro, hidráulica como serviços padrão; governada, versionada, com override futuro por seguradora/produto/plano/corretora | Founder | **APROVADA** | Nasce na SPEC-016 |
| D8 | Voz e n8n congelados; migração da voz para backend próprio na Onda 3; remoção do n8n depois disso | Founder | **APROVADA** | |
| D9 | RAG/Knowledge: arquitetura definida agora (este doc §9); implementação por modelo mais barato sob SPEC + revisão do Fable | Founder | **APROVADA** | |
| D10 | Multi-provider de gestão (Quiver etc.): contrato `PolicyDataProvider` desenhado agora, implementado quando houver corretora com o sistema | Founder | **APROVADA** | Nenhum código novo pode acoplar em "infocap" o que é do contrato |
| D11 | Capability Registry como autoridade única; `tools_config` vira preferência visual; HTTP/MCP exigem capability | Fable | **APROVADA** | Onda 3 |
| D12 | Autonomia do líder técnico com gates: sem deploy sem aceite; migrations só com APPLY→VERIFY→ROLLBACK; provider real só em teste controlado autorizado; legado só sai com plano de rollback | Founder | **VIGENTE** | |
| D13 | Documentação enxuta: este programa + 1 SPEC ativa por vez; sem ADRs avulsos, sem relatórios repetidos | Founder + Fable | **VIGENTE** | |
| D14 | ResultVision = só referência histórica de contrato de dados; nunca reaproveitar o match por `nosnum` | Fable | **VIGENTE** | |

## 5. Ondas de produção (cada onda TERMINA em produção, não em relatório)

> Filosofia: poucas ondas grandes, cada uma entregando valor real e deployável. Nada de dezenas de microfases.

### Onda 1 — SPEC-016: Policy Intelligence end-to-end no Core  ← **ATUAL**
Cliente correto → apólice correta → contexto "ela" → InfoCap estruturada → PDF oficial quando necessário → Policy Facts mínimos → `residential_24h_standard_v1` → resposta humana → cache → E2E → deploy controlado na Resulta → rollback claro.
**Executor:** Fable (esforço alto). Detalhe completo em `docs/canon/specs/SPEC-016-policy-intelligence-core-vertical.md`.

### Onda 1.5 — Purga de legado (paralela, mecânica)
- Remover UCP/Shopify/Storefront: tools, services, schemas, rotas em `main.py`, bloco "SISTEMA DE COMMERCE" do prompt, referências em `graph.py`/`nodes.py`/`agents.py`.
- Remover `app/sandbox`, `app/embed` + `public/widget.js` + logos Smith (`smith-logo*.png`), `lib/mock/tenant-modules.ts` (verificar consumo antes).
- Critério: `npm run typecheck` + `npm run build` + suíte offline Python 100% verdes; nenhum endpoint de commerce respondendo; nenhum prompt menciona commerce.
- Rollback: branch dedicada; revert único.
**Executor:** Codex ou modelo econômico, guiado por batch fechado escrito pelo Fable. **Não misturar com a Onda 1 no mesmo branch.**

### Onda 2 — SPEC-017: Atendente externo no Smith (cérebro único de verdade)
- Portar para Python como módulos determinísticos: slot catalog, corridor step engine, message router (vira pré-classificador/guard), dossiê de handoff, dispatch readiness, action engine (dry-run).
- Agente `external_customer_attendant` roda no grafo Smith: LLM conduz a conversa COM inteligência plena; slots/corredores viram *ferramentas e contratos de resposta* (o guard garante que dado obrigatório foi coletado e que nada é prometido sem evidência — mesmo padrão do guard InfoCap que já funciona).
- Identidade configurável por corretora (D5): nome, avatar, tom, horário, canais, autonomia, handoff. Migração dos hard-codes "Even" no Portal Admin/rotas/slugs, com script de migração de dados reversível.
- WhatsApp: borda TS fina → backend → Smith. Envio real de resposta ao segurado com gate HITL configurável (autonomia por corretora). Acionamento de seguradora continua dry-run nesta onda.
- Runtime TS conversacional: desligado por flag após paridade comprovada em golden tests espelho (mesmos casos, mesmas saídas ou melhores).
**Executor:** Fable (esforço alto) + Codex nos portes mecânicos.

### Onda 3 — SPEC-018: Autoridade única + higiene de plataforma
- Capability Registry vira autoridade única (D11): HTTP tools e MCPs só entram no grafo com capability ativa; `tools_config` rebaixado a preferência visual; `allow_web_search` legado morre; catálogo TS deixa de ser fonte (só render do banco).
- Prompt Efetivo no Portal Admin (somente leitura, redigido, com tools realmente vinculadas e divergências "switch ligado / runtime não lê").
- Renomear capabilities para nomes funcionais (`policy.infocap.read`, `web.search`...) com aliases de compatibilidade.
- Migrar voz para backend próprio; remover `/api/n8n` + `n8nClient` (D8).
- Fatiar `infocap_connector.py` (4k linhas) em módulos por responsabilidade, sem mudar comportamento (testes offline como rede de proteção).
**Executor:** Fable desenha, Codex executa maioria; revisão adversarial do Fable.

### Onda 4 — SPEC-019: Auxiliares como Rotinas (o "Claude Rotinas" do AutoBrokers)
- **Auxiliary Engine**: executar qualquer Auxiliar instalado como agente `auxiliary` no grafo Smith, com capabilities declaradas no contrato (já existe `lib/auxiliaries/contract.ts` — vira contrato de banco).
- **Scheduler**: Celery beat (já no stack) para gatilhos cron por corretora + gatilho manual + gatilho por evento; timezone por corretora; logs de execução nas tabelas/UI já existentes (`execucoes`).
- **Aprovação humana**: rotinas `draft_only`/`approval_required` geram rascunhos para aprovação (reaproveita outbox/approvals do action engine portado).
- Migrar os 2 auxiliares hard-coded para o engine e abrir a galeria global: autoria no Blueprint Studio (Portal Admin) → publicação → instalação e personalização pela corretora no Dashboard (prompts, horários, conexões).
- Primeiros auxiliares de catálogo: Resumo de Atendimentos (migrado), Cobrança/parcelas em atraso (leitura de portal entra na Onda 5; versão 1 usa provider de gestão), Follow-up WhatsApp (migrado, com HITL).
**Executor:** Fable no engine/scheduler; Codex nos auxiliares de catálogo.

### Onda 5 — SPEC-020: Ações externas reais + Knowledge/RAG
- Portal Action Engine real: Browserbase + SessionRef + preflight + HITL + protocolo + retry + auditoria; começa por LEITURA (parcelas em atraso — a maior dor citada pelo Founder), depois abertura de assistência.
- Acionamento de seguradora via WhatsApp (canal da seguradora) com HITL.
- Implementação do RAG/Knowledge conforme §9, por modelo econômico sob SPEC.
- Novos canais WhatsApp (Meta oficial, Evolution) atrás da mesma borda.

## 6. Estratégia de migração do atendimento TS → Smith (detalhe da Onda 2)

1. **Inventário de paridade**: extrair dos módulos TS a lista de comportamentos garantidos (perguntas por slot, regras de risco, gates de envio) → vira matriz golden.
2. **Porte mecânico**: funções puras TS → Python 1:1 (`backend/app/attendance/` novo pacote), com os mesmos casos de teste espelhados. Sem "melhorar" durante o porte — porte primeiro, evolução depois.
3. **Inversão de controle**: no Smith, o LLM do papel `external_customer_attendant` conversa livremente; um **Attendance Response Contract** (mesmo padrão do Policy Response Contract) valida cada resposta: slot obrigatório pendente? risco alto detectado? promessa sem evidência? → guard corrige/substitui deterministicamente.
4. **Canal**: webhook Z-API → borda TS fina (normaliza, autentica) → backend → Smith com thread por caso (`company:case`).
5. **Paridade e corte**: rodar TS e Smith em sombra (mesmos inbounds simulados) até goldens iguais/melhores → flag corta para Smith → TS conversacional removido na onda seguinte.
6. **O que NUNCA muda**: fail-closed de identidade de apólice; nenhuma confirmação de cobertura sem evidência; nenhum envio externo sem gate; máscara de PII para público externo.

## 7. Estratégia de Auxiliares como rotinas globais (detalhe da Onda 4)

Modelo mental = Claude Rotinas: **autoria global** (equipe AutoBrokers cria no Blueprint Studio com o motor Smith) → **galeria** → **instalação por corretora** → **personalização** (prompt adicional, horários, conexões, limites, aprovação) → **execuções auditáveis** → **aprendizado** (memória por corretora + evolução global do template versionado).
Invariantes: auxiliar só acessa o que a capability do contrato declara; execução sempre logada com custo; side effects seguem a escada `none → draft_only → approval_required → external_action(HITL)`; template global versionado — corretora atualiza quando quiser (sem update forçado silencioso).

## 8. Estratégia do Portal Action Engine (detalhe da Onda 5)

Escada de risco: **ler → preparar → pedir aprovação → executar → provar**.
SessionRef/credenciais só via Vault; Browserbase como executor; preflight obrigatório (portal certo? apólice certa? dados mínimos?); toda execução gera evidência (screenshot/protocolo) vinculada ao caso; captcha/mudança de layout → fallback `human_broker_manual` sem drama. O assets TS de portal (registry, skills, canary, session vault) são a base conceitual — portados/adaptados quando a onda chegar.

## 9. Estratégia RAG/Knowledge (arquitetura AGORA, implementação DEPOIS — D9)

| Camada | Conteúdo | Escopo | Regra dura |
|---|---|---|---|
| Knowledge global | Curadoria AutoBrokers: seguros, produtos, procedimentos por seguradora | Todas as corretoras (leitura) | Nunca contém dado de corretora/cliente |
| Knowledge da corretora | Docs próprios, playbooks internos | Só a corretora | Isolamento por `company_id` em storage/Qdrant/busca |
| Evidência de apólice | PDF oficial vinculado a `policy_locator_hash` | Só a apólice/corretora | NUNCA aparece em busca ampla; só via fluxo de evidência |
| Memória | user/session/company/case (já existe MemoryService) | Por dono | Não vira "fonte de verdade" de cobertura |

Regras: RAG nunca confirma cobertura sozinho; toda resposta baseada em documento cita fonte+página; intake bruto só entra com curadoria/redaction; avaliação com golden set antes de ligar para todos. Implementação: modelo econômico, SPEC própria na Onda 5, revisão adversarial do Fable.

## 10. Congelado · Irreversível · Não agora

**Congelado**: n8n/voz (até Onda 3) · Smith V7 · Drive/Notion produtivos · novos conectores (até Onda 3) · prefetch em massa de PDFs.
**Irreversível (nunca reverter)**: P0/P0.1 · matcher humano só por `numapo` · locator estrito `provider:<...>` · resolução única de conexão no backend · envelope preservado · ausência honesta de cobertura · fail-closed em `identity_mismatch`.
**Não agora**: implementação Quiver/Segfy · portal com escrita real (Onda 5) · WhatsApp Meta oficial · criação de Auxiliar por prompt do usuário final · redesign visual amplo.

## 11. Critérios de produção e rollback (padrão para toda onda)

**Produção**: suíte offline 100% · goldens da onda 100% · E2E com stub 100% · teste real controlado aprovado pelo Founder + operador Resulta · checklist de aceite assinado · deploy com flag de rollback OU revert único documentado · logs sem PII verificados.
**Rollback**: cada onda entra atrás de flag ou em revert único; dados novos criados por uma onda precisam de plano de descarte seguro; migration nunca destrutiva no mesmo release que a usa (expand → migrate → contract).

## 12. Regras de trabalho do programa

1. **Uma SPEC ativa por vez** (a purga 1.5 é batch mecânico, não SPEC).
2. **Branch/worktree por onda**; nunca implementar no worktree de auditoria; `main` só recebe merge aprovado.
3. **Esforço por tarefa** (orientação ao Founder): arquitetura/SPECs/blocos críticos/revisão adversarial → Fable esforço alto; portes mecânicos, limpezas, CRUD, docs curtas → Codex/modelo econômico com batch fechado escrito pelo Fable.
4. Toda entrega fecha com: o que mudou · como foi verificado (comando + saída) · como reverter.
5. Gates do Founder (D12) valem para qualquer executor, inclusive o Fable.
