# SPEC-034 — Harness Robusto: arquitetura multi-agente para atendimento perpétuo

**Status:** proposta para aprovação do founder
**Data:** 2026-07-13
**Autor:** Fable 5 (líder técnico do atendimento)
**Escopo:** atendimento WhatsApp (Even + corredores de seguradoras), com extensão natural para portais (cobrança/SPEC-023, vidros/SPEC-025) e auxiliares.

---

## 1. Por que existimos frágeis hoje (diagnóstico honesto)

O que já temos de BOM (e vamos preservar):

- Corredores como **dados versionados** (playbooks com âncoras → respostas), não código.
- Freio de teste (executa tudo e cancela antes de confirmar) — essa invenção vira peça-chave do Cartógrafo (§5.3).
- Guarda anti-invenção determinística (placa/telefone), parser de botões/listas/flows, dossiê mastigado, fila por seguradora, retry, loop-guard por passo.
- Bateria de 25 suítes de testes que roda a cada mudança.

As 5 fragilidades estruturais (todas confirmadas em incidentes reais):

| # | Fragilidade | Evidência |
|---|---|---|
| F1 | **Invisibilidade**: a conversa com a seguradora vive só no Redis com TTL de 6h. Não é espelhada no dashboard, não é auditável depois. | Founder buscou Porto/Azul/Allianz no dashboard: não existem. O incidente da Azul (acionamento que nunca começou) só foi visto porque ELE foi olhar o WhatsApp. |
| F2 | **Sem vigilância de desfecho**: nenhum processo verifica "esse acionamento chegou a um fim?". Travou = silêncio eterno até um humano reparar. | Porto travada 2min no submenu de bateria; founder teve que clicar. Azul nunca iniciou e ninguém soube. |
| F3 | **Conhecimento estático**: âncoras regex vêm de conversas passadas. URA muda um botão → passo não casa → trava. Não existe "mapa vivo" dos fluxos. | Submenu "Entendi. O que você precisa?" existia no mapa da Azul e não no da Porto (mesma família de URA). |
| F4 | **Recuperação rasa**: quando nenhuma âncora casa, o adaptativo tenta às cegas — sem o mapa da URA, sem saber "onde estou no fluxo e qual é o objetivo". | "Ciente, pode prosseguir" respondido a aviso informativo (corrigido com noop, mas o padrão se repetirá a cada URA nova). |
| F5 | **Sem ciclo de melhoria**: cada erro exige o founder reclamar → Fable corrigir → deploy. Nada aprende sozinho; a tendência com mudanças externas é DEGRADAR. | Todo o histórico de 10-12/07. |

Conclusão: o founder está certo — no formato atual, a entropia vence. A resposta não é "mais regra no prompt" (cabresto), é **camadas de agentes com responsabilidades separadas**, como um harness de verdade.

---

## 2. Como um harness de ponta funciona (e o que copiamos)

O que faz o Claude Code / harnesses da Anthropic e OpenAI serem robustos não é mágica do modelo — é engenharia em volta dele:

1. **Loop agêntico com verificação**: perceber → decidir → agir → **verificar o resultado** → repetir. Nunca one-shot. (Nosso motor de URA já é um loop; falta a etapa "verificar desfecho".)
2. **Erros são sinal, não parada**: falhou → diagnostica → tenta caminho diferente → só então escala. Escada de recuperação com degraus finitos.
3. **Guardas determinísticas em volta do LLM** (hooks): o que é crítico (dinheiro, identidade, confirmação de serviço) nunca depende só do modelo. Já fazemos (freio, anti-invenção) — formalizamos.
4. **Subagentes especializados**: contexto isolado por tarefa, cada um com ferramentas próprias. Um agente que faz tudo se perde; seis agentes com um papel cada não.
5. **Memória em camadas**: sessão (Redis), caso (Supabase), conhecimento (RAG), aprendizado (evals). O mega-bug do histórico (12/07) mostrou o custo de UMA camada quebrada.
6. **Bateria de evals que nunca dorme**: toda conversa real vira caso de replay; regressão dispara alarme antes do cliente sentir.
7. **Tiering de modelos**: rotina roda em trilho determinístico (custo zero) ou modelo barato; decisões difíceis (desvio de fluxo, recuperação) rodam em modelo de ponta. Baixo volume × alto valor.

