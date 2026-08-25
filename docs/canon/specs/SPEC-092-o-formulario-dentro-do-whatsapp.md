# SPEC-092 · O FORMULÁRIO DENTRO DO WHATSAPP

> **Quatro seguradoras pararam de perguntar por texto e passaram a abrir um
> aplicativo dentro da conversa. Quando isso acontece, o corredor para.**
>
> 📊 **460 apólices de auto — 26,9% da carteira** estão nessas quatro.
>
> v1 · 25/08/2026 · escrita sob o `PROTOCOLO-AUTOBROKERS-AAA.md` **v9**
> Branch: `feat/spec092-o-formulario-dentro-do-whatsapp`

---

## 0. AS DUAS CONTAS — `PROTOCOLO-AUTOBROKERS-AAA.md` §3

| | ALC | REV | FREQ | **RISCO** | **SUP** | piso? |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| a SPEC inteira, como lote | 3 | 3 | 2 | **8** | **3** | sim (§3.2: envia mensagem) |

**ALCANCE 3** — o segurado fica sem chamado aberto. **REVERSIBILIDADE 3** — sai do
prédio: a mensagem vai para a seguradora. **FREQUÊNCIA 2** — 📊 30–60 formulários
por semana no acervo, contínuo. **SUPERFÍCIE 3** — território que ninguém mapeou:
📊 o convite do formulário **nunca foi capturado**, e a prova de que responder
funciona vive em **três exemplares decodificados**.

> 🔴 **Time do lote: equipe completa + red team + juiz final fresco.**
> A §5 traz o time de **cada unidade**, por extenso.

### 0.1 As referências, por dimensão (§7 do protocolo)

| dimensão | referência inspecionável | 🧑 |
|---|---|:---:|
| **o envio** | 📊 `docs/canon/O-FORMULARIO-NATIVO-RESOLVIDO.md` — a prova de 03/08, com linha de controle. **É a única coisa deste assunto que está provada.** | proposta |
| **o método** | `whatsapp_integrations.py:356-368` — a lista `tentativas`, que É a linha de controle **codificada e viva** | proposta |
| **o formato da resposta** | 🔴 o `flow_reply` de **HDI, 18/07/2026, `source=live`** — o único com o payload decodificado inteiro | proposta |
| **o exemplar mais recente** | 🔴 **Yelum, 19/08/2026 16:02, `source=live`, AutoFleet** — um dos 3 com campos decodificados | proposta |
| **prova sem risco** | `POST /api/whatsapp-integrations/prova-de-formulario` — do nosso número para o nosso número | proposta |

---

## 1. O RESULTADO

```
Quando a seguradora abrir o aplicativo dentro da conversa,
o corredor RECONHECE, PREENCHE e RESPONDE — e o chamado continua.

E quando ele não conseguir, ele SABE que não conseguiu,
e o segurado ouve a verdade.
```

⛔ **O que NÃO é o resultado:** que o robô responda todo formulário de toda
seguradora. 📊 Porto e Azul **não têm schema recuperável** (§2.5) — para elas o
resultado é **capturar**, não responder.

---

## 2. O QUE ESTÁ QUEBRADO — medido

### 2.1 🔴 O achado que reordena a SPEC: **o acervo está partido em duas tabelas**

```sql
attendance_transcripts   155.512 linhas   2024-09 → 25/08/2026   flow_reply: ❌ ZERO
observed_events           28.151 linhas   2025-07 → 24/08/2026   flow_reply: ✅ 62

cruzando por message_id:  1 mensagem em comum entre 28.151
```

> 🔴 **São dois pipelines de captura distintos, não cópia nem subconjunto.**
> **Quem investigar o formulário olhando a tabela grande — a óbvia, a de 155 mil —
> conclui que ele não existe. A prova toda mora na tabela pequena.**

⚠️ **Esta é a primeira coisa que o executor precisa saber**, e é a que mais
facilmente o faria concluir o oposto do verdadeiro.

### 2.2 📊 O formulário JÁ FOI RESPONDIDO. 62 vezes. Por gente.

