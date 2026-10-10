# SPEC-131-0 — As contas da corretora: comerciais, Aggers, sistemas de gestão, WhatsApps e os três serviços

> **PROPOSTA DE PLANEJAMENTO · v0.1 · 10/10/2026** · escrita pelo planejador da fatia F5 da SPEC-133-A.1 (Opus 5.5, fresco),
> branch `spec/133-A1-qcm-ajustes`, base `bba54ce`. **Não executa nada agora** (D-133A1-05). O chat que for executá-la escreve a
> SPEC executável a partir desta proposta, com um revisor cego, no rito do protocolo v13.
> Fonte das vontades: [`RETORNO-DO-FOUNDER-2026-10-10.md`](../programa-multicalculo/RETORNO-DO-FOUNDER-2026-10-10.md) (texto
> integral). Prévia anterior: [`PLANO-COMERCIAIS-E-CONTAS.md`](../programa-multicalculo/PLANO-COMERCIAIS-E-CONTAS.md) (06/10) — esta
> proposta a SUBSTITUI onde discordar (ver §5, D-131-0-05).
> Legenda: **FATO** (com arquivo:linha, tabela ou comando) · **INFERÊNCIA** · **RECOMENDAÇÃO** · 📊 medido · 💭 ilustrativo.

---

## 0. Em uma página

O Founder pediu uma arquitetura em que **qualquer corretora** (CLAUDE.md §13.9) configure: o seu **sistema de gestão** (InfoCap,
Quiver, outro ou nenhum), o seu **Agger global**, os **Aggers dos comerciais**, os **WhatsApps** (da corretora e de cada pessoa), e
**três serviços com manuais separados** — Quem Cobra Menos, Cotação e Renovação —, cada um podendo **só calcular** ou **calcular,
entregar e negociar**.

O que a medição de hoje mostrou, em seis linhas:

1. 📊 **A InfoCap diz, sem ambiguidade, quem é o dono de cada renovação** — mas por um campo que o código de hoje NÃO lê. Em 228 de
   228 renovações dos próximos 30 dias, exatamente UM produtor tem a caixa "Ind." desmarcada (`indireto = "F"`), e em 224 o nome dele
   termina em FECHADOR/FECHADORA. O campo só vem no `/prod_docs` avulso (uma chamada por apólice). (§2.3)
2. 📊 **O que o código usa hoje como "produtor direto" é a pessoa ERRADA para a renovação:** o `produtor` de `/renovacoes` e o
   `ordem == 1` coincidem com o dono em só **27 de 228**. (§2.3)
3. 📊 **O papel (EXECUTIVO/INDICADOR/FECHADOR) não é campo da API:** é sufixo do NOME do produtor, convenção da corretora. 105 códigos
   de produtor, 95 pessoas, 10 pessoas com mais de um código. O vínculo pessoa ↔ produtor precisa ser CONFIGURADO. (§2.3)
4. 📊 **O motor de hoje trata todas as contas do Agger de uma corretora como um rodízio único** (`robos.py:215-224`): se um Agger de
   comercial entrar hoje pela tela, o Quem Cobra Menos passa a cotar nele. → **decisão JÁ** (D-131-0-04, §5).
5. 📊 **Os usuários são uma tabela de vínculo com um papel de texto livre**, três papéis oferecidos, nenhum grupo, nenhuma conexão por
   pessoa em produção, e a tabela de usuários guarda 1.161 leads junto com 7 pessoas da equipe. (§2.1)
6. 📊 **O Agger tem sessão única por login** (A-PROVA-DO-AGGER §E1/§10): calcular "no Agger da Mariana" é entrar com o login dela —
   a regra D-MC-24 proíbe isso hoje. O conflito precisa de uma medição no Agger e de uma decisão (D-131-0-05).

**Quando executar (RECOMENDAÇÃO, §8):** a parte A (a fundação: membros, vínculo com o produtor, contas do Agger com dono, qual Agger
usar, manual por serviço) **depois da 129-C e antes da 130-B/131** — antes da 131 porque a renovação calcula no Agger de cada
comercial, e antes da 132 porque a cotação pedida pela Ellen sai no Agger dela; a parte B (WhatsApp de cada pessoa e a ponte do
admin pelo WhatsApp) **junto com a 132**; a chave "negociar" se realiza na **135**.

---

## 1. Os requisitos do Founder, um a um (as palavras dele)

