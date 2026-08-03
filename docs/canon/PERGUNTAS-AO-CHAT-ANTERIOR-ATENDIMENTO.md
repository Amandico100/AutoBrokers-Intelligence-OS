# Perguntas ao chat anterior — o Atendimento

> **02/08/2026.** Para o Founder copiar e colar inteiro no chat anterior.
> Escrito depois de uma auditoria de cinco frentes no código e no banco de
> produção. **Não peça a ele para re-derivar o que já está medido aqui** —
> peça o que só ele sabe: a intenção, o histórico e a decisão.

---

## COPIE DAQUI PARA BAIXO

Estou com o novo líder técnico do AutoBrokers. Ele fez uma auditoria completa do
atendimento em 02/08/2026, medindo direto no banco de produção
(`dcajcvlzcjbmyapmklil`) e lendo o código no commit `c28daff`.

Ele **não vai mexer em nada do atendimento** antes de entender tudo. Já foi
pego uma vez afirmando algo errado sobre corredores, e por isso está pedindo a
sua ajuda no que não está escrito em lugar nenhum.

**Não precisa repetir o que já foi medido.** Segue o que ele já sabe, para você
não gastar tempo:

```
corridor_templates ........ 2 linhas (Allianz Residencial + subcorredor Eletricista)
                            22 das 28 colunas sem leitor de runtime
                            phases, required_slots, guardrails, golden_tests:
                            ZERO leitores em qualquer linguagem
                            motor apagado no commit d88ac70 (20/07)
                            graveyard.corridor_runs: 50, todas 'active'
                            graveyard.dispatch_packets: 7, ZERO enviados

corridor_playbooks.py ..... 11 roteiros de WhatsApp, vivos e executando
                            nenhum vínculo de código com corridor_templates
                            line_kind 'residential' (banco) x 'residencial' (código)

conduct_playbooks ......... 16 (12 active), destilados de 297 atendimentos reais
                            NENHUMA palavra chega ao prompt do agente

knowledge_cards ........... 8.916 publicadas — o ÚNICO conhecimento que chega
ura_maps .................. 10 mapas VIVOS (238 versões aposentadas)
agentes de atendimento .... os 4 estão is_active = false
aprovações de atendimento . ZERO, na vida inteira do produto
telefonia (twilio/asterisk) ZERO ocorrências no repositório
estado do acionamento ..... só no Redis, TTL 6h, nenhuma tabela
Atlas ..................... último evento capturado 29/07 18:48
```

**São doze perguntas. Responda o que souber e diga claramente o que não sabe —
"não sei" é uma resposta útil; um palpite apresentado como fato não é.**

---

### 1. Os dois corredores

Existem duas coisas chamadas "corredor" e elas não se tocam em nenhuma linha:
a tabela `corridor_templates` (desenho da SPEC-005/006, com fases e slots) e
`corridor_playbooks.py` (11 roteiros de URA de WhatsApp).

**Qual dos dois é o corredor de verdade, na sua cabeça?** E qual era a intenção
para o outro? O GLOSSARIO que existe hoje aponta para o arquivo Python.

### 2. Por que o motor da tabela foi apagado

O commit `d88ac70` (20/07) removeu 30 módulos, incluindo `corridor-runtime.ts`,
`action-engine.ts` (1.075 linhas), `dispatch-readiness.ts`,
`policy-evidence-pack.ts` e `tenant-corridor-activation.ts`.

**Foi decisão de arquitetura ou limpeza de código morto?** O desenho da tabela
(fases, slots obrigatórios, guardrails com severidade, 10 golden tests) é bom.
Foi abandonado por estar errado, ou por não ter dado tempo?

### 3. A ativação de corredor que não ativa nada

A tela de Seguradoras diz ao corretor: *"Sua corretora tem N corredor(es)
ativo(s) nesta seguradora — o atendente já aciona por eles."*

Isso é falso hoje: a tool de acionamento resolve o playbook de dicionários em
memória e nunca abre o banco. A função `isCorridorOperable()`, que ligaria as
duas pontas, foi apagada no mesmo commit.

