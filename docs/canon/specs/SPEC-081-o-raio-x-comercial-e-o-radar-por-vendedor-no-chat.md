---
status: "PRONTA PARA EXECUÇÃO — escrita em 18/08/2026, para apresentação em 19/08/2026"
spec: "SPEC-081"
titulo: "O Raio-X Comercial e o Radar por vendedor nascem de uma frase no chat"
criada_em: "2026-08-18"
branch_sugerida: "feat/spec081-raio-x-comercial-e-radar-por-vendedor"
repo: "Amandico100/AutoBrokers-Intelligence-OS · pasta AutoBrokers-FIX"
baseline_observada: "db2d9f12c90311ee45a26f66ba5aa10716a27cb1 (feat/spec078-cobranca-funciona-e-entrega-aparece)"
supabase_producao: "dcajcvlzcjbmyapmklil"
depende_de: "SPEC-057 (Artifact Hub e Brand Fabric — CONSUMIDOS, nunca alterados) · SPEC-056 (Tool Gateway) · SPEC-014/016 (conector InfoCap — LIDO, nunca alterado) · SPEC-065 (arquitetura de carteira — CORRIGIDA nesta SPEC, ver §2.3)"
deploy_esperado: "smith-api (backend). ZERO mudança em app/, middleware.ts, next.config.js — logo, o gate do CLAUDE.md §9.1 não se aplica (mas roda mesmo assim, ver §19)."
migration_esperada: "NENHUMA. Duas linhas de DML em brand_assets/brand_profiles (§Bloco E), com UNDO escrito antes."
custo_de_api_esperado: "Zero a US$ 0,006 por relatório. O caminho determinístico não chama LLM; o veredito opcional é UMA chamada curta (📊 US$ 0,00285 é o custo médio de uma chamada de chat, token_usage_logs, 30 dias, 18/08/2026)."
restricao_absoluta: "Atendimento e Auxiliar de Cobrança são INTOCÁVEIS. §Bloco G prova."
---

# SPEC-081 — O Raio-X Comercial e o Radar por vendedor nascem de uma frase no chat

> **Resultado desta SPEC, em uma frase:** o Founder digita uma frase no chat do
> dashboard da Resulta e recebe **um link clicável** que abre um relatório
> visual com a logo da Resulta, os dados reais da InfoCap e os cruzamentos que
> **não existem em tela nenhuma da corretora** — quem vende, quanto rende,
> quanto custa; e quais renovações estão em jogo, **por período e por
> vendedor**.
>
> **Regra de ouro:** esta SPEC **não cria motor**. O Artifact Hub existe, o
> renderizador existe, os 17 blocos existem, os 9 gráficos existem, o
> visualizador de entregas existe, o conector da InfoCap existe e o agente do
> chat existe. Esta SPEC escreve **uma camada de dados, um punhado de funções
> puras e duas ferramentas** — e liga tudo ao que já está de pé.
>
> 🔴 **Restrição que organiza o documento inteiro:** o **Atendimento** e o
> **Auxiliar de Cobrança** têm apresentação amanhã e **não podem ser tocados**.
> O §Bloco G não é uma seção de cortesia: é um gate, com lista de arquivos,
> teste e linha de controle.

---

---

# 0.0 🔴 ERRATA MEDIDA — 18/08/2026, 07h. **LEIA ISTO ANTES DE QUALQUER BLOCO.**

> **Esta seção SOBREPÕE todo número e todo nome de campo que a conflitar, em
> qualquer parte do documento.** Onde o texto adiante disser outra coisa, vale
> o que está aqui.

A SPEC foi escrita a partir de uma investigação que **confundiu dois
endpoints**. Um juiz adversarial apontou a incoerência aritmética; eu fui
medir, e a medição achou mais do que ele apontou. CLAUDE.md §9.2: *medir vence
deduzir*. Tudo abaixo foi chamado de verdade na API em 18/08/2026, às 07h.

## A · Três campos que a SPEC usa NÃO EXISTEM em `/renovacoes`

O array `prod_docs[]` **embutido em `/renovacoes`** é uma versão REDUZIDA do
endpoint `/prod_docs` avulso. 📊 Os campos reais, lidos de uma linha:

```
tem:      agente · automat · cod_age · cod_pro · ordem · per_r · produtor · val_r
NAO tem:  indireto · nome_produtor · base_r · nome_agente · perpart · campo_base_r
```

Consequências, e cada uma é fatal sozinha:

| A SPEC diz | A API entrega | Onde aparece |
|---|---|---|
| `ordem == 1 and indireto is False` | **`indireto` não existe** | I5, §6, §A.2, §A.4, §B.x |
| `nome_produtor` | o campo é **`produtor`** | §A.2, §B.5 |
| `/renovacoes` traz `val_c` | 📊 **`val_c` é `None`** | §D.3 |

🔴 **O algoritmo correto é `ordem == 1`, e só isso.** Não há como distinguir
direto de indireto por este endpoint — e não é preciso: 📊 a soma por `ordem=1`
já bate com a comissão real, sem triplicar.

⚠️ E há uma divergência interna da API que precisa de guarda: 📊 uma linha com
`quant_produtores: 3` trouxe `prod_docs` com **2** itens. Trate `prod_docs`
como a verdade e `quant_produtores` como pista; nunca itere pelo contador.

## B · As duas populações são QUASE DISJUNTAS — 2,8%, não 92%

O §A.6 explica a diferença entre R$ 2.276.444 e R$ 3.094.963 dizendo que são
populações diferentes. **A explicação está certa; a magnitude estava errada, e
é por isso que o Gate A era impossível de ficar verde.**

📊 Medido, cruzando `nosnum`:

```
BI inivig-2025 ............ 3.272 documentos
RENOVACOES fimvig-2025 .... 3.536 documentos
na INTERSECAO .............   100      <-- 2,8% das renovacoes
```

O motivo é simples e devia estar escrito desde o começo: **apólice anual que
COMEÇA em 2025 TERMINA em 2026.** A população `fimvig-2025` é, em quase tudo, a
produção de 2024. Comparar as duas somas é comparar dois anos diferentes.

🔴 **Portanto: R$ 3.094.963 NÃO é um número de 2025 e não pode ser citado como
tal. Ele sai do documento.**

## C · O mapa de produtores precisa de QUATRO anos, e a cobertura é parcial

Como `/renovacoes` filtra por `fimvig`, cobrir a produção de um ano exige
varrer vários anos de vencimento. 📊 Medido com `fimvig` 2024+2025+2026+2027:
**8.894 apólices** no mapa `nosnum → produtor`.

⚠️ E não dá para pedir tudo de uma vez: 📊 a janela 2018-2032 devolve **HTTP
502**, o mesmo teto do `/documentos_bi`. Ano a ano funciona sempre — 8s, 4s e
3s por ano medidos.

E aqui está o achado que salva o relatório:

```
                       documentos   comissao          com produtor
BI 2025 tipo_doc=TODOS      3.272   R$ 2.276.444        41,4%   (comissao 70,6%)
BI 2025 tipo_doc=A          1.680   R$ 1.863.831        80,6%   (comissao 86,2%)
```

📊 **Filtrar `tipo_doc=A` na própria chamada dobra a cobertura de produtor.** O
que estava de fora eram endossos, propostas e afins — que nunca deviam ter
entrado num relatório de produção.

🔴 **INVARIANTE NOVA (substitui parte de I6):** a chamada ao `/documentos_bi`
usa `tipo_doc=A`. O filtro entra na REQUISIÇÃO, não depois — economiza metade
do payload e é o que torna o cruzamento viável.

🔴 **INVARIANTE NOVA — A COBERTURA VAI IMPRESSA NA PEÇA.** 📊 19,4% das apólices
não têm produtor identificado. Um relatório que soma 80,6% e se apresenta como
"o ano inteiro" mente por omissão. O bloco `callout` da peça diz, com número:

> *"1.354 das 1.680 apólices (80,6%) têm produtor identificado. O ranking cobre
> R$ 1,61 mi dos R$ 1,86 mi de comissão do período."*

## D · A CALIBRAÇÃO CORRETA — é esta que vira teste

📊 2025, `tipo_doc=A`, `data=INIVIG`, mapa de 4 anos de `fimvig`, `ordem=1`:

```
apolices ............... 1.680      novo 717  /  renovacao 963
comissao atribuida ..... R$ 1.606.265
produtores distintos ... 82
```

| # | Produtor | Apól | Comissão | Ticket | Repasse |
|---|---|---:|---:|---:|---:|
| 1 | RAFAEL L SILVEIRA-EXECUTIVO | 250 | 266.926 | 1.068 | 4,6% |
| 2 | **MARCOS TONIOLO - INDICADOR** | **7** | **261.565** | **37.366** | 3,0% |
| 3 | RAFAEL LACAU SILVEIRA - FECHADOR | 139 | 233.551 | 1.680 | 3,4% |
| 4 | LUIZ GUILHERME ARAUJO - FECHADOR | 101 | 191.493 | 1.896 | 3,3% |
| 5 | LUIZ GUILHERME - EXECUTIVO | 99 | 85.729 | 866 | 5,0% |
| 6 | OLIM IMOVEIS | 64 | 49.692 | 776 | **25,0%** |
| 7 | MARIANA SOUZA FECHADORA | 49 | 48.654 | 993 | **0,7%** |
| 8 | RAFAEL IRANI (CONDOMINIOS) | 16 | 47.753 | 2.985 | 20,0% |
| 9 | CONTATO ASSESSORIA CONDOMINIAL | 22 | 40.754 | 1.852 | 25,0% |
| 10 | KATLYN FECHADOR | 81 | 38.744 | 478 | 1,5% |

**Gate A passa a ser esta tabela.** Tolerância: ±1 apólice e ±R$ 500 por linha
(a API pode ter movimentação entre execuções); a ORDEM dos cinco primeiros é
exata.

## E · A manchete muda, e melhora

❌ **Some do documento:** *DVA BYD ITAJAI, 50,0% de repasse*. 📊 Não se reproduz
nesta população; o maior repasse medido é **25,0%**.

✅ **Entra no lugar, e é mais forte porque tem duas pontas:**

> 📊 **Sete apólices, R$ 261 mil.** O Marcos Toniolo fez 7 apólices em 2025 e
> gerou R$ 261.565 de comissão — ticket médio de **R$ 37.366**, trinta e cinco
> vezes o do primeiro colocado em volume. Volume e valor são coisas diferentes,
> e a corretora nunca teve como ver as duas na mesma tela.
>
> 📊 **E o repasse varia de 0,7% a 25%.** De cada real de comissão, um canal
> devolve um quarto e outro devolve menos de um centésimo. Esse número não
> existe em tela nenhuma hoje: ele mora em dois endpoints diferentes e só passa
> a existir quando alguém os cruza.

## F · O que fica INVALIDADO no resto do documento

| Seção | O que ignorar | O que vale |
|---|---|---|
| I5, §6, §A.2, §A.4, §B.x | `indireto` | só `ordem == 1` |
| §A.2, §B.5 | `nome_produtor` | `produtor` |
| §A.5 tabela de ranking | a tabela inteira | a tabela do §0.0-D |
| §A.5, §B.9 | 3.272 apólices · 2.301/971 | 1.680 · 717/963 |
| §A.6, §B.2, §B.9, §C.2, §15.6 | R$ 3.094.963 | R$ 1.606.265 |
| §B.3 | ticket bruto R$ 4.492,64 | ticket por produtor, tabela §0.0-D |
| §0.3, §C.4, §15.6 | 50,0% / DVA BYD | 25,0% / OLIM, e a manchete do §0.0-E |
| §D.3 | `val_c` vindo de `/renovacoes` | 📊 é `None`; vem do BI pelo `nosnum` |

🔴 **§C.2 e §15.6 são as seções que o Founder LÊ EM VOZ ALTA no palco.** Elas
citam três números brutos, e os três estão errados. Os corretos são os do
§0.0-D. **Nenhum número vai ao palco sem estar nesta errata.**

## G · O que o juiz achou e continua valendo

Além do acima, estes seguem abertos e **precisam de correção antes da
execução** — a errata não os resolve, só os registra:

1. **O `upsert` do §E.3 não funciona.** `brand_assets_one_current_per_kind` é
   índice PARCIAL (`WHERE is_current`); `ON CONFLICT (company_id, kind)` sem
   `WHERE` correspondente dá erro 42P10. Trocar por dois statements: `update …
   set is_current=false`, depois `insert` puro. E o UNDO do §E.5 precisa levar
   `is_published = false` junto.
2. **`visual_style='aurora'` vira INVARIANTE COM TESTE.** 📊 `service.py:187`
   resolve `estilo = pedido || MARCA.visual_style || template.visual_style` — a
   marca **vence** o template. Gravar `'meridian'` na captura trocaria o tema de
   **todas as peças do Auxiliar de Cobrança** em silêncio, no dia da
   apresentação.
3. **Preflight: dois SELECT de 60 segundos.** As linhas de `report_templates`
   para `commercial.pipeline` e `renewals.radar` existem? E o
   `agents.agent_role` do agente de atendimento da Resulta é mesmo
   `'attendance'`? (📊 `graph.py:528` faz `_agent_role or "core"` — papel NULO
   entraria como core e receberia as tools novas.)
4. **Plano de deploy e smoke test pós-deploy.** A SPEC não tem nenhum. O que
   será reconstruído é o `smith-api`, que carrega o webhook do WhatsApp e a
   Cobrança. Exige janela declarada, um round-trip vivo do Atendimento, uma
   varredura de cobrança, e commit de rollback pronto num terminal aberto.
5. **Onde roda o pré-aquecimento.** 📊 `config.py:53` traz `REDIS_URL` com
   default `localhost` — script rodado do laptop aquece um Redis que o
   `smith-api` deployado nunca lê.
6. **`stacked` não trunca rótulo** (📊 `charts.py:512`): nome de 32 caracteres a
   72 px de passo vira borrão, justamente no quadro "mix de ramo por vendedor".
   E o **`sources` mostra o label, não a hora** (📊 `blocks.py:363`) — a hora
   tem de ir DENTRO do `as_of_label`, como a Cobrança já faz.
7. **§D.3 viola a própria I6**: não cruza `/producao` nem filtra `tipdoc`. 📊 O
   `/renovacoes` TEM `tipdoc` e `cancelado` na própria linha — usar os dois de
   lá resolve sem nenhuma chamada extra.
8. **A circularidade do §2.4**: o preflight é entregável do Bloco A e é exigido
   antes de escrever a primeira linha dele.

## H · O que continua de pé, e é a maior parte

A arquitetura não mudou. 📊 Verificado arquivo por arquivo em 18/08:

- o despacho por `exige_async` funciona (`nodes.py:1084`);
- o registro de tool é fechado por papel e **não vaza para o Atendimento**
  (`graph.py:528`), e está dentro de `try/except` — tool nova que quebre ao
  carregar não derruba o chat;
- os **13 blocos** que a SPEC usa **existem** em `blocks.py`;
- **não há timeout** no caminho do chat (proxy Next, backend, uvicorn);
- a credencial da InfoCap responde em **1,8 s** com 17 permissões;
- o caminho de artifact da Cobrança (`criar → renderizar → publicar` com
  composição pronta em código) é o caminho certo, e tem 40 execuções provadas.

E o mais importante: **os dados existem e são bons.** 82 produtores, quatro
anos de histórico, ticket que varia 35× entre canais e repasse que varia 35×
também. O relatório tem o que mostrar.

---

# 0. Por que esta SPEC existe agora

## 0.1 O que o Founder pediu, textualmente

> *"Amanhã, na apresentação, eu quero digitar no chat e receber um link que
> abre um relatório bonito, com a logo da Resulta, com dados reais e
> cruzamentos."*

Dois relatórios:

**1. Raio-X Comercial** — *"quem vende, quanto rende, quanto custa"*: ranking
por comissão, ticket médio, custo de aquisição por canal, mix de ramo por
vendedor, novo vs renovação, comparação entre períodos.

**2. Radar de Renovações** — e aqui ele foi explícito, e a ênfase é dele:

> 🔴 *"TEM QUE SER POR PERÍODO, E SEPARADO POR VENDEDOR — quem tem mais
> renovações, comissões em jogo. NÃO do ano inteiro."*

Essa frase é a **invariante I3** desta SPEC (§4). Um radar anual, agregado, é
exatamente o relatório que a InfoCap já dá e que ele já disse não querer.

## 0.2 A ferramenta que existe nunca produziu nada — e por quê

📊 Medido em 18/08/2026, projeto `dcajcvlzcjbmyapmklil`:

```sql
select origin, count(*) from artifacts group by 1;
```

```text
routine   40
chat       0
```

**Quarenta artifacts em produção. Nenhum veio do chat.** A tool
`gerar_relatorio` existe desde a SPEC-057, está registrada no grafo
(📊 `backend/app/agents/graph.py:531`) e **nunca entregou uma peça**.

Três defeitos em série, todos medidos no código em 18/08/2026:

### Defeito 1 — ela cai no `_run`, que é um bilhete de desculpas

📊 `backend/app/agents/tools/report_tool.py:202-203`:

```python
    def _run(self, **_: Any) -> str:
        return "Esta ferramenta é assíncrona; o runtime deve chamá-la por `arun`."
```

📊 E o executor (`backend/app/agents/nodes.py:1084-1085`) decide assim:

```python
                        if (getattr(tool, "exige_async", False)
                                or tool_name in _TOOLS_SEMPRE_ASYNC) and hasattr(tool, "_arun"):
```

📊 `_TOOLS_SEMPRE_ASYNC` (`nodes.py:38-39`) é
`("delegate_to_subagent", "infocap_policy_lookup", "insurer_dispatch", "portal_action")`.
**`gerar_relatorio` não está lá, e não declara `exige_async`** — 📊 a única
declaração no repositório inteiro é `human_handoff.py:294`. Resultado: o modelo
recebe a string do bilhete e nenhum relatório é gerado.

### Defeito 2 — o modelo não preenche o payload

O `args_schema` da tool pede tipo, título, KPIs, seções, ações, fontes. É o
modelo que tem de inventar tudo — e é o que a nota 64 do §5 D1 registra: **ele
já provou que falha nisso.**

### Defeito 3 — sem `compartilhar=True` não sai link

Mesmo que os dois primeiros passassem, o link só nasce se o modelo pedir.

### A causa de fundo, que é a única que interessa

**A tool existente pede ao LLM que INVENTE o conteúdo do relatório.**

As duas tools desta SPEC fazem o oposto: **buscam, calculam e montam o artifact
em código determinístico.** O LLM só reconhece a intenção e copia o período que
o Founder escreveu. Isso é a decisão **D1** (§5), e é a espinha do documento.

## 0.3 O número que vale a apresentação

📊 Levantamento da InfoCap da Resulta, 18/08/2026 — custo de aquisição por
canal, calculado como repasse ao produtor dividido pela comissão da corretora
nas apólices em que aquele canal participa:

```text
RAFAEL EXECUTIVO   R$    61.280 repassado  sobre R$ 1.258.472   =   4,9%
DVA BYD ITAJAI     R$    57.855 repassado  sobre R$   115.089   =  50,0%
```

**Um canal fica com metade.** Esse número não existe em tela nenhuma da
corretora, nem na InfoCap, nem em planilha. Ele nasce de um cruzamento —
`prod_docs[].val_r` contra `val_c` — que ninguém faz porque ninguém tem por
onde fazer.

**É este número que justifica a SPEC.** Um ranking de vendedor a corretora já
tem. O custo por canal, não.

## 0.4 🔴 O que NÃO se pode concluir, e que já custou uma conclusão errada

> ⚠️ **Correção de leitura, obrigatória antes do Bloco A.**

📊 `backend/app/data/global_knowledge/infocap-corpapi-mapa.md:42-48` afirma:

```text
## Endpoints NEGADOS no perfil padrão (pedir liberação à corretora)

Financeiro completo: /parcelas, /comissao, /comissoes, /financeiro, /titulos,
/contas_receber, /contas_pagar, /fluxo_caixa, /faturamento.
Gestão: /vendedores, /usuarios, /propostas, /sinistro, /endossos, /tarefas,
/agenda, /cias, /filiais.
As permissões são flags do perfil de API do usuário InfoCap da corretora.
```

