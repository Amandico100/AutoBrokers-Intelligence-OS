---
> # ⏸️ SPEC FUTURA — NÃO EXECUTAR NESTA LEVA
>
> **Status:** canônica · **congelada até depois do piloto**
> **Versão:** 1.0 · **Criada em:** 01/08/2026
> **Gatilho de execução:** decisão do Founder, depois de Resulta e AutoFleet
> rodarem o piloto sem incidente
> **Autoridade superior:** CLAUDE.md · SPEC-054 · SPEC-062
> **Origem:** pesquisa de arquitetura de canais de 31/07/2026
> **Branch:** `feat/spec069-canais-definitivos`
---

# SPEC-069 — Canais Definitivos

> **⏸️ Esta SPEC não entra na leva atual, e a decisão é do Founder:** implantá-la
> agora atrasaria o piloto, e com **3 a 5 boletos por dia** o risco atual é baixo.
> Ela é escrita agora porque o conhecimento está fresco — e porque **quando
> chegar a hora, é para executar, não replanejar.**

---

## 0. Por que ela está congelada, e quando descongela

### 0.1 A decisão registrada

O Founder decidiu, em 01/08/2026:

> *"Podemos adotar todas as questões que você falou, mas isso iria atrasar o
> plano piloto. Agora só com Resulta e AutoFleet quero continuar com a Evolution
> para cobrança também. Depois que estivermos testando, fazendo a coisa andar,
> aí sim vamos incluir a Meta oficial para boletos."*

**Concordo com a decisão, e o motivo é aritmético:** 3 a 5 boletos por dia é
volume em que o risco de bloqueio é baixo, e o custo de migrar agora é uma ou duas
semanas de atraso no que importa.

### 0.2 O que descongela esta SPEC

**Qualquer um destes gatilhos:**

```
1. o piloto rodar sem incidente por 4 semanas
2. o volume de cobrança passar de ~30 mensagens frias por dia por corretora
3. uma terceira corretora entrar
4. qualquer número receber aviso de restrição do WhatsApp
5. decisão comercial do Founder
```

**O gatilho 4 não espera.** Se um número der sinal de restrição, esta SPEC vira
prioridade máxima no mesmo dia.

### 0.3 O que a SPEC-063 já faz, e que é suficiente por ora

```
governador de envio ...... 4 a 8 minutos, aleatório, nunca redondo
segundo número ........... cobrança separada do atendimento
guarda dura .............. observer nunca é canal de saída
parada de emergência ..... para o frio sem derrubar o reativo
registro ................. quem, quando, por qual número
```

**Com isso, o piloto roda seguro.** Esta SPEC é sobre escala, não sobre o piloto.

---

## 1. O achado que muda a premissa

### 1.1 A API oficial da Meta é mais barata que a não-oficial

**FATO**, documentação oficial, lida em 31/07/2026. Desde **01/07/2025** a
cobrança é **por mensagem entregue**, não por conversa:

| Categoria | Preço | O que é |
|---|---|---|
| **Utility** | **US$ 0,0068 (~R$ 0,037)** | boleto, aviso de vencimento, 2ª via |
| Marketing | US$ 0,0625 (~R$ 0,34) | campanha, oferta |
| **Serviço / resposta na janela de 24h** | **grátis** | todo o atendimento reativo |
| **Utility dentro da janela aberta** | **grátis** | — |

**Cobrança de boleto é utility, não marketing.**

```
500 boletos/mês pela Cloud API direta ..... R$ 18
Z-API ..................................... R$ 99,99/mês
Evolution self-hosted ..................... ~R$ 40/mês de VPS
```

### 1.2 O caro nunca foi a Meta

```
Meta direto ..... R$ 0,037
Zenvia .......... R$ 0,55    ← 15× a Meta
Blip ............ R$ 0,60    ← 16×
```

**A intuição "oficial é caro" vem de duas coisas que já não valem:** o modelo
antigo por conversa (morto em julho de 2025) e o preço de *marketing*, que é 9
vezes o de utility.

`360dialog` repassa sem markup por €49 por número/mês; **a Cloud API direta não
tem mensalidade nenhuma.**

