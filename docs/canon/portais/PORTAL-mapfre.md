# PORTAL MAPFRE — MAPFRE Negócios — o mapa do território

> **Leia a [SPEC-070](../specs/SPEC-070-cobranca-multi-seguradora.md) antes de mexer aqui.**
>
> Estado: 🟡 **FASE 1 EM ANDAMENTO** · credenciais gravadas · porta medida ·
> aguardando a captura do Founder
> Última medição: 12/08/2026

| Marca | Significado |
|---|---|
| 📊 | medido, com data | ❓ | **não medido** | 🔴 | trava séria | 🚫 | o robô nunca toca |

---

# 1. A PORTA

📊 **URL:** `https://negocios.mapfre.com.br/acesso` (gravada no catálogo).

## 1.1 🔴 A trava mais séria não é técnica — é CROSS-TENANT

📊 Depois do login aparece um modal **`Selecione o código interno`** com dois
campos, e o primeiro é uma lista de **corretoras**:

```
Corretora          [ RESULTA CORRETORA DE SEGUROS L  ]
                   [ AUTO FLEET R CORRETORA DE SEGU  ]
Código interno     [ TODOS · 111 · 130183 · 1932 ]  (FLORIANOPOLIS - GC DO BRASIL)
```

> 🔴 **O MESMO login enxerga as DUAS corretoras.** Se a varredura da Resulta
> selecionar a AutoFleet, ela traz os inadimplentes da AutoFleet para dentro do
> `company_id` da Resulta. Isso é **dado atravessando tenant** — o que a
> CLAUDE.md §7 proíbe em qualquer circunstância.
>
> Não é hipótese: está nos dois prints, com as duas corretoras na mesma lista.

**Como fica resolvido, e por que assim:**

1. Cada `portal_accounts` da MAPFRE guarda em `account_label` **o nome exato da
   corretora que aquele login deve selecionar**:
   `RESULTA CORRETORA DE SEGUROS L` · `AUTO FLEET R CORRETORA DE SEGU`
2. A journey **seleciona pelo rótulo** e depois **relê a tela para conferir** que
   a seleção pegou.
3. Se não conferir, ela **para** — `needs_human`. Nunca varre "o que estiver
   selecionado", porque o default do portal é escolha dele, não nossa.

> Isto materializa a **P-108**, que estava anotada como hipótese desde a Tokio
> ("uma corretora pode ter mais de um código"). Aqui é pior: são duas
> **empresas** diferentes atrás do mesmo usuário.

## 1.2 O formulário é Ionic — e os nomes dos campos NÃO são estáveis

📊 Medido na página pública (sem tentar entrar):

```
input[type=text]      name="ion-input-0"
input[type=password]  name="ion-input-1"
```

> 🔴 `ion-input-0` é gerado pelo Ionic **em ordem de renderização**. Um campo
> novo na tela, ou uma mudança de ordem, e o `-0` vira `-1`. Selecionar por esse
> nome é a mesma classe de erro das aspas em entidade da Tokio: funciona hoje e
> falha calado depois. **Seleciona-se por `type`.**

📊 A página é uma SPA (795 KB), com 1 iframe e **nenhum botão visível** no
carregamento — o de entrar nasce por JS. Espera-se o campo, nunca o relógio.

## 1.3 As travas: o que foi medido e o que NÃO foi

📊 Na **página pública de login**: sem captcha, sem Akamai, sem DataDome, sem
Incapsula, sem Cloudflare.

> ⚠️ **Isso é sobre a porta, não sobre a casa.** Em 12/08/2026 eu disse que a
> Yelum não tinha trava nenhuma medindo exatamente isto — e o app logado dela
> roda Akamai. ❓ **As travas do MAPFRE logado não foram medidas** e só serão
> quando houver o HAR de dentro.

## 1.4 O login vai com dígitos, não com pontuação

📊 O Founder informou `030.743.279-36`. Guardamos `03074327936`. O campo tem
máscara: digitar dígitos numa máscara sempre funciona; digitar a pontuação junto
pode duplicar separador e produzir "credencial inválida" — um erro que manda
procurar no lugar errado.

---

# 2. A TOPOLOGIA — o que os prints já mostram

## 2.1 Dois caminhos até as parcelas

