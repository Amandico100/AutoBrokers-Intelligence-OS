# Resgate dos áudios — o que aconteceu e o que fazer

> **Situação apurada em 30/07/2026 · ATUALIZADA em 04/08/2026** com o resultado
> do primeiro teste real do "caminho A". Contexto em `ESTADO-DA-CAMPANHA.md` §22.
>
> ⚠️ **Leia o §0 antes do resto.** O caminho A foi testado, e ele **não basta
> sozinho** — por um motivo que ninguém tinha medido.

---

## 0. O QUE MUDOU EM 04/08/2026 — leia isto primeiro

### 0.0 Quinze leitores independentes disseram que o áudio é o buraco

> 📊 Acrescentado em 04/08/2026, depois da noite da destilação. Relatório completo
> em [`reports/A-NOITE-DA-DESTILACAO-04-08-2026.md`](reports/A-NOITE-DA-DESTILACAO-04-08-2026.md).

Vinte e sete destiladores leram **1.784 conversas** em pacotes diferentes, sem se
falarem. **Quinze deles** relataram, por conta própria, a mesma coisa: entre 12 e 20
conversas de cada 70 têm a resposta decisiva em `[audio]`, com só o *"ok, entendi"*
chegando ao texto.

E um deles formulou o padrão melhor que os outros:

> **"Quanto mais resolutivo o atendimento, mais ele acontece em áudio."**

A pergunta do segurado fica escrita. A explicação da atendente — que é a carta —
vira `[audio]`. **O acervo guarda sistematicamente a dúvida e perde a resposta.**

Exemplos medidos: *"troca de vidro precisa de BO?"* apareceu duas vezes e foi
respondida por áudio nas duas. Uma pergunta sobre assistência residencial dentro de
assistência auto ficou sem resposta nenhuma no transcript. Vários destiladores
escreveram a mesma recomendação, sem combinarem: *"transcrever áudio rende mais
cartas do que processar outro pacote inteiro de texto."*

**Consequência que muda a prioridade:** enquanto o resgate parecia salvar arquivos,
ele era uma dívida de completude. Agora está medido que ele salva **a melhor parte
do conhecimento** — justamente a que o acervo mais precisa e a única que não dá para
recuperar de outro jeito. É a pendência de maior retorno medido do produto.

### 0.1 O caminho A foi testado. Funciona pela metade.

📊 A AutoFleet repareou em 04/08 às 18:39 e o `history_sync` reentregou tudo
(20.338 transcrições, terminou às 19:05). O resultado, medido:

```
6.284 áudios no banco
2.630 com directPath + mediaKey          ← a correção de 30/07 FUNCIONOU
    0 com fileEncSha256                  ← 🔴
    0 com fileSha256                     ← 🔴
    0 arquivados                         ← consequência
```

🔴 A coordenada gravada é **parcial**.

> **Repescar áudio do banco é impossível.** Não é lentidão nem falta de
> autorização: os dados que estão lá não bastam, e nunca vão bastar.

### 0.1.1 ⚠️ CORREÇÃO de 05/08/2026 — a conclusão estava certa, a razão não

Este parágrafo afirmava, até hoje, que *"sem os dois hashes não há como
decifrar"*. **Está errado**, e razão errada leva ao conserto errado depois.

📊 Lido na fonte (`whatsmeow/download.go:290,310`): a chave de decifração sai
**só do `mediaKey`**, por HKDF. Os SHA256 são outra coisa: `fileEncSHA256` é o
parâmetro `hash=` da URL do CDN, e `fileSHA256` é a conferência de integridade
do arquivo já baixado.

**A conclusão prática não muda, e por um motivo diferente:** `download.go:249`
e `:304` transformam um `fileSHA256` ausente em 32 bytes zerados, e a
comparação então **sempre falha** com `ErrInvalidMediaSHA256`. Os 2.654 áudios
já gravados continuam irrecuperáveis — não porque falte a chave, mas porque
falta o que prova que o arquivo chegou inteiro.

