# Relatório de execução — SPEC-131-A: a madrugada da renovação

**SPEC:** `docs/canon/specs/SPEC-131-A-a-madrugada-da-renovacao.md` · proposta `specs-propostas/SPEC-131-O-APLICATIVO-DE-RENOVACAO.md`
**Branch:** `spec/131-A-a-madrugada` · **base** `2cd6168` (= `origin/main`, 0 atrás, 0 pendente) · **final** ver §7 (push)
**Gerente:** Opus 5.5 · protocolo AAA v13.2 · nível CRÍTICO · todos os 14 subagentes declararam `claude-opus-5-5` na 1ª linha (D-131-32)

## 0.0 EXECUTION CARD
```
OUTCOME ........ todo dia, por corretora, antes das 7h: cada renovação que vence em ≤ 10 dias está CALCULADA no Agger certo ou
                 PENDENTE com o motivo à vista; nenhuma esquecida; o dia fica VERMELHO se a conferência achar uma que faltou
RISCO .......... 7 (alcance 2 · saiu do prédio 3 · todo dia 2)
SUPERFÍCIE ..... 2 (peça nova sobre motor/porta existentes)
PISO APLICADO .. CRÍTICO: migration de estrutura · sessão de terceiro (Agger da pessoa) · filtro company_id
NÍVEL .......... CRÍTICO · builders Opus 5.5 · juiz Opus 5.5 ‖ red team Opus 5.5 · lente do dado · confirmação
O FIO .......... tick → renovacao.preparar → lista + dono + ficha + perfil → de_apolice → porta(prioridade 7, madrugada) →
                 qual_agger → motor → estado derivado → conferência independente 05:30 → desvio 06:15 → aviso 06:45
PARALELISMO REAL F1 ‖ F2 ‖ F3 (arquivos disjuntos) → F4 costura → F5 perfil → F6 combustível; conserto C1 ‖ C2 (disjuntos)
UNIDADES ....... 6 fatias + 2 de conserto
COESÃO ......... máquina de estados + conferência juntas (F1); ramo + opções + CPF (F2); sessão + guarda + teto (F3)
TIME ........... 8 builders · 2 medidores do BLOCO 0 · 1 de design (para a 131-B) · juiz ‖ red team · confirmação · bateria
REFERÊNCIA ..... interna: test_a_maquina_de_lavar_vai_ate_o_fim.py · MIGRATIONS-AUTHORITY · CLAUDE.md §7; externa: SPEC §8
GATES .......... fio · 7 mutações · 2 corretoras · migration VERIFY · canário real · bateria
O ELO .......... "nada esquecido PORQUE a conferência relê a InfoCap": a conferência não importa o montador (guarda AST) e a mutação
                 "um item some" fica vermelha (📊 F1)
FAIXA DE RELÓGIO declarada 💭 4–6 h · real ≈ 16 h (18:29 de 12/10 → ~10:30 de 13/10): máquina com 📊 ~400 MB livres, coleta do pytest
                 de 7 a 30 min, e dois achados que a SPEC não previa (o perfil do segurado e o combustível) — ambos BLOCKER do outcome
```

## 1. Resumo executivo (FATO)
- 📊 **A primeira renovação real calculada pelo produto**: canário de 13/10 (AutoFleet, conta do robô), 2 renovações `calculada` com
  📊 16/15 e 21/22 ofertas nas duas opções, num processo isolado (o motor de produção não tocou: 6/6 cálculos com o dono do processo do
  canário, 0 de outro). A 3ª saiu recusada pelas seguradoras ("renovação não encontrada", FIPE, aceitação).
- **O que ficou construído:** a tabela `renovacoes` com a máquina inteira e os eventos, a lista do dia (com antecipação até 7 dias e teto
  de 12 por conta por noite — 📊 pico de 42 renovações de um dono num dia na Resulta), a conferência independente das 05:30, o desvio das
  06:15, o aviso das 06:45 pelo canal do briefing, o perfil do segurado montado da InfoCap (📊 fecha 10 de 15 AUTO), os 7 códigos de
  combustível do Agger, o "Prosseguir" de madrugada com 7 travas (só o id que o próprio aviso devolve), prioridade 7, teto de sessões,
  sessão da pessoa mantida, ausência/substituto, licença do Agger avisada, CPF/CNPJ inválido barrado antes da InfoCap em todo chamador,
  ramo desconhecido/moto/frota nunca viram carro.
- **Nada liga sozinho:** 📊 0 corretoras com o aplicativo instalado (`tenant_auxiliaries` slug renovacao = 0) — a madrugada só roda onde a
  131-B instalar o aplicativo. Nada é enviado a cliente.

