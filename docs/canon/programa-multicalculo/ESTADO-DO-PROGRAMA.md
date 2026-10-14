# Estado do Programa Multicálculo — o que está feito, o que espera, o que se gastou

> Arquivo vivo. Todo chat do programa lê este arquivo junto com a [PASSAGEM de 05/10](PASSAGEM-2026-10-05-WHATSAPP-PLANO-A.md) e o
> [plano](PLANO-MESTRE-MULTICALCULO.md) (v2.5.1) e o atualiza ao fechar cada SPEC. Decisões em
> [`FOUNDER-DECISIONS.md`](../FOUNDER-DECISIONS.md) (D-MC-08…74 · D-130A-06…11 · D-130A1-01…16 · D-133A-13…16 · D-133A1-01…07 · D-129C-01…09 · D-131-0-03…35 · D-1311-01…06 · D-130B-01…17 · D-131-01…28 · D-131-29…39 · D-131-40…52 · D-132A-01…08 · D-132B-00…10 · D-B4-01 · D-132C-01…05 · D-132-E1 · D-132-G1…G3; as D-133A-01…12 estão na [SPEC-133-A](../specs/SPEC-133-A-quem-cobra-menos-no-whatsapp.md) §2).

## 1. O checklist (§0.1 do plano, v2.5.1 — a fila INTERCALADA de 05/10 tarde, D-MC-61, com a 129-C da D-MC-73)

Duas linhas que andam juntas: **QCM** = Quem Cobra Menos (leads novos para as corretoras) · **AUX** = Auxiliares de Renovação e de
Cotação (o dia a dia da corretora, no chat principal) · **base** = serve às duas. A **134 flutua**: entra assim que a Meta aprovar, a
qualquer momento depois da 133-A. **A 129-C (mais ramos do Agger) entra logo depois da 133-A e antes da 130-B/131 (D-MC-73, 06/10).** Se o
portão da 131 abrir antes do da 130-B, a 131 sobe para logo depois da 129-C; a 132 exige a 130-B.
**A fila em vigor — D-1311-02 ✅ TOMADA pelo Founder em 11/10, com ajuste** (o [mapa de possibilidades](131-0/MAPA-DE-POSSIBILIDADES-INFOCAP-AGGER-SEGURADORAS.md)):
✔ 133-A.1 → ✔ 129-C → ✔ 131-0 parte A → ✔ **130-B ficha única** → ✔ **131-A a madrugada** → ✔ **131-B o aplicativo de Renovação** (13/10, `main` `1247e44`) → ✔ **132 o chat e a Cotação
Rápida** (132-A o chat · 132-B a Cotação Rápida · 132-C o WhatsApp do corretor = a 131-0 parte B1; 14/10; a 130-C, a página dos outros ramos, NÃO entrou —
segue com a D-129C-08) → ⏭ **PRÓXIMA: "A loja de aplicativos" (8.1) ·
vida e moto (8.2, anotadas 12/10)** → 133-B → 135 (+ B2, o WhatsApp pareado) → **Emissão e registro** → **Endosso assistido** → … →
**cobrança estável, com o religar em teste (FIM da fila)**. O ajuste do Founder: a cobrança não é pré-requisito de renovação nem de cotação,
então vai para o fim; o **financeiro por planilha** fica ADIADO ("outra ocasião"). A 130-B mudou de escopo — de "leitor da cotação" para **a
ficha única da apólice do produto** (D-1311-01; a mudança foi ACEITA pelo Founder em 11/10, CHANGE-ADDENDA).
🔴 **O que a 131-0 parte A mudou na 130-B e na 131 (BLOCO 0, 11/10):** a InfoCap da Resulta TEM RE (D-131-0-26) — a 131 lê da InfoCap da
corretora QUEM renova (o dono: produtor `indireto="F"` do `/prod_docs`, D-131-0-03) e QUANDO (`/renovacoes`; 📊 99 apólices em 30 dias
na Resulta, 217 na AutoFleet); e o PDF da apólice vem do próprio CORP por `/documento_anexos` (📊 77 de 99 renovações com o arquivo;
RESI/EMPR/COND completos) — a 130-B (leitor de apólice) passa a ter esse PDF como entrada da renovação, além das apólices enviadas.

