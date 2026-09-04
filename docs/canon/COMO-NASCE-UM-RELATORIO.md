# COMO NASCE UM RELATÓRIO — o protocolo dos 6 passos

> **Para qualquer chat com o Claude Code executar em minutos, com guarda.**
> SPEC-094.1 · BLOCO E · 03/09/2026 · o guarda deste documento é
> `backend/tests/test_o_relatorio_nasce_pelo_protocolo.py`.

📊 **Por que este documento existe.** Medido em `COMO-NASCE-UM-RELATORIO-HOJE.md`:
um relatório novo eram **7 passos, 5 arquivos e um deploy** — cálculo em
`calculos.py` → `Template` no `CATALOGO` → pista léxica em `escolher()` → seed →
tool em `agents/tools/` → uma linha em `graph.py` → guarda → `git push`. **Nada
passava por Skill, Tool Gateway ou Registry.** Depois da SPEC-094, a maior parte
disso deixou de ser necessária: um relatório novo é, quase sempre, **uma
definição e uma seção**.

```
⛔ NÃO é uma tool nova.       ⛔ NÃO é uma Skill.       ⛔ NÃO é um Auxiliar.
⛔ NÃO é SQL gerado.          ⛔ NÃO é sandbox.         ⛔ NÃO é deploy de motor.
```

---

## 1 · CLASSIFIQUE — o que você está criando, das quatro coisas?

| é… | quando | onde mora |
|---|---|---|
| **MÉTRICA** | há um número novo a calcular | `backend/app/comercial/metricas/<arquivo>.py` |
| **SEÇÃO** | o número precisa aparecer na peça | `_compor` da tool + `templates.py` |
| **FONTE** | o dado ainda não entra no produto | adapter (`app/providers/`) + CBIM |
| **ENTREGA** | muda o canal ou o formato | template/canal — SPEC-095 |

🔴 **Um relatório novo é quase sempre 1 MÉTRICA + 1 SEÇÃO.** Se a sua resposta
foi "uma tool nova", pare: a tool `executive_intelligence` já recebe qualquer
assunto pelo query plan, e uma segunda tool sobre os mesmos fatos é motor
paralelo (CLAUDE.md §5).

---

## 2 · MEÇA — antes de escrever uma linha

```bash
cd backend

# a fonte tem o dado?  (o manifesto de capacidade, não a memória)
python -c "import json;d=json.load(open('../docs/canon/providers/infocap/infocap-capability-manifest.json'));print(sorted(d))"

# o fato canônico já existe?  (CBIM — se não existir, o passo é FONTE, não MÉTRICA)
grep -n "^class .*Fact" app/comercial/cbim.py

# e a pergunta JÁ TEM métrica?  ← o passo que evita a duplicata
python -c "from app.comercial.metricas import registry as r; [print('%-32s %s' % (k, v.pergunta_verificada)) for k,v in sorted(r.todas().items())]"
```

🔴 **A terceira pergunta é a que mais economiza.** 📊 Modelado no Euno (SPEC-094.1
ref ②): a proposta é revisada contra o catálogo ANTES de existir, porque
**duplicata é o modo de falha real** — três "comissão do mês" divergentes
destroem mais confiança do que uma métrica faltando. É a mesma pergunta que o
chat faz sozinho com `listar_metricas`.

---

## 3 · DEFINA — a métrica é uma DECLARAÇÃO, não um trecho de código

Um arquivo em `backend/app/comercial/metricas/`. Ele **não importa o registry**:
o registry se injeta (`instalar(reg)`), porque um import criaria uma segunda
cópia do catálogo quando alguém carregasse `registry.py` por caminho.

