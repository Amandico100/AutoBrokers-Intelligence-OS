# SPEC-084 — A FÁBRICA DE ROTAS

> **Levar as 62 rotas ao nível da máquina de lavar — uma de cada vez, na ordem que a árvore da URA impõe, e nenhuma liberada sem o juiz.**
>
> Autor: execução · **v1, 21/08/2026** · Commit base: `bae33ea`
> Branch: `feat/spec084-a-fabrica-de-rotas`
> Depende de: **SPEC-083 (A Régua)** — sem a régua, esta SPEC não tem como saber se terminou

---

## 0. PREFLIGHT OBRIGATÓRIO

```bash
git rev-parse --show-toplevel      # AutoBrokers-FIX
git branch --show-current          # feat/spec084-a-fabrica-de-rotas
git rev-parse HEAD                 # registrar no relatório
git status --short                 # LIMPO ao iniciar
```

**Pré-condição absoluta:** a SPEC-083 tem de estar **fechada e verde**. Sem `medir_rota.py`, sem o corpus e sem o gate de replay, esta SPEC não tem instrumento — e trabalho sem instrumento vira opinião.

```bash
python backend/scripts/medir_rota.py --seguradora allianz --ramo residencial --servico maquina_de_lavar
# tem de responder com a nota e os 3 itens que faltam. Se não responder, PARE.
```

Leitura obrigatória, além do `CLAUDE.md` inteiro:

1. **`docs/canon/specs/SPEC-083-a-regua-do-corredor.md`** — a régua, a rubrica, os `DECIDE:`. Esta SPEC não redefine nada disso.
2. `docs/canon/O-ATLAS-E-UM-SO-E-E-DE-TODAS.md` — o Atlas é um só, de todas.
3. `docs/canon/O-ATLAS-E-PARA-QUEM-ESCREVE-O-CORREDOR.md`
4. `docs/canon/GLOSSARIO.md`

---

## 1. POR QUE ESTA SPEC EXISTE

📊 O produto tem **62 rotas** (seguradora × ramo × serviço) e **uma** validada em produção: `allianz × residencial × maquina_de_lavar`, protocolo 52955490, 19/08/2026, 5min55 do "oi" ao protocolo.

📊 A distância entre ela e o resto, medida pelo replay contra as telas reais:

```
allianz-residencial / maquina_de_lavar   respondidas=20   órfãs= 7
allianz-residencial / chaveiro           respondidas=11   órfãs=16   ← MESMO corredor
mapfre-auto  / guincho                   respondidas= 0   órfãs=29
tokio-auto   / guincho                   respondidas= 0   órfãs=29
```

📊 E o material para consertar existe: **28.094 eventos · 544 sessões · 17 pares corretora×seguradora · 13 meses**. A mapfre — que uma auditoria chamou de "sem sessões" — tem 13 sessões e evento de **21/08/2026 às 10:04**.

**Esta SPEC transforma esse material em rotas AAA.**

---

## 2. 🔴 A DESCOBERTA QUE ORGANIZA TUDO: A URA É UMA ÁRVORE

### 2.1 O que se pensava, e por que estava errado

A intuição natural é tratar cada rota como uma coisa separada: "a rota do guincho", "a rota do chaveiro". Sob essa intuição, o trabalho seria uma fila de 62 itens independentes, e a validade de cada um seria a idade da última sessão **daquele serviço**.

**Está errado, e o erro custa caro nos dois sentidos.**

### 2.2 A evidência

📊 Medido na Allianz, 21/08/2026 — quantos **serviços diferentes** veem cada tela:

| tela | serviços que a veem | sessões | visto por último |
|---|---:|---:|---|
| `Termo de Privacidade: Ao prosseguir…` | **5** | 123 | 19/08/2026 |
| `Certo! Por favor digite o *CPF* ou *CNPJ* do(a) titular…` | **5** | 78 | 19/08/2026 |
| `Olá! Sou a assistente virtual da Allianz. Você precisa de Assistência…` | **5** | 59 | 19/08/2026 |
| `Qual seguro deseja utilizar? *1 - Residencial* …` | **5** | 37 | 19/08/2026 |
| `Por favor, confirme o endereço para atendimento:` | **4** | 79 | 19/08/2026 |
| `Agora, me confirme o número da residência.` | **4** | 72 | 19/08/2026 |
| `Vou transferir seu caso para um especialista…` | **5** | 98 | 03/08/2026 |

