# Fase C — Plano de Correção Estrutural (2 batches) para FUNCIONAR em produção

> Data: 2026-06-23. Reação direta aos problemas reais reportados pelo Founder + auditoria do novo chat.
> Princípio: **fazer funcionar de verdade, reusando o que existe (Smith/Vault/MCP/OAuth/permission_grants), SEM estrutura paralela.** Foco ESTRUTURAL (sem curadoria de RAG agora).

## Assumindo os erros (o que está quebrado e por quê)
1. **Busca web não funciona no chat.** Causa provável: `TAVILY_API_KEY` foi colocada no serviço **web (Next)**, mas a busca roda no **backend (Python/LangGraph)** — a chave não chega ao processo do chat. Além disso, o "ligada" do cockpit é só uma flag, não reflete um healthcheck real.
2. **InfoCap no chat falha com "precisa ser assíncrona".** Bug que eu introduzi: a tool `InfocapPolicyLookupTool._run` (síncrono) devolve essa mensagem; o executor do Smith chamou o caminho síncrono. Tem que rodar o async de verdade.
3. **Runtime ignora o Registry.** O `graph.py` anexa Control Plane + InfoCap só pelo papel (`core`/vazio), sem ler `capabilities/bindings/entitlements`/conexão. Cockpit mostra um estado, runtime faz outro. Agente sem papel não pode herdar poderes de Core.
4. **InfoCap duplicada na Resulta.** Duas conexões: `InfoCap — Resulta Seguros` (configuring, canônica) e `InfoCap RESULTA` (draft, duplicada). Falta regra de unicidade (singleton).
5. **UX de conectores burocrática e confusa.** Termos técnicos em inglês (read/draft_message/test_connection), não dá pra selecionar Core+Atendimento+Auxiliares de uma vez, aprovação humana obrigatória só pra **conectar** (sem sentido — quem conecta já é humano autorizando), login/senha não aparece, Notion não abre OAuth como no ChatGPT, status nunca fica claro ("conectado"). Nada ficou realmente conectado.
6. **Tabelas do Registry ainda não aplicadas** no Supabase (você aplica o `SPEC-014-01`).

## Modelo-alvo dos conectores (igual aos Apps do ChatGPT)
```
Dashboard da corretora → "Aplicativos/Conectores" → cards por categoria
   → [Conectar]
      • App OAuth (Drive/Calendar/Slack/Notion/GitHub): abre login oficial do fornecedor e volta
      • App por credencial (InfoCap): abre modal seguro com login/senha
   → "Quem pode usar?" (Chat Principal • Atendimento • Auxiliares) — múltipla escolha, UMA tela
   → [Conectar] → status claro: Conectado ✓ / Atenção / Credencial inválida / Desconectado
```
- **Sem aprovação humana para CONECTAR** (o próprio corretor está autorizando).
- **Aprovação só para AÇÃO externa sensível** (enviar WhatsApp, escrever no Notion, abrir assistência, operar portal) — no momento da execução, não da conexão.
- **Linguagem humana**: "Consultar informações" (read), "Preparar mensagem para revisão" (draft_message), "Testar conexão" (test_connection), etc. — para TODOS os conectores.
- Reusa por baixo: `tenant_connections`, `connector_templates`, `permission_grants`, `approval_requests`, Vault, MCP servers + OAuth, HTTP Tools. **Nada paralelo.**

---

## BATCH 1 — "FAZER FUNCIONAR" (runtime + governança + bugs)
Objetivo: o que já existe passa a funcionar de verdade no chat, governado pelo Registry.

