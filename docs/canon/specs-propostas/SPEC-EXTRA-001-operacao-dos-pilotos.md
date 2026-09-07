<!-- SANITIZADO em 07/09/2026 pelo orquestrador (EXTRA-001 RP0): telefones de teste substituidos pelos aliases TESTE-A/TESTE-B; os valores reais ficam na configuracao privada (BILLING_CANARIO_ALLOWLIST / ATTENDANT_INBOUND_ALLOWLIST). SHA-256 dos bytes de ENTRADA: e62b12bd71d3c6c4e10fc969a767e54e471b425da69bdb2cc077019a040aa0e9 -->
# SPEC-EXTRA-001 — OPERAÇÃO DOS PILOTOS
## Cobrança completa, respostas com contexto e convivência com atendimento

**Produto:** AutoBrokers Intelligence OS.
**Status:** PROPOSTA PARA CONVERSÃO, AQUECIMENTO E EXECUÇÃO — não é SPEC canônica aprovada nem implementação realizada.
**Versão:** 1.0 · **Data:** 07/09/2026.
**Baseline remoto da pesquisa:** `34424fa576f8fdb35f687e3a3af5c66a6e07f915`; o BLOCO 0 deve remedir a revisão atual e a produção.
**Branch sugerida:** `feat/spec-extra-001-operacao-pilotos`.
**Destino desta proposta:** `docs/canon/specs-propostas/SPEC-EXTRA-001-operacao-dos-pilotos.md`.
**SPEC definitiva a criar pelo Fable:** `docs/canon/specs/SPEC-EXTRA-001-operacao-dos-pilotos.md`.
**Research Pack:** `SPEC-EXTRA-001-operacao-dos-pilotos-RESEARCH-PACK.md`; SHA-256 dos bytes de entrada: `3ce221c0dca9600d0bcd5b568866e0c42d50b6ef0c2695f4d202a7a106d9a911`; verificar no RP0 e no manifesto.
**Relatório a criar durante a execução:** `docs/canon/reports/SPEC-EXTRA-001-EXECUTION-REPORT.md`.
**Protocolo:** AAA vigente no repositório; baseline consultada v11.2 + OPÇÃO B. A execução tem piso CRÍTICO porque envia, toca autorização e pode exigir migração.
**Executor:** Claude Code / Fable, com os papéis e modelos definidos no protocolo efetivamente disponível. Este documento não simula execução ou julgamento.

## 0. Resultado e motivo

> A corretora configura o auxiliar de cobrança para entregar o pacote final à atendente ou diretamente ao contato validado do cliente. O sistema obtém o documento correto, entrega pelo WhatsApp autorizado, trata respostas no contexto do caso, impede repetições indevidas e mostra toda pendência à equipe, preservando o atendimento existente. O produto fica implantável e utilizável de ponta a ponta; a comprovação viva desta execução usa exclusivamente os dois números de teste autorizados pelo Founder.

Resulta e AutoFleet são os pilotos de negócio. Saionara e Regina participarão da validação funcional conduzida pelo Founder. **Isso não autoriza o executor a usar os números operacionais pareados dessas corretoras nem a enviar mensagens a elas.** Os nomes identificam o contexto do projeto, não uma autorização de contato.

Não prometer ausência absoluta de erros. Entregar critérios objetivos, provas adversariais, alertas, possibilidade de interrupção e estado final honesto.

### 0.1 Decisões do Founder já incorporadas

| ID | Decisão que governa esta execução |
|---|---|
| D-E001-01 | Prioridade imediata: fechar cobrança e preservar atendimento para os pilotos |
| D-E001-02 | Atendimento permanece Evolution Go; não migrar provedor agora |
| D-E001-03 | Cobrança e atendimento usam inicialmente o mesmo número autorizado da corretora; não exigir segundo QR |
| D-E001-04 | Dois modos reais: encaminhar pacote final à atendente; enviar diretamente ao cliente validado |
| D-E001-05 | No modo humano, texto e PDF devem estar prontos para encaminhar, sem marca de teste ou instrução interna misturada |
| D-E001-06 | Respostas, anti-repetição e aviso de falhas pertencem ao produto completo desta EXTRA |
| D-E001-07 | Testes vivos somente pelos números do Founder listados na §1; números operacionais Resulta/AutoFleet estão proibidos |
| D-E001-08 | Criar família EXTRA, manter 099–114 numeradas, com execução linear temporariamente pausada |
| D-E001-09 | Depois: investigação Agger, canais após pilotos, renovação e demais auxiliares em propostas próprias |
| D-E001-10 | Atualizar o dossiê de SPECS e execução ao longo do trabalho, não apenas no encerramento |

IDs acima são referências deste pacote. O Fable deve registrá-los no mecanismo de decisões existente, verificando colisões; não representam entradas já criadas no repositório.

### 0.2 EXECUTION CARD — enquadramento proposto, a medir

```text
OUTCOME .............. cobrança humana/direta completa, resposta contextual, sem repetição indevida; atendimento preservado
RISCO ................ piso CRÍTICO; calcular alcance + reversibilidade + frequência na conversão
SUPERFÍCIE ........... 3 provisória: mapear todos os caminhos de efeito e retorno
PISO APLICADO ........ AAA §3.2: envio externo, autorização/tenant; migration se necessária
NÍVEL ................ CRÍTICO — opção B
UNIDADES ............. A contrato/UI; B entrega/dedup; C respostas/convivência; D alertas/prova/entrega
COESÃO ............... um contrato de delivery/caso; arquivos-hub com um dono; integração serial
PARALELISMO REAL ..... apenas arquivos disjuntos e investigação independente, conforme mapa do executor
TIME ................. investigador+pesquisador; aquecimento; desenhista; builder(s); duas lentes + red team; juiz fresco
REFERÊNCIA ........... SPEC-078, 095, 097/097.1, 098; referências externas do research pack
GATES ................ G00–G23 da §15, mais gates canônicos pertinentes
O ELO ................ rotina → documento → entrega autorizada → retorno → caso correto → resolução/aviso
FAIXA DE RELÓGIO ..... estimar depois do BLOCO 0; não há promessa de horas nesta proposta
ORÇAMENTO ............ alvo canônico CRÍTICO ≤2,5 M de tokens de subagentes; medir, não confundir com créditos do plano
```

