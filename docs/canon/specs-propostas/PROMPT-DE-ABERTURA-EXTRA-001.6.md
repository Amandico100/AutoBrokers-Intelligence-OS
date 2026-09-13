# PROMPT DE ABERTURA — SPEC-EXTRA-001.6 · A cobrança prova que funciona

> Cole este documento **inteiro** em um chat NOVO do Claude Code Fable, aberto na árvore `AutoBrokers-FIX`.
> Ele não contém número de teste em claro: os dois números do Founder vivem na allowlist privada e nas variáveis de ambiente do smith-api, e aqui aparecem só como **TESTE-A** e **TESTE-B**.

Você é o **ORQUESTRADOR Fable** da **SPEC-EXTRA-001.6 · A cobrança prova que funciona**, co-líder técnico com o Founder Amandus. Você executa o processo completo: preflight, remedição, conversão da proposta em SPEC definitiva, aquecimento do executor, implementação, prova, canário, entrega e comprovação — segundo `CLAUDE.md` e o **PROTOCOLO AUTOBROKERS AAA v11.2 + OPÇÃO B**.

**Não comece outra SPEC.** Esta é a 001.6 da família EXTRA-001 (D-PILOTO-08). Uma SPEC por chat.

---

## 1. A tarefa e os arquivos, por caminho

Você recebe três arquivos, já na árvore:

```text
docs/canon/specs-propostas/SPEC-EXTRA-001.6-a-cobranca-prova-que-funciona.md               ← a PROPOSTA
docs/canon/specs-propostas/SPEC-EXTRA-001.6-a-cobranca-prova-que-funciona-RESEARCH-PACK.md ← a EVIDÊNCIA
docs/canon/specs-propostas/PROMPT-DE-ABERTURA-EXTRA-001.6.md                               ← este documento
```

Você **cria**:

```text
docs/canon/specs/SPEC-EXTRA-001.6-a-cobranca-prova-que-funciona.md      ← a SPEC definitiva
docs/canon/reports/SPEC-EXTRA-001.6-EXECUTION-REPORT.md                 ← o relatório, aberto no início
backend/supabase/migrations/20260914_01_spec_extra0016_cobranca_por_segurado.sql
backend/tests/test_a_cobranca_prova_que_funciona.py
backend/tests/test_o_portal_diz_por_que_nao_entrou.py
backend/tests/corpus/telas_reais_de_portal/<portal>-<desfecho>-<aaaammdd>.txt
docs/canon/ROTEIRO-VALIDACAO-EXTRA-001.6-ATENDENTES.md
```

⛔ **Não sobrescreva a proposta nem o research pack** para fingir que já estavam validados. O que mudar na conversão vai para a SPEC definitiva e para a matriz de premissas corrigidas do BLOCO 0.

Projeto do Founder: `C:\Users\amand\Projetos\AUTOBROKERS RESULTA\AutoBrokers-FIX`. **Confirme a árvore real pelo preflight; não confie no nome da pasta** (CLAUDE.md §2).

---

## 2. Autorizações atuais — leia antes de delegar qualquer coisa

**Testes vivos de WhatsApp:** exclusivamente **TESTE-A (remetente) → TESTE-B (destino)**, os dois na allowlist, no tenant e no run do canário. Os valores estão em `BILLING_CANARIO_ALLOWLIST` e `CANARIO_TESTE_B` no smith-api (📊 já configuradas desde 08/09) e na configuração privada do Founder. ⛔ Nunca commitar, publicar no dossiê, colar em log, fixture ou relatório.

**Proibido, sem exceção:**

1. Enviar para segurado, atendente real, grupo de suporte, seguradora ou qualquer número fora da allowlist — inclusive por fallback, alerta, fila, retry, replay e incidente.
2. Usar número operacional da Resulta ou da AutoFleet como remetente, mesmo para mandar ao Founder.
3. Contatar Saionara ou Regina. Você **prepara** o roteiro; quem conduz é o Founder.
4. 🔴 **Tentar entrar na Allianz ou na Mapfre com a senha atual.** 📊 As duas estão recusadas (Allianz desde 18/08; a Mapfre nunca teve um `done`). Insistir é o caminho para o portal **bloquear a conta da corretora**. As senhas novas chegam na segunda-feira (🧑) e **isso não trava nada**: o canário roda com **Tokio, HDI, Yelum e Zurich**.
5. Trocar, apagar, renomear ou reparear conexão de WhatsApp; mexer em QR.
6. Aplicar migration sem ter lido `docs/canon/MIGRATIONS-AUTHORITY.md` inteiro e sem APPLY/VERIFY/ROLLBACK escritos **antes**.
7. Relaxar qualquer controle de produção para fazer um teste passar.

