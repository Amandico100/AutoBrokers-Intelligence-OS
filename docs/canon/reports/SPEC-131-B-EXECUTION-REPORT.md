# Relatório de execução — SPEC-131-B: o aplicativo de Renovação

**SPEC:** `docs/canon/specs/SPEC-131-B-o-aplicativo-de-renovacao.md` · proposta `specs-propostas/SPEC-131-O-APLICATIVO-DE-RENOVACAO.md` §4.6–§4.10
**Branch:** `spec/131-B-o-aplicativo` · **base** `e58db51` (a 131-A na `main`) · **final** ver §7 (push)
**Gerente:** Opus 5.5 · protocolo AAA v13.2 · nível CRÍTICO · todos os subagentes declararam `claude-opus-5-5` (D-131-32; telemetria §11)

## 0.0 EXECUTION CARD
```
OUTCOME ........ o corretor abre Aplicativos e vê uma loja bonita; todo aplicativo tem a MESMA estrutura (Início · Configurar · o trabalho
                 feito · Dúvidas, com "Como começar"); a Renovação vem completa: Configurar limpo, a aba Renovações (lista e quadro,
                 celular primeiro), a página de RENOVAÇÃO para o cliente e "Enviar pelo WhatsApp" que abre o WhatsApp DO COMERCIAL
RISCO .......... 6 (segurado 3 · reversível 2 · semanal 1)
SUPERFÍCIE ..... 2 (vários comportamentos + peça nova)
PISO APLICADO .. CRÍTICO: migration que altera dado (catálogo) · filtro company_id na API · app/
NÍVEL .......... CRÍTICO · builders Opus 5.5 · juiz ‖ red team ‖ juiz de design · confirmação · 2 juízes de design de confirmação
O FIO .......... galeria → card → [slug]?aba=renovacoes → QuadroOuLista → /api/renovacoes (sessão) → backend (company_id) → apresentação
                 (publicar_renovacao → /r/) → envio (telefone na hora → mensagem → wa.me no aparelho de quem clica) → `enviada`
PARALELISMO REAL G1 ‖ G2 ‖ G3 ‖ G4 (arquivos disjuntos) → G5 costura; conserto K1 ‖ K2 (backend × tela) → K3 design
UNIDADES ....... 5 fatias + 3 de conserto
COESÃO ......... a casca e o catálogo juntos (G1); a aba e a API juntas (G2); a página e a mensagem juntas (G4)
TIME ........... 8 builders · juiz ‖ red team ‖ juiz de design · confirmação · 2 juízes de design · bateria · atualizador
REFERÊNCIA ..... interna: DS-001 §5 · o laudo DESIGN-DO-PADRAO-DE-APLICATIVO §6 (25 itens) · a "carteira" da 130-A; externa: SPEC §8
GATES .......... fio · tsc · rotas montam · next build + next start + requisição · 5 mutações · 2 corretoras · design ≥ 90 · bateria
O ELO .......... "o cliente recebe a página de RENOVAÇÃO PORQUE o envio publica pela variante" → o teste do fio lê o HTML SERVIDO por
                 `abrir_compartilhado` depois do POST de envio (📊 G5)
FAIXA DE RELÓGIO declarada 💭 5–7 h · real ≈ 14 h (07:22 → 21:45 de 13/10, horário de Brasília): `next build` de 80–115 min nesta máquina (8 GB), coleta do
                 pytest de 7–30 min, e 3 rodadas de design até ≥ 90
```

## 1. Resumo executivo (FATO)
- **A loja** melhorou NA GALERIA QUE JÁ EXISTE: capa gerada por aplicativo (4 composições, cor de cada um), ícones lucide para os 19
  aplicativos (📊 migration: `icones_lucide` 19, `ativos_sem_icone` 0), prova só com número real, sem emoji, sem estrelas. Espaço `cover_url`
  para as capas do Founder (1600×900 WebP ≤ 150 KB).
- **O padrão de aplicativo** (a casca) para TODOS: cabeçalho, abas por `?aba=`, Início na ordem do laudo, "Como começar" com "N de M prontos",
  atividade REAL (o Histórico deixou de mentir), Dúvidas. Cobrança: modal intocado.
- **A Renovação completa:** Configurar (O que fazer · Quando · Com qual conta — "do responsável"/"da corretora" FUNCIONA · Avançado recolhido),
  Personalização → Serviços redireciona para ela; a aba Renovações (lista agrupada por vencimento, quadro sem arrastar, 4 atalhos, Minhas ·
  Todas, detalhe em gaveta/tela cheia com [Enviar pelo WhatsApp] [Ver apresentação] + Copiar + Abrir no Agger).
