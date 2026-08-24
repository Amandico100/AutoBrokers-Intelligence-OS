# A LICENÇA DE AUTONOMIA — SPEC-085, da FASE 1 até o fim

> **Cole no chat da execução.** 24/08/2026 · FASE 0 conferida no banco, não no relatório.

---

# A FASE 0 passou. Conferi no banco, não no seu relatório.

```
work_runs.unblock_state + CHECK dos 5 estados      ✅
work_steps.output_redacted                          ✅
work_runs_travamento_idx (parcial, por company_id)  ✅
🔴 POLICIES em work_runs / work_steps / work_events ✅  2 cada
0 de 2.656 runs tocados                             ✅
```

🔴 **Três coisas que você fez e que eu não tinha pedido, e as três estão certas:**

1. **Estendeu `work_runs` em vez de criar tabela.** `CLAUDE.md` §5 respeitado sem cobrança.
2. **O `COMMENT` do `output_redacted` guarda o PORQUÊ** — *"NUNCA é lido pela restauração: quem restaura lê `output_summary`"*. 🔴 **Isso é a armadilha nº 2 da SPEC virando defesa permanente no schema.** Quem mexer daqui a seis meses vai ler antes de errar.
3. **"Não declaro suíte verde. Ela tem um vermelho, e ele é verdadeiro."** É a frase que separa relatório de propaganda.

E o achado do commit — **o corredor voltava MUTADO de cada rodada** — é da mesma família que quase foi a produção na SPEC-084. **Você pegou sozinho.**

---

# 🔴 E AGORA A REGRA QUE MUDA COMO VOCÊ TRABALHA DAQUI ATÉ O FIM

**Você parou depois da FASE 0 e fez três perguntas. Duas delas você podia ter decidido.**

⛔ **Isso não se repete. Você vai da FASE 1 até o BLOCO G sem parar.**

## A conta que você roda ANTES de considerar perguntar

```
① O TESTE DO PRODUTO (§1 do protocolo)
   muda um byte que chega ao SEGURADO, à CORRETORA, ao BANCO ou à SEGURANÇA?
   NÃO  →  PENDÊNCIA. Registra com o que destrava, e SEGUE.

② É uma das OITO condições de parada do CLAUDE.md §10?
   (perda de dados · decisão comercial · conflito canônico · P0/P1 de segurança
    ou cross-tenant · ação física do Founder · mudança material de escopo ·
    custo extraordinário · falta de acesso)
   NÃO  →  não é motivo de parada. Nenhum.

③ Precisa da MÃO do Founder — variável de ambiente, QR, senha, pagamento,
   decisão de preço?
   SIM  →  🔴 ANOTA NA CAIXA DO FOUNDER (abaixo) e SEGUE. Ele resolve em
           paralelo, e o seu próximo bloco não depende disso.
```

> 🔴 **Você só para se ①, ② E ③ derem "sim" — e ainda assim só se, sem aquilo, o próximo bloco for IMPOSSÍVEL, não apenas incômodo.**

## 🔴 A REGRA DOS 30 MINUTOS — para tudo que aparecer fora do bloco atual

```
achado fora do bloco em que você está:

  conserta em ≤ 30 min  E  toca no máximo 2 arquivos  E  não precisa de desenho?
      →  CONSERTA, e escreve uma linha no relatório dizendo que foi fora de escopo

  qualquer outra coisa
      →  PENDÊNCIA, com: o que é · o que destrava · de quem é (🧑 ou 🤖) ·
         e o que custa esquecer

⛔ Se o conserto exige DECIDIR algo (qual formato, qual tabela, qual ordem),
   ele não cabe nos 30 minutos. É pendência. Sem exceção.
```

⚠️ **O critério não é "é importante?" — quase tudo é.** O critério é **"cabe agora sem me tirar do bloco?"**

## 📋 A CAIXA DO FOUNDER

Abra uma seção no relatório chamada **`PARA O FOUNDER`** e vá **acrescentando linhas** à medida que aparecerem. **Nunca pare para entregar uma.** Eu entrego a caixa inteira a ele de uma vez, no fim.

Cada linha: **o que é · o que ele precisa fazer · o que custa esquecer · bloqueia a execução? (quase sempre NÃO)**

---

# As suas três perguntas, respondidas — e as três eram para você seguir, não parar

### 🔴 P-227 · `INSURER_DISPATCH_LIVE` duplicada com valores opostos

**Vai para a CAIXA DO FOUNDER. Ele apaga a linha hoje. ⛔ Não bloqueia você.**

