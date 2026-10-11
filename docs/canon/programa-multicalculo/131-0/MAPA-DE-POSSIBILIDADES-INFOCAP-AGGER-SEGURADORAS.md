# O mapa das possibilidades: InfoCap, Agger e seguradoras

> 11/10/2026 · agente de síntese do gerente (Opus 5.5), modo INVESTIGAÇÃO → registro. Nada foi alterado no produto, no banco, na
> InfoCap nem no Agger: na InfoCap só se fez leitura e login, e no Agger só se leu o código público da página.
> Fontes (todas nesta pasta): [`LAUDO-CORPAPI-COMPLETA.md`](LAUDO-CORPAPI-COMPLETA.md) · [`LAUDO-AGGER-E-MERCADO.md`](LAUDO-AGGER-E-MERCADO.md) ·
> [`LAUDO-COBRANCA.md`](LAUDO-COBRANCA.md) · [`LAUDO-LEITURA-DE-APOLICE.md`](LAUDO-LEITURA-DE-APOLICE.md) · e os anteriores
> [`LAUDO-CORPAPI-ROTA-A-ROTA.md`](LAUDO-CORPAPI-ROTA-A-ROTA.md) · [`LAUDO-PRINTS-DO-CORP.md`](LAUDO-PRINTS-DO-CORP.md).
> Marcas: 📊 medido (o comando está no laudo citado) · 💭 ilustrativo · **FATO / INFERÊNCIA / RECOMENDAÇÃO** separados.
> Notas 0–100 copiadas dos laudos; onde juntei duas ideias, a conta está escrita ao lado. Nenhum nome de cliente ou de pessoa da equipe.

---

## 0. O resumo, em uma página

**O que descobrimos hoje, em oito frases:**

1. **Endosso e renovação não se sobrepõem.** O endosso é um documento "filho" da apólice, com número próprio; ele não apaga a apólice,
   soma-se a ela. A renovação é outra apólice, do ano seguinte. 📊 Em 2025 foram **561 endossos na Resulta e 760 na AutoFleet**.
2. **Nem o Agger nem a InfoCap abrem endosso.** Os dois só LEEM o endosso já feito. Endosso vira SPEC própria, **"assistida"**: o
   agente prepara tudo e uma pessoa executa no portal da seguradora (nota **80**).
3. **A API da InfoCap não dá tudo.** Dá clientes, apólices, parcelas, endossos, itens, produtores e o repasse DEVIDO, sinistros e
   renovações. **Não dá** comissão recebida, fechamento, repasse pago, fluxo de caixa nem metas (📊 60 rotas financeiras testadas → todas
   "não existe"). O caminho para o financeiro é **exportar a planilha do CORP** (nota **85**), não capturar a tela (nota **10**).
4. **Dá para ESCREVER na InfoCap** (19 tipos de escrita), inclusive **cadastrar a proposta fechada mandando o PDF pelo "INCORP"** — o
   mesmo caminho que as corretoras já usam à mão (📊 34 de 60 apólices na Resulta e 54 de 60 na AutoFleet entraram assim). Mas
   **não existe ambiente de teste nem botão de apagar documento**: o primeiro teste gravaria de verdade. Antes, pedir à InfoCap.
5. **Ninguém transmite a proposta sozinho, nem o Agger.** O Agger só abre o portal da seguradora já logado no cálculo, e **uma pessoa**
   termina lá. O caminho seguro para a etapa final, que proponho chamar **"Emissão e registro"**, é: o agente deixa tudo pronto e
   aprovado, a pessoa transmite com um clique, e o agente registra na InfoCap (nota **82**). Transmitir sozinho só por API oficial da
   seguradora (a HDI publica uma; nota **72**).
6. **🔴 O Agger entrega as senhas das seguradoras ao navegador** de qualquer pessoa logada na corretora. O Agger nunca pode ser cofre
   de senhas para um robô nosso (nota **5**, proibido), e você precisa saber disso (tarefa T-152).
