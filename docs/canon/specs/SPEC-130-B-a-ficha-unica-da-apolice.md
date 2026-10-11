# SPEC-130-B — A ficha única da apólice: um leitor só, que lê qualquer seguradora e diz quando não leu

> **Executável · v1.0 · 11/10/2026** · gerente Opus 5.5 · branch `spec/130-B-a-ficha-unica` · base `4bfd562`.
> Fonte: a proposta [`specs-propostas/SPEC-130-B-A-FICHA-UNICA-DA-APOLICE.md`](../specs-propostas/SPEC-130-B-A-FICHA-UNICA-DA-APOLICE.md)
> e o [`LAUDO-LEITURA-DE-APOLICE.md`](../programa-multicalculo/131-0/LAUDO-LEITURA-DE-APOLICE.md). Onde discordarem, **esta vence**.
> Legenda: 📊 medido (com o comando) · 💭 ilustrativo.

## 0.2 EXECUTION CARD
```
OUTCOME ........ o corretor e o segurado recebem a apólice LIDA INTEIRA de qualquer seguradora (não só Allianz/HDI),
                 com "conferida: a soma bate com o prêmio" ou "não conferida: li X de Y"; o PDF que o segurado manda no
                 WhatsApp nunca mais vai cru ao modelo; toda leitura fica registrada (taxa de acerto mensurável)
RISCO .......... 8 = alcance 3 (cobertura dita ao SEGURADO) + reversibilidade 3 (a mensagem sai) + frequência 2
SUPERFÍCIE ..... 2 (vários comportamentos, lugares listados no §3)
PISO ........... CRÍTICO por 3 motivos: dado pessoal vai a modelo · migration que altera dado (`llm_papeis`) · resposta ao segurado
NÍVEL .......... CRÍTICO · builders Opus 5.5 xhigh · juiz Opus 5.5 ‖ red team Opus 5.5 · lente de PII por gatilho
O FIO .......... §2 · o teste do fio é a 1ª entrega da F1 (`backend/tests/test_spec130b_o_fio.py`), nasce VERMELHO
PARALELISMO .... F1 ‖ F2 ‖ F3 ‖ F4 com ARQUIVOS DISJUNTOS (§5) contra o CONTRATO do §4; F5 = costura + bancada, em série
UNIDADES ....... U1 fio · U2 texto tolerante + registro · U3 cascata · U4 fontes · U5 renovação/capacidade · U6 bancada
COESÃO ......... a cascata, o juiz, a máscara, o registro e os campos novos da ficha = um contrato → F1 inteira
TIME ........... 4 builders paralelos + 1 de costura · juiz ‖ red team UMA vez · confirmação se houver blocker
REFERÊNCIA ..... interna: `reconciliar` + `_contador_de_premio` (policy_data_provider.py:1606/1847) e os 11 que fecham;
                 externa: §8
GATES .......... py_compile · testes novos verdes · as 3 mutações do §6 ficam VERMELHAS · régua das 32 ≥ metas do §6
                 sem perder nenhuma das 11 · migration pelo VERIFY · bateria 0 regressão
O ELO .......... "a ficha fecha" = Σ prêmio das linhas = prêmio líquido do CORP, medido pelo CÓDIGO DO PRODUTO sobre os
                 BYTES REAIS (régua da F5), conferido pelo `/documento` (caminho independente)
FAIXA .......... 💭 4h30–6h de relógio · tetos de fatia do protocolo §10 (CRÍTICO)
```

## 1. O contrato
**Muda:** o MOTOR de leitura dentro de `policy_document_evidence_service` (cascata com juiz) · as FONTES que entram por ele
(`url_apolice` + `/documento_anexos`, anexo do WhatsApp, anexo do chat) · a `ApoliceDocumental` ganha `tipo_documento`,
`leitura` e `objeto_do_risco` · a leitura é REGISTRADA (`documents.metadata` + a ficha JSON no MinIO) · um papel novo no
Model Router (`leitura_de_apolice`).
**Não pode mudar:** a regra de quem vence em `reconciliar` · as 11 apólices que hoje fecham (controle) · o QCM continua sem
mandar o conteúdo da mídia ao modelo (B1) · cobrança e relatórios na API · nenhum motor paralelo (CLAUDE.md §5) · o
`_contador_de_premio` mantém a tolerância de hoje (R$ 0,05) para o CADASTRO.

