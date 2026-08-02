---
> **Status:** canônica · **bloqueada por terceiro** (API InfoCap responde 500)
> **Versão:** 1.0 · **Criada em:** 01/08/2026
> **Autoridade superior:** CLAUDE.md · SPEC-052 · SPEC-053 · SPEC-055 · SPEC-059
> **Origem:** análise de 46 telas do InfoCap · auditoria do conector de 30/07 ·
> confirmação de 01/08 de que a API responde 500 · a pergunta do Founder sobre
> por que o meu harness acha coisas que o do produto não acha
> **Branch:** `feat/spec065-carteira-dinheiro`
---

# SPEC-065 — A Carteira e o Dinheiro Visível

> **A frase que resume:** o InfoCap tem 35 relatórios prontos e ninguém os roda,
> porque **tudo é PULL** — todo relatório espera alguém lembrar, escolher filtros
> e ler. Nenhuma tela dispara ação, atribui responsável ou cobra prazo. **O buraco
> não é falta de dado. É falta de empurrão.**

---

# AVISO DE HONESTIDADE — leia antes de tudo

**Esta SPEC foi escrita a partir de prints desatualizados e de leitura de código.
A API da InfoCap não respondeu uma única vez durante a escrita.**

Isso significa, sem rodeio:

```
os números da Resulta vieram de telas de 2025 e podem estar velhos
os campos podem ter mudado de nome
endpoints que eu suponho existir podem não existir
cálculos que eu proponho podem não ter os dados que assumo
```

**Nada nesta SPEC vira código antes do Bloco 0.** E o Bloco 0 desta SPEC é maior
que o das outras, porque aqui há mais suposição.

**A regra que atravessa o documento:** toda análise proposta tem uma linha
**"como validar"** — o teste que prova que a ideia funciona **antes** de virar
funcionalidade.

---

## 1. O estado, e por que ele bloqueia

### 1.1 A API está fora

Medido em 01/08/2026, três tentativas, duas contas:

```
api.corpnuvem.com/login             HTTP 500 "Internal Server Error"
   com senha errada (controle)      HTTP 400 "Usuário ou senha incorretos"
   com e-mail inexistente           HTTP 403 "Usuário sem permissão"
   com campos vazios                HTTP 400 "Senha deve conter valor"

/attendance/connectors/infocap/lookup (produção)
   status: provider_error · blockers: ['network_error']
```

**As credenciais estão certas** — senha errada dá 400. **O usuário existe e tem
permissão** — se não tivesse, daria 403. **O servidor deles quebra.**

`/seguradoras` responde **401 "Token de autenticação inválido"** — o endpoint
existe e está vivo. Só o login não passa.

**Ação:** do Founder, junto à InfoCap. Não é resolvida aqui.

### 1.2 O que isso implica

```
BLOQUEADO ......... A · B · C · E · G  (tudo que toca InfoCap)
EXECUTÁVEL AGORA .. D (portal) · F (harness) · parte do Bloco 0
```

**O Bloco F não depende da InfoCap** e é o de maior efeito de longo prazo.
Pode ser executado enquanto a API não volta.

### 1.3 O bloco financeiro é 403, e é outra conversa

Além do 500, o mapa canônico (`INFOCAP-CORPAPI-MAPA.md:28-29`) registra que estes
retornam **403** com o perfil atual:

```
/comissao · /comissoes · /parcelas · /financeiro · /titulos
/contas_receber · /fluxo_caixa · /faturamento
/vendedores · /propostas · /sinistro · /endossos
```

E a causa: *"As permissões são flags do perfil de API (visíveis no login:
p500/p501/...=T). A corretora libera no cadastro do usuário de API dentro do
InfoCap."*

**Sem essa liberação, comissão e sinistralidade da carteira são matematicamente
impossíveis. Nenhuma linha de código resolve.**

---

# BLOCO 0 — A auditoria, que aqui é maior

**Obrigatório. E mais extenso que nas outras SPECs, porque há mais suposição.**

## 0.1 O que confirmar antes de tudo

### 0.1.1 A API volta?

```
[ ] login responde 200 nas duas contas
[ ] o token funciona em /seguradoras
[ ] quanto tempo demora — nosso limite é 8s e o 500 estourava ele
```

### 0.1.2 As flags de permissão