- **Meu perfil:** Minhas conexões (cada um o SEU Agger), Meu WhatsApp de trabalho (só o número, confirmado pela pessoa; nada pareado; o de
  atendimento e o do QCM são outros e não mudam), Ausência. **Equipe:** a situação de cada pessoa.
- **A página do cliente de RENOVAÇÃO:** "O seu seguro hoje × a renovação", "Sua renovação" em 1º, "renova com a gente há N anos" SÓ com prova,
  "Quero renovar" ao dono confirmado → corretora → sem botão. 📊 cotação e canal idênticos byte a byte (5/5 hashes).
- **O envio:** `wa.me` no aparelho de quem clica; telefone do cliente buscado na hora, nunca gravado nem logado; o produto não envia nada.

## 2. Escopo (FATO — commits)
`c052550` SPEC · `67f86f6` G1 · `006f8e8` G2 · `a194786` G3 · `64ed0ab` G4 · `af7ea4f` G5 · `66feb3e` laudos · `b452d07` K1 · `f148cf9` K2 ·
`c74197d` laudos · `191ecfa` K3 · `173f469` a regressão da bateria. 📊 `git diff --stat 7d41c1f..HEAD` → 87 arquivos, +12.848 / −1.645.

## 4. Migrations
`20261014_01_spec131b_catalogo.sql` — APLICADA pelo gerente (psycopg, transação, `lock_timeout 5s`), versão 📊 `20261013113534`. VERIFY do
objeto 📊 `3·4·19·0·3·0·1·2·2` (= o esperado); comportamental 📊 "celular=aceito, fixo=aceito, sem_mais=recusado, ddd_zero=recusado,
celular_curto=recusado, confirmado_sem_numero=recusado, capa_http=recusado, faq_objeto=recusado, icone_cru=recusado", 0 linha restante.

## 5. Testes e gates
- 📊 Rodada final dirigida (K3): `136 passed` (5 test_spec131b_* + test_spec1310_f3_contas) · `a-loja-e-a-casca.test.mjs` 164 OK ·
  `a-busca-nao-vai-na-url.test.mjs` 11–12 OK · `tsc --noEmit` 0 · rotas montam (322).
- **§9.1 completo:** 📊 `next build` → BUILD_OK (2×: 16:21→~17:40 e 18:58→~21:40) · `next start` + `/api/renovacoes` 401 ·
  `/dashboard/auxiliares` 307 · `?aba=renovacoes` 307 · `/dashboard/configuracoes` 307 · `/dashboard/personalizacao/servicos` 307 ·
  `/api/versao` 200 · 0 erro no log.
- Mutações vermelhas: (1) "a melhor das N"/menor completa em 1º na renovação · (2) "N anos" sem prova · (3) "Quero renovar" à corretora com
  dono confirmado · (4) rota que muda estado por coluna · (5) telefone num log — + as dos consertos (busca na URL, reaproveitar página com
  quem atende mudado, copiar o curto, telefone de `contatos[]`, classe min-h sem CSS, duas parcelas, controle do "Ligar").

## 6. Canário e rollout
Sem canário real nesta SPEC (nada liga: 📊 0 corretoras com o aplicativo instalado). O Founder liga a Renovação numa corretora pelo botão
"Ligar" (com confirmação) DEPOIS de Implantar os 4 serviços juntos (smith-api, smith-worker, portal-worker, smith-web).

## 7. Gate da SPEC
juiz 84 (1 blocker) ‖ red team 72 (3 blockers) ‖ design 82 → conserto K1 ‖ K2 → **confirmação 90** (4 blockers fechados, 9 testes vermelhos com
o conserto revertido) → design 87 (com capturas) → K3 → **design final 91** (página do cliente 93) · bateria 📊 parte A 17 failed · 1836
passed · B 0 · 397 · C 19 · 4363 · triagem 32 iguais, 3 sumiram, 4 novas = 3 de ambiente/pré-existente + **1 regressão** (o guarda da ordem das
seções) → consertada (`173f469`, guarda mede a ordem de renderização, controle vermelho). Push: na resposta ao Founder.

