# SPEC-EXTRA-001 · CONTRATOS COMPARTILHADOS — o que desenhista e builders assumem em comum

> Anexo de todo pacote da EXTRA-001. Quem escrever algo diferente disto está criando um segundo contrato.
> Protocolo AAA `docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md` §0–§3, §5, §7.3 vale para todos. SPEC: `docs/canon/specs/SPEC-EXTRA-001-operacao-dos-pilotos.md` (v1.1).

## 1. Configuração da rotina de cobrança (`routines.config`, `kind='billing_collection'`)
```
send_mode            'test' | 'none' | 'equipe' | 'cliente'      (legado 'approval' | 'live' → normalizado para 'retido_legado': nada sai, blocker explica)
team_number          só dígitos (telefone_br.so_digitos), obrigatório em 'equipe'
confirmacao_cliente  bool, obrigatório True em 'cliente' (a tela pede; o motor recusa sem ela → 'retido_legado' com motivo)
canario              bool (só o script de canário grava; a tela NUNCA expõe)
test_number, portal_keys, message_template, attendant_name, brokerage_name, max_boletos_por_execucao — inalterados
```
`normalize_billing_config` devolve `send_mode` ∈ {test, none, equipe, cliente, retido_legado} e mantém `send_mode_original`.

## 2. O ledger — `billing_sent_log` (migration `backend/supabase/migrations/20260907_01_spec_extra001_billing_sent_log_estados.sql`, U1)
Colunas novas (todas ADD COLUMN IF NOT EXISTS, aditivas):
```
status text NOT NULL DEFAULT 'entregue'     modalidade text          text_ok boolean        doc_ok boolean
to_phone text (só dígitos)                   to_last4 text            integration_id uuid    work_run_id uuid   routine_id uuid
reserved_at timestamptz                      sent_at timestamptz      updated_at timestamptz NOT NULL DEFAULT now()
attempts int NOT NULL DEFAULT 0              last_error text          motivo text
encaminhado_ao_cliente_em timestamptz        encaminhado_por uuid     retorno_do_cliente text   retorno_em timestamptz
canario boolean NOT NULL DEFAULT false
```
Índices: `billing_sent_log_obrigacao_uniq UNIQUE (company_id, portal_key, recibo) WHERE send_mode = 'real'` · `billing_sent_log_to_phone_idx (company_id, to_phone) WHERE send_mode='real'`.
Modos reais gravam `send_mode='real'` + `modalidade ∈ {equipe, cliente}`. O modo `test` continua gravando `send_mode='test'` como em 17/08 (não tocar).
**Estados** (`status`): `reservado` · `aceito_pelo_canal` · `entregue_equipe` · `parcial` · `incerto` · `falhou` · `adiado` · `liberado` · `suprimido` · `contestado` · `entregue` (legado).
**Retorno do cliente** (`retorno_do_cliente`): `ja_paguei` · `nao_sou` · `nao_quero` · `segunda_via` · `duvida` · `outro`.
Funções no banco (mesma migration, `SECURITY DEFINER` não — rodam com service role):
```
billing_reservar_obrigacao(p_company_id uuid, p_portal_key text, p_recibo text, p_modalidade text, p_to_phone text, p_to_last4 text,
                           p_cliente_nome text, p_apolice_susep text, p_routine_id uuid, p_work_run_id uuid, p_integration_id uuid, p_canario boolean)
  RETURNS TABLE(id uuid, ganhou boolean, status text)
  -- INSERT … send_mode='real', status='reservado', reserved_at=now(), attempts=1 … ON CONFLICT (company_id, portal_key, recibo) WHERE send_mode='real' DO NOTHING RETURNING id, true, status;
  -- sem linha: SELECT id, false, status da existente
billing_reclamar_obrigacao(p_id uuid, p_company_id uuid, p_de_status text[]) RETURNS boolean
  -- UPDATE … SET status='reservado', reserved_at=now(), attempts=attempts+1, updated_at=now() WHERE id=p_id AND company_id=p_company_id AND send_mode='real' AND status = ANY(p_de_status) RETURNING true
```
Toda escrita/leitura de código carrega `.eq("company_id", …)` (CLAUDE.md §7; service role não tem RLS).

