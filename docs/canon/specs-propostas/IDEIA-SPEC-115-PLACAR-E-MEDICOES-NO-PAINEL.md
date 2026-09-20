# 💡 IDEIA · SPEC-115 · O PLACAR — as medições moram no painel, não em três lugares soltos

> **Isto não é uma SPEC.** É um lembrete registrado, no mesmo estilo das 099–114
> (`INDICE-DE-SPECS.md`). Decisão do Founder de 20/09/2026: **depois da 114**.

## O problema — a medição existe, mas espalhada em três lugares

```
1. o resumo das 19h no grupo do WhatsApp        (EXTRA-001.3) — some na conversa
2. `backend/scripts/medir_o_piloto.py`          (EXTRA-001.7) — só quem tem terminal lê
3. os relatórios do painel                      (095/094)     — não guardam histórico por dia
```

Quem quer saber "a semana foi melhor que a passada?" hoje não tem onde olhar. E
cada lugar conta com um caminho próprio, que é como nasce número que discorda de
número.

## O estado desejado — uma área **Placar** no painel de cada corretora

```
· histórico GRAVADO por dia, numa tabela nova por `company_id` (RLS + filtro no código)
· escrita por UMA rotina diária que chama o MESMO motor de hoje:
  `contagens_do_dia` (resumo das 19h) e `medir_o_piloto` — nunca um contador novo
· as NOTAS por dimensão da régua 0–100, com "NÃO AVALIADA" preservado, nunca zero
· cobrança · renovação · cotação · tempo economizado · dinheiro recuperado
· comparação com o período anterior, e o mesmo número que o WhatsApp mandou às 19h
```

## O que falta antes — os escritores

As dimensões sem fonte durável continuam sem nota enquanto ninguém gravar o fato:
**P-E0017-03** (apólice certa em 1 rodada · fala como humano · sabe calar),
**P-E0017-04** e **P-E0017-05**. O Placar mostra o que existe; ele não inventa fonte.

## ⛔ O que NÃO fazer

```
⛔ um segundo contador ao lado do motor de hoje — é motor paralelo (CLAUDE.md §5)
⛔ nota calculada na tela: a tela LÊ a linha gravada, não recalcula
⛔ nome de corretora, de atendente ou PII na tabela do placar (CLAUDE.md §13.9)
```

## Quando

Depois da **SPEC-114**, por decisão do Founder de 20/09/2026 — a sequência de
produto (vidros, isolamento, renovação, cotação) vem antes.
