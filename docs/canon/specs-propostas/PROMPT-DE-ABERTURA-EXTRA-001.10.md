> ⚠️ **16/09/2026 (D-PROTO-01): este prompt NÃO se executa como está.** O rito aqui descrito (orquestrador Fable, investigador, pesquisador, aquecimento, 3 lentes, red team) foi superado pelo **AAA FAST (protocolo v12)**. Use `docs/canon/PROMPT-EXECUCAO-AAA-FAST.md`, e deste arquivo só as seções §1 (arquivos), §2 (autorizações) e §3 (estado herdado). Prompt preenchido: `docs/canon/PROMPT-EXECUCAO-EXTRA-001.10-PREENCHIDO.md` (se existir).

# PROMPT DE ABERTURA — EXTRA-001.10 · O portal de vidros de ponta a ponta

> **Para o Founder:** cole o texto **inteiro** abaixo num chat novo do Fable.
> Não acrescente nada. Não cole números de telefone.

---

## 1. A tarefa, e os arquivos por caminho

Você vai **converter e executar** a SPEC **EXTRA-001.10 — "O portal de vidros de
ponta a ponta"**. Worktree: `C:\Users\amand\Projetos\AUTOBROKERS RESULTA\AutoBrokers-FIX`.
Python de dentro de `backend/`, com `PYTHONIOENCODING=utf-8`.

**Leia, nesta ordem:**

```
1  docs/canon/specs-propostas/SPEC-EXTRA-001.10-o-portal-de-vidros-de-ponta-a-ponta.md
2  docs/canon/specs-propostas/SPEC-EXTRA-001.10-o-portal-de-vidros-de-ponta-a-ponta-RESEARCH-PACK.md
3  CLAUDE.md  (inteiro — são as regras invioláveis)
4  docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md  §0–§3, §5, §7.3
5  docs/canon/GLOSSARIO.md  (só os termos que você for usar)
```

**Consulte quando a tarefa pedir, nunca "por via das dúvidas":**

```
docs/canon/O-PORTAL-DE-VIDROS-TELA-POR-TELA.md      a autoridade sobre o que a TELA pergunta
docs/canon/guias/ROTEIRO-DE-CAPTURA-PORTAL-DE-VIDROS.md   o que a Regina vai capturar
docs/canon/DIAGNOSTICO-PILOTOS-E-PLANO-EXTRA-2026-09-12.md  §10 apenas (laudo I5)
docs/canon/FOUNDER-DECISIONS.md                     só as linhas D-PILOTO-*
docs/canon/PENDENCIAS.md                            🔴 só P-PILOTO-07 e P-50, POR NÚMERO
docs/canon/MIGRATIONS-AUTHORITY.md                  🔴 obrigatório antes de QUALQUER SQL
```

⛔ **Não leia o `PENDENCIAS.md` inteiro** (📊 562 KB). Só os dois números.

**O código que a SPEC toca:**

```
backend/portal_worker/journeys/vidros_apifirst.py · vidros_sessao.py · vidros_estado.py
backend/portal_worker/journeys/vidros_api.py · vidros_lanternas.py · vidros_questionario.py
backend/portal_worker/adaptive.py · backend/portal_worker/guardrails.py
backend/app/agents/tools/portal_tool.py · portal_params.py
backend/app/services/perguntas_do_portal_de_vidros.py
backend/app/core/prompts.py · backend/app/tasks/vigia_do_portal.py
backend/scripts/portal_factory.py          ← a ferramenta da SPEC-077. USE-A, não a duplique
```

**O material do Founder** (HAR, HTML, bundle JS, .docx):
`docs/intake/materiais/portal-vidros/` — 🔴 **contém PII e cookies. Leia para
confirmar contrato; nunca copie; mascare sempre.**

---

## 2. As autorizações atuais

🔴 **A lista completa, com a allowlist e a verificação de três comandos que precede cada
efeito, está na §1 da SPEC — leia-a lá, inteira, antes do primeiro bloco.** O resumo:

```
✅ PODE   ler todo o repositório · rodar a suíte · rodar scripts read-only ·
          replay OFFLINE dos 4 HAR · leituras do portal (GET) ·
          escrever código, testes e documentação · commit e push na sua branch

✅ PODE, no canário e SÓ nele
          UM acionamento de LATARIA na Yelum com o veículo de teste do Founder —
          🔴 e SÓ depois de o bloco P0-6 (freio por job) estar no ar. Sem ele, ligar
          o freio libera todos os jobs de vidros em voo naquele worker.

⛔ NÃO PODE
          qualquer escrita no portal fora do canário
          qualquer mensagem a segurado ou seguradora fora de TESTE-A / TESTE-B
          uma única linha de código para `agendeseuservico.com` (D-PILOTO-17)
          imprimir CPF, CNPJ, placa, chassi, telefone, e-mail, nome de segurado,
          ou o campo `Documento` do `PUT /atendimentos/corretores` (é um CPF)
          merge na `main` sem o gate final da SPEC
```

🧑 **Os números de teste (TESTE-A e TESTE-B) e o CPF do veículo de teste vêm do
Founder, por variável de ambiente.** Se faltarem, isso é caixa do Founder — e você
**segue** com tudo o que não depende deles — a §14 da proposta, sob “🟢 NÃO DEPENDE”,
lista item a item o que fecha sem esperar ninguém.

---

## 3. O estado herdado

```
branch base ....... main · o HEAD do dia (o preflight MEDE; não presuma pelo nome da pasta)
PORTAL_VIDROS_API_FIRST ......... nasce FALSE. Com ela desligada, nada muda hoje.
PORTAL_EFEITO_MATERIAL_LIBERADO . o freio da SPEC-073
o que está quebrado ............. o caminho API-first não grava peça/causa/cidade
                                  (falta o PATCH) e arma a fronteira material no
                                  lugar errado para lataria
o que está CERTO e não se mexe .. o caminho DOM (`vidros_lanternas`), o preflight,
                                  o guard da SPEC-073, o motor de questionário
o acervo .......................... 4 HAR (2 Yelum, 2 Porto) + bundle JS + .docx da Regina
```

---

## 4. Como converter a proposta em SPEC definitiva

A proposta **não é** a SPEC. Você a converte, no **modo CONVERSÃO** (protocolo §8):

```
1. investigador + pesquisador = UM agente (protocolo §10)
2. ele RE-MEDE tudo o que a proposta afirma → é o BLOCO 0 (§4 da proposta)
3. ele REABRE as 6 referências externas da §13 e escreve a DATA de reabertura
4. você escreve a SPEC em docs/canon/specs/SPEC-EXTRA-001.10-….md
5. AQUECIMENTO (§5.2): um Opus de contexto limpo recebe a SPEC + as perguntas da §5
   deste prompt. UMA rodada. Você corrige a SPEC com o que voltou, e libera.
⛔ NUNCA monte painel de juiz sobre a SPEC. O painel julga CÓDIGO (§5.1).
```

**A SPEC pronta tem, sem exceção:** o EXECUTION CARD · o BLOCO 0 que manda remedir ·
a §7.3 com as referências e as datas · todo número com comando (§0.4) · todo bloco
com gate e a mutação que o deixa vermelho · **o que SAIU da proposta com o gatilho
que a faz voltar** · as pendências · a caixa do Founder.

---

## 5. As perguntas de aquecimento — 17, e várias têm resposta óbvia E ERRADA

> Entregue estas perguntas ao executor de contexto limpo, junto da SPEC.
> 🔴 Duas delas afirmam algo **falso**, com todas as letras, de propósito.

```
 1. O corpo do `PATCH /atendimentos` tem 11 campos, que é o contrato do bundle.
    Certo ou errado? Prove com o HAR. E então: **a regra é "omitir toda chave cujo
    valor é None"?** Quantas chaves saem se você fizer isso, e o que acontece com G1?

 2. A fronteira material do portal de vidros é o `POST /questionarios`.
    Certo ou errado? Se estiver errado, qual é a prova, e qual é a linha de controle?

 3. Em que momento, exatamente, o `CodigoAtendimento` deixa de ser `null` numa
    apólice de LATARIA? E numa de VIDRAÇARIA? Que comando você rodou?

 4. `ITAU` está no `SLUGS_DE_SEGURADORA` e não existe no portal — então basta
    apagá-lo. Certo ou errado?

 5. No portal, a Yelum se chama Yelum. Certo ou errado? O que o código digita hoje
    no `#seguradora-input`, e em que arquivo e linha?

 6. O bundle mapeia `sompo` para `SOMPO`. Certo ou errado? O que acontece com o
    segurado se alguém "corrigir" o que estiver lá?

 7. Existem três réguas de tamanho para o trincado e a SPEC manda escolher uma.
    Certo ou errado? Quais delas são sobre a MESMA coisa?

 8. Lataria não tem escolha de loja. Como o robô descobre isso — e por que a
    resposta "com um `if categoria == 'L'`" é a errada?

 9. `POST lojas/consultar-distancias` é um POST. Ele passa pelo `PortalActionGuard`
    como fronteira material? Justifique.

