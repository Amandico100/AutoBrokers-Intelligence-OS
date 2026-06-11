---

# SPEC-003 — Knowledge/RAG/Memory Architecture

**Status:** CANÔNICO após aprovação do fundador/Architect.
**Projeto:** AutoBrokers Intelligence OS
**Relacionado:** SPEC-002, ADR-001, ADR-002, ADR-003, UX-007, ROADMAP-001, 41C.0, 41C.1
**Objetivo:** definir a arquitetura oficial de conhecimento, RAG, memória, curadoria e migração do legado para Agents, SubAgents, Auxiliares e Corredores.

---

## 1. Decisão oficial

O AutoBrokers terá uma arquitetura de conhecimento em camadas:

```txt id="vxa2ef"
1. Global AutoBrokers Knowledge
2. Global Insurance / Carrier Knowledge
3. Tenant / Corretora Knowledge
4. Agent / SubAgent Knowledge
5. Workflow / Corredor Knowledge
6. Conversation / Case Memory
7. Operational / Audit Memory
8. Connector / Portal Knowledge
```

Essas camadas não podem ser misturadas.

O RAG do Smith será reaproveitado como base técnica, mas a camada AutoBrokers precisa adicionar governança, escopo, curadoria, versionamento e separação global/local.

---

## 2. Lei central

```txt id="2zu0fc"
Conhecimento global não pode conter dado local de corretora.
Conhecimento local não pode contaminar o global.
Memória de atendimento não é base de conhecimento.
Logs/auditoria não são RAG por padrão.
Corredor é estrutura/workflow, não apenas documento RAG.
Segredo nunca entra em RAG.
```

---

## 3. O que o Smith já tem

O Smith já possui uma base técnica forte:

```txt id="wl91cn"
documents
company_id obrigatório
agent_id opcional
MinIO para arquivos
Qdrant por empresa
chunking
embeddings
BM25/sparse
hybrid retrieval
retrieval_mode em agents
is_hyde_enabled em agents
session_summaries
user_memories
memory_settings
conversation_logs
sanitization_jobs
benchmark flow
```

Essa base deve ser aproveitada. É proibido criar um motor RAG paralelo sem autorização explícita.

---

## 4. Estado atual após 41C.1

Após o batch 41C.1:

```txt id="alddqx"
documents tem RLS ligado.
documents tem policies de service_role e authenticated own company.
retrieval foi ajustado para isolamento por agent_id.
tenant-wide docs continuam possíveis via agent_id null.
não existe conhecimento global ainda.
não existe coluna scope ainda.
não existe coleção Qdrant global ainda.
documents está vazio.
```

Isso significa que a base está segura para evoluir, mas ainda não está completa para o produto final.

---

## 5. Objetivo da camada de conhecimento

A camada de conhecimento deve permitir:

```txt id="x3fdtf"
1. Criar inteligência global do AutoBrokers.
2. Criar dossiês globais de seguradoras/produtos.
3. Permitir que cada corretora adicione sua base local.
4. Permitir que cada Agent/SubAgent tenha conhecimento específico.
5. Permitir que corredores tenham fases, checklists e critérios.
6. Permitir memória de atendimento sem vazar para RAG global.
7. Migrar conhecimento legado com curadoria.
8. Auditar, versionar e medir qualidade.
```

---

# Parte A — Taxonomia oficial

## 6. Global AutoBrokers Knowledge

Conhecimento global criado pela equipe AutoBrokers.

Exemplos:

```txt id="y5agla"
playbooks de atendimento
tom de voz padrão
regras de humanização
políticas de segurança
guardrails gerais
métodos de triagem
scripts-base
perguntas inteligentes
fluxos conceituais
boas práticas de atendimento
```

Uso:

```txt id="eyd0op"
Agents principais
SubAgents especialistas
Auxiliares globais
Corredores
Treinamento de respostas
```

Formato recomendado:

```txt id="tocb0f"
principalmente estruturado
parcialmente RAG textual curado
versionado
read-only para corretoras
```

Não pode conter:

```txt id="2bwxta"
dados reais de clientes
dados internos de uma corretora específica
credenciais
prints de sistemas
informações sensíveis de produção
```

