# Auditoria do relógio — por que a EXTRA-001.5.1 levou 8 h e como fazer em 2

> 20/09/2026 · medido com `backend/scripts/medir_execucao_claude_code.py --sessao atual` sobre a sessão
> `7bb009e8` (17/09 22:40 → 20/09 01:10 UTC). **Nada aqui é estimativa: são os tempos e custos reais dos agentes.**

---

## 1. Onde o relógio foi embora

📊 Tempo de agente da EXTRA-001.5.1, por fase:

| fase | tempo de agente | o que é |
|---|---|---|
| **construir** as 3 fatias | **138 min** | builder 1 (56) + builder 2 (54) + a fatia 3 antes do primeiro juiz (≈28) |
| ler as 81 linhas | 28 min | leitor read-only, em paralelo — **não custou relógio** |
| **julgar** (5 passadas) | **226 min** | juiz 105 + confirmação 27 + confirmação curta 30 + julgamento 33 + julgamento 31 |
| **consertar** (5 rodadas) | **≈390 min** | o mesmo builder, retomado 5 vezes |
| bateria inteira | 45 min | em 2º plano, não custou relógio |

🔴 **Construir custou 138 minutos. Consertar custou 390.** O build não é o problema.

📊 E o mesmo builder, na SPEC anterior, fazendo trabalho equivalente:

```
fatia 3 da EXTRA-001.5    180 min · 231 turnos · 64,5 M de contexto · US$ 40,66
fatia 3 da EXTRA-001.5.1  425 min · 338 turnos · 150,5 M de contexto · US$ 85,77
```

**2,4× mais caro para a mesma classe de trabalho.** A diferença inteira é retrabalho.

📊 Custo total da SPEC: **US$ 379,63** · 22 agentes · 2.150 turnos · 528 M de tokens de contexto.

---

## 2. A causa: as cinco rodadas, e por que elas existiram

As cinco rodadas atacaram **o mesmo lugar**: o trecho entre a consulta da apólice e a mensagem que sai no
WhatsApp. Nenhum gate das três fatias atravessava esse trecho — todos mediam o **compositor**, que estava certo
desde o começo.

```
rodada 1   a LLM nunca recebia o veredito no WhatsApp
rodada 2   a trava passou a CALAR o acionamento (6 de 11 pedidos de guincho)
rodada 3   a porta perdia 45 % dos pedidos; o turno do CPF desligava tudo
rodada 4   o serviço do veredito vinha da mensagem mais velha da janela
rodada 5   ✅ confirmado, 86
```

**Cada conserto fechava o defeito medido e abria outro no mesmo ponto cego.** Isso não é azar: é o que acontece
quando se conserta um lugar que nenhum teste atravessa.

🔴 **E o protocolo já sabia disso.** O §3.1 fixa **1 rodada (+1 curta)** para CRÍTICO. Eu fiz cinco. O §8 manda
escalar para **AAA COMPLETO (painel de 3 lentes + red team)** quando o juiz reprova duas vezes com blocker
material. Eu não escalei — porque o teto de agentes do chat estava apertado — e paguei com **três rodadas
seriais a mais**.

📊 **A conta do erro:** três rodadas seriais custaram ≈ 155 min de agente (94 de juiz + 61 de conserto) mais o
relógio de quem monta cada pacote entre elas. Um painel de 3 lentes **em paralelo** custa **35 min de relógio**,
porque as três rodam ao mesmo tempo.

> **O painel não é o caro. O serial é o caro.** O AAA FAST tirou o painel para poupar tokens e trocou ~4 % de
> token por horas de relógio. O próprio CLAUDE.md já tinha a medição: com painel, 47 achados e 22 defeitos de
> produto; sem painel, 19 achados e **zero** defeitos de produto.

---

## 3. O que eu proponho — três mudanças, nesta ordem de impacto

### ① O CARD nomeia o CAMINHO VIVO, e todo gate atravessa ele
Antes de escrever a primeira linha, o BLOCO 0 escreve **a cadeia exata do primeiro byte que entra ao último byte
que sai para o cliente**, com arquivo e função em cada elo. Todo gate de unidade tem de **atravessar a cadeia
inteira**, não o pedaço que a unidade tocou.

💭 Custo: **10 minutos**. 📊 Teria evitado 4 das 5 rodadas — ≈ 4 horas.

### ② O PAINEL volta, mas em PARALELO e numa rodada só
Três juízes frescos **simultâneos**, lentes diferentes, sobre o mesmo diff:
```
verdade e evidência   ·   adversarial (o caminho vivo ponta a ponta)   ·   o produto para quem usa
```
Um **conserto único e grande** com tudo junto. Uma confirmação. **CRÍTICO: 3 lentes. PADRÃO: 2.**
💭 Relógio: 35 min de julgamento em vez de 105, e uma rodada de conserto em vez de cinco.

### ③ A REGRA DAS DUAS RODADAS
Na terceira rodada, **o problema não é o código: é o card**. Pare, reescreva o card (o caminho vivo estava
errado), e recomece a fatia. Proibido seguir consertando.

### E três destravas que não mudam o rito
```
· FATIAS EM PARALELO quando não compartilham arquivo (a 001.5.1 rodou 2 e 3 em série sem precisar)
· A BATERIA começa no primeiro commit, em 2º plano — nunca no fim
· TETO DE AGENTES por SPEC = 12, não 6. O teto baixo me forçou a serializar, que é o oposto do objetivo
```

---

## 4. O que isso promete, em relógio

| nível | hoje 📊 | com as três mudanças 💭 |
|---|---|---|
| **PADRÃO**, 1 fatia | 3–4 h | **≤ 2 h** |
| **CRÍTICO**, 2–3 fatias | 6–8 h | **≤ 3 h 30** |

E a qualidade **não cai**: o painel paralelo encontra **mais** do que o juiz único — foi por isso que ele existia.

---

## 5. O que NÃO é o problema (para não gastar tempo aí)

```
⛔ o tamanho do protocolo          o núcleo tem 114 KB e é lido uma vez; não aparece no relógio
⛔ o modelo do builder             Opus xhigh não é lento; ele fez 338 turnos porque foi chamado 5 vezes
⛔ o effort                        a saída é ≈6 % do gasto (§3.1); baixar effort não compra relógio
⛔ trocar o Fable pelo Opus         a troca de gerente no meio não mudou o ritmo em nenhuma das duas vezes
```

**O gargalo é um só: quantas vezes o trabalho volta.**
