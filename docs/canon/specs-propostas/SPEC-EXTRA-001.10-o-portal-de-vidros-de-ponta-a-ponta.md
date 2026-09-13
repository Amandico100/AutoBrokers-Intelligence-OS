# SPEC-EXTRA-001.10 · O portal de vidros de ponta a ponta

> **Proposta de SPEC** · 13/09/2026 · redigida no chat do diagnóstico (D-PILOTO-20)
> **Origem:** `DIAGNOSTICO-PILOTOS-E-PLANO-EXTRA-2026-09-12.md` §10 (laudo I5) ·
> D-PILOTO-17 · P-PILOTO-07 · P-50
> **Marcha:** CRÍTICO · 3 juízes · 💭 10–14 h
> **Evidências com `arquivo:linha` e comando:**
> [`SPEC-EXTRA-001.10-…-RESEARCH-PACK.md`](SPEC-EXTRA-001.10-o-portal-de-vidros-de-ponta-a-ponta-RESEARCH-PACK.md)
>
> 📊 medido (com data, fonte e comando) · 💭 ilustrativo, **nunca citável como fato** — CLAUDE.md §12.1

---

## §0 · O resultado, o motivo, e o card

### 0.1 O resultado, em uma frase

> **Um acionamento de vidros na Yelum ou na Porto sai do WhatsApp do segurado e
> chega ao comprovante (lataria/martelinho) ou à loja, dia e hora confirmados
> (vidraçaria), sem a Regina — e o agente pergunta só o que o catálogo daquela
> apólice exige.**

### 0.2 O motivo — o caminho API-first não pode funcionar como está

📊 Medido em 13/09/2026, relendo o código:

```
vidros_apifirst.py:20-23   documenta, no docstring, a ordem correta:
                             PUT  /atendimentos/corretores
                             POST /solicitantes
                             PATCH /atendimentos   ← "grava peça, causa, local"
vidros_sessao.py:139-237   os métodos que existem: 9. `atualizar_atendimento`: nenhum.
                           grep -c "PATCH" portal_worker/journeys/vidros_sessao.py → 0
```

🔴 **O PATCH é o que grava peça, causa, cidade e local.** Sem ele o questionário do
portal não tem de onde nascer — ele deriva do `CodigoItemCoberto`, que só o PATCH
grava. O módulo salta do `POST /atendimentos` direto para
`QZ.rodar_questionario` (`vidros_apifirst.py:275-279`). **Com a flag
`PORTAL_VIDROS_API_FIRST` ligada hoje, o pedido nasce vazio e o questionário não
tem como responder.**

E há um segundo defeito, mais caro, porque é silencioso:

📊 **A fronteira do efeito material muda de lugar por categoria de peça.** Medido
nos dois HAR da Yelum, com linha de controle nos dois sentidos (CLAUDE.md §9.2):

| captura | categoria | `GET /atendimentos` logo **depois** do PATCH |
|---|---|---|
| Yelum lataria, 09/09 | `L` | `CodigoAtendimento = 23232316` — **nasceu no PATCH** |
| Yelum vidro de porta, 14/08 | `V` | `CodigoAtendimento = None` — só nasce no `POST /questionarios` |

`vidros_estado.py:233` fixa **uma** fronteira (`FRONTEIRA_MATERIALIZAR =
"gravar_questionario"`). Para lataria ela arma no lugar errado: o guard autoriza
depois que o pedido já existe. 🔴 **É a receita de um segundo atendimento, pago,
no nome do mesmo segurado** — e o portal não deixa desfazer
(`O-PORTAL-DE-VIDROS-TELA-POR-TELA.md` §3 e §9.5).

### 0.3 As decisões do Founder já incorporadas — não se reabrem

| decisão | o que ela manda aqui |
|---|---|
| **D-PILOTO-17** | Bradesco: **primeiro uma captura no `abraseuatendimento` com o slug `bradesco`**; o `agendeseuservico` só entra se a captura provar recusa. ⛔ **Zero linhas de código para `agendeseuservico` nesta SPEC.** |
| **D-PILOTO-08** | A numeração é **EXTRA-001.10**; não renumera nada. |
| **D-PILOTO-14** | AAA opção B · marcha fixada · **≤ 12 guardas novos** · bateria sobre motor e acervo real. |
| **D-PILOTO-20** | Execução em chat novo, sob AAA opção B, com a marcha do diagnóstico §8. |
| **D-PILOTO-05** | Coleta dirigida: percorrer até a confirmação e **recusar**. Vale para toda seguradora que não seja o canário nomeado. |
| Founder, 02/08 (mapa §6) | A caixa "receber atualizações via WhatsApp" fica **desmarcada** enquanto o telefone do passo 2 for o da corretora. |
| Founder, 02/08 (mapa §9.2) | **Nunca responder "Não sabe" para destravar tela.** |

### 0.4 🔴 EXECUTION CARD (proposto — o executor reconfirma no BLOCO 0)

```
OUTCOME ......... o acionamento de vidros chega ao comprovante (lataria) ou à loja,
                  dia e hora confirmados (vidraçaria) sem a Regina
RISCO ........... 8 = ALCANCE 3 (o SEGURADO) + REVERSIBILIDADE 3 (sai do prédio:
                  abre pedido no portal da seguradora) + FREQUÊNCIA 2 (todo
                  acionamento de vidros)
SUPERFÍCIE ...... 2 — vários comportamentos, em lugares que eu listo: journey
                  API-first, sessão HTTP, máquina de estado, catálogo de perguntas,
                  tool do agente, prompt do Core, vigia
PISO APLICADO ... §3.2 "qualquer coisa que ENVIE acionamento" → CRÍTICO no mínimo.
                  A conta já dava CRÍTICO (RISCO 8); o piso confirma.
NÍVEL ........... CRÍTICO
UNIDADES ........ 13 blocos (5 em P0, 6 em P1, 4 em P2)
COESÃO .......... P0-1..P0-3 tocam o MESMO contrato (SessaoVidros ↔ vidros_estado ↔
                  vidros_apifirst) → ficam JUNTOS, um dono. P0-4 (mapa de slugs) e
                  P0-5 (cidade + as três verdades) são disjuntos e podem ir em
                  paralelo com P0-1..3. P1 depende de P0 fechado.
PARALELISMO REAL  no máximo 2 escritores: {P0-1..P0-3} e {P0-4, P0-5}. Nunca 3.
                  `vidros_api.py` é ARQUIVO-HUB: UM dono por vez (§3.4).
TIME ............ desenhista da prova (antes do código) · builder por unidade ·
                  verificador mecânico · painel de 3 lentes · red team ·
                  integrador (13 unidades) · 1 juiz fresco de confirmação+auditoria
REFERÊNCIA ...... interna: `backend/tests/test_a_maquina_de_lavar_vai_ate_o_fim.py`
                  (atendimento ponta a ponta, turno a turno) e
                  `docs/canon/MIGRATIONS-AUTHORITY.md` se houver SQL.
                  externa: §13 desta SPEC (6 referências, cada uma inspecionável)
GATES ........... os 12 da §16, cada um com a mutação que o deixa vermelho (§8)
O ELO ........... "a fronteira material muda por CATEGORIA" → medi A (lataria: número
                  nasce no PATCH) · medi B (vidraçaria: não nasce no PATCH, nasce no
                  POST /questionarios) · e medi que B CHEGA em A: o mesmo `GET
                  /atendimentos`, imediatamente após o mesmo PATCH, dá resultado
                  OPOSTO nas duas capturas. É a linha de controle.
FAIXA DE RELÓGIO  💭 10–14 h · 💭 1,5–2,5 M tokens de subagentes (teto CRÍTICO §10)
BLOCKER ......... P0 inteiro. Sem ele o API-first está morto (não grava) ou é
                  perigoso (arma a fronteira no lugar errado).
```

---

## §1 · Autorização de testes — o que pode sair, e para quem

🔴 **Esta SPEC abre pedidos em portal de seguradora. Um pedido aberto por engano é
um vidraceiro na porta de um segurado que não pediu.**

### 1.1 A allowlist

```
✅ PERMITIDO
   · replay OFFLINE dos 4 HAR do acervo (nenhuma rede; o motor lê arquivo)
   · leituras do portal (GET /seguradoras, /apolices, /itens-cobertos, /motivos-dano,
     /ufs, /cidades, /clientes/cidades) — nenhuma delas muda nada
   · UM acionamento de LATARIA na Yelum com o VEÍCULO DE TESTE do Founder, no
     canário da §10, com o freio ligado só para esse job

⛔ PROIBIDO, sem exceção
   · qualquer escrita no portal fora do canário nomeado
   · qualquer POST/PUT/PATCH com apólice de segurado real que não seja a de teste
   · qualquer mensagem a segurado ou a seguradora fora de TESTE-A / TESTE-B
   · acionar Bradesco, Azul, Zurich, ou qualquer uma das 34 restantes (D-PILOTO-17
     e a ordem de ataque da §14 proíbem código antes de captura)
   · imprimir ou gravar CPF, CNPJ, placa, chassi, telefone, e-mail, nome de segurado
     ou o `Documento` do `PUT /atendimentos/corretores` (é um CPF)
```

