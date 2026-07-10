# SPEC-023B - Estado atual, pendencias e plano de continuidade

**Data deste estado**: 2026-07-09  
**Objetivo**: orientar o proximo executor sem perder contexto, sem recriar estruturas paralelas e sem confundir portal worker, auxiliares, Smith e atendimento WhatsApp.  
**Runbook operacional Allianz**: `SPEC-023A-allianz-cobranca-runbook-operacional.md`

---

## 1. Onde estamos agora

Resumo franco:

- O fluxo do worker Allianz para cobranca foi corrigido e provado no portal real.
- A varredura real encontrou 4 inadimplentes.
- O download real de 1 PDF foi provado localmente pelo worker.
- O codigo foi mergeado no repo principal e o `portal-worker` foi deployado.
- A rotina global de cobranca existe e enfileira `portal_jobs`.
- O ponta a ponta da rotina no dashboard, depois do deploy, ainda precisa ser homologado.
- O envio ao cliente real continua bloqueado. Homologacao deve usar modo teste.

Nao declarar ainda:

- "Auxiliar de cobranca esta 100% pronto para cliente real."
- "PDF ja chega como anexo no WhatsApp."
- "Todos os boletos dos 4 inadimplentes foram baixados em uma rotina real."

Declarar com seguranca:

- "Worker Allianz ja conseguiu extrair os 4 inadimplentes reais e baixar 1 boleto PDF real."

---

## 2. As tres familias de agentes

O projeto tem tres familias e elas nao podem ser misturadas:

1. **Smith / Chat Principal**
   - Copiloto interno do corretor.
   - Deve usar ferramentas globais, InfoCap, portais e conhecimento.

2. **Auxiliares / Rotinas**
   - Automacoes globais/agendadas.
   - Usam SPEC-019.
   - Cobranca e uma rotina global, nao um servico isolado.

3. **Atendimento WhatsApp**
   - Agente `attendance`.
   - Fala com segurado.
   - Deve assumir o pos-cobranca quando o cliente responder.

Regra:

- Uma capacidade de portal deve servir Smith, rotinas e atendimento.
- Nao criar portal worker exclusivo para cobranca.

---

## 3. Status por fase da SPEC-023

### P1 - Login autenticado + sessao persistida

Estado: **feito e testado**.

Existe:

- `allianz_corretor.login_check`.
- `interpret_login`.
- sessao persistida em `portal_sessions`.
- credencial por corretora em `portal_accounts`.
- vault Fernet.

Validacao:

- `test_spec023_allianz_login.py`: 19 ok / 0 fail.

Pendencias:

- observar expiracao de sessao ao longo de dias;
- expor status de sessao no dashboard com clareza;
- nunca exibir senha.

---

### P2 - HITL CAPTCHA/2FA

Estado: **parcial**.

Existe:

- worker detecta termos de CAPTCHA/2FA;
- job vira `needs_human`;
- screenshot pode ser capturado;
- evidencia inclui `hitl.required`, `hitl.kind`, `hitl.resume_mode`, `hitl.reason`.

Falta:

- testar com portal real que exige CAPTCHA/2FA;
- fechar UX de retomada;
- definir se v1 reexecuta job apos humano ou mantem browser vivo;
- criar testes de contrato de HITL;
- limpar/arquivar cards antigos;
- validar Porto como piloto de CAPTCHA.

Prioridade:

- Alta, mas depois da homologacao Allianz ponta a ponta em modo teste.

---

### P3 - Allianz cobranca sweep

Estado: **corrigido e provado parcialmente no portal real**.

Feito:

- entrada correta por `INADIMPLENCIAS`;
- reconhecimento de `RESULTADO - TOTAIS`;
- varredura multi-ramo;
- expansao de detalhes;
- busca por nome + categoria `Nome / Razao Social`;
- resultado de cliente;
- `Operar`;
- `Detalhe de Apolice`;
- `Lista Recibos` somente leitura;
- `Ficha Gestao` por clique trusted;
- `Carta Inadimplencia - Aviso`;
- download de PDF.

Validado:

- 4 inadimplentes reais extraidos.
- 1 boleto PDF real baixado.

Falta:

- validar download dos 4 boletos;
- validar comportamento quando existem varias cartas;
- decidir se `Carta Inadimplencia - Aviso` sempre e o documento certo;
- fortalecer selecao de carta por data/parcela/recibo se necessario.

---

### P4 - Auxiliar de Cobranca global

Estado: **estrutura existe; falta homologacao ponta a ponta apos deploy**.

Existe:

- `billing_collection.py`;
- `config.kind = "billing_collection"`;
- selecao de portais;
- enfileiramento de `portal_jobs`;
- polling dos jobs;
- consolidacao de inadimplentes e boletos;
- resolucao de contato via InfoCap;
- modo teste;
- modo aprovacao;
- modo somente relatorio;
- relatorio textual;
- mensagem template.

Falta:

- rodar a rotina no dashboard apos deploy;
- confirmar `portal_jobs` com status `done`;
- confirmar `inadimplentes=4`;
- confirmar `boletos baixados>=1`;
- confirmar link assinado ou arquivo;
- confirmar WhatsApp de teste recebido;
- melhorar modal/UX dos campos;
- decidir PDF anexo vs link temporario;
- validar InfoCap Resulta, nao AutoFleet, para este teste.

