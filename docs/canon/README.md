---
> **Status:** canonical  
> **Versão:** 2.0 — Briefing, Proatividade & Garimpo v3 autorizados  
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

3. [`specs/SPEC-054-foundation-hardening-schema-governance.md`](specs/SPEC-054-foundation-hardening-schema-governance.md)  
   Governa e autoriza o fechamento P0, Storage privado, baseline reproduzível, integridade multi-tenant, hardening de HTTP/MCP, Authority Strict e idempotência preparatória.

4. [`specs/SPEC-055-durable-work-runs-queue-checkpoints-hitl.md`](specs/SPEC-055-durable-work-runs-queue-checkpoints-hitl.md)  
   Governa e autoriza Work Runs universais, fila, worker Smith, leases, checkpoints, HITL, approvals e integração durável de Rotinas, Auxiliares e Portais.

5. [`specs/SPEC-056-skill-registry-tool-gateway.md`](specs/SPEC-056-skill-registry-tool-gateway.md)  
   Governa e autoriza o Skill Registry, Capability Packs, Tool Definitions/Releases, Tool Gateway único, seleção dinâmica e migração de native/HTTP/MCP/Portal/delegation.

6. [`specs/SPEC-057-artifact-hub-report-studio.md`](specs/SPEC-057-artifact-hub-report-studio.md)  
   Governa e autoriza Artifact Hub, Report Studio, templates versionados, renderer determinístico, relatórios web/PDF, XLSX, CSV, PPTX, DOCX, gráficos, Evidence Packs, compartilhamento e entrega.

7. [`specs/SPEC-058-auxiliary-routine-factory.md`](specs/SPEC-058-auxiliary-routine-factory.md)  
   Governa e autoriza a fábrica única de Auxiliares e Rotinas: classificação de trabalho, releases, instalações, revisões, criação por conversa/dashboard, triggers, readiness, custos, demanda e cutover do legado.

8. [`specs/SPEC-059-briefing-proatividade-garimpo-v3.md`](specs/SPEC-059-briefing-proatividade-garimpo-v3.md)  
   Governa e autoriza o Intelligence Fabric único: eventos, sinais, evidências, Findings, recomendações, Briefings, Garimpo v3, Demand Radar, feedback, outcomes e migração da proatividade histórica.

9. SPECs posteriores explicitamente subordinadas às SPECs 052–059.

10. ADRs, SPECs e relatórios históricos apenas quando não houver conflito.

Leia também o índice detalhado em [`specs/README.md`](specs/README.md).

## Separação oficial

- **AutoBrokers.ai** é o produto.
- **AutoBrokers** é o agente principal voltado ao corretor.
- **Smith** é o runtime técnico invisível.
- **Supabase** é a fonte durável de verdade operacional.
- **Redis** é transitório: fila, locks, leases e cache.
- **Qdrant** é índice semântico derivado.
- **MinIO** armazena documentos e artifacts.
- **Capability Registry** governa poderes.
- **Skill Registry** governa procedimentos versionados.
- **Tool Gateway** governa seleção e execução das ferramentas.
- **Artifact Hub** governa resultados, versões, renders, compartilhamento e entrega.
- **Auxiliary Factory** governa proposta, instalação, revisão, lifecycle e composição de Auxiliares/Rotinas.
- **Intelligence Fabric** governa eventos, sinais, evidências, Findings, recomendações, Briefings, demanda e outcomes.
- **Vault** governa segredos e conexões.
- **ResultVision / Agent OS histórico** são referências de domínio, não runtimes ativos.

## Leis centrais

```text
Um único cérebro lógico.
Um único runtime Smith.
Nenhum RAG, memória, publisher, scheduler ou executor paralelo.
Auxiliar é trabalhador de produto.
Rotina é gatilho.
Skill é procedimento versionado.
Capability é poder governável.
Tool é implementação.
Work Run é execução.
Artifact é resultado de primeira classe.
Signal é indício normalizado com evidência.
Finding é diagnóstico que separa fato de inferência.
Recommendation é proposta governada, não execução.
Outcome não medido é inconclusivo, não sucesso.
Nem toda tarefa recorrente vira um Agent.
Auxiliary Factory escolhe o menor padrão de trabalho adequado.
Proatividade exige evidência, relevância, dedupe, cooldown e respeito ao usuário.
Toda ação recomendada é executada pelo Work OS quando autorizada.
Garimpo captura e estrutura demanda, mas não publica conhecimento diretamente.
Vault governa segredos.
Capability Registry governa acesso.
Tool Gateway governa todas as famílias de tools.
Artifact Hub governa todos os novos entregáveis.
Intelligence Fabric governa sinais, Findings, recomendações, Briefings e outcomes.
MinIO privado armazena bytes; Supabase guarda metadata e autoridade.
Schema e migrations são governados pela SPEC-054.
```

## Documentos canônicos principais