### 1.2 A verificação ANTES de cada efeito

Antes de qualquer chamada de escrita, o executor confere, nesta ordem, e registra
a saída no relatório:

```bash
# 1. o freio está ligado? (tem de estar vazio ou false fora do canário)
echo "PORTAL_EFEITO_MATERIAL_LIBERADO=${PORTAL_EFEITO_MATERIAL_LIBERADO:-<vazio>}"
# 2. a flag do caminho novo está desligada em produção?
echo "PORTAL_VIDROS_API_FIRST=${PORTAL_VIDROS_API_FIRST:-<vazio>}"
# 3. o CPF do job é o do veículo de teste? (compara HASH, nunca imprime o valor)
python - <<'PY'
import hashlib, os
print("cpf_hash_do_job =", hashlib.sha256(os.environ.get("CANARIO_CPF","").encode()).hexdigest()[:12])
PY
```

🔴 **Se qualquer uma das três não bater, o bloco para e vai para a caixa do Founder.**
Não é uma das oito paradas legítimas do CLAUDE.md §10 — é a trava desta SPEC, e ela
vence.

---

## §2 · Escopo, e o que sai de propósito

### 2.1 Entra

```
P0  o PATCH e os dois pré-requisitos · a fronteira material por CATEGORIA ·
    o mapa único de seguradoras · o slot bloqueante `cidade_para_o_servico` ·
    a reconciliação das três verdades sobre o que perguntar
P1  ler e APRESENTAR lojas, distâncias, dias e horários · agendar/direcionar atrás
    de flag e aprovação · perguntas por família · desambiguação pelo catálogo ·
    lataria como caminho próprio · vistoria e fotos
P2  uma régua só para o trincado · `abandonar`/`cancelar` como journeys ·
    Bradesco conforme D-PILOTO-17 · o Vigia continua cobrindo vidros
```

### 2.2 Sai — com o gatilho que a faz voltar

| o que sai | por quê | **o que a faz voltar** |
|---|---|---|
| **Subfluxo de domicílio** (`transportes-proprios/*`, `servicos-moveis/ordens-servicos`, formas de pagamento) | 📊 `AtendeServicoMovel:false` nas duas capturas da Yelum; zero exercício | **captura nº 2 da Regina** (domicílio num CEP com cobertura) |
| **`PATCH atendimentos/finalizar`** | declarado no bundle, zero capturas; e nas duas capturas o fluxo terminou sem ele | uma captura que o exerça |
| **`agendeseuservico` (Bradesco)** | 🔴 **D-PILOTO-17 proíbe** código antes da captura dupla | a captura nº 10 do roteiro dizer que o `abraseuatendimento` recusa |
| **Roda/pneu/suspensão** | 📊 o único HAR morre no preflight 400 (sem cláusula) | a captura nº 12 (roda **com** cobertura) |
| **Consultar atendimento / Área do Segurado** | 📊 nunca capturado; é acompanhamento, não acionamento | captura nº 8; e é matéria da EXTRA-001.7 |
| **As 34 seguradoras além de Yelum/Porto/Azul/Zurich** | 📊 zero capturas; P-50 | 1 captura de passo 1 + `itens-cobertos` por seguradora |
| **Reescrever o caminho DOM (`vidros_lanternas`)** | ele funciona e é o fallback; mexer nele agora é risco sem retorno | nunca nesta SPEC |

🔴 **Escopo não se reduz sem decisão do Founder (D5 / CLAUDE.md §11).** Tudo o que
sair além desta tabela vira entrada em
[`CHANGE-ADDENDA.md`](../CHANGE-ADDENDA.md), classificada, **antes** de ser
executado.

---

## §3 · As autoridades preservadas — e nenhum motor paralelo

🔴 **CLAUDE.md §5.** Para cada peça desta SPEC, o que já existe e é reaproveitado:

| o que a SPEC precisa | o que **já existe** e é reaproveitado | o que NÃO se cria |
|---|---|---|
| falar com a API do portal | `SessaoVidros` (`vidros_sessao.py`) — cliente HTTP estreito, allowlist por chamada, teto de 150 chamadas | ⛔ nenhum cliente HTTP novo, nenhuma biblioteca, nenhum socket |
| autorizar efeito material | `PortalActionGuard` da SPEC-073 (`portal_worker/guardrails.py`) — `before`/`submetido`/`confirmado`/`incerto` | ⛔ nenhum guard próprio de vidros |
| estado de negócio do pedido | `EstadoDoAtendimento` + `ESTADOS` (`vidros_estado.py:44-62`) | ⛔ nenhuma máquina de estado nova |
| motor de perguntas do portal | `vidros_questionario.rodar_questionario` + `SessaoVidros.proxima_pergunta` | ⛔ nenhum motor de questionário paralelo |
| catálogo de perguntas ao segurado | `perguntas_do_portal_de_vidros.py` — `_UNIVERSAIS`, `_ESPECIFICAS_POR_IDENTIDADE`, `o_que_falta`, `mensagem_para_o_agente` | ⛔ nenhuma segunda tabela de perguntas |
| derivar contrato de captura | **SPEC-077** `portal_factory.py lab har\|api-infer\|promote` — a escada OBSERVED → CANDIDATE → APPROVED | ⛔ ⛔ **nenhum contrato escrito à mão.** A ferramenta existe e nunca foi usada sobre este material |
| vigiar job de vidros parado | `app/tasks/vigia_do_portal.py` | ⛔ nenhum vigia novo |
| a rota do agente até o portal | `PortalActionTool` (`app/agents/tools/portal_tool.py`) + `build_portal_params` (`app/agents/tools/portal_params.py`) | ⛔ nenhuma tool nova de vidros |

**A regra de ouro desta SPEC:** tudo o que ela acrescenta é **método novo em classe
existente** ou **constante nova em módulo existente**. 📊 Zero arquivos novos em
`portal_worker/journeys/` — com uma exceção nomeada: o **fixture de replay
offline** do gate G1, que vive em `backend/tests/` e não é código de produto.

---

## §4 · BLOCO 0 — converter medindo (obrigatório, antes de qualquer linha)

> Este documento envelhece. As linhas mudaram entre o laudo I5 (13/09 de manhã) e
> esta proposta (13/09 à tarde). **O número do executor vence o meu** (protocolo §5①).

O executor **remede** e cola a saída no relatório, ANTES de codar:

```bash
cd backend
# B0.1 — o PATCH continua ausente?
grep -n "atualizar_atendimento\|PATCH" portal_worker/journeys/vidros_sessao.py    # esperado: 0 linhas
grep -c "async def " portal_worker/journeys/vidros_sessao.py                      # métodos hoje

# B0.2 — a fronteira continua fixa?
sed -n '230,240p' portal_worker/journeys/vidros_estado.py

# B0.3 — quantos EP_ declarados nunca são chamados?
for ep in $(grep -o '^EP_[A-Z_]*' portal_worker/journeys/vidros_api.py); do
  n=$(grep -rn "$ep" --include=*.py . | grep -v "vidros_api.py:" | wc -l)
  [ "$n" = "0" ] && echo "NUNCA CHAMADO: $ep"
done            # 📊 medido em 13/09: 9 (+2 já marcados _NAO_MEDIDO)

# B0.4 — o hardcode de slugs
sed -n '100,110p' portal_worker/journeys/vidros_apifirst.py    # 📊 3 entradas, uma delas ITAU

# B0.5 — as três verdades sobre o que perguntar
grep -n "portal_action\*\* IMEDIATAMENTE" app/core/prompts.py
sed -n '43,60p'   app/agents/tools/portal_params.py            # TRANSPORTAVEIS
sed -n '125,136p' app/agents/tools/portal_tool.py              # a description da tool

# B0.6 — o que o laboratório da SPEC-077 diz do material (a ferramenta já existe)
PYTHONIOENCODING=utf-8 python scripts/portal_factory.py lab har \
  --arquivo "../docs/intake/materiais/portal-vidros/YELUM/YELUM 1/abraseuatendimento.com.br.har" \
  --host abraseuatendimento.com.br
```

📊 **O que o BLOCO 0 tem de reproduzir** (medido em 13/09/2026, comandos acima):

```
lab har sobre o HAR da Yelum lataria:
   354 chamadas · 188 depois de descartar ruído · 41 endpoints distintos
   14 de ESCRITA  ← ⚠️ são 7 escritas + 7 preflight OPTIONS. A sequência que o
                     gate G1 compara é a das 7, sem OPTIONS.
   29 com forma inferível · 44 respostas JSON com corpo capturado
   host que serve API: api.autoglass.com.br (31 respostas JSON)
```

🔴 **Se qualquer número divergir, o do executor vence e a SPEC se corrige por
emenda escrita** — não se silencia a divergência.

### 4.1 Três perguntas que o BLOCO 0 tem de RESPONDER, e que mudam o desenho

