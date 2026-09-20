# 📊 O piloto medido — 2026-09-08 a 2026-09-20

> 📊 **Medido em 20/09/2026 08:19 UTC** · fonte: o banco de produção, só SELECT · gerado por:
> ```
> cd backend && python scripts/medir_o_piloto.py --de 2026-09-08 --ate 2026-09-20 --formato markdown --saida ../docs/canon/reports/SPEC-EXTRA-001.7-MEDICAO-2026-09-20.md
> ```
> Todo número desta página é 📊 MEDIDO. As notas antigas ao lado são 💭 palpite dos auditores em 12/09/2026 e **não são citáveis como medição** (CLAUDE.md §12.1).

⚠️ **O último dia (2026-09-20) ainda está correndo**: ele muda a cada hora. Para um número que não se mexe, peça até o dia anterior.

## Resulta Seguros

### Dia a dia

| dia | conversas que o agente atendeu | conversas só com pessoa | rajadas juntadas | acionamentos com protocolo | handoffs entregues | avisos ao grupo | silêncios do agente |
|---|---|---|---|---|---|---|---|
| 2026-09-08 | NÃO MENSURÁVEL | NÃO MENSURÁVEL | 0 | 0 | 0 | 0 | 0 |
| 2026-09-09 | NÃO MENSURÁVEL | NÃO MENSURÁVEL | 0 | 0 | 0 | 0 | 0 |
| 2026-09-10 | NÃO MENSURÁVEL | NÃO MENSURÁVEL | 0 | 0 | 0 | 0 | 1 |
| 2026-09-11 | NÃO MENSURÁVEL | NÃO MENSURÁVEL | 0 | 0 | 0 | 0 | 0 |
| 2026-09-12 | NÃO MENSURÁVEL | NÃO MENSURÁVEL | 0 | 0 | 0 | 0 | 0 |
| 2026-09-13 | NÃO MENSURÁVEL | NÃO MENSURÁVEL | 0 | 0 | 0 | 0 | 0 |
| 2026-09-14 | 0 | 9 | 0 | 0 | 0 | 0 | 0 |
| 2026-09-15 | 0 | 9 | 0 | 0 | 0 | 0 | 0 |
| 2026-09-16 | 0 | 14 | 0 | 0 | 0 | 0 | 0 |
| 2026-09-17 | 0 | 3 | 0 | 0 | 0 | 0 | 0 |
| 2026-09-18 | 0 | 16 | 0 | 0 | 0 | 0 | 0 |
| 2026-09-19 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2026-09-20 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

📊 No período inteiro (13 dias): **0** conversas com fala do agente, **51** só com uma pessoa da corretora, **0** com os dois. ⚠️ Só **7** desses dias são mensuráveis: antes de 14/09/2026 o produto não marcava quem escreveu a resposta.

📊 Avisos ao grupo, por tipo: nenhum.

📊 Silêncios do agente, por classe: janela 1. ⚠️ Silêncio do agente (com o segurado) e grupo calado (0) são coisas diferentes e nunca se somam. ⚠️ A trava que evita repetir a mesma linha mora na memória de cada processo: se houver mais de um trabalhador no ar, pode haver linha repetida aqui.

📊 Handoffs: 0 entregues, 0 sem ninguém para receber, 162 lembretes no teto. ⚠️ O lembrete no teto é contado **por varredura do vigia**, não por conversa: o mesmo caso parado reaparece a cada rodada.

📊 Rajadas juntadas no período: **0**. ⚠️ Só a FUSÃO deixa rastro durável; a janela de espera e o teto de mensagens moram no log e na memória rápida, e **não são mensuráveis** por aqui.

📊 Apólices marcadas como confirmadas hoje: **0** — é INFORMAÇÃO, não nota: o produto não guarda em quantas rodadas isso aconteceu.

### A régua — atendimento

**Nota do bloco: NÃO AVALIADA** — 0 de 6 dimensões têm fonte durável hoje — uma média sobre a minoria teria cara de nota do bloco inteiro