```sql
SELECT insurer_key, count(*), max(wa_timestamp)
  FROM observed_events WHERE interactive->>'kind' = 'flow_reply' GROUP BY 1;

  porto  27  (9 sessões)   até 28/05/2026
  yelum  14  (8 sessões)   até 🔴 19/08/2026  `source=live`
  hdi    11  (6 sessões)   até 18/07/2026     `source=live`
  azul   10  (4 sessões)   até 29/05/2026
```

🔴 **São exatamente as quatro seguradoras desta SPEC. Nenhuma a mais.** E 📊 **zero
AMANDUS** — a corretora fictícia não tem um único `flow_reply`. Empresas reais:
**AutoFleet 57, Resulta 5.**

📊 **E todas as 62 são `direction='out'`: a PESSOA da corretora respondendo.**
Os dois valores de `source` (`history_sync`, `live`) são espelho do aparelho
humano. **Zero automação hoje.**

### 2.3 📊 A estrutura que deu certo — o exemplar de ouro

**HDI, 18/07/2026, `source=live`** — o único com o payload decodificado inteiro:

```
extra.name       = "galaxy_message"          🔴 ← o rótulo que a LEITURA não conhece
extra.type       = "native_flow_response"
extra.buttonId   = ""      (vazio)
extra.buttonText = ""      (vazio)
extra.paramsJSON = "{ \"rb_EmGaragemOuEstacionamento\": \"1\",
                      \"rb_NivelDaRua\": \"4\",
                      \"ckb_SituacoesVeiculo\": [\"nenhuma_opcoes\"],
                      \"rb_InformacoesLocal\": \"6\",
                      \"rb_Ocupantes\": \"1\",
                      \"flow_token\": \"<uuid>:<n>:<n>\",
                      \"wa_flow_response_params\": {...} }"
```

🔴 **Quatro coisas que o executor tem de respeitar, e cada uma quebra sozinha:**

```
1. `paramsJSON` é STRING JSON, não objeto
2. as respostas são ÍNDICES ("1", "4", "6"), nunca o texto da opção
3. checkbox vira ARRAY
4. o `flow_token` NÃO É DERIVÁVEL — tem de vir do convite
```

📊 **E uma inferência de alta confiança que economiza metade do trabalho:**
os nomes de campo da HDI (`rb_EmGaragemOuEstacionamento`, `rb_NivelDaRua`,
`ckb_SituacoesVeiculo`, `rb_InformacoesLocal`, `rb_Ocupantes`) são **idênticos**
aos decodificados da Yelum. O título Yelum é *"[APP NATIVO] Automóvel — Detalhes
do atendimento (veículo, local e ocupantes) V2"*.
🔴 **Uma plataforma só atrás de duas marcas: é provável que UM mapeamento sirva às
duas.** ⚠️ **Provável, não provado — o BLOCO C mede.**

### 2.4 ⛔ O BLOQUEADOR: **o convite nunca foi capturado**

📊 Sobre **16.268** mensagens `direction='in'` de `observed_events`:

```
nativeFlowMessage      in: 0    out: 4
interactiveMessage     in: 0    out: 4
flow_token             in: 0    out: 5
flow_action_payload    in: 0    out: 4
```

> 🔴 **O convite não existe como linha no acervo.** Ele sobrevive apenas como
> fragmento **citado** (`quotedMessage`) dentro de quatro respostas.

**E a causa está na fonte:** `evolution_inbound.py:268` reconhece
`("flow", "mpm", "wa_payment_details", "review_and_pay")` — e o bot de HDI e
Yelum usa o rótulo legado **`galaxy_message`**.

⚠️ 🔴 **O lado do ENVIO documenta esse fato há semanas** (`evolution_go.py:197-199`).
**Ninguém cruzou com o lado da LEITURA.**

📊 **A consequência, medida:** varredura de 23/08 sobre **28.096 eventos** — o
marcador `[FORMULARIO NATIVO]` aparece **ZERO vezes** (P-084-67). As telas de
abertura chegam como `{"kind":"buttons","options":[]}`.

