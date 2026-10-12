# LAUDO I2 — A loja, as telas e onde mora cada conexão (SPEC-131 · partes A e C do pedido)

> 🔍 Investigador I2 · modo INVESTIGAÇÃO (protocolo AAA v13 §3.3/§8) · 12/10/2026 · branch `investigacao/2026-10-12-renovacao`
> READ-ONLY: nenhum código tocado. Banco só SELECT (`dcajcvlzcjbmyapmklil`). Sem PII.
> Lido: PEDIDO-DO-FOUNDER-2026-10-12 · DS-001 (§5.4, §8.3–8.7, §9.3, §14) · GLOSSARIO (Auxiliar × Rotina) · ONTOLOGIA-DO-TRABALHO
> (erros 1–4) · 6 prints do Founder · as 4 pastas de `docs/intake/TELAS AUXILIARES/` · o frontend real (abaixo, por arquivo:linha).
> Marcação: **FATO** (arquivo:linha ou comando) · **INFERÊNCIA** · **RECOMENDAÇÃO** (nota 0–100). 📊 medido · 💭 ilustrativo.

---

## 0. Os fatos de base (medidos)

| # | fato | comando / fonte |
|---|---|---|
| F1 | O Next.js mora em `app/` na raiz (`app/dashboard/...`). `app/app/` e `app/backend/` são lixo antigo, não montam rota de dashboard. | `Get-ChildItem app -Directory` |
| F2 | 📊 **Galeria, página e modal NÃO mudaram desde 23/09.** Desde então só entraram Serviços e Aggers da equipe: `08e7f77` (F4 Serviços), `0452b18` (F3 Aggers da equipe), `9ab0cf3` (conserto), todos de 11/10. Os prints de `TELAS ATUAIS` (datados 23/09 na barra do Windows) **ainda são a tela de hoje**. | `git log --since=2026-09-23 -- app/dashboard/auxiliares components/auxiliares lib/auxiliaries app/dashboard/configuracoes components/vault/AggersDaEquipe.tsx app/dashboard/personalizacao/servicos` |
| F3 | 📊 Catálogo: **16** Auxiliares, **6** disponíveis e **10** "em breve" (62%). Renovação = `renovacao-maxima`, `coming_soon`, exige `infocap`. **Não existe** template de Cotação nem de Quem Cobra Menos. | `select slug, catalog_state … from auxiliary_templates` |
| F4 | 📊 `renovacao-maxima` **não está instalada em nenhuma corretora** (zero linhas em `tenant_auxiliaries` com esse slug) → trocar o slug custa zero dado. | `select slug, status from tenant_auxiliaries` |
| F5 | 📊 `multicalculo_config` tem **0 linhas** → ninguém salvou a tela Serviços ainda → mudar a tela de lugar não migra dado nenhum. | `select count(*) from multicalculo_config` |
| F6 | `auxiliary_templates` tem a coluna `icon` (texto: `aprovacao`, `success`, `auxiliares`, `null`), mas o leitor do catálogo **não a seleciona** (`lib/auxiliaries/catalog.ts:258-261`). Não há coluna de banner, imagem, FAQ nem avaliação. | `information_schema.columns` + catalog.ts |
| F7 | 📊 **O Histórico da página mente**: a Cobrança Feita da Resulta tem **18** `routine_runs` (último 11/09 14:01 UTC) e `tenant_auxiliaries.last_run_at = NULL`; a página lê `last_run_at` (`AuxiliarDetalheClient.tsx:347`) e escreve "Ainda não rodou nenhuma vez" — o mesmo print mostra 3 execuções logo acima. | SELECT com `routine_runs ⋈ routines` por `tenant_auxiliary_id` |
| F8 | `company_members` tem `funcoes`, **não tem substituto/férias**; `integrations` **não tem dono-pessoa** (WhatsApp por usuário não existe); `portal_accounts.dono_user_id` existe (Agger por pessoa existe); `tenant_connections.owner_user_id` existe (conexão pessoal OAuth, SPEC-044). | `information_schema.columns` |

---

## 1. O nome — Auxiliar · Aplicativo · App · outro

