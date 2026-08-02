# SPEC-064 — Relatório de execução

> **02/08/2026** · branch `feat/spec064-ontologia-casa-limpa`
> commit inicial `26dab07` · commit final `ca55175` · **10 commits**
> 📊 medido · 💭 ilustrativo (CLAUDE.md §12.1)

---

## Gate final

```
build de produção limpo ....... ✅  287 rotas · 135 páginas estáticas
tsc --noEmit .................. ✅  exit 0
suíte de testes ............... ✅  111 verdes · 0 vermelhos
migrations aplicadas .......... 8, todas com APPLY + VERIFY verdes
advisors de performance ....... 0
motor paralelo criado ......... nenhum
```

**Testes acrescentados nesta SPEC: 7 arquivos.** A suíte foi de 102 para 111.

---

## O que mudou, em uma tela

| Antes | Depois |
|---|---|
| 7 pilares, 2 eram Auxiliares disfarçados | **5 pilares** |
| 3 cliques para ver os Auxiliares | **1 tela, todos os 15** |
| Auxiliares de verdade sem link no menu | catálogo global, visível a todas |
| Cobrança era Rotina se chamando "Auxiliar" numa f-string | **Auxiliar de verdade**, no catálogo |
| 26 de 26 briefings em `pending` mudo | **26 de 26 com estado e motivo** |
| config gravada na instalação e nunca mais | **escrita com histórico de revisão** |
| chat criava e editava, não executava | **chat executa qualquer Auxiliar** |
| 5 capabilities apontando para simulador | **apontam para quem entra na Allianz** |
| cookie de admin sem validação em 8 rotas | **sessão assinada + admin conferido no banco** |

---

## Os dez blocos

### 🔒 I.1 · Segurança — saiu na frente, sozinho

`hasAdminCookie()` devolvia `true` para **qualquer cookie chamado
`smith_admin_session`, com qualquer valor**. Guardava 📊 7 pontos de chamada em
5 arquivos, incluindo **instalar auxiliar em qualquer corretora**.

Passou a usar `requireMasterAdmin()` — sessão iron-session assinada, papel
conferido, e o admin validado no banco a cada request. Mutação exige
same-origin.

> A SPEC dizia "na frente **ou junto**". Discordei do *junto*: buraco aberto,
> conserto pequeno, sem dependência de decisão de produto.

### 📖 A · A ontologia virou documento

[`ONTOLOGIA-DO-TRABALHO.md`](../ONTOLOGIA-DO-TRABALHO.md) — as quatro palavras
com o teste de cada uma, os seis corolários, as três camadas e **os cinco erros
já cometidos**. No bootstrap do CLAUDE.md.

> **Auxiliar TEM Rotina. Auxiliar NÃO É Rotina.**

### 📦 D · O catálogo virou produto

📊 **15 Auxiliares**: 5 disponíveis, 10 "em breve" — cada um com headline,
categorias, o que faz, de onde tira o dado, e **o que falta para existir**.

**Nenhum "em breve" promete número.** Todos dizem o que *será* medido — e há
teste que procura `R$`, `%` e "X mil" na promessa.

**Dois ajustes meus além do texto da SPEC:**

1. **"Venda Casada" virou "Proteção Completa".** Venda casada é prática
   proibida pelo CDC art. 39, I. Vender corretagem com esse nome é problema
   jurídico, não de gosto.
2. A **Cobrança migrou de Rotina para Auxiliar** (D.5, acrescentado): nasce
   desligada, aparece para todas, e a Rotina existente ganhou dono — não sumiu.

📊 **Nenhuma Rotina existe sem Auxiliar dono.**

### 🖥️ C · Uma tela, todos os Auxiliares — e a conexão é da corretora

A peça que o Founder pediu em 02/08:

> *"Se o portal da Allianz estiver conectado, ele deve servir para QUALQUER
> auxiliar, e não ter que fazer novamente a conexão em cada auxiliar."*

