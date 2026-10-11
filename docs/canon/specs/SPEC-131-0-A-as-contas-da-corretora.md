# SPEC-131-0 parte A — As contas da corretora: funções, dono da renovação, Agger de cada pessoa, qual Agger usar, manual por serviço

> v1.1 · 11/10/2026 (v1.0 → revisor cego 72 → v1.1: §5.1 motor, §5.2 isolamento, leitores do QCM na F4, ponte F1→F3, régua
> real no gate, nomes neutros) · gerente Opus 5.5 · branch `spec/131-0-A-contas` · base `7aa15ce` · rito AAA v13 · 🔴 CRÍTICO por piso
> Proposta: `specs-propostas/SPEC-131-0-CONTAS-COMERCIAIS-E-CONEXOES.md` (v0.1) · vontades: `programa-multicalculo/RETORNO-DO-FOUNDER-2026-10-10.md`
> BLOCO 0: `programa-multicalculo/131-0/BLOCO0-INFOCAP-A-CONEXAO-TROCADA.md` (a conexão "InfoCap RESULTA" tinha o login da AutoFleet;
> a regra do dono provada nas DUAS carteiras reais: Resulta 99/99, AutoFleet 217/217) + mapa do código do investigador (rascunho).

## 1. EXECUTION CARD
```
OUTCOME ..............  qualquer corretora configura QUEM É QUEM: funções de trabalho de cada pessoa (comercial · calculista ·
                        negociador); que códigos de produtor do sistema de gestão são de cada pessoa; a regra de quem é o DONO da
                        renovação (dado, não código); o Agger de cada pessoa ao lado do Agger da corretora; e o manual de cada
                        serviço (Quem Cobra Menos · Cotação · Renovação) com a chave calcular × entregar × negociar. Uma função
                        só decide em qual Agger cada cálculo acontece, e o cálculo grava quem pediu, qual conta, por qual regra.
RISCO ................  7 — ALCANCE 2 (a corretora) · REVERSIBILIDADE 3 (o cálculo cria negócio no Agger de uma PESSOA) · FREQ 2
SUPERFÍCIE ...........  2 — peças novas (vínculo, regra, qual_agger, tela de serviços) + o motor ganha o eixo pessoa × robô
PISO APLICADO ........  §3.2 — migrations que mudam QUEM PODE (CHECK do papel) e estrutura · autenticação (a fonte do papel) ·
                        senha de pessoa no cofre · o filtro company_id em toda leitura nova
NÍVEL ................  🔴 CRÍTICO · gerente Opus 5.5 · 4 builders Opus 5.5 xhigh EM PARALELO · juiz ‖ red team · conserto ·
                        confirmação se houver blocker · lente do dado (a régua do dono é número que a corretora lê)
O FIO ................  apólice a renovar (InfoCap da corretora, por _abrir) → /prod_docs avulso → regra_de_dono (linha da corretora
                        ou padrão do sistema) → produtor dono → membro_produtores → user_id ativo na corretora → porta.calcular(
                        servico='renovacao', dono_user_id) → qual_agger.decidir → multicalculo_calculos.conta_exigida_id + regra +
                        fallback + motivo → motor._escolher(somente=conta exigida) → robos (uso='membro' = login de PESSOA)
                        · ramos paralelos: QCM → servico='qcm' → SÓ conta uso='global' · cotação → conta do SOLICITANTE, senão global
                        · TESTE DO FIO (1ª entrega da costura, F5): dublê da InfoCap com a forma real do /prod_docs, banco dublê com
                        o esquema real, a porta e o motor REAIS; membro_a/membro_b em duas corretoras (nunca nome real, §13.9)
PARALELISMO REAL .....  F1 ‖ F2 ‖ F3 ‖ F4 com arquivos DISJUNTOS (§4) → F5 costura (gerente)
UNIDADES .............  U1 funções + papel fechado + uma fonte do papel · U2 vínculo produtor e regra de dono · U3 dono_da_apolice +
                        régua · U4 contas com uso e dono + motor pessoa×robô · U5 qual_agger + auditoria · U6 tela Aggers da equipe ·
                        U7 manual por serviço + chave + tela Serviços · U8 o fio
COESÃO ...............  F1 = U1 · F2 = U2+U3 · F3 = U4+U5+U6 · F4 = U7 · F5 = U8 + main.py + migrations aplicadas
TIME .................  gerente · investigadores B0 (feitos) · F1 ‖ F2 ‖ F3 ‖ F4 · F5 · juiz ‖ red team · conserto · confirmação
REFERÊNCIA ...........  interna: test_spec133a1_o_agger_da_corretora.py:118 (dois tenants) · conta_do_robo.py (o conector) ·
                        lib/auxiliaries/config-store.ts (edição com histórico) · externa §7
GATES ................  §6
O ELO ................  "o cálculo da renovação sai no Agger da Mariana PORQUE ela é a dona": medido A (régua 99/99 e 217/217 no
                        /prod_docs real), B (o motor obedece conta_exigida) e o ELO (teste do fio: a apólice cujo dono é o código da
                        Mariana chega ao motor com a conta da Mariana, e a de outro dono nunca)
FAIXA DE RELÓGIO .....  💭 9–13 h (builders 2–3 h em paralelo)
```