O card definitivo abre o relatório e deve caber no limite do guarda canônico. Não multiplicar cards narrativos para burlar o limite. Orçamento não autoriza cortar prova material ou declarar conclusão sem aceite.

## 1. AUTORIZAÇÃO DE TESTES — fronteira obrigatória de todo pacote

### 1.1 Allowlist explícita e privada

| Alias usado em evidências | Número informado pelo Founder | Forma internacional normalizada |
|---|---|---|
| TESTE-A | `[TESTE-A · allowlist privada]` | `+55TESTE-A` |
| TESTE-B | `[TESTE-B · allowlist privada]` | `+55TESTE-B` |

Esta tabela deve permanecer nos insumos privados do executor. **Não commitar os telefones completos, não publicá-los no dossiê, screenshots, logs, fixtures permanentes ou relatório público.** Ao instalar este pacote no canon de um repositório público, substituir a tabela pela referência a uma allowlist privada configurada no mecanismo seguro existente. Manter estes dois valores no prompt privado do chat e na configuração de teste apropriada, sem hardcode no produto. Registrar a sanitização documental.

O Founder informou que TESTE-A já esteve pareado na Resulta Seguros e na Amandus Seguros. Isso é informação histórica, não prova da sessão atual. **A autorização acompanha o telefone efetivo, não o nome do tenant, a label da conexão ou o nome da instância.**

### 1.2 O que está autorizado ao futuro executor

- Implementar a SPEC convertida e executar o processo AAA, usando as permissões vigentes do projeto.
- Testes de mensagens e documentos **entre TESTE-A e TESTE-B**, em conexões cuja identidade efetiva e vínculo com o tenant de teste foram comprovados.
- Testar o modo humano e o modo direto com os mesmos caminhos de produção e interlocutores de teste identificados; a restrição de destinatários fica na autorização do canário, não em um motor alternativo.
- Exercitar respostas automáticas exclusivamente para a conversa/participantes do canário autorizado, após provar a trava de escopo e o bloqueio de dispatch externo.
- Consultar dados mínimos necessários conforme os acessos existentes; preferir dados sintéticos no canário. Dados de corretoras diferentes nunca são copiados entre tenants para “montar teste”.

### 1.3 O que permanece proibido nesta execução

1. Usar número operacional Resulta ou AutoFleet como remetente, mesmo para enviar ao Founder.
2. Enviar para segurados, seguradoras, atendentes, grupos ou contatos fora da allowlist, inclusive por fallback, alerta, fila, reenvio e resposta automática.
3. Ativar globalmente atendimento, cobrança agendada, dispatch ou qualquer agente em tenant operacional para fazer o canário funcionar.
4. Desparear, apagar, recriar, renomear identidades operacionais, trocar QR ou sequestrar sessão existente.
5. Acionar assistência real, abrir sinistro/chamado, contratar/cotar seguro, alterar apólice, emitir pagamento ou executar ações financeiras. Agger está fora desta SPEC.
6. Alterar documentos para uma identidade “de teste” mantendo dado pessoal de outro tenant; alterar valor, vencimento ou beneficiário de boleto real.
7. Tratar as restrições de canário como permissão de retirar controles de produção.

### 1.4 Verificação imediatamente antes de cada efeito

O guardião do canário deve verificar: ambiente + tenant + run/caso de teste + conexão fixada + identidade real do remetente + destino normalizado + janela vigente + autorização do ator/rotina + orçamento de teste + tipo de operação permitido. Tanto remetente quanto destinatário devem estar na allowlist; ambos precisam ser distintos no teste de ida e volta.

Se a identidade não puder ser confirmada ou a sessão tiver sido trocada: **não enviar**. Não escolher outra conexão automaticamente. A verificação precisa cobrir texto, mídia, retorno, alertas e replay, não só o botão “testar”. Não aceitar autorização deduzida pelo LLM.

A normalização utiliza a autoridade existente de telefone brasileiro. Não usar comparação por últimos dígitos nem aliases de dois tenants como prova de dois aparelhos independentes. Não tentar conectar o mesmo número em duas sessões incompatíveis.

### 1.5 Canal autorizado ausente ou ação física necessária

Continuar código, testes isolados, conversão, gates e preparação do rollout. Deixar para o Founder somente a ação física indispensável (por exemplo, parear um dos números de teste num contexto isolado). Explicar qual número/tenant/conexão é necessário de forma privada. **Ausência de canário não vira aprovação de produção.** Não pedir autorização já concedida para os dois números; pedir somente o que de fato faltar.

## 2. Escopo completo e exclusões deliberadas

### Obrigatório nesta EXTRA

- Configuração real dos dois modos de negócio, com migração compatível das configurações antigas.
- Execução ponta a ponta da cobrança das jornadas existentes, respeitando regras de cada seguradora e tratamento explícito das indisponíveis.
- Entrega governada de texto/documento e retorno contextual pelo atendimento existente.
- Identidade da parcela, histórico durável, reserva concorrente, retomada segura e prevenção de contato repetitivo.
- Aviso humano e painel com estados verdadeiros, inclusive execução parcial.
- Preservação dos contratos de identidade/ator da 098, atendimento, observador, takeover e portais.
- Canário autorizado, regressão, roteiro funcional, atualização de acompanhamento, entrega gateada e comprovação de implantação quando o acesso permitir.

### Fora desta EXTRA, sem empobrecer seu outcome

Email corporativo, Meta oficial, segundo QR obrigatório, WhatsApp de usuários, atualização de Evolution Go, multicanal genérico, expansão de seguradoras, Agger/Quiver/Segfy, renovação, cotação, cross-sell, reativação, site público, leitura de email e execução em lote de 099–114.

