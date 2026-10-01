# TAREFAS DO FOUNDER — a lista única

> 🔴 **Desde 01/10/2026, os TESTES estão todos na seção logo abaixo (T-01 a T-81).** Os blocos mais antigos, depois dela,
> guardam o contexto, as decisões e as tarefas que não são teste; onde havia um teste, agora há uma seta **→ T-NN**.

## 🧪 A LISTA ÚNICA DOS TESTES (atualizada 01/10/2026)

> **Para que serve:** é a fila de testes para você fazer **um por um**, ajustar o que não funcionar e, no fim, ligar os
> agentes na vida real. Ela junta **todos** os testes pendentes das SPECs 116 → 124 e das EXTRA-001.1 → 001.10.1, das
> caixas do Founder dos relatórios e das pendências 🧑 de teste/canário/acionamento real. **Esta lista é a verdade**: nos
> blocos antigos mais abaixo, cada teste virou só uma seta **→ T-NN** que aponta para cá.
>
> **Como usar:** siga a ordem dos grupos — cada grupo só depende dos anteriores. Marque `[x]` no que passar. No que falhar,
> cole no chat **o número do teste** (ex.: *"T-43 falhou"*), o horário e o print — nunca o CPF ou o nome de um segurado.
>
> **Status:** ⏳ pendente · ✅ feito. Só está ✅ o que já se sabe feito: o Implantar das SPECs 123 e 124 e a conferência do
> `cerebro_modos`, que você fez em 01/10/2026.
>
> **Onde:** **painel** = `https://autobrokers-intelligence-os-autobrokers-smith-web.golhpm.easypanel.host` · **EasyPanel** =
> onde se clica Implantar e se editam as variáveis (o `smith-worker` usa o mesmo bloco do `smith-api`) · **SQL** = Supabase →
> projeto *AutoBrokers Intelligence OS* → **SQL Editor** (todos os SQL desta lista são só leitura, salvo onde está escrito).
>
> 🔴 **Freio de emergência, se algo sair do controle:** `ACIONAMENTO_FREIO_DE_EMERGENCIA=true` no `smith-api` derruba todo
> acionamento. **Se um modelo piorar** (memória, foto, portal): peça no chat *"volte a rota X para a linha anterior"* — vale em
> até 1 minuto, sem Implantar.

**Os 9 grupos, na ordem:** ① Implantar e conferir · ② Chat principal · ③ Atendimento no WhatsApp com o agente ligado ·
④ Acionamento por seguradora · ⑤ Portal de vidros · ⑥ Grupo de suporte · ⑦ Leitura de foto e documento · ⑧ Cobrança ·
⑨ Desfazer o ensaio e ir para a vida real.

### ① Implantar e conferir — não depende de nada

- [x] **T-01** ✅ **Implantar o código de hoje** — `docling-service` (o worker antes da API) → `smith-api` → `smith-worker` →
      `smith-web`. **Feito em 01/10/2026.** Vale por todos os Implantar pedidos antes, porque o Implantar sobe a `main` inteira.
      · *de:* S116.2 · 0.2 · F.1 · G.1 · I.1 · J.1 · S120.1 · S121.1 · S122.1 · S123.1 · S124.1
- [ ] **T-02** ⏳ **O que está no ar é o código de hoje — inclusive o `portal-worker`**
      **Como:** peça no chat *"rode o conferir o que está no ar"*. E abra
      `https://autobrokers-intelligence-os-portal-worker.golhpm.easypanel.host/health`.
      **Esperar:** **BATE** para cada serviço. No `portal-worker`, um `build_time` de **24/09/2026 ou depois** (📊 o último
      código dele é o commit `79c9e80`, de 24/09). Se for anterior: EasyPanel → `portal-worker` → **Implantar** (demora mais).
      · *de:* S116.2 · F.1 · gate G9 da 119 · P-E0017-02 · P-E0017-11
- [ ] **T-03** ⏳ **A saúde do `smith-api`**
      **Como:** abra `https://autobrokers-intelligence-os-autobrokers-smith-api.golhpm.easypanel.host/health`.
      **Esperar:** `scheduler` = **`lider`** · `executor_threads` com um número (32 ou mais) · `finalize_refs_fantasma` vazio ·
      `finalize_abre_de_verdade` = **false** enquanto você testa (ver T-08).
      **Se vier `seguidor` ou `desligado`:** há outro processo com o agendador ligado, ou `SCHEDULER_ENABLED=false`.
      *Opcional (G.3):* no console do `smith-api`, `python -c "import os; print(os.cpu_count(), min(32,(os.cpu_count() or 1)+4))"`
      → dois números; nada a fazer, é só para saber. · *de:* G.2 · G.3 · J.3 · 001.8
- [ ] **T-04** ⏳ **O crédito das APIs e a recarga automática**
      **Como:** `console.anthropic.com` → Settings → Billing · `platform.openai.com` → Settings → Billing.
      **Esperar:** saldo positivo e **auto-reload / auto recharge ligado** nas duas. (📊 01/10 os testes da 124 rodaram, então
      havia crédito; a recarga automática ninguém conferiu.) · *de:* S116.1
- [x] **T-05** ✅ **O destravador ligado** — `select insurer_key, modo, limiar from cerebro_modos order by 1;` → 40 linhas
      `on`, limiar 70. **Conferido por você em 01/10/2026.** · *de:* S123.3
- [ ] **T-06** ⏳ **O modelo reserva de cada trabalho** (SQL):
      ```sql
      select papel, provider, modelo_primario, provider_reserva, modelo_reserva, esforco_reserva
        from public.llm_papeis where modelo_reserva is not null order by papel;
      ```
      **Esperar:** 📊 **7 linhas** (lido em 01/10): `atendimento`, `chat_principal` e `portal_decisao` (gpt-6.1-sol → reserva
      claude-opus-5-5) · `destravador` (gpt-6.1-sol → claude-sonnet-5-5) · `destravador_segunda` (claude-sonnet-5-5 →
      gpt-6.1-sol high) · `dispatch` (claude-opus-5-5 → gpt-6.1-sol high) · `visao` (gpt-6-luna → claude-sonnet-5-5 low).
      **No dia em que a reserva entrar de verdade**, para ver quando e por quê:
      ```sql
      select created_at, details->>'papel' papel, model_name, details->>'motivo_reserva' motivo
        from public.token_usage_logs where details->>'reserva_usada' = 'true' order by created_at desc limit 20;
      ```
      · *de:* S116.11 · SPEC-116-RESERVA · S124 (reserva da visão)
- [ ] **T-07** ⏳ **A faxina das variáveis de modelo** (EasyPanel → `smith-api` → Environment; o `smith-worker` usa o mesmo
      bloco). **Apague as que existirem:** `PORTAL_VISION_MODEL` (também no `portal-worker`) · `DISPATCH_LLM_PROVIDER` ·
      `DISPATCH_LLM_MODEL` · `ATLAS_PARSER_PROVIDER` · `ATLAS_PARSER_MODEL` · `DISTILLER_PROVIDER` · `DISTILLER_LLM_MODEL` ·
      `DISTILLER_STRONG_MODEL` · `COUNCIL_LEADER_PROVIDER` · `COUNCIL_LEADER_MODEL` · `SUGESTOES_LLM_PROVIDER` ·
      `SUGESTOES_LLM_MODEL` · `GARIMPO_LLM_PROVIDER` · `GARIMPO_LLM_MODEL` · `EVAL_JUDGE_MODEL` · `EXTRATOR_PLANOS_PROVIDER` ·
      `EXTRATOR_PLANOS_MODEL` · `BRAND_CAPTURE_PROVIDER` · `BRAND_CAPTURE_MODEL` · `AUXILIAR_LLM_MODEL`.
      **Abra e confira:** `COUNCIL_MEMBERS` (`smith-api`) — se tiver `gpt-6-sol`, troque por `gpt-6.1-sol`.
      `VISION_MODEL` (`docling-service`) **pode ficar como está** (desde a 124 ela só vale se quem chama não mandar o modelo).
      🔴 **NÃO apague** `GARIMPO_LLM` nem `SUGESTOES_LLM` (sem sufixo): são o liga/desliga. Depois, **Implantar** o serviço
      que mudou. **Esperar:** nada muda na tela — é para ninguém trocar uma delas achando que troca o modelo.
      · *de:* S116.7 · S116.11 · S121.3 · S122.2 · P-121-07 · P-122-02
- [ ] **T-08** ⏳ **As variáveis do ensaio** (EasyPanel → `smith-api` → Environment; faça todas e Implante uma vez):
      (a) `JANELA_SILENCIO_EXCECOES` — tire o item que **não** é número de teste (📊 20/09: 1 de 2);
      (b) `ENV` e `ENVIRONMENT` — o mesmo valor de produção nas duas;
      (c) `PRESENCA_DIGITANDO_LIGADA=true` — só se quiser o T-34;
      (d) `ATTENDANT_INBOUND_ALLOWLIST` — **vazia** agora (ela só é preenchida no T-23);
      (e) `DISPATCH_FINALIZE_MODE=test` **enquanto testa** (com `live`, todo corredor abre chamado de verdade e a lista
      `DISPATCH_FINALIZE_LIVE_PLAYBOOKS` é ignorada). **Esperar:** no T-03, `finalize_abre_de_verdade` = false.
      · *de:* 0.1.a · 0.1.b · 0.1.c · 0.1.d · J.3/D-118-01 · 001.7

### ② Chat principal — no painel, nada sai por WhatsApp

**Onde:** painel da **Resulta** (a InfoCap só abre apólice nela — F-094-07), chat `core`, com a sua conta. Anote cada um como
✅ passou · ⚠️ passou com texto estranho · ❌ falhou (cole a resposta).

- [ ] **T-09** ⏳ **"oi"** no chat → resposta em segundos. É a prova de que o Implantar pegou.
      **Se der erro de modelo** (`sonnet`, `gpt-6.1-sol`, `effort`, `destravador`, `diario_de_decisoes`): mande o print.
      · *de:* 0.3 · S116.2 · S120.1 · S121.1 · S122.1 · S123.1 · S124.1
- [ ] **T-10** ⏳ CPF do cliente que em 09/09 recebeu 4 apólices → **uma** rodada, **zero** vencidas, diz **por que** é aquela e
      avisa que há histórico oculto · *de:* 001.1 (D.1)
- [ ] **T-11** ⏳ *"quais as coberturas da apólice residencial dele?"* (a HDI) → coberturas **com a origem por linha**,
      Assistências Essenciais com origem no documento, franquia certa · *de:* 001.1 (D.2)