📊 **Isso está errado.** Aquelas rotas **não existem**. O 403 que elas devolvem
é o erro de rota inexistente do AWS API Gateway — vem com texto de assinatura
SigV4, e não com mensagem de permissão. Nenhuma flag `p5xx` precisa ser
liberada, porque não há o que liberar.

**A consequência dessa leitura errada foi cara:** a SPEC-065 inteira ficou
parada com o status *"bloqueada por terceiro"*, e sete auxiliares do catálogo
ficaram `coming_soon` esperando uma liberação que nunca ia chegar. 📊 O
`missing_for_launch` do auxiliar `caca-comissao`
(`backend/supabase/migrations/20260802_02_spec064_seed_catalogo.sql:224`) diz
literalmente *"API da InfoCap liberada para comissão (hoje bloqueada)"*.

**A comissão nunca esteve bloqueada.** Ela vem dentro do documento, nos campos
`base_c`, `per_c` e `val_c`. O Bloco A prova isso com número.

> **A lição, na forma do CLAUDE.md §9.2:** o 403 foi *deduzido* como permissão e
> nunca *medido* como rota. Uma requisição a uma rota inventada
> (`/rota_que_nao_existe`) teria dado o mesmo 403 e encerrado a hipótese em
> trinta segundos. **A linha de controle que faltava custou dezessete dias.**

Três documentos e uma SPEC precisam ser corrigidos — §Bloco H.2.

## 0.5 O que existe hoje, e o que falta

📊 Varredura de `backend/` em 18/08/2026:

| Peça | Estado |
|---|---|
| Artifact Hub (`criar` → `renderizar` → `publicar`) | ✅ **vivo**, 40 peças em produção |
| 17 blocos · 9 gráficos SVG · 3 temas | ✅ **prontos** e provados por `docs/canon/visual-acceptance/` |
| Template `renewals.radar` e `commercial.pipeline` | ✅ **existem** (`templates.py:259` e `:143`) |
| Visualizador `/dashboard/entregas/[artifactId]` | ✅ **funciona**, isolamento de tenant correto |
| Conector InfoCap por CPF (`lookup`/`detail`) | ✅ **vivo** |
| Serviço de comissão, ranking de produtor, ticket médio, mix de ramo | ❌ **NÃO EXISTE** — zero ocorrências de `val_c` e `per_c` no repositório |
| Tabela de apólice / carteira / renovação / produtor | ❌ **NÃO EXISTE** — 117 tabelas em `backend/supabase/migrations/`, nenhuma delas |
| Consulta InfoCap em LOTE (por período, não por CPF) | ❌ **NÃO EXISTE** — `InfocapLookupInput` só aceita CPF, nome ou apólice |
| Link de chat que abre relatório | ❌ **NUNCA aconteceu** (`origin='chat'` = 0) |

**O buraco é exatamente um: entre uma superfície de entrega que já está pronta
e uma fonte de dados que ninguém nunca consultou em lote.** Esta SPEC preenche
esse buraco, e nada além dele.

---

# 1. Autoridade — antes de tocar em uma linha

```text
CLAUDE.md (processo)
  §5   não criar motor paralelo        ← §3 desta SPEC responde item por item
  §7   multi-tenant                    ← §Bloco A.2 e §Bloco G
  §9   blocos com gate verificável
  §9.1 build verde ≠ aplicação sobe    ← §19
  §9.2 medir vence deduzir; controle   ← §0.4 é o exemplo caro
  §9.3 teste que guarda verdade vencida ← §Bloco H.2
  §12.1 📊 medido · 💭 ilustrativo
→ SPEC-052 · SPEC-053
→ SPEC-057 (Artifact Hub e Brand Fabric)   ← CONSUMIDOS. Ver a lista congelada em §Bloco G.1
→ SPEC-056 (Tool Gateway)                  ← a tool nova precisa de linha em NOME_PARA_CHAVE
→ SPEC-065 (carteira e dinheiro visível)   ← ⚠️ CONFLITA. Ver §2.3
→ docs/canon/ONTOLOGIA-DO-TRABALHO.md      ← §3: isto é Tool, não Auxiliar, não Rotina
→ docs/canon/GLOSSARIO.md
→ docs/canon/MIGRATIONS-AUTHORITY.md       ← só para confirmar: esta SPEC não tem migration
```

---

# 2. Preflight

## 2.1 O preflight de sempre

```bash
git rev-parse --show-toplevel      # .../AutoBrokers-FIX
git branch --show-current          # feat/spec081-raio-x-comercial-e-radar-por-vendedor
git rev-parse HEAD                 # registrar no relatório
git status --short                 # limpo ao iniciar
```

📊 Baseline desta SPEC: `db2d9f12c90311ee45a26f66ba5aa10716a27cb1`.
**Anote esse SHA.** O teste de não-regressão do §Bloco G o usa literalmente.

## 2.2 O preflight de estado

```sql
-- 1. O chat nunca entregou uma peça. Este é o número que a SPEC vira.
select origin, count(*) from artifacts group by 1;
-- ESPERADO hoje: routine 40 · chat 0

-- 2. A Resulta não tem marca. As 40 peças saíram genéricas.
select company_id, display_name,
       (palette->>'primary') as primaria, logo_asset_id, visual_style
  from brand_profiles;
-- ESPERADO hoje: 3 linhas, TODAS com primaria NULL e logo_asset_id NULL

-- 3. A conexão da InfoCap da Resulta está elegível?
select tc.id, tc.company_id, tc.status, tc.health_status,
       (tc.connection_config->>'base_url') as base_url,
       (tc.encrypted_secret_ref is not null) as tem_segredo
  from tenant_connections tc
  join connector_templates ct on ct.id = tc.connector_template_id
 where ct.slug = 'infocap';
-- ESPERADO: EXATAMENTE UMA linha elegível para a Resulta.
-- Duas linhas elegíveis => `ambiguous_connection` e a tool devolve erro.
```

## 2.3 🔴 O conflito canônico — resolver ANTES do Bloco A

**FATO.** 📊 `docs/canon/specs/SPEC-065-carteira-e-dinheiro-visivel.md`, linha 2:

```text
status: canônica · bloqueada por terceiro (API InfoCap responde 500)
```

e §1.3 (linha 82) lista `/comissao`, `/parcelas`, `/financeiro`, `/vendedores`
como **403 por permissão**, concluindo que *"sem liberação de flag `p5xx` pela
corretora, comissão da carteira é matematicamente impossível"*.

📊 **Os dois fatos venceram.** O levantamento de 18/08/2026 mediu, na InfoCap
da Resulta, quatro anos de produção, 16.693 linhas de documento e o repasse por
produtor — sem nenhuma flag nova. A tabela do §Bloco A.4 é a prova.

**INFERÊNCIA.** O motivo original do bloqueio era uma leitura errada do 403
(§0.4). Esta SPEC remove o motivo, e ao fazê-lo desbloqueia sete auxiliares do
catálogo que estavam presos à mesma premissa.

**RECOMENDAÇÃO — parada legítima, CLAUDE.md §10(3).** Antes do Bloco A, o
executor **registra em `FOUNDER-DECISIONS.md`** e obtém decisão explícita
sobre:

```text
D-a  A SPEC-065 sai de "bloqueada por terceiro"? (o bloqueio não existia)
D-b  O §1.3 da SPEC-065 e os dois mapas de InfoCap são corrigidos para dizer
     que aquelas rotas NÃO EXISTEM, e que a comissão vem no documento?
D-c  A SPEC-081 entrega a leitura em lote da InfoCap SEM criar o "espelho da
     carteira" que a SPEC-065 §B planejou — ou seja: consulta ao vivo com cache
     de curta duração, nenhuma tabela nova. (Ver §3 e §5 D5.)
```

> **Por que isto é parada e não nota de 0 a 100:** CLAUDE.md §9.3 —
> *"teste que guarda verdade vencida é pior que teste nenhum"*, e a mesma regra
> vale para documento canônico. Um `status: bloqueada` que já não é verdade
> ensina a ignorar o cabeçalho das SPECs. **Executar contra um canônico vencido
> sem corrigi-lo repete o defeito que custou dezessete dias.**
>
> **D-c é a que importa para amanhã.** Se a resposta for "faça o espelho", a
> apresentação de 19/08 não acontece: espelho é migration, backfill e Work Run.
> A recomendação registrada é **consulta ao vivo com cache**, e o espelho fica
> como P-224.

## 2.4 O preflight de rede — 📊 medir, nunca supor

Antes de escrever uma linha do Bloco A, rode e **cole a saída no relatório**:

```bash
python backend/scripts/preflight_infocap_bi.py --company <UUID_DA_RESULTA>
```

O script (é o primeiro entregável do Bloco A, §A.7) faz exatamente cinco
requisições e imprime o resultado de cada uma:

```text
1. POST /login                                     -> espera 200 + token
2. GET  /documentos_bi  (01/01/2026..31/12/2026)   -> espera 200 + N linhas
3. GET  /producao       (mesma janela, qtd_pag=5000, pag=1)
4. GET  /renovacoes     (dt_ini=hoje, dt_fim=hoje+90, qtd_pag=5000, pag=1)
5. GET  /rota_que_nao_existe   <-- 🔴 A LINHA DE CONTROLE
```

> **A quinta requisição é o que dá direito à conclusão.** Ela tem de devolver
> **403 com texto de assinatura SigV4** — provando que 403 nesta API significa
> *rota inexistente*, e não *permissão negada*. Sem essa linha, a correção do
> §0.4 é opinião. Com ela, é medição. (CLAUDE.md §9.2.)

**Se o passo 1 falhar com 500**, a P-01 de `PENDENCIAS.md` voltou e a SPEC para
aqui — é condição legítima de parada nº 8 (falta de acesso indispensável).

---

# 3. Ontologia — o que esta SPEC cria, e o que ela explicitamente NÃO cria

`docs/canon/ONTOLOGIA-DO-TRABALHO.md` faz três perguntas. As respostas:

| Pergunta | Resposta | Consequência |
|---|---|---|
| *Dois trabalhadores diferentes poderiam usar?* | sim, mas ninguém pediu | não vira **Skill** agora |
| *Cabe em "toda terça às 8h"?* | **não** — o Founder quer sob demanda | não é **Rotina** |
| *Aparece em "o que trabalha para mim"?* | **não** — é um pedido, não um trabalhador instalado | não é **Auxiliar** |
| *É a implementação técnica de um poder?* | **sim** | é **Tool** |

```text
O que esta SPEC cria:  DUAS TOOLS  +  uma camada de dados  +  funções puras
                       registradas no agente `core` que já existe
                       consumindo o Artifact Hub que já existe

O que NÃO cria:        runtime · scheduler · publisher · executor
                       Skill Registry · Tool Gateway · Artifact Hub
                       tabela de carteira · ETL · detector · tela nova
```

**Resposta item por item ao CLAUDE.md §5:**

| Peça proibida de duplicar | Esta SPEC | Prova |
|---|---|---|
| runtime | usa `graph.py`/`nodes.py` | duas linhas de `tools.append` |
| scheduler | **nenhum** | não há agendamento; o pré-aquecimento é um CLI que um humano roda |
| publisher | usa `ArtifactService.publicar` | §Bloco C.5 |
| Artifact Hub | **consome**, não altera | §Bloco G.1 congela os cinco arquivos |
| Tool Gateway | registra em `NOME_PARA_CHAVE` | §Bloco C.6 |
| conector InfoCap | **importa** `_resolve_infocap_connection`; **zero edições** | §Bloco A.2 e §Bloco G |
| espelho da carteira (SPEC-065 §B) | **NÃO faz** | decisão D-c do §2.3; vira P-224 |

> **Sobre o diretório novo `backend/app/services/comercial/`:** ele não executa,
> não agenda, não publica e não decide. É **um adaptador de leitura + funções
> puras + montadores de composição**. Nenhuma peça do runtime muda de dono, e
> nenhum dado é persistido fora de `artifacts`. Isso é o mesmo argumento que a
> SPEC-080 §C.2 usou para o Reconciliador, e vale pela mesma razão.

---

# 4. Invariantes — se uma delas quebrar, a SPEC falhou

```text
I1  ZERO alteração nos arquivos congelados do §Bloco G.1. Não por disciplina —
    por teste, com linha de controle que prova que o teste sabe ficar vermelho.

I2  Nenhum número do relatório é escrito pelo LLM. O código calcula; o LLM,
    no máximo, redige o VEREDITO a partir de números já calculados.

I3  🔴 O Radar é POR PERÍODO e POR VENDEDOR. Nunca do ano inteiro, nunca
    agregado sem a coluna do vendedor. Foi o pedido literal do Founder.

I4  Se a chamada de LLM do veredito falhar, o relatório SAI IGUAL, com o
    veredito determinístico. NUNCA sai sem relatório.

I5  Comissão soma apenas o produtor DIRETO (`ordem=1` e `indireto="F"`).
    Somar todos triplica o faturamento. 📊 Média de 3 produtores por apólice.

I6  Apólice CANCELADA não entra em número nenhum, e `tipdoc` diferente de `A`
    também não. As duas exclusões vêm do MESMO cruzamento com `/producao`.

I7  Nenhum dado de segurado (CPF, telefone, e-mail, placa, nome de pessoa
    física) entra no artifact nem no `payload`. Os dois relatórios são
    agregados por vendedor, canal e ramo — não precisam de PII para existir.

I8  Nenhuma janela de consulta maior que UM ANO. 📊 > ~6 anos devolve 502 aos
    28 s; ano a ano sempre funciona.

I9  Toda tool nova declara `exige_async: ClassVar[bool] = True`. Sem isso ela
    cai no `_run` e o modelo recebe um bilhete em vez de um relatório.

I10 Multi-tenant: `company_id` vem do construtor da tool (injetado pelo grafo),
    NUNCA do argumento que o modelo preenche. A chave de cache carrega
    `company_id`. Nenhuma consulta desta SPEC roda sem ele.
```

---

# 5. As decisões de arquitetura

## 5.1 As seis já tomadas — a SPEC documenta e executa

Estas **não são para reabrir**. Estão decididas, com nota. O que segue é o
**COMO**.

### D1 · O modelo escolhe O QUE fazer. O código FAZ. (nota 94)

📊 A tool `gerar_relatorio` nunca produziu um artifact (§0.2), e a causa de
fundo é que ela **pede ao LLM que invente o conteúdo**.

As tools desta SPEC buscam, calculam e montam a composição **em código
determinístico**. O LLM faz duas coisas e só duas: reconhece a intenção
("ele quer o Raio-X") e copia o período que o Founder escreveu ("de 2025").

Alternativas rejeitadas: tool genérica de consulta + LLM compõe (**nota 64** —
o modelo já provou que falha em preencher payload); Auxiliar com Rotina
(**nota 45** — o Founder quer sob demanda, não agendado; e Rotina é gatilho,
não pedido).

### D2 · Usa o caminho de artifact da COBRANÇA, não o `report_tool` (nota 96)

📊 `backend/app/services/billing_collection.py:1363-1396` faz
`ArtifactService.criar(payload=..., composition=blocos)` → `renderizar` →
`publicar`, **passando a composição pronta**:

```python
1375	    r = servico.criar(
1376	        company_id=company_id,
1377	        title=titulo,
1378	        template_key="financial.billing_collection",
1379	        payload=payload,
1380	        composition=blocos,
...
1392	    versao = (r.get("version") or {}).get("id")
1393	    if versao:
1394	        servico.renderizar(company_id=company_id, version_id=versao)
1395	        servico.publicar(company_id=company_id, version_id=versao)
```

📊 40 artifacts provados por essa via, 4 deles em 17/08/2026.

Isso contorna os três defeitos do `report_tool.py` de uma vez, e destrava os
**17 blocos e 9 gráficos** — 📊 `report_tool._compor()` só traduz 5 tipos de
seção (`_MAPA_SECAO`, `report_tool.py:117-120`: `tabela`, `ranking`, `rosca`,
`texto`, `alerta`), e **não alcança `chart`, `waterfall`, `funnel`, `stacked`,
`ring` nem `split`.** Nenhum gráfico temporal chega ao chat por aquele caminho.

⚠️ **Consequência a documentar:** `report_tool.py` continua quebrado. O
§Bloco H.1 conserta o `exige_async` dele — **uma linha** — mas é bloco
**separado e opcional**, e o caminho dos dois relatórios **não depende dele**.

### D3 · Duas tools, não uma com parâmetro `tipo` (nota 88)

Descrição crisp por tool ajuda o LLM a rotear. Uma tool com enum (**nota 74**)
concentra o risco na escolha do enum — e o enum é exatamente o tipo de campo
que o modelo erra (D1).

### D4 · O texto: código monta os números, LLM escreve só o veredito (nota 88)

O código calcula tudo e monta um **veredito determinístico de fallback**. Se
houver orçamento, **uma** chamada curta ao LLM reescreve o veredito a partir dos
números **já calculados** — nunca inventando número.

🔴 **Invariante I4:** se a chamada falhar, o relatório sai igual, com o veredito
determinístico. **Nunca sai sem relatório.**

### D5 · Cache, porque 45 segundos ao vivo é uma eternidade (nota 90)

📊 Medido: 4 anos de produção + carteira = **8-10 chamadas, ~45 s**. Latência
típica 0,7-1,0 s por chamada; lote grande, 4-9 s.

Cache em Redis por `(company_id, ano)`, TTL curto, **mais** um jeito de
pré-aquecer antes da apresentação. §Bloco F especifica os dois.

### D6 · A logo entra (nota 92)

📊 `brand_profiles` tem 3 linhas, **todas com `palette.primary = NULL` e
`logo_asset_id = NULL`**. Os 40 artifacts saíram com `is_fallback: true` —
paleta genérica (📊 `#2C6E8F` / `#D98324`, `brand/system.py:60-61`), sem logo.

📊 A logo real existe: `backend/tools/_resulta_logo.png`, **4.694 bytes**.

§Bloco E faz a Resulta ter marca de verdade, com passos exatos e UNDO escrito.

## 5.2 As quatro que esta SPEC decide agora, com nota

> CLAUDE.md, formato pedido: onde há dúvida genuína, nota de 0 a 100 e a maior
> vence, com o porquê. Nada disso vira parada.

### D7 · `template_key`: reusar os que existem — **nota 90**

| Opção | Nota | Por quê |
|---|---|---|
| **A — reusar `commercial.pipeline` e `renewals.radar`, passando composição própria** | **90** | 📊 `renewals.radar` é literalmente "Radar de Renovações" (`templates.py:259`), já é `meridian`, e `commercial.pipeline` é `category='commercial'`. **Zero edição em `templates.py`**, que é importado por `service.py` no caminho da Cobrança. O nome que o Founder vê é `artifacts.title`, que nós controlamos |
| B — dois templates novos no `CATALOGO` | 78 | Mais honesto no `report_templates`, mas edita um arquivo que a Cobrança importa **na véspera da apresentação**, e depende de `_garantir_template` acertar o `CHECK` de `category`/`narrative_shape` na primeira execução em produção — se errar, `criar()` levanta e não sai peça |

**Executar A.** Registrar P-225 para criar os templates próprios depois.

⚠️ **Consequência que precisa estar escrita:** o `data_contract` de
`renewals.radar` (📊 `window`, `renewals`, `by_week`) **não descreve** o nosso
payload (que é por vendedor). Isso é dívida de documentação, não de
comportamento — `renderizar` só usa `tpl.composition` quando a nossa é vazia
(📊 `service.py:193`), e a nossa nunca é. **A composição e o data_contract reais
dos dois relatórios estão escritos nesta SPEC** (§Bloco C.4 e §Bloco D.4) e são
cobrados por teste.

### D8 · O estilo visual: passar explícito no `renderizar` — **nota 95**

📊 `service.py:185-188`:

```python
        marca = v.get("brand_snapshot") or {}
        tpl = POR_CHAVE.get(art.get("template_key") or "")
        estilo = (visual_style or marca.get("visual_style")
                  or (tpl.visual_style if tpl else "aurora"))
```

**O snapshot da marca VENCE o do template** — e é por isso que 📊 todos os 40
artifacts saíram `aurora`, inclusive os de template que declara `meridian`.