| # | Passo | Linha | Estado | Branch / commit | Portão | Marco |
|---|---|---|---|---|---|---|
| 0 | Fechar a 126/127 | — | código pronto; testes de celular do Founder | `main` `e7f76df` | — | — |
| 0.5 | Registro + `/r/` + P-E0018-14 | — | ✅ CONCLUÍDO e NO AR 04/10 (Founder implantou; `/r/` falso em aba anônima → "Este link não está mais disponível") (juiz 84 · red team 62 → conserto → confirmação 80 → conserto com prova mecânica) | `programa-mc/passo-0.5` → `main` | 🧑 Implantar + abrir um `/r/` em aba anônima | — |
| 1 | 129-A espera durável | base | ✅ CONCLUÍDA 04/10 (juiz 78 · red team 62 → conserto → confirmação 89; migrations _01 e _02 APLICADAS; _03 na caixa do Founder) — inventário já medido: ver relatório do 0.5 §1 | — | — | — |
| 2 | 128 prova do Agger | base | ✅ CONCLUÍDA 04/10 (juiz 72 ‖ red team 62 → conserto → confirmação; lente 84; 📊 16 cálculos de 25; nada apagado no Agger nem na InfoCap) — resultado em [`A-PROVA-DO-AGGER.md`](A-PROVA-DO-AGGER.md) · `reports/SPEC-128-EXECUTION-REPORT.md` · D-128-01…08 · P-128-01…14 | `spec/128-a-prova-do-agger` (código até `9db6372`) | ✅ autorização da corretora declarada (04/10) · ✅ D-128-03 TOMADA 05/10 · 🧑 os 3 negócios de teste | — |
| 3 | 129-B motor (várias corretoras em paralelo, D-MC-56; padrão + econômica juntas, D-MC-60; medir a hipótese do CPF em 2 corretoras) | base | ✅ **CONCLUÍDA 05/10** (juiz 80 ‖ red team 62 → conserto → confirmação 85; nota 86; canário AO VIVO 📊 5/5 cálculos fechados, 104 ofertas, retomada +0 `calcularV2`, 0 senha nas 5 tabelas; migration `20261005_01` APLICADA; o motor nasce DESLIGADO) — `reports/SPEC-129-B-EXECUTION-REPORT.md` · D-129B-01…11 · P-129B-01…13 | `spec/129-B-o-motor` | ✅ D-128-03 · ✅ portão de preço respondido (D-MC-62…65) · 🧑 Implantar + 1 usuário de robô por corretora (T-120) + `MULTICALCULO_HMAC_KEY` | — |
| 4 | 130-A comparação (entre seguradoras e entre corretoras), proposta e página "uau" | base | ✅ **CONCLUÍDA 06/10** no código (revisor cego da SPEC 68 → v1.1 · juiz 80 (3 blockers) ‖ red team 74 QUEBREI (1 blocker) · crítico final de design 91 · conserto único: 4 blockers + pendências, 21 guardas sobre o HTML servido, 219 testes verdes; migrations `20261006_01/_02/_03` APLICADAS) — igual-com-igual por opção (só compreensiva casco 100 % anual; produto diferente e assinatura à parte), vencedora entre corretoras, 3 opções por situação (D-MC-66/69, D-130A-09), nota 0–100 com motivos, validade (padrão 5 dias da config), mensagem ≤ 2 opções + link (D-MC-74), a página "carteira" (D-130A-11) como artefato `proposal.quote` servido pelo `/r/`, prévia PNG 1200×630, abertura e clique "Quero fechar" medidos, `ordem_do_mais_barato` e `cotacao_alvo` na porta, `multicalculo_config` por corretora, a completa+ no motor. Canário real: pedido `d0bb15ba` publicado na produção (📊 16 seguradoras · 13 completas · 1 só produto diferente · 2 sem resposta) — `reports/SPEC-130-A-EXECUTION-REPORT.md` · P-130A-01…20 | `spec/130-A-a-proposta` (base `5952324`) | ✅ portão de preço (D-MC-62…65) · ✅ D-MC-66…74 · ✅ modelo visual (D-130A-11) · 🧑 **sobram:** Implantar os 3 serviços (T-124) · WhatsApp de atendimento + nº SUSEP no cadastro de marca e a marca da AutoFleet (T-125; sem o WhatsApp, publicar RECUSA) · abrir o link do canário no celular (T-126) · ~~jurídico da remuneração (T-127)~~ cancelada 06/10 (D-130A-08 revogada) · T-124 ✅ feita | — |
| 4.1 | 130-A.1 Quem Cobra Menos: a mensagem, o mínimo do mínimo e a margem corrigida | QCM | ✅ **CONCLUÍDA 07/10** (juiz 82 ‖ red team 70 QUEBREI — 3 blockers: volume contava recálculo, a mínima dizia "menos dias" no WhatsApp, selo renomeável; conserto único + confirmação; migration `20261006_04` APLICADA) — a mensagem do canal (volume REAL 📊 82 no canário, tempo, economia com a origem da conta, vencedor com o parcelado, 2 cartões, 6 por seguradora, a corretora em lista, a pergunta final), o 4º cálculo `minima` (sem carro reserva), a margem até 10 % sozinho passo a passo com a alavanca de fechamento em R$, o manual por contexto, a remuneração CNSP fora — `reports/SPEC-130-A1-EXECUTION-REPORT.md` · P-130A1-01…06 | `spec/130-A1-quem-cobra-menos` (base `705b67f`) | 🧑 Implantar (T-129) · a lista do Nível 5 (T-130) · testadores, verba e robô (T-131) | — |
| 5 | 133-A Quem Cobra Menos no WhatsApp, piloto fechado (Evolution) | QCM | ✅ **CONCLUÍDA 07/10** no código, nota 88 (juiz 74 ‖ red team 68 QUEBREI — 3 blockers: mídia/apólice tomada como resposta e CPF ao modelo, a conversa presa em "calculando", e na confirmação "não quero mais" no meio da frase apagava a conversa; conserto único → confirmação 84 → 88; migrations `20261007_01/_02` APLICADAS) — o desvio do canal no webhook do Evolution GO antes do observer (só números convidados, limite por dia, anti-laço com linha/agente de corretora, fromMe, grupo e teto de mensagens), a conversa com consentimento e 11 perguntas uma por vez ("quanto você paga hoje?"), a placa supre FIPE/ano/combustível, o pedido ao motor (Work Run `canal.cotacao`), a página da marca QCM com a corretora vencedora dentro, a mensagem na copy do Founder (D-130A1-15, `canal.volume.base` = 100 é configuração), até 2 lembretes de segunda a sábado (D-133A-15), a passagem com evento + card no Inbox do operador (D-133A-16), o QR no portal admin (Conexões → Canais); a marca da AutoFleet publicada (logo, 2011 — D-130A1-16). 📊 O FIO: `test_spec133a_o_fio.py` 17 casos (o caminho feliz + 4 controles com ZERO envio pelo webhook real); bateria 2 metades: 0 regressão de produto — `reports/SPEC-133-A-EXECUTION-REPORT.md` · D-133A-01…16 · P-133A-01…08 · prévia visual https://claude.ai/artifact/Js8TDvChAtdxhQiuVFidwZ | `spec/133-A-qcm-whatsapp` (base `de66449`) | 🧑 **sobram:** Implantar (T-132) · ler o QR do número no portal admin (T-133) · cadastrar os convidados (T-134) · o login do Agger do robô (T-135 — hoje as duas contas estão pausadas e sem senha: nenhuma cotação do canal sai) | — (as rodadas dos testadores correm no calendário enquanto se constroem a 129-C, a 131 e a 132) |
| 5.1 | 133-A.1 Quem Cobra Menos: os ajustes do Founder, o Agger da corretora pela tela e o plano das contas | QCM | ✅ **CONCLUÍDA 10/10** (10/10 requisitos), nota 88 (ALTO; 5 builders em paralelo · juiz 88 ‖ red team 84, sem blocker → conserto curto com teste e mutação; nenhuma migration) — as opções do QCM lado a lado em carrossel, cada cartão na ordem menor parcela → à vista → maior sem juros, a menor parcela de TODAS as formas de pagamento (📊 a Youse só traz 4x, D-133A1-07); "homem ou mulher?" só para nome ambíguo (📊 tabela do IBGE, 630 nomes; ≥ 70 % de um sexo não pergunta, D-133A1-02); o card "Agger da corretora" no painel (a conta GLOBAL do robô, um serviço só para a tela e o comando, um login nunca em duas contas — revê a D-129B-11, D-133A1-03/04); a tela de conexões abre a conexão existente; as contas `cotador@` medidas (A-PROVA §11: AutoFleet 15 seguradoras válidas; Resulta com HDI/Mitsui/Tokio pendentes); a senha provisória "mudar123" fora do produto (📊 4 de 7 membros ainda com ela); o plano da [SPEC-131-0](../specs-propostas/SPEC-131-0-CONTAS-COMERCIAIS-E-CONEXOES.md) e o mapa das [situações de entrada](SITUACOES-DE-ENTRADA-DA-COTACAO.md) (16 situações). 📊 bateria 2 metades: 0 regressão — `reports/SPEC-133-A1-EXECUTION-REPORT.md` · D-133A1-01…07 | `spec/133-A1-qcm-ajustes` (base `9928ad3`) → `main` `0860d31` | 🧑 **o que é seu, na ordem:** T-137 trocar as senhas "mudar123" (hoje) · T-132 Implantar com os valores das variáveis · T-133 ler o QR · T-134 cadastrar os convidados · T-135 o Agger de cada corretora pela tela · T-136 corrigir a conta da Resulta no Agger | — |
| 5.5 | 129-C mais ramos do Agger (Condomínio, Empresarial e Residencial primeiro; o mesmo motor e montador da 129-B, um pedido e um preset por ramo — nunca motor novo) | base | ✅ **CONCLUÍDA 11/10**, nota 88 (🔴 CRÍTICO; juiz 76 ‖ red team 62 → conserto portal ‖ app → confirmação 88; migration `20261011_01` APLICADA) — o MESMO motor da 129-B calcula Condomínio (16), Residencial (2) e Empresarial (18): o pedido de RE pelo contrato, as opções de RE (a básica vem do pedido), o corpo de RE (coberturas em `configuracoes`, a comissão explícita no item), a atividade do empresarial por seguradora (sem atividade compatível → sai listada, nunca um código errado), o leitor e a comparação de RE, a config por ramo (preferência de seguradoras, reajuste da renovação, comissão); o Agger da corretora SEMPRE ligado (F0). 📊 **canário AO VIVO 11/10 nos 3 ramos** (conta cotador@ da Resulta, 3 `calcularV2`, HTTP 201 nos 3, 1 login e 1 logout): condomínio 3/7 com preço (Allianz R$ 8.408,79) · residencial 3/8 (Tokio R$ 490,25) · empresarial 1/1 (Allianz R$ 2.072,76; 9 seguradoras sem atividade compatível) · ~47 s do envio ao último preço · 0 erro de contrato do Agger. 📊 bateria 2 metades: 0 regressão de produto — `reports/SPEC-129-C-EXECUTION-REPORT.md` · [`129-C/CANARIO-AO-VIVO.md`](129-C/CANARIO-AO-VIVO.md) · D-129C-01…09 · P-129C-01…06 | `spec/129-C-mais-ramos` (base `8d468b4`) → `main` `c3a7495` | 🧑 **o que é seu:** seguir o [`ROTEIRO-DE-VALIDACAO-DO-FOUNDER.md`](ROTEIRO-DE-VALIDACAO-DO-FOUNDER.md) (T-138: 17 passos em 5 blocos — Implantar, Agger com as credenciais de RE (P-129C-04: Porto/Mapfre/HDI recusam por credencial), o número do QCM, o seu teste, os 4 testadores) · ~~onde está a carteira patrimonial da Resulta (P-129C-02)~~ ✅ FECHADA 11/10: na InfoCap, banco da Resulta (BLOCO 0 da 131-0) · o reajuste 15 × 10 % (P-129C-03) | — |
| 5.6 | 131-0 parte A — as contas da corretora (membros, vínculo com o produtor da InfoCap, contas do Agger com dono, qual Agger usar, manual por serviço) | base | ✅ **CONCLUÍDA 11/10** (🔴 CRÍTICO; 4 builders em PARALELO F1‖F2‖F3‖F4 + costura F5 · juiz 87 ‖ red team 74 (2 blockers latentes: login de pessoa sem desfecho insistia; o canal podia pedir cotação/renovação no Agger de uma pessoa) → conserto único (8 itens) → confirmação; **nota: ver relatório**; migrations `20261011_02/_03/_04` APLICADAS) — funções de cada pessoa e papel de acesso fechado com uma fonte só; o vínculo produtor da InfoCap ↔ pessoa e a regra do dono como DADO; o Agger de cada pessoa (`uso='membro'`) ao lado do da corretora, com logout sempre e sem nunca cair calado na global; `qual_agger.decidir` único e auditado; o manual por serviço (QCM · Cotação · Renovação) e a tela Serviços com os 4 passos. 📊 régua do dono pelo código do produto (`dono.medir_regra`): Resulta 99/99 (mutada para `ordem 1` → 37/99). 🔴 BLOCO 0: a conexão "InfoCap RESULTA" da Amandus tinha o login da AutoFleet → a InfoCap da Resulta TEM RE (D-131-0-26); a conexão foi renomeada "InfoCap AUTOFLEET" (D-131-0-27) — [`131-0/BLOCO0-INFOCAP-A-CONEXAO-TROCADA.md`](131-0/BLOCO0-INFOCAP-A-CONEXAO-TROCADA.md) · `reports/SPEC-131-0-A-EXECUTION-REPORT.md` · D-131-0-03…35 · P-1310-01…13 | `spec/131-0-A-contas` (base `7aa15ce`; `69ba085`…`786238b`) → `main`: ver o push no relatório | 🧑 **o que é seu:** T-139 (Implantar os 4 serviços) · T-140 (funções e quem é quem) · T-141 (o Agger de cada comercial, com o aceite dela) · T-142 (Serviços) · T-143 (a InfoCap da Amandus é a da AutoFleet) · T-144 (a InfoCap em cada corretora real) | — |
| 6 | 130-B **a ficha única da apólice** (D-1311-01: o motor do leitor que já existe, para atendimento, chat, renovação, cotação e QCM) | base | ✅ **CONCLUÍDA 12/10** (juiz 84 (1 blocker: o juiz conferia só a soma) ‖ red team 58 QUEBREI (4 blockers: só a soma · erro passageiro do modelo virava leitura final · laudo/BO/orçamento classificados como apólice · "leitura em andamento" sem nada rodando) → conserto único (4 blockers + 8 pendências; 40 testes novos, 38 vermelhos no código antigo; 26 mutações vermelhas) → confirmação 80 (1 defeito novo na regra das 2 linhas + o limite da visão → consertados com teste e mutação; régua das 7 afetadas idêntica); bateria 2 metades: 0 regressão em aberto (2 consertadas); **nota 87**; migration `20261011_05` APLICADA 11/10, VERIFY 1–3 ok) — UM leitor de documento de seguro, DENTRO do `policy_document_evidence_service` (sem motor paralelo): páginas tolerantes (PyPDF2 por página, PyMuPDF só onde falha) → regex → JUIZ (Σ prêmio das linhas = prêmio líquido, max(R$ 0,05; 0,5 %), conferido linha a linha) → modelo barato (papel novo `leitura_de_apolice`, Luna medium, texto MASCARADO, trecho literal de uma linha) → juiz → visão (só página sem texto) → juiz → estado da leitura; a leitura guardada por hash + `LEITOR_VERSAO` 130B.2 (ficha no MinIO + resumo em `documents.metadata.leitura`); o modelo com orçamento de 20 s e 2º plano com trava Redis; erro passageiro tenta de novo (até 3×, 10 min). Fontes: `url_apolice` → `/documento_anexos`; o prêmio líquido do CORP vai ao juiz; `/itens?data=` = hoje, presa na vigência. O anexo do WhatsApp e do chat passa pelo mesmo leitor (ao segurado só a ficha mascarada; ao corretor a ficha + o texto mascarado; laudo/BO/orçamento seguem como texto mascarado). `reconciliar` acende `documento_nao_conferido` e o atendimento não afirma lista completa; `capacidades().documento_oficial` = SUPORTADA; a renovação (`de_apolice`) monta o pedido de AUTO e de RE pela ficha — ninguém a chama ainda (a 131 liga). 📊 **régua** (código do produto, bytes reais das 32 apólices de 11/10, `backend/scripts/regua_ficha_da_apolice.py`, resultados sem PII `RESULTADOS/ficha_da_apolice_20261011.json` e `_20261012.json`): ANTES 11/32 → **24/28 com PDF** (RESI 7/7 · COND 6/8 · EMPR 5/7 · AUTO 6/6); as 11 de controle intactas pelo regex, custo 0; 0 pipeline caído (Sura e Yelum leem); a Porto escaneada lida pela visão (16 páginas, ao centavo); 4/32 sem PDF na fonte. ⚠️ a meta de COND (≥ 7/8) ficou em 6/8: a tabela da Tokio quebrada em duas linhas pelo PyPDF2 (P-130B-01) — `reports/SPEC-130-B-EXECUTION-REPORT.md` · laudos `SPEC-130-B-LAUDO-DO-JUIZ.md` e `…-LAUDO-DO-RED-TEAM.md` · D-130B-01…17 · P-130B-01…14 · P-LEITOR-01…04 FECHADAS | `spec/130-B-a-ficha-unica` (base `4bfd562`) → `main`: ver o push no relatório | ✅ bancada das 32 · verba 📊 US$ 0,0983 de US$ 1,50 · 🧑 **o que é seu:** T-154 Implantar `smith-api` → `smith-worker` (📊 `git diff 4bfd562..HEAD --stat`: os 25 arquivos de código estão em `backend/`; `frontend/` e `portal_worker/` sem mudança — o `smith-web` e o `portal-worker` não precisam; o `smith-web` já foi implantado em 11/10 com o `/api/versao` conferido) · T-155 dizer se apaga as pastas velhas `app/app/` e `app/backend/` (P-130B-14) | — |
| 7 | 131-A **a madrugada da renovação** | AUX | ✅ **CONCLUÍDA 13/10**, nota 86 (🔴 CRÍTICO; 6 fatias F1‖F2‖F3 → F4 costura → F5 perfil → F6 combustível · juiz 72 (3 blockers: InfoCap fora virava `falta_dado` e o dia "completo"; moto calculada como carro e de volta toda noite; licença nunca gravada) ‖ red team 78 QUEBREI (1 blocker: o desvio das 06:15 recalculava o que já tinha saído no Agger do dono) → conserto C1‖C2 → confirmação **86** (4/4 fechados; N1–N3 consertados); bateria 2 metades: 1 regressão (o guarda dos mil linhas) consertada com paginação; migration `20261013_01` APLICADA, versão `20261013003843`) — a tabela `renovacoes` com a máquina inteira e os eventos; 00:30 a lista congelada (antecipa até 7 dias, teto 12 por conta por noite, D-131-33) · 02:00 os cálculos (prioridade 7, teto de sessões, a sessão da pessoa mantida, ausência/substituto, Prosseguir com 7 travas só no id do aviso, D-131-34) · 05:30 a conferência INDEPENDENTE sobre leitura nova da InfoCap (fica vermelha; `sem_conexao` não conta, D-131-37) · 06:15 o desvio · 06:45 o aviso pelo canal do briefing; o perfil do segurado da InfoCap (suposições marcadas) e os 7 códigos de combustível; ramo desconhecido/moto/frota/RCF-V nunca viram carro (D-131-38); as 3 opções pela ficha (D-131-39); CPF/CNPJ inválido barrado em todo chamador. 📊 **canário real 13/10** (corretora de origem, conta do robô, relógio injetado): **2 renovações AUTO `calculada`** (16/15 e 21/22 ofertas), 1 moto → não cotada, 1 sigla desconhecida → pendente; 0 órfão, 0 linha em outra corretora, nada enviado. 📊 0 corretoras com o aplicativo instalado: nada roda até a 131-B — `reports/SPEC-131-A-EXECUTION-REPORT.md` · laudos [`131/`](131/) JUIZ · RED-TEAM · CONFIRMACAO · D-131-29…39 · P-131A-01…16 | `spec/131-A-a-madrugada` (base `2cd6168`) → `main` `e58db51` (push `2cd6168..e58db51`) | 🧑 T-159 licenças do Agger (⚠️ Resulta 13/10, AutoFleet 20/10) · T-160 Implantar `smith-api`+`smith-worker`+`portal-worker` JUNTOS depois da 131-B · T-156 o aceite do Prosseguir · T-161 as 8 linhas de ensaio · T-162 a conta do BLOCO 0 · T-144/T-140 (sem elas, tudo no Agger da corretora, com aviso) | — |
| 7.1 | 131-B **o aplicativo de Renovação** | AUX | ✅ **CONCLUÍDA 13/10**, nota **89** (🔴 CRÍTICO; G1‖G2‖G3‖G4 → G5 costura · juiz 84 (1 blocker: o CPF da busca na URL e no log de acesso) ‖ red team 72 QUEBREI (3 blockers: o envio reaproveitava a página com o WhatsApp de quem saiu; "Copiar" copiava o texto curto; o telefone saía de `contatos[]`) ‖ juiz de design 82 → conserto K1‖K2 → **confirmação 90** (4/4 fechados, 📊 9 testes vermelhos com o conserto revertido) → design 87 com capturas → K3 → **design final 91** (página do cliente 93); bateria 3 partes: 1 regressão (a ordem das seções) consertada em `173f469`; migration `20261014_01_spec131b_catalogo` APLICADA, versão 📊 `20261013113534`; §9.1 completo: `next build` + `next start` + 7 requisições, 0 erro) — a loja na galeria que existe (capa gerada + 19 ícones lucide, prova só com número real, D-131-40/41); a casca de TODO aplicativo (Início · Configurar · trabalho · Dúvidas, "Como começar" com "N de M prontos", D-131-51); a Renovação: Configurar (Personalização → Serviços redireciona, D-131-06/46; "com qual conta" de verdade, D-131-47), a aba Renovações (lista e quadro, Minhas · Todas, busca por cabeçalho, D-131-49), Meu perfil (o SEU Agger, Meu WhatsApp de trabalho, Ausência, D-131-43), Equipe com a situação de cada um; a página de RENOVAÇÃO (D-131-42/44/50) — 📊 cotação e canal idênticos byte a byte (5/5); o envio por `wa.me` no aparelho de quem clica, telefone buscado na hora e nunca gravado; ligar exige `confirmar_ligar` (D-131-52). 📊 0 corretoras com o aplicativo ligado: nada roda até a T-163 — `reports/SPEC-131-B-EXECUTION-REPORT.md` · laudos [`131/`](131/) JUIZ · RED-TEAM · CONFIRMACAO · JUIZ-DE-DESIGN (×3) · D-131-40…52 · P-131B-01…15 | `spec/131-B-o-aplicativo` (base `e58db51`) → `main` `1247e44` (push `7d41c1f..1247e44`) | 🧑 T-160 Implantar os **4** JUNTOS (`smith-api` → `smith-worker` → `portal-worker` → `smith-web`) · T-161 as 8 linhas de ensaio (a aba não filtra `canario`) · T-157 cada comercial no Meu perfil · **T-163 LIGAR** numa corretora (= a madrugada calcula) · T-165 quem vê "Todas" · T-164 as capas (opcional) · e o "⓪ para LIGAR" (T-144 · T-140 · T-156 · T-122 · T-159 · T-125) | 🚀1 renovação no ar (falta Implantar + Ligar) |
| 8 · A | 132-A **o chat principal** (a caixa que cabe no celular, lê o que se manda e responde rápido) | AUX | ✅ **CONCLUÍDA 14/10**, nota 💭 **84** (proposta do atualizador; 🔴 CRÍTICO; A1‖A2‖A3 → A4 costura → A5 · juiz 88 (0 blocker) ‖ red team 62 QUEBREI (2 blockers: a célula da planilha cortada ANTES da máscara deixava 9–10 dígitos do CPF; um CSV/xlsx/PNG "bomba" de 1 MB derrubava o backend de todas as corretoras) + 2 promovidos pelo gerente (o mesmo pedido 2× chamava o modelo 2× — 📊 6/6 × base 1×; o aquecimento com `SystemExit`) → conserto único → **confirmação 86** (4/4, nenhum defeito novo); nenhuma migration; buckets 20 MB/25 tipos e o modelo pt do spaCy na imagem (D-132-G2/G3); §9.1 completo no HEAD `bdfdfd0`: `next build` 331 rotas + `next start` + 401/307, 0 erro) — o composer novo ("+" com Câmera · Fotos · Arquivos · Esforço · Pesquisa na web, áudio, Copiar, foco, sem a barra do rodapé, `viewport` que não dança, D-132A-01…03/07); os anexos lidos por BYTES e mascarados (foto, PDF da 130-B, planilha, Word, áudio; 10 × 20 MB, HEIC; o path de outra corretora → 403, D-132A-05); o turno rápido (stream imediato, pré-trabalho dentro do stream, contexto em paralelo, aquecimento, `fases_ms`; Rápido/Equilibrado/Máximo no MESMO modelo, D-132A-04/08); o áudio pelo mesmo stream (D-132A-06); a resposta que chega depois por consulta de 6 s (D-132B-09). 📊 BLOCO 0 em produção: 1º delta **10,2 s** (conversa nova) · 7,1 s (2ª msg) — o DEPOIS espera o Implantar (o ELO). ⚠️ juiz de design NÃO rodou — `reports/SPEC-132-A-EXECUTION-REPORT.md` · laudos [`132/`](132/) JUIZ · RED-TEAM · CONFIRMACAO · D-132A-01…08 · P-132A-01…14 | `spec/132-o-chat-e-a-cotacao` (base `285cadc`) → `main`: ver o push no relatório | 🧑 T-166 Implantar os 4 JUNTOS (o `smith-api` reconstrói a imagem) · T-168 testar o chat · T-173 "meça a latência" | — |
| 8 · B | 132-B **a Cotação Rápida** (pedir no chat, receber a cotação e o link de VENDA com a cara da corretora; absorve a EXTRA-004) | AUX | ✅ **CONCLUÍDA 14/10**, nota 💭 **82** (proposta do atualizador; 🔴 CRÍTICO; B1‖B2‖B3 → B4 costura (9 defeitos de costura) → E exemplos · juiz 70 (4 blockers: o recálculo com a tabela e o link ANTIGOS; "economia" sem apólice; o CPF de OUTRO cliente da conversa; o disparo sem o "sim") ‖ red team 62 QUEBREI (3: o prêmio "4200.00" lido como 420.000; o recálculo; o link de quem saiu e o vencido na aba) → conserto único dos 6 → **confirmação 82** (6/6 + 1 defeito novo: o "sim" por áudio nunca confirmava → consertado em `ce32e89`, 📊 43 passed); migrations `20261014_02` (versão 📊 `20261014075627`) e `_04` (📊 `20261014093346`) APLICADAS — ⚠️ o ROLLBACK escrito na `_04` está errado, o correto no MANIFEST) — três ferramentas no agente CORE pela capability `tenant.multicalculo.cotacao` (preparar → o "sim" FALADO pelo corretor → disparar → ajustar), o `confirmacao_id` de uso único (D-132B-03), o Work Run `cotacao.chat` que responde NA MESMA conversa (D-132B-04), a placa e a apólice suprem o pedido; a página de VENDA (template único com a marca, bloco sem dado some, economia só com a apólice LIDA, D-132B-01/02) — 📊 carteira, renovação e canal idênticos byte a byte; o aplicativo "Cotação Rápida" (abas, Cotações, regras do cálculo, API com `company_id`) e "Renovação Automática" (D-132B-06/07); a comissão de entrada só em RE (D-132B-10); o link vai ao CORRETOR (D-132B-05); 3 exemplos publicados com a faixa (D-132B-08/D-132-E1; 📊 404 em produção até o Implantar). ⚠️ canário REAL e juiz de design da página NÃO rodaram — `reports/SPEC-132-B-EXECUTION-REPORT.md` · D-132B-00…10 · D-B4-01 · P-132B-01…15 | idem | 🧑 T-166 · T-167 os 3 exemplos · T-169 uma Cotação Rápida real · T-170 o SEU Agger · **T-172** a capability vale para toda corretora com agente central (hoje sim)? | 🚀2 cotação no chat principal (falta Implantar + o canário) |
| 8 · C | 132-C **o WhatsApp do corretor** (o mesmo chat pelo número da plataforma "AutoBrokers"; executa a 131-0 parte B1) | AUX | ✅ **CONCLUÍDA 14/10, DESLIGADA**, nota 💭 **86** (proposta do atualizador; 🔴 CRÍTICO; C1 → C2 → C3 costura · juiz 84 (1 blocker: o portão do assistente falhava ABERTO com o banco instável) + o P1 promovido (o código valia de QUALQUER remetente, sem teto global) ‖ red team 82 QUEBREI (1: a volta da cotação mandava à LINHA de atendimento de uma corretora, robô → robô) → conserto único → **confirmação 88** (3/3; N1 "o teto global desliga a ativação de todos" consertado em `ce32e89`); migrations `20261014_03` (📊 `20261014075717`) e `_05` (📊 `20261014112744`) APLICADAS) — a verificação por POSSE (o corretor manda "ATIVAR <código>" do celular DELE; o código só vale do número declarado, D-132C-02); o desvio no webhook antes do observer, desconhecido = silêncio (D-132C-03); o MESMO `/chat/stream` em processo (D-132C-04); `channel='whatsapp_assistente'`, fora da Central, do espelho e da Fila (D-132C-05); o cinto único da saída com anti-laço e teto de envios; a volta da cotação pelo WhatsApp; o QR em Admin → Canais. 📊 QCM e atendimento intactos (`test_spec133a_o_fio` 17/17) — `reports/SPEC-132-C-EXECUTION-REPORT.md` · D-132C-01…05 · P-132C-01…10 | idem | 🧑 **T-171** o número do AutoBrokers: chip → QR → `ATALHO_WHATSAPP_LIGADO=1` → cada corretor declara e ativa | — |
| 8.1 | **"A loja de aplicativos"** (anotada 12/10, D-131-28): a galeria nova com imagens, os OUTROS aplicativos no padrão da 131-B (conteúdo, aba de trabalho), o modal da Cobrança no padrão, a P-16 e a **EXTRA-001.9** juntas (mesmas rotas) | base | ⏳ SPEC a escrever, depois da 132 | — | a 131-B feita (o padrão nasce nela) | — |
| 8.2 | **Vida e moto** — ramos novos do Agger (anotada 12/10, D-131-28, nota 80; 📊 ~9 renovações de vida por mês numa corretora real, laudo I1 §4) | base | ⏳ SPEC a escrever, depois da 132 (129-D) | — | — | — |
| 9 | 133-B Quem Cobra Menos piloto ampliado | QCM | ⏳ | — | 🧑 regras de negócio entre corretoras (D-MC-56) · preço do canal (D-MC-29) | 🚀3 Quem Cobra Menos piloto no WhatsApp |
| 10 | 135 a proposta conversa (+ 131-0 parte **B2**: o WhatsApp do usuário PAREADO, o envio automático da renovação e a negociação — anotado 12/10, D-131-24/28) | AUX | ⏳ | — | atendimento das corretoras ligado · D-MC-32 · a 131 deixa pronto: estados, link rastreado, pedido no mesmo Agger, "o que o cliente respondeu" | 🚀4 negociação pelo WhatsApp |
| 11 | 136 lembretes | base | ⏳ | — | opt-in | — |
| 12 | 137 Quem Cobra Menos público (WhatsApp oficial, aberto) | QCM | ⏳ | — | a 134 feita | 🚀5 público |
| ★ | Claude/ChatGPT (o conector e a prova de instalação da v2.4) | QCM | ⏳ | — | depois da 137 | — |
| ⇅ | 134 migração do número para a API oficial da Meta — **FLUTUANTE** | QCM | ⏳ (entra assim que a Meta aprovar, a qualquer momento depois da 133-A) | — | 🧑 Meta: empresa verificada, número, nome · cartão na conta Meta | — |

