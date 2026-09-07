# PACOTE · BUILDER U3 — SPEC-EXTRA-001 · a tela do Auxiliar e as rotas Next

Você é o 🔧 BUILDER da unidade **U3 · tela e rotas Next** da **SPEC-EXTRA-001 · A operação dos pilotos**. Modelo: Opus 5. A escrita desta unidade é **só sua** (§4). Árvore: `C:\Users\amand\Projetos\AUTOBROKERS RESULTA\AutoBrokers-FIX` (branch `feat/spec-extra-001-operacao-pilotos`). Um desenhista escreve `scripts/a-cobranca-chega-a-quem-deve.test.mjs` e um builder U1 escreve o backend **ao mesmo tempo** — você não toca em Python nem nesse script.

## Leia primeiro
```
docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md              §0–§3, §5, §7.3
CLAUDE.md                                            §7 · §9.1 · §9.3 · §12.1
docs/canon/PROMPT-DE-EXECUCAO-EXTRA-001-CONTRATOS.md inteiro — §1, §2 (colunas do ledger) e §6 são o seu contrato exato
docs/canon/specs/SPEC-EXTRA-001-operacao-dos-pilotos.md   §0.5 · §2 · §5 · §6 · §8 (G02, G03, G11, G14, G18, G23)
docs/canon/DS-001-design-brief.md                    §5 (a referência de UI que o juiz abre)
components/auxiliares/PainelDeRotinas.tsx            inteiro (1.057 linhas) — arquivo-hub, UM dono: você
app/api/dashboard/rotinas/route.ts                   inteiro
app/api/dashboard/auxiliaries/cobranca/liberar-reenvio/route.ts   o padrão de rota (resolveSessionCompany + .eq('company_id')); NÃO muda
lib/vault/server.ts                                  resolveSessionCompany / getSupabaseAdmin (só ler)
scripts/rotina-mora-no-auxiliar.test.mjs             o guarda vizinho que TEM de continuar verde (`node scripts/rotina-mora-no-auxiliar.test.mjs`)
docs/canon/reports/SPEC-098-EXECUTION-REPORT.md      §6/§11 — como a 098 descreveu "a empresa ATIVA" nas rotas (resolveSessionCompany é fail-closed)
```

## As travas
```
⛔ NENHUMA mensagem sai. NENHUM agente é ligado. NENHUM portal. Banco: só SELECT (as rotas novas escrevem no ledger, mas você NÃO as executa contra produção; prova com `tsc` e com o guarda).
⛔ NUNCA imprimir CPF, telefone, apólice, placa, nome de pessoa, senha ou token. NUNCA um telefone real no código, nem como placeholder (📊 `PainelDeRotinas.tsx:861` tem um hoje — troque por `55 47 9XXXX-XXXX`).
⛔ NUNCA `git add -A`. NÃO commitar. NÃO tocar em variável de ambiente. Arquivos com LF.
⛔ Nenhuma tela ou controle sem motor por trás (SPEC-078 E.1): `equipe` e `cliente` só aparecem porque U1 os implementa; `approval`/`live` NÃO voltam ao seletor.
⛔ A tela nunca expõe `canario`.
```

## O EXECUTION CARD desta unidade
```
OUTCOME ..............  a corretora escolhe a modalidade em português (Teste · Somente relatório · Encaminhar para minha equipe · Enviar diretamente ao cliente), informa o WhatsApp da equipe,
                        confirma explicitamente o envio direto, vê a configuração antiga retida com explicação, e vê as pendências da cobrança com "Marcar como encaminhado ao cliente" e "Liberar reenvio"
RISCO / SUPERFÍCIE ...  5 / 2   (herda o piso do lote: CRÍTICO)   PISO §3.2 via a SPEC
ARQUIVOS (só estes) ..  components/auxiliares/PainelDeRotinas.tsx · app/api/dashboard/rotinas/route.ts ·
                        app/api/dashboard/auxiliaries/cobranca/pendencias/route.ts (novo) · …/cobranca/encaminhado/route.ts (novo) · …/cobranca/liberar/route.ts (novo)
INTERFACES QUE TOCA ..  CONTRATOS §1 (config) · §2 (colunas e estados do ledger) · §6 (rotas)
REFERÊNCIA ...........  interna: DS-001 §5 · `liberar-reenvio/route.ts` (padrão de rota) · a 098 (`resolveSessionCompany` fail-closed) · externa: WhatsApp Business Policy (a supressão é terminal: `suprimido` não libera)
GATES ................  `npx tsc --noEmit` · `node scripts/rotina-mora-no-auxiliar.test.mjs` (continua verde) · `node scripts/a-cobranca-chega-a-quem-deve.test.mjs` (do desenhista, quando existir) ·
                        `npm run test:rotas-montam` (você criou rotas em app/) · G18 (IDOR: id de outro tenant → 404)
PENDÊNCIAS ...........  P-097-TELEFONE-BR-DUPLICADO (não crie uma 3ª cópia da regra do 9º dígito: só dígitos e comprimento 10–13)
FAIXA DE RELÓGIO .....  1h30–2h30
```

