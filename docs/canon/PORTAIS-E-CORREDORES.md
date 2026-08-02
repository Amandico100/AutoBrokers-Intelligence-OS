# Portais e corredores — o que existe, o que é pesquisa, e o que vem depois

> **Documento canônico.** Escrito em **02/08/2026**, na SPEC-064 Bloco H, a
> partir de uma pergunta do Founder: *"não entendi o que são esses 189
> portais."*
>
> 📊 medido · 💭 ilustrativo (CLAUDE.md §12.1)

---

## A pergunta, e a resposta curta

> *"Cada seguradora tem seu portal para as corretoras acessarem. Pode ser que
> tenha mais de um por causa dos nichos, mas não sei se devemos colocar 189
> portais no nosso sistema."*

**Você estava certo, e o número que você chutou estava exato.**

```
o produto tem ......... 📊 17 portais    ← 15 de corretor + 2 de vidros
a pesquisa tem ........ 📊 189 URLs      ← de 18 seguradoras
```

**Os 189 nunca foram 189 portais.** São 189 **endereços** — e a distribuição
denuncia isso na hora:

```
sulamerica ... 39      nenhuma seguradora tem 39 portais de corretor
azul ......... 24
porto ........ 20
tokio ........ 20
```

📊 Quando se olha o que cada endereço é:

```
login_base ......... 37   ← os portais de verdade
sinistro ........... 23
api_catalog ........ 21   ← quais seguradoras têm API pública
suporte ............ 19
mobile_app ......... 19
developer_portal ... 12   ← idem
outros ............. 58   cotação, apólice, cobrança, status…
```

> **É um inventário das propriedades web de cada seguradora, não um catálogo
> de portais a automatizar.** E 78 dos 189 estão marcados `needs_review` — nem
> o próprio levantamento os dá por confirmados.

---

## O que o produto realmente tem — e está certo

📊 Tabela `portals`, **17 registros, todos ativos**:

| Categoria | Quantos | Quais |
|---|---|---|
| **Portal de corretor** | **15** | Allianz · Alfa · Azul · Bradesco · HDI · Mapfre · Porto · SulAmérica · Sompo · SURA · Suhai · Seguros Unimed · Tokio Marine · Yelum · Zurich |
| **Portal de vidros** | **2** | Abra Seu Atendimento · Agende Seu Serviço (Bradesco) |

**Um por seguradora, login e senha da corretora.** É exatamente o desenho que
você descreveu, e ele já está no lugar.

**Nada a fazer aqui.** A estrutura de portais do produto está correta e
completa para o que existe hoje.

---

## Então para que serve o catálogo de 189?

**Para uma coisa só, e ela vale.**

📊 Dentro dos 189 há **33 endereços de API** — 21 catálogos de API e 12 portais
de desenvolvedor, com evidência de fonte oficial e data de verificação.

> Você disse: *"quando acessamos o portal da Allianz para baixar um boleto, nós
> fazemos isso através da API por dentro do sistema. E a ideia é fazer isso
> para todos os outros portais também — porque é mais robusto, e porque a mesma
> estrutura de API vai facilitar renovações e cotações depois."*
>
> **Esses 33 endereços são a resposta a "quais seguradoras já têm API".**

**Regra:** o catálogo é **pesquisa**, não dado de produto.

```
✓ consultar quando for abrir uma seguradora nova
✓ conferir se ela tem API antes de escrever robô
✗ carregar os 189 no banco
✗ mostrar 189 portais para o corretor
✗ tratar 'needs_review' como confirmado
```

Ele vive em `lib/attendance/portal-global-catalog-seed.ts` porque foi gerado
por código (`portal-intake-importer.ts` lê o CSV do levantamento). **Não é
consumido por nenhuma tela, e não deve ser.**

---

## Os corredores — e o que o Atlas já entregou

**Corredor não é portal.** A distinção decide onde cada trabalho acontece:

```
PORTAL     o motor entra no site da seguradora com login e senha
           → boleto, apólice, comissão            → portal_worker

CORREDOR   o motor conversa com a URA da seguradora
           → acionar guincho, vidro, chaveiro     → corridor_playbooks

RAG        o agente conversa com o SEGURADO
           → o que a apólice cobre, o que fazer   → 8.916 cartas
```

### O que o Atlas já mapeou

📊 `ura_maps` — **251 mapas de URA**, em 11 seguradoras:

| Seguradora | Mapas | | Seguradora | Mapas |
|---|---:|---|---|---:|
| **Yelum** | 49 | | Tokio | 24 |
| **Porto** | 41 | | Alfa | 8 |
| **Allianz** | 35 | | Bradesco | 8 |
| **HDI** | 35 | | Azul | 8 |
| **Zurich** | 25 | | Mapfre | 8 |

**É a matéria-prima dos corredores, e ela já existe.** O trabalho da SPEC-063
Bloco F é transformar mapa em corredor — não sair mapeando do zero.

### A ordem, medida

📊 Cartas de conhecimento de **auto**, por seguradora — o que diz onde está o
volume real de atendimento:

```
Allianz .... 439      (708 no total, somando residencial e outros)
Yelum ...... 276
Tokio ...... 251
HDI ........ 184
Youse ...... 177      ← não estava na lista inicial
Porto ...... 165      ← é a 6ª, não a 2ª
Bradesco ... 116
Mapfre ..... 100
```

⚠️ **A SPEC-063 F.2.1 diz que "as 69.150 transcrições dizem quais são".** 📊
Não dizem: `attendance_sessions.insurer_key` é **NULL em 100% das 8.872
sessões**. Quem diz são as cartas. Ver PENDENCIAS.md P-10.

### E os corredores dependem da InfoCap?

**Parcialmente, e a parte que depende é a que importa.**

```
navegar a URA .......... NÃO depende — o mapa está no Atlas
capturar protocolo ..... NÃO depende — a âncora é regex
CONFIRMAR A APÓLICE .... DEPENDE  — e sem isso não se aciona nada
```

O corredor precisa saber **qual apólice**, **qual cobertura** e **se está
vigente** antes de acionar a seguradora. 📊 A única fonte de apólice é a
InfoCap (P-01).

> **Dá para escrever e testar corredor com a InfoCap fora** — o
> `DISPATCH_FINALIZE_MODE=test` percorre o fluxo inteiro e cancela antes de
> abrir. **O que não dá é acionar de verdade.**

---

## O que vem depois desta SPEC

**Uma SPEC própria para portais, quando o Founder mandar.** O desenho já está
decidido e registrado aqui:

```
1. o Cobrador da Allianz vira o MOLDE
   ele já funciona: login, varredura, boleto, envio

2. cada seguradora nova é uma jornada nova no portal_worker
   mesma estrutura, outro mapa de tela

3. antes de escrever robô, conferir se a seguradora tem API
   (é para isso que o catálogo de 189 existe)

4. cobrança primeiro. Renovação depois, se a estrutura sustentar.
```

**E a regra que não muda:** um auxiliar de cobrança por seguradora **não é um
auxiliar novo** — é o mesmo Auxiliar "Cobrança Feita" com mais um portal na
configuração da corretora. Criar um auxiliar por seguradora seria a bagunça
voltando pela porta dos fundos.

---

## Registro rápido

| O quê | Estado | Onde |
|---|---|---|
| 17 portais do produto | ✅ correto e completo | tabela `portals` |
| 189 URLs de pesquisa | 📚 pesquisa, não produto | P-26 |
| 33 endereços de API | 📚 insumo do plano "via API" | P-26 |
| 251 mapas de URA | ✅ matéria-prima pronta | tabela `ura_maps` |
| Corredores implementados | 11 (1 residencial + 10 auto) | `corridor_playbooks.py` |
| Ordem dos corredores | 📊 medida | P-27 |
| Portal de vidros | ✅ existe, 2 portais | P-29 |

---

*Autoridade: CLAUDE.md · SPEC-063 Bloco F · SPEC-064 Bloco H · decisão do
Founder de 02/08/2026.*
