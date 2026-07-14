# PROMPT — Claude Design: aba MEMÓRIAS (Segundo Cérebro) + superfícies admin

> Como usar: cole este prompt no Claude Design. Anexe junto: (1) o arquivo
> `docs/canon/DS-001-design-brief.md` (direção visual canônica do AutoBrokers),
> (2) prints do dashboard e do portal admin atuais, (3) os prints do Obsidian
> (graph view) que inspiraram o conceito. Se o Claude Design puder navegar,
> aponte o dashboard em produção para ele sentir o tom atual.

---

Você vai desenhar a experiência **"Memórias"** do AutoBrokers.ai — o segundo
cérebro visual do corretor de seguros — e 3 superfícies do portal admin.
Leia o DS-001 antes: o produto deve parecer **um ChatGPT/Claude especializado
em seguros**, não um SaaS de cards; dark theme primeiro; sofisticação sóbria.

## Contexto do produto
AutoBrokers é um SaaS multi-tenant para corretoras de seguros no Brasil. Cada
corretora tem vários usuários (dono, gestores, vendedores). O conhecimento vive
em 3 camadas: **Global AutoBrokers** (biblioteca curada por nós: jurídico,
marketing, vendas, finanças — valiosa e protegida), **Corretora** (docs e dados
da empresa, incl. operação via InfoCap) e **Pessoal** (memórias do usuário:
conversas, e-mails conectados, fatos que a IA aprendeu). O Chat Principal usa
tudo isso para responder "mastigado".

## Tela 1 — Memórias (dashboard do corretor) — A ESTRELA
Uma aba "Memórias" com um **grafo de conhecimento interativo** (referência:
Obsidian graph view; implementação alvo: react-force-graph 2D/canvas, dark).

Requisitos de experiência:
1. **Cores por camada**: Global = dourado/âmbar; Corretora = azul; Pessoal =
   verde. Legenda discreta fixa. Nós maiores = mais conectados/mais usados.
2. **Pastas/temas como constelações**: Jurídico, Marketing, Vendas, Finanças,
   Seguradoras, Clientes — clusters visualmente separáveis; filtro por tema e
   por camada (chips no topo).
3. **Hover** (o momento uau): acende o nó + vizinhos, esmaece o resto, mostra
   tooltip com título + origem + data. **Clique**: painel lateral com o resumo
   do conteúdo, fonte, "perguntar ao Chat sobre isso" (CTA que abre o chat com
   contexto) e conexões navegáveis.
4. **Conteúdo global BLOQUEADO por plano**: nós dourados aparecem SEMPRE (o
   corretor VÊ o tamanho da biblioteca — percepção de valor), mas com cadeado
   quando o plano não inclui; clique → paywall elegante ("Biblioteca Jurídica
   AutoBrokers — disponível no plano X"). O conteúdo bruto NUNCA é exportável;
   quem usa é o Chat, citando a fonte.
5. **Busca** proeminente ("pesquise em tudo que eu sei sobre o seu negócio") —
   resultado destaca os nós no grafo, não vira lista fria.
6. **Estado vazio bonito** (corretora nova): poucas estrelas + convite ("conecte
   seu e-mail / suba seus documentos e veja seu cérebro crescer") — o grafo
   crescendo é retenção.
7. Performance: até ~3k nós fluidos; degradar com elegância (agrupar clusters).

## Telas 2-4 — Portal Admin (gestão interna; visual mais operacional, mesmo DS)
2. **Central de Agentes**: os agentes do sistema (Espelho, Vigia, Sentinela,
   Cérebro, Cartógrafo, Alfaiate, Auditor, Garimpo, Sugestões) como cards vivos:
   o que faz (1 frase), último run, ações nas últimas 24h, saúde. Para operadores
   humanos novos entenderem o organismo em 1 minuto.
3. **Acionamentos ao vivo**: lista das sessões com seguradoras (estado, tempo,
   seguradora, corretora) + timeline do transcript + badges de intervenção da
   Sentinela e alertas do Vigia.
4. **Insights (Garimpo)**: dores/desejos/pedidos dos corretores ranqueados, com
   filtro por corretora e agregado global; e o histórico da IA de Sugestões
   (enviado × respondido).

## Restrições técnicas (para o design ser implementável)
- Next.js + Tailwind + shadcn no dashboard; /admin usa componentes nativos.
- Dark theme primeiro (o produto vive nele); light como variação.
- Mobile: Memórias vira lista rica com mini-grafo (canvas full só desktop).
- Entregáveis: direção visual + specs de componente (estados hover/loading/
  empty/locked) + tokens usados — prontos para Claude Code implementar.
