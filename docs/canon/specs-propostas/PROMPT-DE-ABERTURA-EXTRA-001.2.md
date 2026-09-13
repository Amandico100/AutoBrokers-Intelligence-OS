# PROMPT DE ABERTURA — SPEC-EXTRA-001.2 · O agente lê tudo antes de falar

> Cole este documento **inteiro** num chat NOVO do Claude Code Fable, aberto na árvore atualizada do AutoBrokers.
> Acrescente **uma linha privada** com os dois números de teste (TESTE-A e TESTE-B). ⛔ **Não commitar esses números.** No canon só os aliases.

Você é o **ORQUESTRADOR Fable** da **SPEC-EXTRA-001.2 · O agente lê tudo antes de falar**, co-líder técnico com o Founder Amandus. Você é o executor do processo completo: medir, converter a proposta em SPEC definitiva, aquecer o executor, implementar, provar, integrar e entregar — segundo `CLAUDE.md` e o **PROTOCOLO AUTOBROKERS AAA v11.2 + OPÇÃO B**.

**Não comece outra SPEC.** Esta é a **quarta** da fila da família EXTRA (diagnóstico §12.1). Uma SPEC por chat (**D-PILOTO-20**).

---

## 1. A tarefa e os arquivos, por caminho

Tudo já está na árvore. Nada para baixar.

```text
docs/canon/specs-propostas/SPEC-EXTRA-001.2-o-agente-le-tudo-antes-de-falar.md                 ← a PROPOSTA
docs/canon/specs-propostas/SPEC-EXTRA-001.2-o-agente-le-tudo-antes-de-falar-RESEARCH-PACK.md   ← evidência e medições
docs/canon/specs-propostas/PROMPT-DE-ABERTURA-EXTRA-001.2.md                                   ← este arquivo
docs/canon/specs/SPEC-EXTRA-001.2-o-agente-le-tudo-antes-de-falar.md          ← VOCÊ cria a definitiva
docs/canon/reports/SPEC-EXTRA-001.2-EXECUTION-REPORT.md                       ← VOCÊ inicia e preenche
```

Worktree do Founder: `C:\Users\amand\Projetos\AUTOBROKERS RESULTA\AutoBrokers-FIX`.
🔴 **Confirme a árvore real, a branch e a `origin/main` pelo preflight — não confie no nome da pasta** (CLAUDE.md §2). Baseline da preparação: `a0bb5fe` (0 atrás, 0 à frente em 13/09/2026).

⛔ Os dois primeiros arquivos são **proposta**, não execução. Não os sobrescreva para fingir que já estavam validados. Correções da conversão vão para a **SPEC definitiva** e para a matriz de premissas corrigidas do BLOCO 0.

**Resultado que a SPEC persegue, em uma frase:** o segurado manda cinco mensagens e uma foto em doze segundos; o agente lê **tudo** e responde **uma vez**, sem pergunta repetida, sem cumprimento no meio, com a identidade certa, e com o nome que a corretora escolheu.

---

## 2. Autorizações atuais do Founder

**Testes vivos de WhatsApp SOMENTE entre os dois números de teste**, cujos valores estão na linha privada deste prompt e na configuração privada do projeto. No canon, sempre `TESTE-A` e `TESTE-B`.

🔴 **Confira o telefone realmente conectado hoje.** Nome de corretora, rótulo de instância ou propósito **não provam identidade**.

**Está autorizado:** implementar a SPEC e rodar o AAA · canário vivo TESTE-A ↔ TESTE-B · consultas **read-only** ao banco de produção para o BLOCO 0 e para o corpus (**só contagens, intervalos e traços derivados**) · `migrar_conversas_fantasma_lid.py` em **dry-run** à vontade · aplicar as migrations M1/M2 depois do VERIFY em branch.

**Está proibido:** usar número operacional Resulta/AutoFleet como remetente, **inclusive** para enviar ao Founder · enviar a segurados, seguradoras, atendentes ou grupos · ligar atendimento/dispatch globalmente numa corretora operacional · acionar assistência real, abrir sinistro ou tocar portal · rodar `--vivo` do script das fantasmas sem M1, sem VERIFY e sem o veredito do item 0 do BLOCO 0 · alterar `JANELA_SILENCIO_EXCECOES` para "facilitar" um teste · imprimir CPF, telefone, nome de segurado, placa, e-mail ou credencial em qualquer saída.

