# Inventário de rotas — a régua aplicada às 73

> Gerado em **2026-08-23T03:09:43+00:00** · commit `4dc6ab0`
> 📊 acervo no momento da geração: **543 sessões** em 10 seguradoras

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

| seguradora | ramo | serviço | nota | patamar | 🔴 o que FALTA para o nível da máquina de lavar | 🔴 o que DESTRAVA | dem |
|---|---|---|---:|---|---|---|---:|
| allianz | residencial | encanador | **106/106** | AAA(106) | nada — está no nível | nada | 14 |
| allianz | residencial | maquina_de_lavar | **106/106** | AAA(106) | nada — está no nível | nada | 0 |
| allianz | residencial | chaveiro | **102/106** | AAA(106) | apelidos do jeito que o cliente fala (+4) | 🧑 acesso ao Espelho para conferir os apelidos | 5 |
| allianz | residencial | eletricista | **102/106** | AAA(106) | apelidos do jeito que o cliente fala (+4) | 🧑 acesso ao Espelho para conferir os apelidos | 12 |
| allianz | residencial | ar_condicionado | **99/106** | quase(106) | apelidos do jeito que o cliente fala (+4) · o handoff casa >=1 tela REAL (+3) | 🤖 ampliar handoff_triggers contra o corpus · 🧑 acesso ao Espelho para conferir os apelidos | 2 |
| alfa | auto | guincho | **90/106** | quase(106) | transcrita no bloco do subservico (+4) · apelidos do jeito que o cliente fala (+4) · expectativa_do_desfecho existe (+3) · regras_para_o_cliente casam o corpus (+3) | 🤖 transcrever a sessão no bloco · 🤖 recontar as notes · 🧑 acesso ao Espelho para conferir os apelidos · 🤖 escrever as regras que a URA diz ao segurado | 72 |
| alfa | auto | pneu | **88/106** | quase(106) | transcrita no bloco do subservico (+4) · apelidos do jeito que o cliente fala (+4) · expectativa_do_desfecho existe (+3) · regras_para_o_cliente casam o corpus (+3) | 🤖 transcrever a sessão no bloco · 🧑 coleta: +1 sessão desta rota · 🤖 recontar as notes · 🧑 acesso ao Espelho para conferir os apelidos · 🤖 escrever as regras que a URA diz ao segurado | 10 |
| yelum | auto | pneu | **87/106** | quase(106) | transcrita no bloco do subservico (+4) · apelidos do jeito que o cliente fala (+4) · expectativa_do_desfecho existe (+3) · regras_para_o_cliente casam o corpus (+3) | 🤖 transcrever a sessão no bloco · 🤖 recontar as notes · 🧑 acesso ao Espelho para conferir os apelidos · 🤖 escrever as regras que a URA diz ao segurado | 10 |
| hdi | auto | socorro_mecanico | **67/84** | parcial(84) | zero orfas funcionais (+10) · >=1 linha de CONTROLE (+3) · >=2 sessoes distintas (+2) · notes com contagem que RECONTA (+2) | 🧑 coleta: +1 sessão desta rota · 🤖 mapear 1 tela(s) · 🤖 recontar as notes | 7 |
| hdi | auto | pneu | **83/106** | parcial(106) | transcrita no bloco do subservico (+4) · apelidos do jeito que o cliente fala (+4) · expectativa_do_desfecho existe (+3) · regras_para_o_cliente casam o corpus (+3) | 🤖 transcrever a sessão no bloco · 🧑 coleta: +1 sessão desta rota · 🤖 recontar as notes · 🧑 acesso ao Espelho para conferir os apelidos · 🤖 escrever as regras que a URA diz ao segurado | 10 |
| allianz | residencial | limpeza_caixa_dagua | **73/96** | parcial(96) | zero orfas funcionais (+16) · apelidos do jeito que o cliente fala (+4) · o handoff casa >=1 tela REAL (+3) | 🤖 mapear 2 tela(s) · 🤖 ampliar handoff_triggers contra o corpus · 🧑 acesso ao Espelho para conferir os apelidos | 2 |
| yelum | auto | socorro_mecanico | **59/84** | parcial(84) | zero orfas funcionais (+20) · >=1 linha de CONTROLE (+3) · notes com contagem que RECONTA (+2) | 🤖 mapear 3 tela(s) · 🤖 recontar as notes | 7 |
| allianz | auto | pneu | **74/106** | parcial(106) | zero orfas funcionais (+16) · transcrita no bloco do subservico (+4) · apelidos do jeito que o cliente fala (+4) · expectativa_do_desfecho existe (+3) | 🤖 transcrever a sessão no bloco · 🤖 mapear 2 tela(s) · 🤖 recontar as notes · 🧑 acesso ao Espelho para conferir os apelidos · 🤖 escrever as regras que a URA diz ao segurado | 10 |
| allianz | residencial | consulta_veterinaria | **66/96** | parcial(96) | zero orfas funcionais (+20) · >=85% deterministico (+4) · apelidos do jeito que o cliente fala (+4) · >=2 sessoes distintas (+2) | 🧑 coleta: +1 sessão desta rota · 🤖 mapear 4 tela(s) · 🤖 subir o determinismo acima de 85% · 🧑 acesso ao Espelho para conferir os apelidos | 0 |
| porto | auto | vidros | **66/96** | parcial(96) | a ROTA foi percorrida ate o fim (+12) · o freio casa >=1 tela REAL (+8) · o cliente recebe protocolo + dia + periodo (+5) · >=2 sessoes distintas (+2) | 🧑 coleta: +1 sessão desta rota · 🤖 client_summary com dia + período · 🤖 recontar as notes | 0 |
| allianz | auto | guincho | **70/106** | parcial(106) | zero orfas funcionais (+20) · transcrita no bloco do subservico (+4) · apelidos do jeito que o cliente fala (+4) · expectativa_do_desfecho existe (+3) | 🤖 transcrever a sessão no bloco · 🤖 mapear 4 tela(s) · 🤖 recontar as notes · 🧑 acesso ao Espelho para conferir os apelidos · 🤖 escrever as regras que a URA diz ao segurado | 72 |
| allianz | residencial | eletrodomesticos | **70/106** | parcial(106) | a ROTA foi percorrida ate o fim (+12) · o freio casa >=1 tela REAL (+8) · o cliente recebe protocolo + dia + periodo (+5) · transcrita no bloco do subservico (+4) | 🤖 transcrever a sessão no bloco · 🤖 client_summary com dia + período · 🧑 acesso ao Espelho para conferir os apelidos · 🤖 escrever as regras que a URA diz ao segurado | 0 |
| yelum | residencial | eletricista | **69/106** | parcial(106) | zero orfas funcionais (+16) · transcrita no bloco do subservico (+4) · apelidos do jeito que o cliente fala (+4) · o handoff casa >=1 tela REAL (+3) | 🤖 transcrever a sessão no bloco · 🤖 mapear 2 tela(s) · 🤖 recontar as notes · 🤖 ampliar handoff_triggers contra o corpus · 🧑 acesso ao Espelho para conferir os apelidos · 🤖 escrever as regras que a URA diz ao segurado | 12 |
| yelum | residencial | encanador | **67/106** | parcial(106) | zero orfas funcionais (+20) · transcrita no bloco do subservico (+4) · >=85% deterministico (+4) · o handoff casa >=1 tela REAL (+3) | 🤖 transcrever a sessão no bloco · 🤖 mapear 7 tela(s) · 🤖 subir o determinismo acima de 85% · 🤖 recontar as notes · 🤖 ampliar handoff_triggers contra o corpus · 🤖 escrever as regras que a URA diz ao segurado | 14 |
| allianz | auto | bateria | **66/106** | parcial(106) | zero orfas funcionais (+20) · transcrita no bloco do subservico (+4) · >=85% deterministico (+4) · apelidos do jeito que o cliente fala (+4) | 🤖 transcrever a sessão no bloco · 🤖 mapear 5 tela(s) · 🤖 subir o determinismo acima de 85% · 🤖 recontar as notes · 🧑 acesso ao Espelho para conferir os apelidos · 🤖 escrever as regras que a URA diz ao segurado | 16 |
| allianz | residencial | desentupimento | **65/106** | parcial(106) | a ROTA foi percorrida ate o fim (+12) · o freio casa >=1 tela REAL (+8) · o cliente recebe protocolo + dia + periodo (+5) · transcrita no bloco do subservico (+4) | 🤖 transcrever a sessão no bloco · 🤖 client_summary com dia + período · 🤖 ampliar handoff_triggers contra o corpus · 🧑 acesso ao Espelho para conferir os apelidos · 🤖 escrever as regras que a URA diz ao segurado | 1 |
| porto | residencial | eletrodomesticos | **56/94** | parcial(94) | o freio casa >=1 tela REAL (+8) · teste nomeia a rota, chama o motor, toca >=3 telas (+6) · o cliente recebe protocolo + dia + periodo (+5) · transcrita no bloco do subservico (+4) | 🤖 transcrever a sessão no bloco · 🧑 coleta: +1 sessão desta rota · 🤖 client_summary com dia + período · 🧑 acesso ao Espelho para conferir os apelidos · 🤖 escrever as regras que a URA diz ao segurado | 0 |
| tokio | auto | guincho | **56/94** | parcial(94) | o freio casa >=1 tela REAL (+8) · teste nomeia a rota, chama o motor, toca >=3 telas (+6) · o cliente recebe protocolo + dia + periodo (+5) · transcrita no bloco do subservico (+4) | 🤖 transcrever a sessão no bloco · 🤖 client_summary com dia + período · 🤖 ampliar handoff_triggers contra o corpus · 🧑 acesso ao Espelho para conferir os apelidos · 🤖 escrever as regras que a URA diz ao segurado | 72 |
| hdi | auto | guincho | **61/106** | parcial(106) | zero orfas funcionais (+20) · toda tecla _opcao tem origem (3 fontes) (+6) · transcrita no bloco do subservico (+4) · apelidos do jeito que o cliente fala (+4) | 🤖 transcrever a sessão no bloco · 🤖 mapear 5 tela(s) · 🤖 recontar as notes · 🤖 dar origem às teclas órfãs · 🧑 acesso ao Espelho para conferir os apelidos · 🤖 escrever as regras que a URA diz ao segurado | 72 |
| yelum | auto | guincho | **61/106** | parcial(106) | zero orfas funcionais (+20) · toda tecla _opcao tem origem (3 fontes) (+6) · transcrita no bloco do subservico (+4) · apelidos do jeito que o cliente fala (+4) | 🤖 transcrever a sessão no bloco · 🤖 mapear 9 tela(s) · 🤖 recontar as notes · 🤖 dar origem às teclas órfãs · 🧑 acesso ao Espelho para conferir os apelidos · 🤖 escrever as regras que a URA diz ao segurado | 72 |
| hdi | auto | chaveiro | **58/106** | esqueleto(106) | a ROTA foi percorrida ate o fim (+12) · zero orfas funcionais (+10) · o cliente recebe protocolo + dia + periodo (+5) · transcrita no bloco do subservico (+4) | 🤖 transcrever a sessão no bloco · 🧑 coleta: +1 sessão desta rota · 🤖 mapear 1 tela(s) · 🤖 client_summary com dia + período · 🤖 recontar as notes · 🧑 acesso ao Espelho para conferir os apelidos · 🤖 escrever as regras que a URA diz ao segurado | 5 |
| porto | residencial | chaveiro | **57/106** | esqueleto(106) | a ROTA foi percorrida ate o fim (+12) · o freio casa >=1 tela REAL (+8) · toda tecla _opcao tem origem (3 fontes) (+6) · o cliente recebe protocolo + dia + periodo (+5) | 🤖 transcrever a sessão no bloco · 🧑 coleta: +1 sessão desta rota · 🤖 client_summary com dia + período · 🤖 dar origem às teclas órfãs · 🧑 acesso ao Espelho para conferir os apelidos · 🤖 escrever as regras que a URA diz ao segurado | 5 |
| zurich | auto | guincho | **49/94** | esqueleto(94) | zero orfas funcionais (+16) · toda tecla _opcao tem origem (3 fontes) (+6) · teste nomeia a rota, chama o motor, toca >=3 telas (+6) · transcrita no bloco do subservico (+4) | 🤖 transcrever a sessão no bloco · 🧑 coleta: +1 sessão desta rota · 🤖 mapear 2 tela(s) · 🤖 recontar as notes · 🤖 dar origem às teclas órfãs · 🧑 acesso ao Espelho para conferir os apelidos · 🤖 escrever as regras que a URA diz ao segurado | 72 |
| porto | auto | guincho | **54/106** | esqueleto(106) | zero orfas funcionais (+20) · a ROTA foi percorrida ate o fim (+12) · o cliente recebe protocolo + dia + periodo (+5) · transcrita no bloco do subservico (+4) | 🤖 transcrever a sessão no bloco · 🤖 mapear 5 tela(s) · 🤖 client_summary com dia + período · 🤖 recontar as notes · 🧑 acesso ao Espelho para conferir os apelidos · 🤖 escrever as regras que a URA diz ao segurado | 72 |
| hdi | residencial | chaveiro | **51/106** | esqueleto(106) | a ROTA foi percorrida ate o fim (+12) · zero orfas funcionais (+10) · o freio casa >=1 tela REAL (+8) · o cliente recebe protocolo + dia + periodo (+5) | 🤖 transcrever a sessão no bloco · 🧑 coleta: +1 sessão desta rota · 🤖 mapear 1 tela(s) · 🤖 client_summary com dia + período · 🤖 recontar as notes · 🧑 acesso ao Espelho para conferir os apelidos · 🤖 escrever as regras que a URA diz ao segurado | 5 |
| porto | auto | tecnico | **46/96** | esqueleto(96) | zero orfas funcionais (+20) · a ROTA foi percorrida ate o fim (+12) · teste nomeia a rota, chama o motor, toca >=3 telas (+6) · o cliente recebe protocolo + dia + periodo (+5) | 🤖 mapear 4 tela(s) · 🤖 client_summary com dia + período · 🤖 recontar as notes · 🧑 acesso ao Espelho para conferir os apelidos | 3 |
| hdi | residencial | encanador | **50/106** | esqueleto(106) | zero orfas funcionais (+20) · a ROTA foi percorrida ate o fim (+12) · o cliente recebe protocolo + dia + periodo (+5) · transcrita no bloco do subservico (+4) | 🤖 transcrever a sessão no bloco · 🤖 mapear 5 tela(s) · 🤖 subir o determinismo acima de 85% · 🤖 client_summary com dia + período · 🤖 recontar as notes · 🤖 ampliar handoff_triggers contra o corpus · 🤖 escrever as regras que a URA diz ao segurado | 14 |
| porto | auto | chaveiro | **50/106** | esqueleto(106) | zero orfas funcionais (+16) · a ROTA foi percorrida ate o fim (+12) · teste nomeia a rota, chama o motor, toca >=3 telas (+6) · o cliente recebe protocolo + dia + periodo (+5) | 🤖 transcrever a sessão no bloco · 🧑 coleta: +1 sessão desta rota · 🤖 mapear 2 tela(s) · 🤖 client_summary com dia + período · 🤖 recontar as notes · 🧑 acesso ao Espelho para conferir os apelidos · 🤖 escrever as regras que a URA diz ao segurado | 5 |
| hdi | residencial | eletricista | **45/106** | esqueleto(106) | zero orfas funcionais (+20) · a ROTA foi percorrida ate o fim (+12) · o freio casa >=1 tela REAL (+8) · o cliente recebe protocolo + dia + periodo (+5) | 🤖 transcrever a sessão no bloco · 🤖 mapear 4 tela(s) · 🤖 client_summary com dia + período · 🤖 recontar as notes · 🧑 acesso ao Espelho para conferir os apelidos · 🤖 escrever as regras que a URA diz ao segurado | 12 |
| porto | auto | bateria | **45/106** | esqueleto(106) | zero orfas funcionais (+20) · a ROTA foi percorrida ate o fim (+12) · teste nomeia a rota, chama o motor, toca >=3 telas (+6) · o cliente recebe protocolo + dia + periodo (+5) | 🤖 transcrever a sessão no bloco · 🤖 mapear 6 tela(s) · 🤖 client_summary com dia + período · 🤖 recontar as notes · 🧑 acesso ao Espelho para conferir os apelidos · 🤖 escrever as regras que a URA diz ao segurado | 16 |
| azul | auto | bateria | **44/106** | esqueleto(106) | zero orfas funcionais (+20) · a ROTA foi percorrida ate o fim (+12) · teste nomeia a rota, chama o motor, toca >=3 telas (+6) · o cliente recebe protocolo + dia + periodo (+5) | 🤖 transcrever a sessão no bloco · 🤖 mapear 10 tela(s) · 🤖 subir o determinismo acima de 85% · 🤖 client_summary com dia + período · 🤖 recontar as notes · 🧑 acesso ao Espelho para conferir os apelidos · 🤖 escrever as regras que a URA diz ao segurado | 16 |
| azul | auto | guincho | **44/106** | esqueleto(106) | zero orfas funcionais (+20) · a ROTA foi percorrida ate o fim (+12) · teste nomeia a rota, chama o motor, toca >=3 telas (+6) · o cliente recebe protocolo + dia + periodo (+5) | 🤖 transcrever a sessão no bloco · 🤖 mapear 21 tela(s) · 🤖 subir o determinismo acima de 85% · 🤖 client_summary com dia + período · 🤖 recontar as notes · 🧑 acesso ao Espelho para conferir os apelidos · 🤖 escrever as regras que a URA diz ao segurado | 72 |
| yelum | residencial | eletrodomesticos | **43/106** | esqueleto(106) | zero orfas funcionais (+16) · a ROTA foi percorrida ate o fim (+12) · o freio casa >=1 tela REAL (+8) · o cliente recebe protocolo + dia + periodo (+5) | 🤖 transcrever a sessão no bloco · 🧑 coleta: +1 sessão desta rota · 🤖 mapear 2 tela(s) · 🤖 subir o determinismo acima de 85% · 🤖 client_summary com dia + período · 🤖 recontar as notes · 🧑 acesso ao Espelho para conferir os apelidos · 🤖 escrever as regras que a URA diz ao segurado | 0 |
| yelum | auto | bateria | **42/106** | esqueleto(106) | zero orfas funcionais (+16) · a ROTA foi percorrida ate o fim (+12) · o freio casa >=1 tela REAL (+8) · o cliente recebe protocolo + dia + periodo (+5) | 🤖 transcrever a sessão no bloco · 🧑 coleta: +1 sessão desta rota · 🤖 mapear 2 tela(s) · 🤖 client_summary com dia + período · 🤖 recontar as notes · 🧑 acesso ao Espelho para conferir os apelidos · 🤖 escrever as regras que a URA diz ao segurado | 16 |
| azul | auto | tecnico | **37/96** | esqueleto(96) | zero orfas funcionais (+20) · a ROTA foi percorrida ate o fim (+12) · teste nomeia a rota, chama o motor, toca >=3 telas (+6) · o cliente recebe protocolo + dia + periodo (+5) | 🧑 coleta: +1 sessão desta rota · 🤖 mapear 4 tela(s) · 🤖 subir o determinismo acima de 85% · 🤖 client_summary com dia + período · 🤖 recontar as notes · 🧑 acesso ao Espelho para conferir os apelidos | 3 |
| porto | residencial | encanador | **37/106** | esqueleto(106) | zero orfas funcionais (+20) · a ROTA foi percorrida ate o fim (+12) · o freio casa >=1 tela REAL (+8) · toda tecla _opcao tem origem (3 fontes) (+6) | 🤖 transcrever a sessão no bloco · 🤖 mapear 3 tela(s) · 🤖 client_summary com dia + período · 🤖 dar origem às teclas órfãs · 🤖 escrever as regras que a URA diz ao segurado | 14 |
| alfa | auto | bateria | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 16 |
| alfa | auto | chaveiro | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 5 |
| allianz | auto | chaveiro | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 5 |
| azul | auto | chaveiro | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 5 |
| azul | auto | pneu | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 10 |
| bradesco | auto | bateria | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 16 |
| bradesco | auto | chaveiro | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 5 |
| bradesco | auto | guincho | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 72 |
| bradesco | auto | pneu | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 10 |
| hdi | auto | bateria | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 16 |
| hdi | residencial | desentupimento | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 1 |
| hdi | residencial | eletrodomesticos | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 0 |
| mapfre | auto | bateria | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 16 |
| mapfre | auto | chaveiro | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 5 |
| mapfre | auto | guincho | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 72 |
| mapfre | auto | pneu | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 10 |
| porto | auto | bateria_nova | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 0 |
| porto | auto | pneu | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 10 |
| porto | auto | taxi | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 1 |
| porto | residencial | desentupimento | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 1 |
| porto | residencial | eletricista | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 12 |
| tokio | auto | bateria | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 16 |
| tokio | auto | chaveiro | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 5 |
| tokio | auto | pneu | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 10 |
| yelum | auto | chaveiro | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 5 |
| yelum | residencial | chaveiro | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 5 |
| yelum | residencial | desentupimento | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 1 |
| zurich | auto | bateria | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 16 |
| zurich | auto | chaveiro | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 5 |
| zurich | auto | pneu | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 10 |
| zurich | auto | socorro_mecanico | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 7 |
| zurich | auto | vidros | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 0 |