```
Q-A  O freio `PORTAL_EFEITO_MATERIAL_LIBERADO` é POR JOB ou GLOBAL?
     Se for global, ligá-lo no canário abre a porta para todos os jobs de vidros
     em voo. Nesse caso nasce o bloco P0-6 (BLOCKER, via CHANGE-ADDENDA): uma
     allowlist de job/CPF, como a `BILLING_CANARIO_ALLOWLIST` já faz na cobrança.

Q-B  `GET /apolices/itens-cobertos` exige o Token (ou seja, exige que o
     `POST /atendimentos` já tenha acontecido)?
     📊 Na ordem BRUTA do HAR o POST vem ANTES do itens-cobertos. Se o catálogo só
     existir depois da fronteira A, a desambiguação de P1-4 acontece ENTRE as duas
     fronteiras — o que é read-only para categoria `V` e é DEPOIS DO EFEITO para
     categoria `L`. Para `L`, a desambiguação tem de sair do catálogo genérico da
     seguradora, não do da apólice. Isto muda P1-4.

Q-C  O autocomplete do portal lista "Liberty" ou "Yelum"?
     📊 O bundle serve `app/paginas/seguradoras/liberty/` com
     `<title>Menu Atendimento - Liberty</title>`, e `portal_params.py:69-71`
     traduz LIBERTY → "Yelum", texto que `vidros_lanternas.py:1090-1108` DIGITA
     no `#seguradora-input`. Se o campo lista "Liberty", o caminho DOM pode estar
     clicando na primeira opção visível de uma busca que não casou.
```

---

## §5 · P0 — sem isto o API-first está morto ou é perigoso

### P0-1 · `SessaoVidros.atualizar_atendimento` = `PATCH /atendimentos`

**Contrato do bundle** (📊 lido na função `atualizarAtendimento` de
`app-231e920f7d.min.js`, 13/09 — o comando está no RESEARCH-PACK):

```python
async def atualizar_atendimento(
    self,
    *,
    codigo_item_coberto: str,          # "1|142|S|11335|1|0|L"  ← a chave composta
    codigo_cidade: int,                # de GET /cidades, pela UF
    codigo_objeto_causa: int,          # de GET /motivos-dano, pela peça
    avaliacao_dano: str,               # o relato — o portal exige mín. 30 chars
    perimetro_dano: str,               # "U" | "R" | "N"  (PRIMEIRA LETRA)
    cep: str = "",
    codigo_zona: Optional[int] = None,
    item_removido: Optional[bool] = None,       # "O item permanece no veículo?"
    evento_composto: Optional[bool] = None,     # "Mais de um item danificado?"
    polimento_farol: Optional[bool] = None,     # só quando a oferta apareceu
    servicos_martelinho_lataria: Optional[list] = None,
        # [{"CodigoServico": int, "CodigoObjetoCausa": int}, ...]
) -> Dict[str, Any]:
    """FRONTEIRA MATERIAL para categoria `L`. Leitura-e-escrita para `V`."""
```

🔴 **A regra do corpo — e ela é o coração do gate G1.** O contrato do bundle tem
**11 campos**. 📊 **O que sai no fio, em 2 de 2 capturas, são 8**: `ItemRemovido`,
`EventoComposto` e `PolimentoFarol` **não aparecem** porque o AngularJS serializa
com `JSON.stringify`, que **descarta chaves `undefined`**. `CodigoZona` sobrevive
porque o bundle a escreve com um ternário explícito para `null`.

```
✅ CERTO   omitir a chave quando o valor é None  → corpo de 8 chaves, igual ao HAR
❌ ERRADO  mandar "ItemRemovido": null           → corpo de 11 chaves, ≠ do HAR
```

Um `null` explícito onde o portal nunca viu um `null` é um campo inventado. E o
gate G1 compara **o corpo inteiro, chave a chave**.

**Onde entra:** `vidros_apifirst.py`, entre o `POST /atendimentos` (a fronteira A,
hoje em `:225`) e o questionário (hoje em `:275`), **e depois de P0-2**.

**Gate P0-1:** o replay offline do HAR da Yelum lataria produz um corpo de PATCH
igual ao capturado — mesmas chaves, mesma ordem, mesmos valores não-PII (os campos
de PII vêm do fixture).

---

### P0-2 · `POST /solicitantes` + `PUT /atendimentos/corretores` — obrigatórios

📊 **Presentes em 3 de 3 HAR que abriram atendimento**, sempre nesta ordem:

```
POST /atendimentos            ← nasce NumeroProtocolo (16 dígitos) + Token
PUT  /atendimentos/corretores   {"Documento": "<CPF/CNPJ do corretor>"}
POST /solicitantes              {RelacaoTitular, EmailSegurado, [EmailTitularAplice,]
                                 NomeSolicitante, CpfCnpjSolicitante, EmailCorretor,
                                 Telefones, TermoExibido, TermoAceito}
PATCH /atendimentos           ← P0-1
```

🔴 **`RelacaoTitular` é uma string, e o código de Corretor é `"6"`, não `"4"`.**
`vidros_api.py:298-305` já tem o mapa `RELACAO_TITULAR` com `6: "Corretor"` e o
comentário que explica por que decorar a posição da lista dá errado. 📊 A captura
de 09/09 mandou `"6"`; a de 14/08 mandou `"5"` (Outros) — **duas capturas, dois
valores, e a nossa escolha é sempre `"6"`**, porque quem abre é a corretora.

🔴 **`TermoAceito: false` nas duas capturas.** Não inventar `true`.

**Gate P0-2:** o replay produz as 3 escritas nesta ordem, com
`RelacaoTitular == "6"` e `TermoAceito == False`.

---

### P0-3 · A fronteira material calculada por CATEGORIA

**O contrato:**

```python
# vidros_estado.py — ao lado das constantes que já existem (:232-238)

def fronteira_materializar_de(codigo_item_coberto: str) -> str:
    """Qual ação NESTA peça é a que faz o pedido existir para o analista.

    📊 Medido nos dois HAR da Yelum, com linha de controle nos dois sentidos:
       categoria `L` (lataria) → o PATCH materializa. Não há POST /questionarios.
       categoria `V` (vidraçaria) → o PATCH NÃO materializa; o POST /questionarios sim.
    Categoria desconhecida → devolve FRONTEIRA_ABRIR, que é a mais conservadora:
    arma antes, nunca depois. Fail-closed.
    """
```

Reaproveita `API.partes_do_item_coberto` (`vidros_api.py:263`), que já quebra a
chave composta e devolve `categoria` (índice 6), e já é fail-closed para formato
inesperado.

A journey passa a nomear ao guard a fronteira **daquela peça**:

```python
guard.acao_material_esperada = ST.fronteira_materializar_de(item["CodigoItemCoberto"])
```

🔴 **E o guarda que fecha a porta (G2 da §8): um teste que fica VERMELHO se
`FRONTEIRA_MATERIALIZAR` voltar a ser consumida como constante fixa dentro da
journey.** Sem ele, a regressão é invisível: o código compila, os testes de
vidraçaria passam, e só a lataria quebra — em produção, com dinheiro.

**Gate P0-3:** dois casos, mesma superfície, veredito oposto (protocolo §5):
`"1|142|S|11335|1|0|L"` → a autorização é pedida **antes do PATCH**;
`"3|129|N|10700|1|0|V"` → a autorização é pedida **antes do `POST /questionarios`**.

---

### P0-4 · Um mapa só de seguradora, e ele é o do portal

📊 Medido em 13/09 sobre o HAR de 09/09 e o bundle:

```
GET /seguradoras/ ......... 38 códigos ativos
bundle (rota da SPA) ...... 43 slugs
só no bundle .............. 5 — BLLU · GENERALI · GRUPO_HDI · ITAU · ZURICHSANTANDER
só na API ................. 0
o código conhece .......... 3 — PORTO · AZUL · ITAU   (vidros_apifirst.py:102-106)
```

🔴 **Três defeitos, não um:**

1. **`ITAU` está no código e não está entre os 38 ativos.** Ele existe como rota no
   bundle, mas a API não o oferece. A promessa fail-closed de
   `slug_da_seguradora` (`vidros_apifirst.py:82-97`) fica de pé por acidente para
   35 seguradoras e **quebra justamente para o ITAU**, que passa.
2. **Yelum é `LIBERTY`.** 📊 O bundle roteia `LIBERTY: "yelum"` (o nome do estado do
   ui-router) e serve os templates de `app/paginas/seguradoras/liberty/`, com
   `<title>Menu Atendimento - Liberty</title>`. Enquanto isso
   `portal_params.py:69-71` traduz `LIBERTY → "Yelum"` e
   `vidros_lanternas.py:1090-1108` **digita esse texto** no `#seguradora-input`.
   Ver a pergunta Q-C do BLOCO 0: **medir antes de consertar.**
3. **`sompo` e `SOMPO` são coisas diferentes.** 📊 O bundle diz
   `GRUPO_HDI: "sompo"` **e** `SOMPO: "sompo-seguros"`. Quem "corrigir" o primeiro
   para `SOMPO` roteia o segurado para a seguradora errada.

