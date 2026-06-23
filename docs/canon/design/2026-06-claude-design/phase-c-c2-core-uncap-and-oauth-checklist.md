# C2 (parte 1) — Core descapado + InfoCap por papel + checklist OAuth Drive/Notion

> Data: 2026-06-23. Responde às dúvidas do Founder e entrega os ajustes imediatos. OAuth Drive/Notion = parte 2 (depende das credenciais que só você cria).

## 1. Sua dúvida: a InfoCap é UMA conexão para todos?
**Sim — uma conexão por corretora, com regras diferentes por papel.** Não existem 3 InfoCaps (Chat/Atendimento/Auxiliar). Existe **1 conexão técnica** (credencial no Vault) e o **Capability Registry** decide quem pode usá-la:
- **Chat Principal (Core)** → uso INTERNO amplo: lê apólices/coberturas/vigências/parcelas/segurado da própria corretora e **entrega ao corretor** (ele é o dono). *(Descapado neste batch.)*
- **Even / Atendimento (WhatsApp)** → usa a MESMA conexão técnica, mas com **política externa restrita** (prompt evidence-first, por identidade/contexto/consentimento). Não despeja dado de terceiro a qualquer um.
- **Auxiliares** → só recebem InfoCap se a capability declarada do auxiliar exigir (ex.: relatório de carteira).
- **Permissões** (tela Conectores) não criam outra conexão — definem quais papéis podem chamar a mesma.

Resumo: **mesma credencial, exposição diferente por papel.** Liberar tudo para o Core e restringir o Atendimento é uma questão de POLÍTICA (prompt + Registry), não de conexões separadas.

## 2. Ajustes entregues agora (já no código)
- **Core descapado**: o prompt do Core não recusa mais dados de apólice/cobertura ao corretor "por privacidade". Ele entrega o que a InfoCap retornar; só não inventa o que a fonte não trouxe. Ação externa (enviar/abrir) continua exigindo aprovação; leitura para o corretor não.
- **Detalhe de cobertura**: a tool InfoCap do Core agora tem 2 modos — listar (CPF/nome) e **detalhar** (passando `policy_ref`) → traz coberturas/itens da apólice. (Antes só listava.)
- **Even continua restrito** (prompt de atendimento inalterado).
- **Bug do menu corrigido**: agora **"Arquivar conexão" aparece sempre** (resolve o Notion TESTE que não deixava excluir nem arquivar). "Excluir rascunho vazio" é extra só para rascunhos.
- **Singleton aplicado em produção**: arquivei os 3 testes da Rafael e criei o índice `uniq_active_connection_per_template` → **impossível duplicar conexão** (acabou InfoCap 1/InfoCap 2). *(Você não precisa rodar SQL — já está feito.)*

## 3. Próximo passo (parte 2): OAuth Google Drive + Notion
A conexão certa é **OAuth oficial** (não MCP para login). Os MCP/HTTP Tools entram como execução depois. Para eu ligar, **você precisa criar os apps OAuth** (são suas contas) e me passar os IDs. Checklist exata:

### Google Drive (Google Cloud Console)
1. Criar projeto (ou usar um) em console.cloud.google.com.
2. **APIs & Services → Library**: habilitar **Google Drive API**.
3. **OAuth consent screen**: tipo External; nome do app; e-mail de suporte; escopos: `drive.readonly` (leitura) — e `drive.file` se quiser leitura de arquivos selecionados.
4. **Credentials → Create OAuth client ID → Web application**.
5. **Authorized redirect URI** (exata): `https://autobrokers-intelligence-os-autobrokers-smith-web.golhpm.easypanel.host/api/connectors/google-drive/callback`
6. Copiar **Client ID** e **Client Secret**.
7. Envs no **serviço web (Next)** do EasyPanel: `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GOOGLE_OAUTH_REDIRECT_URI` (a URL acima).

### Notion (Notion Integrations)
1. notion.so/my-integrations → **New integration → Public**.
2. Tipo **Public** (OAuth); nome; logo.
3. **Redirect URI** (exata): `https://autobrokers-intelligence-os-autobrokers-smith-web.golhpm.easypanel.host/api/connectors/notion/callback`
4. Copiar **OAuth client ID** e **client secret**.
5. Envs no serviço web: `NOTION_OAUTH_CLIENT_ID`, `NOTION_OAUTH_CLIENT_SECRET`, `NOTION_OAUTH_REDIRECT_URI`.
6. (No uso) o corretor autoriza e **escolhe quais páginas/bases** compartilhar com a integração.

### O que eu faço quando você tiver os IDs (parte 2)
- Fluxo Catálogo → **Conectar → OAuth oficial → callback → Conectado ✓ → Quem pode usar** (reusando Vault/Registry; sem rascunho-lixo se o OAuth não estiver configurado).
- Capabilities `knowledge.google_drive.read/search` e `knowledge.notion.read/search`; refresh token + healthcheck + desconectar.
- Core lê/busca tudo que a corretora autorizou (sem escrita neste passo); Auxiliares conforme declaração; Even não recebe acesso cru.

> Observação honesta: **escrita/edição** em Drive/Notion fica para depois (mais sensível). Primeiro leitura robusta (que é o que o Core precisa pra trabalhar com as fontes da corretora). Quando você quiser escrita, ligamos com aprovação para ação externa.

## 4. Teste agora (após deploy)
1. Chat: *"detalhe as coberturas da apólice de vida da Zurich do CPF 030.743.279-36"* → o Core deve **trazer os detalhes** (ou dizer honestamente que a InfoCap não retornou os itens), **sem recusar por privacidade**.
2. Conectores → Notion TESTE → **⋯ → Arquivar conexão** → some da lista.
3. Tentar criar 2ª InfoCap → impedido (índice singleton).