- [ ] **T-12** ⏳ CPF só com apólices vencidas → a frase de "sem vigente", **com a data** · *de:* 001.1 (D.3)
- [ ] **T-13** ⏳ CPF com duas vigentes do mesmo ramo → pergunta **uma vez**, mostrando as duas · *de:* 001.1 (D.4)
- [ ] **T-14** ⏳ a pergunta que em 10/09 devolveu *"ainda não recebi uma pergunta sua"* → agora responde · *de:* 001.1 (D.5)
- [ ] **T-15** ⏳ 🔴 **controle:** *"quantos clientes eu tenho?"* → a ferramenta de apólice **não** é chamada · *de:* 001.1 (D.6)
- [ ] **T-16** ⏳ o caso do residencial Allianz de 10/09: prêmios, franquias, coberturas → **da vigente**, com origem por linha
      · *de:* 001.1 (D.7)
- [ ] **T-17** ⏳ depois de consultar uma apólice, pergunte *"Ela cobre eletricista?"* → responde **sem** consultar de novo (era
      um laço de 7 consultas) · *de:* S116.9 passo 6
- [ ] **T-18** ⏳ **Painel → Personalização → Conhecimento** → bloco **Cobertura dos planos** com 8 seguradoras e 20 combinações;
      **Fila de curadoria** com **8 linhas e só elas** (táxi da Azul, retidas de propósito). Nome de tabela, coluna ou SQL na
      tela = defeito · *de:* 001.5 (D2.0)
- [ ] **T-19** ⏳ trocar de corretora no topo e voltar → os números do T-18 são **os mesmos**, e a tela diz numa linha por quê (a
      base é global) · *de:* 001.5 (D2.1)
- [ ] **T-20** ⏳ com **uma apólice real de cada seguradora**, pergunte no chat: *"meu seguro cobre guincho? até quantos km?"* ·
      *"tenho carro reserva?"* · *"cobre chaveiro?"* · *"cobre vidraceiro?"* (residencial) → sim/não **com o limite** (km, diárias,
      R$ por evento), mais o documento e a página. 🔴 Se vier *"ainda não sei"* numa apólice que **tem** plano, copie **exatamente**
      como o nome do plano aparece na apólice + a seguradora (P-E00152-07). **Não é defeito:** Mapfre auto "ainda não sei" ·
      Allianz moto/caminhão/frota · Bradesco condomínio · seguradora sem documento. (Tabela por seguradora:
      `reports/SPEC-EXTRA-001.5-CANARIO-PASSO-A-PASSO.md` §B.) · *de:* 001.5.2 (D2.2 · D2.3)
- [ ] **T-21** ⏳ 🔴 **controle:** *"quantas parcelas faltam para o segurado tal?"* → responde sobre parcelas e **não** consulta a
      base de planos · *de:* 001.5 (D2.4)
- [ ] **T-22** ⏳ 20 minutos com as duas atendentes do piloto: *"dá para conferir de onde veio a resposta?"* · *"'ainda não
      sabemos' soa honesto ou soa falha?"* · *"o gancho do plano superior soa útil ou soa empurrão?"* · *de:* 001.5 (D2.5)

### ③ Atendimento no WhatsApp, com o agente ligado numa corretora de teste

**Onde:** o celular de teste escrevendo ao WhatsApp da **corretora de ensaio**. Nada aqui usa número de cliente.

- [ ] **T-23** ⏳ **Preparar o ensaio** (uma vez só):
      (1) `ATTENDANT_INBOUND_ALLOWLIST` (`smith-api`) com **só** o número do celular de teste → Implantar;
      (2) criar um grupo de WhatsApp só com você e cadastrá-lo em **Personalização → Suporte humano** da corretora de ensaio;
      (3) cadastrar o seu celular como **número da casa** dessa corretora (é o que o T-62 usa);
      (4) parear o celular pessoal como atendente (painel → conexão de WhatsApp → QR) — **depois** do passo 1.
      **Esperar:** o destino aparece ativo; o número da casa aparece na lista. · *de:* 1.2 · 1.3 · 1.4 · 1.5 · 0.1.d · S116.9 passo 1
- [ ] **T-24** ⏳ **O checklist, em modo canário** — peça no chat *"rode o checklist de ligar em modo canário"*.
      **Esperar:** **PODE LIGAR**, uma linha por trava. O que ele não consegue conferir conta como trava fechada, de propósito.
      · *de:* 001.7 (P1)
- [ ] **T-25** ⏳ **Ligar o agente da corretora de ensaio** — botão **Ligar agente**. No painel de administração, abra o agente:
      o campo de modelo mostra o **modelo efetivo** que o catálogo escolheu.
      **Esperar:** liga sem recusa (se recusar com frase de gente, é o destino de suporte — volte ao T-23 passo 2).
      📊 01/10: 0 de 4 agentes de atendimento ligados — enquanto ninguém liga, o destravador da 123 não age. · *de:* S116.9 passos 2 e 7 · P-77
- [ ] **T-26** ⏳ do celular de teste, **"oi"** → resposta em segundos · *de:* S116.9 passo 3
- [ ] **T-27** ⏳ cinco mensagens + 1 foto em 12 segundos → **um** turno, **uma** resposta, foto reconhecida · *de:* 001.2 (A.1)
- [ ] **T-28** ⏳ mandar só o CPF de um cliente de teste → resposta em ~3 s, consultando a apólice **uma vez** e respondendo com a
      seguradora · *de:* 001.2 (A.2) · S116.9 passo 5
- [ ] **T-29** ⏳ *"o carro parou na"* → esperar 15 s → *"marginal pinheiros"* → **um** turno · *de:* 001.2 (A.3)
- [ ] **T-30** ⏳ mandar mensagem **enquanto** ele responde → nunca perde nem duplica · *de:* 001.2 (A.4)
- [ ] **T-31** ⏳ encerrar, voltar dentro da janela, depois puxar assunto novo → **sem** reapresentação na janela; **uma**
      apresentação no assunto novo · *de:* 001.2 (A.5)
- [ ] **T-32** ⏳ trocar o nome do agente no meio do assunto, e tentar um nome **igual ao de um membro** → nada muda no assunto em
      curso; o nome colidente é **recusado** · *de:* 001.2 (A.6)
- [ ] **T-33** ⏳ responder pelo **celular pareado**, como atendente → o agente **cala**, o silêncio aparece no feed **com o
      motivo**, nada gravado em dobro · *de:* 001.2 (A.7)
- [ ] **T-34** ⏳ repetir o T-29 com `PRESENCA_DIGITANDO_LIGADA=true` (T-08 c) → o "digitando…" **aparece e some** · *de:* 001.2 (A.8)
- [ ] **T-35** ⏳ **Dúvida simples no WhatsApp** — as mesmas perguntas do T-20, com uma apólice de teste → sim/não **com o
      limite**, **sem** citação de documento, e **sem** chamar a equipe · *de:* 001.5.2 (D2.2) · S123.4 item 3
- [ ] **T-36** ⏳ **A segunda chance do agente de atendimento** (novo da 123) — provoque um pedido de pessoa por **dúvida** ou
      **dado que falta** (💭 ex.: *"não sei se meu plano cobre isso, alguém pode ver?"*).
      **Esperar:** o agente **não** chama a equipe na 1ª vez — pergunta ou responde; só na 2ª vez no mesmo dia vai à equipe. SQL:
      ```sql
      select created_at, acao, explicacao_para_gente from public.diario_de_decisoes
       where origem = 'atendimento' order by created_at desc limit 5;
      ```
      → uma linha nova por segunda chance. 🔴 **Controles:** *"quero falar com uma pessoa"* → vai **direto** à equipe;
      sinistro (*"caiu um raio aqui"*), condomínio e empresarial → **direto**, sem segunda chance.
      · *de:* S123 (F7) · S123.4 item 3
- [ ] **T-37** ⏳ **A apólice fica no caso até o fim** — um cliente de teste com **Auto e Residencial**: *"preciso de um
      encanador"* + o CPF; depois três curtas: *"ok"*, *"e agora?"*, *"pode abrir"*.
      **Esperar:** ele **não** pede o CPF de novo e **não** consulta de novo; o acionamento de teste leva o ramo **residencial**.
      SQL (só presença, sem dado pessoal):
      ```sql
      select updated_at, (ficha_atendimento->>'apolice') is not null as apolice_nasceu,
             ficha_atendimento->>'ramo' as ramo, ficha_atendimento->>'seguradora' as seguradora,
             coalesce(jsonb_array_length(ficha_atendimento->'apolice_do_caso'->'apolices'), 0) as apolices,
             (ficha_atendimento->'apolice_do_caso') ?| array['document','name'] as vazou_dado_pessoal
        from public.conversations where ficha_atendimento ? 'apolice_do_caso'
       order by updated_at desc limit 5;
      ```
      → `apolice_nasceu` = true, `ramo` = residencial, `vazou_dado_pessoal` = **false**. Repita na **segunda corretora de
      teste** (é o que prova o isolamento). · *de:* 117 (I.2)
- [ ] **T-38** ⏳ **Central de Agentes → "Mensagens perdidas"**, por corretora → **zero** · *de:* 001.8 (G.4)
- [ ] **T-39** ⏳ 🔴 **O canário de isolamento** — dois números de teste, **cada um numa corretora de teste diferente**. Os 6 casos
      (relatório `reports/SPEC-EXTRA-001.8-EXECUTION-REPORT.md` §6): uma conversa normal · travar a 2ª corretora de propósito e
      medir a 1ª ao mesmo tempo · a travada é atendida, lenta mas atendida · 50 mensagens de uma vez, nenhuma perdida ·
      derrubar o provedor da 2ª e a 1ª não sente · desligar tudo e o número volta ao normal. · *de:* 001.8 (G.5) · P-E0018-01

### ④ Acionamento por WhatsApp, seguradora por seguradora

🔴 **Pré-requisitos:** T-08 (e) `DISPATCH_FINALIZE_MODE=test` e T-25 (agente ligado). `INSURER_DISPATCH_LIVE` está ligada: a
mensagem **sai de verdade** para a seguradora — use sempre a apólice e o número **de teste**, e vá até o fim com o observador
ligado. **Anote o dia e a hora** de cada um: é por eles que a medição seguinte acha a conversa.

- [ ] **T-40** ⏳ numa seguradora de **menu numerado**, ir até a confirmação e **RECUSAR** → o menu recebe o número certo; as
      telas entram no acervo · *de:* 001.4 (C.1)
- [ ] **T-41** ⏳ digitar **uma** vez à mão, pelo celular pareado, na conversa com a URA → o robô **espera 15 s**, não manda nada
      ao grupo nem ao segurado, e **continua lendo** · *de:* 001.4 (C.2)
