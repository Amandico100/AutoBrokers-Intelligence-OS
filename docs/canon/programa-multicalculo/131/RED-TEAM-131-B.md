# RED TEAM · SPEC-131-B · O aplicativo de Renovação

> 13/10/2026 · 🗡️ red team fresco (claude-opus-5-5), cego ao juiz · árvore `AutoBrokers-FIX`, branch `spec/131-B-o-aplicativo`,
> diff `c052550..af7ea4f` · read-only: nenhum arquivo de produto editado, nada commitado.
> Banco real: só `SELECT` (MCP, `dcajcvlzcjbmyapmklil`). Todo ataque que escreve rodou no dublê em memória da G4/G5
> (`BancoU1` + `InfocapDaCorretora`), com `get_supabase_client` trocado por um que EXPLODE. Nenhuma mensagem, nenhum
> Agger, nenhuma InfoCap real. Script: `scratchpad/redteam131b/test_ataques_131b.py` (fora do repositório).
> 📊 medido · 💭 ilustrativo.

## VEREDITO: QUEBREI

Três defeitos mudam o que chega ao segurado (§2). Isolamento entre corretoras, XSS, a forma do `wa.me` e o guarda do
telefone resistiram.

## BLOCKERS

### B1 · O envio reaproveita a página e manda o cliente ao WhatsApp de quem saiu ou apagou o número
- **Onde:** `backend/app/api/renovacoes.py:551-583` (`ultima_apresentacao`), usada no envio em `:792-795`. O número do
  dono fica CONGELADO no modelo publicado (`backend/app/services/multicalculo/proposta.py:1363`, `destino = dono.get("whatsapp") …`).
  `ultima_apresentacao` confere token, corretora, revogação, validade e o formato do modelo, mas nunca confere se o
  dono gravado na página ainda é membro ativo e ainda tem aquele número confirmado.
- **Reprodução** (dublê, motor real): apresentação publicada com o dono confirmado. Depois o dono sai da corretora (o
  `DELETE` de `app/api/dashboard/team/route.ts:235` apaga o vínculo), ou apaga o próprio número em Meu perfil. Outra
  pessoa clica "Enviar pelo WhatsApp".
- **📊 Saída** (`test_A1`, `test_A1b`):
  ```
  A1  {'mesmo_token': True, 'wa_no_link_enviado': ['5548988880001'],             <- número de quem SAIU
       'wa_numa_publicacao_nova': ['5548999990002']}                              <- o que uma publicação nova faria
  A1b {'mesmo_token': True, 'wa_no_link_enviado': ['5548988880001']}             <- o dono APAGOU o número; o link ainda o leva
  ```
  O "Quero renovar" do cliente vai para o WhatsApp pessoal de quem não está mais na corretora, ou de quem retirou o
  número. Isso contraria a D-131-43/44: o número só aparece confirmado e com a pessoa na corretora.
- **Exposição hoje:** 📊 0 membros com número confirmado e 0 renovações `apresentada` (SELECT de 13/10). O caminho está
  vivo e dispara no primeiro uso real.
- **Conserto barato:** em `ultima_apresentacao`, recalcular `P.membro_para_o_cliente(db, cid, dono)` e não reaproveitar
  a página quando `modelo.renovacao.dono.whatsapp` ou `fechar_com` diferem do de hoje (a função já devolve None e o
  envio republica).

### B2 · "Copiar a mensagem" copia o texto CURTO, e a mensagem completa nunca chega a ninguém
- **Onde:** `components/aplicativos/renovacao/useAcoesDaRenovacao.ts:103-105` copia `j.texto`. O backend
  (`renovacoes.py:797-799`) põe em `texto` a versão curta sempre que a completa passa de 500 caracteres. O campo
  `texto_completo` não é lido em nenhum lugar de `components/` (📊 `grep texto_completo components` → 0).
- **📊 Saída** (`test_A12`, o mundo do próprio fio):
  ```
  A12 {'len_texto': 235, 'len_completo': 617, 'copiar_devolve_texto_len': 235, 'copiar_igual_ao_curto': True}
  ```
  Na renovação canônica do fio, a mensagem completa tem 617 caracteres: as 2 opções, as parcelas, "Hoje você paga…
  a menos por ano", a assinatura e a validade. Ela é montada e descartada. O segurado recebe uma linha só, pelo link
  e também pelo "Copiar", e no caso "sem telefone" a tela mostra essa mesma linha.
