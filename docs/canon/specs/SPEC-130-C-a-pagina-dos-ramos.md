modelo: claude-opus-5-5

# SPEC-130-C — A página do cliente para todos os ramos, a corretora que se apresenta e as fotos da marca

> **v1.0 · 16/10/2026** · redator Opus 5.5 (gerente) · branch `spec/130-C-a-pagina-dos-ramos` (da `origin/main` `40f66de`) · AAA v13 ·
> **CRÍTICO** (a página vai ao SEGURADO; migration muda índice e estrutura). Fontes: D-129C-08 · D-129D-10/16 · P-129C-05 · ESTADO-DO-PROGRAMA
> §1 · as palavras do Founder de 16/10 (abertura desta SPEC). 📊 medido · 💭 ilustrativo.

## 0. EXECUTION CARD
```
OUTCOME ........ (1) a RENOVAÇÃO passa a ter o mesmo esqueleto da página de COTAÇÃO (o hero com a oferta, as opções em carrossel com
                 abas e "1 de N", sem o efeito 3D que trava), com a voz de quem JÁ é cliente; (2) Condomínio (16), Residencial (2),
                 Empresarial (18) e Vida (91) ganham a página — na cotação nova E na renovação — no MESMO gerador (nunca página ao
                 lado); (3) toda página (cotação, renovação, Quem Cobra Menos) ganha o BLOCO DA CORRETORA: título por momento → cartão
                 da corretora → 2 selos (Nível 5 + Premiada) → "<Nome>, corretora premiada Nível 5" → os itens do Nível 5 → carrossel
                 com as FOTOS da corretora; (4) a corretora sobe as fotos (e os prêmios) na Identidade; cada foto só aparece nas
                 páginas DELA; (5) o Quem Cobra Menos usa o mesmo carrossel das opções. Custo de modelo da página: ZERO (medido).
RISCO .......... 8 · segurado 3 · página publicada sai do prédio 3 · toda cotação/renovação 2
SUPERFÍCIE ..... 2 · peça nova (bloco + fotos) e vários comportamentos (3 páginas × 5 ramos)
PISO ........... CRÍTICO: vai ao segurado · migration muda índice único e colunas · foto de uma corretora na página de outra = vazamento
NÍVEL .......... CRÍTICO · builders Opus 5.5 xhigh · juiz ‖ red team Opus 5.5 · juiz de DESIGN com capturas (≥ 90) · confirmação se blocker
O FIO .......... §2 · o teste do fio é a 1ª entrega da costura (F4)
PARALELISMO .... F1 (a marca) ‖ F2 (as páginas) ‖ F3 (os dados e os ramos) — arquivos disjuntos §5 → F4 costura + capturas
UNIDADES ....... U1 renovação = esqueleto da venda · U2 bloco da corretora · U3 fotos + prêmios na marca · U4 os ramos (RE e vida) nas
                 duas páginas · U5 o carrossel do QCM · U6 o custo medido
COESÃO ......... os 4 arquivos de página + o bloco num dono só (o mesmo CSS e o mesmo script); a marca (migration + API + tela) noutro;
                 o modelo (proposta.py, manual, config, workflow) noutro
TIME ........... gerente · F1 ‖ F2 ‖ F3 · F4 costura · juiz ‖ red team ‖ design · conserto único · confirmação
REFERÊNCIA ..... interna: a página de venda da 132-B (o design 91 do juiz) e o cartão da corretora do QCM · externa §8
GATES .......... fio · 2 corretoras (foto de A nunca em B) · ramos sem palavra de carro · migration APPLY/VERIFY/ROLLBACK · §9.1
                 (a tela da Identidade: rotas-montam + next start + 1 requisição) · design ≥ 90 com capturas · bateria
O ELO .......... "a foto que aparece é da corretora certa PORQUE vem do company_id da página" → teste com 2 corretoras reais lendo
                 bytes distintos + o red team tentando cruzar
FAIXA .......... 💭 8–12 h
```

