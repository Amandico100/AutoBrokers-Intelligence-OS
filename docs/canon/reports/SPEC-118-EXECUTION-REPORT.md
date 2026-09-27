# Relatório de execução — SPEC-118: O formulário dentro do WhatsApp funciona, e o agente sabe o que vem

**Produto:** AutoBrokers Intelligence OS
**SPEC:** `specs-propostas/SPEC-118-o-formulario-dentro-do-whatsapp-funciona-e-o-agente-sabe-o-que-vem.md`
**Branch:** `spec/118-formulario-nativo-e-corredores` · **Worktree:** `AutoBrokers-FIX`
**Início:** 26/09/2026 · **Conclusão:** 26/09/2026
**Commit inicial:** `70632a8` (= `origin/main`) · **Commit final desta fatia:** `00a78e7`
⚠️ O commit final da SPEC é o do gerente, depois do julgamento, da bateria e do `git push`.
**Estado final:** CONCLUÍDA — aguardando o Implantar do Founder e o canário

📊 medido · 💭 ilustrativo (§12.1) · FATO · INFERÊNCIA · RECOMENDAÇÃO marcados onde importa.

---

## 0.0 O EXECUTION CARD

```
OUTCOME ....  o segurado pede assistência no WhatsApp da corretora e recebe o protocolo da
              seguradora sem que nenhuma pessoa toque no caso — inclusive quando a seguradora
              abre o formulário nativo
RISCO ......  8  (ALCANCE o segurado 3 · REVERSIBILIDADE saiu do prédio 3 · FREQUÊNCIA 2)
SUPERFÍCIE .  2  (vários comportamentos + peça nova: mapas de formulário e o portão de coleta)
PISO .......  §3.2 — "qualquer coisa que ENVIE: mensagem, acionamento, chamado" → CRÍTICO
NÍVEL ......  🔴 CRÍTICO · rito AAA v13.2
UNIDADES ...  5 fatias (F1 transporte · F2 mapas · F3 o agente pede · F4 a costura · F5 a régua,
              os documentos e o controle do Founder)
COESÃO .....  F2 e o portão de coleta no MESMO arquivo-hub (`corridor_playbooks.py`) → juntos
PARALELISMO   F1 ‖ F2 (arquivos disjuntos) · F3 → F4 → F5 em série
TIME .......  5 builders frescos, um por fatia
REFERÊNCIA .  interna `_NATIVE_FLOWS_FAMILIA_HDI_YELUM` (`corridor_playbooks.py:2653`) ·
              externa `O-FORMULARIO-NATIVO-RESOLVIDO.md` §5 (medir com linha de controle)
GATES ......  §7
O ELO ......  título: "para PORQUE a rota não existe E falta o mapa". 🔴 1ª metade FALSIFICADA
              pelo comando: 📊 prova em produção 26/09 17:24 → 200 `InteractiveResponseMessage`,
              CONTROLE sem embrulho → 479. A rota EXISTE; swagger é catálogo, não capacidade
              (§0.4). 2ª metade MEDIDA: o fio nasceu VERMELHO (`sem_chute:latitude,longitude`)
              e ficou VERDE — B chega em A.
FAIXA DE RELÓGIO  💭 4–7 h declaradas · 📊 real 6 h 57 de commits (26/09 17:28 → 27/09 00:25),
              + prontidão antes e julgamento depois · 3 réguas (53 min) · 3 baterias (~1 h 05)

① PAINEL?   não — a conta do §3 não o pediu para uma fatia de documentos + um conserto de regex
            com régua antes/depois. A conta está escrita acima
② AUDITORIA EXTERNA?  juiz ‖ red team são do gerente, depois desta fatia
③ PENDÊNCIA por VALOR MARGINAL?  regerar o corpus (P-118-08): a régua teve de medir ANTES e
            DEPOIS com o MESMO corpus — ver D-118-03
```

---

## 0. Declaração de integridade

