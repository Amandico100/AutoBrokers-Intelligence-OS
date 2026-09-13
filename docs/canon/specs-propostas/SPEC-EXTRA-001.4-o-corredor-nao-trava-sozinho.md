# SPEC-EXTRA-001.4 — O CORREDOR NÃO TRAVA SOZINHO
## Menu numerado nunca recebe palavra · "opção inválida" é reparada pelo motor · humano na URA, dos dois lados

**Produto:** AutoBrokers Intelligence OS.
**Status:** PROPOSTA PARA CONVERSÃO, AQUECIMENTO E EXECUÇÃO — não é SPEC canônica aprovada nem implementação realizada.
**Versão:** 1.0 · **Data:** 13/09/2026.
**Baseline medida nesta redação:** worktree `AutoBrokers-FIX`, branch `docs/diagnostico-pilotos-0912`, HEAD `a0bb5fe` (`git rev-parse HEAD`, 13/09/2026). Todo `arquivo:linha` deste documento foi reaberto hoje nesta revisão; o BLOCO 0 remede.
**Origem:** `docs/canon/DIAGNOSTICO-PILOTOS-E-PLANO-EXTRA-2026-09-12.md` §1.6 (o defeito com causa), §3 bloco EXTRA-001.4 (v1, da manhã), §11 **inteiro** (laudo I7: o humano da seguradora na URA) e §11.4 (a medição que fecha a D-PILOTO-10).
**Branch sugerida:** `feat/spec-extra-001-4-corredor-nao-trava`.
**Destino desta proposta:** `docs/canon/specs-propostas/SPEC-EXTRA-001.4-o-corredor-nao-trava-sozinho.md`.
**SPEC definitiva a criar pelo executor:** `docs/canon/specs/SPEC-EXTRA-001.4-o-corredor-nao-trava-sozinho.md`.
**Research Pack:** `SPEC-EXTRA-001.4-o-corredor-nao-trava-sozinho-RESEARCH-PACK.md` (mesma pasta).
**Relatório a criar durante a execução:** `docs/canon/reports/SPEC-EXTRA-001.4-EXECUTION-REPORT.md`.
**Protocolo:** AAA v11.2 + OPÇÃO B. Marcha **CRÍTICO, 3 juízes + red team**, fixada pelo diagnóstico §8 e pela D-PILOTO-14.
**Pendências absorvidas:** P-PILOTO-05, P-PILOTO-06.

---

## 0. Resultado e motivo

> Um acionamento que chega a um menu numerado responde com o **número**. Se a URA recusar, o motor **conserta sozinho**, lendo as opções que a própria tela ofereceu, antes de pedir ajuda a alguém. Se a atendente da corretora digitar à mão, o robô **espera 60 s em silêncio** em vez de digitar por cima dela. E se um humano **da seguradora** se apresentar — mesmo catorze minutos depois de a sessão ter travado — o caso é retomado, o resumo sai, e o segurado recebe protocolo em vez de silêncio.

### 0.1 O que aconteceu, e por que isto é CRÍTICO

📊 Reconstrução da sessão Allianz de 10/09 (`observed_events`, sessão `432614de…`, diagnóstico §1.6 e §11.2):

```
17:12 e 17:18   o corredor respondeu "residência" ao menu
                "1 Residencial · 2 Condomínio · 3 Empresarial"        ← duas vezes
17:14:19        o Sentinela esgotou as 2 tentativas  →  needs_human
17:17:21        a URA encerrou por inatividade (253 s de silêncio)
17:18:12        a SAIONARA digitou "1" à mão. O Cérebro nunca digitou
17:18:14 → :16  o corredor digitou de novo a MESMA tecla que ela acabou de digitar
17:19:30        a URA transferiu ao especialista  →  human_phase
17:21:35        travou em `complemento_referencia`  →  needs_human de novo
17:35:40        a VIVIAN, da Allianz, se apresentou.  ZERO eventos do motor
17:38:18        a URA encerrou "por falta de contato"
18:09 · 18:19 · 18:29   3 alertas ao grupo sobre um caso que a seguradora já tinha fechado
```

**Nenhum destes é um defeito de inteligência.** São cinco defeitos de máquina de estado, cada um com uma linha:

| # | o defeito | a linha, conferida em 13/09 |
|---|---|---|
| 1 | um slot `*_opcao` que ninguém converte em dígito | `corridor_playbooks.py:370-375` (`reply: "{qual_seguro_opcao}"`) × `insurer_dispatch_service.py:394` (`_derivar_teclas_do_caso`, que deriva 23 slots e **não este**) |
| 2 | "opção inválida" não tem reparo: só o Sentinela, e ele gasta 2 tentativas de sessão | `dispatch_watchdog.py:38` (`MAX_SENTINELA_ATTEMPTS = 2`), `:332-336`, `:375/384/389/419` |
| 3 | o humano da corretora não cala o robô — só é **creditado** por ele | `dispatch_router.py:2687-2765` (`note_manual_outbound`): 3 escritas, **nenhum bloqueio** |
| 4 | `needs_human` fecha as três portas de uma vez | `insurer_dispatch_service.py:2909` (só `ura → human_phase`) · `dispatch_router.py:2923` (exige `human_phase`) · `dispatch_watchdog.py:49,73-74` (`needs_human` é terminal: `return None` seco) |
| 5 | a URA encerrou e o produto não soube | regex `insurer_closed` em `insurer_dispatch_service.py:2544-2553` não cobre *"Por falta de contato, estou encerrando"* |

📊 **E o defeito 1 é muito maior do que o diagnóstico viu.** Medido hoje por AST sobre os 805 passos dos 14 corredores: **52 slots `*_opcao` são exigidos por algum passo · 23 são derivados · 29 não têm derivação nenhuma.** `qual_seguro_opcao` é um dos 29. (Comando e lista completa no RESEARCH-PACK §2.1.)

### 0.1.1 🔴 TRÊS ACHADOS DE HOJE QUE MUDAM A ORDEM DOS BLOCOS

Medidos em 13/09 sobre `backend/tests/corpus/telas_reais/` (16 arquivos, 📊 4.279 telas, 195 sessões):

```
🔴 A SESSÃO DE 10/09 NÃO ESTÁ NO CORPUS.
   📊 grep -c '2026-09' backend/tests/corpus/telas_reais/*.jsonl  →  0 nos 16
   📊 wa_timestamp máximo do acervo local: 2026-08-21T12:50:30+00:00
   É o P-PILOTO-06 em pessoa. CONSEQUÊNCIA: o gate "replay do acervo Allianz 10/09"
   NÃO PODE RODAR até o corpus ser regenerado. Por isso a regeneração deixou de ser
   o último bloco e virou BLOCO 0-bis, pré-requisito de A, B e D (§4.1).

🔴 "POR FALTA DE CONTATO, ESTOU ENCERRANDO" NÃO EXISTE NESSA REDAÇÃO.
   📊 grep -ic "falta de contato" *.jsonl  →  0 nos 16
   📊 grep -ic "estou encerrando" *.jsonl  →  3, só em bradesco-auto
   E a redação real é  "estou encerrando este atendimento por falta de interaç…"
   ⚠️ que a regex ATUAL JÁ CASA (`encerrad[ao] por (?:inatividade|falta de intera)`,
   insurer_dispatch_service.py:2548). A frase de setembro que o diagnóstico mediu
   está em `observed_events`, NÃO no corpus — e sai de uma consulta SQL, não de um grep.

🔴 "ISSO PODE LEVAR ALGUNS INSTANTES" NÃO EXISTE EM NENHUMA REDAÇÃO.
   📊 grep -ic "instantes" *.jsonl  →  8, e nenhuma é essa frase.
   As reais: "aguarde alguns instantes" (hdi, 1) · "em instantes, um de nossos anali…"
   (yelum, 1) · e 🔴 "podem aparecer depois de alguns instantes" (porto, 6) — que NÃO
   é transferência e viraria falso positivo.
   ⛔ A âncora não se escreve a partir da frase do enunciado. Ela sai da tabela MEDIDA
   (`zonas_do_acervo.FRONTEIRAS` / `AVISO_DE_ESPERA`), §8.1.
```

✅ **O que se confirmou, e vale como alvo:** *"Vou transferir seu caso para um especialista"* existe **literal, 42 vezes** (allianz-residencial 31, allianz-auto 11); e o menu das três opções existe **16 vezes** (15 sessões na allianz-residencial + 1 na allianz-auto) — mas **com uma redação que importa**:

```
Qual seguro deseja utilizar?

*1 - Residencial:* Para sua casa ou apartamento individual
*2 - Condomínio:* Para áreas comuns e estrutura do condomínio
*3 - Empresarial:* Para proteger seu negócio
```

⚠️ **O asterisco do negrito é o detalhe que decide o bloco A** — e a prova de que ele importa está no próprio passo. A âncora dele, conferida hoje em `corridor_playbooks.py:371-372`, é:

```python
"anchor": r"qual seguro deseja utilizar\?[\s\S]{0,60}"
          r"\*?1\s*-\s*resid[êe]ncial",      # ← 🔴 o `\*?` está ali de propósito
```

🔴 **Quem escreveu o passo JÁ SABIA do asterisco e o tolerou na âncora. O parser do Atlas não o tolera:** `cartographer._NUMERADA` (`:221`) é `(?:^|\n)\s*(\d{1,2})\s*[-–.)\]]\s*([^\n|]{2,80})` — exige o dígito logo depois da quebra de linha, e em `*1 - Residencial:*` há um `*` **antes** dele.

Previsão: no texto **cru** o parser devolve **zero** opções; depois do `_norm` (que tira o `*`), **três**. É a armadilha do CLAUDE.md §9.4, palavra por palavra — *"medido em texto CRU, aplicado em texto NORMALIZADO"* — o mesmo defeito que fez `\*servi[çc]o\*?:` cair de 112 sessões para ZERO na SPEC-083. **Medir antes de usar** é item do BLOCO 0 e é gate (GA-3).

### 0.2 Decisões do Founder já incorporadas — são lei, não se reabrem

| ID | o que governa esta SPEC |
|---|---|
| **D-PILOTO-05** | Coleta dirigida: percorrer a URA **até a tela de confirmação e recusar**. Nunca confirmar chamado sem demanda real. É o único canário vivo autorizado aqui |
| **D-PILOTO-08** | Numeração **EXTRA-001.4** dentro da família; nada renumera |
| **D-PILOTO-10** | Humano da corretora na URA: **opção C — pausa de 60 s**, renovada automaticamente a cada envio real à seguradora, **máximo 2 renovações sem saída**; `AGENTE` retoma já, `EU CUIDO` tira o agente do acionamento. 📊 O valor saiu medido contra 56 encerramentos reais (§11.4 do diagnóstico): 60 s = nota 92 · 90 s = 74 · 120 s = 41 |
| **D-PILOTO-14** | Alta qualidade sem ser exorbitante: AAA opção B, **≤ 12 guardas novos**, bateria sobre o **motor** e o **acervo real** |
| **D-PILOTO-20** | Esta proposta nasce no chat do diagnóstico; a **execução é em chat novo**, sob AAA opção B, com a marcha do §8 do diagnóstico |

⚠️ **Uma correção de copy, registrada.** O diagnóstico §3 (bloco 001.4, versão da manhã) escreve *"assumo de volta em 90 s"* na mensagem ao grupo. A **D-PILOTO-10 e o §11.4 dizem 60 s**, e a segunda leitura vence (cabeçalho do diagnóstico). **Toda copy desta SPEC usa 60 s.** O 90 s do §3 é texto vencido.

### 0.3 🔴 EXECUTION CARD proposto — a conta, a medir no BLOCO 0

```text
OUTCOME .............. menu numerado nunca recebe palavra; "opção inválida" é reparada pelo motor;
                       humano da corretora coordena em vez de duplicar; humano da seguradora que se
                       apresenta é atendido mesmo com a sessão travada
RISCO ................ 8   alcance SEGURADO 3 · reversibilidade "saiu do prédio" 3 (mensagem à URA
                           da seguradora, acionamento real) · frequência TODO atendimento 2
SUPERFÍCIE ........... 2   vários comportamentos + peças novas (reparo, pausa, reentrada, pergunta
                           ao segurado) — os lugares são listáveis e estão listados em §3.2.
                           🔴 se o BLOCO 0 achar um gatilho de grupo fora da lista das nove, vira 3
PISO APLICADO ........ §3.2 — "qualquer coisa que ENVIE". Piso CRÍTICO independente da conta,
                       e a conta também dá CRÍTICO (RISCO 8)
NÍVEL ................ CRÍTICO — opção B · 3 lentes + red team + juiz fresco (§6.1)
UNIDADES ............. 6   0-bis acervo e linha de base (PRÉ-REQUISITO) · A regra B (tecla) ·
                           B regra A (reparo) · C humano da corretora · D humano da seguradora ·
                           E riscos adjacentes e higiene da bateria
COESÃO ............... A+B+D compartilham o arquivo-hub `insurer_dispatch_service.py`;
                       C+D compartilham `dispatch_router.py` e `dispatch_watchdog.py`.
                       🔴 UM dono para o motor, integração SERIAL na ordem A → B → D → C.
                       🔴 0-bis vem ANTES de todos: sem corpus de setembro, os gates de
                       A, B e D não têm sobre o que rodar (§0.1.1). E é disjunto e paralelo
PARALELISMO REAL ..... 2 escritores: o motor (um só) e o acervo/régua. NUNCA dois em `insurer_dispatch_service.py`
TIME ................. investigador+pesquisador (um agente) · aquecimento · desenhista · builder do
                       motor · builder do acervo · integrador (5 unidades) · 3 juízes · red team ·
                       juiz fresco que confirma E audita o dado
REFERÊNCIA ........... interna: `backend/scripts/medir_rota.py --com-espelho` (§7.1 do protocolo) ·
                       `backend/tests/corpus/telas_reais/` · rota de referência `allianz/auto/guincho`
                       externa: as cinco de §16 (SCXML · XState · Step Functions · gen_statem · VoiceXML)
GATES ................ G0 (BLOCO 0) · G0-bis (corpus de setembro + linha de base commitada) ·
                       GA · GB · GC · GD · GE · GR (régua sem regressão) · GT (dois tenants) ·
                       GC1 (canário da coleta dirigida)
O ELO ................ o Cérebro não digitou "1" PORQUE o slot nunca virou tecla → medi o slot (1),
                       medi a ausência de derivação (2), e medi que a ausência CHEGA na tela
                       (`reply: "{qual_seguro_opcao}"` interpolado cru, `corridor_playbooks.py:373`)
FAIXA DE RELÓGIO ..... 💭 8–11 h (diagnóstico §12.1). Faixa, nunca promessa (§9.2 do protocolo)
ORÇAMENTO ............ CRÍTICO ≤ 2,5 M tokens de subagentes. Estourou → menos LENTES, nunca menos MUTAÇÃO
```

