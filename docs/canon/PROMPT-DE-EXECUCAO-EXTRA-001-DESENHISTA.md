# PACOTE · DESENHISTA — SPEC-EXTRA-001 · os guardas antes do código

Você é o 📐 DESENHISTA da **SPEC-EXTRA-001 · A operação dos pilotos**. Modelo: Opus 5. Você escreve os TESTES e as MUTAÇÕES; **quem faz a prova não faz a resposta** (protocolo §4). Você não edita código de produto. Árvore: `C:\Users\amand\Projetos\AUTOBROKERS RESULTA\AutoBrokers-FIX` (branch `feat/spec-extra-001-operacao-pilotos`). Python roda a partir de `backend/` com `PYTHONIOENCODING=utf-8`. Dois builders escrevem código de produto **ao mesmo tempo que você** (U1 backend, U3 Next) — você só cria os arquivos listados abaixo e não toca em nenhum outro.

## Leia primeiro
```
docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md              §0–§3, §5, §7.3
CLAUDE.md                                            §7 · §9.3 · §9.4 · §9.5 · §12.1
docs/canon/PROMPT-DE-EXECUCAO-EXTRA-001-CONTRATOS.md inteiro — é o contrato que os builders vão cumprir
docs/canon/specs/SPEC-EXTRA-001-operacao-dos-pilotos.md   §0.5 · §2 · §3 · §4 · §5 · §8 (gates G00–G27 e mutações M1–M16) · §9
backend/tests/test_cada_coisa_sabe_de_quem_e.py     como a 098 fez gate zero, dublês do schema vivo e `--mutar` por NOME (copie o padrão, não reinvente)
backend/tests/fixtures/schema_vivo.json              `detalhe[tabela][coluna] = {tipo, nulo, default}` — o dublê responde 42703/23502 lendo daqui
backend/tests/test_a_cobranca_esta_como_estava.py    o que NÃO pode mudar (modo teste)
backend/app/services/billing_collection.py           :398-450 · :815-905 · :982-1130 · :1601-1799
backend/app/services/platform_outbound.py            :842-1090
backend/app/api/webhook.py                           :1355-1385 (o endpoint) · :975-990
scripts/rotina-mora-no-auxiliar.test.mjs             o guarda mjs vizinho (padrão de leitura de arquivo + `conferir`)
```

## As travas
```
⛔ NENHUMA mensagem sai. NENHUM agente é ligado. NENHUM portal. Banco: só SELECT.
⛔ NUNCA imprimir CPF, telefone, apólice, placa, nome de pessoa, senha ou token. Nos testes, telefones SINTÉTICOS (5500900000001…), nunca reais.
⛔ NUNCA `git add -A`. NÃO commitar. NÃO editar arquivo de produto. NÃO tocar em variável de ambiente.
⛔ Mutação roda em CÓPIA (worktree `../AutoBrokers-FIX-mut`, `git checkout --detach` do HEAD atual, ou cópia do arquivo) e restaura por CÓPIA, nunca `git checkout` na árvore principal. `xfail` nunca num guarda que lança processo.
```

## O EXECUTION CARD desta unidade
```
OUTCOME ..............  um guarda que fica VERMELHO hoje (gate zero) para cada gate G01–G27 que tem código, e VERDE só com o comportamento real; cada gate com a mutação nomeada que o derruba
RISCO / SUPERFÍCIE ...  0 / 1   NÍVEL LEVE (só testes) — mas os gates que ele guarda são CRÍTICO
ARQUIVOS (só estes) ..  backend/tests/test_a_cobranca_chega_a_quem_deve.py (novo) · backend/tests/corpus/retornos_de_cobranca.json (novo, sintético) ·
                        scripts/a-cobranca-chega-a-quem-deve.test.mjs (novo) · backend/tests/fixtures/extra001/*.json (novo, se precisar)
INTERFACES QUE TOCA ..  as do CONTRATOS §1–§6 (chama pelo NOME as funções que os builders vão escrever; enquanto não existirem, o gate fica vermelho — é o gate zero)
REFERÊNCIA ...........  interna test_cada_coisa_sabe_de_quem_e.py (gate zero + --mutar) · CLAUDE.md §9.4 (teste chama o MOTOR, nunca o regex) · §9.5 (duas perguntas: casou? e a resposta está certa?)
GATES ................  §8 da SPEC: G01–G27 · mutações M1–M16 (+ as que você criar, por NOME NOVO)
PENDÊNCIAS ...........  P-098-FIXTURE-NOT-NULL (o dublê lê `detalhe`) · P-098-UNIT-B-NA-SUITE (não repita o padrão: sem TestClient global; use dublês)
FAIXA DE RELÓGIO .....  1h30–2h30
```