| # | o que ele disse (10/10) | o que isso exige |
|---|---|---|
| R1 | *"EXISTEM CORRETORAS QUE TERÃO APENAS UM AGGER E OUTRAS CORRETORAS QUE TERÃO VARIOS AGGER PQ TEM VARIOS COMERCIAIS"* | uma conta Agger GLOBAL por corretora + N contas de MEMBRO |
| R2 | *"ESSE AGGER QUE EU FALEI PARA COLOCAR NOS CONECTORES, ELE É PARA O QUEM COBRA MENOS"* | o QCM usa só o global (ou um específico do serviço) |
| R3 | *"QUANDO FOR UMA COTAÇÃO VIA CHAT FEITA PELA ELLEN, PRECISA SER COTADO COM O AGGER DA ELLEN E NAO COM OO GLOBAL E NAO PODE SER COM OUTRO CORRETOR"* | a cotação usa o Agger de QUEM PEDIU; nunca o de outro membro |
| R4 | *"SE NAO TIVER UM AGGER ESPECIFICOO VINCULADO AOO USUARIO, AI SERÁ USADO O GLOBAL"* | o global é o fallback de quem não tem Agger próprio (admin, corretora sem comerciais) |
| R5 | *"SE NA INFOCAP ESTIVER QUE O CLIENTE É DA MARIANA, PRECISA SER CALCULADOO NO AGGER DA MARIANA E DEIXAR PROROONTO DENTROO DO AGGER PRA ELA CONFERIR"* | a renovação calcula no Agger do DONO segundo o sistema de gestão |
| R6 | *"TEM OS EXECUTIVOS, INDICADORES E FECHADORES. EM CADA RENOVAÇÃO É PRECISO COLOCAR O COMERCIAL E USAR O AGGER CORRESPONDENTE"* | a regra de dono lê os papéis do repasse |
| R7 | *"OUTRA CORRETORA POODE TER A ESTRUTURA DENTRO DO QUIVER E TER OUTROS NOMES PARA OOS COMERCIAIS. PODE SER COMERCIAL 1, 2 3"* · *"NAO PODEMO CRIAR UMA SITUAÇÃO QUE SÓ DE PRA USSAR COM A RESULTA E AUTOFLEET DENTRO DA INFOOCAP"* | a regra de dono é DADO por corretora e por sistema; nenhum papel escrito no código |
| R8 | *"NAO SEI SE NO CONECTOR DO AGGER PODEREMOS COLOCAR ADICIONAR AGGER… E AI PERSONALIZA CADA COMERCIAL, VAI ADICIONANDO ELES UM A UM"* | tela para adicionar Aggers por pessoa |
| R9 | *"TALVEZ ANTES DE COLOCAR O AGGER PRECISA SER COLOCADO O SISTEMA DE GESTÃO … E SO DEPOIS O AGGER DA CORRETOORA … E AI OS AGGER ADICIONAIS DOOS COOMERCIAIS"* | uma ordem guiada de configuração |
| R10 | *"SE COLOCANDO DENTRO DOOS USUARIOS ESSAS REGRAS… SE COLOOCOAR DENTRO DOS APLICATIVOS/AUXILIARES"* | decidir onde cada regra mora (§4.1) |
| R11 | *"A CORRETRORA DEVE PODER ESCOLHER SE QUER QUE O AGENTE … FAÇA SÓ O CALCULO … OU SE QUER LIGAR A OPÇÃO DE NEGOCIAÇÃO"* · *"PRECISAM SER ETAPAS SEPARADAS DENTRO DO MESMO SERVIÇO"* | uma chave por serviço: calcular-só × calcular+entregar+negociar |
| R12 | *"A NEGOCIAÇÃO PODE SER FEITA PELO CONTATO [WHATSAPP] GLOBAL DA CORRETORA … OU … POR CADA COMERCIAL … O AGENTE NEGOCIA EM NOME DO COMERCIAL"* | WhatsApp da corretora × WhatsApp do membro, escolhido por regra |
| R13 | *"CRIAR UMA PONTE DOS ADMS … PELO WHATSAPP DELE … MANDA UM AUDIO E UMA APOLICE … 'CALCULE ESSE SEGURO PRA MIIM'"* | o chat principal por WhatsApp, para membros identificados |
| R14 | *"O MANUAL DE REGRAS SPARA RENOVAÇÃO, COMO PENSAR, COMOO COTAR, DEVE SER DIFERENTE DE QUEM COBRA MENOS E DA COTAÇÃO"* · *"SE EU FALAR QUE É PARA TODAS A MESMA REGRA, AI AJUTA EM TUDO"* | um manual/config por serviço; regra compartilhada só por ordem explícita (D-133A1-01) |
| R15 | *"O QUEM COBRA MENOS TALVE TENHA QUE VIRAR UM AUXILIAR QUE APARECE DENTRO DO DASHBOARD DAS CORRETOORAS SELECIONADAS"* | o QCM visível só às corretoras aderentes |
| R16 | *"TER UMA PARTE DE PREFERENCIAS EM CADA RAMO PRA COORRETORA COLOCAR AS PRINCIPAIS"* (ex.: Allianz residencial) | preferências de seguradora por ramo por corretora |
| R17 | *"SEMPRE QUE A COORRETORA RENOVA, ELA AUMENTA A COBERTURA BASICA EM 15%"* | regra do manual de RENOVAÇÃO, por ramo, como config |
| R18 | *"QUEM COBRA MENOS … NAO TERÁ COMERCIAL AINDA PQ SÃO LEADS FRIOS"* | o QCM nasce sem dono; a passagem escolhe quem recebe |
| R19 | *"O COMERCIAL PASSA PARA A PESSOA RESPONSAVEL PELO CLIENTE … QUE NEM SEMPRE É A PESSOA QUE NEGOCIA"* | "quem calcula" ≠ "quem negocia" ≠ "quem é responsável pelo cliente" |
| R20 | *"O COMERCIAL VAI VERIFICAR TODOS OS DIAS DE MANHÃ"* | o que fica pronto no Agger e no painel, e o aviso |
| R21 | *"EU SINTO QUE USUARIOS ESTA MEIO DESCONEXO … ENGESSADOO, NAOO É TÃ BEM DIVIDIDOO COOMO TEAMS DO CLAUDE E OOPENAI, SLAK"* | rever o modelo de usuários (§4.4, D-131-0-14) |
| R22 | *"ANOTE TUDO, MAS NAO FAÇA ANOOTAÇÕES SIMPLIFICADAS"* · *"VC TEM O DEVER DE MAPEAR TUDOO, TODAS AS VARIAVEIS QUE FALTARAM"* | o §3 |

---

## 2. O que existe hoje (FATO, medido em 10/10/2026)

Banco: `backend/.env` `SUPABASE_DB_URL`, psycopg, `set transaction read only`, só contagens (script no rascunho do F5,
`f5-131-0/q.py`). InfoCap: a conexão `connected` (a da Resulta, dentro da corretora de ensaio, D-MC-27), **só GET**, nenhum nome ou
CPF impresso, scripts `f5-131-0/ic2.py…ic6.py`, arquivos com dado pessoal apagados ao fim.

### 2.1 Usuários, membros e papéis — o que o Founder chama de "engessado"