## 2. O que muda (contrato) e o que NÃO pode mudar
**Muda:** (1) `company_members.funcoes` e o papel de acesso fechado; o papel passa a ter UMA fonte (`company_members`); (2) a
corretora diz que códigos de produtor são de quem e qual é a regra do dono; (3) uma conta Agger pode ser da CORRETORA (`uso='global'`)
ou de uma PESSOA (`uso='membro'`, `dono_user_id`); (4) toda escolha de conta passa por `qual_agger.decidir` e fica auditada;
(5) `multicalculo_config.servicos.{qcm,cotacao,renovacao}` separa os manuais; a chave `modo` por serviço com exceções.
**Não muda:** o Quem Cobra Menos cota como hoje (só pela conta global, agora por regra escrita e testada); a retomada/o recálculo
continuam funcionando; a conta global continua sem horário (D-129C-01); nada é enviado ao cliente por esta SPEC; nada se escreve na
InfoCap (só GET).

## 3. Decisões tomadas na abertura (nota 0–100; o maior vence; registradas em FOUNDER-DECISIONS)
| id | decisão | nota |
|---|---|---|
| D-131-0-03 | dono da renovação na InfoCap = o produtor `indireto="F"` do `/prod_docs` avulso — 📊 Resulta 99/99, AutoFleet 217/217 | 96 |
| D-131-0-05 | o Agger de uma pessoa é login de PESSOA: o robô entra, calcula, sai (logout sempre); sessão ativa = Cancelar e esperar, nunca "Prosseguir"; QUANDO usar é regra do auxiliar (renovação de madrugada; cotação = a própria pessoa pediu). Ocupada 3× → o cálculo falha com o motivo e QUEM PEDIU decide (a 132 pergunta); nunca cai calado na global (R3). ⚠️ decidida SEM medir "transferir negócio entre usuários" (exige escrita na conta de uma pessoa) → P-1310 para o BLOCO 0 da 132 | 84 |
| D-131-0-06 | a senha do Agger da pessoa: o admin cadastra por ela OU a própria pessoa; nunca reaparece | 88 |
| D-131-0-14 | usuários: opção B incremental (funções + papel fechado + uma fonte); grupos fora | 85 |
| D-131-0-26 | revê a D-129C-02: a InfoCap da Resulta TEM RE (📊 2026: RESI 255 · COND 227 · EMPR 148); é a fonte de QUEM e QUANDO renova | 95 |
| D-131-0-27 | a conexão "InfoCap RESULTA" da Amandus guarda o login da AutoFleet → o NOME é corrigido para dizer a verdade; trocar o login fica com o Founder (o canário de auto da Amandus usa o banco da AutoFleet) | 85 |
| D-131-0-28 | o convite por link (que hoje nem cria o vínculo) fica para a SPEC de usuários; o `mudar123` já saiu (133-A.1) | 80 |
| D-131-0-29 | o dono da conta Agger é a PESSOA (`dono_user_id` → `users_v2`), não o vínculo — remover alguém da equipe não fica travado por cálculos antigos; a conta só vale se a pessoa for membro ATIVO daquela corretora | 88 |
| D-131-0-30 | o vínculo produtor ↔ pessoa usa `(user_id, company_id)` → `company_members` ON DELETE CASCADE (saiu da equipe = o vínculo cai = a renovação dele vai para "sem dono") | 90 |
| D-131-0-31 | a regra do dono é DADO: linha da corretora em `regras_de_dono`, senão o padrão do SISTEMA em JSON (sem nome de corretora); a auditoria diz qual das duas decidiu | 86 |
| D-131-0-32 | `servico` é coluna NOVA (`qcm·cotacao·renovacao`); `origem` não muda (CHECK, prioridade, ~15 leitores) | 92 |
| D-131-0-08 | os auxiliares Cotação/Renovação NASCEM com runtime (131/132); a parte A entrega a config por serviço e a tela "Serviços", não cartões vazios no catálogo | 85 |
| D-131-0-07 | a ordem guiada (R9) é o cabeçalho da tela "Serviços": 4 passos com estado lido do banco (sistema de gestão → Agger da corretora → equipe e Aggers → serviços) e o link de cada um | 86 |
| D-131-0-33 | quem calcula × quem negocia × responsável POR RAMO (R19/D-131-0-24) e o substituto de férias (V2) ficam para a 131/135, que os consomem; aqui só as funções da pessoa | 78 |

