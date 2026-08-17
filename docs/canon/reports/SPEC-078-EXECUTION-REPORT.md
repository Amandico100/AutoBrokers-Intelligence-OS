# SPEC-078 — Relatório de execução

**Branch:** `feat/spec078-cobranca-funciona-e-entrega-aparece`
**Commit inicial:** `6e1d4d3` (= `origin/main` ao começar)
**Commit final:** `0c8b50a` — publicado em `main` em 17/08/2026
**Supabase:** `dcajcvlzcjbmyapmklil`
**Tamanho:** 7 commits · 44 arquivos · +7837 / −816

---

## 1. O que a SPEC entregou

| Bloco | Resultado |
|---|---|
| **A** Segurança | As portas que dependiam de sorte passaram a depender de código |
| **B** Canal `auxiliary` | O número pareado da corretora **pode** enviar pelos Auxiliares, mediante autorização explícita |
| **C** Auxiliar × Rotina | Toda Rotina tem dono — por **constraint**, não por disciplina |
| **D/E** Modal | Nenhum campo visível sem efeito; o seletor só oferece modo com motor |
| **F** Entregas | O trabalho pronto **abre** |

---

## 2. Migrations — APPLY / VERIFY / ROLLBACK

Quatro aplicadas, todas expand-first, nenhuma destrutiva.

| Arquivo | O quê |
|---|---|
| `20260817_02_spec078_canal_auxiliary.sql` | `integrations.permite_envio_de_auxiliar` (default **false**) |
| `20260817_03_spec078_toda_rotina_tem_dono.sql` | Auxiliar de plataforma · backfill · FK RESTRICT · **NOT NULL** · FK composta por corretora |
| `20260817_04_spec078_historico_e_artifact.sql` | `routine_runs.company_id` + trigger · `output_full` · funções de retenção do bucket |

📊 **VERIFY, saída real:**

```
orfas                              0
coluna_ainda_nullable              0
dono_de_outra_corretora            0
corretoras_sem_tarefas_agendadas   0   (5 de 5)
execucoes_total                   32
execucoes_sem_dono                 0
trigger_existe                     1
canais autorizados a enviar        0   (ninguém ganhou por acidente)
agentes de atendimento ligados     0
```

### As travas MORDEM — e o controle prova que não é excesso de zelo

```
insert de rotina sem dono            → ERRO 23502  violates not-null
insert com dono de OUTRA corretora   → ERRO 23503  violates fk_routines_auxiliary_same_company
insert de execução sem company_id    → HERDOU o dono pelo trigger
CONTROLE: insert válido              → PASSOU (e foi apagado)
```

⚠️ **Nota de método:** tentei fazer `insert`+`delete` num CTE só e o `delete`
**não enxergou** a linha do `insert` — em Postgres, CTEs veem o mesmo snapshot.
A linha de prova ficou no banco até eu conferir e apagar em statement separado.
Vale para qualquer prova destrutiva: dois statements, e confira.

### ROLLBACK

Escrito em cada arquivo. Nenhum apaga rotina, execução ou Auxiliar. O rollback
do Bloco C **mantém** `tarefas-agendadas` de propósito: removê-lo deixaria
rotinas apontando para linha inexistente — o rollback criaria um problema pior
que o original.

---

## 3. Testes — saída real

### Guardas novos

| | Asserções |
|---|---|
| `test:spec078-seguranca` | **39** verdes · 0 vermelhas |
| `test:canal-auxiliary` | **43** verdes · 0 |
| `test:rotina-no-auxiliar` | verde, com controle em cada bloco |
| `test:entregas-abrem` | verde · 10 itens · 6 consultas com `company_id` |
| `test:entregas-historico` | verde · 19 linhas de controle |
| `test:ontologia-gate` | rc=1 sem credencial (era rc=0 e passava calado) |

### Bateria completa, ao fechar