| dimensão | nota medida | 💭 palpite de 12/09 | o critério | amostra |
|---|---|---|---|---|
| apolice certa | **NÃO AVALIADA** — o produto ainda não grava em quantas rodadas a apólice foi fixada: só existe um sim/não que é sobrescrito, sem histórico (conversations.ficha_atendimento.apolice_confirmada) | 💭 50 | de cada 10 atendimentos, em quantos o agente fixou a apólice certa logo na primeira tentativa | 0 (mínimo 0) |
| coleta e age | **NÃO AVALIADA** — amostra insuficiente (0 de 5) — denominador zero não é 0%, é 'sem acionamentos no período' | 💭 40 | de cada 10 casos que o agente pegou, em quantos ele foi até o fim sozinho em vez de parar por não conseguir | 0 (mínimo 5) |
| aciona | **NÃO AVALIADA** — amostra insuficiente (2 de 5) | 💭 25 | de cada 10 acionamentos que o agente abriu, em quantos o segurado recebeu o protocolo no fim | 2 (mínimo 5) |
| fala como humano | **NÃO AVALIADA** — não há fonte durável: julgar isto exige LER a mensagem, e conteúdo de conversa não entra em medição (CLAUDE.md §7). Nenhuma nota, nenhuma avaliação automática e nenhum sinal do segurado são gravados | 💭 60 | o segurado sentiu que falou com uma pessoa, e não com um robô | 0 (mínimo 0) |
| sabe calar | **NÃO AVALIADA** — o produto grava QUANTAS vezes o agente calou (1 no período, por classe) mas nunca se o silêncio era o certo: não existe registro de 'devia ter falado e não falou'. ⛔ Um período sem silêncio nenhum seria 100 por ausência de prova, e isso é proibido | 💭 45 | quando havia uma pessoa da corretora na conversa, o agente ficou quieto — e falou quando era a vez dele | 0 (mínimo 0) |
| sabe pedir ajuda | **NÃO AVALIADA** — amostra insuficiente (0 de 5) | 💭 55 | de cada 10 vezes que o agente pediu ajuda humana, em quantas alguém da equipe realmente recebeu o caso | 0 (mínimo 5) |

### A régua — chat principal

**Nota do bloco: NÃO AVALIADA** — 1 de 5 dimensões têm fonte durável hoje — uma média sobre a minoria teria cara de nota do bloco inteiro

| dimensão | nota medida | 💭 palpite de 12/09 | o critério | amostra |
|---|---|---|---|---|
| apolice certa | **NÃO AVALIADA** — sem escritor: nada liga a pergunta do chat à apólice que foi usada para responder (conversation_logs não grava a apólice) | 💭 35 | quando a corretora pergunta sobre uma apólice, o chat traz a apólice certa | 0 (mínimo 0) |
| uma rodada | **NÃO AVALIADA** — sem escritor: nenhuma linha diz se a pergunta seguinte foi uma repetição da anterior | 💭 25 | a corretora recebe a resposta sem ter de repetir a pergunta | 0 (mínimo 0) |
| completude | **NÃO AVALIADA** — não há fonte durável: julgar completude exige ler a resposta e compará-la com a pergunta — é trabalho de avaliador, não de SELECT | 💭 45 | a resposta traz tudo o que foi perguntado, e não metade | 0 (mínimo 0) |
| confiabilidade | **NÃO AVALIADA** — a única coluna disponível não consegue discordar: 📊 conversation_logs.status é 'success' em 100% das linhas medidas (1). Um guarda que não tem como falhar não guarda nada (CLAUDE.md §9.3) — e uma resposta que nunca saiu não deixa linha nenhuma | 💭 80 | de cada 10 perguntas, em quantas o chat respondeu em vez de falhar | 1 (mínimo 0) |
| velocidade | **0** | 💭 60 | a resposta chega antes de a pessoa desistir de esperar (até 5s vale 100; a partir de 30s, 0) | 38 casos (mínimo 20) · p90 do response_time_ms do pior dia do período (44850 ms) |

## AutoFleet

### Dia a dia

| dia | conversas que o agente atendeu | conversas só com pessoa | rajadas juntadas | acionamentos com protocolo | handoffs entregues | avisos ao grupo | silêncios do agente |
|---|---|---|---|---|---|---|---|
| 2026-09-08 | NÃO MENSURÁVEL | NÃO MENSURÁVEL | 0 | 0 | 0 | 0 | 0 |
| 2026-09-09 | NÃO MENSURÁVEL | NÃO MENSURÁVEL | 0 | 0 | 0 | 0 | 0 |
| 2026-09-10 | NÃO MENSURÁVEL | NÃO MENSURÁVEL | 0 | 0 | 0 | 0 | 0 |
| 2026-09-11 | NÃO MENSURÁVEL | NÃO MENSURÁVEL | 0 | 0 | 0 | 0 | 0 |
| 2026-09-12 | NÃO MENSURÁVEL | NÃO MENSURÁVEL | 0 | 0 | 0 | 0 | 0 |
| 2026-09-13 | NÃO MENSURÁVEL | NÃO MENSURÁVEL | 0 | 0 | 0 | 0 | 0 |
| 2026-09-14 | 0 | 16 | 0 | 0 | 0 | 0 | 0 |
| 2026-09-15 | 0 | 12 | 0 | 0 | 0 | 0 | 0 |
| 2026-09-16 | 0 | 15 | 0 | 0 | 0 | 0 | 0 |
| 2026-09-17 | 0 | 12 | 0 | 0 | 0 | 0 | 0 |
| 2026-09-18 | 0 | 3 | 0 | 0 | 0 | 0 | 0 |
| 2026-09-19 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2026-09-20 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

📊 No período inteiro (13 dias): **0** conversas com fala do agente, **58** só com uma pessoa da corretora, **0** com os dois. ⚠️ Só **7** desses dias são mensuráveis: antes de 14/09/2026 o produto não marcava quem escreveu a resposta.

📊 Avisos ao grupo, por tipo: nenhum.