1. **Runtime governado pelo Registry** (`graph.py`): resolver capabilities pelas tabelas (`capabilities`/`capability_bindings`/`tenant_capability_entitlements`) + presença de conexão, e só anexar cada tool quando **`active`** para aquele tenant/papel. Fallback seguro se as tabelas não existirem (degrada para internas).
2. **Bloquear papel vazio**: agente sem `agent_role` definido NÃO herda poderes de Core (corrige o "core/vazio").
3. **InfoCap async fix**: a tool funciona no chat real (executa o caminho assíncrono provado; `_run` roda o async corretamente). Testes: CPF, nome, múltiplos, não encontrado, credencial inválida, provider fora.
4. **Busca web — corrigir + provar**: (a) **`TAVILY_API_KEY` no serviço BACKEND** (não no web) + redeploy; (b) healthcheck real ("busca web operacional?") que alimenta o cockpit — o status deixa de ser flag e passa a refletir o runtime; (c) erro real aparece no log (parar de engolir).
5. **InfoCap singleton + dedup**: manter a canônica (`InfoCap — Resulta Seguros`), **arquivar** a duplicada (`InfoCap RESULTA`, sem segredo — seguro), e impor **1 conexão por conector singleton por corretora** (índice/validação). Nada é apagado destrutivamente.
6. **Diagnóstico que reflete a realidade** (cockpit Capacidades): cada capability mostra estado real (ativo/aguardando conexão/sem credencial), com healthcheck por provider.
- **Pré-requisito seu:** aplicar `SPEC-014-01` (cria as 3 tabelas + seed). 
- **Linha de chegada:** no chat da Resulta, busca web responde com fontes; InfoCap responde (após credencial) ou diz "configure em Conectores"; Control Plane responde números reais; cockpit = verdade; sem duplicidade.

## BATCH 2 — "CONECTORES ESTILO CHATGPT" (UX/produto, no Dashboard)
Objetivo: a corretora conecta apps fácil e funciona — reusando Vault/MCP/OAuth.

1. **Galeria de conectores no Dashboard** (cards por categoria: produtividade/pesquisa/comunicação/seguros) — uma tela, sem labirinto.
2. **Fluxo Conectar único**: OAuth oficial (Drive/Calendar/Slack/Notion/GitHub via os MCP servers + OAuth que já existem) **ou** modal de credencial (InfoCap login/senha) — o campo que hoje não aparece.
3. **"Quem pode usar" multi-ator numa tela** (Chat Principal + Atendimento + Auxiliares juntos), gravando como política única na conexão (sob o capó usa `permission_grants`, mas o corretor não vê isso).
4. **Linguagem 100% humana** em ações/permissões (todos os conectores).
5. **Remover aprovação-para-conectar**; aprovação só para ação externa sensível (execução).
6. **Status inequívoco + desconectar/editar** (healthcheck por conexão).
7. **Higiene**: arquivar conexões de teste (WhatsApp TESTE APAGAR, Notion TESTE) com confirmação.
- **Linha de chegada:** corretora conecta InfoCap (login/senha) e Drive/Notion (OAuth) em poucos cliques; escolhe quem usa; vê "Conectado ✓"; os agentes passam a usar.

---

## O que NÃO entra nestes 2 batches (depende de você/conteúdo — honesto)
- **RAG/Knowledge curado** (Seed Packs, ingestão) — só depois do estrutural, com sua aprovação.
- **Z-API paga + webhook + 42X5C** (depende de pagar/ativar) → corredor eletricista WhatsApp ponta a ponta.
- **Portal Allianz real** (credencial + rotacionar Browserbase) → Skills de Portal.
- **Release nova global do Core** (modelo explícito + capabilities declaradas + rollout ativo p/ Resulta) — entra no fim do Batch 1 ou início do 2.
- **Hardening SEC-001** (advisors do Supabase) antes de tráfego externo amplo.

## Superfícies (não misturar)
- **Portal Admin** = você (governança/diagnóstico/auditoria/catálogo).
- **Dashboard novo** = corretora (conectar e usar).
- **Portal Lab** = interno master (já colapsado).

## Suas ações para o Batch 1 rodar
1. Aplicar `SPEC-014-01` (APPLY) no SQL Editor.
2. Mover **`TAVILY_API_KEY` para o serviço BACKEND** (Python) no EasyPanel + redeploy (e revogar/gerar nova chave).
3. Confirmar no backend: `INFOCAP_BASE_URL`, `CORE_CHAT_MODEL`, chave interna Next↔Backend, `ENCRYPTION_KEY` estável.
4. **Não** cadastrar credencial InfoCap ainda (espere o dedup do Batch 1).
```
ESTADO ALVO PÓS 2 BATCHES: Core e Even usando capacidades reais (web, InfoCap, control plane, conhecimento)
governadas pelo Registry; conectores que a corretora liga sozinha estilo ChatGPT; sem duplicidade; sem
burocracia inútil. Depois: RAG curado + trilhas externas (Z-API/Allianz) = produção plena.
```
