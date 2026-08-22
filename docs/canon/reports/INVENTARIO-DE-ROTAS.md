# Inventário de rotas — a régua aplicada às 62

> Gerado em **2026-08-22T01:16:58+00:00** · commit `4fca114`
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
| alfa | auto | guincho | **59/96** | parcial(96) | zero orfas funcionais (+20) · o cliente recebe protocolo + dia + periodo (+5) · transcrita no bloco do subservico (+4) · expectativa_do_desfecho existe (+3) | 🤖 transcrever a sessão no bloco · 🤖 mapear 9 tela(s) · 🤖 client_summary com dia + período · 🤖 recontar as notes · 🤖 escrever as regras que a URA diz ao segurado | 72 |
| allianz | residencial | maquina_de_lavar | **56/96** | parcial(96) | zero orfas funcionais (+20) · toda tecla _opcao tem origem (3 fontes) (+6) · o cliente recebe protocolo + dia + periodo (+5) · >=85% deterministico (+4) | 🤖 mapear 15 tela(s) · 🤖 subir o determinismo acima de 85% · 🤖 client_summary com dia + período · 🤖 recontar as notes · 🤖 dar origem às teclas órfãs · 🤖 ampliar handoff_triggers contra o corpus | 0 |
| allianz | auto | guincho | **55/96** | parcial(96) | zero orfas funcionais (+20) · o cliente recebe protocolo + dia + periodo (+5) · transcrita no bloco do subservico (+4) · >=85% deterministico (+4) | 🤖 transcrever a sessão no bloco · 🤖 mapear 22 tela(s) · 🤖 subir o determinismo acima de 85% · 🤖 client_summary com dia + período · 🤖 recontar as notes · 🤖 escrever as regras que a URA diz ao segurado | 72 |
| allianz | auto | pneu | **55/96** | parcial(96) | zero orfas funcionais (+20) · o cliente recebe protocolo + dia + periodo (+5) · transcrita no bloco do subservico (+4) · >=85% deterministico (+4) | 🤖 transcrever a sessão no bloco · 🤖 mapear 18 tela(s) · 🤖 subir o determinismo acima de 85% · 🤖 client_summary com dia + período · 🤖 recontar as notes · 🤖 escrever as regras que a URA diz ao segurado | 10 |
| allianz | residencial | chaveiro | **52/96** | esqueleto(96) | zero orfas funcionais (+20) · toda tecla _opcao tem origem (3 fontes) (+6) · o cliente recebe protocolo + dia + periodo (+5) · transcrita no bloco do subservico (+4) | 🤖 transcrever a sessão no bloco · 🤖 mapear 8 tela(s) · 🤖 subir o determinismo acima de 85% · 🤖 client_summary com dia + período · 🤖 recontar as notes · 🤖 dar origem às teclas órfãs · 🤖 ampliar handoff_triggers contra o corpus | 5 |
| allianz | residencial | eletricista | **52/96** | esqueleto(96) | zero orfas funcionais (+20) · toda tecla _opcao tem origem (3 fontes) (+6) · o cliente recebe protocolo + dia + periodo (+5) · transcrita no bloco do subservico (+4) | 🤖 transcrever a sessão no bloco · 🤖 mapear 10 tela(s) · 🤖 subir o determinismo acima de 85% · 🤖 client_summary com dia + período · 🤖 recontar as notes · 🤖 dar origem às teclas órfãs · 🤖 ampliar handoff_triggers contra o corpus | 12 |
| yelum | residencial | eletricista | **50/96** | esqueleto(96) | zero orfas funcionais (+20) · o cliente recebe protocolo + dia + periodo (+5) · transcrita no bloco do subservico (+4) · >=85% deterministico (+4) | 🤖 transcrever a sessão no bloco · 🤖 mapear 10 tela(s) · 🤖 subir o determinismo acima de 85% · 🤖 client_summary com dia + período · 🤖 recontar as notes · 🤖 ampliar handoff_triggers contra o corpus · 🤖 escrever as regras que a URA diz ao segurado | 12 |
| hdi | auto | pneu | **48/96** | esqueleto(96) | zero orfas funcionais (+20) · o cliente recebe protocolo + dia + periodo (+5) · transcrita no bloco do subservico (+4) · >=85% deterministico (+4) | 🤖 transcrever a sessão no bloco · 🧑 coleta: +1 sessão desta rota · 🤖 mapear 7 tela(s) · 🤖 subir o determinismo acima de 85% · 🤖 client_summary com dia + período · 🤖 recontar as notes · 🤖 escrever as regras que a URA diz ao segurado | 10 |
| allianz | residencial | eletrodomesticos | **46/96** | esqueleto(96) | a ROTA foi percorrida ate o fim (+12) · zero orfas funcionais (+10) · o freio casa >=1 tela REAL (+8) · toda tecla _opcao tem origem (3 fontes) (+6) | 🤖 transcrever a sessão no bloco · 🤖 mapear 1 tela(s) · 🤖 client_summary com dia + período · 🤖 recontar as notes · 🤖 dar origem às teclas órfãs · 🤖 ampliar handoff_triggers contra o corpus | 0 |
| allianz | residencial | desentupimento | **44/96** | esqueleto(96) | a ROTA foi percorrida ate o fim (+12) · zero orfas funcionais (+10) · o freio casa >=1 tela REAL (+8) · toda tecla _opcao tem origem (3 fontes) (+6) | 🤖 transcrever a sessão no bloco · 🤖 mapear 1 tela(s) · 🤖 client_summary com dia + período · 🤖 recontar as notes · 🤖 dar origem às teclas órfãs · 🤖 ampliar handoff_triggers contra o corpus | 1 |
| yelum | residencial | eletrodomesticos | **33/96** | esqueleto(96) | zero orfas funcionais (+20) · a ROTA foi percorrida ate o fim (+12) · o freio casa >=1 tela REAL (+8) · o cliente recebe protocolo + dia + periodo (+5) | 🤖 transcrever a sessão no bloco · 🧑 coleta: +1 sessão desta rota · 🤖 mapear 3 tela(s) · 🤖 subir o determinismo acima de 85% · 🤖 client_summary com dia + período · 🤖 recontar as notes · 🤖 escrever as regras que a URA diz ao segurado | 0 |
| yelum | auto | bateria | **30/96** | esqueleto(96) | zero orfas funcionais (+20) · a ROTA foi percorrida ate o fim (+12) · o freio casa >=1 tela REAL (+8) · o cliente recebe protocolo + dia + periodo (+5) | 🤖 transcrever a sessão no bloco · 🧑 coleta: +1 sessão desta rota · 🤖 mapear 3 tela(s) · 🤖 subir o determinismo acima de 85% · 🤖 client_summary com dia + período · 🤖 recontar as notes · 🤖 escrever as regras que a URA diz ao segurado | 16 |
| alfa | auto | bateria | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 16 |
| alfa | auto | chaveiro | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 5 |
| alfa | auto | pneu | **NAO_RESPONDE** | NAO_RESPONDE | o corredor não fala esta URA: 5 órfãs funcionais e determinismo 69% | 🤖 escrever passos para 5 tela(s) órfã(s) em 1 sessão(ões) | 10 |
| allianz | auto | bateria | **NAO_RESPONDE** | NAO_RESPONDE | o corredor não fala esta URA: 9 órfãs funcionais e determinismo 69% | 🤖 escrever passos para 9 tela(s) órfã(s) em 2 sessão(ões) | 16 |
| allianz | auto | chaveiro | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 5 |
| allianz | residencial | encanador | **NAO_RESPONDE** | NAO_RESPONDE | o corredor não fala esta URA: 29 órfãs funcionais e determinismo 65% | 🤖 escrever passos para 29 tela(s) órfã(s) em 5 sessão(ões) | 14 |
| azul | auto | bateria | **NAO_RESPONDE** | NAO_RESPONDE | o corredor não fala esta URA: 33 órfãs funcionais e determinismo 41% | 🤖 escrever passos para 33 tela(s) órfã(s) em 3 sessão(ões) | 16 |
| azul | auto | chaveiro | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 5 |
| azul | auto | guincho | **NAO_RESPONDE** | NAO_RESPONDE | o corredor não fala esta URA: 88 órfãs funcionais e determinismo 30% | 🤖 escrever passos para 88 tela(s) órfã(s) em 5 sessão(ões) | 72 |
| azul | auto | pneu | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 10 |
| azul | auto | vidros | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 0 |
| bradesco | auto | bateria | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 16 |
| bradesco | auto | chaveiro | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 5 |
| bradesco | auto | guincho | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 72 |
| bradesco | auto | pneu | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 10 |
| hdi | auto | bateria | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 16 |
| hdi | auto | chaveiro | **NAO_RESPONDE** | NAO_RESPONDE | o corredor não fala esta URA: 6 órfãs funcionais e determinismo 65% | 🤖 escrever passos para 6 tela(s) órfã(s) em 1 sessão(ões) | 5 |
| hdi | auto | guincho | **NAO_RESPONDE** | NAO_RESPONDE | o corredor não fala esta URA: 47 órfãs funcionais e determinismo 68% | 🤖 escrever passos para 47 tela(s) órfã(s) em 5 sessão(ões) | 72 |
| hdi | residencial | chaveiro | **NAO_RESPONDE** | NAO_RESPONDE | o corredor não fala esta URA: 17 órfãs funcionais e determinismo 6% | 🤖 escrever passos para 17 tela(s) órfã(s) em 1 sessão(ões) | 5 |
| hdi | residencial | desentupimento | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 1 |
| hdi | residencial | eletricista | **NAO_RESPONDE** | NAO_RESPONDE | o corredor não fala esta URA: 69 órfãs funcionais e determinismo 7% | 🤖 escrever passos para 69 tela(s) órfã(s) em 5 sessão(ões) | 12 |
| hdi | residencial | eletrodomesticos | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 0 |
| hdi | residencial | encanador | **NAO_RESPONDE** | NAO_RESPONDE | o corredor não fala esta URA: 19 órfãs funcionais e determinismo 14% | 🤖 escrever passos para 19 tela(s) órfã(s) em 2 sessão(ões) | 14 |
| mapfre | auto | bateria | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 16 |
| mapfre | auto | chaveiro | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 5 |
| mapfre | auto | guincho | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 72 |
| mapfre | auto | pneu | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 10 |
| porto | auto | bateria | **NAO_RESPONDE** | NAO_RESPONDE | o corredor não fala esta URA: 46 órfãs funcionais e determinismo 52% | 🤖 escrever passos para 46 tela(s) órfã(s) em 4 sessão(ões) | 16 |
| porto | auto | chaveiro | **NAO_RESPONDE** | NAO_RESPONDE | o corredor não fala esta URA: 10 órfãs funcionais e determinismo 52% | 🤖 escrever passos para 10 tela(s) órfã(s) em 1 sessão(ões) | 5 |
| porto | auto | guincho | **NAO_RESPONDE** | NAO_RESPONDE | o corredor não fala esta URA: 47 órfãs funcionais e determinismo 62% | 🤖 escrever passos para 47 tela(s) órfã(s) em 5 sessão(ões) | 72 |
| porto | auto | pneu | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 10 |
| porto | auto | vidros | **NAO_RESPONDE** | NAO_RESPONDE | o corredor não fala esta URA: 9 órfãs funcionais e determinismo 31% | 🤖 escrever passos para 9 tela(s) órfã(s) em 1 sessão(ões) | 0 |
| porto | residencial | eletricista | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 12 |
| porto | residencial | eletrodomesticos | **NAO_RESPONDE** | NAO_RESPONDE | o corredor não fala esta URA: 12 órfãs funcionais e determinismo 14% | 🤖 escrever passos para 12 tela(s) órfã(s) em 1 sessão(ões) | 0 |
| porto | residencial | encanador | **NAO_RESPONDE** | NAO_RESPONDE | o corredor não fala esta URA: 69 órfãs funcionais e determinismo 9% | 🤖 escrever passos para 69 tela(s) órfã(s) em 3 sessão(ões) | 14 |
| tokio | auto | bateria | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 16 |
| tokio | auto | chaveiro | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 5 |
| tokio | auto | guincho | **NAO_RESPONDE** | NAO_RESPONDE | o corredor não fala esta URA: 12 órfãs funcionais e determinismo 0% | 🤖 escrever passos para 12 tela(s) órfã(s) em 3 sessão(ões) | 72 |
| tokio | auto | pneu | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 10 |
| yelum | auto | chaveiro | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 5 |
| yelum | auto | guincho | **NAO_RESPONDE** | NAO_RESPONDE | o corredor não fala esta URA: 56 órfãs funcionais e determinismo 56% | 🤖 escrever passos para 56 tela(s) órfã(s) em 5 sessão(ões) | 72 |
| yelum | auto | pneu | **NAO_RESPONDE** | NAO_RESPONDE | o corredor não fala esta URA: 16 órfãs funcionais e determinismo 70% | 🤖 escrever passos para 16 tela(s) órfã(s) em 2 sessão(ões) | 10 |
| yelum | residencial | chaveiro | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 5 |
| yelum | residencial | desentupimento | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 1 |
| yelum | residencial | encanador | **NAO_RESPONDE** | NAO_RESPONDE | o corredor não fala esta URA: 19 órfãs funcionais e determinismo 62% | 🤖 escrever passos para 19 tela(s) órfã(s) em 5 sessão(ões) | 14 |
| zurich | auto | bateria | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 16 |
| zurich | auto | chaveiro | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 5 |
| zurich | auto | guincho | **NAO_RESPONDE** | NAO_RESPONDE | o corredor não fala esta URA: 12 órfãs funcionais e determinismo 54% | 🤖 escrever passos para 12 tela(s) órfã(s) em 1 sessão(ões) | 72 |
| zurich | auto | pneu | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 10 |
| zurich | auto | vidros | **SEM_CORPUS** | SEM_CORPUS | não há uma linha desta rota no corpus | 🧑 coleta dirigida: 1 acionamento observado desta rota | 0 |