*(os cinco serviços: eletricista · eletrodoméstico · encanador · guincho · outros)*

**Uma tela vista por cinco serviços não pertence a nenhum deles. Pertence à seguradora.**

### 2.3 🔴 E a URA muda o tronco — está medido

📊 Duas redações da MESMA tela de abertura da Allianz:

```
"Olá! Sou a *assistente virtual da Allianz*. Você precisa de Assistência…"
     59 sessões · 4-5 serviços · visto por último 19/08/2026

"Olá! Sou a *assistente virtual da Allianz*. Este é um canal exclusivo de…"
     64 sessões · 4 serviços · visto por último 26/03/2026
```

**A Allianz reescreveu a primeira tela entre março e agosto.** E essa mudança **não é do guincho, nem do eletricista** — é de **todas as rotas da Allianz**, das duas linhas, dos dois ramos.

### 2.4 O modelo que esta SPEC adota

> ## A URA é uma ÁRVORE. A unidade de trabalho é o **NÓ**, não a rota.
>
> ```
>                   [ tronco ]  ← vista por TODOS os serviços
>          Olá · Termo · CPF · Qual seguro
>                        │
>            ┌───────────┴───────────┐
>       [ galho AUTO ]        [ galho RESIDENCIAL ]   ← vista por um ramo
>            │                        │
>     ┌──────┴──────┐         ┌───────┴────────┐
>  guincho      chaveiro   eletricista   eletrodoméstico   ← FOLHA: um serviço
> ```

E daí saem três consequências que governam a SPEC inteira:

**(a) Consertar um nó de tronco paga por todas as rotas daquela seguradora.**
📊 A tela do CPF da Allianz é vista por 5 serviços em 78 sessões. Uma âncora certa ali serve às 6 rotas residenciais **e** às 4 de auto.

**(b) A validade é por NÓ, não por rota.**
Uma tela vista **hoje** numa sessão de guincho está atualizada **para todo mundo que passa por ela** — inclusive para o chaveiro, cuja última sessão foi há seis meses.

**(c) Consertar uma folha paga por uma rota só.**
E é por isso que folha vem depois de tronco, sempre.

---

## 3. 🔴 AS REGRAS DE ATUALIDADE

O cenário que o Founder descreveu, resolvido em regras que um agente segue sem interpretar.

### 3.1 O cenário, literal

> *"Se um atendimento for de Allianz residencial guincho e for feito hoje, e na 4ª pergunta tiver que escolher entre guincho × chaveiro… as atualizações até a pergunta 4 devem ser consideradas e valem para todas as rotas.*
>
> *Se a pergunta 1 desse atendimento tiver uma mudança, todas as rotas que tiverem a mesma pergunta precisarão ser ajustadas, porque é a primeira pergunta para todas.*
>
> *Se a pergunta 4 que mudou, as rotas que têm as perguntas 1, 2 e 3 sem mudança precisam continuar as mesmas. Só a partir da URA mudada é que devemos ajustar.*
>
> *Se o último atendimento de chaveiro da Allianz auto foi em dezembro e guincho foi hoje, precisa ser ajustado para chaveiro se a mudança influencia chaveiro também."*

### 3.2 As cinco regras

