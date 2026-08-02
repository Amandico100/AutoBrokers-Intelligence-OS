# Auditoria forense de entrada — o novo líder mede antes de concordar

> **02/08/2026** · commit base `2a9b04e` · branch `feat/spec061-control-plane-full`
> Banco medido ao vivo: `dcajcvlzcjbmyapmklil` (produção).
> Método: nada foi aceito por estar escrito. Cada afirmação foi conferida contra
> banco, código ou o servidor de terceiro. **Separo FATO, INFERÊNCIA e
> RECOMENDAÇÃO** (CLAUDE.md §12).

---

## Veredito em cinco linhas

```
as SPECs 063 e 064 estão CERTAS ......... auditei os P0 um a um; existem
o achado-bandeira do produto está ERRADO  a "comissão zero" é leitura errada
                                          de um relatório de inadimplência
a InfoCap NÃO está fora do ar ........... o servidor responde e discrimina
a diferenciação (SUSEP) é REAL .......... verifiquei hoje, byte a byte
a tese de dinheiro NUNCA foi medida ..... e é a base de 065 e 067
```

---

# 1 · ✅ CONFIRMADO — o que medi e está certo

## 1.1 Os P0 da SPEC-063 são todos reais

| # | Afirmação da SPEC | Como confirmei |
|---|---|---|
| **B2** | ternário morto zera `agent_id` | `pairing_orchestrator.py:493` — `"agent_id": None if purpose == "observer" else None` — **literal** |
| **B1** | sem `agent_id`, escolhe o agente ativo mais antigo | `langchain_service.py:199-210` — `.eq("is_active",True).order("created_at").limit(1)`, **sem filtro de papel nem de público** |
| **B1** | na Resulta, o mais antigo é o copiloto interno | banco: CORE `20845996` criado **21/06 00:36:49** `is_active=true`; Saionara **04:45:28** `is_active=false` |
| **B1** | o prompt do CORE manda entregar CPF sem mascarar | `core/prompts.py` — *"É PROIBIDO recusar dado… repasse-o por completo (ex.: o CPF do segurado, **sem mascarar**)"* — **literal** |
| **B3** | `request_human_agent` não anexada | `tools_config = {}` nos 3 agentes de atendimento; `graph.py:245` só anexa se `human_handoff.enabled` |
| **B4** | handoff só faz UPDATE | `tools/human_handoff.py:86-99` — um `UPDATE conversations`, zero import de envio |
| **B5** | tela e backend leem tabelas diferentes | `human_support_destinations` tem **só Amandus** (2 linhas, uma duplicada inativa); Amandus tem `acionamento_profile = {}` |
| **B8** | buffer sem tenant na chave | `message_buffer_service.py:36-38` — `f"whatsapp_buffer:{phone}"` |
| **D1** | `observer` pode virar canal de saída | `billing_collection.py:403-414` — rank 2, mas `return rows[0]` se for a única |
| **E** | zero skill de cobrança | 20 skills registradas, nenhuma de cobrança/boleto/inadimplência |

## 1.2 Os números do banco

| Afirmado | Medido | |
|---|---|---|
| 8.916 cartas publicadas | **8.916** | ✅ exato |
| 8.872 conversas encerradas | **8.872** | ✅ exato |
| memórias da corretora = 0 | **0** (`company_memories`, `user_memories`) | ✅ |
| 12 detectores, 0 olham o negócio | **12**, todos `automacao/conexoes/operacao/qualidade` | ✅ |
| 2 rotinas, uma é a Globo | **"Notícias Principais da Globo"**, ambas desligadas | ✅ |
| 6 templates, 3 TESTE | **6, 3 arquivados TESTE** | ✅ |
| 5 auxiliares instalados, todos Amandus | **5, todos Amandus, `last_run_at` NUNCA em todos** | ✅ |
| 7 pilares de menu | **7** (`lib/navigation.ts:14-28`) | ✅ |
| Portal Browser é 100% simulação | `"mock session criada; nenhum browser real aberto"` | ✅ |
| Resulta InfoCap nunca usada | `last_used_at = NULL` | ✅ |
| AutoFleet sem InfoCap | nenhuma linha | ✅ |

