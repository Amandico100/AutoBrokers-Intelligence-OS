# Relatório de implementação — SPEC-051

**Data:** 22/07/2026
**Branch de execução:** `feat/spec-051-evolution-go-pairing`
**Provider:** `0.7.2-autobrokers.1`
**Status:** implementação técnica em validação; ação física de QR ainda não executada

## Resultado técnico até aqui

### Provider e infraestrutura

- upstream fixado no commit `9337afc47e10b86cc896a6f432240e40fee95dd1`;
- imagem sem `latest`, executada pelo usuário não-root `evolution`;
- diretório `/app/logs` criado com ownership correto;
- health público retorna `status=ok` e `version=0.7.2-autobrokers.1`;
- uma réplica, `CONNECT_ON_STARTUP=false` e limite de QR explícito;
- bancos `evogo_auth` e `evogo_users` isolados no papel `evolution_go`;
- ownership de database, schema, tabelas e sequências ajustado para o papel;
- linha de base ociosa observada: 1 conexão auth + 2 users = 3 conexões;
- erro de ownership do GORM identificado durante a implantação e corrigido sem
  alterar o banco principal do produto.

### Pareamento e passkey

- máquina de estados com 25 estados canônicos;
- tentativa e lock distribuído por `company_id + purpose` no Redis;
- timeout de rede de 10s, setup de 30s, proxy Next de 20s e tentativa total de
  10 minutos;
- polling serial, retomada por `attempt_id`, proteção contra clique duplo,
  cancelamento e retry explícito;
- apenas um `/instance/connect` por tentativa;
- QR expirado e falhas de passkey são terminais;
- confirmação de passkey acima de 90 segundos é invalidada;
- tokens do provider permanecem no backend e são cifrados no banco;
- helper `0.7.2-ab1` disponível com SHA-256, limitado a
  `https://web.whatsapp.com` e ao origin fixo do Evolution Go;
- pareamento por número disponível apenas como alternativa secundária.

### Observador e agentes

- integração criada como `purpose=observer`, escopo
  `insurers_and_clients`, `agent_id=null`;
- agente de atendimento permanece `is_active=false`;
- Observador sem import ou caminho de envio de mensagem;
- chats diretos aceitos por tenant; grupos, status, chamadas, self e números
  internos/excluídos são descartados na borda;
- mídia registrada primeiro como metadado e enriquecida em fila assíncrona;
- bytes arquivados em objeto privado; áudio, imagem e documento usam os
  serviços existentes; temporários são removidos em `finally`;
- Atlas incremental configurável em 15 minutos;
- memória dos agentes configurável em 6 horas;
- botão administrativo **Processar aprendizado agora** processa dados novos sem
  publicar conhecimento automaticamente;
- mudanças estruturais continuam dependentes de revisão e playbooks/cards
  permanecem em draft/pending review.

## Testes automatizados executados

- contrato de pareamento/passkey da SPEC-051: verde;
- contrato de isolamento/Observador/agentes da SPEC-051: verde;
- contrato de runtime da imagem: 3/3 verde;
- compilação Python dos módulos alterados: verde;
- TypeScript `tsc --noEmit`: verde.

O relatório será atualizado com a bateria de regressão, deploy Web/API,
tentativa técnica única de QR, estabilidade do pool e evidências de Resulta e
AutoFleet antes do encerramento.

## Ajustes de revisão e validação concluídos

- fallback global bloqueado para `purpose=observer`; corretora sem integração
  recebe estado seguro `unpaired`, sem enxergar instância de outro tenant;
- segunda aba ou reload reutiliza a tentativa ativa mesmo após o lock de setup;
- refresh e cancelamento serializados por tentativa, sem ressurreição de estado;
- gravação de estado protegida por revisão/CAS atômico no Redis, inclusive se o
  lock expirar durante uma chamada lenta do provider;
- `@lid` só é capturado com JID telefônico alternativo verificável; caso
  contrário, a borda falha fechada;
- Atlas incremental com watermark por seguradora/ramo e deduplicação de drift
  estrutural ainda não resolvido; execuções concorrentes usam claims `SET NX`;
- testes comportamentais cobrem tentativa única, isolamento Resulta/AutoFleet,
  corrida poll×cancel, retry fresco, expiração de passkey após 90 segundos e
  sucesso/falha isolada do worker de mídia;
- build Next de produção concluído com 123 páginas;
- regressões SPEC-017/038/040/045/047/048/049/050 e adapters concluídas sem
  falha.

## Pendências físicas autorizadas ao founder

Nenhuma solicitada até o momento. O próximo ponto de parada será somente quando
todo o deploy estiver pronto e for necessário escanear o QR ou confirmar a
passkey no dispositivo.