Prioridade:

- Maxima.

---

## 4. Pendencias criticas imediatas

### 4.1 Homologar rotina no dashboard

Passos:

1. Garantir Allianz conectado na conta Resulta.
2. Garantir InfoCap apontando para Resulta.
3. Garantir WhatsApp da corretora conectado.
4. Configurar rotina:
   - portal Allianz selecionado;
   - modo `test`;
   - numero de teste;
   - `max_boletos_por_execucao=1`;
   - intervalo manual/curto apenas para teste.
5. Rodar/despausar.
6. Ler relatorio.
7. Abrir `portal_jobs`.
8. Confirmar evidencia.
9. Confirmar mensagem no WhatsApp de teste.
10. Repetir com `max_boletos_por_execucao=4`.

Resultado esperado:

- `Portais varridos: allianz_corretor`.
- `Jobs: 1`.
- `inadimplentes: 4`.
- `boletos baixados: >=1`.
- mensagem de modo teste.
- nenhum cliente real recebe mensagem.

### 4.2 Fechar envio do boleto

Decisao de produto:

- Homologacao aceita link temporario?
- Produto final exige PDF como arquivo/documento?

Se exigir arquivo:

- implementar envio de documento PDF no provider WhatsApp;
- ou usar media upload e link, conforme provider;
- testar em modo teste;
- registrar no relatorio se enviou arquivo ou link.

### 4.3 Corrigir UX do modal de cobranca

Pontos:

- distinguir numero de teste, numero de relatorio e WhatsApp remetente;
- explicar modos `test`, `approval`, `live`, `none`;
- deixar portais selecionados claros;
- impedir que template global critico seja quebrado por edicao livre;
- manter campos de personalizacao seguros.

### 4.4 Rotacionar segredos expostos

Durante a conversa, segredos foram colados.

Recomendacao:

- rotacionar chaves sensiveis antes de compartilhar contexto amplo;
- nao escrever segredos em docs;
- usar vault/EasyPanel.

---

## 5. Portal Worker - contrato definitivo

Criar uma spec curta para contrato do worker.

Ela deve definir:

- status permitidos:
  - `done`
  - `needs_human`
  - `failed`
- shape de `JourneyResult`;
- shape minimo de `evidence`;
- campos obrigatorios por stage;
- convencao de screenshots;
- convencao de storage;
- regra de PII;
- regra de retry;
- regra de timeout;
- regra de upload;
- regra para HITL;
- regra para "nao progrediu";
- regra para fallback adaptativo;
- padrao de teste por journey.

Pendencia tecnica importante:

- Health do `portal-worker` deve mostrar commit SHA/build time, para provar qual versao esta rodando.

---

## 6. Historico de tarefas executadas

Ideia do founder:

- Criar tela central para tudo que agentes fizeram.

Deve incluir:

- atendimentos;
- rotinas;
- Smith/chat principal;
- portal jobs;
- envios;
- acionamentos;
- erros/HITL.

Sugestao:

1. Mapear tabelas existentes antes de criar nova.
2. Se necessario, criar entidade canonica `agent_task_executions`.
3. UI em `Historico`:
   - `Historico de conversas`;
   - `Tarefas executadas`.
4. Filtros:
   - periodo;
   - tipo de agente;
   - rotina;
   - status;
   - portal/seguradora;
   - cliente/apolice quando permitido.
5. Nos cards de rotina:
   - remover lista longa poluindo a tela;
   - colocar botao `Execucoes`;
   - abrir modal filtrado daquela rotina.
6. Futuro:
   - rotina semanal de relatorio para corretor.

Nao executar antes:

- fechar Allianz em modo teste;
- especificar modelo de dados sem duplicar logs existentes.

---

## 7. Pos-cobranca WhatsApp

Depois do boleto, o segurado pode responder:

- "vou pagar dia X";
- "troquei cartao";
- "quero mudar cartao";
- "ja paguei";
- "nao reconheco";
- "manda de novo";
- "quero cancelar";
- "esta caro";
- "quero falar com humano".

Padrao correto:

- O pos-cobranca deve ser do agente `attendance`, nao uma rotina paralela.
- A rotina deve registrar contexto de envio.
- O inbound WhatsApp deve associar resposta recente ao contexto de cobranca.
- O agente usa playbook global de pos-cobranca.

Pendencias:

- criar spec/playbook de pos-cobranca;
- registrar contexto no envio;
- adicionar regras de handoff;
- testar conversas comuns;
- decidir o que o agente pode ou nao pode fazer sem humano.

Regra:

- Alterar dados de pagamento/cartao/debito ou escrever em portal e acao sensivel. Deve ter aprovacao/handoff.

---

## 8. Expansao multi-portal de cobranca

Padrao replicavel:

1. Cadastrar portal global em `portals`.
2. Salvar credencial por corretora em `portal_accounts`.
3. Criar journey:
   - login;
   - interpretacao;
   - cobranca_sweep.