**FATO (custo de renomear):**
- UI/lib: 📊 **172** linhas não-comentário com "Auxiliar" em **31** arquivos (a maioria identificador: `lib/auxiliaries/contract.ts` 43, `types.ts` 23); texto VISÍVEL 💭 estimado em 40–60 linhas em ~15 arquivos (não contei uma a uma). Menu: **1** linha (`lib/navigation.ts:31`).
  Comando: `Select-String "Auxiliar" -CaseSensitive` em `app/dashboard, components, lib`, excluindo `//`, `*`, `import`.
- Backend: 📊 **499** linhas com `auxiliar|auxiliary` em **82** arquivos de `backend/app`; **75** linhas com "Auxiliar" nos prompts/agentes (`backend/app/agents`, `prompts`).
- Banco: 📊 **12** tabelas com `auxiliar`/`routine` no nome; **7 de 16** textos de catálogo usam a palavra.

| opção | corretor | glossário | custo | nota |
|---|---|---|---|---|
| **"Aplicativo" SÓ NA TELA** (menu "Aplicativos", texto "aplicativo"); código, banco e canon continuam `auxiliary`/Auxiliar; GLOSSARIO ganha a linha *"Aplicativo = o nome do Auxiliar na tela"* | entende na hora (celular/loja); tira o medo de "agente de IA" que o Founder citou | preserva a regra: **Aplicativo TEM Rotina, Aplicativo NÃO É Rotina** | ~1 menu + ~40–60 strings + 7 textos de catálogo + 1 frase de sinônimo no prompt do chat | **84** |
| "App" só na tela | curto, cabe em chip; anglicismo para corretor 50+ | igual | igual | 62 |
| manter "Auxiliar" | "auxiliar" soa a pessoa/estagiário, não a produto que se instala | já está | zero | 55 |
| "Aplicativo" em TUDO (código + banco + canon) | igual ao 1º | sinônimo some | 499+172 linhas, 12 tabelas, migration de renome → risco sem ganho para o corretor | 25 |
| "Serviço" | colide com a tela "Serviços", com `servico` do multicálculo e com **serviço de assistência** (guincho, chaveiro) do atendimento | colisão | médio | 30 |
| "Assistente" | é exatamente o "agente de IA" que o Founder quer evitar | — | médio | 30 |

**RECOMENDAÇÃO (84):** "Aplicativos" no menu e nos títulos; "aplicativo" no texto. Nada muda no código/banco. Uma linha no
GLOSSARIO e uma no prompt do chat ("quando o corretor disser *aplicativo de renovação*, é o Auxiliar `renovacao`"). ⚠️ A troca
no menu vale para TODOS os auxiliares — é uma string (`lib/navigation.ts:31`), e por isso cabe na 131 sem custo.

---

## 2. Estado atual das telas

### 2.1 Galeria (`app/dashboard/auxiliares/AuxiliaresClient.tsx`, 245 linhas)
**Funciona:** uma tela só com todos os Auxiliares, nenhum escondido (`:14-17`); grupos "Trabalhando para você / Disponíveis / Em breve"
(`:50-69`); filtro por RESULTADO, não por módulo (`:182-216`); "falta conectar" dito no card (`:107-113`).
**Ruim (Founder: "ícones infantis", sem imagem/logo) — conferido:**
- o card é nome + selo + frase + chips (`:71-125`); **sem ícone, sem imagem**, embora o banco tenha `icon` (F6);
- as categorias são **emoji** 💰📈🤝⚖️🛡️⏱️ (`lib/auxiliaries/catalog.ts:131-138`) — **contra o DS-001 §14** ("evitar ícones … coloridos demais"); é a fonte do "infantil";
- o Checklist mostra **6 chips** de categoria no mesmo card (print) → ruído;
- 📊 10 de 16 são "em breve" (F3): a vitrine é mais promessa do que produto;
- busca de `w-40` (`:224`) e textos `text-[10px]/[11px]`.

**As "30 avaliações fictícias" (pedido A):** **REJEITAR — nota 10.** FATO: a Apple expulsa quem usa *"fake feedback"* (App Review
Guidelines, introdução da §3); no Brasil é publicidade enganosa (CDC art. 37 — o projeto já usa esse artigo em D-131-0-12).
Uma corretora que descobre uma avaliação inventada deixa de confiar no número de verdade também.
**Em vez disso (85):** prova MEDIDA no card, quando existir: "📊 1.214 renovações calculadas este mês nas corretoras" / "usado por N
corretoras"; e uma avaliação REAL de 1 toque para quem usa o aplicativo há ≥ 7 dias. Sem número real, o card não mostra estrela.

