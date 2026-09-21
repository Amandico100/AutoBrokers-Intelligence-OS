# TAREFAS DO FOUNDER — a lista única para validar as EXTRA-001.1 → 001.10

> **Escrito em 20/09/2026.** É esta a lista que vale. Ela substitui a lista antiga do §6/§7 e junta,
> sem repetir, tudo o que saiu das "Caixas do Founder" dos nove relatórios, do roteiro de canário e
> das pendências abertas.
>
> **Como ler:** cada tarefa tem o que é, **onde se faz**, o comando pronto para copiar (quando há),
> o que esperar, o que anotar se não bater, e a SPEC que ela valida. `[ ]` é para você marcar.
>
> **A ordem importa** — ela foi montada para você trocar de tela o mínimo possível: um Implantar só,
> um pareamento só, todas as variáveis de uma vez.
>
> 🔴 **Nada aqui exige terminal**, com uma exceção declarada (o bloco E, que é um `curl` no console
> do serviço). Para o piloto, o caminho recomendado é **pedir no chat** — está explicado lá.

**Onde as coisas ficam:**

| apelido | o que é |
|---|---|
| **painel** | o produto: `https://autobrokers-intelligence-os-autobrokers-smith-web.golhpm.easypanel.host` |
| **EasyPanel** | onde se clica Implantar e se editam as variáveis (Environment) |
| **console do serviço** | a aba Console do serviço dentro do EasyPanel |
| **smith-api** | o cérebro. O **smith-worker** usa **o mesmo bloco de variáveis** que ele |
| **smith-web** | as telas |
| **portal-worker** | o robô que abre portal de seguradora. Tem bloco **próprio**, pequeno |

---

## 0 · Antes de tudo — segurança e ambiente

### 0.1 As variáveis de ambiente, todas numa sentada

**Onde:** EasyPanel → `smith-api` → Environment (e, onde indicado, `smith-web` / `portal-worker`).
**Faça as três edições e só então clique Implantar uma vez** (tarefa 0.2).

📊 Conferido em 20/09/2026 pelo **nome**, contra o seu arquivo de credenciais e contra o código que lê cada uma.
Nenhum valor foi lido, impresso ou guardado.

| variável | serviço | está? | o que fazer | o que trava se esquecer |
|---|---|---|---|---|
| **`ADMIN_API_KEY`** | smith-api **e** smith-web | ✅ nos dois | nada | é **esta** que vale como "chave interna": o código aceita `BACKEND_INTERNAL_API_KEY` **ou** `ADMIN_API_KEY`, nesta ordem (`app/core/auth.py`). Sem ela o painel inteiro dá 401 |
| `BACKEND_INTERNAL_API_KEY` | smith-api / smith-web | ❌ ausente nos dois | **nada a fazer** — é o nome alternativo da mesma chave, e o `ADMIN_API_KEY` já cobre | — |
| **`ATTENDANT_INBOUND_ALLOWLIST`** | smith-api | ⚠️ **existe e está VAZIA** | **vazia é o certo para o piloto de verdade.** Preencha **só** para o ensaio de canário (bloco A/C), com o número do aparelho de teste — e **esvazie antes dos 3 dias** | preenchida no piloto = todo segurado fora da lista é ignorado **em silêncio**, e os 3 dias medem o vazio |
| **`JANELA_SILENCIO_EXCECOES`** | smith-api | ⚠️ **2 itens, e 1 deles NÃO é número de teste** | 🔴 **tire esse item.** 📊 conferido pelo **motor** do produto (`_variantes_do_telefone`), que casa com/sem `55` e com/sem o nono dígito — não por comparação de texto | esse número fica **fora** da janela de silêncio: o robô fala por cima da atendente naquela conversa, e de fora não há sintoma nenhum |
| `BILLING_CANARIO_ALLOWLIST` | smith-api | ✅ 2 itens | nada — o canário do bloco E exige **≥ 2** e recusa com 409 abaixo disso | bloco E não roda |
| `CANARIO_TESTE_B` | smith-api | ✅ 1 item, dentro da allowlist acima | nada | bloco E recusa com 409 |
| **`RESUMO_DIARIO_HORA`** | smith-api | ❌ ausente | opcional. Ausente = **19h**, no fuso da **plataforma**, não de cada corretora | se você quiser o resumo em outra hora, é aqui. Bloco B.5 |
| **`RESUMO_DIARIO_ATIVO`** | smith-api | ❌ ausente | opcional. Ausente = **ligado** | pôr `false` desliga o resumo das 19h |
| **`PRESENCA_DIGITANDO_LIGADA`** | smith-api | ❌ ausente | 🔴 **ponha `true`** se quiser rodar o caso A.8 | ausente = `false` no código (`app/core/config.py:110`): o "digitando…" **nunca aparece**, e o caso A.8 não tem como passar |
| `GLOBAL_KNOWLEDGE_COMPANY_ID` | smith-api | ✅ preenchida (identificador, 36 caracteres) | nada | é o "dono" da base de conhecimento global; sem ela a base cai num nome padrão e a destilação escreve no lugar errado |
| `POLICY_INTELLIGENCE_V2` | smith-api | ✅ **ligada** | nada | desligada = a Skill de apólice não roda e o canário da 001.5 mede o comportamento antigo. ⚠️ P-E0017-08: se você trocar o valor, use **`true`** e não `sim` — há um ponto do código que não aceita `sim` |
| `INSURER_DISPATCH_LIVE` | smith-api | ✅ **ligada** | nada | é o portão de **enviar mensagem à seguradora**. Ligada = o bloco C manda mensagem de verdade — por isso o bloco C só roda na sessão do canário |
| `DISPATCH_FINALIZE_MODE` | smith-api | ✅ `live` (4 caracteres) | nada | é o modo de **terminar** o chamado. Não é o mesmo portão do de cima: um diz "posso falar", o outro diz "o chamado abre de verdade ou cancela no fim" |
| **`DISPATCH_FINALIZE_MODE`** + **`DISPATCH_FINALIZE_LIVE_PLAYBOOKS`** | smith-api | 🔴 **corrigido em 20/09** | 📊 lido no código (`insurer_dispatch_service.py:349-380`): com `DISPATCH_FINALIZE_MODE=live` **TODOS os corredores abrem chamado de verdade** e a lista é **ignorada**. A lista só vale em `test`. **Para os seus testes (nenhum chamado real):** `DISPATCH_FINALIZE_MODE=test` e **apague** `DISPATCH_FINALIZE_LIVE_PLAYBOOKS`. **Para produção:** `DISPATCH_FINALIZE_MODE=live` (a lista pode ficar apagada). Confira no `/health`: `finalize_abre_de_verdade` | em `live` um teste seu despacha prestador de verdade |
| `ACIONAMENTO_FREIO_DE_EMERGENCIA` | smith-api | ❌ ausente | ausente = **freio solto** (certo). É a sua parada de emergência: pôr `true` derruba todo acionamento numa linha | guarde o nome. Num incidente é isso que você digita |
| `PORTAL_REAL_ENABLED` | **portal-worker** | ✅ ligada (só existe no bloco do portal-worker) | nada | desligada = o portal não abre; o bloco E.3 falha inteiro |
| `PORTAL_EFEITO_MATERIAL_LIBERADO` | smith-api **e** portal-worker | ✅ ligada nos dois | nada | é o que permite o portal **fazer** algo, não só olhar |
| **`GLOBAL_KILL_SWITCH`** | smith-web | ⚠️ **ligada** (= bloqueando) | 🔴 **deixe como está.** Hoje ela **não bloqueia o atendimento**: o único lugar que a lê é `lib/security/production-gates.ts`, usado por **uma** rota de diagnóstico (`/api/admin/security/production-gates`). Ela relata, não impede | nada trava por causa dela hoje. ⚠️ Mas o nome promete mais do que ela faz — não conte com ela como freio |
| `GLOBAL_KILL_SWITCH` | portal-worker | ✅ desligada | nada | — |
| **`ENVIRONMENT` × `ENV`** | smith-api | ✅ as duas, **com valores diferentes** | 🔴 **alinhe as duas** para o mesmo valor de produção | o backend lê **`ENV`** (`app/main.py:16`) e só para o Sentry: com `ENV` ≠ produção, os erros do ar chegam etiquetados como se fossem de desenvolvimento e a amostragem de rastro fica em 100% (mais custo). Nenhum comportamento do produto muda. `ENVIRONMENT` não é lido por nenhuma linha do backend |
| `BACKEND_URL` / `NEXT_PUBLIC_API_URL` | smith-api / smith-web | ✅ os dois apontam para o smith-api | nada | a tela abre e os blocos vêm vazios |