## 1. O contrato
**Muda:** `render_renovacao` passa a montar sobre o esqueleto da venda (`proposta_cotacao_html`), com a voz da renovação · o bloco da
corretora em `artifacts/proposta_corretora.py` (novo), usado pelas três páginas · as páginas sabem o RAMO (título, o bem, os textos do
sinistro e das dúvidas, os nomes das coberturas de vida) · a vida publica página na cotação nova (revê a D-129D-16) · `brand_assets`
aceita várias fotos (`kind='photo'`) com ordem e legenda; `brand_profiles.awards` guarda os prêmios · a Identidade ganha "Fotos da
corretora" e "Prêmios" · `montar_anfitria` leva fotos, prêmios e o selo às três páginas · o QCM usa o carrossel com abas da venda.
**Não pode mudar:** a carteira antiga (`render_proposta` sem `situacao` de venda/renovação) byte a byte · o motor, o robô, o leitor e a
comparação · o `destino_do_fechar` (o "Quero fechar/renovar" vai sempre ao número do MODELO) · nada é ENVIADO por esta SPEC (a página é
publicada pelos caminhos que já existem) · CSP do `/r/` (`img-src 'self' data:` já aceita as fotos embutidas) · nenhum nome de
corretora em código (§13.9).

## 2. O FIO
```
Identidade (tela) → PUT /api/dashboard/brand-identity/photos (company_id da SESSÃO) → backend POST /brand/photos → fotos.py valida os
BYTES, reduz e grava `brand_assets(kind='photo', company_id, sort_order, caption)` → [cotação/renovação/canal] montar_anfitria(db,
company_id) lê fotos+prêmios+selo SÓ daquele company_id → modelo.anfitria.{fotos, premios, selo} → render (venda | renovação | canal)
→ proposta_corretora.bloco_da_corretora(modelo, momento) → HTML guardado → /r/<token> (data: embutido) → o cliente vê
ramo: pedido (16/2/18/91) → comparação → publicar_cotacao/publicar_renovacao (+ workflow da vida) → modelo.ramo/bem/faq/sinistro do
ramo → a MESMA página
```

## 2.1 BLOCO 0 (📊 16/10/2026 — gerente + investigador read-only)
| # | premissa | medição (comando) | muda o desenho |
|---|---|---|---|
| M1 | a renovação "trava" | renovação usa o `.track` da carteira: o script escreve `--d/--ad` em cada cartão por quadro de rolagem e o CSS faz `transform` + `mask` 3D (`proposta_html.py` `SCRIPT_DA_PROPOSTA` measure; `CSS_DA_RENOVACAO` não neutraliza); a venda neutraliza (`.venda .pass{transform:none;mask:none}`) | U1: a renovação no esqueleto da venda |
| M2 | QCM empilhado no celular | o código atual JÁ é carrossel (`.ops` scroll-snap desde a 133-A.1, 10/10; captura 390 px do gerente); o HTML é GUARDADO no publicar — link publicado antes de 10/10 continua empilhado | U5 unifica com abas; o Founder testa com link NOVO |
| M3 | onde moram as fotos | `brand_assets.kind` já aceita `'photo'`; índice único `brand_assets_one_current_per_kind (company_id, kind) WHERE is_current` permite UMA (migration 20260725_05 :79). 📊 `select count(*) from brand_assets where kind='photo'` → 0 | migration troca o índice; 0 linha afetada |
| M4 | o logo vai embutido | `proposta.py:422-439` `_data_url`, teto 256 KB, só raster; `/r/` `img-src 'self' data:` (`app/r/[token]/route.ts:174`) | fotos embutidas, sem rota pública nova |
| M5 | RE/vida bloqueados? | só a vida na cotação pelo chat (`cotacao/workflow.py:373`, responde no chat); RE e renovação passam sem portão, com textos de carro (`_bem` lê `modeloSelecionado`; `faq_da_renovacao` e `manual_de_negociacao.sinistro_padrao` falam de carro/FIPE/bônus) | U4 |
| M6 | selo e prêmio | `anfitria.selo` só no canal (`proposta.py:976-979`, `config.py:143` padrão ligado); "premiad" → 0 ocorrências no backend de marca; `canal.selo_criterios` nunca é escrito | U2/U3: selo nas 3 páginas; prêmio novo |
| M7 | custo de montar a página | nenhuma chamada a modelo em `montar_proposta`/`publicar_*`/render/prévia (PNG por PyMuPDF). 📊 `token_usage_logs` 30 d: `chat` gpt-6.1-sol 19 chamadas, média US$ 0,0208/turno; `canal_cotacao` 0 linhas em produção; leitura de apólice (130-B) média 📊 US$ 0,00124 | U6: o número vai ao Founder |
| M8 | "perto de você" | 0 ocorrências em `services/canal`, `services/multicalculo`, `programa-multicalculo/` | fora, P-130C |
| M9 | a marca das 2 corretoras | 📊 Resulta: publicada, sem ano, 0 diferenciais, 0 parceiras; AutoFleet: publicada, com ano; 0 fotos nas duas | o bloco tem de ficar bonito MAGRO |

