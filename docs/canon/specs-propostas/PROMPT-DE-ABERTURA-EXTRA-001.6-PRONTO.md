# PROMPT DE ABERTURA — EXTRA-001.6 (pronto para colar num chat novo do Fable, 14/09/2026)

Você é o executor da família EXTRA-001 do AutoBrokers, começando pela **EXTRA-001.6 — A cobrança prova que funciona**. Leia este prompt inteiro antes de qualquer ação.

## 0. Onde o projeto está (contexto que você não tem e precisa)

- O AutoBrokers é um SaaS multi-tenant para corretoras de seguros (FastAPI em `backend/app`, Next.js em `app/` e `lib/`, Supabase, Redis, Qdrant, MinIO, WhatsApp via Evolution, portal-worker Playwright, implantação pelo EasyPanel em três serviços: `smith-api`, `smith-web`, `portal-worker`).
- Duas corretoras-piloto: **Resulta** (atendente Saionara; residencial, condomínio, empresarial) e **AutoFleet** (atendente Regina; auto). Os pilotos de 09–11/09 foram "satisfatórios, não excelentes". O diagnóstico completo, com causas e linhas, está em `docs/canon/DIAGNOSTICO-PILOTOS-E-PLANO-EXTRA-2026-09-12.md`. Leia **§0, §7, §9, §12 e §13** dele (não o documento inteiro).
- **Neste momento está tudo pausado de propósito**: nenhum agente de atendimento ativo (`agents`: as linhas ativas são do chat principal; a linha "Amanda" está desligada), só 1 de 4 destinos de suporte ativos, `companies.agent_enabled=false` nas 5 empresas, rotina de cobrança da Resulta com `is_active=false`. Isso é o estado esperado enquanto as SPECs EXTRA-001.x são executadas. **Não ligue nada por conta própria.** Quando as SPECs necessárias estiverem no ar, o Founder reinicia os testes e libera o atendimento. Sua SPEC diz exatamente o que fica em espera.
- As decisões do Founder são lei: `docs/canon/FOUNDER-DECISIONS.md`, linhas **D-PILOTO-01 a D-PILOTO-20**. Para esta SPEC importam D-PILOTO-14, 18, 19 e 20.
- As senhas dos portais Allianz e Mapfre estão recusadas e **as novas só chegam em 15/09**. Isso não trava a SPEC (D-PILOTO-19): o bloco P0 e tudo o mais executam; o canário desses dois portais fica em espera nomeada no relatório e fecha quando a senha chegar.

## 1. O que você vai fazer, e como

A proposta já está escrita, revisada por um segundo agente e emendada. **Não converta, não reescreva, não reabra decisões.** Execute a proposta como está, medindo antes de codar (o BLOCO 0 dela) e registrando toda divergência entre a proposta e a árvore no relatório, nunca "consertando" a proposta para casar com o que encontrou.

Árvore: `C:\Users\amand\Projetos\AUTOBROKERS RESULTA\AutoBrokers-FIX`. Preflight obrigatório (CLAUDE.md §2): `git rev-list --count HEAD..origin/main` tem de ser 0; crie a branch `feat/extra-001-6-cobranca`. Python de dentro de `backend/`, `PYTHONIOENCODING=utf-8`.

**Leitura mínima, nesta ordem, e nada além disto antes de começar:**
1. `CLAUDE.md` inteiro.
2. `docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md` §0–§3 e §5.
3. `docs/canon/DIAGNOSTICO-PILOTOS-E-PLANO-EXTRA-2026-09-12.md` §0, §7, §9, §12, §13.
4. `docs/canon/specs-propostas/SPEC-EXTRA-001.6-a-cobranca-prova-que-funciona.md` (a proposta; manda) e `...-RESEARCH-PACK.md` (apoio).
5. `docs/canon/FOUNDER-DECISIONS.md`, só as linhas `D-PILOTO-*`.
6. `docs/canon/MIGRATIONS-AUTHORITY.md` (esta SPEC tem migrations).
7. A EXTRA-001 executada, que esta SPEC preserva: `docs/canon/reports/SPEC-EXTRA-001-EXECUTION-REPORT.md` (se não existir, a proposta em `docs/canon/specs-propostas/SPEC-EXTRA-001-operacao-dos-pilotos.md`).

Essa leitura é o seu aquecimento. Depois dela, escreva no chat, em 15 linhas, o que você entendeu que vai construir, em que ordem, e as 3 coisas que ainda não sabe e vai medir no BLOCO 0. Só então comece.

## 2. Autorização

- Números de teste: só os dois do Founder, chamados TESTE-A e TESTE-B. Os valores estão nas variáveis de ambiente do implantado (`JANELA_SILENCIO_EXCECOES` e a allowlist de canário descrita na proposta); nunca em arquivo, commit, relatório ou chat.
- Nenhuma mensagem a segurado ou seguradora real fora do canário descrito na proposta. O modo `equipe` da rotina só é ligado com `team_number` = TESTE-B.
- Banco de produção: leitura livre para medir (só contagens no relatório, sem CPF, CNPJ, telefone, nome de segurado); escrita só por migration com APPLY/VERIFY/ROLLBACK escritos antes, ou por escritor que já existe no produto.
- Portais das seguradoras: só `login_check` e leitura; nenhum efeito material.
- Segredos: nunca no chat, no relatório, no commit. Presença/ausência, só.

## 3. O laço (D-PILOTO-20; diagnóstico §13.7)

