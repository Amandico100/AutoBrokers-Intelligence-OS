# LAUDO — O Agger como canal para as seguradoras, e o mercado de acesso estável

> 📋 **Cópia para o canon (11/10/2026, agente de síntese):** revisada por `grep` de CPF/CNPJ, telefone, e-mail, nº de apólice e nomes próprios de pessoa → **0 ocorrências a redigir**. Nenhuma credencial: do `/incorp_url_post` só a FORMA da resposta, nunca os valores. Os caminhos `scratchpad/…` citados são do rascunho da sessão e não estão no repositório. O resumo para o Founder está em [`MAPA-DE-POSSIBILIDADES-INFOCAP-AGGER-SEGURADORAS.md`](MAPA-DE-POSSIBILIDADES-INFOCAP-AGGER-SEGURADORAS.md).

> Modo INVESTIGAÇÃO (protocolo §3.3) · read-only · 11/10/2026 · investigador + pesquisador (Opus 5.5)
> 🔴 Nenhum login no Agger nem em portal de seguradora. Fontes: capturas já existentes no repositório, o bundle JS
> **público** do Aggilizador (baixado sem login), documentos públicos das seguradoras e da SUSEP, imprensa.
> Nenhum dado pessoal neste laudo. Nenhum arquivo do repositório foi alterado.
> 📊 medido (com o comando) · 💭 ilustrativo · FATO / INFERÊNCIA / RECOMENDAÇÃO separados.

## 0. EXECUTION CARD (investigação)

```
OUTCOME ........ o Founder sabe o que o Agger faz além do cálculo (transmitir? boleto? apólice?), quais caminhos
                 estáveis existem no mercado para cobrança/transmissão/InfoCap/endosso, e a nota de cada ideia
RISCO / SUPERF.  0 (só leitura de material público e já capturado) · SUPERFÍCIE 3 (território não mapeado) → INVESTIGAÇÃO
O ELO .......... "o Agger NÃO transmite" é afirmação de AUSÊNCIA: medida no bundle INTEIRO (161 arquivos), não num chunk
REFERÊNCIA ..... interna: A-PROVA-DO-AGGER.md · LAUDO-CORPAPI-ROTA-A-ROTA.md · portal_worker/journeys/*_corretor.py
                 externa: §6 (URLs)
```

## 1. Em uma tela

| pergunta | resposta curta | força |
|---|---|---|
| O Agger **transmite/efetiva** a proposta na seguradora? | **NÃO.** Não existe rota de transmissão/emissão na API. O "Fechar negócio" é CRM (marca ganho/perdido, sobe o PDF da proposta, prêmio, comissão). O que existe é **"Ver na seguradora"**: uma **extensão do Chrome** recebe login+senha da seguradora e o nº do cálculo e abre o portal da seguradora, logado, naquele cálculo — **um humano** termina lá. | 📊 FATO (bundle) |
| O Agger baixa **boleto / 2ª via**? | **NÃO baixa boleto.** Tem uma tela **"Parcelas pendentes"** (lista: segurado, apólice, parcela, valor, vencimento, seguradora, tipo de pagamento) alimentada por **robôs do próprio Agger**; a ação da linha é "Ver na seguradora" (extensão abre o portal) — sem PDF de boleto. | 📊 FATO (bundle) |
| O Agger consulta **apólice emitida / proposta / extrato**? | **SIM, como "Sincronizações"**: "Apólice digital" (PDF da apólice/endosso, nº, emissão), "Proposta digital" (PDF), "Extrato de comissão" (PDF), "Parcelas pendentes". O usuário pede "sincronizar" um período × seguradoras; o servidor do Agger dispara robôs e devolve os documentos. | 📊 FATO (bundle) · ⚠️ NÃO medido se as nossas contas têm o módulo |
| **Endosso / sinistro** pelo Agger? | Só **leitura** do nº de endosso dentro da "Apólice digital". Não há abertura de endosso nem de sinistro. | 📊 FATO (bundle) |
| Quem é o Agger hoje | **Agger comprou a InfoCap** (09/01/2024) e a **Dimensa** (Totvs/B3, hoje sob a Evertec) comprou o Agger (fechado 03/07/2025, R$ 260 mi), dona também da **Quiver**. Agger + InfoCap + Quiver = **mesmo grupo**. | FATO (imprensa, §6) |
| Melhor caminho estável para **cobrança** | o que o produto **já faz** (cliente HTTP derivado de HAR, 5–6 seguradoras) + **API oficial onde existe** (a **HDI** publica parcelas com status e 2ª via de boleto) + login assistido 1× com sessão persistente | INFERÊNCIA + RECOMENDAÇÃO |
| Melhor caminho para **cadastrar a proposta na InfoCap** | o fluxo **InCorp** da própria CorpAPI (upload do PDF → a IA da Corp lê → grava o documento) | 📊 FATO (rotas existem) · escrita NÃO testada |