## 4. As fatias — arquivos de cada uma (DISJUNTOS)
**F1 · membros** — `backend/supabase/migrations/20261011_02_spec1310_membros.sql` (funcoes text[] + CHECK; CHECK do papel
`owner·admin_company·member·attendant` NOT VALID→VALIDATE) · `lib/admin/admin-auth.ts` (o fallback lê `company_members` da empresa
primária, nunca `users_v2.role`) · `app/api/dashboard/team/route.ts` (funcoes no GET/POST/PATCH; PATCH espelha o papel em `users_v2`
quando é a empresa primária; DELETE chama `POST /api/portal/aggers-da-equipe/desligar-membro` da F3 — nunca escreve `portal_accounts`;
o fallback de `admin-auth.ts` exige vínculo `status='active'` e falha FECHADO)
· `app/dashboard/personalizacao/equipe/TeamClient.tsx` · `lib/admin/admin-auth-policy.ts` · `lib/admin/tenant-overview-store.ts` ·
`backend/tests/test_spec048_isolamento_corretoras.py` (§9.3: a lição migra) · testes novos `scripts/spec1310-*.test.mjs`,
`backend/tests/test_spec1310_f1_*.py`.

**F2 · dono** — `…/20261011_03_spec1310_dono.sql` (`membro_produtores`, `regras_de_dono`) · `backend/app/comercial/fonte_infocap.py`
(`prod_docs_avulso`, `produtores`) · `backend/app/services/sistema_de_gestao/` (novo: `dono.py`) ·
`backend/app/data/providers/infocap/regra-de-dono-padrao.json` · `backend/app/api/contas_da_corretora.py` (novo router, SEM registrar
no main.py) · `app/api/dashboard/equipe/sistema-de-gestao/route.ts` · `app/dashboard/personalizacao/equipe/QuemEQuemNoSistema.tsx` ·
`app/dashboard/personalizacao/equipe/page.tsx` · aposentar `producer-roles.resulta.json` (+ `executive_intelligence.py` +
`test_o_vocabulario_viaja_na_imagem.py` + `test_o_pulso_360_nao_pertence_a_infocap.py`) · testes `backend/tests/test_spec1310_f2_*.py`.
A chave de cache do `/prod_docs` leva a CONEXÃO/corretora (o `nosnum` se repete entre bancos — 📊 laudo dos prints); `dono_da_apolice`
e `medir_regra` aceitam `fonte` injetada (a régua real do gate).

**F3 · contas** — `…/20261011_04_spec1310_contas.sql` (`portal_accounts.uso/dono_user_id`; `multicalculo_pedidos.servico/
solicitante_user_id`; `multicalculo_calculos.conta_exigida_id/conta_regra/conta_fallback/conta_motivo`) ·
`backend/portal_worker/multicalculo/{robos,motor,conta_do_robo,comando_robo}.py` · `backend/app/services/multicalculo/{porta,
qual_agger(novo),repositorio}.py` · `backend/app/services/canal/cotacao.py` · `backend/app/api/portal.py` ·
`app/api/dashboard/agger-da-corretora/route.ts` · `app/api/dashboard/aggers-da-equipe/route.ts` (novo) ·
`components/vault/AggerDaCorretoraModal.tsx` (monta a seção "Aggers da equipe") · `components/vault/AggersDaEquipe.tsx` (novo) ·
`backend/tests/dubles/banco_multicalculo.py` · testes `backend/tests/test_spec1310_f3_*.py` · os que o dublê quebra:
`test_spec133a1_o_agger_da_corretora.py`, `test_spec129b_o_motor.py`, `test_spec129b_o_fio.py`, `test_spec129c_*`.

**F4 · serviços** — `backend/app/services/multicalculo/config.py` · os leitores do QCM da §5.3 (`multicalculo/proposta.py`,
`multicalculo/negociacao.py`, `multicalculo/manual_de_negociacao.py`, `canal/{workflows,entrada,conversa,repositorio}.py`,
`artifacts/proposta_apresentacao.py`) · `backend/app/api/servicos_da_corretora.py` (novo, SEM main.py; inclui `GET …/prontidao` dos
4 passos, só leitura) · `app/api/dashboard/servicos/route.ts` · `app/dashboard/personalizacao/servicos/` (novo) · o arquivo de
navegação de Personalização · testes `backend/tests/test_spec1310_f4_*.py` (o G8 da 130-A e os `test_spec130a*`/`test_spec133a*`
continuam verdes).