```
R1 · A ATUALIDADE É DO NÓ
     Cada TELA tem a sua própria data de "visto por último", e ela é o MAIOR
     `wa_timestamp` em que aquela tela apareceu — em QUALQUER sessão, de
     QUALQUER serviço, de QUALQUER corretora.

     📊 A tela do CPF da Allianz foi vista em 19/08/2026, numa sessão de
     eletrodoméstico. Ela está atualizada para o chaveiro também.

R2 · A MUDANÇA SOBE, NUNCA DESCE
     Uma tela que mudou afeta TODAS as rotas que passam por ela — e só elas.
     Rota que não passa por aquela tela não é tocada.

     Como se decide "quem passa por ela": as sessões do corpus em que a tela
     aparece, e os serviços dessas sessões.

R3 · O PREFIXO INTACTO NÃO SE MEXE
     Se a tela que mudou está na posição 4, as telas 1, 2 e 3 continuam
     idênticas para todas as rotas. Mexer nelas "de carona" é a forma mais
     rápida de quebrar rota que estava boa.

     Verificador: depois de qualquer mudança, o replay de TODAS as rotas
     daquela seguradora tem de manter ou aumentar as respondidas. Uma que
     caia é regressão, e o bloco não fecha.

R4 · SESSÃO ANTIGA NÃO INVALIDA TELA NOVA — E VICE-VERSA
     Se o último chaveiro foi em dezembro e o guincho foi hoje, e as duas
     sessões passam pela tela X:
       · a tela X vale pela versão de HOJE (R1)
       · as telas que SÓ o chaveiro vê continuam com a evidência de dezembro,
         e ficam marcadas com essa data
       · a rota do chaveiro recebe o carimbo `TRONCO_ATUAL / FOLHA_ANTIGA`

     🔴 É PROIBIDO concluir "o chaveiro está velho, não mexe". A parte dele
     que é tronco está atualizada, e ela é a maior parte.

R5 · DUAS REDAÇÕES DA MESMA TELA = A NOVA VENCE, A ANTIGA SOBREVIVE
     Quando a mesma tela aparece com dois textos, a âncora é AMPLIADA para
     cobrir os dois — nunca trocada.

     📊 Razão medida: a redação de 26/03 da abertura da Allianz aparece em 64
     sessões. Trocar a âncora emudeceria o corredor se a seguradora voltasse
     atrás, e apagaria a capacidade de ler o próprio acervo.

     E o CONTROLE é obrigatório no teste: a redação antiga TEM de continuar
     casando. Foi assim que o conserto de `numero_residencia` foi feito
     (`(?:informe|confirme)`, e não `confirme`).
```

### 3.3 🔴 Como o agente decide o que é tronco e o que é folha

**Não por intuição. Por medição, com esta consulta:**

```sql
-- Para uma seguradora, quantos SERVIÇOS distintos veem cada tela.
with s as (
  select session_id, <CLASSIFICADOR_DE_SERVICO> as servico
  from observed_events where insurer_key = '<SEG>' group by 1
)
select _norm(e.text) as tela,
       count(distinct s.servico) as servicos,
       count(distinct e.session_id) as sessoes,
       max(e.wa_timestamp) as visto_por_ultimo
from observed_events e join s using (session_id)
where e.insurer_key='<SEG>' and e.direction='in'
group by 1;
```

```
servicos ≥ 3  →  TRONCO       consertar aqui paga por todas as rotas
servicos = 2  →  GALHO        paga por duas
servicos = 1  →  FOLHA        paga por uma
```

⚠️ `<CLASSIFICADOR_DE_SERVICO>` é o `PADROES_DE_SERVICO` entregue pela SPEC-083 §5.5. **Não invente outro.**

⚠️ E há um viés a declarar: uma tela que só apareceu numa sessão parece folha mesmo sendo tronco. Por isso a classificação **também** olha a posição: tela que aparece antes da primeira escolha de serviço é tronco **por construção**, mesmo com `servicos = 1`.

---

## 4. A ORDEM DO TRABALHO

### 4.1 A pergunta que o Founder fez

> *"Precisa ver qual é a melhor sequência… se por seguradora, se por ramo, etc."*

**A resposta que a árvore dá: nem por seguradora, nem por ramo. Por PROFUNDIDADE — e dentro de cada profundidade, por demanda.**

```
ONDA 1 · O TRONCO de cada seguradora        ← paga por TODAS as rotas dela
ONDA 2 · Os GALHOS (auto / residencial)     ← paga por metade
ONDA 3 · As FOLHAS, por demanda medida      ← paga por uma
```

### 4.2 Por que é essa, e não outra

**Por seguradora inteira** — faria o executor escrever a folha do chaveiro da Allianz antes do tronco da Porto. 📊 O tronco da Porto é visto por 138 sessões; a folha do chaveiro da Allianz, por poucas.