```
A) card do home  → "Parcelas Inadimplentes"  → Ver detalhes
B) menu          → FINANCEIRO → Consulta Parcelas
```

📊 O menu de topo, medido: `Cotação` · `Endossos` · `Sinistro` · `Financeiro` ·
`Carteira de Clientes` · `Movimentações Vida` · `Consultar`, e acima
`Atuar` · `Para você` · `Comunicações` · `Agiliza` · `Vistoria Prévia Auto` · `Ajuda`.

📊 Cards do home (`Preciso Atuar`): Propostas para Atuar · **Parcelas
Inadimplentes** · Apólices Emitidas · Prêmio Emitido · Sinistros em Andamento ·
Sinistros Finalizados · **Renovações** · Propostas Recusadas.

> O card `Renovações` é o mesmo padrão da Tokio e da Yelum: o portal já conta
> para nós. Vale para o Auxiliar de Renovação, de graça.

## 2.2 A tela `Parcelas dos Clientes` — os filtros

📊 Da captura:

```
Número da Apólice · Número do CPF/CNPJ do Segurado · Nome do Segurado
Período  [28/07/2026-12/08/2026]     ← 🔴 o padrão é de QUINZE DIAS
Status da Parcela*  [ Todos · Pago · A vencer · Vencida · Cancelada ]
Forma de Pagamento  [ … ]
☐ 1ª Parcela      ☐ Parcelas Reprogramadas
```

> 🔴 **O período padrão são 15 dias.** É a janela mais curta de todas as quatro
> seguradoras já feitas (HDI 30 dias por bloco, Yelum ~90). Uma dívida de dois
> meses não aparece sem alargar. ❓ O alcance máximo não foi medido.

📊 `Status da Parcela` é **obrigatório** (tem asterisco) — não existe busca sem
escolher um. `Vencida` é o nosso.

---

# 3. O ESTADO DA CARTEIRA — e por que ele NÃO bloqueia

📊 Em 12/08/2026, com o período padrão de 15 dias e status `Vencida`:
**`Não encontrado`** nas duas corretoras. O card `Parcelas Inadimplentes` também
marca `0`.

> **Zero inadimplente é um ESTADO, não uma propriedade do portal.** Amanhã muda.
> O que não podemos é confundir "a carteira está limpa hoje" com "não dá para
> construir".

**O que dá para provar sem nenhum inadimplente:**

| Etapa | Dá para provar? | Como |
|---|:--:|---|
| login + seleção da corretora | ✅ | é onde está o risco de verdade (§1.1) |
| a busca e o formato da lista | ✅ | com `Status = Todos` e período largo |
| baixar o boleto | ✅ | 📊 na Tokio e na Yelum o boleto de parcela **A vencer** sai pelo mesmo caminho da vencida |
| a coluna extra de juros/multa da vencida | ❓ | só com um inadimplente real |

📊 A base dessa terceira linha: na **Tokio**, a parcela 4 (a vencer) baixou pelo
mesmo botão da parcela 3 (vencida); na **Yelum**, a parcela 3 `A Vencer` tinha o
mesmo `Boleto Bancário` da parcela 2 `Atrasado`. Duas seguradoras independentes,
mesmo comportamento.

> Então a MAPFRE fecha como **"pronta, com o caso vencido não exercitado"** — e
> o primeiro inadimplente de verdade valida o último palmo. A alternativa
> (esperar aparecer um) só troca trabalho de hoje por trabalho no dia em que
> houver pressa.

---

# 4. O QUE FALTA — a captura da Fase 1

Ver a mensagem de handoff. Em resumo: **HAR de dentro** + os HTMLs da lista e do
detalhe + **um boleto de parcela `A vencer`**, com `Status = Todos` e período
largo para haver linhas de todos os tipos.

---

# 5. HISTÓRICO

| Data | O que |
|---|---|
| 12/08/2026 | Credenciais das duas corretoras gravadas cifradas, URL `negocios.mapfre.com.br/acesso` no catálogo, porta pública medida (Ionic SPA, sem trava **na porta**). 🔴 Achado principal: **o mesmo login enxerga as duas corretoras** — risco cross-tenant, resolvido guardando a corretora-alvo em `account_label` e conferindo a seleção antes de varrer. 📊 Carteira sem inadimplente nas duas corretoras nesta data. |
