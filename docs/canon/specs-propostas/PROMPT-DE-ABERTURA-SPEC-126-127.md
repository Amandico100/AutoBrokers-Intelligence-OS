# Texto para abrir o chat das SPECs 126 e 127 (copiar tudo abaixo da linha)

---

Execute, nesta ordem e neste mesmo chat, a SPEC-126 e depois a SPEC-127:
- docs/canon/specs-propostas/SPEC-126-o-atendimento-quase-sem-erro.md
- docs/canon/specs-propostas/SPEC-127-o-portal-de-vidros-no-nivel-do-whatsapp.md

Leia primeiro o CLAUDE.md, o protocolo AAA v13 (docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md), o glossário
(docs/canon/GLOSSARIO.md), as duas SPECs inteiras e o relatório docs/canon/reports/SPEC-125-EXECUTION-REPORT.md. Depois,
só o que elas citam (PENDENCIAS por número, nunca inteiro).

O QUE EU QUERO (decidi em 02/10 — é lei, está no §3 das SPECs):
- Primeiro o atendimento SEM ERRO e SEM HUMANO no que não é grave. Custo não é prioridade agora; baratear é depois.
- Antes de mexer em qualquer coisa, valide a SPEC-125 no modelo de produção (gpt-6.1-sol high, k=2 nos críticos). É a linha
  de base honesta.
- A confirmação do acionamento aceita qualquer "ok" claro ("pode mandar", "manda", "pode", "isso", "bora", "👍"), e nunca
  aciona com "pode deixar", "prefiro amanhã" ou "não, pode acionar o outro". Escolhida: o classificador barato + a regra de
  hoje (só aciona se os dois concordarem), com a bancada de 120 frases; botões onde o WhatsApp permitir.
- O parente (cônjuge, filho, pai/mãe, motorista) PODE pedir o acionamento na apólice do titular, sem o titular junto; não
  recebe nenhum dado da apólice. O mesmo celular com mais de 2 apólices diferentes em 5 dias → aviso ao grupo de suporte da
  corretora, sem bloquear o atendimento.
- O CPF é mascarado só na conversa com o segurado; a URA da seguradora e o portal de vidros recebem os dados completos —
  com teste que prove.
- Pedido de cancelamento depois de acionar: o agente não promete cancelar; avisa e chama a pessoa da corretora na hora,
  com o dossiê. Cancelar sozinho fica para depois.
- O portal de vidros tem de chegar ao nível do WhatsApp: faltou dado → pergunta antes de escrever no portal, cidade do
  serviço certa, reparo e ofertas nunca aceitos sozinhos, a parada do portal chega ao destravador e volta ao mesmo pedido.

DINHEIRO DE API (leia do registro de custo; o runner para sozinho):
- OpenAI: cerca de US$ 3 para a validação da 125, a 126 e a 127 juntas. Pode passar um pouco se for importante — tenho
  US$ 5 na conta; o teto duro é US$ 4,50 (a conta e a ordem de corte estão no §8 da SPEC-126).
- Anthropic: só a nota do Opus na calibração da dedução, lida do registro; sem saldo, a dedução não religa.
- Se precisar de mais, me avise na caixa do Founder; não gaste além.

REGRAS DE EXECUÇÃO:
- Agentes sempre Opus 5.5, sem teto de agentes ao mesmo tempo, até 100 por sessão. Builders frescos por unidade; juiz ‖
  red team frescos e cegos um ao outro.
- Nota alvo acima de 90 em cada SPEC. O que não couber vira pendência — nada de SPEC nova no meio.
- Nenhuma mensagem real, nenhum agente ligado, nenhum acionamento real e nenhum pedido real no portal pela execução.
- No fim de CADA SPEC: push na main com a saída colada, painel e documentos atualizados, e o relatório completo para mim
  em linguagem de gente (o que mudou, o que eu faço agora com comandos prontos, se der errado, decisões com nota, o que
  ficou fora, a próxima SPEC).
- Os testes que eu tiver de fazer (aparelho real, canário do portal, SQL) vão para a lista única T-NN do
  docs/canon/TAREFAS-DO-FOUNDER.md, continuando a numeração (a próxima é a T-91).
