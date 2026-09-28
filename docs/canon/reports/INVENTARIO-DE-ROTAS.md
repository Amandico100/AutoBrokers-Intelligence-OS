# notas gravadas: docs/canon/reports/NOTAS-DAS-ROTAS.json (73 rotas, 2026-09-28)
# Inventário de rotas — a régua aplicada às 73

> Gerado em **2026-09-28T02:48:52+00:00** · commit `f9b7204`
> 📊 acervo no momento da geração: **682 sessões** em 12 seguradoras

🔴 A nota é sempre sobre o **denominador real**. Item dispensado sai do
denominador e aparece explícito — **nunca é renormalizado**, e a
exibição **nunca é reescalada para /100**: `61/86 = 71%` pareceria
melhor que uma rota que ganhou 65 de 100 disputando tudo.

## A regra do Founder que governa este inventário

> *"Não é obrigatório termos todos os corredores 100%. O ideal é o máximo
> possível. O que não for possível ter no nível da Allianz residencial máquina
> de lavar deve ser feito o mais confiável e completo possível, ajudar os agentes
> a executar, e quando não conseguirem, vai para handoff. **Mas devemos ter
> LISTADO o que trava de ter o nível da máquina de lavar, para completarmos
> quando pudermos.**"*

🔴 **Uma rota em 60 com o bloqueio nomeado é ENTREGA. Uma rota em 95 com furo
invisível não é.** É por isso que este inventário tem três colunas, e não uma.

🔴 **A nota que se lê é `%`.** O `bruto` ao lado é o `pontos/denominador` que a sustenta — e o denominador **muda por rota**, então dois brutos não se comparam entre si. A `%` compara.

🔴 **A coluna `pedidos` é POR ROTA**, não por serviço — 📊 demanda medida em 2026-09-28 · fonte `observed_events` · `cd backend && python scripts/demanda_por_rota.py --medir --gravar`. `—` quer dizer **não medido**, nunca zero.

