modelo: claude-opus-5-5

# SPEC-139 — A loja de aplicativos: capas de verdade feitas em código, e todo aplicativo com a mesma casa

> **v1.0 · 14/10/2026** · redator Opus 5.5 · branch `spec/139-a-loja-de-aplicativos` (da `origin/main` depois do push da 131-0-B2) · AAA v13 ·
> **CRÍTICO** (o Configurar da Cobrança governa envio real a segurado). Fonte: programa 8.1 (D-131-28: a loja + a P-16 + a EXTRA-001.9 +
> o modal da Cobrança, "mesmas rotas") · **D-132F-03** (capas em código, sem IA paga; `cover_url` para as do Founder) · D-131-40/41 (a loja
> na galeria que existe, galeria híbrida) · D-131-51 (Como começar) · [laudo de design](../programa-multicalculo/131/DESIGN-DO-PADRAO-DE-APLICATIVO.md)
> §2–§6 · [SPEC-131-B](SPEC-131-B-o-aplicativo-de-renovacao.md) (a casca nasceu lá). 📊 medido · 💭 ilustrativo.
> **Número:** 139 = o próximo livre (📊 `ls docs/canon/specs` + `git grep "SPEC-139"` = 0, 14/10); 133-B · 134 · 135 · 136 · 137 já têm destino
> na fila e 138 é o conector ChatGPT/Claude (PLANO-MESTRE §490).

## 0. EXECUTION CARD
```
OUTCOME ........ o corretor abre Aplicativos e vê uma loja com cara de loja: cada aplicativo com uma capa própria, do mesmo sistema
                 visual, bonita no claro e no escuro; ao abrir QUALQUER aplicativo encontra a mesma casa (Início · Configurar · o trabalho
                 · Dúvidas). A Cobrança sai do modal e entra nessa casa sem mudar UMA regra de envio; o Checklist das 6h, o Follow-up e o
                 Resumo de atendimentos ganham a aba do trabalho no lugar certo; os que não têm trabalho dizem "Em breve" com honestidade.
RISCO .......... 6 · segurado 3 (a Cobrança envia de verdade) · reversível 2 · TODO uso 1
SUPERFÍCIE ..... 2 · refazer peça existente (capa) + mover telas que funcionam
PISO ........... CRÍTICO: config que governa envio real (Cobrança) · rotas novas e redirects em app/ (CLAUDE.md §9.1) · migration de catálogo
NÍVEL .......... CRÍTICO · builders Opus 5.5 xhigh · juiz ‖ red team ‖ JUIZ DE DESIGN (capturas, celular e notebook, 2 temas)
O FIO .......... §2 · `tests/a-loja-de-aplicativos.test.mjs` + `backend/tests/test_spec139_o_fio.py` = 1ª entrega da L6, VERMELHOS
PARALELISMO .... L1 ‖ L2 ‖ L3 ‖ L4 ‖ L5 (arquivos disjuntos, §5) → L6 costura + design
GATES .......... fio · payload da Cobrança idêntico byte a byte · guarda de links internos · rotas montam + next build + next start +
                 1 requisição por redirect · tsc · 6 mutações · 2 corretoras · design ≥ 90 · bateria
O ELO .......... "a Cobrança não mudou PORQUE o Configurar novo grava o MESMO payload" → teste dourado: os mesmos cliques no modal antigo
                 e na aba nova produzem o MESMO corpo de requisição (📊 hash)
FAIXA .......... 💭 6–8 h · ⚠️ `next build` 80–115 min nesta máquina (131-B): só a L6 constrói
```

