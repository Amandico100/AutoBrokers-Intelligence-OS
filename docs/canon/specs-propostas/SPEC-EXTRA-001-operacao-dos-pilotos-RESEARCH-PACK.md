# SPEC-EXTRA-001 — RESEARCH PACK
## Cobrança completa e convivência com atendimento para os pilotos

**Versão:** 1.0 · 07/09/2026. **Natureza:** evidência para conversão; não é relatório de execução.
**Repositório:** Amandico100/AutoBrokers-Intelligence-OS.
**Baseline remoto consultado nesta preparação:** `34424fa576f8fdb35f687e3a3af5c66a6e07f915`.
**Método:** leitura pelo conector GitHub de arquivos nessa revisão e documentação primária pública. Nesta preparação não foram executados testes do produto, consultas novas ao banco, envios, entrada em portais, alterações de produção ou implantação. Não confundir leitura de código com prova de funcionamento.

## 0. Legenda e precedência

- **DECISÃO:** instrução explícita do Founder incorporada à proposta.
- **OBSERVADO NO REPO:** existência/comportamento visível no código dessa revisão; precisa de prova de execução no BLOCO 0.
- **HIPÓTESE:** consequência a investigar; não é incidente constatado.
- **PENDENTE DE MEDIÇÃO:** precisa de comando, consulta ou canário autorizado.
- **FONTE EXTERNA:** padrão documentado; não determina a arquitetura interna.

A instrução atual sobre números de teste prevalece sobre permissões mais amplas de documentos antigos. Esta entrega é documentação; o Fable é o futuro executor. Os documentos não contêm credenciais nem autorizam uso de linhas operacionais das corretoras.

## 1. Fontes canônicas inspecionadas e como aproveitar

| Fonte no repositório | O que aproveitar | O que não transportar sem conferir |
|---|---|---|
| `CLAUDE.md` | Autoridades únicas, isolamento, bootstrap, migrações, gates, condições de parada, relatório | O caminho de worktree de um exemplo não prova que a árvore esteja atualizada |
| `docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md` | v11.2, card, conversão medida, aquecimento, mutação, laço independente | Não reescrever o protocolo para reduzir a qualidade desta EXTRA |
| `docs/canon/DECISAO-DO-RITMO-03-09-2026.md` | Opção B, sessão nova, orçamento, CRÍTICO com duas lentes + red team + juiz fresco | Introdução histórica de protocolo pausado não é a fila atual; prompts 098/099 já adotam B |
| `docs/canon/PROMPT-DE-ABERTURA-098-PREENCHIDO.md` | Handoff de estado, conversão seguida de execução, dossiê por bloco | Apagar `index.lock` por timeout não é seguro sem comprovar ausência de processo proprietário |
| `docs/canon/PROMPT-DE-ABERTURA-099-PREENCHIDO.md` | Herança da 098, pendências por número, canário, atualização do dossiê | Fila 099 imediata foi substituída pelo Founder; números de runtime são históricos |
| `docs/canon/pacotes/PACOTE-AQUECIMENTO.md` e `README.md` | Pacotes curtos, contexto novo, perguntas refutáveis e duas falsas assinadas | O aquecimento continua somente leitura; autorização limitada de canário não se estende a investigadores/juízes |
| `docs/canon/specs-propostas/9 - SPEC-095-artifact-delivery-hub-completion.md` e research pack correspondente | Metadados, legenda, outcome, não objetivos, contratos, gates, matriz de evidência e referências | A proposta histórica não prova que a entrega atual implementou tudo que ela desejava |
| `docs/canon/specs/SPEC-078-o-auxiliar-de-cobranca-funciona-e-a-entrega-aparece.md` | Ponto de partida da cobrança e separação entre opção exibida e motor real | Não atribuir implementação a uma futura 079 apenas porque o código a menciona |
| `docs/canon/reports/SPEC-098-EXECUTION-REPORT.md` | Herança de identidade, tenant, ator, esquema vivo e pendências | Não copiar falhas antigas, contagens ou status de deploy como se tivessem sido medidos hoje |
| `docs/canon/reports/SPEC-EXECUTION-REPORT-TEMPLATE.md` | Estrutura de relatório preenchida durante a execução | Ajustar referências históricas de seções ao protocolo vigente sem eliminar campos obrigatórios |
| `docs/canon/reports/dossies/dossies-autobrokers.html` | Fonte versionada do acompanhamento solicitado pelo Founder | Estar na main não significa estar implantado; o HTML contém textos históricos dessa natureza |

