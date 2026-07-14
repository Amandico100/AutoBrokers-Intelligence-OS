# SPEC-036 — Auditoria profunda do Portal Admin + Plano de execução (com o design novo)

**Status:** AUDITORIA CONCLUÍDA — plano aguardando liberação do founder
**Data:** 2026-07-14 · **Insumos:** código real (24 rotas), banco real (Supabase), HTMLs do Claude Design (Portal Admin + Memórias)

---

## 1. O que a auditoria encontrou (fatos, não achismo)

### 1.1 Banco de dados — a verdade sobre as "empresas técnicas"
Só existem **4 empresas**: RAFAEL SEGUROS (teste, 100 conversas), **Resulta Seguros** (real, 38 conversas, 8 docs), e as duas técnicas:
- **AutoBrokers Blueprint Studio** — VAZIA (0 conversas, 0 docs). É a "oficina": empresa onde um auxiliar global é construído antes de ser publicado. A máquina em volta dela FUNCIONA: `auxiliary_templates` tem 5 templates publicados e `tenant_auxiliaries` tem 5 instalados nas corretoras — é o fluxo que abastece a Galeria de Auxiliares do dashboard (SPEC-013/019). **Veredito: MANTER a função, esconder da lista comum** (flag `empresa técnica`, seção própria).
- **AutoBrokers Global Knowledge** — VAZIA e sem uso no código. Era a ideia antiga de hospedar o conhecimento global antes do desenho de escopos (SPEC-003). **Veredito: REAPROVEITAR** como dona da ingestão do RAG global (o chat RAG do founder subirá os documentos globais por ela até a UI de escopo existir) — ou arquivar se preferirem. Recomendo reaproveitar: zero risco e resolve a ingestão global da Onda 3.

### 1.2 "Rotinas Prontas" vs "Auxiliares Globais" — NÃO são a mesma coisa (mas moram juntas)
- **Auxiliares Globais** (912 linhas) → `auxiliary_templates` → abastece a **Galeria** do dashboard (auxiliares completos).
- **Rotinas Prontas** (255 linhas) → `routine_templates` (3 rotinas) → abastece as **Rotinas** do dashboard (agendamentos padrão).
Ambas vivas e consumidas pelo dashboard. **Veredito: FUNDIR numa página "Catálogo Global"** com abas (Auxiliares / Rotinas / Blueprints) — 3 páginas viram 1.

### 1.3 Consolidações já meio-feitas (bom sinal)
`integrations` e `documents` **já são redirects**; `connectors` só aninha o portal-browser. A direção da SPEC-035 já tinha começado organicamente — vamos terminar direito.

### 1.4 Páginas nativas Smith que FUNCIONAM e são a base (não mexer na lógica, só no visual)
- **FinOps** (1.584 linhas — a mais rica do admin): custo de LLM por corretora. **Intocável na função**; vira a aba principal do hub Financeiro.
- **Companies** (1.640): o coração — vira o **cockpit da corretora**.
- **Conversations** (1.193) + conversation-logs (723) + logs (222): fundem em "Conversas" com abas.
- billing (823) + costs (517): entram no hub Financeiro junto do FinOps.

### 1.5 Portal Browser — Registry & Contas (685 linhas)
É a UI real do motor de portais (SPEC-020/023 — relay, execução real, skills, contas). `portals`=17, `portal_accounts`=1. **Veredito: MANTER** — vira "Portais (motor)" dentro de Conexões.

### 1.6 Prompt Efetivo (285 linhas)
Ferramenta de debug útil (mostra o prompt final por agente). **Veredito: MANTER** dentro do hub Inteligência (aba "Prompt efetivo").

### 1.7 O que os agentes novos já estão produzindo (e não tem onde aparecer)
`conversation_scorecards` **já tem registros reais** (Auditor rodou em produção!), `broker_insights`/`ura_maps`/`playbook_overlays` prontos e aguardando eventos. Confirma a urgência das 3 páginas novas do design.

---

## 2. Mapa final: 24 rotas → 10 destinos