| fato | onde / comando |
|---|---|
| A pessoa mora em `users_v2` (e-mail, senha, CPF, telefone, plano Stripe, **e também `company_id` e `role`**) e o vínculo em `company_members (user_id, company_id, role varchar, is_owner, status)` — **dois lugares dizem o papel** | `information_schema.columns` |
| 📊 `company_members`: 10 vínculos, 7 pessoas, 3 corretoras; `admin_company` 8, `member` 2; 6 dos 10 vínculos são de pessoas com mais de uma corretora (os sócios) | `select role,is_owner,status,count(*)… from company_members group by 1,2,3` |
| 📊 `users_v2` guarda **1.161 linhas `status='lead'`** sem vínculo em `company_members` — clientes misturados com a equipe | `select count(*) from users_v2 u where deleted_at is null and not exists (…company_members…)` |
| Os papéis oferecidos na tela são três: `admin_company`, `member`, `attendant` | `app/api/dashboard/team/route.ts:31` |
| A política aceita `owner`, `admin`, `admin_company`, `master_admin` para escrever config — dois deles nunca são oferecidos | `lib/admin/admin-auth-policy.ts:5` |
| 🔴 Membro criado sem senha nasce com a senha **`mudar123`** | `app/api/dashboard/team/route.ts:58` |
| `invites` existe (📊 10 convites, todos `admin_company`), com `role`, `email_restriction`, `max_uses` | `select role,count(*) from invites` |
| Admin da plataforma é separado: `admin_users` (📊 1) + `platform_admin_role_bindings` (📊 1 `platform_owner`) | idem |
| Nenhum grupo/equipe dentro da corretora; nenhuma função ("comercial", "calculista", "negociador") | 📊 0 tabelas: `information_schema.tables where table_name ~ '(group\|grupo\|equipe\|team)'` |
| O chat sabe QUEM pede: o BFF resolve `userId`/`companyId` pela sessão e valida em `company_members` a cada request; o corpo do navegador não manda nisso | `app/api/chat/stream/route.ts:13-45` |
| O Work Run já carrega quem pediu: `work_runs.requester_user_id` e `owner_user_id`, `visibility` | `information_schema.columns` de `work_runs` |
| A camada `user` de conexão existe no papel, mas 📊 "Ainda não há conector desta camada em produção" | `CAMADAS-DE-CONEXAO.md` |
| `company_internal_numbers (phone, label, kind ∈ fixo·comercial·socio·membro·outro)` — os números da equipe, **sem vínculo com o usuário** (📊 0 linhas hoje) | `app/api/dashboard/internal-numbers/route.ts:25` |

**INFERÊNCIA:** "engessado" = (a) papel é um texto, não uma função de trabalho; (b) a mesma informação em duas tabelas; (c) não há
o que um Slack/Teams/Claude Team tem: **papéis fechados + grupos + conexões da organização habilitadas pelo admin e conectadas por
cada pessoa** (§7.3 abaixo); (d) a tabela de usuários serve a clientes e funcionários.

### 2.2 As conexões

| fato | onde / comando |
|---|---|
| Três tabelas dizem o que a corretora conectou: `tenant_connections` (caminho novo, com `owner_user_id`), `portal_accounts` (portais e Agger), `integrations` (WhatsApp) — unificar é dívida registrada | `CAMADAS-DE-CONEXAO.md` |
| 📊 `connector_templates` tem `quiver` (scope `company`) **sem nenhum código que fale com o Quiver** — só citações em comentários | `select slug,scope from connector_templates` · `git grep -il quiver -- backend/app` |
| 📊 InfoCap: 1 conexão `connected` (a da Resulta, na corretora de ensaio), 2 `disconnected`, 4 `archived` | `tenant_connections ⨝ connector_templates` |
| 📊 `portal_accounts` do Agger: 2 linhas (uma por corretora), `robo_estado='pausado'`, nenhuma com dono humano — **não existe coluna de dono-membro** | `select portal_key,robo_estado,… from portal_accounts` |
| O motor escolhe a conta entre TODAS as contas `agger` com `robo_estado` não nulo da corretora, a menos usada primeiro (rodízio) | `backend/portal_worker/multicalculo/robos.py:215-224` (`candidatos`) e `:244-281` (`escolher`) |
| A conta de pessoa (`teste`) só serve a pedido de teste no canário | `robos.py:179-184` |
| `resolver_conta` (portais de seguradora) recusa quando há mais de uma conta ("ambígua") | `backend/app/services/portals/resolver.py:136-235` |
| A porta do multicálculo não recebe QUEM pediu nem qual conta: `calcular(company_id, pedido, corretoras, origem)` | `backend/app/services/multicalculo/porta.py:278` |
| `multicalculo_pedidos.origem ∈ ('auxiliar','canal','teste')` | `backend/supabase/migrations/20261005_01_spec129b_motor.sql:310` |
| `multicalculo_config`: **uma linha por corretora** com seções misturadas (`comissao`, `renovacao`, `canal`, `nota`…) — o manual do QCM e o da renovação moram no mesmo objeto | `backend/app/services/multicalculo/config.py:34-140` |
| 📊 `integrations` (WhatsApp): `evolution-go/observer` ativo 3 (3 corretoras), atendimento inativo; **sem dono-pessoa** (`company_id`, `agent_id`, `purpose`) | `select provider,purpose,is_active,count(*)…` |
| 📊 `tenant_auxiliaries`: 10, todas `visibility='company'`, 0 com `owner_user_id` · no catálogo, `renovacao-maxima` existe (`coming_soon`, exige `infocap`) e não há auxiliar de cotação nem de QCM | `select … from auxiliary_templates where slug ~* 'renov|cota|…'` |
| O Agger: uma conta por contrato da corretora, N licenças = N logins; 📊 Resulta 5 licenças, AutoFleet 8 (04/10); as senhas das SEGURADORAS são do contrato; "cada login enxerga uma corretora só"; negócio e versão têm `usuarioId` | `A-PROVA-DO-AGGER.md` §2/§E14 · `backend/portal_worker/multicalculo/agger_robo.py:295,380-391` |

### 2.3 A InfoCap responde à pergunta do Founder? — **SIM, com uma ressalva**

Documentação pública (coleção Postman `CorpAPI`, publicada 14/03/2025, baixada de
`documenter.gw.postman.com/api/collections/33455116/2sAYkBrLmi`): **55 rotas**. As que importam aqui: `/produtores?texto=&codage=`,
`/agentes`, `/prod_docs` (GET por `codfil`+`nosnum`; POST/PATCH/DELETE com `indireto`), `/renovacoes` (por `fimvig`),
`/documento`, `/itens`, `/cliente`, `/negocio` (o corpo tem `codusu_responsavel`), `/negocios_andamento`, `/documentos_bi`. A
documentação **não traz resposta de exemplo** de `/produtores` nem do `/prod_docs` avulso — foi preciso medir.

