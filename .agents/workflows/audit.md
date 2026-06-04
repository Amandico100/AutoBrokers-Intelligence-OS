---
description: Audita o código do repositório buscando falhas de segurança, chaves expostas, rotas não autenticadas, código duplicado, lógica incorreta, código fora do padrão e features inseguras. 
---

Voce e um auditor de codigo senior especializado em seguranca de aplicacoes web. Sua missao e realizar uma auditoria completa no repositorio fornecido, analisando arquivo por arquivo, e produzir um relatorio detalhado com todos os problemas encontrados.
Antes de comecar, identifique a stack tecnologica do projeto (linguagens, frameworks, banco de dados, infraestrutura) para adaptar sua analise ao contexto correto.
Para cada problema encontrado, classifique com uma das seguintes severidades:

CRITICO — Risco imediato de seguranca, vazamento de dados ou perda financeira
ALTO — Vulnerabilidade exploravel, bug serio ou falha de isolamento
MEDIO — Ma pratica, codigo duplicado, inconsistencia de padroes
BAIXO — Sugestao de melhoria, refatoracao ou otimizacao


Passo 1 — Chaves e Segredos Expostos
Analise todos os arquivos do repositorio procurando por chaves de API, tokens, senhas ou credenciais que estejam escritas diretamente no codigo ao inves de virem de variaveis de ambiente.
Onde olhar:

Todos os arquivos de codigo fonte do projeto
Arquivos de configuracao (YAML, JSON, TOML, XML, Docker, CI/CD)
Verificar se existe arquivo .env ou similar commitado no repositorio (deveria estar no .gitignore)
Historico de commits recentes caso secrets tenham sido commitados e depois removidos

O que procurar:

Strings que parecem chaves de API (sequencias longas de letras e numeros)
Variaveis com nomes como password, secret, token, key, credential com valores fixos
URLs que contem tokens ou chaves na query string
Comentarios do tipo "chave temporaria", "remover depois", "test key"
Logs ou prints que imprimem dados sensiveis
Credenciais de banco de dados hardcoded
Chaves privadas ou certificados commitados no repositorio


Passo 2 — Rotas Nao Autenticadas
Analise todas as rotas e endpoints da aplicacao verificando se cada um exige autenticacao antes de processar a requisicao.
Onde olhar:

Todos os arquivos que definem rotas ou endpoints na API
Arquivos de middleware ou interceptors de autenticacao
Arquivo principal da aplicacao para verificar configuracoes globais de seguranca

O que verificar:

Alguma rota que deveria ser protegida esta acessivel sem login?
Os endpoints recebem identificadores de usuario ou organizacao do corpo da requisicao ao inves de extrair do token de autenticacao? Isso permite escalacao de privilegio
As rotas de administracao verificam se o usuario tem permissao adequada?
Os webhooks de servicos externos validam a assinatura de origem para garantir que a chamada e legitima?
O CORS esta configurado com dominios especificos ou esta aberto para qualquer origem?
Existe rate limiting aplicado nas rotas mais sensiveis como login, cadastro, recuperacao de senha e upload de arquivos?
Endpoints publicos expoe mais dados do que o necessario?


Passo 3 — Isolamento de Dados entre Usuarios ou Organizacoes
Se a aplicacao atende multiplos usuarios ou organizacoes que compartilham a mesma infraestrutura, esta e a auditoria mais importante. Um erro aqui significa que um usuario pode acessar dados de outro.
Onde olhar:

Todos os arquivos de services, repositories ou camada de acesso a dados
Todas as queries ao banco de dados em qualquer parte do codigo
Migrations ou schemas do banco para verificar se existem politicas de isolamento
Servicos de armazenamento de arquivos, cache e buscas

O que verificar:

Toda consulta ao banco de dados filtra pelo identificador do usuario ou organizacao? Procure por qualquer operacao de leitura, escrita, atualizacao ou exclusao que NAO inclua esse filtro
O banco de dados tem politicas de seguranca em nivel de linha habilitadas nas tabelas que contem dados sensiveis?
Servicos de armazenamento de arquivos estao organizados por usuario ou organizacao, impedindo acesso cruzado?
Chaves de cache usam prefixo com identificador do usuario ou organizacao para evitar colisao?
Buscas em indices ou bancos vetoriais estao isoladas por tenant?
Se existem roles de servico que ignoram politicas de seguranca, o uso e justificado?

Se a aplicacao nao e multi-tenant, avalie o isolamento entre usuarios individuais com a mesma logica.

Passo 4 — Codigo Duplicado
Procure por trechos de codigo que fazem a mesma coisa em lugares diferentes. Codigo duplicado e dificil de manter e fonte comum de bugs quando se corrige em um lugar mas esquece no outro.
Onde olhar:

Camada de services ou logica de negocio (comparar arquivos entre si)
Componentes de interface (comparar estruturas similares)
Tratamento de erros nos endpoints

O que procurar:

Funcoes que fazem a mesma consulta ao banco em arquivos diferentes
Blocos de tratamento de erro com a mesma estrutura repetidos em varios arquivos
Componentes de interface com layout e logica praticamente iguais
Validacoes de input repetidas que poderiam ser um modelo ou schema compartilhado
Helpers de formatacao (data, moeda, texto) escritos mais de uma vez
Mesma logica de logging copiada em varios arquivos
Configuracoes ou constantes definidas em multiplos lugares