### 0.4 O que é BLOCKER nesta SPEC, pelo teste do produto (§2 do protocolo)

```
BLOCKER  — muda um byte do que chega ao SEGURADO ou à SEGURADORA:
  · tecla de menu que sai como palavra (bloco A)
  · reparo de "opção inválida" (bloco B)
  · robô digitando por cima da atendente (bloco C)
  · needs_human surdo ao humano da seguradora (bloco D)
  · `insurer_closed` que não reconhece o encerramento da Allianz (bloco D)
  · o passo morto do `complemento` da porto-auto (bloco E)

PENDÊNCIA — registra e segue:
  · schema do formulário nativo Porto/Azul (P-PILOTO-05, depende de acionamento real 🧑)
  · os 5 pares homônimos da hdi-residencial que NÃO mudam resposta (medir um a um; só os que
    mudam resposta são blocker)
  · observabilidade do Vigia (`agente.vigia`) além da linha durável exigida no bloco D
```

---

## 1. AUTORIZAÇÃO DE TESTES — a fronteira obrigatória

### 1.1 Allowlist explícita e privada

| Alias | Número | Uso nesta SPEC |
|---|---|---|
| **TESTE-A** | `[TESTE-A · allowlist privada]` | o segurado do canário; é quem pede o acionamento e quem responde à pergunta do bloco D |
| **TESTE-B** | `[TESTE-B · allowlist privada]` | a "atendente da corretora" do canário do bloco C e o destino de grupo de teste |

⛔ **Não commitar, não publicar, não colocar em fixture permanente, log, print ou dossiê.** Nas evidências, sempre os aliases. A autorização acompanha o **telefone efetivo**, nunca o nome do tenant, da instância ou da conexão.

### 1.2 O que está autorizado

- Implementar e executar sob AAA, com as permissões vigentes do projeto.
- **Replay do acervo pelo motor**, à vontade: é leitura de `observed_events`/corpus e execução de funções puras. Não envia nada.
- **Canário vivo da coleta dirigida (D-PILOTO-05):** percorrer a URA de uma seguradora **até a tela de confirmação e recusar**, com TESTE-A como segurado. É o único caminho que toca uma seguradora real.
- Consultas SELECT ao banco de produção, **só contagens e estruturas**, sem conteúdo de mensagem.

### 1.3 O que permanece proibido

1. **Confirmar um chamado.** A coleta dirigida vai até a confirmação e **recusa** (D-PILOTO-05). Passar disso despacha prestador real.
2. Usar número operacional da Resulta ou da AutoFleet como remetente, mesmo para enviar ao Founder.
3. Falar com segurado, seguradora, atendente, grupo ou contato fora da allowlist — inclusive por fallback, alerta, cutucada, dossiê, fila e retry. **A cutucada e o dossiê do Vigia são saída externa**: o canário precisa provar a trava antes de ligar o Vigia sobre uma sessão viva.
4. Ligar atendimento, dispatch ou agente globalmente num tenant operacional para o canário funcionar.
5. Alterar o corpus para o teste passar. O texto da tela vem do acervo (CLAUDE.md §9.4).
6. Exercitar o bloco C escrevendo no lugar da atendente numa conversa real com seguradora.

### 1.4 Verificação imediatamente antes de cada efeito

Ambiente · tenant · run/sessão de canário · conexão fixada · identidade real do remetente · **telefone da seguradora de destino** · janela vigente · ator/rotina autorizados · tipo de operação permitido. Se a identidade não puder ser confirmada: **não envia**, e não escolhe outra conexão sozinho.

🔴 **Uma trava específica deste corredor:** o alvo de um envio do dispatch é o **telefone da URA da seguradora**, não um cliente. A allowlist de canário precisa cobrir os dois lados — `insurer_phone` permitido **e** `user_phone` na allowlist — porque um `send_to_client` do bloco D (a pergunta ao segurado) sai pelo canal do cliente.

### 1.5 Canal ausente ou ação física necessária

Continuar código, replay, gates e preparação. Deixar para o Founder só a ação física indispensável (parear um número de teste, abrir a conversa com a URA). **Ausência de canário não vira aprovação de produção**; o gate fica declarado como não comprovado.

---

## 2. Escopo completo e exclusões deliberadas

### Obrigatório nesta SPEC

1. **Regra B** — nenhum slot `*_opcao` chega cru à URA. Derivação obrigatória palavra → dígito (com `qual_seguro_opcao` primeiro), **rede de segurança em tempo de execução lendo a tela real**, e guarda **por passo** que fica vermelho para slot sem derivação.
2. **Regra A** — reparo determinístico de "opção inválida / não entendi", antes do Sentinela, **uma vez por tela**, sem consumir tentativa; o Cérebro passa a receber `ultima_resposta_recusada` e `tela_com_menu_pendente`; **tentativas contadas por tela**, não por sessão.
3. **Humano da corretora na URA** — opção C: pausa de 60 s renovável (máx. 2 renovações), uma mensagem ao grupo, `AGENTE` e `EU CUIDO`, e **nenhum gatilho de grupo enquanto o humano está lá**.
4. **Humano da seguradora na URA** — âncora **positiva** de entrada na fase humana; **`needs_human` reentra em `human_phase`**; **perguntar ao segurado e voltar**; **dois relógios** (fila × humano sumido); `insurer_closed` reconhece o encerramento da Allianz; `registrar_ato_do_agente` **passa a gravar**.
5. **Riscos adjacentes e acervo** — `azul-auto/menu_atendimento`; `complemento` homônimo em porto-auto; regenerar corpus, régua, inventário e roteiro (P-PILOTO-06); tratar P-PILOTO-05 com a coleta dirigida.

### Fora desta SPEC, sem empobrecer o outcome

| Frente | por que não entra | gatilho de retorno |
|---|---|---|
| Reescrever as âncoras dos 14 corredores | não é o defeito medido: 📊 **zero constantes** enviam palavra onde a tela pede número (diagnóstico §1.6). O defeito está nos **slots** | uma rota nova, ou a régua acusando queda |
| Fábrica de rotas / Atlas / `tela_cega` com leitor | SPEC-084 e SPEC-087 são donas; aqui só se **consome** o que elas já produzem | P-264 (a `tela_cega` sem leitor) na SPEC que fechar o leitor |
| Grupo de suporte: modelos de dossiê, números da casa, resumo das 19h | é a **EXTRA-001.3** inteira. Aqui só se **cala** o grupo durante a pausa e se acrescenta uma linha de retomada | 001.3 executa depois/junto |
| Rajadas, buffer, janela adaptativa, identidade do agente | é a **EXTRA-001.2** | 001.2 |
| Portal de vidros, cobrança, apólice | 001.10, 001.6, 001.1 | — |
| Schema do formulário nativo de Porto e Azul | 🧑 depende de um acionamento real observado (P-PILOTO-05) | o primeiro acionamento real dessas duas; a coleta dirigida desta SPEC **produz as telas**, não o desfecho |

⚠️ **Escopo não se reduz sem decisão do Founder (CLAUDE.md §11, D5).** Corte sugerido vira proposta escrita em `CHANGE-ADDENDA.md`, nunca execução silenciosa.

---

## 3. Autoridades preservadas e arquitetura — nenhum motor paralelo

### 3.1 🔴 O que já existe e é REAPROVEITADO — a lista, por arquivo

Esta SPEC **não cria** runtime, parser, scheduler, watchdog, fila ou registro de eventos. Cada peça nova pendura numa autoridade existente:

| o que a SPEC precisa | o que JÁ EXISTE, e onde | o que muda |
|---|---|---|
| ler um **menu numerado** e casar rótulo → dígito | 🔴 **`backend/app/services/cartographer.py:221`** (`_NUMERADA = r"(?:^\|\n)\s*(\d{1,2})\s*[-–.)\]]\s*([^\n\|]{2,80})"`), `parse_options()` `:357`, `numero_da_opcao()` `:587`, `classify_screen()` `:593`; casamento aproximado rótulo↔opção em `app/services/atlas/weaver.py:143-161` | 📊 `grep -n "cartographer" dispatch_router.py insurer_dispatch_service.py` = **0**. O parser existe e **o corredor nunca o importou**. A SPEC **liga** os dois. Não escreve parser novo |
| **âncora positiva** de transferência para humano, por seguradora | 🔴 **`backend/scripts/zonas_do_acervo.py:56`** (`FRONTEIRAS`, 10 seguradoras, cada padrão com a contagem de sessões medida), `:216` (`APRESENTACAO_HUMANA`), `:335` (`APRESENTACAO_DO_ROBO`, o controle negativo), `:327` (`AVISO_DE_ESPERA`), `:587` (`guarda_de_completude_da_fronteira`, que **já ficou vermelho** em 4 seguradoras) | as tabelas **mudam de casa** para um módulo que o produto importa; `scripts/` passa a importar de lá. Zero duplicação, zero tabela nova escrita à mão |
| **pausa** que o Vigia respeita | 🔴 `dispatch_router.py:86` (`_SILENCIO_S = 60`), `:2986-2988` (escrita de `silencio_deliberado_ate`), `dispatch_watchdog.py:106-116` (o Vigia **já** honra o campo) | quem escreve o campo passa a ser também o caminho do humano (`note_manual_outbound`). O mecanismo é o mesmo |
| marcar que **um humano assumiu** | `dispatch_router.py:2687-2765` (`note_manual_outbound`), `:2768-2800` (`_registrar_assuncao_humana`), evento `travamento.assumido`, `ASSUMIDO_POR_HUMANO` `:2684` | ganha **efeito** (hoje só credita) |
| **contagem por passo** | `insurer_dispatch_service.py:2634` (`session["step_counts"]`, usado por `reply_repeat`) | ganha a irmã `tentativas_por_tela`, com reset na reentrada |
| **registro durável de ato do agente** | `dispatch_router.py:997-1027` (`registrar_ato_do_agente`) e `_evento` `:683-700` → `work_events` | 🔴 **ela É chamada** (`:2967`, `:3057`, `dispatch_watchdog.py:408`). O que falta é descobrir por que **0 linhas** chegam ao banco (hipótese: o `return False` de `:1011-1013` quando `session["work_run_id"]` está vazio) — é medição do BLOCO 0, não reescrita |
| **relógios** do corredor | `dispatch_watchdog.py:31-38` (7 constantes), ciclo de **20 s** (`app/tasks/buffer_processor.py:176-182`) | ganha a distinção fila × humano sumido. Nenhum scheduler novo |
| **espera por resposta** | `work_waits` + `espera_watchdog_check` (`app/tasks/handoff_watchdog.py`, job em `buffer_processor.py:571-577`) e o próprio Vigia, que já varre `dispatch:active:*` a cada 20 s | a pergunta ao segurado usa **o Vigia** (já varre, já tem prazo), e só cria linha em `work_waits` se o BLOCO 0 provar que ela é lida |
| forma da tecla por seguradora | `backend/tests/test_a_tecla_tem_a_forma_da_seguradora.py:78-86` (`convencao_do_corredor`, medida por maioria), `:92-130` (`valores_derivados`, por AST), `:133-138` (`donos`) | o guarda **inverte o laço** (§10 GA-1). `donos()` já existe e já sabe achar o dono de um slot |
| **chamar o motor a partir de um teste ou script** | 🔴 `backend/scripts/regua_motor.py:56-57` — a **camada única** de import (`match_ura_step = CP.match_ura_step`, `extract_capture_anchors = CP.extract_capture_anchors`), mais o leitor paginado de `observed_events` (`:214-254`) | todo guarda novo passa por aqui ou importa o motor direto. ⛔ Nenhum guarda reimplementa regex (CLAUDE.md §9.4; `backend/scripts/detector_do_eixo_e.py:62` é o detector que já existe) |
| **replay de uma sessão pelo motor** | `backend/scripts/replay.py:156` (`replay(rota, …)`), `:106-120` (`carregar_corpus`), classificação RESPONDIDA/NOOP/ORFA_INOCUA/**ORFA_FUNCIONAL**/HANDOFF/CAPTURADA (`:3-20`), filtro por serviço dentro da sessão (`:161-174`) | os replays de gate (Allianz 10/09, Vivian) são **rodadas deste script**, não um replay novo |
| **régua e inventário** | `backend/scripts/medir_rota.py` (641 linhas): `--todas`, `--com-espelho`, `--formato markdown`, `--salvar-linha-de-base`, `--comparar-com` (gate R3, **exit 1** se uma rota perder respondidas, `:386-390`) | ganha a **linha de base commitada** que hoje não existe (§4.1) |

⛔ **Proibido nesta SPEC:** um segundo parser de menu · uma segunda tabela de frases de transferência · um segundo watchdog · uma segunda fila de espera · um segundo registro de eventos · um "modo corredor v2" ao lado do atual (CLAUDE.md §5).

### 3.2 Os lugares que a SPEC toca — a lista que sustenta SUPERFÍCIE 2

```
backend/app/services/insurer_dispatch_service.py     A · B · D   (arquivo-hub, UM dono)
backend/app/services/corridor_playbooks.py           A · D · E
backend/app/services/dispatch_router.py              B · C · D
backend/app/tasks/dispatch_watchdog.py               B · C · D
backend/app/services/cartographer.py                 B   (só importado; não se altera o parser)
backend/scripts/zonas_do_acervo.py                   D · E   (as tabelas mudam de casa)
backend/scripts/medir_rota.py · gerar_corpus_de_telas.py · roteiro_de_coleta.py   E
backend/tests/…                                      todos
```

⚠️ `dispatch_watchdog.py` mora em **`backend/app/tasks/`**. O diagnóstico escreve `app/services/dispatch_watchdog.py` — **esse arquivo não existe**; os números de linha citados batem com `app/tasks/`. Correção registrada.

### 3.3 Multi-tenant (CLAUDE.md §7)

Nada nesta SPEC cria tabela ou rota nova de leitura. Mesmo assim:

- Toda função nova recebe `company_id` **explícito**, como as vizinhas (`note_manual_outbound(company_id, insurer_phone, …)`, `registrar_ato_do_agente(company_id, session, …)`).
- A sessão do corredor é carregada por `load_active_dispatch(company_id, insurer_phone)` — a chave já é composta. **Nenhuma função nova pode carregar sessão só por `insurer_phone`**: duas corretoras podem falar com a mesma URA.
- A pausa, a espera pelo segurado e o `menu_pendente` vivem **dentro da sessão** (Redis `dispatch:active:{company_id}:{insurer_phone}`), então herdam o escopo.
- Prova de isolamento: duas corretoras, mesma seguradora, mesma tela, uma em pausa e a outra não — a pausa de uma **não** cala a outra, e o dossiê de uma não vai para o grupo da outra. É o gate GT de §10.

---

## 4. BLOCO 0 — converter medindo, antes de qualquer linha de produto

> Este documento envelhece. O número do executor vence o número daqui (§5① do protocolo).

1. **Preflight**, na ordem do CLAUDE.md §2: `git rev-list --count HEAD..origin/main` (tem de ser 0) · `git rev-list --count origin/main..HEAD` · `git branch --show-current` · `git rev-parse HEAD` · `git status --short`.
2. **Remedir as cinco linhas da §0.1** e as da §3.1, uma a uma. Divergiu? corrige a SPEC definitiva e anota na matriz premissa → observação → comando → decisão.
2-bis. 🔴 **`grep -rn "o_grupo_pode_saber" backend/`** — a guarda única da EXTRA-001.3. **Existe?** então esta SPEC **chama** e acrescenta a causa `pausa_humana`. **Não existe?** então esta SPEC **cria** a função, com a assinatura da §5 da 001.3, e a 001.3 depois a chama. ⛔ Em nenhuma hipótese se escreve a segunda (§7.3).
3. **Recontar os órfãos da derivação** com o comando do RESEARCH-PACK §2.1 (AST). 📊 Hoje: 52 usados · 23 derivados · **29 órfãos**. Se o número mudou, ele manda.
4. 🔴 **Descobrir por que `registrar_ato_do_agente` grava 0 linhas**, já que tem 3 chamadores. O ELO (§0.3 do protocolo): medi que a função existe · medi que é chamada · **medi que a chamada CHEGA ao INSERT?** Comando: `SELECT event_type, count(*) FROM work_events WHERE event_type LIKE 'agente.%' GROUP BY 1;` e, no código, ler de `dispatch_router.py:997` até `:1027` procurando o `return False` de `:1011-1013`. Sem esta resposta o bloco D não começa.
5. 🔴 **Medir o dialeto do normalizador** (CLAUDE.md §9.4). `zonas_do_acervo.norm_para_classificar` (`:463`) × `insurer_dispatch_service._norm_text` (`:2939-2949`) × `corridor_playbooks._norm`. Rodar **os mesmos padrões de `FRONTEIRAS` nas três normalizações, sobre o mesmo acervo**, e escrever as três contagens lado a lado. **Um padrão medido com um normalizador e aplicado com outro é um padrão sobre outra coisa.** Se divergirem, o motor adota o normalizador que produziu o número.
6. **Medir os dois relógios** com a consulta do §11.4 do diagnóstico reproduzida: tempo até a primeira fala do humano por seguradora (📊 Allianz 114 transferências, 50 atendentes: 59 % < 10 s · mediana 3 s · p90 10,5 min · máx 49 min) e tempo do último evento até o encerramento por inatividade (📊 56 encerramentos; Porto 95 s e Allianz 103 s são os piores). **Os valores de `FILA_ALERTA_S`, do prazo da pergunta ao segurado e do intervalo de holding saem daqui, medidos, não chutados.**
7. 🔴 **Contar no BANCO, não no corpus**, as frases que viram âncora — porque o corpus local termina em 21/08 (§0.1.1). Em `observed_events`, por `insurer_key`, **só contagens**: a frase de encerramento de setembro (📊 diagnóstico: 9 mensagens em 6 sessões), as frases de recusa de menu do bloco B, e cada padrão de `FRONTEIRAS`. **Cada número com a consulta ao lado.** ⚠️ Leitura **paginada** obrigatória: o PostgREST corta em 1000 e 📊 o acervo tem 28.096 eventos (`regua_motor.py:222-226`).
8. 🔴 **Medir o parser sobre o texto REAL do menu**, nas duas formas — cru e normalizado: `cartographer.parse_options("*1 - Residencial:* …")` devolve quantas opções? E depois de `corridor_playbooks._norm`? 📊 A previsão desta proposta é **0 e 3**. Se der outra coisa, o número do executor vence, e a camada 1 do bloco A é desenhada em cima do que ele mediu.
9. 🔴 **Triagem NOMINAL da bateria vermelha de hoje.** Medido em 13/09, de dentro de `backend/`, com `PYTHONIOENCODING=utf-8`:

   ```
   test_spec017_dispatch.py                                exit 1   IndexError em :158,
                                                                    depois de "[X] P4: analista
                                                                    humano -> resumo mastigado ...:
                                                                    preparing"
   test_spec031_auto_dispatch.py                           exit 1   IndexError em :134, depois de
                                                                    "[X] dry-run porto ok: {'ok':
                                                                    False, 'missing_slots':
                                                                    ['local_seguro']}"
   test_o_corredor_conhece_a_tela_que_esta_na_frente.py    exit 1   "VERMELHO - 2 falha(s)"
   test_spec038_sentinela.py                               exit 0
   test_a_regua_nao_tem_furo.py                            exit 0   (71 s: roda mutações)
   ```

   🔴 **Dois dos três vermelhos são testes de dispatch, e o primeiro falha exatamente no caminho "analista humano → resumo mastigado" — que é o BLOCO D desta SPEC.** ⛔ Nenhuma linha de produto é escrita antes de o relatório dizer, por teste: é falha pré-existente (demonstrada na base **e** no head), é regressão de uma das cinco entregas de 08–10/09 que entraram sem SPEC, ou é defeito que esta SPEC vai consertar. **"Pré-existente" não é rótulo coletivo** (§8 do protocolo).
10. **Rodar os guardas atuais** e colar a saída: `python tests/test_a_tecla_tem_a_forma_da_seguradora.py` (📊 hoje: `12 assercoes verdes - 0 vermelhas`, **com o defeito vivo** — é o retrato do problema).
11. **Ler `MIGRATIONS-AUTHORITY.md`** antes de qualquer SQL e medir se `work_events` tem CHECK em `event_type` (o CHECK conhecido é em `actor_type`: `ATORES_VALIDOS` em `dispatch_router.py:680`). Se `event_type` for livre, **não há migration nesta SPEC** — e isso vai escrito.

**GATE B0:** a matriz premissa → observação nova → comando/consulta → decisão · a resposta do item 4 · as três contagens do item 5 · os valores medidos do item 6 · as contagens do banco do item 7 · os dois números do item 8 · **a triagem nominal do item 9**. **Nenhum achado não reproduzido é vendido como incidente confirmado.**

**MUTAÇÃO B0:** o desenhista entrega ao aquecimento duas premissas deliberadamente falsas e assinadas (§5.2 do protocolo). Sugestões em §6 do RESEARCH-PACK.

---

## 4.1 BLOCO 0-bis · O ACERVO E A LINHA DE BASE — pré-requisito de A, B e D

> 🔴 **Este bloco existe porque a medição de hoje derrubou o plano da manhã.** O gate desta SPEC é *"replay do acervo Allianz 10/09"*, e **o acervo local não tem 10/09** (§0.1.1). Sem este bloco, os gates de A, B e D rodam sobre agosto e provam a coisa errada.

```bash
cd backend && export PYTHONIOENCODING=utf-8

# ① o corpus volta a ter o mês do piloto  (P-PILOTO-06)
python scripts/gerar_corpus_de_telas.py --todas --auditar-pii
python tests/test_o_corpus_nao_vaza_pii.py            # o guarda de PII que já existe

# ② a régua roda e a LINHA DE BASE É COMMITADA — hoje não existe nenhuma
python scripts/medir_rota.py --todas --com-espelho --formato markdown   # → INVENTARIO-DE-ROTAS.md
python scripts/medir_rota.py --todas --com-espelho --salvar-linha-de-base docs/canon/reports/LINHA-DE-BASE-DE-ROTAS.json

# ③ o roteiro de coleta, com o denominador novo
python scripts/roteiro_de_coleta.py --markdown
```

⚠️ **Três travas medidas hoje, que custam a rodada inteira se esquecidas:**

```
🔴 rode de dentro de `backend/`. Da raiz, `tem_banco()` não acha `backend/.env` e a
   nota CAI PARECENDO MEDIDA (medir_rota.py:459-481). Confirmado hoje: de dentro, True
🔴 `PYTHONIOENCODING=utf-8`. 📊 Sem ele, "96 verdes / 8 vermelhos" vira "104 verdes /
   0 vermelhos" — e a falha é no `print` de uma seta, não em asserção (run_all.py:18-27)
🔴 📊 934 respostas de botão têm `text` VAZIO no acervo (yelum 370, hdi 254, porto 165,
   bradesco 62, azul 54): o `interactive` guardou só as chaves. A ESCOLHA DO SEGURADO NÃO
   ESTÁ NO BANCO nesses casos (regua_motor.py:230-238). Um replay que a conte como
   "não respondeu" mente. O relatório diz quantas do 10/09 caem nisso
```

**E duas coisas que o corpus regenerado precisa conter, ou o bloco não fechou:**

1. a sessão Allianz de **10/09** (a do `"residência"`), em `allianz-residencial.jsonl`;
2. a frase de encerramento de setembro medida no item 7 do BLOCO 0 — se ela **não** entrar no corpus, a âncora do bloco D não tem como ser guardada offline, e isso vai escrito como limitação, não escondido.

**GATE 0-bis:** (1) `grep -c '2026-09' backend/tests/corpus/telas_reais/*.jsonl` > 0 na allianz; (2) `LINHA-DE-BASE-DE-ROTAS.json` commitado; (3) `INDICE.md` do corpus cobre os **16** arquivos — 📊 hoje cobre **1** (foi sobrescrito por uma geração `--seguradora bradesco`, carimbo 23/08); (4) `medir_rota.py --comparar-com` roda contra a base e sai **0**.

⚠️ **Uma assimetria achada e registrada:** 📊 existem `tokio-residencial.jsonl` e `tokio-condominio.jsonl` (59 telas, 6 sessões) e **`rotas()` não produz nenhuma rota tokio residencial/condomínio** — corpus que a régua nunca mede. É **pendência**, não blocker (não muda byte para o segurado hoje), e entra em `PENDENCIAS.md` com o número novo.

---

## 5. BLOCO A · REGRA B — nenhum slot `*_opcao` chega cru à URA

### 5.1 O defeito, com a linha

```python
# backend/app/services/corridor_playbooks.py:370-375   (allianz-residencial-whatsapp@v1)
{"step": "menu_qual_seguro_tres_opcoes",
 "anchor": r"qual seguro deseja utilizar\?...",
 "reply": "{qual_seguro_opcao}",          # ← interpolado CRU
 "requires": ["qual_seguro_opcao"],
 "fallback_adaptive": True}
```

`qual_seguro_opcao` é **coletado da atendente** (`corridor_playbooks.py:9653` pede *"de que seguro ele fala — o da residência"*; campo da tool em `app/agents/tools/insurer_dispatch_tool.py:310`) e **nunca convertido**. `_derivar_teclas_do_caso` (`insurer_dispatch_service.py:394-1019`, 625 linhas, 23 slots `*_opcao`) não o conhece. A SPEC-083 trocou a constante `"1"` — que mandava condomínio para residencial — por um slot, e **não criou a derivação**.

📊 E não é caso único: **29 slots `*_opcao` exigidos por passos não têm derivação** (lista no RESEARCH-PACK §2.1). Alguns são atenuados por constante no dicionário do subserviço; os demais dependem só da atendente, e **passo sem slot preenchido fica calado** — a família do defeito de 2 min 22 documentada em `insurer_dispatch_service.py:398-403`.

### 5.2 O contrato — duas camadas, e a de baixo é a que salva o piloto

#### Camada 1 (runtime, fail-closed) — `resolver_tecla`

```python
# backend/app/services/insurer_dispatch_service.py
ORIGENS = Literal["subservico", "derivacao", "inline", "menu_lido", "constante"]

class Tecla(TypedDict):
    valor: str            # o que vai para a URA
    origem: ORIGENS       # de onde veio — escrito no transcript e no work_event
    rotulo: str | None    # o rótulo casado, quando origem == "menu_lido"
    motivo: str           # por que ESTE valor está certo (§9.5 do CLAUDE.md)

def resolver_tecla(playbook: dict, step: dict, session: dict,
                   tela: str) -> Tecla | None
```

Regra, na ordem:

```
1. o passo interpola {X_opcao} e o valor está preenchido e JÁ é dígito
        → envia, origem = a que o preencheu
2. o valor está preenchido e NÃO é dígito
   2a. a TELA REAL oferece menu numerado (cartographer.parse_options devolve ≥ 2 opções
       com dígito) e o valor casa, normalizado, o rótulo de UMA opção
        → 🔴 envia o DÍGITO daquele rótulo · origem = "menu_lido" · rotulo = o casado
   2b. a tela oferece menu numerado e o valor casa ZERO ou 2+ rótulos
        → ⛔ NÃO ENVIA. `needs_human` com reason="tecla_ambigua" (2+) ou vai ao
          reparo do bloco B (zero). O dossiê diz o valor, os rótulos e a tela
   2c. a tela NÃO oferece menu numerado (é lista, é texto livre)
        → envia o valor como está. É o caso legítimo da porto (`reply: "Novo serviço"`)
3. o valor está VAZIO
        → ⛔ NÃO ENVIA. `needs_human` com reason="slot_opcao_sem_derivacao", e o
          dossiê nomeia o slot. Hoje o passo fica CALADO: o silêncio vira mensagem
```

🔴 **É esta camada, e só ela, que conserta os 29 órfãos de uma vez** — porque ela não depende de alguém lembrar de escrever a derivação. A camada 2 impede que órfãos novos nasçam.

⚠️ **Duas travas, e as duas são do CLAUDE.md §9.4.**

**(a) O palpite fica desligado.** `parse_options` tem um ramo de "palpite" para listas nuas (`cartographer.py:397+`), documentado em `:232-244` como produtor de invenção. **A camada 1 usa SÓ o ramo `_NUMERADA` (`:221`) e o ramo `Botão N:` da Evolution (`:382`).** Desligado por parâmetro explícito, com guarda (GA-3).

