# SPEC-023A - Runbook operacional Allianz cobranca

**Data deste estado**: 2026-07-09  
**Escopo**: AllianzNet corretor, fluxo de inadimplencia/cobranca, download de boleto PDF e integracao com a rotina global de cobranca.  
**Spec mae**: `SPEC-023-portais-autenticados-hitl-cobranca.md`  
**Documento de pendencias**: `SPEC-023B-pendencias-portais-cobranca-atendimento.md`

> Este documento e para continuidade operacional. Ele nao cria arquitetura nova. O fluxo deve continuar
> usando `portal_worker`, `portal_jobs`, `portal_accounts`, `portal_sessions`, vault, `billing_collection`,
> InfoCap e WhatsApp ja existentes.

---

## 1. Estado atual em 2026-07-09

O fluxo Allianz foi corrigido e testado no portal real da Resulta.

O que foi provado no worker:

1. Login autenticado Allianz funciona usando credencial salva no vault/dashboard.
2. A entrada correta na area de inadimplencias e pela home, no card/linha `INADIMPLENCIAS`.
3. O worker nao deve digitar `cobranca` na busca global para achar inadimplencia.
4. A tela `RESULTADO - TOTAIS` e reconhecida como tela valida de inadimplencia.
5. A varredura agora percorre mais de um ramo.
6. No teste real, foram extraidos 4 inadimplentes:
   - 2 em `2013 - Residencia Digital`.
   - 2 em `2024 - Empresa PME`.
7. O worker abriu o contexto de uma apolice buscando pelo nome do segurado.
8. O worker abriu `Lista Recibos` e leu as parcelas pendentes.
9. O worker abriu `Ficha Gestao` em nova janela.
10. O worker clicou `Carta Inadimplencia - Aviso`.
11. O worker clicou no PDF e baixou 1 boleto real com sucesso.
12. O codigo foi mergeado no repo principal e o deploy do `portal-worker` foi disparado.
13. O health de producao respondeu `healthy` com `portal_real_enabled=true`.

O que ainda nao esta fechado como ponta a ponta completo:

1. Reexecutar a rotina do dashboard depois do deploy e validar o fluxo inteiro por `portal_jobs`.
2. Confirmar que a rotina resolve telefone via InfoCap para Resulta.
3. Confirmar envio WhatsApp em modo teste para o numero configurado.
4. Decidir se homologacao/final deve enviar boleto como link temporario ou PDF como arquivo/documento.
5. Se for PDF como arquivo, implementar/validar envio de documento no provider WhatsApp.
6. Validar download de mais de um boleto na mesma execucao.

---

## 2. Arquivos principais

Codigo do portal:

- `backend/portal_worker/journeys/allianz_corretor.py`

Orquestracao da rotina:

- `backend/app/services/billing_collection.py`
- `backend/app/services/routine_engine.py`

Worker e fila:

- `backend/portal_worker/worker.py`
- tabela `portal_jobs`

Credenciais/sessao:

- `backend/app/api/portal.py`
- `backend/app/services/portal_vault.py`
- tabelas `portal_accounts`, `portal_sessions`, `portals`

InfoCap:

- `backend/app/api/infocap_connector.py`
- `backend/app/providers/policy_data_provider.py`

WhatsApp:

- `backend/app/services/whatsapp_service.py`
- `backend/app/services/integration_service.py`
- `backend/app/api/whatsapp_integrations.py`
- `backend/app/api/whatsapp_channel.py`

Testes:

- `backend/tests/test_spec023_cobranca.py`
- `backend/tests/test_spec023_allianz_login.py`

---

## 3. Commits, deploy e verificacoes

Commits relevantes:

- `be3d93f fix: stabilize Allianz billing portal flow`
- `161cf0b merge: SPEC-023 Allianz billing portal flow`

Verificacoes executadas:

- `python backend\tests\test_spec023_cobranca.py`
  - Resultado observado: `PASS=83 FAIL=0`.