## 1. O contrato
**Muda:** a capa de TODO aplicativo (o MESMO `CapaGerada.tsx`, agora composição SVG em código — nunca um componente ao lado) · a paleta
por aplicativo como tabela única · a Cobrança (`cobranca-feita`) na casca: Início · Configurar (o conteúdo do modal) · Cobranças (o que saiu)
· Dúvidas · o Checklist das 6h, o Follow-up do WhatsApp e o Resumo de atendimentos com a aba do trabalho em `[slug]?aba=` (P-16), os
endereços antigos redirecionam · os "em breve" com a casca honesta · a EXTRA-001.9 (as rotas de Personalização, §4.5).
**Não pode mudar:** nenhuma regra de envio da Cobrança (o backend `billing_*` e `platform_outbound.py` intocados; o payload salvo idêntico) ·
a Renovação, a Cotação Rápida e o QCM (só a capa muda) · `cover_url` vence a capa gerada · tokens globais de cor (D-131-45) · nenhuma prova
inventada (número só com fonte, sem estrela — D-131-26).

## 2. O FIO
```
/dashboard/auxiliares → AuxiliaresClient → CardDoAplicativo → CapaGerada(slug → paleta + composição SVG; cover_url vence) →
/dashboard/auxiliares/cobranca-feita?aba=configurar → ABAS_DO_APLICATIVO['cobranca-feita'] → components/aplicativos/cobranca/AbaConfigurar
→ o MESMO formulário extraído de PainelDeRotinas → a MESMA rota de gravação (corpo idêntico) → a rotina da corretora (company_id da sessão)
→ ?aba=cobrancas → leitura do que saiu (routine_runs / billing_sent_log, só da corretora) · /dashboard/auxiliares/galeria/follow-up-whatsapp
→ 307 → /dashboard/auxiliares/follow-up-whatsapp?aba=… (idem resumo-atendimentos, checklist-6h/hoje)
```

## 2.1 BLOCO 0
**📊 Já lido (14/10):** `CapaGerada.tsx` = CSS (`.capa-aplicativo` em `globals.css`), 4 composições por hash do ícone, `--app-h` = matiz,
`cover_url` primeiro com queda para a gerada · 19 aplicativos com ícone lucide e matiz (laudo §2.4; migration `20261014_01`) · o modal da
Cobrança = `components/auxiliares/PainelDeRotinas.tsx`, montado por `[slug]/AuxiliarDetalheClient.tsx` · as telas fora do lugar:
`galeria/follow-up-whatsapp/page.tsx` e `galeria/resumo-atendimentos/page.tsx` (P-16) e `auxiliares/checklist-6h/hoje/page.tsx` · a EXTRA-001.9
(DIAGNOSTICO 12/09 §286): `personalizacao/agentes/even`, `equipe`, `conhecimento`, `custos` → "corretora/", com redirects + guarda de `href`
+ tirar "Even" da Prontidão (📊 `personalizacao/corretora/` já existe com `dados`, `identidade`, `suporte-humano`, `whatsapp`).

| # | a medir | o que muda |
|---|---|---|
| B1 | quais aplicativos têm trabalho REAL (📊 `routine_runs`/instalações por slug, 2 corretoras) | com trabalho → aba do trabalho nesta SPEC; sem → "Em breve" |
| B2 | a rota e o corpo que o modal da Cobrança grava (captura no navegador ou leitura) | vira o teste dourado do ELO |
| B3 | a fonte de "o que saiu" da Cobrança (`billing_sent_log`? `routine_runs`?) e se há leitura por `company_id` pronta | sem leitura pronta → endpoint de LEITURA novo, só select com filtro |
| B4 | o destino da 001.9: `/dashboard/corretora/` ou `/dashboard/personalizacao/corretora/` (o texto diz "corretora/") | o que já existe vence: `personalizacao/corretora/` (💭 85 × pasta nova 50) — registrar |
| B5 | `lucide-react` expõe o desenho do ícone (`iconNode`) para entrar DENTRO do SVG da capa? | sim → o ícone é `<g>` da capa · não → ícone sobreposto em HTML (como hoje) |

