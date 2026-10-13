# JUIZ FRESCO · SPEC-131-B · O aplicativo de Renovação

> MODELO: claude-opus-5-5 · read-only (código, contrato, dados) · 13/10/2026 · árvore `AutoBrokers-FIX`, branch
> `spec/131-B-o-aplicativo`, HEAD `af7ea4f`, diff `c052550..af7ea4f` (78 arquivos, +10.825/−1.603). Banco: só SELECT
> (projeto dcajcvlzcjbmyapmklil). Testes com dublê (o PostgREST em memória dos próprios testes). Nenhum CPF, telefone ou
> nome real impresso; os números de telefone abaixo são sintéticos.

## VEREDITO — PASS COM PENDÊNCIAS, condicionado a 1 BLOCKER pequeno (B1)

O fio está inteiro e provado com o motor real. O isolamento entre corretoras está certo. O produto não envia nada sozinho.
A página de cotação e a do canal não mudaram (provei byte a byte). O telefone do cliente não vai para log nem para o banco.
O único defeito material é o CPF do campo de busca, que vai em claro para a URL e para o log de acesso do backend.
O conserto é de 1–2 arquivos.

## BLOCKERS

### B1 · O CPF (e o nome) digitado na busca vai em claro para o log de acesso do backend e para a URL da página
- **Onde:** `components/aplicativos/renovacao/AbaRenovacoes.tsx:283` (placeholder "Nome ou CPF") → `:126/:136` (o `q`
  vai para a URL da página por `router.replace`) → `app/api/renovacoes/route.ts:24-29` (repassa `q` na query string do
  GET ao backend) → `backend/Dockerfile:27` (`uvicorn app.main:app …` sem `--no-access-log`). Com isso, o uvicorn 0.27
  grava `get_path_with_query_string(scope)` em `access_logger.info` (medido no código-fonte instalado,
  `uvicorn/protocols/http/h11_impl.py`). Não existe filtro de `uvicorn.access` em `backend/app` (grep: 0).
- **Por que importa:** `backend/app/api/renovacoes.py:382-386` compara o CPF por HMAC justamente para que o documento
  "nunca esteja em claro". O log de acesso desfaz isso: o CPF inteiro fica no log do contêiner a cada busca (e no
  histórico do navegador e em qualquer log de proxy, porque vai na URL da página). O mesmo vale para o nome do cliente.
- **Teste do produto (§2):** muda a SEGURANÇA (vazamento de dado pessoal num log)? **SIM → BLOCKER.** Não se rebaixa.
- **Conserto sugerido (o executor reproduz antes):** (a) a busca com 11 ou 14 dígitos não vai para a URL da página
  (fica só no estado); (b) o proxy manda `q` ao backend no corpo de um POST ou num cabeçalho, nunca na query string.
  Guarda: um teste que monta a requisição do proxy com um CPF sintético e exige zero dígitos dele na URL, mais a linha
  de controle que fica vermelha quando `q` volta para a query.

## PENDÊNCIAS (nenhuma muda um byte hoje, ou é aceite ainda não provado)

1. **P1 · O gate de `app/` (CLAUDE.md §9.1) está incompleto.** O `next build` não terminou, então não houve `next start`.
   O `next dev` não substitui: ele compila sob demanda e não pega erro que só aparece no build. Reproduzi o que dava:
   📊 `tsc --noEmit` = **0 erros** (EXIT 0) · 📊 `node scripts/rotas-montam.test.mjs` = **322 rotas ordenadas, "A
   TABELA DE ROTAS MONTA"**. **O que destrava:** rodar `next build && next start` e fazer 1 GET em `/api/renovacoes`
   (esperado 401 sem sessão) numa máquina com memória ou dentro do `docker build`. Se não der, conferir depois do
   Implantar com `/api/versao` + `/api/renovacoes` → 401, nunca 500. Classificação: aceite não provado (MATERIAL pela
   §9.1 do protocolo), mas não é defeito de código.
2. **P2 · "Quero renovar" pode ir a quem não está ativo.** `proposta.membro_para_o_cliente` filtra a corretora, mas
   não filtra `company_members.status='active'`. Hoje o risco é latente: 📊 10/10 membros estão `active`, e o DELETE de
   `app/api/dashboard/team/route.ts:235` apaga a linha (e o número vai junto). Destrava com `.eq("status","active")`
   (mais `ROB.membro_ativo`).
