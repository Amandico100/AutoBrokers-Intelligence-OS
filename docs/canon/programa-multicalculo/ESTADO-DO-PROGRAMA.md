# Estado do Programa Multicálculo — o que está feito, o que espera, o que se gastou

> Arquivo vivo. Todo chat do programa lê este arquivo junto com a [PASSAGEM de 05/10](PASSAGEM-2026-10-05-WHATSAPP-PLANO-A.md) e o
> [plano](PLANO-MESTRE-MULTICALCULO.md) (v2.5.1) e o atualiza ao fechar cada SPEC. Decisões em
> [`FOUNDER-DECISIONS.md`](../FOUNDER-DECISIONS.md) (D-MC-08…74 · D-130A-06…11).

## 1. O checklist (§0.1 do plano, v2.5.1 — a fila INTERCALADA de 05/10 tarde, D-MC-61, com a 129-C da D-MC-73)

Duas linhas que andam juntas: **QCM** = Quem Cobra Menos (leads novos para as corretoras) · **AUX** = Auxiliares de Renovação e de
Cotação (o dia a dia da corretora, no chat principal) · **base** = serve às duas. A **134 flutua**: entra assim que a Meta aprovar, a
qualquer momento depois da 133-A. **A 129-C (mais ramos do Agger) entra logo depois da 133-A e antes da 130-B/131 (D-MC-73, 06/10).** Se o
portão da 131 abrir antes do da 130-B, a 131 sobe para logo depois da 129-C; a 132 exige a 130-B.