- [ ] **0.1.a** Tirar o item estranho de `JANELA_SILENCIO_EXCECOES` (smith-api → Environment) · **001.7**
- [ ] **0.1.b** Alinhar `ENV` e `ENVIRONMENT` (smith-api) · **001.7**
- [ ] **0.1.c** Acrescentar `PRESENCA_DIGITANDO_LIGADA=true` (smith-api), se quiser o caso A.8 · **001.2**
- [ ] **0.1.d** Conferir que `ATTENDANT_INBOUND_ALLOWLIST` está **vazia** (e só preencher no ensaio) · **001.2 / 001.7**

### 0.2 O Implantar único

- [ ] **0.2** Clicar **Implantar** em **`smith-api`**, **`smith-worker`** e **`smith-web`**, nesta ordem · **todas**

**Onde:** EasyPanel, um clique em cada serviço.
**O que esperar:** cada um volta a verde em 2–5 min.
**Por que agora:** é o único Implantar de toda esta lista. Ele sobe, de uma vez, o chat da 001.1, a
pausa e a reentrada da 001.4, o vocabulário da 001.5.2, a fila com o selo do conferente, os quatro
modelos do grupo, e a contagem das exceções do silêncio que o checklist da 001.7 precisa ler
(P-E0017-02).
**O que anotar se não bater:** se o serviço não voltar verde, copie as últimas 20 linhas do log.

⚠️ **Estar na `main` não é estar no ar.** Enquanto não clicar, o produto roda o código de ontem.

- [ ] **0.3** Abrir o chat do painel e mandar um "oi" · **001.1**
      **O que esperar:** resposta em segundos. É a prova de que o Implantar pegou.

### 0.4 As credenciais e as chaves — quando conveniente, antes de ter cliente pagante

- [ ] **0.4.a** ✅ **já feito** — o arquivo `CREDENCIAIS EASYPANEL.txt` **não está mais dentro da pasta do
      projeto**. 📊 conferido em 20/09: não há nenhum arquivo com esse nome na árvore do repositório.
      Mantenha-o fora. **Metade de P-PILOTO-09 fechada.** · **higiene**

- [ ] **0.4.b** **Rotacionar (trocar) as chaves que já foram coladas em chat.** Não é urgência de hoje;
      é uma tarde de trabalho antes de existir cliente pagando. A ordem abaixo é por **gravidade**:
      primeiro o que dá acesso a **todos os dados**, depois o que **gasta dinheiro**, depois o resto.

