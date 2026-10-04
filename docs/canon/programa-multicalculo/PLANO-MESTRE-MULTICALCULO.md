# Plano mestre — Programa Multicálculo

## Renovação, cotação e Quem Cobra Menos, em linha reta

**Versão 2.4 · 04/10/2026 · DEFINITIVA para a execução · desenvolvimento declarado pelo Amandus em 04/10 · nada aqui foi implementado ainda.**

> **Para o Claude Code:** este é o plano do programa. Ele vale abaixo do CLAUDE.md e do protocolo v13. A execução é contínua (§0.1): siga SPEC atrás de SPEC e pare só nos portões e nas paradas legítimas.

O que mudou da v2.3 para a v2.4 (pedidos do Amandus, 04/10):
- **Mesma pasta, sem worktree.** A 126/127 terminou no código; só faltam os testes de celular do Amandus.
- **Execução contínua (D-MC-49).**
  - O Claude Code segue o plano sozinho, sem voltar à concepção a cada SPEC.
  - Encadeia 2–3 SPECs por chat e entrega o texto do chat seguinte.
  - O plano fica gravado no repositório.
- **O conhecimento compartilhado continua global (D-MC-39).**
  - O conserto da P-E0018-14 só garante que ele saia anônimo.
  - O texto da v2.3 dizia o contrário por erro de resumo.
- **Nome da marca: Quem Cobra Menos (D-MC-22).**
- **Narração ao vivo honesta durante o cálculo (D-MC-50, §6.6).**
- **As chaves da 129-A vêm de duas variáveis do EasyPanel,** não do log.

O que mudou da v2.2 para a v2.3:
- **Revisão do Claude Code (04/10) incorporada:**
  - os 7 pontos de abertura;
  - as 12 correções;
  - os 6 itens que tinham ficado de fora.
- **Os dois consertos do passo 0.5 seguem o rito CRÍTICO.**
- **A 129-A abre com o inventário dos trabalhos presos.** Três pendências saem dela.
- **Respostas do Amandus (04/10):**
  - o ajuste mais pedido é o preço;
  - a proposta passa a ter 2 opções por padrão (completa e recomendada; econômica), com nota de 0 a 100 e motivos;
  - entra um portão de preço antes da 130-A e da 133-B;
  - o desenvolvimento está declarado, e a nova fila confirmada.
- **Entra o checklist até a produção (§0.1).**
- **O nome está em revisão (D-MC-22).** Os candidatos estão na concepção viva.

O que mudou da v2.1 para a v2.2:
- **Ordem:**
  - a 129 se divide em 129-A (a espera durável) e 129-B (o motor);
  - a 129-A vem antes da prova do Agger (128);
  - entram o passo 0.5 (decisões registradas e dois consertos curtos) e a prova de instalação do Quem Cobra Menos (133-A), logo no começo.
- **Fatos corrigidos:**
  - a sessão do Agger é por usuário (login), não por conta;
  - o preço depende da corretora;
  - o token do motor dura 3 h;
  - a primeira oferta chega em 12,6–40,5 s;
  - a renovação nasce da InfoCap;
  - o link público de relatório está quebrado (conferido no ar).
- **Decisões:**
  - as decisões viram D-MC-*, porque D8–D22 já existem no canon com outro sentido;
  - entram as D-MC-23 a D-MC-38.
- **Instalação:** revista com as fontes oficiais de 03/10.
  - O ChatGPT pessoal ficou mais incerto.
  - O diretório do Claude ficou mais forte: vale no plano Free e no celular.
- **Páginas do cliente:** viram um padrão próprio ("uau"), com modelo visual aprovado antes da 130.

Legenda: **FATO** (verificado, com fonte) · **AMANDUS** (informação ou decisão dele) · **HIPÓTESE** · **RECOMENDAÇÃO**. Números: 📊 medido · 💭 ilustrativo ou estimado.

"Quem Cobra Menos" é o nome da marca de consumo, escolhido pelo Amandus em 04/10. Antes, era "Seguros Baratos", e antes ainda, "GPT SEGUROS".

---

## 0. Em uma página

- **Um computador, uma fila, SPECs em linha reta.**
- **O programa:**
  1. a espera durável;
  2. a prova do Agger;
  3. a prova de instalação;
  4. o motor;
  5. a comparação e a proposta;
  6. a renovação;
  7. a cotação;
  8. o Quem Cobra Menos piloto;
  9. o canal público;
  10. o WhatsApp oficial;
  11. a proposta conversa;
  12. os lembretes;
  13. o Quem Cobra Menos público.
- **Quem escreve o quê:** as fichas estão aqui. O Claude Code escreve cada SPEC executável a partir da ficha, um revisor novo e cego a confere, e ela é executada em seguida (D-MC-49).
- **Nomes e números:**
  - 📊 os números 128–138 estão livres no repositório (git grep, 03/10);
  - as decisões usam o prefixo D-MC-;
  - no código, o cálculo não se chama "quote", porque esse nome já é do funil comercial.

| # | O quê | SPEC | Tamanho 💭 | Entra quando |
|---|---|---|---|---|
| 0 | Fechar a 126/127: os testes possíveis agora e os consertos | — | — | — |
| 0.5 | Registrar as decisões e a nova fila; consertar o link público `/r/` e a P-E0018-14 | consertos curtos, rito CRÍTICO | P | desenvolvimento declarado (04/10) ✔ |
| 1 | A espera durável (Work OS) | 129-A | M · 2 etapas | — |
| 2 | A prova do Agger: primeiro com as gravações, depois 2 sessões ao vivo | 128 | M · 2–3 etapas | autorização escrita da corretora para concluir cálculos; login livre no horário |
| 3 | A tomada do Quem Cobra Menos e a prova de instalação | 133-A | M · 2 etapas | 10–15 testadores leigos |
| 4 | O motor de multicálculo | 129-B | G · 5–6 etapas | 129-A pronta; 128 respondida |
| 5 | Comparação, proposta e registro (130-A) · leitor de apólice (130-B) | 130 | G · 4–5 etapas | modelo visual aprovado; crédito de API (T-04) |
| 6 | Auxiliar de Renovação, fase 1 | 131 | G · 4 etapas | InfoCap da Resulta de volta na Resulta (D-MC-27) |
| 7 | Auxiliar de Cotação, fase 1 | 132 | M · 3 etapas | — |
| 8 | Quem Cobra Menos piloto: cotação no chat | 133-B | G · 3–4 etapas | preço do canal acertado (D-MC-29) |
| ★ | Canal público | — | — | números da 133-A e da 133-B |
| 9 | WhatsApp oficial | 134 | G · 3–4 etapas + prazo da Meta | atendimento ligado; verificação na Meta |
| 10 | A proposta conversa (fase 2) | 135 | M · 2–3 etapas | atendimento ligado; fase 1 medida (D-MC-32) |
| 11 | Lembretes de vencimento | 136 | M · 2 etapas | opt-in em nome da corretora de registro |
| 12 | Quem Cobra Menos público | 137 | G (isca) a GG (login e conta) | decisão ★ |

Ajustes da ordem:
- **Os passos 2 e 3 podem trocar de lugar.** Vai primeiro o que ficar pronto antes: a autorização e o horário da 128, ou os testadores da 133-A.
- **Se a ★ escolher um diretório,** a 137 sobe para logo depois da 133-B.
- **Tamanho:** P/M/G/GG. Uma etapa é o que um agente faz numa sessão.
- **Portões de preço:** antes da 130-A e antes da 133-B, o Claude Code faz ao Amandus as perguntas de preço, com os números da 128 (D-MC-45).

### 0.1 O caminho até a produção — checklist

**Execução contínua (D-MC-49) — como o Claude Code anda:**
1. **Pasta.** A mesma pasta de sempre. Um chat mexe no código de cada vez.
2. **Para cada SPEC, sem esperar aprovação:**
   1. escreve a SPEC executável a partir da ficha (§4), no formato do protocolo v13;
   2. um revisor novo e cego compara a SPEC com a ficha e com o código, e o que ele achar é consertado;
   3. executa pelo protocolo v13 (juiz e red team), roda a bateria e empurra para a `main`;
   4. fecha com a resposta do CLAUDE.md §12.2: o que mudou, o passo a passo do Implantar e os testes do Amandus;
   5. segue para a próxima SPEC. Só espera o Implantar quando a próxima depender do que está no ar.
3. **Para e pede ao Amandus o que precisa, de forma objetiva, só em dois casos:**
   - uma parada legítima do CLAUDE.md §10;
   - um destes portões:
     - **128 ao vivo:** autorização escrita da corretora, 3–5 apólices autorizadas, login livre no horário;
     - **133-A:** o serviço e o domínio no EasyPanel, e os testadores;
     - **130-A e 133-B:** as perguntas de preço (D-MC-45), já prontas, com os números da 128;
     - **131:** a InfoCap da Resulta de volta na Resulta;
     - **134:** a verificação na Meta e o número novo;
     - **135:** o atendimento ligado;
     - **qualquer licença ou custo novo.**

   Enquanto um portão espera, avança no que não depende dele. Nunca inventa decisão comercial ou de preço.
4. **Contexto.** Encadeia 2–3 SPECs por chat. Passando de 60%:
   - termina a SPEC em curso;
   - atualiza o ESTADO-DAS-SPECS;
   - entrega ao Amandus o texto exato para abrir o próximo chat, na mesma pasta (modelo no §12).
5. **Falha da 126/127.** Se o Amandus relatar uma falha num teste da 126/127, conserta antes de seguir.

**☐ 0 · Fechar a 126/127** — código pronto; faltam os testes de celular do Amandus
- Se um teste falhar, o Amandus cola o erro no chat do programa, que conserta.

**☐ 0.5 · Registro e dois consertos** — chat novo, mesma pasta (prompt do §12)
- Grava este plano no repositório e registra no canon as decisões e a nova fila.
- Conserta o link de relatório `/r/`: o cliente volta a abrir sem login.
- Garante que o conhecimento compartilhado entre as corretoras saia sempre anônimo. Ele continua global (D-MC-39).
- **Amandus:** implanta os 4 serviços (o relatório traz o passo a passo).
- **Pronto quando:** um link `/r/` abre numa aba anônima.

**☐ 1 · 129-A · Espera durável** — mesmo chat
- O sistema espera os ~7 min do Agger sem perder nada, sobrevive a reinício e nunca roda duas vezes.
- Antes de tudo, faz o inventário dos trabalhos presos e aplica uma regra: volta o que pode rodar; o velho expira sem rodar.
- Tira o CPF em claro dos passos de trabalho.
- **Amandus:** informa no prompt duas variáveis do `smith-api` no EasyPanel; implanta; testa.
- **Pronto quando:** um trabalho de teste dorme 10 min e acorda; um reinício no meio não duplica.

**☐ 2 · 128 · Prova do Agger**
- Primeiro sem conta, com as gravações; depois 2 sessões ao vivo (teto de 25 cálculos).
- Mede:
  - o seguro novo e a renovação a partir da InfoCap;
  - quanto cada alavanca baixa o preço (comissão, assistência, carro reserva, vidros, franquia);
  - se 2 opções saem de um cálculo só;
  - o volume por dia e as cotas.
- **Amandus:** autorização escrita da corretora; 3–5 apólices autorizadas; o login livre nos horários.
- **Pronto quando:** tabela de capacidade com números e o contrato do cálculo.

