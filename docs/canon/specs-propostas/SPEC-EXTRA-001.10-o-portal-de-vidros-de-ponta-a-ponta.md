# SPEC-EXTRA-001.10 · O portal de vidros de ponta a ponta

> **Proposta de SPEC** · 13/09/2026 · redigida no chat do diagnóstico (D-PILOTO-20)
> **Origem:** `DIAGNOSTICO-PILOTOS-E-PLANO-EXTRA-2026-09-12.md` §10 (laudo I5) ·
> D-PILOTO-17 · P-PILOTO-07 · P-50 · **Marcha:** CRÍTICO · 3 juízes · 💭 10–14 h
> **Evidência com `arquivo:linha` e comando:** [`…-RESEARCH-PACK.md`](SPEC-EXTRA-001.10-o-portal-de-vidros-de-ponta-a-ponta-RESEARCH-PACK.md)
>
> 📊 medido (data, fonte, comando) · 💭 ilustrativo, **nunca citável como fato** — CLAUDE.md §12.1

---

## §0 · O resultado, o motivo, e o card

### 0.1 O resultado, em uma frase

> **Um acionamento de vidros na Yelum ou na Porto sai do WhatsApp do segurado e chega
> ao comprovante (lataria/martelinho) ou à loja, dia e hora confirmados (vidraçaria),
> sem a Regina — e o agente pergunta só o que o catálogo daquela apólice exige.**

### 0.2 O motivo — o caminho API-first não pode funcionar como está

📊 Medido em 13/09/2026: `vidros_apifirst.py:20-23` documenta, **no docstring**, a ordem
correta (`PUT /atendimentos/corretores` · `POST /solicitantes` · `PATCH /atendimentos` —
"grava peça, causa, local"). E `vidros_sessao.py:139-237` tem 9 métodos, **nenhum
`atualizar_atendimento`** — `grep -c "PATCH" …/vidros_sessao.py` → **0**.

🔴 **O PATCH é o que grava peça, causa, cidade e local.** Sem ele o questionário do
portal não tem de onde nascer — ele deriva do `CodigoItemCoberto`, que só o PATCH grava.
A journey salta do `POST /atendimentos` (`:225`) direto para `QZ.rodar_questionario`
(`:275-279`). **Com `PORTAL_VIDROS_API_FIRST` ligada hoje, o pedido nasce vazio e o
questionário não tem como responder.**

E há um segundo defeito, mais caro porque é silencioso: 📊 **a fronteira do efeito
material muda de lugar por categoria de peça.** Medido nos dois HAR da Yelum, com linha
de controle nos dois sentidos (CLAUDE.md §9.2):

| captura | categoria | `GET /atendimentos` logo **depois** do PATCH |
|---|---|---|
| Yelum lataria, 09/09 | `L` | `CodigoAtendimento = 23232316` — **nasceu no PATCH** |
| Yelum vidro de porta, 14/08 | `V` | `CodigoAtendimento = None` — nasce no `POST /questionarios` |

`vidros_estado.py:233` fixa **uma** fronteira. Para lataria ela arma no lugar errado: o
guard autoriza depois que o pedido já existe. 🔴 **É a receita de um segundo atendimento,
pago, no nome do mesmo segurado** — e o portal não deixa desfazer
(`O-PORTAL-DE-VIDROS-TELA-POR-TELA.md` §3 e §9.5).

### 0.3 As decisões do Founder já incorporadas — não se reabrem

| decisão | o que ela manda aqui |
|---|---|
| **D-PILOTO-17** | Bradesco: **primeiro uma captura no `abraseuatendimento` com o slug `bradesco`**; o `agendeseuservico` só entra se a captura provar recusa. ⛔ **Zero linhas de código para `agendeseuservico` nesta SPEC.** |
| **D-PILOTO-08** | A numeração é **EXTRA-001.10**; não renumera nada. |
| **D-PILOTO-14** | AAA opção B · marcha fixada · **≤ 12 guardas novos** · bateria sobre motor e acervo real. |
| **D-PILOTO-20** | Execução em chat novo, sob AAA opção B, com a marcha do diagnóstico §8. |
| **D-PILOTO-05** | Coleta dirigida: percorrer até a confirmação e **recusar** — em toda seguradora que não seja o canário nomeado. |
| Founder, 02/08 (mapa §6) | A caixa "atualizações via WhatsApp" fica **desmarcada** enquanto o telefone do passo 2 for o da corretora. |
| Founder, 02/08 (mapa §9.2) | **Nunca responder "Não sabe" para destravar tela.** |

### 0.4 🔴 EXECUTION CARD (proposto — o executor reconfirma no BLOCO 0)

```
OUTCOME ......... o acionamento de vidros chega ao comprovante (lataria) ou à loja,
                  dia e hora confirmados (vidraçaria), sem a Regina
RISCO ........... 8 = ALCANCE 3 (o SEGURADO) + REVERSIBILIDADE 3 (sai do prédio: abre
                  pedido no portal) + FREQUÊNCIA 2 (todo acionamento de vidros)
SUPERFÍCIE ...... 2 — vários comportamentos, em lugares que eu listo: journey API-first,
                  sessão HTTP, máquina de estado, catálogo de perguntas, tool do agente,
                  prompt do Core, vigia
PISO APLICADO ... §3.2 "qualquer coisa que ENVIE acionamento" → CRÍTICO no mínimo.
                  A conta já dava CRÍTICO (RISCO 8); o piso confirma.
NÍVEL ........... CRÍTICO
UNIDADES ........ 15 blocos (5 em P0 · 6 em P1 · 4 em P2)
COESÃO .......... P0-1..P0-3 tocam o MESMO contrato (SessaoVidros ↔ vidros_estado ↔
                  vidros_apifirst) → JUNTOS, um dono. P0-4 e P0-5 são disjuntos e podem
                  ir em paralelo. P1 depende de P0 fechado.
PARALELISMO REAL  no máximo 2 escritores: {P0-1..P0-3} e {P0-4, P0-5}. Nunca 3.
                  `vidros_api.py` é ARQUIVO-HUB: UM dono por vez (§3.4).
TIME ............ desenhista da prova (antes do código) · builder por unidade ·
                  verificador mecânico · painel de 3 lentes · red team · integrador ·
                  1 juiz fresco de confirmação+auditoria (§6.1)
REFERÊNCIA ...... interna: `backend/tests/test_a_maquina_de_lavar_vai_ate_o_fim.py`
                  (ponta a ponta, turno a turno) · `MIGRATIONS-AUTHORITY.md` se houver
                  SQL. externa: §13 (6 referências, cada uma inspecionável)
GATES ........... os 12 da §16, cada um com a mutação que o deixa vermelho (§8)
O ELO ........... "a fronteira muda por CATEGORIA" → medi A (lataria: o número nasce no
                  PATCH) · medi B (vidraçaria: não nasce no PATCH, nasce no POST
                  /questionarios) · e medi que B CHEGA em A: o mesmo `GET /atendimentos`,
                  logo após o mesmo PATCH, dá resultado OPOSTO. É a linha de controle.
FAIXA DE RELÓGIO  💭 10–14 h · 💭 1,5–2,5 M tokens de subagentes (teto CRÍTICO §10)
BLOCKER ......... P0 inteiro. Sem ele o API-first está morto (não grava) ou é perigoso
                  (arma a fronteira no lugar errado).
```

---

## §1 · Autorização de testes — o que pode sair, e para quem

🔴 **Esta SPEC abre pedidos em portal de seguradora. Um pedido aberto por engano é um
vidraceiro na porta de um segurado que não pediu.**

