# SPEC-EXTRA-001.10 · O portal de vidros de ponta a ponta

> **SPEC convertida** em 20/09/2026 (modo CONVERSÃO, protocolo §8) sobre `083eeca`, a partir de
> [`specs-propostas/SPEC-EXTRA-001.10-…md`](../specs-propostas/SPEC-EXTRA-001.10-o-portal-de-vidros-de-ponta-a-ponta.md)
> (a proposta continua sendo a fonte do detalhe por unidade e da §13 — referências externas).
> Rito: PROTOCOLO AAA **v13 · O FIO**. 📊 medido · 💭 ilustrativo · ❓ desconhecido.
> 🔴 **Esta conversão incorpora a CAPTURA Nº 1 (para-brisa Yelum, 20/09/2026)**, que chegou antes do build e muda o desenho.

## 0. EXECUTION CARD

```
OUTCOME ..............  o segurado descreve o dano no WhatsApp; o agente coleta ANTES tudo o que o portal pede,
                        abre o pedido em QUALQUER seguradora que o portal publica, LÊ o desfecho que o portal
                        decidiu (loja direta · agenda com lojas · analista · vistoria) e devolve ao segurado
                        nº do atendimento + franquia + próximo passo. Tela/resposta desconhecida = handoff com
                        dossiê + fila de aprendizado, nunca silêncio
RISCO ................  8 = alcance 3 (segurado) + reversibilidade 3 (pedido real na seguradora) + frequência 2
SUPERFÍCIE ...........  3
PISO APLICADO ........  §3.2 "qualquer coisa que ENVIE" → CRÍTICO
NÍVEL ................  CRÍTICO · builders Opus 5 xhigh · juiz Fable ‖ red team Fable · confirmação se blocker
O FIO ................  §2 abaixo · teste do fio: backend/tests/test_o_fio_do_portal_de_vidros.py
PARALELISMO REAL .....  2 builders, arquivos DISJUNTOS (§4): A = worker/journeys/vidros_*  ·  C = app/* + freio
UNIDADES .............  §3
COESÃO ...............  tudo que toca SessaoVidros ↔ vidros_estado ↔ vidros_apifirst ↔ vidros_api fica com A
                        (mesmo contrato, arquivo-hub). O contrato A↔C é a §5 e é LEI para os dois
TIME .................  2 builders · juiz ‖ red team · confirmação (gatilho: ≥1 blocker) · atualizador de docs
REFERÊNCIA ...........  interna: backend/tests/test_spec074_a_fronteira_material_executada.py (dublês e ordem
                        checkpoint×POST) · test_a_maquina_de_lavar_vai_ate_o_fim.py · externa: proposta §13
GATES ................  §6 (G1–G11)
O ELO ................  "loja/agenda aparece PORQUE opcoes-disponiveis manda": A medido (3 desfechos), B medido
                        (20 chaves × 3 capturas), B→A medido no bundle (função roteadora M(o)) — §1
FAIXA DE RELÓGIO .....  💭 10–14 h · teto 1,5× · 24 agentes
```

## 1. BLOCO 0 — remedido em 20/09/2026

| # | a proposta afirma | 📊 medido | comando |
|---|---|---|---|
| B0.1 | sem PATCH na sessão | 0 ocorrências · 12 métodos | `grep -n "atualizar_atendimento\|PATCH" portal_worker/journeys/vidros_sessao.py` |
| B0.2 | fronteira fixa | `FRONTEIRA_MATERIALIZAR = "gravar_questionario"` (:233) | `sed -n 228,240p …/vidros_estado.py` |
| B0.3 | 9 EP_ nunca chamados | **11** | laço `grep -rn $ep` da proposta §4 |
| B0.4 | 3 slugs, um é ITAU | confirmado (:102-106) | `sed -n 100,107p …/vidros_apifirst.py` |
| B0.5 | três verdades | prompt agora na linha **136** (não 133); `TRANSPORTAVEIS` 6 campos | `grep -n IMEDIATAMENTE app/core/prompts.py` |
| B0.6 | 354/188/41/14/29/44 | **idêntico** | `python scripts/portal_factory.py lab har --arquivo "…/YELUM 1/…har"` |
| C-A | freio global ao processo | confirmado (`__init__.py:294-323`) · 🔴 e em produção ele já está **LIGADO** nos dois serviços | env colado pelo Founder |
| C-B | token só depois do PUT corretores | confirmado no HAR novo | leitor Opus sobre `importar_har` |
| Q-C | tela lista "Liberty" ou "Yelum"? | `NomeFantasia = "YELUM SEGURADORA"`, slug `LIBERTY`, código 56 → digitar "Yelum" casa | `GET /seguradoras/` no HAR novo [0008] |

