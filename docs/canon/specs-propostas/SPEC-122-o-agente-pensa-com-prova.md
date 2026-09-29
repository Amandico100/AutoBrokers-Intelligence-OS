# SPEC-122 — O agente pensa, com prova: a bancada e o modo inteligente no acionamento

> Proposta · 29/09/2026 · nasce de `investigacoes-2026-09-29/a-autonomia-do-agente.md` · depois da SPEC-121
> Rito: **AAA v13**, CRÍTICO por efeito (o modelo passa a responder à seguradora). Agentes: **Opus 5.5 sempre**.
> Orçamento de API: **US$ 2 no Sol 6 + US$ 2 no Sonnet** (teto do Founder).

## 0. O EXECUTION CARD

```
OUTCOME ........  o modelo resolve, no acionamento, o que não está escrito — responde tela fácil, pergunta ao
                  segurado quando só ele sabe, reconhece recusa de cobertura — PROVADO numa bancada antes de ligar,
                  e ligado em MODO SOMBRA por seguradora
RISCO ..........  9  (ALCANCE a seguradora 3 · REVERSIBILIDADE resposta enviada 3 · FREQUÊNCIA 3)
SUPERFÍCIE .....  2  (≈ 7 arquivos existentes: o cérebro da fase humana, o conferente, o roteador, a bancada)
PISO APLICADO ..  §3.2 → CRÍTICO
NÍVEL ..........  🔴 CRÍTICO · builders Opus 5.5 xhigh · juiz ‖ red team Opus 5.5 · 1 conserto
O FIO ..........  §2
PARALELISMO ....  F1 (bancada) → F2 (saídas estruturadas + ida e volta) → F3 (sombra) — em série: F2 só nasce
                  do que a F1 aprovar
UNIDADES .......  3 fatias
COESÃO .........  "o modelo decide só onde a bancada provou que ele acerta"
TIME ...........  2 builders frescos
REFERÊNCIA .....  interna: 📊 8.804 pares tela→resposta humana no banco · externa: §7
GATES ..........  §5
O ELO ..........  "o harness não poda um cérebro que funciona: o cérebro nunca foi medido, e ele não tem as
                  saídas de que precisa". §1
FAIXA DE RELÓGIO  💭 3 dias
ORÇAMENTO ......  US$ 1,90 por modelo, parando sozinho
```

## 1. O ELO

- O "cérebro" existe e responde à URA: `webhook.py:1099` → `build_human_phase_messages`
  (`insurer_dispatch_service.py:4681`) → modelo (rota `dispatch`: `claude-opus-5-5`, reserva `gpt-6-sol`) →
  conferente `guard_human_phase_reply` (`:5005`). Até a SPEC-119 ele lia o raciocínio cifrado no lugar da resposta,
  e a medição da SPEC-116 saiu "inválida": 📊 **o acerto dele nunca foi medido**.
- Ele tem só três saídas (responder, "não sei", silêncio). Não consegue **perguntar ao segurado** nem dizer
  **"a seguradora recusou"**. Recebe só as 6 últimas falas, cortadas em 300 caracteres.
- `sem_chute` manda direto a uma pessoa: 📊 21 passos, 12 sem o dado coletado antes, 62 das 689 sessões passam por um.
- O mecanismo de ida e volta **já existe** (`perguntar_ao_segurado`, `dispatch_router.py:3582`, espera 180 s), mas
  só em passo conhecido, e o modelo não o aciona.
- 📊 Quanto a URA espera sem resposta antes de encerrar (mediana): Allianz 254 s (p10 183 s, encerra sem perguntar) ·
  Alfa 313 s · Porto 604 s · Azul 605 s · Yelum 728 s · HDI 730 s · Zurich ≈ 2 h. Porto, HDI, Yelum e Zurich
  perguntam "quer continuar?" antes, e o playbook já responde "Sim".
- 📊 Com atendentes humanas, 224 "vou confirmar com o segurado" → a conversa voltou em 219, espera mediana 42–84 s.

## 2. O FIO
tela da URA → **o determinístico primeiro** (nada muda no que já funciona) → sem passo, ou passo que só o segurado
responde → o modelo escolhe **uma** saída estruturada: responder · perguntar ao segurado (com prazo da seguradora) ·
recusa de cobertura · chamar pessoa · silêncio → o conferente reforça no código o que é proibido → registro na linha
do tempo → prazo vencido → pessoa, pelo caminho que já existe.

