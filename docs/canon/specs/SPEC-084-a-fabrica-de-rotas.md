# SPEC-084 — A FÁBRICA DE ROTAS

> **Levar as 62 rotas ao nível da máquina de lavar — uma de cada vez, na ordem que a árvore da URA impõe, e nenhuma liberada sem o juiz.**
>
> Autor: execução · **v7, 21/08/2026** · Commit base: `bae33ea`
> Branch: `feat/spec084-a-fabrica-de-rotas`
> Depende de: **SPEC-083 (A Régua)** — sem a régua, esta SPEC não tem como saber se terminou

---

## 0. PREFLIGHT OBRIGATÓRIO

```bash
git rev-parse --show-toplevel      # AutoBrokers-FIX
git branch --show-current          # feat/spec084-a-fabrica-de-rotas
git rev-parse HEAD                 # registrar no relatório
git status --short                 # LIMPO ao iniciar
```

**Pré-condição absoluta:** a SPEC-083 tem de estar **fechada e verde**. Sem `medir_rota.py`, sem o corpus e sem o gate de replay, esta SPEC não tem instrumento — e trabalho sem instrumento vira opinião.

```bash
python backend/scripts/medir_rota.py --seguradora allianz --ramo residencial --servico maquina_de_lavar
# tem de responder com a nota e a lista INTEIRAMENTE NOMEÁVEL do que falta
# (📊 hoje são CINCO — §4.4; a v1 desta SPEC fixou em três e o gate virou
# aritmeticamente impossível). Se não responder, PARE.
```

Leitura obrigatória, além do `CLAUDE.md` inteiro:

1. **`docs/canon/specs/SPEC-083-a-regua-do-corredor.md`** — a régua, a rubrica, os `DECIDE:`. Esta SPEC não redefine nada disso.
2. `docs/canon/O-ATLAS-E-UM-SO-E-E-DE-TODAS.md` — o Atlas é um só, de todas.
3. `docs/canon/O-ATLAS-E-PARA-QUEM-ESCREVE-O-CORREDOR.md`
4. `docs/canon/GLOSSARIO.md`

---

## 1. POR QUE ESTA SPEC EXISTE

📊 O produto tem **62 rotas** (seguradora × ramo × serviço) e **uma** validada em produção: `allianz × residencial × maquina_de_lavar`, protocolo 52955490, 19/08/2026, 5min55 do "oi" ao protocolo.

📊 A distância entre ela e o resto, medida pelo replay contra as telas reais:

```
allianz-residencial / maquina_de_lavar   respondidas=20   órfãs= 7
allianz-residencial / chaveiro           respondidas=11   órfãs=16   ← MESMO corredor
mapfre-auto  / guincho                   respondidas= 0   órfãs=29
tokio-auto   / guincho                   respondidas= 0   órfãs=29
```

📊 E o material para consertar existe (medido 21/08/2026): **28.096 eventos · 16.242 telas `direction='in'` · 544 sessões · 16 pares corretora×seguradora · 10 seguradoras · 13 meses**. A mapfre — que uma auditoria chamou de "sem sessões" — tem 13 sessões e evento de **21/08/2026 às 10:04**.

**Esta SPEC transforma esse material em rotas AAA.**

---

## 2. 🔴 A DESCOBERTA QUE ORGANIZA TUDO: A URA É UMA ÁRVORE

### 2.1 O que se pensava, e por que estava errado

A intuição natural é tratar cada rota como uma coisa separada: "a rota do guincho", "a rota do chaveiro". Sob essa intuição, o trabalho seria uma fila de 62 itens independentes, e a validade de cada um seria a idade da última sessão **daquele serviço**.

**Está errado, e o erro custa caro nos dois sentidos.**

### 2.2 A evidência

📊 Medido na Allianz, 21/08/2026 — quantos **serviços diferentes** veem cada tela:

| tela | serviços que a veem | sessões | visto por último |
|---|---:|---:|---|
| `Termo de Privacidade: Ao prosseguir…` | **5** | 123 | 19/08/2026 |
| `Certo! Por favor digite o *CPF* ou *CNPJ* do(a) titular…` | **5** | 78 | 19/08/2026 |
| `Olá! Sou a assistente virtual da Allianz. Você precisa de Assistência…` | **5** | 59 | 19/08/2026 |
| `Qual seguro deseja utilizar? *1 - Residencial* …` | **5** | 37 | 19/08/2026 |
| `Por favor, confirme o endereço para atendimento:` | **4** | 79 | 19/08/2026 |
| `Agora, me confirme o número da residência.` | **4** | 72 | 19/08/2026 |
| ~~`Vou transferir seu caso para um especialista…`~~ 🔴 **FRONTEIRA — não é nó** | — | 98 | 03/08/2026 |

*(os cinco serviços: eletricista · eletrodoméstico · encanador · guincho · outros)*

🔴 **E a linha `Vou transferir seu caso para um especialista` NÃO é nó de tronco.
É a FRONTEIRA da árvore.**

📊 Pela fórmula de retorno desta própria SPEC (§4.3), ela é **5 × 98 = 490** — o
**maior** da tabela, maior que a tela do CPF (5 × 78 = 390) que a SPEC elege como
prioridade #1. Escrita como está, a regra manda o executor transformar em passo,
antes de tudo, **a tela que entrega o atendimento ao humano**.

> **Regra:** a tela de transferência de cada seguradora é catalogada como
> `FRONTEIRA`, vira gatilho de `pausar_e_chamar` — e **tudo o que vem depois dela
> numa sessão sai do corpus** (§2.5).

🔴 **E `outros` NUNCA conta em `count(distinct servico)`.** É balde de
não-classificado: contá-lo faz a regra `serviços ≥ 3 → TRONCO` disparar com dois
serviços reais mais ruído. Tela que só alcança 3 **com** `outros` é **GALHO**, e o
relatório diz quantas caíram nesse caso.

⚠️ **As contagens da tabela acima ainda incluem a zona humana** (📊 22 · 18 · 6 ·
13 · 16 sessões, linha a linha). **A tabela só vale depois de refeita com
`zona='URA'`** — e quem a refaz, para as 10 seguradoras, é o BLOCO 0.

**Uma tela vista por cinco serviços não pertence a nenhum deles. Pertence à seguradora.**

### 2.3 🔴 E a URA muda o tronco — está medido

📊 Duas redações da MESMA tela de abertura da Allianz:

```
"Olá! Sou a *assistente virtual da Allianz*. Você precisa de Assistência…"
     59 sessões · 4-5 serviços · visto por último 19/08/2026

"Olá! Sou a *assistente virtual da Allianz*. Este é um canal exclusivo de…"
     64 sessões · 4 serviços · visto por último 26/03/2026
```

**A Allianz reescreveu a primeira tela entre março e agosto.** E essa mudança **não é do guincho, nem do eletricista** — é de **todas as rotas da Allianz**, das duas linhas, dos dois ramos.

### 2.4 O modelo que esta SPEC adota

> ## A URA é uma ÁRVORE. A unidade de trabalho é o **NÓ**, não a rota.
>
> ```
>                   [ tronco ]  ← vista por TODOS os serviços
>          Olá · Termo · CPF · Qual seguro
>                        │
>            ┌───────────┴───────────┐
>       [ galho AUTO ]        [ galho RESIDENCIAL ]   ← vista por um ramo
>            │                        │
>     ┌──────┴──────┐         ┌───────┴────────┐
>  guincho      chaveiro   eletricista   eletrodoméstico   ← FOLHA: um serviço
> ```

E daí saem três consequências que governam a SPEC inteira:

**(a) Consertar um nó de tronco paga por todas as rotas daquela seguradora.**
📊 A tela do CPF da Allianz é vista por 5 serviços em 78 sessões. Uma âncora certa ali serve às 6 rotas residenciais **e** às 4 de auto.

**(b) A validade é por NÓ, não por rota.**
Uma tela vista **hoje** numa sessão de guincho está atualizada **para todo mundo que passa por ela** — inclusive para o chaveiro, cuja última sessão foi há seis meses.

**(c) Consertar uma folha paga por uma rota só.**
E é por isso que folha vem depois de tronco, sempre.

---

## 2.5 🔴 NEM TODA MENSAGEM `direction='in'` É TELA DE URA

**Esta seção vem antes das regras de atualidade porque decide QUAIS mensagens
entram na árvore.** Errar aqui não erra um número: contamina o corpus, a
classificação tronco/folha, a ordem do trabalho e os três juízes de uma vez.

`direction='in'` é a **direção** da mensagem, não o **emissor**. Depois que a URA
transfere o caso, quem escreve `in` é o **atendente humano da seguradora**.

📊 Medido em 21/08/2026:

```
eventos `in` depois da tela de transferência .....  4.696 / 16.242 = 28,9 %
sessões afetadas .................................    137 / 527

ALLIANZ  — 38 % do acervo, e a PRIMEIRA do BLOCO 1:
   eventos pós-transferência .....................  3.737 / 7.513 = 49,7 %
   telas distintas que só existem ali ............  1.149 / 1.412 = 81,4 %
```

📊 **CONTROLE que prova que as duas zonas são qualitativamente diferentes** — se
fossem a mesma coisa, os percentuais seriam parecidos:

```
zona                        eventos    texto único (1 sessão)   texto em 10+ sessões
A_POS  (humano)               4.674            44,8 %                  35,3 %
        (4.696 eventos ao todo; 4.674 com texto não-vazio, que é o recorte deste controle)
B_PRE  (URA)      CONTROLE    3.509            11,7 %                  68,5 %
C_sem_transferência CONTROLE  8.031            21,6 %                  44,8 %
```

Texto que aparece **numa única sessão** é 11,7% da zona URA e 44,8% da zona
humana — **3,8×**. URA se repete; gente não.

🔴 **E o que a regra do §3.3 classificaria como TRONCO da Allianz, sem esta
separação:**

```
"com quem falo?" ............................... 55 sessões
"ajudo em algo mais? mais alguma dúvida?" ...... 52
"ok" ........................................... 31
"mais um momento por favor." ................... 18
"tem algum ponto de referência do endereço?" ... 18   ← e esta PEDE resposta
"um momento" ................................... 17
```

**E o efeito nos juízes é o que mata a SPEC.** O JUIZ 1 CÉTICO (§6.2) pergunta:
*"alguma tela do corpus não casa passo nenhum e pede algo?"*

```
Allianz — telas distintas que PEDEM algo:
   zona humana .......... 472
   zona URA  CONTROLE ... 126      ← 3,7× menos
```

📊 **472 reprovações automáticas, permanentes e insanáveis.** Nenhuma rota da
Allianz jamais é liberada: todas batem o teto de 3 voltas e viram
`PRECISA_DE_HUMANO`. A SPEC não falharia com erro — falharia **reprovando tudo**,
e o executor procuraria o defeito no corredor a vida inteira.

### 2.5.1 🔴 A marca é POR SEGURADORA — uma regex só carimba nove de dez

📊 A v2 desta SPEC trazia **uma** regex, escrita a partir do vocabulário da
Allianz. Medido em 21/08/2026, o que ela remove por seguradora:

```
allianz  3.737 removidos      hdi     169        bradesco   0
porto      459                azul     21        tokio      0
yelum      278                zurich   10        mapfre     0        alfa  0
```

🔴 **E o `case` declarava `zona='URA'` tudo que ela não pegasse.** Quatro
seguradoras entrariam na fábrica com selo de limpeza que **nenhuma medição
sustenta** — e o gate ① da §2.5.2 passaria nelas com 100%.

📊 O que sobrou dentro da "zona URA" da mapfre — 100% dela, porque removidos = 0:

```
"olá bom dia tudo bem? como posso te chamar?"          ← humano, e PEDE
"me informa seu código e cpf por gentileza?"           ← humano, e PEDE
"posso te auxiliar em mais alguma coisa ?"             ← humano, e PEDE
"peço um momento por gentileza, irei verificar"        ← humano
"perfeito, que bom" · "que bom falar com você!" · "certo"
```