### 1.1 🔴 O que a captura nº 1 mudou (📊 4 capturas lidas por `trafego.importar_har`, 20/09)

```
1. QUEM DECIDE loja/agenda é o PORTAL, por `GET /agendamentos/opcoes-disponiveis` (20 chaves), roteado no bundle:
     IrParaConclusaoDeAtendimento|ExisteVistoriaCriada|ExisteAgendamento|ExisteOrdemServico|VistoriaFinalizada
                                   → CONCLUSÃO: loja já atribuída, SEM agenda ("ligue para a loja para agendar")
     PermiteVistoriaAmbas|PermiteVistoriaLoja|PermiteVistoriaMobile|RealizarVistoria → VISTORIA (0 exercícios)
     DisponibilizarAgendamento → AGENDA: OpcoesAgendamento[] (lojas) → datas → horários
   📊 para-brisa c/ reparo: conclusão · lataria: conclusão · vidro de porta (troca): agenda com 1 loja.
   Mesma seguradora, mesma apólice, mesma categoria V, desfechos opostos ⇒ NÃO é atributo de peça.
2. O REPARO é uma decisão do SEGURADO que o código não conhecia: `POST /questionarios/regras-reparo` →
   `{ExibirDialogDeReparo}`; se true o portal pergunta "quer tentar o reparo? (grátis, 30 min)" e grava por
   `PUT /atendimentos/alterar-reparo {"Reparo": bool}`. 📊 grep no repo: 0 ocorrências das duas coisas.
   `StatusReparo` na OPÇÃO da pergunta prediz o desvio uma rodada antes.
3. A inferência de P0-3 foi CONFIRMADA (N=2 em V): para-brisa → CodigoAtendimento nasce no GET após
   `POST /questionarios`; lataria → após o PATCH, sem questionário.
4. O questionário do para-brisa Yelum tem 3 perguntas: posição (5) · maior/menor que 10 cm (8) · sensor de
   direção/faixa (140, tipo P). 📊 NÃO perguntou chuva, degradê, antena, aquecimento. A régua "10 cm" VEM do portal.
5. `ScriptFinalizacao` REESCREVE a si mesmo: só vale lido DEPOIS de opcoes-disponiveis (PossuiOrdemServico=true).
6. Contato: 3 de 4 capturas gravaram telefone `Tipo 21 = CELULAR CORRETOR` ⇒ `PossuiTelefoneRecebeWhatsapp:false`:
   o segurado não recebe nada do portal e a loja liga para a corretora. `Tipo 20 = CELULAR SEGURADO`: 0 exercícios.
7. `POST agendamentos` / `POST direcionamentos`: continuam com ZERO exercícios (a agenda antiga deu `Blocos: []`).
8. `GET /seguradoras/` = 38 itens, sem campo Ativo (a inatividade vem no NomeFantasia: "(INATIVO)").
```

## 2. O FIO

