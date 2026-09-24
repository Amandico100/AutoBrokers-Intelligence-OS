# SPEC-EXTRA-001.10.1 · A continuação do portal de vidros

> **SPEC escrita na execução** em 23/09/2026 sobre `4573a46` (não havia proposta: a fonte é o handoff §12 do
> relatório da EXTRA-001.10, a pendência **P-E00110-A11**, as **duas capturas novas de 21/09** e as respostas da
> atendente às 15 perguntas). Rito: PROTOCOLO AAA **v13 · O FIO**. 📊 medido · 💭 ilustrativo · ❓ desconhecido.

## 0. EXECUTION CARD

```
OUTCOME ..............  o robô RETOMA um atendimento já aberto (pelo token do portal, guardado cifrado), CONCLUI o
                        agendamento quando o portal abre agenda (loja + dia + hora confirmados pelo próprio portal) e
                        responde sozinho o que o portal pede depois do protocolo (prioridade, preferência de vistoria).
                        Parada que depende do segurado vira PERGUNTA + continuação; parada técnica vira nova tentativa.
                        Mão humana só quando o portal recusa o token (401) ou mostra tela nunca vista.
RISCO ................  8 = alcance 3 (segurado) + reversibilidade 3 (agendamento/pedido real) + frequência 2
SUPERFÍCIE ...........  2 (vários comportamentos, peça nova: a journey de continuação)
PISO APLICADO ........  §3.2 "qualquer coisa que ENVIE" (acionamento e agendamento reais) → CRÍTICO
NÍVEL ................  CRÍTICO · builders Opus xhigh · juiz ‖ red team · confirmação se houver blocker
O FIO ................  §2 · teste do fio: backend/tests/test_e001101_o_fio_da_continuacao.py
PARALELISMO REAL .....  2 builders, arquivos DISJUNTOS (§4): A = portal_worker/journeys/* · C = app/* + worker
UNIDADES .............  §3 (9)
COESÃO ...............  sessão durável + journey de continuação + agendamento + roteador ficam com A (mesmo contrato,
                        mesmo hub SessaoVidros); tool + coleta + mensagens + vigia + work_run ficam com C
TIME .................  2 builders ‖ → costura A↔C → juiz ‖ red team → conserto → confirmação → bateria → docs
REFERÊNCIA ...........  interna: tests/test_o_fio_do_portal_de_vidros.py (replay de borda sobre HAR real) · externa §8
GATES ................  §6 (G1–G12)
O ELO ................  "o robô consegue continuar PORQUE o token guardado ainda vale": A medido (a API só exige o
                        header token_autorizacao; CORS *), B medido (token de 21/09 → 401 em 23/09), B→A: a
                        continuação LÊ primeiro (GET /atendimentos) e só age com 200 — o 401 é o desfecho legível
FAIXA DE RELÓGIO .....  💭 6–10 h · teto 1,5× · agentes ≤ 24
```

## 1. BLOCO 0 — medido em 23/09/2026 (as capturas novas são as de 21/09; a 001.10 terminou em 21/09 03:18 UTC)