## Os eixos, para quem quiser a decomposição

| seguradora | ramo | serviço | A | B | C | D | E | família |
|---|---|---|---:|---:|---:|---:|---:|---|
| alfa | auto | guincho | 16 | 8 | 20 | 0 | 15 | — |
| allianz | residencial | maquina_de_lavar | 20 | 4 | 11 | 6 | 15 | — |
| allianz | auto | guincho | 16 | 4 | 20 | 0 | 15 | — |
| allianz | auto | pneu | 16 | 4 | 20 | 0 | 15 | — |
| allianz | residencial | chaveiro | 16 | 4 | 11 | 6 | 15 | — |
| allianz | residencial | eletricista | 16 | 4 | 11 | 6 | 15 | — |
| yelum | residencial | eletricista | 14 | 4 | 17 | 0 | 15 | — |
| hdi | auto | pneu | 12 | 4 | 20 | 0 | 12 | — |
| allianz | residencial | eletrodomesticos | 4 | 18 | 3 | 6 | 15 | — |
| allianz | residencial | desentupimento | 2 | 18 | 3 | 6 | 15 | — |
| yelum | residencial | eletrodomesticos | 2 | 4 | 12 | 0 | 15 | — |
| yelum | auto | bateria | 2 | 4 | 12 | 0 | 12 | — |
| alfa | auto | bateria | — | — | — | — | — | — |
| alfa | auto | chaveiro | — | — | — | — | — | — |
| alfa | auto | pneu | — | 0 | — | — | — | — |
| allianz | auto | bateria | — | 0 | — | — | — | — |
| allianz | auto | chaveiro | — | — | — | — | — | — |
| allianz | residencial | encanador | — | 0 | — | — | — | — |
| azul | auto | bateria | — | 0 | — | — | — | — |
| azul | auto | chaveiro | — | — | — | — | — | — |
| azul | auto | guincho | — | 0 | — | — | — | — |
| azul | auto | pneu | — | — | — | — | — | — |
| azul | auto | vidros | — | — | — | — | — | — |
| bradesco | auto | bateria | — | — | — | — | — | — |
| bradesco | auto | chaveiro | — | — | — | — | — | — |
| bradesco | auto | guincho | — | — | — | — | — | — |
| bradesco | auto | pneu | — | — | — | — | — | — |
| hdi | auto | bateria | — | — | — | — | — | — |
| hdi | auto | chaveiro | — | 0 | — | — | — | — |
| hdi | auto | guincho | — | 0 | — | — | — | — |
| hdi | residencial | chaveiro | — | 0 | — | — | — | — |
| hdi | residencial | desentupimento | — | — | — | — | — | — |
| hdi | residencial | eletricista | — | 0 | — | — | — | — |
| hdi | residencial | eletrodomesticos | — | — | — | — | — | — |
| hdi | residencial | encanador | — | 0 | — | — | — | — |
| mapfre | auto | bateria | — | — | — | — | — | — |
| mapfre | auto | chaveiro | — | — | — | — | — | — |
| mapfre | auto | guincho | — | — | — | — | — | — |
| mapfre | auto | pneu | — | — | — | — | — | — |
| porto | auto | bateria | — | 0 | — | — | — | — |
| porto | auto | chaveiro | — | 0 | — | — | — | — |
| porto | auto | guincho | — | 0 | — | — | — | — |
| porto | auto | pneu | — | — | — | — | — | — |
| porto | auto | vidros | — | 0 | — | — | — | — |
| porto | residencial | eletricista | — | — | — | — | — | — |
| porto | residencial | eletrodomesticos | — | 0 | — | — | — | — |
| porto | residencial | encanador | — | 0 | — | — | — | — |
| tokio | auto | bateria | — | — | — | — | — | — |
| tokio | auto | chaveiro | — | — | — | — | — | — |
| tokio | auto | guincho | — | 0 | — | — | — | — |
| tokio | auto | pneu | — | — | — | — | — | — |
| yelum | auto | chaveiro | — | — | — | — | — | — |
| yelum | auto | guincho | — | 0 | — | — | — | — |
| yelum | auto | pneu | — | 0 | — | — | — | — |
| yelum | residencial | chaveiro | — | — | — | — | — | — |
| yelum | residencial | desentupimento | — | — | — | — | — | — |
| yelum | residencial | encanador | — | 0 | — | — | — | — |
| zurich | auto | bateria | — | — | — | — | — | — |
| zurich | auto | chaveiro | — | — | — | — | — | — |
| zurich | auto | guincho | — | 0 | — | — | — | — |
| zurich | auto | pneu | — | — | — | — | — | — |
| zurich | auto | vidros | — | — | — | — | — | — |