- [ ] **T-42** ⏳ digitar **duas** vezes em 15 s → o robô **sai em silêncio** e não volta · *de:* 001.4 (C.3)
- [ ] **T-43** ⏳ 🔴 **O destravador pergunta ao segurado** (novo da 123) — um guincho de teste na **Porto** ou na **HDI** até a
      tela que pede algo que só o segurado sabe (💭 ex.: *"o local é seguro, escuro ou deserto?"*, data e período de um
      serviço residencial).
      **Esperar:** (1) o celular de teste recebe *"Só mais uma informação que a Porto (ou a HDI) pediu…"* com as opções numeradas,
      **sem** "Voltar"; (2) responda com o número → o acionamento continua; (3) **Atendimentos → Decisões do agente**
      (`/dashboard/atendimentos/decisoes`) mostra a linha em português — o que a seguradora perguntou, o que o agente fez, por
      quê, com que certeza —, com os botões **certo / errado**: marque um; (4) na visão do master, **`/admin/decisoes`**, a mesma
      linha aparece com a corretora. SQL:
      ```sql
      select created_at, origem, seguradora, classe, acao, nota, explicacao_para_gente
        from public.diario_de_decisoes order by created_at desc limit 10;
      ```
      → `origem` = acionamento, `acao` = perguntou_segurado.
      🔴 **Controle:** repita e responda **outra coisa** (fora das opções) → o caso vai a uma pessoa e **nada** vai à
      seguradora. **Endereço em BR/rodovia:** o agente **não** responde "Nenhuma das anteriores" sozinho.
      ⚠️ O C.4 da 001.4 esperava também o evento `acionamento.dado_faltou` no histórico; se aparecer só um dos dois (o evento ou
      a linha do diário), anote qual. · *de:* 001.4 (C.4) · S122.4 · S123.4 item 2 · D-123-K
- [ ] **T-44** ⏳ **Responder depois do prazo** — repita o T-43 e espere passar o prazo (**2 min** na Allianz, Alfa, Mapfre e
      Azul; **3 min** nas outras) antes de responder → o caso é **reaberto** quando o segurado responde (no máximo 2 vezes),
      **sem** abrir pedido duplicado. *"Abriu um segundo pedido"* = prioridade: mande o print da conversa com a seguradora.
      · *de:* S123 (o que muda no Implantar)
- [ ] **T-45** ⏳ **Guincho da Yelum** → protocolo **sem pessoa** (📊 a rota passou a atender sozinha na 123); no grupo, o ✅ com
      *serviço · seguradora · protocolo* · *de:* S120 passo 3 · S123.4 item 1
- [ ] **T-46** ⏳ **Guincho da Porto, com o pin** — quando o agente pedir a localização, mande o pin (📎 → Localização → Enviar
      localização atual).
      **Esperar:** (1) o agente pede **uma coisa de cada vez** e **ensina** a mandar o pin; (2) o formulário dentro do WhatsApp é
      respondido **sem ninguém tocar**; (3) o caso **não** vai a uma pessoa; (4) o protocolo chega ao segurado.
      *Se der:* o mesmo formulário numa **HDI** (P-71). · *de:* 118 (J.2) · S120 passo 3 · P-118-04 · P-71
- [ ] **T-47** ⏳ **Allianz residencial** — (a) um encanador até o protocolo; (b) uma apólice com **vários endereços** → o agente
      escolhe o endereço do caso; se nenhum casar, vai a uma pessoa (antes mandava "1" às cegas).
      · *de:* S120 passo 3 · S123.4 item 4 · P-123-10
- [ ] **T-48** ⏳ **Carro reserva da Yelum** — antes, confirme com a Yelum ou com a atendente o número do canal *"Segurado e
      Terceiros"* e crie no `smith-api` `INSURER_CONTACT_YELUM_CARRO_RESERVA` (só dígitos, com 55 e DDD) → Implantar.
      **Esperar:** em dia útil, das 9h às 17h, com número do sinistro e cartão de crédito, o agente diz que a Yelum confirma
      **em até 3 horas úteis**. **Sem a variável:** vai a uma pessoa com o resumo — nada quebra. · *de:* S121.2 · P-121-01
- [ ] **T-49** ⏳ **Guincho da Mapfre** até o protocolo — é a única coisa que tira `mapfre/auto/guincho` de "sem conversa" (📊 28/09:
      zero conversas de guincho da Mapfre) · *de:* 119.B · P-119-01 · §10 linha 18
- [ ] **T-50** ⏳ **As rotas que ainda faltam provar** — um acionamento de cada, até o fim, quando der (cada um vale uma rota a mais
      no "atende sozinho"):
      (a) carro reserva **Porto**, **Zurich**, **Bradesco**, **Mapfre** · (b) **HDI eletricista** (um problema que não seja
      "falta de energia") · (c) **Allianz desentupimento** · (d) **Allianz eletrodoméstico** (que não seja máquina de lavar) ·
      (e) **Porto eletrodomésticos** · (f) **Yelum eletrodoméstico** não essencial · (g) **HDI chaveiro** · (h) **Porto com mais
      de um carro** na apólice · (i) **Zurich guincho** com o carro em garagem · (j) a **consultora da Porto** que entra no meio
      da conversa, se aparecer · (k) **Bradesco** e **Zurich** até o protocolo (📊 zero no acervo) · (l) **Tokio auto** até o
      desfecho · (m) **Azul auto** até o formulário e **Azul pneu** · (n) depois, as rotas "sem conversa" da aba **CORREDORES**,
      de cima para baixo. · *de:* S120 passo 5 · S121.4 · S123.4 item 4 · J.4 · 119.B · P-120-02 · P-121-03 · P-123-09 ·
      P-118-01/02/03/09
- [ ] **T-51** ⏳ **Quando o robô para, a pessoa assume** — num dos acionamentos acima que parar numa tela: o grupo recebe o
      dossiê com *"momento: acionamento"*, o caso aparece na **Fila**, e uma pessoa assume dali. Mande o print da tela onde
      parou (é uma tela nova para o acervo). · *de:* S120 passo 3 · P-232
- [ ] **T-52** ⏳ **A contagem depois do bloco** (SQL):
      ```sql
      select event_type, count(*) from public.work_events where event_type like 'agente.%' group by 1;
      select origem, modo, acao, count(*) as decisoes, count(*) filter (where veredito = 'errado') as erradas
        from public.diario_de_decisoes group by 1, 2, 3 order by 4 desc;
      select service_type, count(*) as chamadas, round(sum(total_cost_usd)::numeric, 4) as dolares
        from public.token_usage_logs where service_type in ('destravador', 'destravador_segunda')
         and created_at >= now() - interval '7 days' group by 1;
      ```
      **Esperar:** os eventos `agente.%` **saem de zero**; o diário tem as linhas dos testes acima; 💭 perto de US$ 0,01–0,02 por
      trava. · *de:* 001.4 (C.5) · S123.2
- [ ] **T-53** ⏳ **O diário é de quem decidiu** — com acionamentos em **duas** corretoras de teste: entrando como a corretora B,
      a tela **Decisões do agente** **não** mostra as linhas da A (e vice-versa); `/admin/decisoes` mostra as duas.
      SQL: `select company_id, origem, count(*) from public.diario_de_decisoes group by 1, 2;` → uma linha por corretora.
      · *de:* P-123-14 · P-122-18

### ⑤ Portal de vidros

- [ ] **T-54** ⏳ **Os logins dos portais** — no console do `smith-api`:
      ```bash
      curl -X POST "https://autobrokers-intelligence-os-autobrokers-smith-api.golhpm.easypanel.host/api/admin/canario/extra001?portais=1" \
        -H "X-Internal-Key: $ADMIN_API_KEY"
      ```
      **Esperar** (~2 min): Tokio, HDI, Yelum e Zurich **abrem**; quando um não entra, diz **em português** por quê. Allianz e
      Mapfre esperam as senhas. · *de:* 001.6 (E.3)
- [ ] **T-55** ⏳ **Ligar o caminho novo do portal (`PORTAL_VIDROS_API_FIRST`) — decisão já autorizada por você (D-124-F)**,
      junto com o canário e **com a allowlist** (só o CPF do ensaio passa):
      1. EasyPanel → **`portal-worker`** → Environment:
         ```
         PORTAL_VIDROS_API_FIRST=true
         PORTAL_CANARIO_ALLOWLIST=cpf:1f2d4a03549e
         PORTAL_EFEITO_MATERIAL_LIBERADO=true
         ```
      2. EasyPanel → **`smith-api`** → Environment:
         ```
         PORTAL_CANARIO_ALLOWLIST=cpf:1f2d4a03549e
         PORTAL_EFEITO_MATERIAL_LIBERADO=true
         ```
      3. **Implantar** os dois.
      📊 Lido no código (01/10): a chave `PORTAL_VIDROS_API_FIRST` é lida **só no `portal-worker`**
      (`backend/portal_worker/journeys/vidros_apifirst.py:87`, `api_first_habilitado`) — no `smith-api` ela não faz nada. A
      allowlist e o efeito material são lidos **nos dois** (o `smith-api` confere antes de mandar o pedido, o `portal-worker`
      confere de novo). ⚠️ A allowlist **só estreita**: escrita errada **barra tudo** (é o certo).
      · *de:* D-124-F · D-E00110-F2 · F.2 passos 1–3 · S124.3
- [ ] **T-56** ⏳ **O canário de vidro** — agente da corretora daquela apólice **ligado**. Do celular de teste, como o segurado
      da apólice das capturas de 21/09: vidro da porta traseira do lado do motorista quebrado, carro estacionado, em
      Florianópolis/SC; quando ele perguntar a agenda, *"amanhã às 16h"*.
      **Esperar:** (1) um aviso de que vai acionar; (2) em ~1–2 min, o número do atendimento (8 dígitos), a franquia e *"Agendei o
      serviço ✅"* com loja, endereço, dia, horário e permanência — **ou** a lista de horários; responda *"loja 1, dia X às
      HH:MM"* e espere a confirmação. **Mande no chat o número do atendimento**: com ele se mede quanto tempo o acesso ao portal
      vive (+1 h, +6 h, +24 h).
      **Se der errado:** a mensagem diz o número primeiro e o que falta; nada é aberto duas vezes.
      · *de:* F.2 passos 4–5 · P-E001101-01 · P-E001101-02 · P-190 · G12
- [ ] **T-57** ⏳ **O portal destrava com a mesma régua do WhatsApp** (novo da 124) — se o portal parar numa pergunta durante o
      T-56 (ex.: estado da cidade desconhecido, uma pergunta do questionário), o agente **pergunta ao segurado** ou chama uma
      pessoa, e continua **o MESMO pedido** (não abre outro). Hoje ele **não responde nada sozinho**, de propósito. SQL:
      ```sql
      select created_at, classe, acao, nota, explicacao_para_gente from public.diario_de_decisoes
       where origem = 'portal' order by created_at desc limit 10;
      ```
      → uma linha por parada; a mesma linha em **Decisões do agente**. Se o portal não parar em nada, este teste fica sem
      material — não é defeito. · *de:* S124 (F1) · P-124-02
- [ ] **T-58** ⏳ **Depois do canário** — cancele o pedido no portal (motivo com ≥ 20 caracteres, como a atendente faz). Então:
      **verde** → para abrir a todos os segurados, apague `PORTAL_CANARIO_ALLOWLIST` dos dois serviços e Implante
      (`PORTAL_VIDROS_API_FIRST` fica `true`); **vermelho** → volte `PORTAL_VIDROS_API_FIRST=false` no `portal-worker` e
      Implante. · *de:* F.2 (depois) · D-E00110-F2
