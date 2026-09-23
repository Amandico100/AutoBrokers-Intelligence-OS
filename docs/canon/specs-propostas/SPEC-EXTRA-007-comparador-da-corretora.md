# SPEC-EXTRA-007 — O COMPARADOR DA CORRETORA
## Um site público com a marca da corretora: o visitante preenche, vê a comparação das seguradoras, e vira lead dela

**Status:** PROPOSTA **CONCEITUAL** — vem **depois** da EXTRA-003 e da EXTRA-004.
**Versão:** 1.0 · 22/09/2026 · **Baseline:** `origin/main` = `d8510df` (herdado da 003; re-medir na conversão).
**Evidência:** `SPEC-EXTRA-002-investigacao-prova-agger-RESEARCH-PACK.md` (**RP**) · `SPEC-EXTRA-003-renovacao-feita.md` (**003**) · `SPEC-EXTRA-004-cotacao-pelo-chat.md` (**004**).

> ⚠️ **NÍVEL CONCEITUAL.** Onde a evidência não sustenta contrato, esta proposta diz **conceito** e lista o ❓ com o experimento que o fecha (§6). Nada daqui vira SPEC executável antes do §6 medido, do parecer jurídico (§7) e da 003 e 004 em produção. Números sem 📊 são 💭 ou ❓.

---

## 0. Resultado

> 💭 Um visitante entra no site da corretora (domínio dela, marca dela), informa o carro, o CEP e como usa o veículo, confirma o telefone, e vê as ofertas chegando: *"7 seguradoras responderam · a partir de R$ … · menor franquia …"*. Os cálculos que faltam aparecem sozinhos. No fim: *"Um corretor da [corretora] vai falar com você no WhatsApp confirmado."* Do outro lado, o corretor já recebe o lead com o cálculo feito e a apresentação pronta.

🔴 **A corretora é a responsável** pela oferta, pelo dado e pelo atendimento; o AutoBrokers é a tecnologia dela (§4.7).

---

## 1. Por que vem DEPOIS da 003 e da 004

| ordem | nota | por quê |
|---|:-:|---|
| **003 → 004 → 007** | **92** (herdada, 002 §8) | o motor é provado primeiro com quem **sabe** conferir (o corretor); o site só expõe o que já funciona |
| 007 antes | 30 | põe um motor ainda não medido diante de anônimos, com custo por visita e dado pessoal |

O que a 007 **herda pronto**: espera durável, `QuoteProvider`, matriz de verdade (003) · coleta por perguntas fixas e confirmação com hash (004, §5–§6) · comparação honesta e rótulos (003 §4.3) · estados honestos (003 §5). 💭 A 007 é, no código, **a 004 com outro rosto e outra fronteira de confiança**.

---

## 2. O FIO (conceito)

| # | elo | peça | estado |
|---|---|---|---|
| 1 | o site abre no domínio/slug da corretora e **resolve a corretora pelo banco** | molde 📊 `app/embed/[agentId]` + `app/api/leads/identify/route.ts:10-40` ("a corretora é DERIVADA da linha de `agents`", nunca do corpo do pedido) | 🔧 evolui |
| 2 | marca, nome, CNPJ, nº SUSEP da corretora na página | `brand_profiles` (📊 1 de 3 corretoras com marca, RP §4) + ❓ campos de registro | 🔧 |
| 3 | etapa 1 — só o carro e o uso, **sem dado pessoal**; etapa 2, **depois do telefone verificado** — o segurado e o condutor, que o cálculo exige (📊 RP §3: CPF, nascimento, sexo, estado civil) | perguntas fixas da 004 §5; ❓ o multicálculo calcula sem CPF? | 🔧 reusa 004 |
| 4 | aviso de privacidade + registro do consentimento (texto, versão, hora, finalidade) | 🆕 tabela de consentimento por `company_id` | 🆕 |
| 5 | CAPTCHA **no nosso site**, validado no servidor | 🆕 (ex.: Turnstile, §9) | 🆕 |
| 6 | verificação do telefone **antes** do cálculo | código pelo canal WhatsApp da corretora (EXISTE) ou SMS | 🆕 |
| 7 | limites por telefone, IP, placa, dia, e cota da corretora | molde 📊 `check_widget_rate_limit` (`api/middleware/widget_security.py:49-85`) — ⚠️ hoje **deixa passar** se a checagem falha (`:84-85`, "allowing request"): para cálculo pago, **fecha** | 🔧 |
| 8 | o lead nasce | 📊 tabela `leads` (`schema_completo.sql:791`: `company_id`, `email NOT NULL`, `phone`) — ❓ `email NOT NULL` não serve a um fluxo por telefone; migration só com MIGRATIONS-AUTHORITY | 🔧 |
| 9 | Work Run `quote.public` (origem = site), idempotente por telefone + placa + dia | `WorkRunService` | EXISTE |
| 10 | matriz → confirmação → `QuoteProvider.calcular` → espera durável → coleta | 003 + 004 | reusa |
| 11 | resultado parcial no navegador | 🆕 endpoint público que responde por um **token opaco do pedido** (curto, preso a `company_id` + pedido); o navegador consulta a cada 💭 5 s | 🆕 |
| 12 | experiência web: ofertas chegando, rótulos, validade, "cálculo, não proposta" | 🆕 página pública | 🆕 |
| 13 | handoff ao corretor | lead + run + Artifact na área da corretora; aviso pelo canal que ela já usa | 🔧 |
| 14 | retenção e eliminação | rotina de expurgo (agenda existente) | 🔧 |