## 1.3 A diferenciação é real — e é o achado mais sólido do acervo

**Verifiquei eu mesmo, hoje, sem credencial:**

```
POST https://www2.susep.gov.br/safe/menumercado/REP2/Produto.aspx/Consultar
     numeroProcesso=15414.002216/2004-57

→ HTTP 200 · 72.638 bytes · 72 links .pdf
```

**Bate byte a byte com o que a pesquisa afirmou.** As condições gerais versionadas
por vigência existem, são públicas, e a Allianz mudou aquele produto 72 vezes.
A tese da SPEC-066 está de pé.

---

# 2 · ⚠️ CORRIGIDO — o que a documentação diz errado

## 2.1 O achado-bandeira do produto é uma leitura errada

O prompt do novo líder, o `HANDOFF` §10 e o `00-LEIA-PRIMEIRO` abrem com isto:

```
2013 · Residência Digital    3 apólices   R$   593,83   R$ 17,76   → 2,99%
2024 · Empresa PME           1 apólice    R$ 1.297,56   R$  0,00   → ZERO
```

> *"Ou a comissão é zero de verdade… Ou é erro de cadastro."*

**FATO — os dois números existem no banco. A interpretação não se sustenta.**

Fui à evidência bruta (`portal_jobs`, varredura de 15/07) e fiz a aritmética:

```
106,03 + 107,17 + 380,63 = 593,83     ← as três parcelas ATRASADAS
  0,00 +   0,03 +  17,73 =  17,76     ← a comissão DAQUELAS TRÊS PARCELAS
```

**Aquilo não é a produção da corretora no ramo. É o subtotal do relatório de
INADIMPLÊNCIA.** A "taxa de 2,99%" é comissão-de-parcela-atrasada dividida por
valor-de-parcela-atrasada — uma razão sem significado de negócio.

E a "Empresa PME com comissão ZERO" é **uma única parcela vencida**, a **4/4**.

**O padrão que a análise não considerou:**

| parcela | valor | comissão | |
|---|---|---|---|
| **4/4** (última) | 1.297,56 | **0,00** | |
| **10/10** (última) | 106,03 | **0,00** | |
| 3/10 | 96,95 | 0,03 | |
| 3/10 | 107,17 | 0,03 | |
| 2/7 | 380,63 | 17,73 | |

**As duas linhas com comissão zero são as duas últimas parcelas.** A explicação
mais provável — comissão antecipada nas primeiras parcelas, prática padrão do
mercado — **não aparece na falsa dicotomia "ou é zero de verdade ou é erro".**

> **INFERÊNCIA (não provada — 5 pontos de dado não provam padrão):** a comissão é
> antecipada. **FATO:** a conclusão publicada foi construída sobre um relatório
> lido como se fosse outro.

**Também testei e derrubei uma hipótese minha:** achei que o robô via 68 linhas e
processava 4 (perda de 94%). Fui ao código: `inadimplentes_rows_seen` acumula a
mesma linha a cada clique de ramo. O portal mostrou 4 mesmo. **Errei, medi, e
estou registrando o erro.**

## 2.2 A InfoCap NÃO está fora do ar

Você pediu para conferir. **Testei o servidor hoje, sem credencial, sem alterar
nada:**

```
GET  /                          → HTTP 403   (servidor responde)
POST /login  conta inexistente  → HTTP 403   "Usuário sem permissão de acesso ao Corp+."
```

**O servidor está no ar e discriminando** — devolve exatamente o mesmo 403 que a
própria auditoria anterior registrou como controle. **A teoria "o servidor deles
quebrou" está morta.**

O que continua verdade é mais estreito e mais acionável: **o HTTP 500 acontece
com aquelas duas contas.** Isso aponta mais para cadastro/permissão do que para
falha de infraestrutura — e "permissão" é exatamente o que a auditoria já dizia
estar bloqueado (`p500/p501`).

**Não consegui fechar** porque não há `.env` local e a credencial está no Vault.
É um comando, e preciso de você.

## 2.3 A gravidade de B10 está subestimada

**FATO:** Resulta e AutoFleet apontam para **o mesmo grupo de WhatsApp**:
`120363427334937446@g.us`.