**Por ramo** — quebra a árvore no lugar errado: 📊 `Termo de Privacidade` e `CPF` são vistos por auto **e** residencial.

**Por demanda pura** — começaria por `chaveiro` (213 sessões), que é folha de 10 seguradoras diferentes; cada uma exigiria o tronco daquela seguradora antes. Ordem que se auto-bloqueia.

**Por profundidade** — cada onda entrega valor para todas as rotas abaixo dela, e nunca espera nada de uma onda posterior.

### 4.3 Dentro de cada onda, a ordem é o RETORNO MEDIDO

```
retorno(nó) = (nº de rotas que passam por ele) × (nº de sessões em que aparece)
```

📊 Exemplo, Allianz: a tela do CPF (5 serviços × 78 sessões = 390) vem antes da tela de complemento de endereço (4 × 71 = 284).

E entre seguradoras, na Onda 1, o desempate é o tamanho do acervo:

```
allianz 141 sessões · porto 138 · yelum 100 · tokio 47 · hdi 44
bradesco 22 · azul 19 · zurich 15 · mapfre 13 · alfa 9
```

### 4.4 🔴 A exceção que vem antes de tudo

**Os três buracos da própria régua.** A SPEC-083 os mediu e eles são as **três primeiras entregas** desta SPEC:

| # | o quê | +pts |
|---|---|---:|
| 1 | transcrever a sessão `7ac3c101` no bloco do subserviço `maquina_de_lavar` | +4 |
| 2 | mapear a órfã funcional `"Agendamento para: … Podemos continuar ?"` | +10 |
| 3 | pôr contagem própria no `notes` dos passos respondidos | +5 |

**Razão:** enquanto a régua não tirar ≥95, ela não é régua — é aspiração. E 61 rotas seriam medidas contra ela.

### 4.5 A segunda exceção: o serviço que já funciona e está desligado

📊 **Socorro mecânico** aparece em **38 sessões** do acervo (yelum 21, zurich 9, hdi 8) e `subservice_supported()` devolve `False`. Não existe `socorro_mecanico` em nenhum `subservices` nem em `_SUBSERVICE_ALIASES`.

**Estamos recusando um serviço que os clientes pedem e que a URA atende.** Entra logo depois dos três buracos da régua.

⚠️ A afirmação anterior de "6 sessões com protocolo, 2 ao vivo" **não reproduziu** e está sob `ANCORA_SUSPEITA` (zurich não escreve "protocolo"). **Refazer a medição citando as `session_id` antes de decidir a prioridade final.**

---

## 5. O PROCESSO DE UMA ROTA

**Uma rota por vez. Nunca duas.** Foi assim que a máquina de lavar deu certo — e 📊 é a diferença dela para as outras 61.

### 5.1 Os sete passos

```
① COLHER
   Ache as sessões do corpus que passam por esta rota, ordenadas por
   `wa_timestamp` decrescente. Para cada TELA da rota, a versão válida é a
   MAIS RECENTE em que ela apareceu — em qualquer sessão, de qualquer
   serviço (R1).

   Zero sessões e zero telas → PARA. Devolve `SEM_FONTE` com o roteiro de
   coleta. NÃO escreve passo nenhum.
   🔴 Inventar rótulo de menu manda o segurado para a opção errada — e o
   corredor não trava, ele RESPONDE COM CONFIANÇA a coisa errada.

② TRANSCREVER
   No comentário do bloco, turno a turno, na ordem em que a URA usou, com a
   marca `📊 sessão <8 hex>` de cada uma. É o que permite auditar sem voltar
   ao banco — e vale 4 pontos do eixo A da régua.

③ ESCREVER
   passos exclusivos com `only_subservices` · teclas fixas no subserviço ·
   derivação com DEFAULT para toda tecla dinâmica · apelidos do jeito que o
   cliente fala (tirados do acervo) · `regras_para_o_cliente` e
   `expectativa_do_desfecho` lidos nas telas.

   🔴 REGRA DE ORDEM: `match_ura_step` devolve o PRIMEIRO que casa. Tela que
   pede resposta vai ANTES de qualquer `noop` largo.

④ PROVAR
   Teste que chama o MOTOR (CLAUDE.md §9.4), com `MUTACOES` declaradas e
   executadas por `medir_rota --verificar-mutacoes`.

⑤ MEDIR
   `python backend/scripts/medir_rota.py --seguradora X --ramo Y --servico Z`
   Meta: ≥95.

⑥ JULGAR
   Os três juízes de §6. **A liberação é deles, nunca do executor.**

⑦ REGISTRAR
   O que ficou faltando por ausência de evidência vai para `PENDENCIAS.md`
   com o que destrava. Rota liberada com lacuna anotada é honesta;
   rota liberada em silêncio, não.
```

