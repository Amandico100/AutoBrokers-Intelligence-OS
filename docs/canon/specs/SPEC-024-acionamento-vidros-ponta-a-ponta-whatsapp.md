# SPEC-024 — Acionamento de vidros PONTA A PONTA via WhatsApp (a ponte atendente→portal)

> **Contexto para o novo chat:** o MOTOR do portal já funciona. Provado: quando recebe os dados REAIS,
> o worker navega o formulário inteiro do portal de vidros e para nos 80% ("Confirme a peça danificada"),
> **estável, 3/3 runs, 18 passos** (ver `adaptive.py` + SPEC-020). O que está QUEBRADO é a **ponte** entre
> o atendente do WhatsApp (conversa + InfoCap) e a tool `portal_action`: ela alimenta o portal com dados
> **inventados/incompletos**. Esta SPEC conserta essa ponte. É o PRIMEIRO trabalho do novo chat de portais
> (antes da SPEC-023). NÃO reescreva o motor.

## 1. Evidência do fracasso (teste real no WhatsApp, 2026-07-07)

Segurado pediu acionamento de vidro. O atendente identificou na InfoCap, mas o job enfileirado tinha
**dados falsos** (comparado a um teste direto que chega nos 80%):

| Campo | Teste direto (✅ chega nos 80%) | Job do WhatsApp (❌ falhou) |
|---|---|---|
| `insurer_name` | `Yelum` | **`Liberty`** (nome legado; portal usa Yelum) |
| `placa` | `QJQ0A91` (real, da apólice) | **`ABC1D23`** (INVENTADA pelo LLM) |
| `segurado` | 9 campos (apólice, chassi, veículo, endereço, cep…) | **ausente / vazio** |
| `local` | SC / Florianópolis / CEP real | **SP / São Paulo / CEP `01000-000`** (INVENTADOS) |

`params` reais do job falho:
```json
{ "insurer_name":"Liberty", "placa":"ABC1D23", "cpf_cnpj":"03074327936", "data_dano":"05/07/2026",
  "local":{"estado":"SP","cidade":"São Paulo","cep":""},
  "dano":{"peca":"vidro da porta","como":"deixei o carro estacionado...","onde":"urbano","descricao":"..."},
  "solicitante":{...ok...} }   // <-- SEM chave "segurado". placa/local INVENTADOS.
```

Passos do `adaptive` (evidência `evidence.adaptive_steps`) mostram o efeito cascata:
```
 9. select qualItemDanificado  v="vidro da porta"          -> mdselect=VIDRO PARABRISA - CARGA   ❌ (item ERRADO)
10. select comoOcorreuDano     v="deixei o carro estac..." -> mdselect=CHOQUE TERMICO            ❌ (causa ERRADA)
14. fill   estado              v="SP"                       -> filled_autocomplete  (local errado)
17-22. fill CEP "01000-000" repetido -> Avançar disabled -> tela travada
```
E no WhatsApp o atendente entrou em LOOP de "um momento…" sem nunca concluir (o mesmo desastre original),
porque a `portal_action` voltava `needs_human`/falha e ele re-tentava sem corrigir a causa.

## 2. Causas-raiz (com arquivos exatos)

### C1 — A tool `portal_action` NÃO carrega os dados da apólice (InfoCap) → o LLM inventa
- `backend/app/agents/tools/portal_params.py::build_portal_params`: monta os params **sem chave
  `segurado`**. Só usa `insurer_name/cpf/placa/data` + `solicitante`(perfil da corretora) + `dano`/`local`
  vindos do LLM. **Placa, cidade, estado, cep, apólice, chassi, veículo — nada vem da InfoCap.**
- `backend/app/agents/tools/portal_tool.py::PortalActionInput`: o schema tem `placa/estado/cidade/cep`
  como args do LLM → o LLM **alucina** (`ABC1D23`, `SP`, `01000-000`) porque não tem esses dados na conversa
  e a tool não os busca.
- **O motor precisa do `segurado` completo** (o worker preenche apólice/veículo/endereço no portal e o
  portal valida por CPF+placa+apólice). Sem isso, o cérebro do portal chega a **perguntar "qual o número da
  apólice?"** (job `10ab2d74`).

**Correção (C1):** a `portal_action` deve **buscar a apólice na InfoCap por CPF (e nº da apólice se houver
mais de uma)** e preencher `params.segurado` (apólice, placa REAL, chassi, veículo, cep, endereço, cidade,
estado, nome, telefone) — **server-side, nunca confiando no LLM para placa/endereço**. O atendente já fez o
lookup na conversa; reusar esse resultado (passá-lo à tool) ou refazer o lookup dentro da tool. O LLM só
decide: qual apólice (se múltiplas), a peça/como/onde do dano (da conversa) e a data.