O mínimo contrato de conexão/identidade/expiração indispensável à cobrança está dentro. A plataforma definitiva de canais fica para 099. Não introduzir interfaces fictícias ou seletores de opções ainda não executáveis.

## 3. Autoridades preservadas e arquitetura

Ler autoridades específicas antes de tocar a superfície: `CLAUDE.md`, SPECS 052/053 e os trechos pertinentes de 055/056/057/058; reaproveitar rotina, Work Run, aprovação, Artifact Hub, Vault, sender governado, governor e armazenamento existentes. **Não criar novo runtime, scheduler, agente paralelo de cobrança, ledger universal paralelo, inbox ou motor de delivery ao lado do atual.**

O investigador precisa localizar o escritor vigente de cada estado. Alterações no serviço de entrega devem centralizar a política usada pelos chamadores; não duplicar a proteção em um wrapper exclusivo de teste. Se o serviço existente precisar evoluir para texto + PDF, fazê-lo sob o mesmo contrato governado.

Contrato lógico mínimo, sem obrigar tabela nova:

```text
Tenant + rotina/auxiliar + Work Run + ator/autoridade de sistema
→ item de cobrança identificado e proveniente de fonte conhecida
→ destinatário validado + modalidade + conexão fixada
→ pacote imutável de texto/documento e versão
→ intenção/reserva durável + tentativas por componente
→ evidência do provedor + histórico do negócio
→ conversa/caso e devolutiva humana
```

A implementação decide colunas/tabelas somente após inventariar o schema real. Supabase mantém verdade durável; Redis é trânsito/lease/cache. Todo novo acesso é tenant-scoped no código e no banco. IDs relacionados devem pertencer à mesma corretora, inclusive documento, conexão, run, aprovação, conversa e caso.

## 4. BLOCO 0 — converter medindo, antes de código de produto

1. Confirmar worktree, `origin/main`, commits locais e modificações não commitadas. Não apagar trabalho para obter árvore limpa; usar isolamento conforme autoridade vigente.
2. Conferir hash do research pack e distinguir proposta de SPEC executável.
3. Abrir fontes do RP e remedir o fluxo UI → API → writer → job → portal → documento → entrega → inbound → agente → caso → alerta.
4. Ler `MIGRATIONS-AUTHORITY.md` antes de SQL; medir schema, constraints, índices, RLS, triggers e escritores das tabelas tocadas. Atualizar fixture a partir da realidade, incluindo nulabilidade quando necessária.
5. Inventariar conexões sem publicar segredos/telefones; separar identidade real, função, tenant e status. Mapear canário possível sem tocar sessões operacionais.
6. Medir quais modos realmente funcionam e o estado dos consumidores de aprovação. Contar filas e execuções por estado com dados mínimos.
7. Estabelecer baseline de regressão. Falha antiga precisa ser reproduzida na base e comparada, não atribuída ao ambiente por conveniência.
8. Conferir serviços implantados e contratos frontend/backend. O relatório 098 contém status de deploy histórico; não copiá-lo sem verificar. Health isolado não prova SHA nem comportamento.
9. Identificar pendências tocadas, testes relevantes, arquivos-hub e necessidade real de migration.
10. Converter com card, referências externas, gates, MUTAÇÃO por bloco, “O QUE SAIU”, caixa do Founder e critérios de fechamento.

**GATE B0:** matriz premissa → observação nova → comando/consulta → decisão, mapa de efeitos e autorização do canário. Nenhum achado não reproduzido pode ser vendido como incidente confirmado. Se algum gap já estiver fechado, testar e reutilizar.

**MUTAÇÃO B0:** desenhista fornece no aquecimento premissas deliberadamente falsas, claramente confinadas ao exercício. Executor deve refutá-las com evidência; não se alteram permissões reais.

## 5. Modalidades de negócio e compatibilidade

| Modalidade na interface | Destino | Conteúdo | Estado honesto |
|---|---|---|---|
| Encaminhar para minha equipe | Contato humano configurado e autorizado | Texto final copiável + PDF correto; contexto interno separado | Entregue/encaminhado à equipe segundo a evidência; cliente ainda não confirmado |
| Enviar diretamente ao cliente | Contato validado daquele item | Mesmo pacote final, sem instrução interna | Estado conforme tentativa e receipt, nunca pagamento presumido |
| Teste técnico | Número permitido pela sessão de teste | Simulação explicitamente identificada, quando esse modo for escolhido | Teste; não conta como entrega de negócio |
| Somente relatório | Sem envio externo | Resultado no painel | Preparado/pendente, não enviado |

Não chamar o modo humano de “teste”. Não usar `approval` sem demonstrar consumidor. A corretora escolherá sua política de envio em produção, respeitando papel e autorização. Se approval for exigido pelo mecanismo existente, integrar o ciclo request → aprovação válida → execução exatamente uma vez; se não for parte necessária da modalidade, não exibir controle sem motor.

Migrar `test` para `test`, `none` para `none` e preservar desligamento existente. **Nunca promover configuração antiga a envio direto automaticamente.** Configuração legada `approval/live` sem contrato válido deve ficar retida com explicação, sem efeito externo; documentar a migração e a ação de configuração adequada.

Alteração de destinatário, conteúdo sensível, conexão ou modalidade depois de uma aprovação invalida a autorização anterior quando afetar seu escopo. Ator removido e rotina desativada são reavaliados na hora do envio e do replay.

**GATE A:** salvar/reabrir configuração real e exercitar cada modo pelo caminho do produto; alternar corretora não mistura dados. **MUTAÇÃO A:** habilitar seletor sem executor; reaproveitar aprovação com destino diferente; promover teste legado para live — guardas devem reprovar.

## 6. Pacote humano e mensagem final

O pacote contém versão final de texto e documento associado ao mesmo item. A atendente deve conseguir copiar o texto e encaminhar o PDF sem editar comentários de homologação. A interface pode exibir dados internos do caso; o payload destinado ao cliente não pode levá-los.