## 2. Escopo por fatia (FATO — commits arquivo a arquivo)
| fatia | commit | entrega |
|---|---|---|
| SPEC + BLOCO 0 | `eb69098` `fc54f4a` `7c177c3` | SPEC executável; A1 (Prosseguir derruba SÓ aquela sessão), A2 (pico), A5 (`per_c` é da corretora, 20/20), A8, A9, B4–B7 |
| F1 | `0c5eb27` | migration, repositório com CAS, máquina, preparar/calcular/conferir/desvio/avisar, tick no fuso da corretora |
| F2 | `480e1f3` | ramo, as 3 opções pela ficha, comissão +1 pp, antecedência 10, CPF barrado |
| F3 | `96d178e` | porta (prioridade, política), qual_agger (ausência, desvio), guarda e sessão do Prosseguir, teto, licença |
| F4 | `a285269` | costura; achou 2 defeitos (chave interna da ficha; desvio sempre recusado) e o BLOCKER do perfil |
| F5 | `9f54c75` | o perfil do segurado da InfoCap, suposições marcadas; motor `ignorar_espera` só para pedidos nomeados (canário) |
| F6 | `3ac24ef` | combustível (7 códigos do bundle do Agger; FIPE supre); 1ª renovação calculada |
| conserto | `09c9efb` `babe4bf` `62f95a8` `0197596` + paginação | os 4 blockers + N1–N3 da confirmação + a regressão da bateria |

## 3. Arquivos alterados
📊 `git diff --stat 2cd6168..HEAD` → 42 arquivos, +10.890 / −125. Novos: `multicalculo/renovacao.py`, `madrugada.py`,
`conferencia_da_renovacao.py`, `perfil_da_renovacao.py`, `app/utils/documento_br.py`, a migration, 8 arquivos `test_spec131a_*`, 2 scripts.

## 4. Migrations
`20261013_01_spec131a_renovacoes.sql` — APLICADA pelo gerente via MCP, versão 📊 `20261013003843`. VERIFY do objeto 📊
`4·4·1·1·1·1·2·1·1·1·1·2·0` (igual ao esperado); VERIFY comportamental: 10/10 recusas e aceites certos, 0 linha restante. ROLLBACK escrito
no cabeçalho e RECUSA se houver dado (📊 há: 6 linhas `canario=true` da AutoFleet).

## 5. Testes
📊 os 8 `test_spec131a_*` + o guarda dos mil linhas: ver §5.1. Mutações vermelhas (cada uma restaurada por cópia): (1) item some ·
(2) conferência lê a lista congelada · (3) desconhecido → AUTO · (4) Prosseguir fora da janela / em conta global · (5) prioridade 5 ·
(6) estado reservado gravado · (7) econômica/mínima na renovação · + guarda aceitando outro `derrubaSessao` · + os 4 blockers do conserto
(confirmação: 📊 `2 failed` · `2 failed` · `6 failed` · `2 failed` com o conserto revertido).
### 5.1 Rodada final (depois da paginação)
📊 os 8 `test_spec131a_*` + o guarda dos mil: `1 failed, 214 passed in 1533.92s` — a falha era do PRÓPRIO conserto (a ordem dos eventos
ganhara desempate por id e mudava o "último evento"); corrigida e reexecutados os afetados: 📊 `37 passed in 1202.25s` (lista e
conferência + conserto C1 + o guarda dos mil linhas).

## 6. Canário e rollout
- **Canário real** (AutoFleet, 13/10, ≤ 3 AUTO + 1 não cotável, relógio injetado, D-131-31/35): 📊 F4 0 pedidos (achou o perfil) ·
  F5 2 pedidos, 64/64 recusas "informe o combustível" · F6 **2 calculadas**, 0/50 recusas de combustível. Custo de modelo 📊 US$ 0,00
  (`token_usage_logs` vazio no intervalo). Isolamento provado por SELECT. Linhas `canario=true` ficaram (limpeza é decisão do Founder).
- **Rollout:** Implantar `smith-api` → `smith-worker` → `portal-worker` JUNTOS (o motor antigo não conhece as opções novas — RT-P9). Nada
  roda até a 131-B instalar o aplicativo numa corretora.

## 7. Gate da SPEC
fio verde · 7 mutações vermelhas · 2 corretoras (filtro + RLS) · migration VERIFY · canário com cálculo real · juiz 72 → conserto →
confirmação **86** · bateria: 📊 m1 18 failed · 1835 passed / m2 22 failed · 4638 passed · triagem 32 iguais, 8 novas = 7 de carga/ambiente
(passam isoladas) + **1 regressão** (o guarda dos mil linhas: `renovacao.py` pedia 5000) → consertada com paginação em páginas de 1000
(o molde do `attendance_distiller`). Push: na resposta final ao Founder (saída do `git push` colada).

