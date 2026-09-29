# SPEC-120 — Os dezesseis corredores atendem sozinhos

> Relatório de execução · 29/09/2026 · rito AAA v13 · branch `spec/119-corredores-prontos`
> commit inicial `ff5a52b` · commit final: ver §2 · SPEC `specs-propostas/SPEC-120-os-dezesseis-corredores-atendem-sozinhos.md`

## 0. O EXECUTION CARD

```
OUTCOME ........  os 16 corredores que TÊM conversa gravada passam a atender de ponta a ponta
                  sem humano — e o de 24 sobe para o máximo que a evidência permitir
RISCO ..........  9  (ALCANCE o SEGURADO 3 · REVERSIBILIDADE a resposta vai à SEGURADORA 3 ·
                  FREQUÊNCIA 3)
SUPERFÍCIE .....  2  (10 corredores com tela órfã, 4 playbooks residenciais, 3 montadores de dossiê)
PISO APLICADO ..  §3.2 — toda resposta nova SAI para a seguradora → CRÍTICO
NÍVEL ..........  🔴 CRÍTICO · builder Opus 5.5 xhigh · juiz ‖ red team cegos · 1 conserto
O FIO ..........  §2 da SPEC
PARALELISMO ....  F1+F2+F3 (corredores, um dono) ‖ F4 (o grupo, gerente) → F5 (medição)
UNIDADES .......  5 fatias
COESÃO .........  as respostas das telas e a política da tela desconhecida são o mesmo domínio
TIME ...........  1 builder dos corredores (dono único de corridor_playbooks.py) · gerente na F4
REFERÊNCIA .....  interna: as 67 respostas HUMANAS achadas no banco · externa: CLAUDE.md §9.5
GATES ..........  G1–G9, §4 abaixo
O ELO ..........  "as telas sem resposta já FORAM respondidas, e a resposta está no banco" —
                  📊 67 de 86 (§1 da SPEC); e B chega em A: 76 das 86 viraram passo (§1 abaixo)
FAIXA DE RELÓGIO  💭 sem teto do Founder; ≈ 1 dia de relógio, SPEC-119 e 120 no mesmo chat
nota da execução  86/100 (§9)
```

## 1. O QUE MUDOU PARA O CORRETOR E PARA O SEGURADO

### 1.1 Sete rotas passaram a atender sozinhas
📊 `python scripts/simular_corredor.py --todas --formato json`, commit `b800117`, 29/09/2026:

```
                    antes (ff5a52b)   depois (b800117)
ATENDE SOZINHO            24                31
VAI PARA UMA PESSOA        2                 2
FALTA CAPTURA             47                40
```

Entraram: `allianz/residencial/encanador` · `allianz/residencial/maquina_de_lavar` · `azul/auto/guincho` ·
`bradesco/auto/guincho` · `hdi/auto/guincho` · `hdi/residencial/encanador` · `porto/auto/guincho`.
📊 Telas órfãs nas 10 rotas trabalhadas: **86 → 10**. As 10 que ficaram são **declaradas**, não esquecidas:
5 são uma consultora da Porto conversando (P-120-04), 2 são telas de chaveiro numa sessão de guincho da
Yelum (P-120-05), 3 são o menu de outro ramo na HDI eletricista.

As respostas vêm das decisões do Founder (§3 da SPEC, D1–D17): garagem e período **perguntados** ao
segurado; blindado, câmbio e animal → Não; desatrelado e rodas livres → Sim; primeira data disponível;
táxi além do guincho **perguntado** (só Porto); amperes pela **tabela de porte**, 60 Ah por padrão, em
qualquer formato de tela, **nunca** trava nem chama pessoa.

📊 **A régua das 73 rotas** (`medir_rota.py --todas --gravar-notas`, worktree `-f5`, 29/09 00:35 → 01:04),
comparada ao retrato versionado anterior — **8 rotas subiram, nenhuma caiu** (é o controle de que o conserto não
derrubou ninguém):

