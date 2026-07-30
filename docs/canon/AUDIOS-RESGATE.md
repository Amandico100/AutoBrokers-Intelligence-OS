# Resgate dos áudios — o que aconteceu e o que fazer

> **Para quem pegar esta tarefa amanhã (31/07/2026) ou depois.**
> Situação apurada em 30/07/2026. Contexto completo em `ESTADO-DA-CAMPANHA.md` §22.

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

## 3. O caminho A — reconexão (tentar primeiro, custa nada)

Quando o WhatsApp reconecta, ele **re-entrega histórico**. Com a correção no ar,
as coordenadas dos áudios que **ainda estiverem nos servidores do WhatsApp** são
gravadas, e aí dá para transcrever.

**Quantos sobrevivem é desconhecido** — o WhatsApp poda mídia antiga e a retenção
não é publicada. Pode ser nenhum; podem ser os dos últimos meses.

**Como verificar depois de reconectar:**

```sql
select count(*) filter (where media_meta ? 'mediaKey') as recuperaveis,
       count(*) as total
from attendance_transcripts where msg_type='audio';
```

Se `recuperaveis > 0`, siga para o §5 (transcrição).

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
