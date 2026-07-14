# INFOCAP / CorpAPI — MAPA DE NAVEGAÇÃO (canônico)

> Descobertas validadas AO VIVO em 14/07/2026 (credenciais API RESULTA + AUTOFLEET).
> Para TODOS os agentes e devs. Ingerir no RAG global (`global_autobrokers`) quando
> a ingestão ligar — os agentes devem "saber navegar" por aqui.
> Base: `https://api.corpnuvem.com` · Auth: `POST /login {email, senha, aplicacao}` →
> campo `token` na resposta (usar cru no header `Authorization`, sem "Bearer").

## ✅ ACESSÍVEL com o perfil atual

| Endpoint | Para quê | Formato-chave |
|---|---|---|
| `GET /cliente_cpf?cpf_cnpj=&codfil=1` | Cliente por CPF | `{cliente:[{codigo, nome, telefone, email, enderecos:[{logradouro, numero, complemento, bairro, cep, cidade, estado}]}]}` |
| `GET /lista_clientes?texto=` | Busca por nome | `{clientes:[{codigo, nome, ddd, numero}]}` |
| `GET /cliente_ligacoes?codigo=` | TODAS as apólices do cliente | `{documentos:{documentos:[{nosnum, codfil, tipdoc(A=apólice), seguradora(ALLI/ZURI/TMAR...), ramo(AUTO/RESI/VIND...), numapo, inivig, fimvig(dd/mm/yyyy), cancelado(T/F), sin_situacao, renovacao_situacao}]}}` |
| `GET /documentos?texto=` | Apólice por número | idem acima |
| `GET /documento?nosnum=&codfil=` | Detalhe FINANCEIRO da apólice | prêmios (preliq/pretot/prepri), parcelas (numpar), vencimento, forma_pag, datas — **NÃO tem veículo** |
| `GET /itens?nosnum=&codfil=` | **⭐ O VEÍCULO vive AQUI** | placa, modelo/descrição, chassi, FIPE (só ramos AUTO/FROT) |
| `GET /cotacoes?codfil=1` | Cotações em aberto | `{cotacoes:[{codigo, codcli, cliente, status, prioridade, ...}]}` — pipeline comercial! |
| `GET /atendimentos?codfil=1` | Histórico de atendimentos/tarefas | 2.355 registros na Resulta — mina de ouro p/ diagnóstico operacional |
| `GET /seguradoras` | Tabela de cias (61) | `{seguradoras:[{codigo, nome, abreviatura}]}` — decodifica ALLI/ZURI/TMAR |
| `GET /ramos` | Tabela de ramos (50) | decodifica AUTO/RESI/VIND/CAPI/MOB... |

**Códigos já decodificados:** ALLI=Allianz, ZURI=Zurich, PORT=Porto, AZUL, BRAD=Bradesco, TOKI/TMAR=Tokio, YELU/LIBE=Yelum, MAPF/MAP=Mapfre, HDI, ALFA, SULA, SUHA=Suhai, SOMP, ITAU, SURA, YOUS=Youse · AUTO, RESI=residencial, VIND/VIDA=vida, EMPR, COND, FROT=frota, SAUD, CAPI, MOB.

## 🔒 NEGADO (403) com o perfil atual — pedir liberação à corretora

**Financeiro completo** (o bloco inteiro): `/parcelas`, `/comissao`, `/comissoes`, `/financeiro`, `/titulos`, `/contas_receber`, `/contas_pagar`, `/fluxo_caixa`, `/faturamento`.
**Gestão**: `/vendedores`, `/usuarios`, `/propostas`, `/sinistro`, `/endossos`, `/tarefas`, `/agenda`, `/cias`, `/filiais`.

> As permissões são flags do perfil de API (visíveis no login: p500/p501/...=T). A
> corretora libera no cadastro do usuário de API dentro do InfoCap.

## O que dá para fazer HOJE vs o que destrava com a liberação

**HOJE:** ficha completa do cliente e carteira (apólices, vigências → calendário de RENOVAÇÕES = pipeline), veículos com placa, pipeline de cotações, histórico de atendimentos, twin comercial básico.
**COM financeiro liberado:** análise de comissões por seguradora/ramo (as CONDIÇÕES COMERCIAIS da SPEC-037!), fluxo de caixa, inadimplência, rentabilidade por produto, relatórios financeiros e propostas tributárias do Decision Harness.

## Regras para agentes
- Sempre via a FERRAMENTA InfoCap (nunca chamadas cruas no chat); dados de cliente NUNCA vão ao RAG.
- `cancelado=T` e `fimvig` vencida = apólice inválida para qualquer fluxo.
- A "seguradora" da apólice é a EMISSORA (decide canal de acionamento — ver Registro de Seguradoras).