**☐ 3 · 133-A · Prova de instalação**
- Um conector da marca, sem dado pessoal, com kit de instalação: link pessoal, 6 passos, vídeo e ajuda no WhatsApp.
- 10–15 leigos tentam instalar no próprio celular, no Claude e no ChatGPT.
- **Amandus:** cria o serviço e o domínio no EasyPanel; recruta os testadores.
- **Pronto quando:** se sabe quantos instalam sozinhos, em quanto tempo e onde travam.

**☐ 4 · 129-B · O motor**
- O AutoBrokers calcula e recalcula sozinho no Agger:
  - login de robô por corretora;
  - fila e freios;
  - resultado aos poucos;
  - senhas nunca expostas.
- Cobrança e vidros não travam durante um cálculo.
- **Amandus:** um login de robô em cada corretora (se faltar licença, decide a compra).
- **Pronto quando:** renovação e seguro novo de ponta a ponta pelo robô; duas corretoras isoladas.

**☐ 5 · 130-A · Comparação e proposta**
- Portão de preço antes de começar: com os números da 128, o Claude Code pergunta como montar as 2 opções e como usar a comissão.
- Proposta com 2 opções (completa e recomendada; econômica), nota de 0 a 100 e motivos, em página "uau" com PDF.
- Registro de oportunidades e consentimentos.
- **Amandus:** aprova o modelo visual; responde ao portão de preço.
- **Pronto quando:** um corretor aprova a proposta.

**☐ 6 · 130-B · Leitor de apólice**
- Lê PDF ou foto de qualquer seguradora e monta a ficha, com o modelo mais barato que acertar.
- **Amandus:** 20–30 apólices autorizadas; crédito de API.
- **Pronto quando:** o acerto está medido por campo.

**☐ 7 · 131 · Renovação (fase 1)** → 🚀 **MARCO 1: renovação no ar para as corretoras**
- As renovações da janela aparecem calculadas, comparadas e com proposta pronta; o corretor ajusta e envia.
- **Amandus:** devolve a InfoCap à Resulta; implanta; testa com uma semana real.
- **Pronto quando:** as renovações AUTO de uma semana real ficam prontas sem ninguém calcular.

**☐ 8 · 132 · Cotação no chat (fase 1)** → 🚀 **MARCO 2: cotação no ar**
- O corretor escreve "cota" ou "ajusta" no chat do AutoBrokers e recebe ali mesmo.
- **Pronto quando:** sai uma cotação nova a partir da apólice de outra corretora.

**☐ 9 · 133-B · Quem Cobra Menos em piloto** → 🚀 **MARCO 3: piloto do consumidor**
- Portão de preço do canal antes de começar: a comissão com Resulta e AutoFleet.
- Pessoas cotam conversando no Claude, com narração ao vivo durante o cálculo e proteções contra abuso e contra CPF de outra pessoa.
- **Amandus:** 10–30 pessoas reais; o acerto comercial.
- **Pronto quando:** 10–30 pessoas cotaram de ponta a ponta e nada vazou entre elas.

**☐ ★ · Escolha do canal público** — com os números da 133-A e da 133-B.

**☐ 10 · 134 · WhatsApp oficial**
- Número oficial, modelos aprovados, opt-in.
- **Amandus:** verificação na Meta (começar durante 129–131) e um número novo.
- **Pronto quando:** um modelo aprovado sai e a resposta volta à conversa.

**☐ 11 · 135 · A proposta conversa (fase 2)** → 🚀 **MARCO 4: negociação pelo WhatsApp**
- O agente leva a proposta no WhatsApp, ajusta e passa ao humano para fechar.
- **Entra quando:** o atendimento estiver ligado e a fase 1 medida.
- **Pronto quando:** um ciclo completo roda com cliente de teste.

**☐ 12 · 136 · Lembretes de vencimento**
- Recota e avisa quem consentiu, 30 e 15 dias antes.
- **Pronto quando:** a mensagem sai no dia certo, e quem recusou não recebe.

**☐ 13 · 137 · Quem Cobra Menos para o público** → 🚀 **MARCO 5: público**
- O canal escolhido na ★: diretório do Claude primeiro, ChatGPT no modo conta, ou WhatsApp.
- **Pronto quando:** qualquer pessoa usa pelo celular.

---

## 1. Onde estamos (04/10/2026)

### 1.1 Repositório e implantação — FATO
- **`main`:** em `e7f76df`. Entraram 6 commits em 04/10 às 00:22, da continuação da 126/127. Nenhum toca o `middleware.ts`, o Work OS ou a `conduct_playbooks` (📊 `git diff --name-only a87b2e7..e7f76df`, revisão de 04/10).
- **Produção atrás da `main`:** o no ar é o código de `a87b2e7`. O Implantar do passo 0.5 cobre a diferença.
- **Implantação conferida no ar** (📊 03/10, 18:23, só `GET /health`):
  - a digital do código do `portal-worker` e do `smith-api` era igual à de `a87b2e7`;
  - o `smith-web` não foi conferido;
  - o `portal-worker` roda com 📊 1 navegador (`concurrency: 1`).
- **`smith-worker`:** rodando (AMANDUS, 03/10).
- **Duas chaves de risco que o `/health` não mostra.** São duas variáveis de ambiente do `smith-api` no EasyPanel: `WORK_RUNS_ROUTINE_BRIDGE` (ponte_rotinas) e `WORK_WORKER_IN_PROCESS` (worker_na_api). Ficam ligadas com `1`, `true` ou `on`; ausentes, ficam desligadas. A linha de log `[STARTUP] SUBSISTEMAS` também as mostra (`main.py:398-410`).
  - com `ponte_rotinas=on`, a cobrança passa pelo Work OS;
  - com `worker_na_api=on`, o defeito do reinício silencioso está ativo em produção.
- **Testes e pendências:**
  - 📊 95 testes pendentes e 10 feitos, de T-01 a T-105 (04/10);
  - 📊 46 pendências P-126/P-127 abertas (48 registradas, 2 fechadas).
- **Verba das bancadas:** 📊 US$ 4,28 de 4,50 da OpenAI já usados na 126/127.

### 1.2 O Agger — FATO
Fontes: o parecer; 📊 as gravações (HAR) de 18/09, da conta da AutoFleet, medidas em 03/10; a prova de 23/09, feita na conta da Resulta.

**Sessão, token e tempos**
- **Sessão única por usuário (login).** A conta medida tinha 📊 8 licenças e 7 usuários ativos.
- **O token do motor de cálculo dura 📊 3 h.** Token é a "pulseira" de acesso que o site dá depois do login.
- **Tempos (n = 2):**
  - primeira oferta em 📊 12,6 s e 40,5 s (aos 5 s chegaram 2 erros);
  - 📊 16 de 17 seguradoras tinham respondido aos 42 s (R1), e 12 de 17 aos 137 s (R2);
  - todas as ofertas úteis entre 30 e 229 s;
  - conjunto fechado em 413–420 s.
  - Consequência: o motor entrega aos poucos, sem esperar os 7 minutos.

**Resultados e preço**
- **Um cálculo traz vários pacotes:** 📊 22 ofertas de 12 seguradoras (R1); 21 de 11 (R2).
- **O preço depende da corretora.** A comissão (📊 14–20 %) e o desconto (📊 0–15 %) vão por seguradora em cada cálculo, junto com as credenciais da corretora.
- **Toda oferta gera um número de cálculo na seguradora,** sob o código da corretora (📊 22/22 e 21/21).
- **Recalcular cria uma versão nova no mesmo negócio** (📊 3/3). Cada versão guarda o formulário, os cálculos e as credenciais.
- **O negócio pertence à conta da corretora,** não ao login: a busca lista os negócios da conta.
- **O Agger sabe se o CPF foi cotado recentemente** (`seguradoCotadoRecentemente`). Esse sinal nunca pode chegar à pessoa.
- **O campo `credenciaisValidas` mente:** veio `true` com senha errada.

**Dados sensíveis**
- **A partir de um CPF, o Agger devolve nome, nascimento, sexo e estado civil.**
- **A sessão do robô enxerga as senhas de todas as seguradoras da corretora:**
  - 📊 17 de 17 senhas são reenviadas no cálculo;
  - as senhas aparecem em 📊 28 de 28 consultas de acompanhamento.
- **A comissão vem no resultado** (📊 10/11 e 11/11).

**Renovação e fornecedor**
- **Os negócios capturados eram do ciclo atual.** O vínculo com o ano anterior veio vazio nas 2 amostras.
- **O Agger tem permissão de "envio de cotação" e de "fechamento de negócio"** (📊 `proposalStatus` em 19 seguradoras).
- **O mesmo fornecedor é dono da InfoCap.**
- **O login e o cálculo (`api-prod`) passam pelo Akamai** (📊 32 de 32 respostas).

### 1.3 O código — FATO
Os locais (arquivo:linha) vêm do parecer. ✔ marca o que eu conferi por conta própria em 03/10.

**A espera durável não existe**
- O estado "tentar de novo" é gravado (`runs.py:272`), mas o varredor só olha `running`, `planning` e `cancelling` (`runs.py:35`, `:199`) ✔.
- O worker conclui por cima de "esperando aprovação" (`smith_worker.py:385-393`).
- O botão "Reprocessar" não avisa o processador (`api/work_runs.py:204-222`).
- A espera do portal é de no máximo 150 s (`gateway.py`, `ESPERA_MAXIMA_S`) ✔, contra um cálculo de 413–420 s, e usa `time.sleep` em código assíncrono.
- No modo "worker dentro da API", o reinício mata o trabalho e grava que "será retomado", o que é falso (`smith_worker.py:289-292`).
- 📊 Nenhum commit nesses arquivos desde 06/09.
- **Cuidado ao consertar:**
  - os registros de acionamento também entram em "tentar de novo", gravados "sem fila" (`runs.py:393-415`);
  - o conciliador os conta como "em voo" e expira o órfão em 7 dias (`dispatch_router.py:388-390`);
  - o worker reprova trabalho sem executor (`smith_worker.py:366-369`).
  - Um re-enfileirador genérico ressuscitaria trabalhos velhos, que rodariam dias depois do pedido.

**O link público de relatório está quebrado**
- O caminho `/r/` não está entre as rotas públicas (`middleware.ts:92-108`) ✔.
- 📊 Em 03/10, um `GET` com token falso caiu em `/login` ✔.
- O próprio agente manda o corretor enviar esse link ao cliente, com o texto "Link para enviar (válido por 30 dias)" (`report_tool.py:296`) ✔.
- Logo, todo relatório enviado por link abriu a tela de login para o cliente.

**Peças que faltam ou têm defeito**
- **Servidor MCP:** nenhum exposto (📊 0 SDK).
- **Abuso:** o limitador confia no IP do `X-Forwarded-For` (`rate_limit.py:20-28`), que se pode forjar.
- **CPF:** o "hash de CPF" é sha256 sem sal, cortado em 12 caracteres (`journeys/__init__.py:352-369`), logo reversível. Ele é o apelido da lista de liberação do canário do portal (T-101). Não pode ser trocado; os limites da 133-B usam uma função nova, em HMAC.
- **PDF:** o Artifact Hub (no `smith-api`) só gera HTML.
  - O backend só tem PyMuPDF (`requirements.txt:56`).
  - O Chromium existe só na imagem do `portal-worker`.
- **Extrator:** o da 001.1 apaga o CPF e só tira trechos por regex (`policy_document_evidence_service.py:167`).
- **Leads:** `email` NOT NULL e `UNIQUE(company_id, email)`. Isso vem do `schema_completo.sql`, um retrato antigo; conferir no banco.
- **P-E0018-14:** a `conduct_playbooks` tem 1 escritor (`attendance_distiller.py:1178`) e 7 leitores.
- **Manifesto de migrations:** toda migration nova o atualiza (`MIGRATIONS-AUTHORITY.md:162`). Ele já está sem `20261002_10/_11` (P-126-24).
- **InfoCap:**
  - a fonte `/renovacoes` traz CPF/CNPJ em 📊 99,2 % das linhas (n = 3.536, 22/09), mas o código descarta (`fonte_infocap.py:184-200`);
  - a apólice traz placa, chassi e FIPE.