```
node    rotas-montam · auxiliares-instalacao · canal-auxiliary · entregas-abrem
        entregas-historico · rotina-no-auxiliar · security-gates
        atendimento-estados                                      8 × rc=0

python  spec078_bloco_a · governador_de_envio · observador_nunca_fala
        alerta_que_nao_sai · spec044_tres_camadas · f2_routines
        spec073_runtime · spec045_observacao_whatsapp             8 × rc=0

tsc --noEmit                          limpo
next build                            exit 0 · BUILD_ID SFk0SkBa4ex-AyEsh11KB
rotas-montam                          292 rotas
```

### O servidor RESPONDE (CLAUDE.md §9.1)

```
/login                                        200
/landing                                      200
/api/dashboard/entregas                       401   executa e recusa
/api/dashboard/rotinas?auxiliar=...           401   executa e recusa
/dashboard/auxiliares/rotinas                 307 → /login?redirect=…  (o stub)
/dashboard/entregas/<uuid>                    307
/dashboard/entregas/rotina/<uuid>             307
/dashboard/entregas/abc.def/arquivo           404   a rota de bytes recusa de verdade
```

---

## 4. A mutação achou o que eu não achei — quatro vezes

Este é o dado mais útil do relatório. Foram **~34 mutações** ao longo da
execução, e **quatro passaram VERDE na primeira tentativa**. Em todos os quatro
casos o código estava certo e **o guarda é que estava errado**:

| # | O guarda casava com… | Conserto |
|---|---|---|
| 1 | uma string dentro de um **comentário** (Bloco B, `rank = {...}`) | casar com contexto do código |
| 2 | um **rótulo entregue à tela** em vez do tratador (Bloco B) | regex do `if (action === …)` |
| 3 | o formato do `<option>` **antigo**, que já não existia (E.1) | ler a lista `MODOS_COM_MOTOR` e comparar o conjunto |
| 4 | `output_full` citado no **comentário de cabeçalho** (F.4) | exigir as duas pontas: `select` e JSX |

E mais duas asserções minhas ficaram vermelhas por casar com comentários que
**explicavam que aquilo tinha sido removido** — o guarda ganhou
`semComentarios()`.

> **A regra que sai daqui:** guarda de fonte lê **código**. Um guarda que a
> documentação satisfaz não guarda nada. Onde a intenção for verificar o texto
> de um comentário, isso tem de ser dito com todas as letras.

### E um aviso operacional que vale mais que o código

📊 O commit `0e5bc5b` foi feito com `git add -A` **no meio de uma bateria de
mutação de um agente paralelo**, e capturou o defeito injetado — o
`output_preview` cru despejando CPF na lista de Entregas — mais um arquivo
`.bak`. Detectado e corrigido antes de subir; o `HEAD` traz `detalheDaExecucao`,
que lê só a **primeira linha** do relatório (o título), nunca a lista de
clientes.

> **`git add -A` durante mutação commita o defeito.**

---

## 5. Correções de afirmações minhas anteriores

Separando FATO de erro, como o CLAUDE.md §12 exige.

| O que eu afirmei | O que é verdade |
|---|---|
| "A tela só deixa marcar 2 de 6 seguradoras" | **Errado.** A lista fixa já tinha sido removida na SPEC-073 Q3; a tela deriva de `/api/dashboard/portal-credentials`. A auditoria leu o repositório principal, atrasado em relação à `main`. 📊 O worker no ar reporta as 6 operacionais |
| "`PUT /api/agent/config` liga o agente por omissão" | **Errado.** Ele escreve `agent_enabled`, que 📊 **nenhum caminho de runtime lê** (`grep` em `nodes.py` → zero) |
| "Tela e instalador discordam sobre 'conectado'" | **Errado.** Os dois usam `conexoesDaCorretora` |
| "O segundo número vira necessário quando `send_mode` for `live`" | Certo na direção, **errado no essencial**: `live` não existe. Não há caminho de código até um envio |

---

## 6. O que ficou de fora, e por quê

