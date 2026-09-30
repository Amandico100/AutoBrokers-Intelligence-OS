# SPEC-124 — O portal de vidros destrava do mesmo jeito, e a leitura de documentos no modelo certo

> Proposta PRONTA · 30/09/2026 · executar LOGO DEPOIS da SPEC-123, no MESMO chat, reusando o destravador e o diário dela.
> Rito: **AAA v13**, 🔴 CRÍTICO (o portal abre pedido de verdade numa loja). Agentes: **Opus 5.5 sempre**, até 4 ao mesmo
> tempo. **Nota alvo > 90.** ⛔ Nada de SPEC nova: o que não couber vira pendência. Fecha a frente "autonomia" do Founder.

## 0. POR QUE — o pedido do Founder
> *"A autonomia e o destravamento têm de acontecer tanto no portal de vidros quanto no WhatsApp das seguradoras. Ele precisa
> conseguir destravar, ter autorização para pensar, tomar decisões, escolher a melhor opção que acha e destravar sem precisar
> de um humano, mesmo que em alguns casos cometa erros. Isso será ajustado depois."*
> Sobre leitura de documentos: *"praticamente todo atendimento terá apólice e documento; custo alto onera cada corretora.
> Precisa acertar o máximo possível — não podemos ter erros — e, quanto mais barato no volume, mais lucrativo."*

**O que já existe (não refazer — CLAUDE.md §5):** o portal worker (`backend/portal_worker/`: `adaptive.py`,
`modelo_do_portal.py`) já tem uma camada de decisão por modelo, lendo o modelo do catálogo (papel `portal_decisao`, hoje
`gpt-6.1-sol` medium, reserva Opus 5.5); a retomada do vidro pela resposta do segurado (EXTRA-001.10.1); o destravador,
a política das 5 classes e o diário (SPEC-123); o leitor de documentos `docling-service` (hoje escolhe o modelo por env
`VISION_MODEL` — autoridade fora do catálogo, P-122-01/02).

## 1. O EXECUTION CARD
```
OUTCOME ........  (a) quando o portal de vidros trava (tela inesperada, campo que não casa, botão que mudou), a MESMA política
                  da SPEC-123 decide: conduzir · preencher com dado do caso · deduzir com nota ≥ limiar e 2ª opinião ·
                  perguntar ao segurado · nunca sozinho — e cada decisão vai ao MESMO diário; (b) a leitura de documentos
                  (apólice, CNH, documento do veículo, orçamento) roda no modelo de MELHOR custo-benefício medido, com
                  reserva de outro provedor, e o docling passa a obedecer ao catálogo
RISCO ..........  9 (ALCANCE segurado e loja 3 · REVERSIBILIDADE pedido aberto na loja 3 · FREQUÊNCIA 3)
SUPERFÍCIE .....  2 (decisão do portal worker, contrato do docling, rota de visão)
PISO APLICADO ..  §3.2 — abre pedido real; muda o modelo que lê todo documento → CRÍTICO
NÍVEL ..........  🔴 CRÍTICO · builders Opus 5.5 xhigh · juiz ‖ red team Opus 5.5 · 1 conserto · confirmação
O FIO ..........  §2
PARALELISMO ....  F1 (portal destrava: portal_worker/) ‖ F2 (visão: bancada de documentos + docling + rota) — arquivos disjuntos
UNIDADES .......  2 fatias + costura
COESÃO .........  "uma política de destravar para os dois canais; um catálogo para todos os modelos"
TIME ...........  2 builders em paralelo · juiz ‖ red team · confirmação · atualizador de documentos
REFERÊNCIA .....  interna: a política e o diário da SPEC-123; SPEC-EXTRA-001.10/001.10.1 (o fio do vidro); a bancada de
                  visão da SPEC-116 · externa: §6
GATES ..........  §5
O ELO ..........  "o portal chama humano porque a camada de decisão não tem a política nem o contexto" — medir onde o
                  portal para hoje (F1 BLOCO 0) e que o destravador resolve essas paradas (teste do fio com telas reais)
FAIXA DE RELÓGIO  💭 meio dia de relógio
ORÇAMENTO ......  OpenAI ≤ US$ 1,00 · Anthropic ≤ US$ 0,80 nesta SPEC (dentro do teto total do Founder: OpenAI ≤ US$ 3 nas
                  SPECs 123+124; Anthropic saldo US$ 2,86 somando as duas), lido do ledger, parando sozinho
```

