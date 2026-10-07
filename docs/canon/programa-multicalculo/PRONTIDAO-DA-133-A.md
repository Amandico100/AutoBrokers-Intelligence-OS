# Prontidão da SPEC-133-A — dá para fazer do jeito que o Founder falou?

> 06/10/2026, 23h40 · gerente da SPEC-130-A.1 · lido contra `PLANO-MESTRE-MULTICALCULO.md` (SPEC-133-A), as decisões D-MC-51…61,
> D-130A-06 e D-130A1-01…11. A 133-A roda **neste mesmo chat** quando o Founder mandar o prompt.

## 1. Resposta curta
**Sim**, com 3 coisas que só o Founder faz (QR, login de robô antes dos testadores, verba de API) e 2 travas no número temporário.
Nada do que ele pediu exige motor paralelo: o número entra no hub de WhatsApp que já existe, o agente é o mesmo Work OS com escopo
estreito, a mensagem e o mínimo do mínimo já saem prontos da 130-A.1.

## 2. O que a 133-A recebe pronto (da 130-A e da 130-A.1)
- a comparação, as opções, a nota, a validade e a página no `/r/` (130-A);
- a **mensagem do canal** pós-cálculo (D-130A1-01/02/03) e o texto do follow-up como dado (D-130A1-06);
- o **mínimo do mínimo** como 4º cálculo, só no canal (D-130A1-05);
- a **margem corrigida** (até 10 % sozinho, passo a passo; 12→10 % só como fechamento, em R$) e o manual do canal (D-130A1-07).

## 3. O que a 133-A constrói (proposta de fatias — a SPEC decide)
| fatia | o quê | paralela? |
|---|---|---|
| A · o número | a empresa do canal (`platform_canal`) com a conexão de WhatsApp do hub; a página **admin → Canais → Quem Cobra Menos → WhatsApp** para ler o QR (D-130A1-09) | ‖ |
| B · a conversa | o agente de cotação (escopo estreito), do "oi" ao resultado: consentimento, perguntas do perfil, o pedido ao motor, a narração curta, a mensagem do canal, a pergunta final, os 2 lembretes, a passagem à corretora vencedora | série com A no fim (costura) |
| C · a página do Quem Cobra Menos | a marca do QCM, a corretora vencedora dentro, o bloco "Corretora Nível 5" com a lista, a lista completa por seguradora (D-130A1-08); a página da carteira não muda | ‖ (arquivos disjuntos) |
| D · a porta | lista de números convidados, limite por número, registro do lead e do consentimento (D-130A-06) | com B |

## 4. O que trava (e de quem é)
| # | trava | de quem | trava o quê |
|---|---|---|---|
| 1 | **Implantar a 130-A.1** (smith-api e portal-worker) depois do push; a migration `20261006_04` o chat aplica antes | 🧑 Founder (EasyPanel) | o mínimo do mínimo e a mensagem nova em produção |
| 2 | **Ler o QR do número temporário** (47 98808-7463) na página admin que a 133-A cria | 🧑 Founder (ação física) | o número no ar |
| 3 | **Um usuário-robô do Agger em cada corretora (T-120)** antes dos testadores. 📊 A sessão do Agger é única por login: o robô no login da Ellen a derruba no meio do dia (06/10 houve sessão fantasma) | 🧑 Founder + corretoras | os testadores (não trava construir: o chat constrói com a Ellen fora do horário dela) |
| 4 | **Verba de API** para o agente conversar (o roteador de modelos) — 💭 US$ 5–10 para construção + rodadas | 🧑 Founder | a conversa ao vivo |
| 5 | **WhatsApp de atendimento das corretoras no cadastro (T-125)** | 🧑 Founder (amanhã, disse ele) | o botão "Quero fechar" da página; a passagem pela conversa não depende dele |

**As 2 travas do número temporário (D-130A1-10):** 📊 o 47 98808-7463 é HOJE o "cliente de teste" do atendimento
(`ATTENDANT_INBOUND_ALLOWLIST`). Se ele virar o número do canal sem trava, o agente do canal responderia às mensagens que os
agentes das corretoras mandam a esse número — **dois robôs conversando sozinhos**. Por isso: (1) o canal só responde a números
**convidados**; (2) nunca responde a número cadastrado como linha de corretora/agente, com guarda de laço.