### 5.2 🔴 Depois de CADA rota: o replay de regressão

```bash
python backend/scripts/medir_rota.py --seguradora <SEG> --todas-as-rotas-dela
```

**Nenhuma rota daquela seguradora pode ter perdido respondidas** (R3). Uma que caia é regressão, e o trabalho volta antes de seguir.

📊 Razão: 58 assinaturas de passo aparecem em mais de um playbook, e `_YELUM_FAMILY_STEPS` alimenta `hdi-auto` **e** `yelum-auto`. Mexer num passo de família mexe em dois corredores.

### 5.3 Como os subagentes se dividem

```
COLETOR    lê o acervo, monta o corpus da rota, classifica tronco/galho/folha
           NÃO escreve corredor

ESCRITOR   recebe o corpus do coletor e escreve passos, teclas, apelidos, teste
           NÃO consulta o banco

JUÍZES     recebem o resultado e o corpus
           NÃO escrevem nada
```

🔴 **Quem observa não escreve.** Se o mesmo agente colhe e escreve, ele escreve o que gostaria de ter visto. A separação é o que torna o corpus uma prova, e não uma justificativa.

**Paralelismo permitido:** um COLETOR por seguradora, em paralelo. **Um ESCRITOR por rota, em série dentro da seguradora** — porque duas rotas da mesma seguradora tocam os mesmos arquivos.

---

## 6. 🔴 OS JUÍZES — E O LAÇO QUE NÃO ACABA ATÉ LIBERAR

### 6.1 A regra do Founder, literal

> *"O juiz deve falar, o executor fazer os ajustes, e o juiz conferir de novo. E fazer isso até liberar de verdade. Não pode ser feito o juiz fala, executa e acabou."*

```
      ┌──────────────────────────────────────────────┐
      │                                              │
      ▼                                              │
   EXECUTOR escreve  ──▶  JUÍZES julgam  ──▶  reprovou? ──┘
                                │
                            aprovou (os TRÊS)
                                │
                                ▼
                        ROTA LIBERADA
```

**A liberação é do juiz. Sempre. O executor nunca declara pronto.**

### 6.2 As três lentes

Lentes **diferentes** de propósito — três agentes idênticos encontram o mesmo defeito três vezes e perdem os outros dois.

#### 🔍 JUIZ 1 — O CÉTICO
*Tenta refutar que a rota está pronta.*

- Alguma tela do corpus **não casa** passo nenhum e **pede** algo?
- Alguma âncora casa **zero** vezes no acervo? (o defeito do `numero_residencia`)
- Alguma âncora é **larga demais** e rouba a tela de outro passo?
- A transcrição bate com a sessão que ela cita?
- 📊 O número no `notes` é **daquela seguradora**, ou foi copiado de família?

**Reprova se:** qualquer resposta acima for sim.

#### 🛡️ JUIZ 2 — O SEGURANÇA
*Onde errar é irreversível, o corredor para?*

- O freio de finalização **casa a tela real** de confirmação desta rota?
- Toda tecla `_opcao` tem origem nas **três** fontes?
- A tecla escolhida é **a certa**? (📊 `14` é máquina de lavar; `10` é lava-louças; `13` é secadora)
- Existe tela que **pede dinheiro** ao cliente e é respondida automaticamente? (📊 a Yelum tem: *"valor excedente a ser pago para o prestador de $ 115,00"*)
- Alguma resposta **afirma um fato** que ninguém confirmou? (📊 a tela *"idade do aparelho? 1- Até 10 anos"* é respondida `"1"` sem ninguém ter confirmado)