```
allianz/residencial/encanador         55% parcial   → 87% quase
allianz/residencial/maquina_de_lavar  76% parcial   → 95% quase
azul/auto/guincho                     76% parcial   → 95% quase
bradesco/auto/guincho                 41% esqueleto → 72% parcial
hdi/auto/guincho                      63% parcial   → 95% quase
hdi/residencial/encanador             68% parcial   → 95% quase
porto/auto/guincho                    63% parcial   → 95% quase
yelum/auto/guincho                    63% parcial   → 68% parcial
```

### 1.2 O que o juiz e o red team pegaram, e que teria chegado à seguradora
Consertado no único conserto (`f4028d8`), cada um provado pelo motor nas telas reais (`61485f7`):

| | antes | depois |
|---|---|---|
| a recusa virava "Sim" (*"claro que não"*, *"quero não"*, *"pode deixar"*) no táxi e na garagem | táxi pedido para quem recusou | "Não"; dúvida vai a uma pessoa |
| a tela da Porto que só AVISA o preço da bateria recebia "60" | resposta colada na pergunta seguinte | nenhuma resposta |
| o destino da Bradesco saía com a rua da ORIGEM, e a conferência não comparava o destino | guincho levado ao lugar errado | a rua do destino; a conferência compara origem **e** destino |
| o número da origem ia como número do destino (HDI/Yelum) | idem | decide por *"para onde levar"* já respondido |
| "chamou a polícia?" respondia "Não" num relato de acidente (Bradesco) | sinistro seguindo como assistência | só pane mecânica nomeada recebe "Não"; o resto vai a uma pessoa |

### 1.3 O grupo de suporte: um aviso só, na hora, completo
- **O vigia parou de cobrar o grupo** sobre conversa antiga (`a633f92`) — o print de 244h é impossível por
  construção. Ele só tenta de novo um **primeiro** aviso que **nunca saiu**, em caso de até 2h (`bf18e8f`).
- **O dossiê sai inteiro e clicável**, sem máscara (ordem do Founder): nome, CPF/CNPJ, seguradora, WhatsApp
  `wa.me`, **data, hora e momento** (conversa inicial · acionamento · pós-acionamento) (`15bf83f`, `63e3ce0`).
- **O ✅ de conclusão diz o quê**: serviço, seguradora e protocolo (`42200d9`).
- **O resumo das 19h lista as assistências abertas no dia** — nome, serviço, seguradora, protocolo e
  WhatsApp — anotadas quando o **protocolo** existe, não quando o caso fecha (`8c46b6d`).
- **Com humano atendendo, nada sai ao grupo** (D17): os 12 remetentes passam pela mesma porta.
- Número estrangeiro não vira o WhatsApp de outra pessoa (`1181980`).

## 2. COMMITS E ARQUIVOS

📊 `git log --oneline ff5a52b..HEAD` → 26 commits de produto e teste + os documentos desta entrega.
Arquivos de produto: `app/services/corridor_playbooks.py` · `app/agents/tools/insurer_dispatch_tool.py` ·
`app/services/attendance_ficha.py` · `app/services/insurer_dispatch_service.py` ·
`app/agents/tools/human_handoff.py` · `app/tasks/handoff_watchdog.py` · `app/services/dispatch_router.py` ·
`app/services/o_fim_do_atendimento.py` · `app/services/os_modelos_do_grupo.py`.
Testes novos: `test_os_dezesseis_corredores_atendem_sozinhos.py` · `test_o_grupo_recebe_o_caso_inteiro.py`.
Migrados (CLAUDE.md §9.3): 11 arquivos de teste, cada um com o porquê escrito ao lado.
Script: `backend/scripts/pagina_dos_corredores.py` — o guarda do §13.9 lia o hash `ecb701e` como a palavra `ecb`; hash hexadecimal **com dígito** sai antes de fatiar (nome de gente não tem dígito), e as 4 mutações do guarda continuam vermelhas.
📊 **ZERO migration.**

⚠️ **Histórico reescrito antes de subir:** o primeiro `reports/TELAS-SEM-RESPOSTA-DOS-16.json` guardava a
resposta crua da atendente (placa, rua, nome). Os commits ainda não empurrados foram reescritos com a versão
limpa (D-120-K) — por isso os hashes acima de `ff5a52b` no remoto diferem dos citados nos laudos.

## 3. OS TESTES, COM SAÍDA REAL