## 2. O FIO (do 1º byte ao último)
```
CORP /documento (preliq, url_apolice) → infocap_connector._maybe_attach_official_policy_document_evidence (+ /documento_anexos
quando não há url_apolice; passa premio_liquido_esperado) → PolicyDocumentEvidenceService.ensure_official_policy_evidence
→ [hit: a LEITURA guardada da versão atual, sem modelo] · [miss: download → DocumentService.store_official_policy_document
   → páginas TOLERANTES (PyPDF2 por página; PyMuPDF só onde o PyPDF2 falha ou volta vazio)]
→ ler_documento_de_seguro: regex → JUIZ → modelo (texto MASCARADO, papel leitura_de_apolice; trecho literal obrigatório)
   → JUIZ → visão (só páginas sem texto) → JUIZ → estado
   (o modelo estoura o orçamento? → a leitura SEGUE em 2º plano com trava Redis por hash, e a resposta de agora usa o regex)
→ grava ficha JSON (MinIO) + resumo (documents.metadata) → evidence_items no pack
→ infocap_policy_provider.apolice_documental_do_pack (+ tipo/leitura/objeto) → reconciliar (+ sinal "documento_nao_conferido")
→ infocap_tool (output_summary com o estado da leitura) → chat/atendimento
Anexo: webhook.py / chat.py → ler_anexo_de_seguro (em memória) → ficha_para_o_modelo (MASCARADA) → texto do turno
```

## 3. BLOCO 0 — o que mudaria o desenho (medido em 11/10, `HEAD 4bfd562`)
| # | premissa | medição | efeito no desenho |
|---|---|---|---|
| 1 | as 11 ainda fecham? | 📊 `python medir_leitor.py 8` (script do laudo, rascunho da sessão) → **11/32**, as MESMAS 11 (RESI-ALLI ×6, COND-ALLI ×4, COND-HDI ×1); Sura 19/19 e Yelum 4/4 páginas com erro no PyPDF2 | controle válido |
| 2 | PDFs novos desde 26/09 | 📊 `select … from documents group by origem` → 21 do CORP, último 26/09, **0 com metadata** | nada novo a migrar |
| 3 | o mascarador do canal serve? | 📊 `canal/conversa.py:332` troca QUALQUER sequência de 8+ dígitos por `[NUMERO]` → apagaria `600.000,00` | NÃO serve como está: máscara própria do leitor que REUSA e-mail/CEP/placa e nunca toca dinheiro (D-130B-07) |
| 4 | o modelo barato lê o que o regex não lê? | 📊 `probe_modelo.py` (papel `auxiliar`, Luna medium): Tokio COND **20 linhas, Σ = 31.875,89 = líquido**, 20/20 trechos literais, **123,5 s**, US$ 0,0017 · Allianz EMPR **7 linhas, Σ = 10.244,03 = líquido**, 7/7, **10,3 s**, US$ 0,0006 (`token_usage_logs service_type='bancada_130b'`) | o degrau do modelo FUNCIONA e é barato; mas 2 min não cabem numa conversa → 2º plano (D-130B-08) |
| 5 | dá para baixar o esforço? | 📊 `llm_pricing`: Luna `esforco_minimo_producao = medium` | a latência não cai pelo esforço |
| 6 | papel para leitura de documento | 📊 `llm_papeis`: só `visao_documento` (do docling); nenhum de texto | papel NOVO `leitura_de_apolice` (D-130B-09) |
| 7 | onde gravar a leitura | 📊 `information_schema.columns` → `documents.metadata jsonb` e `source_kind` existem | sem migration de estrutura |
| 8 | `/itens?data=` | 📊 o script do laudo chama com `data=<inivig>` e recebe coberturas em 27/32 | data = hoje dentro da vigência, senão o início (D-130B-10) |

