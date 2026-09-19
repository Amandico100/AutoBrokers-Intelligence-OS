# SPEC-EXTRA-001.5.1 — A base de planos chega ao cliente

> **Proposta**, escrita em 18/09/2026 pelo gerente Opus 5, para o **Fable 5.1 REVISAR, EMENDAR e só então
> EXECUTAR** sob o PROTOCOLO AUTOBROKERS AAA v12.2, modo GERENTE.
> **Base:** `origin/main` = `e0f51ee` (a EXTRA-001.5, entregue em 18/09).
> **Antecessora:** `SPEC-EXTRA-001.5-o-agente-sabe-o-que-cada-plano-cobre.md` · relatório
> `reports/SPEC-EXTRA-001.5-EXECUTION-REPORT.md` · inventário `reports/SPEC-EXTRA-001.5-INVENTARIO-DA-FILA.md`.

---

## 0. Por que esta SPEC existe

A EXTRA-001.5 entregou a base de planos, a Skill dos cinco estados, as duas migrations, a tela e 13 guardas. O
juiz deu 72, o conserto fechou os quatro blockers, a confirmação deu 88. **E o produto não funciona em produção.**

📊 **Medido em 18/09/2026 contra a API implantada**, com a chave interna:

```
GET /api/assistance-plans/cobertura   ->  HTTP 200 em 1,99 s
GET /api/assistance-plans/fila        ->  HTTP 500 em 1,82 s      🔴
```

A causa é uma só e explica quase tudo o que o Founder viu na tela: **o arquivo do vocabulário de serviços não
está dentro da imagem do backend.** Ele mora em `docs/canon/providers/susep/servicos-de-assistencia.json`, e o
`backend/Dockerfile` é `WORKDIR /app` + `COPY . .` **de dentro de `backend/`** — a pasta `docs/` não entra.
📊 O `/health` de produção publica `code_files: 396`, que é exatamente o número de `.py` em `backend/app`.

O resolvedor de caminho (`assistance_plans_base.py:128-147`) tenta três lugares, e **os três estão fora da
imagem**: a variável `AUTOBROKERS_REPO_ROOT` (não existe em produção), a subida da árvore procurando `docs/canon`
(não existe), e o caminho histórico `parents[4]` (idem). Resultado: `VocabularioNaoEncontrado`.

**O efeito em cascata, medido:**

| onde | o que acontece hoje em produção |
|---|---|
| `GET /fila` | 500. `_termos_do_servico` (`api/assistance_plans.py:134`) lê o vocabulário |
| a tela de Conhecimento | o front não testa `r.ok` (`route.ts:42`) nem `fila.ok` (`KnowledgeClient.tsx:108`), então o erro vira `itens=[]` e a tela escreve **"Nada esperando revisão"** — com o contador do topo dizendo 60 |
| 🔴 **a Skill de cobertura** | `servico_canonico` (`cobertura_e_assistencia.py:499`) é a PORTA que reconhece a pergunta. Ela levanta a exceção, o composer captura tudo (`policy_answer_composer.py:576`, `except Exception`) e loga `Skill de cobertura indisponível` — **o produto volta ao caminho antigo, com o defeito do "Sim" para tudo, em silêncio** |

🔴 **Nem o juiz nem a confirmação pegaram, e a razão importa:** os dois rodaram na árvore de desenvolvimento,
onde `docs/` existe. É o mesmo tipo de cegueira que o `CLAUDE.md` §9.1 descreve — "build verde não é prova de
que a aplicação sobe" —, agora na forma "teste verde na árvore não é prova de que roda no contêiner".

E há mais, medido no mesmo dia (§2). **Esta SPEC fecha tudo isso de uma vez.**

---

## 1. O outcome, em três linhas

```
O corretor pergunta no chat e o segurado pergunta no WhatsApp. Os dois recebem a MESMA verdade,
em DUAS vozes: o corretor com a fonte (documento e página) e formatação de leitura; o segurado em
conversa, sem citação. A base responde por consulta ao banco, nunca baixando PDF. E o que o agente
NÃO souber vira tarefa visível, para virar conhecimento na próxima destilação.
```

---

## 2. Os doze defeitos, cada um com a medição

