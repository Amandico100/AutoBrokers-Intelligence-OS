# A simulação dos corredores — a lista por rota

> gerado em 2026-09-30T03:22:05+00:00 · commit `4ccd063` · corpus `backend/tests/corpus/telas_reais/`

🔴 **Offline por construção:** corpus versionado + motor do produto. Nenhum modelo foi chamado, nenhum `observed_events` foi lido.

Cada rota foi atravessada com as **telas reais** do acervo, tela a tela, e cada passo respondeu às duas perguntas do `CLAUDE.md` §9.5: *o passo casou a tela?* **e** *a resposta está confirmada?*

| faixa | rotas | o que significa |
|---|---:|---|
| **ATENDE SOZINHO** | 31 | o robô responde tudo o que o acervo mostra, sem decidir pelo segurado, e já chegou ao protocolo pelo menos uma vez |
| **HANDOFF** | 4 | vai a uma pessoa — por desenho (a seguradora só dá link) ou porque ainda responde algo errado |
| **FALTA CAPTURA** | 41 | falta conversa: ou o acervo não tem nenhuma, ou tem uma tela sem resposta escrita, ou nenhuma chegou ao fim |

## ATENDE SOZINHO — 31 rota(s)

| rota | telas | respondidas | órfãs | A | B | C | chegou ao fim | por quê |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| `alfa/auto/guincho` | 86 | 61 | 0 | 0 | 0 | 0 | sim | todas as 61 telas que pedem algo são respondidas, nenhuma resposta decide pelo segurado sem evidência, e a seguradora devolveu protocolo/agendamento em 2 conversa(s) — a primeira é `665b5bad` |
| `alfa/auto/pneu` | 23 | 16 | 0 | 0 | 0 | 0 | sim | todas as 16 telas que pedem algo são respondidas, nenhuma resposta decide pelo segurado sem evidência, e a seguradora devolveu protocolo/agendamento em 1 conversa(s) — a primeira é `1b13140b` |
| `allianz/auto/bateria` | 105 | 64 | 0 | 0 | 0 | 0 | sim | todas as 64 telas que pedem algo são respondidas, nenhuma resposta decide pelo segurado sem evidência, e a seguradora devolveu protocolo/agendamento em 3 conversa(s) — a primeira é `46e8e180` |
| `allianz/auto/guincho` | 350 | 242 | 0 | 0 | 0 | 0 | sim | todas as 242 telas que pedem algo são respondidas, nenhuma resposta decide pelo segurado sem evidência, e a seguradora devolveu protocolo/agendamento em 10 conversa(s) — a primeira é `061c2960` |
| `allianz/auto/pneu` | 85 | 59 | 0 | 0 | 0 | 0 | sim | todas as 59 telas que pedem algo são respondidas, nenhuma resposta decide pelo segurado sem evidência, e a seguradora devolveu protocolo/agendamento em 3 conversa(s) — a primeira é `298e0c49` |
| `allianz/residencial/ar_condicionado` | 83 | 67 | 0 | 0 | 0 | 0 | sim | todas as 67 telas que pedem algo são respondidas, nenhuma resposta decide pelo segurado sem evidência, e a seguradora devolveu protocolo/agendamento em 1 conversa(s) — a primeira é `448c6aae` |
| `allianz/residencial/chaveiro` | 50 | 34 | 0 | 0 | 0 | 0 | sim | todas as 34 telas que pedem algo são respondidas, nenhuma resposta decide pelo segurado sem evidência, e a seguradora devolveu protocolo/agendamento em 1 conversa(s) — a primeira é `e70dfcaa` |
| `allianz/residencial/consulta_veterinaria` | 48 | 35 | 0 | 0 | 0 | 0 | sim | todas as 35 telas que pedem algo são respondidas, nenhuma resposta decide pelo segurado sem evidência, e a seguradora devolveu protocolo/agendamento em 1 conversa(s) — a primeira é `c58a171a` |
| `allianz/residencial/eletricista` | 51 | 36 | 0 | 0 | 0 | 0 | sim | todas as 36 telas que pedem algo são respondidas, nenhuma resposta decide pelo segurado sem evidência, e a seguradora devolveu protocolo/agendamento em 1 conversa(s) — a primeira é `acc3e885` |
| `allianz/residencial/encanador` | 147 | 96 | 0 | 0 | 0 | 0 | sim | todas as 96 telas que pedem algo são respondidas, nenhuma resposta decide pelo segurado sem evidência, e a seguradora devolveu protocolo/agendamento em 4 conversa(s) — a primeira é `0591c1d1` |
| `allianz/residencial/limpeza_caixa_dagua` | 92 | 72 | 0 | 0 | 0 | 0 | sim | todas as 72 telas que pedem algo são respondidas, nenhuma resposta decide pelo segurado sem evidência, e a seguradora devolveu protocolo/agendamento em 2 conversa(s) — a primeira é `382cbdb7` |
| `allianz/residencial/maquina_de_lavar` | 116 | 90 | 0 | 0 | 0 | 0 | sim | todas as 90 telas que pedem algo são respondidas, nenhuma resposta decide pelo segurado sem evidência, e a seguradora devolveu protocolo/agendamento em 3 conversa(s) — a primeira é `7ac3c101` |
| `azul/auto/bateria` | 90 | 47 | 0 | 0 | 0 | 0 | sim | todas as 47 telas que pedem algo são respondidas, nenhuma resposta decide pelo segurado sem evidência, e a seguradora devolveu protocolo/agendamento em 2 conversa(s) — a primeira é `0189f34b` |
| `azul/auto/guincho` | 259 | 132 | 0 | 0 | 0 | 0 | sim | todas as 132 telas que pedem algo são respondidas, nenhuma resposta decide pelo segurado sem evidência, e a seguradora devolveu protocolo/agendamento em 6 conversa(s) — a primeira é `14398ee8` |
| `azul/auto/tecnico` | 33 | 19 | 0 | 0 | 0 | 0 | sim | todas as 19 telas que pedem algo são respondidas, nenhuma resposta decide pelo segurado sem evidência, e a seguradora devolveu protocolo/agendamento em 1 conversa(s) — a primeira é `d70ced75` |
| `bradesco/auto/guincho` | 129 | 107 | 0 | 0 | 0 | 0 | sim | todas as 107 telas que pedem algo são respondidas, nenhuma resposta decide pelo segurado sem evidência, e a seguradora devolveu protocolo/agendamento em 3 conversa(s) — a primeira é `0d5284f3` |
| `hdi/auto/chaveiro` | 26 | 17 | 0 | 0 | 0 | 0 | sim | todas as 17 telas que pedem algo são respondidas, nenhuma resposta decide pelo segurado sem evidência, e a URA chegou à tela que CONFIRMA a abertura em 1 conversa(s) — a primeira é `697abd09` |
| `hdi/auto/guincho` | 637 | 380 | 0 | 0 | 0 | 0 | sim | todas as 380 telas que pedem algo são respondidas, nenhuma resposta decide pelo segurado sem evidência, e a seguradora devolveu protocolo/agendamento em 13 conversa(s) — a primeira é `21a53457` |
| `hdi/auto/pneu` | 44 | 27 | 0 | 0 | 0 | 0 | sim | todas as 27 telas que pedem algo são respondidas, nenhuma resposta decide pelo segurado sem evidência, e a seguradora devolveu protocolo/agendamento em 1 conversa(s) — a primeira é `886066e5` |
| `hdi/auto/socorro_mecanico` | 48 | 24 | 0 | 0 | 0 | 0 | sim | todas as 24 telas que pedem algo são respondidas, nenhuma resposta decide pelo segurado sem evidência, e a seguradora devolveu protocolo/agendamento em 1 conversa(s) — a primeira é `71caf82f` |
| `hdi/residencial/encanador` | 55 | 32 | 0 | 0 | 0 | 0 | sim | todas as 32 telas que pedem algo são respondidas, nenhuma resposta decide pelo segurado sem evidência, e a seguradora devolveu protocolo/agendamento em 1 conversa(s) — a primeira é `61b96027` |
| `porto/auto/chaveiro` | 34 | 17 | 0 | 0 | 0 | 0 | sim | todas as 17 telas que pedem algo são respondidas, nenhuma resposta decide pelo segurado sem evidência, e a seguradora devolveu protocolo/agendamento em 1 conversa(s) — a primeira é `d0d64bfc` |
| `porto/auto/guincho` | 519 | 259 | 0 | 0 | 0 | 0 | sim | todas as 259 telas que pedem algo são respondidas, nenhuma resposta decide pelo segurado sem evidência, e a seguradora devolveu protocolo/agendamento em 13 conversa(s) — a primeira é `12203ed9` |
| `porto/auto/tecnico` | 76 | 39 | 0 | 0 | 0 | 0 | sim | todas as 39 telas que pedem algo são respondidas, nenhuma resposta decide pelo segurado sem evidência, e a seguradora devolveu protocolo/agendamento em 2 conversa(s) — a primeira é `b1ff65f2` |
| `porto/residencial/chaveiro` | 37 | 21 | 0 | 0 | 0 | 0 | sim | todas as 21 telas que pedem algo são respondidas, nenhuma resposta decide pelo segurado sem evidência, e a seguradora devolveu protocolo/agendamento em 1 conversa(s) — a primeira é `565cb39a` |
| `porto/residencial/encanador` | 114 | 58 | 0 | 0 | 0 | 0 | sim | todas as 58 telas que pedem algo são respondidas, nenhuma resposta decide pelo segurado sem evidência, e a seguradora devolveu protocolo/agendamento em 3 conversa(s) — a primeira é `0fe42179` |
| `yelum/auto/bateria` | 201 | 116 | 0 | 0 | 0 | 0 | sim | todas as 116 telas que pedem algo são respondidas, nenhuma resposta decide pelo segurado sem evidência, e a seguradora devolveu protocolo/agendamento em 5 conversa(s) — a primeira é `86769bd5` |
| `yelum/auto/pneu` | 82 | 50 | 0 | 0 | 0 | 0 | sim | todas as 50 telas que pedem algo são respondidas, nenhuma resposta decide pelo segurado sem evidência, e a seguradora devolveu protocolo/agendamento em 2 conversa(s) — a primeira é `8a6040a7` |
| `yelum/residencial/eletricista` | 69 | 38 | 0 | 0 | 0 | 0 | sim | todas as 38 telas que pedem algo são respondidas, nenhuma resposta decide pelo segurado sem evidência, e a seguradora devolveu protocolo/agendamento em 2 conversa(s) — a primeira é `315f0681` |
| `yelum/residencial/encanador` | 76 | 38 | 0 | 0 | 0 | 0 | sim | todas as 38 telas que pedem algo são respondidas, nenhuma resposta decide pelo segurado sem evidência, e a seguradora devolveu protocolo/agendamento em 2 conversa(s) — a primeira é `01e31e80` |
| `zurich/auto/guincho` | 83 | 50 | 0 | 0 | 0 | 0 | sim | todas as 50 telas que pedem algo são respondidas, nenhuma resposta decide pelo segurado sem evidência, e a seguradora devolveu protocolo/agendamento em 2 conversa(s) — a primeira é `8e5fb8c0` |