## 2. O Agger por dentro — o que o código público diz (Pergunta 1)

### 2.1 Como foi medido
- 📊 HAR existentes: `docs/intake/MULTICALCULO AGGER/{GERAL,RENOVAÇÃO 1,RENOVAÇÃO 2}/*.har` (18/09/2026) → endpoints únicos
  extraídos com `json.load(har)['log']['entries']` (lista no §2.4). 📊 102 arquivos JS vieram dentro dos HAR.
- 📊 Bundle atual: `curl https://aggilizador.com.br/` (público, sem login) → `main-LVUAYDI7.js` + crawl recursivo de
  `import("./chunk-*.js")` → **161 arquivos, 22 MB** (`scratchpad/aggnow/`). Rotas lidas da tabela do roteador Angular
  (`re.findall(r'path:"([^"]*)",load(?:Component|Children)...` em `main-LVUAYDI7.js`) — **44 rotas**.
- Busca de termos (`transmi|emiss|emitir|boleto|parcela|apolice|endoss|efetiv|proposta|segundaVia|sinistro|fechar`)
  sobre todas as strings do bundle (script Python no rascunho).

### 2.2 O que existe — por função

| função | rota da tela | API (host · caminho) | o que faz | FATO/INFERÊNCIA |
|---|---|---|---|---|
| multicálculo | `/cotacao/:ramo/...` | `api-prod…/calculo/calcularV2`, `calculo/cotacao/versoes/`, `calculo/print` | o que a 129-B já usa | 📊 FATO |
| **"Ver na seguradora"** (continuar o cálculo no portal) | botão no resultado | `window.postMessage({type:"VER_CALCULO" \| "VER_CALCULO_RESIDENCIAL", text: {login, senha, numeroRef, seguradora,…}}, "*")` → **extensão Chrome "Aggilizador"** (`ebmkefigmmcbigompbbacndedlapmdcc`) | abre o portal da seguradora logado no cálculo; **o humano transmite lá** | 📊 FATO (`chunk-6WTLBPCZ.js`, função `verNaSeguradora`) |
| login automático no portal | "Minhas plataformas"/config | `postMessage({type:"REALIZAR_LOGIN"})` (Justos e Axa com token próprio) | só abre o portal logado | 📊 FATO (`logarSeguradora`) |
| **Fechar negócio** | modal de fechamento | `POST api-prod…/calculo/fechaNegocio` | CRM: fechado/perdido, upload do PDF da proposta, prêmio, comissão, franquia, forma e nº de parcelas | 📊 FATO (`chunk-IYMSSAB4.js`, rótulos "Upload da proposta", "Valor do prêmio"…) |
| **Proposta digital** | `/propostas` | `GET pdocs.aggilizador.com.br/cor/getProposal` | lista + PDF da proposta (`window.open(e.file)`) | 📊 FATO (`chunk-C3Q3VTFE.js`) |
| **Apólice digital** | `/apolices` | `GET pdocs…/cor/documentos?dataEmiIni&dataEmiFim&texto&seguradora` | segurado, **apólice/endosso**, data de emissão, seguradora, **PDF** (`Body.FileUri` ou `anexos[0].url`; o formato "Body" é de fila **SQS**) | 📊 FATO (`chunk-WJ6ID4YO.js`) |
| **Extrato de comissão** | `/extratos` | `GET pdocs…/cor/getExtract` | PDF do extrato por seguradora | 📊 FATO (`chunk-VQRYF65O.js`) |
| **Parcelas pendentes** | `/parcelas-pendentes` | `GET pdocs…/cor/getParcelasPendentes?initial_date&final_date&segurado&seguradora` | nome, apólice (`nrDocum`), nº parcela, valor, vencimento, seguradora, tipo de pagamento; ação = "Ver na seguradora" (`VER_PARCELAS`, só com a extensão ativa) — **sem PDF de boleto** | 📊 FATO (`chunk-XBT6OV4E.js`) |
| disparar a sincronização | botão "Sincronizar" | `POST pdocs…/cor/enviarRequisicao {dataIni, dataFim, tipo, seguradoras[], usuarioId, customerId}` · acompanhar: `GET pdocs…/cor/getRequisicoes?tipo` (a tela espera até **10 min**) | os **robôs do Agger** vão às seguradoras com as credenciais **compartilhadas** da corretora | 📊 FATO (`chunk-GUEGRI6A.js`, `chunk-OZW74FP6.js`) |
| que seguradoras sincronizam o quê | — | `GET pdocs…/app/seguradoraStatus/` → por seguradora `proposalStatus`, `documentosStatus`, `extractStatus`, `parcelasStatus` (ativa se ∈ {1, 10}) | **a lista por seguradora mora no servidor** | 📊 FATO (a regra) · ⚠️ a LISTA não foi medida (exige login) |
| tipos de robô | — | enum: `APOLICES=1 · PARCELAS_PENDENTES=4 · EXTRATO=6 · PROPOSTAS=7` | | 📊 FATO |
| impressão do orçamento ao cliente | `/cotacao/:id/impressao`, `/orcamento-cliente` | `pdocs…/calculo/orcamento`, `…/marcaEnviado`, `calculo/enviarCotacaoEmail` | PDF/WhatsApp/e-mail para o cliente | 📊 FATO |
| outros | `/online` (site do corretor), `/to-segurado`, `/atendimento-ia` (plugin Conversu), `/meu-plano`, `/modulos-adicionais` | `hub.aggilizador.com.br`, `quiverplus.net.br`, `quiverpro.net.br`, `app.tosegurado.com.br` | integrações do grupo | 📊 FATO (hosts no `environment`) |

