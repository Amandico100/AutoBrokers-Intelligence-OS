# SPEC-117 · LAUDO DO RED TEAM

> Opus 5.5 · 26/09/2026 · branch `spec/117-apolice-persistente` · diff `79c9e80..e49dfc7`
> Ataques rodam o **MOTOR** (`nodes.tool_node`, `attendance_ficha.fundir/gravar`,
> `policy_context` real, `_sanitize_policy`/`_sanitize_match`/`_canonical_customer_identity` reais).
> Dublês só na borda (ferramenta e Supabase de mentira), reusados do próprio harness da SPEC.
> Scripts: `<scratchpad>/redteam117/ataques.py` e `.../g6_e_hmac.py`.
> 📊 = medido, com o comando · 💭 = ilustrativo.
> ⛔ Nenhum arquivo de produto ou de teste foi alterado por mim: `git diff --stat -- backend`
> ao terminar → **vazio**. O `M backend/tests/test_a_atendente_na_ura_cala_o_robo.py` que aparece
> no `git status` já estava lá no status de abertura da sessão, e não foi tocado.
> Nenhuma mensagem, chamado, portal ou banco real tocado.
> 🔴 Eu **não** classifico blocker e **não** decido conserto (protocolo §2 é do executor).
> 📊 E os 53 guardas novos **passam** enquanto tudo abaixo acontece
> (`python -m pytest tests/test_o_atendimento_guarda_a_apolice.py tests/test_o_policy_context_e_puro.py
> tests/test_a_apolice_do_caso_atravessa_o_atendimento.py -q` → `53 passed in 29.30s`).

---

## O QUE EU QUEBREI

### R1 · 🔴 A apólice do caso é escolhida SEM olhar o ramo do PEDIDO — e depois SOBRESCREVE o ramo certo do modelo

**O caminho.** `policy_context._escolha_inicial` escolhe (a) o que a fonte escolheu, (b) a única
vigente. **Nunca** o ramo do que o segurado está pedindo. Em seguida `nodes.tool_node` (F3.1)
força `ramo_da_apolice` e `insurer_key` dessa apólice no `insurer_dispatch`, e
`_gravar_ficha_do_turno` (F3.3) grava `ficha["ramo"]`/`ficha["seguradora"]` dela — que é de onde
`graph._slots_obrigatorios_do_caso` resolve o CORREDOR do caso.
🔴 `policy_context.apolices_vigentes(contexto, ramo=…)`, a função que a SPEC §2/G5 apresenta como
"quem escolhe pelo ramo é o PEDIDO", **não é chamada em lugar nenhum de `backend/app`**:
`grep -rn "apolices_vigentes" backend/app` → 1 linha, e é o docstring do próprio módulo.
Ela só aparece em `tests/test_o_policy_context_e_puro.py` — guarda que prova o helper, não o motor
(CLAUDE.md §9.4). **G5 "Auto+Resi → serviço de casa escolhe resi sem perguntar" está NÃO PROVADO
no motor, e medido como FALSO abaixo.**

**Reprodução** — `python <scratchpad>/redteam117/ataques.py a1 a2`

```
A1 · casa alagada; o cliente tem 1 AUTO vigente e 1 RESI VENCIDA
selecionada automaticamente: ('A-0001', 'auto')
o modelo pediu        : ramo_da_apolice=residencial insurer_key=porto
o acionamento RECEBEU : ramo_da_apolice='auto' insurer_key='allianz'
ficha durável         : ramo='auto' seguradora='allianz' apolice='A-0001'
log: [APOLICE] ramo DIVERGENTE no acionamento: modelo='residencial' sistema='auto' — vale o sistema

A2 · AUTO e RESI as DUAS vigentes; turno 1 tratou do carro (a fonte escolheu a auto)
apolices no contexto: [('A-0001','auto',True), ('R-0002','resi',True)]
turno 2, "deu um vazamento em casa, pode acionar":
o acionamento RECEBEU : ramo='auto' seguradora='allianz'
ficha                 : ramo='auto' seguradora='allianz' apolice='A-0001'
```