4. Criar runbook do portal.
5. Criar testes de contrato.
6. Rodar portal real com limite 1.
7. Validar download.
8. Integrar no `billing_collection` via `portal_keys`.
9. Adicionar UI de selecao.

Portais/seguradoras citadas:

- Porto;
- HDI;
- Tokio Marine;
- Liberty/Yelum;
- Bradesco;
- Alfa;
- Azul;
- Mapfre;
- Sompo;
- Suhai;
- Sura;
- Zurich.

Prioridade sugerida:

1. Allianz cobranca em modo teste.
2. Porto + HITL CAPTCHA.
3. HDI/Tokio/Liberty conforme volume.

---

## 9. Assistencia auto WhatsApp

Objetivo citado:

- Criar fluxos ponta a ponta de assistencia auto no WhatsApp para 4 ou 5 seguradoras.

Seguradoras provaveis:

- Porto;
- HDI;
- Liberty/Yelum;
- Tokio;
- Allianz/outros conforme piloto.

Padrao correto:

- usar agente `attendance`;
- usar InfoCap para identificar apolice/seguradora;
- usar playbooks por seguradora/subservico;
- usar `portal_worker` se houver portal;
- usar dispatch/WhatsApp da seguradora se for esse o canal;
- registrar evidencia;
- handoff quando precisar.

Nao criar:

- atendente separado por seguradora;
- ferramenta avulsa fora do runtime;
- novo canal paralelo.

---

## 10. Firecrawl

Pedido:

- Criar conector global Firecrawl.

Estado:

- Nao implementado neste bloco.

Uso ideal:

- pesquisa de mercado;
- novidades de seguradoras;
- comunicados publicos;
- clipping;
- monitoramento de produtos;
- auxiliares de pesquisa aberta;
- Smith consultando web publica.

Nao usar:

- como substituto do `portal_worker` para baixar boleto dentro de portal autenticado.

Spec sugerida:

- `SPEC-Firecrawl-conector-global` com escopo, custos, limites, segredo, UI e ferramentas.

---

## 11. Sugestao de specs pequenas a criar

Antes de criar, checar numeracao canonica.

Sugestoes:

1. `SPEC-026-portal-worker-contract.md`
2. `SPEC-027-allianz-cobranca-end-to-end-homologacao.md`
3. `SPEC-028-hitl-captcha-2fa-produto-e-worker.md`
4. `SPEC-029-historico-tarefas-executadas.md`
5. `SPEC-030-pos-cobranca-whatsapp-attendance.md`
6. `SPEC-031-assistencia-auto-whatsapp-multi-seguradora.md`
7. `SPEC-032-firecrawl-conector-global.md`

---

## 12. Ordem recomendada para o Fable

### Bloco 1 - Entender antes de executar

Ler:

- `EXECUTION-GUIDE-OPUS.md`
- `SPEC-019`
- `SPEC-020`
- `SPEC-023`
- `SPEC-023A`
- `SPEC-023B`
- `SPEC-025`
- codigo real de `allianz_corretor.py`
- codigo real de `billing_collection.py`
- codigo real de `worker.py`

Confirmar:

- branch;
- deploy atual;
- tabelas;
- rotina criada;
- ultima execucao;
- logs/evidence.

### Bloco 2 - Fechar Allianz no dashboard

1. Rodar rotina em modo teste.
2. Inspecionar job.
3. Corrigir apenas com evidencia.
4. Validar WhatsApp teste.
5. Validar storage/link/PDF.

### Bloco 3 - Melhorar contrato e UX

1. Health com versao.
2. Evidence padronizada.
3. Jobs arquivaveis/filtraveis.
4. Modal de rotina mais claro.

### Bloco 4 - Pos-cobranca e historico

1. Contexto de envio.
2. Playbook atendimento.
3. Historico de tarefas.

### Bloco 5 - Outros portais e assistencia auto

1. Porto/HITL.
2. HDI/Tokio/Liberty.
3. Playbooks auto.

---

## 13. Como o Fable deve agir

Deve:

- ler codigo real;
- confirmar docs contra implementacao;
- perguntar decisoes de produto;
- instrumentar antes de corrigir;
- criar teste antes de mudar comportamento;
- usar evidencia de `portal_jobs`;
- manter tudo multi-tenant;
- manter tudo global quando for auxiliar/template;
- preservar estruturas existentes.

Nao deve:

- criar worker novo;
- criar fila nova;
- criar motor de browser novo;
- criar uma UI paralela de conectores;
- tratar cobranca como caso Resulta-only;
- tratar InfoCap como auto-only;
- mandar mensagem para cliente real em teste;
- colar segredo em docs;
- esconder incerteza.

---

## 14. Definicao de pronto para a proxima etapa

Considerar a proxima etapa pronta quando:

- rotina no dashboard rodar em modo teste;
- `portal_job` terminar `done`;
- houver pelo menos 1 boleto baixado no storage;
- mensagem chegar no WhatsApp de teste;
- relatorio explicar o que aconteceu;
- nenhum cliente real receber mensagem;
- pendencias restantes estiverem registradas como produto/UX/expansao.

