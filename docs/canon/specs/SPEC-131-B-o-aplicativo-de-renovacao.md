# SPEC-131-B — O aplicativo de Renovação: a loja que dá vontade de abrir, o padrão de todo aplicativo e o lugar onde o comercial confere e envia

> **v1.0 · 13/10/2026** · gerente Opus 5.5 · branch `spec/131-B-o-aplicativo` (da `origin/main` depois do push da 131-A) · rito AAA v13 · **CRÍTICO**.
> Fonte: [proposta](../specs-propostas/SPEC-131-O-APLICATIVO-DE-RENOVACAO.md) §4.6–§4.10 · laudos [I2](../programa-multicalculo/131/LAUDO-I2-A-LOJA-E-AS-TELAS.md) §4–§6,
> [I3](../programa-multicalculo/131/LAUDO-I3-A-APRESENTACAO-E-O-ENVIO.md) §2–§3 · [DESIGN-DO-PADRAO-DE-APLICATIVO](../programa-multicalculo/131/DESIGN-DO-PADRAO-DE-APLICATIVO.md)
> (o detalhe visual mora nele, por §) · [SPEC-131-A](SPEC-131-A-a-madrugada-da-renovacao.md) (a tabela `renovacoes` que esta mostra). 📊 medido · 💭 ilustrativo.

## 0. EXECUTION CARD
```
OUTCOME ........ o corretor abre Aplicativos e VÊ uma loja bonita (capa, ícone premium, estado, prova real); todo aplicativo tem a MESMA
                 estrutura (Início · Configurar · o trabalho feito · Dúvidas, com "Como começar"); a Renovação vem completa: configurar
                 em 1 tela limpa, a aba Renovações (lista e quadro, celular primeiro) com cada renovação da madrugada, a apresentação
                 de RENOVAÇÃO para o cliente e "Enviar pelo WhatsApp" que abre o WhatsApp DO COMERCIAL com a mensagem pronta.
RISCO .......... 6 · segurado 3 (a página) · reversível 2 · semanal 1        SUPERFÍCIE 2 · vários comportamentos + peça nova
PISO ........... CRÍTICO: migration que altera dado (catálogo) · filtro company_id na API · app/
NÍVEL .......... CRÍTICO · builders Opus 5.5 xhigh · juiz ‖ red team Opus 5.5 · JUIZ DE DESIGN (página servida e app, celular e notebook)
O FIO .......... §2 · teste `backend/tests/test_spec131b_o_fio.py` = 1ª entrega da G5, VERMELHO
PARALELISMO .... G1 ‖ G2 ‖ G3 ‖ G4 (arquivos disjuntos, §5) → G5 costura + design
GATES .......... fio · rotas montam + next start + /api/renovacoes · tsc · 5 mutações · 2 corretoras · juiz de design ≥ 90 · bateria
REFERÊNCIA ..... interna: DS-001 §5/§8.6/§8.7/§14 · a fila de atendimentos (o Kanban que já existe) · a "carteira" da 130-A (📊 91)
                 externa: §8
FAIXA .......... 💭 5–7 h · fatia ≤ 1h15
```

## 1. O contrato
**Muda:** a GALERIA que já existe (`/dashboard/auxiliares`, mesma rota) com o card novo para TODOS os aplicativos · a CASCA da página
`[slug]` (abas por `?aba=`) para todos, conteúdo completo só na Renovação · "Aplicativos" na tela (o código segue `auxiliary`, D-131-18) ·
slug `renovacao` e as linhas de catálogo de Cotação e Quem Cobra Menos · Configurar no lugar de Personalização → Serviços (o endereço
antigo redireciona) · a aba Renovações · Meu perfil (Minhas conexões, Meu WhatsApp de trabalho, Ausência) · Equipe (situação de cada um) ·
a variante `situacao="renovacao"` da página do cliente · o envio pelo `wa.me` do comercial.
**Não pode mudar:** o modal da Cobrança (`PainelDeRotinas.tsx`, piloto) · o backend de Serviços (só lido) · a página do canal QCM e a do
QCM v1 (D-130A1-01/08) · tokens globais de cor (proposta à parte, laudo de design §7) · **o produto não envia nada sozinho** · nenhum
WhatsApp é pareado nesta SPEC.

