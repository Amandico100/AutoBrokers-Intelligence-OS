---
> **Status:** canonical  
> **Versão:** 1.4 — Cérebro Unificado + Work OS  
> **Última atualização:** 2026-07-24  
> **Produto:** AutoBrokers.ai  
> **Sistema:** AutoBrokers Intelligence OS  
> **Função:** índice principal da documentação canônica ativa
---

# AutoBrokers Intelligence OS Canon

Esta pasta é a fonte de verdade documental ativa do AutoBrokers.ai.

## Autoridade soberana atual

1. [`specs/SPEC-052-cerebro-cognitivo-unificado-autobrokers.md`](specs/SPEC-052-cerebro-cognitivo-unificado-autobrokers.md)  
   Governa conhecimento, RAG, memória, Context Assembly, aprendizagem, capabilities e o cérebro cognitivo unificado.

2. [`specs/SPEC-053-autobrokers-work-os-core-harness.md`](specs/SPEC-053-autobrokers-work-os-core-harness.md)  
   Governa o Work OS: Core Harness, Skills, Tool Gateway, execução durável, Auxiliares, Rotinas, approvals, artifacts e Portal Admin Control Plane.

3. SPECs posteriores explicitamente subordinadas às SPECs 052 e 053.

4. ADRs, SPECs e relatórios históricos apenas quando não houver conflito.

Leia também o índice detalhado em [`specs/README.md`](specs/README.md).

## Separação oficial

- **AutoBrokers.ai** é o produto.
- **AutoBrokers** é o agente principal voltado ao corretor.
- **Smith** é o runtime técnico invisível.
- **Supabase** é a fonte durável de verdade operacional.
- **Redis** é transitório: fila, locks, leases e cache.
- **Qdrant** é índice semântico derivado.
- **MinIO** armazena documentos e artifacts.
- **ResultVision / Agent OS histórico** são referências de domínio, não runtimes ativos.

## Leis centrais

```text
Um único cérebro lógico.
Um único runtime Smith.
Nenhum RAG, memória, publisher, scheduler ou executor paralelo.
Auxiliar é trabalhador de produto.
Rotina é gatilho.
Skill é procedimento.
Work Run é execução.
Artifact é resultado de primeira classe.
Vault governa segredos.
Capability Registry governa acesso.
```

## Documentos canônicos principais

| Documento | Propósito |
| --- | --- |
| `PRD-001-visao-produto.md` | Visão de produto, público, módulos, MVP e naming. |
| `ADR-001-runtime.md` | Runtime oficial e fronteiras entre produto, Smith e domínio. |
| `ADR-002-vault.md` | Vault, credenciais, PII e limites de dados sensíveis. |
| `ADR-003-atendimento.md` | Atendimento e migração curada de domínio. |
| `UX-001-navegacao.md` | Arquitetura de navegação do tenant e Admin. |
| `UX-007-auxiliares.md` | Direção histórica de UX de Auxiliares, subordinada à SPEC-053. |
| `SPEC-002-auxiliares-runtime-smith.md` | Fundação histórica: Auxiliares = produto; Smith = runtime; Vault = governança. Parcialmente superada pela SPEC-053. |
| `SPEC-005-atendimento-runtime-architecture.md` | Arquitetura de Atendimento, casos, corredores, Evidence Pack e HITL. |
| `SPEC-006-allianz-residencial-corredor-eletricista-mvp.md` | Corredor Allianz Residencial/Eletricista e expansão da família. |
| `SPEC-014-capability-registry-knowledge-os.md` | Capability Registry e governança de acesso. |
| `specs/SPEC-019-rotinas-auxiliares-claude-parity.md` | Fundação histórica do motor de Rotinas. Parcialmente superada pela SPEC-053. |
| `specs/SPEC-051-evolution-go-pareamento-passkey-observador.md` | Evolution Go, QR/passkey, Observador silencioso e aprendizado incremental. |
| `specs/SPEC-052-cerebro-cognitivo-unificado-autobrokers.md` | Cérebro cognitivo unificado e soberano. |
| `specs/SPEC-053-autobrokers-work-os-core-harness.md` | Work OS e Harness avançado soberano. |
| `runbooks/RUNBOOK-PAREAMENTO-WHATSAPP-CORRETORA.md` | Pareamento de corretoras com baixo atrito. |
| `runbooks/RUNBOOK-PASSKEY-WHATSAPP.md` | Fluxo de passkey. |
| `runbooks/RUNBOOK-EVOLUTION-GO-POOL-POSTGRES.md` | Diagnóstico do pool Postgres Evolution Go. |

## Documentos parcialmente superados

As SPECs 003, 004, 008, 010, 034, 040 e 044 continuam como histórico e detalhamento, mas a SPEC-052 prevalece em arquitetura cognitiva.

As SPECs 002 e 019 continuam como fundação histórica de Auxiliares e Rotinas, mas a SPEC-053 prevalece em ontologia, Work Runs, Skills, Tool Gateway, approvals, artifacts e Control Plane.

## Regra operacional

Quando documentos canônicos divergirem:

```text
SPEC-052 / SPEC-053
→ SPEC subordinada mais nova e explícita
→ ADR aplicável
→ documento histórico
```

Em ambiguidade relevante, o agente deve parar e solicitar validação do CEO/Founder.
