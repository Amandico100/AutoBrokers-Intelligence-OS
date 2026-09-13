# PROMPT DE ABERTURA — SPEC-EXTRA-001.3 · O grupo só recebe o que importa

> **Amandus: cole este documento INTEIRO em um chat NOVO do Claude Code Fable**, aberto na árvore `AutoBrokers-FIX`.
> Este prompt é **privado**: no §2 você substitui `TESTE-A` e `TESTE-B` pelos dois números reais antes de colar. ⛔ **Não commitar este arquivo com os números preenchidos.** A cópia que fica no canon usa os aliases.

Você é o **ORQUESTRADOR Fable** da **SPEC-EXTRA-001.3 · O grupo só recebe o que importa**, co-líder técnico com o Founder Amandus. Você é o executor do processo inteiro: investigar, remedir, converter a proposta em SPEC definitiva, aquecer o executor, implementar, provar, integrar, entregar e comprovar — segundo `CLAUDE.md` e o **PROTOCOLO AUTOBROKERS AAA v11.2 + OPÇÃO B**.

**Não comece outra SPEC.** Esta é a quinta da família EXTRA-001.x, na ordem fixada em §12.1 do diagnóstico. Uma SPEC por chat.

---

## 1. A tarefa e os arquivos, por caminho

O pacote desta SPEC são **três arquivos**, todos já na árvore:

```text
docs/canon/specs-propostas/SPEC-EXTRA-001.3-o-grupo-so-recebe-o-que-importa.md               ← a PROPOSTA
docs/canon/specs-propostas/SPEC-EXTRA-001.3-o-grupo-so-recebe-o-que-importa-RESEARCH-PACK.md ← as evidências
docs/canon/specs-propostas/PROMPT-DE-ABERTURA-EXTRA-001.3.md                                  ← este texto
```

**Você cria:**

```text
docs/canon/specs/SPEC-EXTRA-001.3-o-grupo-so-recebe-o-que-importa.md   ← a SPEC DEFINITIVA
docs/canon/reports/SPEC-EXTRA-001.3-EXECUTION-REPORT.md                ← o relatório, aberto no começo
```

Árvore do Founder: `C:\Users\amand\Projetos\AUTOBROKERS RESULTA\AutoBrokers-FIX`.
🔴 **Confirme a árvore real, a branch e o `origin/main` pelo preflight. Não confie no nome da pasta** (CLAUDE.md §2).

⛔ Os dois primeiros arquivos são **proposta e evidência**, não execução. Não os sobrescreva para fingir que já estavam validados. O que mudar na conversão vai para a **SPEC definitiva** e para a matriz de premissas corrigidas do BLOCO 0.

---

## 2. Autorizações atuais do Founder

**Números autorizados para teste de WhatsApp, e só eles:**

```text
TESTE-A: [preencher antes de colar · allowlist privada]
TESTE-B: [preencher antes de colar · allowlist privada]
```

**Grupo de canário:** você pode **criar** um destino `whatsapp_group` num tenant de teste, com só o Founder dentro.

🔴 **PROIBIDO, e sem exceção:**

1. Enviar qualquer coisa aos grupos de suporte **operacionais** da Resulta ou da AutoFleet.
2. Usar número operacional de corretora como remetente — nem para mandar ao Founder.
3. Contatar Saionara, Regina, segurados, seguradoras ou membros de equipe.
4. Ligar o agente de atendimento, o dispatch ou uma rotina **globalmente** numa corretora operacional para fazer o canário funcionar. Se a ativação seletiva não existir, **implemente-a antes** do teste vivo.
5. Abrir sinistro, acionar assistência, entrar em portal de seguradora, alterar apólice ou executar ação financeira.
6. **Mexer nos destinos de suporte da Resulta e da AutoFleet.** 📊 Os dois estão `is_active=false` hoje — é a configuração atual do Founder. Se o canário precisar de destino ativo, **crie um novo no tenant de teste** e remova no fim.
7. Imprimir ou gravar CPF, CNPJ, telefone inteiro, nome de segurado, placa, e-mail ou credencial — em log, evidência, relatório, dossiê ou fixture.

**Permitido:** consultas read-only ao banco de produção para **contagens**; execução local do motor sobre o acervo; mensagens entre TESTE-A e TESTE-B e para o grupo de canário, com a identidade do remetente conferida **no ato**.

⚠️ Investigador, pesquisador, aquecimento, juízes e red team continuam **read-only e sem envios**. Inclua esta fronteira em **cada** pacote que você montar.

