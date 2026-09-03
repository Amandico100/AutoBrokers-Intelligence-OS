<!-- HISTÓRICO: anterior à v11 do protocolo (03/09/2026). Não é pacote vivo; os pacotes vivos estão em docs/canon/pacotes/. -->
# SPEC-093 — para o chat que já executou a 085 e a 092

> **Cole isto no MESMO chat que executou as SPECs 085 e 092.** Ele já conhece o
> sistema; isto é só o que mudou desde então. 💭 ~10 minutos, não 20.
> 25/08/2026 · commit base `0447db3`

---

Você já executou a **SPEC-085** (o travamento vira linha de banco) e a
**SPEC-092** (o formulário nativo dentro do WhatsApp). **Você não precisa
reaprender o produto.** Isto é o delta.

## ⛔ AS TRAVAS — as mesmas de sempre, e continuam valendo

```
⛔ SOMENTE LEITURA até eu liberar a execução. No banco: só SELECT.
⛔ NENHUMA MENSAGEM SAI. Para ninguém, por nenhum canal.
⛔ NENHUMA ENTRADA EM PORTAL DE SEGURADORA.
⛔ É PROIBIDO LIGAR AGENTE DE ATENDIMENTO. Os quatro estão desligados.
⛔ NÃO tocar em variável de ambiente de produção.
⛔ NUNCA imprimir CPF, telefone, apólice, placa ou nome de pessoa.
```

## 🔴 PREFLIGHT — antes de qualquer coisa

```bash
git rev-parse --show-toplevel        # tem de ser AutoBrokers-FIX
git rev-list --count HEAD..origin/main   # 🔴 TEM DE SER 0
git status --short                   # limpo
```

⚠️ **Se o topo não for `AutoBrokers-FIX`, pare.** Existe uma cópia velha
(`AutoBrokers-Opus-Exec`) 208 commits atrás, com um `CLAUDE.md` de 25/07.

## O QUE MUDOU DESDE A SPEC-092

```
docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md    🔴 releia — mudou hoje
docs/canon/specs/SPEC-093-o-atendimento-real-liga-e-funciona.md
```

📊 **Três coisas novas no protocolo, e elas mudam como você trabalha:**

1. **A bateria ficou 26% mais rápida** (16m10 → 12m41 de média). Os guardas
   rodam em paralelo agora. ⚠️ **E `test_a_arvore_ficou_limpa_no_fim` fica
   vermelho de vez em quando por vazamento de mutação (P-246) — é conhecido,
   não é defeito seu, e a árvore termina limpa porque a rede restaura.**

2. **`backend/tests/conftest.py` conta as rodadas.** 🔴 **O relatório final desta
   SPEC TEM de trazer o número** — a query está no template. É o passo 2º do
   protocolo, e ninguém nunca mediu.

3. ⛔ **NUNCA `git add -A`.** 📊 Hoje isso levou uma mutação de `rubrica.py`
   para dentro de um commit — **pela segunda vez** (P-247). Adicione arquivo por
   arquivo.

---

# 🔴 A REGRA QUE VALE MAIS QUE TODAS — e você já a conhece

> **📊 = MEDIDO** · **💭 = ILUSTRATIVO**

E o motivo, atualizado com o que aconteceu hoje:

> **Três lentes independentes revisaram a proposta de SPEC-086 (52 KB, escrita
> por outro modelo). Elas acharam que ela declarava como "fundações existentes a
> reusar" três coisas que 📊 têm 0, 1 e 4 linhas no banco.**
>
> 🔴 **A SPEC-093 foi escrita por mim, com os mesmos olhos. Presuma que ela
> também erra.**

## As oito perguntas

⚠️ Algumas têm resposta óbvia **E ERRADA**, de propósito.

**1.** 📊 `company_members`: quais papéis existem e quantas pessoas em cada um?
🔴 Que papel a Regina e a Saionara precisam ter **hoje** para apertar o botão de
ligar o agente?

**2.** 🔴 **A allowlist de entrada.** O que acontece com um telefone fora dela?
`arquivo:linha`. **E quem MAIS lê essa variável no produto?**
⚠️ *Esta segunda parte é a que separa quem mediu de quem leu.*

**3.** 📊 Com o agente **desligado**, o que acontece com a mensagem? E **ao
religar**, com as que chegaram no intervalo?

**4.** 🔴 **O clique da atendente.** Quando uma pessoa responde pelo WhatsApp da
corretora e o corredor segue, **o produto registra que foi um humano?** Prove
pelo dado.

**5.** Para **Vigia**, **Sentinela** e **Cérebro**: 📊 quantas vezes cada um já
destravou um acionamento? ⚠️ *Um dos três não deixa rastro em banco. Qual?*

**6.** 📊 **`work_effects` é a autoridade de efeitos externos deste produto.**
Confirme ou refute, com o número.

**7.** 📊 **Ligar um corredor na tela de Corredores liga o canal e passa a
enviar mensagem para a seguradora.** Confirme ou refute, com `arquivo:linha`.

**8.** 🔴 **Ache um defeito real que a SPEC-093 não aponta**, com evidência.
⚠️ *"Procurei em X, Y e Z e não achei" também é resposta.*

---

## COMO RESPONDER

- **Evidência em cada resposta**: `arquivo:linha`, a consulta SQL, ou a saída.
- **FATO** (medi) separado de **INFERÊNCIA** (deduzi).
- 🔴 **DUAS DAS OITO AFIRMAM ALGO FALSO**, assinado por quem te dá a tarefa.
  Ache-as e refute **com o número**. **É exatamente esse o teste.**

## Depois

Você manda as oito respostas. Eu corrijo o que estiver torto, e **aí você executa
a SPEC-093 do começo ao fim, sem parar** — na ordem `E → A → B → C → D → G → F`.

> 🔴 **Quando a SPEC disser algo que você mediu diferente, a SPEC está errada até
> prova em contrário.** Meça, mostre o número, e devolva.