> ⚠️ **TAMANHO DECLARADO:** 📊 **16,3 KB** contra a diretriz de **≤ 15 KB** do protocolo (§5 ⑧) —
> 6% acima. Três cortes foram tentados e cada um removia **evidência**: as saídas das 3 rodadas de
> bateria, das 2 réguas e das mutações por blocker. 🔴 Preferi **declarar o excedente a apagar
> medição** — um relatório curto que não prova nada é pior que um 6% maior. O que **não** couber vai
> para os companheiros (`SPEC-118-REGUA-ANTES-E-DEPOIS.md`) e para os laudos, não para o lixo.


- [x] 🔴 **Nenhum motor paralelo** (§5). O `_STREET_RE` é **uma expressão** no reconhecedor que já
      existia; `valor_de_slot_honesto` é **uma** função com **três** consumidores, não três régua;
      a conferência do pin mora **num** lugar (`inject_address_slots`).
- [x] **Nenhuma migration**, nenhum DDL, nenhum segredo neste arquivo.
- [x] Nenhum escopo reduzido sem decisão registrada · nenhum dado atravessou tenants (§7).
- [x] `CLAUDE.md`, o protocolo e a SPEC lidos no início, por cada builder e cada julgador.
- [x] 🔴 **Nenhum nome de corretora, atendente, CPF ou telefone** em código, teste ou fixture
      (§13.9/§13.3) — conferido pelo red team nas 6.847 linhas novas.

---

## 1. Resumo executivo

**FATO.** Um acionamento pelo WhatsApp da **Porto** atravessa o formulário nativo **sem parar e sem
chamar uma pessoa**. 📊 Com o pin de localização e **nada digitado**: `state=ready_to_send`,
`missing_slots=[]`, `montar_resposta_de_flow → ok=True` com as 10 chaves da captura de 21/09.

**FATO.** A premissa central da proposta estava **errada**, e o comando a derrubou. A SPEC afirmava,
por leitura do `swagger`, que `/send/interactiveResponse` não existia, e pedia **rebuild** ao Founder:
```
POST /api/whatsapp-integrations/prova-de-formulario        (26/09 17:24, produção)
  tentativa 1 (CONTROLE, sem o embrulho) .... HTTP 500 · "server returned error 479"
  tentativa 2 (com DocumentWithCaption) ..... HTTP 200 · ACEITO
→ Type: "InteractiveResponseMessage" · ID 3EB02C9B1BFC57E46E3136
```
⛔ **Não houve rebuild.** O `swagger` não lista a rota porque o patch `0005` não anotou —
**catálogo incompleto não é ausência** (§0.4). **P-62** foi fechada com essa medição.

**FATO.** A **Tokio** deixou de fingir que atende (📊 52% das sessões terminam em link, não em
protocolo) e vai a uma pessoa **com dossiê**. E ali havia defeito grave: o handoff era
**INALCANÇÁVEL** — o segurado era **abandonado** até o vigia perceber, nunca passado a alguém.

**FATO.** 4 blockers do red team e 3 achados do juiz foram reproduzidos e consertados, cada um com
mutação **vermelha**. A confirmação curta: *"o conserto NÃO criou defeito"*, 136 passed.

⚠️ **MAIOR LACUNA, e ela é do Founder:** nenhuma seguradora recebeu uma resposta nossa. *"O formato
está certo"* e *"a Porto aceitou"* são duas afirmações; só a **primeira** está medida.

---

## 2. Escopo executado, por fatia

