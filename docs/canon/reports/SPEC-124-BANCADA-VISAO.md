# SPEC-124 · F2 — a bancada da visão por campo (D3 · G4 · G6)

> 01/10/2026 · builder F2 (Opus 5.5 xhigh) · branch `spec/123-o-agente-destrava` (não commitado: o gerente commita)
> Fonte de todo número: os JSONs das rodadas (scratchpad da F2) e o ledger `token_usage_logs`.
> Comando da tabela: `python scripts/bancada.py --resumo-visao "<scratch>/visao_*.json" --recalcular`.

## 1. O que foi medido
- **Corpus** `backend/tests/corpus/bancada/visao_campos/` — 10 documentos SINTÉTICOS (PIL): apólice auto
  em 2 layouts, apólice residencial, CNH, CRLV, orçamento de oficina, boleto, foto de para-brisa trincado
  com a placa visível, apólice auto DEGRADADA (62 % da resolução, inclinada, ruído, JPEG q38) e CNH
  FOTOGRAFADA (inclinada, fundo escuro, desfoque). Distratores: prêmio por cobertura ao lado do LMI,
  prêmio líquido/IOF ao lado do total, franquia de vidros ao lado da básica, subtotal/desconto, data do
  documento ao lado do vencimento. Dados fictícios válidos em forma (CPF com dígito verificador, placa
  Mercosul), vindos dos marcadores de `dubles.materializar` — nenhum valor no texto do corpus.
- **Gabarito por campo** — 12 campos por documento (nome, CPF, placa, nº apólice, vigência início/fim,
  coberturas com LMI, valor total, franquia, vencimento, validade, tipo). **Juiz** normalizado: CPF/apólice
  só dígitos, placa sem traço, datas ISO, valores em centavos, nome sem acento/caixa; coberturas por nome
  compatível E LMI igual, sem cobertura a mais. Campo que o documento não tem e o modelo preencheu =
  **inventou** (erro).
- **Mesmo prompt para todos**: o produto só DESCREVE (`describe_image`), então a bancada usa UMA
  instrução fixa de extração (`bancada.INSTRUCAO_DE_CAMPOS`), com a imagem no formato do produto.
  Braços pela fábrica do produto (`criar_de_resolvido`), ledger `service_type='bancada'`, `details.papel='visao'`.
- **Nota D3** = campos críticos com valor acertados ÷ (com valor + críticos inventados). O "acerto geral"
  conta null certo como acerto e esconde erro: 📊 o dublê `burro` tira 48,3 % no geral e 0 % na D3.

## 2. A tabela (k=3 · 30 documentos por braço)
| braço | nota D3 | docs perfeitos | inventou | formato ✘ | US$/doc (bancada) | p50 | p90 |
|---|---|---|---|---|---|---|---|
| `openai:gpt-6-luna:medium` | **100,0 %** | 30/30 | 0 | 0 | **0,00016** | 3,0 s | 4,7 s |
| `openai:gpt-6.1-sol:medium` (o atual) | 100,0 % | 30/30 | 0 | 0 | 0,00566 (1ª passada) · 0,00226 (com cache) | 4,7 s | 7,8 s |
| `anthropic:claude-sonnet-5-5:low` | 100,0 % | 30/30 | 0 | 0 | 0,00548 | 2,0 s | 3,0 s |
| linha de controle `duble:perfeito` | 100,0 % | 10/10 | 0 | 0 | — | — | — |
| linha de controle `duble:burro` | 0,0 % | 0/10 | 0 | 10 | — | — | — |

**Por campo** (os três braços reais): tipo 30/30 · nome 30/30 · CPF 30/30 · placa 30/30 · apólice 30/30 ·
vigência início 30/30 · vigência fim 30/30 · coberturas 30/30 · valor total 30/30 · franquia 30/30 ·
vencimento 30/30 · validade 30/30.

**O prompt de DESCRIÇÃO do produto** (corpus `visao` da SPEC-116, `describe_image`, k=1): Luna 10/10 ·
Sol 6.1 10/10 · Sonnet 5.5 low 10/10.

**Opus 5.5 não rodou**: os três candidatos já estão no teto do corpus — o Opus como "teto de qualidade"
não teria o que separar, e o orçamento fica.

### ⚠️ Correção de gabarito, declarada
📊 Na 1ª rodada da Luna, `coberturas` deu 26/30: nos 4 erros o modelo listou "Assistência 24h" (que o
layout A mostra DENTRO do quadro de coberturas, sem LMI) com valor null. É leitura defensável do
documento, não erro do modelo. O gabarito passou a declarar esse item como `opcional` (pode vir sem
valor, ou não vir; **com valor inventado continua erro** — testado). As imagens ficaram byte a byte
iguais (md5 conferido). As respostas gravadas foram RE-JULGADAS sem modelo (`--recalcular`): 30/30.

## 3. A decisão (D3 · G4)
- **Principal `visao` = `openai/gpt-6-luna` medium** — empate técnico (0 pontos de diferença ≤ 2) → o
  mais barato. **G4 ✅**: acerta = o atual (100 % = 100 %) e custa ~1/18 (ledger, sem cache: US$ 0,000202 ×
  0,003673 por chamada).
- **Reserva `visao` = `anthropic/claude-sonnet-5-5` low** — outro provedor, 100 %, o mais rápido.
- **`visao_documento` = `openai/gpt-6-luna` medium, SEM reserva**: o docling só fala Chat Completions
  OpenAI (`PictureDescriptionApiOptions`, lido no wheel docling-slim 2.130.0). 📊 Smoke 01/10: o pedido
  EXATO do docling com a Luna → HTTP 200, `usage` devolvido.
- Migration pronta, **NÃO aplicada**: `backend/supabase/migrations/20261001_03_spec124_visao_por_bancada.sql`.

## 4. O custo (G6) — ledger, `service_type='bancada'`, desde 2026-10-01T00:00Z
| | antes da F2 (`details.papel='visao'`) | depois | teto da fatia |
|---|---|---|---|
| OpenAI | US$ 0,0000 | **US$ 0,128485** (Luna 0,008937 em 50 chamadas · Sol 6.1 0,119548 em 40) | 0,45 |
| Anthropic | US$ 0,0000 | **US$ 0,223422** (Sonnet 5.5 em 40 chamadas) | 0,35 |

(O ledger da bancada desde 01/10 já tinha US$ 1,354635 OpenAI e 1,301633 Anthropic do destravador da
SPEC-123 — fora desta fatia; por isso o teto da F2 é lido só por `details.papel='visao'`.)

## 5. Limites (o que este número NÃO diz)
- Corpus **sintético e limpo** — o número é TETO. Documento real mascarado não existe no acervo e não
  há mascarador de imagem; foto de celular de verdade (reflexo, dobra, corte) não foi medida.
- 10 documentos × 3 passadas: 0 erros em 30 não prova taxa de erro 0 (IC 95 % superior ≈ 10 %).
