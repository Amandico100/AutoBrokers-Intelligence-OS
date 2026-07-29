# ESTADO DA CAMPANHA — passagem de bastão

> **Se você é um chat novo:** leia este arquivo inteiro antes de qualquer coisa,
> depois `CLAUDE.md` e `docs/canon/CURADORIA-POR-SUBAGENTES.md`. Este arquivo diz
> **onde paramos**; os outros dizem **como se trabalha aqui**.

**Atualizado em 29/07/2026, 21h** · commit `60bcca1` + os desta sessão

---

## 1. O que estamos fazendo agora, em uma frase

A destilação do histórico de duas corretoras está sendo feita por **subagentes
Opus 5 pelo plano Max**, e não pela API — porque por API custaria ~US$ 80 e o
projeto tem US$ 6.

Isso é **temporário**. Quando Resulta e AutoFleet estiverem prontas, a Central
de Agentes volta a fazer o trabalho corrente, com Batch API a 50% de desconto.

---

## 2. Estado dos números (29/07, 21h)

```
RESULTA      7.733 sessoes · ~2.900 destiladas
AUTOFLEET      705 sessoes ·    173 destiladas
CARTAS       ~3.200 no RAG · marca `destilacao_max_29_07_2026` nas novas
ATLAS        10 mapas tecidos · 456 sessoes de seguradora · 17.488 eventos
API          US$ 0,00 gasto pelos subagentes hoje
TESTES       97 suites verdes
```

**Lotes em disco** (gitignored, reexportados limpos às 20h):
`backend/scripts/destilacao_max/lotes/` (52 lotes, Resulta) e
`lotes_autofleet/` (10 lotes). Os `.destilado.jsonl` já aplicados podem ser
reconhecidos por `aplicar.py` devolver "0 sessões".

---

## 3. O fluxo, em quatro comandos

```bash
cd backend
# 1. exportar (mascara com as funcoes de producao; custo zero)
python scripts/destilacao_max/exportar.py --lotes 60 --por-lote 100 \
       --empresa <company_id> --saida scripts/destilacao_max/lotes
# 2. destilar: um subagente Opus 5 por lote, 2 lotes por agente, 2-4 em paralelo
#    Prompt: ler BRIEFING-SUBAGENTE.md, destilar, gravar .destilado.jsonl, PARAR
# 3. gravar (nao e o subagente que grava — foi o que cortou 60% dos tokens)
python scripts/destilacao_max/aplicar.py scripts/.../lote_00X.destilado.jsonl
# 4. publicar: nao faca nada. O publicador de `distill_once` leva ao RAG.
```

`company_id`: Resulta `04b5cdbc-04cd-4ddf-8e4b-f43efb062fab` ·
AutoFleet `6c9c55e2-2f30-4ca2-a1ef-4ef464ed1b4a`

---

## 4. AS PEGADINHAS — leia antes de mexer em qualquer coisa

### 4.1 Nunca reaplique `templatize` num transcript montado

`cliente` está na lista de rótulos do `_LABELED_VALUE` e a regra é ancorada em
início de linha. `CLIENTE: meu vidro trincou` casa como "rótulo: valor" e a fala
inteira do segurado vira `{VALOR}`.

**Eu fiz isso três vezes em 29/07** ao reaplicar o mascarador nos lotes
pendentes depois de cada conserto de PII. Apaguei a fala do cliente em 278
sessões. Use `mascarar.remascarar()`, que desmonta a linha primeiro — ou
simplesmente reexporte do banco. Ver `test_remascarar_nao_apaga_o_cliente.py`.

### 4.2 O teto de gasto é 0 por padrão, e isso é de propósito

`DESTILADOR_TETO_POR_RODADA=0` → nenhuma chamada de modelo em `distill_once`.
O botão "Processar aprendizado" **não** processa um lote: processa até a fila
secar ou o crédito acabar. Foi assim que US$ 6 sumiram numa rodada.

O teto **não** desliga curar e publicar — é por ali que as cartas dos
subagentes chegam ao RAG. Não use `_env_int` para lê-lo: aquele faz `max(1,...)`
e transformaria o teto travado em uma conversa + um playbook no modelo caro.

### 4.3 PostgREST corta em 1.000 linhas e não avisa

Toda consulta que possa passar de mil linhas precisa paginar com `.range()`.
Foi essa mudez que construiu o mapa da Allianz sobre 40% do material.

### 4.4 `hash()` de string em Python é aleatório por processo

Não use para `on_conflict` nem para id estável. Use `hashlib`.

### 4.5 Claude Opus 5 e Sonnet 5 PENSAM por padrão

O LangChain devolve `content` como lista de blocos. `str()` numa lista dá a
repr, e o leitor de JSON falha. Use `_texto_da_resposta()`. Isto custou US$ 15
em chamadas repetidas antes de ser achado.

### 4.6 Deploy sai da `main`

O EasyPanel constrói a `main`. Commit em feature branch não chega em produção:
`git push origin HEAD:main`.

### 4.7 Uma sessão que falha três vezes sai da fila

`summary.distill_falhas >= 3` → parada. Sem isso a mesma sessão é cobrada em
toda rodada, para sempre, em silêncio.

---

## 5. Regras do Founder que não se negociam

