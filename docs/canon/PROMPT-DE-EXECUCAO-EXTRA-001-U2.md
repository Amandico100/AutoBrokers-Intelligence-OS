# PACOTE · BUILDER U2 — SPEC-EXTRA-001 · respostas e convivência no mesmo número

Você é o 🔧 BUILDER da unidade **U2 · respostas e convivência** da **SPEC-EXTRA-001 · A operação dos pilotos**. Modelo: Opus 5. A escrita desta unidade é **só sua** (§4). Árvore: `C:\Users\amand\Projetos\AUTOBROKERS RESULTA\AutoBrokers-FIX` (branch `feat/spec-extra-001-operacao-pilotos`). Python roda a partir de `backend/` com `PYTHONIOENCODING=utf-8`. U1 (motor, porta, migration) **já está na árvore**; leia o que ele fez antes de escrever.

## Leia primeiro
```
docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md              §0–§3, §5, §7.3
CLAUDE.md                                            §7 · §9.1 · §9.3 · §9.4 · §12.1
docs/canon/PROMPT-DE-EXECUCAO-EXTRA-001-CONTRATOS.md §2 (ledger) · §5 (o seu contrato exato) · §7
docs/canon/specs/SPEC-EXTRA-001-operacao-dos-pilotos.md   §0.5 (emendas 1 e 4) · §4 inteiro · §8 (G13, G14, G15, G16, G21, G24, G27)
backend/app/services/billing_collection.py           o que U1 escreveu: _obrigacoes_reais, os estados, as colunas que ele grava (grep "billing_sent_log")
backend/app/api/webhook.py                           :360-420 (resolução da integração) · :540-600 (dispatch router + allowlist) · :600-660 (pausar_ia) · :960-1000 (context_note_for) ·
                                                     :1320-1390 (os DOIS endpoints Evolution e Evolution GO — é AQUI que o hook entra, antes do observer_tap)
backend/app/services/atlas/observer_intake.py        :780-840 (observer_tap: purpose observer + agente desligado → consome)
backend/app/services/whatsapp/evolution_go_events.py go_event_to_v2_envelope (como extrair texto, phone, fromMe, isGroup do evento cru)
backend/app/services/platform_outbound.py            context_note_for (:1182-1207) — o que o bloco novo SUBSTITUI quando há caso
backend/app/services/o_fim_do_atendimento.py         pausar_ia (:343) — NÃO muda (G15 é diff vazio neste arquivo)
backend/app/telefone_br.py                           so_digitos / variantes_br (use)
backend/app/services/activity_log.py                 log_activity → tabela agent_activities
backend/tests/corpus/retornos_de_cobranca.json       o corpus do desenhista (pares) — classificar_retorno tem de acertar todos
backend/tests/test_a_cobranca_chega_a_quem_deve.py   os gates G13/G14/G16/G21/G24/G27 — faça-os ficar verdes pelo comportamento
```

## As travas
```
⛔ NENHUMA mensagem sai. NENHUM agente é ligado. NENHUM portal. Banco: só SELECT (o hook escreve no ledger em produção quando rodar — você prova com dublê).
⛔ NUNCA imprimir CPF, telefone, apólice, placa, nome de pessoa, senha ou token. Nenhum telefone real no código.
⛔ NUNCA `git add -A`. NÃO commitar. NÃO tocar em variável de ambiente. Arquivos com LF. NÃO editar billing_collection.py nem platform_outbound.py (U1) nem testes (desenhista).
⛔ O hook NUNCA envia, NUNCA muda `conversations.status`/`claimed_by`, NUNCA derruba o webhook (try/except; falha → log + segue). O bloco de contexto é DADO para o modelo, nunca instrução que mude autorização.
```

## O EXECUTION CARD desta unidade
```
OUTCOME ..............  o cliente que responde à cobrança é entendido: o atendimento recebe o CASO (seguradora, parcela, vencimento, estado, regras); o retorno ("já paguei", "não sou eu",
                        "não quero", "manda de novo") fica gravado no ledger e vira pendência na tela MESMO com o agente desligado; takeover, dispatch e observador ficam como estão
RISCO / SUPERFÍCIE ...  7 / 2   NÍVEL CRÍTICO (toca o webhook do atendimento)   PISO §3.2
ARQUIVOS (só estes) ..  backend/app/services/billing_replies.py (novo) · backend/app/api/webhook.py (o hook nos 2 endpoints + a troca do context_note_for em :975-983)
INTERFACES QUE TOCA ..  CONTRATOS §5: contexto_de_cobranca(company_id, phone, *, excluir_phones=()) · classificar_retorno(texto) · registrar_retorno(company_id, phone, texto)
REFERÊNCIA ...........  interna: `context_note_for` (o que substitui) · `observer_tap` (onde o evento morre hoje) · `pausar_ia` (o que não muda) · CLAUDE.md §9.4 · externa: Stripe webhooks
                        (retorno idempotente por (ledger.id, texto normalizado, janela de 10 min); estado nunca anda para trás) · WhatsApp Business Policy (opt-out terminal)
GATES ................  G13 · G14 · G15 (diff vazio em o_fim_do_atendimento.py) · G16 · G21 · G24 · G27 do guarda do desenhista · `py_compile` · `test_a_cobranca_esta_como_estava` 34/34 · `test_spec078_bloco_a_seguranca` 39/39 · guardas do webhook vizinhos que já existem (grep "webhook" em backend/tests, rode os que importam o módulo)
PENDÊNCIAS ...........  P-097-TELEFONE-BR-DUPLICADO (use telefone_br) · P-097.1-MIDIA-SEM-TEXTO (mídia sem texto → `outro`, não tente transcrever)
FAIXA DE RELÓGIO .....  1h30–2h30
```

