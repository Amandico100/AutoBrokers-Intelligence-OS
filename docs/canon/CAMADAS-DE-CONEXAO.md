# As camadas de conexão — quem paga, quem conecta, quem usa

> **Documento canônico.** Lido no bootstrap de sessão, junto com a
> [`ONTOLOGIA-DO-TRABALHO.md`](ONTOLOGIA-DO-TRABALHO.md).
> **v1.0 · 02/08/2026 · SPEC-064**, a partir de decisão do Founder.

---

## Por que este documento existe

Em 02/08/2026 eu declarei o **Firecrawl** como conector exigido por dois
Auxiliares. Consequência: a tela passaria a dizer, para **todas** as
corretoras — *"Falta conectar: Firecrawl"* — e travaria o botão de ligar num
Auxiliar que funciona perfeitamente, porque **a chave do Firecrawl é do
AutoBrokers e está no ambiente desde sempre.**

O erro não foi o campo. Foi a falta de um conceito: `connector_templates`
tratava tudo como se fosse a mesma coisa.

> **O corretor não pode ser convidado a assinar um serviço que já está pago.**

---

## A regra, em uma frase

> ## A **definição** do conector é sempre global. O que muda é **quem segura a credencial.**

Isso é o que o campo `connector_templates.scope` responde.

---

## As três camadas

### 🌐 `platform` — a AutoBrokers paga, todas usam

```
exemplos ......... Firecrawl · Tavily · conversas internas · documentos internos
credencial ....... nossa, no ambiente da plataforma
a corretora ...... NÃO vê card · NÃO conecta · NÃO tem chave
cobrança ......... pelo uso, no consumo dela
está pronto? ..... SEMPRE. Nunca fica pendente, nunca trava um Auxiliar.
```

**É o modelo de negócio:** entregamos o serviço pronto e cobramos pelo uso.
A corretora usufrui do benefício sem assinar nada, sem gerenciar chave, sem
descobrir que precisa de uma conta em algum lugar.

**Regra dura:** conector de plataforma **nunca** aparece em
`/api/vault/templates`. Se aparecer, a corretora vai tentar conectar — e vai
achar que o produto está pedindo dinheiro dela duas vezes.

### 🏢 `company` — a conta da corretora

```
exemplos ......... InfoCap · portal da seguradora · Google Drive · WhatsApp
credencial ....... da corretora
quem usa ......... TODOS os usuários dela e TODOS os Auxiliares dela
conecta uma vez .. e serve a tudo. Nunca se reconecta por Auxiliar.
```

**A regra que o Founder cravou:**

> *"Se o portal da Allianz estiver conectado, ele deve servir para QUALQUER
> auxiliar que precisar de acesso ao portal da Allianz, e não ter que fazer
> novamente a conexão em cada auxiliar."*

### 👤 `user` — a conta da pessoa

```
exemplos ......... Outlook · Gmail · Notion pessoal
credencial ....... daquele usuário, dentro daquela corretora
três usuários .... três contas, e uma não enxerga a da outra
```

Ainda não há conector desta camada em produção. O campo existe para que o
primeiro nasça no lugar certo — em vez de virar mais um `company` mal
classificado que dá a três pessoas acesso à caixa de e-mail de uma.

---

## O caso que parece exceção e não é

**O portal da seguradora.**

```
o mapa do portal ........ é NOSSO. Nós é que mapeamos a Allianz,
                          a jornada, as âncoras, o corredor.
                          Isso é da plataforma.

o login e a senha ....... são da CORRETORA. É a conta dela,
                          sobre o dado dela.
```

Ele é **`company`**, porque o `scope` diz **quem segura a credencial** — não
quem escreveu o mapa. Todo conector tem definição global; se o scope falasse
de definição, todos seriam `platform` e o campo não serviria para nada.

---

## Como classificar um conector novo

```
Quem paga a conta do serviço?

  a AutoBrokers, e todas as corretoras usam a mesma
     → platform      não aparece como card, nunca fica pendente

  a corretora, uma conta por corretora
     → company       aparece em Conectores, serve a todos os Auxiliares dela

  cada pessoa, uma conta por usuário
     → user          aparece no dashboard da pessoa, só ela enxerga
```

**Em dúvida entre `platform` e `company`, a pergunta que decide é:**
*se duas corretoras usarem isso, elas usam a MESMA conta?*
Sim → `platform`. Não → `company`.

---

## O que nunca pode acontecer

```
✗ card pedindo a chave de um serviço que a plataforma já paga
✗ Auxiliar travado por conector de plataforma
✗ conector `company` conectado duas vezes, uma por Auxiliar
✗ conector `user` dando a uma pessoa acesso à conta de outra
✗ conector novo entrando sem `scope` explícito
✗ chave de plataforma gravada em `tenant_connections`
```

---

## Onde isso vive no código

```
connector_templates.scope          a camada de cada conector
/api/vault/templates               filtra `scope <> 'platform'`
lib/auxiliaries/catalog.ts         conexoesDaCorretora() marca todo
                                   conector de plataforma como pronto
auxiliary_templates.required_connectors
                                   o que cada Auxiliar exige
```

**A verdade sobre o que a corretora tem conectado ainda mora em três tabelas** —
`tenant_connections` (o caminho novo), `portal_accounts` (o portal worker) e
`integrations` (o WhatsApp, anterior ao conceito de conector). `conexoesDaCorretora()`
lê as três de propósito: ignorar qualquer uma faria a tela dizer *"não
conectado"* para quem já fez o trabalho. **Unificar as três é dívida
registrada, e não pode ser feita apagando nenhuma antes de a nova provar que
lê tudo.**

---

*Autoridade: CLAUDE.md §6 · SPEC-064 · decisão do Founder de 02/08/2026.*