| # | fato 📊 | como foi medido | consequência |
|---|---|---|---|
| B0.1 | O HAR `YELUM LATARIA.har` tem **duas execuções**: [0–60] vidro lateral (atend. `…739`) e [61–113] lataria (`…795`) | `trafego.importar_har` → 114 chamadas à API | o replay precisa de FAIXA, não só de corte no 1º cancelar |
| B0.2 | **Agendamento concluído**: `POST /agendamentos` 7 chaves `{CodigoCliente, DataDeAgendamento "AAAA-MM-DD", Horario "HH:MM", CodigoProduto, QuantidadeTempoServico, QuantidadeTempoPermanencia, Encaixe}` → `{ServicoAgendado:true}` | HAR lateral [048] | P-E00110-A1 **destravada**: o endpoint sai de CANDIDATE |
| B0.3 | Os valores vêm do que o portal publicou: `CodigoCliente/CodigoProduto` = a loja de `OpcoesAgendamento`, os tempos = `TempoServico 75 / TempoPermanencia 90` de `horarios-disponiveis` | HAR [037][045][048] | nada é digitado: tudo é lido e casado por igualdade |
| B0.4 | No dia escolhido, **todos** os 40 blocos tinham `QuantidadeDisponivel:0`; 8 tinham `PossuiEncaixeDisponivel:true`; o escolhido (16:00) era encaixe e foi `Encaixe:true` | HAR [045] | horário "livre" = normal OU encaixe; a regra de `Encaixe` vem do bundle (§1.1) |
| B0.5 | Depois do `POST /agendamentos`, o `GET /atendimentos` traz no `ScriptFinalizacao` **"Agendado para 22/09/2026 às 16:00"** + loja + endereço + referência + permanência | HAR [049] | a confirmação é LIDA do portal, nunca presumida |
| B0.6 | O e-mail da Maxpar ao segurado diz só "registrado com sucesso" + franquia + link da Área do Segurado — **sem loja, dia ou hora** | `EMAIL VIDROS.txt`, `EMAIL LATARIA.txt` | quem entrega o agendamento ao segurado é o NOSSO agente |
| B0.7 | Lataria: `opcoes-disponiveis` = `BloqueadoIlhaNormal:true` + `PermiteOpcaoVistoria:true`, sem agenda nem conclusão; o SPA gravou `POST /atendimentos-prioridades {Situacao, DataLimite, Observacao}` e `POST /ocorrencias {"SEGURADO TEM PREFERÊNCIA POR REALIZAR VISTORIA EM LOJA"}` e só então veio `IrParaConclusaoDeAtendimento:true` → "com o analista" | HAR [089][092][093][105] | o roteador de hoje chama isso de **desconhecido → mão humana**; o portal segue. Unidade A5 |
| B0.8 | 🔴 O token de 21/09 22:09 UTC devolve **401** em 23/09 23:40 UTC | 1 GET somente-leitura com o token da captura | o token EXPIRA (entre minutos e ~50 h ❓): continuar CEDO, e 401 é desfecho legível |
| B0.9 | Sem token, só `/seguradoras/` e `/apolices` respondem; ufs, cidades, tipos-telefone, motivos, itens, serviços → **401** | 11 GET sem token | catálogo só depois do protocolo ⇒ a continuação é o único jeito de não perder o pedido |
| B0.10 | A API aceita `Origin: null` (página em branco): CORS `*` com `token_autorizacao` liberado | `OPTIONS` com 3 origens → 204, ACAO `*` | o API-first a partir de `about:blank` funciona (risco do canário fechado) |
| B0.11 | O token aparece em **5 URLs** do portal (`#/yelum/passoN/<token>`): o "continuar" do próprio portal é voltar com o token | HAR lateral, `pages`/URLs | o desenho da continuação é o do portal, não uma invenção |
| B0.12 | Contato nas 6 capturas: `StatusEnvioWhatsapp:true` só 1× (Tipo 20 CELULAR SEGURADO, lateral) ⇒ agregado `PossuiTelefoneRecebeWhatsapp:true`; sem a caixinha ⇒ `false` | script sobre as 6 capturas | Founder: "é bom ele receber" ⇒ Tipo 20 + `StatusEnvioWhatsapp:true` |
| B0.13 | `REDIS_URL` no portal-worker **nunca foi confirmado** (pendência aberta desde 17/08); `PORTAL_VAULT_KEY` existe (cifra senhas e sessões de portal) | `PENDENCIAS.md` §Bloco N · `portal_worker/vault.py` | o token vai CIFRADO pelo cofre do worker, não para o Redis |
| B0.14 | E-mail do corretor: regra já no código (`portal_tool._load_profile`): Perfil de Acionamento → e-mail do contato principal. Resulta e AutoFleet têm contato principal com domínio próprio e CNPJ | SELECT via conector, 23/09 | não trava; vira decisão registrada (D-E001101-03) |
| B0.15 | `PUT /atendimentos/cancelar` medido **4×** com `codigoMotivoCancelamento: 39` + texto livre; a atendente: "abriu um modal só para escrever, mínimo ~20–30 caracteres" | HAR + resposta 13 | ver §1.1 |

