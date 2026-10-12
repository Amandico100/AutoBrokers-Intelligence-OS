# LAUDO I3 — os 3 cálculos, a página de renovação e o envio (SPEC-131)

> 🔍 Investigador I3 · modo INVESTIGAÇÃO (protocolo v13 §3.3/§8) · 12/10/2026 · árvore `AutoBrokers-FIX`, branch
> `investigacao/2026-10-12-renovacao`, HEAD `db87ad5` · READ-ONLY: só leitura de código e docs, 7 SELECTs no banco
> `dcajcvlzcjbmyapmklil` (só contagens e nomes de coluna, nenhuma PII), 1 leitura de artefato, 6 buscas na web. Nenhuma
> mensagem enviada, nenhum Agger, nenhuma InfoCap, nenhum modelo chamado.
> Cobre: PEDIDO-DO-FOUNDER §B itens 8 e 9, e §C na parte do WhatsApp do usuário.
> Legenda: **FATO** = arquivo:linha ou SELECT · **INF** = inferência · **REC** = recomendação com nota 0–100.

## 0. Resumo em 8 linhas

1. O motor JÁ calcula várias opções no mesmo negócio sem custo de tempo relevante; o que falta é a **opção "igual ao ano
   passado"**. O `de_apolice` não leva as coberturas da apólice anterior para o AUTO, e a comissão do ano anterior não entra em nenhum cálculo.
2. A regra atual de renovação da 130-A coloca **a menor completa em 1º** e a econômica como "Mais em conta". Isso **contradiz** o
   pedido do Founder, que quer a recomendada baseada no ano passado e nunca o mínimo. A 131 tem de trocar a regra de ordem para `situacao="renovacao"`.
3. O que "os clientes sempre pedem" está anotado em `ESTRATEGIA-COMERCIAL-DAS-CORRETORAS.md` §1.1/§1.4/§1.5 e em `A-PROVA-DO-AGGER.md`.
   Nas versões medidas, o que mais muda é a franquia (71), depois o desconto (54) e a comissão (33). A 3ª opção natural é a **completa+ (pequenos reparos)**, que é a D-MC-69.
4. A página da 130-A (a "carteira") serve de base: 1 template com uma variante de renovação, **não 3 templates**.
5. 🔴 Hoje **publicar uma renovação RECUSA nas 3 corretoras**: 📊 0/3 marcas com WhatsApp e 0 integração de atendimento ativa.
6. 🔴 A "131-0 parte B1" **não é** o WhatsApp do usuário para ENVIAR. A B1 serve para PEDIR pelo número verificado. Enviar e negociar pelo número do membro é a **B2**, que vai junto com a 135.
7. REC: a 131 entrega **"conferir e enviar" pelo `wa.me` no WhatsApp do próprio comercial** (sem pareamento), e o "Quero renovar"
   volta para o comercial dono. O pareamento por pessoa fica para a 135.
8. A 131 deixa a negociação preparada com o link rastreado (`share.viewed`/`share.clicked`), o estado do card e a métrica da D-MC-32.

---

## 1. Os 3 cálculos da renovação

### 1.1 O que o motor já sabe (FATO)
- **Presets AUTO** — `backend/portal_worker/multicalculo/presets.py`:
  - `_PADRAO` :40-56: franquia **REDUZIDA** (`tipoFranquia 1`), vidros completo, reserva 15 d, assistência completa, RCF 200/200/20 mil, APP 5 mil.
  - `_ECONOMICA` :61-67: franquia normal, vidros básico, 7 d, assistência básica.
  - `_COMPLETA_MAIS` :73-76: padrão + `reparoRapido`.
  - `_MINIMA` :90-93: econômica sem carro reserva.
  - Ordem do disparo `ORDEM` :102.
  - ⚠️ A **padrão do produto JÁ É franquia reduzida**. Então a opção (b) só difere da (a) quando a apólice anterior tinha franquia normal.
- **Presets RE** :151-252: `ORDEM_RE = (PADRAO, ECONOMICA)` :216, ou seja, só 2 opções. O ajuste de RE só muda comissão, desconto e
  assistência (`CAMPO_DO_AJUSTE_RE` :220). **Não existe "franquia reduzida" medida no RE.** `coberturas_re(..., extras=)` :229-252 aceita as
  coberturas da apólice anterior ("extras VENCE a opção"), mas **ninguém as preenche** (abaixo).