```
WhatsApp → app/core/prompts.py (bloco vidros) → app/services/perguntas_do_portal_de_vidros.py:o_que_falta
 → app/agents/tools/portal_params.py:build_portal_params   (TRANSPORTAVEIS cobra cidade_para_o_servico)
 → app/agents/tools/portal_tool.py:_arun                   (portal_jobs + work_run + _idempotency_key + freio por job)
 → portal_worker/worker.py:_run_job                        (motivo_para_barrar com job/cpf_hash)
 → journeys/vidros_lanternas.py:abrir_atendimento → journeys/vidros_apifirst.py:abrir_atendimento_api
     GET /seguradoras (slug por DADO) → GET /apolices (preflight) ── fronteira A ── POST /atendimentos
     → PUT corretores → POST solicitantes → GET itens-cobertos/motivos-dano/ufs/cidades/clientes-cidades
     → [L: fronteira B AQUI] PATCH /atendimentos → [V: questionário → regras-reparo → fronteira B → POST /questionarios
        → (se diálogo) PUT alterar-reparo] → GET opcoes-disponiveis → GET /atendimentos (ScriptFinalizacao válido)
     → conclusão: POST emitir-atendimento-formalizado · agenda: consultar-distancias + datas + horários (LEITURA)
     → evidence["desfecho"]
 → app/agents/tools/portal_params.py:format_result / app/tasks/vigia_do_portal.py:diagnosticar → WhatsApp
 → resposta desconhecida → needs_human + dossiê → app/services/tela_cega.py:registrar_tela_cega (pela vigia/tool)
```

## 3. Unidades

| unidade | dono | estado ao fechar |
|---|---|---|
| P0-1 PATCH (8 chaves, regra por campo) · P0-2 corretores+solicitantes · P0-3 fronteira por categoria | A | no ar atrás da flag |
| P0-4 seguradora POR DADO: o slug sai de `GET /seguradoras/` ao vivo (casando nome↔NomeFantasia/slug + apelidos medidos); as listas velhas morrem | A (+C consome) | no ar |
| P0-5 slot `cidade_para_o_servico` + as três verdades reconciliadas | C | no ar |
| P0-6 freio por JOB (`PORTAL_CANARIO_ALLOWLIST`, só ESTREITA) | C | no ar |
| **N-1 (novo)** o DESFECHO lido do roteador do portal (conclusão · agenda · analista · vistoria · desconhecido) | A | no ar |
| **N-2 (novo)** o REPARO: `regras-reparo` + `alterar-reparo`, decisão do segurado coletada ANTES (`aceita_reparo`) | A + C | no ar (medido 1×, `Reparo:true`) |
| **N-3 (novo)** contato no portal: solicitante = Corretor ("6"), telefone/e-mail DO SEGURADO (D-E00110-01) | A + C | no ar; `Tipo 20` provado só no canário |
| P1-1 lojas, distância, dias, horários APRESENTADOS (leitura) | A + C | no ar |
| P1-2 `POST agendamentos`/`direcionamentos` | A | escrito, CANDIDATE, **não sai** (G7) |
| P1-3/P1-4 perguntas por família + restrição pelo catálogo da apólice | C (perguntas) + A (catálogo) | famílias de catálogo no ar |
| P1-5 lataria até o comprovante (multi-peça) | A | no ar |
| P1-6 vistoria/fotos multipart | A | escrito e desligado |
| P2-1 régua do trincado vem do portal · P2-2 cancelar (medido 2×) / abandonar (CANDIDATE) | A | cancelar no ar como função; journey própria só se couber |
| P-PILOTO-02 work_run + agent_id + protocolo durável · P-PILOTO-08 fila de aprendizado | C | no ar |
| `_idempotency_key` lido e nunca escrito (achado do BLOCO 0) | C | no ar |
| CANÁRIO (lataria Yelum) | 🧑 + 🤖 | roteiro pronto; depende de Implantar + veículo de teste (CLAUDE.md §10-5) |

**Sai (com gatilho):** domicílio (`transportes-proprios/*`, captura com `AtendeServicoMovel:true`) · `PATCH finalizar` · roda/pneu ·
polimento de farol · livre escolha (`DireitoLivreEscolha:true`) · 2º motor `atendimentos/respostas` · Bradesco escrita (D-PILOTO-17) ·
reescrever o caminho DOM. ⛔ Zero linhas para `agendeseuservico.com`.