- **Auxiliares:** a "fábrica de auxiliares" só classifica pedidos (`factory.py:223`); o `bridge_auxiliar` grava "sucesso" sem trabalho feito.
- **Meta (WhatsApp oficial):**
  - recusada no registro de provedores (`registry.py:30-33`);
  - 📊 0 código de webhook ou de modelo;
  - a resposta do painel sai pela primeira integração ativa (`integration_service.py:318-376`).

**O que já existe e serve**
- O worker exige que a conta seja da corretora do pedido e falha fechado (`worker.py:1205-1214`) ✔.
- No código, "conta" já é um login (`portal_accounts.username`).
- Existe o tipo "empresa técnica" (`company_kind`/`is_technical`, migration `20260727_06`) ✔. Não existe "tenant da plataforma".

**Colisões de nome**
- D8, D12, D19 e outras já existem no canon com outro sentido ✔.
- `quotes` já é o funil comercial ✔.

### 1.4 As plataformas (FATO, 03/10; detalhes no §6)
**Claude**
- O conector personalizado vale em todos os planos (Free: 1).
- Ele é adicionado pela web ou pelo desktop; no celular, a instalação está em beta. Depois de adicionado, funciona no app.
- Os conectores do diretório valem para todos os usuários, inclusive no celular.

**ChatGPT**
- A página oficial, atualizada em 03/10, diz:
  - MCP completo, com ações de escrita, só em Business, Enterprise e Edu, e só na web;
  - Pro conecta MCP só para leitura.
- Em 01/10, a equipe da OpenAI disse que o "modo desenvolvedor" deixou de ser um modo separado. Os "usuários elegíveis" criam o app em chatgpt.com/plugins → Add → Create MCP App.
- Plugin hospedado por conta pessoal não se compartilha por link.

---

## 2. Decisões (D-MC-*)

| # | Decisão | Origem | Consequência · o que substitui |
|---|---|---|---|
| D-MC-08 | Um computador para tudo do AutoBrokers; o segundo só para VSL e marketing | Amandus (antiga D8) | Plano em linha reta |
| D-MC-09 | Agger é o multicálculo oficial; APIs alternativas pesquisadas em paralelo | Amandus | Porta do multicálculo: trocar = adaptador novo |
| D-MC-10 | CPF obrigatório no Agger; CPF falso fora de questão; a apólice é a melhor entrada | Amandus | §6.3 |
| D-MC-11 | Começar com 1 usuário robô, depois 2; mais quando a demanda pedir | Amandus (corrigida: "usuário", não "conta") | §5 |
| D-MC-12 | Escala: várias corretoras, vários usuários robô, vários multicálculos | Amandus | 129-B |
| D-MC-13 | Qualquer corretora cota qualquer ramo | Amandus | Contrato por ramo; v1 = auto |
| D-MC-14 | (Informação do Amandus, estimativa da equipe) 3 de cada 5 renovações enviadas pedem ajuste, quase sempre de preço; 1 em cada 10 que ajustam pede um segundo ajuste. As alavancas são comissão, assistência e coberturas | Amandus, 03–04/10 | Recalcular com ajuste é função de primeira classe; 💭 ≈ 1,66 cálculo por renovação; a 128 mede quanto cada alavanca baixa |
| D-MC-15 | Fases: P1 o humano envia; P2 o agente negocia no WhatsApp e passa para fechar; P3 o agente fecha na seguradora | Amandus | §9 |
| D-MC-16 | Todo cálculo fica registrado para mensagem futura | Amandus | Refinada pela D-MC-31 |
| D-MC-17 | Custo por cálculo o menor possível, sem erro | Amandus | §8 |
| D-MC-18 | Na busca, nenhuma corretora em destaque; no fim, a vencedora com credenciais e link | Amandus | §6.4 |
| D-MC-19 | Cobrança, parecer jurídico e copy ficam para depois | Amandus | — |
| D-MC-20 | Isca no site só se o Quem Cobra Menos travar | Amandus | 137 |
| D-MC-21 | A 001.9 não é prioridade | Amandus | Depois do programa |
| D-MC-22 | Nome da marca de consumo: **Quem Cobra Menos**. Headline e copy ficam para depois | Amandus, 04/10 | O Amandus registra marca e domínio. Nenhuma peça promete "o mais barato" sem prova (CDC, art. 37 e 38) |
| D-MC-23 | O agente usa o Agger com a autorização da corretora que tem o contrato (uso próprio da corretora). Sem pedido de anuência ao Agger agora; negociar no futuro, com clientes usando | Amandus, 03/10 | Substitui a D-E002-01. A 128 conclui cálculos com autorização escrita da corretora (a de 23/09 cobria só leitura). Risco aceito; mitigação no §13 |
| D-MC-24 | Usuário robô dedicado por corretora: um login só do robô, dentro do contrato da corretora; nunca o login de uma pessoa no motor | Claude, por delegação (nota 95 do parecer) | Confirma a D-E002-02. Na 128, o login de teste já cadastrado serve se ninguém o usar no horário. Antes de a 129-B ir a uso real, cada corretora tem o seu. Se faltar licença, o Claude Code avisa |
| D-MC-25 | No início, a AutoBrokers opera o canal Quem Cobra Menos e controla o registro do canal; cada corretora controla as próprias oportunidades. Parceiras iniciais: Resulta e AutoFleet | Amandus, 03/10 (provisória) | Muda o texto do consentimento (§6.4). A expansão se decide depois |
| D-MC-26 | O canal mora como catálogo global + adesão por corretora (o padrão `auxiliary_templates` → `tenant_auxiliaries`) + registro mínimo numa empresa técnica | Claude, por delegação (nota 86 do juiz) | §6.5. Um só link para a marca; o "não me contate" vale para todas as parceiras; a trava do worker continua |
| D-MC-27 | A conexão InfoCap da Resulta dentro da Amandus foi intencional (testes). O Amandus a devolve à Resulta quando a execução começar | Amandus, 03/10 | Condição de entrada da 131 |
| D-MC-28 | Transporte: interceptação (provada em 23/09) como padrão; chamadas de dentro da página só com autorização expressa do Amandus, se a 128 mostrar fragilidade | Recomendação (80 × 78) | 129-B |
| D-MC-29 | Preço no canal: termo por corretora, com comissão e desconto por seguradora; nunca fixo no código, nunca ao acaso | Recomendação (85); confirmar antes da 133-B | No piloto, acerto com Resulta e AutoFleet |
| D-MC-30 | Porta do piloto: convite pessoal revogável dentro do próprio link do conector, wa.me no pedido de contato, teto diário e interruptor | Recomendação (82) | Substitui a D-E007-03 no piloto; o público se decide na ★ |
| D-MC-31 | Todo cálculo é registrado; contato futuro só com consentimento; sem consentimento, os dados pessoais são anonimizados depois de N dias (💭 90) | Recomendação (85) | Refina a D-MC-16 |
| D-MC-32 | A 135 liga depois de N propostas medidas na fase 1 (💭 50), com pouca edição, em vez de 60 dias fixos | Recomendação; confirmar ao chegar à 135 | Revê a D-E002-04 |
| D-MC-33 | No piloto, o canal usa o usuário robô da corretora de registro, com prioridade para o pedido ao vivo e renovação em janela; no público, robô próprio do canal | Recomendação | Revê a D-E007-06 no piloto |
| D-MC-34 | Páginas para o cliente: personalizáveis por corretora, bonitas, persuasivas e honestas ("uau"), com modelo visual aprovado antes da 130 | Amandus, 03/10 | §7 |
| D-MC-35 | Senhas e segredos citados no parecer, inclusive apagar as gravações do intake depois das fixtures (a execução não apaga intake, CLAUDE.md §13.5): o Amandus cuida fora do programa; não bloqueiam SPEC | Amandus, 03/10 | — |
| D-MC-36 | Prova de instalação cedo (133-A), sem dado pessoal | Amandus, 04/10 (confirmada ao declarar o início) | §4 |
| D-MC-37 | No código, o cálculo não usa o nome "quote" (já é o funil). Porta proposta: `MulticalculoProvider` | Recomendação do parecer | 129-B |
| D-MC-38 | A fila deste plano substitui a ordem da D-FILA-01 e a D-E002-07. O registro no canon é a primeira tarefa do passo 0.5 | Amandus, 04/10 (confirmada ao declarar o início) | Canon |
| D-MC-39 | O conhecimento destilado das conversas continua **global e compartilhado** por todas as corretoras ("O Atlas é UM SÓ, e é de todas", decisão do Founder de 15/08). A P-E0018-14 só garante que ele saia sempre anônimo: um guarda obrigatório antes de gravar deixa entrar o que descreve o serviço e barra nome de corretora, nome de pessoa, telefone, CPF, placa e e-mail. **Nunca** pôr `company_id` na `conduct_playbooks`, porque isso mataria o compartilhamento | Amandus, 04/10 (o conserto pela revisão, nota 85) | Passo 0.5 |
| D-MC-40 | A 129-B prova o isolamento com 1 robô em cada uma de 2 corretoras. O rodízio entre 2 robôs da mesma corretora é provado em teste automático, e ao vivo quando o segundo login existir. A distribuição do canal entre corretoras nasce na 133-B, como camada sobre o roteador da 129-B | Claude, por delegação (revisão, item 9) | 129-B · 133-B |
| D-MC-41 | O recálculo volta à conta da corretora onde o negócio nasceu, não ao mesmo login | Claude, por delegação (revisão, item 12) | 129-B |
| D-MC-42 | Concorrência na 129-B: fila e navegador próprios para o cálculo. Soltar o navegador depois do disparo fica descartado, porque perde o resultado aos poucos | Claude, por delegação (revisão, item 10) | 129-B |
| D-MC-43 | O PDF da proposta sai de um render próprio, fora do navegador do cálculo: Chromium na imagem do `smith-api` ou serviço de render | Recomendação (80 × 50); decidir na 130-A | 130-A |
| D-MC-44 | A proposta tem 2 opções por padrão: "completa (recomendada)" e "econômica", com nota de 0 a 100 e motivos | Amandus, 04/10 (o desenho sai no portão de preço) | 130-A, 131, 133-B |
| D-MC-45 | Portão de preço: com os números da 128 na mão, o Claude Code faz ao Amandus as perguntas de preço na abertura da 130-A (como montar as 2 opções; quando usar a comissão) e na abertura da 133-B (a comissão do canal, D-MC-29) | Amandus, 04/10 | 130-A · 133-B |
| D-MC-46 | Barrar o CPF de outra pessoa: declaração "sou o segurado ou tenho autorização dele"; o servidor compara o nome da apólice com o nome que o Agger devolve pelo CPF (nunca mostrado); se divergir, para. Nunca sinalizar "já cotado" ou "já cliente" | Claude, por delegação (revisão, de fora, item 1) | 133-B |
| D-MC-47 | O robô marca no Agger os negócios que cria e nunca recalcula um negócio que uma pessoa mexeu há menos de 24 h | Claude, por delegação (proposta 002 §4) | 129-B |
| D-MC-48 | Os dois consertos do passo 0.5 seguem o rito CRÍTICO (protocolo §3.2): juiz, red team e a prova do §9.1 | Claude, por delegação (revisão, ponto b) | Passo 0.5 |
| D-MC-49 | **Execução contínua.** O Claude Code segue o plano sozinho, SPEC atrás de SPEC, na mesma pasta, sem esperar aprovação entre elas. Para só nas paradas do CLAUDE.md §10 e nos portões do §0.1. Encadeia 2–3 SPECs por chat e, quando o contexto encher, entrega o texto para o chat seguinte. O plano fica gravado no repositório | Amandus, 04/10 | §0.1 · §12 |
| D-MC-50 | **Narração ao vivo honesta.** Durante o cálculo, o chat conta o que está acontecendo ("Cotando na Porto…", "Nova liderança…"), e cada frase nasce de um evento real do cálculo. Se demorar, mostra o que já chegou e segue atualizando; seguradora com erro ou recusa sai da espera | Amandus, 04/10 (a ideia); o desenho é recomendação | 133-B · §6.6 |