Exemplo apenas ilustrativo de composição: saudação, identificação da corretora quando necessária, referência mínima da parcela, documento anexo e convite para esclarecer dúvidas. Campos e linguagem vêm dos dados validados e do Jeito de atender da corretora. Não fixar copy com afirmação de atraso, prazo ou valor não confirmado.

O pacote para a equipe deve permitir identificar e localizar o cliente no painel autorizado, sem confundir o número da atendente com o número do segurado. Se contexto adicional for enviado à equipe, manter em mensagem separada inequivocamente interna. Não transformar cada mensagem da atendente em resposta de um dos múltiplos clientes sob revisão.

Oferecer registro explícito de “encaminhado ao cliente” quando necessário para conciliar os modos. Esse é relato humano auditado, não receipt do WhatsApp do cliente. Reabrir uma tarefa e reenviar precisa de motivo e histórico.

**GATE H:** texto final livre de prefixos/sufixos de teste, sem instrução interna, PDF correto e identificação operacional no painel; envio à equipe não conclui entrega ao cliente. **MUTAÇÃO H:** incluir `[TESTE]` no payload final ou marcar cliente entregue a partir do recebimento da equipe.

## 7. Obtenção do boleto, elegibilidade e contato

Respeitar a fonte e regras de cada jornada existente: itens sem boleto por regra da seguradora, sem contato confiável, com documento incompatível ou que exigem humano ficam retidos com motivo acionável. Não baixar “qualquer PDF” e não substituir boleto por link sem alterar explicitamente a evidência/estado.

Antes de enviar: conferir correlação entre item, seguradora, apólice/recibo/parcela, documento, tenant e cliente; tipo real do arquivo, abertura, tamanho compatível e validade da URL privada usada pelo provedor. Nome de arquivo, log, preview e link não devem expor dados desnecessários.

Não afirmar pagamento pendente com dado obsoleto sem indicar necessidade de conferência. Antes de replay antigo, revalidar elegibilidade e documento. Se a fonte não fornecer informação suficiente, encaminhar à equipe.

Contato ausente, ambíguo, compartilhado sem vínculo claro, inválido ou de outra corretora → humano. O agente não inventa telefone a partir de busca genérica e não escolhe pessoa por semelhança. A validação do contato precisa ter procedência, não apenas formato numérico.

Consulta/download em portal já conectado usa somente o caminho autorizado e necessário à cobrança, sem operações de alteração de apólice ou acionamento. Se a jornada exigir ação externa além de consulta/obtenção do documento existente, identificar o efeito e a autorização necessária antes de prosseguir. Não forçar acesso nem contornar autenticação.

**GATE P:** erro de login, documento inexistente, contato inválido e PDF de outro item são retidos e visíveis; um portal indisponível não apaga o resultado dos demais. **MUTAÇÃO P:** trocar documento entre dois casos/tenants ou aceitar HTML como PDF.

## 8. Entrega governada e estados verdadeiros

Texto e PDF são componentes de uma entrega lógica. Registrar intenção, canal, destino, versão, reserva, tentativas, resultado e evidência. Não assumir capacidade do provider ainda não demonstrada. Reutilizar o Artifact Hub e o mecanismo de delivery efetivamente existentes.

Estados conceituais para mapear aos contratos atuais:

| Estado | Significado |
|---|---|
| Preparado | Pacote válido, ainda sem efeito externo |
| Aguardando equipe/aprovação | Trabalho retido para ação humana específica |
| Na fila | Intenção durável aguardando janela/lease/permissão |
| Em envio | Uma execução tem a reserva válida |
| Aceito pelo provedor | Provedor aceitou componente; não prova leitura |
| Parcial | Texto ou documento sem confirmação suficiente do outro |
| Entrega confirmada | Somente com evidência suportada pelo canal |
| Resultado incerto | Timeout/perda de confirmação depois de possível efeito |
| Falhou/precisa de atenção | Falha conhecida com próximo passo |
| Cancelado/expirado/suprimido | Efeito não deve mais acontecer |

Se o canal somente retornar booleano, registrar exatamente a evidência disponível; não fabricar receipt. “Cliente leu”, “cliente pagou” e “cobrança resolvida” nunca decorrem de HTTP 200.

Revalidar ator/autoridade da rotina, tenant, destinatário, conexão e documento imediatamente antes de cada efeito. Guardar `work_run_id` por toda a cadeia. Rotina de sistema não ganha autorização universal por estar sem usuário. Não remover o interruptor geral existente para liberar novo fluxo: separar permissão de cobrança, permissão de resposta e silenciamento intencional, sem regressão.

Fila possui validade de negócio, janela operacional/fuso, tentativas limitadas e política de cancelamento. TTL de Redis sozinho não é histórico nem reconciliação. Repetição após reinício conserva canal e autoridade; troca de conexão requer decisão explícita válida.

**GATE D:** texto+PDF, parcial, timeout, fila expirada, ator revogado e conexão trocada exercitados. **MUTAÇÃO D:** aceitar texto como pacote completo; ignorar ator no retry; escolher outro número ao desconectar.

## 9. Idempotência, concorrência e frequência de contato

### 9.1 Identidade do negócio

Definir chave estável da obrigação usando os campos reais da fonte. Incluir tenant e namespace suficiente da seguradora/conta/recibo/parcela; provar quando recibo é único. Dia, run e modalidade não redefinem a obrigação. Identificar separadamente intenção de contato, pacote/versão e tentativa de componente.

Não inventar uma chave só porque os nomes parecem corretos. Reprocessar item da mesma obrigação deve conservar identidade; recibos homônimos de seguradoras distintas não podem suprimir o cliente errado.

### 9.2 Reserva antes do efeito

Reutilizar mecanismos existentes e completar uma reserva transacional/claim com exclusão concorrente. Dois workers não podem ganhar permissão simultânea. Lease vencido após envio de resultado desconhecido não significa autorização para repetir.