| # | defeito | medido em 18/09 | efeito para quem usa |
|---|---|---|---|
| **D1** 🔴 | o vocabulário está fora da imagem | `/fila` → 500; Dockerfile copia só `backend/` | **a Skill inteira está desligada em produção** |
| **D2** 🔴 | o front esconde o erro | `route.ts:42` não testa `r.ok`; `catch` devolve objeto sem `itens`; `KnowledgeClient.tsx:108` não testa `fila.ok` | a tela mente: diz "Nada esperando revisão" quando a chamada falhou |
| **D3** | o contador conta a página, não a base | `TETO_DA_FILA = 60` (`api/assistance_plans.py:55`); a base tem **81** linhas | dois números diferentes na mesma tela |
| **D4** | a fila não tem ordem estável | `fila_de_curadoria` (`assistance_plans_base.py:1100`) sem `ORDER BY` | quais 21 linhas ficam de fora do teto muda a cada abertura |
| **D5** | a fila baixa 24 PDFs em série | 📊 **65,3 s** para montar a fila | a tela trava a cada abertura |
| **D6** | não existe publicação em lote | nenhum script chama `publicar_servico`; só a tela | 81 linhas = 81 cliques, 60 por vez |
| **D7** | 4 serviços presos sob planos em `rascunho` | Mapfre condomínio 1, Mapfre residencial 1, Tokio auto 2 | aprovar não funciona: o plano pai só sobe de `proposto` |
| **D8** | 5 planos em `rascunho` sem motivo gravado | `plano_para_rascunho` só escreve o motivo no log | ninguém sabe por que foram recusados |
| **D9** | o botão morre quando o PDF não abre | `FilaDeCuradoria.tsx:151` `disabled={… || !i.texto_da_pagina}` | falha de MinIO vira botão cinza sem explicação |
| **D10** | o texto é único para os dois canais | `_texto()` (`cobertura_e_assistencia.py:232`) não sabe o canal; o guarda de `nodes.py:305` devolve `rendered` sem canal | a citação e o "no plano **dele**" chegam ao segurado no WhatsApp |
| **D11** | o gancho não nomeia a atendente | `infocap_tool.py:789` não passa `atendente=` | sai "nossa equipe", nunca a pessoa |
| **D12** | o que o agente não sabe morre no turno | `capability_gaps` = 0 linhas; nenhuma escrita a partir de cobertura | nada guia a próxima destilação |

---

## 3. O que NÃO é defeito, e precisa ficar escrito

O Founder levantou três preocupações. Duas estão corretas (D5 e D10, acima). A terceira é um mal-entendido que
esta SPEC tem de **provar por teste**, para não voltar:

> 🔴 **A resposta ao cliente NÃO baixa PDF. Nunca baixou.**

📊 O caminho da resposta é: a pergunta entra, `servico_canonico` reconhece o serviço (leitura de um JSON em
memória), `buscar_servico` faz **uma consulta ao Postgres** com índice, e a frase é montada. **Zero download,
zero chamada ao modelo para consultar a base, zero embedding.**

Quem baixa PDF é outra coisa, e só duas:

```
a TELA DE CURADORIA   baixa o PDF para mostrar a página a quem revisa     ← é o D5, e conserta-se
o EXTRATOR            baixa o PDF UMA vez por documento, na coleta        ← roda fora do atendimento
```

E o RAG (as cartas e os pedaços das condições gerais) é uma terceira camada, usada para a **prosa** — barata:
📊 1 embedding + 2 buscas vetoriais, ≤ 24 pedaços, ≈ 24 KB de contexto.

**As três camadas, e para que serve cada uma:**

| camada | responde | custo por pergunta | estado |
|---|---|---|---|
| **base de planos** (001.5) | o veredito: tem/não tem, limite, página | 1 consulta SQL | 81 linhas, 0 publicadas |
| **cartas do RAG** | a prosa: como se explica isso | 1 embedding + 2 buscas | 5.561 de 4 seguradoras |
| **pedaços do documento** | o texto literal do contrato | na mesma busca | 42.091 pedaços, 8 seguradoras |

🔴 **A SPEC tem de deixar isso provado por um guarda que conta as chamadas de I/O do caminho da resposta.**
Se alguém um dia fizer a resposta abrir um PDF, o guarda fica vermelho.

---

## 4. O isolamento entre corretoras — o que foi medido, e o que a SPEC guarda

O Founder pediu: o conhecimento **global** é de todas; o conhecimento **da corretora** é só dela; e nada vaza.

📊 **Medido em 18/09, e hoje está certo:**

```
conhecimento GLOBAL   knowledge_cards (18.715) e normative_documents (194): SEM coluna de corretora
                      coleção Qdrant `autobrokers_global`, lida por toda corretora
                      insurer_assistance_plans (81 linhas): SEM company_id (o guarda M-A4 prova)
conhecimento DA CORRETORA  documents: company_id NOT NULL — 17 · 2 · 1 nas três corretoras
                      coleção Qdrant `company_<id>`, uma por corretora
a soma                search_service.py:531 busca nas DUAS e soma, com orçamento próprio para cada
```