---

## 7. Global Insurance / Carrier Knowledge

Conhecimento global sobre seguradoras, produtos, canais e condições gerais.

Exemplos:

```txt id="4zxxlf"
dossiê Allianz residencial
dossiê Porto auto
canais de assistência
procedimentos de sinistro
condições gerais públicas
coberturas genéricas
exclusões comuns
documentos exigidos
telefones e canais oficiais
regras por produto
```

Uso:

```txt id="getdsk"
SubAgent especialista de apólice
SubAgent especialista de seguradora
Corredor de assistência
Corredor de sinistro
Auxiliar de conferência de documentos
Atendimento WhatsApp
```

Formato recomendado:

```txt id="5vtiwh"
RAG textual para documentos longos
JSON estruturado para canais, procedimentos, campos obrigatórios e regras
versionamento obrigatório
validade/fonte obrigatória
```

Regra:

```txt id="bg8p9f"
Condições gerais podem ir para RAG.
Regras operacionais críticas devem virar estrutura/checklist.
```

---

## 8. Tenant / Corretora Knowledge

Conhecimento local da corretora.

Exemplos:

```txt id="63v0a6"
nome da corretora
equipe
horários
telefones
tom local
seguradoras atendidas
processos internos
regras comerciais
carteira
documentos internos
preferências de atendimento
responsáveis por área
```

Uso:

```txt id="57icay"
Agent principal da corretora
SubAgents da corretora
Auxiliares instalados na corretora
Atendimentos
Corredores locais
```

Formato recomendado:

```txt id="nkeryw"
documents com company_id da corretora
agent_id null para conhecimento compartilhado da corretora
agent_id específico para conhecimento de um Agent/SubAgent
```

Regra:

```txt id="jq2r7m"
Tenant knowledge nunca vira global automaticamente.
Qualquer promoção para global exige curadoria manual.
```

---

## 9. Agent / SubAgent Knowledge

Conhecimento específico de um Agent ou SubAgent.

Exemplos:

```txt id="u1ltzm"
documentos de um especialista de apólice
instruções de um especialista de sinistro
materiais de um agente de vendas
checklist de um auxiliar específico
manuais de ferramenta de um subagent
```

Uso:

```txt id="3tfl18"
Agents/SubAgents com retrieval_mode ativo.
```

Regra de isolamento:

```txt id="yfdz2x"
Agent A não pode consultar documentos do Agent B.
Agent A pode consultar:
- seus próprios documentos;
- documentos tenant-wide da corretora;
- conhecimentos globais explicitamente permitidos.
```

SubAgents podem ter:

```txt id="v0qoqx"
RAG
memória
segurança
tools
MCP
prompt/persona
```

SubAgents não devem ter no MVP:

```txt id="xt4r3t"
WhatsApp direto
Widget público
especialistas próprios
commerce
```

---

## 10. Workflow / Corredor Knowledge

Conhecimento de processo, fase e orquestração.

Exemplos:

```txt id="ro32b7"
entrada
identidade
levantamento
apólice
decisão
humanização
acionamento
acompanhamento
encerramento
critérios de passagem
slots obrigatórios
ações permitidas
HITL obrigatório
```

Formato recomendado:

```txt id="mt8nnr"
estruturado
schema
workflow config
checklist
phase contract
não apenas RAG
```

Regra:

```txt id="6cg8nj"
Corredor não é documento.
Corredor é runtime/workflow com fases, estado e critérios.
```

RAG pode apoiar o corredor, mas não deve substituir sua estrutura.

---

## 11. Conversation / Case Memory

Memória do atendimento/caso.

Exemplos:

```txt id="mgh40a"
resumo da conversa
decisões tomadas
pendências
próximos passos
dados coletados
status do atendimento
última intenção do segurado
histórico do caso
```

Armazenamento esperado:

```txt id="zsoj00"
session_summaries
user_memories
conversations
messages
case-specific future tables
```

Regra:

```txt id="807jmx"
Case memory não é knowledge global.
Case memory não deve ser usado em RAG geral sem curadoria.
```

---

## 12. Operational / Audit Memory

Memória operacional do sistema.

