---
# ADR-002 — Vault, Conectores, Permissões e Fontes Sensíveis

Status: canonical  
Produto: AutoBrokers.ai  
Sistema: AutoBrokers Intelligence OS  
Tipo: Architecture Decision Record  
Última atualização: 2026-06-06  
Responsável estratégico: Architect / CEO AutoBrokers.ai  
Audiência: Claude Design, Claude Code, Codex, devs, segurança, UX, LLMs estratégicas e time fundador

---

# 1. Decisão

O AutoBrokers.ai terá uma camada central chamada **Vault**.

O Vault será responsável por organizar, proteger e governar:

- credenciais;
- conectores;
- permissões;
- acessos a portais;
- integrações com sistemas externos;
- uso de dados sensíveis;
- fontes de conhecimento;
- chaves de API;
- conexões por corretora;
- permissões por módulo;
- autorizações por ação;
- rastreabilidade de uso.

Decisão principal:

```txt
Toda conexão sensível da corretora deve ser cadastrada uma única vez no Vault e reutilizada por AutoBrokers, Atendimentos, Auxiliares e módulos futuros, sempre respeitando permissões.
```

O Vault não é apenas “um lugar para guardar senha”.

Ele é a camada de confiança do produto.

---

# 2. Por que esta decisão existe

O AutoBrokers.ai terá múltiplas inteligências e módulos operando sobre os mesmos recursos da corretora:

- AutoBrokers central;
- Agentes de atendimento;
- Auxiliares;
- Corredores;
- integrações com seguradoras;
- WhatsApp;
- e-mail;
- sistemas de gestão;
- documentos;
- base de conhecimento;
- portais;
- MCPs;
- APIs;
- rotinas futuras.

Sem um Vault central, o sistema cairia em problemas graves:

- credenciais duplicadas;
- permissões confusas;
- risco de exposição de senha;
- conectores criados várias vezes;
- Auxiliares com acessos indevidos;
- atendimento usando conexão diferente da automação;
- dados sensíveis indo para RAG sem curadoria;
- dificuldade de auditoria;
- dificuldade de revogar acesso;
- risco LGPD;
- risco operacional;
- desorganização para o usuário final.

Portanto, o Vault deve ser pensado cedo, mesmo que sua implementação completa seja progressiva.

---

# 3. Definição curta

Vault é o cofre operacional da corretora dentro do AutoBrokers.ai.

Ele responde:

```txt
O que esta corretora conectou?
Quem pode usar?
Para qual finalidade?
Com qual nível de risco?
Quando foi usado?
O que pode ser feito automaticamente?
O que precisa de aprovação humana?
Como revogar?
```

---

# 4. Escopo do Vault

O Vault cobre seis categorias principais.

## 4.1 Credenciais e segredos

Exemplos:

- login/senha de portal de seguradora;
- token de API;
- chave OAuth;
- refresh token;
- senha de e-mail;
- credencial de sistema de gestão;
- credencial InfoCap;
- credencial Quiver;
- credencial Segfy;
- credencial Capta;
- credencial Evolution API;
- credencial Z-API, se usada;
- credencial SMTP/Resend/SendGrid;
- credencial Google Workspace;
- credencial Microsoft;
- credencial MCP.

---

## 4.2 Conectores

Exemplos:

- WhatsApp;
- e-mail;
- Google Drive;
- Google Calendar;
- Slack;
- Notion;
- GitHub;
- sistema de gestão;
- portal Bradesco;
- portal Porto;
- portal Allianz;
- portal HDI;
- portal Tokio;
- InfoCap;
- Quiver;
- Segfy;
- planilhas;
- webhooks;
- APIs internas;
- APIs de seguradoras;
- telefonia.

---

## 4.3 Fontes de conhecimento

Exemplos:

- documentos da corretora;
- apólices;
- PDFs;
- imagens;
- áudios;
- conversas de WhatsApp;
- manuais internos;
- templates;
- regras comerciais;
- playbooks;
- histórico de atendimento;
- protocolos;
- arquivos de seguradora;
- materiais do Agent OS;
- intake bruto curado.

---

## 4.4 Permissões de uso

Exemplos:

- pode ler;
- pode resumir;
- pode gerar rascunho;
- pode sugerir ação;
- pode executar com aprovação;
- pode executar automaticamente;
- pode acessar documentos;
- pode acessar conversas;
- pode acessar credencial;
- pode abrir portal;
- pode preencher formulário;
- pode enviar mensagem;
- pode consultar sistema;
- pode criar tarefa;
- pode gravar log;
- pode acionar outro Auxiliar.

