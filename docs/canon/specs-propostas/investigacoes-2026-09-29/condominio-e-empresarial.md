# Condomínio e empresarial pelo agente: dá para fazer?

**Investigação só de leitura** · 29/09/2026 · main `c310e77` · nenhuma mensagem enviada, nada gravado no banco, nenhum modelo chamado.
Corretora **R** = `04b5cdbc…` (a atendente de residencial, condomínio e empresarial) · Corretora **A** = `6c9c55e2…` (auto). PII mascarada: nenhum nome, CNPJ, telefone ou endereço aparece aqui.
Scripts e saídas em `scratchpad/inv-condo-empresa/` (`p3`–`p8.py` para as URAs, `at2`–`at8.py` para as conversas com clientes, `pl.py`/`pl2.py` para a base de planos).

## Resposta curta

**Hoje não dá para fazer corredor de ponta a ponta, sem errar, sem travar e sem pessoa, para quase nenhuma combinação.** Existe **uma** exceção técnica: **Allianz × condomínio × serviços emergenciais** (encanador, desentupimento, eletricista, chaveiro). A URA dela é a mesma do residencial, com quase as mesmas telas, e **2 das 4 tentativas novas de 2026 terminaram em protocolo sem ninguém da seguradora**. O problema vem depois: **3 dos 5 chamados de condomínio agendados na Allianz deram problema no pós-atendimento** (prestador não foi, prestador pediu autorização ou peças). E o volume é pequeno: **cerca de 1 pedido novo de condomínio por mês**. Minha recomendação é **manter com a atendente agora** e deixar uma SPEC pequena pronta, **com aprovação dela em um toque**, para ser aberta depois de três condições (item 5).

## 1. Volume, de 28/07/2025 a 29/09/2026 (14 meses)

📊 Fonte 1: conversas com as URAs (`observed_events`, 33.628 eventos, 689 sessões). Classifiquei cada sessão de condomínio e empresarial lendo o menu escolhido e as telas (`p3.py`, `p4.py`, lista manual em `p6.py`). Para auto e residencial usei palavras-chave, então esses números são **estimativa**:

| sessões com a URA | condomínio | empresarial | residencial (est.) | auto (est.) |
|---|---:|---:|---:|---:|
| Corretora R | **18** | **8** (1 delas é sinistro) | ~131 | ~56 |
| Corretora A | 0 | 0 (as 5 com "empresa" são frota de auto) | ~14 | ~320 |

📊 Fonte 2: conversas da corretora com os segurados (`attendance_sessions`/`attendance_transcripts`, filtro `company_id`, `at2.py`–`at8.py`). O classificador do produto (`summary.distilled.ramo`) **não tem** condomínio nem empresarial, então busquei as palavras (condomínio, síndico, zelador, administradora, prumada, empresarial) e li cada sessão. No mesmo período, pedidos de **assistência**: residencial **215** e auto **72** na R; auto **384** na A.

**Condomínio:** separei **13 pedidos novos de assistência** para áreas comuns e **9 contatos de acompanhamento** (visita que não aconteceu, reembolso, laudo, retorno). Isso dá **~1 pedido novo por mês**.
- Por seguradora: **Allianz 10**, Tokio 2 (chegam por link), Porto 1, e 1 de seguradora desconhecida (provavelmente foi por telefone). A Tokio mandou ainda **3 pesquisas de satisfação** endereçadas a condomínios, o que mostra assistências abertas fora do WhatsApp.
- Por serviço: encanador ou desentupimento **7**, vigia 2, eletricista 2, calha 1, caixa d'água 1.
- Desfecho: **5 agendados ou com protocolo** · **4 sem cobertura** (bomba ou cisterna, calha, vigia sem sinistro, limite do ano esgotado) · 2 consultas que não viraram chamado · 2 que pararam num link.
- ⚠️ Várias conversas com "condomínio" são **apartamentos com apólice residencial**. Separei esses casos um a um.

**Empresarial:** **9 pedidos novos**, todos da corretora R, em lojas. Allianz 6, Porto 2, Tokio 1. Desfecho: **1 agendado** (encanador) · **6 sem cobertura ou "não é esse serviço"** (lâmpadas duas vezes, filtro de água, caixa de gordura, papa-entulho, porta de correr, e uma apólice da Porto sem assistência) · 1 link · 1 abandonado.

**Sinistro:** 📊 **325 sessões** com palavra de condomínio foram classificadas como sinistro pelo destilador, com **121 contrapartes** diferentes (`at5.py`/`at6.py`). O número inclui algum residencial dentro de condomínio. Mesmo assim, o volume de sinistro de condomínio é **mais de 10 vezes** o de assistência. Sinistro continua com pessoa, como você decidiu.

## 2. Como cada seguradora atende