## 2. O que o Founder informou na abertura (04/10/2026)

- **Variáveis do `smith-api` no EasyPanel:** `WORK_RUNS_ROUTINE_BRIDGE=1` (a cobrança e as rotinas passam pelo Work OS →
  a 129-A mexe em caminho que **envia mensagem**: rito CRÍTICO pelo piso §3.2) · `WORK_WORKER_IN_PROCESS` **não existe**
  (o worker roda como serviço dedicado; o defeito do reinício silencioso do modo "dentro da API" não está ativo).
- **Autorização:** Resulta e AutoFleet autorizaram o uso do Agger e o desenvolvimento do programa, inclusive concluir
  cálculos (D-MC-23). Pode ler e analisar as cotações da equipe no Agger; **nunca apagar cotação feita por uma pessoa**.
- **InfoCap:** a conexão da Resulta está hoje dentro da corretora de ensaio, de propósito (D-MC-27); pode ler a da
  AutoFleet e a da corretora de ensaio.
- **Apólices de teste:** `docs/intake/MULTICALCULO AGGER/APOLICES/` (fora do git), autorizadas para cotar e testar.
- **Login do Agger (Founder, 04/10):** até existir o login exclusivo do robô, usar o login da Ellen (Resulta e AutoFleet). Parar se
  o Founder mandar ou se houver outra pessoa logada (o modal de sessão única avisa — NUNCA clicar "Prosseguir" sobre sessão de outra pessoa).
  Exceção temporária à D-MC-24, só para a 128 e testes; o motor (129-B) em uso real exige o login do robô.