---

## 4.5 Rastreabilidade

Exemplos:

- quem conectou;
- quando conectou;
- quem usou;
- qual módulo usou;
- qual Auxiliar usou;
- qual agente usou;
- qual ação foi tentada;
- qual ação foi aprovada;
- qual ação foi bloqueada;
- qual dado foi lido;
- qual conector foi chamado;
- qual erro ocorreu;
- qual custo foi gerado.

---

## 4.6 Governança e revogação

Exemplos:

- pausar conector;
- revogar permissão;
- desconectar;
- expirar token;
- exigir nova autenticação;
- bloquear por risco;
- bloquear por tenant;
- bloquear globalmente;
- reduzir permissão;
- obrigar aprovação humana;
- colocar em quarentena;
- impedir ingestão em RAG.

---

# 5. O que o Vault não é

Vault não é:

- uma página visual apenas;
- um gerenciador simples de senhas;
- um lugar para jogar PDFs brutos;
- uma pasta de uploads sem classificação;
- um banco de dados de secrets exposto;
- um sistema de automação separado;
- uma feature opcional;
- um módulo para o usuário técnico mexer em JSON;
- uma permissão genérica “tudo ou nada”.

O Vault deve ser invisível quando possível e explícito quando necessário.

Para o usuário final, a experiência deve ser simples:

```txt
Conecte.
Permita.
Use.
Revogue quando quiser.
```

---

# 6. Princípio central de reutilização

Uma conexão deve ser criada uma vez e reutilizada por vários módulos.

Exemplo:

```txt
A corretora conecta o portal Bradesco uma vez.
Depois, essa conexão pode ser usada por Atendimento, Auxiliares e AutoBrokers, desde que cada uso tenha permissão adequada.
```

Outro exemplo:

```txt
A corretora conecta o WhatsApp uma vez.
Depois, o Atendimento pode responder clientes, um Auxiliar pode preparar mensagens de cobrança, e o AutoBrokers pode sugerir follow-ups — cada um com escopo e aprovação próprios.
```

Regra:

```txt
Conexão é compartilhada.
Permissão é específica.
Ação é auditada.
```

---

# 7. Separação entre conexão, permissão e execução

O sistema deve separar três coisas.

## 7.1 Conexão

A conexão responde:

```txt
A corretora possui acesso a este serviço?
```

Exemplo:

- Google Drive conectado;
- WhatsApp conectado;
- portal Allianz conectado;
- InfoCap conectado;
- e-mail conectado.

---

## 7.2 Permissão

A permissão responde:

```txt
Este módulo/agente/Auxiliar pode usar esta conexão para esta finalidade?
```

Exemplo:

- Auxiliar de Cobrança pode usar WhatsApp apenas para gerar rascunhos;
- Atendimento pode usar WhatsApp para conversas com segurados;
- AutoBrokers pode ler documentos do Drive, mas não editar;
- Auxiliar de Relatório pode ler dados, mas não enviar mensagens.

---

## 7.3 Execução

A execução responde:

```txt
O que foi feito agora, por quem, com qual resultado?
```

Exemplo:

- mensagem preparada;
- mensagem enviada após aprovação;
- documento lido;
- portal consultado;
- erro de login;
- token expirado;
- acesso negado.

---

# 8. Papéis de usuário

O Vault precisa respeitar diferentes papéis.

## 8.1 Admin Global AutoBrokers

Equipe interna AutoBrokers.

Pode:

- criar conectores globais;
- definir templates;
- definir categorias;
- definir riscos;
- publicar conectores;
- bloquear conectores;
- revisar logs globais;
- configurar providers;
- definir padrões de segurança;
- criar Auxiliares globais;
- decidir quais conectores aparecem para corretoras.

Não deve usar credenciais de uma corretora sem permissão e sem log.

---

## 8.2 Dono/Admin da corretora

Usuário principal da corretora.

Pode:

- conectar serviços da corretora;
- autorizar acessos;
- revogar conexões;
- aprovar permissões;
- ativar Auxiliares;
- configurar agentes de atendimento;
- ver execuções;
- ver logs da corretora;
- convidar equipe;
- decidir quem pode usar o quê.

---

## 8.3 Operador da corretora

Usuário comum da corretora.

