---
# ADR-003 — Runtime de Atendimento, Corredores e Cérebro de Seguros

Status: canonical  
Produto: AutoBrokers.ai  
Sistema: AutoBrokers Intelligence OS  
Tipo: Architecture Decision Record  
Última atualização: 2026-06-06  
Responsável estratégico: Architect / CEO AutoBrokers.ai  
Audiência: Claude Design, Claude Code, Codex, devs, segurança, UX, LLMs estratégicas e time fundador

---

# 1. Decisão

O módulo de **Atendimento** do AutoBrokers.ai será reconstruído sobre o runtime técnico do Smith, mas usando o conhecimento de seguros do ResultVision, Agent OS, corredores, skills, guardrails, conversas reais e materiais de intake como **fontes de domínio curadas**.

Decisão principal:

```txt
Smith será o motor técnico.
ResultVision / Agent OS será fonte de domínio.
AutoBrokers.ai será o produto final.
```

O Atendimento não será uma simples cópia do dashboard antigo.

Também não será um chat genérico do Smith renomeado.

Ele será uma camada operacional própria do AutoBrokers.ai para atender segurados, organizar casos, acionar seguradoras, acompanhar protocolos e manter rastreabilidade.

---

# 2. Objetivo do Atendimento

O Atendimento existe para resolver demandas reais de segurados e clientes da corretora.

Exemplos:

- assistência residencial;
- assistência auto;
- sinistro;
- renovação;
- dúvidas sobre apólice;
- envio de documentos;
- acompanhamento de protocolo;
- reclamação;
- urgência;
- acionamento de seguradora;
- coleta de dados;
- direcionamento humano;
- confirmação de cobertura;
- acompanhamento de prestador;
- encerramento do caso.

O Atendimento é diferente do AutoBrokers central.

```txt
AutoBrokers central = cérebro conversacional da corretora.
Atendimento = operação de casos e conversas com clientes/segurados.
Auxiliares = automações/rotinas especializadas.
```

---

# 3. Separação entre AutoBrokers central e Atendimento

O AutoBrokers central é o chat principal do corretor.

Ele pode:

- consultar informações;
- explicar a operação;
- sugerir ações;
- abrir módulos;
- resumir atendimentos;
- orientar o corretor;
- disparar Auxiliares;
- analisar dados;
- ajudar na gestão.

Mas o AutoBrokers central não é, por si só, o agente de atendimento externo ao cliente.

O Atendimento tem agentes próprios.

Exemplo:

```txt
AutoBrokers:
"Mostre os atendimentos urgentes de hoje."

Agente de Atendimento:
"Olá, sou o assistente da Resulta Seguros. Vou te ajudar com sua assistência residencial."
```

---

# 4. Três tipos de agentes

O produto precisa manter separação clara entre três tipos de inteligência.

## 4.1 AutoBrokers

Nome fixo: **AutoBrokers**.

Função:

- assistente central da corretora;
- conversa com usuários internos;
- entende a operação;
- consulta conhecimento;
- sugere melhorias;
- abre módulos;
- interpreta dados;
- pode orquestrar ações com permissão.

Não é personalizável por nome.

---

## 4.2 Agentes de atendimento

São agentes que conversam com clientes/segurados.

Podem ser personalizados pela corretora.

Exemplos:

- nome;
- tom;
- avatar;
- gênero;
- estilo de linguagem;
- horário de funcionamento;
- regras de handoff;
- mensagens padrão.

Função:

- receber mensagem;
- coletar dados;
- classificar demanda;
- consultar apólice;
- abrir caso;
- acompanhar atendimento;
- preparar acionamento;
- comunicar cliente;
- pedir documentos;
- acionar humano.

---

## 4.3 Auxiliares

São automações ou subagentes especializados.

Exemplos:

- Auxiliar de Cobrança;
- Auxiliar de Renovação;
- Auxiliar de Relatório Diário;
- Auxiliar de Conferência de Documentos;
- Auxiliar de Follow-up;
- Auxiliar de Análise de Conversas;
- Auxiliar de Reputação Google;
- Auxiliar de Triagem de Leads.

Auxiliares podem usar dados de atendimento, mas não são o Atendimento em si.

---

# 5. Fontes de domínio

O Atendimento deve ser construído a partir de várias fontes.

## 5.1 ResultVision