```
F1  TRANSPORTE  virou GUARDA, não conserto: fixa `/send/interactiveResponse` + `galaxy_message` +
                embrulho `DocumentWithCaptionMessage` OBRIGATÓRIO; a docstring vencida saiu (§9.3)
F1b A PROVA     `prova-de-formulario` passa a medir o caminho da PRODUÇÃO; o 404 para de prometer
                rebuild (foi essa frase vencida que enganou o gerente)
F2a OS MAPAS    `native_flows` da Porto das 3 capturas, cada uma com bloco `observed` apontando a
                linha do acervo; a pesquisa marcada NÃO-RESPONDÍVEL; a Azul declarada não mapeada
F2b A LÓGICA    o montador responde TEXTO; o portão soma os campos dos formulários que AQUELE
                subserviço abre; a Tokio vira handoff (📊 129 telas, 9 casam, 0 divergências) — e o
                handoff dela era INALCANÇÁVEL (`match_ura_step` precedia `detect_handoff_trigger`)
F3  O AGENTE    pede uma informação por vez, em português, ENSINANDO a mandar o pin; formulário sem
                fonte vira handoff COM MOTIVO, nunca silêncio
F4  A COSTURA   o TESTE DO FIO (⑤→⑭, motor real), que NASCEU VERMELHO; a coordenada ganha FONTE (o
                pin) e `latitude='0'` deixa de fechar o formulário
F5  RÉGUA+DOCS  régua antes/depois · `_STREET_RE` · a trava do `ref` fantasma · inventário · a aba
                CORREDORES · 6 documentos canônicos
CONSERTO ÚNICO  os 4 blockers do red team + os 3 do juiz, cada um com mutação VERMELHA
```

## 3. Arquivos alterados — a SPEC INTEIRA

📊 `git diff --stat origin/main..HEAD` → **30 arquivos, +6847 / −423**, em **48 commits**, arquivo
por arquivo (nunca `-A`). **7 motores** (`corridor_playbooks` · `insurer_dispatch_service` ·
`insurer_dispatch_tool` · `evolution_go` · `evolution_inbound` · `main` · `verificar_mutacoes`),
**11 guardas** (9 novos, 4 alterados mantendo a lição — §9.3), **1 fixture** (a captura de 21/09,
mascarada) e **9 documentos**. ⛔ **Zero migrations. Zero motores paralelos** (§0).

## 4. Migrations

**N/A — nenhuma.** 📊 Esta SPEC não tocou SQL em nenhuma fatia. Não há APPLY, VERIFY nem ROLLBACK a
escrever porque não há nada aplicado.

---

## 5. Testes executados — com saída real

### 5.1 O gate da SPEC — medido TRÊS vezes, por três leitores independentes

```
gerente,  HEAD 91808d5, 7 guardas ..............  80 passed in 39.82s
juiz fresco, mesmo HEAD, mesmos 7 .............  80 passed in 36.96s   (bate)
conserto, HEAD 581c271, 7 + 3 guardas novos ...  83 passed in 68.74s
confirmação, HEAD 581c271, 7 + o campo-tem-valor  136 passed, 0 failed
```
⚠️ `PYTHONIOENCODING=utf-8` **sempre**: sem ele os guardas-script morrem em cp1252 **e devolvem
exit 0** — falso verde. 📊 Nesta SPEC isso produziu 3 falsos "PROBLEMAS" e 1 falso verde meu
(`python tests/test_o_travamento_vira_linha.py` → saída vazia, exit 0: o arquivo não tem `__main__`).

### 5.2 O guarda do `_STREET_RE` — **nasceu vermelho**

📊 ANTES (`b897ac7`): `2 failed, 11 passed in 8.65s` — `{'rua':'Posto Shell','bairro':'R. Rafael
Bandeira',…}`. DEPOIS: `6 passed in 4.53s`. As 4 linhas de controle (via por extenso · `Dr.`/`Sr.`
que **não** são logradouro · sem ponto de referência · rodovia) verdes nas **duas** rodadas — o
mérito é do fator que mudou (§9.2). O guarda não foi escrito depois do conserto para carimbá-lo.

### 5.3 O guarda do `ref` fantasma — e a mutação que pegou um guarda MEU

📊 `7 passed in 4.40s`. 🔴 A 1ª redação era um carimbo: com a asserção sobre a **chave**, apagar a
linha que a **calcula** deixava verde, porque o caminho de erro escreve a mesma chave. Reescrita
sobre a **atribuição que chama o motor**: a mesma mutação dá `1 failed, 6 passed`. CLAUDE.md §9.3.

### 5.4 🔴 A RÉGUA COMPLETA, ANTES E DEPOIS

