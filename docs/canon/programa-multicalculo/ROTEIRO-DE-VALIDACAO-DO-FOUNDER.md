# Roteiro de validação do Founder — 130-A.1 · 133-A · 133-A.1 · 129-C

> 11/10/2026 · uma tarefa por vez, nesta ordem. Cada passo diz o que fazer, o que ESPERAR e o que fazer se não bater.
> Os números T-xxx são os de `docs/canon/TAREFAS-DO-FOUNDER.md`.

## Bloco 1 — deixar o sistema pronto (uns 20 minutos)
1. **Implantar de novo** (a 129-C mudou o robô, o app e a tela do Agger): EasyPanel → Implantar `smith-api` → `smith-worker` →
   `portal-worker` → `smith-web`. **Esperar:** `https://autobrokers-intelligence-os-portal-worker.golhpm.easypanel.host/health` com
   `build_time` de 11/10/2026 ou depois. **Se não:** Implantar o `portal-worker` de novo.
2. **A tela do Agger** (painel → Personalização → Conectores → "Agger da corretora", em cada corretora). **Esperar:** "Ligado o tempo
   todo" e nenhum campo de horário. **Se aparecer horário:** o `smith-web` não foi implantado.
3. **Segurança (T-137):** painel → Personalização → Equipe → em cada pessoa, "Nova senha" → salvar → copiar a senha que aparece e entregar.
   São 4 pessoas com a senha padrão antiga.
4. **O Agger da Resulta (T-136 + P-129C-04)**, com um login de administrador da Resulta no Agger: HDI (credencial inválida → corrigir e
   Validar) · Mitsui (cadastrar, se houver código) · Tokio (preencher o login do serviço web) · **a data de licença era 13/10** → conferir
   "Meu plano" · Porto e Mapfre: ver se pedem credencial própria para Condomínio/Residencial/Empresarial (no cálculo real recusaram por
   credencial) · o `cotador@` com o perfil restrito do robô da AutoFleet.

## Bloco 2 — o número do Quem Cobra Menos (o chip novo)
5. Instalar o **WhatsApp Business** no chip novo, com o nome "Quem Cobra Menos".
6. **Ler o QR (T-133)** com o número NOVO: portal admin → Conexões → Canais: Quem Cobra Menos (WhatsApp) → Conectar → no celular do chip
   novo: WhatsApp → Aparelhos conectados → Conectar aparelho. **Esperar:** "conectado".
7. **Convidar você (T-134)** — Console do `smith-api`:
   `python -m app.services.canal.comando_convidados --adicionar 5547996274743 --apelido "Amandus"` e
   `python -m app.services.canal.comando_convidados --listar`. **Esperar:** o seu número aparece mascarado.

## Bloco 3 — o seu teste (uns 15 minutos)
8. Do seu celular, mande **"oi"** para o número novo. **Esperar:** a apresentação e o consentimento.
9. Responda **"sim"** e as perguntas (placa, CEP, aplicativo, km, condutor jovem, CPF, nome, nascimento, anos de carteira, quanto paga hoje).
   **Esperar:** uma pergunta por vez; com um nome comum, a pergunta "homem ou mulher?" NÃO aparece.
10. **Esperar o resultado** (alguns minutos). **Esperar:** "Prontinho, <nome>! Descobrimos Quem Cobra Menos…", "Fiz <100 + cotações>
    Cotações…", "Você deve economizar até R$ …" (contra o valor que você disse), "Quem cobra menos? Corretora … · <N>x de *R$ …*", os
    cartões, o melhor preço por seguradora, quem é a corretora (com SUSEP e anos), o link e a pergunta final.
11. **Abrir o link.** **Esperar:** a marca do Quem Cobra Menos; as opções LADO A LADO (arraste para o lado); em cada cartão a menor
    parcela no topo, depois o à vista, depois o maior sem juros; o logo da corretora vencedora; o bloco "Nível 5".
12. **Tocar em "Quero fechar".** **Esperar:** volta para a conversa com o texto pronto; ao mandar, a resposta de passagem e um card
    "Cliente do canal quer fechar" no Inbox do portal admin.
13. **Não responder por 15 minutos** num segundo teste. **Esperar:** 1 lembrete; no dia seguinte, no horário comercial, o 2º; nunca um 3º.
14. **Mandar "parar".** **Esperar:** uma frase de confirmação e nada mais.
**Se algo não bater:** um print de cada tela e a hora, aqui no chat.

## Bloco 4 — os 4 testadores (depois do seu teste dar certo)
15. Cadastrar cada um (o comando do passo 7 com o número e o apelido).
16. Mandar a eles: *"Oi! Estou testando um serviço que descobre quem cobra menos no seguro do seu carro. Manda 'oi' para <número novo> e
    responde as perguntas. Precisa da placa, do CEP de onde o carro dorme e do seu CPF. É cotação de verdade, mas você não é obrigado a
    fechar. Depois me conta: chegou até o resultado? Quanto tempo levou? Onde travou? Mostraria para um amigo?"*
17. Juntar as respostas e os prints e mandar aqui.

## Bloco 5 — os outros ramos (129-C) — nada para você testar no WhatsApp ainda
A 129-C ensinou o motor a cotar Condomínio, Residencial e Empresarial (📊 1 cálculo real de cada fechou no Agger da Resulta em 11/10). A
tela/proposta desses ramos é a 130-C. O que você valida agora: os passos 1 e 4 (o Agger da Resulta com as credenciais de RE certas).