**Por quê:** os quatro agentes `attendance` estão `is_active=false`. A trava nº 1 da cadeia segura sozinha, e você não vai ligar nenhum. **Você segue.**

⚠️ **Mas você acertou em gritar** — duas variáveis com valores opostos é o pior estado possível: **o comportamento passa a depender de qual delas a plataforma escolhe.** Isso é P1 de configuração, e é exatamente o que a caixa existe para carregar.

### 🔴 P-231 · `test_duas_medicoes_nao_se_atropelam` vermelho na quarentena

**Você já consertou o vazamento na FASE 0.** O que falta é o guarda que pega o próximo. **Faça-o no fim da FASE 1, com teto de 30 minutos.**

**Por quê no fim da FASE 1 e não agora:** a FASE 1 mexe no que o corredor grava. **O guarda protege exatamente isso, e vale mais depois do trabalho do que antes.**

⛔ **E o teto é literal:** se em 30 minutos ele não fechar, **volta para a quarentena com o diagnóstico escrito** e você segue para o BLOCO A. **Um guarda é ferramenta, não destino.**

### ✅ P-228 · a régua devolvendo 102/100

**Já estava decidido no alinhamento: é BLOCKER, e é da SPEC-089.** ⛔ **Não toque nisso durante a 085.**

---

# ⚠️ E uma decisão que eu preciso que você tome agora, porque é sua

Você pôs **`pytest tests/` inteiro** no `gate.yml` — melhor do que eu tinha feito. Mas ele está **`1 failed`**.

> 🔴 **Um gate permanentemente vermelho ensina todo mundo a ignorar o gate.** É o `CLAUDE.md` §9.3 pelo avesso: um guarda que está sempre vermelho não guarda mais que um que nunca falha.

**Faça uma das duas, e escreva qual e por quê:**

```
(a) o vermelho é asserção vencida ou defeito conhecido
       →  entra na quarentena com o motivo, e o gate fica VERDE E VERDADEIRO

(b) o vermelho é defeito de produto que a 085 conserta
       →  fica vermelho, e o relatório diz em qual bloco ele fecha
```

⛔ **O que não vale é deixar como está sem dizer qual dos dois é.**

---

# Como você trabalha da FASE 1 até o G

```
FASE 1    o mascarador          ← você já mapeou os campos. Vai.
          + P-231, teto 30min, no fim
BLOCO A   o estado diz a verdade
BLOCO B   os três caminhos de handoff (o C é o que nunca fala)
BLOCO C   o segurado ouve a verdade
BLOCO D   a retomada, as 16 famílias
BLOCO E   a tela que destrava — SOMANDO ao Redis, nunca substituindo
BLOCO F   os dois vigias se encontram
BLOCO G   a prova, pelos caminhos B E C, com a linha de controle
```

## 🔴 O painel, uma vez, no fim — não a cada bloco

⛔ **Não chame juiz a cada bloco.** Termine **todos** os blocos, e então:

```
as QUATRO LENTES da §7 DA SPEC, DE UMA VEZ, CEGAS ENTRE SI
  → você funde e aplica o TESTE DO PRODUTO a cada achado
  → conserta tudo junto
  → UM juiz novo confirma
🔴 teto: 3 rodadas de painel. Bateu → classifica e entrega.
```

📊 **O motivo é medido:** na escrita desta SPEC eu rodei um juiz genérico três vezes, em série, e dois juízes de contexto limpo acharam coisas **quase inteiramente diferentes** — sobreposição praticamente zero. **Uma passada de quatro lentes vale mais que três passadas de uma.**

## E o verificador mecânico, esse sim, a cada bloco

```
pytest tests/  ·  e se tocou app/: npm run test:rotas-montam + next start + /api/…
```

---

## ⛔ As travas, sem uma vírgula de mudança

```
⛔ agentes attendance DESLIGADOS · INSURER_DISPATCH_LIVE FECHADO
⛔ só AMANDUS nos ensaios · a AUTOFLEET é a única pareada de verdade
⛔ nenhuma mensagem sai · nenhuma entrada em portal
⛔ só SELECT fora das migrations desta SPEC
⛔ nunca CPF, telefone, apólice, placa ou nome em resposta nenhuma
```

---

> ## 🔴 O resumo, numa linha
>
> **Vá da FASE 1 ao BLOCO G sem parar. Decida com a conta, anote o que não couber, junte o que for do Founder numa caixa só — e me chame quando o BLOCO G estiver fechado, não antes.**
>
> Se algo genuinamente impossível aparecer, você vai saber: **é quando as três perguntas derem sim e o próximo bloco não puder começar.** Aí você para, e ninguém vai reclamar.
