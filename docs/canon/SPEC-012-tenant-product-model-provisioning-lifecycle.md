# SPEC-012 — Modelo Canônico de Produto: Agentes, Templates, Tenants, Personalização e Provisionamento

> Status: canonical (planejamento) · Produto: AutoBrokers.ai · Sistema: AutoBrokers Intelligence OS (sobre runtime Smith)
> **Docs-only.** Nenhum código/migration/agente alterado neste turno. Fundamentado em inspeção read-only do repositório + Supabase canônico (`dcajcvlzcjbmyapmklil`).
> Data: 2026-06-21 · Modelo: Claude Opus 4.8 · base: `b80e734`
> Depende de: SPEC-002 (Auxiliares), SPEC-004 (Agent Intelligence/Context), SPEC-005 (Atendimento), SPEC-006 (Allianz Eletricista), SPEC-008 (Produção Global), SPEC-010 (RAG), SPEC-011 (Portal). Consolida o `tenant-activation-center-audit-and-two-batch-plan.md`.

---

## 0. Convenção de leitura
`[FATO]` confirmado no código/DB · `[DECISÃO]` canônica (aprovada pelo Founder) · `[PROPOSTA]` minha recomendação · `[LACUNA]` falta hoje · `[RISCO]` · `[FORA]` fora de escopo.

---

## 1. Decisão executiva (o modelo em 1 página)

O AutoBrokers é **composição**, não cópia. Tudo que é global vive como **template/blueprint global** e fica **disponível** a todas as corretoras; o que é da corretora é uma **instância/instalação** criada sob demanda. A configuração que o runtime usa é **derivada** (Effective Configuration), nunca duplicada.

```
Blueprint Global (versionado)
  + Guardrails imutáveis AutoBrokers
  + Variáveis da empresa (company_name, attendant_name, gender, pronoun, ...)
  + Overrides seguros da corretora (avatar, tom, mensagens, horários)
  + Capacidades instaladas (corredores/auxiliares ativados)
  + Conexões autorizadas (WhatsApp/portais/conectores da corretora)
  = Effective Configuration (o que o runtime executa)
```

Regra-mãe (não-negociável):
```
GLOBAL DISPONÍVEL ≠ TENANT INSTALADO ≠ TENANT ATIVO ≠ CANAL CONECTADO ≠ AÇÃO EXTERNA AUTORIZADA
```

Toda corretora **nasce** com exatamente **2 agentes próprios** (instâncias): **AutoBrokers** (Core) e **Even** (Attendance). Auxiliares, corredores e subagentes **NÃO** são copiados fisicamente por empresa — ficam globais e geram linha por tenant só quando **instalados/ativados**.

### [PROPOSTA — correção importante para o Founder]
Você pediu que cada empresa "nasça com TODOS os auxiliares/subagentes já criados". **Recomendo fortemente não duplicar fisicamente** auxiliares/subagentes por empresa — e isso **não tira nada da experiência**: na Galeria a corretora vê **tudo** disponível; ao "ativar", criamos a linha dela. Por quê:
- **Custo/escala:** 100 corretoras × 30 auxiliares = 3.000 linhas/configs para manter; com composição, são 30 templates + N instalações reais.
- **Atualização:** melhorar um auxiliar global atualiza todos instantaneamente; com cópias, viraria migração em massa.
- **Portal Admin limpo:** você vê por empresa **2 agentes reais + o que ela instalou**, não centenas de cópias.
O resultado visível é idêntico ao seu desejo ("tudo pronto e disponível"), mas **escalável e barato**. Essa é a única divergência do seu texto literal — adotada por ser melhor para o produto. Se discordar, é a decisão D-7 abaixo.

---

