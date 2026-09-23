# RESEARCH PACK — EXTRA-002 · Investigação e prova do Agger (Aggilizador)

**Versão 1.0 · 22/09/2026 · MODO INVESTIGAÇÃO (protocolo §8)** · baseline `origin/main` = `d8510df` (📊 `git rev-list --count HEAD..origin/main` → 0)
**O que é:** a evidência sanitizada que sustenta a proposta `SPEC-EXTRA-002-investigacao-prova-agger.md` e as propostas EXTRA-003/004/007.
**O que não é:** nada aqui é contrato do Agger. Tudo que vem da rede é **"endpoint interno observado pela interface"** (classe B da §5) — não é API oficial.

> 🔴 **Regra de sanitização aplicada:** nenhum CPF, CNPJ de segurado, placa, nome de segurado, token, senha, e-mail de usuário ou id de corretora aparece aqui. Formas de payload são dadas por **nome de campo e tipo**. Os arquivos brutos ficam em `docs/intake/MULTICALCULO AGGER/` (📊 `git check-ignore -v` → `.gitignore:113: docs/intake/`) e **não sobem ao Git**.

Legenda: 📊 medido (com comando/arquivo) · 💭 inferido · ❓ não sabemos · 🧪 testado

---

## 1. Inventário do intake (`docs/intake/MULTICALCULO AGGER/`)

📊 `find . -type f ! -iname "*.png" … -printf "%s %p"` em 22/09/2026. 166 imagens (logos de seguradora) omitidas.

| pasta | arquivo | tamanho | o que prova | segredo/PII |
|---|---|---:|---|---|
| RENOVAÇÃO 1 | `aggilizador.com.br.har` | 49,1 MB | login, formulário, **cálculo de renovação PF**, 28 pollings | 🔴 **SIM** — senhas de 17 portais de seguradora em `calculos[]`, token, CPF, placa |
| RENOVAÇÃO 1 | `Aggilizador TELA 1/2/3 *.html` | 0,9–1,3 MB | DOM salvo das 3 telas | PII |
| RENOVAÇÃO 1 | `BRADESCO AUTO.pdf`, `PDF EXEMPLO DE CALCULO DA HDI.pdf`, `INFORMAÇÕES DA APOLICE.txt` | 2,7 MB / 45 KB / 7 KB | a apólice/cálculo atual (o "seguro atual") | PII |
| RENOVAÇÃO 2 | `aggilizador.com.br.har` | 55,3 MB | **cálculo de renovação PJ**, 28 pollings | 🔴 **SIM** (idem) |
| RENOVAÇÃO 2 | HTMLs das telas (incl. "PACOTE ALTERNATIVO"), `ZURICH AUTO.pdf`, `.txt` | — | idem | PII |
| COTAÇÃO 1 / 2 | `TOKIO AUTO.pdf`, `HDI AUTO.pdf`, `.txt` | 304 / 192 KB | cálculo de **seguro novo** (só o PDF da seguradora; **sem HAR**) | PII |
| GERAL | `aggilizador.com.br TELA DE SEGURADORAS.har` | 35,6 MB | tela de configuração das credenciais das seguradoras | 🔴 **SIM** |
| GERAL | `Aggilizador TELA CREDENCIAIS.html` | 1,6 MB | DOM da tela de credenciais | 🔴 |
| GERAL | `MODELO DE APRESENTAÇÃO COM 3 OPÇÕES.pdf` | 150 KB | **a apresentação que a corretora envia hoje** (referência observada) | PII |

🔴 **Achado de segurança sobre o próprio intake:** 📊 o payload de `POST /calculo/calcularV2` carrega, por seguradora, `login`, `senha`, `loginWs`, `senhaWs` (formas `str11`, `str16`…). O Aggilizador entrega ao navegador as credenciais dos portais das seguradoras.