3. **P3 · A tela aceita números que o banco recusa, e a pessoa vê um erro genérico (500).** `normalizar_whatsapp`
   aceita E.164 estrangeiro e fixo com 10 dígitos começando em 6–9. O CHECK `ck_company_members_whatsapp_e164` exige
   `+55` e fixo `[2-5]`. 📊 Testei 5 entradas sintéticas: 3 passam no app e caem no CHECK (`+1…`, `(11) 8xxx-xxxx`,
   `+351…`). A pessoa recebe "não consegui fazer isso agora". Destrava: a mesma regra no app, com a recusa 422 em
   português.
4. **P4 · A regra D-131-07 só existe no proxy Next.** `aggers-da-equipe/route.ts:85-90` recusa o admin que tenta
   `conectar`/`trocar_senha` por outra pessoa. No backend, `conta_do_robo._pode_mexer` ainda deixa (é rota interna, com
   chave, e só se chega a ela pelo proxy). Destrava: a mesma recusa no `agir_do_membro`, como defesa em profundidade.
   A rota genérica `/credentials` continua recusando `agger` (`PORTAIS_SO_PELO_COMANDO`).
5. **P5 · "Todas" está aberto a qualquer membro, inclusive a atendente.** Isso inclui o envio, que devolve o `wa.me`
   com o telefone do cliente. É o desenho: o laudo de design §5 diz "comercial → Minhas; admin → Todas" como padrão,
   não como trava. Mas a FAQ do catálogo ("Quem administra a corretora vê todas") pode ser lida como restrição. Fica
   como decisão para o Founder: limitar por papel, ou corrigir a frase.
6. **P6 · O substituto não vê as renovações de quem está ausente em "Minhas".** O filtro é só dono ou responsável. O
   aviso vai para ele (D-131-08), mas a lista dele não mostra as renovações. Destrava: incluir as renovações de quem
   ele cobre hoje.
7. **P7 · Duas falhas de Playwright eram do ambiente, não do código.** Na rodada em lote,
   `test_spec130a_conserto::test_navegador_cada_rotulo…[390|1280]` deram `TimeoutError` em `set_content` (o `tsc`
   rodava ao mesmo tempo). Sozinhas: 📊 **2 passed (193 s)**. O modelo delas (`novo_sem_apolice`) gera HTML idêntico ao
   da base.
8. **P8 · O envio reaproveita a página já publicada.** Se a pessoa trocar o WhatsApp de trabalho depois de publicar, o
   "Quero renovar" da página antiga continua com o número velho até ela republicar. É raro.

## EVIDÊNCIA