---

## 3. Por que esta ordem

- **129-A primeiro:**
  - não depende do Agger;
  - todo cálculo precisa dela;
  - os defeitos estão abertos desde 22/09.
- **128 em seguida:**
  - começa sem conta nenhuma: transforma as gravações em fixtures saneadas e depois apaga as gravações;
  - depois faz 2 sessões ao vivo;
  - responde o que muda o motor: renovação a partir da InfoCap, seguro novo, simultaneidade, volume, comissão por cálculo.
- **133-A cedo:** é a prioridade número um do Amandus. Mede a instalação com leigos antes de investir na 133-B:
  - não tem dado pessoal;
  - vira a base da 133-B;
  - pode trocar de lugar com a 128.
- **129-B depois da 128:** com a moradia do canal já decidida (D-MC-26).
- **130 → 131 → 132:** como antes; a 130 se divide em duas partes.
- **133-B depois da 132;** a ★ se decide com os números da 133-A e da 133-B.
- **134 precisa do atendimento ligado** (testes da classe A) e da verificação na Meta, que começa durante 129–131. A ★ não trava a 134.
- **135 precisa do atendimento ligado e da D-MC-32.**
- **136 precisa do opt-in registrado** em nome da corretora de registro (nasce na 133-B).

**Sobreposições declaradas** (cada ficha diz o que absorve):

| SPEC do canon | Tema | Onde entra no programa |
|---|---|---|
| 099 | canais | 134 |
| 107 | porta de conteúdo não confiável (PDF, MCP) | 130-B e 133-B |
| 109 | motor headless e `renewals.radar` | 129-B e 131 |
| 110 | gateway para ChatGPT/Claude | 133-A (primeira fatia), 133-B e 138 |
| 111 | custo e cota | 129-B e 133-B |
| 101 | conectores de gestão | Depois do programa (D-E002-08 × D-PILOTO-16 em aberto) |
| EXTRA-005 | reativação | 136 |

**Depois do programa (ordem proposta):**
1. 138: o corretor cota dentro do ChatGPT/Claude (recorte da 110).
2. 103: marketplace de auxiliares.
3. 101 + EXTRA-008/009: um segundo multicálculo (Quiver, Segfy) e corretoras fora da InfoCap. Sobe para logo depois da 133-B se o Agger restringir o uso.
4. Outros ramos.
5. EXTRA-005 e EXTRA-006.
6. Fase 3.
7. 001.9 e 001.0.
8. Restante da 099–114.
9. 114 e 115.

---

## 4. As fichas

Cada ficha diz o objetivo, o que entra, o que não entra, o que absorve e quando está pronta. Os portões G1–G20 da proposta 002 §7 valem e são citados por número nas SPECs. Exemplos:
- G7: detector de vazamento com teste de mutação;
- G10: dois processos disputando um login.

### Passo 0 · Fechar a 126/127 (sem SPEC nova)
- **Estado (Amandus, 04/10):** o código terminou; faltam os testes de conversa de atendimento no WhatsApp, pelo celular.
- **Se um teste falhar:** o Amandus cola o erro no chat do programa, que conserta antes de seguir.
- **O que não depende só do Amandus:**
  - T-93 a T-96 dependem do ensaio do grupo de WhatsApp (T-23 a T-25, T-08);
  - T-101 depende de T-55/56;
  - T-97 e T-103 esperam evento externo;
  - T-98 e T-102 são verba, não teste.
- **Esses vão para o mapa de testes (§10).** Travam ligar o atendimento, não o programa.

### Passo 0.5 · Decisões e consertos curtos (sem SPEC grande)
1. **Registrar no canon:**
   - as decisões D-MC-08 a D-MC-38 (as recomendações como propostas, até a confirmação);
   - a nova fila, nos documentos de estado;
   - as substituições: a ordem da D-FILA-01, a D-E002-01, a D-E002-07 e, como descrito no §2, a D-E002-04, a D-E007-03 e a D-E007-06.
2. **Conserto do link público `/r/`:**
   - incluir `'/r/'` em `publicPrefixes` (`middleware.ts:111-113`). A rota já foi feita para ser pública: recusa token fora do formato e devolve "Link indisponível" (`app/r/[token]/route.ts:37-50`);
   - prova: `npm run test:rotas-montam`, `next start` e um `GET` sem sessão que não cai no `/login` (CLAUDE.md §9.1);
   - contar, por corretora, os links gerados nos últimos 30 dias, para o corretor reenviar se quiser.
3. **Conserto da P-E0018-14 (D-MC-39).**
   - **O conhecimento destilado das conversas é global por desenho.** Toda corretora que pareia o WhatsApp alimenta o mesmo acervo, e todas usam ("O Atlas é UM SÓ, e é de todas").
   - **O conserto não muda isso.** Ele põe um guarda obrigatório antes de gravar na `conduct_playbooks` (1 escritor, `attendance_distiller.py:1178`):
     - entra o que descreve o serviço;
     - não entram nome de corretora, nome de pessoa, telefone, CPF, placa e e-mail.
   - **Teste com mutação:** o guarda fica vermelho com um nome de corretora reintroduzido.
   - **Nunca** pôr `company_id` nessa tabela.
4. **Rito:** os dois consertos mexem em sessão ou em conhecimento entre corretoras, então seguem o piso CRÍTICO, com juiz, red team e a prova do §9.1 (D-MC-48).
5. **Implantar os 4 serviços.** Isso também traz a produção para a `main` atual.

### SPEC-129-A · A espera durável
- **Objetivo:** um pedido dorme por minutos, acorda sozinho, sobrevive a reinício e nunca roda duas vezes.
- **Primeira etapa — só leitura em produção:**
  - **inventário dos trabalhos presos, por tipo** (só SELECT);
  - **as duas chaves,** que o Amandus informa no prompt: `WORK_RUNS_ROUTINE_BRIDGE` e `WORK_WORKER_IN_PROCESS`, do Environment do `smith-api`. Se não vierem, pergunte:
    - com `WORK_RUNS_ROUTINE_BRIDGE` ligada (ponte_rotinas), a 129-A mexe em algo que envia mensagem, e o rito sobe para CRÍTICO;
    - com `WORK_WORKER_IN_PROCESS` ligada (worker_na_api), o reinício silencioso está ativo em produção;
  - **a regra:** volta para a fila só o que nasceu pela fila e tem executor; o que está velho fecha como expirado e nunca roda (os acionamentos "sem fila" ficam de fora, §1.3).
- **Entra:**
  - os 5 defeitos do §1.3: o "tentar de novo" que nunca volta; a conclusão por cima da aprovação; o "Reprocessar" mudo; a espera de 150 s com `time.sleep`; o reinício silencioso;
  - P-223 / P-126-09: CPF e telefone em claro em `work_steps` — todo cálculo leva CPF. Mascarar as 📊 12 linhas antigas (18–19/08) altera dado: rito CRÍTICO, com a conferência independente no banco (a "lente do dado");
  - P-093B-RLS (`work_waits` com RLS ligada e 0 policies), só se a espera usar `work_waits`. Se usar `work_runs.wake_at` (o desenho da proposta 003, fatia 1), ela sai;
  - a primeira migration põe o MANIFEST em dia, inclusive `20261002_10/_11` (P-126-24).
- **Saem da 129-A:**
  - P-126-16 vai para a fila do atendimento (é lógica do atendimento);
  - P-198 e P-182 vão para a 129-B, com a prova contra Redis real.
- **Não entra:** nada do Agger.
- **Pronta quando:**
  - um trabalho de teste dorme 10 min e acorda;
  - um reinício no meio retoma sem duplicar;
  - o "tentar de novo" roda só para o que pode rodar;
  - o "Reprocessar" funciona;
  - nenhum CPF fica em claro em `work_steps`;
  - o manifesto está em dia.
- **Tamanho:** M, 2 etapas.

### SPEC-128 · A prova do Agger
- **Objetivo:** medir tudo que o motor precisa antes de construí-lo.
- **Modo:**
  1. **Primeiro, sem conta:** transformar as 3 gravações (HAR) em fixtures saneadas (P-E002-HAR). A execução não apaga material de intake (CLAUDE.md §13.5); apagar as gravações fica com o Amandus (D-MC-35).
  2. **Depois, 2 sessões ao vivo** (💭 4–6 h, ≈ 10–14 cálculos; **teto de 25 cálculos**, proposta 002 §4), conduzidas passo a passo em modo investigação, com captura. O robô de ponta a ponta é da 129-B.
- **O que a evidência já responde:**
  - **E6:** vários pacotes por cálculo;
  - **E8:** o preço difere entre corretoras, por construção;
  - **E10:** famílias de resposta — oferta, credencial, permissão, aceitação, comercial, instabilidade;
  - **E11:** o que fica gravado — negócio e versões;
  - **E5 e E9:** parciais.
- **O que medir:**

| # | O que medir |
|---|---|
| E0 | Volume AUTO por dia em cada corretora. Sem ele não se dimensionam os usuários robô |
| E1 | Entrar com o login dedicado sem derrubar ninguém; quanto dura a sessão |
| E2 | Renovação a partir dos dados da InfoCap: quais campos do formulário ela preenche e quais faltam (ex.: questionário de risco); com que frequência existe negócio anterior no Agger para enriquecer |
| E3 | **Seguro novo** com o formulário do zero: fluxo e campos obrigatórios |
| E4 | CPF: obrigatoriedade e validação; o que acontece com CPF fora do cadastro |
| E5 | **Alavancas de preço** (o ajuste mais pedido é preço, D-MC-14): quanto cada uma baixa o prêmio, mudando só ela, em 2–3 perfis — comissão, assistência (guincho), carro reserva, vidros, franquia, % da FIPE. E o tempo de um ajuste isolado |
| E7 | Simultaneidade por usuário: dois cálculos na mesma sessão (abas)? Dois usuários robô em paralelo? Se der 2 ou mais por sessão, a reserva precisa mudar: hoje ela permite um trabalho por login, por construção (`worker.py:1716-1725`) |
| E9 | Tempos com n ≥ 10, lendo o histórico de versões sem calcular |
| E12 | PDF da seguradora e o "Imprimir" do Agger |
| E13 | Mapear, sem calcular, o formulário de residencial |
| E14 | Que documento e código de corretor cada seguradora usa em cada conta (pessoa física e jurídica) |
| E15 | A cota de cálculos do plano Agger, e se a consulta de CPF é cobrada |
| E16 | Comissão e desconto por cálculo: dá para definir por pedido? Qual o efeito no prêmio, mudando só isso? |
| E17 | Como se apaga um negócio no Agger (obrigação de LGPD no fornecedor) |
| E18 | Renovação do token de 3 h sob a reserva |
| E19 | O bloqueio do usuário depois de senhas erradas (`bloqueioPreventivo`): guarda para nunca disparar |
| E20 | **Duas opções num cálculo só:** a "completa" e a "econômica" (coberturas e assistência diferentes) saem de um cálculo, configurando pacotes? E o modelo de 3 opções da corretora? |
| E21 | A lista de seguradoras que respondem em cada conta (base para qualquer frase pública sobre "as maiores seguradoras") |