| Opção | Nota | Por quê |
|---|---|---|
| **A — passar `visual_style=` explícito em `renderizar()`** | **95** | é a **primeira** prioridade da expressão. Zero edição em `service.py`. Resolve o problema para as nossas duas peças **sem mudar o de ninguém** |
| B — inverter a precedência em `service.py` | 30 | arquivo congelado (§G.1). Mudaria o visual das 40 peças existentes, incluindo as da Cobrança, na véspera |

**Executar A.** Raio-X → `aurora`. Radar → `meridian` (📊 é o que o próprio
template declara, e o `meridian` tem numeral tabular em `td.num`, o que importa
numa tabela de dinheiro por vendedor). Registrar P-226 para B.

### D9 · A logo entra como `data:` URI dentro de `storage_ref` — **nota 92**

📊 `render.py:67-72` resolve a logo assim:

```python
    logo_url = logo.get("data_uri") or logo.get("public_url") or logo.get("storage_ref")
```

📊 Mas `snapshot_para_artefato` (`brand/capture.py:562-566`) só seleciona
`storage_ref, width, height, has_transparency, mime_type` — **`data_uri` nunca
existe em produção**. E 📊 `app/r/[token]/route.ts:99` serve com CSP
`img-src 'self' data:`, que **bloqueia imagem remota**.

| Opção | Nota | Por quê |
|---|---|---|
| **A — gravar o `data:` URI direto em `brand_assets.storage_ref`** | **92** | 📊 a coluna é `text NOT NULL` **sem CHECK de formato** (migration `20260725_05...:45`). `render.py` a lê no terceiro `or` e emite `<img src="data:image/png;base64,…">`. **Zero código, zero migration, zero edição em arquivo congelado.** 📊 O data URI tem **6.282 caracteres** (`python -c "len('data:image/png;base64,'+b64(open(...).read()))"`, 18/08/2026) |
| B — alterar `snapshot_para_artefato` para embutir o data URI | 40 | `capture.py` está no caminho de `criar()` — **é o caminho da Cobrança**. Editar isso na véspera é o risco que a SPEC existe para evitar |
| C — subir para MinIO e usar URL pública | 25 | a CSP de `/r/[token]` bloqueia host externo. Falharia justamente no link que se quer mostrar |

**Executar A.** §Bloco E tem o SQL e o UNDO.

⚠️ **Efeito colateral que precisa ser declarado, não escondido:** dar marca à
Resulta muda **também** a aparência das peças da Cobrança dessa corretora — elas
passam a sair com a logo e as cores da Resulta em vez da paleta genérica. **Isso
é melhoria, não regressão**, é reversível com um `UPDATE`, e o §Bloco G.4 tem
uma asserção que verifica que a Cobrança **continua gerando** a peça depois da
mudança. Não é surpresa: está escrito aqui.

### D10 · O silêncio no palco: o modelo avisa antes de chamar — **nota 86**

📊 **Não existe mensagem de progresso no chat.** `graph.py:1596-1599` filtra o
stream para emitir **só** tokens do nó `agent`; enquanto o nó `tools` roda,
**zero bytes saem pelo SSE**. O único feedback é o `TypingIndicator` — três
bolinhas, sem texto (`app/dashboard/chat/page.tsx:637-640`). 📊 E **não há
timeout algum** que mate uma tool de 45 s: nem em `nodes.py`, nem em `chat.py`,
nem no proxy do Next, nem no fetch do browser.

| Opção | Nota | Por quê |
|---|---|---|
| **A — a descrição da tool manda o modelo ANUNCIAR antes de chamar** | **86** | 📊 `llm_factory.py:155` cria o modelo com `"streaming": True`, e o Claude emite bloco de texto **antes** do bloco de tool_use. O texto sai token a token, no nó `agent`, **antes** da tool rodar. **Zero código novo.** Somado ao pré-aquecimento (§Bloco F), a espera real cai para segundos |
| B — evento `on_tool_start` novo no SSE | 60 | toca `graph.py` **e** `chat.py`, e 📊 `chat.py:600` acumula tudo em `full_response`, que é **persistido no banco** — um status viraria parte da mensagem salva |
| C — heartbeat `: ping` no SSE | 55 | resolve corte de borda, não resolve o silêncio percebido; e exige tarefa concorrente no gerador |

**Executar A.** Registrar P-227 (B) e P-228 (C).

---

# 6. A arquitetura, em uma figura

```text
  O Founder digita no chat do dashboard
              │
              ▼
  agent_role='core'  ──►  o modelo emite TEXTO ("vou levantar…")  ──► streama já
              │                                                        (D10)
              ▼
  tool: raio_x_comercial(periodo="2025")     ou    radar_de_renovacoes(periodo="90 dias")
              │  exige_async=True  ·  company_id vem do CONSTRUTOR (I10)
              ▼
  ┌───────────────────────── BLOCO A · camada de dados ─────────────────────────┐
  │  Redis  raiox:bi:{company_id}:{ano}   TTL 6 h   ◀── pré-aquecido (BLOCO F)  │
  │     miss │                                                                  │
  │          ▼                                                                  │
  │  _resolve_infocap_connection(db, company_id=…)   ← IMPORTADO, não alterado   │
  │  POST /login → token → header Authorization CRU (sem "Bearer")              │
  │  GET /documentos_bi (1 ano)  ·  GET /producao (paginado)  ·  GET /renovacoes│
  │  retry 3× · semáforo 4 · 404=vazio · 500=retry/dividir · 403 SigV4=fatal    │
  │          ▼                                                                  │
  │  saneamento:  tipdoc='A'  ·  cancelado='F'  ·  ordem=1 & indireto='F'       │
  └─────────────────────────────────────────────────────────────────────────────┘
              │  dataclasses puras, sem rede
              ▼
  ┌───────────────────────── BLOCO B · cálculos puros ──────────────────────────┐
  │  ranking · ticket médio · custo de aquisição · mix de ramo                  │
  │  novo vs renovação · comparação de períodos · projeção                      │
  │  cada um: uma FUNÇÃO PURA, um número esperado, um teste                     │
  └─────────────────────────────────────────────────────────────────────────────┘
              │
              ▼
  ┌────────── BLOCO C/D · a peça ───────────────────────────────────────────────┐
  │  composição em blocos {block, props}  ─── 17 blocos, 9 gráficos             │
  │  veredito determinístico  (+ opcional: 1 chamada de LLM que só REESCREVE)   │
  └─────────────────────────────────────────────────────────────────────────────┘
              │
              ▼
  ArtifactService.criar(origin='chat') → renderizar(visual_style=…) → publicar()
              │                                          ▲
              │                          BLOCO E · a marca (logo + paleta)
              ▼
  a tool devolve: "…  /dashboard/entregas/<id>"
              │
              ▼
  MessageBubble.tsx:112  (remarkGfm → autolink)   ──►  O FOUNDER CLICA
```

---

# 7. BLOCO A — A camada de dados da InfoCap

**Gate:** rodando contra a InfoCap real da Resulta, a camada devolve o ranking
de 2025 com os **sete primeiros nomes na ordem exata** da tabela §A.5, e o teste
de mutação prova que cada uma das três armadilhas medidas sabe deixar o guarda
vermelho.

> Este bloco é o primeiro porque **todo o resto é aritmética em cima dele.** Um
> erro aqui não aparece como erro: aparece como um número bonito e falso num
> relatório com a logo da corretora.

## A.1 — Os fatos medidos que este bloco implementa

📊 **Todos medidos em 18/08/2026**, na InfoCap da Resulta
(`https://api.corpnuvem.com`), pelo levantamento que originou esta SPEC.

**Autenticação.** `POST /login` com `{email, senha, aplicacao: 0}` → devolve
`token` (JWT). Header nas chamadas seguintes:

```text
Authorization: <token>        ← CRU. SEM a palavra "Bearer".
```

📊 É exatamente o que o conector já faz — `infocap_connector.py:1060`:
`headers = {"Authorization": token, "Content-Type": "application/json"}`.
**Não invente um segundo jeito de autenticar.**

**`GET /documentos_bi`** — `datini=DD/MM/AAAA`, `datfim=DD/MM/AAAA`,
`data=INIVIG`, `tipo_doc=TODOS`.

- Sem paginação: devolve tudo numa chamada.
- 20 campos: `codfil, nosnum, codcli, cliente, seguradora, ramo, inivig,
  numpar, preliq, pretot, base_c, val_c, val_cp, numapo, numend, nosnum_ren,
  datpro, fimvig, datalt, sit_sinistro`.
- `data` aceita **só** `INIVIG | DATINC | DATALT | DATPROP`.
- 📊 Janela maior que ~6 anos → **502 aos 28 s**. Ano a ano **sempre** funciona.
  → Invariante **I8**.

**`GET /producao`** — `qtd_pag=5000`, `pag=1..n`. Traz `cancelado`, `datemi` e
`tipdoc`, que **faltam** no `documentos_bi`.
🔴 📊 **O default de página é 15.** Sem `qtd_pag` você recebe quinze linhas e
acha que a corretora vendeu quinze apólices no ano.

**`GET /renovacoes`** — `dt_ini`, `dt_fim`, `qtd_pag=5000`, `pag=1..n`,
`cancelado=F`, `resgates=F`.
🥇 **O endpoint mais rico.** 33 campos, e o **único** que traz `produtor`,
`quant_produtores` e o array `prod_docs[]` **embutidos, em lote** — evita
3.000 chamadas individuais a `/documento`.
Traz também `dias_a_vencer`, `pretot`, `cic`, `fone`, `email`, `sin_situacao`,
`historico_hint`.
📊 1.341 linhas em 9,2 s, 100% com produtor. 📊 Janela 2020-2030 →
`count = 19.906`.
🔴 **Filtra por `fimvig`, não por `inivig`.** Isso não é detalhe — ver §A.6.

**Comissão.** Não há endpoint de comissão, e **nunca houve bloqueio** (§0.4).
Ela vem no documento: `base_c` (base de cálculo), `per_c` (% da corretora),
`val_c` (R$).
📊 `per_c` varia de 0,3% a 100% conforme o ramo. Valores negativos são
**estorno**. 📊 `val_cp` está **zerado em 100% das 16.693 linhas** — não use.

**Repasse ao produtor.** `prod_docs[]`, com
`codpro, ordem, indireto, per_r, val_r, nome_produtor, nome_agente`.

```text
🔑  ordem == 1  E  indireto == "F"   →  o produtor DIRETO. Quem VENDEU.
    indireto == "T"                  →  participação de comissionamento.
```

**Outros, medidos:** `GET /produtores?texto=&codage=1` → 📊 116 produtores.
`GET /sinistros` → 📊 2.530. `GET /clientes` → 📊 14.967.
Chave estruturante: `(codfil, nosnum)` em 9 endpoints; `codcli` em 6;
`codpro` em 3.

**Nunca chamar, em hipótese nenhuma:** `POST/PUT/PATCH/DELETE` de `/cliente`,
`/endereco`, `/email`, `/telefone`, `/negocio`, `/prod_docs`, `/incorp*`.
O módulo só emite `GET`, mais o `POST /login`. Isso é asserção de teste (§A.8).

## A.2 — Onde mora, e o que ele **não** pode tocar

**Arquivos novos:**

```text
backend/app/services/comercial/__init__.py
backend/app/services/comercial/fonte_infocap.py     ← este bloco
backend/scripts/preflight_infocap_bi.py             ← §2.4
```

**Credenciais — uma autoridade só, a que já existe:**

```python
from app.api.infocap_connector import _resolve_infocap_connection
from app.services.encryption_service import get_encryption_service

async def _credenciais(db, company_id: str) -> Credencial:
    """A conexão da corretora, pela MESMA função que o Atendimento usa.

    🔴 IMPORTAÇÃO, NUNCA EDIÇÃO. `infocap_connector.py` é arquivo do
    Atendimento (§Bloco G.1). Importar não muda comportamento; editar mudaria.

    📊 Assinatura real (infocap_connector.py:722):
        async def _resolve_infocap_connection(db, *, company_id, requested_connection_id=None)
        -> {"selected_connection": dict|None, "status": str, "summary": {...}}
    """
    d = await _resolve_infocap_connection(db, company_id=company_id)
    conn = d.get("selected_connection")
    if not conn:
        raise SemConexao(d.get("status") or "blocked_missing_credentials")
    cfg = conn.get("connection_config") or {}
    base = (cfg.get("base_url") or settings.INFOCAP_BASE_URL or "").rstrip("/")
    creds = json.loads(get_encryption_service().decrypt(conn["encrypted_secret_ref"]))
    return Credencial(base_url=base,
                      email=creds.get("username") or creds.get("email"),
                      senha=creds.get("password") or creds.get("senha"))
```

> **Por que não uma env var `CORP_INFOCAP_RESULTA_*`:** 📊 essas variáveis
> existem em **um** lugar do repositório — `backend/scripts/build_cartographer_dataset.py:168-173`
> — e são de um script offline. Usá-las no runtime criaria um **segundo caminho
> de credencial**, amarrado a uma corretora pelo nome, dentro de um produto
> multi-tenant. **Nota 40 contra nota 90.** A tabela `tenant_connections` é a
> autoridade, e o Atendimento já a usa.

> **Sobre o `egress_guard`:** 📊 ele guarda a HTTP tool dinâmica
> (`http_request.py`) e a captura de marca (`brand/web.py`) — URLs que vêm do
> cadastro ou do modelo. O host da InfoCap vem de `tenant_connections`, exatamente
> como no conector, que também não passa pelo guard. **Mesma decisão, mesma
> razão:** a URL não é controlada por agente.

## A.3 — O cliente HTTP: retry, concorrência e semântica de erro

📊 **Não existe cliente HTTP compartilhado com retry no backend.** O conector
abre `async with httpx.AsyncClient(...)` por requisição e **não tem retry
nenhum** (zero tenacity, zero backoff em 4.254 linhas). Este bloco cria o seu,
**local ao módulo**, sem tocar em nada existente.

📊 **Por que retry é obrigatório:** 10 requisições paralelas terminaram em 4,5 s,
mas **1 de 10 devolveu HTTP 500**. Sem retry, um relatório em dez sai capenga —
e capenga sem avisar.

**A semântica, medida:**

| Resposta | Significado | O que fazer |
|---|---|---|
| **404** | consulta vazia | **não é erro.** Devolve `[]` |
| **500** | quase sempre janela grande demais, às vezes esporádico | retry 3× com espera 0,5 s → 1,5 s → 4 s. Persistiu: **divide a janela ao meio** e tenta as duas metades. Persistiu de novo: erro explícito |
| **502 aos ~28 s** | janela muito grande | mesma divisão; e **nunca peça mais de 1 ano** (I8) |
| **403 com texto de assinatura SigV4** | **rota inexistente** | 🔴 **erro fatal, sem retry.** É bug de código, não da API |
| **401/403 sem SigV4** | credencial | erro explícito, sem retry |
| timeout | rede | conta como 500 |

```python
_TETO_PARALELO = 4      # 📊 10 paralelas deram 1 erro em 10. 4 é a margem.
_TENTATIVAS    = 3
_ESPERAS       = (0.5, 1.5, 4.0)
_TIMEOUT_S     = 45.0   # 📊 o 502 chega aos 28 s; o teto tem de ser maior
_SIGV4         = "Credential="   # marca do erro do API Gateway
```

> **A regra que não pode ser afrouxada:** `404 → []` e `403 SigV4 → estoura`.
> Se as duas forem tratadas igual, um erro de rota vira "a corretora não vendeu
> nada" — e o relatório sai com zeros, bonito, e mentindo. É o pior resultado
> possível, exatamente como a docstring de `render_html` já ensina.

## A.4 — O que a camada devolve, e o saneamento que ela aplica

```python
@dataclass(frozen=True)
class Documento:
    codfil: str; nosnum: str; codcli: str
    seguradora: str; ramo: str
    inivig: date; fimvig: date
    pretot: float          # prêmio total
    base_c: float          # base de cálculo da comissão
    val_c: float           # comissão da CORRETORA, em R$ (pode ser negativa = estorno)
    nosnum_ren: str        # não-vazio => é RENOVAÇÃO
    tipdoc: str            # vem do cruzamento com /producao
    cancelado: bool        # idem

@dataclass(frozen=True)
class Produtor:
    codpro: str; nome: str
    ordem: int; indireto: bool
    per_r: float; val_r: float     # repasse ao produtor

@dataclass(frozen=True)
class Carteira:
    """Uma janela de tempo, saneada. É o que os cálculos recebem."""
    documentos: list[Documento]              # já filtrados (I6)
    produtores_por_doc: dict[tuple, list[Produtor]]   # (codfil, nosnum) -> prod_docs[]
    sem_produtor: list[tuple]                # os que não casaram — VISÍVEIS, nunca zerados
    janela: tuple[date, date]
    aviso: list[str]                         # tudo que foi descartado e por quê
```

### As três armadilhas, e como cada uma é fechada

**Armadilha 1 — `documentos_bi` inclui CANCELADAS e não tem campo `cancelado`.**
📊 506 canceladas em 2025 inflam a comissão em **R$ 90.671 (4,0%)**.

**Armadilha 2 — `documentos_bi` mistura `tipdoc`, e não tem o campo.**
📊 2025: `A`=1.680, `F`=1.064, `X`=255, `C`=193, `M`=52, `R`=9, `I`=3.
Só `A` é apólice.

> 🔑 **As duas se fecham com UM cruzamento.** `/producao` traz `cancelado` **e**
> `tipdoc`. Uma varredura paginada por ano monta
> `{(codfil, nosnum): (tipdoc, cancelado)}`, e o filtro é uma linha:
>
> ```python
> docs = [d for d in docs if mapa.get(chave(d), ("", True)) == ("A", False)]
> ```
>
> ⚠️ **Documento que não aparece em `/producao` é DESCARTADO e CONTADO** no
> `aviso`. Fail-closed: na dúvida, fora. O contrário — assumir "A, não
> cancelada" — reintroduz a armadilha pela porta dos fundos.

**Armadilha 3 — 🔴 a que mais importa: TRÊS produtores por apólice.**
📊 Média de 3 (2025, n=3.536: 2 produtores → 1.204 apólices; 3 → 1.221;
4 → 1.046; 5 → 64).

**Somar `val_c` por todos os produtores TRIPLICA o faturamento.**

```python
def produtor_direto(prods: list[Produtor]) -> Optional[Produtor]:
    """O único que conta para RANKING e para NOVO×RENOVAÇÃO.

    🔴 `ordem == 1` E `indireto is False`. Os dois. Uma apólice com cinco
    linhas em prod_docs tem UM vendedor; as outras quatro são participação de
    comissionamento e entram SÓ no custo de aquisição (§Bloco B.4).
    """
    diretos = [p for p in prods if p.ordem == 1 and not p.indireto]
    return diretos[0] if len(diretos) == 1 else None
```

⚠️ `len(diretos) != 1` → a apólice vai para `sem_produtor`, **não** para o
primeiro da lista. Chutar aqui é atribuir venda a quem não vendeu.

**Estornos.** `val_c` negativo é dinheiro que voltou. **Entra na soma** — é o
resultado real — **e aparece numa linha própria** do relatório
(§Bloco C.4, bloco `callout`). Esconder estorno é o mesmo defeito de esconder
cancelada.

## A.5 — 📊 Os números esperados, que viram teste

**Produção bruta por ano, `documentos_bi` com `data=INIVIG`, sem nenhum filtro**
(📊 18/08/2026):

| Ano | Apólices | Prêmio | Comissão | Novo | Renov. |
|---|---:|---:|---:|---:|---:|
| 2023 | 5.503 | R$ 22.976.063 | R$ 3.314.589 | 3.351 | 2.152 |
| 2024 | 5.879 | R$ 25.682.981 | R$ 3.642.961 | 3.642 | 2.237 |
| 2025 | 3.272 | R$ 14.699.927 | R$ 2.276.444 | 2.301 | 971 |
| 2026 (parcial) | 2.039 | R$ 10.154.725 | R$ 1.750.968 | 1.481 | 558 |

