# ALINHAMENTO — depois do aquecimento, antes da SPEC-085

> **Cole isto no MESMO chat que fez a auditoria**, junto com
> `docs/canon/specs/SPEC-085-o-destravamento-nao-trava-em-silencio.md`.
> 24/08/2026 · commit `e3686f9`

---

# Você passou. **96/100.** Está liberado para executar.

E o que fez a nota não foi ter acertado as respostas. Foi **você ter achado cinco erros meus — quatro deles em trabalho que eu tinha feito naquele mesmo dia.**

## O que você achou, e o que eu já consertei por causa disso

| você achou | eu consertei |
|---|---|
| 🔴 `pytest tests/` **aborta a sessão inteira** | `conftest.py` com `collect_ignore`. 📊 **De 0 para 322 testes coletados** |
| 🔴 o meu "151" era subconjunto | a regra virou **uma só**: sem `def test_` → roda como processo. **273** |
| 🔴 *"3 das 5 corretoras"* | 📊 **1 de 3.** Duas linhas de `companies` são tenants técnicos, e a Resulta **tem** destino |
| 🔴 o docstring mentindo sobre o próprio conserto | corrigido para o passado, com o aviso maior: **na `origin/main` o passo ainda não existe** |
| 🔴 colisão de numeração na P-183 | eram **quatro**. P-180→**P-223** · P-181→**P-224** · P-182→**P-225** · P-183→**P-226** |

🔴 **E quando os 122 arquivos que você me fez descobrir começaram a rodar, apareceram 28 vermelhos novos.**

```
📊 o vermelho real: 42 de 273 guardas-script (15,4%)  +  6 asserções nos
   arquivos que são pytest de verdade                 =  48
   (a P-226 dizia "14")

✅ depois da quarentena:  233 passed, 42 xfailed in 440s
```

## E um erro meu que você não pegou, mas que a sua medição expôs

🔴 **A máquina de lavar é 19/08, não 18/08.** Eu confundi a **conversa** com o **run**.

📊 É o `work_run` **`e5279497`**, 19/08 16:35–16:41 BRT — o único dos quatro que chegou a `monitoring`, e o único sem `error_code`. A conversa de 18/08 (165 msgs, `Motor de Acionamento`) é **robô × URA**, e corresponde ao `test_aborted`.

**A SPEC foi corrigida. Você tinha razão na sua tabela da resposta 9.**

---

## ⚖️ As duas decisões que você pediu que eu cravasse

### 1 · Os cinco vermelhos da régua: **BLOCKER — e vai para a SPEC-089, não para a 085**

Você deixou as duas leituras e pediu o veredito. **Aqui está, com o raciocínio:**

Pela letra do §1, nota de régua é medição de execução → pendência. **Mas o que a régua decide é se um corredor está bom o bastante, e corredor chega em segurado.** Uma régua que devolve **102 numa escala de 100** e **parou de achar órfã** aprova o que deveria reprovar. **O byte muda: é a rota que sobe sem estar pronta.**

⚠️ **Não é da 085.** É da 083/089, e está registrado com as cinco asserções. **Não conserte isso durante a 085.**

### 2 · O interlocutor das 2 conversas de julho: **é teste**

Sua inferência estava certa e você fez bem em não afirmar. 📊 **O Founder confirmou: tudo até hoje foi teste.** O número honesto da sua resposta 1 é: **o robô nunca teve uma conversa de assistência real com um segurado.** A única travessia completa é o `e5279497`.

---

## 🔴 Três dos seus nove pontos cegos precisam fechar ANTES de você começar

Dos nove que você listou — e listou bem —, **seis podem ficar abertos.** Estes três não:

| # | o seu ponto cego | por que ele é bloqueante |
|---|---|---|
| **1** | *"não sei como a retomada reconstrói uma sessão cujo TTL de 6h venceu"* | 🔴 **é o BLOCO D inteiro.** Você vai desenhar a retomada; sem isso, desenha no escuro |
| **4** | *"li os cabeçalhos dos quatro vigias, não a lógica; não sei se todos rodam"* | 🔴 **é o BLOCO F.** E você mesmo escreveu a frase: *"a diferença entre 'existe' e 'roda' é a que este projeto mais castiga"* |
| **7** | *"os 14 da quarentena — não abri nenhum"* | 🔴 **agora são 42, e seis deles tocam esta cadeia.** Estão marcados na quarentena com `🔴 TOCA A SPEC-085` |

**Feche os três lendo, antes do primeiro commit. Os outros seis** — o portal, o destilador, as `attendance_sessions`, os 72 corredores — **ficam anotados no relatório e não são desta SPEC.**

---

## Como você trabalha a partir daqui

### 🔴 O painel paralelo, não o laço em série

⛔ **Não rode um juiz genérico três vezes.** 📊 Foi o que eu fiz na escrita desta SPEC, e o `PROTOCOLO §6.0.0` existe por causa disso: dois juízes de contexto limpo, o mesmo documento, **sobreposição de achados praticamente zero.**

```
③ AS QUATRO LENTES DA §7 DA SPEC, DE UMA VEZ, CEGAS ENTRE SI
④ VOCÊ funde e aplica o TESTE DO PRODUTO a cada achado
⑤ conserta tudo junto
⑥ UM juiz novo confirma  ← porque conserto cria defeito. Na escrita, dois criaram.
```

### 🔴 E o que você já provou que sabe fazer, e é o que mais importa

> **Quando a SPEC disser algo que você mediu diferente, a SPEC está errada até prova em contrário.**

Você fez isso cinco vezes na auditoria. **Faça de novo, o quanto precisar.** A §4 do protocolo é literal: *"o executor REPRODUZ antes de aplicar — e devolve com o número se não bater."*

⚠️ **E vale nos dois sentidos:** 📊 na volta 3 da escrita, um juiz mediu `fallback_adaptive` por `grep` e achou 138; **carregando o módulo são 228** — parte dos passos recebe a marca em tempo de import. **Contar no texto subestima em 39%.** Quando o número for de marca de passo, **carregue o módulo.**

### As correções do enunciado que você trouxe, todas aceitas

📊 `PENDENCIAS.md` tem **8.592** linhas · são **10** seguradoras com corredor (o enunciado omitia alfa e bradesco) · e o `PROTOCOLO §6.1` diz "230 commits à frente" quando hoje são 12.

> **Sua frase — *"nem um 📊 sobrevive ao dia inteiro"* — está certa, e é por isso que a marca 📊 exige a data junto.** Um número medido é uma fotografia, não uma lei.

---

## ⛔ As travas continuam valendo, sem uma vírgula de mudança

```
⛔ É PROIBIDO LIGAR AGENTE DE ATENDIMENTO. Os quatro estão desligados.
⛔ INSURER_DISPATCH_LIVE fica FECHADO. O ensaio roda em DRY-RUN.
⛔ SÓ AMANDUS nos ensaios. A AUTOFLEET é a única pareada de verdade — não a toque.
⛔ NENHUMA mensagem sai. NENHUMA entrada em portal.
⛔ Somente SELECT, fora das migrations desta SPEC.
⛔ NUNCA CPF, telefone, apólice, placa ou nome de pessoa em resposta nenhuma.
⛔ AVISE O FOUNDER antes de qualquer coisa que envie, ligue ou publique.
```

**Você respeitou todas na auditoria. Continue.**

---

## E a última coisa, que é a que me deixa confortável em te entregar isto

Na sua resposta 15 você escreveu:

> *"O único corredor que vi funcionar de verdade foi allianz-residencial × máquina de lavar, uma vez. Sobre os outros 72 eu não tenho medição nenhuma — e nem este repositório tem."*

🔴 **É a frase mais correta do documento inteiro, e é a régua com que você deve julgar tudo o que a SPEC te mandar fazer.**

**Agora leia a SPEC-085. Boa execução.**
