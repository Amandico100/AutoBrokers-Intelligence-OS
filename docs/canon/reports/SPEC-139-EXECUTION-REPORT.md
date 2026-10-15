# Relatório de execução — SPEC-139: a loja de aplicativos — capas feitas em código e todo aplicativo com a mesma casa

**SPEC:** `docs/canon/specs/SPEC-139-a-loja-de-aplicativos.md` · 2ª de duas no mesmo chat (a 1ª foi a 131-0-B2)
**Branch:** `spec/139-a-loja-de-aplicativos` · **base** `4a08ce4` (= `origin/main` depois do push da B2) · **último commit** `dbd6da1`
**Gerente:** Opus 5.5 · protocolo AAA v13 · nível CRÍTICO (o Configurar da Cobrança governa envio real a segurado) · todos os subagentes `claude-opus-5-5` (§11)
**Estado final:** **CONCLUÍDA** · código pronto, nada no ar até o Implantar do `smith-web` (T-183, depois da T-174) · as 2 migrations de conteúdo JÁ estão no banco

## 0.0 EXECUTION CARD
```
OUTCOME ........ o corretor abre Aplicativos e vê uma loja com cara de loja: cada aplicativo com capa própria, do mesmo sistema
                 visual, no claro e no escuro; QUALQUER aplicativo abre na mesma casa (Início · Configurar · o trabalho · Dúvidas).
                 A Cobrança sai do modal para essa casa sem mudar UMA regra de envio; Checklist das 6h, Follow-up e Resumo ganham a
                 aba do trabalho; os sem trabalho dizem "Em breve" sem botão Ligar; as rotas de Personalização (EXTRA-001.9) no lugar.
RISCO .......... 6 (segurado 3: a Cobrança envia de verdade · reversível 2 · todo uso 1)
SUPERFÍCIE ..... 2 (refazer a capa que existe + mover telas que funcionam)
PISO APLICADO .. CRÍTICO: config que governa envio real · rotas novas e redirects em app/ (§9.1) · migration de catálogo
NÍVEL .......... CRÍTICO · builders Opus 5.5 · juiz ‖ red team ‖ juiz de design (capturas, 390/1440, 2 temas) · conserto · confirmação
O FIO .......... /dashboard/auxiliares → AuxiliaresClient → CardDoAplicativo → CapaGerada(slug → paleta + composição SVG; cover_url vence)
                 → [slug]?aba=configurar → ABAS_DO_APLICATIVO['cobranca-feita'] → o formulário EXTRAÍDO → a MESMA rota de gravação
                 (corpo idêntico) → ?aba=cobrancas → leitura de billing_sent_log só da corretora · endereços antigos → 307 → ?aba=
UNIDADES ....... L1 capas · L2 Cobrança · L3 telas no lugar (P-16) · L4 casca para todos + migration · L5 EXTRA-001.9 · L6 costura + design
COESÃO ......... o MESMO CapaGerada; UM formulário (modal e aba, o mesmo hook); redirect = page.tsx antiga
PARALELISMO REAL L1 ‖ L2 ‖ L3 ‖ L4 ‖ L5 em worktrees próprios (arquivos disjuntos) → L6 costura
TIME ........... 5 builders · costura · juiz ‖ red team ‖ design · conserto A ‖ B · confirmação · design R2 · conserto 2 · R3 · bateria
REFERÊNCIA ..... interna: a casca da 131-B, laudo DESIGN-DO-PADRAO §2–§6; externa: as 5 da SPEC §8 — o juiz de design NÃO as abriu
GATES .......... fio · dourado do corpo da Cobrança · guarda de links · rotas-montam + next build + next start + requisições · tsc ·
                 6 mutações · 2 corretoras · design ≥ 90 · bateria
O ELO .......... "a Cobrança não mudou PORQUE o Configurar novo grava o MESMO corpo" → 📊 MEDIDO: S1–S7 hash idêntico ao modal de
                 5f9bdac; 10/10 entradas digitadas = corpo do modal antigo (depois do conserto A)
FAIXA DE RELÓGIO declarada 💭 6–8 h · real 📊 L1 15/10 04:51 → bateria ~18:30 UTC (≈ 13 h 40 de relógio, dividido com a B2 até o push
                 dela às ~12:10; ≈ 6 h 30 só da 139). Por que passou: next build 📊 47 min e a bateria 📊 2 h 57 (agente)
```
① painel de lentes: não (juiz ‖ red team ‖ design pedidos pela SPEC). ② auditoria externa: os três frescos + confirmação 88 + design R2 89
e R3 92, todos frescos. ③ pendência por valor marginal: P-139-08 (código morto), P-139-12 (pílula encosta no anel).