## 3. O desenho das páginas (U1, U2, U4, U5)
**Venda (cliente novo) e renovação (já é cliente) no MESMO esqueleto**, nesta ordem: topo (marca + SUSEP) · hero (o título do momento,
a frase, o cartão da oferta com a parcela em destaque; na renovação, "vence em" e a faixa "o que continua: o mesmo atendimento, sem
dia descoberto, renovar leva um minuto" — só o que é verdade) · [renovação] "o seu seguro hoje × a renovação" · as opções (carrossel
com abas e "1 de N" no celular; lado a lado ≥ 1024 px; SEM o efeito 3D) + comparar · [venda] economia (só com a apólice) · **o bloco da
corretora** · quem cuida de você · depois do sim / se acontecer · dúvidas · fecho · [renovação] todas as seguradoras recolhidas · legal.

**O bloco da corretora** (um componente, três vozes — o Founder, 16/10):
1. título: venda "Por que fechar com a <Nome>" · renovação **"Mais um ano em boas mãos"** · canal "Quem é a corretora que cobra menos?"
2. o cartão (o do QCM: logo/monograma, nome, cidade, fatos — anos de mercado, Google, SUSEP, parceiras, site, "renova com a gente há N
   anos" só com prova) com o texto de cada momento (venda: quem representa você; renovação: quem já conhece o seu seguro e revisou as
   seguradoras; canal: quem atende é a corretora, o canal só compara);
3. os 2 selos lado a lado: **Nível 5** (o selo do programa, `anfitria.selo`) e **Corretora premiada** (só com ≥ 1 prêmio cadastrado);
4. "<Nome>, corretora premiada Nível 5" (sem prêmio: "<Nome>, corretora Nível 5"; sem selo: o passo 3–5 some);
5. os itens do Nível 5 em bullets (a lista do programa; a da config vence);
6. o carrossel das fotos (até 4; legenda; sem foto, SOME). Prêmio cadastrado aparece como legenda/linha ("Prêmio X · 2025").
Bloco sem dado some (D-132B-02): nada inventado — nenhum ano, nota, prêmio ou foto.

**Os ramos:** título e frases pelo ramo ("a cotação do seu seguro residencial / do condomínio / da sua empresa / de vida"); o bem do
RE e da vida sem dado pessoal; ícones e nomes das coberturas de RE (os da comparação) e de VIDA (dicionário — nunca `isAppMorte`
na tela); franquia só se existir; "guincho", "carro", "FIPE", "bônus", "bater" NUNCA fora do auto; sinistro e dúvidas por ramo.

## 4. As fotos e os prêmios (U3)
- `brand_assets(kind='photo')`: até **8** por corretora, ordem (`sort_order`) e legenda (`caption` ≤ 80); a página mostra as **4**
  primeiras. Os BYTES decidem o tipo (JPEG/PNG/WEBP/HEIC), entrada ≤ 10 MB, reduzidas no servidor a ≤ 1080 px e ≤ 💭 90 KB (WEBP), sem
  EXIF (sem GPS); guardadas como `data:` em `storage_ref` (o mesmo desenho do logo, `capture.py:167`).
