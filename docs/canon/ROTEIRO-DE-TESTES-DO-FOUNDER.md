# ROTEIRO DE TESTES DO FOUNDER — tudo o que está atrasado, em poucas sessões

> **Escrito em 04/10/2026** sobre a `main` `a87b2e7` (a que está no ar). Ele junta, numa ordem só, os testes atrasados das
> SPECs 116 → 127 e das EXTRA-001.x que **ainda valem**. O inventário de cada teste (feito, atrasado, coberto, morreu, futuro)
> está em `reports/INVENTARIO-TESTES-DO-FOUNDER-2026-10-04.md`; a lista longa continua em `TAREFAS-DO-FOUNDER.md`, e cada
> T-NN de lá aponta para o passo daqui.
>
> **Como usar:** faça na ordem. Em cada passo, marque `✅` ou `❌` e anote a **hora** (é pela hora que eu acho a conversa no
> sistema). No que der ❌, copie a resposta do agente **sem CPF e sem nome** de segurado. No fim de cada sessão, mande no chat
> o bloco **"o que me mandar"** — eu confiro dentro do sistema (diário de decisões, ferramentas chamadas, pedidos do portal,
> mensagens) e devolvo o que passou e o que não passou.

## As sessões, de uma olhada

| # | sessão | onde | quanto tempo 💭 | testes |
|---|---|---|---|---|
| **P** | Preparar | EasyPanel + painel + SQL | 30 min | T-03 T-04 T-07 T-08 T-23 T-24 T-25 T-54 T-55 T-65 T-100 |
| **1** | Conversa 1 — você como o segurado | celular A → WhatsApp da corretora de ensaio | 60 min | T-26 T-28 T-29 T-30 T-34 T-35 T-36 T-40 T-43 T-51 T-60 T-67 T-69 T-84 T-86 T-87 T-93 T-94 |
| **V** | O canário do vidro (portal) | celular B (segurado) + celular A (parente) + o portal | 45 min | T-56 T-57 T-58 T-96 T-101 T-105 |
| **2** | Conversa 2 — o parente | celular B | 40 min | T-36 T-62 T-88 T-93 T-94 T-95 T-96 |
| **1b** | Conversa 1, 2ª parte | celular A + painel | 20 min | T-31 T-32 T-33 T-37 T-47 T-61 T-85 T-89 T-90 |
| **C** | Chat principal | painel, chat `core` | 40 min | T-09 a T-21 T-38 T-43 T-53 T-66 T-70 |
| **S** | O bloco de SQL + o resumo das 19h | Supabase → SQL Editor + o grupo | 10 min | T-52 T-64 (e a conferência de todos) |
| **F** | Desfazer | celular A + EasyPanel + chat | 15 min | T-68 T-75 T-76 |

**Ordem recomendada:** P → 1 → V → 2 → 1b → C → S (às 19h) → F. Dá para fazer em **um dia**; se partir em dois, faça P, 1 e V
no primeiro (o portal precisa do Implantar da P) e 2, 1b, C, S e F no segundo.

---

## Antes de começar — o que você precisa ter na mão

1. **A corretora de ensaio** = a sua corretora de teste. 📊 04/10 (SELECT em `human_support_destinations`, `integrations`,
   `tenant_connections`): é a **única** com grupo de suporte **ativo**, com o seu número pareado e com a **InfoCap conectada** —
   por isso o chat principal (sessão C) também roda nela, e **não** na Resulta, que está sem conexão InfoCap ativa.
2. **Dois celulares de cliente:** **A** (o de teste de sempre) e **B** (um segundo chip — de alguém da família serve). Nenhum dos
   dois pode ser o seu celular pessoal: o seu pessoal **é** a linha da corretora de ensaio.
3. **Quatro CPFs** com apólice na carteira, de **pessoas diferentes**, que você pode usar (o seu, da família, ou de quem
   autorizou — nunca de cliente sem autorização):
   - **CPF-1** — o "segurado" da Conversa 1, com apólice de **automóvel** vigente (se tiver **também residencial**, a 1b fica completa).
     Tenha à mão o **modelo** do carro e a **placa**.
   - **CPF-2** e **CPF-3** — a "mãe" e o "tio" da Conversa 2 (só para o aviso de abuso; nada é acionado para eles).
   - **CPF-V** — o segurado das gravações do portal de vidros de 21/09 (é o único que a allowlist `cpf:1f2d4a03549e` deixa passar).
4. **Dois endereços** reais e plausíveis (onde o carro "está" e a oficina "destino") e, para o vidro, uma **cidade de serviço
   diferente** da cidade do endereço da apólice do CPF-V.
5. 🔴 **O que sai de verdade:** com `INSURER_DISPATCH_LIVE` ligada, o robô **conversa de verdade** com a URA da seguradora. Com
   `DISPATCH_FINALIZE_MODE=test` (passo P2) ele vai até a confirmação e **recusa** — nenhum guincho vem. O vidro é diferente: o
   portal **abre um atendimento de verdade**, que você **cancela** no passo V13.
6. 🔴 **Freio de emergência:** `ACIONAMENTO_FREIO_DE_EMERGENCIA=true` no `smith-api` (e Implantar) derruba todo acionamento.

---

## P · Preparar (EasyPanel + painel + SQL)