Papel:

```txt
Referência de domínio, UX operacional e arquitetura antiga de atendimento.
```

Pode fornecer:

- páginas de atendimento;
- fila;
- casos;
- conversas;
- segurados;
- seguradoras;
- corredores;
- canais;
- layouts operacionais;
- conceitos de operação;
- lógica de atendimento;
- experiências já desenhadas.

Não deve ser copiado bruto.

---

## 5.2 Agent OS antigo

Papel:

```txt
Fonte de raciocínio, contratos, skills, guardrails e inteligência operacional.
```

Pode fornecer:

- Constituição;
- Orquestrador;
- Runtime conversacional;
- Skills;
- Corredores;
- Guardrails;
- Contratos;
- Templates;
- Observabilidade;
- Memória;
- Execution Plane.

Não deve ser carregado diretamente no runtime.

---

## 5.3 AutoBrokers Intelligence V2

Papel:

```txt
Futura organização canônica do cérebro.
```

Deve servir como estrutura de destino para conhecimento curado.

Mas não deve ser considerado runtime ativo até aprovação.

---

## 5.4 AUTOBROKERS_RESULTA_INTAKE

Papel:

```txt
Fonte bruta de evidências reais.
```

Contém:

- conversas de WhatsApp com clientes;
- conversas de WhatsApp com seguradoras;
- imagens;
- PDFs;
- documentos;
- áudios;
- planilhas;
- acessos;
- materiais de operação real;
- exemplos de perguntas;
- exemplos de resposta;
- protocolos;
- problemas reais.

Risco:

```txt
Alto risco de PII, credenciais e dados sensíveis.
```

Nunca deve ser ingerido bruto no RAG.

---

# 6. Regra de curadoria

Nenhuma fonte de domínio entra diretamente no runtime.

Fluxo correto:

```txt
Fonte bruta ou legado
→ inventário
→ classificação
→ extração
→ reescrita
→ validação
→ pacote operacional
→ teste
→ uso controlado
```

Isso vale para:

- corredores;
- skills;
- conversas;
- templates;
- regras;
- PDFs;
- prints;
- scripts;
- documentos de seguradora;
- protocolos;
- materiais do WhatsApp.

---

# 7. O que é um Atendimento

Um Atendimento é uma unidade operacional.

Ele representa uma demanda real ou potencial de um cliente/segurado.

Exemplo:

```txt
Cliente informa que houve vazamento na cozinha e deseja acionar assistência residencial.
```

Um Atendimento pode envolver:

- cliente;
- segurado;
- apólice;
- corretora;
- agente;
- conversa;
- mídia;
- documentos;
- cobertura;
- seguradora;
- canal;
- corredor;
- subcorredor;
- protocolo;
- prestador;
- previsão;
- status;
- humano responsável;
- logs;
- follow-up;
- encerramento.

---

# 8. Ciclo de vida do Atendimento

O Atendimento não começa no corredor.

Corredor é apenas uma parte do fluxo.

O ciclo completo tem várias fases.

```txt
1. Entrada
2. Entendimento inicial
3. Coleta e consolidação
4. Identificação do cliente
5. Apólice e elegibilidade
6. Classificação operacional
7. Decisão de atendimento
8. Preparação do acionamento
9. Corredor / subcorredor
10. Acionamento assistido
11. Captura de retorno
12. Comunicação ao cliente
13. Acompanhamento
14. Handoff humano, se necessário
15. Encerramento
16. Aprendizado / avaliação
```

---

# 9. Fase 1 — Entrada

A entrada recebe a primeira mensagem do cliente.

Canais possíveis:

- WhatsApp;
- chat web;
- formulário;
- e-mail;
- telefone transcrito;
- upload;
- mensagem encaminhada;
- atendimento humano iniciado manualmente.

Objetivo:

```txt
Receber a demanda sem assumir conclusões prematuras.
```

Tarefas:

- identificar canal;
- registrar mensagem;
- detectar se é fragmentada;
- esperar complemento se necessário;
- reconhecer urgência inicial;
- iniciar sessão;
- criar ou recuperar atendimento;
- preservar contexto.

---

# 10. Fase 2 — Entendimento inicial

Objetivo:

```txt
Entender o que o cliente quer, em linguagem humana.
```

Exemplos de intenção:

- assistência residencial;
- assistência auto;
- sinistro;
- guincho;
- chaveiro;
- vidraceiro;
- eletricista;
- encanador;
- dúvida sobre apólice;
- reclamação;
- segunda via;
- renovação;
- problema com prestador;
- acompanhamento de protocolo.

O agente não deve pular direto para acionamento.

Ele deve primeiro entender.

---

# 11. Fase 3 — Coleta e consolidação

Objetivo:

```txt
Coletar apenas os dados necessários para avançar com segurança.
```

Regras:

- não perguntar tudo de uma vez;
- não repetir o que já foi enviado;
- interpretar mensagens fragmentadas;
- usar imagens/documentos quando possível;
- pedir complemento com clareza;
- evitar linguagem robótica;
- explicar por que precisa da informação.

Dados comuns:

- nome;
- CPF/CNPJ;
- telefone;
- endereço;
- placa;
- seguradora;
- número da apólice;
- descrição do problema;
- fotos;
- documento;
- localização;
- urgência;
- melhor horário;
- contato alternativo.

---

# 12. Fase 4 — Identificação do cliente

Objetivo:

```txt
Saber quem está falando e se pode solicitar o atendimento.
```

Pode envolver:

- cliente titular;
- segurado;
- familiar;
- funcionário;
- terceiro;
- corretor;
- representante;
- pessoa não autorizada.

Regras:

- validar solicitante;
- pedir autorização quando necessário;
- evitar expor dados da apólice;
- não confirmar informações sensíveis para pessoa errada;
- registrar incerteza.

---

# 13. Fase 5 — Apólice e elegibilidade

Objetivo:

```txt
Verificar se existe apólice relacionada e se há possibilidade de assistência/cobertura.
```

Fontes possíveis:

- banco interno;
- sistema de gestão;
- InfoCap;
- Quiver;
- Segfy;
- Capta;
- PDF de apólice;
- documento enviado;
- dados manuais;
- histórico;
- seguradora;
- base da corretora.

Regra crítica:

```txt
O agente não deve prometer cobertura sem fonte confiável.
```

Linguagem correta:

```txt
"Vou verificar as informações da apólice antes de confirmar o melhor caminho."
```

Linguagem proibida:

```txt
"Está coberto."
"Pode ficar tranquilo que a seguradora vai pagar."
"Já acionei."
"Já está garantido."
```

---

# 14. Fase 6 — Classificação operacional

Objetivo:

```txt
Transformar a demanda em um tipo operacional acionável.
```

Exemplos:

```txt
assistencia_residencial.eletricista
assistencia_residencial.encanador
assistencia_residencial.chaveiro
assistencia_residencial.desentupimento
assistencia_auto.guincho
sinistro_auto.colisao
sinistro_residencial.danos_eletricos
duvida_apolice.cobertura
acompanhamento.protocolo
reclamacao.prestador
```

A classificação deve considerar:

- ramo;
- seguradora;
- canal;
- serviço;
- urgência;
- dados disponíveis;
- apólice;
- localização;
- histórico;
- restrições;
- risco.

---

# 15. Fase 7 — Decisão de atendimento

Objetivo:

```txt
Decidir o próximo passo seguro.
```

Possíveis decisões:

- continuar coleta;
- consultar apólice;
- abrir caso;
- acionar humano;
- preparar corredor;
- pedir documento;
- orientar cliente;
- iniciar acompanhamento;
- encerrar por falta de dados;
- redirecionar para seguradora;
- bloquear automação por risco;
- pedir aprovação.

---

# 16. Fase 8 — Preparação do acionamento

Antes de acionar seguradora, o sistema precisa montar um pacote de dispatch.

Esse pacote deve conter:

- cliente;
- solicitante;
- apólice;
- seguradora;
- ramo;
- serviço;
- endereço;
- descrição do problema;
- imagens/documentos relevantes;
- dados mínimos;
- perguntas já respondidas;
- lacunas;
- nível de urgência;
- canal sugerido;
- corredor sugerido;
- risco;
- necessidade de humano;
- autorização.

Regra:

```txt
Sem pacote mínimo, não acionar.
```

---

# 17. Fase 9 — Corredor

Corredor é a rota operacional para executar uma parte específica do atendimento.

Um corredor não é o atendimento inteiro.

Ele representa:

```txt
Como resolver uma etapa operacional específica, para uma seguradora, ramo, canal e serviço.
```

Exemplo:

```txt
Allianz
→ Assistência Residencial
→ WhatsApp
→ Eletricista
```

Isso é um corredor/subcorredor de acionamento.

---

# 18. Definição de corredor

Um Corredor contém:

- seguradora;
- ramo;
- tipo de atendimento;
- canal;
- serviço;
- dados mínimos;
- perguntas esperadas;
- mensagens padrão;
- sequência operacional;
- riscos;
- lacunas;
- fallback;
- critérios de sucesso;
- critérios de handoff;
- como capturar protocolo;
- como capturar prestador;
- como capturar previsão;
- como comunicar cliente.

---

# 19. Definição de subcorredor

Subcorredor é uma especialização do corredor.

Exemplo:

Corredor:

```txt
Allianz Assistência Residencial via WhatsApp
```

Subcorredores:

```txt
Eletricista
Encanador
Chaveiro Residencial
Desentupimento
Eletrodomésticos
```

Cada subcorredor pode ter:

- perguntas próprias;
- dados próprios;
- restrições próprias;
- mensagens próprias;
- riscos próprios;
- critérios próprios.

---

# 20. Canais de acionamento

O Atendimento pode acionar ou interagir por diferentes canais.

## 20.1 WhatsApp da seguradora

Exemplo:

- assistência 24h Allianz;
- HDI;
- Porto;
- outras seguradoras.

Risco:

- conversa pode mudar;
- robô pode perguntar diferente;
- atendente humano pode entrar;
- protocolo pode vir em formato variável;
- pode exigir dados sensíveis.

---

## 20.2 Portal da seguradora

Risco maior.

Pode exigir:

- login;
- senha;
- 2FA;
- documentos;
- preenchimento;
- anexos;
- confirmação;
- aceite.

No MVP, portal deve ser:

```txt
consulta assistida ou dry-run, não execução automática irrestrita.
```

---

## 20.3 Telefone / 0800

Pode envolver:

- script humano;
- transcrição;
- resumo;
- apoio ao atendente;
- registro manual;
- checklist.

---

## 20.4 API

Quando existir API oficial, usar preferencialmente.

Mas ainda precisa:

- Vault;
- permissões;
- logs;
- validação;
- tratamento de erro;
- aprovação se ação externa.

---

# 21. Fase 10 — Acionamento assistido

No MVP, o acionamento deve ser assistido.

Significa:

```txt
O sistema prepara, organiza, sugere, valida e registra.
Ação externa real exige humano ou modo aprovado.
```

O sistema pode:

- preparar mensagem para seguradora;
- mostrar dados faltantes;
- sugerir canal;
- montar checklist;
- abrir tela de aprovação;
- executar em dry-run;
- registrar tentativa.

Não deve, no início:

- enviar automaticamente sem aprovação;
- acionar seguradora sem confirmação;
- abrir protocolo real sem log;
- preencher portal e concluir sem HITL.

---

# 22. Fase 11 — Captura de retorno

O sistema deve capturar respostas reais da seguradora/canal.

Retornos importantes:

- protocolo;
- número de atendimento;
- prestador;
- telefone do prestador;
- previsão;
- prazo;
- negativa;
- dados faltantes;
- pedido de documento;
- restrição;
- orientação;
- erro;
- fila;
- transferência;
- mensagem inconclusiva.

Regra:

```txt
Não comunicar protocolo, prestador ou previsão ao cliente se não houver retorno real.
```

---

# 23. Fase 12 — Comunicação ao cliente

O agente de atendimento deve comunicar o cliente com linguagem humana.

Exemplos:

```txt
"Consegui registrar o pedido com a seguradora. O protocolo informado foi X. Agora vou acompanhar a previsão do prestador e te aviso assim que tiver atualização."
```

Se ainda não houver retorno:

```txt
"Ainda estou aguardando o retorno da assistência. Assim que tiver protocolo, prestador ou previsão, te aviso por aqui."
```

Se faltar dado:

```txt
"Para seguir com o acionamento, preciso confirmar mais uma informação: o endereço completo do local onde o atendimento será realizado."
```

---

# 24. Fase 13 — Acompanhamento

Atendimento não termina no acionamento.

O sistema precisa acompanhar:

- se prestador foi designado;
- se prestador chegou;
- se prazo atrasou;
- se cliente reclamou;
- se houve nova informação;
- se precisa recontato;
- se precisa humano;
- se precisa registrar encerramento.

Possíveis status:

```txt
novo
em_triagem
coletando_dados
aguardando_cliente
consultando_apolice
pronto_para_acionamento
acionamento_em_preparacao
aguardando_aprovacao
acionado
aguardando_retorno_seguradora
aguardando_prestador
em_atendimento
atrasado
em_handoff
resolvido
encerrado
cancelado
bloqueado
erro
```

---

# 25. Fase 14 — Handoff humano

Handoff é obrigatório quando:

- cliente está irritado;
- há risco jurídico;
- há negativa de cobertura;
- dados são inconsistentes;
- seguradora pede algo inesperado;
- há urgência grave;
- há acidente com vítima;
- há risco à vida;
- há exposição financeira;
- há dúvida sobre cobertura;
- há ação externa crítica;
- cliente pede humano;
- agente perdeu confiança.

O handoff deve entregar um dossiê.

Dossiê humano:

- resumo;
- histórico;
- dados coletados;
- apólice;
- documentos;
- fotos;
- status;
- risco;
- recomendação;
- próxima ação sugerida;
- mensagens importantes;
- lacunas.

---

# 26. Fase 15 — Encerramento

Encerramento deve registrar:

- resultado;
- protocolo;
- prestador;
- tempo de resposta;
- satisfação;
- pendências;
- documentos;
- custos, se houver;
- motivo de encerramento;
- se houve humano;
- se houve erro;
- avaliação do agente;
- aprendizado.

---

# 27. Fase 16 — Aprendizado e avaliação

Todo atendimento deve poder alimentar:

- evals;
- golden cases;
- melhorias de corredor;
- melhoria de template;
- ajuste de skill;
- identificação de lacunas;
- métricas;
- base de conhecimento;
- treinamento futuro, se permitido.

Mas não deve alimentar RAG/treino automaticamente sem política de privacidade, redaction e curadoria.

---

# 28. Arquitetura runtime

O runtime técnico oficial é o Smith.

Portanto:

```txt
Atendimento deve ser implementado progressivamente dentro do AutoBrokers Intelligence OS, reaproveitando FastAPI, Next.js, Supabase, agents, tools, logs, RAG, MinIO, Qdrant e billing.
```

Mas o domínio de atendimento vem do AutoBrokers antigo.

---

# 29. Como portar o Agent OS para Smith

Não portar tudo de uma vez.

Estratégia correta:

```txt
1. Escolher um fluxo pequeno.
2. Extrair regras do Agent OS/ResultVision/intake.
3. Reescrever como pacote operacional.
4. Criar contratos mínimos.
5. Criar golden tests.
6. Implementar no runtime Smith.
7. Testar em sandbox.
8. Só então expandir.
```

---

# 30. MVP de Atendimento

O MVP de Atendimento não deve tentar cobrir todas as seguradoras e todos os corredores.

MVP recomendado:

```txt
Atendimento assistido, com chat, caso, histórico, coleta de dados e um fluxo de demonstração controlado.
```

Possível primeiro fluxo:

```txt
Allianz Assistência Residencial
→ WhatsApp
→ Eletricista ou Encanador
→ modo assistido / no-send / aprovação humana
```

Mas só deve ser implementado depois de:

- UX base definida;
- Vault conceitual definido;
- docs canônicos validados;
- runtime estável;
- escopo do fluxo escolhido;
- material de corredor revisado.

---

# 31. O que não entra no primeiro MVP de Atendimento

Não entra:

- todos os corredores;
- todos os ramos;
- todos os portais;
- execução automática irrestrita;
- acionamento real sem aprovação;
- ingestão bruta do WhatsApp;
- automação browser complexa;
- integração profunda com InfoCap/Quiver;
- todos os canais;
- substituição completa do humano;
- autoaprendizado sem revisão.

---

# 32. Papel do n8n

O ResultVision antigo usava n8n como gateway importante.

No novo AutoBrokers Intelligence OS:

```txt
n8n pode continuar como adaptador/transição quando fizer sentido, mas não deve ser o núcleo estratégico do runtime.
```

Decisão:

- Smith/FastAPI/LangGraph é o runtime principal;
- n8n pode orquestrar integrações específicas;
- n8n pode ser usado em fase de transição;
- n8n não deve virar dependência obrigatória de toda ação;
- fluxos críticos devem ter contratos e logs no AutoBrokers.

---

# 33. Papel do WhatsApp

WhatsApp é canal crítico.

Mas precisa ser tratado com segurança.

Possíveis providers:

- Evolution API;
- Z-API herdado do Smith;
- provider futuro.

Decisão conceitual:

```txt
Criar abstração de WhatsApp Provider.
```

O Atendimento não deve depender diretamente de Evolution ou Z-API.

Ele deve depender de uma interface:

```txt
sendMessage
receiveMessage
sendMedia
receiveMedia
getConversation
markHandled
```

No MVP:

```txt
WhatsApp real deve começar em dry-run ou com aprovação.
```

---

# 34. Papel do InfoCap / Quiver / Segfy / Capta

Sistemas de gestão são fontes importantes.

Podem fornecer:

- apólices;
- clientes;
- propostas;
- parcelas;
- sinistros;
- documentos;
- renovações;
- contatos;
- produtores;
- comissões.

Mas no MVP:

```txt
Começar com leitura assistida ou dados mock/sandbox.
```

Antes de escrita real:

- Vault;
- permissões;
- logs;
- rollback;
- aprovação;
- contrato técnico;
- teste por tenant.

---

# 35. Papel de mídia

Atendimento real envolve mídia.

Clientes podem enviar:

- foto da batida;
- foto da TV queimada;
- foto da torneira vazando;
- documento;
- PDF;
- áudio;
- localização;
- vídeo;
- print de conversa;
- print de apólice.

O Atendimento precisa evoluir para entender mídia.

Fases:

1. receber e armazenar;
2. associar ao caso;
3. resumir;
4. extrair dados;
5. classificar;
6. usar como evidência;
7. redigir PII;
8. enviar para seguradora com aprovação.

No MVP, mídia pode ser armazenada e mostrada, mesmo que interpretação avançada venha depois.

---

# 36. Relação com RAG

RAG ajuda o Atendimento, mas não substitui o fluxo operacional.

RAG pode responder:

- regras gerais;
- templates;
- instruções;
- documentos da corretora;
- regras da seguradora;
- histórico curado;
- FAQs.

Mas ações de atendimento precisam de estado, contratos e logs.

Regra:

```txt
RAG responde conhecimento.
Runtime executa fluxo.
Vault governa acesso.
Logs registram ação.
```

---

# 37. Relação com Vault

Atendimento depende do Vault para:

- WhatsApp;
- portal;
- e-mail;
- sistema de gestão;
- documentos;
- dados de cliente;
- fontes de conhecimento;
- credenciais;
- permissões;
- aprovações.

Nenhum acionamento real deve ignorar o Vault.

---

# 38. Relação com Auxiliares

Auxiliares podem apoiar Atendimento.

Exemplos:

- resumir conversa;
- gerar dossiê;
- revisar mensagem;
- analisar sentimento;
- criar follow-up;
- verificar documentos;
- gerar relatório diário;
- identificar atraso;
- recomendar handoff.

Mas Auxiliares não substituem automaticamente o fluxo de Atendimento.

---

# 39. Relação com Personalização

A corretora deve poder personalizar:

- agentes de atendimento;
- tom;
- horários;
- handoff;
- mensagens padrão;
- canais;
- seguradoras ativas;
- ramos atendidos;
- permissões;
- equipe;
- documentos;
- regras comerciais.

Mas não deve precisar entender detalhes técnicos de corredor.

---

# 40. Relação com Seguradoras e Corredores

Seguradoras e corredores devem aparecer na experiência de Personalização/Canais/Atendimento de forma limpa.

O usuário deve entender:

- quais seguradoras estão disponíveis;
- quais canais existem;
- quais canais estão conectados;
- quais ramos estão ativos;
- quais corredores estão prontos;
- quais precisam configuração;
- quais estão em beta;
- quais exigem aprovação humana.

Evitar mostrar estrutura técnica demais.

---

# 41. UX do Atendimento

Atendimento deve ser operacional, mas não poluído.

Páginas prováveis:

```txt
Atendimentos
→ Painel
→ Fila
→ Casos
→ Conversas
→ Segurados
```

