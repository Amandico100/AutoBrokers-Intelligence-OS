---
> **Status:** canônico — plano de execução aprovado para a demonstração
> **Criado em:** 14/08/2026 · **Branch:** `fix/p0-espelho-egress` → `main`
> **Objetivo:** o atendimento funcionar de ponta a ponta, monitorado, na semana de 18/08
> **Regra desta SPEC:** nada é executado sem o bloco anterior estar verde.
---

# SPEC-071 — Atendimento ponta a ponta, monitorado, e o go-live

## 0. O que esta SPEC resolve

O Founder vai apresentar o sistema funcionando na semana de **18/08/2026**, com
**Regina (AutoFleet)** e **Saionara (Resulta)** monitorando um agente de IA que
atende clientes reais. Elas olham, anotam os erros e intervêm quando ele erra.

Esta SPEC é a lista fechada do que precisa estar pronto para esse dia — e a
ordem em que precisa ser feito.

---

## 1. REGRAS INVIOLÁVEIS DESTA EXECUÇÃO

Decisões do Founder, 14/08/2026. Valem para todos os blocos.

| # | Regra |
|---|---|
| R1 | **Nada é enviado a seguradora nenhuma sem autorização explícita, por escrito, no chat.** `INSURER_DISPATCH_LIVE` fica DESLIGADO. |
| R2 | **Nenhum teste escreve no WhatsApp da AutoFleet ou da Resulta.** Só código, ou a AMANDUS. |
| R3 | **Dados de cliente real só com autorização prévia, caso a caso.** 📊 Dado fictício não serve — nem a InfoCap acha a apólice, nem a seguradora inicia o atendimento. O Founder busca uma apólice real quando chegarmos lá. |
| R4 | **Não desparear nem reconfigurar canal de WhatsApp.** Diagnóstico é leitura. |
| R5 | **Nenhum job periódico gasta API sozinho** enquanto o trabalho cognitivo é feito pelo Claude Code no plano Max. |
| R6 | **Todo material destilado passa por juiz crítico** antes de entrar em qualquer lugar. O juiz roda no plano Max, não na API. |
| R7 | **Qualidade sobre volume.** Carta que repete o que já existe não entra. |

---

## 2. O ESTADO MEDIDO — 14/08/2026

### 🟢 Funciona e está provado
| | |
|---|---|
| Captura → Espelho → Chat | AutoFleet 3.887/7d · Resulta 44.706 em 12h · **0 vazias, 0 duplicatas** |
| Conserto de Egress | sob o despejo da Resulta: **5.075 leituras → 824 mensagens (6:1)**, contra 136:1 do desenho antigo |
| Motor de Work Runs | 1.702 runs, 1 falha |
| RAG | 18.400 cartas, escrevendo hoje |
| Mapas | **1 mapa `active` por seguradora**, 10 seguradoras. Allianz e Tokio atualizadas hoje |
| Playbooks | **12 `active`, 6 `draft`** — todos escritos em Opus 5 |
| Gate de playbook | 3 portões (determinístico + juiz + conselho), rollback de 1 clique. **Regredir é estruturalmente impossível** |
| Corredores | **14** (10 auto + 4 residencial), 61 pares seguradora × ramo × serviço |
| Buffer de rajada | espera 8s de silêncio, teto 25s, junta tudo numa mensagem |
| Observador | **captura as conversas com seguradora, com menus e botões** — 2.453 mensagens interativas |

### 🔴 Quebrado — e cada um tem bloco nesta SPEC
| # | O quê | Bloco |
|---|---|---|
| D1 | O agente **se cala sozinho** depois da primeira resposta | 2 |
| D2 | Atendente respondendo por **áudio/foto não pausa** a IA | 2 |
| D3 | Portão de silêncio é **fail-open** — falha de leitura e a IA fala por cima | 2 |
| D4 | **Seguradora não é reconhecida** — `insurer_key = 0`, o Atlas não recebe nada | 4 |
| D5 | **Portal de vidros** não conhece as telas finais | 5 |
| D6 | **Lapidador escapa da trava** de gasto | 3 |
| D7 | **Dossiê insuficiente** para a atendente agir sem reler tudo | 3 |
| D8 | 2.603 mensagens da Resulta presas numa fila de 14h | 1 |

