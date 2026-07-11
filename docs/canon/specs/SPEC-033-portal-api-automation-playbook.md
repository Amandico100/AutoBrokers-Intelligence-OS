# SPEC-033 — Playbook: automação de portais de seguradora por API (método F12/Network)

**Autor**: Fable 5 (líder técnico) · 2026-07-11 · **Status**: VALIDADO EM PRODUÇÃO (Allianz cobrança)
**Origem**: aprendizado real ao construir o Auxiliar de Cobrança Allianz. Este documento é o
**método canônico** para automatizar QUALQUER fluxo dentro de um portal de seguradora
(cobrança, cotação, renovação, sinistro, emissão de 2ª via, etc.). Não cria motor paralelo:
roda dentro do `portal_worker` (SPEC-020) e é orquestrado pelo motor de rotinas (SPEC-019).

---

## 1. A grande lição (leia primeiro)

**Dirigir a tela (clicar, digitar, esperar renderizar) é FRÁGIL. Chamar as APIs JSON do portal
direto é ROBUSTO.** No Allianz, a navegação visual falhou ~40 vezes (busca do portal devolvia
"não foram encontrados" para a automação headless mesmo com o cliente existindo, popovers Angular
não montavam, apps quebravam no boot). Quando passamos a chamar as APIs internas que a própria
tela usa, funcionou de primeira e ficou determinístico.

**Regra de ouro:** para LER e BAIXAR (dados, boletos, apólices, PDFs) → **API direta**.
Para AÇÕES transacionais (cotar, emitir) → **híbrido**, e **sempre parar antes de finalizar/emitir**.
Manter a navegação visual como **fallback** (se a API mudar, o agente ainda tenta pela tela;
se a tela mudar, ele usa a API). Isso respeita o pedido do founder: determinístico onde dá,
mas com o direito de raciocinar e escalar para humano quando algo sai do script.

---

## 2. Como descobrir as APIs de um portal (o que PEDIR ao founder)

O agente **não** tem o navegador do corretor logado. Então o corretor captura os endpoints uma
vez, com o portal aberto e logado, assim (mande este passo a passo a ele):

1. Abrir o portal e o fluxo desejado (ex.: buscar um cliente inadimplente).
2. `F12` → aba **Network** → marcar **Preserve log**.
3. Executar a ação na tela (ex.: digitar o nome e clicar na opção).
4. Nas linhas que aparecem, **ignorar** o que tem `google-analytics`, `collect`, `gtm`,
   `analytics`, `.js`, `.css`, `.png`, fontes — é rastreamento/estático.
5. Clicar na linha que é uma chamada de API (Type `xhr`/`fetch`, Status 200, Content-Type
   `application/json`, URL com `/api/`).
6. Copiar 3 abas dessa linha: **Headers** (Request URL + Request Headers), **Payload** (corpo
   enviado) e **Response** (o JSON de volta).
7. Repetir para cada passo do fluxo (buscar → detalhar → baixar). Encadear pela resposta:
   a resposta de um passo (ex.: `clientId`) vira o input do próximo.

**O que o líder faz com isso:** reconstrói a cadeia de chamadas `fetch` in-page, encadeada,
com os headers reais. Valida cada passo com `curl`/httpx usando o token do corretor (válido ~24h)
antes de escrever no worker.

---

## 3. Autenticação (a parte que mais dá trabalho)

- Os BFFs modernos da Allianz (`rws-bff-azb-epac`, `rws-bff-file-management`) usam **JWT Bearer**
  no header `Authorization`, além de `epac-company-id` e `x-rws-rootapp` (o valor deste MUDA por
  app: `ngx-azb-epac` para o shell, `spa-file-management` para a ficha de gestão). Sempre casar o
  `x-rws-rootapp` com o BFF chamado.
- O token vive no `sessionStorage` (`STORAGE_NGX-AZB-EPAC::access_token` e/ou `access_token`).
  **Usar o de MAIOR `exp`** (o do shell restaurado costuma vir vencido).
- **Sessão restaurada = tokens vencidos.** A sessão salva do worker (`portal_sessions`) envelhece;
  o access token E o refresh token expiram e o app **não** se auto-renova como no navegador real.
  Sintoma: `401 {"error":"invalid_token","error_description":"Access token expired"}`.
- **Solução validada:** quando o token está vencido, fazer **login LIMPO num contexto novo do
  navegador** (a senha em `portal_accounts.secret_encrypted` é válida — dá pra conferir decifrando
  com `PORTAL_VAULT_KEY`), navegar até o app autenticado (ex.: `.../ngx-azb-epac/private/home`) para
  o SPA **minar um token fresco**, e rodar a cadeia de API nesse contexto. Ver
  `_download_via_fresh_login` em `allianz_corretor.py`.
- **NUNCA** logar/escrever token, senha ou PII em claro. Comparações de credencial são feitas em
  memória; escrita só no cofre Fernet (`portal_worker/vault.py`).

---

