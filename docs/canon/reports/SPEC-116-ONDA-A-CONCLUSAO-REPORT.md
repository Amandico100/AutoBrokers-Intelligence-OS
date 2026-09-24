# SPEC-116 · Conclusão da Onda A (decisão do Founder, 24/09/2026)

## EXECUTION CARD
```
OUTCOME ....... todo papel operacional em modelo APPROVED: Sol (chat medium · atendimento HIGH · portal/visão/documentos/juiz/subagente medium),
                Luna medium (volume), Opus 5.5 (ex-Opus 5), gpt-transcribe (ex-whisper-1). Produção só aceita APPROVED.
RISCO 8 · SUPERFÍCIE 2 · CRÍTICO (atendimento) · executado ENXUTO por ordem do Founder (franquia em 5%)
O FIO ......... o de SPEC-116 §4 (inalterado); teste do fio: backend/tests/test_o_fio_do_modelo.py
GATES ......... migration VERIFY · 0 rotas não-APPROVED · legacy gate com mutação · 250 testes verdes
```
## O que mudou
- Migration `20260924_01_spec116_onda_a_conclusao.sql` APLICADA (versão 20260924180612): catálogo (Sol/Luna/gpt-transcribe APPROVED;
  Sonnet 5, Opus 5, Haiku 4.5 DEPRECATED; Luna com esforço mínimo medium), 25 rotas, trigger de produção = só APPROVED + esforço ≥ mínimo.
- `model_policy.py`: produção (rota/agente/snapshot/portal) só APPROVED; a BANCADA continua podendo usar CANDIDATE/DEPRECATED por override.
- `audio_service.py`: gpt-transcribe pela API /audio/transcriptions (não a fábrica de chat), prompt de domínio sem PII com seguradoras de
  `insurer_registry`, ledger por minuto com duração medida (WAV/OGG); sem duração → não inventa.
- `auxiliaries.py`: template pode declarar `runtime_policy.papel_de_modelo`; default `auxiliar` (Luna medium). Só Resumo e Follow-up usam LLM;
  `specialized_executor`/`agent_backed_auxiliary` são rótulos (factory.py:50-51, 390) sem execução própria.
- Docling: `docling==2.130.0` (o que `>=2.0.0` resolve hoje; API `PictureDescriptionApiOptions` conferida no fonte), `VISION_MODEL=gpt-6-sol`,
  `reasoning_effort=medium`, sem `seed`, timeout 90 s. ⚠️ 2.1xx troca OCR padrão (rapidocr) — conferir no Implantar.
- Defaults consertados: `COUNCIL_MEMBERS` (gpt-6-sol, claude-opus-5-5) · `constants.memory_llm_model` (chave morta removida).

## Mapa efetivo (📊 `resolver()` depois da migration)
atendimento gpt-6-sol high · chat_principal/portal_decisao/visao/visao_documento/juiz_eval/subagente gpt-6-sol medium ·
memoria/hyde/chunking_agentico/distiller/extrator_planos/brand_capture/garimpo/auxiliar gpt-6-luna medium ·
dispatch/atlas_parser/distiller_forte/conselho_lider/juiz_playbook/prompt_optimizer/sugestoes claude-opus-5-5 (esforço padrão) ·
transcricao gpt-transcribe · embedding text-embedding-3-small (mantido) · rerank cohere v3.0 (mantido). Cobrança: não tem papel próprio —
a conversa usa o agente de atendimento (Sol high); executores determinísticos sem LLM (SPEC-078).

## Varredura residual
OPERACIONAL indevido: 0. Pendente de decisão: `llama_guard_service.py:71` (guardrail Groq, DEPRECATED, sem substituto). Restante: comentários,
histórico, baseline (`benchmark_service`), texto de tela (`finops/plans/page.tsx:427`), catálogo.
Limitação do gate: literal novo num arquivo que já tem o MESMO nome classificado como comentário não é pego (pendência).

## BLOCKED_BY_CREDIT
chamada live GPT-6 Sol · GPT-6 Luna · Opus 5.5 · gpt-transcribe · visão do Docling · smoke real · canário.

## Desvio declarado
Juiz ‖ red team NÃO rodaram (ordem do Founder: franquia em 5%). Prova = VERIFY da migration + 250 testes + mutação do gate.
Recomendado: juiz curto na próxima sessão, antes do canário.

## Proposta criada
`docs/canon/specs-propostas/SPEC-117-o-atendimento-nunca-perde-a-apolice-que-encontrou.md` — PROPOSTA, NÃO EXECUTADA.