---

## 3. BLOCO 1 — A mesa da Saionara *(10 min · sem risco)*

**Problema.** 📊 3.436 mensagens elegíveis da Resulta; 1.599 no chat. As outras
estão atrás de 41.270 linhas de histórico antigo que o cursor precisa atravessar
a 500 por ciclo — ~14 horas.

**Ação.** Chamar o endpoint one-shot, que lê por `wa_timestamp` e ignora o
histórico:
```
POST /api/whatsapp-channel/espelho/trazer-conversas
     ?company_id=<resulta>&dias=30&limite=6000
```

**VERIFY.** `conversas vazias = 0` · `duplicatas = 0` · elegíveis ≈ espelhadas.
**ROLLBACK.** Não aplicável — é idempotente por `wa_message_id`.

---

## 4. BLOCO 2 — Os três P0 do atendimento
> **Sem este bloco verde, nenhum agente é ligado. Em lugar nenhum.**

### 2.1 · D1 — a IA reconhecer a própria voz
📊 `webhook.py:1180` trata todo `fromMe` com texto como "a atendente respondeu".
A resposta da própria IA volta pelo WhatsApp como `fromMe` e a pausa dispara.
📊 `webhook.py:777` grava a resposta da IA **sem `payload`** — não há marca.

**Desenho.** Antes de enviar, registrar em Redis a impressão digital da
mensagem (`company_id` + telefone + hash do texto), TTL curto. O ramo `fromMe`
consulta: se bater, é eco próprio — espelha e **não pausa**.

Redis e não banco: é transitório por natureza, e uma perda de Redis degrada
para "pausou sem precisar" (chato, reversível por botão), nunca para "não pausou
quando precisava".

### 2.2 · D2 — áudio e foto também pausam
📊 A condição exige `and normalized.get("text")`. Áudio é o formato mais comum.
**Ação.** Pausar por **qualquer** `fromMe` humano, com ou sem texto.

### 2.3 · D3 — o portão vira fail-closed
📊 `webhook.py:506` — no `except`, `is_human_mode` fica `False` e a IA fala.
O portão irmão (`_em_silencio`) é fail-closed. **Ação:** igualar. Não conseguir
confirmar que a conversa está livre **nunca** vira permissão para falar.
Acrescentar `company_id` ao filtro (CLAUDE.md §7).

### 2.4 · Testes com mutação — obrigatórios
| Teste | Mutação que tem de reprovar |
|---|---|
| eco da IA não pausa a conversa | remover o registro da digital |
| atendente por texto pausa | — |
| atendente por **áudio** pausa | voltar a exigir `text` |
| leitura falhando ⇒ IA **cala** | voltar a fail-open |
| a **outra** conversa segue com a IA | — (controle) |
| mesmo telefone em outra corretora não é tocado | — (controle) |

---

## 5. BLOCO 3 — Travas e o dossiê

### 3.1 · `INSURER_DISPATCH_LIVE=false` (R1)
Com ela fechada o acionamento roda **até o fim** e grava `dry_run: true` com o
conteúdo que teria enviado.

### 3.2 · D6 — Lapidador atrás da mesma trava
📊 Roda sozinho, semanal, madrugada, em `claude-opus-5`, **sem consultar o teto**.
**Ação.** Sujeitá-lo ao mesmo interruptor. Nasce desligado.

### 3.3 · Comentário vencido no arquivo de envio
📊 A docstring de `evolution_go.py` diz "recusa por padrão"; o código faz o
oposto. **É verdade vencida no arquivo mais perigoso do sistema** (CLAUDE.md §9.3).

### 3.4 · D7 — O DOSSIÊ NOVO

**O que ele é.** A mensagem que a atendente recebe no WhatsApp quando o agente
precisa de gente. Ela tem que **olhar e já saber o que fazer** — sem abrir o
histórico.