Estado da arte que valida cada peça (pesquisa 13/07/2026):

- **Botium Crawler** (mercado de QA de chatbots, hoje Cyara): crawler que navega a árvore de conversa de um bot clicando em todos os quick-replies/botões e gera o mapa completo do fluxo + datasets de teste. É EXATAMENTE o Cartógrafo — só que nós crawleamos o bot da seguradora, não o nosso.
- **Frameworks de self-healing para agentes LLM** (arXiv 2026, Union.ai, Latitude): padrão consolidado = detecção de falha → classificação do tipo → estratégia de recuperação específica → escalação. É a Sentinela.
- **Nubank**: framework de avaliação contínua (evals + GEPA/DSPy) para agentes de atendimento em escala de 100M+ usuários; **Decagon** (líder em CX agents) usa GEPA em produção. É o Auditor + auto-evolução.

---

## 3. A arquitetura: 6 agentes + o cérebro

```
                        ┌─────────────────────────────────────────────┐
                        │                 PRODUÇÃO                     │
  Cliente ──WhatsApp──▶ │  EVEN (atendente)                            │
                        │   └─ aciona ─▶ MOTOR DE CORREDOR (âncoras)   │
  Seguradora ─WhatsApp▶ │                 │ desvio? ─▶ CÉREBRO v2      │
                        │                 │            (LLM forte      │
                        │                 │             + Mapa de URA) │
                        └────────┬────────┴──────────────┬────────────┘
                                 │ tudo é espelhado       │ travou?
                        ┌────────▼────────┐      ┌────────▼────────┐
                        │ ESPELHO         │      │ SENTINELA       │
                        │ persiste 100%   │      │ detecta stall/  │
                        │ das conversas   │      │ loop → escada   │
                        │ (dashboard)     │      │ de recuperação  │
                        └────────┬────────┘      └────────┬────────┘
                                 │                        │ alerta
                        ┌────────▼────────┐      ┌────────▼────────┐
                        │ AUDITOR         │      │ VIGIA           │
                        │ replay + score  │      │ desfecho de tudo│
                        │ de cada conversa│      │ + digest diário │
                        └────────┬────────┘      └─────────────────┘
                                 │ drift/erro
      ┌─────────────┐   ┌────────▼────────┐
      │ CARTÓGRAFO  │──▶│ ALFAIATE        │──▶ playbook vN+1 ─▶ SIMULADOR ─▶ produção
      │ mapeia URAs │   │ propõe/aplica   │         (replay das conversas reais)
      │ (nº de      │   │ patches c/      │
      │  exploração)│   │ classes de risco│
      └─────────────┘   └─────────────────┘
```

Regra de ouro da arquitetura: **falha nunca é silenciosa e nunca é terminal sem handoff**. Todo caminho termina em: resolvido, OU entregue a humano com dossiê + alerta, OU alarme de anomalia. "Travado em silêncio" deixa de existir por construção.

---

## 4. Onda 1 — visibilidade e vigilância (fazer AGORA, antes de retomar testes)

### 4.1 Espelho — persistência total das conversas com seguradoras

**Problema que resolve:** F1 (e a reclamação direta do founder de 13/07).

- Cada mensagem in/out da conversa com a seguradora é gravada em `conversations`/`messages` (conversa por `(company, insurer_phone, case)` com marcação `kind: insurer_dispatch`), exatamente como o agente a vê — botões renderizados como "Botão 1: X / Botão 2: Y" (o founder confirma no dashboard SE a LLM está enxergando todos os cards).
- O transcript estruturado (JSON com payload interativo bruto) vai para tabela própria `dispatch_transcripts` — substrato para Auditor, Alfaiate e replay.
- Dashboard: as conversas de seguradora aparecem na lista (com badge "Acionamento — Porto"), lincadas ao atendimento do cliente que as originou.
- Causa-raiz de hoje documentada: `webhook.py` retorna cedo quando o roteador de dispatch assume (linhas ~423-425) e o transcript vive só no Redis com TTL 6h (`dispatch_router.py:37`). O Espelho grava ANTES/DURANTE o roteamento, não depois.

### 4.2 Vigia — watchdog de desfecho + alertas + digest

**Problema que resolve:** F2 ("como ninguém viu isso? quem vai ver?").