Falha da consulta de histórico ou reserva → não enviar. Falha do registro posterior a possível envio → resultado incerto, reconciliação/atenção humana, sem reenvio automático cego. Não prometer exactly-once externo quando o provider não oferece a evidência necessária.

### 9.3 Regra de contato exigida pelo Founder

- Não reenviar automaticamente a mesma parcela no mesmo dia ou em dias seguintes só porque continua pendente.
- Uma nova execução não limpa histórico. Troca de modo, canal ou configuração não limpa histórico.
- Retomar apenas componente comprovadamente faltante; componente incerto exige reconciliação.
- Pedido explícito de segunda via pelo cliente ou reenvio autorizado pelo humano cria motivo rastreável e continua sujeito às guardas.
- “Já paguei”, “não sou essa pessoa”, “não quero receber” e contestação suspendem a sequência aplicável e vão para conferência/atendimento; não apagar auditoria.
- Não inaugurar régua automática de lembretes recorrentes nesta EXTRA.

### 9.4 Passagem humano → direto

Recebimento pela equipe não comprova encaminhamento ao cliente. Se o mesmo item migrar para direto e não houver certeza sobre encaminhamento, exigir reconciliação/decisão humana específica. Não marcar todos como entregues nem liberar todos novamente. Esse estado é necessário para evitar cobrança duplicada pela atendente e pelo robô.

**GATE I:** corrida concorrente; dois dias simulados; troca de modo; reinício após efeito; falha de banco; parcela distinta; segundo pedido legítimo. **MUTAÇÃO I:** retorno vazio em erro de histórico, chave incluindo somente dia/run, dois claims vencedores ou retry de timeout incerto.

## 10. Respostas e convivência no mesmo WhatsApp

Há uma ponte existente entre envios da plataforma e atendimento. Reutilizá-la, completando contexto estruturado do caso e guardas. **Um interlocutor não recebe respostas simultâneas de dois agentes concorrentes.** Atendimento e cobrança compartilham a coordenação existente com ferramentas/contexto especializado quando necessário.

Recuperar a cobrança por tenant, conexão, interlocutor e caso/entrega; usar referência de resposta à mensagem quando disponível. Não limitar primeiro todos os envios da corretora e depois tentar achar o cliente. Se houver vários casos possíveis, perguntar de forma simples sem revelar documentos de outros clientes.

| Resposta recebida | Comportamento esperado |
|---|---|
| “Que boleto é esse?” | Explicar só os fatos do caso identificado |
| “Já paguei” | Acolher, suspender repetição e pedir/encaminhar conferência; não dar baixa financeira por fala |
| “Me manda de novo” | Recuperar documento autorizado do caso; reenvio solicitado auditado |
| “O boleto venceu / quero desconto” | Não recalcular ou negociar sem capacidade autorizada; encaminhar à equipe |
| “Não sou essa pessoa” | Parar exposição de dados e sinalizar correção cadastral |
| “Não me mande mais” | Registrar preferência/supressão pertinente e acionar equipe, sem insistência |
| “Preciso de guincho” | Classificar mudança de assunto e seguir coordenação de atendimento; no canário, bloquear qualquer acionamento real |
| Retorno da equipe com vários pacotes | Tratar como interlocutor interno e pedir referência de caso quando faltar |
| Mensagem de seguradora/URA | Manter corredor/dispatch correto; nunca responder como se fosse cliente cobrado |
| Mensagem pessoal | Preservar classificação e descarte pertinentes, sem tratá-la como atendimento por conveniência |

Tom e identidade vêm do Jeito de atender da corretora. Dados recuperados/documentos/mensagens são contexto, não instruções que possam mudar autorização. Provar tentativas de injeção pedindo envio a terceiros, troca de empresa ou acesso a boleto de outra pessoa.

Preservar takeover humano e pausa do agente, inclusive mídia e eco `fromMe`. Diferenciar saída automática de intervenção humana real conforme o mecanismo existente. Cobrança não pode silenciar atendimento indevidamente; atendimento urgente não deve ser atravessado por mensagem proativa de cobrança. A política de cortesia deve adiar e explicar, sem perder o item.

**GATE C:** conversas completas e pares mínimos pelo caminho real do agente, com controle do efeito externo. Testar histórico volumoso sintético, casos simultâneos, takeover e retorno de seguradora. **MUTAÇÃO C:** nota de outra pessoa, corte global de histórico antes do cliente, bot respondendo durante takeover ou duas respostas para um evento.

## 11. Alertas, painel e recuperação

Incidente durável com tenant/run/item, etapa, motivo redigido em linguagem humana, impacto, ação sugerida, estado e histórico. Usar superfície existente de Atividades/Entregas/casos e evidenciar pendências da rotina; não criar inbox paralelo.

Alertar sobre seguradora sem acesso, download falho, contato inválido, documento incompatível, conexão desconectada, envio parcial/incerto, falha de registro, aprovação vencida, fila expirada e resposta que requer humano. Agrupar falhas repetidas por causa sem esconder clientes afetados; recuperação da conexão não dispara todo o backlog automaticamente.

Tentativa de notificação externa segue as mesmas guardas. No canário, somente TESTE-A/TESTE-B; nenhum grupo real. `destination_type` precisa ser respeitado. Não resolver qualquer destino como telefone se for outro tipo.

**Painel é obrigatório mesmo se o WhatsApp falhar.** Enquanto email definitivo estiver fora do escopo, a operação piloto é assistida por alguém com o painel aberto e roteiro de acompanhamento. Não declarar alerta externo entregue se só existe registro interno. Se o caso exigir operação desassistida que dependa de canal independente ainda ausente, registrar essa limitação de ativação; não inventar email provisório.

Resumo por execução distingue encontrados, elegíveis, preparados, retidos, aceitos pelo canal, parciais/incertos, encaminhados à equipe e entregas confirmadas conforme receipts. Contagens devem ser reconciliáveis, com definições que evitem dupla contagem. Não transformar humano avisado ou rotina finalizada em “todos os clientes cobrados”.