### 2.2 Página do Auxiliar (`app/dashboard/auxiliares/[slug]/AuxiliarDetalheClient.tsx`, 363 linhas)
**Funciona:** rota dinâmica ÚNICA (`[slug]/page.tsx:6-9`); "instalar ≠ ligar", ligar é o último passo (`:215-221`, `:294-343`);
"desligar não apaga nada" (`:318-321`); o motivo de não poder ligar é dito.
**Ruim (Founder: nota 50, poluída, subtítulos apagados, sem banner/logo) — conferido:**
- **subtítulos apagados:** todo título de seção é `text-xs uppercase text-muted-foreground` (`:27`); as explicações são
  `text-[11px] text-faint` (`:175, :208, :248, :269, :318, :333`) → contraste baixo de propósito, em 9 seções numa coluna só (`max-w-3xl`, `page.tsx:36`);
- **sem abas** — o DS-001 §8.7 JÁ manda abas na página do Auxiliar ("Resumo · Configuração · Conectores · Permissões · Execuções");
- **"De onde ele tira a informação"** mostra slug cru com `_` trocado por espaço: "portal seguradora", "whatsapp" (`:162-179`);
- **"Conexões que ele usa"** mostra o SLUG como nome: "insurance portal", "whatsapp zapi" (`:186-195`; `catalog.ts:324` só guarda slugs);
- a frase "A conexão é da corretora" (`:209-210`) fica FALSA quando a conexão for do usuário (Agger dele, WhatsApp dele);
- **Histórico mente** (F7);
- "Executar agora" leva para telas fora da rota (P-16: `galeria/follow-up-whatsapp`, `galeria/resumo-atendimentos`).

### 2.3 Modal de rotina (`components/auxiliares/PainelDeRotinas.tsx`, 1.504 linhas)
**Funciona:** o erro mora dentro do modal (`:1014-1019`); o campo inerte "Conhecimento" sai da cobrança (`:1074-1091`); o modo de
envio só oferece o que tem motor (`:1149-1153`).
**Ruim (Founder: confuso, sem hierarquia, informação não editável repetida) — conferido:**
- **repete o que não se edita:** "Rotina de" com o nome fixo (`:1028-1033`) e o parágrafo "O que este Auxiliar faz" em leitura (`:1052-1061`);
- **mistura três assuntos num modal:** o QUÊ (seguradoras, limite, intervalo de dias), o COMO FALA (quem assina, mensagem com
  `{placeholders}` crus, número de teste) e o QUANDO (diária/N minutos, dias, horário, entrega) — tudo num `max-w-lg` (`:1007`)
  com grade de 2 colunas que espreme o texto (print MODAL PARTE 1/2);
- lista as ~14 seguradoras com a maioria DESABILITADA ("sem credencial"/"em breve", `:1111-1143`);
- **contra o DS-001 §8.6:** "não usar modal gigante para configurações longas".

### 2.4 Serviços (`app/dashboard/personalizacao/servicos/ServicosClient.tsx`, 509 linhas)
**Funciona:** um manual por serviço (abas Cotação · Renovação · QCM, `:207-219`); a chave calcular × entregar × negociar (`:47-60`);
exceções por ramo/valor (`:376-434`); proteção contra dois admins (versão/409, `:182-186`); os "4 passos" com estado (`:333-374`).
**Ruim — e o "erro de lugar" do Founder tem raiz escrita:** a proposta da 131-0 decidiu **D-131-0-08 = "os serviços COMO AUXILIARES do
catálogo" (nota 88)** (`specs-propostas/SPEC-131-0-…md:347`, árvore em `:257-261`); a execução F4 criou uma aba em Personalização.
A tela seguiu o backend, não a ontologia. Mais: seguradora preferida é **texto livre** "Nome da seguradora" (`:495-499`) → grafia errada
vira preferida que nunca casa; QCM aparece como aba que não se edita (`:221-229`).

### 2.5 Meu perfil (`app/dashboard/configuracoes/page.tsx`, 360 linhas)
**Funciona:** dados pessoais, senha, tema.
**Ruim (Founder: subaproveitado) — conferido:** só 4 abas (`:157-183`); "Preferências e integrações" são DOIS placeholders
"em breve" (`:365-380`); **"Uso e Custos" da CORRETORA** mora no perfil pessoal (`:185-197`, "da sua corretora") e TAMBÉM em
`app/dashboard/personalizacao/custos/` (mesmo `UsageClient`) → duplicado e no lugar errado; título `text-3xl font-bold` próprio
(`:153`), fora do `DetailHeader` do resto do painel. Nenhuma conexão pessoal (Agger, WhatsApp, e-mail).

