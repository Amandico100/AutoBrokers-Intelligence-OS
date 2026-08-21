# SPEC-083 — A RÉGUA DO CORREDOR

> **O que é uma rota pronta, como se prova sem opinião, e a ferramenta que dá a nota sozinha.**
>
> Autor: execução · Data: 21/08/2026 · Commit base: `7af5c3c`
> Branch: `feat/spec083-a-regua-do-corredor`
> Antecede e habilita: **SPEC-084 (A Fábrica de Rotas)**

---

## 0. PREFLIGHT OBRIGATÓRIO

```bash
git rev-parse --show-toplevel      # deve terminar em AutoBrokers-FIX
git branch --show-current          # feat/spec083-a-regua-do-corredor
git rev-parse HEAD                 # registrar no relatório final
git status --short                 # LIMPO ao iniciar
```

Leitura obrigatória antes da primeira linha de código:

1. `CLAUDE.md` — inteiro. Em especial **§9.2** (medir vence deduzir; toda bateria precisa de CONTROLE), **§9.3** (teste que guarda verdade vencida) e **§12.1** (📊 medido vs 💭 ilustrativo).
2. `docs/canon/GLOSSARIO.md` — os termos desta SPEC (`corredor`, `subcorredor`, `rota`, `playbook`, `âncora`, `passo`) precisam bater com ele. Se divergirem, **o glossário vence** e esta SPEC é corrigida.
3. `docs/canon/PORTAIS-E-CORREDORES.md` — portal ≠ corredor ≠ Atlas.
4. `docs/canon/O-ATLAS-E-UM-SO-E-E-DE-TODAS.md` — o Atlas é um só, de todas as corretoras.

⚠️ **Esta SPEC não altera nenhum corredor.** Ela cria a régua, a ferramenta e o gate. Quem altera corredor é a SPEC-084. Misturar as duas é o que produz o defeito que esta SPEC existe para impedir: mudar a coisa e a medida da coisa no mesmo commit.

---

## 1. POR QUE ESTA SPEC EXISTE

### 1.1 O fato que a originou

📊 Em **19/08/2026 às 16:35 BRT** o Founder conduziu, ao vivo e com cliente real (Clarissa Medeiros da Luz, CPF `030***95`, apólice Allianz residencial `202623140079868`), um acionamento de assistência para **máquina de lavar**. A atendente Saionara coletou os dados em 10 minutos e 6 perguntas; o corredor conversou com a URA da Allianz e voltou com o **protocolo 52955490** em **5 minutos e 55 segundos**.

Work Run: `e5279497-a642-4703-a85f-d92a381e45ac`.

📊 A execução, medida em duas fontes independentes que batem (`work_events` e o Espelho em `conversations`/`messages`):

```
22 respostas à URA
19 por âncora determinística ......... 86 %
 3 pelo cérebro adaptativo ........... 14 %
 2 silêncios deliberados (noop)
 0 needs_human
 0 retentativas
 0 loop_guard
```

**Foi o primeiro e único corredor validado em produção do produto.** Virou a régua.

### 1.2 O problema: a régua tinha quatro furos, e nenhum era visível

📊 Auditoria de **21/08/2026** encontrou, dentro dessa mesma rota:

| # | furo | evidência medida |
|---|---|---|
| 1 | O passo `numero_residencia` exigia a frase `informe o número da residência` | 📊 **ZERO ocorrências** em 28.092 eventos do acervo. A URA escreve `"Agora, me CONFIRME o número da residência"` — 180 mensagens, 72 sessões, a mais recente sendo **a própria sessão da régua**, às 16:36:51 |
| 2 | O freio de finalização do residencial não tinha `dados a seguir estão corretos` | 📊 154 mensagens / 64 sessões passaram pela conferência **sem freio**. O `allianz-auto` tem essa âncora desde sempre |
| 3 | `schedule_agendado` era declarado e o motor **nunca o lia** | 📊 `extract_capture_anchors` lia 5 chaves e não essa. A cliente recebeu *"Prontinho! ✅ Sua assistência foi aberta"* — **sem data e sem período** |
| 4 | `\*dica:\*` exigia asterisco literal num texto que `_norm` já removeu | âncora morta desde 17/08, deixando `test_o_negrito_da_seguradora_nao_emudece_o_corredor` **vermelho em produção** |

**Nenhum dos quatro derrubou o atendimento.** Todos foram cobertos por cima — pelo cérebro adaptativo (que respondeu as telas órfãs) ou pela própria atendente (que deduziu a senha). **Furo coberto é furo que ninguém vê.**

Os quatro foram consertados no commit `7af5c3c`, com o guarda `test_a_regua_nao_tem_furo.py` (25 asserções, 3 mutações provadas). **Esta SPEC existe porque eles não deveriam ter chegado à produção.**

### 1.3 🔴 A causa raiz: o teste guardava o regex, não o motor

O furo nº 3 é o mais instrutivo. A rota tinha **72 asserções verdes** (`test_a_maquina_de_lavar_vai_ate_o_fim.py`, 401 linhas) — e o agendamento nunca chegava ao cliente.