🔴 **Novo nesta SPEC:** a **presença "digitando…"** é efeito externo — chega ao aparelho do segurado. Ela passa pela **mesma** allowlist e pela mesma verificação da §1.4 da proposta. E `PRESENCA_DIGITANDO_LIGADA` nasce **desligada**.

Investigador, pesquisador, aquecimento e juízes continuam **read-only e sem envios**. Inclua esta fronteira em **cada** pacote de execução.

---

## 3. Estado herdado — não confundir com medição de hoje

- **Decisões que são lei, não se reabrem:** **D-PILOTO-12** (nome do agente é escolha livre da corretora; a SPEC garante que nunca confunde) · **D-PILOTO-14** (≤ 12 guardas novos por SPEC; bateria sobre motor e acervo real) · **D-PILOTO-08** (numeração) · **D-PILOTO-20** (execução em chat novo, AAA opção B) · **D-PILOTO-07** (≥ 4 atendimentos simultâneos por corretora, nenhuma interferindo em outra — obriga a trava a ser **por conversa**) · **D-PILOTO-02** (a atendente responder pelo celular pausa o robô, **e isso é o desejado**) · **D-E001-02** (atendimento permanece Evolution Go).
- **Cinco pacotes entraram na main em 08–10/09 sem SPEC** (mídia 16 MB, pausa por intervenção, rajadas em paralelo, janela de 7 dias, `JANELA_SILENCIO_EXCECOES`). Eles funcionam e têm testes; o canon está sendo acertado pela **EXTRA-001.0**. ⚠️ Vários **nunca foram exercitados com segurado real**.
- 📊 `companies.agent_enabled = false` nas **5** empresas: o agente está **desligado** agora. O canário desta SPEC é o primeiro exercício real da trava, da janela e do nome.
- **Não copie status de deploy de relatório antigo.** Health isolado não prova SHA nem comportamento.

🔴 **Dez correções ao diagnóstico já estão feitas no RESEARCH-PACK §1. Leia-as antes de qualquer código** — entre elas: o `graph.py` não está em `agents/core/`; a mídia pula o buffer em **três** pontos, não um; a ficha de slots **já existe** (o buraco é o escritor: 15 de 35); `companies.agent_name` **não existe**; `messages.created_at` é o relógio do **espelho**; e **P-PILOTO-15 não é o que o plano supôs**.

---

## 4. Bootstrap enxuto e obrigatório

```text
CLAUDE.md                                          inteiro
docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md            §0–§3, §5, §7.3
docs/canon/GLOSSARIO.md                            termos
a proposta + o RESEARCH-PACK desta SPEC            inteiros
docs/canon/MIGRATIONS-AUTHORITY.md                 ANTES de qualquer SQL — inteiro
```

Por demanda: `SPEC-EXECUTION-REPORT-TEMPLATE.md` · `ESTADO-DAS-SPECS.md` (só a seção da família EXTRA) · `CHANGE-ADDENDA.md`.
**Pendências por NÚMERO, nunca o arquivo inteiro (562 KB):** `P-PILOTO-13`, `P-PILOTO-15`, e 16/17/18 só para dar veredito.
⛔ Não leia o `PENDENCIAS.md` inteiro. ⛔ Não leia o canon todo.

**Para subagentes: pacote, nunca canon** (AAA §1) — o protocolo §0–§3/§5/§7.3 é o **primeiro** item, mais o contrato da unidade, os arquivos por caminho, as regras do CLAUDE.md **por número**, a referência interna e a externa, os gates com a mutação que os deixa vermelhos, e as pendências por número. Use os pacotes-modelo de `docs/canon/pacotes/`.

---

## 5. Como começar e converter

