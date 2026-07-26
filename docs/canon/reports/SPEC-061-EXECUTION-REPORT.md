---
> **Status:** relatório de execução — SPEC-061 Portal Admin Control Plane
> **Branch:** `feat/spec061-control-plane-full`
> **Commit inicial:** `affd55f` · **Commit final:** `7639b3e` · **Data:** 27/07/2026
---

# SPEC-061 — Relatório de execução

## 1. Em uma frase

O Portal Admin passou a ter **autoridade própria, verificável no servidor** —
em vez de um único bit `master` que abria 41 telas e 118 rotas de API para
quem entrasse.

```text
Antes:  entrou como master → pode tudo, ninguém registra nada.
Agora:  cada papel pode só o que deve, toda escrita passa por um portão,
        e a trilha diz por quê — sem vazar segredo.
```

---

## 2. Resultado dos gates

| Gate | Resultado |
|---|---|
| `broker_outcome_regression_pack.py` | **33/33 · GATE VERDE** (era 30/30 ao fim do Bloco 0) |
| `npx tsc --noEmit` | **exit 0** |
| Security Advisor | **ERROR 0 · WARN 0** |
| VERIFY da migration do Control Plane | **9/9 garantias recusaram dado inválido** |
| Canário da Inbox contra produção | 7 consultas, zero erro de coluna |
| Dívida de navegação do Admin | **9 → 0** |

### Casos novos no gate

| ID | O que protege |
|---|---|
| `RBA-01` | Cada papel do Admin pode só o que deve |
| `AUD-02` | A trilha diz por quê sem vazar segredo |
| `INB-01` | A caixa mostra a causa, não o sintoma |

---

## 3. Bloco A — Fundação, autenticação e RBAC

### 3.1 O problema, dito com precisão

As regras da §8.5 — *"o financeiro não acessa conteúdo sensível de corretora"*,
*"o auditor é somente leitura"*, *"o suporte não altera cobrança"* — não estavam
mal implementadas. Elas **não tinham onde ser escritas**. Nenhuma delas é
expressável com um booleano.

E a proteção que existia acontecia **no navegador**: `app/admin/layout.tsx` lia
a sessão de `localStorage` e comparava a rota atual com uma lista de
`masterOnlyRoutes`. Isso esconde a tela e não protege a API — §8.4 já diz:
*"esconder botão é conveniência, não segurança"*.

### 3.2 Schema — `20260727_05`, aplicada e verificada

As sete tabelas do §9, RLS ligada e **zero policy** nas sete. Nove garantias de
conduta, provadas com dado real em Amandus (bloco revertido — nada persistido):

```text
VERIFY_061_A || RECUSOU: G1(papel) G2(unico ativo) G3(prazo obrigatorio)
                         G4(motivo) G5(critico exige motivo) G6(append-only)
                         G7(escrita exige aprovador) G8(snooze com data)
                         G9(sev1 exige postmortem)
             || DEIXOU PASSAR: nada
```

Três decisões que valem mais que o schema:

- **`platform_admin_permission_overrides.expires_at` é `NOT NULL`.** Exceção sem
  prazo é a regra nova que ninguém escreveu. A §9.2 diz "não usar overrides
  como substituto da matriz de papéis"; o jeito de fazer valer é impedir que o
  override sobreviva sozinho.
- **A trilha é append-only por trigger.** Quem mais teria motivo para reescrever
  uma linha é exatamente quem ela existe para registrar.
- **Escrita em nome da corretora exige aprovador.** Ler para ajudar é uma coisa;
  agir em nome dela é outra.

### 3.3 RBAC — `services/control_plane/rbac.py`

51 permissions, 10 papéis. **A matriz é código e o vínculo é dado**: a lista de
permissions muda no deploy que cria a tela; quem tem qual papel muda numa terça
à tarde. Mantida em tabela, o código cobraria uma permission que o banco não
conhece — e a tela sumiria sem explicação.

Fail-closed em cada bifurcação: permission desconhecida nega **até para o dono**,
papel desconhecido não concede nada, data ilegível é tratada como vencida, falha
de leitura devolve lista vazia. `deny` vence papel — é o instrumento de conter
alguém no meio de um incidente.

§8.2: quem já era `master` vira `platform_owner` enquanto os papéis novos não
são atribuídos. Sem isso, aplicar esta SPEC deixaria o Founder de fora do próprio
Admin no primeiro deploy.

