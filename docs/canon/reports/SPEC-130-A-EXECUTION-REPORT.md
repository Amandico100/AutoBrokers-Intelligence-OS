# SPEC-130-A — A comparação, a proposta e a página "uau" · relatório de execução

> 06/10/2026 · branch `spec/130-A-a-proposta` · base `5952324` · rito AAA v13, 🔴 CRÍTICO por piso · SPEC
> `specs/SPEC-130-A-a-comparacao-e-a-proposta.md` (v1.1) · laudos no rascunho do gerente (`laudos/juiz.md`, `laudos/redteam.md`,
> `laudos/confirmacao.md`, `design/criticas/*.md`)

## EXECUTION CARD
```
OUTCOME ..............  um pedido do motor vira PROPOSTA: ofertas comparadas igual-com-igual (produto diferente e assinatura à
                        parte), a corretora vencedora, 3 opções por situação com nota 0–100 e motivos, validade, a mensagem de
                        WhatsApp (≤ 2 opções + link) e a página "carteira" no /r/, na marca da anfitriã. 📊 canário REAL:
                        pedido d0bb15ba publicado em produção → /r/83MdBCdO… 200, 16 cotadas = 13 completas + 1 diferente + 2 sem
                        resposta, Youse R$ 3.730,56 recomendada, 0 comissão, 0 nome da perdedora
RISCO ................  7 — ALCANCE 3 · REVERSIBILIDADE 2 (link público + 3 migrations) · FREQUÊNCIA 2
SUPERFÍCIE ...........  2 — peças novas sobre Artifact Hub, marca e porta, que já existiam
PISO APLICADO ........  §3.2 — migration de estrutura e de dado · link público com dado do cliente · lê a marca da anfitriã
                        (outra company) para a página do solicitante
NÍVEL ................  🔴 CRÍTICO · gerente Opus 5.5 · builders Opus 5.5 · juiz ‖ red team · confirmação
O FIO ................  porta.consultar → comparacao.comparar/opcoes → proposta.montar_proposta → Artifact Hub (proposal.quote:
                        criar→render→publicar→compartilhar) → /r/<token> (CSP com o hash do NOSSO script) → página; e →
                        mensagem.mensagem_whatsapp · teste `test_spec130a_o_fio.py` (nasceu VERMELHO: ModuleNotFoundError)
PARALELISMO REAL .....  D0 (3 designers ‖) · F1 ‖ D0 · F4 · F2a ‖ D0 · F2b ‖ F3 (arquivos disjuntos)
UNIDADES .............  U1 comparação · U2 config + manual + migration · U3 negociação na porta · U4 proposta · U5 página + /r/ ·
                        U6 mensagem · U7 publicar + comando + canário · (F4) completa+
TIME .................  gerente · investigador · 3 designers · 8 críticos (4 rodadas) · revisor cego da SPEC · F1 F4 F2a F2b F3 ·
                        crítico final · juiz ‖ red team · conserto único · confirmação · atualizador
REFERÊNCIA ...........  interna: Artifact Hub, brand, porta, /r/ · externa: SPEC §8 (8 URLs)
GATES ................  G1–G17 (SPEC §9 + §10)
O ELO ................  "a página só mostra o comparável PORQUE o comparador separa antes" → medido no HTML SERVIDO (fio + 21
                        guardas do conserto), não na função
FAIXA DE RELÓGIO .....  💭 8–12 h · 📊 ~7 h (04:16–11:30) incluindo a medição do Agger e ~1 h 30 esperando a pergunta ao Founder
```

## 1. A medição do Agger (antes da SPEC, ZERO cálculos)
Resultado em `programa-multicalculo/A-PROVA-DO-AGGER.md` §10: 📊 Resulta 1.021 negócios — Condomínio (16) 672 · Empresarial (18) 182 ·
Residencial (2) 115 · Vida (91) 32 · Auto (31) 14; AutoFleet 103 de auto. Formulários mapeados (sem dado pessoal):
`backend/tests/fixtures/agger_formularios/formularios_por_ramo.json` — Condomínio 83 campos/43 obrigatórios, Empresarial 59/16,
Residencial 86/33, Vida 47/12, Auto 139/63. 🔴 Incidente: a 1ª entrada recarregava a página a cada tela; a guarda cortou a 6ª troca de
token, o logout não saiu; às 04:38 e 07:36 o aviso de sessão ativa → Cancelar e parar (regra). Lição gravada: navegar sem recarregar.

## 2. O que mudou
- **Comparação** (`multicalculo/comparacao.py`): só compreensiva, casco 100 %, prêmio anual entra no ranking; roubo-só, terceiros, casco
  < 100 % e assinatura viram "produto diferente" com o motivo; ranking POR OPÇÃO (a opção vem do cálculo); recusas em frase humana;
  a vencedora entre corretoras; as opções por situação (D-MC-66/69, D-130A-09) com nota e motivos; QUALQUER ramo.