## 4. O CONTRATO entre as fatias (quem implementa: F1; quem consome: F2–F5)
```python
# backend/app/services/policy_document_evidence_service.py  (F1)
LEITOR_VERSAO = "130B.1"
async def ler_documento_de_seguro(pages, *, company_id, premio_esperado=None, fonte_do_esperado=None,
        file_bytes=None, total_paginas=None, parser_por_pagina=None, permitir_modelo=True,
        leitor_modelo=None, leitor_visao=None, document_id="", policy_locator=None, content_hash="") -> dict
    # → {"evidence_items": [...mesmo formato de hoje: coverage_row/assistance_plan/... com page_number e evidence_text],
    #    "leitura": {leitor_versao, tipo_documento, estado: fechou|nao_fechou|sem_premio_para_conferir|pendente|falhou,
    #                degraus, linhas, soma_linhas, premio_esperado, fonte_do_esperado, diferenca, paginas,
    #                paginas_sem_texto, parser_por_pagina, custo_usd, modelo, duracao_s},
    #    "objeto_do_risco": {placa, chassi, ano_modelo, cep, atividade, importancia_segurada}  (só na ficha, nunca no metadata)}
async def ler_anexo_de_seguro(file_bytes, file_name, *, company_id, orcamento_s=40.0, leitor_modelo=None) -> dict  # em memória
def ficha_para_o_modelo(resultado: dict, *, audiencia: "segurado" | "corretor") -> str   # MASCARADA, legível
def mascarar_texto_de_apolice(texto: str) -> str                                         # CPF/CNPJ/telefone/e-mail/CEP; nunca dinheiro
ensure_official_policy_evidence(..., premio_liquido_esperado=None)  # o resultado ganha "leitura" e "objeto_do_risco"
# backend/app/services/document_service.py  (F1)
def extrair_paginas_tolerante(file_bytes) -> (pages, parser_por_pagina: {"1": "pypdf2"|"pymupdf"|"sem_texto"}, total_paginas)
# backend/app/providers/policy_data_provider.py  (F1)
ApoliceDocumental(+ tipo_documento: Optional[str] = None, leitura: Optional[Mapping] = None,
                  objeto_do_risco: Optional[Mapping] = None)            # defaults: nenhum chamador de hoje quebra
def fecha_o_premio(soma, esperado, *, tolerancia=None) -> (fecha: bool, diferenca: Decimal, pct: Decimal)
TOLERANCIA_DO_DOCUMENTO = max(R$ 0,05; 0,5 % do esperado)   # o juiz do documento; o do cadastro não muda
reconciliar: pdf.leitura com estado ≠ "fechou" → Sinal("documento_nao_conferido", {estado, linhas, soma, esperado})
```

## 5. As fatias (arquivos DISJUNTOS — cada arquivo tem UM dono)
| fatia | entrega | arquivos (só estes) |
|---|---|---|
| **F1 · o motor** | U1 o teste do fio (vermelho) · U2 páginas tolerantes + registro · U3 a cascata, o juiz, a máscara, o 2º plano com trava, a ficha guardada, o docling fora do laço `async`, o teto de itens por tipo · o papel novo (migration + snapshot) | `services/policy_document_evidence_service.py` · `services/document_service.py` · `providers/policy_data_provider.py` · `factories/modelos_snapshot.json` · `supabase/migrations/20261011_05_spec130b_papel_leitura_de_apolice.sql` · `tests/test_spec130b_o_fio.py` · `tests/test_spec130b_o_motor.py` |
| **F2 · as fontes do CORP** | `/documento_anexos` · o prêmio esperado ao leitor · `/itens?data=` · o pack → os campos novos · a capacidade · o estado da leitura no `output_summary` | `api/infocap_connector.py` · `providers/infocap_policy_provider.py` · `agents/tools/infocap_tool.py` · `tests/test_spec130b_fontes_do_corp.py` |
| **F3 · os anexos** | WhatsApp e chat pelo mesmo leitor; ao modelo só a ficha mascarada (corretor: + texto mascarado) | `api/webhook.py` · `api/chat.py` · `services/vision_service.py` · `tests/test_spec130b_anexos.py` |
| **F4 · a renovação** | `de_apolice` lê a ficha: AUTO (objeto do risco) e RE (coberturas + objeto), recusando com a lista do que falta | `services/multicalculo/pedido.py` · `tests/test_spec130b_renovacao_le_a_ficha.py` |
| **F5 · costura + bancada** | o fio verde com o motor real · a régua `scripts/regua_ficha_da_apolice.py` sobre as 32 (locators fora do git) · a capacidade com o número medido · as mutações | `scripts/regua_ficha_da_apolice.py` · `tests/corpus/bancada/RESULTADOS/ficha_da_apolice_*.json` · + os consertos de costura nos arquivos acima |

## 6. A bancada e os guardas
- **Régua:** o leitor do PRODUTO sobre os bytes reais das 32 (semente 1311), Σ das linhas × prêmio líquido do `/documento`.
  📊 hoje 11/32. **Metas:** as 11 **intactas** · RESI ≥ 7/8 · COND ≥ 7/8 · EMPR ≥ 5/8 · AUTO ≥ 5/8 · **0** pipeline caído · o escaneado
  da Porto lido pela visão. Sem PDF (4/32) não conta contra. Resultado por id com hash, sem PII.
- **Mutações (cada uma tem de ficar VERMELHA):** (1) PyMuPDF no lugar do PyPDF2 no caminho do regex · (2) o juiz sempre "fecha" ·
  (3) o texto vai ao modelo sem máscara.