## 5. Os 5 testadores — o que precisamos deles
- **Quem:** 5 pessoas leigas do círculo do Founder, com carro próprio e WhatsApp — de preferência idades e carros diferentes.
- **O que fazem:** mandam "oi" para o número, seguem a conversa até o resultado e respondem 3 perguntas: **chegou ao fim? quanto
  tempo levou? onde travou?** (+ "mostraria a um amigo?"). Uma rodada cada; o Founder repassa as respostas (ou o chat lê a conversa).
- **O que precisam ter à mão:** placa ou modelo/ano do carro, CEP de pernoite, CPF do principal condutor e as respostas do perfil
  (garagem, uso, km, condutor jovem).
- **O que precisam saber antes (consentimento):** a cotação é **real** — o CPF e o carro vão às seguradoras pelo Agger da corretora
  vencedora, e o cálculo aparece no Agger dela como um negócio novo. Ninguém é obrigado a fechar.
- **Avisar a equipe das corretoras** que vão aparecer negócios do canal no Agger (marcados pelo robô).

## 6. Apólice e fotos — podem mandar?
Podem, e o agente aceita: **guarda o arquivo (com o consentimento) e segue pelas perguntas** — a leitura da apólice é da 130-B/133-B.
Notas: aceitar e guardar 80 × recusar 50 × ler já com a visão que existe 65 (ler errado aqui nega sinistro depois; a 130-B mede antes).
O arquivo guardado vira amostra real para medir a leitura na 130-B.

## 7. O nível da conversa
Escopo estreito: **só cotação de seguro auto**. Tom humano e curto, perguntas uma de cada vez, nada de "formulário no WhatsApp".
💭 8–15 mensagens nossas por cotação. Responde as objeções com o manual do canal (D-130A1-07), nunca força venda (D-MC-59), nunca
inventa evento. Fora do escopo (sinistro, outro ramo, reclamação) → "vou te passar para a corretora" e a passagem com o resumo.
Quando a pessoa quer fechar → a passagem à corretora vencedora, na mesma conversa, com a proposta anexada.

## 8. "Corretora Nível 5" — a lista que a página precisa (💭 rascunho para o Founder lapidar)
O Founder: *"o Nível 5 tem de estar ligado ao AutoBrokers; qualquer corretora pode ser Nível 5 ao entrar; não é tamanho"*. Uma forma
crível e simples: **Nível 5 = cumpre os 5**, e cada item é verificável pelo próprio AutoBrokers:
1. **Registro ativo na SUSEP** (conferido no cadastro e na consulta pública).
2. **Cota em todas as seguradoras que aceitam o perfil** (o multicálculo prova, a cada pedido).
3. **Responde na hora, 24 h** (o agente do AutoBrokers atende; a pessoa da corretora assume no horário dela).
4. **Acompanha o sinistro do aviso ao fim** (o corredor de sinistro do AutoBrokers registra cada passo).
5. **Reputação pública conferida** (Google e Reclame Aqui lidos e respondidos — a nota aparece como está, sem filtro).
Por que assim: é verdadeiro no dia 1 para quem usa o AutoBrokers, não depende de porte, e cada item tem prova que a página pode
mostrar. O selo (o "ISO 9001" do Founder) vem depois, sobre a mesma lista.

## 9. Ideias que valem a 133-A (não obrigatórias)
- **O print compartilhável:** a 1ª mensagem do canal é feita para virar print ("Quem Cobra Menos no seu seguro foi encontrado · 104
  cotações · 47 segundos") — é o gatilho de "mostrar a um amigo" sem pedir.
- **"Indique e veja quanto seu amigo economiza":** depois do fechamento, uma linha com o link de convite (lista de convidados) — mede
  o boca a boca do piloto.
- **O "achado de ouro" honesto:** quando a vencedora é ≥ 20 % mais barata que a 2ª, a mensagem diz isso com os dois números.