📊 Duas rodadas de `medir_rota.py --todas`, **mesmo corpus**, árvore **sozinha**. Nominal em
`SPEC-118-REGUA-ANTES-E-DEPOIS.md`.
```
ANTES b897ac7 18m24s   ·   DEPOIS 125a024 16m45s
AAA 0 · quase 26 · parcial 15 · esqueleto 2 · SEM_CORPUS 30 · portão aberto 18   (nos DOIS)
SUBIRAM 0 · CAÍRAM 0 · mudaram de ESTADO 0 · IDÊNTICAS 73 · md5 af4d7a2b… nas duas
```
🔴 **INFERÊNCIA, e é o que importa: a régua NÃO VÊ este defeito.** O corpus é de telas da **URA**;
o endereço com nome de lugar chega pelo **pin do segurado** — o outro lado da conversa. Nota estável
**não** prova que nada mudou: prova que a régua mediu outra coisa. Por isso o guarda próprio (§5.2).

### 5.5 A BATERIA — 3 rodadas, em ÁRVORES SEPARADAS

📊 `pytest tests -q`, ~1 h 05 cada. 🔴 **A lição operacional mais cara desta SPEC:** a bateria
contém guardas que **mutam `corridor_playbooks.py`** e restauram por cópia a cada ~10 s. Rodá-la na
árvore de trabalho **apagou dois conjuntos de edições de um builder em silêncio**, pôs uma mutação
num commit (desfeita em `d910613`) e me fez reportar uma "queda de 10 pontos" que **não existia**.
⛔ **Bateria e régua rodam em `git worktree` separado, nunca na árvore de trabalho.** → P-118-14.
📊 Linha de base do arquivo canônico está **vencida** (lista 35 nomes; o cabeçalho diz 47) — por isso
a triagem desta SPEC foi contra o **commit base num worktree**, não contra a lista.


## 6. Canário e rollout

🔴 **O canário NÃO rodou, e não podia rodar aqui:** exige um **pin de localização de verdade**,
mandado de um telefone para um número de teste. **O limite honesto:** os testes provam que o produto
**monta** a resposta inteira, pelo caminho e com o embrulho que a prova de 26/09 mostrou serem
aceitos; **não** que a Porto a aceite (P-118-04). Roteiro no bloco **J.2** de `TAREFAS-DO-FOUNDER.md`.
⛔ Nenhuma mensagem real enviada. Nenhuma variável tocada. Nenhum agente ligado.

---

## 7. Gate da SPEC

```
G1 ✅ prova do transporte em produção, com linha de controle — 📊 26/09 17:24, 200 × 479
G2 ✅ o caminho REAL usa a mesma rota e o mesmo embrulho — fixado por guarda (F1)
G3 ✅ o teste do fio verde, e provadamente vermelho antes (F4)
G4 ✅ nenhuma rota caiu — 📊 as duas rodadas saem IDÊNTICAS byte a byte (§5.4)
G6 ✅ mutação dos guardas NOVOS: os dois ficam vermelhos com o defeito reintroduzido
G8 ✅ a Azul declarada NÃO MAPEADA, com motivo e roteiro (P-118-01, P-118-02)
G9 ✅ a aba CORREDORES com a régua de HOJE — conteúdo em `painel-do-founder/`;
      ⛔ a republicação do artefato é do GERENTE, não desta fatia
G5 ✅ `conferir_o_que_esta_no_ar.py` rodado pelo gerente: **DIVERGE**, e é o esperado — o
      repositório está em `e108f1f7…` e a produção em `c4b896e6…`. **O trabalho não foi empurrado
      ainda**; é exatamente onde deve estar antes do gate. Vira ✅ depois do push + Implantar
G7 ✅ bateria em **3 rodadas**, em `git worktree` SEPARADOS (§5.5): base `70632a8`, HEAD antes e
      depois do conserto. 🔴 Triagem contra o **commit base**, não contra a lista canônica —
      ela está vencida (35 nomes; o cabeçalho diz 47). P-118-16 regrava a linha de base
```

⚠️ CLAUDE.md §9.1 (`test:rotas-montam` + `next start`) **não se aplica**: nada de `app/`,
`middleware.ts`, `next.config.js` ou variável de ambiente foi tocado — `backend/app/` é o cérebro
em Python, não a árvore de rotas do Next.