**Permitido:** consultas read-only ao banco de produção; leitura dos objetos já gravados no bucket privado `portal-evidence`; `login_check` nos quatro portais cuja credencial está válida; rodar a rotina de cobrança da Resulta em `test` e em `equipe` **com `team_number` = TESTE-B**.

Investigador, pesquisador, aquecimento e juízes continuam **read-only e sem envios**. Inclua esta fronteira em **cada** pacote que você montar.

---

## 3. Estado herdado — não confunda com medição de hoje

- **Antecessora:** SPEC-EXTRA-001 · Operação dos pilotos. Relatório em `docs/canon/reports/SPEC-EXTRA-001-EXECUTION-REPORT.md`; `main` em `ba7ba75`; **implantada**. Ela construiu o ledger com **reserva atômica antes do efeito**, os **estados por componente**, a **retenção honesta** e a porta `send_to_client_guarded`. 🔴 **Preserve tudo isso.** Esta SPEC conserta o que fica **entre o motor e o humano**.
- 📊 13/09: `billing_sent_log` tem **0 linhas**. A máquina da EXTRA-001 nunca foi ligada, porque as execuções de 10 e 11/09 rodaram em `test`, e em teste o ledger é desligado por desenho.
- 📊 13/09: a rotina está `is_active=false`, `next_run_at=14/09`, `send_mode='test'`, **`team_number` vazio**, **`attendant_name` vazio**.
- **Dívida herdada que esta SPEC fecha:** o canário **Q1–Q6 nunca rodou ao vivo** (`P-E001-CANARIO-VIVO-NO-IMPLANTADO`, `P-E001-Q4-VIVO-DEPENDE-DE-DEPLOY`, `P-PILOTO-11`). As variáveis já estão no smith-api desde 08/09; falta chamar `POST /api/admin/canario/extra001` com a chave interna e colar o resultado.
- **Lição operacional registrada no relatório da EXTRA-001:** a suíte **restaura arquivos por cópia**. Duas horas de edição foram refeitas por isso. Não edite durante a suíte; não use `git checkout` para restaurar mutação.

---

## 4. Decisões do Founder que são LEI nesta execução

| ID | decisão |
|---|---|
| **D-PILOTO-18** | o modo da rotina é **`equipe`**, não `cliente` |
| **D-PILOTO-19** | **N = 7 dias** por segurado · `attendant_name` = a atendente humana da Resulta (**confirme o nome com o Founder; nunca invente**) · `team_number` = **TESTE-B** durante o canário, e trocá-lo pelo número real é ato **só do Founder**, depois · a rotina **só é reativada depois que o BLOCO P0 estiver no ar** · as senhas de Allianz e Mapfre chegam na segunda e **não travam nada** |
| **D-PILOTO-08** | numeração EXTRA-001.1…001.10 mantida |
| **D-PILOTO-14** | alta qualidade sem execuções exorbitantes — **teto de 12 guardas novos** |
| **D-E001-03/04/05** | mesmo número pareado; `equipe` = nota interna separada + texto limpo + PDF |
| **D-E001-07** | testes vivos só entre TESTE-A e TESTE-B |

🔴 **D-PILOTO-08…20 ainda não estão em `docs/canon/FOUNDER-DECISIONS.md`** (📊 lá só existem D-PILOTO-01…07). **Registrá-las é entrega desta SPEC.** Os textos estão em `docs/canon/DIAGNOSTICO-PILOTOS-E-PLANO-EXTRA-2026-09-12.md` §7.1 e §12.

---

## 5. Bootstrap enxuto — leia isto, e só isto, antes de começar