🔴 📊 **E não só no disparo — nas RESPOSTAS também:** as chaves `login/senha/loginWs/senhaWs`, com valor, aparecem nas respostas de `cfg/seguradora/config`, `calculo/seguradoras`, `cotacao/versoes/{id}`, `negocio/{id}` (login/senha) e em **todas as 28** respostas de polling `cotacao/calculos/{id}/{v}`, além do corpo do `POST calcularV2` (📊 varredura de chaves nos 2 HARs, 22/09). Qualquer integração recebe as senhas de ~15 portais **a cada consulta** — o contrato de redação está na EXTRA-003 §3.5. **Consequência para nós:** os três HARs são material secreto; não podem ser anexados, enviados a terceiros nem copiados para fora da pasta ignorada. Registrado como pendência de higiene (§12).

⚠️ **Lacuna do intake:** não há HAR de **cotação nova** — só os PDFs. A diferença cotação × renovação (§6) vem do formulário e dos campos, não de uma captura de seguro novo.

---

## 2. Arquitetura do Aggilizador — o que a rede mostra

📊 Script `har_map.py` (scratchpad da sessão; ignora estáticos e telemetria) sobre os 3 HARs. Os mesmos números saem do laboratório da casa: `python backend/scripts/portal_factory.py lab api-infer` (RENOVAÇÃO 1 + 2) → **34 endpoints, 5 de escrita, confiança média 67/100** (laudo F1a §8).

```text
navegador (SPA Angular, aggilizador.com.br)
   │  Authorization: <token>   (📊 pré-voos CORS pedem "authorization"; 0 cookies em 577 requisições)
   ├── api-prod.aggilizador.com.br   usuário, login, config de seguradoras, cliente, DISPARO do cálculo
   ├── api.multicalculo.net          motor: negócio, versões, placa, FIPE, CEP, POLLING dos resultados
   ├── api.aggilizador.com.br        tabelas legadas (Auto/Data, Travel/Data)
   └── json.agger.com.br             comunicados, leads (JSON estático)
seguradoras ← chamadas pelo BACKEND do Agger (o navegador nunca fala com seguradora)
```

### 2.1 Endpoints por etapa (📊 RENOVAÇÃO 1, tempo relativo ao 1º login)

| etapa | método e rota | observado |
|---|---|---|
| login | `POST api-prod…/usuario/login` body `{email, senha}` | 201, ~1,9 s |
| login que derruba sessão | `POST …/usuario/login` body `{email, senha, derrubaSessao}` | 201 — 🔴 **sessão única por usuário** |
| token de documentos | `POST …/usuario/login/pdocs` | 201, token próprio de 3 h |
| lista de negócios (tela inicial) | `GET api.multicalculo.net/calculo/negocio/busca/v2?modo,page,limit,ramos,periodo,sortOrder` | 40 segurados/página, cada um com `negocios[]` (status, vigência, placa, modelo) |
| status das seguradoras | `GET …/app/seguradoraStatus/` | 56 seguradoras × status por ramo/funcionalidade (`renovationStatus`, `proposalStatus`…) |
| seguradoras da corretora | `GET api-prod…/calculo/seguradoras` | 15 configuradas (com credenciais — 🔴) |
| catálogo "seguradora anterior" | `GET …/calculo/seguradorasRenovacao` | 69 seguradoras × ramos |
| cliente por CPF/CNPJ | `GET api-prod…/cadastros/cliente?cpfCnpj,simplificado,apenasBuscaLocal` | nome, sexo, nascimento, estado civil, `externo` |
| cotado recentemente? | `GET …/calculo/seguradoCotadoRecentemente?cpfCnpj,ramo` | lista de cálculos anteriores (o modal "CPF já cotado") |
| placa → veículo | `GET …/calculo/buscaPlaca?placa` | FIPE, ano fab/mod, chassi, modelo (~1,7 s) |
| chassi → veículo | `GET …/calculo/chassiDecoder` | (RENOVAÇÃO 2) |
| FIPE | `GET …/calculo/fipeModelo?ano,fipe,zero` | valores FIPE por mês |
| CEP | `GET …/calculo/cep?cep` | logradouro, cidade, UF |
| **negócio anterior** | `GET …/calculo/negocio/{uuid}` | 🔴 **o formulário INTEIRO da cotação anterior** (segurado, veículo, condutor, questionário, dados de renovação) |
| versões | `GET …/calculo/cotacao/versoes/{uuid}` | até 185 KB — histórico de versões e resultados |
| **disparo** | `POST api-prod…/calculo/calcularV2` body `{cotacao, negocio:{id}, correlationId}` | **201 em 1,5–1,9 s**, resposta `{idIntegracao, versao}` (66 bytes) |
| **polling** | `GET …/calculo/cotacao/calculos/{idIntegracao}/{versao}` | 📊 **28 consultas** em cada HAR, até 138 KB |