Pode:

- usar módulos permitidos;
- solicitar ação;
- consultar dados autorizados;
- aprovar ações se tiver permissão;
- usar AutoBrokers;
- usar Atendimentos;
- acompanhar Auxiliares autorizados.

Não deve acessar credenciais.

---

## 8.4 Agente / Auxiliar / Sistema

Entidade automatizada.

Pode:

- agir apenas dentro do escopo permitido;
- acessar apenas fontes autorizadas;
- executar apenas ações permitidas;
- gerar logs obrigatórios;
- pedir aprovação quando necessário.

Não pode decidir sozinho ampliar seu próprio acesso.

---

# 9. Tipos de conectores

## 9.1 Conectores OAuth

Exemplos:

- Google Drive;
- Google Calendar;
- Gmail;
- Microsoft;
- Slack;
- Notion;
- GitHub;
- HubSpot;
- outros SaaS.

Fluxo ideal:

```txt
Galeria de conectores
→ escolher conector
→ explicar permissões
→ conectar via OAuth
→ salvar token seguro
→ confirmar status
→ permitir uso por módulos
```

---

## 9.2 Conectores por API Key

Exemplos:

- Evolution API;
- Z-API;
- webhooks;
- serviços internos;
- APIs de terceiros;
- ferramentas específicas.

Fluxo ideal:

```txt
Informar chave
→ testar conexão
→ salvar segredo
→ definir permissões
→ registrar conector ativo
```

---

## 9.3 Conectores por login/senha

Exemplos:

- portal de seguradora;
- sistema legado;
- portal não-OAuth.

Fluxo ideal:

```txt
Informar credencial
→ armazenar de forma segura
→ testar login em ambiente controlado
→ marcar como portal sensível
→ exigir aprovação para ações críticas
```

Esse tipo tem risco maior.

---

## 9.4 Conectores por arquivo/documento

Exemplos:

- planilha;
- PDF;
- pasta de Drive;
- export de WhatsApp;
- relatório;
- base CSV;
- documentos da corretora.

Fluxo ideal:

```txt
Upload/seleção
→ classificação
→ detecção de PII
→ redaction se necessário
→ aprovação de ingestão
→ indexação controlada
```

---

## 9.5 Conectores internos

Exemplos:

- Supabase;
- conversas;
- documentos;
- mensagens;
- custos;
- logs;
- histórico de atendimento;
- usuários;
- empresas;
- agentes;
- Auxiliares;
- filas.

Esses conectores não precisam aparecer como “conectar”, mas precisam de permissão.

---

# 10. Conectores prioritários

## 10.1 MVP

Para MVP, priorizar conectores de baixo risco e alto valor:

- documentos da corretora;
- base de conhecimento;
- histórico de conversas internas;
- upload manual;
- Google Drive, se simples;
- WhatsApp em modo rascunho/dry-run;
- e-mail em modo rascunho;
- dados internos do sandbox.

Não priorizar:

- portal de seguradora com execução real;
- alteração em sistema externo;
- envio automático sem aprovação;
- InfoCap/Quiver real com escrita;
- ingestão bruta de WhatsApp sem curadoria.

---

## 10.2 Fase intermediária

Adicionar:

- Evolution API;
- WhatsApp real com aprovação;
- InfoCap leitura;
- Quiver leitura;
- Google Workspace;
- e-mail;
- portais de seguradora em modo consulta;
- webhooks internos;
- integração com Atendimentos.

---

## 10.3 Fase avançada

Adicionar:

- portais com automação browser;
- envio externo sem aprovação para ações de baixo risco;
- rotinas agendadas;
- execução multi-etapa;
- atualização em sistemas de gestão;
- integração profunda com seguradoras;
- MCPs externos amplos.

---

# 11. Níveis de risco

Todo conector e toda permissão devem ter nível de risco.

## 11.1 Baixo

Apenas leitura de dados não sensíveis ou dados já autorizados.

Exemplos:

- ler FAQ;
- ler documento interno público;
- consultar template;
- resumir texto fornecido pelo usuário.

Permissão padrão:

```txt
Pode executar sem aprovação, com log.
```

---

## 11.2 Médio

Leitura de dados sensíveis ou geração de rascunhos.

Exemplos:

- ler apólice;
- resumir conversa;
- gerar mensagem para cliente;
- consultar histórico de atendimento;
- analisar documento.

Permissão padrão:

```txt
Pode gerar resultado, mas ações externas exigem aprovação.
```

---

## 11.3 Alto

Ação externa ou acesso operacional sensível.

Exemplos:

- preparar envio de WhatsApp;
- preparar e-mail;
- consultar portal de seguradora;
- consultar sistema de gestão;
- acessar dados financeiros;
- usar credenciais de corretora.

Permissão padrão:

```txt
Exige aprovação humana antes de executar ação externa.
```

---

## 11.4 Crítico

Ação que altera realidade externa ou pode gerar impacto financeiro/legal.

Exemplos:

- enviar mensagem automaticamente;
- alterar cadastro;
- abrir sinistro;
- acionar assistência;
- cancelar serviço;
- enviar documento para seguradora;
- modificar dados em sistema de gestão;
- acionar cobrança;
- acessar portal autenticado e enviar formulário.

Permissão padrão:

```txt
Bloqueado por padrão no MVP.
Só liberar com HITL, logs, rollback e aprovação explícita.
```

---

# 12. Regras de aprovação humana

No MVP:

```txt
Toda ação externa real exige aprovação humana.
```

Ações externas incluem:

- enviar WhatsApp;
- enviar e-mail;
- responder segurado;
- acionar seguradora;
- abrir protocolo;
- acessar portal com envio de formulário;
- alterar sistema de gestão;
- enviar documento;
- criar cobrança;
- atualizar status externo;
- usar credencial sensível de portal.

A aprovação deve mostrar:

- quem vai receber;
- o que será enviado;
- qual conector será usado;
- qual fonte foi usada;
- qual Auxiliar/agente solicitou;
- risco;
- custo estimado;
- botão aprovar;
- botão editar;
- botão recusar.

---

# 13. Política para dados brutos do intake

A pasta `AUTOBROKERS_RESULTA_INTAKE` é material bruto.

Ela pode conter:

- conversas de clientes;
- conversas com seguradoras;
- nomes;
- telefones;
- CPFs;
- e-mails;
- apólices;
- imagens;
- PDFs;
- áudios;
- dados de veículos;
- endereços;
- credenciais;
- informações de sinistro;
- informações sensíveis;
- material de seguradora;
- dados comerciais.

Decisão:

```txt
Intake bruto não pode ser ingerido diretamente no RAG/runtime.
```

Antes de qualquer uso, precisa passar por:

1. inventário;
2. classificação;
3. detecção de PII;
4. redaction;
5. separação por tipo;
6. autorização de uso;
7. transformação em pacote curado;
8. registro de origem;
9. aprovação;
10. indexação controlada.

---

# 14. Política para Agent OS e Corredores

Agent OS, corredores, skills e guardrails são fonte estratégica de conhecimento.

Mas não devem ser copiados brutos para runtime.

Fluxo correto:

```txt
Agent OS / ResultVision / Intake
→ análise
→ extração
→ curadoria
→ pacote de conhecimento
→ validação
→ ingestão controlada
→ uso por AutoBrokers/Atendimento/Auxiliares
```

O Vault precisa registrar:

- origem;
- versão;
- escopo;
- permissão;
- validade;
- público autorizado;
- data de ingestão;
- responsável;
- classificação de risco.

---

# 15. Política de RAG

O RAG deve respeitar o Vault.

Não basta um documento estar no MinIO/Qdrant.

O sistema precisa saber:

- de qual corretora é;
- quem pode consultar;
- qual agente pode usar;
- qual Auxiliar pode usar;
- qual módulo pode usar;
- se contém PII;
- se foi redigido;
- se é global ou privado;
- se pode ser usado para resposta;
- se pode ser usado para ação;
- se pode ser usado para treino/avaliação;
- se deve expirar.

Regra:

```txt
Busca sem permissão é bloqueada.
Documento sem classificação não entra em uso operacional.
```

---

# 16. Conhecimento global vs conhecimento da corretora

## 16.1 Conhecimento global

Criado pelo Admin Global AutoBrokers.

Exemplos:

- conceitos de seguros;
- regras gerais;
- templates genéricos;
- boas práticas;
- documentação de produto;
- playbooks globais;
- modelos de Auxiliares;
- regras de atendimento não sensíveis.

Pode ser compartilhado com todas as corretoras.

Mas ainda precisa versionamento e escopo.

---

## 16.2 Conhecimento da corretora

Pertence a uma corretora específica.

Exemplos:

- documentos internos;
- equipe;
- clientes;
- apólices;
- conversas;
- regras comerciais;
- credenciais;
- templates próprios;
- histórico;
- carteira;
- relatórios.

Nunca deve vazar para outra corretora.

---

## 16.3 Conhecimento híbrido

Exemplo:

```txt
Template global de cobrança + tom personalizado da corretora + lista de clientes da corretora.
```

Precisa respeitar:

- template global;
- dados privados;
- permissão específica;
- logs.

---

# 17. Tenant isolation

O AutoBrokers.ai é multi-tenant.

Regra absoluta:

```txt
Dados, credenciais e conexões de uma corretora nunca podem ser acessados por outra corretora.
```

Isso inclui:

- documentos;
- Qdrant collections;
- MinIO objects;
- Supabase rows;
- logs;
- conversations;
- messages;
- agent configs;
- Auxiliares;
- conexões;
- tokens;
- credenciais;
- execuções;
- aprovações.

Todo design de Vault deve reforçar isolamento por:

- `company_id`;
- policies;
- server-side checks;
- logs;
- permissões;
- namespaces;
- collections separadas quando aplicável;
- nunca expor service role ao client.

---

# 18. Armazenamento de secrets

Decisão:

```txt
Segredos nunca devem ser expostos ao frontend.
```

Regras:

- nunca usar `NEXT_PUBLIC_` para segredos;
- nunca salvar segredo em texto puro;
- nunca imprimir segredo em log;
- nunca retornar segredo por API;
- nunca colocar segredo em documento canônico;
- nunca versionar `.env`;
- usar criptografia;
- usar service role apenas server-side;
- limitar acesso por rota;
- auditar uso.

O frontend pode mostrar:

- status conectado;
- nome do serviço;
- últimos 4 caracteres, se fizer sentido;
- data da conexão;
- quem conectou;
- permissões;
- botão revogar.

O frontend não deve mostrar:

- token completo;
- senha;
- refresh token;
- service role;
- API key completa;
- segredo MinIO;
- senha Redis;
- credencial portal.

---

# 19. Modelo conceitual de dados

Este ADR não fecha schema final.

Mas define entidades necessárias.

## 19.1 Connector Template

Criado pelo Admin Global.

Campos conceituais:

- id;
- nome;
- categoria;
- descrição;
- tipo;
- provider;
- risco;
- escopos disponíveis;
- permissões disponíveis;
- instruções de conexão;
- status;
- visibilidade;
- versão;
- logo/ícone;
- documentação;
- created_at;
- updated_at.

---

## 19.2 Tenant Connection

Instância de conector conectada por corretora.

Campos conceituais:

- id;
- company_id;
- connector_template_id;
- status;
- display_name;
- auth_type;
- encrypted_secret_ref;
- metadata;
- scopes_granted;
- connected_by;
- connected_at;
- last_used_at;
- last_health_check;
- error_state;
- revoked_at.

---

## 19.3 Permission Grant

Permissão de uso para módulo/agente/Auxiliar.

Campos conceituais:

- id;
- company_id;
- tenant_connection_id;
- subject_type;
- subject_id;
- allowed_actions;
- risk_level;
- requires_approval;
- created_by;
- approved_by;
- expires_at;
- status;
- created_at.

`subject_type` pode ser:

- AutoBrokers;
- Atendimento;
- Auxiliar;
- Agente de Atendimento;
- Usuário;
- Sistema.

---

## 19.4 Vault Audit Log

Registro de uso.

Campos conceituais:

- id;
- company_id;
- actor_type;
- actor_id;
- module;
- connection_id;
- action;
- status;
- risk_level;
- approval_id;
- trace_id;
- metadata;
- created_at.

---

## 19.5 Approval Request

Aprovação humana.

Campos conceituais:

- id;
- company_id;
- requested_by_type;
- requested_by_id;
- action_type;
- connection_id;
- summary;
- payload_preview;
- risk_level;
- status;
- approved_by;
- rejected_by;
- decision_reason;
- created_at;
- decided_at.

---

## 19.6 Knowledge Source

Fonte de conhecimento controlada.

Campos conceituais:

- id;
- company_id nullable;
- scope;
- source_type;
- title;
- classification;
- pii_level;
- redaction_status;
- ingestion_status;
- storage_ref;
- vector_ref;
- allowed_modules;
- allowed_agents;
- expires_at;
- created_by;
- approved_by;
- created_at.

---