**F5 · costura (gerente)** — `backend/app/main.py` (2 routers) · `backend/tests/test_spec1310_o_fio.py` · aplicar `_02→_03→_04` com VERIFY
· corrigir o NOME da conexão da Amandus (D-131-0-27) · a régua real.

## 5. Os contratos entre fatias (nomes exatos)
```
F2  app.services.sistema_de_gestao.dono
      regra_de_dono(db, company_id, sistema='infocap') -> Regra{campo, igual, codigo, origem: 'corretora'|'padrao_do_sistema'}
      dono_da_apolice(db, company_id, *, codfil, nosnum, fonte=None) -> DonoDaApolice{status: 'ok'|'sem_dono'|'ambiguo'|
            'sem_membro'|'sem_conexao', codigo_produtor, papel_cru, user_id|None, regra_origem, motivo}
      membro_do_produtor(db, company_id, sistema, codfil, codigo) -> user_id|None   (só membro ATIVO da corretora)
      medir_regra(db, company_id, *, dias=30, limite=150) -> dict (apólices, com_um_dono, sem_dono, ambíguas, donos_sem_membro…)
F3  app.services.multicalculo.qual_agger
      decidir(db, *, company_id, servico, solicitante_user_id=None, dono_user_id=None, conta_de_origem_id=None,
              vence_em_dias=None, cfg=None) -> DecisaoDeConta{conta_id|None, uso, regra, fallback, motivo, aviso, recusa}
      regras: qcm→global (conta_id None: o motor faz rodízio SÓ entre uso='global') · cotacao→conta membro do solicitante
      ativa, senão global com aviso · renovacao→conta do dono; sem dono/sem conta→global + aviso ao admin; senha recusada→
      recusa, global só se vence em < servicos.renovacao.conta_global_se_vence_em_dias (padrão 5) · recálculo→a mesma conta
    porta.calcular(..., servico=None, solicitante_user_id=None, dono_user_id=None)  — servico None = legado (teste)
F4  config.carregar(company_id, db, servico=None)  — padrão do produto ⊕ corretora ⊕ servicos[servico] (o serviço sobrepõe)
    config.modo_do_servico(cfg, servico, ramo=None, valor=None) -> 'calcular'|'calcular_entregar'|'calcular_entregar_negociar'
    config.pode_entregar(...) / pode_negociar(...) -> bool
Colunas (F1 lê a de F3): portal_accounts.dono_user_id uuid · portal_accounts.uso text ∈ global·membro·teste (só portal_key='agger')
```

