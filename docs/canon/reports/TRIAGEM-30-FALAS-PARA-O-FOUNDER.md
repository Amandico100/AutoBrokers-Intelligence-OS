# Triagem — 30 falas para a auditoria do Founder

> SPEC-083 · gerado em 21/08/2026 · decisão **Q2 (b)**: a triagem é feita por
> um juiz separado, e o Founder audita por amostra.

> 🔴 **SEMENTE REGISTRADA:** `spec083-triagem-21082026`
> A amostra é reprodutível: mesma semente, mesmas 30 falas.

> 📊 A fila (pool): **2189 telas** da `zona='URA'` vistas em ≤3 sessões,
> em 10 seguradoras. Estas 30 são um sorteio dela.

## A REGRA DA AUDITORIA

```
Para cada linha, responda:  URA  (robô da seguradora)  ou  GENTE  (humano)

🔴 Se você discordar de MAIS DE 3 das 30 (10%), a triagem inteira é refeita.
```

⚠️ **O que já se sabe, e limita o que esta amostra prova:** 📊 o pré-filtro que
monta a fila tem **54,9% de sensibilidade** — quase metade da fala humana
**não** entra nela. Ler a fila inteira não prova ausência de gente. Quem pega
o resto é o JUIZ 1 por rota, em segunda instância — e ele já pegou: a sessão
`44ff2017` entrou no corpus como URA e é conversa humana inteira.

---