# 20. Possível mapeamento com Smith Runtime

O Smith já tem parte da infraestrutura.

Provável reaproveitamento:

- `agents`;
- `agent_delegations`;
- `agent_http_tools`;
- `agent_mcp_connections`;
- `agent_mcp_tools`;
- `documents`;
- `conversations`;
- `messages`;
- `memory_settings`;
- `user_memories`;
- `token_usage_logs`;
- `billing`;
- `admin_users`;
- `companies`.

Mas pode faltar uma camada produto para:

- connector templates;
- tenant connections;
- permission grants;
- approval requests;
- vault audit logs;
- auxiliary runs;
- knowledge source classification;
- redaction status.

Decisão:

```txt
Não criar schema sem auditoria técnica.
Primeiro documentar o modelo conceitual.
Depois Claude Code audita tabelas existentes.
Só então propor migrations.
```

---

# 21. Experiência UX do Vault

O Vault não precisa aparecer como “Vault” para o corretor.

Termos visíveis recomendados:

- Conectores;
- Integrações;
- Permissões;
- Fontes;
- Acessos;
- Segurança;
- Conexões da corretora.

Evitar para usuário final:

- Vault;
- Secret store;
- Credential manager;
- MCP;
- OAuth scope, salvo quando necessário;
- token;
- JSON;
- runtime.

---

# 22. Onde aparece no Dashboard da Corretora

O Vault aparece indiretamente dentro de:

```txt
Personalização / Configurações
```

E também dentro dos fluxos de:

- Auxiliares;
- Atendimentos;
- Conectores;
- Conhecimento;
- Seguradoras;
- Corredores;
- AutoBrokers.

Exemplo:

```txt
Ao ativar o Auxiliar de Cobrança, o sistema solicita conexão com WhatsApp ou e-mail.
```

O usuário não precisa ir primeiro numa página técnica de Vault.

O fluxo deve levar ele ao conector certo.

---

# 23. Conectores como experiência estilo ChatGPT Apps

A galeria de conectores deve seguir a lógica:

```txt
Galeria
→ Detalhe do conector
→ Permissões
→ Conectar
→ Testar
→ Pronto
```

Card de conector:

- nome;
- ícone;
- categoria;
- descrição curta;
- status;
- se requer admin;
- se é beta;
- se é seguro;
- botão conectar.

Página de detalhe:

- o que faz;
- por que conectar;
- quais dados acessa;
- quais módulos podem usar;
- permissões;
- risco;
- termos;
- botão conectar.

Modal de permissão:

- permissões claras;
- linguagem simples;
- opção cancelar;
- opção autorizar;
- link para detalhes.

---

# 24. Conectores de seguradoras

Seguradoras são casos especiais.

Uma seguradora pode ter:

- WhatsApp;
- portal;
- 0800;
- API;
- e-mail;
- corretores/canais;
- corredores;
- subcorredores;
- regras por ramo;
- regras por serviço;
- credenciais;
- documentos.

Por isso, uma seguradora pode ser modelada como:

```txt
Conector composto
```

Exemplo:

```txt
Allianz
├── WhatsApp Assistência
├── Portal
├── 0800
├── Residencial
├── Auto
├── Corredor Eletricista
├── Corredor Encanador
└── Regras de acionamento
```

Decisão:

```txt
Seguradoras devem usar o Vault para credenciais e permissões, mas sua experiência de domínio pode ficar dentro de Personalização/Atendimento/Canais conforme UX-001.
```

---

# 25. Conexões de portais autenticados

Portais de seguradoras e sistemas de gestão têm risco alto.

Regras:

- não liberar automação real no MVP;
- começar com cadastro e teste de conexão;
- depois consulta assistida;
- depois preenchimento em dry-run;
- depois execução com aprovação;
- só no futuro execução controlada.

Todo uso deve gerar log.

Se houver browser automation:

- não salvar sessão sem política;
- não expor cookies;
- não imprimir credenciais;
- isolar ambiente;
- ter timeout;
- ter replay;
- ter screenshot redigido se necessário;
- pedir aprovação antes de envio final.

---

# 26. Relação com Auxiliares

Auxiliares dependem do Vault.

Exemplo:

Auxiliar de Cobrança pode precisar:

- base de clientes;
- WhatsApp;
- e-mail;
- regras de comunicação;
- aprovação humana.

Fluxo:

```txt
Ativar Auxiliar
→ identificar conectores necessários
→ verificar conexões existentes
→ solicitar permissões
→ testar
→ ativar
```

O Auxiliar não deve pedir a senha novamente se a conexão já existe.

Ele deve pedir permissão de uso.

---

# 27. Relação com AutoBrokers central

AutoBrokers central pode consultar o Vault para saber:

- quais fontes existem;
- quais conectores estão ativos;
- o que pode acessar;
- o que não pode acessar;
- quais Auxiliares podem ser sugeridos;
- quais ações exigem aprovação;
- quais integrações estão faltando.

Exemplo de resposta:

```txt
Posso preparar os rascunhos de cobrança, mas ainda preciso que você conecte o WhatsApp ou escolha envio por e-mail.
```

AutoBrokers não deve fingir que tem acesso se não tem.

---

# 28. Relação com Atendimentos

Atendimento usa Vault para:

- WhatsApp;
- telefonia;
- portal de seguradora;
- sistema de gestão;
- documentos;
- apólices;
- dados de cliente;
- corredores;
- canais.

Exemplo:

```txt
Para acionar assistência residencial Allianz via WhatsApp, o sistema precisa saber se o canal está configurado e se o agente tem permissão de uso.
```

No MVP, ações de atendimento real devem ser controladas.

---

# 29. Relação com Conhecimento

Conhecimento usa Vault para controlar:

- upload;
- origem;
- escopo;
- classificação;
- PII;
- redaction;
- indexação;
- permissão;
- expiração;
- uso por agente.

Documento sem classificação deve ficar em estado:

```txt
Pendente de curadoria
```

Não deve alimentar resposta operacional.

---

# 30. Relação com Admin Global

Admin Global controla:

- conectores disponíveis;
- templates;
- categorias;
- permissões padrão;
- riscos;
- documentação;
- conectores beta;
- bloqueios globais;
- logs;
- health geral;
- provedores;
- custos;
- políticas.

Admin Global não deve expor complexidade para tenant.

Ele deve preparar o catálogo.

A corretora ativa e personaliza.

---

# 31. Estados de conexão

Estados recomendados:

```txt
Disponível
Conectado
Precisa configurar
Aguardando autenticação
Aguardando aprovação
Ativo
Pausado
Com erro
Token expirado
Revogado
Bloqueado
Beta
Indisponível
```

---

# 32. Health check

Cada conexão deve ter um status de saúde.

Exemplos:

- última conexão bem-sucedida;
- token válido;
- credencial inválida;
- portal fora do ar;
- permissão insuficiente;
- limite atingido;
- erro desconhecido.

O usuário deve ver mensagens simples.

Exemplo:

```txt
A conexão com o Google Drive está ativa.
```

Exemplo de erro:

```txt
Não conseguimos acessar o portal. Revise o login ou tente novamente mais tarde.
```

---

# 33. Logs amigáveis vs logs técnicos

Usuário final deve ver logs amigáveis.

Exemplo:

```txt
Auxiliar de Cobrança usou WhatsApp para preparar 12 mensagens. Nenhuma mensagem foi enviada sem aprovação.
```

Admin técnico pode ver logs técnicos.

Exemplo:

```txt
connector_id=abc action=prepare_message status=success trace_id=xyz
```

Separar visualização.

---

# 34. Política de nomes visíveis

Não usar:

- Smith;
- Agent Smith;
- JARVYS;
- LionClaw;
- OpenClaw;
- LangGraph;
- MCP, salvo área técnica;
- Qdrant;
- MinIO;
- Redis;
- Supabase, salvo admin técnico.

Usar:

- AutoBrokers;
- Conectores;
- Integrações;
- Fontes;
- Permissões;
- Auxiliares;
- Atendimentos;
- Conhecimento;
- Segurança;
- Acessos.

---

# 35. MVP do Vault

## 35.1 O que precisa existir conceitualmente no MVP

Mesmo que visualmente simples:

- conexão pertence a uma corretora;
- conexão tem status;
- conexão tem tipo;
- conexão tem risco;
- permissão é separada de conexão;
- ação externa exige aprovação;
- uso gera log;
- documentos precisam classificação;
- intake bruto é bloqueado.

---

## 35.2 O que pode ficar manual no início

- cadastro de alguns conectores;
- configuração de API;
- curadoria de documentos;
- classificação;
- ativação de fontes;
- liberação para Auxiliares;
- aprovações.

---

## 35.3 O que não entra no MVP