> ## 🔴 O transporte provado em 03/08 está ligado e NUNCA é exercitado. Uma SPEC que testasse só o envio mediria um cano que não recebe água.

### 2.5 📊 O acervo utilizável é MENOR que 62 — e a §9.2 do `CLAUDE.md` se aplica

```
62  flow_reply no total
 5  com `flow_token`
 4  com o payload de fio completo
 3  com campos decodificados      ← 🔴 é isto que existe
57  guardam só `title: "Enviada"` — o recibo, não o conteúdo
```

⚠️ **`CLAUDE.md` §9.2, literal:** *"um acervo de um permite comparar; não permite
conferir hipótese."* **Esta SPEC está sendo desenhada sobre três exemplares.**
🔴 **Por isso o BLOCO A vem primeiro: ele multiplica o acervo antes de o resto
depender dele.**

📊 **E Porto e Azul são piores:** 37 eventos delas foram gravados pelo caminho
`history_sync`, que guardou só `sorted(m.keys())` (P-084-38). **Não são
recuperáveis** — `observed_events` não tem coluna de raw. **Porto e Azul não têm
schema de formulário nenhum, e não vão ter sem um acionamento ao vivo.**

### 2.6 📊 O outro formulário — botão e lista — tem a MESMA doença

```
em attendance_transcripts:  buttons 950 · list 544 · button_reply 611 · list_reply 436
📊 4.715 opções registradas nos convites;  `id` preenchido em ZERO delas
```

Só o `title` sobrevive. Mas as respostas mostram **id opaco de servidor**
(`pd-dc-<ts>-<hash>-0`) — **não reconstruível a partir do título.**

🔴 **É a mesma perda de ingestão da §2.4, noutra forma.** O BLOCO A conserta as duas.

### 2.6.1 📊 AS CINCO ROTAS, nomeadas — medidas contra o corpus

```
hdi   × auto × guincho            âncora "V2 condições"        3 telas / 3 sessões
hdi   × auto × chaveiro           "local e ocupantes"          1 / 1
yelum × auto × guincho            "V2 condições"               2 / 2
yelum × auto × pneu               "local e ocupantes"          1 / 1
yelum × auto × socorro_mecanico   "local e ocupantes"          3 / 3
```

⚠️ **Nenhuma outra seguradora casa âncora**, e 🔴 **Porto e Azul usam formulário
e não têm schema nenhum**: `native_flows` só existe em `HDI_AUTO_WHATSAPP_V1`
(`corridor_playbooks.py:2982`) e `YELUM_AUTO_WHATSAPP_V1` (`:3010`). Residencial
declara que não tem (`:3966`).

⚠️ E os documentos divergiam: o relatório da 084.2 §3.1 dizia *"quatro rotas"*, a
declaração final *"5 sessões"*, a SPEC-085 *"5 rotas"*. **A medição dá CINCO.**

### 2.7 📊 Onde dói mais — a taxa de resposta em 60 min

```
youse 226 · mapfre 455 · autoglass 199 · localiza 22 ....  90–92%   funciona
yelum 60 ...............................................  82%
bradesco 49 · sem chave 410 ............................  41–45%
🔴 vix 18 ..............................................  22%
🔴 hdi 12 ..............................................   8%
🔴 tokio 12 ............................................   0%      trava total
```

⚠️ **E `vix` e `tokio` não estão nas quatro da SPEC.** 💭 Podem ser 6 seguradoras,
não 4 — e `zurich` e `mapfre` têm marcas de `native_form` em `list_reply`.
**O BLOCO A mede; a SPEC não amplia o escopo por palpite.**

### 2.8 O que acontece quando o envio falha, hoje

`insurer_dispatch_service.py:1596-1599` → `needs_human` com `formulario_envio_falhou`,
e o motivo nasce num `except Exception` — ⚠️ **timeout entra aí, e timeout não
prova que o formulário não chegou.**

🔴 **E ele NÃO retoma, de propósito:** está em `DIRETO_AO_HUMANO` (`:2980`).
📊 Foi derrubado da lista de retomáveis por red team — o formulário nativo **é** o
passo de confirmação, logo `captured["protocol"]` está vazio **por construção**, e
o único freio antiduplicação é estruturalmente cego aqui. **Retomar manda um
segundo prestador à casa de alguém.** ⛔ **Não mexa nisso.**