📊 Silêncios do agente, por classe: nenhum. ⚠️ Silêncio do agente (com o segurado) e grupo calado (7) são coisas diferentes e nunca se somam. ⚠️ A trava que evita repetir a mesma linha mora na memória de cada processo: se houver mais de um trabalhador no ar, pode haver linha repetida aqui.

📊 Handoffs: 0 entregues, 0 sem ninguém para receber, 162 lembretes no teto. ⚠️ O lembrete no teto é contado **por varredura do vigia**, não por conversa: o mesmo caso parado reaparece a cada rodada.

📊 Rajadas juntadas no período: **0**. ⚠️ Só a FUSÃO deixa rastro durável; a janela de espera e o teto de mensagens moram no log e na memória rápida, e **não são mensuráveis** por aqui.

📊 Apólices marcadas como confirmadas hoje: **0** — é INFORMAÇÃO, não nota: o produto não guarda em quantas rodadas isso aconteceu.

### A régua — atendimento

**Nota do bloco: NÃO AVALIADA** — 0 de 6 dimensões têm fonte durável hoje — uma média sobre a minoria teria cara de nota do bloco inteiro

| dimensão | nota medida | 💭 palpite de 12/09 | o critério | amostra |
|---|---|---|---|---|
| apolice certa | **NÃO AVALIADA** — o produto ainda não grava em quantas rodadas a apólice foi fixada: só existe um sim/não que é sobrescrito, sem histórico (conversations.ficha_atendimento.apolice_confirmada) | 💭 50 | de cada 10 atendimentos, em quantos o agente fixou a apólice certa logo na primeira tentativa | 0 (mínimo 0) |
| coleta e age | **NÃO AVALIADA** — amostra insuficiente (0 de 5) — denominador zero não é 0%, é 'sem acionamentos no período' | 💭 40 | de cada 10 casos que o agente pegou, em quantos ele foi até o fim sozinho em vez de parar por não conseguir | 0 (mínimo 5) |
| aciona | **NÃO AVALIADA** — amostra insuficiente (0 de 5) | 💭 25 | de cada 10 acionamentos que o agente abriu, em quantos o segurado recebeu o protocolo no fim | 0 (mínimo 5) |
| fala como humano | **NÃO AVALIADA** — não há fonte durável: julgar isto exige LER a mensagem, e conteúdo de conversa não entra em medição (CLAUDE.md §7). Nenhuma nota, nenhuma avaliação automática e nenhum sinal do segurado são gravados | 💭 60 | o segurado sentiu que falou com uma pessoa, e não com um robô | 0 (mínimo 0) |
| sabe calar | **NÃO AVALIADA** — o produto grava QUANTAS vezes o agente calou (0 no período, por classe) mas nunca se o silêncio era o certo: não existe registro de 'devia ter falado e não falou'. ⛔ Um período sem silêncio nenhum seria 100 por ausência de prova, e isso é proibido | 💭 45 | quando havia uma pessoa da corretora na conversa, o agente ficou quieto — e falou quando era a vez dele | 0 (mínimo 0) |
| sabe pedir ajuda | **NÃO AVALIADA** — amostra insuficiente (0 de 5) | 💭 55 | de cada 10 vezes que o agente pediu ajuda humana, em quantas alguém da equipe realmente recebeu o caso | 0 (mínimo 5) |

### A régua — chat principal

**Nota do bloco: NÃO AVALIADA** — 1 de 5 dimensões têm fonte durável hoje — uma média sobre a minoria teria cara de nota do bloco inteiro

| dimensão | nota medida | 💭 palpite de 12/09 | o critério | amostra |
|---|---|---|---|---|
| apolice certa | **NÃO AVALIADA** — sem escritor: nada liga a pergunta do chat à apólice que foi usada para responder (conversation_logs não grava a apólice) | 💭 35 | quando a corretora pergunta sobre uma apólice, o chat traz a apólice certa | 0 (mínimo 0) |
| uma rodada | **NÃO AVALIADA** — sem escritor: nenhuma linha diz se a pergunta seguinte foi uma repetição da anterior | 💭 25 | a corretora recebe a resposta sem ter de repetir a pergunta | 0 (mínimo 0) |
| completude | **NÃO AVALIADA** — não há fonte durável: julgar completude exige ler a resposta e compará-la com a pergunta — é trabalho de avaliador, não de SELECT | 💭 45 | a resposta traz tudo o que foi perguntado, e não metade | 0 (mínimo 0) |
| confiabilidade | **NÃO AVALIADA** — a única coluna disponível não consegue discordar: 📊 conversation_logs.status é 'success' em 100% das linhas medidas (35). Um guarda que não tem como falhar não guarda nada (CLAUDE.md §9.3) — e uma resposta que nunca saiu não deixa linha nenhuma | 💭 80 | de cada 10 perguntas, em quantas o chat respondeu em vez de falhar | 35 (mínimo 0) |
| velocidade | **16** | 💭 60 | a resposta chega antes de a pessoa desistir de esperar (até 5s vale 100; a partir de 30s, 0) | 35 casos (mínimo 20) · p90 do response_time_ms do pior dia do período (25995 ms) |