- **Entrega:**
  - tabela de capacidade;
  - decisões;
  - contrato do cálculo por ramo (entrada, resultado aos poucos, ajuste) com fixtures saneadas na `main`.
- **Pronta quando:**
  - todos os E têm resposta;
  - E0, E2, E3, E5, E7, E16 e E20 respondidos com número;
  - as fixtures saneadas estão na `main`.
- **No relatório final:** as perguntas do portão de preço (D-MC-45) já vêm prontas, com os números das alavancas, para o Amandus responder antes da 130-A.
- **Entra quando:**
  - houver autorização escrita da corretora para concluir cálculos (D-MC-23);
  - o login estiver livre no horário (D-MC-24);
  - houver 3–5 apólices autorizadas.
- **Absorve:** EXTRA-002, parte 2.
- **Tamanho:** M, 2–3 etapas.

### SPEC-133-A · A tomada e a prova de instalação (nova)
- **Objetivo:** saber, com pessoas leigas e o celular delas, se conseguem instalar o Quem Cobra Menos no Claude e no ChatGPT, quanto tempo leva e onde travam. Tudo isso antes de investir na cotação pelo chat.
- **Entra:**
  - **Servidor MCP:** serviço próprio, mesmo repositório, implantação separada, endereço próprio. Sem chave mestra do banco e sem dado pessoal.
  - **2 ferramentas sem dado pessoal:**
    - "como funciona / boas-vindas";
    - "explicar termos do seguro auto" (base da 001.5 + glossário).
  - **Link pessoal revogável:** o link que a pessoa cola já é o convite.
  - **Kit de instalação (§6.2):**
    - página para celular com botão "copiar meu link";
    - atalhos para as telas certas (a conferir);
    - vídeo de 40 s;
    - texto pronto para WhatsApp;
    - ajuda humana no WhatsApp.
  - **Medição:** convite → instalou (primeira chamada) → tempo → plataforma (Claude ou ChatGPT; app ou navegador).
  - **No ChatGPT:** testar "Create MCP App" com contas pessoais (Free, Go, Plus), porque a elegibilidade está incerta (§1.4).
- **Protocolo:** 10–15 leigos, metade com Claude e metade com ChatGPT, cada um com o plano que já tem, sem ajuda nos primeiros 5 minutos.
- **Antes de executar:** o Amandus cria o serviço e o domínio no EasyPanel. Usa o nome escolhido, ou um provisório (D-MC-22).
- **Pronta quando:**
  - 📊 % de instalações sem ajuda, por plataforma;
  - 📊 tempo mediano;
  - lista dos pontos de travamento;
  - recomendação para a ★.
- **Absorve:** a primeira fatia da SPEC-110.
- **Tamanho:** 💭 M, 2 etapas.

### SPEC-129-B · O motor de multicálculo
- **Objetivo:** qualquer parte do AutoBrokers pede "calcule" ou "recalcule com este ajuste" e recebe o resultado aos poucos, sem saber qual multicálculo nem qual login foi usado.
- **Entra:**
  - **A porta:** `MulticalculoProvider` (D-MC-37), no molde da `PolicyDataProvider` (`policy_data_provider.py:1904`). Ela calcula, consulta aos poucos, recalcula com ajuste, baixa o PDF e informa as capacidades por ramo.
  - **O adaptador do Agger** no `portal-worker` (journeys `agger.*`):
    - interceptação (D-MC-28);
    - renovação do token de 3 h sob a reserva;
    - nunca reconstruir a autenticação.
  - **Onde o resultado fica:** pedido de cálculo, versões e ofertas, com a corretora de registro em cada linha de oferta. Nasce aqui, não na 130.
  - **Usuários robô:**
    - colunas novas em `portal_accounts`: estado, teto por hora, janela de horário. É migration crítica, com APPLY, VERIFY, ROLLBACK e o manifesto atualizado;
    - um login por usuário robô (D-MC-24);
    - P-198: a reserva provada contra Redis real;
    - P-182: o cofre com suporte a duas chaves, para trocar a chave sem cifrar tudo de novo depois que as senhas dos robôs entrarem.
  - **Roteador:**
    - compõe o `resolver_conta` de cada corretora;
    - a trava "conta da mesma corretora" do worker continua;
    - o roteador do canal entre corretoras nasce na 133-B, como camada por cima deste (D-MC-40), sem reimplementar.
  - **Afinidade:** o recálculo volta à conta da corretora onde o negócio nasceu, não ao mesmo login (D-MC-41).
  - **Concorrência:** um cálculo de 7 minutos não pode prender o navegador da cobrança e dos vidros. A saída é fila e navegador próprios para o cálculo (D-MC-42). Soltar o navegador depois do disparo perderia o resultado aos poucos.
  - **Convivência com as pessoas:** o robô marca no Agger os negócios que cria e nunca recalcula um negócio que uma pessoa mexeu há menos de 24 h (D-MC-47).
  - **O que sai do adaptador:**
    - só o que está na lista branca (as senhas das seguradoras vêm em 📊 28 de 28 consultas, e a comissão vem no resultado);
    - a sessão e o token do robô são segredo de nível máximo;
    - nenhuma resposta crua vai para log ou evidência.
  - **PDF:** o da seguradora é copiado para o nosso armazenamento; o link do fornecedor nunca é repassado.
  - **Freios:** por usuário robô e por hora, por corretora, geral e por seguradora por dia.
- **Não entra:** ler apólice, comparar, proposta (130), ciclo (131), conversa (132/133).
- **Pronta quando:**
  - **com 1 usuário robô:**
    - renovação (dos dados da InfoCap) e seguro novo de ponta a ponta;
    - um ajuste vira nova versão;
    - worker morto no meio retoma sem recalcular;
  - **com 1 robô em cada corretora (Resulta e AutoFleet):**
    - as duas corretoras isoladas: o que é de uma não aparece para a outra;
    - cada oferta com a corretora de registro certa;
  - **rodízio entre 2 robôs da mesma corretora:**
    - provado em teste automático;
    - provado ao vivo quando o segundo login existir (D-MC-40);
  - **sempre:**
    - senha nunca em log nem em resultado;
    - cobrança e vidros não travam durante um cálculo;
    - custo de modelo por cálculo medido (meta: zero).
- **Absorve:** EXTRA-003-A. Sobrepõe 109 e 111.
- **Tamanho:** G, 5–6 etapas, crítica.

### SPEC-130 · Comparação, proposta e registro (130-A) · leitor de apólice (130-B)

**130-A**, consumida pela 131:
- **Portão de preço na abertura (D-MC-45).** Com os números da 128 (alavancas, E16, E20), o Claude Code pergunta ao Amandus:
  - como montar a opção econômica (comissão, assistência, coberturas);
  - quando o agente pode propor baixar a comissão, e até onde;
  - se a nota de 0 a 100 e os motivos aparecem para o cliente.
- **Duas opções por padrão (D-MC-44):**
  - a "completa (recomendada)" e a "econômica", com nota de 0 a 100 e motivos;
  - é a resposta antecipada à objeção mais comum, o preço;
  - se a E20 confirmar, as duas saem de 1 cálculo; senão, de 2.
- **Comparação determinística:**
  - mesma cobertura;
  - rótulos (menor preço, menor franquia, mais parecida com a atual);
  - diferenças em linguagem simples;
  - "pegadinhas" da apólice atual;
  - economia só quando real.
- **Proposta:**
  - página no padrão do cliente (§7, modelo visual aprovado);
  - PDF gerado da mesma página, num render próprio, fora do navegador do cálculo (D-MC-43). Hoje o Chromium só existe na imagem do `portal-worker`;
  - versões a cada ajuste;
  - validade tirada do PDF da seguradora, porque não é fixa (📊 5, 18, 6 e 10 dias, n = 4);
  - o modelo de 3 opções da corretora, quando ela quiser: 1 cálculo se a E20 confirmar, senão 2–3.
- **Registro:**
  - **oportunidade:**
    - evoluir `leads`: conferir o schema no banco vivo; o `email` NOT NULL e o `UNIQUE(company_id, email)` vêm de um retrato antigo. É migration crítica;
    - consolidar com `users_v2` "lead";
  - **consentimento:** tabela nova com `company_id`;
  - **"não me contate":** por telefone.
- **Remuneração:** a proposta tem como mostrar a remuneração da corretora. A Res. CNSP 382/2020, art. 4º, §1º, IV, no texto original, manda informar antes da aquisição. Alteração posterior não foi conferida; o jurídico vem depois.

**130-B**, consumida pela 132 e pela 133-B:
- **Extrator apólice → ficha:**
  - PDF e foto;
  - origem e confiança por campo;
  - validação do CPF (dígitos), da placa e das datas;
  - o modelo mais barato que passar na bancada (o Luna é candidato).
- **Bancada:** 20–30 apólices reais autorizadas. É crítica, porque há CPF na bancada.
- **Verba:** crédito de API (T-04).

**Comum às duas partes**
- **Absorve:** 003 fatia 4 e 004 fatia 3. Sobrepõe a 107.
- **Pré-requisito:** o link `/r/` consertado no passo 0.5.
- **Tamanho:** G, 4–5 etapas, crítica.

### SPEC-131 · Auxiliar de Renovação, fase 1
- **Objetivo:** as renovações da janela aparecem calculadas, comparadas e com proposta pronta; o corretor revisa, ajusta e envia.
- **Entra:**
  - **Ciclo:**
    - a lista de renovações da InfoCap, guardando o CPF que hoje se descarta, mas sem deixá-lo em claro;
    - a apólice da InfoCap (placa, chassi, FIPE);
    - a janela (D-30, configurável);
    - o motor;
    - a proposta (130-A).
  - **Recálculo** perto do fim da validade ou quando o cliente aceitar.
  - **Painel** por estado, com "refazer com ajuste". Precisa da prova de que o servidor sobe (§9.1).
  - **Executor real e determinístico,** no molde da cobrança. A "fábrica" só classifica; não se aproveita o "sucesso" falso do `bridge_auxiliar`.
  - **Envio:** é ação do corretor.
- **Entra quando:** a InfoCap da Resulta estiver de volta na Resulta (D-MC-27), com prova em duas corretoras.
- **Pronta quando:**
  - as renovações AUTO de uma semana real ficam prontas sem ninguém calcular;
  - os ajustes são refeitos pelo painel;
  - 📊 % de propostas enviadas sem edição;
  - 📊 % de clientes que pedem ajuste com as 2 opções, contra os 3 em 5 de hoje (H11).
- **Absorve:** EXTRA-003-B. Sobrepõe a 109.
- **Tamanho:** G, 4 etapas, crítica.

### SPEC-132 · Auxiliar de Cotação, fase 1
- **Objetivo:** o corretor escreve "cota…" ou "ajusta…" no chat do AutoBrokers e recebe o resultado na mesma conversa.
- **Entra:**
  - ferramentas cotar, ajustar e versões;
  - entrega do resultado na conversa quando ele chegar (`work_runs.conversation_id`) — nenhuma ficha cobria isso;
  - confirmação antes de disparar, no molde do portão da 126;
  - sem repetição: P-126-13, os "dois cliques";
  - apagar o CPF antes do modelo. Hoje o PDF anexado vai ao modelo principal sem redação (`chat.py:829-841`), e o Presidio vem desligado.
