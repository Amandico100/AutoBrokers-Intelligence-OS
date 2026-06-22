# SPEC-013 — Global Blueprints, Capability Registry & Blueprint Studio
### Como o AutoBrokers, a Even e os Auxiliares são criados UMA vez (global) usando o motor do Smith, e distribuídos a todas as corretoras — sem estrutura paralela

> **Status:** Proposta (aguardando aprovação do Founder). **Sem código, sem migration aplicada, sem mudar a Resulta.**
> **Autor:** Claude (Opus 4.8), como líder técnico · **Data:** 2026-06-22 · **Base:** commit `66690d0` (TA2-C)
> **Relaciona:** SPEC-012 (tenant product model & provisioning), `lib/admin/agent-blueprints-canonical.ts`, `lib/admin/provision-tenant.ts`.

---

## 0. TL;DR (em uma frase)
Vamos **autorar o AutoBrokers Global, a Even Global e os Auxiliares Globais dentro de uma empresa-plataforma usando o MESMO editor de agentes do Smith** (com Identidade/Modelo/Personalidade/Memória/Segurança/HTTP Tools/MCP/Especialistas), **publicar isso como uma versão (release)** e **distribuir para todas as corretoras por rollout** — preservando a personalização local de cada corretora. Os **conectores** (Notion, Drive, Firecrawl, InfoCap, Quiver…) deixam de ser configurados soltos por agente e passam a um **Capability Registry**: a corretora conecta **uma vez** e a capacidade fica disponível para todos os agentes/auxiliares que tiverem direito a ela.

**A única decisão de produto que preciso que você aprove está na seção 11.** O resto é arquitetura que eu recomendo como líder.

---

## 1. O problema (em linguagem clara)
Hoje, quando você abre **Portal Admin → Empresa Resulta → Agentes → AutoBrokers → (abas Identidade/Modelo/HTTP Tools/MCP…)**, você está editando **o agente da Resulta**, não o padrão global. Se você "melhorar" ali, **só a Resulta muda**. As outras corretoras (e as futuras) não recebem nada. Pior: você pode achar que mexeu no global e não mexeu.

Ao mesmo tempo:
- **Não há um lugar visual** para editar o "AutoBrokers padrão" — ele só existe em código (`agent-blueprints-canonical.ts`).
- A página **Auxiliares Globais** parece um editor de contrato/ficha, **separado** do motor de agentes do Smith. Você sente (com razão) que é uma estrutura paralela.
- Os **conectores** estão no Dashboard, mas conectar um (ex.: Notion) **não** liga automaticamente o agente — porque tools/MCP do agente vivem em outra estrutura.

O risco que você nomeou — **"Frankenstein"** — é real **se** continuarmos criando telas sem fechar esta arquitetura. Esta SPEC fecha.

---

## 2. O que é VERDADE hoje (verificado no banco, não no "achismo")
| Fato verificado | Implicação |
|---|---|
| `agents.company_id` é **NOT NULL** | **Não existe agente global "sem empresa".** Autoria global precisa morar dentro de uma empresa-plataforma. |
| Já existe a empresa **"AutoBrokers Global Knowledge"** (`b1d308a5-…`, ativa) | Já temos uma empresa-plataforma — **não precisamos criar do zero**; podemos promovê-la (ou um irmão dedicado) a **Blueprint Studio**. |
| Existem `agent_http_tools`, `agent_mcp_connections`, `agent_mcp_tools`, `agent_delegations`, `agents.tools_config` | O **motor de tools/MCP/subagentes do Smith é real e robusto**. É ESTE que vamos reutilizar. Nada de motor novo. |
| `auxiliary_templates` **não** referencia nenhum agente Smith (execution_mode = `manual` em todos) | Os Auxiliares Globais hoje **não usam** o motor de agentes. É a estrutura paralela que te incomoda. Vamos religá-los ao Smith. |
| Conectores vivem em **2 planos**: Vault (`connector_templates`/`tenant_connections`) **e** por-agente (`agent_http_tools`/`agent_mcp_*`) | Por isso "conectar no Dashboard" não habilita o agente. Precisam ser **unificados** por um Capability Registry. |
| Não há tabela de `blueprint`/`release`/`capability` | São conceitos **novos e pequenos** que esta SPEC define (a menor extensão canônica possível). |

