# CONFIRMAÇÃO · SPEC-131-B · O aplicativo de Renovação (protocolo §6.1)

> Juiz novo (claude-opus-5-5), read-only. Diff do conserto: `git diff 66feb3e..b452d07` (41 arquivos, +1536/−261).
> Missão: "o conserto fechou os blockers e criou defeito?". 13/10/2026.

## VEREDITO: PASS. Os 4 blockers estão FECHADOS, cada um com guarda que fica VERMELHO quando o conserto é revertido. Nenhum defeito novo passa no teste do produto (§2).

## BLOCKERS

| blocker | estado | prova |
|---|---|---|
| **J-B1** CPF/nome na URL e no log | **FECHADO** | Tela: `AbaRenovacoes.tsx:153` manda `x-renovacoes-busca` (percent-encoded) e apaga `?q=` velho da barra (`:135`). Proxy: `pedido.ts` não tem `q` em `FILTROS_DA_QUERY` e repassa em `x-busca`. Backend: `listar_renovacoes` só lê `Header(alias="x-busca")`, e `?q=` não filtra (teste `test_jb1_q_na_query…`). Não há middleware que logue cabeçalho; `x-busca` só aparece em `app/api/renovacoes.py`. Acento: `busca_do_cabecalho` aceita percent-encoded, cru e UTF-8 lido como latin-1 (`brú` nas três formas). |
| **RT-B1** WhatsApp do dono congelado | **FECHADO** | `ultima_apresentacao` chama `P.quem_atende_mudou`, que compara nome + dígitos do `cta.whatsapp_url` da página com `quem_atende_agora` (dono **ativo** com número confirmado → corretora). Os formatos batem: os dois lados passam por `_digitos_de_whatsapp`. Os 4 casos (saiu, inativo, apagou, trocou) republicam; o controle "nada mudou" reaproveita o mesmo token sem versão nova. |
| **RT-B2** Copiar copiava o curto | **FECHADO** | `textos_do_envio`: `texto` = a completa, `texto_curto` = a do link (≤ 500). O hook lê só `j.texto` (`copiar` e "sem telefone"). No fio, `len(curto) < len(texto) ≤ 700`, e "Hoje você paga" e a assinatura estão no `texto`. |
| **RT-B3** telefone de `contatos[]` ou estrangeiro | **FECHADO** | `numero_de_whatsapp` lê só `telefone` e `telefones[]`, como `_client_phone`, e normaliza por `e164_do_brasil`, a regra do CHECK. `+1`, `001…`, `+351` e `+44` dão None; o fixo do cliente vence o celular do contador. |

**Mutação**, num worktree temporário em scratchpad (sem junction e já removido; a árvore principal não foi tocada). Reverti os 4 consertos juntos: `q` volta à query, `texto` = curto, `contatos[]` volta e `quem_atende_mudou → False`. Rodei `test_spec131b_conserto_k1.py -k "jb1 or rtb1_quem or rtb2 or rtb3"`:
📊 **9 failed** (jb1 ×2, rtb3, rtb2 ×2, rtb1 ×4 [saiu/inativo/apagou/trocou]), 28 deselected. Todos ficaram vermelhos.
Os guardas do Next também têm controle próprio, e ele passou: 📊 `a-busca-nao-vai-na-url.test.mjs` deu os dois CONTROLE OK (o `q` reinserido no `pedido.ts` e a tela de 66feb3e ficam vermelhos), mais o CONTROLE do Copiar (`texto_curto`).

## ATAQUES AO CONSERTO

- **(a) Busca.** Nenhum caminho põe a busca em URL, log ou evento. `grep [?&]q=|'q'` em `components/aplicativos`, `app/api/renovacoes` e `renovacoes.py` só acha a remoção do `q` velho. O teste do log (caplog) prova que o CPF não aparece em nenhum registro quando vai pelo cabeçalho, e a linha de controle prova que o guarda enxerga o CPF quando ele está na query.
- **(b) `quem_atende_mudou`.**
  - Não republica de menos: os 4 casos de mudança foram medidos.
  - Não republica demais: o controle reaproveita (versões iguais). Leitura que falha republica ("na dúvida"), o que é seguro.
  - Ver N1 para o único caso de oscilação possível.
- **(c) `fixar_referencia`.** O link enviado é sempre o `proposta_ref` gravado:
  - Na corrida, quem perde adota o link do outro (`test_rtp1`: enviado == gravado == o do outro clique).
  - Perto do fim do link, republica e a referência acompanha (`test_rtp2`).
  - Página órfã nunca é enviada. A apresentação usa o mesmo caminho (`renovacoes.py:875-879`).