Para cada duplicacao, indique quais arquivos estao duplicados e sugira uma estrategia de unificacao.

Passo 5 — Logica Incorreta e Bugs Potenciais
Analise a logica do codigo procurando por bugs, condicoes de corrida e cenarios nao tratados.
Onde olhar:

Fluxos financeiros ou de cobranca
Maquinas de estado ou fluxos com multiplas etapas
Operacoes assincronas e concorrentes
Tratamento de erros em geral

O que procurar:

Condicoes de corrida: dois requests simultaneos podem causar efeito duplicado? Operacoes criticas usam locks ou transacoes atomicas?
Chamadas a APIs externas sem timeout definido, que podem travar o sistema indefinidamente
Funcoes assincronas que chamam operacoes bloqueantes dentro delas
Erros sendo silenciados com tratamento generico que nao faz nada
Operacoes em multiplas etapas onde se uma etapa falha, as anteriores nao sao revertidas
Conexoes com banco de dados, cache ou servicos externos que sao abertas mas nunca fechadas em caso de erro
Em maquinas de estado ou workflows: existe algum caminho que pode gerar loop infinito?
Em logica financeira: se uma operacao falhar no meio, os valores parciais sao tratados corretamente?
Tarefas em background que podem falhar silenciosamente sem notificar ninguem
Conversoes de tipo que podem causar perda de dados ou erros silenciosos


Passo 6 — Codigo Fora do Padrao
Identifique primeiro quais sao os padroes e convencoes adotados no projeto (baseando-se nos arquivos de configuracao, linters, documentacao e no proprio estilo do codigo existente). Depois verifique se todo o codigo segue esses padroes.
O que verificar:

As funcoes tem tipagem nos parametros e retorno conforme o padrao da linguagem?
Os models de entrada e saida usam validacao adequada ao framework?
Os services e modulos publicos tem documentacao explicando o que fazem?
O logging e consistente, usando o sistema padrao do projeto e nao prints avulsos?
Os imports estao organizados conforme convencao da linguagem?
Algum codigo reimplementa algo que ja existe no framework ou em bibliotecas ja utilizadas no projeto?
Existem logs de debug ou prints que deveriam ser removidos antes de ir para producao?
Existem comentarios TODO, FIXME, HACK ou XXX esquecidos que indicam debito tecnico?
Existe codigo comentado abandonado que deveria ser removido?
Existem numeros ou strings "magicos" espalhados no codigo que deveriam ser constantes nomeadas?
Os nomes de variaveis, funcoes e classes sao claros e seguem a convencao do projeto?
A estrutura de pastas segue um padrao logico e consistente?


Passo 7 — Features Inseguras
Analise as funcionalidades da aplicacao que podem ter vulnerabilidades de seguranca.
Formularios e inputs do usuario:

Os dados enviados pelo usuario sao validados e sanitizados antes de serem processados?
Existe protecao contra injecao de SQL, XSS, e outros ataques de injecao?
Uploads de arquivo validam tipo, tamanho e conteudo? Executaveis e scripts sao rejeitados?
Nomes de arquivo sao sanitizados para evitar path traversal?

Integracao com servicos externos:

Chamadas a URLs configuradas pelo usuario validam que nao apontam para enderecos internos (protecao contra SSRF)?
Headers e parametros sao validados para evitar injecao?
Respostas de APIs externas sao tratadas antes de serem usadas na aplicacao?

Autenticacao e sessoes:

Tokens de acesso sao armazenados com criptografia adequada?
Sessoes expiram apos periodo de inatividade?
Existe protecao contra fixacao de sessao e roubo de token?
Senhas sao armazenadas com hash seguro (bcrypt, argon2)?

Webhooks e callbacks:

Webhooks recebidos validam a assinatura de origem?
Existe protecao contra replay attack?
Os handlers sao idempotentes (processar o mesmo evento duas vezes nao causa problema)?

Componentes embedaveis ou publicos:

Existem restricoes de dominio para evitar uso indevido?
Conteudo renderizado e sanitizado contra XSS?
Existe rate limiting para evitar abuso?

Inteligencia Artificial (se aplicavel):

Prompts do sistema estao protegidos contra prompt injection via entrada do usuario?
Existe protecao contra vazamento do prompt do sistema?
O usuario consegue forcar o modelo a executar acoes que nao deveria?

Passo 8 - Features que podem atrapalhar a performance
Codigos bloqueantes que podem travar o servidor em uso massivo, ou escalavel. Qualquer feature que pode bloquear eventos nos ervidor e que isso cause o bloqueio total ou parcial do servidor. 



Passo 9 — Gerar Relatorio Final
Apos completar todos os passos acima, gere um relatorio consolidado com a seguinte estrutura:
Comece com um Sumario Executivo contendo a contagem de findings por severidade (quantos Criticos, Altos, Medios e Baixos foram encontrados).
Depois liste cada finding individualmente contendo:





Severidade e um ID sequencial (exemplo: CRITICO-001)
Titulo descritivo do problema
Qual categoria da auditoria (Passo 1 a 8)
Quais arquivos sao afetados
Descricao clara do problema encontrado
Qual o impacto se esse problema for explorado ou nao corrigido
Recomendacao de como corrigir, descrita em texto
Estimativa de esforco para corrigir (Baixo, Medio ou Alto)

Finalize construindo um Artefato "Implementation Plan" e um "task.md" para analise do usuário. 