**GATE N:** desconectar provedor por simulação controlada, mostrar incidente e próximo passo; falha de aviso fica explícita. **MUTAÇÃO N:** alertar só pelo canal morto e concluir “suporte avisado”; esconder parcial sob status verde da rotina.

## 12. UI pronta para uso

Reaproveitar layout e componentes existentes. A interface precisa mostrar modalidade, destinatário da equipe quando aplicável, conexão/remetente com identificação apropriada ao usuário, agenda/fuso, limites existentes, estado e controle de pausar. Não exibir env vars, SQL ou nomes técnicos como instrução para a atendente.

Antes de salvar modalidade direta, deixar clara a consequência e exigir a permissão de negócio prevista; o usuário autorizado escolhe a operação, não precisa habilitar “teste” para conseguir usá-la. A configuração do canário continua separada e restrita à equipe técnica.

Testar salvamento/reabertura, troca entre corretoras, falta de configuração, estados vazios, parcial/erro e recuperação. Não remover QR ou configuração de atendimento existente. Não anunciar email/Meta já funcional.

## 13. Migração e compatibilidade

Antes de DDL: localizar autoridade, comparar objeto real e fixture, redigir APPLY/VERIFY/ROLLBACK e análise de compatibilidade entre versões. Preferir alterações aditivas com escritores/leitores compatíveis.

Histórico existente deve continuar protegendo contra repetição. Backfill sem prova de entrega não cria “entregue”; ausência de histórico também não prova que nunca houve encaminhamento humano. Definir tratamento conservador do legado desconhecido.

Teste com dois tenants isolados: leitura, gravação, referências cruzadas, actor revogado, documento estrangeiro, IDOR por troca de parâmetro. Usar fixtures próprias e canários marcados; não conectar/simular dois tenants com uma mesma conversa operacional.

Canário em tabela append-only deve ser marcado segundo autoridade existente, não apagar trigger ou dado por conveniência. Limpeza apenas por ID + tenant + marca de teste, com verificação posterior. Reversão de código não desfaz mensagem enviada; preservar evidência e impedir repetição no rollback.

## 14. Sequência interna de execução e AAA

1. RP0 + BLOCO 0 + card e relatório iniciado.
2. Investigador/pesquisador mede, reabre fontes e entrega premissas corrigidas.
3. Fable converte em SPEC definitiva, registra mudanças de escopo propostas e referências.
4. Aquecimento Opus em contexto novo, uma rodada de 10–15 perguntas com duas falsas assinadas, dúvidas reais e defeito não listado.
5. Emendar SPEC. Desenhista prepara prova, pares mínimos e gate zero vermelho em cópia limpa antes do código.
6. Builder implementa unidades coesas; um escritor por arquivo. Integração serial de contratos compartilhados.
7. Verificador mecânico: compilação/tipos, testes do bloco, lint, VERIFY de migration, rotas quando aplicável, regressão.
8. Painel CRÍTICO opção B: verdade/regressão + produto/DADO + red team, independentes, sobre produto/código/provas. Não montar painel para polir proposta.
9. Consolidar achados, corrigir materialmente; juiz fresco confirma consertos e audita dados. Respeitar limites de rodadas, nunca reusar juiz para validar o próprio achado.
10. Canário restrito e comprovação de deployment/efeito nas etapas permitidas; atualizar documentação, main gateada e dossiê.

Usar pacotes vivos de `docs/canon/pacotes/`, carregando núcleo AAA §0–§3, §5 e §7.3 e as travas específicas deste pacote. Modelos conforme o ambiente realmente disponível e autoridade vigente; nunca declarar um modelo que não foi usado.

Economia vem de leitura por demanda, contrato coeso, provas reutilizáveis, menos repetição de suite inteira e checkpoints. Não vem de trocar teste real por regex, ocultar falha ou retirar gate de segurança. Aplicar §2 junto de §9.1 do AAA: materialidade do efeito e critérios aceitos, sem transformar gosto por nomes/estilo em ciclo infinito.

## 15. Matriz de aceite e mutações obrigatórias

Cada gate precisa de caminho/comando executável na SPEC definitiva. Onde há prova viva, simulação é complemento e não substituto. Onde a execução é proibida em linha operacional, declarar a fronteira e usar canário isolado autorizado.

| Gate | Deve comprovar | Contraexemplo / mutação que precisa reprovar |
|---|---|---|
| G00 | Base, permissões e schema atuais conhecidos | Proposta tratada como produção comprovada |
| G01 | Remetente E destinatário permitidos em toda saída de teste | Remetente operacional → Founder, alerta a grupo ou replay fora da allowlist |
| G02 | `test`, humano, direto e relatório distintos e executáveis | Habilitar opção sem consumidor; teste migrado para direto |
| G03 | Pacote humano limpo e caso identificável | Prefixo de teste/instrução interna no texto encaminhável |
| G04 | Direto chega ao contato validado do item | Telefone de outro cliente ou tenant |
| G05 | PDF corresponde ao item e é acessível no canal | PDF trocado, inválido, URL expirada ou HTML disfarçado |
| G06 | Estado de texto e PDF reconciliado | Texto aceito + PDF falho contado como completo |
| G07 | Concorrência produz uma reserva vencedora | Dois workers enviam o mesmo componente |
| G08 | Reexecução/dia seguinte não insiste na parcela | Dia/run/modo novo libera novo contato automaticamente |
| G09 | Falha de histórico bloqueia efeito | Exception → conjunto vazio → envio |
| G10 | Timeout incerto não dispara retry cego | Provedor pode ter aceitado e execução repete |
| G11 | Mudança humano→direto respeita histórico/decisão | Equipe já encaminhou e robô envia de novo sem revisão |
| G12 | Fila expira/revalida ator, rotina, conexão e documento | Mensagem velha ou ator revogado sai no replay |
| G13 | Resposta recupera caso correto apesar de volume | Contexto desaparece após envios de outros clientes |
| G14 | “Já paguei”, contestação e opt-out suspendem insistência | Agente dá baixa sem prova ou cobra de novo |
| G15 | Takeover, mudança de assunto e eco automático preservados | Dois agentes respondem; cobrança pausa atendimento por engano |
| G16 | Seguradora/URA não vira interlocutor de cobrança | Dispatch responde ao cliente errado / abre chamado real no canário |
| G17 | Falhas visíveis e alertas honestos | Canal morto é usado como única prova de humano avisado |
| G18 | Dois tenants e papéis isolados no dado e no efeito | Cruzar conversa, documento, conexão ou run; IDOR |
| G19 | Reinício/rollback não perde intenção ou repete efeito incerto | Lease vencido apaga a memória de possível envio |
| G20 | Atendimento/QR/jornadas existentes sem regressão material | Recriar sessão, alterar rota de atendimento ou exibir motor fictício |
| G21 | Payload não obedece instrução maliciosa do documento/cliente | Enviar a terceiro, trocar tenant ou revelar outro boleto |
| G22 | Instalação e validação têm status e evidência separados | Main verde vira “produção validada” sem deployment/canário |
| G23 | Relatório, índice e dossiê coerentes e navegáveis | EXTRA some por regex numérica; link não publicado marcado atualizado |

