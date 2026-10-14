modelo: claude-opus-5-5

# CONFIRMAÇÃO do conserto da SPEC-132-B (Cotação Rápida)

> Juiz NOVO, cego ao conserto. 14/10/2026. Branch `spec/132-o-chat-e-a-cotacao`, HEAD `bdfdfd0`.
> Conserto = 14 commits `fix(spec-132-B conserto)` (`a62a8f9` … `d4aa30c`), 802+/91− em 14 arquivos.
> Pergunta única: o conserto fechou os blockers e criou defeito novo?

## VEREDITO

**FECHADOS 6/6. UM DEFEITO NOVO (o "sim" por ÁUDIO nunca confirma). NOTA 82/100.**

## 1. Os seis blockers — medidos

📊 14/10/2026, dublês do repositório (banco U1, robô do Agger, Redis em memória), pytest um arquivo por vez pela trava.

| # | blocker | prova | resultado |
|---|---|---|---|
| B1 | recálculo com a tabela e o link de antes | `scratchpad/juizB/test_juiz_132b.py::test_sonda_o_recalculo_mostra_o_preco_novo` | `[AJUSTE] link IGUAL antes/depois? False` — tabela e link novos. **FECHADO** |
| B2 | economia sem apólice + o parser 100× | `conserto132b/test_rt_132b_depois.py` rt1/rt2 (7/7 passam) · sonda: `valor_em_reais("4200.00")=4200.0`, `"3.500,50"=3500.5`, `"3500.50"=3500.5` · `seguro_atual` só põe `novo_com_apolice` com ficha `estado=fechou` + `tipo=apolice` | rt1: `'4200.00' -> None novo_sem_apolice` (o dito nunca vira economia). **FECHADO** |
| B3 | CPF de outro cliente da mesma conversa | `montar` só lê o texto cru quando o modelo mandou um CPF, e `documento_compativel`: sonda `("52998224725","***.***.***-25")=True`, `(…,"-31")=False` | **FECHADO** |
| B4 | disparo sem o "sim" | `test_sonda_disparar_no_mesmo_turno_sem_um_sim`: `pedidos criados: 0`. **Controle:** o `rt132b/test_rt_132b.py` ORIGINAL (o fluxo sem a fala "sim") agora FALHA em rt2; a cópia `_depois`, que difere SÓ por `m.falou(conversa, "sim, pode calcular")`, passa 7/7 — o mérito é da regra nova e de mais nada. 📊 Rodada completa do original (sem `-x`): **5 failed, 2 passed** — falham exatamente os 5 que dependem do disparo (rt2/3/5/6/7; `RT4 pedidos: []`), passam os 2 que não disparam (rt1, rt4) | **FECHADO** |
| B5 | link da aba de quem saiu / vencido / pessoa errada | rt7 (`_depois`): `depois que saiu: mesmo link? False` · `link vencido: a aba devolve o mesmo? False` · `wa.me leva o link morto? False` | **FECHADO** |
| B6 | CPF no `risco` e com espaços | sonda: `'529 982 247 25' -> '***.***.***-25'`, `'529.982.247.25' -> '***.***.***-25'`; `resumo_do_cliente` passa o `risco` pela máscara antes do cinto `\d{6,}` | **FECHADO** |

Testes do produto: 📊 `test_spec132b_o_fio.py` **15 passed** (64 s) · `test_spec132b_a_conversa.py` **28 passed** (19 s) · `test_rt_132b_depois.py` **7 passed** · `test_juiz_132b.py` **2 passed**.

## 2. Regressão procurada

### 🔴 DEFEITO NOVO — o "sim" falado por ÁUDIO nunca confirma (painel e atalho do WhatsApp)

**FATO.** `confirmacao.ler_falas` lê só `messages.content` (`select("id, conversation_id, role, content, created_at")`).
Quando o corretor manda só áudio, a fala gravada é `content = "[Anexo] audio.webm"`:
- painel: `app/api/chat/stream/route.ts:250-256` grava `[Anexo] <nome>`; a transcrição vai para `payload.transcricao`
  (`backend/app/api/chat.py:1208-1229`, gravada antes do turno, linha 1548) — que `ler_falas` não lê;
