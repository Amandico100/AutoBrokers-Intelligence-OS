# SPEC-083 — A RÉGUA DO CORREDOR

> **O que é uma rota pronta, como se prova sem opinião, e a ferramenta que dá a nota sozinha.**
>
> Autor: execução · **v2, 21/08/2026** · Commit base: `95b0d21`
> Branch: `feat/spec083-a-regua-do-corredor`
> Antecede e habilita: **SPEC-084 (A Fábrica de Rotas)**

---

## HISTÓRICO DE VERSÃO

**v1 → v2.** A v1 foi submetida a juiz crítico e **REPROVADA (54/100)**. Os defeitos e as correções estão no §12. Os cinco que mudaram a estrutura:

1. 🔴 O gate central era **impossível de satisfazer** — três regras da própria SPEC se contradiziam (teto matemático de 85 contra uma exigência de ≥95).
2. 🔴 A régua **não tira 98 com esta rubrica. Tira ~79** — e isso deixou de ser problema para virar a primeira entrega da SPEC-084.
3. 🔴 **75 dos 100 pontos ganhavam-se por declaração.** Agora todo ponto é cobrado contra o **corpus real**.
4. 🔴 A regra do eixo A mandava **inventar** rotas em 13 unidades cujo acervo está cheio — porque zurich e bradesco escrevem *"ordem de serviço"*, não *"protocolo"*.
5. 🔴 O VERIFY de PII **não conseguia falhar**.

---

## 0. PREFLIGHT OBRIGATÓRIO

```bash
git rev-parse --show-toplevel      # deve terminar em AutoBrokers-FIX
git branch --show-current          # feat/spec083-a-regua-do-corredor
git rev-parse HEAD                 # registrar no relatório final
git status --short                 # LIMPO ao iniciar
```

Leitura obrigatória antes da primeira linha de código:

1. `CLAUDE.md` — inteiro. Em especial **§5** (nunca criar motor paralelo), **§7** (multi-tenant), **§9.2** (medir vence deduzir; toda bateria precisa de CONTROLE), **§9.3** (teste que guarda verdade vencida; guarda que não pode falhar não guarda) e **§12.1** (📊 medido vs 💭 ilustrativo).
2. `docs/canon/GLOSSARIO.md` — conferir **termo a termo**: `corredor`, `subcorredor`, `rota`, `playbook`, `âncora`, `passo`, `subserviço`. Se esta SPEC divergir, **o glossário vence** e a SPEC é corrigida antes de executar. Registrar a conferência no relatório.
3. `docs/canon/PORTAIS-E-CORREDORES.md` — portal ≠ corredor ≠ Atlas.
4. `docs/canon/O-ATLAS-E-UM-SO-E-E-DE-TODAS.md` — **especialmente as linhas 73-95**, a tabela de identidade. Ela é a autoridade da higiene do corpus (§5.4).
5. `docs/canon/O-ATLAS-E-PARA-QUEM-ESCREVE-O-CORREDOR.md` — o uso offline do mapa.

### O escopo, e o que ele NÃO inclui

✅ **Esta SPEC pode alterar:** scripts novos, testes (inclusive consertar testes existentes), `CLAUDE.md`, documentos de canon.

❌ **Esta SPEC não altera nenhum corredor** — nem `ura_steps`, nem `subservices`, nem âncoras, nem `_SUBSERVICE_ALIASES`. Quem altera corredor é a SPEC-084.

> **Por que a separação:** medir a coisa e mudar a coisa no mesmo commit é como se perde a régua. Se a nota subir, ninguém sabe se foi a rota que melhorou ou a medida que afrouxou.

⚠️ **Consertar teste não é consertar corredor.** O `test_a_maquina_de_lavar_vai_ate_o_fim.py` tem 📊 **zero chamadas ao motor em 401 linhas** — consertá-lo é escopo **desta** SPEC (Bloco C), e sem isso o gate não fecha.

---

## 1. POR QUE ESTA SPEC EXISTE

### 1.1 O fato que a originou

📊 Em **19/08/2026 às 16:35 BRT** o Founder conduziu, ao vivo e com cliente real (Clarissa Medeiros da Luz, CPF `030***95`, apólice Allianz residencial `202623140079868`), um acionamento de assistência para **máquina de lavar**. A atendente Saionara coletou os dados em 10 minutos; o corredor conversou com a URA da Allianz e voltou com o **protocolo 52955490** em **5 minutos e 55 segundos**.

Work Run: `e5279497-a642-4703-a85f-d92a381e45ac`. Sessão no Atlas: `7ac3c101`.

📊 **Fonte de cada número desta seção** — a distinção importa, e a v1 a omitia:

| número | onde foi medido |
|---|---|
| 29 telas da URA | `observed_events`, sessão `7ac3c101`, `direction='in'` |
| 22 respostas nossas · 19 âncora · 3 cérebro | `work_events` do Work Run + o Espelho (`conversations`/`messages`) |
| 0 `needs_human` · 0 retentativas | `work_events` |

⚠️ `observed_events` **só guarda as entradas** (`direction='in'`) desta sessão. As saídas vivem no Espelho. Quem contar respostas no Atlas conta zero.

**Foi o primeiro e único corredor validado em produção do produto.** Virou a régua.

### 1.2 O problema: a régua tinha quatro furos, e nenhum era visível

📊 Auditoria de **21/08/2026** encontrou, dentro dessa mesma rota:

| # | furo | evidência medida |
|---|---|---|
| 1 | O passo `numero_residencia` exigia `informe o número da residência` | 📊 **ZERO ocorrências** em 28.094 eventos. A URA escreve `"Agora, me CONFIRME o número da residência"` — 180 mensagens, 72 sessões, a mais recente sendo a **própria sessão da régua**, 19/08 às 19:36:51 UTC (16:36 BRT) |
| 2 | O freio de finalização do residencial não tinha `dados a seguir estão corretos` | 📊 **156 mensagens / 65 sessões** passaram pela conferência **sem freio**. O `allianz-auto` tem essa âncora desde sempre |
| 3 | `schedule_agendado` era declarado e o motor **nunca o lia** | 📊 `extract_capture_anchors` lia 5 chaves e não essa. A cliente recebeu *"Prontinho! ✅ Sua assistência foi aberta"* — **sem data e sem período** |
| 4 | `\*dica:\*` exigia asterisco literal num texto que `_norm` já removeu | âncora morta desde 17/08, deixando `test_o_negrito_da_seguradora_nao_emudece_o_corredor` **vermelho em produção** |

**Nenhum dos quatro derrubou o atendimento.** Todos foram cobertos por cima — pelo cérebro adaptativo ou pela própria atendente. **Furo coberto é furo que ninguém vê.**

Os quatro foram consertados no commit `7af5c3c`, com o guarda `test_a_regua_nao_tem_furo.py` (25 asserções, 3 mutações provadas). **Esta SPEC existe porque eles não deveriam ter chegado à produção.**

### 1.3 🔴 A causa raiz: o teste guardava o regex, não o motor

O furo nº 3 é o mais instrutivo. A rota tinha **72 asserções verdes** (`test_a_maquina_de_lavar_vai_ate_o_fim.py`, 401 linhas) — e o agendamento nunca chegava ao cliente.

📊 **E é pior do que a v1 desta SPEC descreveu.** Medido:

```bash
grep -cE 'CP\.(match_ura_step|extract_capture_anchors|detect_finalize_anchor|missing_slots_for_subservice)' \
     backend/tests/test_a_maquina_de_lavar_vai_ate_o_fim.py
→ 0
```

**Zero chamadas ao motor em 401 linhas.** São dois desvios, não um:

- **linha 295**, `_captura(chave, texto)` — roda `re.search` direto sobre `capture_anchors`
- **linha 64**, `passo_de(...)` — **reimplementa `match_ura_step`** com `re.search(anchor, ...)`

A única menção a `match_ura_step` no arquivo está numa docstring. O teste provava que os regexes casavam. Não provava que alguém os usava.

