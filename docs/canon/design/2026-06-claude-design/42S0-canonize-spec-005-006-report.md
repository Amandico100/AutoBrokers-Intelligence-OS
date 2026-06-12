# 42S0 — Canonize SPEC-005 & SPEC-006 Report

> **Status:** concluído · documentação apenas · **SPECs NÃO reescritas** · nenhum código/SQL/schema/RAG/prompt/agente alterado · sem deploy.
> **Data:** 2026-06-12 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 1. Arquivos verificados
- `docs/canon/SPEC-005-atendimento-runtime-architecture.md` — **existe** (1284 linhas). Título e status presentes ("SPEC canônica proposta · pronta para revisão do Founder/CEO"). Princípio mestre: Atendimento = estado + workflow estruturado + conversa + tools + HITL (não WhatsApp/RAG/prompt solto).
- `docs/canon/SPEC-006-allianz-residencial-corredor-eletricista-mvp.md` — **existe** (1418 linhas). Título e status presentes. Dependência declarada: SPEC-005. Família Allianz Residencial com Eletricista como MVP.

> Origem: ambos foram adicionados ao repositório pelo Founder/Architect (commits `21badb5` e `1cffae4`, "Add files via upload"). O local foi alinhado ao `origin/main` (autoritativo) antes desta edição.

## 2. Revisão mínima de consistência (superficial)
| Check | SPEC-005 | SPEC-006 |
|---|---|---|
| Título presente | ✅ | ✅ |
| Status presente | ✅ | ✅ |
| Sem placeholder óbvio (TODO/TBD/FIXME/lorem) | ✅ (só falsos positivos com a palavra "todo/todos" = "all") | ✅ (idem) |
| Sem segredo/token/credencial literal | ✅ nenhum | ✅ nenhum |
| Sem PII explícita (CPF/telefone) | ✅ nenhum padrão | ✅ nenhum padrão |
| Sem conteúdo bruto de intake/conversas reais | ✅ (procedural/arquitetural) | ✅ (procedural/arquitetural) |

**Nenhuma reescrita, simplificação ou alteração de conteúdo/decisão estratégica foi feita.** Apenas leitura.

## 3. README atualizado
`docs/canon/README.md`:
- Adicionadas 2 "Lei nova": SPEC-005 (Atendimento = estado + workflow estruturado, não WhatsApp/RAG/prompt solto) e SPEC-006 (Allianz Residencial como família de corredor; Eletricista = 1º slice MVP dry-run/HITL).
- Adicionadas 2 linhas no índice canônico ("Canonical Documents") com as descrições sugeridas.
- Nenhum documento antigo foi alterado.

## 4. Confirmações
- **SPEC-005 e SPEC-006 não foram reescritas** (apenas verificadas/lidas).
- **Não** mexi em código/`app/`/`backend/`/`lib/`/SQL/migration/schema/RAG/prompt/agentes; **sem deploy**.
- **Nenhum segredo/PII óbvio** encontrado nas SPECs (scan literais de secret/token/credential, CPF e telefone → nada).
- Nenhum conteúdo bruto do Agent OS/intake foi copiado.

## 5. Arquivos alterados neste batch
- `docs/canon/README.md` (índice + leis novas).
- `docs/canon/design/2026-06-claude-design/42S0-canonize-spec-005-006-report.md` (este).
- (As duas SPECs já estavam commitadas em `origin/main`; não foram modificadas.)

## 6. Próximos batches recomendados
1. **42A4** — Attendance Boundary Blueprint v1 (seed do papel `attendance`, separado do Core).
2. **42B1** — Atendimento Runtime Architecture (implementação por fases conforme SPEC-005).
3. **42B2** — Allianz Residencial **Eletricista** Corredor (conforme SPEC-006), curado, sem PII.
4. **42B3** — SQL mínimo (attendance_cases/corridor_templates/corridor_runs/dispatch_packets), controlado pelo Architect.
5. Rodar **CORE-REGRESSION-001** a cada batch que tocar runtime.