### 2.2 Autenticação e sessão (📊, só nomes de claims e durações)

| fato | medida |
|---|---|
| esquema | cabeçalho `Authorization`; 📊 CORS `access-control-request-headers: authorization` em 62/65 pré-voos (RENOV. 1) |
| token de usuário | JWT HS256, **validade 8,0 h** (`expires − iat`) — claims: `corretoraId`, `qtdeLicenca`, `licenca`, `expirationDate`, `senhaRequerAlteracao`, `diasParaExpirarSenha`… |
| token de documentos (`pdocs`) | JWT HS256, **3,0 h**, claim `dataLimiteCalculo` |
| sessão | 🔴 **uma por usuário**: o segundo login carrega `derrubaSessao=<id da sessão anterior>` |
| licenças | 💭 `qtdeLicenca` + `products[].licenses` sugerem cobrança **por usuário** |
| senha | 💭 `diasParaExpirarSenha`, `senhaRequerAlteracao` → a senha **expira**; um robô precisa de rotina de troca |
| captcha no login | 📊 nenhum campo de captcha no body do login |
| proteção anti-robô | 📊 o site carrega o sensor **Akamai** (`/akam/13/…`, `akstat.io`). ❓ se a API barra chamadas de servidor. **Não investigamos contorno e não se contorna** — ver proposta §3 |

### 2.3 O cálculo é ASSÍNCRONO — a linha do tempo real

📊 `har_poll2.py` sobre os dois HARs; `tempoResposta` é o campo do próprio Agger, em ms.

**RENOVAÇÃO 1 (PF, 17 seguradoras, 18/09 ~20h38 BRT):**
```text
  5 s   Sura ✗ (valor do veículo abaixo do mínimo)   Tokio ✗ (sem permissão)
 13 s   Mapfre ✓  Youse ✓  Ezze ✓  Azul Assinatura ✓  Darwin ✗ (não oferece)
 19 s   HDI ✓
 24 s   Allianz ✓
 30 s   Aliro ✓  Liberty ✓  Mitsui ✓  Azul ✓  Porto ✓  Itaú ✗ (oferta não disponível ao parceiro)
 36 s   Zurich ✗ (login ou senha incorreta)          → 16 de 17 decididas
420 s   Bradesco ✗ (instabilidade da seguradora)     → fechamento (💭 corte do Agger ou timeout da seguradora?)
```
**RENOVAÇÃO 2 (PJ, 17 seguradoras, 18/09 ~21h14 BRT):**
```text
 41 s Allianz ✓ · 68 s Mapfre ✓ · 84 s Sura ✗ · 95 s Zurich ✗, Tokio ✓ · 106 s Porto, Mitsui, Itaú, HDI, Azul ✓
127 s Liberty ✓, Darwin ✗ · 168 s Aliro ✓ · 229 s Ezze ✓ · 291 s Azul Assinatura ✗
413 s Bradesco ✗, Youse ✗   → fechamento (💭 corte do Agger ou timeout da seguradora?)
```