**Diretrizes do Founder:** completo mas legível · linguagem humana (nunca
`assistencia.residencial.encanador`) · **sem protocolo e sem caso** (numeração de
um projeto que não existe mais) · com **diagnóstico e sugestão de ação**.

**Template proposto:**
```
🔧 ASSISTÊNCIA · ENCANADOR
━━━━━━━━━━━━━━━━━━━━━━━━━
Rafael Menezes · (47) 9627-4743
Allianz Residencial · apólice 2026231401085
Rua das Flores 210, Blumenau/SC

O QUE ACONTECEU
Vazamento embaixo da pia da cozinha desde ontem à noite.
Ele já fechou o registro. Não há risco elétrico.

O QUE FALTA
⚠️ Confirmar se é casa ou apartamento (a Allianz pergunta)

👉 O QUE FAZER
Acionar encanador pela Allianz Residencial. A resposta do
formulário já está montada — é só confirmar.

━━━━━━━━━━━━━━━━━━━━━━━━━
CONVERSA (últimas 6)
14:32 Cliente  Oi, tô com um vazamento aqui em casa
14:33 🤖 IA     Poxa, que chato! Me conta o que houve?
14:35 Cliente  [🎤 áudio 12s]
14:36 👤 Marina Já vou verificar sua apólice
━━━━━━━━━━━━━━━━━━━━━━━━━
▶ abrir: <link direto para a conversa>
Ninguém assumiu ainda · há 4 minutos
```

**As sete regras deste template:**
1. **Título em linguagem humana**, com emoji do tipo de serviço
2. **Identificação em 3 linhas** — quem, qual seguro, onde
3. **"O QUE ACONTECEU"** — narrativa em português, não campos soltos
4. **"O QUE FALTA"** — só o que bloqueia; se nada falta, a seção some
5. **"O QUE FAZER"** — a recomendação. É o que a atendente lê primeiro
6. **🤖 IA vs 👤 pessoa** — marcado em cada linha. Ela precisa saber quem
   prometeu o quê. Hoje tudo é "Agente"
7. **Link direto + quem assumiu + há quanto tempo**

**Onde testar:** AMANDUS (R2).

---

## 6. BLOCO 4 — D4 · O sistema reconhecer as seguradoras
> Este bloco vem **antes** da destilação. Sem ele, conversa de seguradora
> entraria no RAG como se fosse conversa de cliente.

### O achado
📊 As conversas **estão** capturadas, com menus e botões:

| telefone | interativas | quem é |
|---|---:|---|
| `551140029000` | 97 | **MAPFRE** — *"A MAPFRE Seguros agradece o seu contato"* |
| `552733204114` | 283 | vistoria — *"Reagendamento (Vistoria)"*, *"Status do atendimento"* |
| `553196158666` | 74 | carro reserva — *"15 diárias"*, *"a Localiza poderá"* |

Total: **2.453 mensagens interativas** no acervo.

📊 E `insurer_key = 0`. **O sistema captura e não sabe o que capturou.**

**Causa (a confirmar no bloco):** o registro de números de seguradora só tem os
telefones de **assistência 24h** (`INSURER_CONTACT_*_ASSISTENCIA`). A Regina usa
os números de **atendimento ao corretor / sinistro**, que são outros.

### Ações
| # | O quê |
|---|---|
| 4.1 | **Diagnóstico somente leitura** (R4) — por que o reconhecimento falha, sem tocar em pareamento |
| 4.2 | Levantar os números **reais** de seguradora a partir do acervo (assinatura: quem manda botão/lista não é cliente) |
| 4.3 | Ampliar o registro — por corretora, sem quebrar isolamento |
| 4.4 | **Reprocessar o histórico**: marcar `insurer_key` retroativamente |
| 4.5 | Alimentar o **Atlas** com esse material — é o passo a passo clique a clique |
| 4.6 | Tirar essas conversas da **mesa da atendente** (elas não são cliente) |

### Por que este bloco vale mais que todos os outros juntos
Cada acionamento que a Regina faz é um mapa de URA de graça. **Estamos jogando
fora todo dia.** É a resposta para *"a inteligência dos acionamentos está
aumentando?"* — não estava porque o material nunca chegou ao Atlas.