- **Nenhuma mensagem pode ser perdida ou apagada do WhatsApp da Resulta.**
- **Nunca analisar as 9.565 mídias por API.** Só as 20 autorizadas.
- **Áudio liberado para transcrição, desde que não seja por API** — hoje isso
  significa: não é possível. Claude não recebe áudio aqui, e Whisper é API.
  A conta honesta está na §7.
- Menu não cresce: coisa nova vai dentro de item existente.
- Se um teste com dado real revelar defeito no seu código, corrija o código.
- Nunca criar motor paralelo (CLAUDE.md §5). Consolidar antes de duplicar.
- Separe **FATO**, **INFERÊNCIA** e **RECOMENDAÇÃO** em todo relatório.
- Em 29/07 o Founder afastou o excesso de zelo com LGPD: *"estamos num projeto
  controlado só na minha máquina e sem clientes"*. O portão de PII continua
  valendo, mas **não bloqueie trabalho por causa dele** — o que não pode é
  perder conversa.

---

## 6. Pendências abertas

| # | O quê | Estado |
|---|---|---|
| 1 | **Telas quase-duplicadas no Atlas** | achado, não corrigido — §7 |
| 2 | Destilar o resto: ~4.800 Resulta + ~530 AutoFleet | em andamento |
| 3 | WhatsApps desconectados desde 18:49 de 29/07 | esperando repareamento |
| 4 | 50 sessões abertas não fecham → não destilam | investigar |
| 5 | Playbooks de conduta: 3 existem, faltam os demais | precisa teto > 0 |
| 6 | Validar os 3% da AutoFleet pelo caminho automático | `TETO=20`, ~US$ 0,13 |
| 7 | `isForwarded` não é persistido → conduta trocada (CA-021) | registrado |
| 8 | 45 chaves de seguradora distintas, com sujeira antiga | limpeza pendente |
| 9 | Áudio: conhecimento falado que não fica registrado | decisão do Founder |
| 10 | Relatório consolidado de condutas de risco observadas | ~7 ocorrências |

---

## 7. A auditoria do Atlas de 29/07 — o que foi verificado

**FATO — a AutoFleet FOI processada.** A hipótese de que o tecelão ignorou as
conversas novas porque já existia mapa está **errada**, e a prova é o volume:

```
                telas de URA        eventos
                ontem → hoje        ontem → hoje
Allianz          221 → 326          5.330 → 6.746
Yelum            179 → 492            546 → 3.026
Porto            298 → 686          1.019 → 2.883
HDI              229 → 387            884 → 1.965
Zurich            39 → 115             94 →   379
Tokio             40 →  54            138 →   178
```

Mais: **456 sessões de seguradora no banco = 456 contadas nos mapas.** Zero
eventos sem seguradora. Zero seguradoras sem mapa. Nada foi deixado de lado.

**FATO — por que a cobertura da Allianz ficou em 63%.** Cobertura é
`opções percorridas / opções descobertas` = 435/687. A AutoFleet descobriu
opções novas (denominador subiu) e percorreu parte delas (numerador subiu), na
mesma proporção. Em número absoluto a Allianz passou de ~140 para **435 opções
percorridas**. Percentual estável com mapa maior é mais território conhecido,
não estagnação.

**INFERÊNCIA — o defeito real é inflação de telas.**

```
Porto     686 telas de URA · 1.292 opções
Yelum     492 telas
HDI       387 telas
Allianz   326 telas de URA + 924 nós de conversa humana
```

Uma URA de seguradora tem 30 a 80 telas. 686 é a mesma tela contada muitas
vezes, porque algo dentro dela varia — protocolo, nome, saudação com hora. Já
consertamos parte disso em 28/07 (mascarar `Assistência: 8923467` derrubou 18
nós da Yelum para 1), mas sobrou muito.

Três consequências concretas:
1. a cobertura parece baixa porque o denominador está inflado;
2. o Canvas fica ilegível;
3. **o agente não acha a rota certa** — é a pior das três.

**FALSO ALARME que eu mesmo levantei e descartei:** achei que `edges` apontava
para nós inexistentes (977 chaves órfãs na Porto). A chave de `edges` é
`nó|opção`, então o número maior é esperado. Não é defeito.

**A INVESTIGAR:** Tokio tem 36 sessões e só 178 eventos — 5 por sessão. Ou as
conversas são curtíssimas, ou algo corta antes do fim.

**Sobre áudio, a conta honesta:** transcrever exige API. Claude não recebe áudio
neste ambiente. Whisper custa US$ 0,006/min — se a média for 30s, são US$ 0,003
por áudio. Não é os US$ 80 que o Founder teme; é da ordem de **US$ 10 a US$ 15
por milhares de áudios**. É decisão dele, com o número na mão. Imagem é outra
conversa: descrever foto de para-choque não ensina processo.

---

## 8. A próxima auditoria recomendada

**Assinatura de tela.** Medir quantas das 686 telas da Porto são a mesma tela e
endurecer a assinatura no `cartographer`. É a auditoria que destrava a cobertura
real de todas as seguradoras de uma vez — e é a que mais importa para o
atendimento, porque cobertura inflada esconde rota que o agente precisa achar.

Método: agrupar nós por conjunto de opções normalizado, não pelo texto inteiro
da tela. Duas telas com as mesmas opções na mesma ordem são a mesma tela, ainda
que o cabeçalho traga um protocolo diferente.