**🔴 Três páginas para três momentos (Founder, 12/10):** a de RENOVAÇÃO (quem já é cliente: relação, "seu seguro hoje × a renovação",
continuidade) é desta SPEC; a de COTAÇÃO (quem ainda não é cliente: venda) é da 132; a do Quem Cobra Menos é a do canal e não muda. Uma
nunca usa a copy da outra (guarda no HTML servido).
**🔴 WhatsApp sem interferência (Founder):** o número de ATENDIMENTO da corretora, o do QUEM COBRA MENOS e o futuro número de TRABALHO de
cada comercial (135) são três conexões separadas, nunca trocadas. Nesta SPEC o envio sai do aparelho de quem clica (`wa.me`); o "Meu
WhatsApp de trabalho" no perfil é só o NÚMERO (para o cliente responder ao dono), sem pareamento e sem tocar em `integrations`.

## 2. O FIO
```
/dashboard/auxiliares (galeria) → card Renovação → /dashboard/auxiliares/renovacao?aba=inicio|configurar|renovacoes|duvidas
 aba=renovacoes → components/aplicativos/renovacao/AbaRenovacoes → QuadroOuLista → GET /api/renovacoes (Next, sessão) →
 backend api/renovacoes.py (company_id da sessão; "minhas" = dono/responsável = eu) → renovacoes + renovacao_eventos + multicalculo_*
 → ?item=<id> (gaveta/tela cheia) → "Ver apresentação": POST /api/renovacoes/<id>/apresentacao → proposta.publicar_renovacao →
 render_proposta(situacao="renovacao") → /r/<token> (share.viewed) → estado `apresentada`
 → "Enviar pelo WhatsApp": POST /api/renovacoes/<id>/envio → telefone do cliente buscado NA HORA (InfoCap) → mensagem_de_renovacao →
   devolve {wa_me_url, texto} (nunca gravado nem logado) → o navegador abre o WhatsApp DO APARELHO → evento `aberto_para_envio` → `enviada`
 → no /r/: "Quero renovar" → wa.me do DONO (Meu WhatsApp de trabalho) | corretora | sem botão: "responda a mensagem que recebeu" (share.clicked)
```

## 2.1 BLOCO 0 (medido na 131-A, [BLOCO0-131-A-LEITURAS](../programa-multicalculo/131/BLOCO0-131-A-LEITURAS.md) e [AO-VIVO](../programa-multicalculo/131/BLOCO0-131-A-AGGER-AO-VIVO.md))
| # | premissa | estado | o que muda |
|---|---|---|---|
| B1 | `wa.me` com 500–700 caracteres | NÃO medido (aparelhos) | o texto do link ≤ 💭 500 + "Copiar a mensagem" SEMPRE ao lado |
| B2 | "cliente desde" | 📊 `/cliente_ligacoes` 0/10 docs; cadeia `nosnum_ren` 0–7 passos (0,8–8,3 anos) | só "renova com a gente há N anos" pela cadeia; nunca "cliente desde" |
| B3 | `?aba=` ao lado de outra pasta dinâmica | por medir (G5) | `test:rotas-montam` + `next start`; não monta → abas no cliente |
| B4 | link direto ao cálculo no Agger | 📊 rota `/cotacao/:ramo/resultados/:idIntegracao` no bundle; clique não provado | "Abrir no Agger" usa o link; texto "se pedir login, entre e volte" |
| B5 | telefone do cliente | 📊 `/renovacoes.fone` ≥ 10 dígitos: 97,6 % e 80,3 % | buscado NA HORA; sem ele, só "Copiar a mensagem" |
| B6 | config de Serviços / `renovacao-maxima` instalada | 📊 0 e 0 | redirect sem migração de dado |
| B7 | telefone verificado do comercial | 📊 0 verificados; `users_v2.phone` 10/10 membros, sem verificação | "Meu WhatsApp de trabalho" confirmado pela pessoa (D-131-41) |
| B8 | o estado da renovação na tela | 📊 a 131-A grava `renovacoes` + eventos; 0 corretoras com o aplicativo instalado | instalar = ligar a madrugada; o botão Ligar mostra o "Como começar" antes |