Mas a UX final será definida por UX-001 e Claude Design.

Regra atual:

```txt
Não recriar dashboard antigo bruto.
Não criar páginas densas antes do design system.
Não misturar configuração com operação.
```

---

# 42. Mobile-first

Atendimento deve funcionar bem no celular.

Principalmente para:

- ler conversa;
- responder cliente;
- ver status;
- aprovar ação;
- acompanhar caso;
- abrir detalhe;
- voltar para fila;
- ver mídia;
- transferir para humano.

No mobile, usar navegação em camadas:

```txt
Fila
→ Caso
→ Conversa
→ Dados
→ Ação
```

Evitar:

- tabelas grandes;
- dashboards densos;
- múltiplas colunas;
- cards excessivos;
- menus profundos sem retorno claro.

---

# 43. Estados do Atendimento

Estados mínimos recomendados:

```txt
novo
em_triagem
aguardando_cliente
aguardando_documento
consultando_apolice
em_analise
pronto_para_acionamento
aguardando_aprovacao
acionamento_em_andamento
aguardando_seguradora
aguardando_prestador
em_acompanhamento
handoff_humano
resolvido
encerrado
cancelado
erro
bloqueado
```

Esses estados podem ser refinados depois.

---

# 44. Dados mínimos de um caso

Um caso de atendimento deve ter, conceitualmente:

- id;
- company_id;
- customer_id;
- contact_id;
- policy_id opcional;
- channel;
- status;
- priority;
- intent;
- branch;
- insurer;
- service_type;
- assigned_agent_id;
- assigned_human_id;
- created_at;
- updated_at;
- last_message_at;
- summary;
- risk_level;
- handoff_required;
- metadata.

---

# 45. Dados mínimos de uma conversa

Uma conversa deve ter:

- id;
- company_id;
- case_id;
- channel;
- participant;
- messages;
- attachments;
- status;
- last_message_at;
- source;
- trace_id.

---

# 46. Dados mínimos de uma ação

Uma ação deve ter:

- id;
- company_id;
- case_id;
- actor_type;
- actor_id;
- action_type;
- target;
- payload_preview;
- risk_level;
- approval_status;
- execution_status;
- result;
- trace_id;
- created_at;
- executed_at.

---

# 47. Logs obrigatórios

Toda ação relevante deve gerar log.

Logs mínimos:

- mensagem recebida;
- intenção classificada;
- dado coletado;
- apólice consultada;
- corredor sugerido;
- mensagem gerada;
- aprovação solicitada;
- aprovação concedida/negada;
- ação externa executada;
- retorno capturado;
- handoff acionado;
- encerramento.

---

# 48. Guardrails obrigatórios

O Atendimento deve respeitar guardrails.

## 48.1 Proibido prometer cobertura

Não pode dizer:

```txt
"Está coberto."
"A seguradora vai pagar."
"Já está garantido."
```

Sem confirmação.

---

## 48.2 Proibido fingir ação

Não pode dizer:

```txt
"Já acionei."
"Já abri protocolo."
"O prestador já está a caminho."
```

Sem retorno real.

---

## 48.3 Proibido expor dados

Não pode revelar dados de apólice para pessoa não autorizada.

---

## 48.4 Proibido enviar ação externa sem aprovação no MVP

Toda ação externa real exige HITL.

---

## 48.5 Proibido usar intake bruto diretamente

Conversas reais só entram depois de curadoria.

---

# 49. Golden tests

Cada corredor implementado precisa de testes.

Exemplos para Allianz Residencial:

- cliente pede eletricista;
- cliente manda foto de tomada queimada;
- cliente fala “minha TV queimou” e sistema não confunde com eletricista;
- cliente pede encanador;
- cliente pede desentupimento;
- seguradora pede CPF;
- seguradora retorna protocolo;
- seguradora não retorna previsão;
- cliente irritado;
- cliente pede humano;
- faltam dados;
- apólice não encontrada;
- endereço incompleto.

Cada teste deve validar:

- pergunta correta;
- não promessa indevida;
- coleta mínima;
- handoff quando necessário;
- mensagem clara;
- log correto.

---

# 50. Estratégia de implementação

Implementar por camadas.

## 50.1 Camada 1 — Base visual e navegação

Definida por UX-001 e Claude Design.