## 2. Glossário canônico [DECISÃO]
- **Blueprint (global, versionado):** definição-base de um agente (role, audience, prompt-template com variáveis, ferramentas, guardrails, defaults de modelo). Fonte da verdade do "padrão".
- **Agent Instance (por tenant):** linha em `agents` (company_id) derivada de um blueprint. Ex.: o AutoBrokers da Resulta.
- **Core:** Chat Principal interno (`agent_role='core'`, `agent_audience='broker_internal'`). Marca fixa "AutoBrokers".
- **Attendance:** Atendente externo (`agent_role='attendance'`, `agent_audience='insured_external'`). Padrão "Even".
- **SubAgent:** especialista interno do Smith (`is_subagent=true`), acionado por orquestrador; invisível ao cliente.
- **Auxiliary Template (global):** `auxiliary_templates`. **Tenant Auxiliary (instalado):** `tenant_auxiliaries`.
- **Corridor Template (global):** `corridor_templates`. **Tenant Corridor (instalado/ativado):** `tenant_corridors` [LACUNA — criar].
- **Skill / Capability Pack:** capacidade reutilizável (ex.: `session_login_verify`, `open_electrician_request`) ligada a corredor/portal/canal.
- **Connector Template / Tenant Connection:** `connector_templates` / `tenant_connections`.
- **Portal Account / SessionRef:** conta de portal por tenant + referência opaca de sessão.
- **Global Knowledge / Tenant Knowledge:** RAG global curado vs conhecimento privado da corretora.
- **Effective Configuration:** resultado da composição (§6); o que o runtime executa.
- **Provisioning:** criar o mínimo canônico de uma empresa (Core + Even).
- **Readiness / Activation / Pause / Revoke / Archive:** estágios de ciclo de vida.

---

## 3. Mapa de entidades e fontes da verdade
| Conceito | Estrutura (confirmada) | Global/Tenant | Criado quando | Editado por | Visível p/ corretora | Observação |
|---|---|---|---|---|---|---|
| Empresa | `companies` [FATO] | tenant | assinatura | master/dashboard | sim (próprios dados) | Resulta `04b5cdbc` |
| Equipe | `users_v2` [FATO] | tenant | onboarding | dashboard/master | sim | papéis (master/company_admin/member) |
| Core (AutoBrokers) | `agents` role=`core` [PROPOSTA] | tenant (instância) | provisionTenant | dashboard (seguro) | sim | hoje é o "Sandbox" legado |
| Attendance (Even) | `agents` role=`attendance` [FATO] | tenant (instância) | provisionTenant | dashboard (seguro) | sim | criado inativo (42X5B) |
| SubAgents | `agents` `is_subagent` [FATO] | ver §8 | sob demanda | master | não | recomendação: virar Skills/runtime, não cópia |
| Blueprint global | `agent-blueprints.ts` [FATO, genérico] | global | — | master/código | não | [LACUNA] role-aware + versão |
| Auxiliar global | `auxiliary_templates` [FATO] | global | master cria | master | vê na galeria | catálogo |
| Auxiliar instalado | `tenant_auxiliaries` [FATO] | tenant | corretora instala | dashboard | sim | execução/custo só aqui |
| Corredor global | `corridor_templates` [FATO] | global | master/Claude | master | vê no catálogo | scope=global |
| Corredor ativado | `tenant_corridors` [LACUNA — criar] | tenant | corretora ativa | dashboard | sim | runtime só usa ativados |
| Conector | `connector_templates`/`tenant_connections` [FATO] | global/tenant | — | dashboard | sim | Vault refs ocultas |
| Portal Account/SessionRef | `tenant_connections.connection_config` [FATO] | tenant | login assistido | dashboard | parcial (status) | sem segredo |
| Contatos seguradora | `insurer-contacts-global-seed` [FATO] | global | seed | master (futuro) | read-only | override por tenant futuro |
| Approvals/Handoff/Dispatch | `approval_requests`/`human_support_destinations`/`dispatch_packets` [FATO] | tenant | runtime | dashboard | sim | — |
| Conhecimento | `documents`/memória/Qdrant + RAG [FATO] | global+tenant | upload/curadoria | dashboard/master | sim (privado) | isolado por tenant |
| Custo/tokens | usage logging + `company_credits`/`credit_transactions` + `billing_service` [FATO] | tenant | cada chamada LLM | sistema | sim (saldo) | tag company_id+agent_id |
| Portal Admin | `app/admin/*` [FATO] | master | — | master | — | espelha canônico, não duplica |
| Dashboard | `app/dashboard` + TenantAppShell [FATO] | tenant | — | corretora | sim | DS-001 |

---