```
✅ PERMITIDO
   · replay OFFLINE dos 4 HAR do acervo (nenhuma rede; o motor lê arquivo)
   · leituras do portal (GET /seguradoras, /apolices, /itens-cobertos, /motivos-dano,
     /ufs, /cidades, /clientes/cidades) — nenhuma delas muda nada
   · UM acionamento de LATARIA na Yelum com o VEÍCULO DE TESTE do Founder, no canário
     da §10, com o freio ligado só para esse job

⛔ PROIBIDO, sem exceção
   · qualquer escrita no portal fora do canário nomeado
   · qualquer POST/PUT/PATCH com apólice de segurado real que não seja a de teste
   · qualquer mensagem a segurado ou seguradora fora de TESTE-A / TESTE-B
   · acionar Bradesco, Azul, Zurich ou qualquer uma das 34 restantes (D-PILOTO-17 e a
     ordem de ataque da §14 proíbem código antes de captura)
   · imprimir ou gravar CPF, CNPJ, placa, chassi, telefone, e-mail, nome de segurado,
     ou o campo `Documento` do `PUT /atendimentos/corretores` — ele É um CPF, e o nome
     da chave não o denuncia
```

**A verificação ANTES de cada efeito**, nesta ordem, com a saída no relatório:

```bash
echo "PORTAL_EFEITO_MATERIAL_LIBERADO=${PORTAL_EFEITO_MATERIAL_LIBERADO:-<vazio>}"
echo "PORTAL_VIDROS_API_FIRST=${PORTAL_VIDROS_API_FIRST:-<vazio>}"
python -c "import hashlib,os; print('cpf_hash=',hashlib.sha256(os.environ.get('CANARIO_CPF','').encode()).hexdigest()[:12])"
```

🔴 **Se qualquer uma das três não bater, o bloco para e vai para a caixa do Founder.**
Não é uma das oito paradas do CLAUDE.md §10 — é a trava desta SPEC, e ela vence.

---

## §2 · Escopo, e o que sai de propósito

**Entra:** P0 (o PATCH e os dois pré-requisitos · a fronteira por CATEGORIA · o mapa
único de seguradoras · o slot bloqueante `cidade_para_o_servico` · as três verdades) ·
P1 (ler e APRESENTAR lojas, dias e horários · agendar/direcionar atrás de flag e
aprovação · perguntas por família · desambiguação pelo catálogo · lataria como caminho
próprio · vistoria e fotos) · P2 (uma régua só para o trincado · `abandonar`/`cancelar` ·
Bradesco conforme D-PILOTO-17 · o Vigia cobrindo vidros).

**Sai — com o gatilho que a faz voltar:**

| o que sai | por quê | **o que a faz voltar** |
|---|---|---|
| **Subfluxo de domicílio** (`transportes-proprios/*`, `servicos-moveis/*`, formas de pagamento) | 📊 `AtendeServicoMovel:false` nas duas capturas; zero exercício | **captura nº 2** (domicílio num CEP com cobertura) |
| **`PATCH atendimentos/finalizar`** | declarado no bundle, zero capturas | uma captura que o exerça |
| **`agendeseuservico` (Bradesco)** | 🔴 **D-PILOTO-17 proíbe** código antes da captura dupla | a captura nº 10 dizer que o `abraseuatendimento` recusa |
| **Roda/pneu/suspensão** | 📊 o único HAR morre no preflight 400 (sem cláusula) | captura nº 12 (roda **com** cobertura) |
| **Consultar atendimento / Área do Segurado** | 📊 nunca capturado; é acompanhamento, não acionamento | captura nº 8; é matéria da EXTRA-001.7 |
| **As 34 seguradoras além de Yelum/Porto/Azul/Zurich** | 📊 zero capturas; P-50 | 1 captura de passo 1 + `itens-cobertos` cada |
| **Reescrever o caminho DOM (`vidros_lanternas`)** | funciona e é o fallback; mexer agora é risco sem retorno | nunca nesta SPEC |

🔴 **Escopo não se reduz sem decisão do Founder (D5 / CLAUDE.md §11).** O que sair além
desta tabela vira entrada em [`CHANGE-ADDENDA.md`](../CHANGE-ADDENDA.md), classificada,
**antes** de ser executado.

---

## §3 · As autoridades preservadas — nenhum motor paralelo (CLAUDE.md §5)

| o que a SPEC precisa | o que **já existe** e é reaproveitado | o que NÃO se cria |
|---|---|---|
| falar com a API do portal | `SessaoVidros` — allowlist por chamada, teto de 150 | ⛔ nenhum cliente HTTP novo, biblioteca ou socket |
| autorizar efeito material | `PortalActionGuard` da SPEC-073 | ⛔ nenhum guard próprio de vidros |
| estado de negócio do pedido | `EstadoDoAtendimento` + `ESTADOS` (`vidros_estado.py:44-62`) | ⛔ nenhuma máquina de estado nova |
| motor de perguntas do portal | `vidros_questionario.rodar_questionario` + `SessaoVidros.proxima_pergunta` | ⛔ nenhum motor de questionário paralelo |
| perguntas ao segurado | `perguntas_do_portal_de_vidros.py` (`_UNIVERSAIS`, `_ESPECIFICAS_POR_IDENTIDADE`, `o_que_falta`) | ⛔ nenhuma segunda tabela de perguntas |
| derivar contrato de captura | **SPEC-077** `portal_factory.py lab har\|api-infer\|promote` — a escada OBSERVED → CANDIDATE → APPROVED | ⛔ **nenhum contrato à mão.** A ferramenta existe e nunca foi usada sobre este material |
| vigiar job parado | `app/tasks/vigia_do_portal.py` | ⛔ nenhum vigia novo |
| a rota do agente ao portal | `PortalActionTool` + `build_portal_params` | ⛔ nenhuma tool nova de vidros |

**A regra de ouro:** tudo o que esta SPEC acrescenta é **método novo em classe existente**
ou **constante nova em módulo existente**. 📊 Zero arquivos novos em
`portal_worker/journeys/` — exceto o **fixture de replay offline** do gate G1, em
`backend/tests/`, que não é código de produto.

---

## §4 · BLOCO 0 — converter medindo (antes de qualquer linha)

> Este documento envelhece. 3 linhas citadas pelo diagnóstico já mudaram (RESEARCH-PACK
> §1). **O número do executor vence o meu** (protocolo §5①).

```bash
cd backend
# B0.1 o PATCH continua ausente?
grep -n "atualizar_atendimento\|PATCH" portal_worker/journeys/vidros_sessao.py   # esperado: 0
# B0.2 a fronteira continua fixa?
sed -n '230,240p' portal_worker/journeys/vidros_estado.py
# B0.3 quantos EP_ declarados nunca são chamados?  📊 13/09: 9 (+2 já _NAO_MEDIDO)
for ep in $(grep -o '^EP_[A-Z_]*' portal_worker/journeys/vidros_api.py); do
  n=$(grep -rn "$ep" --include=*.py . | grep -v "vidros_api.py:" | wc -l)
  [ "$n" = "0" ] && echo "NUNCA CHAMADO: $ep"; done
# B0.4 o hardcode de slugs (📊 3 entradas, uma delas ITAU)
sed -n '100,110p' portal_worker/journeys/vidros_apifirst.py
# B0.5 as três verdades sobre o que perguntar
grep -n "portal_action\*\* IMEDIATAMENTE" app/core/prompts.py
sed -n '43,60p' app/agents/tools/portal_params.py ; sed -n '125,136p' app/agents/tools/portal_tool.py
# B0.6 o que o laboratório da SPEC-077 diz do material
PYTHONIOENCODING=utf-8 python scripts/portal_factory.py lab har \
  --arquivo "../docs/intake/materiais/portal-vidros/YELUM/YELUM 1/abraseuatendimento.com.br.har" \
  --host abraseuatendimento.com.br
```