## 2. O FIO
segurado pede vidro → agente coleta → portal worker navega pelo caminho conhecido (API-first, 001.10) → **trava** →
destravador (contexto: o caso, a conversa com o segurado, a tela/DOM/imagem atual, o histórico da navegação, o que o
portal fez em pedidos anteriores) → classe + nota + motivo → política em código (a MESMA da 123) → age ou pergunta ao
segurado ou chama pessoa → linha no diário → resultado (pedido aberto? loja confirmou?).
Documento chega → leitor (docling) → modelo da rota `visao_documento` (catálogo) → campos extraídos → o agente usa.

## 3. DECISÕES (do Founder — lei)
| # | decisão | nota |
|---|---|---|
| D1 | A política das 5 classes, o limiar e a segunda opinião de OUTRO provedor valem IGUAIS no portal (reusar o módulo da 123; proibido copiar) | Founder |
| D2 | NUNCA SOZINHO no portal: aceitar franquia/valor/custo, escolher loja paga fora do que o caso pede, cancelar pedido, inventar dado. Confirmar o pedido com os dados do caso COMPLETOS é o objetivo do fluxo, não é proibido | 85 |
| D3 | Visão: o modelo principal é o que ACERTA os campos críticos (nome, CPF, placa, apólice, vigência, coberturas, valores) com o menor custo por documento; empate técnico (≤ 2 pontos de acerto) → o mais barato. Reserva de OUTRO provedor. Candidatos: `gpt-6-luna`, `gpt-6.1-sol`, `claude-sonnet-5-5` (Opus só como teto de qualidade, se sobrar orçamento) | Founder "custo alto onera; não pode errar" |
| D4 | O docling passa a receber o modelo do chamador (que resolve a rota `visao_documento` no catálogo); `VISION_MODEL` vira só paraquedas. Contrato do serviço muda (form do /parse + tarefa) — é a pendência P-122-01, entra aqui | 85 |
| D5 | Ligado de verdade no portal, com diário; sombra só se a calibração pedir (igual à SPEC-123 D5) | 85 |

## 4. AS FATIAS
**F1 · O portal destrava** (dono: `backend/portal_worker/*` e o ponto do smith-api que o chama)
- BLOCO 0: onde o portal para hoje e chama humano (contagem real nos registros do portal e nos casos de vidro), por motivo.
- Plugar a política da 123 na camada de decisão do portal (sem motor paralelo); contexto completo; diário.
- Testes pelo motor com telas REAIS gravadas do portal (as do acervo da 001.10), com CONTROLE: o caminho conhecido não muda.
- Canário: nenhum pedido real — `PORTAL_REAL_ENABLED`/allowlist continuam com o Founder.

**F2 · A visão certa** (dono: bancada de visão em `evals/`, `docling-service/`, a rota no catálogo por migration)
- Bancada com ~10 documentos reais MASCARADOS (apólice auto, apólice residencial, CNH, CRLV, orçamento, boleto) com gabarito
  dos campos; os candidatos D3 no mesmo prompt; acerto por campo, custo por documento (do ledger), latência.
- Escolher principal + reserva pelo número; migration da rota `visao_documento` (e `visao`, se a medição mandar) com
  APPLY/VERIFY/ROLLBACK; docling obedecendo ao catálogo (D4); smoke real barato.

**Costura** (gerente): um vidro com documento atravessa leitura → coleta → portal → trava → destravador → diário.

## 5. OS GATES
```
G1 🔴 o caminho conhecido do portal não muda (testes da 001.10/001.10.1 verdes; controle)
G2 🔴 NUNCA SOZINHO no portal: 0 violação; mutação → vermelho
G3 calibração do destravador no portal: na faixa de agir, acerto ≥ 90% nas telas reais (ou limiar sobe)
G4 visão: o modelo escolhido acerta os campos críticos ≥ o atual (gpt-6.1-sol) e custa ≤ ele por documento — ou fica o atual
G5 docling segue o catálogo: trocar a rota muda o modelo usado, sem mexer em env (teste)
G6 custo real ≤ orçamento, do ledger · G7 bateria completa 0 novas · G8 diário legível, duas corretoras isoladas
```

## 6. O QUE O ESTADO DA ARTE FAZ (§7.3)
- Agentes de navegação: ação com contexto da página e verificação do efeito: https://www.anthropic.com/engineering/building-effective-agents
- Calibração da confiança: https://arxiv.org/abs/2207.05221 · segunda opinião: https://arxiv.org/abs/2203.11171
- Avaliação de extração de documentos por campo (acerto por campo, não "parece bom"): https://docs.anthropic.com/en/docs/test-and-evaluate/develop-tests

## 7. O QUE FICA DE FORA
Carro reserva; condomínio e empresarial; outros portais além do de vidros; Computer Use da OpenAI (BLOCO 0 da 122: só Astra,
navegador hospedado por terceiros — decisão futura).
