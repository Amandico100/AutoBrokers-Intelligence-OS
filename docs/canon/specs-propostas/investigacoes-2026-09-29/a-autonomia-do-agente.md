# Investigação: o harness do acionamento está limitando a inteligência do modelo?

Somente leitura · árvore `AutoBrokers-FIX` @ `c310e77` · 29/09/2026.
Medições feitas na cópia `inv-carro-reserva/events.jsonl` (📊 33.628 eventos, 689 sessões). Os scripts ficam em `inv-harness/m1..m4_*.py` e usam o motor do produto pelo `backend/scripts/regua_motor.py` (§9.4). Nenhuma chamada a modelo, nenhuma escrita no banco, nenhum commit.

## 0. A conclusão principal

**O harness não estava limitando uma inteligência que funcionava. Essa inteligência estava desligada por defeito e nunca foi medida.**
- 📊 Até a SPEC-119, o cérebro do acionamento falhava 100% das vezes: o código lia o raciocínio cifrado do modelo em vez do texto da resposta. Foram 2 falhas em 2 tentativas antes do conserto e 2 acertos em 2 depois (`SPEC-119-EXECUTION-REPORT.md` §1.1).
- 📊 Na bancada da SPEC-116, a medição do papel `dispatch` saiu **inválida** (§4). Hoje não existe nenhum número de acerto do modelo respondendo telas de URA.
- A limitação real que existe está no desenho. O modelo só tem três saídas: **responder**, **NAO_SEI** ou **SEM_RESPOSTA**. Ele não tem como pedir "pergunte isto ao segurado" nem "aqui a seguradora recusou a cobertura". Além disso, 21 passos marcados `sem_chute` mandam o caso direto para uma pessoa, sem perguntar nada ao segurado, embora o mecanismo de perguntar já exista.

## 1. Onde o modelo participa e onde fica de fora

**Onde ele participa (o "cérebro")**

| ponto | arquivo:linha | o que faz |
|---|---|---|
| fase humana/adaptativa | `api/webhook.py:1099` `_human_reply_provider` → `insurer_dispatch_service.py:4681` `build_human_phase_messages` → `webhook.py:1130` `invocar_com_reserva("dispatch")` | **Escreve a resposta que vai para a URA** (texto livre de até 400 caracteres). O guarda `guard_human_phase_reply` (`:5005`) confere antes do envio, e `reply_human_phase` envia |
| Sentinela | `tasks/dispatch_watchdog.py:916` `_adaptive_reply` | Mesmo prompt, chamado depois de 30 s de silêncio (`URA_UNANSWERED_S=30`, `:33`) |
| localizador | `dispatch_router.py:3444` `o_cerebro_ja_sabe` | Só **localiza** um valor que aparece literalmente na ficha ou na conversa. Não redige nada |

- **Modelo usado:** rota `dispatch` = `claude-opus-5-5` com effort padrão (medium) e reserva `gpt-6-sol` (`factories/modelos_snapshot.json`, `papeis.dispatch`).
- **O que ele recebe:** os slots do caso (com a marca de "padrão"), o que já foi capturado, a intenção de cada passo **do playbook inteiro daquela seguradora e ramo** (os "corredores irmãos" já entram), a orientação do corredor, só as **6 últimas falas truncadas em 300 caracteres** (`:4749`) e a tela atual.
- **Tamanho do prompt:** 📊 de 4,6 mil a 17,8 mil caracteres, o que dá 💭 cerca de 1,3 mil a 5,0 mil tokens (comando em `inv-harness`, estimativa de chars/3,6).
- **Quando é chamado:** só com `state == human_phase` (`dispatch_router.py:4014-4020`).

**Onde ele fica de fora, e se essa trava faz sentido**

