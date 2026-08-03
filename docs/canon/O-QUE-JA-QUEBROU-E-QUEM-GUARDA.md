# O que já quebrou, e quem guarda para não quebrar de novo

> **03/08/2026.** Cada defeito encontrado nesta jornada, o que ele causava, e o
> **teste automático** que impede o retorno.
>
> A pergunta que este documento responde: *"consertamos, mas continua
> consertado?"* — e a resposta não pode ser memória de ninguém.
>
> 📊 Suíte: **132 testes**, 0 vermelhos. Portão: `python backend/tests/run_all.py`

---

## Como ler

| Coluna | Significado |
|---|---|
| **O defeito** | o que estava errado, e o que causava |
| **Quem guarda** | o teste que falha se voltar |
| **Estado** | ✅ consertado e guardado · ⚠️ consertado sem guarda · 🔴 aberto |

---

## 🖥️ O produto no ar

| O defeito | Quem guarda | Estado |
|---|---|---|
| **Duas pastas `[slug]` e `[templateId]` na mesma posição da rota derrubaram o site inteiro por 1h40** — com build verde, 111 testes verdes e o contêiner dizendo `Ready`. Todos os portões paravam antes de ligar o servidor | `test_a_tabela_de_rotas_monta.py` + `scripts/rotas-montam.test.mjs` (chama o `getSortedRoutes` real do Next) | ✅ |
| **A tela de Corredores contava playbooks e chamava de corredores** | `test_a_pagina_de_corredores_diz_a_verdade.py` | ✅ |

> **Regra que nasceu daí (CLAUDE.md §9.1): uma rota que responde 200 vale mais
> que um build de 287 rotas.**

---

## 🔒 Quem fala com o segurado

| O defeito | Quem guarda | Estado |
|---|---|---|
| **`"agent_id": None if purpose == "observer" else None`** — um ternário que devolve `None` nos dois ramos. Sem dono, o motor pegava o agente mais antigo: 📊 o **core**, que entrega CPF sem mascarar | `test_quem_responde_o_segurado.py` | ✅ |
| **CPF vazava por DOIS caminhos** — o prompt e a tool. Quem consertasse só o prompt acharia que resolveu | idem | ✅ |
| **O handoff dizia "um atendente foi solicitado" TAMBÉM quando falhava** | `test_handoff_chega_em_alguem.py` | ✅ |
| **Duas corretoras no mesmo grupo de suporte** — dossiê com CPF cairia no grupo da outra | idem (recusa fail-closed) | ✅ |
| **Buffer com chave só de telefone** — conversas de corretoras diferentes se fundiam | `test_higiene_de_plataforma.py` | ✅ |
| **O observador era escolhido como canal de saída quando era o único ativo** | idem | ✅ |

---

## 📡 O canal

| O defeito | Quem guarda | Estado |
|---|---|---|
| **Três integrações diziam `connected` com `last_seen_at` congelado há 4 dias** — `connection.update` é evento de transição e não chega em canal parado: silêncio e saúde eram indistinguíveis | `test_o_canal_nao_mente.py` (o heartbeat confirma antes de contestar; sem resposta grava `unknown`, não `disconnected`) | ✅ |
| **🆕 Beco sem saída do pareamento** — instância já existente com telefone fazia todo "Gerar novo QR" morrer em *"precisa de ajuste pelo suporte"*. E como a tela dizia "Desconectado", **não havia botão Desconectar**: sem QR e sem saída | `test_o_pareamento_nao_vira_beco_sem_saida.py` | ✅ |
| **🆕 O escopo da observação se desfazia sozinho** — o pareamento sobrescrevia `observer_scope` por atribuição; quem escolhia `insurers_only` perdia no re-pareamento seguinte | `test_o_pareamento_respeita_o_escopo.py` | ✅ |
| **🆕 `observer_exclusions` só valia AO VIVO** — o histórico do pareamento (que é o volume: anos contra um dia) passava direto | idem | ✅ |