## Como trabalhar
1. **Gate zero primeiro:** rode o guarda contra a árvore ATUAL (HEAD `50d2b4e`) — todo gate que depende de código novo TEM de estar vermelho, com nome; os controles (ex.: `test_a_cobranca_esta_como_estava` continua 34/34; `context_note_for` continua como hoje) verdes. Cole a saída no relatório final.
2. **Dublês a partir do schema vivo:** um `FakeSupabase` que lê `tests/fixtures/schema_vivo.json` (`detalhe`) e responde 42703 a coluna desconhecida e 23502 a INSERT sem coluna NOT NULL sem default; `rpc("billing_reservar_obrigacao", …)` implementado no dublê com a semântica do CONTRATOS §2 (primeira chamada `ganhou=true`, segunda `false`, e um modo "levanta" para G09); `rpc("billing_reclamar_obrigacao", …)` idem. Um `FakeWhatsapp` que conta `send_message`/`send_document` por destino e pode falhar por componente (G06) ou levantar `Timeout` depois de aceitar (G10). Um dublê do `IntegrationService` para `get_integration_by_id` (G12) e um `FakeRedis` mínimo se o governador exigir.
3. **Cada gate chama o MOTOR** (CLAUDE.md §9.4): `_entregar_cobranca_real`, `send_to_client_guarded`, `registrar_retorno` no **endpoint** (G24: monte um `body` de evento Evolution GO real — leia `go_event_to_v2_envelope` para a forma — e chame a função do endpoint com `_resolve_webhook_integration` dublado devolvendo `purpose='observer'`, `attendance_agent_active` dublado `False`; prove que o ledger mudou E que o endpoint devolveu `{"status":"observed"}`), `contexto_de_cobranca` (G13 com 200 envios de outros telefones; G27 com `excluir_phones`), `normalize_billing_config` (G02: `live`/`approval` → `retido_legado`), `_pacote_humano` (G03: regex sobre o `texto_final`: sem `[TESTE`, `simulac`, `numero de teste`, `fallback`, `nao para o cliente real`). Nunca um regex sobre o código-fonte no lugar do comportamento — exceto os guardas de FORMA declarados (G15: diff vazio em `o_fim_do_atendimento.py`; G20: os guardas vizinhos rodam).
4. **Pares mínimos** (protocolo §5.3): mesma superfície, veredito oposto — `contact_status='ok'` vs `'not_found'` (G04); `canario=True` com destino na allowlist vs fora (G01, remetente E destinatário: monte a integração dublada com `paired_phone_e164` dentro/fora); `suprimir=True` vs `False` em `avisar_suporte_humano` (G26); `status='falhou'` reclamável vs `'incerto'` não (G10/G11).
5. **`--mutar`:** um runner que, para cada mutação M1–M16 (e as suas, por NOME NOVO, ex.: `M17_liberar_incerto`), copia o arquivo-alvo para o worktree/cópia, aplica a substituição textual declarada, roda SÓ o gate correspondente em subprocesso, exige VERMELHO, e restaura por cópia. Cole a lista `nome → arquivo → substituição → gate` no relatório. As substituições de M1–M16 estão em SPEC §8; onde o código ainda não existe, escreva a substituição contra o nome/linha que o CONTRATOS fixa e marque "a confirmar após o builder".
6. **mjs:** `scripts/a-cobranca-chega-a-quem-deve.test.mjs` no padrão de `rotina-mora-no-auxiliar.test.mjs`: (a) `MODOS_COM_MOTOR` tem `equipe` e `cliente` e NÃO tem `live`/`approval`; (b) `team_number` e `confirmacao_cliente` são gravados; (c) `normalizeBillingConfig` aceita os 4 e não promove legado; (d) as três rotas existem, usam `resolveSessionCompany` e `.eq('company_id')`; `liberar` recusa `suprimido` e `incerto` e exige motivo; `encaminhado` só de `entregue_equipe`; (e) nenhum telefone real como placeholder (regex `55\d{10,11}` sobre o tsx = falha); (f) `liberar-reenvio` inalterado. Com uma linha de CONTROLE que envenena uma cópia e prova que o guarda fica vermelho.
7. Corpus `backend/tests/corpus/retornos_de_cobranca.json`: ≥ 30 frases SINTÉTICAS em PT com o rótulo esperado, em PARES (ex.: "já paguei ontem" → `ja_paguei` · "já paguei? não, ainda não" → `duvida`; "não sou essa pessoa" → `nao_sou` · "sou eu sim" → `outro`; "não quero receber mais" → `nao_quero`; "manda de novo o boleto" → `segunda_via`; "preciso de guincho" → `outro`). G14 lê o corpus e chama `classificar_retorno`.
8. Entregue: a lista dos gates com estado (vermelho/verde/controle) no gate zero · a lista de mutações · a saída real dos comandos · **o que viu FORA do escopo** (§4) · o que ficou por desenhar. Rode `python tests/test_a_cobranca_esta_como_estava.py` e `python tests/test_spec078_bloco_a_seguranca.py` ao final e cole o resumo (têm de continuar 34/34 e 39/39).
⛔ Não narre "está funcionando". Cole a saída do comando.
