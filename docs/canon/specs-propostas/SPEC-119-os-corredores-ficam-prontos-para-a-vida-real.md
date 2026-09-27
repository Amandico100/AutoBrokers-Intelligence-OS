# SPEC-119 — Os corredores ficam prontos para a vida real

> **27/09/2026**, sobre `origin/main` = `ff711bd`, branch `spec/119-corredores-prontos`.
> 🔴 **O outcome, numa frase:** a Resulta e a AutoFleet ligam o agente sabendo, por rota, se ele
> atende sozinho — e o que ainda falta nas que não atendem.
>
> 📊 medido · 💭 ilustrativo (CLAUDE.md §12.1)

---

## 0. O EXECUTION CARD

```
OUTCOME ........  o Founder recebe uma lista por rota — ATENDE SOZINHO / HANDOFF / FALTA
                  CAPTURA — provada por simulação sobre telas REAIS, e liga o agente nas duas
                  corretoras sem retrabalho para a Regina e a Saionara

RISCO ..........  8  (ALCANCE o SEGURADO 3 · REVERSIBILIDADE saiu do prédio 3 · FREQUÊNCIA 2)
SUPERFÍCIE .....  3  (território não mapeado: 73 rotas, o classificador do acervo, uma classe
                  nova de passo e cinco baterias de simulação — não sei apontar TODOS os lugares)
PISO APLICADO ..  §3.2 — qualquer coisa que ENVIE mensagem/acionamento → CRÍTICO no mínimo
NÍVEL ..........  🔴 CRÍTICO · builders Opus 5 xhigh · juiz Opus 5.5 ‖ red team Opus 5.5 ·
                  🔬 lente do dado (a SPEC publica números de `observed_events`) ·
                  1 rodada + 1 confirmação curta

O FIO ..........  §2
PARALELISMO ....  F1 → F2 em série (F2 consome o classificador da F1) ‖ F3 (arquivos disjuntos)
                  → F4 (a costura e as provas) → F5 (a página e o painel)
UNIDADES .......  5 fatias, §5
COESÃO .........  o classificador e o gerador do corpus são o mesmo domínio → F1 e F2 vizinhas,
                  em série, nunca no mesmo builder (arquivos diferentes, dono único cada)
TIME ...........  5 builders frescos · juiz ‖ red team UMA vez · ESCALAÇÃO se a F3 reprovar 2×
REFERÊNCIA .....  interna: `porto-auto.jsonl` — 📊 524 telas com 21 `(vazio)`, a mediana do que
                  um corpus BEM classificado parece · externa:
                  `docs/canon/O-FORMULARIO-NATIVO-RESOLVIDO.md` §5 (medir com linha de controle)
GATES ..........  §6
O ELO ..........  a afirmação-título é "rotas ficam SEM CORPUS porque o CLASSIFICADOR é cego,
                  não porque falta conversa". §3 mede A, mede B e mede que B chega em A.
FAIXA DE RELÓGIO  💭 sem teto declarado pelo Founder. 3 baterias autorizadas.
                  Tetos de contexto: 250 turnos por builder.
ORÇAMENTO ......  🔴 US$ 4 na OpenAI (as simulações com o agente REAL) · US$ 5 na Anthropic
                  (Vigia/Sentinela/Cérebro). ⛔ Parar e declarar ao cruzar 80% de cada teto.
```

---

## 1. POR QUE ESTA SPEC EXISTE — o que o Founder disse, e o que eu medi

> *"Como pode ter 72 pedidos e não ter o corredor? É um absurdo."*

📊 **Ele estava certo sobre o essencial e enganado por um rótulo nosso.** Duas medições de 27/09:

**① A coluna DEMANDA é por SERVIÇO, não por rota.** `medir_rota.py:275` faz
`demanda.get(n.rota.servico)` e a fonte é uma lista fixa
(`padroes_de_servico.py:543`): `("guincho", 72, 197)`. **O mesmo 72 aparece nas 10 linhas de
guincho.** `mapfre/auto/guincho · 72` nunca significou 72 acionamentos na Mapfre. O Founder passou
meses achando que tinha 72 conversas para copiar — **e o documento dizia que tinha**.

**② As conversas EXISTEM. O classificador é que é cego.** 📊 Contra os 10 telefones de assistência
que o Founder forneceu, em `observed_events`:

| seguradora | sessões | eventos | última |
|---|---:|---:|---|
| allianz | **163** | 14.919 | 25/09 |
| porto | **142** | 4.699 | 21/09 |
| yelum | 79 | 4.675 | 22/09 |
| tokio | 54 | 447 | 21/09 |
| hdi | 45 | 3.127 | 24/09 |
| azul | 19 | 829 | 28/07 |
| bradesco | **17** | 472 | 09/09 |
| zurich | **15** | 672 | 18/09 |
| mapfre | **12** | 186 | 21/08 |
| alfa | 9 | 264 | 15/07 |

**555 sessões.** 🔴 E o corpus versionado as tem — sem etiqueta:

```
mapfre-auto.jsonl   113 telas · 100 com servico (vazio)  · só carro_reserva classificado
zurich-auto.jsonl   253 telas · 217 (vazio)              · só 36 em guincho
bradesco-auto.jsonl 192 telas · guincho 89 · bateria 36  · 27 (vazio)
porto-auto.jsonl    524 telas · bem classificado         · só 21 (vazio)   ← a REFERÊNCIA
```

**③ A causa, nomeada.** `servico_da_sessao` (`padroes_de_servico.py:417`) é uma cascata de três
níveis, e dois deles são listas estreitas:
- `MENUS_DE_SERVICO` é **por seguradora** (`if menu["seguradora"] != seguradora: continue`).
  📊 **A Mapfre é a ÚNICA sem entrada.** A Zurich tem uma, e ela cobre 36 de 253 telas.
- `PADRAO_OURO` tem **2 padrões**, globais, para 10 seguradoras:
  `^servi[çc]o\s*:\s*(…)` e `sua solicita[çc][ãa]o de (…) foi aberta`. Quem não escreve assim
  não é classificado.

⛔ **Nada disso é falta de dado nem arquitetura errada. São três listas que ninguém alimentou.**

**④ A dependência circular dos apelidos.** O item *"apelidos do jeito que o cliente fala"* (4 pts,
10 rotas) exige três apelidos vivos do **Espelho** — que só enche com o **agente ligado**. E o
agente não liga porque as rotas não pontuam. 🔴 **A rota não pode pontuar até o agente estar
ligado, e o agente não liga até a rota pontuar.**

**⑤ A régua premia o que deveria punir.** Existe um item *"100% determinístico"*, 8 pontos. 📊 Mas o
CLAUDE.md §9.5 registra **oito** casos em que o corredor **casou a tela e respondeu errado** —
todos verdes. Determinismo é obrigatório onde a resposta **DECIDE** (serviço, ramo, aceitar custo);
é desperdício onde ela só **CONDUZ** (confirmar, informar endereço, navegar). A régua não distingue,
e por isso empurra o produto para a super-determinação que trava o Founder.

---

## 2. O FIO

```
 ①  a conversa da Regina/Saionara com a URA     observed_events (555 sessões)
 ②  o classificador etiqueta o serviço          scripts/padroes_de_servico.py::servico_da_sessao
                                                🔴 ELO ROTO 1 — cego para mapfre/zurich (F1)
 ③  o corpus versionado nasce                   scripts/gerar_corpus_de_telas.py
                                                🔴 ELO ROTO 2 — teto de 5 sessões por rota (F2)
 ④  a régua mede a rota                         scripts/medir_rota.py + rubrica.py
                                                🔴 ELO ROTO 4 — demanda global e nota única (F5)
 ⑤  o corredor responde a tela                  corridor_playbooks.py::match_ura_step
                                                🔴 ELO ROTO 3 — DECIDE e CONDUZ tratados igual (F3)
 ⑥  o que ele não conhece                       unknown_step_policy: adaptive_then_handoff
 ⑦  o destravamento                             Vigia → Sentinela → Cérebro
                                                ⚠️ NUNCA rodou com tráfego real (F4)
 ⑧  a pessoa, com dossiê                        human_handoff
 ⑨  o Founder decide se liga                    o painel — hoje com nota única e coluna mentirosa
```

🔴 **O TESTE DO FIO (1ª entrega da F4):** uma sessão REAL da Mapfre atravessa ② → ⑤ e a rota
`mapfre/auto/guincho` sai de `SEM_CORPUS`. Nasce VERMELHO.

---

## 3. O ELO — medido nas três pontas

```
A (o efeito) ..... `mapfre/auto/guincho` = SEM_CORPUS na régua de 26/09
B (a causa) ...... a Mapfre não tem entrada em MENUS_DE_SERVICO; 100 de 113 telas sem etiqueta
B chega em A? .... 🔴 É O QUE A F4 PROVA: com a entrada da Mapfre escrita a partir das 12
                  sessões dela, a mesma rota passa a ter corpus e nota. Sem essa terceira
                  medição, são duas medições certas e uma causa suposta (protocolo §0.3).
```