> 📊 Em todos os quatro anos, `Novo + Renov = Apólices`. Isso confirma que a
> partição é **exaustiva** e que a regra é simples: `nosnum_ren` preenchido ⇒
> renovação. É **INFERÊNCIA** confirmada por quatro somas independentes, e o
> teste A.8 asserção 6 a re-verifica.

**Ranking 2025 por produtor direto (`ordem=1`, `indireto='F'`)** — 📊 18/08/2026:

| # | Produtor | Apólices | Comissão |
|---|---|---:|---:|
| 1 | RAFAEL L SILVEIRA-EXECUTIVO | 519 | R$ 537.970 |
| 2 | LUIZ GUILHERME ARAUJO - FECHADOR | 125 | R$ 389.889 |
| 3 | MARCOS TONIOLO - INDICADOR | 22 | R$ 354.926 |
| 4 | LUIZ GUILHERME - EXECUTIVO | 350 | R$ 312.521 |
| 5 | RAFAEL LACAU SILVEIRA - FECHADOR | 154 | R$ 187.946 |
| 6 | JEEP- FLORIPA | 222 | R$ 117.672 |
| 7 | DVA BYD ITAJAI | 182 | R$ 112.066 |

📊 Soma de **todos** os produtores diretos em 2025: **R$ 3.094.963**.

## A.6 — 🔴 As duas populações não são a mesma, e isso precisa estar escrito

**FATO.** `documentos_bi` filtra por **`inivig`** (o que **começou** no período).
`/renovacoes` filtra por **`fimvig`** (o que **vence** no período).

**FATO.** 📊 A produção bruta de 2025 soma R$ 2.276.444 sobre 3.272 documentos.
📊 O ranking de produtor direto de 2025 soma R$ 3.094.963, e a distribuição de
produtores por apólice foi medida sobre **n = 3.536**.

**Os dois não podem ser o mesmo número, porque não são o mesmo conjunto.**

**INFERÊNCIA, declarada como tal:** `n = 3.536` corresponde à população de
`/renovacoes` com `fimvig` dentro de 2025 (`cancelado=F`, `resgates=F`) — 264
documentos a mais que a produção por `inivig`, o que é o esperado quando a
carteira cresce e apólices iniciadas em 2024 vencem em 2025.

**Como o executor confirma, em vez de acreditar:**

```bash
python backend/scripts/preflight_infocap_bi.py --company <UUID> \
       --contar-renovacoes 01/01/2025 31/12/2025
# ESPERADO: count == 3536 (±5). Se bater, a inferência está confirmada e o
# ranking DEVE reproduzir a tabela do §A.5 sobre essa população.
# Se NÃO bater, PARE e registre o número real no relatório antes de seguir.
```

**A decisão que sai disso, e ela é normativa:**

```text
RAIO-X COMERCIAL   população = PRODUÇÃO  (documentos_bi, data=INIVIG)
                   porque o Founder pediu "quem VENDE" — e vender é iniciar.

RADAR DE RENOVAÇÕES população = VENCIMENTO (/renovacoes, fimvig)
                   porque renovação é sobre o que VENCE.

CALIBRAÇÃO         o ranking rodado sobre a população de VENCIMENTO de 2025
                   tem de reproduzir a tabela do §A.5. É esse run que prova
                   que o CÓDIGO está certo — e ele vai para o relatório.
```

> 🔴 **Não force o número a bater mudando o filtro.** Se o ranking sobre
> produção der diferente de R$ 3.094.963, **está certo assim** — é outra
> população. O que tem de bater é a **calibração**. Trocar `inivig` por `fimvig`
> no Raio-X para o total ficar bonito é o defeito que o CLAUDE.md §12.1 chama de
> "campo que mente sobre o que guarda".

## A.7 — O cache e o pré-aquecimento (a parte que o §Bloco F usa)

```python
_CHAVE = "raiox:bi:{company_id}:{ano}"          # documentos_bi + producao já cruzados
_CHAVE_REN = "raiox:ren:{company_id}:{ini}:{fim}"   # /renovacoes por janela
_TTL_S = int(os.getenv("RAIOX_CACHE_TTL_S") or 21600)   # 6 h
```

📊 O TTL de 6 h copia o precedente medido do cartógrafo
(`cartographer_runner.py:28`, `_TTL = 6 * 3600`), e a escrita segue a convenção
da casa: `await r.set(chave, payload, ex=_TTL_S)` com
`get_async_redis_client()` (`app/core/redis.py:48`).

🔴 **Redis fora do ar não pode derrubar o relatório.** Toda leitura e toda
escrita de cache vão dentro de `try/except` largo, com log em `warning`. Sem
cache, o relatório demora; **sem relatório, a apresentação acaba.**

## A.8 — Teste e mutação

**Arquivo:** `backend/tests/test_a_comissao_nao_triplica.py`
**Script:** `npm run test:comissao-nao-triplica`

Roda **offline**, sobre uma fixture gravada — 📊 uma amostra real e **anonimizada**
de `documentos_bi`, `/producao` e `/renovacoes` de 2025, com os campos de PII
(`cic`, `fone`, `email`, `cliente`) já removidos na gravação. A fixture é gerada
uma vez por `preflight_infocap_bi.py --gravar-fixture` e vive em
`backend/tests/fixtures/infocap_2025_anon.json`.

| # | Asserção |
|---|---|
| 1 | com a fixture inteira, o ranking devolve os **7 primeiros nomes na ordem** da tabela §A.5 |
| 2 | RAFAEL L SILVEIRA-EXECUTIVO: **519** apólices e **R$ 537.970** (± R$ 1.000) |
| 3 | 🔴 **CONTROLE**: a mesma soma **sem** o filtro `ordem=1` dá **mais que o dobro** — provando que o filtro filtra |
| 4 | as **506** canceladas de 2025 são excluídas, e a comissão cai **R$ 90.671** (± R$ 500) |
| 5 | 🔴 **CONTROLE**: com o cruzamento de `/producao` desligado, a diferença é **zero** — provando que a asserção 4 mede o cruzamento e não o acaso |
| 6 | só `tipdoc='A'` sobrevive: **1.680** documentos, e os `F/X/C/M/R/I` somam **1.576** descartados |
| 7 | `nosnum_ren` preenchido ⇒ renovação; sobre a fixture de 2025, **2.301 novo / 971 renovação** |
| 8 | apólice com 2 linhas `ordem=1` vai para `sem_produtor`, **não** para a primeira |
| 9 | documento ausente em `/producao` é descartado **e contado** em `aviso` |
| 10 | `val_c` negativo entra na soma **e** aparece no total de estornos |
| 11 | 404 devolve `[]`; 500 dispara retry; **403 com `Credential=` no corpo LEVANTA** |
| 12 | nenhuma requisição do módulo usa verbo diferente de `GET`, exceto `POST /login` — varredura por AST do arquivo |
| 13 | nenhuma janela pedida excede 366 dias (I8) |
| 14 | Redis indisponível → o resultado sai igual, só mais devagar |
| 15 | multi-tenant: duas `company_id` diferentes geram **chaves de cache diferentes**, e a de A nunca serve B |

| Mutação | Esperado |
|---|---|
| **M1** — `produtor_direto` devolve `prods[0]` | asserções 1, 2 e 8 **vermelhas** |
| **M2** — remover o filtro `indireto is False` | asserções 1 e 2 **vermelhas** |
| **M3** — remover o cruzamento com `/producao` | asserções 4 e 6 **vermelhas**; a 5 fica **verde** (é o controle) |
| **M4** — `403` passa a ser tratado como `404` | asserção 11 **vermelha** |
| **M5** — `qtd_pag` sai da chamada de `/producao` | asserção 6 **vermelha** (só 15 linhas no mapa) |
| **M6** — chave de cache sem `company_id` | asserção 15 **vermelha** |
| **M7 (controle)** — TTL de 6 h para 2 h | **VERDE** — o teste mede isolamento e correção, não o prazo |

> **As asserções 3 e 5 são as que dão direito à conclusão.** Sem a 3, um código
> que somasse zero passaria na 1 e na 2 por acaso de ordenação. Sem a 5, a
> queda de R$ 90.671 poderia vir de qualquer coisa.

---

# 8. BLOCO B — Os cálculos, com a fórmula de cada um

**Gate:** cada cálculo é uma **função pura**, testável sem rede, com um número
esperado escrito nesta SPEC.

**Arquivos novos:**
`backend/app/services/comercial/calculos.py` · `backend/app/services/comercial/periodo.py`

## B.1 — O período que o Founder escreve

🔴 Este é o **único** campo que o LLM preenche, e por isso ele é **texto livre**
que o **código** interpreta. (D1: o modelo copia; o código decide.)

```python
def interpretar_periodo(texto: str, *, hoje: date, futuro: bool = False
                        ) -> tuple[date, date, str]:
    """Devolve (inicio, fim, rotulo_humano). NUNCA levanta: sem sinal, usa o padrão.

    `futuro=True` (Radar) muda o padrão e a leitura de "90 dias":
      passado  -> os 90 dias que TERMINAM hoje
      futuro   -> os 90 dias que COMEÇAM hoje
    """
```

| O que o Founder escreve | Passado (Raio-X) | Futuro (Radar) |
|---|---|---|
| *(vazio)* | 01/01 do ano corrente → hoje · "2026 (parcial)" | hoje → hoje+90 · "próximos 90 dias" |
| `2025` | 01/01/2025 → 31/12/2025 | 01/01/2025 → 31/12/2025 |
| `este ano`, `ano atual`, `2026` | 01/01/2026 → hoje | 01/01/2026 → 31/12/2026 |
| `ano passado` | 01/01/2025 → 31/12/2025 | idem |
| `últimos 12 meses`, `12 meses` | hoje-365 → hoje | — |
| `próximos 60 dias`, `60 dias` | hoje-60 → hoje | hoje → hoje+60 |
| `primeiro semestre`, `1o semestre` | 01/01 → 30/06 do ano corrente | idem |
| `segundo semestre` | 01/07 → 31/12 | idem |
| `agosto`, `agosto de 2025` | 01/08 → 31/08 do ano indicado (ou corrente) | idem |
| `3o trimestre`, `Q3` | 01/07 → 30/09 | idem |
| `de 01/03/2026 a 30/06/2026` | literal | literal |
| qualquer outra coisa | **o padrão**, e o rótulo diz qual foi usado | idem |

🔴 **Nunca levanta exceção, nunca pergunta de volta.** O Founder vai estar
nervoso no palco. Texto que o parser não entende vira o padrão, e o **rótulo no
relatório diz honestamente qual período foi usado** — quem lê vê na capa.

⚠️ **Recorte de janela (I8):** se `fim - inicio > 366 dias`, a camada de dados
**divide em anos civis** e junta. O período de 4 anos do Founder ("desde 2023")
vira 4 chamadas, não um 502.

## B.2 — Ranking por comissão

```text
Para cada documento d da população saneada:
    p = produtor_direto(prod_docs[chave(d)])
    se p é None: soma em SEM_PRODUTOR e segue
    ranking[p.nome].apolices  += 1
    ranking[p.nome].comissao  += d.val_c
    ranking[p.nome].premio    += d.pretot
ordena por comissao DESC
```

📊 Esperado (calibração 2025): a tabela do §A.5, total R$ 3.094.963.

⚠️ **Normalização de nome.** 📊 A InfoCap tem `RAFAEL L SILVEIRA-EXECUTIVO` e
`RAFAEL LACAU SILVEIRA - FECHADOR` como **duas linhas distintas** — e são
papéis diferentes da mesma pessoa. **NÃO fundir.** Agrupe por `codpro`, e use
`nome_produtor` só como rótulo. Fundir por semelhança de nome inventaria um
vendedor que não existe no sistema da corretora.

## B.3 — Ticket médio

```text
ticket_medio = Σ pretot / nº de documentos          (população saneada)
ticket_medio_por_produtor = Σ pretot(p) / apólices(p)
```

📊 Conferência 2025 (produção bruta): 14.699.927 / 3.272 = **R$ 4.492,64**.
Depois do saneamento o número **muda** — e tem de mudar; se não mudar, o
saneamento não rodou.

## B.4 — 🔴 Custo de aquisição por canal — o número da apresentação

```text
Para cada produtor p (QUALQUER ordem, QUALQUER indireto):
    repassado[p] = Σ val_r  de todas as linhas de prod_docs de p
    base[p]      = Σ val_c  das APÓLICES DISTINTAS em que p aparece
custo_de_aquisicao[p] = repassado[p] / base[p]
```

> **Repare na assimetria, e ela é deliberada:** o **ranking** (B.2) conta só
> `ordem=1`; o **custo** conta **todas** as participações. Ranking responde
> *"quem vendeu"*; custo responde *"quanto daquela comissão saiu pela porta"*.
> Usar o mesmo filtro nos dois esconderia exatamente o achado.

📊 Conferência obrigatória:

```text
RAFAEL EXECUTIVO   61.280 / 1.258.472  =  4,9%
DVA BYD ITAJAI     57.855 /   115.089  = 50,0%
```

**Tolerância: ± 0,3 ponto percentual.** Fora disso, **a fórmula está errada, não
o número** — e a diferença provável é o denominador: `base` são as apólices
**distintas** em que o produtor aparece, contando o `val_c` **da apólice
inteira**, não a fatia dele.

⚠️ **Piso de amostra:** canal com menos de **5** apólices não entra no quadro.
💭 Um canal com uma apólice e um repasse alto produziria "97% de custo" e uma
conversa constrangedora no palco sobre um caso isolado.

## B.5 — Mix de ramo por vendedor

```text
mix[produtor_direto][ramo] = Σ val_c
percentual = mix[p][r] / Σ_r mix[p][r]
```

Vira o bloco `stacked` (📊 `blocks.py:219`, `categories` + `series`), com os
**6 maiores ramos** e o resto agregado em "Demais ramos".
💭 Seis é o número que cabe numa legenda sem virar sopa de letrinha; ajustável
na execução.

## B.6 — Novo vs renovação

```text
é_renovação(d)  ⇔  d.nosnum_ren  não vazio
taxa_de_renovação = renovações / total
```

📊 Conferência: 2025 → 2.301 novo, 971 renovação (soma 3.272 ✓).
2024 → 3.642 / 2.237 (soma 5.879 ✓). 2023 → 3.351 / 2.152 ✓.
2026 parcial → 1.481 / 558 ✓.

## B.7 — Comparação entre períodos

```text
periodo_anterior = a MESMA janela deslocada 1 ano para trás
delta_pct(x) = (x_atual - x_anterior) / |x_anterior| * 100      se x_anterior != 0
             = None                                             se x_anterior == 0
```

🔴 `x_anterior == 0` → `delta = None`, e o KPI sai **sem seta**. 📊 O bloco
`kpis` já trata `delta` ausente (`blocks.py:129`). Dividir por zero e imprimir
"∞%" ou "0%" é a maneira mais rápida de perder a credibilidade de um relatório.

⚠️ **Ano corrente é parcial.** Comparar 2026 (janeiro→agosto) com 2025 inteiro é
uma comparação errada apresentada como certa. Quando `fim > hoje` da janela
anterior for irrelevante, a comparação usa a **mesma fração do ano**:
`01/01/2025 → 18/08/2025` contra `01/01/2026 → 18/08/2026`. O rótulo diz
`"vs. mesmo período de 2025"`, nunca `"vs. 2025"`.

## B.8 — Projeção

```text
fracao   = dias_decorridos_da_janela / dias_totais_da_janela
projecao = realizado / fracao                        (linear, sem sazonalidade)
```

🔴 **Rotulagem obrigatória na peça:** `"projeção linear"`, sempre, no `note` do
KPI. 💭 A projeção é uma hipótese aritmética, não uma previsão — e um número de
projeção sem etiqueta é exatamente o defeito que o CLAUDE.md §12.1 documenta:
número ilustrativo que atravessa seis documentos como se fosse medição.

Se `fracao < 0,15`, **não projeta** — devolve `None` e o KPI some.

## B.9 — Teste e mutação

**Arquivos:** `backend/tests/test_o_periodo_que_o_founder_escreve.py` ·
`backend/tests/test_os_calculos_do_raio_x.py`
**Scripts:** `npm run test:periodo-do-founder` · `npm run test:calculos-raio-x`

**Do parser** — a tabela do §B.1 vira tabela de teste, com `hoje` fixo em
18/08/2026, mais:

| # | Asserção |
|---|---|
| 1 | as 12 linhas da tabela §B.1 devolvem as datas escritas |
| 2 | `"me faz aí aquele negócio de vendas"` → o padrão, e o rótulo diz qual |
| 3 | `futuro=True` inverte "90 dias" (começa hoje em vez de terminar hoje) |
| 4 | **CONTROLE**: `"2025"` e `"ano passado"` devolvem **exatamente** as mesmas datas |
| 5 | nenhuma entrada, nem `""`, nem `None`, nem emoji, levanta exceção |
| 6 | janela > 366 dias é recortada em anos civis, e a união cobre a janela |

**Dos cálculos** — sobre a fixture anonimizada:

| # | Asserção |
|---|---|
| 1 | ranking 2025 = tabela §A.5 |
| 2 | ticket médio bruto 2025 = R$ 4.492,64 (± R$ 1) |
| 3 | custo de aquisição: RAFAEL EXECUTIVO 4,9% e DVA BYD 50,0% (± 0,3 p.p.) |
| 4 | 🔴 **CONTROLE**: se o denominador virar a fatia do produtor em vez do `val_c` da apólice, o número **muda** — provando que a asserção 3 mede o denominador certo |
| 5 | novo/renovação 2025 = 2.301 / 971 |
| 6 | canal com 4 apólices **não** aparece no quadro de custo; com 5, aparece |
| 7 | `delta_pct` com anterior = 0 devolve `None`, nunca `inf` nem `0` |
| 8 | comparação de ano parcial usa a mesma fração, e o rótulo diz "mesmo período" |
| 9 | `fracao < 0,15` → projeção `None` |
| 10 | mix por vendedor soma 100% (± 0,1 p.p.) para cada vendedor |
| 11 | dois produtores com nomes parecidos e `codpro` diferentes **continuam separados** |

| Mutação | Esperado |
|---|---|
| **M1** — custo passa a filtrar `ordem=1` | asserção 3 **vermelha** (os dois números caem) |
| **M2** — `delta_pct` volta a dividir por zero | asserção 7 **vermelha** |
| **M3** — comparação volta a usar o ano inteiro anterior | asserção 8 **vermelha** |
| **M4** — agrupar produtor por nome normalizado | asserção 11 **vermelha** |
| **M5** — piso de amostra cai para 1 | asserção 6 **vermelha** |
| **M6 (controle)** — mudar de 6 para 5 o número de ramos do mix | **VERDE** — o teste mede a soma, não a quantidade |

---

# 9. BLOCO C — O Raio-X Comercial

**Gate:** uma frase no chat da Resulta produz uma linha em `artifacts` com
`origin='chat'`, e o link abre uma peça com logo, dados reais e o quadro de
custo por canal.

## C.1 — A tool

**Arquivo novo:** `backend/app/agents/tools/comercial_tools.py`

```python
class RaioXInput(BaseModel):
    periodo: Optional[str] = Field(
        default=None,
        description=("O período, EXATAMENTE como o usuário escreveu. Exemplos: "
                     "'2025', 'este ano', 'ano passado', 'últimos 12 meses', "
                     "'primeiro semestre', 'agosto', 'de 01/03/2026 a 30/06/2026'. "
                     "Se ele não disse período, deixe vazio."))


class RaioXComercialTool(BaseTool):
    exige_async: ClassVar[bool] = True          # 🔴 I9. Espelha human_handoff.py:294

    name: str = "raio_x_comercial"
    description: str = """
    Gera o RAIO-X COMERCIAL da corretora e devolve o LINK do relatório pronto.
    Responde "quem vende, quanto rende, quanto custa": ranking de vendedores por
    comissão, ticket médio, CUSTO DE AQUISIÇÃO POR CANAL, mix de ramo por
    vendedor, novo contra renovação, e comparação com o mesmo período do ano
    anterior.

    Use quando pedirem: raio-x comercial · quem mais vende · ranking de
    vendedores · desempenho comercial · produção do período · quanto cada
    vendedor rendeu · quanto custa cada canal · comissão por vendedor ·
    relatório de vendas · resultado comercial.

    ANTES de chamar, diga em UMA frase curta que você vai levantar os dados e
    que leva alguns segundos. DEPOIS, entregue o link EXATAMENTE como veio,
    sem reescrever a URL.
    """
    args_schema: Type[BaseModel] = RaioXInput

    company_id: str = ""
    supabase_client: object = None
```