## 3. Dados — migration `backend/supabase/migrations/20261014_01_spec131b_catalogo.sql` (G1; global, expand-only)
- `auxiliary_templates` + `cover_url text null`, `faq jsonb null`, `featured_rank int null`; UPDATE de `icon` para o nome lucide de cada
  slug (laudo de design §2.4); linhas de catálogo `renovacao` (substitui a vitrine `renovacao-maxima`, 📊 instalada em 0), `cotacao`,
  `quem-cobra-menos` (sem rotina, D-131-21). Nenhum nome de corretora.
- `users_v2`/`company_members`: + `whatsapp_trabalho_e164 text null` e `whatsapp_trabalho_confirmado_em timestamptz null` no MEMBRO
  (por corretora) — G3 grava, G4 lê. ⛔ nada em `integrations`.
APPLY · VERIFY · ROLLBACK escritos antes; aplicada pelo gerente.

## 4. O desenho (o visual exato: laudo de design, por §)
- **Galeria** (§2): híbrida — destaque grande no topo, cards com capa 16:9 para Ligados e Disponíveis (capa GERADA em CSS a partir da cor
  do aplicativo + ícone lucide traço 1.6 como marca; `cover_url` do Founder quando houver, 1600×900 WebP ≤ 150 KB), linha compacta só
  com ícone para "Em breve"; sem emoji; estado com selo; prova = número REAL (execuções em `routine_runs`, renovações do mês) ou nada; sem
  estrelas (D-131-26). Contraste AA: `muted-foreground` no lugar de `text-faint`; botão Ligar com contraste ≥ 4,5:1.
- **Página** (§3): cabeçalho (capa/ícone, nome, frase, estado, botão principal por estado, "Funciona com" em nome humano) · abas `?aba=`
  · Início: o que é → o que faz → o que a corretora ganha → **Como começar** (cada passo com estado, link e "N de M prontos") → atividade
  recente (fonte REAL) → dúvidas. Saem "De onde ele tira a informação" e os slugs crus. Outros aplicativos: a casca com o conteúdo que têm
  (Configurar deles = o painel de hoje; Cobrança intocada).
- **Configurar** (§4), Renovação: O que fazer (calcular · quantas opções 1–3) · Quando (antecedência, padrão 10; "pronto antes das 7h")
  · Com qual conta ("do responsável" padrão · "da corretora"; o decidido vira "✓ Conectado · mudar") · Avançado recolhido (exceções,
  reajuste, teto por noite, antecipação). Popover (não tooltip) para ⓘ; barra Salvar fixa só com alteração. Grava pela config da 131-A.
- **Renovações** (§5): `QuadroOuLista` extraído da fila (sem arrastar); colunas Vai calcular · Calculada · Enviada · (Em negociação ·
  Fechada · Emitida e registrada · Perdida escondidas até alguém chegar lá); selo "Precisa de você"; 4 atalhos-filtro; Minhas · Todas;
  filtros na URL; lista agrupada por vencimento com linha que expande nos 3 cálculos; detalhe = gaveta 520 px (notebook) / tela cheia
  (celular) com barra fixa [Enviar pelo WhatsApp] [Ver apresentação] + Copiar; "Abrir no Agger" pelo link direto (BLOCO 0 B4).
- **Meu perfil** (I2 §5): Dados · Minhas conexões (o MEU Agger; senha nunca volta) · Meu WhatsApp de trabalho (número + confirmar) ·
  Ausência (período + OUTRA pessoa, de lista) · Segurança · Aparência. "Aggers da equipe" sai do modal; Equipe mostra SITUAÇÃO e "pedir
  para conectar".
- **A página de RENOVAÇÃO** (I3 §2.3): hero com o vencimento · o seu seguro hoje × a renovação (R$ e %) · 3 cartões com "por que" (a
  "Sua renovação" em 1º) · "Mostrar só o que muda" · a relação ("renova com a gente há N anos" SÓ com prova pela cadeia `nosnum_ren`) +
  "quem cuida de você" = o dono · sinistro · FAQ de renovação · dock "Quero renovar" / "Tirar uma dúvida" · "Todas as seguradoras"
  recolhida · nunca duelo, QCM, "a melhor das N", econômica/mínima. "Salvar PDF" = imprimir.