- [ ] **T-59** ⏳ **As capturas que faltam do portal** (com a atendente, quando acontecer um caso de verdade): vistoria/fotos ·
      questionário de vigia, farol, retrovisor, teto e para-choque · serviço a domicílio · passo 1 + itens cobertos de **outra**
      seguradora · uma captura de **outra corretora**. · *de:* F.3 (restos) · P-E00110-A3 · P-E00110-A14 · P-E00110-C-01 ·
      P-E00110-C-02 · P-E00110-C-04 · P-E001101-05

### ⑥ Grupo de suporte

**Onde:** a corretora de ensaio + o grupo de canário (T-23). 📊 Desde a 121, aviso de conversa só chega ao grupo quando **o
agente está ligado**, **foi o agente quem pediu ajuda** e **nenhuma pessoa da corretora falou na conversa nos últimos 7 dias**.

- [ ] **T-60** ⏳ do celular de teste, *"quero falar com uma pessoa"* → **UM** aviso no grupo com nome, CPF, seguradora, WhatsApp
      **clicável** e *"🕐 dd/mm às hh:mm · conversa inicial"*; espere 15 min → **nenhum** lembrete. **Se chegar mascarado
      (`****`)**: o Implantar não pegou. · *de:* 001.3 (B.1) · S120 passo 2
- [ ] **T-61** ⏳ responda o segurado pelo **celular** (ou pelo painel) e provoque outro pedido de ajuda → **nada** chega ao grupo
      (a pessoa falou nos últimos 7 dias) · *de:* 001.3 (B.2) · S120 passo 2 · S121
- [ ] **T-62** ⏳ mande mensagem do **número da casa** (T-23 passo 3) → o agente **não responde**, nada entra na fila, nada vai ao
      grupo · *de:* 001.3 (B.3)
- [ ] **T-63** ⏳ conclua um caso (um protocolo do bloco ④) → ✅ curto no grupo, com *serviço · seguradora · protocolo*
      · *de:* 001.3 (B.4) · S120 passo 3
- [ ] **T-64** ⏳ às **19h** (ou a hora de `RESUMO_DIARIO_HORA`) → 📊 o resumo com números que **batem** com o dia e a lista das
      assistências abertas · *de:* 001.3 (B.5) · S120 passo 3
- [ ] **T-65** ⏳ desative o destino de suporte e tente **ligar** o agente → recusa **com frase de gente**; reative → liga
      · *de:* 001.3 (B.6)
- [ ] **T-66** ⏳ com um usuário `member`, tente mexer em destino, credencial ou conexão → **403** · *de:* 001.3 (B.7)
- [ ] **T-67** ⏳ 🔴 **controle:** conversa **sem** pessoa, com pedido de ajuda → o alerta **chega** · *de:* 001.3 (B.8)
- [ ] **T-68** ⏳ **Agente desligado = grupo calado** — numa corretora com o agente **desligado**, um pedido de pessoa → **nada**
      no grupo; cobrança e resumo das 19h continuam. E confira que o grupo de cada corretora está **dentro** dela (um já nasceu
      na corretora errada). · *de:* S121 · S121.6 · 1.1 · P-PILOTO-10

### ⑦ Leitura de foto e de documento

- [ ] **T-69** ⏳ **A foto lida pelo `gpt-6-luna`** — no WhatsApp de teste, mande uma **foto de CNH ou de apólice** (pode ser a
      sua) e pergunte algo dela (*"qual o número dessa apólice?"*); e uma foto de para-brisa → ele descreve o que viu. SQL:
      ```sql
      select model_name, total_cost_usd, created_at from public.token_usage_logs
       where service_type = 'vision' order by created_at desc limit 5;
      ```
      **Esperar:** o dado certo da foto, e a linha mais nova com `gpt-6-luna`, perto de **US$ 0,0002–0,0003** (📊 o teste de
      01/10 deu 0,000308). **Aparece `gpt-6.1-sol`** → o `smith-api` não está no código de hoje (T-02). **Leu errado** → mande o
      print da foto **com os dados cobertos** e a resposta (é o caso que a bancada não mediu, P-124-05).
      · *de:* S124.2 · S116.9 passo 4
- [ ] **T-70** ⏳ **O docling — só vale com "Analisar imagens e gráficos" marcado** (`extract_images`). Painel do master →
      **`/admin/knowledge-base/sanitize`** → suba um PDF **com imagem** (sem dado pessoal) com a caixa **Analisar imagens e
      gráficos** marcada.
      **Esperar:** o trabalho termina (não fica em erro). SQL:
      ```sql
      select created_at, model_name, total_cost_usd, details->>'estimativa' as estimativa
        from public.token_usage_logs where details->>'papel' = 'visao_documento' order by created_at desc limit 5;
      ```
      → uma linha com `gpt-6-luna`; `estimativa` vazia (se vier `true`, o custo foi estimado, não lido — anote).
      **Se der erro `TypeError`**: o worker do docling ficou antigo — Implante o worker do docling de novo.
      Sem a caixa marcada, o docling não chama modelo e o teste não mede nada. · *de:* S124.1 · P-124-06 · P-124-13
- [ ] **T-71** ⏳ *(opcional)* **~10 fotos reais com os dados cobertos** (CNH, documento do carro, apólice) para uma rodada da
      bancada da visão — hoje o número da Luna é o **melhor caso** (documentos fabricados). · *de:* P-124-05

### ⑧ Cobrança — painel da Resulta, envio só para o seu número

- [ ] **T-72** ⏳ **Preencher o Auxiliar de cobrança** (Rotinas): **"Quem assina"** · modo **Encaminhar** · WhatsApp da equipe =
      **o seu número** · antecedência **7 dias**. Sem "Quem assina", o resto não vale · *de:* 001.6 (E.1)
- [ ] **T-73** ⏳ **O canário da cobrança** — console do `smith-api`:
      ```bash
      curl -X POST "https://autobrokers-intelligence-os-autobrokers-smith-api.golhpm.easypanel.host/api/admin/canario/extra001?esperar_retorno_s=180" \
        -H "X-Internal-Key: $ADMIN_API_KEY"
      ```
      **Esperar:** um JSON começando por `{"ok": true`; no seu WhatsApp, **uma** mensagem por segurado, N boletos juntos,
      **nunca a mesma parcela duas vezes**; responda a pergunta Q4. `409 canário desarmado` = variáveis do canário fora do
      lugar. · *de:* 001.6 (E.2)
- [ ] **T-74** ⏳ **Só depois do T-73**, religar a rotina de cobrança (Rotinas → Auxiliar de cobrança) · *de:* 001.6 (E.4)

### ⑨ Desfazer o ensaio e ir para a vida real

- [ ] **T-75** ⏳ **Desfazer o ensaio:** desativar o destino do **grupo de canário** (deixando ativo o grupo de verdade) · apagar
      os **números da casa** de teste · **desparear** o celular pessoal · **esvaziar** `ATTENDANT_INBOUND_ALLOWLIST` e Implantar ·
      desligar o agente da corretora de ensaio, se era só ensaio · cancelar as **intenções pendentes** que o ensaio deixou ·
      voltar `DISPATCH_FINALIZE_MODE=live` (e apagar a lista) quando quiser chamado de verdade (D-118-01).
      · *de:* 9.1–9.5 · S116.9 passo 8 · J.3
- [ ] **T-76** ⏳ peça no chat *"tem alguma sessão de acionamento aberta?"* → **nenhuma** · *de:* 001.4 (9.6)
- [ ] **T-77** ⏳ **O checklist, de verdade** — peça *"rode o checklist de ligar"* (sem "canário") → **PODE LIGAR**. Com a
      allowlist preenchida ele **não** pode dar verde: preenchida no piloto = todo segurado fora dela é ignorado em silêncio.
      · *de:* 001.7 (P1)
- [ ] **T-78** ⏳ **Só com "PODE LIGAR" na tela**, clique **Ligar agente** em cada corretora do piloto · *de:* 001.7 (P1.b)
- [ ] **T-79** ⏳ **Os 3 dias úteis** com o agente ligado. Combine com a equipe uma coisa só: *"quando o agente errar, NÃO
      desligue: assuma a conversa pelo celular (isso o cala ali) e anote o que ele fez de errado"*. Nada de folha diária.
      · *de:* 001.7 (P2) · P-E0017-09
- [ ] **T-80** ⏳ *(opcional)* **No meio**: *"rode a medição do piloto de DD/MM a DD/MM e me mostre a tabela"* (até **ontem**).
      **Não é defeito:** "NÃO AVALIADA — amostra insuficiente" (menos de 5 casos) · "NÃO MENSURÁVEL" antes de 14/09 · "NÃO
      LIDO" (peça de novo; nunca vira zero). **Anote se** a tabela disser 0 conversas num dia em que você viu o agente
      responder. · *de:* 001.7 (P3)
- [ ] **T-81** ⏳ **O veredito, no 4º dia** — chat novo, cole `docs/canon/PROMPT-VEREDITO-DO-PILOTO.md` (troque só as duas datas).
      Responde **PASSOU** ou **NÃO PASSOU**. Cortes propostos (D-E0017-03, sua): nada abaixo do palpite de 12/09 · "aciona" ≥ 5
      casos e nota ≥ 70 · "sabe pedir ajuda" ≥ 90 · apólice errada ≤ 1 em 10. · *de:* 001.7 (P4)

**O que ficou fora desta lista, de propósito** (não são testes): trocar chaves e senhas (S116.3, 0.4.b–d, F.5) · as decisões
(§10, S116.8, S116.10, S120.4, S121.5, S121.7, S122.5, S123.5, S124.3 restantes, G.6, G.7, I.3, J.3) · o Agger (bloco H) · ler a aba
CORREDORES (119.A) · o chamado à InfoCap pelas duas telas com erro 500 (P-99) · reparear os áudios da AutoFleet (P-96).

---

## O que veio antes — as caixas do Founder, por SPEC (escrito a partir de 20/09/2026)

> **Escrito em 20/09/2026** (para os testes, vale a lista única acima, de 01/10). Esta parte substituiu a lista antiga do §6/§7 e juntou,
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

## SPEC-116 — o que só você faz (23/09/2026) · cada trabalho no modelo que provou servir

