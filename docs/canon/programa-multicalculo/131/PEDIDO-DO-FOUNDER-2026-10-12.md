# O pedido do Founder para a SPEC-131 (12/10/2026) — organizado pelo gerente

> Fonte: a mensagem do Founder de 12/10 + o PDF "RASCUNHO AUXILIAR DE RENOVAÇÃO" (notas de 23/09, **parcialmente vencidas**:
> muita coisa já foi feita depois) + 6 prints (no rascunho da sessão: `images/1.png` Meu perfil · `2.png` Personalização → Serviços ·
> `3.png` Relatórios · `4.png` lista de cotações do Agger · `5.png` inspiração de tabela/mobile · `6.png` a ficha do caso do Atendimento)
> + a pasta `docs/intake/TELAS AUXILIARES/` (inspirações: galeria, página do aplicativo, modal, telas atuais — fora do git).
> Tudo abaixo é a VOZ DO FOUNDER resumida; "regra" só onde ele diz que é. O resto é inspiração para o executor decidir com nota.

## A. A visão
- O AutoBrokers é o **celular**; a página de Auxiliares é a **loja (Play Store / App Store)**; cada auxiliar é um **aplicativo**
  com função específica, que a corretora instala/liga e desliga. Frente: facílima, bonita, "efeito wow", confiança (Netflix/Spotify/
  plugins do ChatGPT como inspiração). Trás: robusto, sincronizado, sem erro. Evitar o medo de "agente de IA": gerar a SENSAÇÃO de app.
- Pergunta: trocar o nome "Auxiliar" por "Aplicativo" (ou outro)? Quer nota 0–100 para cada nome.
- Três telas precisam impressionar: **galeria** (cards com imagem/logo, nota 5 estrelas — ele propõe 30 avaliações fictícias iniciais;
  ícones hoje "infantis", quer premium enterprise) · **página do aplicativo** (hoje nota 50: poluída, subtítulos apagados, sem banner,
  sem logo; quer abas: principal · dúvidas frequentes · sugestões; um bloco "como instalar / o que você precisa fazer" passo a passo;
  "o que a corretora ganha"; conexões com ícone e linguagem humana; tirar "de onde ele tira a informação") · **modal de configuração**
  (hoje confuso, sem hierarquia, informação que não se edita repetida; quer limpo, rápido, tooltips, esconder o que já está decidido).
- **Serviços (Personalização → Serviços) foi um ERRO de lugar**: tudo o que está lá (Cotação · Renovação · Quem Cobra Menos: só
  calcular / calcular e entregar / calcular, entregar e negociar; exceções por ramo; seguradoras preferidas; reajuste) tem de morar
  DENTRO de cada aplicativo (Renovação, Cotação, Quem Cobra Menos). A aba Serviços sai.
- **Nova aba padrão em todo aplicativo: "o trabalho feito"** (Renovações / Cobranças / …): lista com filtros (dia, ramo, seguradora,
  comercial), status, atalhos (ver a apresentação, enviar ao cliente pelo WhatsApp com a mensagem pronta, PDF, abrir o cálculo no
  Agger na página certa, talvez a seguradora), detalhe ao clicar (dados do cliente, contato, valores simplificados, indicadores),
  e opção **Kanban** (o agente move os cards por estágio). Referência interna: `dashboard/atendimentos/fila` (Kanban) e
  `dashboard/atendimentos/ficha/<id>` (o caso). Inspiração externa: a lista do Agger (print 4) e o print 5. Responsivo: notebook E
  celular, decidir e enviar pelo celular. Hoje as nossas listas estão "muito aquém".
- Fazer o visual agora ou numa SPEC só de layout depois? **O executor decide** (o pedido antigo de layout pode já estar numa SPEC
  futura; a EXTRA-001.9 "o painel diz de quem é" arruma rotas de Personalização). Não reinventar a roda.

## B. O aplicativo de Renovação — o ciclo
Hoje (humano): todo dia vê no sistema de gestão quem vence → cota no Agger → monta a apresentação → envia → negocia → fecha →
efetiva na seguradora → registra na InfoCap. **Objetivo final: o ciclo inteiro** (cálculo → negociação → "Emissão e registro").
Agora: decidir o que entra nesta SPEC e o que fica para as próximas, deixando tudo preparado.
1. **Quando calcular:** padrão **10 dias antes** do vencimento (Resulta/AutoFleet fazem mais ou menos isso), **configurável por corretora**.
2. **A promessa "às 7h":** todo dia, antes das 7h, o comercial encontra TODAS as renovações do dia calculadas no Agger DELE (pode
   ficar pronto às 3h, 4h, 5h). O executor define o horário de início (2h? 3h?) pelo tempo real de cálculo e pelo volume
   (📊 99 renovações/30 dias na Resulta, 217 na AutoFleet — BLOCO 0 da 131-0). Avaliar **lotes / paralelismo** (de 5 em 5?) e o risco
   de sobrecarga; talvez calcular **por ramo** (auto primeiro, depois residencial…) para ficar organizado no Agger.