- `python backend\tests\test_spec023_allianz_login.py`
  - Resultado observado: `19 ok / 0 fail`.
- Teste real local sem download:
  - `cobranca Allianz concluida: 4 inadimplente(s), 0 boleto(s)`.
- Teste real local com download:
  - `cobranca Allianz concluida: 1 inadimplente(s), 1 boleto(s)`.
  - Download com `ok=true` e bytes positivos.
- Deploy:
  - `portal-worker` disparado via EasyPanel.
  - Health de producao: `status=healthy`, `portal_real_enabled=true`.

Importante:

- Health prova que o servico esta saudavel, nao prova sozinho que a rotina inteira rodou.
- O proximo passo e rodar a rotina pelo dashboard e inspecionar o `portal_jobs` real.

---

## 4. Evidencias locais e prints

As evidencias visuais estao em:

- `.codex_tmp/allianz_jobs/`

Esses prints contem dados reais de segurados/apolices. Por seguranca:

- nao versionar no git;
- nao colar em prompt publico;
- nao enviar para quem nao precisa;
- usar apenas como evidencia local para depuracao.

Prints mais importantes:

1. `.codex_tmp/allianz_jobs/local_count_all_inadimplentes.jpg`
   - Evidencia da varredura com os ramos e inadimplentes.

2. `.codex_tmp/allianz_jobs/local_download_trusted_click_page0.jpg`
   - Tela `LISTAGEM DE RECIBOS (AZR)`.
   - Mostra que `Lista Recibos` e leitura.
   - Mostra botoes cinza do rodape, incluindo `Ficha Gestao`.

3. `.codex_tmp/allianz_jobs/local_download_trusted_click_page1.jpg`
   - Janela `Ficha Gestao`.
   - Mostra tabela de documentos e linha `Carta Inadimplencia - Aviso`.

4. `.codex_tmp/allianz_jobs/local_download_ficha_url_page1.jpg`
   - Janela em branco da tentativa de abrir URL diretamente.
   - Prova que URL direta nao deve ser caminho principal.

5. `.codex_tmp/allianz_jobs/local_download_ficha_url_page2.jpg`
   - Segunda evidencia de janela em branco pela URL direta.

6. `.codex_tmp/allianz_jobs/search_dropdown_name.jpg`
   - Mostra dropdown/categorias da busca por nome.

7. `.codex_tmp/allianz_jobs/customer_result_click.jpg`
   - Mostra resultado/modal de busca por cliente.

8. `.codex_tmp/allianz_jobs/policy_context_after_customer_match.jpg`
   - Mostra contexto operacional da apolice apos selecionar cliente e abrir detalhe.

9. `.codex_tmp/allianz_jobs/download_one_wait_frame_fix.jpg`
   - Evidencia da tela de recibos em conteudo legado/frame.

Nao ha boleto PDF salvo como evidencia versionada. Isso e intencional porque boleto contem dados sensiveis.

---

## 5. Mapa da tela 1 - Login Allianz

URL publica:

- `https://www.allianznet.com.br/ngx-azb-epac/public/home`

Credenciais:

- Devem estar no dashboard/vault (`portal_accounts`).
- Nao colocar senha em doc, teste, prompt ou log.
- O worker decifra a senha via `PORTAL_VAULT_KEY`.

Fluxo esperado:

1. Abrir URL publica.
2. Tentar sessao persistida.
3. Se sessao valida, seguir direto.
4. Se sessao ausente/expirada, preencher usuario e senha.
5. Submeter.
6. Interpretar:
   - dashboard privado -> `done`;
   - credencial invalida -> `failed`;
   - CAPTCHA/2FA/codigo -> `needs_human`;
   - tela desconhecida -> `needs_human`.
7. Ao finalizar job com login ok, salvar storage state e session storage cifrados.

Sinais de dashboard:

- `Corretor principal`
- `Parcelas Inadimplentes`
- `Nova Cotacao`
- `Fale com a gente agora`
- `Tempo sessao`
- menus `Vendas`, `Consultas`, `Gestao`

