# PACOTE · BUILDER U1 — SPEC-EXTRA-001 · o motor, a porta de saída e a migration

Você é o 🔧 BUILDER da unidade **U1 · motor + porta + migration** da **SPEC-EXTRA-001 · A operação dos pilotos**. Modelo: Opus 5. A escrita desta unidade é **só sua** (§4). Árvore: `C:\Users\amand\Projetos\AUTOBROKERS RESULTA\AutoBrokers-FIX` (branch `feat/spec-extra-001-operacao-pilotos`). Python roda a partir de `backend/` com `PYTHONIOENCODING=utf-8`. Um desenhista escreve os guardas em `backend/tests/test_a_cobranca_chega_a_quem_deve.py` e um builder U3 escreve o Next **ao mesmo tempo** — você não toca nesses arquivos.

## Leia primeiro
```
docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md              §0–§3, §5, §7.3
CLAUDE.md                                            §7 · §8 · §9.1 · §9.3 · §9.4 · §12.1
docs/canon/MIGRATIONS-AUTHORITY.md                   🔴 inteiro antes do SQL
docs/canon/PROMPT-DE-EXECUCAO-EXTRA-001-CONTRATOS.md inteiro — §1–§4 são o seu contrato exato
docs/canon/specs/SPEC-EXTRA-001-operacao-dos-pilotos.md   §0.1 · §0.3 · §0.5 · §2 · §3 · §6 · §7 · §8 · §10
backend/app/services/billing_collection.py           inteiro (1.799 linhas) — é o arquivo-hub
backend/app/services/platform_outbound.py            :100-180 · :217-330 · :618-700 · :842-1210
backend/app/services/integration_service.py          :50-70 · :150-170 · :220-300
backend/app/services/whatsapp_service.py             :131-290
backend/app/services/routine_engine.py               :280-330 · :520-610
backend/app/services/work/workflows.py               :295-360 (a ponte da rotina → onde o run_id existe)
backend/app/telefone_br.py                           so_digitos / variantes_br (use; não copie a regra)
backend/tests/fixtures/schema_vivo.json              `detalhe.billing_sent_log`, `detalhe.platform_sends`, `detalhe.integrations`
backend/tests/test_a_cobranca_esta_como_estava.py    34/34 hoje — TEM de continuar (o modo teste não muda)
```

## As travas
```
⛔ NENHUMA mensagem sai. NENHUM agente é ligado. NENHUM portal. API InfoCap: só leitura.
⛔ Banco: SELECT livre. Escrita só pela migration desta unidade, com APPLY/VERIFY/ROLLBACK ESCRITOS ANTES no cabeçalho do .sql — e você NÃO aplica a migration em produção: o orquestrador aplica. Você prova o SQL com `psql`-like leitura e com o dublê.
⛔ NUNCA imprimir CPF, telefone, apólice, placa, nome de pessoa, senha ou token. NUNCA um telefone real no código (nem como exemplo).
⛔ NUNCA `git add -A`. NÃO commitar. NÃO tocar em variável de ambiente. Arquivos com LF.
⛔ Motor paralelo é proibido (CLAUDE.md §5): nada de fila/scheduler/sender/ledger novo. O ledger É `billing_sent_log`; a porta É `send_to_client_guarded`.
⛔ Canário VIVO só com `AUTOBROKERS_CANARIO=1` — não é sua tarefa.
```

## O EXECUTION CARD desta unidade
```
OUTCOME ..............  `equipe` e `cliente` enviam de verdade pela porta única (texto limpo + PDF), com reserva ANTES do efeito por RPC, estado por componente,
                        conexão fixada e revalidada, autorização de auxiliar sem depender do agente de atendimento, incidentes em Atividades; modo teste intacto
RISCO / SUPERFÍCIE ...  8 / 3   NÍVEL CRÍTICO   PISO §3.2 (envia + migration de estrutura)
ARQUIVOS (só estes) ..  backend/app/services/billing_collection.py · backend/app/services/platform_outbound.py · backend/app/services/routine_engine.py (só repassar work_run_id) ·
                        backend/app/services/work/workflows.py (só repassar work_run_id em bridge_rotina, se o ctx o tiver) ·
                        backend/supabase/migrations/20260907_01_spec_extra001_billing_sent_log_estados.sql (novo) · backend/supabase/migrations/MANIFEST.md (uma linha)
INTERFACES QUE TOCA ..  CONTRATOS §1 (config) · §2 (ledger + RPCs) · §3 (porta) · §4 (motor). U2 e U3 dependem dos NOMES fixados lá — não renomeie.
REFERÊNCIA ...........  interna: `send_to_client_guarded` como está (o CONTROLE: defaults preservam o comportamento de hoje) · `test_a_cobranca_esta_como_estava.py` ·
                        `_send_test_messages` (não muda) · externa: Postgres ddl-constraints (índice único parcial + predicado no ON CONFLICT) · AWS outbox (intenção antes do efeito; `incerto`)
GATES ................  G01–G12, G17–G19, G25, G26 da SPEC §8 (o desenhista escreve; você faz ficar verde pelo comportamento) · `test_a_cobranca_esta_como_estava` 34/34 · `test_spec078_bloco_a_seguranca` 39/39 · `test_governador_de_envio` · `py_compile`
PENDÊNCIAS ...........  P-098-RUN-NOS-JOBS (parcial: o run viaja até o ledger e a porta) · P-097-TELEFONE-BR-DUPLICADO (use `telefone_br`, não copie)
FAIXA DE RELÓGIO .....  2h30–3h30
```

