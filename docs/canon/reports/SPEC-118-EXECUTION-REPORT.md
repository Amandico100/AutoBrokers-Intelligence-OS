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
GATES ......  §7          FAIXA ......  declarada 💭 4–7 h · real desta fatia: ≈ 3 h (20:31 → 21:35), das quais 53 min de régua em 3 rodadas completas

① PAINEL?   não — a conta do §3 não o pediu para uma fatia de documentos + um conserto de regex
            com régua antes/depois. A conta está escrita acima
② AUDITORIA EXTERNA?  juiz ‖ red team são do gerente, depois desta fatia
③ PENDÊNCIA por VALOR MARGINAL?  regerar o corpus (P-118-08): a régua teve de medir ANTES e
            DEPOIS com o MESMO corpus — ver D-118-03
```

---

## 0. Declaração de integridade

- [x] 🔴 **Nenhum motor paralelo.** O §A é **uma expressão regular** no reconhecedor que já existia;
      a trava do `/health` são **duas funções** ao lado do `finalize_live_for` que já existia — e a
      leitura da variável passou de uma para **uma**.
- [x] **Nenhuma migration** (a SPEC não tocou SQL) · nenhum DDL monolítico · nenhum segredo aqui.
- [x] Nenhum escopo reduzido sem decisão registrada · nenhum dado atravessou tenants.
- [x] `CLAUDE.md`, o protocolo e a SPEC foram lidos no início.
- [x] 🔴 **Nenhum nome de corretora, atendente, CPF ou telefone de pessoa** em código, teste ou
      fixture (§13.9/§13.3): as vias dos testes são públicas, com número `0` ou o da captura já
      mascarada.

---

## 1. Resumo executivo

**FATO.** Um acionamento pelo WhatsApp da Porto agora atravessa o formulário nativo — a telinha com
campos que a seguradora abre dentro da conversa — **sem parar e sem chamar uma pessoa**. 📊 Com o pin
de localização e **nada digitado**: `state=ready_to_send`, `missing_slots=[]`,
`montar_resposta_de_flow → ok=True` com as 10 chaves da captura real de 21/09/2026.

**FATO.** A premissa central da proposta estava **errada**, e quem a derrubou foi o comando. A SPEC
afirmava, por leitura do `swagger`, que `/send/interactiveResponse` **não existia** na imagem no ar, e
pedia um **rebuild** ao Founder. 📊 A prova em produção em 26/09 17:24, **com linha de controle**:

```
POST /api/whatsapp-integrations/prova-de-formulario
  tentativa 1 (CONTROLE, sem o embrulho) .... HTTP 500 · "server returned error 479"
  tentativa 2 (com DocumentWithCaption) ..... HTTP 200 · ACEITO
→ servidor: Type: "InteractiveResponseMessage" · ID 3EB02C9B1BFC57E46E3136
```

⛔ **Não houve rebuild.** O `swagger` lista 88 rotas e nenhuma com `interactive` porque o patch `0005`
não anotou — **catálogo incompleto não é ausência** (protocolo §0.4). **P-62**, que repetia o pedido,
foi fechada com essa medição e movida para `PENDENCIAS-FECHADAS.md`.

**FATO.** A **Tokio** deixou de fingir que atende: 📊 52% das sessões dela terminam num link, não num
protocolo — o caso vai a uma pessoa **com dossiê**. E ali havia um defeito grave: o handoff era
**inalcançável** (`match_ura_step` precedia `detect_handoff_trigger`), então o segurado era
**abandonado** até o vigia perceber, nunca passado a uma pessoa.

**FATO.** A régua das 73 rotas rodou **duas vezes** nesta fatia, antes e depois do único conserto de
produto que ela fez. É essa comparação que dá direito às conclusões do §5.4.

---

## 2. Escopo executado, por fatia

```
F1  o TRANSPORTE   virou GUARDA, não conserto: fixa `/send/interactiveResponse` + envelope
                   `galaxy_message` + embrulho `DocumentWithCaptionMessage` OBRIGATÓRIO. A
                   docstring vencida de `evolution_go.py` saiu (§9.3)
F2  os MAPAS       `native_flows` da Porto das 3 capturas com schema, cada uma com bloco `observed`
                   apontando a linha do acervo; o flow de pesquisa marcado NÃO-RESPONDÍVEL
F2b o PORTÃO       o montador responde campo de TEXTO; o portão de coleta soma os campos
                   obrigatórios dos formulários que AQUELE subserviço abre; a Tokio vira handoff
                   com dossiê (📊 129 telas, 9 casam a âncora, 0 divergências)
F3  o AGENTE PEDE  uma informação por vez, em português, ENSINANDO a mandar o pin; formulário sem
                   fonte vira handoff COM MOTIVO, nunca silêncio
F4  a COSTURA      o TESTE DO FIO (⑤→⑭, motor real), que NASCEU VERMELHO; a coordenada ganha FONTE
                   (o pin), e `latitude='0'` deixa de fechar o formulário
F5  esta fatia     a régua antes/depois, `_STREET_RE`, a trava do `ref` fantasma, o inventário
                   regenerado, a aba CORREDORES e os seis documentos canônicos
```

---

## 3. Arquivos alterados nesta fatia (F5)

```
app/services/corridor_playbooks.py        `_STREET_RE` reconhece `R.`  (§A)
app/services/insurer_dispatch_service.py  refs_de_finalizacao_declarados() + ..._sem_corredor()
app/main.py                               /health publica finalize_refs_fantasma (None, nunca
                                          [], no caminho de erro)