### 1.3 E o faturamento em BRL

**A partir de 01/07/2026** dá para faturar em reais pela Facebook Brasil — nota
fiscal local, sem IOF. **Migração obrigatória até 30/06/2027.**

---

## 2. O risco que a pesquisa reposicionou

### 2.1 O número não é nosso — é o telefone da corretora

**FATO:** o número pareado é o **celular de trabalho da corretora**. SIM real,
aparelho da atendente.

> **Um banimento não derruba nossa infraestrutura. Destrói o telefone comercial
> do cliente** — com histórico, contatos e a identidade que os segurados têm
> salva. E é praticamente irreversível.

O maior gateway não-oficial do Brasil diz, sobre número banido: *"foi desativado
permanentemente, sem aviso prévio ou chance de recuperação."*

**Ninguém credível publica taxa de sucesso de apelação.**

### 2.2 O que de fato causa bloqueio

**FATO, fonte primária** (documento de segurança da própria WhatsApp): os sinais
são **reputação do número, comportamento no envio, e denúncias de usuários.**
IP aparece só no **registro** — que já aconteceu, no celular da atendente.

**FATO, novo e grave:** desde maio de 2025 a detecção alcança a **biblioteca**,
não só o comportamento. Há caso documentado do aviso *"sua conta pode estar
usando ferramentas não autorizadas"* atingindo clientes que **só respondiam
mensagens recebidas** — volume baixo, sem disparo. A hipótese dos mantenedores é
**telemetria ausente**: o cliente oficial emite um pacote que a biblioteca não
emite. **É impressão digital de cliente, não de IP.**

**FATO, operador real:** número que mandava 1.000 mensagens/dia passou a ser
banido em **40 a 50 mensagens**.

### 2.3 A distinção que importa operacionalmente

```
mensagem FRIA, para quem não escreveu antes ..... o risco quase todo mora aqui
resposta dentro de conversa existente ........... a parte segura
```

**Atendimento reativo é seguro. Cobrança proativa carrega o risco inteiro.**

---

## 3. Proxy: não

**Não há uma única evidência credível de que proxy reduz banimento. Há evidência
contra.**

### 3.1 A evidência contra

**FATO** (artigo acadêmico, novembro de 2025): pesquisadores rodaram **a mesma
biblioteca que usamos** e enumeraram bilhões de contas — **7.000 números por
segundo, durante meses, de um único IP estático de universidade, sem proxy.**

Texto deles: *"nem nosso endereço IP nem nossas contas foram bloqueados."*

**Isso mata a premissa "IP de datacenter = banimento."**

**FATO** (operador real): tentou **rotação de proxy, VPS separada por instância,
conteúdo randomizado, imagens aleatórias, remoção de links e aquecimento** — foi
**banido em 40 a 50 mensagens mesmo assim.** Banido *durante* o aquecimento.

**FATO:** um fornecedor que vende software não-oficial mas **não vende proxy** tem
página dedicada a evitar bloqueio e **não menciona proxy nem IP em lugar nenhum.**

### 3.2 O conflito de interesse

**100% das fontes que afirmam que proxy previne banimento vendem proxy.**
Nenhuma publica medição.

### 3.3 Onde proxy TEM uso legítimo — e é outro

**Raio de explosão.** O documento da WhatsApp diz que rede *"recentemente usada
por abusadores conhecidos"* conta.

> Com 300 corretoras num único IP, **uma que abuse contamina todas.**

**Isso justifica IP estático por tenant a partir de ~100 corretoras** — não proxy
residencial rotativo.

### 3.4 ⚠️ A armadilha, se decidirmos usar

**A biblioteca, ao falhar o proxy, conecta direto e em silêncio** — registra
*"erro de proxy, continuando sem proxy"* e segue.

**O isolamento vira ficção exatamente quando importa.**

**Se usar proxy: verificar o IP de saída depois de conectar, e alarmar.**

---

## 4. "Aquecimento de chip" não tem evidência