| ordem | variáveis (por nome) | onde se troca | por que nesta posição |
|---|---|---|---|
| 1 | `SUPABASE_SERVICE_ROLE_KEY` · `SUPABASE_SERVICE_KEY` · `SUPABASE_KEY` · `SUPABASE_ANON_KEY` · `NEXT_PUBLIC_SUPABASE_ANON_KEY` · `SUPABASE_DB_URL` | supabase.com → seu projeto → Project Settings → **API keys** (e **Database** para a senha do `SUPABASE_DB_URL`) | a service role **passa por cima de toda a separação entre corretoras**. É a chave que lê tudo de todo mundo |
| 2 | `ADMIN_API_KEY` · `ADMIN_TOKEN` · `SESSION_SECRET` · `APP_SECRET` · `SECRET_KEY` · `REVIEW_ENGINE_LINK_SECRET` | **você mesmo gera** (qualquer gerador de senha longa) e cola nos **dois** blocos, smith-api e smith-web | é o "sou o painel" do produto inteiro. Quem tem ela fala com a API como se fosse você |
| 3 | `ENCRYPTION_KEY` · `PORTAL_VAULT_KEY` | idem | 🔴 **não troque sem falar comigo antes**: são elas que abrem as senhas de portal já guardadas. Trocar sem re-criptografar deixa as credenciais das seguradoras ilegíveis |
| 4 | `ANTHROPIC_API_KEY` · `CLAUDE_API_KEY` | console.anthropic.com → **API keys** | gasta dinheiro seu |
| 5 | `OPENAI_API_KEY` | platform.openai.com → **API keys** | idem |
| 6 | `GOOGLE_API_KEY` · `GEMINI_API_KEY` · `GOOGLE_PLACES_API_KEY` | Google AI Studio (Gemini) e Google Cloud Console → Credentials (Places) | idem |
| 7 | `CORP_INFOCAP_RESULTA_PASSWORD` · `CORP_INFOCAP_AUTOFLEET_PASSWORD` | no próprio **InfoCap**, trocando a senha do usuário | dá acesso à carteira real das corretoras |
| 8 | `EVOLUTION_API_KEY` · `EVOLUTION_GO_GLOBAL_KEY` · `EVOLUTION_GO_INSTANCE_TOKEN` · `GLOBAL_API_KEY` (bloco do Evolution) | painel do serviço Evolution no EasyPanel → Environment (trocar e reimplantar o Evolution) | quem tem ela **manda mensagem pelo WhatsApp da corretora** |
| 9 | `REDIS_URL` (a senha vai embutida na URL) | EasyPanel → serviço do **Redis** → trocar a senha e atualizar a URL nos três blocos | fila, travas e cache |
| 10 | `MINIO_ROOT_USER` · `MINIO_ROOT_PASSWORD` · `MINIO_BACKUP_S3_ACCESS_KEY_ID` · `MINIO_BACKUP_S3_SECRET_ACCESS_KEY` | EasyPanel → serviço **minio** (e, no backup, no painel do provedor S3) | os documentos e apólices guardados |
| 11 | `TWILIO_ACCOUNT_SID` · `TWILIO_AUTH_TOKEN` | console.twilio.com → Account → **API keys & tokens** | telefonia; gasta dinheiro |
| 12 | `ELEVENLABS_API_KEY` · `DEEPGRAM_API_KEY` | elevenlabs.io → Profile → API key · console.deepgram.com → API keys | voz; gasta dinheiro |
| 13 | `N8N_API_KEY` · `BROWSERBASE_API_KEY` (+ `BROWSERBASE_PROJECT_ID`) | painel do n8n → Settings → API · browserbase.com → Settings | automações e navegador remoto |
| 14 | `GOOGLE_OAUTH_CLIENT_SECRET` · `NOTION_OAUTH_CLIENT_SECRET` | Google Cloud Console → Credentials → OAuth client · notion.so/my-integrations | login de terceiros |
| 15 | `DOCLING_SERVICE_KEY` · `TAVILY_API_KEY` · `FIRECRAWL_API_KEY` · `STRIPE_SECRET_KEY` · `STRIPE_WEBHOOK_SECRET` | cada painel próprio | menor exposição / pouco ou nada em uso |

📊 **Estão vazias hoje** (nada a trocar): `OPENROUTER_API_KEY`, `GROQ_API_KEY`, `QDRANT_API_KEY`,
`SENDGRID_API_KEY`, `SENDGRID_FROM_EMAIL`, `LANGCHAIN_API_KEY`, `LANGSMITH_API_KEY`,
`LANGSMITH_WORKSPACE_ID`, `ZAPI_INSTANCE_ID`, `ZAPI_TOKEN`, `ZAPI_CLIENT_TOKEN`, e `SENTRY_DSN` no smith-web.

**Depois de trocar qualquer uma: Implantar o serviço.** Variável nova só vale depois do Implantar.

---

## 1 · Preparar o ensaio — pré-requisitos

- [ ] **1.1 Reativar o grupo de suporte de cada corretora do piloto** · **001.3 / 001.7** 🔴
      **O que é:** o grupo de WhatsApp para onde o agente manda o 🆘 quando precisa de gente.
      **Onde:** painel → troque para a corretora no topo → **Personalização → Suporte humano**.
      **O que fazer:** reative (ou recadastre) o grupo da equipe, **em cada corretora**, marcado como principal.
      **O que esperar:** o destino aparece ativo.
      **O que anotar:** 📊 20/09: as duas corretoras do piloto têm 1 destino cada, **ambos desativados
      desde 10/09** (P-E0017-01). E confira que o grupo de cada corretora está **dentro dela** — o da
      AutoFleet tinha nascido dentro da Resulta (P-PILOTO-10). Se estiver no lugar errado, apague a
      linha e recrie depois de trocar de corretora no topo.
      ⚠️ O sinal de saúde do sistema **não** mostra esse defeito: ele só olha corretora com o agente já ligado.

- [ ] **1.2 Criar o grupo de canário** — um grupo de WhatsApp só com você — e cadastrá-lo como destino
      de suporte da corretora de ensaio · **001.3**
      **Onde:** WhatsApp para criar; painel → Personalização → Suporte humano para cadastrar.

- [ ] **1.3 Cadastrar o número do seu celular como "número da casa"** da corretora de ensaio · **001.3**
      **Onde:** painel → Personalização (números da equipe/casa).
      **Para que:** o caso B.3 prova que o agente **não responde** a quem é da casa.

- [ ] **1.4 Parear o celular pessoal** como atendente · **001.2 / 001.4**
      **Onde:** painel → conexão de WhatsApp → ler o QR.
      🔴 **Antes de parear**, se for fazer o ensaio de canário, ponha o número do aparelho de teste em
      `ATTENDANT_INBOUND_ALLOWLIST` (tarefa 0.1.c/0.1.d) — senão o teste mede o vazio.
      **Ao terminar tudo, desparear** (seção "Depois de tudo").

- [ ] **1.5 Deixar o agente de atendimento DESLIGADO** nas corretoras até o bloco A · **001.2**
      **Onde:** painel → botão **Ligar agente**. Desligado, ele só observa.