## 3. A direção de arte (D-132F-03) — 2 a 3 direções ANTES de produzir as 19
**O sistema (vale para qualquer direção):** tela `viewBox 0 0 1600 900` (16:9), área segura de 80 px, recortes do card (16:9) e do
cabeçalho (4:1) conferidos; **cor por aplicativo** = a matiz do laudo §2.4 numa tabela única `paleta.ts` (OKLCH, mesma luminosidade e croma
para todos — nenhum "grita" —, vizinhos na galeria com ≥ 18° de distância; claro e escuro por variáveis, nunca duas artes); **ícone lucide**
com traço 1.6 como assinatura; **sem texto, sem emoji, sem foto**; ≤ 4 KB de SVG por capa, zero requisição; `prefers-reduced-motion`
respeitado (no máximo um leve deslocamento no hover). Determinística por slug (a mesma capa hoje e daqui a um ano).
**As direções (a prancha):**
- **A · Placa** — o ícone num tile grande e arredondado no terço esquerdo, sobre o degradê da matiz, com 2–3 arcos concêntricos saindo da
  borda direita. Calma, "loja de aplicativos". 💭 nota 85 (lê bem pequena; a mais segura).
- **B · Traço** — o ícone ampliado ~3×, cortado pela borda, só linha, sobre uma grade de pontos na matiz. Técnica e elegante. 💭 82 (pode
  ficar fria no claro).
- **C · Cena** — três formas do TRABALHO de cada aplicativo (cartão, bolha, calendário, documento, gráfico) em perspectiva leve + o ícone
  num selo. Conta o que o aplicativo faz. 💭 78 (19 cenas = mais tempo e mais risco de inconsistência).
**A prancha:** 3 direções × 4 aplicativos (Renovação, Cobrança, Checklist das 6h, um "em breve") × claro/escuro, no card E no cabeçalho —
publicada pelo gerente como página privada para o Founder escolher no BLOCO 0. Enquanto ele não responde, andam L2–L5 (não dependem da capa);
se a L1 chegar à produção sem resposta, vai a de maior nota (A) e a escolha é registrada (trocar depois = só `composicoes.tsx`). Se o
Founder não gostar de nenhuma: ele envia as dele (ChatGPT) e elas entram por `cover_url` (1600×900 WebP ≤ 150 KB, sem texto).

## 4. O desenho (o detalhe visual: laudo de design §2–§5)
1. **Galeria:** o card de hoje com a capa nova; destaque no topo; "Em breve" em linha compacta só com ícone (laudo §2.2). Prova = número
   real ou nada.
2. **Cobrança na casca:** Início (o que é → o que faz → o que a corretora ganha → Como começar: portal conectado · número de envio · regras ·
   "N de M prontos") · **Configurar** = o formulário do modal EXTRAÍDO (mesmo estado, mesmas validações, mesma gravação), no layout do laudo
   §4 (grupos, Popover no ⓘ, barra Salvar só com alteração, 409 humano) · **Cobranças** = o que saiu (lista por dia: segurado mascarado,
   parcela, situação; filtro por período; só leitura) · Dúvidas. O botão antigo que abria o modal leva à aba Configurar.
3. **Checklist das 6h · Follow-up do WhatsApp · Resumo de atendimentos:** a tela que já funciona vira a aba do trabalho (o conteúdo MOVIDO,
   não reescrito), cada endereço antigo dá 307 para o novo.
4. **Em breve** (o que a B1 disser): Início honesto ("o que ele vai fazer"), Dúvidas, selo "Em breve", **sem** botão Ligar.
5. **EXTRA-001.9:** `agentes/even` → `corretora/agente-de-atendimento`, `equipe`, `conhecimento`, `custos` para o destino da B4, cada antigo
   com redirect; o menu (`lib/navigation.ts`) aponta para o novo; o guarda casa TODO `href` interno com a tabela de rotas (o `rotas-montam`
   não valida links); "Even" sai da tela Prontidão (o nome oficial é AutoBrokers — CLAUDE.md §1).