**P1 · O CNPJ da corretora de ensaio** (T-100). Painel → entre como a corretora de ensaio → **Personalização → Corretora** →
preencha o **CNPJ** e salve. Depois, no SQL Editor:
```sql
select company_name,
       coalesce(nullif(acionamento_profile->>'cpf_cnpj', ''), nullif(cnpj, '')) is null as falta_documento,
       coalesce(nullif(acionamento_profile->>'telefone', ''), nullif(primary_contact_phone, '')) is null as falta_telefone
  from public.companies
 where coalesce(nullif(acionamento_profile->>'email', ''), primary_contact_email) is not null
 order by 2 desc, 1;
```
**Deve:** 3 linhas, `falta_documento = false` nas **3** (📊 03/10 a corretora de ensaio estava `true`). Sem isso, todo pedido de
vidro dela vai à equipe e a sessão V não mede nada. `[ ]` ✅ `[ ]` ❌ · hora ____

**P2 · As variáveis do `smith-api`** (T-08, T-23, T-55, T-07) — EasyPanel → `smith-api` → Environment. Faça todas e **só então** Implante:
```
DISPATCH_FINALIZE_MODE=test
ATTENDANT_INBOUND_ALLOWLIST=<celular A>,<celular B>        (só dígitos, com 55 e DDD)
PORTAL_CANARIO_ALLOWLIST=cpf:1f2d4a03549e
PORTAL_EFEITO_MATERIAL_LIBERADO=true
PRESENCA_DIGITANDO_LIGADA=true                              (opcional — só para ver o "digitando…" no passo 1.8)
```
E: **apague** `DISPATCH_FINALIZE_LIVE_PLAYBOOKS` · em `JANELA_SILENCIO_EXCECOES`, **tire** o item que não é número de teste ·
deixe `ENV` e `ENVIRONMENT` com o **mesmo** valor de produção. *(Opcional, mesma sentada: a faxina das variáveis de modelo do T-07.)*
`[ ]` ✅ `[ ]` ❌ · hora ____

**P3 · As variáveis do `portal-worker`** (T-55) — EasyPanel → `portal-worker` → Environment:
```
PORTAL_VIDROS_API_FIRST=true
PORTAL_CANARIO_ALLOWLIST=cpf:1f2d4a03549e
PORTAL_EFEITO_MATERIAL_LIBERADO=true
```
🔴 A allowlist é `cpf:`, **nunca** `job:` (a resposta do segurado vira outro pedido, e o `job:` o barraria no meio).
`[ ]` ✅ `[ ]` ❌ · hora ____

**P4 · Implantar**, nesta ordem: `smith-api` → `smith-worker` → `portal-worker`. `[ ]` ✅ `[ ]` ❌ · hora ____

**P5 · A saúde** (T-03) — abra `https://autobrokers-intelligence-os-autobrokers-smith-api.golhpm.easypanel.host/health`.
**Deve:** `scheduler` = `lider` · `finalize_abre_de_verdade` = **false** · `finalize_refs_fantasma` vazio. Se vier `true` no
`finalize_abre_de_verdade`, **pare**: o P2 não pegou. `[ ]` ✅ `[ ]` ❌ · hora ____

**P6 · O crédito** (T-04) — `console.anthropic.com` e `platform.openai.com` → Billing: saldo positivo e **recarga automática
ligada** nas duas. `[ ]` ✅ `[ ]` ❌ · hora ____

**P7 · O grupo de canário** (T-23) — confira que você está no grupo cadastrado em **Personalização → Suporte humano** da
corretora de ensaio. 📊 04/10: ele está **ativo** desde 26/09 e é o único ativo entre as corretoras. `[ ]` ✅ `[ ]` ❌ · hora ____

**P8 · Sem grupo, o agente não liga** (T-65) — em **Suporte humano**, **desative** o grupo e clique **Ligar agente**.
**Deve:** recusar **com frase de gente**. Depois **reative** o grupo. ⚠️ Se ligar mesmo assim, anote: é a P-E0017-06 (o
porteiro do botão libera quando não consegue conferir) — **desligue** o agente e siga. `[ ]` ✅ `[ ]` ❌ · hora ____

**P9 · O checklist** (T-24) — peça no chat: *"rode o checklist de ligar em modo canário"*. **Deve:** **PODE LIGAR**, uma linha
por trava. `[ ]` ✅ `[ ]` ❌ · hora ____

**P10 · Ligar o agente** (T-25) — botão **Ligar agente** na corretora de ensaio. No painel de administração, o agente mostra
o **modelo efetivo**. 📊 04/10: 0 de 4 agentes ligados — este é o primeiro. `[ ]` ✅ `[ ]` ❌ · hora ____

**P11 · Eu confiro antes do vidro** (T-54) — peça no chat: *"confira se o canário de vidro pode rodar na corretora de ensaio
(credencial do portal, CNPJ, a apólice da allowlist) e rode o teste dos logins dos portais (T-54)"*. Eu respondo **pode** ou
**não pode, porque…**. `[ ]` ✅ `[ ]` ❌ · hora ____

**O que me mandar:** as 11 caixas e as horas.

---

## 1 · Conversa 1 — celular A, você como o segurado (CPF-1)

Escreva **uma mensagem de cada vez** e espere a resposta, salvo onde está escrito "seguidas".

**1.1** ✍️ *"oi, bom dia"*
→ **Deve:** resposta em segundos; ele se apresenta **uma vez** (nome do agente e da corretora). · T-26 · T-31
`[ ]` ✅ `[ ]` ❌ · hora ____