## 0.1 O protocolo — o laço, rebaixamentos, drenagem
**O laço:** 1 volta de código (conserto A ‖ B → confirmação 88, saída "só pendências") + 2 voltas de design (83 → 89 → 92). **Rebaixamentos
pelo gerente:** nenhum. **Promoveu** o harness `/embed/loja` (P1 do red team, "BLOCKER se chegar à main") a guarda: apagado em `0447bd5` e
`scripts/o-harness-de-design-nao-vai-ao-ar.test.mjs` (`6415078`, 📊 2 vermelhos com a pasta, 2 verdes sem).
**Pendências que a SPEC tocou:** P-16 ✅ FECHADA · P-131B-15 🟡 PARCIAL · P-131B-03/-04/-05/-14 🟡 CONTINUAM (detalhe em `PENDENCIAS.md`,
"A drenagem das pendências que a SPEC-139 tocou").

## 1. Resumo executivo (FATO)
- **As capas:** o MESMO `CapaGerada.tsx` passou a desenhar uma composição SVG em código (`capas/composicoes.ts`, `paleta.ts`,
  `icones-svg.ts` gerado do lucide); sem texto, emoji ou imagem externa; `cover_url` vence. Direção do produto **C · Cena** (escolha do
  Founder, 15/10). 18 capas na grade (a `renovacao-maxima` saiu da vitrine e herda a da Renovação).
- **A Cobrança na casca:** Início · Configurar (o formulário EXTRAÍDO do `PainelDeRotinas`, mesmo hook, mesma rota) · Cobranças (rota
  nova só leitura `app/api/dashboard/auxiliaries/cobranca/enviadas`, `company_id` da sessão, nome mascarado, 4 dígitos do telefone) · Dúvidas.
- **As telas no lugar (P-16):** Checklist das 6h → aba Hoje; Follow-up → aba Follow-ups; Resumo → aba Resumos. Conteúdo MOVIDO; os
  endereços antigos são `redirect()` de 1 salto.
- **A casca para todos:** "Em breve" sem Ligar, com Início honesto e Dúvidas; Follow-up e Resumo sem aba Configurar (D-139-L4-02).
- **EXTRA-001.9:** `personalizacao/{agentes/even,equipe,conhecimento,custos}` → `personalizacao/corretora/…` com redirect; menu; guarda
  `scripts/links-internos-casam-rotas.test.mjs`; "Even" fora da Prontidão.
- **Catálogo** (2 migrations, só texto global): Dúvidas para 15 aplicativos, frases de gente, 3 Dúvidas falsas corrigidas.

## 2. Escopo (FATO — commits)
📊 `git rev-list --count 4a08ce4..dbd6da1` → **141** · `git diff --shortstat 4a08ce4 dbd6da1` → **89 arquivos, +8.538 / −3.119**.
L1 11 · L2 15 · L3 9 · L4 6 · L5 22 (cherry-picados sem conflito de worktrees nascidos em `5f9bdac`) · L6 32 (costura, prancha, fio) ·
conserto A 17 (`b0b074c..c7a25fb`) · conserto B 13 (`2106f02..dc6b652` → `4b918e3`; prancha "Escolhida pelo Founder: C" `a21c6ba`) ·
conserto de design 2 12 (`a114532..8e6da83`) · harness fora `0447bd5` · guarda do harness `6415078` · guarda vencido `dbd6da1`.
**Achado:** um builder escreveu por engano na árvore principal (um `page.tsx` idêntico ao da L5 — descartado; um teste VAZIO de 0 bytes
— apagado); nada entrou no push da B2 (commits por arquivo).