## 8. Mudanças além do texto da SPEC (CHANGE-ADDENDA)
ESSENCIAL: o **perfil do segurado** (F5) e o **combustível** (F6) — sem eles 📊 0 de 2 AUTO reais calculavam. ESSENCIAL: o motor ganhou
`ignorar_espera` só junto de `somente_pedidos` (o canário isolado do motor de produção). VALIOSA: licença do Agger lida de `/usuario/current`.

## 9. Decisões
D-131-29 retentativa de hora em hora (Founder) · D-131-30 teto 1 por corretora até medir A4 · D-131-31 canário com relógio injetado ·
D-131-32 todo subagente declara o modelo · D-131-33 teto 12/conta/noite + antecipar 7 dias · D-131-34 Prosseguir só com o id do aviso ·
D-131-35 canário na corretora de origem dos dados · D-131-36 licença avisada · **D-131-37** completude: `pendente(sem_conexao)` NÃO conta como
feito; `precisa_de_voce` conta (é pendência com motivo visível) — revê a fórmula da §4 (confirmação N4) · **D-131-38** moto revelada pela
placa vira `pendente(ramo_nao_cotado)` (fora dos cotáveis) · **D-131-39** a 3ª opção: `anterior` usa a franquia NORMAL quando a ficha não
a diz (marcada não conferida), a `franquia_reduzida` só cede quando a ficha prova que já era reduzida.

## 10. Riscos remanescentes
- O Prosseguir e a licença NUNCA rodaram ao vivo com o código novo (📊 0 eventos `licenca_agger`; 0 contas de pessoa) → canário depois do Implantar.
- P-131A-COMISSAO: 📊 10 recusas por comissão acima do máximo (Allianz, Sura, Zurich: 30 %) — falta teto por seguradora.
- O perfil supõe condutor = segurado e habilitação = idade − 18 (teto 10), marcados "não conferido"; o comercial confere antes de enviar.
- `falhou` definitivo e `precisa_de_voce` só voltam pela tela (131-B).

## 10.1 📋 CAIXA DO FOUNDER
- **Licença do Agger:** Resulta 📊 13/10 (hoje) e AutoFleet 📊 20/10 — renovar. Bloqueia? sim, a madrugada daquela corretora.
- **Implantar os 3 serviços juntos** (smith-api, smith-worker, portal-worker) — depois da 131-B, que é quem liga.
- **InfoCap das corretoras** (T-144) e **o vínculo produtor ↔ pessoa** (T-140): sem eles tudo cai no Agger da corretora, com aviso.
- **Aceite do Prosseguir** (T-156) por comercial — sem ele a política fica desligada naquela conta.
- **Conta da Ellen (AutoFleet):** pode ter ficado uma sessão do teste presa; se aparecer "sessão ativa", "Prosseguir" é seguro.

## 11. Impacto para o corretor
Quando o aplicativo for ligado (131-B): toda manhã, antes das 7h, o comercial encontra no Agger dele as renovações dos próximos 10 dias
calculadas, e um aviso: "N prontas no seu Agger · M pendentes (porquê) · K falharam · N calculadas de M cotáveis".

## 12. Estado do Master Plan
131-A entregue; a 131-B (o aplicativo, a página de renovação, o envio) segue NESTE chat (ordem do Founder). Pendências P-131A-*.

## 13. ROLLBACK da SPEC inteira
Código: `git revert` dos commits do §2. Banco: o ROLLBACK da migration recusa enquanto houver dado — apagar as linhas `canario=true` é
decisão do Founder (`delete from renovacoes where canario`).

## 📊 A BATERIA — quantas vezes ela rodou nesta SPEC
1 rodada inteira (em 2 metades, HEAD `62f95a8`) + reexecuções dirigidas depois do conserto (§5.1).

## §11 A TELEMETRIA (`python backend/scripts/medir_execucao_claude_code.py --sessao atual`, 13/10 ~10:40 local)
📊 executor 772 min · 145 turnos · pico 552 k · US$ 43,13 (API-equivalente) · **15 agentes, todos `opus-5-5`** · 1.714 turnos · US$ 262,17
no total. Maiores: F1 US$ 30,54 (pico 477 k) · F3 28,98 · F2 24,83 · F4 22,33 · F5 21,66. Achados por mecanismo: BLOCO 0 (pico, A1, licença) ·
costura F4 (2 defeitos + o BLOCKER do perfil, EXCLUSIVO do canário real) · F5 canário (combustível, EXCLUSIVO) · juiz 3 blockers ·
red team 1 blocker (EXCLUSIVO: o desvio) · confirmação N1–N3 · bateria 1 regressão (EXCLUSIVO). Rodadas da bateria: 1 inteira.

**Nota da execução: 86/100** (critério: o outcome provado com dado real × o que só roda depois do Implantar).