Exemplos:

```txt id="f2v3h0"
logs
execuções de auxiliares
approval_requests
vault_audit_log
custos
falhas
ações externas
testes
eventos de integração
```

Uso:

```txt id="9shzce"
auditoria
debug
governança
compliance
analytics
```

Regra:

```txt id="jf7s7p"
Operational memory não é RAG por padrão.
Pode virar conhecimento apenas após curadoria explícita.
```

---

## 13. Connector / Portal Knowledge

Conhecimento sobre conectores, portais e integrações.

Exemplos:

```txt id="limzvp"
endpoints
contratos de API
schemas de payload
mapeamentos de campos
selectors de browser
passos de portal
limitações de provedor
rate limits
```

Regra absoluta:

```txt id="hv47qt"
credenciais nunca entram aqui.
segredos ficam somente no Vault.
```

Formato recomendado:

```txt id="30acvl"
structured metadata
connector_templates
tenant_connections metadata
docs técnicos curados
browser playbooks versionados
```

---

# Parte B — Modelo de escopo

## 14. Escopos oficiais

Todo documento/conhecimento deve pertencer a um escopo lógico:

```txt id="e3v1vm"
global_autobrokers
global_carrier
tenant
agent
workflow
case
operational
connector
```

No estado atual do banco, `documents` ainda não tem coluna `scope`. A fase 41C.2 deve adicionar isso de forma controlada.

---

## 15. Regra de company_id

Hoje `documents.company_id` é obrigatório. Isso deve ser preservado para não quebrar o Smith.

Para conhecimento global, há duas opções:

```txt id="g18h17"
Opção A — tornar company_id nullable.
Opção B — criar um owner interno AutoBrokers Global e usar scope='global_*'.
```

Decisão recomendada para MVP:

```txt id="z2bva1"
Opção B.
```

Motivo:

```txt id="e1kc61"
não quebra NOT NULL existente
mantém compatibilidade com serviços atuais
mantém auditoria de propriedade
permite RLS segura
evita reescrever fluxo de upload inteiro agora
```

Portanto, conhecimento global deve ter:

```txt id="q1ci42"
company_id = empresa interna AutoBrokers Global
scope = global_autobrokers ou global_carrier
```

Nunca usar uma corretora real como owner global.

---

## 16. Regra de agent_id

```txt id="tmh6an"
agent_id null = conhecimento tenant-wide ou global-wide
agent_id preenchido = conhecimento específico daquele Agent/SubAgent
```

Retrieval deve respeitar:

```txt id="hppcnw"
se agent_id informado:
  buscar docs do agent_id
  + docs tenant-wide agent_id null
  + docs globais permitidos

se agent_id não informado:
  buscar apenas tenant-wide/company-wide permitido
```

---

# Parte C — Retrieval oficial

## 17. Ordem de recuperação de contexto

Para uma resposta do Agent/SubAgent, a ordem lógica deve ser:

```txt id="a4ftqj"
1. System prompt / blueprint / security settings
2. Estado atual da conversa/caso
3. Memória curta da sessão
4. Knowledge do Agent/SubAgent
5. Knowledge tenant-wide da corretora
6. Knowledge global explicitamente permitido
7. Structured registries/checklists aplicáveis
8. Tools/MCP/Vault, quando autorizado
```

RAG textual não deve atropelar guardrails estruturados.

---

## 18. Regra de prioridade

Quando houver conflito:

```txt id="tlcelm"
guardrail estruturado > política de segurança > dado local da corretora > dado global > inferência do modelo
```

Exemplo:

```txt id="5951qy"
Se o global diz "pergunte CPF para identificar",
mas o tenant define que a corretora primeiro pede placa,
o Agent pode seguir o fluxo local desde que não viole segurança.
```

---

## 19. Knowledge refs

Templates globais de Auxiliares e blueprints de Agents devem poder declarar dependências de conhecimento.

Formato recomendado em `default_config`:

```json id="vqbkim"
{
  "runtime": {
    "kind": "smith_agent_blueprint",
    "agent_blueprint": {}
  },
  "knowledge": {
    "requires": [
      {
        "scope": "global_autobrokers",
        "namespace": "atendimento-humanizado",
        "version": "v1",
        "required": true
      },
      {
        "scope": "global_carrier",
        "carrier_slug": "allianz",
        "product_slug": "residencial",
        "required": false
      }
    ],
    "tenant_customization": {
      "allowed": true,
      "recommended": true
    }
  }
}
```

Isso não copia documentos para o template. Apenas declara dependência.

---

## 20. Instalação de Auxiliar com knowledge refs

Ao instalar um Auxiliar global:

```txt id="4zvm3x"
1. Cria tenant_auxiliary.
2. Cria Agent/SubAgent local quando runtime = smith_agent_blueprint.
3. Salva agent_id local.
4. Mantém knowledge refs globais no config.
5. Permite adicionar knowledge local da corretora depois.
```

O template global continua sendo modelo. O Agent local pode ser personalizado.

---

# Parte D — Global Knowledge

## 21. Estrutura futura mínima para 41C.2

A fase 41C.2 deve adicionar ao `documents` algo próximo de:

```txt id="my256v"
scope
knowledge_class
namespace
visibility
version
curation_status
valid_from
valid_until
source_kind
source_ref
metadata
```

Campos podem ser ajustados após inspeção técnica, mas o conceito é obrigatório.

Valores recomendados:

```txt id="92ry9q"
scope:
- tenant
- agent
- global_autobrokers
- global_carrier

knowledge_class:
- playbook
- carrier_dossier
- product_conditions
- guardrail_reference
- script
- checklist
- manual
- connector_reference

curation_status:
- draft
- review
- approved
- published
- deprecated
- quarantined
```

---

## 22. Coleção Qdrant global

O sistema atual usa coleção por empresa:

```txt id="u2vmt9"
company_{company_id}
```

Para global knowledge, o recomendado é criar coleção separada:

```txt id="poje5r"
autobrokers_global
```

Ou outra nomenclatura clara.

Payload mínimo dos chunks globais:

```txt id="53e9cf"
document_id
scope
knowledge_class
namespace
version
carrier_slug
product_slug
valid_until
curation_status
source_hash
```

Regra:

```txt id="6cc64k"
Busca global só pode ocorrer quando explicitamente permitida pelo Agent/template/contexto.
```

---

## 23. Global read-only

Corretoras não editam conhecimento global.

Permissões:

```txt id="eusg43"
Admin Global AutoBrokers:
  cria, edita, publica, deprecia global knowledge

Corretora:
  lê indiretamente via Agent/Assistant
  não altera
  não vê documentos internos brutos se não for apropriado

Agent:
  consulta apenas refs permitidas
```

---

# Parte E — Tenant e Agent Knowledge

## 24. Conhecimento da corretora

O conhecimento local da corretora deve continuar usando o fluxo Smith:

```txt id="7xddtw"
Admin → Empresas → Base de Conhecimento
upload vinculado à corretora
opcionalmente vinculado a Agent/SubAgent
MinIO
Qdrant company_{company_id}
```

Regras:

```txt id="62f9e8"
agent_id null = compartilhado pela corretora
agent_id preenchido = específico daquele Agent/SubAgent
```

---

## 25. Personalização local de Auxiliar global

Quando um Auxiliar global é instalado, a corretora pode personalizar:

```txt id="w1aqmf"
prompt local
modelo
tom
horários
documentos locais
seguradoras atendidas
permissões Vault
conectores
MCPs
HTTP tools
guardrails locais
```

Mas não deve editar diretamente:

```txt id="x4h3b9"
template global original
documentos globais
dossiês globais aprovados
SPECs canônicas
```

---

## 26. Atualização de blueprint global

Quando um template global é atualizado:

```txt id="hm6xol"
não sobrescrever automaticamente personalização local
não apagar documentos locais
não trocar agent local sem confirmação
```

Deve existir futuramente uma política:

```txt id="8w1dkr"
aplicar atualização global
revisar diff
manter customizações locais
rollback
```

---

# Parte F — Corredores e SubCorredores

## 27. Corredor não é RAG

Corredor é workflow estruturado.

Um corredor deve ter:

```txt id="wre6s1"
fases
estado
slots
critérios de entrada
critérios de saída
ações permitidas
HITL obrigatório
SubAgents por fase
conectores necessários
documentos exigidos
fallback humano
auditoria
```

RAG entra como suporte, não como orquestrador.

---

## 28. Exemplo: Assistência Residencial Allianz

Estrutura esperada:

```txt id="2r632b"
Workflow:
Assistência Residencial

Carrier:
Allianz

Canal:
WhatsApp

Fases:
1. Entrada
2. Identidade
3. Levantamento
4. Apólice
5. Decisão
6. Humanização
7. Acionamento
8. Acompanhamento
9. Encerramento

Orquestrador:
Agent Atendimento Assistência Residencial

SubAgents:
- Especialista Identidade
- Especialista Apólice
- Especialista Cobertura
- Especialista Acionamento
- Especialista Comunicação

Conhecimento:
- playbook global de atendimento
- dossiê Allianz residencial
- documentos locais da corretora
- memória do caso
```

---

## 29. Como usar legado em corredores

O legado ResultVision/Agent OS deve ser classificado como:

```txt id="yivjrz"
SPEC
WORKFLOW
AGENT_PROMPT
STRUCTURED_JSON
CHECKLIST
RAG_GLOBAL
RAG_CARRIER
GOLDEN_TEST
DISCARD
DO_NOT_MIGRATE
```

Não copiar bruto. Não importar n8n como runtime. Não abrir credenciais. Não importar PII.

---

# Parte G — Structured vs RAG

## 30. O que deve ser estruturado

Deve ser estruturado, não RAG solto:

```txt id="59zoam"
fases de corredor
slots obrigatórios
action_safety
HITL rules
permissões
Vault refs
schemas
contratos de payload
policy guards
regras de fallback
listas de actions
status machine
gate de CPF/identidade
```

Motivo:

```txt id="1ue9sy"
isso exige previsibilidade, não recuperação semântica solta.
```

---

## 31. O que pode ser RAG textual

Pode ser RAG:

```txt id="ezicko"
condições gerais
manuais de seguradora
playbooks longos
FAQ
scripts explicativos
trechos de política
documentos internos
materiais de treinamento
```

Desde que tenha:

```txt id="fig8ky"
fonte
escopo
curadoria
validade
versão
status
```

---

## 32. O que não pode ir para RAG

Proibido:

```txt id="f9of1w"
senhas
tokens
client_token
api_key
credenciais
dados bancários sensíveis
prints de login
cookies
2FA
PII sem necessidade
logs crus de atendimento
mensagens completas não sanitizadas
documentos de uma corretora no global
```

---

# Parte H — Memórias

## 33. Memória curta

Memória curta é contexto da conversa atual.

Exemplos:

```txt id="d7fmaf"
última pergunta
dados coletados na sessão
status do fluxo
pendência imediata
```

Não deve virar RAG persistente sem curadoria.

---

## 34. Memória de caso

Memória de caso acompanha um atendimento/sinistro/assistência.

Exemplos:

```txt id="293t4g"
resumo
decisões
pendências
próximos passos
documentos solicitados
status do acionamento
```

Deve ser vinculada a:

```txt id="myl2ef"
company_id
agent_id
conversation_id
case_id futuro
```

---

## 35. Memória de usuário

Memória de usuário pode guardar fatos úteis, respeitando LGPD.

Exemplos:

```txt id="rb5j14"
preferência de canal
perfil de atendimento
dados recorrentes autorizados
```

Regras:

```txt id="d7i4a1"
ter política de retenção
ter possibilidade de exclusão
não salvar dado sensível sem necessidade
não virar global
```

---

## 36. Memória operacional

Memória operacional é para governança:

```txt id="8ufdgu"
custos
execuções
falhas
aprovações
auditoria
```

Não é fonte de resposta ao cliente por padrão.

---

# Parte I — Segurança e LGPD

## 37. Invariantes de isolamento

```txt id="y5p3kt"
corretora A nunca acessa knowledge da corretora B
agent A não acessa docs agent B
global não contém dados locais
case memory não vira global
segredos ficam no Vault
ações externas passam por HITL
```

---

## 38. RLS