**Reprova se:** qualquer irreversível não estiver freado.

#### 🧍 JUIZ 3 — O SEGURADO
*Ele soube o quê, e quando?*

- Ao final, o cliente recebe **protocolo + dia + período**?
- As `regras_para_o_cliente` são ditas **antes** do acionamento?
- O que o cliente ouve é **verdade**? (📊 o corredor disse *"a senha são os 4 últimos do telefone informado"* e a senha era a do número da corretora)
- Se travar, o cliente **fica sabendo**?
- A `expectativa_do_desfecho` está certa? (📊 eletrodoméstico é **agendado**, não é hoje)

**Reprova se:** o cliente puder ser surpreendido por algo que o sistema já sabia.

### 6.3 O teto do laço, e o que acontece ao bater nele

```
VOLTA 1   executor escreve  → juízes julgam → reprovou? devolve O MOTIVO
VOLTA 2   executor corrige com o motivo em mãos
VOLTA 3   última — e o prompt do executor DIZ que é a última
──────────────────────────────────────────────────────────────────
BATEU O TETO  não é silêncio, e não é liberação:

   · a rota vira `PRECISA_DE_HUMANO` no inventário
   · o dossiê traz: as 3 versões, e por que CADA uma foi reprovada
   · vai para `PENDENCIAS.md` com o que destrava
   · o Founder decide: aceitar com lacuna anotada, ou coletar mais evidência
```

🔴 **Três é o número.** Depois disso um modelo forte para de melhorar e começa a inventar — e invenção é exatamente a falha que se quer evitar num menu de URA.

⚠️ **Reprovação sem motivo acionável não conta como volta.** O juiz que reprovar tem de dizer **qual conferência** falhou e **qual tela** a prova. "Está incompleto" não é reprovação — é ruído, e o executor devolve pedindo o motivo.

### 6.4 O juiz também julga a SPEC

O mesmo laço vale para os documentos: **esta SPEC** foi ao juiz, será corrigida, e volta ao juiz até liberar. 📊 A SPEC-083 foi reprovada com 54/100 na primeira volta — e o defeito mais grave (o gate matematicamente impossível) só apareceu porque alguém foi conferir a aritmética.

---

## 7. O QUE FAZER QUANDO NÃO HÁ CONVERSA

### 7.1 A regra

> *"Se não existirem as conversas nas seguradoras, deve ser feito até onde temos evidências e anotar o que falta ser conferido."*

```
① Escreva os passos que a evidência sustenta.
② Onde a evidência acaba, o corredor NÃO inventa: o passo seguinte é o
   `pausar_e_chamar`, que responde ao cliente
   💭 "Só um instante, vou confirmar com a equipe" e chama o humano.
③ A rota é liberada pelo juiz com o carimbo `PARCIAL: até a tela N`.
④ `PENDENCIAS.md` recebe: qual tela falta, quantas sessões teriam de
   existir, e o roteiro de coleta.
```

🔴 **Um corredor que para e avisa é infinitamente melhor que um que responde chutando.** Chutar não trava — abre o chamado errado.

### 7.2 Os três estados de fonte, e o que cada um permite

| estado | o que o executor pode fazer |
|---|---|
| 🟢 **COMPLETA** | rota inteira, meta ≥95 |
| 🟡 **PARCIAL** | até onde há tela; `pausar_e_chamar` no resto; meta = a nota máxima possível com a evidência que existe, e ela é **declarada** |
| 🟠 **ANCORA_SUSPEITA** | 🔴 **NÃO é ausência de fonte.** Primeiro amplia a âncora de desfecho daquela seguradora, e só então mede |
| 🔴 **SEM_FONTE** | nada. Vai para a lista de coleta |

📊 O estado `ANCORA_SUSPEITA` cobre hoje **13 rotas**: mapfre (4), bradesco (4), zurich (5) — porque zurich e bradesco escrevem *"ordem de serviço"*, não *"protocolo"*, e mapfre casa zero em 13 sessões.

---

## 8. 🔴 MULTI-CORRETORA: A MESMA PERGUNTA, DADOS DIFERENTES