📊 A instrução *"ANTES de chamar, diga em uma frase curta"* é o que executa a
decisão **D10**: `llm_factory.py:155` cria o modelo com `"streaming": True`, e o
texto que o Claude emite antes do bloco de `tool_use` sai token a token pelo nó
`agent` — que é justamente o único nó que `graph.py:1596-1599` deixa passar.
**O chat para de ficar mudo sem uma linha de código novo.**

## C.2 — O que a tool devolve

```text
✅ Raio-X Comercial · 2025 pronto.

Abrir: /dashboard/entregas/<uuid>

R$ 3,09 mi em comissão · 3.272 apólices · ticket médio R$ 4.492
Maior vendedor: RAFAEL L SILVEIRA-EXECUTIVO, R$ 537.970 em 519 apólices.
Canal mais caro: DVA BYD ITAJAI, 50,0% da comissão vai em repasse.

(entregue o link acima literalmente, em markdown, sem reescrevê-lo)
```

🔴 **Retorna `str`.** 📊 `nodes.py:1160-1168` faz `content = str(result)` para
qualquer tool sem handler dedicado, e o modelo redige a resposta final — o
usuário **nunca** vê o retorno bruto. Daí a última linha, que é instrução ao
modelo, e os três números na frente, que sobrevivem à reescrita.

**A URL.** 📊 `/r/{token}` está **quebrada** — `middleware.ts:92-103` não tem
`/r/` em `publicRoutes` nem em `publicPrefixes`, e sem sessão a rota redireciona
para `/login`. **Esta SPEC não a conserta** (mexer em `middleware.ts` dispara o
gate do §9.1 do CLAUDE.md na véspera da apresentação — P-229).

O link é o do **visualizador de tenant**, que 📊 funciona, tem isolamento
correto (`.eq('company_id', empresa)` nas três consultas,
`app/dashboard/entregas/[artifactId]/page.tsx:120,133,144`) e o Founder já está
logado nele:

```python
base = (os.getenv("PUBLIC_APP_URL") or os.getenv("NEXT_PUBLIC_APP_URL") or "").rstrip("/")
url  = f"{base}/dashboard/entregas/{artifact_id}" if base else f"/dashboard/entregas/{artifact_id}"
```

📊 O link relativo também funciona: `MessageBubble.tsx:112` usa
`ReactMarkdown` com `remarkGfm`, e `[abrir](/dashboard/entregas/…)` vira âncora
relativa clicável. **A tool nunca chama `compartilhar()`** — sem token, sem
`/r/`, sem link quebrado no palco.

## C.3 — O veredito (D4)

```python
def veredito_determinístico(r: ResultadoRaioX) -> str:
    """Sempre existe. É a rede de segurança da I4."""
```

💭 Forma ilustrativa (os números vêm de `r`, nunca escritos à mão):

```text
A corretora emitiu R$ {premio} em {n} apólices no período, com R$ {comissao}
de comissão — {delta} contra o mesmo período de {ano-1}. {top1} respondeu por
{pct}% da comissão. O ponto de atenção é o custo do canal {pior}: {custo}% da
comissão gerada volta como repasse, contra {melhor_custo}% do canal mais
eficiente.
```

Depois, **se** `RAIOX_VEREDITO_LLM=1` (padrão `1`) e houver orçamento:

```python
try:
    texto = await _reescrever_veredito(numeros_ja_calculados, prazo_s=12)
except Exception:
    texto = veredito_determinístico(r)     # 🔴 I4
```

**Regras da chamada, e são duras:**
- prompt recebe **apenas números já calculados**, em JSON;
- instrução explícita: *"não invente número nenhum; use só os que estão aqui"*;
- teto de 12 s e de ~400 tokens de saída;
- **qualquer** exceção, timeout ou resposta vazia → veredito determinístico;
- 🔴 **guarda pós-chamada:** se o texto devolvido contiver um número que **não
  está** na lista de números permitidos (varredura por regex de dígitos), o
  texto é **descartado** e volta o determinístico. Um veredito bonito com um
  número inventado é pior que um veredito seco e certo.

## C.4 — A composição, completa

📊 Chave é **`block`**, dados em **`props`** (`blocks.py:406-424`). Itens de
`ranking`/`donut`/`waterfall`/`funnel` usam chaves **em português**
(`rotulo`, `valor`, `nota`); `kpis`/`table`/`chart`/`actions`, em inglês.
Limites silenciosos: `kpis` 6, `actions` 8, `ring` 4, `ranking.max` 10.

```python
composition = [
  {"block": "cover", "props": {
      "eyebrow": "Raio-X Comercial", "period": rotulo,          # "2025"
      "title": titulo_do_periodo,                               # do veredito, 1ª frase
      "subtitle": f"{n_apolices} apólices · {n_produtores} vendedores · "
                  f"{n_ramos} ramos · fonte InfoCap",
      "verdict": veredito,
      "headline_label": "Comissão no período", "headline_value": fmt_currency(comissao),
      "headline_delta": delta_comissao_pct, "headline_better": "up"}},

  {"block": "kpis", "props": {
      "eyebrow": "Os números do período", "title": "Como a corretora fechou",
      "items": [   # 🔴 no máximo 6 (blocks.py:134)
        {"label": "Comissão",        "value": ..., "delta": ..., "since": f"vs. {rot_ant}"},
        {"label": "Prêmio emitido",  "value": ..., "delta": ..., "since": f"vs. {rot_ant}"},
        {"label": "Apólices",        "value": ..., "delta": ...},
        {"label": "Ticket médio",    "value": ..., "delta": ..., "better": "up"},
        {"label": "Taxa de renovação","value": ..., "unit": "%", "delta": ...},
        {"label": "Custo médio de aquisição", "value": ..., "unit": "%", "better": "down"},
      ]}},

  {"block": "verdict", "props": {"text": veredito, "note": nota_de_metodo}},

  {"block": "chart", "props": {          # evolução mês a mês, 2 séries
      "eyebrow": "Evolução", "title": "Comissão mês a mês",
      "lede": f"Comissão da corretora, em milhares de reais. {rotulo} contra {rot_ant}.",
      "value_type": "short", "labels": meses_da_janela,
      "series": [{"name": rotulo, "values": serie_atual},
                 {"name": rot_ant, "values": serie_anterior}]}},

  {"block": "split", "props": {"sidebar": True,
      "left": [{"block": "ranking", "props": {
          "eyebrow": "Quem vende", "title": "Vendedores por comissão",
          "value_type": "currency_short", "highlight": 3, "max": 10,
          "items": [{"rotulo": nome, "valor": comissao,
                     "nota": f"{apolices} apólices · ticket {ticket}"} ...]}}],
      "right": [{"block": "donut", "props": {
          "eyebrow": "Composição", "title": "Comissão por ramo",
          "value_type": "currency_short",
          "center_value": fmt_currency_short(comissao), "center_label": "no período",
          "slices": [{"rotulo": ramo, "valor": v} ...]}}]}},

  {"block": "table", "props": {          # 🔴 O QUADRO QUE VALE A APRESENTAÇÃO
      "eyebrow": "Quanto custa", "title": "Custo de aquisição por canal",
      "lede": "Repasse ao produtor dividido pela comissão da corretora nas "
              "apólices em que ele participa. Canais com menos de 5 apólices "
              "ficam de fora.",
      "columns": [
        {"key": "canal",    "label": "Canal"},
        {"key": "apolices", "label": "Apólices",  "align": "right", "format": "number"},
        {"key": "comissao", "label": "Comissão",  "align": "right", "format": "currency"},
        {"key": "repasse",  "label": "Repassado", "align": "right", "format": "currency"},
        {"key": "custo",    "label": "Custo",     "align": "right", "format": "percent",
         "pill": True},
      ],
      "rows": [...],       # `custo_tone`: "positive" < 15% · "info" < 30%
      "total": {...}}},    #              "warning" < 40% · "negative" >= 40%

  {"block": "stacked", "props": {
      "eyebrow": "Distribuição", "title": "Mix de ramo por vendedor",
      "value_type": "currency_short",
      "categories": nomes_dos_10_maiores_vendedores,
      "series": [{"name": ramo, "values": [...]} for ramo in seis_maiores_ramos]}},

  {"block": "donut", "props": {
      "eyebrow": "Origem", "title": "Novo contra renovação",
      "center_value": f"{taxa_renovacao:.0f}%", "center_label": "renovação",
      "slices": [{"rotulo": "Novo", "valor": n_novo},
                 {"rotulo": "Renovação", "valor": n_renov}]}},

  {"block": "callout", "props": {        # só quando houver o que dizer
      "tone": "warning", "title": "O que ficou de fora desta conta",
      "text": aviso_de_saneamento}},     # canceladas, tipdoc, sem produtor, estornos

  {"block": "actions", "props": {
      "eyebrow": "Plano", "title": "O que fazer", "items": [...]}},   # máx. 8

  {"block": "sources", "props": {}},     # cai em data_sources (blocks.py:348)
  {"block": "footer",  "props": {}},
]
```

**`data_contract` real do Raio-X** (o que a SPEC cobra por teste, e o que
substitui o `data_contract` do `commercial.pipeline` — D7):

```python
{
 "periodo":       {"type": "object", "required": True,
                   "description": "inicio, fim, rotulo, rotulo_anterior"},
 "totais":        {"type": "object", "required": True,
                   "description": "premio, comissao, apolices, ticket_medio, estornos"},
 "comparacao":    {"type": "object", "required": True,
                   "description": "mesmos totais do período anterior + delta_pct"},
 "ranking":       {"type": "array",  "required": True,
                   "description": "codpro, nome, apolices, premio, comissao, ticket"},
 "custo_por_canal":{"type": "array", "required": True,
                   "description": "codpro, nome, apolices, comissao, repasse, custo_pct"},
 "mix_por_ramo":  {"type": "object", "required": True,
                   "description": "{codpro: {ramo: comissao}}"},
 "novo_vs_renovacao": {"type": "object", "required": True},
 "serie_mensal":  {"type": "object", "required": True,
                   "description": "labels, atual[], anterior[]"},
 "saneamento":    {"type": "object", "required": True,
                   "description": "canceladas, tipdoc_descartados, sem_produtor, estornos"},
}
```

🔴 **`saneamento` é obrigatório e aparece na peça.** Um relatório que descarta
506 linhas em silêncio é um relatório que não se pode defender numa pergunta.

## C.5 — A entrega (o caminho da Cobrança, D2)

```python
def _publicar(supabase, company_id, titulo, subtitulo, resumo, payload, blocos, estilo):
    """Cópia estrutural de billing_collection.py:1363-1396. Nenhum caminho novo."""
    from app.services.artifacts.service import ArtifactService
    s = ArtifactService(supabase)
    r = s.criar(company_id=company_id, title=titulo,
                template_key="commercial.pipeline",     # D7, nota 90
                payload=payload, composition=blocos,
                subtitle=subtitulo, summary=resumo,
                kind="report", origin="chat",           # 🔴 o número que vira 1
                work_run_id=None,
                data_sources=[{"label": "InfoCap · CorpAPI",
                               "detail": "documentos_bi · producao · renovacoes",
                               "as_of_label": "consultado em", "as_of": agora_iso}])
    versao = (r.get("version") or {}).get("id")
    s.renderizar(company_id=company_id, version_id=versao, visual_style=estilo)  # D8
    s.publicar(company_id=company_id, version_id=versao)
    return (r.get("artifact") or {}).get("id")
```

Chamado de dentro do `_arun` com `await asyncio.to_thread(_publicar, ...)` —
📊 `ArtifactService` é síncrono e usa o cliente Supabase bloqueante; é o mesmo
motivo documentado em `billing_collection.py:1369-1371`.

⚠️ 📊 `publicar()` levanta `ValueError` se a marca congelada não tiver `palette`
**e** `name` (`service.py:228-233`). Hoje o fallback preenche os dois, então
passa. Depois do §Bloco E, passa melhor.

Estilo do Raio-X: **`aurora`** (D8).

## C.6 — Registro no grafo e no Gateway

📊 `graph.py:528` abre o bloco do `core`:

```python
    if company_id and supabase_client and str(_agent_role or "core").strip().lower() in ("core", "", "core(legado)"):
```

Dentro dele, no mesmo formato dos vizinhos:

```python
        try:
            from .tools.comercial_tools import RaioXComercialTool, RadarDeRenovacoesTool
            tools.append(RaioXComercialTool(
                company_id=str(company_id), supabase_client=supabase_client))
            tools.append(RadarDeRenovacoesTool(
                company_id=str(company_id), supabase_client=supabase_client))
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[Graph] ⚠️ ferramentas comerciais não anexadas: {e}")
```

🔴 **`company_id` no construtor; `user_id` NUNCA.** 📊 O grafo é cacheado por
(empresa, agente) e reusado entre conversas — `graph.py:552-560` documenta que
amarrar usuário na montagem vaza dado entre sessões. As duas tools **não
precisam** de `user_id`, e por isso **não** entra `elif` nenhum em
`nodes.py:968-1005`.

E duas linhas em `NOME_PARA_CHAVE` (📊 `gateway_cutover.py:84`) — sem elas a
tool executa e fica **cega em `tool_invocations`**.

## C.7 — Teste e mutação

**Arquivo:** `backend/tests/test_o_chat_entrega_um_link.py`
**Script:** `npm run test:chat-entrega-link`

Com Supabase e InfoCap **falsos** (fake encadeável no padrão de
📊 `backend/tests/test_spec040_onda2_operational_view.py:47`).

| # | Asserção |
|---|---|
| 1 | `RaioXComercialTool.exige_async is True` (I9) |
| 2 | `_run` levanta — ninguém cai no caminho síncrono por engano |
| 3 | o `_arun` chama `criar` com `origin='chat'` e `composition` **não vazia** |
| 4 | `renderizar` recebe `visual_style='aurora'` **explicitamente** (D8) |
| 5 | o retorno contém `/dashboard/entregas/` e **não** contém `/r/` |
| 6 | todo item da composição tem as chaves `block` e `props`, e todo `block` está em `BLOCOS` (`blocks.py:397`) — nada de bloco inventado |
| 7 | o `payload` **não** contém CPF, telefone, e-mail nem nome de pessoa física — varredura por regex (I7) |
| 8 | a chamada de LLM do veredito falha → **sai relatório**, com o veredito determinístico (I4) |
| 9 | 🔴 **CONTROLE**: com a chamada de LLM funcionando, o veredito é **outro** — provando que a asserção 8 mede o fallback e não a ausência do recurso |
| 10 | veredito do LLM com número que não está na lista permitida → **descartado** |
| 11 | InfoCap indisponível → a tool devolve frase clara ao Founder e **não** cria artifact meio-pronto |
| 12 | AST de `graph.py`: os dois `append` estão **dentro** do `if` que testa `core` |
| 13 | AST de `graph.py`: nenhum dos dois recebe `user_id=` |
| 14 | as duas tools têm linha em `NOME_PARA_CHAVE` |
| 15 | a descrição da tool contém a instrução de anunciar antes (D10) e a de não reescrever a URL |

| Mutação | Esperado |
|---|---|
| **M1** — remover `exige_async` | asserção 1 **vermelha** |
| **M2** — `origin='routine'` | asserção 3 **vermelha** |
| **M3** — `renderizar` sem `visual_style` | asserção 4 **vermelha** |
| **M4** — o `except` do veredito vira `raise` | asserção 8 **vermelha** |
| **M5** — mover o `append` para fora do `if` do core | asserção 12 **vermelha** — e o Atendimento ganharia as tools |
| **M6** — pôr `cliente` no payload | asserção 7 **vermelha** |
| **M7 (controle)** — mudar o texto do veredito determinístico | **VERDE** — o teste mede o caminho, não a redação |

---

# 10. BLOCO D — O Radar de Renovações, por período e por vendedor

**Gate:** o relatório sai **por período** e **com coluna de vendedor**, e existe
um teste que fica **vermelho** se alguém agregar o ano inteiro ou tirar a coluna.

> 🔴 Este bloco existe porque o Founder disse, em letras maiúsculas: *"TEM QUE
> SER POR PERÍODO, E SEPARADO POR VENDEDOR. NÃO do ano inteiro."* É a
> invariante **I3**, e ela tem guarda próprio.

## D.1 — A fonte, e por que é a mais rica

📊 `GET /renovacoes?dt_ini=&dt_fim=&qtd_pag=5000&pag=1&cancelado=F&resgates=F`
é o **único** endpoint que traz `produtor`, `quant_produtores` e `prod_docs[]`
**em lote**. Sem ele seriam ~3.000 chamadas a `/documento`.

🔴 **Ele filtra por `fimvig`** — que é exatamente o que um radar de renovação
precisa. §A.6 explica por que isso torna a população diferente da do Raio-X.

**Comissão em jogo — duas colunas, porque são duas coisas:**

```text
comissao_da_corretora = val_c do documento, obtido pelo casamento
                        (codfil, nosnum) com documentos_bi
                        📊 o join casa 99% (4.858 de 4.877)

comissao_do_vendedor  = val_r do prod_docs de ordem=1 & indireto='F'
                        vem embutido, sem join
```

⚠️ **O 1% que não casa vai para uma linha própria** — *"N apólices sem comissão
apurada"* — e **nunca** vira zero silencioso. Zero silencioso subestima o que
está em jogo, que é justamente o número que decide se alguém liga para o
cliente.

⚠️ **A janela do `documentos_bi` para o join** precisa cobrir o `inivig` das
apólices que vencem no período: `[dt_ini - 400 dias, dt_fim]`, recortada em anos
civis (I8). 💭 400 dias, e não 366, dá folga para vigências de 13 meses e para
endosso com data deslocada.

🔴 **PII.** 📊 `/renovacoes` devolve `cic` (CPF/CNPJ), `fone` e `email`. **Os
três são descartados na entrada da camada de dados**, antes de qualquer
estrutura em memória. O Radar é agregado por vendedor: **não precisa de nenhum
deles para existir** (I7).

## D.2 — A tool

```python
class RadarInput(BaseModel):
    periodo: Optional[str] = Field(
        default=None,
        description=("A janela de vencimento, como o usuário escreveu. Exemplos: "
                     "'próximos 60 dias', 'setembro', 'próximo trimestre', "
                     "'de 01/09/2026 a 30/11/2026'. Vazio = próximos 90 dias."))


class RadarDeRenovacoesTool(BaseTool):
    exige_async: ClassVar[bool] = True
    name: str = "radar_de_renovacoes"
    description: str = """
    Gera o RADAR DE RENOVAÇÕES do período e devolve o LINK do relatório pronto.
    Mostra, POR VENDEDOR, quantas apólices vencem na janela, quanto de prêmio e
    quanta comissão estão em jogo, e quais vencem primeiro.

    Use quando pedirem: radar de renovações · o que vence · renovações do mês ·
    quem tem mais renovação · comissão em jogo · vencimentos por vendedor ·
    carteira a vencer · quanto está em risco de renovação.

    SEMPRE trabalhe com uma JANELA de vencimento. Se o usuário não disser
    qual, use vazio (o padrão é os próximos 90 dias) — nunca peça o ano inteiro.

    ANTES de chamar, diga em UMA frase curta que vai levantar os vencimentos.
    DEPOIS, entregue o link EXATAMENTE como veio.
    """
```

Estilo do Radar: **`meridian`** (D8) — 📊 é o que o próprio template
`renewals.radar` declara (`templates.py:265`), e é o estilo cujo numeral é
tabular em `td.num`, o que importa numa tabela de dinheiro por vendedor.

## D.3 — Os cálculos do Radar

