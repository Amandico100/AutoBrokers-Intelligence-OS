# SPEC-130-B · LAUDO DO RED TEAM (fresco, cego ao juiz)

> 11/10/2026 · árvore `AutoBrokers-FIX` · branch `spec/130-B-a-ficha-unica` · HEAD `e508120` · diff `8beabf9..e508120`
> (22 arquivos, +6.792/−160 — `git diff 8beabf9..e508120 --stat`). Legenda: 📊 medido (comando ao lado) · 💭 ilustrativo.
> ⛔ Nenhuma chamada a modelo, InfoCap, WhatsApp, portal ou banco. Todo PDF/valor é SINTÉTICO. Dublês SÓ na borda
> (HTTP do CORP, MinIO, Supabase, Redis, modelo, docling). Os scripts de reprodução estão no scratchpad da sessão:
> `C:\Users\amand\AppData\Local\Temp\claude\c--Users-amand-Projetos-AUTOBROKERS-RESULTA-AutoBrokers-FIX\e014e95b-b73c-4d39-af67-42670df67d3f\scratchpad\`
> (`rt1_juiz.py` · `rt2_pii.py` · `rt3_servico.py` · `rt4_fio_ponta.py` · `rt5_bordas.py` · `rt6_sinistro.py` · `mut_trecho.py`).
> Rodar cada um: `cd backend; $env:PYTHONIOENCODING="utf-8"; .venv/Scripts/python.exe <scratchpad>\<script>`.

## VEREDITO — QUEBREI

Quatro quebras mudam bytes que chegam ao segurado, à corretora e ao banco. O isolamento por corretora, a trava do 2º
plano com Redis, a máscara de dinheiro e o orçamento de tempo NÃO quebraram.

Linha de base: os testes da SPEC passam — 📊 `pytest tests/test_spec130b_o_fio.py tests/test_spec130b_o_motor.py
tests/test_spec130b_costura.py tests/test_spec130b_anexos.py -q` → **57 passed in 57.56s**. Mutação minha no elo do meio
(o degrau do texto deixa de exigir o trecho literal, plugin `mut_trecho.py`): 📊 **1 failed, 20 passed** — o guarda
`test_linha_do_modelo_sem_trecho_literal_e_descartada` fica VERMELHO. O guarda serve; as quebras abaixo estão no que ele
NÃO afirma.

---

## BLOCKERS

### B1 · O juiz confere a SOMA, não a LINHA: rótulo, limite e "linha = o total" passam como "conferida"
`policy_document_evidence_service.py:1239–1291` (`_linhas_do_modelo`) só confere (a) que o `trecho` é substring do texto
mascarado da página e (b) que o prêmio é um dos valores do trecho. O `rotulo` e o `limite` do modelo NÃO são conferidos
contra o trecho; o trecho pode ser a linha do PRÊMIO LÍQUIDO, uma linha "Total" ou a página inteira (o texto é
normalizado em espaço único, então qualquer trecho multi-linha é substring). No degrau da visão (`:1459`,
`exigir_trecho_literal=False`) não há âncora nenhuma: só a soma. A docstring de `:1251` ("O modelo não tem como inventar
uma linha que o documento não tem") é refutada.

📊 Reprodução no motor (`rt1_juiz.py`, página Tokio sintética, esperado R$ 31.875,89):
```
CONTROLE (modelo honesto)        estado: fechou  · 2 linhas certas
1a rótulo trocado + LMI inventado estado: fechou  · "Danos Eletricos | lmi R$ 9.999.999,00 | premio R$ 16.771,96"
1b uma linha = o prêmio líquido   estado: fechou  · "Incendio | lmi R$ 5.000.000,00 | premio R$ 31.875,89"
1c trecho = a página inteira      estado: fechou  · "Cobertura Ampla | premio R$ 31.875,89"
1e só a linha 'Total' do quadro   estado: fechou  · "Total | premio R$ 31.875,89"
1g visão: 1 linha inventada       estado: fechou  · "Coberturas Basicas | lmi R$ 1,00 | premio R$ 31.875,89"
ficha ao segurado (1a): "Conferida: a soma das coberturas bate com o prêmio líquido (R$ 31.875,89). // Coberturas: //
 - Danos Eletricos · limite R$ 9.999.999,00 · prêmio R$ 16.771,96 ..."