---

## 3. O QUE JÁ ESTÁ PRONTO — ⛔ e esta SPEC NÃO REFAZ

### 3.1 📊 O ENVIO está provado, com linha de controle, desde 03/08/2026

`docs/canon/O-FORMULARIO-NATIVO-RESOLVIDO.md` — **leitura obrigatória.**

```
📊 rodada 1: cinco formas, cinco vezes 479 (variando version, nós <biz>, body)
   → "fator que não muda o resultado não é a causa" → o payload inteiro caiu
📊 rodada 2: controle → 479 · embrulho DocumentWithCaption → 200
   servidor devolveu Type: "InteractiveResponseMessage"
```

📊 **479 = "Invalid stanza sent (smax-invalid)"**, lido no comentário do próprio
`whatsmeow` — **não pesquisado.** Significa recusa do **envelope**, não do conteúdo.

**O que existe e funciona:**
- `send_native_flow_response` (`evolution_go.py:464`) — a rota provada
- `montar_nfm_reply` (`:169`) — **função pura**, testável sem rede
- 🔴 `paramsJSON` viaja **byte a byte, nunca re-serializado** — re-serializar
  reordena chaves e reescreve acentos
- `POST /api/whatsapp-integrations/prova-de-formulario` — do nosso número para o
  nosso número. **Foi assim que a prova foi feita.**

⛔ **Não reescreva nada disso.** Quem tocar `send_native_flow_response` ou
`montar_nfm_reply` sem uma linha do relatório justificando **reprova no gate.**

### ⛔ 3.1.1 · MAS DUAS COISAS DO ENVIO ESTÃO MEDIDAS COMO ERRADAS

🔴 **A prova de 03/08 mediu que o WhatsApp ACEITA. Não mediu que os campos
estão certos.** Duas estão falsificadas contra as capturas reais:

```
📊 `montar_nfm_reply` manda   version = 1        (evolution_go.py:176, :240, :473)
   as 4 capturas reais yelum   version = "3"      (03, 07, 17 e 19/08)
   ⚠️ e o comentário dizia que o GO DESCARTA o campo — ele não descarta

📊 o código escreve         "format": "EXTENSIONS"   (evolution_go.py:231)
   as capturas reais trazem  "format": "1"
```

⚠️ **O `version = 1` estava escrito com 💭 explícito de que era hipótese** — e
a hipótese durou porque a bateria **parou na primeira forma que passou** (§3.2).
🔴 **Isto é conserto do BLOCO D, e sai com a captura ao lado.**

### ⛔ 3.1.2 · E dois guardas que NÃO TÊM COMO FALHAR

```
📊 `flow_reply_supported()` (evolution_go.py:455) e `formulario_pronto_sem_transporte`
   estão OBSOLETOS: a rota nunca é vazia por padrão, e `webhook.py:499` SEMPRE
   injeta o `flow_sender`. É o CLAUDE.md §9.3 — guarda que não pode falhar.

🔴 `formulario_nativo_desconhecido` (:1538) é INALCANÇÁVEL hoje: as duas
   condições dependem do parser que nunca emite `flow`.
   **O desconhecido escorrega MUDO para a fase humana** — exatamente o que o
   guarda existe para impedir.
```

⚠️ **E dois comentários vencidos em arquivo que decide envio** (`evolution_inbound.py:520-524`
e `dispatch_router.py:1697-1699`): afirmam que *"o `webhook.py` ainda não passa o
`interactive`"*. **Passa desde `webhook.py:507` e `:1440`.**

### 3.2 O que ficou por provar, e está escrito

📊 `O-FORMULARIO-NATIVO-RESOLVIDO.md:167-175`: `version` · `response_message`
(~6 KB — exigido ou decoração?) · `MessageSecret` (nunca testado: a bateria parou
na primeira que passou) · 🔴 **e o desfecho — provamos que o WhatsApp aceita;
NÃO que a seguradora aceita.**