## 4. Lifecycle de empresa (provisionTenant)
```
Assinatura → company criada
→ provisionTenant(companyId) IDEMPOTENTE:
   - garante 1 Core (AutoBrokers) [migra o legado se existir]
   - garante 1 Attendance (Even), inativo
   - garante company_credits inicial (reusa billing)
   - NÃO instala auxiliares/corredores/subagentes (ficam globais/galeria)
→ corretora preenche dados mínimos
→ personaliza Core e Even (variáveis seguras)
→ instala/ativa corredores (tenant_corridors)
→ instala auxiliares (tenant_auxiliaries)
→ conecta canais (WhatsApp/portais)
→ adiciona conhecimento privado
→ checklist de readiness
→ ativação → operação → (pausa/cancelamento/arquivamento)
```
Casos: **empresa existente/Resulta** → provisionTenant migra Sandbox→Core e mantém a Even; **sem crédito** → opera mas bloqueia LLM real (reusa balance check existente); **canal desconectado/corredor não instalado** → Even não opera externamente; **suspensa** → tudo pausado. [FATO] `bootstrap-tenant` já é idempotente e cria o agente de chat — vira o caminho legado de `provisionTenant`.

---

## 5. Modelo de agentes

### 5.1 AutoBrokers (Core)
- `agent_role='core'`, `agent_audience='broker_internal'`, `allow_direct_chat=true`, `is_subagent=false`.
- **Nome de marca FIXO:** "AutoBrokers" [DECISÃO D-1/D-3]. Apresentação dinâmica: "Sou o AutoBrokers da {{company_name}}." (via `build_system_prompt`, que [FATO] já injeta company_name).
- **Editável pela corretora (seguro):** avatar, tom, objetividade, idioma, apresentação, conhecimento privado, contexto operacional, conectores autorizados.
- **Bloqueado:** nome "AutoBrokers", guardrails, isolamento multi-tenant, Vault, approval, regras de cobertura, instruções protegidas do Core, ferramentas sensíveis, flags globais.
- **Conhecimento:** global curado + tenant próprio autorizado; **nunca cross-tenant**; consome resumos/casos/métricas autorizados, não chats brutos indiscriminados [DECISÃO D-14].

### 5.2 Even (Attendance)
- `agent_role='attendance'`, `agent_audience='insured_external'`. Nasce **provisionada e inativa**.
- **Padrão:** nome "Even", apresentação feminina [DECISÃO D-4/D-5].
- **Editável (variáveis):** {{attendant_name}}, {{attendant_gender}}, {{attendant_pronoun}}, avatar, voz, tom, mensagem de abertura/encerramento, horários, handoff, corredores instalados, canais. Ex.: Resulta=Even, Autofleet=Joana, ABC=João [DECISÃO D-6].
- **Bloqueado:** guardrails de cobertura, evidência, approval, dispatch, Vault, gates, Skills críticas, isolamento.
- **Opera só quando:** ≥1 corredor ativado + canal conectado + readiness + gates/approval.

### 5.3 Variáveis de personalização [PROPOSTA — mecanismo central]
O prompt global do blueprint contém **placeholders canônicos**; a corretora só altera **valores**, nunca o texto protegido:
```
{{company_name}} {{attendant_name}} {{attendant_gender}} {{attendant_pronoun}} {{broker_brand}} {{business_hours}} {{handoff_target}}
```
Renderização no runtime (estender `build_system_prompt`/context). Os valores vivem na instância do agente (`context_package`/campos próprios). Assim, mudar "Even→Joana" no Dashboard reflete **em todo o sistema e no Portal Admin** sem tocar no prompt global. [FATO] a UI já tem "+ Inserir Variável" — formalizar o conjunto canônico.

### 5.4 Futuros agentes de atendimento [DECISÃO]
"Novo agente de atendimento" = **novo blueprint/Capability Pack/corredor/Skill**, não dezenas de instâncias por empresa. Uma nova família (ex.: Atendimento Auto) nasce como **blueprint global** + corredores; a corretora a recebe na galeria e ativa. Evita explosão de agentes.

---