- [ ] **1.6 Saber onde o teste de apólice roda** · **001.1 / 001.6**
      ⚠️ A InfoCap tem um bloqueio conhecido (F-094-07): duas corretoras descriptografam para a **mesma
      conta**, e o adaptador recusa a segunda. Por isso os testes de **apólice** (bloco D) e de
      **cobrança** (bloco E) ficam na **Resulta**, só leitura ou envio ao seu número.

---

## 2 · Bloco D — a apólice certa, no chat do painel (001.1)

**Onde:** painel da **Resulta**, chat `core`, com a sua conta. Nada sai por WhatsApp.
**Anote cada um como:** ✅ passou · ⚠️ passou mas o texto ficou estranho · ❌ falhou (cole a resposta).

- [ ] **D.1** CPF do cliente que em 09/09 recebeu 4 apólices → **uma** rodada, **zero** vencidas, diz
      **por que** é aquela e avisa que há histórico oculto · **001.1**
- [ ] **D.2** *"quais as coberturas da apólice residencial dele?"* (a HDI) → coberturas **com a origem
      por linha**, Assistências Essenciais com origem no documento, franquia certa · **001.1**
- [ ] **D.3** CPF só com apólices vencidas → a frase de "sem vigente", **com a data** · **001.1**
- [ ] **D.4** CPF com duas vigentes do mesmo ramo → pergunta **uma vez**, mostrando as duas · **001.1**
- [ ] **D.5** a pergunta que em 10/09 devolveu *"ainda não recebi uma pergunta sua"* → agora responde · **001.1**
- [ ] **D.6** 🔴 **controle:** *"quantos clientes eu tenho?"* → a ferramenta de apólice **não** é chamada · **001.1**
- [ ] **D.7** o caso do Rafael (residencial Allianz): prêmios, franquias, coberturas → **da vigente**,
      com origem por linha · **001.1**

---

## 3 · Bloco D2 — a base de planos responde (001.5 e 001.5.2)

**Onde:** mesmo chat `core`, e o WhatsApp do aparelho de teste.
📊 A base já está publicada: **492 serviços, 108 planos, 8 seguradoras**. Não há mais fila para curar.

- [ ] **D2.0 Abrir `Painel → Personalização → Conhecimento`** · **001.5**
      **O que esperar:** o bloco **Cobertura dos planos** com 8 seguradoras e 20 combinações publicadas;
      a **Fila de curadoria** com **8 linhas e só elas** (táxi da Azul, retidas de propósito).
      **O que anotar:** se aparecer nome de tabela, de coluna, SQL ou chave técnica na tela, é defeito — me avise.
      Se a fila tiver **mais** de 8 linhas, me avise.
- [ ] **D2.1 Trocar de corretora e voltar** → os números têm de ser **os mesmos**, e a tela diz numa linha
      por quê (a base é global, de propósito) · **001.5**
- [ ] **D2.2** Com **uma apólice real de cada seguradora**, pergunte no chat e no WhatsApp: · **001.5.2**
      ```
      meu seguro cobre guincho? até quantos km?
      tenho carro reserva?
      cobre chaveiro?
      cobre vidraceiro?          (numa apólice residencial)
      ```
      **O que esperar:** sim ou não **com o limite** (km, diárias, R$ por evento). No chat vem também o
      documento e a página; no WhatsApp, a mesma verdade sem citação.
      A tabela de comparação, seguradora por seguradora, está em
      `reports/SPEC-EXTRA-001.5-CANARIO-PASSO-A-PASSO.md` §B.
- [ ] **D2.3 🔴 O que anotar se vier "ainda não sei"** com uma apólice que **tem** plano: copie e cole
      **exatamente** como o nome do plano aparece na apólice, mais a seguradora. É a pendência
      P-E00152-07, e só apólice real mede. · **001.5.2**
      **Não é defeito:** Mapfre auto dizer "ainda não sei" (falta o manual no acervo) · Allianz não
      responder por moto/caminhão/frota · Bradesco condomínio quase vazio · seguradora sem documento.
- [ ] **D2.4 🔴 controle:** *"quantas parcelas faltam para o segurado tal?"* → responde sobre parcelas e
      **não** consulta a base de planos · **001.5**
- [ ] **D2.5** A validação com a Saionara e a Regina (20 min), com estas perguntas: · **001.5**
      ```
      dá para conferir de onde veio a resposta? você abriria o documento na página citada?
      "ainda não sabemos" soa honesto, ou soa que o sistema falhou?
      o gancho do plano superior soa útil, ou soa empurrão de venda?
      ```

---

## 4 · Bloco A — a conversa no WhatsApp (001.2)

**Onde:** WhatsApp do aparelho de teste (TESTE-A) escrevendo para a corretora de ensaio.
**Pré-requisito:** ligar o agente **só** para o ensaio. Ao fim do bloco, desligue de novo.

- [ ] **A.1** cinco mensagens + 1 foto em 12 segundos → **um** turno, **uma** resposta, foto reconhecida · **001.2**
- [ ] **A.2** mandar só o CPF → resposta em ~3 s · **001.2**
- [ ] **A.3** *"o carro parou na"* → esperar 15 s → *"marginal pinheiros"* → **um** turno · **001.2**
- [ ] **A.4** mandar mensagem **enquanto** ele responde → nunca perde nem duplica · **001.2**
- [ ] **A.5** encerrar, voltar dentro da janela, depois puxar assunto novo → **sem** reapresentação na
      janela; **uma** apresentação no assunto novo · **001.2**
- [ ] **A.6** trocar o nome do agente no meio do assunto, e tentar um nome **igual ao de um membro** →
      nada muda no assunto em curso; o nome colidente é **recusado** · **001.2**
- [ ] **A.7** responder pelo **celular pareado**, como atendente → o agente **cala**, o silêncio aparece
      no feed **com o motivo**, e nada é gravado em dobro · **001.2**
- [ ] **A.8** repetir o caso A.3 com `PRESENCA_DIGITANDO_LIGADA=true` → o "digitando…" **aparece e some** · **001.2**
      ⚠️ sem a variável (tarefa 0.1.c) este caso não tem como passar.

---

## 5 · Bloco B — o grupo da equipe (001.3)

**Onde:** painel da corretora de ensaio + o grupo de canário (tarefa 1.2).