- **Segredos:** a rotação é do Founder, no fim do projeto (D-MC-35). Nenhum segredo entra em arquivo versionado.

## 2.1 O que o Founder decidiu em 05/10/2026

Na conversa que fechou a SPEC-128 (04–05/10), o Founder mudou o canal e a fila. O resumo com o porquê está na
[PASSAGEM](PASSAGEM-2026-10-05-WHATSAPP-PLANO-A.md); as decisões são a D-MC-51 a D-MC-60 (a D-MC-57, modelo comercial, é
hipótese, não decisão). Em uma linha: o Quem Cobra Menos nasce no WhatsApp comum (Evolution), num número exclusivo da marca,
separado do atendimento das corretoras; migra para a API oficial da Meta na 134; compara seguradoras e corretoras parceiras,
calculadas em paralelo, e indica a vencedora; Claude/ChatGPT ficam para a ★.

## 2.2 O que o Founder decidiu em 05/10/2026, à tarde (v2.5.1)

- **D-MC-61 · a fila intercalada** (tabela do §1): as duas linhas andam juntas; a 134 flutua. Notas: intercalada 88 · auxiliares
  primeiro 75 · a v2.5 como estava 55. O porquê na [PASSAGEM](PASSAGEM-2026-10-05-WHATSAPP-PLANO-A.md) §3 e §8.
