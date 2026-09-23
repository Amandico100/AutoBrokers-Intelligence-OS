# EXTRA-002 · Agger via navegador — NOTAS AO VIVO (seletores, fluxo, auth)

> 📊 Medido AO VIVO em 22–23/09/2026 na conta AUTORIZADA da Resulta, navegador real (`--headless=new`), como evidência da proposta SPEC-EXTRA-002. Varredura de segredo/PII → 0. Valores de sessão (token, senha, CPF, placa) nunca entram aqui.

# Agger (aggilizador.com.br) — seletores e fluxo medidos (SEM segredo/PII)

App Angular Material (Material 3). Host da API do motor: `api.multicalculo.net`.
Host de auth/config: `api-prod.aggilizador.com.br`. Navegador real `--headless=new` passa o Akamai.

## 1. Login pela TELA (form real)
- URL: `https://aggilizador.com.br/login`  (SPA lento: form aparece ~11–50 s)
- e-mail:  `input[type="email"]`
- senha:   `input[type="password"]`
- entrar:  `button:has-text("Entrar")`  (1 só na tela)
- 🔴 MODAL de sessão única (SEMPRE que já há sessão ativa — o robô derruba a do humano):
  título "Aviso"; texto "…já há uma sessão ativa com este mesmo usuário. Deseja encerrá-la e prosseguir?"
  botões `Cancelar` / **`Prosseguir`**  → clicar `button:has-text("Prosseguir")` (é o fluxo `derrubaSessao`)
- pós-login navega para `https://aggilizador.com.br/cotacoes`

## 2. Auth (o que decide a arquitetura)
- `POST api-prod.aggilizador.com.br/usuario/login`  {email, senha} → 201, token no CORPO (JSON), NÃO cookie.
  token "aggilizador" ≈ 1319 chars → autoriza `api-prod.aggilizador.com.br` (header `Authorization: <token>`).
- `POST api-prod.aggilizador.com.br/usuario/login/pdocs` → 201; devolve `token` (≈488 chars) + `idIntegracao`.
  Esse token de 488 é o que vai em `Authorization` de **api.multicalculo.net** (medido: len do header = 488).
- Ou seja: DOIS tokens distintos; o motor (multicalculo) usa o token do **pdocs**, não o do login normal.
- Sem cookie de sessão; tudo por header `Authorization`. Token expira (~8 h; JWT).

## 3. Lista de negócios (renovações)
- `/cotacoes` dispara `GET api.multicalculo.net/calculo/negocio/busca/v2?modo=1&…`
- resposta: `{page, limit, data[]}`; `data[]` agrupa por CLIENTE:
  item = {seguradoNome, seguradoCpfCnpj, fone1, qtdNegocios, negocios[]}  (PII → só contar)
- `negocios[]` item = {id(uuid), ramo(int; **31 = auto**), placa, modelo, status(2=calculado),
  vigenciaIni, vigenciaFim, idIntegracao, …}
- Na UI a lista é um accordion: `mat-expansion-panel-header` (1 por cliente). Expandir revela
  os cards: `a.dados-cotacao[href*="/cotacao/<ramo>/resultados/{uuid}"]` (auto, residencial, vida, …).

## 4. Abrir a renovação (fluxo confirmado)
1. expandir um `mat-expansion-panel-header`
2. clicar `a.dados-cotacao[href*="/cotacao/auto/resultados/"]`  → página de RESULTADOS
   🔴 GUARD de rota: `goto` direto OU clique "cedo" volta para `/cotacoes`. Só navega via clique
   no card DEPOIS da hidratação; passa de forma probabilística → clicar com retry (força + wait_for_url).
3. na página de resultados, botões: **`Recalcular`**, `Imprimir`, `Incluir cálculo`, `Status`.
   clicar `button:has-text("Recalcular")` → formulário `/cotacao/auto/formulario/{uuid}/{versao}`
4. formulário (prefill dispara buscaPlaca, fipeModelo, negocio/{uuid}, cotacao/versoes/{uuid}):
   - toggle **"Esta é uma renovação"** (`mat-checkbox`/`mat-slide-toggle` com texto "renova")
   - botões: `Calcular`, `Aplicar`, `Configurar pacotes`, `Salvar`, `Redefinir`, `Voltar`
   - **clicar só `button:has-text("Calcular")`** (nunca Salvar) → `POST calcularV2`
   - form controls: cpfCnpj, placa, fipe, modelo, anoFab/anoMod, bonusAnterior, isDanosMateriais/
     Corporais/Morais, isAppMorte, carroReserva, vidros, cep, etc. (todos `formcontrolname`)

## 5. Cálculo + polling (interceptar as respostas do próprio app)
- `POST api-prod.aggilizador.com.br/calculo/calcularV2` (201) — corpo grande (tem senhas de seguradora → não logar)
- `GET api.multicalculo.net/calculo/cotacao/calculos/{uuid}/{versao}` — pola ~28x, ~7 min
  resposta = array de ~17 seguradoras; por seguradora:
  {nomeSeguradora, premio, premioMensal, valorFranquia, tipoFranquia, credenciaisValidas,
   retornoErro, tempoResposta, resultados[]}
  cada `resultados[]` = {nroCalculo, pathPdf/pdfFileNameAgger, premio, premioMensal, franquia,
   coberturas{casco, isDanos*, isApp*, vidros, carroReserva, assist24hs, tipoFranquia, …},
   parcelamentos[]{parcelas, premioPrimeiraParc, premioDemaisParc, tipoPag}}
  🔴 STRIP obrigatório em TODA resposta: `login, senha, loginWs, senhaWs` (presentes no polling e em versoes/negocio).

## 6. Recomendação de arquitetura (produção)
- FORM LOGIN (com o modal Prosseguir) + INTERCEPTAÇÃO de `page.on("response")` das rotas do app.
  Deixar o PRÓPRIO app autenticar no multicalculo (token pdocs) e só LER as respostas — não reconstruir a auth.
- Sessão única: um login por conexão sob lease; token pdocs em Redis por (company_id, connection_id).
- Navegação depende de guard → dirigir a UI como humano (expandir → clicar card → Recalcular → Calcular),
  com retry; nunca `goto` direto na rota de resultados.