## 6. Effective Configuration (resolver canônico) [PROPOSTA — chave anti-bug]
Função única (server-side) que compõe, com precedência explícita:
```
1. Blueprint global vN (role-aware)           [imutável p/ tenant]
2. Guardrails imutáveis AutoBrokers           [imutável]
3. Variáveis da empresa                        [tenant]
4. Overrides seguros (whitelist de campos)     [tenant]
5. Capacidades instaladas (corredores/aux)     [tenant]
6. Conexões autorizadas                         [tenant]
= Effective Configuration (runtime)
```
- **Versionamento:** cada instância guarda `blueprint_version` [FATO existe a coluna]. Atualização global → marca "update disponível / compatível / exige revisão" por tenant; **nunca sobrescreve** override do tenant.
- **Auditoria:** Portal Admin mostra a Effective Configuration resolvida (sem segredo).
- **Proteção:** a corretora só edita a whitelist (camadas 3/4); 1/2 são protegidas; rollback por versão.

---

## 7. Auxiliares (lifecycle) [DECISÃO + FATO]
```
auxiliary_templates (global, galeria)
→ corretora instala → tenant_auxiliaries (config local: horário, conector, equipe, limites, approval)
→ só a instalação executa, consome tokens e usa conectores
```
- Novo auxiliar global aparece **instantaneamente** na galeria de todos (sem cópia física).
- Auxiliar **exclusivo** de uma corretora = template `tenant-scoped` (visível só p/ ela; vendável sob medida) [DECISÃO D-9/D-11].
- Portal Admin mostra, por empresa, os **instalados** (+ custo/execuções).

## 8. Corredores, Subcorredores, Skills
```
corridor_templates (global) → tenant_corridors (ativado/pausado por tenant) [LACUNA — criar tabela]
```
- Runtime (`loadAvailableCorridors`) [FATO hoje traz todo global] passa a exigir **tenant_corridor ativo** [DECISÃO D-12].
- **[RISCO]** mudar isso sem auto-ativar a Resulta quebra o piloto → a migração ativa Allianz Residencial+Eletricista p/ Resulta.
- **SubAgents [PROPOSTA/D-13]:** especialistas de negócio (cobertura, coleta, dispatch, portal, evidência) = **módulos internos do runtime/Skills**, não linhas `agents` por empresa. Só viram instância quando forem configuráveis pela corretora. (Decisão de design: ver D-13.)
- Fluxo canônico Eletricista:
```
Allianz Residencial → Even → coleta (1 info por vez) → policy evidence → dispatch packet
→ resolveInsurerDispatchTarget (contato global) → WhatsApp Allianz / portal / humano
→ approval → resultado estruturado → caso atualizado
```
- **[LACUNA]** `resolveInsurerDispatchTarget` ainda não está ligado ao builder de dispatch → Batch 1.

## 9. RAG / Memória / Conhecimento
```
Conhecimento Global AutoBrokers (curado) + Conhecimento Global Seguradora
+ Conhecimento Privado da Corretora + Contexto do Caso + Evidência de Apólice
```
- Global = opt-in [FATO `knowledge_scope`]; **não copiado por tenant**.
- Core: global autorizado + tenant próprio. Even: só o pertinente ao atendimento/corretora.
- **Nunca** vaza memória/documento entre corretoras. RAG **nunca** confirma cobertura. [FORA: ingestão real = trilha RAG1+.]

## 10. Portal Admin vs Dashboard (matriz)
| Função | Dashboard (corretora) | Portal Admin (master) |
|---|---|---|
| Editar dados/Core/Even (variáveis seguras) | ✅ | ✅ (supervisão) |
| Instalar auxiliar / ativar corredor | ✅ | ✅ (ver/forçar) |
| Conectar WhatsApp/portal, Login Assistido | ✅ | ✅ (ver) |
| Aprovar canary, ver SessionRef/Vault/Browserbase | ❌ | ✅ |
| Editar contatos globais / criar corredor/Skill global | ❌ | ✅ |
| Ver custo/tokens/logs por empresa/agente | resumo próprio | ✅ completo |
| Ativar/suspender empresa | ❌ | ✅ |
Ambos leem a **mesma fonte canônica** [DECISÃO D-12/15]; Portal Admin **espelha** (não duplica). Toda edição no Dashboard altera o mesmo registro visto no Portal Admin.