## 4. Arquivos por builder (DISJUNTOS)

```
A  backend/portal_worker/journeys/vidros_api.py · vidros_sessao.py · vidros_estado.py · vidros_apifirst.py ·
   vidros_questionario.py · vidros_lanternas.py (só o mínimo) · backend/portal_worker/adaptive.py (só se preciso)
   backend/tests/test_o_fio_do_portal_de_vidros.py · test_e00110_a_*.py · backend/tests/fixtures do replay
C  backend/app/agents/tools/portal_params.py · portal_tool.py · backend/app/core/prompts.py ·
   backend/app/services/perguntas_do_portal_de_vidros.py · backend/app/tasks/vigia_do_portal.py ·
   backend/portal_worker/journeys/__init__.py · backend/portal_worker/worker.py · backend/tests/test_e00110_c_*.py
```

## 5. 🔴 O CONTRATO A ↔ C (os dois constroem contra isto)

**C → A, em `portal_jobs.params`** (chaves novas; as antigas não mudam):
```
local.cidade_servico ....... {"uf": "SC", "cidade": "Joinville"}     texto do segurado; A resolve CodigoCidade por /ufs→/cidades
especificos.aceita_reparo .. "sim" | "nao" | ausente                  `regras-reparo` é LEITURA e roda ANTES da fronteira B.
                                                                      Portal oferece reparo + resposta ausente ⇒ A PARA ali
                                                                      (needs_human, stage "decidir_reparo"), nada materializado
dano.pecas_lataria ......... ["porta dianteira esquerda", …]          só lataria; A casa com servicos-itens
contato .................... {"relacao": "6", "telefone": …, "tipo_telefone": "segurado"|"corretora", "email_segurado": …,
                              "email_corretora": …, "nome_solicitante": …, "documento_corretor": …}   tudo vem do banco/perfil
_idempotency_key ........... a mesma chave de `chave_de_idempotencia`
_conversation_id / work_run_id  (C grava no job; A só repassa em evidence)
```
**A → C, em `evidence["desfecho"]`** (e `captured` espelha `tipo`, `protocolo`):
```
tipo ............. "loja_direta" | "agenda" | "analista" | "vistoria" | "desconhecido"
codigo_atendimento (8 díg.) · franquias [{titulo, valor}] · reparo (bool|None) · link_area_segurado
loja ............. {nome, endereco, referencia, telefone, orientacao}          (loja_direta)
lojas ............ [{nome, endereco, cidade, uf, distancia, tempo, dias:[…], horarios:{dia:[…]}, tem_agenda}]   (agenda)
titulo_portal .... o Titulo do ScriptFinalizacao, literal
roteador ......... as chaves booleanas de opcoes-disponiveis (para o dossiê e o aprendizado)
```
`tipo == "desconhecido"` ou qualquer resposta fora do contrato ⇒ `needs_human` + `evidence["tela_desconhecida"] = {onde, resumo_mascarado}`;
C transforma isso em dossiê + `registrar_tela_cega(ramo="vidros")`.
**Seguradora:** `API.resolver_seguradora(nome, lista_ao_vivo) -> {"slug","codigo","nome_de_tela"} | None` e
`API.apelidos_de_seguradora()`; `portal_params.normalize_insurer` passa a ler dali (import de `portal_worker.journeys.vidros_api`,
que existe na imagem do smith-api — 📊 `backend/Dockerfile:11 COPY . .`; o inverso NÃO: o portal-worker não tem `app/`).

## 6. Gates