- **Conflito de contrato:** a SPEC §2.1 B1 diz "o texto do link ≤ 500 + Copiar SEMPRE ao lado". O docstring da G4
  (`mensagem.py`, `texto` ≤ 700 "para o Copiar a mensagem") e o comentário da própria API (`renovacoes.py:47-48`, "a
  mensagem inteira vai no Copiar") dizem a mesma coisa. Só o hook da G2 diz "a MESMA mensagem que vai no link".
- **Conserto:** o "Copiar" (e o fallback "sem telefone") usa `texto_completo`. Ou o gerente registra a decisão
  contrária e apaga o `texto_completo`.

### B3 · O telefone do cliente pode sair de `contatos[]`, ou seja, de OUTRA pessoa
- **Onde:** `renovacoes.py:283-311`. `numero_de_whatsapp` junta `telefones[]`, **`contatos[]`**, `celular` e
  `telefone`, e depois escolhe o primeiro CELULAR entre todos (`:310`). O leitor canônico do produto,
  `backend/app/api/infocap_connector.py:4589` `_client_phone`, lê `telefone` e depois `telefones[]`, e **nunca**
  `contatos`. É um segundo leitor do mesmo dado, com regra diferente (CLAUDE.md §5).
- **📊 Saída** (`test_A5`, função real):
  ```
  fixo_do_cliente_e_celular_do_CONTATO: {'telefone':'(11) 3333-4444','contatos':[{'nome':'Contador X','celular':'11 98888-7777'}]}
      → '5511988887777'          <- o celular do CONTATO vence o telefone do próprio cliente
  estrangeiro_+1: '+1 415 555 2671' → '5514155552671'   <- vira um número brasileiro de DDD 14 (outra pessoa)
  ```
- **Teste do produto:** quando `contatos` guarda outra pessoa (o contador de uma PJ, um parente), o nome do cliente,
  o vencimento, o preço e o link da página vão para ela. ⚠️ INFERÊNCIA: o significado de `contatos` na InfoCap não foi
  medido. `/cliente` tem a chave `contatos` (📊 `infocap-schema-fingerprints.json`), mas não existe cache local do
  conteúdo e a InfoCap real estava proibida. Confiança média. A regra de preferência já diverge do leitor canônico
  mesmo sem essa medição.
- **Conserto:** reusar `_client_phone` (ou a mesma ordem: `telefone` → `telefones[]`), sem `contatos`. Só prefixar
  `55` quando o texto não começa com `+` e não é de outro país.

## PENDÊNCIAS (não mudam um byte hoje, ou dependem de decisão)

| # | o quê | onde | 📊 medição | destrava |
|---|---|---|---|---|
| P1 | Dois "Enviar" ao mesmo tempo publicam DUAS páginas. Os dois recebem 200, e um link enviado não é o `proposta_ref` (a "vista" dele nunca será ligada à renovação) | `renovacoes.py:786-806` | `A2 {'status':[200,200],'publicados':2,'proposta_ref_igual_a':[False,True]}`; eventos corretos (1 transição + 1 evento extra) | trava curta (lock por renovação) ou conferir o `proposta_ref` depois de `_apresentar` e mandar o link gravado |
| P2 | Link a menos de 2 dias do fim: cada clique em Enviar cria uma versão nova, e `proposta_ref` fica no token velho (`_apresentar` só grava em `calculada`) | `renovacoes.py:653-660` | `A3 {'tokens_enviados':['JD33LA','E1H1bb'],'proposta_ref':'UYzA45','versoes':3}` | `_apresentar` atualizar `proposta_ref` em `apresentada`/`enviada` (campo da máquina) |
| P3 | O Python aceita números que o CHECK do banco recusa, e a pessoa vê "não consegui fazer isso agora" (500) em vez da frase de correção. O caso mais comum é "+11 9…" (esqueceu o 55) | `perfil_do_membro.py:104-123` × `ck_company_members_whatsapp_e164` | `A7`: `+11987654321`, `11 6123-4567`, `+55 11 1234-5678`, `+351…` → BANCO_RECUSA→500 | a mesma regra do CHECK no Python (fixo `[2-5]`, só `+55`) |
| P4 | "Renova há N anos": um elo SEM `tipdoc` conta como apólice provada | `proposta.py:1182` (`or "A"`) | `A8 {'sem_tipdoc': 7, 'endosso': None}` | exigir `tipdoc == "A"` explícito (CDC art. 37: sem prova, sem frase) |
| P5 | Ausências cruzadas: A fora com B cobrindo, B fora com A cobrindo, no mesmo período. A sobreposição só é conferida contra as ausências da PRÓPRIA pessoa, e `_com_o_substituto` não confere se o substituto também está fora, então o aviso vai a quem está de férias | `perfil_do_membro.py:212-214`, `qual_agger.py:283-284` | por leitura; o ataque no dublê parou antes (`membro_ativo` do dublê recusou o DONO) | recusar substituto ausente no período |
| P6 | Qualquer membro ativo (inclusive `attendant`) vê "todas" e envia qualquer renovação da corretora. Não há travessia entre corretoras | `app/api/renovacoes/route.ts:22`, `comum.ts:34-57` | `A10 {'todas_itens':1,'envio_por_nao_dono':200}` | decisão do Founder: quem pode enviar a renovação de outra pessoa |
| P7 | Instalar = ligar a madrugada: um `POST` sem corpo em `/api/dashboard/auxiliaries/<id>` instala (o `action` padrão é `install`), e a confirmação existe só na tela. Exige papel admin + mesma origem e é idempotente (`dup`), então o clique duplo não duplica nada | `app/api/dashboard/auxiliaries/[auxiliar]/route.ts:25`, `tenant-auxiliary-store.ts:138` | por leitura; o único chamador de `installTenantAuxiliary` é essa rota | aceitar como está, ou exigir `confirmo:true` no servidor para slugs de `INSTALAR_JA_LIGA` |

## O QUE TENTEI (e não quebrou)
- **IDOR / isolamento:** todas as rotas Next tiram `company_id`/`user_id` da sessão (`comum.ts:23-31`, `meu-perfil`,
  `equipe/situacao` com `write:true`). O backend exige a chave interna (📊 `A10 sem_chave → 401`) e filtra por
  corretora em `por_id`, `calculos_e_ofertas` (solicitante), `ultima_apresentacao`, `aplicativo_ligado`, ausências e
  WhatsApp. O fio, com outra corretora, dá 404/vazio (rodou dentro do A11). Um corpo com `estado` é recusado
  (📊 400). `aggers-da-equipe`: o admin não conecta o Agger de outra pessoa (403).
- **`wa.me`:** um texto com `&`, `#`, `\n`, `?text=…&phone=`, emoji e `%0A` volta idêntico, com uma chave só (📊 `A6`).
  O nome do cliente na mensagem passa por `_primeiro` (só letras). O host é sempre `wa.me`, e o front só abre
  `https://wa.me/`.
- **Telefone em log/banco:** minha mutação (o envio passa a logar o número) deixa o teste do fio VERMELHO (📊 `A11`).
  O guarda atravessa o fio e carrega o motor real.
- **XSS na `/r/`:** cliente `<img onerror>`, dono `<svg onload>` e marca `"></title><script>` foram escapados. A página
  tem exatamente 2 `<script>`: o JSON e o do hash constante (📊 `A4`). `_json_para_html` troca `<`/`>`/`&`. A prévia
  (og/PNG) não leva nome, vencimento nem documento (`_previa_da_renovacao`).
- **"N anos" forjável pelo banco/tela:** `numero_inteiro` no render e `int()` no bloco. A frase vem só da cadeia `nosnum_ren`
  (exceto P4).
- **"Quero renovar" para número não confirmado:** `membro_para_o_cliente` exige `confirmado_em`, e o CHECK
  `ck_company_members_whatsapp_confirmado` impede confirmação sem número. O GET de Equipe devolve só um booleano.
  Ninguém grava o número de outra pessoa (`_so_a_propria_pessoa`).
- **Ausência:** período invertido (código + CHECK), a própria pessoa como substituta (código + CHECK), substituto de
  outra corretora (código + FK composta `(substituto_user_id, company_id)`) e membro comum marcando a ausência de outro
  (`_e_admin`) são todos recusados.
- **"Com qual conta":** só `servico == "renovacao"` lê `conta` (`qual_agger.py:228-236`). Cotação e QCM não mudam, e
  `EDITAVEL_POR_SERVICO["cotacao"]` não aceita `conta`. Com "corretora" e sem o Agger dela conectado, sai um aviso
  (`_AVISO_SEM_GLOBAL`), sem desvio silencioso. O substituto só muda o AVISO, não a conta.
- **Fila de atendimentos:** não havia arrastar antes (📊 `git show c052550` → 0 `drag`). O teto de 50 por coluna, a
  chave de preferência e o "esconder coluna vazia" (`esconderSeVazia:true`) se mantêm.
- **Redirect de Serviços:** 📊 `multicalculo_config` = 0 linhas e `tenant_auxiliaries` de renovação = 0 (13/10). Todas
  as chaves da tela antiga existem na Configurar nova (contagem por chave). A rota PUT segue com o porteiro.
- **Catálogo:** 📊 `renovacao-maxima` `is_active=false`/`coming_soon`; `renovacao`, `cotacao` e `quem-cobra-menos`
  ativos; colunas novas aplicadas.

## O ELO MAIS FRACO
O reaproveitamento da página no envio (`ultima_apresentacao`). Ele economiza uma versão, mas congela o "quem atende" num
momento em que esse dado ainda pode mudar.

## NOTA: 72/100 · confiança: alta em B1, B2, P1-P4 (reproduzidos no motor real); média em B3 (o significado de `contatos` não foi medido)