**(b) 🔴 O texto que se dá ao parser é o NORMALIZADO, e isso tem de ser medido, não deduzido.** A tela real da Allianz escreve `*1 - Residencial:*` — com o asterisco do negrito **antes do dígito**. `_NUMERADA` exige `(?:^|\n)\s*(\d{1,2})`, e o `*` quebra a âncora. 📊 Previsão desta proposta: **cru → 0 opções · depois de `_norm` → 3 opções**; o item 8 do BLOCO 0 mede, e o número medido manda.

```
📊 é o mesmo defeito, com outro nome, da execução da SPEC-083:
   "medido em texto CRU, aplicado em texto NORMALIZADO" — `\*servi[çc]o\*?:` caiu de
   112 sessões para ZERO porque o `_norm` tira o `*` (CLAUDE.md §9.4)
🔴 O guarda que fecha a porta: um teste que exija ZERO opções no texto CRU. É assim
   que se descobre que a normalização era o que fazia o parser funcionar.
```

#### Camada 2 (estática) — derivação obrigatória

- `qual_seguro_opcao` ganha derivação em `_derivar_teclas_do_caso`, **primeiro da fila**, no padrão dos vizinhos: lê o texto normalizado do relato, casa `residencia/casa/apartamento` → `"1"`, `condominio` → `"2"`, `empresa/empresarial/comercial/loja/escritorio` → `"3"`, e **default documentado** com o motivo escrito ao lado (a convenção de `:398-403`).
  🔴 **O default aqui é perigoso e precisa de justificativa própria:** esta tecla **decide o ramo da apólice**, não navega. Mandar condomínio para residencial foi o defeito que a SPEC-083 consertou. Portanto: **sem casamento, não há default** — vai para `needs_human` com `reason="ramo_indeterminado"`. É a exceção explícita à regra do default, e ela está registrada aqui porque §9.5 do CLAUDE.md manda: *"uma constante que escolhe entre alternativas de conteúdo precisa dizer por que está certa, escrito ao lado dela"*.
- Os outros 28 órfãos são **classificados** (não necessariamente derivados) numa tabela do relatório: `tem constante no subserviço` · `nasce inline` · `depende da atendente e é aceitável` · `precisa de derivação`. Os que precisarem ganham derivação nesta SPEC; os que não, ficam registrados com o motivo. **A camada 1 cobre todos de qualquer forma.**

### 5.3 Gate A

```bash
cd backend && export PYTHONIOENCODING=utf-8
python tests/test_o_menu_numerado_recebe_numero.py        # 1. o defeito de 10/09, pelo MOTOR,
                                                          #    sobre a tela REAL do acervo
python scripts/…                                          # 2. a lista de órfãos, recontada
                                                          #    (o comando está no RESEARCH-PACK §2.1)
python tests/test_a_tecla_tem_a_forma_da_seguradora.py    # 3. o guarda invertido: VERMELHO no
                                                          #    estado de hoje, verde depois
```

**GATE A:** (1) o passo `menu_qual_seguro_tres_opcoes`, alimentado com o caso real e a tela real, responde **`"1"`**; (2) com o slot vazio, o motor **não envia nada** e devolve `needs_human` com `reason="slot_opcao_sem_derivacao"`; (3) com a tela sem menu numerado, a palavra sai inteira (é a porto, e ela tem de continuar funcionando — **linha de controle**); (4) o guarda por passo acusa os órfãos que sobrarem, com nome.

**MUTAÇÃO A:** trocar o retorno de `resolver_tecla` para o valor cru (`return {"valor": slots[X], "origem": "subservico"}`) → o teste do menu **tem de ficar vermelho com "residência"**. Se ficar verde, o teste não está chamando o motor (CLAUDE.md §9.4).

---

## 6. BLOCO B · REGRA A — o reparo determinístico de "opção inválida"

### 6.1 O defeito, com a linha

Hoje só existe uma saída para uma tela que não anda: o **Sentinela**, em `dispatch_watchdog.py:320` (`_sentinela_recover`), com teto `MAX_SENTINELA_ATTEMPTS = 2` (`:38`).

📊 **E o contador é por SESSÃO, não por tela.** `session["sentinela_attempts"]` é lido em `:332` e `:336`, incrementado em **quatro** pontos (`:375` sem canal · `:384` envio falhou · `:389` sucesso · `:419` "tentativa consumida mesmo sem envio"), e **nunca é zerado**: `grep -rn 'sentinela_attempts.*=.*0|pop("sentinela_attempts"|del .*sentinela_attempts' backend/app/` → **0 resultados**. Duas tentativas gastas na tela A deixam **zero** para a tela B. Em 10/09 as duas foram gastas às 17:14, e o resto da sessão correu sem rede.

E o Cérebro **não sabe que foi recusado**: `build_human_phase_messages` (`insurer_dispatch_service.py:3019`) monta o prompt com os últimos 6 turnos e a orientação do corredor, e **nenhum campo diz "a sua última resposta foi recusada"**.

### 6.2 O contrato

```python
# backend/app/services/insurer_dispatch_service.py

RECUSA_DE_MENU: list[str]   # âncoras MEDIDAS no acervo (BLOCO 0 item 7), não inventadas

def detectar_recusa_de_menu(tela: str) -> bool

class MenuPendente(TypedDict):
    tela_id: str                 # nome do passo + hash do texto normalizado da tela
    opcoes: list[tuple[str, str]]   # [(dígito, rótulo)] — de cartographer.parse_options
    nossa_resposta: str          # o que mandamos
    em: str                      # iso

def reparar_opcao_invalida(session: dict, playbook: dict,
                           tela: str) -> Tecla | None
```

**As quatro condições, todas obrigatórias** (§0.3 do protocolo: a regra é `A E B E C E D`, e cada cláusula se conta separada):

```
① a tela atual casa RECUSA_DE_MENU
② existe session["menu_pendente"] e ele tem ≥ 2 opções com dígito
③ session["menu_pendente"]["nossa_resposta"] NÃO é um dígito
④ session["reparos_por_tela"][tela_id] == 0      ← uma vez por tela, e só uma
```

Satisfeitas: reenvia o **dígito do rótulo mais próximo** entre as opções do menu pendente, com `origem="menu_lido"`, e **não incrementa `sentinela_attempts`**. Falhou o casamento de rótulo: **não inventa dígito**; segue para o Sentinela normalmente.

**Onde roda:** dentro de `handle_insurer_message`, **antes** do caminho de fase humana de `:2909` e antes de qualquer agendamento do Sentinela — porque o reparo é determinístico e o Sentinela é caro (chama o Cérebro). Ordem explícita no código, com comentário, para a próxima pessoa não inverter.

**O Cérebro passa a saber.** `build_human_phase_messages` ganha dois campos no contexto:

```
ultima_resposta_recusada : {"nossa_resposta": str, "tela": str, "em": iso} | None
tela_com_menu_pendente   : [(dígito, rótulo), …] | None
```

💭 Copy da instrução ao modelo (ilustrativa, a final sai do desenhista): *"A sua última resposta (`{nossa_resposta}`) foi recusada por esta tela. As opções que a tela oferece são: 1) … 2) … 3) …. Responda com o número da opção correta para o caso. Não repita a resposta recusada."*

**Tentativas por tela.** `session["tentativas_por_tela"][tela_id]` substitui a leitura de `sentinela_attempts` no portão de `:336`, com dois tetos:

```
MAX_TENTATIVAS_POR_TELA   = 2     # o que o Sentinela gasta numa tela
MAX_TENTATIVAS_NA_SESSAO  = 6     # 💭 teto de segurança — o valor sai medido no BLOCO 0
```

🔴 **Por que o teto de sessão continua existindo:** pelo `gen_statem` do Erlang/OTP (§16), *repetir o mesmo estado não cancela o state timeout* — e é exatamente assim que se evita o laço infinito educado, em que o corredor conserta, tenta, é recusado, reentra na mesma tela e recomeça a contagem para sempre. **Reset por tela, teto por sessão.**

### 6.3 Gate B

**GATE B:** (1) tela de recusa do acervo + menu pendente + nossa resposta em palavra → sai **o dígito**, e `sentinela_attempts` **não muda**; (2) a mesma tela de novo → **não repara duas vezes** (condição ④); (3) duas telas diferentes, cada uma com 2 tentativas → o Sentinela funciona nas duas (hoje não funciona na segunda); (4) recusa **sem** menu numerado na tela → não repara, cai no Sentinela (**linha de controle**: prova que a condição ② tem efeito).

**MUTAÇÃO B:** trocar a contagem por tela pela contagem por sessão → o teste (3) **tem de ficar vermelho**. E desligar a condição ③ (nossa última resposta era dígito) → o motor passa a reenviar o mesmo dígito recusado, e o teste (4) fica vermelho.

---

## 7. BLOCO C · O HUMANO DA CORRETORA NA URA — opção C, 60 s (D-PILOTO-10)

### 7.1 O defeito, com a linha e o relógio

📊 10/09, 17:18:12 a Saionara digitou `"1"`; **17:18:14 e 17:18:16 o corredor digitou de novo**. Numa tela de confirmação, isso confirma duas vezes.

`note_manual_outbound` (`dispatch_router.py:2687-2765`) faz três escritas — transcript com `manual: True` (`:2748-2751`), `destravado_por="humano"` + `assumido_por_humano_em` (`:2760-2762`), e `_registrar_assuncao_humana` (`:2763`, evento `travamento.assumido` com ator `user`, `:2792-2799`) — e **nenhum bloqueio**. 📊 `grep` por `pausa|pause|lease|lock|takeover` em `dispatch_router.py`: nenhum hit é mecanismo de pausa do corredor.

E o Sentinela pode responder por cima dela **30 s depois** (`dispatch_watchdog.py:119-125` → `_sentinela_recover` em `:320`, `URA_UNANSWERED_S = 30`).

### 7.2 Por que 60 s, medido

📊 Acervo inteiro, 56 encerramentos por inatividade (diagnóstico §11.4): silêncio < 60 s → **0 de 56** · < 90 s → **0 de 56** · < 120 s → **2 de 56** (Porto 95 s, Allianz 103 s). O Vigia roda a cada **20 s** (`buffer_processor.py:176-182`), então 90 s viram até 110 s reais e **perdem os dois piores casos**. 60 s deixa 35 s de margem sobre a Porto e 43 s sobre a Allianz, e cabe o Cérebro (💭 ~4 s) mais um ciclo do Vigia. **Nota 92 × 74 × 41.**

### 7.3 O contrato

```python
# backend/app/services/dispatch_router.py
PAUSA_HUMANA_S            = 60     # D-PILOTO-10
PAUSA_HUMANA_MAX_RENOV    = 2      # 120 s no total, sem saída

session["pausa_humana"] = {
    "ate": iso,            # agora + 60 s
    "renovacoes": int,     # 0, 1, 2
    "aberta_em": iso,
    "avisou_grupo": bool,  # a mensagem sai UMA vez por pausa
    "canal": str,
}
```

**Abre** dentro de `note_manual_outbound`, no ramo `foi_humano=True` (`:2748+`), logo depois das marcas que já existem — e escreve **também** `session["silencio_deliberado_ate"]`, que o Vigia **já honra** (`dispatch_watchdog.py:106-116`). Nenhum mecanismo novo.

**Renova** a cada novo `note_manual_outbound(foi_humano=True)` **cujo destino seja a seguradora desta sessão** — porque é esse envio que reinicia o relógio da URA do outro lado (D-PILOTO-10). Renovação sem saída tem teto: na 3ª vez (`renovacoes == 2`), a pausa **não renova**; o corredor retoma sozinho **lendo a tela atual**, e registra `pausa_humana_esgotada`.

⚠️ **`foi_humano=False` é o eco da nossa própria voz** (`dispatch_router.py:2732-2747`, `e_a_nossa_propria_voz`) e **não abre nem renova pausa**. Sem esta cláusula, a resposta do próprio Cérebro voltando como `fromMe` pausaria o corredor contra si mesmo — é a mesma inversão que o painel pegou na SPEC-085 C.1, do outro lado.

**A mensagem ao grupo**, uma vez por pausa (💭 copy ilustrativa; a final sai do desenhista e passa pela régua de língua):

```
👋 Vi que você entrou no atendimento da {seguradora} do {primeiro nome do segurado}.
Eu assumo de volta em 60 segundos.
Responda AGENTE para eu seguir agora · EU CUIDO para eu sair deste acionamento.
```

**As duas palavras**, lidas na entrada do grupo:

| palavra | efeito | estado |
|---|---|---|
| `AGENTE` | fecha a pausa imediatamente e o corredor retoma lendo a tela atual | continua `ura`/`human_phase` |
| `EU CUIDO` | o agente **sai deste acionamento**: sem Sentinela, sem cutucada, sem dossiê novo | `needs_human`, `reason="humano_assumiu"` — 🔴 **e este reason NÃO é reentrável** pelo bloco D |

**Enquanto a pausa está aberta, nenhum gatilho de grupo dispara.**

🔴 **PONTO DE COLISÃO DECLARADO COM A EXTRA-001.3, e o protocolo para resolvê-lo.** A 001.3 escreve a guarda única *"humano já está nesta conversa"*, com o nome `o_grupo_pode_saber`, consultada por **todos** os gatilhos de grupo. É **a mesma guarda** que esta SPEC precisa, chamada de outro lugar. ⛔ Duas implementações = motor paralelo, e **as duas SPECs reprovam**.

```
quem executar PRIMEIRO   → CRIA `o_grupo_pode_saber(company_id, session|conversa) -> bool`,
                           com `session["pausa_humana"]` como uma das causas de "não pode"
quem executar DEPOIS     → CHAMA a que existe, e acrescenta a sua causa
🔴 O BLOCO 0 desta SPEC verifica se a função já existe ANTES de escrever qualquer
   consulta. Se existir, esta SPEC não escreve guarda nenhuma: escreve o CAMPO e a CAUSA.
```

Os nove gatilhos do dispatch, com a linha — **todos passam pela guarda única**:

```
dispatch_router.py:3304   dossiê de handoff
dispatch_router.py:3140   falhou avisar o segurado do encaminhamento
dispatch_router.py:3186   falhou avisar o segurado do protocolo
dispatch_watchdog.py:566  URA calada (120 s)
dispatch_watchdog.py:585  analista humano sumido (1200 s)
dispatch_watchdog.py:593  nunca começou (300 s)
dispatch_watchdog.py:601  deadline da sessão (2700 s)
dispatch_watchdog.py:421  escada do Sentinela esgotada → dossiê
dispatch_watchdog.py:575  cutucada — 🔴 esta vai para a SEGURADORA, não para o grupo;
                          e ela também tem de calar, porque cutucar a URA durante a
                          pausa é o robô falando por cima da atendente
```

⚠️ `espera.vencida` (as 3 mensagens das 18:09/18:19/18:29) **não é do dispatch**: vive em `app/tasks/handoff_watchdog.py:407`, e é da **EXTRA-001.3**. Aqui só se registra o elo: enquanto a pausa está aberta, a conversa **tem humano**, e `o_grupo_pode_saber` precisa enxergar `session["pausa_humana"]` — inclusive para calar a `espera.vencida`, que esta SPEC **não** toca.

### 7.4 Gate C

**GATE C:** (1) `note_manual_outbound(foi_humano=True)` → a pausa abre, e o Sentinela **não responde** nos 60 s seguintes (hoje responde em 30 s); (2) segundo envio humano → renova; terceiro → **não renova**, e o corredor retoma; (3) `AGENTE` fecha a pausa na hora; (4) `EU CUIDO` põe `needs_human/humano_assumiu` e **nada mais sai**; (5) com a pausa aberta, os **nove** gatilhos devolvem "não enviei, pausa humana"; (6) `foi_humano=False` **não** abre pausa (**linha de controle**).

**MUTAÇÃO C:** desligar a escrita de `silencio_deliberado_ate` no caminho humano → o teste (1) fica vermelho. Tirar o teto de renovações → o teste (2) fica vermelho. Trocar `foi_humano` por `True` fixo → o teste (6) fica vermelho.

---

## 8. BLOCO D · O HUMANO DA SEGURADORA NA URA (diagnóstico §11)

### 8.1 D1 · A âncora POSITIVA de entrada na fase humana

**Hoje a transição é por EXCLUSÃO:** `insurer_dispatch_service.py:2908-2910` — *"Sem âncora de URA: fase humana da seguradora"*. Qualquer tela que não case passo nenhum vira fase humana. É frágil nos dois sentidos: uma tela de URA desconhecida vira "humano", e um humano que fale algo parecido com uma tela conhecida continua sendo tratado como URA.

**O que a SPEC faz:** passos declarados `noop` com a chave nova **`enters_human_phase: True`**.

```python
# corridor_playbooks.py — exemplo no allianz-residencial
{"step": "transferencia_ao_especialista",
 "anchor": r"vou transferir seu caso para um especialista",
 # 📊 98 sessões (zonas_do_acervo.FRONTEIRAS["allianz"]) · 42 ocorrências literais no
 #    corpus de hoje: allianz-residencial 31, allianz-auto 11 (grep -ic, 13/09)
 "reply": "", "noop": True, "enters_human_phase": True,
 "notes": "âncora medida em zonas_do_acervo.FRONTEIRAS['allianz']"}
```

⛔ **E o que NÃO entra como âncora, porque foi medido e não existe.** O §11.3 do diagnóstico sugere *"Isso pode levar alguns instantes"* como âncora positiva. 📊 Medido hoje nos 16 arquivos do corpus: essa frase **não aparece em nenhuma redação**. As reais são *"aguarde alguns instantes"* (hdi, 1), *"em instantes, um de nossos anali…"* (yelum, 1) e — 🔴 a perigosa — *"seu atendimento podem aparecer depois de alguns instantes"* (porto, 6), **que não é transferência nenhuma** e viraria falso positivo em 6 telas. A âncora de espera correta já existe medida: `AVISO_DE_ESPERA` (`zonas_do_acervo.py:327`, 5 padrões, 📊 40 sessões em 4 seguradoras), e **ela não muda a fase** — ela alimenta o relógio de fila do §8.4.

⚠️ **O falso positivo gêmeo, já catalogado:** *"Previsão de chegada do especialista"* (📊 3 sessões) é o **prestador a caminho**, não a transferência — e já está em `NAO_E_FRONTEIRA["allianz"]`. Qualquer âncora que procure só a palavra "especialista" o pega. É por isso que a tabela tem controle negativo e um teste de cruzamento obrigatório (`cruzamento_fronteira_x_nao_fronteira`, `:644`): **todo padrão de `FRONTEIRAS` roda contra `NAO_E_FRONTEIRA` e tem de dar ZERO.**

`noop` **já existe** e o motor já o trata (`insurer_dispatch_service.py:2628-2631`: reconhece e não responde). A chave nova acrescenta uma linha ali: reconheceu, não responde, **e muda a fase**.

🔴 **As âncoras não são escritas à mão: vêm de `backend/scripts/zonas_do_acervo.py:56` (`FRONTEIRAS`)**, que tem as 10 seguradoras, cada padrão com a contagem de sessões medida ao lado, e um **controle negativo** (`NAO_E_FRONTEIRA`, `:597+`) com o teste obrigatório de cruzamento (`cruzamento_fronteira_x_nao_fronteira`, `:644`). A SPEC **move as tabelas** para um módulo importável pelo produto e faz `scripts/` importar de lá. Uma fonte, dois consumidores.

⚠️ **E aqui mora a armadilha do §9.4 do CLAUDE.md.** Aqueles padrões foram medidos sobre `norm_para_classificar` (`zonas_do_acervo.py:463`). O motor normaliza com `_norm_text` (`insurer_dispatch_service.py:2939-2949`) e com `corridor_playbooks._norm`. **Antes de confiar num número que veio de outra ferramenta, rode-o na ferramenta que vai usá-lo** — é o item 5 do BLOCO 0, e é gate.

### 8.2 D2 · `needs_human` deixa de ser surdo

**As três portas que `needs_human` fecha**, cada uma com a linha conferida hoje:

```
insurer_dispatch_service.py:2909   if session.get("state") == "ura":   ← só "ura"
                                   📊 grep '\["state"\] *= *"human_phase"' app/ → 1 ocorrência
dispatch_router.py:2923            if (state == "human_phase" and …)   ← o Cérebro exige a fase
dispatch_watchdog.py:49,73-74      _TERMINAL_STATES inclui needs_human → `return None` seco
```

**O contrato da reentrada:**

```python
REENTRAVEIS = {           # a sessão travou, mas a conversa está viva
    "sentinela_stall", "slot_opcao_sem_derivacao", "tecla_ambigua",
    "ramo_indeterminado", "segurado_nao_respondeu",
}   # + os "human_phase_guard:*"
NAO_REENTRAVEIS = {       # a conversa acabou, ou alguém assumiu
    "insurer_closed", "test_aborted", "humano_assumiu", "encaminhado", "resolvido",
}

def pode_reentrar_em_fase_humana(session, tela: str, seguradora: str) -> bool:
    # state == "needs_human"
    # AND session["reason"] em REENTRAVEIS
    # AND (é FRONTEIRA da seguradora  OU  tem APRESENTACAO_HUMANA)
    # AND NOT APRESENTACAO_DO_ROBO       ← o controle negativo, obrigatório
```

🔴 **O controle negativo não é detalhe: é o que impede a regra de comer o acervo inteiro.** 📊 Sem ele, `meu nome é|me chamo|sou a` marca 123 de 140 sessões da Allianz — porque *"sou a assistente virtual da Allianz"* é o **robô** se apresentando (`zonas_do_acervo.py`, bloco do controle negativo, e `NAO_E_FRONTEIRA["allianz"]`). O robô se apresenta **mais** que a gente.

**O que acontece quando reentra:**

1. `state = "human_phase"`. O Vigia **volta a vigiar sozinho** — `dispatch_watchdog.py:73` deixa de devolver `None` porque o estado mudou. **Nenhuma linha do Vigia precisa mudar para isso.**
2. O **resumo determinístico** sai, **uma vez**: o caminho já existe (`insurer_dispatch_service.py:2911-2927`, `render_opening_message` em `corridor_playbooks.py:8384`) e já é guardado por `session["summary_sent"]` (`:2925-2926`). A reentrada **não** limpa a flag.
3. O grupo recebe **"a seguradora respondeu, retomei"** 🔴 **só se já tinha recebido o pedido de ajuda** — a condição é `session.get("dossier_sent")`. Sem dossiê antes, não há o que corrigir, e uma mensagem a mais é exatamente o ruído que a 001.3 existe para matar.
   💭 Copy: *"↩️ A {seguradora} respondeu no caso do {primeiro nome}. Retomei o atendimento — aviso quando tiver o protocolo."*
4. `registrar_ato_do_agente(…, agente="cerebro", mensagem="reentrada em fase humana")` grava a linha (bloco D6).

**O gate é o relógio da Vivian:** partindo do estado `needs_human` com o texto exato dela (só estrutura e horários; **nenhum nome, nenhum dado pessoal no teste**), o resumo do caso sai em **≤ 30 s**. 📊 Em 10/09 não saiu em 48 minutos, e o resumo **estava pronto**: rodando o motor sobre o texto dela, o gatilho casa e a execução chega ao `resumo_analista`. Faltou o estado.

### 8.3 D3 · Perguntar ao segurado e voltar

📊 Todas as **7** chamadas de `send_to_client` no roteador são **avisos** (`dispatch_router.py:2667, 2893, 3091, 3126, 3163, 3304, 3345`). Nenhuma pergunta e espera. Em 10/09 a URA pediu **ponto de referência** — uma coisa que só o segurado sabe — e o Cérebro respondeu `NAO_SEI` duas vezes, **corretamente**, e a sessão morreu por não haver caminho.

```python
# backend/app/services/dispatch_router.py
async def perguntar_ao_segurado(company_id: str, session: dict, *,
                                slot: str, pergunta: str,
                                prazo_s: int) -> bool

session["esperando_do_segurado"] = {
    "slot": str, "pergunta": str,
    "pedido_em": iso, "ate": iso,
    "holdings": int,          # quantas vezes seguramos a seguradora
    "tela": str,              # a tela que pediu
}
```

O desenho, em quatro movimentos:

```
① pergunta pelo canal do CLIENTE (send_to_client, que já existe e já é governado)
   💭 "Só uma coisa para a {seguradora} conseguir chegar aí: {pergunta}"
② avisa a SEGURADORA que estamos confirmando — e 🔴 é este envio que reinicia o
   relógio de inatividade da URA do outro lado (a mesma física da D-PILOTO-10)
   💭 "Um instante, por favor — estou confirmando esse dado com o segurado."
③ o prazo. O Vigia já varre `dispatch:active:*` a cada 20 s: a espera vive na sessão
   e é lida lá. ⛔ Nenhum scheduler novo. Se o BLOCO 0 provar que `work_waits` tem
   leitor para este caso, usa-se `work_waits`; senão, o Vigia basta
④ o desfecho, e ele é obrigatório:
   · segurado respondeu a tempo  → preenche o slot, responde a URA, segue
   · prazo vencido               → repete ② (máx. HOLDINGS_MAX) e, esgotado,
                                   `needs_human` com reason="segurado_nao_respondeu"
                                   e dossiê que diz exatamente o que falta
   · `insurer_closed` chegou antes → 🔴 para tudo. Não insiste com a seguradora,
                                   não cutuca, e o dossiê diz "a seguradora encerrou
                                   enquanto eu esperava o segurado"
```

**Os valores saem medidos** no BLOCO 0 (item 6): `prazo_s` e `HOLDINGS_MAX` derivam do encerramento por inatividade **daquela seguradora** (📊 Allianz mín. 103 s · mediana 246 s; Yelum mín. 359 s). 💭 Ponto de partida a refutar: `prazo_s = 0,6 × mediana_da_seguradora`, `HOLDINGS_MAX = 2`.

⚠️ **Limite declarado:** só se pergunta ao segurado o que a **ficha não tem** e o que **só ele sabe**. `responder_da_ficha` (`insurer_dispatch_service.py:1396-1442`) já resolve o resto e já marca `sem_dado_na_ficha` (`:1436-1441`, virando `session["falta_para_a_ura"]` em `:2901-2906`). **Esse campo é o gatilho da pergunta** — não se inventa um detector novo.

### 8.4 D4 · Dois relógios: FILA ≠ HUMANO SUMIDO

📊 O acervo da Allianz (114 transferências, 50 atendentes distintos): **59 % chegam em < 10 s · mediana 3 s · p90 10,5 min · máx 49 min**. Cutucar em 2 minutos cutucaria **fila vazia** em ~30 % dos casos — falar com ninguém.

Hoje há um relógio só: `HUMAN_NUDGE_S = 600` e `HUMAN_ALERT_S = 1200` (`dispatch_watchdog.py:34-35`), aplicados a `direction == "out"` em `:126-130`, **sem distinguir se alguém já falou**.

```python
session["humano_falou_em"] = iso | None     # primeira fala classificada como zona HUMANO
session["fila_desde"] = iso                 # entrada em human_phase sem ninguém falar

# FILA — prazo ABSOLUTO desde a entrada (Step Functions TimeoutSeconds;
#        gen_statem state_timeout: mensagens soltas não o cancelam)
FILA_ALERTA_S = 1200      # 💭 ponto de partida = o HUMAN_ALERT_S de hoje; sai medido
#   ⛔ NENHUMA cutucada enquanto estivermos em fila. Não se cutuca ninguém.
#   📊 AVISO_DE_ESPERA (zonas_do_acervo.py:327) confirma a fila pelo texto
#      ("estamos com alto volume", "você está na fila para atendimento") e
#      renova o prazo UMA vez — a URA disse que estamos na fila; ela sabe

# HUMANO SUMIDO — watchdog DESLIZANTE, só existe depois de humano_falou_em
#                 (Step Functions HeartbeatSeconds; cada fala é um heartbeat)
HUMAN_NUDGE_S = 600       # mantém
HUMAN_ALERT_S = 1200      # mantém
# 🔴 INVARIANTE, copiada da AWS: heartbeat < timeout. 600 < 1200. Um guarda afirma isso
```

### 8.5 D5 · O encerramento da Allianz reconhecido

A regex `insurer_closed` (`insurer_dispatch_service.py:2544-2553`, inline — **não há constante nomeada a importar**) cobre hoje, literalmente:

```
conversa ser[áa] encerrada · estamos encerrando (?:esta|a) conversa
tempo m[áa]ximo de espera.*excedid · encerrad[ao] por (?:inatividade|falta de intera)
falta de intera[çc][ãa]o esta conversa foi encerrada · conversa foi encerrada
```