---

## 3. Estado herdado — não confunda com medição de hoje

- **Repositório:** `Amandico100/AutoBrokers-Intelligence-OS`. Baseline da redação: `a0bb5fef440eba394a9275671b1143f5025807ef`, 13/09/2026. A revisão de hoje pode ter avançado.
- **De onde esta SPEC nasce:** `docs/canon/DIAGNOSTICO-PILOTOS-E-PLANO-EXTRA-2026-09-12.md` §1.5, §3, §7.2, §7.5, §12.1.
- **Decisões do Founder que são LEI:** D-PILOTO-08, 09, 13, 14, 20 (`docs/canon/FOUNDER-DECISIONS.md`, linhas ~1752-1764). ⛔ Não reabra nenhuma.
- **O que já está na `main` e ainda não foi exercitado com segurado real:** a janela de silêncio de 7 dias, a pausa por intervenção humana, o conserto do `@lid`, membros ligarem o agente, o dossiê humano, o piso de 8192 tokens e as exceções da janela (`JANELA_SILENCIO_EXCECOES`, commit `05f46a9`). **Reproduza antes de corrigir.**
- 📊 **O estado de hoje, medido em 13/09:** 5 corretoras com `agent_enabled=false`; 4 destinos de suporte, **1 ativo** (AMANDUS); `platform_sends` com 19 linhas, **nenhuma de grupo**; `work_events` com `handoff.realertado` = **0**.
- ⚠️ **Seis afirmações do diagnóstico estão vencidas.** Estão listadas na §4 do research pack e na §4.1 da proposta. Corrija-as sem hesitar — e se achar outras, escreva.

---

## 4. Bootstrap enxuto — leia isto, e só isto, antes de começar

```text
1. CLAUDE.md                                    inteiro
2. docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md      §0–§3, §5 e §7.3
3. docs/canon/GLOSSARIO.md                      os termos
4. a proposta e o research pack desta SPEC      inteiros
```

**Por demanda, nunca "por via das dúvidas":**

- `docs/canon/MIGRATIONS-AUTHORITY.md` — **obrigatório antes de qualquer SQL**;
- `docs/canon/reports/SPEC-EXECUTION-REPORT-TEMPLATE.md` — para abrir o relatório;
- `docs/canon/ESTADO-DAS-SPECS.md` e `EXECUTION-MASTER-PLAN.md` — só as seções afetadas;
- `docs/canon/PENDENCIAS.md` **por número**: P-PILOTO-02, 03, 04, 10, 12, 13, 15, 20. ⛔ **Nunca inteiro** (📊 562 KB).

🔴 **Para cada subagente: o PACOTE, nunca o canon** (AAA §1). O pacote carrega o protocolo §0–§3, §5 e §7.3 como **primeiro item**, o contrato da unidade, os arquivos por caminho, as regras do CLAUDE.md **por número**, a referência interna e a externa, os gates e a mutação de cada um. Os pacotes-modelo estão em `docs/canon/pacotes/`. ⛔ Um subagente que receba pacote sem o protocolo **não começa: ele pede**.

---

## 5. Como começar, e como converter

1. **Preflight Git** na ordem do CLAUDE.md §2. 🔴 `git rev-list --count HEAD..origin/main` **tem de ser 0**. Se não for, **pare e pergunte qual árvore usar**.
2. **Abra o relatório** pelo template, começando pelo **EXECUTION CARD** (AAA §0.2) e recalculando RISCO e SUPERFÍCIE você mesmo. **Piso CRÍTICO** — não rebaixe para economizar tokens.
3. **BLOCO 0** — os dez passos da §4 da proposta. Investigador + pesquisador em **um** agente (AAA §10). O ponto que não pode faltar: **remedir as conversas elegíveis pelo motor Python**, não por SQL (§3.3 do research pack) — 📊 o número já derivou de 58 para 59 na mesma tarde, então ele é datado e nunca vira literal de guarda. É a medição mais importante do bloco.
4. **Converta em SPEC definitiva** em `docs/canon/specs/`, com: card · BLOCO 0 que manda remedir · as 7 unidades com contrato e gate · **a mutação de cada gate** · §7.3 com as 5 referências **reabertas por você** (a data da reabertura vai na SPEC) · "O QUE SAIU" com o gatilho de retorno · pendências por número · Caixa do Founder.
5. **Aquecimento** (AAA §5.2) com as perguntas da §6 abaixo, em contexto limpo, Opus, **uma rodada**. Emende a SPEC com o que voltar.
6. ⛔ **Não monte painel de juízes sobre a SPEC** (AAA §5.1). O painel julga **código, teste rodando e banco**.

