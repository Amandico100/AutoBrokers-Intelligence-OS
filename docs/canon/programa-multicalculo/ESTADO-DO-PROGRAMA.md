# Estado do Programa Multicálculo — o que está feito, o que espera, o que se gastou

> Arquivo vivo. Todo chat do programa lê este arquivo junto com o [plano](PLANO-MESTRE-MULTICALCULO.md) e o
> atualiza ao fechar cada SPEC. Decisões em [`FOUNDER-DECISIONS.md`](../FOUNDER-DECISIONS.md) (D-MC-08…50).

## 1. O checklist (§0.1 do plano)

| # | Passo | Estado | Branch / commit | Portão |
|---|---|---|---|---|
| 0 | Fechar a 126/127 | código pronto; testes de celular do Founder | `main` `e7f76df` | — |
| 0.5 | Registro + `/r/` + P-E0018-14 | ✅ CONCLUÍDO e NO AR 04/10 (Founder implantou; `/r/` falso em aba anônima → "Este link não está mais disponível") (juiz 84 · red team 62 → conserto → confirmação 80 → conserto com prova mecânica) | `programa-mc/passo-0.5` → `main` | 🧑 Implantar + abrir um `/r/` em aba anônima |
| 1 | 129-A espera durável | ✅ CONCLUÍDA 04/10 (juiz 78 · red team 62 → conserto → confirmação 89; migrations _01 e _02 APLICADAS; _03 na caixa do Founder) — inventário já medido: ver relatório do 0.5 §1 | — | — |
| 2 | 128 prova do Agger | ✅ CONCLUÍDA 04/10 (juiz 72 ‖ red team 62 → conserto → confirmação; lente 84; 📊 16 cálculos de 25; nada apagado no Agger nem na InfoCap) — resultado em [`A-PROVA-DO-AGGER.md`](A-PROVA-DO-AGGER.md) · `reports/SPEC-128-EXECUTION-REPORT.md` · D-128-01…08 · P-128-01…14 | `spec/128-a-prova-do-agger` (código até `9db6372`) | ✅ autorização da corretora declarada (04/10) · 🧑 D-128-03 e os 3 negócios de teste |
| 3 | 133-A prova de instalação | ⏭ próxima (chat novo) | — | 🧑 serviço + domínio no EasyPanel; 10–15 testadores |
| 4 | 129-B motor | ⏳ | — | 🧑 1 login de robô por corretora |
| 5 | 130-A comparação e proposta | ⏳ | — | 🧑 portão de preço (D-MC-45) — as perguntas do portão de preço estão prontas em [`A-PROVA-DO-AGGER.md`](A-PROVA-DO-AGGER.md) §6; modelo visual |
| 6 | 130-B leitor de apólice | ⏳ | — | 🧑 crédito de API; 20–30 apólices |
| 7 | 131 renovação | ⏳ | — | 🧑 InfoCap da Resulta de volta na Resulta |
| 8 | 132 cotação | ⏳ | — | — |
| 9 | 133-B Quem Cobra Menos piloto | ⏳ | — | 🧑 portão de preço do canal |
| ★ | canal público | ⏳ | — | números da 133-A/B |
| 10–13 | 134 · 135 · 136 · 137 | ⏳ | — | Meta · atendimento ligado · opt-in · ★ |

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

## 3. Livro-caixa da API de modelo (verba do programa: 💭 US$ 4,00, Founder 04/10)

| data | SPEC | o quê | US$ | saldo |
|---|---|---|---:|---:|
| 04/10 | — | abertura | 0,00 | 4,00 |
| 04/10 | 128 | medições ao vivo e testes | 0,00 | 4,00 |

Regra: nenhuma rodada paga sem estimativa escrita aqui antes. O que sobrar passa para a SPEC seguinte.

## 4. O mapa dos testes do Founder, recontado (04/10/2026)

📊 Comando (no `docs/canon/`): `grep -cE '^- \[ \] \*\*T-[0-9]+' TAREFAS-DO-FOUNDER.md` → **95 pendentes**;
`grep -cE '^- \[x\] \*\*T-[0-9]+'` → **10 feitos** (T-01, 02, 05, 06, 82, 91, 92, 98, 99, 102). Total T-01…T-105.
A classe é a régua "PODE LIGAR" da validação de 03/10, reaplicada por script às 95 (a T-31 morreu → C).

| classe | quantos | quais |
|---|---:|---|
| **A · trava ligar o atendimento** (e por isso trava a 134 e a 135) | **48** | T-03 04 08 · 23–30 32 33 · 35–44 · 51 53 · 60–63 · 65–69 · 75–78 · 84–88 · 90 · 93–96 |
| **B · trava o programa** | **0** | — (o que travava a 128 estava fora da lista T: bloco H → D-MC-23/24/27/35) |
| **C · pode esperar** | **47** | T-07 · 09–22 · 31 · 34 · 45–50 · 52 · 54–59 · 64 · 70–74 · 79–81 · 83 · 89 · 97 · 100 · 101 · 103–105 |

A T-04 (crédito de API) pesa a partir da 130. O passo a passo de cada teste está em
[`ROTEIRO-DE-TESTES-DO-FOUNDER.md`](../ROTEIRO-DE-TESTES-DO-FOUNDER.md).
