# SPEC-064 · Bloco 0 — a auditoria que vem antes do código

> **02/08/2026** · commit base `26dab07` · banco `dcajcvlzcjbmyapmklil` (ao vivo)
> Método: cada `arquivo:linha` citado pela SPEC foi aberto. Cada número foi
> consultado. Nada foi aceito por estar escrito.
> Marcação de números conforme CLAUDE.md §12.1 — 📊 medido · 💭 ilustrativo.

---

## Por que a 064 é a primeira, e não a 063

📊 **Fato novo do Founder (02/08):** nenhuma corretora tem QR pareado, nada está
em produção, e nada será ligado sem ordem dele.

Isso muda o cálculo de risco que ordenava as SPECs:

```
a urgência da 063 era ....... "não ligue antes de consertar"
o estado real é ............. nada está ligado, e nada liga sem ordem
logo ........................ a pressão de ordem some; sobra o que destrava mais
```

E a InfoCap fora do ar cria uma janela: **o atendimento não fica plenamente capaz
enquanto ela não voltar, faça o que fizer.** A 064 é a única SPEC do plano que
**não depende de InfoCap nem de WhatsApp** — executá-la agora não custa nada em
atraso e evita construir o Cobrador e seis corredores dentro da bagunça, para
migrar depois.

> **A 063 sai imediatamente depois, e nada será ligado antes dela.**

---

# 1 · ✅ CONFIRMADO

Abri cada arquivo. **Dez de dez afirmações estruturais da SPEC são verdadeiras**,
e três são piores do que ela descreve.

| Item | Afirmação | Prova |
|---|---|---|
| **I.1** | `hasAdminCookie()` só checa presença | `lib/admin/factory.ts:37-40` — `return Boolean(store.get('smith_admin_session'))`. Sem assinatura, sem expiração |
| **E.1** | `delivery_policy.decidir()` sem chamador | varredura em `backend/app/` — **zero** ocorrências fora do próprio arquivo |
| **G.1** | `factory_tool` nunca cria | `:88` *"[Não crie nada…]"* · `:130` *"[Não instale, não crie rotina e não prometa que já está funcionando.]"* — literal |
| **F.1** | leitura de override existe, escrita não | `auxiliary_context.py:169-178` `_read_contract` prefere `tenant config.contract` sobre `template default_config.contract` |
| **I.2** | submenu "Inteligência" com 9 itens | `app/admin/layout.tsx:308-322` — 9, e 4 respondem "o que o sistema pode fazer" |
| **J.1** | `EXECUTION-MASTER-PLAN` mente | linhas 31 e 33: SPEC-057 e 058 como **"NÃO INICIADO"** — com código e tabelas no banco |
| **J.1** | comentário contradiz o código | `graph.py:872` diz *"OFF p/ attendance"*; `:865` inclui `"attendance"` na lista. **O código está certo** |
| **J.1** | cabeçalho de SPEC revogada | `prompts.py:14` — `# SPEC-013 P0` |
| **J.1** | a página ensina a ontologia errada | `auxiliares/page.tsx:3` — *"SPEC-019 — Auxiliares = Rotinas (motor F2, o caminho ÚNICO)"* |
| **H.4** | campos que ninguém escreve | 📊 5 linhas: `last_run_at` NULL · `release_id` NULL · `work_pattern` NULL |
| **H.1** | Portal Browser é simulação | `"mock session criada; nenhum browser real aberto"` · `real_action_allowed: false` |
| **B.1** | menu com 7 pilares | `lib/navigation.ts:14-28` |
| **D.3** | 3 templates de teste + rotina da Globo | 📊 confirmado no banco |

## 1.1 Três que são PIORES do que a SPEC diz

**a) O buraco do admin é maior.** A SPEC diz que o cookie guarda *"criar template
global e instalar em qualquer corretora"*. 📊 **Medido: 8 pontos de chamada em 6
arquivos**, e incluem também **editar** (`PATCH`) e o caminho `from-agent`:

```
POST   /api/admin/auxiliaries/templates                    criar global
GET    /api/admin/auxiliaries/templates                    listar
PATCH  /api/admin/auxiliaries/templates/[id]               editar global
POST   /api/admin/auxiliaries/templates/[id]/install       instalar em QUALQUER corretora
GET    /api/admin/auxiliaries/templates/[id]/installations listar instalações
POST   /api/admin/auxiliaries/templates/from-agent         criar a partir de agente
```

> **Qualquer pessoa que consiga definir um cookie chamado `smith_admin_session`,
> com qualquer valor, instala um auxiliar em qualquer corretora.**

E o comentário do próprio arquivo diz *"mesmo padrão das rotas /api/admin
existentes"* — **o que sugere que o padrão fraco foi copiado para outros lugares.**

**b) A doença ainda está se reproduzindo.** A SPEC descreve a galeria como uma
rota. 📊 Medido:

```
app/dashboard/auxiliares/galeria/
├── [slug]/                    ← a rota dinâmica, correta
├── follow-up-whatsapp/        ← página FIXA, escrita à mão
└── resumo-atendimentos/       ← página FIXA, escrita à mão
```

**Os dois únicos auxiliares reais ganharam página própria ao lado da rota
dinâmica.** É exatamente o *"o próximo auxiliar nasce numa página nova"* que a
SPEC diz querer evitar — só que já aconteceu, duas vezes.

**c) A inversão da ontologia está escrita em código, em uma linha.**

`backend/app/services/billing_collection.py:586`

```python
f"Auxiliar de Cobranca - {routine.get('name') or 'Cobranca de boletos'}"
```

**Uma Rotina que se apresenta como "Auxiliar" numa string.** 📊 E no banco a
Cobrança está em `routines` (desligada), **não** em `tenant_auxiliaries`.

---

# 2 · ⚠️ CORRIGIDO

**a) A tabela de rotas do Bloco B está incompleta — e é o maior risco de quebra.**

A SPEC lista 9 rotas. 📊 **Existem 46 rotas em `app/dashboard/`.** Ficaram de
fora, entre outras:

```
/dashboard/chat            /dashboard/agente        /dashboard/conversas
/dashboard/documentos      /dashboard/equipe        /dashboard/historico
/dashboard/configuracoes   /dashboard/plano
/dashboard/auxiliares/galeria/[slug]
/dashboard/auxiliares/galeria/follow-up-whatsapp
/dashboard/auxiliares/galeria/resumo-atendimentos
```

**`/dashboard/conversas` e `/dashboard/atendimentos/conversas` coexistem** — dois
caminhos para a mesma coisa, e nenhum dos dois está na tabela da SPEC.

**Correção:** o Bloco B passa a operar sobre o inventário completo, levantado
antes de mover qualquer arquivo. **O teste B2 (nenhuma rota devolve 404) só vale
se a lista de origem estiver completa.**

**b) O teste H4, como escrito, passa errado.**

A SPEC diz que `health`, `last_run_at` e `current_revision` estão *"nulos nas 5
linhas"*. 📊 Medido:

```
health ............. 'unknown'   ← string, NÃO nulo
current_revision ... 0           ← zero, NÃO nulo
last_run_at ........ NULL        ✓
```

Um teste que verifique `IS NULL` **passa sem provar nada** em dois dos três
campos. O teste tem de verificar *"escrito por alguém"*, não *"não é nulo"*.

**c) O número da entrega envelheceu.** SPEC diz 20 de 20. 📊 Hoje: **26 de 26**,
todas `pending`. O defeito é o mesmo e piorou.

---

# 3 · ➕ ACRESCENTADO — o que a SPEC não previu

## 3.1 Apagar o Portal Browser quebra o Cobrador *(o achado mais importante)*

A SPEC H.1 diz: *"Morre: o código, as tabelas, as telas e a documentação."*

📊 **Medido no banco — `capabilities`, cinco linhas ATIVAS:**

| capability_key | nome | provider |
|---|---|---|
| `operational.portal.policy.read` | consultar apólice | **portal_browser** |
| **`operational.portal.billing.read`** | **consultar cobrança** | **portal_browser** |
| `operational.portal.assistance.read` | consultar assistência | **portal_browser** |
| `operational.portal.assistance.prepare` | preparar abertura | **portal_browser** |
| `operational.portal.assistance.request` | solicitar assistência | **portal_browser** |