🔴 **A credencial do multicálculo NUNCA vai ao navegador.** Tudo roda no servidor; o navegador conhece só o token do pedido. 📊 A lição já existe no código: `leads/identify` *"era um oráculo público"* (SPEC-098) — o conserto foi **não deixar o corpo escolher a corretora**. Aqui vale o mesmo.

---

## 3. Por que o público anônimo muda tudo

```text
na 004, quem pede é um CORRETOR autenticado, que sabe o que pede e paga o erro
na 007, quem pede é QUALQUER UM, e cada pedido:
   · dispara um cálculo REAL em até 📊 17 seguradoras, na conta da corretora (RP §2.3)
   · cria versão de negócio no multicálculo e nº de cálculo em cada seguradora (RP §2.4)
   · disputa a sessão ÚNICA do usuário robô (📊 RP §2.2) com as renovações da 003
   · carrega dado pessoal de quem pode nem ser o dono do carro
```

---

## 4. Os riscos próprios, e a resposta de cada um

### 4.1 LGPD (📊 artigos conferidos nesta sessão no texto do Planalto; enquadramento é ❓ do jurídico)
| tema | o que a lei diz | resposta conceitual |
|---|---|---|
| base legal do cálculo | art. 7º, V: execução de contrato ou **procedimentos preliminares**, **a pedido do titular** | o cálculo pedido pelo visitante; ❓ jurídico confirma |
| base legal do contato posterior / marketing | art. 7º, I: consentimento | caixa separada, desmarcada, opcional |
| prova do consentimento | art. 8º, §2º: o ônus da prova é do controlador | registro com texto, versão, hora, finalidade (elo 4) |
| finalidade e necessidade | art. 6º, II e III | só os campos que o cálculo usa (📊 RP §3); nada "por via das dúvidas" |
| informar o titular | art. 9º | aviso curto antes do formulário, com o nome da corretora |
| término e eliminação | arts. 15 e 16 | 💭 prazo por corretora; lead sem contato em N dias → eliminação |
| direitos do titular | art. 18 | canal da corretora para acesso e exclusão |
| registro e segurança | arts. 37 e 46 | log de operações sem PII; isolamento por `company_id` |

❓ **Quem é o controlador:** 💭 a corretora (controladora) e o AutoBrokers (operador) — exige contrato de operação entre os dois. ❓ **Dado de terceiro:** o condutor principal pode ser outra pessoa (CPF, nascimento) → o jurídico diz se o site pode pedir ou se isso fica para o corretor.

### 4.2 Abuso e custo
| controle | onde | 💭 padrão (configurável por corretora) |
|---|---|---|
| CAPTCHA legítimo no **nosso** site, validado no servidor | antes do código de telefone | sempre |
| telefone verificado **antes** do cálculo | elo 6 | sempre |
| limite por telefone | elo 7 | 2 cálculos/dia |
| limite por IP | elo 7 | 5 cálculos/dia |
| limite por placa | elo 7 | 1 cálculo a cada 5 dias — dentro da validade (📊 5 dias, 002 §0) devolve o resultado guardado |
| cota diária da corretora + disjuntor | elo 7 (❓ reusa a cota da EXTRA-001.8) | o que a corretora aceita pagar |
| checagem que falha | elo 7 | **recusa** (o molde de hoje deixa passar) |

🔴 **Concorrência com a renovação:** 📊 sessão única por usuário no multicálculo (RP §2.2). O site não pode derrubar o robô das renovações nem esperar a madrugada dele. ❓ usuário robô próprio para o site, ou fila com prioridade (D-E007-06).

### 4.3 Fraude
- **Oráculo de dado pessoal:** o multicálculo completa CPF → nome, nascimento; placa → modelo (📊 002 §2, item 10). 🔴 **O site NUNCA mostra dado que ele mesmo não recebeu do visitante.** Enriquecimento só no servidor, e não volta à tela.
- **Placa alheia:** cálculo com a placa de outra pessoa é possível; o limite por placa e o telefone verificado tornam o abuso caro, não impossível. ❓ o jurídico diz se o CPF entra no site ou só no contato do corretor.
- **Lead falso em massa:** CAPTCHA + telefone verificado + limites.