7. **A cobrança não "dá muito erro" no robô: dá erro na SENHA.** 📊 Quando o robô entra no portal, ele acerta **13 de 13**. As falhas
   são: senha recusada (Allianz e Mapfre), lista vazia sem explicação (Zurich), e o robô está **parado há 30 dias** (📊 último trabalho
   em 11/09). Trocar duas senhas e religar em modo teste resolve 2 de 3 seguradoras sem uma linha de código (nota **93**).
8. **A leitura da apólice deve vir do PDF do CORP para TUDO** — atendimento, chat, renovação e Quem Cobra Menos —, mas com um **leitor
   melhor**: o de hoje lê inteira só **11 de 32** apólices (📊). A SPEC-130-B deixa de ser "o leitor da cotação" e vira **a ficha única
   da apólice do produto** (nota **90–92**), dentro da peça que já existe, sem criar outra.

**A fila que recomendo** (§10): 130-B ficha única → cobrança estável → 131 renovação → 132 cotação no chat → **Emissão e registro** →
**Endosso assistido** → o financeiro por planilha. **O que é seu** (§11): 2 senhas, 3 capturas de tela, 2 e-mails, 1 conferência no
Agger e 1 alerta de segurança.

---

## (a) Endosso × renovação — sobrepõem? Como a InfoCap faz? Dá no Agger? Vira SPEC?

**FATO — como a InfoCap guarda o endosso** (📊 3 de 3 endossos inspecionados a fundo, e 57/57 + 180/180 filhos com a mãe apontada):
- O endosso é um **documento filho**: tem o seu próprio "nosso número", maior que o da apólice-mãe, e aponta para ela. O número da
  apólice na seguradora é o mesmo da mãe.
- **Não apaga a apólice.** A mãe mantém o próprio prêmio; o endosso tem o dele (positivo se cobra, negativo se devolve). 📊 Um
  cancelamento visto tinha prêmio de −1.111,00. O valor do contrato = mãe + soma dos filhos.
- O **cancelamento** (tipo X) marca a mãe como cancelada ("APÓLICE CANCELADA PELO DOCUMENTO [nº]").
- O item segurado **na data** se lê pela API: 📊 em 7 de 7 trocas de veículo, o carro "antes" e "depois" do endosso eram diferentes.
- Tipos: C (cobra) · R (devolve) · M (sem prêmio) · X (cancela a apólice) · I (tira um item) · F (fatura mensal — não é endosso) ·
  D (proposta devolvida).

📊 **Quantos** (por ano de cadastro, contando C+X+M+R+I):

| | 2025 | 2026 até 11/10 | o motivo mais comum |
|---|---|---|---|
| Resulta | 561 endossos (1.699 apólices) | 222 (1.232) | alteração de item; cancelamento a pedido do segurado |
| AutoFleet | 760 endossos (3.198 apólices) | 636 (2.772) | **troca de veículo** (📊 49 "substituição de itens" entre os endossos de cobrança de ago–set/2026) |

**Sobrepõe a renovação?** **Não.** A renovação é uma apólice NOVA (tipo A) que aponta para a anterior por outro campo. O que importa
para a renovação (INFERÊNCIA forte): ela precisa ler **o item atualizado pelo último endosso** (o carro novo, o endereço novo), não o da
apólice original — senão a renovação cota o carro errado. A API já dá isso (`/itens` com a data).

**Dá para fazer endosso no Agger?** **Não.** 📊 Busca nos 161 arquivos do Agger: nenhuma tela ou chamada abre endosso; ele só mostra o
número do endosso dentro da "Apólice digital". **Pela API da InfoCap?** Também não: nenhuma rota cria endosso. Endosso se faz no portal
de cada seguradora.

**Vira SPEC?** **Sim — "Endosso assistido".** As ideias, com nota (LAUDO-AGGER-E-MERCADO §6 D):

| ideia | nota |
|---|---|
| D1 · o agente **recebe o pedido do segurado e prepara o pacote** (o que muda, documento, apólice) e abre a tarefa; a pessoa executa no portal | **80** |
| D2 · o agente **acompanha** o endosso emitido pela InfoCap e avisa o segurado | **74** |
| D3 · endosso por API oficial (só a Bradesco cita; HDI não lista endosso no auto) | 40 |
| D4 · robô abrindo endosso no portal | 20 |