O motivo está na linha 295 do teste: um helper `_captura` que roda `re.search` **direto na âncora**, sem passar por `extract_capture_anchors`. O regex estava certo. O motor não o lia. O teste provava o regex.

> ## A REGRA QUE NASCE DESTA SPEC
>
> **Teste de corredor tem de chamar o MOTOR.**
> **Teste que chama o regex não guarda o corredor — guarda o regex.**
>
> Corolário do CLAUDE.md §9.3, e ela vai para o CLAUDE.md nesta SPEC.

### 1.4 O que a auditoria mediu sobre o resto do produto

📊 62 unidades (seguradora × ramo × serviço) em 14 corredores. Nota média **46,3**, mediana **49**. **Uma** unidade acima de 80 — a régua. O segundo lugar tira **75**.

📊 E o acervo que existe para consertar isso é muito maior do que a primeira auditoria enxergou:

```
28.092 eventos · 16 pares corretora×seguradora · 13 meses (jul/2025 → 21/08/2026)
300 menções a protocolo

por seguradora:  allianz 141 sessões · porto 138 · yelum 100 · tokio 47 · hdi 44
                 bradesco 22 · azul 19 · zurich 15 · mapfre 13 · alfa 9
por serviço:     chaveiro 213 · guincho 205 · eletricista 176 · encanador 152
                 bateria 113 · pneu 105 · eletrodoméstico 105 · mecânico 91 · vidros 79
```

📊 A mapfre — que uma auditoria anterior classificou como "sem nenhuma sessão observada" — tem **13 sessões e evento de 21/08/2026 às 10:04**. O erro veio de `observed_sessions.ramo` e `.servico` estarem **NULL nas 572 linhas**, forçando classificação por texto.

**Conclusão que muda o plano inteiro: o material existe. Falta minerá-lo e indexá-lo por serviço.**

---

## 2. O QUE É UMA ROTA AAA

### 2.1 A definição, em uma frase

> **Uma rota AAA é aquela em que o agente vai do "oi" do segurado ao protocolo da seguradora sem nenhum humano tocar — e o segurado sabe o número do chamado, o dia e o período em que o técnico vem.**

Tudo o mais nesta SPEC é a tradução dessa frase em conferências que uma máquina consegue fazer.

### 2.2 Por que "AAA" e não "100%"

O Founder pediu o equivalente ao **triplo A** da indústria de jogos: um patamar que um juiz crítico cobra sem negociar. A tradução para este produto:

| na indústria de jogos | aqui |
|---|---|
| não trava, não crasha | **o acionamento não emudece nem morre em silêncio** |
| não tem textura faltando | **nenhuma tela da URA fica órfã** |
| não tem bug de progressão | **toda tecla tem origem; nenhuma é chutada** |
| o jogador entende o que fazer | **o segurado sabe o protocolo, o dia e o período** |
| passa na certificação | **o teste chama o motor e a mutação fica vermelha** |

**O juiz crítico não aprova nada abaixo disso.** Não existe "quase pronto".

### 2.3 As dez conferências

Cada uma é verificável por código, sem opinião:

| # | conferência | como se prova |
|---|---|---|
| 1 | Existe ≥1 sessão observada que chegou ao protocolo, **transcrita no comentário do bloco** | a `session_id` citada existe em `observed_events` e contém a âncora de protocolo |
| 2 | **Zero órfãs funcionais** no replay das telas reais | `replay` da rota contra as telas da(s) sessão(ões): toda tela que PEDE algo casa um passo |
| 3 | ≥85% das respostas por âncora determinística | contagem no replay |
| 4 | Toda tecla `_opcao` tem origem: subserviço **ou** derivação com default | varredura dos `requires` contra `subservices` + `_derivar_teclas_do_caso` |
| 5 | Os apelidos cobrem como o cliente **fala** | `canonical_subservice()` resolve cada apelido; os apelidos vêm do acervo |
| 6 | `regras_para_o_cliente` e `expectativa_do_desfecho` existem e **citam a tela de origem** | presença + o comentário aponta a tela |
| 7 | O freio de finalização **casa** a tela real de confirmação daquele fluxo | `detect_finalize_anchor()` contra o texto do banco |
| 8 | Existe teste dedicado que chama **o motor**, com mutação provada | o arquivo existe, referencia `match_ura_step`/`extract_capture_anchors`/`detect_finalize_anchor`, e a mutação fica vermelha |
| 9 | Todo slot de `required_slots` tem frase em `_COMO_PERGUNTAR` | varredura |
| 10 | A mensagem ao cliente carrega **protocolo + dia + período** quando o serviço é agendado | `client_summary_from_capture` sobre a captura real |

### 2.4 🔴 O que NÃO entra na régua, e por quê

**O teste ao vivo não vale ponto.** Ele vira **selo**.

Razão, com o caso concreto: 📊 antes de 19/08 a máquina de lavar já estava pronta — os 9 passos, as 3 teclas, os 11 apelidos, as 5 regras, as 72 asserções. Uma rubrica que descontasse "não testado" lhe daria nota baixa **exatamente quando ela estava boa**. A nota teria mentido.