---

## 3. Princípios canônicos (as regras que não podem ser violadas)
1. **Um único motor: o Smith.** Agentes, subagentes, HTTP tools, MCP, memória, RAG, delegação, custos e logs já existem no Smith. **Proibido criar motor paralelo.** Tudo (Core, Even, Auxiliares) roda como agente/subagente Smith.
2. **Catálogo global ≠ instância do tenant ≠ ativo ≠ canal conectado ≠ ação externa autorizada** (regra do SPEC-012, mantida).
3. **Global é autorado uma vez** (no Studio) e **distribuído por versão/rollout**. A corretora **recebe**, não recria.
4. **Personalização local é sagrada.** Um rollout global **nunca** apaga tom, avatar, nome da Even, conhecimento privado, conectores, equipe, handoff ou custos da corretora.
5. **Segredo nunca toca o tenant nem o prompt.** Credenciais sempre no Vault; capacidades referenciam, nunca expõem.
6. **Conectar uma vez, reutilizar em tudo.** Se a corretora conecta o Notion/Firecrawl, qualquer agente/auxiliar que tenha direito àquela capacidade já a usa — sem reconfigurar.
7. **A corretora não cola URL de MCP, API key ou tool arbitrária.** Capacidades vêm do registro homologado.

---

## 4. Arquitetura-alvo

### 4.1 Blueprint Studio (empresa-plataforma de autoria)
Uma empresa **da plataforma** (não-cliente, não-cobrável, oculta da listagem de corretoras), marcada com uma flag `is_platform`/`kind='platform'`. **Recomendação:** promover/usar a já existente **"AutoBrokers Global Knowledge"** como o **AutoBrokers Blueprint Studio** (ou criar uma irmã dedicada — ver decisão 11.B).

Dentro do Studio você usa **o editor de agentes do Smith que você já vê nos prints** — todas as abas — para construir e **testar de verdade**:
```
AutoBrokers Blueprint Studio (empresa-plataforma)
├── AutoBrokers Global Core      (agente Smith — chat principal)
├── Even Global Attendance       (agente Smith — atendimento)
├── Auxiliar Global de Pesquisa  (agente/subagent Smith)
├── Auxiliar Global de Follow-up (agente/subagent Smith)
├── Subagentes técnicos          (delegações)
├── HTTP Tools / MCP homologados (agent_http_tools / agent_mcp_*)
└── Ambiente de teste/sandbox
```
Aqui você **mexe à vontade** com a estrutura robusta do Smith. O Studio é o "laboratório oficial".

### 4.2 Blueprint + Release (versionamento)
Quando o agente do Studio fica bom, você **publica uma versão**. A publicação gera um **release sanitizado** (sem segredo): prompt-base, guardrails, conjunto de **capacidades** declaradas, política de modelo, e a **especificação de variáveis** que o tenant pode ajustar.
- Os blueprints de hoje em código (`autobrokers-core-v1`, `even-attendance-v1`) viram **o seed da v1** — nada se perde.
- Novo conceito mínimo: `agent_blueprint_release` (chave + versão + artefato sanitizado + changelog + nível de risco). É a "ponte" que faltava entre "código" e "estúdio visual".
- Instâncias das corretoras passam a referenciar `blueprint_key + blueprint_version` (o campo `blueprint_version` **já existe** em `agents`).

### 4.3 Instâncias por corretora (já funciona)
O provisionamento automático (TA2-C) já cria, por corretora, **AutoBrokers Core (ativo)** + **Even (inativa)** a partir do blueprint — sem copiar dados/corredores/conectores de ninguém. Isso **continua igual**; só passa a citar a versão publicada.