> ## A REGRA QUE NASCE DESTA SPEC
>
> **Teste de corredor tem de chamar o MOTOR.**
> **Teste que chama o regex não guarda o corredor — guarda o regex.**
>
> Corolário do CLAUDE.md §9.3, e vai para o CLAUDE.md no Bloco E.

### 1.4 O tamanho do problema

⚠️ **Nota:** a v1 desta SPEC citava "média 46,3, mediana 49, segundo lugar 75" com marca 📊. **Aquilo era saída de uma rubrica que esta SPEC ainda vai construir** — número marcado como medido produzido por instrumento não publicado. Removido. A distribuição de notas é **saída** desta SPEC (Bloco D), não entrada.

📊 O que **está** medido, e reproduz:

```
_PLAYBOOKS ................ 14 corredores (10 auto + 4 residencial)
soma dos subservices ...... 62 unidades (seguradora × ramo × serviço)
observed_events ........... 28.094 eventos · 544 sessões · 17 pares corretora×seguradora
                            (16 com insurer_key + 1 evento com NULL)
período ................... 29/07/2025 → 21/08/2026
```

📊 E o replay — a única medida da v1 que **reproduziu na conferência do juiz**:

```
allianz-residencial / maquina_de_lavar   respondidas=20   ← reconstruído à mão, bateu
allianz-residencial / chaveiro           respondidas=11  órfãs=16   ← MESMO corredor
mapfre-auto  / guincho                   respondidas= 0  órfãs=29
tokio-auto   / guincho                   respondidas= 0  órfãs=29
```

### 1.5 🔴 O achado que muda o plano: o material existe

📊 Uma auditoria anterior classificou 25 unidades como "sem nenhuma sessão observada". **Estava errado**, e a causa é conhecida: `observed_sessions.ramo` e `.servico` são **NULL nas 573 linhas**, forçando classificação por texto.

O acervo real, por seguradora:

| seguradora | sessões | eventos | mais recente |
|---|---:|---:|---|
| allianz | 141 | 13.154 | 19/08/2026 |
| porto | 138 | 4.510 | 11/08/2026 |
| yelum | 100 | 4.604 | 19/08/2026 |
| tokio | 47 | 409 | 20/08/2026 |
| hdi | 44 | 2.974 | 29/07/2026 |
| bradesco | 22 | 477 | 23/07/2026 |
| azul | 19 | 829 | 28/07/2026 |
| zurich | 15 | 646 | **21/08/2026** |
| **mapfre** | **13** | **226** | **21/08/2026 10:04** |
| alfa | 9 | 264 | 15/07/2026 |

**A mapfre — a "sem sessões" — tem evento de hoje.**

> **Conclusão que orienta a SPEC-084: não é coletar. É minerar o que já temos e indexar por serviço.**

---

## 2. O QUE É UMA ROTA AAA

### 2.1 A definição, em uma frase

> **Uma rota AAA é aquela em que o agente vai do "oi" do segurado ao protocolo da seguradora sem nenhum humano tocar — e o segurado sabe o número do chamado, o dia e o período em que o técnico vem.**

Tudo o mais nesta SPEC é a tradução dessa frase em conferências que uma máquina consegue fazer.

### 2.2 Por que "AAA"

O Founder pediu o equivalente ao **triplo A** da indústria de jogos: um patamar que um juiz crítico cobra sem negociar.

| na indústria de jogos | aqui |
|---|---|
| não trava, não crasha | **o acionamento não emudece nem morre em silêncio** |
| não tem textura faltando | **nenhuma tela da URA fica órfã** |
| não tem bug de progressão | **toda tecla tem origem; nenhuma é chutada** |
| o jogador entende o que fazer | **o segurado sabe o protocolo, o dia e o período** |
| passa na certificação | **o teste chama o motor e a mutação fica vermelha DE VERDADE** |

**O juiz não aprova nada abaixo disso.** Não existe "quase pronto".

### 2.3 🔴 O PRINCÍPIO QUE GOVERNA A RUBRICA INTEIRA

> ## Ponto só se ganha contra o CORPUS. Declaração não vale ponto.

Na v1, 75 dos 100 pontos podiam ser obtidos escrevendo campos. O juiz achou a receita: chamar `_auto_playbook` para uma seguradora nova, escrever um teste com uma chamada ao motor e quatro comentários com a palavra CONTROLE — **49/100 sem responder uma única tela real**.

A causa é estrutural e está medida:

| campo | por que era grátis | 📊 |
|---|---|---|
| `_COMO_PERGUNTAR` | **nenhum** dos 29 slots do produto fica sem redação | item sem como falhar em nenhuma das 62 rotas |
| `finalize_anchors` | `_ALLIANZ_FAMILY_FINALIZE` / `_YELUM_FAMILY_FINALIZE` são copiados | 14/14 corredores têm ≥1 |
| `handoff_triggers` | `_AUTO_HANDOFF_TRIGGERS` copiado | 14/14 têm ≥1 |
| apelidos | `_SUBSERVICE_ALIASES` é **global e cego à seguradora** | `chaveiro`/`bateria`/`pneu` têm **0** apelidos, em todas |
| mutação | a rubrica **lia um comentário** dizendo que ficou vermelha | comentário não fica vermelho |

**Na v2, cada um desses itens passou a ser cobrado contra o corpus daquela seguradora.** Âncora herdada de família que nunca casou no acervo próprio vale **zero** — é a mesma classe de furo do `numero_residencia`.

### 2.4 As dez conferências, cada uma com o seu `DECIDE:`

A v1 abria dizendo "verificável por código, sem opinião" e quatro delas não eram. Agora cada uma traz a expressão exata que a decide.

| # | conferência | `DECIDE:` |
|---|---|---|
| 1 | A rota foi percorrida até o **fim**, e há registro | ≥1 sessão do corpus em que `extract_capture_anchors(pb, tela)` devolve `protocol`, **ou** `detect_finalize_anchor` casou e a sessão seguiu ≥1 tela depois |
| 2 | A sessão está **transcrita** | o bloco do subserviço contém `📊 sessão <8 hex>` e esse prefixo existe em `observed_events` |
| 3 | **Zero órfãs funcionais** | toda tela do corpus para a qual `_tela_pede_alguma_coisa(pb, tela)` é `True` casa um `ura_step` via `match_ura_step(pb, tela, subservice=rota)` |
| 4 | ≥85% determinístico | `respondidas ÷ (telas que pedem algo)` |
| 5 | Toda tecla `_opcao` tem origem | o nome está em **uma das TRÊS** fontes: o dict do subserviço · `_derivar_teclas_do_caso` · as derivações inline de `new_dispatch_session` |
| 6 | Os apelidos são do jeito que o cliente fala **daquela seguradora** | ≥3 apelidos resolvem por `canonical_subservice` **e** cada um aparece ≥1 vez no corpus daquela seguradora |
| 7 | O freio **casa tela real** | `detect_finalize_anchor(pb, tela)` casa ≥1 tela do corpus daquela seguradora+ramo |
| 8 | O handoff **casa tela real** | idem, com `detect_handoff_trigger` |
| 9 | Teste chama **o motor**, e a mutação **fica vermelha** | ver §3.6 — a mutação é **executada**, não lida |
| 10 | O cliente recebe protocolo + dia + período | `client_summary_from_capture` sobre a captura real da sessão contém os três |

### 2.5 🔴 O que NÃO entra na régua

**O teste ao vivo não vale ponto. Vira selo.**

Razão, com o caso concreto: 📊 antes de 19/08 a máquina de lavar já tinha os 9 passos, as 3 teclas, os 11 apelidos, as 5 regras. Uma rubrica que descontasse "não testado" lhe daria nota baixa **exatamente quando ela estava boa**. A nota teria mentido.

O teste ao vivo prova outra coisa: que **a URA de hoje** ainda é a que mapeamos. É informação de **validade**, não de qualidade.