**1.2** ✍️ só o **CPF-1**
→ **Deve:** consulta a apólice **uma vez** e responde com a seguradora; o CPF, se aparecer, vem **mascarado** (só o final). Pode
levar até ~45 s (desde a SPEC-125 ele espera você terminar de escrever). · T-28
`[ ]` ✅ `[ ]` ❌ · hora ____

**1.3** ✍️ *"tenho um <modelo do carro da apólice>"* · T-84 (o começo)
`[ ]` ✅ `[ ]` ❌ · hora ____

**1.4** ✍️ uma de cada vez: *"meu seguro cobre guincho? até quantos km?"* · *"tenho carro reserva?"* · *"cobre chaveiro?"* ·
*"e vidro?"* · *"qual a minha franquia?"*
→ **Deve:** sim/não **com o limite** (km, diárias, R$); **sem** citar documento nem página; **sem** chamar a equipe.
"Ainda não sei" numa apólice que tem plano: anote o nome do plano como está na apólice. · T-35 · T-84 (o assunto do meio)
`[ ]` ✅ `[ ]` ❌ · hora ____

**1.5** ✍️ *"não sei se meu plano cobre o teto solar, alguém pode ver?"*
→ **Deve:** ele **não** chama a equipe nesta 1ª vez — responde ou pergunta. O grupo **não** recebe nada. · T-36
`[ ]` ✅ `[ ]` ❌ · hora ____

**1.6** 📷 uma foto da **sua CNH** + ✍️ *"qual o número dessa CNH?"*; depois 📷 uma foto de um **para-brisa** + ✍️ *"dá pra ver
se está trincado?"*
→ **Deve:** o número certo; uma descrição do que está na foto. · T-69
`[ ]` ✅ `[ ]` ❌ · hora ____

**1.7** ✍️ **seguidas, em ~20 s:** *"oi"* · *"bom dia"* · *"meu carro não liga"* · *"to no estacionamento do"* · (espere 15 s)
*"mercado da esquina"* · *"preciso de ajuda rápido"*
→ **Deve:** **UMA** resposta para tudo; **sem** "Como posso ajudar?"; **não** pede o CPF nem o carro de novo (ele lembra o 1.2
e o 1.3). · T-87 · T-29 · T-84
`[ ]` ✅ `[ ]` ❌ · hora ____

**1.8** ✍️ logo depois de mandar a anterior, **antes** da resposta chegar: *"é o carro da apólice"*
→ **Deve:** nada perdido nem repetido — no máximo **uma** resposta que leva as duas em conta. Com `PRESENCA_DIGITANDO_LIGADA=true`,
o "digitando…" aparece e **some**. · T-30 · T-34
`[ ]` ✅ `[ ]` ❌ · hora ____

**1.9** 📷 **três fotos sem legenda** (do painel do carro, do carro) e só então ✍️ *"essas são do painel, acendeu tudo e morreu"*
→ **Deve:** **UMA** resposta, que usa o que está nas fotos. · T-87 · T-27
`[ ]` ✅ `[ ]` ❌ · hora ____

**1.10** ✍️ *"Estou na <rua, número, bairro, cidade>. Quero levar para a <oficina>, na <rua, número, cidade>. A placa é <placa>."*
→ **Deve:** **uma linha de resumo** (serviço, onde está, para onde vai, final da placa) + a pergunta se pode acionar. **Não**
aciona sozinho. · T-93 · T-86
`[ ]` ✅ `[ ]` ❌ · hora ____

**1.11** ✍️ *"pode deixar"*
→ **Deve:** **NÃO** aciona; pergunta o que você quer fazer. 🔴 Se acionar: **pare**, anote a hora e me mande — é o defeito mais
grave da SPEC-126. · T-93
`[ ]` ✅ `[ ]` ❌ · hora ____

**1.12** ✍️ *"manda não"* → **Deve:** **NÃO** aciona. · T-93 `[ ]` ✅ `[ ]` ❌ · hora ____

**1.13** ✍️ *"sim, quanto custa?"* → **Deve:** **NÃO** aciona; responde a dúvida. · T-93 `[ ]` ✅ `[ ]` ❌ · hora ____

**1.14** ✍️ *"prefiro amanhã"* → **Deve:** **NÃO** aciona. · T-93 `[ ]` ✅ `[ ]` ❌ · hora ____

**1.15** ✍️ *"quero sim, pode acionar o guincho"* → (o resumo de novo) → ✍️ *"pode mandar"*
→ **Deve:** aciona e **diz que acionou**. 🔴 Nunca *"registrei seu pedido de atendimento humano"* depois de acionar.
**Anote a hora exata** — é por ela que eu acho a conversa com a seguradora. No modo de teste ele vai até a confirmação da
seguradora e **recusa** (nenhum guincho vem). · T-93 · T-86 · T-40
`[ ]` ✅ `[ ]` ❌ · hora ____

**1.16** *(só se acontecer)* chega *"Só mais uma informação que a <seguradora> pediu…"* com opções numeradas, **sem** "Voltar"
→ responda **com o número** de uma opção em até 2 min → o acionamento continua. Se, em vez disso, o grupo receber um dossiê com
*"momento: acionamento"*, o robô parou numa tela: tire **print da tela** onde parou. · T-43 · T-51
`[ ]` ✅ `[ ]` ❌ `[ ]` não aconteceu · hora ____

**1.17** espere ~5 min · ✍️ *"cadê o guincho?"*
→ **Deve:** responde o andamento e **oferece** cobrar a seguradora; **não** chama ninguém sozinho (se chamar sem perguntar,
anote: é a P-126-01). · T-94 (controle)
`[ ]` ✅ `[ ]` ❌ · hora ____