Sem lógica pesada.

---

## 50.2 Camada 2 — Casos e conversas

Criar ou adaptar estrutura para:

- fila;
- caso;
- conversa;
- status;
- histórico.

---

## 50.3 Camada 3 — Agente de atendimento simples

Permitir:

- responder em sandbox;
- resumir;
- classificar;
- pedir dados;
- handoff.

---

## 50.4 Camada 4 — Um corredor assistido

Escolher um fluxo.

Implementar:

- dados mínimos;
- templates;
- dispatch packet;
- aprovação;
- retorno manual/simulado;
- logs.

---

## 50.5 Camada 5 — Integração real controlada

Só depois:

- WhatsApp real;
- Evolution/Z-API;
- portal;
- seguradora;
- InfoCap;
- Quiver.

---

# 51. Ordem recomendada

A ordem correta agora é:

```txt
1. Finalizar docs canônicos.
2. Claude Design definir UX e estrutura visual.
3. Claude Code implementar chat-first limpo e sidebar base.
4. Implementar Auxiliares MVP ou Atendimento MVP conforme decisão de roadmap.
5. Só depois corredores reais.
```

Não começar por corredores agora.

Corredores são importantes, mas dependem de:

- UX;
- Vault;
- dados;
- permissões;
- runtime;
- logs;
- golden tests;
- fluxo de caso.

---

# 52. Decisão sobre corredores antigos

Os corredores antigos são valiosos.

Mas devem ser tratados como:

```txt
Material-fonte especializado.
```

Não como:

```txt
Código pronto.
Documento runtime pronto.
Prompt final.
Fonte carregável diretamente.
```

Cada corredor precisa virar:

- versão curta;
- contrato;
- matriz de dados;
- templates;
- critérios de ação;
- critérios de handoff;
- testes;
- pacote operacional.

---

# 53. Papel do Claude Design

Claude Design deve usar este ADR para entender:

- Atendimento é módulo operacional;
- não é Home;
- não é AutoBrokers central;
- precisa ser limpo;
- precisa ser mobile-first;
- precisa separar operação de configuração;
- corredores não devem poluir tela principal;
- fluxo deve ir em camadas;
- inspiração vem do dashboard antigo, mas com estética ChatGPT/Claude.

Claude Design deve desenhar:

- lista de atendimentos;
- detalhe do caso;
- conversa;
- painel simples;
- status;
- ações;
- aprovação;
- handoff;
- configuração de canal/corredor em outro módulo.

---

# 54. Papel do Claude Code

Claude Code deve:

- não copiar ResultVision;
- não copiar Agent OS bruto;
- não criar todos os corredores;
- não criar automação real sem contrato;
- auditar schema antes de migrar;
- reaproveitar Smith quando possível;
- manter typecheck/build;
- trabalhar em batches pequenos;
- proteger secrets;
- manter ações externas bloqueadas por padrão.

---

# 55. Critérios de pronto do Atendimento MVP

O Atendimento MVP estará no caminho certo quando:

- existir módulo visual limpo;
- existir fila/casos/conversas;
- agente puder classificar demanda;
- agente puder coletar dados;
- humano puder acompanhar;
- ação externa estiver bloqueada ou aprovada;
- logs existirem;
- um fluxo assistido funcionar em sandbox;
- cliente não receber promessa indevida;
- dados sensíveis forem protegidos;
- corretor entender o que está acontecendo;
- mobile for utilizável.

---

# 56. Decisão final

O Atendimento do AutoBrokers.ai deve ser reconstruído com disciplina.

Não será uma migração cega do ResultVision.

Não será uma cópia bruta do Agent OS.

Não será uma tela de dashboard densa.

Não será uma automação irresponsável.

Será:

```txt
Um módulo operacional de seguros, integrado ao Smith Runtime, alimentado por conhecimento curado do AutoBrokers, governado pelo Vault, com ações externas protegidas por aprovação humana, e desenhado com UX limpa, mobile-first e escalável.
```

O caminho certo é:

```txt
Base limpa.
UX clara.
Vault conceitual.
Casos e conversas.
Um fluxo assistido.
Golden tests.
Expansão progressiva.
```

Esse ADR é a decisão oficial para impedir retrabalho e orientar Claude Design, Claude Code, Codex e qualquer LLM futura.