| métrica (n = 2 cálculos) | RENOV. 1 | RENOV. 2 |
|---|---:|---:|
| 1ª resposta | 5 s | 41 s |
| ofertas válidas | 11 | 11 |
| recusas/erros | 6 | 6 |
| todas as **ofertas válidas** recebidas | **30 s** | **229 s** |
| conjunto fechado (último item decidido) | **420 s** | **413 s** |

💭 **Leitura (hipótese, não medição):** o fechamento em 413–420 s *parece* um **corte em ~7 min** — mas com **n = 2** e o **mesmo confundidor** nos dois casos (o último a fechar foi sempre o Bradesco instável, com a Youse junto na RENOV. 2), é igualmente compatível com um **timeout por seguradora**, e não com um teto global do Agger. A cotação útil fica pronta em 📊 0,5–4 min; o resto é espera por seguradora lenta ou fora. ❓ Com n = 2 **não há p50/p95** — o E3 da proposta mede, com cálculos **sem** seguradora instável como linha de controle.

### 2.4 O resultado já vem PADRONIZADO pelo Agger

📊 `har_result.py`, último polling da RENOVAÇÃO 1. Cada seguradora (`calculos[i]`) traz `retorno`, `retornoErro`, `erros[]`, `alertas[]`, `tempoResposta`, `dataHoraEnvio/Retorno`, `premio`, `valorFranquia`, `packageType` e `resultados[]`:

```text
resultados[] = {
  principal, selected, packageType, identificacao, codigoIdentificacaoSeg,
  nroCalculo,                     ← número do cálculo NA SEGURADORA
  premio (float), premioMensal, franquia, renovacaoGarantida,
  alertas[], erros[], observacoes[],
  coberturas: { casco, percComissao, percDesconto, assist24hs (texto), vidros (texto),
                carroReserva (texto), isDanosMateriais, isDanosCorporais, isDanosMorais,
                isAppMorte, isAppInvalidez, despesasExtra, isBlindagemValor, reparoRapido,
                protecaoPneuRodas, tipoFranquia, franquiaPadronizado,
                franquiaPadronizadoPercentual, tipo, tipoPadronizado, modeloSelecionado },
  franquias {},
  parcelamentos[] = { parcelas, premioPrimeiraParc, premioDemaisParc, tipoPag, valorIof }  (📊 32 opções na Mapfre)
  pathPdf, pdfFileNameAgger       ← o PDF OFICIAL da seguradora
}
```
📊 Quantidade de `resultados` por seguradora: Allianz 6 · Ezze 3 · Azul 3 · Itaú 2 · Azul Assinatura 2 · demais 1. As abas da tela ("Pacotes", "Pacotes alternativos", "Pacotes por assinatura") são o `packageType`.

**As seis famílias de erro observadas** (texto da seguradora, via Agger):

| erro observado | família | quem resolve | tratar como |
|---|---|---|---|
| "Login ou senha incorreta" (Zurich) | CONFIGURAÇÃO | a corretora, no Aggilizador | alerta de conexão, não "sem oferta" |
| "Usuário não possui acesso à funcionalidade" (Tokio) | CONFIGURAÇÃO | a corretora, na seguradora | idem |
| "Oferta não disponibilizada ao Parceiro" (Itaú) | COMERCIAL | ninguém (acordo) | "não disponível" |
| "valor do veículo abaixo do limite mínimo" (Sura) | ACEITAÇÃO | ninguém | recusa legítima, com motivo |
| "Não oferecemos seguro para os dados enviados" (Darwin) | ACEITAÇÃO | ninguém | recusa legítima |
| "instabilidade no momento" (Bradesco) | TRANSITÓRIO | o tempo | **tentar de novo** mais tarde |

💭 Isto é o que torna o **"às 7h sem mentira verde"** possível: o produto sabe dizer *por que* cada seguradora não entrou.

---

## 3. O formulário — o que o cálculo realmente pede

📊 Campos do `cotacao` enviado em `calcularV2`, RENOV. 1 (PF) × RENOV. 2 (PJ), **presença** apenas (script de comparação na sessão). ~45 campos de negócio.