## 2.1 Preflight (colado do gerente)
```
depois do push da B2: origin/main 4a08ce4 · branch spec/139-a-loja-de-aplicativos criada da origin/main · HEAD..origin/main = 0 ·
origin/main..HEAD = 0 · status: só os resíduos antigos não relacionados (.claude/hooks/teto-de-agentes.py M; 3 docs D; app/app/,
app/backend/, portal_worker/, tests/, docs soltos ??)
```

## 2.2 BLOCO 0 (📊 15/10, banco só leitura)
| # | medido | o que mudou |
|---|---|---|
| B1 | Cobrança: 17 `routine_runs` numa corretora, a última 11/09, instalada em 2 (pausadas) · Checklist: `briefing_publications` 92/91/91 em 3 corretoras, a última 14/10 · Follow-up 1 e Resumo 3 `auxiliary_runs` (junho) · Radar e tarefas-agendadas 0 trabalho (mas têm motor) · 9 `coming_soon` | as 4 com trabalho ganham aba; Radar e tarefas-agendadas NÃO viram "Em breve" (D-139-L4-01) |
| B2 | o modal grava `POST /api/dashboard/rotinas` com `action,id,auxiliar,name,instructions,knowledge,schedule,delivery,config` (`PainelDeRotinas.tsx@5f9bdac:583-610`) | vira o dourado do ELO |
| B3 | a fonte do que saiu é `billing_sent_log` (📊 0 linhas hoje) | rota nova só leitura |
| B4 | `personalizacao/corretora/` já existia; `app/dashboard/corretora` não | destino da 001.9 |
| B5 | o `lucide-react` 0.446 NÃO exporta `iconNode` | os 19 ícones extraídos por script para `capas/icones-svg.ts` (gerado, comando no cabeçalho) |

## 3. A prancha e a escolha do Founder
Publicada como página privada https://claude.ai/artifact/XSqfwGfcQZ54sftSUvq7eq (v1 com A/B/C; v2 "Escolhida: A · Placa"; v3 "Escolhida
pelo Founder: C"). Notas do builder: A 90 → 92 depois do polimento · C 88 · B 86. Sem resposta, o gerente tomou a A (D-139-03). **Em 15/10
o Founder escreveu "Eu escolho a opção C"** → D-139-07 (C · Cena, nota 85 × manter a A 70; trocar = a linha `DIRECAO_DO_PRODUTO` em
`composicoes.ts`); o conserto B adaptou à C. T-177 FECHADA. Bytes por capa 📊 (`capas.test.mjs` no HEAD): A 4.651–5.045 · B 3.798–4.407 ·
C card 5.338–5.970 · C cabeçalho 6.117–6.664 · C destaque 6.160–6.677 — teto 8.192 (D-139-L1-01). Matizes 📊: os 9 com capa a 24° dois a
dois; as 18 a 20° nas distâncias 1–4 das grades de 2/3/4 colunas (regra ≥ 18°); ≤ 5 no ciano; controle com a paleta de antes VERMELHO.