**O contrato:** um único mapa em `vidros_api.py` (o módulo que já é a autoridade de
contrato do portal), derivado da medição, com as duas direções:

```python
# 📊 38 códigos de GET /seguradoras/ (09/09/2026) + 5 só no bundle, marcados.
SEGURADORAS_DO_PORTAL: Dict[str, Dict[str, Any]] = {
    "LIBERTY":   {"rota": "yelum", "template": "liberty", "ativa": True,
                  "marcas": ("yelum", "liberty", "libe")},
    "GRUPO_HDI": {"rota": "sompo", "ativa": False, "marcas": ()},
    "SOMPO":     {"rota": "sompo-seguros", "ativa": True, "marcas": ("sompo",)},
    "ITAU":      {"rota": "itau", "ativa": False, "marcas": ()},  # rota existe, API não oferece
    ...
}
```

`slug_da_seguradora` e `normalize_insurer` passam a ler **deste mapa**, e as duas
listas velhas (`SLUGS_DE_SEGURADORA` em `vidros_apifirst.py:102-106` e
`_INSURER_ALIASES` em `portal_params.py:68-88`) morrem. ⛔ **Não se cria um terceiro
mapa ao lado: consolida-se e migra-se** (CLAUDE.md §5).

**Gate P0-4:** G3 da §8 — **ZERO slug que o portal não conhece**, e o par
`sompo → GRUPO_HDI` num teste com o comentário que diz **por que está certo**, para
que a próxima pessoa não o "conserte".

---

### P0-5 · O slot bloqueante `cidade_para_o_servico` — e as três verdades

**Por que é bloqueante.** 📊 A cidade é campo obrigatório do PATCH (`CodigoCidade`,
não-nulo nas duas capturas: `8350` e `8214`), e **a Regina pergunta a cidade em 8 de
8 blocos do .docx** — é a única pergunta, além da data, que aparece em todos.
🔴 **O CEP da InfoCap é o de casa do segurado, não o da cidade onde ele quer o
serviço.** Quem quebra o vidro viajando conserta onde está, não onde mora.

**O caminho de dado**, todo já existente e hoje nunca chamado:

```
GET /ufs                    → a lista de UFs                       (EP_UFS)
GET /cidades?UF=&ExibeMunicipios=&PolidorFarol=
                            → as cidades daquela UF                (EP_CIDADES)
GET /clientes/cidades?CodigoCidade=&CodigoTipoScript=&CodigoScript=&Chassi=&Reembolso=
                            → há rede credenciada nessa cidade?    (EP_CLIENTES_CIDADES)
```

**O contrato do slot:** uma `Pergunta` nova em `_UNIVERSAIS`
(`perguntas_do_portal_de_vidros.py:199-276`), com `de_quem=DO_SEGURADO`, **sem**
`aceita_nao_sabe` (numa cidade não existe "não sei" honesto), e o campo entra em
`TRANSPORTAVEIS` (`portal_params.py:43-60`) para que o agente seja **cobrado** por
ele antes de o portal abrir.

💭 A copy proposta (o executor ajusta ao tom do agente; a régua de língua da
EXTRA-001.2 vale):

> *"Em qual cidade você quer fazer o serviço? (pode ser diferente da cidade onde
> você mora — é onde vai ficar mais fácil pra você levar o carro)"*

**E a reconciliação das três verdades.** 📊 Hoje três lugares dizem coisas
diferentes sobre o que o agente precisa ter antes de chamar o portal:

| lugar | o que diz | 📊 |
|---|---|---|
| `app/core/prompts.py:133` | "Você só precisa de: CPF + DATA + o RELATO" | 3 coisas |
| `app/agents/tools/portal_params.py:43-60` | `TRANSPORTAVEIS` — o que **trava** de verdade | 6 campos |
| `app/agents/tools/portal_tool.py:125-135` | a `description` da tool: CPF, data, peça, como, onde **e** as específicas | tudo |

🔴 **O prompt é o que o modelo lê primeiro, e é o mais errado dos três.** Ele manda
chamar com 3 coisas; o `build_portal_params` recusa por falta de 6
(`portal_params.py:178`); e o agente recebe de volta uma mensagem pedindo o que o
prompt disse que não precisava. É um laço de ida e volta que custa mensagens ao
segurado.

**A verdade única passa a ser `TRANSPORTAVEIS`**, porque é a única das três que é
**código executado**, e as outras duas passam a ser derivadas dela:

```
prompts.py:133      →  aponta para a lista, sem repeti-la em prosa
portal_tool.py      →  a description é GERADA de `TRANSPORTAVEIS` + a família da peça
portal_params.py    →  continua sendo o dono
```

**Gate P0-5:** G4 da §8 — um teste que lê `TRANSPORTAVEIS` e falha se o texto do
prompt ou da tool listar um campo a mais ou a menos. E ele tem de **conseguir ficar
vermelho**: a mutação acrescenta um campo a `TRANSPORTAVEIS` sem tocar nos textos.

---

## §6 · P1 — o que fecha o ponta a ponta

### P1-1 · Ler e **apresentar** lojas, distâncias, dias e horários — sem clicar

📊 Os quatro contratos, lidos do bundle:

```
GET  agendamentos/opcoes-disponiveis       (sem params)
GET  agendamentos/datas-disponiveis        {CodigoProduto, CodigoCliente, Ano}
GET  agendamentos/horarios-disponiveis     {CodigoCliente, DataAgendamento, CodigoProduto}
POST lojas/consultar-distancias            {CodigoAtendimento, Cep, Uf, Cidade, Logradouro, Bairro}
```

⚠️ **`POST lojas/consultar-distancias` é um POST e NÃO é escrita de negócio** — 📊 na
captura de 14/08 ele roda depois do pedido já criado e devolve distância e tempo.
Ele **não** passa pelo guard como fronteira material; passa pela allowlist de host,
como qualquer leitura. Tratar um cálculo de rota como efeito material seria armar o
guard onde não há nada a desfazer — e treinar a equipe a ignorá-lo.

🔴 **Isto é o que elimina a razão de sortear loja.** `adaptive.py:936-960` explica,
com três motivos medidos, por que o robô não escolhe a loja: *"a lista de lojas só
existe NESTA tela. O segurado nunca a viu."* **P1-1 faz a lista existir na conversa.**
A decisão continua sendo do segurado; o que muda é que ele passa a ter o que
decidir.

💭 A copy proposta, uma mensagem só:

> *"Seu pedido está aberto — protocolo XXXXXXXX. Franquia de R$ XXX,XX.*
> *Agora é só escolher onde consertar:*
> *1️⃣ AUTOGLASS Centro — Rua Tal, 555 — 4,2 km (12 min) — tem agenda quinta e sexta*
> *2️⃣ AUTOGLASS Sul — Av. Outra, 120 — 9,8 km (21 min) — tem agenda amanhã*
> *Me diz o número e o dia que prefere."*

**Gate P1-1:** a partir do agregado do HAR de 14/08 (que tem a lista real de lojas),
o motor produz uma mensagem que contém **nome, endereço e distância de cada loja**,
e **nenhuma loja que não esteja no agregado**.

---

### P1-2 · Agendar e direcionar — atrás de flag **e** de aprovação humana

📊 Contratos do bundle, **ambos CANDIDATE** (SPEC-077): zero exercícios em 4 HAR.

```
POST agendamentos      {CodigoCliente, DataDeAgendamento, Horario, CodigoProduto,
                        QuantidadeTempoServico, QuantidadeTempoPermanencia, Encaixe}
POST direcionamentos   {CodigoCliente, CodigoProduto, TipoCredenciado}
```

**A trava é dupla, e as duas precisam estar verdes:**

```
1. PORTAL_EFEITO_MATERIAL_LIBERADO  ligado para ESTE job (o freio da SPEC-073)
2. uma Approval humana vinculada    (`approval_requests` — o que o GLOSSARIO chama
                                     de Approval, e não é frase de prompt)
```

🔴 **E a terceira, que é a da SPEC-077:** enquanto o endpoint estiver `CANDIDATE`, a
chamada **não sai**, mesmo com as duas travas verdes. A promoção a `APPROVED` é
`portal_factory.py lab api-infer` sobre a captura nº 1 + `lab promote`, com o gate
humano. **Escreve-se o código contra o contrato do bundle; libera-se contra a
captura.**

💭 Como se promove, quando a captura nº 1 chegar (o executor deixa isto escrito no
relatório, para quem for fazer):

```bash
python backend/scripts/portal_factory.py lab api-infer \
  --arquivo "<captura-1>.har" \
  --arquivo "docs/intake/materiais/portal-vidros/YELUM/YELUM 1/abraseuatendimento.com.br.har" \
  --host abraseuatendimento.com.br --saida <dir>
python backend/scripts/portal_factory.py lab promote --estado OBSERVED ...
```

**Gate P1-2:** G5 da §8 — um teste que prova que, com as duas flags **ligadas** e o
endpoint `CANDIDATE`, o `POST agendamentos` **não sai**. Mutação: promover o
endpoint no fixture e ver o teste ficar vermelho (porque aí ele sai).