```text
Para cada renovação r da janela (cancelado=F, resgates=F):
    p = produtor_direto(r.prod_docs)          # I5
    d = documentos_bi[(r.codfil, r.nosnum)]   # 99%
    por_vendedor[p].apolices        += 1
    por_vendedor[p].premio          += r.pretot
    por_vendedor[p].comissao_corretora += (d.val_c se d senão -> sem_apuracao += 1)
    por_vendedor[p].comissao_vendedor  += p.val_r
    por_vendedor[p].mais_urgente     = min(dias_a_vencer)

por_semana[semana_iso] = contagem e prêmio         (o bloco `stacked`)
faixas = {"vence em <=15d", "16-30d", "31-60d", "61-90d", ">90d"}
```

🔴 **`dias_a_vencer` vem da própria API** — 📊 é campo de `/renovacoes`. Não
recalcule a partir de `fimvig` sem conferir contra ele; se divergirem, **vale o
campo da API** e a divergência entra no `aviso`.

⚠️ **Sinistro aberto muda a conversa.** 📊 `/renovacoes` traz `sin_situacao`.
Renovação com sinistro aberto ganha um `pill` de tom `warning` na tabela — é a
que vai subir de preço, e é a que o vendedor precisa ver primeiro.

## D.4 — A composição, completa

```python
composition = [
  {"block": "cover", "props": {
      "eyebrow": "Radar de Renovações", "period": rotulo,     # "próximos 90 dias"
      "title": f"{n} apólices vencem {rotulo} — R$ {comissao} em comissão",
      "subtitle": f"{n_vendedores} vendedores · {n_seguradoras} seguradoras · "
                  f"a primeira vence em {min_dias} dias",
      "verdict": veredito,
      "headline_label": "Comissão em jogo", "headline_value": fmt(comissao_total),
      "headline_delta": None}},              # 🔴 sem delta: não há período anterior

  {"block": "kpis", "props": {
      "title": "A janela de risco",
      "items": [
        {"label": "Apólices a vencer",  "value": n},
        {"label": "Prêmio em jogo",     "value": ...},
        {"label": "Comissão da corretora","value": ...},
        {"label": "Vence em até 15 dias","value": ..., "better": "down"},
        {"label": "Com sinistro aberto", "value": ..., "better": "down"},
        {"label": "Sem vendedor apurado","value": ..., "better": "down"},
      ]}},

  {"block": "verdict", "props": {"text": veredito}},

  {"block": "table", "props": {              # 🔴 A TABELA QUE O FOUNDER PEDIU
      "eyebrow": "Por vendedor",
      "title": f"Quem tem renovação {rotulo}",
      "lede": "Ordenado por comissão da corretora em jogo. "
              "A coluna 'primeiro' é o vencimento mais próximo daquele vendedor.",
      "columns": [
        {"key": "vendedor",  "label": "Vendedor"},
        {"key": "apolices",  "label": "Apólices",   "align": "right", "format": "number"},
        {"key": "premio",    "label": "Prêmio",     "align": "right", "format": "currency"},
        {"key": "com_corr",  "label": "Comissão da corretora", "align": "right",
                              "format": "currency"},
        {"key": "com_vend",  "label": "Repasse ao vendedor",   "align": "right",
                              "format": "currency"},
        {"key": "primeiro",  "label": "Primeiro vence em",     "align": "right",
                              "pill": True},   # tom por urgência
      ],
      "rows": [...], "total": {...}}},

  {"block": "stacked", "props": {
      "eyebrow": "Cronologia", "title": "Vencimentos por semana e por vendedor",
      "value_type": "currency_short",
      "categories": semanas_da_janela,
      "series": [{"name": vendedor, "values": [...]} for vendedor in top_6]}},

  {"block": "ranking", "props": {
      "eyebrow": "Concentração", "title": "Maiores comissões em jogo",
      "value_type": "currency_short", "highlight": 3, "max": 10,
      "items": [{"rotulo": f"{seguradora} · {ramo}", "valor": com,
                 "nota": f"vence em {dias} dias"} ...]}},   # 🔴 SEM nome de segurado

  {"block": "actions", "props": {
      "eyebrow": "Prioridades", "title": "O que fazer nesta semana",
      "items": [...]}},         # owner = vendedor · due = data · impact = comissão

  {"block": "callout", "props": {"tone": "info",
      "title": "O que ficou fora", "text": aviso}},   # sem apuração, sem vendedor
  {"block": "sources", "props": {}},
  {"block": "footer",  "props": {}},
]
```

**`data_contract` real do Radar** (substitui o de `renewals.radar` — D7):

```python
{
 "janela":        {"type": "object", "required": True,
                   "description": "inicio, fim, rotulo, dias"},
 "por_vendedor":  {"type": "array",  "required": True,
                   "description": "codpro, nome, apolices, premio, "
                                  "comissao_corretora, comissao_vendedor, "
                                  "primeiro_vencimento_dias"},
 "por_semana":    {"type": "object", "required": True,
                   "description": "{semana_iso: {codpro: comissao}}"},
 "faixas":        {"type": "object", "required": True,
                   "description": "<=15, 16-30, 31-60, 61-90, >90"},
 "maiores":       {"type": "array",  "required": True,
                   "description": "seguradora, ramo, comissao, dias — SEM segurado"},
 "saneamento":    {"type": "object", "required": True,
                   "description": "sem_apuracao, sem_vendedor, com_sinistro"},
}
```

🔴 **`por_vendedor` é obrigatório no contrato.** Um payload de Radar sem essa
chave é um Radar que desobedeceu o Founder, e o teste D.5 asserção 1 o reprova.

## D.5 — Teste e mutação

**Arquivo:** `backend/tests/test_o_radar_e_por_periodo_e_por_vendedor.py`
**Script:** `npm run test:radar-por-vendedor`

| # | Asserção |
|---|---|
| 1 | 🔴 o `payload` tem `por_vendedor` com **≥ 2** vendedores distintos (I3) |
| 2 | 🔴 a composição tem um bloco `table` cuja primeira coluna é `vendedor` (I3) |
| 3 | 🔴 a janela pedida à API tem **≤ 366 dias**, e com `periodo` vazio tem **90** |
| 4 | 🔴 **CONTROLE**: uma composição montada com os mesmos dados **agregados** (sem vendedor) é **reprovada** pelo mesmo guarda — provando que 1 e 2 conseguem ficar vermelhas |
| 5 | a chamada usa `cancelado=F`, `resgates=F` e `qtd_pag=5000` |
| 6 | a paginação percorre até a última página; com 2 páginas de 5.000, chegam 10.000 linhas, não 5.000 |
| 7 | 🔴 `cic`, `fone` e `email` **não existem** em nenhuma estrutura em memória depois da entrada — varredura recursiva do dataclass (I7) |
| 8 | as apólices sem casamento em `documentos_bi` viram `saneamento.sem_apuracao`, **não** comissão zero |
| 9 | `dias_a_vencer` vem da API; divergência de `fimvig` entra em `aviso` |
| 10 | renovação com `sin_situacao` aberto recebe `pill` de tom `warning` |
| 11 | o bloco `ranking` **não** contém nome de segurado — varredura de `rotulo` contra a lista de clientes da fixture |
| 12 | `visual_style='meridian'` é passado explicitamente |

| Mutação | Esperado |
|---|---|
| **M1** — agregar tudo e remover `por_vendedor` | asserções 1 e 2 **vermelhas** |
| **M2** — janela padrão vira o ano inteiro | asserção 3 **vermelha** |
| **M3** — `qtd_pag` some | asserções 5 e 6 **vermelhas** |
| **M4** — o não-casado vira `comissao = 0` | asserção 8 **vermelha** |
| **M5** — `cliente` volta ao dataclass | asserções 7 e 11 **vermelhas** |
| **M6 (controle)** — trocar a ordem das colunas 3 e 4 da tabela | **VERDE** — o guarda exige a coluna `vendedor`, não uma ordem decorada |

---

# 11. BLOCO E — A Resulta ganha marca de verdade

**Gate:** o HTML de uma peça da Resulta contém `<img src="data:image/png;base64,`
e o diagnóstico do render devolve `marca_padrao: False`.

## E.1 — O estado medido, e o que ele custa

📊 18/08/2026:

```sql
select company_id, display_name, (palette->>'primary') as primaria,
       logo_asset_id, visual_style, capture_status
  from brand_profiles;
```

```text
3 linhas · primaria = NULL nas três · logo_asset_id = NULL nas três
```

Consequência, medida no código: `snapshot_para_artefato` cai no ramo de fallback
(📊 `brand/capture.py:554-558`) e devolve
`{"palette": build_design_system("#2C6E8F", "#D98324"), "logo": None,
"visual_style": "aurora", "is_fallback": True}`.

**Os 40 artifacts em produção saíram assim: azul-petróleo genérico, sem logo.**

📊 E a marca real existe, num script offline:
`backend/tools/gerar_visual_acceptance_pack.py:62-96` monta, à mão,
`name="Resulta Seguros"`, `legal_name="Resulta Corretora de Seguros Ltda."`,
`susep_code="20.2185.4"`, telefone `(48) 3364-6664`, cores `#1D5579` / `#EE7501`
e o `data_uri` da logo. 📊 Nada disso está no banco.

## E.2 — O caminho, e por que é este (D9)

📊 `render.py:67-72` procura a logo nesta ordem:
`data_uri` → `public_url` → `storage_ref`.
📊 `snapshot_para_artefato` só devolve `storage_ref`.
📊 `brand_assets.storage_ref` é `text NOT NULL`, **sem CHECK de formato**.

**Logo: grava-se o `data:` URI dentro de `storage_ref`.** 📊 6.282 caracteres.
Zero código novo, zero migration, zero edição em arquivo congelado.

> ⚠️ **Isto é um desvio de intenção da coluna, e está declarado.** O comentário
> da migration diz *"caminho canônico bucket/path (SPEC-054)"*. O caminho
> canônico não existe: 📊 **nenhum código do repositório sobe logo para MinIO**,
> e a única escrita em `brand_assets` (`capture.py:300`) já grava ali a URL
> externa do site com o comentário *"reescrito ao subir p/ storage"* — uma
> reescrita que nunca foi implementada. **A coluna já não guarda o que o nome
> promete.** Esta SPEC não piora isso; ela registra **P-223** para consertar o
> campo, que é o que o CLAUDE.md §12.1 manda fazer.

## E.3 — Os passos exatos

**Arquivo novo:** `backend/tools/instalar_marca_resulta.py`

```bash
python backend/tools/instalar_marca_resulta.py --company <UUID_DA_RESULTA> --dry-run
python backend/tools/instalar_marca_resulta.py --company <UUID_DA_RESULTA>
```

O que ele faz, nesta ordem:

```text
1. Lê backend/tools/_resulta_logo.png            📊 4.694 bytes
2. analisar_logo(dados, "image/png")             ← app.services.brand.extract, JÁ EXISTE
      -> width, height, has_transparency, ink_colors[], primary, accent
   🔴 Se `primary` sair diferente de #1D5579, VALE O MEDIDO, não o script de
      aceite. O pixel é a fonte; o script era um chute com fallback.
3. data_uri = "data:image/png;base64," + b64(dados)          📊 6.282 chars
4. upsert em brand_assets, on_conflict="company_id,kind":
      company_id, kind='logo_primary', storage_ref=<data_uri>,
      mime_type='image/png', byte_size=4694, width, height, has_transparency,
      ink_colors=[...], source_url=NULL, source_kind='upload',
      confidence=1.00, is_current=true
   -> guarda o id devolvido
5. BrandCaptureService(db).editar(company_id, valores, user_id=None) com:
      palette      = {"primary": <medida>, "accent": <medida>}
      logo_asset_id= <id do passo 4>
      display_name = "Resulta Seguros"
      legal_name   = "Resulta Corretora de Seguros Ltda."
      susep_code   = "20.2185.4"
      contact      = {"phone": "(48) 3364-6664"}
      visual_style = "aurora"
   📊 `editar()` (capture.py:494) re-deriva o sistema de design inteiro quando
      recebe `palette` (capture.py:505-512) e marca provenance human_edited.
6. Imprime o VERIFY do §E.4 já executado.
```

⚠️ **Passo 4, cuidado com o índice.** 📊 Existe
`brand_assets_one_current_per_kind UNIQUE (company_id, kind) WHERE is_current`.
O `upsert` com `on_conflict="company_id,kind"` é o mesmo que `capture.py:307`
usa e respeita o índice. **Não faça `insert` puro.**

⚠️ **`--dry-run` é obrigatório na primeira execução** e imprime as cores
medidas, o tamanho do data URI e o SQL que seria executado. Rodar direto em
produção sem ver as cores é como publicar um relatório sem olhar.

## E.4 — VERIFY

```sql
-- 1. O asset existe e é um data URI.
select id, kind, mime_type, byte_size, width, height, is_current,
       left(storage_ref, 30) as inicio_do_ref, length(storage_ref) as tam
  from brand_assets
 where company_id = '<UUID>' and kind = 'logo_primary';
-- ESPERADO: 1 linha · inicio_do_ref = 'data:image/png;base64,iVBORw0KGg'
--           tam ~ 6282 · byte_size = 4694 · is_current = true

-- 2. O perfil aponta para ele e tem cor.
select display_name, (palette->>'primary') as primaria,
       (palette->>'accent') as acento, logo_asset_id, visual_style
  from brand_profiles where company_id = '<UUID>';
-- ESPERADO: primaria NÃO nula, logo_asset_id = o id do passo 1

-- 3. 🔴 A prova que importa: uma peça nova sai COM marca.
--    (rodar o Raio-X e depois:)
select a.id, a.title, (v.brand_snapshot->>'is_fallback') as marca_padrao,
       (v.brand_snapshot->'logo'->>'storage_ref' is not null) as tem_logo,
       position('data:image/png;base64,' in r.inline_content) > 0 as logo_no_html
  from artifacts a
  join artifact_versions v on v.artifact_id = a.id
  join artifact_renders  r on r.artifact_version_id = v.id
 where a.company_id = '<UUID>' and a.origin = 'chat'
 order by a.created_at desc limit 1;
-- ESPERADO: marca_padrao = false · tem_logo = true · logo_no_html = true
```

## E.5 — UNDO, escrito antes de aplicar

```sql
-- Volta ao estado de 18/08/2026. Nenhuma linha é apagada de brand_assets:
-- desligar `is_current` basta, e preserva a auditoria.
update public.brand_profiles
   set palette = '{}'::jsonb, logo_asset_id = null
 where company_id = '<UUID>';

update public.brand_assets
   set is_current = false
 where company_id = '<UUID>' and kind = 'logo_primary'
   and storage_ref like 'data:image/png;base64,%';
```

⚠️ **O UNDO não desfaz peças já geradas** — o snapshot é congelado por versão
(📊 `service.py:158`), de propósito: um artifact é registro, não view. Peças
antigas continuam como estavam; as novas voltam ao fallback.

## E.6 — 🔴 O efeito colateral na Cobrança, declarado

Dar marca à Resulta muda **também** a aparência das peças que a Cobrança gerar
dali em diante: elas passam a sair com a logo e as cores da Resulta em vez do
azul-petróleo genérico.

**Isso é melhoria, e não regressão** — mas é **efeito**, e efeito não declarado
vira surpresa no palco. Por isso:

- está escrito aqui;
- é revertido por dois `UPDATE` (§E.5);
- e o §Bloco G.4 tem uma asserção que **executa** a composição da Cobrança com a
  marca nova e verifica que ela **continua saindo inteira**.

## E.7 — Teste

**Arquivo:** `backend/tests/test_a_resulta_tem_marca.py`
**Script:** `npm run test:resulta-tem-marca`

| # | Asserção |
|---|---|
| 1 | `analisar_logo` sobre `_resulta_logo.png` devolve `ink_colors` não vazio e `primary` válido |
| 2 | o data URI começa com `data:image/png;base64,` e tem 6.282 caracteres |
| 3 | `render_html` com `brand={"logo": {"storage_ref": <data_uri>}, ...}` produz HTML com `<img src="data:image/png;base64,` |
| 4 | 🔴 **CONTROLE**: com `logo=None`, o mesmo render produz `ab-cover-wordmark` e **nenhum** `<img` de capa — provando que a asserção 3 mede a logo |
| 5 | com `palette.primary` preenchida, `snapshot_para_artefato` devolve `is_fallback: False` |
| 6 | 🔴 **CONTROLE**: com `palette` vazia, devolve `is_fallback: True` |
| 7 | o script tem `--dry-run` e, com ele, **nenhuma** escrita acontece |

| Mutação | Esperado |
|---|---|
| **M1** — data URI vira caminho `bucket/path` | asserção 3 **vermelha** |
| **M2** — `is_current` sai do upsert | 4 assertions do VERIFY falham (índice único) |
| **M3 (controle)** — trocar `#1D5579` por outra cor válida | **VERDE** — o teste mede a presença da marca, não a cor exata |

---

# 12. BLOCO F — O pré-aquecimento, e o silêncio de 45 segundos

**Gate:** com o cache quente, o Raio-X de um ano volta em **menos de 5 s**
medidos; e o chat **não fica mudo** enquanto a tool roda.

## F.1 — O problema, medido

📊 4 anos de produção + carteira = **8-10 chamadas à InfoCap, ~45 s**.
Latência típica 0,7-1,0 s por chamada; lote grande, 4-9 s.

📊 E não há nada que preencha esse tempo: `graph.py:1596-1599` só deixa passar
tokens do nó `agent`; enquanto o nó `tools` roda, **zero bytes** saem pelo SSE.
📊 Não há timeout que mate a tool — nem em `nodes.py`, nem em `chat.py`, nem no
proxy do Next (`app/api/chat/stream/route.ts:32-40`, `fetch` sem
`AbortController`), nem no browser. **A tool não morre; ela só emudece.**

## F.2 — Três medidas, nesta ordem de importância

### 1. Pré-aquecer (a que realmente resolve)

**Arquivo novo:** `backend/scripts/preaquecer_comercial.py`

```bash
python backend/scripts/preaquecer_comercial.py \
       --company <UUID_DA_RESULTA> \
       --anos 2023 2024 2025 2026 \
       --renovacoes-dias 180
```

O que faz: chama a **mesma** função da camada de dados que a tool chama, para
cada ano, e para a janela de renovações. Grava nas **mesmas** chaves de Redis.
Imprime o tempo de cada chamada e o total.

```text
[preaquece] 2023  documentos_bi   1,4 s   5.503 linhas
[preaquece] 2023  producao (2 pg) 2,1 s   5.611 linhas
...
[preaquece] renovacoes 180d       9,2 s   1.341 linhas
[preaquece] TOTAL 41,8 s · 9 chaves gravadas · TTL 21600 s (6 h)
```

🔴 **Rodar 20 a 30 minutos antes da apresentação.** TTL de 6 h dá folga
confortável; rodar de novo é barato e idempotente.

**Conferir se está quente, em um segundo:**

```bash
python backend/scripts/preaquecer_comercial.py --company <UUID> --so-conferir
# imprime, por chave: EXISTE (ttl 19.842 s) | FALTA
```

### 2. O modelo anuncia antes de chamar (D10)

Já especificado em §C.1: a última linha da `description` de cada tool manda
dizer uma frase curta antes. 📊 Funciona porque `llm_factory.py:155` liga
`streaming: True` e o Claude emite o bloco de texto **antes** do `tool_use`.

💭 O que o Founder vê, aproximadamente:

```text
[digita]  me faz o raio-x comercial de 2025

[0,8 s]   Vou levantar a produção de 2025 na InfoCap — leva alguns segundos.
[bolinhas pulando por 2 a 5 s, com cache quente]
[~5 s]    ✅ Raio-X Comercial · 2025 pronto.
          Abrir: https://…/dashboard/entregas/8f3a…
```

### 3. O que NÃO entra agora

Evento de progresso no SSE (P-227) e heartbeat (P-228). 📊 O motivo é
`chat.py:600`: `full_response += token` — **tudo que passa pelo canal é
persistido como a mensagem do assistente**. Um "estou trabalhando…" viraria
parte do histórico. Fazer isso direito exige um segundo canal de evento, e isso
é mudança em dois arquivos do caminho do chat na véspera. **Nota 60.**

## F.3 — Teste

**Arquivo:** `backend/tests/test_o_cache_esquenta_e_o_chat_fala.py`
**Script:** `npm run test:cache-esquenta`

