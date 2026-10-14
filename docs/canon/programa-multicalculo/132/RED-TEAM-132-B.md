modelo: claude-opus-5-5

# RED TEAM · SPEC-132-B · A Cotação Rápida

> 14/10/2026 · branch `spec/132-o-chat-e-a-cotacao` · código lido em `618ba14` (o HEAD chegou a `41e6896` durante o
> trabalho; os 5 commits novos são só da fatia E: `proposta_html.py` (a faixa de exemplo), o script e o teste dos
> exemplos, e nenhum mexe nos achados abaixo) · somente leitura no código · dublês do repositório: `BancoU1`, `RoboDuble`
> do motor com as rodadas reais da fixture, Redis em memória, LLM dublê pelo `tool_node` REAL, `create_agent_graph`
> REAL, `SmithWorker._processar` REAL, `publicar_cotacao` REAL, `ArtifactService.abrir_compartilhado` REAL.
> Arquivo dos ataques (fora do repositório):
> `C:\Users\amand\AppData\Local\Temp\claude\c--Users-amand-Projetos-AUTOBROKERS-RESULTA-AutoBrokers-FIX\225fe662-4bfa-4f52-90eb-cec15851686d\scratchpad\rt132b\test_rt_132b.py`
> (saída inteira em `saida.txt`, na mesma pasta). Comando:
> `cd backend && bash …/pesado.sh python -m pytest …/rt132b/test_rt_132b.py -q -s -p no:cacheprovider -W ignore`
> → 📊 `7 passed` (os testes IMPRIMEM o que o produto fez; cada número abaixo vem dessa saída).

## VEREDITO: QUEBREI — 3 BLOCKERS

O isolamento entre corretoras, a confirmação de uso único e a identidade injetada pelo `tool_node` **resistiram** a todos
os ataques. Quebraram três coisas: o que a página afirma ao segurado e o que o chat afirma ao corretor.

---

## B-1 · A página de venda diz ao segurado uma "economia" que não tem prova, e o prêmio com ponto decimal vale 100 vezes mais (BLOCKER)