| grupo | campos | PF | PJ |
|---|---|:-:|:-:|
| segurado | nome, tipoPessoa, cpfCnpj, cep, logradouro, bairro, cidade, uf | ✓ | ✓ |
| segurado PF | dataNasc, sexo, estadoCivil | ✓ | — |
| veículo | placa, chassi, fipe, fabricante, anoFab, anoMod, combustível, descricao, zeroKm, valReferenciado, pctAjuste, tipoIsencao | ✓ | ✓ |
| **questionário de risco** | **cepPernoite, garagemResidencia, garagemTrabalho, garagemEstudo, tpUso, periodoUso, kmAnual, rastreador, antiFurto**, blindado, alienado, kitGas, jovemCondutor | ✓ | ✓ |
| **condutor principal** | nome, cpf, dataNasc, sexo, estadoCivil, **dataPrimHabil, tempoHabilitacao, relacComSegurado, tpResidencia**, principal | ✓ | ✓ |
| **renovação** | `renovacao=true`, **bonusAnterior**, **sinistrosAnterior**, **numeroRenovacao** (nº da apólice), **seguradoraAnteriorId**, **vigFimAnterior**, `CI` (nulo nos dois), `renovacaoGarantida` | ✓ | ✓ |
| cálculo | vigenciaIni, vigenciaFim, tpCobertura, ramo, negocioId, versao, correlationId | ✓ | ✓ |
| perfil por seguradora | `calculos[]`: IS de DM/DC/DMorais/APP, franquia, carro reserva, vidros, assistência, comissão, desconto (**configuração da corretora**, vem pronta do Agger) | ✓ | ✓ |

💭 **A descoberta que decide a EXTRA-003:** o questionário de risco e o condutor **não existem na InfoCap** (laudo F1b §9; laudo F1a §9: `grep -rni "classe_bonus\|codigo_identificacao"` → 0; CEP de pernoite e condutor → 0). Eles existem **na cotação do ano anterior dentro do Agger** (`GET negocio/{uuid}`). Logo:

```text
renovação AUTOMÁTICA  = cotação do ano anterior no Agger  +  datas/bônus/apólice da InfoCap
sem cotação anterior  = "precisa confirmar dado" (nunca "pronta")
```

---

## 4. O AutoBrokers hoje — o que existe e o que falta (laudos F1a e F1b)

Laudos completos nos arquivos de trabalho da sessão; os pontos que mudam o desenho, com a evidência:

| peça | estado | evidência |
|---|---|---|
| código de cotação/multicálculo | ❌ **inexistente** | 📊 `grep -rli "agger\|aggilizador\|multic"` em `backend/app backend/portal_worker app lib` → só comentários-reserva (`providers/policy_data_provider.py:548,823`) e catálogo de frontend |
| Auxiliar `renovacao-maxima` | CATÁLOGO (`coming_soon`, 0 instalações, `runtime none`) | 📊 `auxiliary_templates`; seed `supabase/migrations/20260802_02_spec064_seed_catalogo.sql:294-306`; o próprio template diz faltar *"espelho da carteira com vigências e valor de referência do bem"* |
| Skill/Capability/Tool de cotação | ❌ | 📊 21 skills, 38 capabilities, 32 tool_definitions — nenhuma com renew/quote/cotac |
| Agger em `portals`/`connector_templates` | ❌ | 📊 17 portais, 11 templates de conector; `quiver` existe com 0 conexões |
| lista de renovações | ✅ EXERCITADO | `comercial/fonte_infocap.py:547 carteira_a_vencer` → `/renovacoes` da InfoCap; template `renewals.radar` (📊 15 artifacts) |
| volume | 📊 Resulta: 297 renovações em 90 dias (≈3,3/dia, todos os ramos, radar de 18/08) · censo 2025: Resulta 3.536, AutoFleet 2.654 · ❓ fatia AUTO e pico diário | laudo F1b §9 |
| preenchimento InfoCap `/renovacoes` | 📊 fim de vigência, nº apólice, seguradora, ramo, situação de renovação 100% · CPF/CNPJ 99,2% · elo com apólice anterior 57,8% (n = 3.536) | laudo F1b §9 |
| Work OS: espera durável | ❌ | todo polling é `sleep` em processo (`portal_tool.py:780-822`, `billing_collection.py:1148-1164`, `gateway.py:140` — 📊 `self._dormir = dormir or time.sleep`); `work_waits` é espera de **conversa** (📊 `20260826_05_spec086_blocoB_work_waits.sql:68` `conversation_id NOT NULL`, `:104` CHECK de 3 kinds, `:121` FK `(conversation_id, company_id)`) |
| Work OS: retomada | ⚠️ só no papel | 📊 `checkpoint_id` 0/13.888; `executar_passo` re-executa passo já concluído (`workflows.py:111-140`) |
| Work OS: retry | ⚠️ | `retry_scheduled` sem re-enfileirador; retry manual sem outbox (`api/work_runs.py:180-239`) |
| agenda | ✅ | `routine_engine` + `routines.config.workflow` lido por `bridge_rotina` (`workflows.py:333-347`); 📊 `WORK_RUNS_ROUTINE_BRIDGE=1` no env de produção |
| credencial por corretora | ✅ molde | `tenant_connections` + `encryption_service` (InfoCap: 7 conexões, 3 corretoras) |
| Portal Worker | ✅ mas **sempre abre Chromium** | `worker.py:1336-1395`; API-first de vidros usa `page.evaluate(fetch)` — errado para uma API com token |
| lock por credencial | ✅ | `LeaseDePortal` Redis por `(company_id, portal_key, account_label)` (`leases.py:256`) — o molde para "uma sessão por usuário Agger" |
| Artifact Hub + marca | ✅ | `services/artifacts/service.py`; snapshot da marca no render (`render.py:67-79`); 📊 209 renders, **todos HTML** |
| link público | IMPLEMENTADO, nunca usado | `/r/[token]`, expiração, revogação; 📊 `artifact_shares` = 0 |
| white-label | ⚠️ gravado e **não lido** | `white_label` sem leitor; o selo da plataforma sairia (`blocks.py:387-389`) |
| marca configurada | 📊 1 de 3 corretoras | `brand_profiles` |
| Approval antes de enviar | ❌ na prática | 📊 `validar_para_execucao`/`marcar_executada` 0 chamadores; `decidir()` não retoma o run |
| laboratório SPEC-077 | ✅ útil (nota 82) | aprende o Agger do HAR; não modela Bearer nem polling; `examples` **não redigidos** |

---

## 5. As opções de integração, medidas

| | caminho | nota | por quê |
|---|---|:-:|---|
| **C** | **API oficial / acordo de integração com a Agger** | **92** (se existir) | contrato, suporte, sem risco de bloqueio; ❓ existência e preço — é pergunta **comercial** |
| **B** | endpoints que a própria interface usa, **com anuência escrita da Agger** e **usuário robô dedicado** | **84** | 📊 a interface é 100 % JSON: disparo + polling, resultado padronizado com PDF; sem navegador, custo ~0. Contra: não é contrato (pode mudar), Akamai ❓ |
| **A** | navegador (Portal Worker) preenchendo a tela como uma pessoa | **58** | usa peça existente; contra: 1 Chromium preso até 7 min por cálculo, frágil a mudança de tela, 45 campos por DOM |
| **E** | híbrido: C/B como motor + portal da seguradora só onde o Agger falha | **70** (futuro) | cobre seguradora que o Agger não calcula; custo de 1 journey por seguradora |
| **D** | cotar direto nos portais das 17 seguradoras | **25** | 17 formulários de 40+ campos, 17 normalizações; é refazer o Agger |

🔴 **B sem anuência não é opção** que esta investigação recomenda: além do risco contratual, o site tem proteção anti-robô, e contornar proteção de terceiro está fora do que fazemos (proposta §3).