📊 **O que B0.6 tem de reproduzir** (13/09/2026): `354 chamadas · 188 sem ruído · 41
endpoints distintos · 14 de ESCRITA · 29 com forma inferível · 44 respostas JSON com
corpo · host de API: api.autoglass.com.br`. ⚠️ **As "14 escritas" são 7 escritas + 7
preflight `OPTIONS`.** O gate G1 compara as 7. 🔴 **Divergiu? O número do executor vence,
e a SPEC se corrige por emenda escrita.**

### 4.1 Três perguntas que o BLOCO 0 tem de RESPONDER — elas mudam o desenho

```
Q-A  O freio PORTAL_EFEITO_MATERIAL_LIBERADO é POR JOB ou GLOBAL?
     Se global, ligá-lo no canário abre a porta para todos os jobs de vidros em voo.
     Nesse caso nasce o bloco P0-6 (BLOCKER, via CHANGE-ADDENDA): uma allowlist de
     job/CPF, como a BILLING_CANARIO_ALLOWLIST já faz na cobrança.

Q-B  `GET /apolices/itens-cobertos` exige o Token (isto é, exige que o
     `POST /atendimentos` já tenha acontecido)?
     📊 Na ordem BRUTA do HAR o POST vem ANTES do itens-cobertos. Se o catálogo só
     existir depois da fronteira A, a desambiguação de P1-4 acontece ENTRE as duas
     fronteiras — read-only para `V`, e DEPOIS DO EFEITO para `L`. Para `L` ela teria de
     sair do catálogo genérico da seguradora. Isto muda P1-4.

Q-C  O autocomplete do portal lista "Liberty" ou "Yelum"?
     📊 O bundle serve `seguradoras/liberty/` com `<title>Menu Atendimento - Liberty</title>`,
     e `portal_params.py:69-71` traduz LIBERTY → "Yelum", texto que
     `vidros_lanternas.py:1090-1108` DIGITA no `#seguradora-input`. Se o campo lista
     "Liberty", o caminho DOM pode estar clicando na primeira opção de uma busca que não
     casou.
```

---

## §5 · P0 — sem isto o API-first está morto ou é perigoso

### P0-1 · `SessaoVidros.atualizar_atendimento` = `PATCH /atendimentos`

📊 Contrato lido da função `atualizarAtendimento` do bundle (comando no RESEARCH-PACK
§2.3). Assinatura proposta — **FRONTEIRA MATERIAL para categoria `L`**, leitura-e-escrita
para `V`:

```python
async def atualizar_atendimento(self, *,
    codigo_item_coberto: str,     # "1|142|S|11335|1|0|L"  ← a chave composta
    codigo_cidade: int,           # de GET /cidades, pela UF
    codigo_objeto_causa: int,     # de GET /motivos-dano, pela peça
    avaliacao_dano: str,          # o relato — o portal exige mín. 30 chars
    perimetro_dano: str,          # "U" | "R" | "N"  (PRIMEIRA LETRA)
    cep: str = "", codigo_zona: Optional[int] = None,
    item_removido: Optional[bool] = None,     # "O item permanece no veículo?"
    evento_composto: Optional[bool] = None,   # "Mais de um item danificado?"
    polimento_farol: Optional[bool] = None,   # só quando a oferta apareceu
    servicos_martelinho_lataria: Optional[list] = None,  # [{CodigoServico, CodigoObjetoCausa}]
) -> Dict[str, Any]:
```

🔴 **A regra do corpo — o coração do gate G1.** O contrato do bundle tem **11 campos**.
📊 **O que sai no fio, em 2 de 2 capturas, são 8**: `ItemRemovido`, `EventoComposto` e
`PolimentoFarol` **não aparecem**, porque o AngularJS serializa com `JSON.stringify`, que
**descarta chaves `undefined`**. `CodigoZona` sobrevive porque o bundle a escreve com um
ternário explícito para `null`.

```
✅ CERTO   omitir a chave quando o valor é None  → corpo de 8 chaves, igual ao HAR
❌ ERRADO  mandar "ItemRemovido": null           → corpo de 11 chaves, ≠ do HAR
```

Um `null` explícito onde o portal nunca viu um `null` é um campo inventado.
**Onde entra:** `vidros_apifirst.py`, entre o `POST /atendimentos` (`:225`) e o
questionário (`:275`), **e depois de P0-2**.

**Gate P0-1:** o replay offline do HAR da Yelum lataria produz um corpo de PATCH igual ao
capturado — mesmas chaves, mesma ordem, mesmos valores não-PII.

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

🔴 **`RelacaoTitular` é string, e Corretor é `"6"`, não `"4"`.** `vidros_api.py:296-305`
já tem `RELACAO_TITULAR` com `6: "Corretor"` e o comentário que explica por que decorar a
posição da lista dá errado. 📊 A captura de 09/09 mandou `"6"`; a de 14/08 mandou `"5"`
(Outros) — **duas capturas, dois valores, e a nossa escolha é sempre `"6"`**, porque quem
abre é a corretora. 🔴 **`TermoAceito: false` nas duas.** Não inventar `true`.

**Gate P0-2:** o replay produz as 3 escritas nesta ordem, com `RelacaoTitular == "6"` e
`TermoAceito == False`.

### P0-3 · A fronteira material calculada por CATEGORIA

```python
# vidros_estado.py — ao lado das constantes que já existem (:232-238)
def fronteira_materializar_de(codigo_item_coberto: str) -> str:
    """Qual ação NESTA peça faz o pedido existir para o analista.
    📊 categoria `L` → o PATCH materializa (não há POST /questionarios).
       categoria `V` → o PATCH NÃO materializa; o POST /questionarios sim.
    Desconhecida → FRONTEIRA_ABRIR, a mais conservadora: arma antes. Fail-closed.
    """