| seguradora | ramo | serviço | nota | bruto | patamar | 🔴 o que FALTA para o nível da máquina de lavar | 🔴 o que DESTRAVA | pedidos |
|---|---|---|---:|---:|---|---|---|---:|
| alfa | auto | guincho | **95%** | 72/76 | quase(76) | apelidos do jeito que o cliente fala (+4) | 🤖 conferir os apelidos pelo leitor do Espelho | 4 |
| allianz | auto | bateria | **95%** | 72/76 | quase(76) | apelidos do jeito que o cliente fala (+4) | 🤖 conferir os apelidos pelo leitor do Espelho | 3 |
| allianz | auto | guincho | **95%** | 72/76 | quase(76) | apelidos do jeito que o cliente fala (+4) | 🤖 conferir os apelidos pelo leitor do Espelho | 29 |
| allianz | auto | pneu | **95%** | 72/76 | quase(76) | apelidos do jeito que o cliente fala (+4) | 🤖 conferir os apelidos pelo leitor do Espelho | 3 |
| allianz | residencial | chaveiro | **95%** | 72/76 | quase(76) | apelidos do jeito que o cliente fala (+4) | 🤖 conferir os apelidos pelo leitor do Espelho | 2 |
| allianz | residencial | eletricista | **95%** | 72/76 | quase(76) | apelidos do jeito que o cliente fala (+4) | 🤖 conferir os apelidos pelo leitor do Espelho | 5 |
| azul | auto | bateria | **95%** | 72/76 | quase(76)!1 | apelidos do jeito que o cliente fala (+4) | 🤖 conferir os apelidos pelo leitor do Espelho | 3 |
| porto | auto | bateria | **95%** | 72/76 | quase(76)!1 | apelidos do jeito que o cliente fala (+4) | 🤖 conferir os apelidos pelo leitor do Espelho | 4 |
| yelum | auto | pneu | **95%** | 72/76 | quase(76)!1 | apelidos do jeito que o cliente fala (+4) | 🤖 conferir os apelidos pelo leitor do Espelho | 2 |
| yelum | residencial | encanador | **95%** | 72/76 | quase(76)!1 | apelidos do jeito que o cliente fala (+4) | 🤖 conferir os apelidos pelo leitor do Espelho | 4 |
| allianz | residencial | limpeza_caixa_dagua | **94%** | 66/70 | quase(70) | apelidos do jeito que o cliente fala (+4) | 🤖 conferir os apelidos pelo leitor do Espelho | 4 |
| zurich | auto | guincho | **94%** | 60/64 | quase(64) | apelidos do jeito que o cliente fala (+4) | 🤖 conferir os apelidos pelo leitor do Espelho | 2 |
| yelum | auto | socorro_mecanico | **93%** | 54/58 | quase(58)!1 | apelidos do jeito que o cliente fala (+4) | 🤖 conferir os apelidos pelo leitor do Espelho | 5 |
| alfa | auto | pneu | **92%** | 70/76 | quase(76) | apelidos do jeito que o cliente fala (+4) · >=2 sessoes distintas (+2) | 🧑 coleta: +1 sessão desta rota · 🤖 conferir os apelidos pelo leitor do Espelho | 1 |
| porto | residencial | encanador | **92%** | 70/76 | quase(76)!1 | apelidos do jeito que o cliente fala (+4) · a mais recente tem <180 dias (+2) | 🤖 conferir os apelidos pelo leitor do Espelho | 3 |
| porto | auto | tecnico | **91%** | 64/70 | quase(70)!1 | apelidos do jeito que o cliente fala (+4) · a mais recente tem <180 dias (+2) | 🤖 conferir os apelidos pelo leitor do Espelho | 2 |
| hdi | auto | socorro_mecanico | **90%** | 52/58 | quase(58)!1 | apelidos do jeito que o cliente fala (+4) · >=2 sessoes distintas (+2) | 🧑 coleta: +1 sessão desta rota · 🤖 conferir os apelidos pelo leitor do Espelho | 1 |
| hdi | auto | pneu | **89%** | 68/76 | quase(76)!1 | apelidos do jeito que o cliente fala (+4) · >=2 sessoes distintas (+2) · a mais recente tem <180 dias (+2) | 🧑 coleta: +1 sessão desta rota · 🤖 conferir os apelidos pelo leitor do Espelho | 1 |
| porto | auto | chaveiro | **89%** | 68/76 | quase(76)!1 | apelidos do jeito que o cliente fala (+4) · >=2 sessoes distintas (+2) · a mais recente tem <180 dias (+2) | 🧑 coleta: +1 sessão desta rota · 🤖 conferir os apelidos pelo leitor do Espelho | 1 |
| porto | residencial | chaveiro | **89%** | 68/76 | quase(76)!1 | apelidos do jeito que o cliente fala (+4) · >=2 sessoes distintas (+2) · a mais recente tem <180 dias (+2) | 🧑 coleta: +1 sessão desta rota · 🤖 conferir os apelidos pelo leitor do Espelho | 1 |
| allianz | residencial | consulta_veterinaria | **89%** | 62/70 | quase(70) | apelidos do jeito que o cliente fala (+4) · >=2 sessoes distintas (+2) · a mais recente tem <180 dias (+2) | 🧑 coleta: +1 sessão desta rota · 🤖 conferir os apelidos pelo leitor do Espelho | 1 |
| azul | auto | tecnico | **89%** | 62/70 | quase(70)!1 | apelidos do jeito que o cliente fala (+4) · >=2 sessoes distintas (+2) · a mais recente tem <180 dias (+2) | 🧑 coleta: +1 sessão desta rota · 🤖 conferir os apelidos pelo leitor do Espelho | 1 |
| allianz | residencial | ar_condicionado | **88%** | 67/76 | quase(76) | apelidos do jeito que o cliente fala (+4) · o handoff casa >=1 tela REAL (+3) · a mais recente tem <180 dias (+2) | 🤖 ampliar handoff_triggers contra o corpus · 🤖 conferir os apelidos pelo leitor do Espelho | 4 |
| yelum | residencial | eletricista | **88%** | 67/76 | quase(76)!1 | apelidos do jeito que o cliente fala (+4) · o handoff casa >=1 tela REAL (+3) · a mais recente tem <180 dias (+2) | 🤖 ampliar handoff_triggers contra o corpus · 🤖 conferir os apelidos pelo leitor do Espelho | 2 |
| allianz | residencial | maquina_de_lavar | **76%** | 58/76 | parcial(76) | zero orfas funcionais (+10) · 100% deterministico (+4) · apelidos do jeito que o cliente fala (+4) | 🤖 mapear 1 tela(s) · 🤖 subir o determinismo acima de 85% · 🤖 conferir os apelidos pelo leitor do Espelho | 6 |
| azul | auto | guincho | **76%** | 58/76 | parcial(76)!1 | zero orfas funcionais (+10) · 100% deterministico (+4) · apelidos do jeito que o cliente fala (+4) | 🤖 mapear 1 tela(s) · 🤖 subir o determinismo acima de 85% · 🤖 conferir os apelidos pelo leitor do Espelho | 7 |
| tokio | auto | guincho | **70%** | 45/64 | parcial(64) | o freio casa >=1 tela REAL (+8) · o cliente recebe protocolo + dia + periodo (+5) · apelidos do jeito que o cliente fala (+4) · a mais recente tem <180 dias (+2) | 🤖 client_summary com dia + período · 🤖 conferir os apelidos pelo leitor do Espelho | 3 |
| hdi | auto | chaveiro | **70%** | 53/76 | parcial(76)!1 | a ROTA foi percorrida ate o fim (+12) · o cliente recebe protocolo + dia + periodo (+5) · apelidos do jeito que o cliente fala (+4) · >=2 sessoes distintas (+2) | 🧑 coleta: +1 sessão desta rota · 🤖 client_summary com dia + período · 🤖 conferir os apelidos pelo leitor do Espelho | 1 |
| hdi | residencial | encanador | **68%** | 52/76 | parcial(76)!1 | zero orfas funcionais (+16) · 100% deterministico (+4) · apelidos do jeito que o cliente fala (+4) | 🤖 mapear 2 tela(s) · 🤖 subir o determinismo acima de 85% · 🤖 conferir os apelidos pelo leitor do Espelho | 3 |
| hdi | auto | guincho | **63%** | 48/76 | parcial(76)!1 | zero orfas funcionais (+20) · 100% deterministico (+4) · apelidos do jeito que o cliente fala (+4) | 🤖 mapear 21 tela(s) · 🤖 subir o determinismo acima de 85% · 🤖 conferir os apelidos pelo leitor do Espelho | 16 |
| porto | auto | guincho | **63%** | 48/76 | parcial(76)!1 | zero orfas funcionais (+20) · 100% deterministico (+4) · apelidos do jeito que o cliente fala (+4) | 🤖 mapear 17 tela(s) · 🤖 subir o determinismo acima de 85% · 🤖 conferir os apelidos pelo leitor do Espelho | 25 |
| yelum | auto | guincho | **63%** | 48/76 | parcial(76)!1 | zero orfas funcionais (+20) · 100% deterministico (+4) · apelidos do jeito que o cliente fala (+4) | 🤖 mapear 22 tela(s) · 🤖 subir o determinismo acima de 85% · 🤖 conferir os apelidos pelo leitor do Espelho | 26 |
| allianz | residencial | eletrodomesticos | **62%** | 47/76 | parcial(76) | a ROTA foi percorrida ate o fim (+12) · o freio casa >=1 tela REAL (+8) · o cliente recebe protocolo + dia + periodo (+5) · apelidos do jeito que o cliente fala (+4) | 🤖 client_summary com dia + período · 🤖 conferir os apelidos pelo leitor do Espelho | 3 |
| porto | residencial | eletrodomesticos | **61%** | 39/64 | parcial(64)!1 | o freio casa >=1 tela REAL (+8) · o cliente recebe protocolo + dia + periodo (+5) · apelidos do jeito que o cliente fala (+4) · expectativa_do_desfecho existe (+3) | 🧑 coleta: +1 sessão desta rota · 🤖 client_summary com dia + período · 🤖 conferir os apelidos pelo leitor do Espelho · 🤖 escrever as regras que a URA diz ao segurado | 1 |
| yelum | residencial | eletrodomesticos | **59%** | 45/76 | parcial(76)!1 | a ROTA foi percorrida ate o fim (+12) · o freio casa >=1 tela REAL (+8) · o cliente recebe protocolo + dia + periodo (+5) · apelidos do jeito que o cliente fala (+4) | 🧑 coleta: +1 sessão desta rota · 🤖 client_summary com dia + período · 🤖 conferir os apelidos pelo leitor do Espelho | 1 |
| allianz | residencial | desentupimento | **58%** | 44/76 | parcial(76) | a ROTA foi percorrida ate o fim (+12) · o freio casa >=1 tela REAL (+8) · o cliente recebe protocolo + dia + periodo (+5) · apelidos do jeito que o cliente fala (+4) | 🤖 client_summary com dia + período · 🤖 ampliar handoff_triggers contra o corpus · 🤖 conferir os apelidos pelo leitor do Espelho | 4 |
| hdi | residencial | chaveiro | **57%** | 43/76 | parcial(76)!1 | a ROTA foi percorrida ate o fim (+12) · o freio casa >=1 tela REAL (+8) · o cliente recebe protocolo + dia + periodo (+5) · apelidos do jeito que o cliente fala (+4) | 🧑 coleta: +1 sessão desta rota · 🤖 client_summary com dia + período · 🤖 conferir os apelidos pelo leitor do Espelho | 1 |
| yelum | auto | bateria | **57%** | 43/76 | parcial(76)!1 | a ROTA foi percorrida ate o fim (+12) · o freio casa >=1 tela REAL (+8) · o cliente recebe protocolo + dia + periodo (+5) · apelidos do jeito que o cliente fala (+4) | 🧑 coleta: +1 sessão desta rota · 🤖 client_summary com dia + período · 🤖 conferir os apelidos pelo leitor do Espelho | 1 |
| allianz | residencial | encanador | **55%** | 42/76 | parcial(76) | zero orfas funcionais (+20) · a rota anda sozinha (+6) · 100% deterministico (+4) · apelidos do jeito que o cliente fala (+4) | 🤖 mapear 4 tela(s) · 🤖 subir o determinismo acima de 85% · 🤖 conferir os apelidos pelo leitor do Espelho | 18 |
| porto | auto | vidros | **53%** | 37/70 | esqueleto(70)!1 | a ROTA foi percorrida ate o fim (+12) · o freio casa >=1 tela REAL (+8) · o cliente recebe protocolo + dia + periodo (+5) · apelidos do jeito que o cliente fala (+4) | 🧑 coleta: +1 sessão desta rota · 🤖 client_summary com dia + período · 🤖 conferir os apelidos pelo leitor do Espelho | 1 |
| bradesco | auto | guincho | **41%** | 31/76 | esqueleto(76)!1 | zero orfas funcionais (+20) · a ROTA foi percorrida ate o fim (+12) · o cliente recebe protocolo + dia + periodo (+5) · 100% deterministico (+4) | 🤖 mapear 5 tela(s) · 🤖 subir o determinismo acima de 85% · 🤖 client_summary com dia + período · 🤖 conferir os apelidos pelo leitor do Espelho | 5 |
| hdi | residencial | eletricista | **30%** | 23/76 | esqueleto(76)!1 | zero orfas funcionais (+20) · a ROTA foi percorrida ate o fim (+12) · o freio casa >=1 tela REAL (+8) · o cliente recebe protocolo + dia + periodo (+5) | 🤖 mapear 3 tela(s) · 🤖 subir o determinismo acima de 85% · 🤖 client_summary com dia + período · 🤖 conferir os apelidos pelo leitor do Espelho | 5 |
| alfa | auto | bateria | **SEM_CORPUS** | — | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | — |
| alfa | auto | chaveiro | **SEM_CORPUS** | — | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | — |
| allianz | auto | chaveiro | **SEM_CORPUS** | — | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | — |
| azul | auto | chaveiro | **SEM_CORPUS** | — | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | — |
| azul | auto | pneu | **SEM_CORPUS** | — | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | — |
| bradesco | auto | bateria | **SEM_CORPUS** | — | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | — |
| bradesco | auto | chaveiro | **SEM_CORPUS** | — | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | — |
| bradesco | auto | pneu | **SEM_CORPUS** | — | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | — |
| hdi | auto | bateria | **SEM_CORPUS** | — | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | — |
| hdi | residencial | desentupimento | **SEM_CORPUS** | — | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | — |
| hdi | residencial | eletrodomesticos | **SEM_CORPUS** | — | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | — |
| mapfre | auto | bateria | **SEM_CORPUS** | — | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | — |
| mapfre | auto | chaveiro | **SEM_CORPUS** | — | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | — |
| mapfre | auto | guincho | **SEM_CORPUS** | — | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | — |
| mapfre | auto | pneu | **SEM_CORPUS** | — | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | — |
| porto | auto | bateria_nova | **SEM_CORPUS** | — | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | — |
| porto | auto | pneu | **SEM_CORPUS** | — | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | — |
| porto | auto | taxi | **SEM_CORPUS** | — | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | — |
| porto | residencial | desentupimento | **SEM_CORPUS** | — | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | — |
| porto | residencial | eletricista | **SEM_CORPUS** | — | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | — |
| tokio | auto | bateria | **SEM_CORPUS** | — | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | — |
| tokio | auto | chaveiro | **SEM_CORPUS** | — | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | — |
| tokio | auto | pneu | **SEM_CORPUS** | — | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | — |
| yelum | auto | chaveiro | **SEM_CORPUS** | — | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | — |
| yelum | residencial | chaveiro | **SEM_CORPUS** | — | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | — |
| yelum | residencial | desentupimento | **SEM_CORPUS** | — | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | — |
| zurich | auto | bateria | **SEM_CORPUS** | — | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | — |
| zurich | auto | chaveiro | **SEM_CORPUS** | — | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | — |
| zurich | auto | pneu | **SEM_CORPUS** | — | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | — |
| zurich | auto | socorro_mecanico | **SEM_CORPUS** | — | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | — |
| zurich | auto | vidros | **SEM_CORPUS** | — | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | — |

## Os eixos, para quem quiser a decomposição

| seguradora | ramo | serviço | A | B | C | D | E | família |
|---|---|---|---:|---:|---:|---:|---:|---|
| alfa | auto | guincho | 16 | 33 | 11 | 6 | — | — |
| allianz | auto | bateria | 16 | 33 | 11 | 6 | — | — |
| allianz | auto | guincho | 16 | 33 | 11 | 6 | — | — |
| allianz | auto | pneu | 16 | 33 | 11 | 6 | — | — |
| allianz | residencial | chaveiro | 16 | 33 | 11 | 6 | — | — |
| allianz | residencial | eletricista | 16 | 33 | 11 | 6 | — | — |
| azul | auto | bateria | 16 | 33 | 11 | 6 | — | — |
| porto | auto | bateria | 16 | 33 | 11 | 6 | — | — |
| yelum | auto | pneu | 16 | 33 | 11 | 6 | — | — |
| yelum | residencial | encanador | 16 | 33 | 11 | 6 | — | — |
| allianz | residencial | limpeza_caixa_dagua | 16 | 33 | 11 | 0 | — | — |
| zurich | auto | guincho | 4 | 33 | 11 | 6 | — | — |
| yelum | auto | socorro_mecanico | 4 | 33 | 11 | 0 | — | — |
| alfa | auto | pneu | 14 | 33 | 11 | 6 | — | — |
| porto | residencial | encanador | 14 | 33 | 11 | 6 | — | — |
| porto | auto | tecnico | 14 | 33 | 11 | 0 | — | — |
| hdi | auto | socorro_mecanico | 2 | 33 | 11 | 0 | — | — |
| hdi | auto | pneu | 12 | 33 | 11 | 6 | — | — |
| porto | auto | chaveiro | 12 | 33 | 11 | 6 | — | — |
| porto | residencial | chaveiro | 12 | 33 | 11 | 6 | — | — |
| allianz | residencial | consulta_veterinaria | 12 | 33 | 11 | 0 | — | — |
| azul | auto | tecnico | 12 | 33 | 11 | 0 | — | — |
| allianz | residencial | ar_condicionado | 14 | 33 | 8 | 6 | — | — |
| yelum | residencial | eletricista | 14 | 33 | 8 | 6 | — | — |
| allianz | residencial | maquina_de_lavar | 16 | 19 | 11 | 6 | — | — |
| azul | auto | guincho | 16 | 19 | 11 | 6 | — | — |
| tokio | auto | guincho | 2 | 28 | 3 | 6 | — | — |
| hdi | auto | chaveiro | 2 | 28 | 11 | 6 | — | — |
| hdi | residencial | encanador | 16 | 13 | 11 | 6 | — | — |
| hdi | auto | guincho | 16 | 9 | 11 | 6 | — | — |
| porto | auto | guincho | 16 | 9 | 11 | 6 | — | — |
| yelum | auto | guincho | 16 | 9 | 11 | 6 | — | — |
| allianz | residencial | eletrodomesticos | 4 | 28 | 3 | 6 | — | — |
| porto | residencial | eletrodomesticos | 2 | 28 | 3 | 0 | — | — |
| yelum | residencial | eletrodomesticos | 2 | 28 | 3 | 6 | — | — |
| allianz | residencial | desentupimento | 4 | 28 | 0 | 6 | — | — |
| hdi | residencial | chaveiro | 0 | 28 | 3 | 6 | — | — |
| yelum | auto | bateria | 0 | 28 | 3 | 6 | — | — |
| allianz | residencial | encanador | 16 | 9 | 11 | 6 | — | — |
| porto | auto | vidros | 0 | 28 | 3 | 0 | — | — |
| bradesco | auto | guincho | 4 | 4 | 11 | 6 | — | — |
| hdi | residencial | eletricista | 4 | 4 | 3 | 6 | — | — |
| alfa | auto | bateria | — | — | — | — | — | — |
| alfa | auto | chaveiro | — | — | — | — | — | — |
| allianz | auto | chaveiro | — | — | — | — | — | — |
| azul | auto | chaveiro | — | — | — | — | — | — |
| azul | auto | pneu | — | — | — | — | — | — |
| bradesco | auto | bateria | — | — | — | — | — | — |
| bradesco | auto | chaveiro | — | — | — | — | — | — |
| bradesco | auto | pneu | — | — | — | — | — | — |
| hdi | auto | bateria | — | — | — | — | — | — |
| hdi | residencial | desentupimento | — | — | — | — | — | — |
| hdi | residencial | eletrodomesticos | — | — | — | — | — | — |
| mapfre | auto | bateria | — | — | — | — | — | — |
| mapfre | auto | chaveiro | — | — | — | — | — | — |
| mapfre | auto | guincho | — | — | — | — | — | — |
| mapfre | auto | pneu | — | — | — | — | — | — |
| porto | auto | bateria_nova | — | — | — | — | — | — |
| porto | auto | pneu | — | — | — | — | — | — |
| porto | auto | taxi | — | — | — | — | — | — |
| porto | residencial | desentupimento | — | — | — | — | — | — |
| porto | residencial | eletricista | — | — | — | — | — | — |
| tokio | auto | bateria | — | — | — | — | — | — |
| tokio | auto | chaveiro | — | — | — | — | — | — |
| tokio | auto | pneu | — | — | — | — | — | — |
| yelum | auto | chaveiro | — | — | — | — | — | — |
| yelum | residencial | chaveiro | — | — | — | — | — | — |
| yelum | residencial | desentupimento | — | — | — | — | — | — |
| zurich | auto | bateria | — | — | — | — | — | — |
| zurich | auto | chaveiro | — | — | — | — | — | — |
| zurich | auto | pneu | — | — | — | — | — | — |
| zurich | auto | socorro_mecanico | — | — | — | — | — | — |
| zurich | auto | vidros | — | — | — | — | — | — |