---

## 6. Aquecimento — 15 perguntas

> As perguntas **1 e 2** afirmam algo **FALSO** com todas as letras, assinadas por mim. São exercício, **não regras do projeto**. Se uma delas tiver deixado de ser falsa por mudança na árvore, substitua-a por outra falsa **medida** antes de enviar.

1. **AFIRMAÇÃO DELIBERADAMENTE FALSA, assinada pelo orquestrador:** *"O re-alerta de 6 h nunca checa se há um humano na conversa — por isso saem 58 mensagens."* Refute pelo código executável, dizendo **quais** checagens já existem, **onde**, e **quantas conversas** elas já calam hoje.
2. **AFIRMAÇÃO DELIBERADAMENTE FALSA, assinada pelo orquestrador:** *"Gravar os envios ao grupo em `platform_sends` é inócuo: a tabela é só um log."* Mostre o caminho executável que contradiz isso, diga **quantas** leituras sem filtro existem, e o que cada uma governa. *(Resposta óbvia e incompleta: "uma, a da cota da hora".)*
3. A guarda deve ser **fail-open** ou **fail-closed** quando não consegue ler o banco? Justifique pela consequência de cada erro, e diga onde no repositório essa escolha já foi feita **ao contrário** e por quê.
4. Quais tipos de mensagem **passam** pela guarda mesmo com um humano na conversa, e por quê cada um? *(Resposta óbvia e errada: "nenhum".)*
5. A janela do grupo deve ter número próprio ou o mesmo do atendimento? Mostre a função, a env e o override por corretora, e diga o que acontece quando o valor é **0**.
6. Liste **todos** os pontos do backend que mandam mensagem ao grupo de suporte. Para cada um: passa `bloco_unico`? consulta a janela? resolve o destino por qual caminho? *(Se a sua lista tiver menos de 10, procure mais.)*
7. Por que três reaberturas de sessão de acionamento produziram três dossiês em 21 minutos, se o código tem um marcador de "já entreguei"? Onde mora esse marcador, e qual tem de ser a chave nova?
8. `espera_vencida` manda 3 avisos. O que quebra se você simplesmente mudar `AVISOS_ATE_EXPIRAR` de 3 para 1?
9. O que a lista de números da casa tem de fazer, **além** de não responder? Nomeie os quatro efeitos e diga onde cada um entra. E diga por que a chave `internal_numbers` que já existe no JSONB não resolve — com três razões medidas.
10. Aplicar `requireCompanyMember({write:true})` nas 6 rotas **tira acesso de alguém**? De quem? Como você descobre isso **antes** de a Saionara reclamar na segunda-feira?
11. A fórmula de eficiência das 19h: o que entra no numerador, o que entra no denominador, e o que fica **fora dos dois**? O que acontece quando o denominador é zero? E um `motivo` desconhecido cai em qual classe? *(Resposta óbvia e ERRADA: "em `regra`, para não punir o agente". Rode `grep -rn "motivo_classe" backend/app` e conte quantas conversas têm `human_handoff_reason` preenchido **antes** de responder — depois diga que eficiência a fórmula daria hoje.)*
11b. Quem **escreve** `motivo_classe`? Nomeie o arquivo e a função, e diga o que os gatilhos automáticos (re-alerta, espera vencida) gravam quando não sabem o motivo.
12. Reproduza **três** medições da proposta com comando e resultado, redigidos sem PII: (a) as 7 mensagens do 10/09, (b) as elegíveis ao re-alerta, (c) os balões do dossiê. 🔴 **Espera-se que (b) NÃO bata** — a proposta mediu 58 e depois 59 na mesma tarde. Diga o seu número e explique por que ele **não** pode virar literal num guarda.
13. Liste o que você **NÃO** entendeu ou não conseguiu provar. ⛔ *"Entendi tudo"* reprova o exercício.
14. Ache um **defeito material** que esta proposta não aponta — ou diga exatamente onde procurou e não achou. Entregue a nota 0–100 e o card que você aplicaria.

⛔ Não insira respostas prontas no pacote de quem deve investigar. As permissões da §2 **não** são pegadinha: a proibição de linhas operacionais é inequívoca.

---

## 7. O que você entrega como produto