---

## 6-B. BLOCO 5 — A AUDITORIA DA REALIDADE
> **O bloco mais importante desta SPEC para o futuro do projeto.**
> Comparar o que a Regina e a Saionara **realmente fazem** com o que os mapas,
> os playbooks e as instruções **dizem que se faz** — e corrigir só o que
> mudou de verdade.
>
> Decisão do Founder, 14/08: *"não podemos regredir, nem deixar oportunidades
> passar"*.

### 6-B.1 · Por que ele existe

Os mapas de URA foram construídos por observação. As URAs mudam. Um menu que
trocou de tecla transforma um corredor que funciona num corredor que erra — e
o erro só aparece com um segurado real esperando guincho.

📊 E o material para conferir **já está no acervo**: 2.453 mensagens
interativas, com menu, botão e passo a passo, de conversas reais.

### 6-B.2 · 🔴 As quatro travas — o que impede este bloco de piorar o produto

| # | Trava | Por quê |
|---|---|---|
| T1 | **O padrão é CONFIRMA** | O ônus da prova é de quem quer mudar. Um agente solto "melhora" o que está certo |
| T2 | **Nunca edita no lugar** | Gera versão nova; a `active` só cai quando aprovada. Mesmo padrão do gate de playbook |
| T3 | **Toda mudança cita a mensagem exata** | Data, hora e texto literal. Sem citação, a proposta é descartada sem discussão |
| T4 | **O juiz entra DUAS vezes** | Ver 6-B.4 |

### 6-B.3 · Os três vereditos possíveis por rota

```
CONFIRMA   o mapa bate com a conversa            → nada muda
MUDOU      a URA mudou                           → proposta + citação obrigatória
NOVA       apareceu rota que não tínhamos        → proposta + citação obrigatória
```

Um quarto desfecho é legítimo e deve ser dito em voz alta:
**SEM EVIDÊNCIA** — não houve conversa suficiente para julgar aquela rota.
Silêncio não é confirmação.

### 6-B.4 · Onde o juiz crítico entra — e por que duas vezes

**Juiz 1 — ANTES de escrever qualquer coisa.** *"A evidência sustenta esta
mudança, ou o agente está vendo padrão onde não tem?"*
É o portão mais importante do bloco. Uma conversa atípica não é mudança de URA.
O juiz reprova a proposta e a rota volta para CONFIRMA.

**Juiz 2 — DEPOIS de escrever.** *"O mapa novo responde melhor que o velho
contra as MESMAS conversas?"* Mesma regra do gate de playbook: **empate mantém
o antigo.** Regredir tem de ser estruturalmente impossível.

### 6-B.5 · Como será executado

| | |
|---|---|
| Motor | subagentes **Opus 5, esforço máximo**, plano Max (R5) |
| Um subagente **por seguradora** | não misturar HDI com Yelum numa cabeça só |
| Entrada | as conversas reais daquela seguradora + o mapa `active` + o playbook + o corredor |
| Saída | um cartão por rota: veredito · evidência citada · proposta (se houver) |
| Juiz | subagente separado, que **não escreveu** a proposta |
| Tecelão | só entra depois do Juiz 1 aprovar a evidência |

### 6-B.6 · Escopo — as duas frentes

**Frente A · AutoFleet (Regina) — todas as seguradoras**
📊 A Regina aciona por WhatsApp e as conversas estão todas no acervo, uma
seguradora por número. Auditar cada uma contra o seu mapa.

**Frente B · Allianz Residencial (Saionara/Resulta) — auditoria dedicada**
Decisão do Founder, 14/08: *"é um WhatsApp importante, com bastante demanda…
precisa ser feita uma análise bem detalhada… não pode ter erro nisso."*
Allianz Residencial é o corredor com mais serviços (eletricista, encanador,
chaveiro, desentupimento, eletrodomésticos) e o candidato natural ao primeiro
teste ponta a ponta. Ganha subagente próprio e passada mais profunda.

### 6-B.7 · O que sai deste bloco