### 2.6 "Aggers da equipe" (`components/vault/AggersDaEquipe.tsx`, 216 linhas)
**Funciona:** senha nunca volta (`:21-22`); o servidor decide quem pode (`:117`); desconectar explica a consequência (`:196`).
**Ruim (Founder: "lista todos — rever"):** mora DENTRO do modal do Agger da CORRETORA (`AggerDaCorretoraModal.tsx:227`), dentro de
Conectores (`conectores/page.tsx:493`): para conectar o SEU Agger, o comercial precisa achar o modal da corretora. O admin vê e
cadastra o login de todos (`:117`, decisão D-131-0-06 "ambos 88").

### 2.7 O que está vencido no PDF de 23/09
⚠️ **NÃO MEDIDO:** o PDF "RASCUNHO AUXILIAR DE RENOVAÇÃO" não está no repositório (`Get-ChildItem -Recurse docs -Filter *.pdf` → nada).
Pelo git (F2), o que foi FEITO depois de 23/09 e portanto está vencido em qualquer pedido do PDF: o manual por serviço e a chave
calcular/entregar/negociar (`08e7f77`); o Agger por pessoa + `qual_agger` com auditoria (`0452b18`); o Agger da corretora pela tela
(133-A.1); COND/RESI/EMPR no motor (129-C). **Feito, mas no lugar errado** (Serviços, Aggers da equipe). Galeria/página/modal: nada feito.

---

## 3. Já existe SPEC para o visual da loja?

**FATO: não existe.** Buscas: `Select-String "galeria de auxiliares|loja|App Store|001\.9|página do auxiliar|layout"` em
`docs/canon/specs-propostas` e `specs`; PENDENCIAS por "galeria|vitrine|Meu perfil|Aggers da equipe".

| peça | o que cobre | o que NÃO cobre |
|---|---|---|
| **SPEC-064** (executada) | a galeria única, a ontologia Auxiliar × Rotina, a rota `[slug]` | visual "loja", abas, banner |
| **SPEC-078** (executada) | rotinas dentro da página, "ligar é o último passo", modal D.1–D.5/E | o modal limpo, a hierarquia |
| **DS-001** §8.4/8.5/8.7/9.3/14 | o PADRÃO: galeria (busca·filtros·cards), detalhe com abas, ícones lineares | não foi aplicado às telas atuais |
| **EXTRA-001.9** "o painel diz de quem é" | só rotas de Personalização: `agentes/even → corretora/…`, `equipe`/`conhecimento`/`custos` para `corretora/` com redirects, guarda de `href`, limpar "Even". **Sem proposta escrita** (`PROMPT-DE-ABERTURA-EXTRA-001.9-PRONTO.md:5-9`); na fila em DEPOIS (`EXECUTION-MASTER-PLAN.md:106`) | loja, Meu perfil, conexões por pessoa |
| "**SPEC de painel**" | citada 4× (`DIAGNOSTICO…:286/825`, 001.2 `:1095`, 001.8 `:709`) | **nunca escrita** |
| SPEC-115 (ideia) | o PLACAR de medições no painel | não é a loja |
| **P-16** | duas telas de execução fora de `[slug]` | — |

---

## 4. Agora ou depois?

**INFERÊNCIA central:** a página e o card são **um componente genérico cada** (`[slug]/page.tsx` + `AuxiliarDetalheClient`;
`Card` em `AuxiliaresClient.tsx:71`). Trocar a CASCA muda todos os aplicativos de graça. O caro é o CONTEÚDO de cada um (banner,
dúvidas, "como instalar") e o modal da Cobrança (1.504 linhas, em piloto). E a ONTOLOGIA proíbe a saída fácil: **erro nº 3 — "dar
página própria ao auxiliar novo"** (`ONTOLOGIA-DO-TRABALHO.md:148-154`).