O desenhista pode agrupar comandos e compartilhar fixtures. Não precisa criar um arquivo para cada gate. Mutação deve atingir comportamento real em cópia/worktree, produzir falha nova nomeada em subprocesso e restaurar por cópia. Não pode rodar sobre árvore que outro agente escreve. Guardas puramente textuais não substituem prova de envio, isolamento ou conversa.

## 16. Plano de canário controlado em produção

### Antes

Identificar privado TESTE-A/TESTE-B e conexões atuais; conferir remetente real sem alterar QR operacional. Fixar tenant/conversa/run, participantes, janela e orçamento limitado, definidos pelo executor no plano. Provar bloqueios com saídas simuladas antes de liberar qualquer envio vivo. Esvaziar/cancelar somente intenções próprias do canário; nunca limpar fila operacional inteira.

Se o sistema não permitir ativação seletiva, implementar essa limitação necessária antes do canário; nunca ligar tenant inteiro temporariamente. Proteção no último ponto de efeito e nas ferramentas de dispatch deve impedir que um pedido de guincho de teste abra atendimento real na seguradora.

### Casos mínimos

1. Equipe: pacote final de um caso de teste chega ao número de teste representando atendente; painel não registra cliente entregue.
2. Direto: contato do cliente de teste no domínio de teste resolve para o outro número autorizado; recebe texto/documento pelos serviços reais.
3. Retorno: Founder responde perguntas de cobrança; agente usa dados do caso e respeita limites. Se precisar da ação manual do Founder, explicar uma única sequência curta.
4. Reexecução: repetir job sem novo contato; repetir em dia simulado nos testes isolados, sem esperar um dia ou alterar relógio de produção.
5. Parcial/incerto/erro: falhas injetadas em ambiente controlado não enviam para terceiros; painel e retomada se comportam corretamente.
6. Convivência: conversa de cobrança e atendimento de teste, takeover e mudança de assunto, com dispatch real proibido.

Documentos sintéticos devem ser claramente sem validade financeira, sem linha digitável/PIX acionável. Essa identificação pertence ao documento de teste; o texto final do modo de negócio deve continuar limpo. Boleto real, se indispensável e já autorizado ao Founder, permanece no tenant correto e não pode ser alterado nem publicado nas evidências.

### Depois

Desligar apenas a habilitação temporária do canário, cancelar suas intenções ainda pendentes, restaurar configurações de teste que foram alteradas, conferir que não ficaram envios futuros ou agentes amplamente habilitados e preservar logs de auditoria sem PII. Verificar conexão operacional sem modificá-la. Entregar evidências com aliases.

## 17. Validação com Saionara e Regina

O Fable prepara roteiro e telas. O Founder conduz a sessão com elas pelos números de teste; o executor não as contata nem usa seus números operacionais.

Validar: facilidade de configurar modo; qualidade da mensagem; documento correto; como copiar/encaminhar; clareza do status; atendimento de dúvida; aviso de erro; regra de não insistência; localização do histórico; pausa e retomada. Registrar feedback e aceites de cada uma somente se realmente recebidos.

Roteiro deve distinguir “não testado”, “aprovado pelo canário técnico” e “validado pela atendente”. Não bloquear trabalho técnico esperando a agenda delas; também não declarar o aceite delas antecipadamente. Uma autorização posterior para linhas operacionais deverá ser específica e registrada fora desta execução.

## 18. Entrega, implantação e rollback

Preflight e regressão segundo autoridade vigente. Nunca `git add -A`, force push, exclusão de trabalho ou alteração de guardas apenas para obter verde. Se main avançar, integrar com cuidado e repetir gates pertinentes sobre o commit que será entregue. Colar saída real do push e SHA; conferir head remoto.

Deployment segue o mecanismo e a autorização do projeto. Se a autoridade vigente exigir clique do Founder no EasyPanel, preparar tudo e deixar esse clique como ação final concreta; não contornar via API. Se houver autorização e mecanismo válido para implantação pelo executor, executá-la com a sequência medida. Não reutilizar automaticamente “web antes de api” da 098: medir compatibilidade desta mudança.

Relatório distingue:

| Marco | Evidência exigida |
|---|---|
| Implementado e gateado | Commit, gates, mutações e parecer independente |
| Entregue na main | SHA remoto e saída do push |
| Implantado | Serviço/imagem/SHA ou evidência equivalente verificável + health/contratos |
| Validado no canário autorizado | Casos, participantes por alias, resultados e nenhum efeito fora do escopo |
| Validado pelas pilotos | Feedback real de Saionara/Regina, registrado pelo Founder |
| Ativado em linhas operacionais | Fora da autorização atual; não realizar nem presumir |