| pergunta do Founder | resposta medida (10/10, conexão da Resulta) |
|---|---|
| a renovação está clara? | 📊 `/renovacoes` de 10/10 a 09/11/2026 → **228** apólices (221 AUTO, 5 MOBI, 1 FROT, 1 RESI), todas com `cic` e 224 com telefone |
| os comerciais estão lá? | 📊 `/produtores` → **105** códigos, só `codigo` e `nome` (nenhum campo de papel, de ativo/inativo, de e-mail ou de usuário do sistema); `/agentes` → 1 |
| o papel de cada comercial? | 📊 o papel é **sufixo do nome**: 17 nomes com INDICADOR/A, 14 com FECHADOR/A, 2 com EXECUTIVO, 72 sem rótulo; 95 pessoas-base, **10 pessoas com mais de um código** (um por papel) |
| quem renova cada cliente? | 📊 `/prod_docs` avulso, nas **228**: exatamente **1** produtor com `indireto="F"` (a caixa "Ind." desmarcada) por apólice — **228/228**; o nome dele tem FECHADOR/A em **224**, sem rótulo em 4. A regra da administração ("o desmarcado é o fechador direto", prévia de 06/10) **está confirmada pela API** |
| o código de hoje acha esse dono? | 📊 **NÃO.** O `produtor` de `/renovacoes` = o `ordem 1` em 227/228 e = o desmarcado em só **27/228**; o desmarcado está na ordem 1 em 26, 2 em 99, 3 em 48, 4 em 53. O `prod_docs` embutido em `/renovacoes` vem reduzido (só ordem 1 e 2, sem `indireto`). `fonte_infocap.py:529` e `:566` usam `ordem == 1` como "produtor direto" — serve ao ranking de produção, **é errado para dono da renovação** |
| quantos donos? | 📊 9 fechadores distintos carregam as 228 do mês; os 5 maiores: 88 · 32 · 29 · 26 · 19 |
| custo de ler | 📊 1 chamada `/prod_docs` por apólice (228 em sequência, 0 erro); a armadilha de concorrência (1 em 10 paralelas → 500) já está em `fonte_infocap.py` |

**Resposta ao Founder:** está claro O SUFICIENTE para não errar o dono — o campo `indireto` decide 228 de 228 —, **desde que** (1) o
sistema leia o `/prod_docs` avulso (não o `/renovacoes`), (2) a corretora diga uma vez quais códigos de produtor são de qual pessoa
da equipe (o papel é convenção de nome, não dado), e (3) o vínculo produtor → pessoa → Agger seja configuração, não código. O que a
InfoCap NÃO diz: qual usuário do sistema é cada produtor, se o produtor ainda trabalha na corretora, e quem NEGOCIA (o
`codusu_responsavel` existe em `/negocio`, mas 📊 `/negocios_andamento` de 01/09 a 10/10 devolveu 404 = vazio; não medido).
**Não medido:** a InfoCap da AutoFleet (não há conexão `connected` dela hoje) — a 131-0 mede na abertura se o padrão se repete.

### 2.4 As situações de entrada (apólice, cotação em mãos, preço, nada)
Mapa completo em [`SITUACOES-DE-ENTRADA-DA-COTACAO.md`](../programa-multicalculo/SITUACOES-DE-ENTRADA-DA-COTACAO.md).

---

## 3. Todas as variáveis (as que o Founder citou e as que ele não citou)

Cada uma com a recomendação; as que pedem escolha viram decisão no §5.

**Pessoas e carteira**
- V1 · **comercial que sai da corretora:** o membro é desativado → a conta Agger dele é pausada e a senha APAGADA do cofre; as
  renovações cujo dono é um produtor sem membro ativo caem na fila "sem dono" (Agger global + aviso ao admin) até a corretora
  reatribuir os códigos de produtor (na InfoCap, a carteira continua no nome antigo até alguém mudar o repasse). D-131-0-15.
- V2 · **férias / substituto:** o membro tem `substituto` + período; a renovação continua calculada no Agger do DONO (é lá que ele vai
  conferir na volta) e o AVISO vai ao substituto; na cotação do chat, quem pede é quem conta. D-131-0-16.
- V3 · **dois comerciais no mesmo cliente:** o dono é por APÓLICE (o desmarcado daquela apólice), não por cliente — o auto pode ser da
  Mariana e o residencial da Karina. D-131-0-18.
- V4 · **produtor sem membro:** indicador externo, parceiro, "corretora" (📊 3 nomes com CORRETORA) → nunca vira usuário; se for o
  desmarcado, a apólice cai na fila "sem dono".
- V5 · **membro sem produtor:** admin, financeiro, atendente → usa o global em toda cotação (R4).
- V6 · **uma pessoa em duas corretoras** (📊 6 de 10 vínculos são de quem tem mais de uma): o Agger do membro é por
  (pessoa, corretora); trocar a corretora ativa troca o Agger. Nunca um login de uma corretora calcula para a outra (o Agger já
  amarra: um login enxerga uma corretora só).
- V7 · **o dono muda no meio** (o repasse é editado depois do cálculo): o dono é relido no disparo e na entrega; mudou → o cálculo
  feito fica, o aviso vai ao novo dono, e o novo cálculo (se houver) sai no Agger dele.
- V8 · **várias filiais** (`codfil` na InfoCap): o vínculo produtor ↔ membro leva `codfil`.
- V9 · **quem calcula ≠ quem negocia ≠ responsável pelo cliente** (R19): três funções configuráveis por corretora (e por ramo:
  condomínio e empresarial costumam ir ao responsável). D-131-0-24.
- V10 · **"calculista" que não fala com cliente** (Resulta): função de membro sem canal de negociação.

**Sistema de gestão**
- V11 · **corretora sem sistema de gestão:** sem fonte de renovação automática → importação de planilha (vencimento, CPF/CNPJ, placa,
  dono) ou "renovação sob pedido" no chat. D-131-0-13.
- V12 · **sistema diferente (Quiver, Segfy, outros):** cada um vira um ADAPTADOR que entrega a MESMA forma (`apólice a renovar` +
  `participantes com papel cru` + `dono segundo a regra`), no molde da `PolicyDataProvider`; a regra de dono é dado da corretora
  (`fonte`, `campo`, `valor`) — ex.: InfoCap `indireto = F`; outro sistema "o produtor de papel X", "o vendedor", "a carteira fixa".
  Nenhum nome de papel no código (R7).
- V13 · **papéis com nomes diferentes** ("Comercial 1, 2, 3"): o papel cru é procedência (como já faz `producer-roles.*.json`), a
  decisão é a regra da corretora.
- V14 · **o sistema fora do ar / credencial vencida:** a renovação do dia não roda e o admin é avisado; nunca "segue sem dono".