- **A renovação vira pedido** — `backend/app/services/multicalculo/pedido.py`:
  - `de_apolice` :702-739.
  - AUTO `_de_apolice_auto` :742-772 leva placa/chassi/ano, condutor e pernoite. **Não leva franquia, vidros, carro reserva nem
    RCF/APP da apólice anterior**: as coberturas saem do preset.
  - RE `_de_apolice_re` :775-802 leva só a Básica reajustada (`basica_renovada`, config `renovacao.reajuste_basica_pct`).
  - A ficha da 130-B tem as coberturas com `limite/franquia/premio` com origem (`backend/app/providers/policy_data_provider.py:471-501`).
    📊 A InfoCap sozinha não tem RCF/APP (`impseg` vazio, `A-PROVA-DO-AGGER.md:17` e §E2 :51-55).
- **A ordem das opções na renovação** — `backend/app/services/multicalculo/comparacao.py:925-1003`:
  - "🔴 A 1ª opção é SEMPRE a menor completa" (:938).
  - A seguradora atual entra como "Sua renovação" (:983-990).
  - "Mais em conta" = a menor entre econômica e mínima, se for mais barata (:991-998).
  - Depois vêm "Mais completa" (:999-1000) e "Menor franquia"/"Outra completa" (:962-972).
  - A mínima só entra com `incluir_minima` (:927, :956), que só o canal usa.
- **Quantas opções** — `config.py:74` `opcoes: {no_whatsapp: 2, na_pagina: 3}`, com mínimo 1 (`config.py:285-287`). A página
  corta em `na_pagina` (`comparacao.py:1012`).
- **Comissão**:
  - O preset AUTO não leva `percComissao`: a comissão vem da conta (`presets.py:89`).
  - O RE leva a comissão explícita por ramo (`config.py:40-53`, `comissao_do_ramo` :321).
  - A config tem `renovacao.comissao_a_mais_pp {1, 2}` (`config.py:57`), mas 📊 `git grep comissao_a_mais_pp` acha esse valor **só como texto do
    manual** (`manual_de_negociacao.py:201-202`). **Nenhum cálculo usa.**
  - A comissão do ano anterior existe na InfoCap: `/documento` `per_c val_c` (`131-0/LAUDO-CORPAPI-COMPLETA.md:216`).
  - O recálculo com `comissao → percComissao` já existe (`presets.py:110`).
  - ⚠️ Porto, Azul e Itaú **ignoram a comissão** e obedecem o desconto (`config.py:85`; `A-PROVA` E5 :78).
- **"Igual ao ano passado" no Agger**: o pedido marca `renovacao=True` e `seguradora_anterior` (`pedido.py:663-700`). Que o Agger
  tenha um botão "copiar o ano anterior" **não foi medido em lugar nenhum** (ver §6).

### 1.2 Onde estão "os ajustes que os clientes pedem" (FATO; a busca pedida)
`git grep` em `docs/canon` por "pedem / clientes pedem / franquia reduzida / carro reserva / pequenos reparos / comercial".

| fonte | o que está lá |
|---|---|
| `ESTRATEGIA-COMERCIAL-DAS-CORRETORAS.md:10-18` (§1.1 Renovação; 4 comerciais, nomes trocados por A–D) | manter o valor do ano anterior (ou um pouco menos) **e tentar AUMENTAR a comissão** (A, B, C) · opções: **A ≥ 3 (uma igual à apólice atual + 2–3 com melhorias) · B 2–3 (mais completa, franquia menor) · C 3–4 · D 2 (padrão + sugestão)** · 1ª alavanca quando o cliente pede mais barato: desconto comercial, "nunca abaixo cobertura" (A, C); franquia maior/carro reserva (B) · piso de comissão de 10 % |
| idem :31-34 (§1.4 o que convence) | **proteções · pequenos reparos · franquia menor · parcelamento longo no cartão · o atendimento no sinistro** · "me coloquei no seu lugar, por isso mandei também a opção tal" |
| idem :36-40 (§1.5 objeções) | melhorar o preço · **reduzir a franquia mantendo o valor** · outras seguradoras · "qual opção eu tenho hoje?" · banco/cooperativa · concessionária · parcelar mais · "ligo para quem?" · aplicativo |
| `A-PROVA-DO-AGGER.md:15` | 📊 o que mais muda entre as versões da equipe no Agger: **franquia 71 · desconto 54 · comissão 33** (137 recálculos) |
| `FOUNDER-DECISIONS.md:2242` D-MC-14 | 💭 3 em cada 5 renovações pedem ajuste, quase sempre de preço |
| `FOUNDER-DECISIONS.md:2370` D-MC-69 ✅ | com apólice: **igual à atual · econômica · completa+ (franquia reduzida e pequenos reparos)** |
| `129-C/AGREGADO-POR-RAMO.md` §2 | RE: o "mais em conta" da equipe = tirar acessórias e baixar a assistência (citado em `presets.py:139-142`) |
| "Ellen" | aparece só como dona do login do Agger nos testes (`ESTADO-DO-PROGRAMA.md:57`). **Nenhuma anotação dela sobre pedidos de cliente** |