```

Reaproveita `API.partes_do_item_coberto` (`vidros_api.py:263`), que já quebra a chave
composta, devolve `categoria` (índice 6) e já é fail-closed. A journey passa a nomear ao
guard a fronteira **daquela peça**:
`guard.acao_material_esperada = ST.fronteira_materializar_de(item["CodigoItemCoberto"])`.

🔴 **O guarda que fecha a porta (G2): um teste que fica VERMELHO se
`FRONTEIRA_MATERIALIZAR` voltar a ser consumida como constante fixa dentro da journey.**
Sem ele a regressão é invisível: o código compila, os testes de vidraçaria passam, e só a
lataria quebra — em produção, com dinheiro.

**Gate P0-3:** dois casos, mesma superfície, veredito oposto (protocolo §5):
`"1|142|S|11335|1|0|L"` → autorização pedida **antes do PATCH**;
`"3|129|N|10700|1|0|V"` → autorização pedida **antes do `POST /questionarios`**.

### P0-4 · Um mapa só de seguradora, e ele é o do portal

📊 Medido em 13/09 sobre o HAR de 09/09 e o bundle:

```
GET /seguradoras/ ..... 38 códigos ativos   ·   bundle (rota da SPA) ..... 43 slugs
só no bundle (5) ...... BLLU · GENERALI · GRUPO_HDI · ITAU · ZURICHSANTANDER
só na API ............. 0
o código conhece ...... 3 — PORTO · AZUL · ITAU   (vidros_apifirst.py:102-106)
```

🔴 **Três defeitos, não um:** (1) **`ITAU` está no código e não está entre os 38 ativos** —
existe como rota no bundle, mas a API não o oferece, e o fail-closed de
`slug_da_seguradora` (`:82-97`) fica de pé por acidente para 35 seguradoras e **quebra
justamente para o ITAU**, que passa; (2) **Yelum é `LIBERTY`** — ver Q-C do BLOCO 0,
**medir antes de consertar**; (3) **`sompo` e `SOMPO` são coisas diferentes** — 📊
`GRUPO_HDI: "sompo"` **e** `SOMPO: "sompo-seguros"`, e quem "corrigir" o primeiro roteia
o segurado para a seguradora errada.

**O contrato:** um único mapa em `vidros_api.py` (já é a autoridade de contrato do
portal), derivado da medição, com as duas direções:

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

`slug_da_seguradora` e `normalize_insurer` leem **deste mapa**; as duas listas velhas
(`SLUGS_DE_SEGURADORA` em `vidros_apifirst.py:102-106` e `_INSURER_ALIASES` em
`portal_params.py:68-88`) morrem. ⛔ **Não se cria um terceiro mapa ao lado: consolida-se
e migra-se** (CLAUDE.md §5).

**Gate P0-4:** G3 — **ZERO slug que o portal não conhece**, e o par `sompo → GRUPO_HDI`
num teste com o comentário que diz **por que está certo**, para que a próxima pessoa não
o "conserte".

### P0-5 · O slot bloqueante `cidade_para_o_servico` — e as três verdades

📊 A cidade é campo obrigatório do PATCH (`CodigoCidade`, não-nulo nas duas capturas:
`8350` e `8214`), e **a Regina pergunta a cidade em 8 de 8 blocos do .docx** — a única
pergunta, além da data, presente em todos. 🔴 **O CEP da InfoCap é o de casa, não o da
cidade onde ele quer o serviço.** Quem quebra o vidro viajando conserta onde está.

**O caminho de dado**, já existente e hoje nunca chamado: `GET /ufs` (EP_UFS) →
`GET /cidades?UF=&ExibeMunicipios=&PolidorFarol=` (EP_CIDADES) →
`GET /clientes/cidades?CodigoCidade=&CodigoTipoScript=&CodigoScript=&Chassi=&Reembolso=`
(EP_CLIENTES_CIDADES — *há rede credenciada nessa cidade?*).

**O contrato:** uma `Pergunta` nova em `_UNIVERSAIS`
(`perguntas_do_portal_de_vidros.py:199-276`), `de_quem=DO_SEGURADO`, **sem**
`aceita_nao_sabe` (numa cidade não existe "não sei" honesto), e o campo entra em
`TRANSPORTAVEIS` (`portal_params.py:43-60`) para que o agente seja **cobrado** por ele
antes de o portal abrir. 💭 Copy: *"Em qual cidade você quer fazer o serviço? (pode ser
diferente da cidade onde você mora)"*.

**A reconciliação das três verdades.** 📊 Hoje três lugares discordam:

| lugar | o que diz | 📊 |
|---|---|---|
| `app/core/prompts.py:133` | "Você só precisa de: CPF + DATA + o RELATO" | 3 coisas |
| `app/agents/tools/portal_params.py:43-60` | `TRANSPORTAVEIS` — o que **trava** de verdade | 6 campos |
| `app/agents/tools/portal_tool.py:125-135` | a `description`: CPF, data, peça, como, onde **e** as específicas | tudo |

🔴 **O prompt é o que o modelo lê primeiro, e é o mais errado dos três.** Manda chamar com
3 coisas; `build_portal_params` recusa por falta de 6 (`:178`); e o agente recebe de volta
um pedido do que o prompt disse que não precisava — um laço de ida e volta que custa
mensagens ao segurado. **A verdade única passa a ser `TRANSPORTAVEIS`**, a única das três
que é **código executado**: `prompts.py:133` aponta para a lista sem repeti-la, e a
`description` da tool passa a ser **gerada** de `TRANSPORTAVEIS` + a família da peça.

**Gate P0-5:** G4 — um teste que lê `TRANSPORTAVEIS` e falha se o texto do prompt ou da
tool listar um campo a mais ou a menos. Mutação: acrescentar um campo a `TRANSPORTAVEIS`
sem tocar nos textos.

---

## §6 · P1 — o que fecha o ponta a ponta

### P1-1 · Ler e **apresentar** lojas, distâncias, dias e horários — sem clicar

📊 Os quatro contratos, do bundle:

```
GET  agendamentos/opcoes-disponiveis     (sem params)
GET  agendamentos/datas-disponiveis      {CodigoProduto, CodigoCliente, Ano}
GET  agendamentos/horarios-disponiveis   {CodigoCliente, DataAgendamento, CodigoProduto}
POST lojas/consultar-distancias          {CodigoAtendimento, Cep, Uf, Cidade, Logradouro, Bairro}
```

⚠️ **`POST lojas/consultar-distancias` é POST e NÃO é escrita de negócio** — 📊 na captura
de 14/08 roda depois do pedido criado e devolve distância e tempo. **Não** passa pelo
guard como fronteira material: armar o guard num cálculo de rota treina a equipe a
ignorá-lo.

🔴 **Isto elimina a razão de sortear loja.** `adaptive.py:936-960` explica, com três
motivos medidos, por que o robô não escolhe: *"a lista de lojas só existe NESTA tela. O
segurado nunca a viu."* **P1-1 faz a lista existir na conversa.** A decisão continua sendo
do segurado; o que muda é que ele passa a ter o que decidir. 💭 Copy: uma mensagem só —
protocolo · franquia · lojas numeradas com endereço, km, minutos e os dias com agenda ·
*"me diz o número e o dia."*

**Gate P1-1:** a partir do agregado do HAR de 14/08 (que tem a lista real de lojas), o
motor produz uma mensagem com **nome, endereço e distância de cada loja**, e **nenhuma
loja que não esteja no agregado**.

### P1-2 · Agendar e direcionar — atrás de flag **e** de aprovação humana

📊 Contratos do bundle, **ambos CANDIDATE** (SPEC-077): zero exercícios em 4 HAR.

```
POST agendamentos      {CodigoCliente, DataDeAgendamento, Horario, CodigoProduto,
                        QuantidadeTempoServico, QuantidadeTempoPermanencia, Encaixe}
POST direcionamentos   {CodigoCliente, CodigoProduto, TipoCredenciado}
```

**Três travas, e as três precisam estar verdes:**

```
1. PORTAL_EFEITO_MATERIAL_LIBERADO ligado para ESTE job (o freio da SPEC-073)
2. uma Approval humana vinculada (`approval_requests` — o Approval do GLOSSARIO, e não
   uma frase de prompt)
3. 🔴 o endpoint APROVADO na escada da SPEC-077. Enquanto for CANDIDATE, a chamada NÃO
   SAI, mesmo com 1 e 2 verdes.
```

**Escreve-se o código contra o contrato do bundle; libera-se contra a captura.** 💭 Como se
promove, quando a captura nº 1 chegar (o executor deixa isto escrito no relatório):

```bash
python backend/scripts/portal_factory.py lab api-infer --arquivo "<captura-1>.har" \
  --arquivo "docs/intake/materiais/portal-vidros/YELUM/YELUM 1/abraseuatendimento.com.br.har" \
  --host abraseuatendimento.com.br --saida <dir>