`documents` deve manter:

```txt id="xf6t7f"
RLS enabled
service_role full access
authenticated own company
```

Para global knowledge futuro:

```txt id="k8y42g"
acesso direto de authenticated deve ser restrito
consulta global deve passar pelo backend/service role
backend aplica refs/escopos permitidos
```

---

## 39. Retrieval trace

Toda resposta com RAG deve futuramente registrar:

```txt id="4q9fnh"
document_ids usados
scope
knowledge_class
agent_id
company_id
chunk ids
score
global refs usados
```

Isso pode ir para `conversation_logs.rag_chunks` ou equivalente.

---

# Parte J — Curadoria

## 40. Status de curadoria

Conhecimento global deve ter status:

```txt id="tbwewv"
draft
review
approved
published
deprecated
quarantined
```

Só `published` entra em produção.

---

## 41. Versionamento

Todo conhecimento global deve ter:

```txt id="1vmsot"
version
created_at
updated_at
source
source_hash
valid_from
valid_until
owner
reviewer
```

Condições gerais e dossiês de seguradora precisam de validade.

---

## 42. Golden tests

O legado possui padrões de golden tests/replay gates. Devem ser reaproveitados como inspiração.

Uso futuro:

```txt id="mpu0b9"
testar retrieval correto
testar política de identidade
testar não vazamento
testar resposta humanizada
testar fase de corredor
testar ação externa bloqueada sem HITL
```

---

# Parte K — Legado

## 43. Regra de migração do legado

Nenhum conteúdo legado entra no sistema sem classificação.

Pipeline obrigatório:

```txt id="xgbfdr"
1. inventariar
2. classificar
3. sanitizar
4. decidir destino
5. converter
6. revisar
7. publicar
8. testar
```

---

## 44. Destinos possíveis

```txt id="45pg3c"
SPEC
structured registry
workflow/corredor
agent blueprint
subagent prompt
global RAG
carrier RAG
tenant RAG
checklist
golden test
discard
do-not-migrate
```

---

## 45. O que reaproveitar do legado

Reaproveitar com curadoria:

```txt id="rj6kgc"
9 fases de atendimento
modelos de corredor
guardrails
policy guards
recipes de seguradora
signals
CSAT model
coverage matrices
golden tests
schemas/contratos
templates humanizados
```

---

## 46. O que descartar

Descartar como runtime:

```txt id="j5batd"
n8n como orquestrador principal
Drizzle/Replit runtime antigo
código Express legado
credenciais antigas
workflows com PII
INTAKE
quarentena
arquivos com segredos
duplicações antigas
```

---

# Parte L — Admin e UX

## 47. Admin Global — Conhecimento

Criar futuramente área:

```txt id="iok9pk"
Admin → Conhecimento Global
```

Funções:

```txt id="xezs5v"
gerenciar playbooks globais
gerenciar dossiês de seguradora
gerenciar versões
publicar/deprecar documentos
ver golden tests
ver uso por Agents/Auxiliares
```

---

## 48. Admin Empresa — Base de Conhecimento

Continuar usando:

```txt id="evbu0o"
Admin → Empresas → Base de Conhecimento
```

Mas evoluir para separar:

```txt id="jpdihh"
documentos da corretora
documentos tenant-wide
documentos por Agent/SubAgent
status de ingestão
qualidade
última atualização
```

---

## 49. Dashboard da corretora

No futuro, a corretora deve conseguir:

```txt id="wia74k"
ver seus documentos
subir documentos permitidos
vincular documentos a Auxiliares/Agents
ver o que é conhecimento global usado
não editar global
solicitar atualização/curadoria
```

---

# Parte M — Auxiliares

## 50. Auxiliar global com conhecimento global

Um Auxiliar global pode declarar:

```txt id="xn4ssx"
precisa de playbook global X
precisa de dossiê seguradora Y
recomenda docs locais da corretora
usa SubAgent Z
usa Vault permission W
```

Mas não copia documentos.

---

## 51. Auxiliar exclusivo

Um Auxiliar exclusivo pode ter:

```txt id="48t2b4"
blueprint específico
knowledge local específico
agent original vinculado
config privada
```