**A resposta do `/login` traz `p500/p501/...` e o código lê só o token
(`_extract_token`, `:413-428`) e descarta o resto.**

```
[ ] quais flags vêm ligadas hoje, por corretora
[ ] mapear flag → endpoint que ela libera
[ ] passar a gravar isso: o sistema deve saber o que cada corretora pode
```

**Isso responde sozinho "o que já dá para fazer nesta corretora" — hoje é chute.**

### 0.1.3 Os quatro endpoints nunca chamados

```
[ ] /cotacoes?codfil=1 ...... responde? que campos? quantos registros?
[ ] /atendimentos?codfil=1 .. os 2.355 da Resulta ainda estão lá?
[ ] /seguradoras ............ as 61 companhias, com abreviatura?
[ ] /ramos .................. os 50 ramos?
```

### 0.1.4 `/producao` — a hipótese que muda tudo

Foi chamado uma vez com `texto=<cpf>` e deu **500**. *"Produção"* em corretagem é
**relatório de negócio emitido** — deve esperar `codfil` + período.

```
[ ] testar com codfil + data inicial + data final
[ ] se responder: QUE CAMPOS traz? tem prêmio? comissão? por vendedor?
```

**Se `/producao` responder, boa parte do Bloco B deixa de ser necessária.**

### 0.1.5 A API permite ESCRITA?

O mapa lista só consulta. Nenhum `POST` de criação aparece.

```
[ ] existe endpoint de criação de cliente, apólice ou endosso?
[ ] se não: Digitação Zero muda de caminho (ver Bloco G)
```

### 0.1.6 Os números dos prints ainda valem?

Tudo que a SPEC cita da Resulta veio de telas de 2025:

```
[ ] prêmio e comissão do último ano fechado
[ ] a queda de 46,7% em documentos — ainda é essa?
[ ] o mix por seguradora — Bradesco 0,35 e Mapfre 0,24 confirmam?
[ ] renovação 19,7% contra novos 15,5% confirma?
[ ] 14.540 clientes cadastrados confirma?
```

**Se qualquer um mudar, a ordem de prioridade dos detectores muda junto.**

### 0.1.7 A armadilha da parcela

Nos prints: parcelas com **data de quitação preenchida e valor R$ 0,00**, todas
com a mesma data, com vencimentos futuros.

```
[ ] confirmar que isso existe na API, não só na tela
[ ] confirmar a regra: quitação com valor zero = baixa por cancelamento
[ ] existe outro campo que distingue? (situação, motivo, tipo de baixa)
```

**Isto é pré-requisito de tudo.** Sem ele, todo cálculo de inadimplência e de
comissão a receber nasce errado — **inclusive o nosso.**

### 0.1.8 As corretoras são opostas

```
Resulta ...... empresarial e condomínio · AUTO é 3,8%
AutoFleet .... 100% auto
```

```
[ ] confirmar o perfil de cada uma pela API
[ ] toda análise nasce com o perfil como parâmetro — validar que faz sentido
```

## 0.2 O relatório

Mesmo padrão das outras SPECs: **✅ confirmado · ⚠️ corrigido · ➕ acrescentado ·
❓ em aberto · 🚫 retirado**. Sem ele aprovado, a execução não começa.

## 0.3 A regra de validação de ideia

**Para cada detector do Bloco E, antes de construir:**

```
1. rodar a consulta contra dado real
2. ver quantos casos aparecem
3. conferir 3 casos À MÃO contra o InfoCap e/ou o portal
4. calcular o valor com o número real, não com o estimado
5. só então virar código
```

**Detector que não sobrevive ao passo 3 não entra.**

---

# BLOCO A — O que já está liberado e nunca foi chamado

**Nota 88.** Barato, rápido, e destrava mais do que parece.

## A.1 Os quatro endpoints

Documentados como acessíveis em 14/07/2026, validados ao vivo, **e nunca
chamados por linha nenhuma de código**:

| Endpoint | O que traz | Por que importa |
|---|---|---|
| `/cotacoes?codfil=1` | `codigo · codcli · cliente · status · prioridade` | **o funil comercial inteiro, numa chamada.** É o único agregado real disponível hoje |
| `/atendimentos?codfil=1` | histórico de atendimento/tarefa | 2.355 registros na Resulta |
| `/seguradoras` | 61 companhias com abreviatura | **sem isso todo relatório sai "ALLI: 37" em vez de "Allianz: 37"** |
| `/ramos` | 50 ramos | idem |