```
BLOCO 0   meça o que a proposta manda; divergência vira linha do relatório, não pergunta ao Founder
P0        o bloco implantável do 1º dia (bloco único, motivo da Mapfre, frases da Allianz medidas contra os
          prints reais, blocker do nome): construa, teste, commite, faça o push e ENTREGUE AO FOUNDER O COMANDO
          DE IMPLANTAR antes de seguir para o resto — o P0 é o que permite reativar a rotina
BUILD     os demais blocos, um a um, com os guardas da proposta (≤ 12, todos pelo motor sobre acervo real)
JUIZ      ao fim, um subagente Opus FRESCO (esforço máximo), que não viu o diff nascer, recebe: a proposta, o
          diff, a ordem de rodar os guardas e o canário vivo com TESTE-A/B, e três perguntas adversariais fixas
          (o que acontece com dado vazio ou nulo? com duas corretoras ao mesmo tempo? com a mesma mensagem
          duas vezes?). Devolve até 10 achados com prova e nota 0–100. Esta SPEC é CRÍTICA: acrescente UMA
          lente do dado (um segundo subagente que reconstrói os números da rotina sobre o acervo real)
CONSERTO  uma rodada. Achado não consertado vira pendência escrita em PENDENCIAS.md, nunca some
SUÍTE     bateria inteira com a árvore parada; saída real colada no relatório
ENTREGA   git push origin HEAD:main com a saída colada; comando de implantação por serviço; variáveis novas
          por nome (sem valor); rollback escrito
```

Sem aquecimento de 16 perguntas, sem painel de três lentes, sem red team, sem auditoria externa. **No máximo 3 subagentes ao mesmo tempo**, Opus 5 em esforço máximo para builders e juiz. Teto 💭 1 M tokens nesta SPEC. **Commite ao fim de cada bloco**: se a janela acabar, o que está em disco tem de estar salvo.

## 4. O que entregar

1. Código na `main` (push com saída colada).
2. `docs/canon/reports/SPEC-EXTRA-001.6-EXECUTION-REPORT.md` no template `docs/canon/reports/SPEC-EXECUTION-REPORT-TEMPLATE.md`, com EXECUTION CARD, testes com saída, canário com resultado, o que ficou fora e por quê (inclusive Allianz/Mapfre à espera da senha), pendências novas em `PENDENCIAS.md` (com dono e custo de esquecer), decisões novas em `FOUNDER-DECISIONS.md`, e a linha em `ESTADO-DAS-SPECS.md`.
3. Ao final do P0 e ao final da SPEC, uma mensagem ao Founder de no máximo 20 linhas: o que está no ar, **o que ele precisa fazer** (Implantar qual serviço; na tela do Auxiliar de cobrança: nome da atendente, modo `equipe`, `team_number` de teste, N=7 dias, e só então reativar a rotina), e a nota 0–100 com o critério.

## 5. Condições de parada (CLAUDE.md §10) e nada mais

Risco de perda de dados · decisão comercial · conflito canônico · P0/P1 de segurança ou cross-tenant · ação física do Founder · mudança material de escopo · custo extraordinário · falta de acesso. Fora disso: complete o bloco, rode o VERIFY, avance.

## 6. A sequência depois desta SPEC

Você vai executar as primeiras SPECs da família **neste mesmo chat, uma por vez, na ordem abaixo**, sempre pedindo ao Founder "posso seguir para a próxima?" ao fechar cada uma. Se o seu contexto ficar acima de ~70 % de uso, pare ao fim da SPEC corrente e diga ao Founder para abrir um chat novo com o `PROMPT-DE-ABERTURA-EXTRA-001.x-MODELO.md` e o bloco `[SPEC]` da próxima.

```
1. EXTRA-001.6  A cobrança prova que funciona                 CRÍTICO   esta
2. EXTRA-001.1  A apólice certa, inteira, em uma rodada        CRÍTICO   docs/canon/specs-propostas/SPEC-EXTRA-001.1-a-apolice-certa-inteira-em-uma-rodada.md
3. EXTRA-001.2  O agente lê tudo antes de falar                CRÍTICO   SPEC-EXTRA-001.2-o-agente-le-tudo-antes-de-falar.md  (depende de nada; nota ao Founder sobre o agente "Amanda" antes do canário)
4. EXTRA-001.3  O grupo só recebe o que importa                CRÍTICO   SPEC-EXTRA-001.3-o-grupo-so-recebe-o-que-importa.md  (depende da 001.2)
5. EXTRA-001.4  O corredor não trava sozinho                   CRÍTICO   SPEC-EXTRA-001.4-o-corredor-nao-trava-sozinho.md
6. EXTRA-001.7  O piloto medido                                LEVE      rascunho SPEC-EXTRA-001.7-o-piloto-medido.md (sem revisão; use como protocolo de operação + régua)
7. EXTRA-001.10 O portal de vidros de ponta a ponta            CRÍTICO   SPEC-EXTRA-001.10-o-portal-de-vidros-de-ponta-a-ponta.md
8. EXTRA-001.5  O agente sabe o que cada plano cobre           PADRÃO    SPEC-EXTRA-001.5-o-agente-sabe-o-que-cada-plano-cobre.md (depende da 001.1)
9. EXTRA-001.0  As cinco entregas sem SPEC (retroativa)        LEVE      SPEC-EXTRA-001.0-as-cinco-entregas-sem-spec.md
—  EXTRA-001.8 (isolamento) e 001.9 (rotas do painel): adiadas até o piloto medido; não execute
```

Cada proposta tem o seu próprio `PROMPT-DE-ABERTURA-EXTRA-001.<N>.md` escrito antes desta decisão; **onde ele divergir deste prompt (marcha, laço, tetos, painel), vale este prompt e o MODELO.**

Comece pelo preflight e pela leitura da §1. Depois, as 15 linhas. Depois, o BLOCO 0.