💭 **O ponto que tira a pressão da escolha:** o desenho da EXTRA-003 põe o Agger **atrás de uma porta** (`QuoteProvider`, espelho do `PolicyDataProvider`). B e C são o **mesmo adaptador** com transporte diferente; A é o mesmo contrato com um executor diferente. A decisão comercial não trava a engenharia.

---

## 6. Cotação nova × renovação (📊 do formulário; ❓ sem HAR de seguro novo)

| aspecto | cotação nova | renovação |
|---|---|---|
| flag | `renovacao=false` | `renovacao=true` |
| dados do segurado | digitados ou `cadastros/cliente` | idem + negócio anterior |
| questionário/condutor | **perguntar** | **reaproveitar** do negócio anterior, confirmar se mudou |
| bônus, sinistros, apólice, seguradora anterior, fim anterior | não se aplica | **obrigatórios** — InfoCap tem apólice/seguradora/vigência; bônus ❓ taxa |
| "Item calculado recentemente" | — | 📊 o Agger **incorpora** o cálculo novo como versão do negócio existente |
| "renovação garantida" | — | campo existe por resultado (`renovacaoGarantida`) |

💭 O Agger **não tem um botão "renovar" que faça tudo** — tem uma cotação marcada como renovação, que reaproveita o negócio anterior. ❓ A permissão `RENOVACOES_PENDENTES` existe no login com `oculto` — há uma tela de renovações pendentes não contratada/escondida; investigar na prova ao vivo.

---

## 7. Referência observada — como a corretora entrega hoje

📊 `GERAL/MODELO DE APRESENTAÇÃO COM 3 OPÇÕES.pdf` (2 páginas): cabeçalho com logo e endereço da corretora · cliente, condutor, CEP de pernoite, uso · veículo · **tabela com 3 colunas** (3 opções, a mesma seguradora em variações) · coberturas (casco %FIPE, DM, DC, APP, danos morais) · cláusulas (assistência, vidros, carro reserva, guincho) · formas de pagamento (à vista, 4x, 6x, 10x) · franquias · observações (**"validade de 05 dias"**, regras de condutor, CEP de pernoite e uso). 📊 contém um erro de digitação humano no nome da seguradora numa das colunas.
📊 Mensagem de WhatsApp de apoio (anexo do Founder): um texto com emojis resumindo casco, DM, DC, danos morais, APP, vidros, assistência, **franquia reduzida × super reduzida** e parcela.

💭 **O que isso ensina:** a corretora já compara **variações de franquia e de limites**, não só seguradoras. A apresentação WOW precisa mostrar o **seguro atual** ao lado (o PDF de hoje não mostra), e a validade curta obriga a registrar **"calculado em … válido até …"** em cada preço.

---

## 8. O que ficou por medir (❓) e o experimento que decide

| ❓ | experimento | onde |
|---|---|---|
| a API aceita chamada de servidor (Akamai)? | E1 — 1 login + 1 leitura com usuário robô, **com anuência da Agger** | proposta §4 |
| p50/p95 do cálculo | E3 — 10 renovações reais, horário noturno | proposta §4 |
| paralelismo por usuário (quantos cálculos simultâneos numa sessão) | E4 — 1, 2, 3 simultâneos, com linha de controle | proposta §4 |
| seguradoras respondem de madrugada? | E3 às 02h × 20h | proposta §4 |
| fatia AUTO e pico diário | E0 — `carteira_a_vencer` 365 dias por corretora, agrupado por ramo/dia (leitura InfoCap) | proposta §4 |
| taxa de preenchimento de bônus, CI, FIPE em `/itens` | E0 — amostra ≥ 50 apólices AUTO | proposta §4 |
| % de renovações com cotação anterior no Agger | E2 — cruzar CPF da lista com `seguradoCotadoRecentemente` | proposta §4 |
| licença por usuário robô: custo | pergunta comercial à Agger | caixa do Founder |