- `brand_profiles.awards jsonb` = `[{nome, ano?}]` (≤ 10, nome ≤ 80). "Premiada" = ≥ 1 prêmio.
- Escrita SÓ pelo `company_id` da sessão; leitura SÓ pelo `company_id` da página; nenhuma URL pública nova.
- Sem foto cadastrada, a página real NÃO mostra carrossel; o EXEMPLO (`publicar_exemplo_da_pagina`) mostra 4 ilustrações geradas em
  código, marcadas "Exemplo" (nunca gravadas na marca de uma corretora real).

## 5. Fatias (cada arquivo, UM dono)
| fatia | entrega | arquivos (só estes) |
|---|---|---|
| **F1 · a marca** | migration · `fotos.py` · API · tela Identidade (fotos + prêmios) · testes | `backend/supabase/migrations/20261016_03_spec130c_fotos_e_premios.sql` (o `_02` já é da SPEC-139) (+ MANIFEST da pasta, se existir o padrão) · `backend/app/services/brand/fotos.py` (novo) · `backend/app/api/brand.py` · `app/api/dashboard/brand-identity/photos/route.ts` (novo) · `app/api/dashboard/brand-identity/route.ts` (só `awards` no PATCH) · `app/dashboard/personalizacao/corretora/identidade/BrandIdentityClient.tsx` · `backend/tests/test_spec130c_fotos_da_marca.py` |
| **F2 · as páginas** | renovação no esqueleto da venda · bloco da corretora · ramos na tela · QCM com o carrossel único · o script (pontos do carrossel de fotos; sem o efeito 3D fora da carteira) | `backend/app/services/artifacts/{proposta_corretora.py (novo), proposta_cotacao_html.py, proposta_html.py, proposta_canal_html.py, proposta_apresentacao.py, proposta_estilo.py}` · `backend/tests/test_spec130c_as_paginas.py` + a MIGRAÇÃO dos testes de página que afirmam o layout antigo (§9.3: a lição migra) |
| **F3 · o modelo** | `montar_anfitria` com fotos/prêmios/selo nas 3 páginas · `bem`, FAQ e sinistro por ramo · nomes de vida · vida publica página · exemplo com ramo e fotos ilustrativas | `backend/app/services/multicalculo/{proposta.py, manual_de_negociacao.py, config.py}` · `backend/app/services/cotacao/workflow.py` · `backend/scripts/publicar_exemplo_da_pagina.py` · `backend/tests/test_spec130c_o_modelo.py` · `backend/tests/test_spec129d_cotacao_nova.py` (só a afirmação "vida sem página", §9.3) |
| **F4 · costura** | o FIO, 2 corretoras, capturas 390/1280 claro/escuro dos 5 ramos × 3 momentos | `backend/tests/test_spec130c_o_fio.py` · roteiro de captura no rascunho |

**O contrato F1 ↔ F3:** `fotos.fotos_da_pagina(db, company_id, teto=4) -> list[{"src": "data:image/webp;base64,…", "legenda": str}]` e
`fotos.premios(db, company_id) -> list[{"nome": str, "ano": int|None}]` — ambos filtram `company_id` no SELECT. **F3 ↔ F2:** o modelo
ganha `ramo:int`, `bem:{rotulo, descricao, ano, apelido}` (sem PII), `anfitria.fotos`, `anfitria.premios`, `anfitria.selo` (todas as
origens, pela config `canal.selo`), `anfitria.selo_criterios?`; F2 nunca lê o banco.

