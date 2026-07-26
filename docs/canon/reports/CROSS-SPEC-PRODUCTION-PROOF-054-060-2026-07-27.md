---
> **Status:** relatório do Bloco 0 da SPEC-061 — Cross-SPEC Production Proof Gate
> **Branch:** `feat/spec060-research-intelligence`
> **Commit inicial:** `29c0053` · **Data:** 27/07/2026
---

# Bloco 0 — o que a produção provou, e o que ela desmentiu

## 1. A frase que resume o bloco

O produto estava funcionando **e sem deixar rastro**. Havia 43 Work Runs
concluídos, 104 etapas e 423 eventos — e, ao mesmo tempo:

```text
work_attempts    = 0
tool_invocations = 0
usage_events     = 0
artifacts        = 0
```

Não era coincidência nem tabela nova esperando uso. Eram **três causas
diferentes**, e duas delas eram defeito real.

---

## 2. FATO — o que foi encontrado e provado

### 2.1 `work_attempts` não tinha writer nenhum

Nenhuma linha do código escrevia nessa tabela. Pior: a docstring de
`executar_passo` dizia, em `services/work/workflows.py`:

> "Roda uma etapa registrando início, fim, **tentativa** e progresso."

A tentativa nunca era registrada. `work_steps` guarda o **estado final** de uma
etapa; sem a tentativa, uma etapa que só passou na quarta vez é
**indistinguível** de uma que passou de primeira.

Quem paga esse custo é quem precisa diagnosticar: o Founder olhando um trabalho
lento, e o Cockpit da SPEC-061 — que governa exatamente estes objetos.

### 2.2 `tool_invocations` tinha writer, e ninguém o chamava

`ToolGateway.registrar_invocacao()` e `finalizar_invocacao()` estavam escritos
e **sem um único chamador** no repositório inteiro.

O Gateway decidia *quais* ferramentas o agente recebia — isso funcionava — e
depois **perdia a chamada de vista**: a execução acontecia no `tool_node` do
LangGraph, que não falava com ele.

Consequência concreta: o corretor diz "ele não conseguiu consultar a apólice" e
não havia como saber se a ferramenta falhou, se foi negada por capability, ou
se o modelo simplesmente nunca a chamou.

### 2.3 `usage_events = 0` e `artifacts = 0` NÃO eram defeito

Os 43 Work Runs são **todos** workflows internos de inteligência:

| workflow | runs |
|---|---|
| `intelligence.detect_signals` | 30 |
| `intelligence.measure_outcomes` | 6 |
| `intelligence.garimpo` | 2 |
| `intelligence.daily_briefing` | 2 |
| `intelligence.cluster_demand` | 1 |
| `system.healthcheck` / `test.wf` | 2 |

Eles leem o banco da própria corretora e **não chamam provider pago nenhum**.
Zero consumo é o número correto: não havia chave de Tavily configurada e o
Firecrawl estava sem crédito. Zero Artifact também: nenhuma peça foi pedida.

> Este é o tipo de distinção que o Bloco 0 existe para fazer. Duas tabelas
> zeradas por defeito, duas zeradas por verdade. Tratar as quatro igual teria
> produzido correção onde não havia problema — e nenhuma onde havia.

### 2.4 Security Advisor: 1 ERROR → 0

`public.v_gateway_cutover_progresso` era `SECURITY DEFINER` e concedia
`SELECT, INSERT, UPDATE, DELETE, TRUNCATE` a **`anon` e `authenticated`**.

A tabela base `tool_gateway_shadow_diffs` tem RLS ligada e zero policy — ou
seja, ela **barrava** corretamente esses papéis. A view, por ser SECURITY
DEFINER, executava com os poderes do dono e **contornava exatamente essa
barreira**.

Quem tivesse a chave pública do projeto — que por definição vive no navegador —
lia pela view o que a tabela negava: quantas decisões o Gateway toma por dia,
em quantas ele diverge do caminho antigo, quantas dão erro.

**Corrigido** (`20260727_03`): `security_invoker = on`, `revoke` de `anon`,
`authenticated` e `public`, `grant select` só a `service_role`.

Saída real do Advisor depois:

```text
ERROR: 0 | WARN: 0 | INFO: 97
```

Os 97 INFO são `rls_enabled_no_policy` — o **deny-all deliberado** de
CLAUDE.md §7, não uma pendência.

### 2.5 A cadeia completa é aceita pelo schema real

