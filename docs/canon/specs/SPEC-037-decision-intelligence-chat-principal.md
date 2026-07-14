# SPEC-037 — Decision Intelligence: o Chat Principal que faz a corretora GANHAR DINHEIRO

**Status:** visão aprovada em conceito (founder 14/07) — execução em blocos intercalados
**Insumo:** proposta do GPT 5.5 ("Insurance Intelligence OS") revisada pelo Fable com o contexto REAL do projeto.

---

## 1. Meu veredito sobre a proposta do GPT

**O que ele acertou (e adoto):** o diagnóstico central está correto — RAG recupera conhecimento, não gera decisão; o diferencial é o **Decision Harness** (diagnóstico → cálculo → estratégia → crítica → plano → acompanhamento de resultado); "300 knowledge cards excelentes > 50 mil PDFs"; lifecycle governado de auto-evolução (nunca publicar sozinho no global); benchmarking por cohort anonimizado; a matemática do funil como exemplo canônico.

**O que ele NÃO sabia (e muda o plano):** metade do que ele propõe **JÁ EXISTE construído** nas últimas 48h — ele leu um repo desatualizado. Espelho/Vigia/Sentinela/Auditor/Garimpo/Sugestões/Atividades/heartbeats são exatamente as fundações do "Outcome Tracker" e do "motor de sugestões" que ele desenha como futuros. O plano dele de 9 ondas encolhe para **4 blocos** porque não partimos do zero.

**O que ele superdimensionou (e corto):** criar dezenas de documentos de governança antes de conteúdo (viram 1 doc: política de fontes+lifecycle); "warehouse analítico" formal agora (com 2 corretoras reais, broker_insights+scorecards+InfoCap bastam; warehouse entra com 20+ corretoras); consolidar coleções Qdrant (problema de escala futura, não de hoje).

## 2. As VARIÁVEIS que faltavam (pedido do founder — o que ninguém estava enxergando)

O Digital Twin da corretora precisa capturar, além do óbvio:

1. **Condições comerciais POR seguradora** (a que o founder apontou): comissão por ramo, campanhas vigentes, metas de produção/bonificação, contratos de exclusividade, relacionamento com a filial/gerente. → *Toda recomendação de venda considera PARA ONDE é mais lucrativo vender; quem tem condição ruim recebe alternativa (mix, renegociação, volume p/ destravar campanha).*
2. **Apetite de subscrição atual** das seguradoras (o que estão aceitando/recusando por região/perfil — muda todo mês; vem das recusas reais + rede).
3. **Carteira por vigência** = pipeline garantido: renovações dos próximos 90 dias são a venda mais barata que existe; o twin precisa do calendário de vigências (InfoCap já tem).
4. **Sazonalidade e geografia** (enchente no Sul → residencial; dezembro → viagem; frota agrícola → safra).
5. **Capacidade operacional real** (quantos atendimentos/dia a equipe aguenta — plano que estoura capacidade é plano que falha).
6. **CAC e ciclo POR CANAL** (indicação converte 5x anúncio; o plano aloca orçamento por canal com número, não por moda).
7. **Concentração de risco da receita** (60% da comissão numa seguradora = fragilidade a ser apontada).
8. **Inadimplência e cancelamento precoce** (vender mal custa caro — estratégia inclui qualidade da venda).
9. **Momento do dono** (sucessão, sociedade, expansão, cansaço — o Garimpo já captura sinais disso).

## 3. Arquitetura (delta sobre o que existe)

```
Pergunta/gatilho → CLASSIFICADOR (simples? → resposta direta | complexa? → pipeline)
PIPELINE ESTRATEGISTA (Cérebro forte):
  1. Digital Twin (companies.twin + condições comerciais + capacidade)
  2. Dados vivos (InfoCap: carteira, vigências, mix; scorecards; insights)
  3. Conhecimento (RAG global playbooks/cards + tenant)
  4. Web fresca (Firecrawl: mercado local, concorrência, normas)
  5. Cohort (quando houver massa: percentis de corretoras semelhantes)
  → ANALISTA (funil com contas explícitas) → ESTRATEGISTA (3 cenários)
  → CRÍTICO (fura premissas) → PLANO (semanas, responsáveis, KPIs, gatilhos)
  → Outcome (Atividades + Sugestões já medem execução/resposta)
```

## 4. Execução em 4 blocos (intercalados com o trabalho atual)

| Bloco | Entrega | Quando |
|---|---|---|
| **D1 — Digital Twin v1** | `companies.twin` (JSONB): estrutura/comercial/marketing/condições comerciais por seguradora/capacidade/metas; origem observed/declared/verified; onboarding conversacional ("me conta da sua corretora") + auto-enriquecimento Firecrawl (site/GMN/Instagram → observed, corretor confirma) | após os mapas do Cartógrafo |
| **D2 — Estrategista v1** | O pipeline acima como modo do Chat Principal (detector de pergunta estratégica → monta o context pack → resposta com diagnóstico/contas/cenários/plano/fontes). Golden: "100 clientes em 60 dias" com a matemática do funil real da corretora | +1 bloco |
| **D3 — Knowledge Cards** | Formato card no RAG global (princípio→aplicação em seguros→quando não usar→métrica); primeiros 50 cards dos temas nobres (funil, follow-up, renovação, cross-sell, GMN/SEO local, oferta, comissões); chat RAG do founder produz, Fable estrutura | paralelo (chat RAG) |
| **D4 — Sugestões v2 com impacto** | A mensagem semanal ganha o formato sinal→impacto R$→causa→plano→métrica (ex.: "64 propostas sem follow-up ≈ 5 vendas perdidas; plano em 3 passos; posso preparar as mensagens?") usando twin+InfoCap | após D1 |

**Regras herdadas que continuam valendo:** publicação global sempre governada (Alfaiate-style, classes de risco); dado bruto de corretora NUNCA cruza tenants (só agregados/cohorts); jurídico/cobertura = fonte oficial + ressalva profissional; web sempre com data+fonte.

## 5. Decisão de sequência (do líder)

O Cartógrafo vem PRIMEIRO (founder de prontidão com o celular; mapas destravam o atendimento — receita hoje). Na sequência imediata: D1 (twin), que também serve o Memórias/onboarding. D3 roda em paralelo no chat RAG desde já. D2/D4 fecham o ciclo. Meta de prova: os 3 pilotos do GPT (plano de 100 clientes; gargalo da semana; oportunidade não vista) respondidos com dados REAIS da Resulta.