- **Absorve:** EXTRA-004.
- **Tamanho:** M, 3 etapas, crítica.

### SPEC-133-B · Quem Cobra Menos piloto: cotação no chat
- **Objetivo:** pessoas comuns cotam conversando no Claude (e no ChatGPT, se a 133-A mostrar que dá), com o cálculo real na conversa.
- **Portão de preço na abertura (D-MC-45):** a comissão e o desconto do canal com Resulta e AutoFleet (D-MC-29), e quais das 2 opções o canal mostra.
- **Narração ao vivo honesta (D-MC-50, §6.6):**
  - a ferramenta "ver resultado" devolve as ofertas que já chegaram e os eventos reais desde a última consulta;
  - o roteiro manda o modelo narrar esses eventos em frases curtas e consultar de novo até o fim, com teto de tempo;
  - a página ao vivo mostra o mesmo.
- **Corte por tempo:**
  - passado um tempo (definido com os números da 128), mostra a melhor oferta até ali e segue atualizando;
  - seguradora com erro ou recusa sai da espera na hora;
  - a promessa é mostrar quem cobra menos, não ser o mais rápido.
- **Entra** (sobre a tomada da 133-A):
  - **ferramentas:**
    - começar comparação, com consentimento;
    - enviar apólice (arquivo ou campos) e CPF;
    - ver resultado aos poucos, com página ao vivo;
    - ajustar;
    - explicar cobertura (complementar a base da 001.5, que hoje explica assistências e não casco ou franquia);
    - falar com especialista: wa.me para o número de venda da corretora de registro;
    - me avise no vencimento: opt-in em nome da corretora de registro;
  - **proteções do §6.3,** todas condição de pronto, inclusive barrar o CPF de outra pessoa (D-MC-46);
  - **o roteador do canal entre corretoras** (D-MC-40), por cima do roteador da 129-B;
  - **preço:** D-MC-29;
  - **dados:** §6.5;
  - **roteiro versionado:**
    - texto primeiro;
    - objeções com suavidade;
    - a seguradora vencedora e a corretora de registro no fim;
    - remuneração informada a quem perguntar.
- **Pronta quando:**
  - 10–30 pessoas reais cotaram de ponta a ponta;
  - 📊 tempo até a primeira oferta e até o conjunto;
  - 📊 % que pede contato;
  - nenhum dado de uma pessoa aparece para outra;
  - os testes de abuso falham fechado: CPF de outra pessoa, o mesmo CPF repetido, teto atingido.
- **Sobrepõe:** 107, 110 e 111.
- **Tamanho:** G, 3–4 etapas.

### ★ Decisão do canal público
- Com os números da 133-A e da 133-B. Ver §6.1.

### SPEC-134 · WhatsApp oficial (recorte da 099)
- **Entra:**
  - provedor Meta e webhook com assinatura;
  - modelos, opt-in e janela de 24 h;
  - prender o canal na conversa (`integration_service.py:318-376`);
  - um segundo número, porque o atual faz atendimento e observação (D-Canal-01).
- **Fora do código:** a verificação do negócio na Meta. Começa durante 129–131.
- **Entra quando:** o atendimento estiver ligado (testes da classe A, §10).
- **Tamanho:** G, 3–4 etapas, mais o prazo da Meta.

### SPEC-135 · A proposta conversa (fase 2)
- **Entra:**
  - a ferramenta "proposta" no agente de atendimento, com dois modos (renovação e seguro novo);
  - o dossiê de fechamento;
  - as regras de parada.
  - `HumanHandoffTool`, `enviar_ao_grupo` e Skill Registry já existem.
- **Entra quando:** o atendimento estiver ligado e a D-MC-32 for cumprida.
- **Tamanho:** M, 2–3 etapas.

### SPEC-136 · Lembretes de vencimento
- **Entra:**
  - filtro de data (D-30/D-15, configurável);
  - o "não me contate" conferido na porta de saída;
  - para quem veio do Quem Cobra Menos: o número oficial e o opt-in de cada corretora parceira;
  - o molde da cobrança: intervalo entre envios, estados que não voltam, governador de mensagem fria.
- **Sobrepõe:** EXTRA-005.
- **Tamanho:** M, 2 etapas.

### SPEC-137 · Quem Cobra Menos público
- **Entra:** o que a ★ escolher (§6.1).
- **Já existe:** `legal_documents` e `/landing`.
- **Projeto Supabase separado:** seria uma segunda fonte de verdade (CLAUDE.md §6). Evitar.
- **Tamanho:** G (isca) a GG (login e conta).

---

## 5. O motor em detalhe — feito para escalar

**Usuários robô**
- No Agger, cada corretora tem um contrato com N licenças, e cada licença é um login.
- A sessão é única por login: o login do robô derruba quem estiver nele, e vice-versa.
- Por isso o robô tem login próprio (D-MC-24). Escalar = mais logins de robô, não mais contas.

**Quem usa quais usuários**
- Um auxiliar de uma corretora usa só os robôs dela.
- O canal Quem Cobra Menos usa os robôs das corretoras que aderiram (D-MC-26). O roteador entre corretoras nasce na 133-B (D-MC-40).
- No piloto, o canal divide o robô da corretora de registro, com prioridade para o pedido ao vivo (D-MC-33).

**Corretora de registro**
- É a dona do login que calculou. É ela que aparece no fim, recebe a oportunidade e pode fechar.
- A E14 confere se cada login tem uma corretora só. Na conta medida, é a mesma corretora como pessoa física e como pessoa jurídica.

**Preço**
- Depende da comissão e do desconto da corretora, por seguradora.
- Num canal com várias corretoras, o mesmo pedido teria preços diferentes conforme o login livre. Por isso o preço do canal vem de um termo por corretora (D-MC-29).
- A E16 mede se a comissão pode ser definida por cálculo. Se puder, ela vira um ajuste de primeira classe:
  - "baixar a comissão para fechar" na renovação;
  - "preço do canal" no Quem Cobra Menos.

**Roteamento**
- Escolhe um login livre entre os elegíveis, reserva, calcula e libera.
- Se não houver login livre, o pedido vai para uma fila com tempo de espera real.
- O recálculo volta à conta da corretora onde o negócio nasceu, por qualquer robô livre dela (D-MC-41).
- O cálculo tem fila e navegador próprios, separados da cobrança e dos vidros (D-MC-42).

**Aos poucos**
- As seguradoras respondem em segundos ou minutos. A porta entrega cada oferta quando chega e fecha o conjunto no fim.

**Proteções**
- Freios por login, por corretora, geral e por seguradora por dia.
- Lista branca na saída.
- Segredo de nível máximo para a sessão do robô.
- Nenhum nome de corretora no código.
- Isolamento provado com duas corretoras.

**Observação**
- Cálculos por login, tempos, falhas por seguradora e custo por cálculo.

---

## 6. Quem Cobra Menos — instalação, CPF e apólice

### 6.1 Todos os caminhos (FATOS de 03/10; notas = julgamento)

A nota mede a facilidade para um leigo no celular, que é o critério principal do Amandus, junto com o valor para o negócio.

| Caminho | Plano | Como a pessoa instala (celular) | Revisão | CPF e apólice | Piloto guiado | Leigo sozinho |
|---|---|---|---|---|---:|---:|
| Claude · diretório de conectores | Todos, inclusive Free | 1–2 toques (pelo app, em beta; pela web, sempre) | Anthropic | Política pede só o dado necessário e uma política de privacidade; sem proibição explícita de CPF (HIPÓTESE a testar na submissão) | — | 80 |
| WhatsApp/site próprio (isca) | Todos | Nenhuma instalação | Nenhuma de plataforma | Sim (LGPD) | — | 75 (sem o gancho do ChatGPT) |
| ChatGPT · diretório | Todos (varia por app e região) | 2–3 toques, no app | OpenAI | CPF proibido no app → CPF e apólice na conta, no nosso site | — | 70 |
| Claude · conector personalizado | Todos (Free: 1 conector) | Pelo navegador do celular (claude.ai), ~6 passos; no app, em beta; depois funciona no app | Nenhuma | Sim | 75 | 40 |
| Claude · plugin pelo GitHub ("Adicionar marketplace") | Planos pagos (Free a conferir) | Web ou desktop | Nenhuma | Sim | 40 | 10 |
| ChatGPT · "Create MCP App" (conta pessoal) | Incerto: a página oficial diz Business/Enterprise/Edu (Pro só leitura); a OpenAI disse em 01/10 que "usuários elegíveis" podem | Só na web; no celular, "não" (página oficial) | Nenhuma | Sim | 20 | 5 |
| ChatGPT · plugin em Sites, zip ou prompt | Hospedar: todos; conta pessoal não compartilha por link | — | — | — | 5 | 0 |

**Conclusão**
- **Para um leigo sozinho no celular, o fácil de verdade é o diretório ou o WhatsApp.**
  - Fora do diretório, instalar pede navegador e ~6 passos.
  - Nenhum texto ou prompt instala nada sozinho.
- **Piloto (133-A e 133-B):**
  - Claude por conector personalizado, guiado: kit e ajuda humana;
  - ChatGPT só se a 133-A provar que contas pessoais conseguem. Senão, ele entra direto pelo diretório.
- **Público (★):**
  - recomendação provisória: primeiro o diretório do Claude (Free e celular; CPF sem proibição explícita);
  - depois o do ChatGPT, no modo conta, pelo tamanho do público;
  - o WhatsApp é a rede de segurança sem instalação.
  - A decisão sai com os números.

### 6.2 O kit de instalação (rascunho; conferir na 133-A)

Texto para WhatsApp (Claude):
> Oi! Para cotar seu seguro no Claude com o Quem Cobra Menos (uns 2 minutos):
> 1. Copie seu link pessoal: [link]
> 2. Abra claude.ai no navegador do celular e entre na sua conta (a mesma do app).
> 3. Toque em Personalizar → Conectores → + Adicionar → Conector personalizado.
> 4. Nome: Quem Cobra Menos · URL: cole o link · Sem login → Adicionar.
> 5. No app do Claude, toque em + → Conectores e ligue o Quem Cobra Menos.
> 6. Escreva "quero cotar o seguro do meu carro" e mande a foto ou o PDF da apólice.
> Travou? Responda esta mensagem que eu te ajudo.

**A página do kit**
- Botão "copiar meu link".
- Atalho para a tela de conectores (endereço a conferir).
- Vídeo de 40 s.
- Botão "começar minha cotação", com o pedido já escrito (`claude.ai/new?q=…`, a conferir).
- Os nomes dos menus vêm da página oficial em inglês ("Customize → Connectors → Add → Add custom connector"). Em português, conferir na tela.

### 6.3 CPF, apólice e proteção contra abuso

**Piloto (modo direto)**
- O Claude lê a apólice e manda os campos à ferramenta.
- O CPF é digitado se não estiver na apólice. A 130-B mede em quantas apólices ele vem.
- O servidor valida os dígitos.
- Nunca CPF inventado ou de terceiro.

**Proteções obrigatórias** (condição de pronto da 133-B)
- **Porta de entrada:** convite pessoal revogável no próprio link (D-MC-30), teto diário global e interruptor.
- **Limites:**
  - por HMAC do CPF: uma impressão digital que só nós reproduzimos, com chave no cofre. É uma função nova; a atual (`cpf_hash_de`) continua, porque é a lista de liberação do canário (T-101);
  - por placa e por sessão;
  - falhando fechado;
  - sem confiar em IP, que no MCP é o da OpenAI ou da Anthropic.