### 1.1 O que o JavaScript do portal decide (perícia do bundle `app-231e920f7d`, 23/09)
Laudo completo (com os trechos literais) do investigador Sonnet, read-only, 64 buscas: arquivado junto do relatório.
```
ROTEADOR  function M(o), nesta ordem: (1) IrParaConclusao|ExisteVistoriaCriada|ExisteAgendamento|ExisteOrdemServico|
          VistoriaFinalizada → conclusão · (2) PermiteVistoriaAmbas · (3) Loja · (4) Mobile · (5) RealizarVistoria ·
          (6) DisponibilizarAgendamento · (7) PermiteOpcaoVistoria → modal "queremos entender sua necessidade"
          (prioridade + preferência de vistoria) · (8) senão → conclusão.
          🔴 BloqueadoPorFraude / BloqueadoIlhaNormal / GerarOrdemServicoGenesis: ZERO ocorrências nos 3 bundles.
          O nosso roteador parava em BloqueadoIlhaNormal — o portal não. É o caso da lataria (ramo 7).
ENCAIXE   vem do MODO da agenda (TipoAgendamento === "Encaixe"), não de um campo do bloco. Livre no modo normal:
          QuantidadeDisponivel > 0; no modo encaixe: QuantidadeEncaixeParametrizadoDisponivel > 0.
          📊 Coerente com a captura: normal todo lotado, 16:00 com encaixe 1 ⇒ Encaixe:true.
VISTORIA  opção L/M grava só POST ocorrencias ("…REALIZAR VISTORIA EM LOJA" / "…ONLINE (LINK)") e vai à conclusão;
          "receber link" = GET vistoriamobile?telefone= (0 exercícios). Fotos: até 10, JPG/PNG ≤ 5 MB.
PRIORIDADE só no ramo 7; opções fechadas de Situação (5, variam com veiculoCarga) e prazo (4). 📊 medido 1×:
          "Não se aplica" · "Não tenho".
CANCELAR  motivos-cancelamento é código MORTO; 39 é constante do controlador; observação com mínimo 20 caracteres.
RETOMADA  o token vem de $stateParams.token (a URL) ou do POST /atendimentos; guardado em cookie. Não existe endpoint
          que devolva token para atendimento existente por placa/CPF/chassi.
TERMO     TermoExibido só quando e-mail + relação preenchidos E (Próprio sem corretor OU Corretor COM e-mail de
          corretor). 📊 bate com as 6 capturas; o código de hoje manda sempre true — defeito.
FORA      vistorias-previas/processar (sempre) e corretores-reclamacoes (fire-and-forget) não bloqueiam o roteamento.
```

## 2. O FIO

```
ABERTURA (001.10, inalterada no essencial)
 portal_tool._arun → portal_jobs(abrir_atendimento) → worker._run_job → vidros_apifirst.abrir_atendimento_api
   POST /atendimentos (Token) → [NOVO] sessao_duravel.guardar(token cifrado + estado) em evidence["continuacao"]
   → … → desfecho; se agenda e há preferência → [NOVO] agendar na MESMA sessão; se ilha/opção de vistoria →
     [NOVO] prioridade + ocorrência de vistoria → releitura → analista
CONTINUAÇÃO (nova)
 WhatsApp (resposta do segurado) → prompts (bloco vidros) → portal_tool._arun com a resposta
   → pedido vivo parado/aguardando + evidence["continuacao"]["possivel"] → portal_jobs(continuar_atendimento,
     idempotency = vidros_estado.idempotencia_de_continuacao(empresa, protocolo, operação))
   → worker._run_job (mesmo freio, mesma allowlist) → vidros_continuacao.continuar_atendimento_api
     restaura o token (cofre) → GET /atendimentos (o "consultar") → 401 ⇒ sessao_expirada (legível)
     → executa a ação pendente pelo ESTADO REAL do agregado → desfecho → evidence
   → format_result / mensagem_do_desfecho → WhatsApp
 vigia_do_portal: parada TÉCNICA depois do protocolo ⇒ enfileira continuação "reler" (teto de tentativas)
```

## 3. Unidades

| # | unidade | dono |
|---|---|---|
| A1 | **Sessão durável**: token cifrado (`vault`) + `evidence["continuacao"]` = {possível, etapa, ação esperada, emitida_em, seguradora, protocolo, código, categoria}; nunca o token em claro em evidence/log | A |
| A2 | **Journey `continuar_atendimento`** (registro + função): reidrata, lê o agregado, decide pelo estado REAL, executa a ação pendente; ⛔ nunca `POST /atendimentos` (a sessão em modo continuação recusa); reusa as fases da abertura (refatoração em funções, nenhum segundo motor) | A |
| A3 | **Agendar**: `POST /agendamentos` APPROVED; escolha por IGUALDADE (loja por código publicado, dia `DD/MM`, horário `HH:MM`) contra o publicado NAQUELE momento; `Encaixe` pela regra do bundle; confirmação lida do `ScriptFinalizacao`; comprovante | A |
| A4 | **Agendar na mesma sessão** quando o segurado já deu a preferência (a partir de que dia · manhã/tarde/qualquer): loja mais próxima pela distância que o portal calculou; primeiro horário que casa; sem casamento ⇒ apresenta e espera (continuação) | A |
| A5 | **Roteador**: ilha normal + opção de vistoria ⇒ prioridade + ocorrência de preferência (link × loja) ⇒ releitura ⇒ analista/vistoria; `atendimentos-prioridades` e `ocorrencias` APPROVED só com o texto/opções do bundle | A |
| C1 | **Tool continua**: pedido vivo parado + resposta nova ⇒ job `continuar_atendimento`; nunca um 2º `abrir_atendimento`; frase honesta quando a continuação é impossível | C |
| C2 | **Coleta**: preferência de agenda (famílias de troca) e de vistoria (lataria) coletadas ANTES e sem travar; domicílio SAI (decisão do Founder) e vira "loja" por padrão; contato Tipo 20 + WhatsApp | C |
| C3 | **Mensagens**: agendamento confirmado (loja, endereço, referência, dia, hora, permanência, franquia, número); agenda para escolher com HORÁRIOS; paradas deixam de dizer "a equipe assume" quando há continuação | C |
| C4 | **Vigia + Fila**: parada técnica ⇒ continuação automática (teto); agenda confirmada conclui o run; 401 ⇒ alerta humano com dossiê | C |