As propostas 097/098 são citadas por prompts antigos, mas não constam da árvore remota de `specs-propostas` consultada. Podem existir localmente. Não inventar seu conteúdo nem bloquear esta EXTRA por sua ausência: usar SPECS convertidas, relatórios e padrões disponíveis.

## 2. Achados centrais no código

As linhas abaixo são coordenadas desta baseline, não contratos permanentes. Reencontrar os símbolos na revisão de execução e ler a função inteira, seus chamadores e consumidores.

| ID | Evidência observada | Consequência para a conversão / prova necessária |
|---|---|---|
| R01 | `backend/app/services/billing_collection.py:1730–1743`: `approval` registra espera; `live` termina com envio direto desativado | Implementar a cadeia efetiva. Não apenas remover o aviso ou habilitar seletor |
| R02 | `components/auxiliares/PainelDeRotinas.tsx:90–112,813–833`: opções com motor são `test` e `none`; comentário aponta aprovação sem consumidor | Rastrear `send_billing_whatsapp` até efeito real. Encaminhar ao humano é modo próprio de negócio, não sinônimo de approval |
| R03 | `billing_collection.py:888–905`, `_format_test_message` | Marcadores e comentários de simulação estão no payload. Criar composição final limpa sem apagar o modo técnico de teste |
| R04 | `billing_collection.py:908–921`, `_already_sent_recibos`: falha de consulta devolve conjunto vazio | Testar falha do banco antes do efeito: recusar envio e registrar pendência, nunca interpretar como ausência de histórico |
| R05 | `billing_collection.py:924–953`, `_record_sent`: conflito `company_id,recibo,send_mode`; portal é armazenado fora da chave | Identidade do recibo precisa ser provada por seguradora/conta/apólice/parcela. Colisão entre seguradoras é hipótese, não incidente medido |
| R06 | `billing_collection.py:1035–1124`: leitura prévia, texto, documento, registro posterior; texto aceito pode coexistir com documento falho | Reserva atômica e estados separados. Timeout externo não admite retry cego. Falha do PDF não é entrega completa |
| R07 | `billing_collection.py:227–265`, `avisar_suporte_humano`: resolve destino e envia pela integração WhatsApp; ausência/falha retorna falso | Aviso pelo canal avariado pode falhar. Incidente durável no painel é obrigatório; destino precisa respeitar tipo e autorização |
| R08 | `platform_outbound.py:880–950`, `send_to_client_guarded`: ator/run e interruptor do atendimento; assinatura atual recebe texto | Estender caminho governado para documento e destino explícito, preservando revalidação. Não ativar atendimento inteiro para destravar cobrança |
| R09 | `platform_outbound.py:1071–1084`, `_entregar_agora`: integração selecionada novamente por empresa | Fixar conexão autorizada ao pedido e revalidá-la no efeito/replay. Mudança de conexão não pode trocar remetente silenciosamente |
| R10 | `platform_outbound.py:1182–1207`, `context_note_for`: limita registros recentes da empresa antes de filtrar o telefone | Testar cliente cujo envio não está na amostra recente. Contexto da cobrança precisa ser recuperável pelo caso e pelo interlocutor |
| R11 | `backend/app/api/webhook.py:981–983`: `context_note_for` entra no fluxo do atendimento | Há ponte de contexto; não foi demonstrado um agente especializado completo de respostas de cobrança |
| R12 | `backend/app/services/whatsapp/channel_identity.py:84,141`: observer/attendance/dispatch compartilham identidade canônica | `purpose=observer` não prova ausência de atendimento. Preservar número, sessão e QR; não recriar conexão para renomear propósito |
| R13 | `backend/app/services/atlas/observer_intake.py:800–829`: observer consome conforme agente ligado/desligado | Provar caminho do webhook até grafo com canário restrito; não mudar condição global para fazer um teste passar |
| R14 | `backend/app/api/webhook.py:396–398,1335`: integração pode viajar no inbound | Conferir isolamento de entrada e de saída juntos; uma metade correta não prova a outra |

### 2.1 O que continua desconhecido

