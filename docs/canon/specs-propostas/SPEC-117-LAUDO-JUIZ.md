# SPEC-117 · LAUDO DO JUIZ FRESCO

> Opus 5.5 · 26/09/2026 · branch `spec/117-apolice-persistente` · diff `79c9e80..e49dfc7`
> Read-only: nenhum arquivo de produto ou de teste alterado (as duas mutações foram aplicadas
> em cópia e restauradas — `git diff --stat -- backend/app` vazio ao fim, md5 conferido).
> 📊 medido · 💭 ilustrativo (CLAUDE.md §12.1)

---

## VEREDITO

**REPROVA** — três blockers, todos com conserto local e nenhum deles de desenho.

A arquitetura está certa e é a que a SPEC prometeu: **uma** autoridade
(`app/services/policy_context.py`, puro), **um** escritor do estado
(`nodes.py:2555`), **um** escritor da ficha (`attendance_ficha.fundir:440`, alimentado só por
`novidades_da_apolice`), **nenhuma** migration, **nenhum** motor paralelo. Os testes novos
chamam o MOTOR (`tool_node` real, `fundir`/`gravar`/`bloco_para_o_prompt` reais, dublê só na
borda) e eu provei por mim mesmo que dois deles **conseguem ficar vermelhos**. O BLOCO 0 é
honesto ao ponto de refutar a premissa herdada (B0.6).

O que reprova são três coisas que **mudam bytes**: CPF cru gravado em coluna durável no papel
`core`; a consulta ao sistema de gestão **executada duas vezes** para a mesma mensagem (a
linha de controle da própria bancada ficou vermelha); e o ramo/seguradora do sistema
sobrescrevendo o pedido **sem conferir se a apólice do caso serve o serviço pedido**.

---

## BLOCKERS

### B1 · O CPF e o nome do cliente passam a ser GRAVADOS em coluna durável (papel `core`)