## 6. A régua
**Mutações (o guarda tem de ficar VERMELHO):** (1) `montar_anfitria` sem o filtro `company_id` nas fotos → a página de B mostra a foto
de A · (2) "Corretora premiada" com 0 prêmios · (3) "carro"/"guincho"/"FIPE" numa página de RE ou vida · (4) `isAppMorte` na tela ·
(5) a renovação com `transform` 3D no cartão · (6) foto com EXIF GPS gravada · (7) PNG renomeado de .exe/SVG com script aceito.
**Isolamento:** Resulta × AutoFleet com fotos DIFERENTES (bytes conhecidos) — cada página só com as suas. **Design:** juiz com capturas
(390 e 1280 px, claro e escuro) ≥ 90. **Verba de API do produto:** US$ 0,00 (nenhuma chamada a modelo; o canário é render).

## 7. Decisões desta SPEC (pela maior nota; o Founder confirma se quiser)
| # | decisão | nota | contra |
|---|---|---|---|
| D-130C-01 | Renovação no esqueleto da venda (uma página, duas vozes) | 92 | manter a carteira com remendo 45 |
| D-130C-02 | Um bloco da corretora, três vozes (venda/renovação/canal) | 92 | três blocos copiados 40 |
| D-130C-03 | Fotos em `brand_assets` (kind photo), embutidas na página (`data:`), 4 na página, 8 guardadas | 85 | rota pública por token 70 · bucket novo 55 |
| D-130C-04 | "Corretora premiada" só com prêmio cadastrado (CDC art. 37); o Founder cadastra os prêmios na Identidade | 90 | selo em toda corretora 25 |
| D-130C-05 | Selo Nível 5 nas 3 páginas pela config que já existe (`canal.selo`, ligado por padrão; a corretora pode desligar) | 85 | só no canal 50 |
| D-130C-06 | Sem foto → o carrossel some; o EXEMPLO usa ilustrações geradas e marcadas | 88 | fotos falsas na marca real 10 |
| D-130C-07 | Título da renovação "Mais um ano em boas mãos" | 86 | "Por que continuar com a X" 60 (soa como dúvida) |
| D-130C-08 | A vida publica página na cotação nova (revê D-129D-16) | 85 | só no chat 50 |
| D-130C-09 | O QCM usa o carrossel com abas da venda | 84 | manter o seu 60 |
| D-130C-10 | "Perto de você" não existe — fica fora (P-130C) | 90 | construir agora 30 (§11: escopo) |

## 8. O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS
1. **https://www.w3.org/WAI/ARIA/apg/patterns/carousel/** · faz: o carrossel acessível (rótulo, "slide N de M", controles, sem rodar
   sozinho) · modelamos: abas + "1 de N" + setas, rolar só por quem toca · rejeitamos: autoplay · juiz: teclado e leitor de tela.
2. **https://www.nngroup.com/articles/designing-effective-carousels/** · faz: carrossel com indicador e o próximo cartão à vista ·
   modelamos: a borda do próximo cartão aparece · rejeitamos: carrossel de foto sem legenda · juiz: captura 390 px.
3. **https://developer.mozilla.org/en-US/docs/Web/CSS/scroll-snap-type** · faz: o encaixe nativo · modelamos: carrossel funciona SEM
   script · rejeitamos: rolagem por JS quadro a quadro (o que travava) · juiz: página sem JS.
4. **https://www.planalto.gov.br/ccivil_03/leis/l8078compilada.htm** (CDC, art. 37) · faz: proíbe publicidade enganosa · modelamos:
   selo/prêmio/foto só com dado da corretora · rejeitamos: "premiada" por padrão · juiz: mutação 2.
5. **https://web.dev/articles/choose-the-right-image-format** · faz: WEBP e o peso da imagem · modelamos: ≤ 💭 90 KB por foto, sem EXIF
   · rejeitamos: foto original de 4 MB embutida · juiz: o tamanho do HTML servido.

## 9. O QUE SAI (com destino)
"Perto de você" (corretora pela região do cliente) → SPEC própria quando houver corretoras fora de Florianópolis (P-130C) · o QCM de RE
e vida (o canal só calcula auto, `porta.py:523`) → 133-B · cadastrar fotos e prêmios reais → o Founder (tarefa) · links publicados
antes desta SPEC seguem com o HTML antigo (o render é guardado) → republicar quando quiser.