O teste ao vivo prova outra coisa: que **a URA de hoje** ainda é a que mapeamos. É informação de validade, não de qualidade. Por isso é selo com data.

**Também não entram:** número de linhas, número de passos, tamanho do playbook. 📊 Contraexemplo que fecha a porta: `mapfre-auto` tem **8 `required_slots`** e **4 `ura_steps`**. Coleta oito dados e tem quatro telas onde usá-los. **Slot sem passo é dado que não vira tecla.**

---

## 3. A RUBRICA — 100 pontos, eixo por eixo

### 3.1 Os cinco eixos

```
A · EVIDÊNCIA NO ACERVO ................................. 25 pontos
B · COBERTURA DO MAPA ................................... 25 pontos
C · SEGURANÇA ........................................... 20 pontos
D · CONHECIMENTO ........................................ 15 pontos
E · PROVA ............................................... 15 pontos
                                                        ─────────
                                              PRONTIDÃO  100 pontos
```

### 3.2 Eixo A — Evidência no acervo (25)

*Pergunta: alguém já percorreu esta rota até o fim, e nós temos o registro?*

| condição | pontos |
|---|---|
| ≥1 sessão que alcançou **protocolo** neste serviço | **15** |
| a sessão está **transcrita** no comentário do bloco (turno a turno) | **5** |
| ≥2 sessões distintas do mesmo serviço (permite comparar redações) | **3** |
| a sessão mais recente tem menos de 180 dias | **2** |

🔴 **Regra dura:** eixo A = 0 → a rota **não pode receber nota nenhuma** nos outros eixos. Devolve `SEM_FONTE` e vai para a lista de coleta.

Justificativa: 📊 sem sessão, escrever passo é inventar rótulo de menu. Um rótulo inventado manda o segurado para a opção errada — e o corredor não trava, ele **responde com confiança a coisa errada**. É o pior desfecho possível.

**Como medir (SQL):**
```sql
-- Sessões daquela seguradora que mencionam a tela mais funda do serviço
-- E que contêm a âncora de protocolo do corredor.
with s as (
  select session_id, insurer_key, max(wa_timestamp) as fim,
         bool_or(text ~* '<ANCORA_DE_PROTOCOLO_DO_CORREDOR>') as protocolo,
         string_agg(lower(text), ' ') as tudo
  from observed_events where insurer_key = '<SEGURADORA>' group by 1,2
)
select count(*) filter (where protocolo) as com_protocolo,
       count(*) as sessoes,
       max(fim) as mais_recente
from s where tudo ~ '<PADRAO_DO_SERVICO>';
```

### 3.3 Eixo B — Cobertura do mapa (25)

*Pergunta: as telas que a URA mostra viraram passos?*

O coração é o **replay**: pegar as telas reais da(s) sessão(ões) e rodá-las contra `match_ura_step` com o subserviço da rota.

Cada tela cai em uma de quatro classes:

```
RESPONDIDA      casou um passo que devolve resposta          ✅
NOOP            casou um passo `noop` (silêncio deliberado)  ✅
ÓRFÃ INÓCUA     não casou, e a tela NÃO pede nada            ⚪ tolerável
ÓRFÃ FUNCIONAL  não casou, e a tela PEDE algo                🔴 é o defeito
```

| condição | pontos |
|---|---|
| **zero órfãs funcionais** | **15** |
| 1 órfã funcional | 8 |
| 2 órfãs funcionais | 3 |
| ≥3 órfãs funcionais | 0 |
| ≥85% de respostas determinísticas (respondidas ÷ telas que pedem algo) | **6** |
| entre 70% e 85% | 3 |
| toda tela respondida cita a contagem de ocorrências no `notes` | **4** |

**O discriminador "a tela pede algo"** já existe no produto: `_tela_pede_alguma_coisa(playbook, texto)` em `insurer_dispatch_service.py`. **Reusar, nunca reescrever** (CLAUDE.md §5) — ele lê os `finalize_anchors` do próprio corredor e a lista genérica, e um segundo discriminador divergiria em silêncio.

### 3.4 Eixo C — Segurança (20)

*Pergunta: quando errar dói, o corredor para?*

| condição | pontos |
|---|---|
| o freio de finalização **casa** a tela real de confirmação daquele fluxo | **8** |
| toda tecla `_opcao` da rota tem origem (subserviço ou derivação com default) | **6** |
| existe ≥1 `handoff_trigger` que casa a frase real de transferência da seguradora | **3** |
| nenhuma âncora da rota exige `*` literal (`\*` sem `?`) | **3** |

**Por que o freio vale 8:** é a última porta antes de mandar um prestador a um endereço. 📊 A ausência dele no residencial deixou 64 sessões passarem pela conferência sem nenhuma verificação.

**Por que a tecla vale 6:** 📊 tecla errada não trava — ela **abre o chamado errado**. `14` é máquina de lavar; `10` é lava-louças; `13` é secadora. O erro só aparece quando o técnico chega.

### 3.5 Eixo D — Conhecimento (15)