### 3.4 BFF e Command Gateway

| Arquivo | Papel |
|---|---|
| `lib/admin/control-plane/authority.ts` | resolve sessão → papéis → permissions. **Não reimplementa a matriz: pergunta ao backend** |
| `lib/admin/control-plane/command-gateway.ts` | toda escrita passa por um portão: autoriza, executa, audita, devolve recibo |
| `app/api/admin/control-plane/me` | o menu é **derivado** das permissions |
| `backend/app/api/control_plane.py` | a autoridade, em um lugar só |

Com 118 rotas de API cada uma decidindo sozinha se audita, a pergunta *"esta rota
audita?"* exigiria ler 118 arquivos. Com um portão, vira *"esta rota passa pelo
Gateway?"* — verificável por busca e por teste.

**Tentativa negada também é registrada.** É assim que se descobre que alguém bate
numa porta que não deveria — ou que um papel está apertado demais para o trabalho
real.

O cache de autoridade dura 30s. Curto o bastante para que revogar papel tenha
efeito quase imediato (§8.4: *"role binding suspenso perde acesso imediatamente"*).
Falha de rede **não** entra em cache: backend fora do ar não pode conceder acesso.

### 3.5 Trilha — `services/control_plane/audit.py`

Uma trilha falha de dois jeitos, e os dois são silenciosos:

1. **guarda de menos** — registra "corretora suspensa" sem o motivo, e seis meses
   depois ninguém responde à corretora por quê;
2. **guarda demais** — copia o `before`/`after` de uma conexão e leva o segredo
   junto, criando um lugar novo onde a chave existe.

O segundo é pior, porque a trilha é justamente o lugar que ninguém apaga.

- **O risco vem da permission, nunca de quem chama.** Deixar o chamador informar
  permitiria registrar suspensão de corretora como `low`, e o CHECK que exige
  motivo deixaria de valer exatamente onde importa.
- **Só o que MUDOU é gravado.** O objeto inteiro nos dois lados transforma
  "limite de 100 para 200" numa parede de trinta campos idênticos.
- **Redação em profundidade, com teto.** Auditoria ilegível não é lida.

---

## 4. Bloco B — "O que precisa de mim"

As SPECs 054–060 produzem trabalho o tempo todo, cada um na sua tabela com a sua
tela. O operador não abre nove telas de manhã: abre uma, e a pergunta é sempre a
mesma. **O rótulo do menu é essa pergunta.**

### Projeção, não cópia (§13.1)

A caixa **lê** as autoridades existentes e não guarda o item. Copiar criaria uma
segunda verdade: a aprovação seria decidida na tela de aprovações e continuaria
pendente aqui — a caixa passaria a mentir.

O que é guardado (`admin_inbox_states`) é só o estado **pessoal**.

### Dedupe por causa (§13.4)

Oito rotinas quebradas pelo mesmo provider fora do ar são **um** problema. Oito
cartões idênticos fazem o operador tratar sintoma; um cartão que diz *"afeta 3
corretoras e 8 rotinas"* faz ele tratar a causa.

A causa deliberadamente **não** inclui a corretora: é juntando corretoras
diferentes que o cartão revela que o problema é de plataforma.

### Três decisões

- **Fonte que a pessoa não pode ler não é consultada.** Ler para depois esconder
  é como dado vaza por um log ou por uma contagem que sobrou na tela.
- **Fonte fora do ar não zera a caixa.** Se aprovações cair, o operador ainda
  precisa ver os incidentes.
- **Caixa vazia diz que está vazia.** Sem a frase, ninguém sabe se está limpa ou
  quebrada.

E o monitor de pesquisa com falha nunca diz "nada mudou": diz *"não consegui
ler"*. A primeira é uma afirmação, e ela é falsa quando ninguém olhou.

### Canário com dado real

As sete consultas rodaram contra o schema de produção **sem erro de coluna**. A
caixa mostraria 2 itens hoje: 1 sinal de alta severidade e 1 Work Run falhado.

---

## 5. Bloco C — Navegação

Três telas existiam com conteúdo real e **sem nenhum link** chegando até elas:

| Tela | Linhas | Onde passou a viver |
|---|---|---|
| `/admin/conversation-logs` | 723 | Conversas › Histórico detalhado |
| `/admin/costs` | 517 | Financeiro › Custo por corretora |
| `/admin/logs` | 222 | Sistema › Registro técnico |