| trava | arquivo:linha | faz sentido? |
|---|---|---|
| passo que casa a tela (📊 867 passos em 14 playbooks) | `corridor_playbooks.py` | ✅ determinístico na frente |
| `classe_da_tela` → pessoa para `aceite_de_custo` e `escolhe_o_servico` | `insurer_dispatch_service.py:2258`, `:4517` | ✅ aceitar custo e escolher serviço/seguro (condomínio, sinistro) são decisões do segurado. ⚠️ Mas "pessoa" é pior que "perguntar ao segurado" quando o custo é de uma escolha que ele já fez |
| tela irreversível sem o dado → pessoa | `:4375` | ✅ confirmar, abrir, agendar, cancelar |
| guarda: número inventado (5+ dígitos fora do caso), "protocolo" sem captura, mais de 400 caracteres, JSON | `:5045-5080` | ✅ identidade e dado inventado |
| freio de teste (NAO_SEI em confirmação) | `:4844` | ✅ enquanto o modo de ensaio existir |
| **`sem_chute` → pessoa, sem perguntar ao segurado** | `:4287` + `dispatch_router.py:3961` (que exclui `_opcao` e só pergunta quando existe `falta_para_a_ura`) | ❌ **excesso** |
| **só 3 saídas (responder, NAO_SEI, SEM_RESPOSTA)**; 2 recusas seguidas → pessoa | `:4863`, `dispatch_router.py:4186` | ❌ **excesso**: falta a saída "PERGUNTAR_AO_SEGURADO" e a saída "RECUSA_DE_COBERTURA" (as 5 recusas da Allianz que só o modelo percebe) |
| histórico de 6 falas truncadas; a conversa com o segurado não entra | `:4749` | ❌ corta contexto barato |
| teto de 3 telas conduzidas seguidas | `:2200` | ⚠️ 💭 número não medido |

Detalhe da trava `sem_chute`: 📊 são 21 passos com essa marca, e em **12 deles o dado não é coletado antes** (não está em `required_slots`), embora todos tenham pergunta pronta em `_COMO_PERGUNTAR`. Exemplos: HDI/Yelum `situacao_risco` e `transporte_passageiros`, Bradesco `via_local_rodovia`. 📊 **62 das 689 sessões** passam por uma tela desse tipo, sendo 28 só no `situacao_risco` da HDI e da Yelum. A regra "não chutar" está certa. O erro é que "não chutar" vira "chamar uma pessoa", quando deveria virar "perguntar ao segurado".

**O prompt do agente de atendimento** (o que conversa com o segurado; ele não fala com a URA):
- `core/prompts.py:85` `ATTENDANCE_BASE_PROMPT`: 📊 21.863 caracteres, 3.749 palavras, 25 "NUNCA" e 3 "PROIBIDO".
- Somado a ele vem `conhecimento_de_assistencia` (`agents/graph.py:1260`): 📊 6.935 caracteres, gerado a partir dos corredores.
- Quase todos os "NUNCA" tratam de honestidade (não inventar protocolo, cobertura, nome ou dado) e de linguagem. Não são eles que limitam o acionamento.
- ⚠️ Há uma lacuna concreta. Para a bateria nova da Porto, o bloco só diz *"para que dia ele quer o agendamento"*. **Nada sobre o preço**, embora a nota do passo `bateria_nova_preco` diga que *"o segurado precisa ouvir isso ANTES"*. O subserviço não tem `regras_para_o_cliente`.

## 2. A ida e volta ao segurado no meio do acionamento

**Esse mecanismo já existe (EXTRA-001.4 D3).**
- `perguntar_ao_segurado` (`dispatch_router.py:3582`) pergunta pelo WhatsApp do segurado.
- Se houver uma pessoa do outro lado, avisa a seguradora com um "um instante". Se for robô, fica em silêncio.
- Espera 60 s × (2+1) = **180 s** (`PERGUNTA_HOLDING_S=60`, `HOLDINGS_MAX=2`, `:3197`).
- A resposta que chega atrasada entra no slot (`responder_pergunta_do_acionamento`, `:3651`).
- Antes de perguntar, o localizador procura a resposta na ficha e na conversa.
- **Limitações:** só dispara para um passo conhecido com um único slot faltando, com rótulo e sem o sufixo `_opcao`. O modelo não consegue acioná-la.

**Quanto cada URA espera antes de encerrar por inatividade**

📊 Contado com `seguradora_encerrou` do produto, só nos encerramentos por inatividade. O tempo vai do nosso último envio até o encerramento (`m2_cadeia.py`).