**Sai (com gatilho):** fotos/vistoria multipart e link de vistoria mobile (0 exercícios; gatilho: captura) · domicílio
(decisão do Founder) · cancelar/abandonar automáticos (decisão de gente; gatilho: pedido explícito do segurado + D) ·
reagendar (o portal não mostrou a tela; gatilho: captura) · a Fila do front ler o run (P-E00110-C-03).

## 4. Arquivos por builder (DISJUNTOS)
```
A  backend/portal_worker/journeys/vidros_api.py · vidros_sessao.py · vidros_estado.py · vidros_apifirst.py ·
   vidros_continuacao.py (NOVO) · vidros_questionario.py (só se preciso) · journeys/__init__.py (só o registro)
   backend/tests/_replay_vidros.py · test_e001101_a_*.py · test_e001101_o_fio_da_continuacao.py
   + os testes da 001.10 que afirmarem verdade vencida (CLAUDE.md §9.3) — só A os altera
C  backend/app/agents/tools/portal_params.py · portal_tool.py · backend/app/core/prompts.py ·
   backend/app/services/perguntas_do_portal_de_vidros.py · backend/app/tasks/vigia_do_portal.py ·
   backend/portal_worker/worker.py (só se preciso) · backend/tests/test_e001101_c_*.py
```

## 5. 🔴 O CONTRATO A ↔ C
**C → A (params do job de abertura, chaves novas):**
```
especificos.preferencia_agenda ... {"a_partir_de": "DD/MM/AAAA", "periodo": "manha"|"tarde"|"qualquer", "horario"?: "HH:MM"}   (opcional; com "horario" o motor agenda SÓ esse horário, no 1º dia ≥ a_partir_de em que ele está livre; não achou ⇒ agenda com as opções)
especificos.preferencia_vistoria . "link" | "loja"                                                      (opcional)
contato.tipo_telefone ............ "segurado" (padrão)  · contato.recebe_whatsapp: true
```
**C → A (job `continuar_atendimento`):** `params` = os do job de origem + `_continuacao`:
```
{"job_origem": uuid, "operacao": "agendar"|"responder"|"reler"|"vistoria",
 "escolha": {"loja": <CodigoCliente como texto>, "dia": "DD/MM", "horario": "HH:MM"},   (agendar)
 "respostas": {<os slots novos: cidade_servico, peca, como, pecas_lataria, aceita_reparo, pergunta_N…>}}
```
**A → C (evidence):**
```
continuacao ...... {possivel, etapa, acao_esperada, emitida_em, sessao_guardada, motivo}   ⛔ sem token
desfecho.tipo .... + "agendado"  · desfecho.agendamento = {loja, endereco, referencia, data "DD/MM/AAAA",
                   horario "HH:MM", permanencia, confirmado_pelo_portal: bool}
desfecho.lojas[].horarios = {"DD/MM": ["HH:MM", …]}   (só blocos livres: normal ou encaixe)
stage ............ + "sessao_expirada" (401 na continuação) · + "horario_indisponivel" (escolha sumiu)
```