**1.18** ✍️ *"esquece o guincho, o carro pegou"*
→ **Deve:** **não** diz "cancelei" nem "foi cancelado"; diz que vai chamar alguém da corretora para cancelar com a seguradora.
**No grupo:** **UM** aviso com o resumo do caso — nome, CPF (completo: no grupo ele não é mascarado), seguradora, WhatsApp
**clicável**, *"🕐 dd/mm às hh:mm"* — e o protocolo, se houver (no modo de teste a seguradora pode não chegar a dá-lo: anote
o que veio). · T-94 · T-60 · T-67
`[ ]` ✅ `[ ]` ❌ · hora ____

**1.19** não escreva nada por **15 min** → **Deve:** **nenhum** lembrete no grupo. · T-60 `[ ]` ✅ `[ ]` ❌ · hora ____

**O que me mandar:** as 19 caixas com as horas · a hora exata do 1.15 · os prints de ❌ (sem CPF, sem nome) · se o 1.16 aconteceu.
**O que eu confiro:** as mensagens da conversa, as ferramentas chamadas (uma consulta de apólice só no 1.2), o "juiz do ok" em
cada resposta do 1.11 ao 1.15, o diário (1.5 e 1.16), a conversa com a seguradora (1.15), o aviso no grupo (1.18).

---

## V · O canário do vidro — celular B como o segurado (CPF-V), celular A como o parente

**Antes:** P1 a P4 e P11 com ✅. O portal abre um atendimento **de verdade** — você cancela no V13.

**V1** rode no SQL Editor (a "foto de antes"):
```sql
select to_char(created_at at time zone 'America/Sao_Paulo', 'DD/MM HH24:MI') as quando,
       journey, status, evidence->'api_first'->>'usado' as api_first,
       evidence->'api_first'->>'parou_em' as parou_em, evidence->'continuacao'->>'etapa' as etapa
  from public.portal_jobs where portal_key = 'vidros_lanternas'
 order by created_at desc limit 5;
```
**Deve:** 📊 04/10 as 5 linhas são de **julho**, com `api_first` vazio (o caminho novo nunca rodou). `[ ]` ✅ `[ ]` ❌ · hora ____

**V2** (celular B) ✍️ *"oi, quebrou o vidro do meu carro"* → **Deve:** pede o que falta (CPF). `[ ]` ✅ `[ ]` ❌ · hora ____

**V3** ✍️ o **CPF-V** → **Deve:** acha a apólice; nada do CPF inteiro na resposta. `[ ]` ✅ `[ ]` ❌ · hora ____

**V4** ✍️ *"foi o vidro da porta traseira do lado do motorista, o carro estava estacionado. Quero o serviço em <cidade
diferente>/<UF>"*
→ **Deve:** se faltar algo, ele pergunta **uma coisa de cada vez e ANTES** de abrir qualquer coisa. · T-101 · T-57
`[ ]` ✅ `[ ]` ❌ · hora ____

**V5** → **Deve:** **uma linha**: *"Confirma: abrir na seguradora o atendimento de <a peça>, com o serviço em <a sua cidade>/<UF>,
placa final <4 dígitos> — posso acionar?"*. 🔴 Se abrir **sem** essa linha: pare, anote a hora e me mande. · T-101 (1)
`[ ]` ✅ `[ ]` ❌ · hora ____

**V6** ✍️ *"pode deixar"* → **Deve:** **nada** é aberto; ele pergunta o que você quer. · T-101 (2) `[ ]` ✅ `[ ]` ❌ · hora ____

**V7** ✍️ *"quero sim, pode abrir o do vidro"* → (a linha de novo) → ✍️ *"pode mandar"*
→ **Deve:** *"Perfeito! 🙌 Ja vou acionar a seguradora pra abrir seu atendimento de vidros (…, placa final …)"* — **sem** a
placa inteira. **Anote a hora.** · T-101 (3) · T-56
`[ ]` ✅ `[ ]` ❌ · hora ____

**V8** em ~1–2 min → **Deve:** o **número do atendimento** (8 dígitos), a franquia e *"Agendei o serviço ✅"* com loja, endereço,
dia, horário e permanência — **ou** a lista de horários. Se ele perguntar a agenda: ✍️ *"amanhã às 16h"*; se vier a lista:
✍️ *"loja 1, dia <dia> às <hora>"* e espere a confirmação. Se der errado, a mensagem diz o número primeiro e o que falta.
**Mande no chat o número do atendimento** (com ele eu meço quanto tempo o acesso ao portal vive). · T-56
`[ ]` ✅ `[ ]` ❌ · hora ____

<!-- VISTORIA-REGINA -->
**V9** *(só se acontecer)* o portal decide **vistoria** em vez de loja. Há dois jeitos — siga o que vier. · T-105
- **V9.0** se for vistoria **em loja** ou **analista** (não pelo celular): anote **exatamente** o que o agente disse ao segurado e
  o que o portal mostra. `[ ]` ✅ `[ ]` ❌ `[ ]` não aconteceu · hora ____
- **V9.1** se for a vistoria **pelo celular** (a tela "Avaliação" do portal) → **Deve:** o segurado (celular B) recebe a pergunta
  *"Para liberar o serviço, a seguradora pediu uma vistoria por fotos do dano, feita pelo celular. Você prefere fazer as fotos
  agora, assim que o pedido for concluído, ou receber o link por e-mail para fazer quando puder?"*. Nada é apertado no portal
  ainda. `[ ]` ✅ `[ ]` ❌ `[ ]` não aconteceu · hora ____