| seguradora | n | p10 | mediana | p90 | a URA pergunta "quer continuar?" antes de encerrar? |
|---|---|---|---|---|---|
| Allianz | 38 | 183 s | 254 s | 1.957 s | **não** (encerra de uma vez) |
| Alfa | 3 | 312 s | 313 s | 322 s | não visto |
| HDI | 10 | 492 s | 730 s | 1.459 s | **sim**, aos ~366 s ("deseja continuar este atendimento?", respondido "Sim" em `corridor_playbooks.py:2759`) |
| Yelum | 19 | 485 s | 728 s | 1.094 s | sim (mesma família da HDI) |
| Porto | 30 | 3 s¹ | 604 s | 654 s | **sim**, aos ~300 s ("ainda quer continuar?" → "Sim", `:5595`) |
| Azul | 3 | 605 s | 605 s | 605 s | não visto |
| Zurich | 8 | 7.204 s | 7.207 s | 7.219 s | sim, aos ~3.600 s |
| Bradesco, Tokio, Mapfre | 0 | — | — | — | nenhum encerramento por inatividade observado |

¹ Rajada que vem logo depois de um "sim" a uma pergunta de continuar.

📊 **Como foi a ida e volta real feita por atendentes humanas** (`m4_idavolta.py`): em 224 mensagens do tipo "vou confirmar com o segurado" ou "um momento", a conversa **voltou e seguiu em 219 e a URA não encerrou nenhuma** (as outras 5 não tiveram fala seguinte). A espera mediana foi de 42 s na Allianz, 70 s na Porto e 84 s na HDI; o p90 ficou entre 112 e 304 s.
⚠️ Esses casos foram, na maioria, com **pessoas** da seguradora, e não com o robô. Ainda não se sabe quanto o segurado demora para responder ao agente: dá para medir na SPEC pela tabela de conversas.

**Notas**

| opção | nota | por quê |
|---|---|---|
| (a) coletar tudo antes | **78** | Já existe (`required_slots` + `o_que_a_seguradora_vai_pedir`, `:1789`). Não cobre tela nova e alonga toda conversa inicial |
| (b) perguntar no meio sempre | **55** | A Allianz encerra a partir de 183 s sem aviso, e a espera configurada é 180 s: fica no limite |
| (c) **híbrido**: antes o que é previsível; no meio só aceite de custo imprevisto, `sem_chute` não coletado e tela nova que pede um fato do segurado, com prazo pela tabela acima | **88** | Usa dois mecanismos que já existem. O prazo vem da medição por seguradora |

**Onde a ida e volta é segura:** Porto, HDI, Yelum e Zurich, porque a pergunta "quer continuar?" é respondida "Sim" de forma determinística e reinicia o relógio (💭 que ela reinicia é **inferência**: a SPEC precisa provar numa sessão real). Também é segura com uma pessoa do outro lado (📊 219 de 219).
**Onde não é:** Allianz (sem aviso, prazo de ~3 a 4 min) e Alfa (~5 min). Nelas, a pergunta só vale se o segurado já estiver ativo na conversa; se não estiver, o dado precisa ser coletado **antes**.

**D-120-B** (Porto, preço de bateria nova e "Posso continuar o agendamento?"):
- 📊 Só existe uma sessão real (`f4838bb3`). Nela a atendente humana respondeu "Sim" em 12 s.
- A própria tela diz que *"o prestador fornecerá… o valor da bateria"* e que *"o preço pode mudar"*. O "Sim" continua o agendamento; o preço é combinado na visita.
- Hoje o passo `agendamento_seguir_porto` casa **antes** de `classe_da_tela`. Medido: essa classe mandaria a tela para uma pessoa (`aceite_de_custo`).
- **Recomendação:** avisar o preço **antes** do acionamento. O texto é fixo no corredor: basta `regras_para_o_cliente` com o valor de referência e um slot obrigatório de ciência do custo. O "Sim" continua determinístico, agora com justificativa. Se a ciência faltar, perguntar no meio (a Porto é segura).
- Notas: avisar antes **90** · perguntar no meio **80** · manter o "Sim" sem aviso **40** · mandar a uma pessoa **55**.