### 4.4 Fila e resultado parcial
📊 RP §2.3: primeira oferta em **5–41 s**, todas as úteis em **30–229 s**, conjunto fechado em **413–420 s** (n = 2). A página:
```text
mostra cada seguradora quando ela responde ("chegando…" → preço, ou motivo em linguagem simples)
diz o tempo real: "algumas seguradoras levam até 7 minutos"
deixa sair: "o resultado completo chega no seu WhatsApp confirmado" ← isso é ENVIO: piso CRÍTICO,
   consentimento próprio, texto aprovado pela corretora
transitória no corte → "esta seguradora não respondeu agora; o corretor confirma com você"
```

### 4.5 Quando pedir o telefone
| opção | nota |
|---|:-:|
| **depois do carro e do uso, antes do cálculo, com código** | **86** — o cálculo pago só existe com uma pessoa verificada atrás |
| na primeira tela | 60 — mais atrito antes de o visitante ver valor |
| depois de mostrar o resultado | 35 — cálculo pago e sem limite para anônimos |

### 4.6 O que mostrar e o que esconder
```text
NUNCA: comissão (📊 o resultado traz `percComissao`, RP §2.4 — sai no SERVIDOR, com guarda) · desconto da
       corretora · motivos técnicos de configuração ("login ou senha incorreta" vira "indisponível agora")
SEMPRE: "calculado em … válido até …" · "é cálculo, não proposta; sujeito à análise da seguradora" ·
        franquia ao lado do preço · o que a opção NÃO cobre
```

| preço ou faixa? | nota |
|---|:-:|
| **preço por seguradora, com validade e aviso de cálculo** | **78** — é o que o visitante veio buscar; é o dado real |
| faixa (menor–maior) + "fale com o corretor" | 66 — protege a negociação, mas parece isca |
| só "a partir de" | 50 |

💭 A diferença não é grande e é **comercial** → vai ao Founder e, depois, **a cada corretora** (configuração por `company_id`, nunca constante).

### 4.7 Transparência sobre ser corretora
A página diz, sempre, com dado do **banco**: nome e CNPJ da corretora, nº de registro SUSEP, que ela é a responsável e quem trata o dado. 📊 Referência de mercado: comparador online que exibe o registro SUSEP e o CNPJ no rodapé (§9). "Tecnologia AutoBrokers" só se a corretora não usar `white_label` (📊 hoje `white_label` é gravado e **não lido**, RP §4 — a 003 conserta).

### 4.8 Isolamento
- o domínio/slug resolve a corretora **pelo banco**; nenhum identificador de corretora vem do navegador (molde `leads/identify`);
- lead, consentimento, run e token do pedido carregam `company_id`; RLS + filtro no serviço (CLAUDE.md §7);
- prova com **duas corretoras reais** e dois sites; nenhum nome de corretora em código, teste ou página-modelo (CLAUDE.md §13.9).

---

## 5. O que o site NÃO faz
não emite · não faz proposta · não cobra · não decide "a melhor" (rótulos, D-E002-05) · não envia nada ao visitante sem consentimento próprio · não mostra comissão · não usa a credencial no navegador · não contorna proteção de terceiro.

---

## 6. ❓ O que precisa ser MEDIDO antes de virar SPEC executável

| ❓ | experimento | fecha quando |
|---|---|---|
| o multicálculo permite uso por site público, e a que custo por cálculo? | pergunta comercial à Agger (junto da 002 §11) | resposta escrita |
| quantos cálculos simultâneos cabem por robô (site × renovação) | E4 da 002 | nível medido, com controle |
| o visitante sabe responder CEP de pernoite, garagem, 1ª habilitação? | **piloto A** (D-E007-02): formulário sem cálculo automático, lead + cotação feita pelo corretor na 004, 30 dias | taxa de campos respondidos por campo |
| quantos visitantes chegam ao fim, e quanto vira venda | piloto A, funil medido | 📊 funil de 30 dias por corretora |
| quanto tempo o visitante espera antes de abandonar | piloto B, com cálculo real e limite baixo | curva de abandono × tempo |
| a verificação por WhatsApp da corretora funciona para número desconhecido | 1 envio real de código, com linha de controle | entrega medida |
| limites (telefone/IP/placa) seguram abuso sem barrar gente | piloto B, contagem de recusas × reclamações | taxa medida |

---

## 7. ❓ Jurídico — a verificar, não afirmado aqui

