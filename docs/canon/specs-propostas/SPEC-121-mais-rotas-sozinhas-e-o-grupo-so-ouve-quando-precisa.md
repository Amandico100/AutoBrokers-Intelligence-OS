# SPEC-121 — Mais rotas atendem sozinhas, e o grupo só ouve quando precisa

> Proposta · 29/09/2026 · nasce das seis investigações de `investigacoes-2026-09-29/` (só leitura, 📊 banco
> `observed_events` com 33.628 eventos e 689 sessões, lido em 29/09) · depois da SPEC-120 (main `c310e77`)
> Rito: **AAA v13**, CRÍTICO por efeito (envia à seguradora e ao grupo). Agentes: **Opus 5.5 sempre**.

## 0. O EXECUTION CARD

```
OUTCOME ........  o grupo de suporte só recebe aviso de conversa que o humano NÃO conhece, com o agente
                  LIGADO; e 📊 de 31 para o máximo de rotas que atendem sozinhas, com carro reserva
RISCO ..........  9  (ALCANCE segurado e corretora 3 · REVERSIBILIDADE mensagem enviada 3 · FREQUÊNCIA 3)
SUPERFÍCIE .....  3  (grupo: 6 remetentes · corredores · acervo e classificador)
PISO APLICADO ..  §3.2 — envia à seguradora e ao grupo → CRÍTICO
NÍVEL ..........  🔴 CRÍTICO · builders Opus 5.5 xhigh · juiz ‖ red team Opus 5.5 · 1 conserto
O FIO ..........  §2
PARALELISMO ....  F1 (grupo) ‖ F3 (acervo/classificador, scripts) ‖ [F2 → F4 → F5] (corredor_playbooks, UM dono)
                  → F6 (medição)
UNIDADES .......  6 fatias, §5
COESÃO .........  "o agente resolve sozinho, e quando não resolve, avisa UMA vez quem não sabe"
TIME ...........  3 builders frescos, dono único por arquivo
REFERÊNCIA .....  interna: os 29 avisos errados de 21/09 (📊 29 de 29) e as 6 investigações ·
                  externa: §7.3
GATES ..........  §6
O ELO ..........  "os avisos errados vêm de 3 causas no código, e as rotas travam por acervo cortado,
                  etiqueta errada e 3 telas novas — não por falta de conversa". §1 mede A, B e B→A
FAIXA DE RELÓGIO  💭 1 dia de relógio
ORÇAMENTO ......  sem chamada de modelo
```

## 1. O ELO — o que as investigações mediram

**O grupo** (`investigacoes-2026-09-29/o-grupo-de-suporte.md`): 📊 **29 de 29** avisos enviados desde 16/09 eram
de conversa que a atendente já conhecia (ela tinha falado entre 241,6 e 295,7 h antes) e com o agente de
atendimento **desligado**. Legítimos: **0**. Causas no código:
1. o espelho grava "pedido de humano" quando a **atendente responde pelo celular**, e o vigia lê esse status como
   "o agente pediu ajuda" (`handoff_watchdog.py:151`, `:285-289`) — o aviso tardio da SPEC-120 **herda** o erro;
2. a proteção "humano na conversa" vence: claim por 6 h, janela de 7 dias limitada às **40** últimas mensagens
   (`o_fim_do_atendimento.py:1104`, `:1129`); sinistro e conclusão ✅ nem passam por ela (`o_grupo_so_o_que_importa.py:85`);
3. **nenhum remetente pergunta se o agente de atendimento está ligado** — só o resumo das 19h (`o_resumo_das_19h.py:111`);
   e na dúvida (falha de leitura, lote cortado) a porta **avisa** (`:415`, `:440`, `:455`; vigia `:189`, `:205`).
📊 470 conversas estão em "pedido de humano" vindas do espelho; 95 disparariam aviso se o cliente escrevesse de novo.
Hoje nada sai só porque os destinos de suporte estão desativados desde 21/09.

**As rotas** (`yelum-guincho-porto-bateria-hdi-eletricista.md`, `eletrodomesticos-e-sem-desfecho.md`, `carro-reserva.md`):
- `zonas_do_acervo.zonas` joga fora tudo depois da 1ª transferência para humano — 📊 na Allianz residencial,
  **39 sessões** têm o protocolo só nessa parte, e em 19 o robô da URA recomeçou. Desentupimento e eletrodomésticos
  da Allianz "nunca chegaram" no acervo e **chegaram 4 de 4 e 3 de 3 no banco**.