**O que chega ao segurado.** Ele diz que a casa alagou; o produto abre (ou tenta abrir) a
assistência **de automóvel**, na **seguradora do carro**, com as teclas de URA do corredor `auto`
— e, como o corredor do caso passa a ser `auto`, a lista de obrigatórios e o texto ao humano vêm
todos do contrato errado. **Nada trava**: o segurado ouve "sua assistência foi aberta"
(CLAUDE.md §9.5, o defeito silencioso). Antes desta SPEC o `ramo_da_apolice` do modelo
("residencial") ia intacto — 📊 a linha que sobrescreve é nova no diff (`nodes.py`, F3.1) e a
divergência é **só logada**.

⚠️ **E o guarda novo fica verde**: `test_o_ramo_e_a_seguradora_do_sistema_vencem_o_palpite_do_modelo`
só mede o caso em que o pedido e a apólice são do MESMO ramo (uma resi, vazamento). A mutação que
prova o carimbo é a própria A1: nenhum dos 53 testes muda de cor.

---

### R2 · 🔴 O portal de vidros recebe a apólice AUTO ERRADA quando há duas vigentes

**O caminho.** `tool_node`/F3.2 injeta `policy_number` da apólice do caso sempre que a família é
`auto`, **sobrescrevendo** o número que o modelo escreveu. Com duas autos vigentes, a selecionada
é a que a fonte fixou num turno anterior — não a do dano.

**Reprodução** — `... ataques.py a3`
```
o modelo pediu policy_number=A-0002   (o vidro é do outro carro)
o portal RECEBEU policy_number='A-0001'
log: [APOLICE] apólice DIVERGENTE no portal: modelo='A-0002' sistema='A-0001' — vale o sistema
```
**O que chega ao segurado/corretora.** Pedido de vidro aberto no portal da seguradora **contra o
contrato errado** — sai da corretora como pedido válido. É exatamente o risco que o comentário de
`FAMILIA_DO_PORTAL` descreve, com a família certa e a APÓLICE errada.

---

### R3 · 🔴 A consulta FORÇADA do WhatsApp passou a ir SEM identidade — e o que volta vira a apólice oficial do caso

**O caminho.** `_policy_context_tool_args` (F3.5) trocou `else: return None` por
"tem `cliente_ref`?". No papel `attendance` **não há** `document`/`name`, então os `tool_args`
saem **sem identidade nenhuma**, com o `policy_number` que `_extract_context_policy_number`
tira do TEXTO do segurado (`nodes.py:346`, `re.search(r"\b[A-Za-z]?\d[A-Za-z0-9-]{4,}\b", text)`).
`agent_node:1502-1515` força essa chamada de verdade. O `lookup(policy_number=…)` sem documento é
busca **global na base da corretora** (`infocap_connector`, `global_search_used=True`, exato por
`numapo`), e o contexto que volta, sendo de OUTRO cliente, **substitui** o do caso
(`policy_context.fundir`: `cliente_ref` diferente → `novo`). A própria F3.5 reconheceu o problema
e travou **só** o ramo da LISTAGEM (`identity and len(candidates) > 1`); o ramo do NÚMERO ficou aberto.

**Reprodução** — `... ataques.py a9`
```
contexto (attendance) tem document/name? {'document': None, 'name': None}
tool_args FORCADOS: {'policy_number': '202623140269982', 'user_query': '...'}
CONTROLE — a versão de 79c9e80 tinha 'else: return None' antes do número: True
apolice do caso ANTES : 'A-0001'
apolice do caso DEPOIS: 'Z-9999'  (cliente_ref mudou? True)
ficha durável: apolice='Z-9999' ramo='residencial' seguradora='azul'
bloco ao modelo: "Apólice deste caso, veio do sistema de gestão — é ELA que vale, não o palpite:
                  Z-9999 · residencial · Azul · vigente até 01/03/2027"
```
**O que chega ao segurado/segurança.** Basta o segurado digitar, com um termo de detalhe na frase,
um número que exista na base da corretora (o da esposa, o da empresa, o de um vizinho, um que ele
viu) para o produto (1) consultar contrato de terceiro **sem verificar de quem é**, (2) adotá-lo
como a apólice do caso na ficha durável e (3) afirmar ao modelo que "é ELA que vale" — com ramo e
seguradora de outra pessoa indo ao acionamento. **Antes desta SPEC este caminho estava fechado
neste canal** (controle acima).