⚠️ **Isto é PIOR que a v1.** A v1 não separava, e o executor sabia. A v2 separa,
**carimba**, e o §5.1① manda o corpus ser essa zona. Selo falso é pior que selo
nenhum.

**A tabela, publicada como código, uma entrada por seguradora, cada padrão com
📊 sessões medidas ao lado:**

```python
FRONTEIRAS = {   # 🔴 toda entrada carrega a contagem medida e a data
  "allianz":  [r"vou transferir seu caso para um especialista"],            # 📊 98 ses
  "hdi":      [r"necessario falar com um de nossos especialistas",          # 📊 7
               r"conversa foi encerrada pelo atendente",                    # 📊 8
               r"atendimento prestado pelo nosso analista",                 # 📊 8
               r"(vou|irei) (precisar )?te transferir|(vou|irei) transferir",# 📊 3 🔴 ver abaixo
               r"vamos te direcionar para um de nossos especialistas"],     # 📊 1
  "mapfre":   [r"vou te direcionar para a pessoa que vai dar continuidade", # 📊 3
               r"passando seu caso para eles"],   # 📊 1 ses — ÂNCORA FINA:
               # revalidar quando a mapfre passar de 20 sessões (083 §4.1)
  "porto":    [r"vou (precisar )?transferir (o )?seu atendimento",          # 📊 15
               r"irei te transferir para a central"],                       # 📊 1
  "yelum":    [r"necessario falar com um de nossos especialistas",          # 📊 11
               r"conversa foi encerrada pelo atendente"],                   # 📊 12
  "azul":     [r"vou precisar transferir o seu atendimento"],               # 📊 2
  "zurich":   [r"irei te transferir para um de nossos atendentes",         # 📊 2
               r"vou transferir voce para a pessoa que vai continuar"],    # 📊 1
  "bradesco": [],   # ✅ VAZIA CONFERIDA: não há transferência consumada no acervo
  "tokio":    [],   # ✅ VAZIA CONFERIDA: sai por link, não transfere no fio
  "alfa":     [],   # ✅ VAZIA CONFERIDA: nada
}
```

⚠️ **A entrada da hdi da v3 estava QUEBRADA.** 📊 O padrão
`r"(vou|irei) (te )?(precisar )?transferir"` **não casa o texto da hdi que o
motivou** — o acervo escreve *"vou **precisar te** transferir"*, e o padrão exige
*"vou te precisar transferir"*:

```sql
select ('vou precisar te transferir para um de nossos analistas'
        ~ '(vou|irei) (te )?(precisar )?transferir');
→ false
```

Corrigido para `r"(vou|irei) (precisar )?te transferir|(vou|irei) transferir"`.

🔴 **E o `"zurich": []` da v3 NÃO era medição — era o corte da query.** A busca de
marcas perdidas rodou com `order by insurer_key, ses desc limit 22`, e `zurich` é
a **última em ordem alfabética**: o resultado truncou antes de chegar nela.
**Ausência de linhas no resultado foi lida como ausência de marca no acervo.**

### 2.5.1.4 🔴 `NAO_E_FRONTEIRA`: o controle negativo, sem o qual a URA é cortada no meio

📊 Ao medir a zurich sem o corte, apareceram **três textos que casariam padrões
plausíveis e NÃO são fronteira**:

```
"não foi possível te transferir para um atendente. tente novamente…"   🔴 NEGATIVA
"vou direcionar você para nosso menu principal."                       🔴 é MENU
"o que você deseja fazer agora? … falar com um atendente"              🔴 é MENU
```

**Cortar ali joga fora o resto de uma sessão de URA legítima** — e o gate ④ **nem
acusa**, porque remover telas repetidas *baixa* o percentual de texto único.
O guarda ficaria verde enquanto o corpus encolhe.

```python
NAO_E_FRONTEIRA = {   # 🔴 todo padrão de FRONTEIRAS é testado contra esta lista
  "zurich":   [r"nao foi possivel te transferir",
               r"vou direcionar voce para nosso menu",
               r"o que voce deseja fazer agora"],
  "bradesco": [r"qual opcao voce escolhe.*chamar atendente"],   # menu, não transferência
  "tokio":    [r"clique no link.*conversar com um atendente"],  # sai por link
  "azul":     [r"fale com um dos nossos especialistas, clicando no link"],
}
```

> 🔴 **TESTE OBRIGATÓRIO:** todo padrão de `FRONTEIRAS` roda contra
> `NAO_E_FRONTEIRA` e **tem de dar ZERO**. Padrão que casa os dois não entra na
> tabela.
>
> **Um guarda sem controle negativo não distingue "transferiu" de "não conseguiu
> transferir".** E `bradesco`, `tokio` e `alfa` só puderam ficar vazias **porque
> alguém mediu que o que existe lá é menu, link e nada** — não porque a busca
> voltou vazia.

> 🔴 **Lista vazia NÃO significa seguradora limpa.** Significa uma de duas coisas
> — ela não transfere, ou a marca não foi achada. **Quem separa as duas é o gate
> ④ da §2.5.2, nunca quem escreveu a tabela.**

### 2.5.1.1 🔴 A zona é calculada em PYTHON, no mesmo lugar que a árvore

A v2 escreveu a zona como **view SQL** e a §3.3 da mesma versão provou, três
seções adiante, que esse SQL não pode existir:

```
§3.3 prova:  `unaccent` NÃO existe neste banco
             📊 pg_extension = {pg_stat_statements, pgcrypto, plpgsql,
                                supabase_vault, uuid-ossp}
§3.3 prova:  normalizar em SQL é PROIBIDO -- seria um segundo normalizador
             ao lado do `_norm` (CLAUDE.md §5), e os dois divergem no dia
             em que um for corrigido
§2.5.1 v2:   era SQL, casava `~*` sobre `text` CRU, e trazia `necessário`
             COM ACENTO -- uma normalização implícita que o banco não faz
```

📊 E o acervo tem as duas grafias: eventos `in` escrevem `transferencia` e
`necessario` **sem acento** — inclusive a marca de fronteira da mapfre
(*"já realizo a transferencia"*), que por isso **nunca casaria**, mesmo estando
na tabela.

```python
# medir_rota.py --exportar-arvore, antes de qualquer contagem:
def zonas(eventos_da_sessao, seguradora):
    t_transf = None
    for e in ordenados_por_wa_timestamp(eventos_da_sessao):
        if e.session_id is None:                 # 📊 493 eventos (3,0%)
            yield e, "ORFAO"; continue
        n = _norm(e.text or "")                  # o _norm de verdade, importado
        # 🔴 NÃO existe zona CORRETORA — ver §2.5.1.3. A identidade é
        #    MASCARADA antes do _norm, e a tela FICA no corpus.
        if t_transf is None and any(re.search(p, n)
                                    for p in FRONTEIRAS[seguradora]):
            t_transf = e.wa_timestamp
            yield e, "URA"                       # a própria fronteira ainda é URA
            continue
        yield e, ("HUMANO" if t_transf else "URA")
```

⚠️ **Nenhuma view SQL.** A da v2 não faz o que promete.

### 2.5.1.2 🔴 A zona tem TRÊS valores, não dois

| zona | o que é | 📊 hoje | destino |
|---|---|---:|---|
| **URA** | a seguradora falando por robô | — | **o corpus** |
| **HUMANO** | atendente da seguradora digitando | 4.696 | preservada; insumo do BLOCO 4 |
| **ORFAO** | `session_id is null` | **493** (3,0%) | fora do corpus + `PENDENCIAS.md` |
| ~~**CORRETORA**~~ | ❌ **ELIMINADA — a medição inverteu a premissa** | — | ver §2.5.1.3 |

🔴 **`ORFAO` existe porque sem sessão não há "antes/depois da transferência"** — e
o `left join` da v2 devolvia `NULL`, o `case` caía no `else`, e os 493 entravam
como **URA**. 📊 E há fala humana entre eles: *"maria, não é nesta central, irei te
transferir para a central frota…"* (porto) tem `session_id` nulo — **é uma marca
de fronteira que a v2 classificava como URA**. Nenhum dos três gates pegava: eles
carregavam o carimbo, e as linhas semeadas do gate ③ teriam `session_id`.

3% do acervo sem sessão é **defeito de ingestão**, e vai para `PENDENCIAS.md` com
dono 🤖.

### 2.5.1.3 🔴 A zona `CORRETORA` foi ELIMINADA — e a razão é medida

A v3 criou uma zona para descartar os eventos que citam a corretora, presumindo
que fossem *"a nossa ponta escrevendo"*. **A medição inverteu a premissa.**

📊 Medido em 21/08/2026, com os padrões completos:

```
seguradora   eventos que citam   na zona URA   TELAS DE URA que seriam   sessões
             a corretora                        DESCARTADAS
   hdi              93                93                29                17
   yelum            62                62                24                16
   tokio            60                60                 9                21
   porto            30                20                 4                 7
   allianz          27                 0                 0                13
                  ---               ---               ---
                   272               235                66
```

🔴 **São 272 eventos, não 75.** O número da v3 usou só `resulta seguros|autofleet`;
com `saionara`, `christian - `, `maria regina - `, `resulta corretora` e
`sga corretora`, são **272** — subcontagem de **3,6×**.

**E o que essas mensagens SÃO:** não é a corretora escrevendo. É a **URA da
seguradora saudando a corretora pelo nome antes de perguntar**:

```
tokio  "olá, christian - autofleet seguros! digite o cpf/cnpj do titular"    ← A TELA DO CPF
yelum  "saionara - resulta, estamos prontos para seguir. qual é o serviço"   ← A TELA DO SERVIÇO
yelum  "saionara - resulta, qual é o nome da pessoa responsável pelo téc…"   ← PEDE
hdi    "saionara - resulta seguros, a chegada do prestador está prevista…"   ← O DESFECHO
```

🔴 **A tokio tem 46 sessões, `FRONTEIRAS` vazia e ZERO removidos. A zona
`CORRETORA` tiraria dela a tela do CPF** — e ninguém veria o buraco. A yelum e a
hdi perdem a tela que pergunta o serviço.

**E a autoridade já tinha resolvido isso do jeito oposto:** SPEC-083 §6.4 —
**"🔴 Higiene: MASCARAR, não recusar"**. A v3 recusava.

```python
from app.services.atlas.templater import templatize   # 🔴 o mascarador do Atlas
n = _norm(templatize(e.text))                         #    NUNCA um segundo
```

