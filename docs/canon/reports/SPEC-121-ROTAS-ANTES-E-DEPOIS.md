# SPEC-121 · as rotas antes e depois — cada queda com a causa

> 📊 medido em 30/09/2026, commit `4ccd063`. **Antes** = os arquivos da SPEC-120 como estão no
> `HEAD` (simulação de 29/09 no commit `5ae1755`; régua de 29/09 no commit `ecb701e`).
> **Depois** = regerados nesta fatia:
> ```
> cd backend && python scripts/medir_rota.py --todas --gravar-notas docs/canon/reports/NOTAS-DAS-ROTAS.json   # em worktree separado
> cd backend && python scripts/simular_corredor.py --todas --formato json > ../docs/canon/reports/SIMULACAO-DOS-CORREDORES.json
> cd backend && python scripts/pagina_dos_corredores.py --gravar
> ```
> O acervo (`backend/tests/corpus/telas_reais/`) foi regerado nesta SPEC: sessões partidas em
> atendimentos onde o robô recomeça · a consulta de pedido que já existia ("Ver detalhes") fora ·
> etiquetas `chave → chaveiro` e `recarga → bateria` · fogão pedido pelo menu do eletricista sem
> etiqueta · 3 rotas novas de carro reserva.

## O placar (faixa do simulador)

| | antes | depois |
|---|---|---|
| rotas | 73 | **76** (+3 de carro reserva) |
| ATENDE SOZINHO | 31 | **31** |
| VAI PARA UMA PESSOA (HANDOFF) | 2 | **4** |
| FALTA CAPTURA | 40 | **41** |

## Mudou de faixa

| rota | antes → depois | causa |
|---|---|---|
| `yelum/auto/bateria` | FALTA CAPTURA → **ATENDE SOZINHO** ⬆ | `recarga → bateria`: 📊 22 → 201 telas, 1 → 6 sessões; a rota ganhou sessões com desfecho |
| `yelum/auto/socorro_mecanico` | ATENDE SOZINHO → **FALTA CAPTURA** ⬇ | as 📊 179 telas / 5 sessões que a sustentavam eram **recarga de bateria** mal etiquetadas — foram, todas, para `yelum/auto/bateria`. O "atende" antigo era falso; a rota não tem hoje uma conversa sua |
| `tokio/auto/carro_reserva` | (nova) → HANDOFF | desenho: a seguradora entrega link (📊 21 telas) |
| `yelum/auto/carro_reserva` | (nova) → HANDOFF | desenho `encaminha` (📊 91 telas) — ver ⚠️ abaixo |
| `azul/auto/carro_reserva` | (nova) → FALTA CAPTURA | nenhuma conversa desta rota no acervo |

## Mudou de nota na régua (sem mudar de faixa)

| rota | antes → depois | causa |
|---|---|---|
| `yelum/auto/bateria` | 57 → **95** ⬆ | `recarga → bateria` (acima) |
| `yelum/auto/chaveiro` | SEM_CORPUS → **55** ⬆ | `chave → chaveiro`: 📊 0 → 72 telas, 2 sessões; segue FALTA CAPTURA por tela órfã |
| `hdi/auto/socorro_mecanico` | 90 → **93** ⬆ | sessão partida: 📊 1 → 2 sessões (item ">=2 sessões") |
| `allianz/residencial/consulta_veterinaria` | 89 → **91** ⬆ | sessão partida: 📊 1 → 2 sessões |
| `allianz/residencial/eletricista` | 95 → **88** ⬇ | **consulta fora**: a única tela de handoff (📊 sessão de 01/2026) era da consulta de um pedido existente (acompanhar/cancelar) e saiu do acervo (−3, "handoff casa ≥1 tela real"); e a sessão mais recente (07/2026, recomeçou e foi para outro serviço) deixou de ser eletricista — a mais recente agora é de 📊 19/01/2026, > 180 dias (−2). 💭 INFERÊNCIA sobre o porquê da segunda: partida onde o robô recomeça |
| `allianz/residencial/maquina_de_lavar` | 95 → **91** ⬇ | **consulta fora**: as 📊 3 telas que casavam o handoff eram "Ver detalhes → alterar/cancelar" de pedido já aberto (−3, mesmo item). Sessões 5 → 5 (duas trocadas pelo piso de diversidade) |
| `hdi/residencial/eletricista` | 30 → **SEM_CORPUS** ⬇ | **fogão pelo menu do eletricista**: as 📊 5 sessões / 109 telas pediam conserto de fogão → sem etiqueta (regra F3/F3b). Já era FALTA CAPTURA (tela órfã); agora a causa é "sem conversa desta rota" |
| `yelum/auto/socorro_mecanico` | 93 → **SEM_CORPUS** ⬇ | ver acima (`recarga → bateria`) |
| 9 rotas de `allianz/residencial` | % igual (salvo as 2 acima) · **portão B aberto** | "notes com contagem que RECONTA": 📊 em `allianz/residencial/chaveiro`, 19 de 22 notes reproduzem contra o acervo novo. O número das `notes` do playbook foi medido no acervo antigo; a população mudou (consulta fora, sessões partidas). 🤖 recontar as 3 notes |

## ⚠️ Duas observações para o gerente (não consertadas aqui)

1. `yelum/auto/carro_reserva` aparece na aba com o motivo *"a seguradora não abre pela conversa: devolve
   link ou formulário"*. Para a Yelum não é exato: o robô percorre a URA até *"em análise"* e fecha como
   `encaminha` (canal próprio, pronto e desligado sem `INSURER_CONTACT_YELUM_CARRO_RESERVA`). O texto
   vem do ramo `por_desenho_link` de `simular_corredor.py`, que junta link e encaminhamento.
2. A coluna de pedidos mudou em muitas rotas porque a unidade virou **atendimentos** (commit `998f9da`);
   isso não é subida nem queda de rota.
3. 📊 As 9 rotas da Allianz residencial perderam 1 ponto no item "as notas contam certo" (2/2 → 1/2): as telas de 3 passos
   (`link_acompanha` = consulta de pedido, `escolher_entre_dois_enderecos`, `repique_somente_numeros`) saíram do acervo com a
   janela de consulta e a partição por atendimento (triagem da bateria, 30/09). A régua lê "zero telas" como "a nota mente";
   com o corpus agora excluindo zonas de propósito, isso é uma decisão sobre a régua (P-121-24).