- **Envio**: `wa.me/<cliente>?text=` no aparelho de quem clica + "Copiar a mensagem"; evento `aberto_para_envio` (quem, versão);
  telefone na hora, nunca guardado nem logado; `calcular_entregar` segue DESLIGADO.

## 5. Fatias (cada arquivo, UM dono; caminhos do frontend a partir da pasta do smith-web)
| fatia | entrega | arquivos |
|---|---|---|
| **G1 · a loja e a casca** | galeria, card, capa, ícones, casca com abas, Início, Como começar, Histórico real, menu "Aplicativos", catálogo | `app/dashboard/auxiliares/AuxiliaresClient.tsx` · `…/auxiliares/[slug]/page.tsx` · `…/[slug]/AuxiliarDetalheClient.tsx` · `components/aplicativos/casca/*` (NOVOS) · `lib/auxiliaries/catalog.ts` · `lib/navigation.ts` · `app/globals.css` (só o bloco da capa) · `backend/supabase/migrations/20261014_01_spec131b_catalogo.sql` · `docs/canon/GLOSSARIO.md` (1 linha) |
| **G2 · a aba Renovações** | QuadroOuLista, lista/quadro, filtros, detalhe, celular, API de leitura e envio | `components/aplicativos/QuadroOuLista.tsx` (NOVO) · `app/dashboard/atendimentos/fila/AttendanceQueueClient.tsx` · `components/aplicativos/renovacao/*` (NOVOS, menos Configurar) · `app/api/renovacoes/**` · `backend/app/api/renovacoes.py` (NOVO) + o registro do router · `backend/tests/test_spec131b_api_renovacoes.py` |
| **G3 · Configurar, Meu perfil, Equipe** | aba Configurar da Renovação, Cotação e QCM · redirect de Serviços · Minhas conexões · WhatsApp de trabalho · Ausência · Situação | `components/aplicativos/renovacao/AbaConfigurar.tsx` + `components/aplicativos/configurar/*` (NOVOS) · `app/dashboard/personalizacao/servicos/**` · `lib/mock/tenant-modules.ts` · `app/dashboard/configuracoes/**` · `components/perfil/*` (NOVOS) · `components/vault/AggersDaEquipe.tsx` · `components/vault/AggerDaCorretoraModal.tsx` · `app/dashboard/personalizacao/equipe/**` · a API de membros/ausência (o arquivo que o BLOCO 0 apontar) + teste |
| **G4 · a página e a mensagem** | variante de renovação, ordem, relação com prova, dono, `wa.me` | `backend/app/services/artifacts/proposta_html.py` · `backend/app/services/multicalculo/comparacao.py` · `…/proposta.py` · `…/mensagem.py` · `backend/tests/test_spec131b_a_pagina_de_renovacao.py` |
| **G5 · costura + design** | fio verde · rotas · next start · design · mutações | consertos de costura · `backend/tests/test_spec131b_o_fio.py` |

**Contrato:** G1 exporta em `catalog.ts` `ABAS_DO_APLICATIVO: Record<slug, {id, rotulo, componente}[]>` e carrega
`components/aplicativos/<slug>/Aba<Nome>.tsx` por import dinâmico (G2/G3 escrevem, G1 nunca). G4 exporta
`publicar_renovacao(company_id, renovacao_id, *, pessoa) -> {token, url}` e `mensagem_de_renovacao(renovacao, proposta, *, pessoa) ->
{texto, texto_curto, link}`, chamados por `api/renovacoes.py` (G2). G3 grava `whatsapp_trabalho_e164` no membro; G4 o lê.
API: `GET /api/renovacoes?escopo=minhas|todas&estado=&ramo=&de=&ate=&seguradora=&q=` · `GET /api/renovacoes/<id>` ·
`POST /api/renovacoes/<id>/apresentacao` · `POST /api/renovacoes/<id>/envio` (→ `{wa_me_url, texto}`) — company_id SEMPRE da sessão.