## 6. Gates
```
G1  replay do HAR LATERAL, abertura + preferência: POST /agendamentos sai UMA vez com as 7 chaves e os valores
    do publicado; desfecho "agendado" com o "Agendado para" LIDO. Mutação: Encaixe invertido ⇒ VERMELHO
G2  replay LATERAL em 2 jobs: abertura termina "agenda" (sem POST agendamentos) → continuação com a escolha ⇒
    agenda; escolha fora do publicado ⇒ "horario_indisponivel", NADA sai
G3  a continuação NUNCA emite POST /atendimentos (mutação: permitir ⇒ VERMELHO)
G4  token ausente/indecifrável ⇒ continuação impossível e legível; GET 401 ⇒ "sessao_expirada", nenhuma escrita
G5  replay da LATARIA [61–113]: ilha + opção de vistoria ⇒ prioridade + ocorrência (texto do bundle) ⇒ analista;
    sem preferência coletada ⇒ para ANTES da ocorrência com a pergunta
G6  o token nunca aparece em evidence, log, work_run nem mensagem (varredura do texto com o token do replay)
G7  tool: pedido vivo parado + resposta ⇒ job continuar_atendimento com idempotência de continuação; a mesma
    resposta 2× ⇒ um job só; resposta sem pedido parado ⇒ comportamento de hoje
G8  mensagens: "agendado" imprime loja/endereço/dia/hora/permanência exatos, sem {, [, None
G9  domicílio não trava mais o pedido; contato Tipo 20 + StatusEnvioWhatsapp:true no corpo de /solicitantes
G10 os 3 HAR da 001.10 continuam verdes (regressão direta)
G11 dois tenants: a continuação de A nunca lê o job de B (filtro company_id no código)
G12 🧑 canário — roteiro entregue; execução depende do Founder
```

## 7. Decisões tomadas na execução (nota 0–100)
| # | decisão | notas |
|---|---|---|
| D-E001101-01 | **Onde mora o token:** cifrado pelo cofre do portal-worker (`PORTAL_VAULT_KEY`) dentro de `portal_jobs.evidence["continuacao"]`, com instante de emissão; nunca em claro | cofre **88** · Redis com TTL 60 (REDIS_URL não confirmado no worker) · coluna nova + migration 70 · manter o job vivo esperando 40 |
| D-E001101-02 | **Agendamento:** preferência (a partir de que dia · manhã/tarde) coletada ANTES; o robô agenda na mesma sessão a loja mais próxima e o 1º horário que casa, e confirma lendo o portal; sem casamento, apresenta as opções e continua quando o segurado escolher | preferência + continuação **90** · só continuação 70 (depende do token viver até a resposta) · equipe agenda na mão (hoje) 20 |
| D-E001101-03 | **E-mail do corretor:** Perfil de Acionamento → e-mail do contato principal da corretora → nenhum (EmailCorretor nulo) | regra do banco **90** · e-mail fixo de atendente 10 (CLAUDE.md §13.9) |
| D-E001101-04 | **Contato (fecha D-E00110-F1, respondida pelo Founder):** Corretor (6) + celular e e-mail do SEGURADO + WhatsApp marcado | **88** (escolha do Founder) |
| D-E001101-05 | **Domicílio:** fora; o robô não pergunta e não oferece | decisão do Founder |

## 8. O que o estado da arte faz, e o que modelamos
1. **Stripe — Idempotent requests** · `https://docs.stripe.com/api/idempotent_requests` · a mesma chave devolve o mesmo
   resultado · MODELAMOS: a continuação tem chave própria (empresa+protocolo+operação) · REJEITAMOS: reaproveitar a chave
   de criação · JUIZ: G7, mesma resposta 2× = 1 job.
2. **Temporal — Durable Execution** · `https://docs.temporal.io/workflows` · o estado de um fluxo longo sobrevive a
   quedas e retoma do passo · MODELAMOS: a etapa e a ação esperada ficam no banco e a continuação decide pelo estado REAL
   lido · REJEITAMOS: um motor de workflow novo (CLAUDE.md §5) · JUIZ: G2 em dois jobs separados.
3. **RFC 6750 — Bearer Token** · `https://www.rfc-editor.org/rfc/rfc6750` · token de portador expira e 401 é a resposta
   · MODELAMOS: 401 é desfecho legível, nunca retry cego · REJEITAMOS: renovar token por novo POST (criaria outro
   pedido) · JUIZ: G4.
4. **cryptography — Fernet** · `https://cryptography.io/en/latest/fernet/` · cifra simétrica autenticada ·
   MODELAMOS: o token em repouso só cifrado, pela chave que o worker já tem · REJEITAMOS: guardar em claro "porque
   expira" · JUIZ: G6.
5. **W3C HAR 1.2** · `https://w3c.github.io/web-performance/specs/HAR/Overview.html` · replay de borda ·
   MODELAMOS: o dublê responde o que o portal respondeu, por faixa de entradas · JUIZ: G1/G2/G5.
</content>
</invoke>