### [PROPOSTA] Portal Admin — visão por empresa (rollup, sem duplicar)
Em Empresas → empresa: Core + Even (Effective Config) · corredores/auxiliares instalados · conexões/portais · saúde de SessionRef · conhecimento privado (contagem) · **consumo LLM + custo por agente/auxiliar/corredor** · casos/handoffs/approvals · **readiness score**.

## 11. Dashboard da corretora (telas)
Sidebar (DS-001): **AutoBrokers · Atendimentos · Auxiliares · Personalização**. Em Personalização (lista→detalhe, mobile-first): Dados da corretora · Equipe · Aprovadores · **AutoBrokers (Core)** · **Even (Atendimento)** · WhatsApp · Seguradoras (→ Portais/Corredores/Contatos) · Portais conectados · Corredores (ativar/pausar) · Auxiliares (galeria/instalados) · Conhecimento · Handoff · **Checklist de ativação (readiness)** · Custos e uso. Cada tela documenta: fonte de dados · API existente a reusar / a criar · permissão · global vs tenant · editável vs read-only · gatilhos de approval · critério de aceite.

### [PROPOSTA — alto valor comercial] Readiness Score
Card de "Ativação: X%" com checklist (dados ✓, Core personalizado, Even personalizada, ≥1 corredor ativo, WhatsApp conectado, portal conectado, aprovadores definidos). Aumenta ativação/percepção de valor no onboarding.

## 12. Migração da Resulta (segura)
```
AutoBrokers Sandbox (id atual)  → AutoBrokers Core (mesmo agent_id; muda role=core, audience=broker_internal, nome de exibição/prompt p/ blueprint Core; preserva conversas/custos/docs)
Atendimento AutoBrokers — Resulta → Even (ativa via provisionamento; aplica variáveis padrão)
Allianz Residencial + Eletricista → tenant_corridors ATIVOS (auto-ativados na migração)
Contatos globais → dispatch resolver ligado
WhatsApp → preparado p/ 42X5C
```
- **[DECISÃO D-15/D-16]** preservar `agent_id`; **aposentar o bootstrap-sandbox** (vira `provisionTenant` ou fixture-only) p/ não reconverter Core em Sandbox.
- Rollback: snapshot dos campos antes da migração + reversão por script. [RISCO] preservar histórico/custos ligados ao agent_id.

## 13. FinOps / custo [FATO — reusar]
Toda chamada LLM (Core, Even, Auxiliar, Corredor, Skill, vision/audio) já passa por usage logging + `company_credits`/`credit_transactions` (`billing_service`). [DECISÃO D-20] **garantir tag `company_id` + `agent_id` (+ `auxiliary_run_id`/`corridor_run_id`) em toda chamada**, para o Portal Admin/FinOps somar por empresa/agente/auxiliar/corredor. Conectores globais usam credencial AutoBrokers; conexões da corretora são privadas. [LACUNA] confirmar que auxiliares/corredores propagam agent_id no log (auditar no Batch 1).

## 14. Plano de implementação (2 batches)

### Batch Tenant Activation 1 — Núcleo canônico (backend/dados/runtime)
- **Objetivo:** provisionamento canônico + ativação por tenant + custo atribuível + dispatch ligado.
- **Escopo:** (1) blueprints **role-aware** (Core/Attendance) estendendo `agent-blueprints.ts` (agent_role/audience/blueprint_version/variáveis) — sem estrutura paralela; (2) `provisionTenant(companyId)` idempotente (Core+Even via backend `/api/agents/`); (3) **migração Resulta** (Sandbox→Core, Even ativa) com preservação de id + rollback; (4) aposentar/realiar bootstrap-sandbox; (5) **migration `tenant_corridors`** (+verify+rollback+RLS) e ajuste de `loadAvailableCorridors` (auto-ativa Resulta); (6) **Effective Configuration resolver** + renderização de variáveis; (7) **wire `resolveInsurerDispatchTarget`** no dispatch packet (dry-run); (8) garantir tag company_id+agent_id no usage logging.
- **Banco:** `tenant_corridors` (migration versionada, não aplicada automaticamente). 
- **Testes:** provisionamento idempotente; runtime só usa corredor ativado; Core≠Even na seleção; variáveis renderizam; dispatch resolve destino global; custo tagueado; nada real enviado.
- **Aceite:** empresa nova nasce com Core(AutoBrokers)+Even; corredor global só opera se ativado; Resulta migrada sem perder histórico; gates `false`.
- **[FORA]** UI do Dashboard, WhatsApp real, RAG ingestão.