A metade difícil já estava certa (conexões são por `company_id`). Faltava o
Auxiliar **declarar** do que precisa. `required_connectors` + trigger que
impede pedir conector inexistente + `conexoesDaCorretora()` calculada uma vez.

📊 Compartilhamento medido: `infocap` serve **10** auxiliares, `whatsapp` 3,
`insurance_portal` 2.

**Duas travas no servidor, não no botão:** "em breve" não instala, e sem a
conexão exigida não instala.

### 🔌 As camadas de conexão — correção do Founder

Eu tinha declarado `firecrawl` como conector exigido. **A tela diria "Falta
conectar: Firecrawl" para todas as corretoras** e travaria um Auxiliar que
funciona — porque a chave é nossa.

> **A definição do conector é sempre global. O que muda é quem segura a
> credencial.**

```
platform   AutoBrokers paga, todas usam, ninguém conecta   firecrawl · tavily
company    a conta da corretora                            infocap · portal
user       a conta da pessoa                               outlook (futuro)
```

**O portal da seguradora é `company`** — o mapa é nosso, o login é dela. O
scope diz quem segura a credencial, não quem escreveu o mapa.

### 🧭 B · Sete pilares viram cinco

```
AutoBrokers · Atendimentos · Auxiliares · Entregas · Personalização
```

**Entregas** substitui três itens que respondiam a mesma pergunta e dá tela a
dois produtores que não tinham nenhuma: os artifacts e as execuções de
Auxiliar. Cinco leituras normalizadas, nenhuma tabela nova.

**A duplicata de conversas** (1.195 linhas chamando `/api/admin/conversations`
de dentro da casa da corretora) foi removida com as 3 rotas de API que só ela
usava.

**Erro meu:** escrevi os redirects em lote e sobrescrevi 📊 **2.758 linhas de
tela real**, apontando duas para destinos inexistentes. Revertido antes de
commitar. O certo é **mover o conteúdo e só então redirecionar** — e há teste
que confere o tamanho do destino.

### 📬 E · Publicar não é entregar

📊 26 de 26 publicações em `pending`, e `delivery_policy.decidir()` com **zero
chamadores**. A política existia, pura e testada. **Ninguém a chamava.**

Toda publicação agora termina com estado final e motivo legível. Canal
indisponível vira **motivo escrito**, nunca silêncio.

**Bug que eu ia mandar para produção:** escrevi `delivered`/`delivered_partial`
e o CHECK da coluna aceita `sent`/`partial`. Os testes passaram porque o banco
falso não valida constraint. O Postgres recusou no backfill.

### ⚙️ F+G · A corretora configura, e o chat executa

`tenant_auxiliary_revisions` tinha **zero referências em código**, e o lado da
leitura estava pronto esperando há semanas.

Escopo fechado: `runtime`, `system_prompt` e `visibility` **não** são
ajustáveis. Campo fora do escopo é **recusado**, não ignorado.

**O chat executa** pelo mesmo `bridge.auxiliary.execute` da Rotina — muda só
`source_type='chat'`.

**E a regra de oferecer**, que o Founder mandou repensar:
[`QUANDO-OFERECER-AUTOMACAO.md`](../QUANDO-OFERECER-AUTOMACAO.md). Separa
**ajuste** de **oferta**, olha o catálogo antes de propor construir, e traz as
travas anti-chatice — nunca na primeira vez, nunca reperguntar o recusado, uma
por conversa, nunca durante um sinistro.

**Erro meu:** ia amarrar `user_id` na montagem do grafo. O próprio arquivo
documentava por que não — o grafo é cacheado por (empresa, agente), e isso faria
o trabalho de uma pessoa nascer no nome de outra.

### 🧹 H · O portal aponta para quem trabalha

**Minha auditoria estava errada.** Eu disse que apagar quebraria o Cobrador.
📊 Medido: **não quebraria, porque nada checa** — `billing_collection.py` não
consulta o Capability Resolver.

E isso é pior: as 5 capabilities resolviam `needs_connection` para **todas** as
corretoras enquanto o trabalho acontecia por fora. **O registro mentia.**

