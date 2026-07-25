---
> **Status:** canônico — template obrigatório
> **Criado em:** 25/07/2026
> **Uso:** copiar para `docs/canon/reports/SPEC-0NN-EXECUTION-REPORT.md` ao iniciar a SPEC e preencher ao longo da execução
---

# Template de relatório final de execução de SPEC

## Instruções de uso

1. Copiar este arquivo no **início** da SPEC, não no fim. O relatório é preenchido durante a execução.
2. Nenhuma seção pode ser removida. Seção sem conteúdo recebe `N/A` **com justificativa**.
3. Separar sempre **FATO**, **INFERÊNCIA** e **RECOMENDAÇÃO**.
4. Nunca afirmar que algo funciona só porque existe código. Prova é saída de teste ou consulta ao banco.
5. Nenhum segredo, hash, token ou credencial — apenas presença/ausência.
6. O relatório é pré-condição do gate final. SPEC sem relatório completo **não** faz merge na `main`.

---

<!-- ============ COPIAR A PARTIR DAQUI ============ -->

# Relatório de execução — SPEC-0NN: <título>

**Produto:** AutoBrokers Intelligence OS
**SPEC:** `docs/canon/specs/SPEC-0NN-<slug>.md`
**Branch:** `feat/spec0NN-<slug>`
**Worktree:** `AutoBrokers-Opus-Exec`
**Executor:** <modelo/sessão>
**Início:** DD/MM/AAAA · **Conclusão:** DD/MM/AAAA
**Commit inicial:** `<sha>`
**Commit final:** `<sha>`
**Estado final:** CONCLUÍDA | CONCLUÍDA COM RESSALVAS | PARCIAL | BLOQUEADA

---

## 0. Declaração de integridade

- [ ] Nenhum motor paralelo foi criado (runtime, RAG, memória, publisher, scheduler, executor, registry, gateway, hub, factory, fabric, control plane, eval platform, billing engine, ledger).
- [ ] Nenhuma migration existente foi movida, renomeada, apagada ou reaplicada fora do manifesto.
- [ ] Nenhum DDL monolítico foi aplicado.
- [ ] Nenhum segredo foi exposto em log, artifact, blueprint ou neste relatório.
- [ ] Nenhum escopo foi reduzido sem decisão registrada em `FOUNDER-DECISIONS.md`.
- [ ] Nenhum dado atravessou tenants nas verificações executadas.
- [ ] `CLAUDE.md`, `EXECUTION-MASTER-PLAN.md` e `FOUNDER-DECISIONS.md` foram lidos no início.

Qualquer item não marcado exige explicação nominal na §10.

---

## 1. Resumo executivo

Máximo 20 linhas. O que foi entregue, o que mudou para o corretor, o que ficou de fora e por quê.

---

## 2. Escopo executado por bloco

### Bloco A — <título>
| Entrega prevista na SPEC | Estado | Evidência |
|---|---|---|
| | CONCLUÍDA / PARCIAL / NÃO FEITA | arquivo:linha, teste, consulta |

### Bloco B — <título>
| Entrega prevista na SPEC | Estado | Evidência |
|---|---|---|

### Bloco C — <título>
| Entrega prevista na SPEC | Estado | Evidência |
|---|---|---|

**Entregas da SPEC que NÃO foram executadas:** listar cada uma com o motivo. Ausência de motivo é falha de relatório.

---

## 3. Arquivos alterados

```text
<git diff --stat entre commit inicial e final>
```

| Área | Criados | Alterados | Removidos |
|---|---:|---:|---:|
| Backend | | | |
| Frontend | | | |
| Migrations | | | |
| Testes | | | |
| Documentação | | | |

---

## 4. Migrations

Uma seção por migration. Sem exceção.

### `<versão>_<slug>.sql`