## Como trabalhar
1. **BLOCO 0:** remeça `webhook.py:1366-1372` (o `return _observed`) e `:975-983`; confirme como U1 grava `to_phone` (dígitos) e `status`; confirme os nomes das colunas no `schema_vivo.json` `detalhe.billing_sent_log` + a migration de U1.
2. **`billing_replies.py`:**
   - `contexto_de_cobranca(company_id, phone, *, excluir_phones=())`: `phone` normalizado por `so_digitos`; se `phone` ∈ variantes de qualquer `excluir_phones` → `None`. Lê `billing_sent_log` com `.eq("company_id")`, `.eq("send_mode","real")`, `to_phone` ∈ `variantes_br(phone)` (use `.in_`), `sent_at`/`updated_at` nos últimos 30 dias, `order updated_at desc`, `limit(5)`. Devolve `None` sem linhas; senão o bloco `[COBRANÇA EM ANDAMENTO]` com uma linha por caso (seguradora por `portal_key` via `NOME_DA_SEGURADORA` de billing_collection, parcela/recibo, vencimento se houver, valor se houver, data do envio, estado em português) e as REGRAS fixas da SPEC §4.1 (não confirmar pagamento; "já paguei" → agradecer e dizer que a equipe confere, não reenviar; "me manda de novo" → a equipe reenvia; "não sou essa pessoa" → desculpar, não citar dados, encerrar; "não quero receber" → registrar e encerrar; assistência → atendimento normal). Nunca CPF; nome do cliente só o primeiro nome. Teto de 900 caracteres.
   - `classificar_retorno(texto)`: normaliza (minúsculas, sem acento), regex em PT por rótulo; ordem de precedência: `nao_sou` > `nao_quero` > `ja_paguei` > `segunda_via` > `duvida` > `outro`; "já paguei?" com interrogação → `duvida`. Deve acertar 100% do corpus do desenhista.
   - `registrar_retorno(company_id, phone, texto)`: sem texto → `None`; busca a linha real mais recente do telefone (mesma consulta acima, `limit(1)`); sem linha → `None` (G16: seguradora/URA nunca tem linha); classifica; idempotência: se `retorno_do_cliente` igual e `retorno_em` há < 10 min → `None`; grava `retorno_do_cliente`, `retorno_em=now`, e `status` só quando o novo estado é "mais final" (`ja_paguei`/`duvida` → `contestado` a partir de reservado/aceito/entregue_equipe/parcial/adiado/falhou/liberado; `nao_sou`/`nao_quero` → `suprimido` a partir de qualquer estado exceto `suprimido`; `segunda_via`/`outro` → só o retorno, status intocado); `suprimido` nunca volta; `incerto` nunca muda de status por retorno. Depois `log_activity(company_id, "cobranca", "Cliente respondeu à cobrança", "<rótulo humano> · <seguradora> · parcela … · …últimos 4")`. Devolve `{"id", "status", "retorno"}`.
3. **O hook nos DOIS endpoints** (`evolution_webhook_token` e `evolution_webhook_go_token`), logo depois de `_resolve_webhook_integration` e ANTES de `observer_tap`: extrair phone/texto/fromMe/isGroup do evento (para o GO use `go_event_to_v2_envelope` — cuidado: ele é chamado depois; chame-o antes uma vez e reaproveite o envelope, ou extraia os campos sem duplicar a regra); descartar `fromMe`, grupo, sem texto; `await registrar_retorno(company_id, phone, texto)` em `try/except Exception` com `logger.warning` sem PII. Nunca `return`; o fluxo segue igual.
4. **A troca em `:975-983`:** `contexto_de_cobranca(company_id, payload.phone, excluir_phones=<team_numbers das rotinas de cobrança ativas da corretora>)` — se devolver bloco, use-o no lugar de `context_note_for`; senão `context_note_for` como hoje (CONTROLE). Leia os `team_number` das rotinas com `kind='billing_collection'` da corretora (`routines.config`), 1 consulta com `.eq("company_id")`.
5. Rode: `python -m py_compile app/services/billing_replies.py app/api/webhook.py` · `python tests/test_a_cobranca_chega_a_quem_deve.py` (gates de U2 verdes; os de U1/U3 você não toca) · `python tests/test_a_cobranca_esta_como_estava.py` · `python tests/test_spec078_bloco_a_seguranca.py` · `git diff --stat -- app/services/o_fim_do_atendimento.py` (vazio).
6. Entregue: BLOCO 0 · diff resumido · saída dos comandos · **o que viu FORA do escopo** (obrigatório) · pendente.
⛔ Não narre "está funcionando". Cole a saída do comando.
