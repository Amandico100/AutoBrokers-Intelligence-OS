# Os corredores, rota por rota — o que liga hoje e o que falta

> 🔴 **Três retratos, três datas, e elas estão escritas porque são diferentes de propósito:**
>
> | o que | medido em | de onde |
> |---|---|---|
> | **quantas pessoas pediram** (`pedidos`) | **28/09/2026** | `observed_events`, o banco — vivo |
> | **a nota da régua** (`qualidade`) | **28/09/2026** | o corpus versionado no commit `f9b7204` |
> | **dá para ligar?** | **28/09/2026** | a simulação com as telas reais no commit `a83dc06`, `simular_corredor.py --todas` |
>
> ⚠️ O banco é de hoje; o corpus é do commit. Comparar os dois números de uma mesma rota é legítimo — comparar sem ver as datas, não.

## 🔴 A frase que o Founder pode dizer a uma corretora

> **De 73 rotas medidas, o sistema resolve sozinho 34% (25), 3% (2) vão para uma pessoa, e 63% (46) ainda não dão para ligar.**

⚠️ **E a segunda metade da frase é obrigatória, com o número exato:** das 46 que ainda não ligam, **31 não têm uma conversa gravada** — essas não são falha do robô, e só um acionamento real as destrava. As outras **15** têm conversa: nelas o material existe e **falta código nosso**.

## 🔴 DUAS PERGUNTAS, NUNCA UMA

```
DÁ PARA LIGAR?   binária     SIM · VAI PARA UMA PESSOA · FALTA CAPTURA
QUALIDADE        a régua, %  0–100 — serve para PRIORIZAR, não para decidir
```

Uma rota pode ter qualidade baixa e **dar para ligar**; e uma rota com qualidade alta pode **não** dar, por falta de captura. Foi a lição da SPEC-117: *uma régua não serve para duas perguntas*.

🔴 **A `%` substituiu o `58/76`.** O denominador da régua muda por rota (76, 70, 64…), porque itens que não se aplicam saem da conta. 📊 `42/64` **parece** pior que `48/76` e é melhor: 66% contra 63%. O bruto continua na tabela, para quem for auditar.


## ATENDE SOZINHO — 25 de 73 (34%)

*o sistema resolve sozinho, do começo ao protocolo*