> **O que mudou, em uma frase:** cada tarefa do produto (responder no chat, atender no WhatsApp, ler foto, decidir no
> portal, lembrar do cliente…) agora pede o seu modelo de inteligência a **um lugar só**, e trocar ou voltar um modelo é
> uma linha no banco, em minutos, sem Implantar. Três trabalhos já trocaram, porque a bancada de testes provou que o novo
> acerta mais: **memória** (📊 39 de 45 acertos, era 32), **leitura de foto** (📊 30 de 30, era 28) e **decisão no portal de
> vidros** (📊 43 de 43, era 38 de 41). O chat, o atendimento, a cobrança e a conversa com a seguradora **não mudaram**:
> a medição parou antes, por falta de crédito. Relatório: `reports/SPEC-116-EXECUTION-REPORT.md`.
>
> **Estado em 24/09/2026:** a Onda A foi concluída (`ccb2b0d`: chat e atendimento no GPT-6 Sol, volume no GPT-6 Luna,
> Opus 5.5 no lugar do Opus 5, transcrição no gpt-transcribe). E a **SPEC-116-RESERVA** acrescentou um **modelo reserva de
> outra empresa** nos 4 caminhos que não podem parar: se a OpenAI cair, o atendimento, o chat e o portal respondem pelo
> Claude Opus 5.5; se a Anthropic cair, a conversa com a seguradora responde pelo GPT-6 Sol. Relatório:
> `reports/SPEC-116-RESERVA-REPORT.md`. Tarefa nova: **S116.11**.

- [ ] **S116.1** Recarregar o crédito e ligar a recarga automática → **T-04**

- [x] **S116.2** Implantar → **T-01** (feito 01/10) · o `portal-worker` → **T-02** · o "oi" → **T-09**

- [ ] **S116.3** **Trocar as chaves e senhas que foram coladas no chat** · higiene
      **Quais (só o NOME):** chaves de IA: OPENAI_API_KEY · ANTHROPIC_API_KEY/CLAUDE_API_KEY · GOOGLE_API_KEY/GEMINI_API_KEY · COHERE_API_KEY · DEEPGRAM_API_KEY · ELEVENLABS_API_KEY · TAVILY_API_KEY · FIRECRAWL_API_KEY · GOOGLE_PLACES_API_KEY · BROWSERBASE_API_KEY; banco e infra: SUPABASE_SERVICE_ROLE_KEY (=SUPABASE_KEY/SUPABASE_SERVICE_KEY) · senha do banco em SUPABASE_DB_URL · senha do REDIS_URL · MINIO_ROOT_PASSWORD · MINIO_BACKUP_S3_ACCESS_KEY_ID/SECRET_ACCESS_KEY · senha do Postgres do evolution-go; segredos do app: SESSION_SECRET/APP_SECRET/SECRET_KEY · ADMIN_API_KEY/ADMIN_TOKEN · ENCRYPTION_KEY · PORTAL_VAULT_KEY · REVIEW_ENGINE_LINK_SECRET · DOCLING_SERVICE_KEY; canais e integrações: EVOLUTION_API_KEY · EVOLUTION_GO_INSTANCE_TOKEN · EVOLUTION_GO_GLOBAL_KEY/GLOBAL_API_KEY · N8N_API_KEY · TWILIO_AUTH_TOKEN · GOOGLE_OAUTH_CLIENT_SECRET · NOTION_OAUTH_CLIENT_SECRET; logins de portal: senhas da API InfoCap (Resulta e AutoFleet) · senhas do Agger (2 contas) · senha do Segfy — e as de P-PILOTO-09.
      **Onde:** no painel de cada provedor, gere a nova e **apague a antiga**; cole a nova no EasyPanel (smith-api →
      Environment; e no portal-worker, se ela existir lá) e clique Implantar.
      🔴 **Nunca cole a chave nova no chat.**

- [ ] **S116.4** *(opcional)* **Pedir "retenção zero" (ZDR) à OpenAI e à Anthropic**
      **Onde:** o formulário de vendas de cada uma — peça *"Zero Data Retention"* para a sua organização.
      **Por quê:** hoje o que o segurado escreve fica guardado no provedor pelo prazo padrão dele. Não bloqueia nada.

- [ ] **S116.5** *(opcional)* **Ligar o Gemini na bancada**
      **Onde:** ponha `GOOGLE_API_KEY` no arquivo `backend/.env` do seu computador (o mesmo nome que já está no EasyPanel) e,
      no Google AI Studio → Billing, confirme que o projeto está no **plano pago** — o gratuito usa os dados para treino.
      **O que esperar:** nada muda no produto; a próxima bancada passa a comparar o Gemini também.

- [ ] **S116.6** **Documentos (docling): `VISION_MODEL`** — **hoje, deixe como está**
      O serviço de documentos escolhe o modelo por essa variável, não pelo lugar único. Hoje o valor (`gpt-4o-mini`) é o
      mesmo da rota de documento, então nada a fazer. **Anote:** quando a rota de documento mudar, esta variável muda junto
      (P-S116-09).

- [ ] **S116.7** Apagar as variáveis que o produto deixou de ler → **T-07**

- [ ] **S116.8** **Decidir se apaga as 31 linhas de teste** que um teste gravou por engano no registro de custos (P-S116-11)
      São 📊 31 linhas do portal, sem corretora, custo zero, entre 17:43 e 17:47 UTC de 23/09. Nunca foram cobradas.
      **Para apagar:** peça no chat *"pode apagar as 31 linhas de teste do portal no ledger (P-S116-11)"*.
      **O que esperar:** a resposta mostra **31** apagadas. Outro número = pare e peça a conferência.

- [ ] **S116.9** O canário do atendimento → allowlist **T-23** · ligar **T-25** · "oi" **T-26** · foto **T-69** · CPF **T-28** ·
      *"Ela cobre eletricista?"* **T-17** · modelo efetivo **T-25** · desfazer **T-75**. *Se algo piorar:* nota no topo da lista.

- [ ] **S116.10** *(opcional)* **Confirmar a D-116-18** — no portal e na foto ficou o modelo de **maior margem** (GPT-6 Sol)
      e não o mais barato que empatou (GPT-6 Luna, 📊 ~1/15 do custo por acerto). Recomendação: manter o Sol até o canário
      e depois testar a Luna (Onda B). Se preferir já a Luna, é uma linha — peça no chat.

- [ ] **S116.11** Depois da SPEC-116-RESERVA: apagar as 3 variáveis velhas → **T-07** · conferir a reserva → **T-06**

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

- [ ] **0.1.a–d** As quatro variáveis desta tabela → **T-08** (a allowlist do ensaio → **T-23**)

### 0.2 O Implantar único

- [x] **0.2** O Implantar único → **T-01** (feito 01/10)

- [ ] **0.3** O "oi" no chat do painel → **T-09**

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

- [ ] **0.4.c 🔴 TROCAR AGORA as senhas que estão nas capturas do Agger** (acrescentado em 22/09). As três
      capturas de tela (arquivos HAR) que vieram para a investigação do Agger foram gravadas na sessão de uma
      pessoa da corretora e contêm **a senha dela no Aggilizador** e **as senhas dos portais das seguradoras**
      (📊 22/09: as senhas dos portais aparecem em **todas** as 28 respostas de acompanhamento do cálculo —
      Research Pack da EXTRA-002 §1, §2.1). **O que fazer:** (1) trocar a senha desse usuário no Aggilizador;
      (2) trocar a senha de cada portal de seguradora cadastrado no Aggilizador; (3) **nunca** anexar esses
      arquivos a chat, drive ou e-mail; (4) apagá-los depois da parte 2 da EXTRA-002 (antes disso a execução
      extrai só as respostas, sem senha). **Não bloqueia nada, mas é a primeira coisa a fazer.** · **EXTRA-002 ·
      P-E002-HAR**
- [ ] **0.4.d Rodízio das credenciais de produção coladas no chat da sessão da EXTRA-002** (22/09: chaves de
      API, banco, portais). Elas passaram a existir em mais um lugar. É a mesma tabela do 0.4.b — só sobe a
      urgência. · **EXTRA-002 · P-PILOTO-09**

---

## 1 · Preparar o ensaio — pré-requisitos

- [x] **1.1** Reativar o grupo de suporte de cada corretora — 📊 20/09 ativo nas duas (P-E0017-01 fechada). A conferência de
      que cada grupo está **dentro** da sua corretora → **T-68** · **001.3 / 001.7**
- [ ] **1.2 a 1.5** Grupo de canário · número da casa · parear o celular · agente desligado até o ensaio → **T-23**

- [ ] **1.6 Saber onde o teste de apólice roda** · **001.1 / 001.6**
      ⚠️ A InfoCap tem um bloqueio conhecido (F-094-07): duas corretoras descriptografam para a **mesma
      conta**, e o adaptador recusa a segunda. Por isso os testes de **apólice** (bloco D) e de
      **cobrança** (bloco E) ficam na **Resulta**, só leitura ou envio ao seu número.

---

## 2 · Bloco D — a apólice certa, no chat do painel (001.1)

**Onde:** painel da **Resulta**, chat `core`, com a sua conta. Nada sai por WhatsApp.
**Anote cada um como:** ✅ passou · ⚠️ passou mas o texto ficou estranho · ❌ falhou (cole a resposta).

- [ ] **D.1 a D.7** → **T-10 a T-16** (na mesma ordem)

---

## 3 · Bloco D2 — a base de planos responde (001.5 e 001.5.2)

**Onde:** mesmo chat `core`, e o WhatsApp do aparelho de teste.
📊 A base já está publicada: **492 serviços, 108 planos, 8 seguradoras**. Não há mais fila para curar.

- [ ] **D2.0** → **T-18** · **D2.1** → **T-19** · **D2.2** chat → **T-20**, WhatsApp → **T-35** · **D2.3** → **T-20** · **D2.4** → **T-21** ·
      **D2.5** → **T-22**

---

## 4 · Bloco A — a conversa no WhatsApp (001.2)

**Onde:** WhatsApp do aparelho de teste (TESTE-A) escrevendo para a corretora de ensaio.
**Pré-requisito:** ligar o agente **só** para o ensaio. Ao fim do bloco, desligue de novo.

- [ ] **A.1 a A.8** → **T-27 a T-34** (na mesma ordem)

---

## 5 · Bloco B — o grupo da equipe (001.3)

**Onde:** painel da corretora de ensaio + o grupo de canário (tarefa 1.2).

- [ ] **B.1 a B.8** → **T-60 a T-67** (na mesma ordem)

---

## 6 · Bloco C — o acionamento ao vivo (001.4)

🔴 **Só na sessão do canário**, na corretora de ensaio. `INSURER_DISPATCH_LIVE` está **ligada**: o que
sair daqui sai de verdade para a seguradora.

- [ ] **C.1** → **T-40** · **C.2** → **T-41** · **C.3** → **T-42** · **C.4** → **T-43** · **C.5** → **T-52**

---

## 7 · Bloco E — a cobrança e os portais (001.6)

**Onde:** painel da **Resulta** (tela) + **console do serviço `smith-api`** (os dois comandos).
🔴 **Todo envio vai só para o seu número** — é o que `BILLING_CANARIO_ALLOWLIST` e `CANARIO_TESTE_B`
garantem; sem elas o comando recusa com **409** e não manda nada.

- [ ] **E.1** → **T-72** · **E.2** → **T-73** · **E.3** → **T-54** · **E.4** → **T-74**

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

