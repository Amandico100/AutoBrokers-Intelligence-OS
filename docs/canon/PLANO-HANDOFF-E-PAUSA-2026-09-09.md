# PLANO · o handoff chega e o agente cala quando a atendente fala (09/09/2026)

> Três defeitos do primeiro dia de piloto real (AutoFleet, Regina), investigados no código e no
> banco de produção (só leitura). **Nada de código foi executado ainda**; a única ação foi a correção
> de dados dos grupos (§0). Execução proposta em 4 unidades com builders Opus e o orquestrador como
> juiz, sem AAA (limite de tokens, D-PILOTO-06).

## 0. Feito hoje (dados, autorizado pelo Founder)

`human_support_destinations`: "Suporte AutoFleet" (`…05dc75`) movido da Resulta para a **AutoFleet**,
principal e ativo; "Grupo Suporte Resulta" (`…569c6f`) reativado como principal da Resulta. VERIFY pelo
motor real `resolver_destino_de_suporte`: AutoFleet → grupo …4@g.us · Resulta → grupo …6@g.us ·
`recusa=None` nos dois. ROLLBACK: antes, os dois estavam sob a Resulta; o da Resulta inativo.
⚠️ Efeito colateral esperado: as 5 conversas `HUMAN_REQUESTED` de hoje na AutoFleet têm re-alerta
a cada 6 h (`handoff_watchdog`) — o grupo pode receber dossiês antigos nas próximas horas.

## 1. Causas raiz (📊 medido 09/09)

| # | defeito visto | causa raiz | evidência |
|---|---|---|---|
| A | os dois grupos aparecem nas duas corretoras; "desativar" parece não fazer nada; AutoFleet sem destino | as 4 rotas de Suporte humano resolvem o tenant por `users_v2.company_id` (corretora **primária** do usuário = Resulta), não pelo seletor (`resolveSessionCompany`, SPEC-098) | `lib/attendance/support-destinations.ts:26-30`; GET/POST `app/api/attendance/support-destinations/route.ts:30,77`; PATCH/DELETE `[destinationId]/route.ts:30,114`; o DELETE **funcionou** (linha ficou `is_active=false` às 01:22) mas a tela lista `?active=all` sem marcar inativo |
| B | "vou chamar a equipe de sinistro" e ninguém recebe | AutoFleet com **zero** destinos nas 3 fontes → a ferramenta recusa mentir (`FALHA_DO_HANDOFF`) e marca `HUMAN_REQUESTED`; a falha só vai a `logger.error`, nada persistido | resolvedor rodado de verdade: AutoFleet `destino=VAZIO`; 5 conversas `HUMAN_REQUESTED` hoje, 0 `work_events claims.%` |
| B' | **cross-tenant latente**: até hoje à noite o único destino ativo da Resulta era o grupo da AutoFleet | consequência de A; o guarda de JID duplicado não pega linha no tenant errado | resolvido em §0 |
| C | o agente não para quando a Regina responde | **a pausa foi gravada na conversa errada**: chat endereçado por `@lid` (dispositivo vinculado / WhatsApp Web) → `normalize_evolution_inbound` usa `key.remoteJid` e o "telefone" vira um LID de 15 dígitos → nasce conversa-fantasma e a pausa cai nela; a conversa real segue `open` | `evolution_inbound.py:868`; 📊 as **5** pausas por intervenção de toda a história estão em conversas com `user_phone` de 15 dígitos; 11 mensagens de hoje espelhadas em duas conversas (real e fantasma) |
| C' | com o agente **desligado** nada pausa | `observer_tap` consome o evento antes do ramo `fromMe` quando o agente está desligado; ao religar, a conversa volta a ser do robô | `observer_intake.py:812-829`, `webhook.py:1622-1628`; 📊 430 `fromMe` humanas hoje, 11 tentativas de pausa |
| C'' | robô responde 6–8 s depois da Regina | corrida: a resposta já estava no buffer (8–25 s) quando ela escreveu; a pausa só é checada na entrada | 📊 2 de 14 respostas indevidas ≤ 25 s; 12 de 14 são pausa inexistente |

Fatos que mudam a leitura do dia: a Regina trabalhou pelo WhatsApp Web (📊 93% dos ids de saída no
formato multi-device) — a hipótese do Founder estava certa pelo motivo do `@lid`, não por evento
diferente; 0 mensagens pelo painel; `voz_propria` nunca foi exercitada (0 ecos do robô voltam pelo GO);
o robô cumprimentou "bom dia, começar o dia com você" às 11:40 na 30ª mensagem de um sinistro com vítima.

## 2. As regras de janela (recomendação)

**Princípio: a última palavra humana da corretora manda.** Não é "conversa de 15 dias"; é *quando foi a
última vez que uma pessoa da corretora escreveu nesta conversa*.

