# POLÍTICA DE SEGURANÇA — Conhecimento Global (a Inteligência da AutoBrokers)

> Decisão do founder (14/07/2026), inegociável. Aplica-se a TODA a inteligência
> global construída por nós: mapa InfoCap, skills, plugins, playbooks, knowledge
> cards, mapas de URA, e até conhecimento público que NÓS organizamos.

## O princípio

O conhecimento global é a **inteligência da AutoBrokers** — o moat. Ele existe para
**os nossos agentes serem mais inteligentes a favor de TODAS as corretoras**, mas
o CONTEÚDO **nunca** é acessível/exportável por corretora, corretor ou qualquer
usuário externo. Aparecer nas Memórias (para dar volume e impressionar) é
permitido; **acessar o que tem dentro, não.**

Regra de ouro: **os agentes USAM; ninguém de fora VÊ, LISTA ou BAIXA.**

## Como está garantido (verificado 14/07)

1. **Isolamento por company_id (multi-tenant).** Toda rota de conhecimento do
   dashboard (`/api/dashboard/knowledge`, `upload`, `memorias`) trava o
   `company_id` na sessão do usuário (`requireCompanyMember`) — a corretora NUNCA
   consegue passar o id da empresa técnica "AutoBrokers Global Knowledge" nem o de
   outra corretora. Uma corretora só lê a própria InfoCap e o próprio cofre.
2. **Sem rota de download.** Não existe endpoint no dashboard que devolva o
   arquivo/conteúdo bruto de um documento — nem do próprio tenant, nem do global.
3. **Memórias mascaradas.** Os nós globais no grafo aparecem como
   "{Tema} AutoBrokers #N" — **sem o file_name real, sem data, sem conteúdo,
   marcados `locked`**. Dão volume visual; não revelam a estrutura da inteligência.
4. **A busca global só serve o AGENTE.** `KNOWLEDGE_GLOBAL_SEARCH` injeta o
   conteúdo global apenas no context pack interno do LLM (search_service), que o
   usa para RESPONDER — nunca é devolvido como lista de documentos ao cliente.
5. **Admin only.** A gestão da biblioteca global (upload, listagem de arquivos)
   vive no PORTAL ADMIN, sob `require_master_admin` — fora do alcance das corretoras.

## Regras para novas features (obrigatórias)
- Nenhuma rota nova pode devolver `file_name`, `content`, url de storage ou chunks
  de documento com `scope` global/de outra empresa para um usuário não-master.
- O LLM, ao usar conhecimento global, pode CITAR a fonte de forma genérica
  ("segundo a jurisprudência consolidada..."), mas é instruído a NÃO listar/dump
  do acervo ("me liste todos os documentos" → recusa educada).
- Skills/plugins/prompts internos seguem a mesma regra: executam, não se expõem.
- Toda telemetria/log mascara conteúdo global (só contadores/hashes).

## O que o corretor PODE ver
- Que a biblioteca existe e o seu TAMANHO (contagem por tema) — para valor/venda.
- Cadeado nos temas fora do seu plano (gatilho de upgrade).
- As RESPOSTAS que o Chat Principal gera USANDO esse conhecimento (mastigadas).