## Os eixos, para quem quiser a decomposição

| seguradora | ramo | serviço | A | B | C | D | E | família |
|---|---|---|---:|---:|---:|---:|---:|---|
| allianz | residencial | encanador | 20 | 35 | 26 | 10 | 15 | — |
| allianz | residencial | maquina_de_lavar | 20 | 35 | 26 | 10 | 15 | — |
| allianz | residencial | chaveiro | 20 | 35 | 26 | 6 | 15 | — |
| allianz | residencial | eletricista | 20 | 35 | 26 | 6 | 15 | — |
| allianz | residencial | ar_condicionado | 20 | 35 | 23 | 6 | 15 | — |
| alfa | auto | guincho | 16 | 33 | 26 | 0 | 15 | — |
| alfa | auto | pneu | 14 | 33 | 26 | 0 | 15 | — |
| yelum | auto | pneu | 16 | 33 | 26 | 0 | 12 | — |
| hdi | auto | socorro_mecanico | 2 | 23 | 26 | 4 | 12 | — |
| hdi | auto | pneu | 12 | 33 | 26 | 0 | 12 | — |
| allianz | residencial | limpeza_caixa_dagua | 16 | 19 | 23 | 0 | 15 | — |
| yelum | auto | socorro_mecanico | 4 | 13 | 26 | 4 | 12 | — |
| allianz | auto | pneu | 16 | 17 | 26 | 0 | 15 | — |
| allianz | residencial | consulta_veterinaria | 14 | 11 | 26 | 0 | 15 | — |
| porto | auto | vidros | 0 | 29 | 18 | 4 | 15 | — |
| allianz | auto | guincho | 16 | 13 | 26 | 0 | 15 | — |
| allianz | residencial | eletrodomesticos | 4 | 30 | 18 | 3 | 15 | — |
| yelum | residencial | eletricista | 14 | 17 | 23 | 0 | 15 | — |
| yelum | residencial | encanador | 16 | 9 | 23 | 4 | 15 | — |
| allianz | auto | bateria | 16 | 9 | 26 | 0 | 15 | — |
| allianz | residencial | desentupimento | 2 | 30 | 15 | 3 | 15 | — |
| porto | residencial | eletrodomesticos | 2 | 30 | 18 | 0 | 6 | — |
| tokio | auto | guincho | 2 | 30 | 15 | 0 | 9 | — |
| hdi | auto | guincho | 16 | 13 | 20 | 0 | 12 | — |
| yelum | auto | guincho | 16 | 13 | 20 | 0 | 12 | — |
| hdi | auto | chaveiro | 2 | 18 | 26 | 0 | 12 | — |
| porto | residencial | chaveiro | 0 | 30 | 12 | 0 | 15 | — |
| zurich | auto | guincho | 2 | 18 | 20 | 0 | 9 | — |
| porto | auto | guincho | 4 | 9 | 26 | 0 | 15 | — |
| hdi | residencial | chaveiro | 0 | 18 | 18 | 0 | 15 | — |
| porto | auto | tecnico | 2 | 9 | 26 | 0 | 9 | — |
| hdi | residencial | encanador | 4 | 4 | 23 | 4 | 15 | — |
| porto | auto | chaveiro | 2 | 13 | 26 | 0 | 9 | — |
| hdi | residencial | eletricista | 4 | 8 | 18 | 0 | 15 | — |
| porto | auto | bateria | 4 | 9 | 26 | 0 | 6 | — |
| azul | auto | bateria | 4 | 5 | 26 | 0 | 9 | — |
| azul | auto | guincho | 4 | 5 | 26 | 0 | 9 | — |
| yelum | residencial | eletrodomesticos | 2 | 8 | 18 | 0 | 15 | — |
| yelum | auto | bateria | 0 | 12 | 18 | 0 | 12 | — |
| azul | auto | tecnico | 0 | 5 | 26 | 0 | 6 | — |
| porto | residencial | encanador | 2 | 10 | 12 | 4 | 9 | — |
| alfa | auto | bateria | — | — | — | — | — | — |
| alfa | auto | chaveiro | — | — | — | — | — | — |
| allianz | auto | chaveiro | — | — | — | — | — | — |
| azul | auto | chaveiro | — | — | — | — | — | — |
| azul | auto | pneu | — | — | — | — | — | — |
| bradesco | auto | bateria | — | — | — | — | — | — |
| bradesco | auto | chaveiro | — | — | — | — | — | — |
| bradesco | auto | guincho | — | — | — | — | — | — |
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