```
o agente responde ao segurado SE, E SÓ SE:
  1. não há intervenção humana da corretora nesta conversa nos últimos N dias
     (intervenção = fromMe humano pelo celular OU WhatsApp Web OU painel sem #nota;
      cada nova mensagem da atendente renova o prazo)
  2. e a conversa não está reivindicada na tela (claimed_by) — reivindicada só volta pelo botão
     "Devolver ao agente"
  3. e o agente está ligado
```

| situação do Founder | o que acontece |
|---|---|
| Regina começou há 3 dias, segurado volta hoje | há palavra humana < N dias → **agente cala** |
| Regina falou há 3 meses, segurado volta hoje | palavra humana > N dias → **agente atende como assunto novo** (cumprimenta, usa o histórico como memória: "vi que em junho falamos de…") |
| agente começou 09/09, foi desligado, religado 13/09, segurado escreve | nenhuma palavra humana → **agente continua** |
| agente atendeu 09/09, segurado volta 22/09 | nenhuma palavra humana → **agente atende**, sem confundir com a janela |
| Regina intervém numa conversa do agente | **cala por N dias contados da última mensagem dela**, renovado a cada mensagem; sinistro que ela conduz por semanas fica calado o tempo todo |
| Regina quer devolver antes de N dias | botão "Devolver ao agente" na Ficha/Conversas |
| Regina anota sem assumir | `#nota` no painel (só no painel; pelo WhatsApp chega ao segurado) |

Implementação sem migração: o gate `pausar_ia` (`o_fim_do_atendimento.py:~343`) passa a consultar a
última mensagem humana da corretora na conversa (`messages.role='assistant'` com `payload.origem in
('espelho','dashboard')` e não-nota) e compara com `agora − N dias`. Vale retroativamente para as 467
conversas antigas no instante em que o agente liga — sem varredura, sem coluna nova. `N` por env
`JANELA_SILENCIO_HUMANO_DIAS` com override por corretora em `acionamento_profile`.

**N = 7 dias: nota 82/100.** Assistência se resolve em 1–3 dias; quem volta depois de uma semana quase
sempre traz assunto novo; sinistro longo já está protegido pela renovação a cada mensagem da Regina.
**N = 15 dias: nota 60/100.** Protege um pouco mais o caso raro do segurado que retoma depois de 10 dias
o mesmo assunto, mas cala o agente em muitos contatos legítimos (a Regina fala com dezenas de segurados
por quinzena) e o custo é invisível: segurado sem resposta. Recomendo **7**, configurável, e medir na
primeira semana quantas conversas caem em cada lado.

## 3. Unidades de execução (Opus builders · orquestrador juiz)

| U | o quê | arquivos | gate |
|---|---|---|---|
| **U1 tenant** | `getCompanyId` → `resolveSessionCompany` nas 3 rotas (support-destinations GET/POST/PATCH/DELETE + infocap diagnostics); `null` → 401/403, nunca primária; tela marca "desativado" e mostra "esta corretora não tem destino — nenhum handoff sai" | `lib/attendance/support-destinations.ts`, as 3 rotas, `HumanSupportSettingsClient.tsx` | teste com **dois tenants reais**: CONTROLE sem seletor = primária; B selecionado → GET só B, POST grava B, PATCH/DELETE num id de A = 404 (hoje 200 → tem de ficar vermelho antes), vínculo revogado = 401. `tsc`, `rotas-montam` |
| **U2 pausa** | identidade única `telefone_do_evento(key)` (@lid → `remoteJidAlt`) usada pelos dois normalizadores; pausar pelo `conversation_id` que o espelho já devolve; `logger.error` + evento quando o UPDATE casa zero linhas; registro da intervenção **antes** do `observer_tap` (como a cobrança já faz); checagem da pausa **na saída** (antes de enviar) para matar a corrida ≤ 25 s; `saudacao_do_religamento` no caminho do WhatsApp; script de migração das ~30 conversas-fantasma LID com APPLY/VERIFY/ROLLBACK | `evolution_inbound.py`, `attendance_capture.py`, `webhook.py`, `espelho_chat.py`, `observer_intake.py`, script novo | testes: fromMe por `@lid` pausa a conversa REAL (controle `@s.whatsapp.net`); fromMe com agente desligado pausa; voz do robô não pausa; `#nota` não pausa (controle "#nota no meio" pausa); guarda de forma: nenhuma conversa nasce com `user_phone` sem `55`; **todos vermelhos no código de hoje** |
| **U3 janela** | regra §2 no gate `pausar_ia` + `JANELA_SILENCIO_HUMANO_DIAS` (default 7) + override por corretora; botão "Devolver ao agente" (já existe o release; conferir) ; "assunto novo" quando > N dias sem qualquer mensagem | `o_fim_do_atendimento.py`, prompt/graph (saudação de assunto novo), tela | teste com os 7 cenários da tabela §2, cada um com mutação (N=0 e N=∞) vermelha |
| **U4 rastro** | falha do handoff vira `work_events` (severity error) via `claims_shadow.registrar_evento`; guarda de configuração "agente ligado sem destino de suporte" (falha o `/health` + aviso na tela); histórico de liga/desliga do agente em `work_events`; `human_handoff_reason` NULL em 4/5 (investigar o ramo) | `human_handoff.py`, `main.py` (health), rota de ligar agente | teste: handoff sem destino deixa linha; `/health` acusa corretora ligada sem destino |