---

## 4. A ORDEM, E POR QUE ELA É ESSA

```
BLOCO A   CAPTURAR O CONVITE          ← 🔴 ANTES DE TUDO
BLOCO B   RECONHECER `galaxy_message`
BLOCO C   O `flow_id` É POR SEGURADORA
BLOCO D   RESPONDER, ligando o cano provado ao corredor
BLOCO E   A 4ª TELA DA YELUM
BLOCO F   A PROVA
```

🔴 **O BLOCO A vem primeiro por dois motivos, e os dois são medidos:**

1. **Sem o convite não há `flow_token`, e sem `flow_token` não há resposta.**
   O token **não é derivável** (§2.3).
2. 🔴 **A Regina, da AutoFleet, faz acionamentos reais TODOS OS DIAS.** 📊 30–60
   formulários por semana atravessam o acervo. **Se a captura for consertada
   hoje, em uma semana existe corpus. Se não for, continuam três exemplares.**

> **O BLOCO A é o único que fica mais barato quanto antes for feito.**

---

## 5. AS UNIDADES DE TRABALHO — cada uma pontuada (§3 do protocolo)

| # | unidade | ALC/REV/FREQ | **RISCO** | **SUP** | time, por extenso |
|---|---|:---:|:---:|:---:|---|
| **A** | capturar o convite: `nativeFlowMessage`, `flow_token`, `options[].id` | 2/2/2 | **6** | 2 | builder · juiz da superfície · verificador · desenhista da prova |
| **B** | `galaxy_message` reconhecido na leitura | 3/2/2 | **7** | 1 | builder · juiz da superfície · verificador |
| **C** | o `flow_id` por seguradora | 3/3/2 | **8**·piso | 1 | builder · juiz da superfície · verificador · desenhista da prova |
| **D** | responder: ligar o cano provado ao corredor | 3/3/2 | **8**·piso | 2 | builder · juiz da superfície · verificador · desenhista · **RED TEAM** |
| **E** | a 4ª tela da Yelum | 3/3/1 | **7**·piso | 0 | builder · JUIZ DA SUPERFÍCIE |
| **F** | a prova ponta a ponta | 3/0/2 | **5** | 3 | builder · investigador · desenhista · verificador |

🔴 **INTEGRADOR entra** — 3+ unidades no mesmo lote (§4).
🔴 **A ESCRITA É DE UM SÓ** (§8 EXECUÇÃO): 📊 os blocos B, C e D tocam
`evolution_inbound.py` e `insurer_dispatch_service.py`. **Integração serial.**

---

## BLOCO A · CAPTURAR O CONVITE — 🔴 antes de tudo

```
A.1  `evolution_inbound.py` passa a GRAVAR, quando a mensagem for interativa:
       · o `nativeFlowMessage` / `interactiveMessage` cru
       · o `flow_token` e o `flow_id`
       · 🔴 `options[].id`, que hoje é gravado VAZIO em 4.715 convites
     ⚠️ Guardar o CRU é o ponto: 📊 o caminho `history_sync` guardou só
        `sorted(m.keys())` e perdeu 37 eventos de Porto e Azul PARA SEMPRE.

A.2  🔴 E GRAVA MESMO O QUE NÃO RECONHECE.
     📊 `observed_events` tem 204 linhas com `interactive` não-nulo e `kind` NULO
     — forma não classificada, já hoje. Uma forma nova de seguradora não pode
     virar perda de dado. **Desconhecido guarda o cru e marca `kind='desconhecido'`.**

A.3  🔴 A DECISÃO QUE O INVESTIGADOR TOMA, com o motivo escrito:
     `observed_events` e `attendance_transcripts` são DOIS pipelines com 1 linha
     em comum (§2.1). A captura entra em qual? Nos dois? 
     ⛔ CLAUDE.md §5: consolidar antes de duplicar. Um terceiro caminho reprova.
```

⚠️ **PII:** o convite carrega dado do segurado. 🔴 **O mascarador da SPEC-085
(`pii_da_sessao.py`) já existe — REUSE.** Um quinto mascarador reprova (§10).

