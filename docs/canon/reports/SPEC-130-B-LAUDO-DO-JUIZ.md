# SPEC-130-B · A ficha única da apólice — LAUDO DO JUIZ FRESCO

> Juiz Opus 5.5, read-only, sem a narrativa dos builders. Branch `spec/130-B-a-ficha-unica`, diff `8beabf9..e508120`
> (31 commits, 22 arquivos, +6792/−160). Data: 11/10/2026. Legenda: 📊 medido (com o comando) · 💭 ilustrativo.
> Todo código que importa serviço rodou com dublê (leitor de modelo injetado; nenhum Supabase/MinIO/LLM real).
> Banco: só SELECT pelo MCP.

## VEREDITO
**PASS COM PENDÊNCIAS — e UM BLOCKER pequeno (B1).** A obra é boa: os números da régua se reproduzem do JSON ao
centavo, as 11 de controle seguem no regex com custo zero, a regra de quem vence em `reconciliar` não mudou, o contador
do cadastro manteve R$ 0,05, a migration está aplicada e certa, as mutações do §6 ficam vermelhas, não há PII nem PDF na
bancada versionada. O único defeito material é que o JUIZ DO DOCUMENTO confere a SOMA e o TRECHO, mas não confere o
RÓTULO: uma linha do modelo com rótulo inventado, citando a linha do "Prêmio Líquido", fecha e sai "Conferida".

## BLOCKERS

### B1 · O juiz aceita linha do modelo com rótulo que não está no trecho (inclusive a linha do prêmio líquido)
- **Onde:** `backend/app/services/policy_document_evidence_service.py` `_linhas_do_modelo` (≈ linhas 1239–1291 no HEAD):
  o filtro é `rotulo_nao_e_cobertura(rotulo)` sobre o rótulo que o MODELO escreveu + `trecho in pagina_texto` +
  `_premio_no_trecho(premio, trecho)`. Nada exige que o rótulo esteja no trecho, nem que o trecho não seja a linha de
  total/prêmio líquido/IOF. O degrau da visão (`exigir_trecho_literal=False`) só tem a soma.
  A docstring afirma *"O modelo não tem como inventar uma linha que o documento não tem"* — 📊 medido falso.
- **Medição** (script do juiz com dublê, `scratchpad/ataque_juiz.py`, `python ataque_juiz.py` de `backend/`):
  ```
  0 regex: nao_fechou 0 0.00                                    ← controle: o regex não lê a tabela sintética
  1 honesto: fechou 2                                           ← controle: 2 linhas certas fecham
  2 trecho=premio liquido, rotulo inventado: fechou 1 ['Incendio Raio Explosao']
     ficha ao segurado: Documento: apólice. | Conferida: a soma das coberturas bate com o prêmio líquido (R$ 1.000,00).
     | Coberturas: | - Incendio Raio Explosao · prêmio R$ 1.000,00 (pág. 1)
  3 rotulos fora do trecho: fechou ['Roubo', 'Vendaval']        ← rótulos trocados, trechos reais, soma fecha
  4 trecho inventado: nao_fechou … descartadas 1                ← a defesa que EXISTE funciona
  ```
- **TESTE DO PRODUTO:** SIM. Muda o que chega ao SEGURADO (`ficha_para_o_modelo` diz "Conferida" e lista uma cobertura
  que o documento não tem) e ao CORRETOR/BANCO (`reconciliar` casa por rótulo e o DOCUMENTO VENCE no limite — um rótulo
  trocado põe o limite de uma cobertura em outra, por cima do cadastro). Não foi observado na bancada (o JSON não tem
  rótulos, de propósito), mas 14 das 26 que fecham fecharam pelo MODELO e 1 pela VISÃO — 📊 `regua.py` sobre o JSON:
  `quem venceu nas que fecham: {'regex': 11, 'modelo': 14, 'visao': 1}`: o rótulo dessas 15 não foi conferido por ninguém.
- **Conserto sugerido (≈ 15 linhas + 1 teste vermelho→verde):** (a) descartar a linha cujo TRECHO casa o vocabulário
  de total (`rotulo_nao_e_cobertura(trecho)` ou o mesmo regex de prêmio líquido/IOF/custo/total/parcela); (b) exigir o
  rótulo (normalizado, sem acento, tokens ≥ 3 letras) DENTRO do trecho — ou, se isso derrubar linhas de rótulo em duas
  linhas, ao menos dentro da PÁGINA; (c) na visão: `rotulo_nao_e_cobertura` e recusar UMA linha só igual ao esperado.
  Rerodar a régua (📊 custo da rodada anterior: US$ 0,027 estimado, soma de `custo_usd_estimado` no JSON) e mostrar
  que as 26 seguem. Mutação: tirar (a)/(b) faz o teste novo ficar vermelho.