Os protocolos publicados **discordam entre si em 5 a 10 vezes** — dia 1 vai de 5
a 50 mensagens; "maduro" vai de 3 a 30 dias. **A Meta nunca publicou nada.** Todo
fornecedor que vende maturador se isenta na letra miúda.

> **Existe um mercado de R$ 47 a 149 por mês no Brasil construído sobre premissa
> que ninguém mediu. Não pague por isso.**

**A âncora defensável, essa sim:** a Meta concede **250 conversas novas por 24h**
a um negócio verificado na API oficial. **Quem dispara 500/dia num chip de duas
semanas está 2 a 4 vezes acima do que a própria Meta considera seguro para um
remetente identificado.**

---

# BLOCO 0 — A auditoria que vem antes de qualquer linha de código

**Obrigatório, e aqui ela tem uma característica própria: os preços mudam.**

## 0.1 O que reconfirmar

```
[ ] o preço de utility ainda é o mesmo? (a estrutura mudou em 07/2025)
[ ] a janela de 24h ainda é grátis para utility?
    ⚠️ um BSP avisou que a partir de 01/10/2026 a Meta passaria a cobrar
       utility dentro da janela. NÃO CONSEGUI CORROBORAR em fonte da Meta.
       Se for verdade, o custo triplica — para ~R$ 55, ainda barato.
       PERGUNTAR DIRETO A UM BSP.
[ ] o faturamento em BRL pela Facebook Brasil está disponível?
[ ] o limite de 10 clientes novos por semana ainda vale?
[ ] o SES ainda tem multi-tenancy nativa, e ao mesmo preço?
```

## 0.2 O que medir antes de decidir sobre proxy

```
[ ] consumo de banda por sessão, medido 7 dias com um tenant real
    → decide entre proxy por-GB e por-IP
[ ] quantas corretoras compartilham IP hoje
[ ] há sinal de restrição em algum número?
```

## 0.3 O relatório

**✅ confirmado · ⚠️ corrigido · ➕ acrescentado · ❓ em aberto · 🚫 retirado.**

---

# BLOCO A — A API oficial da Meta

**Nota 90 de economia. Zero de urgência enquanto o volume for baixo.**

## A.1 O desenho: o quinto provedor

**Não é motor paralelo.** O contrato de provedor em
`backend/app/services/whatsapp/providers/base.py` **já tem as marcas `templates`
e `session_window_24h`** — a API oficial foi antecipada no desenho.

```
é o quinto provedor no registry que já existe
o Tool Gateway continua sendo a autoridade
o governador de envio da SPEC-063 continua valendo
```

## A.2 A divisão de canais

| Função | Canal | Por quê |
|---|---|---|
| **Atendimento** (segurado inicia) | Evolution Go, número da corretora | resposta dentro de conversa é a zona segura, e é grátis |
| **Cobrança** (nós iniciamos) | **API oficial, número separado** | carrega 100% do risco; custa R$ 0,037; **e não pode destruir o telefone do cliente** |
| **Relatório ao corretor** | **e-mail + dashboard** | não é conversa com segurado; não precisa de WhatsApp |
| **Alerta crítico** | dashboard + e-mail | **nunca pelo canal que caiu** |

**A mudança de maior valor é mover cobrança para o oficial.** É mais barata que o
que pagamos hoje, **e tira o único uso que pode destruir o telefone da corretora.**

## A.2.1 A pergunta que a SPEC-064 deixou registrada: onde ficam as conversas de VÁRIOS números?

> **Acrescentado em 02/08/2026**, durante a SPEC-064, a pedido do Founder.
> **Não é para executar agora. É para não ser descoberto tarde.**

O problema aparece no momento em que a divisão de canais da §A.2 vira realidade:

```
atendimento ..... Evolution Go · número A · o SEGURADO escreve
cobrança ........ API da Meta  · número B · NÓS escrevemos
(futuro) ........ campanha     · número C
```

**O mesmo cliente vai ter conversa em dois ou três números diferentes.** E hoje
a tela de conversas (`/dashboard/atendimentos/conversas`) foi desenhada para um
canal só — ela lista `conversations` sem nenhuma noção de "por qual número isto
entrou".