- **(d) `confirmar_ligar`.** A tela manda o campo tanto na instalação quanto na retomada:
  - `botaoPrincipal` dá `confirmar:true` para `install` (Renovação) e para `resume` (pausado), em `catalog.ts:394/398`.
  - O `AlertDialogAction` chama `onAcao(acao, {confirmado:true})` (`CabecalhoDoAplicativo.tsx:140`), e `agir` põe `confirmar_ligar:true` no corpo (`AuxiliarDetalheClient.tsx:83`).
  - A rota confere `install || resume` antes de `installTenantAuxiliary`.
  - `catalog.ts` só importa `type` e serve no servidor.
- **(e) J-P4 (`_pode_mexer`).** O fluxo legítimo continua intacto: `por == dono` retorna antes da nova recusa (`conta_do_robo.py:528-529`). Os chamadores de `cadastrar_do_membro` são só `agir_do_membro` e testes em que a própria pessoa cadastra. 📊 Em `test_spec1310_f3_contas`, a própria pessoa conecta (200) e o admin recebe 409 "Meu perfil". `pausar`, `religar` e `desconectar` do admin seguem valendo.
- **(f) Cotação e canal byte a byte.** 📊 `scratchpad/g4/hashes.py` agora × `hashes_antes.txt`: **5/5 iguais** (cotacao_novo_sem/com_apolice `56d8c9e5…`, canal `d5c72d4b…`, previa `479e50c1…`, hash_script `c2d5df3d…`). As mudanças de design em `comparacao.py` e `proposta_html.py` só valem com `renovacao=True`.

## TESTES (saída real)

- 📊 `pytest -v test_spec131b_{conserto_k1,api_renovacoes,o_fio,perfil_e_ausencia,a_pagina_de_renovacao}.py test_spec1310_f3_contas.py`: **134 passed**, 18 warnings, em 863,67 s (a máquina estava carregada com o `next build`).
- 📊 `node components/aplicativos/casca/a-loja-e-a-casca.test.mjs`: "TODOS OS GUARDAS VERDES", exit 0.
- 📊 `node components/aplicativos/renovacao/a-busca-nao-vai-na-url.test.mjs`: "TODOS OS GUARDAS VERDES" (11 OK, 3 CONTROLE).

## DEFEITOS NOVOS (todos PENDÊNCIA; nenhum muda um byte hoje)

- **N1 · O número da corretora pode oscilar e fazer republicar a cada envio.** `whatsapp_da_corretora` → `_whatsapp_da_anfitria` lê `integrations` de atendimento **sem ORDER BY**. Com 2 ou mais integrações ativas pareadas, o número "de agora" pode trocar entre leituras, `quem_atende_mudou` dá True e cada envio vira uma página nova.
  - 📊 Exposição hoje: SELECT de 13/10 deu **0** corretoras com integração de atendimento ativa e pareada.
  - §2: não muda nada hoje → PENDÊNCIA.
  - Conserto: `order(created_at)` na leitura.
- **N2 · O "controle" do guarda RT-P7 é tautológico** (`test_spec131b_conserto_k1.py:443-445`). Ele substitui a string e confere que ela sumiu, o que nunca falha (CLAUDE.md §9.3, corolário). O guarda em si fica vermelho se a trava sair: `rota.index` lança. Falta só o controle honesto, ou um teste de runtime da rota.
- **N3 · A troca da referência não deixa rastro na linha do tempo.** `_trocar_referencia` muda `proposta_ref` + `versao` sem gravar evento em `renovacao_eventos`. Isso é inferência por leitura: não medi se o evento do envio carrega o token. Pendência de auditoria.
- **(herdada) J-P1 · §9.1 continua aberto:** `next build` + `next start` + uma requisição. O conserto mexeu em `app/` (rota nova `pedido.ts`, `route.ts`, telas). Não rodei por ordem do gerente.

## MAIOR LACUNA
O §9.1 não foi provado com este diff, porque nenhum servidor Next respondeu. O `pedido.ts` é um arquivo não-rota dentro de `app/api/renovacoes/`, importado por um componente cliente. Isso é legítimo, mas só o `next build` + `next start` confirma.

## CONFIANÇA — 88 · o que ficou por medir
`next start` (J-P1), o `x-busca` atravessando o proxy Next real e o N3.

## NOTA — 90