---

## 6. Mapa da tela 2 - Home privada do corretor

Elementos:

- Header Allianz.
- Dados do corretor principal.
- Tempo de sessao.
- Identificacao/logo da corretora.
- Menus `Vendas`, `Consultas`, `Gestao`.
- Busca global `Pesquisar ...`.
- Botao azul `Fale com a gente agora`.
- Botao laranja `Nova Cotacao`.
- Area `Alertas de Negocio`.
- Linha/card `INADIMPLENCIAS` com contador.

Entrada correta:

- Clicar em `INADIMPLENCIAS`.

O que nao fazer:

- Nao usar busca global com `cobranca`.
- Nao clicar no chat.
- Nao clicar em documentacao/ajuda.
- Nao tentar achar boleto nessa tela.

Erro anterior:

- O job ficava na home, digitava `cobranca` e clicava em chat/ajuda.
- Resultado antigo: `needs_human`, `inadimplentes: 0`.

Correcao:

- `_ensure_inadimplentes_page` prioriza a entrada segura `INADIMPLENCIAS`.
- `_safe_home_inadimplencias_text` rejeita texto de chat/cotacao/documentacao.

---

## 7. Mapa da tela 3 - `Parcelas Inadimplentes` / `RESULTADO - TOTAIS`

Sinais:

- `PARCELAS INADIMPLENTES`
- `FILTRO`
- `RESULTADO - TOTAIS`

Campos:

- `Susep`
- `Codigo Corretor`
- `Premio`
- `Comissao`
- `Ramo`

Botoes:

- `Pesquisar`
- `Limpar`

Tabela:

- `Cd.Corretor`
- `Ramo`
- `Ramo BR`
- `Qtd.Apolices`
- `Qtd.Pcs.`
- `Premio`
- `Comissao`

Linhas reais observadas:

- `2013 - Residencia Digital`
- `2024 - Empresa PME`

Acao correta:

1. Extrair todas as linhas de ramo.
2. Clicar no primeiro ramo.
3. Coletar resultado por parcela.
4. Voltar para totais.
5. Clicar no proximo ramo.
6. Repetir ate acabar.

Erro anterior:

- Abria apenas a primeira linha ou tratava totais como tela incompleta.

Correcao:

- `extract_totals_from_rows(rows)` extrai todos os ramos.
- `_collect_inadimplentes_items(...)` itera os ramos.
- `_ensure_inadimplentes_page(...)` aceita totais como estado valido.

Testes:

- `extrai dois ramos do resultado totais`
- `entrada aceita Resultado - Totais como area de inadimplentes`
- `entrada nao abre primeira linha dos totais`

---

## 8. Mapa da tela 4 - `RESULTADO - POR PARCELA`

Quando clica em um ramo, abre a tabela de parcelas.

Sinais:

- `RESULTADO - POR PARCELA`
- colunas de recibo/apolice/vencimento/premio
- botao `Gerar Planilha`
- botao `Voltar`

Dados extraidos:

- recibo;
- parcela;
- apolice SUSEP;
- adesao;
- endosso;
- vencimento;
- valor;
- nome do segurado;
- CPF/CNPJ;
- modalidade.

Acao correta:

1. Clicar nas setas/expansores cinza no inicio das linhas.
2. Ler as linhas expandidas.
3. Associar detalhe expandido a parcela anterior.
4. Estruturar os inadimplentes.
5. Nao clicar na linha do recibo para buscar boleto.

Detalhe:

- O expansor pode aparecer como `img[id^="img_tdExtdInfo_"]`.
- A linha expandida pode vir separada no DOM.

Correcao:

- `_expand_inadimplente_details(...)`
- `_attach_expanded_details(...)`
- `extract_inadimplentes_from_rows(...)`

Testes:

- `formato real com expansor extrai recibo`
- `formato real com expansor extrai parcela`
- `formato real com expansor extrai CPF`
- `anexa detalhe expandido ao recibo anterior`

---

## 9. Busca global pelo segurado