---

### P1-3 · Perguntas por família — saindo de `PECAS_SEM_ESPECIFICAS_MAPEADAS`

📊 Hoje `perguntas_do_portal_de_vidros.py:355` declara cinco famílias sem perguntas:
`("vigia", "retrovisor", "farol", "lanterna", "teto")`. O .docx da Regina tem as
perguntas de quatro delas.

🔴 **E o achado que reorganiza tudo (diagnóstico §10.4): a maioria das perguntas da
Regina não é o questionário do portal — é o que decide QUAL PEÇA DO CATÁLOGO
escolher.** Capa pintada ou fosca, com pisca, bipartida da mala ou da lateral: cada
resposta é uma **linha diferente** da lista de `itens-cobertos`.

Isso muda para onde a resposta vai:

```
pergunta que escolhe a PEÇA   → entra em `CodigoItemCoberto` no PATCH (P0-1)
pergunta do QUESTIONÁRIO 80%  → entra em `PerguntasResposta` (o motor que já existe)
```

**O contrato:** as famílias entram em `_ESPECIFICAS_POR_IDENTIDADE`, e cada
`Pergunta` ganha um campo novo que diz **para onde a resposta vai**:

```python
DESTINO_CATALOGO     = "catalogo"       # restringe itens-cobertos
DESTINO_QUESTIONARIO = "questionario"   # responde o 80%
```

As famílias e as perguntas, 📊 do .docx (64 parágrafos, 8 blocos, **23 perguntas
distintas**):

| família | perguntas | destino |
|---|---|---|
| **para-brisa** | posição · tamanho · sensor de chuva · faixa degradê · ADAS | questionário — 🟡 **a confirmar na captura nº 1** |
| **porta** | lado · dianteira/traseira · película · fixo × sobe-e-desce | as 3 primeiras = questionário 📊 medido; **fixo/sobe-desce = catálogo** (decide `VIDRO DE PORTA` × `VIDRO DE JANELA` × `MÁQUINA`) |
| **vigia** | película · desembaçador térmico | questionário — 🟡 a confirmar |
| **retrovisor** | lado · capa pintada/fosca · pisca · regulagem · capa na peça | **catálogo** — a lista traz `RETROVISOR COMPLETO PINTADO COM PISCA`, `CAPA DE RETROVISOR…`, `LENTE…`, `PISCA…` |
| **farol** | lado · tipo (convencional/LED/xenon/milha) | **catálogo** — `FAROL PRINCIPAL XENON`, `FAROL PRINCIPAL LED ORIENTADO POR CÂMERA`, `FAROL MILHA/NEBLINA` |
| **lanterna** | lado · bipartida mala × carroceria · lâmpada | **catálogo** |
| **para-choque** | dianteiro/traseiro · pintado × sem pintura | **catálogo** |
| **lataria** | quais peças (lista) · mesmo evento | catálogo multi-peça + `EventoComposto` |

🔴 **O que NÃO se inventa:** as perguntas de **para-brisa** e **vigia** que ainda não
foram vistas numa tela. Elas entram marcadas como não-confirmadas e o agente as faz
— porque a Regina já as faz e elas não custam nada — **mas a resposta não é enviada
ao questionário do portal enquanto não houver captura**. Ver §14.

**Gate P1-3:** G6 — as **23 perguntas distintas do .docx** casam com um slot
existente, com nome e família. Mutação: apagar a família `retrovisor` do mapa.

---

### P1-4 · Desambiguação guiada pelo catálogo — ler ANTES de perguntar

🔴 **Hoje o código lê `itens-cobertos` e `motivos-dano` DEPOIS de já ter cobrado tudo
do segurado.** 📊 E o catálogo **varia por apólice, não por seguradora**:

| captura | itens | categorias | motivos da 1ª peça |
|---|---|---|---|
| Yelum, 09/09 | 21 | `L`, `V` | 7 |
| Yelum, 14/08 | 30 | `L`, `U`, `V` | 12 |
| Porto, 15/08 | 21 | `V` | 14 |

**Duas apólices da mesma seguradora, 21 × 30 itens.** Decorar catálogo é errado por
construção — e **perguntar antes de ler também é**: se a apólice só tem 21 itens sem
categoria `U`, perguntar sobre roda desperdiça mensagem e cria expectativa.

**O contrato — a regra de ouro:**

```python
def perguntas_que_restringem(itens_cobertos: list, familia: str) -> List[Pergunta]:
    """Das perguntas da família, só as que separam ≥ 2 itens DESTE catálogo.

    Se o catálogo desta apólice tem um único FAROL, não se pergunta o tipo:
    a resposta não muda nada e custa uma mensagem ao segurado.
    """
```

⚠️ **A ordem real depende da resposta Q-B do BLOCO 0.** Se `itens-cobertos` exigir o
Token, a desambiguação acontece **entre as duas fronteiras** — read-only para `V`, e
**depois do efeito** para `L`. Nesse caso, para `L`, a desambiguação sai do catálogo
genérico da seguradora, não do da apólice.

**Gate P1-4:** com o catálogo de 21 itens, a pergunta "qual tipo de farol?" **não é
feita**; com o de 30, é. Dois casos, veredito oposto.

---

### P1-5 · Lataria como caminho próprio

📊 O que a lataria tem de diferente, medido:

```
CodigoItemCoberto ............. categoria `L`     (ex.: "1|142|S|11335|1|0|L")
multi-peça .................... ServicosMartelinhoLataria: [{CodigoServico, CodigoObjetoCausa}, …]
                                📊 2 serviços na captura de 09/09
mesmo evento .................. EventoComposto
catálogo de serviços .......... GET atendimentos/servicos-itens?CodigoScript=&CodigoTipoScript=
tamanho do amassado ........... GET atendimentos/servicos-detalhes
                                📊 [MENOR QUE 05cm | ENTRE 5 E 20cm | MAIOR QUE 20cm]
sem questionário 80% .......... 📊 zero POST /questionarios na captura inteira
sem escolha de loja ........... 📊 GET agendamentos/opcoes-disponiveis devolveu:
                                {"DisponibilizarAgendamento": false,
                                 "IrParaConclusaoDeAtendimento": true,
                                 "ExisteOrdemServico": true, "OpcoesAgendamento": []}
comprovante ................... POST atendimentos/emitir-atendimento-formalizado/{codigo}
```

🔴 **A descoberta que evita um hardcode:** o robô **não precisa saber** que lataria
não tem agendamento. **O portal diz.** `DisponibilizarAgendamento: false` +
`IrParaConclusaoDeAtendimento: true` é a instrução, legível por máquina, e vale para
qualquer peça que um dia se comporte assim. ⛔ **Não escrever
`if categoria == "L": nao_perguntar_loja`.** Ler a resposta.

E o que isso muda na conversa: 💭 *"Nesse tipo de reparo a seguradora é que indica a
oficina — ela te manda o endereço por e-mail e SMS. Não precisa escolher nada."*
📊 É literalmente o que a Regina escreve no .docx (parágrafos 50 e 57).

**Gate P1-5:** o replay da lataria chega ao `emitir-atendimento-formalizado` e
**nunca** pergunta loja nem domicílio.

---

### P1-6 · Vistoria e fotos — o segundo caminho de `page.evaluate`

📊 Dois contratos, do bundle:

```
GET  atendimentos/vistoriamobile?telefone=<telefone>   → gera o LINK que a Regina cola à mão
POST atendimentos-fotografias/web                      → MULTIPART
     FormData: "CodigoAtendimento" + N× "Imagens"
     transformRequest: angular.identity, headers: {"Content-Type": undefined}
```

🔴 **`SessaoVidros.chamar` só sabe JSON** (`vidros_sessao.py:108-121`:
`JSON.stringify(corpo)` e `Content-Type: application/json`). Multipart exige um
**segundo caminho de `page.evaluate`** que monte um `FormData` no browser e **deixe o
`Content-Type` em branco**, para o browser escrever o `boundary`.

```python
async def enviar_fotografias(self, *, codigo_atendimento: str,
                             imagens: List[bytes]) -> Dict[str, Any]:
    """O ÚNICO caminho multipart da sessão. Mesma allowlist, mesmo teto."""
```

⛔ **Não instalar `requests`/`httpx`, não abrir socket, não trocar de transporte.** O
motivo está no docstring de `vidros_sessao.py:11-16`: é a mesma sessão, o mesmo
cookie, o mesmo app.

📊 **E a razão de nunca termos visto isto funcionar está medida:**
`PermiteVistoriaMobile: false` e `LinkVistoriaMobile: ""` em **todas** as capturas —
a seguradora não habilitou vistoria naquelas apólices. `vidros_api.py:345-370` já
documenta isso e já recusa inventar o link. **Aqui se escreve o caminho; a captura
nº 3 da Regina o liga.**

**Gate P1-6:** com `PermiteVistoriaMobile: false`, o motor **não** chama
`vistoriamobile` e **não** promete link. Com `true` (fixture), chama uma vez e o link
entra em `evidence["link_vistoria"]` — a chave que `adaptive.py:132-141` já espera.