1. **Preflight Git** na ordem do CLAUDE.md §2. `HEAD..origin/main` ≠ 0 → **pare e pergunte qual árvore usar**.
2. **Abra o relatório** pelo template, começando pelo **EXECUTION CARD** (AAA §0.2). Piso **CRÍTICO** — ⛔ não rebaixe para economizar tokens. O card proposto está na §0.2 da proposta: RISCO **8**, SUPERFÍCIE **3**, 6 unidades, 3 lentes + red team + juiz fresco.
3. 🔴 **BLOCO 0 item 0 PRIMEIRO: o candidato a P0 cross-tenant.** 📊 104 de 134 `wa_message_id` repetidos aparecem sob **dois `company_id`**. Determine a causa. Confirmado → **pare, registre em `FOUNDER-DECISIONS.md`, trate como P0 próprio**. ⛔ **Nenhuma migration antes deste veredito.**
4. **BLOCO 0 completo** (§4 da proposta, 12 itens): reabra cada `arquivo:linha`, reconte os **três** desvios de mídia, remeça o buraco da ficha, **meça a duração real de um turno** (o TTL da trava sai daí, não dos 💭 90 s), aplique `tracos_da_mensagem` ao texto real, gere o corpus, leia o `MIGRATIONS-AUTHORITY.md`, reconte as fantasmas, confirme a rota de presença no fork Go implantado, rode os guardas que não podem quebrar, e dê veredito às pendências.
5. **Converta em SPEC definitiva** com: card · BLOCO 0 · unidades coesas · gate **e mutação por bloco** · §7.3 com as 7 referências externas **reabertas por você, com a data nova** · "O QUE SAIU" com gatilho · pendências · caixa do Founder.
6. **Aquecimento (§6 abaixo) no lugar de painel sobre a SPEC.** ⛔ Não se monta painel de juiz sobre documento (AAA §5.1). Uma rodada, emende, e execute **nesta mesma sessão**.

---

## 6. Aquecimento — 14 perguntas, respondidas com COMANDO e saída (AAA §0.4)

Use `docs/canon/pacotes/PACOTE-AQUECIMENTO.md`. As perguntas **1 e 2 são falsas deliberadas do exercício, assinadas pelo orquestrador** — não são regras do projeto. Se alguma tiver deixado de ser falsa, substitua por outra falsa **medida** antes de enviar.

1. **AFIRMAÇÃO DELIBERADAMENTE FALSA DO EXERCÍCIO, assinada pelo orquestrador:** *"Basta trocar o debounce de 8 s por 20 s no `message_buffer_service` e a fragmentação acaba."* Refute com o caminho executável e com os intervalos medidos.
2. **AFIRMAÇÃO DELIBERADAMENTE FALSA DO EXERCÍCIO, assinada pelo orquestrador:** *"O `get_and_clear_buffer` é atômico, logo duas gerações nunca disputam a mesma conversa."* Mostre o entrelaçamento que contradiz isso.
3. Onde, exatamente, a mídia pula o buffer? **Quantos pontos?** *(resposta óbvia e errada: um, o que o diagnóstico cita)*
4. A ficha guarda os slots já respondidos? *(resposta óbvia e errada: "não, só `apolice_confirmada`")* — mostre o número que decide a questão, e diga **onde o elo se parte**.
5. Qual coluna guarda o nome que o agente usa para se apresentar? *(resposta óbvia e errada: `conversations.agent_name`)* — e qual é o nome **ativo** da Resulta hoje?
6. Por que a trava de turno **não** pode ser por corretora? Qual teste **existente** prova isso, e o que acontece com ele se a chave perder o telefone?
7. Se a trava falhar em ser adquirida, o que acontece com as mensagens do buffer? Por que a ordem `trava → get_and_clear` e não o contrário?
8. Qual relógio mede uma rajada, e por quê? Reproduza a linha de controle dos dois relógios e diga a diferença percentual.
9. O índice único do espelho existe? Ele resolve as duplicatas medidas? **Quantas estão dentro da mesma conversa?**
10. O que é P-PILOTO-15, **com o texto que está no `PENDENCIAS.md`**? E qual é o segundo defeito de silêncio que esta SPEC conserta e **não** tem pendência própria?
11. Onde o `--vivo` das fantasmas está travado, e qual é o texto exato do CHECK que precisa mudar? Quantas fantasmas existem **hoje** e quantas têm par real?
12. Como a presença "digitando…" chega ao WhatsApp neste produto? Existe alguma chamada hoje? Qual flag precisa nascer, e por quê o limite é **25 s**?
13. **Reproduza 3 números 📊 da SPEC ao acaso**, com o comando, e diga se batem. Um que não bate reprova a amostra.
14. **Liste o que você NÃO entendeu ou não conseguiu provar** — "entendi tudo" reprova. E **ache um defeito material que a SPEC não aponta**, ou diga onde procurou e não achou. Entregue a **sua** nota 0–100 para a SPEC e o **seu** EXECUTION CARD.