**RECOMENDAÇÃO:** D1 + D2 numa SPEC só ("Endosso assistido", nota **80** = a da D1; a D2 entra junto porque usa a mesma leitura e fecha
o laço com o segurado). Vem depois de "Emissão e registro" (§10).

---

## (b) Temos acesso a TUDO da InfoCap pela API? O que os prints mostram e a API não dá?

**FATO:** 📊 a coleção oficial da API é a inteira (3 cópias baixadas, idênticas): **12 pastas, 51 requisições, 37 caminhos**. Não há
outra versão nem ambiente publicado.

**O que a API DÁ** (📊 status medido hoje nas duas bases):
- **Cliente:** ficha, contatos, busca por CPF ou nome, as apólices e negócios dele.
- **Apólice:** o documento inteiro (84 campos), parcelas, histórico, situação ("emitido e não recebido"…), o PDF da apólice, os
  endossos, o item segurado na data, os produtores com o repasse DEVIDO.
- **Carteira:** produção por período, renovações, sinistros, uma linha financeira por documento (prêmio, comissão).
- **CRM da Corp** (negócios, tarefas): existe, mas está **parado desde 2024** e não é usado pelas corretoras.

**O que os prints mostram e a API NÃO dá** (LAUDO-CORPAPI-COMPLETA §5.2 e §7):

| tela do CORP | por quê não vem |
|---|---|
| Comissões recebidas / pendentes / diferenças / fechamento | não existe rota (📊 → "não existe") |
| Histórico de comissões importado das seguradoras (INCORP › Comissões) | o INCORP da API é só de propostas |
| Repasse ao produtor **pago** | a API dá o devido, não o pago (📊 data de pagamento vazia em 100 %) |
| Fluxo de caixa, contas a pagar e receber | não existe rota |
| Metas e rankings prontos | não existe; o `/dashboard` existe mas recusa todo parâmetro testado |
| Telefones e observações das seguradoras | a API só dá código e nome |
| Multicálculo da Corp | não existe (o nosso é o do Agger) |

**INFERÊNCIA importante (nota 85):** a base da AutoFleet nasceu em **set/2024 como cópia da base da Resulta**. 📊 2.353 de 2.355
tarefas antigas são idênticas nas duas. Consequência: clientes e negócios antigos aparecem nas duas; contar "clientes da corretora"
pela API dá número inflado, e um número de apólice sozinho não diz de qual base veio (já registrado no BLOCO 0 da 131-0 e em P-INFOCAP-BASES-CLONADAS).

---

## (c) Que serviços e auxiliares NOVOS podemos criar?

| ideia | o que muda para a corretora | nota | de onde |
|---|---|---|---|
| **Emissão e registro** (§f) | o "sim" do cliente vira proposta transmitida e cadastrada na InfoCap sem redigitação | **82** | B1 82 (transmissão humana com 1 clique) + C1 (INCORP) como 2º passo |
| **Endosso assistido** (§a) | pedido de troca de carro/endereço chega pronto à pessoa; o segurado é avisado quando sai | **80** | D1 80 + D2 74 |
| **Financeiro por planilha** | comissão recebida, pendente, repasse e caixa dentro do AutoBrokers, importados do export do CORP | **85** | LAUDO-CORPAPI §5.3 |
| **Cobrança que avisa antes do cancelamento** | 📊 cancelamentos "por falta de pagamento" existem nas duas (7 e 10 na amostra de 2 meses): ligar a cobrança ao risco de cancelar | nota da cobrança, §h | LAUDO-CORPAPI §4.3 + LAUDO-COBRANCA |
| **Acompanhamento de emissão** | alerta "emitido e não recebido" / "recebido e não entregue ao cliente" (📊 amostra de 60 apólices por base: 30 e 14 no 1º estado, 30 e 45 no 2º — Resulta e AutoFleet) | 💭 sem nota de laudo; é leitura pura, entra junto da Emissão e registro | LAUDO-CORPAPI §7 |
| **2ª via da apólice ao segurado** | o PDF da apólice pelo WhatsApp, a pedido | 💭 sem nota de laudo; leitura pura, entra na 130-B (o mesmo PDF) | LAUDO-CORPAPI §7 |
| **Painel de produção e comissão devida** | prêmio e comissão por mês, ramo, seguradora e produtor, calculados por nós | 💭 sem nota de laudo | LAUDO-CORPAPI §5.1 |
| **Sinistralidade na renovação** | a renovação sabe se houve sinistro no ano | 💭 sem nota de laudo; é da 131 | `/sinistros` |