### 3.1 A bateria completa — em worktree separado, triada contra o commit base
📊 Uma rodada da bateria completa, worktree `AutoBrokers-FIX-mut` em `b800117` (= `ecb701e` depois da
reescrita, mesmo código), 29/09/2026 00:35 → 01:44, `python -m pytest tests -q -p no:warnings`:

```
43 failed, 2252 passed, 1 skipped, 32 xfailed, 1 xpassed in 4132.35s (1:08:52)
```

Triagem contra a lista de falhas da base (52 linhas, rodada completa de 28/09):
- **42 das 43 já falhavam na base.** Entre elas as 4 de `test_spec031_finalize_v2` (nova tentativa ×3 e o
  analista do residencial — falham em `0c0e070`, antes de qualquer código desta SPEC) e as de
  `test_o_caso_se_explica_sozinho`.
- **10 que falhavam na base agora passam** — entre elas `test_a_regua_pontua_e_nao_bate_no_portao`,
  `test_a_orfa_que_a_spec_nomeia_foi_MAPEADA…` e 5 guardas-script (`test_a_atendente_na_ura_cala_o_robo`,
  `test_a_cobranca_prova_que_funciona`, `test_o_atendente_alcanca_o_portal_de_vidros`,
  `test_o_vocabulario_viaja_na_imagem`, `test_os_numeros_da_casa_nao_atravessam_corretoras`).
- **1 nova: `test_todos_os_guardas_script_rodam.py::test_a_arvore_ficou_limpa_no_fim`** — *"a sessão TERMINOU
  com rubrica.py diferente do início"*. `rubrica.py` é mutado de propósito pela entrada C17 de
  `test_a_regua_nao_tem_furo`; nem ele nem o harness foram tocados por esta SPEC
  (`git diff --stat ff5a52b HEAD -- backend/scripts/rubrica.py backend/tests/test_todos_os_guardas_script_rodam.py` → vazio),
  e o próprio teste restaurou o arquivo. ⚠️ A régua das 73 rotas rodava **ao mesmo tempo** em outro worktree
  (disputa de CPU). Linha de controle — o arquivo de guardas sozinho, máquina livre, HEAD final:

```
HEAD 41bcab8 (máquina livre)   13 failed, 297 passed · 25:53 · "TERMINOU com higiene_do_corpus.py diferente"
BASE ff5a52b (máquina livre)   18 failed, 292 passed · 30:25 · "TERMINOU com rubrica.py diferente"
```

  🔴 O controle **não** absolveu a disputa de CPU — a falha voltou com a máquina livre —, mas **a base falha
  igual**: o vazamento é anterior a esta SPEC, e o arquivo sujo muda de rodada para rodada (`rubrica.py`,
  `higiene_do_corpus.py`), que é a assinatura de uma mutação cortada pelo teto de 120 s. Esta SPEC deixou o
  arquivo de guardas com **5 falhas a menos** que a base. Vira **P-120-20**.



### 3.2 As mutações
📊 Worktree `mut-e001`, controle 178 passed; **16 de 16 mutações vermelhas** nos corredores, entre elas as do
red team (RT-M3, RT-M3b, RT-M5) e a do juiz (JZ-M1, que o guarda `ALCANCE` pegou: cada um dos 38 passos
novos tem congelado o conjunto de sessões que casa; o dos amperes casa exatamente `porto-auto:4830574a`).
No grupo: 4 de 4 vermelhas (`M-G1a` fase de encerramento · `M-G1b` sem trava por sessão · `M-G1c` lista sem
conversa · `M-G1d` lista repetida).

### 3.3 Os guardas do gerente
📊 `test_o_grupo_recebe_o_caso_inteiro.py` 17 passed · `test_o_grupo_so_e_chamado_quando_alguem_espera.py`
16/0 (inclui a seção 4b, com linha de CONTROLE: a mesma conversa com 3h só é medida).

## 4. OS GATES