### O que quebra se ninguém decidir antes

```
a mesma pessoa vira duas conversas soltas, sem se reconhecerem
o atendente responde sobre o boleto sem saber que houve boleto
   (é o Bloco E da SPEC-063, agora multiplicado por N canais)
"assumir a conversa" fica ambíguo: assumir qual?
e a caixa de entrada vira uma lista onde nada tem contexto
```

### A recomendação, para quando descongelar

**Uma caixa, várias linhas — nunca várias caixas.**

```
1. `conversations` ganha CANAL DE ORIGEM explícito
   (integration_id + purpose: attendance | billing | campaign)
   Hoje existe `channel`, que diz "web" ou "whatsapp" — não diz QUAL whatsapp.

2. A tela agrupa por PESSOA, não por número.
   Uma pessoa, uma thread visível, com as mensagens marcadas pela origem —
   do mesmo jeito que um e-mail mostra "para: financeiro@" sem criar uma
   segunda caixa de entrada.

3. Responder devolve pelo MESMO canal que recebeu.
   Nunca pelo "canal disponível" — é assim que a cobrança sairia pelo número
   do atendimento, ou pior, pelo observador (SPEC-063 Bloco D).

4. O agente que responde é o do canal.
   Cobrança tem agente de cobrança (SPEC-063 E.2.2). Atendimento tem o dele.
   Um agente só respondendo em dois papéis é o mesmo defeito da SPEC-063
   Bloco A com outra roupa.

5. E o identificador da pessoa é o TELEFONE DELA + a corretora — nunca só o
   telefone. O buffer sem tenant (SPEC-063 H.2) já provou onde isso dá errado.
```

**A regra que resume:** *o número é por onde a mensagem passou, não quem é o
cliente.* Modelar o contrário é o que produz caixa duplicada.

### Por que fica registrado e não executado

📊 **Medido em 02/08/2026:** nenhuma corretora tem WhatsApp pareado, e a
cobrança não tem número próprio. **Não há conversa de segundo canal para
organizar** — e desenhar a caixa multicanal antes de existir o segundo canal
seria construir sobre suposição.

**O gatilho é o Bloco A desta SPEC.** No dia em que a cobrança ganhar número
próprio, esta seção deixa de ser registro e vira requisito.

## A.3 O modelo multi-tenant — e o prazo escondido

**FATO:** o modelo em nome de terceiro foi descontinuado em 01/10/2025. **Cada
corretora precisa ser dona da própria conta comercial.**

E o cadastro embutido é limitado a **10 clientes novos por semana**, subindo para
200 **só após** três verificações da Meta: verificação de negócio, revisão de
aplicativo, e verificação de acesso.

> **Para centenas de corretoras, essas três verificações precisam começar cedo.**
> **É a única coisa do plano inteiro com fila de terceiro e prazo próprio.**

## A.4 O que muda para o corretor

```
ele precisa ter (ou criar) uma conta comercial da Meta
o número da cobrança precisa ser dele, verificado
e as mensagens de cobrança viram TEMPLATE aprovado pela Meta
   → menos flexível, mas com entrega garantida e sem risco de banimento
```

**O template aprovado é uma restrição real** e precisa ser desenhado com cuidado:
uma vez aprovado, mudar exige nova aprovação.

## A.5 Testes

| # | Prova |
|---|---|
| A1 | o provedor Meta é o quinto no registry, sem motor paralelo |
| A2 | cobrança sai pelo oficial; atendimento continua no Evolution |
| A3 | mensagem fora de template é recusada antes de tentar enviar |
| A4 | a janela de 24h é detectada e a mensagem gratuita é usada quando cabe |
| A5 | o custo por mensagem é registrado por corretora |
| A6 | restrição na conta oficial não derruba o atendimento reativo |

---

# BLOCO B — O e-mail definitivo

**Nota 88.**

## B.1 A escolha: Amazon SES

```
custo ............ US$ 0,10 por mil
faturamento ...... em BRL, pela entidade brasileira, com nota fiscal, sem IOF
região ........... São Paulo
```