- **Config** (`multicalculo/config.py` + `multicalculo_config`): o ÚNICO lugar dos números de D-MC-62…72; `manual_de_negociacao.py`
  (alavancas, limites, objeções reais, FAQ, sinistro) como dado para a 133-A.
- **Negociação** na porta: `ordem_do_mais_barato`, `cotacao_alvo` + `avaliar_cotacao_alvo` (assíncronas; só a corretora dona; 12 %
  sozinho, 10 % com concorrência E aprovação).
- **Completa+** (`presets.py`, `motor.py`, `porta.py`): a padrão + pequenos reparos, no mesmo negócio, depois da econômica.
- **A página** (`artifacts/proposta_{html,apresentacao,estilo,previa}.py`): o desenho "carteira" aprovado (D-130A-11), funciona sem
  JavaScript, script só por hash (`route.ts`), prévia PNG 1200×630 sem dado pessoal, abertura sem contar robô de prévia, clique
  "Quero fechar" registrado (`?fechar=`), impressão = PDF (D-130A-07).
- **A proposta** (`multicalculo/proposta.py`, `mensagem.py`, `comando_proposta.py`): artefato no SOLICITANTE, marca da anfitriã no
  modelo, logo embutido, recusa sem WhatsApp (salvo `--sem-whatsapp`) e sem apólice quando a situação pede.
- `brand/capture.py`: `snapshot_para_artefato` não quebra sem linha de marca (o canal).

## 3. O desenho (D0) — "não aceite a primeira opção"
3 direções (conversa · precisão · carteira), painel cego de 2 críticos frescos por rodada (conversão ‖ acabamento), 4 rodadas:
📊 rodada 1 carteira 85/83 × precisão 81/77 × conversa 68/74 → 89/88 → 90/92 → 91/90. O Founder escolheu a carteira (pergunta
ÚNICA, 06/10). Página de PRODUÇÃO medida por crítico final fresco: 📊 91; os consertos dele entraram no conserto único.

## 4. Julgamento
| peça | nota | o que achou |
|---|---|---|
| revisor cego da SPEC | 68 | 7 blockers de desenho (onde mora o artefato, Hub sem gancho, porta síncrona inexistente, mistura de opções no ranking, assinatura, escopo, 3ª opção) → v1.1 |
| juiz | **80 PASS c/ 3 blockers** | página promete WhatsApp sem WhatsApp · "Igual à sua atual" sem apólice · resumo 16 ≠ 13 + 2 |
| red team | **74 QUEBREI** | com apólice + completa+, a mais cara virava "a melhor das 11" (título, og:title, selo) — EXCLUSIVO |
| conserto único | — | 4 blockers + 13 pendências; 21 guardas sobre o HTML SERVIDO, 21 mutações vermelhas; 219 passed |
| confirmação | **88 PASS** | os 4 fechados com prova; 433 testes do dublê endurecido verdes; 2 defeitos novos menores no caminho com apólice (P-130A-21/22) |

🔴 **A lição:** 186 testes verdes conviviam com 4 frases mentirosas — os testes afirmavam sobre o MODELO, nunca sobre a FRASE servida.

## 5. Testes (saída real)
- Suítes da 130-A + regressão dirigida (conserto): 📊 219 passed · confirmação: 145 passed (6 suítes) + 288 passed (21 arquivos do dublê).
- `node scripts/a-pagina-da-proposta.test.mjs` 27 ok · `npm run test:rotas-montam` "A TABELA DE ROTAS MONTA" (308 rotas) ·
  `next build` + `next start` + `/api/auth/me` 200 + `/r/<inválido>` 404 (F2a).
- Mutações (uma vez, restauradas por cópia): F1 9 · F4 2 · F2a 7 · F2b 7 · F3 9 · conserto 21 — todas vermelhas.

## 6. Bateria
📊 worktree limpo `C:/wt130a` em `2250127` (o `backend/.env` copiado, sem link), `pytest tests -q -p no:cacheprovider` em DUAS METADES
(301 + 301 arquivos, cada uma com `--ignore` da outra, rodadas ao mesmo tempo): **metade 1 → 15 failed · 1.398 passed · 2 skipped
(48:48)** · **metade 2 → 21 failed · 4.128 passed · 7 skipped · 32 xfailed (50:14)**. TRIAGEM NOMINAL contra `BATERIA-LINHA-DE-BASE.txt`:
32 das 36 na base; as 4 NOVAS isoladas: `test_o_handoff_que_falha_deixa_rastro` → 📊 1 passed (5:08) · `test_spec129a_o_or_no_postgrest_real`
(3) → 📊 5 passed (23 s) = CARGA (as 2 metades em paralelo + PostgREST real pela rede). → **0 regressões.** Rodadas: 1 (em 2 metades).

