# HANDOFF — Novo chat Fable: Atendimento de Assistência Auto (corredores por seguradora)

**De**: Fable 5 (líder técnico atual) · **Para**: novo chat Fable dedicado ao atendimento · 2026-07-11
**Modelo em produção**: `claude-sonnet-5` (atendente "Even" e core "AutoBrokers"). Já validado.

> Cole este documento (ou o "Prompt de abertura" no fim) para iniciar o novo chat. O objetivo é
> deixar o **atendimento de assistência auto por WhatsApp** funcionando de ponta a ponta, sem humano,
> com um corredor ESPECÍFICO para cada seguradora. **NÃO comece codando.** Primeiro auditar, entender,
> perguntar, propor. Só depois executar.

---

## 1. O que precisa acontecer (a visão do founder)

Fluxo completo, do início ao fim, sem travar e sem humano (exceto onde a regra manda chamar humano):

1. O segurado manda mensagem no **WhatsApp da corretora**.
2. O **atendente** (Even) inicia a fila de atendimento, com conversa humana, empática, educada.
3. Coleta só o que falta — **identifica o cliente na InfoCap** e **NÃO pede o que já está na apólice**
   (placa, veículo, coberturas). Não ser redundante, não ser burro.
4. Confere coberturas/assistência da apólice.
5. Faz o **acionamento na seguradora** seguindo o **corredor específico daquela seguradora** no
   WhatsApp dela (cada uma tem um menu/fluxo diferente).
6. **Avisa o cliente ANTES** que vai acionar, e quando tiver retorno (protocolo, horário, detalhes)
   **volta e avisa** — o cliente nunca pode se sentir abandonado esperando.
7. **Acompanha até finalizar** (a fila não acaba no acionamento) — protocolo de acompanhamento
   inteligente, sem ser chato, para o cliente sentir que cuidamos dele de verdade.

Regras duras:
- **Trava final**: NUNCA finalizar/confirmar o acionamento real na seguradora nesta fase (fluxo
  completo, mas para antes de efetivar). Se passar, cancelar.
- **Sinistro → humano.** **Sem corredor para a seguradora → humano.** Qualquer situação fora do
  script que não dê para resolver com inteligência → registrar o motivo e **chamar humano** (nunca
  travar em loop nem inventar).
- Determinístico onde dá, mas o atendente **tem o direito de pensar/raciocinar** para sair de
  imprevistos — não pode ser burro, engessado, cheio de cabresto.

---

## 2. O que deu ERRADO antes (não repetir) — o desastre da Yelum

Ver as memórias `incidente-2026-07-10-fixes` e os prints do founder. Resumo dos erros:
- Corredores criados **genéricos**, "da cabeça", sem ler as conversas reais de cada WhatsApp de
  seguradora → o atendente **não conseguia clicar nas opções do menu** da Yelum, travou 4x no CPF,
  a conversa foi encerrada pela seguradora.
- Atendente **burro**: listou apólice vencida como ativa, esqueceu a conversa, repetiu perguntas,
  respondeu antes do cliente terminar de digitar, **inventou** placa (ABC1D23) e telefone
  ((47) 99999-9999), mandou "bateria" quando o cliente pediu **guincho**, e **mentiu** que já tinha
  acionado.
- Espelho no dashboard mostrava seguradora errada e faltava quase tudo da conversa real.

Já foram corrigidos na base (modelo Sonnet, vigência real, anti-invenção, resumo pro analista, loop
guard, freios). **Mas os corredores precisam ser refeitos a partir das conversas REAIS**, uma
seguradora de cada vez, com profundidade.

---

## 3. O que LER antes de qualquer código (obrigatório)