*Pergunta: a atendente sabe o que perguntar e o que avisar, antes de chamar a ferramenta?*

| condição | pontos |
|---|---|
| todo slot de `required_slots` tem frase em `_COMO_PERGUNTAR` | **5** |
| `expectativa_do_desfecho` existe para a rota | **4** |
| `regras_para_o_cliente` existe **e cita a tela de origem** no comentário | **3** |
| os apelidos resolvem ≥3 formas de o cliente falar, e vieram do acervo | **3** |

📊 Base: o bloco `conhecimento_de_assistencia` (3.577 caracteres para o corredor residencial da Allianz) é **gerado** desses campos e injetado no prompt da atendente. Campo vazio = atendente muda sobre aquele ponto.

### 3.6 Eixo E — Prova (15)

*Pergunta: se alguém quebrar isto amanhã, algo fica vermelho?*

| condição | pontos |
|---|---|
| existe arquivo de teste que nomeia a rota | **3** |
| ele chama **o motor** (`match_ura_step` / `extract_capture_anchors` / `detect_finalize_anchor` / `missing_slots_for_subservice`) | **5** |
| ≥1 linha de **CONTROLE** explícita (prova que a asserção consegue falhar) | **4** |
| a mutação documentada fica vermelha (registrada no comentário do teste) | **3** |

🔴 **A conferência do motor é automatizável e obrigatória:** o arquivo de teste é lido e se ele contém `re.search(` sobre uma âncora **sem** chamar o motor no mesmo bloco, o eixo E é **zerado**, por mais asserções verdes que tenha. Foi exatamente esse o caso das 72 asserções da régua.

### 3.7 O selo e o estado da fonte

Fora dos 100 pontos, dois carimbos:

```
SELO DE CAMPO      🟢 TESTADO AO VIVO em <data>, protocolo <n>
                   ⚪ NÃO TESTADO
                   🔴 TESTADO E FALHOU em <data>, motivo <x>

ESTADO DA FONTE    🟢 COMPLETA    sessão(ões) até o protocolo
                   🟡 PARCIAL     sessão existe, não chegou ao fim
                   🔴 INEXISTENTE nunca trilhada — precisa de coleta
```

**A leitura de uma linha da tabela passa a ser:**

> `allianz × residencial × maquina_de_lavar` — **98/100** · 🟢 testado 19/08 · 🟢 fonte completa

📊 E a mesma rota **antes** do teste ao vivo: **98/100 · ⚪ não testado · 🟢 fonte completa.** A prontidão não muda. É essa a correção que esta rubrica traz.

### 3.8 Os patamares

```
 98-100   AAA        pronto. O juiz aprova.
 85-97    quase       falta algo nomeável. Vai à fila com o item que falta.
 60-84    parcial     o caminho existe e não fecha sozinho.
 30-59    esqueleto   há passos, não há rota.
  1-29    toco        o corredor não responde a esta URA.
    —     SEM_FONTE   eixo A = 0. Não é nota baixa: é ausência de matéria-prima.
```

⚠️ **`SEM_FONTE` não é uma nota ruim.** É um estado diferente, e a tabela precisa mostrá-lo em coluna própria — senão a média mistura "está mal feito" com "nunca vimos", e as duas pedem ações opostas.

---

## 4. A FERRAMENTA — `medir_rota.py`

### 4.1 O que ela é

Um script em `backend/scripts/medir_rota.py` que recebe uma rota e devolve a nota, eixo por eixo, com a evidência de cada ponto. **Determinístico, sem LLM, sem rede além do Supabase de leitura.**

```bash
# uma rota
python backend/scripts/medir_rota.py --seguradora allianz --ramo residencial --servico maquina_de_lavar

# todas
python backend/scripts/medir_rota.py --todas --formato tabela
python backend/scripts/medir_rota.py --todas --formato json > /tmp/notas.json

# só o replay, com o detalhe de cada tela
python backend/scripts/medir_rota.py --seguradora allianz --ramo residencial \
       --servico maquina_de_lavar --replay-detalhado
```

### 4.2 A saída, por rota

```
allianz × residencial × maquina_de_lavar
─────────────────────────────────────────────────────────────────
PRONTIDÃO  98/100      🟢 testado 19/08/2026 (protocolo 52955490)
FONTE      🟢 COMPLETA  3 sessões · 3 com protocolo · mais recente 19/08/2026

A EVIDÊNCIA NO ACERVO      25/25
  ✅ 15  3 sessões com protocolo (8ad1d251, b2bf40e7, 7ac3c101)
  ✅  5  transcrita no comentário (linhas 436-465 de corridor_playbooks.py)
  ✅  3  ≥2 sessões distintas
  ✅  2  mais recente há 2 dias

B COBERTURA DO MAPA        23/25
  ✅ 15  zero órfãs funcionais
  ✅  6  86% determinístico (19 de 22)
  ⚠️  2/4  3 de 9 passos sem contagem no `notes`

C SEGURANÇA                20/20
  ✅  8  freio casa "Podemos confirmar o atendimento?" e "dados a seguir estão corretos"
  ✅  6  3 teclas no subserviço + 2 derivações com default
  ✅  3  handoff casa "não foi possível"
  ✅  3  nenhuma âncora exige asterisco

D CONHECIMENTO             15/15
E PROVA                    15/15
  ✅  3  test_a_maquina_de_lavar_vai_ate_o_fim.py + test_a_regua_nao_tem_furo.py
  ✅  5  chama match_ura_step, extract_capture_anchors, detect_finalize_anchor
  ✅  4  17 linhas de CONTROLE
  ✅  3  mutação registrada: 3 mutações, 1/2/6 vermelhas

O QUE FALTA PARA 100
  · pôr a contagem de ocorrências no `notes` de menu_aparelho,
    aparelho_marca e aparelho_modelo               (+2)
```