| opção | nota |
|---|---|
| **A · A 131 cria o PADRÃO genérico e o aplica à Renovação.** Casca nova para todos: card com ícone (linear, da coluna `icon`), página com cabeçalho (ícone + nome + frase + botão) e **abas**, o bloco "Como começar" passo a passo derivado das conexões, nomes humanos das conexões, Histórico pela fonte real (F7), "Aplicativos" no menu, e o ENCAIXE da aba "o trabalho feito" por slug (um mapa, como `TELA_DE_EXECUCAO`, `catalog.ts:95-99`). Conteúdo completo (banner, dúvidas, sugestões, a aba de trabalho, a configuração) **só para Renovação** (+ Cotação/QCM só com Visão geral e Configurar, §5). Os outros aplicativos ganham a casca com o conteúdo que já têm. **O modal da Cobrança não muda.** | **88** |
| B · Renovação com página própria, fora de `[slug]` | 20 (repete o erro nº 3) |
| C · A loja inteira agora: todos os aplicativos com conteúdo, banners, modal da Cobrança reescrito, Meu perfil completo, 001.9 | 50 (131 já é CRÍTICO, com cálculo de madrugada; mexer no modal da Cobrança em piloto mistura riscos) |
| D · Nada de visual; Renovação nasce na página atual | 35 (nasce no padrão que o Founder deu nota 50) |

**RECOMENDAÇÃO (88): opção A**, e registrar a **SPEC "A loja"** (proposta, não executada) com: conteúdo dos outros aplicativos,
banners/ilustrações, o modal da Cobrança no padrão novo, a aba de trabalho da Cobrança, P-16 e a EXTRA-001.9 junto (as duas mexem
nas mesmas rotas). Gate de risco da opção A: `npm run test:rotas-montam` + `next start` + 1 requisição (CLAUDE.md §9.1), porque mexe em `app/`.

**O modal limpo (padrão, para a Renovação):** 💭 três passos curtos em vez de um formulário — **O que fazer** (a chave
calcular/entregar/negociar como 3 cartões) · **Quando** (dias antes do vencimento, padrão 10; horário pronto) · **Com qual conta**
(Agger e WhatsApp: "do responsável pela apólice" (padrão) ou "da corretora"). O que já está decidido aparece como uma linha
"✓ Agger da corretora conectado" com "mudar", não como campo. Tooltips (ⓘ) no lugar dos parágrafos `text-[11px]`. Avançado
(exceções por ramo/valor, reajuste, conta global) recolhido. Configuração longa vai para a **aba Configurar**, não para modal (DS-001 §8.6). Nota 85.

---

## 5. Arquitetura de informação — onde mora cada conexão

**A regra (já escrita em `SPEC-131-0-…md:264-267`, nota da casa):** o QUE fazer mora no **aplicativo**; COM QUAL conta mora na
**pessoa** e na **corretora**; DE QUEM é o cliente mora no **sistema de gestão**.

| peça | mora em | quem mexe | o aplicativo mostra |
|---|---|---|---|
| sistema de gestão (InfoCap/Quiver) | Personalização → Conectores | admin | "✓ conectado" + link |
| Agger **da corretora** (QCM e reserva) | Personalização → Conectores (o modal atual, **sem** "Aggers da equipe") | admin | opção "usar o da corretora" |
| WhatsApp de atendimento | Personalização → Corretora → WhatsApp (existe) | admin | opção "enviar pelo da corretora" |
| e-mail da corretora | Personalização → Conectores (`scope=company`) | admin | — (futuro) |
| seguradoras preferidas por ramo (padrão dos 3) | **Personalização → Seguradoras** (existe `InsurersClient.tsx`), com LISTA de seguradoras, não texto livre | admin | "usar a lista da corretora (padrão) / lista própria deste aplicativo" (D-131-0-12, 86) |
| **o MEU Agger** | **Meu perfil → Minhas conexões** | a própria pessoa | opção "usar o do responsável" |
| **o MEU WhatsApp** (pareado, separado do atendimento) | Meu perfil → Minhas conexões (nasce com a B1/131) | a própria pessoa | opção "enviar pelo do responsável" |
| o MEU e-mail | Meu perfil → Minhas conexões (`tenant_connections.owner_user_id` já existe, F8) | a pessoa | — |
| **ausência / substituto** | Meu perfil → **Ausência**: período + "quem assume" (uma PESSOA da corretora, de uma lista) | a pessoa (admin pode) | aviso "Fulana está fora até 20/10; Beltrana assume" |
| quem é comercial + código de produtor | Personalização → Equipe (existe `QuemEQuemNoSistema.tsx`) | admin | — |
| uso e custos | Personalização → Custos (já existe) — **sai do Meu perfil** | admin | — |