**Também não entram:** número de linhas, de passos, de slots. 📊 Contraexemplo: `mapfre-auto` tem **8 `required_slots`** e **4 `ura_steps`**. Coleta oito dados e tem quatro telas onde usá-los. **Slot sem passo é dado que não vira tecla.**

---

## 3. A RUBRICA — 100 pontos, com o comportamento dominando

### 3.1 Os cinco eixos

```
A · EVIDÊNCIA   a rota foi percorrida até o fim?           20
B · COBERTURA   as telas viraram passos?                   35   ← o peso está aqui
C · SEGURANÇA   o freio casa tela REAL?                    20
D · CONHECIMENTO medido contra o acervo                    10
E · PROVA       mutação executada, não comentada           15
                                                        ─────
                                              PRONTIDÃO  100
```

**B vale 35 porque é a única medida que reproduz.** O juiz reconstruiu o replay da régua à mão e chegou às mesmas 20 respondidas da auditoria. É a medida que separa a régua (20 respondidas) de `mapfre-auto` (0 de 29).

### 3.2 Eixo A — Evidência (20)

*A rota foi percorrida até o fim, e nós temos o registro?*

| item | pts | `DECIDE:` |
|---|---:|---|
| a sessão chegou ao **fim** | **12** | §2.4/#1 — pelo **motor**, nunca por regex do script |
| está **transcrita** no bloco | **4** | §2.4/#2 |
| ≥2 sessões distintas da rota | **2** | contagem |
| a mais recente tem <180 dias | **2** | `max(wa_timestamp)` |

#### 🔴 A correção mais importante do eixo A

A v1 dizia: *"eixo A = 0 → a rota não pode receber nota nenhuma"*, e mandava usar a âncora de protocolo. 📊 Medido pelo juiz, isso mandaria **13 rotas** para a lista de coleta com o acervo cheio:

| seguradora | sessões | casam a âncora | dizem "protocolo" | rotas afetadas |
|---|---:|---:|---:|---:|
| **mapfre** | 13 | **0** | 2 | 4 |
| **bradesco** | 22 | 3 | **0** | 4 |
| **zurich** | 15 | 4 | **0** | 5 |

📊 Zurich e Bradesco **nunca escrevem "protocolo"** — escrevem **"ordem de serviço"** (zurich 25 ocorrências, bradesco 10).

**A regra que a v1 escreveu mandaria inventar exatamente onde a SPEC diz que inventar é o pior desfecho possível.**

#### O estado novo: `ANCORA_SUSPEITA`

**Antes de rodar a rubrica**, o Bloco A entrega a **conferência da âncora de desfecho, por seguradora**:

```sql
select insurer_key,
       count(distinct session_id) as sessoes,
       count(distinct session_id) filter (where text ~* '<ANCORA_DE_PROTOCOLO>') as casam
from observed_events group by 1;
```

| resultado | estado | ação |
|---|---|---|
| ≥1 sessão casa | normal | rubrica roda |
| **0 casam** e a seguradora tem **≥10 sessões** | 🟠 **`ANCORA_SUSPEITA`** | é **defeito da âncora**, não ausência de fonte. Vai para a SPEC-084 como "ampliar a âncora de desfecho", não para a lista de coleta |
| 0 casam e <10 sessões | 🔴 `SEM_FONTE` | vai para coleta |

> **Confundir "a seguradora escreve diferente" com "nunca vimos esta rota" manda a SPEC-084 coletar o que já está coletado.**

⚠️ **E o vazamento no outro sentido:** 📊 `_ANCORA_DE_PROTOCOLO` tem o ramo `o\.?s\.?`, que casa o **artigo "os"** seguido de 6-20 dígitos. Em yelum, **31 das 38** sessões "com protocolo" casam **só** pelos ramos largos. O eixo A daria 12 pontos a rotas que talvez nunca tenham terminado. Por isso o `DECIDE:` de #1 exige o **motor** (`extract_capture_anchors`, que devolve o grupo capturado) e não a presença do padrão.

### 3.3 Eixo B — Cobertura (35)

*As telas que a URA mostra viraram passos?*

O replay: cada tela do corpus roda por `match_ura_step(pb, tela, subservice=rota)` e cai em uma classe:

```
RESPONDIDA      casou um passo que devolve resposta          ✅
NOOP            casou um passo `noop`                        ✅
ÓRFÃ INÓCUA     não casou, e `_tela_pede_alguma_coisa` = False   ⚪ tolerável
ÓRFÃ FUNCIONAL  não casou, e `_tela_pede_alguma_coisa` = True    🔴 é o defeito
```

| item | pts |
|---|---:|
| **zero órfãs funcionais** | **20** |
| 1 órfã funcional | 10 |
| 2 órfãs funcionais | 4 |
| ≥3 | 0 |
| ≥85% determinístico | **8** (4 se 70–85%) |
| `notes` com contagem **daquela seguradora** — **pro-rata** | **7** × (passos respondidos com contagem própria ÷ passos respondidos) |

#### 🔴 O `notes` não pode premiar medição emprestada

📊 Medido: das 24 `notes` com contagem no produto inteiro, **16 estão no `yelum-residencial`** — e foram copiadas dali para a família. 📊 `_YELUM_FAMILY_STEPS` (35 passos) alimenta `hdi-auto` e `yelum-auto`; `_ALLIANZ_FAMILY_AUTO_STEPS` (23) alimenta `allianz-auto` e `alfa-auto`. **58 assinaturas de passo aparecem em mais de um playbook.**

Um passo da HDI ganharia pontos exibindo uma contagem **medida no acervo da Yelum**.

`DECIDE:` a `notes` traz a seguradora explícita — `📊 hdi: 12 ocorrências`. Contagem sem seguradora, em passo que veio de família, vale **zero**.

#### O discriminador é o do produto, nunca um novo

`_tela_pede_alguma_coisa(playbook, texto) -> bool` existe em `insurer_dispatch_service.py:1974` e 📊 tem exatamente a assinatura que esta SPEC assume: lê os `finalize_anchors` do próprio corredor via `pergunta_de_decisao` e cai na lista genérica `_MARCA_DE_PERGUNTA`. **Reusar. Um segundo discriminador divergiria em silêncio** (CLAUDE.md §5).

### 3.4 Eixo C — Segurança (20)

*Quando errar dói, o corredor para?*

| item | pts | `DECIDE:` |
|---|---:|---|
| o freio **casa ≥1 tela real do corpus** | **8** | `detect_finalize_anchor(pb, tela)` sobre o corpus daquela seguradora+ramo |
| toda tecla `_opcao` tem origem nas **três** fontes | **6** | §2.4/#5 |
| o handoff **casa ≥1 tela real do corpus** | **3** | `detect_handoff_trigger` |
| nenhuma âncora da rota exige `*` literal | **3** | `re.search(r"\\\*(?!\?)", anchor)` sobre cada `anchor` |

#### 🔴 As teclas têm TRÊS origens, não duas

📊 A v1 mandava varrer `subservices` + `_derivar_teclas_do_caso`. Com isso, **a própria régua reprovaria**: `telefone_adicionar_opcao` é exigido pelo passo `confirmar_telefone` (`corridor_playbooks.py:225`), **não está** no subserviço `maquina_de_lavar` e **não está** em `_derivar_teclas_do_caso`. Ele nasce **inline** em `new_dispatch_session` (`insurer_dispatch_service.py:489-490`).

As três fontes:
1. a chave `<x>_opcao` no dict do subserviço
2. `_derivar_teclas_do_caso` (`insurer_dispatch_service.py:391`)
3. as derivações **inline** de `new_dispatch_session` — hoje: `telefone_adicionar_opcao`

> Uma quarta origem que apareça e não esteja nesta lista é **defeito desta lista**, não da rota. A ferramenta reporta `ORIGEM_DESCONHECIDA` com o nome da tecla, e o executor decide.

#### Por que o freio vale 8

📊 É a última porta antes de mandar um prestador a um endereço. A ausência dele no residencial deixou **65 sessões** passarem pela conferência sem verificação nenhuma.

#### Por que a tecla vale 6