**Agger**
- V15 · **sessão única** (o robô no login de uma pessoa derruba a pessoa): D-131-0-05.
- V16 · **Agger do comercial com senha vencida ou bloqueado** (o Founder perguntou: *cair para o global ou parar?*): para a RENOVAÇÃO,
  para e avisa o dono e o admin; só cai para o global quando o vencimento estiver a menos de N dias (💭 padrão 5, config), e diz
  isso no aviso; para a COTAÇÃO do chat, pergunta a quem pediu ("seu Agger recusou a senha; calculo no da corretora?"). 1 tentativa,
  nunca insistir (E19: bloqueio por tentativas). D-131-0-17.
- V17 · **licenças:** cada Agger de pessoa já é uma licença paga (📊 Resulta 5 licenças, 6 usuários ativos em 04/10); um usuário-robô
  POR comercial seria uma licença a mais por pessoa — custo novo = parada §10(7) do CLAUDE.md, decisão do Founder.
- V18 · **o negócio criado pelo robô no Agger da pessoa:** marcado como do AutoBrokers (D-MC-47); se a pessoa mexeu há menos de 24 h,
  o robô não recalcula por cima (já é regra, `agger_robo.py:675-686`).
- V19 · **a renovação que a comercial JÁ calculou à mão:** não duplicar — antes de criar, procurar negócio do mesmo CPF/placa na
  janela (📊 E2: 2 de 3 renovações da Resulta já tinham negócio no Agger).
- V20 · **afinidade do recálculo:** hoje o recálculo volta a "qualquer robô da corretora" (D-MC-41); com dono, volta à MESMA conta
  (senão o ajuste aparece no Agger de outra pessoa). O `somente` de `robos.escolher` já existe (`robos.py:244-262`).
- V21 · **as seguradoras configuradas no contrato** (senhas das seguradoras são da conta; 📊 Resulta 14 e AutoFleet 15 ativas): se o
  Founder confirmar que cada usuário vê a mesma configuração, o Agger do membro não muda QUEM cota, só ONDE o negócio fica. A medir.
- V22 · **o QCM nunca usa conta de membro** (o lead é frio, R18) e a conta global nunca é a de uma pessoa (D-MC-24).

**Serviços e canais**
- V23 · **o mesmo cliente pede pelo QCM e é da carteira:** o QCM nunca sinaliza "já é cliente" (§6.3 do plano, D-MC-46); cruzar o CPF
  do lead com a carteira de uma corretora é decisão de LGPD → não cruzar no piloto. D-131-0-19.
- V24 · **o lead do QCM que fecha:** vira cliente da corretora vencedora; QUEM recebe a passagem (rodízio entre comerciais, uma pessoa
  fixa, a fila do Inbox) é config da corretora no serviço QCM.
- V25 · **o admin pedindo pelo WhatsApp pessoal com áudio + apólice** (R13): identidade pelo número verificado do membro; a mesma
  ferramenta de cotação do chat (132), o mesmo Work Run com `requester_user_id`, a resposta no mesmo WhatsApp. Exige 130-B (apólice) e
  a transcrição que já existe (`audio_service.py:195`).
- V26 · **o WhatsApp pessoal do comercial conectado** (para NEGOCIAR em nome dele, R12): o agente veria TODAS as conversas pessoais do
  número → só lê/escreve as conversas abertas por um trabalho do AutoBrokers; o resto é descartado na entrada (como o observer já faz
  com conversas pessoais — memória 097.1). Privacidade e risco de bloqueio do número são do membro, com aceite dele.