**Gate A:** um formulário que chega hoje passa a ter linha com `flow_token` e
`options[].id` preenchidos.
⚠️ **CONTROLE 1:** uma mensagem de texto comum **não** gera linha de convite.
⛔ **CONTROLE 2:** uma forma **desconhecida** gera linha com o cru e
`kind='desconhecido'` — **não** é descartada.

---

## BLOCO B · RECONHECER `galaxy_message`

> ⛔ 🔴 **ESTE BLOCO É UMA APOSTA ATÉ O BLOCO A PRODUZIR UMA CAPTURA DE ENTRADA.**
> 📊 `_raw_capped` só roda `if from_me` (`observer_intake.py:981-985`): **não existe
> UMA captura crua do `nativeFlowMessage` de ENTRADA.** `direction='in'` com
> `galaxy` = **0 de 28.151**. Os 5 `galaxy_message` medidos são todos da
> **RESPOSTA** do humano.
>
> **Ligar `galaxy_message` na allowlist de leitura é apostar que o botão de
> ENTRADA usa o mesmo rótulo da RESPOSTA.** ⚠️ Plausível, e não medido.
> 🔴 **O BLOCO A vem primeiro exatamente por isso. Se a captura mostrar outro
> rótulo, este bloco muda — e o relatório diz qual era.**

```
B.1  `evolution_inbound.py:268` passa a reconhecer o rótulo QUE A CAPTURA MOSTROU
     — 💭 provavelmente `galaxy_message` — ao lado de `flow`, `mpm`,
     `wa_payment_details`, `review_and_pay`.

B.2  🔴 E O CONTROLE QUE PROVA QUE NADA MAIS MUDOU:
     reprocessar os 28.096 eventos e mostrar que NENHUMA outra mensagem mudou
     de classificação. 📊 O marcador `[FORMULARIO NATIVO]` sai de ZERO para N,
     e o relatório traz o N — e as classificações antigas, intactas.
```

⚠️ **Sem o B.2 este bloco é um `if` a mais num parser que decide o que 28 mil
eventos são.** É o tipo de mudança que parece trivial e reclassifica o acervo.

**Gate B:** o `[FORMULARIO NATIVO]` deixa de ser zero.
⛔ **CONTROLE:** as outras classificações do reprocessamento são **idênticas**.

---

## BLOCO C · O `flow_id` É POR SEGURADORA — 🔴 e errar isso é silencioso

📊 **P-084-69:** o **mesmo** formulário V2 tem id `857030507196739` na HDI e
`3206000179602236` na Yelum. `montar_resposta_de_flow` devolve
`flow_schema["flow_id"]` — 🔴 **responder à Yelum ecoaria o id da HDI.**

> **Se a Yelum validar, a resposta é descartada EM SILÊNCIO, e a janela de
> 12 minutos queima.** Nenhum erro, nenhum log, e o segurado espera.

```
C.1  o `flow_id` passa a sair da SEGURADORA da sessão, nunca do schema herdado
C.2  📊 e a hipótese que economiza metade do trabalho é MEDIDA, não assumida:
     os nomes de campo de HDI e Yelum parecem IDÊNTICOS (§2.3).
     🔴 Se forem, UM mapeamento serve às duas — e o relatório mostra a
     comparação campo a campo. Se não forem, são dois mapeamentos.
     ⛔ Não assuma. Meça.
```

**Gate C:** uma resposta montada para a Yelum carrega o id da Yelum.
⛔ **CONTROLE:** montar para HDI e Yelum e **provar que os ids diferem** — se
saírem iguais, o bug está vivo e o teste não o vê.

---

## BLOCO D · RESPONDER — ligar o cano provado ao corredor