python backend/scripts/portal_factory.py lab promote --estado OBSERVED ...
```

**Gate P1-2:** G5 — com as duas flags **ligadas** e o endpoint `CANDIDATE`, o
`POST agendamentos` **não sai**. Mutação: promover o endpoint no fixture → ele sai, e o
teste fica vermelho.

### P1-3 · Perguntas por família — saindo de `PECAS_SEM_ESPECIFICAS_MAPEADAS`

📊 Hoje `perguntas_do_portal_de_vidros.py:355` declara cinco famílias sem perguntas:
`("vigia", "retrovisor", "farol", "lanterna", "teto")`. O .docx da Regina tem as perguntas
de quatro delas.

🔴 **O achado que reorganiza tudo (diagnóstico §10.4): a maioria das perguntas da Regina
não é o questionário do portal — é o que decide QUAL PEÇA DO CATÁLOGO escolher.** Capa
pintada ou fosca, com pisca, bipartida da mala ou da lateral: cada resposta é uma **linha
diferente** de `itens-cobertos`. Isso muda para onde a resposta vai:

```
pergunta que escolhe a PEÇA   → entra em `CodigoItemCoberto` no PATCH (P0-1)
pergunta do QUESTIONÁRIO 80%  → entra em `PerguntasResposta` (o motor que já existe)
```

**O contrato:** as famílias entram em `_ESPECIFICAS_POR_IDENTIDADE`, e cada `Pergunta`
ganha um campo de destino — `DESTINO_CATALOGO` ou `DESTINO_QUESTIONARIO`. 📊 Do .docx
(64 parágrafos, 8 blocos, **23 perguntas distintas**):

| família | perguntas | destino |
|---|---|---|
| **para-brisa** | posição · tamanho · sensor de chuva · faixa degradê · ADAS | questionário — 🟡 **a confirmar na captura nº 1** |
| **porta** | lado · dianteira/traseira · película · fixo × sobe-e-desce | as 3 primeiras = questionário 📊 medido; **fixo/sobe-desce = catálogo** (decide `VIDRO DE PORTA` × `VIDRO DE JANELA` × `MÁQUINA`) |
| **vigia** | película · desembaçador térmico | questionário — 🟡 a confirmar |
| **retrovisor** | lado · capa pintada/fosca · pisca · regulagem · capa na peça | **catálogo** — a lista traz `RETROVISOR COMPLETO PINTADO COM PISCA`, `CAPA DE RETROVISOR…`, `LENTE…`, `PISCA…` |
| **farol** | lado · tipo (convencional/LED/xenon/milha) | **catálogo** — `FAROL PRINCIPAL XENON`, `…LED ORIENTADO POR CÂMERA`, `FAROL MILHA/NEBLINA` |
| **lanterna** | lado · bipartida mala × carroceria · lâmpada | **catálogo** |
| **para-choque** | dianteiro/traseiro · pintado × sem pintura | **catálogo** |
| **lataria** | quais peças (lista) · mesmo evento | catálogo multi-peça + `EventoComposto` |

🔴 **O que NÃO se inventa:** as perguntas de **para-brisa** e **vigia** nunca vistas numa
tela. Entram marcadas como não-confirmadas, e o agente as faz — a Regina já as faz e não
custam nada — **mas a resposta não vai ao questionário do portal enquanto não houver
captura**. Ver §14.

**Gate P1-3:** G6 — as **23 perguntas distintas do .docx** casam com um slot existente,
com nome e família. Mutação: apagar a família `retrovisor` do mapa.

### P1-4 · Desambiguação guiada pelo catálogo — ler ANTES de perguntar

🔴 **Hoje o código lê `itens-cobertos` e `motivos-dano` DEPOIS de já ter cobrado tudo do
segurado.** 📊 E o catálogo **varia por apólice, não por seguradora**: Yelum 09/09 = **21
itens** (categorias `L`,`V`; 7 motivos) · Yelum 14/08 = **30 itens** (`L`,`U`,`V`; 12
motivos) · Porto 15/08 = 21 itens (`V`; 14 motivos).

**Duas apólices da mesma seguradora, 21 × 30 itens.** Decorar catálogo é errado por
construção — e **perguntar antes de ler também é**: se a apólice não tem categoria `U`,
perguntar sobre roda desperdiça mensagem e cria expectativa.

```python
def perguntas_que_restringem(itens_cobertos: list, familia: str) -> List[Pergunta]:
    """Das perguntas da família, só as que separam ≥ 2 itens DESTE catálogo.
    Se o catálogo desta apólice tem um único FAROL, não se pergunta o tipo: a resposta
    não muda nada e custa uma mensagem ao segurado.
    """
```

⚠️ **A ordem real depende de Q-B do BLOCO 0.** Se `itens-cobertos` exigir o Token, a
desambiguação acontece **entre as duas fronteiras** — read-only para `V`, e **depois do
efeito** para `L`; nesse caso, para `L`, ela sai do catálogo genérico da seguradora.

**Gate P1-4:** com o catálogo de 21 itens, "qual tipo de farol?" **não é feita**; com o de
30, é. Dois casos, veredito oposto.

### P1-5 · Lataria como caminho próprio

📊 O que a lataria tem de diferente, medido:

```
categoria `L` no CodigoItemCoberto  (ex.: "1|142|S|11335|1|0|L")
multi-peça ..... ServicosMartelinhoLataria: [{CodigoServico, CodigoObjetoCausa}, …]
                 📊 2 serviços na captura de 09/09   · mesmo evento: EventoComposto
catálogos ...... GET atendimentos/servicos-itens?CodigoScript=&CodigoTipoScript=
                 GET atendimentos/servicos-detalhes → 📊 [MENOR QUE 05cm | ENTRE 5 E
                 20cm | MAIOR QUE 20cm]   (o tamanho do AMASSADO)
sem 80% ........ 📊 zero POST /questionarios na captura inteira
sem loja ....... 📊 GET agendamentos/opcoes-disponiveis → {"DisponibilizarAgendamento":
                 false, "IrParaConclusaoDeAtendimento": true, "ExisteOrdemServico": true,
                 "OpcoesAgendamento": []}
comprovante .... POST atendimentos/emitir-atendimento-formalizado/{codigo}
```

🔴 **A descoberta que evita um hardcode:** o robô **não precisa saber** que lataria não tem
agendamento. **O portal diz** — a instrução é legível por máquina e vale para qualquer
peça que um dia se comporte assim. ⛔ **Não escrever
`if categoria == "L": nao_perguntar_loja`.** Ler a resposta. 💭 Na conversa: *"Nesse tipo
de reparo a seguradora é que indica a oficina — ela te manda o endereço por e-mail e
SMS."* 📊 É o que a Regina escreve no .docx (§§ 50 e 57).

**Gate P1-5:** o replay da lataria chega ao `emitir-atendimento-formalizado` e **nunca**
pergunta loja nem domicílio.

### P1-6 · Vistoria e fotos — o segundo caminho de `page.evaluate`

📊 Dois contratos, do bundle:

```
GET  atendimentos/vistoriamobile?telefone=<telefone>  → gera o LINK que a Regina cola à mão
POST atendimentos-fotografias/web                     → MULTIPART
     FormData: "CodigoAtendimento" + N× "Imagens"
     transformRequest: angular.identity, headers: {"Content-Type": undefined}