Canário em Amandus (`3aa75902…`), bloco encerrado com `raise exception` —
**nada persistido**:

```text
CANARIO_BLOCO0 || ACEITOU: work_run work_step
                           work_attempts(1=falha,2=sucesso)
                           UNIQUE(step,numero) tool_invocation
               || PROBLEMA: nenhum
```

Descoberta lateral: `work_runs` tem
`CHECK (thread_id = 'work:' || company_id || ':' || id)`. A thread de um
trabalho **não consegue** ser escrita fora do escopo da corretora — é isolamento
por constraint, não por convenção.

### 2.6 Testes

`test_bloco0_auditoria_execucao.py`, 10 grupos, todos verdes. Prova, entre
outras coisas, que:

- a tentativa carrega duração, worker e o instante de término;
- erro de rede é `retryable`, `TypeError` **não** é (repetir produz o mesmo erro
  e queima a fila);
- a mensagem do erro é **redigida** — uma exceção de provider carrega URL com
  query string, e query string carrega chave;
- na retomada, a segunda tentativa é a de número **2** e a etapa continua sendo
  **uma**;
- com o registro de auditoria falhando, a etapa **ainda entrega**;
- o resumo da invocação guarda a *forma* da chamada, nunca CPF, telefone ou o
  conteúdo do resultado.

**Gate: 30/30 verde** (era 29/29; +`AUD-01`). **`npx tsc --noEmit`: exit 0.**

---

## 3. CORRIGIDO — o que mudou no código

| Arquivo | Mudança |
|---|---|
| `services/work/workflows.py` | `_abrir_tentativa` / `_fechar_tentativa` / `_localizar_step` / `_redigir`. Toda etapa passa a gravar a tentativa |
| `services/skills/invocation_recorder.py` | **novo.** Amarra a execução da ferramenta aos métodos que já existiam no Gateway |
| `agents/nodes.py` | o `tool_node` executa dentro de um `with` de registro — ponto único, para que a próxima ferramenta não nasça sem auditoria |
| `agents/gateway_cutover.py` | 7 nomes que faltavam no mapa (research e intelligence) |
| `services/research/providers.py` | `TavilyProvider.extract` e `.crawl` — `operacoes` declarava `extract` e o método não existia |
| `services/research/provider_router.py` | `tavily_extract` como degrau intermediário + política de roteamento declarada |
| `supabase/migrations/20260727_03` | view do cutover fechada |
| `supabase/migrations/20260727_04` | 4 índices dos read models da 061 |

### O elo do Gateway, em uma frase

Registrar no `tool_node` — e não dentro de cada ferramenta — é o que impede que
a **próxima** ferramenta nasça sem auditoria: quem esquecer de instrumentar
continua registrado, porque o ponto de execução é um só.

### Firecrawl deixou de ser o único degrau acima da leitura direta

A hierarquia de leitura era `direct_fetch → firecrawl`: o mais barato e depois
**o mais caro**, sem nada no meio. Agora:

```text
direct_fetch  → tavily_extract → firecrawl
(grátis)        (barato)         (último recurso)
```

`crawl` ganhou teto absoluto (`TETO_DE_CRAWL = 50`), profundidade limitada e
fronteira de domínio — crawl que sai do site pedido vira varredura da internet,
e ninguém orçou isso. Ele **não** entra em rota automática.

`Research` (pesquisa profunda do Tavily) também **não** entra em rota
automática: é minutos e créditos por pergunta, e uma pergunta de rotina que caia
nele transforma custo previsível em conta surpresa.

---

## 4. NÃO PROVADO — e por que

Sou obrigado a ser exato aqui, porque a diferença importa.

| Item | Estado | Motivo |
|---|---|---|
| Work Run real ponta a ponta **em produção** com attempt + invocation gravados | **NÃO PROVADO** | não há `.env` local nem endereço da API implantada no repositório; não consigo dirigir o serviço daqui |
| Tavily Search/Extract com chamada real | **NÃO PROVADO** | idem — a chave está no ambiente do serviço, não aqui |
| Comparação `basic` × `advanced` medida | **NÃO PROVADO** | exige chamada real; a política foi escrita, a medição não |
| Google Places com chamada real | **NÃO PROVADO** | idem |
| Artifact canônico real com render e MinIO | **NÃO PROVADO** | exige o backend rodando |
| Radar instalado em Amandus | **NÃO PROVADO** | a instalação chama `POST /api/research/radar/install` no backend |
| Memory Fabric ponta a ponta | **NÃO PROVADO** | exige conversa real |