- **D-128-03 TOMADA:** o robô recalcula reenviando o corpo do pedido (`calcularV2`) com o ajuste, de dentro da página, com o token do
  próprio app; resolve a D-MC-28 (o login continua pela tela; a interceptação continua lendo os resultados). P-128-14 FECHADA, T-107 feita.
- **Os logins do Agger:** os da 128 são os da **Ellen** — uma PESSOA —, autorizados para TESTES. O Agger tem sessão ÚNICA por login: o
  robô e a Ellen ao mesmo tempo derrubam um ao outro. **Construir e testar a 129-B:** o login da Ellen, de preferência fora do horário
  dela (aviso de sessão ativa → Cancelar e parar; nunca "Prosseguir"; nunca apagar nada; captador de lista branca). **Uso real** (antes
  de a 133-A ir aos testadores e antes da 131/132 irem para as corretoras): um usuário NOVO no Agger só para o robô em cada corretora
  (T-120). 📊 04/10 (`cfg/assinatura-aggilizador` e `listaUsuarios`): Resulta 5 licenças e 6 usuários ativos · AutoFleet 8 e 7 → a
  AutoFleet tem 1 licença livre; a Resulta provavelmente precisa de 1 a mais ou liberar uma (decisão de compra do Founder).

## 2.3 O que o Founder decidiu em 05/10/2026, à noite (o portão de preço da 130-A)

