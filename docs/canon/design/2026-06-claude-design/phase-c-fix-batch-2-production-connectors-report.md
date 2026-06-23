# C-FIX-2 — Relatório: Recuperação InfoCap + Conectores de Produção

> Data: 2026-06-23. Encerra a infraestrutura de conectores. Reusa Smith/Vault/MCP/Registry — nada paralelo.

## Causa-raiz (por que InfoCap não conectava)
1. O modal enviava só login/senha, **sem `connection_id`**; a rota escolhia "a conexão InfoCap mais recente" → o segredo caiu numa conexão nova ("InfoCap 1") **sem base_url**, enquanto a canônica tinha base_url **sem segredo**. Resultado: nenhuma "conectava".
2. O backend marcava `connected` só com base_url na própria conexão (sem fallback global) e **sem testar auth de verdade** → status mentiroso.
3. Não havia como **excluir/arquivar/desconectar** conexões nem **menu de ações** → lista poluída.

## O que foi feito
**Recuperação de dados (Resulta, via MCP — seguro/reversível):**
- Segredo movido da "InfoCap 1" (errada) para a canônica "InfoCap — Resulta Seguros" (mesma chave Fernet/mesma corretora → decifra igual); base_url global garantido; "InfoCap 1" arquivada e segredo limpo. → **1 InfoCap canônica** com segredo + base_url + 7 permissões.

**Backend (conexão real + verdade):**
- `infocap_connector.py`: gravação de segredo usa **`INFOCAP_BASE_URL` global** como fallback e faz **teste de auth REAL** (login) → status `connected` / `error`(credencial inválida) / `configuring`(indisponível). Novo endpoint **`POST /attendance/connectors/infocap/test`** testa com o segredo já salvo (sem re-digitar).
- O resolver (C-FIX-1) só libera InfoCap ao Core quando a conexão está `connected`.

**Next/UI:**
- `infocap/secret/route.ts`: usa o **`connection_id` explícito** (nunca "a mais recente"); fallback = única InfoCap não-arquivada.
- `infocap/test/route.ts` (novo): proxy do teste real.
- `ConfigureInfocapModal`: envia `connection_id`; mensagem honesta (Conectado ✓ / credencial inválida).
- `vault/connections/[id]` **DELETE** com modos: **arquivar** (preserva histórico), **excluir rascunho vazio** (só sem segredo/permissões/aprovações), **desconectar** (remove segredo, status disconnected).
- **Menu ⋯ por conexão** (Gerenciar acesso, Testar conexão, Desconectar, Arquivar/Excluir) — fim dos botões soltos.
- **Status real** no Catálogo e em Minhas conexões (mesma verdade); **arquivadas somem** da lista ativa.
- **Permissões agregadas por ator** (Chat Principal/Atendimento/Auxiliares) — acaba a poluição de 7 linhas; "Remover acesso" revoga tudo do ator.

**Runbook:** `SPEC-014-03B-infocap-recovery-and-singleton.sql` (recuperação documentada + índice singleton com pré-check). Substitui o uso prático do `SPEC-014-03`.

## Estado antes → depois
| Item | Antes | Depois |
|---|---|---|
| InfoCap Resulta | 2 não-arquivadas, segredo na errada | 1 canônica (segredo+base_url+permissões) |
| Status "Conectado" | nunca aparecia | real, após teste de auth (Catálogo + Minhas conexões) |
| Conectar InfoCap | segredo na conexão errada | modal envia connection_id correto |
| Excluir/arquivar conexão | impossível | menu ⋯ (arquivar/excluir rascunho/desconectar) |
| Permissões | 7 linhas técnicas | agregadas por ator |
| Core usa InfoCap | não | sim, quando `connected` (após Testar) |

## Suas tarefas (após deploy)
1. **Deploy** backend + frontend.
2. Dashboard → Conectores → **InfoCap "Reconectar"** OU menu ⋯ → **"Testar conexão"** (usa o login/senha já salvo). Deve virar **Conectado ✓**.
3. No InfoCap → ⋯ → **Gerenciar acesso**: confirme Chat Principal + Atendimento + Auxiliares.
4. Limpar testes: menu ⋯ → **Arquivar/Excluir** nas conexões de teste (inclui as duplicadas da **Rafael**).
5. Depois que **nenhuma** corretora tiver duplicadas, aplicar **`SPEC-014-03B`** (índice singleton). *(Hoje a Rafael ainda tem duplicadas de teste — o pré-check do runbook mostra quais.)*

## Roteiro de aceite
1. InfoCap → ⋯ → Testar conexão → **Conectado ✓** (ou "credencial inválida" se a senha estiver errada — honesto).
2. Chat: "consulte a apólice do CPF 030.743.279-36, quantas apólices ativas?" → resultado sanitizado (não mais "não tenho acesso").
3. Catálogo: card InfoCap mostra **Conectado**.
4. ⋯ → Arquivar numa conexão de teste → some da lista.
5. Gerenciar acesso → uma linha por ator (sem poluição); "Remover acesso" funciona.

## Limitações reais (honesto)
- **OAuth Notion/Drive/Slack/Calendar**: a galeria + os MCP servers existem; o fluxo OAuth ponta-a-ponta no Dashboard **não foi finalizado neste batch** (precisa dos client IDs/secret + callback URL configurados pela plataforma). Sem isso, "Preparar conexão" deve evoluir para abrir OAuth — fica como próximo passo focado, com checklist de envs/callback. *(Prioridade foi InfoCap + gestão de conexões, que eram o bloqueio real.)*
- O índice singleton só aplica após limpar as duplicadas de teste da Rafael (via ⋯).
- Busca web já funcionava; melhoria de apresentação de fontes não foi alterada neste batch.

## Verificação
resolver 11/11; capabilities 21/21; agent-health 10/10; model 10/10; py_compile OK; tsc=0; build verde.