## Como trabalhar
1. **BLOCO 0 primeiro:** remeça o que a SPEC §1 afirma sobre `billing_collection.py:1734-1737`, `:908-921`, `:924-953`, `:1088-1105`, `platform_outbound.py:948-990`, `:1071-1084`, `integration_service.py:274-298`. Se o seu número for diferente, o seu vence. Escreva os dois lados.
2. **A migration** (CONTRATOS §2), idempotente (`ADD COLUMN IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`, `CREATE OR REPLACE FUNCTION`), expand-first, com cabeçalho `-- APPLY / -- VERIFY / -- ROLLBACK` e `COMMENT ON COLUMN` dizendo de quem é cada coluna. `to_phone` é dado da própria corretora (a tabela já guarda `cliente_nome`), mas NUNCA vai para log, relatório de execução ou artifact. As duas funções: `billing_reservar_obrigacao` e `billing_reclamar_obrigacao`, exatamente com as assinaturas do CONTRATOS. Se o cliente Python do Supabase não tiver `rpc` no objeto usado (`client.rpc(...)` existe no supabase-py; confira o wrapper `app.core.database`), diga como chamou.
3. **A porta** (CONTRATOS §3): acrescente os kwargs com defaults que preservam HOJE. Ordem das checagens: `ator_ainda_pode` → (se `canario`: remetente E destinatário na allowlist, por `variantes_br`) → (se `autorizacao_de_auxiliar`: integração fixada relida por id + `pode_enviar(para="auxiliar")`; senão: interruptor do atendimento como hoje) → QUENTE/cortesia/governador (com `enfileirar`/`destino_interno`) → `_entregar_agora(integration=fixada, documento, ledger_ref, canario)`. `_entregar_agora` com `ledger_ref` marca `text_ok`, `doc_ok`, `sent_at`, `status` (`aceito_pelo_canal` sem doc previsto · `entregue_equipe` se `kind=="billing_equipe"` e doc ok · `parcial` se doc previsto e falhou · `falhou` se o texto falhou) e `last_error`; se a marcação DEPOIS de um `ok` levantar → não levanta para fora: devolve `{"ok":True,"ledger":"falhou"}` e o chamador grava `incerto`… se puder; senão o incidente vai ao log. A fila carrega as chaves novas quando existirem.
4. **O motor** (CONTRATOS §4): `normalize_billing_config` (4 modos + `retido_legado`, `team_number`, `confirmacao_cliente`, `canario`); `_pacote_humano`; `_obrigacoes_reais`; `_entregar_cobranca_real`; `avisar_suporte_humano(..., *, suprimir=False)` nas 3 chamadas; `execute_billing_collection_routine(..., *, work_run_id=None)`; o ramo de despacho por modo (o `live`/`approval` legado vira blocker "configuração antiga: escolha Encaminhar para minha equipe ou Enviar ao cliente"); relatório e peça com as contagens reais. **`_send_test_messages` e `_format_test_message` NÃO mudam** — o guarda 34/34 é o controle.
5. **Incidentes:** toda falha material (sem canal, reserva falhou, conexão trocada, parcial, incerto, contato inválido, fora da allowlist) → `log_activity(company_id, "cobranca", <título humano curto>, <detalhe sem PII>)`.
6. Rode parciais: `python -m py_compile` dos arquivos; `python tests/test_a_cobranca_esta_como_estava.py`; `python tests/test_spec078_bloco_a_seguranca.py`; `python tests/test_governador_de_envio.py`; e, quando o desenhista tiver publicado `tests/test_a_cobranca_chega_a_quem_deve.py`, rode-o e faça os gates de U1 ficarem verdes (se um gate estiver errado contra o CONTRATOS, diga qual e por quê — não "ajuste o teste para passar").
7. Entregue: diff resumido por arquivo · BLOCO 0 medido · a saída dos testes · o SQL inteiro da migration no relatório · **o que viu FORA do escopo** (obrigatório) · o que ficou pendente.
⛔ Não narre "está funcionando". Cole a saída do comando.