**"Aggers da equipe" (nota por opção):** cada um conecta SÓ o seu no perfil; o admin vê em Personalização → Equipe uma coluna de
SITUAÇÃO ("Agger conectado ✓ / senha recusada / falta") e um botão "pedir para conectar", **sem** campo de login de outra pessoa —
**86** · manter o admin cadastrando o de todos (D-131-0-06 atual) — 55 · só a pessoa, sem o admin ver — 60. ⚠️ Muda a D-131-0-06:
o gerente registra a decisão nova.

**Substituto de férias:** escolher OUTRA PESSOA; o cálculo continua no **Agger do DONO** (de férias ele não está logado → sem disputa de
sessão única, D-131-0-05) e o aviso/envio vai para o substituto — **85** (bate com D-131-0-16, nota 80) · no Agger do substituto — 60 (mistura
carteiras no Agger dele) · novo login e senha — 15 (o que o Founder rejeitou). FATO: falta a coluna (F8) → migration expand-only na 131.

**O que fazer com a tela Serviços (campo → destino):**

| campo hoje (`ServicosClient.tsx`) | destino |
|---|---|
| "Configuração em 4 passos" (`:333-374`) | bloco **"Como começar"** na Visão geral de cada aplicativo, gerado das conexões que ele exige + do Meu perfil |
| "O que o AutoBrokers faz" — a chave (`:232-250`) | **Aplicativo → Configurar → O que fazer** (Renovação e Cotação; no QCM, texto fixo) |
| Exceções por ramo/valor (`:376-434`) | Aplicativo → Configurar → Avançado (recolhido) |
| Seguradoras preferidas (`:436-509`) | padrão em Personalização → Seguradoras; no aplicativo só "lista da corretora / própria" |
| Reajuste da básica, antecedência, "Agger do comercial falhar → global" (`:263-304`) | **Renovação → Configurar** ("Quando" e Avançado) |
| aviso "as regras são separadas" (`:203-205`) | some (cada aplicativo tem a sua) |

O backend NÃO muda: `/api/servicos-da-corretora` e `multicalculo_config.servicos` seguem iguais; a tela de cada aplicativo lê o
seu `servico`. 📊 0 linhas gravadas (F5) → nada a migrar. A rota `personalizacao/servicos` vira **redirect** para a Renovação
(`?aba=configurar`), e sai o cartão `lib/mock/tenant-modules.ts:81`. **Cotação e QCM** precisam de casa quando a aba sair (F3: não há
template): criar as duas linhas de catálogo sem rotina (D-131-0-08), só com Visão geral + Configurar — **80** · manter a aba Serviços
só para elas até a 132 — 55 (dois lugares para a mesma regra).

**Rotas propostas:**
```
/dashboard/auxiliares                         a loja (menu "Aplicativos")
/dashboard/auxiliares/renovacao               slug novo (F4: renovacao-maxima não instalada → troca grátis); nota 80
   ?aba=visao | renovacoes | configurar | duvidas | sugestoes        ← abas por QUERY, nota 85
   ?aba=renovacoes&item=<id>                  o detalhe de uma renovação (gaveta no desktop, tela cheia no celular)
/dashboard/auxiliares/cotacao · /quem-cobra-menos      visão + configurar
/dashboard/configuracoes                      "Meu perfil": Dados · Minhas conexões · Ausência · Segurança · Aparência
/dashboard/personalizacao/servicos            → redirect
```
Abas por **subrota** `[slug]/trabalho` — **65**: INFERÊNCIA (não medido) — existe a pasta estática `auxiliares/checklist-6h/` ao lado de
`[slug]`; `/auxiliares/checklist-6h/trabalho` cairia na estática e daria 404. Só depois de resolver a P-16. ⚠️ Não criar outro nome de
parâmetro na mesma posição de `[slug]` (CLAUDE.md §9.1).

---

## 6. A aba "o trabalho feito" (Renovações)

**O que já existe e se reaproveita (FATO):**
- `atendimentos/fila/AttendanceQueueClient.tsx`: alternância **Quadro × Lista** com a escolha salva (`:96`, `:233`), colunas com
  contagem, `snap` horizontal no celular (`:22-27`, `:310`), teto de 50 cards por coluna (`:101`), e a regra **"sem arrastar: o estágio é
  DERIVADO do que aconteceu"** (`:29-30`) — casa com o Founder: *o agente* move os cards;
