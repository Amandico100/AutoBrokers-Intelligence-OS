# SPEC-133-A.1 — Quem Cobra Menos: os ajustes do Founder, o Agger da corretora no painel e o plano das contas

> v1.0 · 10/10/2026 · gerente Opus 5.5 · branch `spec/133-A1-qcm-ajustes` · base `9928ad3` (main) · rito AAA v13 · 🟠 ALTO
> Origem: o retorno do Founder de 10/10 depois da 133-A (texto integral guardado em `docs/canon/programa-multicalculo/RETORNO-DO-FOUNDER-2026-10-10.md`).

## 1. EXECUTION CARD
```
OUTCOME ..............  (1) a página do QCM com as opções LADO A LADO em carrossel; o cartão do vencedor e cada cartão com a MENOR
                        parcela no topo (12x quando a seguradora trouxer), depois o à vista, depois o maior sem juros — só no QCM;
                        (2) a pergunta "homem ou mulher?" só para nome ambíguo (≥ 70 % de um sexo pelo nome → não pergunta);
                        (3) o "Agger da corretora" vira um CONECTOR no painel (login e senha pela tela, como a InfoCap), que liga o
                        robô do multicálculo — e a tela de conexões sem a confusão do "nova conexão" quando já existe uma;
                        (4) as duas contas novas do Agger (cotador@) verificadas; (5) o PLANO detalhado das contas/comerciais/
                        Aggers/sistemas de gestão/WhatsApps/serviços (SPEC-131-0, só planejamento) e o mapa das situações de
                        entrada (apólice, cotação em mãos, só o preço, nada) na fila de SPECs.
RISCO ................  6 — ALCANCE 3 · REVERSIBILIDADE 2 · FREQUÊNCIA 1
SUPERFÍCIE ...........  2 — a tela de conexões das corretoras é tocada
PISO APLICADO ........  §3.2 — senha de portal gravada pela tela (cofre) · texto ao consumidor
NÍVEL ................  🟠 ALTO · gerente Opus 5.5 · builders Opus 5.5 em paralelo · juiz ‖ red team
O FIO ................  (1) proposta.montar (parcelas) → proposta_canal_html (carrossel) e mensagem_do_canal; (2) conversa.responder
                        (nome → sexo provável); (3) tela de conexões → rota → serviço de portal → portal_accounts (cofre) → o robô
                        do motor resolve a conta → calcularV2
PARALELISMO REAL .....  F1 página+mensagem ‖ F2 sexo pelo nome ‖ F3 conector Agger + UX de conexões ‖ F4 verificação das contas
                        Agger (ao vivo) ‖ F5 o plano (só documentos)
GATES ................  testes de cada fatia com mutação · a carteira byte a byte igual · `npm run test:rotas-montam` (F3) ·
                        nenhuma senha em log/arquivo/teste · dois tenants no conector · bateria sem regressão
FAIXA DE RELÓGIO .....  💭 4–6 h
```

## 2. Decisões (pela maior nota)
| id | decisão | notas |
|---|---|---|
| D-133A1-01 | regras de apresentação do QCM ≠ renovação ≠ cotação: cada serviço tem o seu manual/config; mudar um não muda os outros, salvo ordem explícita do Founder | 95 |
| D-133A1-02 | o sexo sai do primeiro nome por tabela do IBGE (Censo, frequência por sexo) quando ≥ 70 % de um lado; entre 30–70 % ou nome fora da tabela → pergunta | 88 |
| D-133A1-03 | **revê a D-129B-11:** com logins DEDICADOS de robô (cotador@), o Agger da corretora entra pela TELA de conexões (cofre), não mais só pelo comando. O login de PESSOA continua proibido para o robô | 85 × só comando 50 |
| D-133A1-04 | o "Agger da corretora" é a conta GLOBAL (QCM e quem não tem Agger próprio); os Aggers dos comerciais são da SPEC-131-0 | 90 |
| D-133A1-05 | a SPEC-131-0 (contas, comerciais, Aggers, sistemas de gestão, WhatsApps por usuário, calcular × negociar) é PLANEJADA agora e EXECUTADA antes da 131 (a renovação precisa do Agger de cada comercial) | 90 |
| D-133A1-06 | a 129-C (mais ramos) vai para um chat NOVO (este chat está no teto de contexto do CLAUDE.md §9), com o prompt pronto; os manuais da Resulta entram como atualização quando chegarem (a regra +15 % é config desde já) | 85 × esperar os manuais 60 |