📊 Termos procurados que **não existem** como rota/serviço em nenhum dos 161 arquivos: transmitir/transmissão, emitir proposta,
efetivar/efetivação, segunda via de boleto, abertura de endosso, abertura de sinistro (o único "Emitir" é `eventEmitirPdf`,
gerar o PDF do orçamento). Comando: o script de busca de strings do §2.1. → **FATO: o Aggilizador não transmite.**

### 2.3 Por seguradora
- **"Ver na seguradora"**: 📊 para todas, **exceto 2 ids** (`seguradora != 19 && != 24` → "Acesso temporariamente
  indisponível"). Na tabela de seguradoras do bundle, `id` 19 = Sancor e 24 = Sura; `idAgger` 19 = Indiana e 24 = Affinity —
  **qual espaço de id o código usa não foi resolvido**.
- **Sincronizações** (apólice/proposta/extrato/parcelas): a lista por seguradora vem de `app/seguradoraStatus/` —
  **NÃO medida** (exige login; 🔴 não feito por regra). 💭 Hipótese a conferir numa sessão já autorizada: as grandes de auto
  (Porto, Allianz, Tokio, HDI, Bradesco…) sincronizam apólice; parcelas é o tipo mais restrito.
- ⚠️ **Disponibilidade nas nossas contas: NÃO medida.** O menu "Sincronizações" depende da permissão `SINCRONIZACOES`; no
  §11 da A-PROVA o menu do robô da Resulta mostrou "Cotações · Dashboard · Tarefas · Minhas plataformas · Configurações" e o da
  AutoFleet só "Cotações · Configurações" — **sem** Sincronizações. INFERÊNCIA: é módulo/plano (o produto "ONE" da Dimensa
  vende gestão + multicálculo + sincronização juntos) ou permissão de perfil.

### 2.4 Endpoints que as capturas de 18/09 já tinham (para registro)
📊 `api-prod.aggilizador.com.br`: `usuario/login`, `usuario/login/pdocs`, `calculo/calcularV2`, `calculo/seguradoras`,
`cfg/seguradora/config`, `cfg/cobertura`, `cfg/assinatura-aggilizador`, `cadastros/cliente`, `dashboard/tarefas`,
`notificacoes/busca-notificacoes`, `saude/operadoras`, `usuario/{buscaSeguradorasEscondeLead,getResearch,listaUsuarios,usuarioBuscarPreferencias}`;
`api.aggilizador.com.br`: `Auto/Data`, `Travel/Data`. **Nenhum** de sincronização (as telas não foram abertas na gravação).

### 2.5 🔴 Achado de segurança (do Agger, que nos toca)
📊 FATO: para "Ver na seguradora", o front do Agger monta `{login, senha}` da seguradora e faz `window.postMessage(..., "*")`
(alvo `"*"` = qualquer ouvinte da janela). Logo a **API do Agger devolve a senha da seguradora em claro** a qualquer usuário
logado da corretora — inclusive ao login do robô (a A-PROVA §11 só leu "preenchido/vazio", nunca o valor).
INFERÊNCIA/RECOMENDAÇÃO: (a) o `agger_guarda` e o leitor **nunca** devem gravar/registrar a resposta de `cfg/seguradora/config`
nem rodar a página do robô com extensão ou script de terceiro; (b) **usar o Agger como cofre de senhas para um robô
nosso é proibido** (nota 5 no §5); (c) avisar o Founder: qualquer funcionário com login no Agger consegue as senhas das
seguradoras — se uma vazar, troca-se no Agger **e** na seguradora.

## 3. O que o produto JÁ tem (para não reinventar — CLAUDE.md §5)

| peça | estado | fonte |
|---|---|---|
| Cobrança por HTTP derivado de HAR (SPEC-033/070) | **Allianz, HDI, Tokio, Yelum ✅** · Zurich (journey existe) · **MAPFRE 🔨 fase 1** · Porto/Azul/Bradesco/SulAmérica ⬜ | `docs/canon/portais/README.md`; `backend/portal_worker/journeys/{allianz,hdi,tokio,yelum,mapfre,zurich}_corretor.py` |
| Regressão 4 seguradoras (12/08/2026) | 📊 22 inadimplentes → **20 boletos**, 20/20 `%PDF`, 2 retidos por regra | `PENDENCIAS.md` ~l.3395 |
| Travas conhecidas | 📊 Bradesco = captcha + **Akamai**; Porto = captcha + **Incapsula/Imperva**; Yelum app logado = **Akamai Bot Manager**; HDI e Tokio bloquearam após ~15 e ~4 visitas em < 30 min | `PENDENCIAS.md` ~l.3343–3380; `portais/README.md` |
| Captcha/2FA hoje | detectado → `needs_human` ("nunca burlado") | `allianz_corretor.py:728,833`; `worker.py:723` |
| InfoCap (CorpAPI) | `/documento.parcelas[]` (venc./quitação por apólice) · `/documento_anexos` (PDFs: 📊 ~31 "BOLETO", 69 PROPOSTA, 77 APÓLICE em 99 apólices) · `/documento_endossos` · **rotas de escrita: `POST /negocio`, `POST /cliente`, fluxo InCorp `GET /incorp_url_post` → POST S3 → `POST /incorp` → `/incorp_contexto` → `/incorp_documento`** · `acompanhamento.emissao.{bot_emitido, bot_a_dthora}` (a InfoCap já tem robô de emissão) | `docs/canon/programa-multicalculo/131-0/LAUDO-CORPAPI-ROTA-A-ROTA.md` §0.1, §1 (l.65–85), §6 |

## 4. O mercado (Pergunta 2)

### 4.1 APIs oficiais das seguradoras para corretor/parceiro

| seguradora | o que existe publicamente | boleto/parcelas | emissão/efetivação | acesso | serve ao AutoBrokers? |
|---|---|---|---|---|---|
| **HDI** | portal `developers.hdi.com.br` com índice público: **Cotação, Recálculo, Efetivação, Impressão Proposta, Lista de Propostas com Status, Lista de Apólices Emitidas, Detalhes da Apólice, 2ª via de Apólice, Extrato de Comissões, Lista de parcelas com status, Impressão da 2ª via do Boleto** — em Auto, Residencial, Frota, Condomínio, Empresarial… | **SIM** | **SIM** | "solicitar acesso" → chaves → OAuth2 (`openapi.hdi.com.br`) | **SIM — a melhor candidata.** INFERÊNCIA: a **Yelum** (mesmo grupo; token em `integracao.grupohdiseguros.com.br`) deve seguir o mesmo caminho |
| **Bradesco Seguros** | `apiportal.bradescoseguros.com.br` + Swagger público: 📊 `API-ParcelasEmAberto.json` (`POST /parcelas-abertas`) e `API-ParcelasPorApolice.json` (`POST /listarParcelasApolice`), servidor `sauto.bradescoseguros.com.br/V2/WSBL-CotacaoCSP/service/`, Bearer JWT; registro interno cita efetivação/pagamento/endosso | SIM (parcelas) · boleto não visto | indício | onboarding de parceiro (PDF "ONBOARDING_PARCEIRO_BS_v2"; mTLS citado) | sim, mas onboarding alto; resolve a trava Akamai |
| **Porto** | `dev.portoseguro.com.br/api-portal` (OAuth2, client_id/secret por APP; produção exige **contrato com a Porto** e aprovação) | catálogo não lido | catálogo não lido | contrato | resolveria a Incapsula; viabilidade comercial incerta |
| **Tokio Marine** | API portal Sensedia + Swagger com apólices/endossos (registro interno) | não confirmado | não confirmado | conta + aprovação | o portal web já funciona por BFF (journey ✅) |
| **Zurich** | `api-portal.zurich.com.br` (OAuth2, app no portal) | catálogo não lido | — | "ponto de contato na companhia" | journey web já existe |
| **Sompo** | `developers.sompo.com.br`: Corretor (login/perfil), Apólices, **Financeiro (status de pagamento)**, Sinistros, Cotação (agro/transporte/garantia) | status de pagamento | não | cadastro no portal + token | útil para empresarial/condomínio da Resulta |
| **SulAmérica** | Sensedia, app com client_id/secret | — | — | alto | baixa prioridade (Resulta usa p/ vida/condomínio) |
| **Yelum (ex-Liberty)** | PDFs técnicos: cotação auto (`client_credentials`), legado Liberty com **E-Retorno** (arquivo de retorno p/ sistemas de gestão) | via E-Retorno (INFERÊNCIA) | cotação | chaves por parceiro | journey web ✅ (REST limpo) |
| **Allianz** | só evidência pontual (Vida Individual, server-to-server) | não | não | aprovação comercial | journey web ✅ (BFF JSON) |
| **MAPFRE, Azul, Suhai, Sura** | sem portal de API público encontrado | — | — | — | só portal web (MAPFRE 🔨) |

Fonte das linhas sem URL própria: `docs/intake/portal-registry/portal_registry_tecnico_resumo_consolidado.csv` (checked_at 2026-04-06, fontes oficiais
na coluna `official_sources`) — ⚠️ pesquisa, não produto (PORTAIS-E-CORREDORES.md).

**INFERÊNCIA central:** API oficial de seguradora quase sempre é concedida a **plataforma parceira** (multicálculo/gestão), não a
corretora pequena; as credenciais são por **app** e o "corretor" vai como parâmetro (código SUSEP/código de corretor). O AutoBrokers
como SaaS multi-corretora é exatamente o perfil de parceiro — **mas o prazo é comercial (semanas/meses), não técnico.**

### 4.2 Open Insurance Brasil (OPIN/SUSEP)
- FATO: Fase 2 = compartilhamento de dados de apólice/pagamentos/sinistros **com consentimento do segurado**; Fase 3 = **iniciação**
  (contratação, endosso, aviso de sinistro, resgate, portabilidade); o Bloco 6 (pessoas, previdência, capitalização) foi adiado para
  30/06/2025. Quem inicia é a **SPOC** (Sociedade Processadora de Ordem do Cliente), credenciada na SUSEP: **sociedade anônima com PL
  mínimo de R$ 1 milhão**, governança, SAC, PLD; **corretora pode ser SPOC** (a 1ª credenciada foi uma corretora, mar/2024).
- FATO: 2025 foi de revisão — Resolução SUSEP 61/2025 (participação voluntária com saída em 30 dias) e um GT interno para rever a norma (21/10/2025).
- INFERÊNCIA: para o AutoBrokers hoje **não serve** para cobrança nem transmissão: exige credenciamento SPOC (S.A. + R$ 1 mi), consentimento
  **por segurado** e a cobertura real de danos/auto nas APIs de iniciação é incerta. Vale acompanhar como **fonte de dados de apólice**
  de prospects (portabilidade de cliente de outra corretora) — horizonte de 2027+.

### 4.3 Outros multicálculos/hubs
| quem | o que faz que importa aqui | serve? |
|---|---|---|
| **Agger / Aggilizador** (Dimensa) | multicálculo + sincronização (apólice/proposta/extrato/parcelas) + extensão "Ver na seguradora"; **não transmite** | já em uso; ver §5 E |
| **InfoCap Corp** (Agger desde 2024) | gestão; anexos de apólice/proposta/boleto; `bot_emitido` (robô de emissão); **InCorp** (IA que lê PDF e cadastra) | já em uso (leitura); a escrita é o caminho C |
| **Quiver** (Dimensa) | gestão "digitação zero": importa PDF de proposta/apólice/comissão; integração automática com seguradoras | concorrente/irmão; não precisamos dele |
| **Segfy** | multicálculo (~18 seguradoras), proposta personalizada, "contratação 100 % digital" (link de proposta) — **sem evidência pública de transmissão automática** | não |
| Serviços genéricos de boleto (Asaas, Cora…) | emitem boleto **do próprio cedente** | **não servem**: o boleto do seguro é da seguradora |
INFERÊNCIA: no mercado brasileiro **ninguém público vende "transmissão automática em todas as seguradoras"**; o padrão de quem
"transmite" é **deep link/extensão para o portal** (Agger) ou **API oficial seguradora a seguradora** (HDI/Yelum/Bradesco).

## 5. Por que navegador é instável, e como se resolve (Pergunta 3)

**As 5 causas, medidas no próprio projeto:**
1. **Anti-bot (WAF)** — Akamai (Bradesco, Yelum app), Incapsula/Imperva (Porto): bloqueiam por impressão digital do navegador/IP.
2. **Captcha/2FA no login** — hoje vira `needs_human` (correto).
3. **Teto de frequência** — HDI ~15 e Tokio ~4 visitas em < 30 min derrubaram o acesso.
4. **Sessão única** — no Agger, uma sessão nova derruba/avisa a pessoa (A-PROVA §10); token de 3 h; recarga = troca de token.
5. **Tela muda** — DOM/iframe mudam sem aviso; o "clicar" quebra; a API por baixo muda menos.

**Como projetos sérios resolvem (padrão):**
| técnica | o que é | o projeto já faz? | nota |
|---|---|---|---|
| **Cliente HTTP derivado do HAR** | chamar a API interna que a tela chama (BFF/REST/GraphQL) | **SIM** (SPEC-033; 6 journeys; Agger por `calcularV2`) | manter — é o certo |
| **Navegador só no login, HTTP no resto** | logar num navegador real (headful, IP fixo) e reaproveitar cookie/token | parcialmente | ⬆ ampliar para Porto/Bradesco |
| **Sessão persistente** | guardar `storageState`/cookies/refresh-token no Vault, renovar antes de vencer, 1 sessão por credencial com *lease* | `leases.py` existe; persistência por seguradora varia | ⬆ |
| **Login de serviço separado** | usuário próprio do robô na seguradora/Agger (como `cotador@` no Agger) — não derruba a pessoa | **SIM no Agger**; nas seguradoras, não | ⬆ pedir sub-usuário em cada portal que permita |
| **Captcha** | resolver por serviço (2Captcha etc.) **viola termos** dos portais e o espírito do CLAUDE.md; o padrão sério é **humano 1× + sessão longa** | `needs_human` | manter; acrescentar "login assistido" (o corretor resolve 1× pelo celular, o robô herda a sessão) |
| **2FA** | (a) **TOTP**: a corretora cadastra o segredo do autenticador no Vault e o robô gera o código (RFC 6238); (b) **e-mail**: caixa dedicada do robô lida por API; (c) **SMS**: frágil — evitar | não | ⬆ por seguradora, conforme o 2FA dela |
| **Ritmo e testemunha** | teto de visitas, janela fora do horário, controle intercalado, fixture para repetir leitura | **SIM** (SPEC-070) | manter |
| **Canário diário + impressão digital do esquema** | 1 login/dia por seguradora e comparação da forma da resposta → alerta antes do cliente sentir | parcial (`infocap-schema-fingerprints.json`) | ⬆ estender aos portais |
| **Contrato/API oficial** | sair do portal | não | o único caminho realmente **estável** — §4.1 |

## 6. LISTA DE IDEIAS — nota 0–100 (valor × viabilidade × estabilidade)

### A. Cobrança estável em todas as seguradoras
| # | ideia | V | Vi | E | **nota** | por quê |
|---|---|---|---|---|---|---|
| A1 | **Consolidar o que já existe** (Allianz/HDI/Tokio/Yelum ✅, Zurich, MAPFRE 🔨) com sessão persistente no Vault + login assistido 1× + canário diário | 95 | 90 | 70 | **85** | 4 já provadas em produção; o problema é manter, não construir |
| A2 | **API oficial da HDI** (parcelas com status + 2ª via do boleto) e **Yelum** pelo mesmo grupo | 85 | 70 | 95 | **82** | catálogo público confirma as duas rotas; troca robô por contrato |
| A3 | InfoCap como **detector** do que está em aberto (`/documento.parcelas[]` com `datquit`) e **boleto já anexado** (`/documento_anexos` "BOLETO") | 70 | 90 | 90 | **75** | estável e já lido; mas boleto só existe quando alguém anexou (~31/99) e a quitação depende da baixa manual |
| A4 | Porto e Bradesco por **API oficial** (Bradesco já publica `parcelas-abertas`) em vez de enfrentar Akamai/Imperva | 85 | 45 | 95 | **68** | resolve as duas mais difíceis; onboarding comercial lento |
| A5 | Agger "Parcelas pendentes" como **lista** multi-seguradora (sem boleto) | 55 | 40 | 70 | **50** | exige módulo/permissão não medidos, escrita `enviarRequisicao` (D-MC-28), e ainda falta o PDF |
| A6 | Navegador para Porto/Bradesco com contorno de WAF/captcha | 70 | 30 | 20 | **25** | bloqueio e risco à credencial da corretora |
| A7 | Open Insurance para dados de pagamento | 40 | 10 | 60 | **15** | SPOC + consentimento por segurado |

### B. Efetivar/transmitir a proposta fechada
| # | ideia | V | Vi | E | **nota** | por quê |
|---|---|---|---|---|---|---|
| B1 | **Humano transmite com 1 clique**: o AutoBrokers deixa a proposta pronta (dados conferidos, aceite do cliente, Approval) e o corretor usa o **"Ver na seguradora" do Agger** (extensão abre o portal no cálculo) | 80 | 90 | 85 | **82** | zero risco de transmitir errado, já existe, cobre quase todas as seguradoras; o tempo humano cai a ~1–2 min 💭 |
| B2 | **API oficial de efetivação da HDI** (Cotação → Efetivação → Impressão Proposta → Status), depois Yelum/Bradesco | 90 | 55 | 90 | **72** | o único caminho automático estável; é **ENVIO** (piso CRÍTICO) e exige Approval sempre |
| B3 | Robô HTTP transmitindo no portal da seguradora | 85 | 30 | 30 | **30** | irreversível, dinheiro, anti-bot; um erro emite apólice errada |
| B4 | Open Insurance iniciação de contratação | 60 | 5 | 50 | **10** | não disponível para nós |

### C. Cadastrar a proposta na InfoCap
| # | ideia | V | Vi | E | **nota** | por quê |
|---|---|---|---|---|---|---|
| C1 | **Fluxo InCorp da CorpAPI**: `GET /incorp_url_post` → upload do PDF da proposta → `POST /incorp` → `/incorp_contexto` (agente/produtor) → `/incorp_documento` (grava) | 90 | 75 | 85 | **83** | é o caminho oficial da própria Corp, usa a IA dela; ⚠️ escrita nunca testada → ensaio em 1 corretora com 1 PDF, D-decisão do Founder |
| C2 | Perguntar à InfoCap/Agger (mesmo grupo) se o **Aggilizador → Corp** já é integrado (a Corp tem `cotacao.codmulti`, `multi_corp_mais`, `sit_multi`) | 80 | 70 | 90 | **78** | pode ser zero código; custa um e-mail |
| C3 | `POST /negocio` para registrar o negócio/etapa (sem o PDF) | 60 | 80 | 85 | **70** | complementa C1 (pipeline comercial) |
| C4 | Robô digitando na tela da Corp | 50 | 40 | 30 | **25** | a API existe |

### D. Endosso
| # | ideia | V | Vi | E | **nota** | por quê |
|---|---|---|---|---|---|---|
| D1 | **Coletar e preparar** (o agente pega o pedido do segurado, monta o pacote: o que muda, documento, apólice), abrir tarefa e o corretor executa no portal | 75 | 90 | 90 | **80** | endosso varia por seguradora e mexe em prêmio; humano decide |
| D2 | **Acompanhar** o endosso emitido pela InfoCap (`/documento_endossos`, `historico.qtd_endossos`) e avisar o segurado | 65 | 85 | 85 | **74** | leitura estável já disponível |
| D3 | Endosso por API oficial (Bradesco cita; HDI não lista endosso no AUTO) | 70 | 25 | 85 | **40** | poucas seguradoras, onboarding |
| D4 | Robô de endosso no portal | 70 | 20 | 25 | **20** | |

### E. Usar o Agger como ponte
| # | ideia | V | Vi | E | **nota** | por quê |
|---|---|---|---|---|---|---|
| E1 | Multicálculo pelo Agger (o que a 129-B/C já faz) | 95 | 95 | 80 | **90** | provado |
| E2 | Extensão "Ver na seguradora" para a **pessoa** transmitir (= B1) | 80 | 90 | 85 | **82** | |
| E3 | **Parceria/API oficial com a Dimensa** (Agger + InfoCap + Quiver): pedir acesso por API a cálculo, sincronização e Corp | 90 | 40 | 95 | **65** | estabilidade máxima e multi-corretora; prazo comercial |
| E4 | Ler a **Sincronização** (`cor/documentos`, `getProposal`, `getExtract`, `getParcelasPendentes`) para saber "foi emitida?" e pegar o PDF da apólice | 65 | 45 | 75 | **55** | os robôs são do Agger (mantidos por eles) — mas módulo não medido, `enviarRequisicao` é escrita (D-MC-28) e a InfoCap já dá apólice/anexos |
| E5 | Pegar as **senhas das seguradoras** do Agger para robôs nossos | 60 | 10 | 10 | **5** | 🔴 proibido: segredo fora do Vault, viola a regra "senhas nunca chegam ao Python" |

## 7. RECOMENDAÇÃO (ordem)
1. **Agora, sem código:** (a) e-mail à HDI pedindo acesso de parceiro às APIs (efetivação + parcelas/boleto) — vale para todas as
   corretoras do produto; (b) perguntar à InfoCap/Dimensa se existe integração Aggilizador→Corp e acesso por API à Sincronização;
   (c) o Founder conferir, no login dele no Agger, se o menu **Sincronizações** aparece e quais seguradoras estão ativas (1 tela, nenhuma escrita).
2. **Próxima SPEC de portais:** A1 (sessão persistente + login assistido + canário) e C1 (InCorp) — ambas reaproveitam peças existentes.
3. **Transmissão:** B1 já (fluxo humano de 1 clique com Approval); B2 só depois de A2 trazer a credencial da HDI.
4. **Nunca:** E5, A6, B3 sem API oficial.

## 8. Referências externas (o que modelamos, o que rejeitamos)
1. https://developers.hdi.com.br/llms.txt (índice das APIs HDI) · modela: API oficial de efetivação/parcelas/boleto · rejeita: nada · juiz: abrir o índice e conferir "Efetivação" e "Impressão da 2ª Via do Boleto".
2. https://www.bradescoseguros.com.br/portalapis/Portal/dist/API-ParcelasEmAberto.json e `.../API-ParcelasPorApolice.json` · modela: parcelas por API · rejeita: robô contra Akamai · juiz: baixar o JSON (📊 10.462 e 11.709 bytes em 11/10).
3. https://dev.portoseguro.com.br/api-portal/content/autorizacao · Porto exige APP + aprovação + **acordo** para produção.
4. https://developers.sompo.com.br/api-portal/content/nossas-apis-0 · Sompo: Financeiro (status de pagamento), Apólices, Sinistros.
5. https://chromewebstore.google.com/detail/aggilizador/ebmkefigmmcbigompbbacndedlapmdcc · a extensão do Agger (~20 mil usuários, v1.0.7.97 de 02/09/2026) · modela: deep link para o humano · rejeita: receber senha em claro.
6. https://revistaapolice.com.br/2024/01/focada-em-expandir-sua-receita-agger-adquire-infocap · Agger compra a InfoCap (09/01/2024).
7. https://exame.com/invest/mercados/dimensa-da-totvs-tots3-conclui-compra-agger-e-amplia-presenca-no-setor-de-seguros · Dimensa conclui a compra do Agger (R$ 260 mi; sinergia com Quiver).
8. https://legismap.com.br/conteudos/artigos-e-noticias/dimensa-empresa-da-evertec-lanca-o-one-plataforma-em-nuvem-para-gestao-e-cotacao-de-seguros-em-pequenas-e-medias-corretoras · ONE = gestão + multicálculo + sincronização.
9. https://cqcs.com.br/noticia/veja-quem-pode-ser-uma-spoc-no-mercado-de-seguros/ · SPOC: S.A., PL ≥ R$ 1 mi; corretora pode ser.
10. https://legismap.com.br/conteudos/artigos-e-noticias/retrospectiva-do-open-insurance-em-2025-o-ano-em-que-a-susep-consolidou-o-aprimoramento-continuo-do-ecossistema-de-dados-abertos · Res. SUSEP 61/2025 e o GT de revisão.
11. https://www.infomoney.com.br/minhas-financas/open-insurance-tem-fases-adiadas-e-travas-com-bancos-quando-o-mercado-de-seguros-aberto-comeca/ · fases e SPOC.
12. Padrões técnicos (não reabertos nesta sessão): https://playwright.dev/docs/auth (sessão salva) · https://datatracker.ietf.org/doc/html/rfc6238 (TOTP) · https://github.com/alufers/mitmproxy2swagger (HAR → OpenAPI).

## 9. O que NÃO foi medido (e por quê)
- A lista de seguradoras por tipo de sincronização (`app/seguradoraStatus/`) e se as contas têm o módulo — exige login (proibido nesta tarefa).
- Qual id (19/24) o "Ver na seguradora" exclui — ambíguo no código.
- O catálogo completo de Porto, Zurich, Tokio e Bradesco — os portais exigem cadastro.
- Se a escrita InCorp/`POST /negocio` da CorpAPI funciona com o perfil das corretoras — escrita não feita.
- Os arquivos do bundle ficam só no rascunho (`scratchpad/aggnow/`, `scratchpad/aggjs/`); nada foi para o repositório.