E a **causa** de os hashes não estarem no banco não era o Go omitindo: era o
nosso extrator pedindo o nome errado. Ver §0.1.2.

### 0.1.2 A causa raiz: a caixa alta de uma letra

📊 05/08/2026. O Evolution GO serializa o evento com `json.Marshal` do struct
do whatsmeow, **não com protojson**. As chaves do webhook são as tags json —
os nomes do proto, com o acrônimo em MAIÚSCULA:

```
o fio manda        fileSHA256 · fileEncSHA256 · URL
nós pedíamos       fileSha256 · fileEncSha256 · url
```

**A linha de controle**, sobre 2.655 áudios do acervo:

```
grafia IGUAL à nossa     directPath 2.654 · mediaKey 2.654 · mediaKeyTimestamp 2.655
grafia DIFERENTE         fileSha256 0 · url 0
```

Um fator — a caixa das letras — e seis resultados. E o serializador está
**provado, não suposto**: `mediaKeyTimestamp` chega como **número** JSON, e
protojson emitiria `int64` como string.

> **É a segunda vez.** `selectedButtonId` × `selectedButtonID` já apagou 98,9%
> dos cliques na leitura, neste repositório, pelo mesmo serializador. A lição
> que fica: **quem serializa o protobuf escolhe a caixa das letras e não
> avisa** — então a leitura tem de casar por grafia normalizada, nunca por
> nome exato.

Consertado em `observer_intake.py`, com teste
(`test_a_caixa_alta_do_acronimo_nao_apaga_audio.py`) que inclui a linha de
controle provando que a grafia antiga **perdia** o payload do Go.

**O conserto salva o futuro, não repesca o passado.**

E o próprio `history_ingest.py` já dizia isso, em comentário, desde antes:

> *"A mídia antiga SÓ EXISTE AQUI, NESTE INSTANTE. (…) Uma foto do histórico,
> depois que esta função retorna, é inalcançável para sempre."*

### 0.2 Havia um segundo motivo, e era pior

📊 O portão do orçamento estava no **enfileiramento**, não na transcrição. O
comentário do código prometia que *"sem orçamento a mídia só é ARQUIVADA — ela
não se perde"*. **Não era verdade:** sem orçamento nada era baixado, então nada
era arquivado.

**Consertado em 04/08.** As duas contas nunca foram a mesma:

```
baixar + arquivar   custo ZERO — bytes do WhatsApp pela sessão já pareada,
                    guardados no MinIO do próprio servidor (não toca o Supabase)
transcrever         Whisper cobra por minuto — só isto pede orçamento
```

E nasceu o estado `arquivado` (salvo, sem leitura), para dar como achar depois o
que ainda falta transcrever.

### 0.3 Só áudio desce, por decisão do Founder

📊 Volume medido em 04/08, do que ainda é recuperável:

| tipo | arquivos | tamanho |
|---|---:|---:|
| **áudio** | **1.623** | **80 MB** |
| documento | 292 | 165 MB |
| imagem | 792 | 106 MB |
| vídeo | 29 | 106 MB |
| sticker | 108 | 30 MB |

`OBSERVER_MEDIA_KINDS` (padrão `audio`) corta **84% dos bytes e 43% dos
arquivos**. Menos tráfego pela sessão é menos risco de o número ser marcado como
anômalo — e o áudio é onde o segurado explica o caso; foto de documento e PDF de
apólice a InfoCap já tem estruturado.

### 0.4 O guarda contra bloqueio do número

`_load_integration_sync` conferia se o canal estava ativo **só no caminho de
fallback**; o caminho normal (por `integration_id`) não conferia nada. Baixar em
rajada por sessão que cai e volta é exatamente o padrão que faz o WhatsApp
desconfiar. Agora recusa canal fora do ar e **levanta** — o item volta para a
fila em vez de ser marcado como visto sem ter baixado.