**O que foi provado no lugar:** que o código escreve as linhas certas (teste com
banco falso que honra as UNIQUEs reais) e que o **schema de produção aceita
exatamente essas linhas** (canário revertido). É prova de contrato, não de
execução.

> Não afirmo que funciona porque existe código. Afirmo que o contrato está
> correto dos dois lados e que a execução falta ser observada.

### O que o Founder precisa rodar para fechar isso

Com a API e o worker no ar, uma conversa no dashboard de Amandus que use uma
ferramenta (por exemplo: *"o que precisa da minha atenção hoje?"*). Depois:

```sql
select count(*) from public.tool_invocations;   -- esperado: > 0
select count(*) from public.work_attempts;      -- esperado: > 0 após um tick
```

Se continuarem em zero **depois do deploy deste commit**, aí sim é defeito novo.

---

## 5. Git e migrations

### 5.1 Sincronização

```text
branch      feat/spec060-research-intelligence
HEAD        29c0053  (SPEC-060)
origin/main 92e5cc0
```

A SPEC-060 **não estava publicada**. Varredura de segredo no diff completo
(`origin/main...HEAD`, 44 arquivos, 11.361 linhas) e no histórico desde
01/07/2026:

```text
padrões de chave (tvly-, AIza…, fc-, sk-, eyJ…, BEGIN PRIVATE): 0 ocorrências
menções encontradas: apenas os NOMES das variáveis
  TAVILY_API_KEY · FIRECRAWL_API_KEY · GOOGLE_PLACES_API_KEY
```

Sempre lidas de ambiente (`os.getenv` / `settings`), nunca literais.

### 5.2 Migrations

| Arquivo | SPEC | Aplicada | Verificada | Rollback |
|---|---|---|---|---|
| `20260727_01_spec060_research_foundation.sql` | 060 | sim | 7/7 garantias | por objeto |
| `20260727_02_spec060_auxiliar_radar.sql` | 060 §37 | sim | sim | por `slug` exato |
| `20260727_03_seguranca_view_cutover.sql` | Bloco 0 §7 | sim | sim + Advisor | reversível |
| `20260727_04_indices_read_models_061.sql` | Bloco 0 §19 | sim | 4/4 índices | `drop index` nomeado |

Nenhum rollback usa `LIKE` amplo. O de seed atua por chave exata — a lição do
CA-016, onde um `delete ... like 'research.%'` teria apagado o catálogo em uso.

---

## 6. Índices (§19)

O levantamento cruzou as consultas previstas pelo Cockpit da SPEC-061 com os
índices existentes. **Já existiam** os de `work_runs (company_id, status)`,
`work_steps (work_run_id)`, `work_attempts (work_step_id)`,
`tool_invocations (work_run_id)`, `artifacts` e os de `research_*`.

Faltavam quatro, todos com a mesma forma — *filtra por corretora, ordena por
tempo decrescente*:

| Índice | Consulta que atende |
|---|---|
| `ix_work_runs_company_recente` | "últimos trabalhos desta corretora" |
| `ix_work_attempts_company_status` | "onde falhou e quantas vezes tentou" |
| `ix_tool_invocations_company_recente` | "quais ferramentas usou, quais falharam" |
| `ix_usage_events_company_recente` | "quanto consumiu no período" |

**Custo antes/depois: não mensurável hoje.** Três dessas tabelas estão com zero
linhas; com tabela vazia o plano usa Seq Scan de qualquer jeito e o número seria
sem significado. Foram criados **agora** porque com a tabela vazia a criação é
desprezível — depois, com volume e o Admin em uso, exigiria `CONCURRENTLY` e uma
janela. Nenhum outro índice foi criado.

---

## 7. Baseline do Admin para a SPEC-061 (§20)

Medido em 27/07/2026:

| Métrica | Valor |
|---|---|
| Páginas em `app/admin/` (não dinâmicas) | **39** |
| Com link no menu | **24** |
| **Órfãs** | **9** |
| Rotas em `app/api/admin/` | **114** |
| Arquivos do Admin usando `localStorage` | **2** — `layout.tsx` e `login/page.tsx` |

As 9 órfãs: `/admin/agent`, `/admin/billing`, `/admin/conversation-logs`,
`/admin/conversations`, `/admin/costs`, `/admin/documents`,
`/admin/integrations`, `/admin/logs`, `/admin/team`.