| rota | pedidos | qualidade | bruto | por quê | 🔴 o que destrava |
|---|---:|---:|---:|---|---|
| `allianz/auto/guincho` | 29 | 95% | 72/76 | responde tudo e chega ao fim | ✅ nada — esta rota está pronta para ligar |
| `allianz/residencial/eletricista` | 5 | 95% | 72/76 | responde tudo e chega ao fim | ✅ nada — esta rota está pronta para ligar |
| `yelum/auto/socorro_mecanico` | 5 | 93% | 54/58 | responde tudo e chega ao fim | ✅ nada — esta rota está pronta para ligar |
| `alfa/auto/guincho` | 4 | 95% | 72/76 | responde tudo e chega ao fim | ✅ nada — esta rota está pronta para ligar |
| `porto/auto/bateria` | 4 | 95% | 72/76 | responde tudo e chega ao fim | ✅ nada — esta rota está pronta para ligar |
| `yelum/residencial/encanador` | 4 | 95% | 72/76 | responde tudo e chega ao fim | ✅ nada — esta rota está pronta para ligar |
| `allianz/residencial/limpeza_caixa_dagua` | 4 | 94% | 66/70 | responde tudo e chega ao fim | ✅ nada — esta rota está pronta para ligar |
| `allianz/residencial/ar_condicionado` | 4 | 88% | 67/76 | responde tudo e chega ao fim | ✅ nada — esta rota está pronta para ligar |
| `allianz/auto/bateria` | 3 | 95% | 72/76 | responde tudo e chega ao fim | ✅ nada — esta rota está pronta para ligar |
| `allianz/auto/pneu` | 3 | 95% | 72/76 | responde tudo e chega ao fim | ✅ nada — esta rota está pronta para ligar |
| `azul/auto/bateria` | 3 | 95% | 72/76 | responde tudo e chega ao fim | ✅ nada — esta rota está pronta para ligar |
| `porto/residencial/encanador` | 3 | 92% | 70/76 | responde tudo e chega ao fim | ✅ nada — esta rota está pronta para ligar |
| `allianz/residencial/chaveiro` | 2 | 95% | 72/76 | responde tudo e chega ao fim | ✅ nada — esta rota está pronta para ligar |
| `yelum/auto/pneu` | 2 | 95% | 72/76 | responde tudo e chega ao fim | ✅ nada — esta rota está pronta para ligar |
| `zurich/auto/guincho` | 2 | 94% | 60/64 | responde tudo e chega ao fim | ✅ nada — esta rota está pronta para ligar |
| `porto/auto/tecnico` | 2 | 91% | 64/70 | responde tudo e chega ao fim | ✅ nada — esta rota está pronta para ligar |
| `yelum/residencial/eletricista` | 2 | 88% | 67/76 | responde tudo e chega ao fim | ✅ nada — esta rota está pronta para ligar |
| `alfa/auto/pneu` | 1 | 92% | 70/76 | responde tudo e chega ao fim | ✅ nada — esta rota está pronta para ligar |
| `hdi/auto/socorro_mecanico` | 1 | 90% | 52/58 | responde tudo e chega ao fim | ✅ nada — esta rota está pronta para ligar |
| `allianz/residencial/consulta_veterinaria` | 1 | 89% | 62/70 | responde tudo e chega ao fim | ✅ nada — esta rota está pronta para ligar |
| `azul/auto/tecnico` | 1 | 89% | 62/70 | responde tudo e chega ao fim | ✅ nada — esta rota está pronta para ligar |
| `hdi/auto/pneu` | 1 | 89% | 68/76 | responde tudo e chega ao fim | ✅ nada — esta rota está pronta para ligar |
| `porto/auto/chaveiro` | 1 | 89% | 68/76 | responde tudo e chega ao fim | ✅ nada — esta rota está pronta para ligar |
| `porto/residencial/chaveiro` | 1 | 89% | 68/76 | responde tudo e chega ao fim | ✅ nada — esta rota está pronta para ligar |
| `hdi/auto/chaveiro` | 1 | 70% | 53/76 | responde tudo e chega ao fim | ✅ nada — esta rota está pronta para ligar |


## VAI PARA UMA PESSOA — 2 de 73 (3%)

*o caso segue com alguém — por desenho da seguradora ou por defeito*

| rota | pedidos | qualidade | bruto | por quê | 🔴 o que destrava |
|---|---:|---:|---:|---|---|
| `tokio/auto/guincho` | 3 | 70% | 45/64 | a seguradora não abre pela conversa: devolve link ou formulário | ✅ nada — é o desenho certo, e já é handoff pela SPEC-118 |
| `porto/auto/vidros` | 1 | 53% | 37/70 | a seguradora não abre pela conversa: devolve link ou formulário | ✅ nada — é o desenho certo, e já é handoff pela SPEC-118 |


## AINDA NÃO DÁ PARA LIGAR — 46 de 73 (63%)

*e a causa diz de quem é o trabalho: sem conversa é acionamento; tela sem resposta é código*

📊 **Dentro desta faixa:** **31** nenhuma conversa desta rota no acervo · **9** existe conversa, e uma tela dela ninguém respondeu · **6** responde tudo o que o acervo mostra e nunca chegou ao protocolo