## A.2 As duas tabelas primeiro

`/seguradoras` e `/ramos` são **tabelas de tradução**: pequenas, sem dado
pessoal, cacheáveis por muito tempo.

**São a primeira coisa a buscar** — sem elas, nada do que produzirmos é legível.

## A.3 As flags que chegam de graça

O `/login` devolve as permissões `p5xx` e o código **lê só o token**.

**Passa a gravar.** O sistema descobre sozinho o que cada corretora liberou, e a
tela de conexão passa a mostrar:

```
✅ consulta de cliente e apólice
✅ cotações e atendimentos
🔒 comissões — peça liberação à InfoCap
🔒 sinistros — peça liberação à InfoCap
```

**Isso vira argumento de venda:** o corretor vê o que está perdendo por não
liberar.

## A.4 `/producao` — re-testar com os parâmetros certos

```
[ ] codfil + data_inicial + data_final
[ ] variações: periodo, dt_ini/dt_fim, mes/ano
```

**Se responder, o Bloco B encolhe drasticamente.**

## A.5 Testes

| # | Prova |
|---|---|
| A1 | seguradoras e ramos são buscados e cacheados |
| A2 | nenhum relatório mostra código cru — sempre o nome |
| A3 | as flags são lidas e gravadas por corretora |
| A4 | a tela mostra o que está liberado e o que não está |
| A5 | falha de qualquer endpoint não derruba os outros |

---

# BLOCO B — A carteira local

**Nota 92.** É a fundação de tudo que vem depois.

## B.1 O problema

**Não existe tabela de apólice.** Varredura de `backend/supabase/migrations/`:
nenhuma `policies`, nenhuma `carteira`. E o InfoCap responde **por CPF**, não por
conjunto.

Sem espelho não há *"quantas vencem em setembro"* nem *"quanto de comissão está
preso"*.

## B.2 A ressalva que o Founder levantou, e ele tem razão

> *"O InfoCap informa quantas apólices vencem em setembro. As corretoras já têm
> processo de renovação. Verifique isso direito."*

**Ele está certo, e a distinção é importante:**

```
O QUE O INFOCAP JÁ FAZ            o relatório "Renovações", com filtro por mês
                                  NÃO REFAZER

O QUE FALTA                       priorizar: a tela de renovação mostra nome,
                                  seguradora, data e flag de sinistro.
                                  SEM prêmio, SEM comissão, SEM responsável,
                                  SEM histórico. E o filtro é SÓ por mês.
```

**Não vamos construir "a lista de renovações". Vamos construir "qual dessas
renovações você vai perder, e quanto isso custa".**

**Validar no Bloco 0:** a tela de renovação realmente não traz prêmio nem
comissão? Se trouxer, esta parte encolhe.

## B.3 O espelho, e por que ele é derivado

```
FONTE DA VERDADE ...... o InfoCap. Sempre.
O ESPELHO ............. cópia local, reconstruível, para agregar e comparar
NUNCA .................. o espelho não decide nada sozinho, e nunca
                         é apresentado como se fosse o sistema da corretora
```

**Isto é decisão canônica** (SPEC-052 §5.5 manda consultar dado vivo). O espelho
existe **porque agregar sobre N clientes não cabe num handler de 8 segundos** — e
está registrado como tal em `FOUNDER-DECISIONS.md`.

## B.4 A regra que salva todos os números

```
parcela com data de quitação preenchida E valor de quitação = 0,00
   → NÃO FOI PAGA. Foi baixada no cancelamento.
```

**Vira teste, não comentário.** Qualquer cálculo de inadimplência ou de comissão
a receber que conte essas parcelas como pagas está errado.

**Validar no Bloco 0** (§0.1.7) antes de codificar.

## B.5 A varredura durável

Iterar a carteira exige N chamadas. Hoje o conector **faz login novo a cada
chamada** — não há cache de token. Varrer a carteira seriam milhares de logins,
padrão que qualquer API trata como abuso.

**Pré-requisitos, ambos obrigatórios:**

```
1. reuso de token — um login por varredura, não por chamada
2. tratamento de 429 — hoje cai no ramo genérico de erro
                       e é indistinguível de falha real
```

**A varredura é um Work Run** (SPEC-055): retomável, com checkpoint, sem
recomeçar do zero. **Não é scheduler novo.**