- Todo acionamento nasce com desfecho esperado e prazo (ex.: guincho urgente → estado terminal em ≤ 30min).
- Job a cada 60s (já temos o scheduler do follow-up): sessão sem estado terminal no prazo → alerta no grupo de suporte + evento no portal admin ("Acionamento Porto do caso X parado há 12min no passo Y — transcript aqui").
- Estados terminais: `captured/monitoring` (sucesso), `test_aborted` (teste ok), `needs_human` (handoff feito). Qualquer outro no prazo = anomalia.
- Digest diário no grupo/admin: N atendimentos, % autônomo, handoffs por causa, anomalias, tempo médio.
- Health: webhook vivo, instância Evolution conectada, fila por seguradora.

### 4.3 Sentinela v1 — detector de travas em tempo real + escada de recuperação

**Problema que resolve:** F2/F4 ("toda vez EU preciso clicar pra destravar").

- Detecção **determinística** (state machine + timers, não LLM — barata, incansável, sem alucinação):
  - URA mandou mensagem e nós não respondemos em 45s → suspeita de passo não mapeado.
  - Nós respondemos e URA calada além do padrão dela → suspeita de resposta rejeitada silenciosamente.
  - Mesmo par (passo, resposta) 3x → loop (já existe; integra aqui).
- **Escada de recuperação** (degraus finitos — resposta direta à pergunta "supervisor não vai virar loop?"):
  1. T+45s: repassa a mensagem ao Cérebro v2 com o Mapa de URA + objetivo + histórico ("você está no fluxo da Porto, objetivo recarga de bateria, apareceu esta tela nova — qual opção avança?").
  2. T+3min ou 2ª falha: tenta "cutucada" segura (reenviar a última resposta válida OU "Voltar"/opção de menu quando o mapa indicar).
  3. Máximo 2 intervenções por sessão. Falhou → `needs_human` com dossiê + alerta do Vigia. **Nunca loop infinito, por construção.**
- Cada intervenção da Sentinela vira evento registrado → alimenta o Alfaiate ("a URA da Porto mostrou tela desconhecida X — provável mudança de menu").

**Critério de aceite da Onda 1:** o founder faz um teste e (a) vê a conversa inteira com a seguradora no dashboard em tempo real, (b) se travar, recebe alerta no grupo em ≤ 3min com o transcript — sem precisar descobrir sozinho, (c) se a Sentinela destravar sozinha, ele vê o evento registrado.

---

## 5. Onda 2 — conhecimento vivo (mapa + cérebro + cartógrafo + simulador)

### 5.1 Mapa de URA (o "guarda-chuva" que o founder descreveu)

- Nova tabela `ura_maps`: árvore versionada por seguradora — cada nó = {texto da mensagem (normalizado), tipo (menu/pergunta/informativo/terminal), opções (rótulo + o que responde), qual resposta avança para qual nó, hash do conteúdo}.
- Fontes: (1) conversas reais espelhadas (Espelho), (2) exploração do Cartógrafo, (3) os playbooks atuais (semente inicial).
- O mapa NÃO substitui o playbook — o playbook é o "caminho feliz" compilado; o mapa é o território completo que o Cérebro consulta nos desvios.

### 5.2 Cérebro Adaptativo v2

- Hoje: adaptativo às cegas. Passa a receber: mapa da URA + posição atual estimada + objetivo do caso + slots + transcript da sessão + espaço de ações permitidas (responder opção do menu, texto livre, Voltar, abortar-para-humano).
- Modelo de ponta (Fable/Opus-tier) — é chamado só nos desvios (baixo volume, alto valor). O trilho de âncoras continua custando zero.
- Responde E emite evento `map_drift` quando percebe que a tela real difere do mapa → alimenta Cartógrafo/Alfaiate.
- Responde à cena que o founder descreveu: "botão que era A virou B" → o Cérebro raciocina pelo OBJETIVO (pedir bateria) sobre o mapa + tela real, escolhe B, segue o atendimento, e registra a mudança para o sistema se atualizar.

### 5.3 Cartógrafo (o Botium Crawler do nosso lado)

Viabilidade: **SIM** — tecnicamente é só conversar com a URA via WhatsApp e clicar/digitar cada opção. Provas: Botium Crawler faz isso há anos com chatbots; nosso parser de botões/listas já lê os cards; nosso freio de teste já sabe parar antes de confirmar serviço.