**Teste do produto:** muda o BANCO e a SEGURANÇA — dado pessoal cru passa a persistir em
`conversations.ficha_atendimento`, que hoje não guarda nenhum, e que o painel do Founder lê.
É exatamente a linha de risco que a própria SPEC §7 escreveu (*"PII escapa pelo campo durável
novo → incidente LGPD (o painel lê a ficha)"*); a mitigação declarada ("lista branca") é
derrotada pela exceção do papel `core`, porque `novidades_da_apolice` grava o contexto
**inteiro**.

**Onde:**
- `backend/app/services/policy_context.py:371-379` — a exceção legítima da lista branca
  (`document`/`name` crus quando `papel in ("", "core")`).
- `backend/app/services/attendance_ficha.py:655` — `novidades_da_apolice` põe o contexto
  inteiro em `ficha["apolice_do_caso"]`, **sem projetar a lista branca**.
- `backend/app/agents/nodes.py:2558-2560` — `_gravar_apolice_do_caso` é chamado **sem
  nenhuma trava de papel**.

**Medição (pelo MOTOR, `tool_node` real, Supabase de mentira):**

```
[attendance] data tem client_document? False | mascarado? True
[attendance] ficha GRAVADA no banco? True
[attendance] PII na ficha durável: nenhum
[core]       data tem client_document? True | mascarado? False
[core]       contexto nasceu? True | chaves extras: ['document', 'name']
[core]       ficha GRAVADA no banco? True
[core]       PII na ficha durável: ['CPF', 'nome:Cliente', 'nome:Teste', 'nome:Sintetico']
[core]       chaves de apolice_do_caso: [... 'document' ... 'name' ...]
```

(script em `scratchpad/ataque5_motor.py`, reaproveitando o harness real do próprio
`tests/test_a_apolice_do_caso_atravessa_o_atendimento.py`.)

**Alcance real, 📊 medido no banco (`dcajcvlzcjbmyapmklil`, 26/09/2026):**

```sql
select agent_role, capability_key, enabled from capability_bindings
 where capability_key like '%infocap%';
-- attendance | operational.infocap.policy_lookup.read | true
-- core       | operational.infocap.policy_lookup.read | true      <- o papel core CONSULTA

select a.agent_role,
       count(*) filter (where c.ficha_atendimento <> '{}'::jsonb) as com_conteudo,
       count(*) as total
  from conversations c left join agents a on a.id = c.agent_id group by 1;
-- core | 0 | 79      <- hoje NENHUMA das 79 fichas de core tem conteúdo
-- (column_default = '{}'::jsonb, is_nullable = NO, data_type = jsonb)
```

Ou seja: a linha existe (o UPDATE acha), o papel `core` consulta a InfoCap, e a **primeira**
coisa que esta SPEC escreve nessa ficha é o CPF.

**Conserto (≤ 10 linhas):** projetar a lista branca na saída — `novidades_da_apolice` grava
o contexto **sem** `document`/`name` (ou `_gravar_apolice_do_caso` grava só o que a §2 marca
como durável). ⚠️ O `state` pode continuar com as chaves cruas: `_policy_context_tool_args`
depende delas hoje no Chat Principal. O que não pode é **persistir**.
🔴 E o guarda que fecha a porta: o teste de PII rodando com `papel="core"`, não só
`attendance` — hoje nenhum dos 40 testes novos varre o caminho `core` → ficha.

---

### B2 · A mesma mensagem dispara DUAS consultas ao sistema de gestão (G6 e G10 vermelhos)

**Teste do produto:** muda a CORRETORA (duas chamadas ao sistema de gestão dela por
mensagem, e o `content` da tool volta duas vezes ao modelo) e **quebra dois gates da própria
SPEC**. A §3 da SPEC é explícita: *"o laço de consultas forçadas … esta SPEC não o conserta,
e **o G6 não pode piorá-lo**"*. Piorou: o laço, que antes não existia no canal do segurado
(a função devolvia `None` sem identidade crua), passou a existir.

**Onde:** `backend/app/agents/nodes.py:418` (F3.5) —
`if not identity and not str(context.get("cliente_ref") or "").strip(): return None`.

**Medição — o gate da bancada, como entregue:**

```
$ python -m pytest tests/test_spec116_bancada_gates.py tests/test_spec116_bancada_corpus.py -q
FAILED tests/test_spec116_bancada_gates.py::test_linha_de_controle_separa_perfeito_de_burro[atendimento-N2]
AssertionError: [('atd-n2-identidade-mascarada', ['efeitos_exatos'], None),
                 ('atd-n2-handoff-leva-a-apolice', ['efeitos_exatos'], None)]
assert 0.9047619047619048 == 1.0
```

O veredito do avaliador: **"Efeito DUPLICADO: 1 execução(ões) a mais com a mesma chave."**
O rastro mostra a MESMA chave de efeito `3c0ee80f4a3bf6c0` duas vezes, para a MESMA
`mensagem_atual`, com o modelo tendo pedido a tool **uma** vez:

```
efeitos = [
 {"tool":"infocap_policy_lookup","chave":"3c0ee80f4a3bf6c0",
  "args":{"policy_number":"918305498337572","selected_policy_number":null, ...}},
 {"tool":"infocap_policy_lookup","chave":"3c0ee80f4a3bf6c0",
  "args":{"policy_number":"918305498337572","selected_policy_number":"918305498337572", ...}},
 {"tool":"insurer_dispatch", ...}]
tool_calls = [{"name":"infocap_policy_lookup", ...}, {"name":"insurer_dispatch", ...}]
#            ^ UMA consulta pedida pelo modelo, DUAS executadas
```

**🔴 A LINHA DE CONTROLE que dá direito à conclusão (CLAUDE.md §9.2 · protocolo §0.3):**
desliguei SÓ a porta da F3.5 (`if not identity: return None`) e rodei os dois mesmos casos:

```
atd-n2-identidade-mascarada PASS | lookups= 1 | falhas= []
atd-n2-handoff-leva-a-apolice PASS | lookups= 1 | falhas= []
```

Um fator, um resultado: **a causa é a porta da F3.5, e mais nada.** (Arquivo restaurado por
cópia; md5 conferido.)

**Conserto:** a consulta forçada só deve disparar quando ela **acrescenta** fato — não quando
o `policy_number` que ela vai mandar é o que o contexto já tem (`selected_policy_number ==
policy_number` → não force). Alternativa: idempotência por turno (um `lookup` por mensagem,
já que o memo do turno existe: `memo_da_apolice`).

---

### B3 · O ramo e a seguradora do sistema vencem SEM conferir se a apólice serve o serviço pedido

**Teste do produto:** muda o que chega ao SEGURADO. O acionamento sai para a **seguradora
errada**, com o **ramo errado**, e não trava — é o defeito silencioso do CLAUDE.md §9.5
(*"um passo que responde errado é silencioso e chega ao cliente"*), e é a linha de risco nº 1
da própria SPEC §7, cuja mitigação declarada ("G5 desambiguação") **não está ligada**.

**Onde:** `backend/app/agents/nodes.py:2251-2278` — o override de `ramo_da_apolice` e
`insurer_key` no `insurer_dispatch` é incondicional na família da apólice. ⚠️ O caminho do
PORTAL, no mesmo diff, TEM esse guarda (`FAMILIA_DO_PORTAL = "auto"`, nodes.py:520-529) —
quem escreveu reconheceu o risco num consumidor e o omitiu no outro.

**Medição (pelo MOTOR, `tool_node` real, `_data_do_conector` das funções REAIS do conector):**

```
--- SÓ RESI vigente + segurado diz "quebrou o parabrisa do meu carro" ---
  SELECIONADA: R-0002 resi
  MODELO pediu      : {ramo_da_apolice: auto,        insurer_key: allianz, servico: vidros}
  SEGURADORA recebeu: {ramo_da_apolice: resi,        insurer_key: porto,   servico: vidros}
  FICHA ramo/seguradora: residencial / porto

--- SÓ AUTO vigente + modelo pede encanador (serviço de casa) ---
  MODELO pediu      : {ramo_da_apolice: residencial, insurer_key: porto,   servico: encanador}
  SEGURADORA recebeu: {ramo_da_apolice: auto,        insurer_key: allianz, servico: encanador}
  FICHA ramo/seguradora: auto / allianz
```

Um chaveiro/parabrisa de CARRO sai para a seguradora da casa; um ENCANADOR sai para a
seguradora do carro. E o efeito não para no acionamento: a ficha recebe `ramo=residencial`,
e `graph._slots_obrigatorios_do_caso` (graph.py:798) resolve o corredor **residencial** para
um caso de carro — a lista de obrigatórios do caso inteiro passa a ser a errada.

**A causa de raiz, 📊 medida:** a escolha por SERVIÇO que o G5 promete
(*"Auto+Resi → serviço de casa escolhe `resi` sem perguntar"*) foi **construída e nunca
ligada**:

```
$ grep -rn "apolices_vigentes\|escolher_apolice" backend/app --include=*.py
# ZERO chamadas a policy_context.apolices_vigentes(...) e a policy_context.escolher_apolice(...)
# fora do próprio módulo. (As ocorrências em infocap_tool/policy_data_provider são a função
# HOMÔNIMA e pré-existente do provider, não esta.)
```

E com Auto+Resi as duas vigentes, `selecionada` volta `None` (medido) — ninguém escolhe pelo
pedido. O override só age quando há UMA vigente, que é justamente o caso em que ela pode não
ser a do serviço.

**Conserto:** o override só vale quando a família da apólice do caso é compatível com o
serviço/linha pedido — o mesmo guarda que o portal já tem. Sem compatibilidade: não
sobrescrever, e (melhor) escolher com `apolices_vigentes(contexto, ramo=<linha do pedido>)`.

---

## PENDÊNCIAS (não bloqueiam — registrar)

1. **`vigente` não exclui `expirada`.** `policy_context.py:213` —
   `vigente = active_now is True and not cancelada`. O caminho 2 de `_escolha_inicial`
   (`policy_context.py:346-348`) filtra por `vigente`, **não** por `_selecionavel`. 📊 Medido:
   `{"active_now": True, "expired": True}` → `selecionada=902, expirada=True` — uma apólice
   VENCIDA selecionada, contra o G5. ⚠️ **Hoje é latente, não vivo**: `infocap_connector
   ._active_expired` (api/infocap_connector.py:869-885) deriva `active` e `expired` do MESMO
   `valid_to`, então a combinação não sai da fonte real. Basta um segundo escritor de
   `active_now` para virar defeito vivo. Conserto de uma linha: usar `_selecionavel` também
   no caminho 2.
2. **A métrica de divergência grita sem motivo.** `nodes.py:2050-2058` compara o valor CRU do
   modelo com a **LINHA DO CORREDOR** do sistema, sem passar por `familia_de_ramo` — ao
   contrário do `insurer_dispatch`, que normaliza. 📊 Toda rodada da bancada imprime
   `[APOLICE] ramo DIVERGENTE na ficha: modelo='resi' sistema='residencial' — vale o sistema`,
   com modelo e sistema **concordando**. O byte gravado está certo; a métrica é que fica
   inútil — e um alarme que grita sempre é desligado quando a divergência for real.
3. **HMAC sem chave de plataforma.** `policy_context.py:90-97` tem
   `DERIVACAO_SEM_CHAVE_DE_PLATAFORMA`, um segredo que não é segredo, quando nem
   `POLICY_CONTEXT_HMAC_KEY` nem `ENCRYPTION_KEY` estão no ambiente. 📊 No meu ambiente
   `chave_de_plataforma_presente()` = **False**. Em produção **não é alcançável**:
   `core/config.py:38` declara `ENCRYPTION_KEY: str` sem default (obrigatória). ⚠️ Mas (a) a
   SPEC §2/D3 diz "HMAC-SHA256 com chave de plataforma" e **não declara o fallback**, e
   (b) `chave_de_plataforma_presente()` não tem nenhum chamador — ninguém seria avisado.
   Declarar na SPEC e logar a ausência uma vez no arranque.
4. **O `pop` da trava cross-tenant em `fundir` é código morto.**
   `attendance_ficha.py:432-440`: no caso de corretora diferente faz
   `nova.pop(CHAVE_DA_APOLICE)` e, três linhas abaixo,
   `if _tem_valor(novidades.get(CHAVE_DA_APOLICE)): nova[CHAVE_DA_APOLICE] = …` o repõe — e
   `novidades_da_apolice` sempre manda as duas chaves juntas. O docstring diz *"nunca funde
   com esta ficha"*; o código **substitui**. ⛔ **Não é vazamento provado**: a trava real está
   em `_gravar_apolice_do_caso` (nodes.py:625-628) e em `carregar` (filtro por `company_id`),
   e as duas passaram nos meus ataques. É a defesa em profundidade que está mais fraca do que
   o comentário afirma — e o teste
   `test_a_apolice_de_outra_corretora_NUNCA_funde_com_esta_ficha` tem nome mais forte do que
   o que ele prova (ele afirma a SUBSTITUIÇÃO).
5. **`policy_context.escolher_apolice` não tem chamador em `backend/app`** — peça pronta e
   desligada, com testes. Aceitável (CLAUDE.md §11.1), mas vai para `PENDENCIAS.md` com o que
   destrava: é ela que persistiria a escolha do segurado sem depender de reconsulta.
6. **B0.5b é impreciso.** A SPEC afirma *"ZERO — `selected_policy_ramo` não aparece em
   `backend/tests`"*. 📊 `git grep -c selected_policy_ramo 79c9e80 -- backend/tests` →
   **75 ocorrências** em `corpus/bancada/RESULTADOS/chat_principal_N2_23e6cfa2….json`. Em
   `backend/tests/*.py` é zero (confirmado). Corrigir a frase, não o número.
7. **Um controle que não controla.** `test_spec116_conserto_unico.py:
   test_c8_CONTROLE_a_divergencia_de_versao_seria_vista` afirma `not (4 == 3)` sobre literais
   — prova o `==` do Python, não o guarda de cima. O resto da mudança nesse arquivo é
   legítima (§9.3: a lição migrou de `== 3` para "corpus e manifesto não divergem" + piso).
8. **O relatório ainda não fecha a polícia do protocolo.**
   `pytest tests/test_o_protocolo_tem_policia.py` →
   `FALHA SPEC-117-EXECUTION-REPORT.md: sem a contagem da bateria (rodadas) · sem a nota
   0–100 da execução`. Esperado no passo ④ (a bateria é o ⑦), mas **é gate de entrega**: sem
   isso a SPEC não fecha.

---

## EVIDÊNCIA — gate por gate

| gate | veredito | a medição |
|---|---|---|
| **G1** o contexto nasce no core **e** no atendimento | **PASS** | `tool_node` real, `data` do conector mascarado → contexto nasce (`[attendance] contexto nasceu? True`, ataque 5); controle interno `test_linha_de_controle_no_core_o_contexto_ja_nascia`; **mutação 1** (porta volta a exigir identidade crua) → **15 failed, 5 passed** nos dois arquivos novos |
| **G2** PII não vaza | **FAIL** (papel `core`) · PASS (`attendance`) | ver **B1**: `['CPF','nome:Cliente','nome:Teste','nome:Sintetico']` na ficha durável. O guarda de PII existe e é honesto (varre VALORES, tem controle, e monkeypatcha `_resumo_da_apolice` para provar que fica vermelho) — só **nunca roda com `papel="core"`** |
| **G3** ramo oficial vence o palpite | **PASS mecanicamente · FAIL na resposta** | o override chega ao `insurer_dispatch` (medido: modelo `auto` → seguradora recebe `resi`) e a **mutação 2** (modelo volta a vencer) deixa 4 testes vermelhos, entre eles os dois nominais. Mas ver **B3**: vencer sem conferir o serviço é o §9.5 |
| **G4** seguradora e apólice persistem | **PASS parcial** | `ficha["apolice"] = 'A-0001'` STRING + `apolice_do_caso` DICT (medido por mim); `_linha_da_apolice` recebe string (teste deles). ⚠️ Não re-medi 6+ turnos ponta a ponta: o caso N2 que faria isso (`atd-n2-handoff-leva-a-apolice`) está **vermelho por B2** |
| **G5** duas vigentes desambiguadas; vencida nunca | **PARTE PASS / PARTE NÃO IMPLEMENTADA** | vencida/cancelada nunca `selecionada`: **PASS** em 9 cenários que eu rodei (vencida como `matches[0]`, vencida única, cancelada única, vencida como `selected` da fonte, cancelada como `selected`, `escolher_apolice` com chave de vencida → `ValueError`, `fundir` reintroduzindo seleção que venceu → `None`). ⛔ **"serviço de casa escolhe `resi` sem perguntar": não existe** — `apolices_vigentes(contexto, ramo=…)` tem ZERO chamadores em `backend/app`; com Auto+Resi vigentes, `selecionada=None`. Ver pendência 1 para o buraco latente |
| **G6** sem consulta repetida | **FAIL** | 2 execuções de `infocap_policy_lookup` com a mesma chave `3c0ee80f4a3bf6c0` para a mesma mensagem, com 1 `tool_call`; causa isolada por linha de controle (ver **B2**) |
| **G7** compressão não apaga estado | **PASS** | `test_a_apolice_sobrevive_a_compressao_da_toolmessage` passa e fica **vermelho** sob a mutação 2 — logo guarda o fato, não a serialização |
| **G8** retomada | **PASS** | `test_a_apolice_volta_da_ficha_quando_o_processo_reiniciou` passa e cai nas DUAS mutações; `_contexto_da_apolice_do_turno` confere `company_id` **na volta** da leitura durável (nodes.py:571-574) |
| **G9** dois tenants | **PASS** | mesmo `codfil:codigo` em A e B → `f4af36d9c599356077cbe7db` ≠ `6553789a2f0faa884669e162`; `mesmo_cliente(A,B)=False`; `fundir(A,B).company_id = B` (nunca mistura); escrita de contexto alheio recusada com `logger.error` (nodes.py:625-628). Ver pendência 4 para a profundidade |
| **G10** sem efeito duplicado | **FAIL** | `dup = 1` em 2 das 21 trajetórias N2, com o **dublê perfeito** — a linha de controle da bancada caiu de 1,0 para **0,9047619047619048** |
| **§8 migration** | **PASS** | `git diff 79c9e80..HEAD -- backend/supabase/migrations` → **vazio**. A coluna é a que já existia (`jsonb`, `is_nullable=NO`, default `'{}'::jsonb`, confirmado por SELECT em `information_schema`) |
| **§5 motor paralelo** | **PASS** | escritor único do estado: `nodes.py:2555` (1 ocorrência). Escritor único da ficha: `attendance_ficha.py:438/440`, alimentado só por `novidades_da_apolice:662`. `_gravar_apolice_do_caso`: 1 chamador. É a inspeção que a R3 (Google ADK) pediu |
| **§7.3 referência externa** | **PASS** | 5 URLs na §9 (guarda exige ≥ 3). R1 (LangGraph persistence) está modelado: o fato mora em campo tipado e a retomada vem do Supabase, não do `MemorySaver`. R2 (memory/trim) → G7 passa. R3 (ADK session state) → escritor único conferido acima; o prefixo `user:` foi de fato REJEITADO (`fundir` derruba a apólice no assunto novo: `attendance_ficha.py:392-399`, provado por `test_o_assunto_novo_NAO_herda_a_apolice_do_caso_anterior`). R4 (OWASP LLM02) → modelado no papel `attendance`, **furado no `core`** (B1). R5 (ENISA/LGPD) → HMAC com `company_id` no material, `sha256` nu de fato rejeitado; a chave vem do ambiente e **não** aparece em log, exceção ou retorno (`_segredo_do_hmac` devolve só presença/ausência) — mas ver pendência 3 |
| **testes alterados (regressão direta)** | **PASS — conserto de harness, não régua afrouxada** | `test_spec016_policy_intelligence` 94→**94** checks · `test_spec016_e2e_stub` 22→**22** · `test_infocap_policy_output_guard` 14→**14** · `test_spec016_1_answer_quality` 41→**43** (duas asserções NOVAS, uma delas linha de controle). O que mudou: a assinatura (`company_id`, `papel`) propagada aos chamadores, e o harness passando a carregar os módulos **REAIS** (`policy_context`, `policy_facts`, `policy_data_provider`) — ⛔ nenhum dublê de `policy_context`. No `answer_quality` os dicionários escritos à mão viraram saída do CONSTRUTOR real, e as afirmações do D6 continuam idênticas (`selected preservado`, `cliente novo NÃO herda`, `document == "99988877766"`). Em `test_spec116_conserto_unico` a verdade vencida (`== 3`) foi migrada, não apagada — ver pendência 7 |
| **efeito externo** | **PASS** | nenhum envio, chamado ou portal real: todas as bordas são dublês (`_Duble`, `_DubleDaConsulta`, `_SupabaseDeMentira`), e `test_o_policy_context_e_puro` proíbe por leitura do fonte `httpx`/`requests`/`aiohttp`/`supabase`/`async def` no módulo novo |
| **mutação (§5 ③)** | **PASS** | eu rodei 2 das mutações, não todas: (1) a porta volta a exigir identidade crua → **15 failed**; (2) o ramo do modelo volta a vencer → **4 failed**, incluindo os dois guardas nominais. Os guardas novos **conseguem** ficar vermelhos com o defeito histórico reintroduzido |

**Os 3 números do BLOCO 0 que eu reconferi por caminho independente:** B0.4 (`jsonb`,
`is_nullable=NO` — SELECT meu em `information_schema.columns`) ✅ · B0.5 escritor único
(grep meu, 1 ocorrência) ✅ · B0.5b (`selected_policy_ramo` = 0 em `backend/tests/*.py` no
commit base) ✅ **com ressalva** (75 ocorrências num JSON de RESULTADOS — pendência 6).

---

## MAIOR LACUNA — o que ninguém mediu

**Ninguém mediu se a apólice que o sistema impõe é a apólice do SERVIÇO que o segurado
pediu.** Toda a bateria nova pergunta *"o fato atravessou?"* — e ele atravessa, com elegância.
Nenhum teste pergunta *"o fato que atravessou é o CERTO para este pedido?"*. É literalmente a
segunda pergunta do CLAUDE.md §9.5, e é a que faltou: `atd-n2-auto-e-resi-eletricista` existe,
mas o caso que pega o defeito — **uma** apólice vigente, de ramo **diferente** do serviço — não
existe no corpus. Foi assim que B3 atravessou 40 testes verdes.

Em segundo lugar: **a bateria não rodou** (protocolo §5 ⑦), e o gate de entrega
(`test_o_protocolo_tem_policia`) está vermelho por isso.

---

## PRÓXIMA AÇÃO

1. **B2 primeiro** — é o que deixa o gate da bancada vermelho e mede os outros. Não forçar
   consulta quando o `policy_number` a mandar é o que o contexto já tem.
2. **B1** — projetar a lista branca na escrita durável + o teste de PII com `papel="core"`.
3. **B3** — o guarda de família no `insurer_dispatch` (o mesmo que o portal tem) e, com ele,
   um caso N2 de UMA apólice vigente de ramo diferente do serviço.
4. Pendências 1 e 2 (uma linha cada) no mesmo conserto; 3 a 8 para `PENDENCIAS.md`.
5. Reroda: `test_o_atendimento_guarda_a_apolice`,
   `test_a_apolice_do_caso_atravessa_o_atendimento`, `test_o_policy_context_e_puro`,
   `test_spec116_bancada_gates`, `test_spec016_*` — e a bateria, depois.

---

## CONFIANÇA · e o que ficou por medir

**Alta** nos três blockers: os três têm comando, saída colada e, no caso de B2, linha de
controle que isola o fator único. **Alta** em G1, G7, G8, G9, §5 e §8.

**O que eu NÃO medi:**
- o canário com duas corretoras reais (§8) — é do Founder, nenhum acesso meu o substitui;
- `next start` + rota real: esta SPEC não toca `app/`, `middleware.ts` nem
  `next.config.js`, então o §9.1 não se aplica;
- a bateria inteira (protocolo §5 ⑦ — é depois do conserto, e é do executor);
- as outras mutações dos guardas novos (o protocolo me proíbe de rodar todas);
- se `INSURER_DISPATCH_LIVE` está aberto hoje — B3 muda o destino do acionamento de todo
  jeito (dry-run inclusive), mas o tamanho do estrago depende disso;
- G4 em 6+ turnos ponta a ponta por caminho independente do deles: o caso N2 que faria isso
  está vermelho por B2.

---

## NOTA · **70 / 100**

Critério em uma linha: **desenho, autoridade única e guardas com mutação provada valem 90;
três defeitos que mudam bytes — CPF em coluna durável, consulta duplicada ao sistema da
corretora e acionamento na seguradora errada — tiram 20, e nenhum deles é de arquitetura:
são três guardas que faltaram nos três lugares onde o diff já sabia colocá-los.**