📊 Ritmo: 3 arquivos a cada 10s = **18/min**. Para os 1.623 áudios, ~90 min.

### 0.5 O caminho que sobrou, e a decisão do Founder

**Para os áudios da AutoFleet existe UM caminho: reparear de novo, agora com o
conserto no ar.** O `history_sync` reentrega as mensagens cruas, e desta vez a
mídia é enfileirada e baixada.

📊 E o texto não duplica — provado no ar em 04/08: **1 duplicata em 13.481
linhas** depois do repareamento.

**Decisão do Founder em 04/08:** *"não faz mal agora essa questão dos áudios.
Continuam no celular dela. Não vou pedir agora para ela reparear. Isso fica como
tarefa pendente mais pra frente, porque os áudios são na verdade cartas pro RAG e
podemos criar elas com os áudios depois. Quero a destilação apenas das conversas
em texto agora."*

> **Portanto: a destilação de TEXTO acontece primeiro e não espera áudio.**
> O áudio entra numa segunda leva, depois de um repareamento combinado.

### 0.6 O que a destilação custou, medido

📊 Consumo de crédito Claude do sistema inteiro, por dia:

```
29/07   US$ 10,10  em 1.702 chamadas   ← a destilação
28/07   US$  1,06  em 2.593 chamadas
resto   US$  0,43
                    TOTAL US$ 11,59
```

Isso produziu **9.699 cartas** de **8.872 sessões** — ou seja:

> 📊 **≈ US$ 0,0012 por carta.** A destilação é barata; o que ela precisa é de
> material e de alguém olhando o resultado.

⚠️ **E o crédito acabou.** A próxima leva precisa de saldo novo. Ver §5 para o
custo da transcrição, que é a parte que este documento sempre tratou como paga.

---

## 1. O que aconteceu, em uma frase

**A captura guardava a ficha do áudio e jogava fora o áudio.**

```
3.653 áudios registrados nas duas corretoras
        0 com bytes guardados
        0 com chave de download (mediaKey, directPath, url)
       26 presos em `enrichment_status = pending`
       11 com `failed` / HTTPStatusError
```

`media_meta` guardava `kind`, `mimetype`, `bytes`, `segundos`, `caption`,
`filename` — e **descartava `mediaKey` e `directPath`**, que são o que o WhatsApp
manda para permitir buscar e descriptografar a mídia depois.

O worker (`app/services/atlas/observer_media.py`) recebia o payload inteiro pela
fila do Redis e **funcionava** — enquanto a fila existisse. `QUEUE_TTL_SECONDS =
3 * 24 * 3600`: **três dias.** Depois disso, a única cópia das coordenadas tinha
evaporado e ninguém no sistema sabia mais onde estava o áudio.

**Ninguém errou.** Um sistema que funciona por 72 horas e depois apaga em
silêncio é pior que um que falha na cara, porque ninguém vai olhar.

---

## 2. O que já foi consertado (commit em `main`, 30/07)

`app/services/atlas/observer_intake.py`:

- **`COORDENADAS_DE_MIDIA`** — constante única com `directPath`, `mediaKey`,
  `fileEncSha256`, `fileSha256`, `mediaKeyTimestamp`, `url`. A captura agora
  grava todas.
- **`sem_coordenadas()`** — troca esses campos por `download: recuperavel` /
  `sem coordenadas`. Usado por `admin_atlas.py::observer_report`, que devolvia
  `media_meta` cru e passaria a exibir a chave numa resposta HTTP.

**A tensão que isto resolve:** `mediaKey` **é** chave de descriptografia. Precisa
existir no banco para a mídia ser recuperável e **não pode** sair em resposta de
API (CLAUDE.md §13.3). Lista única lida pelo gravador **e** pelo escondedor —
duas listas paralelas significariam que acrescentar uma chave ao gravador e
esquecer do escondedor publica um segredo sem ninguém perceber.