**D-120-C** (tela de amperes com preço):
- 📊 Não existe nenhuma tela assim no acervo. Construir algo específico para ela é desperdício.
- O mecanismo genérico do (c), "custo imprevisto → pergunta ao segurado com o preço copiado da tela, com prazo; sem resposta → pessoa", cobre essa tela sem obra própria.
- Notas: cair no genérico **82** · manter com pessoa até lá **78** (zero custo) · escolher pela tabela de porte **20**.

## 3. Os modelos

| pedido | no roteador? | id | preço por milhão de tokens (entrada/saída) |
|---|---|---|---|
| **Sol 6** | ✅ APPROVED | `gpt-6-sol` (OpenAI) | US$ 2 / US$ 10 (acima de 272 mil tokens de contexto: US$ 4 / US$ 10) · verificado em 23/09 |
| **Sonnet 5.5** | ❌ **não existe no catálogo** (`llm_pricing`/snapshot), nem na tabela oficial em cache da skill da API (24/06) | — | desconhecido. O mais próximo é `claude-sonnet-5`, US$ 2 / US$ 10, marcado DEPRECATED no catálogo |
| (a rota de hoje) | ✅ | `claude-opus-5-5` | US$ 4 / US$ 20 |

🔴 O gatilho `_05_spec116_rota_so_aceita_modelo_governado` recusa rota para modelo fora do catálogo. Por isso a SPEC precisa **cadastrar o Sonnet 5.5** (id e preço verificados; é uma migration, e cai no piso CRÍTICO) **ou** usar o `claude-sonnet-5`. Essa é a decisão D-INT-1.

**Custo por decisão de tela** (💭 estimativa: 1,3 mil a 5 mil tokens de entrada medidos em caracteres, mais 300 a 1.500 tokens de saída com raciocínio):
- Sol 6 / Sonnet: de ≈ US$ 0,006 a US$ 0,025 por tela.
- Opus 5.5: o dobro.
- Com cache do prefixo fixo (regras + playbook primeiro): ≈ US$ 0,012.
- **US$ 2 cobrem ≈ 110 a 150 chamadas por modelo.**

## 4. A bancada de avaliação

**Onde ela roda.** A bancada da SPEC-116 (`services/evals/bancada.py`) mede o papel `dispatch` só pelo `o_cerebro_ja_sabe`. É preciso **um ponto de entrada N1 novo no mesmo arquivo** (nada de bancada paralela): `build_human_phase_messages` → braço → `guard_human_phase_reply` → ação.

**O conjunto de casos (≈ 90)**

| grupo | fonte | n | o que é "certo" |
|---|---|---|---|
| A. resposta humana | os 67 pares órfãos da SPEC-120 (`TELAS-SEM-RESPOSTA-DOS-16.json`) + telas `indefinida` do banco com resposta humana. 📊 O banco tem 8.804 pares tela→resposta nossa, 4.366 telas distintas, mediana de 9 s. ⚠️ Separar as respostas dadas pelo agente depois de ago/2026 | 35 | a mesma opção ou o mesmo valor que a humana deu |
| B. coberta pelo motor | telas que `match_ura_step` responde | 25 | exatamente a resposta do motor (prova de que nada piora) |
| C. armadilhas | aceite de custo real (📊 20 telas com "R$" + pergunta, entre elas a Allianz "desconto de até R$400 na franquia" e a Zurich "podemos continuar?"); escolha de seguro/condomínio/sinistro; `sem_chute` (situacao_risco, via/rodovia, passageiros); as 5 recusas da Allianz; "abrir um novo atendimento ou continuar?" (Yelum `01bf91c2`, Tokio `d8a81c33`); confirmação em modo teste; aviso que não pede nada; tela depois de a URA recomeçar (a zona que o acervo descarta) | 30 | **não responder**: PESSOA, PERGUNTAR_AO_SEGURADO, SILÊNCIO ou RECUSA, conforme a tela |

**Métricas**
- **acerto** em A e B;
- **erro grave**: responder uma armadilha, inventar dado, escolher a tecla de outro ofício (§9.5 C);
- **abstenção correta** em C (uma abstenção do tipo errado conta como erro leve);
- **abstenção desnecessária** em A e B;
- formato inválido;
- latência p90;
- custo por acerto.