- Identidade real das conexões atualmente pareadas e quais pertencem aos dois números autorizados.
- Imagem/SHA realmente implantados em cada serviço; status operacional atual dos portais.
- Conteúdo, permissões e estado atual de rotinas, filas, aprovações, destinos e credenciais.
- Contratos reais de receipts/documentos do Evolution Go implantado.
- Cobertura e latência reais de cada jornada de cobrança e atendimento.
- Se há implementação posterior/local que fechou algum achado acima.

Não transportar censos anteriores como números de hoje. A investigação anterior viu peças para seis jornadas (Allianz, HDI, Tokio Marine, Yelum, MAPFRE, Zurich); o executor deve confirmar o registro atual em `backend/portal_worker/journeys/__init__.py`. Jornada registrada não significa canário aprovado.

## 3. Pesquisa externa — fontes primárias reabertas em 07/09/2026

### E01 — PostgreSQL: constraints

URL: https://www.postgresql.org/docs/current/ddl-constraints.html

O que faz: define integridade por UNIQUE, NOT NULL, CHECK e chaves estrangeiras; explica a semântica de valores nulos.

O que modelamos: identidade de negócio com restrições verificáveis, inclusive tenant e campos obrigatórios, e testes que exigem recusa pelo banco.

O que rejeitamos: supor que UNIQUE posterior ao envio garante uma única mensagem externa. Também não assumir que CHECK elimina nulos.

Como o juiz inspeciona: reabre a documentação da versão de Postgres efetivamente usada e executa inserções adversariais somente em fixtures autorizadas.

### E02 — AWS: transactional outbox

URL: https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html

O que faz: trata a inconsistência de escrever no banco e publicar mensagem como operações separadas.

O que modelamos: intenção durável ligada à transação de negócio, retomada e consumo idempotente no mecanismo existente.

O que rejeitamos: instalar uma stack AWS, outro scheduler ou uma segunda autoridade de delivery. O padrão não fornece exactly-once externo por si só.

Como o juiz inspeciona: falha entre reserva, envio e confirmação; recomeço do processo; duas execuções disputando o mesmo item.

### E03 — Stripe: webhooks

URL: https://docs.stripe.com/webhooks

O que faz: documenta tratamento de eventos repetidos, entrega e verificação de eventos de provedor.

O que modelamos: processamento idempotente e validação do evento recebido, sem presumir ordem de chegada.

O que rejeitamos: copiar headers, assinatura ou contrato da Stripe para o Evolution. A verificação real deve seguir o provedor efetivamente instalado.

Como o juiz inspeciona: repete e reordena eventos numa entrada controlada; um evento estrangeiro não altera outro tenant ou entrega.

Estas três referências alimentam a seção obrigatória do protocolo §7.3. O pesquisador do Fable deverá reabri-las na conversão e registrar a data. São padrões de integridade pertinentes a esta EXTRA; pesquisa de Meta, SES, Agger e outros provedores pertence às próximas etapas.

## 4. Roteiro de remedição — leitura antes de edição

Rodar na árvore correta. Comandos são instruções para o futuro executor, não saídas já obtidas nesta preparação.

```bash
git fetch origin
git rev-parse HEAD
git rev-parse origin/main
git rev-list --count HEAD..origin/main
git rev-list --count origin/main..HEAD
git status --short
rg -n 'send_billing_whatsapp|MODOS_COM_MOTOR|customer_send_allowed' backend components app
rg -n '_already_sent_recibos|_record_sent|dedup_de_envio_ativa' backend/app/services/billing_collection.py
rg -n 'send_to_client_guarded|send_document|_entregar_agora|context_note_for' backend/app
rg -n 'human_support_destinations|avisar_suporte_humano' backend/app
rg -n 'purpose_canonico|FUNCOES_DO_NUMERO_DA_CORRETORA|_agente_ligado' backend/app/services
rg -n 'P-098-FILA-SEM-EXPIRE|P-098-RUN-NOS-JOBS|P-098-FICHA-RMW|P-097-TELEFONE-BR-DUPLICADO|P-098-UNIT-B-NA-SUITE|P-098-FIXTURE-NOT-NULL' docs/canon/PENDENCIAS.md
rg -n 'SPEC-0|p-s0|section.page|querySelectorAll' backend/tests/test_o_protocolo_tem_policia.py docs/canon/reports/dossies/dossies-autobrokers.html
```