⚠️ As quatro linhas sem nota não foram avaliadas por nenhum investigador; estão aqui como lembrança, não como recomendação.

---

## (d) Dá para EDITAR ou completar a InfoCap pela API? O que deveria ser feito?

**FATO — o que existe de escrita** (19 escritas; **nenhuma foi chamada**, nem de teste):

| o quê | criar | alterar | apagar | risco |
|---|---|---|---|---|
| Cliente | sim | **não** (nome, CPF e nascimento não se corrigem) | sim | duplicar cliente; apagar cliente com apólice = destruição |
| Endereço, e-mail, telefone | sim | sim | sim | baixo-médio |
| Negócio do CRM | sim | não | sim | baixo (CRM parado) |
| Produtor da apólice (repasse) | sim | sim | sim | 🔴 **alto: mexe em dinheiro** do produtor |
| **Apólice/proposta pelo INCORP** (manda o PDF, a IA da Corp lê, nós dizemos o produtor, grava) | sim | não | **não** | 🔴 alto: grava na produção e só se desfaz à mão |

**FATO — o que NÃO existe:** criar ou alterar documento direto (só pelo INCORP), endosso, anexo em documento existente, tarefa,
sinistro, baixa de parcela, comissão, cotação, usuário, apagar documento. **🔴 Não há ambiente de teste:** os dois logins são de
PRODUÇÃO.

**RECOMENDAÇÃO (LAUDO-CORPAPI §8):** não escrever nada até a InfoCap dar **(a) uma base de homologação** e **(b) o formato do JSON do
INCORP** (tarefa T-150). Depois, nesta ordem de valor: **INCORP da proposta fechada** → **contato do cliente** (reversível) →
**produtor da apólice** (só com dupla checagem). Negócio e tarefa da Corp: não vale.

---

## (e) Financeiro, contabilidade e comissões: o que temos, o que falta, vale HAR/F12?

**Temos pela API (FATO):** prêmio de cada documento; **comissão devida** (no endosso de cancelamento ela vem negativa); parcelas com
vencimento; **repasse devido ao produtor** (📊 confere com a conta "% × comissão" em 52/53 e 57/57).

**🔴 Cuidado (FATO):** a "data de pago" da parcela **não prova que o cliente pagou.** 📊 Ela é igual ao vencimento em 208/212 e 395/403
parcelas, e há "pago" em parcela que **ainda vai vencer** (30/126 e 171/241). INFERÊNCIA (nota 70): é baixa automática por previsão.
Nunca dizer ao segurado "consta pago" ou "consta em aberto" só por esse campo (P-INFOCAP-PARCELA-PAGA). E o relatório BI da API
**esquece documentos** (📊 74 de 275 num mês), então o financeiro completo usa a lista de documentos, não só o BI.

**Falta:** comissão recebida, pendente, diferenças, fechamento, repasse pago, fluxo de caixa, metas.

**Vale HAR/F12?** (LAUDO-CORPAPI §5.3)

| caminho | traz | nota |
|---|---|---|
| captura (HAR) do **CORP clássico** | desenho de tela, não dados (é um programa de Windows transmitido ao navegador) | **10** |
| captura (HAR) do **CorpNow** (Produção + abrir uma apólice) | os parâmetros do `/dashboard`; **não** chega ao financeiro | **65** |
| **exportar do CORP clássico** (Gerenciador de Relatórios → Excel): Comissões Recebidas, Comissões Pendentes, Repasse ao Produtor, Fluxo de Caixa – Extrato Diário | o financeiro inteiro, em planilha | **85** |
| pedir à InfoCap rotas de comissão e extrato | API oficial | **75** |