---

## 🎯 O acionamento

| O defeito | Quem guarda | Estado |
|---|---|---|
| **937 cliques de botão + 23 de formulário gravados VAZIOS** | `test_o_clique_nao_se_perde.py` | ✅ |
| **Fallback da Allianz** — segurado da Porto seria roteado para a Allianz | `test_corredores_novos.py` | ✅ |
| **O acionamento vivia só no Redis com TTL 6h** — restart perdia acionamento em voo | `test_acionamento_sobrevive.py` | ✅ |
| **`billing_collection` disparava 100 mensagens em rajada** — número novo fazendo isso é banido, e quem perde o canal é a corretora | `test_governador_de_envio.py` | ✅ |
| **A memória do atendimento era a janela de 60 mensagens** — o agente repediu o CPF do mesmo cliente | `test_o_atendimento_tem_memoria.py` | ✅ |
| **12 playbooks de conduta destilados de 297 atendimentos, órfãos** — `grep conduct_playbook graph.py` → zero | `test_a_conduta_chega_ao_turno.py` | ✅ |
| **🆕 O envelope do formulário era adivinhado** — usávamos o `flow_name`; o real é `galaxy_message`. Envelope errado = resposta descartada **em silêncio** | `test_o_acionamento_nao_trava.py` | ✅ |
| **🆕 A resposta do formulário não tinha transporte** — `flow_sender` chegava sempre `None`; todo formulário parava com a resposta pronta ao lado | `test_o_formulario_nativo_tem_transporte.py` | ✅ |
| **🆕 Sem o embrulho `DocumentWithCaption`, o WhatsApp recusa com 479** | idem + 6 testes Go dentro do build | ✅ |

---

## 🏗️ A corretora

| O defeito | Quem guarda | Estado |
|---|---|---|
| **`ensureAgentByRole` devolvia `exists` e nunca atualizava** — corretora nascia incompleta | `test_a_corretora_nasce_completa.py` | ✅ |
| **AutoFleet com core ativo e MUDO** (prompt de 0 caracteres) | idem + view no banco | ✅ |

---

## 🔴 Aberto — sem guarda ainda

| # | O quê | Por que ainda não |
|---|---|---|
| **P-67** | **Conversa pessoal no número da corretora pode virar carta no RAG.** O telefone de uma corretora é um telefone de gente: *"oi amor, passa no mercado"* é o normal. 📊 O filtro de PII existe e reprova (310 cartas barradas), mas ele mira em **dado pessoal**, não em **pertinência** — conversa doméstica sem CPF passa limpa. E a curadoria publica sem aprovação humana | precisa de uma **prova de pertinência** antes de destilar, e o teste tem de mostrar que ela recusa um exemplo doméstico real |
| **P-65** | A tela de pareamento não declara **o que será capturado** antes do QR | é mudança de UI + decisão de copy |
| **P-66** | Payload cru do primeiro history sync fica 7 dias no Redis (vence 10/08) | vence sozinho; não está em índice nem em RAG |
| **§7 do formulário** | 4 coisas não provadas: `version`, `response_message`, **o desfecho na seguradora**, `MessageSecret` | ver [`O-FORMULARIO-NATIVO-RESOLVIDO.md`](O-FORMULARIO-NATIVO-RESOLVIDO.md) §7 |

---

## A regra que atravessa tudo isto

> **Um guarda que não tem como falhar não está guardando nada.**

Vários testes desta lista incluem uma verificação de que **eles próprios
conseguem reprovar** — o teste do formulário confere que `Unmarshal`+`Marshal`
de fato altera o texto, senão a comparação byte a byte estaria passando por
coincidência.

E o corolário, aprendido caro em 03/08: **teste que guarda uma verdade vencida é
pior que teste nenhum.** Dois testes tiveram de ser atualizados quando o canal
de formulário passou a existir. A lição não morreu — mudou de lugar: a recusa
limpa continua testada, agora **desligando a rota de propósito**.