### 5.1 O motor: `uso × evento → ação` (F3)
```
evento                         global (robô dedicado)        membro (login de PESSOA)                    teste (canário)
quem pode escolher             candidatos() — rodízio        SÓ por somente=conta_exigida_id            como hoje (origem teste)
fim do cálculo                 como hoje (segura ociosa)     LOGOUT sempre (_soltar_conta por USO)      como hoje (logout)
SessaoOcupada / sessão ativa   ocupada 30 min (como hoje)    Cancelar; conta ocupada 30 min; o cálculo   pausado (como hoje)
                                                             volta à fila; na 3ª → falha motivo
                                                             'agger_da_pessoa_em_uso' (sem cair na global)
senha recusada                 como hoje                     bloqueado na 1ª (nunca insistir)            como hoje
retomada / recálculo           como hoje (qualquer global)   somente=account_id (a MESMA conta, V20)    como hoje
janela                         nenhuma (D-129C-01)           nenhuma na conta (R-HORARIO-2: o auxiliar)  exige janela (como hoje)
servico=None (legado/canário)  pode                          NUNCA                                        pode
backfill                       label 'agger-da-corretora'    —                                            robo_estado 'teste' ou label 'canario%'
teto                           teto_da_conta por conta; o teto da corretora soma todas — a renovação usa origem 'auxiliar' (prioridade menor que 'canal')
```
### 5.2 Isolamento do dono da conta (F3)
Escrita: `conta_do_robo.cadastrar_do_membro(supa, company_id, dono_user_id, usuario, senha, por_user_id)` recusa se o dono não é
`company_members` ATIVO da MESMA `company_id` ou `users_v2.status` não ativo; só admin da corretora OU o próprio dono. Uso: `qual_agger`
E `robos.conta_elegivel` reconferem (membro ativo + usuário ativo) — falha = conta inelegível (fail-closed). Banco: índice único parcial
`(company_id, dono_user_id) WHERE uso='membro'`; `CHECK (portal_key<>'agger' OR uso IS NOT NULL)`; `CHECK ((uso='membro') = (dono_user_id
IS NOT NULL))` para agger; FK `dono_user_id → users_v2` ON DELETE RESTRICT; FK composta `(conta_exigida_id, company_id) →
portal_accounts(id, company_id)`. Desligar: `conta_do_robo.desligar_do_membro(supa, company_id, user_id)` (pausa + apaga a senha) é o
ÚNICO escritor; endpoint `POST /api/portal/aggers-da-equipe/desligar-membro` (chave interna) que a F1 chama no DELETE da equipe (falhou →
o vínculo sai mesmo assim, a conta já é inelegível; a resposta diz `agger_pendente: true`). Mutação: conta de membro removido ou de
outra corretora escolhida → VERMELHO.
### 5.3 O manual por serviço tem LEITOR (F4)
`servico=None` = a base da corretora (o comportamento de hoje). Os leitores do QCM passam `servico='qcm'`: `proposta.py` (cfg_sol e
cfg_anf), `canal/{workflows,entrada,conversa,repositorio}.py`, `artifacts/proposta_apresentacao.py`, `negociacao.py`,
`manual_de_negociacao.py` → F4. (`canal/cotacao.py` é da F3, que passa `servico='qcm'` na porta E no `carregar`.) O gate mede pelo
CAMINHO DA PROPOSTA: mudar `servicos.renovacao` não muda o HTML do QCM; mudar `servicos.qcm` muda. A F4 põe no `PADRAO_DO_PRODUTO`
`servicos.renovacao.conta_global_se_vence_em_dias = 5`. A tela edita: modo + exceções (ramo, valor acima de) por serviço;
preferências de seguradoras por ramo (comum e por serviço); renovação: `reajuste_basica_pct` por ramo, `antecedencia_dias`,
`conta_global_se_vence_em_dias`. O `aviso` da decisão fica em `multicalculo_calculos.conta_motivo`; quem o entrega é a 131/132.

## 6. GATES
dois tenants reais em toda fatia (CLAUDE.md §7) · mutações, uma vez cada: o QCM pega conta `membro` → VERMELHO · a cotação da Ellen
usa a conta da Mariana → VERMELHO · o dono vira `ordem 1` → VERMELHO · o fallback do papel volta a `users_v2.role` → VERMELHO · mudar
`servicos.renovacao` altera o QCM → VERMELHO · nenhuma senha em log/arquivo/teste · `py_compile`/`tsc` · migrations pelo VERIFY (o
OBJETO) · `npm run test:rotas-montam` + `next start` + uma requisição a `/api/…` (§9.1) · bateria sem regressão contra a linha de base ·
🔴 a RÉGUA REAL: `dono.medir_regra` (código do produto, fonte injetada com o login de cada corretora) nas duas carteiras de 30 dias →
um dono em 100 % (📊 BLOCO 0: 99/99 e 217/217), e a mesma régua com a regra mutada para `ordem 1` cai (≈ 37/99, 24/217) · `nosnum` igual
em duas corretoras nunca cruza cache nem vínculo.

## 7. O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS
- https://slack.com/help/articles/360018112273-Types-of-roles-in-Slack · papéis de acesso FECHADOS (owner/admin/member/guest) separados
  do que a pessoa faz · MODELAMOS: papel fechado + funções de trabalho à parte · REJEITAMOS papéis customizáveis (nenhuma SPEC pede) ·
  o juiz confere o CHECK do papel e que `funcoes` não dá acesso.
- https://support.anthropic.com/en/articles/9267305-what-is-the-claude-team-plan · a organização habilita a integração e CADA pessoa
  autentica a sua · MODELAMOS: Agger da corretora (global) + Agger de cada pessoa · REJEITAMOS conexão pessoal sem a corretora · o juiz
  confere que a conta `membro` só vale para membro ativo da MESMA corretora.
- https://help.openai.com/en/articles/8542115-chatgpt-business-faq · admin gerencia membros e conectores do workspace · MODELAMOS: o
  admin cadastra o Agger por qualquer pessoa, a pessoa pelo seu · o juiz abre a rota e testa admin × membro × outra corretora.
- https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners ·
  o DONO é regra declarada (arquivo), não convenção na cabeça · MODELAMOS: a regra do dono é dado com origem auditada · REJEITAMOS
  inferir o dono pelo nome · o juiz muta a regra para `ordem 1` e vê a régua cair de 99/99.