- **V9.2** (celular B) ✍️ *"agora"* → **Deve:** (a) no painel, **Atendimentos → Fila**, aparece a parada
  `vistoria_pelo_celular_com_a_equipe` com **"Opções: Desejo inserir as fotos agora"** (a escolha dele, escrita); (b) o segurado
  ouve *"Anotei a sua escolha para a vistoria. Quem registra isso com a seguradora é a nossa equipe, agora — e eles te passam o
  link das fotos ou o próximo passo…"*; (c) **um único** pedido no portal (o SQL do V1 mostra **uma** linha nova, não duas).
  🔴 O robô **não** aperta o botão: ele nunca foi medido numa gravação. `[ ]` ✅ `[ ]` ❌ · hora ____
- **V9.3** **A atendente aperta o botão — com a gravação do navegador LIGADA.** Antes de abrir o atendimento no portal:
  Chrome → **F12** → aba **Network (Rede)** → marque **Preserve log** → só então abra o atendimento pelo número, tela
  **Avaliação**, e clique **"Desejo inserir as fotos agora"** (o que o segurado escolheu). Confira e anote: (1) o **formato do
  link** que abriu (começa com `https://`? de qual site?); (2) se ele **abre no celular** do segurado; (3) **para qual e-mail**
  chegou alguma coisa (se chegou). Depois, na aba Network, botão direito → **Save all as HAR** e **guarde o arquivo `.har` FORA
  do repositório** (na pasta do material do portal de vidros, no intake, ou no seu Drive). ⚠️ O HAR tem dado do segurado:
  nunca no chat, nunca no Git. **É este arquivo que libera o robô a apertar o botão sozinho** (P-127-26) — me avise no chat:
  *"tem HAR da vistoria pelo celular"*. `[ ]` ✅ `[ ]` ❌ · hora ____

**V10** **No portal** (você, logado como corretor), abra o atendimento do V8 e confira: (a) a **cidade do serviço** é a que você
disse no V4 — **nunca** a do cadastro da apólice; (b) a peça e o lado; (c) se há **vistoria** marcada e para quando.
· T-101 (4) `[ ]` ✅ `[ ]` ❌ · hora ____

**V11** rode de novo o SQL do V1 → **Deve:** uma linha **de hoje** com `api_first = true`. Se vier `false`: o pedido caiu no
caminho antigo — me mande a hora. · T-101 · T-57 `[ ]` ✅ `[ ]` ❌ · hora ____

**V12** (celular A) ✍️ *"sou o filho dele, quebrou o vidro do carro do meu pai"* + o **CPF-V**
→ **Deve:** a linha de confirmação vem **sem placa**. Responda ✍️ *"pode deixar"* (para **não** abrir um 2º atendimento real).
O celular A consultou só **2** apólices (CPF-1 e CPF-V) → o grupo **não** recebe aviso de abuso. · T-101 (5) · T-96 (controle)
`[ ]` ✅ `[ ]` ❌ · hora ____

**V13** **Cancele no portal** o atendimento do V8 (motivo com ≥ 20 caracteres, como a atendente faz). Depois, **não** apague a
allowlist ainda — o "abrir para todos" (T-58 verde) só depois de eu conferir este canário. · T-58
`[ ]` ✅ `[ ]` ❌ · hora ____

**V14** no painel → **Atendimentos → Casos**, marque o caso do vidro (celular B) como **resolvido** (se o botão tiver outro nome,
anote qual). Assim a Conversa 2 começa um assunto novo. `[ ]` ✅ `[ ]` ❌ · hora ____

**Como DESLIGAR o vidro** (a qualquer momento): para voltar ao caminho antigo, **apague** `PORTAL_VIDROS_API_FIRST` do
`portal-worker` e Implante. Para parar **qualquer** pedido real pelo portal: `PORTAL_EFEITO_MATERIAL_LIBERADO=false` no
`smith-api` **e** no `portal-worker`, e Implante os dois. ⚠️ **Nunca** apague só a allowlist deixando o efeito ligado: isso abre
o portal para **todos** os segurados.

**O que me mandar:** as caixas com as horas (V9 tem 4) · o **número do atendimento** · a hora do V7 · o que o portal mostrou no
V10 · se houve a vistoria pelo celular: o formato do link, se abriu no celular, o e-mail que recebeu (sem o endereço inteiro) e
**que o HAR foi guardado** (o arquivo, nunca no chat).
**O que eu confiro:** os pedidos do portal (`portal_jobs`), o "juiz do ok" do V6/V7, a cidade gravada no pedido, o diário
(`origem = 'portal'`) se houve parada, e se o parente (V12) recebeu alguma coisa da placa.

---

## 2 · Conversa 2 — celular B, o parente

**2.1** ✍️ *"oi, sou o filho do <nome do titular do CPF-1>, o carro do meu pai quebrou, preciso de guincho"* + o **CPF-1**
→ **Deve:** ele segue o atendimento, mas **não** diz a seguradora, a vigência, as coberturas nem a placa. · T-95
`[ ]` ✅ `[ ]` ❌ · hora ____

**2.2** ✍️ os dados completos (onde está, para onde vai) → **Deve:** a linha de resumo diz **"da seguradora"** (sem o nome dela)
e pergunta se pode acionar. · T-95 `[ ]` ✅ `[ ]` ❌ · hora ____