---

## 4. O QUE ESTA SPEC **NÃO** FAZ

```
⛔ não inventa tela, tecla, âncora ou apelido que o acervo não mostre
⛔ não afrouxa o determinismo onde a resposta DECIDE conteúdo (CLAUDE.md §9.5)
⛔ não liga agente nenhum — quem liga é o Founder
⛔ não promete que a Tokio atende: ela vira link (📊 52%), e isso já é handoff pela SPEC-118
⛔ não mexe no Portal de Vidros
⛔ não cria peça nova de runtime (Jev fica como opção registrada, nota 60, fora do escopo)
```

---

## 5. AS FATIAS

### F1 · O CLASSIFICADOR DEIXA DE SER CEGO
**Arquivos:** `backend/scripts/padroes_de_servico.py` ·
`backend/tests/test_o_classificador_ve_as_dez_seguradoras.py` (NOVO)

1. **Entrada de `MENUS_DE_SERVICO` para a MAPFRE**, lida das 12 sessões dela no acervo.
2. **Ampliar a entrada da ZURICH** (📊 36 de 253 hoje) e conferir as outras oito.
3. **Ampliar `PADRAO_OURO`** com as formas que as outras seguradoras usam de fato.
4. 🔴 **Guarda com linha de controle:** cada seguradora classifica ≥ X% das telas que pedem
   serviço, **e** um rótulo que a seguradora não nomeia continua saindo `?rotulo` (é achado, não
   ruído — `nivel-1a-rotulo-desconhecido` já existe e **fica**).
⛔ Nenhum padrão sai da cabeça: cada um vem com a sessão e a frase real ao lado.

### F2 · O ACERVO INTEIRO ENTRA
**Arquivos:** `backend/scripts/gerar_corpus_de_telas.py` · `backend/tests/corpus/telas_reais/**` ·
`backend/tests/test_o_corpus_nao_joga_sessao_fora.py` (NOVO)

1. 🔴 **O teto de 5 sessões por rota sobe** (ou sai, com a decisão medida): 📊 hoje ele descarta
   sessões com desfecho — `zurich-auto` avisa *"5 sessão(ões) FORA do corpus pelo teto"*.
2. **Regerar com as 555 sessões** e os 10 telefones do Founder. ⚠️ O corpus é **global por
   seguradora+ramo** (decisão do Founder) e **mascarado** — a contagem `marcas_de_corretora() = 8`
   é o CONTROLE de que a geração rodou COM banco.
3. **Investigar as sessões que continuarem sem etiqueta** e dizer, por seguradora, o motivo.

### F3 · DECIDE × CONDUZ — a classe de passo que liberta o agente
**Arquivos:** `backend/app/services/corridor_playbooks.py` ·
`backend/app/services/insurer_dispatch_service.py` ·
`backend/tests/test_o_passo_que_decide_e_o_passo_que_conduz.py` (NOVO)

1. Todo passo de URA ganha uma classe: **`decide`** (escolhe serviço, ramo, aceita custo, confirma
   irreversível) ou **`conduz`** (navega, confirma sem consequência, ecoa dado que o caso já tem).
2. **`decide`** exige tecla/âncora observada — **como hoje, sem afrouxar nada**.
3. **`conduz`** sem tela conhecida passa a ser respondido pelo **agente, com o contexto do caso e a
   tela REAL na frente**, em vez de travar. ⚠️ Com teto de tentativas e **handoff** se não resolver.
4. 🔴 **A classificação sai da EVIDÊNCIA, nunca de adjetivo:** a tela oferece alternativas de
   CONTEÚDO? → `decide`. O CLAUDE.md §9.5 é a régua: *"Navegar e decidir têm a mesma forma no
   código e resultados opostos na vida do segurado."*
5. 🔴 **Guarda:** as oito respostas erradas históricas (tecla do eletricista na tela do encanador,
   condomínio virando residencial, idade do aparelho afirmada, CEP como protocolo…) **continuam
   vermelhas**. É a linha de controle desta fatia — se uma passar, a fatia reverte.

### F4 · AS PROVAS — cinco baterias que eu rodo sozinho
**Arquivos:** `backend/tests/` (novos) · `backend/scripts/simular_corredor.py` (NOVO)

