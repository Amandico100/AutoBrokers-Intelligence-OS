# Plano — as comerciais, as contas do Agger e os WhatsApps de cada uma

> 06/10/2026 · gerente da SPEC-130-A.1 · **PLANO, não construção** (D-130A1-11). Entra com a **131** (o auxiliar de renovação é o
> primeiro que precisa dele). Pedido do Founder (06/10, noite): *"pense numa prévia de plano, deixe anotado; não construa agora"*.

## 1. O que o Founder descreveu
- Uma corretora tem várias comerciais (💭 na piloto: 4 pessoas), **cada uma com o próprio WhatsApp e o próprio login no Agger**.
- No InfoCap, a aba **Repasses** de cada documento diz quem participa do negócio. 📊 O print de 06/10 (apólice 100383) mostra 3
  linhas do mesmo agente: um **EXECUTIVO** e um **INDICADOR** com a caixa "Ind." **marcada** e uma **FECHADORA** com a caixa
  **desmarcada**. A regra dita pela administração: **"o desmarcado é quem cuida do negócio — o fechador direto"**. A mesma
  comercial pode ter dois tipos de fechador. Na renovação o InfoCap já traz o repasse parametrizado; no seguro novo, é manual.
- O auxiliar de renovação deveria **cotar no Agger da comercial dona do cliente**, **avisar a comercial** (painel ou canal) e, depois,
  mandar ao cliente e negociar.
- Outras corretoras terão regras diferentes: o desenho é **global**, a regra é **dado da corretora** (CLAUDE.md §13.9).

## 2. O que já existe (medido no código em 06/10)
| peça | onde | o que serve |
|---|---|---|
| papéis de produtor do InfoCap (EXECUTIVO · FECHADOR · INDICADOR) e o repasse apropriado | `backend/app/comercial/metricas/produtores.py`, `fonte_infocap.py`, capability `financial.producer_repasse_accrued` | já lê QUEM participa de cada apólice e quanto recebe |
| mapa de produtor curado por gente (nasce vazio, de propósito) | `backend/app/data/providers/infocap/producer-roles.resulta.json` (SPEC-094 F) | a forma do vínculo pessoa ↔ papel, sem inventar vínculo trabalhista |
| contas de portal por corretora, com estado, teto e janela | `portal_accounts` (129-B) + `resolver_conta` + afinidade da conta onde o negócio nasceu (D-MC-41) | várias contas do Agger por corretora já cabem no modelo; o rodízio entre logins da mesma corretora está provado em teste (D-MC-40) |
| WhatsApp por corretora (hub, QR, saúde) | `app/dashboard/personalizacao/corretora/whatsapp/` + `app/api/vault/whatsapp/*` | uma conexão por corretora hoje |

## 3. O desenho proposto (para a 131)
1. **A comercial vira um "membro comercial" da corretora** (não um tenant): `company_id` + pessoa do time + o rótulo exato do
   produtor no InfoCap (a chave do vínculo) + o login do Agger dela (no cofre, nunca em texto) + o WhatsApp dela (uma conexão do hub,
   opcional) + o canal de aviso (painel, WhatsApp interno ou e-mail).
2. **A regra de dono é dado da corretora**, não código: `regra_do_dono = {"fonte": "infocap.repasses", "dono": "produtor sem Ind."}`
   para a piloto; outra corretora escolhe "o EXECUTIVO", "quem emitiu", "uma carteira fixa por comercial" etc. Sem regra → o pedido
   cai na conta-robô da corretora e no aviso geral.
3. **A conta do Agger usada no cálculo** = a da comercial dona (afinidade, D-MC-41); sem login dela → a conta-robô da corretora
   (T-120). 🔴 Login de pessoa no robô continua proibido no uso real (D-MC-24): **cada comercial que quiser o cálculo na conta dela
   cria um usuário-robô dela no Agger** (ou a corretora aceita que o cálculo saia na conta-robô e só o AVISO vá para a comercial).
   📊 A sessão do Agger é única por login — o robô no login de uma pessoa a derruba no meio do dia (o incidente de 06/10, `A-PROVA-
   DO-AGGER.md` §10).
4. **O aviso à comercial** usa o que já existe (aprovações/notificações do Work OS); a mensagem ao cliente sai pelo WhatsApp DELA
   quando houver conexão, senão pelo da corretora.
5. **Uma conexão de WhatsApp por comercial** = o hub de hoje com um "dono" a mais (a pessoa), nunca um motor novo (CLAUDE.md §5).
   O QR de cada uma é lido pela própria comercial, na conta dela no painel.

## 4. Decisões que a 131 vai precisar (com a nota de hoje)
| pergunta | recomendação | notas |
|---|---|---|
| o login do Agger da comercial: usuário-robô dela ou só a conta-robô da corretora + aviso? | **conta-robô da corretora + aviso à comercial dona** no começo; usuário-robô por comercial quando a corretora pedir | 80 × um robô por comercial já 60 (4 usuários novos no Agger, 4 senhas, 4 sessões) |
| onde a regra do dono mora | config da corretora (`multicalculo_config` ou tabela de membros) | 88 × constante 10 |
| o WhatsApp da comercial | opcional, no hub, dono = a pessoa | 82 × obrigatório 40 |
| o InfoCap: ler o "Ind." pela API | medir na abertura da 131 se a API devolve a caixa "Ind." do repasse (o print é da tela Windows) | — (medir antes) |

## 5. O que fica para depois
- A medição do "Ind." na API do InfoCap (leitura, sem escrita) — na abertura da 131.
- O seguro novo (repasse manual) — a regra cai na comercial que pediu o cálculo.
- A comissão por comercial (cada uma com a sua régua) — só se a corretora pedir; hoje a régua é da corretora.