---

## 8. Mudanças além do texto da SPEC · 9. Decisões registradas

**Quatro adendas** em `CHANGE-ADDENDA.md` (26/09): a rede de segurança da restauração da régua · o
`R.` do §A · o `ref` fantasma visível no `/health` · e a asserção do `/health` que **nasceu frouxa**.
⛔ Nenhum escopo reduzido.

**Cinco decisões** em `FOUNDER-DECISIONS.md` (26/09), com opções e nota 0–100: **D-118-01** (a
finalização — a única que volta ao Founder) · **D-118-02** (`_STREET_RE` aqui, com a régua de
controle) · **D-118-03** (não regerar o corpus) · **D-118-04** (publicar hoje **e** declarar a
não-comparabilidade) · **D-118-05** (a rede de segurança).

---

## 9.9 A NOTA DA EXECUÇÃO

```
juiz fresco ........................  89/100   1 defeito real, 4 pendências, nenhum blocker
red team (cego ao juiz) ............  72/100   🔴 4 BLOCKERS da mesma família
confirmação curta (juiz novo) ......  91/100   "o conserto NÃO criou defeito" · 136 passed
```
🔴 **NOTA DA SPEC: 87/100.** Manda a menor leitura independente (72), corrigida pelo que o
conserto fechou: os 4 blockers reproduzidos, consertados, cada um VERMELHO sob mutação, e zero
defeito novo na confirmação. ⚠️ O que impede nota maior não é o conserto: é a **MAIOR LACUNA**,
declarada pelos dois julgadores — *"«o formato está certo» e «a Porto aceitou» são duas afirmações;
só a primeira está medida"*. O canário com pin real é do Founder.

📊 **Por que os DOIS papéis:** o juiz achou 1 defeito que o red team não viu; o red team achou 4
que o juiz não viu. **Nenhum dos dois, sozinho, fecharia esta SPEC com segurança.**

## 10. Riscos remanescentes e dívida assumida

1. 🔴 **A Porto aceita a resposta?** Não se mede sem seguradora do outro lado (P-118-04/05).
   **INFERÊNCIA:** *"o formato está certo"* e *"a seguradora aceitou"* são duas afirmações; só a 1ª
   está medida.
2. As notas descrevem o acervo de **16/09**; regerar o corpus move as 73 (P-118-08).
3. 7 rotas de Mapfre e Tokio saem `SEM_CORPUS` porque **nenhum acionamento delas chegou ao fim**
   (P-118-03) — não é falta de conversa: 📊 a Mapfre tem 572 textos de URA capturados.
4. Bradesco e Zurich **nunca entregaram protocolo** no acervo (P-118-09).
5. A régua **suja a árvore** quando a restauração falha (P-118-14): mitigada, não eliminada.

---

## 11. Impacto para o corretor

O segurado que pede um guincho pela Porto passa a ser atendido **do "oi" ao protocolo** sem que
ninguém da corretora toque no caso, respondendo o formulário com o endereço do próprio pin. Onde o
produto **não** consegue (Tokio, e toda tela nunca vista), ele para **entregando o caso a uma pessoa,
com tudo escrito** — em vez de ficar calado. 🔴 Nada disso chega à corretora antes do **Implantar**.

---

## 12. Estado do Master Plan

`ESTADO-DAS-SPECS.md` ganhou a linha **118**. ⚠️ O `EXECUTION-MASTER-PLAN.md` continua parando na
SPEC-062 — dívida antiga, já registrada no próprio `ESTADO-DAS-SPECS.md`.

---

## 13. ROLLBACK da SPEC inteira

```bash
git checkout main                       # a main segue em 70632a8; tudo está na branch
# se já tiver ido para a main, o intervalo é contíguo:
git revert --no-commit 70632a8..<commit final da 118> && git commit
```

⚠️ Nada de migration para desfazer, nada de variável para repor. O `/health` volta a **não** publicar
`finalize_refs_fantasma` — e o `ref` fantasma volta a ser invisível.