**RECOMENDAÇÃO:** o export em planilha (T-153) e, em paralelo, o pedido à InfoCap (T-150). A captura do CorpNow é opcional.

---

## (f) Depois que o cliente fecha: efetivar na seguradora e cadastrar na InfoCap — e o nome da etapa

**Efetivar (transmitir) a proposta — FATO:** o Agger **não transmite** (📊 nenhum dos 161 arquivos tem transmissão, emissão ou
efetivação). O "Fechar negócio" do Agger é só anotação de CRM. O que ele tem é o botão **"Ver na seguradora"**: uma extensão do Chrome
abre o portal da seguradora já logado naquele cálculo, e **uma pessoa** termina.

| ideia (LAUDO-AGGER §6 B) | nota |
|---|---|
| B1 · **o agente deixa a proposta pronta e aprovada** (dados conferidos, aceite do cliente, Approval) e **a pessoa transmite com 1 clique** pelo "Ver na seguradora" | **82** |
| B2 · **API oficial de efetivação da HDI** (cotação → efetivação → proposta → status), depois Yelum e Bradesco | **72** (é ENVIO de verdade: nível CRÍTICO e Approval sempre) |
| B3 · robô transmitindo no portal | 30 (irreversível, mexe em dinheiro, antirrobô) |
| B4 · Open Insurance | 10 (exige ser "SPOC": S.A. com R$ 1 mi de patrimônio) |

**Cadastrar na InfoCap — FATO:** só pelo **INCORP** (§d). 📊 É o caminho que as corretoras já usam à mão.

| ideia | nota | conta |
|---|---|---|
| C1 · **INCORP**: PDF da proposta → a IA da Corp lê → nós dizemos o produtor → grava | **78** | os laudos dão 83 (Agger, como ideia) e 75 (CorpAPI, pesando a escrita nunca testada); uso a média até haver homologação |
| C2 · **perguntar à InfoCap/Dimensa se o Agger já alimenta a Corp** (mesmo grupo; a Corp tem campos de "multi") | **78** | pode ser zero código; custa um e-mail (T-150) |
| C3 · registrar o negócio no CRM da Corp (sem o PDF) | 70 | complementa C1; CRM parado |
| C4 · robô digitando na tela da Corp | 25 | a API existe |

**Dá por API ou só por portal?** **Transmitir:** só portal (humano), salvo HDI por API oficial. **Cadastrar na InfoCap:** por API
(INCORP), depois da homologação.

**O nome da etapa — decisão (D-1311-06):**

| nome | nota | por quê |
|---|---|---|
| **Emissão e registro** | **86** | é como a corretora fala ("já emitiu?"); o próprio CORP chama a fase de "emissão"; "registro" cobre o cadastro na InfoCap |
| Do sim à apólice | 78 | bonito, mas não diz o que faz num menu |
| Efetivação e cadastro | 62 | "efetivação" é jargão de portal |
| Pós-venda | 35 | confunde com atendimento e pós-acionamento |

**RECOMENDAÇÃO:** SPEC "Emissão e registro" = B1 (agora) + acompanhamento da emissão pela InfoCap + C1 (quando houver homologação) +
B2 (quando a HDI der acesso).

---

## (g) Usar o Agger como ponte para os portais (Porto via Agger), boletos e efetivação — dá?

| uso do Agger (LAUDO-AGGER §6 E) | dá? | nota |
|---|---|---|
| E1 · multicálculo (o que a 129-B/C já faz) | ✅ provado | **90** |
| E2 · "Ver na seguradora" para a **pessoa** transmitir (= B1) | ✅ (todas, salvo 2 seguradoras com "acesso indisponível") | **82** |
| E3 · parceria com a Dimensa (dona do Agger, da InfoCap e da Quiver) por API | depende deles | **65** |
| E4 · ler as "Sincronizações" do Agger (apólice digital, proposta, extrato de comissão, parcelas pendentes) | ⚠️ não sabemos se as nossas contas têm o módulo (📊 o menu não apareceu nos robôs) | **55** |
| A5 · "Parcelas pendentes" do Agger como lista de cobrança | lista sem boleto; módulo não medido | **50** |
| E5 · pegar as senhas das seguradoras do Agger para robôs nossos | 🔴 **proibido** | **5** |