- yelum/auto/guincho está em 68% por **uma** sessão (`56bd78f7`) em que a chave foi perdida e a Yelum converteu em
  guincho; sem ela: 📊 449/449 telas respondidas, 15 conversas com protocolo, ≈ 95%.
- porto/auto/bateria: 📊 4 de 6 sessões vão ao protocolo **sem** a consultora; ela entra por perfil do cliente.
- 🔴 **A Porto auto mudou o menu**: *"Você quer falar sobre qual assunto? … Sinistro …"* não casa passo nenhum e a
  palavra "sinistro" dispara a passagem para pessoa **antes do serviço**, em qualquer serviço. 📊 2 das 3 conversas
  de Porto auto dos últimos 30 dias vieram com ele (`910b6295` em 14/09, `9e043112` em 29/09). *"Por favor, selecione o
  veículo."* também não tem passo.
- Classificador: geladeira/fogão/micro-ondas/freezer não casam eletrodoméstico; recarga de bateria da Yelum vira
  "socorro mecânico"; chave perdida vira guincho.

## 2. O FIO
segurado pede → agente coleta (inclusive as perguntas novas antes do acionamento) → corredor responde a URA →
protocolo → ✅ no grupo **só se o agente atendeu** · se trava: **um** aviso, **só** se o agente está ligado e o humano
não conhece a conversa → a atendente assume → o agente **nunca mais** fala dessa conversa no grupo (7 dias).

## 3. DECISÕES (as do Founder são lei)
| # | decisão | origem |
|---|---|---|
| D1 | Grupo = avisar o humano do que ele **não conhece** e o agente não concluiu. Humano já falou → nada, nunca, nem lembrete | Founder, 29/09 |
| D2 | Agente de atendimento **desligado** → nenhum aviso de atendimento ao grupo (auxiliares que não são de conversa — cobrança, queda de canal, resumo — seguem) | Founder, 29/09 |
| D3 | Regra dos 7 dias: conversa com humano → o agente não se mete por 7 dias; vale também para o grupo | Founder, 29/09 |
| D4 | Na dúvida (banco ilegível, lote cortado), a porta **cala** e registra o motivo | investigação, nota 80 × 55 |
| D5 | Sinistro e conclusão ✅ obedecem à regra (hoje são isentos) | investigação; **confirmar com o Founder** |
| D6 | O aviso tardio do vigia fica, mas **exige prova** de que foi o agente quem pediu (nota 92) — não o status do espelho | investigação; **confirmar** |
| D7 | Azul, Bradesco e Zurich passam a **perguntar** a garagem (como a D2 da SPEC-120) | Founder, 29/09 |
| D8 | D-120-B revisada pela evidência: **avisar o segurado do preço da bateria nova ANTES de acionar**, e manter o "Sim" na tela (📊 única sessão real: a atendente respondeu "Sim" em 12 s; a tela diz que o preço é combinado na visita) | nota 90 × perguntar no meio 80 |
| D9 | D-120-C: tela de amperes **com preço** continua indo a uma pessoa até existir uma tela real (📊 zero no acervo); a SPEC-122 dá o caminho genérico | nota 78 |
| D10 | Portão eletrônico **não** é eletricista. Eletricista = curto, disjuntor, tomada, bocal. Raio/queda de energia que danificou o motor = **sinistro de danos elétricos** → pessoa | atendente de residencial, 29/09 |
| D11 | Consultora humana da Porto que assume no meio → pessoa da corretora com dossiê (motivo: "a Porto passou para uma consultora"). Conversar com ela fica para o futuro | Founder, 29/09 |
| D12 | Condomínio e empresarial **continuam com a atendente** nesta SPEC (ver §4) | investigação, nota 80 |

## 4. O QUE ESTA SPEC NÃO FAZ (O QUE SAIU)
- **Autonomia do modelo no acionamento** (perguntar ao segurado no meio, responder tela não escrita) → **SPEC-122**.
- **Condomínio e empresarial**: 📊 13 pedidos de condomínio e 9 de empresarial em 14 meses (6 dos 9 sem cobertura),
  contra 215 residenciais e 456 de auto; Porto, Tokio e Allianz-empresarial transferem para pessoa ou link. Revisitar
  só Allianz × condomínio × emergenciais, depois de: canário residencial Allianz verde + respostas da atendente + ≥ 3
  pedidos/mês (`condominio-e-empresarial.md`).