- automação irrestrita;
- portal com envio automático;
- scheduler avançado;
- marketplace público;
- permissões granulares completas;
- ingestão bruta automatizada;
- classificação 100% automática sem revisão;
- multi-provider complexo;
- rotação automática de todos os tokens.

---

# 36. Primeiros conectores recomendados para UX

Para Claude Design, desenhar primeiro com exemplos simples:

1. Google Drive;
2. WhatsApp;
3. E-mail;
4. InfoCap;
5. Portal de Seguradora;
6. Base de Conhecimento;
7. Upload de Documento.

Esses exemplos cobrem quase todos os padrões:

- OAuth;
- API key;
- login/senha;
- arquivo;
- fonte interna;
- conector sensível.

---

# 37. Padrão de tela para conector

Claude Design deve criar um padrão reutilizável.

## 37.1 Galeria

Mostra conectores em cards.

Filtros:

- Todos;
- Comunicação;
- Seguradoras;
- Sistemas;
- Documentos;
- Produtividade;
- Atendimento;
- Dados.

---

## 37.2 Detalhe

Mostra:

- nome;
- descrição;
- benefícios;
- dados acessados;
- módulos que podem usar;
- permissões;
- status;
- histórico;
- botão conectar/desconectar.

---

## 37.3 Permissões

Mostra claramente:

```txt
Este conector poderá:
- Ler arquivos selecionados.
- Usar documentos para responder dentro do AutoBrokers.
- Não poderá enviar ou apagar arquivos.
```

---

## 37.4 Sucesso

Mensagem:

```txt
Conexão realizada com sucesso.
Agora você pode permitir que AutoBrokers, Atendimentos ou Auxiliares usem esta conexão.
```

---

# 38. Mobile-first

No mobile, o Vault deve usar navegação em camadas.

Exemplo:

```txt
Conectores
→ Google Drive
→ Permissões
→ Conectar
→ Status
```

Evitar:

- modais gigantes;
- tabelas;
- excesso de texto;
- configurações avançadas visíveis;
- várias ações na mesma tela.

Usar:

- telas curtas;
- botões grandes;
- estados claros;
- transição lateral;
- voltar fácil;
- breadcrumbs simples, se necessário.

---

# 39. Como Claude Design deve usar este ADR

Claude Design deve:

- desenhar experiência de conectores;
- desenhar galeria;
- desenhar detalhe;
- desenhar permissões;
- desenhar estado conectado;
- desenhar erro/token expirado;
- desenhar fluxo mobile;
- desenhar como aparece dentro de Auxiliares;
- desenhar como aparece dentro de Personalização;
- não criar jargão técnico;
- não criar dashboard denso;
- não criar tela de Vault técnico para usuário final.

---

# 40. Como Claude Code deve usar este ADR

Claude Code deve:

- auditar tabelas existentes antes de criar migrations;
- não criar schema novo sem aprovação;
- reaproveitar estruturas do Smith quando possível;
- garantir server-only para secrets;
- não expor service role;
- não imprimir credenciais;
- não mexer em intake bruto sem tarefa específica;
- criar adapters progressivos;
- implementar primeiro estados visuais e mocks seguros, se necessário;
- separar conexão, permissão e execução;
- adicionar logs para ações sensíveis;
- bloquear ações externas por padrão.

---

# 41. Critérios de pronto

O Vault estará no caminho certo quando:

- conectores forem cadastrados uma vez;
- permissões forem por módulo/uso;
- Auxiliares reutilizarem conexões;
- Atendimento reutilizar conexões;
- AutoBrokers souber o que pode acessar;
- ações externas pedirem aprovação;
- logs existirem;
- segredos não aparecerem no frontend;
- dados de uma corretora não vazarem para outra;
- documentos sensíveis não entrarem no RAG sem curadoria;
- usuário final entender o que está autorizando.

---

# 42. Decisão final

O Vault é obrigatório para o AutoBrokers.ai escalar com segurança.

Ele deve ser criado como uma camada central, não como função escondida de cada módulo.

Direção final:

```txt
Conectar uma vez.
Permitir com clareza.
Usar com segurança.
Auditar sempre.
Revogar facilmente.
```

Sem Vault, Auxiliares, Atendimentos, AutoBrokers e Conectores viram peças soltas.

Com Vault, o AutoBrokers.ai vira uma plataforma confiável, reutilizável e escalável para corretoras de seguros.