## 8. Mudanças além do texto da SPEC (CHANGE-ADDENDA)
ESSENCIAL: a configuração de Serviços aceita as chaves novas da renovação (sem elas a tela não gravava) · `tailwind.config.ts` `minHeight` =
a escala de spacing (o Tailwind 3.3 não gerava `min-h-11`; o CSS só ganhou classes). VALIOSA: o harness de captura TEMPORÁRIO em `/embed/`
(apagado) — o painel foi VISTO sem criar usuário nem mexer em autenticação.

## 9. Decisões
D-131-40 a loja na galeria que existe · D-131-41 galeria híbrida · D-131-42 três páginas por momento · D-131-43 WhatsApp de trabalho = só o
número confirmado · D-131-44 "Quero renovar" dono → corretora → sem botão · D-131-45 tokens globais intocados · **D-131-46** Serviços aceita
as chaves da renovação (85) · **D-131-47** "com qual conta" ligada de verdade (`servicos.renovacao.conta`) (80) · **D-131-48** "calcular e
preparar o envio" fora da tela (o envio é sempre do comercial) (88) · **D-131-49** a busca vai por cabeçalho, nunca na URL (CPF fora do log)
(95) · **D-131-50** a página do cliente só é reaproveitada se "quem atende" não mudou (90) · **D-131-51** com passo faltando, "Como começar"
sobe para logo depois de "O que é" (85) · **D-131-52** ligar a Renovação exige `confirmar_ligar` no servidor (instalar = ligar a madrugada) (90).

## 10. Riscos remanescentes
- "Todas" vale para todo membro ativo, inclusive atendente, e o envio devolve o telefone do cliente no `wa.me` (J-P5/RT-P6) — **decisão do Founder**.
- O `wa.me` com 500 caracteres não foi medido num aparelho (B1): por isso "Copiar a mensagem" sempre ao lado.
- A Fila de atendimentos (fora da 131-B) tem alvos < 44 px no celular ("Atualizar" 34 px) e o "Close" do Sheet é global em inglês.

## 10.1 📋 CAIXA DO FOUNDER
- **Implantar os 4 serviços juntos** (smith-api → smith-worker → portal-worker → smith-web) — a 131-A e a 131-B andam juntas.
- **Ligar a Renovação** numa corretora: Aplicativos → Renovação → Como começar (os passos) → Ligar. Ligar = a madrugada começa a calcular.
- **As capas dos aplicativos** (opcional): 1600×900, WebP ≤ 150 KB, sem texto — vão em `auxiliary_templates.cover_url`.
- **Decidir** se a atendente vê "Todas" as renovações (hoje vê).

## 11. Impacto para o corretor
Abre Aplicativos e encontra uma loja com cara de loja; entra na Renovação e configura numa tela; toda manhã vê as renovações calculadas, abre a
apresentação, toca "Enviar pelo WhatsApp" e o WhatsApp DELE abre com a mensagem pronta — ele confere e manda.

## 13. ROLLBACK da SPEC inteira
Código: `git revert` dos commits do §2 (o redirect de Serviços volta à tela antiga). Banco: o ROLLBACK da migration recusa se houver instalação
ou número gravado; as colunas novas são anuláveis e a vitrine antiga só foi desativada.

## 📊 A BATERIA — quantas vezes ela rodou nesta SPEC
1 rodada inteira em 3 partes (HEAD `191ecfa`) + reexecução dirigida do guarda consertado.

## §11 A TELEMETRIA (`python backend/scripts/medir_execucao_claude_code.py --sessao atual`, 13/10 ~21:50)
📊 executor (a sessão inteira, 131-A + 131-B) 1.639 min · pico 710 k · US$ 88,82 · agentes da 131-B: G1 15,72 · G2 16,85 · G3 15,36 · G4 21,54 ·
G5 21,93 · juiz 9,86 · red team 8,28 · design 5,86 · K1 22,65 · K2 17,86 · confirmação 5,32 · design 2 5,74 (+ K3, design final e bateria, não
listados ainda pelo script). Todos `opus-5-5`. Achados por mecanismo: teste do fio (publicar com o banco errado, EXCLUSIVO) · juiz (CPF na URL) ·
red team (WhatsApp congelado, Copiar curto, telefone de contato) · juiz de design (contraste, 44 px, aumento como vantagem) · capturas da K2
(o import das abas compilava os testes, EXCLUSIVO) · 2º design (o Tailwind não gerava min-h, EXCLUSIVO) · bateria (a ordem das seções).

**Nota da execução: 89/100** (design 91 visto em captura, confirmação 90, §9.1 completo; falta a prova em produção e o canário com corretor real).