1. Mapas do Atlas corrigidos **só onde mudou**, com rota nova incorporada
2. Playbooks ajustados onde a conversa real contradiz a conduta escrita
3. Instruções de corredor conferidas contra a prática
4. **Um relatório do que NÃO tinha evidência** — a lista do que ainda não
   sabemos, que é tão valiosa quanto o que corrigimos

### 6-B.8 · O que este bloco NÃO faz
Não aciona nada · não escreve em WhatsApp nenhum · não ativa mapa sozinho —
toda promoção passa pelo humano, como no gate de playbook.

---

## 7. BLOCO 6 — D5 · O portal de vidros
> 📊 Prioridade alta: vidros é um dos principais serviços, e **não** vai pelo
> WhatsApp da seguradora — vai pelo portal `abraseuatendimento.com.br`, que
> atende **várias** seguradoras.

### O estado
📊 `vidros_lanternas.py` tem **8 telas mapeadas**. Mas:
```
39 acionamentos → ZERO protocolos capturados
Todas pararam na tela 6 — a que ABRE o pedido — por causa da trava.
A tela 7 (a do protocolo) NUNCA foi vista pelo robô.
```

### O que a Regina entregou em 14/08 — e o que falta
| Ela mostrou | O robô sabe? | Ação |
|---|---|---|
| `Atendimento nº 23085997` | ✅ (inclusive o `º` vs `°`) | — |
| **`Franquia R$ 925,00`** | ❌ zero menções | ensinar a ler |
| **`https://vistoria.mobi/...`** | ❌ zero menções | ensinar a ler |
| Popup *"Queremos entender melhor sua necessidade"* — aparece em **todos** os atendimentos, não só Tokio | ❌ não sabe que existe | mapear a tela e as 5 opções |
| Regra: para-choque / lataria / pequeno reparo → **loja**; resto → **link** | ❌ | virar regra de playbook |
| Depois ela pega o link no **portal maxpar do corretor** | ❌ passo inexistente | mapear |
| *"não existe questionário… peça é a mesma para o grupo do veículo"* | ❌ | tratar o caso sem perguntas |

### Ações
5.1 mapear as telas novas · 5.2 ensinar a extrair **franquia + link + protocolo**
(os três, não só um) · 5.3 a regra loja-vs-link no playbook · 5.4 o passo do
portal maxpar · 5.5 **quando o agente deve escolher o portal em vez do WhatsApp**
· 5.6 nenhuma tela desconhecida trava: pausa com `needs_human` e diz qual era.

---

## 8. BLOCO 7 — Os testes
> R1, R2 e R3 valem em todos.

### Teste A · conversa (sem tocar em seguradora)
AMANDUS · celular do Founder como cliente · agente ligado · dispatch DESLIGADO.
Mede: a conversa é humana? aguenta rajada? escolhe o playbook certo?
**a IA continua respondendo depois da primeira mensagem?** (prova do D1)
E: quando o Founder responde pelo celular da corretora, **a IA cala?**

### Teste B · acionamento por WhatsApp de seguradora
🔴 **Exige apólice real — o Founder autoriza caso a caso (R3).**
Vai até o formulário e **para**. Mede qual mapa, qual playbook, e **o nome do
envelope do formulário** — a dúvida silenciosa da HDI/Yelum.

### Teste C · portal de vidros
🔴 **Exige apólice real (R3).** Vai até a tela anterior à confirmação e **para**.
Mede: passa o popup novo? chega à tela 7? lê franquia e link?

### Teste D · linha de controle
Uma conversa em que só o humano responde — tem de ficar pausada. Prova que o
mecanismo funciona e que o defeito era a falta de distinção de autor.

---

## 9. BLOCO 8 — A destilação *(madrugada, quando o Founder avisar)*

**Entrada:** AutoFleet histórica + AutoFleet atual + Resulta.
**Motor:** subagentes Opus 5, esforço máximo, plano Max. Zero API (R5).
**Juiz:** nosso, no plano Max (R6).