Produto completo e implantado pode permanecer desativado para linhas operacionais por autorização. Isso é uma fronteira de uso, não desculpa para deixar os modos sem motor. Se um gate material faltar, status PARCIAL/BLOQUEADO conforme o caso; “pronto” não substitui evidência.

Rollback: parar efeitos novos da funcionalidade, cancelar filas próprias conforme semântica do negócio, preservar entrega incerta e histórico, reverter código/flags de forma compatível, executar VERIFY e smoke. Não apagar ledger para permitir retry, não apagar dados de clientes e não prometer desfazer mensagens já enviadas.

## 19. Documentação e acompanhamento obrigatórios

Durante a execução, atualizar com um único escritor por arquivo:

1. SPEC definitiva e relatório no template canônico, card no início e telemetria de cinco linhas.
2. `docs/canon/INDICE-DE-SPECS.md`: EXTRA-001 como trabalho atual; 099–114 pausadas na sequência linear; sem renumerar ou marcar canceladas.
3. `docs/canon/ESTADO-DAS-SPECS.md` e `EXECUTION-MASTER-PLAN.md`, nas seções pertinentes, mantendo histórico.
4. `FOUNDER-DECISIONS.md`, `CHANGE-ADDENDA.md`, `PENDENCIAS.md`, manifesto de migrations quando aplicável.
5. `docs/canon/reports/dossies/dossies-autobrokers.html`: página `p-extra001` (ou ID equivalente compatível medido), item de navegação, linha na home, próximo passo, progresso por bloco, testes, pendências, deploy e caixa do Founder.
6. Memória/handoff do programa no mecanismo local existente, com a nova fila e as restrições de teste; não inventar acesso a uma ferramenta de memória.

A família EXTRA deve aparecer nos guardas de protocolo, indexadores e navegação. Se houver regex que só aceita `SPEC-0NN`, adaptar o reconhecimento preservando a exigência AAA, com teste positivo EXTRA e negativo relatório incompleto. **Não renumerar para 115 nem excluir EXTRA dos guardas.**

Publicação solicitada: https://claude.ai/code/artifact/afe1510d-f31c-4d13-9441-aa920ad2b868

Conforme prompts anteriores, ler o HTML publicado inteiro antes de republicar com `url`, preservar conteúdo e publicar a cada bloco fechado. Verificar que o link mostra a alteração. Se a ferramenta não existir ou faltar acesso, atualizar fonte e registrar publicação pendente com arquivo e instrução exata; não alegar atualização do URL. Nunca publicar números de teste completos ou dados de clientes.

Não criar um painel novo para substituir o acompanhamento pedido. Corrigir na home a diferença entre “na main” e “no ar” quando relacionada ao estado desta entrega, sem reescrever vereditos históricos sem evidência.

## 20. O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS

Transportar para a SPEC definitiva as três referências E01–E03 do research pack, reabertas pelo pesquisador, no formato AAA §7.3: URL · faz · modelamos · rejeitamos · como o juiz inspeciona · data. São padrões para integridade, consistência entre banco/efeito e eventos idempotentes; não introduzem provedores novos.

## 21. O QUE SAIU E QUANDO VOLTA

| Frente | Motivo de não entrar nesta EXTRA | Gatilho de retorno |
|---|---|---|
| Email/Meta/multicanal completo | Não é necessário para provar cobrança no WhatsApp atual | SPEC-099 após pilotos, reconciliando SPEC-069 |
| Segundo QR | Não deve atrasar nem mexer nas sessões atuais | Decisão de canais e contrato de múltiplas conexões |
| Atualização Evolution Go | Não é objetivo; risco de regressão sem benefício demonstrado | Diferença upstream/runtime relevante comprovada |
| Agger | Investigação independente sem credenciais disponíveis neste pacote | Nova proposta EXTRA-002 e acesso autorizado |
| Auxiliares comerciais adicionais | Dependem de capacidade de cálculo e dados | Prova Agger e propostas específicas |
| Outras SPECS 100–114 | Pausa do lote linear para resultado imediato | Dependência real ou retomada deliberada da fila |

Os itens obrigatórios da §2 não podem sair silenciosamente. Se a conversão mostrar conflito material, registrar proposta de mudança e preservar o trabalho possível; não chamar recorte unilateral de “otimização AAA”.

## 22. Fila após esta entrega — contexto, não autorização para executar agora

EXTRA-001 operação dos pilotos → EXTRA-002 investigação/prova Agger → 099 canais após pilotos → EXTRA-003 renovação (inclui capacidade compartilhada de cálculo) → EXTRA-004 cotação pelo chat → EXTRA-005 reativação → EXTRA-006 cross-sell → EXTRA-007 site de captação/cotação → EXTRA-008 Quiver → EXTRA-009 Segfy → EXTRA-010 assistente de email.

Quiver/Segfy podem subir de prioridade quando uma corretora trouxer acesso e demanda. 100–114 continuam existentes; executar por dependência comprovada e planejamento posterior. Agger será primeiro provedor investigado, não arquitetura fixa. Esta sessão não cria nem executa as próximas propostas. Seu handoff deixa a investigação Agger como próximo assunto com o Founder.

## 23. Definição final de conclusão

Concluir o outcome inteiro dentro da autorização: modos de cobrança com motor, documento correto, destino/contexto corretos, reexecução segura, atendimento preservado, respostas e suporte, evidências AAA, entrega e acompanhamento atualizados. Indicar separadamente qualquer dependência física de implantação, teste ou aceite das atendentes.

O resumo ao Founder precisa responder em linguagem simples: o que consigo usar; como configuro; o que foi realmente testado; o que ficou desligado por autorização; que falhas ainda impedem uso; onde acompanhar; qual é a única próxima ação necessária. Não atribuir “100% testado em produção” a uma suite ou a uma leitura de código.