📊 Tecla errada **não trava** — abre o chamado errado. `14` é máquina de lavar; `10` é lava-louças; `13` é secadora. O erro só aparece quando o técnico chega.

### 3.5 Eixo D — Conhecimento (10)

*A atendente sabe o que perguntar e avisar — e isso veio do acervo?*

| item | pts | `DECIDE:` |
|---|---:|---|
| apelidos que **aparecem no corpus daquela seguradora** | **4** | ≥3 apelidos resolvem por `canonical_subservice` **e** cada um casa ≥1 tela ou resposta do corpus. Apelido só global: máximo **1** ponto |
| `expectativa_do_desfecho` existe para a rota | **3** | chave presente e não-vazia |
| `regras_para_o_cliente` **com trecho que casa o corpus** | **3** | lista não-vazia **e** o comentário nas 20 linhas acima da chave contém `📊` seguido de trecho de ≥40 caracteres que `_norm`-casa alguma tela do corpus daquela seguradora+ramo |

#### 🔴 `_COMO_PERGUNTAR` saiu da rubrica

📊 Dos 29 slots distintos do produto, **zero** ficam sem redação. Era um item que **não tinha como falhar** em nenhuma das 62 rotas — 5 pontos de graça. Continua sendo obrigação (a SPEC-084 cobra ao criar slot novo), mas não pontua.

#### ⚠️ A assimetria arquitetural que a rubrica precisa declarar

📊 Os 10 corredores de auto vêm da fábrica `_auto_playbook`; os 4 residenciais são dicts literais. **Não há fábrica que propague `regras_para_o_cliente` e `expectativa_do_desfecho`** — e por isso eles existem em **1 de 14** playbooks.

Sem declarar isso, 13 corredores perdem 6 dos 10 pontos do eixo D por uma razão **arquitetural**, não de qualidade — e a SPEC-084 "consertaria" copiando campos para calar a régua.

> **Decisão registrada:** a ferramenta marca essas rotas com `SEM_FABRICA` no relatório. A SPEC-084 decide se cria a fábrica ou preenche uma a uma — **e a decisão é dela, não desta**.

### 3.6 Eixo E — Prova (15)

*Se alguém quebrar isto amanhã, algo fica vermelho — de verdade?*

| item | pts | `DECIDE:` |
|---|---:|---|
| existe teste que nomeia a rota **e chama o motor** | **6** | ver a regra por-arquivo abaixo |
| ≥1 linha de **CONTROLE** explícita | **3** | rótulo de asserção contendo `CONTROLE` |
| a mutação **fica vermelha quando executada** | **6** | `medir_rota --verificar-mutacoes` aplica, roda, exige vermelho, restaura |

#### 🔴 A regra por-arquivo (a v1 zerava a régua e travava o próprio gate)

