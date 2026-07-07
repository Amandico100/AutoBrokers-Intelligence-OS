# SPEC-025 — Acionamento de VIDROS ponta a ponta no WhatsApp (corrige e substitui a SPEC-024)

**Autor**: Opus 4.8 (executor) · 2026-07-07 · **Status**: proposta, aguardando green-light do founder
**Supersede**: SPEC-024. Mantém o diagnóstico dela, mas **corrige o erro central**: a placa/veículo
**existem** na InfoCap — só que num endpoint que o sistema **nunca chamava** (`/itens`), não no
`/documento`. Verificado ao vivo (conta AutoFleet, CPF do Rafael) em 2026-07-07.

> Regra de ouro do founder: **não engessar o agente**. Este conserto REMOVE a necessidade de o LLM
> inventar dados (placa/endereço) dando a ele os fatos reais; a inteligência (qual apólice, peça, como,
> ler as telas do portal) continua 100% livre. Determinismo só sobre FATOS; julgamento continua do agente.

---

## 1. Root cause (verificado, não suposto)

O **motor do portal funciona** (navega o formulário inteiro e para nos 80% com dados reais — provado,
job `4a6647e7` chegou a `done`; os demais com dados reais param no 80% = `needs_human` seguro).

O que quebra é a **ponte de dados** entre o atendente (WhatsApp) e a tool `portal_action`:

- A tool **não busca os dados do veículo na InfoCap**. O schema (`portal_tool.py`) pede `placa`, `estado`,
  `cidade`, `cep` **ao LLM** — que não tem esses dados na conversa e por isso **inventa**
  (`placa=ABC1D23`, `local=São Paulo/SP`). Confirmado no banco `portal_jobs`:

  | | Job WhatsApp (travou) | Job com dados reais (chega no 80%) |
  |---|---|---|
  | insurer | `Liberty` | `Yelum` |
  | placa | `ABC1D23` (inventada) | `QJQ0A91` (real) |
  | `segurado` | ausente | presente |
  | local | `SP/São Paulo` | `SC/Florianópolis` |

- **Por que o LLM não puxou da InfoCap?** Porque a integração InfoCap **não expõe** placa/chassi/veículo.
  O connector consulta `/documento` (financeiro/comissão) e mascara o endereço. **A placa não está lá.**