## 4. A cadeia validada (Allianz cobrança) — modelo de referência

Todos os passos são `fetch` in-page (mesma origem), com `credentials: 'include'` + os 3 headers.

1. **Buscar por nome** — `POST /rws-bff-azb-epac/api/searchEngine/getCustomersName/<agente>`
   body `{"action":"","customersList":[],"numPag":1,"textSearch":"<NOME>"}` →
   `data.customersList[] { clientId, name, documentId }`. (Cliente pode ter VÁRIAS contas.)
2. **Apólices do cliente** — `GET /rws-bff-azb-epac/api/customerPositonPolicies/policies/<clientId>?policeRef=0&applicationRef=0&agentId=<711110>&collaborator=0&agentCol=0`
   → `data.policies[] { policyNumber (=nº interno/poliza), policySusep, covered }`.
   **Casar `policySusep` com a SUSEP da inadimplência** para escolher a apólice/conta certa
   (resolve o caso de cliente com 2 contas sem chutar).
3. **Documentos** — `POST /rws-bff-file-management/api/fileManagement/getListIni`
   `{poliza, aplica:0, tiporef:'P', usuarioenvio:<login>, fejecucion:99999999, vista:'EP', origen:'EP', subVista:'P', busqueda:'IN', appOrigen:''}`
   → lista agrupada por mês; achar `file.descmodelo` contendo "inadimpl" (Carta Inadimplência).
4. **Baixar o PDF** — `POST /rws-bff-file-management/api/fileManagement/getDetail`
   `{vista:'EP', codFicha, modelo, tipoRef:'P', tipoDoc:'I', gtl, ut, itemId26, ref:<poliza>, marcarLeido:true}`
   → campo **`imagen` = PDF em base64** (`tipoDoc:'I'` é a chave — 'obtenerDetalle' não traz a imagem).
   base64decode → `%PDF-` → upload no storage → anexa no WhatsApp.

Detalhes do agente: `agentPath` (7 díg, ex. `0711110`) e `agentId` (sem zero à esquerda, `711110`)
são decodificados do próprio JWT (`epac-broker`/`user_name`).

---

## 5. Estrutura no código (onde mora)

- `backend/portal_worker/journeys/allianz_corretor.py` — a journey. `_API_CHAIN_JS` (fetch
  encadeado), `_download_carta_via_api_chain`, `_download_via_fresh_login`. Navegação visual =
  fallback. Contexto do navegador: `locale pt-BR`, `timezone America/Sao_Paulo`, shim de
  `setAttribute` (apps legados quebram em headless en-US).
- `backend/app/services/billing_collection.py` — orquestração da rotina (smith-api): enfileira
  `portal_jobs`, consolida, monta a mensagem, envia WhatsApp (teste/aprovação/live), anti-duplicação.
- Tabelas: `portal_accounts` (credencial Fernet), `portal_sessions` (storage_state), `portal_jobs`
  (fila/resultado), `billing_sent_log` (anti-duplicação).

---

## 6. Como aplicar a OUTRO portal (passo a passo p/ o próximo chat)

1. Founder captura no console os endpoints do fluxo desejado (seção 2).
2. Validar cada endpoint com o token do corretor (curl) — confirmar payload/response.
3. Criar/atualizar a journey do portal em `portal_worker/journeys/<portal>.py` seguindo o modelo:
   `_API_CHAIN_JS` da seguradora + `_download_via_fresh_login` (login limpo p/ token fresco).
4. Adicionar o `portal_key` ao `DEFAULT_PORTAL_KEYS`/config da rotina; credencial em `portal_accounts`.
5. Testar em modo `test` (só o número de teste recebe) até o job dar `done` com PDF.
6. Manter a navegação visual como fallback e a trava de "parar antes de finalizar" em ações.

**Dificuldades esperadas** (todas já resolvidas na Allianz — reusar as soluções):
token vencido → login limpo; `x-rws-rootapp` errado → 401; app quebra no boot headless →
locale + shim; cliente multi-conta → casar SUSEP; busca visual vazia → usar a API direto.

---

## 7. Extensão a outros serviços (cotação, renovação, etc.)

O MÉTODO é o mesmo (F12 → Network → capturar → replicar). O que muda é o **contrato** (endpoints
e payloads) e o **risco**:
- **Cotação**: transacional multi-step (produto → risco → coberturas → cálculo → emitir). Precisa
  capturar TODO o fluxo, provavelmente lidar com CSRF/`X-XSRF-TOKEN`/checksum entre passos, e
  **parar antes de emitir** (freio obrigatório, como no acionamento de seguradora). Recomendação:
  híbrido — partes estáveis (FIPE, CEP, catálogos) por API; submissão com fallback visual + freio.
- **Renovação / 2ª via / consulta**: majoritariamente leitura → API direta, igual à cobrança.

**Regra:** para cada novo fluxo, decidir caso a caso (só-API vs híbrido) e sempre achar a solução
mais robusta. Este playbook é o ponto de partida; adaptar ao portal.