- Roda no **número de exploração** (instância Evolution GO de teste — já criada em 11/07; NUNCA o número de produção).
- Estratégia BFS educada: entra no fluxo, percorre um ramo até o freio (âncora de finalize → aborta com a resposta de cancelamento), volta ao menu, próximo ramo. Cadência lenta (mensagem a cada 20-40s), horário de baixa (2h-5h), 1 seguradora por noite.
- **Freios do Cartógrafo (inegociáveis):** nunca responde a confirmação final com "sim"; nunca explora ramo de SINISTRO além do 1º nó; usa CPF de teste combinado com o founder; para se a URA pedir dado que não temos; máximo N mensagens por sessão.
- Saída: Mapa de URA vN + diff legível vs vN-1 ("Porto: submenu novo após 'Bateria' com 3 opções; rótulo 'Técnico' virou 'Técnico residencial'").
- Frequência: sob demanda (founder ou evento `map_drift` da Sentinela) + quinzenal automática.
- Riscos e mitigação: bloqueio do número (cadência + abort educado + número dedicado descartável); URAs com memória de CPF (o mapa registra o comportamento — já conhecemos das auditorias); custo (desprezível — mensagens de WhatsApp e um modelo barato para classificar telas).
- **Firecrawl NÃO serve aqui** (é para páginas web) — o conceito é o mesmo, a ferramenta é nossa (Evolution + parser + motor). Para PORTAIS, o equivalente já existe e é melhor: Playwright + cadeia de API (SPEC-033) — o Cartógrafo de portais é a evolução natural do que a cobrança já faz.

### 5.4 Simulador (gêmeo digital dos corredores)

- Replay: toda conversa real espelhada vira um "boneco de URA" que responde como a seguradora respondeu. Playbook novo roda contra as últimas K conversas reais + o mapa — sem WhatsApp, sem seguradora, em segundos.
- É o degrau que permite ao Alfaiate validar patches automaticamente antes de produção (e à bateria de testes crescer sozinha: cada atendimento real de hoje é um teste de regressão de amanhã).

---

## 6. Onda 3 — auto-evolução (alfaiate + auditor + RAG)

### 6.1 Alfaiate (auto-ajuste de playbooks com classes de risco)

Resposta direta ao medo "IA ajustando fluxo não é perigoso?": é, se for sem freio. Por isso classes de risco:

| Classe | Exemplos | Ação |
|---|---|---|
| **Auto-aplica** | novo aviso informativo (noop), mudança de rótulo de botão equivalente, tela intermediária nova sem coleta | aplica + valida no Simulador + notifica no admin: "Mudou X→Y na Allianz. Já ajustei (playbook v12). Diff aqui." |
| **Aprovação 1-clique** | mudança em passo de coleta de dados, ordem de fluxo, novo ramo | propõe patch + resultado do simulador; corredor entra em modo cauteloso (Cérebro v2 supervisiona cada passo) até aprovação |
| **Nunca automático** | finalize_anchors, abort replies, identificação/CPF, qualquer coisa que confirme serviço | só humano aprova; até lá, handoff nesses pontos |

- Todo patch é uma nova VERSÃO do playbook (já são dados) → rollback instantâneo.
- O aviso no portal admin que o founder pediu ("mudou XXX para YYYY e já fizemos o ajuste") é exatamente o output da classe Auto-aplica.

### 6.2 Auditor (a fábrica de melhoria contínua — casa com SPEC-021)

- Scorecard de TODA conversa (LLM-judge barato): re-pediu dado conhecido? repetiu mensagem? inventou fato/ação? tom humanizado? resolveu?
- Métricas no admin: taxa de autonomia (meta 97%), tempo de ciclo por corredor, handoffs por causa-raiz, drift por seguradora.
- Regressão: replay noturno dos corredores contra o Simulador; queda de nota = alarme ANTES de cliente sentir.
- Fase 2: otimização GEPA/DSPy dos prompts da Even com os scorecards como feedback (o caminho Nubank/Decagon) — ganho comprovado, mas só depois que o resto estiver de pé.

### 6.3 RAG (deixa de ser prateleira vazia)

O RAG vira o destino natural do que os agentes produzem — sem depender de humano subir documento:

- Mapas de URA em linguagem natural ("como funciona o fluxo de guincho da Porto") → o Cérebro e a Even consultam.
- Procedimentos por seguradora (franquias de vidro, o que cada assistência cobre, telefones) extraídos das conversas reais + docs.
- Aprendizados do Auditor ("na Azul, cliente com 2 veículos: sempre confirmar placa antes de acionar").
- Curadoria: Alfaiate/Auditor propõem, versionam e datam os chunks (framework do SPEC-010 já prevê).

---

## 7. Respostas diretas às perguntas do founder

1. **"Vale a pena pausar os testes e dar esse salto agora?"** Sim — com prazo. Onda 1 é pré-requisito para testar com dignidade (sem ela, cada teste custa a SUA atenção como sentinela humana). Mas o mega-bug do histórico (12/07) era o maior vilão da conversa com o cliente e JÁ está corrigido — então a pausa é curta: Onda 1 → retoma testes → Ondas 2-3 em paralelo com testes.
2. **"A LLM vê todos os cards?"** Vê — botões, listas e flows são convertidos em texto ("Botão 1: X") desde 11/07. O que NÃO existia era você poder conferir isso. O Espelho resolve: o dashboard mostrará exatamente o que ela vê.
3. **"Preciso tirar print de todas as telas?"** Não. As telas entram sozinhas pelo Espelho (conversas reais) e pelo Cartógrafo (exploração). Prints continuam úteis só para fluxo que nunca visitamos.
4. **"É possível uma IA que navega os menus e monta o mapa?"** Sim (Botium Crawler prova há anos). Com número separado (GO), freio antes de confirmar, cadência educada. §5.3.
5. **"Firecrawl consegue?"** Não para WhatsApp (é para web). Para portais, nosso Playwright/API-first (SPEC-033) já é o caminho certo. O Cartógrafo usa nossa própria stack.
6. **"Supervisor não vai virar loop?"** Não: detecção é determinística, recuperação tem no máximo 2 degraus, e o degrau final é sempre handoff com dossiê + alerta. Loop infinito é impossível por construção.
7. **"IA ajustando fluxos não estraga tudo?"** Com classes de risco + simulador + versões com rollback + aviso no admin: o risco fica menor que o atual (hoje quem "ajusta" é a entropia).
8. **"Como é a sua inteligência? dá pra copiar?"** A parte copiável está no §2 (loop com verificação, escada de recuperação, guardas, subagentes, memória, evals, tiering). A parte não-copiável é a qualidade bruta do modelo — por isso o Cérebro v2 usa modelo de ponta nos desvios e trilho determinístico no resto.
9. **"100% sem travar, para sempre?"** Compromisso honesto: 97% autônomo (sua meta), 3% handoff impecável, e **0% travado em silêncio** — toda exceção vira alerta em minutos com transcript. Prometer 100% de autonomia seria a mentira que combatemos no atendente.
10. **"Criar outro chat Fable para isso?"** Onda 1 é código do próprio atendimento — faço NESTE chat. Cartógrafo/Alfaiate (Ondas 2-3) podem ganhar um chat dedicado depois, com este SPEC como contrato.

---

## 8. Sequência de execução

| Onda | Entregas | Pré-requisito para |
|---|---|---|
| **1 — Visibilidade & Vigilância** | Espelho (dashboard + transcripts persistentes) · Vigia (watchdog de desfecho + alertas + digest) · Sentinela v1 (stall detection + escada com Cérebro atual) | retomar testes Porto/Azul/Zurich |
| **2 — Conhecimento vivo** | Schema Mapa de URA · Cérebro v2 (mapa + objetivo) · Cartógrafo v1 (sob demanda, número GO) · Simulador/replay | Alfaiate |
| **3 — Auto-evolução** | Alfaiate (classes de risco + notificação admin) · Auditor (scorecards + métricas + regressão noturna) · RAG alimentado pelos agentes · GEPA depois | perpetuidade |

Depois da Onda 1: retomar os testes reais (Porto bateria fim-a-fim, Azul do zero, Zurich primeira vez) — agora com o founder vendo tudo no dashboard e alertas ativos.

---

## 9. Decisões pendentes do founder

1. Aprovar este SPEC (ou apontar ajustes).
2. Onda 1 começa imediatamente após aprovação, neste chat.
3. CPF de teste dedicado para o Cartógrafo (pode ser o mesmo dos testes atuais?).
4. Cadência inicial do Cartógrafo: sob demanda apenas (recomendado para começar) ou já quinzenal?