- **Descoberta desta spec (o que a SPEC-024 errou):** a InfoCap TEM o veículo, no endpoint **`/itens`**
  (`GET /itens?codfil=<>&nosnum=<>`), que **nenhuma parte do código chama**. Ao chamar, veio tudo real:
  `placa=QJQ0A91`, `chassi=98867513WJKH74022`, `veiculo=COMPASS LIMITED...`, `fipe=170470`,
  `anofab/anomod=2018`, `renavam`, as `garantias` (inclui "VIDROS VIP") e até a **tabela de franquia de
  vidros** em `observacoes` (Para-brisa R$630, Laterais R$195, Retrovisores R$335…). O endereço do
  segurado vem do `/cliente` (`enderecos[padrao]`: logradouro/número/bairro/**cep**/cidade/**estado**).

**Conclusão:** garbage-in → garbage-out. O agente foi vendado nos fatos que precisava e empurrado a
prosseguir; preencheu os obrigatórios com invenção; o portal (bom) escolheu a peça errada e travou.

## 2. Os 4 consertos

### C1 — Ponte de dados via InfoCap `/itens` (resolve ~90%) — server-side, o LLM não fornece fatos
- **Novo método no provider** `InfocapPolicyDataProvider.vehicle(company_id, policy_ref|document+policy_number)`
  → delega a uma nova função `infocap_vehicle_item` em `infocap_connector.py` (reusa
  `_resolve_infocap_connection` + login existentes). Retorna:
  ```
  { ok, insurer_key, segurado: { apolice, placa, chassi, veiculo, fipe, ano, combustivel, renavam,
      nome, cpf_cnpj, telefone, cep, logradouro, numero, bairro, cidade, estado },
    local: { estado, cidade, cep }, glass_franchise_text }
  ```
- **`portal_action` (tool)**: no `_arun` (async), depois de já ter a apólice escolhida, **busca o veículo
  na InfoCap** e monta `params.segurado`/`placa`/`local`/`insurer_name` **no servidor**. 
- **`PortalActionInput` (schema)**: remover `placa`, `estado`, `cidade`, `cep`, `insurer_name` como
  entradas do LLM. O LLM só fornece: `cpf_cnpj` (ou já da conversa), `policy_number`/`policy_ref` (quando
  houver mais de uma apólice), `data_dano`, e `peca/como_ocorreu/onde_ocorreu/descricao` (do relato). 
- **Fallback honesto**: se a InfoCap não tiver a placa daquela apólice (ex.: apólice de outra
  seguradora não sincronizada), a tool devolve um retorno claro pedindo a placa ao cliente — **nunca
  inventa**. (Placa é a única coisa que o cliente sempre sabe.)
- `build_portal_params` passa a validar `params.segurado.placa` (real) em vez de aceitar placa do LLM.

### C2 — Normalizar seguradora (Liberty → Yelum)
- Mapa de sinônimos aplicado a partir do `insurer_key`/`seguradora` da InfoCap antes de montar o job
  (`LIBE`/`LIBERTY SEGUROS S/A` → `Yelum`; extensível). Local: helper puro em `portal_params.py`
  (testável), alimentado pelo dado da InfoCap, não pelo LLM.

### C3 — `adaptive.py::_apply_mdselect`: parar de cair na 1ª opção às cegas (sem engessar)
- Hoje: se o texto não bate por substring, escolhe **a 1ª opção** → "vidro da porta" virou "VIDRO
  PARABRISA". 
- Novo: **similaridade por tokens** (mais palavras em comum vence). E, em campos **críticos**
  (item danificado / causa do dano), se o melhor score for fraco, **não chutar** — devolver as opções
  reais ao cérebro (`needs_human` com `opcoes`, fluxo que já existe) para ele decidir vendo a lista.
  Isso é **mais** inteligência, não menos: o cérebro escolhe com a lista real na mão.
- Em campos de formato (tipo de telefone) segue tolerante (qualquer opção serve).

### C4 — Atendente (`prompts.py`): sem invenção, sem loop de "um momento"
- Passo de vidros: **nunca inventar placa**; a tool já traz da InfoCap. Se a tool pedir a placa
  (fallback), perguntar **só** a placa (uma pergunta), sem pedir CEP/nome/endereço.
- Acabar com o loop: quando a tool voltar `needs_human`/`failed`, dar **um** retorno honesto e específico
  ("cheguei até a confirmação, o portal parou em X"); **não** repetir a mesma chamada com os mesmos
  dados; se travar de verdade, chamar humano (regra já existente) em vez de "um momento…" infinito.
- Filtrar apólices AUTO **ativas** ao decidir (não listar vencidas/canceladas como opção de vidros).

## 3. Segurança (inalterada)
`confirm=False` **permanece** — o motor navega tudo e **para na tela de confirmação**, nunca envia o
pedido real. (Trava de teste confirmada pelo founder; a liberação do clique final é um passo futuro.)

## 4. Testes (house-style: importlib + stubs + `check()`, ASCII, sem pytest)
- `test_spec025_portal_params`: `build_portal_params` com `segurado` real → placa real, insurer
  normalizado (Liberty→Yelum), local da InfoCap; rejeita quando falta `segurado.placa`.
- `test_spec025_insurer_alias`: mapa de sinônimos.
- `test_spec025_mdselect_similarity` (worker): "vidro da porta" casa "VIDRO DE PORTA" (2 tokens) e **não**
  "VIDRO PARABRISA" (1 token); score fraco em campo crítico → devolve opções (não chuta).
- `infocap_vehicle_item`: teste com HTTP stubado (resposta `/itens` + `/cliente` fixas) → segurado montado.
- Frontend: n/a (sem UI nova). `npx tsc --noEmit` se algo tocar o front (não deve).
- **Verificação ponta a ponta**: enfileirar via a própria tool (não à mão) e confirmar que o `params` do
  job fica **igual ao job que chega no 80%** (placa/insurer/local reais, `segurado` presente); job real
  chega no 80% "Confirme a peça danificada" com a peça CERTA.

## 5. Não-regressão
O acionamento com dados reais já chega no 80% (SPEC-020). Rodar o job de referência e confirmar que
continua chegando no 80%. Nada no motor (`adaptive.py`) muda além do `_apply_mdselect`.

## 6. Deploy
Commit em `feat/spec-017-attendant` → merge `--no-ff` na main → push → trigger de deploy
(**API** p/ `prompts.py` + tools + connector/provider; **worker** p/ `adaptive.py`). Ciclo do worker ≈ 4 min.

## 7. O que preciso do founder (coordenação, não código)
1. Confirmar que o **portal-worker está no ar** no EasyPanel com os envs (`SUPABASE_*`, `PORTAL_VAULT_KEY`,
   `OPENAI_API_KEY`, `PORTAL_REAL_ENABLED`).
2. Ligar `PORTAL_REAL_ENABLED=true` na hora do teste ao vivo (e desligar depois, se quiser).
3. InfoCap conectada na **AutoFleet** (auto) durante o teste de vidros — já está, confirmar.
4. Os tokens de trigger de deploy (API e worker) — se você quiser que eu dispare; ou você dispara.

## 8. Fora de escopo (desta spec)
Liberar o clique final de envio (produção); cobrança/portais autenticados (SPEC-023); Allianz residencial
(revisão separada); novos corredores auto (Porto/HDI/Allianz).