```
📊 De PONTA A PONTA (`rt4_fio_ponta.py`: conector REAL → serviço → DocumentService → leitor → `apolice_reconciliada_do_pack`;
o `/itens` do CORP traz os LMIs CERTOS 5.000.000 e 600.000):
```
controle                       leitura: fechou | sinais: [] | Incendio 5000000.00 · Danos Eletricos 600000.00 (documento_oficial)
rótulos trocados + LMI         leitura: fechou | sinais: [] | Incendio limite=1000.00 · Danos Eletricos limite=9999999.00 (documento_oficial)
uma linha só = prêmio líquido  leitura: fechou | sinais: [] | + "Vendaval limite=50000.00 premio=31875.89 (documento_oficial)"
documents.metadata.leitura.estado gravado: ['fechou']   (os três)
```
O documento VENCE o cadastro em limite (regra de `reconciliar`, `policy_data_provider.py:1690`): o LMI inventado
SOBRESCREVE o LMI certo do CORP, sem sinal, com "conferida".
**Teste do produto:** muda o limite e a lista de coberturas ditos ao segurado e à corretora, e o `documents.metadata`
(a taxa de acerto do leitor contaria isto como acerto) → **BLOCKER**. Exige o modelo errar (alucinação, coluna trocada
no PyPDF2/PyMuPDF, "Total" que o prompt proíbe mas o código não barra) ou injeção no PDF; o juiz existe exatamente para
esse caso. Confiança: alta no defeito; a FREQUÊNCIA não foi medida (régua de 32 sem gabarito por linha).
Direção (o executor decide): no degrau do texto, `rotulo_nao_e_cobertura` (+ "total") sobre o TRECHO; rótulo e limite
(quando vier) dentro do trecho; trecho dentro de UMA linha do texto original; e uma linha cujo prêmio = esperado nunca
fecha sozinha. Na visão, "fechou" só com ≥ 2 linhas e nenhuma = esperado (ou a visão nunca dá "conferida").

### B2 · Erro passageiro do modelo vira leitura FINAL para sempre
`_leitura_guardada` (`:1774–1781`) aceita `nao_fechou` como final desde que exista QUALQUER degrau `modelo`/`visao` — inclusive
um degrau com `erro` (429, crédito zerado, timeout de rede) ou com JSON truncado (0 linhas, sem erro). O 2º plano grava o
mesmo estado (`:1871`).
📊 `rt3_servico.py` 4a (1ª chamada 429, depois modelo saudável; Redis dublê):
```
1a: estado=nao_fechou cache=miss degraus=[regex, (modelo, erro=RuntimeError)]
2a: estado=nao_fechou cache=hit  degraus=[... (modelo, erro=RuntimeError)]
3a: estado=nao_fechou cache=hit  ...      chamadas ao modelo: 1 (o saudável nunca mais é chamado)
4d (o 2º plano morre com exceção): travas restantes = 0 | 2a: nao_fechou cache=hit (modelo, erro) | chamadas: 1
```
📊 `rt5_bordas.py` 5d (JSON truncado pelo teto de saída): `estado=nao_fechou degraus=[{'degrau':'modelo','linhas':0,
'descartadas':0}]` — sem `erro`, gravado como final pelo mesmo caminho.
Só destrava mudando `LEITOR_VERSAO` ou o `preliq`. 📊 O laudo do BLOCO 0 mediu **123,5 s** na Tokio COND e a memória do
programa registra crédito de API zerado (SPEC-116) — o evento é realista.
**Teste do produto:** depois de um 429, a apólice que fecharia ("Conferida" + lista inteira) fica "NÃO conferida" + a lista
parcial do regex, para o segurado e a corretora, indefinidamente → **BLOCKER**.

### B3 · Documento de SINISTRO que cita a apólice perde o conteúdo; orçamento de oficina vira "cotação com coberturas"
`tipo_de_documento` (`:963–986`) devolve `apolice` para qualquer PDF com a palavra "apólice" nas 3 primeiras páginas, e
`cotacao` para "orçamento" sem número de apólice. `vision_service.conteudo_do_anexo` (`:425–438`) manda ao modelo do
atendimento SÓ a ficha quando o tipo é "de seguro" — e a ficha de um laudo/BO não tem linha nenhuma.
📊 `rt6_sinistro.py` (PDFs sintéticos de laudo, BO, aviso de sinistro e orçamento; arquivo "documento.pdf" e
"IMG-…-WA0003.pdf"; ledger = o classificador REAL `claims_shadow.tipo_de_documento` via `webhook.nome_do_documento`):
```
orcamento de oficina  ao modelo: 'Documento: cotação. Sem prêmio líquido…  Coberturas: - Para-choque dianteiro
                      substituicao · limite R$ 1.250,00 … - Total do orcamento · limite R$ 2.740,00'