### A ordem — não pode ser trocada
```
1. SEPARAR      conversa de CLIENTE  ×  conversa de SEGURADORA
                (depende do BLOCO 4 — sem ele, contamina)
2. CLASSIFICAR  ramo + serviço por sessão
3. AGRUPAR      juntar as que dizem a mesma coisa
4. TRIAR        o que é lixo sai; o que o acervo já tem sai
5. DESTILAR     por grupo, nunca por sessão
6. JULGAR       juiz crítico — só passa o que melhora
7. ENCAMINHAR   playbook · carta do RAG · mapa do Atlas · descarte
```

**Metas:** os 6 drafts do beco sem saída (bateria, pneu, chaveiro de auto;
vidros de outro/residencial; chaveiro residencial) ganharem material · as
conversas de seguradora virarem **mapa**, não carta · nenhuma carta que repita
o que já existe.

**Exclusão:** AMANDUS (`3aa75902-a3d5-4c5d-ac4b-66cbfbc782fe`) — corretora de
teste, conversas fictícias.

---

## 10. ORDEM DE EXECUÇÃO

### As levas — executadas inteiras, não picotadas

```
LEVA 1 · A BASE SEGURA                                   ~4h · sem risco externo
  BLOCO 1  Resulta: a mesa da Saionara ........ 10 min
  BLOCO 2  os 3 P0 + mutações ................. ~2h     trava o "ligar agente"
  BLOCO 3  travas + Lapidador + dossiê novo ... ~1h30
  → ao fim: o agente pode ser ligado sem se calar; nada aciona nada

LEVA 2 · A INTELIGÊNCIA DA REALIDADE                     ~5h · subagentes Opus 5
  BLOCO 4  reconhecer seguradora .............. ~2h     habilita tudo abaixo
  BLOCO 5  auditoria da realidade ............. ~3h     mapas × conversas reais
           Frente A: AutoFleet, todas as seguradoras
           Frente B: Allianz Residencial (Saionara), dedicada
  → ao fim: os mapas dizem o que a URA realmente faz

LEVA 3 · O PORTAL DE VIDROS                              ~2h
  BLOCO 6  telas finais, franquia, link, popup novo, regra loja×link

LEVA 4 · OS TESTES                                       com o Founder
  BLOCO 7  A e D na Amandus  ·  B e C exigem R3

LEVA 5 · A DESTILAÇÃO                                    madrugada, sob aviso
  BLOCO 8  agrupar → triar → destilar → julgar → encaminhar
```

**Dependências que não podem ser trocadas:**
- BLOCO 5 depende do 4 (sem `insurer_key` não se sabe qual conversa é de quem)
- BLOCO 7 depende do 2 e do 5 (mapa errado faz o teste falhar pelo motivo errado)
- BLOCO 8 depende do 4 e do 5 (senão conversa de seguradora contamina o RAG)

---

## 11. PENDÊNCIAS — registradas, não perseguidas nesta SPEC

| # | O quê |
|---|---|
| **P-130** | **Loop juiz-crítico em todo ponto que fizer sentido** — não só playbook: cartas, mapas, destilação, instruções. Padrão: um agente propõe, um juiz reprova sem gabarito. **Item estruturante — decisão do Founder, 14/08** |
| P-131 | Devolução automática da conversa à IA (hoje, tocou pelo celular = pausada para sempre + alarme falso a cada 6h) |
| P-132 | Métrica de "turnos sem conduta" — hoje a falta de playbook degrada em silêncio |
| P-133 | Rajada acima de 25s parte no meio |
| P-49 | Nenhum corredor testado contra URA real |
| P-124 · P-127 | Gate SEC-05 · views com SECURITY DEFINER |
| — | Docs canônicos dizem 11 e 13 corredores; o código tem 14 |
| — | Admin com 40+ telas; o atendimento usa 4 |

---

## 12. O QUE SÓ O FOUNDER PODE FAZER

| # | O quê | Quando |
|---|---|---|
| 1 | Liberar os Blocos 1–5 | agora |
| 2 | Autorizar apólice real, caso a caso | testes B e C |
| 3 | Avisar a hora da destilação | madrugada |
| 4 | Aprovar os playbooks no gate | depois da destilação |
| 5 | Configurar os grupos de suporte humano | antes da demonstração |