### 4.3 A saída, com `--todas`

Uma linha por unidade, ordenável, com as colunas que o Founder pediu:

```
SEGURADORA  RAMO         SERVIÇO           PRONT  A  B  C  D  E  SELO  FONTE   DEMANDA
allianz     residencial  maquina_de_lavar    98  25 23 20 15 15  🟢    🟢          105
yelum       auto         guincho             75  20 15 17 12 11  ⚪    🟢          205
...
tokio       auto         chaveiro            14   0  0  8  3  3  ⚪    🟡          213
mapfre      auto         bateria              —   0  —  —  —  —  ⚪    🔴          113
```

A coluna **DEMANDA** é 📊 a contagem de sessões no acervo em que aquele serviço aparece — é o que ordena o trabalho da SPEC-084.

### 4.4 Requisitos de implementação

**Onde mora.** `backend/scripts/medir_rota.py`. Script, não serviço: ele não roda em produção, não tem rota HTTP, não é agendado. É ferramenta de quem escreve corredor — exatamente o uso que `docs/canon/O-ATLAS-E-PARA-QUEM-ESCREVE-O-CORREDOR.md` já define para o mapa.

**O que ele NÃO pode fazer:**
- ❌ escrever qualquer coisa no banco
- ❌ chamar LLM
- ❌ tocar em portal ou WhatsApp
- ❌ importar `app.services.__init__` (ele puxa o mundo). Carregue os módulos por caminho, como fazem os testes:
  ```python
  for pkg in ("app", "app.services", "app.core"):
      mod = types.ModuleType(pkg); mod.__path__ = [...]; sys.modules[pkg] = mod
  ```

**O que ele DEVE reusar, e nunca reescrever** (CLAUDE.md §5):

| precisa de | usar |
|---|---|
| casar tela com passo | `corridor_playbooks.match_ura_step` |
| capturar protocolo/senha/agendamento | `corridor_playbooks.extract_capture_anchors` |
| saber se a tela é de finalização | `corridor_playbooks.detect_finalize_anchor` |
| saber se a tela pede algo | `insurer_dispatch_service._tela_pede_alguma_coisa` |
| resolver apelido → rota | `corridor_playbooks.canonical_subservice` |
| saber o que falta na ficha | `corridor_playbooks.missing_slots_for_subservice` |
| normalizar texto | `corridor_playbooks._norm` |

🔴 **Se a ferramenta reimplementar qualquer um desses, ela mede uma coisa e o produto faz outra** — e a nota vira ficção. É o mesmo defeito do helper `_captura` que originou esta SPEC, um nível acima.

**Credenciais.** Lê `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` do ambiente. Sem elas, roda em **modo offline**: mede os eixos B, C, D e E (que só dependem do código) e devolve `A: sem banco` — nunca inventa o eixo A.

---

## 5. O GATE DE REPLAY

### 5.1 O que é

Um teste que roda o replay de **todas** as rotas com fonte disponível e falha se alguma tiver órfã funcional.

`backend/tests/test_o_replay_nao_deixa_orfa.py`

### 5.2 Por que ele é o gate certo

📊 A auditoria mediu, com o replay, a distância entre a régua e o resto:

```
allianz-residencial / maquina_de_lavar   respondidas=20  noop=2  órfãs= 7
allianz-residencial / chaveiro           respondidas=11  noop=2  órfãs=16   ← MESMO corredor
allianz-residencial / desentupimento     respondidas=11  noop=2  órfãs=16
mapfre-auto  / guincho                   respondidas= 0  noop=0  órfãs=29
tokio-auto   / guincho                   respondidas= 0  noop=0  órfãs=29
```

Uma única medida separa a rota validada de todas as outras. **É a medida que o gate cobra.**

### 5.3 Como ele se comporta

- Rota com **fonte completa** e órfã funcional → **vermelho**
- Rota com **fonte parcial/inexistente** → **pulada, com linha no relatório** dizendo qual e por quê
- 🔴 **Nunca pula em silêncio.** CLAUDE.md: *"se um workflow limita cobertura, `log()` o que foi descartado — truncar em silêncio lê-se como 'cobrimos tudo'"*

### 5.4 O corpus do replay

As telas vêm de um arquivo versionado, não de consulta ao banco em tempo de teste:

`backend/tests/corpus/telas_reais/<seguradora>-<ramo>.jsonl`