- [ ] **B.1** conversa nova em que o agente **pede ajuda** → **um único** balão 🆘, com WhatsApp clicável · **001.3**
- [ ] **B.2** responder pelo painel e provocar um novo alerta → **nada** chega ao grupo · **001.3**
- [ ] **B.3** mandar mensagem do **número da casa** (tarefa 1.3) → o agente **não responde**, nada entra
      na fila, nada vai ao grupo · **001.3**
- [ ] **B.4** concluir um caso → ✅ curto no grupo · **001.3**
- [ ] **B.5** esperar as **19h** (ou a hora de `RESUMO_DIARIO_HORA`) → 📊 com números que **batem** com o
      que aconteceu no dia · **001.3**
- [ ] **B.6** desativar o destino de suporte e tentar **ligar** o agente → recusa **com frase humana**;
      reativar → liga · **001.3**
- [ ] **B.7** com um usuário `member`, tentar mexer em destino, credencial ou conexão → **403** · **001.3**
- [ ] **B.8** 🔴 **controle:** conversa **sem** humano, com pedido de ajuda → o alerta **chega** · **001.3**

---

## 6 · Bloco C — o acionamento ao vivo (001.4)

🔴 **Só na sessão do canário**, na corretora de ensaio. `INSURER_DISPATCH_LIVE` está **ligada**: o que
sair daqui sai de verdade para a seguradora.

- [ ] **C.1** abrir um acionamento numa seguradora de **menu numerado**, ir até a confirmação e
      **RECUSAR** → o menu recebe o número certo; as telas entram no acervo · **001.4**
- [ ] **C.2** digitar **uma** vez à mão, pelo celular pareado, dentro da conversa com a URA → o robô
      **espera 15 s**, não manda nada ao grupo nem ao segurado, e **continua lendo** · **001.4**
- [ ] **C.3** digitar **duas** vezes em 15 s → o robô **sai em silêncio** e não volta · **001.4**
- [ ] **C.4** forçar uma tela que peça um dado **fora da ficha** → nada sai à URA; a pergunta chega ao
      TESTE-A; a resposta dele é usada; o histórico ganha `acionamento.dado_faltou` · **001.4**
- [ ] **C.5** ao fim do bloco, peça no chat: *"quantos eventos `agente.%` existem?"* → tem de **sair de
      zero**. (Se preferir o console do smith-api:
      `select event_type, count(*) from work_events where event_type like 'agente.%' group by 1`) · **001.4**

---

## 7 · Bloco E — a cobrança e os portais (001.6)

**Onde:** painel da **Resulta** (tela) + **console do serviço `smith-api`** (os dois comandos).
🔴 **Todo envio vai só para o seu número** — é o que `BILLING_CANARIO_ALLOWLIST` e `CANARIO_TESTE_B`
garantem; sem elas o comando recusa com **409** e não manda nada.

- [ ] **E.1 Preencher a tela do Auxiliar de cobrança** · **001.6**
      **Onde:** painel da Resulta → Rotinas → Auxiliar de cobrança.
      **O que preencher:** **"Quem assina"** (o nome que sai na mensagem) · modo **Encaminhar** ·
      WhatsApp da equipe = **o seu número** · antecedência **7 dias**.
      ⚠️ Sem "Quem assina" preenchido, o resto do bloco não vale.

- [ ] **E.2 Rodar o canário da cobrança** · **001.6**
      **Onde:** EasyPanel → `smith-api` → **Console**. Cole exatamente isto (a chave já existe no ambiente
      do serviço, por isso não há nada para preencher):
      ```bash
      curl -X POST "https://autobrokers-intelligence-os-autobrokers-smith-api.golhpm.easypanel.host/api/admin/canario/extra001?esperar_retorno_s=180" \
        -H "X-Internal-Key: $ADMIN_API_KEY"
      ```
      **O que esperar:** o comando fica até 3 minutos esperando uma resposta sua no WhatsApp, e devolve
      um JSON começando por `{"ok": true`. No seu WhatsApp: **uma** mensagem por segurado, com N boletos
      juntos, **nunca a mesma parcela duas vezes**; a pergunta Q4 pede que você responda — responda.
      **O que anotar se não bater:** `409 canário desarmado` = as variáveis do canário não estão como
      deviam (veja 0.1) · duas mensagens para o mesmo segurado, ou a mesma parcela repetida, cole o texto.

- [ ] **E.3 Rodar a parte dos portais** · **001.6**
      ```bash
      curl -X POST "https://autobrokers-intelligence-os-autobrokers-smith-api.golhpm.easypanel.host/api/admin/canario/extra001?portais=1" \
        -H "X-Internal-Key: $ADMIN_API_KEY"
      ```
      **O que esperar** (leva ~2 min): Tokio, HDI, Yelum e Zurich **abrem**, e cada portal diz **em
      português** por que não entrou, quando não entra. Allianz e Mapfre continuam esperando as senhas.
      **O que anotar:** qualquer mensagem de erro que não esteja em português de gente.

- [ ] **E.4 Só depois disto, reativar a rotina de cobrança** · **001.6**
      **Onde:** painel da Resulta → Rotinas → ligar o Auxiliar de cobrança.

---

## 8 · O piloto de 3 dias (001.7)

> ### 📖 Em linguagem de gente, antes de começar
>
> **"Ligar o agente"** é o botão **Ligar agente**, no painel, **em cada corretora**. É ele que faz o robô
> **responder os segurados no WhatsApp**. Com ele desligado, o sistema só **observa**: vê as conversas,
> guarda, não fala. Ligar é o que dá início ao piloto — e é a única coisa que muda o que o segurado vê.
>
> **"Canário"** é um **ensaio com um único celular de teste**, antes de soltar para clientes reais. No
> checklist, `--modo canario` quer dizer: *"nesta rodada, a lista de entrada estar preenchida só com o
> número de teste é o esperado"*. No piloto de verdade é o contrário — a lista tem de estar **vazia**,
> senão todo segurado que não estiver nela é ignorado em silêncio e os 3 dias medem o nada.
>
> **"Quando o agente errar"** é no **atendimento**: ele respondeu errado, ou respondeu fora de hora, a um
> segurado de verdade. 🔴 **Não desligue o agente.** A atendente **responde pelo celular naquela
> conversa** — isso cala o robô ali, só ali, na hora. Anote o que aconteceu. Isso **não** é erro da
> medição, e não invalida o piloto: é exatamente o tipo de coisa que o piloto existe para contar.
>
> **Quando termina:** depois de **3 dias úteis completos** com o agente ligado. No **4º dia** sai o
> veredito — e é uma coisa só, num chat novo (passo P4).
>
> **Você não precisa rodar nada no console.** O caminho recomendado é **pedir no chat**; eu rodo da
> minha máquina contra a produção, **só leitura**: nada envia mensagem, liga agente ou escreve no banco.