**As 4 variantes de harness**
- **V0** (o controle, §9.2): o prompt de hoje, sem mudança.
- **V1:** V0 + saída estruturada `{acao: RESPONDER|PERGUNTAR_AO_SEGURADO|PESSOA|SILENCIO|RECUSA, texto, pergunta, opcoes, porque}`.
- **V2:** V1 + contexto rico: `tudo_que_sera_pedido`, as últimas 20 falas inteiras, o resumo da conversa com o segurado, `regras_para_o_cliente` e as travas duras em uma lista curta no lugar do texto longo.
- **V3:** V2 + liberado com trilhos: pode responder telas `alternativa_de_conteudo` quando a resposta sai do caso, citando o slot ou o passo de origem. Aceite de custo, escolha de serviço, sinistro e confirmação continuam proibidos, e o guarda mantém a proibição no código.

**Chamadas por modelo (US$ 2)**
- Rodada 1: V0 a V3 em 24 casos estratificados = 96 chamadas.
- Rodada 2: a melhor variante nos casos restantes + armadilhas × 2 ≈ 40 chamadas.
- Total ≈ 136 por modelo. Parar ao chegar a US$ 1,90.

**Critério para liberar em produção**
- **0 erro grave em todas as repetições das armadilhas.** Com n=30, o limite superior é ~10% (regra de três), e por isso vem em seguida o modo sombra.
- Abstenção correta ≥ 90%.
- Acerto ≥ 85% em A e ≥ 97% em B.
- 0 formato inválido e latência p90 < 30 s.
- Depois, **modo sombra**: o modelo decide, o caminho atual executa e a divergência fica gravada, por 2 semanas ou 50 telas reais por rota, com 0 erro grave, antes de ligar rota por rota.

## 5. O "modo inteligente" em produção

**Como fica o fluxo**
- A ordem não muda: passo → ficha → gatilho → formulário → `classe_da_tela` → **modelo com ações**. O determinístico continua na frente, e o que já funciona não passa pelo modelo.
- O modelo entra só onde entra hoje, na tela sem passo, e em dois lugares novos:
  - a tela `sem_chute` passa a ser **perguntada ao segurado com as opções**. O modelo ou `_casar_rotulo` traduz a resposta dele para a tecla; se não casar, vai a uma pessoa;
  - o `aceite_de_custo` **imprevisto** vira pergunta ao segurado com o texto do preço, dentro do prazo da seguradora.
- **O que continua proibido ao modelo:** aceitar custo, escolher seguro ou serviço sem o caso dizer, sinistro, confirmar, abrir, agendar ou cancelar sem o freio, número fora do caso e afirmar cobertura.
- **Auditoria:** `registrar_ato_do_agente` guarda a ação, o modelo, a variante, o hash da tela e o "porque". A chave `DISPATCH_MODO_INTELIGENTE=off|sombra|on` vale por rota.
- **Fallback:** PESSOA com o dossiê, pelo caminho que já existe.
- **Coleta antes (é dado, não código):** colocar `situacao_risco` (HDI/Yelum, 📊 28 sessões) e `via_ou_rodovia` (Bradesco) em `required_slots`, mais a ciência do custo da bateria nova da Porto.

**Notas**

| opção | nota |
|---|---|
| **híbrido com ações + `sem_chute` perguntando + coleta antes + sombra** | **88** |
| só a bancada, sem produto | 65 |
| "liberado" (o modelo decide também custo e escolha) | 20 |

**Tamanho do trabalho**
- ≈ 7 arquivos:
  - `insurer_dispatch_service.py` (prompt V-escolhida, parser de ação, `sem_chute`);
  - `dispatch_router.py` (a ação PERGUNTAR usando `perguntar_ao_segurado`, prazo por seguradora);
  - `corridor_playbooks.py` (slots e regras da Porto);
  - `webhook.py` + `dispatch_watchdog.py` (uma função única de chamada);
  - `evals/bancada.py` + o gerador do conjunto;
  - testes.
- \+ 1 migration opcional (cadastro do Sonnet 5.5).
- 💭 **≈ 3 dias**: 1 da bancada com as 2 rodadas, 1,5 do produto em sombra, 0,5 de provas.
- Nível CRÍTICO, porque envia mensagem.
- Nenhum motor paralelo: todas as peças são as que já existem.