- `components/atendimento/caso-visual.tsx`: o vocabulário de card/linha/chip/"quem cuida"/"há quanto tempo" (`CardDoCaso :193`,
  `LinhaDoCaso :259`, `QuemCuida :155`, `haQuantoTempo :75`) — uma peça, duas telas;
- `atendimentos/ficha/[conversaId]/FichaClient.tsx`: a ficha com "Próximo passo", uma coluna no celular e duas no desktop
  (`:23-28`, `:578`) — o modelo do detalhe;
- `components/patterns/` (`DetailHeader`, `StatusPill`, `GalleryCard`…); `components/ui/table.tsx` existe mas só o admin usa.
**RECOMENDAÇÃO:** extrair o quadro/lista da fila para um componente genérico ("QuadroOuLista" com colunas e card por parâmetro) e
usá-lo nas duas telas — **82** · copiar o arquivo da fila para a renovação — 40 (dois quadros que divergem).

**Os estados (colunas do quadro)** — 💭 nomes para o juiz validar contra o motor do I1/I3:
```
Vai calcular      entrou na janela (D-10), ainda não calculou
Calculada         pronta no Agger + apresentação pronta          (até as 7h)
Enviada           saiu para o cliente (link ou PDF)
Em negociação     o cliente respondeu / pediu ajuste
Fechada           o cliente aceitou
Emitida e registrada   efetivada na seguradora + InfoCap         (coluna aparece quando existir a etapa)
Perdida           não renovou — com MOTIVO obrigatório (preço, foi para outra, desistiu, sem cotação)
```
"Precisa de você" **não é coluna, é selo** no card (Agger recusou a senha, ramo que não cotamos, sem comercial, cálculo falhou) —
como o chip de atenção do atendimento (`caso-visual.tsx:48-58`). Nota da proposta: **84** · com "Calculando" e "Sem cotação" como colunas
próprias — 70 (colunas que vivem minutos ou viram cemitério). Referência: Won/Lost obrigatórios e campo exigido ao entrar no estágio (HubSpot, §7).

**A lista (notebook):** agrupada por **dia de vencimento** (como o Agger agrupa por cliente, print 4); colunas:
`Cliente (nome + documento mascarado) · Ramo (ícone) · Vence (data + "em 8 dias") · Seguradora atual → recomendada ·
Prêmio atual → novo (Δ %) · Responsável · Estado · Ações`. Ações em ícone com rótulo no hover: **Ver apresentação · Enviar pelo
WhatsApp (mensagem pronta) · PDF · Abrir no Agger** · ⋯ (marcar fechada/perdida, recalcular). Linha que **expande** e mostra os 3
cálculos lado a lado (print 5) — nota 80.
**Filtros:** período (hoje · 7 dias · 30 dias · mês), ramo, seguradora, responsável (padrão "minhas" para o comercial, "todas" para o
admin — V33 da 131-0), estado, busca por nome/CPF/placa. **Atalhos no topo:** 💭 "Hoje: 12 calculadas · 3 enviadas · 1 precisa de você",
cada número é um filtro.
**O detalhe:** cabeçalho (cliente, ramo, vence em, estado, **próximo passo** — igual à ficha), contato, os 3 cálculos (recomendado ·
franquia reduzida · o pedido de sempre) com Δ contra o ano anterior, comissão (só quem pode ver), linha do tempo (calculada 03:20,
enviada, respondida), botões.
**O celular:** a lista vira cartões (nome, vence em, prêmio novo, estado, 1 botão grande "Enviar"); filtros em chips com rolagem;
o detalhe em tela cheia com barra fixa embaixo **[Enviar pelo WhatsApp] [Ver apresentação]**; o quadro rola uma coluna por vez (`snap`, já existe).

---

## 7. O que o estado da arte faz, e o que modelamos (protocolo §7.3)

1. **https://developer.apple.com/app-store/product-page/** — define a página do app: ícone, nome e subtítulo (30 caracteres),
   telas, prévia, descrição (a 1ª frase decide), avaliações, "o que há de novo". **Modelamos:** o cabeçalho ícone + nome + frase de
   uma linha + 1 botão, e a faixa de telas. **Rejeitamos:** palavras-chave e compras internas (não há loja pública). **Juiz:** abre a URL e
   confere o cabeçalho da Renovação item a item.