Ordem: U1 e U2 em paralelo (arquivos disjuntos) → U3 (depende do U2 para a origem das mensagens) →
U4. Juiz: gates acima + `test_098_builder_b_unit`, `test_quem_fala_primeiro_cala_o_outro`,
`test_ninguem_fala_com_o_segurado_sem_o_agente_ligado`, `test_handoff_chega_em_alguem` (hoje inspeciona
texto-fonte; migrar para chamar o motor). Deploy: smith-api → smith-web. 💭 Estimativa: 3–4 h de relógio,
≈ 600k tokens Opus, ≈ 80k do orquestrador.

## 4. O que o Founder faz

- Nada nos grupos: §0 já valeu. Confira na tela **depois do U1** (antes dele a tela continua mostrando a Resulta).
- Amanhã (Saionara, Resulta): o handoff da Resulta já resolve para o grupo certo. A pausa por intervenção
  **continua quebrada até o U2 subir**: se ela responder pelo WhatsApp Web, o robô pode continuar. Até lá,
  a forma segura de assumir é **clicar "Assumir" na Conversa do painel** (pausa por id, imune ao defeito).
- Decidir N (7 recomendado) e dar o "vai" das 4 unidades.

## 5. Fora do escopo, anotado para a fila

`normalize_evolution_inbound` erra também o telefone de entrada vindo de `@lid` (mesma bomba, outra
direção) · duas linhas duplicadas na Amandus · rota `admin/integrations` fora do helper canônico ·
CPF/placa em texto puro no corpo das mensagens (redação do `messages.content`) · o ramo `fromMe` do
webhook com 230 linhas e um teste que mede bytes de código.

## 6. Resultado da execução (09/09, noite)

**Commits na `main` a partir de `9e75d9f`:** `b1f6f57` U1 tenant · `c36e9a3` U5 membros ligam o agente ·
`1b64d81` U4 rastro do handoff + `/health` · `ba9688e` U3 motor da janela · `8dae4d4` U2 pausa ·
`0fa6e62` pendências 13–16 · `07ad723` U6 janela ligada nos portões · + este.

**Decisão do orquestrador:** N = **7 dias** (`JANELA_SILENCIO_HUMANO_DIAS=7`, override por corretora em
`acionamento_profile.janela_silencio_humano_dias`; `0` desliga). Trocar para 15 é uma variável no EasyPanel.

**Gates do juiz, em isolamento, árvore parada (📊 09/09 ~23h):** pytest de 6 arquivos `182 passed` ·
`test_a_atendente_fala_e_o_robo_cala` TUDO VERDE · `test_a_janela_esta_ligada_nos_portoes` TUDO VERDE ·
`test_o_handoff_que_falha_deixa_rastro` 22 verdes · `test_handoff_chega_em_alguem` rc=0 (agora chama o
motor, dois tenants) · `test_a_cobranca_chega_a_quem_deve` 169 ok · `test_quem_fala_primeiro_cala_o_outro`
TUDO VERDE · `test_ninguem_fala_com_o_segurado_sem_o_agente_ligado` rc=0 · `test_o_caso_se_explica_sozinho`
verde · `test_o_sinistro_deixa_rastro` 249 ok · `test_a_central_diz_a_verdade` 530 ok ·
`test_o_atendimento_sabe_como_terminou` verde · `tsc --noEmit` 0 · rotas montam (301) ·
`o-destino-de-suporte-e-da-corretora-selecionada` rc=0 · `o-membro-liga-o-agente` rc=0 ·
`admin-auth-policy` rc=0 · `cada-coisa-sabe-de-quem-e` rc=0. A suíte inteira não foi rodada (tokens).

**Implantação (🧑):** smith-api **e** smith-web (os dois mudaram). Depois: `/health` deve trazer
`corretoras_ligadas_sem_destino_de_suporte: []`; a tela Suporte humano da AutoFleet mostra só o grupo dela.

**Ficou:** P-PILOTO-13 (174 fantasmas LID + CHECK) · 14 (sombra de sinistro muda) · 15 (`resolvido_em` vs
pausa) · 16 (papel `attendant`) · `#nota` pelo WhatsApp ainda chega ao segurado (SPEC-090) · botão "Devolver ao
agente" na tela não foi conferido (o release existe na rota).