Teste: `tests/test_audio_nao_pode_sumir.py` (5 blocos, verde).

**Deploy feito em 30/07.** Ou seja: **a partir de agora, áudio novo é
recuperável.**

---

## 3. O caminho A — reconexão · ⚠️ TESTADO EM 04/08, E A CONCLUSÃO MUDOU

> **Esta seção descrevia a esperança. O §0 descreve o resultado.** Fica aqui
> porque a hipótese era razoável e a diferença entre ela e o que aconteceu é o
> que ensina — não porque ainda vale como instrução.

**A hipótese era:** reconectar re-entrega o histórico; com a correção no ar, as
coordenadas são gravadas e dá para transcrever.

📊 **O que de fato aconteceu (AutoFleet, 04/08):** as coordenadas **foram**
gravadas — 2.630 áudios com `directPath` + `mediaKey`. A correção de 30/07
funcionou.

🔴 **E mesmo assim nada foi baixado**, por dois motivos que a hipótese não
previa:

1. **A coordenada é parcial.** 0 áudios têm `fileEncSha256`/`fileSha256`, e o
   `/message/downloadmedia` exige o `waE2E.Message` inteiro. Ver §0.1.
2. **O portão do orçamento estava no enfileiramento**, então a mídia nem entrava
   na fila. Ver §0.2 — consertado em 04/08.

**A consulta de verificação continua útil, mas a leitura dela mudou:**

```sql
select count(*) filter (where media_meta ? 'mediaKey')        as com_coordenada,
       count(*) filter (where media_meta ? 'fileEncSha256')   as com_hash,
       count(*) filter (where media_meta ? 'private_object')  as ARQUIVADO,
       count(*)                                               as total
from attendance_transcripts where msg_type='audio';
```

> **A coluna que importa é `ARQUIVADO`.** `com_coordenada > 0` só diz que a
> ficha foi guardada; foi exatamente isso que confundiu a leitura em 30/07.

**O caminho real, hoje:** reparear COM o conserto de 04/08 no ar. Aí a mídia é
enfileirada no instante da reentrega — que é o único instante em que ela existe.

**A lição que fica, e é a mesma do §6 noutra roupa:** *"tem coordenada"* não é
*"dá para baixar"*. Um dado meio guardado parece guardado.

---

## 4. O caminho B — pedir às atendentes (se o A não trouxer)

### Os áudios que mais valem, em ordem

| corretora | contato | quando | áudios | duração | o que é |
|---|---|---|---|---|---|
| AutoFleet | `211462781935860` (grupo/LID) | **16/07/2026** | 22 recebidos + 8 enviados | **27 min**, um deles de **23 min** | conversa inteira num único dia com marcadores de "passo a passo"; **o alvo principal** |
| AutoFleet | `110681340772419` (grupo/LID) | **28/07/2026** | 1 | 2min15 | ao lado do texto que explica o caminho da Bradesco por telefone e pelo corretor online |
| Resulta | `554796274743` | **29/07/2026** | 7 enviados | 5min15 | mais recente da Resulta com marcador de ensino |
| AutoFleet | `554899694442` | **30/06/2026** | 2 enviados + 4 recebidos | 3min | |
| AutoFleet | `554891314384` | 25/11/25 a 25/06/26 | 10 enviados | 1min23 | disperso, menor prioridade |

**A conversa de 16/07/2026 é a prioridade absoluta.** Trinta áudios, um único
dia, uma única conversa, quase meia hora de fala, com marcadores textuais de
ensino ("Ouvindo", "Mando sim") — é o formato exato de uma sessão de treinamento.

### O jeito mais fácil de as atendentes enviarem

**Não peça arquivo por arquivo.** O WhatsApp tem exportação nativa que leva a
mídia junto:

```
1. Abrir a conversa no WhatsApp (celular)
2. Tocar no nome do contato/grupo no topo
3. Rolar até "Exportar conversa"
4. Escolher **"Incluir mídia"**   ← ESSENCIAL
5. Enviar o .zip por e-mail
```

**Limite conhecido:** com mídia, a exportação leva as ~10.000 mensagens mais
recentes e o zip pode ficar grande. Para a conversa de 16/07 isso não é problema.

**Alternativa se a exportação falhar:** encaminhar os áudios para um contato só
(um número da empresa, ou "Mensagens salvas"), num único bloco. Encaminhar
preserva o áudio; captura de tela não serve.

**O que pedir, literalmente:**

> "Preciso da conversa do dia 16/07 com [contato], exportada **com mídia**.
> No WhatsApp: abrir a conversa → tocar no nome no topo → Exportar conversa →
> Incluir mídia → mandar o arquivo por e-mail."

### Onde colocar o que chegar

`backend/scripts/destilacao_max/audios/` (criar; já está no `.gitignore` por
estar sob `scripts/destilacao_max/` — **conferir antes de commitar**).

---

## 5. Transcrição — como fazer quando houver áudio

**Whisper (`whisper-1`), US$ 0,006/min.** É o certo: transcrição é tarefa
mecânica, e pagar modelo de raciocínio para isso seria o mesmo erro que já
consertamos quando os subagentes pararam de gerar SQL.

```
regra de seleção .... só ÁUDIO DE ATENDENTE (`direction='out'`) com
                      `segundos >= 30`. Áudio de cliente RELATA; áudio de
                      atendente ENSINA.
custo estimado ...... US$ 2,00 a 2,50 para ~300 áudios
teto ................ o Founder liberou US$ 5,75; ideal não passar de US$ 3
```

> ⚠️ **ATUALIZAÇÃO 04/08/2026 — o teto acima não existe mais.**
>
> 📊 O crédito da API Claude **acabou**: US$ 11,59 consumidos, 87% deles num
> único dia (29/07, a destilação). Ver §0.6.
>
> E o teto de áudio do worker é **3 minutos** (`MEDIA_MAX_AUDIO_SECONDS=180`,
> ≈ US$ 0,018 por áudio). Acima disso o áudio é arquivado sem transcrição —
> visível, recuperável, e não vira conta. 🔴 Isso significa que o áudio de
> **23 minutos** da conversa de 16/07 (o alvo principal do §4) **não seria
> transcrito pelo caminho automático**. Ele precisa de decisão à parte: ou o
> teto sobe só para ele (~US$ 0,14), ou vai por transcrição manual.
>
> **Ordem que vale agora, por decisão do Founder:** destilar o TEXTO primeiro,
> sem esperar áudio. O áudio é uma segunda leva, com repareamento combinado e
> saldo novo.

**A destilação continua de graça** — Whisper vira texto, e daí em diante é o
mesmo pipeline de subagentes pelo plano Max. **A API paga a transcrição, nunca o
raciocínio.**

Depois de transcrito, o texto entra pelo caminho já existente: escrever no campo
`text` da mensagem (ou num lote `.jsonl` de conversas) e destilar com o
`BRIEFING-SUBAGENTE.md`.

**Atenção de PII:** a transcrição precisa passar pelo `remascarar()` de
`scripts/destilacao_max/mascarar.py` antes de ir para qualquer subagente —
áudio de atendente diz nome, CPF e placa em voz alta com a mesma frequência que
o texto.

---

## 6. O que este episódio ensina, e vale além do áudio

**Nenhum dado essencial pode existir em cópia única e transitória.**

A fila do Redis era a única cópia das coordenadas. Funcionava. Expirava em três
dias. Ninguém notou por meses, porque o sistema não reclamava — ele só esquecia.

Vale procurar outros lugares onde a mesma forma aparece: algo importante que só
existe em Redis, em cache, em variável de processo, ou em fila com TTL.