```

🔴 **`SessaoVidros.chamar` só sabe JSON** (`vidros_sessao.py:108-121`). Multipart exige um
**segundo caminho de `page.evaluate`**, que monte um `FormData` no browser e **deixe o
`Content-Type` em branco**, para o browser escrever o `boundary`:
`async def enviar_fotografias(self, *, codigo_atendimento, imagens) -> Dict` — o único
caminho multipart da sessão, mesma allowlist, mesmo teto. ⛔ **Não instalar
`requests`/`httpx`, não abrir socket, não trocar de transporte:** é a mesma sessão, o
mesmo cookie, o mesmo app (`vidros_sessao.py:11-16`).

📊 **A razão de nunca termos visto isto funcionar está medida:** `PermiteVistoriaMobile:
false` e `LinkVistoriaMobile: ""` em **todas** as capturas. `vidros_api.py:345-370` já
recusa inventar o link. **Aqui se escreve o caminho; a captura nº 3 da Regina o liga.**

**Gate P1-6:** com `PermiteVistoriaMobile: false`, o motor **não** chama `vistoriamobile`
e **não** promete link. Com `true` (fixture), chama uma vez e o link entra em
`evidence["link_vistoria"]` — a chave que `adaptive.py:132-141` já espera.

---

## §7 · P2 — o que fecha as bordas

**P2-1 · Uma régua só para o trincado.** 📊 Hoje existem três números, e **dois são sobre
coisas diferentes**: `vidros_lanternas.py:331-333` `_LIMITE_CM = 10.0` (trincado de
para-brisa — a pergunta do portal diz 10 cm) · o .docx da Regina, parágrafo 15, "moeda de
1 real" (mesma coisa, outro número) · `GET atendimentos/servicos-detalhes` 5/20 cm — 🔴
**amassado de LATARIA**, chamado na captura de lataria. A contradição real é **10 cm ×
moeda de 1 real**, e ela decide **troca × reparo**.

**A regra:** a régua do trincado **vem do portal ou não existe**. O limite chega em
`DescricaoPergunta`/`DescricaoResposta` do `POST /questionarios/perguntas`. Até a captura
nº 1, o agente pergunta em linguagem do segurado — 💭 *"maior ou menor que um cartão de
crédito?"* — e a resposta casa com a opção real da tela por `match_option`, como já se faz
para "como ocorreu" (`perguntas_do_portal_de_vidros.py:214-222`).
**Gate:** G7 — **ZERO** limite numérico de trincado no código quando a régua não veio do
portal. Mutação: reintroduzir `_LIMITE_CM = 10.0` no caminho do para-brisa.

**P2-2 · `abandonar` e `cancelar` como journeys reais.** 📊 A Regina cancelou ou abandonou
em **2 de 3** acionamentos. Contrato medido: `PUT atendimentos/cancelar
{codigoMotivoCancelamento, codigoAtendimento, observacaoMotivoCancelamento}` ·
`GET atendimentos/motivos-cancelamento` (a lista, nunca decorada) ·
`PATCH atendimentos/abandonar` (no bundle; zero capturas). `vidros_estado.py:234-235` já
tem `FRONTEIRA_CANCELAR` e `FRONTEIRA_ABANDONAR`; `ESTADOS` já tem `CANCELADO` e
`ABANDONADO` (`:60-61`). 🔴 **São fronteiras materiais e passam pelo guard como qualquer
outra.** ⚠️ `abandonar` fica CANDIDATE; `cancelar` está medido e pode ser `APPROVED`.

**P2-3 · Bradesco — D-PILOTO-17, e nada além.** ✅ O slug `bradesco` existe no bundle e no
`GET /seguradoras/` (📊 código `BRADESCO`, rota `bradesco`): entra no mapa único de P0-4
como qualquer uma das 38, e o preflight read-only pode ser exercido. ⛔ **Nenhuma linha de
código para `agendeseuservico.com`.** 🧑 O que destrava: a captura dupla da §4.4 do
roteiro da Regina.

**P2-4 · O Vigia continua cobrindo vidros.** 📊 `vigia_do_portal.py:306` filtra
`.eq("portal_key", "vidros_lanternas")`. 🔴 **Se qualquer bloco criar um `portal_key`
novo, o Vigia para de ver os jobs de vidros no dia seguinte, em silêncio.** A chave
continua `vidros_lanternas`; se o executor precisar de outra, o Vigia muda **no mesmo
commit**, e G8 prova.

---

## §8 · Os guardas e as mutações — 8 novos, teto de 12 (D-PILOTO-14)

🔴 **Todo guarda roda sobre o MOTOR e sobre o ACERVO real** (CLAUDE.md §9.4). ⛔ Proibido
teste que reimplementa a regra: se ele chama um regex ou uma constante em vez da função,
guarda o regex, não o comportamento.

| # | o guarda | o que ele chama | a mutação que o deixa **vermelho** |
|---|---|---|---|
| **G1** | **Replay do HAR da Yelum lataria** produz a mesma sequência de 7 escritas e o mesmo corpo de PATCH (8 chaves) | `abrir_atendimento_api` inteiro, contra fixture derivado do HAR por `lab har` | acrescentar `"ItemRemovido": None` → 9 chaves ≠ 8 |
| **G2** | A fronteira material é **calculada**, não fixa | `ST.fronteira_materializar_de` + `guard.acao_material_esperada` no fluxo real | trocar por `ST.FRONTEIRA_MATERIALIZAR` fixo → o caso `L` fica vermelho |
| **G3** | **ZERO** slug desconhecido; e `sompo → GRUPO_HDI` está certo | `API.slug_da_seguradora` sobre os 43 do bundle e os 38 da API | "corrigir" `GRUPO_HDI` para `SOMPO` |
| **G4** | As três verdades dizem a **mesma** coisa | lê `TRANSPORTAVEIS` e confere contra `prompts.py` e a tool | acrescentar um campo a `TRANSPORTAVEIS` sem tocar nos textos |
| **G5** | Endpoint `CANDIDATE` **não sai**, mesmo com as duas flags ligadas | `POST agendamentos` com freio ligado e Approval concedida | promover o endpoint a `APPROVED` no fixture → ele sai |
| **G6** | As **23 perguntas do .docx** casam com slot existente, com nome e família | `o_que_falta` + `_ESPECIFICAS_POR_IDENTIDADE`, sobre o texto real do .docx | apagar a família `retrovisor` |
| **G7** | A régua do trincado **vem do portal** — ZERO limite numérico no código | varre o caminho do para-brisa procurando literal de cm | reintroduzir `_LIMITE_CM = 10.0` ali |
| **G8** | O Vigia enxerga a `portal_key` que a journey grava | `vigia_do_portal.diagnosticar` sobre job do caminho novo | trocar a `portal_key` sem mexer no Vigia |

**Sobram 4 do teto.** ⚠️ São para o que o painel achar — não para preencher. Candidato
natural (G9): **desligar `PORTAL_VIDROS_API_FIRST` devolve o comportamento de hoje** (§11).

🔴 **A regra da mutação (protocolo §10):** roda em **worktree próprio ou com lock
exclusivo**, restaura por **cópia** (nunca `git checkout`), e o orquestrador **não roda a
bateria inteira** enquanto um juiz muta.

---

## §9 · Migrations

**📊 Nenhuma migration é necessária para P0 e P1.** Todo o estado cabe em colunas
existentes: `portal_jobs.params` · `portal_jobs.evidence` (jsonb) · `approval_requests` ·
o checkpoint durável da SPEC-073 (já usado por `_checkpoint`).

🔴 **Se o executor concluir que precisa de SQL**, a regra é inteira: leitura obrigatória de
[`MIGRATIONS-AUTHORITY.md`](../MIGRATIONS-AUTHORITY.md), diretório
`backend/supabase/migrations/`, idempotente, expand-first, e **APPLY / VERIFY / ROLLBACK
escritos ANTES de rodar**. ⚠️ Migration que altera dado, estrutura, trava ou quem pode ler
dispara o piso CRÍTICO (§3.2) — esta SPEC já é CRÍTICA; muda a lente do painel, não a
marcha.

---

## §10 · O canário controlado em produção

> 🔴 **O gate que nenhum teste substitui.** Build verde não prova que a aplicação sobe
> (CLAUDE.md §9.1); teste verde não prova que o portal aceita.

**O que é:** um acionamento de **LATARIA na Yelum**, com o veículo de teste do Founder, do
WhatsApp ao comprovante. 📊 É o único ramo **fechável hoje**: 100% do fluxo está medido,
do preflight ao `emitir-atendimento-formalizado`, e **não existe escolha de loja nem
agendamento** — justamente a parte que depende da captura nº 1.

**ANTES**

```
[ ] 🧑 Founder confirma apólice Yelum ATIVA com cobertura de lataria no veículo de teste
[ ] 🧑 Founder confirma o CPF do titular — por variável de ambiente, nunca versionado
[ ] 🤖 PORTAL_EFEITO_MATERIAL_LIBERADO ligado SÓ para este job (ver Q-A do BLOCO 0)
[ ] 🤖 PORTAL_VIDROS_API_FIRST ligado SÓ para este job
[ ] 🤖 a saída dos três comandos da §1, colada no relatório
```

🔴 **"Só para esse job" é exigência, e a SPEC não presume que exista** (Q-A). Se o freio
for global, ligá-lo abre a porta para todos os jobs de vidros em voo — e nasce o bloco
P0-6 (**BLOCKER**, via `CHANGE-ADDENDA`): allowlist de job ou de CPF, como a
`BILLING_CANARIO_ALLOWLIST` já faz na cobrança.

**OS CASOS**

```
Q1  o segurado (TESTE-A) descreve o dano de lataria em linguagem natural
Q2  o agente pergunta SÓ: data · quais peças · rodovia/urbano · cidade · relato
    ⛔ não pergunta placa, chassi, CEP, endereço, versão (vêm da InfoCap)
    ⛔ não pergunta loja nem domicílio (DisponibilizarAgendamento:false)