## B.6 Testes

| # | Prova |
|---|---|
| B1 | parcela com quitação zero **não** conta como paga |
| B2 | o espelho é reconstruível: apagar e refazer dá o mesmo resultado |
| B3 | um login por varredura, não por chamada |
| B4 | 429 é distinguido de erro real e respeita o backoff |
| B5 | varredura interrompida retoma sem duplicar e sem pular |
| B6 | nenhuma tela apresenta o espelho como sendo o InfoCap |

---

# BLOCO C — Parar de jogar a comissão fora

**Nota 95.** O dado já é buscado. É só guardar.

## C.1 O desperdício, com prova

`backend/portal_worker/journeys/allianz_corretor.py` extrai, por parcela
atrasada:

```
comissao · dt_prev_cancelamento · dt_fim_cobertura · vencimento
valor · parcela · apolice_susep · cliente_nome · cpf_cnpj
```

E por ramo (`extract_totals_from_rows:210`): `qtd_apolices · premio · comissao`.

**Aí `backend/app/services/billing_collection.py:350` descarta o campo
`comissao`** antes de gravar.

> ⚠️ **CORRIGIDO EM 02/08/2026 pela auditoria forense de entrada.**
> O que estava escrito aqui era uma leitura errada, e ficou registrada porque
> **o extrator do portal batiza a coluna com o nome errado.** Ver §C.1.1.

### C.1.1 O defeito de nomenclatura que causou o erro

`extract_totals_from_rows` devolve `qtd_apolices · premio · comissao`.
**Nenhum dos três é o que o nome diz.** A tabela de origem é o relatório de
**inadimplência**, e as colunas são:

```
qtd_apolices ... apólices COM PARCELA VENCIDA no ramo
premio ......... 📊 soma do VALOR DAS PARCELAS VENCIDAS   ← não é prêmio
comissao ....... 📊 soma da comissão DAQUELAS PARCELAS     ← não é a comissão do ramo
```

**A prova aritmética, na varredura de 15/07:**

```
106,03 + 107,17 + 380,63 = 593,83   ✓  as três parcelas vencidas
  0,00 +   0,03 +  17,73 =  17,76   ✓  a comissão daquelas três
```

**Correção obrigatória neste bloco:** renomear para
`qtd_apolices_com_parcela_vencida · valor_parcelas_vencidas ·
comissao_parcelas_vencidas`. **É a causa, não o efeito.** Enquanto o campo mentir
no nome, todo leitor futuro — humano ou LLM — erra do mesmo jeito.

### C.1.2 O que o dado realmente mostra

📊 **Medido** — universo completo das varreduras de 08/07 a 15/07, Resulta ×
Allianz: **5 parcelas vencidas distintas**.

| parcela | valor vencido | comissão | % |
|---|---|---|---|
| **4/4** (última) | R$ 1.297,56 | **R$ 0,00** | 0,00% |
| **10/10** (última) | R$ 106,03 | **R$ 0,00** | 0,00% |
| 3/10 | R$ 96,95 | R$ 0,03 | 0,03% |
| 3/10 | R$ 107,17 | R$ 0,03 | 0,03% |
| 2/7 | R$ 380,63 | R$ 17,73 | 4,66% |

**As duas linhas com comissão zero são as duas últimas parcelas.**

💭 **Inferência não provada:** comissão antecipada nas primeiras parcelas,
prática padrão. **Não explica tudo** — a parcela 2/7 paga 4,66% e a 3/10 paga
0,03%, 150× de diferença. **O formato muda por produto, e é isso que precisa ser
descoberto**, não "zero ou erro".

**🚫 RETIRADO:** a dicotomia *"ou a comissão é zero de verdade, ou é erro de
cadastro"*. Havia uma terceira explicação, mais provável, que não foi
considerada.

## C.2 O que continua valendo, e é o que importa

**O mecanismo é real:** a comissão é liberada por parcela paga. Se o segurado
atrasa, ela não é gerada. **E hoje o sistema lê esse dado e joga fora.**

**O que muda:** este bloco para de prometer um achado específico e passa a
entregar a **capacidade de descobrir a regra de comissionamento por produto**,
cruzando parcela × comissão ao longo do tempo. A afirmação de valor sai do texto
e passa a ser calculada.

