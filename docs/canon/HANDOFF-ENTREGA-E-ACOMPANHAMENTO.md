# HANDOFF — a ENTREGA (2ª etapa) e o ACOMPANHAMENTO (3ª etapa)

> Para a sessão que vai fazer o Auxiliar de Cobrança **falar com o segurado**.
> Escrito em 14/08/2026, ao fechar a 1ª etapa (a colheita).
>
> **Leia antes:** `CLAUDE.md` · `SPEC-070` · `docs/canon/PENDENCIAS.md`
> (P-153, P-158) · os runbooks em `docs/canon/portais/`.

---

# 1. O QUE JÁ ESTÁ PRONTO — e não deve ser refeito

📊 **Seis seguradoras colhem inadimplente e baixam boleto**, com journey
testada e gate exercitado contra o portal real:

| Seguradora | Estado | Prova |
|---|---|---|
| Allianz | 🟢 | 10 de 10 boletos no bucket, usada como linha de controle |
| HDI | 🟢 | jobs `done` pela fila de produção |
| Tokio | 🟢 | jobs `done` pela fila |
| Yelum | 🟢 | jobs `done` pela fila |
| MAPFRE | 🟢 | 2 de 2 boletos, guarda cross-tenant por `brokerId` |
| Zurich | 🟢 | boleto por `GerarBoleto2`, 107.288 bytes `%PDF` |

📊 **O deploy funciona.** Em 14/08 um job `zurich_corretor.cobranca_sweep`
enfileirado à mão rodou no worker do EasyPanel e terminou `done`, lendo 43
parcelas. A imagem no ar tem tudo.

> 🚫 **Não reabrir**: nenhuma journey, nenhum parser de portal, nenhuma
> fixture. A 1ª etapa está fechada. O que falta é depois dela.

---

# 2. O DESENHO QUE NÃO SE NEGOCIA

```
COLHER    uma entrada por portal. Baixa TODOS os boletos. NÃO envia.
          É por seguradora, e está pronto.

ENTREGAR  independente, ordenada, governada, em horário comercial.
          É do AUXILIAR, não do portal — UMA regra para as SEIS.

ACOMPANHAR  quem não pagou continua na lista semana que vem.
            Hoje NÃO EXISTE.
```

🔴 **As regras de entrega valem para TODAS as seguradoras.** A colheita é
específica de cada portal; a conversa com o segurado é uma só. Uma regra
"da Zurich" seria o começo de seis auxiliares em vez de um.

---

# 3. 🔴 O BURACO PRINCIPAL — auditado em 14/08

**Nada liga a cobrança à InfoCap para achar o WhatsApp do segurado.**

📊 O que foi verificado no código:

```
backend/app/services/billing_collection.py     existe, 1.226 linhas
  fila_de_cobranca()                            separa quem pode ser cobrado
  ordenar_para_entrega()                        ordena a entrega
  _find_whatsapp_integration()                  acha a INSTÂNCIA que envia
  grep por "infocap"                            -> só uma string de config

backend/app/agents/tools/infocap_tool.py       existe — mas é ferramenta do
                                                CHAT, não da cobrança

quem preenche item["whatsapp"]                 -> NINGUÉM
```

📊 E **nenhum dos seis portais entrega telefone utilizável**:

| Portal | O que dá | O que falta |
|---|---|---|
| Allianz | CPF/CNPJ | telefone |
| HDI | CPF/CNPJ | telefone |
| Tokio | CPF/CNPJ; 🔴 o telefone do portal **se contradiz** entre duas telas | telefone confiável |
| Yelum | CPF/CNPJ (2ª chamada); `TelePhoneNumber` vem **vazio** | telefone |
| MAPFRE | CPF/CNPJ na própria lista; `mainPhone` **vazio** | telefone |
| Zurich | CPF/CNPJ (2 chamadas); tem `TelefoneSegurado` preenchido | — mas a fonte única é a InfoCap |

> **A ponte é: CPF/CNPJ → InfoCap → WhatsApp.** É a peça que falta, e é a
> primeira coisa a construir na 2ª etapa. Sem ela, a fila monta e não sai
> mensagem nenhuma.

📊 As credenciais da InfoCap já existem no ambiente
(`CORP_INFOCAP_RESULTA_*` e `CORP_INFOCAP_AUTOFLEET_*`, base
`api.corpnuvem.com`), e há documentação Postman que o Founder tem.
❓ A busca por documento **nunca foi exercitada pela cobrança**.

---

# 4. AS SETE DECISÕES QUE SÓ O FOUNDER TOMA

Não são regras escondidas: são decisões que ninguém tomou. O que a Saionara
(suporte da corretora) respondeu quando perguntada como faz hoje:

> *"Eu envio o boleto e fico acompanhando se pagou. Se não pagou eu reenvio e
> sempre lembro a data limite, para não cancelar por falta de pagamento."*

Isso já entrega três regras: **reenvia** · **acompanha** · **sempre cita a data
limite**. Faltam:

| # | A decisão | Por que o robô não pode inventar |
|---|---|---|
| 1 | De quantos em quantos dias reenvia | a Saionara faz por sensibilidade; o robô precisa de número |
| 2 | Quantas vezes, antes de virar tarefa humana | sem teto, vira perseguição |
| 3 | Horário e dias em que pode falar | comercial? sábado? |
| 4 | Se o segurado responder, o robô para? | quase certamente sim — mas tem de estar escrito |
| 5 | Quem **nunca** recebe automático | cliente que só a atendente fala |
| 6 | Teto por dia por corretora | para não parecer disparo em massa |
| 7 | O texto, e o que muda quando o cancelamento está perto | é o que a Saionara faz à mão hoje |

> 🔴 **Escrever isto ANTES do primeiro envio.** Mensagem enviada não volta, e
> corrigir depois é corrigir na frente do cliente da corretora.

---

# 5. A FREQUÊNCIA — e por que a janela é de 90 dias

O Founder levantou a pergunta certa: **quantas vezes por semana se entra no
portal, e com que janela?**

📊 O ponto que não é óbvio: a busca filtra por **data de vencimento**, não por
"novidades". Uma parcela vencida há 60 dias e ainda não paga **mantém o
vencimento antigo** — ela some de uma janela de 30 dias mesmo estando em aberto.

Então a janela não é sobre frequência de varredura: é sobre **quanto tempo uma
dívida vive antes de a seguradora cancelar a apólice**.

**Recomendação, para o Founder decidir:**

- **Janela: 90 dias**, fixa. Cobre a vida da dívida até o cancelamento.
- **Frequência: 2× por semana** (ex.: terça e sexta). Diária é agressiva para o
  segurado e para o portal; semanal deixa a dívida envelhecer 7 dias.
- **Configurável por corretora** — volume grande pode querer 3×, pequeno 1×.

📊 Curiosidade útil: a tela da Zurich oferece atalhos de **"3 dias"** e
**"7 dias"** — a própria seguradora pensa em janelas curtas para o que está
por vencer.

⚠️ **Limites medidos por portal:** Zurich aceita até ~90 dias e **404 acima
disso** (e pedir demais derruba a sessão); HDI trabalha em blocos de 30;
MAPFRE aceita 730 numa chamada; Yelum ~90.

---

# 6. A 3ª ETAPA — o acompanhamento (P-158)

Hoje **nada no sistema sabe** *"já falei com esta pessoa, sobre esta parcela,
há N dias, pela Kª vez"*.

📊 O `billing_sent_log` existe — mas para **retomada** (não repetir no mesmo
dia), não para **cadência** (decidir o 2º e o 3º toque).

O que a 3ª etapa precisa criar:

1. memória por **(segurado, parcela)**, não por rodada;
2. a decisão "reenviar ou escalar", com as regras do §4;
3. o texto do reenvio, que muda conforme o cancelamento se aproxima;
4. o desfecho quando o segurado paga — parar, e saber que parou.

> Não começar isto antes de a 2ª etapa mandar a primeira mensagem. Sem um envio
> real, o acompanhamento é desenho no papel.

---

# 7. O QUE MAIS ESTÁ ESPERANDO

| # | O que | De quem |
|---|---|:--:|
| **P-116** | `human_support_destinations` só tem a AMANDUS. **Resulta e AutoFleet têm zero** — item retido é montado e descartado | 🧑 Founder |
| **P-117** | **Zero rotinas de cobrança ativas.** A única existente é da Resulta, desligada e só com Allianz | 🧑 decide horário · 🤖 liga |
| **P-118** | O envio real nunca aconteceu, em nenhuma seguradora | 🧑 autoriza |
| **P-148** | Credencial da **Resulta na MAPFRE** é inválida (a da Zurich funciona) | 🧑 Saionara |
| **P-152** | 21 números de pendência duplicados no `PENDENCIAS.md` | 🤖 sessão própria |
| **P-155** | Parsers da Yelum e da MAPFRE zeram em `"1,287,99"` — latente | 🤖 |
| — | **Rotação de chaves** antes de haver cliente real | 🧑 |

---

# 8. O MÉTODO — o que a 1ª etapa ensinou, e custou caro

Escrito por quem errou, para quem vem depois.

1. **O fallback documentado existe para ser usado.** A SPEC-033 diz "cadeia
   direta, e navegação visual como fallback". Na Zurich eu passei horas variando
   cabeçalho e timestamp para reproduzir uma URL, quando o caminho previsto era
   chamar a função da própria página. 📊 Ela funcionou na primeira tentativa.

2. **Verifique a coisa forte, não a fácil.** Um campo de data guardou
   `40/82/0261` e meu guarda perguntava se estava *preenchido*. Estava. A busca
   saiu errada e a tela voltou vazia **sem erro nenhum**.

3. **Meça antes de mandar o Founder agir.** Eu disse três vezes "falta o
   deploy" sem nunca ter enfileirado um job. O deploy estava certo desde o
   começo — um job na fila responde isso em 30 segundos.

4. **A linha de controle no FIM, não só no começo.** Na Zurich, repetir a busca
   que funcionava, depois de um pedido largo, revelou que o pedido tinha
   derrubado a sessão. Sem isso eu teria concluído a coisa errada.

5. **O portal instável é um fato, não um enigma.** Zero linhas numa busca que
   funcionou minutos antes é o portal, e a resposta é clicar de novo — não
   investigar por horas.

---

*Autoridade: CLAUDE.md · SPEC-070 · SPEC-033 (método) · SPEC-063 Bloco C
(governador de vazão) · SPEC-023/023A/023B (cobrança).*