## HANDOFF — 4 rota(s)

| rota | telas | respondidas | órfãs | A | B | C | chegou ao fim | por quê |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| `porto/auto/vidros` | 20 | 11 | 0 | 0 | 0 | 0 | sim | esta seguradora não abre o chamado pela conversa: ela devolve um link ou um formulário. O robô entrega o link e o caso segue com uma pessoa — é o desenho, não uma falha |
| `tokio/auto/carro_reserva` | 21 | 8 | 0 | 0 | 0 | 0 | sim | esta seguradora não abre o chamado pela conversa: ela devolve um link ou um formulário. O robô entrega o link e o caso segue com uma pessoa — é o desenho, não uma falha |
| `tokio/auto/guincho` | 27 | 9 | 0 | 0 | 0 | 0 | sim | esta seguradora não abre o chamado pela conversa: ela devolve um link ou um formulário. O robô entrega o link e o caso segue com uma pessoa — é o desenho, não uma falha |
| `yelum/auto/carro_reserva` | 91 | 67 | 4 | 0 | 0 | 0 | sim | esta seguradora não abre o chamado pela conversa: ela devolve um link ou um formulário. O robô entrega o link e o caso segue com uma pessoa — é o desenho, não uma falha |

## FALTA CAPTURA — 41 rota(s)