```
D.1  com o convite capturado (A) e reconhecido (B), o corredor monta a resposta
     por `montar_nfm_reply` e envia por `send_native_flow_response`.
     ⛔ NÃO reescrever nenhuma das duas (§3.1).

D.2  🔴 `match_ura_step` roda ANTES de `_responder_formulario_nativo`.
     📊 P-084-68: por isso o corredor envia "Digitar endereço" como TEXTO para
     uma tela que só aceita clique. **A ordem precisa inverter quando a tela
     for formulário** — e o relatório diz o que mais essa inversão afeta.

D.3  🔴 CONSERTAR `version` E `format`, com a captura ao lado (§3.1.1):
       version = 1            →  o que a captura mostrar  (📊 as 4 reais: "3")
       format  = "EXTENSIONS" →  o que a captura mostrar  (📊 as reais: "1")
     ⚠️ E o comentário que dizia que o GO descarta o `version` sai junto:
        📊 ele não descarta.

D.4  ⛔ `formulario_envio_falhou` CONTINUA em `DIRETO_AO_HUMANO`.
     📊 Foi derrubado dos retomáveis por red team, e o motivo é estrutural
     (§2.8). **Retomar manda um segundo prestador à casa de alguém.**
```

⚠️ 🔴 **E a trava que o BLOCO D tem de respeitar:** `INSURER_DISPATCH_LIVE`
fechado faz `flow_sender` **nunca ser chamado** — o transcript grava
`dry_run: True` e a sessão vai para `state="ura"` **como se tivesse respondido**.
**O ensaio precisa distinguir "não enviei porque o freio está fechado" de
"enviei e falhou".**

**Gate D:** o corredor responde um formulário do corpus, ponta a ponta, em
dry-run, e o `paramsJSON` montado é **byte a byte igual** ao exemplar de ouro.
⛔ **CONTROLE:** com o freio fechado, o estado **não** vai para `ura` sem que o
transcript diga que foi dry-run.

---

## BLOCO E · A 4ª TELA DA YELUM

📊 **P-084-68:** o formulário `1579547063352571` (*"Informar endereço V2"*) não
foi transcrito. **Uma tela sem transcrição é uma tela que o corredor responde
por texto.**

**Gate E:** a tela existe no schema, e o corredor a responde por clique.
⛔ **CONTROLE:** uma tela **sem** schema continua indo para `needs_human` com
`formulario_nativo_desconhecido` — **e não é chutada.**

---

## BLOCO F · A PROVA

```
F.1  🔴 O ENSAIO SEM RISCO, e ele já existe:
     `POST /api/whatsapp-integrations/prova-de-formulario` manda DO NOSSO NÚMERO
     PARA O NOSSO NÚMERO a mensagem exata que um telefone humano produz.
     Foi assim que a prova de 03/08 foi feita.

F.2  ⛔ E O GUARDA QUE FALTA NESSA ROTA:
     📊 ela NÃO passa por freio nenhum — só por `_require_internal_key`.
     Não consulta `dispatch_live_enabled()` nem `freio_de_emergencia_armado()`.
     🔴 É segura porque o destino é nosso, e INSEGURA se alguém passar o número
     de uma seguradora. **Este bloco põe a recusa: destino que não é nosso, 400.**

F.3  o `ura_simulator.py` passa a exercitar o caminho do formulário.
     📊 Hoje ele chama `handle_insurer_message(session, screen)` com TEXTO SÓ —
     sem o parâmetro `interactive` — então `flow_sender` é `None` e todo
     formulário vira `formulario_pronto_sem_transporte`.
     🔴 **O simulador não exercita o caminho de envio. É a lacuna nº 1.**

F.4  🔴 A LINHA DE CONTROLE do ensaio: o mesmo roteiro com uma tela de TEXTO.
     Nenhum formulário montado, nenhum envio, o corredor responde por texto
     como sempre fez.
```

### 🔴 As travas do ensaio, e nenhuma é negociável

```
⛔ NENHUMA mensagem para seguradora. O ensaio é do nosso número para o nosso.
⛔ `INSURER_DISPATCH_LIVE` fica FECHADO.
⛔ `CARTOGRAPHER_MODE` fica em 0 — 📊 =1 manda WhatsApp REAL a seguradoras.
⛔ Agentes `attendance` DESLIGADOS.
⛔ Só AMANDUS nas simulações. A AUTOFLEET é a única pareada de verdade.
⛔ Somente SELECT no banco, fora das migrations desta SPEC.
⛔ Nunca CPF, telefone, apólice, placa ou nome em resposta nenhuma.
```