| # | Passo | Linha | Estado | Branch / commit | Portão | Marco |
|---|---|---|---|---|---|---|
| 0 | Fechar a 126/127 | — | código pronto; testes de celular do Founder | `main` `e7f76df` | — | — |
| 0.5 | Registro + `/r/` + P-E0018-14 | — | ✅ CONCLUÍDO e NO AR 04/10 (Founder implantou; `/r/` falso em aba anônima → "Este link não está mais disponível") (juiz 84 · red team 62 → conserto → confirmação 80 → conserto com prova mecânica) | `programa-mc/passo-0.5` → `main` | 🧑 Implantar + abrir um `/r/` em aba anônima | — |
| 1 | 129-A espera durável | base | ✅ CONCLUÍDA 04/10 (juiz 78 · red team 62 → conserto → confirmação 89; migrations _01 e _02 APLICADAS; _03 na caixa do Founder) — inventário já medido: ver relatório do 0.5 §1 | — | — | — |
| 2 | 128 prova do Agger | base | ✅ CONCLUÍDA 04/10 (juiz 72 ‖ red team 62 → conserto → confirmação; lente 84; 📊 16 cálculos de 25; nada apagado no Agger nem na InfoCap) — resultado em [`A-PROVA-DO-AGGER.md`](A-PROVA-DO-AGGER.md) · `reports/SPEC-128-EXECUTION-REPORT.md` · D-128-01…08 · P-128-01…14 | `spec/128-a-prova-do-agger` (código até `9db6372`) | ✅ autorização da corretora declarada (04/10) · ✅ D-128-03 TOMADA 05/10 · 🧑 os 3 negócios de teste | — |
| 3 | 129-B motor (várias corretoras em paralelo, D-MC-56; padrão + econômica juntas, D-MC-60; medir a hipótese do CPF em 2 corretoras) | base | ✅ **CONCLUÍDA 05/10** (juiz 80 ‖ red team 62 → conserto → confirmação 85; nota 86; canário AO VIVO 📊 5/5 cálculos fechados, 104 ofertas, retomada +0 `calcularV2`, 0 senha nas 5 tabelas; migration `20261005_01` APLICADA; o motor nasce DESLIGADO) — `reports/SPEC-129-B-EXECUTION-REPORT.md` · D-129B-01…11 · P-129B-01…13 | `spec/129-B-o-motor` | ✅ D-128-03 · ✅ portão de preço respondido (D-MC-62…65) · 🧑 Implantar + 1 usuário de robô por corretora (T-120) + `MULTICALCULO_HMAC_KEY` | — |
| 4 | 130-A comparação (entre seguradoras e entre corretoras), proposta e página "uau" | base | ✅ **CONCLUÍDA 06/10** no código (revisor cego da SPEC 68 → v1.1 · juiz 80 (3 blockers) ‖ red team 74 QUEBREI (1 blocker) · crítico final de design 91 · conserto único: 4 blockers + pendências, 21 guardas sobre o HTML servido, 219 testes verdes; migrations `20261006_01/_02/_03` APLICADAS) — igual-com-igual por opção (só compreensiva casco 100 % anual; produto diferente e assinatura à parte), vencedora entre corretoras, 3 opções por situação (D-MC-66/69, D-130A-09), nota 0–100 com motivos, validade (padrão 5 dias da config), mensagem ≤ 2 opções + link (D-MC-74), a página "carteira" (D-130A-11) como artefato `proposal.quote` servido pelo `/r/`, prévia PNG 1200×630, abertura e clique "Quero fechar" medidos, `ordem_do_mais_barato` e `cotacao_alvo` na porta, `multicalculo_config` por corretora, a completa+ no motor. Canário real: pedido `d0bb15ba` publicado na produção (📊 16 seguradoras · 13 completas · 1 só produto diferente · 2 sem resposta) — `reports/SPEC-130-A-EXECUTION-REPORT.md` · P-130A-01…20 | `spec/130-A-a-proposta` (base `5952324`) | ✅ portão de preço (D-MC-62…65) · ✅ D-MC-66…74 · ✅ modelo visual (D-130A-11) · 🧑 **sobram:** Implantar os 3 serviços (T-123) · WhatsApp de atendimento + nº SUSEP no cadastro de marca e a marca da AutoFleet (T-124; sem o WhatsApp, publicar RECUSA) · abrir o link do canário no celular (T-125) · jurídico da remuneração (T-126) | — |
| 5 | 133-A Quem Cobra Menos no WhatsApp, piloto fechado (Evolution) | QCM | ⏭ **próxima** (chat novo) | — | 🧑 chip novo + WhatsApp Business + instância Evolution (QR); os 5 testadores · login de robô nas corretoras antes de ir aos testadores (T-120) | — (as rodadas correm no calendário enquanto se constroem a 131 e a 132) |
| 5.5 | 129-C mais ramos do Agger (Condomínio, Empresarial e Residencial primeiro; o mesmo motor e montador da 129-B, um pedido e um preset por ramo — nunca motor novo) | base | ⏳ (D-MC-73: logo depois da 133-A, antes da 130-B/131) | — | os nomes dos ramos 69/93/46/100 e a lista de seguradoras da Resulta nos formulários (P-130A-17) · login de robô (T-120) | — |
| 6 | 130-B leitor de apólice | base | ⏳ | — | 🧑 crédito de API; 20–30 apólices | — |
| 7 | 131 renovação | AUX | ⏳ (sobe para logo depois da 129-C se o portão abrir antes do da 130-B) | — | 🧑 InfoCap da Resulta de volta na Resulta (D-MC-27) · login de robô (T-120) | 🚀1 renovação no ar |
| 8 | 132 cotação no chat principal | AUX | ⏳ | — | a 130-B · login de robô (T-120) | 🚀2 cotação no chat principal |
| 9 | 133-B Quem Cobra Menos piloto ampliado | QCM | ⏳ | — | 🧑 regras de negócio entre corretoras (D-MC-56) · preço do canal (D-MC-29) | 🚀3 Quem Cobra Menos piloto no WhatsApp |
| 10 | 135 a proposta conversa | AUX | ⏳ | — | atendimento das corretoras ligado · D-MC-32 | 🚀4 negociação pelo WhatsApp |
| 11 | 136 lembretes | base | ⏳ | — | opt-in | — |
| 12 | 137 Quem Cobra Menos público (WhatsApp oficial, aberto) | QCM | ⏳ | — | a 134 feita | 🚀5 público |
| ★ | Claude/ChatGPT (o conector e a prova de instalação da v2.4) | QCM | ⏳ | — | depois da 137 | — |
| ⇅ | 134 migração do número para a API oficial da Meta — **FLUTUANTE** | QCM | ⏳ (entra assim que a Meta aprovar, a qualquer momento depois da 133-A) | — | 🧑 Meta: empresa verificada, número, nome · cartão na conta Meta | — |

## 2. O que o Founder informou na abertura (04/10/2026)

- **Variáveis do `smith-api` no EasyPanel:** `WORK_RUNS_ROUTINE_BRIDGE=1` (a cobrança e as rotinas passam pelo Work OS →
  a 129-A mexe em caminho que **envia mensagem**: rito CRÍTICO pelo piso §3.2) · `WORK_WORKER_IN_PROCESS` **não existe**
  (o worker roda como serviço dedicado; o defeito do reinício silencioso do modo "dentro da API" não está ativo).