📊 **Não há vazamento hoje, e por um motivo que precisa virar guarda:** a tabela `agents` **não tem** a coluna
`collection_name` que o `graph.py:203` tenta ler. Ela devolve `None` sempre, e a coleção cai no padrão da
própria corretora. A cerca `colecao_permitida` (`graph.py:218`) existe e nunca precisa agir.

⚠️ **O risco é estrutural e está registrado** (P-098-RAG-COLECAO-DO-AGENTE): o tenant do RAG é o **nome da
coleção**, não um filtro por `company_id` no payload. Se a coluna voltar a existir, ou se alguém configurar uma
coleção à mão, vaza sem erro. **Esta SPEC não conserta isso** (é da SPEC-098), **mas acrescenta o guarda que
prova o isolamento hoje**, com duas corretoras reais, para que a regressão seja barulhenta.

🔴 **E muda a tela de lugar.** Hoje a curadoria da base global vive em `Personalização → Conhecimento` da
corretora, misturada com os 17 documentos privados dela. Isso dá a impressão errada e dá a uma corretora o poder
de publicar o que vale para todas. A tela de curadoria passa a exigir **papel de administrador da plataforma**,
e a tela da corretora passa a **mostrar** a cobertura global em modo leitura, com uma linha dizendo de onde vem.

---

## 5. As unidades

### A · A cegueira (D1, D2, D3, D4, D9) — **primeiro, sozinha, porque sem ela nada mais existe**

1. **O vocabulário entra na imagem.** O arquivo passa a ser `backend/app/data/servicos-de-assistencia.json`,
   que é código e entra no `COPY . .`. O de `docs/canon/providers/susep/` continua existindo como **documento**
   e um guarda prova que os dois são **byte a byte iguais** (ou o de `docs/` vira um ponteiro, com a decisão
   escrita). O resolvedor passa a procurar primeiro dentro do pacote.
2. 🔴 **O guarda que reproduz o contêiner.** Copia SÓ `backend/` para uma pasta temporária, roda
   `python -c "from app.services.knowledge import assistance_plans_base as B; print(B.servico_canonico('tem carro reserva?'))"`
   e exige resposta. **Nasce vermelho com o código de hoje.** Este guarda é a entrega mais importante da SPEC.
3. **O erro aparece como erro.** `route.ts` testa `r.ok` e propaga `{ok:false, error}`; `KnowledgeClient.tsx`
   testa `fila.ok`; a tela mostra "Não consegui carregar a fila agora" com o motivo, **nunca** "Nada esperando
   revisão" por falha. O estado vazio honesto continua existindo para o caso de a fila estar mesmo vazia.
4. **O contador conta a base.** `itens_na_fila` passa a ser `count(*)` das linhas em `proposto`, e a tela diz
   "mostrando 60 de 81".
5. **Ordem estável:** `ORDER BY insurer_key, ramo, produto, plano, servico, id`.
6. **Botão cinza ganha motivo:** sem `texto_da_pagina`, a linha diz por quê e oferece "tentar de novo".

**GATE A:** a Skill responde numa árvore sem `docs/`; `/fila` responde 200 em produção; a tela mostra 81 e
carrega; o guarda do contêiner fica vermelho se o arquivo sair do pacote.

### B · A fila utilizável e a publicação em lote (D5, D6, D7, D8)

7. **A página sob demanda.** A fila devolve as linhas **sem** o texto da página; o texto é buscado quando o
   revisor abre aquela linha. 📊 De 65,3 s para o tempo de uma consulta. Um cache curto por documento evita
   rebaixar o mesmo PDF na mesma sessão.
8. **Publicação em lote, por comando.** `backend/scripts/publicar_linhas_da_base.py`, com
   `--seguradora`, `--ramo`, `--ids`, `--revisor <uuid>`, `--dry-run` por padrão e `--aplicar` para valer.
   Publica a linha **e o plano pai**, recusa o que não estiver em `proposto`, e imprime o que fez.
   🔴 Ele usa o escritor que já existe (`publicar_servico`), nunca SQL solto.
9. **Os 4 serviços presos:** ou o plano pai volta a `proposto` com motivo, ou a publicação em lote os promove
   junto. A decisão vai escrita.
10. **O motivo do rascunho fica gravado**, num campo que a fila mostra. Sem campo, a migration cria um.

**GATE B:** a fila abre em menos de 3 s; o script publica 10 linhas em seco e depois de verdade, com VERIFY;
nenhuma linha publicada sem revisor; os 4 presos saem do limbo.