**E o que decide, para multi-tenant:** o SES ganhou **isolamento por tenant** —
reputação e supressão separadas, com **pausa automática de UM tenant sem afetar
os outros**, a US$ 0,005 por tenant/mês.

```
100 corretoras = US$ 0,50/mês de isolamento
```

**Nenhum concorrente oferece isso.**

## B.2 O que temos hoje

**SendGrid**, ligado, usado **só para convite de equipe**. Custa ~4× o SES e **não
tem isolamento por tenant.**

## B.3 O que passa a ir por e-mail

```
relatório e achado do Descobridor ..... o conteúdo completo
briefing ............................. quando o corretor escolher e-mail
artefato ............................. o link, e o conteúdo quando couber
alerta crítico ....................... sempre, junto com o dashboard
```

**E o WhatsApp deixa de levar relatório** — leva a manchete e o link. **É melhor
de ler e mais seguro contra bloqueio.**

## B.4 Testes

| # | Prova |
|---|---|
| B1 | e-mail sai pelo SES, com remetente da corretora |
| B2 | rejeição de um tenant não afeta os outros |
| B3 | supressão é por tenant, não global |
| B4 | falha de e-mail não impede a entrega pelo dashboard |

---

# BLOCO C — Push e o que NÃO usar

## C.1 Push no navegador: sim, como complemento

```
custo ....... zero
alcance ..... ~94% dos desktops brasileiros são navegadores compatíveis
adesão ...... 6,11% de aceitação real (dado público de telemetria)
iOS ......... exige "adicionar à tela de início" — e isso não mudou
```

**É complemento do e-mail, nunca substituto.**

## C.2 Telegram: não

```
instalado no Brasil ..... 57%
abre DIARIAMENTE ........ 38%, caindo dois anos seguidos
apelação de bot ......... sem processo publicado
histórico ............... bloqueado judicialmente no Brasil duas vezes
```

**Não vale a superfície de manutenção.**

## C.3 SMS para boleto: não

```
custo .......... R$ 0,07 a 0,12
remetente ...... não dá para marcar — a operadora sobrescreve com código numérico
```

**E o problema decisivo:** com o golpe do boleto passando de R$ 4 bilhões por ano
e a Febraban dizendo publicamente que nunca contata por SMS, **nossa cobrança
ficaria visualmente idêntica a golpe.**

---

# BLOCO D — Isolamento e escala

## D.1 O estado hoje

**Um container, uma réplica, todas as corretoras juntas.** Uma queda derruba
todas.

## D.2 Os números reais

**Única medição séria publicada no ecossistema:** ~**50 MB e ~0,015 CPU** por
sessão.

```
100 sessões ..... ~5 GB · 3 a 5 CPU
1.000 sessões ... ~50 GB · 10 a 16 vCPU
```

**Os "500 por container" da página comercial implicam 13 MB por sessão — não é
crível.** A documentação de engenharia do mesmo fornecedor diz **~100 por
servidor.**

## D.3 O desenho

```
sharding em trabalhadores de 200 a 400 sessões, um banco por trabalhador
NUNCA escalar réplicas do mesmo processo — não existe chave de partição,
   e as réplicas disputariam as mesmas sessões
o Postgres do WhatsApp SEPARADO do operacional,
   com limite de conexão por papel, para que exaustão não escape
```

## D.4 ⚠️ A sincronia completa

A biblioteca força sincronização total de histórico. Num caso público, **844
sessões geraram 43 GB de Postgres.**

**Com centenas de corretoras, é problema de armazenamento e de estabilidade de
onboarding.** Precisa de decisão sobre quanto histórico realmente queremos.

## D.5 Testes

| # | Prova |
|---|---|
| D1 | queda de um shard não afeta os outros |
| D2 | o Postgres do WhatsApp tem limite de conexão por papel |
| D3 | novo pareamento não afeta sessões existentes |
| D4 | o crescimento de armazenamento por sessão é medido e alarmado |

---

# BLOCO E — As dependências que ninguém mapeou

**Registradas aqui porque não estão em SPEC nenhuma, e as três são reais.**

## E.1 O vazamento upstream continua aberto

