# BLOCO 0 da SPEC-131-A — o Agger AO VIVO (A1 · A3 · A7 · A10 · A11 · B4 · licença)

> 🔍 Medidor ao vivo · 12/10/2026, 21:45–22:50 UTC (18:45–19:50 BRT) · branch `spec/131-A-a-madrugada`, HEAD `2cd6168`.
> Script: [`backend/scripts/bloco0_131a_agger_ao_vivo.py`](../../../../backend/scripts/bloco0_131a_agger_ao_vivo.py) (sem segredo; credenciais
> do ambiente). Saídas brutas fora do git. Chromium local, `PORTAL_HEADLESS_MODE=classic`.
> ⛔ Sem dado pessoal: ids viram `<id>`, valores `<redigido>`, comparações por **hash** (sha256, 12 hex). Marcas: 📊 medido · 💭 estimativa.
> ⚠️ A máquina estava sem memória (📊 `Win32_OperatingSystem`: 357 MB livres de 8.084 MB, 37 processos `chrome`): a 1ª carga
> de `/login` levou 📊 32–180 s em 5 de 9 tentativas (curl na mesma hora: 0,2–1,7 s). Tempos daqui: PIORES que no servidor.

## 0. Em uma tela
| # | resultado | o que muda no desenho |
|---|---|---|
| **A1** | 📊 O "Prosseguir" é o **mesmo** `POST /usuario/login` com uma chave a mais: `{email, senha, derrubaSessao}`, e `derrubaSessao` = o **id da sessão ativa** que o próprio Agger devolve na 1ª tentativa (hash igual ao `idSessao` do contexto 1: 2/2). Nenhuma rota de "derrubar todos" no app. **Mas a sessão "derrubada" não cai**: o token antigo seguiu 200 por ≥ 147 s e a tela antiga não reagiu (3/3) | A exceção PODE ligar (só derruba aquele login). A guarda deixa passar SÓ `derrubaSessao == data.id` da resposta "Já existe uma sessão ativa" do MESMO contexto. ⚠️ "a pessoa voltou" não se detecta por 401: só por um novo login ver o aviso (ver §1.3) |
| **A3 / A10** | **NÃO MEDIDO** — não há no repositório perfil de teste sem dado pessoal; o da 129-B/129-C mora fora do git | fica a premissa 📊 2 simultâneos 16/16 (E7); 3 e a 3ª versão de RE seguem por medir — pedir ao Founder um perfil autorizado |
| **A7** | **NÃO MEDIDO** — o `cotador@` da AutoFleet enxerga 📊 **0** negócios (busca do próprio app, 730 d, 13 ramos, `usuario` vazio, `limit=500`): não há negócio dele para a comercial procurar. A tentativa de leitura na conta da pessoa não terminou o login (máquina lenta) | depende de A3. Até lá vale o "se der errado" da SPEC: o aviso diz "no Agger da corretora" por extenso |
| **A11** | 📊 1º contexto logado: **+300–310 MB RSS / +217–227 MB USS**; cada contexto a mais logado: **+169–225 MB RSS / +29–73 MB USS** (n=3, ocioso em `/cotacoes`, Windows, sem cálculo) | 💭 6 contextos ≈ 1,3–1,5 GB RSS por processo. Medir de novo no contêiner Linux durante um cálculo antes de fixar o teto |
| **B4** | 📊 O roteador do app declara `cotacao/:ramo/:page/:idIntegracao/:versao` e usa `/cotacao/:ramo/resultados/:idIntegracao` (e `…/:versao/:token`), `/cotacao/:ramo/formulario/:idIntegracao/:versao`, `cotacao/:idIntegracao/impressao` | o "Abrir no Agger" pode ser **link direto** `…/cotacao/<ramo>/resultados/<negocio_ref>` (temos `negocio_ref` e o ramo). ⚠️ Que ele abre com a pessoa já logada e volta ao destino depois do login **não foi provado por clique** |
| **licença** | Resulta: **NÃO MEDIDO** (2 cargas de página falharam + 1 aviso de sessão ativa no `cotador@` da Resulta). AutoFleet, do `/usuario/current`: 📊 `licenca` 2026-10-20 · `expirationDate` 2026-10-27 · `dataLimiteCalculo` 2026-10-27 · `qtdeLicenca` 9 · `statusCorretora` 1 · nenhum aviso na tela | 🧑 a Resulta tinha 📊 `licenca` 13/10/2026 em 10/10 (A-PROVA §11) = amanhã. O motor pode ler `dataLimiteCalculo` no login e avisar ANTES da madrugada falhar |