| ataque | resultado | prova |
|---|---|---|
| isolamento (a API e as rotas Next) | PASS | `comum.ts:23-31,43-51`: `company_id`/`user_id` vêm de `requireCompanyMember`, e o corpo do navegador é ignorado (só `via`). Backend: `RepositorioDeRenovacoes` + `solicitante_company_id` no banco e de novo no código (`renovacoes.py:337-352`). No fio, passo ⑤, a outra corretora recebe 404 em detalhe, apresentação e envio, e "todas" volta `[]` |
| a mesma ação 2×, e duas ao mesmo tempo | PASS | envio já `enviada` → só o evento (`renovacoes.py:670-672`); `ConcorrenciaPerdida` → 409; o corpo com `estado`/`coluna` → 400 (mutação 4) |
| o telefone do cliente | PASS | aparece só no `wa_me_url`. Os logs registram só `type(exc).__name__`. O fio prova "nem log, nem linha" com linha de controle vermelha (`test_spec131b_o_fio.py:96-104,159-163`). `cliente_cru` sem cache |
| o produto envia sozinho? | PASS (não envia) | sem envio no diff (grep de `send/evolution/sendText` = 0). A Renovação oferece só "Só calcular" e "Enviar e negociar" (em breve). `calcular_entregar` é só lido (`AbaConfigurar.tsx`). As opções da Cotação já existiam antes (`ServicosClient` da base) |
| WhatsApp de trabalho de outra pessoa · `integrations` | PASS | `_so_a_propria_pessoa` + proxy com `user_id` da sessão (`meu-perfil/route.ts:71-75`). Nenhuma escrita em `integrations` no código. 📊 `integrations` atualizadas hoje = 0 · `whatsapp_trabalho_e164` gravados = 0 |
| ausência com substituto de outra corretora | PASS | `criar_ausencia`: `membro_ativo(cid, sub)` filtra a corretora e o status; só a própria pessoa ou o admin (`_e_admin`) |
| admin cadastra o Agger de outra pessoa | PASS no produto (P4) | proxy 403; o modal da corretora não lista mais as pessoas; `AggersDaEquipe apenasEu` |
| a página de RENOVAÇÃO servida | PASS | fio: h1 com o vencimento, "Sua renovação" em 1º, "O seu seguro hoje × a renovação", "há 3 anos" com 3 elos provados. Proibidas ausentes: "a melhor das", "Mais em conta", "Recomendada", "Comparação independente", "cliente desde". `anos_de_renovacao` só conta elo com a linha anterior presente. Os testes "sem prova" e "Quero renovar ao dono / à corretora / sem botão" leem o HTML servido |
| cotação e canal sem mudança | PASS, byte a byte | script meu: `render_proposta` da BASE (`git show c052550`) × HEAD, 7 modelos. Carteira cotação, com_apólice e sem_apólice iguais (`2eaf073ee01a`); canal cotação, renovação e sem_apólice iguais (`1df55a583cef`); só `carteira_renovacao` muda. `SCRIPT_DA_PROPOSTA` e `CSS_DA_PROPOSTA` idênticos. 📊 0 artefatos de renovação já publicados no banco: nenhuma página antiga muda ao reabrir |
| "com qual conta = corretora" | PASS | `qual_agger.decidir` só no ramo `servico=="renovacao"` e sem `conta_de_origem`. Regra própria, `fallback=False`, sem aviso de desvio (avisa só se a conta global não estiver conectada). O teste prova B sem a escolha, o recálculo na conta de origem e a cotação intocada |
| instalar = ligar | PASS | `INSTALAR_JA_LIGA={'renovacao'}` → `confirmar:true` → `AlertDialog` "Ligar Renovação?", com o "Como começar" e "a partir da próxima madrugada" (`CabecalhoDoAplicativo.tsx:112-145`). O card da galeria só tem link |
| regressão da fila (QuadroOuLista) | PASS por leitura | mesmo teto de 50, coluna vazia escondida, `localStorage` em try/catch, a ordem do quadro e da lista preservadas, sem arrastar |
| o teste do fio usa as peças REAIS? | PASS | `publicar_renovacao` real pela API, e `ArtifactService.abrir_compartilhado` real sobre o banco dublê; dublê só no banco e na InfoCap |
| testes | PASS | 📊 16 arquivos (os 4 da 131-B, os 4 migrados e as vizinhas 130-A/131-0/131-A): **307 passed, 1 skipped, 2 failed** em 22 min 29 s. As 2 falhas passaram sozinhas (P7). `node --test a-loja-e-a-casca.test.mjs`: **"TODOS OS GUARDAS VERDES"** |
| testes migrados (§9.3) | legítimo | 130-A: renovação `[recomendada, sua_renovacao]` → `sua_renovacao` em 1º (D-131-22), com a lição transferida para o arquivo da 131-B; o link de Serviços virou a aba Configurar |

**Os 3 números que reproduzi (§0.4):** 📊 VERIFY da migration `3·4·19·0·3·0·1·2·2` bateu (SELECT do bloco VERIFY). 📊
BLOCO 0 B6: `renovacao-maxima` instalada = **0**. 📊 B7: membros ativos com `phone` ≥ 10 dígitos = **10/10**. Também
batem: 322 rotas e tsc com 0 erros. 📊 Renovações no banco: 8 (2 calculadas, 1 falhou, 5 pendentes); 0 corretoras com o
aplicativo instalado.

**Rollback da migration:** escrito antes; recusa se houver instalação ou número gravado; devolve os ícones.
Expand-only. OK.

## MAIOR LACUNA
O §9.1 não foi cumprido: ninguém viu `next start` responder com este diff (P1). Tudo o que provei para baixo dele
(tsc 0, 322 rotas, `next dev` sem 500) é necessário, mas não basta.

## PRÓXIMA AÇÃO
Consertar B1 (a busca fora da query string e da URL da página, com o guarda) e conseguir o `next build` + `next start`
+ 1 GET em `/api/renovacoes` antes do push.

## CONFIANÇA — 80
Ficou POR MEDIR: o `next start`. A página e o app no celular e nos dois temas (é do juiz de design). As mutações 1–5
(não rerodei; li os guardas, e os de telefone e fio têm linha de controle). O clique real no `wa.me` com 500 caracteres
(B1 do BLOCO 0). A bateria inteira.

## NOTA — 84
(Com B1 consertado e P1 provado, 89.)