```text
1. CLAUDE.md                                       inteiro
2. docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md         §0–§3, §5, §7.3
3. docs/canon/GLOSSARIO.md                         os termos
4. a PROPOSTA e o RESEARCH PACK desta SPEC         inteiros
5. docs/canon/MIGRATIONS-AUTHORITY.md              🔴 antes de qualquer SQL
```

Por demanda, e **só** as seções pertinentes: `DIAGNOSTICO-PILOTOS-E-PLANO-EXTRA-2026-09-12.md` §9 (a origem) · `docs/canon/reports/SPEC-EXTRA-001-EXECUTION-REPORT.md` §6 e §10 · `reports/SPEC-EXECUTION-REPORT-TEMPLATE.md` · `ESTADO-DAS-SPECS.md` / `INDICE-DE-SPECS.md` nas linhas da fila.

⛔ **Não leia `PENDENCIAS.md` inteiro** (📊 562 KB). Por número: `P-264` · `P-PILOTO-11` · `P-E001-CANARIO-VIVO-NO-IMPLANTADO` · `P-E001-Q4-VIVO-DEPENDE-DE-DEPLOY` · `P-E001-FILA-SEM-AUTORIZACAO-DE-AUXILIAR` · `P-E001-LEDGER-SEM-VENCIMENTO-E-VALOR` · `P-E001-INCERTO-ESCRITA-DUPLA`.

Para subagentes: **o pacote, nunca o canon** — protocolo §0–§3, §5, §7.3 + o contrato da unidade + os arquivos por caminho + as regras invioláveis por número + os gates + a mutação de cada gate. Use os modelos de `docs/canon/pacotes/`.

---

## 6. Como começar, e como converter

1. **Preflight** (CLAUDE.md §2): `git fetch` · contagem atrás (🔴 tem de ser 0) · contagem à frente · branch · `git rev-parse HEAD` · `git status --short`. Registre o SHA no relatório.
2. **Abra o relatório** pelo template, começando pelo **EXECUTION CARD** (§0.2 do protocolo), com as duas contas feitas — não copiadas da proposta.
3. **BLOCO 0 — remeça.** As 14 premissas da proposta §4.2, cada uma com o comando e o valor de HOJE. **O seu número vence o da proposta.** Corrija o que divergir e anote a divergência (a §12.1 da proposta já lista oito coordenadas que mudaram entre 12 e 13/09 — espere mais).
4. **Primeira tarefa concreta do BLOCO 0:** baixar e **ler** os 12 prints de `portal-evidence/{job}/00-desfecho-*.jpg` dos jobs de 10–11/09 e **transcrever o texto** para `backend/tests/corpus/telas_reais_de_portal/`. 🔴 Sem isso não existe o corpus do guarda G3 — 📊 `evidence.body_text` e `evidence.debug_dom` estão **vazios** em todos os seis jobs `failed`/`needs_human`.
5. **Converta** em SPEC executável: BLOCO 0 · blocos com contrato e gate · as 12 mutações · a seção §7.3 com as 5 referências externas **reabertas por você** (com a data) · "O QUE SAIU" com gatilho · pendências · caixa do Founder.
6. **Aqueça o executor** com as perguntas da §7 abaixo, em contexto limpo, **uma rodada**. Emende a SPEC com o que voltar. ⛔ Não monte painel de juízes sobre a SPEC (§5.1 do protocolo).
7. **Execute**, na ordem dos blocos, com **um escritor por arquivo** e integração serial nos contratos compartilhados.

---

## 7. Aquecimento — 14 perguntas, em contexto limpo

> Entregue ao executor a SPEC + estas perguntas. Duas são **deliberadamente falsas e assinadas**. Uma pede o que ele não entendeu — *"entendi tudo"* reprova. Uma pede um defeito que a SPEC não aponta. Adapte as coordenadas ao código do dia.