Cada linha: `{"session_id": "...", "wa_timestamp": "...", "direction": "in", "text": "..."}`

**Por quê versionado:**
1. o teste roda sem banco (CI, máquina de quem escreve corredor)
2. o corpus é **prova datada** — se a URA mudar, o corpus antigo continua sendo o que justificou aquele passo
3. 📊 o acervo tem PII: o corpus é gerado com a mesma higiene que o Atlas usa (`ura_map_service`), e o gerador **recusa** gravar linha com CPF, telefone ou nome não mascarado

Gerador: `backend/scripts/gerar_corpus_de_telas.py --seguradora <x> --ramo <y>`

---

## 6. A REGRA DO TESTE NO CLAUDE.md

Acrescentar ao `CLAUDE.md`, como **§9.4**:

```markdown
### 9.4 Teste de corredor chama o motor — teste que chama o regex guarda o regex

> Acrescentado em 21/08/2026, depois que 72 asserções verdes conviveram com um
> agendamento que nunca chegava ao cliente.

A rota da máquina de lavar tinha teste dedicado, 401 linhas, 72 asserções, e
linhas de controle de verdade. A âncora `schedule_agendado` estava correta. E o
segurado recebeu "sua assistência foi aberta" sem data e sem período — porque
`extract_capture_anchors` lia cinco chaves e **nunca aquela**.

O teste passava porque tinha um helper próprio que rodava `re.search` direto na
âncora. Ele provava que o regex casava. Não provava que alguém o usava.

    ✅  CP.extract_capture_anchors(playbook, tela_real)
    ❌  re.search(playbook["capture_anchors"]["schedule"], tela_real)

**Vale para toda peça declarativa:** âncora, passo, gatilho, slot, tecla. O que
se afirma é o comportamento do MOTOR sobre o texto REAL — nunca a forma da
declaração.

**E o texto da tela vem do acervo, não da imaginação.** Copiar do banco custa
uma query; inventar custa uma âncora que nunca casa. 📊 O passo
`numero_residencia` exigiu por semanas uma frase com ZERO ocorrências em 28.092
eventos.
```

---

## 7. OS BLOCOS DE EXECUÇÃO

Cada bloco é entrega coesa com gate verificável. Gates internos são automáticos (CLAUDE.md §9): aplicar → VERIFY → testes → verde → avançar.

### BLOCO A — O corpus de telas reais

**Entrega:** `backend/scripts/gerar_corpus_de_telas.py` + os `.jsonl` das 10 seguradoras.

**Passos:**
1. Ler `observed_events` por `(insurer_key, ramo inferido)`.
2. Deduplicar por `(session_id, wa_timestamp, text)` — 📊 metade dos eventos de algumas sessões são duplicatas (a sessão `9cb09e20` repete o fluxo inteiro).
3. Passar cada linha pela higiene de PII. **Recusar** a linha que não passar, e contar quantas foram recusadas.
4. Gravar ordenado por `wa_timestamp`.

**VERIFY:**
```bash
python backend/scripts/gerar_corpus_de_telas.py --todas --dry-run
# imprime: por seguradora, quantas telas, quantas sessões, quantas recusadas por PII
ls backend/tests/corpus/telas_reais/*.jsonl | wc -l     # esperado: ≥10
grep -cE '[0-9]{11}' backend/tests/corpus/telas_reais/*.jsonl   # esperado: 0 em todos
```

**Guarda:** `test_o_corpus_nao_vaza_pii.py` — com **linha de controle**: uma linha com CPF real é recusada, e uma linha mascarada passa. Se as duas passarem ou as duas forem recusadas, o guarda não guarda.

---

### BLOCO B — O replay

**Entrega:** `backend/scripts/medir_rota.py` (só a parte do replay) + `test_o_replay_nao_deixa_orfa.py`.

**Passos:**
1. Para cada rota, carregar o corpus da seguradora+ramo.
2. Rodar cada tela por `match_ura_step(playbook, tela, subservice=rota)`.
3. Classificar em RESPONDIDA / NOOP / ÓRFÃ INÓCUA / ÓRFÃ FUNCIONAL usando `_tela_pede_alguma_coisa`.
4. Devolver a contagem e a lista das órfãs funcionais, com o texto da tela.

**VERIFY:**
```bash
python backend/scripts/medir_rota.py --seguradora allianz --ramo residencial \
       --servico maquina_de_lavar --replay-detalhado
# esperado: órfãs funcionais = 0 (a régua)

python backend/scripts/medir_rota.py --seguradora allianz --ramo residencial \
       --servico chaveiro --replay-detalhado
# esperado: órfãs funcionais > 0  ← A LINHA DE CONTROLE
```

🔴 **O controle é obrigatório.** Se o replay devolvesse zero órfãs para as duas, ele não estaria medindo nada. 📊 A auditoria mediu 7 órfãs para a máquina de lavar e 16 para o chaveiro — o replay **consegue** distinguir.

---

### BLOCO C — A rubrica completa

**Entrega:** os cinco eixos em `medir_rota.py` + `test_a_rubrica_e_honesta.py`.