---

## §7 · P2 — o que fecha as bordas

### P2-1 · Uma régua só para o trincado

📊 Hoje existem três números, e **dois deles são sobre coisas diferentes**:

| onde | valor | é sobre |
|---|---|---|
| `vidros_lanternas.py:331-333` `_LIMITE_CM = 10.0` | 10 cm | **trincado de para-brisa** — 📊 a própria pergunta do portal diz 10 cm (mapa §4) |
| `.docx` da Regina, parágrafo 15 | moeda de 1 real (≈ 2,7 cm) | **trincado de para-brisa** — mesma coisa, outro número |
| `GET atendimentos/servicos-detalhes` | 5 cm / 20 cm | 🔴 **amassado de LATARIA** — 📊 a chamada roda na captura de lataria, não na de vidro |

🔴 **Duas réguas legítimas e uma contradição real.** A contradição é 10 cm × moeda de
1 real, e ela decide **troca × reparo** — ou seja, qual serviço o vidraceiro vai
prestar. 5/20 cm não entra na conta: é outra peça.

**A regra:** a régua do trincado **vem do portal ou não existe**. O texto da pergunta
chega em `DescricaoPergunta` / `DescricaoResposta` do `POST /questionarios/perguntas`,
e é dele que se extrai o limite. Enquanto não houver a captura nº 1 (que traz o
questionário do para-brisa), o agente pergunta em **linguagem do segurado** e deixa o
portal decidir:

💭 *"A trinca é maior ou menor que um cartão de crédito?"* — e a resposta casa com a
opção real da tela por `match_option`, que é o que o código já faz para "como
ocorreu" (`perguntas_do_portal_de_vidros.py:214-222`).

**Gate P2-1:** G7 — um teste que exige **ZERO** limite numérico de trincado escrito no
código quando a régua não veio do portal. Mutação: reintroduzir `_LIMITE_CM = 10.0`
no caminho do para-brisa e o teste fica vermelho.

---

### P2-2 · `abandonar` e `cancelar` como journeys reais

📊 A Regina cancelou ou abandonou em **2 de 3** acionamentos. O contrato medido:

```
PUT   atendimentos/cancelar   {codigoMotivoCancelamento, codigoAtendimento,
                               observacaoMotivoCancelamento}
GET   atendimentos/motivos-cancelamento   → a lista de motivos (nunca decorar)
PATCH atendimentos/abandonar              (declarado no bundle; zero capturas)
```

`vidros_estado.py:234-235` já tem `FRONTEIRA_CANCELAR` e `FRONTEIRA_ABANDONAR`, e
`ESTADOS` já tem `CANCELADO` e `ABANDONADO` (`:60-61`). 🔴 **São fronteiras materiais
e passam pelo guard como qualquer outra** — cancelar um pedido é um efeito que sai do
prédio.

⚠️ **`abandonar` fica CANDIDATE** (zero capturas). `cancelar` está medido e pode ser
`APPROVED` pela escada da SPEC-077.

---

### P2-3 · Bradesco — D-PILOTO-17, e nada além

```
✅ o que esta SPEC faz:  o slug `bradesco` existe no bundle e no GET /seguradoras/
                         (📊 código `BRADESCO`, rota `bradesco`). Ele entra no mapa
                         único de P0-4 como qualquer uma das 38, e o preflight
                         read-only pode ser exercido.
⛔ o que esta SPEC NÃO faz: uma linha de código para `agendeseuservico.com`.
🧑 o que destrava:        a captura dupla da §4.4 do roteiro da Regina.
```

---

### P2-4 · O Vigia continua cobrindo vidros

📊 `app/tasks/vigia_do_portal.py:306` filtra `.eq("portal_key", "vidros_lanternas")`.
🔴 **Se qualquer bloco desta SPEC criar um `portal_key` novo, o Vigia para de ver os
jobs de vidros no dia seguinte, em silêncio.**

**A regra:** a `portal_key` continua `vidros_lanternas`. Se o executor concluir que
precisa de outra, o Vigia muda **no mesmo commit**, e o gate G8 prova.

---

## §8 · Os guardas e as mutações — 8 novos, teto de 12 (D-PILOTO-14)

🔴 **Todo guarda roda sobre o MOTOR e sobre o ACERVO real** (CLAUDE.md §9.4).
⛔ Proibido teste que reimplementa a regra: se o teste chama um regex ou uma
constante em vez da função, ele guarda o regex, não o comportamento.

| # | o guarda | o que ele chama | a mutação que o deixa **vermelho** |
|---|---|---|---|
| **G1** | **Replay do HAR da Yelum lataria pelo motor** produz a mesma sequência de 7 escritas e o mesmo corpo de PATCH (8 chaves) | `abrir_atendimento_api` inteiro, contra um fixture derivado do HAR por `lab har` | acrescentar `"ItemRemovido": None` ao corpo → 9 chaves ≠ 8 |
| **G2** | A fronteira material é **calculada**, não fixa | `ST.fronteira_materializar_de` + `guard.acao_material_esperada` no fluxo real | trocar a chamada por `ST.FRONTEIRA_MATERIALIZAR` fixo → o caso `L` fica vermelho |
| **G3** | **ZERO** slug desconhecido pelo portal; e `sompo → GRUPO_HDI` está certo | `API.slug_da_seguradora` sobre os 43 do bundle e os 38 da API | "corrigir" `GRUPO_HDI` para `SOMPO` no mapa |
| **G4** | As três verdades dizem a **mesma** coisa | lê `TRANSPORTAVEIS` e confere contra o texto de `prompts.py` e da tool | acrescentar um campo a `TRANSPORTAVEIS` sem tocar nos textos |
| **G5** | Endpoint `CANDIDATE` **não sai**, mesmo com as duas flags ligadas | o caminho de `POST agendamentos` com o freio ligado e Approval concedida | promover o endpoint a `APPROVED` no fixture → ele sai, e o teste vira vermelho |
| **G6** | As **23 perguntas do .docx** casam com slot existente, com nome e família | `o_que_falta` + `_ESPECIFICAS_POR_IDENTIDADE`, sobre o texto real do .docx | apagar a família `retrovisor` do mapa |
| **G7** | A régua do trincado **vem do portal** — ZERO limite numérico no código | varre o caminho do para-brisa procurando literal de cm | reintroduzir `_LIMITE_CM = 10.0` naquele caminho |
| **G8** | O Vigia enxerga a `portal_key` que a journey grava | `vigia_do_portal.diagnosticar` sobre um job gravado pelo caminho novo | trocar a `portal_key` da journey sem mexer no Vigia |

**Sobram 4 do teto.** ⚠️ Eles são para o que o painel achar — não para preencher.
Um candidato natural (G9): **desligar `PORTAL_VIDROS_API_FIRST` devolve exatamente o
comportamento de hoje** (a propriedade de rollback da §11).

🔴 **A regra da mutação (protocolo §10):** roda em **worktree próprio ou com lock
exclusivo**, restaura por **cópia** (nunca `git checkout`), e o orquestrador **não
roda a bateria inteira** enquanto um juiz muta.

---

## §9 · Migrations

**📊 Nenhuma migration é necessária para P0 e P1.** Todo o estado desta SPEC já cabe
em colunas existentes:

```
portal_jobs.params · portal_jobs.evidence        (jsonb, já usados)
approval_requests                                 (a Approval de P1-2 — tabela existente)
o checkpoint durável da SPEC-073                  (já usado por `_checkpoint`)
```

🔴 **Se o executor concluir que precisa de SQL**, a regra é inteira e sem atalho:
leitura obrigatória de [`MIGRATIONS-AUTHORITY.md`](../MIGRATIONS-AUTHORITY.md),
diretório `backend/supabase/migrations/`, idempotente, expand-first, e **APPLY /
VERIFY / ROLLBACK escritos ANTES de rodar**. ⚠️ Uma migration que altera dado,
estrutura, trava ou quem pode ler dispara o piso CRÍTICO do protocolo §3.2 — esta
SPEC já é CRÍTICA, então não muda a marcha; muda a lente do painel.

---

## §10 · O canário controlado em produção

> 🔴 **Este é o gate que nenhum teste substitui.** Build verde não prova que a
> aplicação sobe (CLAUDE.md §9.1); teste verde não prova que o portal aceita.

### 10.1 O que é

**Um acionamento de LATARIA na Yelum, com o veículo de teste do Founder, do WhatsApp
ao comprovante.**

📊 **Por que lataria, e não vidro:** é o único ramo **fechável hoje**. 100% do fluxo
está medido, do preflight ao `emitir-atendimento-formalizado`, e **não existe escolha
de loja nem agendamento** — que é exatamente a parte que depende da captura nº 1.

### 10.2 ANTES