## 5. Fatias (cada arquivo, UM dono; caminhos a partir da raiz do smith-web)
| fatia | entrega | arquivos |
|---|---|---|
| **L1 · as capas** | sistema, paleta, 3 direções, prancha, as 19 | `components/aplicativos/casca/CapaGerada.tsx` · `components/aplicativos/casca/capas/{paleta.ts,composicoes.tsx}` (NOVOS) · `app/globals.css` (só o bloco `.capa-aplicativo`) · `scripts/prancha-das-capas.mjs` (NOVO) · `components/aplicativos/casca/capas.test.mjs` (NOVO) |
| **L2 · a Cobrança** | Configurar extraído, Cobranças, Início | `components/auxiliares/PainelDeRotinas.tsx` (só a extração) · `components/aplicativos/cobranca/*` (NOVOS) · a leitura do que saiu (o arquivo que a B3 apontar, só leitura) · `tests/a-cobranca-na-casca.test.mjs` |
| **L3 · as telas no lugar (P-16)** | Checklist, Follow-up, Resumo como abas + redirects | `components/aplicativos/{checklist-6h,follow-up-whatsapp,resumo-atendimentos}/*` (NOVOS) · `app/dashboard/auxiliares/checklist-6h/**` · `app/dashboard/auxiliares/galeria/{follow-up-whatsapp,resumo-atendimentos}/**` |
| **L4 · a casca para todos** | catálogo das abas, "Em breve", conteúdo | `lib/auxiliaries/catalog.ts` · `app/dashboard/auxiliares/AuxiliaresClient.tsx` · `app/dashboard/auxiliares/[slug]/AuxiliarDetalheClient.tsx` · `components/aplicativos/casca/{AbaInicio,ComoComecar,CardDoAplicativo}.tsx` · `backend/supabase/migrations/20261016_01_spec139_conteudo_dos_aplicativos.sql` (global, só `faq`/frases; APPLY/VERIFY/ROLLBACK) |
| **L5 · EXTRA-001.9** | rotas de Personalização, menu, guarda de links, "Even" | `app/dashboard/personalizacao/{agentes,equipe,conhecimento,custos,prontidao}/**` · o destino da B4 · `lib/navigation.ts` · `tests/links-internos-casam-rotas.test.mjs` (NOVO) |
| **L6 · costura + design** | o fio, §9.1, capturas, conserto de design | consertos de costura · `tests/a-loja-de-aplicativos.test.mjs` · `backend/tests/test_spec139_o_fio.py` |

**Contrato (o da 131-B):** L4 registra em `ABAS_DO_APLICATIVO` as abas `cobranca-feita: inicio|configurar|cobrancas|duvidas`,
`checklist-6h: inicio|hoje|configurar|duvidas`, `follow-up-whatsapp` e `resumo-atendimentos: inicio|<trabalho>|configurar|duvidas` e carrega
`components/aplicativos/<slug>/Aba<Nome>.tsx` por import dinâmico — L2/L3 escrevem esses arquivos, L4 nunca. L1 mantém a assinatura de
`CapaGerada` (`icone, matiz, coverUrl, className, marca, esmaecer, crescerNoHover`) + `slug` opcional. Redirect = `redirect()` na
`page.tsx` antiga (nunca pasta dinâmica nova na mesma posição — CLAUDE.md §9.1). Só a L6 roda `next build`.

## 6. A régua
- **Mutações (cada uma VERMELHA uma vez; restaura por cópia):** (1) o Configurar novo grava um corpo diferente do modal (o dourado do ELO) ·
  (2) capa com texto, emoji ou `<img>` externa sem `cover_url` · (3) "Cobranças" mostra linha de OUTRA corretora · (4) um `href` interno
  sem rota (o guarda) · (5) um endereço antigo sem redirect (404) · (6) aplicativo "Em breve" com botão Ligar.
- **Isolamento** com duas corretoras reais na leitura da Cobrança (o filtro, não a RLS).
- **§9.1:** `npm run test:rotas-montam` + `next build` + `next start` + uma requisição a cada endereço antigo (307) e novo (200/307) +
  `tsc --noEmit`. ⚠️ P-132D-01: o Implantar do `smith-web` só fora do horário de atendimento, e depois da T-174 (swap).