**Passos:** implementar A, B, C, D, E conforme §3, cada um devolvendo `(pontos, maximo, [evidencias])`.

**VERIFY — e este é o gate mais importante da SPEC:**
```bash
python backend/scripts/medir_rota.py --seguradora allianz --ramo residencial --servico maquina_de_lavar
```

**Esperado: PRONTIDÃO entre 95 e 100.**

🔴 Se a régua não tirar ~98, **a rubrica está errada, não a rota.** A rota é a definição de pronto; a rubrica é a tentativa de descrevê-la. Divergiram → ajusta-se a rubrica, **nunca** se maquia a rota.

**Linhas de controle obrigatórias no `test_a_rubrica_e_honesta.py`:**
```
· a régua tira ≥95
· `tokio × auto × chaveiro` tira <30          (a rubrica consegue dar nota baixa)
· uma rota sem fonte devolve SEM_FONTE, não 0 (são estados diferentes)
· zerar `regras_para_o_cliente` da régua faz D cair exatamente 3 pontos
· remover o freio da régua faz C cair exatamente 8 pontos
```

As duas últimas provam que **cada ponto tem dono**. Sem elas, a nota pode ser um número bonito produzido por outra coisa.

---

### BLOCO D — O inventário publicado

**Entrega:** `docs/canon/reports/INVENTARIO-DE-ROTAS.md` — gerado, não escrito à mão.

**Passos:**
1. `python backend/scripts/medir_rota.py --todas --formato markdown > docs/canon/reports/INVENTARIO-DE-ROTAS.md`
2. O cabeçalho traz: o commit, a data, o total de eventos do acervo e a régua com sua nota.
3. Uma seção `## O QUE FALTA COLETAR` lista as rotas `SEM_FONTE`, com o roteiro de coleta de cada uma.

**VERIFY:** o arquivo existe, tem 62 linhas de dados, e a linha da régua bate com a saída de `--seguradora allianz`.

---

### BLOCO E — A regra no CLAUDE.md

**Entrega:** o §9.4 de §6 desta SPEC, acrescentado ao `CLAUDE.md`.

**VERIFY:** `grep -c "9.4 Teste de corredor chama o motor" CLAUDE.md` → 1

**Guarda:** acrescentar ao `test_a_rubrica_e_honesta.py` a conferência do eixo E que detecta `re.search` sobre âncora sem chamada ao motor — rodada contra `test_a_maquina_de_lavar_vai_ate_o_fim.py`, que 📊 **hoje tem esse defeito na linha 295**. O guarda deve acusá-lo.

⚠️ Consertar aquele helper é trabalho da **SPEC-084**, não desta. Aqui só se prova que o detector o enxerga.

---

## 8. O QUE FICA DE FORA DESTA SPEC

| item | por quê | vai para |
|---|---|---|
| Consertar qualquer corredor | esta SPEC cria a medida; medir e mudar no mesmo commit é o defeito que ela combate | SPEC-084 |
| Consertar o helper `_captura` da régua | idem | SPEC-084 |
| A cadeia de destravamento (Vigia/Sentinela/Cérebro) | é outra estrutura, com outros defeitos | SPEC-085 |
| A senha que chega 1 segundo tarde | é do motor de acionamento, não do corredor | SPEC-085 |
| O `endereco_logradouro` na ficha residencial | idem | SPEC-085 |
| A auto-atualização | precisa de rotas boas para manter | SPEC-087 |
| A Central de Agentes | independente | SPEC-088 |

---

## 9. RISCOS E COMO SÃO FECHADOS

| risco | fechamento |
|---|---|
| **A rubrica premia o que é fácil de medir, não o que importa** | O gate do Bloco C: a régua tem de tirar ~98. Ela é a definição, e a rubrica é a hipótese sobre ela |
| **O corpus congela uma URA que já mudou** | O corpus é prova datada, não verdade eterna. O `medir_rota` mostra a idade da sessão mais recente, e o eixo A desconta acima de 180 dias |
| **A ferramenta diverge do motor** | Proibição de reimplementar + a lista de §4.4. O guarda do eixo E detecta o padrão |
| **`SEM_FONTE` vira "nota zero" na leitura** | Coluna própria na tabela e no relatório. Estados diferentes, ações opostas |
| **O gate de replay fica vermelho e viram a chave para ignorá-lo** | Ele só cobra rotas com fonte completa. Rota sem fonte é pulada **com linha no relatório** |

---

## 10. ANEXO — OS DADOS MEDIDOS QUE A SPEC-084 VAI PRECISAR

📊 Levantado em 21/08/2026, banco `dcajcvlzcjbmyapmklil`.

### 10.1 O acervo, por corretora e seguradora