## 3. A porta de saída — `platform_outbound.send_to_client_guarded` (U1)
Assinatura (só acrescenta; defaults preservam o comportamento de hoje = CONTROLE):
```
send_to_client_guarded(company_id, phone, text, kind="other", summary="", *, temperatura=FRIA, tentativas=0, adiamentos=0,
                       actor_user_id=None, work_run_id=None,
                       integration_id: Optional[str] = None,        # conexão FIXADA; relida por id no efeito e revalidada (is_active, company_id, pode_enviar)
                       autorizacao_de_auxiliar: bool = False,       # True: exige integration_id + pode_enviar(para="auxiliar"); NÃO exige agente ligado
                       documento: Optional[dict] = None,            # {"bucket": "portal-evidence", "path": str, "filename": str} — assinado no efeito, enviado DEPOIS do texto
                       enfileirar: bool = True,                     # False: cortesia/governador devolvem {"ok":False,"queued":False,"reason":"cliente_em_atendimento"|"governador","esperar_s":n}
                       destino_interno: bool = False,               # True: governar_envio(para_numero_de_teste=True) — um número só, da corretora
                       ledger_ref: Optional[dict] = None,           # {"table":"billing_sent_log","id":uuid} — _entregar_agora marca text_ok/doc_ok/sent_at/status/last_error
                       canario: bool = False)                       # True: remetente (paired_phone_e164 da integração) E destinatário têm de estar em BILLING_CANARIO_ALLOWLIST; senão {"reason":"fora_da_allowlist"}
-> {"ok": bool, "queued": bool, "reason": Optional[str], "doc_ok": Optional[bool], "integration_id": Optional[str], "motivo"?: str, "esperar_s"?: int}
```
`_entregar_agora(company_id, phone, text, kind, summary, *, integration=None, documento=None, ledger_ref=None, canario=False)` continua o único ponto que chama `send_*` neste caminho. Entrada da fila carrega `integration_id`, `documento`, `ledger_ref`, `canario` quando existirem; entrada antiga sem as chaves cai no comportamento de hoje.
Revalidação da conexão no efeito: `integration_service.get_integration_by_id(integration_id)`; divergiu (inexistente, `is_active` falso, `company_id` diferente, `pode_enviar(para=...)` falso) → `{"ok":False,"queued":False,"reason":"conexao_trocada"}`, nunca escolhe outra.
Env: `BILLING_CANARIO_ALLOWLIST` (dígitos separados por vírgula; comparação por `telefone_br.variantes_br`, nunca por últimos dígitos). Vazio + `canario=True` → recusa tudo.

## 4. O motor (U1) — `billing_collection.py`
- `_pacote_humano(item, cfg, boleto) -> dict(nota_interna: str, texto_final: str, documento: Optional[dict])` — `texto_final = build_customer_message(...)` sem prefixo/sufixo; nota interna começa com `📋 COBRANÇA · para encaminhar` e traz cliente · seguradora · parcela · vencimento · valor · WhatsApp legível do cliente · a instrução "quando encaminhar, marque no painel".
- `_entregar_cobranca_real(client, routine, fila, boletos, cfg, blockers, *, work_run_id) -> List[dict]` — fixa a integração 1× (`_find_whatsapp_integration`), lê `_obrigacoes_reais`, para cada item: pré-condições (portal_key não vazio; boleto no bucket; em `cliente`: telefone válido + `contact_status` aceito + `confirmacao_cliente`), reserva por RPC (`ganhou` ou reclamação de `falhou|adiado|liberado|parcial`), envia pela porta (`equipe`: nota interna + texto + doc, `destino_interno=True`; `cliente`: texto + doc), marca o ledger, grava incidentes por `log_activity(company_id, "cobranca", …)`. Reserva/leitura levantando → **não envia**, blocker + incidente. Retorno da porta `ok` sem `doc_ok` → `parcial`. Exceção DEPOIS de `ok` (registro falhou) → `incerto`, nunca retry.
- `avisar_suporte_humano(client, company_id, texto, rotulo, *, suprimir=False)` — 3 chamadas passam `suprimir=bool(cfg.get("canario"))`.
- `_send_test_messages` **não muda**. `execute_billing_collection_routine(supabase, routine, *, work_run_id=None)`; `routine_engine`/`workflows.bridge_rotina` repassam o run quando o têm.
- Relatório (`_format_report`) e peça (`compor_peca_da_cobranca`) ganham as contagens dos estados reais.