| rota | telas | respondidas | órfãs | A | B | C | chegou ao fim | por quê |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| `alfa/auto/bateria` | 0 | 0 | 0 | 0 | 0 | 0 | não | o acervo não tem UMA conversa desta rota. Não é que o robô falhe: ninguém nunca ligou para esta seguradora pedindo este serviço pelo WhatsApp da corretora (ou o classificador não soube etiquetar a conversa que existe) |
| `alfa/auto/chaveiro` | 0 | 0 | 0 | 0 | 0 | 0 | não | o acervo não tem UMA conversa desta rota. Não é que o robô falhe: ninguém nunca ligou para esta seguradora pedindo este serviço pelo WhatsApp da corretora (ou o classificador não soube etiquetar a conversa que existe) |
| `allianz/auto/chaveiro` | 0 | 0 | 0 | 0 | 0 | 0 | não | o acervo não tem UMA conversa desta rota. Não é que o robô falhe: ninguém nunca ligou para esta seguradora pedindo este serviço pelo WhatsApp da corretora (ou o classificador não soube etiquetar a conversa que existe) |
| `allianz/residencial/desentupimento` | 40 | 32 | 0 | 0 | 0 | 0 | não | o robô responde todas as telas que o acervo mostra, mas nenhuma sessão do corpus chegou ao protocolo, à confirmação ou ao encaminhamento — então não há prova de que esta rota vá até o protocolo. Falta uma conversa que termine |
| `allianz/residencial/eletrodomesticos` | 60 | 44 | 0 | 0 | 0 | 0 | não | o robô responde todas as telas que o acervo mostra, mas nenhuma sessão do corpus chegou ao protocolo, à confirmação ou ao encaminhamento — então não há prova de que esta rota vá até o protocolo. Falta uma conversa que termine |
| `azul/auto/carro_reserva` | 0 | 0 | 0 | 0 | 0 | 1 | não | o acervo não tem UMA conversa desta rota. Não é que o robô falhe: ninguém nunca ligou para esta seguradora pedindo este serviço pelo WhatsApp da corretora (ou o classificador não soube etiquetar a conversa que existe) |
| `azul/auto/chaveiro` | 0 | 0 | 0 | 0 | 0 | 0 | não | o acervo não tem UMA conversa desta rota. Não é que o robô falhe: ninguém nunca ligou para esta seguradora pedindo este serviço pelo WhatsApp da corretora (ou o classificador não soube etiquetar a conversa que existe) |
| `azul/auto/pneu` | 0 | 0 | 0 | 0 | 0 | 0 | não | o acervo não tem UMA conversa desta rota. Não é que o robô falhe: ninguém nunca ligou para esta seguradora pedindo este serviço pelo WhatsApp da corretora (ou o classificador não soube etiquetar a conversa que existe) |
| `bradesco/auto/bateria` | 0 | 0 | 0 | 0 | 0 | 0 | não | o acervo não tem UMA conversa desta rota. Não é que o robô falhe: ninguém nunca ligou para esta seguradora pedindo este serviço pelo WhatsApp da corretora (ou o classificador não soube etiquetar a conversa que existe) |
| `bradesco/auto/chaveiro` | 0 | 0 | 0 | 0 | 0 | 0 | não | o acervo não tem UMA conversa desta rota. Não é que o robô falhe: ninguém nunca ligou para esta seguradora pedindo este serviço pelo WhatsApp da corretora (ou o classificador não soube etiquetar a conversa que existe) |
| `bradesco/auto/pneu` | 0 | 0 | 0 | 0 | 0 | 0 | não | o acervo não tem UMA conversa desta rota. Não é que o robô falhe: ninguém nunca ligou para esta seguradora pedindo este serviço pelo WhatsApp da corretora (ou o classificador não soube etiquetar a conversa que existe) |
| `hdi/auto/bateria` | 0 | 0 | 0 | 0 | 0 | 0 | não | o acervo não tem UMA conversa desta rota. Não é que o robô falhe: ninguém nunca ligou para esta seguradora pedindo este serviço pelo WhatsApp da corretora (ou o classificador não soube etiquetar a conversa que existe) |
| `hdi/residencial/chaveiro` | 26 | 16 | 0 | 0 | 0 | 0 | não | o robô responde todas as telas que o acervo mostra, mas nenhuma sessão do corpus chegou ao protocolo, à confirmação ou ao encaminhamento — então não há prova de que esta rota vá até o protocolo. Falta uma conversa que termine |
| `hdi/residencial/desentupimento` | 0 | 0 | 0 | 0 | 0 | 0 | não | o acervo não tem UMA conversa desta rota. Não é que o robô falhe: ninguém nunca ligou para esta seguradora pedindo este serviço pelo WhatsApp da corretora (ou o classificador não soube etiquetar a conversa que existe) |
| `hdi/residencial/eletricista` | 0 | 0 | 0 | 0 | 0 | 0 | não | o acervo não tem UMA conversa desta rota. Não é que o robô falhe: ninguém nunca ligou para esta seguradora pedindo este serviço pelo WhatsApp da corretora (ou o classificador não soube etiquetar a conversa que existe) |
| `hdi/residencial/eletrodomesticos` | 0 | 0 | 0 | 0 | 0 | 0 | não | o acervo não tem UMA conversa desta rota. Não é que o robô falhe: ninguém nunca ligou para esta seguradora pedindo este serviço pelo WhatsApp da corretora (ou o classificador não soube etiquetar a conversa que existe) |
| `mapfre/auto/bateria` | 0 | 0 | 0 | 0 | 0 | 0 | não | o acervo não tem UMA conversa desta rota. Não é que o robô falhe: ninguém nunca ligou para esta seguradora pedindo este serviço pelo WhatsApp da corretora (ou o classificador não soube etiquetar a conversa que existe) |
| `mapfre/auto/chaveiro` | 0 | 0 | 0 | 0 | 0 | 0 | não | o acervo não tem UMA conversa desta rota. Não é que o robô falhe: ninguém nunca ligou para esta seguradora pedindo este serviço pelo WhatsApp da corretora (ou o classificador não soube etiquetar a conversa que existe) |
| `mapfre/auto/guincho` | 0 | 0 | 0 | 0 | 0 | 0 | não | o acervo não tem UMA conversa desta rota. Não é que o robô falhe: ninguém nunca ligou para esta seguradora pedindo este serviço pelo WhatsApp da corretora (ou o classificador não soube etiquetar a conversa que existe) |
| `mapfre/auto/pneu` | 0 | 0 | 0 | 0 | 0 | 0 | não | o acervo não tem UMA conversa desta rota. Não é que o robô falhe: ninguém nunca ligou para esta seguradora pedindo este serviço pelo WhatsApp da corretora (ou o classificador não soube etiquetar a conversa que existe) |
| `porto/auto/bateria` | 193 | 99 | 4 | 0 | 0 | 0 | sim | 4 tela(s) desta rota pedem alguma coisa e o robô não tem resposta escrita para elas. A primeira, na conversa 4830574a: “{NOME} esta por aí?” |
| `porto/auto/bateria_nova` | 0 | 0 | 0 | 0 | 0 | 0 | não | o acervo não tem UMA conversa desta rota. Não é que o robô falhe: ninguém nunca ligou para esta seguradora pedindo este serviço pelo WhatsApp da corretora (ou o classificador não soube etiquetar a conversa que existe) |
| `porto/auto/pneu` | 0 | 0 | 0 | 0 | 0 | 0 | não | o acervo não tem UMA conversa desta rota. Não é que o robô falhe: ninguém nunca ligou para esta seguradora pedindo este serviço pelo WhatsApp da corretora (ou o classificador não soube etiquetar a conversa que existe) |
| `porto/auto/taxi` | 0 | 0 | 0 | 0 | 0 | 0 | não | o acervo não tem UMA conversa desta rota. Não é que o robô falhe: ninguém nunca ligou para esta seguradora pedindo este serviço pelo WhatsApp da corretora (ou o classificador não soube etiquetar a conversa que existe) |
| `porto/residencial/desentupimento` | 0 | 0 | 0 | 0 | 0 | 0 | não | o acervo não tem UMA conversa desta rota. Não é que o robô falhe: ninguém nunca ligou para esta seguradora pedindo este serviço pelo WhatsApp da corretora (ou o classificador não soube etiquetar a conversa que existe) |
| `porto/residencial/eletricista` | 0 | 0 | 0 | 0 | 0 | 0 | não | o acervo não tem UMA conversa desta rota. Não é que o robô falhe: ninguém nunca ligou para esta seguradora pedindo este serviço pelo WhatsApp da corretora (ou o classificador não soube etiquetar a conversa que existe) |
| `porto/residencial/eletrodomesticos` | 15 | 11 | 0 | 0 | 0 | 0 | não | o robô responde todas as telas que o acervo mostra, mas nenhuma sessão do corpus chegou ao protocolo, à confirmação ou ao encaminhamento — então não há prova de que esta rota vá até o protocolo. Falta uma conversa que termine |
| `tokio/auto/bateria` | 0 | 0 | 0 | 0 | 0 | 0 | não | o acervo não tem UMA conversa desta rota. Não é que o robô falhe: ninguém nunca ligou para esta seguradora pedindo este serviço pelo WhatsApp da corretora (ou o classificador não soube etiquetar a conversa que existe) |
| `tokio/auto/chaveiro` | 0 | 0 | 0 | 0 | 0 | 0 | não | o acervo não tem UMA conversa desta rota. Não é que o robô falhe: ninguém nunca ligou para esta seguradora pedindo este serviço pelo WhatsApp da corretora (ou o classificador não soube etiquetar a conversa que existe) |
| `tokio/auto/pneu` | 0 | 0 | 0 | 0 | 0 | 0 | não | o acervo não tem UMA conversa desta rota. Não é que o robô falhe: ninguém nunca ligou para esta seguradora pedindo este serviço pelo WhatsApp da corretora (ou o classificador não soube etiquetar a conversa que existe) |
| `yelum/auto/chaveiro` | 72 | 44 | 3 | 0 | 0 | 0 | sim | 3 tela(s) desta rota pedem alguma coisa e o robô não tem resposta escrita para elas. A primeira, na conversa e6a07317: “Para que a remoção do veículo ocorra sem imprevistos, precisamos entender o local e as condições do veículo.” |
| `yelum/auto/guincho` | 818 | 474 | 2 | 0 | 0 | 0 | sim | 2 tela(s) desta rota pedem alguma coisa e o robô não tem resposta escrita para elas. A primeira, na conversa 75400aad: “Para seguir, por favor me informe o número da sua *assistência*, *placa* ou *CPF*.” |
| `yelum/auto/socorro_mecanico` | 0 | 0 | 0 | 0 | 0 | 0 | não | o acervo não tem UMA conversa desta rota. Não é que o robô falhe: ninguém nunca ligou para esta seguradora pedindo este serviço pelo WhatsApp da corretora (ou o classificador não soube etiquetar a conversa que existe) |
| `yelum/residencial/chaveiro` | 0 | 0 | 0 | 0 | 0 | 0 | não | o acervo não tem UMA conversa desta rota. Não é que o robô falhe: ninguém nunca ligou para esta seguradora pedindo este serviço pelo WhatsApp da corretora (ou o classificador não soube etiquetar a conversa que existe) |
| `yelum/residencial/desentupimento` | 0 | 0 | 0 | 0 | 0 | 0 | não | o acervo não tem UMA conversa desta rota. Não é que o robô falhe: ninguém nunca ligou para esta seguradora pedindo este serviço pelo WhatsApp da corretora (ou o classificador não soube etiquetar a conversa que existe) |
| `yelum/residencial/eletrodomesticos` | 17 | 11 | 0 | 0 | 0 | 0 | não | o robô responde todas as telas que o acervo mostra, mas nenhuma sessão do corpus chegou ao protocolo, à confirmação ou ao encaminhamento — então não há prova de que esta rota vá até o protocolo. Falta uma conversa que termine |
| `zurich/auto/bateria` | 0 | 0 | 0 | 0 | 0 | 0 | não | o acervo não tem UMA conversa desta rota. Não é que o robô falhe: ninguém nunca ligou para esta seguradora pedindo este serviço pelo WhatsApp da corretora (ou o classificador não soube etiquetar a conversa que existe) |
| `zurich/auto/chaveiro` | 0 | 0 | 0 | 0 | 0 | 0 | não | o acervo não tem UMA conversa desta rota. Não é que o robô falhe: ninguém nunca ligou para esta seguradora pedindo este serviço pelo WhatsApp da corretora (ou o classificador não soube etiquetar a conversa que existe) |
| `zurich/auto/pneu` | 0 | 0 | 0 | 0 | 0 | 0 | não | o acervo não tem UMA conversa desta rota. Não é que o robô falhe: ninguém nunca ligou para esta seguradora pedindo este serviço pelo WhatsApp da corretora (ou o classificador não soube etiquetar a conversa que existe) |
| `zurich/auto/socorro_mecanico` | 0 | 0 | 0 | 0 | 0 | 0 | não | o acervo não tem UMA conversa desta rota. Não é que o robô falhe: ninguém nunca ligou para esta seguradora pedindo este serviço pelo WhatsApp da corretora (ou o classificador não soube etiquetar a conversa que existe) |
| `zurich/auto/vidros` | 0 | 0 | 0 | 0 | 0 | 0 | não | o acervo não tem UMA conversa desta rota. Não é que o robô falhe: ninguém nunca ligou para esta seguradora pedindo este serviço pelo WhatsApp da corretora (ou o classificador não soube etiquetar a conversa que existe) |