📊 **E o gatilho não é só má-fé:** `python <scratchpad>/redteam117/g6_e_hmac.py`
```
papel=attendance  consultas forçadas em 8 perguntas: ANTES=0 DEPOIS=2
   MUDOU: 'meu cep para o reboque e 01310900, tem cobertura?'
          antes=None  depois={'policy_number': '01310900', 'user_query': '...'}
```
Um **CEP** vira `policy_number` de uma consulta forçada.

---

### R4 · 🔴 PII CRUA (CPF + nome completo) passou a ser gravada em `conversations.ficha_atendimento`

**O caminho.** `policy_context._derivar_chaves_legadas` copia `document` e `name` crus no papel
`core` (exceção declarada na §2). `tool_node` → `_gravar_apolice_do_caso`/`_gravar_ficha_do_turno`
→ `novidades_da_apolice(contexto)` grava o **contexto inteiro** em `ficha["apolice_do_caso"]`.
📊 Até 79c9e80 **ninguém** escrevia essa chave (a própria SPEC mede isso), então é PII nova em
repouso, numa coluna que o painel do Founder lê.

**Reprodução** — `... ataques.py a7`
```
PII na ficha gravada: ['CPF', 'nome:Cliente', 'nome:Teste', 'nome:Sintetico']
ficha['apolice_do_caso'] document='39053344705' name='Cliente De Teste Sintetico'
bloco do prompt (limpo): 'Apólice deste caso … A-0001 · auto · Allianz · vigente até 01/03/2027'
```
**Onde vaza e onde NÃO vaza.** ⛔ Não vaza para o prompt (a lista branca de `_bloco_da_apolice`
segura) — vaza para **o banco e a tela**. ⚠️ Alcance maior do que "o Chat Principal": `_papel_do_agente`
devolve `"core"` por **padrão** quando `agent_data.agent_role` está vazio, e o guarda de PII da
costura (`test_...atravessa_o_atendimento`) só varre a ficha do papel `attendance` — é por isso
que ele fica verde.

---

### R5 · `_escolha_inicial` escolhe uma VENCIDA quando a fonte se contradiz, e `apolices_vigentes` devolve vencida

`_selecionavel` só é aplicado ao ramo (a) da escolha; o ramo (b) ("exatamente UMA vigente")
**não passa por ele**. `vigente = active_now is True and not cancelada` ignora `expirada`.

**Reprodução** — `... ataques.py a5` (`active_now=True` + `expired=True`)
```
resumo: {... 'vigente': True, 'expirada': True, 'cancelada': False}
selecionada (deveria ser None): 'A-0001'
apolices_vigentes devolve a VENCIDA? ['A-0001']
```
Contradição vem da fonte, então a reprodução parte de `_sanitize_policy` real com `expired`
forçado. **Gravidade real hoje: baixa** (`_active_expired` é coerente); o que fica medido é que a
trava do G5 **não está** nos dois ramos da escolha nem no leitor de vigentes.

### R6 · `policy_status: "cancelado"` é ignorado — no shape de `_sanitize_match` uma CANCELADA é selecionável

**Reprodução** — `... ataques.py a6` (função REAL `_sanitize_match(doc com cancelado="S")`)
```
keys: [... 'policy_status', 'product']   → tem 'cancelled'? False ; tem 'expired'? False
policy_status='cancelado'
resumo: {... 'vigente': False, 'expirada': False, 'cancelada': False}
selecionada: 'A-0001'   |   escolher_apolice aceita a cancelada? True
```
`policy_context` nunca lê `policy_status`. Hoje `_sanitize_match` só alimenta
`status="ambiguous_customer"` (`infocap_connector.py:1241`), onde a escolha não roda — a porta que
segura é de OUTRO arquivo. 🔴 Basta um caminho novo devolver esse shape com `status="found"` para
uma apólice **cancelada** virar a apólice do caso, sem guarda que grite.