| rota | pedidos | qualidade | bruto | por quê | 🔴 o que destrava |
|---|---:|---:|---:|---|---|
| `yelum/auto/guincho` | 26 | 63% | 48/76 | existe conversa, e uma tela dela ninguém respondeu | 🤖 escrever o passo da tela que ficou sem resposta |
| `porto/auto/guincho` | 25 | 63% | 48/76 | existe conversa, e uma tela dela ninguém respondeu | 🤖 escrever o passo da tela que ficou sem resposta |
| `allianz/residencial/encanador` | 18 | 55% | 42/76 | existe conversa, e uma tela dela ninguém respondeu | 🤖 escrever o passo da tela que ficou sem resposta |
| `hdi/auto/guincho` | 16 | 63% | 48/76 | existe conversa, e uma tela dela ninguém respondeu | 🤖 escrever o passo da tela que ficou sem resposta |
| `azul/auto/guincho` | 7 | 76% | 58/76 | existe conversa, e uma tela dela ninguém respondeu | 🤖 escrever o passo da tela que ficou sem resposta |
| `allianz/residencial/maquina_de_lavar` | 6 | 76% | 58/76 | existe conversa, e uma tela dela ninguém respondeu | 🤖 escrever o passo da tela que ficou sem resposta |
| `bradesco/auto/guincho` | 5 | 41% | 31/76 | existe conversa, e uma tela dela ninguém respondeu | 🤖 escrever o passo da tela que ficou sem resposta |
| `hdi/residencial/eletricista` | 5 | 30% | 23/76 | existe conversa, e uma tela dela ninguém respondeu | 🤖 escrever o passo da tela que ficou sem resposta |
| `allianz/residencial/desentupimento` | 4 | 58% | 44/76 | responde tudo o que o acervo mostra e nunca chegou ao protocolo | 🧑 um acionamento que vá até o fim — a prova do desfecho |
| `hdi/residencial/encanador` | 3 | 68% | 52/76 | existe conversa, e uma tela dela ninguém respondeu | 🤖 escrever o passo da tela que ficou sem resposta |
| `allianz/residencial/eletrodomesticos` | 3 | 62% | 47/76 | responde tudo o que o acervo mostra e nunca chegou ao protocolo | 🧑 um acionamento que vá até o fim — a prova do desfecho |
| `porto/residencial/eletrodomesticos` | 1 | 61% | 39/64 | responde tudo o que o acervo mostra e nunca chegou ao protocolo | 🧑 um acionamento que vá até o fim — a prova do desfecho |
| `yelum/residencial/eletrodomesticos` | 1 | 59% | 45/76 | responde tudo o que o acervo mostra e nunca chegou ao protocolo | 🧑 um acionamento que vá até o fim — a prova do desfecho |
| `hdi/residencial/chaveiro` | 1 | 57% | 43/76 | responde tudo o que o acervo mostra e nunca chegou ao protocolo | 🧑 um acionamento que vá até o fim — a prova do desfecho |
| `yelum/auto/bateria` | 1 | 57% | 43/76 | responde tudo o que o acervo mostra e nunca chegou ao protocolo | 🧑 um acionamento que vá até o fim — a prova do desfecho |
| `alfa/auto/bateria` | — | — | SEM_CORPUS | nenhuma conversa desta rota no acervo | 🧑 um acionamento real desta rota, com o observador ligado |
| `alfa/auto/chaveiro` | — | — | SEM_CORPUS | nenhuma conversa desta rota no acervo | 🧑 um acionamento real desta rota, com o observador ligado |
| `allianz/auto/chaveiro` | — | — | SEM_CORPUS | nenhuma conversa desta rota no acervo | 🧑 um acionamento real desta rota, com o observador ligado |
| `azul/auto/chaveiro` | — | — | SEM_CORPUS | nenhuma conversa desta rota no acervo | 🧑 um acionamento real desta rota, com o observador ligado |
| `azul/auto/pneu` | — | — | SEM_CORPUS | nenhuma conversa desta rota no acervo | 🧑 um acionamento real desta rota, com o observador ligado |
| `bradesco/auto/bateria` | — | — | SEM_CORPUS | nenhuma conversa desta rota no acervo | 🧑 um acionamento real desta rota, com o observador ligado |
| `bradesco/auto/chaveiro` | — | — | SEM_CORPUS | nenhuma conversa desta rota no acervo | 🧑 um acionamento real desta rota, com o observador ligado |
| `bradesco/auto/pneu` | — | — | SEM_CORPUS | nenhuma conversa desta rota no acervo | 🧑 um acionamento real desta rota, com o observador ligado |
| `hdi/auto/bateria` | — | — | SEM_CORPUS | nenhuma conversa desta rota no acervo | 🧑 um acionamento real desta rota, com o observador ligado |
| `hdi/residencial/desentupimento` | — | — | SEM_CORPUS | nenhuma conversa desta rota no acervo | 🧑 um acionamento real desta rota, com o observador ligado |
| `hdi/residencial/eletrodomesticos` | — | — | SEM_CORPUS | nenhuma conversa desta rota no acervo | 🧑 um acionamento real desta rota, com o observador ligado |
| `mapfre/auto/bateria` | — | — | SEM_CORPUS | nenhuma conversa desta rota no acervo | 🧑 um acionamento real desta rota, com o observador ligado |
| `mapfre/auto/chaveiro` | — | — | SEM_CORPUS | nenhuma conversa desta rota no acervo | 🧑 um acionamento real desta rota, com o observador ligado |
| `mapfre/auto/guincho` | — | — | SEM_CORPUS | nenhuma conversa desta rota no acervo | 🧑 um acionamento real desta rota, com o observador ligado |
| `mapfre/auto/pneu` | — | — | SEM_CORPUS | nenhuma conversa desta rota no acervo | 🧑 um acionamento real desta rota, com o observador ligado |
| `porto/auto/bateria_nova` | — | — | SEM_CORPUS | nenhuma conversa desta rota no acervo | 🧑 um acionamento real desta rota, com o observador ligado |
| `porto/auto/pneu` | — | — | SEM_CORPUS | nenhuma conversa desta rota no acervo | 🧑 um acionamento real desta rota, com o observador ligado |
| `porto/auto/taxi` | — | — | SEM_CORPUS | nenhuma conversa desta rota no acervo | 🧑 um acionamento real desta rota, com o observador ligado |
| `porto/residencial/desentupimento` | — | — | SEM_CORPUS | nenhuma conversa desta rota no acervo | 🧑 um acionamento real desta rota, com o observador ligado |
| `porto/residencial/eletricista` | — | — | SEM_CORPUS | nenhuma conversa desta rota no acervo | 🧑 um acionamento real desta rota, com o observador ligado |
| `tokio/auto/bateria` | — | — | SEM_CORPUS | nenhuma conversa desta rota no acervo | 🧑 um acionamento real desta rota, com o observador ligado |
| `tokio/auto/chaveiro` | — | — | SEM_CORPUS | nenhuma conversa desta rota no acervo | 🧑 um acionamento real desta rota, com o observador ligado |
| `tokio/auto/pneu` | — | — | SEM_CORPUS | nenhuma conversa desta rota no acervo | 🧑 um acionamento real desta rota, com o observador ligado |
| `yelum/auto/chaveiro` | — | — | SEM_CORPUS | nenhuma conversa desta rota no acervo | 🧑 um acionamento real desta rota, com o observador ligado |
| `yelum/residencial/chaveiro` | — | — | SEM_CORPUS | nenhuma conversa desta rota no acervo | 🧑 um acionamento real desta rota, com o observador ligado |
| `yelum/residencial/desentupimento` | — | — | SEM_CORPUS | nenhuma conversa desta rota no acervo | 🧑 um acionamento real desta rota, com o observador ligado |
| `zurich/auto/bateria` | — | — | SEM_CORPUS | nenhuma conversa desta rota no acervo | 🧑 um acionamento real desta rota, com o observador ligado |
| `zurich/auto/chaveiro` | — | — | SEM_CORPUS | nenhuma conversa desta rota no acervo | 🧑 um acionamento real desta rota, com o observador ligado |
| `zurich/auto/pneu` | — | — | SEM_CORPUS | nenhuma conversa desta rota no acervo | 🧑 um acionamento real desta rota, com o observador ligado |
| `zurich/auto/socorro_mecanico` | — | — | SEM_CORPUS | nenhuma conversa desta rota no acervo | 🧑 um acionamento real desta rota, com o observador ligado |
| `zurich/auto/vidros` | — | — | SEM_CORPUS | nenhuma conversa desta rota no acervo | 🧑 um acionamento real desta rota, com o observador ligado |


