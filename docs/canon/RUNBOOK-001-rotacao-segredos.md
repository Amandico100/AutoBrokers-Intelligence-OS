# RUNBOOK-001 — Rotação de Segredos (Onda 3 / SPEC-018 S8)

**Status**: pronto para execução pelo founder · **Autor**: Fable (líder técnico) · **Data**: 2026-07-03

## Por que agora

Credenciais de produção foram coladas em chats de trabalho (Claude/GPT) durante o
debug da Onda 2. Chat não é cofre: considere TODAS as chaves abaixo como expostas
e rote TODAS. Este runbook lista o quê, onde e em que ordem — **nunca** os valores.

**Regra de ouro**: gere a chave nova, atualize o(s) env(s), reinicie o serviço,
CONFIRME funcionando, e só então revogue a antiga (quando o painel permitir manter
as duas vivas por alguns minutos). Assim não há janela de queda.

## Inventário de chaves expostas (rotacionar TODAS)

| # | Segredo | Onde gerar a nova | Onde atualizar (EasyPanel) |
|---|---------|-------------------|----------------------------|
| 1 | OpenAI API key | platform.openai.com → API keys | smith-api: `OPENAI_API_KEY` |
| 2 | Anthropic API key | console.anthropic.com → API keys | smith-api: `ANTHROPIC_API_KEY` |
| 3 | Tavily API key (se existir no env) | app.tavily.com | smith-api: `TAVILY_API_KEY` |
| 4 | Twilio Auth Token | console.twilio.com (botão de rotação nativo, mantém 2 vivos) | smith-api: env Twilio |
| 5 | `ADMIN_API_KEY` / `BACKEND_INTERNAL_API_KEY` | você mesmo gera (64+ caracteres aleatórios; ex.: gerador de senha) | smith-api E smith-web (a MESMA nova nos dois) |
| 6 | Evolution `AUTHENTICATION_API_KEY` | você mesmo gera (padrão ABK_..., 40+ chars) | evolution-api E smith-api `EVOLUTION_API_KEY` (a MESMA nos dois; cuidado com linha duplicada — já nos mordeu uma vez) |
| 7 | Gatilhos de deploy EasyPanel (api e web) | EasyPanel → serviço → Deploy → regenerar URL do gatilho | ninguém (só me passar as URLs novas por print/chat NOVO) |
| 8 | Supabase `service_role` + `anon` | Supabase → Settings → API (ver ordem especial abaixo) | smith-api: `SUPABASE_SERVICE_ROLE_KEY`(+URL); smith-web: `SUPABASE_SERVICE_ROLE_KEY` e `NEXT_PUBLIC_SUPABASE_ANON_KEY` |

Z-API/UAZAPI legadas: se ainda houver tokens nos envs, apagar as linhas (não usamos mais).

## Ordem de execução (do mais simples ao mais delicado)

**Fase A — provedores externos (5 min cada, sem risco de queda)**
1. OpenAI → nova key → atualizar env smith-api → Restart → testar uma pergunta no chat → revogar key antiga.
2. Anthropic → idem.
3. Tavily (se existir) → idem (testar uma pergunta que use busca na web).
4. Twilio → rotação nativa do console → atualizar env → Restart.

**Fase B — chaves internas nossas (10 min)**
5. Gerar `ADMIN_API_KEY` nova → colocar a MESMA em smith-api e smith-web → Restart nos dois → abrir o dashboard e a página Prompt Efetivo (as duas usam a chave interna por trás).
6. Gerar Evolution key nova → colocar em evolution-api (`AUTHENTICATION_API_KEY`) e smith-api (`EVOLUTION_API_KEY`) → Restart nos dois → abrir o modal do WhatsApp e ver o diagnóstico verde.
   ⚠️ Conferir que cada env tem UMA linha só de cada chave (as duplicadas foram a causa do bug da RODADA-4).
7. Regenerar os 2 gatilhos de deploy no EasyPanel → me mandar as URLs novas (em chat novo, não no histórico antigo).

**Fase C — Supabase (a mais delicada; fazer por último, fora de horário de teste)**
8. Supabase → Settings → API → rotacionar o JWT secret (isso troca `anon` E `service_role` JUNTAS).
9. IMEDIATAMENTE atualizar: smith-api `SUPABASE_SERVICE_ROLE_KEY`; smith-web `SUPABASE_SERVICE_ROLE_KEY` + `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
10. Restart api e web. O web precisa de REBUILD (a anon key é embutida no build do Next) → disparar deploy do web após salvar o env.
11. Testar: login no dashboard, uma conversa com o AutoBrokers, página Empresas do admin.
12. Usuários logados vão precisar logar de novo (sessões antigas morrem com o JWT secret). Normal.

## Depois de rodar

- Me avise "rotação feita" + qualquer erro/print. Eu valido os fluxos ponta a ponta.
- Apagar dos chats/arquivos locais qualquer cópia das chaves antigas (elas ficam inúteis, mas higiene é higiene).
- Daqui pra frente: chave nova NUNCA em chat. Se eu precisar de uma chave para debug, você cola direto no env do EasyPanel e eu uso pelos endpoints internos.

## O que NÃO precisa rotacionar

- Tokens de webhook por integração (`webhook_token_hash`): já são hash no banco, gerados por nós, não expostos em chat.
- Senhas de usuários / URL do banco interna do EasyPanel: não circularam em chat.