## 4. Migrations (APLICADAS pelo gerente: psycopg, transação, registro em `supabase_migrations.schema_migrations`)
| campo | `20261016_01_spec139_conteudo_dos_aplicativos.sql` | `20261016_02_spec139_a_duvida_da_cobranca.sql` |
|---|---|---|
| sha256[0:16] · versão | 📊 `d78f271281279019` · `20261015122333` | 📊 `e227e37a8d36a7d9` · `20261015142645` |
| APPLY | só UPDATE de texto global em `auxiliary_templates`: `faq` dos 15 sem dúvida (só onde vazio), frases de máquina, "o que falta" dos 9 "Em breve"; não toca `catalog_state` | só `faq` de 3 linhas, cada UPDATE guardado pelo md5 do texto antigo: Cobrança por MODO de envio e sem seguradora cravada; Checklist (horário do Configurar, padrão 8h; sem "três itens"; sem "canal que escolher"); Radar (SUSEP diária, CNSP semanal) |
| VERIFY | 📊 `(1,0,0,0,0,9,9)` = 1 ativo sem dúvida (só `quem-cobra-menos`) · 0 frases de máquina · 0 "faz" em texto solto · 0 dúvida malformada · 0 promessa sem acento · 9 disponíveis · 9 em breve (juiz reconferiu) | antes 📊 `(1,1,1,1,5,4,3,0)` → depois `(0,0,0,0,5,4,3,0)` (confirmação reconferiu; 📊 só 3 linhas com `updated_at` novo) |
| ROLLBACK | no arquivo, os textos de 15/10 LITERAIS | no arquivo, os 3 `faq` de antes LITERAIS |
| expand-first / destrutiva | sim / não | sim / não |

⚠️ O conteúdo já vale para a tela de produção de hoje (o banco é um só); nenhuma regra, coluna ou corretora mudou. O par arquivo→versão
está registrado em `MIGRATIONS-AUTHORITY.md` §11 (P5 do juiz).

## 5. Testes e gates (📊 saídas reais)
- **Fatias:** L1 `capas.test` TUDO VERDE (108 capas byte-idênticas; mutação 2 vermelha no motor e no produto) · L2 `a-cobranca-na-casca`
  73 checagens (7 cenários dourados; mutações 1 e 3 vermelhas) · L3 `as-telas-no-lugar` 40 OK (mutações 5a/5b vermelhas) · L4
  `a-loja-e-a-casca` 280 OK (mutação 6 vermelha) · L5 `links-internos` 8/0, 283 links lidos, 275 conferidos (mutações 4 e 5 vermelhas; 2
  links quebrados PRÉ-EXISTENTES em `app/api/admin/control-plane/me/route.ts:26-27` em `QUEBRADOS_CONHECIDOS`) · L6 o fio
  `scripts/a-loja-de-aplicativos.test.mjs` nasceu VERMELHO (15 elos) → verde; `backend/tests/test_spec139_o_fio.py` (📊 18 aplicativos
  lidos, faq nos 15) · `tsc --noEmit` exit 0 · rotas-montam "339 rotas ordenadas · MONTA" · pytest 26 passed.
- **Depois do conserto B:** capas 68 OK · fio 58 OK · casca 281 OK · telas 44 OK · links 8/0.
- **Confirmação** (HEAD `a21c6ba`): os 6 node + `test_spec139_o_fio` 6 passed + `tsc` 0 linhas + 3 sondas (abaixo).

## 5.1 §9.1 — o servidor responde (HEAD `6415078`)
`test:rotas-montam` → "A TABELA DE ROTAS MONTA" · `next build` exit 0 em 📊 47 min · `next start :3100` → `GET /api/versao` **200** ·
`GET /api/dashboard/auxiliaries/cobranca/enviadas` **401** (sem sessão; a rota nova EXECUTA) · `/dashboard/auxiliares` **307** → `/login` ·
os antigos (`galeria/follow-up-whatsapp`, `checklist-6h/hoje`, `personalizacao/agentes/even`, `personalizacao/custos`) **307** →
`/login?redirect=…` (o middleware de sessão vem ANTES do redirect da página) · `/embed/loja` 200 = a página EXISTENTE `/embed/[agentId]` com
`agentId='loja'` (conferido: sem o harness no HTML) · `tsc --noEmit` exit 0.
**NÃO MEDIDO por HTTP:** o 307 da página antiga para a nova DEPOIS do login — exige sessão real e não se forja sessão contra produção.
Coberto por executar o `page.tsx` real (`as-telas-no-lugar` 44 OK) e pelo guarda de links (casa os destinos); o red team 📊 0 de 26
páginas-redirect com destino sem rota ou 2 saltos. Fica para o Founder: clicar os 4 endereços antigos depois do Implantar (T-184).