## 5. Respostas (U2, depois de U1) — `backend/app/services/billing_replies.py` (novo)
```
async def contexto_de_cobranca(company_id: str, phone: str, *, excluir_phones: Iterable[str] = ()) -> Optional[str]
def classificar_retorno(texto: str) -> str            # ja_paguei | nao_sou | nao_quero | segunda_via | duvida | outro
async def registrar_retorno(company_id: str, phone: str, texto: str) -> Optional[dict]   # None se o telefone não tem linha real; grava retorno + status (contestado|suprimido) + log_activity("cobranca")
```
Hook no **endpoint** `evolution_webhook_go_token` (e no `evolution` legado) entre `_resolve_webhook_integration` e `observer_tap`, em `try/except`. Injeção no `webhook.py:975-983` substituindo `context_note_for` quando há caso.

## 6. Tela e rotas (U3, Next) — arquivos só de U3
- `components/auxiliares/PainelDeRotinas.tsx` (hub, UM dono): `MODOS_COM_MOTOR` = test · none · equipe · cliente; `team_number` em `equipe`; confirmação (`confirmacao_cliente`) em `cliente`; legado mostra aviso; placeholder mascarado; lista "Pendências da cobrança" (GET) com ações "Marcar como encaminhado ao cliente" (POST encaminhado) e "Liberar reenvio" (POST liberar, motivo obrigatório).
- `app/api/dashboard/rotinas/route.ts`: `normalizeBillingConfig` aceita os 4 modos + `team_number` (só dígitos) + `confirmacao_cliente`; legado `approval|live` preservado como está (o Python normaliza para retido).
- Rotas novas (todas `resolveSessionCompany` + `.eq('company_id')`): `app/api/dashboard/auxiliaries/cobranca/pendencias/route.ts` GET → `{ ok, itens: [{ id, status, modalidade, portal_key, recibo, cliente_nome, apolice_susep, to_last4, sent_at, updated_at, retorno_do_cliente, retorno_em, encaminhado_ao_cliente_em, motivo }] }` (send_mode='real', status ∈ parcial|incerto|entregue_equipe(sem encaminhado)|contestado|suprimido|falhou|adiado, `order updated_at desc limit 100`); `…/encaminhado/route.ts` POST `{id, motivo?}` só de `entregue_equipe` → `encaminhado_ao_cliente_em=now`, `encaminhado_por=<user>`; `…/liberar/route.ts` POST `{id, motivo}` só de `entregue_equipe|parcial|falhou|adiado` e `contestado` com motivo → `status='liberado'`; `suprimido`/`incerto` → 409; id de outro tenant → 404; motivo vazio em liberar → 400.

## 7. Travas de todo pacote
```
⛔ NENHUMA mensagem sai. NENHUM agente é ligado. NENHUM portal. API InfoCap: só leitura. Banco: SELECT livre; escrita só pela migration desta SPEC (U1) com APPLY/VERIFY/ROLLBACK.
⛔ NUNCA imprimir CPF, telefone, apólice, placa, nome de pessoa, senha ou token. Telefones só por alias TESTE-A/TESTE-B ou últimos 4.
⛔ NUNCA `git add -A`. NÃO commitar (o orquestrador commita). NÃO tocar em variável de ambiente. Escrever arquivos com LF.
⛔ Motor paralelo é proibido (CLAUDE.md §5): nenhuma fila, scheduler, sender, inbox ou ledger novo ao lado dos existentes.
⛔ Canário VIVO só com `AUTOBROKERS_CANARIO=1` — e NÃO é tarefa de builder nem de desenhista: o orquestrador roda.
```