Efeito: `state="needs_human"`, `reason="insurer_closed"` (`:2551-2552`), rodando **depois** da captura de protocolo e do `detect_referral_step` (`:2527`) e **antes** de qualquer passo de URA.

🔴 **Correção medida ao diagnóstico, e ela muda o trabalho.** O diagnóstico §11.2(a) escreve a frase como *"Por falta de contato, estou encerrando"*. 📊 Medido hoje no corpus: `grep -ic "falta de contato"` → **0 nos 16 arquivos**; `grep -ic "estou encerrando"` → **3, só em `bradesco-auto`**, e a redação real é *"Bom, estou encerrando este atendimento por falta de interaç…"* — 🔴 **que a regex de `:2548` JÁ CASA** (`encerrad[ao] por (?:…|falta de intera)`).

**Então uma de duas coisas é verdade, e o BLOCO 0 decide qual:**

```
① a frase de setembro tem outra redação, que está em `observed_events` e não no corpus
   (o corpus para em 21/08). → a SPEC acrescenta A REDAÇÃO MEDIDA, com a consulta ao lado
② a frase já era coberta e o defeito real era OUTRO — por exemplo, a ordem: a Allianz
   escreve a frase DEPOIS de a sessão já estar em `needs_human`, e `handle_insurer_message`
   nem chega a `:2544`. → o conserto não é a âncora; é a reentrada do §8.2 aplicada ao
   caminho de encerramento
```

⛔ **Escrever a âncora antes de saber qual das duas é verdade seria consertar o sintoma errado.** A consulta é o item 7 do BLOCO 0, e ela é bloqueante deste sub-bloco. Se for ①, a frase entra **com a contagem ao lado**; se for ②, o relatório registra que a âncora **não** precisava mudar e o achado do diagnóstico é corrigido por escrito.

Em qualquer dos dois casos, o guarda é o mesmo e fecha a porta: **ZERO `human_phase` depois da frase de encerramento**, sobre o texto do acervo regenerado. E `insurer_closed` é o primeiro dos `NAO_REENTRAVEIS` (§8.2) — depois dela, nem o resumo, nem o Vigia, nem a cutucada.

### 8.6 D6 · Os atos do agente passam a existir

📊 `work_events` com `agente.cerebro | agente.sentinela | agente.vigia`: **0 de 0 em toda a base** (diagnóstico §11.2c). O desempenho do Cérebro é inauditável — e é o que mais atrapalha qualquer medição do piloto (EXTRA-001.7).

🔴 **Correção ao diagnóstico, medida hoje:** a função **não é código morto**. `registrar_ato_do_agente` (`dispatch_router.py:997-1027`) tem **três chamadores reais**: `:2967` (Cérebro, 1ª tentativa), `:3057` (Cérebro, retentativa aceita) e `dispatch_watchdog.py:408` (Sentinela). O que não existe é `agente="vigia"`: 📊 `grep -rn 'agente="' backend/app/` devolve só `cerebro` (×2) e `sentinela` (×1), apesar de `DESTRAVADORES` (`dispatch_router.py:710`) e `_ATOR_DO_DESTRAVADOR` (`:727-733`) já preverem `"vigia"`.

**Então a pergunta certa não é "por que ninguém chama", e sim "por que a chamada não chega ao INSERT"** — o ELO. A hipótese mais forte, a refutar no BLOCO 0: `:1011-1013` devolve `False` quando `session["work_run_id"]` está vazio. O conserto sai **da medição**, não desta proposta.

A SPEC entrega: (1) a causa escrita no relatório, com o comando; (2) o conserto; (3) o chamador do Vigia; (4) o guarda **≥ 1 linha `agente.*` por sessão que usou o Cérebro**.

### 8.7 Gate D

**GATE D:** (1) replay da sessão da Vivian (só estrutura e horários, sem PII) a partir do estado `needs_human` → o resumo sai em **≤ 30 s**; (2) o mesmo texto com *"sou a assistente virtual da Allianz"* → **não** reentra (**linha de controle**); (3) `needs_human` com `reason="insurer_closed"` → **ZERO** `human_phase` depois; (4) `EU CUIDO` (`humano_assumiu`) → **não** reentra; (5) fila sem ninguém falar por 15 min → **nenhuma cutucada**, e um alerta ao grupo no prazo medido; (6) humano falou e sumiu 11 min → **cutucada**; (7) a URA pede ponto de referência → pergunta ao segurado sai pelo canal do cliente, holding sai para a seguradora, e o desfecho dos três casos acontece; (8) `SELECT count(*) FROM work_events WHERE event_type LIKE 'agente.%'` sai de 0.

**MUTAÇÃO D:** tirar a condição `NOT APRESENTACAO_DO_ROBO` → o teste (2) fica vermelho. Tirar `insurer_closed` de `NAO_REENTRAVEIS` → o (3) fica vermelho. Fundir os dois relógios num só → o (5) fica vermelho. Remover a frase nova da âncora `insurer_closed` → o (3) fica vermelho **pelo texto do acervo**.

---

## 9. BLOCO E · RISCOS ADJACENTES, ACERVO E RÉGUA

### 9.1 `azul-auto / menu_atendimento` — "1" sem rede

```python
# corridor_playbooks.py:3269   (AZUL_AUTO_WHATSAPP_V1, def em :3220)
{"step": "menu_atendimento", "anchor": r"de que atendimento voc[êe] precisa", "reply": "1", …}
```

O próprio `constante_justificada` (`:3270-3271`) **reconhece o risco por escrito**: *"'Cancelar serviço' é a opção 1 em uma das variantes: tecla errada aqui CANCELA um serviço já aberto."*

🔴 **O contraste que fecha o caso, medido hoje:** a **Porto usa a âncora literalmente idêntica**, no mesmo menu, e responde **pelo rótulo** — `corridor_playbooks.py:2250`, `reply: "Novo serviço"`. Duas telas com a mesma redação; uma aposta na posição, a outra lê o rótulo.

**Conserto:** a azul passa a responder `"Novo serviço"`, como a Porto — e a **camada 1 do bloco A** converte para dígito **lendo a tela real** quando ela for numerada. Assim as duas variantes funcionam, e nenhuma depende da posição. 📊 Nota adjacente medida em 23/08 no próprio arquivo (`:3276-3279`): a variante numerada desse corredor tem **zero ocorrências desde 26/12/2025** — a viva é a lista.

### 9.2 Os passos homônimos

📊 `porto-auto-whatsapp@v1` tem **dois** passos chamados `complemento`:

| origem | linha | reply |
|---|---|---|
| corpo do playbook (def `:2228`) | **`:2294`** | `"não tem"` — constante |
| `_PORTO_TRONCO` (def `:4645`) | **`:4749`** | `"{local_complemento}"` + `fallback_adaptive: True` |

A concatenação (`:4851-4853`) põe o corpo primeiro (índices reais **11** e **39**), e `match_ura_step` (`:8424-8436`) devolve **o primeiro que casa**. 🔴 **O passo que leria o complemento real do caso é código morto em porto-auto**, e o segurado recebe "não tem" no lugar do endereço dele.

⚠️ **E não é só ele.** 📊 Medido hoje: `hdi-residencial-whatsapp@v1` tem **5 pares homônimos** (`quando_agora`, `identificacao_dado`, `desambiguacao_veiculo_ou_residencial`, `menu_servico_residencial`, `servico_ja_aberto`), vindos da concatenação de `:4956-4958`, que anexa os passos inteiros da yelum-residencial aos da hdi. **Isto não está no diagnóstico.**

**Conserto:** (1) a porto-auto perde o passo morto — ou o vivo passa a vir primeiro, com o motivo escrito; (2) os 5 pares da hdi são **medidos um a um** (as duas respostas são iguais? então é ruído; são diferentes? é o mesmo defeito da porto) e o relatório traz a tabela; (3) uma asserção nova **dentro da régua existente** (não um guarda novo — o teto é 12): *"nenhum corredor tem dois passos com o mesmo nome, salvo os declarados numa lista de exceções com o motivo"*.

### 9.3 O resto do P-PILOTO-06, e a higiene da bateria

A regeneração em si **subiu para o BLOCO 0-bis** (§4.1), porque os gates de A, B e D dependem dela. Fica aqui o que sobra:

- 🔴 **A frase vencida sai.** `medir_rota.py:~569` ainda imprime *"🧑 acesso ao Espelho"* — vencida, porque o leitor existe. `grep -n "acesso ao Espelho" backend/scripts/medir_rota.py` → tem de dar **0** depois (§0.4 do protocolo: mudou a frase, `grep` do valor **antigo**; sobrevivente é defeito).
- 🔴 **`INDICE.md` do corpus volta a cobrir os 16 arquivos.** 📊 Hoje cobre **1** (`bradesco-auto`, carimbo 23/08): foi sobrescrito por uma geração `--seguradora bradesco`. Um índice que descreve 1 de 16 é pior que índice nenhum, porque parece completo.
- 🔴 **Dois testes que o §9.4 do CLAUDE.md condena, e um deles é do Sentinela.** 📊 Medido hoje: `test_spec038_sentinela.py` (110 linhas) tem **zero** chamadas ao motor; `test_a_cobertura_tem_lastro_no_acervo.py` (254 linhas) tem **zero** chamadas ao motor e **7 regex próprios**. O Sentinela é peça central dos blocos B e C: **um guarda dele que não chama o motor guarda o regex, não o comportamento.** O `detector_do_eixo_e.py:62` já sabe detectar isso. Conserto: o teste do Sentinela passa a exercitar `_sentinela_recover` de verdade. O outro entra em `PENDENCIAS.md` se não for tocado.

⚠️ **E o que NÃO se faz aqui:** rotina automática de fim de dia encadeando os três comandos. 📊 Ela não existe (não há `Makefile`, não há orquestrador), e criá-la nesta SPEC seria scheduler novo por conveniência (§5). O P-PILOTO-06 fecha com os comandos rodados e a linha de base commitada; a automação vira pendência nomeada.

### 9.4 P-PILOTO-05 — o formulário nativo de Porto e Azul

📊 `native_flows` só existe em HDI e Yelum auto (`corridor_playbooks.py:2982, 3010`). Porto e Azul: *"sem schema recuperável; só um acionamento ao vivo produz um"*.

**Esta SPEC não fecha a pendência — ela produz o insumo.** O canário da coleta dirigida (D-PILOTO-05) percorre a URA **até a confirmação e recusa**, e as telas que ele produz entram no corpus. A pendência fica `CONTINUA`, com o que destrava escrito: *um acionamento real observado em cada uma*. Até lá, a tela de formulário vai a handoff com dossiê — que é o comportamento de hoje e continua correto.

### 9.5 Gate E

**GATE E:** (1) `python scripts/medir_rota.py --todas --com-espelho --comparar-com docs/canon/reports/LINHA-DE-BASE-DE-ROTAS.json` sai **0** — número contra número, não impressão (o comparador já reprova quem perde `respondidas`, `medir_rota.py:386-390`); (2) as âncoras novas do bloco D casam nas telas de setembro que o 0-bis trouxe; (3) zero passos homônimos não declarados; (4) `grep -n "acesso ao Espelho" backend/scripts/medir_rota.py` → **0**; (5) `INDICE.md` cita os 16 arquivos; (6) `test_spec038_sentinela.py` passa a chamar o motor — e um teste que hoje passa **continua passando** (linha de controle).

---

## 10. GUARDAS E MUTAÇÕES — doze, e nem um a mais (D-PILOTO-14)

> Regra de admissão, do CLAUDE.md §9.3–§9.5: **todo guarda chama o MOTOR e lê o ACERVO**. Guarda que roda regex por fora, ou que reimplementa a regra, não entra. E **todo guarda vem com a mutação que o deixa vermelho** — um guarda que não consegue falhar não guarda nada.

| # | o guarda | o que ele afirma | a mutação que o deixa VERMELHO |
|---|---|---|---|
| **GA-1** | `test_a_tecla_tem_a_forma_da_seguradora.py` — **laço invertido** | todo slot `*_opcao` **exigido por um passo** tem origem declarada (subserviço · derivação · inline · constante justificada). Hoje o laço parte dos derivados (`:143`, `:154`) e um órfão é invisível; `donos()` (`:133-138`) já existe e passa a ser a origem do laço | apagar a derivação de `problema_eletrico_opcao` → o guarda tem de nomear o slot. (Hoje o teto de `:160`, `len(VALORES) >= 15`, toleraria apagar 8) |
| **GA-2** | menu numerado recebe número — **pelo motor, sobre a tela real** | `resolver_tecla` sobre a tela do acervo e o caso real devolve `"1"`; com slot vazio devolve `needs_human`; com tela sem menu devolve a palavra | `resolver_tecla` devolvendo o valor cru → vermelho com **"residência"** |
| **GA-3** | o parser lê o **texto certo**, e o palpite fica desligado | duas afirmações: (a) `parse_options` sobre o texto **CRU** do menu da Allianz devolve **ZERO** opções, e sobre o **normalizado** devolve **três** — é assim que se prova que a normalização era o que fazia funcionar; (b) o corredor nunca usa o ramo de lista nua (`cartographer.py:397+`) | tirar o `_norm` da chamada → GA-2 fica vermelho com o menu real. Ligar o palpite → uma tela de prosa do acervo vira "menu" e o guarda acusa |
| **GB-1** | o reparo acontece, uma vez, sem consumir tentativa | recusa + menu pendente + resposta em palavra → sai o dígito, `sentinela_attempts` inalterado, e o 2º reparo na mesma tela não sai | remover a condição ④ → repara duas vezes, vermelho |
| **GB-2** | tentativas são **por tela** | duas telas, 2 tentativas cada, o Sentinela funciona nas duas | trocar por contagem de sessão → a 2ª tela fica sem rede, vermelho |
| **GB-3** | o Cérebro **sabe** que foi recusado | o prompt montado por `build_human_phase_messages` contém `ultima_resposta_recusada` e as opções da tela | remover os campos → vermelho |
| **GC-1** | a pausa cala o Sentinela | 60 s depois de `note_manual_outbound(foi_humano=True)`, o Sentinela não respondeu; e `foi_humano=False` **não** abre pausa (controle) | não escrever `silencio_deliberado_ate` → vermelho |
| **GC-2** | a pausa tem teto | 3ª renovação não acontece; o corredor retoma | teto infinito → vermelho |
| **GC-3** | com pausa aberta, **os nove** gatilhos calam | cada um dos nove devolve "não enviei: pausa humana" | remover a consulta de **um** deles → vermelho, e o guarda diz **qual** |
| **GD-1** | `needs_human` reentra, e o resumo sai | replay da Vivian a partir de `needs_human` → resumo em ≤ 30 s; com *"assistente virtual"* **não** reentra (controle) | remover o controle negativo → o robô se apresentando reabre a sessão, vermelho |
| **GD-2** | encerrada é encerrada | **ZERO** `human_phase` depois da frase de encerramento **medida no item 7 do BLOCO 0**, sobre o acervo regenerado — e a frase que o guarda usa é a do acervo, ⛔ nunca a do enunciado (§8.5) | tirar a frase da âncora → vermelho pelo texto real. Se o BLOCO 0 concluir o caso ②, a mutação é reintroduzir a ordem antiga do `handle_insurer_message` |
| **GD-3** | os dois relógios existem, e o heartbeat é menor que o teto | fila 15 min → **nenhuma** cutucada; humano falou e sumiu 11 min → cutucada; e `HUMAN_NUDGE_S < FILA_ALERTA_S` | fundir os relógios → vermelho nos dois sentidos |
| **GD-4** | o agente deixa rastro | ≥ 1 linha `agente.cerebro\|sentinela\|vigia` por sessão que chamou o Cérebro | remover o `registrar_ato_do_agente` de `:2967` → vermelho |