- **D-MC-62 · a econômica padrão:** franquia normal + vidros básicos + carro reserva 7 dias + assistência básica; casco 100 % FIPE e RCF/APP intactos (FIPE a 90 % fora).
- **D-MC-63 · a margem da corretora** (comissão e desconto como UMA regra): o agente calcula a versão com margem menor e a mostra ao CORRETOR; nada vai ao cliente sem ele aprovar, cada vez.
- **D-MC-64 · o piso padrão da margem** = comissão de 10 % enquanto a corretora não configurar o dela.
- **D-MC-65 · a completa é UM padrão único** para todas as corretoras (RCF 200/200/20 mil, APP 5 mil, franquia reduzida, vidros completos, reserva 15 dias, assistência completa).
- 🧑 **Ressalva do Founder:** são usadas agora; ele perguntou aos comerciais das corretoras e fará ajustes pontuais quando tiver as respostas → cada uma é CONFIGURAÇÃO (presets/colunas), nunca constante espalhada.
- 📊 Medido no canário da 129-B (05/10, 3ª rodada): econômica ÷ padrão por seguradora, média **0,873** (corretora A, 14 seguradoras) e **0,872** (B, 11) — a D-MC-62 estimava 💭 12–20 % abaixo.

## 2.4 O que o Founder decidiu em 06/10/2026 (a abertura da 130-A)

- **D-MC-66…69 · a estratégia das comerciais:** três situações (renovação · novo com apólice · novo sem apólice), cada uma com a sua estratégia e as suas 3 opções ("igual à atual" sempre que houver apólice); a ordem do "mais barato" (desconto da seguradora → comissão 15 → 12 % → franquia → reserva → vidros/assistência); o agente aplica sozinho até 12 %, 10 % só com o corretor aprovando.
- **D-MC-70…72 · o agente e a negociação:** "usa o carro para aplicativo?" é a 1ª pergunta; validade e lembretes honestos (nunca cronômetro falso); a cotação-alvo procura o alvo com a MAIOR comissão possível.
- **D-MC-73 · a 129-C** (mais ramos do Agger) entra logo depois da 133-A e antes da 130-B/131 · **D-MC-74 · o WhatsApp leva no máximo 2 opções + 1 linha-resumo + o link**; o resto mora na página.
- **D-130A-06/07/08 · escopo:** registro do lead e consentimento → 133-A; PDF = imprimir do navegador (o do servidor depois, D-MC-43); a remuneração da corretora (CNSP 382) desligada até o jurídico.
- **D-130A-11 · o modelo visual = a "carteira"** (painel cego de 4 rodadas, 8 críticos: 85/83 → 89/88 → 90/92 → 91/90); protótipo claude.ai/artifact/K3pGqdMQ9dvThA7r6AZSZC. Tudo é CONFIGURAÇÃO por corretora (`multicalculo_config`), nunca constante.

## 2.5 O que o Founder decidiu em 10/10/2026 (a 133-A.1)

- **D-133A1-01 · QCM, Cotação e Renovação têm regras e apresentação SEPARADAS** — ajustar uma não muda as outras sem ordem explícita.
- **D-133A1-02 · "homem ou mulher?" só para nome ambíguo** (tabela do IBGE, ≥ 70 % de um sexo → não pergunta; configuração do canal).
- **D-133A1-03/04 · o Agger da corretora entra pela TELA** (cofre, o mesmo serviço do comando) e é a conta GLOBAL do robô; login de
  pessoa continua proibido; um login nunca em duas contas (revê a D-129B-11).
- **D-133A1-05 · a SPEC-131-0 é planejada agora** e executada (parte A) depois da 129-C e antes da 130-B/131.
- **D-133A1-06 · a 129-C abre num chat NOVO**; a regra +15 % é configuração · **D-133A1-07 · a menor parcela é a que a seguradora traz.**

## 2.6 O que a 129-C decidiu em 11/10/2026 (D-129C-01…09, pela maior nota)

- **D-129C-01 · o Agger da corretora fica SEMPRE ligado** (92); o horário mora no auxiliar · **D-129C-02 · a fonte de RE é o histórico do
  Agger**, não a InfoCap (95; 📊 InfoCap da Resulta 0/12/3 em 32.901 × Agger 672/115/182). ↪ **REVISTA por D-131-0-26 (11/10):** a
  conexão medida tinha o login da AutoFleet; a InfoCap da Resulta TEM RE (📊 2026: RESI 255 · COND 227 · EMPR 148).
- **D-129C-03 · as opções de RE não fixam valores**: a básica vem do pedido, a opção varia extras e assistência (88) · **D-129C-04 · a
  atividade do empresarial é por seguradora**, sem atividade compatível a seguradora sai listada (85).
- **D-129C-05 · a comissão de RE vai explícita no item** (88) · **D-129C-06 · o reajuste da renovação é configuração**, padrão 15 % —
  🧑 o Founder confirma contra o +10 % medido (80) · **D-129C-07 · preferência de seguradoras por ramo** (90).
- **D-129C-08 · a página/proposta dos outros ramos é a 130-C** (82) · **D-129C-09 · o canário usa 1 risco real por ramo** pela conta
  cotador@ da Resulta, nada vai ao cliente (85).

## 2.7 O que a 131-0 parte A decidiu em 11/10/2026 (D-131-0-03…35, pela maior nota)

- **D-131-0-03 · o dono da renovação é o produtor `indireto="F"` do `/prod_docs`** (96; 📊 Resulta 99/99 · AutoFleet 217/217) ·
  **D-131-0-26 · a InfoCap da Resulta TEM RE** e é a fonte de quem e quando renova (95) · **D-131-0-27 · a conexão da Amandus é a AutoFleet**,
  renomeada; trocar o login é do Founder (85).