| # | Página final (nav nova) | Absorve |
|---|---|---|
| 1 | **Central de Agentes** (NOVA — design pronto) | — |
| 2 | **Acionamentos ao vivo** (NOVA — design pronto) | — |
| 3 | **Insights · Garimpo** (NOVA — design pronto) | — |
| 4 | **Corretoras** (cockpit por corretora, abas) | companies + partes de billing/knowledge por corretora |
| 5 | **Conversas** (abas: Ao vivo / Logs / Sistema) | conversations, conversation-logs, logs |
| 6 | **Financeiro** (abas: FinOps / Cobrança / Custos) | finops, billing, costs |
| 7 | **Conexões** (abas: WhatsApp / Portais-motor / Canais de seguradora) | integrations*, portal-browser, insurer-action-channels |
| 8 | **Inteligência** (abas: Catálogo Global [Auxiliares+Rotinas+Blueprints] / Agentes / Prompt efetivo) | auxiliares, routine-templates, blueprint-center, agent, prompt-effective |
| 9 | **Conhecimento (RAG)** | knowledge-base, documents* |
| 10 | **Pessoas** (abas: Usuários / Pendentes / Equipe) + Configurações/Legal | all-users, pending-users, team, settings, legal-documents |

(*) já eram redirects. Rotas antigas → redirect 1:1 (nada quebra; bookmarks continuam).

---

## 3. Design system extraído do Claude Design (aplicar em TODO o admin)

Fundo `#06080C` / superfícies `#0B0F15` / bordas `#161D28` · fontes **Geist + Geist Mono** · cores de agente/semânticas: azul `#7FB7E8`, dourado `#E2A94F`, verde `#43C08C`, vermelho `#E06B6B` · sidebar 232px com status "PRODUÇÃO · OPERACIONAL" pulsante · badges mono uppercase com borda translúcida · ticker AO VIVO no topo da Central. Os HTMLs entregues (Portal Admin.dc.html e Memórias.dc.html) são a referência de layout e microinterações; a implementação usa os componentes nativos do /admin (regra: Radix vaza tema no /admin).

---

## 4. Plano de execução (2 etapas + 1 do dashboard)

### Etapa 1 — Fundação + páginas novas (backend + shell)
1. Endpoints admin de leitura/ação: agentes-status (última execução por task via Redis/heartbeats), sessões ativas (Redis dispatch), insights (broker_insights), scorecards, overlays/mapas (aprovar 1-clique), registro de seguradoras.
2. Shell novo do /admin (sidebar do design, nav de 10 itens, tokens).
3. As 3 páginas novas implementadas a partir dos HTMLs do design.
4. Redirects das rotas duplicadas + flag "empresa técnica" nas 2 empresas (some da lista comum, ganha seção própria).
5. `tsc --noEmit` + deploy + validação com o founder.

### Etapa 2 — Reskin e consolidação das páginas mantidas
6. Conversas (fusão 3→1), Financeiro (fusão 3→1, FinOps intacto na lógica), Conexões, Inteligência (Catálogo Global 3→1), Conhecimento, Pessoas.
7. **Cockpit da corretora** (companies/[id] com abas: Visão geral c/ nota do Auditor e acionamentos, Tokens & custos, Cobrança, Conexões, Conhecimento, Insights, Config).
8. Limpeza: código das rotas antigas arquivado (git preserva tudo).

### Etapa 3 — Dashboard do corretor
9. **Aba Memórias** implementada a partir do Memórias.dc.html (canvas próprio do design, cores por camada, cadeado por plano, painel lateral, "perguntar ao AutoBrokers").
10. SPEC-022 (hub Personalização→Seguradoras) na mesma leva.

Riscos e mitigação: nada é deletado sem redirect; FinOps/fluxos nativos preservados na lógica; cada etapa com deploy próprio e validação sua antes da seguinte.

---

## 5. Dúvidas para o founder (respostas mudam detalhes, não a estrutura)
1. "AutoBrokers Global Knowledge": reaproveitar como dona do RAG global (recomendado) ou arquivar?
2. RAFAEL SEGUROS (empresa de teste com 100 conversas): manter ativa ou marcar como teste/arquivada?
3. Na Central de Agentes, o glossário dos agentes pode usar exatamente as descrições do design (1 frase por agente)? (Ajusto a do Alfaiate — no design ficou "ajusta o tom das respostas", mas ele ajusta PLAYBOOKS.)