Depois de extrair o inadimplente, o worker precisa abrir a apolice.

Fluxo correto:

1. Usar o nome do segurado.
2. Preencher a busca global.
3. Aguardar dropdown/categorias.
4. Clicar `Nome / Razao Social`.
5. Clicar no resultado correto do cliente.

O que nao fazer:

- Nao apertar Enter direto.
- Nao clicar na lupa direto.
- Nao usar `recibo` como caminho principal para boleto.
- Nao usar `cobranca`.

Correcao:

- `_fill_global_search_for_category(...)`
- `_click_search_category_candidate(...)`
- `_click_search_category_for_term(...)`

Evidencia:

- `.codex_tmp/allianz_jobs/search_dropdown_name.jpg`

---

## 10. Resultado de cliente e duplicidade

Descoberta:

- A busca por nome pode trazer mais de uma linha para o mesmo segurado.
- Nem todo resultado leva ao card operacional com apolice.

Fluxo correto:

1. Procurar nome exato.
2. Usar CPF/CNPJ quando disponivel.
3. Clicar resultado que abre card operacional.
4. Se abrir contexto incompleto, registrar evidencia e tentar fallback controlado.

Correcao:

- `_click_customer_search_result(...)`.
- O matcher aceita contexto por apolice ou por nome do segurado.

Risco:

- Se a Allianz mudar o modal, o agente deve parar com evidencia, nao clicar em qualquer pessoa.

---

## 11. Card do cliente, `Operar` e `Detalhe de Apolice`

Depois de clicar no cliente:

1. A tela mostra card(s).
2. Clicar `Operar`.
3. Aguardar area expandida.
4. Clicar `Detalhe de Apolice`.
5. Aguardar tela legada da apolice.

Correcao:

- `_click_operar_candidate(...)`.
- `_open_policy_detail_from_customer(...)`.
- `_policy_context_matches_customer(...)`.

Teste:

- `contexto operacional pode confirmar pelo nome do segurado`.

Evidencia:

- `.codex_tmp/allianz_jobs/policy_context_after_customer_match.jpg`

---

## 12. Tela legada da apolice

Elementos:

- Abas:
  - `Gerais`
  - `Segurado`
  - `Dados Risco`
  - `Coberturas`
  - `Clausulas`
  - `SDD`
  - `Resumo`
- Campos:
  - `Apolice`
  - `Apolice SUSEP`
  - `Ramo`
  - `Nome`
  - `Tomador`
- Botoes cinza no rodape:
  - `V. Global`
  - `Lista Sinistros`
  - `Ficha Gestao`
  - `Lista Recibos`
  - `Lista de Adesoes`
  - `Historico da Apolice`

Detalhe tecnico:

- Esta tela esta em frame/conteudo legado.
- Ler apenas `document.body` principal nao basta.

Correcao:

- Usar `_all_body_text(page)`.
- Clicar nos frames.
- Usar helpers especificos para `.sectionButton`.

---

## 13. `Lista Recibos`

Regra definitiva:

> `Lista Recibos` e so leitura. Nao tem nada para clicar nas linhas para abrir PDF.

Fluxo:

1. Clicar `Lista Recibos`.
2. Aguardar `LISTAGEM DE RECIBOS (AZR)`.
3. Ler tabela `RECIBOS`.
4. Identificar linhas com `Status Recibo = Pendente`.
5. Guardar recibos/parcelas/valores.
6. Em seguida clicar `Ficha Gestao`.

O que ler:

- recibo;
- parcela;
- tipo recibo;
- data emissao;
- data vencimento;
- premio total;
- status recibo;
- data status;
- corretor.

Erro anterior:

- O agente ficou procurando botao dentro de `Lista Recibos`.

Correcao:

- `_open_receipts_for_item(...)` abre e le recibos sem clicar em linha.

Testes:

- `abre recibos sem clicar em linha inadimplente`
- `fluxo nao clica em linha de recibo/inadimplente`
- `fluxo abre contexto da apolice antes de Lista Recibos`