## 1. A1 — o "Prosseguir", elo a elo
📊 3 rodadas completas (21:57, 22:02, 22:08 UTC), conta de ROBÔ `cotador@` da AutoFleet. Contexto 1 = a sessão do PRODUTO
(`Sessoes.obter` + `agger_guarda`); contexto 2 = o mesmo login, com uma guarda de medição que grava tudo e só deixa passar
escrita em `/usuario/*`. Comando: `bloco0_131a_agger_ao_vivo.py --env <fora do git> --saida <fora do git> prosseguir`.

### 1.1 O que sai
| t desde o clique | requisição | resposta |
|---|---|---|
| (antes) | `POST api-prod /usuario/login` `{email, senha}` | **201** `{message: "Já existe uma sessão ativa com esse usuário.", data: {id, token, usuarioId, status: true, dispositivo: null, createdAt…}, assinaturaId}` |
| — | o aviso, 📊 6,9 / 10,1 / 7,3 s após "Entrar": *"Caro usuário do Aggilizador, identificamos que já há uma sessão ativa com este mesmo usuário. Deseja encerrá-la e prosseguir com o login?"* · botões `Cancelar` · `Prosseguir` | |
| 0,12 s | `POST api-prod /usuario/login` `{email, senha, derrubaSessao: <uuid>}` | **201** o usuário inteiro + token NOVO + `idSessao` NOVO |
| 1,6–3,3 s | GETs da tela inicial + 2× `POST /usuario/login/pdocs` `{}` | 201 · 201 |
| 2,6–3,1 s | o contexto 2 chega a `/cotacoes` | |

- 📊 `hash(derrubaSessao)` = `hash(idSessao do contexto 1)` (rodada 2: `7339eaecde01`; rodada 3: `71bcccf69aa4`). O alvo é UMA sessão, por id.
- 📊 Rotas `usuario/*` no código do app: 33.
  Nenhuma de "derrubar todas"; o diálogo é `app-derruba-sessao` / `openDerrubaSessaoDialog`.
- A guarda de produção já barra isso: `DERRUBA` (`agger_guarda.py:47`) casa `derrubaSessao` no corpo (`agger_guarda.py:184`).

### 1.2 O que acontece com quem foi "derrubado" (o contexto 1)
| sonda (a cada ~7 s, até 147 s) | rodada 2 (guarda do produto) | rodada 3 (WebSocket livre, "como pessoa") |
|---|---|---|
| `GET /calculo/seguradoras` com o token ANTIGO | 📊 200 em 21/21 | 📊 200 em 21/21 |
| `GET /usuario/current` com o token ANTIGO | 📊 200 em 21/21 — e devolve a sessão **NOVA** (hash do `idSessao` e do token = os do contexto 2) | idem |
| a tela | 📊 continua em `/cotacoes`, sem diálogo, sem texto de sessão encerrada | 📊 idem · o app abriu **0** WebSocket |
| controle: as mesmas sondas com o token do contexto 2 | 📊 200 / 200 | 📊 200 / 200 |

- ⚠️ `pdocs`: na rodada 1, `busca/v2?page=1` com o token antigo deu 📊 403 em 12/12 desde 5,8 s — **sem linha de controle** (a consulta
  pode ser a causa: a mesma busca com outros parâmetros dá 400 para os dois contextos). O controle certo (a busca do próprio app)
  falhou 2× na carga de página → **NÃO MEDIDO**. Escrita (`calcularV2`) com o token antigo: não testada (seria um cálculo).
- 📊 Logout do contexto antigo depois do Prosseguir: `deslogaSessao` 201 (3/3). 3º login de conferência: **sem aviso** (3/3) → nada sobrou.

### 1.3 O que isso muda (INFERÊNCIA a partir do medido)
1. "Prosseguir" encerra **só a sessão daquele login, pelo id** — a pré-condição (1) da nota 88 (I1 §5.2) está cumprida.
2. O Agger garante a sessão única **no login**, não durante o uso: quem foi derrubado não é avisado e o token dele segue lendo.
   💭 A pessoa derrubada às 03:00 só percebe ao entrar de novo (verá o aviso). Para o robô: ser derrubado pela pessoa **não**
   aparece como 401 nas leituras de `api-prod` — o `descartar` por 401/403 (`agger_sessao.py:299`) pode não disparar.