📊 São **13 linhas** na tabela porque GA-3 e GB-3 cabem dentro dos arquivos de GA-2 e GB-1 — **12 arquivos de guarda novos, no máximo**, e o relatório traz a contagem real. Se passar de 12, corta-se o de menor valor marginal e registra-se qual e por quê (§9.1 do protocolo).

**Onde a mutação roda:** worktree próprio ou lock exclusivo, restaurando **por cópia**, nunca `git checkout` (§10 do protocolo). ⚠️ E a lição da EXTRA-001: *a suíte restaura arquivos por cópia* — o orquestrador **não** roda a bateria inteira enquanto um juiz muta. `backend/scripts/verificar_mutacoes.py` (293 linhas) já executa mutações contra `test_a_regua_nao_tem_furo.py` **e exige vermelho**: é o padrão a copiar, não a reinventar.

🔴 **Como a bateria se roda aqui — medido hoje, e não é `pytest`:**

```bash
cd backend && PYTHONIOENCODING=utf-8 python tests/run_all.py    # o runner canônico
#   📊 347 arquivos test_*.py · cada um em PROCESSO separado · TIMEOUT_POR_TESTE = 180 s
#   📊 a suíte NÃO usa `assert` na maioria: o padrão é um helper `checar(cond, texto)`
#      que imprime ok/FALHA e sai com sys.exit(1). `grep -c assert` SUBESTIMA a cobertura
#   ⚠️ não há Makefile, não há marcas pytest declaradas. `pytest tests/` só funciona por
#      causa do conftest.py, que isola os 273 arquivos sem `def test_` em subprocesso
```

**Guardas novos desta SPEC nascem no padrão do arquivo vizinho** (`checar()` + `sys.exit`), não em `assert`, para que `run_all.py` os conte. E todos passam pelo `regua_motor` ou importam o motor direto (§3.1).

**Três asserções que entram em guardas existentes, não em arquivos novos** — porque o teto é 12:

- **GT · dois tenants** (CLAUDE.md §7): duas corretoras, **mesma seguradora, mesma tela**, uma com pausa aberta e a outra não → a pausa de uma **não** cala a outra, o `menu_pendente` de uma **não** aparece na outra, e o dossiê de uma **não** vai ao grupo da outra. 🔴 Entra **dentro de GC-3**, com dois `company_id` reais de fixture. Mutação: carregar a sessão só por `insurer_phone` (sem `company_id`) → vermelho. ⚠️ O backend usa **service role**: RLS sem policy não protege nada contra erro de filtro no código — o que se prova é **o filtro no código**.
- nenhum corredor tem passos homônimos não declarados (§9.2) → dentro da régua;
- o dialeto do normalizador: os padrões de `FRONTEIRAS` dão a **mesma** classificação com `_norm_text` e com `norm_para_classificar` sobre o acervo (§8.1) → dentro de GD-1.

---

## 11. MIGRATIONS

**Leitura obrigatória antes de qualquer SQL:** [`docs/canon/MIGRATIONS-AUTHORITY.md`](../MIGRATIONS-AUTHORITY.md). Diretório canônico de migrations novas: `backend/supabase/migrations/`.

**Previsão desta proposta: nenhuma migration.** Tudo o que a SPEC cria vive (a) dentro da sessão do corredor, em Redis (`dispatch:active:{company_id}:{insurer_phone}`), que é transitório por desenho (CLAUDE.md §6), ou (b) em `work_events`, que já existe e já é escrita por `_evento` (`dispatch_router.py:683-700`).

🔴 **A única DDL possível, e ela é condicional:** se o BLOCO 0 (item 10) descobrir um `CHECK` em `work_events.event_type` que recuse `agente.vigia`, a SPEC ganha **uma** migration aditiva. O CHECK conhecido hoje é em `actor_type` (`ATORES_VALIDOS = ("system","worker","user","agent","admin","provider")`, `dispatch_router.py:680`), e `"agent"` já está lá.

Se houver migration: **idempotente · expand-first · com APPLY / VERIFY / ROLLBACK escritos ANTES de rodar**, e o VERIFY conferindo **o objeto no banco**, não o ledger de migrations.

```sql
-- APPLY   (exemplo, só se o CHECK existir e recusar)
ALTER TABLE work_events DROP CONSTRAINT IF EXISTS work_events_event_type_check;
ALTER TABLE work_events ADD  CONSTRAINT work_events_event_type_check CHECK (...);
-- VERIFY
SELECT pg_get_constraintdef(oid) FROM pg_constraint
 WHERE conrelid='work_events'::regclass AND contype='c';
-- ROLLBACK
-- restaura a definição anterior, colada literalmente no relatório antes do APPLY
```

⛔ Proibido: mover, renomear, apagar ou reaplicar migration existente sem manifesto aprovado. Proibido sempre: `schema_completo.sql`, `upgrade_v6.2.sql`, `storage_buckets.sql`.

---

## 12. CANÁRIO CONTROLADO EM PRODUÇÃO

### Antes

1. Confirmar TESTE-A e TESTE-B na configuração privada; conferir **qual número está efetivamente pareado** (nome de conexão não prova identidade).
2. Fixar tenant, conversa e sessão de canário; **provar a trava do último ponto de efeito com saídas simuladas antes de liberar qualquer envio vivo** — e a trava precisa cobrir os quatro caminhos de saída deste corredor: mensagem à URA, `send_to_client`, **cutucada** (`dispatch_watchdog.py:575`) e **dossiê ao grupo** (`:421`, `dispatch_router.py:3304`).
3. Ligar o Vigia **só** para a sessão do canário. ⛔ Nunca ligar dispatch num tenant operacional.

### Os casos mínimos

| # | caso | o que prova | quem faz |
|---|---|---|---|
| 1 | **Coleta dirigida (D-PILOTO-05)** numa seguradora com menu numerado: percorrer até a tela de confirmação e **RECUSAR** | a regra B viva: o menu recebe número, e as telas entram no corpus (insumo do P-PILOTO-05) | 🤖, com TESTE-A como segurado |
| 2 | **Pausa humana:** durante o caso 1, o Founder (TESTE-B representando a atendente) digita à mão na conversa com a URA | a pausa abre, o Sentinela cala 60 s, a mensagem sai ao grupo de teste uma vez | 🧑 o gesto · 🤖 a leitura |
| 3 | `AGENTE` e `EU CUIDO` no grupo de teste | as duas palavras têm efeito, e `EU CUIDO` **não** é reentrável | 🧑 envia · 🤖 verifica |
| 4 | **Pergunta ao segurado:** forçar uma tela que exija um dado ausente da ficha | a pergunta sai pelo canal do cliente (TESTE-A), o holding sai para a seguradora, e o desfecho acontece | 🤖 |
| 5 | **Rastro:** ao fim, `SELECT event_type, count(*) FROM work_events WHERE event_type LIKE 'agente.%'` | sai de 0 | 🤖 |

⛔ **O caso 1 termina na recusa.** Passar da confirmação despacha prestador real — é a linha que a D-PILOTO-05 desenhou e ela não se cruza "para ver se funciona".

### Depois

Desligar a habilitação do canário; cancelar intenções pendentes da sessão de teste; conferir que **nenhuma sessão do canário ficou ativa** em `dispatch:active:*` (uma sessão órfã tem TTL de 6 h e o Vigia continuaria agindo sobre ela); preservar as telas capturadas no corpus, com PII mascarada (`test_o_corpus_nao_vaza_pii.py` é o guarda que já existe); entregar as evidências com aliases.

---

## 13. VALIDAÇÃO COM SAIONARA E REGINA

O executor **não as contata** e **não usa os números operacionais delas**. Ele prepara o roteiro; o Founder conduz.

O que se valida com elas, e só isto:

1. A mensagem de pausa ao grupo é compreensível? `AGENTE` e `EU CUIDO` são óbvios, ou precisam de outra palavra?
2. Quando elas digitam na URA, 60 s é pouco, muito, ou certo? (📊 a medida diz 60 s; a **percepção** delas é dado novo e vai para `FOUNDER-DECISIONS` se contrariar).
3. A pergunta ao segurado ("Só uma coisa para a {seguradora} conseguir chegar aí…") soa como a corretora fala?
4. A linha de retomada ("A {seguradora} respondeu, retomei") chega na hora certa ou vira ruído?

Registrar aceite **só se recebido**. Distinguir, no relatório: `não testado` · `aprovado pelo canário técnico` · `validado pela atendente`.

---

## 14. ENTREGA, IMPLANTAÇÃO E ROLLBACK

**Preflight e regressão** pela autoridade vigente. ⛔ Nunca `git add -A`, force push, exclusão de trabalho ou alteração de guarda para obter verde.

🔴 **Entregar não é commitar. É empurrar** (CLAUDE.md §2):

```bash
git rev-list --count origin/main..HEAD          # 0 = o trabalho está no ar
git merge-base --is-ancestor origin/main HEAD && git push origin HEAD:main
```

A saída real do `push` vai **colada** no relatório, com o SHA remoto conferido.

**Implantação:** o serviço afetado é o do atendimento/dispatch (o que roda `buffer_processor` e o Vigia). O executor prepara tudo e deixa o clique **Implantar** no EasyPanel como ação final do Founder, se a autoridade vigente assim exigir; não contorna por API.

**Variáveis de ambiente novas** — nome, sem valor, e todas com default seguro no código:

```
PAUSA_HUMANA_S                 (default 60)     · D-PILOTO-10
PAUSA_HUMANA_MAX_RENOVACOES    (default 2)
MAX_TENTATIVAS_POR_TELA        (default 2)
MAX_TENTATIVAS_NA_SESSAO       (default 6)      · valor final medido no BLOCO 0
FILA_ALERTA_S                  (default 1200)   · valor final medido no BLOCO 0
PERGUNTA_AO_SEGURADO_HOLDINGS  (default 2)
```

⚠️ Mexeu em env: o verificador mecânico roda `npm run test:rotas-montam` **se** houver mudança em `app/`, `middleware.ts` ou `next.config.js` — aqui não há, e isso vai **escrito** no relatório em vez de ser presumido (CLAUDE.md §9.1).

**Rollback:** todas as travas novas são **fail-closed** — desligá-las devolve o comportamento de hoje, que é pior, não perigoso. A ordem: (1) `PAUSA_HUMANA_S=0` desliga o bloco C sem tocar em código; (2) a reentrada do bloco D é desligável por flag; (3) a camada 1 do bloco A **não** se desliga por flag — desligá-la reintroduz o defeito que mandou "residência" ao menu, e isso vai escrito. Reversão de código **não desfaz mensagem já enviada** à seguradora.

---

## 15. DOCUMENTAÇÃO E ACOMPANHAMENTO OBRIGATÓRIOS

Um escritor por arquivo, durante a execução e não no fim:

1. **SPEC definitiva** em `docs/canon/specs/SPEC-EXTRA-001.4-o-corredor-nao-trava-sozinho.md` e **relatório** em `docs/canon/reports/SPEC-EXTRA-001.4-EXECUTION-REPORT.md`, pelo template canônico, **abrindo com o EXECUTION CARD** (§0.1 do protocolo: relatório sem card = SPEC aberta) e com a telemetria de cinco linhas (§11).
2. **`PENDENCIAS.md`**: `P-PILOTO-05` → `CONTINUA` com o que destrava (acionamento real; a coleta dirigida produziu as telas); `P-PILOTO-06` → `FECHADA` com a saída dos três comandos colada. **Pendências novas que esta redação já identificou e que a execução precisa registrar se não as fechar:** os 28 órfãos de derivação remanescentes · os 5 pares homônimos da hdi-residencial que não mudarem resposta · `tokio-residencial`/`tokio-condominio` sem rota na régua (📊 59 telas, 6 sessões nunca medidas) · `test_a_cobertura_tem_lastro_no_acervo.py` com 0 motor e 7 regex · a rotina automática de fim de dia do P-PILOTO-06 · `agente.vigia` além da linha mínima. Cada uma com **o que destrava · de quem é (🧑/🤖) · o que custa esquecer**.
3. **`FOUNDER-DECISIONS.md`**: registrar o valor **medido** de `FILA_ALERTA_S`, do prazo da pergunta ao segurado e de `MAX_TENTATIVAS_NA_SESSAO` — são decisões delegadas, e o §9 do protocolo manda dar nota 0–100, escolher e registrar.
4. **`CHANGE-ADDENDA.md`**: os 5 pares homônimos da hdi-residencial e os 28 órfãos remanescentes, classificados BLOCKER · ESSENCIAL · VALIOSA · FUTURA.
5. **`ESTADO-DAS-SPECS.md`** e `INDICE-DE-SPECS.md`: a EXTRA-001.4 aparece; a família EXTRA passa pelos mesmos guardas de protocolo (⛔ nada de isentar por regex numérica).
6. **Dossiê do Founder** — fonte versionada `docs/canon/reports/dossies/dossies-autobrokers.html`, publicado em https://claude.ai/code/artifact/afe1510d-f31c-4d13-9441-aa920ad2b868 (aba **Pilotos**). Ler o HTML publicado **inteiro** antes de republicar com `url`, preservar as páginas existentes, publicar **a cada bloco fechado**. Sem ferramenta ou acesso: atualizar a fonte e registrar **"publicação do dossiê pendente"**, com o arquivo e o passo exato. ⛔ Nunca afirmar que o link foi atualizado sem conferir.