## PENDÊNCIAS (não mudam byte hoje, ou dependem de medição)
1. **P-130B-J1 · os 21 PDFs já guardados são lidos com as páginas VELHAS.** No hit (`ensure_official_policy_evidence`,
   ≈ linha 1921) as páginas vêm de `load_raw_pages` (extração de antes da 130-B) e a visão só roda se
   `metadata.parser_por_pagina` existir — 📊 SELECT: `documents` com `file_name like 'infocap-policy-%'` = 21, 3 corretoras,
   último 26/09, **0 com metadata**. Um PDF da Sura/Yelum (PyPDF2 com erro por página) ou escaneado guardado antes de hoje
   não ganha o leitor tolerante nem a visão até `force_refresh`. A régua mediu bytes FRESCOS. Destrava: no hit sem
   `parser_por_pagina`, reextrair de `carregar_pdf_original` (o método já existe). Vira BLOCKER se algum dos 21 tiver
   página vazia no raw (medir no MinIO).
2. **P-130B-J2 · máscara:** passam intactos 📊 `RG 12.345.678-9`, `CPF 123 456 789 09`, nº de apólice com pontos,
   data de nascimento; nome e endereço passam por desenho (classe `pii` declarada). A visão manda a página como imagem,
   sem máscara (declarado no §2). Destrava: acrescentar RG pontuado e CPF com espaços.
3. **P-130B-J3 · linhas do modelo que NÃO fecham também vencem** quando o regex leu 0 (`linhas_m and juizo["linhas"]==0`):
   📊 EMPR-ALLI-17 (falta R$ 798,12) e EMPR-ALFA-21 (sobra R$ 18,53 — uma linha a mais, provavelmente errada). Essas
   linhas entram no pack e, em `reconciliar`, o documento vence o cadastro no limite — com o sinal
   `documento_nao_conferido` aceso. Destrava: decisão (manter com o sinal × não deixar vencer o cadastro sem fechar).
4. **P-130B-J4 · latência:** o anexo do segurado no webhook espera até 40 s (+20 s de folga) ANTES do turno
   (`vision_service.conteudo_do_anexo`, orçamento padrão 40); sem 2º plano e sem cache por hash (reenviar repaga o modelo).
   E `/documento_anexos` é consultado a cada pergunta documental sem `url_apolice`, antes do hit do cache, sem Redis.
5. **P-130B-J5 · `chat.py`:** `company_id=str(chat_request.companyId)` vira `"None"` se o campo vier vazio.
6. **P-130B-J6 · `guardar_leitura` faz I/O síncrono (MinIO + Supabase) dentro do laço async**, inclusive na tarefa de
   2º plano — o padrão de antes do serviço, mas agora roda em toda leitura.
7. **P-130B-J7 · AUTO-LIBE-26 sai `tipo_documento=endosso` e `fechou` (dif. R$ 8,42 ≤ tol. R$ 17,25).** A renovação
   marca `documento_nao_e_a_apolice` (F4); o atendimento não marca nada. Conferir se é endosso de verdade.