3. A regra "a pessoa voltou → não prossegue de novo" só se detecta no PRÓXIMO login (o aviso). Como o Agger de pessoa faz logout
   depois de cada pedido (`motor.py:742-750`), cada pedido seguinte vê o aviso se ela entrou → o "1× por conta por noite" funciona.

## 2. A11 — memória por contexto (📊 psutil, soma dos processos `chrome-headless-shell` filhos do script)
| momento | rodada 1 RSS/USS (MB) | rodada 2 | rodada 3 |
|---|---|---|---|
| navegador, 0 contexto | 75 / 24 | 85 / 31 | 59 / 16 |
| contexto 1 logado | 376 / 241 | 395 / 259 | 366 / 242 |
| + contexto 2 logado | 601 / 315 | 587 / 305 | 534 / 271 |

## 3. Os NÃO MEDIDOS e por quê
- **A3/A10:** os perfis do repositório são gravações saneadas — rodar com eles seria inventar
  pessoa e mandá-la às seguradoras. 📊 `multicalculo_canario.py` recusa perfil dentro do git (`_fora_do_git`).
- **A7:** sem negócio do `cotador@` (📊 0). A entrada SÓ LEITURA na conta da pessoa (22:41 UTC) terminou em `SessaoIndefinida`
  (login sem desfecho em 90 s, máquina lenta) e o logout automático deu tempo esgotado — ver §4.
- **Licença Resulta / B4 por clique:** 1ª tentativa, `goto /login` > 30 s; 2ª (21:54 UTC), **aviso de sessão ativa no `cotador@` da
  Resulta** → Cancelar (📊 `portal_accounts.robo_batida_em` nulo: não era o motor do produto); 3ª, `ERR_CONNECTION_ABORTED`.

## 4. ⚠️ Rastro deixado
- `cotador@` AutoFleet: 📊 12 `POST /usuario/login` (3 com `derrubaSessao`), 9 sessões, 9 logouts 201, 3 conferências sem aviso.
  `calcularV2` = 0. Nenhuma pessoa derrubada.
- `cotador@` Resulta: 1 login → aviso → **Cancelar**.
- 🔴 **Conta da PESSOA (AutoFleet): possível sessão fantasma** criada entre 22:41 e 22:46 UTC (19:41–19:46 BRT): o POST de login
  passou pela guarda (o ramo de logout só roda com `logins ≥ 1`, `agger_sessao.py:233`) e o logout esgotou o tempo. Se ela vir o
  aviso ao entrar, é o login dela: **pode Prosseguir** (§1.1: derruba só aquela sessão). 📊 O token `api` dura ≈ 8 h (`expires`
  do `/usuario/current` − hora do login = 29.018 s); o `pdocs`, ≈ 3 h (11.026 s) — o "3 h" da E18 é o do `pdocs`.

## 5. Fora do escopo, visto
1. 🔴 **Segurança do Agger:** a resposta do login com sessão ativa traz `data.token` = o token da OUTRA sessão (📊 hash igual ao
   `Authorization` do contexto 1, 2/2). Quem tem a senha pega a sessão viva sem derrubar ninguém. O robô não usa (o token vem só do
   header das próprias requisições, `agger_sessao.py:113-126`) — e nenhum log pode gravar o corpo da resposta de login.
2. **`goto` de 30 s no login** (`agger_sessao.py:216`, padrão do Playwright): com a máquina carregada falhou 5 de 9 vezes; a falha sai
   como `TimeoutError`, não `SessaoIndefinida`.
3. **A busca/v2 mudou:** `?ramos=<r>&periodo=730` (129-C) dá 📊 400; a do app leva `textoBusca, modo=2, page, limit, ramos, tipos,
   usuario, periodo, sortOrder, integracaoInfo`.
4. O login devolve `dataLimiteCalculo`, `licenca`, `expirationDate` e `diasParaExpirarSenha` (📊 115) — dá para avisar a corretora antes.
5. O app tem `usuario/refreshToken` (P-128-01) e `calculo/fechaNegocio`.