- **Autorização:** Resulta e AutoFleet autorizaram o uso do Agger e o desenvolvimento do programa, inclusive concluir
  cálculos (D-MC-23). Pode ler e analisar as cotações da equipe no Agger; **nunca apagar cotação feita por uma pessoa**.
- **InfoCap:** a conexão da Resulta está hoje dentro da corretora de ensaio, de propósito (D-MC-27); pode ler a da
  AutoFleet e a da corretora de ensaio.
- **Apólices de teste:** `docs/intake/MULTICALCULO AGGER/APOLICES/` (fora do git), autorizadas para cotar e testar.
- **Login do Agger (Founder, 04/10):** até existir o login exclusivo do robô, usar o login da Ellen (Resulta e AutoFleet). Parar se
  o Founder mandar ou se houver outra pessoa logada (o modal de sessão única avisa — NUNCA clicar "Prosseguir" sobre sessão de outra pessoa).
  Exceção temporária à D-MC-24, só para a 128 e testes; o motor (129-B) em uso real exige o login do robô.
- **Segredos:** a rotação é do Founder, no fim do projeto (D-MC-35). Nenhum segredo entra em arquivo versionado.

## 2.1 O que o Founder decidiu em 05/10/2026

Na conversa que fechou a SPEC-128 (04–05/10), o Founder mudou o canal e a fila. O resumo com o porquê está na
[PASSAGEM](PASSAGEM-2026-10-05-WHATSAPP-PLANO-A.md); as decisões são a D-MC-51 a D-MC-60 (a D-MC-57, modelo comercial, é
hipótese, não decisão). Em uma linha: o Quem Cobra Menos nasce no WhatsApp comum (Evolution), num número exclusivo da marca,
separado do atendimento das corretoras; migra para a API oficial da Meta na 134; compara seguradoras e corretoras parceiras,
calculadas em paralelo, e indica a vencedora; Claude/ChatGPT ficam para a ★.

## 2.2 O que o Founder decidiu em 05/10/2026, à tarde (v2.5.1)

- **D-MC-61 · a fila intercalada** (tabela do §1): as duas linhas andam juntas; a 134 flutua. Notas: intercalada 88 · auxiliares
  primeiro 75 · a v2.5 como estava 55. O porquê na [PASSAGEM](PASSAGEM-2026-10-05-WHATSAPP-PLANO-A.md) §3 e §8.
- **D-128-03 TOMADA:** o robô recalcula reenviando o corpo do pedido (`calcularV2`) com o ajuste, de dentro da página, com o token do
  próprio app; resolve a D-MC-28 (o login continua pela tela; a interceptação continua lendo os resultados). P-128-14 FECHADA, T-107 feita.
- **Os logins do Agger:** os da 128 são os da **Ellen** — uma PESSOA —, autorizados para TESTES. O Agger tem sessão ÚNICA por login: o
  robô e a Ellen ao mesmo tempo derrubam um ao outro. **Construir e testar a 129-B:** o login da Ellen, de preferência fora do horário
  dela (aviso de sessão ativa → Cancelar e parar; nunca "Prosseguir"; nunca apagar nada; captador de lista branca). **Uso real** (antes
  de a 133-A ir aos testadores e antes da 131/132 irem para as corretoras): um usuário NOVO no Agger só para o robô em cada corretora
  (T-120). 📊 04/10 (`cfg/assinatura-aggilizador` e `listaUsuarios`): Resulta 5 licenças e 6 usuários ativos · AutoFleet 8 e 7 → a
  AutoFleet tem 1 licença livre; a Resulta provavelmente precisa de 1 a mais ou liberar uma (decisão de compra do Founder).

## 2.3 O que o Founder decidiu em 05/10/2026, à noite (o portão de preço da 130-A)

- **D-MC-62 · a econômica padrão:** franquia normal + vidros básicos + carro reserva 7 dias + assistência básica; casco 100 % FIPE e RCF/APP intactos (FIPE a 90 % fora).
- **D-MC-63 · a margem da corretora** (comissão e desconto como UMA regra): o agente calcula a versão com margem menor e a mostra ao CORRETOR; nada vai ao cliente sem ele aprovar, cada vez.
- **D-MC-64 · o piso padrão da margem** = comissão de 10 % enquanto a corretora não configurar o dela.
- **D-MC-65 · a completa é UM padrão único** para todas as corretoras (RCF 200/200/20 mil, APP 5 mil, franquia reduzida, vidros completos, reserva 15 dias, assistência completa).
- 🧑 **Ressalva do Founder:** são usadas agora; ele perguntou aos comerciais das corretoras e fará ajustes pontuais quando tiver as respostas → cada uma é CONFIGURAÇÃO (presets/colunas), nunca constante espalhada.
- 📊 Medido no canário da 129-B (05/10, 3ª rodada): econômica ÷ padrão por seguradora, média **0,873** (corretora A, 14 seguradoras) e **0,872** (B, 11) — a D-MC-62 estimava 💭 12–20 % abaixo.