### C · A resposta certa, por canal (D10, D11) — **o plano que o Founder já aprovou**

11. **`_texto()` passa a saber para quem fala**, com um parâmetro de canal, como `normalize_insurer_key` já faz
    com `para=`. Duas famílias de frase, o mesmo veredito.
    - **corretor:** mantém a citação, ganha negrito no veredito, o limite destacado e a fonte em linha própria.
    - **segurado:** segunda pessoa ("o seu plano"), frases curtas, **sem citação**, sem jargão de base.
12. **O guarda de `nodes.py` escolhe o texto do canal**, mantendo a regra que importa: nunca afirmar o que a
    base nega.
13. **Formatação no lugar que já existe:** uma linha em `CORE_BASE_PROMPT` e uma em `ATTENDANCE_BASE_PROMPT`
    (`backend/app/core/prompts.py`), dizendo o que fazer com o veredito. ⛔ **Nenhuma regra de escrita nova em
    outro lugar.**
14. **A opção 1 do Founder:** quando a base diz que não cobre, a resposta ao segurado **oferece o caminho da
    equipe na mesma mensagem**. E o gancho nomeia a atendente de verdade (D11): a fonte é o card Equipe; se não
    houver, "nossa equipe" continua sendo o texto, nunca um nome inventado.

**GATE C:** um par de teste por estado, nos dois canais: o do corretor traz documento e página, o do segurado
não traz nenhum dos dois; nenhuma frase ao segurado diz "dele"; o gancho nunca cita preço.

### D · A lacuna vira tarefa (D12) — **o pedido novo do Founder**

15. **Quando o agente não sabe, três coisas acontecem, nesta ordem:**
    - a resposta honesta sai (o estado `nao_sabemos_ainda` já existe);
    - **o humano é avisado** pela porta única do grupo que a EXTRA-001.3 construiu — o modelo 🆘 PRECISO DE
      AJUDA, com a pergunta e o caso, respeitando a guarda "humano já está aqui";
    - **a lacuna é gravada** em `capability_gaps`, que já existe e já aceita `gap_type='missing_data'`, com
      `fingerprint` (seguradora + ramo + produto + serviço), `frequency_count`, `first_seen_at`/`last_seen_at`.
      ⛔ Sem PII: a pergunta entra redigida, nunca crua.
16. **A lacuna aparece no portal admin**, ordenada por quantas vezes foi perguntada. É ela que diz qual
    seguradora destilar primeiro — por demanda, não por palpite.
17. ⚠️ **Escopo declarado:** esta unidade cobre a lacuna **de cobertura**. Estender a toda pergunta que o agente
    não souber é maior e vira SPEC própria; a SPEC deixa o mecanismo pronto para receber outros tipos.

**GATE D:** uma pergunta sem linha publicada grava exatamente uma linha em `capability_gaps` e manda exatamente
um aviso ao grupo; a segunda pergunta igual **não** cria linha nova, incrementa a contagem; o varredor de PII
não acha nada; a tela do admin lista por frequência.

### E · O isolamento provado (§4)

18. **Um guarda com duas corretoras reais** prova: a base de planos devolve o mesmo para as duas; um documento
    privado de uma **não** aparece na busca da outra; o conhecimento global aparece para as duas.
19. **A tela de curadoria exige papel de administrador da plataforma**; a tela da corretora mostra a cobertura
    em leitura, com a frase que explica que é conhecimento de todas.
20. **Um guarda prova que a resposta não faz I/O de arquivo** (§3).

**GATE E:** os três guardas verdes, cada um com a mutação que o deixa vermelho.

---

## 6. O que fica FORA, com o gatilho

- **A destilação das 4 seguradoras que faltam** — é trabalho do Founder com subagentes, e tem documento próprio:
  `docs/canon/PROTOCOLO-DE-DESTILACAO-DAS-SEGURADORAS.md`.
- **O filtro por `company_id` no payload do Qdrant** — é a SPEC-098 (P-098-RAG-COLECAO-DO-AGENTE). Esta SPEC só
  acrescenta o guarda que prova o estado de hoje.
- **A extração dos 26 pares seguradora × ramo sem linha** (empresarial, vida, equipamentos e garantia estão
  zerados) — depende da destilação e de uma rodada nova do extrator.
- **A destilação de conversas** (`DESTILADOR_TETO_POR_RODADA=0`) — outro trilho, com prazo próprio: o material
  cru vence ~27/10/2026.

---

## 7. O ELO — a afirmação que esta SPEC tem de provar

```
"o produto responde 'ainda não sabemos' a tudo PORQUE ninguém publicou linha"   ← o que se acreditava
"o produto responde 'ainda não sabemos' a tudo PORQUE a Skill nem roda"         ← o que foi medido
```