```python
_DEFINICOES.append(dict(
    metric_id="commission.avg_per_producer_by_segment", version=1,
    label="Comissão média por produtor, por ramo",
    grain="producer", unit="BRL",
    time_basis=POLICY_VALID_FROM,          # 🔴 qual população? emissão ou vencimento
    required_capabilities=("financial.commission_accrued",
                           "portfolio.producers"),
    formula=_media_por_produtor_por_ramo,  # (ctx) -> (valor, cobertura, breakdown, avisos)
    coverage_rule="fração da comissão do período com produtor E ramo legíveis",
    forbidden_fallback="⛔ produtor sem ramo nunca entra num ramo 'outros' para "
                       "fechar o total",
    pergunta_verificada="Quanto cada produtor apropriou de comissão, por ramo?",
    golden=golden(1250.0),                 # 📊 o número na fixture conhecida
))
```

**Os campos que ninguém pode esquecer, e por quê:**

- `time_basis` — 📊 a rota de produção filtra pelo **início** de vigência
  (1.680/1.680) e a de vencimentos pelo **fim** (3.536/3.536): **interseção de
  2,8%**. A mesma apólice está em dois períodos diferentes conforme a pergunta.
  Um número sem base declarada é um número que ninguém reproduz.
- `coverage_rule` — toda soma de dinheiro devolve **o total E o denominador**.
  Uma métrica que some 80% da carteira e se apresente como "o período" mente por
  omissão.
- `forbidden_fallback` — o que esta métrica **não** pode fazer quando falta
  dado, escrito. É a linha que o próximo leitor encontra antes de "arredondar
  para zero só desta vez".
- `pergunta_verificada` — 📊 ref ④ (Cortex Analyst): perguntas verificadas por
  gente melhoram a precisão (+20 p.p. em teste controlado). E ninguém reconhece
  a própria pergunta em `mix.branch`.
- `golden` — o número esperado numa população conhecida. Sem ele, uma mudança de
  fórmula troca o resultado em **silêncio**, e silêncio é o modo de falha caro
  (CLAUDE.md §9.5).

🔴 **A fórmula NÃO conhece a fonte.** Nenhum arquivo de `metricas/` pode conter
`infocap`, `susep` ou `nosnum` — é a mutação **M1**, e o guarda a mede.

---

## 4 · PROVE — quatro perguntas, e cada uma pega o que as outras não pegam

```bash
cd backend
python tests/test_o_relatorio_nasce_pelo_protocolo.py     # o protocolo
python tests/test_o_pulso_360_nao_pertence_a_infocap.py   # a 094 inteira
python tests/test_a_fabrica_de_relatorios.py              # a 094.1
```

| | pergunta | como se prova |
|---|---|---|
| **golden** | o número esperado sai? | `registry.calcular(...)` sobre a fixture, comparado ao `golden['esperado']` |
| **M1** | a fórmula conhece a fonte? | `grep -riE "infocap\|susep\|nosnum" app/comercial/metricas/` → **0** |
| **UNAVAILABLE ≠ 0** | ausência vira zero? | mutação: troque `None` por `0.0` na fórmula → o guarda fica **VERMELHO** |
| **dois tenants** | o número de uma casa aparece na outra? | dois `company_id` na mesma rodada, saídas disjuntas |

🔴 **Toda mutação precisa da RESTAURAÇÃO e do CONTROLE.** Um guarda que não
consegue ficar vermelho não é guarda, é carimbo — e um que não consegue ficar
verde ensina a ser ignorado (CLAUDE.md §9.3). Restaure **por cópia**, nunca por
`git checkout`.

---

## 5 · MOSTRE — a métrica vira seção da peça

1. Acrescente o `metric_id` à visão certa em `VISOES`
   (`app/agents/tools/executive_intelligence.py`) — é o assunto que o modelo
   escolhe, e ele **não** escolhe métrica.
2. Desenhe a seção em `_compor`, com o cartão citando a cobertura no `lede` —
   dentro do cartão, não seis seções abaixo.
3. Se a seção for **nova no template**, acrescente-a à `composition` de
   `templates.py`. 🔴 `_garantir_template` faz upsert no uso: **não há
   migration**. Se algum dia houver, leia `MIGRATIONS-AUTHORITY.md` antes.

⛔ **Não crie template novo para um número novo.** Um segundo catálogo de
templates é motor paralelo.

---

## 6 · FECHE