Evidencia:

- `.codex_tmp/allianz_jobs/local_download_trusted_click_page0.jpg`

---

## 14. `Ficha Gestao`

Regra:

> O PDF vem da `Ficha Gestao`, nao da tabela `Lista Recibos`.

Como abrir:

1. Estar na tela da apolice/listagem de recibos.
2. Clicar no botao cinza `Ficha Gestao`.

Detalhe tecnico:

- O botao e um `div.sectionButton`.
- O portal chama `sendMenuVerticalEventNewWindow(...)`.
- Ele abre uma janela `ngx-file-management/fileManagement`.
- Abrir a URL diretamente pode dar tela em branco.
- O caminho principal deve ser clique trusted do Playwright com `expect_popup`.

Correcao:

- `_click_section_button_candidate_trusted(...)`.
- `_open_ficha_gestao_for_item(...)`.
- `_extract_new_window_url_from_onclick(...)` existe como fallback, nao como primeira opcao.

Evidencias:

- Sucesso: `.codex_tmp/allianz_jobs/local_download_trusted_click_page1.jpg`
- Falha por URL direta: `.codex_tmp/allianz_jobs/local_download_ficha_url_page1.jpg`
- Falha por URL direta: `.codex_tmp/allianz_jobs/local_download_ficha_url_page2.jpg`

---

## 15. Janela `Ficha Gestao` / documentos

Elementos:

- Header Allianz.
- Abas `Nota` e `Indexacao`.
- Titulo parecido com `EP - P- APOLICE - ... registros`.
- Campo `Tipo de referencia`.
- Tabela:
  - Data;
  - Tipo Modelo;
  - Descricao;
  - Usuario.

Linhas observadas:

- `O debito do seu seguro nao foi realizado.`
- `Carta Inadimplencia - Aviso`
- `PDF Conversao de Debito Automatico em Boleto`
- `Recibo ... rejeitado/Insuficiencia...`
- `NAO EXIS. AUTORIZ. DEBITO`
- `SMS`
- `Allianz Apolice Digital`
- `Apolice, Endosso ...`
- `Cartao Assistencia ...`
- `Proposta`

Fluxo:

1. Clicar `Carta Inadimplencia - Aviso`.
2. Aguardar abrir painel/preview.
3. Rolar se necessario.
4. Clicar no icone/imagem do PDF.
5. Capturar download.

Risco:

- Pode haver mais de uma carta.
- Ainda precisa validar escolha correta quando houver varias cartas para varias parcelas.

---

## 16. Download e storage do PDF

No Windows manual:

- Clicar no icone PDF abre `Salvar como`.

No Playwright:

- O contexto precisa ter `accept_downloads=True`.
- O codigo usa `page.expect_download`.
- Em producao, `_upload_blob` salva no bucket privado `portal-evidence`.

Path seguro:

```text
{company_id}/{portal_key}/{job_id}/boleto-{recibo}.pdf
```

Nao colocar no path:

- nome do segurado;
- CPF/CNPJ;
- telefone;
- dados sensiveis.

Teste:

- `path nao contem CPF`
- `path nao contem nome`
- `path termina em PDF`

---

## 17. Dados estruturados esperados

Do portal Allianz:

- `portal`
- `cliente_nome`
- `cpf_cnpj`
- `recibo`
- `parcela`
- `apolice_susep`
- `adesao`
- `endosso`
- `vencimento`
- `valor`
- `ramo_total`
- `recibos_pendentes`
- `boleto.storage_path`

Da InfoCap:

- telefone/WhatsApp;
- nome canonico;
- item segurado;
- seguradora;
- dados de veiculo quando for auto;
- dados complementares da apolice.

Observacao importante:

- InfoCap nao e "auto". E sistema de gestao usado por Resulta e AutoFleet.
- Resulta tem outros ramos; AutoFleet tem auto/frotas.

---

## 18. Mensagem de cobranca

Template desejado:

```text
Ola [NOME DO SEGURADO],
Aqui e a [NOME DA ATENDENTE], da [NOME DA CORRETORA], tudo bem?

A Seguradora [NOME DA SEGURADORA] informou que a parcela [NUMERO DA PARCELA] do seguro do [ITEM SEGURADO] ainda esta pendente.
Desta forma, a seguradora gerou um novo boleto para pagamento pra voce nao ficar sem cobertura, ok!?

Qualquer duvida estou a disposicao.

Segue o boleto abaixo.
Apolice: [NUMERO DA APOLICE]

{ENVIAR O PDF EM SEGUIDA}
```

Variaveis:

- `nome_segurado`
- `nome_atendente`
- `nome_corretora`
- `nome_seguradora`
- `numero_parcela`
- `item_segurado`
- `numero_apolice`

Estado do codigo:

- O template base esta em `billing_collection.py`.
- Em modo teste, a mensagem inclui prefixo de teste.
- Em modo teste, quando houver boleto, o codigo tenta gerar link temporario.

Lacuna:

- Se produto exige PDF como arquivo/documento no WhatsApp, ainda precisa implementar/validar envio de midia.

---

## 19. Configuracao da rotina

Tipo:

- `config.kind = "billing_collection"`

Portais:

- `config.portal_keys`, por exemplo `["allianz_corretor"]`.

Modos:

- `test`: envia somente para `test_number`.
- `approval`: cria pedido de aprovacao.
- `live`: envio real, ainda bloqueado por gates.
- `none`: somente relatorio.

Campos:

- `approval_required`
- `send_mode`
- `test_number`
- `message_template`
- `attendant_name`
- `brokerage_name`
- `insurer_name`
- `max_boletos_por_execucao`
- `poll_timeout_seconds`
- `management_provider`

Teste recomendado agora:

1. Configurar modo `test`.
2. Selecionar Allianz.
3. Usar `max_boletos_por_execucao=1`.
4. Rodar/despausar.
5. Ver relatorio.
6. Inspecionar `portal_jobs`.
7. Confirmar mensagem de teste no WhatsApp.
8. Depois subir para 4.

---

## 20. Como depurar se falhar

Se a rotina disser `inadimplentes: 0`:

1. Abrir o `portal_job` da execucao.
2. Ver `status`, `evidence`, `screenshots`, `error`.
3. Confirmar se chegou em `RESULTADO - TOTAIS`.
4. Confirmar se clicou em `INADIMPLENCIAS`.
5. Ver se voltou ao erro antigo de busca/chat.
6. Confirmar versao do worker em producao.

Se disser `inadimplentes > 0` e `boletos baixados: 0`:

1. Ler `evidence.download_notes`.
2. Ver a ultima etapa:
   - busca por nome;
   - categoria `Nome / Razao Social`;
   - resultado do cliente;
   - `Operar`;
   - `Detalhe de Apolice`;
   - `Lista Recibos`;
   - `Ficha Gestao`;
   - `Carta Inadimplencia - Aviso`;
   - PDF/download.
3. Usar screenshot.
4. Reproduzir local com `max_boletos=1`.

Se WhatsApp nao chegar:

1. Confirmar modo `test`.
2. Confirmar `test_number`.
3. Confirmar integracao WhatsApp ativa da corretora.
4. Ver se o provider aceita envio de texto.
5. Ver se boleto e link ou arquivo.

---

## 21. Regras para o proximo executor

Fazer:

- ler este runbook antes de codar;
- usar evidencia real;
- criar teste house-style antes de corrigir comportamento;
- rodar teste local;
- rodar teste real controlado;
- usar `portal_jobs` como fonte de verdade;
- manter o motor unico.

Nao fazer:

- criar outro worker;
- criar outra fila;
- criar outro browser engine;
- usar Firecrawl como substituto do Playwright no portal autenticado;
- procurar botao dentro de `Lista Recibos`;
- colar senha/token em doc;
- dizer que esta pronto sem rodar a rotina ponta a ponta.