laudo de vistoria     ao modelo: 'Documento: apólice. Sem prêmio líquido…'  | o CONTEÚDO chega? False | ledger antes=laudo agora=outro
boletim de ocorrencia ao modelo: 'Documento: apólice. Sem prêmio líquido…'  | o CONTEÚDO chega? False | ledger antes=boletim_ocorrencia agora=outro
aviso de sinistro     ao modelo: 'Documento: apólice. Sem prêmio líquido…'  | o CONTEÚDO chega? False | ledger antes=outro agora=outro
```
Antes desta SPEC o texto (cru) chegava; agora o atendente lê "Documento: apólice" e nada do laudo/BO, e o orçamento da
oficina é apresentado como cotação de SEGURO com "coberturas" e "limite". E o evento `claims.documento_recebido` muda de
enum (o 2º argumento de `tipo_de_documento` em `webhook.py:1838` agora é a FICHA, não o texto).
**Teste do produto:** muda a mensagem que o segurado recebe num sinistro e o enum gravado no ledger → **BLOCKER**.
Direção: ficha sem nenhuma linha de cobertura/plano → o texto MASCARADO (como já é para "não é de seguro"); "orçamento"
só é cotação com "seguro"/"prêmio"; o 2º argumento do classificador do ledger continua sendo o texto (mascarado), não a ficha.

### B4 · "Leitura em andamento" quando nada está em andamento (baixa gravidade, uma linha)
No ANEXO não existe 2º plano: estourado o orçamento, `ler_anexo_de_seguro` (`:1584–1588`) cancela o modelo e marca
`pendente`; a ficha diz "Leitura completa ainda em andamento". No CORP sem Redis, o mesmo (`:1886–1889`,
`orcamento_estourado_sem_segundo_plano`) e a marca do atendimento diz "a leitura ainda esta em andamento" (`infocap_tool`).
📊 `rt5_bordas.py` 7: orçamento 2 s, modelo de 10 s → `2.0 s | modelo chamado 1 | "Documento: apólice. // Leitura completa
ainda em andamento: a lista abaixo pode estar incompleta."` — e nenhuma tarefa continua. 📊 `rt3_servico.py` 4b: sem Redis,
`motivo=orcamento_estourado_sem_segundo_plano`, estado `pendente`.
**Teste do produto:** o atendente pode prometer ao segurado um retorno que nenhum processo fará → **BLOCKER** (copy:
"leitura parcial", não "em andamento", quando não há 2º plano).

---

## PENDÊNCIAS (não mudam byte hoje, ou são de modo degradado / pré-existentes)

| # | achado | medição | o que destrava |
|---|---|---|---|
| P1 | máscara deixa passar telefone com ESPAÇO (`11 98765 4321`, `98765 4321`, `11.98765.4321`), CEP cru (`01310100`), CPF com espaços/barra, RG (`12.345.678-9`, `MG-…`, 7 dígitos), nascimento; nome/endereço chegam por desenho | 📊 `rt2_pii.py`: **10 de 34** formas vazam; ao dublê do modelo de leitura CHEGAM nome, endereço, telefone c/ espaço, RG | o papel é `classe_de_dado="pii"` (o provedor já recebe nome/endereço): defesa em profundidade, não vazamento novo. Ampliar telefone/CEP, que o contrato §4 promete |
| P2 | texto ao modelo SEM teto | 📊 `rt5_bordas.py` 5b: 300 páginas → **648.490 chars (~162 mil tokens)**; `rt2`: 848.190 chars | teto por chars/páginas (como `MAX_DOCUMENT_TEXT_CHARS`), ou só as páginas com dinheiro |
| P3 | sem Redis: TODA pergunta espera o orçamento e paga o modelo de novo (o `pendente` gravado nunca serve) | 📊 `rt3` 4b: 3 perguntas → tempos `[0.53, 0.51, 0.53]` com orçamento 0,5 s, **3 chamadas** ao modelo; em produção = +20 s por pergunta | backoff por hash fora do Redis, ou não tentar o modelo sem trava |
| P4 | "ENDOSSO N 12 DE RESTITUICAO" vira `tipo=apolice` (o regex exige `nº`/`no`/`n.`); prêmio negativo impresso é ignorado (→ "sem prêmio") | 📊 `rt5` 5e | aceitar `n\s*\d`; sinal no `_VALOR_BR` do impresso |
| P5 | regex leu 0 linhas → o modelo VENCE mesmo sem fechar: linha duplicada e separador trocado entram na ficha (com "NÃO conferida") | 📊 `rt1` 1d: 3 linhas, Σ 46.979,82; 1f: "prêmio R$ 16,77" de `16,771.96` | recusar duplicata por (página, rótulo, prêmio); recusar `\d,\d{3}\.\d{2}` |
| P6 | caminho vivo que o card não nomeou: `POST /attendance/media/document-extract` (`attendance_media.py:302–379`) lê PDF por `extract_text_internal` com máscara PRÓPRIA (`_mask_pii`) — um 2º leitor de anexo fora da ficha | leitura do código; pré-existente | consolidar no leitor (CLAUDE.md §5) |
| P7 | com `POLICY_INTELLIGENCE_V2` desligada, `nodes._conteudo_da_consulta_para_o_modelo` serializa o resultado INTEIRO ao modelo — agora também `objeto_do_risco` (placa/chassi/CEP crus); o `document_text` (pré-existente) já levava o mesmo | `nodes.py:582–598` | pré-existente; o estado da flag em produção decide |
| P8 | anexo 100 % escaneado: sem prêmio impresso não há `esperado` → a visão nunca roda → "não consegui ler" | 📊 `rt5` 5c: `estado=sem_premio_para_conferir … degraus=['regex']` | visão no anexo sem esperado (com teto) |
| P9 | latência do webhook: o handler espera o anexo inline até **40 s + 20 s de folga = 60 s** (`vision_service.py` ORÇAMENTO/FOLGA) antes do agente; extração fora do orçamento (📊 300 pág = 6,0 s nesta máquina) | 📊 `rt5` 7: orçamento respeitado (2,0 s com orçamento 2 s); tool do CORP: +20 s no miss/hit sem leitura final, + 1 GET `/documento_anexos` por pergunta sem `url_apolice` | aceitar (D-130B-08) ou baixar o orçamento do anexo |
| P10 | JSON gigante do modelo é processado no laço `async` | 📊 `rt5` 5d: 200 mil linhas → 12,0 s (irreal: o teto de saída do modelo é ~centenas de linhas) | teto de linhas aceitas |

