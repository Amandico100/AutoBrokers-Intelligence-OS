# Retomada da LEVA 5 — como continuar sem perder trabalho

> **Escrito em 15/08/2026, antes de começar**, porque o Founder avisou que os
> tokens da janela acabariam no meio. Este arquivo existe para que a próxima
> sessão continue de onde esta parar, sem refazer o que já ficou pronto.

## O estado durável é o SISTEMA DE ARQUIVOS — não a minha memória

```bash
cd backend/scripts/destilacao_max

# ⚠️ ANTES DE TUDO — NORMALIZE O NOME. Os subagentes gravam
#    `lote_004.jsonl.destilado.jsonl` (com o .jsonl no meio) e o laço abaixo
#    procura `lote_004.destilado.jsonl`. Sem esta linha ele reporta trabalho
#    PRONTO como pendente e manda refazer. Aconteceu na onda 1.
for f in lotes_v2/lote_*.jsonl.destilado.jsonl; do
  [ -e "$f" ] || continue
  mv -n "$f" "${f%.jsonl.destilado.jsonl}.destilado.jsonl"
done

# O QUE FALTA (a fila de trabalho, sempre atual):
for f in lotes_v2/lote_*.jsonl; do
  case "$f" in *destilado*) continue;; esac
  [ -f "${f%.jsonl}.destilado.jsonl" ] || echo "PENDENTE $f"
done

# O QUE JÁ FOI FEITO:
ls lotes_v2/*.destilado.jsonl | wc -l
```

**Um lote com `.destilado.jsonl` ao lado está pronto.** Sem ele, não está. Não
há estado em lugar nenhum além disso — de propósito.

## O ponto de partida, medido em 15/08/2026 04:5x UTC

```
lotes brutos em lotes_v2/ ......... 72
já destilados ..................... 16   (ONDA 1 — lotes 001, 004-018)
pendentes ......................... 56   (002, 003 e 019-072)
sessões de cliente pendentes ... 2.568   (1.314 Resulta + 1.254 AutoFleet)
cartas no RAG hoje ............. 18.400   (17.458 publicadas)
```

## A ordem que NÃO pode ser trocada (SPEC-071 BLOCO 8)

```
1. SEPARAR      cliente × seguradora   ✅ FEITO — commit b490ca6
2. CLASSIFICAR  ramo + serviço          (o subagente faz, por conversa)
3. AGRUPAR      juntar o que diz o mesmo
4. TRIAR        lixo sai; o que o acervo já tem sai
5. DESTILAR     por grupo, nunca por sessão
6. JULGAR       juiz crítico — só passa o que melhora
7. ENCAMINHAR   playbook · carta do RAG · mapa do Atlas · descarte
```

⚠️ O passo 1 **não existia no código** e foi corrigido em `b490ca6`: 📊 191
sessões de robô já tinham sido destiladas antes disso (Casas Bahia e uma
clínica médica incluídas).

## O que cada peça faz

| arquivo | papel |
|---|---|
| `BRIEFING-SUBAGENTE.md` | **o contrato do destilador** — leia inteiro antes |
| `PROMPT-DESTILADOR.md` | o prompt de conversa de cliente |
| `PROMPT-DESTILADOR-SEGURADORA.md` | o de conversa de URA (vira mapa, não carta) |
| `lotes_v2/lote_NNN.jsonl` | entrada: uma conversa por linha, já mascarada |
| `lotes_v2/lote_NNN.destilado.jsonl` | saída: uma linha JSON por conversa |
| `aplicar.py` | grava o destilado no banco |
| `conferir_indice.py` | confere antes de aplicar |

## As regras que valem mais que a velocidade

**O RAG é GLOBAL** — de todas as corretoras, não da Resulta nem da AutoFleet
(`docs/canon/O-ATLAS-E-UM-SO-E-E-DE-TODAS.md`). Nenhuma carta pode conter nome
de corretora, de atendente ou dado de cliente. O que personaliza é o dashboard.

**Prefira zero a encher.** Fato genérico demais ocupa o lugar da carta que
resolveria o caso. `fatos_reutilizaveis: []` com o motivo em `flags` é uma
resposta legítima e boa.

**`seguradora` é o campo mais perigoso.** Só preencha quando ela aparecer
explicitamente. Uma regra da Porto atribuída à Allianz faz o agente mentir para
o segurado com confiança.

## Como retomar, em três comandos

1. Rode o laço acima para achar os pendentes.
2. Para cada bloco de 3 lotes pendentes, um subagente **Opus 5, esforço high**,
   com o `BRIEFING-SUBAGENTE.md` inteiro no prompt.
3. Ao fim de cada onda: um **juiz crítico, esforço max**, que NÃO destilou,
   lendo uma amostra dos destilados contra as conversas originais.

**Commite depois de cada onda.** Lote destilado e não commitado é o único jeito
de perder trabalho aqui.

## O que ficou pendente de decisão do Founder

- As **3 cartas** que dizem *"sistema Bradesco Autofleet"*: é um sistema real da
  Bradesco ou o destilador colou o nome da corretora num fato da seguradora?
- As **276 versões `superseded`** de `ura_maps` com 2.287 CPF: limpar ou apagar.
- `INSURER_DISPATCH_LIVE=true` no ambiente contra a regra R1 (P-168).