## 6. A régua
- **Fio** (G5): de uma renovação `calculada` no banco dublê até `aberto_para_envio`, com o HTML SERVIDO do `/r/`.
- **Mutações (cada mutação provada VERMELHA uma vez, restaura por cópia):** (1) "menor completa em 1º"/"a melhor das N" volta na renovação (guarda no HTML servido) · (2) "N anos" sem
  prova · (3) "Quero renovar" à corretora com dono de WhatsApp confirmado · (4) arrastar um card muda o banco · (5) telefone do cliente
  num log ou numa linha do banco.
- **Isolamento:** a API com duas corretoras (o filtro, não a RLS).
- **Gates de app/** (CLAUDE.md §9.1): `npm run test:rotas-montam` + `next start` + 1 requisição a `/api/renovacoes` + `tsc --noEmit`.
- **Juiz de design**: o checklist de 25 itens do laudo de design §6, no celular e no notebook, nos dois temas, nas 3 telas (galeria,
  página do aplicativo, aba Renovações) + a página `/r/` de renovação. Nota ≥ 90 ou o item vira conserto.
- **Verba:** 💭 ≤ US$ 0,30.

## 7. Decisões desta SPEC
| # | decisão | nota | contra |
|---|---|---|---|
| D-131-38 | A loja melhora NA GALERIA QUE EXISTE (mesma rota), já nesta SPEC, com o card novo para TODOS os aplicativos (Founder 12/10) | 90 | página nova 45 · só depois 60 |
| D-131-39 | Galeria híbrida (capa gerada + ícone lucide; capa do Founder por `cover_url`) | 90 | capa em tudo 72 · só ícone 68 |
| D-131-40 | Três páginas por momento (renovação · cotação · QCM), copy nunca cruzada | F | — |
| D-131-41 | "Meu WhatsApp de trabalho" = só o número, confirmado pela pessoa; nunca pareado aqui; atendimento, QCM e trabalho nunca trocados | 88 | parear já 40 |
| D-131-42 | "Quero renovar": dono confirmado → corretora → sem botão ("responda a mensagem que recebeu"); a página publica sem número da corretora quando o envio é pelo comercial | 85 | recusar publicar 50 |
| D-131-43 | Tokens globais intocados; contraste corrigido nas telas novas; a correção global vira proposta | 80 | mexer em tudo agora 50 |

## 8. O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS
1. **https://www.raycast.com/store** · faz: loja de extensões com ícone forte, nome, frase e instalar em 1 clique · modelamos: o card e o
   estado "Ligado/Instalar" · rejeitamos: contagem de downloads falsa · juiz: abre a galeria e confere ícone + frase + estado em cada card.
2. **https://linear.app/docs/board-layout** · faz: lista ↔ quadro, colunas por estado, colunas escondidas · modelamos: QuadroOuLista ·
   rejeitamos: arrastar (o estado é derivado) · juiz: arrasta um card e confere que o banco não muda.
3. **https://int.ezlynx.com/solutions/renewals-client-retention** · faz: "o que mudou" entre a apólice atual e a renovação · modelamos: o
   seu seguro hoje × a renovação · rejeitamos: o portal do agente · juiz: acha o bloco com R$ e % na página servida.
4. **https://www.nngroup.com/articles/comparison-tables/** · faz: ≤ 5 itens, atributos consistentes · modelamos: 3 cartões + "só o que
   muda" · rejeitamos: > 5 colunas · juiz: conta colunas no celular.
5. **https://apps.shopify.com/shopify-forms** · faz: página de app B2B na ordem cabeçalho → descrição → funciona com → suporte · modelamos:
   a ordem da aba Início · rejeitamos: preço e "apps parecidos" · juiz: compara a ordem das seções.
6. **https://developer.apple.com/app-store/review/guidelines/** (§3, avaliações falsas) · rejeitamos as estrelas fictícias · juiz: nenhum
   card com estrela sem dado.

## 9. O QUE SAIU (fora desta SPEC, com destino)
Negociar e o WhatsApp pareado por pessoa → 135 · página de COTAÇÃO → 132 · emissão → SPEC própria · o modal da Cobrança e os outros
aplicativos com conteúdo completo → SPEC "A loja" (a casca e o card já chegam a todos aqui) · tokens globais → proposta do laudo §7.