- [ ] **P1** O checklist de ligar → **T-24** (modo canário) e **T-77** (de verdade) · **P1.b** → **T-78** · **P2** → **T-79** ·
      **P3** → **T-80** · **P4** → **T-81**

---

## 8.5 · Bloco F — o portal de vidros (001.10 · 001.10.1)

> **O que mudou:** o robô aprendeu a abrir o pedido de vidro **em qualquer uma das 38 seguradoras** que o portal
> publica (antes eram 3, e nenhuma delas era a Yelum — 📊 o motor antigo escrevia **zero** nas capturas reais), e
> aprendeu a **ler o desfecho que o portal decidiu**: loja já escolhida, agenda com lojas e horários, analista ou
> vistoria. Ele devolve ao segurado o número do atendimento, a franquia e o próximo passo.
> **E agora (001.10.1), ele RETOMA um atendimento já aberto** — guarda o acesso cifrado, e quando a resposta do
> segurado chega (a agenda, uma preferência), ele volta ao portal, lê onde o pedido está e continua sozinho, em vez
> de terminar em mão humana.
>
> 🔴 **Nada disso está ligado.** Tudo mora atrás de uma chave que nasce desligada: `PORTAL_VIDROS_API_FIRST`.
> O que atende hoje continua sendo o caminho antigo. Implantar **não muda nada** no ar — e é de propósito.

- [x] **F.1** Implantar → **T-01** (feito 01/10); o `portal-worker` → **T-02**
- [ ] **F.2** O canário → ligar a chave **T-55** · o canário **T-56** · o portal destrava **T-57** · depois **T-58**
- [x] **F.3 As capturas que faltam** — chegaram em 21/09 e liberaram o agendamento (P-E00110-A1 FECHADA). O que
      ainda falta (fotos/vistoria, domicílio decidido fora, cancelar) está em P-E001101-05 e no bloco novo de
      pendências da 001.10.1. · **001.10 · 001.10.1**
- [x] **F.4 As 15 perguntas à atendente** — respondidas em 21/09. A nº 12 ("dá para retomar por número?") decidiu
      a 001.10.1, que já foi executada. · **001.10 · P-E00110-A11 (FECHADA)**
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

- [x] **G.1** Implantar → **T-01** (feito 01/10) · **G.2** e **G.3** → **T-03** · **G.4** → **T-38** · **G.5** → **T-39**
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

## 8.7 · Bloco H — cotar e renovar pelo Agger (EXTRA-002, parte 2)

> **O que a investigação descobriu (22/09):** a tela do Aggilizador é uma "casca" sobre um serviço que o
> computador consegue chamar diretamente — dispara o cálculo, espera, lê o resultado já padronizado por
> seguradora, com PDF. 📊 Em 2 cálculos medidos, as primeiras ofertas completas chegaram em 30 s e 229 s, e o
> conjunto fechou em ~7 min. Ou seja: **tecnicamente dá**. O que falta é **só da sua mão**: a permissão da Agger,
> um usuário próprio para o robô e a senha dele guardada no produto. Sem isso, a prova ao vivo (parte 2) não
> roda — e a Renovação Feita (EXTRA-003) não tem motor.
>
> 🔴 **Antes deste bloco: o 0.4.c** (trocar as senhas que estão nas capturas).

- [ ] **H.1 Confirmar a conexão "InfoCap RESULTA" que está dentro da Amandus.** 📊 Ela foi criada em 21/09 às
      20:29 **sob a corretora Amandus**; a Resulta ficou sem conexão InfoCap que funcione. **Onde:** painel →
      conexões da Amandus. **O que decidir:** foi de propósito? Se **não**, diga no chat e a execução a recria
      na corretora certa, com prova de isolamento. **Bloqueia:** o experimento E0 (quantas renovações de
      automóvel por dia) para a Resulta. · **EXTRA-002 · P-E002-X1**
- [ ] **H.2 Conversar com a Agger** — três perguntas, na mesma conversa: (1) existe **API oficial** ou acordo
      de integração? (2) se não, vocês **autorizam por escrito** o acesso programático pelos mesmos endereços
      que a tela usa? (3) quanto custa **um usuário a mais** (o do robô)? 🔴 **Sem essa autorização, nenhuma
      automação** — nem por navegador. **Bloqueia:** E1–E4 da parte 2. · **EXTRA-002 · D-E002-01**
- [ ] **H.3 Criar o usuário robô no Aggilizador** da Resulta (e da AutoFleet), com um nome que diga o que é
      (💭 ex.: "AutoBrokers"). **Por quê:** o Aggilizador aceita **uma sessão por usuário** — se o robô usasse o
      login de uma pessoa, ele a derrubaria no meio do trabalho. **Bloqueia:** E1. · **EXTRA-002 · D-E002-02**
- [ ] **H.4 Guardar a senha do robô no AutoBrokers**, na **tela de conexões** da corretora — **nunca** em
      arquivo, chat ou e-mail. **Bloqueia:** E1. · **EXTRA-002**
- [ ] **H.5 Decidir D-E002-01 a 08** (ver §10, linha 14). Todas já vêm com a opção recomendada e a nota; se
      você não disser nada, a execução segue a recomendação. **Não bloqueia.** · **EXTRA-002**

**Bloqueia alguma coisa?** H.2, H.3 e H.4 bloqueiam a parte 2 inteira (e, com ela, a EXTRA-003). H.1 bloqueia
só a medição de volume da Resulta.

---

## 8.8 · Bloco I — a apólice não se perde no meio do atendimento (117)

> **O que mudou:** quando o agente do WhatsApp descobre a apólice do segurado, ela agora **fica no caso até o fim**.
> Antes ela sumia: o agente já tinha a apólice na mão e, na hora de acionar a seguradora ou abrir o portal, o **ramo**
> (automóvel, residencial) voltava a ser palpite do modelo — inclusive contra a sua decisão de 17/09, de que **o ramo da
> apólice manda**. 🔴 A causa era estrutural: a peça que monta esse contexto exigia **CPF ou nome crus**, e o agente que
> fala com o segurado só recebe a versão mascarada — então o contexto **nunca nascia** no WhatsApp, e toda regra pendurada
> nele estava desligada sem ninguém saber. Agora existe **um lugar só** que escolhe a apólice do caso, ela é gravada na
> ficha do atendimento, e **todos** leem a mesma: o acionamento da seguradora, o portal de vidros, o aviso à pessoa que
> assume o caso e a resposta seguinte. Nenhum dado pessoal cru chega ao modelo — o cliente viaja como **apelido opaco**.
>
> 🔴 **Nada aqui precisa de configuração nova:** nenhuma variável é obrigatória e 📊 **não houve nenhuma mudança de
> banco**. Relatório: `reports/SPEC-117-EXECUTION-REPORT.md`.

- [x] **I.1** Implantar → **T-01** (feito 01/10) · **I.2** O canário de duas corretoras → **T-37**
- [ ] **I.3 Decidir a P-S117-08** — criar ou não uma **variável própria** para o apelido opaco do cliente
      (`POLICY_CONTEXT_HMAC_KEY`). **Hoje funciona sem ela:** o código usa a chave de cifra que já existe no ambiente
      (`ENCRYPTION_KEY`), e o apelido continua estável e isolado por corretora. O certo pelo manual europeu de
      pseudonimização (ENISA) é ter a chave do apelido **separada** da chave de cifra. **Não bloqueia nada** — se algum
      dia o `ENCRYPTION_KEY` faltar, o apelido enfraquece sem ninguém notar. · **117 · P-S117-08**

**Bloqueia alguma coisa?** 🔴 **Nada aqui bloqueia a entrega** — a SPEC está pronta e provada por teste, e nada nela
espera terceiro. O **I.1** é o que leva a mudança ao ar; o **I.2** é o que a prova na vida real (sem ele, o isolamento e
o ramo oficial ficam provados só por teste); o **I.3** é uma melhoria de segurança que pode esperar.

---

## 8.9 · Bloco J — o formulário dentro do WhatsApp deixa de parar o acionamento (118)

> **O que mudou, em uma frase:** quando a seguradora abre aquele **formulário dentro da conversa** — a telinha com
> campos para preencher, que o WhatsApp mostra sem sair do chat —, o produto agora sabe respondê-lo **sozinho** na
> Porto, e o agente pergunta antes, em português, o que a seguradora vai exigir lá dentro.
>
> 🔴 **E uma coisa que eu te pedi errado, e agora está medida:** eu pedi um **rebuild da imagem do WhatsApp**. Não era
> preciso. 📊 Em 26/09 às 17:24 a prova rodou contra o serviço no ar e o envio de resposta de formulário **funcionou na
> primeira tentativa certa** (HTTP 200, `Type: "InteractiveResponseMessage"`), com a tentativa de controle — sem o
> embrulho — devolvendo erro 479. O catálogo do serviço (`swagger`) não lista a rota, mas a rota existe: **o catálogo
> estava incompleto, não o serviço.** A pendência **P-62**, que repetia o pedido de rebuild há semanas, foi fechada.
>
> **O que mais mudou:** a **Tokio** deixou de fingir que atende. 📊 Em 52% das conversas dela o atendimento termina num
> **link** da seguradora, e não num protocolo — então o caso passa a ir para uma pessoa **com o dossiê pronto**, em vez
> de ficar preso até o vigia perceber. (E havia um defeito grave aí: a entrega para uma pessoa era **inalcançável** no
> código — o segurado era simplesmente abandonado.)

- [x] **J.1** Implantar → **T-01** (feito 01/10) · **J.2** O canário do formulário → **T-46**
- [ ] **J.3 Decidir a `D-118-01` — quando abrir a finalização para todas as seguradoras.** Você pediu *"todas
      liberadas, para não ter confusão depois"*. **A recomendação da execução é o contrário, e por um motivo concreto:**
      hoje a lista `DISPATCH_FINALIZE_LIVE_PLAYBOOKS` aceita um nome escrito errado **e não avisa** — o corredor
      simplesmente nunca fecha o chamado, em silêncio. Enquanto os testes correm, o modo `test` + a lista explícita é o
      estado mais seguro (é o que está no ar hoje: Porto e Yelum). Depois do canário do J.2, troque para
      `DISPATCH_FINALIZE_MODE=live` e **apague a lista** — aí todas ficam liberadas, sem lista para esquecer.
      **Onde:** EasyPanel → `smith-api` → Environment. · **118 · D-118-01 · P-118-15**
- [ ] **J.4** As capturas da Azul, Mapfre e Tokio → **T-50** (m, l) · **118 · P-118-01 · P-118-02 · P-118-03**

**Bloqueia alguma coisa?** ⛔ **Não.** Nada nesta entrega espera terceiro, chave ou pagamento. O **J.1** leva ao ar; o
**J.2** é o que prova na vida real; o **J.3** é sua decisão e pode esperar o J.2; o **J.4** é coleta de material, e cada
captura vale uma rota a mais no painel.

---

## 9 · Depois de tudo — desfazer o ensaio

