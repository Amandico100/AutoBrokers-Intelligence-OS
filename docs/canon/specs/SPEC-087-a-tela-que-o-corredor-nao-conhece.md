# SPEC-087 · A TELA QUE O CORREDOR NÃO CONHECE

> **O que ela entrega:** quando a seguradora manda uma tela que o corredor não
> sabe responder, **o produto passa a saber disso** — e a rota morta deixa de
> morrer em silêncio.
>
> **v1** · 26/08/2026 · commit base `882b951` · repo `AutoBrokers-FIX`

---

## 🔴 A razão desta SPEC existir — e é o maior número medido no projeto

📊 Medido em 26/08/2026, rodando `match_ura_step` sobre **todas** as telas reais
de URA dos últimos 45 dias, contra **todos** os playbooks da seguradora × 10
subserviços — o casamento mais generoso possível, então **o número é piso, não
teto**:

```
755 telas distintas reais
486 conhecidas
269 CEGAS ....................... 35,6%
 66 delas são MENU (≥2 opções numeradas) — exigem resposta, e não há passo

 allianz  105/208  (11 menus)      yelum  56/154  (26 menus)
 porto     35/105  ( 6)            mapfre 14/26   ( 3)
 zurich    13/52   ( 5)            🔴 tokio 13/13 — CEM POR CENTO cego
```

> **Uma em cada três telas que a seguradora manda, o corredor não conhece.**

## ⚠️ Duas ressalvas honestas sobre esse número

**1. Ele cobre SEIS seguradoras, e existem dez com tráfego.** 📊 Cruzando o
acervo dos mesmos 45 dias:

```
                ocorrências   telas distintas (md5 do texto cru)
 allianz            9.102          2.443
 porto              3.509          1.379
 yelum              3.184          1.113
 🔴 hdi             2.102            795   ← NÃO entrou na medição
 azul                 623            220   ← NÃO entrou
 zurich               505            281
 tokio                379            109
 bradesco             306            141   ← NÃO entrou
 mapfre               182            119
 alfa                 169             63   ← NÃO entrou
```

🔴 **A hdi é a quarta em volume e ficou fora.** As 269 cegas são, portanto,
**piso duas vezes**: pelo casamento generoso e pela cobertura parcial.

**2. Os dois números não são comparáveis, e o executor precisa saber por quê.**
As 755 telas vêm do casador real com o texto **normalizado**; as 6.663 acima
vêm de `md5` do texto **cru** — onde o mesmo menu com um nome diferente conta
duas vezes. ⛔ **Não divida um pelo outro.**

> **O BLOCO 0 do executor começa refazendo a medição nas DEZ seguradoras.**
> É a primeira coisa a fazer, e ela pode mudar o tamanho da fila.

⚠️ **E a tokio tem drift registrado em 25/08 — ontem.** Cem por cento cega, com a
URA mexendo agora.

## 1.1 · 🔴 E o detector de hoje enxerga 6% disso

📊 `route_drift` tem **16 linhas**. Elas nascem de `check_insurer`, que compara
**mapa-ativo × mapa-observado** — ⛔ **não compara tela observada × corredor.**

```
o que o produto detecta hoje ....  o mapa do Atlas mudou
o que dói no atendimento ........  chegou tela e nenhum passo casou
```

**São coisas diferentes, e só a segunda faz o segurado esperar.**

## 1.2 · 🔴 O Alfaiate está morto, e a causa é uma chave

📊 Medido com linha de controle — mesmo mapa, mesmo script, **só a chave muda**:

```
 CHAVE DO SENTINELA          -> simulate()      CONTROLE: chave real -> simulate()
 allianz:todos               -> RAISE KeyError  allianz-auto-whatsapp@v1  -> ok=False
 tokio:todos                 -> RAISE KeyError  tokio-auto-whatsapp@v1    -> ok=True
 ... 10 de 10 LEVANTAM                          ... 10 de 10 RODAM (5 ok=True)
```