## EVIDÊNCIA (comandos e saídas)
| ataque | comando | resultado |
|---|---|---|
| gates da SPEC | `pytest tests/test_spec130b_{o_fio,o_motor,fontes_do_corp,anexos,renovacao_le_a_ficha,costura}.py -q` | 📊 **111 passed** em 72,55 s |
| régua — 3 números | `regua.py` + recálculo à mão de `max(0,05; 0,5 %)` sobre `soma`×`esperado` do JSON | 📊 RESI 7/7 · COND 8/8 · EMPR 5/7 · AUTO 6/6 = **26/28**, 4 sem PDF; **0 divergências** entre a tolerância à mão e `fecha_juiz` |
| as 11 de controle | idem | 📊 as 11 `fechou`, degraus `['regex']`, custo somado **0.0** |
| migration | `select … from llm_papeis where papel='leitura_de_apolice'` | 📊 `openai/gpt-6-luna/medium · anthropic/claude-sonnet-5-5/medium · pii · alto · v1 · migration 20261011_05`; `schema_migrations` tem `20261012000915 spec130b_papel_leitura_de_apolice` (o nome do ROLLBACK casa) |
| rollback | leitura do arquivo | `delete` da linha + da versão + regerar snapshot; sem FK; falha fechada (`ModeloNaoResolvido` → regex, `nao_fechou`). OK |
| mutação (2) juiz sempre fecha | plugin em memória `mutacao_juiz.py`, `MUTACAO=juiz` | 📊 **12 failed**, 9 passed (o_motor + o_fio) |
| mutação (3) texto sem máscara | `MUTACAO=mascara` | 📊 **1 failed** (`test_o_texto_que_chega_ao_modelo_esta_mascarado`) |
| dado vazio/nulo | `ataque_juiz.py` 5a–5e | JSON inválido → `nao_fechou`, 0 linhas · modelo fora → `degrau.erro=RuntimeError`, `nao_fechou` · sem páginas → `nao_fechou` · sem esperado → usa o impresso · sem esperado nem impresso → `sem_premio_para_conferir`, **0 chamadas** ao modelo |
| quem vence em `reconciliar` | leitura `policy_data_provider.py:1685–1764` + diff | só ACRESCENTA o sinal `documento_nao_conferido` antes do `if pdf is None or not pdf.linhas`; o resto é idêntico |
| `_contador_de_premio` | leitura :1940–1975 + `pytest test_o_contador_de_premio_acende.py test_a_divergencia_aparece_inteira.py test_toda_linha_tem_origem.py` | guarda de `liquido ≤ 0` continua antes; tolerância `TOLERANCIA_DE_PREMIO` (0,05); 📊 **3 passed** |
| regressão vizinha | `pytest` de 8 arquivos (pipeline documental, 2ª corretora não vê a 1ª, documento lido sempre, cobertura inteira, 129-B porta/fio, 016, porta não vaza) + 2 scripts | 📊 **31 passed**; `test_a_apolice_responde_item_por_item.py` PASS=31 FAIL=0; `test_o_plano_vem_da_apolice…` 25 verdes |
| duas corretoras | testes `test_isolamento_a_leitura_da_corretora_A_nao_serve_a_B`, `test_duas_corretoras_nao_trocam_o_cache_dos_itens`, `…_o_candidato`; código | ficha em `{company_id}/raw/{doc}.leitura.json` + `company_id` conferido dentro; trava `leitor_apolice:{h(company)}:{h(conexão)}:{hash16}`; `/itens` com company+conexão+data na chave; o documento já era por conexão (`find_official_policy_document`) |
| mesma leitura 2× / 2 processos | testes `…segue_em_segundo_plano_e_a_proxima_vem_do_guardado`, `…duas_chamadas_simultaneas_uma_leitura_pela_trava`, `…sem_redis_nao_ha_segundo_plano` (vermelhos sob a mutação 2) | `SET NX EX 600`; quem não trava devolve `pendente` sem modelo; a ficha só grava estado final; Redis com `decode_responses=True` (📊 `core/redis.py:31,62`) — o `get == marca` do `_soltar` compara str com str |
| o produto chama | rastreio | conector `infocap_lookup`/`infocap_policy_detail` → `_maybe_attach…(client=…)` → `ensure_official_policy_evidence(premio_liquido_esperado=)` → `_ler_e_registrar` → pack → `apolice_documental_do_pack` (`infocap_policy_provider.py:906,1051`) → `reconciliar` → tool (`_com_documento`, marca no atendimento) → recorder; webhook `:3322` e `chat.py` → `conteudo_do_anexo` → `ler_anexo_de_seguro` → `ficha_para_o_modelo` |
| PII / bancada | `git ls-files docs/intake/BANCADA-130B` → 0; `.gitignore:113 docs/intake/`; nenhum `.pdf`/`.env` no diff; regex de CPF/11 dígitos/URL/e-mail/placa no JSON → 1 casamento, é um `locator_hash` | sem PII versionada |
| efeito externo | `grep` de envio no diff | 0 chamadas novas de envio; nenhuma corretora por nome no código (§13.9) |

## MAIOR LACUNA
O rótulo das linhas que o modelo e a visão leem não é conferido por nada — e é o rótulo que `reconciliar` usa para
pôr limite em cobertura e que o segurado ouve como "conferida" (B1). A soma prova que o DINHEIRO está todo lá; não prova
que cada real está com o NOME certo.

## PRÓXIMA AÇÃO
Consertar B1 em `_linhas_do_modelo` (trecho de total recusado + rótulo dentro do trecho/página; visão com o mesmo filtro),
1 teste com a linha de controle, rerodar a régua (≈ US$ 0,03) e uma confirmação curta (§6.1).

## CONFIANÇA — 82
Medido: os gates, os números da régua a partir do JSON, a tolerância à mão, a migration, duas mutações, a regressão
vizinha, os ataques de vazio/nulo e de rótulo. **Por medir:** a mutação (1) (PyMuPDF no caminho do regex) não foi
rerodada por mim; os 21 PDFs guardados (P-J1) — não abri o MinIO; a latência real do webhook com o modelo de verdade;
a bateria completa (é depois do conserto, §5 ⑦); os rótulos reais das 15 que fecharam pelo modelo/visão (a régua não os
guarda).

## NOTA DA UNIDADE — 84
(88 sem B1. O desenho, o isolamento, o registro sem PII e a régua são de nível alto; o juiz que é o coração da SPEC tem
uma porta aberta barata de fechar.)