- [ ] **9.1 a 9.5** → **T-75** · **9.6** → **T-76**

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
| 11 | **D-E00110-F1 · o contato do segurado no portal — `RESOLVIDA`** | você escolheu: corretor como solicitante declarado + celular e e-mail do **segurado** como contato, com WhatsApp marcado. É o desenho que a 001.10.1 já entrega (D-E001101-04); só falta o canário provar que o portal aceita | `FOUNDER-DECISIONS.md` |
| 12 | **D-E00110-F2 · quando ligar `PORTAL_VIDROS_API_FIRST`** | ✅ **AUTORIZADA** por você (01/10, D-124-F): ligar **junto com o canário**, com allowlist; abrir a todos só depois do canário verde. Passo a passo → **T-55** a **T-58** | `FOUNDER-DECISIONS.md` |
| 13 | **D-E00110-F3 · a 001.10.1 (a continuação) entra antes da 001.8? — `CUMPRIDA`** | sim: a 001.10.1 foi executada em 24/09/2026 (nota 88), antes da 001.8 seguir para canário | `FOUNDER-DECISIONS.md` |
| — | **D-E001101-01…07 (001.10.1)** — todas tomadas pela execução, nenhuma aberta para você | token no cofre do worker (88) · agendar pela preferência + continuação (90) · e-mail do corretor = Perfil de Acionamento (90) · contato do segurado + WhatsApp (88, fecha a F1) · domicílio fora (sua decisão) · `BloqueadoIlhaNormal` deixa de travar (90) · peça reescrita com pedido esperando resposta vira continuação (85) | `FOUNDER-DECISIONS.md` |
| 14 | **D-E002-01 a 08 · o Agger, a renovação e a fila** (22/09, propostas) | as oito já vêm com a recomendação: pedir à Agger a **API oficial e a autorização** na mesma conversa, sem autorização nenhuma automação (01: 92 × 84 × 58 × 25) · **usuário robô** por corretora (02: 95) · calcular em D-30 e **recalcular** perto do fechamento, porque a cotação vale 5 dias (03: 88) · **o corretor revisa e envia** (04: 92) · **rótulos transparentes** em vez de "a melhor" escolhida por IA (05: 94) · a 003 em **duas partes**, fundação e ciclo (06: 88) · a posição na fila (07: 78 × 65 — diferença pequena, é a que mais precisa de você) · o Agger como porta **de cotação**, não de gestão (08: 90) | `FOUNDER-DECISIONS.md` · proposta 002 §10 |
| 15 | **P-S117-08 · a chave do apelido opaco do cliente** | hoje o apelido do cliente é derivado com a chave de cifra que já existe (`ENCRYPTION_KEY`) e funciona; o certo pela ENISA é uma chave **separada** (`POLICY_CONTEXT_HMAC_KEY`). **Não bloqueia nada**: se o `ENCRYPTION_KEY` faltar um dia, o apelido enfraquece em silêncio | `PENDENCIAS.md` P-S117-08 · bloco **I.3** |
| 16 | **D-118-01 · quando abrir a finalização para TODAS as seguradoras** | você pediu *"todas liberadas, para não ter confusão depois"*. A recomendação da execução (nota 88 × 55 × 40) é o contrário **enquanto os testes correm**: `DISPATCH_FINALIZE_MODE=test` + a lista explícita — que é o estado no ar hoje (📊 Porto e Yelum) —, e só **depois do canário do J.2** trocar para `live` e **apagar a lista**. O motivo é concreto: a lista aceitava um nome escrito errado e não avisava; o corredor nunca fechava o chamado, em silêncio. ✅ Isso virou **defeito visível** no `/health` nesta SPEC (`finalize_refs_fantasma`) | relatório 118 · D-118-01 · P-118-15 |

---

## SPEC-119 — o que só você faz (28/09/2026) · os corredores ficam prontos para a vida real

> 🔴 **Nada aqui é urgente e nada bloqueia o produto.** São **capturas** — conversas de verdade
> que precisam acontecer com o observador ligado. Cada uma resolve uma rota, e **nenhuma linha de
> programa substitui uma delas.**

### 119.A · Ler a aba CORREDORES de novo — ela mudou de verdade

`[ ]` Abra o painel, aba **CORREDORES**. O que você vai ver de diferente:

```
antes   mapfre / auto / guincho ....... 72 pedidos
hoje    mapfre / auto / guincho ....... —   (nenhuma conversa desta rota no acervo)
```

📊 **Aquele 72 nunca foi da Mapfre.** Era o total de guincho somando **sete** seguradoras, medido
em **21/08/2026**, impresso igual nas dez linhas de guincho. A maior rota de guincho de verdade,
medida em **28/09** nas conversas reais, é a **Allianz** com **29** — e a Mapfre tem **zero**.

⚠️ **Onde a página mostrar `—`, leia "não sabemos", nunca "ninguém pediu".** São coisas
diferentes, e a aba tem uma seção no fim dizendo quantas conversas existem sem etiqueta.

### 119.B · As capturas que destravam rota — uma conversa cada

`[ ]` **Guincho na Mapfre** → **T-49** · **As 31 rotas sem uma única conversa** → **T-50** (n)

### 119.C · A decisão que sobra para você

`[ ]` **`carro reserva` vira corredor?** 📊 O segurado pede: **126 telas** e **13 conversas** no
acervo (Yelum 10, Tokio 2, Mapfre 1). E **não existe um único passo escrito** para ele — o produto
não atende. ⚠️ **Não precisa de captura nova**: o material já está gravado; precisa de uma SPEC.
Isto é a **P-119-05**.

`[ ]` **Condomínio e a Tokio continuam fora?** A Tokio entrega **link** (📊 5 de 5 conversas
residenciais dela), e condomínio está fora de escopo por decisão sua de 21/08. As duas coisas
aparecem como "100% sem etiqueta" na medição — e é **por desenho**, não por defeito. Se mudou de
ideia, é uma SPEC nova.

| # | tarefa | por que importa | onde |
|---|---|---|---|
| 17 | **ler a aba CORREDORES** | a coluna `pedidos` mudou de significado; o `—` agora quer dizer "não medido" | painel, aba CORREDORES |
| 18 | **1 acionamento de guincho na Mapfre** → **T-49** | é o gate **G2**, e ele **não se cumpre com código** | WhatsApp da corretora · P-119-01 |
| 19 | **decidir se `carro reserva` vira corredor** | 13 conversas pedindo, zero passos escritos | P-119-05 |

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

---

## SPEC-120 — os corredores com conversa atendem sozinhos (29/09/2026)

📊 No simulador, 24 → **31** das 73 rotas atendem sozinhas (`simular_corredor.py --todas`, commit `7844542`).
Nada foi testado com seguradora de verdade: estes passos são o que falta antes de mandar a Resulta e a AutoFleet ligarem.

1. **Implantar** → **T-01** (feito 01/10) · o "oi" → **T-09**
2. **O dossiê no grupo** → **T-60** e **T-61**
3. **Acionamentos reais** → Yelum **T-45** · Porto com o pin **T-46** · Allianz residencial **T-47** · o ✅ no grupo **T-63** · o resumo das 19h **T-64** ·
   o robô parou numa tela **T-51**
4. **Decidir** D-120-B (preço da bateria na Porto + "posso continuar?": recomendo perguntar ao segurado, 85) e D-120-C (amperes com preço: recomendo manter com pessoa, 80).
5. Quando der: as 6 rotas de P-120-02 → **T-50**


---

## SPEC-121 — o grupo só ouve quando precisa, e mais rotas atendem sozinhas (30/09/2026)

⏳ **Estado em 30/09/2026: PENDENTE — você disse que faz estes testes no fim.** Continuam valendo como estão abaixo.

📊 O grupo de suporte: os 29 avisos errados de 21/09 viram **zero** no teste (commit `823a845`). Agora só chega ao grupo aviso
de conversa quando **o agente está ligado**, **foi o agente quem pediu ajuda** e **nenhuma pessoa da corretora falou na conversa
nos últimos 7 dias**. 📊 No simulador: **31 de 76** rotas atendem sozinhas (eram 31 de 73; entraram 3 de carro reserva).
O Sonnet 5 saiu do sistema e o Sonnet 5.5 entrou (a mudança no banco já foi aplicada e conferida).

1. **Implantar** → **T-01** (feito 01/10)
2. **O número de carro reserva da Yelum** → **T-48**
3. **Limpar as variáveis antigas de modelo** (P-121-07) → **T-07**
4. **Os acionamentos reais que faltam** (P-121-03) → **T-50**
5. **Decidir o "Admin Intervention"** (P-121-18). Quando alguém pausa uma conversa pelo painel, ela nunca volta ao agente,
   nem com mensagem nova depois de 7 dias. Opções: continuar assim (a pausa do painel é para sempre) · ou tratar como a regra
   dos 7 dias (mensagem nova depois de 7 dias volta ao agente). Recomendo **a regra dos 7 dias, 70 × 60** — as notas estão
   perto, então é escolha sua.
6. **Conferir o grupo da terceira corretora do piloto** (C3 no relatório): grupo de suporte **ativo** e agente **desligado**.
   O teste → **T-68**. A decisão (se o grupo dela continua ativo) segue sua.
7. **Pergunta que continua aberta para a atendente:** por qual canal a Allianz, a Bradesco e a HDI atendem carro reserva?
   Até ela responder, esses pedidos vão para uma pessoa da corretora, por decisão sua de 29/09.


---

## SPEC-122 — o agente pensa, com prova, e o GPT-6.1 Sol sucede o Sol 6 (30/09/2026)

⏳ **Os testes da SPEC-121 (bloco acima, S121.1 a S121.7) continuam pendentes** — você disse que faz no fim. Nada da 122
depende deles, e nada deles foi feito por aqui.

📊 O que mudou: o **GPT-6.1 Sol** substituiu o Sol 6 nos 7 trabalhos que usavam o Sol 6 e na reserva do acionamento, cada um
com o mesmo esforço de antes (a mudança no banco já foi aplicada e conferida; 📊 teste real com US$ 0,0073). O "cérebro" que
responde à seguradora quando a URA sai do roteiro foi **medido pela primeira vez** (📊 92 casos reais mascarados, 30/09):
nenhuma versão passou na régua de "zero erro grave", então **nada ganhou autonomia** — o acionamento continua no Opus 5.5,
e o cérebro novo só pode rodar **em sombra** (decide ao lado, não envia nada). O que muda para o segurado: na Porto, HDI,
Yelum e Zurich, quando a URA pede algo que só ele sabe (ex.: "o local é seguro, escuro ou deserto?"), o agente **pergunta
a ele** com as opções da tela, em vez de passar a uma pessoa.