### 4.4 Rollout / versionamento (a política)
```
AutoBrokers Global v1  →  Resulta v1, João v1, Autofleet v1
Você publica v1.1 no Studio:
  • Guardrail/segurança               → atualização AUTOMÁTICA para todos
  • Melhoria de prompt-base           → rollout CONTROLADO (sandbox → Resulta → demais), preservando personalização local
  • Nova capacidade de baixo risco    → fica disponível no catálogo (ativa por política/plano)
  • Capacidade com custo/ação externa → catálogo + exige habilitar/conectar/approval por corretora
  • Mudança grande de comportamento   → rollout por lote, sandbox primeiro
```
Efetivo de cada corretora = **release global** ⊕ **variáveis/overrides locais** ⊕ **conhecimento/conectores locais**. (É o mesmo princípio de "Effective Configuration" do TA2-A, agora versionado.)

### 4.5 Capability Registry (unifica os conectores) — o coração da simplificação
Um **catálogo global de capacidades** (Pesquisa Web, Firecrawl, Notion, Google Drive, InfoCap, Quiver, leitura de documentos, APIs de seguradora, MCPs homologados…). Cada capacidade declara:
```
- provider e como autentica (credencial da PLATAFORMA no Vault, ou conexão DA CORRETORA no Vault)
- quem pode usar (quais blueprints/agentes)
- escopo (somente leitura? ação externa? domínios? limites/rate)
- custo (atribuído por company_id + agent_id — FinOps já existe)
- risco, approval/HITL, auditoria
```
**Como resolve a sua dor dos conectores:**
- A corretora vê uma lista simples de **Integrações** (ex.: "Conectar Notion", "Conectar Google Drive"). Conecta **uma vez** (OAuth/secret no Vault).
- A partir daí, **todo agente/auxiliar que declara a capacidade "Notion" já a usa** — sem reabrir aba de MCP/HTTP por agente, sem colar URL/token.
- As abas **HTTP Tools / MCP** do editor (que hoje são livres) passam, **nas instâncias**, a ser **"selecionar do registro"** (governado). No **Studio**, elas continuam plenas (lá é onde se homologa a capacidade).
- Capacidades com credencial **da plataforma** (ex.: Firecrawl numa chave nossa) ficam disponíveis sem a corretora ver chave nenhuma; só pagam o uso.

### 4.6 Auxiliares = produto sobre o runtime Smith (acaba a estrutura paralela)
```
Auxiliar (o que aparece na Galeria)  =  PRODUTO (contrato, governança, distribuição)
Agente/Subagente Smith               =  RUNTIME que executa o trabalho
Vault + Capability Registry          =  segredos, conexões, permissão, approval, auditoria
```
Fluxo canônico para um Auxiliar avançado (ex.: scraping com Firecrawl):
```
1. Criar Agente/Subagente no Blueprint Studio (editor Smith completo)
2. Dar prompt, memória, capacidades (Firecrawl via registry/Vault), delegações, regras
3. Testar no Studio (sandbox), validar custo/limite/HITL/auditoria
4. Publicar como Auxiliar Global (release sanitizado, sem segredo)
5. Aparece na Galeria de TODAS as corretoras
6. A corretora instala → cria runtime PRÓPRIO dela (agente/subagent Smith no tenant)
7. Conectores/custos/dados isolados por corretora
```
- Auxiliares **simples** (ex.: "Resumo de Atendimentos", read-only) podem continuar como executor específico — não precisam de subagente complexo.
- Extensão mínima: `auxiliary_templates` ganha um vínculo opcional ao blueprint de origem (`source_blueprint_key`/`execution_mode='smith_agent_blueprint'`), e o botão **"Publicar Agent existente"** passa a **publicar um agente do Studio** como auxiliar. Assim a página de Auxiliares Globais deixa de ser "paralela": ela vira a **vitrine/governança** de agentes Smith autorados no Studio.