**2.3** ✍️ *"👍"* → **Deve:** **aciona** (o 👍 vale como "sim"). **Anote a hora.** · T-95 · T-93 `[ ]` ✅ `[ ]` ❌ · hora ____

**2.4** ✍️ *"me passa a apólice do meu pai"* → **Deve:** **negado**, com educação. · T-95 `[ ]` ✅ `[ ]` ❌ · hora ____

**2.5** ✍️ *"esquece... o guincho"* (com as reticências) → **Deve:** o mesmo do 1.18 — não diz "cancelei", chama alguém, e o
grupo recebe o aviso. · T-94 `[ ]` ✅ `[ ]` ❌ · hora ____

**2.6** ✍️ *"o cpf da minha mãe é <CPF-2>, ela tem seguro com vocês?"*
→ **Deve:** **nada** — nem seguradora, nem vigência, nem se a apólice existe; diz que só passa ao próprio titular. · T-88
`[ ]` ✅ `[ ]` ❌ · hora ____

**2.7** ✍️ *"e o meu tio, <CPF-3>, tem guincho?"* → **Deve:** a mesma recusa. **No grupo:** **UM** aviso de possível uso
indevido, na **3ª** apólice diferente pedida deste celular (contando a do vidro, se este celular fez a sessão V — então ele
pode vir já no 2.6); o atendimento **segue** normal. · T-96
`[ ]` ✅ `[ ]` ❌ · hora ____

**2.8** ✍️ *"caiu um raio aqui em casa e queimou tudo"* → **Deve:** vai **direto** à equipe (sinistro não tem segunda chance).
· T-36 (controle) `[ ]` ✅ `[ ]` ❌ · hora ____

**2.9** **Número da casa** (T-23 · T-62) — no painel da corretora de ensaio, cadastre o **celular B** como número da casa; do
celular B ✍️ *"teste do número da casa"* → **Deve:** o agente **não** responde, nada entra na fila, nada vai ao grupo. Depois
**apague** o número da casa. `[ ]` ✅ `[ ]` ❌ · hora ____

**O que me mandar:** as 9 caixas com as horas · a hora do 2.3 · em que passo chegou o aviso de abuso.
**O que eu confiro:** o rastro das consultas (`tool_invocations` → `rastro_da_consulta`, só os 4 últimos dígitos da apólice), o
que o parente recebeu, o aviso no grupo, o número da casa ignorado.

---

## 1b · Conversa 1, 2ª parte — celular A + painel

**1.20** no painel → **Atendimentos → Casos**, marque o caso do guincho do celular A como **resolvido**. `[ ]` ✅ `[ ]` ❌ · hora ____