## 🔴 O segurado pede, e o produto não tem corredor nenhum

📊 Medido em 28/09/2026 em `observed_events`. Estes serviços foram escolhidos por gente de verdade, e **não existe playbook para eles** — então eles não aparecem em nenhuma das faixas acima, porque a lista de rotas só conhece o que tem corredor.

| serviço pedido | conversas | o que é |
|---|---:|---|
| `yelum/auto/carro_reserva` | 10 | 🔴 serviço real, sem um único passo escrito |
| `allianz/residencial/?conserto residencial` | 5 | 🔴 rótulo que o classificador não reconhece — ver a seção dos `?` abaixo |
| `bradesco/auto/tecnico` | 2 | 🔴 serviço real, sem um único passo escrito |
| `tokio/auto/carro_reserva` | 2 | 🔴 serviço real, sem um único passo escrito |
| `allianz/auto/eletricista` | 1 | 🔴 serviço real, sem um único passo escrito |
| `allianz/auto/encanador` | 1 | 🔴 serviço real, sem um único passo escrito |
| `allianz/auto/taxi` | 1 | 🔴 serviço real, sem um único passo escrito |
| `allianz/residencial/?check-up lar` | 1 | 🔴 rótulo que o classificador não reconhece — ver a seção dos `?` abaixo |
| `allianz/residencial/?limpeza` | 1 | 🔴 rótulo que o classificador não reconhece — ver a seção dos `?` abaixo |
| `allianz/residencial/?pet assistance` | 1 | 🔴 rótulo que o classificador não reconhece — ver a seção dos `?` abaixo |
| `allianz/residencial/?reembolso - qualidade` | 1 | 🔴 rótulo que o classificador não reconhece — ver a seção dos `?` abaixo |
| `allianz/residencial/?retorno em garantia` | 1 | 🔴 rótulo que o classificador não reconhece — ver a seção dos `?` abaixo |
| `allianz/residencial/guincho` | 1 | 🔴 serviço real, sem um único passo escrito |
| `allianz/residencial/telhado` | 1 | 🔴 serviço real, sem um único passo escrito |
| `mapfre/auto/carro_reserva` | 1 | 🔴 serviço real, sem um único passo escrito |
| `porto/auto/?4145720 - 26` | 1 | 🔴 rótulo que o classificador não reconhece — ver a seção dos `?` abaixo |
| `yelum/residencial/limpeza_caixa_dagua` | 1 | 🔴 serviço real, sem um único passo escrito |