---

## 16. O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS (§7.3 do protocolo)

> Cinco fontes primárias, reabertas em **13/09/2026**. O pesquisador do executor as reabre de novo na conversão e registra a data. Nenhuma vira autoridade: modela-se o **padrão** (CLAUDE.md §5).

### E01 — W3C SCXML 1.0 (REC 01/09/2015)
**URL:** https://www.w3.org/TR/scxml/ · seções §3.5 `<transition>`, §3.7 `<final>`, §3.13, §6.2 `<send>`, §6.3 `<cancel>`.
**O que faz:** timeout de estado não é um timer atado ao estado — é um **evento agendado** (`<send delay>`) com identificador, que o autor é **obrigado a cancelar** na saída (`<cancel sendid>`). E a nota normativa de §3.5 separa dois gestos que parecem um: *"If the 'target' on a `<transition>` is omitted… taking the transition does not change the state configuration but does invoke the executable content"* — e transição **para o próprio estado** *"the state is exited and reentered, triggering execution of its `<onentry>` and `<onexit>`"*.
**O que modelamos:** a distinção exata do bloco B. Quando a URA manda algo irrelevante, é transição **sem target**: executa ação, **não** rearma relógio. Quando a URA **recusa a opção**, é transição para o próprio estado: sai, reentra, **reenvia o prompt e zera a contagem daquela tela**.
**O que rejeitamos:** o cancelamento *best-effort* ("se o delay expirou, o cancel falha"). Nossos eventos chegam por webhook concorrente, então o timer carrega a **geração** do estado (`state_seq`) e **se auto-descarta** ao acordar fora dela. Também rejeitamos o despacho single-threaded do processador SCXML.
**Como o juiz inspeciona:** abre §3.5, lê a nota do atributo `target`, e confere no código que os dois caminhos existem separados — e que o teste GB-2 distingue os dois.

### E02 — XState (documentação oficial Stately)
**URL:** https://stately.ai/docs/delayed-transitions e https://stately.ai/docs/transitions
**O que faz:** `after` arma ao entrar no estado e — verbatim — *"Delayed transition timers are canceled when the state is exited."* Delays podem ser função do contexto (backoff por tentativa é de primeira classe). E `reenter` é **opt-in**: sem ele, transitar para o mesmo estado *"will not execute the `exit` and `entry` actions"*.
**O que modelamos:** "timer morre com o estado" vira **invariante** do corredor — nenhum timeout sobrevive à troca de tela. E o reparo do bloco B é declarado como reentrada **explícita**.
**O que rejeitamos:** o default `reenter: false` como default **nosso** — no corredor, "a mesma tela de novo" quase sempre é tentativa nova. E rejeitamos o timer em memória do processo: o nosso vive na sessão e é lido pelo Vigia a cada 20 s, porque o processo morre e o relógio não pode morrer com ele.
**Como o juiz inspeciona:** abre as duas páginas, confere a tabela de `reenter`, e roda GB-1/GB-2.

### E03 — AWS Step Functions · `TimeoutSeconds` × `HeartbeatSeconds`
**URL:** https://docs.aws.amazon.com/step-functions/latest/dg/state-task.html
**O que faz:** a doc separa **dois relógios** e é a fundação direta do nosso §8.4. `TimeoutSeconds` — *"the maximum time an activity or a task can run before it times out… The timeout count begins when the start event is executed"*. `HeartbeatSeconds` — *"Heartbeats indicate that a task is still running and it needs more time to complete. Heartbeats prevent an activity or task from timing out within the TimeoutSeconds duration"*, e *"must be a positive, non-zero integer value less than the TimeoutSeconds field value"*, e *"If more time than the specified seconds elapses between heartbeats from the task, the Task state fails"*.
**O que modelamos:** **fila** = `TimeoutSeconds` (absoluto, desde a entrada em `human_phase`, não reseta por mensagem solta) · **humano sumido** = `HeartbeatSeconds` (deslizante, cada fala do humano é um heartbeat). E a invariante dura: **heartbeat < timeout** (`HUMAN_NUDGE_S` 600 < `FILA_ALERTA_S` 1200), afirmada pelo guarda GD-3.
**O que rejeitamos:** o heartbeat como **obrigação do worker** (`SendTaskHeartbeat`) — ninguém do outro lado nos manda sinal de propósito; o nosso é **inferido do tráfego real**. E rejeitamos os defaults de 99.999.999 s: sem timeout explícito, um corredor trava para sempre.
**Como o juiz inspeciona:** abre a seção *Task state timeouts and heartbeat intervals*, e confere que os dois relógios do código são ortogonais e que o guarda afirma a desigualdade.

### E04 — Erlang/OTP `gen_statem` · os três tipos de timeout
**URL:** https://www.erlang.org/doc/apps/stdlib/gen_statem.html
**O que faz:** separa **event timeout** (*"Any event that arrives cancels this time-out"*), **state timeout** (*"A state change cancels this timer"* — e **repetir o mesmo estado não é state change**) e **generic timeout nomeado** (não é cancelado por eventos nem por mudança de estado; rearmar pelo mesmo nome substitui).
**O que modelamos:** o vocabulário inteiro. Event timeout = "ninguém falou nada" · state timeout = o prazo da tela, imune a mensagens soltas · generic nomeado = os relógios transversais (deadline de sessão, 2700 s hoje). 🔴 E sobretudo a regra *"repetir o mesmo estado não cancela o state timeout"*: é ela que impede o **laço infinito educado** do bloco B — reset por tela, **teto por sessão**.
**O que rejeitamos:** o cancelamento implícito por state change, que só é seguro num processo BEAM único e determinístico. No nosso caso o relógio está fora do processo, então o cancelamento vira **descarte na hora do disparo**, por comparação de `(tela_id, geração)`. E rejeitamos `infinity` como forma de cancelar: silencioso demais para auditar.
**Como o juiz inspeciona:** abre a seção de tipos de timeout, e confere que o teto de sessão de GB-2 existe e tem valor medido.

### E05 — W3C VoiceXML 2.0 · reprompt com contagem **por prompt**
**URL:** https://www.w3.org/TR/voicexml20/ (§2.1.4 tapered prompts · §5.2 event handling · §5.2.4 seleção por `count`) · DTD normativa https://www.w3.org/TR/voicexml20/vxml.dtd · VoiceXML 1.0 NOTE §11.2 https://www.w3.org/TR/2000/NOTE-voicexml-20000505/
**O que faz:** a URA clássica já resolveu este problema há 25 anos. A DTD normativa dá `count` a `catch`, `nomatch`, `noinput` **e** `prompt`. E o §11.2 é literal: *"Each form item and `<menu>` maintains a counter for each event that occurs while it is being visited; these counters are **reset each time** the `<menu>` or form item's `<form>` is **re-entered**."* Além disso, `noinput` (silêncio) e `nomatch` (falou, mas inválido) são **caminhos de reparo diferentes**.
**O que modelamos:** (1) **contagem por tela, com reset na reentrada** — é literalmente o nosso `tentativas_por_tela`, e é a doutrina que o `MAX_SENTINELA_ATTEMPTS` por sessão viola; (2) a separação `noinput` × `nomatch`, que no nosso caso é **relógio de silêncio** × **reparo de opção inválida** — contadores diferentes, caminhos diferentes; (3) prompts escalonados por `count` (1ª vez o dígito; 2ª vez o dígito com o rótulo; 3ª vez humano).
**O que rejeitamos:** a herança de escopos do VoiceXML (item → form → document → application), longa e implícita demais — ficamos com **dois níveis: tela e corredor**. E rejeitamos o turno estritamente síncrono da IVR: no WhatsApp a URA manda duas mensagens fora de ordem e um humano interrompe no meio, então `nomatch` **não** se infere de "resposta do turno atual" — casa-se explicitamente contra o menu vigente.
**Como o juiz inspeciona:** abre a DTD (o `count` está lá, verbatim) e o §11.2 da NOTE 1.0, e confere que GB-2 reproduz o reset na reentrada.

---

## 17. O QUE SAIU, E QUANDO VOLTA

| Frente | por que saiu | gatilho de retorno |
|---|---|---|
| A guarda única `o_grupo_pode_saber` | é o coração da **EXTRA-001.3**, e duas SPECs escrevendo a mesma guarda é motor paralelo | 001.3. 🔴 **Protocolo de colisão (§7.3):** quem executar primeiro **cria**; quem executar depois **chama**. Esta SPEC entrega o campo `pausa_humana` e a causa |
| Modelos de dossiê (🆘 · 🚨 · ✅ · 📊) e números da casa | 001.3 | 001.3 |
| Derivar os 28 órfãos restantes um a um | a camada 1 do bloco A cobre todos em runtime; derivar 28 à mão é trabalho sem efeito material hoje | a régua acusando um passo calado, ou um acionamento real falhando num deles |
| Leitor da fila `tela_cega` (P-264) | a SPEC-087 é dona; e a regra é **não criar fila sem leitor** | a SPEC que fechar o leitor |
| Schema do formulário nativo Porto/Azul | 🧑 depende de acionamento real (P-PILOTO-05) | o primeiro acionamento real de cada uma |
| Trocar a chave `anchor`/`reply` dos passos por um DSL melhor | refatoração sem efeito no segurado; e `arquivo-hub` com 805 passos não se mexe por gosto (§9.1) | uma SPEC de fábrica de rotas que precise disso |

⚠️ Nada da §2 sai em silêncio. Conflito material na conversão → proposta escrita em `CHANGE-ADDENDA.md` com problema, evidência, consequência e autorização.

---

## 18. DEPENDÊNCIAS E ORDEM NA FAMÍLIA (diagnóstico §12.1)

```
001.0 retroativa  →  001.6-P0  →  001.1  →  001.2  →  001.3  ∥  ►001.4◄  →  001.6  →  001.7
```

- **Não depende de ninguém.** É paralela à 001.3 (§12.1 do diagnóstico), e pode ser executada antes dela.
- **Colisão declarada com a 001.3, e ela está resolvida por protocolo, não por juízo:** a guarda única `o_grupo_pode_saber` é **uma só**. Quem executar primeiro a **cria**; quem executar depois a **chama** e acrescenta a sua causa. Esta SPEC entrega o campo `session["pausa_humana"]` (a causa) e o `dossier_sent` como condição da linha de retomada. 🔴 O item 1 do BLOCO 0 de **ambas** é verificar se a função já existe.
- **Deixa para a 001.7 (o piloto medido):** 🔴 as linhas `agente.*` em `work_events`. Sem elas, o desempenho do Cérebro é inauditável e **nenhuma nota do piloto passa de palpite**. Esta é a dependência mais importante da família e ela está no bloco D6.
- **Deixa para a 001.10 (vidros):** o padrão "ler a tela antes de escolher a opção" (camada 1 do bloco A) é o mesmo princípio do *"perguntar só o que restringe o catálogo daquela apólice"* (§10.4 do diagnóstico). Não é código compartilhado; é a mesma doutrina.
- **Não bloqueia:** a coleta dirigida do canário produz telas que alimentam o corpus de todas as seguintes.

---

## 19. DEFINIÇÃO FINAL DE CONCLUSÃO — a lista fechada

A SPEC está concluída quando **todos** os itens abaixo forem verdadeiros, cada um com evidência no relatório:

```
□  BLOCO 0 com a matriz premissa → observação → comando → decisão
□  a TRIAGEM NOMINAL dos 3 testes vermelhos de hoje: pré-existente · regressão de 08–10/09 ·
   defeito desta SPEC — um veredito por teste, demonstrado na base E no head
□  BLOCO 0-bis: corpus com setembro · LINHA-DE-BASE-DE-ROTAS.json commitada · INDICE.md com 16
□  a causa das 0 linhas de `agente.*` está ESCRITA, com o comando que a produziu
□  a resposta de §8.5 (caso ① ou caso ②) está escrita, com a consulta
□  as três contagens do dialeto do normalizador estão lado a lado
□  `parse_options` no menu real: cru → 0 · normalizado → 3 (ou o número medido)
□  A · resolver_tecla no motor; qual_seguro_opcao derivado; os 29 órfãos classificados
□  B · reparo determinístico, uma vez por tela, sem consumir tentativa; Cérebro informado;
      tentativas por tela com teto de sessão
□  C · pausa de 60 s renovável (máx 2), AGENTE e EU CUIDO, os NOVE gatilhos calados
□  D · âncora positiva; needs_human reentra; pergunta ao segurado e volta; dois relógios;
      insurer_closed reconhece a Allianz; work_events com linhas `agente.*`
□  E · azul e porto consertadas; homônimos medidos; corpus, régua, inventário e roteiro regenerados
□  os 12 guardas verdes, e cada MUTAÇÃO demonstrada VERMELHA em subprocesso nomeado
□  GT · dois tenants, mesma seguradora, uma em pausa: nada atravessa (CLAUDE.md §7)
□  régua `medir_rota.py --todas --com-espelho` sem regressão contra a linha de base
□  replay Allianz 10/09 → "1" · mutação "residência" vermelha
□  replay Vivian a partir de needs_human → resumo em ≤ 30 s
□  bateria inteira (`python tests/run_all.py`, com `PYTHONIOENCODING=utf-8`) rodada 2–4 vezes,
   com a contagem no relatório e o número de vermelhos ANTES e DEPOIS
□  painel de 3 lentes + red team + juiz fresco, com os achados e o que foi rebaixado, por escrito
□  canário: coleta dirigida com TESTE-A, percorrida até a confirmação e RECUSADA
□  `git push origin HEAD:main` com a saída colada; SHA remoto conferido
□  PENDENCIAS, FOUNDER-DECISIONS, CHANGE-ADDENDA, ESTADO-DAS-SPECS e dossiê atualizados
□  declaração explícita: nenhum motor paralelo foi criado (CLAUDE.md §5), com a lista da §3.1
```

**O resumo ao Founder responde, em língua de gente:** o que mudou para quem aciona · o que foi realmente testado com seguradora real e onde parou · o que ficou desligado por autorização · que falhas ainda impedem uso · qual é a única próxima ação necessária. ⛔ Não atribuir "testado em produção" a uma suíte verde nem a uma leitura de código.