| Documento | Propósito |
| --- | --- |
| `PRD-001-visao-produto.md` | Visão de produto, público, módulos, MVP e naming. |
| `ADR-001-runtime.md` | Runtime oficial e fronteiras entre produto, Smith e domínio. |
| `ADR-002-vault.md` | Vault, credenciais, PII e limites de dados sensíveis. |
| `ADR-003-atendimento.md` | Atendimento e migração curada de domínio. |
| `UX-001-navegacao.md` | Arquitetura de navegação do tenant e Admin. |
| `UX-007-auxiliares.md` | Direção histórica de UX de Auxiliares, subordinada à SPEC-058. |
| `SPEC-002-auxiliares-runtime-smith.md` | Fundação histórica: Auxiliares = produto; Smith = runtime; Vault = governança. Parcialmente superada pela SPEC-058. |
| `SPEC-005-atendimento-runtime-architecture.md` | Arquitetura de Atendimento, casos, corredores, Evidence Pack e HITL. |
| `SPEC-006-allianz-residencial-corredor-eletricista-mvp.md` | Corredor Allianz Residencial/Eletricista e expansão da família. |
| `SPEC-014-capability-registry-knowledge-os.md` | Fundação histórica do Capability Registry; subordinada à SPEC-056 para Skills e Tool Gateway. |
| `specs/SPEC-019-rotinas-auxiliares-claude-parity.md` | Fundação histórica do motor de Rotinas. Parcialmente superada pelas SPECs 053 e 058. |
| `specs/SPEC-051-evolution-go-pareamento-passkey-observador.md` | Evolution Go, QR/passkey, Observador silencioso e aprendizado incremental. |
| `specs/SPEC-052-cerebro-cognitivo-unificado-autobrokers.md` | Cérebro cognitivo unificado e soberano. |
| `specs/SPEC-053-autobrokers-work-os-core-harness.md` | Work OS e Harness avançado soberano. |
| `specs/SPEC-054-foundation-hardening-schema-governance.md` | Hardening de fundação autorizado para execução. |
| `audits/AUDIT-SPEC-054-foundation-hardening-schema-governance-2026-07-24.md` | Auditoria read-only obrigatória antes da SPEC-054. |
| `specs/SPEC-055-durable-work-runs-queue-checkpoints-hitl.md` | Execução durável de lançamento. |
| `specs/SPEC-056-skill-registry-tool-gateway.md` | Skills versionadas e Tool Gateway único de lançamento. |
| `specs/SPEC-057-artifact-hub-report-studio.md` | Artifacts e Report Studio de lançamento, com Visual Acceptance Pack obrigatório. |
| `specs/SPEC-058-auxiliary-routine-factory.md` | Factory de Auxiliares e Rotinas de lançamento, com criação por conversa/dashboard, catálogo, releases, revisões, triggers e demanda. |
| `specs/SPEC-059-briefing-proatividade-garimpo-v3.md` | Intelligence Fabric de lançamento: Briefings, proatividade, Garimpo v3, recomendações, Demand Radar, feedback e outcomes. |
| `runbooks/RUNBOOK-PAREAMENTO-WHATSAPP-CORRETORA.md` | Pareamento de corretoras com baixo atrito. |
| `runbooks/RUNBOOK-PASSKEY-WHATSAPP.md` | Fluxo de passkey. |
| `runbooks/RUNBOOK-EVOLUTION-GO-POOL-POSTGRES.md` | Diagnóstico do pool Postgres Evolution Go. |

## Documentos parcialmente superados

As SPECs 003, 004, 008, 010, 034, 040 e 044 continuam como histórico e detalhamento, mas a SPEC-052 prevalece em arquitetura cognitiva.

As SPECs 002 e 019 e o UX-007 continuam como fundação histórica de Auxiliares e Rotinas, mas a SPEC-058 prevalece em Factory, releases, instalações, revisões, runtime padrão, criação por conversa/dashboard, lifecycle e cutover.

A SPEC-014 continua como fundação histórica do Capability Registry, mas a SPEC-056 prevalece em Skill Releases, Capability Packs, Tool Definitions/Releases, seleção dinâmica, Tool Gateway e cutover de autoridades legadas.

Relatórios textuais, exports isolados, PDFs avulsos e templates espalhados continuam como evidência histórica, mas a SPEC-057 prevalece em Artifact Hub, versões, renderers, templates, Report Studio, compartilhamento e entrega.

As decisões históricas das SPECs 034, 035, 036, 037, 040 e 049 sobre Garimpo, sugestões semanais, relatório de sábado, regressão e Admin Insights permanecem como fundação. A SPEC-059 prevalece em eventos, sinais, evidências, Findings, recomendações, Briefings, Demand Radar, feedback, outcomes, scheduling e cutover. `broker_insights.py`, `proactive_suggestions.py`, `weekly_report.py`, `regression_sentinel.py` e o Admin Insights histórico deixam de ser autoridades soberanas depois da migração.

## Regra operacional

Quando documentos canônicos divergirem:

```text
SPEC-052
→ SPEC-053
→ SPEC-054 para schema e segurança de fundação
→ SPEC-055 para execução durável
→ SPEC-056 para Skills, capabilities e tools
→ SPEC-057 para artifacts, renderers, relatórios e entregas
→ SPEC-058 para Auxiliares, Rotinas, Factory, catálogo e criação
→ SPEC-059 para sinais, Findings, recomendações, Briefings, Garimpo e outcomes
→ SPEC subordinada mais nova e explícita
→ ADR aplicável
→ documento histórico
```

Em ambiguidade relevante, o agente deve parar e solicitar validação do CEO/Founder.