| # | Asserção |
|---|---|
| 1 | com cache quente (Redis falso pré-preenchido), a camada faz **zero** requisições HTTP |
| 2 | 🔴 **CONTROLE**: com cache frio, faz **N** requisições — provando que 1 mede o cache |
| 3 | a chave contém `company_id`; corretora B não lê a chave de A (I10) |
| 4 | Redis fora do ar → resultado idêntico, com log em `warning`, **sem exceção** |
| 5 | `--so-conferir` não escreve nada no Redis |
| 6 | a `description` das duas tools contém a instrução de anunciar antes |
| 7 | a mesma função é usada pelo script e pela tool — comparação por `is` do objeto importado |

| Mutação | Esperado |
|---|---|
| **M1** — o script grava numa chave própria | asserções 1 e 7 **vermelhas** |
| **M2** — `except` do Redis vira `raise` | asserção 4 **vermelha** |
| **M3 (controle)** — TTL diferente entre script e tool | **VERDE** — o que importa é a chave, não o prazo |

---

# 13. BLOCO G — 🔴 Prova de não-regressão

**Gate:** `git diff` contra a baseline não mostra **nenhum** dos arquivos
congelados, e a linha de controle prova que o comando **sabe** enxergar
mudanças.

> Este bloco é o que autoriza a SPEC a existir na véspera de duas
> apresentações. Sem ele, tudo acima é risco.

## G.1 — A lista congelada

**Nenhuma linha destes arquivos muda.**

### Atendimento

```text
backend/app/api/infocap_connector.py          ← IMPORTADO em §A.2, nunca editado
backend/app/api/webhook.py
backend/app/api/whatsapp_channel.py
backend/app/providers/policy_data_provider.py
backend/app/agents/nodes.py                   ← nenhum `elif` novo (§C.6)
backend/app/agents/tools/infocap_tool.py
backend/app/agents/tools/insurer_dispatch_tool.py
backend/app/agents/tools/human_handoff.py
backend/app/agents/tools/portal_tool.py
backend/app/agents/tools/portal_params.py
backend/app/services/corridor_playbooks.py
backend/app/services/insurer_dispatch_service.py
backend/app/services/dispatch_router.py
backend/app/services/dispatch_mirror.py
backend/app/services/message_buffer_service.py
backend/app/services/whatsapp_service.py
backend/app/services/whatsapp/                (diretório inteiro)
backend/app/core/prompts.py
```

### Cobrança

```text
backend/app/services/billing_collection.py    ← COPIADO como padrão, nunca editado
backend/app/services/billing_gate.py
backend/app/services/billing_avisos.py
backend/app/services/billing_service.py
backend/app/workers/billing_tasks.py
backend/portal_worker/worker.py
backend/portal_worker/journeys/                (diretório inteiro)
```

### Artifacts e marca — 📊 os cinco que o Founder nomeou, mais dois

```text
backend/app/services/artifacts/blocks.py       🔴 os cinco nomeados
backend/app/services/artifacts/charts.py
backend/app/services/artifacts/styles.py
backend/app/services/artifacts/render.py
backend/app/services/artifacts/service.py
backend/app/services/artifacts/templates.py    ← acrescentado por D7 (nota 90)
backend/app/services/brand/capture.py          ← acrescentado por D9 (nota 92)
backend/app/api/artifacts.py
```

> **Por que `templates.py` e `capture.py` entram na lista mesmo não tendo sido
> nomeados:** os dois são importados **dentro** do caminho que a Cobrança
> percorre para gerar a peça dela — `service.criar()` chama
> `_garantir_template` (que importa `POR_CHAVE`) e `snapshot_para_artefato`.
> Congelá-los custa **nada** (D7 e D8 já resolveram sem eles) e remove duas
> chances de quebrar a Cobrança.

### Frontend — 🔴 nenhum arquivo de `app/`, `components/`, `lib/`

Nem `middleware.ts`, nem `next.config.js`, nem `instrumentation.ts`.
**Consequência:** o gate do CLAUDE.md §9.1 não é disparado por mudança. Ele
**roda mesmo assim** (§19) — porque "não mexi em `app/`" é uma afirmação, e
afirmação se verifica.

## G.2 — O que a SPEC de fato toca

```text
NOVO   backend/app/services/comercial/__init__.py
NOVO   backend/app/services/comercial/fonte_infocap.py
NOVO   backend/app/services/comercial/calculos.py
NOVO   backend/app/services/comercial/periodo.py
NOVO   backend/app/services/comercial/peca_raio_x.py
NOVO   backend/app/services/comercial/peca_radar.py
NOVO   backend/app/agents/tools/comercial_tools.py
NOVO   backend/scripts/preflight_infocap_bi.py
NOVO   backend/scripts/preaquecer_comercial.py
NOVO   backend/tools/instalar_marca_resulta.py
NOVO   backend/tests/test_*.py                (6 arquivos) + fixtures/

EDITA  backend/app/agents/graph.py            +1 bloco try/except DENTRO do `if core`
EDITA  backend/app/agents/gateway_cutover.py  +2 linhas em NOME_PARA_CHAVE
EDITA  package.json                           +7 scripts de teste
EDITA  backend/app/agents/tools/report_tool.py  +1 linha  ← 🔴 BLOCO H, OPCIONAL

DOCS   backend/app/data/global_knowledge/infocap-corpapi-mapa.md
DOCS   docs/canon/INFOCAP-CORPAPI-MAPA.md
DOCS   docs/canon/specs/SPEC-065-carteira-e-dinheiro-visivel.md   (status e §1.3)
DOCS   docs/canon/PENDENCIAS.md · CHANGE-ADDENDA.md · FOUNDER-DECISIONS.md

DML    brand_assets + brand_profiles da Resulta                  ← BLOCO E, com UNDO
```

**Três arquivos de produção editados. Um deles é opcional.** É esse o tamanho
do risco.

## G.3 — O teste

**Arquivo:** `backend/tests/test_o_raiox_nao_encosta_no_atendimento_nem_na_cobranca.py`
**Script:** `npm run test:raiox-nao-encosta`

Escrito no idioma da casa — script solo, `check()`, `sys.exit(1 if FAIL else 0)`
— espelhando 📊 `backend/tests/test_a_cobranca_esta_como_estava.py`.

```python
BASE = "db2d9f12c90311ee45a26f66ba5aa10716a27cb1"   # §2.1

def mudou(caminho: str) -> bool:
    saida = subprocess.run(["git", "diff", "--name-only", BASE, "--", caminho],
                           cwd=RAIZ_DO_REPO, capture_output=True, text=True).stdout
    return bool(saida.strip())
```

| # | Asserção |
|---|---|
| 1 | **nenhum** dos ~30 caminhos congelados do §G.1 aparece no `git diff` contra a baseline |
| 2 | 🔴 **CONTROLE**: `backend/app/services/comercial/` **aparece** — provando que o comando enxerga mudança. Sem esta linha, um `git diff` que devolvesse vazio por erro de path passaria em tudo |
| 3 | 🔴 **CONTROLE 2**: um caminho inventado (`backend/app/nao_existe/`) devolve vazio — provando que a asserção 2 não é vazia por acaso |
| 4 | `git diff --name-only BASE -- app/ components/ lib/ middleware.ts next.config.js` é **vazio** |
| 5 | AST de `graph.py`: os dois `tools.append` novos estão **dentro** do `if` que testa `core` (o Atendimento não os recebe) |
| 6 | AST de `graph.py`: `insurer_dispatch` continua **fora** do bloco do core, como estava |
| 7 | `_TOOLS_SEMPRE_ASYNC` em `nodes.py` tem os **mesmos 4 nomes** de antes |
| 8 | a Cobrança ainda insere em `portal_jobs` com `journey='cobranca_sweep'` (herda de `test_a_cobranca_esta_como_estava.py`) |
| 9 | `billing_collection` ainda usa `template_key='financial.billing_collection'` e `origin='routine'` |
| 10 | `motivo_para_barrar(<portal>, 'cobranca_sweep') == ""` para os 6 portais |
| 11 | 🔴 **CONTROLE 3**: `motivo_para_barrar('vidros_lanternas', 'abrir_atendimento')` **não** é vazio — o freio ainda freia alguma coisa |
| 12 | `send_message` continua com os 3 primeiros parâmetros posicionais na mesma ordem |
| 13 | nenhum módulo de `services/comercial/` é importado por qualquer arquivo congelado — varredura de `import` |

## G.4 — A asserção da marca (o efeito colateral do §E.6)

| # | Asserção |
|---|---|
| 14 | `compor_peca_da_cobranca(...)` com a marca **nova** produz composição **não vazia**, e `render_html` devolve `falhas == []` e `desconhecidos == []` |
| 15 | 🔴 **CONTROLE**: a mesma composição com a marca **antiga** (fallback) também produz `falhas == []` — provando que 14 mede a peça, não a marca |
| 16 | os dois HTML têm o **mesmo número de blocos**; o que muda é cor e logo, não estrutura |

| Mutação | Esperado |
|---|---|
| **M1** — tocar uma linha em `billing_collection.py` | asserção 1 **vermelha** |
| **M2** — tocar uma linha em `render.py` | asserção 1 **vermelha** |
| **M3** — mover o `append` das tools para fora do `if core` | asserção 5 **vermelha** |
| **M4** — apagar `backend/app/services/comercial/` | asserção 2 **vermelha** |
| **M5** — trocar o SHA da baseline por `HEAD` | asserção 2 **vermelha** (nada mudou contra si mesmo) |
| **M6 (controle)** — acrescentar um comentário num arquivo **não** congelado (`graph.py`) | **VERDE** — a lista congelada não é "o repositório inteiro" |

> 🔴 **M5 é a mutação mais importante deste bloco.** Um teste de não-regressão
> que compare `HEAD` com `HEAD` passa sempre e não guarda nada — é o "guarda que
> não tem como falhar" do CLAUDE.md §9.3.

---

# 14. BLOCO H — Os dois consertos avulsos (OPCIONAL, e separado de propósito)

> 🔴 **Nada dos §Blocos A-G depende deste bloco.** Ele pode ser executado
> depois da apresentação sem custo nenhum. Está aqui porque a SPEC o descobriu,
> e CLAUDE.md §11 manda registrar o que se descobre.

## H.1 — O `exige_async` do `report_tool` (uma linha)

📊 `backend/app/agents/tools/report_tool.py`, junto ao `name` (linha 184):

```python
    exige_async: ClassVar[bool] = True     # espelha human_handoff.py:294
```

📊 O executor já lê a declaração (`nodes.py:1084`). Com essa linha,
`gerar_relatorio` deixa de receber o bilhete do `_run` e passa a executar.

⚠️ **Isso NÃO conserta a tool.** Os defeitos 2 e 3 do §0.2 continuam: o modelo
ainda tem de inventar o payload, e sem `compartilhar=True` ainda não sai link. A
linha só devolve a tool ao caminho correto. **Vai para P-230** o resto.

⚠️ E há um risco real de ligar isso na véspera: uma tool que hoje **não executa**
passaria a executar, e o modelo pode escolhê-la em vez das duas novas — 📊 as
pistas de `escolher()` incluem `"venda"` e `"comiss"`
(`templates.py:813-814`), que são exatamente as palavras do Founder.
**Recomendação: executar o Bloco H DEPOIS de 19/08.**

**Teste:** herdar o padrão de
📊 `backend/tests/test_a_atendente_nao_mente_sobre_transferir.py:199-223`, que
já verifica estaticamente a declaração e o `if` do executor.

## H.2 — 🔴 A correção dos documentos que ensinaram errado

Três arquivos afirmam que rotas inexistentes são "negadas por permissão", e essa
afirmação **já custou uma conclusão errada e dezessete dias** (§0.4).

### 1. `backend/app/data/global_knowledge/infocap-corpapi-mapa.md:42-48`

Este é o mais grave: 📊 ele é **injetado no conhecimento global dos agentes**.
Um agente que leia isso responde ao corretor que a comissão está bloqueada.

A seção `## Endpoints NEGADOS no perfil padrão` é **substituída** por:

```markdown
## Rotas que NÃO EXISTEM nesta API (403 do API Gateway, não é permissão)

📊 Medido em 18/08/2026. `/comissao`, `/comissoes`, `/parcelas`, `/financeiro`,
`/titulos`, `/contas_receber`, `/contas_pagar`, `/fluxo_caixa`, `/faturamento`,
`/vendedores`, `/usuarios`, `/propostas`, `/sinistro`, `/endossos`, `/tarefas`,
`/agenda`, `/cias`, `/filiais` devolvem **403 com texto de assinatura SigV4** —
que é como o AWS API Gateway responde a uma rota que não está registrada.
**Não é flag de perfil. Não há o que a corretora liberar.**

Prova: `/rota_que_nao_existe` devolve o MESMO 403.

## Onde os dados realmente estão

| O que se quer | Onde está |
|---|---|
| comissão da corretora | `base_c`, `per_c`, `val_c` **dentro do documento** |
| repasse ao produtor | `prod_docs[]`: `codpro, ordem, indireto, per_r, val_r` |
| vendedor / produtor | `prod_docs[]` com `ordem=1` e `indireto="F"` (o DIRETO) |
| produção por período | `GET /documentos_bi?datini&datfim&data=INIVIG&tipo_doc=TODOS` |
| cancelamento e `tipdoc` | `GET /producao?...&qtd_pag=5000&pag=N` |
| renovações a vencer | `GET /renovacoes?dt_ini&dt_fim&qtd_pag=5000&cancelado=F` |
| lista de produtores | `GET /produtores?texto=&codage=1` (📊 116) |

⚠️ `documentos_bi` **inclui apólices canceladas** e **mistura `tipdoc`** —
cruze com `/producao` antes de somar qualquer coisa.
⚠️ `val_cp` está 📊 zerado em 100% das 16.693 linhas. Não use.
```

### 2. `docs/canon/INFOCAP-CORPAPI-MAPA.md:26-37` — a mesma correção

### 3. `docs/canon/specs/SPEC-065-carteira-e-dinheiro-visivel.md`

Linha 2 (`status`) e §1.3 (linha 82) — conforme a decisão D-a/D-b do §2.3.
**Não reescrever a SPEC-065**: acrescentar um bloco `> ⚠️ CORRIGIDO EM 18/08/2026
PELA SPEC-081` no topo e no §1.3, preservando o texto original. 📊 É o padrão de
correção que o repositório já usa e que não apaga a história.

### 4. `docs/canon/PENDENCIAS.md`, P-01

📊 P-01 diz *"A API da InfoCap devolve 500 no pós-login"*, medido em 02/08/2026,
e é declarada como *"bloqueia a SPEC-065 inteira"*. O §2.4 desta SPEC re-mede
o login. Se voltar 200, **P-01 é resolvida com a saída colada**; se voltar 500,
a SPEC-081 para (§2.4) e P-01 continua, agora com data nova.

> **Por que a correção é bloco e não nota de rodapé:** CLAUDE.md §9.3 —
> *"teste que guarda verdade vencida é pior que teste nenhum"*. Um documento de
> conhecimento **injetado no agente** que afirma um bloqueio inexistente é
> exatamente isso, e ele responde ao corretor todos os dias.

---

# 15. 🔴 O QUE O FOUNDER DIGITA

> Esta seção existe porque ele vai estar no palco, com plateia, e nervoso. As
> frases têm de ser naturais e **tolerantes**. Nada aqui depende de o Founder
> lembrar de uma sintaxe.

## 15.1 Onde ele digita

**Dashboard da Resulta → Chat** (`/dashboard/chat`). É o agente `AutoBrokers`,
`agent_role='core'` — 📊 a Resulta tem esse agente com `is_active=true`.

🔴 **Não é o WhatsApp.** As duas tools só existem no agente `core` (§C.6, gate
G.3 asserção 5). Isso é proteção do Atendimento, não limitação.

## 15.2 As duas frases principais

```text
1)   me faz o raio-x comercial de 2025

2)   radar de renovações dos próximos 90 dias
```

**É só isso.** As duas funcionam sem mais nada.

## 15.3 O que também funciona — Raio-X

Todas estas caem em `raio_x_comercial`, porque a `description` da tool carrega
os gatilhos (§C.1):

```text
raio-x comercial
raio x comercial de 2025
quem mais vende na Resulta
ranking de vendedores
ranking de vendedores do ano passado
quanto cada vendedor rendeu esse ano
desempenho comercial do primeiro semestre
produção comercial de 2025
resultado comercial dos últimos 12 meses
comissão por vendedor
quanto custa cada canal
custo de aquisição por canal
me mostra quem vende, quanto rende e quanto custa
relatório de vendas de agosto
```

## 15.4 O que também funciona — Radar

```text
radar de renovações
o que vence nos próximos 60 dias
quem tem mais renovação esse mês
renovações de setembro
comissão em jogo nas renovações
vencimentos por vendedor
carteira a vencer no próximo trimestre
quanto está em risco de renovação até dezembro
```

## 15.5 Como ele fala o período — todas estas o código entende

📊 A tabela completa está no §B.1. As formas naturais:

```text
2025 · 2024 · 2023
este ano · ano atual · ano passado
últimos 12 meses · últimos 6 meses
primeiro semestre · segundo semestre · 3o trimestre
agosto · agosto de 2025 · setembro
próximos 30 / 60 / 90 dias
de 01/03/2026 a 30/06/2026
```

🔴 **E se ele não disser período nenhum**, ou disser algo que o parser não
entende: **sai relatório mesmo assim**, no padrão, e a **capa diz qual período
foi usado**. Nunca uma pergunta de volta, nunca um erro. (§B.1)

## 15.6 O que ele vê, etapa por etapa

```text
ETAPA 1  ·  ele digita e aperta Enter
            a mensagem dele aparece na direita

ETAPA 2  ·  ~1 s
            "Vou levantar a produção de 2025 na InfoCap — leva alguns segundos."
            (o texto sai token a token, D10)

ETAPA 3  ·  2 a 5 s com o cache quente (§Bloco F)
            três bolinhas pulando

ETAPA 4  ·  o assistente escreve:
            ✅ Raio-X Comercial · 2025 pronto.
               Abrir: https://…/dashboard/entregas/8f3a…
               R$ 3,09 mi em comissão · 3.272 apólices · ticket médio R$ 4.492
               Maior vendedor: RAFAEL L SILVEIRA-EXECUTIVO, R$ 537.970.
               Canal mais caro: DVA BYD ITAJAI, 50,0% em repasse.

ETAPA 5  ·  ele CLICA no link
            abre /dashboard/entregas/<id>: cabeçalho com título e data,
            e o relatório inteiro num iframe

ETAPA 6  ·  a peça, de cima para baixo
            CAPA        logo da Resulta · "Raio-X Comercial · 2025" ·
                        veredito · R$ 3,09 mi em destaque
            KPIS        6 números com seta contra 2024
            VEREDITO    o parágrafo
            GRÁFICO     comissão mês a mês, 2025 contra 2024
            RANKING     vendedores por comissão | ROSCA comissão por ramo
            TABELA      🔴 CUSTO DE AQUISIÇÃO POR CANAL — 4,9% contra 50,0%
            EMPILHADO   mix de ramo por vendedor
            ROSCA       novo contra renovação
            AVISO       o que ficou de fora (canceladas, tipdoc, estornos)
            AÇÕES       o que fazer
            FONTES      InfoCap · CorpAPI, com a hora da consulta
            RODAPÉ      logo, SUSEP, data por extenso
```

## 15.7 🔴 Os três socorros, decorados

Se algo travar no palco:

```text
1. "não entendeu o pedido"
   -> digite exatamente:  raio-x comercial
   (sem período — o padrão sai na hora)

2. "demorou demais / parece travado"
   -> ESPERE. Não há timeout: a tool não morre, só demora (§F.1).
      Se passar de 60 s, digite de novo — a segunda vem do cache.

3. "o link não abre"
   -> abra pelo menu: Entregas. O relatório está lá, no topo da lista,
      independentemente do link.
```

📊 A rota `/dashboard/entregas` já lista artifacts com `.eq('company_id', …)` e
`href = /dashboard/entregas/${a.id}`
(`app/api/dashboard/entregas/route.ts:241`). **A entrega existe mesmo que o
chat engasgue.**

