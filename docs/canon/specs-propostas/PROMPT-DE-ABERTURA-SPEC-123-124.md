# Texto para abrir o chat das SPECs 123 e 124 (copiar tudo abaixo da linha)

---

Execute, nesta ordem e neste mesmo chat, a SPEC-123 e depois a SPEC-124:
- docs/canon/specs-propostas/SPEC-123-o-agente-destrava-com-nota-diario-e-aprendizado.md
- docs/canon/specs-propostas/SPEC-124-o-portal-de-vidros-destrava-e-a-visao-certa.md

Leia primeiro o CLAUDE.md, o protocolo AAA v13 (docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md), o glossário e as duas SPECs
inteiras. Depois, só o que elas citam: docs/canon/reports/SPEC-122-EXECUTION-REPORT.md, SPEC-122-BANCADA.md,
TELAS-QUE-FALTAM-2026-09-30.md e SPEC-121-EXECUTION-REPORT.md.

O QUE EU QUERO (é o coração das duas SPECs — não perca isto):
- O agente continua determinístico até travar. Travou, ele está AUTORIZADO a pensar, usar todo o contexto e DESTRAVAR sozinho:
  conduzir, responder com o dado do caso, deduzir quando a nota dele for ≥ 70 (com a segunda opinião de um modelo de OUTRO
  provedor), perguntar ao segurado quando só ele sabe (em TODAS as seguradoras, com retomada se a URA fechar, sem duplicar
  pedido). Só chama pessoa no irreversível (aceitar custo/pagamento, abrir sinistro, cancelar, inventar dado) ou sem saída.
- Vale no WhatsApp das seguradoras (SPEC-123) e no portal de vidros (SPEC-124).
- Toda decisão autônoma vai para um DIÁRIO no painel admin, escrito para GENTE entender, com "certo / errado".
  O "errado" vira caso de teste e, se for regra, carta de conhecimento. É assim que o agente aprende.
- A porta para ligar NÃO é "zero erro grave". É a calibração medida: na faixa de nota em que ele age, acerta ≥ 90%.
  Pode errar um pouco no começo — as corretoras sabem. O que não pode é travar e chamar humano por excesso de zelo.
- O modelo do destravador e o da leitura de documentos são escolhidos pela bancada: o de melhor custo-benefício que não
  erre. Compare os modelos no MESMO prompt antes de afirmar vencedor (a SPEC-122 comparou coisas diferentes).
- Complete o guincho da Yelum (26+ conversas) e o que der das rotas da Allianz residência; atualize o documento dos
  corredores com a verdade. As perguntas que mandei para a Regina e a Saionara podem não chegar: siga sem elas.

DINHEIRO DE API (não passe disso; leia do registro de custo; pare sozinho):
- OpenAI: tenho US$ 6, mas o teto de gasto é US$ 3 somando as duas SPECs.
- Anthropic: tenho US$ 2,86 para as duas SPECs.
- Se precisar de mais, me avise na caixa do Founder; não gaste além.

REGRAS DE EXECUÇÃO:
- Agentes sempre Opus 5.5, até 4 ao mesmo tempo, até 50 por sessão. Builders frescos por fatia; juiz ‖ red team frescos.
- Nota alvo acima de 90 em cada SPEC. O que não couber vira pendência — nada de SPEC nova no meio. Estas duas fecham a
  frente de autonomia para seguirmos o resto do projeto.
- Carro reserva, condomínio e empresarial ficam FORA.
- As variáveis PORTAL_VISION_MODEL e COUNCIL_MEMBERS foram apagadas por mim no EasyPanel; as senhas coladas em chats
  antigos estão sendo trocadas — não use nada que venha de chat.
- No fim de CADA SPEC: push na main com a saída colada, painel atualizado, documentos atualizados, e o relatório completo
  para mim em linguagem de gente (o que mudou, o que eu faço agora com comandos prontos, decisões com nota, o que ficou fora).