- **Teto por seguradora por dia:** cada oferta gera um cálculo sob o código da corretora e mexe na taxa de conversão dela.
- **Saída:** lista branca, só ofertas. Nunca devolver os dados de cadastro que o Agger traz a partir do CPF (nome, nascimento, sexo, estado civil). Sem isso, o Quem Cobra Menos vira uma máquina de consultar CPF alheio.
- **CPF de outra pessoa (D-MC-46):**
  - declaração "sou o segurado ou tenho autorização dele";
  - no servidor, o nome da apólice é comparado com o nome que o Agger devolve pelo CPF, sem nunca mostrar; se divergir, para;
  - nunca sinalizar "já cotado" ou "já cliente".
  - Esse é o mecanismo que deixa o teste "CPF de outra pessoa falha fechado" ficar vermelho quando deve.

**ChatGPT diretório (modo conta)**
- CPF e apólice na conta, no nosso site. O app nunca vê o CPF.
- HIPÓTESE a testar na submissão.

**Claude diretório**
- HIPÓTESE de aceitar o CPF no conector, com dado mínimo e política de privacidade.

**Campo seguro dentro do chat** (componente interativo): melhoria da v1.1.

### 6.4 Consentimento, vencedora e remuneração

**Linha de consentimento** (ajustada pela D-MC-25; a confirmar):
> "O Quem Cobra Menos é operado pela AutoBrokers e cota nas seguradoras pelo sistema de corretoras parceiras registradas na SUSEP. Seus dados só são usados para isso, e ninguém entra em contato sem o seu pedido."

**Base legal (LGPD)**
- A lista de parceiras fica na política de privacidade (art. 9º, III e V).
- A base é o pedido da própria pessoa (art. 7º, V).
- A prova do consentimento e o "não me contate" ficam no registro do canal (art. 8º, §2º; art. 18).

**No fim da conversa**
- A seguradora vencedora.
- A corretora de registro, com credenciais verdadeiras e link.
- Falar em "disputa entre corretoras" só quando duas ou mais calcularam.

**Avisos (CDC)**
- "Sujeita à aceitação da seguradora; válida até …", com a validade da seguradora.

**Remuneração**
- O modelo não vê a comissão.
- Quem perguntar recebe a resposta.
- A corretora que fecha cumpre a Res. CNSP 382/2020.

### 6.5 Onde ficam os dados (D-MC-26)
- **Na corretora de registro** (com o `company_id` dela): o trabalho, o cálculo, a oportunidade e o consentimento.
- **No registro do canal** (na empresa técnica):
  - o HMAC do CPF;
  - o recibo do consentimento, com a versão do roteiro;
  - para qual corretora foi;
  - a recusa de contato;
  - os contadores.
  - Nunca apólice nem oferta.
- **Antes do roteamento:** só campos, no Redis, com prazo de validade. Nada de bytes de apólice.
- **O serviço MCP não carrega a chave mestra do banco** (service role). Ele fala com o `smith-api` por rotas estreitas.
- **Ler a adesão de todas as corretoras é nível crítico:** só adesão e saúde do login, com teste de guarda em duas corretoras.

---

### 6.6 Narração ao vivo durante o cálculo (D-MC-50)

**Regra:**
- cada frase nasce de um evento real do cálculo: uma seguradora consultada, uma oferta que chegou, uma recusa, o fim;
- nunca uma frase "de efeito" sem o evento;
- "Eureka" só com condição especial real, e "abaixo do que você paga" só quando a apólice atual informa o prêmio.

**Tom:** curto, vivo, no estilo das linhas de status do Claude.

| Momento | Frase (exemplos; o roteiro é versionado) | Evento real que a dispara |
|---|---|---|
| Início | "Lendo sua apólice…" · "Conferindo placa, CEP e vencimento…" | leitura e validação |
| Disparo | "Tudo certo. Chamando as seguradoras para a disputa…" | cálculo disparado |
| Durante | "Cotando na {seguradora}…" | seguradora ainda sem resposta |
| Durante | "{Seguradora} respondeu: R$ {valor} por ano." | oferta recebida |
| Durante | "Nova liderança: {seguradora} assumiu o menor preço." | nova melhor oferta |
| Durante | "Eureka! A {seguradora} veio {X}% abaixo do que você paga hoje." | oferta abaixo do prêmio atual informado |
| Durante | "Achei uma condição especial na {seguradora}: {condição}." | condição real no resultado (ex.: franquia menor pelo mesmo preço) |
| Durante | "Garimpando ofertas… ainda faltam {n} seguradoras." | seguradoras pendentes |
| Durante | "A {seguradora} não quis cotar este perfil. Sigo com as outras." | recusa ou erro |
| Espera | "Algumas seguradoras são mais lentas; às vezes a melhor chega por último." | pendentes depois do primeiro corte |
| Fim | "Raspando o tacho: esperando as últimas respostas…" | poucas pendentes |
| Fim | "Pronto! {n} seguradoras responderam. Separei a opção mais completa e a mais econômica para você." | cálculo fechado |
| Corte | "Já tenho {n} ofertas boas. Vou te mostrando, e se chegar coisa melhor eu aviso." | corte por tempo |

Sobre "raspando o tacho das corretoras": por enquanto, só "raspando o tacho". Há uma corretora de registro por cálculo.

## 7. Páginas do cliente — o padrão "uau" (D-MC-34)

**Onde vale**
- A proposta (130-A).
- A página ao vivo do Quem Cobra Menos (133-B).
- Os relatórios do Artifact Hub.
- Os lembretes (136).

**Requisitos**
- Link público que abre sem login (passo 0.5).
- Personalizável por corretora: logo, cores, fotos e credenciais verdadeiras.
- Feita para o celular, rápida.
- **Estrutura persuasiva e honesta:**
  - o resultado no topo;
  - a opção recomendada em destaque, com o porquê;
  - comparação lado a lado;
  - diferenças em linguagem simples;
  - economia só quando real;
  - prova social verdadeira;
  - um botão claro de WhatsApp;
  - avisos de aceitação e validade.
- O PDF sai da mesma página.
- Versões a cada ajuste.
- Medição de abertura e clique.

**Modelo visual**
- É desenhado em paralelo, fora da fila de SPECs, e aprovado pelo Amandus antes da 130-A.
- Pode ser feito no segundo computador (marketing) ou como protótipo nesta conversa.

---

## 8. Custo por cálculo

- **Sem modelo de linguagem:** login, formulário, cálculo, leitura do resultado, comparação e proposta são código.
  - O custo real é o assento do Agger, as licenças de robô e a máquina do navegador.
- **Modelo barato, cada etapa com papel próprio no Model Router (modelo e esforço):**
  - ler a apólice: o modelo mais barato que passar na bancada (o Luna é candidato);
  - entender o ajuste: classificação curta;
  - texto ao cliente: só na conversa.
- **Quem Cobra Menos:** a conversa é feita pelo modelo da pessoa e não custa para nós.
- **Pacotes:** se a E20 confirmar, as 2 opções (completa e econômica) saem de 1 cálculo em vez de 2.
- **Ajustes:** 💭 ≈ 1,66 cálculo por renovação hoje (D-MC-14). Com a opção econômica já na proposta, a expectativa é cair (H11, medido na 131).
- **Jev:** só para tela desconhecida ou classificação; fora do caminho principal (P-119-03).
- **Verba:** a bancada do extrator precisa do crédito de API (T-04).
- **Meta:** medir o custo por cálculo e por proposta nas 129-B e 130 e fixar o teto depois.

---

## 9. As fases da negociação

| Fase | O que acontece | Onde | SPEC |
|---|---|---|---|
| P1 | O agente calcula e monta a proposta; o corretor revisa, ajusta (painel ou chat) e envia | AutoBrokers | 131, 132 |
| P2 | O agente envia no WhatsApp oficial, responde, ajusta e, no "quero fechar", confirma e passa ao humano com dossiê | WhatsApp oficial | 134, 135 |
| P3 | O agente transmite a proposta e fecha na seguradora | Portal da seguradora | Depois do programa |

**Regras**
- **Um agente por canal**, com a habilidade "proposta" em dois modos. Criar outro agente seria motor paralelo (CLAUDE.md §5).
- **O agente nunca diz "fechado":** confirma a vontade de fechar e passa a quem fecha.
- **O ajuste mais pedido é o preço** (D-MC-14). As alavancas são comissão (E16), assistência e coberturas; a 128 mede quanto cada uma baixa.
- **A proposta já nasce com a opção econômica** (D-MC-44), para responder à objeção antes que ela apareça.
- **Condições da P2:** atendimento ligado e a D-MC-32.

---

## 10. Pendências e testes

**Triagem da D-FILA-01**
O `PENDENCIAS.md` não tem nota por item (📊 0 ocorrências), e a única lista com nota ≥ 90 é a do painel (9 itens, 20/09).

| Pendência | Situação | Onde drena |
|---|---|---|
| P-PILOTO-10 (94) | resolvida, falta sair da lista | só mover |
| P-E00151-09 (93) | fechada na 001.8 e duplicada | resíduos P-E0018-15 e P-E00110-A5 |
| P-098-MCP (92) | fechada na 001.8 e duplicada | resíduos P-E0018-12/13 |
| P-E00151-04 (92) | aberta: a trava de negação pega 6 de 9 formas | 133-B · 135 |
| processo único (91) | executada; o canário T-39 segue aberto | — |
| 40/81 linhas (90) | resolvida na 001.5.2 | — |
| P-E00151-02 (90) | aberta: cobertura com cliente síncrono sem guarda | 133-B |
| P-096-CHAVE (90) | resolvida, falta sair da lista | 135 |
| P-PILOTO-09 (90) | o Amandus cuida fora do programa (D-MC-35) | — |
| P-E002-HAR 🔴 | gravações com dados de acesso no disco | 128 (fixtures, depois apagar) |
| P-E002-X1 🔴 | InfoCap da Resulta dentro da Amandus, de propósito (D-MC-27) | 131 |
| P-E0018-14 | conhecimento atravessando corretoras | passo 0.5 |

**Das 46 abertas da 126/127,** tocam o programa: P-126-09/13/16/18 e P-127-01/02/03/06/12/17/20/23.

**Mapa dos testes** (julgamento do parecer, com a régua "PODE LIGAR"):
- **Em 03/10:** 101 pendentes; 55 travavam ligar o atendimento (classe A); 0 travavam o programa (classe B); 46 podiam esperar (classe C).
- **Em 04/10:** 📊 95 pendentes e 10 feitos, de T-01 a T-105. O mapa é recontado no registro do canon (passo 0.5), com a T-104 e a T-105.
- **A classe A trava também a 134 e a 135.**
- **A T-04 (crédito de API) pesa a partir da 130.**
- **T-91 e T-99 estão conferidas até `a87b2e7`, sem o `smith-web`:**
  - `portal-worker` e `smith-api` pela digital do código;
  - `smith-worker` rodando, pelo Amandus.
  - O Implantar do passo 0.5 fecha a diferença.
- **O que travava a 128 fora da lista T (bloco H) foi resolvido assim:**
  - H.1 → D-MC-27 (entrada da 131);
  - H.2 → D-MC-23 (autorização da corretora);
  - H.3 e H.4 → D-MC-24;
  - 0.4.b/c/d → D-MC-35.

---

## 11. Caixa do Amandus (o que só você faz, e quando)