1. **AFIRMAÇÃO DELIBERADAMENTE FALSA DO EXERCÍCIO, assinada pelo orquestrador:** *"Basta ligar `bloco_unico=True` dentro de `_entregar_agora` e toda mensagem da plataforma passa a sair inteira, sem efeito colateral."* Refute pelo caminho executável, nomeando quem mais chama aquela porta.
2. **AFIRMAÇÃO DELIBERADAMENTE FALSA DO EXERCÍCIO, assinada pelo orquestrador:** *"A Mapfre falhou sem motivo nenhum: a journey não escreve por que recusou."* Mostre a consulta que contradiz isso e diga exatamente qual linha de código deixa de ler o motivo.
3. A dedup por parcela e a regra de "1 cobrança por segurado a cada 7 dias" são a mesma regra com números diferentes? Se não, o que cada uma protege, e o que acontece se você implementar só uma?
4. A reserva pode passar a ser por **grupo** de segurado, já que a mensagem é uma só? Responda pelo contrato da identidade da obrigação, e diga o que se reabriria.
5. `CREATE OR REPLACE FUNCTION` com um parâmetro a mais **substitui** a função existente? E se o parâmetro novo tiver `DEFAULT`, o que acontece com uma chamada de 12 argumentos? Diga o código de erro e onde ele apareceria.
6. Qual é o dialeto do motor que compara a tela da Allianz? Escreva as duas frases novas da lista `_FAIL` exatamente como elas têm de ser escritas, e explique por que "Acesso negado" com maiúscula seria um padrão morto **e um teste verde**.
7. Onde está, hoje, o texto real da tela de um portal que falhou? Se a resposta for "no banco", mostre a consulta. Se não for, diga o que isso obriga a SPEC a fazer antes de escrever o guarda.
8. `portal_accounts.health = 'unknown'` é um defeito a eliminar ou uma peça do desenho? Ligue a sua resposta aos três estados do padrão de circuit breaker e a `app/api/portal.py:165`.
9. Por que credencial recusada **não** entra no backoff com jitter, mesmo sendo uma falha de portal? Qual é o risco concreto, e para quem?
10. O guarda `backend/tests/test_a_cobranca_esta_como_estava.py` afirma que "o inadimplente recebe UMA mensagem, como sempre recebeu". Rode o motor real e diga se a afirmação é verdadeira hoje. Se não for, explique **por que ela está verde** — e o que isso ensina sobre corpus de teste.
11. Agrupar por `cpf_cnpj` é suficiente? Dê o caso concreto em que a chave sem o portal produz uma mensagem errada, e o caso em que o fallback por nome funde duas pessoas.
12. O que acontece com a atendente se a rotina for reativada **antes** do BLOCO P0 estar no ar? Responda com o número de mensagens, calculado.
13. Liste o que você **NÃO** entendeu ou não conseguiu provar. *"Entendi tudo"* não satisfaz o exercício.
14. Ache um defeito material que esta SPEC **não** aponta — ou diga onde procurou e não achou. Entregue a nota 0–100 e o EXECUTION CARD que você aplicaria.

⛔ Não coloque respostas prontas no pacote de quem deve investigar. As permissões (§2) não são pegadinha: são inequívocas.

---

## 8. Execução AAA — opção B, sem desperdício e sem atalho

```text
NÍVEL      CRÍTICO por piso (§3.2: envia + migration de estrutura). A proposta §12.4 registra a
           divergência com o diagnóstico, que fixara PADRÃO. Faça a sua conta no card e decida —
           por escrito, com nota, e sem rebaixar segurança ou isolamento
TIME       desenhista antes do código · builders Opus por unidade coesa · verificador Sonnet ·
           painel de 3 lentes CEGAS DE UMA VEZ (verdade+regressão · produto+DADO · red team) ·
           juiz fresco que confirma o conserto E audita o dado (§6.1)
GUARDAS    🔴 no máximo 12 novos. Todos sobre o MOTOR e o ACERVO real. ⛔ proibido teste que
           reimplementa a regra. Cada guarda com a MUTAÇÃO que o deixa vermelho, nomeada
MUTAÇÃO    worktree próprio ou lock exclusivo · restaura por CÓPIA, nunca `git checkout` ·
           falha nova identificável em subprocesso · ⛔ nunca `xfail`
BATERIA    suíte inteira no gate de cada bloco e no fim (2 a 4 vezes na SPEC), com a ÁRVORE PARADA.
           Parciais à vontade. O relatório traz a contagem do diário
ROTAS      mexeu em `app/`? `npm run test:rotas-montam` + `next start` + UMA requisição real
COMMIT     arquivo por arquivo, conserto completo antes do seguinte. ⛔ nunca `git add -A`
ORÇAMENTO  ≤ 2,5 M de tokens de subagentes. 💭 alvo 1,4–1,8 M. Estourou → menos LENTES, nunca menos mutação
RELÓGIO    💭 6–9 h. Estourou a faixa? não pare: responda POR ESCRITO por que continuar (§9.2)
```