## 15.8 O que dizer se perguntarem de onde vêm os números

> *"Direto do sistema de gestão da corretora, a InfoCap, no momento em que eu
> pedi. Não é planilha, não é estimativa, e o próprio relatório mostra o que
> ficou de fora da conta — apólices canceladas, documentos que não são apólice,
> e estornos."*

📊 E é verdade: o bloco `sources` carrega `as_of` com a hora da consulta
(§C.5), e o bloco `callout` de saneamento é obrigatório (§C.4).

---

# 16. O ENSAIO — o roteiro de hoje à noite

> Fazer **na ordem**, colando a saída de cada passo no relatório. Um passo que
> não produzir a saída esperada **para o ensaio**, não o passo seguinte.

```text
 0. PREFLIGHT DE REDE  (§2.4)
    python backend/scripts/preflight_infocap_bi.py --company <UUID>
    ESPERADO: 200 no login · linhas em documentos_bi · e a QUINTA requisição
              devolvendo 403 com "Credential=" (a linha de controle).
    🔴 Login 500 -> PARE. É a P-01 de volta, e é parada legítima.

 1. CONFIRMAR A POPULAÇÃO  (§A.6)
    ... --contar-renovacoes 01/01/2025 31/12/2025
    ESPERADO: 3536 (±5). Anote o número real.

 2. GRAVAR A FIXTURE ANONIMIZADA
    ... --gravar-fixture backend/tests/fixtures/infocap_2025_anon.json
    CONFERIR À MÃO: grep -c "cic\|fone\|email" no arquivo -> 0

 3. RODAR OS TESTES OFFLINE
    npm run test:comissao-nao-triplica
    npm run test:periodo-do-founder
    npm run test:calculos-raio-x
    ESPERADO: ranking = tabela §A.5 · 4,9% e 50,0% no custo · 2.301/971

 4. A MARCA  (§Bloco E)
    python backend/tools/instalar_marca_resulta.py --company <UUID> --dry-run
    -> conferir as cores medidas e o tamanho do data URI
    python backend/tools/instalar_marca_resulta.py --company <UUID>
    -> rodar o VERIFY do §E.4, passos 1 e 2

 5. PRÉ-AQUECER  (§Bloco F)
    python backend/scripts/preaquecer_comercial.py --company <UUID> \
           --anos 2024 2025 2026 --renovacoes-dias 180
    ESPERADO: 9 chaves gravadas. Anote o tempo total.

 6. 🔴 O ENSAIO DE VERDADE — no chat, logado como a Resulta
    digitar:  me faz o raio-x comercial de 2025
    CRONOMETRAR do Enter até o link aparecer.

 7. CONFERIR NO BANCO — é este SELECT que muda de 0 para 1:

       select origin, created_at, title, status
         from artifacts
        where origin = 'chat'
        order by created_at desc;
       -- ESPERADO: pelo menos 1 linha. Antes de hoje: NENHUMA.

 8. CONFERIR A MARCA NA PEÇA  (§E.4, passo 3)
    ESPERADO: marca_padrao = false · logo_no_html = true

 9. CLICAR NO LINK
    ESPERADO: a peça abre, com logo, e a TABELA DE CUSTO POR CANAL está lá.
    Ler os números em voz alta. Se algum parecer errado, ele está errado.

10. O RADAR
    digitar:  radar de renovações dos próximos 90 dias
    ESPERADO: tabela COM coluna de vendedor, ≥ 2 vendedores (I3).

11. AS VARIAÇÕES  (§15.3 e §15.4) — testar pelo menos SEIS, incluindo:
       "quem mais vende"
       "ranking de vendedores do ano passado"
       "raio-x comercial"            (sem período)
       "o que vence nos próximos 60 dias"
       "quem tem mais renovação esse mês"
       "me faz aí aquele relatório"  (o pedido vago)

12. 🔴 O SOCORRO Nº 3
    Abrir /dashboard/entregas e confirmar que os relatórios de hoje estão
    listados e abrem — o caminho que não depende do chat.

13. 🔴 NÃO-REGRESSÃO — a última coisa da noite, e a mais importante
    npm run test:raiox-nao-encosta
    npm run test:cobranca-intacta
    npm run test:atendente-nao-mente
    npm run test:corredor-residencial
    npm run test:freio-vidros-nao-mata-cobranca
    npm run test:entregas-abrem
    npm run test:rotas-montam
    ESPERADO: todos verdes.

14. E A LINHA DE CONTROLE DA NOITE
    Rodar UMA cobrança em modo teste, ponta a ponta, e conferir que ela
    entrega igual — agora com a logo da Resulta na peça (§E.6).
```

> **O passo 14 é tão obrigatório quanto o 6.** A SPEC promete não quebrar a
> Cobrança; promessa que não é exercida não é prova.

---

# 17. O que NÃO entra nesta SPEC

| | Por quê |
|---|---|
| **Espelho da carteira em tabela** (SPEC-065 §B) | migration + backfill + Work Run. Não cabe em uma noite. Consulta ao vivo com cache resolve o pedido. **P-224** |
| **Consertar `/r/[token]`** | 📊 exige `middleware.ts`, que dispara o gate do CLAUDE.md §9.1 na véspera. E o link de tenant já funciona. **P-229** |
| **Consertar o `report_tool` de verdade** | §Bloco H.1 devolve uma linha; o resto (payload, link) é outra conversa. **P-230** |
| **Inverter a precedência de estilo em `service.py`** | 📊 mudaria as 40 peças existentes, incluindo as da Cobrança. D8 resolveu sem tocar. **P-226** |
| **Templates próprios no `CATALOGO`** | D7, nota 90 contra 78. **P-225** |
| **Evento de progresso no SSE** | 📊 `chat.py:600` persistiria o status como mensagem. **P-227** |
| **Heartbeat SSE** | **P-228** |
| **Ligar o auxiliar `renovacao-maxima`** | 📊 está `coming_soon` no catálogo (`20260802_02_spec064_seed_catalogo.sql:294`) com `runtime.kind='none'`. Mudar estado de catálogo é decisão de produto. **P-231** |
| **Sinistralidade, funil de cotação, clientes perdidos** | outros seis auxiliares travados na mesma premissa. Esta SPEC destrava a premissa; não entrega os seis |
| **Marca das outras duas corretoras** | 📊 as 3 linhas de `brand_profiles` estão vazias. A SPEC entrega a da Resulta, que é a da apresentação. **P-232** |
| **Upload de logo por tela** | 📊 não existe rota que aceite bytes de imagem. **P-223** |

---

# 18. O que fica em `PENDENCIAS.md`

📊 O último ID em uso é **P-214**. ⚠️ A SPEC-080 §14 reserva **P-215 a P-221**.
Esta SPEC começa em **P-222**.

| ID | Título | Dono | O que destrava · o que custa esquecer |
|---|---|---|---|
| **P-222** | O `data_contract` de `commercial.pipeline` e `renewals.radar` não descreve o payload que os dois relatórios gravam | 🤖 | D7. Custa: quem ler o contrato no `templates.py` vai achar que o payload é outro |
| **P-223** | `brand_assets.storage_ref` guarda ora URL externa, ora `data:` URI — nunca o "caminho canônico bucket/path" que o nome promete | 🤖 | 📊 nenhum código sobe logo para MinIO. Destrava com upload real + coluna `data_uri` própria. **É o corolário do CLAUDE.md §12.1: o nome do campo mente** |
| **P-224** | Não existe espelho da carteira; toda leitura é ao vivo com cache de 6 h | 🧑 Founder | decisão D-c do §2.3. Custa: relatório de 4 anos leva ~45 s a frio, e a InfoCap fora do ar deixa o produto sem número nenhum |
| **P-225** | Os dois relatórios usam `template_key` emprestado | 🤖 | D7. Destrava: dois `Template` no `CATALOGO` depois da apresentação |
| **P-226** | 📊 O snapshot da marca VENCE o `visual_style` do template — todos os 40 artifacts saíram `aurora` | 🤖 | `service.py:187-188`. Custa: `obsidian` e `meridian` são inalcançáveis por quem não passa o estilo explícito |
| **P-227** | O chat fica mudo enquanto uma tool roda | 🤖 | 📊 `graph.py:1596` filtra o nó `agent`; `chat.py:600` persiste tudo que passa. Exige canal de evento separado |
| **P-228** | SSE sem heartbeat | 🤖 | 45 s sem byte é candidato a corte por idle timeout de borda. 📊 Não achei configuração de proxy no repo — é risco não medido |
| **P-229** | 📊 `/r/[token]` está quebrada: `/r/` não está em `publicRoutes` do `middleware.ts` | 🤖 | uma linha + `npm run test:rotas-montam` + `next start`. Custa: o link público de artifact **nunca funcionou** |
| **P-230** | `gerar_relatorio` continua inútil mesmo com o `exige_async` | 🤖 | o modelo não preenche o payload e não pede `compartilhar`. Destrava: aplicar o padrão D1 (código monta) também nela — ou aposentá-la |
| **P-231** | O auxiliar `renovacao-maxima` continua `coming_soon` com `runtime.kind='none'`, embora o Radar já funcione | 🧑 Founder | decidir se o Radar vira a primeira rotina dele. 📊 Mais 6 auxiliares travados na mesma premissa que esta SPEC derrubou |
| **P-232** | Amandus e AutoFleet continuam sem marca | 🤖 | rodar o script do §E.3 para cada uma. Custa: peça de corretora paga saindo com paleta genérica |
| **P-233** | 📊 Não existe cliente HTTP com retry compartilhado no backend; o conector da InfoCap tem **zero** retry em 4.254 linhas | 🤖 | esta SPEC cria o seu, local. Consolidar depois — mas **não** editando o conector do Atendimento sem gate próprio |

---

# 19. Gates

| Bloco | Gate |
|---|---|
| **§2.3** | D-a, D-b e **D-c** registradas em `FOUNDER-DECISIONS.md` **antes** do Bloco A |
| **§2.4** | preflight de rede com a **quinta requisição** (a linha de controle SigV4) na saída |
| **A** | ranking 2025 = tabela §A.5; asserções 3 e 5 (controles) verdes; M1-M7 com os vermelhos previstos |
| **B** | custo 4,9% e 50,0% (± 0,3 p.p.); novo/renovação 2.301/971; parser não levanta em nenhuma entrada |
| **C** | `select origin, count(*) from artifacts` muda de `chat: 0` para `chat: ≥1`; a composição só usa blocos que existem em `BLOCOS` |
| **D** | 🔴 `payload.por_vendedor` com ≥ 2 vendedores **e** a asserção 4 (controle) reprovando a versão agregada |
| **E** | `marca_padrao = false` e `logo_no_html = true` no VERIFY §E.4 passo 3; UNDO testado |
| **F** | Raio-X de um ano em **< 5 s** com cache quente, medido e anotado; e a asserção 2 (controle, cache frio) verde |
| **G** | 🔴 `git diff` limpo nos ~30 congelados **e** a asserção 2 mostrando `services/comercial/` — sem ela o gate não vale |
| **H** | opcional. Se executado, **depois de 19/08** |
| **FINAL** | os 14 passos do §16, com saída real, **incluindo o 13 e o 14** |

**Gate de aplicação (CLAUDE.md §9.1).** Esta SPEC **não** mexe em `app/`,
`middleware.ts`, `instrumentation.ts`, `next.config.js` nem em variável de
ambiente do front. **Mesmo assim**, antes de declarar verde:

```bash
npm run test:rotas-montam       # a tabela de rotas monta
next start + GET /api/chat      # o servidor RESPONDE, não só compila
```

> **Por quê, se não mexi em `app/`?** Porque *"não mexi"* é uma afirmação, e a
> lição de 02/08/2026 é que **todos os gates paravam antes de ligar o
> servidor**. Rodar custa dois minutos; não rodar custou 1h40 de produto fora do
> ar. E o passo 4 do §G.3 é exatamente o teste dessa afirmação.

**Gate de infraestrutura (CLAUDE.md §8).** **Nenhuma migration.** As duas
escritas do Bloco E são DML, com VERIFY e UNDO escritos **antes** (§E.4, §E.5).
📊 `MIGRATIONS-AUTHORITY.md` não se aplica a DML, mas a disciplina de
APPLY/VERIFY/ROLLBACK, sim.

**Relatório final:** template canônico
(`docs/canon/reports/SPEC-EXECUTION-REPORT-TEMPLATE.md`), com commit inicial e
final, a saída real do preflight de rede (inclusive a linha de controle SigV4),
o número que a calibração do §A.6 produziu, canário Amandus → Resulta →
AutoFleet, e a declaração de que **nenhum motor paralelo foi criado**.

---

# 20. Ordem de execução

```text
§2.3  DECISÃO D-a / D-b / D-c        ← trava tudo
§2.4  PREFLIGHT DE REDE              ← se o login der 500, a SPEC para aqui

A  Camada de dados        ─┐  tudo depende dela. Sem A, B calcula ar.
B  Cálculos               ─┤  depende de A (dos dataclasses, não da rede)
                           │
E  A marca                 │  🔴 INDEPENDENTE. Pode ir em PARALELO com A e B,
                           │     e deve — é o bloco de menor risco e maior
                           │     efeito visual. Faça primeiro se a rede falhar.
                           │
C  Raio-X                 ─┤  depende de A, B, E
D  Radar                  ─┘  depende de A, B, E — e reusa 90% de C

F  Pré-aquecimento            depende de A
G  Não-regressão              🔴 roda DEPOIS de tudo, e é o último gate
H  Consertos avulsos          DEPOIS de 19/08. Nada depende dele.
```

**As duas dependências que não podem ser invertidas:**

1. **A antes de C e D.** Entregar a peça antes da camada de dados produziria um
   relatório bonito com números errados — que é o pior resultado possível,
   porque **parece pronto**.
2. **G por último, sempre.** Um teste de não-regressão rodado no meio da
   execução prova que o repositório estava limpo naquele momento, e nada sobre
   o estado final.

**Se o tempo apertar,** a ordem de corte é: **H** (já é opcional), depois **F**
(o relatório sai, só mais devagar), depois **a parte de projeção do B.8**.
🔴 **A, C, D, E e G não são cortáveis.** Sem E não há logo, e a logo foi pedida
por escrito. Sem G, a SPEC não tem direito de ir para produção na véspera.

---

# 21. FATO · INFERÊNCIA · RECOMENDAÇÃO

## FATO — medido em 18/08/2026

**No banco** (projeto `dcajcvlzcjbmyapmklil`):

- `artifacts`: `origin='routine'` = 40, `origin='chat'` = **0**.
- `brand_profiles`: 3 linhas, **todas** com `palette.primary = NULL` e
  `logo_asset_id = NULL`.
- 117 tabelas em `backend/supabase/migrations/`; **nenhuma** de apólice,
  carteira, comissão, renovação ou produtor.
- `token_usage_logs`, 30 dias: chat/`claude-sonnet-5` 4.394 chamadas a
  US$ 0,00285 médio; chat/`claude-opus-5` 46 a US$ 0,07439.

**No código** (commit `db2d9f1`):

- `report_tool.py:202` é um stub; a tool **não declara** `exige_async`; a única
  declaração no repositório é `human_handoff.py:294`.
- `report_tool._compor()` traduz **5** tipos de seção; `chart`, `waterfall`,
  `funnel`, `stacked`, `ring` e `split` são inalcançáveis pelo chat.
- `service.py:187-188`: o snapshot da marca vence o `visual_style` do template.
- `render.py:67-72` procura `data_uri` → `public_url` → `storage_ref`;
  `capture.py:562-566` só devolve `storage_ref`.
- `brand_assets.storage_ref` é `text NOT NULL` sem CHECK de formato.
- `graph.py:1596-1599` só deixa passar tokens do nó `agent`; `chat.py:600`
  acumula tudo em `full_response`, que é persistido.
- `llm_factory.py:155`: `"streaming": True`.
- Não há timeout de execução de tool em nenhuma camada do chat do dashboard.
- `infocap_connector.py`: **zero** retry em 4.254 linhas; `_TOOLS_SEMPRE_ASYNC`
  tem 4 nomes; o header é `Authorization: <token>` cru.
- `middleware.ts:92-103`: `/r/` **não** está em `publicRoutes`.
- `val_c` e `per_c` **não existem** em nenhum arquivo do repositório.
- `backend/tools/_resulta_logo.png` = 4.694 bytes; o data URI = 6.282 chars.

**Na InfoCap da Resulta:**

- Produção 2023-2026: a tabela do §A.5.
- 506 canceladas em 2025 inflam a comissão em R$ 90.671 (4,0%).
- `tipdoc` 2025: A=1.680, F=1.064, X=255, C=193, M=52, R=9, I=3.
- Média de 3 produtores por apólice (2025, n=3.536).
- Ranking `ordem=1` 2025: a tabela do §A.5; total R$ 3.094.963.
- Custo por canal: RAFAEL EXECUTIVO 4,9%; DVA BYD ITAJAI 50,0%.
- `val_cp` zerado em 100% das 16.693 linhas.
- Janela > ~6 anos → 502 aos 28 s. Ano a ano sempre funciona.
- 10 requisições paralelas em 4,5 s, com **1 HTTP 500** em 10.
- Join `renovacoes × documentos_bi` por `nosnum` casa 99% (4.858/4.877).
- `/comissao`, `/vendedores`, `/financeiro` **não existem** — o 403 é do API
  Gateway, com texto SigV4.

## INFERÊNCIA — raciocínio, não medição

- **`n = 3.536` é a população de `/renovacoes` com `fimvig` em 2025.** É a
  explicação mais simples para a diferença contra os 3.272 documentos de
  `inivig`, e é o que faz o total de R$ 3.094.963 conviver com os R$ 2.276.444.
  📊 **O passo 1 do §16 a confirma ou a derruba em uma chamada.** Se o número
  vier diferente, a inferência cai e o §A.6 tem de ser reescrito antes do
  Bloco B.
- **`nosnum_ren` preenchido ⇒ renovação.** Sustentada por quatro somas
  independentes que fecham exatamente (§A.5). É forte, mas continua inferência.
- **O 403 é rota inexistente, não permissão.** Sustentada pelo texto SigV4 e
  pelo fato de que a comissão vem no documento sem flag nenhuma. 📊 A quinta
  requisição do preflight (§2.4) a transforma em medição.
- **A instrução de "anunciar antes" vai fazer o modelo emitir texto antes do
  `tool_use`.** Sustentada por `streaming: True` e pelo comportamento conhecido
  do Claude. 💭 **Não foi medida neste produto.** O §16 passo 6 é o experimento;
  se falhar, o pré-aquecimento (§F.2 item 1) já reduz a espera para poucos
  segundos e o silêncio deixa de importar.
- 💭 O teto de 5 apólices para entrar no quadro de custo (§B.4) é hipótese sobre
  legibilidade, não medição.

## RECOMENDAÇÃO

1. **Executar §2.3 e §2.4 antes de tudo.** Um canônico vencido não se contorna;
   corrige-se. E um login que deu 500 há dezesseis dias se re-mede antes de se
   construir em cima dele.
2. **Fazer o Bloco E primeiro se houver qualquer dúvida sobre a rede.** É o de
   menor risco, maior efeito visual, e é o único que não depende da InfoCap.
3. **Não executar o Bloco H antes de 19/08.** Ligar o `gerar_relatorio` faz
   aparecer uma tool concorrente cujas pistas (`"venda"`, `"comiss"`) colidem
   com as frases do Founder.
4. **Rodar o §16 inteiro na noite de 18/08, com cronômetro**, e o
   pré-aquecimento **de novo** 20 minutos antes da apresentação.
5. **Se o ranking sobre produção não bater com R$ 3.094.963, não mexa no
   filtro.** Confira a calibração sobre a população de vencimento (§A.6). Forçar
   o número a bater trocando `inivig` por `fimvig` produz um relatório que soma
   certo e responde a pergunta errada.
6. **Depois da apresentação, P-224.** Sete auxiliares do catálogo estão parados
   esperando o espelho da carteira, e esta SPEC acaba de provar que a fonte
   sempre esteve aberta.
