# SPEC-045 — Personalização reorganizada, WhatsApp por função e o botão do agente

> Aprovada pelo founder em 20/07/2026. Reorganiza o dashboard nas 3 camadas
> (SPEC-044), resolve a confusão de WhatsApp com o modelo POR FUNÇÃO com
> compartilhamento seguro, e entrega o botão liga/desliga do atendimento
> (observação → atendimento no MESMO número).

## 1. Grade nova de Personalização (menos cliques, zero jargão)

- **🤖 AutoBrokers — Chat Principal** (card DIRETO; o card "Agentes" morre).
  Subtítulo fixo: "Chat Principal". Dentro: explicação em 2-3 frases do que
  ele é e faz (copiloto interno; navega InfoCap, conhecimento, rotinas,
  operação) + configurações atuais (tom, idioma, criatividade). Nome de
  exibição SEMPRE "AutoBrokers da {corretora}" (dinâmico — já é template).
- **🏢 Corretora** (o hub da empresa): Dados da corretora · **Agente de
  Atendimento** (movido p/ cá) · **WhatsApp da corretora** (hub novo, §3) ·
  Suporte humano · Equipe · **Conhecimento da corretora** (movido) ·
  **Custos e Uso** (movido de Configurações; total + por pessoa).
- **🔌 Conectores** (com a escolha corretora/pessoal da SPEC-044) ·
  **Seguradoras** · **Corredores** · **Prontidão** (mantidos).
- **Configurações** (menu lateral) vira 100% PESSOAL: Dados pessoais · Senha ·
  Aparência · **Meu conhecimento** (novo) · **Meu consumo** (só o próprio).
- Limpeza global de sujeira: badges/textos "MVP ativo", "sandbox", "dry-run",
  "sem envio real", "em breve" órfãos → substituídos por status REAIS
  (Ativo/Conectado/Pendente/Observando) ou removidos. Ajuda contextual: ícone
  "?" discreto nos hubs abre modal explicativo curto (não poluir a página).

## 2. Agente de Atendimento (dentro de Corretora)

- Card e página SEM nome próprio fixo: título "Agente de Atendimento",
  subtítulo com o nome escolhido ("Sandra — atendendo pela Resulta Seguros").
  Varrer TODO texto fixo "Even" restante no frontend (títulos, breadcrumbs,
  descrições) → papel ou nome configurado.
- **Pronome: REMOVIDO** (campo e variável saem do blueprint; a LLM resolve).
- **Mensagem de abertura**: default novo com variáveis
  "Olá! Sou {{attendant_name}}, da {{company_name}}. Como posso ajudar?" +
  nota na UI: "É o ponto de partida — se o cliente já disser o que precisa,
  o agente vai direto ao assunto." (é como o runtime já se comporta).
- **BOTÃO LIGAR/DESLIGAR (a peça central)** — controla `agents.is_active`:
  - DESLIGADO = "👁 Observando em silêncio": o número continua pareado, a
    equipe humana atende, e o sistema captura tudo (Espelho). O agente NÃO
    responde ninguém.
  - LIGADO = "💬 Atendendo": o agente passa a responder no MESMO número.
  - GARANTIA BACKEND (o coração da spec): com o agente OFF, o webhook de
    atendimento NÃO gera resposta, MAS espelha a conversa e alimenta a
    captura da Parte 1 (attendance_transcripts) — é a transição
    observação→atendimento SEM re-parear, exatamente o fluxo do founder.
  - Confirmação de 1 clique ao ligar ("A partir de agora o agente responde
    os segurados neste número. Ligar?") + registro em Atividades.

## 3. WhatsApp da corretora — hub por FUNÇÃO com compartilhamento seguro

Modelo: números por FUNÇÃO, nunca por pessoa. Máximo 2 funções visíveis:

| Função | O que faz | Obrigatório? |
|---|---|---|
| **Atendimento & Acionamentos** | recebe os segurados; aciona seguradoras; é o número observado na fase de observação | 1 por corretora |
| **Auxiliares & Avisos** | cobranças, campanhas/leads, relatórios, alertas | OPCIONAL — default: usa o número de Atendimento |

- **Corretora pequena (1 número só): SUPORTADO e seguro** — é o default.
  Auxiliares enviam pelo número de Atendimento com as guardas do §4.
- Hub mostra os números conectados (função, número, status vivo, desde
  quando) + botão "Conectar número" → wizard: escolhe a função → instruções
  (WhatsApp NORMAL, não Business; celular carregado; ~2 min) → QR → verificação
  automática ("recebemos o sinal do número ✓") → pronto.
- Ao conectar um 2º número para Auxiliares: envios de auxiliares migram para
  ele automaticamente (routing por purpose — já existe no backend).
- Avisos honestos no wizard quando for usar 1 número para tudo: "Mensagens de
  cobrança e avisos sairão do mesmo número do atendimento. Se um cliente
  estiver em atendimento, os envios de auxiliar para ele aguardam na fila."

## 4. Guardas anti-conflito (backend — determinístico, custo zero)

O medo do founder ("cobrança no meio do atendimento / resposta de cobrança
confunde o atendente") vira 3 regras de código:

1. **Fila de cortesia (outbound de auxiliar)**: antes de enviar a um número,
   o serviço de envio de plataforma consulta se há conversa de ATENDIMENTO
   ativa com aquele cliente (últimas N horas, Redis/conversations). Se sim →
   adia (fila com retry em 2-6h, marcador Redis); loga em Atividades
   ("cobrança adiada: cliente em atendimento").
2. **Contexto na resposta (inbound pós-auxiliar)**: todo envio de auxiliar é
   registrado (billing_sent_log já existe; generalizar em `platform_sends`
   leve). Quando o cliente responde e o atendente assume a conversa, o
   contexto injeta uma NOTA: "há X dias este cliente recebeu {cobrança da
   parcela Y / mensagem de boas-vindas}" — o agente responde sabendo do que
   se trata, sem confusão.
3. **Observador × atendimento no mesmo número**: já é TAP por construção
   (o Espelho captura e o pipeline segue) — nada a mudar, só documentar.

## Invioláveis
- Reusar `integrations.purpose` (attendance | auxiliary | observer | dispatch)
  — NENHUMA estrutura nova de canal.
- O toggle nunca derruba a captura (Espelho é independente do agente).
- tsc + bateria + deploys api+web + smoke antes de reportar.