⛔ Não insira respostas prontas no pacote de quem deve investigar. Permissões não são pegadinha: a allowlist e a proibição de linhas operacionais são inequívocas.

---

## 7. O que você deve entregar como produto

- **Trava de turno por conversa** — `SET NX EX` com token, liberação pelo script Lua que **compara o valor**, renovação com teto, e **reconferência de posse antes de enviar**. Quem perdeu a posse **não fala**.
- **Janela que escuta o conteúdo** — 3 · 8 · 18 s calibrados no acervo, teto **25 s**, e o piso rígido de 8 s **morto** (`grep "max(settings.BUFFER"` tem de voltar vazio).
- **Mídia no buffer nos três pontos**, legenda e arquivo no mesmo turno; **re-planejamento** relendo o buffer antes de gerar; **presença "digitando…"** só quando o agente vai mesmo falar.
- **Ficha com todo slot que o corredor exige**, derivada e não escrita à mão; guarda de pergunta repetida sobre o motor e o acervo.
- **Apresentação condicional** (a decisão sai do modelo e vira código), hierarquia de tamanho **medida**, identidade da thread reescrita a cada assunto.
- **Uma conversa por contraparte** + as 175 fantasmas + a trava da 176ª; **`wa_message_id` no pipeline**; ordem correta do silêncio e P-PILOTO-15; **todo silêncio no feed com motivo**.
- **O nome do agente inteiro** (D-PILOTO-12): apresentação, "especialista" = a atendente real, troca que não muda conversa em andamento, **o servidor recusa nome colidente**, e 🤖 nos dossiês.
- **12 guardas novos**, cada um com a mutação que o deixa vermelho; **G6 e G7 são vermelhos HOJE** — esse é o gate zero.
- **Duas migrations** com APPLY/VERIFY/ROLLBACK escritos **antes**, VERIFY em SQL executável, `MANIFEST.md` atualizado.

⛔ **Nenhum motor paralelo** (CLAUDE.md §5). Tudo acima cabe em peças que já existem — a §3 da proposta lista, por caminho, o que reaproveitar e por quê. ⛔ Nenhuma tabela nova.

---

## 8. Execução AAA sem desperdício e sem atalhos

**CRÍTICO opção B:** desenhista da prova **antes** do código · builder por unidade coesa, **um escritor por arquivo** · verificador mecânico (`py_compile`/`tsc` → testes do bloco → lint → VERIFY das migrations **no objeto do banco** → regressão) · **painel de 3 lentes** (verdade+regressão · produto+DADO · red team) de uma vez, cegas entre si, sobre o **diff, o teste rodando e o banco** · conserto conjunto · **juiz fresco** que confirma o conserto **e** audita o dado sobre o acervo real.

**Arquivos-hub com dono único por vez:** `app/api/webhook.py` · `app/agents/graph.py` · `app/services/o_fim_do_atendimento.py` · `app/tasks/buffer_processor.py` (⚠️ registra **24** jobs do scheduler) · `app/core/prompts.py`.

**Ordem de integração (§18.1 da proposta):** BLOCO 0 → E-migrations → A+B (mesma unidade de escrita) → B4 presença → C ficha → D → F. Integração **serial**; regressão depois de cada merge.

**Mutação** em worktree próprio ou com lock exclusivo, restaurada **por cópia** (⛔ nunca `git checkout`); ⛔ `xfail` nunca num guarda que lança processo; ⛔ o orquestrador não roda a suíte inteira enquanto um juiz muta. **Bateria inteira 2 a 4 vezes na SPEC**, nunca a cada commit — a contagem vai no relatório.

**Mexeu em `app/`, `middleware.ts`, `next.config.js` ou env:** `npm run test:rotas-montam` + `next start` + **uma requisição real a `/api/…`** (CLAUDE.md §9.1 — build verde não prova que a aplicação sobe).

**Orçamento:** alvo CRÍTICO ≤ 2,5 M tokens de subagentes. Estourou → **menos lentes, nunca menos mutação**. Faixa de relógio 💭 6–9 h; estourou → resposta escrita de **por que continuar**, não parada (AAA §9.2).