- **Uma** guarda "humano já está nesta conversa", consultada por **todos** os gatilhos de grupo — assumida · humano falou nos últimos N dias (a **mesma** `janela_de_silencio_dias`) · número da casa.
- **Lista de números da casa no card Equipe**, com os **quatro** efeitos (não responde · não entra na Fila · não vai ao grupo · captura marcada `interno`) e migration expand-first com APPLY/VERIFY/ROLLBACK.
- **Mensagem inteira** nos três caminhos; espera vencida com **um** aviso; `ura_silent`/`human_silent` viram linha do resumo; queda de canal vai **ao dono**; reabertura não fura o marcador.
- **Os quatro modelos** — 🆘 PRECISO DE AJUDA · 🚨 NOVO SINISTRO · ✅ ATENDIMENTO CONCLUÍDO · 📊 ATENDIMENTOS REALIZADOS (19h) — com `wa.me/55DDDNÚMERO` sem `+`, **sem** link de painel, **sem** últimas mensagens, e o campo `motivo` classificado em incapacidade × regra.
- **Todo envio ao grupo contado** em `platform_sends`, **sem envenenar o governador de vazão** — 🔴 as **três** leituras de `_historico_sync` (cota da hora/dia, `dias_de_uso` e `total` → `maturidade_do_canal`), por **allowlist** de `kind` e nunca por prefixo, alinhada com `billing_nota`/`billing_doc` da 001.6.
- **Gate de ligar o agente**: sem destino ativo + canal conectado, recusa com frase humana.
- **As 6 mutações** com `requireCompanyMember` + `assertSameOrigin` + auditoria.
- **12 guardas** novos, **12 mutações** vermelhas, todos sobre o **motor** e o **acervo real**.

⛔ **Nenhum motor novo** (CLAUDE.md §5): nem escalonamento, nem fila de alerta, nem scheduler, nem ledger, nem resolvedor de destino, nem motor de janela. A §3.1 da proposta lista, arquivo por arquivo, o que já existe e é reaproveitado.

---

## 8. Execução AAA opção B, sem desperdício e sem atalho

**CRÍTICO, 3 lentes + red team** (fixado em §8 do diagnóstico): desenhista escreve a prova **antes** do código · builder por unidade coesa, **escrita de um só** · verificador mecânico · painel de 3 lentes cegas entre si, em paralelo, sobre o **diff, o teste rodando e o banco** · conserto conjunto · **juiz fresco** que confirma o conserto **e** audita o dado (AAA §6.1).

🔴 **Uma das lentes reconstrói o OUTCOME sobre o acervo real** (AAA §5 ④): o número da eficiência das 19h é um **dataset**, e alguém tem de refazê-lo por `SELECT` e perguntar se ele diz a verdade.

```
TETO DE GUARDAS   12 novos, e nem um a mais (D-PILOTO-14)
MUTAÇÃO           worktree próprio, restaura por CÓPIA, nunca `git checkout`
BATERIA           a suíte inteira no gate de cada bloco e no fim: 2 a 4 vezes por SPEC,
                  nunca a cada commit. Parciais à vontade. A contagem vai no relatório
COMMIT            arquivo por arquivo; cada conserto salvo COMPLETO antes do seguinte.
                  ⛔ nunca `git add -A`, nunca force push
MODELO            orquestrador Fable · builder/juiz/pesquisador/red team Opus ·
                  verificador e rerodagem mecânica Sonnet. ⛔ não trocar no meio
ORÇAMENTO         ≤ 2,5 M tokens de subagentes. Estourou → menos LENTES, nunca menos MUTAÇÃO
ROTAS NEXT        mexeu em `app/` ou env: `npm run test:rotas-montam` + `next start` +
                  UMA requisição real a `/api/…` (CLAUDE.md §9.1)
```

⚠️ **A baseline da suíte já tem falhas** (P-PILOTO-20: 4 guardas de policy quebram por import desde 23/08). Demonstre-as na base **e** no head, triagem nominal. ⛔ Não rotule toda falha como "pré-existente".

🔴 **Canário vivo é obrigatório** — os 8 casos da §14 da proposta, **incluindo o par de controle** (caso 8: conversa sem humano tem de **receber** mensagem). Um canário que só prova que o produto calou não prova nada.

⚠️ **E antes do primeiro caso, escreva a pré-condição** (§14 da proposta, §3.7 do research pack): 📊 hoje há **1 destino ativo em 4** (nenhum das pilotos) e `agent_enabled=false` em **5 de 5**. A ordem é: criar destino no tenant de teste → ligar o agente → **medir a linha de base com a guarda DESLIGADA** → ligar a guarda e repetir. 🔴 Sem esse terceiro passo, "0 mensagens ao grupo" é o produto desligado, não a guarda funcionando.

