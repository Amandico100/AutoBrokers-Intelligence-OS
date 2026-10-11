# SPEC-133-A.1 — Quem Cobra Menos: os ajustes do Founder, o Agger da corretora no painel e o plano das contas · relatório

> 10/10/2026 · branch `spec/133-A1-qcm-ajustes` · base `9928ad3` · rito AAA v13, 🟠 ALTO · SPEC
> `specs/SPEC-133-A1-qcm-ajustes-do-founder.md` · retorno do Founder `programa-multicalculo/RETORNO-DO-FOUNDER-2026-10-10.md`

**Nota da execução: 88/100** (juiz 88 · red team 84, sem blocker; conserto curto dos achados P2/P3 com teste e mutação).

## EXECUTION CARD
```
OUTCOME ..............  carrossel e parcelas do QCM · "homem ou mulher?" só para nome ambíguo · o Agger da corretora pela TELA (a
                        conta global do robô) e a tela de conexões sem a confusão do "nova conexão" · as contas cotador@ medidas
                        · o plano da SPEC-131-0 e o mapa das situações de entrada · a senha "mudar123" fora do produto
RISCO ................  6 — ALCANCE 3 · REVERSIBILIDADE 2 · FREQUÊNCIA 1
SUPERFÍCIE ...........  2 — a tela de conexões das corretoras é tocada
PISO APLICADO ........  §3.2 — senha de portal gravada pela tela (cofre) · texto ao consumidor
NÍVEL ................  🟠 ALTO · gerente Opus 5.5 · builders Opus 5.5 em paralelo · juiz ‖ red team · conserto
O FIO ................  proposta (parcela_menor, parcela_sem_juros_maior) → página do canal (carrossel) e mensagem · conversa
                        (nome → sexo) · tela → rota → conta_do_robo (o serviço único) → portal_accounts/cofre → robos.escolher
PARALELISMO REAL .....  F1 ‖ F2 ‖ F3 ‖ F4 ‖ F5 (arquivos disjuntos) → julgamento → conserto
UNIDADES .............  F1–F5 (as do PARALELISMO acima)
COESÃO ...............  F1 página+mensagem+modelo · F2 conversa+dados · F3 conector+serviço+tela · F4/F5 documentos
TIME .................  gerente · builders F1 ‖ F2 ‖ F3 ‖ F4 ‖ F5 · juiz ‖ red team · conserto único · investigadores da bateria
REFERÊNCIA ...........  interna: o conector InfoCap (molde do card do Agger) e a página do canal da 133-A · externa: a tabela de
                        nomes do IBGE (Censo 2010)
GATES ................  pytest das fatias + regressão (290 no julgamento) · rotas montam · tsc · next build + next start + 401/200 ·
                        bateria inteira em 2 metades
O ELO ................  "a tela e o comando gravam o MESMO registro": um serviço só (`conta_do_robo.py`), testado nos dois caminhos
FAIXA DE RELÓGIO .....  💭 4–6 h · 📊 ~7 h
```

## 1. O que mudou
- **F1:** as opções do QCM lado a lado (scroll-snap; grade ≥ 880 px; até 4); cada cartão na ordem menor parcela → à vista → maior
  sem juros; a menor parcela vem de TODAS as formas de pagamento. 📊 A Youse do canário só traz até 4x (4 parcelamentos, sem juros);
  Tokio/Aliro/HDI/Zurich/Mapfre/Liberty/Azul trazem 12x — quando a seguradora traz, aparece. Achado: a régua antiga de "sem juros"
  (diferença < R$ 1) errava com centavos (Tokio 12x sai R$ 1,58 MAIS BARATO que o prêmio e era "com juros") — régua nova só no canal.
- **F2:** tabela do IBGE (📊 630 nomes, Censo 2010; cobre ~62 % da população); ≥ 70 % de um sexo → não pergunta (Mariana 0,4 % homem,
  José 99,6 %); Juraci 45 % → pergunta; declarado como assumido no pedido; o nome nunca vai ao modelo.
- **F3:** o card "Agger da corretora" no painel (login + senha → a conta GLOBAL do robô, ativa, janela padrão seg-sab 07–22; trocar
  senha, pausar/religar, horário, desconectar que apaga a senha); a tela e o comando usam o mesmo serviço; um login nunca em duas
  contas; a tela de conexões abre a conexão existente (nunca "nova" quando já há uma); InfoCap nova num gesto só. Revê a D-129B-11.
- **F4:** contas cotador@ medidas (A-PROVA §11): AutoFleet igual à da Ellen (15 seguradoras válidas, Bradesco agora válida); Resulta com
  HDI inválida, Mitsui ausente, Tokio sem login web, data de licença 13/10, permissões largas (T-136).
- **F5:** `specs-propostas/SPEC-131-0-CONTAS-COMERCIAIS-E-CONEXOES.md` (22 requisitos do Founder, 37 variáveis, 25 decisões, fatias,
  fila) e `programa-multicalculo/SITUACOES-DE-ENTRADA-DA-COTACAO.md` (16 situações). 📊 InfoCap: o dono da renovação é o produtor com
  `indireto="F"` no `/prod_docs` (228/228 renovações de 10/10–09/11); o código atual pega o produtor errado (27/228) — a 131-0 conserta.
- **Segurança:** a senha provisória de membro novo era sempre "mudar123" → aleatória, mostrada uma vez ao admin; o servidor recusa
  "mudar123" e senhas < 10. 📊 4 dos 7 membros com senha estão com "mudar123" (T-137).

## 2. Julgamento
juiz 88 (sem blocker) · red team 84 (R1 P2: o mesmo cotador@ em duas contas pelo comando + tela → duas sessões; R2–R4 P3) → conserto
com teste e mutação (66 passed; `a-senha-do-membro` 22/0) · §9.1: `next build` exit 0 · `next start` Ready · `GET
/api/dashboard/agger-da-corretora` → 401 · `GET /` → 200.

## 3. Bateria (1 rodada inteira: 2 metades em paralelo, worktrees no commit `f4edb0d`)
metade 1: `9 failed, 3128 passed, 3 skipped in 1084.50s` — 0 nova · metade 2: `34 failed, 2738 passed, 6 skipped, 31 xfailed, 1 xpassed
in 5095.72s` — 5 fora da linha de base: 4 passam isoladas (`4 passed in 48.78s`, carga/tempo) e 1 era o guarda do protocolo pedindo este relatório (resolvido). **0 regressão.**

## 4. Fora (com dono)
a 129-C (chat novo, prompt pronto em `specs-propostas/PROMPT-DE-ABERTURA-SPEC-129-C-PRONTO.md`) · a 131-0 (planejada) · a régua de
"sem juros" da carteira (precisa de ordem do Founder, D-133A1-01) · o nome editável da conexão do Agger (migration, 131-0) · os
membros com "mudar123" (T-137).

## 5. Entrega
O código e o relatório (push anterior, 10/10):
```
9928ad3..0860d31  HEAD -> main
```
O estado, a fila e o painel (`docs(133-A.1): estado, fila e painel`; painel republicado em
https://claude.ai/code/artifact/defe331c-9399-4584-9d1c-2126a527cea0, versão 33):
```
(saída colada abaixo, no commit seguinte)
```