**INF:** para quem já é cliente, as comerciais descrevem **igual ao ano passado + melhorias**: franquia menor, pequenos reparos e coberturas melhores.
Ninguém descreve "o mais barato possível". A ordem da 130-A (a menor completa primeiro, depois a econômica) é a lógica do cliente
NOVO (§1.2/§1.3).

### 1.3 O desenho recomendado

| opção | o que é | AUTO | RE (16/2/18) | nota |
|---|---|---|---|---|
| **(a) Recomendada = "Sua renovação"** | as coberturas da apólice anterior, **iguais ou melhores** (a ficha da 130-B mapeada para os códigos do Agger: franquia normal/reduzida, vidros, dias de reserva, RCF/APP, sempre arredondando para cima e nunca para baixo) + **comissão = `per_c` anterior + `comissao_a_mais_pp`** no item (explícita; nas que ignoram comissão, o desconto) · na página, a seguradora **atual** primeiro quando o preço dela fica até X % (config) da menor que cobre igual ou melhor; senão, a menor dessas | preset novo `anterior`, montado pela porta a partir da ficha | `coberturas_re(extras=ficha)` + a Básica reajustada (o caminho já existe) | **88** |
| (a') manter a regra da 130-A (a menor completa em 1º) | — | — | — | 55 — contradiz o Founder e as comerciais |
| (a'') a "padrão" do produto como recomendada | sem olhar a apólice | — | — | 60 — pode cobrir MENOS que o ano passado |
| **(b) Franquia reduzida** | (a) com `tipoFranquia 1`. Se a anterior **já era** reduzida, a opção não acrescenta nada (`_repete`, `comparacao.py:899-907`) e o lugar passa para a (c) ou a "Menor franquia" de outra seguradora | ✅ código medido | ⛔ **não existe toggle medido** → no RE a 2ª opção é a "padrão típica do ramo" (coberturas típicas, `presets.py:189-205`) | **85** AUTO · 62 RE |
| **(c) "O que os clientes pedem"** | (a) + **pequenos reparos** (`reparoRapido`, a completa+ da D-MC-69), com vidros completo e reserva 15 d quando a anterior tinha menos | ✅ preset existe | assistência completa (código 3, `presets.py:151`) 💭 | **82** AUTO · 58 RE |
| mínima / econômica | — | **NUNCA** na renovação (`incluir_minima=False` + guarda) | — | — |

- **1, 2 ou 3 opções, configurável**: a lista ordenada `servicos.renovacao.opcoes = ["anterior","franquia_reduzida","completa_mais"]`
  sobre o `opcoes.na_pagina` que já existe. Com 1 opção, só a (a). **86** (× fixo em 3: 60).
- 💭 A regra das 2 opções da mensagem (D-MC-74) continua: (a) + (b).

### 1.4 Quanto custa calcular 3 (FATO + INF)
- **Não sai num envio só.** 📊 "1 pacote por cálculo → a proposta de 2 opções custa 2 cálculos" (`A-PROVA-DO-AGGER.md:16`, E6 :88-90).
  Cada opção é uma versão `calcularV2` no MESMO negócio.
- O motor **dispara em série** (só o POST, poucos segundos; `motor.py:1064-1089`, ordem pelo preset :103) e **acompanha em PARALELO**
  (`asyncio.gather`, `motor.py:881-882`). 📊 2 cálculos simultâneos na mesma sessão fecharam 16/16 em 45 e 44 s (`A-PROVA` E7 :93).
- 📊 Um cálculo: cerca de 45 s no relógio do servidor; mediana de fechamento 64 s, p90 406 s por causa da cauda de 1–2 seguradoras (`A-PROVA:13, :29`).
  RE 46–48 s do POST ao último preço; login 54 s (`129-C/CANARIO-AO-VIVO.md:42-43`).
- **INF:** 3 opções ≈ 1 opção + cerca de 5–10 s 💭 de disparos, mais uma sessão por grupo (o login vale para o grupo). Por renovação, 💭 1,5–2,5 min
  por Agger, com a sessão aberta uma vez. Com 📊 217 renovações em 30 dias na maior carteira (BLOCO 0 da 131-0), dá 💭 cerca de 10 por dia útil, ou 💭 15–25 min por login
  por noite. **O custo de 3 em vez de 1 é ~0 no relógio**; o que pesa é a cauda das seguradoras lentas e o login.
- ⚠️ O canário da 130-A.1 (📊 495 s até o último preço, `config.py:137`) teve fila do robô + corretoras em série com concorrência 1. Não é
  o tempo de uma renovação.

---

## 2. A página de apresentação de RENOVAÇÃO

### 2.1 O que existe (FATO)
- **A página da 130-A** — `backend/app/services/artifacts/proposta_html.py`, `render_proposta` :811-1117, na ordem:
  - topo com marca e nota do Google (:841-858)
  - h1 "Nome, a melhor das N…" (:860-871)
  - carrossel de passes (:880-886)
  - régua `_regua` (:581) e **comparar lado a lado** `_comparar` (:647)
  - "Todas as seguradoras que cotamos" + produto diferente + não responderam + duelo entre corretoras (:888-947)
  - "Quem vai cuidar do seu seguro": anos, SUSEP, cidade, tagline, WhatsApp, site (:949-991)
  - "Se acontecer alguma coisa" (:993-999)
  - FAQ (:1000-1002)
  - "Pronto para fechar?" (:1034-1041)
  - legal com validade (:1004-1009)
  - dock fixo "Tirar uma dúvida" / "Quero fechar" (:1020-1031)
  - Funciona sem JS; o script vai por hash na CSP (`HASH_DO_SCRIPT` :237).
- **O artefato do QCM v1** (`claude.ai/artifact/K3pGqdMQ9dvThA7r6AZSZC`, lido em 12/10): o mesmo desenho "carteira" (D-130A-11, 4 rodadas,
  📊 91/90). `proposta-com-marca.html` tem a mesma sequência de seções, com nota 0–100 por cartão, "O que muda em relação à recomendada"
  e "Mostrar só o que muda" no lado a lado.
- **Renovação já prevista no modelo**:
  - rótulo "Sua renovação" (`comparacao.py:983`)
  - FAQ "qual tenho hoje" (`proposta.py:585`)
  - a recusa de rotular "igual" sem a apólice atual (`comparacao.py:914-922`)
  - ⚠️ P-130A-21: a mensagem não cita o preço de renovar
  - ⚠️ P-130A-22: com apólice, a "Mais completa" sai do carrossel
- **Identidade** (`proposta.montar_anfitria`, `backend/app/services/multicalculo/proposta.py:528-563`) lê de `brand_profiles`:
  - `display_name`, `palette.themes` (claro/escuro), `logo_asset_id` (embutido em `data:`), `service_area`, `tagline`, `founded_year`, `susep_code`,
    `website_url`, `contact.whatsapp`
  - o Google só quando a corretora confirmou (`config.google_confirmado`, :514-525)
  - A tela: `app/dashboard/personalizacao/corretora/identidade/BrandIdentityClient.tsx` (rótulos :130-144: frase de marca, SUSEP, "Desde",
    cores, logo, jeito de atender, site).
  - 📊 SELECT 12/10 em `brand_profiles` (3 linhas): publicada 2/3 · logo 2/3 · SUSEP 2/3 · `founded_year` 1/3 · **`contact.whatsapp` 0/3**.
- **Prévia e PDF**:
  - prévia PNG 1200×630 sem dado pessoal (`proposta_previa.py`; rota `app/r/[token]/previa.png/route.ts`)
  - og:image injetada na hora de servir (`proposta_html.py:1123-1146`)
  - **PDF = imprimir do navegador** (D-130A-07, `FOUNDER-DECISIONS.md:2385`); PDF gerado no servidor **não existe**.

### 2.2 "N anos juntos": de onde vem (FATO + INF)
- `/cliente` **não tem** campo "cliente desde": `codfil codigo nome ativo cpf_cnpj datanas … vigente observacoes profissao … dt_venchab`
  (`131-0/LAUDO-CORPAPI-ROTA-A-ROTA.md:59`).
- Há duas fontes possíveis:
  - `/documento.historico[]` = `codfil nosnum tipdoc numapo numend inivig fimvig qtd_endossos nosnum_ren nosnum_endosso renovado` (:30-32),
    com `nosnum_ren` = o documento ANTERIOR que esta apólice renova (:147). Isso dá a cadeia da MESMA apólice.
  - `/cliente_ligacoes` = todos os documentos do cliente, com `dat_inc` (:66).
- **INF (💭 75):** "cliente desde" = o menor `inivig` entre os documentos do cliente em `/cliente_ligacoes` (vale mesmo quando o cliente teve outro bem). A cadeia
  `nosnum_ren` dá "renova com a gente há N anos" só para este bem. **Nenhum dos dois foi medido** (§6). Regra: sem prova, a frase NÃO
  aparece (CDC art. 37, como o Google só confirmado). O "N anos atendendo" da CORRETORA já existe (`founded_year`, `proposta_html.py:953-956`).

### 2.3 Seções: obrigatórias × irrelevantes para quem JÁ é cliente (REC)

| seção | renovação | por quê |
|---|---|---|
| hero pessoal: "Mariana, a renovação do seu Compass está pronta" + vencimento da apólice | **obrigatória** | o motivo da página é o vencimento; o h1 atual ("a melhor das N") é discurso de cliente novo |
| **o seu seguro hoje × a renovação** (seguradora, quanto pagou, franquia, coberturas; "o que mudou" em R$ e %; reajuste da Básica no RE dito por extenso) | **obrigatória, nova** | é o "lado a lado" que importa (EZLynx, §5); responde a objeção 4 ("qual eu tenho hoje?") |
| 3 cartões (a)(b)(c), com nota e "por que recomendamos" | obrigatória (reaproveita `_passe`) | — |
| comparar lado a lado "Mostrar só o que muda" | obrigatória (`_comparar`) | NN/g: ≤ 5 itens, cabeçalho preso (§5) |
| relação: "N anos juntos" (só com prova) + "quem cuida de você" com o **comercial dono** (nome, WhatsApp dele) | obrigatória | a relação vende a renovação (§1.4 "estou sempre com o celular") |
| sinistro "quem cuida é a corretora, não um 0800" | obrigatória | §1.4 |
| FAQ de renovação (reajuste, bônus, "posso mudar a franquia?", "e se eu não renovar?", parcelar) | obrigatória, com outra lista | as objeções de cliente novo (banco/cooperativa) saem |
| "Pronto para renovar?" + dock "Quero renovar" / "Tirar uma dúvida" | obrigatória | — |
| "Todas as seguradoras que cotamos" (ranking inteiro) | **recolhida** (`<details>`) | 💭 para o cliente da casa, o ranking inteiro convida a trocar de seguradora; mostra-se recolhido como prova de trabalho |
| duelo entre corretoras · "O que é o QCM?" · selo "Comparação independente" | **NUNCA** | é página do canal (D-130A1-01/08) |
| nota do Google | opcional (desligada por padrão) | quem já é cliente não precisa de prova social de estranho |

### 2.4 Templates e formato (REC)
| opção | nota | porquê |
|---|---|---|
| **1 template ótimo (a carteira) + variante de renovação** | **88** | 📊 a carteira já mediu 91 (`SPEC-130-A` §3); só as frases mudam por `situacao`. A lição da 130-A: 186 testes verdes com 4 frases mentirosas, e 21 guardas sobre o HTML servido para UM template |
| 1 layout + 2–3 "temas" (paleta/tipografia por `css_do_tema`) | 72 | o visual muda sem multiplicar as guardas; fica para a SPEC de layout |
| 3 templates (elegante · luxuoso · "wow" com animação) | **45** | 3× crítica, guardas e CSP; animação briga com "funciona sem JS" e com o script por hash; nenhuma evidência de que converte mais |
| **link `/r/` (rastreado)** como entrega principal | **90** | `share.viewed` / `share.clicked` medem abertura e intenção (§4); a prévia já existe |
| botão "Salvar PDF" = imprimir (o CSS de impressão que já existe) | 70 | o comercial que precisa anexar tem como |
| PDF gerado no servidor | 40 agora | não existe; D-130A-07 adiou |

---

## 3. O envio

### 3.1 O que existe (FATO)
- **A mensagem pronta**: `mensagem.mensagem_whatsapp` (`backend/app/services/multicalculo/mensagem.py:166`), com ≤ 2 opções + link (D-MC-74).
- **Publicar recusa sem WhatsApp**: `publicar_proposta` (`proposta.py:959-994`). O número vem de `_whatsapp_da_anfitria` (:462-483):
  1º `contact.whatsapp` da marca publicada, 2º a integração `purpose='attendance'` ativa; ⛔ o observer não entra.
  📊 SELECT 12/10 em `integrations` (8 linhas): **0 de atendimento ativa** (todas `retired`/`close`); observers conectados 3, dois deles
  com `permite_envio_de_auxiliar=true`. Somando `contact.whatsapp` 0/3: **hoje uma renovação não publica em nenhuma corretora** sem
  `--sem-whatsapp` (P-130A-01 segue aberta).
- **"Quero fechar"** vai para o `wa.me` **da corretora** (`proposta_html.py:1155-1175`, `destino_do_fechar` :1210-1240) e registra
  `share.clicked` (`backend/app/api/artifacts.py:177-183`; rota `app/r/[token]/route.ts:93-100`). 📊 `artifact_events` em produção:
  tipos `artifact.* · share.created · share.viewed · version.published`, **0 `share.clicked`**; `artifact_shares` = 2.
- **O modo do serviço**: `servicos.renovacao.modo = "calcular"` (padrão), com as alternativas `calcular_entregar` e `calcular_entregar_negociar`
  (`config.py:174-186`, `modo_do_servico` :551-573).
- **Cobrança (o molde)**: `send_mode` ∈ `test · none · equipe · cliente` (`billing_collection.py:693-696`); `cliente` exige
  confirmação explícita; os legados `approval/live` → `retido_legado` ("nunca promovidos automaticamente", :686-692).
  O envio de auxiliar sai pela conexão com `permite_envio_de_auxiliar` (`platform_outbound.py:1259-1289`,
  `integration_service.py:223`).
- **133-A**: o canal usa a própria integração (`canal.envio.numero_do_canal`, `proposta.py:486-499`). Não serve à carteira.
- **WhatsApp por pessoa: não existe.** 📊 SELECT 12/10:
  - `integrations` não tem coluna de dono-pessoa (colunas: `company_id, provider, purpose, agent_id, paired_phone_e164, …,
    permite_envio_de_auxiliar`)
  - `company_internal_numbers` tem **0 linhas** e nenhum vínculo com usuário (`SPEC-131-0…md:94`)
  - `company_members.funcoes` está preenchido em 0 de 10
  - `users_v2.phone` está preenchido em 1.169 de 1.169 (mistura membros e leads, sem verificação; a 131-0 já registra que os leads saem dos usuários)
- 🔴 **O que a 131-0 chama de B1 e B2** (`docs/canon/specs-propostas/SPEC-131-0-CONTAS-COMERCIAIS-E-CONEXOES.md`):
  - **B1** = "pedir pelo WhatsApp (com a 132): número verificado do membro → a mesma ferramenta de cotação do chat" (:379, V25 :209-211,
    V37 :237). **B1 não envia nada ao cliente.**
  - **B2** = "negociar pelo WhatsApp do membro (com a 135): instância com dono = pessoa, filtro das conversas pessoais" (:380,
    V26 :212-214: o agente veria TODAS as conversas pessoais; privacidade e risco de bloqueio são do membro, com aceite).
  - D-131-0-11: "dois usos separados" (:350, nota 90).
  - O PEDIDO §B9 chama de B1 o que é **B2**.
- O plano da 131: "**Envio: é ação do corretor**" (`PLANO-MESTRE-MULTICALCULO.md:745`).

### 3.2 As opções para a 131 (REC)
| opção | o que é | nota |
|---|---|---|
| **A · "Conferir e enviar" pelo `wa.me` no WhatsApp do próprio comercial** | no card da renovação (celular ou notebook), o botão abre `https://wa.me/<telefone do cliente>?text=<mensagem pronta + link /r/>` no WhatsApp **do aparelho de quem clica**; o comercial confere e toca "enviar". O produto registra "aberto para envio por <pessoa>" e o card passa a "enviada". Zero pareamento, zero risco de bloqueio, e a mensagem sai do número que o cliente já conhece | **90** |
| A' · "Copiar a mensagem" + "abrir conversa" (o par de A) | quando o texto não cabe no `wa.me` ou o telefone falta | 80 (complemento obrigatório de A) |
| B · envio automático pela conexão da CORRETORA (`calcular_entregar`, molde da cobrança: `platform_outbound` com autorização de auxiliar) | exige número de atendimento/observer autorizado (📊 hoje 2 observers autorizados e 0 atendimentos), opt-in/LGPD, rito CRÍTICO (envio ao segurado), e o cliente recebe de um número que pode não conhecer | 62 — deixar a chave pronta e **desligada**; ligar por corretora depois do canário |
| C · parear o WhatsApp de cada usuário (Evolution GO por pessoa, B2) já na 131 | instância por pessoa, filtro de conversas pessoais, aceite, risco de bloqueio do número pessoal, e o Founder já pôs a B2 com a 135 | **40** |
| **D · o "Quero renovar" e o "Tirar uma dúvida" vão para o COMERCIAL DONO** (telefone do membro, vindo do vínculo da 131-0) e, sem ele, para a corretora | resolve a recusa de publicar (hoje 0/3) sem precisar do número de atendimento, e o cliente fala com quem ele já conhece | **80** |

**REC final:** a 131 entrega **A + A' + D**; **B** fica construída como modo `calcular_entregar` desligado (o que já existe na config);
**C** vai para a 135 (B2). Para A e D faltam:
1. o telefone do cliente, de `/renovacoes.fone` (📊 71/99 linhas, `LAUDO-CORPAPI-ROTA-A-ROTA.md:198`) ou de `/cliente.telefones`.
   É PII: guardar só cifrado ou buscar na hora, e nunca em log.
2. o telefone do membro, verificado uma vez (é o "número verificado" da V37; serve depois à B1).

---

## 4. Negociação: o que a 135 prevê e o que a 131 deixa pronto
- **FATO, a 135** (`PLANO-MESTRE-MULTICALCULO.md:820-827`):
  - a ferramenta "proposta" no agente de atendimento, com dois modos (renovação e seguro novo)
  - o dossiê de fechamento e as regras de parada (`HumanHandoffTool`, `enviar_ao_grupo` e o Skill Registry já existem)
  - entra quando o atendimento estiver ligado e a **D-MC-32** for cumprida: liga depois de 💭 50 propostas medidas "com pouca edição" (:406)
- **FATO, as peças da negociação que já existem**:
  - `negociacao.py` (`ordem_do_mais_barato`, `cotacao_alvo`/`avaliar_cotacao_alvo`) e `manual_de_negociacao.py`
  - a config da margem `comissao.entrada/autonomo_minimo/piso/passo_pp` (`config.py:40-53`)
  - o recálculo no mesmo negócio e na mesma conta (D-128-03; V20 da 131-0)
- **REC: o que a 131 deixa preparado** (nota 85 para o conjunto):
  1. **O link rastreado** já existe. A 131 lê `share.viewed` (abriu) e `share.clicked` + a opção (quer renovar) **para mudar o estado do card**:
     calculada → conferida → enviada → aberta → quer renovar → renovada/perdida.
  2. **"Quero renovar"** com o texto pronto da opção (`_texto_do_fechar`, `proposta_html.py:1178-1207`), que vai para o comercial dono (D, §3.2).
  3. **O evento de envio** ("aberto para envio por <pessoa>", com a versão da proposta) → a métrica da D-MC-32: 📊 % enviadas sem
     recálculo/ajuste antes do envio, e % de clientes que pedem ajuste (o "pronta quando" do plano, `PLANO:750-751`).
  4. O `pedido_id` e o `negocio_ref` no card, para o agente da 135 recalcular **na mesma conta do Agger** e versionar a proposta.
  5. 💭 A pergunta "o que o cliente respondeu?" registrada pelo comercial em 1 toque (aceitou · pediu ajuste: preço/franquia/
     cobertura · não respondeu). É o acervo de exemplos de conversa que a 135 precisa (PEDIDO §B10).
- ⛔ Fica para a 135: o agente falando com o cliente, o recálculo pedido em conversa e o fechamento.

---

## 5. Referências externas (inspecionadas em 12/10/2026)
1. **EZLynx — Renewals & client retention**: https://int.ezlynx.com/solutions/renewals-client-retention — trecho:
   "summarizes premium-bearing changes between the insured's current policy and the carrier's renewal offer … side-by-side
   comparison highlighting all the pertinent differences". → o bloco **"o seu seguro hoje × a renovação"** (§2.3).
2. **Nielsen Norman Group — Comparison Tables**: https://www.nngroup.com/articles/comparison-tables/ → "use comparison tables for up to
   5 items", consistência de atributos, cabeçalho preso, cor com parcimônia. Confirma 3 cartões e o "Mostrar só o que muda".
3. **Bird — WhatsApp click-to-chat link**: https://bird.com/explained/whatsapp/what-is-a-whatsapp-click-to-chat-link → formato
   `https://wa.me/<número>?text=<texto codificado>`; afirma ⚠️ "Meta limits prefilled messages to 140 characters". **Conflita** com o
   `_TEXTO_MAXIMO = 500` da 130-A (`proposta_html.py:1152`) → medir (§6). Daí o A' "copiar a mensagem".
4. Já no repositório, para o desenho: `ESTRATEGIA-COMERCIAL-DAS-CORRETORAS.md:66-69` (lemonade.com, airbnb.com.br bloco
   "anfitrião", apple.com/br/iphone/compare).
- ⚠️ Uma 5ª fonte (parloa.com, "2–3 opções: básica, igual ao ano passado, melhorada") apareceu no resumo da busca, mas a página
  **não traz** essa frase quando lida. Por isso NÃO foi citada como fato.

---

## 6. O que ficou por medir (nenhuma chamada foi feita: modo read-only)
1. **"Cliente desde"**: `/cliente_ligacoes` (o menor `inivig`) × a cadeia `nosnum_ren` em ~10 renovações. Ver se a data sai coerente e
   quanto custa (1 chamada por cliente?).
2. **`per_c` do ano anterior** em `/documento`: em quantas das 📊 99 renovações vem preenchido, e se é % da corretora (não do produtor).
3. **A ficha → os códigos do Agger (AUTO)**: nas 📊 6/6 apólices AUTO lidas pela 130-B, extrair franquia (normal/reduzida), vidros,
   dias de reserva e RCF/APP, e mapear para o preset `anterior`. É a peça que falta para a (a).
4. **O Agger tem "copiar a apólice anterior"/importar renovação?** Uma tela, nenhuma escrita.
5. **O `wa.me` com cerca de 500–700 caracteres** (Android, iOS, WhatsApp Web, Desktop): o texto chega inteiro? O limite de 140 é real?
6. **3 opções de RE no mesmo negócio**: hoje só existem 2 presets de RE. Medir se o Agger aceita a 3ª versão e se as seguradoras recusam
   a "anterior" (limites relativos à Básica, `presets.py:143-148`).
7. **A comissão "melhor" de verdade**: em quantas seguradoras o `percComissao` explícito mais alto muda o prêmio (Porto, Azul e Itaú ignoram;
   📊 E5 mediu só de 15 para 10 %, nunca para cima).
8. **O tempo de 3 opções às 3h** num login de comercial com cerca de 10 renovações: o relógio total e a cauda.

## 7. Pendências que este laudo sugere ao gerente (P-131-I3-*)
- 01 🤖 trocar a ordem das opções para `situacao="renovacao"` (a "Sua renovação" iguais-ou-melhores em 1º; nunca econômica/mínima), com guarda no
  HTML SERVIDO (lição da 130-A).
- 02 🤖 preset `anterior` (AUTO) + `extras` do RE preenchidos pela ficha; comissão anterior + `comissao_a_mais_pp` de fato aplicada.
- 03 🧑/🤖 o telefone verificado do membro (V37) e o "Quero renovar" indo para o dono; sem ele, a corretora; sem nenhum dos dois, a recusa de hoje.
- 04 🧑 `contact.whatsapp` no cadastro de marca (📊 0/3), que continua sendo o fallback (T-125).
- 05 🤖 os estados do card alimentados por `share.viewed`/`share.clicked` + o evento "aberto para envio".
- 06 🤖 corrigir no PEDIDO/plano: "WhatsApp do usuário para ENVIAR" = **B2** (com a 135), não B1.