A SPEC classifica como **P1**. **Discordo: é P0.** Um handoff de segurado da
AutoFleet entrega dossiê com nome, CPF e conversa dentro de um grupo que a
Resulta lê. CLAUDE.md §7 é literal: *"Nenhum dado atravessa tenants."*

## 2.4 O vazamento de CPF tem dois caminhos, não um

A SPEC aponta o prompt. **O prompt é um dos caminhos. O outro é a tool:**

```
infocap_tool.py:371  "Monte sua FICHA do atendimento com: titular, CPF, ..."
infocap_tool.py:508  f"- Titular: {titular}" + f" - CPF/CNPJ: {pack.get('document')}"
infocap_tool.py:532  f"- CPF/CNPJ: {r.get('client_document')}"
```

**Quem consertar só o prompt vai achar que resolveu, e o vazamento continua** —
inclusive no ramo `client_facing`, que é o do segurado.

## 2.5 Números que se moveram

```
briefing_publications ..... SPEC diz 20 · são 26 · 100% ainda 'pending'
```

O defeito é real e piorou. O número da SPEC envelheceu em um dia.

---

# 3 · ➕ ACRESCENTADO — o que nenhuma SPEC previu

## 3.1 A AutoFleet tem um agente ativo sem prompt nenhum

**FATO:** agente `c95de02a` "AutoBrokers" da AutoFleet — `is_active = true`,
`agent_enabled = true`, **`agent_system_prompt = NULL`**.

Com o defeito B1, é ele que responderia o segurado da AutoFleet: um agente ativo,
**sem uma linha de instrução**, e portanto sem nenhuma das travas do prompt.
**Não está na lista dos doze bloqueios.**

## 3.2 O handoff mente ao segurado em todo caminho de falha

`tools/human_handoff.py` — quando o UPDATE não encontra a conversa (`:109-117`)
**e** quando estoura exceção (`:119-126`), a tool devolve:

> *"Um atendente foi solicitado. Em breve você será atendido."*

**Sucesso declarado em cima de falha.** O Bloco B acrescenta a notificação — mas
se a notificação falhar, o segurado continua sendo informado de que alguém vem.
**A regra que falta: caminho de falha nunca afirma sucesso.**

## 3.3 O handoff escreve sem filtro de tenant

`.update({...}).eq("session_id", session_id)` — **sem `company_id`**. CLAUDE.md §7
exige filtro no service, precisamente para não depender de o `session_id` ser
único. É violação de regra escrita, mesmo que hoje não estoure.

## 3.4 Um Work Run pode entrar na fila e sumir para sempre

**FATO:**

```
intelligence.detect_signals · queued · criado 28/07 · parado há 5 dias
intelligence.detect_signals · queued · criado 30/07 · parado há 2 dias
       lease_owner = NULL · heartbeat_at = NULL · next_attempt_at = NULL
```

**Nunca foram arrendados.** Não é "falhou e vai tentar de novo" — é
*desapareceu*. Não há dead-letter nem alarme para `queued` sem lease.

**E o mais grave:** existe a regra `operacao.work_run_travado`, ela **rodou hoje
às 14:04**, e **não pegou nenhum dos dois**. O detector que existe para achar
trabalho travado não acha trabalho travado. Os únicos sinais que o motor produz
são um `operational_backlog` por dia.

> A SPEC-055 entregou a fila durável. **Durável não é o mesmo que observável.**

## 3.5 70.576 linhas mortas sem política de retenção

```
attendance_transcripts_copias_removidas_20260728 ....... 58.091
observed_events_copias_removidas_20260728 .............. 12.485
```

Backup de uma deduplicação de 28/07. Sem dono, sem prazo, sem registro.

## 3.6 O defeito de documentação que causou o erro do §2.1

Em `00-LEIA-PRIMEIRO.md` §3, isto aparece:

> *"**R$ 2.180 da sua comissão não foi gerada** porque 41 parcelas estão
> atrasadas. **6 apólices têm cancelamento previsto…**"*

**Nenhum desses números existe.** O real é 4 parcelas e R$ 17,76 de comissão.

É *copy ilustrativa* — legítima. **Mas está formatada exatamente igual a um
número medido**, no mesmo documento, com o mesmo negrito. Nem você nem a próxima
LLM conseguem distinguir.