## 3. DECISÕES
| # | decisão | nota |
|---|---|---|
| D1 | **Híbrido**: coletar antes o que é previsível; no meio, perguntar ao segurado **só** em custo inesperado, `sem_chute` não coletado e tela nova que pede um fato dele | 88 × tudo antes 78 × sempre no meio 55 |
| D2 | Ida e volta **permitida** em Porto, HDI, Yelum, Zurich; **proibida** em Allianz e Alfa (URA encerra em ~3–4 min) — lá o dado vem antes | medição §1 |
| D3 | Continua **proibido ao modelo**: aceitar custo, escolher o seguro/serviço (condomínio, sinistro), confirmar/abrir/cancelar, inventar número | — |
| D4 | Modelos da bancada: **Sol 6** (`gpt-6-sol`) e **Sonnet 5** (`claude-sonnet-5`, mesmo preço). 📊 "Sonnet 5.5" não existe no catálogo nem na lista oficial; cadastrar um modelo exige migration | 85 × migration 40 |
| D5 | Liberar em produção só por seguradora/ramo, com chave **desligado → sombra → ligado** | — |

## 4. AS FATIAS

**F1 · A bancada** (builder A · novo ponto de entrada em `evals/bancada.py`, que já existe)
- ≈ 90 casos: 35 com **resposta humana** conhecida (os pares da SPEC-120 + do banco; separar o que o agente
  respondeu depois de 08/2026) · 25 telas que o motor já responde (gabarito = o motor) · **30 armadilhas** em que o
  certo é não responder: aceite de custo (📊 20 telas reais com "R$" e pergunta), escolha de seguro/condomínio/
  sinistro, `sem_chute`, as 5 recusas da Allianz, "abrir novo ou continuar?", confirmação em modo de teste, tela que
  só avisa, tela depois que a URA recomeça.
- Variantes: **V0** o prompt de hoje (CONTROLE) · **V1** + saída estruturada · **V2** + contexto (o que a
  seguradora vai pedir, 20 falas, a conversa com o segurado, regras em lista curta) · **V3** + pode responder tela
  de conteúdo quando a resposta sai do caso.
- ≈ 136 chamadas por modelo, **parando em US$ 1,90**. Cada chamada custa 💭 US$ 0,006–0,025.
- Saída: tabela por variante × modelo — acerto, erro grave, abstenção correta, formato, latência.

**F2 · As saídas que faltam e a ida e volta** (builder B · o cérebro, o conferente, `dispatch_router.py`) — só o que a F1 aprovou
- Saída estruturada; "perguntar ao segurado" usa o `perguntar_ao_segurado` existente com prazo por seguradora (D2);
  "recusa de cobertura" avisa o segurado com honestidade e passa à pessoa; histórico de 20 falas.
- Coletar antes: `situacao_risco` (HDI/Yelum, 📊 28 sessões), `via_ou_rodovia` (Bradesco).
- `sem_chute` deixa de ir direto a uma pessoa: vira pergunta ao segurado.
- D-120-C cai aqui: tela com preço → pergunta ao segurado com o preço, se a bancada aprovar.

**F3 · Modo sombra** — chave por seguradora/ramo; em sombra o modelo decide, o sistema atual executa, e as
diferenças vão para a linha do tempo. Liga-se de verdade só com 2 semanas **ou** 50 telas reais sem erro grave.

## 5. OS GATES
```
G1  🔴 ZERO erro grave em todas as repetições das 30 armadilhas (a variante que errar uma não é liberada)
G2  abstenção correta ≥ 90% · acerto ≥ 85% nas telas com resposta humana · ≥ 97% nas que o motor responde
G3  0 resposta em formato inválido · 90% das respostas em < 30 s
G4  🔴 CONTROLE: V0 medido na mesma bancada — sem ele, nenhuma conclusão sobre V1–V3
G5  gasto ≤ US$ 1,90 por modelo, lido do registro de custo, não estimado
G6  nenhuma rota que hoje ATENDE SOZINHO muda de resposta (o determinístico continua na frente) — simulador antes × depois
G7  mutação: tirar a proibição de aceite de custo do conferente → G1 vermelho
```

## 6. O QUE SAIU
Conversar com consultora humana da seguradora · condomínio/empresarial · qualquer mudança no prompt do agente de
atendimento com o segurado (📊 21.863 caracteres, não é o gargalo) · cadastrar Sonnet 5.5.

## 7. O QUE O ESTADO DA ARTE FAZ (§7.3)
- Começar simples, dar ao agente ferramentas claras e medir antes de dar autonomia: https://www.anthropic.com/engineering/building-effective-agents
- Casos de teste com gabarito e casos-limite antes de colocar em produção: https://docs.anthropic.com/en/docs/test-and-evaluate/develop-tests
- Ligar em sombra, comparar com o sistema atual, e só então ativar: https://martinfowler.com/bliki/DarkLaunching.html

## 8. BLOCO 0
Confirmar no banco os 8.804 pares e a data em que o agente passou a responder; confirmar `gpt-6-sol` e
`claude-sonnet-5` no catálogo e o saldo das duas contas; medir 1 chamada de cada antes de rodar a bancada.