### 8.1 A decisão, e a autoridade

📊 As duas corretoras têm acervos da mesma seguradora:

| | Resulta | AutoFleet |
|---|---:|---:|
| allianz | 10.608 ev · 93 sessões | 2.546 ev · 47 sessões |
| porto | 2.004 · 38 | 2.506 · 99 |
| yelum | 1.056 · 18 | 3.548 · 82 |

**Decisão do Founder, registrada:** *"A seguradora tem a mesma pergunta para todas as corretoras. O que pode mudar é se não forem as mesmas rotas, ou perguntas com dados diferentes."*

Coerente com `O-ATLAS-E-UM-SO-E-E-DE-TODAS.md`: a URA é a mesma para todas.

### 8.2 A distinção que o agente precisa fazer, e ela é a fina

```
MESMA TELA, DADOS DIFERENTES  →  ESPERADO. Não é achado.
  "Para esse CPF localizamos o serviço de CHAVEIRO RESIDENCIAL"
  "Para esse CPF localizamos o serviço de ENCANADOR"
  É a mesma tela. O que muda é a apólice do cliente.
  → a âncora casa a PARTE FIXA; a variável vira grupo de captura ou é ignorada

MESMA TELA, TEXTO FIXO DIFERENTE  →  ACHADO. Duas hipóteses:
  (a) a URA mudou de redação entre as duas datas   → R5: amplia a âncora
  (b) a seguradora trata as corretoras diferente    → PARA e pergunta ao Founder

  Como distinguir: compare as DATAS.
    · datas afastadas  → provável (a). Amplia a âncora e registra as duas
    · MESMO período e corretoras diferentes → provável (b). PARA.
```

### 8.3 O procedimento

1. O corpus é **global por seguradora+ramo** (SPEC-083 §6.2), com `company_id` como metadado.
2. Ao achar duas redações da mesma tela, o COLETOR reporta `DUAS_REDACOES` com: os dois textos, as datas, as corretoras e as contagens.
3. Datas afastadas → **R5**, amplia, e o CONTROLE do teste guarda as duas.
4. Mesmo período + corretoras diferentes → **`DIVERGENCIA_ENTRE_CORRETORAS`**, a rota **para**, e o Founder decide.

⚠️ **O agente nunca escolhe sozinho no caso (b).** Escolher errado ali significa escrever, para uma corretora, o corredor da outra.

---

## 9. OS BLOCOS DE EXECUÇÃO

### BLOCO 0 — A régua fecha a si mesma

**Entrega:** os três buracos de §4.4 + o replay de regressão da Allianz residencial.

**Gate:** `medir_rota --seguradora allianz --ramo residencial --servico maquina_de_lavar` ≥ **95**.
**+ os três juízes liberam.**

🔴 Enquanto este bloco não fechar, **nenhum outro começa**.

---

### BLOCO 1 — O tronco de cada seguradora

**Ordem:** allianz → porto → yelum → tokio → hdi → bradesco → azul → zurich → mapfre → alfa.

**Por seguradora:**
1. Classificar as telas em tronco / galho / folha (§3.3)
2. Para cada tela de tronco, na ordem de retorno (§4.3): a versão **mais recente** vira/atualiza passo
3. Replay de **todas** as rotas daquela seguradora — nenhuma perde respondidas (R3)
4. Os três juízes

**VERIFY por seguradora:**
```bash
python backend/scripts/medir_rota.py --seguradora <SEG> --todas-as-rotas-dela --antes-e-depois
# esperado: TODAS as rotas sobem ou empatam. Uma que caia = regressão.
```

**O que se espera medir:** 💭 o tronco é ~40% das telas de uma sessão típica. Fechá-lo deve levar as rotas daquela seguradora de "toco" para "parcial" **sem tocar em nenhuma folha**.

---

### BLOCO 2 — Os galhos (auto / residencial)

Mesmo procedimento, nas telas de `servicos = 2`.

📊 Exemplo Allianz: `Por favor, confirme o endereço` e `Agora, me confirme o número da residência` são vistas por 4 serviços — são galho residencial e valem para eletricista, encanador, eletrodoméstico e chaveiro de uma vez.