### R7 · Vigência DESCONHECIDA vira "é ELA que vale"

`fimvig` ausente/ilegível → `_active_expired` devolve `active_now=None, expired=None` →
`expirada=False` → selecionável → selecionada.
**Reprodução** — `... ataques.py a4`
```
sanitizado real: active_now=None expired=None cancelled=False policy_status='ativo'
selecionada: {'numapo': 'A-0001', 'vigencia_fim': None, 'vigente': False, 'expirada': False}
bloco ao modelo: 'Apólice deste caso, veio do sistema de gestão — é ELA que vale, não o palpite: …'
```
O produto afirma autoridade sobre uma apólice que ele **não sabe** se está valendo (e o texto
muda de "vigente até" para nada, sem dizer ao modelo que não sabe).

### R8 · A apólice do caso TROCA em silêncio quando a selecionada vence ou sai da lista

**Reprodução** — `... ataques.py a15`
```
anterior.selecionada -> 'A-0001' (auto)
depois de A-0001 vencer     : selecionada='R-0002'   (a resi, de outro ramo)
depois de A-0001 desaparecer: selecionada='R-0002'
novo=None -> preserva o anterior? True   (este lado está certo)
```
`fundir` corretamente recusa herdar a vencida, mas devolve o `novo`, cuja auto-escolha "única
vigente" fixa **outro contrato** — e ninguém avisa. Somado a R1, o acionamento seguinte sai com o
ramo/seguradora dessa outra apólice.

### R9 · `_gravar_ficha_do_turno` grava contexto de OUTRA corretora (a trava está só no outro escritor)

`_gravar_apolice_do_caso` tem a trava (`contexto.company_id != state.company_id → não grava`);
`_gravar_ficha_do_turno` → `novidades_da_apolice` **não tem**, e `_contexto_da_apolice_do_turno`
confere o tenant só no caminho da FICHA, nunca no caminho do ESTADO (que é o primeiro).
**Reprodução** — `... ataques.py a8`
```
contexto usado veio do tenant 1111…  ; o turno é do tenant 2222…
o acionamento do tenant B RECEBEU: ramo='resi' seguradora='porto'
linha gravada: ('2222…','whatsapp:…') → apolice_do_caso.company_id = '1111…', cliente_ref e
               numapo da corretora A
```
⚠️ **Alcançabilidade honesta:** o checkpoint é `thread_id = f"{company_id}:{session_id}"`
(`graph.py:1778`), então o caminho normal não cruza tenants hoje. Alcança por qualquer chamador
que monte o `state` (bancada, replay, script, backfill). Registro porque é a mesma regra que o
próprio `attendance_ficha.fundir` escreve: *"uma trava que depende de quem chama não é trava"*.

### R10 · Sem a env var, o `cliente_ref` cai por força bruta em 0,1 s — e a presença é medida por `os.getenv`

**Reprodução** — `python <scratchpad>/redteam117/g6_e_hmac.py`
```
chave de plataforma presente? False
alvo=f4af36d9c599356077cbe7db revertido=(codfil 1, codigo 7788) em 7789 tentativas / 0.1 s
(88.328 HMAC/s num notebook)
```
A constante de fallback está no fonte, como o módulo admite. 🔴 O que o módulo **não** considera:
`_segredo_do_hmac` usa `os.getenv("ENCRYPTION_KEY")`, e o resto do produto lê a chave por
`Settings` com `env_file = ".env"` (`app/core/config.py:172-173`) — pydantic lê o ARQUIVO e **não**
popula `os.environ`. Se em produção a chave chega por `.env` em vez de variável de ambiente real,
todo `cliente_ref` é reversível **e nada alerta**. Comando que decide:
`docker exec <container> printenv ENCRYPTION_KEY` (não executado — não tenho o contêiner).