- **D-131-0-05 · o Agger de uma pessoa é login de pessoa** (logout sempre; sessão ativa = Cancelar; 3× ocupada → falha com motivo, nunca a
  global calada) (84) · **D-131-0-06 · a senha** pelo admin ou pela pessoa, nunca reaparece (88) · **D-131-0-29/30** o dono da conta é a
  pessoa e o vínculo cai com ela (88/90).
- **D-131-0-31 · a regra do dono é dado** (86) · **D-131-0-32 · `servico` é coluna nova** (92) · **D-131-0-14 · funções + papel fechado** (85).
- Cortes (CHANGE-ADDENDA, propostos ao Founder): **D-131-0-08** auxiliares no catálogo só com runtime (85) · **D-131-0-28** convite por
  link (80) · **D-131-0-33** funções por ramo e substituto (78). Dos builders: **D-131-0-34** sem índice "uma global" (80) ·
  **D-131-0-35** a aba do QCM só leitura (80).

## 2.8 O mapa de 11/10/2026 — InfoCap, Agger, seguradoras, cobrança e leitura de apólice (D-1311-01…06)

- **D-1311-01 · a 130-B vira a ficha única da apólice** e abre em chat novo (92 × 40; a mudança de escopo ACEITA pelo Founder 11/10) ·
  **D-1311-02 · a fila nova** (✅ TOMADA pelo Founder 11/10, com a cobrança estável no FIM — acima no §1).
- **D-1311-03 · o Agger nunca é cofre de senhas** (📊 o Agger publica a senha da seguradora no navegador; a ideia contrária tem nota 5) ·
  **D-1311-04 · escrever na InfoCap só com homologação** (88 × 30; não há ambiente de teste nem DELETE de documento).
- **D-1311-05 · endosso = SPEC própria "assistida"** (80; nem Agger nem InfoCap abrem endosso) · **D-1311-06 · "Emissão e registro"** é o
  nome da etapa depois do "sim" (86).
- 📊 Cobrança: o robô acerta 13/13 quando entra; as falhas são senha (Allianz, Mapfre) e a lista vazia da Zurich; parado desde 11/09
  (P-COBRANCA-01…04). O que é do Founder: **T-145 a T-153**.

## 2.9 O que o Founder respondeu em 11/10/2026 (às T-145…T-153) e o que a 130-B decidiu (D-130B-01…17)

- **Feito:** o `smith-web` implantado e o `/api/versao` conferido ("já implantei e deu certo") · as senhas da Allianz e da Mapfre das duas
  corretoras-piloto enviadas e GRAVADAS pelo gerente no cofre do produto (`portal_accounts`, cifradas; conferidas por releitura; o cifrado
  antigo guardado fora do git) — 📊 uma das Mapfre já tinha a senha nova (a falha antiga não era a senha); a outra trocou também o LOGIN;
  nada foi testado no portal (a cobrança continua desligada) (T-145).
- **Respondido:** a InfoCap **não tem base de homologação** para o INCORP → a D-1311-04 continua valendo (não escrever na InfoCap) e a
  "Emissão e registro" terá de PROPOR como escrever em produção com segurança (P-INFOCAP-INCORP); o Agger **não** alimenta a InfoCap
  sozinho; "Sincronizações" por API = a API atual (dá para tentar por HAR dentro da InfoCap, se for preciso) (T-150) · o menu
  "Sincronizações" **não existe** no Agger (T-151) · o e-mail à HDI **não precisa**: a liberação de parceiro já existe; por ora, as
  informações do Agger (T-149). Prioridade do Founder agora: cotações, renovações, Quem Cobra Menos e cálculos.
- **Para o fim da fila (cobrança estável):** religar em teste (T-146) · os HAR (T-147/T-148: o material de MAPFRE, TOKIO e ZURICH está em
  `docs/intake/PORTAL SEGURADORAS/`, 📊 2 HAR cada + HTML; o HAR da Allianz usado na construção da cobrança não foi guardado).
  **Adiado:** o Excel financeiro (T-153). **Sem resposta:** T-152 (as senhas expostas pelo Agger).
- **A 130-B:** D-130B-01…12 (SPEC §7) + as do conserto: rótulo embrulhado em 2 linhas só com o prêmio na de baixo, 3+ nunca (13) ·
  nascimento mascarado pelo rótulo (14) · linha do modelo/visão que não fecha não passa por cima do cadastro (15) · `LEITOR_VERSAO` 130B.2,
  tudo relido uma vez (16) · `documento_oficial` = SUPORTADA (17).

## 2.10 O que a 131-A decidiu em 12–13/10/2026 (D-131-29…39)

- **Do Founder:** retentativa de hora em hora até 06:15 quando a pessoa volta ao Agger (D-131-29) · todo subagente declara o modelo (D-131-32).
- **Do gerente:** teto 1 sessão por corretora até medir A4 (82) · canário com relógio injetado (85) · 📊 pico de 42 renovações de um dono →
  12 por conta por noite + antecipar 7 dias (85) · o Prosseguir só no id do aviso (90; revê D-131-0-05 com a D-131-03) · canário na corretora
  de origem (85) · a licença do Agger avisada (85).
- **Do conserto:** `sem_conexao` não conta na completude e o aviso traz "N calculadas de M cotáveis" (D-131-37, revê a fórmula da SPEC §4) ·
  moto pela placa, frota e RCF-V = `pendente(ramo_nao_cotado)` (D-131-38) · sem franquia na ficha, `anterior` com a NORMAL e a reduzida volta
  como 3ª opção (D-131-39). ⚠️ O rascunho da 131-B usa D-131-38/39 para outras decisões: a 131-B renumera.

## 2.11 O que a 131-B decidiu em 13/10/2026 (D-131-40…52)

- **Da SPEC (§7):** a loja na galeria que existe (90) · galeria híbrida, capa gerada + `cover_url` (90) · três páginas por momento (F) · WhatsApp de trabalho = só o número confirmado (88) · "Quero renovar" dono ativo → corretora → sem botão (85) · tokens globais intocados (80).
- **Das fatias e do conserto:** Serviços aceita as chaves da renovação (85) · "com qual conta" ligada de verdade (80) · "preparar o envio" fora da tela (88) · a busca por cabeçalho, nunca na URL (95) · a página só é reaproveitada se quem atende não mudou (90) · "Como começar" sobe quando falta passo (85) · ligar exige `confirmar_ligar` no servidor (90).
- ⏳ **Do Founder:** quem vê "Todas" (T-165, P-131B-01). ✅ A colisão D-131-38/39 da 131-A está resolvida (a 131-B começou na D-131-40).

## 2.12 O que a 132 (A · B · C) decidiu em 14/10/2026 (D-132A-01…08 · D-132B-00…10 · D-B4-01 · D-132C-01…05 · D-132-E1 · D-132-G1…G3)

- **132-A, o chat (SPEC §7):** refazer o composer, não remendar (90) · a barra de atalhos do rodapé sai do celular (82) · a tela vazia sem
  atalhos (80) · esforço = o MESMO modelo do `chat_principal` com `low/medium/high` (85) · o anexo lido por BYTES, nunca URL nossa ao provedor
  (92) · o áudio pelo mesmo stream, fora do `/api/n8n` (88) · caixa no meio no notebook (85) · esforço lembrado por aparelho (80).
- **132-B, a Cotação Rápida (SPEC §7):** A e B no mesmo branch (80) · a página de COTAÇÃO vira página de VENDA (88) · bloco sem dado SOME (95) ·
  `confirmacao_id` de uso único, 30 min (92) · a resposta volta na MESMA conversa (90) · o link vai ao CORRETOR (92) · Configurar mostra todas
  as regras e edita três (82) · os nomes "Cotação Rápida" e "Renovação Automática" (F) · exemplos com a faixa (85).