**Canário vivo é obrigatório**, e em duas camadas: os **Q1–Q6 herdados** (que fecham três pendências da EXTRA-001) e os **Q7–Q10 novos** desta SPEC. Só TESTE-A → TESTE-B; limpeza por `id + company_id + canario` conferida depois.

**A licença de autonomia (§9):** não muda um byte do que a atendente lê, do que o segurado recebe, do que fica no banco ou de quem pode ler? → **pendência, e segue**. Dúvida entre caminhos → nota 0–100 em cada, escolhe o maior, registra, segue. Travou 30 min → o mais conservador, anota na caixa, segue.

---

## 9. Dossiê e acompanhamento

O Founder acompanha em https://claude.ai/code/artifact/afe1510d-f31c-4d13-9441-aa920ad2b868 (aba **Pilotos**). Fonte versionada: `docs/canon/reports/dossies/dossies-autobrokers.html`.

- Leia o HTML publicado **inteiro** antes de republicar com `url`. Preserve as páginas existentes. Um escritor por arquivo.
- Atualize **a cada bloco fechado**, não só no fim: fase, gates, provas, falhas materiais, implantação, caixa do Founder.
- ⛔ Nunca alegue que o link foi atualizado. Sem ferramenta ou acesso: atualize a fonte, escreva **"publicação do dossiê pendente"** e entregue o arquivo e o passo exato.
- ⛔ Nenhum número de teste, CPF, telefone ou nome de segurado no dossiê.

Registre também: `ESTADO-DAS-SPECS.md`, `INDICE-DE-SPECS.md`, `EXECUTION-MASTER-PLAN.md`, `CHANGE-ADDENDA.md`, `PENDENCIAS.md`, `FOUNDER-DECISIONS.md` (🔴 D-PILOTO-08…20) e `backend/supabase/migrations/MANIFEST.md`.

---

## 10. Integração, produção e estado final

**Duas implantações, nesta ordem:**

1. **BLOCO P0 sozinho** — `smith-api` (+ `smith-web` se o rótulo "Quem assina" entrar junto). Não depende das senhas novas. 🔴 **Só depois desta implantação o Founder reativa a rotina.**
2. **B1 + B2 + B3 + B4** — migration aplicada e verificada **antes**; `smith-api` e `portal-worker` primeiro, `smith-web` depois.

**Entrega é `git push`, não commit:**

```bash
git rev-list --count HEAD..origin/main
git rev-list --count origin/main..HEAD
git merge-base --is-ancestor origin/main HEAD && git push origin HEAD:main
git fetch origin && git rev-parse --short origin/main
```

Cole a **saída real** no relatório. Depois o Founder clica **Implantar** no EasyPanel — e você entrega **o comando e a ordem dos serviços**, nunca a tarefa.

**No fim, entregue:**

1. o que mudou para a corretora, em linguagem de gente, e como ela usa;
2. SPEC definitiva, relatório, SHAs, a migration com VERIFY rodado e a saída colada;
3. quais gates passaram, quais dependem de ação física, e o que **não** foi comprovado;
4. estado separado: **implementado / na main / implantado / canário técnico / aceite das atendentes / ativação operacional**;
5. dossiê atualizado — ou pendência nominal;
6. **caixa do Founder** com as ações concretas mínimas: as senhas de Allianz e Mapfre, o **nome da atendente**, o `team_number` real (só ele troca), a redação 💭 do plural, e o N de dias se quiser diferente de 7;
7. handoff: a próxima da fila é a **001.7 · o piloto medido** (que consome a observabilidade por portal desta SPEC); antes dela, o que estiver aberto na ordem de `DIAGNOSTICO-PILOTOS-E-PLANO-EXTRA-2026-09-12.md` §12.1. **Não execute a próxima neste chat.**

Comece pelo preflight, pelo EXECUTION CARD e pelo BLOCO 0. Não me devolva uma análise: **converta e execute**, dentro da autorização descrita, até a entrega e a comprovação possível.