| | Por quê |
|---|---|
| **Modo `live`** | SPEC-079. Não é configuração, é construção — e é a única parte capaz de dano irreversível a terceiro. Juntá-la a uma SPEC que mexe em ontologia, telas e migrations é misturar o reversível com o irreversível no mesmo gate |
| **Modo `approval` com motor** | Mesmo fio do `live` |
| **Chamador da purga do Storage** | A função existe e está **desligada**. Ligar exige duas decisões do Founder: o prazo e a flag. P-214 |
| **`NOT NULL` em `routine_runs.company_id`** | O segundo escritor não foi tocado nesta rodada; o trigger cobre. Endurecimento na próxima |
| **Apagar a coluna `agent_enabled`** | Remoção de coluna viva não cabe numa SPEC de funcionalidade |

Tudo acima está em [`PENDENCIAS.md`](../PENDENCIAS.md) — P-211, P-212, P-213,
P-214 — com dono e o que destrava.

---

## 7. Canário

| Corretora | Estado ao fechar |
|---|---|
| **AMANDUS SEGUROS** | `tarefas-agendadas` instalado `inactive` · 0 portais · agente **desligado** |
| **Resulta Seguros** | `cobranca-feita` `inactive` + `tarefas-agendadas` `inactive` · 1 rotina pausada, agora **com dono** · agente **desligado** |
| **AutoFleet** | `cobranca-feita` `paused` + `tarefas-agendadas` `inactive` · 1 rotina pausada, agora **com dono** · agente **desligado** |

📊 Os dois Auxiliares em `active` no banco (`follow-up-whatsapp` e
`resumo-atendimentos`, na AMANDUS) são de **junho**, de gatilho manual, e não
foram tocados.

---

## 8. Invariantes — todas conferidas contra o banco

```
I1  nenhum agente de atendimento ligado          0   ✅
I2  nenhum canal autorizado a enviar             0   ✅  (nada por acidente)
I3  toda Rotina tem dono                         0 órfãs, coluna NOT NULL   ✅
I4  desligar o Auxiliar para o robô              provado por teste + controle   ✅
I5  o observer nunca vira canal de saída         proibição preservada por padrão   ✅
I6  nenhum campo sem efeito                      guarda com 3 mutações   ✅
I7  toda entrega abre                            guarda com 9 mutações   ✅
I8  nenhum motor paralelo                        ver §9   ✅
```

---

## 9. Declaração

**Nenhum motor paralelo foi criado.** Não nasceu outro runtime, RAG, memória,
publisher, scheduler, executor, Skill Registry, Tool Gateway, Artifact Hub,
Auxiliary Factory, Intelligence Fabric, Research Orchestrator, Control Plane,
Eval Platform, Billing Engine, Ledger nem Readiness Engine.

Peças **reutilizadas** em vez de recriadas:
`IntegrationService.pode_enviar` (a autoridade de canal) · o Artifact Hub do
Checklist das 6h · o governador de vazão de `platform_outbound` · o
`routine_engine` existente · o mapa de telas de `catalog.ts` · o padrão de stub
de redirect das três rotas irmãs da SPEC-064.

Peça **movida**, não duplicada: o painel de rotinas, por `git mv` — o histórico
do arquivo sobreviveu.

---

## 10. Riscos remanescentes

1. **P-212** — `get_platform_whatsapp_integration` escolhe sem ranquear. Não
   morde hoje (nenhuma corretora tem duas elegíveis); morderá quando alguém
   autorizar o canal `auxiliary` numa corretora com `attendance` ativo.
2. **P-213** — `notFound()` devolve 200 em página dinâmica. 📊 Controle rodado:
   afeta a app inteira, não só as rotas novas. Não há vazamento — a rota de
   bytes devolve 404 de verdade.
3. **A purga do Storage não tem chamador.** Boletos de segurado continuam sem
   prazo até o Founder decidir. 62 objetos, o mais antigo de 11/07.
4. **`GLOBAL_KILL_SWITCH` continua ausente do portal-worker.** 📊
   `kill_switch_presente: false`. A porta que importava foi fechada por código
   (A.1); esta é a que depende de uma variável de ambiente.