**Validar no Bloco 0:** confirmar contra o InfoCap a comissão contratada do
produto e o esquema de antecipação. **📊 A única medição de comissão em risco
que existe hoje no sistema inteiro é R$ 17,76.** Qualquer número maior que isso
precisa vir de query, não de estimativa.

## C.3 A correção

```
1. parar de descartar `comissao` em _safe_items_for_payload
2. gravar em tabela própria: comissão observada por ramo, por data, por portal
3. série histórica — o valor de hoje não diz nada; a MUDANÇA diz tudo
```

## C.4 Testes

| # | Prova |
|---|---|
| C1 | `comissao` sobrevive até o banco |
| C2 | a série histórica registra a mudança entre varreduras |
| C3 | taxa zero ou muito abaixo da média dispara achado |

---

# BLOCO D — O cruzamento InfoCap × portal

**Nota 96. E não depende da API da InfoCap para começar** — o lado do portal
funciona hoje.

## D.1 A ideia

```
InfoCap ....... o que a CORRETORA acha que tem
portal ........ o que a SEGURADORA diz que tem

onde divergem → há dinheiro, ou há erro
```

**Ninguém compara os dois.** Não porque seja difícil — porque exige abrir duas
telas e ler linha por linha.

## D.2 O que comparar

| Campo | Divergência significa |
|---|---|
| comissão contratada × creditada | dinheiro a cobrar |
| apólice ativa no InfoCap × não no portal | cancelamento não registrado |
| apólice no portal × não no InfoCap | **produção não lançada** — o caso da AutoFleet |
| parcela paga × em aberto | baixa não processada |
| vigência | endosso não registrado |
| prêmio | reajuste não lançado |

## D.3 O portal funciona — está provado

```
login real ......... allianznet.com.br/ngx-azb-epac/private/home
boleto baixado ..... 116.620 bytes, salvo no storage
API interna ........ capturada (cobranca_api_chain, api_capture)
18 varreduras ...... concluídas
```

**Ele não lê a tela. Fala com a API por trás dela.** Isso é muito mais confiável
que raspar HTML — e significa que **replicar para outra seguradora é caminho
conhecido, não aposta.**

## D.4 O problema medido

**34 varreduras em `needs_human` contra 18 concluídas.** Quase o dobro precisou de
gente — provavelmente sessão expirada.

**Entra nesta SPEC:** renovação de sessão, e distinção entre "sessão caiu"
(recuperável sozinho) e "precisa de humano de verdade" (MFA, captcha).

## D.5 Testes

| # | Prova |
|---|---|
| D1 | divergência detectada é reproduzível: rodar duas vezes dá o mesmo |
| D2 | divergência é apresentada com os dois lados, nunca só a conclusão |
| D3 | sessão expirada renova sozinha e não vira `needs_human` |
| D4 | nada é escrito no portal — só leitura, e o teste prova |

---

# BLOCO E — Os detectores que apontam para dinheiro

**Nota 99.** É o que o corretor sente.

## E.1 O defeito

Os doze detectores de hoje vigiam o próprio sistema:

```
automacao.lacuna_recorrente    operacao.aprovacao_parada
automacao.resultado_positivo   operacao.artifact_nao_entregue
automacao.tarefa_repetida      operacao.auxiliar_degradado
conexoes.conexao_degradada     operacao.work_run_falhando
conexoes.orcamento_no_limite   operacao.work_run_travado
qualidade.atendimento_parado   qualidade.regressao_atendimento
```

**Nenhum olha dinheiro, venda, renovação ou cliente.**

## E.2 Onde eles moram

**Não é motor novo.** O Intelligence Fabric existe e funciona: 12 regras ativas,
388 execuções de detecção concluídas, briefing publicado todo dia.

O contrato já está definido: `ContextoDeDeteccao → SignalDraft`, e **o detector
nunca grava** — quem grava é o `SignalService`, com dedupe, redação e evidência
obrigatória.

```
1. arquivo novo em services/intelligence/detectors/
2. registrar o módulo na tupla de _carregar()   ← o passo que todo mundo esquece
3. INSERT em intelligence_rules
```

## E.3 Os dez primeiros

Cada um com **a frase**, **os dados** e **como validar**.

### E.3.1 · Comissão presa
> *"R$ 2.180 da sua comissão não foi gerada porque 41 parcelas estão atrasadas.
> 6 apólices têm cancelamento previsto para os próximos 15 dias."*