**Isso é bug conhecido, dívida assumida, ou ninguém percebeu?**

### 4. Por que os quatro agentes de atendimento estão desligados

Saionara (Resulta), JOANA (Amandus), Maria Regina (AutoFleet) e Even: todos
`is_active = false`. A Resulta tem integração `purpose='attendance'` **ativa**.

**É decisão consciente (gate de go-live), efeito colateral, ou esqueceram?**
E o que precisa acontecer, na sua visão, para ligar o primeiro?

### 5. Por que o Atlas parou em 29/07

Último `observed_event` em 29/07 18:48; última `observed_session` em 28/07.
As três integrações `observer` estão ativas e `connected`. Quatro dias sem
capturar nada, e nenhum documento registra.

**Você sabe o que aconteceu?** Instância do Evolution Go caiu, processo
reiniciado sem reconectar, ou alguém desligou de propósito?

### 6. Os valores das variáveis em produção

Nenhuma destas está no `.env.example`, e o deploy é EasyPanel:

```
INSURER_DISPATCH_LIVE           (portão de envio real)
DISPATCH_FINALIZE_MODE          (test | live)
DISPATCH_FINALIZE_LIVE_PLAYBOOKS
CARTOGRAPHER_MODE               (o Cartógrafo envia WhatsApp real a seguradoras)
WHATSAPP_WEBHOOK_AUTH_MODE      (default no código: "disabled")
ATTENDANT_INBOUND_ALLOWLIST
CONTEXT_ASSEMBLY_MODE           (default: shadow)
DESTILADOR_TETO_POR_RODADA      (default: 0 — nenhuma carta nova é destilada)
```

**Quais estão ligadas hoje em produção?**

### 7. Algum corredor já acionou de verdade?

Há cicatrizes no código: *"incidente 2026-07-10: placa e telefone inventados
foram parar na seguradora"* e *"teste Allianz 12/07: '1' fixo pegou o carro
ERRADO"*.

**Algum acionamento já completou o ciclo ponta a ponta com uma seguradora
real — abriu chamado e recebeu protocolo?** Quantos? Quais seguradoras?

### 8. As fases do atendimento

Não existe estado de atendimento no código: nenhum campo de fase, de slot
preenchido ou de dado confirmado. As seis etapas vivem em prosa dentro do
prompt, e a memória do que já foi coletado é a janela de 60 mensagens.

**Isso foi decisão deliberada** (deixar o modelo conduzir) **ou é a peça que
ficou faltando?** Havia plano de persistir a ficha do atendimento?

### 9. Os playbooks de conduta que não chegam

16 playbooks destilados pelo Opus 5 de 297 atendimentos humanos reais, com
ficha de coleta de até 19 campos, aprovados por um juiz automático — e lidos
apenas por esse juiz e pela tela de admin.

**Isso é a SPEC-063 Bloco G esperando execução, ou houve motivo para não
conectar?** Chegou a existir teste de que conectá-los melhora a resposta?

### 10. As duas migrations que não existem no repositório

`20260728_02_redestilar_sessoes_que_foram_cortadas` e
`20260728_04_remover_observacao_de_teste_amandus` estão aplicadas em produção
e **nunca foram commitadas**. Apagaram dado, sem APPLY/VERIFY/ROLLBACK.

**Você tem o SQL delas?** Se não, tem a lembrança do que fizeram?

### 11. O suporte humano compartilhado

Resulta e AutoFleet apontam para o mesmo grupo de WhatsApp
(`120363427334937446@g.us`) como destino de suporte humano. O Founder já disse
que esse grupo foi coisa dele e pode ser apagado.

**Havia mais alguma coisa dependendo desse grupo** além do handoff?

### 12. O que você faria diferente

Se você tivesse mais um bloco de execução no atendimento, **qual seria e por
quê?** E qual é o erro que você acha que o próximo líder vai cometer se
ninguém avisar?

---

**Por fim:** se você discordar de alguma medição acima, diga qual e por quê. Ele
prefere ser corrigido agora do que descobrir depois.

## COPIE ATÉ AQUI