## Como trabalhar
1. **BLOCO 0:** remeça `PainelDeRotinas.tsx:85-125` e `:805-870` (MODOS_COM_MOTOR, o texto "ainda não está disponível", o placeholder) e `rotinas/route.ts:16-36`. Escreva o que achou.
2. **Seletor:** `MODOS_COM_MOTOR` = `test` ("Teste — envia para o meu número de teste") · `none` ("Somente relatório — não envia nada") · `equipe` ("Encaminhar para minha equipe — a atendente recebe o pacote pronto e repassa") · `cliente` ("Enviar diretamente ao cliente — o segurado recebe texto e boleto"). O comentário da SPEC-078 E.1 acima da constante é atualizado (📊 data 07/09/2026, `_entregar_cobranca_real` em `billing_collection.py`), não apagado. Campo `team_number` visível só em `equipe` (rótulo "WhatsApp de quem recebe o pacote (sua equipe)"). Em `cliente`: um bloco de confirmação com o texto "O cliente vai receber diretamente pelo WhatsApp da corretora. Cada parcela é cobrada uma vez; a resposta dele chega ao atendimento." e um checkbox que grava `confirmacao_cliente=true`; o botão de salvar fica desabilitado sem ele. Config com `send_mode` fora dos 4 (legado `approval`/`live`): a tela mostra um aviso ("Esta configuração é antiga e não envia nada. Escolha uma modalidade.") e o `<select>` fica sem valor selecionado até a pessoa escolher. O texto "Enviar direto ao segurado ainda não está disponível" SAI.
3. **Pendências da cobrança:** uma lista dentro da seção de cobrança (só quando a rotina é de cobrança), carregada de `GET /api/dashboard/auxiliaries/cobranca/pendencias`, com colunas humanas: cliente · seguradora (mapeie `portal_key` → nome como `NOME_DA_SEGURADORA` faz; não invente nomes) · parcela/recibo · para quem foi (…últimos 4) · quando · situação em português (`entregue_equipe` → "Entregue à equipe — falta encaminhar ao cliente" · `parcial` → "Texto foi, PDF não" · `incerto` → "Não sei se saiu — precisa de conferência" · `contestado` → "Cliente respondeu: {retorno}" · `suprimido` → "Cliente pediu para não receber" · `falhou` → "Não saiu" · `adiado` → "Adiado — tenta na próxima execução") · ações: "Marcar como encaminhado ao cliente" (só em `entregue_equipe`) e "Liberar reenvio" (com campo de motivo; desabilitado em `suprimido` e `incerto`, com o porquê ao lado). Estados vazios ("Nenhuma pendência") e erro ("Não consegui carregar as pendências") escritos.
4. **Rotas** (CONTRATOS §6): `pendencias` GET, `encaminhado` POST, `liberar` POST — `resolveSessionCompany()` (401 sem sessão), `.eq('company_id', ctx.companyId)` em toda query, `.eq('send_mode','real')`, `404` quando o id não é do tenant (o UPDATE com `.eq('company_id')` retorna 0 linhas → 404), `409` para `suprimido`/`incerto` em `liberar` e para status fora do permitido em `encaminhado`, `400` sem motivo em `liberar`. `encaminhado_por` = o `userId` do contexto de sessão (veja o que `resolveSessionCompany` devolve). Respostas com mensagem em português. Comentário de cabeçalho no padrão do repositório (por que existe, o que nunca faz).
5. **`rotinas/route.ts`:** `normalizeBillingConfig` aceita `['test','none','equipe','cliente','approval','live']` (os dois últimos preservados como estão — quem os retém é o Python), `team_number` só dígitos (10–13), `confirmacao_cliente` booleano.
6. Rode: `npx tsc --noEmit` · `node scripts/rotina-mora-no-auxiliar.test.mjs` (a asserção "nenhum modo sem motor (`live`, `approval`)" continua verde; se alguma asserção dele ficar vermelha por ter mudado de fato, diga qual e por quê — não a edite) · `npm run test:rotas-montam` · e o `.mjs` do desenhista quando existir.
7. Entregue: diff resumido por arquivo · BLOCO 0 · saída dos comandos · **o que viu FORA do escopo** (obrigatório) · pendente.
⛔ Não narre "está funcionando". Cole a saída do comando.