E o mesmo em código: `lib/capabilities/registry.ts:40-44` e
`capability_resolver.py:33` (`"portal_browser": ["insurance_portal", "browserbase"]`).

> **`operational.portal.billing.read` é exatamente a capacidade que o Cobrador
> exerce.** Ela está declarada sobre o provedor que é 100% simulação — enquanto o
> trabalho real é feito pelo `portal_worker`, que **não é o provedor de
> capacidade nenhuma.**

📊 **E há uma sexta, paralela:** `tenant.portal.execute` — *"Acessar portais
(vidros/corretor)"* — com `provider` vazio.

> **São dois caminhos de portal dentro do Capability Registry.** É a duplicação
> que o Founder quer eliminar, e ela mora dentro de um motor protegido pelo
> CLAUDE.md §5.

**Correção obrigatória — dois passos, nesta ordem:**

```
1. REAPONTAR  as 5 capacidades para o provedor portal_worker,
              consolidar tenant.portal.execute, e provar com teste
              que o Cobrador continua resolvendo a capacidade

2. APAGAR     só então, a implementação do Portal Browser
```

**"Consolidar e migrar antes de duplicar" (CLAUDE.md §5) vale também para
apagar.** Apagar primeiro deixaria o Cobrador exercendo uma capacidade que não
existe mais no registro.

## 3.2 O chat não executa auxiliar — e o Founder pediu que executasse

O Bloco G cobre **criar e editar** auxiliar pelo chat. **Não cobre executar.**

O plano de execução tem isso como decisão **D9** — *"O chat principal chama
qualquer auxiliar… o corretor pede no chat e recebe ali mesmo, na hora"* — **e a
SPEC-064 não a implementa.** Caiu entre as SPECs.

**Acrescento `G.2.5`:**

```
o chat executa qualquer auxiliar instalado, sob demanda, com resposta síncrona
mesmo motor da rotina — não um segundo caminho (CLAUDE.md §5)
o que for irreversível ou externo continua exigindo aprovação
o resultado vira Artifact e aparece em Entregas, igual ao da rotina agendada
```

**Teste G6:** *o mesmo auxiliar, chamado pelo chat e pela rotina, produz o mesmo
Artifact e passa pelos mesmos gates.*

## 3.3 A Cobrança precisa migrar de Rotina para Auxiliar

O Founder foi explícito: *"o auxiliar de cobrança que já está pronto deve
continuar e aparecer para todas as corretoras poderem ativar."*

📊 Hoje ela é uma **Rotina** (`routines`, desligada, só da Amandus), não um
Auxiliar. A SPEC a lista no catálogo como *"existe"* — **mas não descreve a
migração.**

**Acrescento ao Bloco D:** `D.5 — a migração da Cobrança`

```
nasce auxiliary_template  'cobranca-feita', global, visível a TODAS as corretoras
a Rotina existente vira    a Rotina DAQUELE Auxiliar (não some, muda de dono)
o histórico é preservado   as 4 execuções continuam em Entregas
nasce desligada            em todas, inclusive na Amandus
```

**Teste D5:** *as três corretoras veem a Cobrança no catálogo, desligada, e
ligá-la em uma não liga em outra.*

## 3.4 A Amandus deixa de ser exceção

O Founder decidiu: **mesma estrutura, mesmas possibilidades das outras.**

📊 Hoje ela é a única com `tenant_auxiliaries` (5, das quais 3 são lixo) e a única
com agentes `TESTE Runtime Smith` (2, inativos).

**Acrescento ao Bloco H:** limpar os 3 auxiliares de teste, as 3 instalações e os
2 agentes de teste — **e provar que a Amandus enxerga exatamente o mesmo catálogo
global que Resulta e AutoFleet.**

**Teste H5:** *as três corretoras recebem o mesmo catálogo global; nenhuma tem
item que as outras não tenham.*

## 3.5 A ordem interna muda: a segurança sai sozinha e primeiro

A SPEC diz que o Bloco I.1 *"sai na frente ou junto com A–D"*.

**Discordo do "ou junto".** É um buraco aberto agora, o conserto é pequeno e
isolado, e **não depende de nenhuma decisão de ontologia.**