```
[ ] 🧑 o Founder confirma que o veículo de teste tem apólice Yelum ATIVA com
       cobertura de lataria/martelinho (o preflight dirá; confirmar antes evita
       gastar o canário num 400)
[ ] 🧑 o Founder confirma o CPF do titular (entra em variável de ambiente, nunca em
       arquivo versionado, nunca no chat)
[ ] 🤖 PORTAL_EFEITO_MATERIAL_LIBERADO ligado SÓ para este job (ver Q-A do BLOCO 0)
[ ] 🤖 PORTAL_VIDROS_API_FIRST ligado SÓ para este job
[ ] 🤖 a saída dos três comandos de verificação da §1.2, colada no relatório
```

🔴 **"Só para esse job" é uma exigência, e a SPEC não presume que exista.** É a
pergunta Q-A do BLOCO 0. Se o freio for global, ligá-lo abre a porta para todos os
jobs de vidros em voo — e aí nasce o bloco P0-6 (**BLOCKER**, via `CHANGE-ADDENDA`):
uma allowlist de job ou de CPF, como a `BILLING_CANARIO_ALLOWLIST` já faz na
cobrança.

### 10.3 Os casos

```
Q1  o segurado (TESTE-A) descreve o dano de lataria em linguagem natural
Q2  o agente pergunta SÓ: data · quais peças · rodovia/urbano · cidade · relato
    ⛔ não pergunta placa, chassi, CEP, endereço, versão (vêm da InfoCap)
    ⛔ não pergunta loja nem domicílio (o portal disse DisponibilizarAgendamento:false)
Q3  o preflight passa (cobertura existe)
Q4  as 4 escritas saem na ordem: POST /atendimentos → PUT corretores →
    POST solicitantes → PATCH (com ServicosMartelinhoLataria de ≥ 2 peças)
Q5  o GET /atendimentos devolve CodigoAtendimento — e o agente o entrega ao segurado
    na mensagem única do prompt (bloco "AVISAR O QUE FICOU DECIDIDO")
Q6  o comprovante é emitido e chega ao segurado
Q7  o dossiê no grupo da corretora diz o que aconteceu, em língua humana
```

### 10.4 DEPOIS

```
[ ] 🤖 desligar as duas variáveis imediatamente, e provar por comando
[ ] 🤖 colar em §6 do relatório: a trilha de `resumo_para_evidencia` (path sem query),
       o estado final, o CodigoAtendimento MASCARADO (4 últimos dígitos)
[ ] 🧑 o Founder confirma que o e-mail/SMS da seguradora chegou com a loja indicada
[ ] 🧑 Regina/Saionara leem a conversa inteira e dizem se ela soa humana
       (a régua de língua da EXTRA-001.2 vale aqui)
[ ] 🤖 se o pedido precisar morrer, é por `PUT /atendimentos/cancelar` (P2-2), nunca
       fechando a aba — 📊 é o que o roteiro da Regina §2 manda, pelo mesmo motivo
```

🔴 **Se o canário falhar depois do `POST /atendimentos`, existe um pedido real na
Yelum.** O caminho é cancelar pelo portal e registrar. ⛔ **Nunca reexecutar** —
`safe_to_retry_open` (`vidros_estado.py:109-118`) responde `False`, e ele está certo.

---

## §11 · Entrega e implantação

```bash
# a entrega é o PUSH, nunca o commit (CLAUDE.md §2)
git rev-list --count origin/main..HEAD          # o que ainda não subiu
git merge-base --is-ancestor origin/main HEAD && git push origin HEAD:main
# a saída do push vai COLADA no relatório
```

**Serviços a implantar no EasyPanel, nesta ordem:** `smith-api` (a tool, o prompt e o
catálogo de perguntas) → `portal-worker` (a journey e a sessão). ⚠️ O worker é quem
fala com o portal: implantá-lo **antes** da API deixa uma janela em que o agente pede
o que o worker ainda não sabe fazer.

**Variáveis de ambiente — nome, sem valor:**

| variável | para quê | estado desejado após a SPEC |
|---|---|---|
| `PORTAL_VIDROS_API_FIRST` | liga o caminho API-first | **desligada** em produção; ligada só no canário |
| `PORTAL_EFEITO_MATERIAL_LIBERADO` | o freio da SPEC-073 | **desligado**; ligado só no canário, e só para o job |
| `PORTAL_VISION_MODEL` | o cérebro do caminho DOM | inalterada — ⚠️ mas ver a autópsia do mapa §8 (é `gpt-4o-mini` por padrão) |

**Rollback, em uma linha:** desligar `PORTAL_VIDROS_API_FIRST`. 📊 O desenho já
garante isso — `vidros_lanternas.abrir_atendimento` segue exatamente o caminho de
hoje com a flag desligada (`vidros_apifirst.py:6-9`). **Nenhum bloco desta SPEC pode
quebrar essa propriedade.**

---

## §12 · Documentação e acompanhamento — obrigatórios

```
[ ] relatório em docs/canon/reports/, pelo template, ABRINDO com o EXECUTION CARD
    (protocolo §0.1: relatório sem card = SPEC aberta)
[ ] PENDENCIAS.md: P-PILOTO-07 e P-50 re-julgadas — FECHADA (com a prova) ·
    CONTINUA (com o que destrava) · MORREU. E as pendências novas (as capturas que
    faltarem; o freio por job, se ele não existir)
[ ] FOUNDER-DECISIONS.md: só se aparecer decisão nova. D-PILOTO-17 já está lá.
[ ] O-PORTAL-DE-VIDROS-TELA-POR-TELA.md: ele é "a autoridade sobre o que o portal
    pergunta" e está de 06/07. 🔴 Atualizar com o que esta SPEC mediu — ou ele passa
    a mentir para o próximo leitor (CLAUDE.md §12.1, o corolário)
[ ] ESTADO-DAS-SPECS.md e o dossiê do Founder
[ ] CHANGE-ADDENDA.md: tudo que sair do §2.1, classificado, ANTES de executar
```

---

## §13 · O que o estado da arte faz, e o que modelamos

> 🔴 Protocolo §7.3. Cada uma em quatro linhas, e uma quinta dizendo **como o juiz
> inspeciona**. ⚠️ A data de reabertura é do **pesquisador da execução**: ele abre
> cada uma, diz se envelheceu e se há melhor.

**1. Especificação HAR 1.2 (W3C Web Performance)** · `https://w3c.github.io/web-performance/specs/HAR/Overview.html`
- **O que faz:** define o formato que o DevTools exporta — `log.entries[]`, `request.postData.text`, `response.content.text`.
- **O que MODELAMOS:** um ponto — que `response.content.text` só existe no export **"with content"**, e que sem ele o arquivo é uma lista de portas fechadas. É por isso que o roteiro da Regina insiste nessa opção, e por isso o `lab har` denuncia `har_sem_corpos`.
- **O que REJEITAMOS:** usar o HAR como fonte de verdade permanente. Ele é uma **observação datada**, não um contrato — é a razão da escada OBSERVED → CANDIDATE → APPROVED.
- **Como o juiz inspeciona:** abre a spec, confere que `content.text` é opcional, e roda `lab har` sobre um HAR do acervo para ver o campo `har_sem_corpos`.

**2. RFC 5789 — PATCH Method for HTTP** · `https://www.rfc-editor.org/rfc/rfc5789`
- **O que faz:** define `PATCH` como aplicação de uma **modificação parcial**, e diz que o servidor decide como interpretar o documento de patch.
- **O que MODELAMOS:** um ponto — **omitir é diferente de mandar `null`**. É a regra do corpo de 8 × 11 chaves de P0-1, e não é detalhe de estilo: é a diferença entre "não mexi neste campo" e "apague este campo".
- **O que REJEITAMOS:** a ideia de que `PATCH` é seguro por ser parcial. 📊 Aqui ele é a fronteira material da lataria.
- **Como o juiz inspeciona:** abre a §2 da RFC e compara com o corpo do HAR e com o corpo que o motor produz.

**3. Idempotency keys da Stripe** · `https://docs.stripe.com/api/idempotent_requests`
- **O que faz:** um cabeçalho que deixa o cliente repetir uma chamada sem criar uma segunda cobrança.
- **O que MODELAMOS:** um ponto — a **pergunta antes do retry**. Não temos o cabeçalho (o portal não o oferece), mas temos a pergunta que ele responde: *"isto já aconteceu?"* — e ela vive em `safe_to_retry_open` e em `atendimento_aberto_existente`, que é a dedup do **próprio portal**, mais barata que descobrir a duplicidade depois.
- **O que REJEITAMOS:** inventar uma chave de idempotência do nosso lado e achar que ela protege. Ela não chega ao servidor da Maxpar; o que protege é o checkpoint durável da SPEC-073.
- **Como o juiz inspeciona:** abre a doc, e depois lê `vidros_sessao.py:186-194` e `vidros_estado.py:109-118`.

**4. Pact — consumer-driven contract testing** · `https://docs.pact.io/`
- **O que faz:** o consumidor grava o que espera do provedor, e o contrato roda como teste dos dois lados.
- **O que MODELAMOS:** um ponto — o contrato é **gerado da interação real**, não escrito à mão. É exatamente o que `lab api-infer` faz a partir do HAR, e é por isso que esta SPEC proíbe contrato manuscrito.
- **O que REJEITAMOS:** o **provider verification**. Não temos acesso ao servidor da Maxpar e nunca teremos; o lado do provedor é substituído pela escada de promoção e pelo canário.
- **Como o juiz inspeciona:** abre a doc de "consumer contract", roda `lab api-infer` sobre um HAR e compara a forma do que sai.