**Porto via Agger:** o Agger só **abre** o portal da Porto logado para a pessoa; não emite, não baixa boleto. **Boleto:** o Agger
**não baixa boleto** (📊 a tela de parcelas não tem PDF). **Efetivação:** não.

**🔴 Achado de segurança (FATO, LAUDO-AGGER §2.5):** para o "Ver na seguradora", a página do Agger monta login **e senha** da
seguradora e os entrega à janela do navegador para "qualquer ouvinte". Logo, **qualquer pessoa com login no Agger da corretora pode
obter as senhas das seguradoras**. RECOMENDAÇÃO: (a) o Agger nunca é cofre de senhas para nós (D-1311-03); (b) o robô nunca grava a
resposta de configuração de seguradora nem roda com extensão de terceiro; (c) você decide quem tem login no Agger e, se alguém sair,
troca as senhas no Agger **e** na seguradora (T-152).

---

## (h) Cobrança estável em todas as seguradoras — por que falha hoje, e o desenho estável

**Por que falha (FATO, LAUDO-COBRANCA):**
- 📊 **Quando entra no portal, o robô acerta 100 %:** 13 de 13 varreduras concluídas baixaram um boleto para cada inadimplente.
- 📊 Nas duas últimas execuções (10 e 11/09), **3 de 6** seguradoras deram certo — **as mesmas três**: HDI, Tokio, Yelum.
- **Allianz:** o portal diz *"Acesso negado — valide os dados"* → **senha recusada**. **Mapfre:** *"Autenticação inválida!"* → senha
  recusada; 📊 nunca houve uma varredura Mapfre concluída. **Zurich:** entra, mas a lista volta **vazia** (46 bytes), duas vezes — não
  se sabe se é recusa silenciosa ou carteira sem Zurich.
- 📊 **O robô está parado há 30 dias** (último trabalho 11/09; a rotina e o auxiliar estão pausados). Tudo o que se endureceu depois
  (o teste de login antes da varredura, o disjuntor de saúde) **nunca rodou** (📊 0 testes de login na história).
- 🔴 **Risco ao religar:** 📊 a execução com 6 seguradoras leva 831–893 s, contra um teto de 900 s; o teste de login acrescenta 6
  logins na mesma fila → tende a estourar (INFERÊNCIA forte, a medir).
- Não é captcha, nem dois fatores, nem lentidão do portal em nenhuma falha medida.

**O desenho estável (FATO):** o desenho atual — **navegador só para entrar, chamadas diretas para ler e baixar** — já é o estável:
📊 8/8 nas três seguradoras que o usam de ponta a ponta. O que falta é senha, a lista da Allianz (ainda por cliques) e a lista da Zurich.

| opção | nota | de onde |
|---|---|---|
| **A. trocar as 2 senhas + religar em modo teste por 3 dias úteis, com o teto subido para 1.800 s** | **93** | LAUDO-COBRANCA |
| B. Allianz: trocar os 20 cliques até a lista pela chamada direta (exige a captura HAR da Allianz) | **86** | LAUDO-COBRANCA |
| A1. consolidar o que existe: sessão guardada no cofre, login assistido 1× pelo corretor, teste diário | **85** | LAUDO-AGGER |
| C. Zurich: decidir o vazio com a captura HAR da corretora | **82** | LAUDO-COBRANCA |
| A2. API oficial da HDI (parcelas + 2ª via do boleto) e Yelum | **82** | LAUDO-AGGER |
| A3. a InfoCap como detector do que está em aberto e do boleto já anexado | **75** (com a ressalva da data de "pago", §e) | LAUDO-AGGER |
| A4. Porto e Bradesco por API oficial | **68** | LAUDO-AGGER |
| D. HAR da HDI como régua | 60 | LAUDO-COBRANCA |
| G. só religar como está | 45 | LAUDO-COBRANCA |
| E. login sem navegador | 35 | LAUDO-COBRANCA |
| A6. navegador contornando antirrobô na Porto/Bradesco | 25 | LAUDO-AGGER |
| F. "agente que clica olhando a tela" | 20 | LAUDO-COBRANCA |
| A7. Open Insurance | 15 | LAUDO-AGGER |