**Dados:** portal (comissão + data prevista de cancelamento) — **já extraídos**
**Validar:** conferir 3 casos à mão contra o portal antes de somar

### E.3.2 · Carteira vazando
> *"62 apólices venceram nos últimos 90 dias e não têm renovação nem cancelamento
> registrado. Prêmio anual delas: R$ 168 mil."*

**Dados:** vigências + ausência de sucessora + ausência de cancelamento
**Validar:** o InfoCap tem o relatório "Não Renovados" — **comparar com ele.** Se
der o mesmo, o valor está em avisar, não em achar.

### E.3.3 · Cobertura suspensa
> *"7 clientes estão com cobertura suspensa por falta de pagamento. Se baterem o
> carro hoje, a seguradora nega e a culpa vira sua."*

**Dados:** parcelas + regra de suspensão **por seguradora**
**Validar:** a regra de suspensão varia — **confirmar em pelo menos 3 seguradoras
antes de afirmar prazo.** Nunca número fixo.

### E.3.4 · Cotação esfriada
> *"19 cotações têm o cliente como último a falar. O silêncio é seu, não dele. A
> mais quente é a Juliana: ela perguntou a franquia e ninguém respondeu há 11
> dias."*

**Dados:** `/cotacoes` + última mensagem da conversa + quem enviou
**Validar:** confirmar que `/cotacoes` traz data e status utilizáveis

### E.3.5 · Renovação órfã
> *"18 apólices vencem em até 30 dias e não têm nenhuma conversa nos últimos 60
> dias."*

**Dados:** vigências × conversas
**Validar:** a corretora pode já ter processo. **Perguntar antes de construir.**

### E.3.6 · Mix que paga
> *"Bradesco é 9,6% do seu prêmio e 3,4% da sua comissão. Sompo é 19,4% e 25,5%.
> Cada R$ 1 milhão movido do ramo mais fraco para o mais forte vale R$ 166 mil."*

**Dados:** prêmio e comissão por seguradora e por ramo
**Validar:** os dois rankings estão lado a lado na mesma tela do InfoCap.
**Confirmar que a API traz os dois** — se só trouxer um, a análise não existe.

### E.3.7 · Margem real
> *"Nesta apólice você recebeu R$ 1.003,63 e repassou R$ 551,99 a 5 produtores.
> Sobrou 45%. Sua média é 78%."*

**Dados:** comissão da apólice × soma dos repasses por produtor
**Validar:** nos prints, um canal aparece com **participação 100% e nenhuma linha
de repasse** — cadastro inconsistente. **Confirmar se é erro ou regra.**

### E.3.8 · Cliente perdido
> *"ADAIR foi seu cliente por 6 renovações seguidas, de 2012 a 2018, com 2
> veículos. Hoje: zero apólices vigentes. E o telefone dele ainda está no
> cadastro."*

**Dados:** clientes cadastrados × sem apólice vigente × contato válido
**Validar:** 14.540 cadastrados contra ~2.900 ativos é estimativa. **Medir o
número real.**

### E.3.9 · Cancelamento precoce
> *"Cancelou 68 dias após a emissão. R$ 317 de comissão em risco de estorno. É o
> 7º cancelamento com menos de 90 dias este mês."*

**Dados:** início de vigência × endosso de cancelamento
**Validar:** confirmar que o tipo de endosso é identificável pela API

### E.3.10 · Autópsia da queda
> *"Você caiu 46,7% em documentos e 82,4% em novos. A queda está concentrada em
> [produtor / seguradora / ramo]. Faturas foi a única linha positiva."*

**Dados:** série de produção decomposta por três dimensões
**Validar:** **este é o de maior valor e o mais dependente de dado.** Sem
`/producao` ou sem a carteira agregada, não existe.

## E.4 A regra de apresentação

```
todo achado tem: o número · a evidência · o que fazer · e o que acontece
                 se ficar para depois
nenhum achado sem valor em R$ calculável entra no briefing
                 → vai para o Radar consultável
três por dia, no máximo. Uma manchete por semana.
```

## E.5 Testes