## 7. Migrations (APLICADAS em produção, psycopg numa transação, `lock_timeout 5s`, registradas em `schema_migrations`)
- `20261006_01_spec130a_config` — versão `20261006084655` · VERIFY 📊 `1·1·1·0·0·1·4` + DO `OK` (o texto do DO ganhou `::text`).
- `20261006_02_spec130a_completa_mais` — `20261006090505` · VERIFY 📊 `0·0·2·1` → `1·1·2·1` + DO `OK` (9 casos).
- `20261006_03_spec130a_seed_template_proposta` — `20261006121020` · 1 linha `proposal.quote`, 0 artefatos, sem erro de FK.
ROLLBACK de cada uma no arquivo (recusam se houver dado).

## 8. O que ficou fora (P-130A-01…22 em `PENDENCIAS.md`, com dono)
🧑 01 WhatsApp de atendimento no cadastro de marca das 2 corretoras (sem ele, publicar RECUSA) · 02 nº SUSEP · 03 marca da AutoFleet ·
04 a ficha do Google confirmada (nunca por nome) · 09 trava de piso < 10 % · 16 jurídico da remuneração. 🤖 05 validade real por
seguradora (PDFs) · 06 versão nova não revoga o link antigo · 07 índice único por pedido · 08 desconto sobre a comissão de entrada ·
10 "igual à atual" só pela seguradora · 11 CSP/prévia no navegador do WhatsApp · 12 pesos da nota · 13 catálogo de coberturas ·
14 "Mpfi" · 15 recálculo por seguradora ao vivo · 17 ramos 69/93/46/100 (129-C) · 18 sessão fantasma do Agger · 19 seed
`financial.billing_collection` (anterior) · 20 republicar o canário após o Implantar · 21 a renovação não cita o preço de renovar na
mensagem (N1) · 22 com apólice a "Mais completa" sai do carrossel de 3 (N2). Drenadas: P-129B-06 FECHADA · P-129B-02 FECHADA.
Decisões que reduziram escopo: D-130A-06 (consentimento → 133-A) e D-130A-07 (PDF do servidor depois), do Founder, no CHANGE-ADDENDA.

## 9. Canário Amandus → Resulta → AutoFleet
Sem Implantar nesta SPEC. Canário REAL: o comando publicou a proposta do pedido `d0bb15ba` (canal; vencedora AutoFleet) no banco de
produção; o `/r/` da produção (código antigo, sem script) a serve: 📊 200, 152.929 bytes, 390 px sem rolagem, 0 "comissão", 0 nome da
perdedora. Sem o WhatsApp da AutoFleet o botão "Quero fechar" não aparece (P-130A-01). Após o conserto o comando RECUSA publicar sem
WhatsApp (só com `--sem-whatsapp`).

## 10. Declaração
Nenhum motor paralelo: a página é artefato do Artifact Hub (D-130A-01), a negociação usa a `recalcular` da porta, a completa+ usa o
mesmo motor. Nenhuma mensagem saiu. Verba do produto: 📊 2 buscas Google Places (💭 ≈ US$ 0,07) · 0 chamada de modelo → saldo 💭 US$ 3,93.

## 11. Telemetria — `python backend/scripts/medir_execucao_claude_code.py --sessao atual`
```
executor 464 min de parede (≈ 7 h ativas; ~1 h 30 esperando a resposta do Founder) · 183 turnos · pico 564k · US$ 42,89
investigador 10/4,13 · designers 20/4,66 · 18/3,75 · 107/19,45 (3 voltas) · revisor cego 7/2,62 · F1 45/9,69 · F4 18/5,17 ·
F2a 67/12,83 · F2b 43/11,02 · F3 66/14,38 · críticos (8 + final) 2,01–5,08 cada · juiz 17/7,22 · red team 12/5,01 · conserto 40/16,21 ·
confirmação 13/1,64 · atualizador 8/3,11
TOTAL 24 agentes + executor · US$ 235,32 API-equivalente (tokens do Claude Code; não é a verba do produto)
achados por mecanismo: revisor cego 7 blockers de desenho · críticos 4 rodadas (~60 consertos de desenho) · builders (o capture.py:
EXCLUSIVO da F3) · juiz 3 blockers + 8 · red team 1 blocker (EXCLUSIVO) + 10 · crítico final 7 + 2 de dado · confirmação 2 novos ·
CANÁRIO real: a falta do WhatsApp nas 2 corretoras (EXCLUSIVO)
rodadas da bateria: 1 (2 metades) · 0 regressões
nota do executor: 89/100 (critério: canário real na produção, 4 blockers fechados com guarda no HTML servido, desenho 91 medido na
  página de produção; menos: a meta de 95 do desenho não foi alcançada e a sessão fantasma no Agger) · juiz 80 · red team 74 · confirmação 88
```

## 12. Entrega
ENTREGA_AQUI
