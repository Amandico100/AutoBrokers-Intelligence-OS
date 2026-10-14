modelo: claude-opus-5-5

# CONFIRMAÇÃO do conserto da SPEC-132-A

> Juiz novo, cego para o builder. Pergunta única: **o conserto fechou os blockers e criou defeito novo?**
> Branch `spec/132-o-chat-e-a-cotacao` · conserto = `96a3c44..48663df` (`fix(spec-132-A conserto)`) + `bdfdfd0` (`build(spec-132-A)`) · 14/10/2026.

## Veredito

**FECHADOS 4/4 · DEFEITO NOVO: nenhum que mude byte para segurado, corretora, banco ou segurança · NOTA 86.**

## Os quatro blockers

| # | blocker | onde fechou | evidência |
|---|---|---|---|
| B1 | célula de planilha cortada ANTES da máscara | `chat_anexos.py` `_celula_md`: >80 chars → `_mascarar` na célula inteira, corte depois; máscara indisponível → `[texto omitido]` (fail-closed) | 📊 sonda `conf132a/sondas.py` (venv do backend, 14/10): CPF `529.982.247-25` começando nas posições 60/66/70/72/75 → saída `…[CPF]…`, **0** sequências de dígitos. Controle: na posição 66 o corte antigo `cel[:77]` deixava `529.982.247` (9 dígitos-base). CSV de 5 linhas com o mesmo caso → 0 dígitos no bruto. |
| B2 | memória/tempo sem teto (CSV/xlsx/imagem inflados, poço de threads) | leitura em FLUXO (`_uma_aba` + `_Coluna`), `COLUNAS_LIDAS=200`, `CELULAS_POR_ARQUIVO=200k`, linha de CSV cortada em 64 KiB antes do parser, `_conferir_o_pacote` (teto descomprimido + razão), varredura do XML da aba que recusa linha com >20.000 `<c>`, `PIXELS_MAXIMOS` pelo cabeçalho + `draft` no JPEG + `thumbnail` antes do `exif_transpose`, poço próprio de 3 threads (`_no_poco`), prazo cooperativo a cada 256 linhas | 📊 sonda: 60×30 células longas (670 KB) → 0,78 s, 0 dígitos. PNG RGBA 3000×2000 → JPEG 2048×1365 (o caminho normal continua); JPEG 4000×3000 → 2048×1536; **JPEG com EXIF orientação 6 → 1536×2048** (a rotação continua certa depois da troca de ordem thumbnail→transpose). Os testes `test_conserto_b2_*` estão no lote `p3` da bateria do gerente. |
| P1 | mesmo `client_request_id` 2× → modelo 2× | `chat.py` `_ReservaDoTurno`: reserva gravada em `TURNOS_ATIVOS` logo após a conferência, sem `await` no meio (`chat.py:926-938`); solta no `finally` do invólucro `chat_stream` só se ainda for a SUA reserva (`chat.py:829-832`); teto de 429 desconta a própria reserva (`chat.py:1464`); Stop que chega na reserva → task nasce cancelada (`chat.py:1799-1800`) | leitura: o único consumidor externo de `TURNOS_ATIVOS` é `chat_stop` (`.cancel()` — a reserva o tem). `grep TURNOS_ATIVOS backend/app` → só `chat.py`. Só `modo == "painel"` reserva: o widget não muda. Teste `test_conserto_p1_*` no lote `p3`. |
| RT-P1 | aquecimento derrubando o app com `SystemExit` | `main.py:82-87`: `CancelledError` sobe, `BaseException` vira aviso; `presidio_service.py`: `except (Exception, SystemExit)` no carregamento do pt e na init; `Dockerfile` instala `pt_core_news_md` na imagem | leitura do diff; teste `test_conserto_rt_p1_*` no lote `p3`. ⚠️ não rodei `rt132a/aquece.py` (trava ocupada pela bateria). |

## Regressão — o que se pediu para olhar

- **Atendimento ao segurado / widget:** o conserto não toca webhook nem `atalho/`. Em `chat.py` a reserva só existe em `modo == "painel"`. O Presidio (usado pelo `guardrails.py:359`, que atende todo mundo) só muda no caminho de FALHA: com os modelos presentes, o caminho é o mesmo de antes. O poço novo é separado do `EXECUTOR_THREADS`. **Sem regressão encontrada.**
- **Presidio sem o modelo pt:** o fallback é o mesmo de antes do conserto (`AnalyzerEngine()` padrão). O que muda: `SystemExit` não mata mais o processo, e `PRESIDIO_BAIXAR_MODELO=0` proíbe o download. ⚠️ Se a `analyze(language='pt')` funciona com o motor padrão é uma questão que já existia antes do conserto; não medi (precisaria carregar o spaCy `en_core_web_lg` com a bateria rodando). A máscara dos ANEXOS não depende do Presidio: `vision_service.mascarar` → `mascarar_texto_de_apolice` (regex).
- **SSRF do `fileUrl`:** 📊 sonda P5: a URL `SUPABASE_URL + /storage/v1/object/public/…` → baixou (1 pedido); `https://169.254.169.254/…` → `None`; `http://` no host certo → `None`. Caminho legítimo intacto. `git grep fileUrl` (fora de testes e docs): **nenhum produtor no front**; só o BFF repassa (`app/api/chat/stream/route.ts:124,345`). O caminho é legado.
- **Texto que volta à caixa duplica?** Não. `Composer.tsx`: só devolve o texto se a caixa estiver vazia (`if (!textoRef.current.trim())`); `useAnexos.restaurar` deduplica por `id` e corta em 10; `limpar` não revoga a miniatura (`revokeObjectURL` só no `remover`, `useAnexos.ts:166`), então a ficha devolvida continua com a foto. O 4xx que o BFF só repassa traz `status` no corpo (`route.ts:359-364`): `recusaAntesDoTurno` não o trata como recusa prévia. A pergunta gravada continua com o "Tentar de novo".

## Pendências (nenhuma é blocker)

1. **`PARADAS` órfã:** um Stop que cai na reserva de um turno que depois é recusado (política/porteira) deixa `PARADAS[chave]`, que só sai no próximo turno com a mesma chave. É memória de alguns bytes por Stop, e não chega a ninguém.
2. **SSRF amarrado ao host do `SUPABASE_URL` do backend:** se o Storage um dia for servido por domínio próprio, o `fileUrl` legítimo é recusado. Vira o aviso interno de sempre, fail-safe. Não há produtor hoje.
3. **Áudio:** o teto de 15 min só vale quando o cabeçalho diz a duração (o WebM do gravador costuma não dizer). Isso está declarado no código, e o teto de 20 MB continua valendo.
4. **404 + composer:** o caminho "a conversa não é sua" chama `handleNewConversation()` e depois devolve o texto. Não medi se o composer remonta nesse meio; se remontar, o texto se perde. Ele não duplica.
5. **Medição que não fiz:** `test_spec132a_anexos.py`, `test_spec132a_turno_rapido.py`, `rt132a/aquece.py` e `juiz132a/test_juiz_corrida.py`. A trava `pesado.sh` ficou ocupada por mais de 50 min (um `next build`, depois a bateria `bat132`). Os dois arquivos de teste estão no lote `bat132/p3.lst` da bateria do gerente, e **o resultado deles é o que fecha a prova dinâmica de P1 e RT-P1**.

## Nota: 86

Os quatro blockers estão fechados no código, e B1 e B2 foram medidos aqui. Nenhum defeito novo apareceu no que chega ao segurado ou à corretora. Desconto: P1 e RT-P1 foram confirmados por leitura e não por execução minha, e o Presidio-sem-pt não foi medido.