## 6. Canário e rollout
| ambiente | estado |
|---|---|
| Amandus · Resulta · AutoFleet | ⏳ não rodou — o `smith-web` com a 139 não está no ar (T-183, depois da T-174); o canário é a T-184 |

**Isolamento com duas corretoras REAIS** (régua §6): NÃO medível hoje — 📊 `billing_sent_log` tem 0 linhas. A prova é o dublê com 2
corretoras + mutação 3 vermelha; a real fica para a primeira cobrança que sair (P-139-05). **Flags:** nenhuma nova.

## 7. Gate da SPEC — juiz 84 ‖ red team 78 ‖ design 83 → conserto A ‖ B → confirmação 88 · design 89 → conserto 2 → 92
- **Juiz 84** (HEAD `aa244dd`): ELO medido SIM; **B1** a Dúvida da Cobrança "Sim, quando o aplicativo está ligado" falsa em 3 dos 4 modos
  + "Hoje, da Allianz" cravado · **B2** rótulos: "parcela" era o recibo; "N a segurados" contava a equipe.
- **Red team 78 QUEBREI:** **B1** 📊 a tela dizia "2 a segurados" com 0 a segurados (2 pacotes à equipe, 1 teste) · **B2** parcela =
  recibo · **B3** 📊 7 de 10 entradas digitadas gravavam corpo diferente do modal ("2,5" → 25 boletos por execução) · **B4** o passo
  Configurar do Checklist nunca fechava (gravava `/api/dashboard/briefing`, era medido por rotinas).
- **Design 83** (44 capturas): galeria 80 · grade 84 · Configurar 82 · Hoje 80 · Follow-ups 78 · Resumos 79.
- **Conserto A** (os 4 do red team + B1/B2 do juiz + o design da Cobrança: "rotina" fora da tela, estado contraditório, chips humanos na
  mensagem, celular empilhado, "Instalar →"; a migration `_02`) **‖ conserto B** (direção C: destaque com a cena à direita e empilhado no
  celular; tile do card só com `cover_url`; esmaecido nos filtros; paleta 2D; cena por aplicativo; mais luz no escuro; 4:1 inteiro; telas
  movidas no padrão da casca; "Em breve" sem motivo repetido).
- **Confirmação 88 CONFIRMADO:** 📊 "3 cobranças … · 0 a segurados, 2 à equipe, 1 em teste"; campo `parcela`→`recibo`; "10 de 10 entradas
  digitadas gravam o MESMO corpo do modal de antes"; guarda [18] do Checklist verde; VERIFY `_02` `(0,0,0,0,5,4,3,0)`; os 7 hashes S1–S7
  idênticos aos de antes; contraste do tile pior 📊 5,64:1. Pendências C1–C6.
- **Design R2 89** (fresco; 40 páginas, 114 fatias): "o destaque no claro é ilustração de produto de primeira linha"; faltava o escuro em
  retina (grão grosso, peças cinza), `PermissionList` 10 px, o Checklist empilhado no celular, a sombra do hover.
- **Conserto de design 2** (12 commits): grão proporcional e só no fundo, .035 no escuro, peças na cor do aplicativo; hover com sombra (a
  causa: `shadow-card` colidia com a cor `card` e pintava a sombra da cor do cartão) e sem subir com movimento reduzido; `PermissionList`
  legível; Checklist com os 3 números numa faixa; "8 mensagens"; "Falta encaminhar ao cliente"; o nome inteiro em "Precisa de você" com o
  porquê na tela (D-139-G-01).
- **R3 verificação dirigida 92 PASSA** (📊 24 páginas sem rolagem horizontal, `pequenos: []`, `toques: []`, `jargao: []`). Sobram
  P-139-11…15.