- ❓ regras da SUSEP/CNSP para **oferta e cotação de seguro por meio digital** por corretor: o que a página precisa exibir, o que é publicidade, o que é proposta. 📊 O portal da SUSEP (gov.br/susep) lista "Informações ao corretor" e noticia, em 08/2026, nova norma do CNSP sobre contratos de seguros de danos — **conteúdo não lido nesta sessão**; o jurídico avalia se toca a cotação online.
- ❓ exibir preço de seguradora antes da proposta formal exige algum aviso específico?
- ❓ papéis LGPD (controlador/operador) e o contrato de operação.
- ❓ dado de terceiro (condutor) coletado por site público.

🔴 Nenhum artigo de norma da SUSEP é citado nesta proposta, porque nenhum foi verificado.

---

## 8. Decisões do Founder

**D-E007-01 · Ordem** → **003 → 004 → 007** **92** · 007 antes 30.

**D-E007-02 · Como começar**
```text
A  piloto A: formulário público que vira LEAD + cotação feita pelo corretor na 004 (sem cálculo anônimo) .. 84
B  cálculo automático para o visitante desde o 1º dia, com todos os controles do §4.2 ..................... 60
C  só formulário de contato, sem cotação .................................................................. 40
recomendo A por 30 dias: mede o funil e os campos que o visitante sabe responder, com custo zero de cálculo
```

**D-E007-03 · Quando pedir o telefone** → **antes do cálculo, verificado** **86** (§4.5).

**D-E007-04 · Preço ou faixa** → **preço com validade e aviso** **78** · faixa 66 · "a partir de" 50. Diferença pequena → a sua decisão, e depois configuração por corretora.

**D-E007-05 · Mostrar o nome das seguradoras** → **sim, com o motivo de quem não ofertou em linguagem simples** **80** · anonimizar ("Seguradora A") 45 (esconde o que o visitante precisa para escolher).

**D-E007-06 · Robô do site**
```text
usuário robô próprio para o site, por corretora ............................ 82  (não disputa com a renovação)
o mesmo robô, com fila e prioridade ........................................ 64  (sessão única: um espera o outro)
```

**D-E007-07 · Endereço do site** → **domínio da corretora apontando para nós, resolvido pelo banco** **80** · subdomínio nosso por corretora 72 (mais simples; menos marca) · página dentro do site atual da corretora via `embed` 70 (📊 `app/embed/[agentId]` existe).

**D-E007-08 · Base legal** → **art. 7º, V para o cálculo + consentimento separado (art. 7º, I) para contato comercial** **85**, ❓ condicionado ao jurídico · consentimento único para tudo 50 (mistura finalidades).

---

## 9. O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS

| URL | o que faz | o que MODELAMOS | o que REJEITAMOS | como o juiz inspeciona |
|---|---|---|---|---|
| https://www.minutoseguros.com.br/seguro-auto | corretora online: "simular grátis", escolha entre 📊 16 seguradoras (página, 22/09), exibe registro SUSEP e CNPJ no rodapé; o fluxo interno **não foi inspecionado** | a identificação da corretora e do registro na página | — (fluxo não visto) | abrir o rodapé; percorrer o simulador sem enviar dado |
| https://www.policygenius.com/auto-insurance/ | corretora licenciada nos EUA; separa **estimativa educativa** (sem contato) de **cotação real** (com cadastro) — inspecionada | a separação estimativa × cálculo real, e o aviso de que não é proposta | mostrar estimativa estatística como se fosse preço | ler o aviso da calculadora e o caminho "Get Started" |
| https://www.bidu.com.br/seguro-auto/ | comparador/corretora online brasileiro — **não inspecionada nesta sessão** (a página não devolveu conteúdo) | — | — | o juiz abre e preenche esta linha |
| https://developers.cloudflare.com/turnstile/ | verificação humana sem quebra-cabeça na maioria dos casos; o token **precisa** ser validado no servidor (`siteverify`) — inspecionada | CAPTCHA legítimo no NOSSO site, validado no servidor | confiar em token só no navegador | o teste recusa pedido sem token válido |
| https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm | LGPD — arts. 6º II/III, 7º I/V, 8º §2º, 9º, 15, 16, 18, 37, 46 conferidos no texto nesta sessão | base legal por finalidade, prova do consentimento, retenção | um consentimento genérico para tudo | abrir os artigos da §4.1 |
| https://www.gov.br/susep/pt-br | portal do regulador — só o índice foi lido | exibir o registro da corretora | afirmar norma não lida | o jurídico responde §7 |

---

## 10. 📋 CAIXA DO FOUNDER

1. **Antes de tudo:** a 003 e a 004 em produção (esta proposta não começa antes).
2. Perguntar à Agger se o multicálculo pode servir a um site público e a que custo por cálculo (junto da conversa da 002 §11).
3. Pedir ao jurídico o parecer do §7 (SUSEP, LGPD, dado de terceiro, contrato de operação).
4. Escolher uma corretora-piloto disposta a rodar o **piloto A** por 30 dias, com um corretor atendendo os leads.
5. Decidir D-E007-02 a 08 (há padrão recomendado).