## Os rótulos com `?` — o classificador avisando que não sabe

⚠️ O `?` é **honesto**: o padrão-ouro casou uma escolha de menu cujo rótulo não está no vocabulário canônico, e o classificador **declara** isso (`nivel-1a-rotulo-desconhecido`) em vez de chutar. Mas dois deles são coisas diferentes:

- **serviço real sem nome canônico** — precisa entrar no vocabulário, e aí vira rota de verdade;
- 🔴 **`?4145720 - 26` é um NÚMERO DE PROTOCOLO virando 'serviço'** — aqui o padrão-ouro casou uma linha que não é escolha de serviço nenhuma. É defeito do padrão, não falta de vocabulário.


## 🔴 As conversas que existem e o classificador não etiquetou

Enquanto elas estiverem aqui, um `—` na coluna `pedidos` **não quer dizer 'ninguém pediu'** — quer dizer 'não sabemos'. 📊 28/09/2026, `observed_events`.

| seguradora / ramo | conversas sem etiqueta |
|---|---:|
| `allianz/residencial` | 41 |
| `porto/auto` | 30 |
| `mapfre/auto` | 20 |
| `yelum/auto` | 19 |
| `hdi/auto` | 12 |
| `zurich/auto` | 9 |
| `bradesco/auto` | 8 |
| `allianz/auto` | 6 |
| `tokio/residencial` | 5 |
| `porto/residencial` | 4 |
| `alfa/auto` | 3 |
| `tokio/auto` | 2 |
| `yelum/residencial` | 1 |


---

_Gerado por `backend/scripts/pagina_dos_corredores.py --gravar` em 2026-09-28T03:04:52+00:00. **Nenhum número deste documento foi digitado à mão.**_