| gate | resultado |
|---|---|
| G1 zero órfãs funcionais nas 10 rotas | ⚠️ **86 → 10, não zero** — as 10 são declaradas (P-120-04, P-120-05, menu de outro ramo) |
| G2 residenciais tentam; a tela que decide vai a uma pessoa | ✅ allianz e hdi residencial encanador atendem sozinhos; condomínio/empresarial/sinistro com controle |
| G3 amperes nunca trava | ✅ guarda vermelho com pausa ou handoff na tela; ⚠️ a tela **com preço** vai a pessoa (D-120-C) |
| G4 constante nova justificada pelo rótulo da tela | ✅ |
| G5 as oito respostas erradas de 22/08 continuam vermelhas | ✅ 240 passed nas suítes relacionadas |
| G6 mutação de cada guarda novo | ✅ 16/16 + 4/4 |
| G7 bateria em worktree separado | ✅ 1 rodada completa + 2 de controle; 42/43 já falhavam na base, a 43ª falha igual na base (§3.1) |
| G8 o dossiê diz o MOMENTO | ✅ · a metade "lembrete leva seguradora + serviço" **caiu com a D16**: não há mais lembrete |
| G9 o simulador mede | ✅ 📊 24 → 31 |

## 5. JUIZ ‖ RED TEAM

📊 Sobre `441fb60`, cegos um ao outro: **juiz 66/100**, **red team 55/100**. Juntos, 5 blockers e 4 graves
nos corredores + G1 (a assistência nascia no fechamento) e o achado da rede de segurança do vigia no grupo.
Todos consertados, exceto a rajada preço + "Posso continuar?" da Porto (pré-existente, D-120-B).

📊 **Confirmação curta do juiz** sobre `b800117`: **82/100** (era 66). Blocker 1 (avisos respondidos) e blocker 2
(número do destino) **fechados pelo motor na tela real**, com base e HEAD lado a lado; as mutações dele M-A e M-B
ficaram vermelhas. A condição que ele pôs — o JSON cru fora do histórico **antes** do push, *"senão a nota volta
para 74"* — foi cumprida (§2, D-120-K). Os dois resíduos menores que ele achou: o vigia insistia a cada 10 min
quando a porta calava por humano (consertado em `376fe9a`, com guarda que fica vermelho sem o conserto) e o
reinício da URA dentro da sessão (P-120-19).

## 6. O QUE FICOU FORA, E O QUE CUSTA ESQUECER

Tudo em `PENDENCIAS.md`, P-120-01 a P-120-20. Os que o Founder precisa ver:
- **carro reserva** (P-120-01) — 126 telas, zero passos; a próxima SPEC.
- **seis rotas sem desfecho** (P-120-02) — um acionamento real de cada.
- **31 rotas sem conversa** (P-120-03).
- **a consultora da Porto no meio da URA** (P-120-04) e **a tela de limite da Yelum** (P-120-06).
- ⚠️ **§13.9 pré-existente**: nome de funcionária da seguradora no acervo (P-120-12) e o número de teste do
  canário em 8 testes (P-120-13).

## 7. CANÁRIO E RISCOS REMANESCENTES

Canário **não rodou**: nenhuma mensagem saiu para seguradora nem para grupo nesta SPEC. Depende do Implantar
do Founder. Riscos: a janela de 6h do "humano assumiu" (P-120-14); aviso tardio duplicado com Redis fora
(P-120-15); B3/B4 dependem de o passo-sinal ter sido enviado.

## 8. DECLARAÇÃO DE MOTOR PARALELO

Nenhum motor paralelo foi criado. Os passos novos moram em `corridor_playbooks.py` e são executados pelo motor
que já existia (`match_ura_step` / `render_reply`); o grupo continua com **uma** porta (`enviar_ao_grupo`); a
lista das 19h lê `work_events`, que já existia.

## 9. A NOTA DA EXECUÇÃO — 86/100

| dimensão | peso | nota |
|---|---:|---:|
| outcome medido (24 → 31) | 40 | 34 — G1 ficou em 10, não zero |
| respostas certas (§9.5, as duas perguntas) | 25 | 21 — 5 blockers achados e mortos; D-120-B aberta |
| honestidade e registro | 15 | 13 — duas afirmações erradas ao Founder corrigidas no chat; PII achada e tirada do histórico |
| guardas que ficam vermelhos | 10 | 10 — 20/20 |
| PII · §7 · §13.9 | 10 | 8 — o JSON limpo; pré-existentes registrados, não consertados |