| # | Prova |
|---|---|
| E1 | cada detector devolve `valor_brl` calculável ou não emite |
| E2 | evidência obrigatória — nenhum achado sem apólice ou cliente nomeado |
| E3 | dedupe: o mesmo achado não aparece dois dias seguidos |
| E4 | o teto de três por dia é respeitado |
| E5 | achado sem valor vai para o Radar, não para o briefing |
| E6 | cada detector foi validado à mão em 3 casos antes de entrar |

---

# BLOCO F — O harness que calcula

**Nota 100. E não depende da InfoCap.** É o bloco de maior efeito de longo prazo,
e nasceu de uma pergunta do Founder.

## F.1 A pergunta, e a resposta medida

> *"Talvez o seu harness seja muito mais poderoso que o do AutoBrokers. Analise
> isso."*

**Ele está certo. Verificado no código:**

```
o chat principal executa código?     NÃO
consulta dados com pergunta livre?   NÃO
calcula?                             NÃO
```

Ele tem **uma ferramenta de análise de planilha com operações pré-moldadas**. Só.

## F.2 A diferença, em cinco passos

**Como eu achei os R$ 469 mil:**

```
1. rodei consulta contra o banco
2. escrevi código para cruzar duas tabelas
3. olhei o resultado e achei estranho
4. mudei a conta e rodei de novo
5. achei a armadilha da parcela — PORQUE O NÚMERO NÃO FECHAVA
```

**O passo 5 é o que importa.** Eu não achei aquela armadilha porque alguém me
contou. **Achei porque calculei, o resultado ficou esquisito, e fui atrás.**

> **Eu descubro. Ele consulta.**

Uma ferramenta que devolve *"a comissão da Porto foi R$ 411 mil"* responde uma
pergunta. **Ela nunca vai descobrir que a Porto paga 1,31 e o Bradesco 0,35** —
porque ninguém pensou em pedir essa divisão.

## F.3 O que dar a ele

### F.3.1 Executar código em caixa fechada

Recebe dados, escreve código, calcula, devolve o número.

```
sem rede
sem sistema de arquivos além do temporário
tempo e memória limitados
o que entra é dado já buscado por ferramenta governada
```

**Regra:** o código nunca busca dado. **Ferramenta busca, código calcula.** Isso
mantém o Tool Gateway como autoridade única de acesso.

### F.3.2 Consultar com pergunta livre, só leitura

Não *"me dá o relatório X"*, mas *"agrupa por seguradora e divide comissão por
prêmio"*.

```
SOMENTE LEITURA, imposto no banco — não por convenção
filtro de tenant OBRIGATÓRIO e injetado pelo sistema, nunca pelo modelo
lista de tabelas permitidas
limite de linhas e de tempo
toda consulta registrada
```

**Isto é a lição do incidente do Supabase MCP**, e a razão de ele ser desenhado
assim: nosso backend usa service role, e **RLS sem policy não protege contra erro
de filtro no código** — muito menos contra o modelo escrever o filtro errado.

### F.3.3 Duvidar do próprio resultado

O passo que separa análise de consulta.

```
o número fecha com o total conhecido?
a soma das partes bate com o todo?
o resultado é plausível na ordem de grandeza?
```

Não fechando, **investiga em vez de reportar.** E se não conseguir explicar,
**diz que não fecha** — nunca apresenta número que não fecha como se fechasse.

### F.3.4 Guardar a conta que deu certo

Consulta que produziu achado real vira **análise do catálogo** — roda sozinha no
mês seguinte, sem o modelo pensar de novo.

**É assim que o sistema aprende a achar o que ninguém programou.**

## F.4 O que isso NÃO é

```
✗ não é dar SQL livre ao modelo
✗ não é executar código do usuário
✗ não é substituir as ferramentas existentes
✗ não é caminho de escrita — nunca
```

## F.5 Testes

| # | Prova |
|---|---|
| F1 | código executado não alcança a rede |
| F2 | consulta com escrita é recusada, mesmo se o modelo tentar |
| F3 | filtro de tenant é injetado pelo sistema — o modelo não consegue removê-lo |
| F4 | tenant A jamais vê dado do tenant B (dois tenants reais) |
| F5 | resultado que não fecha é reportado como não fechando |
| F6 | consulta que virou achado é guardada como análise |
| F7 | limite de tempo e de linhas é respeitado |

---

# BLOCO G — Digitação Zero

**Nota 96 de valor. Depende de descobrir se a API permite escrita.**

## G.1 A oportunidade, que veio do Founder