**Teste do produto:** muda o que chega ao SEGURADO (o número na página). SIM, então é BLOCKER. Fere o §4.4 da SPEC ("só
com a apólice atual lida… nunca sem prova"), a D-132B-02 e a mutação 5.

**Causa:** `backend/app/services/cotacao/pedido_da_conversa.py:303-313`
```python
seguradora_atual = d.get("seguradora_atual")          # o que o MODELO escreveu
if seguradora_atual:
    apolice_atual = {"seguradora": str(seguradora_atual)}
    premio = d.get("premio_atual_anual")
    ... float(str(premio).replace(".", "").replace(",", "."))   # "4200.00" -> 420000.0
    apolice_atual["origem"] = "documento" if ficha is not None else "corretor"
    situacao = "novo_com_apolice"
```
1. Basta o modelo preencher `seguradora_atual` + `premio_atual_anual`, sem nenhuma apólice anexada, e a situação vira
   `novo_com_apolice`. A página então mostra a economia (`proposta_cotacao_html._economia`, que só olha a `situacao`).
2. O parser apaga TODO ponto, inclusive o decimal. Um LLM escreve `"4200.00"` (é o formato natural de JSON), e o produto
   lê 420.000.
3. O resumo que o corretor confirma (`pedido_da_conversa.py:561-562`) mostra só `- Seguro atual: Seguradora X`. **O
   valor nunca aparece para o corretor**, então a confirmação explícita (D-132B-03) não o protege.
4. Mesmo com a apólice anexada, o prêmio sai do MODELO, não da ficha lida, e vai gravado com `origem: "documento"`.

**Reprodução (📊 saída do RT1/RT2):**
```
RT1 '3500.50' -> 350050.0 novo_com_apolice corretor
RT1 '4200.00' -> 420000.0 novo_com_apolice corretor
RT1 '3.500,50' -> 3500.5          (controle: o formato brasileiro funciona)
RT2 anexo na conversa? False
RT2 '4200' no resumo do corretor? False
RT2 economia na pagina: ['R$ 417.571 a menos por ano</h2><p>Em relação ao seu seguro atual, que custa R$ 420.000 por ano, …']
```
O HTML veio de `abrir_compartilhado(token)`, isto é, da página que o cliente abre.

**Conserto mínimo:** a economia só existe com `ficha is not None` e o prêmio LIDO da ficha (o declarado nunca vira
`novo_com_apolice`). O parser decimal tem de ser o do produto (`AP.dec` / `premio_atual`), e não um `replace(".", "")`.
Quando houver prêmio, ele aparece no resumo para o corretor conferir. Guarda: a mutação 5 com `premio_atual_anual` e SEM
anexo tem de ficar vermelha, e `"4200.00"` tem de ser lido como 4200.

## B-2 · O recálculo responde "Recalculado com a franquia reduzida" e mostra a tabela e o link de ANTES (BLOCKER)

**Teste do produto:** muda o que chega à CORRETORA (a resposta no chat). Ela manda ao cliente um link que acredita ser o
da franquia reduzida, e o link mostra os preços antigos. SIM, então é BLOCKER.

**Causa:** o run do ajuste (`workflow.py:308-357`) chama `publicar_cotacao(company_id, pedido_id)`, que monta o modelo
pelo `CMP.comparar`/`CMP.opcoes`. Por desenho, esses dois **nunca** incluem o cálculo `opcao='ajuste'`
(`comparacao.py:8`: "ajuste NUNCA se mistura"). O modelo sai idêntico, então `link_que_ainda_vale` devolve o MESMO link.
`texto_pronto(..., ajuste=rotulo)` ainda acrescenta "(Recalculado com …)" na frente da tabela velha. O teste da B1
(`test_o_ajuste_recalcula_pela_porta_e_responde_na_conversa`) não roda o run do ajuste, e o dublê de publicação dele
ordena TODAS as ofertas do pedido, inclusive as do ajuste. Por isso o defeito ficou mascarado.

**Reprodução (📊 RT3, motor real + worker real + B2 real):**
```
RT3 resposta do ajuste: Recalculando com a franquia reduzida no seu Agger — volto aqui com o resultado em 1 a 2 minutos.
1ª: Pronto: 13 seguradoras responderam.
    | Recomendada | Azul | 3x R$ 809,77 sem juros | R$ 2.429,31 | R$ 5.128,00 |
2ª: Pronto: 13 seguradoras responderam. (Recalculado com a franquia reduzida.)
    | Recomendada | Azul | 3x R$ 809,77 sem juros | R$ 2.429,31 | R$ 5.128,00 |
RT3 tabela igual? True        RT3 mesmo link? True
RT3 calculo de ajuste: ['fechado']   premios do ajuste (banco): [117.63, 264.94, 1313.34, 1509.92, ...]
```
O cálculo do ajuste FECHOU com preços diferentes no banco, e nenhum deles chegou ao corretor.

**Conserto mínimo:** a resposta do run de ajuste sai das ofertas do `ajuste_calculo_id`: a tabela da opção ajustada e o
N das que responderam ao recálculo. Ou a página ganha a versão ajustada como opção, e aí o modelo muda e o link também.
O que não pode é imprimir "Recalculado com" sobre o quadro antigo. Guarda: rodar o run do ajuste no fio e exigir que a
linha mostre um preço das ofertas do ajuste.

## B-3 · A aba Cotações entrega ao cliente o link de quem saiu da corretora, e também o link já vencido (BLOCKER)

**Teste do produto:** muda o que chega ao SEGURADO. O "Quero fechar" vai ao WhatsApp de um ex-funcionário, ou o cliente
abre um link morto. SIM, então é BLOCKER. A J-P2 da 131-B ("quem saiu não recebe o Quero renovar") vale aqui, e a própria
B2 já cumpre essa regra. É a aba que a contorna.

**Causa:** `backend/app/api/cotacoes.py:541-546`
```python
info = do_run(run)
if info.get("url"):
    return {"url": info["url"], ...}        # o link do run, para sempre: sem conferir share, validade ou quem atende
```
O "Ver apresentação" e o "Enviar pelo WhatsApp" (`envio`) **nunca** voltam à `publicar_cotacao`, que é quem confere o
membro ativo (`membro_para_o_cliente`) e a validade do link (`link_que_ainda_vale`). A lista guarda 90 dias, e o link vale
`dias + folga`.

**Reprodução (📊 RT7):**
```
RT7 pagina aponta p/ o corretor? True
RT7 depois que saiu: mesmo link? True | a pagina servida ainda manda ao numero dele? True
RT7 controle publicar_cotacao: link novo? True | numero dele? False     ← a B2 faz certo
RT7 link vencido: a aba devolve o mesmo? True | o link abre? False | wa.me leva o link morto? True
```

**Conserto mínimo:** `apresentacao()` chama `publicar_cotacao(cid, pid, pessoa_user_id=<solicitante do pedido>,
primeiro_nome=…)`. Quando nada mudou, o reaproveitamento já devolve o MESMO link sem gravar nada (o fio prova isso). Hoje
a função também passa o `uid` de QUEM CLICA como `pessoa_user_id` (`cotacoes.py:527`), e a página passa a dizer que o
gestor "fez a sua cotação". Tem de ser o solicitante enquanto ele estiver ativo e, se não estiver, a corretora.

---

## O QUE NÃO QUEBREI (com a medição)

| ataque | resultado 📊 (RT4/RT5/RT6) |
|---|---|
| corretora B usa o `confirmacao_id` de A | "Essa confirmação não vale mais…" (a chave tem o `company_id`) |
| colega da mesma corretora usa o id de A | "…é de outra conversa ou de outra pessoa" (e o id **não** é consumido) |
| A usa o próprio id noutra conversa | recusado sem consumir; depois A dispara na conversa certa |
| colega com o `session_id` da conversa de A | "Esta conversa é de outra pessoa da equipe" |
| id forjado `0123456789abcdef` | "não vale mais" |
| modelo injeta `company_id/user_id/conversation_id/session_id` de B no disparo | descartados pelo `tool_node` (`nodes.py:3667-3677`); 📊 1 pedido, de A, solicitante A; 1 run, na conversa de A |
| reuso do mesmo id | "Essa cotação já foi disparada" (o `DEL` só deixa passar um) |
| `cotacao_ajustar` com o pedido de A pela corretora B | "Não achei essa cotação na sua corretora" (o guarda do fio já cobre) |
| `GET/POST /api/cotacoes/<id de A>` com a sessão de B | 📊 404 · 404 · 404 |
| busca de B por "Fulana" e pelo CPF de A | 📊 0 · 0 |
| campo estranho no corpo · sem a chave interna | 📊 400 · 401 |
| XSS no nome (`<img/src=x/onerror=…>`) | o nome é recusado ("nome completo"), nada é calculado |
| XSS no carro (`Onix <script>alert(2)</script>`) | escapado na página (`<script>alert(2)` ausente do HTML servido); o React escapa na aba; o markdown do chat não tem `rehype-raw` |
| CPF cru no run, na página, na API | run: `***.***.***-25`; página e mensagem: sem o CPF; API: mascarado |
| apólice de outra corretora (`usar_apolice_anexada`) | `anexos_da_conversa` só lê path com prefixo `<company_id>/` (e o `chat.py:858` já recusa na entrada) |
| WhatsApp de outra corretora ou do número-assistente na página | `_whatsapp_da_anfitria` só lê a marca publicada e `purpose='attendance'` DESTA corretora |
| "anos" sem `founded_year`, nota Google sem `google_confirmado` | só de `int` do perfil / da config confirmada (`proposta.py:563,569`) |
| `Concluido` quebra outro workflow | é aditivo: quem devolve `str` continua igual (`smith_worker.py:511-516`; `concluir(resultado=None)` grava `{}`, como antes) |
| run grava 2 mensagens | id uuid5(run+tipo) + `23505`: 📊 1 mensagem por run no fio; o "não terminou" nunca depois da "pronta" |
| "salvar só o modo" apaga as outras regras | a tela manda o rascunho inteiro (`ConfigurarCotacaoEQcm.tsx:89-106`); a chave editável ausente volta ao padrão, e isso é o desenho |

## PENDÊNCIAS (não mudam um byte hoje, ou dependem de o modelo errar)

1. **P-RT-1** · CPF com ESPAÇOS (`529 982 247 25`) passa pelo cinto `sem_documento_inteiro` e pelo `resumo_do_cliente`
   (`\d{6,}`). 📊 RT5: "CPF com espacos na saida? True". Só acontece se o modelo puser o documento na descrição do carro ou
   no nome do condutor. Nesse caso ele iria em claro para `work_runs.input_payload.risco` e para a aba.
2. **P-RT-2** · A capability é ligada **para todas as corretoras** pela migration (binding global do papel core). Ela
   não depende de o aplicativo "Cotação Rápida" estar instalado. Cálculo que sai do prédio, ligado em toda corretora no
   deploy: registrar a decisão.
3. **P-RT-3** · A faixa da comissão de entrada (`COMISSAO_ENTRADA_FAIXA`) sai do padrão do PRODUTO, e não do
   `autonomo_minimo` da corretora. Uma corretora com o autônomo mais alto grava uma entrada que o `_coerente` depois
   descarta em silêncio.
4. **P-RT-4** · Os links antigos não são revogados quando sai uma versão nova da página: o cliente que já recebeu o link
   do ex-funcionário continua com ele. Isso vem da 131-B, mas, com a B-3 consertada, deixa de piorar.

## MAIOR LACUNA

Os guardas da B1 provam a **forma** (há tabela, há link, há 1 mensagem), mas não o **conteúdo contra o banco**: a linha
do ajuste não é comparada com as ofertas do ajuste, e a economia não é comparada com a presença de uma apólice lida.
Os dois blockers de conteúdo passaram por aí.

## CONFIANÇA E O QUE FICOU POR MEDIR

Alta nos três blockers: cada um foi reproduzido pelo caminho real, de ponta a ponta, com a linha de controle (RT1 com o
formato brasileiro, RT7 com a B2 direta). Ficaram por medir: a tela do chat (o polling e o prazo da 132-A, que é escopo
do juiz da 132-A), o reenvio pelo atalho do WhatsApp da 132-C, o canário real e o desenho visual (escopo do juiz de
design).

## NOTA: 62 / 100

O isolamento está 📊 sólido em 15 ataques. A nota cai pelos três defeitos que chegam ao cliente ou ao corretor como
afirmação falsa: a economia inventada (e ×100), o "recalculado" com o preço antigo, e o link de quem saiu ou já vencido.