```bash
# a proposta que veio do chat vira `promovida`
python -m app.comercial.metricas.promover <run_id> <metric_id> --company <id>

# o que ficou faltando vai para PENDENCIAS.md, com dono e custo de esquecer
# e a entrega é o PUSH, não o commit (CLAUDE.md §2)
git rev-list --count origin/main..HEAD      # 0 = está no ar
git push origin HEAD:main                   # cole a saída no relatório
```

---

## O exemplo completo — `commission.avg_per_producer_by_segment`

> O caso do §0 da SPEC-094.1: *"qual a comissão média por produtor só nas
> apólices de frota?"*

```
TERÇA · o dono pergunta no chat
  o chat chama executive_intelligence(listar_metricas=true) → 16 métricas, e
  nenhuma responde isso
  responde: "não tenho essa métrica registrada; proponho
  commission.avg_per_producer_by_segment sobre comissão apropriada × produtor ×
  ramo — quer que eu registre a proposta para revisão?"     ⛔ ZERO número
  o dono diz sim → propor_metrica(confirmado=true)
  nasce work_runs(workflow_key='metric.proposal', status='waiting_approval')
  + approval_requests(pending) + work_events(metric.proposta_criada)

QUARTA · um chat com o Claude Code abre ESTE documento
  1 CLASSIFIQUE  MÉTRICA + SEÇÃO. Os fatos existem (CommissionFact,
                 ProducerAssignmentFact); a fonte existe. Não é FONTE.
  2 MEÇA         listar as 16: a mais próxima é producer.performance, que conta
                 produtores — não é a mesma pergunta. Segue.
  3 DEFINA       metricas/produtores.py ganha a definição acima, com
                 pergunta_verificada e golden medido na fixture
  4 PROVE        python tests/test_o_relatorio_nasce_pelo_protocolo.py → verde
                 mutação: apagar o `golden` → VERMELHO · restaurar → verde
  5 MOSTRE       VISOES["pessoas"] ganha o metric_id; _compor ganha a linha na
                 tabela "Quem apropriou comissão", com o lede de cobertura
  6 FECHE        git add … && git commit && git push
                 python -m app.comercial.metricas.promover <run_id> \
                     commission.avg_per_producer_by_segment --company <id>
                 → work_events(metric.promovida, actor_type='admin')
                 → o run vai para `succeeded`
```

📊 **15 minutos, um arquivo tocado e meia dúzia de linhas.** O que era 7 passos,
5 arquivos e um deploy de motor.

---

## QUANDO É MAIS QUE ISSO

| o caso | o caminho |
|---|---|
| **fonte nova SEM credencial** (SUSEP, ANS, BACEN) | conector público — o BLOCO B da SPEC-094.1 é o molde: Rotina baixa em lote para o MinIO, o adapter lê o MinIO. ⛔ **nunca no caminho quente do chat** |
| **fonte nova COM credencial** | [`CAMADAS-DE-CONEXAO.md`](CAMADAS-DE-CONEXAO.md) — Vault, manifesto de capacidade, censo medido |
| **canal de entrega novo** (WhatsApp, e-mail, portal) | SPEC-095. ⛔ Nada sai por canal nenhum sem ela |
| **trabalho recorrente** ("todo dia 1º") | **Rotina** agenda o que já existe. "Auxiliar" não é o nome disso ([`GLOSSARIO.md`](GLOSSARIO.md)) |
| **o dado exige escrita na fonte** | fora de qualquer SPEC de relatório: exige ambiente de teste do provedor e Approval |
| **o número não fecha com o extrato** | provavelmente é **apropriado × recebido** (mutação M8). São dois números, e um deles a fonte piloto não expõe |

---

## As seis linhas que este protocolo existe para impedir

```
⛔ um número na tela sem metric_id ao lado
⛔ INDISPONÍVEL apresentado como 0
⛔ duas métricas com o mesmo significado e nomes diferentes
⛔ uma fórmula que sabe o nome do sistema de gestão
⛔ uma tool nova fora do `if` de papel — o Atendimento lendo a carteira
⛔ uma métrica criada por modelo: propor é o teto, promover é de gente
```