- Rotas **sem nenhuma conversa** (31) — continuam na lista até um acionamento real.
- Carro reserva de **Allianz** (só ligação) e **HDI** (canal desconhecido) → pessoa por desenho.

## 5. AS FATIAS

**F1 · O grupo obedece uma regra só** (builder A · `o_grupo_so_o_que_importa.py`, `handoff_watchdog.py`,
`dispatch_watchdog.py`, os 2 avisos de `dispatch_router.py`, a janela de `o_fim_do_atendimento.py`)
- Toda mensagem **com conversa** passa por: **A** agente de atendimento ligado (não dá para ler → cala) · **B** foi o
  agente quem pediu (pedido direto, acionamento, espera criada por ele — nunca o status do espelho) · **C** nenhum
  humano falou com o cliente nos últimos 7 dias (mensagem da atendente pelo celular ou painel, **sem** o limite de 40;
  claim valendo 7 dias; a pausa de 15 s da URA).
- Sem conversa (cobrança, queda de canal, fila, resumo das 19h) → fora da regra.
- Calar deixa rastro (`grupo.calado` com motivo), inclusive por falta de destino.
- ⚠️ A janela de 15 s que o Founder descreveu ("o humano destrava com um clique, o agente espera 15 s") **não foi
  achada** no código como clique; a que existe (`insurer_dispatch_service.py:560`) é a da atendente falando na URA.
  O builder confirma no BLOCO 0; se não existir, **registra**, não constrói.
- Testes T1–T8 de `o-grupo-de-suporte.md` §4, com linha de CONTROLE; **T7 = as 29 conversas reais de 21/09
  anonimizadas → zero envios**.

**F2 · A Porto auto volta a passar do primeiro menu** (builder C, dono de `corridor_playbooks.py`)
- Passos: *"Você quer falar sobre qual assunto?"* → **Assistência**; *"O que você precisa sobre Seguro Auto?
  Assistência / Sinistro"* → **Assistência**; *"Por favor, selecione o veículo."* → o veículo da placa do caso.
- A palavra "sinistro" **dentro de um menu de opções** deixa de disparar a passagem para pessoa (é opção, não relato).
- Consultora da Porto (D11) → pessoa, com motivo.
- Porto bateria: coletar antes o que a consultora pede (placa e modelo, amperes, se aceita que o prestador busque a
  bateria no centro automotivo, endereço, quem está no local, imediato ou agendado) + D8 (aviso do preço antes).

**F3 · O acervo enxerga o fim e as etiquetas dizem a verdade** (builder B · `backend/scripts/`)
- `zonas_do_acervo`: manter as telas em que o **robô da URA recomeça** depois da transferência (a atendente continua
  fora do corpus); regerar o acervo **com a máscara** (inclusive a apresentação de funcionária — fecha P-120-12).
- Classificador: geladeira/fogão/micro-ondas/freezer → eletrodomésticos; "Socorro Mecânico" de recarga → bateria;
  sessão com tela de chave → chaveiro.
- ⚠️ Regerar o acervo move a nota das 73 rotas: régua **completa antes e depois**, em worktree separado (P-118-14).

**F4 · Eletrodomésticos, chaveiro, eletricista e os ajustes pequenos** (builder C, depois da F2)
- Allianz eletrodomésticos: perguntar **o aparelho** e traduzir para a tecla da lista (1 Geladeira … 5 Micro-ondas,
  6 Fogão … 14 Máquina de lavar); hoje o produto aperta "15 - Outros" fixo.
- Perguntas antes do acionamento de eletrodoméstico (das telas reais): aparelho, idade (≤ 10 anos, senão a seguradora
  recusa e a visita conta), defeito, marca e modelo, fora da garantia, geladeira com medicação (Yelum/HDI), ar: BTUs e
  tipo. Avisar quem paga as peças (Allianz: o segurado).
- HDI chaveiro: a mensagem de cobertura que contém a palavra "sinistro" deixa de disparar a passagem para pessoa;
  *"Porta interna / Porta principal"* → pergunta ao segurado.