Antes de SQL, ler `docs/canon/MIGRATIONS-AUTHORITY.md`. Obter versão do banco e schema das tabelas realmente tocadas via `information_schema`/catálogo, não por suposição. Nunca consultar segredos como parte de um censo. Consultar agregados e IDs técnicos apenas quando necessários, mantendo telefone e conteúdo pessoal fora de saídas compartilhadas.

### Censo mínimo que a SPEC definitiva precisa registrar

| Medição | Forma de evidência | Não concluir |
|---|---|---|
| Modos de rotina e existência do consumidor de approval | Rastreamento UI → API → writer → job → envio | Seletor = motor |
| Conexões e identidade do remetente | Consulta com dados sensíveis restritos; comparação com a allowlist privada | Nome “Resulta” = número autorizado/proibido |
| Integridade das relações | Schema vivo, restrições e prova com dois tenants isolados | Service role dispensa filtro |
| Dedup real | Disputa concorrente e falha injetada em cópia controlada | Índice após side effect = exatamente uma entrega |
| Documento e recibo de envio | Contrato do adapter + mensagem/documento reais no canário autorizado | HTTP 200 = cliente leu ou pagou |
| Contexto de retorno | Evento → conversa → caso → resposta → número de origem | Nota genérica no prompt = atendimento de cobrança aprovado |
| Alertas | Falhas injetadas, incidente no painel e tentativa de aviso autorizada | Erro no log = humano avisado |
| Instalação | SHA/imagem e health por serviço, gates vivos permitidos | Push na main = produção |

## 5. Pendências herdadas a drenar somente se tocadas

`P-098-FILA-SEM-EXPIRE`, `P-098-RUN-NOS-JOBS`, `P-098-FICHA-RMW`, `P-097-TELEFONE-BR-DUPLICADO`, `P-098-UNIT-B-NA-SUITE`, `P-098-FIXTURE-NOT-NULL` e pendências da 078 ligadas aos caminhos medidos. Reencontrar por número e dar estado FECHADA / CONTINUA / MORREU com evidência. Não assumir que continuam abertas só porque foram citadas no prompt 099.

A sequência 099–114 continua preservada. Corrigir a expiração ou identidade de uma entrega de cobrança nesta EXTRA não obriga implementar Channel Fabric inteiro. Registrar a peça absorvida e o contrato que a 099 poderá reutilizar.

## 6. Armadilhas que o aquecimento deve refutar

1. `approval` equivale a enviar o pacote final para a atendente. Não equivale.
2. `observer` significa que o WhatsApp não atende. O código faz a distinção por outros controles.
3. Texto aceito e PDF falho pode aparecer como sucesso completo. Deve reprovar.
4. Trocar modo, dia, conexão ou run pode reiniciar a permissão de cobrar a mesma parcela. Deve reprovar.
5. Mensagem recebida pelo Founder autoriza usar qualquer remetente do tenant. Não autoriza.
6. Dois aliases do mesmo número podem servir como teste independente A → B. Não servem.
7. Desligar o atendimento global para o canário ou ligá-lo globalmente para destravar cobrança é aceitável. Não é.
8. TTL no Redis resolve validade da cobrança e histórico de negócio. Não resolve sozinho.
9. Falha de delivery pode gerar alerta pelo mesmo canal e considerar suporte avisado. Não prova aviso.
10. Um retorno “já paguei” comprova pagamento. Não comprova; suspende repetição e exige conferência.

## 7. Acompanhamento publicado

URL solicitado: https://claude.ai/code/artifact/afe1510d-f31c-4d13-9441-aa920ad2b868

A abertura pública nesta preparação falhou. A fonte no GitHub foi lida. Os prompts 098/099 instruem ler o HTML publicado completo antes de republicar com `url`, atualizar por bloco fechado e preservar a navegação derivada do DOM.

O executor deverá verificar qual ferramenta de publicação está disponível no novo chat. Se não conseguir republicar, atualizar a fonte versionada e registrar **publicação pendente**, com o arquivo e a ação exata para o Founder. Não inventar que o link foi atualizado; não substituir o acompanhamento por outro artifact sem explicar.

## 8. Regra de integridade deste research pack

O hash SHA-256 é fornecido no manifesto do pacote e vinculado na proposta. O RP0 do Fable verifica os bytes recebidos antes da conversão. Se houver edição/normalização de quebras de linha, registrar a diferença e a origem antes de atualizar a referência; não “consertar” o hash para esconder mudança de conteúdo.