---

### BLOCO 3 — As folhas, por demanda

💭 Ordem de grandeza (a SPEC-083 §5.5 regera os números exatos):

```
chaveiro ~213 · guincho ~205 · eletricista ~176 · encanador ~152
bateria ~113 · pneu ~105 · eletrodoméstico ~105 · mecânico ~91 · vidros ~79
```

**Uma rota por vez, os sete passos de §5.1, os três juízes em cada uma.**

---

### BLOCO 4 — Os serviços que existem na URA e não no código

| seguradora | ramo | serviço |
|---|---|---|
| todas | auto | **socorro mecânico** — 📊 38 sessões, e recusamos |
| yelum, hdi, porto, allianz | residencial | **ar condicionado** |
| porto | residencial | chuveiro, chaveiro, desentupimento |
| bradesco, tokio | auto | vidros |
| porto | auto | "Técnico", "Táxi" |

⚠️ Levantado por evidência textual citada, **não** por varredura sistemática. **Refazer com o corpus antes de executar.**

---

### BLOCO 5 — O inventário e as pendências

**Entrega:** `INVENTARIO-DE-ROTAS.md` regenerado · `PENDENCIAS.md` com todas as lacunas · a **lista de coleta** com o roteiro de cada rota `SEM_FONTE`.

**O roteiro de coleta**, por rota, no formato que já funcionou com a Yelum:
1. o número da assistência da seguradora
2. o caminho de telas até o ponto desconhecido
3. 🔴 **a linha de controle**: uma segunda rodada com um serviço cujo desfecho já conhecemos, para provar que a URA não mudou entre as duas
4. o que se espera aprender

---

### BLOCO 6 — Os relatórios retroativos (opcional, decisão do Founder)

📊 Sete SPECs foram executadas sem relatório: **065, 069, 070, 071, 072, 076, 081**. Cada uma pode ter deixado trabalho pela metade que ninguém registrou.

Entrega: um relatório por SPEC, a partir do diff dos commits dela, com o que foi feito e o que ficou de fora.

⚠️ Bloco separado e **último** de propósito: é dívida, não é rota. Se o tempo apertar, ele é o que se corta — e cortá-lo fica **registrado**, não silencioso.

---

## 10. RISCOS

| risco | fechamento |
|---|---|
| **Consertar o tronco quebra rota que estava boa** | R3 + o replay de regressão em toda seguradora, com `--antes-e-depois` |
| **O executor declara pronto sem o juiz** | A liberação é do juiz, e o inventário só aceita rota com os três vistos |
| **O laço não converge e trava a fábrica** | Teto de 3 voltas → `PRECISA_DE_HUMANO` com dossiê |
| **Escrever passo sem evidência** | ① do processo: zero sessões → PARA. E o juiz CÉTICO confere a transcrição contra a sessão citada |
| **Família de passos: mexer num muda dois corredores** | Coluna FAMÍLIA no inventário + o replay de regressão pega |
| **Duas corretoras divergem e o agente escolhe** | §8.3: no caso (b) a rota PARA e o Founder decide |
| **A ordem por profundidade atrasa a rota de maior demanda** | É deliberado: 📊 `chaveiro` é folha de 10 seguradoras; sem o tronco de cada uma, ela não fecha em nenhuma |
| **O corpus envelhece durante a execução** | O acervo é vivo (📊 +2 eventos em 28 h). Cada rota registra a data do corpus que usou; o inventário traz o carimbo |

---

## 11. RELATÓRIO FINAL

Além do template padrão:

- a **árvore medida** de cada seguradora (tronco / galho / folha, com as contagens)
- por rota: a nota **antes e depois**, as sessões usadas, e os três vistos dos juízes
- as rotas que bateram o teto de 3 voltas, com o dossiê
- as rotas `PARCIAL`, com a tela onde a evidência acabou
- os casos `DIVERGENCIA_ENTRE_CORRETORAS`, com a decisão do Founder
- o replay de regressão de **todas** as seguradoras tocadas
- a lista de coleta final
- declaração de que nenhuma rota foi liberada sem os três juízes