- **Juiz de design ≥ 90, com capturas** (celular 390 px e notebook 1440 px, claro e escuro; harness temporário em `/embed/` como na 131-B,
  apagado no fim): galeria, a página de 4 aplicativos, o Configurar da Cobrança, as 3 abas movidas. O checklist de 25 itens do laudo §6 +
  os da capa: as 19 juntas numa grade (sistema único? vizinhos distintos?), o ícone legível no card pequeno, nenhum texto, o recorte 4:1
  sem cortar o ícone, escuro sem "lavar" a cor. Nota < 90 → o item vira conserto.
- **Verba:** 💭 US$ 0 (nenhuma chamada paga; as capas são código).

## 7. Decisões desta SPEC
| # | decisão | nota | contra |
|---|---|---|---|
| D-139-01 | A capa vira composição SVG DENTRO do `CapaGerada` que existe | 90 | componente novo ao lado 30 (peça paralela) · IA de imagem 0 (D-132F-03) |
| D-139-02 | Uma paleta única (OKLCH, mesma luz e croma) a partir das matizes do laudo | 88 | cor livre por aplicativo 50 |
| D-139-03 | A direção vem da prancha, escolhida pelo Founder; sem resposta, a de maior nota (A) | 85 | produzir as 19 numa direção só 55 |
| D-139-04 | A Cobrança entra na casca pelo formulário EXTRAÍDO, com teste dourado do corpo | 90 | reescrever o formulário 40 (risco em envio real) · manter o modal 50 (D-131-28) |
| D-139-05 | As telas da P-16 e o Checklist são MOVIDAS (não reescritas), com 307 | 88 | reescrever 45 |
| D-139-06 | A EXTRA-001.9 entra como a última fatia paralela, com o guarda de links | 80 | ficar de fora 55 (D-131-28 a pôs aqui; reduzir escopo é do Founder) |

## 8. O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS
1. **https://developer.apple.com/app-store/product-page/** · faz: a página do aplicativo com ícone, imagens e texto curto em ordem fixa ·
   modelamos: a capa como "imagem de vitrine" sem texto e a ordem do Início · rejeitamos: avaliações e downloads · juiz: compara a ordem e
   procura texto na capa.
2. **https://support.google.com/googleplay/android-developer/answer/9866151** (recursos de visualização, "feature graphic") · faz: uma
   imagem de destaque com proporção fixa e área segura · modelamos: 16:9, área segura de 80 px e os recortes · rejeitamos: texto dentro da
   arte · juiz: confere o recorte 4:1 do cabeçalho.
3. **https://lucide.dev/guide/design/icon-design-guide** · faz: grade 24 px, traço 2, cantos arredondados, consistência · modelamos: o ícone
   como assinatura com traço uniforme (1.6) em todas as capas · rejeitamos: misturar ícones de outra família · juiz: abre 5 capas e confere
   o traço.
4. **https://www.raycast.com/store** · faz: loja com ícone forte, nome, frase e estado · modelamos: o card (D-131-40) · rejeitamos: contagem
   de instalações falsa · juiz: nenhum número sem fonte.
5. **https://linear.app/integrations** · faz: um diretório onde todo item segue o mesmo molde visual · modelamos: as 19 capas como UM sistema
   · rejeitamos: arte individual sem regra · juiz: a grade das 19 numa captura só.

## 9. O QUE SAI (com destino)
Vida e moto → 8.2 (129-D) · a página dos outros ramos → 130-C (D-129C-08) · o conteúdo completo dos "em breve" → a SPEC de cada um · tokens
globais → a proposta do laudo §7 · capas desenhadas pelo Founder → entram por `cover_url`, sem SPEC · Cobrança estável e o religar → fim da
fila (D-1311-02) — aqui só muda a CASA, nunca a regra.