### P1 · Antes de ligar: o checklist

- [ ] **P1** Abra um chat e peça: · **001.7**
      ```
      rode o checklist de ligar
      ```
      **O que esperar:** **PODE LIGAR** ou **NÃO PODE LIGAR**, com uma linha por trava.
      🔴 O que ele não consegue conferir conta como **trava fechada** — de propósito.
      **As três travas conhecidas de 20/09 já são tarefas desta lista:** o destino de suporte (1.1), o
      Implantar (0.2) e as exceções do silêncio (0.1.a). Se você fez as três, ele deve vir verde.

      *Alternativa, no console do `smith-api`:*
      ```bash
      python scripts/conferir_o_que_esta_no_ar.py --ligar
      ```
      ⚠️ 📊 Em 20/09 este comando **quebrou no console** com `ModuleNotFoundError: portal_worker`. O
      conserto foi feito em 20/09 e entra no ar com **um novo Implantar do smith-api**. Até lá, use o chat.

      *Para um ensaio só com o aparelho de teste:* preencha `ATTENDANT_INBOUND_ALLOWLIST` com o número de
      teste, Implante, e peça *"rode o checklist de ligar em modo canário"*. 🔴 **Antes do piloto de
      verdade, esvazie a lista.**

- [ ] **P1.b** **Só com "PODE LIGAR" na tela**, clique **Ligar agente** no painel, **em cada corretora do
      piloto** · **001.7**

### P2 · Os 3 dias

- [ ] **P2** Deixar o agente ligado **3 dias úteis inteiros**, em cada corretora do piloto · **001.7**
      **Combine com a equipe uma coisa só:**
      ```
      quando o agente errar, NÃO desligue: assuma a conversa pelo celular
      (isso o cala naquela conversa) e anote o que ele fez de errado
      ```
      ⚠️ **Não há mais folha diária para preencher.** Isso mudou (decisão D-E0017-04): no 4º dia, um
      avaliador lê uma amostra das conversas e dá as três notas que o produto ainda não grava sozinho.
      Ninguém precisa preencher planilha durante o piloto.

### P3 · Durante (opcional)

- [ ] **P3** Se quiser acompanhar no meio do caminho, peça no chat: · **001.7**
      ```
      rode a medição do piloto de 01/10 a 02/10 e me mostre a tabela
      ```
      **O que esperar:** uma tabela por corretora, dia a dia — conversas atendidas, rajadas juntadas,
      acionamentos com protocolo, handoffs entregues, avisos ao grupo por tipo, silêncios por motivo — e
      embaixo a régua, com a nota de cada dimensão e o critério escrito ao lado.
      🔴 **Nenhum nome, telefone, placa ou apólice aparece: só contagem.**

      **O que NÃO é defeito:**
      ```
      "NÃO AVALIADA — amostra insuficiente" ..... com menos de 5 casos a nota seria chute
      "NÃO MENSURÁVEL" antes de 14/09 ........... antes disso o produto não marcava quem escreveu
      "NÃO LIDO" numa célula .................... a leitura falhou; peça de novo. Nunca vira zero
      a nota do bloco só sai com a maioria das dimensões avaliada ..... de propósito
      pedir até HOJE dá número que muda a cada hora ................... peça até ontem
      ```
      **O que anotar se não bater:** se a tabela disser **0 conversas** num dia em que você **viu** o
      agente responder, me diga **o dia e a corretora** (não precisa do nome do segurado).

      *Alternativa, no console do `smith-api`:*
      ```bash
      python scripts/medir_o_piloto.py --de 2026-10-01 --ate 2026-10-02 --formato markdown
      ```
      (troque as duas datas. ⚠️ Em breve, sem argumento nenhum, ele passa a cobrir os **últimos 7 dias
      fechados** e nem isso será preciso.)

### P4 · O veredito, no 4º dia

- [ ] **P4** Abrir um **chat novo** e colar o prompt inteiro de
      **`docs/canon/PROMPT-VEREDITO-DO-PILOTO.md`** (troque só as duas datas na primeira linha) · **001.7**
      **O que ele faz, sozinho:** roda o checklist, roda a medição dos 3 dias, lê uma **amostra** das
      conversas do piloto e dá as três notas que o produto não grava (*fala como humano* · *sabe calar* ·
      *apólice certa de primeira*), e responde **PASSOU** ou **NÃO PASSOU**, com o porquê.
      **Os cortes** (proposta minha, decisão D-E0017-03 é sua):
      ```
      · nada medido abaixo do palpite de 12/09
      · "aciona" .............. pelo menos 5 casos E nota ≥ 70
      · "sabe pedir ajuda" .... ≥ 90   (pedido de ajuda que ninguém recebe é o pior defeito possível)
      · apólice errada ........ no máximo 1 em cada 10
      ```

---

## 8.5 · Bloco F — o portal de vidros (001.10)

> **O que mudou:** o robô aprendeu a abrir o pedido de vidro **em qualquer uma das 38 seguradoras** que o portal
> publica (antes eram 3, e nenhuma delas era a Yelum — 📊 o motor antigo escrevia **zero** nas capturas reais), e
> aprendeu a **ler o desfecho que o portal decidiu**: loja já escolhida, agenda com lojas e horários, analista ou
> vistoria. Ele devolve ao segurado o número do atendimento, a franquia e o próximo passo.
>
> 🔴 **Nada disso está ligado.** Tudo mora atrás de uma chave que nasce desligada: `PORTAL_VIDROS_API_FIRST`.
> O que atende hoje continua sendo o caminho antigo. Implantar **não muda nada** no ar — e é de propósito.