| Campo | Conteúdo |
|---|---|
| **Objetivo** | |
| **Expand-first** | sim / não |
| **Destrutiva** | não / sim + decisão D-nn |
| **APPLY** | o que faz |
| **VERIFY** | SQL executável + saída real obtida |
| **ROLLBACK** | SQL de reversão, ou justificativa se irreversível |
| **Aplicada em produção** | sim / não · data · versão registrada |
| **MANIFEST atualizado** | sim / não |

**Advisors antes:** `<contagem por nível>`
**Advisors depois:** `<contagem por nível>`
**Diferença:** explicar cada achado novo ou resolvido.

---

## 5. Testes executados

> Colar **saída real**. Resumo de memória não é evidência.

### 5.1 Obrigatórios

| Teste | Comando | Resultado | Saída |
|---|---|---|---|
| Isolamento multi-tenant (2 tenants reais) | | | |
| P0 de segurança / RPC / Storage | | | |
| Idempotência de side effect | | | |
| Migration em ambiente vazio | | | |
| Migration incremental sobre estado atual | | | |
| Approval / IDOR | | | |
| SSRF e egress | | | |
| MCP env allowlist | | | |

### 5.2 Proporcionais ao risco desta SPEC

| Teste | Comando | Resultado |
|---|---|---|

### 5.3 Broker Outcome Regression Pack

| Cenário | Resultado | Observação |
|---|---|---|
| Identidade e multiempresa | | |
| Chat e agentes | | |
| Dados e documentos | | |
| WhatsApp | | |
| Rotinas e Auxiliares | | |
| Portais | | |
| Admin | | |

**Regressões encontradas:** listar e explicar o tratamento de cada uma.

---

## 6. Canário e rollout

| Ambiente | Estado | Evidência | Data |
|---|---|---|---|
| Amandus (técnico) | | | |
| Resulta | | | |
| AutoFleet | | | |

**Flags criadas ou alteradas:** nome, default, quem liga, como desligar.
**Auto-pause configurado:** sim / não · condição.

---

## 7. Gate da SPEC

| Critério de aceite (da SPEC) | Atendido | Evidência |
|---|---|---|
| | SIM / NÃO / PARCIAL | |

**Veredito do gate:** VERDE | VERDE COM RESSALVA | VERMELHO
Ressalva, se houver: descrever e indicar em que SPEC posterior será fechada.

---

## 8. Mudanças além do texto da SPEC

| ID em `CHANGE-ADDENDA.md` | Classe | Estado | Resumo |
|---|---|---|---|

Se nenhuma: declarar explicitamente **"Nenhuma mudança além do texto literal da SPEC."**

---

## 9. Decisões registradas

| ID em `FOUNDER-DECISIONS.md` | Assunto | Estado |
|---|---|---|

---

## 10. Riscos remanescentes e dívida assumida

| Risco | Severidade | Por que foi aceito | Onde será fechado |
|---|---|---|---|

---

## 11. Impacto para o corretor

O que o usuário final consegue fazer hoje que não conseguia antes desta SPEC. Escrever em linguagem de produto, sem termo técnico.

Se a resposta for "nada visível ainda", dizer isso com clareza e explicar qual SPEC transforma esta fundação em valor percebido.

---

## 12. Estado do Master Plan

- [ ] `EXECUTION-MASTER-PLAN.md` atualizado: estado, commits, relatório.
- [ ] `FOUNDER-DECISIONS.md` atualizado, se houve decisão.
- [ ] `CHANGE-ADDENDA.md` atualizado, se houve mudança adicional.
- [ ] `MIGRATIONS-AUTHORITY.md` / `MANIFEST.md` atualizados, se houve migration.

**Próxima etapa do plano:** `<número e nome>`
**Pré-condições da próxima etapa:** listar o que precisa estar verde ou decidido.

---

## 13. ROLLBACK da SPEC inteira

Como reverter tudo o que esta SPEC entregou, se necessário:

```text
1. aplicação:
2. flags:
3. banco:
4. side effects já executados:
5. o que NÃO é reversível e por quê:
```