## 📊 A BATERIA — quantas vezes ela rodou nesta SPEC
**1 rodada inteira** (HEAD `6415078`, worktree próprio, 3 partes em série; logs `scratchpad\bat_139\`): parte 1 **16 failed, 1838 passed,
2 skipped** (42:45) · parte 2 **397 passed** (3:58) · parte 3 **23 failed, 4735 passed, 7 skipped, 30 xfailed, 1 xpassed** (1:07:30) ·
front 13/13 exit 0 (capas 68 · casca 301 · fio 58 · cobrança 102 · telas 44 · links 8/0 · harness 2/0 · entregas 16 · chat-shell 75 ·
o-chat-novo 122 · linha 35/0 · caixa 5/0 · rotas MONTA).
**Triagem nominal (39 falhas):** 29 iguais à `BATERIA-LINHA-DE-BASE.txt` · 6 da base sumiram · 8 novas vs base JÁ triadas na B2
(ambiente/pré-existentes: `test_spec1310_f1_migration`, `test_spec131b_conserto_k1` = P-1310B2-14, `test_a_arvore_ficou_limpa_no_fim`,
`[test_a_fonte_comercial_bate_com_a_infocap]`, 4 `[test_e001101_*]`) · 2 novas: `[test_o_vocabulario_viaja_na_imagem]` **AMBIENTE** (teto
de 120 s sob carga; isolada passa no HEAD e estoura na `origin/main`) e `[test_auxiliar_aparece_e_diz_porque]` **REGRESSÃO DE GUARDA**
(procurava `titulo="O que faz"` literal; a L4 passou ao título condicional do "Em breve"; o produto estava certo) → consertada em `dbd6da1`
(o guarda lê as duas formas e exige "O que ele vai fazer"; verdade vencida, CLAUDE.md §9.3). **0 regressões de produto.**

## 8. Mudanças além do texto da SPEC
ESSENCIAL: (a) a `_02` corrigiu também 2 promessas falsas achadas na conferência (Checklist "às 6h"/"no máximo três"/"o canal que escolher";
Radar "todo dia") · (b) extrair também `PendenciasDaCobranca` e `LiberarReenvioDeTeste` (D-139-L2-01; sem isso a fila de pendências
sumiria) · (c) o guarda do harness (pedido do red team). VALIOSA: o passo "Instalar →" no Como começar da Cobrança (design N1).

## 9. Decisões (detalhe em `FOUNDER-DECISIONS.md`)
SPEC §7: **D-139-01…06** (capa dentro do `CapaGerada` 90 · paleta única 88 · direção pela prancha 85 · Cobrança pelo formulário EXTRAÍDO 90
· telas MOVIDAS 88 · a 001.9 como fatia 80). Da execução: **D-139-07** a C do Founder (85) · **-L1-01** teto 8 KB por capa (85) · **-L1-02**
matizes espalhadas (86) · **-L2-01** extrair a fila e o reenvio · **-L4-01** Radar e tarefas-agendadas fora do "Em breve" (80) · **-L4-02**
Follow-up e Resumo sem Configurar (85) · **-L6-01** sem tile com capa gerada (86) · **-CB-01** paleta 2D · **-CB-02** enquadramentos da C ·
**-CB-03** tile do card só com `cover_url` · **-G-01** nome inteiro em "Precisa de você" (80).

## 10. Riscos remanescentes (INFERÊNCIA)
- **O Implantar do `smith-web`** pode derrubar o servidor (P-132D-01): só depois da T-174 e fora do horário de atendimento.
- **A Cobrança real nunca foi aberta autenticada:** o design foi julgado no harness com os componentes reais e dados de exemplo; a tela
  autenticada, a barra Salvar e o 409 não foram vistos (o 409 nem acontece hoje, P-139-02).
- **Cobranças vazia:** 📊 0 linhas no ledger — a máscara nunca viu um nome real do portal (P-139-22).
- **Já no ar:** as Dúvidas novas aparecem na tela ANTIGA de produção desde as migrations (só texto).

### 10.1 📋 CAIXA DO FOUNDER (detalhe e comandos em `TAREFAS-DO-FOUNDER.md`)
**T-177 ✅ FECHADA** (você escolheu a C em 15/10) · **T-174** antes de tudo (swap) · **T-183** Implantar o `smith-web` (pode ser o MESMO da
T-180), fora do horário de atendimento · **T-184** o canário da loja (celular e notebook, claro e escuro; a Cobrança → Configurar sem
salvar; os 4 endereços antigos).

### 10.2 Pendências novas → `PENDENCIAS.md` P-139-01…25 (cada uma com o que destrava, de quem é e o que custa esquecer)

## 11. Impacto para o corretor
Depois do Implantar: uma capa ilustrada por aplicativo (a mesma família, cada uma com as peças do próprio trabalho), no claro e no escuro;
todo aplicativo na mesma casa; a Cobrança sem modal e com o que saiu, dia a dia; Checklist, Follow-up e Resumo dentro do aplicativo; os "Em
breve" sem Ligar; Personalização → Corretora reúne equipe, conhecimento, custos e o agente. **Nenhuma regra de envio mudou**; links antigos
continuam funcionando.

## 12. Declaração de integridade
Nenhum motor paralelo (CLAUDE.md §5): a capa é o MESMO `CapaGerada` (composição dentro dele, nunca um componente ao lado); a Cobrança é o
formulário EXTRAÍDO do `PainelDeRotinas` (modal e aba usam o mesmo hook e a mesma rota `/api/dashboard/rotinas`, intocada); o envio
(`billing_*`, `platform_outbound.py`) intocado — 📊 `git diff --stat 4a08ce4..HEAD -- backend/app` = só `servicos_da_corretora.py` (um link);
a leitura nova só faz `select` com `company_id` da sessão; os redirects são `page.tsx` existentes (nenhuma pasta dinâmica nova ao lado de
outra). §13.9: 0 nomes de corretora no diff de código. Nenhum segredo em log.

## 13. ROLLBACK
Código: `git revert` dos commits do §2 (o `smith-web` volta à loja da 131-B; os endereços novos somem e os antigos voltam a ter tela). Banco:
os ROLLBACK literais das `_01` e `_02` (devolvem os textos de 15/10), na ordem `_02` → `_01`. Direção da capa: trocar a linha
`DIRECAO_DO_PRODUTO`. Nada a desligar: não há flag nova.

## 14. FATO · INFERÊNCIA · RECOMENDAÇÃO
**FATO:** §7, §4, a bateria e o §5.1 acima; canário e isolamento real NÃO rodados. **INFERÊNCIA:** o risco vivo é operacional (o Implantar
do site). **RECOMENDAÇÃO:** T-174 → T-183 → T-184; a P-139-01 (o "Even" no padrão da Cobrança) antes de alguém instalar a Cobrança de novo.

## Push
```
```n$ git push origin HEAD:main
   4a08ce4..300b323  HEAD -> main
$ git rev-list --count origin/main..HEAD
0
```
```

## §11 A TELEMETRIA (`backend\.venv\Scripts\python.exe backend/scripts/medir_execucao_claude_code.py --sessao atual`, da raiz, 15/10 ~18:40 UTC)
```
SESSAO e9a700da-8565-495d-af27-519f28ff7607   (UTC)
EXECUTOR (sessao principal)                  15/10 03:36    897 min  turnos  226  pico   547k  ctx   76.5M  saida   177k  US$   52.85  opus-5-5
  agente . SPEC-139 L1: cover directions boa 15/10 04:51    445 min  turnos  119  pico   337k  ctx   26.0M  saida     9k  US$   16.56  opus-5-5
  agente . SPEC-139 L2: Cobrança in the app  15/10 05:42     27 min  turnos   76  pico   368k  ctx   18.0M  saida     9k  US$   11.24  opus-5-5
  agente . SPEC-139 L3: move screens into ap 15/10 05:42     15 min  turnos   52  pico   196k  ctx    7.3M  saida     5k  US$    4.77  opus-5-5
  agente . SPEC-139 L4: shell for all apps   15/10 05:42     25 min  turnos   71  pico   305k  ctx   14.9M  saida     9k  US$    9.31  opus-5-5
  agente . SPEC-139 L5: EXTRA-001.9 routes a 15/10 05:43     23 min  turnos   58  pico   202k  ctx    8.1M  saida     2k  US$    5.17  opus-5-5
  agente . SPEC-139 L6 seam and design harne 15/10 12:24     33 min  turnos  110  pico   392k  ctx   30.1M  saida     5k  US$   17.32  opus-5-5
  agente . SPEC-139 design judge with captur 15/10 12:58     44 min  turnos   58  pico   228k  ctx    8.5M  saida     6k  US$    5.60  opus-5-5
  agente . SPEC-139 code judge (fresh)       15/10 12:58     53 min  turnos   76  pico   241k  ctx   12.1M  saida     6k  US$    7.49  opus-5-5
  agente . SPEC-139 red team (fresh)         15/10 12:58     46 min  turnos   93  pico   278k  ctx   17.5M  saida    10k  US$   10.47  opus-5-5
  agente . SPEC-139 fix A: Cobrança and cont 15/10 13:52     34 min  turnos  102  pico   393k  ctx   26.6M  saida    12k  US$   15.75  opus-5-5
  agente . SPEC-139 fix B: covers, gallery,  15/10 13:55     43 min  turnos  123  pico   398k  ctx   33.6M  saida    16k  US$   19.39  opus-5-5
  agente . SPEC-139 design re-judge (fresh)  15/10 14:40     27 min  turnos   51  pico   185k  ctx    6.3M  saida     5k  US$    4.21  opus-5-5
  agente . SPEC-139 fix confirmation judge   15/10 14:40     17 min  turnos   48  pico   171k  ctx    6.1M  saida     5k  US$    4.04  opus-5-5
  agente . SPEC-139 design fix round 2       15/10 15:08     23 min  turnos   65  pico   223k  ctx   10.7M  saida     5k  US$    6.62  opus-5-5
  agente . SPEC-139 design targeted check    15/10 15:32      2 min  turnos   14  pico    89k  ctx    1.0M  saida     2k  US$    0.95  opus-5-5
  agente . SPEC-139 full test battery, triag 15/10 15:33    177 min  turnos   73  pico   143k  ctx    7.6M  saida    10k  US$    4.76  opus-5-5
  agente . SPEC-139 docs updater and report  15/10 18:33      6 min  turnos   35  pico   216k  ctx    5.6M  saida     1k  US$    3.97  opus-5-5
TOTAL  agentes alem do executor: 29  .  turnos 2249  .  ctx 456.8M  .  saida 0.38M  .  US$ 287.48
ferramentas do executor: PowerShell 124, Agent 30, Read 23, Edit 15, Write 12, SendMessage 7
```
📊 As 17 linhas "SPEC-139": **US$ 147,62** (API-equivalente, somadas da tabela; o atualizador medido aos 6 min). As 12 linhas da B2 e a do
chat estão no relatório da 131-0-B2; o EXECUTOR é dos dois. Todos `opus-5-5`. ⚠️ O "445 min" da L1 é relógio de parede: o agente ficou
vivo esperando a escolha do Founder; os turnos (119) dizem o trabalho. **API do produto:** 📊 US$ 0 (as capas são código; nenhuma chamada paga).

**Nota da execução: 87/100** (proposta pelo atualizador; o gerente fecha) — 5 blockers fechados com PAR vermelho e confirmação 88, design 92
com capturas, 0 regressões; desconta o canário e o isolamento com 2 corretoras reais (não rodaram) e o 307 depois do login, não medido por HTTP.