Q3  o preflight passa (cobertura existe)
Q4  as 4 escritas saem na ordem: POST /atendimentos → PUT corretores →
    POST solicitantes → PATCH (com ServicosMartelinhoLataria de ≥ 2 peças)
Q5  o GET /atendimentos devolve CodigoAtendimento, e o agente o entrega ao segurado na
    mensagem única do prompt (bloco "AVISAR O QUE FICOU DECIDIDO")
Q6  o comprovante é emitido e chega ao segurado
Q7  o dossiê no grupo da corretora diz o que aconteceu, em língua humana
```

**DEPOIS**

```
[ ] 🤖 desligar as duas variáveis imediatamente, e provar por comando
[ ] 🤖 colar em §6 do relatório: a trilha de `resumo_para_evidencia` (path sem query), o
       estado final, o CodigoAtendimento MASCARADO (4 últimos dígitos)
[ ] 🧑 Founder confirma que o e-mail/SMS da seguradora chegou com a loja indicada
[ ] 🧑 Regina/Saionara leem a conversa inteira e dizem se soa humana
[ ] 🤖 se o pedido precisar morrer, é por `PUT /atendimentos/cancelar` (P2-2), nunca
       fechando a aba — 📊 é o que o roteiro da Regina §2 manda, pelo mesmo motivo
```

🔴 **Se o canário falhar depois do `POST /atendimentos`, existe um pedido real na Yelum.**
Cancelar pelo portal e registrar. ⛔ **Nunca reexecutar** — `safe_to_retry_open`
(`vidros_estado.py:109-118`) responde `False`, e está certo.

---

## §11 · Entrega e implantação

```bash
git rev-list --count origin/main..HEAD          # o que ainda não subiu
git merge-base --is-ancestor origin/main HEAD && git push origin HEAD:main
# a saída do push vai COLADA no relatório — entregar não é commitar, é empurrar
```

**Ordem no EasyPanel:** `smith-api` (tool, prompt, catálogo de perguntas) →
`portal-worker` (journey e sessão). ⚠️ O worker é quem fala com o portal: implantá-lo antes
da API deixa uma janela em que o agente pede o que o worker ainda não sabe fazer.

| variável (nome, sem valor) | para quê | estado desejado após a SPEC |
|---|---|---|
| `PORTAL_VIDROS_API_FIRST` | liga o caminho API-first | **desligada** em produção; ligada só no canário |
| `PORTAL_EFEITO_MATERIAL_LIBERADO` | o freio da SPEC-073 | **desligado**; ligado só no canário, e só para o job |
| `PORTAL_VISION_MODEL` | o cérebro do caminho DOM | inalterada — ⚠️ ver a autópsia do mapa §8 |

**Rollback, em uma linha:** desligar `PORTAL_VIDROS_API_FIRST`. 📊 O desenho já garante
isso (`vidros_apifirst.py:6-9`). **Nenhum bloco pode quebrar essa propriedade.**

---

## §12 · Documentação e acompanhamento — obrigatórios

```
[ ] relatório em docs/canon/reports/, pelo template, ABRINDO com o EXECUTION CARD
    (protocolo §0.1: relatório sem card = SPEC aberta)
[ ] PENDENCIAS.md: P-PILOTO-07 e P-50 re-julgadas — FECHADA (com a prova) · CONTINUA (com
    o que destrava) · MORREU. E as novas: capturas que faltarem · o freio por job, se ele
    não existir · as 4 travas `regraDeBloqueio` do bundle que ninguém lê
[ ] FOUNDER-DECISIONS.md: só se nascer decisão nova. D-PILOTO-17 já está lá.
[ ] O-PORTAL-DE-VIDROS-TELA-POR-TELA.md — é "a autoridade sobre o que o portal pergunta"
    e está de 06/07. 🔴 Atualizar com o que se mediu, ou ele mente para o próximo leitor
[ ] ESTADO-DAS-SPECS.md e o dossiê do Founder
[ ] CHANGE-ADDENDA.md: tudo que sair do escopo da §2, classificado, ANTES de executar
```

---

## §13 · O que o estado da arte faz, e o que modelamos

> 🔴 Protocolo §7.3. ⚠️ A data de reabertura é do **pesquisador da execução**: ele abre
> cada uma, diz se envelheceu e se há melhor.

**1. HAR 1.2 (W3C)** · `https://w3c.github.io/web-performance/specs/HAR/Overview.html`
**Faz:** define o formato que o DevTools exporta. · **Modelamos:** `content.text` só existe
no export **"with content"** — sem ele o arquivo é uma lista de portas fechadas; daí a
insistência do roteiro da Regina e o `har_sem_corpos` do `lab har`. · **Rejeitamos:** o HAR
como verdade permanente — é **observação datada**, e é a razão da escada OBSERVED →
CANDIDATE → APPROVED. · **Juiz:** abre a spec, confere que `content.text` é opcional, roda
`lab har` sobre um HAR do acervo.

**2. RFC 5789 — PATCH** · `https://www.rfc-editor.org/rfc/rfc5789`
**Faz:** define `PATCH` como modificação parcial interpretada pelo servidor. ·
**Modelamos:** **omitir ≠ mandar `null`** — a regra do corpo de 8 × 11 chaves de P0-1. ·
**Rejeitamos:** a ideia de que `PATCH` é seguro por ser parcial (📊 aqui ele é a fronteira
material da lataria). · **Juiz:** abre a §2 da RFC e compara com o corpo do HAR e com o que
o motor produz.

**3. Idempotency keys da Stripe** · `https://docs.stripe.com/api/idempotent_requests`
**Faz:** repetir a chamada sem criar uma segunda cobrança. · **Modelamos:** a **pergunta
antes do retry** — *"isto já aconteceu?"* — que vive em `safe_to_retry_open` e em
`atendimento_aberto_existente` (a dedup do **próprio portal**). · **Rejeitamos:** achar que
uma chave nossa protege; ela não chega ao servidor da Maxpar — quem protege é o checkpoint
durável da SPEC-073. · **Juiz:** abre a doc, lê `vidros_sessao.py:186-194` e
`vidros_estado.py:109-118`.