**RECOMENDAÇÃO:** A agora (T-145 + T-146); depois uma SPEC "cobrança estável" = B + C + A1, com A2 quando a HDI responder (T-149).

---

## (i) A leitura de apólice: o PDF do CORP deve valer para TUDO? Onde a estrutura de hoje é pior?

**FATO (LAUDO-LEITURA-DE-APOLICE):**
- O produto **já usa** o PDF do CORP no chat e no atendimento (📊 21 PDFs guardados, 21/21 processados).
- **O defeito não é a fonte, é o leitor.** 📊 Rodando o leitor real do produto em 32 apólices da janela de renovação: ele lê a apólice
  **inteira** (a soma das coberturas = o prêmio) em **11 de 32** — só Allianz residencial/condomínio e HDI condomínio. Tokio, Allianz
  empresarial, Alfa, HDI auto: **0 linhas**. Sura e Yelum: o leitor **quebra** e nem o texto chega.
- 📊 A API estruturada (`/itens`) fecha o prêmio em **4 de 8 autos** e em **0 de 24** apólices de residencial/condomínio/empresarial.
- 📊 O PDF existe em **28 de 32** apólices.
- Há **quatro leitores** de documento de seguro no produto, e **só um** monta a ficha da apólice.

**Deve valer para tudo?** **Sim, como FONTE das coberturas** (é o contrato) — com a regra que já existe: **cobertura, limite, franquia
e plano vêm do documento; parcela, situação e vigência vêm da InfoCap**.

| opção (LAUDO-LEITURA §6.1) | nota |
|---|---|
| **A. a ficha única = a que já existe no código, alimentada por UM leitor com motor novo**, consumida por atendimento, chat, renovação, cotação e Quem Cobra Menos | **90** |
| D. modelo de IA em todo PDF, sem a leitura grátis | 60 |
| B. a 130-B como leitor novo só para WhatsApp/QCM/chat | 35 |
| C. só a API estruturada | 30 |

**Onde a estrutura de hoje é pior (FATO):** o PDF que o segurado manda pelo WhatsApp ou pelo chat vai **cru** ao modelo, cortado em 20
mil letras, sem ficha (📊 2 de 6 "não foi possível ler") · o leitor de linhas só conhece 2 layouts · uma página ruim derruba o PDF
inteiro · só se usa o link da apólice, não a lista de anexos · o leitor de reserva trava o servidor e devolve 1 página · teto de 60
itens (apólice de 105 páginas: 7 % lido) · **nada registra se a leitura deu certo** · a renovação não usa a ficha · `/itens` sem data
falha exatamente na renovação.

**RECOMENDAÇÃO:** a 130-B vira **"a ficha única da apólice"** (D-1311-01, nota **92 × 40** o escopo antigo): a nota 92 é a do laudo para
a opção A (90) somada ao ganho de abrir já, porque a 131, a 132 e a 133-B dependem dela. Proposta pronta:
[`../../specs-propostas/SPEC-130-B-A-FICHA-UNICA-DA-APOLICE.md`](../../specs-propostas/SPEC-130-B-A-FICHA-UNICA-DA-APOLICE.md).

---

## 10. O QUE RECOMENDO, EM ORDEM