- Allianz: as 5 frases reais de **recusa de cobertura** viram gatilho, com mensagem honesta ao segurado.
- Yelum bateria: `local_situacao` entra nos dados da rota.
- HDI eletricista: perguntar antes tipo de problema, item, cômodo, data e período (o caminho da URA irmã da Yelum).
- D7 (garagem em Azul, Bradesco, Zurich) · D10 (portão: regra + carta de conhecimento para o agente e o chat).

**F5 · Carro reserva** (builder C, depois da F4) — `carro-reserva.md`
- **Yelum**: corredor até *"em análise, até 3 horas úteis"*, só com **sinistro numerado**; perguntar antes: condutor,
  CPF (só dígitos — 📊 a URA recusou CPF com pontuação em 4 de 9 sessões), cidade, data e hora da retirada,
  diárias; fora do horário (9h–17h, seg–sex) → não aciona, avisa o segurado. Motivo "reparo em outra seguradora"
  (exige PDF) → pessoa. Troca paga por carro melhor → recusar.
- **Tokio** e **Azul**: entregar ao segurado o **link** da seguradora (Azul `porto.vc/carroreserva`; Tokio o link da
  locadora que a URA devolve), com o que ele vai precisar (cartão de crédito em nome do condutor com limite, CNH).
- **Porto, Zurich, Bradesco, Mapfre**: sem conversa que chegue ao fim → pendência de **um acionamento real** cada.
- **Allianz** (só ligação) e **HDI** → pessoa por desenho, com dossiê.

**F6 · Medição** (gerente): régua completa, simulador, bateria em worktree separado triada contra a base, página
dos corredores regerada, painel republicado.

## 6. OS GATES
```
G1  🔴 T7: as 29 conversas reais de 21/09 → ZERO avisos; mutação de A, B ou C → vermelho
G2  🔴 agente desligado → zero avisos de conversa; CONTROLE: cobrança com agente desligado sai
G3  🔴 Porto auto: as 2 sessões do menu novo passam do menu pelo motor; CONTROLE: relato de sinistro ainda vai a pessoa
G4  yelum/auto/guincho e porto/auto/bateria em ATENDE SOZINHO no simulador
G5  allianz desentupimento e eletrodomésticos chegam ao protocolo no acervo regerado
G6  régua completa antes × depois: nenhuma rota cai sem causa escrita
G7  carro reserva Yelum: as sessões reais que chegaram a "em análise" passam pelo motor; CONTROLE: sem número de sinistro → pessoa
G8  toda constante nova com `constante_justificada` nomeando o rótulo da tela real (CLAUDE.md §9.5)
G9  bateria completa em worktree separado, triada contra a base
G10 📊 o simulador mede: de 31 para quanto
```
Cada gate novo tem MUTAÇÃO declarada que o deixa vermelho.

## 7. O QUE O ESTADO DA ARTE FAZ (§7.3)
- Alerta só quando exige ação humana e ninguém está agindo: https://sre.google/sre-book/monitoring-distributed-systems/
- Alertar sobre sintoma, com dono, e silenciar o que já está em tratamento: https://sre.google/workbook/alerting-on-slos/
- Lançar mudança de comportamento atrás de chave, medindo antes de ligar: https://martinfowler.com/bliki/DarkLaunching.html

## 8. BLOCO 0 (remedir antes de codar)
Reproduzir, com comando, na main do dia: os 29 avisos (query de `o-grupo-de-suporte.md`), as 2 sessões do menu
novo da Porto pelo motor, as 39 sessões da Allianz com protocolo depois da transferência, e 31/2/40 no simulador.
Se algum número mudar, a SPEC se ajusta antes de codar.

## 9. PERGUNTAS À CORRETORA (não bloqueiam; o default está escrito)
Carro reserva, à atendente de auto: (1) diárias: o máximo da apólice ou o que o segurado disser? carro reserva por
pane é coberto? (default: o máximo da apólice) · (2) pedir junto com a abertura do sinistro ou só depois do reparo
liberado? (default: depois do número do sinistro) · (3) segurado sem cartão de crédito com limite: qual o caminho?
(default: pessoa) · (4) Yelum "em análise": por onde chega a confirmação e quem avisa o segurado? (default: o agente
avisa que a Yelum confirma em até 3 h úteis) · (5) Allianz, Bradesco e HDI: por qual canal vocês pedem hoje?