- **Isolamento:** a leitura guardada e a trava são por `company_id` + conexão + hash; teste com duas corretoras.
- **Verba:** 💭 teto US$ 1,50, escrito no livro-caixa (ESTADO-DO-PROGRAMA §3) antes de cada rodada.

## 7. Decisões (nota 0–100; diferença grande = já vem decidida)
| # | decisão | nota | contra |
|---|---|---|---|
| D-130B-01 | ficha = `Apolice`/`ApoliceDocumental`; o motor muda DENTRO do serviço que existe | 90 | leitor novo 35 |
| D-130B-02 | o juiz é o fechamento do prêmio (`fecha_o_premio`, o mesmo cálculo do `_contador_de_premio`) | 88 | gabarito digitado 50 |
| D-130B-03 | regex primeiro; modelo só no que não fecha; visão só em página sem texto | 85 | modelo em tudo 60 |
| D-130B-04 | PyMuPDF só como reserva por página | 92 | trocar o extrator 20 (📊 controle 18 → 0) |
| D-130B-05 | o anexo do SEGURADO nunca vai cru: só a ficha mascarada; o do CORRETOR leva a ficha + o texto mascarado (ele pergunta de cláusula) | 85 | só a ficha também ao corretor 70 · texto cru 30 |
| D-130B-06 | o modelo devolve as MESMAS `coverage_row` do regex, com trecho literal conferido; linha sem trecho no texto é descartada | 90 | formato novo 55 |
| D-130B-07 | máscara própria do leitor (reusa e-mail/CEP/placa do canal), nunca toca dinheiro | 88 | o mascarador do canal 20 (📊 apaga LMI) |
| D-130B-08 | o degrau do modelo roda com orçamento (💭 20 s) e, estourado, SEGUE em 2º plano com trava Redis por hash; a próxima leitura já vem pronta | 82 | Work Run no worker 75 (mais encanamento, mesmo efeito) · esperar 2 min na conversa 30 |
| D-130B-09 | papel novo `leitura_de_apolice` (Luna medium, classe pii, reserva Sonnet 5.5) | 80 | reusar `visao_documento` 60 (amarra a visão do docling) |
| D-130B-10 | `/itens?data=` = hoje, presa entre início e fim da vigência (renovação ainda não iniciada → o início) | 85 | sempre o início 55 (o item trocado por endosso some) |
| D-130B-11 | QCM: a função `ler_anexo_de_seguro` fica pronta; ligar na conversa é da 133-B | 80 | ligar agora 55 (muda o canal sem o consumidor) |
| D-130B-12 | juiz do documento = max(R$ 0,05; 0,5 %); a régua mostra também ±2 % | 82 | só ±2 % 70 (esconde uma cobertura pequena faltando) |

## 8. O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS
1. **https://cloud.google.com/document-ai/docs/overview** — classifica o tipo e extrai campos com confiança e revisão humana. ·
   Modelamos: tipo de documento primeiro + estado da leitura + degrau humano. · Rejeitamos: o serviço (dado pessoal sai; extrator
   paralelo). · Juiz: `tipo_documento` e `leitura.estado` na ficha.
2. **https://docs.aws.amazon.com/textract/latest/dg/queryresponse.html** — a resposta vem com página e posição. · Modelamos: toda
   linha cita página e trecho. · Rejeitamos: o serviço. · Juiz: linha do modelo sem trecho literal é recusada (teste).
3. **https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/overview** — layout conhecido + genérico. · Modelamos:
   regex antes do modelo. · Rejeitamos: treinar por seguradora. · Juiz: custo zero nas que o regex fecha (régua).
4. **https://pymupdf.readthedocs.io/en/latest/recipes-text.html** — texto página a página. · Modelamos: reserva por página. ·
   Rejeitamos: trocar o extrator. · Juiz: a mutação (1).
5. **https://docs.claude.com/en/docs/build-with-claude/pdf-support** — o modelo lê texto e imagem da página. · Modelamos: visão só na
   página sem texto. · Rejeitamos: o PDF inteiro a cada pergunta. · Juiz: `paginas_sem_texto` × páginas enviadas à visão.

## 9. Fora (com o porquê)
130-C (página dos outros ramos) · cotação no chat e QCM ampliado (132/133-B; aqui só a função pronta) · INCORP (Emissão e
registro; sem base de homologação — Founder 11/10) · treinar por seguradora · condição geral · pré-leitura noturna das
renovações (a 131 a dispara).