| # | seguradora | sessão | a fala (texto real, mascarado) | URA? | GENTE? |
|---:|---|---|---|:--:|:--:|
| 1 | porto | `59dfcc8f` | Você quer atendimento para o veículo Byd, ano 2026, placa S####82? Botão 1: Sim Botão 2: Não Botão 3: Voltar | ☐ | ☐ |
| 2 | porto | `0c1e8e3e` | https://porto.vc/reparovidros | ☐ | ☐ |
| 3 | allianz | `448c6aae` | Certo! O serviço de *Conserto para eletrodoméstico (Ar condicionado)* deverá ser agendado *1 -* Continuar *2 -* Voltar | ☐ | ☐ |
| 4 | bradesco | `a10d095d` | Encontrei! Placa: *PML4937* Modelo: *RANGE R SPORT HSE DYNAMIC 4 4 SDV8 DIES* Podemos seguir o atendimento para este v | ☐ | ☐ |
| 5 | azul | `6c5280df` | Juliana, além do guincho, você precisa também solicitar um táxi para ir embora do local? *1* - Sim *2* - Não | ☐ | ☐ |
| 6 | porto | `c470d13d` | Certo. O endereço é o mesmo de destino do guincho? Botão 1: Sim Botão 2: Não Botão 3: Voltar | ☐ | ☐ |
| 7 | porto | `12203ed9` | Certo. Devido ao horário da solicitação, a *oficina pode estar fechada*. Nesse caso, dependendo das *condições do auto | ☐ | ☐ |
| 8 | azul | `14398ee8` | Localizei o endereço R. Ver. Carlos Acelino Pereira, null, Real Parque, São José - SC | ☐ | ☐ |
| 9 | yelum | `bb573c0a` | Para esse CPF informado localizamos o seguinte endereço: *Rua:* Do# Joaq### *Numero:* 827 *Bairro:* Cen### *Cidade:* F | ☐ | ☐ |
| 10 | azul | `d70ced75` | Qual período você prefere? *1* - Tarde *2* - Noite *3* - Voltar | ☐ | ☐ |
| 11 | allianz | `b8df5a82` | O que aconteceu com a chave? *1 -* Está presa dentro do veículo *2 -* Está presa ou quebrada na ignição ou em uma port | ☐ | ☐ |
| 12 | allianz | `267eb82f` | Atendimento cancelado com sucesso! O que deseja fazer agora? *1 -* Abrir novo atendimento *2 -* Sair | ☐ | ☐ |
| 13 | porto | `d0d64bfc` | Você quer atendimento para o veículo Volkswagen, ano 2023, placa R####64? Botão 1: Sim Botão 2: Não Botão 3: Voltar | ☐ | ☐ |
| 14 | porto | `5bcf0792` | Os horários mais próximos que eu tenho aqui são: Entre 12h00 e 14h00 Entre 14h00 e 16h00 Entre 16h00 e 18h00 Outros ho | ☐ | ☐ |
| 15 | yelum | `935c4076` | Maria Regina - Autofleet Seguros, o serviço de *SOCORRO MECÂNICO* chegará para te atender entre *09:18 e 09:28*. Você  | ☐ | ☐ |
| 16 | porto | `193c5ad6` | Antes de continuar, só um aviso: estamos com um alto volume de atendimento no momento. Peço a sua paciência, pois o te | ☐ | ☐ |
| 17 | bradesco | `72af1ae1` | Olá! Sou a Assistente Virtual da Bradesco Seguros e vou continuar seu atendimento aqui no WhatsApp. Vi que você já ide | ☐ | ☐ |
| 18 | porto | `5bcf0792` | Pronto! Tudo certo com o seu agendamento 🙂 O prestador deve chegar ao seu endereço no dia 30/01/2026, entre 08h00 e 10 | ☐ | ☐ |
| 19 | azul | `d70ced75` | Por favor, aguarde enquanto solicito o seu serviço. | ☐ | ☐ |
| 20 | yelum | `db2270c8` | O comunicante é: Botão 1: SEGURADO Botão 2: CORRETOR Botão 3: TERCEIRO | ☐ | ☐ |
| 21 | hdi | `78b2de6f` | Estamos prontos para seguir com sua solicitação de Assistência 24 Horas para o Veículo de Placa *MLD8218*, modelo *1.6 | ☐ | ☐ |
| 22 | yelum | `f06c34b8` | Olá! 👋 Somos da Yelum Seguradora e informamos que concluímos a análise do sinistro *22499108* como indenização integra | ☐ | ☐ |
| 23 | yelum | `19d73270` | Você se encontra em uma das situações de risco abaixo? Via com pouca iluminação Via com pouco movimento Ponto de alaga | ☐ | ☐ |
| 24 | porto | `01a18587` | Você deseja atendimento para algum desses produtos? Seguro Celular Seguro Aluguel (Fiança) Previdência Seguro Empresa  | ☐ | ☐ |
| 25 | allianz | `ed379849` | *RESUMO* *Protocolo N.°:* 52158865 *Serviço:* *ENCANADOR*; *Endereço:* R. ### #AIME C#####, 190 - ####IANOP#### - SC * | ☐ | ☐ |
| 26 | yelum | `01bf91c2` | Maria, identifiquei que você já tentou abrir um atendimento e preencheu as informações: | ☐ | ☐ |
| 27 | allianz | `d2e3174b` | Sim, será apenas esse serviço Instalação de Luminárias (até 2 unidades); | ☐ | ☐ |
| 28 | porto | `18e81a66` | Oi, sou assistente virtual da Porto 👋 Felipe, estou aqui pra falar sobre o sinistro de número 553202512105901 para o v | ☐ | ☐ |
| 29 | hdi | `886066e5` | *Resumo da solicitação* *Placa:* RYM5J48 *Assistência:* 8837507 *Telefone:* 48991759360 *Serviço:* Troca de Pneus *Loc | ☐ | ☐ |
| 30 | mapfre | `9fae42e2` | Certo! E você quer falar sobre *qual seguro*? Auto Pagamento, 2ª via de apólice e outros serviços Patrimonial Pagament | ☐ | ☐ |

---

## E as três perguntas que só você responde

1. 🔴 **A sua régua da apresentação mede ~95%, não 99,9%.** 📊 6 de 118 sessões
   com fala humana **não** têm apresentação — e essas 6 também **não** têm
   marca de transferência. As duas condições falham juntas, na mesma
   população. Isso bate com o que você conhece da operação?

2. 🔴 **A tokio tem um terceiro ramo: CONDOMÍNIO** (📊 2 sessões). Não há
   playbook para ele. Vira ramo do produto, ou fica fora?

3. 🔴 **A URA nomeia serviços que o código não tem:** `consulta veterinária`,
   `pet assistance`, `limpeza de caixa d'água`, `dedetização`, `telhado`,
   `ar condicionado`, `chuveiro` — e **socorro mecânico em 38 sessões**, que
   o produto RECUSA. Quais viram subserviço?