| # | a bateria | o que decide |
|---|---|---|
| **1** | 🔴 **Apelidos contra o agente REAL.** As palavras que o cliente usa ("reboque", "carro não pega", "estourou o pneu", "pia entupida") vão ao agente e ele tem de escolher o subserviço certo | **mata o item circular** de 10 rotas. ⚠️ Custa OpenAI — medir o gasto |
| **2** | **O simulador de corredor**: cada rota atravessada com as telas **REAIS** do corpus, tela a tela, conferindo as DUAS perguntas do §9.5 (casou? **e a resposta está confirmada?**) | a lista ATENDE SOZINHO / HANDOFF |
| **3** | **O formulário da HDI/Yelum simulado** fora do WhatsApp, com a captura real | fecha o que a SPEC-118 deixou sem prova local |
| **4** | **Vigia → Sentinela → Cérebro** com um travamento forçado | 📊 nunca rodaram com tráfego real. ⚠️ Custa Anthropic |
| **5** | **Condomínio · empresarial · sinistro** → handoff com dossiê correto, em português | o Founder pediu explicitamente |

🔴 **Toda bateria tem linha de controle**: um caso que **tem** de falhar. Sem ela a bateria não
prova nada (CLAUDE.md §9.2).

### F5 · A PÁGINA DEIXA DE CONFUNDIR
**Arquivos:** `backend/scripts/medir_rota.py` · `backend/scripts/rubrica.py` ·
`docs/canon/painel-do-founder/**` · `docs/canon/reports/**` · os canônicos

1. 🔴 **A coluna DEMANDA passa a ser POR ROTA** (seguradora × ramo × serviço), medida em
   `observed_events`. Onde não houver, escreve `—`, **nunca o número global**.
2. **Nota em porcentagem**, não `58/76` — os denominadores variáveis confundem por construção.
3. 🔴 **DUAS PERGUNTAS, não uma:**
   ```
   DÁ PARA LIGAR?   chegou ao fim ≥1× · nenhuma constante decide conteúdo sem evidência ·
                    o handoff funciona · passou na bateria 2     → SIM / NÃO / FALTA CAPTURA
   QUALIDADE        a régua, em %                                 → 0–100, para priorizar
   ```
4. **A aba CORREDORES reescrita**, sem histórico misturado, em três faixas: **ATENDE SOZINHO ·
   QUASE, e falta o quê · PRECISA DE ACIONAMENTO DA REGINA/SAIONARA**.
5. Relatório, pendências, decisões, addenda, `ESTADO-DAS-SPECS`.

---

## 6. OS GATES

```
G1  📊 nenhuma seguradora com > 25% das telas de serviço sem etiqueta (hoje: mapfre 88%, zurich 86%)
G2  🔴 `mapfre/auto/guincho` sai de SEM_CORPUS — com a sessão nomeada
G3  o TESTE DO FIO verde, e provadamente VERMELHO antes
G4  🔴 NENHUMA rota perde o patamar. Corpus novo muda notas: o gate é o PATAMAR, não o número —
    e toda queda de patamar vem explicada
G5  as OITO respostas erradas históricas continuam VERMELHAS (linha de controle da F3)
G6  as 5 baterias da F4 verdes, cada uma com a sua linha de controle
G7  mutação dos guardas NOVOS: cada um fica vermelho com o defeito reintroduzido
G8  bateria completa, em `git worktree` SEPARADO (P-118-14), triada contra o COMMIT BASE
G9  `conferir_o_que_esta_no_ar.py` → BATE depois do push
G10 🔴 a aba CORREDORES com a lista por rota, e ZERO informação de data anterior sem rótulo
G11 📊 gasto de API declarado, dentro de US$ 4 (OpenAI) e US$ 5 (Anthropic)
```

⚠️ CLAUDE.md §9.1 (`test:rotas-montam` + `next start`) **não** se aplica: nada de `app/` do Next,
`middleware.ts` ou `next.config.js`.

---

## 7. AS PENDÊNCIAS QUE JÁ NASCEM DESTA SPEC

| # | o que | de quem |
|---|---|---|
| P-119-01 | a Tokio segue handoff (é link — 📊 52%) | 🧑 decisão futura |
| P-119-02 | rotas que continuarem sem UMA tela no acervo depois da F1/F2 | 🧑 acionamento dirigido |
| P-119-03 | Jev para URA desconhecida (nota 60, fora do escopo) | 🧑 |
| P-119-04 | `BATERIA-LINHA-DE-BASE.txt` vencida (lista 35, cabeçalho diz 47) | 🤖 regravar |