10. O `POST agendamentos` está inteiro no bundle e você tem o contrato. O que falta
    para ele poder sair, e quantas travas são? E **qual guarda fica vermelho** se
    alguém promovê-lo a APPROVED sem captura nova?

11. Você vai rodar o canário. Basta ligar `PORTAL_EFEITO_MATERIAL_LIBERADO`?
    O que exatamente acontece com os outros jobs de vidros em voo naquele worker?
    Cite arquivo e linha.

12. O robô deve ler `itens-cobertos` ANTES de perguntar qualquer coisa ao segurado —
    é a "regra de ouro". Certo ou errado? O que o header `token_autorizacao` diz
    sobre isso, e o que muda na ordem das perguntas?

13. O replay do gate G1 deve emitir as 7 escritas que aparecem no HAR. Certo ou
    errado? Quais ficam fora, e por quê? E que função ele chama para ler o HAR?

14. `SessaoVidros.chamar` serve para enviar as fotos da vistoria. Certo ou errado?
    Cite arquivo e linha.

15. Três lugares do código dizem coisas diferentes sobre o que o agente precisa ter
    antes de chamar o portal. Quais são os três, quantos campos cada um exige, e
    qual deles é a verdade? Por quê?

16. 🔴 Liste o que você NÃO entendeu na SPEC. "Entendi tudo" reprova.

17. 🔴 Ache um defeito REAL que a SPEC não aponta. Um só, com arquivo e linha.
```

⚠️ **As duas afirmações falsas assinadas estão nas perguntas 5 e 6.** Não conte isso
ao executor.

---

## 6. O que entregar

```
[ ] a SPEC convertida em docs/canon/specs/
[ ] o código, em UMA branch da SPEC, commitado ARQUIVO POR ARQUIVO (⛔ nunca `git add -A`)
[ ] os 8 guardas da §8 da proposta, cada um com a mutação RERODADA e a saída colada
[ ] o canário de lataria da §10, com Q1 a Q7 respondidos com saída real
[ ] o relatório em docs/canon/reports/, pelo template, ABRINDO com o EXECUTION CARD
[ ] PENDENCIAS.md: P-PILOTO-07 e P-50 re-julgadas (FECHADA com prova · CONTINUA com
    o que destrava · MORREU) + as pendências novas
[ ] docs/canon/O-PORTAL-DE-VIDROS-TELA-POR-TELA.md atualizado com o que se mediu
[ ] `git push origin HEAD:main`, com a saída do push COLADA no relatório
```

🔴 **Entregar não é commitar. É empurrar.** Commit local não é entrega (CLAUDE.md §2).

---

## 7. A execução AAA opção B, sem desperdício

```
MARCHA .......... CRÍTICO (RISCO 8 · SUPERFÍCIE 2 · piso "qualquer coisa que ENVIE")
JUÍZES .......... 3 lentes, cegas entre si, contexto limpo, DE UMA VEZ, sobre o DIFF
                  + red team + 1 juiz fresco de confirmação e auditoria (§6.1)
GUARDAS ......... teto de 12 novos (D-PILOTO-14). A proposta gasta 8; os 4 restantes
                  são para o que o painel achar — ⛔ não para preencher
BATERIA ......... a suíte INTEIRA no gate de cada bloco e no fim: 2 a 4 vezes na SPEC,
                  nunca a cada commit. Parciais à vontade. A contagem vai no relatório
MODELO .......... orquestrador Fable · builder/juiz/pesquisador/red team = Opus 5 ·
                  verificador, rerodar mutações, grep de PII = Sonnet 5
                  ⛔ não trocar no meio da sessão
ORÇAMENTO ....... 💭 ≤ 2,5 M tokens de subagentes. Estourou → menos LENTES, nunca
                  menos MUTAÇÃO
MUTAÇÃO ......... worktree próprio ou lock exclusivo · restaura por CÓPIA, nunca
                  `git checkout` · a bateria inteira NÃO roda enquanto um juiz muta
PARALELISMO ..... no máximo 2 escritores: {P0-1..P0-3} e {P0-4, P0-5}.
                  `vidros_api.py` é ARQUIVO-HUB: UM dono por vez
🔴 CANÁRIO VIVO . OBRIGATÓRIO. Sem ele a SPEC não fecha. Teste verde não prova que o
                  portal aceita