**Conversas reais (a fonte da verdade — não inventar nada):**
- Conversas dos atendentes humanos com os segurados (fluxo com o cliente):
  `C:\Users\amand\Projetos\AUTOBROKERS RESULTA\.worktrees\hotfix-runtime-bundle\AUTOBROKERS_AGENT_OS_WORKSPACE\AUTOBROKERS_RESULTA_INTAKE\autofleet\conversas com clientes - assistencia auto\`
  (cada subpasta = 1 atendimento real; servem para quase todos os casos).
- Conversas de acionamento no WhatsApp de cada seguradora (o corredor):
  `...\AUTOBROKERS_RESULTA_INTAKE\autofleet\conversas com seguradoras - auto\`
  (cada seguradora tem UMA conversa longa; **usar as MAIS RECENTES** — os menus mudam).

**Specs e memória:**
- `docs/canon/specs/SPEC-031-assistencia-auto-whatsapp-multi-seguradora.md` (corredores auto) —
  revisar profundamente, provavelmente melhorar.
- `docs/canon/specs/SPEC-017-external-attendant-smith-whatsapp.md` (atendente externo).
- `docs/canon/ADR-003-atendimento.md`, e as memórias `incidente-2026-07-10-fixes`,
  `fable-lead-progress-2026-07-10`.
- Código: `backend/app/services/corridor_playbooks.py` (corredores como DADO versionado — NÃO criar
  motor paralelo), `insurer_dispatch_service.py`, `dispatch_router.py`, `webhook.py`,
  `app/core/prompts.py` (ATTENDANCE_BASE_PROMPT).

**Seguradoras por prioridade** (mais fluxo primeiro): **Allianz, Porto, HDI, Liberty/Yelum**, depois
Tokio, Azul, Mapfre, e as demais. Fazer **um corredor de cada vez**, a fundo, com a conversa real.

---

## 4. Como o novo chat deve trabalhar (processo, não código de primeira)

1. **Auditar**: ler as conversas reais + SPEC-031 + o código atual dos corredores. Mapear, por
   seguradora, o menu/fluxo EXATO do WhatsApp dela (âncoras de texto, opções, ordem das perguntas).
2. **Comparar** com o que está em `corridor_playbooks.py` e listar as diferenças/erros.
3. **Perguntar ao founder** o que estiver ambíguo (ele pediu para perguntar). Propor o melhor caminho.
4. **Só então executar**, um corredor por vez, com testes house-style (replay offline das frases
   reais da URA, `check()`, sem pytest) antes de deploy.
5. Cada corredor: `ura_steps` (âncora regex → resposta com slots), `finalize_anchors` (freio antes de
   efetivar), `handoff_triggers` (sinistro/sem-corredor → humano), passos `noop` para mensagens de
   fila, `capture_anchors` (protocolo). Determinístico + inteligente para imprevistos.
6. Também revisar a **conversa com o cliente**: coletar só o que falta, avisar antes de acionar,
   voltar com o retorno, acompanhar até o fim. E garantir que o **espelho no dashboard** mostre a
   conversa real completa, nome certo, seguradora certa.

---

## 5. Inteligência / RAG (levantado pelo founder)

Os atendentes/auxiliares/chat principal precisam de **base de conhecimento** — hoje o RAG está vazio.
Colocar no RAG: as conversas reais com seguradoras e com clientes, conhecimento de seguros, coberturas,
termos. Existe uma spec de RAG em standby (provavelmente desatualizada) — revisar e priorizar na
sequência (ver checklist). Isso aumenta a inteligência de todo o AutoBrokers.

---

## 6. Arquitetura — o que respeitar (sem estrutura paralela)

- Tudo dentro da estrutura **Smith** única (motores compartilhados). Corredores = **dado versionado**
  em `corridor_playbooks.py`, não código novo por seguradora.
- Respeitar **global vs. por-corretora** (nada global que devia ser por-corretora e vice-versa).
- Nada duplicado/paralelo. Portal Admin integrado a tudo. Reusar SPEC-019 (rotinas), SPEC-020
  (portal-worker), SPEC-016 (policy intelligence/InfoCap).

---

## 7. Prompt de abertura (cole isto no novo chat)

> Você é o Fable 5, líder técnico do AutoBrokers, dedicado a deixar o **atendimento de assistência
> auto por WhatsApp** perfeito e em produção. Leia primeiro `docs/canon/HANDOFF-NOVO-CHAT-ATENDIMENTO-AUTO.md`
> inteiro e os arquivos que ele indica (conversas reais nas pastas de intake, SPEC-031, SPEC-017,
> `corridor_playbooks.py`, as memórias do incidente). **NÃO comece codando.** Faça uma auditoria
> profunda, mapeie o corredor EXATO de cada seguradora a partir das conversas reais (comece por
> Allianz, Porto, HDI, Liberty/Yelum), compare com o que existe, me faça as perguntas que tiver e
> proponha o plano. Só execute depois de alinhado. Regras duras: corredor específico por seguradora
> (não genérico), atendente inteligente (não pede o que já está na apólice, não inventa, não repete,
> avisa o cliente antes de acionar e volta com o retorno, acompanha até o fim), **trava final** (fluxo
> completo mas parar antes de efetivar o acionamento; se passar, cancelar), sinistro/sem-corredor →
> humano. Sem estrutura paralela — corredores são dado em `corridor_playbooks.py`. Modelo já é
> claude-sonnet-5. Ao terminar cada corredor, teste em modo teste (só o número 5547988087463 recebe).