Elas já estão nomeadas em `ORFAS_ANTERIORES_A_SPEC059` e cobradas pelo caso
`NAV-01` do gate, que **impede a lista de crescer**. A correção estrutural
pertence à SPEC-061 — nenhum remendo provisório foi feito.

**114 rotas de API para 39 páginas** é a evidência quantitativa do que o Founder
relatou como "Admin confuso": 2,9 rotas por tela.

---

## 8. RISCO ACEITO

| Risco | Por quê é aceitável |
|---|---|
| Registro de invocação adiciona 2 consultas na primeira chamada de cada ferramenta | há cache de processo por `tool_key`; o catálogo muda por deploy, não por turno |
| Falha do registro é engolida (log, não exceção) | perder auditoria é ruim; perder o trabalho do corretor é pior. Testado em `[5]` e `[8]` |
| `tavily_extract` entrou na hierarquia sem medição real | é estritamente mais barato que o degrau que ele antecede; o pior caso é cair no Firecrawl como antes |

---

## 9. DECISÃO DO FOUNDER NECESSÁRIA

### 9.1 Rotação das credenciais expostas (§6) — **ação física, só o Founder faz**

As chaves do Tavily e do Google Places foram expostas em conversa, e o endereço
MCP do Tavily continha a chave **na própria URL**. Trate como incidente, mesmo
com a conversa privada: URL com segredo vaza por histórico, log de proxy e
captura de tela.

**Tavily**

1. Gerar nova chave no painel.
2. Atualizar `TAVILY_API_KEY` na Smith API **e** no Smith Worker.
3. Reimplantar os dois.
4. Conferir por health check.
5. **Revogar a chave antiga** — este passo é o que fecha o incidente.
6. Parar de usar o endereço MCP com chave embutida.

**Google Places**

1. Criar nova chave.
2. Restringir **somente** à Places API (New) — como já foi feito na atual.
3. Restringir por IP do servidor; **nunca** liberar para uso no navegador.
4. Atualizar os dois serviços, reimplantar, validar.
5. Revogar a antiga.

**Já verificado por mim:** nenhuma das duas chaves aparece no Git, em migration,
em documentação ou em qualquer arquivo do repositório — nem no histórico.

O código nunca registra valor de chave: `providers.py` reporta apenas presença
(`configurado: true/false`) e a mensagem humana do motivo. Este bloco
acrescentou a redação de mensagens de erro antes de gravá-las
(`_redigir`), porque exceção de provider carrega URL com query string.

### 9.2 Reclassificação do D18 — proposta

Com Tavily configurado e `tavily_extract` na hierarquia, **Firecrawl deixa de
ser bloqueio** e passa a ser *provider opcional/premium*, para o site que nem o
Tavily lê. O suporte **não** foi removido, o status continua explícito
(`no_credit` ≠ erro genérico) e a fila continua retomável.

Nenhum plano foi comprado. A reclassificação formal em
`FOUNDER-DECISIONS.md` é decisão sua.

---

## 10. PENDÊNCIA

| Item | Onde fecha |
|---|---|
| Observar attempt/invocation gravados em produção | após o deploy deste commit |
| Canários de Tavily, Places, Artifact, Radar e Memory | exigem a API no ar; roteiro na §4 |
| `basic` × `advanced` medido | quando houver chamadas reais |
| 9 páginas órfãs e as 114 rotas do Admin | SPEC-061 |

---

## 11. Conclusão

**O sistema está apto a entrar na SPEC-061** — com uma ressalva nomeada.

O que a SPEC-061 exige das 054–060 é que os objetos que ela vai governar
**existam e sejam confiáveis**. O Bloco 0 encontrou dois que não seriam
confiáveis: um Cockpit construído hoje mostraria "0 tentativas" e "0 chamadas de
ferramenta" e o operador concluiria, errado, que o sistema não trabalha.

Esses dois foram corrigidos na causa. O terceiro achado — a view aberta a
`anon` — era exposição real e foi fechada.

A ressalva: a prova é **de contrato**, não de execução em produção. Falta um
turno de conversa real depois do deploy. É um passo do Founder, e está escrito
na §4 com o SQL exato de conferência.

### Declaração

Nenhum motor paralelo foi criado. O registro de invocação **chama** os métodos
que já existiam no `ToolGateway`; a tentativa é escrita pelo `executar_passo`
que já existia; a hierarquia de leitura ganhou um degrau, não um segundo
router; os índices atendem consultas existentes.