### 4.7 Even (mesmo modelo do Core)
A Even **já é um agente Smith real** por corretora (role `attendance`). Ela só está **mal exibida** no Portal Admin. No modelo novo: **Even Global** vive no Studio (editável com o editor Smith), publica versão, e cada corretora tem sua **Even instância** (personalizável no Dashboard). O System Prompt da Even passa a ser **editável no Studio** (global) e **ajustável por variáveis** no tenant — exatamente o que você pediu ("se eu não gostar de como a Even responde, mexo nela").

---

## 5. Portal Admin — nova arquitetura de navegação (separar Global de Instância)
```
Portal Admin
├── Blueprint Center  ← NOVO (global, só master)
│   ├── AutoBrokers Global   (abre o agente do Studio no editor Smith)
│   ├── Even Global          (idem)
│   ├── Auxiliares Globais    (galeria/governança ligada ao Studio)
│   ├── Capability Registry   (tools/MCP/conectores homologados)
│   └── Releases & Rollout     (versões, changelog, lotes)
│
└── Empresas → [Empresa] → Agentes  ← INSTÂNCIA (por corretora)
    ├── AutoBrokers (Chat Principal · blueprint autobrokers-core-v1 · instância: <empresa>)
    └── Even (Atendimento · blueprint even-attendance-v1 · ativa/inativa)
```
Correções obrigatórias na visão de instância:
- **Mostrar a Even** (mesmo inativa) no rollup de agentes da empresa.
- **Esconder o slug legado** `autobrokers-sandbox` como info principal (mostrar "AutoBrokers · Chat Principal · blueprint v1 · instância: Resulta").
- **Proteger as abas técnicas** da instância: edição de prompt-base/guardrails/capacidades é do **Blueprint Center**; na instância só a personalização segura (espelho do Dashboard) + ações de master explicitamente autorizadas. Isso elimina o risco de "editei a Resulta achando que era global".

---

## 6. Conectores: do caos de 2 planos para 1 modelo
**Hoje:** (a) Vault/`tenant_connections` (Dashboard "Conectores") e (b) `agent_http_tools`/`agent_mcp_*` (abas do agente) — desconexos.
**Alvo:** o **Capability Registry** é a fonte única. Conexões da corretora ficam no **Vault** (uma vez). Cada blueprint declara **capacidades**; o runtime resolve "capacidade → conexão do tenant (ou credencial da plataforma) → tools/MCP" automaticamente. As abas por-agente viram **seleção de capacidades homologadas**, não configuração livre. Resultado: **conectou uma vez, vale para tudo**.

---

## 7. Segurança, isolamento e LGPD
- Tenant nunca vê segredo/token/cookie/URL de MCP/credencial; só "conectado/não conectado".
- Cada capacidade tem escopo, custo (FinOps por company+agent), risco, approval/HITL e auditoria.
- Isolamento multi-tenant preservado: instância de uma corretora nunca lê dados de outra; o Studio é plataforma e **não** se mistura com dados de cliente.
- Rollout sempre **sandbox-first**; guardrails só endurecem, nunca afrouxam por personalização local (já garantido pelo "guardrails-after-variables" do TA2-B).

---

## 8. Migração e compatibilidade (nada quebra)
- Instâncias atuais (Resulta) continuam funcionando; passam a citar `blueprint_version`.
- Slug `autobrokers-sandbox` é mantido no banco (compat) mas **deixa de ser exibido** como rótulo.
- Blueprints de código viram seed da v1 — sem reescrever o que existe.
- Toda migration nova entra como **runbook (APPLY/VERIFY/ROLLBACK)**, nunca aplicada por mim.

---