Medir A: a resposta em produção hoje, num caso real de cobertura. Medir B: `/fila` → 500 e o log
`Skill de cobertura indisponível`. 🔴 Medir que **B chega em A**: rodar o composer numa árvore sem `docs/` e
mostrar que o veredito volta `None` e o caminho antigo responde — e depois, com o conserto, que responde pela base.

---

## 8. Marcha proposta

```
RISCO ........ 8  (alcance 3: o segurado lê · reversibilidade 3: sai pelo WhatsApp · frequência 2)
SUPERFÍCIE ... 2  (lugares listados: 2 arquivos de backend, 3 de front, 2 prompts, 1 Dockerfile/pacote)
NÍVEL ........ CRÍTICO pela soma. Marcha PADRÃO com o elenco do crítico, como na 001.5
PISO ......... §3.2: texto ao segurado · e a migration do motivo do rascunho, se houver
FATIAS ....... 1 = A (a cegueira) · 2 = B (fila e lote) · 3 = C + D + E (canal, lacuna, isolamento)
TIME ......... gerente Fable no chat · 3 builders Opus 5 xhigh frescos · juiz Fable fresco · confirmação por
               gatilho · lente do dado NÃO (o outcome não é dataset novo)
FAIXA ........ 💭 fatia ≤ 60 min · juiz + conserto + entrega ≤ 45 min
```

🔴 **A regra que esta SPEC acrescenta ao rito, e que o Fable deve impor:** todo gate que prove comportamento de
produção roda **numa árvore que reproduz o contêiner** (só `backend/`), não na árvore de desenvolvimento. Foi a
cegueira que deixou a 001.5 passar por juiz e confirmação com o produto desligado.

---

## 9. Definição de conclusão

1. A Skill responde em produção: `/fila` 200, e uma pergunta de cobertura devolve um dos cinco estados.
2. O guarda do contêiner existe e fica vermelho se o vocabulário sair do pacote.
3. A tela mostra 81, carrega em segundos, e diz "não consegui" quando não consegue.
4. O script de lote publica com revisor, e os 4 presos saem do limbo.
5. O corretor recebe fonte; o segurado não recebe citação nenhuma, e nenhuma frase diz "dele".
6. Uma pergunta sem resposta grava uma lacuna e avisa o humano, sem PII e sem duplicar.
7. O isolamento entre corretoras está provado por guarda, com duas corretoras reais.
8. Um guarda prova que a resposta não abre arquivo nenhum.
9. Relatório com card, telemetria e a divergência de marcha escrita; push com a saída colada.

---

## 10. Emendas da revisão (Fable, 19/09/2026) — a proposta vale COM estas

| # | emenda | motivo medido |
|---|---|---|
| E1 | **Unidade D:** o aviso ao grupo sai no máximo **1× por lacuna (fingerprint) por corretora por dia**, e **só quando a pergunta veio do segurado** (WhatsApp). No chat do corretor a lacuna é gravada mas não avisa o grupo: o corretor já está lendo a resposta | sem teto, toda pergunta sem resposta vira 🆘 no grupo — é o ruído que a 001.3 acabou de matar |
| E2 | **Unidade B:** a publicação das linhas acontece **nesta execução**: um leitor read-only confere as 81 linhas contra a página (`LINHAS-CONFERIDAS.json`), o script de lote publica só as `PUBLICAR`, com o Founder como revisor | o Founder autorizou em 19/09; sem isso o produto continua mudo |
| E3 | **Unidade A-bis (fatia 2):** os três catálogos SUSEP (`seguradora-coenti.json`, `ramo-cogrupo.json` e o de siglas) saem de `docs/` para `backend/app/data/`, com o guarda do contêiner estendido a eles | 📊 `susep_ses_provider.py:100-109` lê por `parents[4]`; na cópia do contêiner os mapas vêm vazios e `familia_de_acionamento` devolve `UNKNOWN` no caminho vivo |
| E4 | `TOOL_GATEWAY_MODE` em produção é `shadow` (não `off`): a release da Skill continua inerte; nada muda na proposta | lido no ambiente do `smith-api` |
| E5 | O guarda do contêiner roda o subprocesso com env mínimo dummy (o `settings` do pydantic exige variáveis) | reproduzido em 19/09: a cópia sem `.env` falha antes de chegar ao vocabulário |
| E6 | A regra "todo gate de produção roda na cópia que reproduz o contêiner" entra no pacote do JUIZ com estas palavras: *"prove na cópia sem `docs/`, não na árvore"* | foi a cegueira da 001.5 |