| | ANTES | DEPOIS |
|---|---|---|
| Resulta (tem conta Allianz) | `needs_connection` | **`ACTIVE`** |
| AutoFleet · Amandus | `needs_connection` | `needs_connection` ✓ |

**Dois erros meus, pegos por teste:**
1. Apaguei `portal-intake-importer.ts` achando que era simulador — **é o
   pipeline que gerou o catálogo de 189 portais**. O teste da SPEC-046 pegou.
2. Reescrevi os tipos de memória e o enum ficou incompleto. Recuperados
   verbatim do git.

### 🏠 I+J · Um lugar por conceito, e a documentação para de mentir

**O teste da SPEC-061 me pegou fazendo o que eu proibi:** criei um nono hub no
admin. §10 proíbe item de primeiro nível sem revisão canônica.

> **"O menu não cresce" vale para os dois lados.**

A separação ficou dentro do submenu. **E o conflito canônico foi registrado,
não decidido** — a SPEC-064 I.3 propõe 6 hubs, a SPEC-061 tem 8 aprovados pelo
Founder. FOUNDER-DECISIONS.md **P2**.

Quatro documentos que contradiziam o código, corrigidos. E o
[`GLOSSARIO.md`](../GLOSSARIO.md): um termo, uma definição, e ele desempata.

---

## Migrations aplicadas

| # | O que fez | VERIFY |
|---|---|---|
| `064_01` | 7 colunas de catálogo + CHECK de vocabulário | ✅ |
| `064_02` | 15 auxiliares, nenhum campo vazio | ✅ |
| `064_03` | Cobrança vira Auxiliar; Rotina ganha dono | ✅ |
| `064_04` | `required_connectors` + trigger | ✅ |
| `064_05` | camadas de conexão (platform/company/user) | ✅ |
| `064_06` | backfill de entrega — 26/26 | ✅ |
| `064_07` | capabilities → `portal_worker` | ✅ |
| `064_08` | limpeza (o último passo) | ✅ |

**Nenhuma destrutiva exceto a 08**, cujo escopo foi declarado item a item e
📊 backup registrado antes: 3 templates, 3 instalações, 2 agentes e 1 rotina —
todos com **zero execuções**.

---

## Canário

```
Amandus ...... catálogo global visível · lixo de teste removido · igual às outras
Resulta ...... Cobrança instalada DESLIGADA · portal ACTIVE · 23 briefings 'sent'
AutoFleet .... catálogo visível · needs_connection correto (não tem portal)
```

---

## O que ficou fora, e por quê

Tudo em [`PENDENCIAS.md`](../PENDENCIAS.md) — **29 pendências**, cada uma com o
que destrava, de quem é e o que custa esquecer.

**As que esta SPEC deixou:**

```
P-13  chave de e-mail — canal construído e desligado
P-14  governador de envio — o briefing não sai por WhatsApp sem ele
P-15  artifact sem visualizador na tela da corretora
P-16  duas telas de execução ainda fora da rota do Auxiliar
P-18  auxiliary_events sem escritor
P-26  catálogo de 189 portais sem consumidor
P-28  a capability de portal existe e ninguém a exerce
P2    (FOUNDER-DECISIONS) 8 hubs ou 6 no admin — decisão sua
```

---

## Riscos remanescentes

| Risco | Estado |
|---|---|
| `main` está 118 commits atrás — **nada em produção** | 🧑 aguarda decisão de merge |
| InfoCap 500 bloqueia o atendimento | 🧑 telefonema |
| Os P0 da SPEC-063 continuam abertos | 🤖 próxima SPEC |
| A capability de portal não é exercida | 🤖 P-28 |

---

## Declaração

**Nenhum motor paralelo foi criado.** O executor de entrega chama a política que
já existia; o chat executa pelo mesmo workflow da Rotina; a configuração usa a
tabela de revisões que já estava no schema; e a remoção do Portal Browser foi
precedida do reaponte, com prova antes e depois.

📊 Todos os números deste relatório foram medidos contra o banco de produção
`dcajcvlzcjbmyapmklil` em 02/08/2026.