A biblioteca cria um pool novo a cada reconexão, sem fechar e sem limite.

```
reportado em 4 issues
4 correções propostas — NENHUMA aceita
nenhum commit desde 03/07/2026
a versão `latest` do Docker Hub É a quebrada
```

**Estamos protegidos porque forkamos.** Mas **cada atualização exige reaplicar o
patch** — é dívida permanente, e precisa estar escrita para quem vier depois.

## E.2 O heartbeat de licença

A API exige **heartbeat com a fundação mantenedora** — responde 503 até ativar.

> **É dependência de terceiro na frente de toda a camada de WhatsApp.**

Se a fundação sair do ar, ou mudar os termos, **nosso WhatsApp para.**

**Precisa de:** monitoramento do heartbeat, alerta antes de expirar, e um plano
de contingência escrito.

## E.3 A cláusula de licença

A licença tem cláusula extra: **sistema fechado que usa a biblioteca precisa
exibir aviso visível**, sob pena de exigir licença comercial.

**Para produto white-label, isso é decisão do Founder** — e precisa ser tomada
antes do lançamento comercial, não depois.

---

# 2. Custo por corretora/mês

| Item | Custo |
|---|---|
| Evolution Go (atendimento), rateio | R$ 1 a 3 |
| API oficial, 500 boletos utility | **R$ 18** (~R$ 5 se 70% caírem em janela aberta) |
| SES (relatórios + isolamento) | R$ 0,10 |
| Push | R$ 0 |
| IP por tenant (só acima de ~100 corretoras) | R$ 13 |
| **Total** | **~R$ 20 a 35** |

**Comparação:** Zenvia para os mesmos 500 boletos = **R$ 375 + R$ 649 de setup.**

---

# 3. Gate final

```
[ ] o relatório do Bloco 0, com os preços reconfirmados
[ ] os 6 testes do Bloco A     [ ] os 4 testes do Bloco D
[ ] os 4 testes do Bloco B     [ ] as 3 dependências do Bloco E documentadas
[ ] a suíte inteira verde
[ ] uma corretora migrada e rodando 2 semanas antes da segunda
```

## 3.1 A prova viva

```
1. boleto pelo oficial          → chega, e o custo é registrado
2. cliente responde             → cai na janela de 24h, e a resposta é grátis
3. relatório por e-mail         → chega, com remetente da corretora
4. rejeição num tenant          → não afeta os outros
5. desligar o oficial           → o atendimento reativo continua
```

---

# 4. Riscos

| Risco | Mitigação |
|---|---|
| o preço mudar | Bloco 0 reconfirma antes; a decisão é revista |
| a verificação da Meta demorar | começar cedo; o piloto não depende dela |
| template aprovado limitar demais | desenhar com folga; testar antes de submeter |
| a fundação da biblioteca sair do ar | monitorar heartbeat; plano de contingência escrito |
| migrar as duas corretoras juntas | uma por vez, com 2 semanas de intervalo |
| proxy dar falsa sensação de isolamento | verificar IP de saída depois de conectar |

---

# 5. O que NÃO pode acontecer

```
✗ executar esta SPEC antes de o piloto rodar sem incidente
✗ comprar proxy sem medir banda e sem verificar o IP de saída
✗ pagar por "aquecimento de chip"
✗ migrar as duas corretoras ao mesmo tempo
✗ segundo motor de envio ao lado do que existe
✗ atualizar a biblioteca sem reaplicar o patch
✗ lançar comercialmente sem decidir a cláusula de aviso visível
```

---

# 6. O que fazer HOJE, mesmo com a SPEC congelada

**Três coisas custam pouco e evitam pressa depois:**

```
1. começar as três verificações da Meta
   → é fila de terceiro, e leva semanas. Não depende de código.

2. monitorar o heartbeat da licença
   → se ele expirar sem aviso, o WhatsApp para. Alerta custa uma hora.

3. medir a banda por sessão
   → 7 dias de medição, e a decisão sobre proxy deixa de ser chute
```

**Nenhuma dessas atrasa o piloto. Todas encurtam esta SPEC quando ela descongelar.**