| corretora | seguradora | eventos | sessões | mais recente |
|---|---|---:|---:|---|
| Resulta | allianz | 10.608 | 93 | 19/08/2026 16:41 |
| AutoFleet | yelum | 3.548 | 82 | 19/08/2026 13:13 |
| AutoFleet | allianz | 2.546 | 47 | 19/08/2026 16:43 |
| AutoFleet | porto | 2.506 | 99 | 11/08/2026 15:37 |
| Resulta | porto | 2.004 | 38 | 18/07/2026 15:12 |
| AutoFleet | hdi | 1.768 | 28 | 29/07/2026 16:50 |
| Resulta | hdi | 1.206 | 15 | 21/07/2026 08:31 |
| Resulta | yelum | 1.056 | 18 | 18/07/2026 11:37 |
| AutoFleet | azul | 829 | 19 | 28/07/2026 16:21 |
| AutoFleet | bradesco | 477 | 22 | 23/07/2026 14:08 |
| AutoFleet | zurich | 458 | 12 | **21/08/2026 11:47** |
| Resulta | tokio | 276 | 22 | 11/08/2026 12:00 |
| AutoFleet | alfa | 264 | 9 | 15/07/2026 14:04 |
| AutoFleet | mapfre | 224 | 12 | **21/08/2026 10:04** |
| Resulta | zurich | 188 | 2 | 06/03/2026 12:22 |
| AutoFleet | tokio | 133 | 24 | 20/08/2026 16:00 |

**Total: 28.092 eventos · 542 sessões · 16 pares.**

### 10.2 Demanda por serviço — a ordem do trabalho da SPEC-084

Sessões em que o serviço aparece, somando as duas corretoras:

```
chaveiro ............ 213      eletrodoméstico ..... 105
guincho ............. 205      pneu ................ 105
eletricista ......... 176      mecânico ............  91
encanador ........... 152      vidros ..............  79
bateria ............. 113
```

Por seguradora (as três maiores de cada serviço):

| serviço | 1º | 2º | 3º |
|---|---|---|---|
| guincho | yelum 55 | allianz 37 | porto 35 |
| chaveiro | allianz 82 | yelum 37 | porto 30 |
| eletricista | allianz 94 | yelum 39 | hdi 19 |
| encanador | allianz 70 | yelum 33 | porto 24 |
| bateria | allianz 24 | porto 23 | yelum 22 |
| pneu | yelum 24 | allianz 23 | hdi 15 |
| mecânico | yelum 38 | allianz 27 | hdi 11 |
| eletrodoméstico | allianz 58 | porto 21 | zurich 10 |
| vidros | porto 29 | azul 16 | zurich 10 |

### 10.3 🔴 O serviço que funciona e está desligado

📊 **Socorro mecânico**: 6 sessões chegaram ao protocolo, **2 delas ao vivo** (yelum 07/08 e 17/08). E `subservice_supported()` devolve `False` → o caso vira handoff.

**Estamos recusando um serviço que já sabemos fazer.** É o item de maior retorno da SPEC-084.

### 10.4 Serviços no menu real da URA sem subserviço no código

| seguradora | ramo | serviço no menu | evidência |
|---|---|---|---|
| yelum | residencial | **Ar condicionado** | está no menu real: *"Encanador / Desentupimento / Eletricista / Chaveiro / Linha branca / Ar condicionado"* |
| hdi, porto, allianz | residencial | Ar condicionado | idem |
| porto | residencial | chuveiro, chaveiro, desentupimento | no menu, sem subserviço |
| bradesco, tokio | auto | vidros | no menu, sem subserviço |
| porto | auto | "Técnico", "Táxi" | no menu, sem subserviço |

### 10.5 Os três defeitos de âncora já corrigidos (`7af5c3c`)

Registrados aqui porque a SPEC-084 vai procurar o **mesmo padrão** nas outras rotas:

1. **Âncora com frase que não existe.** Conferir toda âncora contra o acervo: `select count(*) from observed_events where text ~* '<ancora>'`. Zero = âncora morta.
2. **Duas famílias da mesma seguradora com listas diferentes.** Conferir `finalize_anchors`, `handoff_triggers` e `capture_anchors` entre auto e residencial da mesma seguradora. Divergência sem motivo escrito = defeito.
3. **Declaração que o motor não lê.** Conferir toda chave de `capture_anchors` contra `extract_capture_anchors`. Declarada e não lida = furo silencioso.

### 10.6 As sessões da régua, para o replay

| sessão | data | protocolo | eventos |
|---|---|---|---|
| `8ad1d251` | 22/09/2025 | sim | — |
| `b2bf40e7` | 30/12/2025 | **51022010** | 50 únicos (28 telas + 22 respostas) |
| `7ac3c101` | **19/08/2026** | **52955490** | 29 telas — é a validada |

---

## 11. RELATÓRIO FINAL

Usar `docs/canon/reports/SPEC-EXECUTION-REPORT-TEMPLATE.md`. Obrigatórios:

- commit inicial e final
- a saída **real** de `medir_rota.py` para a régua (o gate do Bloco C)
- a saída **real** do replay da régua **e** do chaveiro (a linha de controle)
- a saída real de cada teste novo, com a mutação e o vermelho que ela produziu
- quantas linhas o gerador de corpus recusou por PII, por seguradora
- o `INVENTARIO-DE-ROTAS.md` gerado
- declaração de que **nenhum corredor foi alterado** nesta SPEC
- o que ficou de fora e por quê → `PENDENCIAS.md`