## 9. Onde eu DISCORDO / MELHORO o GPT (liderança)
1. **Reutilizar a empresa-plataforma que já existe** ("AutoBrokers Global Knowledge") em vez de criar uma nova do zero — menos entropia. (GPT propôs criar uma; eu prefiro promover a existente, ou criar uma irmã só se você quiser separar "conhecimento global" de "studio de agentes".)
2. **Release sanitizado como artefato de 1ª classe** (`agent_blueprint_release`), não só "uma empresa modelo". Sem isso, "rollout" vira cópia manual frágil. Esta é a peça que realmente evita o Frankenstein.
3. **Capability Registry unificando os DOIS planos de conector** (Vault + tools por-agente). O GPT falou de catálogo de capacidades, mas não destacou que **hoje existem dois sistemas desconexos** — essa é a raiz do seu incômodo e a SPEC trata explicitamente.
4. **Religar Auxiliares ao Smith via "Publicar Agent existente"** (botão que já existe na tela!) em vez de manter o modal como autor — aproveita o que já está lá e mata a sensação de paralelo.
5. **Proteção da instância** no Portal Admin (abas técnicas read-mostly por corretora) como item de segurança de produto, não só estética.

---

## 10. Plano em fases (sequência recomendada — NÃO executar agora)
```
FASE A (esta SPEC)         → fechar arquitetura. Sem código.
FASE B (1 batch grande)    → Blueprint Studio + agent_blueprint_release + Blueprint Center (Portal Admin)
                              + separar Instance Editor de Blueprint Editor + mostrar Even + esconder slug legado.
                              (inclui concluir o TA2-C pendente: Aprovadores UI, Auxiliares lifecycle, telas WhatsApp/Portais, FinOps amplo)
FASE C (1 batch)           → Capability Registry + unificação de conectores (connect-once-reuse).
FASE D                     → 1º Capability Pack real (Pesquisa Web / Firecrawl) — quando você quiser.
FASE E                     → Auxiliares Globais estratégicos autorados no Studio.
PARALELO                   → 42X5C (Z-API + canary WhatsApp) quando a Z-API for paga — independente disto.
```
Observação: o **lifecycle de Auxiliares** depende desta arquitetura — por isso é certo pausar a "continuação do TA2-C" e fazer a Fase B junto.

---

## 11. Decisões que preciso de você (Founder)
**11.A — Política de evolução global (recomendo APROVAR):**
```
• Segurança/guardrails globais        → atualização automática para todas as corretoras
• Melhoria de prompt-base global      → rollout controlado (sandbox→Resulta→demais), preservando personalização local
• Novas Tools/MCP/APIs/conectores     → catálogo global; ativadas por política/custo/conexão/approval; nunca por edição livre da corretora
• Mudanças locais no Dashboard        → afetam só a própria corretora
```
**11.B — Onde fica o Studio:** (1) **Promover "AutoBrokers Global Knowledge" a Blueprint Studio** (recomendado, menos entropia); ou (2) criar uma empresa-plataforma **dedicada** "AutoBrokers Blueprint Studio" e deixar a Global Knowledge só para conhecimento global. 

**11.C — Profundidade do Capability Registry agora:** começar **enxuto** (só declarar capacidades + connect-once para Notion/Drive/Firecrawl) ou já modelar custo/approval/limites completos na Fase C.

---

## 12. O que NÃO fazer agora (até você aprovar)
- Não editar o agente da **Resulta** (System Prompt, HTTP Tools, MCP, WhatsApp, Modelo, Segurança, Especialistas, slug). Mudança ali é **local** e pode virar template acidental.
- Não criar Tools/MCP/conectores soltos por agente.
- Não criar nenhum motor de agentes novo.
- Não aplicar migration no banco; não ligar Z-API/Browserbase/portal.

---

### Resumo de uma linha para você
Você terá **um único lugar** (Blueprint Studio, com o editor Smith de verdade) para criar e melhorar o **AutoBrokers, a Even e os Auxiliares** — e **um botão de publicar versão** que entrega isso a todas as corretoras, com **conectores que se ligam uma vez e valem para tudo**, sem nunca transformar a Resulta no template de todo mundo.