📊 `templatize()` existe em `backend/app/services/atlas/templater.py:1381`, com
`marcas_de_corretora()` (l.1309) e `_apagar_marcas_de_corretora()` (l.1350). **É o
mascarador cuja saída a própria SPEC-083 §6.4 cita** (*"o endereço já vem
mascarado pelo Atlas: `R. ### ##TEVES J#####`"*) sem nomeá-lo.

🔴 **Escrever um `_mascarar_identidade` novo seria um SEGUNDO mascarador ao lado
de um que existe** — a mesma violação do CLAUDE.md §5 que esta SPEC recusou
corretamente para o `_norm` em SQL (§2.5.1.1). O argumento vale inteiro aqui.

### 🔴 E o `templatize` tem UM buraco para este uso — não três

⚠️ **Esta seção é o registro de uma medição que quase virou prescrição errada.**

📊 A primeira rodada, feita **sem banco**, devolveu:

```
templatize("Saionara - Resulta")     → inalterado         🔴 "buraco"
templatize("Christian - AutoFleet")  → inalterado         🔴 "buraco"
templatize("SGA Corretora … Ltda")   → inalterado         🔴 "buraco"
marcas_de_corretora()                → 0 entradas         ← ISTO EXPLICA AQUILO
```

🔴 **A quarta linha era o CONTROLE das três primeiras, e não foi lida como tal.**
📊 `marcas_de_corretora()` (`templater.py:1309`) lê a tabela `companies`, e o
docstring dela é literal: *"Sem banco (teste, script solto) devolve vazio"*.
📊 E `companies` **não está vazia**: `Resulta Seguros` · `AutoFleet` · `AMANDUS
SEGUROS` · dois internos.

📊 **Refeita com as marcas reais carregadas:**

```
templatize("Christian - AutoFleet")          → {NOME} - {CORRETORA}   ✅ ARTEFATO do run offline
templatize("Saionara - Resulta Seguros")     → {NOME} - {CORRETORA}   ✅
templatize("Saionara - Resulta")             → Saionara - Resulta     🔴 BURACO REAL
templatize("SGA Corretora de Seguros Ltda")  → inalterado             ⚠️ OUTRA CLASSE
```

**O buraco que sobrevive ao controle é UM:** 📊 a marca gravada é
`Resulta Seguros`; a yelum escreve `"Saionara - Resulta, estamos prontos para
seguir…"` — **só `Resulta`**. Essa é uma das 66 telas do §2.5.1.3, e entraria no
corpus com nome de atendente e razão social em claro.

⚠️ **`SGA Corretora de Seguros Ltda` é outra classe:** a SGA não é corretora
cliente e não está em `companies`. Ela cai na regra **genérica de razão social**
da SPEC-083 §6.4, não na lista de marcas. 📊 4 eventos na porto, numa tela que
traz também telefone e e-mail de terceiro.

> ```
> CONTROLE OBRIGATÓRIO de qualquer medição sobre o mascarador:
>     assert len(marcas_de_corretora(recarregar=True)) > 0
> Se falhar, a medição é INVÁLIDA e não autoriza ampliação nenhuma.
> ```

🔴 **E o gate ⑤ não pode herdar a lista do mascarador.** Se ele perguntar
*"sobrou identidade?"* com a mesma lista, **fica verde sobre o que o mascarador
não viu**. Guarda e mascarador com o mesmo ponto cego não é guarda.

### 🔴 A ampliação é um MODO, nunca global — e há 8 consumidores

📊 Medido: `templatize` tem **8 consumidores de produção** e **~140 asserções de
teste**, 74 delas num arquivo só:

```
services/atlas/weaver.py:242            🔴 o TECELÃO — escreve `ura_maps`
services/attendance_distiller.py:358    o destilador (já gravou o acervo)
services/curadoria_cartas.py:182        o veredito de PII das cartas
services/ura_map_service.py:303,440     o Atlas
api/admin_atlas.py:1006 · playbook_gate.py:60 · main.py:550

test_a_conversa_com_a_seguradora_nao_vaza_gente.py ....... 74 asserções
```

**Mudar `templatize` globalmente muda o que o Tecelão grava em `ura_maps`** — e o
Atlas é UM SÓ e é de todas as corretoras.

📊 **E o mecanismo de modo já existe:** `_vale_neste_modo(padrao,
documento_publico)` em `templater.py:1480`. O corpus entra como **terceiro modo**:

```python
templatize(text, *, documento_publico=False, corpus_de_ura=False)
#                                            ^^^^^^^^^^^^^^^^^^^
# pelo mesmo `_vale_neste_modo`. ZERO mudança para os 8 consumidores
# atuais e para as 74 asserções.
```

🔴 **Isto NÃO é criar motor paralelo** (CLAUDE.md §5): é usar o mecanismo de modo
que a peça já oferece, dentro dela.

> ## 🔴 P1 SEPARADO — e não é desta SPEC
>
> Se `marcas_de_corretora()` devolver **0 em produção**, o **Tecelão está
> gravando `ura_maps` sem apagar marca de corretora** — vazamento de identidade
> dentro do Atlas, que é UM SÓ e de todas.
>
> **Vai para `PENDENCIAS.md` com dono 🤖 e verificação imediata**, independente
> desta SPEC avançar ou não.

### 🔴 E a exceção da senha: `templatize` NÃO cumpre o que a 083 §6.4 exige

📊 A SPEC-083 §6.4 é literal: *"preservar os 4 últimos se eles reaparecerem como
senha (tela #27 de `7ac3c101`) — **senão a âncora de senha perde o alvo**"*.

📊 Rodado sobre a tela real da Allianz (9 sessões):

```
antes:   "Sua senha será os 4 últimos dígitos desse telefone *4743*"
depois:  "Sua senha será os 4 últimos dígitos desse telefone *{SEGREDO}*"
```

**Os dois lados do resultado, e eles não são o mesmo:**

```
✅ a ÂNCORA sobrevive   — o passo casa por PROSA, e a prosa está intacta
                          (conferido: a regex do passo ainda casa)
🔴 o VALOR não          — teste que verifique "o corredor capturou 4743"
                          não tem como verificar nada
```

> **Teste obrigatório antes do BLOCO 0 fechar:** rodar `templatize` sobre a tela
> #27 e exigir que a âncora **case**. 📊 Hoje ela casa. Se um dia deixar de casar,
> o replay perde três passos da régua (#10, #12, #27) e **ninguém vê**, porque a
> perda vira só um número menor.

> **Segundo teste:** rodar sobre as **235 linhas que citam corretora** (§2.5.1.3)
> e exigir que **as 66 telas continuem no corpus** — a tela do CPF da tokio e a
> tela do serviço da yelum/hdi entre elas, agora com `{CORRETORA}` no lugar do
> nome. 📊 Hoje a da tokio passa e **a da yelum não é mascarada** — buraco ①.

⚠️ 🔴 **E mascarar ANTES de `_norm`** — senão a mesma tela vira várias, uma por
nome de atendente (📊 `saionara`, `christian`, `maria regina`), e a contagem de
sessões do §3.3 se fragmenta em silêncio.

🔴 **A exceção que continua valendo:** 📊 a porto tem
*"\*nome\*: sga corretora de seguros ltda \*telefone\*: … \*e-mail\*: …"* (4 eventos)
— razão social, telefone e e-mail de terceiro numa tela. **Mascarar, e o gate de
higiene da SPEC-083 §6.4 roda sobre o `.jsonl` desta SPEC.**

> 🔴 **O corpus, a árvore, o retorno e os três juízes usam `zona='URA'` — e só.**
>
> `HUMANO` **não é lixo e não se apaga**: serve para descobrir **o que a URA não
> resolve**, insumo do BLOCO 4. `ORFAO` fica fora de tudo.
> Nenhuma das duas vira passo de corredor.
>
> 🔴 **E não há zona para a corretora.** A tela que cita a corretora **fica no
> corpus, mascarada** — §2.5.1.3. 📊 Descartá-la tiraria 66 telas de URA, uma
> delas a tela do CPF da tokio.

### 2.5.2 🔴 E o guarda de corpus tem de PODER FICAR VERMELHO

A SPEC-083 §6.3 exige que o `.jsonl` seja 100% `direction='in'`. 📊 **Esse controle
passa com 100% num corpus 29% humano** — ele mede a direção, e o problema é o
emissor. Guarda que não tem como falhar não guarda nada (CLAUDE.md §9.3).

O gate de corpus desta SPEC exige **cinco** coisas:

```
① 100 % das linhas com `zona='URA'`
② ZERO linhas cuja NORMALIZAÇÃO INTEIRA seja uma destas
   — 🔴 ancorado em `^…$`, NUNCA em prefixo:
      ^(ok|certo|perfeito|um momento|mais um momento|com quem falo|
        ajudo em algo mais|bom dia tudo bem)[!.,?]?$

③ 🔴 A PROVA DO GUARDA, NOS DOIS SENTIDOS:
   · corpus semeado com 10 linhas da zona HUMANO  → tem de ficar VERMELHO
   · corpus da Allianz limpa, SEM semear          → tem de ficar VERDE
   📊 A v2 falhou no primeiro. A v3 falhou no segundo.
④ 🔴 O CONTROLE POR SEGURADORA -- ver abaixo
⑤ ZERO linhas com `zona='ORFAO'`
   + ZERO linhas com identidade NÃO MASCARADA (SPEC-083 §6.4)
   🔴 e NÃO "zero linhas que citam a corretora": 📊 235 delas são telas de
   URA legítimas, e uma é a tela do CPF da tokio (§2.5.1.3)
```

### 2.5.2.0 🔴 Por que o ② é `^…$` e não prefixo: ele barrava a tela do CPF

📊 Medido em 21/08/2026. O padrão da v3, ancorado em **prefixo**, rejeita:

```
"certo! por favor digite o *cpf* ou *cnpj* do(a) titular da apólice…"      78 ses 🔴🔴
"certo, neste caso qual é o nome da pessoa que está no local?"             40 ses
"certo! agora preciso que você informe para onde devemos levar o veículo"  23 ses
"ok. antes de continuar o atendimento, você vai precisar informar onde…"   19 ses
"ok, agora selecione o endereço onde está o veículo: *1 - endereço…*"      19 ses
"certo, agora preciso da *placa* do veículo."                              17 ses
                                          … 267 telas distintas ao todo
```

🔴 **A primeira linha é a tela do CPF da Allianz — 78 sessões.** É o nó que a
§2.2 desta SPEC elege como **prioridade #1** (retorno 5 × 78 = 390). O gate ② a
rejeitaria, o BLOCO 0 nunca fecharia, e §9 diz *"enquanto este bloco não fechar,
nenhum outro começa"*.

**É o espelho exato do defeito da v2:** o guarda da v2 **nunca ficava vermelho**;
o da v3 **nunca ficaria verde**.

📊 E o alvo verdadeiro sobrevive ao aperto: `"ok"` **sozinho** e `"um momento"`
**sozinho** somam **63 sessões** — humano, e ainda pegos pelo `^…$`.

> 🔴 **Guarda que nunca acusa é enfeite. Guarda que sempre acusa é bloqueio.**
> Por isso o ③ prova os dois sentidos.

### 2.5.2.1 🔴 O gate ④: cada uma das dez tem de provar a sua própria limpeza

**A métrica:** dentro da `zona='URA'` daquela seguradora, o **percentual de
EVENTOS cujo texto aparece em uma única sessão**. URA se repete; gente não.

## 🔴 E ela NÃO TEM LIMIAR FIXO, porque depende do TAMANHO DA AMOSTRA

🔴 **Um limiar fixo de 25% reprovaria 8 dos 10 recortes da seguradora que este
mesmo gate usa como piso.** 📊 A Allianz **já limpa**, fatiada em 10 blocos de ~14
sessões, dá `24,0 · 22,3 · 44,4 · 26,0 · 27,6 · 27,4 · 31,8 · 31,7 · 27,4 · 32,4`
— contra **12,6%** quando as 137 sessões entram juntas.

⚠️ **E isso mostrou que as duas âncoras da v3 não bastavam.** Elas travavam o
confundidor **menor** e deixavam o **maior** de pé:

```
variação por NORMALIZADOR (_norm × lower) .....   1 a 6 pontos   ← a v3 travou
variação por TAMANHO DE AMOSTRA ...............  mais de 30      ← ficou de pé
```

## 📊 A CURVA DE REFERÊNCIA — método, não adjetivo

🔴 **E o método NÃO é o fatiamento acima.** `ntile` agrupa por `session_id`, e
sessões vizinhas no id são vizinhas **no tempo e na corretora**: ele mede
**agrupamento**, não variância amostral.

📊 **A prova de que o `ntile` infla:** o bloco 3 deu **41,8%** (`_norm`) / 44,4%
(`lower`) — **acima do máximo de 60 sorteios aleatórios no mesmo `n`, que é
40,0%**. Um recorte contíguo não pode exceder o máximo de 60 sorteios se for
amostra aleatória. Logo **não é** — e usá-lo como teto **absolvia a hdi**.

**O método, escrito para ser executado:** Allianz limpa · **sorteio sem
reposição** · **60 reamostragens por `n`** · semente estável
`md5(session_id||rep||n)` — 🔴 **reproduzível; `random()` não é** · `_norm` real,
dentro do `medir_rota.py`.

```
  n      p50    p95    p99    desvio
 13     27,2   35,8   37,0    6,5
 14     25,2   36,3   38,2    6,0
 18     24,4   31,8   33,3    4,7
 22     22,9   28,6   28,8    3,8
 41     16,6   19,3   21,6    1,9
 46     16,0   19,4   20,8    2,3
 92     11,8   13,2   13,6    1,1
134      9,9   10,2   10,3    0,2
```

> ## A comparação é contra a CURVA, no MESMO `n` — e o teto é PERCENTIL
>
> ```
>   ≤ p95(n)      posição baixa na fila de conferência
>   > p95(n)      posição alta
>   > p99(n)      🔎 PRIMEIRA da fila
> ```
>
> 🔴 **E isso é POSIÇÃO NA FILA, não veredito.** A versão anterior desta caixa
> dizia *"> p99(n) 🔴 VERMELHO: a seguradora NÃO entra na fábrica"* — e a
> medição da §2.5.2.1 abaixo mostra que **o número não sustenta isso**
> (📊 31 pontos de dispersão entre corpora limpos). **Quem reprova é a leitura
> humana.**
>
> 🔴 **Nunca o máximo.** 📊 Em `n=14` a distância `p95 → max` é 3,7 pontos e é
> quase toda cauda de 60 sorteios. `p95` e `p99` são estáveis; o máximo não é.

⚠️ 🔴 **E o `teto(n)+10` da v4 saiu de ninguém.** Eu escrevi o `10` sem medir — o
defeito exato que esta SPEC cobra. Ele morre aqui, e o substituto **sai da própria
distribuição**, que já contém a margem. **Número que não sai de medição não entra
no gate — inclusive quando quem o deu foi o juiz.**

## 🔴 E AQUI A MÉTRICA PERDE O PODER DE REPROVAR — está medido

A v3, a v4 e a v5 usaram o hapax para condenar seguradora. 📊 **A medição que
faltava mostra que ele não sustenta isso.**

📊 **CONTROLE, 21/08/2026 — a curva de CADA seguradora LIMPA** (as quatro com
`FRONTEIRAS` vazia por classificação independente), no mesmo `n`, 60
reamostragens:

```
   n = 13            p50      p95
   alfa             10,5     10,5
   azul             20,6     24,6
   ALLIANZ          27,2     35,8      ← a referência que vínhamos usando
   bradesco         34,7     48,4
   tokio            41,7     66,7
```

🔴 **Trinta e um pontos de dispersão entre corpora que sabemos estarem LIMPOS.**
📊 A mapfre, com 57,4%, **cabe dentro do p95 da tokio limpa (66,7%)**.

### 📊 E o confundidor tem nome e número: o TAMANHO DA SESSÃO

```
   allianz  53,7 telas/sessão   ← a referência da curva
   hdi      39,6                     mediana das dez ≈ 20
   zurich   30,6
   azul     26,6
   yelum    25,0
   porto    20,0
   alfa     16,9
   mapfre   11,4
   bradesco 11,0
   tokio     6,7                ← OITO VEZES menos que a Allianz
```

**Sessão longa repete o tronco dezenas de vezes** — termo de privacidade, CPF,
endereço — e o hapax despenca. **Sessão curta é quase toda tela única.** Não é
sujeira: é a forma da URA.

🔴 **E isso condena a escolha da referência:** a Allianz é o **outlier extremo**
desse eixo (53,7 contra mediana 20). **Era a pior referência possível**, e foi a
que quatro versões usaram.

### O que sobrevive, e o que cai

| seguradora | medido | n | veredito v5 | veredito CORRETO |
|---|---:|---:|:---:|---|
| **porto** | 29,0 | 134 | 🔴 | 🔴 **sobrevive** — margem 18,7 com n=134 (desvio 0,2) **+** fronteira parcial (459 de 2.716) |
| mapfre | 57,4 | 13 | 🔴 | ⚠️ **não estabelecido** — cabe no p95 da tokio limpa |
| zurich | 53,3 | 14 | 🔴 | ⚠️ **não estabelecido** — idem |
| hdi | 26,5 | 41 | 🔴 | ⚠️ **não estabelecido** — curva própria desconhecida |
| yelum | 20,1 | 92 | 🔴 | ⚠️ **não estabelecido** — idem |

🔴 **E o erro corre nos DOIS sentidos.** Uma seguradora com URA **repetitiva** e
contaminada fica **abaixo** da curva da Allianz e passa. O gate não era só severo
demais — era **cego assimétrico**.

📊 **E note como a contaminação da mapfre foi realmente achada:** não pelos
57,4%. Foi **lendo** `"olá bom dia tudo bem? como posso te chamar?"`. **O número
nunca foi a prova. Foi a fila.**

> ## O gate ④ é TRIAGEM: ordena a fila, e quem reprova é a LEITURA
>
> ```
> ① o hapax por seguradora ORDENA a fila de conferência — não reprova ninguém
> ② a fila é o POOL INTEIRO, pré-filtrado — 🔴 NUNCA um top-15
> ③ 🔴 UM HUMANO LÊ e decide: é tela de URA, ou é gente?
> ④ o que ele marcar como gente vira entrada da `FRONTEIRAS` ou do filtro ②,
>    com a contagem medida ao lado
> ⑤ VERMELHO = a fila AINDA TEM GENTE.
>    🔴 Nunca "o número passou de X".
> ```

### 🔴 Por que o pool inteiro, e não um top-15

📊 O pool — zona URA, telas vistas em **≤3 sessões** — é grande:

```
seguradora   telas URA   pool ≤3 ses   um top-15 cobriria
porto            758         679             2,2 %
allianz          551         476             3,2 %
yelum            564         450             3,3 %
hdi              493         416             3,6 %
zurich           234         221             6,8 %
azul             140         107            14,0 %
bradesco         109          91            16,5 %
mapfre            96          90            16,7 %
tokio             78          64            23,4 %
alfa              51          44            34,1 %
              ------      ------
               2.974       2.638
```

🔴 **Um top-15 lê 2,2% da porto.** Nomear 15 falas e declarar a fila limpa é
**o guarda que quase não pode falhar** — o defeito da v2 voltando pela porta da
triagem.

**O pré-filtro que torna a fila tratável, medido:**

```
pool bruto ....................................... 2.638 telas
  com MARCA DE URA (botão · `*` · "opção" · "digite" ·
     "selecione" · numeração · "menu") ............ 1.386  (53 %)  descarte automático
  longa (≥90 char) sem marca ......................   554  (21 %)  TIER 2: amostra de 50
  🔴 curta (<90) sem marca ........................   698  (26 %)  TIER 1: LIDA INTEIRA
```

> ### 📊 O CONTROLE DO PRÉ-FILTRO — e ele traz a própria taxa de erro
>
> Rodado na Allianz, contra as **duas zonas conhecidas**:
>
> ```
> do HUMANO conhecido, entra na fila ..... 53,7 %   ← sensibilidade
> da URA    conhecida, entra na fila .....  6,8 %   ← falso positivo
>                                  enriquecimento 7,9×
> ```
>
> ✅ **Especificidade boa:** descarta 93,2% da URA — quase nenhuma leitura
> desperdiçada.
> 🔴 **Sensibilidade 53,7%:** quase metade do humano **não** entra na fila.

## 🔴 E isto obriga a SPEC a admitir: A TRIAGEM NÃO PROVA LIMPEZA

Com sensibilidade de 53,7%, **~46% do humano remanescente não passa pela fila**.
Ler a fila inteira **não** prova ausência de gente, e o gate **não pode afirmar
que prova**.

**A rede que pega o resto são os TRÊS JUÍZES por rota (§6.2).** O JUIZ 1 CÉTICO
pergunta *"alguma tela do corpus não casa passo nenhum e pede algo?"* — e uma
fala humana sobrevivente aparece **ali**, na rota específica, com o executor
olhando. **Captura em segunda instância**, e está escrito porque a primeira não
basta.

⚠️ 🔴 **E o PRÉ-FILTRO É CÓDIGO, fixado como a `FRONTEIRAS` — não uma regex que
cada um escreve.** 📊 Duas implementações do mesmo critério deram fila de **486**
e de **698**. É o mesmo defeito do `_norm` × `lower()`: **o número se move com a
implementação**, e um gate de completude (`len(fila) == len(vereditos)`) sobre um
denominador que muda não guarda nada.

```python
MARCAS_DE_URA = [           # 📊 descarta 53% do pool · falso positivo 6,8%
    r"\*",                  # negrito do WhatsApp — a URA usa, gente quase não
    r"op[çc][ãa]o|digite|responda|selecione|menu",
    r"^[0-9]+ ?[-.)]",      # item numerado
]
LIMITE_TIER_1 = 90          # caracteres. 📊 acima disso, 554 telas → amostra
```
📊 Mudar qualquer um destes valores **muda a fila e o gate G1**. Por isso eles
vivem no código, versionados, com a contagem do dia ao lado.
>
> ### 🔴 O único uso numérico que sobrevive: INTRA-seguradora
>
> Depois de ampliar a `FRONTEIRAS` de uma seguradora, **o hapax DELA tem de
> CAIR**. É a comparação dela com ela mesma, e o confundidor da diversidade
> **se cancela**.
>
> 📊 Referência do que é uma queda real: a Allianz foi de ~50% (bruto) para
> **9,4%** quando a fronteira dela entrou. **Ampliação que não derruba o
> número não achou nada.**

📊 **A linha de controle da v5 continua válida — e prova menos do que dizia.**
As 4 limpas ficaram abaixo e as 5 sujas acima da curva da Allianz; isso é
verdade. Mas com as curvas próprias medidas, sabemos que **bradesco e tokio
ficaram abaixo APESAR de terem URA mais diversa que a Allianz** — o que
**fortalece** a conclusão delas — enquanto **hdi e yelum ficaram acima sem que se
conheça a curva delas**.

> **O controle separa bem os extremos e não separa o meio.** É o que ele prova, e
> é só isso que a SPEC pode afirmar com ele.

🔴 **E a curva continua indo no relatório de toda rodada** — agora como **ordem
de conferência**, não como veredito. Limiar que não mostra a curva que o produziu
é opinião com aparência de medida — **inclusive quando quem deu o número foi o
juiz. Quatro vezes nesta SPEC, foi.**

> ## ⚠️ E o CONFUNDIDOR MENOR, que também precisa de trava: o normalizador
>
> 📊 A mesma medição, refeita com `lower()` em vez de `_norm`, dá **os mesmos
> eventos por zona** (3.776 · 2.257 · 1.532 · 418 · 148 — idênticos) e
> **percentuais 1 a 6 pontos acima**:
>
> ```
>                 _norm      lower()
>    allianz       9,4 %     12,6 %
>    tokio        19,2 %     26,0 %
>    porto        29,0 %     32,3 %
> ```
>
> 🔴 **Por isso a métrica é calculada dentro de `medir_rota.py`, sobre o `_norm`
> real** — nunca ad-hoc, nunca em SQL. A curva e a medida têm de sair do **mesmo
> código**, senão comparam coisas diferentes.
>
> ⚠️ **A v3 propunha travar isto com "duas âncoras" — a Allianz limpa (piso) e a
> zona HUMANO da Allianz (teto, 44,8%).** 📊 Ficou errado por medição: `p99(14)`
> é **38,2%**, então 44,8% como teto **deixa passar contaminação em amostra
> pequena**. As âncoras foram substituídas pela curva inteira.

🔴 **Um guarda calibrado numa seguradora não guarda as outras nove.** Foi assim
que a v2 quase entrou limpando 38% do acervo e carimbando os outros 62%.

---

## 3. 🔴 AS REGRAS DE ATUALIDADE

O cenário que o Founder descreveu, resolvido em regras que um agente segue sem interpretar.

### 3.1 O cenário, literal

> *"Se um atendimento for de Allianz residencial guincho e for feito hoje, e na 4ª pergunta tiver que escolher entre guincho × chaveiro… as atualizações até a pergunta 4 devem ser consideradas e valem para todas as rotas.*
>
> *Se a pergunta 1 desse atendimento tiver uma mudança, todas as rotas que tiverem a mesma pergunta precisarão ser ajustadas, porque é a primeira pergunta para todas.*
>
> *Se a pergunta 4 que mudou, as rotas que têm as perguntas 1, 2 e 3 sem mudança precisam continuar as mesmas. Só a partir da URA mudada é que devemos ajustar.*
>
> *Se o último atendimento de chaveiro da Allianz auto foi em dezembro e guincho foi hoje, precisa ser ajustado para chaveiro se a mudança influencia chaveiro também."*

### 3.2 As cinco regras

```
R1 · A ATUALIDADE É DO NÓ
     Cada TELA tem a sua própria data de "visto por último", e ela é o MAIOR
     `wa_timestamp` em que aquela tela apareceu — em QUALQUER sessão, de
     QUALQUER serviço, de QUALQUER corretora.

     📊 A tela do CPF da Allianz foi vista em 19/08/2026, numa sessão de
     eletrodoméstico. Ela está atualizada para o chaveiro também.

R2 · A MUDANÇA SOBE, NUNCA DESCE
     Uma tela que mudou afeta TODAS as rotas que passam por ela — e só elas.
     Rota que não passa por aquela tela não é tocada.

     Como se decide "quem passa por ela": as sessões do corpus em que a tela
     aparece, e os serviços dessas sessões.

R3 · O PREFIXO INTACTO NÃO SE MEXE
     Se a tela que mudou está na posição 4, as telas 1, 2 e 3 continuam
     idênticas para todas as rotas. Mexer nelas "de carona" é a forma mais
     rápida de quebrar rota que estava boa.

     Verificador: depois de qualquer mudança, o replay de TODAS as rotas
     daquela seguradora tem de manter ou aumentar as respondidas. Uma que
     caia é regressão, e o bloco não fecha.

R4 · SESSÃO ANTIGA NÃO INVALIDA TELA NOVA — E VICE-VERSA
     Se o último chaveiro foi em dezembro e o guincho foi hoje, e as duas
     sessões passam pela tela X:
       · a tela X vale pela versão de HOJE (R1)
       · as telas que SÓ o chaveiro vê continuam com a evidência de dezembro,
         e ficam marcadas com essa data
       · a rota do chaveiro recebe o carimbo `TRONCO_ATUAL / FOLHA_ANTIGA`

     🔴 É PROIBIDO concluir "o chaveiro está velho, não mexe". A parte dele
     que é tronco está atualizada, e ela é a maior parte.

R5 · DUAS REDAÇÕES DA MESMA TELA = A NOVA VENCE, A ANTIGA SOBREVIVE
     Quando a mesma tela aparece com dois textos, a âncora é AMPLIADA para
     cobrir os dois — nunca trocada.

     📊 Razão medida: a redação de 26/03 da abertura da Allianz aparece em 64
     sessões. Trocar a âncora emudeceria o corredor se a seguradora voltasse
     atrás, e apagaria a capacidade de ler o próprio acervo.

     E o CONTROLE é obrigatório no teste: a redação antiga TEM de continuar
     casando. Foi assim que o conserto de `numero_residencia` foi feito
     (`(?:informe|confirme)`, e não `confirme`).
```

### 3.3 🔴 Como o agente decide o que é tronco e o que é folha

🔴 **Não por intuição. Por medição — e a medição é em PYTHON, não em SQL.**

📊 A consulta SQL da v1 não roda. Os dois erros, reproduzidos:

```
select _norm('teste');
→ ERROR 42883: function _norm(unknown) does not exist

with s as (select session_id, <classificador sobre `text`> ... group by 1)
→ ERROR 42803: column "observed_events.text" must appear in the GROUP BY clause
```

`_norm` é função **Python** (SPEC-083 §5.4) e a SPEC-083 §5.4 manda **reusá-la** —
o que por si só já diz que ela não é SQL. E sem `_norm`, o agrupamento cai no
texto cru: 📊 **1.527 linhas** devolvidas para a Allianz, para uma URA de ~25
telas.

⚠️ **E reescrever a query em SQL também não resolve**: a normalização exige
`unaccent`, e 📊 medido em 21/08/2026, **`unaccent` não está instalado** neste
banco (`select extname from pg_extension where extname='unaccent'` → vazio).

🔴 **Reimplementar `_norm` em SQL é proibido** — seria um segundo normalizador ao
lado do que já existe, exatamente o que o CLAUDE.md §5 veda. Dois normalizadores
divergem no dia em que um for corrigido, e o corpus passa a discordar do motor
que ele mede.

**Portanto: a árvore é gerada por `medir_rota.py`, reusando o `_norm` real e o
`PADROES_DE_SERVICO` real.** É entrega do BLOCO 0:

```bash
python backend/scripts/medir_rota.py --exportar-arvore --seguradora <SEG>
```

O que ele faz, e é só isto:

```python
# 1. marca as zonas com `zonas()` (§2.5.1.1) e fica SÓ com zona='URA'
# 2. tela = _norm(text)                     ← o _norm de verdade, importado
# 3. serviço de cada SESSÃO: PADROES_DE_SERVICO (SPEC-083 §5.5), aplicado
#    evento a evento e reduzido por sessão com OR -- uma sessão pode ver
#    mais de um serviço, e `outros` NÃO entra na contagem (§2.2)
# 4. por tela: nº de serviços distintos, nº de sessões, visto por último
# 5. descarta tela vista em 1 só sessão, salvo se for anterior à primeira
#    escolha de serviço (o viés declarado abaixo)
```

Saída, uma linha por tela:

```
tela | servicos | sessoes | visto_por_ultimo | classe
```

```
servicos ≥ 3  →  TRONCO       consertar aqui paga por todas as rotas
servicos = 2  →  GALHO        paga por duas
servicos = 1  →  FOLHA        paga por uma
```

⚠️ O classificador é o `PADROES_DE_SERVICO` entregue pela SPEC-083 §5.5. **Não invente outro** — e não o reescreva em SQL.

⚠️ E há um viés a declarar: uma tela que só apareceu numa sessão parece folha mesmo sendo tronco. Por isso a classificação **também** olha a posição: tela que aparece antes da primeira escolha de serviço é tronco **por construção**, mesmo com `servicos = 1`.

---

## 4. A ORDEM DO TRABALHO

### 4.1 A pergunta que o Founder fez

> *"Precisa ver qual é a melhor sequência… se por seguradora, se por ramo, etc."*

**A resposta que a árvore dá: nem por seguradora, nem por ramo. Por PROFUNDIDADE — e dentro de cada profundidade, por demanda.**

```
ONDA 1 · O TRONCO de cada seguradora        ← paga por TODAS as rotas dela
ONDA 2 · Os GALHOS (auto / residencial)     ← paga por metade
ONDA 3 · As FOLHAS, por demanda medida      ← paga por uma
```

### 4.2 Por que é essa, e não outra

**Por seguradora inteira** — faria o executor escrever a folha do chaveiro da Allianz antes do tronco da Porto. 📊 A Porto tem **137 sessões** no acervo (134 com tela `in`) — seu tronco é visto por até esse tanto; a folha do chaveiro da Allianz, por poucas. ⚠️ O número exato do tronco só existe depois do BLOCO 0: a v1 dizia *"138 sessões"* com 📊, e 138 é **mais sessões do que a Porto tem**.

**Por ramo** — quebra a árvore no lugar errado: 📊 `Termo de Privacidade` e `CPF` são vistos por auto **e** residencial.

**Por demanda pura** — começaria por `chaveiro` (213 sessões), que é folha de 10 seguradoras diferentes; cada uma exigiria o tronco daquela seguradora antes. Ordem que se auto-bloqueia.

**Por profundidade** — cada onda entrega valor para todas as rotas abaixo dela, e nunca espera nada de uma onda posterior.

### 4.3 Dentro de cada onda, a ordem é o RETORNO MEDIDO

```
retorno(nó) = (nº de rotas que passam por ele) × (nº de sessões em que aparece)
```

📊 Exemplo, Allianz: a tela do CPF (5 serviços × 78 sessões = 390) vem antes da tela do número da residência (4 × 72 = 288).

⚠️ A v1 e a v2 diziam *"complemento de endereço (4 × 71 = 284)"* — 📊 `71` não aparece em lugar nenhum da tabela §2.2, que traz 79 e 72. Número herdado que sobreviveu ao conserto da tabela ao lado dele.

E entre seguradoras, na Onda 1, o desempate é o tamanho do acervo:

📊 Medido em 21/08/2026 (`count(distinct session_id)` por `insurer_key`):

```
allianz 140 · porto 137 · yelum 100 · tokio 46 · hdi 43
bradesco 22 · azul 19 · zurich 14 · mapfre 13 · alfa 9        soma 543 + 1 sem chave = 544
```

🔴 A v1 trazia `141 · 138 · 100 · 47 · 44 · 22 · 19 · 15 · 13 · 9` **com marca
📊** — errado em 5 dos 10, sempre para mais, e **somando 548 num universo de
544**. A ordem relativa não mudou; a lição, sim: tabela que soma mais que o
universo não vai para produção com 📊 (CLAUDE.md §12.1).

⚠️ **E esta ordem é 💭 provisória.** Os dois fatores do retorno — serviços e
sessões — mudam quando a zona humana sai (📊 −49,7% dos eventos da Allianz).
**O BLOCO 0 regera a ordem com `zona='URA'`, e a versão medida substitui esta.**

### 4.4 🔴 A exceção que vem antes de tudo: a régua fecha a si mesma

📊 A SPEC-083 v7 §4.1 mediu a rota de referência: **piso 73 · teto 84 · gate ≥70**.

🔴 **E os pontos que faltam não são três. São cinco** — todos nomeados pela
própria SPEC-083:

| # | o quê | eixo | +pts | fonte |
|---|---|:---:|---:|---|
| 1 | transcrever a sessão `7ac3c101` no bloco do subserviço `maquina_de_lavar` | A | +4 | 083 §4.1 |
| 2 | mapear a órfã funcional `"Agendamento para: … Podemos continuar ?"` | B | +10 | 083 §4.2 |
| 3 | contagem própria no `notes` dos passos respondidos | B | +5 | 083 §3.3 |
| 4 | **`handoff_triggers`: 3 dos 4 casam ZERO no acervo** | C | +3 | 083 §4.1 |
| 5 | **`regras_para_o_cliente` com trecho ≥40 char que case o corpus** | D | +3 | 083 §4.1 |
| | **73 + 25 = 98** | | | |

🔴 **Com só os três primeiros o teto é 92, e o gate de 95 é impossível por
aritmética.** A v1 desta SPEC listava três itens somando +19 sobre um piso de 73,
exigia ≥95, e faltavam **3 pontos que não existiam em lugar nenhum** — enquanto
§9 diz *"enquanto este bloco não fechar, nenhum outro começa"*. A SPEC inteira
parava no primeiro bloco.

⚠️ É **exatamente** o defeito que a §6.4 desta SPEC se gaba de ter achado na
SPEC-083 v1. Não fizemos a soma da nossa própria lista.

**E a SPEC-083 v7 §4.3 já tinha avisado, literalmente:**

> *"⚠️ **O gate NÃO exige 'exatamente 3 itens'.** A versão anterior exigia, e o
> próprio conserto da rubrica levou a lista para 4–5 — um gate que quebra quando
> a SPEC melhora não é gate, é armadilha."*

> ## GATE DO BLOCO 0 — é o da SPEC-083 §4.3, não um novo
>
> · `medir_rota` roda e a lista **"O QUE FALTA PARA 95" é inteiramente
>   nomeável** — nenhum item é *"não sei por quê"*
> · a nota medida entra no relatório **com a saída real colada**
> · **≥95 só vira gate depois** que os cinco itens acima estiverem fechados
>
> 🔴 **Nunca maquiar a rota para calar a régua** (083 §4.3).

**Razão de tudo isso vir antes:** enquanto a régua não fechar a si mesma, ela não
é régua — é aspiração. E 61 rotas seriam medidas contra ela.

### 4.5 A segunda exceção: o serviço que já funciona e está desligado

📊 **Socorro mecânico** aparece em **38 sessões** do acervo (yelum 21, zurich 9, hdi 8) e `subservice_supported()` devolve `False`. Não existe `socorro_mecanico` em nenhum `subservices` nem em `_SUBSERVICE_ALIASES`.

**Estamos recusando um serviço que os clientes pedem e que a URA atende.** Entra logo depois dos **cinco itens** da régua (§4.4).

📊 **Medição refeita e confirmada em 21/08/2026: yelum 21 · zurich 9 · hdi 8 = 38 sessões.** O número está firme.

⚠️ O que continua **não** reproduzindo é a afirmação separada de *"6 sessões com protocolo, 2 ao vivo"* — ela segue sob `ANCORA_SUSPEITA`, porque a zurich não escreve *"protocolo"*. As 38 sessões não dependem dela.

---

### 4.6 🔴 A DECISÃO QUE A SPEC-083 DELEGOU A ESTA SPEC: a fábrica de espelhos

📊 A SPEC-083 nomeia a SPEC-084 em **20 linhas** e delega decisões por nome. 📊 A
v1 desta SPEC não continha uma única ocorrência de `SEM_FABRICA`, `SEM_ESPELHO`,
`denominador`, `espelho` nem `banda por fração`. **Recebemos uma delegação e não
soubemos que ela existia.**

📊 SPEC-083 §3.5/§3.9: **13 corredores** perdem 6 dos 10 pontos do eixo D por
razão **arquitetural** — não por descuido — e ~40 das 62 rotas de auto ficam com
**denominador 90** sob a dispensa `SEM_FABRICA`.

> **A decisão desta SPEC, e ela vem ANTES do BLOCO 1:**
>
> `[ ] criar a fábrica` · `[ ] preencher uma a uma` · `[ ] manter a dispensa`

🔴 **E a consequência tem de estar escrita, seja qual for a escolha.** A
SPEC-083 v7 já a declarou:

> *"⚠️ E `AAA` com denominador <100 é PROVISÓRIO… **No dia em que criar [a
> fábrica], os 10 pontos voltam ao denominador e a rota "AAA" cai para
> 86/100 = "quase".**"*

📊 A rota que cai é `allianz × residencial × maquina_de_lavar` — **a mesma que é o
gate do BLOCO 0**. Ou seja: o BLOCO 0 se mede contra uma régua que o próprio
BLOCO 0 pode mudar.

**Como isso se resolve, e não é adiando:**

```
· O BLOCO 0 registra as DUAS leituras da rota de referência: /90 e /100
· O gate é sobre /100 -- a leitura que sobrevive à decisão
· Isso NÃO é regressão. É a régua ficando honesta, e o relatório diz isso
  com essas palavras.
```

🔴 **E todo `≥95` desta SPEC significa 95% do DENOMINADOR REAL daquela rota**,
sempre exibido com o denominador ao lado (083 §3.9) — `AAA(90)`, `quase(100)`.
**Nunca reescalar para /100**: contra denominador 90, "95 pontos" é impossível
por construção, e um gate impossível reprova trabalho bom.

---

## 5. O PROCESSO DE UMA ROTA

**Uma rota por vez. Nunca duas.** Foi assim que a máquina de lavar deu certo — e 📊 é a diferença dela para as outras 61.

### 5.1 Os sete passos

```
① COLHER
   Ache as sessões do corpus que passam por esta rota, ordenadas por
   `wa_timestamp` decrescente. Para cada TELA da rota, a versão válida é a
   MAIS RECENTE em que ela apareceu — em qualquer sessão, de qualquer
   serviço (R1).

   🔴 O corpus é `zona='URA'` (§2.5). Tela da zona humana NUNCA entra.

   Zero telas de URA → PARA. Devolve `SEM_CORPUS` com o roteiro de coleta,
   e NÃO escreve passo nenhum.
   🔴 `SEM_CORPUS` NÃO é o mesmo que `NAO_RESPONDE` — ver §7.2. Confundir os
   dois manda para coleta uma rota cujo acervo está cheio.
   🔴 Inventar rótulo de menu manda o segurado para a opção errada — e o
   corredor não trava, ele RESPONDE COM CONFIANÇA a coisa errada.

② TRANSCREVER
   No comentário do bloco, turno a turno, na ordem em que a URA usou, com a
   marca `📊 sessão <8 hex>` de cada uma. É o que permite auditar sem voltar
   ao banco — e vale 4 pontos do eixo A da régua.

③ ESCREVER
   passos exclusivos com `only_subservices` · teclas fixas no subserviço ·
   derivação com DEFAULT para toda tecla dinâmica · apelidos do jeito que o
   cliente fala (tirados do acervo) · `regras_para_o_cliente` e
   `expectativa_do_desfecho` lidos nas telas.

   🔴 REGRA DE ORDEM: `match_ura_step` devolve o PRIMEIRO que casa. Tela que
   pede resposta vai ANTES de qualquer `noop` largo.

④ PROVAR
   Teste que chama o MOTOR, com `MUTACOES` declaradas e executadas por
   `medir_rota --verificar-mutacoes`.

   ⚠️ A regra é a `CLAUDE.md §9.4` — que 📊 **ainda não existe** no arquivo
   (hoje há §9.1, §9.2, §9.3). Ela é a **Entrega 1 da SPEC-083** (§8.1), e a
   SPEC-083 fecha antes desta. Se o executor abrir o CLAUDE.md e não achar
   a §9.4, a SPEC-083 não foi executada — PARE e execute-a primeiro.
   O critério, enquanto isso, é a regra por-arquivo da SPEC-083 §3.7.

⑤ MEDIR
   `python backend/scripts/medir_rota.py --seguradora X --ramo Y --servico Z`
   Meta: **95% do denominador REAL da rota**, exibido com o denominador ao
   lado — `AAA(90)`, `quase(100)` (§4.6). Nunca reescalar para /100.
   ⚠️ E `≥95` só é **gate** depois que os cinco itens de §4.4 fecharem
   (§4.4 e BLOCO 0). Antes disso, o gate é ≥70 com a lista nomeável.

⑥ JULGAR
   Os três juízes de §6. **A liberação é deles, nunca do executor.**

⑦ REGISTRAR
   O que ficou faltando por ausência de evidência vai para `PENDENCIAS.md`
   com o que destrava. Rota liberada com lacuna anotada é honesta;
   rota liberada em silêncio, não.
```

### 5.2 🔴 Depois de CADA rota: o replay de regressão

⚠️ **As flags `--todas-as-rotas-dela` e `--antes-e-depois` não existem.** 📊 A
SPEC-083 entrega `--seguradora/--ramo/--servico`, `--replay-detalhado`,
`--verificar-mutacoes` e `--todas` (tabela global) — **nenhuma filtra por
seguradora, e nenhuma persiste linha de base**. Escrito como estava, o VERIFY do
BLOCO 1 simplesmente não roda, e o risco #1 desta SPEC fica sem fechamento.

🔴 **Construir as duas é entrega do BLOCO 0**, dentro do `medir_rota.py` — nunca
um script paralelo (CLAUDE.md §5):

```bash
# grava a linha de base ANTES de tocar na seguradora
python backend/scripts/medir_rota.py --todas --seguradora <SEG> \
       --salvar-linha-de-base .baseline/<SEG>-<commit>.json

# depois de cada rota, compara
python backend/scripts/medir_rota.py --todas --seguradora <SEG> \
       --comparar-com .baseline/<SEG>-<commit>.json
# uma linha por rota: respondidas ANTES → DEPOIS
# exit != 0 se QUALQUER rota perdeu respondidas (R3)
```

**Nenhuma rota daquela seguradora pode ter perdido respondidas.** Uma que caia é
regressão, e o trabalho volta antes de seguir.

🔴 **E o comparador tem de PODER ACUSAR.** Antes de confiar nele, o BLOCO 0
**regride uma âncora de propósito** e exige `exit != 0`. Comparador que nunca
acusa não é gate — é enfeite (CLAUDE.md §9.3).

📊 **Razão de existir:** contado em `corridor_playbooks.py` em 21/08/2026, **41
nomes de passo** (chave `"step"`) aparecem em mais de um lugar — 207 ocorrências,
146 distintas — e **19 âncoras** se repetem. E `_YELUM_FAMILY_STEPS` alimenta
`hdi-auto` **e** `yelum-auto`. Mexer num passo de família mexe em dois corredores.

⚠️ A v1 dizia *"58 assinaturas"* com marca 📊 e **não foi possível reproduzir 58
por método nenhum**. A direção da afirmação se sustenta com 41; o número, não.

### 5.3 Como os subagentes se dividem

🔴 **Nenhum coletor roda em paralelo antes do BLOCO 0 fechar.** Com a zona
(§2.5) ainda não implementada, dez coletores produzem **dez corpora
contaminados ao mesmo tempo** — e o retrabalho é dez vezes maior que a espera.

```
COLETOR    lê o acervo, monta o corpus da rota, classifica tronco/galho/folha
           NÃO escreve corredor

ESCRITOR   recebe o corpus do coletor e escreve passos, teclas, apelidos, teste
           NÃO consulta o banco

JUÍZES     recebem o resultado e o corpus
           NÃO escrevem nada
```

🔴 **Quem observa não escreve.** Se o mesmo agente colhe e escreve, ele escreve o que gostaria de ter visto. A separação é o que torna o corpus uma prova, e não uma justificativa.

**Paralelismo permitido — mas SÓ DEPOIS que o BLOCO 0 fechar:** um COLETOR por seguradora, em paralelo. **Um ESCRITOR por rota, em série dentro da seguradora** — porque duas rotas da mesma seguradora tocam os mesmos arquivos.

---

## 6. 🔴 OS JUÍZES — E O LAÇO QUE NÃO ACABA ATÉ LIBERAR

### 6.1 A regra do Founder, literal

> *"O juiz deve falar, o executor fazer os ajustes, e o juiz conferir de novo. E fazer isso até liberar de verdade. Não pode ser feito o juiz fala, executa e acabou."*

```
      ┌──────────────────────────────────────────────┐
      │                                              │
      ▼                                              │
   EXECUTOR escreve  ──▶  JUÍZES julgam  ──▶  reprovou? ──┘
                                │
                            aprovou (os TRÊS)
                                │
                                ▼
                        ROTA LIBERADA
```

**A liberação é do juiz. Sempre. O executor nunca declara pronto.**

### 6.2 As três lentes

Lentes **diferentes** de propósito — três agentes idênticos encontram o mesmo defeito três vezes e perdem os outros dois.

#### 🔍 JUIZ 1 — O CÉTICO
*Tenta refutar que a rota está pronta.*

- Alguma tela do corpus **não casa** passo nenhum e **pede** algo?
  🔴 **"Corpus" aqui é `zona='URA'` (§2.5), sempre.** 📊 Sobre o corpus bruto esta pergunta devolve **472 telas** na Allianz contra **126** no corpus limpo — 3,7× — e nenhuma rota da seguradora seria liberada jamais.
- Alguma âncora casa **zero** vezes no acervo? (o defeito do `numero_residencia`)
- Alguma âncora é **larga demais** e rouba a tela de outro passo?
- A transcrição bate com a sessão que ela cita?
- 📊 O número no `notes` é **daquela seguradora**, ou foi copiado de família?

**Reprova se:** qualquer resposta acima for sim.

#### 🛡️ JUIZ 2 — O SEGURANÇA
*Onde errar é irreversível, o corredor para?*

- O freio de finalização **casa a tela real** de confirmação desta rota?
- Toda tecla `_opcao` tem origem nas **três** fontes?
- A tecla escolhida é **a certa**? (📊 `14` é máquina de lavar; `10` é lava-louças; `13` é secadora)
- Existe tela que **pede dinheiro** ao cliente e é respondida automaticamente? (📊 a Yelum tem: *"valor excedente a ser pago para o prestador de $ 115,00"*)
- Alguma resposta **afirma um fato** que ninguém confirmou? (📊 a tela *"idade do aparelho? 1- Até 10 anos"* é respondida `"1"` sem ninguém ter confirmado)

**Reprova se:** qualquer irreversível não estiver freado.

#### 🧍 JUIZ 3 — O SEGURADO
*Ele soube o quê, e quando?*

- Ao final, o cliente recebe **protocolo + dia + período**?
- As `regras_para_o_cliente` são ditas **antes** do acionamento?
- O que o cliente ouve é **verdade**? (📊 o corredor disse *"a senha são os 4 últimos do telefone informado"* e a senha era a do número da corretora)
- Se travar, o cliente **fica sabendo**?
- A `expectativa_do_desfecho` está certa? (📊 eletrodoméstico é **agendado**, não é hoje)

**Reprova se:** o cliente puder ser surpreendido por algo que o sistema já sabia.

### 6.3 O teto do laço, e o que acontece ao bater nele

```
VOLTA 1   executor escreve  → juízes julgam → reprovou? devolve O MOTIVO
VOLTA 2   executor corrige com o motivo em mãos
VOLTA 3   última — e o prompt do executor DIZ que é a última
──────────────────────────────────────────────────────────────────
BATEU O TETO  não é silêncio, e não é liberação:

   · a rota vira `PRECISA_DE_HUMANO` no inventário
   · o dossiê traz: as 3 versões, e por que CADA uma foi reprovada
   · vai para `PENDENCIAS.md` com o que destrava
   · o Founder decide: aceitar com lacuna anotada, ou coletar mais evidência
```

🔴 **Três é o número.** Depois disso um modelo forte para de melhorar e começa a inventar — e invenção é exatamente a falha que se quer evitar num menu de URA.

⚠️ **Reprovação sem motivo acionável não conta como volta.** O juiz que reprovar tem de dizer **qual conferência** falhou e **qual tela** a prova. "Está incompleto" não é reprovação — é ruído, e o executor devolve pedindo o motivo.

### 6.4 O juiz também julga a SPEC

O mesmo laço vale para os documentos: **esta SPEC** foi ao juiz, será corrigida, e volta ao juiz até liberar. 📊 A SPEC-083 foi reprovada com 54/100 na primeira volta — e o defeito mais grave (o gate matematicamente impossível) só apareceu porque alguém foi conferir a aritmética.

---

## 7. O QUE FAZER QUANDO NÃO HÁ CONVERSA

### 7.1 A regra

> *"Se não existirem as conversas nas seguradoras, deve ser feito até onde temos evidências e anotar o que falta ser conferido."*

```
① Escreva os passos que a evidência sustenta.
② Onde a evidência acaba, o corredor NÃO inventa: o passo seguinte é o
   `pausar_e_chamar`, que responde ao cliente
   💭 "Só um instante, vou confirmar com a equipe" e chama o humano.
③ A rota é liberada pelo juiz com o carimbo `PARCIAL: até a tela N`.
④ `PENDENCIAS.md` recebe: qual tela falta, quantas sessões teriam de
   existir, e o roteiro de coleta.
```

🔴 **Um corredor que para e avisa é infinitamente melhor que um que responde chutando.** Chutar não trava — abre o chamado errado.

### 7.2 Os SEIS estados de fonte, e o que cada um permite

| estado | o que significa | o que o executor faz |
|---|---|---|
| 🟢 **COMPLETA** | o corpus cobre a rota ponta a ponta | rota inteira; meta = 95% do denominador real |
| 🟡 **PARCIAL** | o corpus acaba no meio | até a última tela; `pausar_e_chamar` no resto; meta **declarada** |
| 🟠 **ANCORA_SUSPEITA** | 🔴 **NÃO é ausência de fonte** | amplia a âncora de desfecho daquela seguradora, **depois** mede |
| 🔵 **NAO_RESPONDE** | 📊 **há corpus** e o corredor não casa | 🔴 **É TRABALHO DESTA SPEC: escrever passos.** Nunca vai para coleta |
| 🔴 **SEM_CORPUS** | zero telas com `zona='URA'` desta rota | só a lista de coleta. Não escreve passo |
| ⚫ **ROTA_INDISTINGUIVEL** | a URA não separa este serviço de outro | §7.3. 🔴 **NÃO escrever antes de criar a marca** |

🔴 **`SEM_FONTE` foi ELIMINADO.** Ele fundia dois estados **opostos, com ações
opostas** — e a SPEC-083 v7 proíbe a fusão por nome:

> *"São **estados opostos, com ações opostas**: `SEM_CORPUS` é trabalho do Bloco
> A; `NAO_RESPONDE` é trabalho da SPEC-084 (escrever passos). 🔴 **Fundir os dois
> faria a 084 reescrever corredores que já funcionam** — é o mesmo erro que a v1
> cometeu ao mandar 13 rotas para coleta com o acervo cheio."*

📊 `ANCORA_SUSPEITA` cobre hoje **13 rotas**: mapfre (4), bradesco (4), zurich (5)
— porque zurich e bradesco escrevem *"ordem de serviço"*, não *"protocolo"*, e
mapfre casa zero em 13 sessões.

### 7.3 🔴 As 8 rotas em que a URA NÃO DISTINGUE o serviço

📊 SPEC-083 §3.4, literal:

> *"`mapfre` mapeia os quatro serviços para `"Assistência 24H"`; `bradesco` dá
> `"1"` para guincho **e** bateria; `zurich` dá `"4"` para guincho e bateria. São
> **8 rotas** em que a marca não existe… **Criar a marca é entrega da SPEC-084**."*

🔴 **É PROIBIDO escrever a rota do guincho nessas 8 antes de criar a marca.**

Sem ela o corredor **não erra o menu**: ele acerta o menu e **abre o chamado
errado**. O segurado pede guincho e recebe bateria. E o JUIZ 2 (§6.2) pergunta
*"a tecla escolhida é a certa?"* — na zurich, `4` é as duas. **A pergunta não tem
resposta**, então o juiz não pode nem aprovar nem reprovar.

**Criar a marca** = achar, no corpus `zona='URA'`, a tela **posterior** à tecla
comum que separa os dois serviços — 💭 por exemplo *"o veículo está em local
seguro?"*, se ela só aparecer em guincho — e usá-la como discriminador.

```
tela discriminadora existe   →  vira o passo que separa, e a rota segue
NÃO existe                   →  `PRECISA_DE_HUMANO`, direto, SEM as 3 voltas
```

🔴 **O segundo caso não é falha do executor: é ausência de sinal na URA.** Ele vai
para `PENDENCIAS.md` dizendo exatamente isso, e o que destravaria (uma coleta
dirigida, ou um canal diferente na seguradora).

---

## 8. 🔴 MULTI-CORRETORA: A MESMA PERGUNTA, DADOS DIFERENTES

### 8.1 A decisão, e a autoridade

📊 As duas corretoras têm acervos da mesma seguradora:

| | Resulta | AutoFleet |
|---|---:|---:|
| allianz | 10.608 ev · 93 sessões | 2.546 ev · 47 sessões |
| porto | 2.004 · 38 | 2.506 · 99 |
| yelum | 1.056 · 18 | 3.548 · 82 |

**Decisão do Founder, registrada:** *"A seguradora tem a mesma pergunta para todas as corretoras. O que pode mudar é se não forem as mesmas rotas, ou perguntas com dados diferentes."*

Coerente com `O-ATLAS-E-UM-SO-E-E-DE-TODAS.md`: a URA é a mesma para todas.

### 8.2 A distinção que o agente precisa fazer, e ela é a fina

```
MESMA TELA, DADOS DIFERENTES  →  ESPERADO. Não é achado.
  "Para esse CPF localizamos o serviço de CHAVEIRO RESIDENCIAL"
  "Para esse CPF localizamos o serviço de ENCANADOR"
  É a mesma tela. O que muda é a apólice do cliente.
  → a âncora casa a PARTE FIXA; a variável vira grupo de captura ou é ignorada

MESMA TELA, TEXTO FIXO DIFERENTE  →  ACHADO. Duas hipóteses:
  (a) a URA mudou de redação entre as duas datas   → R5: amplia a âncora
  (b) a seguradora trata as corretoras diferente    → PARA e pergunta ao Founder

  Como distinguir: compare as DATAS.
    · datas afastadas  → provável (a). Amplia a âncora e registra as duas
    · MESMO período e corretoras diferentes → provável (b). PARA.
```

### 8.3 O procedimento

1. O corpus é **global por seguradora+ramo** (SPEC-083 §6.2), com `company_id` como metadado.
2. Ao achar duas redações da mesma tela, o COLETOR reporta `DUAS_REDACOES` com: os dois textos, as datas, as corretoras e as contagens.
3. Datas afastadas → **R5**, amplia, e o CONTROLE do teste guarda as duas.
4. Mesmo período + corretoras diferentes → **`DIVERGENCIA_ENTRE_CORRETORAS`**, a rota **para**, e o Founder decide.

⚠️ **O agente nunca escolhe sozinho no caso (b).** Escolher errado ali significa escrever, para uma corretora, o corredor da outra.

---

## 9. OS BLOCOS DE EXECUÇÃO

### BLOCO 0 — A régua fecha a si mesma, e o corpus fica limpo

**Entregas — sete, e nenhuma exige coleta nova:**

```
1. §2.5  a marcação de zona em PYTHON (não view SQL), com:
         · `FRONTEIRAS` por seguradora, cada padrão com 📊 sessões medidas
         · as TRÊS zonas: URA · HUMANO · ORFAO
           (🔴 `CORRETORA` foi eliminada — §2.5.1.3: mascarar, não recusar)
         · `NAO_E_FRONTEIRA`, o controle negativo, e o teste que exige
           ZERO cruzamento com `FRONTEIRAS`
         · o gate de corpus com CINCO exigências, incluindo:
             ③ a PROVA DO GUARDA (semear 10 linhas humanas → vermelho)
             ④ a TRIAGEM por seguradora (📊 hoje põe porto, mapfre e
               zurich no TOPO da fila — 🔴 posição, não veredito)
             ⑤ zero ORFAO + zero identidade não mascarada
         · a CURVA de referência: Allianz limpa · sorteio SEM reposição ·
           60 reamostragens por `n` · semente `md5(session_id||rep||n)` ·
           p95=⚠️ p99=🔴 · impressa no relatório de TODA rodada
           🔴 NUNCA `ntile` (agrupa) e NUNCA o máximo (instável)
         · a métrica presa ao `_norm` (o confundidor menor)
         · 🔴 o gate ④ é TRIAGEM: ordena a fila, e a fila é o POOL INTEIRO
           pré-filtrado — 📊 698 telas de TIER 1 + amostra de 50 do TIER 2.
           🔴 NUNCA um top-15: ele leria 2,2% da porto.
           QUEM REPROVA É A LEITURA HUMANA, nunca o número
           (📊 31 pontos de dispersão entre corpora limpos; a mapfre cabe
            no p95 da tokio limpa)
         · o PRÉ-FILTRO versionado como código (`MARCAS_DE_URA`,
           `LIMITE_TIER_1`), com o controle que traz a taxa de erro dele:
           📊 53,7% de sensibilidade · 6,8% de falso positivo
           🔴 e a admissão de que a triagem NÃO prova limpeza — o JUIZ 1
           por rota é a segunda instância
         · o único uso numérico: INTRA-seguradora — ampliar a `FRONTEIRAS`
           de uma tem de DERRUBAR o hapax dela (📊 a Allianz: ~50% → 9,4%)
         · `templatize(..., corpus_de_ura=True)` — TERCEIRO MODO pelo
           `_vale_neste_modo` que já existe, NUNCA mudança global
           (📊 8 consumidores de produção, ~140 asserções, o Tecelão entre eles)
         · e os testes: `marcas_de_corretora() > 0` antes de medir · a âncora
           de senha casa · as 66 telas do §2.5.1.3 sobrevivem
2. §3.3  `medir_rota.py --exportar-arvore`, em Python, reusando o `_norm`
         e o `PADROES_DE_SERVICO` reais. Rodado de verdade, saída colada.
3. §2.2 e §4.3 refeitas com `zona='URA'` -- a ORDEM DE EXECUÇÃO da SPEC
         inteira é regerada aqui, e a versão medida substitui a provisória
4. §4.4  os CINCO itens da régua (73 + 25 = 98)
5. §4.6  a decisão `SEM_FABRICA`, com as duas leituras /90 e /100
6. §7.2 e §7.3  os seis estados de fonte e as 8 rotas indistinguíveis
7. §5.2  `--salvar-linha-de-base` e `--comparar-com`
         + a prova do comparador (regredir uma âncora e exigir exit != 0)
```

## GATE DO BLOCO 0 — duas metades, e a primeira é 100% automática

🔴 **Esta metade existe porque o gate ④ virou triagem, e triagem não é gate.**
CLAUDE.md §9: *"Gates internos são automáticos: aplicar → VERIFY → testes →
verde → avançar."* **"Alguém leu e decidiu" não é isso.**

E há algo binário aqui — só não é *"o corpus está limpo"*, que nenhuma medição
sustenta. É que **a triagem foi feita, é completa sobre a fila definida, e é
internamente consistente**:

### A · O CORPUS — cinco checagens binárias, nenhuma opinativa

```
G1 COMPLETUDE      toda fala do TIER 1 (📊 698) e da amostra do TIER 2 (50)
                   tem veredito registrado em `vereditos_de_triagem.json`
                   → len(fila) == len(vereditos)          exit != 0 se não
                   🔴 a fila vem do pré-filtro VERSIONADO (§2.5.2.1) — se ele
                     mudar, o denominador muda e o gate tem de ser refeito

G2 CONSISTÊNCIA +  toda fala com veredito GENTE é casada por algum padrão de
                   `FRONTEIRAS` ou pelo filtro ②          exit != 0 se sobrar

G3 CONSISTÊNCIA −  NENHUMA fala com veredito URA é casada por `FRONTEIRAS`
                   (é o `NAO_E_FRONTEIRA` da §2.5.1.4, generalizado à fila)

G4 QUEDA MEDIDA    toda seguradora que ganhou padrão novo tem o hapax DELA
                   antes e depois — e ele CAIU
                   📊 referência de queda real: Allianz ~50% → 9,4%
                   🔴 é INTRA-seguradora: o confundidor da diversidade cancela

G5 OS GUARDAS      ① zona · ② `^…$` · ③ prova nos DOIS sentidos (semeado
                   vermelho / Allianz limpa verde) · ⑤ zero ORFAO + zero
                   identidade não mascarada · `marcas_de_corretora() > 0`
```

> 🔴 **O que este gate AFIRMA:** a triagem está completa e coerente.
>
> 🔴 **O que ele NÃO afirma:** que o corpus está limpo. 📊 O pré-filtro tem
> sensibilidade de **53,7%** — a limpeza residual é **risco declarado**, não
> resolvido, e quem o pega é o JUIZ 1 por rota (§6.2).
>
> **Guarda que promete mais do que mede é o mesmo defeito de sempre, do outro
> lado.**

### B · A RÉGUA — o gate da SPEC-083 §4.3, inalterado

```
· `medir_rota --seguradora allianz --ramo residencial --servico maquina_de_lavar`
  roda, e a lista "O QUE FALTA PARA 95" é INTEIRAMENTE NOMEÁVEL
· a nota entra no relatório com a SAÍDA REAL colada, nas duas leituras (/90 e /100)
· o comparador de regressão fica VERMELHO com a âncora regredida de propósito
· os três juízes liberam
```

⚠️ **≥95 só vira gate depois** que os cinco itens de §4.4 fecharem. Exigi-lo antes
é exigir 98 pontos de uma soma que dá 92 — o defeito da v1.

### ⏱️ E o PASSO HUMANO, declarado com o custo

📊 **698 falas do tier 1 + 50 da amostra do tier 2 = 748 leituras, uma passada,
dez seguradoras.** 💭 A ~5 s cada, cerca de uma hora.

🔴 **Está escrito porque §9 diz que nenhum outro bloco começa antes deste** — e um
bloco bloqueante com passo humano não declarado é uma parada que ninguém orçou.

🔴 Enquanto este bloco não fechar, **nenhum outro começa** — e nenhum coletor roda
em paralelo (§5.3).

---

### BLOCO 1 — O tronco de cada seguradora

**Ordem** (💭 provisória — 📊 o BLOCO 0 a regera com `zona='URA'`, §4.3):
allianz → porto → yelum → tokio → hdi → bradesco → azul → zurich → mapfre → alfa.

⚠️ **A Allianz é a primeira e é a mais contaminada** — 📊 49,7% dos seus eventos e 81,4% das suas telas distintas estão na zona humana. Sem o BLOCO 0, é ela que quebra primeiro e pior.

**Por seguradora:**
1. Classificar as telas em tronco / galho / folha (§3.3), sobre `zona='URA'`
2. Para cada tela de tronco, na ordem de retorno (§4.3): a versão **mais recente** vira/atualiza passo
3. Replay de **todas** as rotas daquela seguradora — nenhuma perde respondidas (R3)
4. Os três juízes

**VERIFY por seguradora** — com as flags que o BLOCO 0 constrói (§5.2):
```bash
# ANTES de tocar na seguradora
python backend/scripts/medir_rota.py --todas --seguradora <SEG> \
       --salvar-linha-de-base .baseline/<SEG>-<commit>.json

# DEPOIS de cada rota
python backend/scripts/medir_rota.py --todas --seguradora <SEG> \
       --comparar-com .baseline/<SEG>-<commit>.json
# esperado: TODAS as rotas sobem ou empatam. Uma que caia = regressão, exit != 0.
```

**O que se espera medir:** 💭 o tronco é ~40% das telas de uma sessão típica. Fechá-lo deve levar as rotas daquela seguradora de "toco" para "parcial" **sem tocar em nenhuma folha**.

---

### BLOCO 2 — Os galhos (auto / residencial)

Mesmo procedimento, nas telas de `servicos = 2`.

📊 Exemplo Allianz: `Por favor, confirme o endereço` e `Agora, me confirme o número da residência` são vistas por 4 serviços — são galho residencial e valem para eletricista, encanador, eletrodoméstico e chaveiro de uma vez.

---

### BLOCO 3 — As folhas, por demanda

💭 Ordem de grandeza (a SPEC-083 §5.5 regera os números exatos):

```
chaveiro ~213 · guincho ~205 · eletricista ~176 · encanador ~152
bateria ~113 · pneu ~105 · eletrodoméstico ~105 · mecânico ~91 · vidros ~79
```

**Uma rota por vez, os sete passos de §5.1, os três juízes em cada uma.**

🔴 **Exceção obrigatória:** nas folhas de **mapfre, bradesco e zurich**, a marca de §7.3 vem **antes** da rota. 📊 São 8 rotas em que a URA dá a mesma tecla para serviços diferentes — escrever a rota do guincho ali abre o chamado da bateria, e nenhum dos três juízes tem pergunta que detecte isso.

---

### BLOCO 4 — Os serviços que existem na URA e não no código

| seguradora | ramo | serviço |
|---|---|---|
| todas | auto | **socorro mecânico** — 📊 38 sessões, e recusamos |
| yelum, hdi, porto, allianz | residencial | **ar condicionado** |
| porto | residencial | chuveiro, chaveiro, desentupimento |
| bradesco, tokio | auto | vidros |
| porto | auto | "Técnico", "Táxi" |

⚠️ Levantado por evidência textual citada, **não** por varredura sistemática. **Refazer com o corpus antes de executar.**

---

### BLOCO 5 — O inventário e as pendências

**Entrega:** `INVENTARIO-DE-ROTAS.md` regenerado · `PENDENCIAS.md` com todas as lacunas · a **lista de coleta** com o roteiro de cada rota `SEM_CORPUS`.

🔴 **`SEM_CORPUS`, não `NAO_RESPONDE`** (§7.2). Mandar para coleta uma rota cujo acervo está cheio é o erro que a SPEC-083 nomeia: 13 rotas para coleta com o material já no banco.

**O roteiro de coleta**, por rota, no formato que já funcionou com a Yelum:
1. o número da assistência da seguradora
2. o caminho de telas até o ponto desconhecido
3. 🔴 **a linha de controle**: uma segunda rodada com um serviço cujo desfecho já conhecemos, para provar que a URA não mudou entre as duas
4. o que se espera aprender

---

### BLOCO 6 — Os relatórios retroativos (opcional, decisão do Founder)

📊 Sete SPECs foram executadas sem relatório: **065, 069, 070, 071, 072, 076, 081**. Cada uma pode ter deixado trabalho pela metade que ninguém registrou.

Entrega: um relatório por SPEC, a partir do diff dos commits dela, com o que foi feito e o que ficou de fora.

⚠️ Bloco separado e **último** de propósito: é dívida documental, não é rota. Se o tempo apertar, ele é o que se corta — e cortá-lo fica **registrado**, não silencioso.

🔴 **E ele entra em `PENDENCIAS.md` no dia em que esta SPEC começar**, com dono e com o que destrava (CLAUDE.md §11.1) — não fica dependendo de sobrar tempo no fim. Dívida que só existe dentro de um bloco cortável é dívida que some quando o bloco é cortado.

---

## 10. RISCOS

| risco | fechamento |
|---|---|
| 🔴 **O corpus mistura tela de URA com fala de gente** | §2.5: `FRONTEIRAS` **por seguradora** + as 4 zonas + o gate de 5 exigências, com o ③ (semear humano → vermelho) e o ④ (controle por seguradora, 📊 reprova 4 das 10 hoje). Sem isso são 472 reprovações insanáveis só na Allianz — e nove seguradoras com selo falso |
| **Consertar o tronco quebra rota que estava boa** | R3 + `--salvar-linha-de-base` / `--comparar-com` (§5.2), construídos no BLOCO 0 — e o comparador é **provado regredindo uma âncora de propósito** |
| **O executor declara pronto sem o juiz** | A liberação é do juiz, e o inventário só aceita rota com os três vistos |
| **O laço não converge e trava a fábrica** | Teto de 3 voltas → `PRECISA_DE_HUMANO` com dossiê |
| **Escrever passo sem evidência** | ① do processo: zero telas com `zona='URA'` → PARA. E o juiz CÉTICO confere a transcrição contra a sessão citada |
| **Família de passos: mexer num muda dois corredores** | Coluna FAMÍLIA no inventário + o replay de regressão pega |
| **Duas corretoras divergem e o agente escolhe** | §8.3: no caso (b) a rota PARA e o Founder decide |
| **A ordem por profundidade atrasa a rota de maior demanda** | É deliberado: 📊 `chaveiro` é folha de 10 seguradoras; sem o tronco de cada uma, ela não fecha em nenhuma |
| **O corpus envelhece durante a execução** | O acervo é vivo (📊 +2 eventos em 28 h). Cada rota registra a data do corpus que usou; o inventário traz o carimbo |

---

## 11. RELATÓRIO FINAL

Além do template padrão:

- a **árvore medida** de cada seguradora (tronco / galho / folha, com as contagens)
- por rota: a nota **antes e depois**, as sessões usadas, e os três vistos dos juízes
- as rotas que bateram o teto de 3 voltas, com o dossiê
- as rotas `PARCIAL`, com a tela onde a evidência acabou
- os casos `DIVERGENCIA_ENTRE_CORRETORAS`, com a decisão do Founder
- o replay de regressão de **todas** as seguradoras tocadas
- a lista de coleta final
- declaração de que nenhuma rota foi liberada sem os três juízes