```
O eixo E é avaliado POR ARQUIVO, e a nota da rota é a do MELHOR arquivo
que a nomeia.

Um arquivo é DESQUALIFICADO (contribui 0) quando aplica `.search(` /
`.match(` / `.fullmatch(` — por qualquer alias de `re` — sobre um valor
lido de `playbook["capture_anchors"]`, `["finalize_anchors"]`,
`["handoff_triggers"]` ou `step["anchor"]`, e NÃO chama nenhuma função do
motor no mesmo `def`.

NÃO é desqualificação: regex sobre a âncora COMO TEXTO, para conferir a
FORMA da declaração — por exemplo `_re.search(r"\\\*(?!\?)", anchor)`, a
conferência de asterisco literal de `test_a_regua_nao_tem_furo.py:193`.
O alvo é a captura que SUBSTITUI o motor, não a inspeção da declaração.
```

#### 🔴 A mutação é executada, nunca lida

A v1 dava 3 pontos por um **comentário** dizendo que a mutação ficou vermelha. Comentário não fica vermelho.

O teste declara, no topo:

```python
MUTACOES = [
    # (arquivo, texto_de, texto_para, rotulo_da_assercao_que_deve_cair)
    ("app/services/corridor_playbooks.py",
     '"anchor": r"(?:informe|confirme) o n',
     '"anchor": r"informe o n',
     "me CONFIRME o número da residência casa o passo"),
]
```

E `medir_rota --verificar-mutacoes`:
1. **copia o arquivo** para `/tmp` (⚠️ **nunca `git checkout`** — ele apaga trabalho não commitado; e `git diff --quiet` **não vê arquivo untracked**, então não prova restauração)
2. aplica a substituição
3. roda o teste — **exige** a asserção nomeada em vermelho
4. restaura da cópia e **confere por hash** que o arquivo voltou idêntico

Mutação declarada que **não** produz vermelho = **0 pontos e linha no relatório**. É a diferença entre um guarda e um enfeite.

### 3.7 O selo e o estado da fonte

Fora dos 100 pontos:

```
SELO DE CAMPO      🟢 TESTADO AO VIVO em <data>, protocolo <n>
                   ⚪ NÃO TESTADO
                   🔴 TESTADO E FALHOU em <data>, motivo <x>

ESTADO DA FONTE    🟢 COMPLETA          sessão(ões) chegaram ao fim
                   🟡 PARCIAL           sessão existe, não chegou ao fim
                   🟠 ANCORA_SUSPEITA   ≥10 sessões e a âncora casa 0
                   🔴 SEM_FONTE         <10 sessões e nenhuma chega ao fim
```

**A leitura de uma linha passa a ser:**

> `allianz × residencial × maquina_de_lavar` — **79/100** · 🟢 testado 19/08 · 🟢 fonte completa
> *falta: transcrição (4) · 1 órfã funcional (10) · notes pro-rata (5)*

### 3.8 Os patamares

```
 95-100   AAA          pronto. O juiz aprova.
 80-94    quase        falta algo NOMEÁVEL. Vai à fila com o item.
 55-79    parcial      o caminho existe e não fecha sozinho.
 25-54    esqueleto    há passos, não há rota.
  1-24    toco         o corredor não responde a esta URA.
    —     ANCORA_SUSPEITA / SEM_FONTE — estados, não notas
```

---

## 4. 🔴 QUANTO A RÉGUA TIRA — e por que isso é a melhor notícia da SPEC

### 4.1 O cálculo

A v1 afirmava que a régua tiraria 98 e transformava isso em gate. O juiz calculou eixo por eixo, lendo o código, e chegou a **63** com a rubrica v1.

Com a rubrica **v2**, 💭 a estimativa é **~79**:

| eixo | pts | o que falta |
|---|---:|---|
| A | 16/20 | 🔴 **não há transcrição** da sessão no bloco (−4) |
| B | ~18/35 | 🔴 **1 órfã funcional** (−10) · `notes` pro-rata 7/26 (−5) |
| C | 20/20 | ✅ |
| D | 10/10 | ✅ |
| E | 15/15 | ✅ **depois** do conserto do teste, que é escopo desta SPEC |
| | **~79** | |

💭 O número é estimativa até o Bloco C rodar. **O valor medido substitui este parágrafo no relatório final.**

### 4.2 🔴 A órfã funcional da régua

📊 Tela 18 de 29 da sessão validada, 19/08/2026 às 19:39:07 UTC:

```
"Agendamento para: *Quinta-feira 20/08/2026*, *período da tarde das 13:00 às 18:00*
 Podemos continuar ? *1 -* Sim *2 -* Não, quero remarcar"
```

📊 Nenhum `ura_step` casa: `confirmar_atendimento` exige `podemos confirmar o atendimento`; `escolher_periodo_agendamento` exige `agendamento é por período|horários de agendamento`.

📊 E `_tela_pede_alguma_coisa` devolve **True** por dois caminhos independentes: `(?:podemos)…(?:continuar)` e `\bagendamento\b`.

**É órfã funcional pela regra da própria SPEC, no acionamento que virou a régua.**

Ela caiu no cérebro, que respondeu certo. Funcionou — e é exatamente o tipo de furo coberto que esta SPEC existe para tornar visível.

### 4.3 O gate, corrigido

A v1 exigia ≥95 e era impossível. O gate v2:

```
BLOCO C · GATE
  a régua tira ≥75 com a rubrica v2                      ← hoje
  e a lista do que falta nela tem exatamente 3 itens      ← nomeáveis
  e esses 3 itens são as três PRIMEIRAS entregas da 084

Depois que a 084 fechar os três:
  a régua tira ≥95, e ESSE vira o gate permanente
```

> **Por que isto é a melhor notícia da SPEC:** a régua tinha três buracos que ninguém via, e a rubrica os achou **antes** de 61 rotas serem construídas contra eles. O gate da v1 — *"se a régua não tirar 98, a rubrica está errada"* — funcionou: aplicado, ele reprovou a si mesmo. É o que um gate deve fazer.

⚠️ **E a inversão que fica escrita:** se, depois da 084, a régua ainda não tirar ≥95, a pergunta volta a ser **qual dos dois está errado** — a rota ou a medida. Nunca se maquia a rota para calar a régua.

---

## 5. A FERRAMENTA — `medir_rota.py`

### 5.1 O que é

`backend/scripts/medir_rota.py` — recebe uma rota e devolve a nota, eixo por eixo, com a evidência de cada ponto. **Determinístico, sem LLM.**

```bash
python backend/scripts/medir_rota.py --seguradora allianz --ramo residencial --servico maquina_de_lavar
python backend/scripts/medir_rota.py --todas --formato tabela
python backend/scripts/medir_rota.py --todas --formato markdown > docs/canon/reports/INVENTARIO-DE-ROTAS.md
python backend/scripts/medir_rota.py --seguradora allianz --ramo residencial --servico maquina_de_lavar --replay-detalhado
python backend/scripts/medir_rota.py --verificar-mutacoes
python backend/scripts/medir_rota.py --conferir-ancoras-de-desfecho
```

### 5.2 A saída (💭 formato ilustrativo — os números não são medição)

```
allianz × residencial × maquina_de_lavar
─────────────────────────────────────────────────────────────────
PRONTIDÃO  79/100      🟢 testado 19/08/2026 (protocolo 52955490)
FONTE      🟢 COMPLETA  3 sessões · mais recente 19/08/2026

A EVIDÊNCIA          16/20
  ✅ 12  chegou ao fim: extract_capture_anchors devolveu protocol em 7ac3c101
  ❌  0  transcrição AUSENTE — nenhum `📊 sessão <hex>` no bloco     ← falta 4
  ✅  2  3 sessões distintas
  ✅  2  mais recente há 2 dias

B COBERTURA          18/35
  ⚠️ 10  1 órfã funcional: "Agendamento para: … Podemos continuar ?"  ← falta 10
  ✅  8  95% determinístico (19 de 20 telas que pedem algo)
  ⚠️  2  notes com contagem própria: 7 de 26 passos                   ← falta 5

C SEGURANÇA          20/20
D CONHECIMENTO       10/10
E PROVA              15/15
  ✅  6  test_a_regua_nao_tem_furo.py chama match_ura_step,
         extract_capture_anchors e detect_finalize_anchor
         ⚠️ test_a_maquina_de_lavar_vai_ate_o_fim.py DESQUALIFICADO
            (0 chamadas ao motor; `passo_de:64` e `_captura:295`)
  ✅  3  17 rótulos com CONTROLE
  ✅  6  3 mutações EXECUTADAS: 1, 2 e 6 asserções vermelhas

O QUE FALTA PARA 95  (as três primeiras entregas da SPEC-084)
  1. transcrever a sessão 7ac3c101 no bloco do subserviço        (+4)
  2. mapear "Agendamento para: … Podemos continuar ?"            (+10)
  3. pôr contagem própria no `notes` de 19 passos                (+5)
```

### 5.3 A saída com `--todas`

```
SEGURADORA  RAMO         SERVIÇO           PRONT  A  B  C  D  E  SELO FONTE  FAMÍLIA        DEMANDA
allianz     residencial  maquina_de_lavar    79 16 18 20 10 15   🟢   🟢     —                  105
...
mapfre      auto         bateria              —  —  —  —  —  —   ⚪   🟠     _auto_playbook     113
```

- **FAMÍLIA** — se os `ura_steps` vêm de uma família compartilhada. 📊 Mexer num passo de `_YELUM_FAMILY_STEPS` muda `hdi-auto` **e** `yelum-auto`; `native_flows` é o **mesmo objeto** (compartilhado por referência).
- **DEMANDA** — sessões do corpus em que o serviço aparece, por `PADROES_DE_SERVICO` (§5.5). É o que ordena a SPEC-084.

### 5.4 O que a ferramenta DEVE reusar, e nunca reescrever

CLAUDE.md §5. 📊 Todas conferidas como existentes com estes nomes:

| precisa de | usar | onde |
|---|---|---|
| casar tela com passo | `match_ura_step` | `corridor_playbooks.py` |
| capturar protocolo/senha/agendamento | `extract_capture_anchors` | idem |
| tela de finalização? | `detect_finalize_anchor` | idem |
| gatilho de handoff? | `detect_handoff_trigger` | idem |
| apelido → rota | `canonical_subservice` | idem |
| o que falta na ficha | `missing_slots_for_subservice` | idem |
| normalizar texto | `_norm` | idem |
| **a tela pede algo?** | `_tela_pede_alguma_coisa(playbook, texto) -> bool` | `insurer_dispatch_service.py:1974` |
| mensagem ao cliente | `client_summary_from_capture` | idem |

🔴 **Reimplementar qualquer uma faz a ferramenta medir uma coisa e o produto fazer outra** — o mesmo defeito do helper `_captura`, um nível acima.

⚠️ **O import difícil, e a SPEC precisa dizer qual é.** `insurer_dispatch_service` faz `from app.services.corridor_playbooks import (...)` — import de pacote real. O truque de `types.ModuleType` cobre `app`/`app.services`/`app.core`, e **este** módulo é o que exige atenção. O padrão que funciona, verificado:

```python
import sys, types, os, importlib
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for pkg in ("app", "app.services", "app.core"):
    if pkg not in sys.modules:
        m = types.ModuleType(pkg)
        m.__path__ = [os.path.join(RAIZ, *pkg.split("."))]
        sys.modules[pkg] = m
CP  = importlib.import_module("app.services.corridor_playbooks")
IDS = importlib.import_module("app.services.insurer_dispatch_service")
```

### 5.5 `PADROES_DE_SERVICO` — publicado como código

🔴 A v1 deixou `<PADRAO_DO_SERVICO>` como placeholder e mesmo assim publicou uma tabela de demanda. O juiz tentou reproduzir e **não conseguiu**:

📊 `eletricista` em allianz: SPEC dizia 94. Com `~ 'eletricist'` dá **66**; só com `~ 'el.tric'` dá 95 — e esse padrão **contamina AUTO**, porque casa *"parte elétrica"*. Em porto salta de 4 para 24 pelo mesmo motivo.

**Entrega:** `backend/scripts/padroes_de_servico.py`, com um padrão **por serviço E por ramo**:

```python
PADROES_DE_SERVICO = {
    ("residencial", "eletricista"): r"eletricista|reparo el[ée]trico|tomada queimada",
    ("auto",        "guincho"):     r"guincho|reboque|rebocar",
    # eletricista RESIDENCIAL não é "parte elétrica" de AUTO
}
```

E a tabela da §10.2 é **regerada por ele**, com a data e o commit no cabeçalho.

### 5.6 Modo offline

Sem `SUPABASE_URL`/`SUPABASE_SERVICE_ROLE_KEY`: mede **C, D e E** (que só dependem do código) e devolve `A: sem banco`, `B: sem corpus`.

⚠️ Correção à v1: **B não é offline**. Ele depende do corpus, que o Bloco A gera. Rodar B exige o corpus commitado.

---

## 6. O CORPUS DE TELAS REAIS

### 6.1 Onde mora

```
backend/tests/corpus/telas_reais/<seguradora>-<ramo>.jsonl
backend/tests/corpus/telas_reais/<seguradora>-indefinido.jsonl
backend/tests/corpus/telas_reais/INDICE.md
```

Cada linha:
```json
{"session_id":"7ac3c101","wa_timestamp":"2026-08-19T19:39:07Z","company_id":"04b5cdbc","text":"..."}
```

### 6.2 🔴 A decisão multi-tenant, declarada

📊 A mesma seguradora tem acervos de **duas corretoras**:

| | Resulta | AutoFleet |
|---|---:|---:|
| allianz | 10.608 ev · 93 sessões | 2.546 ev · 47 sessões |
| porto | 2.004 · 38 | 2.506 · 99 |
| yelum | 1.056 · 18 | 3.548 · 82 |

**Decisão:** o corpus é **global por seguradora+ramo**, sob a decisão já registrada em `O-ATLAS-E-UM-SO-E-E-DE-TODAS.md`: *a URA é a mesma para todas as corretoras*. Cada linha guarda `company_id` **como metadado**, para auditar proveniência; o replay o ignora.

⚠️ **Se duas corretoras mostrarem a mesma tela com textos diferentes no mesmo período**, isso significa que a seguradora as trata diferente — e é achado, não ruído. A ferramenta reporta `DIVERGENCIA_ENTRE_CORRETORAS` com as duas versões, e **a SPEC-084 para e pergunta ao Founder**. Não escolhe sozinha.

### 6.3 Só `direction = 'in'`

🔴 A v1 mostrava `"direction":"in"` no formato e **não mandava filtrar**. 📊 As mensagens `out` são as **da corretora** — `b2bf40e7` tem 148, `8ad1d251` tem 140. **Versionar `out` em git é versionar a identidade da atendente.**

### 6.4 🔴 Higiene: MASCARAR, não recusar

📊 Das 29 telas da sessão validada, **quatro** trazem telefone em claro:

```
#10  "Registramos o telefone *+55 (47) 99627-4743* … Deseja adicionar outro número?"
#11  "Por favor, informe *o número de celular completo* com DDD"
#12  "Obrigada! Anotei seu número *(48) 99909-5995*. Está correto?"
#27  "Sua senha será os 4 últimos dígitos desse telefone *4743*"
```

*(O endereço já vem mascarado pelo Atlas: `R. ### ##TEVES J#####`. O telefone, não.)*

🔴 A v1 mandava **recusar** a linha. Recusar apagaria a tela **#27** — a única que carrega `capture_anchors["password"]` — e as **#10** e **#12**, que são os passos `confirmar_telefone` e `confirmar_telefone_anotado`. **O replay perderia 3 passos da régua e ninguém veria**, porque a recusa vira só um número.

**A regra:**

```
telefone  → +55 (##) #####-####
            EXCEÇÃO: preservar os 4 últimos se eles reaparecerem como senha
            (📊 tela #27 de 7ac3c101) — senão a âncora de senha perde o alvo
CPF/CNPJ  → ###.###.###-##
nome      → {NOME}
corretora → {CORRETORA}
```

A tabela de identidade é a de `O-ATLAS-E-UM-SO-E-E-DE-TODAS.md` (linhas 73-95) — ela cobre **nome de atendente e razão social da corretora**, que a v1 não cobria e são o que aquele documento identifica como o vazamento real.

**RECUSAR** só a linha que sobrar com dígito não reconhecido depois da máscara — e a recusa vai para `INDICE.md` com `session_id` e motivo.

### 6.5 Teto e retenção

🔴 A v1 não dimensionou. 📊 Medido:

```
b2bf40e7   350 eventos · 202 `in` ·  63 textos distintos
8ad1d251   336 eventos · 196 `in` ·  67 textos distintos
```

*(⚠️ A v1 afirmava que `b2bf40e7` tinha "50 únicos". 📊 Tem **95** textos distintos.)*

**As regras:**
- dedup por `(session_id, _norm(text))` — **o timestamp não entra**. 📊 Metade dos eventos de `9cb09e20` é repetição do mesmo texto
- no máximo **5 sessões** por (seguradora, ramo): a mais recente **com desfecho** + as 4 mais distintas por conjunto de telas
- teto de **500 KB por arquivo**, verificado no gate
- sessão que sai do corpus fica registrada em `INDICE.md` com `session_id` e motivo — **some do arquivo, não do registro**

### 6.6 Por que versionado, e não consultado no teste

1. o teste roda **sem banco** — em CI e na máquina de quem escreve corredor
2. o corpus é **prova datada**: se a URA mudar, ele continua sendo o que justificou aquele passo
3. o gate não depende de rede

---

## 7. O GATE DE REPLAY

`backend/tests/test_o_replay_nao_deixa_orfa.py`

- Rota com **fonte completa** e órfã funcional → **vermelho**
- Rota `PARCIAL` / `ANCORA_SUSPEITA` / `SEM_FONTE` → **pulada, com linha no relatório** dizendo qual e por quê
- 🔴 **Nunca pula em silêncio.** Truncar calado lê-se como "cobrimos tudo"

⚠️ **Exceção temporária, registrada:** enquanto a órfã funcional da régua (§4.2) não for fechada pela SPEC-084, ela consta numa lista `ORFAS_CONHECIDAS` no topo do teste, **com o motivo, a data e a SPEC que a fecha**. Lista que ganhar uma entrada sem esses três campos torna o gate inútil.

---

## 8. OS BLOCOS DE EXECUÇÃO

### BLOCO A — O corpus

**Entrega:** `backend/scripts/gerar_corpus_de_telas.py`, `backend/scripts/padroes_de_servico.py`, os `.jsonl`, o `INDICE.md`.

**Passo 0 — 🔴 INFERIR O RAMO, e registrar como.**
📊 `observed_events` não tem coluna `ramo`; `observed_sessions.ramo` é NULL nas **573** linhas. A v1 mandava ler "por ramo inferido" sem dizer como.

```
residencial  a sessão contém "Residência, Condomínio ou Empresa"
             ou "Qual seguro deseja utilizar" seguido de "Residencial"
auto         a sessão contém "Automóvel, Moto ou Caminhão", ou pede placa
ambíguo      nenhuma das duas → <seguradora>-indefinido.jsonl,
             NÃO alimenta replay de rota nenhuma, com linha no relatório
```

📊 **CONTROLE obrigatório:** a sessão `7ac3c101` tem de sair `residencial`, e uma sessão de guincho da Yelum tem de sair `auto`. **As duas no mesmo balde = a inferência não está inferindo.**

**Passo 1** — ler `observed_events` filtrando `direction='in'` (§6.3).
**Passo 2** — dedup por `(session_id, _norm(text))` (§6.5).
**Passo 3** — mascarar (§6.4). Recusar só o que sobrar; registrar em `INDICE.md`.
**Passo 4** — aplicar o teto de 5 sessões e 500 KB.
**Passo 5** — gravar ordenado por `wa_timestamp`.

**VERIFY — e ele consegue falhar:**
```bash
python backend/scripts/gerar_corpus_de_telas.py --todas --dry-run
python backend/scripts/gerar_corpus_de_telas.py --auditar-pii
# telefone BR com separadores: \+?55[\s(]*\d{2}[\s)-]*9?\d{4}[\s-]*\d{4}
# CPF com pontuação:           \d{3}[.\s]\d{3}[.\s]\d{3}[-\s]\d{2}
```

🔴 **A v1 usava `grep -cE '[0-9]{11}'`.** Ele **não casa** `+55 (47) 99627-4743` — a maior sequência de dígitos ali tem **cinco**. Devolvia 0 com quatro telefones no arquivo. *"Um guarda que não tem como falhar não guarda nada"* (CLAUDE.md §9.3).

**Guarda:** `test_o_corpus_nao_vaza_pii.py` — com **linha de controle**: injeta uma linha com telefone real (tem de acusar) e a mesma mascarada (tem de passar). **As duas passando, ou as duas falhando, o guarda não guarda.**

---

### BLOCO B — O replay

**Entrega:** a parte de replay de `medir_rota.py` + `test_o_replay_nao_deixa_orfa.py`.

**VERIFY:**
```bash
--seguradora allianz --ramo residencial --servico maquina_de_lavar --replay-detalhado
# esperado: respondidas=20 · 1 órfã funcional (a de §4.2)

--seguradora allianz --ramo residencial --servico chaveiro --replay-detalhado
# esperado: órfãs funcionais MUITO maiores        ← A LINHA DE CONTROLE
```

🔴 **O controle é obrigatório.** Se o replay devolvesse zero órfãs para as duas, não estaria medindo nada. 📊 A auditoria mediu 7 órfãs (todas as classes) para a máquina de lavar e 16 para o chaveiro — o replay **consegue** distinguir.

---

### BLOCO C — A rubrica, o detector do eixo E, e o conserto do teste da régua

🔴 **A v1 punha o detector no Bloco E e o gate do Bloco C dependia dele. Circular.** Aqui ele nasce junto do eixo que decide.

**Entrega:**
1. os cinco eixos em `medir_rota.py`, cada um devolvendo `(pontos, maximo, [evidencias])`
2. o **detector do eixo E** (§3.6)
3. `--verificar-mutacoes`
4. `--conferir-ancoras-de-desfecho` (§3.2)
5. 🔴 **o conserto de `test_a_maquina_de_lavar_vai_ate_o_fim.py`** — trocar `passo_de:64` por `match_ura_step` e `_captura:295` por `extract_capture_anchors`. **É conserto de teste, não de corredor** (§0), e sem ele o gate não fecha
6. `test_a_rubrica_e_honesta.py`

**VERIFY — o gate central:**
```bash
python backend/scripts/medir_rota.py --seguradora allianz --ramo residencial --servico maquina_de_lavar
```
**Esperado: PRONTIDÃO ≥75, e a lista "o que falta" com exatamente os 3 itens de §4.1.**

**Linhas de CONTROLE obrigatórias no `test_a_rubrica_e_honesta.py`:**

```
· a régua tira ≥75
· `mapfre × auto × bateria` devolve ANCORA_SUSPEITA, não nota
  (📊 a âncora casa 0 das 13 sessões — foi escolhido no lugar de
   `tokio × auto × chaveiro`, que fica na borda: ~25)
· uma rota sem fonte devolve SEM_FONTE, não 0     (estados diferentes)
· zerar `regras_para_o_cliente` da régua faz D cair EXATAMENTE 3
· remover o freio da régua faz C cair EXATAMENTE 8
· desqualificar o melhor arquivo de teste faz E cair para o 2º melhor,
  não para 0
· `test_a_maquina_de_lavar_vai_ate_o_fim.py` ANTES do conserto é
  desqualificado; DEPOIS, não     ← prova que o detector funciona nos dois sentidos
```

As três últimas provam que **cada ponto tem dono**. Sem elas, a nota pode ser um número bonito produzido por outra coisa.

---

### BLOCO D — O inventário publicado

**Entrega:** `docs/canon/reports/INVENTARIO-DE-ROTAS.md`, **gerado**.

Cabeçalho obrigatório: commit, data/hora, total de eventos e sessões do acervo **no momento da geração**, e a régua com sua nota.

📊 **Por que o cabeçalho importa:** o acervo é vivo. Entre duas medições com ~28 h de diferença, os eventos foram de 28.092 para **28.094**, as sessões de 542 para **544**, os pares de 16 para **17**. Inventário sem carimbo é inventário que ninguém sabe se está velho.

Seções: a tabela · `## ANCORA SUSPEITA` (as 13 rotas de §3.2) · `## O QUE FALTA COLETAR` (só as `SEM_FONTE`, com roteiro) · `## FAMÍLIAS` (quais rotas compartilham passos).

**VERIFY:** o arquivo existe; o número de linhas de dados **é calculado** (`soma dos subservices dos 14 playbooks`), não fixo em 62 — 📊 a §10.4 lista 8+ serviços que a 084 vai criar, e um VERIFY fixo nasceria errado.

---

### BLOCO E — A regra no CLAUDE.md e as pendências

**Entrega 1** — `CLAUDE.md` §9.4:

```markdown
### 9.4 Teste de corredor chama o motor — teste que chama o regex guarda o regex

> Acrescentado em 21/08/2026, depois que 72 asserções verdes conviveram com um
> agendamento que nunca chegava ao cliente.

A rota da máquina de lavar tinha teste dedicado, 401 linhas, 72 asserções e
linhas de controle de verdade. A âncora `schedule_agendado` estava correta. E o
segurado recebeu "sua assistência foi aberta" sem data e sem período — porque
`extract_capture_anchors` lia cinco chaves e **nunca aquela**.

📊 O arquivo tinha **zero** chamadas ao motor. Dois helpers próprios rodavam
regex direto: um sobre `capture_anchors`, outro reimplementando `match_ura_step`.
Provavam que os regexes casavam. Não provavam que alguém os usava.

    ✅  CP.extract_capture_anchors(playbook, tela_real)
    ❌  re.search(playbook["capture_anchors"]["schedule"], tela_real)

**Vale para toda peça declarativa:** âncora, passo, gatilho, slot, tecla. O que
se afirma é o comportamento do MOTOR sobre o texto REAL.

**Exceção:** regex sobre a âncora COMO TEXTO, para conferir a FORMA da
declaração (ex.: "nenhuma âncora exige `*` literal"), é legítimo — o alvo é a
captura que substitui o motor, não a inspeção da declaração.

**E o texto da tela vem do acervo, não da imaginação.** 📊 O passo
`numero_residencia` exigiu por semanas uma frase com ZERO ocorrências em 28.094
eventos.
```

**Entrega 2** — `PENDENCIAS.md`, com no mínimo:
- as 13 rotas `ANCORA_SUSPEITA`, e o que destrava (ampliar a âncora de desfecho)
- os 8+ serviços do §10.4 (menu real sem subserviço)
- a assimetria `_auto_playbook` × dicts literais (§3.5)
- 📊 a data errada no comentário de `corridor_playbooks.py:254` — diz `28/07/2026`, e a sessão `b2bf40e7` é de **30/12/2025**

**Entrega 3** — o relatório final (§11). 🔴 A v1 não o punha em bloco nenhum, e viraria trabalho não planejado.

**VERIFY:** `grep -c "9.4 Teste de corredor chama o motor" CLAUDE.md` → 1 · o `PENDENCIAS.md` tem as 4 entradas · o relatório existe.

---

## 9. O QUE FICA DE FORA

| item | por quê | vai para |
|---|---|---|
| Alterar qualquer corredor | medir e mudar no mesmo commit é como se perde a régua | SPEC-084 |
| Fechar a órfã funcional da régua | é mudança de corredor | SPEC-084, item 2 |
| Transcrever a sessão no bloco | idem | SPEC-084, item 1 |
| A cadeia de destravamento | outra estrutura | SPEC-085 |
| A senha que chega 1 s tarde · `endereco_logradouro` | são do motor de acionamento | SPEC-085 |
| A auto-atualização | precisa de rotas boas para manter | SPEC-087 (absorve a SPEC-080) |
| A Central de Agentes | independente | SPEC-088 |

---

## 10. ANEXO — OS DADOS PARA A SPEC-084

📊 21/08/2026, banco `dcajcvlzcjbmyapmklil`.

### 10.1 O acervo por corretora × seguradora

| corretora | seguradora | eventos | sessões | mais recente (BRT) |
|---|---|---:|---:|---|
| Resulta | allianz | 10.608 | 93 | 19/08 16:41 |
| AutoFleet | yelum | 3.548 | 82 | 19/08 13:13 |
| AutoFleet | allianz | 2.546 | 47 | 19/08 16:43 |
| AutoFleet | porto | 2.506 | 99 | 11/08 15:37 |
| Resulta | porto | 2.004 | 38 | 18/07 15:12 |
| AutoFleet | hdi | 1.768 | 28 | 29/07 16:50 |
| Resulta | hdi | 1.206 | 15 | 21/07 08:31 |
| Resulta | yelum | 1.056 | 18 | 18/07 11:37 |
| AutoFleet | azul | 829 | 19 | 28/07 16:21 |
| AutoFleet | bradesco | 477 | 22 | 23/07 14:08 |
| AutoFleet | zurich | 458 | 12 | **21/08 11:47** |
| Resulta | tokio | 276 | 22 | 11/08 12:00 |
| AutoFleet | alfa | 264 | 9 | 15/07 14:04 |
| AutoFleet | mapfre | 224 | 12 | **21/08 10:04** |
| Resulta | zurich | 188 | 2 | 06/03 12:22 |
| AutoFleet | tokio | 133 | 24 | 20/08 16:00 |
| AutoFleet | *(NULL)* | 1 | 1 | 09/09/2025 |

**28.094 eventos · 544 sessões · 17 pares.**
⚠️ O par com `insurer_key = NULL` vai para `desconhecido-indefinido.jsonl` e não alimenta rota nenhuma.

### 10.2 Demanda por serviço

⚠️ **Estes números foram produzidos por padrões ad-hoc que a v1 não publicou, e o juiz não conseguiu reproduzir três deles.** Ficam como **💭 ordem de grandeza** até o `PADROES_DE_SERVICO` (§5.5) regerar a tabela no Bloco A.

```
💭  chaveiro ~213 · guincho ~205 · eletricista ~176 · encanador ~152
    bateria ~113 · pneu ~105 · eletrodoméstico ~105 · mecânico ~91 · vidros ~79
```

📊 Os que **reproduziram** na conferência: chaveiro (211–213), guincho (203–205), pneu (104–105), vidros (78–79).
🔴 Os que **não** reproduziram: `eletricista` (só com padrão que contamina AUTO) e `encanador` em porto.

### 10.3 🔴 Socorro mecânico — a medição a refazer

📊 **Confirmado:** `subservice_supported()` devolve `False`. Não existe `socorro_mecanico` em nenhum `subservices` nem em `_SUBSERVICE_ALIASES`.

📊 **Refutado:** a v1 dizia "6 sessões com protocolo, 2 ao vivo". O juiz mediu **38 sessões** mencionando socorro mecânico e **0** contendo a palavra "protocolo" (yelum 21, zurich 9, hdi 8).

⚠️ As duas afirmações são compatíveis com `ANCORA_SUSPEITA` (§3.2) — zurich não escreve "protocolo". **A SPEC-084 refaz a medição citando as `session_id`, e só então decide a prioridade.**

**Mas o essencial continua de pé: é um serviço que aparece em 38 sessões e o produto recusa.**

### 10.4 Serviços no menu real sem subserviço no código

| seguradora | ramo | serviço |
|---|---|---|
| yelum, hdi, porto, allianz | residencial | **Ar condicionado** |
| porto | residencial | chuveiro, chaveiro, desentupimento |
| bradesco, tokio | auto | vidros |
| porto | auto | "Técnico", "Táxi" |
| todas | — | **socorro mecânico** |

⚠️ Levantado por evidência textual citada, **não** por varredura sistemática dos menus. A SPEC-084 refaz com o corpus.

### 10.5 O padrão dos defeitos de âncora — o que procurar nas outras rotas

1. **Âncora com frase que não existe.** `select count(*) from observed_events where text ~* '<ancora>'`. Zero = âncora morta.
2. **Duas famílias da mesma seguradora com listas diferentes.** Conferir `finalize_anchors`, `handoff_triggers` e `capture_anchors` entre auto e residencial. Divergência sem motivo escrito = defeito.
3. **Declaração que o motor não lê.** Conferir toda chave de `capture_anchors` contra `extract_capture_anchors`.
4. **Âncora larga demais.** 📊 `o\.?s\.?` casa o artigo "os". Conferir contra o acervo quantas casam **só** pelo ramo largo.

### 10.6 As sessões da régua

| sessão | data real | protocolo | eventos | `in` | textos distintos |
|---|---|---|---:|---:|---:|
| `8ad1d251` | 22/09/2025 | sim | 336 | 196 | 67 |
| `b2bf40e7` | **30/12/2025** | **51022010 e 51014008** | 350 | 202 | 95 |
| `7ac3c101` | **19/08/2026** | **52955490** | 29 | 29 | 29 |

⚠️ 📊 O comentário em `corridor_playbooks.py:254` diz *"sessao b2bf40e7, **28/07/2026**"* — **28/07 é a data de ingestão**, não da conversa. A sessão é de **30/12/2025**. É a única citação de sessão do arquivo, e está errada.

---

## 11. RELATÓRIO FINAL

`docs/canon/reports/SPEC-EXECUTION-REPORT-TEMPLATE.md`. Obrigatórios:

- commit inicial e final · a conferência do GLOSSARIO (§0)
- a saída **real** de `medir_rota.py` para a régua — o gate do Bloco C — com a nota medida substituindo a estimativa de §4.1
- a saída **real** do replay da régua **e** do chaveiro (a linha de controle)
- a saída **real** de `--conferir-ancoras-de-desfecho`, com as rotas `ANCORA_SUSPEITA`
- a saída **real** de `--verificar-mutacoes`
- a saída de cada teste novo, com a mutação e o vermelho que produziu
- quantas linhas o gerador **mascarou** e quantas **recusou**, por seguradora
- o `INVENTARIO-DE-ROTAS.md` gerado
- **declaração de que nenhum corredor foi alterado**
- o que ficou de fora → `PENDENCIAS.md`

---

## 12. O JULGAMENTO DA v1 — o que mudou e por quê

Registrado porque a SPEC-084 vai reusar a mesma disciplina.

| # | defeito na v1 | correção na v2 |
|---|---|---|
| **D1** | Gate impossível: ≥95 exigido, eixo E zerado, conserto proibido. Teto 85 | regra por-arquivo (§3.6) + conserto do teste dentro desta SPEC (Bloco C) + gate ≥75 (§4.3) |
| **D2** | A régua tirava 63, não 98 | §4 inteira. A régua tira ~79, e os 3 buracos viram as 3 primeiras entregas da 084 |
| **D3** | 75 pontos por declaração; rota vazia tirava 49 | §2.3. Todo ponto contra o corpus. `_COMO_PERGUNTAR` fora; apelidos, freio e handoff só com tela real |
| **D4** | 13 rotas iriam para coleta com acervo cheio | `ANCORA_SUSPEITA` (§3.2) |
| **D5** | 4 conferências e 5 itens não decidíveis por máquina | `DECIDE:` em cada um (§2.4, §3) |
| **D6** | Números não reproduzíveis; §1.4 medida por instrumento inexistente | `PADROES_DE_SERVICO` (§5.5) · §1.4 corrigida · §10.2 marcada 💭 · §5.2 marcada 💭 |
| **D7** | PII: recusa apagava 3 passos da régua; VERIFY não podia falhar | mascarar (§6.4) + VERIFY com controle (Bloco A) |
| **D8** | Blocos circulares; Bloco A sem regra de ramo | detector move para C · passo 0 de inferência de ramo |
| **D9** | Famílias: pontos por medição emprestada | `notes` com seguradora explícita (§3.3) · coluna FAMÍLIA (§5.3) |
| **D10** | Multi-tenant nunca decidido; `out` no corpus | §6.2 e §6.3 |
| **D11** | Corpus sem teto | §6.5 |
| **D12** | 11 números errados | corrigidos ao longo do texto |

**O que o juiz aprovou e não deve ser mexido:** §1.3 (o diagnóstico da causa raiz — ele **confirmou** as linhas 64 e 295), o replay como gate (**a única medida que reproduziu**), a linha de controle do chaveiro, o teste ao vivo virando selo, `SEM_FONTE` em coluna própria, a proibição de reimplementar o motor (📊 6 das 7 funções conferidas com nome e assinatura exatos), e o anexo §10.1 (**16 linhas conferidas, todas batem**).