- **132-B, da execução:** a tela consulta a conversa a cada 6 s porque `messages` não está no Realtime (D-132B-09, 85 × 60) · a gravação do
  Configurar substitui as chaves editáveis (D-B4-01, 78 × mesclar 62) · a comissão de entrada vale só em RE; no carro, a da conta do Agger
  (D-132B-10, 85 × mexer nos presets 40) · o exemplo com a barra no número de teste do Founder (D-132-E1, 85 × sem barra 40).
- **132-C, o WhatsApp do corretor (SPEC §7 + execução):** um número da PLATAFORMA para todos (88) · verificação por POSSE (90) · número
  desconhecido = silêncio (85) · o mesmo CORE e a mesma conversa (92) · `channel='whatsapp_assistente'` (D-132C-05, 88 × reusar `whatsapp` 35).
- **Do gerente, com o Founder:** a InfoCap de cada corretora na SUA conta; a corretora de ensaio fica sem InfoCap (D-132-G1, autorizado pelo
  Founder 14/10; 📊 Resulta e AutoFleet `connected/healthy`, 3 conexões antigas arquivadas com motivo) · buckets do chat com 20 MB e 25 tipos
  (D-132-G2) · o modelo português do spaCy na imagem do `smith-api` (D-132-G3).
- ⏳ **Do Founder:** a Cotação Rápida vale para toda corretora com agente central (hoje sim, pela capability global) ou só com o aplicativo
  ligado? (T-172, P-132B-07).

## 3. Livro-caixa da API do produto — modelos e serviços pagos (verba do programa: 💭 US$ 4,00, Founder 04/10)

| data | SPEC | o quê | US$ | saldo |
|---|---|---|---:|---:|
| 04/10 | — | abertura | 0,00 | 4,00 |
| 04/10 | 128 | medições ao vivo e testes | 0,00 | 4,00 |
| 05/10 | 129-B | medições ao vivo e canário | 0,00 | 4,00 |
| 06/10 | 130-A | Google Places: 2 buscas (Text Search) para a ficha das corretoras — 💭 estimado pela tabela pública do Google | 💭 0,07 | 💭 3,93 |
| 06/10 | 130-A | modelos de linguagem | 0,00 | 💭 3,93 |
| 10/10 | 133-A.1 | nenhuma rodada paga de modelo | 0,00 | 💭 3,93 |
| 11/10 | 131-0-A | nenhuma rodada paga de modelo (só GET/`/login` na InfoCap) | 0,00 | 💭 3,93 |
| 11/10 | 130-B | BLOCO 0, 2 leituras de apólice pela Luna (papel `auxiliar`; estimado 💭 0,02 antes) — 📊 real `token_usage_logs` `service_type='bancada_130b'`: 0,000588 + 0,001732 | 📊 0,0023 | 💭 3,93 |
| 11/10 | 130-B | ESTIMATIVA ANTES da régua das 32 (F5, papel `leitura_de_apolice`): 💭 ~21 leituras pelo modelo × US$ 0,002 + ~16 páginas pela visão × US$ 0,003, até 3 rodadas (estimado 💭 0,30 antes) — 📊 real `token_usage_logs service_type='bancada_130b'` depois de 00:30 UTC: 41 chamadas (2 rodadas + 3 diagnósticos) | 📊 0,0515 | 💭 3,88 |
| 12/10 | 130-B | régua do CONSERTO (juiz por linha; estimado 💭 0,06 antes: 1–2 rodadas × ~US$ 0,03) — 📊 real `token_usage_logs service_type='bancada_130b'`, acumulado de 0,053790 a 0,091085 | 📊 0,0373 | 💭 3,84 |

| 12/10 | 130-B | régua da CONFIRMAÇÃO (as 7 apólices da regra das duas linhas, depois do guarda novo; estimado 💭 0,015 antes) — 📊 real: acumulado 0,091085 → 0,098287 | 📊 0,0072 | 💭 3,83 |

| 12/10 | 131-A | ESTIMATIVA ANTES do canário da madrugada (F4): ≤ 5 renovações reais da corretora de origem; leitura da ficha 📊 ~US$ 0,0014 cada (BLOCO 0) × 5 × até 2 rodadas; cálculos no Agger não custam modelo (estimado 💭 0,02 antes) | — | 💭 3,83 |

| 13/10 | 131-A | canário REAL da madrugada (F4 · F5 · F6, 13/10, ~03:30–04:53 UTC; estimado 💭 0,02 antes) — 📊 real `select count(*), sum(total_cost_usd) from token_usage_logs where created_at between '2026-10-13 03:00+00' and '2026-10-13 05:00+00'` → 0 linhas: o canário rodou sem o PDF e o perfil vem da InfoCap (sem modelo) | 📊 0,00 | 💭 3,83 |

| 13/10 | 131-B | nenhuma chamada a modelo pago (loja, telas, página e envio; os testes usam dublê de banco e InfoCap; estimado 💭 0,00 antes) — 📊 real `select service_type, count(*), sum(total_cost_usd) from token_usage_logs where created_at >= '2026-10-13 07:00-03' and created_at < '2026-10-13 22:00-03' group by 1` → só `memory` (o atendimento das corretoras, 22 chamadas, US$ 0,0036, 0 citam renovação ou multicálculo): **0 da 131-B** | 📊 0,00 | 💭 3,83 |

| 14/10 | 132 (A·B·C) | ESTIMATIVA ANTES (do gerente e das SPECs §6): 💭 ≤ US$ 0,05 a medição de latência · ≤ 0,40 a 132-A · ≤ 1,00 a 132-B (canário + exemplos) — 📊 real `select service_type, count(*), sum(total_cost_usd) from token_usage_logs where created_at >= '2026-10-14 05:30+00' group by 1` → `chat` 3 chamadas = os 3 turnos de medição do BLOCO 0 no `chat_principal` (gpt-6.1-sol medium); os builders usaram dublês (0 chamada paga); o canário real da cotação NÃO rodou. `memory` 4 chamadas / US$ 0,0006 = o atendimento das corretoras, não a SPEC | 📊 0,0568 | 💭 3,77 |

📊 **Total da 130-B: US$ 0,0983 de modelo** (79 chamadas; `select sum(total_cost_usd) from token_usage_logs where service_type='bancada_130b'`; verba proposta US$ 1,50). O saldo segue 💭 por causa da linha estimada do Google de 06/10.

Regra: nenhuma rodada paga sem estimativa escrita aqui antes. O que sobrar passa para a SPEC seguinte.

## 4. O mapa dos testes do Founder, recontado (04/10/2026)

📊 Comando (no `docs/canon/`): `grep -cE '^- \[ \] \*\*T-[0-9]+' TAREFAS-DO-FOUNDER.md` → **95 pendentes**;
`grep -cE '^- \[x\] \*\*T-[0-9]+'` → **10 feitos** (T-01, 02, 05, 06, 82, 91, 92, 98, 99, 102). Total T-01…T-105.
A classe é a régua "PODE LIGAR" da validação de 03/10, reaplicada por script às 95 (a T-31 morreu → C).

| classe | quantos | quais |
|---|---:|---|
| **A · trava ligar o atendimento** (e por isso trava a 135; a 134 não, D-MC-58) | **48** | T-03 04 08 · 23–30 32 33 · 35–44 · 51 53 · 60–63 · 65–69 · 75–78 · 84–88 · 90 · 93–96 |
| **B · trava o programa** | **0** | — (o que travava a 128 estava fora da lista T: bloco H → D-MC-23/24/27/35) |
| **C · pode esperar** | **47** | T-07 · 09–22 · 31 · 34 · 45–50 · 52 · 54–59 · 64 · 70–74 · 79–81 · 83 · 89 · 97 · 100 · 101 · 103–105 |

A T-04 (crédito de API) pesa a partir da 130. O passo a passo de cada teste está em
[`ROTEIRO-DE-TESTES-DO-FOUNDER.md`](../ROTEIRO-DE-TESTES-DO-FOUNDER.md).