| seguradora | canal de condomínio e empresarial | até onde a conversa gravada chega |
|---|---|---|
| **Allianz, condomínio** | **Mesmo WhatsApp e mesmo menu do residencial.** Desde 01/04/2026 existe a tela "1 Residencial · 2 Condomínio · 3 Empresarial" (📊 57 sessões). O caminho 2 pede CNPJ, confirma o endereço e o número do condomínio, pede uma referência e o telefone, avisa que "os serviços são exclusivamente das áreas comuns… unidades não", e depois pede tipo de serviço, profissional, quando, o que aconteceu e a descrição. Fecha com um resumo, o **protocolo e a senha** (os 4 últimos dígitos do telefone). "Outros serviços", como vigia, vai para uma pessoa da seguradora. | 📊 7 sessões passaram pela tela do CNPJ (`p8.py`). Das **4 tentativas novas**: **2 terminaram com protocolo** sozinhas · 1 chegou ao resumo e foi para um especialista porque o **limite do ano estava esgotado** · 1 recebeu "**Apólice não encontrada**" duas vezes, com a apólice válida no portal (erro da URA), e foi para um especialista. Antes de 2026 a atendente digitava "cond" e sempre caía com uma pessoa. |
| **Allianz, empresarial** | Opção **3 → "Vou transferir seu caso para um especialista"**, **sempre**. | 📊 Todas as sessões que escolheram 3 foram para uma pessoa. **Não existe autoatendimento empresarial.** |
| **Tokio** | O WhatsApp identifica o CNPJ e devolve um **link para o portal web** de assistência 24h (chaveiro, encanador, eletricista). Os outros reparos são por telefone. | 📊 4 sessões (2 de condomínio, 1 empresarial, 1 com CNPJ não reconhecido): todas terminam no link. O acervo `tokio-condominio.jsonl` tem só isso (16 linhas). Não temos robô para esse portal. |
| **Porto** | CNPJ → "Outros produtos Porto" → "Seguro Condomínio" ou "Seguro Empresa" → Serviços de assistência → Novo serviço → **uma pessoa**. | 📊 3 sessões: condomínio com a calha sem cobertura; empresa sem assistência na apólice; 1 abandonada. |
| Sompo | Sinistro empresarial é tratado com o **analista, por e-mail**. | Fora do escopo (é sinistro). |
| Bradesco, Mapfre | Há planos de condomínio na base. | 📊 **0** sessões de condomínio na URA. |

**O que o condomínio pede a mais que o residencial:** CNPJ no lugar de CPF, o **número do condomínio**, a **área comum** (a URA avisa, mas não confere) e o **telefone de quem recebe o prestador**. A atendente pediu para trocar esse telefone pelo do síndico ou de quem estaria no local **em pelo menos 4 sessões** (`cand.txt`). Na Allianz, "vigia" pede data e hora de entrada e de saída. No empresarial, a pessoa da Allianz pergunta o endereço e qual das apólices quando há mais de uma, e explica o que cobre.

## 3. Onde está o risco

1. **Quem pede.** Nas conversas aparecem síndico ou síndica, subsíndico, zelador ou zeladora, **administradora** (com resposta automática "urgência: fale com o síndico"), conselheiro, **morador** ("meu banheiro… a conta do condomínio vai ser grande") e o **colega vendedor**, que repassa os casos (📊 uma só contraparte interna em 31 sessões de sinistro de condomínio). Na base, a Tokio diz: "**acionamento somente pelo síndico, subsíndico ou representante legal**".
2. **Área comum ou unidade.** Um pedido real foi "cano do condomínio vazando para a unidade X", e a própria atendente perguntou a um cliente "foi para a sua unidade ou para o condomínio?". Errar isso gera recusa no local ou gasta o uso do ano na apólice errada. O código atual já trata esse erro como defeito (`insurer_dispatch_service._apolice_de_areas_comuns`).
3. **Limite muito curto.** Pela base publicada, a Allianz de condomínio paga **R$ 100 por evento e R$ 200 por vigência** em encanador e eletricista (**2 usos por ano**), e encanador e desentupimento contam como eventos separados. A Tokio dá 2 intervenções por ano nas áreas comuns. A Porto tem teto anual de R$ 1.200 a R$ 1.800. **Um acionamento errado gasta metade do ano.** 📊 Já aconteceu uma vez: "limite de cobertura desse serviço foi atingido".
4. **Sinistro ou assistência.** A atendente pergunta antes se vale abrir sinistro por causa da franquia, e se o vazamento está aparente. É uma decisão de dinheiro, não de tela.
5. **O pós-atendimento é o maior custo.** 📊 **3 de 5** chamados de condomínio agendados na Allianz voltaram com problema (prestador não foi duas vezes; prestador não fez o serviço sem autorização e peças). Houve ainda um de seguradora desconhecida em que o prestador chegou e não achou ninguém. Cada caso gerou de 2 a 4 conversas novas com a seguradora, pedido de laudo e reembolso.
6. **Cliente grande.** O mesmo condomínio aparece em **5 conversas de assistência entre fevereiro e junho de 2026** (📊 contraparte `..0975`, `at8.py`). É uma conta que a atendente conhece pelo nome do síndico.
7. **Empresarial quase sempre não cobre** (6 de 9). Com a Allianz, o pedido sempre passa por uma pessoa da seguradora. E a base de planos tem **0 planos empresariais** (📊 `pl.py`: 129 planos, 11 de condomínio, 0 empresariais). O agente não teria como responder "cobre" ou "não cobre".