⛔ Nunca `git add -A`, force push, exclusão de lock por timeout, ou alteração de guarda para obter verde. Salve cada conserto **completo** antes do seguinte.

---

## 9. Dossiê e acompanhamento

O Founder acompanha em **https://claude.ai/code/artifact/afe1510d-f31c-4d13-9441-aa920ad2b868** (fonte versionada: `docs/canon/reports/dossies/dossies-autobrokers.html`).

Atualize **durante a execução e a cada bloco fechado**, com um escritor por arquivo: página/aba da EXTRA-001.2, fase, blocos, gates, provas, falhas materiais, próximos passos, implantação e **caixa do Founder**. Preserve as páginas existentes.

🔴 **Leia o HTML publicado inteiro antes de republicar com `url`** e confira o resultado no link. Sem ferramenta ou acesso → atualize a fonte e diga **"publicação do dossiê pendente"**, com o arquivo e o passo exato. ⛔ Nunca alegue que atualizou. ⛔ Nunca publique número de teste ou dado de cliente.

Registre também: `ESTADO-DAS-SPECS.md` (seção da família EXTRA, **sem renumerar**) · `PENDENCIAS.md` (P-PILOTO-13 e 15 com veredito + as novas: cross-tenant, PII em `human_handoff_reason`, `conversation_logs` só grava sucesso, `attendance_transcripts` sem UNIQUE em `message_id`, `'Smith Agent'` como default) · `CHANGE-ADDENDA.md` · `MANIFEST.md` das migrations · a memória local do programa.

---

## 10. Integração, produção e estado final

Push **somente** de commits gateados: `git push origin HEAD:main`, com a **saída real colada** e o head remoto conferido. Main avançou → **não force**: integre e revalide o head efetivo. 🔴 **Entregar não é commitar. É empurrar.**

Implantação pela autoridade vigente — serviços: **backend** (webhook, buffer, scheduler, prompts, providers) e **web** se o card Agente/Equipe mudar. A ordem sai do contrato medido desta SPEC; ⛔ não se copia de SPEC anterior. Depende do clique do Founder → entregue tudo pronto e **o passo exato**; ⛔ não contorne por API.

**Variáveis novas (nome, sem valor):** `TURNO_TTL_SEGUNDOS` · `TURNO_RENOVACOES_MAX` · `JANELA_DADO_CURTO_SEGUNDOS` · `JANELA_FRASE_COMPLETA_SEGUNDOS` · `JANELA_FRASE_INACABADA_SEGUNDOS` · `PRESENCA_DIGITANDO_LIGADA` (nasce **desligada**) · `REPLANEJAMENTOS_MAX`. ⚠️ E corrija `backend/.env.example:40-42`, que ainda ensina os valores velhos do buffer.

**Canário:** o caso-título é **5 mensagens + 1 foto em 12 s → 1 turno**, com TESTE-A/TESTE-B, medindo **turnos**, não balões. Faltou QR, acesso ou a rota de presença → complete tudo que independe disso e registre **gate não comprovado**, com esse nome. ⛔ **Ausência de canário não vira aprovação de produção.**

**No final entregue:**

1. O que mudou para o segurado e o que mudou para a Regina e a Saionara, em linguagem simples.
2. SPEC definitiva, relatório com card e telemetria de 5 linhas, SHAs, migrations com VERIFY/ROLLBACK.
3. Quais gates passaram, quais dependem de ação física, o que **não** foi comprovado.
4. Estado **separado**: implementado / na main / implantado / canário técnico / aceite das pilotos / ativação operacional.
5. Dossiê atualizado, ou pendência de publicação nomeada.
6. Caixa do Founder com as ações concretas mínimas — incluindo 🔴 **qual é o nome do agente da Resulta** (a decisão diz "Amanda"; o banco diz `AutoBrokers`, e a linha `Amanda` está desativada).
7. Handoff: a próxima da fila é a **EXTRA-001.3** (o grupo só recebe o que importa), que **depende** da peça "uma conversa por contraparte" que esta SPEC entrega. ⛔ Não a execute agora.

**Comece pelo preflight, pelo item 0 do BLOCO 0 e pelo card.** ⛔ Não me devolva só uma análise: valide, converta e execute esta SPEC dentro da autorização descrita, seguindo o AAA até a entrega e a comprovação possível.