---

## 6. 🔴 O QUE ESTA SPEC NÃO RESOLVE, e vai para a CAIXA DO FOUNDER

| | o que é | por quê |
|---|---|---|
| **Porto e Azul** | 📊 não têm schema recuperável (P-084-38) | só um acionamento **ao vivo** produz um. 🧑 **Decisão do Founder** |
| **o desfecho** | provamos que o WhatsApp aceita; **não** que a seguradora aceita | só um acionamento real fecha isso |
| **vix, tokio, zurich, mapfre** | 💭 podem ter formulário também (§2.7) | o BLOCO A mede; ampliar por palpite reprova |

---

## 7. AS LENTES — quatro, EM PARALELO, cegas entre si (§5 do protocolo)

⛔ **Não rode um juiz genérico três vezes.** ⛔ **Não monte painel sobre esta SPEC** —
quem a julga é o **aquecimento do executor** (§5.2 do protocolo).

```
⚖️ O CÉTICO DA MEDIDA      "este número mede o que a frase diz?"
                           🔴 e a pergunta dele aqui: 3 exemplares bastam?
⚖️ O CÉTICO DO SEGURADO    "o que chega a ele quando o formulário falha?"
⚖️ O CÉTICO DO ACERVO      "o reprocessamento mudou classificação de outra coisa?"
⚖️ O CÉTICO DO ISOLAMENTO  "algo novo atravessa corretora? o PII do convite
                            está mascarado?"
🗡️ RED TEAM no BLOCO D     formulário malformado · flow_token vencido · a
                            seguradora respondendo outra coisa · timeout que
                            não prova nada
```

**O laço:** ① builder ② verificador mecânico ③ **as quatro lentes de uma vez**
④ funde e aplica o teste do produto ⑤ conserta tudo junto ⑥ **um juiz novo
confirma**. 🔴 **Teto: 3 rodadas de painel.**

---

## 8. O GATE DA SPEC

```
✅  BLOCO A com os DOIS controles (texto não gera linha; desconhecido guarda o cru)
✅  BLOCO B com o reprocessamento provando que nada mais mudou de classificação
✅  BLOCO C com os ids DIFERENTES entre HDI e Yelum, provado
✅  BLOCO D com o `paramsJSON` byte a byte igual ao exemplar de ouro
✅  BLOCO E · BLOCO F com a linha de controle de texto
✅  🔴 a rota de prova recusa destino que não é nosso
✅  🔴 dois tenants: teste automático que FICA VERMELHO quando o filtro sai
✅  🔴 `pytest tests/` verde · e se tocou `app/`: `test:rotas-montam` + `next start` + /api/
✅  nenhum motor paralelo: nem quinto mascarador, nem terceiro pipeline de captura,
    nem reescrita de `montar_nfm_reply`
✅  relatório completo, com a §0.1 preenchida ANTES de montar time
✅  🔴 A TELEMETRIA do §11 do protocolo — inclusive o tempo até a primeira
    linha de código
```

---

## 9. PREFLIGHT

```bash
git rev-list --count HEAD..origin/main    # 🔴 TEM DE SER 0
git checkout -b feat/spec092-o-formulario-dentro-do-whatsapp
git rev-parse HEAD                        # registre no relatório
git status --short                        # limpo
export PYTHONIOENCODING=utf-8
```

**Leitura — o NÚCLEO do `CLAUDE.md` §2, e mais dois:**

```
CLAUDE.md · PROTOCOLO-AUTOBROKERS-AAA.md · GLOSSARIO.md · esta SPEC
🔴 + docs/canon/O-FORMULARIO-NATIVO-RESOLVIDO.md   (243 linhas — a prova do envio)
🔴 + as pendências POR NÚMERO: P-084-38 · P-084-67 · P-084-68 · P-084-69
```

⛔ **Não leia o `PENDENCIAS.md` inteiro.** São 421 KB, e a §1 do protocolo proíbe.