### R11 · O log novo do portal imprime o número da apólice inteiro

`nodes.py` F3.2: `logger.warning("[APOLICE] apólice DIVERGENTE no portal: modelo=%r sistema=%r")`
📊 enquanto `infocap_tool.py:698` loga `numero[:6] + "***"`. Duas práticas para o mesmo dado no
mesmo produto. Nenhum outro log novo carrega CPF, nome, telefone, locator ou `product` cru —
varri os cinco `logger.*` acrescentados.

---

## O QUE EU TENTEI E NÃO QUEBREI

| ataque | o que me barrou |
|---|---|
| PII no **prompt** e nos `tool_args` | `policy_context._resumo_da_apolice` é lista branca fechada e `attendance_ficha._bloco_da_apolice:682-690` só imprime numapo/ramo/seguradora/vigência. `_policy_context_tool_args` nunca manda locator; e CPF na frase corta a consulta antes (`nodes.py:380`, `_DOCUMENT_IN_TEXT_RE`) |
| locator cru (`infocap:<codfil>:<nosnum>`) no contexto, na ficha ou no aviso ao humano | `chave_da_apolice` → `policy_facts._locator_hash`; varredura recursiva de valores em A7/A9 não achou `infocap:` |
| papéis inesperados (`"Core"`, `"CORE"`, `" core "`, `"core(legado)"`, `""`, `None`, `"insured_external"`, `"auxiliary"`, inventado) | `... ataques.py a12`: só `("", "core")` normalizados copiam identidade crua, e no papel mascarado não existe identidade crua no `data` para copiar. ⚠️ divergência sem efeito hoje: `policy_context` faz `.strip().lower()`, `infocap_tool._unmasked` compara exato — `"Core"` copiaria se algum chamador entregasse `data` cru com esse rótulo |
| `company_id` vazio/`None`/só espaços | `... ataques.py a14`: sem tenant **não nasce** contexto (as três dão `False`) |
| dois tenants com o mesmo `codfil:codigo` | `cliente_ref` diferente (o `company_id` está dentro do material do HMAC) — G9 se sustenta |
| outro cliente da mesma corretora sem `codigo`/`codfil` | `... ataques.py a13`: `cliente_ref=None` e `mesmo_cliente(ctx, ctx) = False` — não se herda de quem não se sabe quem é |
| consulta que não trouxe nada apagar a apólice | `fundir(anterior, None)` devolve o anterior **intacto** (A15) |
| falha de gravação da ficha derrubar o turno ou o estado | `... ataques.py a10`: `turno sobreviveu: True ; contexto no estado: True` — cai no `state`, como a §7 promete |
| retomada por processo novo (só ficha) | os guardas G8 da SPEC rodam o `tool_node` com checkpoint vazio e passam; reproduzi e confirmei |
| assunto novo herdar a apólice | `attendance_ficha.fundir` faz `pop` das duas chaves na troca de `assunto_id` — e o controle do mesmo assunto também passa |
| 🔴 piorar o laço do Chat Principal (G6) | `g6_e_hmac.py`: `papel=core … ANTES=4 DEPOIS=4` em 8 perguntas, com a função de `79c9e80` executada de verdade lado a lado. **Não piorou.** ⚠️ No `attendance` subiu de 0 para 2/8 (intencional na F3.5, mas é consulta nova por turno de anáfora — e é por ela que R3 entra) |
| testes pré-existentes afrouxados | li asserção por asserção os 5 arquivos (`git show 79c9e80:<arquivo>`): os 4 do SPEC-016 só ganharam `company_id=`/`papel="core"` e contextos vindos do construtor real, com as mesmas afirmações — e um controle NOVO ("o lookup falho AINDA produz contexto"). ⚠️ Uma régua **foi** afrouxada, com razão escrita: `test_spec116_…` trocou `== 3` por `== manifesto and >= 3`. O controle que a acompanha (`test_c8_CONTROLE_…`) afirma `not (4 == 3)` sobre inteiros escritos à mão — **não chama** `_oraculo_p19a()` nem `B.manifesto()`, então é carimbo (CLAUDE.md §9.4), não guarda |