scripts/verificar_mutacoes.py             a restauração deixa de desistir
tests/test_o_endereco_do_pin_reconhece_a_abreviacao.py  NOVO · 6 asserções, 4 controle
tests/test_a_lista_de_finalizacao_nao_tem_fantasma.py   NOVO · 7 asserções, 4 controle
docs/canon/reports/INVENTARIO-DE-ROTAS.md               regenerado
docs/canon/reports/SPEC-118-REGUA-ANTES-E-DEPOIS.md     NOVO · a régua e as mutações
docs/canon/painel-do-founder/aba-corredores.html        deixa de ser a foto de 24/08
docs/canon/{PENDENCIAS,PENDENCIAS-FECHADAS,FOUNDER-DECISIONS,TAREFAS-DO-FOUNDER,
            CHANGE-ADDENDA,ESTADO-DAS-SPECS}.md         §8 e §9
```

---

## 4. Migrations

**N/A — nenhuma.** 📊 Esta SPEC não tocou SQL em nenhuma fatia. Não há APPLY, VERIFY nem ROLLBACK a
escrever porque não há nada aplicado.

---

## 5. Testes executados — com saída real

### 5.1 O gate da SPEC

```
$ cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/test_o_fio_do_acionamento_atravessa_o_formulario.py     tests/test_o_agente_pede_antes_de_acionar.py tests/test_o_montador_responde_texto_e_o_portao_cobra_antes.py     tests/test_o_mapa_da_porto_veio_do_acervo.py tests/test_o_transporte_do_formulario_e_conferido.py     tests/test_a_lista_de_finalizacao_nao_tem_fantasma.py -q
74 passed, 13 warnings in 68.46s (0:01:08)
```

⚠️ `PYTHONIOENCODING=utf-8` **sempre**: sem ele os guardas-script morrem em cp1252 **e devolvem
exit 0** — falso verde.

### 5.2 O guarda do §A — **nasceu vermelho**, com as linhas de controle verdes

📊 ANTES do conserto, no HEAD `b897ac7`: `2 failed, 11 passed in 8.65s` —

```
AssertionError: o ponto de referencia do pin virou a rua:
  {'rua': 'Posto Shell', 'bairro': 'R. Rafael Bandeira', 'cidade': 'Florianopolis', ...}
```

📊 DEPOIS: `6 passed in 4.53s`.

🔴 **É a prova exigida pelo CLAUDE.md §9.5:** o guarda **fica vermelho** com o defeito histórico
presente — não foi escrito depois do conserto para carimbá-lo. E as 4 linhas de controle (a mesma
via por extenso · `Dr.`/`Sr.` que **não** são logradouro · endereço sem ponto de referência · a
rodovia com caminho próprio) estavam **verdes nas duas rodadas**: o mérito é do fator que mudou.

### 5.3 O guarda do `ref` fantasma — `7 passed in 4.40s`

🔴 **A mutação pegou um guarda que não tinha como falhar**, e foi um guarda *meu*: com a asserção
sobre a **chave** `sinais["finalize_refs_fantasma"]`, apagar a linha que a **calcula** deixava o teste
verde (`7 passed`), porque o caminho de erro escreve a mesma chave. Reescrita sobre a **atribuição que
chama o motor**: a mesma mutação dá `1 failed, 6 passed`; restaurado, `7 passed`. Detalhe e saídas no
companheiro. CLAUDE.md §9.3.

### 5.4 🔴 A RÉGUA COMPLETA, ANTES E DEPOIS — o controle do conserto do §A

📊 Duas rodadas de `python scripts/medir_rota.py --todas --formato tabela`, de dentro de `backend/`,
com o **mesmo corpus** e a árvore **sozinha**. Nominal completo em
`docs/canon/reports/SPEC-118-REGUA-ANTES-E-DEPOIS.md`.

```
ANTES  b897ac7 (HEAD limpo) 18m24s     DEPOIS  a arvore que virou 125a024  16m45s
AAA 0 · quase 26 · parcial 15 · esqueleto 2 · SEM_CORPUS 30 · com portão aberto 18   (nos DOIS)
SUBIRAM 0 · CAIRAM 0 · mudaram de ESTADO 0 · IDÊNTICAS 73
```

🔴 **E o resultado é mais forte do que "nenhuma caiu": as duas saídas são idênticas byte a byte.**

```
$ diff regua_ANTES_F5.txt regua_DEPOIS_F5.txt      (sem saída)
af4d7a2bed6fd0a152b71cf3527913fa *regua_ANTES_F5.txt
af4d7a2bed6fd0a152b71cf3527913fa *regua_DEPOIS_F5.txt
```

**INFERÊNCIA, e é a parte que importa: a régua NÃO VÊ este defeito.** O corpus versionado é de telas
da **URA da seguradora**; o endereço com nome de lugar chega pelo **pin do segurado**, que é o outro
lado da conversa. Nota estável aqui **não** prova que nada mudou — prova que a régua mediu outra
coisa. ⚠️ É por isso que o conserto tem guarda **próprio**, que nasceu **vermelho** (§5.2): um número
que não mexe é compatível com *"consertou"* **e** com *"não fez nada"*.

⚠️ **O outro limite:** o corpus é o de **16/09/2026**; regerar move as 73 notas e ficou fora de
propósito (P-118-08, D-118-03). 🔴 O comparador **consegue** acusar queda — provado com linha de
controle no companheiro (CLAUDE.md §9.3).


---

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
G5 ⏭️ `conferir_o_que_esta_no_ar.py` NÃO rodado: fala com o serviço no ar, e esta fatia não
      toca produção. É pré-condição do Implantar (bloco J.1)
G7 ⏭️ a bateria triada nominalmente é do gerente, depois da costura das cinco fatias
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