[route_sentinel.py:203](../../backend/app/services/atlas/route_sentinel.py#L203) monta
`f"{insurer_key}:{ramo}"`, e 📊 **100% das linhas de `route_drift` têm
`ramo='todos'`** → `allianz:todos`. O registry real usa
`allianz-auto-whatsapp@v1`.

🔴 **Uma causa explica os três zeros de uma vez:**

```
simulator_passed  NULL em 16/16      porque simulate() sempre levanta
auto_applied      false em 16/16     porque passed=None é fail-closed
playbook_overlays 0 linhas           porque apply_auto_overlays nunca é alcançado
```

> ⛔ **A proposta lê esses zeros como *"o auto-publish é um risco vivo a
> desarmar"*, e gasta um bloco inteiro, um gate e uma mutação nisso.**
> **Eles são o atestado de óbito do Alfaiate.** O defeito é o oposto do que ela
> combate: **não sobra automação demais — falta a que existe funcionar.**

⚠️ **E o Bloco A dela, se executado, CIMENTA o bug**: passa a existir um teste
exigindo que aquele caminho nunca escreva.

## 1.3 · O que a proposta traz e não se sustenta

```
📊 grep -c "📊|💭" no arquivo inteiro (48 KB, 2.844 linhas)  =  0
```

🔴 **Nenhum número tem marca**, e ela **reafirma números de 18/08 como se fossem
de hoje** — `structural escalated=4, cosmetic=0` contra **14 + 2** medidos.

📊 E multi-tenant: no arquivo inteiro, `company_id` = **0 ocorrências**,
`service role` = **0**, `CLAUDE.md` = **0**.

---

## 0. O TESTE DO PRODUTO

> **A Yelum manda um menu que o corredor não conhece. Hoje o segurado espera e
> ninguém sabe. Depois desta SPEC, a tela cai numa fila com o texto, a rota e a
> data — e na manhã seguinte alguém a transforma em passo.**

⛔ **Qualquer bloco que não sirva a esse parágrafo sai desta SPEC.**

---

## 2. ⛔ AS TRAVAS

```
⛔ NENHUMA mensagem sai para segurado ou seguradora. NENHUM agente é ligado.
⛔ NENHUMA entrada em portal de seguradora.
⛔ Banco: SELECT livre; escrita só pelas migrations desta SPEC.
⛔ NUNCA imprimir CPF, telefone, apólice, placa ou nome de pessoa.
⛔ NÃO mexer em variável de ambiente de produção.
⛔ NUNCA `git add -A` (P-247).
```

---

# BLOCO A · 🔴 A tela cega vira fila

> **É o único bloco desta SPEC que muda um byte para o segurado na semana que
> vem.** Os outros servem a ele.

## O problema

📊 269 telas reais em 45 dias que nenhum passo casa. **66 são menus** — a URA
pergunta, o corredor não sabe, e ninguém fica sabendo.

## O conserto

O ponto já existe: 📊 [insurer_dispatch_service.py:2471](../../backend/app/services/insurer_dispatch_service.py#L2471),
onde `match_ura_step` devolve `None`. **Hoje ele degrada para `needs_human` e
para.** Passa a **também** registrar.

```
tela_cega
  company_id · seguradora · ramo · playbook_ref
  texto_mascarado          🔴 mascarado, ver o BLOCO C
  e_menu                   ≥2 opções numeradas
  visto_em · visto_quantas_vezes
```

⚠️ **Não é tabela de log.** É **fila de trabalho**: cada linha é uma tela que
alguém vai transformar em passo.

## 🔴 E a dedupe é o que a torna útil

**A mesma tela chega dezenas de vezes.** Sem dedupe, a fila vira ruído em um dia.

```
chave: (seguradora, ramo, hash do texto normalizado)
segunda vez → incrementa `visto_quantas_vezes`, não cria linha
```

📊 **E é o contador que ordena a fila:** a tela vista 40 vezes vale mais que a
vista uma.

## O gate

```
① tela sem passo → 1 linha na fila, com o texto mascarado
② mesma tela de novo → o contador sobe, NÃO nasce linha nova
③ tela COM passo → nada na fila                    (linha de controle)
④ 🔴 menu é marcado como menu                       (são os 66 que mais doem)
⑤ dois tenants: a fila de A não mostra tela de B
```

🔴 **A mutação:** desligue a dedupe e ② tem de ficar **vermelho**.

---

# BLOCO B · 🔴 A chave quebrada — e o Alfaiate volta a existir

## O problema

📊 `f"{insurer_key}:{ramo}"` nunca casa com o registry. **10 de 10 levantam
`KeyError`.**

## O conserto

⚠️ **Uma linha, e ela reanima quatro coisas de uma vez:** o simulador, o gate, os
overlays e o leitor.

```
route_sentinel.py:203    a chave passa a ser a ref real do registry
                         (resolvida pelo mesmo caminho que `get_playbook` usa)
```

## ⛔ Mas reanimar sem freio seria pior que o coma

🔴 **Com a chave certa, `apply_auto_overlays` volta a poder escrever no corredor
— e o piloto começa na semana que vem.**

```
⛔ O auto-apply NASCE DESLIGADO, por variável, e o padrão é DESLIGADO.
   O bloco entrega a capacidade de MEDIR (o simulador roda, o resultado é
   gravado) — não a de APLICAR.
🔴 `simulator_passed` deixa de ser NULL e passa a dizer sim ou não.
   Aí sim dá para discutir auto-apply, com dado.
```

⚠️ **É o oposto do Bloco A da proposta** — que desarmaria o que já está morto.
**Aqui a arma é consertada, descarregada, e o gatilho fica com o Founder.**

## O gate

```
① `simulate()` roda para os 10 mapas ativos, sem `KeyError`
② `simulator_passed` deixa de ser NULL nas linhas novas
③ 🔴 `playbook_overlays` continua com 0 linhas    (o auto-apply está DESLIGADO)
④ 🔴 LINHA DE CONTROLE: ligue a variável num teste, e o overlay É escrito
   ⚠️ sem isto, ③ passa por vacuidade e ninguém sabe se o caminho funciona
⑤ dois tenants
```

---

# BLOCO C · 🔴 A máscara antes da tabela global

## O problema

📊 `route_drift` e `playbook_overlays` são **globais** — sem `company_id`, de
propósito, porque o Atlas é um só. ✅ **A chave global é correta.**

⛔ **O vazamento não é a chave: é a carga.**

```
📊 anchor_from_text (playbook_tailor.py:61)   grava re.escape(texto[:60]) CRU
📊 note                                        grava texto[:120] CRU
📊 16 de 16 linhas de `route_drift` SEM máscara {{slot}}
📊 1 linha com nome próprio provável
```

> **Tráfego de UMA corretora → tabela global → lida por TODAS.**

⚠️ É o mesmo furo que a SPEC-063 fechou nos mapas (115 nós com nome de segurado),
**num escritor que ela não cobriu.**

## O conserto

O mascarador que já existe passa a rodar **antes** de qualquer escrita em tabela
global — `route_drift`, `playbook_overlays` e a `tela_cega` do BLOCO A.

⛔ **NÃO construa um terceiro.** 📊 Já existem dois, e o BLOCO 0 escolhe qual:

```
backend/app/services/intelligence/redaction_service.py
backend/app/services/pii_da_sessao.py
```

🔴 **O critério de escolha é o gate ②, não a elegância:** o que sobrar depois de
mascarar **ainda tem de casar com a tela real**. Um mascarador que troca o menu
inteiro por `{{texto}}` é perfeito em privacidade e inútil como âncora.

⚠️ **E se nenhum dos dois servir**, o BLOCO 0 diz **por que**, com o teste que
mostra a âncora deixando de casar — `CLAUDE.md` §5 proíbe criar em paralelo, e
"não serviu" precisa de prova, não de opinião.

## O gate

```
① texto com nome, CPF, placa ou telefone → sai mascarado
② 🔴 a âncora mascarada AINDA casa com a tela real
   ⚠️ mascarar demais mata o casamento — este teste é o que impede
③ 🔴 LINHA DE CONTROLE: um texto sem PII passa intacto
④ as 16 linhas existentes são remascaradas no backfill
```

🔴 **A mutação:** desligue o mascarador e ① tem de ficar **vermelho**.

---

# BLOCO D · A prova

```
① os gates de A, B, C passam
② 🔴 os quatro agentes `attendance` continuam `is_active=false`
③ 🔴 ZERO mensagens enviadas — para segurado OU seguradora
④ 🔴 `playbook_overlays` continua com 0 linhas ao fim da execução
⑤ a bateria inteira, com o número de rodadas do diário
⑥ dois tenants em todos os blocos
```

---

## 3. 🔴 O QUE SAIU DA PROPOSTA — e o gatilho de cada peça

📊 A proposta tinha **12 blocos, 10 gates, 51 itens de "pronto" e 21 ataques de
red team**. 💭 **3 a 4 semanas**, e parada esperando uma SPEC-089 que não existe
no canon.

| peça | por que saiu | **volta quando** |
|---|---|---|
| **Bloco A (desarmar auto-apply)** | 🔴 desarma caminho **morto** — e cimentaria o bug | ⛔ nunca. O BLOCO B faz o oposto e é o certo |
| drift v2 + fingerprint | 📊 16 linhas em 14 dias não é volume que exija | a fila do BLOCO A passar de ~200 linhas |
| evidence · candidate · sandbox · bateria | infra: não muda byte para o segurado | houver proposta de patch para julgar |
| before/after com a régua | 📊 a SPEC-089 não está no canon | a 089 existir |
| approval `route_publish` | 📊 `grep` no repo = **vazio**. Nasce do zero | alguém precisar aprovar patch |
| release + canário + breaker | canário sobre 10 mapas e 2 corretoras | houver mais corretora e mais mapa |

> ⚠️ **Nada foi julgado ruim. Foi julgado cedo** — e cada linha tem gatilho
> medível.

---

## 4. O que fica pendente

```
P-087-01  🔴 tokio 13/13 telas cegas, com drift de 25/08. É a rota mais quebrada
          medida, e nenhum bloco desta SPEC a conserta — ela só a torna VISÍVEL.
P-087-02  os 66 menus cegos: virar cada um em passo é trabalho de corredor,
          não de SPEC. A fila do BLOCO A é a lista de serviço.
P-087-03  `check_insurer` compara mapa × mapa, nunca tela × corredor. Esta SPEC
          acrescenta o segundo caminho sem tocar no primeiro.
P-087-04  a "Opção B — Route Release Registry" da proposta seria uma segunda
          autoridade de release ao lado de `_PLAYBOOKS`. `CLAUDE.md` §5.
P-087-05  📊 a proposta cita SPEC-093 zero vezes e SPEC-092 zero vezes.
```

---

## 5. A ordem de execução

```
C  →  A  →  B  →  D
```

💭 **~5h.** O BLOCO A domina (tabela, dedupe, o gancho no ponto certo).

🔴 **C vem primeiro, e não é preferência:** o BLOCO A escreve texto de tela numa
tabela nova. **Escrever primeiro e mascarar depois é criar o vazamento e depois
tapá-lo** — e o backfill de máscara é sempre pior que a máscara na origem.