> **É assim que a alucinação entra: não por invenção, mas por um número de
> exemplo que, três documentos depois, é citado como medição.**

## 3.7 As SPECs novas são um terço do tamanho das executadas

```
SPEC-060 · 3.425 linhas        SPEC-063 ·   826
SPEC-061 · 3.117 linhas        SPEC-065 ·   861
SPEC-062 · 3.523 linhas        SPEC-066 ·   746
```

**INFERÊNCIA:** compressão de contexto no fim da sessão anterior. Não invalida o
conteúdo — as 063/064 que auditei são densas e certas. **Mas 065, 066 e 067
descrevem trabalho maior com menos detalhe**, e é onde eu esperaria encontrar as
lacunas.

## 3.8 O robô da Allianz parou em 15/07

18 dias sem rodar. E as "18 varreduras" são 14 quase-duplicatas em 08/07, 2 em
09/07, 1 em 11/07 e 1 em 15/07. **Quatro dias distintos, não dezoito.**

---

# 4 · A InfoCap — diagnóstico fechado em 02/08/2026

📊 **Medido com as credenciais reais, contra `https://api.corpnuvem.com`.**
Somente leitura. Nenhuma alteração.

## 4.1 A tabela que fecha o caso

| Requisição | Resposta | Tempo |
|---|---|---|
| `/seguradoras`, `/ramos`, `/cotacoes`, `/atendimentos` — sem token | **401** | 0,60–0,62 s |
| `/comissao` — sem token | **403** | 0,60 s |
| `/login` — e-mail inexistente | **403** *"sem permissão de acesso ao Corp+"* | 0,81 s |
| `/login` — e-mail certo, **senha errada** (3×) | **400** *"Usuário ou senha incorretos"* | 0,87 · 0,89 · 0,87 s |
| **`/login` — credencial CORRETA, Resulta (4×)** | **500** | **16,36 · 16,44 · 16,45 · 16,43 s** |
| **`/login` — credencial CORRETA, AutoFleet** | **500** | **16,29 s** |
| `/login` — correta, variando `aplicacao` = 1, 2, 3, 10, ausente | **500** | 16,18–16,40 s |

## 4.2 O que essa tabela prova

```
✅ as credenciais estão CERTAS
      senha errada devolve erro DIFERENTE, específico e rápido.
      o servidor distingue as duas coisas.

✅ a autenticação PASSA
      o 500 só acontece no caminho da senha certa.

✅ a API está SAUDÁVEL
      toda rota responde em menos de 0,7 s.

✅ o defeito é DEPOIS do login, e é TIMEOUT
      16,2–16,5 s em onze medições, desvio de 0,3 s.
      erro de lógica não leva sempre o mesmo tempo. Timeout leva.

🚫 NÃO é bloqueio de segurança, abuso ou invasão
      bloqueio devolve 403/429 e é INSTANTÂNEO — e valeria
      também para a senha errada. Aqui é o contrário:
      só quebra quando dá certo.

🚫 NÃO é a flag de permissão (p500/p501)
      falta de permissão devolve 403, como no e-mail inexistente.
```

## 4.3 O veredito

> **A CorpAPI autentica os dois usuários com sucesso e, logo em seguida,
> trava por 16 segundos numa operação do lado dela e devolve 500.**
>
> É bug do fornecedor, num ponto muito específico e muito diagnosticável:
> a montagem de sessão/perfil logo após a autenticação.

**O telefonema muda de natureza:** não é "não consigo entrar", é
**"vocês têm um timeout de 16 s no post-login destas duas contas — a
autenticação passa, o que vem depois estoura"**. Isso é uma hora de trabalho para
o time deles, não uma investigação.

## 4.4 A consequência que ninguém tinha mapeado

**Não existe tabela de apólice no banco.** E `POLICY_DATA_PROVIDER_SOURCE`
**não é lido por nenhuma linha de código** — é variável morta.

```
logo:  a única fonte de apólice do sistema é a API da InfoCap
       e ela está fora
```

> **O agente de atendimento depende dela para confirmar apólice, cobertura e
> para acionar corredor.** Ligar o atendimento hoje entrega um agente que não
> consegue confirmar uma única apólice.
>
> **A InfoCap não bloqueia só a SPEC-065. Bloqueia o objetivo nº 1.**