- atalho do WhatsApp (132-C): `services/atalho/turno.py::gravar_pergunta` grava `[Anexo] audio.ogg` ANTES de chamar
  o turno (a ordem está certa — o "sim" digitado É visto), mas o áudio vira anexo, não texto.

**Reprodução** (`scratchpad/conf132b/sonda.py`, saída em `sonda.log`):
```
'[Anexo] audio.webm' False
audio sim -> False      # confirmou_depois([{id:"2", content:"[Anexo] audio.webm"}], vistas=["1"], …)
```
**Consequência:** o corretor que responde "sim" por voz recebe `sem_sim` → o modelo pergunta de novo → o áudio é
recusado de novo. No atalho do WhatsApp, onde o corretor fala mais do que digita, a cotação por voz entra em laço e
nunca calcula. Não chega nada errado ao segurado; o caminho legítimo é que fecha.
**Conserto (uma linha de ideia):** `ler_falas` seleciona também `payload` e usa `payload.transcricao` quando o
`content` é `[Anexo] …`; teste: fala de áudio com `transcricao="sim"` → `confirmou_depois` True; com
`transcricao="não, espera"` → False.

### O que NÃO regrediu
- **"sim" digitado legítimo** (sonda): `sim`, `Sim!`, `pode calcular`, `sim, calcula`, `Pode sim`, `pode mandar`,
  `manda ver`, `ok, pode`, `Sim, pode calcular para mim`, `isso mesmo, calcula`, `beleza, vai`, `confirmo`,
  `sim, sem franquia reduzida mesmo` → **True**. Negações e correções → False (`sim, mas espera`, `pode, mas muda o
  CEP para 01310-100`, `sim, CPF …`). ⚠️ Falsos negativos menores: `claro`, `vamos` → False (o modelo pergunta de novo;
  pendência de vocabulário, não blocker).
- **Atalho do WhatsApp grava antes do turno:** `gravar_pergunta` (insert em `messages`) precede `chamar_o_chat` — o
  "sim" digitado é visto.
- **Máscara de CPF com espaços:** não tocou em `telefone (11) 98765-4321`, `11 98765 4321`, `55 11 98765 4321`,
  `protocolo 2024 1015 3321 7`, `calculo 123 456 789 01` (DV inválido), `CEP 01310 100`, `R$ 1.234.567,89`,
  `ano 2021 2022`, boleto, chassi. Mascara um número separado por espaços SÓ se o DV de CPF bate (💭 ~1 em 100
  sequências) — a mesma régua que já valia para o número colado. Aceitável.
- **Renovação / canal / carteira:** nenhum arquivo de renovação ou canal no diff. `montar_proposta` só muda com
  `ajuste_calculo_id`; `apolice_com_prova` só roda em `publicar_cotacao`; `render_cotacao` só serve `e_venda`
  (`origem != "canal"`). Zero byte nas três.

## 3. PENDÊNCIAS (não bloqueiam)
- P1 · frase da economia agora diz "prêmio líquido da sua apólice atual … sem o IOF". INFERÊNCIA: o CLI
  `comando_proposta` com `--atual` (prêmio DECLARADO) num pedido `servico="cotacao"` cairia em `render_cotacao` e
  afirmaria "apólice / líquido" para um número dito. Caminho de operador, não da conversa — conferir ou condicionar a
  frase a `apolice_atual.origem == "documento"`.
- P2 · vocabulário do "sim": `claro`, `vamos`, `com certeza` não confirmam.
- P3 · o modelo que chama `cotacao_preparar` de novo DEPOIS do "sim" (re-prepara) põe o "sim" em `falas_vistas` e o
  disparo ouve `sem_sim` — o corretor teria de dizer "sim" outra vez (atrito, não dano).

## 4. CONFIANÇA
Alta para os 6 blockers (reprodução + controle). Média-alta para a regressão de áudio: medida na função pura com a
forma de fala que o BFF e o atalho gravam (lida no código), não num turno de ponta a ponta com áudio real.
Não medido: turno real com modelo encadeando preparar→disparar.

**NOTA 82/100.**