- V27 · **negociação ligada/desligada** por serviço e por corretora (R11), com exceções por ramo e valor (💭 "condomínio sempre com
  humano" — a memória do plano 121/122 já registra condomínio/empresarial com humano).
- V28 · **quem recebe o aviso** e por onde (painel/Inbox, WhatsApp interno, e-mail), preferência por membro. D-131-0-21.
- V29 · **o que fica no Agger para conferir de manhã** (R20): o negócio com rótulo padrão (💭 "AutoBrokers · renovação · vence
  dd/mm"), as versões padrão + econômica + "igual à atual", e no painel a lista do dia com o link do negócio. D-131-0-22.
- V30 · **preferências de seguradora por ramo** (R16): afetam QUAIS seguradoras entram no cálculo e a ORDEM da recomendação na carteira;
  no QCM nunca mudam o "quem cobra menos" (a promessa é preço, CDC art. 37). D-131-0-12.
- V31 · **regras do manual de renovação por ramo** (R17: +15 % na básica; antecedência — o Founder disse "10 dias antes", a config de
  hoje diz 15, `config.py:49`; comissão +1–2 pp sobre o ano anterior) → seção `renovacao` por ramo, nunca constante.
- V32 · **apólice cancelada, sinistrada, já renovada** (`renovacao_situacao`, 📊 21 de 228 com situação 2; `sin_situacao`): o manual
  diz se calcula, pula ou só avisa.

**Permissão, LGPD e auditoria**
- V33 · **quem vê o cálculo de quem:** o comercial vê os seus; o admin vê todos; o calculista vê os atribuídos; outro comercial, não
  (config da corretora). `work_runs.visibility/owner_user_id` já existem. D-131-0-20.
- V34 · **o nome do produtor é dado pessoal:** o vínculo fica no banco do tenant, nunca em arquivo versionado — 🔴 hoje existe
  `backend/app/data/providers/infocap/producer-roles.resulta.json` (vazio, mas com o nome da corretora no arquivo: CLAUDE.md §13.9)
  → migra para o banco nesta SPEC.
- V35 · **a senha do Agger do membro:** cofre (Fernet, como `portal_accounts.secret_encrypted`), nunca reaparece na tela, nunca em log;
  quem pode trocar: o próprio membro e o admin. D-131-0-06.
- V36 · **auditoria:** todo cálculo grava quem pediu, por qual serviço, qual conta foi usada, POR QUE (a regra que decidiu) e se houve
  fallback. D-131-0-23.
- V37 · **o número do membro como identidade** (R13): telefone verificado por código uma vez; sem verificação, o número é só contato.

---

## 4. A arquitetura proposta

### 4.1 Onde cada regra mora (resposta ao R10)

```
CORRETORA (organização)                    ← "workspace"
 ├─ Sistema de gestão (conexão company)    InfoCap · Quiver · nenhum  + a REGRA DE DONO (dado)
 ├─ Agger GLOBAL (conexão company)         QCM · quem não tem Agger próprio
 ├─ WhatsApp da corretora (integração)     atendimento · negociação "da casa"
 ├─ Preferências por ramo                  seguradoras principais (padrão para os 3 serviços)
 ├─ MEMBROS (pessoas)                      papel de ACESSO (dono · admin · membro · atendente)
 │   ├─ funções de TRABALHO                comercial · calculista · negociador (várias por pessoa)
 │   ├─ vínculo com o sistema de gestão    códigos de produtor (N), por filial
 │   ├─ Agger do membro (conexão user)     o login DELE, no cofre, com janela
 │   ├─ WhatsApp do membro                 PEDIR (número verificado) · NEGOCIAR (instância dele, opcional)
 │   └─ preferências                       aviso por onde · substituto · horário
 └─ SERVIÇOS = AUXILIARES (catálogo global → instalação da corretora)
     ├─ Quem Cobra Menos   manual próprio · Agger global · sem dono · passagem configurável
     ├─ Cotação            manual próprio · Agger de QUEM PEDIU (senão global)
     └─ Renovação          manual próprio · Agger do DONO segundo a regra (senão a fila sem dono)
         cada um: chave  calcular-só | calcular + entregar | calcular + entregar + negociar
```

A regra que decide: **o QUE fazer** (manual, chave de negociação, preferências do serviço) mora no **serviço** (Auxiliar, R14);
**COM QUAL conta** mora na **pessoa e na corretora** (conexões); **DE QUEM é o cliente** mora no **sistema de gestão + vínculo**. Isso
segue a `ONTOLOGIA-DO-TRABALHO.md` (Auxiliar = quem faz; três camadas global → corretora → usuário, o de baixo sobrepõe o de cima) e
a `CAMADAS-DE-CONEXAO.md` (o Agger global é `company`; o Agger do membro é o primeiro conector `user` do produto).

### 4.2 A regra de qual Agger usar (uma função, um lugar)

```
qual_agger(corretora, servico, pedido) →
  QCM        → a conta GLOBAL da corretora (ou a "do serviço", se a corretora marcar uma) — nunca de membro
  Cotação    → a conta do MEMBRO que pediu (work_runs.requester_user_id), se ativa
               senão → a GLOBAL (R4) — e diz "calculei no Agger da corretora"
  Renovação  → dono = regra_de_dono(sistema de gestão, apólice)   ex.: InfoCap /prod_docs indireto = F
               membro = vínculo(dono.codigo_produtor, codfil)
               conta do membro ativa → ela  ·  sem membro/sem conta → fila "sem dono" (global + aviso ao admin)
               conta recusou senha → para e avisa; global só se vence em < N dias (V16)
  Recálculo  → a MESMA conta do cálculo de origem (V20)
  sempre     → grava {quem_pediu, servico, conta, regra, fallback}  (V36)
```

O motor (`robos.escolher`) ganha um filtro de USO: o QCM passa `uso=global`; a cotação e a renovação passam `conta=<id>` (o
`somente` que já existe). O rodízio continua valendo entre contas do MESMO uso (dois robôs globais da corretora).

### 4.3 O que se reusa (CLAUDE.md §5 — nenhum motor paralelo)

| peça existente | papel na 131-0 |
|---|---|
| `company_members` + `invites` + BFF de empresa ativa (SPEC-047/048/098) | o membro e o convite; ganha funções de trabalho, não uma tabela de "comerciais" solta |
| `portal_accounts` + cofre + `robos.py` (lease CAS, janela, teto) + o conector Agger da 133-A.1 (F3) | o Agger global E o do membro: mesma tabela, com `uso` e `dono` |
| `tenant_connections` + `connector_templates.scope` (`company`/`user`) + `ConfigureInfocapModal` | o sistema de gestão (InfoCap; Quiver depois) e a camada `user` |
| `PolicyDataProvider` + `infocap_policy_provider.apolice_do_pack` (`:380`) + `fonte_infocap` | a apólice a renovar e os participantes; um método novo "dono da apólice" lendo `/prod_docs` avulso |
| `integrations` (hub de WhatsApp, Evolution GO) + `company_internal_numbers` | o WhatsApp do membro (dono = pessoa) e o número verificado do membro |
| `auxiliary_templates` / `tenant_auxiliaries` (`renovacao-maxima` já no catálogo) + `work_runs` | os três serviços e a execução; `requester_user_id` já existe |
| `multicalculo_config` (`config.carregar`) | vira o padrão POR SERVIÇO (`canal`, `cotacao`, `renovacao`) + a parte comum declarada |
| aprovações/notificações do Work OS + Inbox do operador (133-A) | o aviso ao comercial |

### 4.4 Os usuários: vale reestruturar? (R21)

| opção | o que é | nota |
|---|---|---|
| A · reestruturar tudo agora (workspaces, grupos, papéis customizáveis, SCIM) | o "Teams completo" | **55** — escopo enorme, nenhuma SPEC da fila precisa de grupo customizado |
| **B · incremental e fechado** | papéis de ACESSO fechados (dono · admin · membro · atendente) + FUNÇÕES de trabalho (comercial · calculista · negociador) + vínculo com produtor + conexões `user` + preferências; uma só fonte do papel (`company_members`; `users_v2.role/company_id` viram leitura legada); convite por link no lugar da senha `mudar123`; os leads saem do caminho dos usuários numa SPEC própria | **85** |
| C · não mexer | o comercial vira um campo solto em `multicalculo_config` | **30** — reproduz o "desconexo" que o Founder sentiu |

**RECOMENDAÇÃO: B.** Grupos ("equipe de condomínio") ficam para quando uma corretora pedir — o desenho de B não os impede.

### 4.5 Diagrama do fluxo (renovação, o caso mais completo)

```
Rotina diária do Auxiliar de Renovação (por corretora)
  → sistema de gestão: apólices com fimvig na janela do RAMO (manual da renovação)
  → para cada apólice: /prod_docs → dono (regra) → membro (vínculo) → conta Agger (qual_agger)
  → dedupe (V19) → pedido ao motor (origem 'auxiliar', conta = a do membro, manual: +15 % básica, comissão +1–2 pp…)
  → motor: lease da conta do membro (janela/sessão, D-131-0-05) → cálculo padrão + econômica + "igual à atual"
  → proposta (130-A, página de RENOVAÇÃO — não a do QCM, D-133A1-01)
  → chave do serviço:
       calcular-só        → aviso ao dono (V28) · o negócio fica no Agger dele · lista no painel
       + entregar         → manda ao cliente pelo WhatsApp de quem negocia (V9/R12)
       + negociar (135)   → o agente conversa em nome do negociador, com as regras de parada
  → auditoria (V36)
```

---

## 5. As decisões

**Precisa ser decidido JÁ** (antes de a 129-C ou a F3 desta SPEC irem para a `main`):

| id | decisão | opções e notas |
|---|---|---|
| **D-131-0-04** | Até a 131-0 existir, **a corretora tem UMA conta Agger pela tela: a global**. A tela da 133-A.1 não oferece "adicionar outro Agger". Motivo 📊: `robos.candidatos` pega toda conta `agger` com `robo_estado` da corretora (`robos.py:215-224`) — um Agger de comercial entraria no rodízio do QCM e o lead frio sairia no Agger da Mariana | **uma conta só até a 131-0: 92** · permitir várias e confiar no rótulo: 20 |
| **D-131-0-03** | **O dono da renovação, na InfoCap, é o produtor com `indireto = "F"` no `/prod_docs` avulso** — nunca o `ordem 1` nem o `produtor` de `/renovacoes` (📊 errados em 201 de 228). Registrar já para que nenhuma SPEC (129-C, 131) construa sobre o `ordem 1` | **95** (já vem decidida pela medição) |
| **D-131-0-25** | A posição na fila (§8): **parte A logo depois da 129-C, antes da 130-B e da 131**; parte B com a 132 | **88** · antes da 129-C: 60 (a 129-C não depende) · só antes da 131, depois da 130-B: 80 |

**Pode esperar a abertura da 131-0** (o chat dela decide com as medições do BLOCO 0):

| id | decisão | opções e notas |
|---|---|---|
| D-131-0-01 | o comercial é uma FUNÇÃO do membro da corretora (`company_members`), não um tenant nem uma tabela à parte | 92 · tabela "comerciais" separada 40 |
| D-131-0-02 | vínculo membro ↔ produtor: N códigos por membro (📊 10 pessoas com >1 código), por filial, configurado numa tela da corretora com SUGESTÃO por nome (nunca automático sem confirmar) | 90 · automático por nome 45 |
| D-131-0-05 | **calcular "no Agger da Mariana" com sessão única** — (a) login dela pelo robô numa JANELA (💭 noite) com a guarda de sessão ativa = Cancelar e parar; serve à renovação ("confere de manhã") · (b) um usuário-robô por comercial (licença nova por pessoa) · (c) calcular no global e TRANSFERIR o negócio para o usuário dela, SE o Agger permitir (o negócio tem `usuarioId`, `agger_robo.py:295`) · (d) global + aviso (a prévia de 06/10) · (e) na cotação do chat, de dia: entrar no login de quem PEDIU com o aceite dele ("sua sessão no Agger vai cair; posso?") | (c) 💭 88 se existir — **medir no BLOCO 0** · (a) 82 para renovação · (e) 78 para cotação · (b) 60 (custo §10.7) · (d) 50 (o Founder pediu "dentro do Agger dela"). Revê a D-MC-24 só para a conta do PRÓPRIO membro, com janela ou aceite — nunca a conta de outra pessoa |
| D-131-0-06 | a senha do Agger do membro: o próprio membro conecta no perfil dele; o admin também pode cadastrar por ele; a senha nunca reaparece | ambos 88 · só o admin 70 · só o membro 75 |
| D-131-0-07 | a ordem guiada (R9): sistema de gestão → Agger global → membros e Aggers → serviços; cada passo pode ser pulado e mostra o que falta | 88 |
| D-131-0-08 | os serviços como Auxiliares do catálogo: Renovação (`renovacao-maxima`), Cotação (zero rotinas: só chamado pelo chat/WhatsApp), Quem Cobra Menos (visível só às corretoras com adesão em `multicalculo_adesoes`) | 88 · só adesão sem Auxiliar 60 |
| D-131-0-09 | o manual por serviço: `multicalculo_config` vira padrão POR SERVIÇO; uma regra "comum" só existe se o Founder mandar (R14) | 90 |
| D-131-0-10 | a chave calcular-só × entregar × negociar: por serviço e corretora, com exceções por ramo e por valor | 85 · só por corretora 60 |
| D-131-0-11 | o WhatsApp do membro em DOIS usos separados: PEDIR (identidade pelo número verificado, conversa com o número do AutoBrokers) e NEGOCIAR (instância do número dele, opcional, com aceite) | separados 90 · um só (instância) 55 |
| D-131-0-12 | preferências de seguradora por ramo: na corretora (padrão para os 3 serviços), sobreposta por serviço; no QCM só escolhem quem é consultado, nunca reordenam preço | 86 · só no serviço 70 |
| D-131-0-13 | corretora sem sistema de gestão: importação de planilha para a renovação | 70 · nada até pedirem 60 |
| D-131-0-14 | usuários: opção B do §4.4 | 85 |
| D-131-0-15 | comercial que sai (V1) | 90 |
| D-131-0-16 | férias: cálculo no Agger do dono, aviso ao substituto (V2) | 80 · no Agger do substituto 65 |
| D-131-0-17 | Agger do membro recusou a senha (V16) | parar + global só perto do vencimento 85 · sempre global 55 · sempre parar 70 |
| D-131-0-18 | dono por apólice, não por cliente (V3) | 92 |
| D-131-0-19 | QCM × carteira: não cruzar CPF no piloto (V23) | 80 · avisar o dono 50 |
| D-131-0-20 | visibilidade (V33) | 85 |
| D-131-0-21 | aviso por preferência do membro (V28) | 85 |
| D-131-0-22 | o que fica no Agger e no painel (V29) | 88 |
| D-131-0-23 | auditoria obrigatória (V36) | 95 |
| D-131-0-24 | três funções (calcula · negocia · responsável) configuráveis por corretora e ramo (V9) | 80 |

---

## 6. As fatias de execução (quando a 131-0 for executada)

**Nível:** CRÍTICO (piso §3.2: migration que muda QUEM PODE LER e o filtro `company_id`; senha de pessoa no cofre; o canal que
envia). Parte A ≈ 💭 G, 4–5 fatias; parte B ≈ 💭 M, 2 fatias.

| fatia | entrega | arquivos (previsão) |
|---|---|---|
| **BLOCO 0** (investigação) | no Agger: (1) dá para transferir um negócio entre usuários do mesmo contrato? (2) cada usuário vê os negócios dos outros? (3) as seguradoras configuradas são as mesmas para todos os usuários? (4) o aviso de sessão ativa num login de pessoa; na InfoCap: o padrão `indireto` na AutoFleet; `/produtores` tem inativos?; `codusu_responsavel` em `/negocio` | só leitura, guarda do Agger em modo leitura |
| A1 · membros | funções de trabalho, papéis fechados, convite no lugar de `mudar123`, uma fonte do papel | `app/api/dashboard/team/*`, `lib/admin/*`, migration de `company_members` |
| A2 · vínculo e regra de dono | tela "quem é quem no sistema de gestão" (sugestão por nome), tabela de vínculo, regra de dono por corretora, método `dono_da_apolice` lendo `/prod_docs`; o `producer-roles.resulta.json` migra para o banco | `providers/infocap_*`, `comercial/fonte_infocap.py`, tela nova em Personalização → Equipe |
| A3 · contas com dono | `portal_accounts` com `uso` e `dono`, `robos.escolher` filtra por uso, `qual_agger` único + auditoria, tela "Aggers da equipe" (o conector da 133-A.1 ganha "adicionar o Agger de um membro") | `portal_worker/multicalculo/robos.py`, `services/multicalculo/porta.py`, `api/portal.py`, `components/vault/*` |
| A4 · serviços | os 3 Auxiliares, config por serviço, chave de negociação, preferências por ramo | `services/multicalculo/config.py`, catálogo, tela do Auxiliar |
| B1 · pedir pelo WhatsApp (com a 132) | número verificado do membro → a mesma ferramenta de cotação do chat | `services/canal/*` ou webhook, `company_internal_numbers` |
| B2 · negociar pelo WhatsApp do membro (com a 135) | instância com dono = pessoa, filtro das conversas pessoais | `integrations`, hub |

**Gates:** dois tenants reais em toda fatia (CLAUDE.md §7) · mutação: o QCM pega conta de membro → VERMELHO; a cotação da Ellen
usa a conta da Mariana → VERMELHO; o dono vira `ordem 1` → VERMELHO na régua das 228 · a régua do dono reproduzida na InfoCap real
(📊 alvo 228/228 do mês) · nenhuma senha em log/arquivo/teste · `npm run test:rotas-montam` + `next start` com uma rota `/api/…`
(§9.1) · bateria sem regressão.

**Migrations previstas (sem SQL; cada uma com APPLY/VERIFY/ROLLBACK antes, `MIGRATIONS-AUTHORITY.md` antes de escrever):**
`portal_accounts` + `uso` + `dono_member_id` (FK composta com `company_id`) · tabela de vínculo membro ↔ produtor
(`company_id`, membro, sistema, `codfil`, código) · `company_members` + funções + substituto · `integrations` + dono-pessoa +
`purpose` do membro · `multicalculo_pedidos` + quem pediu + conta escolhida + motivo · a config por serviço (em
`tenant_auxiliaries.config` ou em `multicalculo_config` com chave de serviço — o BLOCO 0 escolhe) · telefone verificado do membro.

---

## 7. Riscos

- **O robô no login da pessoa enquanto ela trabalha** → ela perde o que digitava · D-131-0-05 + a guarda de sessão (Cancelar e parar).
- **O dono errado** → o cálculo aparece no Agger de outra comercial · regra `indireto` + vínculo confirmado + mutação.
- **Licenças** → custo por comercial · parada §10(7), só com o Founder.
- **LGPD** (nome de produtor, senha pessoal) · banco do tenant, cofre, nunca em arquivo.
- **WhatsApp pessoal conectado** → conversas pessoais lidas, bloqueio do número · D-131-0-11, filtro na entrada, aceite do membro.
- **A convenção de nome muda** · a regra usa `indireto`; o nome é só sugestão.
- **O escopo de usuários cresce** → a 131-0 vira um "Teams" · opção B, grupos fora.

---

## 8. Quando executar (confirmando a recomendação do gerente com fato)

**A recomendação do gerente — "antes da 131, porque a renovação calcula no Agger de cada comercial" — está CONFIRMADA e é preciso
ACRESCENTAR:** (1) a **132** também depende (R3: a cotação pedida pela Ellen sai no Agger dela; 📊 a porta não recebe quem pediu,
`porta.py:278`); (2) uma parte é **JÁ** (D-131-0-04, porque o conector da 133-A.1 é a porta por onde um segundo Agger entraria no
rodízio); (3) a **129-C não depende** dela (a 129-C muda o montador por ramo, não a escolha da conta) e deve só gravar o +15 % na
seção `renovacao` da config (D-133A1-06). Fila recomendada:

```
133-A.1 (agora) → 129-C → 131-0 parte A → 130-B → 131 → 132 (+ 131-0 parte B1) → 133-B → 135 (+ B2) → 136 → 137
                    (se o portão da 130-B abrir antes dos portões da 131-0, a 130-B passa na frente; a 131 exige as duas)
```

**Portões do Founder para a 131-0 (para ir juntando desde já):** a lista de comerciais de cada corretora e quais códigos de produtor
são de quem (a corretora sabe; a tela sugere); se cada comercial aceita o robô no Agger dele (janela? aceite?) ou se a corretora
prefere usuários-robô (licença); a InfoCap da AutoFleet conectada para a medição em dois tenants.

---

## 9. Referências

- Internas: ONTOLOGIA · CAMADAS-DE-CONEXAO · PLANO-COMERCIAIS-E-CONTAS · A-PROVA-DO-AGGER §2/§E1/§E2/§E14/§10 · PLANO-MESTRE §4
  (131, 132, 133-B, 135) e §5 · SPEC-047/048/098 · SPEC-052 §4.3/§8.3 · SPEC-053 §3.2/§9.1 (`OutcomeSpec.user_id`).
- Externa (§7.3; conhecimento geral, **conferir nas páginas oficiais na abertura**): Slack, Claude Team/Enterprise, ChatGPT
  Business/Enterprise — organização → papéis de acesso → grupos → conexões **habilitadas pelo admin e autenticadas por cada pessoa**.
  É o "Agger global (organização) + Agger do membro (pessoa)".