| # | o quê | tipo | nota | depende de |
|---|---|---|---|---|
| 0 | **As tarefas sem código** (§11): senhas, capturas, e-mails, conferência no Agger, alerta | 🧑 você | — | nada |
| 1 | **Religar a cobrança em modo teste** (teto 1.800 s, 3 dias úteis, medir o teste de login) | 🤖 tarefa curta | **93** | T-145, T-146 |
| 2 | **SPEC-130-B · a ficha única da apólice** (chat novo) | 🤖 SPEC | **92** | nada; bancada = as 32 apólices já medidas |
| 3 | **Cobrança estável** (Allianz direto na lista · Zurich decidida · sessão guardada e login assistido · HDI por API quando vier) | 🤖 SPEC | **86** (a maior das peças B/A1/C) | T-147, T-148; T-149 para a HDI |
| 4 | **131 · renovação** (lê a ficha da 130-B e o item atualizado pelo endosso) | 🤖 SPEC | já na fila (D-MC-61) | 130-B · T-144 |
| 5 | **132 · cotação no chat** | 🤖 SPEC | já na fila | 130-B |
| 6 | **Emissão e registro** (transmissão humana com 1 clique + acompanhamento da emissão + INCORP quando houver homologação) | 🤖 SPEC | **82** | T-150 para o INCORP |
| 7 | **Endosso assistido** (prepara + acompanha) | 🤖 SPEC | **80** | a ficha da 130-B |
| 8 | **Financeiro por planilha** | 🤖 SPEC | **85** (alta, mas depende do export) | T-153 |

A 133-B, a 135 e as seguintes **seguem a fila atual**; esta lista só encaixa as peças novas. Por que a cobrança estável (3) vem antes da
131: ela já está construída e parada, e **a cobrança é dinheiro chegando à corretora toda semana**; a 130-B vem antes de tudo porque
três SPECs dependem dela. ⚠️ É **PROPOSTA do gerente** (registrada em `FOUNDER-DECISIONS.md` como D-1311-02); a fila oficial só muda
com o seu "ok".

---

## 11. O QUE PRECISA DE VOCÊ

Passo a passo em [`../../TAREFAS-DO-FOUNDER.md`](../../TAREFAS-DO-FOUNDER.md), seção "⓪ AGORA — o mapa de 11/10".

| tarefa | o quê | tempo 💭 | destrava |
|---|---|---|---|
| **T-145** | entrar à mão na **Allianz** e na **Mapfre** com a conta cadastrada, trocar a senha se não entrar e salvar a nova no conector | 15 min | a cobrança em 2 seguradoras |
| **T-146** | religar a cobrança em modo teste (uma variável no EasyPanel + pedir no chat) | 10 min | medir o teste de login e a saúde das contas |
| **T-147** | captura HAR da **Allianz** (login → Parcelas inadimplentes → 2ª via) | 10 min | tirar os 20 cliques da Allianz |
| **T-148** | captura HAR da **Zurich** (Parcelas vencidas, 90 dias) + print do resultado; depois, sem pressa, a da **HDI** | 15 min | decidir o vazio da Zurich; régua da HDI |
| **T-149** | e-mail à **HDI** pedindo acesso de parceiro às APIs (efetivação, parcelas, 2ª via do boleto) | 5 min | cobrança e transmissão por API na HDI (e talvez Yelum) |
| **T-150** | e-mail à **InfoCap/Dimensa**: base de teste do INCORP e formato do JSON; o Agger já alimenta a Corp?; rotas de comissão; parâmetros do `/dashboard` | 5 min | cadastrar a proposta fechada; o financeiro por API |
| **T-151** | no **seu** login do Agger, ver se aparece o menu **"Sincronizações"** e quais seguradoras estão ativas (só olhar) | 5 min | saber se E4/A5 valem |
| **T-152** | 🔴 **o alerta das senhas**: decidir quem tem login no Agger; se alguém saiu, trocar as senhas das seguradoras | 10 min | segurança das contas das seguradoras |
| **T-153** | (quando quiser o financeiro) exportar do CORP clássico 4 relatórios em Excel | 20 min | o financeiro por planilha |

**Decisões que já vêm tomadas com nota** (você só confirma se quiser): D-1311-01 a 130-B como ficha única em chat novo (92 × 40) ·
D-1311-03 o Agger nunca como cofre de senhas (a ideia contrária, E5, tem nota 5) · D-1311-04 escrever na InfoCap só depois da
homologação (88 × 30 — notas do gerente-síntese, sobre a recomendação 1 do LAUDO-CORPAPI §8) · D-1311-05 endosso = SPEC própria
assistida (80 × 20, D1 × D4) · D-1311-06 o nome "Emissão e registro" (86 × 78). **A que espera você:** D-1311-02, a fila nova.
