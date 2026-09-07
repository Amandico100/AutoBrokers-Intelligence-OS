# Roteiro de validação da cobrança com as atendentes — SPEC-EXTRA-001

> Para o Founder conduzir com **Saionara (Resulta)** e **Regina (AutoFleet)**, pelos **números de teste** (TESTE-A e TESTE-B).
> O executor não contata as atendentes nem usa os números operacionais. Nada aqui liga rotina em linha operacional.
> Cada item termina com uma das três marcas: **não testado** · **aprovado no canário técnico** · **validado pela atendente** — e só a última é aceite delas.

## Antes de começar (5 min, o Founder)
1. Confirmar no EasyPanel que o `Implantar` da EXTRA-001 foi feito (o relatório §14 diz o SHA e a ordem dos serviços).
2. Abrir o painel na corretora de teste, aba **Auxiliares → Cobrança de boletos atrasados**.
3. Ter TESTE-A (a linha pareada) e TESTE-B (o "cliente" ou a "atendente" de teste) à mão.

## Parte 1 · Configurar (a atendente faz, o Founder observa)
| # | o que pedir | o que deve acontecer | marca |
|---|---|---|---|
| 1.1 | "Escolha a modalidade *Encaminhar para minha equipe* e coloque o seu WhatsApp de teste (TESTE-B)." | O campo "WhatsApp de quem recebe o pacote" aparece; salva; ao reabrir, está igual. | |
| 1.2 | "Troque para *Enviar diretamente ao cliente*." | Aparece a caixa de confirmação em português; sem marcar, não salva; marcando, salva. | |
| 1.3 | "Volte para *Encaminhar para minha equipe*." | Nenhum aviso de teste; nenhum texto técnico. | |
| 1.4 | Perguntar: "Ficou claro qual das duas você usaria no dia a dia? Por quê?" | Anotar a resposta literal. | |

## Parte 2 · Receber o pacote (modo equipe)
| # | o que pedir | o que deve acontecer | marca |
|---|---|---|---|
| 2.1 | O Founder roda o canário técnico (item sintético) com `team_number` = TESTE-B. | Em TESTE-B chegam **três** mensagens, nesta ordem: a nota interna (📋 COBRANÇA · para encaminhar…), o texto final limpo, o PDF. | |
| 2.2 | "Encaminhe o texto e o PDF para o seu próprio número (simulando o cliente)." | Ela consegue copiar/encaminhar sem editar nada; o texto **não** tem `[TESTE]`, "simulação" nem instrução interna. | |
| 2.3 | "Volte ao painel: o que aparece em *Pendências da cobrança*?" | A linha "Entregue à equipe — falta encaminhar ao cliente". | |
| 2.4 | "Clique em *Marcar como encaminhado ao cliente*." | A linha sai da lista de pendências; o histórico guarda quem marcou e quando. | |
| 2.5 | Perguntar: "A nota interna tinha o que você precisa para achar o cliente? Faltou algo?" | Anotar. | |

## Parte 3 · Envio direto (modo cliente) — só com item sintético e TESTE-B como "cliente"
| # | o que pedir | o que deve acontecer | marca |
|---|---|---|---|
| 3.1 | O Founder roda o canário em modo cliente **sem** liberar. | **Nada** chega: a parcela já foi entregue à equipe; a pendência pede decisão. | |
| 3.2 | "Clique em *Liberar reenvio* e escreva o motivo." | Sem motivo, o botão recusa. Com motivo, a linha vira "liberada". | |
| 3.3 | O Founder roda de novo. | Em TESTE-B chegam texto limpo + PDF (sem nota interna). | |
| 3.4 | O Founder roda de novo, no mesmo dia e no dia seguinte (simulado). | **Nada** chega: "já cobrado". | |

## Parte 4 · O cliente responde (TESTE-B → TESTE-A)
| # | o que pedir | o que deve acontecer | marca |
|---|---|---|---|
| 4.1 | De TESTE-B, responder "já paguei ontem". | No painel, a pendência muda para "Cliente respondeu: já paguei"; **nenhum** boleto é reenviado. Com o agente de atendimento desligado, ninguém responde automaticamente (esperado). | |
| 4.2 | De TESTE-B, responder "não sou essa pessoa". | Pendência "Cliente pediu para não receber"; *Liberar reenvio* fica **desabilitado** com o porquê. | |
| 4.3 | De TESTE-B, "me manda de novo o boleto". | Pendência "Cliente respondeu: segunda via" — a equipe reenvia pelo botão; o robô não reenvia sozinho. | |
| 4.4 | *(só se o Founder decidir ligar o agente da Resulta por uma janela curta)* "que boleto é esse?" | O agente responde com seguradora, parcela e vencimento **daquele** caso, sem citar outro cliente, sem confirmar pagamento. | |
| 4.5 | Perguntar: "Você entenderia o que fazer só pela tela de pendências?" | Anotar. | |

## Parte 5 · Quando dá errado
| # | o que pedir | o que deve acontecer | marca |
|---|---|---|---|
| 5.1 | O Founder roda o canário com o WhatsApp da equipe **fora** da allowlist (só no canário). | Nada sai; aparece "não saiu — número não autorizado no teste" na pendência/atividades. | |
| 5.2 | Mostrar a tela **Atividades** depois de uma falha simulada de PDF. | "Texto foi, PDF não" aparece como pendência; ninguém é cobrado de novo sozinho. | |
| 5.3 | Perguntar: "Se isso acontecesse de madrugada, você saberia de manhã?" | Anotar (o aviso no grupo é adicional; a tela é a fonte). | |

## Encerramento
- Registrar, por atendente, o que **aprovou**, o que **pediu para mudar** e o que **não entendeu**, com as palavras dela.
- Nada disto autoriza ligar a cobrança nas linhas operacionais: isso é uma autorização separada, específica, registrada em FOUNDER-DECISIONS.