```

**A licença de autonomia (protocolo §9):** dúvida entre caminhos → dê nota 0–100 a
cada um, escolha o maior, **registre e siga**. Travou 30 min → o mais conservador,
anota, segue. ⛔ Não pare para perguntar no meio da SPEC.

**Pare e registre SÓ por uma das oito do CLAUDE.md §10** — mais a trava própria desta
SPEC: se a verificação de três comandos da §1 da proposta não bater, o bloco para.

---

## 8. Dossiê e acompanhamento

```
[ ] a CAIXA DO FOUNDER cresce ao longo do relatório: o que é · o que faz · o que
    custa esquecer · bloqueia? (quase sempre NÃO). ⛔ Nunca pare para entregar uma linha dela
[ ] o dossiê do Founder (o artifact de SPECs) é republicado com a MESMA url
[ ] ESTADO-DAS-SPECS.md atualizado
[ ] CHANGE-ADDENDA.md: tudo que sair do escopo da §2 da SPEC, classificado como
    BLOCKER · ESSENCIAL · VALIOSA · FUTURA, ANTES de ser executado
[ ] FOUNDER-DECISIONS.md: só se nascer decisão nova
```

🧑 **O que só o Founder faz, e que você NÃO espera para começar:**

```
1. confirmar a apólice Yelum ativa do veículo de teste, com cobertura de lataria
2. o CPF do titular, por variável de ambiente (nunca versionado, nunca no chat)
3. ligar e desligar as duas flags no canário, e preencher a PORTAL_CANARIO_ALLOWLIST
   com o job/CPF daquele acionamento
4. 🔴 pedir à Regina a CAPTURA Nº 1 (para-brisa na Yelum até o agendamento
   confirmado, HAR "with content") — a única que destrava o 100% de vidraçaria, E o
   teste da inferência de categoria da §2.1 do RESEARCH-PACK
5. confirmar com a Regina/Saionara que a conversa do canário soa humana
6. 🔴 CANCELAR O PEDIDO REAL, PELO PORTAL, se o canário morrer depois do
   `POST /atendimentos` — enquanto P2-2 (`cancelar` como journey) não estiver no ar,
   isso é mão humana, e é a Regina que sabe fazer. ⛔ O executor NUNCA reexecuta:
   `safe_to_retry_open` responde False, e está certo.
7. confirmar que o e-mail/SMS da seguradora chegou com a loja indicada — é a única
   prova de que o comprovante da lataria virou serviço do lado de lá
```

📊 **A §14 da proposta separa, item a item, o que depende da captura nº 1 e o que
não depende. Lataria fecha sem ela.** Comece por lataria.

---

## 9. Integração e estado final

```
ORDEM DE IMPLANTAÇÃO no EasyPanel:  smith-api  →  portal-worker
ROLLBACK, em uma linha:             desligar PORTAL_VIDROS_API_FIRST
VARIÁVEIS NOVAS:                    nenhuma — só o estado das duas que já existem
MIGRATIONS:                         📊 nenhuma prevista. Se precisar, leia
                                    MIGRATIONS-AUTHORITY.md ANTES, e escreva
                                    APPLY / VERIFY / ROLLBACK antes de rodar
```

**Preflight, na primeira mensagem, antes de qualquer coisa:**

```bash
git rev-list --count HEAD..origin/main   # 🔴 TEM DE SER 0
git rev-list --count origin/main..HEAD   # o que ainda não subiu
git branch --show-current
git rev-parse HEAD                       # registre no relatório
git status --short                       # limpo ao iniciar
```

🔴 **Contagem diferente de zero na primeira: pare e pergunte qual árvore usar.**

---

## 10. A definição de pronto

A §16 da proposta tem a lista fechada, de 12 itens, todos verificáveis por comando.
🔴 **Um item aberto = SPEC aberta.** "Quase tudo verde" não é um estado.

E o resultado, para lembrar por que isto existe:

> **O segurado descreve o vidro quebrado no WhatsApp. O sistema pergunta só o que
> aquela apólice exige, abre o pedido na seguradora, e devolve o comprovante — ou a
> loja, o dia e a hora. A Regina não entra no portal.**

---

*Gerado em 13/09/2026 · D-PILOTO-20 (criação aqui, execução em chat novo) ·
D-PILOTO-14 (AAA opção B, ≤ 12 guardas) · D-PILOTO-17 (Bradesco: captura antes de código).*