Não deve aparecer para outras corretoras.

---

## 52. Auxiliar specific_executor

Auxiliares como `Resumo de Atendimentos` e `Follow-up WhatsApp` podem usar RAG no futuro, mas não devem virar motor paralelo.

Regra:

```txt id="6j37r6"
specific_executor pode chamar Smith RAG/tooling
mas não deve reimplementar o runtime agentico inteiro
```

---

# Parte N — Plano de implementação

## 53. 41C.2 — Global Knowledge mínimo

Objetivo:

```txt id="fk0mtk"
adicionar escopo global sem quebrar documents atual
```

Entregas prováveis:

```txt id="xrx7b1"
SQL controlado para adicionar scope/knowledge_class/metadata/status/version
criar owner interno AutoBrokers Global
criar coleção Qdrant global
ajustar ingestion para scope global
ajustar retrieval para global refs
sem migrar legado ainda
```

---

## 54. 41C.3 — Admin de Conhecimento Global

Objetivo:

```txt id="5cnlyz"
permitir upload/gestão global curada no Admin
```

Entregas:

```txt id="ne4pc5"
página Admin → Conhecimento Global
upload global
status de curadoria
versionamento
lista de documentos
publicar/deprecar
```

---

## 55. 41C.4 — Knowledge refs em Auxiliares/Agents

Objetivo:

```txt id="x4tre6"
fazer Auxiliares/Agents declararem conhecimento necessário
```

Entregas:

```txt id="czeu2l"
default_config.knowledge.requires
UI no Admin Auxiliares
binding na instalação
retrieval usando refs
```

---

## 56. 41C.5 — Dossiês de seguradora

Objetivo:

```txt id="p3n9j1"
criar primeiro conjunto curado de global_carrier knowledge
```

Exemplo inicial:

```txt id="ut2f20"
Allianz Residencial Assistência
```

Fontes:

```txt id="37zmut"
legado curado
documentação pública
condições gerais
playbooks internos
```

---

## 57. 42A — Corredores

Só depois de global/local knowledge organizado.

Objetivo:

```txt id="bu8b20"
criar estrutura workflow/corredor com fases e SubAgents
```

---

# Parte O — Critérios de aceite

## 58. Para considerar RAG pronto para MVP

```txt id="xb11y3"
documents RLS ativo
retrieval filtra agent_id
tenant-wide funciona
global knowledge tem escopo
global não mistura tenant
Admin consegue subir global curado
Admin consegue subir local por corretora
Agent/SubAgent consegue usar docs próprios
Auxiliar global declara knowledge refs
logs mostram chunks usados
legado entra só por curadoria
```

---

## 59. Para considerar memória pronta para atendimento

```txt id="qzu97r"
session summary funcionando
case memory separada
user memory com LGPD
não mistura memória com global RAG
corredor registra fase/status
atendimento pode recuperar contexto do caso
```

---

## 60. Para considerar seguro

```txt id="db9vnh"
sem segredo em RAG
sem PII global
sem cross-tenant
sem cross-agent indevido
global read-only
HITL em ação externa
logs auditáveis
golden tests básicos
```

---

# Parte P — Proibições permanentes

```txt id="1e3ic6"
1. Não criar motor RAG paralelo.
2. Não importar legado bruto.
3. Não usar n8n como orquestrador principal.
4. Não colocar segredo em documento.
5. Não promover conteúdo local para global automaticamente.
6. Não usar logs crus como conhecimento.
7. Não deixar Agent acessar docs de outro Agent sem regra explícita.
8. Não fazer corredor apenas com prompt solto.
9. Não criar global knowledge sem versionamento.
10. Não alterar schema sem SPEC e SQL revisado.
```

---

# Parte Q — Resumo executivo

A arquitetura correta é:

```txt id="cqugcm"
Smith fornece runtime técnico de RAG/memória.
AutoBrokers adiciona escopo, curadoria, global/local, versionamento e produto.
Agents/SubAgents usam conhecimento com isolamento.
Auxiliares declaram dependências de conhecimento.
Corredores usam estrutura, não apenas RAG.
Legado vira fonte curada, não runtime.
Vault continua dono de segredos e ações externas.