---

# 4-A · ❓ EM ABERTO

| O que | O que falta |
|---|---|
| Coluna viva de sinistralidade do SES | a URL que testei devolveu 404; não desmenti, só não confirmei |
| Regra de comissionamento por produto | 5 parcelas não bastam — a resposta está no extrato de comissão |

---

# 5 · Onde eu apostaria CONTRA este plano

**Nas SPECs 065 e 067 — a carteira e o Descobridor.**

Não porque estejam mal escritas. Porque **toda a tese de dinheiro delas nunca foi
medida em dado real**, e as três provas que sustentam essa tese são:

```
1. o achado da Allianz .......... é leitura errada de outro relatório (§2.1)
2. os agregados da InfoCap ...... last_used_at = NULL em TODAS as conexões
                                  nenhuma foi chamada uma única vez
3. os R$ 469 mil/ano ............ derivados de prints de painel, não de query
```

**A única medição real de comissão em risco que existe no sistema inteiro é
R$ 17,76.**

Isso não quer dizer que o dinheiro não esteja lá. O mecanismo é real e
documentado. **Quer dizer que estamos prestes a construir duas SPECs grandes
sobre uma tese que nunca encostou em dado.**

E o custo de descobrir isso é baixíssimo: **a InfoCap responde `/cotacoes` e
`/atendimentos` hoje, liberados, e nunca foram chamados.**

> **RECOMENDAÇÃO:** antes da 065, uma medição de 1–2 dias. Não é SPEC, é uma
> query. Se der R$ 469 mil endereçáveis, a 065 e a 067 ficam blindadas e o preço
> se justifica sozinho. Se der R$ 15 mil, **é melhor descobrir agora do que
> depois de duas SPECs.**

---

# 6 · O que eu mudaria na ordem

```
HOJE:  063 → 064 → 065 → 066 → 067 → 068

EU:    063 (os P0 — sem discussão, é o que impede incidente)
        ↓
       MEDIÇÃO DO DINHEIRO  (1-2 dias, não é SPEC)
        ↓
       064 (a casa limpa — independe do resultado da medição)
        ↓
       065/066/067 na ordem que a medição indicar
```

**Por quê:** a 063 é urgente e certa. A 064 é ortogonal. **A medição custa dois
dias e pode reordenar tudo que vem depois.**

---

# 7 · Regras que proponho acrescentar ao CLAUDE.md

## 7.1 Número medido e número ilustrativo têm marcação obrigatória

```
📊  medido — com data, fonte e query
💭  ilustrativo — exemplo de copy, nunca citável como fato
```

**É a correção estrutural para o problema do §3.6.** Custa nada e é permanente.

## 7.2 Caminho de falha nunca afirma sucesso

Nenhuma tool devolve texto de sucesso quando o efeito não aconteceu. Vale como
teste, não como convenção (§3.2).

## 7.3 Toda fila durável tem alarme de abandono

Um item sem lease além do prazo vira incidente visível. Sem isso, `durável`
significa `perdido em silêncio` (§3.4).

---

# 8 · O que ficou bom e eu manteria sem tocar

Para ser justo com quem escreveu:

- **O Bloco 0 obrigatório em toda SPEC** — é a melhor regra do projeto. Foi ele
  que produziu este relatório.
- **A separação corredor × RAG** (063 Bloco D) — correta e bem argumentada.
- **A ontologia das quatro palavras** (064 Bloco A) — resolve confusão real,
  medida, e o teste automático de que Rotina não existe sem Auxiliar é elegante.
- **"Número vai para tabela, cláusula vai para RAG"** — a regra mais importante
  do acervo, e certa.
- **A leitura do fosso competitivo contra a Segura** — o argumento de que um
  produto pago por seguradora não pode ser adversarial a ela é estrutural e
  correto.
- **A SPEC-067 Bloco B** (registrar o que o corretor fez sem o sistema sugerir) —
  concordo com o líder anterior: é a peça mais elegante do plano.

---

*Auditoria feita sem alterar nenhum dado. Nenhuma credencial exibida. Nenhuma
migration aplicada. Nenhum motor paralelo criado.*
