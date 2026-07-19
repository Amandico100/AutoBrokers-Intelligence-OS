# InfoCap / CorpAPI — Mapa de navegação (como consultar o sistema da corretora)

Guia canônico de navegação no InfoCap (ERP da corretora, CorpAPI). Os agentes
usam SEMPRE a ferramenta InfoCap — nunca chamadas cruas. Dados de cliente NUNCA
vão ao conhecimento global; este mapa é ESTRUTURA de navegação, sem dados.

## Endpoints acessíveis e para que servem

- Cliente por CPF: `GET /cliente_cpf?cpf_cnpj=&codfil=1` — retorna cliente com
  código, nome, telefone, email e endereços completos (logradouro, número,
  complemento, bairro, cep, cidade, estado).
- Busca por nome: `GET /lista_clientes?texto=` — retorna clientes com código,
  nome, ddd e número de telefone.
- TODAS as apólices do cliente: `GET /cliente_ligacoes?codigo=` — lista de
  documentos com: nosnum (id técnico), codfil, tipdoc (A = apólice), seguradora
  (código ALLI/ZURI/TMAR...), ramo (AUTO/RESI/VIND...), numapo (número humano
  da apólice), inivig e fimvig (vigência, dd/mm/yyyy), cancelado (T/F),
  sin_situacao, renovacao_situacao.
- Apólice por número: `GET /documentos?texto=` — mesmo formato acima.
- Detalhe FINANCEIRO da apólice: `GET /documento?nosnum=&codfil=` — prêmios
  (preliq/pretot/prepri), parcelas (numpar), vencimento, forma de pagamento e
  datas. IMPORTANTE: o /documento NÃO tem os dados do veículo.
- O VEÍCULO vive no `GET /itens?nosnum=&codfil=` — placa, modelo/descrição,
  chassi e FIPE (só nos ramos AUTO/FROT). Para achar a placa de um cliente:
  CPF → cliente_ligacoes → apólice AUTO vigente → /itens.
- Cotações em aberto: `GET /cotacoes?codfil=1` — pipeline comercial (código,
  cliente, status, prioridade).
- Histórico de atendimentos/tarefas: `GET /atendimentos?codfil=1` — registros
  operacionais por cliente desde 2014 (tipo, datas, descrição, responsável).
- Tabela de seguradoras: `GET /seguradoras` (61 cias) — decodifica os códigos.
- Tabela de ramos: `GET /ramos` (50 ramos) — decodifica AUTO/RESI/VIND etc.

## Códigos mais comuns (decodificação)

Seguradoras: ALLI=Allianz, ZURI=Zurich, PORT=Porto, AZUL=Azul, BRAD=Bradesco,
TOKI/TMAR=Tokio Marine, YELU/LIBE=Yelum (ex-Liberty), MAPF/MAP=Mapfre, HDI=HDI,
ALFA=Alfa, SULA=SulAmérica, SUHA=Suhai, SOMP=Sompo, ITAU=Itaú, SURA=Sura,
YOUS=Youse.
Ramos: AUTO=automóvel, RESI=residencial, VIND/VIDA=vida, EMPR=empresarial,
COND=condomínio, FROT=frota, SAUD=saúde, CAPI=capitalização, MOB=celular/mobile.

## Endpoints NEGADOS no perfil padrão (pedir liberação à corretora)

Financeiro completo: /parcelas, /comissao, /comissoes, /financeiro, /titulos,
/contas_receber, /contas_pagar, /fluxo_caixa, /faturamento.
Gestão: /vendedores, /usuarios, /propostas, /sinistro, /endossos, /tarefas,
/agenda, /cias, /filiais.
As permissões são flags do perfil de API do usuário InfoCap da corretora.

## Regras de uso para os agentes

- Sempre via a FERRAMENTA InfoCap; nunca montar chamadas manualmente no chat.
- Dado de cliente NUNCA vai ao conhecimento global nem é exposto a terceiros.
- Apólice com cancelado=T ou fimvig vencida é INVÁLIDA para qualquer fluxo —
  não oferecer, não acionar.
- numapo é o número humano (o que o cliente conhece); nosnum é id técnico
  interno — nunca mostrar nosnum ao cliente.
- A "seguradora" da apólice é a EMISSORA — é ela que decide o canal de
  acionamento de assistência.
- Vigências (fimvig) formam o calendário de RENOVAÇÕES da corretora — a venda
  mais barata que existe (pipeline garantido).
