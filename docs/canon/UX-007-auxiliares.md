# UX-007 — Auxiliares

Status: canônico ativo  
Owner: AutoBrokers.ai Architect  
Última atualização: 2026-06-06

---

## 1. Decisão principal

O módulo **Auxiliares** será a camada de automação inteligente do AutoBrokers.ai.

Auxiliares são tarefas/agentes especializados que ajudam a corretora a executar processos repetitivos, recorrentes ou semi-autônomos.

O termo público é:

```txt
Auxiliares
```

Não usar “Rotinas” como nome principal, para diferenciar a marca AutoBrokers.ai de Claude Routines.

---

## 2. Inspiração

Referência principal:

- Claude Routines: criação por nome, instruções, gatilho, conectores, comportamento e permissões.

Referências secundárias:

- ChatGPT Apps/Connectors: galeria, detalhe, conexão e permissões.
- Smith: agents, subagents, delegations, tools, MCP, RAG, logs e billing.
- ResultVision: domínio de seguros, seguradoras, corredores, atendimento e fluxos operacionais.

---

## 3. Diferença entre AutoBrokers, Agentes e Auxiliares

### AutoBrokers

Copiloto central da corretora. Fixo. Não-personalizável. Conversacional.

### Agentes de atendimento

Atendem clientes externos da corretora. Personalizáveis. Usados em canais como WhatsApp, ligações e atendimento.

### Auxiliares

Automatizam tarefas internas ou semi-operacionais.

Exemplo:

```txt
Auxiliar de cobrança de documentos pendentes
Auxiliar de resumo diário
Auxiliar de renovação
Auxiliar de sinistros
```

---

## 4. MVP de Auxiliares

A primeira versão deve ser simples.

### P0 recomendado

- Galeria de Auxiliares globais.
- Ativação por corretora.
- Personalização mínima.
- Execução manual.
- Histórico simples de execução.
- Aprovação humana antes de ação externa real.

### Fora do P0

- scheduler complexo;
- criação livre por prompt;
- autonomia sem aprovação;
- execução em portal real de seguradora;
- múltiplos gatilhos avançados;
- marketplace público.

---

## 5. Estrutura de navegação

Sidebar:

```txt
AUTOMAÇÃO
- Auxiliares
```

Dentro da página de Auxiliares:

```txt
Abas:
- Meus Auxiliares
- Galeria
- Execuções
```

### Meus Auxiliares

Lista dos Auxiliares ativados pela corretora.

### Galeria

Biblioteca de Auxiliares prontos, criados pelo Admin Global.

### Execuções

Histórico de execuções, status, erros, custos e aprovações.

---

## 6. Fluxo de ativação

```txt
Auxiliares → Galeria → Selecionar Auxiliar → Detalhe → Personalizar → Permissões → Ativar
```

A página de detalhe deve mostrar:

- o que o Auxiliar faz;
- quais dados usa;
- quais conectores precisa;
- quais ações pode executar;
- se precisa de aprovação humana;
- custo estimado;
- frequência/gatilho se aplicável.

---

## 7. Fluxo de criação futura

A criação por prompt é desejada, mas não deve ser P0.

Fluxo futuro:

```txt
Auxiliares → Novo auxiliar → descrever tarefa → AutoBrokers gera rascunho → usuário revisa → configura gatilho/conectores/permissões → ativa
```

Essa experiência deve se inspirar em Claude Routines.

---

## 8. Gatilhos possíveis

### P0

- execução manual;
- botão “executar agora”.

### P1

- horário diário/semanal;
- evento interno;
- novo atendimento;
- documento pendente;
- prazo vencido;
- webhook simples.

### P2

- integração com n8n;
- cron avançado;
- evento de portal;
- evento de seguradora;
- evento de WhatsApp;
- evento do sistema de gestão.

---

## 9. Conectores e permissões

Auxiliares não devem pedir credenciais novas sempre que possível.

Regra:

```txt
Conexões são compartilhadas pelo Vault da corretora.
```

Exemplo:

```txt
Portal Bradesco conectado uma vez → usado por Atendimento, Auxiliares e AutoBrokers
```

Cada Auxiliar deve declarar:

- quais conexões usa;
- quais permissões precisa;
- quais ações pode executar;
- se precisa de aprovação humana.

---

## 10. Aprovação humana

No MVP, qualquer ação externa real deve exigir aprovação humana.

Exemplos de ação externa:

- enviar WhatsApp;
- enviar e-mail;
- alterar cadastro;
- abrir protocolo;
- consultar portal autenticado;
- baixar documento sensível;
- responder cliente.

O Auxiliar pode preparar a ação, mas o humano aprova.

---

## 11. Primeiros Auxiliares recomendados

### 11.1 Resumo diário da operação

Gera resumo de atendimentos, pendências, documentos, retornos e riscos do dia.

### 11.2 Cobrança de documentos pendentes

Identifica pendências e prepara mensagens para clientes.

### 11.3 Follow-up de renovação

Lista renovações próximas e sugere ações.

### 11.4 Pendências de sinistro

Monitora sinistros e documentos faltantes.

### 11.5 Relatório operacional diário

Prepara mensagem de fechamento do dia para dono/gestor.

---

## 12. Interface visual

A página deve ser limpa.

Estrutura:

```txt
Título: Auxiliares
Descrição curta
Busca ou comando: “O que você quer automatizar?”
Abas: Meus Auxiliares | Galeria | Execuções
Cards simples
```

Evitar poluição visual.

Cards devem conter:

- nome;
- categoria;
- descrição curta;
- status;
- conectores necessários;
- ação principal.

---

## 13. Relação com Admin Global

Admin Global cria:

- templates globais de Auxiliares;
- categorias;
- conectores necessários;
- permissões padrão;
- prompts base;
- limites;
- políticas de uso.

Corretora faz:

- ativação;
- personalização;
- conexão de credenciais;
- aprovação;
- acompanhamento.

---

## 14. Critérios de sucesso

Auxiliares estarão bem desenhados quando:

1. corretora entende o que cada Auxiliar faz;
2. ativação é simples;
3. permissões são claras;
4. nada executa ação externa sem aprovação no MVP;
5. conecta com o Vault;
6. usa motor Smith sem criar runtime paralelo;
7. histórico mostra o que aconteceu;
8. experiência parece Claude Routines adaptado para seguros.