🔴 **Teto de guardas, explícito:** **7 arquivos**, 12 guardas nomeados, 💭 ~30 asserções (§12.1 da proposta). O teto de D-PILOTO-14 conta **arquivos**. `G-F1/G-G1` é **um** arquivo com 5 asserções — separá-lo em cinco não melhora a prova e estoura o teto. Se quiser separar, diga qual guarda sai.

---

## 9. Dossiê e acompanhamento

O Founder acompanha aqui:
https://claude.ai/code/artifact/afe1510d-f31c-4d13-9441-aa920ad2b868

Fonte versionada: `docs/canon/reports/dossies/dossies-autobrokers.html`

Você (ou um subagente documental, **um escritor por arquivo**) atualiza a fonte **durante a execução e a cada bloco fechado**: fase, status dos blocos, gates, provas, falhas materiais, próximos passos, implantação e caixa do Founder. Preserve as páginas existentes; acrescente a da EXTRA-001.3 e a linha na home.

🔴 **Leia o HTML publicado inteiro antes de republicar com `url`**, e confira o resultado no link. Se não houver ferramenta ou acesso, mantenha a fonte atualizada, diga explicitamente **"publicação do dossiê pendente"** e entregue ao Founder o arquivo e o passo exato. ⛔ Não finja que atualizou; ⛔ não crie um artifact substituto em silêncio.

⛔ Contagem de "no ar" **nunca** se baseia em commits. Resultado de canário **não** é aceite das atendentes. Use sempre os aliases dos números de teste.

Registre a fila em `ESTADO-DAS-SPECS.md`, `EXECUTION-MASTER-PLAN.md` e na memória do programa. ⚠️ Confira se os guardas e indexadores reconhecem `EXTRA-001.3` — a família EXTRA passa pelos **mesmos** gates, não é isentada. ⛔ Não renumere.

---

## 10. Integração, produção e estado final

🔴 **Entregar não é commitar. É empurrar:**

```bash
git rev-list --count origin/main..HEAD          # 0 = está no ar
git merge-base --is-ancestor origin/main HEAD && git push origin HEAD:main
```

A **saída real** do push e o SHA remoto vão colados no relatório. Se a `main` avançar, **integre e revalide o head efetivo** — ⛔ nunca force.

**Implantação:** `smith-api` (backend) e `web` (painel). O Founder clica Implantar no EasyPanel; você entrega o pacote pronto, a **ordem medida** (⛔ não copiada de SPEC anterior) e as variáveis novas por **nome, sem valor** (`RESUMO_DIARIO_HORA`, `RESUMO_DIARIO_ATIVO`). ⚠️ E avise por escrito que `JANELA_SILENCIO_HUMANO_DIAS`, que já existe, passa a ter **dois** efeitos.

**No fim, entregue:**

1. O que mudou para a corretora: **o que o grupo para de receber, e o que passa a receber** — em linguagem simples.
2. SPEC definitiva, relatório, SHAs, a migration com VERIFY rodado no banco.
3. Quais gates passaram, quais dependem de ação física, e o que **não** foi comprovado.
4. Estado separado, sem herança: implementado / na main / implantado / canário técnico / aceite das pilotos / ativação operacional.
5. Dossiê atualizado, ou pendência de publicação nominal.
6. **Caixa do Founder** com as ações concretas mínimas (§22 da proposta — já tem 6 itens; acrescente o que aparecer).
7. **Handoff de encerramento:** a próxima da fila é **EXTRA-001.4 · O corredor não trava sozinho** — ⚠️ e ela **chama a mesma guarda** que você acabou de criar (§21 da proposta). Deixe escrito, com o caminho do módulo e a assinatura da função, para que ela **não** construa a segunda.

---

🔴 **Comece pelo preflight, pelo EXECUTION CARD e pelo BLOCO 0.** Não me devolva uma análise: valide, converta e **execute** esta SPEC dentro da autorização descrita, seguindo o AAA até a entrega e a comprovação possível.

⚠️ E lembre da forma do defeito que você está consertando: **um alarme repetido é como se ensina uma equipe a ignorar alarme.** O modo de falha desta SPEC não é avisar demais — é **calar demais**, e calar em silêncio. Todo silêncio que ela criar tem de deixar rastro e reaparecer no resumo das 19h.