### C2 — Nome da seguradora não normalizado (Liberty vs Yelum)
- A apólice na InfoCap diz **"Liberty"**; o portal de vidros seleciona a seguradora por **"Yelum"** (marca
  atual; Liberty auto = Yelum). O `insurer_name:"Liberty"` pode selecionar errado ou nada.
- **Correção (C2):** tabela/normalização de sinônimos de seguradora (Liberty↔Yelum, etc.), aplicada antes de
  montar o job. Candidato: usar/estender o registro `portals`/`insurers` (SPEC-020) com aliases.

### C3 — `md-select` casa a opção ERRADA em campos críticos (item/causa do dano)
- `backend/portal_worker/adaptive.py::_apply_mdselect` (o `page.evaluate` de match): a preferência é
  exato→startswith→contains→**1ª opção**. Quando o valor do LLM não casa limpo, cai na **1ª opção** — e isso
  escolheu **"VIDRO PARABRISA - CARGA"** para `"vidro da porta"` e **"CHOQUE TERMICO"** para uma frase longa.
- Em campos de **formato** (tipo de telefone) qualquer opção serve; em **item danificado / causa** a opção
  ERRADA é um acionamento ERRADO. **Não pode cair na 1ª opção nesses.**
- **Correção (C3):** trocar o match por **similaridade por tokens** (escolher a opção com mais palavras em
  comum com o valor; "vidro **da** porta" → "VIDRO **DE** PORTA" tem 2 tokens em comum vs "VIDRO PARABRISA"
  com 1). E, para item/causa, se o melhor score for fraco, **não escolher às cegas** — devolver as opções
  para o cérebro decidir (needs_human com as opções, que já existe no fluxo). Instrumentar com `debug_dom`
  (as md-option com texto+valor já são capturáveis — ver `LAST_MDSELECT_DEBUG`).

### C4 — Atendente (API): lista apólices erradas e entra em loop de "um momento"
- Listou **6 apólices** incluindo **vencidas/canceladas** e de ramos não-auto. Para vidros, deve
  **filtrar apólices AUTO ativas** e, se só uma fizer sentido, nem perguntar.
- Quando a `portal_action` falha, o atendente repete **"um momento…"** sem corrigir. Deve: (a) dar UM retorno
  honesto ("o portal parou numa etapa, já estou resolvendo"), (b) não repetir a mesma chamada com os mesmos
  dados errados, (c) se faltar dado real, corrigir a origem (InfoCap), não re-tentar em loop.
- Arquivo: `backend/app/core/prompts.py` (ATTENDANCE_BASE_PROMPT, passo 2/5 do vidros) + a tool.

## 3. O que fazer (ordem sugerida)
1. **C1 (ponte de dados)** — o fix de maior impacto. A `portal_action` monta `params.segurado` a partir da
   InfoCap (placa/apólice/veículo/endereço/cep reais). O LLM não fornece mais placa/local. Teste direto:
   enfileirar via a tool (não à mão) deve gerar params iguais aos do teste que chega nos 80%.
2. **C2 (normalização seguradora)** — Liberty→Yelum.
3. **C3 (match de md-select por similaridade)** — item/causa corretos; sem 1ª-opção às cegas.
4. **C4 (atendente)** — filtrar apólices auto ativas; sem loop de "um momento".
5. **Verificar ponta a ponta pelo WhatsApp** (com o founder), gate on. Alvo: identifica → "tô abrindo" →
   ~1-2 min → 80% com a peça/loja CERTAS.

## 4. Como diagnosticar (ferramentas que já existem — USE, não chute)
- **Banco `portal_jobs`**: `params` (o que a tool montou), `evidence.adaptive_steps` (cada passo + resultado),
  `evidence.debug_dom` (raio-X da tela travada: selects/matselects/invalids/inputs/buttons/text),
  `evidence.mdselect_overlay` (as md-option reais quando um select não casou), `error`, `status`.
- **Comparar** um job do WhatsApp (falho) com um job direto (chega nos 80%) — a diferença nos `params` é o
  bug. Foi assim que este diagnóstico foi feito.
- Scripts de referência em `scratchpad/` do chat do vidros: `diag_dom.py`, `stability.py`, `test1_worker.py`.

## 5. Não-regressão
O acionamento com dados REAIS já chega nos 80% de forma estável (SPEC-020). Qualquer fix aqui deve manter
isso (rode o teste direto com params completos e confirme 80%). Segurança: `confirm=False` nunca finaliza.
