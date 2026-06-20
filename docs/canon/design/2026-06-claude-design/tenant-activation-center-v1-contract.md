# Tenant Activation Center — v1 (Contrato / Visão)

> Documento canônico (read-only). Define a **futura experiência da corretora** no AutoBrokers. NÃO implementado neste batch. Referência de UX: dashboard antigo ResultVision (branch `clean/agent-runtime-foundation-orphan`) + telas de Dados/Contatos/Marca/Endereço/Suporte Humano/WhatsApp/Agentes/Equipe/Seguradoras. Runtime/banco canônico: AutoBrokers Intelligence OS.
> **Data:** 2026-06-20

## 1. Objetivo
Uma área **simples** onde a corretora faz onboarding e ativa o sistema **sem entrar em telas técnicas** (Portal Lab, Relay Sandbox, Skill Factory, Vault, Browserbase). Tudo o que é técnico/perigoso fica no Admin (master) e em Claude Code.

## 2. Jornada de onboarding (corretora)
```
Onboarding
→ Dados da corretora (nome, CNPJ, marca, endereço, contatos)
→ Equipe e aprovadores (usuários, papéis, quem aprova ações)
→ WhatsApp (conectar número próprio — Z-API por tenant)
→ Seguradoras (quais a corretora opera)
→ Portais (login assistido humano — gera SessionRef por corretora)
→ Corredores (ativar por toggle: ex. Allianz Residencial → Eletricista)
→ Conhecimento (curadoria opcional: condições, FAQs, procedimentos)
→ Teste de readiness (checklist: WhatsApp ok, portal ok, corredor ok)
→ Ativação (liga o atendimento real, com kill switch e HITL)
```

## 3. O que a corretora VÊ
```
Perfil da corretora · Equipe · Aprovadores · WhatsApp · Seguradoras
Portais conectados (status saudável/expirado/requer re-login) · Corredores ativos
Status de sessão (amigável) · Conhecimento · Suporte humano · Checklist de ativação
```

## 4. O que a corretora NÃO VÊ (técnico/segredo)
```
Vault · storage_ref · CredentialRef técnico · Relay Sandbox · Skill Factory
Browserbase key · connectUrl · debug URL · traces internos · flags globais
```

## 5. O que o Admin (master/plataforma) VÊ
```
Catálogo global de portais · Skills globais · Portal Maps · Canaries · Auditoria
Tenant health · Gates · Evals · Aprovações · Status de conectores
```

## 6. Modelo de criação (quem cria o quê)
| Item | Onde nasce | Quem cria |
|---|---|---|
| Corretora (company) | Admin/Companies | Founder/master_admin (futuro: auto após assinatura) |
| Usuários da corretora | Dashboard/invites | Corretora/master |
| Portal Account | Portal Lab (admin) | company_admin/master |
| Sessão do portal (SessionRef) | Browserbase Console + Portal Lab | humano autorizado |
| Corredor/Subcorredor (template global) | Claude Code | Claude Code + validação Founder |
| Slots/guardrails/Portal Map/Skill | Claude Code | Claude Code |
| Aprovação operacional | Dashboard/Approval | operador autorizado |
| WhatsApp da corretora | Conector Z-API por tenant | corretora + Founder |
| RAG/Knowledge | Knowledge OS curado | chat de RAG + Founder |

**Regra:** corretora NÃO cria automação de portal livremente (risco de quebrar portal/vazar dado/ação errada/misturar tenants). Corredores/Skills nascem como **template global confiável** via Claude Code. Um futuro "Corridor Studio" no-code seria prematuro agora.

## 7. Princípios de dados
- **company criada após assinatura** (futuro); company_admin inicial; onboarding progressivo.
- **Ativação de corredor por toggle**; portal conectado via login assistido; **SessionRef por corretora** (nunca global).
- Reautenticação simples + fallback humano.
- **Sem duplicação** de dados entre Dashboard, Admin e Supabase — o banco canônico é o AutoBrokers Intelligence OS; ResultVision é só referência de UX.

## 8. Como um atendimento acontece (resumo)
```
Segurado → WhatsApp da corretora → Attendance Agent → Caso → Corredor → Subcorredor
→ Skill (read-only ou ação com gate) → Portal/WhatsApp seguradora/Operador → Resultado estruturado
→ Caso atualizado + resposta honesta ao segurado + HITL quando necessário
```
O cliente vê **apenas** o WhatsApp da corretora. SubAgents/Portal Map/Vault/Browserbase/Skill/SessionRef são internos.

## 9. Não-objetivos do v1
- Não é um SaaS dashboard completo agora.
- Não habilita ação de negócio real sem gate dedicado.
- Não expõe nada técnico/segredo à corretora.

## 10. Próximos passos (após WhatsApp/Z-API)
Implementar incrementalmente as telas de onboarding reaproveitando os dados e rotas existentes (companies, users, connectors, corridors, portal accounts), sempre lendo do banco canônico e nunca duplicando segredo.