---

## NÃO EXECUTADO — exigiria efeito real

- **Acionamento duplicado com seguradoras diferentes.** A trava do `dispatch_router` é por
  **telefone da seguradora** (`dispatch_already_active`, `dispatch_router.py:2180`). Um acionamento
  que saiu com a seguradora do MODELO e um segundo, depois de o contexto nascer, com a do SISTEMA,
  usam telefones diferentes → dois chamados reais para o mesmo caso. 📊 `... ataques.py a11` mostra
  que o `tool_node` não deduplica (2 chamadas em 2 mensagens iguais); o resto exigiria WhatsApp real.
- **Colisão real de `numapo` com CEP/telefone digitado** (R3 sem má-fé): exigiria `SELECT` na base
  InfoCap da corretora, que não é o Supabase.
- **Portal de vidros real** com a apólice errada de R2.
- **`printenv ENCRYPTION_KEY` no contêiner** (R10).

## GRAVIDADE (teste do produto do protocolo §2 — eu meço, não classifico)

| # | SEGURADO | CORRETORA | BANCO | SEGURANÇA |
|---|---|---|---|---|
| R1 ramo/seguradora do sistema vencem o pedido | ✅ mensagem, protocolo, prazo | ✅ corredor e handoff | ✅ ficha | — |
| R2 portal com a auto errada | ✅ pedido no contrato errado | ✅ | — | — |
| R3 consulta forçada sem identidade | ✅ | ✅ | ✅ ficha | ✅ contrato de terceiro |
| R4 CPF/nome na ficha durável | — | ✅ tela do painel | ✅ | ✅ LGPD · OWASP LLM02 |
| R5 vencida selecionável (ramo b) | ✅ (se a fonte contradiz) | — | ✅ | — |
| R6 `policy_status` ignorado | ✅ (shape `_sanitize_match`) | — | ✅ | — |
| R7 vigência desconhecida como oficial | ✅ | ✅ | ✅ | — |
| R8 troca silenciosa de apólice | ✅ | ✅ | ✅ | — |
| R9 ficha de outra corretora | — | ✅ | ✅ | ✅ isolamento |
| R10 `cliente_ref` reversível sem env var | — | — | — | ✅ pseudonimização |
| R11 numapo inteiro no log | — | — | — | ⚠️ inconsistência |

## O QUE EU NÃO OLHEI

Lado **A** (aquisição: `PolicyDataProvider`, `infocap_connector.lookup`, Docling, `policy_facts`) —
só as funções que eu usei como borda · a bancada (`bancada_gerar_corpus.py`, `casos.jsonl`, 577+91
linhas de diff) e os LEIAME/MANIFESTO · `o_fim_do_atendimento.py` além do que o `tool_node` chama ·
RLS/policies no Postgres (só li que o backend é service role) · frontend e painel · custo/latência
das consultas novas em produção · `escolher_apolice`/`classificar_vigencia` do
`policy_data_provider` (motor upstream da escolha) · concorrência real de dois processos no mesmo
`session_id`.

## NOTA

**62/100.** Critério: a peça faz o que prometeu no eixo que ela mediu (a porta abre no WhatsApp, a
lista branca segura o prompt, o tenant entra no pseudônimo, a retomada e o `fundir` são
conservadores, e o laço do Chat Principal não piorou — tudo medido acima). Perde porque as duas
coisas que ela passou a DECIDIR pelo produto — qual apólice é a do caso e o que sobrescreve o
pedido do modelo — decidem **sem olhar o ramo do pedido** (R1/R2/R8) e a consulta forçada nova
**abandonou a trava de identidade** (R3), os dois em caminhos que terminam em mensagem, URA e
portal, com 53 guardas verdes ao lado.