## 2.4 O que o Founder decidiu em 06/10/2026 (a abertura da 130-A)

- **D-MC-66…69 · a estratégia das comerciais:** três situações (renovação · novo com apólice · novo sem apólice), cada uma com a sua estratégia e as suas 3 opções ("igual à atual" sempre que houver apólice); a ordem do "mais barato" (desconto da seguradora → comissão 15 → 12 % → franquia → reserva → vidros/assistência); o agente aplica sozinho até 12 %, 10 % só com o corretor aprovando.
- **D-MC-70…72 · o agente e a negociação:** "usa o carro para aplicativo?" é a 1ª pergunta; validade e lembretes honestos (nunca cronômetro falso); a cotação-alvo procura o alvo com a MAIOR comissão possível.
- **D-MC-73 · a 129-C** (mais ramos do Agger) entra logo depois da 133-A e antes da 130-B/131 · **D-MC-74 · o WhatsApp leva no máximo 2 opções + 1 linha-resumo + o link**; o resto mora na página.
- **D-130A-06/07/08 · escopo:** registro do lead e consentimento → 133-A; PDF = imprimir do navegador (o do servidor depois, D-MC-43); a remuneração da corretora (CNSP 382) desligada até o jurídico.
- **D-130A-11 · o modelo visual = a "carteira"** (painel cego de 4 rodadas, 8 críticos: 85/83 → 89/88 → 90/92 → 91/90); protótipo claude.ai/artifact/K3pGqdMQ9dvThA7r6AZSZC. Tudo é CONFIGURAÇÃO por corretora (`multicalculo_config`), nunca constante.

## 3. Livro-caixa da API do produto — modelos e serviços pagos (verba do programa: 💭 US$ 4,00, Founder 04/10)

| data | SPEC | o quê | US$ | saldo |
|---|---|---|---:|---:|
| 04/10 | — | abertura | 0,00 | 4,00 |
| 04/10 | 128 | medições ao vivo e testes | 0,00 | 4,00 |
| 05/10 | 129-B | medições ao vivo e canário | 0,00 | 4,00 |
| 06/10 | 130-A | Google Places: 2 buscas (Text Search) para a ficha das corretoras — 💭 estimado pela tabela pública do Google | 💭 0,07 | 💭 3,93 |
| 06/10 | 130-A | modelos de linguagem | 0,00 | 💭 3,93 |

Regra: nenhuma rodada paga sem estimativa escrita aqui antes. O que sobrar passa para a SPEC seguinte.

## 4. O mapa dos testes do Founder, recontado (04/10/2026)

📊 Comando (no `docs/canon/`): `grep -cE '^- \[ \] \*\*T-[0-9]+' TAREFAS-DO-FOUNDER.md` → **95 pendentes**;
`grep -cE '^- \[x\] \*\*T-[0-9]+'` → **10 feitos** (T-01, 02, 05, 06, 82, 91, 92, 98, 99, 102). Total T-01…T-105.
A classe é a régua "PODE LIGAR" da validação de 03/10, reaplicada por script às 95 (a T-31 morreu → C).

| classe | quantos | quais |
|---|---:|---|
| **A · trava ligar o atendimento** (e por isso trava a 135; a 134 não, D-MC-58) | **48** | T-03 04 08 · 23–30 32 33 · 35–44 · 51 53 · 60–63 · 65–69 · 75–78 · 84–88 · 90 · 93–96 |
| **B · trava o programa** | **0** | — (o que travava a 128 estava fora da lista T: bloco H → D-MC-23/24/27/35) |
| **C · pode esperar** | **47** | T-07 · 09–22 · 31 · 34 · 45–50 · 52 · 54–59 · 64 · 70–74 · 79–81 · 83 · 89 · 97 · 100 · 101 · 103–105 |

A T-04 (crédito de API) pesa a partir da 130. O passo a passo de cada teste está em
[`ROTEIRO-DE-TESTES-DO-FOUNDER.md`](../ROTEIRO-DE-TESTES-DO-FOUNDER.md).