---

## O QUE TENTEI E NÃO QUEBROU
- **Tenant** (`rt3` §3): A e B, mesmo PDF/hash/locator/nome de conexão, banco e MinIO COMPARTILHADOS → cada uma leu a sua
  (`chamadas ao modelo por empresa: ['A','B']`), fichas no prefixo da própria corretora (`True`, 2), e a ficha de A posta
  no caminho de B **não serve a B** (`False`, a ficha carrega e confere o `company_id`). Trava = company+conexão+hash.
  Cache de `/itens` = hash(company)+hash(conexão)+locator+data (leitura do código).
- **Concorrência com Redis** (`rt3` 4e): 2 simultâneas → **1** chamada ao modelo (`['fechou','pendente']`); sem Redis, 2 (aceitável).
- **2º plano** (`rt3` 4c/4d): termina e grava; a próxima vem `fechou` sem modelo; a trava SOLTA também quando o modelo
  levanta (`travas restantes = 0`). O `pendente` com Redis não relê pelo modelo (a trava barra).
- **Dinheiro na máscara** (`rt2`): 27 formas reais (LMI, prêmio, colados do PyPDF2, `LMI 1000,00`, `Vig 2025-2026`,
  `R$ 150000000,00`, franquia em prosa) → **2 alteradas**, ambas irreais (`1234-5678,00`, `Aba 1234 ,56`).
- **Bordas**: PDF corrompido / vazio / zip → `falhou` + `None` (o webhook diz "reenvie"); `extrair_paginas_tolerante(lixo)`
  levanta `ValueError` como antes; 100 páginas só imagem pelo CORP → a visão recebe **20** páginas (teto), 326 KB;
  `premio_esperado` 0/negativo: o conector devolve `None` (o leitor nunca o recebe).
- **Regressão**: `_contador_de_premio` mantém R$ 0,05 e o guarda `liquido <= 0` acima de `fecha_o_premio`; `reconciliar`
  só acrescenta o sinal (a regra de quem vence não mudou — e é ela que torna B1 grave); o nome mascarado do arquivo não
  muda o enum do ledger em 5 nomes testados (`CNH2025.pdf` já era `desconhecido` antes); `extract_document_text` ficou
  sem chamador no produto (`grep` → só a definição em `vision_service.py:349`).
- **Efeito externo**: nenhum caminho novo envia mensagem, aciona portal ou cobra (leitura do diff; o webhook só monta texto).

## O ELO MAIS FRACO
O juiz prova que a SOMA fecha, e o produto o anuncia como prova de que a LISTA está certa — e o documento vence o CORP no limite.

## NOTA — 58 / 100
Confiança: alta em B1–B4 (reproduzidos com o motor real; dublê só no modelo/HTTP/armazenamento). Não medido: a
frequência real de B1 com a Luna (exige gabarito por LINHA na régua das 32, não só Σ) e o timeout de webhook do Evolution.