### Batch Tenant Activation 2 — Dashboard da corretora (UI)
- **Objetivo:** corretora opera tudo no próprio painel (DS-001, mobile-first), refletindo no Portal Admin.
- **Escopo:** telas §11 (personalização de Core/Even por variáveis; instalar auxiliar; ativar/pausar corredor; conectar WhatsApp/portal via Login Assistido; conhecimento; handoff; **readiness score**) + rollup por empresa no Portal Admin. Reusa APIs/resolvers; sem duplicar dados; sem expor engenharia.
- **Banco:** idealmente nenhum (usa Batch 1). 
- **Testes:** isolamento tenant; corretora não vê segredo; editar Even reflete no Portal Admin; ativar corredor libera runtime; readiness.
- **Aceite:** Resulta entra, personaliza, ativa e vê readiness sem telas técnicas.
- **Relação:** consome Batch 1; Portal usa Login Assistido; WhatsApp usa 42X5C (pós-pagamento Z-API).

> Após Batch 1 já é possível o **42X5C** (canary WhatsApp) com Z-API paga. Batch 2 (Dashboard) pode vir antes ou depois do 42X5C [decisão D-18].

## 15. Testes de aceite do Founder (após os 2 batches)
```
Criar empresa nova → Core nasce "AutoBrokers da {empresa}" + Even provisionada inativa
Auxiliar global aparece na Galeria de todas; não instalado não executa nem cobra
Ativar corredor → runtime passa a selecioná-lo; sem ativar → não opera
Mudar "Even→Joana/João + masculino" no Dashboard → reflete no Portal Admin (mesmo registro)
Personalizar Core (tom/avatar/conhecimento) → reflete no Portal Admin
Dados/conversas de uma corretora não aparecem para outra
Portal conectado é privado; WhatsApp não envia sem gates/consent/approval
Dispatch usa o contato global correto da seguradora
Custo de LLM aparece por empresa e por agente/auxiliar/corredor no Portal Admin
```

## 16. Decisões que dependem do Founder
- **D-7:** Confirmar **não duplicar** auxiliares/subagentes por empresa (galeria global + instalação por tenant). *Recomendo SIM.*
- **D-13:** SubAgents de negócio como **módulos internos/Skills** (não linhas `agents` por empresa)? *Recomendo SIM* (mais limpo/escalável; ainda permite especialistas configuráveis no futuro).
- **D-A:** Ordem após Batch 1 — **Batch 2 (Dashboard) antes ou depois do 42X5C**? *Recomendo: Batch 1 → 42X5C (piloto WhatsApp Resulta) → Batch 2*, para validar receita rápido; mas se a prioridade é "entregar para a Resulta operar sozinha", Batch 2 antes.
- **D-B:** Identidade inicial: Core="AutoBrokers da {empresa}"; Even feminino padrão — confirmado. Avatar/voz padrão da Even? (posso definir um default neutro).
- **D-C:** Confirmar migração da Resulta (Sandbox→Core no mesmo id; aposentar bootstrap-sandbox).
- **D-D:** `tenant_corridors` (recomendado) vs `permission_grants` — *recomendo `tenant_corridors`* (responde "o que a corretora contratou/ativou", não "quem pode").

---

## 17. Itens fora de escopo desta SPEC [FORA]
Ingestão real de RAG (RAG1+); ação de negócio real em portal (depende de credencial + Skills); Evolution Go provider; dashboard visual "perfeito" (refino pós-MVP); auxiliares específicos pagos (modelo previsto, criação sob demanda).

## 18. Conclusão
A espinha dorsal da auditoria está correta. Esta SPEC fecha o **ciclo de vida** (template→instância→instalação→versão→Effective Config), a **personalização por variáveis** (Even/Joana, AutoBrokers da {empresa}), o **custo atribuível**, o **espelho Portal Admin sem duplicação** e a **migração segura da Resulta** — viabilizando **2 batches** de implementação sem reabrir arquitetura. Próximo passo: aprovar D-7/D-13/D-A e executar **Batch Tenant Activation 1**.