Não foram recriadas nem apagadas: apagar tela que alguém escreveu e ninguém achou
resolve o sintoma errado.

`/admin/integrations` saiu da lista por outro motivo — ela **é** um
redirecionamento. Pôr link de menu para uma página que só redireciona seria um
item que não leva a lugar nenhum. A exceção ficou nomeada, com o motivo escrito.

```text
Antes do Bloco 0:  9 órfãs declaradas (5 delas falsas — ver §6)
Depois do Bloco C: 0
```

---

## 6. Correção de uma medição minha

A baseline do Bloco 0 dizia **9 páginas órfãs**. Estava errada, por dois defeitos
no meu próprio teste:

1. **Lia só `masterMenuItems`.** O Admin serve dois papéis com menus diferentes.
   Cinco das nove são alcançadas normalmente pelo administrador da corretora via
   `companyAdminMenuItems`: `/admin/team`, `/admin/conversations`, `/admin/agent`,
   `/admin/documents` e `/admin/billing`.
2. **Contava link comentado como link.** `// { href: '/admin/integrations', … } //
   HIDDEN` é código desligado.

A dívida real era de **quatro** páginas. Um teste que superestima a dívida é tão
ruim quanto um que a esconde: no primeiro caso alguém "conserta" o que não estava
quebrado.

O teste também passou a comparar rótulos duplicados **por menu**, não somados:
"Conversas" existir nos dois não é ambiguidade, porque ninguém vê os dois.

---

## 7. FATO, INFERÊNCIA e NÃO PROVADO

### FATO — verificado com saída real

- 7 tabelas criadas, RLS ligada, zero policy — consultado no banco.
- 9 garantias de conduta recusaram dado inválido em Amandus, nada persistido.
- 51 permissions e 10 papéis, com cada regra da §8.5 verificada por teste.
- A trilha não deixa segredo passar — nem em campo, nem em texto livre, nem
  aninhado em terceiro nível.
- As duas listas de "exige motivo" (Python e TypeScript) **não divergem** — há um
  teste que compara as duas.
- Gate 33/33, `tsc` limpo, Advisor 0 erros.
- Dívida de navegação zerada.

### INFERÊNCIA — coerente, não observado em produção

- O RBAC nunca decidiu sobre uma sessão real: não há `.env` local nem o endereço
  da API implantada no repositório.
- O Command Gateway nunca executou um comando real ponta a ponta.
- A Inbox nunca foi renderizada com sessão real; o canário provou as **consultas**
  contra o schema de produção, não a tela.

### NÃO PROVADO — e o que falta da SPEC-061

A SPEC-061 tem 3117 linhas e pede, além do que foi entregue:

| Pendente | Bloco |
|---|---|
| Sessões: visão, revogação individual e total, break-glass (§7.3) | A |
| Step-up authentication de fato ligado às ações P3/P4 (§7.4) | A |
| Cockpit 360º por corretora (§14) | B |
| Central de Work Runs e de approvals com ação (§15, §16) | B |
| Hubs de Skills, Tools, MCPs, Auxiliares, Artifacts, Research, Conhecimento | B |
| FinOps, billing, MRR (§10.7) | B |
| Command palette e busca global (§11.3) | B |
| Visual Acceptance Pack e canário Amandus → Resulta → AutoFleet (§Bloco C) | C |
| Migração das rotas históricas com redirect (§6.3) | C |

**Não afirmo que a SPEC-061 está concluída.** O que está pronto é a fundação
sobre a qual o resto se apoia — autoridade, portão, trilha e a primeira tela — e
ela está verde e verificada.

---

## 8. Declaração

Nenhum motor paralelo foi criado. A matriz de papéis vive em **um** lugar; o BFF
pergunta. O Command Gateway chama serviços canônicos e não implementa domínio. A
Inbox é projeção das autoridades das SPECs 054–060, sem cópia. Os índices atendem
consultas existentes.

---

## 9. O que o Founder precisa fazer

1. **Deploy** da API e do worker com este código.
2. Abrir `/admin/governanca` e conferir que o acesso histórico continua
   funcionando (o `master` vira `platform_owner` automaticamente).
3. Atribuir papéis reais às pessoas — hoje ninguém tem papel novo, todos operam
   pelo mapeamento do legado.
4. Rotacionar as chaves expostas do Tavily e do Google Places (roteiro na §9.1 do
   relatório do Bloco 0).