**5. VCR.py — record & replay de HTTP em teste** · `https://vcrpy.readthedocs.io/`
- **O que faz:** grava respostas HTTP em "cassetes" e as reproduz offline, para o teste não depender de rede.
- **O que MODELAMOS:** um ponto — o **replay offline determinístico** do gate G1. O HAR é o nosso cassete, e ele já existe.
- **O que REJEITAMOS:** a biblioteca. ⛔ O transporte aqui é `page.evaluate` dentro do browser autenticado, não `requests`; instalar VCR seria criar um segundo transporte para agradar ao teste. **O fixture lê o HAR e alimenta um duplo de `page`.**
- **Como o juiz inspeciona:** abre a doc de "record modes", e confere que o fixture de G1 não faz uma única chamada de rede.

**6. `har-to-openapi`** · 🔴 **o pesquisador confirma o repositório canônico na reabertura** (o pacote o nomeia; a proposta não afirma a URL).
- **O que faz (esperado):** converte HAR em OpenAPI inferindo schemas dos corpos.
- **O que MODELARÍAMOS:** nada de novo — `lab api-infer` já faz isto, e é nosso. A referência serve para o juiz **comparar a qualidade da inferência**: se a ferramenta externa infere algo que a nossa não infere, isso é um achado.
- **O que REJEITAMOS:** substituir `lab api-infer`. ⛔ Seria motor paralelo (CLAUDE.md §5).
- **Como o juiz inspeciona:** roda as duas sobre o mesmo HAR e compara a contagem de endpoints e de schemas.

⚠️ **Nenhuma destas referências vira autoridade.** Modela-se o **padrão**; o Tool
Gateway, o Work Run e o portal worker continuam únicos.

---

## §14 · O que depende da captura nº 1 — e o que **não** depende

> 🧑 **A captura nº 1** = para-brisa na Yelum, do início ao **agendamento
> confirmado**, escolhendo LOJA num dia com agenda, HAR *with content*.
> O roteiro está em [`ROTEIRO-DE-CAPTURA-PORTAL-DE-VIDROS.md`](../guias/ROTEIRO-DE-CAPTURA-PORTAL-DE-VIDROS.md) §5.

### 14.1 🟢 NÃO depende — fecha nesta SPEC, sem esperar ninguém

```
P0 inteiro          o PATCH · solicitantes · corretores · a fronteira por categoria ·
                    o mapa único de seguradoras · o slot de cidade · as três verdades
P1-1                LER e APRESENTAR lojas, distâncias, dias e horários
                    (📊 a captura de 14/08 já tem a lista de lojas e o calendário)
P1-3 (parcial)      as famílias cujas perguntas são de CATÁLOGO: retrovisor, farol,
                    lanterna, para-choque — a lista de `itens-cobertos` já as prova
P1-4                desambiguação guiada pelo catálogo
P1-5                🔴 LATARIA INTEIRA, até o comprovante
P1-6 (o caminho)    o método multipart e o `vistoriamobile` escritos e desligados
P2-1 · P2-2 · P2-4  régua do trincado · cancelar · o Vigia
🔴 O CANÁRIO        o acionamento de lataria na Yelum, ponta a ponta
```

### 14.2 🟡 DEPENDE — fica escrito, CANDIDATE, e desligado

```
P1-2                `POST agendamentos` e `POST direcionamentos` — é o último clique,
                    e ele nunca foi visto. 📊 Zero exercícios em 4 HAR.
P1-3 (o resto)      as perguntas de PARA-BRISA (chuva · degradê · ADAS) e de VIGIA
                    (desembaçador) — o agente as faz, mas a resposta não vai ao
                    questionário do portal enquanto não houver tela medida
P2-1 (o fecho)      a régua real do trincado, que vem no texto da pergunta do portal
```

### 14.3 A ordem de ataque por seguradora

```
1º  Yelum LATARIA      🟢 fechável hoje — é o canário
2º  Yelum VIDRAÇARIA   🟡 99% hoje · 100% depois da captura nº 1
3º  Porto              mesmo motor + `TipoAtendimento` (📊 já modelado em
                       vidros_api.py:220-248) · 1 captura de confirmação
4º  Azul / Zurich      já têm corredor de WhatsApp para vidros — conferir qual ganha
5º  as outras 34       1 captura de passo 1 + `itens-cobertos` cada (P-50)
6º  Bradesco           🔴 captura dupla ANTES de código (D-PILOTO-17)
```

---

## §15 · A fila — de onde esta SPEC vem e o que ela deixa

**Depende de:** nada em código. 📊 O diagnóstico §12.1 a coloca na posição 9, e a
única dependência real é **externa**: a captura nº 1, para o 100% de vidraçaria.
**Lataria fecha sem ela.**

⚠️ **Uma dependência de qualidade, não de código:** a EXTRA-001.2 ("o agente lê tudo
antes de falar") melhora a régua de língua que o canário usa no passo
"Regina/Saionara leem a conversa". Se a 001.2 já estiver no ar, o canário é mais
honesto. **Não bloqueia.**

**Ela deixa para as seguintes:**

```
EXTRA-001.7 (piloto medido)     o acionamento de vidros passa a contar como sucesso na
                                régua de eficiência de D-PILOTO-13 — ele agora chega
                                ao protocolo sozinho
EXTRA-001.5 (base de produtos)  a cobertura de vidros por nível de assistência ganha
                                fonte real: o preflight do portal responde "tem
                                cláusula" antes de qualquer escrita
SPEC-101 (fábrica de conectores) o portal de vidros vira o segundo caso de uso real da
                                escada da SPEC-077, depois do Cobrador da Allianz
```

---

## §16 · Definição final de conclusão — a lista fechada

**Esta SPEC está concluída quando, e só quando, todos os itens abaixo estiverem
verdes e verificáveis por comando:**

```
[ ] 1. BLOCO 0 remedido, com a saída dos 6 comandos colada no relatório, as três
       perguntas Q-A/Q-B/Q-C RESPONDIDAS, e as divergências em relação a esta
       proposta escritas como emenda

[ ] 2. G1 verde: replay offline do HAR da Yelum lataria produz a MESMA sequência de
       7 escritas e o MESMO corpo de PATCH (8 chaves, não 11)
       · e a mutação que acrescenta `"ItemRemovido": None` o deixa VERMELHO

[ ] 3. G2 verde: `"…|L"` arma a fronteira ANTES do PATCH · `"…|V"` arma antes do
       `POST /questionarios` · e a mutação que volta a constante fixa fica VERMELHA

[ ] 4. G3 verde: ZERO slug desconhecido pelo portal · `sompo → GRUPO_HDI` provado ·
       `ITAU` fora do caminho ativo · Yelum = `LIBERTY` em todo lugar

[ ] 5. G4 · G5 · G6 · G7 · G8 verdes, cada um com a mutação rerodada e a saída colada

[ ] 6. 🔴 O CANÁRIO: 1 acionamento de LATARIA na Yelum, com o veículo de teste do
       Founder, do WhatsApp ao COMPROVANTE — Q1 a Q7 da §10.3 respondidos com saída
       real, e as duas variáveis de ambiente provadas desligadas depois

[ ] 7. A bateria inteira rodada no gate de cada bloco e no fim (2 a 4 vezes na SPEC,
       protocolo §10), com a contagem do diário do conftest no relatório

[ ] 8. `next start` + 1 requisição a `/api/…` SE a SPEC tiver tocado `app/`,
       `middleware.ts`, `next.config.js` ou variáveis de ambiente (CLAUDE.md §9.1)

[ ] 9. `git push origin HEAD:main` com a saída colada · serviços implantados na ordem
       da §11 · rollback provado (desligar a flag volta ao caminho de hoje)

[ ] 10. P-PILOTO-07 e P-50 re-julgadas · pendências novas escritas ·
        `O-PORTAL-DE-VIDROS-TELA-POR-TELA.md` atualizado com o que se mediu

[ ] 11. Declaração escrita de que NENHUM motor paralelo foi criado, item a item
        contra a tabela da §3

[ ] 12. Relatório abrindo com o EXECUTION CARD preenchido, com FATO / INFERÊNCIA /
        RECOMENDAÇÃO separados, e todo número com 📊 ou 💭
```

🔴 **Um item aberto = SPEC aberta.** "Quase tudo verde" não é um estado.

---

*Autoridade: CLAUDE.md · PROTOCOLO-AUTOBROKERS-AAA v11.2 · D-PILOTO-08, 14, 17, 20 ·
diagnóstico §10 (laudo I5) · SPEC-073 (fronteira material) · SPEC-074 (API-first) ·
SPEC-077 (laboratório de portal) · `O-PORTAL-DE-VIDROS-TELA-POR-TELA.md` ·
`ROTEIRO-DE-CAPTURA-PORTAL-DE-VIDROS.md`*