> **I.1 vira o primeiro commit da SPEC, sozinho, antes de qualquer outra coisa.**

---

# 4 · ❓ EM ABERTO — e o que recomendo

| Questão | Recomendação |
|---|---|
| `auxiliary_events` e `auxiliary_template_releases` — ganham escritor ou morrem? | **Ganham escritor.** `auxiliary_events` é o que alimenta Entregas e o histórico por auxiliar (Bloco C.3 §9); sem ele a página nasce vazia. `auxiliary_template_releases` é o versionamento do catálogo global — necessário quando o admin publicar a segunda versão de um auxiliar |
| Quantos "em breve" mostrar | A SPEC limita a 10. 📊 O catálogo tem 13, sendo 3 existentes → **10 "em breve" exatos.** Cabe sem mudar a regra |
| `/dashboard/conversas` × `/dashboard/atendimentos/conversas` | Levantar qual é consumida antes de redirecionar. **Entra no inventário do Bloco B** |

---

# 5 · 🚫 RETIRADO

**Nada.** Nenhuma proposta da SPEC-064 se mostrou inválida na auditoria. As
mudanças são de **completude e ordem**, não de direção.

---

# 6 · O que vai quebrar, e o que fizemos a respeito

| O que mudamos | Quem consome | Mitigação |
|---|---|---|
| rotas do dashboard | links salvos, a própria UI, 2 páginas fixas de galeria | inventário completo antes de mover; **toda rota antiga redireciona**; teste conta 404 |
| provedor das 5 capacidades de portal | `capability_resolver`, Tool Gateway, o Cobrador | **reapontar e provar ANTES de apagar** (§3.1) |
| `tools_config` / catálogo | os 3 agentes | migration idempotente; agentes seguem desligados |
| apagar os itens de teste | nada — 0 execuções | é o último passo da SPEC |
| Cobrança vira Auxiliar | `routine_engine`, `billing_collection` | a Rotina não some — muda de dono; histórico preservado |

---

# 7 · O plano de execução

**Dez blocos, quatro levas.** Ordem interna respeitando "apagar é sempre o
último passo".

```
LEVA 0 · SEGURANÇA                                          ~1 commit
   I.1   cookie de admin validado por assinatura e expiração
         → o buraco fecha antes de qualquer outra coisa

LEVA 1 · A ONTOLOGIA E A ESTRUTURA VISÍVEL                  A · B · C · D
   A     as quatro palavras + docs/canon/ONTOLOGIA-DO-TRABALHO.md
   B     menu de 5 pilares + inventário e redirecionamento das 46 rotas
   C     página única de Auxiliares + a página de cada um (9 seções)
   D     catálogo com 13 auxiliares + migração da Cobrança (§3.3)

LEVA 2 · O QUE LIGA AS PEÇAS                                E · F · G
   E     delivery_policy passa a ser chamada; página Entregas
   F     escrita de configuração por corretora + revisões + isolamento
   G     chat cria, edita — E EXECUTA auxiliar (§3.2)

LEVA 3 · A CASA LIMPA                                       H · I · J
   H     reapontar capacidades → apagar Portal Browser → limpar testes
   I     reorganização do admin (6 seções, um lugar por conceito)
   J     glossário, master plan reconciliado, comentários mentirosos
```

**Migrations** — 4, idempotentes, expand-first, com APPLY/VERIFY/ROLLBACK
escritos antes. `MIGRATIONS-AUTHORITY.md` lido. A de limpeza é a última.

**Testes** — 48 da SPEC + 3 acrescentados (G6, D5, H5) = **51**, mais a suíte
existente (102 arquivos) verde.

---

# 8 · O que NÃO entra nesta SPEC

```
✗ construir os 10 auxiliares "em breve"   um por vez, SPECs próprias
✗ os P0 de atendimento                    SPEC-063, imediatamente depois
✗ corredores novos                        SPEC-063 Bloco F
✗ InfoCap, carteira, detectores           SPEC-065, quando destravar
✗ e-mail definitivo (SES)                 SPEC-069
```

---

*Auditoria feita sem alterar nenhum dado de produção. Nenhuma migration
aplicada. Nenhum segredo exibido.*
