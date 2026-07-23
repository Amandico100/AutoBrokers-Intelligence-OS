> [!WARNING]
> **STATUS: PARCIALMENTE SUPERADA PELA SPEC-052.**  
> Esta SPEC permanece válida como histórico e fundação das três camadas, mas a arquitetura soberana de cérebro único, Knowledge Global, memória, Context Assembly, aprendizagem e ferramentas está em `SPEC-052-cerebro-cognitivo-unificado-autobrokers.md`. Em qualquer conflito, a SPEC-052 prevalece.

# SPEC-044 — Três Camadas: Global · Corretora · Usuário (fundação backend)

> Aprovada pelo founder em 20/07/2026. Modelo copiado do que funciona nas
> grandes plataformas (ChatGPT Enterprise/Slack): recursos do WORKSPACE
> (admin implanta para todos) vs recursos PESSOAIS (cada um conecta o seu).
> Executada pelo chat líder (Fable). Auditoria prévia: hoje NADA distingue
> usuário de corretora (só company_id em tudo; created_by é só auditoria).

## O modelo (regra de decisão)

"Se a pessoa sair da corretora amanhã, isso deve continuar existindo para o
 time?" SIM → 🏢 corretora. NÃO → 👤 usuário. Conteúdo da plataforma → 🌐 global.

| Recurso | 🌐 Global | 🏢 Corretora | 👤 Usuário |
|---|---|---|---|
| Inteligência (mapas, cards, playbooks) | ✅ dona | usa | usa |
| Agentes (AutoBrokers, Atendimento) | blueprint | ✅ instância única | usa |
| Conversas/histórico do Chat Principal | — | — | ✅ (JÁ É ASSIM: `conversations.user_id`) |
| Conhecimento (RAG) | ✅ curado | ✅ docs da corretora | ✅ NOVO: docs pessoais |
| Conectores (Drive/Notion/Outlook…) | templates | ✅ conexão da corretora | ✅ NOVO: conexão pessoal |
| Auxiliares/Rotinas | galeria | ✅ instalados p/ todos | ✅ NOVO: pessoais |
| WhatsApp | — | ✅ por FUNÇÃO (SPEC-045) | nunca (entrega vai AO número do usuário) |
| Custos | plataforma | ✅ total + POR PESSOA | vê o próprio |

## Entregas (backend + contratos)

### A. Conversas do Chat Principal — formalizar o que já existe
- FATO: `conversations.user_id NOT NULL` + `/api/conversations` filtra por
  user da sessão. Blindar: varrer TODAS as rotas que listam conversas
  `channel='web'` e garantir filtro por user (a Central de Conversas do
  atendimento já exclui web — correto). Registrar o contrato: conversa web =
  do usuário; conversa whatsapp (segurado) = da corretora.

### B. Conhecimento pessoal (novo escopo `personal`)
- Migração: `documents.owner_user_id uuid NULL` (NULL = da corretora, como hoje).
- `knowledge_scope.py`: novo `SCOPE_PERSONAL`; payload Qdrant ganha
  `owner_user_id` quando personal.
- Busca (search_service): contexto do Core = global + tenant + agent (como
  hoje) **+ personal DO USUÁRIO da sessão** (user_id desce pelo chat request —
  o backend /chat já recebe userId? verificar; se não, adicionar campo
  opcional e propagar até o search). Documento personal NUNCA aparece para
  outro usuário nem para agentes de atendimento.
- Upload (rota dashboard): campo "Para: 🏢 corretora | 👤 só para mim".

### C. Conectores pessoais (padrão ChatGPT Enterprise)
- Migração: `tenant_connections.owner_user_id uuid NULL`;
  trocar o índice singleton por DOIS parciais:
  único `(company_id, connector_template_id) WHERE owner_user_id IS NULL` e
  único `(company_id, connector_template_id, owner_user_id) WHERE owner_user_id IS NOT NULL`.
- OAuth store: aceitar owner_user_id no state/payload.
- Resolução em runtime (tools do Core): conexão PESSOAL do usuário da sessão
  tem prioridade; se não houver, usa a da corretora; nenhuma = indisponível.
- UI (SPEC-045): ao conectar, escolha "🏢 Toda a corretora / 👤 Só para mim"
  com 1 frase de explicação cada. Lista mostra badge de dono.

### D. Auxiliares/Rotinas pessoais
- Migração: `routines.visibility text NOT NULL DEFAULT 'company'`
  (`company`|`personal`); mesmo campo em `tenant_auxiliaries`.
- Defaults inteligentes (menos atrito): rotina criada NO CHAT pelo usuário
  ("toda sexta me manda relatório") = `personal` (é um pedido pessoal);
  auxiliar instalado da GALERIA = `company`. Ambos com opção de trocar.
- Filtros: List/Manage (tools + páginas) mostram `company` para todos e
  `personal` só ao dono. Execução/entrega de personal: destino = telefone do
  PRÓPRIO usuário (users_v2.phone), pelo número de plataforma da corretora.

### E. Custos por pessoa
- `usage_service.track_cost` ganha `user_id` opcional (propagar do chat).
- Endpoint agregado: total da corretora + quebra por usuário (30d).
- Superfície (SPEC-045): card "Custos e Uso" DENTRO de Corretora; a página
  de Configurações do usuário mostra só o consumo próprio.

## Invioláveis
- Nada de RBAC paralelo: papéis continuam owner/admin/member (users_v2).
- Global permanece blindado (POLITICA-SEGURANCA): agentes usam, ninguém lista.
- Migrações expand-only; defaults preservam comportamento atual (tudo que
  existe hoje continua = corretora; nada muda para a Resulta sem ação).
- Testes house-style por entrega; bateria completa antes de cada deploy.