1. **Implantar** → **T-01** (feito 01/10)
2. **Conferir três variáveis pelo nome** (P-122-02) → **T-07**
3. ⚠️ **(01/10) Substituído pela S123.3** — a sombra da 122 deu lugar ao destravador; este SQL agora põe o DESTRAVADOR em sombra.
   **Ligar a sombra, quando quiser** (P-122-16) — **não é obrigatório**, e não muda nada do que vai à seguradora nem ao
   segurado. Só depois do passo 1. No Supabase, **SQL Editor**, cole e rode (liga a sombra na **Porto**, para todas as
   corretoras):
   ```sql
   insert into public.cerebro_modos (company_id, insurer_key, ramo, modo, motivo, ligado_por)
   select id, 'porto', 'todos', 'sombra', 'SPEC-122: medir o cerebro V2 em sombra', 'Founder'
     from public.companies
   on conflict (company_id, insurer_key, ramo)
   do update set modo = 'sombra', motivo = excluded.motivo, ligado_por = excluded.ligado_por, updated_at = now();
   ```
   **Esperar:** "Success" e o número de linhas = o número de corretoras. Para conferir:
   ```sql
   select insurer_key, ramo, modo, count(*) as corretoras from public.cerebro_modos group by 1, 2, 3;
   ```
   → uma linha `porto · todos · sombra · N`. Vale em até 1 minuto.
   **Depois de alguns acionamentos da Porto**, para ver se ela está medindo e quanto custa:
   ```sql
   select count(*) as telas, min(created_at) as primeira, max(created_at) as ultima
     from public.work_events where event_type = 'cerebro.sombra';
   select count(*) as chamadas, round(sum(total_cost_usd)::numeric, 4) as dolares
     from public.token_usage_logs where service_type = 'cerebro_sombra';
   ```
   💭 Custo esperado: perto de US$ 0,02 a 0,03 por tela em que a URA sai do roteiro (📊 o Opus custou US$ 0,0209–0,0272 por
   chamada na bancada de 30/09). **Para desligar**, a qualquer momento:
   ```sql
   update public.cerebro_modos set modo = 'off', updated_at = now() where insurer_key = 'porto';
   ```
   ⚠️ O modo "ligado de verdade" **não existe**: o banco recusa. Ele só virá numa SPEC, depois de 2 semanas ou 50 telas
   reais em sombra sem erro grave (P-122-17).
   **Se der erro** `violates foreign key` ou `relation "cerebro_modos" does not exist`: a tabela não está no banco — mande o
   print no chat (a migration foi aplicada em 30/09 e conferida pelo juiz).
4. **O canário** (a pergunta ao segurado na tela de *situações de risco*) → **T-43**
5. **Autorizar, se quiser, ~US$ 0,50 para completar a medição do Opus** (P-122-03) — a bancada parou no teto de US$ 2 por
   provedor e mediu o Opus em 15 das 32 armadilhas. Não bloqueia nada; só deixa a comparação 6.1 × Opus completa.


## SPEC-123 — o agente destrava: decide, pergunta ao segurado, registra e aprende (01/10/2026)

⚠️ **Os testes das SPECs 121 e 122 (blocos acima) continuam pendentes** — nada da 123 depende deles.

📊 O que mudou: quando o roteiro fixo trava no WhatsApp da seguradora, existe agora um **destravador** — ele lê o caso, a
conversa com o segurado e as telas, e decide: seguir em frente ("Continuar"), responder com um dado que o caso já tem,
**perguntar ao segurado** o que só ele sabe, ou chamar uma pessoa no que é irreversível (custo, sinistro, cancelar, novo
pedido, trocar o titular, confirmar a abertura). Pela sua ordem (D5), ele foi **ligado** em todas as corretoras que têm agente de atendimento, nas 10
seguradoras (📊 01/10: `cerebro_modos` = 40 linhas `on`, limiar 70) — mas 📊 **0 de 4** agentes de atendimento estão ligados
hoje, então **nada acontece até você ligar o agente de uma corretora**. "Escolher sozinho entre opções" (o DEDUZIR) ficou **desligado**: 📊 o modelo acertou 6 de 14 vezes com
nota alta (`reports/SPEC-123-BANCADA.md`). Na bancada com 69 travas reais, 📊 **42 (61 %) foram destravadas certo sem
pessoa** e 62 (90 %) sem pessoa e com segurança — antes era 0 %.

🔴 **O que muda NO IMPLANTAR, mesmo sem ligar nada** (vale para todas as corretoras):
- a pergunta ao segurado passa a valer nas **10 seguradoras** (antes só Porto, HDI, Yelum e Zurich), com prazo de **2 min**
  na Allianz, Alfa, Mapfre e Azul e **3 min** nas outras; se a URA fechar antes da resposta, o caso fica guardado e é
  **reaberto** quando o segurado responder (no máximo 2 vezes), sem abrir pedido duplicado;
- `yelum/auto/guincho` passa a atender sozinho (📊 31 → 32 de 76 rotas);
- na Allianz residencial, a lista com **vários endereços** escolhe o endereço do caso (antes mandava "1" às cegas); se nenhum
  casar, vai a uma pessoa;
- o agente de atendimento, quando quer chamar uma pessoa por **dúvida** ou **dado que falta**, tenta resolver **uma vez**
  antes (1 por conversa por dia). Sinistro, condomínio, empresarial e quem **pede** uma pessoa continuam indo direto.

### S123.1 · Implantar
✅ **Feito em 01/10/2026** → **T-01**.

### S123.2 · Ver o diário
→ **T-43** (a linha em Decisões do agente e em `/admin/decisoes`) · **T-52** (as contagens e o custo, SQL) · **T-53** (isolado
entre corretoras).

### S123.3 · Ver, desligar ou só observar o destravador
📊 **Já está ligado** (migration `20261001_02`, 01/10): 10 seguradoras × 4 corretoras com agente de atendimento = 40 linhas
`on`, limiar 70 (D-123-K, decidida pela execução sob a sua D5). Ele só age quando o agente de atendimento da corretora estiver
ligado. Para mudar, no Supabase → **SQL Editor**, cole UM destes:

**Ver o que está ligado** (✅ conferido por você em 01/10 → **T-05**) — esperar 40 linhas, todas `on` e `70`:
```sql
select insurer_key, modo, limiar from cerebro_modos order by 1;
```
**Desligar UMA seguradora** (exemplo: Porto) — o roteiro volta a ser o de antes, nessa seguradora:
```sql
update cerebro_modos set modo='off' where insurer_key='porto';
```
**Só observar (sombra)** — ele anota no diário o que faria, mas não faz:
```sql
update cerebro_modos set modo='sombra' where insurer_key='porto';
```
**Desligar TUDO** — volta exatamente ao de antes:
```sql
delete from cerebro_modos where ligado_por='migration 20261001_02_spec123_destravador_ligado';
```
**O diário** — as últimas 20 decisões, em português:
```sql
select created_at, seguradora, classe, acao, nota, explicacao_para_gente from diario_de_decisoes order by created_at desc limit 20;
```
**Esperar hoje:** o diário **vazio** — é o certo enquanto nenhum agente de atendimento estiver ligado. **Se der erro** em
qualquer um destes comandos: mande o print no chat.

### S123.4 · Os testes reais sugeridos
→ Yelum guincho **T-45** · a pergunta ao segurado **T-43** (e o prazo **T-44**) · a dúvida simples **T-35** e a segunda chance
**T-36** · as rotas que faltam e os vários endereços da Allianz **T-50** e **T-47**.

### S123.5 · Decisões suas (`FOUNDER-DECISIONS.md`)
- **D-123-K** — onde ligar o destravador: **DECIDIDA pela execução** (sua D5, nota 85): ligado em todas as corretoras com
  agente de atendimento, nas 10 seguradoras. Para mudar, S123.3.
- **D-123-L** — o diário guardar a tela **completa** (com dado pessoal) para a corretora dona: coluna nova **65** × manter
  só a mascarada **60** — notas próximas, decisão sua.
- **D-123-M** — liberar o "escolher sozinho" sem calibração: manter desligado **85** × liberar **35** — já vem decidida;
  confirme se quiser.
- Verba opcional: 💭 ≈ US$ 1 por provedor para calibrar o "escolher sozinho" (P-123-01).

## SPEC-124 — o portal de vidros destrava com a mesma régua, e a leitura de documentos no modelo certo (01/10/2026)

📊 O que mudou:
- **A leitura de fotos e documentos ficou ~18 vezes mais barata, com o mesmo acerto medido.** A foto que o segurado manda
  (CNH, documento do carro, apólice fotografada) e a imagem dentro de PDF passam a ser lidas pelo **GPT-6 Luna** em vez do
  GPT-6.1 Sol: 📊 na bancada de 30 leituras, os dois acertaram **100 %** dos campos importantes (nome, CPF, placa, apólice,
  vigência, coberturas, valores), e a Luna custa 📊 US$ 0,0002 por leitura contra US$ 0,0037. ⚠️ Os documentos da bancada são
  **fabricados** (não havia documento real sem dado pessoal): o número é o melhor caso, não a garantia. Se a OpenAI cair, a
  foto passa ao **Claude Sonnet 5.5**. Isto **já está valendo no banco** e entra no ar no Implantar do `smith-api`.
- **O leitor de documentos (docling) passa a usar o modelo que o catálogo manda**, em vez de uma variável própria, e o custo
  dele passa a aparecer na conta.
- **O portal de vidros ganhou a mesma régua do WhatsApp**: quando o caminho novo do portal para numa pergunta, o mesmo
  destravador da SPEC-123 decide, continua o MESMO pedido (sem abrir outro) e anota no diário. 🔴 **Mas, hoje, ele não
  responde nada sozinho**: ele pergunta ao segurado ou chama uma pessoa — porque "escolher sozinho" segue desligado (SPEC-123)
  e porque o único caso em que respondia sozinho (o estado do serviço) estava **errado** e foi consertado para perguntar.
  E 📊 o portal de vidros **não roda desde 10/07**, e o caminho novo (onde isto foi plugado) **nunca rodou em produção** —
  ele só é usado se você ligar `PORTAL_VIDROS_API_FIRST` (D-124-F). O caminho antigo do portal continua como estava.

### S124.1 · Implantar
✅ **Feito em 01/10/2026** → **T-01**. O docling com imagem → **T-70**.

### S124.2 · Um teste real da leitura de foto
→ **T-69**.

### S124.3 · Decisões suas (`FOUNDER-DECISIONS.md`)
- **D-124-F** — ligar o caminho novo do portal de vidros (`PORTAL_VIDROS_API_FIRST`): **AUTORIZADA por você** — ligar junto com
  o primeiro canário de vidro, com allowlist. O passo a passo → **T-55** a **T-58**.
- Já decididas pela execução (confirme se quiser): Luna nas duas leituras (D-124-A, 88) · reserva só na foto (D-124-B, 85) ·
  caminho antigo do portal fora desta SPEC (D-124-C, 75) · o estado do serviço é perguntado (D-124-D, 92) · ordem do deploy
  (D-124-E, 85).
- Opcional, para fechar a dúvida da visão: ~10 fotos reais (CNH, documento do carro, apólice) **com os dados cobertos** para
  uma rodada da bancada (P-124-05).