## 4. Nota de viabilidade de corredor de ponta a ponta HOJE (0–100)

| seguradora × ramo × serviço | nota | o que falta |
|---|---:|---|
| Allianz × condomínio × encanador/desentupimento | **55** | Religar o passo `cnpj_condominio` (saiu de propósito na SPEC-119). Pegar do caso o número do condomínio e o telefone de quem recebe. Ter uma regra de área comum ou unidade com prova. Tratar "Apólice não encontrada" e "limite atingido". Os passos seguintes já existem no corredor residencial (`numero_condominio`, `aviso_areas_comuns`). |
| Allianz × condomínio × eletricista/chaveiro | **45** | O mesmo fluxo, mas **0 aberturas observadas**. A única tentativa de eletricista (bomba d'água) não tinha cobertura. |
| Allianz × condomínio × outros (vigia etc.) | **10** | Vai para uma pessoa da seguradora e depende de ter sinistro. |
| Tokio × condomínio (chaveiro/encanador/eletricista) | **15** | Um robô para o portal web de assistência 24h, que não existe. Só o síndico pode pedir. |
| Porto × condomínio | **10** | Sempre uma pessoa da seguradora. 1 caso, sem cobertura. |
| Bradesco/Mapfre × condomínio | **5** | Nenhuma tela gravada. |
| Allianz × empresarial (qualquer serviço) | **10** | Sempre uma pessoa da seguradora. A base não tem o plano empresarial. |
| Porto × empresarial | **5** | Sempre uma pessoa da seguradora. Houve apólice sem assistência. |
| Tokio × empresarial | **10** | Link para o portal. |

## 5. Recomendação

| opção | nota |
|---|---:|
| **A. Manter com a atendente agora, com o dossiê que já existe (SPEC-119 bateria 5), e medir por 60 dias quantos pedidos de condomínio chegam** | **80** |
| **B. Depois de X: SPEC pequena só para Allianz × condomínio × emergenciais, com aprovação da atendente em um toque antes de enviar** | **65** |
| C. SPEC agora para condomínio e empresarial de ponta a ponta, sem pessoa | **10** |
| D. Só empresarial agora | **5** |

**Por que A vence:** o ganho é pequeno. Seriam cerca de **4 chamados por ano** que caberiam no corredor da Allianz (os de 2026), contra **~215** assistências residenciais. E o risco fica justamente nos casos de conta grande e de limite de 2 usos por ano. **A diferença entre A e C é grande, então essa decisão já vem tomada.**

**O "X" da opção B**, as três condições:
1. o corredor residencial da Allianz passa no canário com casos reais, porque as telas são as mesmas;
2. a atendente responde as perguntas 1 a 3 abaixo;
3. o volume medido chega a **3 ou mais pedidos novos de condomínio Allianz por mês**.

**Desenho mínimo seguro da opção B:**
1. Só Allianz, só condomínio, só **encanador, desentupimento, eletricista e chaveiro**.
2. O agente monta o caso: CNPJ **da apólice cadastrada**, número do condomínio, área comum descrita, telefone de quem recebe (síndico ou zelador) e se já existe prestador.
3. **A atendente aprova com um toque** (é um Approval de verdade, não uma frase no prompt). Só então o agente conversa com a URA.
4. Vai para uma pessoa, com dossiê, em "Apólice não encontrada", "limite atingido", "Outros serviços", em qualquer transferência para especialista e sempre que o pedido citar uma **unidade** ou um **morador**.
5. O protocolo e a senha vão para o **síndico** e para a atendente.
6. O **acompanhamento** (prestador que não veio, peças, reembolso) continua com a atendente.
7. Empresarial, Tokio, Porto e sinistro continuam com pessoa.

## 6. Cinco perguntas para a atendente

1. Em cada condomínio, **quem pode pedir** assistência: só o síndico, ou também zelador, administradora e conselheiro? Se um **morador** pedir, o que você faz?
2. O que você **confere antes de acionar**: se é área comum ou unidade, se já tem prestador, se vale mais abrir sinistro por causa da franquia, quantos usos do ano sobraram? Já perdeu um uso do ano à toa?
3. **Qual telefone vai no chamado**: sempre o do síndico ou do zelador? E quem recebe o prestador à noite e no fim de semana?
4. Nos empresariais, que quase sempre **não cobrem**: você aceitaria que o agente respondesse "a apólice não cobre isto" direto ao cliente, se a informação viesse da apólice? Ou isso passa sempre por você?
5. Quais **clientes** (condomínios ou empresas) você **não quer que o robô toque de jeito nenhum**? E em qual seguradora está a maior parte da sua carteira de condomínio hoje?

---
**FATO:** as contagens com 📊, cada uma com o script ao lado. **INFERÊNCIA:** "cerca de 1 por mês" e "cerca de 4 por ano no corredor Allianz" saem de 13 casos. Os números de residencial e auto vindos da URA são estimativa por palavra-chave. **RECOMENDAÇÃO:** a tabela do item 5. Nenhum motor paralelo foi proposto: o desenho B reaproveita o corredor residencial da Allianz, a trava `_apolice_de_areas_comuns` e a Approval que já existe.