## Os achados que NENHUMA rota reivindicou

🔴 *“truncar calado lê-se como ‘cobrimos tudo’”* (SPEC-083 §7). Estes achados do conferidor são reais — eles só não têm rota, porque a tela em que acontecem foi etiquetada com **outro** serviço, e o motor não casa aquele passo para o serviço da rota. Eles não entram na faixa de nenhuma rota, e é por isso que aparecem aqui.

_nenhum._

## Bateria 5 — condomínio · empresarial · sinistro

| rota | assunto | conversa | vai para uma pessoa? | por qual caminho |
|---|---|---|:---:|---|
| `allianz/residencial/chaveiro` | apolice_de_condominio_ou_empresa | `aa2e0a68` | sim | a tecla do passo `menu_qual_seguro_tres_opcoes` vai a uma pessoa (apolice_de_condominio_ou_empresa) |
| `allianz/residencial/consulta_veterinaria` | sinistro | `c58a171a` | sim | o passo `menu_outros_assuntos_sinistro` é `noop`: o robô não responde nada nesta tela |
| `allianz/residencial/desentupimento` | apolice_de_condominio_ou_empresa | `3a895d36` | sim | a tecla do passo `menu_qual_seguro_tres_opcoes` vai a uma pessoa (apolice_de_condominio_ou_empresa) |
| `allianz/residencial/eletrodomesticos` | apolice_de_condominio_ou_empresa | `eb7c521e` | sim | a tecla do passo `menu_qual_seguro_tres_opcoes` vai a uma pessoa (apolice_de_condominio_ou_empresa) |
| `allianz/residencial/encanador` | apolice_de_condominio_ou_empresa | `be8e3f8d` | sim | a tecla do passo `menu_qual_seguro_tres_opcoes` vai a uma pessoa (apolice_de_condominio_ou_empresa) |
| `allianz/residencial/encanador` | apolice_de_condominio_ou_empresa | `be8e3f8d` | sim | gatilho de handoff `exclusivamente a servi[çc]os nas[\s\S]{0,4}[áa]reas comuns` |
| `allianz/residencial/encanador` | apolice_de_condominio_ou_empresa | `be8e3f8d` | sim | o passo `aviso_areas_comuns` é `noop`: o robô não responde nada nesta tela |
| `allianz/residencial/limpeza_caixa_dagua` | apolice_de_condominio_ou_empresa | `eade0321` | sim | a tecla do passo `menu_qual_seguro_tres_opcoes` vai a uma pessoa (apolice_de_condominio_ou_empresa) |
| `allianz/residencial/limpeza_caixa_dagua` | apolice_de_condominio_ou_empresa | `eade0321` | sim | gatilho de handoff `exclusivamente a servi[çc]os nas[\s\S]{0,4}[áa]reas comuns` |
| `allianz/residencial/limpeza_caixa_dagua` | apolice_de_condominio_ou_empresa | `eade0321` | sim | o passo `aviso_areas_comuns` é `noop`: o robô não responde nada nesta tela |
| `allianz/residencial/maquina_de_lavar` | apolice_de_condominio_ou_empresa | `7ac3c101` | sim | a tecla do passo `menu_qual_seguro_tres_opcoes` vai a uma pessoa (apolice_de_condominio_ou_empresa) |
| `porto/auto/vidros` | sinistro | `0c1e8e3e` | sim | o passo `vidros_formulario` é `noop`: o robô não responde nada nesta tela |
| `yelum/auto/carro_reserva` | sinistro | `39e395bb` | 🔴 **NÃO** | o passo `cr_outros_assuntos` responde '4' sozinho |