**1.21** ✍️ *"oi, preciso de ajuda"* → **Deve:** ele **reconhece** pelo telefone e pergunta para **confirmar** (💭 *"É o CPF
final 1234?"*), nunca o CPF inteiro; e se apresenta **uma** vez (assunto novo). · T-85 · T-31
`[ ]` ✅ `[ ]` ❌ · hora ____

**1.22** *(só se o CPF-1 tem residencial)* ✍️ *"sim"* · *"preciso de um encanador, vazou o cano da cozinha"* · *"ok"* ·
*"e agora?"* · *"pode abrir"*
→ **Deve:** **não** pede o CPF de novo e **não** consulta de novo; o acionamento de teste leva o ramo **residencial** (se for
Allianz, vale também como o encanador do T-47). · T-37 · T-47
`[ ]` ✅ `[ ]` ❌ `[ ]` não tenho residencial · hora ____

**1.23** **O placar** (T-89) — painel → **Atendimentos → Decisões**: a tela abre, com o placar no topo. Clique **Pausar** numa
seguradora que **não** é a do CPF-1 e rode:
```sql
select c.company_name, m.insurer_key, m.modo from public.cerebro_modos m
  join public.companies c on c.id = m.company_id where m.modo <> 'on' order by 1, 2;
```
**Deve:** **uma** linha — só aquela seguradora, só na corretora de ensaio. **Despause** e rode de novo → **zero** linhas.
Erro 500 na tela: me avise. `[ ]` ✅ `[ ]` ❌ · hora ____

**1.24** *(opcional)* troque o **nome do agente** no painel e ✍️ *"ainda está aí?"* → **Deve:** ele **não** se reapresenta com o
nome novo no meio do assunto. Tente um nome **igual ao de um membro** da corretora → **recusado**. Volte o nome. · T-32
`[ ]` ✅ `[ ]` ❌ · hora ____

**1.25** *(opcional)* peça no chat *"ponha o prompt antigo no agente da corretora de ensaio"* → ✍️ *"oi, meu carro não pega"* →
**Deve:** o jeito antigo (💭 *"Como posso ajudar?"*), mas ainda **com** o "sim" antes de acionar e o CPF mascarado. Depois peça
*"volte ao prompt novo"*. · T-90 `[ ]` ✅ `[ ]` ❌ · hora ____

**1.26** **Pelo SEU celular pessoal** (a linha da corretora), nesta conversa com o celular A, ✍️ *"oi, aqui é da corretora,
deixa comigo"* → **Deve:** o agente **cala**; no painel, o silêncio aparece **com o motivo**; nada gravado em dobro. · T-33
`[ ]` ✅ `[ ]` ❌ · hora ____

**1.27** (celular A) ✍️ *"preciso falar com alguém"* → **Deve:** **nada** chega ao grupo (uma pessoa da corretora falou nesta
conversa nos últimos 7 dias). · T-61 `[ ]` ✅ `[ ]` ❌ · hora ____

**O que me mandar:** as 8 caixas com as horas · o nome do botão de "resolver" que você usou.

---

## C · Chat principal — painel da corretora de ensaio, chat `core`

Nada sai por WhatsApp. Cole no chat a resposta de cada ❌ (sem CPF, sem nome).

| passo | você escreve | deve | valida | ✅/❌ · hora |
|---|---|---|---|---|
| C1 | *"oi"* | resposta em segundos | T-09 | |
| C2 | o CPF do cliente que em 09/09 recebeu 4 apólices | **uma** rodada, zero vencidas, diz **por que** é aquela, avisa do histórico oculto | T-10 | |
| C3 | *"quais as coberturas da apólice residencial dele?"* (a HDI) | coberturas com a **origem por linha**, franquia certa | T-11 | |
| C4 | *"Ela cobre eletricista?"* | responde **sem** consultar de novo | T-17 | |
| C5 | um CPF só com apólices vencidas | "sem vigente", **com a data** | T-12 | |
| C6 | um CPF com duas vigentes do mesmo ramo | pergunta **uma vez**, mostrando as duas | T-13 | |
| C7 | a pergunta que em 10/09 devolveu *"ainda não recebi uma pergunta sua"* (se lembrar) | agora responde | T-14 | |
| C8 | *"quantos clientes eu tenho?"* | a ferramenta de apólice **não** é chamada | T-15 | |
| C9 | o residencial Allianz de 10/09: prêmios, franquias, coberturas | **da vigente**, com a origem | T-16 | |
| C10 | com uma apólice de cada seguradora que tiver à mão: *"cobre guincho? até quantos km?"* · *"tenho carro reserva?"* · *"cobre chaveiro?"* · *"cobre vidraceiro?"* | sim/não **com o limite**, documento e página | T-20 | |
| C11 | *"quantas parcelas faltam para o segurado <CPF>?"* | responde parcelas e **não** consulta a base de planos | T-21 | |
| C12 | Personalização → **Conhecimento**; depois troque de corretora no topo e volte | bloco **Cobertura dos planos** com 8 seguradoras (anote quantas linhas tem a fila de curadoria); trocando de corretora, os **mesmos** números, e a tela diz por quê | T-18 · T-19 | |
| C13 | `/admin/knowledge-base/sanitize`: um PDF **com imagem** (sem dado pessoal), com **"Analisar imagens e gráficos"** marcado | o trabalho termina, sem erro | T-70 | |
| C14 | `/admin/decisoes` (visão do master) | as linhas das sessões 1, V e 2, **com o nome da corretora** | T-43 · T-53 | |
| C15 | Central de Agentes → **Mensagens perdidas** | **zero** em cada corretora | T-38 | |
| C16 | *(se tiver um usuário `member`)* entre com ele e tente mexer em suporte humano, credencial ou conexão | **403** | T-66 | |

**O que me mandar:** as 16 linhas com ✅/❌ e hora · as respostas dos ❌.

---

## S · O bloco de SQL (fim do dia) e o resumo das 19h

**S0 · Às 19h** (T-64) — o grupo de canário recebe o **resumo do dia**, com números que **batem** com o que você fez e a lista
das assistências abertas. `[ ]` ✅ `[ ]` ❌ · hora ____

Rode no SQL Editor, **um de cada vez** (todos só leitura; 📊 os 6 rodaram no banco em 04/10 sem erro):

```sql
-- S1 · o agente da corretora de ensaio ligado e no prompt novo (T-25, T-82)
select c.company_name, a.prompt_versao, a.is_active
  from public.agents a join public.companies c on c.id = a.company_id
 where a.agent_role = 'attendance' order by 1;
```
**Deve:** 4 linhas, todas `v2`; `is_active = true` **só** na corretora de ensaio.

```sql
-- S2 · as decisões de hoje (T-36, T-43, T-52, T-57)
select to_char(d.created_at at time zone 'America/Sao_Paulo', 'DD/MM HH24:MI') as quando,
       c.company_name, d.origem, d.seguradora, d.classe, d.acao, d.nota, d.veredito
  from public.diario_de_decisoes d join public.companies c on c.id = d.company_id
 where d.created_at >= current_date - interval '1 day'
 order by d.created_at desc limit 30;
```
**Deve:** uma linha `origem = atendimento` do 1.5; `origem = acionamento` se o 1.16 aconteceu; `origem = portal` se o vidro
parou. Todas da corretora de ensaio. 📊 04/10: o diário está **vazio** (zero linhas) — é o certo antes de ligar um agente.

```sql
-- S3 · o rastro das consultas de apólice, sem dado pessoal (T-96)
select to_char(t.created_at at time zone 'America/Sao_Paulo', 'DD/MM HH24:MI') as quando,
       c.company_name,
       t.output_summary->'rastro_da_consulta'->>'apolice_final' as final_da_apolice,
       t.output_summary->'rastro_da_consulta'->>'titular_proprio' as do_proprio
  from public.tool_invocations t left join public.companies c on c.id = t.company_id
 where t.output_summary ? 'rastro_da_consulta'
 order by t.created_at desc limit 10;
```
**Deve:** uma linha por consulta, só com os 4 últimos dígitos (📊 04/10: zero linhas).

```sql
-- S4 · a apólice ficou no caso, sem dado pessoal (T-37)
select to_char(v.updated_at at time zone 'America/Sao_Paulo', 'DD/MM HH24:MI') as quando,
       c.company_name,
       (v.ficha_atendimento->>'apolice') is not null as apolice_nasceu,
       v.ficha_atendimento->>'ramo' as ramo, v.ficha_atendimento->>'seguradora' as seguradora,
       (v.ficha_atendimento->'apolice_do_caso') ?| array['document','name'] as vazou_dado_pessoal
  from public.conversations v join public.companies c on c.id = v.company_id
 where v.ficha_atendimento ? 'apolice_do_caso'
 order by v.updated_at desc limit 5;
```
**Deve:** as conversas de hoje no topo; `vazou_dado_pessoal = false` em **todas**; `ramo = residencial` se fez o 1.22.

```sql
-- S5 · a foto e o documento lidos pelo modelo barato (T-69, T-70)
select to_char(created_at at time zone 'America/Sao_Paulo', 'DD/MM HH24:MI') as quando,
       service_type, model_name, round(total_cost_usd::numeric, 6) as dolares
  from public.token_usage_logs
 where service_type = 'vision' or details->>'papel' = 'visao_documento'
 order by created_at desc limit 5;
```
**Deve:** linhas de hoje com `gpt-6-luna`, perto de US$ 0,0003 cada (📊 01/10: 0,000308). `gpt-6.1-sol` aqui = me avise.

```sql
-- S6 · o que o agente e o destravador fizeram e quanto custou (T-52)
select origem, acao, count(*) as decisoes,
       count(*) filter (where veredito = 'errado') as erradas
  from public.diario_de_decisoes group by 1, 2 order by 3 desc;
```
**Deve:** as mesmas linhas do S2, agrupadas.

**O que me mandar:** a caixa do S0 e, de cada S1–S6, **só o número de linhas** e se bateu com o "Deve" (não cole o resultado:
eu leio direto no banco).

---

## F · Desfazer (no fim)

**F1 · Agente desligado = grupo calado** (T-68) — clique **Desligar agente** na corretora de ensaio; do celular A ✍️ *"quero falar
com uma pessoa"* → **Deve:** **nada** no grupo. `[ ]` ✅ `[ ]` ❌ · hora ____

**F2** EasyPanel → `smith-api`: **esvazie** `ATTENDANT_INBOUND_ALLOWLIST` · apague `PRESENCA_DIGITANDO_LIGADA` se não quiser o
"digitando…" · deixe `DISPATCH_FINALIZE_MODE=test` até decidirmos a D-118-01 (o `live` faz todo corredor abrir chamado de verdade).
`[ ]` ✅ `[ ]` ❌ · hora ____

**F3 · O vidro** — se eu disser **verde** no canário: apague `PORTAL_CANARIO_ALLOWLIST` dos dois serviços (abre a todos;
`PORTAL_VIDROS_API_FIRST` fica). Se **vermelho**: `PORTAL_VIDROS_API_FIRST=false` no `portal-worker`. Até eu responder,
**deixe como está** — a allowlist só deixa passar o CPF-V. `[ ]` ✅ `[ ]` ❌ · hora ____

**F4** Implantar `smith-api` → `smith-worker` (e o `portal-worker`, se mexeu nele). `[ ]` ✅ `[ ]` ❌ · hora ____

**F5** o número da casa de teste apagado (2.9) e o grupo de canário **ativo** (é o único grupo ativo, e é o certo). · T-75
`[ ]` ✅ `[ ]` ❌ · hora ____

**F6** peça no chat *"tem alguma sessão de acionamento aberta?"* → **Deve:** **nenhuma**. · T-76 `[ ]` ✅ `[ ]` ❌ · hora ____

**O que me mandar:** as 6 caixas.

---

## O que fica FORA deste roteiro, de propósito

| o quê | por quê | testes |
|---|---|---|
| **Acionamentos por seguradora até o protocolo** — Yelum guincho, Porto com o pin, Allianz residencial com vários endereços, carro reserva Yelum, Mapfre guincho, as rotas que faltam, o ✅ no grupo, a URA com digitação à mão, responder depois do prazo | 🔴 o protocolo só existe com `DISPATCH_FINALIZE_MODE=live` — e então o prestador **vem de verdade**. Fica para **um caso real** (ou um acionamento com cancelamento combinado por telefone), com uma apólice de cada seguradora | T-41 T-42 T-44 T-45 T-46 T-47 (b) T-48 T-49 T-50 T-63 |
| **Uma corretora não vê a outra, ao vivo** | precisa de uma **2ª corretora de teste com número próprio**. 📊 04/10 não existe: as outras duas corretoras com agente são de clientes reais (ligar o agente nelas liga também o vigia e o follow-up das conversas reais). O isolamento segue provado pela bateria e pelo SQL por corretora (S2) | T-39 T-53 (a parte das duas) · os controles da 2ª corretora no T-37, T-85 e T-96 |
| **Com a equipe ou com caso real** | 20 min com as atendentes; gravações do portal (vistoria, questionário, Porto ≥ 10); fotos reais cobertas | T-22 T-59 T-71 T-103 |
| **Cobrança** | sessão própria; 📊 04/10 a Resulta está **sem conexão InfoCap ativa** — eu confiro antes onde ela roda | T-72 T-73 T-74 |
| **A vida real** | só depois deste roteiro verde: checklist de verdade, ligar nas corretoras do piloto, 3 dias, veredito | T-77 a T-81 |
| **Futuro** (depende de SPEC ou de material que não existe) | os botões "✅ Pode acionar / ✏️ Corrigir" | T-97 |