---

## 9. Referência externa (protocolo §7.3)

| URL | o que faz | o que MODELAMOS | o que REJEITAMOS | como o juiz inspeciona |
|---|---|---|---|---|
| https://aggilizador.com.br | o multicálculo em uso | o **contrato observado** de disparo+polling e o resultado padronizado | acoplar tela nossa ao JSON dele (vai atrás de porta) | abrir; conferir as abas Pacotes/Alternativos/Assinatura contra `packageType` |
| https://www.agger.com.br | o grupo dono do Aggilizador e da InfoCap | pedir **API/integração oficial** antes de depender de endpoint interno | presumir "mesma empresa = mesma API" | abrir; procurar área de parceiros/integração |
| https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm | LGPD | base legal e consentimento para o comparador público (EXTRA-007) | coletar dado de visitante sem finalidade declarada | art. 7º e 9º |
| `docs/intake/…/MODELO DE APRESENTAÇÃO COM 3 OPÇÕES.pdf` (interna, observada) | o que a corretora envia hoje | as seções e a validade | tabela sem o seguro atual; digitação manual | abrir o PDF |
| `backend/app/providers/policy_data_provider.py` (interna) | porta de apólice com adaptadores | o padrão **porta + adaptador + CampoComOrigem** para `QuoteProvider` | modelo novo paralelo de apólice | ler `:728-852` |

💭 A pesquisa externa sobre documentação pública do Agger e comparadores de mercado **não rodou nesta sessão** (interrompida). O juiz deve tratar a coluna "externa" como **incompleta** — pendência P-E002-06.

---

## 10. Achados fora do escopo, graves (entregues ao Founder)

1. 🔴 **Possível cruzamento de corretora** (laudo F1b): 📊 21/09 20:28 a conexão InfoCap da Resulta foi desconectada; 20:29 nasceu, **dentro da corretora Amandus**, uma conexão "InfoCap RESULTA"; desde 20:44 a Amandus fez 25 consultas de apólice e a Resulta 0. ❓ se é o canário da 001.8, feito de propósito. **Ninguém alterou nada nesta investigação.**
2. `research_tool` cria run com `source_type="research"`, proibido pelo CHECK do banco → 📊 0 runs `research.execute` na vida (laudo F1a §11.5).
3. `smith_worker._processar` sobrescreve `waiting_approval` com `completed` (💭 leitura, `smith_worker.py:385-393`).
4. 11 runs `queued` eternos e `retry_scheduled` sem re-enfileirador (📊 laudo F1a §11.1–2).
5. `time.sleep` bloqueante no Gateway de portal dentro de workflow async (`gateway.py:140`, usado em `:409`).

## 11. Ideias futuras (não entram na EXTRA-003)

| ideia | valor | esforço | depende de |
|---|:-:|:-:|---|
| alerta "sua renovação ficou X % mais cara" com a causa (bônus, FIPE, seguradora) | 90 | 30 | 003 |
| "cobertura reduzida" — a opção barata tira algo que o cliente tem hoje | 88 | 35 | 003 + apólice atual |
| ranking de risco de perda (preço subiu + sem contato + concorrente mais barato) | 80 | 50 | 003 + dados de fechamento |
| acompanhamento de aceite (proposta enviada → aberta → respondida) | 78 | 30 | link público |
| cross-sell na renovação (residencial, vida) | 70 | 45 | EXTRA-006 |
| reativação de quem não renovou no ano passado | 75 | 40 | EXTRA-005 |

## 12. Pendências de higiene deste pack

- **P-E002-HAR:** os 3 HARs do intake têm senhas de 17 portais de seguradora e tokens. Manter só na pasta ignorada; apagar quando a prova terminar; se alguma senha tiver circulado fora da máquina, a corretora deve trocá-la.
- **P-E002-LAB:** o `examples` do contrato candidato do laboratório SPEC-077 guarda valores observados sem redação — não versionar a saída do `lab api-infer` sobre estes HARs.