```
G1  replay OFFLINE do HAR de lataria (por trafego.importar_har): 5 escritas contratadas na ordem, as 2 fora NÃO saem,
    PATCH com as 8 chaves exatas. Mutações: +`ItemRemovido:None` · −`CodigoZona` ⇒ VERMELHO
G1b replay do HAR do PARA-BRISA: questionário 3 rodadas → regras-reparo → POST /questionarios → alterar-reparo{Reparo:true}
    → opcoes-disponiveis → desfecho "loja_direta" com a loja do ScriptFinalizacao lido DEPOIS. Mutação: ler o script antes ⇒ VERMELHO
G1c replay do HAR ANTIGO (vidro de porta): desfecho "agenda", 1 loja, distância, dias; NENHUM POST agendamentos
G2  "…|L" arma a fronteira antes do PATCH · "…|V" antes do POST /questionarios · constante fixa ⇒ VERMELHO
G3  slug por DADO: toda seguradora da lista medida (38) resolve para o próprio slug; nome fora da lista ⇒ None;
    "yelum"→LIBERTY · "sompo"→SOMPO (o bundle `sompo`→GRUPO_HDI é ROTA de SPA, documentado) · ITAU ⇒ None
G4  sem cidade_para_o_servico o job não nasce (par: com ela, nasce) · o prompt não ENUMERA campos
G5  freio por job: allowlist com 1 job ⇒ o listado passa, o outro é barrado COM motivo; allowlist vazia = hoje
G6  lataria não oferece loja nem domicílio porque o PORTAL disse (mutação: inverter o roteador no dublê ⇒ oferece)
G7  agendamentos/direcionamentos CANDIDATE: não saem com tudo ligado; promover sem captura ⇒ VERMELHO
G8  as perguntas do .docx da Regina casam com slot existente (contagem do builder vence)
G9  resposta/tela desconhecida ⇒ needs_human + dossiê + 1 linha em tela_cega (dois tenants, isolados)
G10 🧑 canário de lataria — roteiro entregue; execução depende do Founder
G11 tabela seguradora × estado no relatório, uma linha por seguradora medida
```

## 7. Decisões tomadas na conversão (nota 0–100)

| # | decisão | notas |
|---|---|---|
| D-E00110-01 | **Contato no portal:** solicitante declarado **Corretor ("6")** (é a verdade: quem abre é a corretora, e ela recebe cópia por e-mail), com **celular e e-mail DO SEGURADO** como contato (`Tipo 20`), porque é o segurado que a loja precisa achar para agendar e é ele que o portal notifica | segurado como contato + corretor declarado **88** · tudo da corretora (hoje) 60 — 📊 o portal marca `PossuiTelefoneRecebeWhatsapp:false` e a loja liga para a corretora · declarar "O Próprio" 45 — declaração falsa |
| D-E00110-02 | **Reparo × troca:** a pergunta entra na COLETA ("se a seguradora oferecer reparo grátis em 30 min, você aceita tentar?") só quando a família é para-brisa; sem resposta e com oferta do portal ⇒ para ANTES da fronteira B e pergunta | coletar antes **90** · decidir pelo segurado 10 · sempre troca 30 |
| D-E00110-03 | **Seguradora por dado ao vivo**, apelidos só como dica | ao vivo **92** · tabela de 38 no código 70 · 3 slugs (hoje) 5 |
| D-E00110-04 | **Canário:** fica na caixa do Founder com roteiro pronto; a SPEC entrega tudo verde offline sobre 3 HAR reais. Motivo: exige Implantar + veículo/CPF de teste (CLAUDE.md §10-5) | entregar + roteiro **85** · esperar o Founder com a branch aberta 40 |
| D-E00110-05 | Bradesco entra na lista por dado, mas o API-first devolve `None` para ele (D-PILOTO-17) | **90** × tratar como as outras 55 |

## 8. O que o estado da arte faz, e o que modelamos
As 6 referências (HAR 1.2 W3C `https://w3c.github.io/web-performance/specs/HAR/Overview.html` · RFC 5789
`https://www.rfc-editor.org/rfc/rfc5789` · Stripe idempotency `https://docs.stripe.com/api/idempotent_requests` · Pact
`https://docs.pact.io/` · VCR.py `https://vcrpy.readthedocs.io/` · har-to-openapi) estão na proposta §13, cada uma com
o que se modela, o que se rejeita e como o juiz inspeciona. Não se pesquisa de novo na execução.