- [ ] **F.1 Implantar**, nesta ordem: `smith-api` → `smith-worker` → `portal-worker`.
      **O que esperar:** os três voltam verdes e o produto continua exatamente como estava. · **001.10**
- [ ] **F.2 O canário** (é o que falta para dar o passo seguinte). Um acionamento de **lataria na Yelum**, com
      **apólice e veículo de teste** — nunca de cliente. Antes dele, em `portal-worker` → Environment:
      ```
      PORTAL_CANARIO_ALLOWLIST = <o id do job do ensaio>
      PORTAL_VIDROS_API_FIRST  = true
      ```
      **O que esperar na tela:** o segurado (você, no número de teste) recebe o número do atendimento, a franquia
      e o próximo passo em português. **Se der errado:** a mensagem diz o número primeiro e **não promete** que o
      robô continua — é assim de propósito, porque hoje ele não consegue retomar. **Ao terminar:** volte
      `PORTAL_VIDROS_API_FIRST` para `false`. · **001.10 · D-E00110-F2**
      ⚠️ A allowlist **só estreita**: vazia = comportamento de hoje; escrita errada = **barra tudo** (é o certo).
- [ ] **F.3 As capturas que faltam** — entregue o roteiro à atendente da corretora:
      `docs/canon/guias/ROTEIRO-DE-CAPTURA-PORTAL-DE-VIDROS.md`, seção "O que ainda falta".
      **A nº 1 vale mais que todas as outras juntas:** um agendamento **levado até o fim** (escolher a loja, o dia,
      o horário e confirmar) na Yelum, com vidro de porta ou vigia. É ela que libera o robô a marcar hora. · **P-E00110-A1**
- [ ] **F.4 As 15 perguntas à atendente** — `docs/canon/guias/PERGUNTAS-PARA-A-ATENDENTE-PORTAL-DE-VIDROS.md`.
      A **nº 12** ("dá para retomar um atendimento parado, por número?") **decide sozinha** a próxima SPEC. · **P-E00110-A11**
- [ ] **F.5 Rotacionar as credenciais** que foram coladas no chat de novo em 20/09. · **P-PILOTO-09**

---

## 8.6 · Bloco G — uma corretora não trava a outra (001.8)

> **O que mudou:** o atendimento passou a dar **4 vagas por corretora**, em rodízio: uma corretora com cinquenta
> mensagens de uma vez, com o modelo lento ou com o portal travado **não atrasa mais a vizinha**, e nada se
> perde — o que não cabe agora espera e é respondido depois. O robô também ganhou **relógio** (nenhuma chamada ao
> modelo passa de 90 s, nenhum atendimento passa de 300 s) e, quando o provedor de inteligência cai, as
> conversas ficam **guardadas** em vez de virarem "tive uma falha técnica". E a Central de Agentes passou a
> mostrar tudo isso **por corretora**.
>
> 🔴 **Nada disso precisa de configuração:** todas as chaves novas têm valor padrão no código. Implantar já liga.
> A única coisa que nasce desligada é o **aviso ao dono da corretora** quando a fila cresce — e ela deve
> continuar desligada por enquanto (tarefa G.7).

- [ ] **G.1 Implantar**, nesta ordem: `smith-api` → `smith-web` (o `portal-worker` não muda).
      **O que esperar:** os dois voltam verdes e o atendimento continua se comportando como antes — o que muda
      só aparece sob carga. · **001.8**
- [ ] **G.2 Conferir o `/health`** do `smith-api` (é a única prova de que a parte nova está no ar).
      **O que esperar:** `scheduler` dizendo **`lider`** e `executor_threads` com um número (32 ou mais).
      **Se vier `seguidor` ou `desligado`:** há outro processo com o agendador ligado, ou `SCHEDULER_ENABLED`
      está `false`. · **001.8 · P-248**
- [ ] **G.3 Medir os núcleos do contêiner** — no **console do `smith-api`**, cole exatamente:
      ```
      python -c "import os; print(os.cpu_count(), min(32,(os.cpu_count() or 1)+4))"
      ```
      **O que esperar:** dois números (núcleos e o tamanho que o Python usaria sozinho). Se o segundo for menor
      que 32, não há nada a fazer — o produto já usa 32 como piso. É só para sabermos. · **001.8 · P-E0018-02**
- [ ] **G.4 Olhar "Mensagens perdidas" na Central de Agentes**, por corretora (painel → Central de Agentes).
      **O que esperar:** **zero**. É a resposta diária à pergunta *"perdi alguma mensagem hoje?"*, e agora ela
      aparece na corretora certa — antes o número de uma corretora podia cair na tela da outra. · **001.8**
- [ ] **G.5 🔴 O canário de isolamento** — é o que falta para esta entrega fechar. Precisa de **dois números de
      teste, cada um numa corretora de teste diferente** (na mesma corretora o ensaio não prova nada). Os 6
      casos estão no relatório `reports/SPEC-EXTRA-001.8-EXECUTION-REPORT.md` §6: medir uma conversa normal ·
      travar a segunda corretora de propósito e medir a primeira ao mesmo tempo · ver a corretora travada ser
      atendida, lenta mas atendida · mandar 50 mensagens de uma vez e conferir que nenhuma se perdeu · derrubar
      o provedor da segunda corretora e ver que a primeira não sente · desligar tudo e conferir que o número
      voltou ao normal. · **001.8 · P-E0018-01**
- [ ] **G.6 Decidir se cria um serviço separado só para as tarefas automáticas** (mesma imagem, com
      `SCHEDULER_ENABLED=true`, e a API passando a `false`). É **capacidade**, não isolamento: o código já sai
      pronto e nada quebra se você não criar. · **001.8**
- [ ] **G.7 🔴 NÃO ligue `ISOLAMENTO_AVISO_AO_DONO`** (o aviso ao dono quando a fila cresce) antes de a
      pendência **P-E0018-09** ser consertada: hoje o aviso reserva a janela de 30 minutos **antes** de tentar
      enviar, então um envio que falha queima a janela e o dono fica sem aviso nenhum. Ausente = não avisa, que é
      o certo por enquanto. · **001.8 · P-E0018-09**