**4. Pact — consumer-driven contracts** · `https://docs.pact.io/`
**Faz:** o consumidor grava o que espera do provedor, e o contrato vira teste. ·
**Modelamos:** o contrato é **gerado da interação real**, nunca escrito à mão — o que
`lab api-infer` faz. · **Rejeitamos:** o *provider verification*; não temos acesso ao
servidor da Maxpar, e o lado do provedor é substituído pela escada e pelo canário. ·
**Juiz:** abre "consumer contract", roda `lab api-infer` sobre um HAR, compara a forma.

**5. VCR.py — record & replay** · `https://vcrpy.readthedocs.io/`
**Faz:** grava respostas em "cassetes" e as reproduz offline. · **Modelamos:** o **replay
offline determinístico** do gate G1 — o HAR é o nosso cassete. · **Rejeitamos:** a
biblioteca. ⛔ O transporte é `page.evaluate` no browser autenticado; instalar VCR criaria
um segundo transporte para agradar ao teste. · **Juiz:** abre "record modes" e confere que
o fixture de G1 não faz uma chamada de rede.

**6. `har-to-openapi`** · 🔴 **o pesquisador confirma o repositório canônico na reabertura**
(o pacote o nomeia; esta proposta não afirma a URL). **Faz:** converte HAR em OpenAPI
inferindo schemas. · **Modelaríamos:** nada — `lab api-infer` já faz, e é nosso; serve ao
juiz para **comparar a qualidade da inferência**. · **Rejeitamos:** substituí-lo — ⛔ motor
paralelo. · **Juiz:** roda as duas sobre o mesmo HAR e compara endpoints e schemas.

⚠️ **Nenhuma destas referências vira autoridade.** Modela-se o **padrão**; o Tool Gateway,
o Work Run e o portal worker continuam únicos.

---

## §14 · O que depende da captura nº 1 — e o que **não** depende

> 🧑 **Captura nº 1** = para-brisa na Yelum, do início ao **agendamento confirmado**,
> escolhendo LOJA num dia com agenda, HAR *with content*
> ([`ROTEIRO-DE-CAPTURA-PORTAL-DE-VIDROS.md`](../guias/ROTEIRO-DE-CAPTURA-PORTAL-DE-VIDROS.md) §5).

```
🟢 NÃO DEPENDE — fecha nesta SPEC, sem esperar ninguém
   P0 inteiro · P1-1 (ler e APRESENTAR lojas, dias e horários — 📊 a captura de 14/08 já
   tem a lista de lojas e o calendário) · P1-3 nas famílias de CATÁLOGO (retrovisor, farol,
   lanterna, para-choque — a lista de `itens-cobertos` já as prova) · P1-4 ·
   🔴 P1-5 LATARIA INTEIRA, até o comprovante · P1-6 (o caminho multipart escrito e
   desligado) · P2-1 · P2-2 · P2-4 · 🔴 O CANÁRIO

🟡 DEPENDE — fica escrito, CANDIDATE, e desligado
   P1-2 `POST agendamentos` e `POST direcionamentos` — é o último clique, e nunca foi visto
   (📊 zero exercícios em 4 HAR) · P1-3 nas perguntas de PARA-BRISA (chuva · degradê · ADAS)
   e de VIGIA (desembaçador): o agente as faz, mas a resposta não vai ao questionário do
   portal enquanto não houver tela medida · P2-1 na régua real do trincado, que vem no
   texto da pergunta do portal
```

**A ordem de ataque por seguradora:**

```
1º Yelum LATARIA     🟢 fechável hoje — é o canário
2º Yelum VIDRAÇARIA  🟡 99% hoje · 100% depois da captura nº 1
3º Porto             mesmo motor + `TipoAtendimento` (📊 já modelado, vidros_api.py:220-248)
4º Azul / Zurich     já têm corredor de WhatsApp para vidros — conferir qual ganha
5º as outras 34      1 captura de passo 1 + `itens-cobertos` cada (P-50)
6º Bradesco          🔴 captura dupla ANTES de código (D-PILOTO-17)
```

---

## §15 · A fila — de onde esta SPEC vem e o que ela deixa

**Depende de:** nada em código. 📊 O diagnóstico §12.1 a coloca na posição 9, e a única
dependência real é **externa**: a captura nº 1, para o 100% de vidraçaria. **Lataria fecha
sem ela.** ⚠️ Uma dependência de qualidade, não de código: a EXTRA-001.2 melhora a régua de
língua que o canário usa no passo "Regina/Saionara leem a conversa". **Não bloqueia.**

**Ela deixa para as seguintes:** a **EXTRA-001.7** ganha o acionamento de vidros como
sucesso na régua de eficiência de D-PILOTO-13 (ele passa a chegar ao protocolo sozinho); a
**EXTRA-001.5** ganha fonte real de cobertura de vidros (o preflight responde "tem
cláusula" antes de qualquer escrita); a **SPEC-101** ganha o segundo caso de uso real da
escada da SPEC-077, depois do Cobrador da Allianz.

---

## §16 · Definição final de conclusão — a lista fechada

```
[ ] 1. BLOCO 0 remedido, com a saída dos 6 comandos colada, as perguntas Q-A/Q-B/Q-C
       RESPONDIDAS, e as divergências escritas como emenda
[ ] 2. G1 verde: replay offline do HAR da Yelum lataria produz a MESMA sequência de 7
       escritas e o MESMO corpo de PATCH (8 chaves, não 11) · e a mutação que acrescenta
       `"ItemRemovido": None` o deixa VERMELHO
[ ] 3. G2 verde: `"…|L"` arma a fronteira ANTES do PATCH · `"…|V"` arma antes do
       `POST /questionarios` · e a mutação que volta a constante fixa fica VERMELHA
[ ] 4. G3 verde: ZERO slug desconhecido pelo portal · `sompo → GRUPO_HDI` provado ·
       `ITAU` fora do caminho ativo · Yelum = `LIBERTY` em todo lugar
[ ] 5. G4 · G5 · G6 · G7 · G8 verdes, cada um com a mutação rerodada e a saída colada
[ ] 6. 🔴 O CANÁRIO: 1 acionamento de LATARIA na Yelum, com o veículo de teste do Founder,
       do WhatsApp ao COMPROVANTE — Q1 a Q7 respondidos com saída real, e as duas
       variáveis provadas desligadas depois
[ ] 7. A bateria inteira rodada no gate de cada bloco e no fim (2 a 4 vezes na SPEC,
       protocolo §10), com a contagem do diário do conftest no relatório
[ ] 8. `next start` + 1 requisição a `/api/…` SE a SPEC tiver tocado `app/`,
       `middleware.ts`, `next.config.js` ou variáveis de ambiente (CLAUDE.md §9.1)
[ ] 9. `git push origin HEAD:main` com a saída colada · serviços implantados na ordem da
       §11 · rollback provado (desligar a flag volta ao caminho de hoje)
[ ] 10. P-PILOTO-07 e P-50 re-julgadas · pendências novas escritas ·
        `O-PORTAL-DE-VIDROS-TELA-POR-TELA.md` atualizado com o que se mediu
[ ] 11. Declaração escrita de que NENHUM motor paralelo foi criado, item a item contra a
        tabela da §3
[ ] 12. Relatório abrindo com o EXECUTION CARD preenchido, com FATO / INFERÊNCIA /
        RECOMENDAÇÃO separados, e todo número com 📊 ou 💭
```

🔴 **Um item aberto = SPEC aberta.** "Quase tudo verde" não é um estado.

---

*Autoridade: CLAUDE.md · PROTOCOLO-AUTOBROKERS-AAA v11.2 · D-PILOTO-08, 14, 17, 20 ·
diagnóstico §10 (laudo I5) · SPEC-073 · SPEC-074 · SPEC-077 ·
`O-PORTAL-DE-VIDROS-TELA-POR-TELA.md` · `ROTEIRO-DE-CAPTURA-PORTAL-DE-VIDROS.md`*