3. **Nunca esquecer uma renovação** (30 calculadas e 2 esquecidas = perda de confiança). Precisa de garantia (um "juiz"/conferência
   de completude?). Cliente sem comercial ou sem Agger: não pode ficar sem cotação — decidir a distribuição (Agger da corretora?).
4. **De quem é cada cliente:** o aplicativo entende os clientes de cada comercial no CORP (o dono — 131-0) e cota no Agger de cada um.
5. **Agger conectado:** de madrugada o robô entra mesmo se o Agger do comercial aparecer conectado (sessão esquecida); se a pessoa
   entrar de novo logo depois, o robô espera e tenta de novo. Cotação pedida no chat: usa o Agger do usuário (entra mesmo conectado);
   admin sem Agger próprio → o da corretora. QCM: sempre o da corretora (já decidido).
6. **Ramos que ainda não sabemos cotar** (RC, risco de engenharia, embarcação, moto, vida…): o que acontece hoje? Qual a solução ideal
   e quando? (o Agger cota muitos ramos; o nosso motor faz AUTO, COND, RESI, EMPR).
7. **No Agger fica o CÁLCULO** (o comercial ajusta lá se quiser; no futuro o agente ajusta negociando). **No AutoBrokers fica a
   APRESENTAÇÃO** e o painel das renovações.
8. **A página de apresentação de RENOVAÇÃO** (nova, definitiva, triplo A, alta conversão): partir do artefato
   `https://claude.ai/artifact/K3pGqdMQ9dvThA7r6AZSZC` (a página feita para o Quem Cobra Menos v1) e da página da 130-A, mas a COPY
   é para quem JÁ É CLIENTE continuar: relação (ex.: "4 anos juntos", lido do sistema de gestão), carinho, cuidado, sugestão,
   contatos, dúvidas, a corretora, comparação lado a lado. Tirar o que é irrelevante na renovação. Identidade da corretora (logo,
   cores, site — Personalização → Identidade). Ele pede **3 cálculos**: o **recomendado** (base = o do ano anterior: coberturas iguais
   ou melhores, preço parecido, se possível comissão melhor), o de **franquia reduzida**, e um **terceiro do que os clientes sempre
   pedem** (ajustes que as comerciais da corretora já descreveram — procurar onde isso foi anotado). NUNCA o "mínimo pelado" do QCM.
   No PDF ele pediu também 3 templates (elegante · luxuoso/tecnológico · wow com animação) para a corretora escolher — avaliar.
   Modelo de 1, 2 ou 3 cotações com uma recomendada — avaliar. Enviar link ou PDF.
9. **Enviar ao cliente:** conferir e clicar "enviar" (mensagem pronta) OU o agente envia sozinho (configurável, como na Cobrança).
   Para isso: **WhatsApp do USUÁRIO pareado** (o celular do comercial), separado do WhatsApp de atendimento da corretora — serve a
   renovação, cotação, cobrança. (Já existe a 131-0 parte B1 "o WhatsApp por pessoa" na fila.)
10. **Negociação e fechamento:** o agente que envia precisa saber negociar, recalcular, fechar; depois "Emissão e registro"
    (efetivar na seguradora + registrar na InfoCap). Decidir quando e o que precisa (exemplos de conversa?).

## C. A estrutura do usuário × corretora (está "confusa e espalhada")
- CORRETORA: sistema de gestão (InfoCap/Quiver), Agger da corretora (QCM e reserva), WhatsApp de atendimento, memórias, conexões com
  seguradoras, e-mail da corretora → **Personalização**.
- USUÁRIO: o Agger dele, o WhatsApp dele (pareado), o e-mail dele, (futuro: falar com o chat pelo WhatsApp) → proposta do Founder:
  centralizar em **Meu perfil** (`/dashboard/configuracoes`, hoje subaproveitado — print 1). Atalhos nos dois lugares só se bem pensado.
- O aplicativo USA as conexões já feitas; dentro dele só se escolhe o que fazer (ex.: "usar o WhatsApp do usuário ou o da corretora",
  "o Agger do usuário ou o da corretora" — com padrão).
- **Agger por usuário:** cada pessoa cadastra só o DELA (no perfil), não os de todos ("Aggers da equipe" hoje lista todos — rever).
  **Substituto de férias**: em vez de novo login e senha, escolher OUTRA PESSOA da corretora para assumir temporariamente.

## D. O que o Founder pede da execução
Qualidade máxima (> 90/100), Opus 5.5 em tudo, quantos subagentes limpos precisar; decidir pela maior nota; nota 0–100 para cada
dúvida; ajustar a SPEC ao que for melhor; deixar claro o que fica para depois e por quê.