**Bloqueia alguma coisa?** Só a G.5: sem o canário, o isolamento fica provado apenas por teste. As outras não
bloqueiam nada.

---

## 9 · Depois de tudo — desfazer o ensaio

- [ ] **9.1** Desativar o destino do **grupo de canário** (painel → Personalização → Suporte humano) —
      deixando ativo o grupo **de verdade** da equipe · **001.3**
- [ ] **9.2** Apagar os **números da casa** que você cadastrou só para o teste · **001.3**
- [ ] **9.3** **Desparear** o celular pessoal · **001.2 / 001.4**
- [ ] **9.4** **Esvaziar** `ATTENDANT_INBOUND_ALLOWLIST`, se você a preencheu para o ensaio (smith-api →
      Environment → Implantar) · **001.2 / 001.7**
- [ ] **9.5** Cancelar as **intenções pendentes** que o ensaio deixou · **001.6**
- [ ] **9.6** Conferir que **nenhuma sessão de acionamento ficou ativa** — peça no chat: *"tem alguma
      sessão de acionamento aberta?"* · **001.4**

---

## 10 · Decisões suas em aberto

| # | a decisão | o que está em jogo | onde está registrada |
|---|---|---|---|
| 1 | **D-E0017-03 · os cortes do veredito do piloto** | são os quatro números do P4. Até você decidir, a régua publica as notas e **não** publica o veredito | `FOUNDER-DECISIONS.md` |
| 2 | **D-E0017-04 · os escritores que faltam entram antes dos 3 dias?** | 📊 três das seis notas do atendimento não têm como ser gravadas pelo produto hoje (P-E0017-03). **Já resolvido pela via do avaliador por amostra** (P4) — falta você dizer se concorda em rodar o piloto assim, ou se prefere adiar ~1 dia para construir os escritores | `FOUNDER-DECISIONS.md` · P-E0017-03 |
| 3 | **`write:true` tira a escrita de 2 pessoas** | 📊 `admin_company` 8 · `member` 2, e os dois `member` estão em corretoras diferentes. Eles param de poder mexer em destino de suporte, credencial de portal e conexão de WhatsApp | relatório 001.3, caixa #3 |
| 4 | **CPF/CNPJ aparece no 🆘 e no 🚨** e fica no histórico do grupo para sempre | a SPEC pediu assim. É decisão de privacidade, não técnica: você quer mesmo? | relatório 001.3, caixa #8 |
| 5 | **A hora do resumo diário** | 19h é o padrão, e é a variável `RESUMO_DIARIO_HORA`. ⚠️ hoje é o fuso da **plataforma**, não de cada corretora | relatório 001.3, caixa #4 |
| 6 | **Ler os quatro modelos de mensagem do grupo** e dizer o que cortaria | 💭 a copy é ilustrativa de propósito. Sem a sua leitura, a validação com a Saionara e a Regina não fecha | relatório 001.3, caixa #5 |
| 7 | **O canal do grupo** (P-E0014-06): ligar grupos na instância — 📊 240 mensagens/min a mais — **ou** botões AGENTE / EU CUIDO na Fila | hoje a atendente que responde **no grupo** não é ouvida; só vale o privado do número de suporte e dos números da casa | relatório 001.4, caixa |
| 8 | **O nome do agente da Resulta** | a SPEC entregou o mecanismo; o nome é seu | relatório 001.2 · P-E0012-D3 |
| 9 | **As senhas de Allianz e Mapfre** para os portais | sem elas o bloco E.3 continua com duas seguradoras de fora | relatório 001.6 |
| 10 | **Destilar as seguradoras que faltam** — a ordem pelo prêmio da carteira está em `providers/susep/fila-onda-3.json` (19 seguradoras) | a base cresce **sem código novo**; hoje 8 seguradoras respondem | relatório 001.5 / 001.5.1 |
| 11 | **D-E00110-F1 · o contato do segurado no portal** | hoje o portal recebe o telefone da corretora, marca `recebe WhatsApp = não` e a loja liga para a equipe. A recomendação (nota 88) é pôr **celular e e-mail do segurado**, mantendo a corretora como quem abriu. Só o canário prova que o portal aceita | `FOUNDER-DECISIONS.md` |
| 12 | **D-E00110-F2 · quando ligar `PORTAL_VIDROS_API_FIRST`** | ligar antes do canário abriria pedido real sem nenhuma prova ao vivo (nota 20). A recomendação é: **só depois do canário verde** (nota 95) | `FOUNDER-DECISIONS.md` |
| 13 | **D-E00110-F3 · a 001.10.1 (a continuação) entra antes da 001.8?** | sem continuação, **toda** parada depois do pedido aberto termina em mão humana. Recomendação 💭: sim (80); a 001.8 é isolamento entre corretoras (70), e sobe de prioridade quando entrar a 3ª corretora | `FOUNDER-DECISIONS.md` |

---

## Apêndice · O que o produto ainda não sabe medir sozinho

Não é tarefa sua — é para você saber o que **não** esperar do relatório do piloto (`PENDENCIAS.md`):

```
P-E0017-03  três dimensões do atendimento não têm escritor: "apólice certa em 1 rodada",
            "sabe calar" e "fala como humano". Por isso existe o avaliador por amostra do P4
P-E0017-04  o chat principal grava "success" em 100% das linhas — a coluna não consegue
            discordar. "Confiabilidade" e "completude" do chat saem NÃO AVALIADA
P-E0017-05  o aviso de caso parado conta VARREDURAS, não casos: o diário enche de ruído
P-E0017-06  o porteiro do botão "Ligar agente" libera quando não consegue conferir, e não
            avisa que não conferiu. O checklist do P1 NÃO herda esse defeito — o botão, sim
P-E0017-07  num dia de banco instável, o resumo das 19h pode dizer "sem acionamentos hoje"
            em vez de "não consegui ler o dia"
P-E0017-08  POLICY_INTELLIGENCE_V2 é lida em dois lugares com listas diferentes: use "true"
```