> *"Provavelmente os funcionários demoram muito para lançar as apólices
> manualmente."*

**Isso explica a AutoFleet com R$ 41.996 em julho contra R$ 705.002 no mesmo dia
do ano anterior.** Não é colapso — é digitação atrasada.

E o CBO oficial do Auxiliar de Seguros é literalmente sete verbos de transcrição:
*"transmitindo propostas, realizando cálculos, conferindo documentos, cadastrando
a apólice, preenchendo propostas de endosso e de renovação, registrando
cancelamento."*

**Isso ataca os sete de uma vez.**

## G.2 Os três caminhos, em ordem de preferência

```
1. API de escrita ......... se existir. Melhor caminho.
                            Validar no Bloco 0.

2. Planilha de importação . o agente lê o PDF, extrai, e entrega o arquivo
                            no formato que o InfoCap importa.
                            O funcionário confere e importa.

3. Portal worker .......... o agente preenche a tela.
                            Já fazemos isso na Allianz.
```

**O caminho 2 é o mais provável e é bom o suficiente** — o trabalho manual morre
do mesmo jeito, sem precisar de permissão nova.

## G.3 A regra que não se negocia

```
o agente NUNCA lança sem conferência humana
o que ele produz é RASCUNHO até alguém aprovar
todo campo extraído mostra de onde veio no PDF
campo que ele não conseguiu ler fica VAZIO e marcado — nunca chutado
```

## G.4 Testes

| # | Prova |
|---|---|
| G1 | campo ilegível fica vazio e marcado, nunca inventado |
| G2 | cada campo aponta para a origem no documento |
| G3 | nada é lançado sem aprovação |
| G4 | o mesmo PDF processado duas vezes dá o mesmo resultado |

---

# 2. Migrations

| Migration | O que faz |
|---|---|
| `..._065_01_carteira_espelho.sql` | espelho reconstruível de apólice, parcela, cliente |
| `..._065_02_comissao_observada.sql` | série de comissão por ramo, por portal, por data |
| `..._065_03_permissoes_infocap.sql` | as flags `p5xx` por corretora |
| `..._065_04_analises_guardadas.sql` | consulta que virou achado (Bloco F) |

Todas idempotentes, expand-first, com APPLY/VERIFY/ROLLBACK escritos antes.
**Ler `MIGRATIONS-AUTHORITY.md` antes de qualquer SQL.**

---

# 3. Gate final

```
[ ] o relatório do Bloco 0 aprovado pelo Founder
[ ] os 5 testes do Bloco A        [ ] os 6 testes do Bloco E
[ ] os 6 testes do Bloco B        [ ] os 7 testes do Bloco F
[ ] os 3 testes do Bloco C        [ ] os 4 testes do Bloco G
[ ] os 4 testes do Bloco D
[ ] a suíte inteira verde
[ ] cada detector validado à mão em 3 casos reais
```

## 3.1 A prova viva

```
1. rodar a varredura na Resulta  → a carteira espelha sem erro
2. abrir o primeiro achado       → o número bate com o InfoCap, conferido à mão
3. pedir um cálculo ao chat      → ele calcula, e o número fecha
4. pedir um cálculo impossível   → ele diz que não fecha, não inventa
5. tenant A pergunta do B        → recusa
```

---

# 4. Riscos

| Risco | Mitigação |
|---|---|
| a API não volta | os blocos D e F são executados enquanto isso |
| os números dos prints estão velhos | Bloco 0 mede tudo de novo antes |
| detector acha coisa que não é | validação à mão em 3 casos antes de entrar |
| varredura vira abuso de API | reuso de token, backoff, Work Run retomável |
| consulta livre vaza entre tenants | filtro injetado pelo sistema + teste com dois tenants |
| espelho vira fonte de verdade | nunca apresentado como tal; reconstruível a qualquer momento |
| refazer o que o InfoCap já faz | Bloco 0 compara com os 35 relatórios existentes |

---

# 5. O que NÃO pode acontecer

```
✗ segundo conector InfoCap ao lado do que existe
✗ store analítico ao lado do Intelligence Fabric
✗ crawler alfabético como substituto de endpoint de listagem
✗ SQL livre sem filtro de tenant injetado pelo sistema
✗ código executado com acesso à rede
✗ espelho apresentado como se fosse o sistema da corretora
✗ detector em produção sem validação à mão
```