2. **https://developer.apple.com/app-store/review/guidelines/** (introdução da §3, *"fake feedback"*) — pune avaliação inventada com
   expulsão. **Modelamos:** estrela só com avaliação real; prova por número medido. **Rejeitamos:** as 30 avaliações fictícias.
   **Juiz:** Ctrl-F "fake feedback" na página e confere que o card não mostra estrela sem dado.
3. **https://apps.shopify.com/shopify-forms** — página de app de loja B2B: cabeçalho (ícone, nota, nº de avaliações, Instalar) →
   telas → descrição → destaques → "funciona com" → recursos → avaliações → suporte. **Modelamos:** a ORDEM da Visão geral (o que é →
   o que você ganha → como começar → funciona com [conexões com ícone] → dúvidas). **Rejeitamos:** "apps parecidos" de concorrente e preço
   (SPEC-062). **Juiz:** abre e compara a ordem das seções.
4. **https://docs.github.com/en/issues/planning-and-tracking-with-projects/customizing-views-in-your-project/changing-the-layout-of-a-view**
   — a mesma coleção em Tabela, Quadro ou Linha do tempo. **Modelamos:** um conjunto de renovações, duas leituras, os mesmos filtros.
   **Rejeitamos:** linha do tempo (o vencimento já é a data). **Juiz:** troca Lista↔Quadro na tela e confere que filtros e contagens não mudam.
5. **https://linear.app/docs/board-layout** — alternância lista/quadro por atalho, colunas agrupadas por estado, esconder coluna.
   **Modelamos:** agrupar por estado, esconder "Emitida" enquanto não existir. **Rejeitamos:** arrastar (o estágio é derivado,
   `AttendanceQueueClient.tsx:29-30`). **Juiz:** tenta arrastar um card e confere que nada muda no banco.
6. **https://knowledge.hubspot.com/object-settings/set-up-and-customize-pipelines** — funil com "ganho" e "perdido" obrigatórios e
   campo exigido ao entrar num estágio. **Modelamos:** "Perdida" com motivo obrigatório. **Rejeitamos:** valor ponderado por
   probabilidade (💭 não temos o dado). **Juiz:** marca uma renovação como perdida sem motivo e confere a recusa.
7. **Interna (vence a externa, §7):** os prints de ChatGPT Plugins em `docs/intake/TELAS AUXILIARES/EXEMPLOS PARA TELA APRESENTAÇÃO
   DO AUXILIAR/` (página: ícone grande, nome, frase, "Instalar" à direita, faixa de 2–3 imagens, "Habilidades" em chips, "Informação" em
   tabela) e `GALERIA PLUGINS GPT COM LOGOO.webp` (galeria: instalados como fileira de ícones, "Populares" em 2 colunas ícone+nome+frase+"+").
   **Modelamos:** os dois. **Rejeitamos:** o Netflix/Astron com foto de pessoa em tela cheia (contra o DS-001 §6.6 "visual calmo";
   o "wow" vem do ícone e da imagem do RESULTADO — 💭 a apresentação de renovação em miniatura — não de fotos). **Juiz:** abre o
   PNG e a tela lado a lado.

---

## 8. O que ficou por medir
- O **PDF de 23/09** (não está no repositório) — a lista do que está vencido é por git, não pelo PDF.
- Se `?aba=` e `[slug]/trabalho` montam e respondem: precisa `npm run test:rotas-montam` + `next start` + requisição (não rodei; READ-ONLY).
- O número exato de strings VISÍVEIS com "Auxiliar" (estimado 40–60, 💭) e o efeito da troca no chat (75 linhas de prompt).
- Contraste real (WCAG) dos títulos `text-muted-foreground`/`text-faint` nos dois temas — afirmado por classe, não por medidor.
- Se o Agger aceita **link direto para um cálculo** ("abrir no Agger na página certa") — é do I1/I3.
- O mapa estado-do-quadro → dado (`multicalculo_pedidos.status` hoje só tem 📊 `fechado` 5 e `cancelado` 1, `servico` nulo) — o motor
  da renovação ainda não existe; os estados acima são PROPOSTA.
- Uso real do modal da Cobrança (quantas corretoras editam) — não medi; por isso a opção A não toca nele.