| Quando | O quê |
|---|---|
| ✔ 04/10 | Desenvolvimento declarado e nova fila confirmada |
| Antes de colar o prompt de execução | Ver duas variáveis no EasyPanel (serviço smith-api → Environment): `WORK_RUNS_ROUTINE_BRIDGE` e `WORK_WORKER_IN_PROCESS`. Anotar o valor de cada uma, ou "não existe" |
| Depois do passo 0.5 | Implantar os 4 serviços pelo passo a passo do relatório e abrir um link `/r/` numa aba anônima |
| Antes das sessões ao vivo da 128 | Autorização escrita da corretora para o agente concluir cálculos (uma mensagem basta); 3–5 apólices autorizadas; horário em que o login fica livre |
| Antes da 133-A | Criar o serviço e o domínio no EasyPanel; 10–15 pessoas leigas para testar a instalação no próprio celular |
| Durante 129–131 | Iniciar a verificação do negócio na Meta e separar um número novo para o WhatsApp oficial |
| Antes da 130 | Responder ao portão de preço (D-MC-45); aprovar o modelo visual da página do cliente; crédito de API (T-04); 20–30 apólices autorizadas para a bancada |
| Antes da 131 | Devolver a conexão InfoCap da Resulta à Resulta (D-MC-27) |
| Antes da 133-B | Responder ao portão de preço do canal: comissão e desconto com Resulta e AutoFleet (D-MC-29) |
| Antes da 134 e da 135 | Os testes de "ligar o atendimento" (classe A) |
| Quando faltar licença | Decidir a compra de login de robô (o Claude Code avisa) |

---

## 12. Como seguir com o Claude Code

**Prompt C** (revisão da v2.2): feito em 04/10, sem bloqueio. Tudo entrou na v2.3.

**Onde:** um chat novo do Claude Code, na mesma pasta de sempre. A 126/127 terminou no código.

**Prompt de execução** (com este arquivo anexado):

```
Você vai executar o PROGRAMA MULTICÁLCULO do começo ao fim, em linha reta. O Amandus declarou o início do desenvolvimento em 04/10/2026. O plano é o PLANO-MESTRE-MULTICALCULO v2.4 (anexo). Ele vale abaixo do CLAUDE.md e do protocolo v13, e já traz a sua revisão de 04/10 com arquivo:linha.

PASTA: esta mesma pasta. A 126/127 terminou no código; só faltam testes de celular do Amandus. Se ele relatar uma falha da 126/127, conserte antes de seguir.

ANTES DA PRIMEIRA SPEC:
1. Faça o preflight do CLAUDE.md.
2. Grave o plano no repositório, cópia fiel do anexo, em docs/canon/programa-multicalculo/PLANO-MESTRE-MULTICALCULO.md. Daqui em diante, a fonte é essa cópia; todo chat seguinte lê de lá.
3. Registre no canon:
   - as decisões do §2 em FOUNDER-DECISIONS: as de origem "Amandus" ou "por delegação" como tomadas; as de origem "Recomendação" como propostas, que você confirma na SPEC de cada uma quando os fatos sustentarem;
   - a nova fila em EXECUTION-MASTER-PLAN, ESTADO-DAS-SPECS e INDICE-DE-SPECS, com as substituições do §2;
   - o mapa de testes recontado.

SEQUÊNCIA (§0 do plano): 0.5 → 129-A → 128 → 133-A → 129-B → 130-A → 130-B → 131 → 132 → 133-B → ★ → 134 → 135 → 136 → 137.

PARA CADA SPEC, SEM ESPERAR APROVAÇÃO ENTRE ELAS:
a. Escreva a SPEC executável a partir da ficha do §4, no formato do protocolo v13.
b. Antes de executar, um revisor novo e cego compara a SPEC com a ficha e com o código. Conserte o que ele achar.
c. Execute pelo protocolo v13 (juiz e red team), rode a bateria e empurre para a main.
d. Feche com a resposta do CLAUDE.md §12.2 para o Amandus: o que mudou, o passo a passo do Implantar e os testes dele.
e. Siga direto para a próxima SPEC. Só espere o Implantar quando a próxima depender do que está no ar.

SÓ PARE, e diga ao Amandus exatamente o que precisa, quando:
- for uma parada legítima do CLAUDE.md §10;
- chegar a um portão do §0.1 do plano:
  - 128 ao vivo: autorização escrita da corretora, apólices, login livre;
  - 133-A: serviço e domínio no EasyPanel, testadores;
  - 130-A e 133-B: as perguntas de preço, prontas, com os números da 128;
  - 131: a InfoCap da Resulta de volta na Resulta;
  - 134: verificação na Meta;
  - 135: atendimento ligado;
  - licença ou custo novo.
Enquanto um portão espera, avance no que não depende dele. Nunca invente decisão comercial ou de preço.

CONTEXTO: encadeie 2 ou 3 SPECs por chat. Passando de 60% do contexto:
- termine a SPEC em curso;
- atualize o ESTADO-DAS-SPECS;
- entregue ao Amandus o texto exato para abrir o próximo chat nesta mesma pasta, no modelo do §12 do plano.

REGRAS QUE NÃO MUDAM:
- O conhecimento destilado das conversas é global por desenho ("O Atlas é UM SÓ, e é de todas"). O conserto da P-E0018-14 só garante que ele saia anônimo. Nunca ponha company_id na conduct_playbooks.
- Nada de inventar cotação, economia, evento ou disponibilidade. A narração ao vivo só narra eventos reais.
- A marca de consumo se chama Quem Cobra Menos.

VARIÁVEIS DO SMITH-API NO EASYPANEL (para a 129-A; vazio = não existe = desligada):
WORK_RUNS_ROUTINE_BRIDGE = 
WORK_WORKER_IN_PROCESS = 

Comece agora, pelo "ANTES DA PRIMEIRA SPEC".
```

**Modelo do texto para o chat seguinte** (o Claude Code preenche e entrega quando o contexto encher):

```
Continue o PROGRAMA MULTICÁLCULO de onde parou, nesta mesma pasta, em execução contínua.
Leia o CLAUDE.md, docs/canon/programa-multicalculo/PLANO-MESTRE-MULTICALCULO.md e o ESTADO-DAS-SPECS.
Última SPEC concluída: [...]. Próxima: [...]. Portões esperando o Amandus: [...].
Siga o §0.1 do plano: SPEC atrás de SPEC, parando só nos portões e nas paradas do CLAUDE.md §10.
```

**Volta à concepção:** opcional, uma vez, com o primeiro relatório completo (o da 129-A), para conferir o alinhamento. Depois, só em dúvida. O Claude Code não espera essa volta para seguir.

## 13. Riscos e planos B

| Risco | Plano B |
|---|---|
| O Agger bloqueia o uso automatizado (risco aceito na D-MC-23) | Login de robô identificado e com tetos; outro adaptador na mesma porta (a pesquisa de APIs segue); o segundo multicálculo sobe na fila |
| Dependência do fornecedor: o Agger tem permissões de envio e fechamento e é dono da InfoCap — pode virar concorrente | Dados e regras no AutoBrokers; porta neutra; segundo multicálculo e fonte de carteira alternativa no radar |
| A seguradora restringe a corretora por muita cotação sem emissão | Teto por seguradora por dia como condição de pronto (133-B); acompanhar a taxa de conversão com a parceira |
| O Quem Cobra Menos vira consulta de CPF alheio | Convite, limites por HMAC, lista branca na saída (§6.3) |
| Leigos não conseguem instalar | 133-A mede cedo; diretório do Claude e WhatsApp como saídas |
| ChatGPT pessoal sem MCP no celular | Claude primeiro; ChatGPT pelo diretório, no modo conta |
| E3 (seguro novo) difícil | Renovação segue pela InfoCap; a cotação nova espera a solução |
| Um cálculo de 7 min trava cobrança e vidros | Fila e navegador próprios para o cálculo (D-MC-42) |
| Dois chats mexendo na mesma pasta | Um chat mexe no código de cada vez. A 126/127 terminou no código; falha de teste dela vai para o chat do programa |
| Consertar a espera ressuscita trabalhos velhos (acionamentos de dias atrás) | Inventário por tipo antes de tudo; volta só o que nasceu pela fila e tem executor; o velho expira sem rodar |
| A Meta demora a verificar | Começar a verificação durante 129–131; a ★ não trava a 134 |
| Falta licença para robô | Compra decidida pelo Amandus; nunca o login de uma pessoa |

---

## 14. Fontes

**Repositório** (`main` `a87b2e7` em 03/10; `e7f76df` em 04/10):
- Revisão do Claude Code da v2.2 (04/10), com arquivo:linha: `middleware.ts:111-113`, `app/r/[token]/route.ts:37-50`, `runs.py:393-415`, `dispatch_router.py:388-390`, `smith_worker.py:366-369`, `main.py:398-410`, `attendance_distiller.py:1178`, `MIGRATIONS-AUTHORITY.md:162`, `worker.py:1716-1725`, `journeys/__init__.py:352-369`, `requirements.txt:56`.
- `CLAUDE.md`, `docs/canon/FOUNDER-DECISIONS.md`, `PENDENCIAS.md`, `TAREFAS-DO-FOUNDER.md`, `EXECUTION-MASTER-PLAN.md`.
- Relatórios da 126, da 127 e da investigação EXTRA-002; propostas EXTRA-002/003/004/007; SPEC-119 (Jev).
- Conferidos por mim em 03/10: `middleware.ts` (rotas públicas), `app/r/[token]/route.ts`, `backend/app/agents/tools/report_tool.py:296`, `backend/app/services/work/runs.py:35/199/272`, `backend/app/services/portals/gateway.py` (`ESPERA_MAXIMA_S`), `backend/portal_worker/worker.py:1205-1214`, migration `20260727_06_coerencia_company_kind.sql`.
- Parecer de validação do Claude Code sobre a v2.1 (03/10), com arquivo:linha dos demais itens.
- No ar, em 03/10: `/health` do `portal-worker` e do `smith-api`; `GET /r/<token falso>` → `/login`.

**OpenAI e ChatGPT:**
- Developer mode e MCP apps (atualizado em 03/10): https://help.openai.com/en/articles/12584461-developer-mode-and-mcp-apps-in-chatgpt
- Plugins in ChatGPT: https://help.openai.com/en/articles/20001256-plugins-in-chatgpt
- Hospedar plugin no ChatGPT Sites: https://help.openai.com/en/articles/20001547-hosting-a-plugin-with-chatgpt-sites
- Fim do modo desenvolvedor separado (equipe da OpenAI, 01–02/10): https://community.openai.com/t/developer-mode-missing-and-mcp-app-creation-unavailable-across-multiple-chatgpt-accounts/1402294
- Regras do diretório: https://developers.openai.com/plugins/plugin-guidelines

**Anthropic e Claude:**
- Conectores personalizados: https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp
- Conectores (diretório, celular): https://support.claude.com/en/articles/11176164-use-connectors-to-extend-claude-s-capabilities
- Conector no app de celular (terceiros): https://docs.ahrefs.com/mcp/docs/claude-mobile
- Política do diretório: https://support.claude.com/en/articles/13145358-anthropic-software-directory-policy
- Pedido pré-preenchido por link (`claude.ai/new?q=`): https://www.oasis.security/blog/claude-ai-prompt-injection-data-exfiltration-vulnerability

**Regulação:**
- LGPD: https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709compilado.htm
- CDC: https://www.planalto.gov.br/ccivil_03/leis/l8078compilado.htm
- Res. CNSP 382/2020 (remuneração antes da aquisição, texto original): https://www.segs.com.br/seguros/220620-idecorr-esclarece-as-duvidas-dos-corretores-de-seguros-sobre-a-resolucao-cnsp-382-2020
