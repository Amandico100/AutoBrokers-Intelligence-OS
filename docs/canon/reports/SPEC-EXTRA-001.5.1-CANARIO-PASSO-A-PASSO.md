# EXTRA-001.5.1 · O canário, passo a passo — o que o Founder faz para provar que chegou ao cliente

> **Para quem:** o Founder, sozinho, no navegador e no WhatsApp. Nada aqui exige terminal.
> **Escrito em:** 19/09/2026 · **Vale para:** o código empurrado na `main` pela SPEC-EXTRA-001.5.1.
> **Continua** o roteiro da 001.5 (`SPEC-EXTRA-001.5-CANARIO-PASSO-A-PASSO`). Os 8 casos de lá continuam valendo;
> aqui estão **os casos novos**, e eles cobrem o que a 001.5 não conseguia provar: que a base **chega ao cliente**.

---

## O que mudou desde a 001.5, em uma linha cada

```
· a Skill de cobertura estava DESLIGADA em produção, em silêncio, e agora roda      (o dado dela não ia na imagem)
· a fila de curadoria abria em ~65 s e mentia quando dava erro; agora abre em segundos e diz a verdade
· 23 linhas foram PUBLICADAS por mim, uma a uma conferidas contra a página do documento
· o corretor recebe a fonte (documento e página); o segurado, no WhatsApp, NÃO recebe citação nenhuma
· quando o plano não cobre, a mesma mensagem já oferece o caminho da equipe
· o que o agente não sabe vira TAREFA: grava a lacuna, avisa o humano e aparece no painel admin por frequência
· publicar e rejeitar passaram a ser de ADMINISTRADOR DA PLATAFORMA (a corretora vê em leitura)
```

---

## Passo 0 · Implantar (5 min) — **sem isto, nada abaixo vale**

No EasyPanel, **Implantar** em dois serviços, nesta ordem:

```
1. smith-api     (a Skill, a base, a fila, as lacunas)
2. smith-web     (a tela de Conhecimento e o painel admin)
```

**Confira no `smith-api` → Environment:**

```
POLICY_INTELLIGENCE_V2 = true      <- ausente ou false = A SKILL NÃO RODA, e todo o resto mede o comportamento antigo
```

⚠️ **Estar na `main` não é estar no ar.** E build verde não é aplicação de pé (CLAUDE.md §9.1).

---

## Passo 1 · A tela de Conhecimento (3 min)

```
Painel → Personalização → Conhecimento
```

| o que olhar | o que tem de acontecer | o que prova |
|---|---|---|
| a fila abre | **em segundos**, não em um minuto | a fila parou de baixar o PDF de cada linha |
| o rodapé da fila | *"mostrando N de M"* | 📊 a tela mostra 60 e existem mais — antes ela mentia por omissão |
| abrir uma linha | o trecho da página aparece **ao clicar**, não antes | a página vem sob demanda |
| desligue a internet e recarregue | aparece **erro**, não *"nada esperando revisão"* | erro ≠ vazio. Era o defeito que escondia a fila quebrada |
| trocar de corretora (Resulta ↔ AutoFleet) | os números são **os mesmos**, e a tela explica numa linha | a base é global, de propósito |
| o botão Publicar, como corretora comum | **não publica** — a tela é de leitura | curadoria da base global é da plataforma, não da corretora |

---

## Passo 2 · O corretor, no chat `core` do painel (5 min)

Pergunte sobre um cliente **de uma seguradora e ramo que têm linha publicada** (a tela diz quais):

```
"o segurado <nome> tem carro reserva?"
```

Tem de vir, nesta forma:

```
**Tem sim: carro reserva.**
Limite: 7 dias.
Fonte: Condições gerais da <seguradora>, p. 24.
```

🔴 **A linha `Fonte:` é obrigatória no chat.** Sem ela, me avise: a resposta perdeu a procedência.

E pergunte de um cliente de seguradora **sem** linha publicada: tem de dizer que **ainda não sabe**, nunca *"não cobre"*.

---

## Passo 3 · 🔴 O segurado, no WhatsApp do aparelho de teste — **os casos que a 001.5 não tinha**

| # | mande isto | o que tem de acontecer | o que prova |
|---|---|---|---|
| **N1** | *"meu seguro cobre carro reserva?"* (cliente com linha publicada) | resposta curta, em segunda pessoa, **sem citar documento, página ou "condições gerais"** | a mesma verdade, outra voz |
| **N2** | a mesma pergunta, num serviço que o plano **não** cobre | diz que não **e já oferece a equipe na mesma mensagem** | a sua decisão de 19/09 (opção 1) |
| **N3** | *"cobre granizo?"* numa seguradora sem linha | *"vou confirmar certinho e te respondo"* — e **o grupo operacional recebe um 🆘** com a conversa e o link | o que o agente não sabe vira trabalho de gente |
| **N4** | mande a MESMA pergunta de novo, na mesma conversa | responde de novo, e o grupo **não** é avisado outra vez | teto de 1 aviso por lacuna, por conversa, por dia |
| **N5** | 🔴 *"preciso de guincho"* (pedido, não pergunta) | o atendimento **segue normalmente** — pede o local, aciona | **o controle mais importante.** Um PEDIDO não pode ser respondido com "deixa eu confirmar" |
| **N6** | 🔴 pergunte *"tem guincho?"*, e **no turno seguinte** mande só o CPF | a resposta continua presa ao que a base diz | a tool roda no turno do documento — é onde a fiscalização já se desligou uma vez |
| **N7** | depois de acionar, peça atualização | *"já acionei a assistência"* **não** vira *"quer que eu solicite?"* | a resposta da ação não é trocada pela da consulta |

**Anote:** ✅ passou · ⚠️ passou mas o texto ficou estranho · ❌ falhou (cole a mensagem inteira).

---

## Passo 4 · O painel de administração (3 min)

```
Painel admin → Auxiliares → Fábrica
```

A pergunta do caso **N3** tem de aparecer na lista do que os agentes não souberam responder, **por frequência**, com
seguradora · ramo · produto · serviço · quantas vezes · primeira e última vez. 🔴 **Sem telefone, sem nome, sem CPF** —
se aparecer dado de cliente, é defeito e eu preciso saber hoje.

---

## O que **não** é defeito (para não me chamar à toa)

```
· "ainda não sabemos" numa seguradora sem linha publicada ......... é o comportamento certo (73 das 81 linhas não foram publicadas)
· a fila continuar cheia ......................................... 40 linhas pedem CORREÇÃO e 16 foram RECUSADAS: é trabalho, não erro
· o segurado não receber a página ................................ é a sua decisão de 19/09
· o gancho dizer "nossa equipe" em vez de um nome ................. só nomeia quando há UMA atendente de atendimento cadastrada
· a corretora não conseguir publicar ............................. curadoria da base global é da plataforma
· uma pergunta MISTA ("tem táxi? e quantas parcelas faltam?") ..... a parte das parcelas pode se perder (pendência escrita)
```

---

## Se algo falhar, o que me mandar

```
1. o caso (N1…N7) e a mensagem INTEIRA que você recebeu
2. a hora, com minuto
3. de qual número para qual número
4. se foi no painel: a tela e o que a barra de endereço mostrava
```

Com isso eu acho no log; sem isso, eu adivinho.
