# Pendências — o que ficou de fora, e o que destrava cada coisa

> **Documento vivo.** Toda SPEC que terminar deixa aqui o que não coube nela.
> **Nada sai desta lista sem estar feito ou sem uma decisão registrada.**
>
> **v1.0 · 02/08/2026** · criado durante a SPEC-064, a pedido do Founder.
> Marcação de números: 📊 medido · 💭 ilustrativo (CLAUDE.md §12.1).

---

## Como ler

| Coluna | O que significa |
|---|---|
| **Destrava** | o que precisa acontecer para sair desta lista |
| **Dono** | 🧑 Founder (ação física, decisão, terceiro) · 🤖 execução |
| **Custa se esquecer** | por que isto não pode virar dívida silenciosa |

---

# 🔴 BLOQUEIA O OBJETIVO Nº 1 — atendimento funcionando

> 🔴 **Este arquivo tem só as pendências ABERTAS.** As fechadas foram para
> [`PENDENCIAS-FECHADAS.md`](PENDENCIAS-FECHADAS.md) em 25/08/2026, quando ele
> chegou a **465 KB e virou 54% do pedágio de leitura de toda sessão**
> (`PROTOCOLO-AUTOBROKERS-AAA.md` §1).
>
> ⚠️ **Fechar uma pendência agora significa MOVÊ-LA**, não só marcar. Uma
> válvula que só enche é um aterro.


## P-01 · A API da InfoCap devolve 500 no pós-login

📊 **Medido em 02/08/2026, onze vezes.** Senha errada → 400 em 0,87 s. Senha
certa → **500 em 16,2–16,5 s**. Toda outra rota da API responde em menos de
0,7 s. **A autenticação passa e algo depois dela estoura num timeout fixo.**

```
NÃO é bloqueio de seguranca  → bloqueio devolve 403/429 e e instantaneo,
                                e valeria tambem para a senha errada
NÃO é credencial             → senha errada da erro diferente e especifico
NÃO é permissão (p500/p501)  → falta de permissao devolve 403
É bug do fornecedor          → na montagem de sessao/perfil pos-login
```

**Consequência que ninguém tinha mapeado:** 📊 não existe tabela de apólice no
banco, e `POLICY_DATA_PROVIDER_SOURCE` **não é lido por nenhuma linha de
código**. A InfoCap é a única fonte de apólice do sistema. **Sem ela, o agente
de atendimento não confirma uma apólice, não responde cobertura e não aciona
corredor.**

- **Destrava:** telefonema à CorpAPI com o diagnóstico acima. É uma hora de
  trabalho para o time deles, não uma investigação.
- **Dono:** 🧑 Founder
- **Custa se esquecer:** bloqueia a SPEC-065 inteira e a capacidade do
  atendimento — não só um auxiliar.

## P-02 · A AutoFleet não tem conexão InfoCap

📊 Nenhuma linha em `tenant_connections` para ela. O atendente dela seria cego
para apólice mesmo com a API no ar.
- **Destrava:** cadastrar depois que a API voltar (hoje não daria para validar).
- **Dono:** 🧑 Founder

## P-03 · Espelho local da carteira

Enquanto a única fonte de apólice for uma API de terceiro, **um fornecedor fora
do ar cega o produto inteiro.** O espelho é a tabela que a SPEC-065 Bloco B já
manda criar — muda só a alimentação.
- **Destrava:** exportação da carteira do InfoCap **web** (que funciona) para
  semear, ou a API voltar.
- **Dono:** 🧑 Founder — precisa autorizar com as corretoras.
- **Estado:** 💬 conversado em 02/08; o Founder ainda não está autorizado a
  baixar os documentos.

---

# 🟠 P0 DE SEGURANÇA E ISOLAMENTO — SPEC-063

Todos medidos na auditoria de 02/08. **Nenhum está em produção porque nada está
pareado** — mas nenhum pode ser ligado antes de resolvido.

## P-04 · Resulta e AutoFleet compartilham o grupo de suporte humano

📊 `120363427334937446@g.us` nas duas. Dossiê com nome e CPF de segurado da
AutoFleet cairia num grupo que a Resulta lê. **CLAUDE.md §7 é literal: nenhum
dado atravessa tenants.**
- A SPEC-063 classificou como **P1**; a auditoria subiu para **P0**.
- **Acréscimo:** enquanto os dois apontarem para o mesmo grupo, o correto é o
  sistema **recusar-se a acionar** — não mandar para o lugar errado com aviso.
- **Dono:** 🤖 SPEC-063 Bloco B · o Founder autorizou apagar o compartilhamento.

## P-226 · 🟡 Metade da suíte era invisível ao `pytest` — **os 151 já rodam; faltam triar 14**

### ✅ 24/08/2026 — A INVISIBILIDADE FECHOU. E a dívida é **48**, não 14.

🔴 **A primeira correção de hoje estava pela metade, e um auditor externo achou:**
`pytest tests/` não coletava zero — **abortava a sessão inteira** (`INTERNALERROR: SystemExit`), porque **60 arquivos chamam `sys.exit()` em nível de módulo** e o import da
coleta os executa. E o meu "151" era subconjunto. 📊 O universo real:

```
279  test_*.py
  6  com `def test_`   → o pytest roda
273  sem `def test_`   → rodam como PROCESSO
       151 com main()  ← o que a v1 pegava
       122 sem main()  ← 🔴 asserções em nível de módulo. Invisíveis para TODOS.
```

📊 **E quando os 122 começaram a rodar, apareceram 28 vermelhos novos:**

```
42 de 273 guardas-script VERMELHOS   (15,4%) — eram 14 conhecidos + 28 achados
 6 asserções vermelhas nos 6 arquivos que SÃO pytest de verdade
                                      (5 em test_a_rubrica_e_honesta, 1 em spec051)
🔴 TOTAL: 48
```

✅ **Depois da quarentena: `233 passed, 42 xfailed in 440s`** — verde e verdadeiro, e
`pytest tests/` voltou de **0** para **322 testes coletados**.

⚠️ **Os 6 dos arquivos pytest NÃO estão no CI ainda**, e o motivo está escrito: pô-los
em `xfail` exigiria editar guardas que não são meus para consertar. **Ficam registrados,
e os cinco da régua são o achado mais grave do lote** — ver abaixo.

### 🔴 OS CINCO DA RÉGUA — a nota devolve **102 numa escala de 100**

📊 `test_a_rubrica_e_honesta.py`, rodado direto: **5 failed, 8 passed**.

```
:72   assert 102 == 96    "o denominador mudou; a nota passou a medir outra coisa"
:371  assert 102 == 100-4  o mesmo 102, por outro caminho
:133  assert []            "o replay não acha NENHUMA órfã funcional. Ou o corredor
                            ficou perfeito — e aí esta asserção precisa ser reescrita
                            com a prova — ou a MEDIDA AFROUXOU e ninguém viu"
:199  "o subserviço já tem regra própria — a mutação precisa mudar de lugar"
:253  assert 9 == 15       "o eixo E deixou de fechar"
```

🔴 **VEREDITO: é BLOCKER, e vai para a SPEC-089.** Pela letra do §1 do protocolo, nota
de régua é medição de execução → pendência. **Mas o que a régua decide é se um corredor
está bom o bastante, e corredor chega em segurado.** Uma régua que devolve 102 e **parou
de achar órfã** aprova o que deveria reprovar. ⚠️ **Não entra na 085** — é da 083/089.

### O registro de como ficou:

📊 `backend/tests/test_todos_os_guardas_script_rodam.py` roda **cada guarda-script como
PROCESSO** e lê o exit code. Saída real: **138 passed, 14 xfailed in 182.64s**. E entrou no
`.github/workflows/gate.yml`, que até hoje rodava dois comandos e não via nenhum dos 151.

⚠️ **Por que NÃO foi um `conftest.py` com `pytest_collect_file`:** 🔴 tentado e descartado
— o hook é **aditivo**, o coletor padrão tenta IMPORTAR o mesmo arquivo, e o `sys.exit()`
de nível de módulo derruba a sessão (`INTERNALERROR> SystemExit`). Registrado para
ninguém repetir.

🔴 **A quarentena é `xfail(strict=True)` e corta dos dois lados:** guarda novo vermelho
**quebra**; guarda da quarentena que volte a passar **também quebra**, obrigando a tirá-lo.

📊 **E a mutação provou:** tirei `test_o_negrito_da_seguradora_nao_emudece_o_corredor` da
quarentena → **1 failed**. Restaurado **por cópia**, nunca por `git checkout`, e conferido.

⚠️ **O QUE FALTA:** triar os 14 — **defeito de produto** ou **asserção vencida**
(`CLAUDE.md` §9.3). Três já têm diagnóstico, e 🔴 **dois cheiram a defeito de produto**:
*"o motor não faz noop de verdade sobre o RESUMO"* e 🔴 *"o freio não freia quando a URA
escreve em NEGRITO"*. **Os dois são do corredor, e não devem esperar a triagem dos 14.**

- **Dono:** 🤖 execução · **Destrava:** um veredito por guarda

### O registro original:

## P-226 · 🔴 Metade da suíte de testes é invisível ao `pytest`, e **14 estão vermelhos**

**Aberta em:** 24/08/2026 · **Dono:** 🤖 execução · **Achada** conferindo uma prescrição que
não reproduzia

📊 **Medido, com os comandos:**

```bash
arquivos tests/test_*.py .................................. 278
  script com main(), sem `def test_`, INVISÍVEIS ao pytest .. 151
  desses, rodados um a um agora: VERMELHOS ................. 14
```

```bash
# rodando cada um e lendo o exit code, nao a saida
for f in tests/test_*.py; do
  grep -q "^def test_" "$f" || { python "$f" >/dev/null 2>&1 || echo "VERMELHO $f"; }
done
```

**Os 14:**

```
test_o_acionamento_nao_pede_o_impossivel.py     VERMELHO -- 12 falhas
test_o_corredor_conhece_a_tela_que_esta_na_frente.py       2
test_o_negrito_da_seguradora_nao_emudece_o_corredor.py     1
test_handoff_chega_em_alguem.py             test_corredores_novos.py
test_corredor_residencial_yelum.py          test_golden_do_eletricista.py
test_destilador_nao_paga_duas_vezes.py      test_o_clique_nao_se_perde.py
test_memorias_nao_vaza_inteligencia.py      test_spec062_porteira_de_cobranca.py
test_o_encaminhamento_chega_ao_segurado.py  test_sem_corredor_de_vidro_nao_e_beco.py
test_o_que_acontece_quando_o_agente_liga.py
```

🔴 **E o CI não roda nenhum dos dois jeitos.** `.github/workflows/gate.yml` executa
`python tests/broker_outcome_regression_pack.py` e `npx tsc --noEmit`. **Não roda `pytest`,
e não roda os 151 scripts.** Os 14 vermelhos não aparecem em lugar nenhum do processo.

⚠️ **Por que isto passou tanto tempo:** os 151 são **scripts** — `def main()` e
`raise SystemExit(main())` — com funções que **não começam com `test_`**. Rodados direto,
funcionam e devolvem exit 1 corretamente. Rodados por `pytest`, coletam **zero** e a suíte
fica **verde por vacuidade**. `pytest tests/` sobre `test_o_acionamento_nao_pede_o_impossivel.py`
diz *"no tests collected"* — e um arquivo que coleta zero é indistinguível de um que passou.

🔴 **É o `CLAUDE.md` §9.3 na forma mais cara:** *"um guarda que não tem como falhar não
guarda nada"*. Aqui é pior — **os guardas têm como falhar, ESTÃO falhando, e ninguém roda.**

⚠️ **E um dos 14 é o guarda central da SPEC-085:** `test_handoff_chega_em_alguem.py`.

- **Destrava:** decidir **um** jeito de rodar (renomear as funções para `test_*`, **ou** um
  coletor que execute os 151 scripts) e pôr isso no `gate.yml`. 🔴 **E antes disso, saber
  quais dos 14 são defeito de produto e quais são asserção vencida** — `CLAUDE.md` §9.3:
  *"quando um fato muda, o teste muda com ele, e a lição migra em vez de morrer"*.
- **O que custa esquecer:** toda SPEC daqui em diante declara gate verde sobre uma suíte
  onde **54% dos arquivos não são executados por nada**.

## P-223 · 🔴 CPF e telefone em claro em `work_steps`, e a máscara existe

**Aberta em:** 24/08/2026 · **Dono:** 🤖 execução · **Achada** medindo para a SPEC-085

📊 **12 linhas** de `work_steps.output_summary` guardam `titular_cpf`,
`telefone_contato` e `client_phone` **sem máscara**, de **18 a 19/08/2026**. São CPFs e
telefones de pessoas reais, em tabela **durável**, que o backend lê com service role.

```sql
SELECT count(*), min(created_at)::date, max(created_at)::date FROM work_steps
 WHERE output_summary::text ~ '"(titular_cpf|telefone_contato|client_phone)"\s*:\s*"[^"#*]';
-- 12 | 2026-08-18 | 2026-08-19     (medido de dois jeitos, os dois dao 12)
```

🔴 **O que torna isto um defeito de construção, e não um esquecimento:** no MESMO
registro, o `transcript` **está mascarado** — o endereço sai como `R. #####ES JÚN###`.
**A máscara existe, roda, e não foi aplicada ao objeto `slots`.** Não falta a função:
falta uma chamada.

⚠️ **E escala com o volume.** As 12 linhas são de **4 acionamentos** — os únicos com
rastro durável na história do produto. A 73 rotas ligadas, isto vira o padrão.

- **Destrava:** aplicar o mascarador ao `slots` antes de gravar `output_summary`, e um
  backfill nas 12. 🔴 **O guarda tem de ser um teste que FALHA hoje** — grava um passo
  com CPF e prova que o que foi para o banco não o contém.
- **O que custa esquecer:** é dado de titular de apólice em repouso, sem necessidade
  operacional — e a auditoria seguinte acha isto antes de achar qualquer outra coisa.

## P-224 · 🔴 `needs_human` é gravado como `status = 'completed'`

**Aberta em:** 24/08/2026 · **Dono:** 🤖 SPEC-085 · **Achada** medindo para a SPEC-085

📊 Os dois únicos `needs_human` duráveis da história — `needs_human:sentinela_stall` e
`needs_human:missing_slots:problema_eletrico_opcao` — estão em `work_runs` com
**`status = 'completed'`**. **Um travamento é indistinguível de um sucesso por status.**

⚠️ E um deles (`448d3f08`) tem **três campos com três verdades**: `error_code` diz
`needs_human:missing_slots`, `current_step_key` diz `test_aborted`, e o `result_summary`
diz *"Simulação completa"*.

- **Destrava:** um estado terminal que **nomeia o travamento**, e a SPEC-085 é quem o
  define — esta pendência é insumo dela, não trabalho paralelo.
- **O que custa esquecer:** todo painel que filtrar por `status` mostra **zero**
  travamentos, para sempre, com o produto travando.

## P-225 · `human_review_tasks` tem schema completo e **nenhum escritor**

**Aberta em:** 24/08/2026 · **Dono:** 🤖 SPEC-085

📊 **0 linhas**, com `motivo`, `veredito` e `revisado_por` prontos. A tabela do
destravamento humano existe e nunca teve quem escrevesse nela. ⚠️ Mesma família da
P-18 (`auxiliary_events` sem escritor) — **tabela sem escritor é promessa de schema.**

- **Destrava:** decidir na SPEC-085 se ela é o registro do destravamento ou se morre.

## P-06 · O handoff mente ao segurado em todo caminho de falha

`tools/human_handoff.py` — quando o UPDATE não acha a conversa **e** quando
estoura exceção, devolve *"Um atendente foi solicitado."* **Sucesso declarado
em cima de falha.**
- **Regra a cravar:** caminho de falha nunca afirma sucesso.
- **Dono:** 🤖 SPEC-063 Bloco B

## P-07 · O handoff escreve sem filtro de tenant

`.update({...}).eq("session_id", …)` — **sem `company_id`**. CLAUDE.md §7 exige
o filtro no service justamente para não depender de o `session_id` ser único.
- **Dono:** 🤖 SPEC-063 Bloco B

## P-08 · O vazamento de CPF tem dois caminhos

A SPEC aponta o prompt (`prompts.py`, literal). **Mas `infocap_tool.py` imprime
`CPF/CNPJ: {doc}` inclusive no ramo `client_facing`.** Quem consertar só o
prompt vai achar que resolveu.
- **Dono:** 🤖 SPEC-063 Bloco A

---

# 🟡 A MÁQUINA QUE RODA E NINGUÉM OBSERVA

## P-09 · Um Work Run pode entrar na fila e sumir para sempre

📊 Dois `intelligence.detect_signals` em `queued` desde 28 e 30/07, com
`lease_owner`, `heartbeat_at` e `next_attempt_at` **todos nulos** — nunca foram
arrendados. E a regra `operacao.work_run_travado` **rodou e não pegou nenhum
dos dois.**

> A SPEC-055 entregou fila durável. **Durável não é o mesmo que observável.**

- **Destrava:** alarme de abandono para `queued` sem lease além do prazo.
- **Dono:** 🤖 — proposto para a SPEC-068 (prontidão).

## P-10 · O observador capturou tudo e não classificou nada

📊 `attendance_sessions.insurer_key` é **NULL em 100% das 8.872 sessões**.
`ramo` e `servico` idem. A SPEC-063 F.2.1 diz que "as 69.150 transcrições dizem
quais seguradoras são" — **as cartas dizem; a tabela de sessões não.**
- **Custa se esquecer:** qualquer análise por seguradora sobre atendimento
  precisa re-analisar, não consultar.

## P-11 · 70.576 linhas de backup sem política de retenção

📊 `attendance_transcripts_copias_removidas_20260728` (58.091) e
`observed_events_copias_removidas_20260728` (12.485). Backup de uma deduplicação
de 28/07 — sem dono, sem prazo, sem registro.

## P-12 · 120 tabelas com RLS ligado e nenhuma policy

📊 Medido nos advisors de segurança. **CLAUDE.md §7:** o backend usa service
role, então RLS sem policy não protege contra erro de filtro no código — mas
também não protege contra nada mais.
- **Dono:** 🤖 — território da SPEC-054/068, não da 064.

---

# 🟢 DEIXADO PRONTO E DESLIGADO — SPEC-064

O padrão: **construir inteiro, deixar desligado, registrar o que liga.**

## P-13 · E-mail: a chave do SendGrid está vazia

📊 `SENDGRID_API_KEY=` vazia no ambiente. O canal de e-mail do Bloco E nasce
**construído e desligado**: a política decide "e-mail", o executor registra
`sem_provedor_configurado` e o `delivery_status` **não fica `pending` mudo**.
- **Destrava:** uma chave. **Mas a decisão do provedor definitivo é da
  SPEC-069** — Amazon SES, US$ 0,10/mil, com isolamento de reputação por
  corretora. **Não vale amarrar no SendGrid agora.**
- **Dono:** 🧑 Founder (quando a 069 descongelar)

## P-14 · WhatsApp para briefing depende do governador de envio

A regra é **só manchete e link**, nunca o relatório inteiro. Mas o governador de
taxa é a SPEC-063 Bloco C e **ainda não existe**: 📊 hoje não há limitação de
envio em lugar nenhum.
- **Regra dura:** o briefing **não sai por WhatsApp antes do governador
  existir**, senão repetimos a rajada de 100 mensagens da cobrança.
- **Dono:** 🤖 SPEC-063 Bloco C

## P-15 · Artifact não tem visualizador na tela da corretora

Em Entregas, o item de tipo `documento` vindo de `artifacts` fica **sem link**
(`href: null`): a rota de leitura de artifact é da SPEC-057 e só existe no lado
da plataforma.
- **Custa se esquecer:** o entregável de primeira classe do produto aparece na
  lista e não abre.

## P-16 · Duas telas de execução ainda moram fora da rota do Auxiliar

`galeria/follow-up-whatsapp` (407 linhas) e `galeria/resumo-atendimentos` (347).
**Não são duplicata de descrição — são telas de execução com API própria, e
funcionam.** São alcançadas pela ficha do Auxiliar (`tela_de_execucao`), mas o
lugar delas é sob `/dashboard/auxiliares/[slug]/`.
- **Custa se esquecer:** o teste só impede a **terceira**; estas duas
  continuam sendo o precedente.

## P-17 · A verdade sobre conexões mora em três tabelas

`tenant_connections` (o caminho novo) · `portal_accounts` (o portal worker) ·
`integrations` (o WhatsApp, anterior ao conceito de conector).
`conexoesDaCorretora()` lê as três **de propósito** — ignorar qualquer uma faria
a tela dizer *"não conectado"* para quem já fez o trabalho.
- **Destrava:** unificação, **sem apagar nenhuma antes de a nova provar que lê
  tudo.**

## P-18 · Duas tabelas de auxiliar sem escritor

📊 `auxiliary_events` = 0 (o `evento()` nunca é chamado) ·
`auxiliary_template_releases` = 0 (lido pelo código, nunca escrito). E
`tenant_auxiliaries.health` / `.current_revision` não são escritos por ninguém.
- **Recomendação registrada:** `auxiliary_events` ganha escritor — é o que
  alimenta o histórico por Auxiliar. **Regra: nenhuma tela mostra coluna
  alimentada por tabela vazia.**
- **Dono:** 🤖 SPEC-064 Bloco H

## P-19 · Os dez Auxiliares "em breve" são rascunho

O Founder foi explícito: são incógnitas até sabermos se entregam valor. Todos
já têm nome, headline, o que fazem, de onde tiram o dado e **o que falta para
existir** — e **nenhum promete número** (CLAUDE.md §12.1).
- **Destrava:** revisão um a um, quando houver dado real para medir. **Cada um
  pode ser melhorado, substituído ou retirado sem afetar os que funcionam.**
- **Dono:** 🧑 + 🤖, um por vez.

---

## P-29 · A SPEC dos portais — cobrança em todas as seguradoras

**Decidida em 02/08/2026 pelo Founder, para depois destas SPECs.**

📊 O produto tem **17 portais** cadastrados — 15 de corretor (um por
seguradora) e 2 de vidros. **Só a Allianz tem jornada de cobrança
implementada.**

```
1. o Cobrador da Allianz é o MOLDE — ele funciona ponta a ponta
2. cada seguradora nova é uma jornada no portal_worker, mesmo desenho
3. ANTES de escrever robô, conferir se ela tem API (é para isso que
   os 33 endereços de API do catálogo servem — P-26)
4. cobrança primeiro; renovação depois, se a estrutura sustentar
```

> **Regra que não muda:** cobrança de outra seguradora **não é Auxiliar novo**.
> É o mesmo "Cobrança Feita" com mais um portal na configuração da corretora.
> Um auxiliar por seguradora seria a bagunça voltando pela porta dos fundos.

**E o portal de vidros** já existe (2 portais, `cred_kind: public`) e faz parte
do atendimento de assistência. Entra na mesma revisão.

- **Destrava:** decisão do Founder de abrir a SPEC.
- **Detalhe completo:** [`PORTAIS-E-CORREDORES.md`](PORTAIS-E-CORREDORES.md)

## P-26 · O catálogo de 189 portais está mapeado e não é usado

📊 `lib/attendance/portal-global-catalog-seed.ts` — **8.696 linhas, 189 portais
de seguradora** levantados de pesquisa oficial: Allianz, Porto, HDI, Sompo,
Mapfre, Bradesco, Chubb, Azul, Junto, Liberty, Alfa e Open Insurance. Cada um
com URL de login, métodos de autenticação, perfil de desafio (captcha/MFA/OTP)
e jornadas suportadas.

**Ele sobreviveu à remoção do Portal Browser de propósito** — o simulador era
código morto; o catálogo é pesquisa. Mas hoje **nada o consome**.

> O Founder foi explícito: depois destas SPECs, repetir na Porto, HDI, Tokio e
> Yelum o que já funciona na Allianz. **Este catálogo é o mapa desse
> trabalho** — e a ordem de prioridade já está medida (P-27).

- **Destrava:** a SPEC de novos portais.
- **Custa se esquecer:** refazer o levantamento de 189 portais do zero.

## P-27 · A ordem dos corredores, medida

📊 Medido no acervo real (cartas de auto por seguradora), 02/08/2026:

```
Allianz .... 439      (+178 residencial +91 outros = 708 no total)
Yelum ...... 276
Tokio ...... 251
HDI ........ 184
Youse ...... 177      ← não estava na lista do Founder
Porto ...... 165      ← é a 6ª, não a 2ª
Bradesco ... 116
Mapfre ..... 100
```

**A lista de seguradoras do Founder estava certa; a ordem não.** E a SPEC-063
F.2.1 afirma que "as 69.150 transcrições dizem quais são" — 📊 **elas não
dizem**: `attendance_sessions.insurer_key` é NULL em 100% das 8.872 sessões
(P-10). Quem diz são as cartas.

- **Destrava:** a SPEC-063 Bloco F.
- **Dono:** 🤖

## P-28 · A capability de portal existe e ninguém a exerce

📊 Medido: `billing_collection.py` **não consulta o Capability Resolver**. As
cinco `operational.portal.*` são declaradas e nunca checadas — o Cobrador entra
no portal por fora do modelo de governança.

A SPEC-064 consertou a **declaração** (o provider agora nomeia quem trabalha, e
o resolver enxerga `portal_accounts`), então ela deixou de mentir. **Falta
ligar a checagem.**

> Enquanto ninguém checar, a capability é documentação. No dia em que alguém
> ligar sem antes conferir, o Cobrador para — e a causa vai parecer
> desconexa.

- **Destrava:** o Tool Gateway sair de `shadow` (📊 `TOOL_GATEWAY_MODE=shadow`).
- **Custa se esquecer:** é uma armadilha armada, não uma dívida passiva.

---

# 🔵 REGISTRADO PARA O MOMENTO CERTO

## P-20 · Conversas de vários WhatsApps

Quando a cobrança tiver número próprio, o mesmo cliente terá conversa em dois ou
três números. **Registrado inteiro em `SPEC-069 §A.2.1`**, com a regra que
resume: *o número é por onde a mensagem passou, não quem é o cliente.*
- **Gatilho:** o Bloco A da SPEC-069.

## P-21 · O esquema de comissionamento por produto

📊 Cinco parcelas vencidas medidas na Allianz: as duas com comissão zero são as
**últimas** (10/10 e 4/4); a 2/7 paga 4,66% e a 3/10 paga 0,03% — **150× de
diferença entre duas parcelas do meio.** 💭 A antecipação explica parte e não
explica tudo.
- **Custa se esquecer:** é o coração do Caça-Comissão. Um auxiliar que
  **descobre a regra** vale mais que um que procura "comissão zerada".

## P-22 · A coluna viva de sinistralidade do SES

A pesquisa afirma que a coluna documentada está morta desde 2013 e que a viva é
`sinistro_ocorrido`. **Não desmenti — não consegui confirmar:** a URL que testei
devolveu 404.
- **Custa se esquecer:** a SPEC-066 inteira assenta nisso.

---

# ⚫ HIGIENE

## P-23 · A `main` está **230** commits atrás, e são **DEZ** branches

📊 **Nada deste trabalho está em produção — nem o conserto de segurança da
Fábrica.** O EasyPanel constrói a `main`.

⚠️ **Remedido em 24/08/2026, e envelheceu:** era 117; são **230** na maior, e
**dez branches** à frente:

```
spec084 +230 · spec083 +162 · spec078 +158 · fix/pos-077 +95 · spec077 +92
spec075  +89 · spec074  +82 · spec073  +69 · spec072     +59 · spec070 +49
```

🔴 **E o que está parado não é abstrato — são estes três, todos medidos:** o produto
mandando `rb_InformacoesLocal="6"` (**LOCAL SEGURO**) para um carro no km 42 de
rodovia; o segurado da geladeira ouvindo que **a peça é por conta dele** quando a URA
da yelum diz *"coberto a mão de obra E PEÇAS"*; e a promessa de SMS sem lastro em
cinco corredores. **Os três estão consertados numa branch, e os três continuam no ar.**
- **Destrava:** merge com o gate final da SPEC (CLAUDE.md §13.8).
- **Dono:** 🧑 Founder decide quando · 🤖 prepara.

🔴 **E há um segundo fato, medido em 24/08/2026:** as duas árvores de trabalho
divergiram. 📊 `AutoBrokers-FIX` → **0 commits atrás** da `origin/main`;
`AutoBrokers-Opus-Exec` → **169 atrás**, último commit de 16/08. O `CLAUDE.md`
nomeava a segunda no preflight — **corrigido**: o preflight agora **mede**
(`git rev-list --count HEAD..origin/main` tem de ser 0) em vez de presumir pelo nome.
⚠️ **Falta a decisão do Founder:** as duas árvores continuam, ou uma é aposentada?
A `Opus-Exec` tem `feat/spec072` não mesclada e rascunhos das SPECs 073–078 não
versionados — **nada foi tocado lá**.
- **Dono desta parte:** 🧑 Founder.

## P-24 · Binários soltos no repositório

📊 `exp.bin` (5,2 KB) e `mensal.xlsx` (6,1 KB) na raiz, commitados sem contexto.

## P-25 · `MIGRATIONS-AUTHORITY.md` §9 está desatualizado

Diz *"enquanto P1 estiver pendente, nenhum write em produção é autorizado"* —
mas **P1 foi resolvida por D11 em 25/07**. Quem ler o documento hoje conclui que
está proibido de aplicar migration.
- **Dono:** 🤖 SPEC-064 Bloco J (documentação).

---

## Índice rápido

| # | Pendência | Dono | Bloqueia |
|---|---|---|---|
| P-01 | InfoCap 500 | 🧑 | atendimento + SPEC-065 |
| P-02 | AutoFleet sem InfoCap | 🧑 | atendimento da AutoFleet |
| P-03 | Espelho da carteira | 🧑 | independência de terceiro |
| P-04 | Grupo de suporte compartilhado | 🤖 | ligar o atendimento |
| P-05 | Agente sem prompt | 🤖 | ligar o atendimento |
| P-06 | Handoff mente na falha | 🤖 | ligar o atendimento |
| P-07 | Handoff sem filtro de tenant | 🤖 | CLAUDE.md §7 |
| P-08 | CPF vaza pela tool | 🤖 | ligar o atendimento |
| P-09 | Work Run some sem alarme | 🤖 | confiança na fila |
| P-10 | Sessões sem classificação | 🤖 | análise por seguradora |
| P-11 | 70.576 linhas de backup | 🤖 | — |
| P-12 | RLS sem policy em 120 tabelas | 🤖 | SPEC-068 |
| P-13 | Chave de e-mail | 🧑 | canal de e-mail |
| P-14 | Governador de envio | 🤖 | briefing por WhatsApp |
| P-15 | Visualizador de artifact | 🤖 | abrir o entregável |
| P-16 | Duas telas fora do lugar | 🤖 | — |
| P-17 | Três tabelas de conexão | 🤖 | — |
| P-18 | Tabelas de auxiliar sem escritor | 🤖 | histórico por Auxiliar |
| P-19 | Dez Auxiliares em rascunho | 🧑+🤖 | valor real |
| P-20 | Conversas multicanal | 🤖 | SPEC-069 |
| P-21 | Comissionamento por produto | 🤖 | Caça-Comissão |
| P-22 | Coluna do SES | 🤖 | SPEC-066 |
| P-23 | `main` atrasada | 🧑 | **tudo em produção** |
| P-24 | Binários soltos | 🤖 | — |
| P-25 | Doc de migrations desatualizado | 🤖 | — |
| P-26 | Catálogo de 189 portais sem consumidor | 🤖 | novos portais |
| P-27 | Ordem dos corredores (medida) | 🤖 | SPEC-063 F |
| P-28 | Capability de portal não é exercida | 🤖 | Tool Gateway |

---

## SPEC-063 — o que ela deixou (03/08/2026)

### 🧑 Do Founder

| # | Pendência | O que destrava | O que custa esquecer |
|---|---|---|---|
| **P-30** | **Separar o grupo de suporte humano** — Resulta e AutoFleet dividem `120363****446@g.us` | dar um destino próprio a cada uma em Personalização → Suporte | **o handoff está RECUSADO nas duas** por segurança. É fail-closed, não bug: o dossiê leva CPF do segurado |
| **P-31** | `INSURER_DISPATCH_LIVE=true` em produção — o portão de envio **real** está aberto | decidir se fica aberto antes do go-live | o que segura hoje é `DISPATCH_FINALIZE_MODE=test` + allowlist + agentes desligados. Nenhuma trava por corretora ou por corredor |
| **P-32** | `CARTOGRAPHER_MODE=1` — o Cartógrafo **envia WhatsApp real** a seguradoras para mapear URA | decidir se continua ligado | mensagem nossa chegando em seguradora sem ninguém esperando |
| **P-33** | Credenciais **Twilio** no ambiente, sem uma linha de código que as use | decidir se telefonia entra no roadmap | é o que falta para a **Youse** ter corredor (ela não tem WhatsApp de assistência) |

### 🤖 De execução

| # | Pendência | O que destrava |
|---|---|---|
| **P-34** | Varredura periódica de acionamento órfão | hoje dispara 1× por processo, no primeiro cache-miss. Falta **uma linha** no laço de manutenção do worker |
| **P-35** | Migration `20260803_06` (índice do Work Run de acionamento) escrita e **não aplicada** | usa `CONCURRENTLY`, precisa rodar fora de transação |
| **P-36** | Três outros caminhos escrevem `agent_system_prompt` **sem o portão** de prompt vazio | `blueprint-studio-store`, `release-rollout-store`, `tenant-agent-store`. Foi por um deles que a AutoFleet zerou |
| **P-37** | `agent-health.ts` detecta agente ausente e duplicado, **não detecta agente mudo** | foi por isso que ninguém percebeu a AutoFleet |
| **P-38** | `unknown` (canal sem confirmação) não está em `ESTADOS_RUINS` | canal demovido para de mentir nas telas mas **não gera sinal** no briefing |
| **P-39** | O freio de emergência de envio **não tem botão** | `parar_envios()`/`retomar_envios()` funcionam, só por console |
| **P-40** | O grito do acionamento órfão não vai por WhatsApp | vai para `work_events` e Atividades; o resolvedor de destino já está pronto ao lado |
| **P-41** | 3 variáveis do heartbeat fora do `.env.example` | `CHANNEL_HEARTBEAT_ENABLED/_INTERVAL_MINUTES/_STALE_MINUTES` |
| **P-42** | `AGENT_OS_TENANT_TIMEZONE` não está no `.env.example` | o governador lê com padrão `America/Sao_Paulo` |
| **P-43** | **GOLD-ELEC-007 nomeia um estado que não existe** — espera `ready_for_approval`, o contrato devolve `ready_to_send` | ou renomeia o código, ou reescreve o caso. Nome que não bate é como um golden deixa de pegar o defeito que existia para pegar |
| **P-44** | 5 dos 10 golden tests só são verificáveis **com modelo** | classificar linguagem natural. Declarado no próprio teste como lacuna nomeada |
| **P-45** | Os corredores recomendados em [`CORREDORES-QUE-PODEMOS-CRIAR.md`](CORREDORES-QUE-PODEMOS-CRIAR.md) | vidros de auto (10 seguradoras) · pane seca · encanador · residencial Porto |

### SPEC-063 Bloco F — os corredores (03/08/2026)

| # | Pendência | Dono | O que destrava |
|---|---|---|---|
| **P-46** | **O motor não consome `encaminha` ainda.** `detect_referral_step()` e `subservice_referral()` existem e estão provados, mas `handle_insurer_message` não fecha a sessão como *resolvido por encaminhamento* nem entrega o link ao segurado. Hoje o passo é `noop` (correto — não responde à URA), e o caso fica aberto até o watchdog | 🤖 | ~30 linhas em `insurer_dispatch_service` |
| **P-47** | `infer_ramo_servico` devolve `"residencial"` genérico para *"encanador"* e *"eletricista"* — e `"residencial"` não é subserviço de nada, então cai em `subservico_invalido` | 🤖 | o classificador precisa nomear o subserviço. Não foi criado alias porque adivinhar qual dos cinco seria chute |
| **P-48** | `unknown_step_policy` e `coverage_guardrails` são **campos declarativos sem consumidor** | 🤖 | nascem anotados, não escondidos (CLAUDE.md §11.1) |
| **P-49** | **Nenhum dos corredores novos foi exercitado contra a URA real** | 🧑 | estão em modo teste com o freio; `DISPATCH_FINALIZE_LIVE_PLAYBOOKS` não os inclui |
| **P-50** | **Vidros sem evidência em 7 seguradoras** — allianz, tokio, mapfre, yelum, hdi, alfa, bradesco | 🧑 | o Atlas precisa ver um atendimento de vidro nessas. Hoje elas caem em handoff, que é o certo |
| **P-51** | **Residencial sem evidência** em yelum, tokio, zurich, azul, alfa, mapfre. Bradesco só tem a entrada do menu (`*2.* Residencial`), sem subserviços | 🧑 | mesmo caminho: observação |
| **P-52** | **Cobertura de URA baixa limita o corredor**: 📊 Tokio 12%, Mapfre 25%, Zurich 28%, Yelum 34%, HDI 36%, Porto 37% | 🧑 | o pareamento da AutoFleet (auto/frota) é o que mais move esses números |
| **P-53** | **Twilio / telefonia** — credenciais no ambiente, zero código. É o que falta para a **Youse** ter corredor | 🧑 | sem prioridade agora, por decisão do Founder (03/08) |

### SPEC-063 Fase 0 — o que ficou esperando (03/08/2026)

| # | Pendência | Dono | O que destrava |
|---|---|---|---|
| **P-54** | **Re-sync do Atlas bloqueado** — os três observadores estão `disconnected`; o `history-sync` puxa da instância conectada | 🧑 | parear os WhatsApps. Runbook completo em [`RUNBOOK-RESYNC-DO-ATLAS.md`](RUNBOOK-RESYNC-DO-ATLAS.md), com a linha de base já gravada (947 cliques, 0 com id) |
| **P-55** | **20 eventos `source='live'` não são recuperáveis** por sync — nasceram do webhook | 🤖 | nada a fazer; **não apagar**. Daqui pra frente nascem certos |
| **P-56** | `evolution_inbound._text_from_message` lê `selectedButtonId` (d minúsculo) — não casa com o `selectedButtonID` real | 🤖 | mesmo defeito do observador, outro arquivo |
| **P-57** | Os 23 `flow_reply` do histórico têm `paramsJSON` com o schema do formulário — não são parseados no caminho do histórico | 🤖 | ganho real, mas tem dimensão de privacidade: avaliar antes |
| **P-58** | `rb_Ocupantes` id `4` tem **título vazio** na captura | 🧑/🤖 | uma nova captura com gestante resolve. Até lá o caso vira `missing` e exige clique humano — seguro, mas bloqueia |
| **P-59** | Os 41% de cobertura da HDI são **projeção**, não número gravado | 🤖 | sai do passo 6 do runbook (retecer) |
| **P-60** | O passo 7 do portal (escolha de loja/domicílio) **nunca foi exercitado** — em 39 acionamentos, `has_protocol` nunca foi True | 🤖 | um acionamento com `confirm=True` mostra o que há lá |
| **P-61** | Variante e lado de peça no portal (`RETROVISOR ELÉTRICO` vs `MANUAL`, porta direita/esquerda) | 🤖 | o segurado não diz; adivinhar troca a peça. Hoje para com a lista, que é o certo |

---

## P-62 · Construir a imagem `0.7.2-autobrokers.2` do Evolution GO 🤖→🧑

**O que é.** O patch `0005-send-interactive-response` abre a rota que faltava
(`POST /send/interactiveResponse`). O código está escrito, os cinco patches
aplicam limpos no commit fixado, e o teste que prova a montagem já existe.

**O que destrava.** O envio de resposta de formulário nativo — 📊 4 seguradoras
o usam (Porto 12 · HDI 6 · Azul 4 · Yelum 2) e 460 apólices de auto (26,9% da
carteira) estão nessas seguradoras.

**Por que ainda não foi feito.** Não há Go nem Docker nesta máquina: **quem
compila é o build**. Até ele rodar, o código nunca passou por um compilador.

**O que custa esquecer.** Os corredores dessas 4 seguradoras já existem e não
rendem. É trabalho pronto parado.

## P-63 · A prova de transporte precisa de UM telefone pareado 🧑

**O que é.** Mandar a resposta de um número nosso para outro número nosso e
comparar o que chega, campo a campo, com o clique humano de 18/07.

**O que destrava.** A diferença entre "escrevemos" e "funciona".

**Por que não dá para pular.** 📊 Temos **uma única** captura real de um humano
respondendo este formulário — as outras 22 foram gravadas vazias pelo defeito
que a Fase 0.1 consertou. Um acervo de um não permite conferir hipótese; permite
só comparar. O loopback é a segunda amostra, e é nossa.

**O que custa esquecer.** Ligar sem provar gasta a única janela do atendimento
real: a URA da HDI encerra em 12 minutos, e uma resposta em formato errado é
descartada **em silêncio** — sem erro, sem reenvio.

## P-64 · `version` do envelope continua HIPÓTESE 💭

**O que é.** A captura de 18/07 **não tem** o campo `version`. Não sabemos se o
remetente não o mandou ou se nosso observador não o leu — as duas explicações
cabem, e a captura não escolhe entre elas.

**Como está tratado.** O Go **omite** quando ninguém pede, e o Python passa
adiante o que lhe derem. Ninguém finge saber.

**O que destrava.** O loopback (P-63): ele mostra o que um cliente real põe ali.

---

## P-65 · 🔴 A tela de pareamento diz uma coisa e liga outra

**O que aconteceu, 03/08/2026 20:15–20:24.** O Founder abriu "Conectar WhatsApp
da corretora" no painel e escaneou. 📊 Quem conectou foram as instâncias do
**Observador** (`ab-obs-*`), não as de atendimento (`ab-*`), que seguem
`disconnected` — confirmado pelo batimento às 20:25:35.

O Observador nasce com escopo `insurers_and_clients`. Resultado: **2.556
transcrições e 745 sessões** de 630 contatos pessoais entraram em
`attendance_transcripts` — a tabela que alimenta o destilador de cartas.

**Contido e revertido.** Escopo fechado nas 3 integrações, API reiniciada para
matar o lote em voo, dados apagados. 📊 Restaurado ao número exato de antes
(69.150 transcrições · 8.872 sessões) e **nenhuma carta foi gerada**
(`knowledge_cards` parou em 30/07, zero no período).

**A causa — CORRIGIDO em 03/08 depois de ler o código.** Minha primeira leitura
dizia "a tela mente". Está errado, e ao contrário: **o texto da tela está certo
e o nome interno é que envelheceu.**

📊 `app/api/dashboard/whatsapp-channel/route.ts:9` — `const PURPOSE = 'observer'`,
usado nas 9 chamadas da rota. **Não existe nenhum caminho na UI que pareie
`attendance`.** O `/setup`, que tem esse padrão, não tem quem o chame.

E 📊 `observer_intake.py:483-523` mostra por que isso não é um bug de
comportamento: a instância chamada "observer" **vira o canal de atendimento
sozinha** quando o agente é ligado, no mesmo número, sem re-parear. O comentário
no código é literal: *"agente LIGADO → captura e o evento SEGUE para o pipeline"*.
A tela promete exatamente isso: *"ligar o agente ativa as respostas automáticas
neste mesmo número"*.

**Então o defeito real é o escopo, não o rótulo.** Aquele pareamento captura
tudo que não for grupo, e ninguém é avisado disso antes de escanear.

**O que destrava.**
1. a tela declarar o que será capturado, com as palavras certas, ANTES do QR;
2. escolher o escopo na hora do pareamento, e não depois;
3. renomear `observer` para o que a coisa é — ou aceitar o nome e documentar,
   mas não deixar os dois significados convivendo.

**O que custa esquecer.** Da próxima vez pode ser o telefone pessoal de um
corretor de verdade — e aí não é reversível com um DELETE nosso.

## P-66 · O payload cru do histórico fica 7 dias no Redis 🤖

📊 `history_ingest.py` guarda o primeiro sync inteiro em Redis, até 200 KB, TTL 7
dias. O DELETE do Postgres **não** o alcança. Vence sozinho em 10/08/2026.

**O que destrava.** Limpar a chave, ou aceitar o vencimento. Não há PII em
índice nem em RAG — é cache bruto, não consultável.

---

## P-67 · 🔴 Conversa pessoal no número da corretora não pode virar carta

**O Founder levantou, e ele está certo.** O WhatsApp de uma corretora é um
telefone de gente. No meio das conversas com segurado vão existir
*"oi amor, quando você vai no mercado?"*, o grupo do prédio, o cunhado pedindo
dinheiro. **Não é caso de exceção — é o normal de qualquer telefone de trabalho
no Brasil.**

Hoje o sistema separa por **origem**: se o número do outro lado está na lista
das 12 seguradoras, vai para o Atlas; se não está e o escopo é total, vai para
`attendance_transcripts` — e de lá o destilador faz carta. **A separação é por
QUEM falou, nunca por SOBRE O QUE se falou.**

📊 O que já existe de proteção, medido: `knowledge_cards` tem **310 cartas
`rejected_pii`** e **5 `rejected_absoluto`**. Ou seja, há um filtro e ele
reprova — mas ele mira em **dado pessoal** (CPF, telefone, endereço), não em
**assunto que não é seguro**. Uma conversa doméstica sem nenhum CPF passa nesse
filtro sem disparar nada.

**E a curadoria publica `pending_review → published` sem aprovação humana.**
Então o caminho inteiro existe: conversa doméstica → transcrição → carta →
RAG consultável pelo agente. Nada nesse caminho pergunta "isto é sobre seguro?".

**O que destrava.** Uma prova de pertinência ANTES de virar carta:
1. o destilador recusar conversa que não trate de seguro, sinistro,
   apólice, acionamento ou atendimento — e o teste ter de mostrar que ele
   recusa mesmo, com um exemplo doméstico real;
2. carta nova de origem não-seguradora nascer `pending_review` de verdade,
   com um humano aprovando, até a prova acima existir;
3. medir quantas das 9.699 cartas atuais vieram de conversa não-seguradora, e
   revisar essas.

**O que custa esquecer.** O agente de uma corretora respondendo a um segurado
com conhecimento destilado da vida particular do corretor. Não é um erro
técnico que se explica — é um constrangimento que não se desfaz.

> Relacionado a [P-65] (a tela não diz o que captura) e [P-66] (payload cru no
> Redis). Os três nasceram do mesmo pareamento de 03/08.

### ✅ 08/08/2026 — o item 1 está feito; 2 e 3 continuam abertos

O filtro de valor existe: `curadoria_cartas.e_sobre_seguro`, determinístico,
sem LLM, chamado em `publicar_lote_sync` — a **única** porta em que uma carta
vira `published` sem ninguém olhar. Carta recusada não some: fica em
`rejected_fora_de_escopo`, com texto e hash intactos, e o `/admin/espelho`
continua podendo aprová-la uma a uma. O nome do status é próprio de propósito:
marcá-la `rejected_pii` faria o próximo a contar vazamentos contar esta junto.

📊 Medido contra as 12.063 `published` (projeto `dcajcvlzcjbmyapmklil`),
refazendo a consulta a cada ajuste do vocabulário:

    um vocabulário só, sem nomes de companhia          184  (1,53%)
    dois níveis, sem os nomes das seguradoras          399  (3,31%)  ← PIOROU
    + nomes de seguradora no nível forte               169  (1,40%)
    + dinheiro repartido em seis entradas               64  (0,53%)  ← em uso

O passo que piorou é o que ensina: dois níveis com vocabulário estreito recusa
MAIS que um nível largo. O mérito é do que está em cada nível, não de haver
dois. E as 64 que sobram são conduta de escritório que serviria a uma pizzaria
(*"Reentrar no sistema (logout/login) pode resolver falhas de exibição"*).

- **Guarda:** [`test_a_carta_precisa_ser_sobre_seguro.py`](../../backend/tests/test_a_carta_precisa_ser_sobre_seguro.py)
  — prova as duas direções com texto REAL do acervo, e a linha de controle
  troca UMA palavra para mostrar que o limiar de duas menções é de verdade.

**Continua aberto:**
- **item 2 · 🧑** aprovação humana para carta de origem não-seguradora. Hoje o
  filtro é vocabular, não semântico: ele barra o que não fala de seguro, não o
  que fala de seguro e é falso.
- **item 3 · 🤖** as 📊 64 `published` que o filtro recusaria **continuam no
  acervo e no Qdrant**. Nada foi escrito no banco. `reindexar_acervo.py` também
  não consulta o filtro — reindexar hoje devolve as 64 ao índice.
  Destrava: rodar `e_sobre_seguro` sobre as 12.063, marcar as recusadas e tirar
  o ponto do Qdrant, com as 64 lidas à mão antes.

---

## P-68 · ⚖️ Conflito canônico: "observer nunca envia" vs. o que o código faz

📊 `SPEC-069-canais-definitivos.md:57` diz *"guarda dura: observer nunca é canal
de saída"*. 📊 `integration_service.py:192-199` implementa
`PROPOSITOS_QUE_NUNCA_ENVIAM = {"observer"}` — mas ela só é consultada em **3
lugares**, todos de envio **frio** iniciado pela plataforma (alerta do Vigia,
follow-up, cobrança).

📊 O caminho **reativo** — responder quem escreveu — não passa por ela:
`webhook.py:276-278` fixa a integração que RECEBEU e `webhook.py:710-712`
responde por ela mesma. Com o agente ligado, **a resposta ao segurado sai pelo
`ab-obs-*`**. Isso é por desenho: é a promessa da tela.

**Não é bug — é uma frase mais absoluta que o código.** E é defensável: o risco
de bloqueio do WhatsApp está no envio frio, não em responder quem falou com você.

**O que destrava.** 🧑 Decidir qual vence antes do piloto e alinhar os dois:
ou a SPEC passa a dizer "observer não INICIA conversa", ou o código passa a
proibir de verdade — e aí a promessa de "mesmo número" cai junto.

**O que custa esquecer.** Alguém lê a SPEC, conclui que aquele número é mudo
para sempre, e desenha em cima disso.

---

## P-69 · 🧑 Um clique: reteceer os mapas do Atlas

**Um clique, e a cobertura de 10 seguradoras melhora sem escrever uma linha.**

📊 Os mapas em `ura_maps` são de **29/07/2026**. O mecanismo que desconta a
NÃO-ROTA da cobertura — pesquisa de satisfação e lista gerada pelo cliente — é
de **02–03/08**. **Os mapas são anteriores ao conserto.**

📊 Verificado contra o texto literal das duas telas de pesquisa da HDI: o
detector devolve `pesquisa_de_satisfacao` e **zero opções** nas duas. Ele está
certo; os mapas é que estão velhos.

Só na família HDI+Yelum são **20 opções fantasmas** (2 pesquisas × 5 notas × 2
seguradoras) contadas como "não cobertas" sem que exista trabalho a fazer.
Elas rebaixam os 36% e 34% e escondem qual é a cobertura real.

**O que destrava.** Painel → **Atlas** → botão **"Tecer mapas"**. É idempotente
e reprocessa o histórico inteiro. **Não depende de pareamento nenhum** — lê o
acervo que já temos.

**O que custa esquecer.** Toda decisão de prioridade da Fase 3 usa a cobertura
como número. Com 20 opções fantasmas dentro dela, a prioridade sai errada — e
o esforço vai para onde não precisava.

---

## P-70 · 🟠 O Follow-up pergunta e ninguém escuta

**O Founder olhou a Central de Agentes e perguntou se o Follow-up é legado,
duplicado, quebrado, ou se vale eliminar. A auditoria respondeu: nenhum dos
quatro. É metade construída, e a metade que existe é boa.**

### O que ele faz bem

📊 `_followup_schedule` agenda 45 min **depois do ETA real do prestador** — não
depois do protocolo — com janela educada 8h30–21h. Isso é produto pensado, não
encanamento. E é o **único** componente do sistema que fala com o segurado por
iniciativa própria depois do acionamento. Nada mais faz isso.

### O que está quebrado

```
1  a resposta do cliente NÃO É LIDA por ninguém
   a chave do acionamento é o telefone da SEGURADORA; o do cliente
   nunca casa, e a resposta cai no agente comum, que não sabe do que
   se trata. 📊 zero leitores no backend inteiro

2  o timer é apagado por baixo
   `_start_next_in_queue` roda na MESMA transição que criou o timer, e
   `start_live_dispatch` trata `monitoring` como sessão velha e limpa.
   Com fila na mesma seguradora, o follow-up morre ao nascer

3  é o único envio frio a segurado que fura o governador
   não respeita a parada de emergência, não conta nos tetos, não entra
   em `platform_sends`. E plugar direto no canal governado QUEBRA:
   `client_busy` considera ocupada toda sessão em `monitoring` — que é
   exatamente o estado em que ele roda. Precisa de exceção explícita

4  o "encerramento" não encerra
   só manda texto; a sessão fica viva até o TTL de 24h

5  a mensagem não entra no transcript
   o Espelho, a timeline e o dossiê não a mostram — o Vigia faz isso, ele não

6  zero teste
   nenhum teste chama `check_dispatch_followups`
```

### 📊 E o card verde era falso — isto já foi corrigido

O critério da Central é só *"o laço rodou nos últimos 15 min"*. O pulso é dado
**mesmo quando a varredura não acha nada**. "SAUDÁVEL · 0 ações" queria dizer
apenas *"rodei e não encontrei nada"*.

A descrição no catálogo passou a dizer a verdade em 03/08. **Um card amarelo
verdadeiro vale mais que um verde falso.**

### DUPLICAÇÃO — a resposta à pergunta do Founder

**Não duplica função.** 📊 O Vigia trata `monitoring` como estado terminal e se
cala exatamente onde o Follow-up age. E os públicos são opostos:

```
VIGIA      fala com a SEGURADORA e com o suporte da corretora
FOLLOW-UP  fala com o SEGURADO
```

**Duplica mecânica.** Dois jobs (20s e 60s) varrem o mesmo keyspace, com o mesmo
parsing e as mesmas chamadas. Uma terceira varredura existe para a tela.

**E há três homônimos que confundem** e não têm relação: o auxiliar comercial
"Follow-up de WhatsApp" (proposta), o card "Follow-up de Propostas · Em breve",
e a fase `follow_up` de `corridor_templates` — 📊 esta última com **zero
leitores em qualquer linguagem**.

### A recomendação

**Manter e completar, fundindo a MECÂNICA e mantendo os NOMES separados.**

Um varredor único que percorre `dispatch:active:*` uma vez e roteia por estado:
vivo → Vigia · `monitoring` → Follow-up. Mata a varredura dupla, mantém dois
cards na Central (papéis distintos), e cria o lugar natural para o passo 5 —
quando o cliente responde *"não chegou"*, quem já sabe alertar o suporte e
montar dossiê é o Vigia.

**O que destrava:** os 6 itens acima, na ordem. O item 2 vem primeiro — sem ele
os outros não importam, porque a mensagem nunca sai.

**O que custa esquecer:** o ciclo termina em *"aqui está seu protocolo"* e a
corretora nunca sabe se o serviço foi prestado. É a diferença entre acionar e
resolver.


---

## ✅ FECHADAS EM 03/08/2026 — o dia do formulário nativo

Registro do que saiu desta lista, com o que provou cada uma.

| # | O que era | Como fechou |
|---|---|---|
| **P-68** | conflito canônico "observer nunca envia" | decisão do Founder → **D-Canal-01**: observar é função muda; atender fala e nasce desligado |
| **P-69** | mapas do Atlas anteriores ao conserto da não-rota | 🧑 o Founder clicou em **Tecer mapas**. 📊 HDI 36→41%, Yelum 34→36%, Allianz 75% |
| **P-70 (2,3,5)** | o timer do Follow-up morria ao nascer; a pergunta não deixava rastro | `monitoring` com compromisso pendente deixa de ser sessão velha; a pergunta entra em `platform_sends` e no transcript |

### E o que a auditoria de ponta a ponta fechou no mesmo dia

```
R1   protocolo sozinho já avisa o segurado (o residencial da Allianz não
     captura eta nem link — a pessoa nunca sabia que o serviço foi aberto)
R2   sem protocolo, a retomada roda; COM protocolo, não — reabrir mandaria
     um segundo prestador para o mesmo carro
R3   o flow_token atravessa: o webhook copia o `interactive` e o buffer
     não o apaga na rajada
R4   tudo que o motor diz ao cliente vira rastro; falha de aviso alerta
     o suporte em vez de sumir no log
R5   o encerramento ENCERRA: marca resolvido e libera a sessão
R5b  má notícia também passa — cancelado, sem prestador, fora da área
```

### E os achados da revisão dos 13 corredores

```
🔴 1  o freio não disparava em 28 das 33 vezes (negrito do WhatsApp no
      *para*), no PONTO DE NÃO-RETORNO. E o CI estava verde porque a
      fixture escrevia a frase sem os asteriscos
🔴 2  `pessoa_no_local` era exigido por passos e não declarado — a sessão
      nascia "pronta" e travava no meio. O PORTÃO foi consertado, não os
      três passos: fecha a classe inteira
🔴 3  apelido de subserviço não resolvia na abertura (hidráulica,
      desentupidor, eletrodoméstico)
🟠 4  vidro exigia quem acompanha no local — vidro é agendado
🟠 5/6 três noop fora de ordem sombreavam o menu re-perguntado
🟠 7  `human_phase_guidance`: 4 blocos de orientação, zero leitores
🟡 10 instruções de guincho iam para pneu, bateria e chaveiro
```

**Restam de P-70:** o item 3 (ler e classificar a resposta do cliente e agir) e
o item 6 (teste com relógio de mentira). O item 5 — passar pelo canal governado
— continua aberto **de propósito**: exige exceção explícita para `monitoring`,
senão `client_busy` adia o follow-up para sempre.

---

## P-71 · 🧑 AMANHÃ: o acionamento REAL da HDI, em modo teste

**É a última coisa não provada da cadeia inteira, e não dá para provar sem ela.**

📊 Provamos que a mensagem de resposta a formulário **sai e o WhatsApp aceita**
(`Type: "InteractiveResponseMessage"`, entre dois números nossos). **Não**
provamos que a **seguradora** aceita essa resposta no meio de um atendimento.
São coisas diferentes, e só uma seguradora de verdade responde a segunda.

### O passo a passo

```
1  🧑  parear os WhatsApps das corretoras (Amandus, Resulta, AutoFleet)
2  🤖  conferir DISPATCH_FINALIZE_MODE=test e a allowlist
3  🧑  abrir conversa com a HDI pelo número da corretora
4  🤖  andar o menu até o formulário nativo chegar
5  🤖  responder AQUELE formulário — não um fabricado
6  🤖  ler o que a HDI devolve
```

**O freio segura antes do ponto de não-retorno.** 📊 E ele foi consertado em
03/08: não disparava em 28 das 33 redações reais, por causa do negrito do
WhatsApp. Agora dispara nas quatro formas conhecidas.

### O que este teste responde, e nada mais responde

```
a resposta chega com o flow_token certo?
a HDI aceita, ou descarta em silêncio?
`response_message` é exigido? (a hipótese nº 2 do documento do formulário)
`version` precisa viajar? (a hipótese nº 1)
```

**Também destrava:** a InfoCap (P-01) — sem ela o agente pergunta a placa ao
segurado em vez de confirmar a apólice.

**O que custa esquecer:** todo o resto está pronto e desligado esperando esta
prova. Sem ela, não há como ligar `INSURER_DISPATCH_LIVE` para corretora
nenhuma — e o produto continua sabendo acionar sem nunca ter acionado.

> Ver [`O-FORMULARIO-NATIVO-RESOLVIDO.md`](O-FORMULARIO-NATIVO-RESOLVIDO.md) §7
> (o que não está provado) e §8 (o que falta para 100%).


---

## ⚠️ AVISO SOBRE O ÍNDICE RÁPIDO DESTE ARQUIVO

📊 Auditado em 03/08/2026: o índice rápido acima ainda lista **P-05, P-06, P-07,
P-08 e P-14 como abertas**. As cinco foram fechadas pelos Blocos A, B, P e C da
SPEC-063 e estão provadas por teste.

**Quem confiar no índice vai reexecutar trabalho pronto.** A tabela de fechadas
(seção "FECHADAS EM 03/08/2026") é a que vale.

| Pendência | Fechada por | Guardada por |
|---|---|---|
| P-05 AutoFleet com agente ativo sem prompt | Bloco P | `test_a_corretora_nasce_completa.py` |
| P-06 handoff mente na falha | Bloco B | `test_handoff_chega_em_alguem.py` |
| P-07 handoff sem filtro de tenant | Bloco B | idem |
| P-08 CPF vaza por dois caminhos | Bloco A | `test_quem_responde_o_segurado.py` |
| P-14 briefing sem governador | Bloco C | `test_governador_de_envio.py` |

---

## ✅ O LOTE 🤖 FECHADO EM 03/08/2026 — oito de uma vez

📊 Suíte **134 → 141 verdes** · `tsc` 0 · tabela de rotas monta (286) ·
`agent-health` 24/24. Verificado por mim, não aceito de relatório.

| # | O que era | Como fechou |
|---|---|---|
| **P-36** | 3 caminhos escreviam o prompt do agente **sem o portão** — foi por um deles que a AutoFleet ficou ativa e muda | o portão virou função única em `provision-tenant.ts`, e os três passam por ela |
| **P-56** | `selectedButtonId` × `selectedButtonID` no inbound — **o mesmo defeito dos 937 cliques**, noutro arquivo, vivo há 3 semanas depois de consertarmos o gêmeo | busca tolerante, e agora ela mora **num lugar só** |
| **P-34** | a varredura de acionamento órfão rodava 1× por processo | job periódico de 5 min |
| **P-37** | `agent-health` não via agente **mudo** | vê, e aparece na ficha |
| **P-38** | `unknown` sumia do radar | classe própria, com sinal deliberadamente mais fraco |
| **P-43** | golden test esperava `ready_for_approval` | 📊 **o caso é que estava errado**: esse estado só existe em `corridor_runs`, a tabela abandonada. Corrigido com o texto original preservado |
| **P-46** | `encaminha` declarado e sem consumidor | desfecho `encaminhado` de verdade, ensinado a 7 consumidores |
| **P-47** | `infer_ramo_servico` devolvia "residencial" genérico → `subservico_invalido` | 4 subserviços com nome próprio |

### Três achados que não estavam na lista

```
1  scripts/agent-health.test.mjs NUNCA RODOU — importava .ts e o node morria
   no import, antes da primeira asserção. Teste que não roda é pior que teste
   ausente: ele conta como cobertura. Consertado e virou `npm run test:agent-health`

2  o stub de test_audio_nao_pode_sumir.py era justificado por um fato VENCIDO
   (dizia que o módulo puxava a stack de IA; 📊 ele importa `json` e `typing`).
   Passou a carregar o módulo real — CLAUDE.md §9.3

3  test_o_clique_nao_se_perde.py C4/C5 agora guardam que a busca tolerante mora
   em UM LUGAR SÓ. Duas listas de grafias em dois arquivos foi exatamente como
   o P-56 sobreviveu três semanas ao conserto do observador
```

### E duas decisões de julgamento, registradas porque são decisões

**P-46 foi maior que as "~30 linhas" estimadas.** Encaminhar é um **desfecho**, e
desfecho sem estado é desfecho que ninguém enxerga. Por isso o estado novo.

E o corredor **não fecha na âncora**: 📊 o link do formulário da Porto vem na
mensagem *seguinte*. Fechar antes entregaria ao segurado uma frase sobre um
formulário — sem o formulário. Janela de 3 mensagens; sem link, vai para uma
pessoa. **Ninguém digita endereço de vidro de memória.** A Zurich fecha na hora,
porque 📊 a mensagem dela não traz link nenhum: esperar um transformaria o
desfecho certo em handoff.

**P-38 — a fraqueza do sinal não depende de ninguém lembrar.** `unknown` nasce
num tier que a própria SPEC-059 recusa como origem de alerta crítico. O teste
prova isso forçando `severity="critical"` e vendo o schema reprovar.

---

## P-72 · 🟠 O portão do CI não pega o defeito que aconteceu

📊 `.github/workflows/gate.yml` roda **dois passos**: um pacote de regressão
Python e `npx tsc --noEmit`. **Nenhum `.mjs`, e nem o `run_all.py`** — hoje 146
testes que ninguém executa automaticamente.

**E a consequência é precisa, não genérica.** Desde 04/08 os mapas do front são
`Record<DispatchState, …>` exaustivos por tipo. Então:

```
estado novo no TypeScript sem rótulo   → o CI PEGA (via tsc) ✅
estado novo no PYTHON que o front não conhece → o CI NÃO PEGA ❌
```

**E o segundo é exatamente o que aconteceu.** `encaminhado` e `resolvido`
nasceram no Python e ficaram órfãos em sete arquivos de tela — um caso encerrado
com sucesso aparecia ao corretor como *"conversando com a seguradora agora"*.

O guarda que cobre isso **existe** — `npm run test:atendimento-estados`, que lê o
Python e compara com a lista canônica do TS — e **não roda no CI**.

**O que destrava:** 🧑 decisão de mexer no gate. Acrescentar `run_all.py` e os
`npm run test:*` é pequeno, mas muda o que bloqueia um merge — e isso é chamada
sua, não minha.

**O que custa esquecer:** o guarda existe e a promessa que ele carrega ("o dia em
que o backend criar um estado que o front não conhece, o teste fica vermelho")
só vale se alguém digitar o comando.

## P-73 · 🟡 `npm run lint` está vermelho no repositório inteiro

📊 2.161 erros `prettier/prettier`, quase todos `Delete ␍` — quebra de linha do
Windows. **Linha de controle:** `components/patterns/StatusPill.tsx`, que
ninguém tocou nesta jornada, dá 36 erros iguais. **É pré-existente.**

Ninguém vê porque `next.config.js` traz `eslint.ignoreDuringBuilds: true` e o
gate não roda lint. Consertar é reformatar o repositório inteiro — 🧑 decisão.

## P-74 · 🟡 O `delete_agent` do backend não filtra por tenant

`backend/app/services/agent_service.py:delete_agent` arquiva o agente com
`.update({"is_active": False}).eq("id", ...)` — **sem `.eq("company_id", ...)`**.
É a mesma classe do defeito que o P-38 fechou no `update_agent`, e o backend roda
com service role: RLS sem policy não protege contra erro de filtro no código
(CLAUDE.md §7).

Não foi consertado junto porque estava fora da lista do bloco e a correção muda
o comportamento quando a resolução do tenant falha — decisão de contrato, não de
digitação.

**O que destrava:** 🤖 execução, junto com uma varredura das outras escritas de
`agents` escopadas só por `id`.
**O que custa esquecer:** um `id` errado (ou adivinhado) desliga o agente de
outra corretora, e o soft delete não deixa rastro de quem pediu.

## P-75 · 🟡 `scripts/admin-agent-blueprints-canonical.test.mjs` não roda

📊 04/08/2026: `node scripts/admin-agent-blueprints-canonical.test.mjs` morre no
import, antes da primeira asserção — ele faz
`import ... from '../lib/admin/agent-blueprints-canonical.ts'`, e o node não
resolve a extensão `.ts` em ESM. **Pré-existente**: confirmado rodando o arquivo
com `git stash` aplicado, antes de qualquer mudança desta jornada.

É exatamente o defeito que `scripts/agent-health.test.mjs` já teve e documenta —
lá foi resolvido transpilando o módulo com a API do próprio TypeScript. A
correção é copiar aquele `carregarTS()`.

**O que destrava:** 🤖 execução (o padrão já existe no repositório).
**O que custa esquecer:** `npm run test:agent-blueprints-canonical` aparece na
lista de scripts e dá a impressão de que os blueprints canônicos têm prova
executável. Não têm — e é esse arquivo que compõe o prompt de toda corretora.

## P-76 · 🟢 A varredura do portão do prompt cobre `agents` e `companies`, e só

`backend/tests/test_o_portao_do_prompt_e_um_so.py` passou a varrer o repositório
por escritas nas tabelas onde `agent_system_prompt` mora, classificando cada uma
como transparente (chaves à vista) ou opaca (variável, spread, `**`).

Ela **não** enxerga escrita por RPC do Postgres — `apply_release_rollout` e
`rollback_release_rollout` gravam a coluna dentro do banco. Os dois estão
cobertos por casos dedicados ([3]), não pela varredura.

**O que destrava:** 🤖 execução — varrer `supabase.rpc('...')` e exigir releitura
para as RPCs que tocam a coluna.
**O que custa esquecer:** uma RPC nova que escreva o prompt nasce invisível para
a varredura, que é a peça que promete "não sobrou nenhum".

---

## P-77 · 🧑 O ÚLTIMO INTERRUPTOR: o agente de atendimento nasce desligado

📊 Medido em 04/08/2026: os **quatro** agentes de atendimento do sistema estão
com `is_active = false` — Saionara (Resulta), Maria Regina (AutoFleet), JOANA
(Amandus), Even (Blueprint).

**Isso não é defeito.** É o modo observação da [D23], funcionando como desenhado:
o número segue pareado, a atendente humana responde pelo celular, o sistema
captura tudo e o agente não fala com ninguém.

Mas tem uma consequência que vale escrever: **enquanto estiver assim, todo o
portal de vidros fica inerte.** Um segurado pode mandar "quebrei o vidro" e nada
acontece — não porque falte código, e sim porque a boca está fechada.

**O que destrava:** 🧑 Founder — ligar o Agente de Atendimento no dashboard da
corretora. É um clique, e ele liga a cadeia inteira.
**O que custa esquecer:** achar que o portal "não funciona" quando ele nunca foi
chamado. É o tipo de conclusão que faz desmontar o que está certo.

---

## P-78 · 🟡 `vidro do porta-malas` é lido como vidro lateral

📊 `identidade_peca("vidro do porta-malas")` devolve `{lateral}`, porque
**"porta"** é sinônimo de lateral no vocabulário de peças. O portal ofereceria
`VIDRO DE PORTA` para um vidro que é do porta-malas.

Achado pelo executor do bloco 7.5 ao montar o catálogo de perguntas; é falha
**pré-existente** do vocabulário compartilhado, não do trabalho novo.

**O que destrava:** 🤖 execução — `_EXPRESSOES` resolve `porta-malas` /
`porta malas` / `portamalas` ANTES de separar em tokens, como já faz com
`para brisa`. É o mesmo mecanismo, e cabe em três linhas.
**O que custa esquecer:** um vidro trocado errado, e o portal proíbe corrigir —
teria de abrir OUTRO acionamento.

---

## P-79 · 🟠 O portal manda `especificos`, mas a tool não tem campo para o LADO

O bloco 7.5 abriu `especificos` no schema da `portal_action`, e as respostas do
80% (película, dianteira/traseira, lado) finalmente chegam ao portal.

Falta o outro lado da moeda: **a chave de idempotência não conhece o lado.**
📊 O portal diz, literalmente, que *"se o item possuir lateralidade será
necessário abrir uma nova solicitação para o outro lado"*. Dois vidros quebrados
são dois pedidos — e, se o agente escrever a mesma `peca` genérica nos dois, o
segundo é **barrado** pela idempotência como se fosse repetição.

A frase de "já existe" ensina a saída (*descreva a peça com o lado*), mas
depender do texto para o modelo acertar é o que esta SPEC inteira está desfazendo.

**O que destrava:** 🤖 execução — `especificos.lado_motorista_ou_carona` entra
na `chave_de_idempotencia` quando estiver presente.
**O que custa esquecer:** o segundo vidro nunca é aberto, e o segurado descobre
quando o vidraceiro chega e conserta um só.

---

## P-80 · 🟡 Telas do portal que ainda não foram medidas

Do mapa [`O-PORTAL-DE-VIDROS-TELA-POR-TELA.md`](O-PORTAL-DE-VIDROS-TELA-POR-TELA.md) §7:

| Lacuna | O que destrava |
|---|---|
| **Consultar atendimento** — o acompanhamento oficial | 🧑 uma captura de tela |
| Perguntas específicas de retrovisor, farol, lanterna, vigia, teto | 🧑 captura ou 1ª execução real |
| Telas de **roda/pneu/suspensão** (só a Porto oferece) | 🧑 uma captura na Porto |
| Quais seguradoras da lista realmente atendem vidros | 🤖 tentativa por seguradora |

**Nenhuma impede o corredor de funcionar** — todas caem no caminho adaptativo,
que lê a tela real. Elas definem quanto o robô precisa pensar em vez de
reconhecer. A primeira é a mais valiosa: hoje prometemos "acompanho até o fim" e
a fonte oficial desse acompanhamento existe e não está ligada.

**O que custa esquecer:** o `especificas_mapeadas()` já declara em voz alta o que
não conhece — então o risco não é errar calado, é continuar pensando mais do que
o necessário.

---

## P-81 · 🟡 O cérebro do portal é OpenAI; o resto do produto poderia decidir isso

📊 `PORTAL_VISION_MODEL` passou de `gpt-4o-mini` para `gpt-4o` em 04/08, com
rede de segurança: erro de modelo cai uma vez no antigo, para que um nome
inválido nunca custe um acionamento.

📊 `app/core/config.py` só declara `OPENAI_API_KEY` — não há chave Anthropic no
backend. Trocar o cérebro do portal por um modelo Claude exigiria uma chave nova.

**O que destrava:** 🧑 Founder — decidir se vale, e fornecer a chave.
**O que custa esquecer:** nada imediato. É otimização, não trava — e o
preenchimento determinístico do bloco 7 já tirou do modelo a maior parte do
trabalho onde ele errava.

---

## P-82 · 🟡 `_expandir_caps` recebe um `set` e não expande nada

`graph.py:227` chama `capacidades_ativas(_active)` com um **set**, e a função
começa com `if not isinstance(ativas, dict): return ativas`. Ou seja: o alias
`platform.web.search` → `platform.research.search` nunca acontece naquele ponto.

Achado de passagem ao consertar o portão do portal (bloco 7.1). Não é do escopo
desta SPEC e **não** foi tocado — mexer nisso muda permissão de pesquisa, que é
outro assunto.

**O que destrava:** 🤖 execução — ou a função aceita `set`, ou a chamada passa o
dicionário resolvido. Com teste que prove a expansão acontecendo.
**O que custa esquecer:** quem tinha a capability antiga não ganha a nova no
cutover — exatamente o que o expand-first prometeu evitar.

---

## P-83 · 🧑 METADE DA SPEC-065 ESTÁ NO AR; A OUTRA METADE ESPERA UM CLIQUE

📊 Medido em 04/08/2026, depois do deploy do commit `79077f6`:

```
web           200        ✅ no ar
API           healthy    ✅ no ar
portal-worker build_time 2026-08-04T12:32:36Z   ❌ NÃO reconstruiu
```

Verifiquei por 4 minutos, de 30 em 30 segundos: o `build_time` não mudou. **O
portal-worker é um serviço próprio no EasyPanel, com gatilho de deploy próprio,
e eu só tenho os gatilhos da API e do web.**

### O que isso significa, arquivo por arquivo

| Onde | Serviço | Está no ar? |
|---|---|---|
| capability + portão do `portal_action` (`graph.py`) | API | ✅ |
| roteamento "sem corredor de vidro → portal" (`insurer_dispatch_tool.py`) | API | ✅ |
| Vigia do Portal (`vigia_do_portal.py`, `buffer_processor.py`) | API | ✅ |
| idempotência e `session_id` (`portal_tool.py`, `portal_params.py`) | API | ✅ |
| campo `especificos` + descrição da tool | API | ✅ |
| perguntar antes de abrir (`perguntas_do_portal_de_vidros.py`) | API | ✅ |
| as duas migrations | Supabase | ✅ (aplicadas e verificadas) |
| **preenchimento determinístico + modelo** (`adaptive.py`) | **worker** | ❌ |
| **vocabulário do 80% + loja crítica** (`vidros_lanternas.py`, `adaptive.py`) | **worker** | ❌ |

**A parte que decide se o portal é chamado está no ar. A parte que decide o que
ele digita, não.**

⚠️ Consequência concreta enquanto isto durar: se um acionamento rodar agora, ele
usa o `gpt-4o-mini` antigo, sem preenchimento determinístico, e `"menor que 10
cm"` ainda pode virar **"Maior (troca do vidro)"**. 📊 Na prática o risco é
teórico hoje — a [P-77] mantém os agentes de atendimento desligados, então
nenhum acionamento nasce. Mas as duas pendências têm de ser resolvidas **na
ordem certa: esta primeiro, a P-77 depois.**

**O que destrava:** 🧑 Founder — uma das duas:
1. clicar **Deploy** no serviço `portal-worker` no EasyPanel, ou
2. me passar o gatilho dele (`http://187.77.45.227:3000/api/deploy/<token>`),
   do mesmo jeito que passou o do `evolution-go-teste`.

**Como conferir que funcionou:** o `build_time` em
`https://autobrokers-intelligence-os-portal-worker.golhpm.easypanel.host/health`
tem de ser MAIOR que `2026-08-04T12:32:36Z`.

**O que custa esquecer:** ligar o atendimento (P-77) com o worker velho no ar. O
sistema passaria a acionar de verdade, com os defeitos que esta SPEC consertou
ainda em produção — e o pior deles troca um para-brisa que tinha conserto.

---

## P-84 · 🧑 DECISÃO: o que o Observador pode gravar, por corretora

📊 Medido em 04/08/2026: as **três** memórias de escopo dizem `insurers_only` —
AMANDUS, AutoFleet e Resulta. Não porque alguém tenha escolhido: foi assim que a
**contenção de 29/07** as deixou, quando o Observador capturou 630 contatos
pessoais de um celular particular.

**Uma emergência virou política sem ninguém decidir.**

E a consequência é concreta: se a Saionara e a Regina parearem amanhã sem tocar
nisso, **nenhuma conversa de segurado será capturada** — só as de seguradora. É
exatamente o oposto do que a curadoria e as cartas precisam.

### Os dois custos, para a decisão ser sua e não minha

| Escopo | O que ganha | O que arrisca |
|---|---|---|
| `insurers_only` | nenhum dado de terceiro entra | 📊 sete dias de observação rendem **zero** conversa de atendimento |
| `insurers_and_clients` | o material das cartas | se o telefone for pessoal, entra conversa particular — e o sistema **não tem como distinguir** (📊 não existe tabela de segurados com telefone neste banco) |

O erro de gravar de MENOS é reversível: 📊 o `history_sync` reentregou 133
eventos de 29/07–03/08 numa rajada de 6 minutos após um restart. O de gravar de
MAIS não é.

**O que destrava:** 🧑 Founder — dizer, por corretora: o número que vai ser
pareado é o **celular de trabalho** dela? Se sim, `insurers_and_clients`. Eu
gravo antes do QR (é uma linha), e a memória passa a preservar para sempre.
**O que custa esquecer:** parear as duas e descobrir dias depois que não há
material nenhum para destilar.

---

## P-85 · 🔴 O handoff humano está RECUSADO para AutoFleet e Resulta

📊 As duas apontam para o **mesmo** destino de suporte (o mesmo grupo de
WhatsApp), replicado em `acionamento_profile`. E `dispatch_router` recusa
destino compartilhado **de propósito** — para não entregar o CPF de um segurado
na corretora errada.

Consequência com o agente ligado: *"quero falar com uma pessoa"* **não aciona
ninguém**. E o dossiê do Vigia do Portal morre no mesmo lugar.

📊 A AMANDUS tem destino próprio e funciona — o que prova que o mecanismo está
certo e o dado é que está compartilhado.

**O que destrava:** 🧑 Founder — um grupo de WhatsApp por corretora.
**O que custa esquecer:** o handoff é a última rede. Ligar o agente sem ela é
prometer "não vou te deixar travado" sem ter para onde passar.

---

## P-86 · 🟠 A allowlist de entrada atende só um número

📊 `ATTENDANT_INBOUND_ALLOWLIST` está preenchida em produção com **um** número.
Enquanto estiver assim, ligar o agente faz ele atender só esse número e **ignorar
todo o resto em silêncio** — botão verde, tela dizendo "atendendo", nada
acontecendo para o segurado.

Isso é ótimo para o teste que o Founder quer fazer na AMANDUS. É armadilha no
dia do go-live.

**O que destrava:** 🤖+🧑 esvaziar a variável quando for atender de verdade —
**e só depois de P-85 estar fechada**, senão o agente atende e não tem para quem
passar quando travar.
**O que custa esquecer:** achar que o agente está quebrado quando ele está
obedecendo.

---

## P-87 · 🔴 O destilador está DESLIGADO, e o material expira em outubro

📊 `DESTILADOR_TETO_POR_RODADA` tem padrão **`0`** — e `0` significa "não
destile nada". Resultado medido:

```
69.150 transcrições capturadas          ✅
 8.872 sessões fechadas                 ✅
 1.460 sessões NUNCA destiladas         🔴  (AutoFleet 480 · Resulta 980)
 9.416 cartas, TODAS nascidas em 28–30/07 — a máquina rodou uma vez e parou
```

E o purge de retenção apaga o cru 90 dias depois de capturado: 📊 por volta de
**27/10/2026**. Sem religar o teto, esse material **expira sem virar carta**.

**O que destrava:** 🤖 execução — definir o teto e rodar uma leva controlada,
conferindo custo. É a peça que transforma conversa capturada em conhecimento, e
hoje ela está de pé e desligada.
**O que custa esquecer:** o acervo inteiro vira lixo com data marcada.

---

## P-88 · 🟠 O telefone pareado nunca é gravado

📊 `observed_sessions.observer_number` da AutoFleet é `6955221` — os dígitos do
**nome da instância** (`ab-obs-6c9c55e22f-1`), não um telefone. O número que
realmente pareou não é persistido em lugar nenhum.

É a causa direta da pergunta do Founder — *"já tinha um pareado e eu não sei
qual era"*. Não dava para saber: o sistema não guarda.

📊 E há fallback literal `"unknown"` (167 eventos da Resulta já estão assim) e
`"attendance-channel"` (1 transcrição).

**O que destrava:** 🤖 execução — `integrations.paired_jid` / `paired_phone_e164`
/ `paired_at`, gravados na confirmação da conexão, com backfill do provedor. Toda
tela passa a dizer `5547*****463 · pareado em 29/07`.
**O que custa esquecer:** nenhuma auditoria de "quem está conectado" é possível,
e a próxima confusão vai custar o mesmo tempo que esta.

> **Escrito em 04/08/2026 (SPEC-063).** As três colunas nascem na migration
> `20260804_03_o_repareamento_nao_duplica.sql` (**ainda não aplicada** — P-91), e
> quem as preenche são `pairing_orchestrator._mark_connected` (do
> `/instance/status`) e o `connection.update` do Observador. A regra de leitura
> mora sozinha em `app/services/whatsapp/numero_pareado.py` e **não inventa**:
> sem JID do provedor, devolve `None` em vez de deduzir do nome da instância.
>
> ⚠️ **Sem backfill, e de propósito.** O telefone das linhas já pareadas não
> existe em campo nenhum deste banco — só apareceria num `/instance/status` ao
> vivo. Reconstruí-lo a partir do `identifier` seria repetir o engano que criou o
> `6955221`. As três integrações atuais ficam com o campo **vazio até reparear**.
>
> O fallback literal também morreu: `"unknown"` passou a ser
> `{company_id[:8]}:sem-digitos`, então duas corretoras sem dígito no identifier
> deixam de colidir. 📊 Os 167 eventos já gravados com `"unknown"` **continuam
> como estão** — reescrevê-los mudaria a chave de dedupe deles.

---

## P-89 · 🟠 Os índices de deduplicação não têm `company_id`

📊 `ux_attendance_transcripts_dedupe` e `uq_observed_events_msg` são
`(observer_number, message_id)` — **sem corretora**. Somado ao `observer_number`
que cai em `"unknown"` (P-88), duas corretoras podem ter sessões **fundidas**.

Hoje é teórico. **Com duas corretoras pareando em dias, deixa de ser.**

**O que destrava:** 🤖 execução — `company_id` nos dois índices, antes do segundo
pareamento.
**O que custa esquecer:** transcrição de uma corretora descartada como duplicata
da outra — e o pior tipo de perda, a silenciosa.

> **Escrito em 04/08/2026 (SPEC-063).** Os índices com `company_id` nascem na
> migration `20260804_03` (**não aplicada** — P-91), e nascem **ao lado** dos
> antigos, não no lugar deles. O motivo está medido:
>
> O código grava com `on_conflict`, que o Postgres exige que case **exatamente**
> com um índice único existente. Dropar o antigo antes de o deploy chegar faria
> `_store_history_event` levar `42P10` — e como `_ingest_conversation` engole a
> exceção, **a ingestão do histórico gravaria zero linha reportando sucesso**.
> Com os dois vivos, as duas grafias funcionam e a ordem entre migration e deploy
> deixa de importar.
>
> 📊 Medido antes de escrever: **0 linhas** colidem com a chave nova e **0** pares
> `(observer_number, message_id)` existem em duas corretoras — a construção dos
> índices não pode falhar, e nada muda de lado.
>
> ⚠️ **A fusão entre corretoras só fecha de fato com o DROP dos antigos** (P-91),
> porque enquanto existirem são eles, mais estritos, que decidem.
> `test_o_repareamento_nao_duplica.py` [3] mede as três configurações e mostra a
> transição colapsando — de propósito, para que o estado intermediário não seja
> confundido com o final.

---

## P-91 · 🧑 A migration `20260804_03` está escrita e NÃO aplicada

O arquivo `backend/supabase/migrations/20260804_03_o_repareamento_nao_duplica.sql`
existe, com APPLY/VERIFY/ROLLBACK, e **nunca foi executado** — por instrução
explícita. Ele é o que fecha P-88 e P-89.

Enquanto não for aplicado, o código já em produção continua funcionando pela
chave antiga (a reserva existe justamente para isso), mas:

- `paired_phone_e164` não existe → o telefone pareado continua sem ser gravado;
- as chaves de dedupe continuam sem `company_id`.

**O que destrava:** 🧑 Founder aplica a migration e roda o VERIFY do cabeçalho
(cinco consultas, incluindo a que prova que o guarda **consegue** falhar).
Depois: 🤖 deploy do backend — e só **então** a segunda migration, de uma linha
por índice, com os três `DROP INDEX` já escritos no cabeçalho do arquivo.
**O que custa esquecer:** parear a Regina e a Saionara antes disso significa
perder a única janela em que a separação por corretora era barata — depois dela,
os dados das duas já estarão dentro da mesma chave.

---

## P-92 · 🟠 Um parâmetro do onboarding pode duplicar o acervo inteiro

📊 `admin_atlas.py:346` — `instance = _obs_instance_name(company_id, int(body.get("seq") or 1))`.

O `seq` vem do **corpo do request**. E `observer_number` é `_digits()` do nome da
instância: `ab-obs-6c9c55e22f-1` → `6955221`; `ab-obs-6c9c55e22f-2` → `6955222`.

Chave diferente = **nada casa** = o history_sync regrava tudo. 📊 São 9.982
transcrições da AutoFleet e 59.168 da Resulta a um dígito de distância.

O caminho normal é seguro — `pairing_orchestrator._instance_name` crava `-1` e
`_prepare_and_connect` reusa o `instance_id` já gravado. O risco é só esta porta.

**O que destrava:** 🤖 execução — ignorar `seq` quando já existe integração
observer para a corretora, ou recusar `seq != 1` sem confirmação explícita.
Não foi feito aqui porque `admin_atlas.py` está fora do escopo que me foi dado.
**O que custa esquecer:** o pareamento "manual de emergência" é justamente o que
alguém usa sob pressão, que é quando ninguém confere um campo numérico.

---

## P-93 · 🟡 1.035 linhas ao vivo ainda podem ganhar cópia no repareamento

📊 04/08/2026: as duas fontes gravam `message_id` de famílias incompatíveis —
`history_sync` usa `hist-…` (100% das 85.766 linhas) e o caminho ao vivo usa o id
do WhatsApp (100% das 1.035). O índice único não tem como saber que são a mesma
mensagem.

O cruzamento por conteúdo em `history_ingest._impressoes_ao_vivo` fecha isso
**daqui para a frente** e está provado em `test_o_repareamento_nao_duplica.py` [4].
Duas ressalvas honestas:

1. Ele só compara mensagens **com texto**. Áudio, foto e documento ficam de fora
   de propósito (regra de `atlas/mensagem.py`: sem texto não há identidade
   segura, e perder áudio é irreversível). 📊 São 9.002 mídias no Espelho.
2. Ele é *fail-open*: se a leitura falhar, a ingestão segue sem o cruzamento — o
   pior desfecho vira uma cópia, que se conserta, em vez de uma mensagem
   descartada, que não.

**O que destrava:** 🤖 execução — depois do primeiro repareamento, rodar o
detector abaixo e decidir sobre o que sobrar:

```sql
SELECT company_id, counterparty, wa_timestamp, direction, msg_type, count(*)
  FROM attendance_transcripts
 WHERE wa_timestamp IS NOT NULL AND text IS NOT NULL
 GROUP BY 1,2,3,4,5 HAVING count(*) > 1;
```

**O que custa esquecer:** a duplicata de mídia não aparece em contagem de
conversa, aparece no custo de transcrever o mesmo áudio duas vezes.

---

## P-91 · 🧑 Duas linhas de env que podem fazer o botão não funcionar

Herança do desenho antigo. **Se o Founder ligar o agente e nada acontecer, é
uma destas duas** — e não haverá erro nenhum para explicar por quê.

1. **`INSURER_DISPATCH_LIVE`** — o padrão do código passou a ser ABERTO, mas um
   `false` *escrito* continua fechando (de propósito: ignorar o que um operador
   escreveu é discordar dele em silêncio). O `.env.example` antigo trazia
   `INSURER_DISPATCH_LIVE=false`; se o ambiente do EasyPanel herdou essa linha,
   **apague-a**.
2. **`PORTAL_REAL_ENABLED`** (serviço `portal-worker`) — com ela desligada o
   worker sobe, responde `/health` e **não pega job nenhum**. O acionamento de
   vidros é enfileirado e fica em `queued` para sempre. 📊 Os 39 jobs de
   `abrir_atendimento` têm `started_at` preenchido (último em 10/07/2026), o que
   indica que ela já esteve ligada — mas o estado atual do ambiente não é
   legível daqui.

**O que destrava:** 🧑 Founder — conferir as duas variáveis no EasyPanel.
**O que custa esquecer:** o botão vira decoração, sem mensagem de erro.

---

## P-92 · 🤖 O chat interno também alcança o portal de vidros

📊 04/08/2026, `capability_bindings`: `tenant.portal.execute` está **ligada para
`core` e `auxiliary`** (e desligada para `attendance`). O chat interno da
corretora, portanto, também recebe `portal_action` — e ele **não** passa pelo
portão `attendance_agent_active` do webhook, porque fala com o corretor, não com
o segurado.

📊 Alcance real hoje: **uma** corretora. A capability exige conexão
(`requires_connection=true`, provider `portal_worker`) e só a Resulta
(`04b5cdbc…`) tem linha em `portal_accounts`; o `core` dela está ativo.

Não é um buraco aberto: `portal_tool` subordina o `confirm` ao mesmo
interruptor, então com o agente de atendimento desligado o job do chat interno
nasce `confirm=False` e para no 80% — exatamente o que já fazia. Mas **quando o
agente for ligado, este caminho também passa a poder abrir pedido de verdade.**

**O que destrava:** 🧑 decisão de produto — o corretor pode abrir um chamado de
vidro pelo chat interno? Se não, é um `UPDATE capability_bindings SET
enabled=false WHERE agent_role='core' AND capability_key='tenant.portal.execute'`.
**O que custa esquecer:** ninguém procura o acionamento de vidros no chat
interno, e é de lá que ele pode sair.

---

## P-93 · 🤖 Um job parado no 80% bloqueia o pedido que agora poderia ser aberto

A chave de idempotência (`idx_portal_jobs_pedido_vivo`) bloqueia todo status
menos `failed` — inclusive `needs_human`. Correto para o que ela foi feita.

Mas um job que rodou com `confirm=False` **não abriu atendimento nenhum** (é o
que `confirm=False` garante: `run_adaptive` para em `is_confirm_screen`). Se um
pedido foi tentado com o agente desligado e ficou em `needs_human`, a mesma
placa + peça + data com o agente ligado recebe *"já existe um atendimento
aberto"* — e não existe.

📊 Alcance hoje: **zero.** Os 91 jobs históricos têm `idempotency_key IS NULL`
(a migration não fez backfill de propósito) e o último `abrir_atendimento` é de
10/07/2026. A janela é só entre agora e o clique no botão.

**O que destrava:** 🤖 execução — ou marcar `failed` o job de 80% cujo
`params->>'confirm'` é `false` quando uma chamada nova está liberada, ou aceitar
o bloqueio e corrigir a frase, que hoje afirma um atendimento que não existe.
**O que custa esquecer:** um segurado ouve que o pedido dele já está aberto, e
não está.

---

## P-94 · 🟠 O mascarador chama de `{CPF}` o celular de 11 dígitos

📊 Medido em 04/08/2026 nos 10 mapas `observed`: **46 nós em 6 seguradoras**
guardam a frase *"O número de telefone {CPF} está correto?"*. Um deles é a tela
mais percorrida da HDI (20 passagens).

```sql
select count(*) from ura_maps m, jsonb_each(m.map->'nodes') k
 where m.status='observed'
   and k.value->>'text' ~* '(telefone|celular|whatsapp|contato)[^\n]{0,40}\{CPF\}';
```

A causa é ordem de regra, não sorte. Em `templater._PII_PATTERNS` o padrão de
CPF vem antes do de telefone, e `\d{3}\d{3}\d{3}\d{2}` casa exatamente os 11
dígitos de um celular com DDD. O telefone nunca chega a ser testado.

O dado continua protegido — o número sai da mesma forma. O que se perde é a
**estrutura**, que é justamente o que o Atlas existe para guardar: a tela diz
que pergunta CPF quando ela pergunta telefone. CLAUDE.md §12.1 manda consertar o
campo, não o texto — e aqui o campo é o rótulo do placeholder.

Desambiguar 11 dígitos não é trivial: `47988087463` é um celular válido e um CPF
possível. A pista boa é a palavra ao redor (`telefone`, `celular`, `contato`,
`WhatsApp`) — a mesma que `_ANSWER_HINTS` já usa para outra finalidade no mesmo
arquivo.

- **Destrava:** 🤖 uma regra em `templater.py` que, havendo `telefone|celular|
  contato|whatsapp` até ~40 caracteres antes do número, marque `{TELEFONE}`
  antes de o padrão de CPF rodar. Reprocessar os mapas depois.
- **Dono:** 🤖 execução — **não foi feito nesta passada porque `templater.py`
  estava em edição por outra frente** (04/08/2026).
- **Custa se esquecer:** o agente que ler o mapa vai responder um CPF onde a URA
  pede telefone, e a tela seguinte é de erro. E cada leitor novo do mapa herda a
  mentira.

## P-95 · 🟠 O mesmo texto vira vários nós, e isso elegeu a raiz errada da Porto

📊 Medido em 04/08/2026: nós que repetem os 80 primeiros caracteres de outro —
yelum 12,2% (72 de 590) · hdi 10,6% · porto 10,2% (86 de 841) · azul 7,2% ·
allianz 6,6% · o resto abaixo de 4%.

```sql
with n as (select m.insurer_key, left(k.value->>'text',80) p80
             from ura_maps m, jsonb_each(m.map->'nodes') k where m.status='observed')
select insurer_key, count(*)-count(distinct p80) from n group by 1;
```

A identidade do nó é o hash do texto inteiro templatizado. Quando sobra
qualquer coisa variável no meio da frase, a mesma tela vira vários nós. O caso
dominante é **nome de pessoa fora da saudação**: a regra `{NOME}` só cobre nome
COLADO em "Olá,"/"Oi,", e a Porto escreve *"Oi, sou assistente virtual da Porto
👋\n\nFulano, estou aqui pra falar sobre…"* — o nome vem depois da quebra.

**Consequência medida:** a eleição da raiz é por contagem de aberturas, e conta
por nó. 📊 Das 149 sessões da Porto, 56 começam por essa saudação e 20 por *"Eu
estou falando com Fulano?"* — mas cada nome vira um nó de 1 voto. `"Aguarde um
momento 🙂"`, que não fragmenta, juntava 10 votos num nó só **e ganhava a
eleição**. O Tecelão agora tira tela de espera da urna (04/08/2026), o que
conserta o sintoma; a fragmentação continua.

⚠️ **Não conserte fundindo por prefixo.** 📊 A Porto tem quatro grupos distintos
com os MESMOS 80 primeiros caracteres e continuações diferentes (sinistro,
vistoria, reparos) — fundi-los juntaria fluxos que não são o mesmo.

- **Destrava:** 🤖 alargar o mascaramento de nome em `templater.py` (nome depois
  de quebra de linha, e no molde "falando com Fulano?"), e só então reprocessar.
  Mexer na identidade do nó invalida `hash`, `src`, `to` e `leads_to` de todos os
  mapas gravados — é reprocessamento completo, não migração.
- **Dono:** 🤖 execução — **não feito nesta passada: o conserto mora em
  `templater.py`, em edição por outra frente**, e o risco de fundir tela errada é
  maior que o do sintoma.
- **Custa se esquecer:** cobertura e contagem de telas seguem divididas entre
  cópias, e a raiz de qualquer seguradora nova pode cair na tela errada pelo
  mesmo motivo.

---

## P-96 · 🧑 Os áudios da AutoFleet esperam um repareamento combinado

📊 Medido em 04/08/2026: **1.623 áudios recuperáveis (80 MB)**, e **zero
arquivados**. O caminho de repesca pelo banco é **impossível** — 0 têm
`fileEncSha256`/`fileSha256`, e o `/message/downloadmedia` exige a mensagem
crua inteira.

**O único caminho é reparear com o conserto de 04/08 no ar.** Aí a mídia é
enfileirada no instante da reentrega, que é o único instante em que ela existe.

📊 E o texto não duplica: **1 duplicata em 13.481 linhas** no repareamento de
hoje.

**Decisão do Founder (04/08):** *"não faz mal agora. Continuam no celular dela.
Isso fica como tarefa pendente mais pra frente, porque os áudios são na verdade
cartas pro RAG e podemos criar elas depois. Quero a destilação apenas das
conversas em texto agora."*

**O que destrava:** 🧑 combinar com a Regina um novo pareamento (5 minutos dela).
**O que custa esquecer:** nada imediato — os áudios estão no celular dela. Mas
cada mês que passa é mais chance de o WhatsApp podar a mídia antiga do servidor,
e aí nem o repareamento traz.
**Documentação completa:** [`AUDIOS-RESGATE.md`](AUDIOS-RESGATE.md) §0.

---

## P-97 · 🧑 O crédito da API Claude acabou — e o gasto tem dono

📊 Consumo total medido em 04/08 (`token_usage_logs`):

```
29/07   US$ 10,10  em 1.702 chamadas   ← a DESTILAÇÃO
28/07   US$  1,06  em 2.593 chamadas
resto   US$  0,43
                    TOTAL US$ 11,59
```

**Não foi agente de bastidor.** O destilador está desligado, o portal usa OpenAI,
os vigias não usam LLM. 📊 Foi `service_type='chat'` com `claude-sonnet-5` — a
destilação das 8.872 sessões em 9.699 cartas.

> 📊 **≈ US$ 0,0012 por carta.** A destilação é barata; o caro seria o
> raciocínio sem material.

**O que destrava:** 🧑 saldo novo na API Claude. Para a próxima leva (as ~700
sessões novas da AutoFleet), a conta proporcional é de **menos de US$ 2** — mais
uma margem para a curadoria.
**O que custa esquecer:** sem saldo, a destilação não roda, e 📊 o material cru
expira por volta de **27/10** (retenção de 90 dias).

---

## P-99 · 🧑 Duas telas da InfoCap ainda devolvem 500 — e uma delas é a produção

**Registrado em** 05/08/2026, durante o teste de leitura da InfoCap com
credenciais reais das duas corretoras.

📊 **O que foi medido**, com sessão autenticada e navegação somente-leitura:

```
/login              200 em 1,38s     ✅
detalhe de apólice  200 · 113 campos ✅ (inclusive `datemi` e `ramo`)
/producao           500              ❌
/cliente_ligacoes   500              ❌
```

O 500 é do lado deles: a mesma sessão que abre a apólice sem erro cai nessas
duas rotas. Não é permissão — é falha de servidor.

**O que destrava:** 🧑 abrir chamado com a InfoCap citando as duas rotas. O
contato já respondeu uma vez neste ciclo (foi assim que o login voltou), então
o caminho está aberto.

**O que custa esquecer:** `/producao` é a listagem por período — é dela que sai
a conferência de carteira e o lastro de qualquer relatório de produção. Sem ela,
a leitura da InfoCap funciona **por apólice** e não **por carteira**: dá para
conferir um contrato, não dá para varrer a base. Todo trabalho que dependa de
"quantas apólices, de quais ramos, vencendo quando" fica esperando esta rota.

⚠️ **E não existe contorno bom.** Reconstruir a carteira apólice por apólice
exige saber de antemão quais apólices existem — que é exatamente o que
`/producao` responde. Tentar adivinhar a lista é como o sistema começa a mentir
sobre o tamanho da própria base.

**O que NÃO espera por eles:** 🤖 nada. O leitor de apólice já funciona e já é
útil. Esta pendência não bloqueia o atendimento; bloqueia o relatório.

---

## P-100 · 🤖 Nove dos dez normativos desceram sem crédito; o décimo é servidor deles

**Resolvido em parte em 05/08/2026.** Dez documentos normativos estavam parados
com o motivo gravado no banco: *"credito do Firecrawl esgotado — aguardando
plano"*. Estavam esperando crédito para uma tarefa que um `GET` resolve — todos
os dez já tinham no banco uma **URL de PDF direta**.

📊 Medido contra as 10 URLs reais, em 05/08/2026:

```
9 de 10 baixaram por GET direto — 3.940.679 caracteres, todos com SUSEP no texto
azul  3/3   ·   bradesco  2/2   ·   tokio  3/3   ·   hdi  1/2
```

**O que sobrou:** as **condições gerais da HDI** —
`hdiseguros.com.br/webprog/webtxt/condicoes_gerais/condicoes_gerais_000_432_01102019_09122019.pdf`
devolve **HTTP 500**. Não é a nossa ponta: o manual do segurado da HDI, no mesmo
domínio-irmão, baixou sem erro no mesmo minuto.

**O que destrava:** 🤖 achar a URL nova das condições gerais da HDI. O arquivo
tem data no nome (`01102019`), então é provável que eles tenham publicado uma
versão mais recente e derrubado esta. **Descobrir URL nova é justamente o que o
Firecrawl faz** — este é o primeiro caso do ciclo em que o crédito faria falta
de verdade (P-98).

**O que custa esquecer:** a HDI fica com manual do segurado e **sem** condições
gerais. O manual descreve a prática; as condições gerais são o contrato. Numa
pergunta de cobertura, o agente responderia pela prática sem poder citar a
cláusula — que é exatamente a distinção que o corpus normativo existe para
sustentar.

⚠️ **E a lição que fica maior que o caso:** o `fetch_error` dizia *"crédito do
Firecrawl esgotado"* em documentos que **nunca precisaram do Firecrawl**. O
motivo gravado descrevia a ferramenta que falhou, não o que o documento
precisava. Nove ficaram parados oito dias por causa dessa frase.

---

## P-101 · 🤖 O rótulo velho continua **escrito dentro do chunk** no Qdrant

Em 05/08/2026 o acervo foi reorganizado no banco: 2.582 rótulos de seguradora
rebaixados para NULL e `category` preenchida com cinco valores. **O índice não
foi refeito.**

`publish_card_sync` grava no Qdrant o texto com o rótulo **no começo da frase**:

```
(allianz / auto / cobranca) Boleto vencido nao pode ser reemitido…
```

📊 FATO (leitura de código, `attendance_distiller.publish_card_sync`): o prefixo
entra no `chunk`, e o `chunk` é o texto indexado — não é metadado.
💭 INFERÊNCIA: os 10.818 pontos publicados carregam hoje o prefixo antigo.

**Por que isto importa mais do que parecia.** O raciocínio de que "o rótulo
errado é inofensivo porque não existe filtro por seguradora" vale para o
*payload*. **Não vale para o texto.** A busca é híbrida e o BM25 casa por termo
exato: quem pergunta "boleto da Allianz" hoje casa lexicalmente com as 746
cartas genéricas cujo chunk começa por `(allianz …)`. O campo não filtra, mas a
palavra pontua.

- **Destrava:** 🤖 republicar as cartas publicadas — mesma função, mesmo
  caminho, sem código novo: `despublicar_carta_sync` + `publish_card_sync`, ou
  um passe que reescreva o ponto. Custo de embedding ≈ 650 mil tokens de
  `text-embedding-3-small` (💭 ordem de US$ 0,01).
- **Não foi feito agora porque:** outro agente está em `search_service.py`,
  `rerank_service.py` e `qdrant_service.py` neste momento. Reescrever 10.818
  pontos no meio do trabalho dele é colisão garantida.
- **Custa se esquecer:** o banco fica honesto e a busca continua respondendo
  pela bandeira errada — e o formato pior possível é esse, porque a auditoria
  no banco diz que está resolvido.

## P-102 · 🤖 `pii_check` virou caixa de marcação geral, e o nome mente

A coluna guarda hoje `deterministic`, `llm_instructed`, `qdrant_pendente`,
`superseded_por`, `motivo`, `por`, `sessao`, e agora `insurer_key_anterior`,
`rebaixado_em` e `prestadora`. Só as duas primeiras têm a ver com PII.

Isto é exatamente o defeito que o CLAUDE.md §12.1 manda consertar no CAMPO, não
no texto: *um nome que mente sobre o que guarda reinfecta todo leitor seguinte*.
Foi usada assim de propósito — é o padrão que `corrigir.py` já estabeleceu, e
`reconciliar_indice_sync` já lê `pii_check->>qdrant_pendente` em produção —
mas a dívida fica anotada em vez de silenciosa.

- **Destrava:** 🤖 migration que renomeie para `marcas` (expand-first: coluna
  nova, backfill, leitura dupla, corte) **e** dê coluna própria a `prestadora`,
  que é dado de negócio e não marca de processo.
- **Gatilho:** no dia em que alguém for FILTRAR por prestadora. Enquanto for só
  registro, jsonb basta.
- **Custa se esquecer:** a próxima pessoa lê `pii_check` e conclui que a carta
  tem problema de PII quando ela só mudou de dono.

## P-103 · 🤖 45 cartas publicadas sabem de quem são e continuam sem dono

O trabalho de 05/08 só **rebaixou**. Promover — dar rótulo a quem não tem —
é a operação inversa e não foi autorizada, com razão: errar para cima é o erro
caro. Mas o material está medido e pronto.

📊 Medido em 05/08/2026 com `curadoria_cartas.texto_nomeia_seguradora` sobre as
10.818 published:

```
30 cartas SEM rótulo cujo texto nomeia exatamente UMA seguradora
15 cartas cujo rótulo caiu e o texto nomeia OUTRA companhia — inclusive
   `sul -> sulamerica` e `bradesco auto/fleet -> bradesco`, que são a mesma
   empresa escrita errado
```

- **Destrava:** 🧑 decisão de que promover é aceitável, e depois 🤖 rodar o
  mesmo `rotular_acervo.py` com o passe de promoção ligado.
- **Custa se esquecer:** 45 fatos que TÊM dono continuam respondendo como
  genéricos — perda menor que o erro contrário, mas perda.

## P-104 · 🤖 `_fila_pendente` pagina por `started_at`, que também empata

Irmã do defeito consertado em `curar_sync` no mesmo dia. 📊 Medido no acervo:
paginar por chave que empata devolveu 11.640 linhas com 11.628 hashes distintos
— 12 repetidas e 12 nunca vistas.

`attendance_distiller._fila_pendente` faz `.order("started_at", desc=True)` com
`.range()` sobre `attendance_sessions`. O empate ali é menos provável (sessões
não nascem em lote como as cartas), e o dano é menor — a fila é um **contador**,
não uma escrita. Por isso ficou de fora do escopo em vez de entrar de carona.

- **Destrava:** 🤖 trocar por `.order("id")`, uma linha.
- **Custa se esquecer:** o número da fila no painel erra para menos, e o modo
  de recuperação (que liga por limiar) decide com um número errado.

## P-105 · 🧑 319 lotes de seguradora estão prontos e NÃO gravados

Preparado em 06/08/2026. O exportador, o prompt e um lote de prova destilado
existem; **nada foi para o banco**, porque a reindexação de 10.818 cartas estava
rodando em produção no mesmo minuto.

📊 `python backend/scripts/destilacao_max/exportar_seguradoras.py` produziu
**27 lotes · 319 conversas · 1,69 milhão de caracteres**, e o
`lote_016.destilado.jsonl` passou no `validar.py` com **12 conversas · 55 fatos**.

- **Destrava:** 🧑 terminar a reindexação; depois 🤖 destilar os 26 lotes
  restantes com o `PROMPT-DESTILADOR-SEGURADORA.md` e aplicar.
- **Custa se esquecer:** é o único acervo do projeto que ensina **o que a
  seguradora faz** em vez de o que a corretora faz, e o rótulo de seguradora
  dele é confiável por construção — o que o acervo antigo nunca teve.

### ✅ 06/08/2026 — `aplicar_seguradoras.py` existe, testado e NÃO rodado

O aplicador foi escrito, provado por mutação (12 mutações, 12 pegas) e rodado
**só em simulação**. 📊 Previsto sobre os 24 lotes destilados até então:
**288 sessões · 1.138 cartas · 1.138 inéditas**, `select` confirmando
`sessoes_marcadas = 0` e `cartas_do_acervo_observado = 0` no banco.

A decisão de rótulo foi tomada como recomendado — `insurer_key` da sessão
observada vale direto —, com um guarda estreito para o caso Porto→Azul. 📊 A
medição que sustenta: 915 de 918 fatos (99,7%) nomeiam a própria seguradora,
contra 32,3% no acervo de atendimento. Ver o cabeçalho do script.

**Falta só 🧑 mandar rodar com `--aplicar`, com a reindexação parada.**

O texto abaixo é o registro do que era o problema.

### O que faltava ANTES de aplicar: não existia `aplicar_seguradoras.py`

`aplicar.py` escreve `summary.distilled` em **`attendance_sessions`**. Este
acervo mora em `observed_sessions`. Aplicar com ele marcaria a sessão errada —
ou nenhuma.

E há uma decisão de verdade embutida: `aplicar.py` trata `seguradora` como
**candidata** e re-decide fato a fato em `curadoria_cartas.seguradora_do_fato`,
porque 📊 no acervo antigo só 32% das cartas etiquetadas citavam a própria
seguradora. **Aqui o rótulo é confiável por construção** — a conversa É com
aquela seguradora. Re-decidir por texto jogaria fora a única coisa que este
acervo tem de melhor.

- **Destrava:** 🧑 decidir se `insurer_key` da sessão observada vale como
  rótulo direto do fato (recomendação: sim, com a exceção do fato que atribui a
  regra a outra companhia); depois 🤖 escrever o aplicador.
- **Custa se esquecer:** sem isso o material fica em disco e a sessão nunca
  recebe a marca `distilled` — a próxima exportação refaz tudo do zero.

## P-106 · 🟠 O vocativo da URA só é mascarado porque a seguradora publica menus

📊 Medido em 06/08/2026 sobre as 319 sessões: **~240 ocorrências** de primeiro
nome de segurado escritas pela própria URA, na forma `"Fulano, só mais uma
informação:"`. Ela tem a MESMA forma de `"Guincho, borracheiro e chaveiro"`.

Quatro hipóteses foram medidas e **três foram refutadas** (forma · raridade ·
vocativo puro). A que funciona pergunta à seguradora o que ela oferece como
opção de menu, exige que a palavra apareça como opção em **4 sessões
distintas**, e mascara o resto.

**Ela depende de um acervo grande o bastante para conter o próprio
vocabulário.** Numa corretora nova, com 20 sessões observadas, o vocabulário de
menu fica pobre e a regra passa a mascarar palavra de menu — perda de
conhecimento, não vazamento.

- **Destrava:** 🤖 quando o acervo observado passar de ~50 sessões por
  seguradora, reconferir com `medir_vocabulario_de_menu`; ou 🧑 decidir semear o
  vocabulário a partir dos mapas do Atlas, que já são globais.
- **Custa se esquecer:** o mascarador fica silenciosamente mais guloso quanto
  menor a corretora, e o custo aparece onde ninguém olha.

## P-107 · 🟠 838 eventos observados não pertencem a sessão nenhuma

📊 Medido em 06/08/2026:

```sql
select count(*) from observed_events where session_id is null;   -- 838
```

São **4,3% dos 19.421 eventos**, espalhados por 4 seguradoras, e mais 1 evento
apontando para uma sessão que não existe. Todo exportador que parte de
`observed_sessions` é cego para eles — inclusive o novo.

- **Destrava:** 🤖 investigar se são captura anterior ao pareamento de sessão
  ou perda de correlação no `observer_intake`, e repará-los por
  (`observer_number`, `counterparty`, janela de tempo).
- **Custa se esquecer:** é conhecimento capturado, pago em risco de sessão, e
  invisível para sempre.

## P-108 · 🟡 O protocolo de 12 dígitos da Porto atravessa o mascarador

📊 17 ocorrências nos lotes exportados, na forma `1-122244434702`. A regra
`{NUMERO}` do `templatize` cobre 7 a 11 dígitos; esta tem 12 e vem colada num
prefixo `1-`. A regra `{PROTOCOLO}` exige a palavra "protocolo" ao lado, e a
Porto imprime o número na linha **seguinte**.

Não é dado de pessoa e o `validar.py` reprova qualquer carta que o contenha —
então ele não chega ao acervo. Mas ele chega ao **lote**, e ao destilador.

- **Destrava:** 🤖 estender a faixa de `{NUMERO}` ou reconhecer o padrão
  `\d-\d{10,}`. Uma linha, com controle de que "197" e "2026" sobrevivem.
- **Custa se esquecer:** um identificador de atendimento de um segurado real
  fica legível num arquivo em disco.

## P-109 · 🟠 `aplicar.py` marca a sessão ANTES de gravar as cartas

Encontrado em 06/08/2026 ao escrever o `aplicar_seguradoras.py`, que faz o
contrário de propósito.

`aplicar.py` escreve `summary.distilled` dentro do laço, conversa a conversa, e
só faz o `upsert` das cartas no **fim do arquivo**. As duas escritas não são uma
transação. Se a rodada cair entre elas — rede, chave expirada, Ctrl-C — as
sessões já marcadas ficam declaradas destiladas **sem uma carta no acervo**, e a
marca é justamente o "não volte mais": `exportar.py` e o destilador as pulam
para sempre.

A carta é idempotente (`on_conflict=card_hash, ignore_duplicates`); a marca é
irreversível na prática. Gravando as cartas primeiro, qualquer queda deixa
trabalho refazível. Gravando a marca primeiro, deixa conhecimento perdido em
silêncio — e ninguém descobre, porque o sintoma é uma sessão que parece pronta.

Não entrou de carona no trabalho de 06/08 porque `aplicar.py` está em uso e
funciona; trocar a ordem dele é uma mudança de comportamento que merece o seu
próprio controle.

- **Destrava:** 🤖 mover o `upsert` das cartas para antes do laço que marca as
  sessões — a mesma ordem que `aplicar_seguradoras._gravar` já usa e que
  `test_a_carta_da_seguradora_sabe_de_quem_e` já guarda nas duas direções.
- **Custa se esquecer:** cada queda no meio de uma rodada apaga em definitivo o
  conhecimento das conversas que estavam no arquivo naquele momento, e a perda
  não deixa rastro nenhum.

### ✅ RESOLVIDO em 08/08/2026

`aplicar.py` foi partido em `_planejar` (só lê) / `_gravar` (só escreve) — a
mesma forma de `aplicar_seguradoras.py`, e é essa separação que torna a ordem
uma escolha em vez de uma consequência: enquanto o plano era feito dentro do
laço que já escrevia, a ordem antiga era a única possível. Agora `_gravar` faz
o `upsert` de todas as cartas e só depois marca as sessões, com releitura
imediatamente antes de cada marca.

- **Guarda:** [`test_a_carta_e_gravada_antes_da_marca.py`](../../backend/tests/test_a_carta_e_gravada_antes_da_marca.py)
  — a linha de controle **reconstitui a `_gravar` antiga dentro do teste** e
  submete as duas à MESMA queda. A antiga termina com a sessão marcada e zero
  cartas; a nova, com as cartas no acervo e a sessão ainda na fila. Sem esse
  bloco o guarda não teria como falhar: exercitar só a ordem certa passaria
  igual no dia em que alguém invertesse tudo de volta.

> A marca congelada que estava no mesmo arquivo virou [P-129].

## P-110 · 🔴 A captura das duas corretoras está PARADA, e o painel diz "Conectado"

📊 Medido em 06/08/2026 (projeto `dcajcvlzcjbmyapmklil`):

```sql
select c.company_name, max(e.created_at) from observed_events e
  left join companies c on c.id = e.company_id group by 1;
--  AutoFleet         04/08 20:34Z   (42 h)
--  Resulta Seguros   03/08 20:19Z   (67 h)
```

📊 E a causa, em `GET /instance/all` do provedor no mesmo dia: **três das quatro
instâncias com `webhook=''` e `events='MESSAGE'`** — inclusive a da AutoFleet,
que estava `Connected: true, LoggedIn: true` naquele instante.

O reconector chamava `/instance/connect` com só `{"immediate": True}`, e o
`Connect` do Go grava `Webhook = data.WebhookUrl` **por cima**: religava o canal
mudo. Consertado em `f81e24e` (`corpo_do_connect` recusa URL vazia; o reconector
rotaciona a credencial antes de religar).

⚠️ **O conserto não repara o estado que já existe.** As instâncias em produção
continuam sem webhook até alguém emitir um `connect` completo. O reconector novo
só age sobre canais que a sonda vê caídos — e a AutoFleet aparece de pé.

- **Destrava:** 🤖 merge de `f81e24e` na `main` (o deploy sai da `main`) **e** um
  `connect` completo por instância para regravar webhook e eventos. 📊 É seguro
  com a instância no ar: `UpdateInstanceSettings` (`whatsmeow.go:175+`) só troca
  campos em memória — não há `Disconnect()` nem `killChannel` no caminho.
- **Custa se esquecer:** o produto segue sem matéria-prima. Nenhuma conversa
  entra no Atlas, no Espelho ou no RAG, e a tela continua dizendo que está tudo
  certo — que é a razão de isto ter durado três dias sem ninguém notar.

## P-111 · 🟠 A linha da Resulta está pareada no telefone errado

📊 `integrations` em 06/08/2026: a instância `ab-obs-04b5cdbc04-1` (Resulta) tem
`paired_phone_e164 = +554788087463` — **DDD 47**. O Founder identificou o número
como o **dele**, não o da atendente (que é DDD 48).

Isso explica o sintoma inteiro: a atendente pedia QR para uma linha que já tinha
dono, e 📊 com `jid` preenchido o whatsmeow **reconecta** em vez de emitir QR
(`whatsmeow.go:325-335`), então o QR não podia vir.

O caminho existe desde `f81e24e`: `POST /api/whatsapp-channel/pairing/liberar-numero`
recria a instância com o **mesmo nome** (preservando `observer_number`, metade da
chave de dedup de 69.150 transcrições) e com `jid` vazio, e o QR volta.

- **Destrava:** 🧑 decisão do Founder — trocar encerra a sessão do DDD 47. Depois
  🤖 deploy + clicar "trocar número" na tela da Resulta e escanear o QR.
- **Custa se esquecer:** a corretora segue capturando o WhatsApp errado, e o que
  o produto aprende não é o atendimento dela.

## P-112 · 🟡 O `/instance/status` do provedor não sabe o que o banco dele sabe

📊 `instance_service.go:391-400`: `Status` lê `clientPointer`, que é **memória do
processo**. Com `CONNECT_ON_STARTUP=false` (a config de produção), todo restart
do Evolution Go esvazia esse mapa e **toda** instância passa a responder
`LoggedIn: false` — inclusive as perfeitamente pareadas.

`f81e24e` contornou no nosso lado (`_sessao_registrada` pergunta ao
`/instance/all`, que é o estado durável). O contorno é correto e deve ficar, mas
a mentira continua na fonte, e todo consumidor novo do `/status` vai cair nela.

📊 Dois mapas divergentes agravam: `instance_service.go:366,381,647,796` apagam
`clientPointer` sem apagar `myClientPointer`. Depois de um `logout`, o `status`
diz "não está rodando" e o `connect` diz "já está rodando" — e não sobe cliente
nenhum. Foi medido: um `connect` na instância da Resulta em 06/08 às 14:54Z não
produziu **uma linha de log**.

- **Destrava:** 🤖 patch 0007 no fork — `Status` consultar o `jid` persistido, e
  os quatro `delete(clientPointer)` limparem os dois mapas. Exige rebuild da
  imagem e teste com as duas corretoras no ar.
- **Custa se esquecer:** todo diagnóstico futuro começa por uma leitura falsa, e
  a instância zumbi (`client != nil && !IsLoggedIn()`) trava a corretora até o
  contêiner reiniciar.

## P-113 · 🔴 O patch 0007 do fork NÃO foi compilado

`infra/evolution-go-autobrokers/patches/0007-status-e-runtime.patch` está escrito
e 📊 os sete patches aplicam limpo sobre o upstream `9337afc4` (`git apply
--check` verde nos sete). Mas **não houve compilação**: não há Go nem Docker na
máquina desta sessão.

Revisão manual feita: `strings` já importado, chaves balanceadas (173/173),
`ClearInstanceCache` está na interface `WhatsmeowService`, `LogWarn` já usado no
arquivo, `instance` existe nos escopos tocados.

Um erro descoberto NA revisão e evitado: a primeira versão aplicava o helper
também no `ForceReconnect`, onde o `killChannel` novo já foi criado logo acima —
`ClearInstanceCache` o fecharia antes de o `StartClient` seguinte encontrá-lo.
Ficou de fora, com o motivo escrito no próprio helper.

⚠️ **O deploy do `evolution-go-teste` derruba a AutoFleet.** `CONNECT_ON_STARTUP=false`
significa que nenhuma instância religa sozinha depois do restart do contêiner.

- **Destrava:** 🤖 `go build` (o Dockerfile já roda `go test ./pkg/instance/service`
  antes do build, então erro de compilação **reprova o build** e a imagem antiga
  continua no ar — o gate existe). Depois 🧑 disparar o deploy e, logo em seguida,
  🤖 um `POST /instance/connect` completo por instância para religar e regravar
  webhook.
- **Custa se esquecer:** o `/instance/status` segue mentindo após cada restart e
  a instância zumbi segue capaz de prender uma corretora até o contêiner cair.

## P-114 · 🟠 O webhook das instâncias precisa ser regravado depois do deploy

📊 Medido em 06/08/2026 ~16:40Z, com o `smith-api` ainda rodando o código antigo:
`integrations.webhook_token_prefix` da Resulta era `zAkKqY_b` enquanto o campo
`webhook` da mesma instância no provedor estava **vazio**. O banco tinha a
credencial; o provedor não tinha a URL. É o defeito do reconector acontecendo em
produção enquanto a correção esperava deploy.

O conserto está na `main` (`f81e24e` + `b078dcf`), mas **ele não repara o estado
que já existe**: o reconector novo só age sobre canais que a sonda vê caídos.

- **Destrava:** 🤖 depois do deploy do `smith-api`, um `connect` completo por
  instância ativa (o mesmo procedimento da Parte II §10 do relatório de
  auditoria), e então conferir `observed_events` algumas horas depois.
- **Custa se esquecer:** captura parada com o painel dizendo "Conectado" — a
  falha que já custou 42 h e 67 h sem ninguém notar.

## P-115 · 🟡 Cobrança e auxiliares: número separado, decisão pendente

O Founder (06/08/2026): *"precisam ser números separados porque são serviços
diferentes, mensagens diferentes... precisamos conversar sobre detalhes de parear
a cobrança e o agente de atendimento separadamente por causa de bloqueio"*.

O caminho já existe e está guardado por teste: `channel_identity` produz
`ab-aux-{b10}-{slug}` para `purpose="auxiliary:<slug>"`, separado do número da
corretora, e `numero_proprio()` responde quem exige QR próprio. **Nada foi
ligado** — é só o vocabulário pronto.

O que falta é decisão de produto, não código: quantos números, quem pareia, qual
o aquecimento antes do primeiro disparo, e o que acontece quando um número é
bloqueado no meio de uma régua de cobrança.

- **Destrava:** 🧑 conversa com o Founder sobre a régua de cobrança temporária
  via Evolution GO (antes da API Oficial da Meta), depois 🤖 a SPEC.
- **Custa se esquecer:** cobrança sai pelo número de atendimento da corretora, e
  um bloqueio derruba o atendimento junto — os dois serviços no mesmo risco.

## P-116 · 🟡 A captura voltou a estar CONFIGURADA — falta prova de que GRAVA

📊 06/08/2026 ~17:00Z, com o `smith-api` já rodando o código novo (os quatro
sinais do pareamento respondem `True` no `/health`; `git_commit` segue
`nao-injetado` porque o EasyPanel não passa o build-arg — e foi por prever isso
que os sinais existem).

**O que ficou provado**, conferido hash a hash entre provedor e banco:

| corretora | `webhook` no provedor | hash no banco | bate |
|---|---|---|---|
| AutoFleet | `…/e3Yd…`→ `cb369f28…` | `cb369f28…` | ✅ |
| Resulta | `9bcf4b49…` | `9bcf4b49…` | ✅ |

📊 E o socket da AutoFleet está **vivo**: `GET /user/privacy` respondeu 200 em
0,3 s com dados reais do WhatsApp dela, contra timeout de 30 s na Resulta (sem
sessão) como linha de controle.

📊 O reconector NOVO religou a Resulta sozinho, com webhook e os quatro eventos —
o conserto funcionando em produção, sem intervenção manual.

**O que NÃO ficou provado:** que uma conversa nova foi gravada. A AutoFleet segue
com `observed_events` parado em 04/08 20:34Z (44 h). Isso depende de chegar
mensagem real e **não é observável por mim**. 📊 O log da instância mostra que
em 05/08 23:23Z ela ainda RECEBIA mensagens e as despachava para o webhook vazio
— foram perdidas exatamente como a auditoria descreveu.

- **Destrava:** 🤖 rodar a query de `observed_events` daqui a algumas horas. E
  agora o produto avisa sozinho: `decidir_alarme_de_entrega` (e8ec78b) abre
  incidente na Caixa do Admin quando um canal diz "conectado" e passa 6 h sem
  gravar. 📊 A AutoFleet cai nessa condição **hoje** — o alarme dispara no
  primeiro ciclo do heartbeat depois do próximo deploy, e essa será a primeira
  prova de que ele funciona.
- **Custa se esquecer:** nada — pela primeira vez, o esquecimento é coberto. Era
  justamente a ausência disso que deixou 42 h e 67 h passarem sem ninguém notar.

> **P-114 fica RESOLVIDO por esta entrada** na parte que era acionável: os
> webhooks foram regravados e conferidos. O que resta é medição no tempo, e é o
> que esta pendência acompanha.

## P-118 · 🟠 O Espelho existe, mas mora só no admin

📊 As conversas capturadas da AutoFleet estão em `/admin/espelho`
(`attendance_sessions` + `attendance_transcripts`, via
`admin_atlas.espelho_sessoes` e `replay_atendimento`). A corretora **não** as vê:
o dashboard dela mostra `conversations`, que é a central do AGENTE.

O Founder (06/08): *"as conversas precisam ir pro dashboard pra fazer o
atendimento dentro do chat de conversas, devem aparecer para o observador na
central de agentes"*.

⚠️ **Isto é mudança de produto, e tem um risco que precisa de decisão.** A tela
`Atendimentos → Conversas` tem campo de resposta. Espelhar ali as conversas
capturadas sem mais nada cria uma porta por onde alguém responde — e a mensagem
sai pelo WhatsApp da corretora. Com todos os agentes desligados de propósito,
essa porta não pode nascer aberta por acidente.

Três caminhos, e a escolha é do Founder:

1. **Espelho read-only no dashboard** (nova aba, sem campo de resposta) — mostra
   o que a equipe conversou, sem criar caminho de envio. É o menor risco.
2. **Conversas do observador na central de atendimento, com envio bloqueado** até
   o botão "Ligar agente" — mais próximo do pedido, exige um guarda explícito e
   testado no caminho de envio.
3. **Só depois de ligar o agente** — o comportamento de hoje, sem mudança.

- **Destrava:** 🧑 decisão entre os três, depois 🤖 a implementação.
- **Custa se esquecer:** a corretora não vê o próprio atendimento, e o produto
  parece vazio para ela mesmo capturando tudo.

## P-119 · 🟡 Áudio e imagem no chat da corretora aparecem, mas não tocam

Decisão do Founder, 06/08/2026: fica para depois, e a mensagem precisa aparecer
de algum jeito enquanto isso.

O Bloco 1 do espelho grava mídia como `[audio]` / `[imagem]` no chat: a mensagem
EXISTE e é visível, mas não reproduz. 📊 Não é caso raro — na primeira hora
medida da AutoFleet havia áudio de cliente no meio das conversas de sinistro.

A mídia já é baixada e guardada com o que é preciso para recuperá-la: 📊 o
`/health` prova em duas linhas (`midia_recuperavel` e `midia_chave_escondida`),
e `observer_intake.COORDENADAS_DE_MIDIA` grava `mediaKey`/`directPath`. Falta a
ponta do chat — subir para o storage e devolver uma URL que o navegador toca.

- **Destrava:** 🤖 reusar `webhook._upload_media_bytes` (que já faz isso no
  pipeline do agente) a partir da ponte do espelho, e o player no
  `ConversasClient.tsx`. Sem peça nova.
- **Custa se esquecer:** a atendente vê `[audio]` e precisa ir ao celular para
  ouvir — o que derrota o motivo de existir o chat no dashboard.

## P-122 · 🟡 O teto de 1.000 linhas: o que foi consertado e o que ficou

🤖 **Execução** · aberta e parcialmente resolvida em 06/08/2026

O PostgREST tem um teto de linhas por resposta que **vence o `.limit()`
pedido**. Pedir 1.500 não dá erro: devolve 1.000 e o código segue achando que
leu tudo. Uma auditoria independente varreu o backend e achou ~28 pontos.

### ✅ Resolvido — o que dava dinheiro e o que afeta a conversa

📊 Medido em produção (`dcajcvlzcjbmyapmklil`) em 06/08/2026 23:43 UTC:

| onde | no banco | chegava | o que estragava |
|---|---|---|---|
| `api/billing.py` | 4.648 | 1.000 | **consumo que o CLIENTE vê**, com multiplicador de venda |
| `control_plane/unit_economics.py` (×2) | 4.406 + 4.787 | 1.000 | relatório de custo — **e o detector de truncagem, derrotado pelo próprio truncamento** |
| `workers/billing_tasks.py` | 5.646 | 1.000 | débito de créditos em fatias, com `processed` mentindo |
| `detectors/conexoes.py` | 4.267 | 1.000 | **alerta de orçamento que não dispara** — e se cala mais no maior cliente |
| `services/agent_memory.py` (×2) | 1.577 | 1.000 | o que o agente lembra: base da resposta, da carta e do RAG |
| `atlas/espelho_chat.py` | 1.570 | 1.000 | 19 conversas abertas e vazias na tela da corretora |
| `whatsapp/channel_state.py` | — | — | alarme de canal mudo lendo a corretora errada |

Peça única: [`backend/app/leitura_completa.py`](../../backend/app/leitura_completa.py)
(`ler_paginado` / `ler_paginado_async`). Mora em `app/` e não em `app/core/`
porque `app/core/__init__` puxa a configuração inteira — 📊 com o import lá,
quatro testes que passavam viraram `ModuleNotFoundError`.

**Escolha deliberada: paginar, não criar função SQL.** Somar dentro do Postgres
seria uma ida em vez de cinco, mas exige migration — e migration no meio de um
lançamento é onde nasce o bug que atrasa tudo. 📊 4.648 linhas são 5 idas ao
banco num relatório sob demanda. Se alguma leitura passar de ~20 mil, a conta se
inverte e aí vale a função SQL; o teto de `ler_paginado` avisa quando esse dia
chegar, em vez de truncar calado.

### 🟠 Fica pendente — 17 pedidos em 9 arquivos

Nenhum erra HOJE: 📊 `intelligence_signals` = 21 linhas, `intelligence_findings`
= 6, `research_*` praticamente vazias. Todos agregam ou contam, então passam a
errar em silêncio no dia em que a tabela crescer.

`agents/gateway_cutover.py` (1, e **ignora o parâmetro `dias` que recebe**) ·
`api/admin_atlas.py` (1) · `api/research.py` (4) ·
`intelligence/detectors/qualidade.py` (1) · `intelligence/feedback_service.py`
(2) · `intelligence/rule_engine.py` (5) · `observability/sli.py` (1, com
`.limit(50_000)` — o número é a assinatura de quem achou que estava lendo tudo)
· `regression_sentinel.py` (1) · `research/monitor_service.py` (1)

- **Destrava:** nada. Trabalho de execução, sem dependência externa.
- **Gatilho para consertar:** quando a tabela de origem passar de ~800 linhas,
  ou quando o número for usado para decidir dinheiro.
- **Como:** `ler_paginado` com `chave_unica="id"`. Nunca por data: 📊 uma
  paginação por `created_at` neste repositório perdeu 12 linhas e repetiu 12 em
  11.640, porque datas empatam.
- **Guarda:** [`test_ninguem_pede_mais_de_mil_linhas_de_novo.py`](../../backend/tests/test_ninguem_pede_mais_de_mil_linhas_de_novo.py)
  varre o backend por AST e **reprova qualquer pedido NOVO**. A lista dos 17
  está lá dentro como linha de base — e o teste também reprova se um deles for
  consertado sem sair da lista, para ela não virar ficção.

### 🔴 Achado adjacente, e não é truncamento

📊 `usage_events`: **4.406 linhas, ZERO com `work_run_id`**. `custo_do_run()`
filtra por esse campo, devolve sempre `{eventos: 0, custo: 0}`, e
`orcamento_estourado()` **sempre responde False**. O teto de orçamento por Work
Run (SPEC-055 §25) está escrito, testado e desligado na prática — porque o elo
nunca é gravado. Não foi corrigido aqui: é assunto da SPEC-055, não deste teto.

### 💭 Não medido

Se `count="exact"` sobrevive ao teto do servidor. O código usa essa técnica em
17 lugares com fallback, o que sugere que ninguém confirmou. Não afeta nada do
que foi feito acima (paginação não depende disso), mas mudaria a técnica
recomendada para os 17 pendentes: seria 1 ida em vez de N.


---

## P-123 · 🔴 O maior grupo do acervo não gera playbook — e o eixo `outro` era o outro

> **Esta entrada foi escrita errada e reescrita no mesmo dia.** A versão
> original dizia: *"`ramo='outro'` nunca é produzido — 3 playbooks ativos são
> inalcançáveis"*. **Isso é falso**, e a medição que a desmentiu está abaixo. A
> versão errada não fica arquivada porque pendência é lista de trabalho, não
> diário: quem ler amanhã precisa do fato certo. O erro fica registrado aqui,
> no cabeçalho, para não se repetir — **eu tinha olhado o eixo errado.**

📊 Medido em 07/08/2026 sobre 9.196 sessões destiladas.

`ramo='outro'` **é produzido, e muito**: 2.905 sessões, 32% de todo o material,
o segundo maior ramo. Os playbooks `outro/sinistro` (629 sessões úteis, nota
74,5) e `outro/consulta` (254, nota 69,6) não são mudos — estão entre os
maiores que existem.

**O eixo descartado é o do SERVIÇO, não o do ramo.** Duas linhas jogam fora
`servico == "outro"`:

- [`attendance_distiller.py:863`](../../backend/app/services/attendance_distiller.py#L863) — `if not ramo or servico in ("", "outro"): continue`
- [`attendance_distiller.py:1037`](../../backend/app/services/attendance_distiller.py#L1037) — `if servico in ("outro", "") or ramo in ("",): continue`

E o que elas jogam fora é o melhor material do acervo:

```
grupo                sessões ÚTEIS   nota    playbook
auto/outro                   2.219   74,4    NENHUM   ← o maior E o melhor
outro/outro                  1.468   67,2    NENHUM
residencial/outro              166   76,3    NENHUM
vida/outro                      24   72,9    NENHUM
                             -----
                             3.877 sessões — mais da metade do aproveitável
```

### A informação nunca se perdeu — ela é ignorada

O classificador grava **`tipo` E `servico`**. O playbook usa só `(ramo,
servico)`. Quando `servico='outro'`, o `tipo` tem a resposta, ao lado, e é
descartada:

```
dentro de servico='outro':
  auto        / cobranca      1.904 úteis   nota 76,2   ← melhor grupo do acervo
  outro       / cobranca        986         nota 72,7
  outro       / outro           381         nota 52,4   ← o único que é ruído
  residencial / assistencia     109         nota 78,5
  auto        / sinistro        103         nota 65,4
  auto        / apolice          64         nota 71,8
```

📊 **Cobrança é 2.890 sessões úteis com nota ~75, e 2.915 das 12.063 cartas do
RAG (24%).** É o maior bloco de atendimento humano bom da corretora, e o
produto não tem uma linha de conduta sobre ele.

### Por que `servico='outro'` foi descartado, e por que a decisão envelheceu

A regra é defensável na origem: um playbook de "outro" seria vago demais para
servir. Só que ela foi escrita quando "outro" era resto. Hoje é o maior balde —
e **`tipo` já o separa em grupos coerentes**. Descartar deixou de proteger e
passou a custar.

- **Destrava:** decisão de eixo (abaixo). Nada externo.
- **De quem é:** 🧑 Founder decide o eixo · 🤖 execução implementa.
- **O que custa esquecer:** o agente atende cobrança — 24% do trabalho — sem
  nenhuma conduta destilada, improvisando, enquanto 2.890 atendimentos humanos
  bons sobre exatamente isso estão gravados e não são lidos.

### 💭 A opção que eu recomendo (não medida, é desenho)

Deixar de tratar `outro` como valor e passar a tratá-lo como **ausência**:
quando `servico == "outro"`, usar `tipo` no lugar. Isso não inventa ramo novo,
não mexe no classificador e não migra dado nenhum — é uma linha de escolha de
chave. E faz nascer `auto/cobranca` (1.904 úteis, nota 76,2) já acima do piso.

Ver [`FOUNDER-DECISIONS.md`](FOUNDER-DECISIONS.md) — a decisão de eixo, com as
alternativas e o que cada uma custa.

---

## P-124 · 🧑 `auto/bateria` está correto e mal lastreado

📊 Medido em 07/08/2026. O texto do playbook foi corrigido (três perguntas que
pediam placa, modelo e telefone viraram confirmação), mas o material que o
sustenta é fraco:

```
13 sessões usadas · 8 com score 0 · nota média 27,8/100
```

Score 0 não é nota baixa: é **"não houve atendimento humano"** — robô da
seguradora, central de prestadora, fragmento. Sobraram 5 atendimentos reais
para ensinar conduta de bateria.

Com o piso novo (`_MIN_SESSIONS_DEFAULT = 12` **úteis**), um playbook assim não
nasceria mais. Este nasceu antes.

- **Destrava:** a destilação das 1.767 sessões da fila (Bloco 5). Se ela trouxer
  atendimentos de bateria com humano, o grupo se re-sintetiza sozinho.
- **De quem é:** 🧑 Founder decide se ativa agora ou espera material melhor.
- **O que custa esquecer:** ativar hoje coloca no ar conduta destilada
  majoritariamente de robô. Esperar deixa o serviço sem playbook — o agente cai
  no prompt genérico, que é pior em coleta e melhor em honestidade.

---

## P-125 · 🟡 Os 7 playbooks ativos restantes não passaram por revisão de conteúdo

Nesta rodada foram corrigidas **11 frases** nos 12 playbooks ativos (10 com
espaço em branco literal, 1 com flag `ja_temos_na_apolice` errada) e os 6
rascunhos foram lapidados campo a campo.

Mas a lapidação campo a campo — objetivo, acolhimento, ordem da ficha,
sensibilidade — **só foi feita nos 6 rascunhos**. Os ativos receberam apenas as
correções que os detectores automáticos apontaram.

- **Destrava:** nada. É trabalho de leitura.
- **De quem é:** 🤖 execução.
- **O que custa esquecer:** detector pega o que sabe procurar. 📊 Dos 9 achados
  iniciais nos rascunhos, 6 eram falso positivo do próprio regex — o que mostra
  que a régua automática erra nos dois sentidos.
- **Quando:** depois da destilação. Vários desses playbooks serão reescritos
  pelo material novo, e revisar agora é revisar duas vezes.

---

## P-127 · 🧑 Os ramos que existem no mercado e não existem no sistema

Decisão do Founder em 07/08/2026: **fica registrado e não se executa agora** —
a saída B de [`D-Playbook-01`](FOUNDER-DECISIONS.md).

O sistema classifica em quatro ramos: `auto`, `residencial`, `vida`, `outro`.
O mercado brasileiro tem muito mais, e o Founder perguntou por condomínio,
empresarial, responsabilidade civil, fiança e saúde.

📊 Medido em 07/08/2026 sobre as 12.063 cartas publicadas — quanto de cada tema
já existe no acervo:

| tema | cartas | % |
|---|---|---|
| condomínio | 468 | 3,9% |
| empresarial / patrimonial | 80 | 0,7% |
| frota | 74 | 0,6% |
| responsabilidade civil | 41 | 0,3% |
| fiança | 25 | 0,2% |
| saúde | 6 | 0,05% |

**Condomínio é o único com massa real.** Os demais quase não aparecem — e isso
**não prova que o ramo não importa**: prova que as duas corretoras capturadas
(Resulta e AutoFleet) trabalham auto e residencial. Uma corretora nova de
benefícios inverteria a tabela inteira.

- **Destrava:** material que justifique o ramo. O piso de evidência é 12
  atendimentos úteis; hoje só condomínio chega perto, e nem ele foi medido em
  ATENDIMENTOS (as 468 são cartas, não conversas).
- **De quem é:** 🧑 Founder decide quando · 🤖 execução implementa.
- **O momento ideal:** depois da destilação do material bruto, quando houver
  contagem de ATENDIMENTOS por tema — não de cartas. Antes disso, acrescentar
  cinco ramos cria cinco baldes abaixo do piso: playbooks que não nascem e
  telas que mostram categorias vazias.
- **O que custa esquecer:** quando entrar uma corretora de condomínio ou
  benefícios, o material dela cai em `outro` e se mistura com o resto — e a
  separação depois é mais cara que a classificação na origem.
- **Pré-requisito técnico:** antes de acrescentar ramo, ler o resultado da
  auditoria de padronização (P-128) — 📊 hoje existem **12 conjuntos distintos**
  de valores de ramo no código, e acrescentar um sexto valor a um vocabulário
  que já diverge multiplica o problema em vez de resolver.

---

## P-130 · 🔴 O acervo oficial está VENCIDO — 14 de 15 documentos

📊 Medido em 08/08/2026 consultando o repositório público da SUSEP, produto por
produto, com os números de processo que temos no banco.

| documento | nossa versão | vigente hoje | versões existentes |
|---|---|---|---|
| **Porto Condomínio** | **01/12/2012** | **11/12/2025** | 26 |
| Bradesco Auto | 01/04/2023 | 11/07/2026 | 45 |
| Bradesco Empresarial | 04/08/2023 | **06/08/2026** | 28 |
| Porto Auto | 01/01/2026 | 01/07/2026 | **100** |
| Allianz Auto | 10/12/2025 | 22/07/2026 | 72 |
| Allianz Residencial | 01/12/2025 | 18/06/2026 | 30 |
| Allianz Vida | 16/12/2025 | 15/07/2026 | 11 |
| Porto Empresa | 11/04/2025 | 31/07/2026 | 25 |
| Azul Auto | 01/05/2025 | 30/08/2025 | 83 |
| **Porto Residência** | 05/12/2025 | 05/12/2025 | ✅ **em dia** |

**Um contrato de 2012 respondendo sobre um condomínio de 2026 é pior que não
ter documento nenhum**: ele erra com a autoridade de um documento oficial, e
quem lê não tem como desconfiar. É a mesma classe do defeito que o RAG já
conhece — *"o formato pior possível é esse, porque a auditoria diz que está
resolvido"*.

📊 O substituto do condomínio já foi baixado na auditoria: `200 application/pdf`,
1.185.165 bytes.

- **Destrava:** nada externo. O caminho está vivo e medido (P-131).
- **De quem é:** 🤖 execução.
- **O que custa esquecer:** cada resposta sobre cobertura sai de um contrato que
  não vale mais, e o sistema não tem como saber disso — não há campo de fim de
  vigência em documento nenhum.

---

## P-132 · 🟠 39,2% das cartas com seguradora são de companhias sem contrato nenhum

📊 08/08/2026, sobre as 2.454 cartas com `insurer_key`: **961 (39,2%)** são de
seguradoras com **zero** condições gerais no acervo.

| seguradora | cartas | sinistro+assistência | site próprio | SUSEP |
|---|---:|---:|---|---|
| **yelum** | 359 | 163 | 🔒 exige CPF e nº da apólice | ✅ 54 versões, vig. 30/04/2026 |
| **hdi** | 267 | 119 | ⚠️ caminho antigo **morto (500)** | ✅ RCF 35 v. · Residencial 18 v. |
| zurich | 76 | 16 | ✅ residencial e vida | ✅ 6 versões |
| alfa | 40 | 15 | ✅ índice público com histórico | ✅ 21 versões |
| sura | 17 | 7 | ⚠️ WAF bloqueia | ✅ 20 versões |

**A Yelum é o caso que prova o método:** o site dela tem porteiro, o repositório
da SUSEP não. 📊 Duas versões baixadas na auditoria, `200 application/pdf`.

### O que NÃO vale, e é metade do valor desta entrada

- **Youse** (139 cartas) — 📊 **100 são de cobrança, 7 de sinistro/assistência**.
  Condições gerais não respondem *"por que meu boleto não chegou"*. Entra por
  ser barato, nunca por ser importante.
- **Itaú** (1 carta) e **Sompo** (8) — 📊 os dois **saíram do auto massificado**.
  A Sompo vendeu o varejo à HDI em 2023; o Itaú hoje vende Porto.
- **SES / sinistralidade** — 542 MB e responde **zero** perguntas de segurado no
  WhatsApp. É ativo de mesa de negociação (SPEC-065/067), não deste agente.
- **Ranking de reclamações** — 📊 a própria página declara os dados **congelados**
  no 4º trimestre de 2025.
- **Registro de corretores** — 📊 é uma SPA que exige JS e a API pede JWT. E este
  agente fala com **segurados**, não com corretores.

---

## P-133 · 🟠 Quatro das cinco ingestões travadas são bug nosso, não fonte morta

📊 Das 5 linhas em `discovered` com 0 chunks, **4 URLs respondem 200**:

- **Tokio** — 403 no nosso robô, **200 com User-Agent de navegador**
- **Bradesco Auto** — PDF de **5,7 MB**, estoura teto/timeout
- **Azul Residencial** — URL viva (200, 337 KB)
- **Youse** — `cdn.youse.com.br/docs/condicoes-gerais-plano-auto.pdf` (200)
- **HDI** — 🔴 a única que morreu de verdade (500 no caminho antigo)

**E um defeito de dado nosso:** 📊 os números de processo da Tokio estão gravados
**truncados** (`15414.100335/2004`, sem o `-74`). Com os dígitos: 50 versões,
vigente desde 14/04/2026. Truncado: **não encontrado, em silêncio**.

- **Destrava:** nada. Três consertos pequenos.
- **O que custa esquecer:** parece falta de fonte e é falta de cabeçalho HTTP.

---

## P-134 · 🟡 Pode ser busca, não acervo — medir antes de creditar

📊 Os limites de assistência da Porto (guincho 400 km, chave reserva 100 km) **já
estão dentro da CG140 que temos indexada**.

E o prompt do agente **não proíbe** falar de cobertura: ele exige **evidência**
(`prompts.py:201` — *"NUNCA confirme cobertura sem evidência da apólice"*).

Ou seja: para a Porto, pode não faltar documento — pode faltar **recuperação**.
Antes de creditar a documento novo uma melhora que seria de busca, medir: fazer
a pergunta ao agente hoje e ver se o trecho certo aparece entre os que chegam.

⚠️ Vale duplo porque 📊 o reranker Cohere continua **desligado** e, sem ele, os
trechos que chegam ao modelo saem de um RRF de duas buscas não comparáveis.

> **Atualizado em 08/08/2026 — o "3" desta pendência venceu.** SPEC-070 LOTE 0
> item 5: o corte final deixou de ser `rerank(top_k=3)` sobre uma lista única e
> passou a ser orçamento por namespace (3 vagas de contrato + 3 de carta + 2 do
> acervo da corretora). O trecho de contrato deixou de disputar vaga com a carta
> curta, que o BM25 favorecia por comprimento. A medição pedida acima continua
> valendo — e agora tem chance de dar outro resultado.

---

## P-135 · 🟢 O reranker Cohere: só falta a variável (e um restart)

📊 Auditado em 08/08/2026. O serviço está **completo e correto**:

| peça | estado |
|---|---|
| pacote `cohere>=5.0.0` | ✅ em `requirements.txt` |
| campo `COHERE_API_KEY` | ✅ em `config.py` (`Optional[str] = None`) |
| documentação | ✅ em `.env.example` |
| `RerankService.rerank()` | ✅ chama, injeta `rerank_score`, cai para pass-through no erro |
| cortes de relevância | ✅ 0,50/0,40/0,30 **preservados byte a byte** para a escala da Cohere |
| teste dos dois estados | ✅ `test_o_contrato_e_a_carta_nao_disputam_a_mesma_vaga.py` §6 |

**Falta a variável no ambiente.** 📊 Ela não está no repositório em lugar nenhum
(`docker-compose.yml` só sobe infra; o backend roda pelo EasyPanel) —
`pydantic-settings` a lê direto do ambiente, então basta declará-la lá.

⚠️ **E um restart.** `get_rerank_service()` é singleton e lê `settings` uma vez:
trocar a env com o processo de pé não liga o reranker.

O que muda quando entrar: `_get_score_scale` passa a devolver `rerank` e os
cortes migram de cosseno (0,28) para a escala calibrada da Cohere (0,40). O
caminho já existe e está testado nos dois estados.

- **Destrava:** uma chave da Cohere + restart do backend.
- **Dono:** 🧑 Founder (segredo).
- **O que custa esquecer:** 💭 ~US$ 2 por mil buscas. Sem ela, a ORDEM dos
  trechos dentro de cada faixa continua saindo de RRF, que mede concordância de
  posição, não relevância. A cota garante que o contrato **esteja na mesa**; o
  reranker é quem escolhe **qual** trecho de contrato.

---

## P-136 · 🔴 Quatro migrations da SPEC-067 escritas e **não aplicadas**

Escritas em 08/08/2026 pelo LOTE 0 (itens 4, 6, 7 e 8). Cada uma traz APPLY,
VERIFY executável e ROLLBACK, e nenhuma foi aplicada — por decisão: **quem
aplica é o Founder, depois de revisar.**

| ordem | arquivo | o que destrava |
|---|---|---|
| 1 | `20260808_01_spec067_a_vigencia_mora_na_versao.sql` | a vigência da SUSEP passa a ter onde morar (📊 hoje NULL em 35/35) |
| 2 | `20260808_02_spec067_o_indice_sabe_de_que_versao_veio.sql` | o backfill dos 29 endereços do esquema legado |
| 3 | `20260808_03_spec067_a_carta_sabe_de_que_contrato_saiu.sql` | achar as cartas de um contrato substituído |
| 4 | `20260808_04_spec067_o_pdf_e_o_texto_tem_endereco.sql` | os ponteiros do MinIO |

⚠️ **O código já grava nessas colunas.** `insurance_corpus.ingerir()` escreve
`vigencia_fonte`, `qdrant_doc_id`, `storage_ref`, `text_storage_ref` e
`arquivado_em` na linha da versão. **Enquanto as migrations não forem
aplicadas, o primeiro documento ingerido vai falhar no INSERT** (coluna
inexistente). Não é degradação silenciosa — é erro alto, e isso é proposital.

- **Destrava:** revisão + APPLY na ordem 01 → 02 → 03 → 04.
- **Dono:** 🧑 Founder.
- **O que custa esquecer:** o LOTE 1 (Porto) não roda. E o item 4 é o que fecha
  a janela: 📊 a URL da HDI devolve 500 e a da Allianz 403 — documento não
  guardado hoje pode não ser baixável amanhã.

---

## P-137 · 🟡 `normative_documents` e `..._versions` eram `SEM_ARQUIVO`, não órfãs

📊 08/08/2026. As duas tabelas **não têm arquivo** em
`backend/supabase/migrations/`, mas **têm versão** no banco:
`20260725215808 spec057_h1_normative_corpus`.

Um levantamento anterior afirmou que não tinham versão — e "órfã sem versão"
pede migration nova, que duplicaria o histórico. O DDL foi reconstruído do
catálogo do Postgres e registrado em
`docs/canon/sql/reconstruidas/20260725215808_spec057_h1_normative_corpus.sql`
(**proibido aplicar**), e o `MANIFEST.md` foi atualizado.

O que **não** foi feito: a reconciliação completa dos 92 versionamentos contra
os 60 arquivos. Um cruzamento por nome apontou dezenas de divergências, mas o
casamento por nome é pouco confiável — `20260803_01_spec063_destino_de_suporte_unico.sql`
corresponde à versão `spec063_01_destino_de_suporte_unico` e nenhuma regra
simples liga os dois. **Esse número não é medição.**

- **Destrava:** o baseline da SPEC-054 Bloco B, gerado do banco vivo.
- **Dono:** 🤖 execução (SPEC-054 B).
- **O que custa esquecer:** cada SPEC que passa acrescenta objeto sem dono
  documental, e o baseline fica mais caro a cada semana.

---

## P-138 · 🟡 A costura de um byte entre o item 1 e o item 4 da SPEC-067

`insurance_corpus._baixar_pdf_direto` ganhou **uma linha**:

```python
self._pdf_baixado = {"bytes": corpo, "media_type": "application/pdf"}
```

É o único ponto onde os bytes do PDF existem. `_guardar_a_fonte()` lê dali e
põe no MinIO. A função é a mesma que o item 1 reescreve (PyPDF2 → PyMuPDF).

⚠️ Se uma reescrita levar a linha embora, o arquivamento **degrada em
silêncio**: o texto continua sendo guardado e o PDF não.
`test_o_acervo_guarda_a_fonte_e_a_versao.py` §3 confere que ela existe, e a
mutação M3 provou que a conferência morde.

- **Destrava:** nada — está funcionando. É um aviso de fronteira.
- **Dono:** 🤖 quem mexer em `_baixar_pdf_direto`.
- **O que custa esquecer:** 📊 a URL da HDI já devolve 500. PDF não guardado é
  PDF perdido.

---

## P-139 · 🟡 A tabela é bloco atômico, mas não foi linearizada em frases

A SPEC-067 §4.5 pede duas coisas para tabela, e **só a primeira foi feita**:

| pedido | estado |
|---|---|
| tabela é bloco atômico, com título e notas de rodapé no mesmo pedaço | ✅ feito |
| corrigir célula girada (`odarugeS`) | ✅ não se aplica ao caminho escolhido |
| **linearizar a grade em frases** com `pdfplumber.extract_tables()` | ⬜ **não feito** |

O que existe: `regioes_de_tabela()` reconhece a corrida de linhas curtas, não
detecta título nem corta dentro dela, e estica a região até engolir `(1)`,
`(2)`, `*` e `Obs.`. A grade entra no pedaço como o PyMuPDF a entrega — uma
célula por linha, em ordem de leitura.

📊 Medido em 08/08/2026 no CG140: a tabela de carro reserva sai inteira, num
pedaço só, com `630`, `882` e as duas notas (`Limite diário R$ 90,00` e
`R$ 126,00`). A pergunta *"quantos dias de carro reserva eu tenho?"* é
respondível por esse pedaço sozinho — o limite é em reais, e a nota é que dá a
diária que converte reais em dias.

📊 E `pdfplumber` foi testado na página real (índice 102): devolve a grade de
24 linhas × 15 colunas, com as células giradas invertidas (`odarugeS`,
`ortsiniS`, `oriecreT`, `enaP`) — que o PyMuPDF, esse, lê certo. Linearizar
exigiria casar cabeçalho de dois níveis com células mescladas, e isso não cabia
no bloco sem arriscar o que já funciona.

- **Destrava:** nada urgente. Vira prioridade se aparecer uma pergunta cuja
  resposta dependa de **cruzar** linha e coluna (ex.: "quanto vale a cláusula
  26F para carro de porte médio?"), que a grade em ordem de leitura não entrega
  sem o modelo inferir o alinhamento.
- **Dono:** 🤖 execução (LOTE 1, se a conferência dos 10 pedaços reprovar).
- **O que custa esquecer:** 💭 a resposta que exige cruzamento sai plausível e
  errada — que é o pior formato de erro num contrato.

---

## P-140 · 🟡 Três produtos da Porto usam o formato de processo anterior a 2004

📊 Medido em 08/08/2026 pelo levantamento real
(`scripts/acervo/coletar_seguradora.py --seguradora porto --diagnostico`):
dos 71 produtos de varejo da Porto no catálogo oficial, **68 tiveram a versão
vigente confirmada e 3 não**:

```
auto   10.003506/01-14     05 | AUTOMÓVEL - CASCO
vida   005-00737/00        13 | VIDA (INDIVIDUAL)
vida   10.005843/99-51     13 | VIDA (INDIVIDUAL)
```

Não é truncamento nosso — é como o **próprio catálogo da SUSEP** os publica.
São processos anteriores ao formato de 17 dígitos, e o REP2 não os aceita: o
script os marca `processo_malformado` e **não indexa**, que é o comportamento
certo (§3.2.1).

⚠️ Eles **não** entram na lista `PENDENCIAS_DE_REPARO` do `susep_rep2.py`: ali
moram os que perderam dígito na nossa gravação e o catálogo recupera. Estes
três estão íntegros na fonte — o formato é que é de outra época. Inventar
dígito verificador para eles é o erro que aquela lista existe para impedir.

- **Destrava:** descobrir se o REP2 tem endereço alternativo para processo em
  formato antigo, ou confirmar que o produto está morto por outra via.
- **Dono:** 🤖 execução (LOTE 1, se algum deles for um produto que se vende).
- **O que custa esquecer:** 💭 um produto vivo fica fora do acervo para sempre,
  e a ausência é silenciosa — ninguém pergunta pelo que não está na lista.

---

## P-141 · 🟡 O ramo oficial da SUSEP não tem coluna — mora em `notes`

A SPEC-070 §5.2 é explícita: *"O REP2 devolve o ramo oficial numerado
(`05 | AUTOMÓVEL - CASCO`). **Grave o código e o nome oficiais.** Criar
vocabulário paralelo ao do regulador é divergência de graça."*

`normative_documents` não tem onde. O que existe é `product_line`, que é o
**nosso** slug (`auto`, `residencial`, `condominio`, …) e é o que a busca já
filtra na raiz do payload. O maestro grava o ramo oficial em
`normative_documents.notes` (`"ramo oficial SUSEP: 05 | AUTOMÓVEL - CASCO"`) e
o repete no `.jsonl` dos subagentes.

⚠️ Texto livre não é consultável. A pergunta *"quais documentos nossos são do
ramo 05?"* continua sem resposta em SQL.

- **Destrava:** uma migration com `susep_ramo_codigo` e `susep_ramo_nome` em
  `normative_documents` — expand-first, duas colunas nulas, nenhum leitor muda.
  Exige manifesto (CLAUDE.md §8).
- **Dono:** 🧑 Founder autoriza o manifesto · 🤖 execução escreve.
- **O que custa esquecer:** 💭 a divergência que a §5.2 quer evitar continua de
  pé, só que escondida numa coluna de observações.

---

## P-144 · 🟡 O vizinho gêmeo — por que a reancoragem NÃO pode ser automática

📊 Achado por um auditor em 08/08/2026, antes de virar defeito.

A auditoria da §6.5 sinaliza quando um pedaço vizinho ancora melhor que o
citado. É tentador aplicar o movimento automaticamente. **Não faça.**

> No condomínio, a carta das exclusões da cobertura Básica **Ampla** (33.1.2.2)
> teve como vizinho melhor a lista da Básica **Simples** (33.1.1.1) — os textos
> são quase idênticos, e a diferença é **exatamente a alínea que some** (danos
> elétricos). Um movimento automático teria trocado a cobertura da carta por
> outra, mais barata e com escopo diferente: **erro muito mais grave que o
> original**.

A regra que sai daí: **semelhança alta entre citado e vizinho é motivo para NÃO
mover, não para mover.** Quando dois trechos são gêmeos, o diferencial mede
ruído, não evidência — e só a leitura separa.

- **Destrava:** nada. É uma trava a acrescentar ao script se algum dia alguém
  quiser automatizar, e está registrada aqui para que a ideia não volte limpa.
- **Dono:** 🤖 execução.
- **O que custa esquecer:** trocar a apólice sobre a qual a carta fala, sem que
  nada no sistema acuse.

---

## P-145 · 🟢 O teste da faceta foi MEDIDO e recusado — não tente de novo sem dados novos

📊 08/08/2026. Um auditor sugeriu um sinal barato: *"o trecho citado contém
material da faceta que a carta declara?"* — `prazo` deveria trazer número e
unidade de tempo, `exclusao` deveria trazer verbo excludente. Ele viu dois casos
em que isso apontava o erro sozinho.

Implementei e medi contra os 19 erros que quatro auditores confirmaram:

```
              erros pegos     falso alarme
exclusao         2 de 14          1 de 27
limite           0 de  0         17 de 19
prazo            1 de  2          0 de  3
documento        0 de  0          1 de  2
TOTAL            3 de 19         19 de 64
```

**Não adotado.** `limite` é ruído quase puro — a marca textual que escrevi não
corresponde a como o contrato escreve limite. `exclusao` tem boa precisão e
pega 14% dos erros. No acervo inteiro o teste acusaria 87 cartas de 1.121, e a
maioria sem motivo.

Um sinal que grita mais do que acerta ensina o próximo a ignorar sinal.

- **Destrava:** um lote novo, com erros confirmados por auditoria, para calibrar
  as marcas por faceta com mais de 19 exemplos.
- **Dono:** 🤖 execução.
- **O que custa esquecer:** alguém relê o relatório do auditor, acha a ideia
  boa — ela **é** boa em tese — e implementa de novo sem medir. Por isso o
  número fica aqui.

---

## P-146 · 🟡 O breadcrumb que perde o pai — investigado, MEDIDO e não aplicado

📊 09/08/2026. Um auditor do P-143 achou uma causa estrutural para o "adjetivo
enxertado" e propôs o conserto de maior alavancagem do lote:

> *"O enxerto não está distribuído por ramo nem por cobertura: está distribuído
> por **trecho de documento onde o breadcrumb do chunker quebrou**. Enquanto o
> caminho preserva `33.2. COBERTURAS ADICIONAIS > 33.2.x`, os casos são
> `provado`. A partir de `#0138` o caminho reinicia — e todo caso dali em diante
> virou reescrita. **Consertar o breadcrumb converteria ~20 das 23 reescritas em
> `provado`, sem tocar no destilador.**"*

**A causa é real e eu a reproduzi.** `_RE_NUMERADO` exige que a linha comece com
dígito, e o documento usa `►` de forma inconsistente:

```
#0135  ►33.1.3 … > 33.2. COBERTURAS ADICIONAIS > 33.2.6 PERDA DE ALUGUEL
#0138  ►33.2.7 ALAGAMENTO                        ← o pai sumiu
```

`►33.2.7` não casa o padrão numerado, cai na regra de RAIZ e **reinicia a
pilha**. As outras regras de título já toleram o marcador (`^[►▶\s]*`); esta
não. O nível deveria vir da numeração, não do símbolo.

### 📊 Por que NÃO foi aplicado

Escrevi o conserto e medi o impacto em 6 documentos reais:

```
documento              hoje   com o conserto   veredito
allianz condominio      319        319         IDÊNTICO
allianz auto            391        391         IDÊNTICO
allianz empresarial     341        341         IDÊNTICO
porto vida              155        155         IDÊNTICO
porto auto              484        487         MUDOU (+3)
porto condominio        277        276         MUDOU (−1)
```

E medi o ganho onde o corte NÃO muda — que seria ganho de graça:

```
allianz condominio: 319 de 319 pedaços com o mesmo corpo
                    0 caminhos melhorados
```

**Zero.** O conserto não alterou uma única trilha no documento onde eu conseguia
comparar sem quebrar nada. Em compensação, mudaria o corte de 2 documentos —
deslocando os `unit_id` de **530 cartas já publicadas e auditadas**.

O ganho de ~20 cartas era 💭 inferência do auditor, tirada de um lote de 43. O
custo é 📊 medido e certo. **Reverti.**

- **Destrava:** um lote em que os documentos afetados sejam re-cortados de
  qualquer jeito — ou seja, quando a Porto publicar versão nova de auto ou
  condomínio. Aí o conserto entra sem custo, junto com a re-destilação que a
  versão nova exige.
- **Dono:** 🤖 execução.
- **O que custa esquecer:** nada hoje. O conserto está escrito neste registro e
  a causa está diagnosticada; quem retomar não precisa redescobrir.
- ⚠️ **O que NÃO fazer:** aplicar "porque é obviamente melhor". Foi o que eu ia
  fazer, e a medição do caminho — 0 de 319 — mostrou que o obviamente melhor não
  se sustentava naquele documento. Meça o caminho antes, não só o corte.

---

## P-147 · 🟡 Contaminação de seção NA FONTE — nenhum guarda automático pega

📊 09/08/2026, achado por um auditor de ancoragem no Allianz Empresa PME.

O PDF emendou duas seções. Sob o título `14.2. Riscos Excluídos` da cobertura de
**Quebra de Vidros** aparecem, no fim da lista alfabética, três alíneas que são
de **Equipamentos Eletrônicos**:

```
p) Sobrecarga… capacidade normal de operação dos equipamentos segurados
q) Negligência do segurado na utilização dos equipamentos
r) Queda, quebra, amassamento ou arranhadura
```

Uma carta usou a alínea `p` e afirmou que a cobertura de **vidros** exclui
sobrecarga *"dos equipamentos segurados"*. 📊 Corrigida — a oração saiu.

### Por que isto é uma família nova de defeito

**O endereço está CERTO.** A carta cita o pedaço que realmente contém aquele
texto. Então:

- `conferir_ancoragem.py` não acusa — não é órfã, não é cópia, o vizinho não
  ancora melhor;
- a auditoria de ancoragem devolve `ok`, e devolve com razão;
- a auditoria de fidelidade (P-143) não acusa — a afirmação **tem** lastro no
  trecho;
- só um leitor que conheça o produto percebe que "equipamentos segurados" não
  faz sentido numa cobertura de vidro.

Foi exatamente o que aconteceu: o auditor marcou os 4 casos como `ok` — o
veredito correto — e **relatou este defeito por fora**, na seção de observações.

O mesmo auditor listou outros dois pedaços do mesmo documento com cabeçalho
mentiroso: `#0238` tem título *"Riscos e Bens Cobertos Específicos"* e corpo
inteiramente de exclusões; `#0211`/`#0212` estão sob *"Reembolso de honorários
de perito Contábil"* e carregam a seção `18.3. Definições`.

- **Destrava:** nada de fora. É uma terceira auditoria, com a pergunta:
  *"o texto deste trecho pertence à cobertura que o título diz?"*
- **Dono:** 🤖 execução.
- **Escopo sugerido:** os pedaços onde o vocabulário do corpo destoa do título —
  falar de `equipamentos` sob um título de `vidros`, de `veículo` sob um título
  de `vida`. 📊 Dois destiladores já acharam isso sozinhos e não destilaram:
  o do vida em grupo achou *"vistoria prévia no veículo"* num clausulado de
  vida; o de equipamentos achou carência de *câncer e cesta básica* num produto
  de morte acidental.
- **O que custa esquecer:** a carta afirma uma exclusão que não é daquela
  cobertura, com o endereço certo apontando para o texto certo. É o formato mais
  difícil de desmentir — quem for conferir **acha exatamente o que a carta diz**.
- 💭 **Hipótese barata a testar:** os destiladores acharam esses casos sozinhos
  quando o contraste era grande (veículo × vida). O caso do PME é sutil
  (equipamentos × vidros, ambos patrimoniais) e escapou. Talvez baste pedir no
  prompt: *"antes de escrever, pergunte se este texto pertence mesmo à cobertura
  do título"*.


---

# 🟠 COBRANÇA MULTI-SEGURADORA — o que ficou aberto (10/08/2026)

## P-98 · 🔴 O `--headless=new` precisa ir para o worker em produção

📊 Medido em 10/08/2026 contra `www.hdi.com.br/hdidigital/`, um fator por vez,
com linha de CONTROLE repetida no início e no fim da bateria:

```
headless clássico ...............  BLOQUEADO   Access Denied (Akamai)
+ args anti-automação ...........  BLOQUEADO
+ script de stealth .............  BLOQUEADO
+ args E stealth ................  BLOQUEADO
navegador COM janela ............  PASSOU
--headless=new ..................  PASSOU      ← e roda sem tela
```

**Cinco variações deram o mesmo bloqueio → nenhuma delas era a causa.** O fator
é o MODO headless: o clássico é um binário separado, com fingerprint próprio, e
o Akamai o reconhece.

📊 **Linha de controle da mudança:** a Allianz, com o modo novo, baixou **4 de 4
boletos** (`via=api_chain`, 103193/117062/117223/117589 bytes). Não houve
regressão — e é isso que dá direito de creditar o ganho ao modo novo.

- **Destrava:** o código já está em `worker._launch_kwargs()`. Falta o deploy.
- **Dono:** 🧑 Founder decide o merge · 🤖 já entregou.
- **Custa se esquecer:** a HDI (e provavelmente Yelum, Porto e toda seguradora
  atrás de Akamai) **nunca** funciona no worker atual. Não é bug da journey.

## P-99 · 🟠 O Akamai da HDI também reage à FREQUÊNCIA

📊 Depois de ~14 acessos em 30 minutos, o `--headless=new` que passava começou a
receber `Access Denied` — e continuou bloqueado 12 minutos depois. **É bloqueio
por IP, temporário, disparado por volume.**

> Isso **valida** a arquitetura de duas fases: a fase COLHER entra no portal
> **uma vez por execução** e sai. Fosse um-a-um ponta a ponta, o robô entraria
> 20 vezes por rodada e seria bloqueado no meio.

- **Destrava:** nada. É desenho, não conserto.
- **Regra dura:** reusar `portal_sessions` sempre que possível, e nunca fazer
  login por item.
- **Custa se esquecer:** alguém "otimiza" o Cobrador entrando por cliente, e a
  corretora perde o acesso ao portal dela.

## P-100 · 🔴 Falta a estrutura HTML da tela de resultado da HDI

A cadeia da HDI está provada até o passo 3:

```
login ...................... ✅ provado (camada visível + camada real)
passo 1 (ponte legado) ..... ✅ HTTP 200, identidade colhida (m_cod_corretor, c_pc, l_s, n_s)
passo 2 (tela de busca) .... ✅ HTTP 200
passo 3 (a lista) .......... ⚠️  HTTP 200, mas o parser leu 0 linhas
passo 4 (o boleto) ......... ⏳ não exercitado
```

📊 O passo 3 respondeu com corpo, então **ou** o `s_tipo` pedido não traz nada,
**ou** o HTML não casa com `extrair_parcelas`. Não dá para saber sem ver o HTML,
e o Akamai cortou a sessão antes.

- **Destrava:** 🤖 uma rodada de `ver_html_parcelas.py` com o IP liberado, ou
  🧑 o founder colando o **Response** da chamada `dsp_parcelas_view_2008.htm`
  (aba Response do F12, não Headers).
- **Custa se esquecer:** é o único passo que separa a HDI de funcionar.

## P-101 · 🟠 Débito automático em atraso não tem boleto para enviar

📊 Na captura de 10/08, a **única** parcela em atraso era débito automático, e a
coluna `Gerar` dizia *"Parcela diferente de Boleto Bancário."* em vez de
*"2ª via"*. Converter para boleto está atrás de **ALTERAÇÕES FINANCEIRAS**, que
escreve no contrato do segurado — proibido.

O código já marca esses casos (`sem_boleto_motivo`) e eles entram no relatório.
**Falta a decisão de produto:** o que a corretora quer que aconteça?

```
a) só avisar o segurado que o débito não passou, sem boleto
b) abrir tarefa para a atendente humana converter no portal
c) não cobrar, só relatar
```

- **Dono:** 🧑 Founder — é decisão comercial, não técnica.

## P-102 · 🟠 Resulta e AutoFleet continuam sem destino de handoff

📊 `human_support_destinations` tem 2 linhas, **ambas da AMANDUS SEGUROS**.

O cano está construído e funciona vazio: sem destino, o problema vai para o
relatório e a rotina abre com o aviso. No dia que o grupo existir, é preencher
um campo — nada precisa ser refeito.

- **Destrava:** 🧑 criar o grupo de suporte de cada corretora.

## P-103 · 🟡 A Yelum devolve 403 a cliente automatizado

📊 `novomeuespacocorretor.yelumseguros.com.br` respondeu **403** tanto na raiz
quanto em `/home`, a um cliente HTTP simples. Provavelmente o mesmo tipo de WAF
da HDI — e provavelmente a mesma solução (`--headless=new`).

- **Custa se esquecer:** quem for fazer a Yelum vai achar que a credencial está
  errada. Não está: 📊 ela foi gravada em 10/08 e o portal recusa antes do login.



---

## ✅ P-100 RESOLVIDO em 12/08/2026 — a HDI baixa boleto

📊 Prova real, uma visita ao portal:

```
status ............ done
mensagem .......... HDI: 1 inadimplente(s), 1 boleto(s)
boleto ............ ok=True · 27.037 bytes · via=dsp_boleto · valida como %PDF
```

**Os quatro defeitos que impediam, e o que cada um ensinou:**

| # | O defeito | A lição |
|---|---|---|
| 1 | **A busca é assíncrona.** O 1º POST devolve *"aguarde, processando"* + um form que se reenvia em 5 s. Era essa sala de espera que eu lia como "tabela vazia" | HTTP 200 com corpo de 4 KB **não** é resultado. Só o reenvio traz a tabela |
| 2 | **`s_tipo=1` é "A vencer"**, não "Atrasadas" — eu pedia justamente quem não interessa | 📊 O `<select>` do portal responde em 3 segundos o que eu tentei adivinhar em 5 rodadas |
| 3 | **O boleto não é `<a href>`** — mora dentro de `onclick="window.open('dsp_boleto.htm?p=…')"` | Procurar `href` não acha nada, mesmo com a tabela lida certa |
| 4 | **Janela máxima de 30 dias** (validação do próprio botão Buscar). Meu padrão era 365 | Varredura em blocos, sem buraco entre eles |

**E duas descobertas de estrutura que valem para o parser de qualquer portal legado:**

- **Uma `<table>` por documento**, não uma tabela com N linhas. E a primeira nem
  fecha o `<tbody>` — parser que exige HTML bem formado quebra aqui.
- **Crédito também não gera boleto**, não só Débito. A marca certa é a frase
  *"Parcela diferente de Boleto Bancário"*, não a forma de pagamento.

📊 Tudo isto está preso por **102 asserções** rodando contra uma fixture com a
estrutura real do HTML e os dados trocados (`backend/tests/fixtures/hdi_parcelas.py`)
— zero acesso ao portal para testar.

- **O que falta para a HDI ser 100%:** rodar pelo worker (fila `portal_jobs`) com
  o storage ligado. Isso depende do deploy (P-98), não de mais código.

## P-104 · 🟡 A regra de ouro contra bloqueio, aprendida a duras penas

📊 Dois portais independentes (HDI e Tokio) passaram a recusar acesso depois de
~15 e ~4 visitas em menos de 30 minutos. **Eles reagem à frequência, não ao
método.**

```
FASE 0 (reconhecimento) .... no máximo 2 visitas
FASE 2 (replicar) .......... 1 visita
FASE 3 (journey) ........... teste roda de FIXTURE, zero visita
FASE 4 (ligar) ............. 1 rodada, com a Allianz junto como controle
```

> **O portal da corretora não é ambiente de teste.** Toda leitura repetida sai de
> fixture salva. Foi assim que a HDI fechou: 4 defeitos corrigidos offline, uma
> única visita para provar.



---

## ✅ P-98 e P-105 RESOLVIDOS em 12/08/2026 — a HDI fecha, e não precisou de proxy

📊 **Prova pela fila real do worker de produção:**

```
HDI ....... done · 1 inadimplente · boleto de 27.037 bytes no bucket
Allianz ... done · 4 inadimplentes · 4 boletos (LINHA DE CONTROLE)
saida_de_rede ... "direta (IP do servidor)"   ← sem proxy nenhum
```

### O Akamai eram DOIS fatores, e nenhum era o IP

| Fator | Sintoma | Correção |
|---|---|---|
| Impressão digital em **JavaScript** | headless clássico é outro binário | `--headless=new` |
| **`HeadlessChrome` no cabeçalho** | filtro derruba antes de rodar JS | `user_agent_sem_headless()` |

### A lição que quase custou uma assinatura de proxy

O primeiro diagnóstico comparou o navegador com "um cliente HTTP simples"
(`page.request`) e concluiu, com confiança, que **o fator era o IP**.

> **O teste estava furado.** `page.request` **herda o User-Agent do contexto** —
> os dois clientes mandaram o mesmo cabeçalho. Ele não isolou o que dizia
> isolar, e produziu uma conclusão confiante e errada.

O que decidiu foi variar **um fator por vez do mesmo IP**, com controle nas duas
pontas: UA limpo passa, UA padrão é bloqueado, UA limpo passa.

**Corolário para o método (SPEC-070):** um teste que não consegue separar o que
promete separar é pior que teste nenhum — ele *fecha* a investigação no lugar
errado. Antes de concluir, perguntar: *"este teste conseguiria dar o outro
resultado?"*

### O que ficou pronto e desligado

`proxy_do_portal()` — saída de rede por portal (`PORTAL_PROXY_<PORTAL>` ou
`PORTAL_PROXY_DEFAULT`). **Não é necessária hoje**, e está sem nenhuma variável
configurada. Fica para o dia em que um portal recusar o IP de verdade — e aí é
ligar uma variável, sem deploy de código.

- **Custa se esquecer:** 📊 o IP do servidor é `AS47583 Hostinger`, faixa de
  hospedagem. Um portal mais agressivo (Porto, Azul) pode barrar por ele — e a
  saída já está construída.


---

## TOKIO MARINE — fechada em 12/08/2026, e o que ela deixou

📊 Job `bc1dfaa0` pela fila de produção: `done`, 3 boletos no bucket, saída
direta (sem proxy). Detalhe em [`portais/PORTAL-tokio.md`](portais/PORTAL-tokio.md).

| # | O que ficou | De quem | Custa se esquecer |
|---|---|:--:|---|
| P-106 | Onde exatamente fica o limite da 2ª via da Tokio — medido em 26 dias (sem) e 7 dias (com); 💭 a hipótese é o `NÃO RECEBER APÓS 15 DIAS` do próprio boleto | 🤖 | nada: o caso já vira tarefa humana com o motivo escrito. Saber o número só deixaria o aviso mais preciso |
| P-107 | Se inadimplente de **cartão de crédito** aparece em `Clientes inadimplentes` ou **só** em `Débitos Pendentes` / `Cobranças no Cartão` | 🤖 1 visita | 🔴 se for "só", um grupo inteiro de inadimplentes fica invisível — a falha que a SPEC-070 §2 proíbe |
| P-108 | Uma corretora com **2+ códigos de corretor** na Tokio (a AutoFleet tem 1) | 🧑 Founder indicar | 🔴 metade da carteira invisível, em silêncio |
| P-109 | O caso **CNPJ** na URL do detalhe (só CPF foi exercitado de ponta a ponta) | 🤖 sai sozinho | a apólice PJ não baixaria boleto — mas apareceria como retido, não como silêncio |
| P-110 | O que é o ramo **`312`** vs `0531` na mesma apólice | 🧑 atendentes | nada hoje: nenhum dos dois decide coisa alguma |

### O defeito que a Tokio revelou — e que era das TRÊS seguradoras

📊 Dos 4 downloads da primeira rodada, 3 viraram PDF e 1 não. Esse item
**continuava entrando na fila de envio**: a única porta era
`sem_boleto_por_regra`, que pega quem a *seguradora* recusa, não quem *falhou
ao baixar*. O segurado receberia "Segue o boleto abaixo" com anexo nenhum.

Corrigido em `fila_de_cobranca(boletos=…)`, e vale para Allianz, HDI e Tokio.

> **A lição:** o comentário da própria função já avisava desse desfecho. Um
> caminho estava coberto e o outro não — e só a rodada real com uma falha
> parcial mostrou a diferença. Teste com tudo dando certo não encontra isto.

## PRÓXIMA SEGURADORA — a porta das três candidatas, medida

📊 12/08/2026, carga pública das telas de login (sem tentar entrar):

| Portal | Peso | Travas detectadas | Veredito |
|---|---:|---|---|
| **Yelum** | 12 KB | **nenhuma** | ✅ **a próxima** |
| Bradesco | 1,79 MB | 🔴 captcha **+ Akamai** | deixar por último |
| Porto | 90 KB · 7 iframes | 🔴 captcha **+ Incapsula (Imperva)** | precisa de estratégia própria |

📊 Yelum: login em `/account/login`, site em **Drupal**, com um
`themes/custom/liberty_cohesion/js/portal_api.js` — indício de camada de API.
Credencial já existe para as duas corretoras; ❓ a senha precisa ser confirmada.

- **Custa se esquecer:** MAPFRE está travada esperando a Saionara (🧑). Yelum
  não depende de ninguém de fora — é a única que dá para começar hoje.

---

## YELUM — fases 1 a 4 fechadas em 12/08/2026

📊 A journey rodou contra o portal real (corretora Resulta) e trouxe um boleto
de **5.908 bytes — exatamente o tamanho do PDF que o Founder baixou à mão** no
mesmo cliente. Detalhe em [`portais/PORTAL-yelum.md`](portais/PORTAL-yelum.md).

| # | O que ficou | De quem | Custa se esquecer |
|---|---|:--:|---|
| P-111 | **Fase 5** da Yelum — rodar pela fila de produção | 🧑 redeploy do `portal-worker` | a Yelum só varre quando o serviço tiver a imagem nova |
| P-112 | A credencial da **AutoFleet** na Yelum (a da Resulta entra; a outra dá erro mesmo parecendo certa) | 🧑 Founder / Saionara | metade das corretoras fica sem Yelum |
| P-113 | O **teto de visitas** da Yelum — não medido (Tokio ~4, HDI ~15) | 🤖 | tratamos como o mais restritivo até saber |
| P-114 | Se a API aceita janela **> 90 dias** (a tela limita) | 🤖 1 chamada | dívida antiga fica fora — mas a testemunha PEGA isso e para a varredura |
| P-115 | Se a credencial **atravessa para a HDI** (mesmo grupo, mesma API) | 🤖 1 visita | seria uma porta a menos para manter |

### 🔴 O erro que eu cometi, e o guarda que ele gera

Eu afirmei ao Founder que **a Yelum não tinha trava nenhuma** — e recomendei
começar por ela justamente por isso. Estava errado: o app logado roda **Akamai
Bot Manager** (`sensor_data` → `{"success": true}`, script de 560 KB com `bmak`,
mPulse).

O que eu medi foi a **página pública de marketing**; o que eu afirmei foi sobre
o **app logado**. São coisas diferentes, e a pública não é protegida.

> **É a terceira vez neste projeto que o mesmo erro aparece:** medir uma coisa
> **vizinha** da que se afirma. Antes foi o `page.request` que herdava o
> User-Agent e "provava" que o fator era o IP; depois foi o guarda de chegada da
> Tokio, que procurava um link que a **porta** também tinha.
>
> A pergunta que teria pego as três:
> **"a coisa que eu medi é a mesma sobre a qual eu vou afirmar?"**

A escolha continua certa (a Yelum saiu numa tarde), mas pelo motivo certo:
**a API é limpa** — não porque não tivesse trava.

---

## REGRESSÃO DAS QUATRO SEGURADORAS — 12/08/2026

📊 Sete jobs pela **fila de produção**, nas duas corretoras, todos `done`:

| Corretora | Seguradora | Inadimplentes | Boletos | Retidos |
|---|---|---:|---:|---:|
| Resulta | Allianz | 5 | **5** | 0 |
| AutoFleet | Allianz | 5 | **5** | 0 |
| Resulta | HDI | 1 | **1** | 0 |
| AutoFleet | HDI | 3 | **3** | 0 |
| Resulta | Tokio | 2 | **2** | 0 |
| AutoFleet | Tokio | 5 | **3** | 2 |
| Resulta | Yelum | 1 | **1** | 0 |
| | **total** | **22** | **20** | **2** |

📊 E a conferência que fecha: **20 de 20 arquivos existem no bucket
`portal-evidence`** e **20 de 20 começam com `%PDF`** — medido baixando os 8
primeiros bytes de cada um, não confiando no que o código disse que fez.

Os 2 retidos são os dois casos de regra, e cada um chegou com o motivo escrito:
o DÉBITO com `repique = S` e a parcela vencida há 26 dias para a qual a Tokio
não emite mais 2ª via.

### 🔴 O que AINDA falta para o ciclo completo

A **colheita** está pronta de ponta a ponta. O **envio** não foi exercitado, e
depende de duas coisas que não são código:

| # | O que falta | De quem | Custa se esquecer |
|---|---|:--:|---|
| P-116 | `human_support_destinations` só tem **AMANDUS**. Resulta e AutoFleet não têm grupo humano cadastrado | 🧑 Founder | os itens retidos (débito, sem 2ª via, sem telefone) **não têm para onde ir** — o aviso é montado e descartado |
| P-117 | **Nenhuma rotina de cobrança cadastrada** para Resulta nem AutoFleet | 🧑 Founder | nada roda sozinho; hoje as varreduras são enfileiradas à mão |
| P-118 | O **envio real de WhatsApp** nunca foi testado ponta a ponta | 🧑 Founder avisar antes | é a única peça do caminho que ainda não tem uma medição própria |

> **Sejamos exatos:** as quatro seguradoras entregam boleto no bucket, com o
> documento do segurado. O que ainda não aconteceu **nem uma vez** é o sistema
> mandar a mensagem para um cliente de verdade — e o Founder pediu para ser
> avisado antes que isso aconteça.

---

## MAPFRE — fase 1, e o risco cross-tenant que deixou de ser hipótese

📊 12/08/2026. Credenciais das duas corretoras gravadas, URL corrigida para
`negocios.mapfre.com.br/acesso`, porta pública medida.

### 🔴 P-119 — o mesmo login enxerga DUAS corretoras

📊 Depois do login, o modal `Selecione o código interno` lista
**RESULTA** e **AUTO FLEET** na mesma caixa, para o mesmo usuário.

> Se a varredura da Resulta selecionar a AutoFleet, os inadimplentes de uma
> entram no `company_id` da outra. É **dado atravessando tenant** — CLAUDE.md §7.

**Resolvido por desenho, não por sorte:** `portal_accounts.account_label` guarda
o nome exato da corretora que aquele login deve selecionar; a journey seleciona
pelo rótulo, **relê a tela para conferir**, e **para** (`needs_human`) se não
conferir. Nunca varre "o que estiver selecionado".

Isto materializa a **P-108**, anotada como hipótese desde a Tokio. Lá era "uma
corretora pode ter mais de um código"; aqui são **duas empresas** atrás do mesmo
usuário — pior, e real.

- **Custa se esquecer:** um incidente de vazamento entre clientes, que é o único
  tipo de defeito deste sistema que não dá para consertar depois.

### P-120 — a carteira MAPFRE está sem inadimplente nas duas corretoras

📊 Status `Vencida`, período padrão: `Não encontrado` nas duas. O card
`Parcelas Inadimplentes` marca `0`.

**Não bloqueia.** Zero inadimplente é um estado, não uma propriedade do portal.
📊 Na Tokio e na Yelum o boleto de parcela **A vencer** sai pelo mesmo caminho da
vencida — então dá para provar a cadeia inteira com `Status = Todos`, e o que
fica ❓ é só a coluna de juros/multa da linha vencida.

- **Custa se esquecer:** nada hoje; no dia em que aparecer o primeiro
  inadimplente, o último palmo se valida sozinho.

### P-121 — o período padrão da MAPFRE é de QUINZE DIAS

📊 `28/07/2026-12/08/2026`. É a janela mais curta das cinco seguradoras
(HDI 30 por bloco, Yelum ~90). ❓ O alcance máximo não foi medido.

- **Custa se esquecer:** dívida de dois meses não aparece — e sem uma testemunha
  independente ninguém saberia. Medir o alcance é pré-requisito do gate.

---

## P-122 (bis) · ~~`ESPELHO_SYNC_ENABLED` precisa ser ligado~~ — **FECHADA em 15/08/2026: já está ligado**

> ⚠️ **Este número está duplicado.** Existe outra P-122 acima (o teto de 1.000
> linhas do PostgREST). Ver P-161 — são 17 números repetidos no arquivo.

📊 **Medido em 15/08/2026 00:44 UTC**, lendo `/health` do serviço em produção
`autobrokers-intelligence-os-autobrokers-smith-api.golhpm.easypanel.host`:

```
espelho_sync_ligado : true
sync_ciclo          : 161 ciclos rodados
sync_linhas_lidas   : 19.217
sync_mensagens_novas: 1.910
```

O Founder ligou a variável e a pendência não foi fechada. **Fechar o documento
faz parte de executar** — enquanto ela ficou aberta, ela mentia sobre o estado
do produto, e eu passei uma hora investigando um sync "desligado" que estava
trabalhando havia horas. Documento desatualizado custa tempo de gente.

O que a pendência dizia continua verdade e vira registro: o recovery nasce
desligado de propósito, e a ponte AO VIVO nunca dependeu dele.

---

## P-161 · 🟡 Dezessete números de pendência estão duplicados

**Aberta em:** 15/08/2026 · **Dono:** 🤖 execução, quando houver folga

📊 `grep -oE "^## P-[0-9]+" PENDENCIAS.md | sort | uniq -d` devolve **17**:
P-91 · P-92 · P-93 · P-98 · P-99 · P-100 · P-101 · P-102 · P-103 · P-104 ·
P-122 · P-123 · P-124 · P-125 · P-126 · P-127 · P-129.

Cada um desses números aponta para **duas pendências diferentes**. "Ver P-124"
não identifica nada — e eu já citei P-124 e P-126 em relatório para o Founder
achando que eram únicas.

**O que destrava:** renumerar as segundas ocorrências para a faixa livre (P-162
em diante) e varrer o repositório atrás de referências às antigas. Não fiz agora
porque renumerar sem conferir quem aponta para elas troca uma ambiguidade por
uma referência quebrada — que é pior, porque não avisa.

**O que custa esquecer:** a lista de pendências é o lugar onde o que não coube
fica guardado. Um índice que não identifica o item começa a ser ignorado, e aí
ele para de guardar qualquer coisa.

---

## P-122 (original) · 🔴 `ESPELHO_SYNC_ENABLED` precisa ser ligado depois do canario

**Aberta em:** 13/08/2026 · **Dono:** 🧑 Founder (uma variavel no EasyPanel)

O recovery periodico do Espelho **nasce desligado** (commit `d9d17bb`). Foi
decisao de desenho: o primeiro boot depois do Upgrade para Pro e o instante mais
perigoso do plano — dezenas de componentes em 402 voltam ao mesmo tempo — e um
sync que sobe trabalhando nesse minuto e exatamente o que nao pode acontecer.

**Enquanto estiver OFF:** a ponte AO VIVO funciona inteira. Mensagem nova
aparece no chat normalmente. O que nao roda e a **rede de seguranca** — a
recuperacao do que a ponte perdeu durante um deploy ou uma reconexao.

**O que destrava:** `ESPELHO_SYNC_ENABLED=true` no servico `autobrokers-smith-api`,
depois do canario one-shot medido nas tres corretoras.

**O que custa esquecer:** mensagem perdida por um deploy nao seria recuperada
automaticamente. Ela continua intacta em `attendance_transcripts` e volta com um
one-shot — mas ninguem seria avisado de que faltou.

---

## P-123 · ~~A recuperacao da janela da pane~~ — **FECHADA em 13/08/2026 20:05 UTC: nao ha o que recuperar**

**Aberta e fechada no mesmo dia.** Foi aberta por deducao; a medicao a desmontou.

📊 Medido depois do deploy, antes do Upgrade:

```
transcripts elegiveis na janela de 7 dias ...... 3.426
destes, FALTANDO no chat ....................... 0
conversas afetadas ............................. 0
```

O Espelho ja tinha alcancado tudo antes da restricao. **Nao ha backfill a fazer.**

E a razao pela qual nao existe "janela da pane" no acervo e mais simples do que
eu supus: 📊 o ultimo transcript capturado e de **12/08 21:12 UTC — 22h50 antes**
desta medicao. A captura escreve via PostgREST, e PostgREST estava em 402: o
Observador nao capturou NADA durante a restricao. Nao ha material esperando no
acervo porque ele nunca chegou la.

**O que isso muda no plano:** o passo "one-shot de recuperacao por corretora"
sai da sequencia pos-Upgrade. Ele existiria para copiar acervo -> chat, e nao ha
diferenca entre os dois.

**O que assume o lugar dele:** quando o Supabase voltar e o Observador
reconectar, o WhatsApp deve reentregar por HISTORY_SYNC as ~23h que nao foram
capturadas. Elas entram pela ponte AO VIVO (que nunca foi desligada), com
`created_at` de agora — depois do cursor. Custo por mensagem depois da Alavanca
A: 2 leituras pequenas + 1 insert. Mesmo um HISTORY_SYNC do tamanho do da
Amandus (13.200 mensagens) fica na casa de poucos MB, contra os 7 GB do desenho
antigo.

**O que observar:** o contador `agora` do `/health` na primeira hora. Se
`mensagem_nova` subir muito, e o HISTORY_SYNC entrando — esperado. Se `erro:*`
subir, ai sim ha algo a investigar.

<!-- texto original preservado abaixo, append-only -->

### Registro original (13/08, antes da medicao)


**Aberta em:** 13/08/2026 · **Dono:** 🤖 execucao, depois do Upgrade

O cursor foi semeado em `now()` (13/08 ~18:30 UTC) de proposito: partir do
comeco varreria as 105.275 linhas do acervo — 26x o ciclo que causou o
incidente, no minuto seguinte ao Founder pagar pelo Pro.

Consequencia: as mensagens que chegaram **durante a restricao 402** nao entram
pelo cursor. Elas estao inteiras em `attendance_transcripts`.

**O que destrava:** depois do gate 402, chamar o endpoint que ja existe, uma
corretora por vez, medindo entre uma e outra:

```
POST /api/whatsapp-channel/espelho/trazer-conversas?company_id=<id>&dias=3&limite=3000
Header: X-AutoBrokers-Internal-Key
```

📊 Volume esperado (medido em 13/08): a maior corretora tem 59.168 transcripts
no total, mas so **4.009 na janela de 7 dias**. `dias=3` cobre a pane com folga.

**O que custa esquecer:** as conversas dos dias da pane nao apareceriam na mesa
de trabalho — visiveis no acervo e no `/admin/espelho`, invisiveis para a
atendente.

---

## P-124 · 🟠 SEC-05 guarda uma tela que mudou de casa — e por isso nao guarda nada

**Aberta em:** 13/08/2026 · **Dono:** 🤖 execucao, bloco proprio

📊 `broker_outcome_regression_pack.py` (caso SEC-05) procura a tela de conversas
em `app/dashboard/conversas/page.tsx` e `app/admin/conversations/page.tsx`. A
primeira **nao existe** e a segunda e um redirecionamento (pulado de proposito).
Resultado: `tela de conversas nao encontrada em nenhum dos caminhos` — **gate
vermelho**, e o guarda de seguranca sem alvo.

A tela real e `app/dashboard/atendimentos/conversas/page.tsx` (SPEC-043/064).

**Nao ha exposicao:** conferido em 13/08 — a tela real nao tem `supabase.storage`
nem `createClient`, e nao renderiza midia. O que falta e o guarda saber onde ela
mora. Ele tambem exige `resolveMediaUrl`, que aquela tela nao usa porque nao
mostra midia — logo o caso precisa ser **reescrito**, nao so reapontado.

**Falha pre-existente:** o P0 do Egress nao tocou um unico arquivo em `app/`
(`git status --short -- app/` = vazio nos dois commits).

**O que custa esquecer:** o gate fica vermelho por um motivo que nao e o que ele
anuncia, e a proxima regressao de verdade se esconde atras deste vermelho
cronico — que e como um gate morre.

---

## P-125 · 🔴 O código do P0 está na `main` e NÃO está no ar — falta clicar Implantar

**Aberta em:** 13/08/2026 · **Dono:** 🧑 Founder (ação física no EasyPanel)

📊 `git push origin HEAD:main` às 16:18 UTC, quatro commits (`51b5c0f`,
`d9d17bb`, `05fb3ae`, `3f9e0d5`). **Vinte e um minutos depois**, o contêiner
ainda servia o código antigo.

**Prova:** o commit `3f9e0d5` acrescenta a chave `espelho_sync_ligado` ao
`/health`. Ela **não aparece** na resposta de produção. `git_commit` vem
`nao-injetado`, então o número do commit não serve para conferir — a chave nova
serve.

**Conclusão: não há auto-deploy.** Push na `main` é condição necessária e não
suficiente. É preciso clicar **Implantar** em `autobrokers-smith-api` (e no
`-worker`, que compartilha o mesmo código).

### 🔴 Por que a ORDEM importa mais do que parece

Se o Upgrade para Pro acontecer **antes** do Implantar, o código antigo volta a
funcionar com cota nova — e o sync retoma saturado, relendo 4.008 linhas por
ciclo com o laço a ~50 min por volta. **O incidente recomeça no minuto em que a
cota é restaurada**, e desta vez custando dinheiro.

```
1. Implantar  (api + worker)
2. conferir   /health → codigo.espelho_sync_ligado == false
3. só então   Upgrade to Pro
```

**O que custa esquecer:** repetir o incidente de 05–13/08 com plano pago.

---

## P-126 · 🔴 A Resulta nao observa WhatsApp ha 15 dias — e nao foi a pane

**Aberta em:** 13/08/2026 · **Dono:** 🧑 Founder (parear de novo — QR/passkey)

📊 Medido logo apos o Upgrade, com o Supabase ja respondendo 200:

| corretora | `channel_status` | ultima captura | total no acervo |
|---|---|---|---|
| AutoFleet | `connected` | **13/08 20:40** (agora) | 46.016 |
| AMANDUS SEGUROS | `connected` | **13/08 20:33** (agora) | 102 |
| **Resulta Seguros** | **`disconnected`** | **29/07 18:27** | 59.168 |

**Nao foi causado pelo incidente de Egress.** A Resulta parou em **29/07**; o
Egress comecou a subir em **07/08** e a restricao 402 chegou em **12/08**. Sao
nove dias de diferenca — a Resulta ja estava muda antes.

📊 `capturou_7d = 0` para a Resulta, contra 3.887 da AutoFleet no mesmo periodo.

O heartbeat do canal (SPEC-063 Bloco V) esta funcionando: `last_seen_at` de tres
minutos atras com `channel_status = disconnected` e exatamente o vigia
**desmentindo** a tela, que e para o que ele existe.

**O que destrava:** repareamento do WhatsApp da Resulta (QR ou passkey). E acao
fisica — ninguem pareia um WhatsApp por API.

**O que custa esquecer:** a Resulta e uma das corretoras do canario e uma das
duas contas da MAPFRE. Ha quinze dias nao ha conversa dela entrando na mesa de
trabalho, e o `/admin/espelho` dela esta parado em 29/07. Qualquer medicao de
atendimento que a inclua esta medindo silencio.

---

## P-127 · 🟠 Duas views com SECURITY DEFINER — o Advisor marca CRITICAL

**Aberta em:** 13/08/2026 · **Dono:** 🤖 execucao, bloco proprio

📊 O Advisor do Supabase, depois do Upgrade, aponta 2 issues CRITICAL:

```
public.vw_destinos_de_suporte_em_conflito
public.vw_agentes_mudos
```

As duas sao views comuns (`relkind='v'`) de dono `postgres` e **sem**
`security_invoker=true`. Sem essa opcao, a view executa com os privilegios de
quem a CRIOU, nao de quem a CONSULTA — as policies de RLS do consumidor deixam
de valer.

**Nao e deste P0** e nao foi introduzida por ele: as duas views sao anteriores.
Nao tocadas nesta intervencao.

**O que destrava:** `ALTER VIEW ... SET (security_invoker = true)` — mas so
depois de conferir quem consulta cada uma e se alguma depende do comportamento
atual. Uma view de "agentes mudos" que passe a respeitar RLS pode devolver menos
linhas para o admin, e isso precisa ser verificado, nao presumido.

**O que custa esquecer:** e o unico CRITICAL aberto no Advisor. Cross-tenant por
view e o tipo de furo que nao aparece em teste de aplicacao (CLAUDE.md §7).

---

## P-128 · 🔴 A ANÁLISE QUE O FOUNDER PEDIU: os acionamentos com as seguradoras

**Aberta em:** 13/08/2026 · **Dono:** 🤖 execução · **Prioridade: alta, sessão própria**

Pedido do Founder, palavras dele: *"quero uma análise muito detalhada sobre o
que foi conversado com as seguradoras — acionamento na Allianz, na Porto, na
HDI... me diga se tivemos aumento dos mapas, se tivemos análise dos cliques, dos
cliques nos menus, nos apps dentro do WhatsApp da HDI, Yelum, Porto. Preciso
saber se a nossa inteligência entende tudo e se os nossos atendentes vão
conseguir fazer os acionamentos, se eles têm as informações corretas,
completas."*

### O que a análise tem de responder

1. **O que foi realmente conversado** com cada seguradora nos acionamentos
   reais — não o que o playbook diz, o que aconteceu.
2. **Os mapas cresceram?** `ura_maps` por seguradora, antes × depois. Quantas
   rotas novas, quantas mudaram, quantas morreram.
3. **Os cliques foram analisados?** Menus, botões e os *apps dentro do WhatsApp*
   (HDI, Yelum, Porto) — o formulário nativo resolvido em 03/08 é o precedente:
   ali a resposta veio de MEDIR, não de ler.
4. **A inteligência entende?** Uma coisa é ter o mapa; outra é o Atlas saber
   escolher a rota certa na hora.
5. **O atendente consegue fechar o acionamento sozinho?** Ele tem a informação
   correta e COMPLETA — placa, apólice, endereço, o que a seguradora pede em
   cada passo?

### Por que é a peça que falta

O atendimento ponta a ponta morre no acionamento. Tudo antes (captura, espelho,
chat, RAG) serve para chegar até aí. Se o atendente trava no menu da HDI, o
resto não importa.

**O que destrava:** sessão dedicada, com medição em `ura_maps`,
`attendance_transcripts` das conversas com seguradora (`insurer_key` não nulo),
`route_drift` e os `playbook_overlays`.

**O que custa esquecer:** ir a produção com o atendimento cego no último metro.

---

## P-129 · Medir o custo por sessão do destilador (teto 0 → 5, uma janela só)

**Aberta em:** 13/08/2026 · **Dono:** 🤖 execução, quando o Founder pedir

📊 `attendance_sessions`: **11.347 fechadas, ZERO destiladas**, atrás de
`DESTILADOR_TETO_POR_RODADA=0`.

O objetivo **não** é destilar por API — a destilação de verdade será feita pelo
Claude Code no plano Max, com subagentes e Opus 5, sem custo marginal. O objetivo
é **saber o número**: subir o teto para `5`, deixar UMA janela da madrugada
rodar, medir o custo real por sessão, e voltar para `0`.

Serve para responder "quanto custaria se um dia quiséssemos" com medição, e não
com estimativa — e para dimensionar a SPEC-062 (billing) com dado real.

**O que custa esquecer:** decidir preço e plano em cima de número inventado.

---

# MAPFRE — a quinta seguradora, e o que ela deixou aberto

📊 13/08/2026. Journey escrita, 92 testes verdes, gate real com **2 de 2
boletos no bucket** e Allianz **10 de 10** como linha de controle.
Ver [`PORTAL-mapfre.md`](portais/PORTAL-mapfre.md).

## P-148 · 🔴 A credencial da Resulta na MAPFRE é inválida

**Aberta em:** 13/08/2026 · **Dono:** 🧑 Founder / Saionara

📊 Testei **uma vez** e parei: o portal respondeu **"Autenticação inválida!"**
com o CPF e a senha corretamente digitados na tela (conferido no dump antes de
submeter). Não repeti — tentativa falha em sequência trava conta, e conta
travada custa mais que a espera.

A credencial da **AutoFleet** (o CPF do Founder) funciona e foi ela que
exercitou o portal inteiro.

**O que destrava:** alguém entrar à mão em `negocios.mapfre.com.br/acesso` com
o CPF da Resulta e dizer se a senha ainda vale ou se o usuário está bloqueado /
expirado. Depois é só regravar em Conectores > Portais — **nenhuma linha de
código muda**.

**O que custa esquecer:** a Resulta fica sem cobrança na MAPFRE, em silêncio —
a varredura dela termina em `needs_human` com o motivo escrito, mas ninguém lê
`needs_human` se não estiver esperando.

---

## P-149 · 🔴 O deploy do portal-worker com a journey da MAPFRE

**Aberta em:** 13/08/2026 · **Dono:** 🧑 Founder

O gate foi exercitado **localmente**, com as credenciais reais, o portal real e
o bucket real. Mas a imagem que roda no EasyPanel ainda não tem
`mapfre_corretor.py`: enquanto não for implantada, um job MAPFRE na fila termina
com *"journey desconhecida"*.

📊 E push na `main` **não** dispara build (P-125): é preciso clicar **Implantar**.

**O que destrava:** merge desta branch na `main` + Implantar no serviço
`portal-worker`.

**O que custa esquecer:** achar que a MAPFRE está no ar porque os testes estão
verdes — exatamente o defeito que a CLAUDE.md §9.1 registra.

---

## P-150 · 🟡 O catálogo de páginas da MAPFRE não foi mapeado

**Aberta em:** 13/08/2026 · **Dono:** 🤖 execução, na SPEC de Renovação

📊 `GET /api/1.0.0/config/page?path=…` devolve **HTTP 504** com os dois tokens
quando chamado por `fetch` de dentro da página, embora o app o consuma
normalmente. É o equivalente MAPFRE dos 338 destinos da Tokio — traz `url`,
`name` e `codigo_permiso` de cada tela.

**O que custa esquecer:** a Renovação começa às cegas e gasta uma visita de
descoberta que já poderia estar paga.

---

## P-151 · 🟡 A linha vencida com juros/multa não foi exercitada

**Aberta em:** 13/08/2026 · **Dono:** 🤖 execução, quando houver caso

📊 A lista traz `receiptTotFinalAmn: 294.35` e o PDF emitido mostra
**R$ 301,28**. São coisas diferentes — a parcela e o documento com encargos — e
a journey **não** força igualdade nem inventa juros. Mas nenhum caso com a
coluna de encargos visível na lista foi lido ainda.

**O que custa esquecer:** nada hoje; no dia em que a atendente comparar os dois
números, precisamos saber explicar qual é qual.

---

## P-152 · 🟡 A numeração das pendências colidiu — 21 números repetidos

**Aberta em:** 13/08/2026 · **Dono:** 🤖 execução, em sessão própria

📊 Hoje aparecem **duas ou três vezes** como título de seção:
`P-22 · P-91..P-105 · P-119..P-129` — 21 números ao todo. Duas sessões
trabalhando em paralelo numeraram por cima uma da outra.

Já é ambíguo dizer *"resolvi a P-119"*: existem duas.

**Por que não renumerei agora:** a correção é mecânica mas atravessa o arquivo
inteiro, e este documento é como o Founder conversa com a execução. Renumerar no
meio de uma SPEC em curso troca as referências que ele acabou de usar. As
entradas novas nasceram em **P-148+**, únicas.

**O que destrava:** uma passada dedicada, com o Founder ciente de que os
números antigos mudam — e um guarda que faça o número duplicado falhar no CI.

**O que custa esquecer:** a lista deixa de ser endereçável, e "resolvido" passa
a apontar para a coisa errada.

---

## P-153 · 🟡 O que falta DEPOIS da Zurich, para o Auxiliar de Cobrança fechar

**Aberta em:** 13/08/2026 · **Dono:** 🧑 Founder + 🤖 execução, na ordem abaixo

Registrada a pedido do Founder, para não depender de memória de sessão. A ordem
é dele: **primeiro fechar as seguradoras, depois o envio.**

Quando as seis seguradoras estiverem colhendo, esta é a fila:

| # | O que | De quem |
|---|---|:--:|
| 1 | **InfoCap** — exercitar a busca do WhatsApp pelo CPF/CNPJ. 📊 Nunca foi exercitada: nenhuma das seis seguradoras entrega telefone utilizável, e é a InfoCap que fecha essa ponta | 🤖 |
| 2 | **Qual WhatsApp envia** — decidir e ligar o número/instância que fala com o segurado | 🧑 |
| 3 | **Grupo de suporte humano** para Resulta e AutoFleet (`human_support_destinations`) — hoje só a AMANDUS tem. Sem ele, item retido é montado e descartado | 🧑 |
| 4 | **As regras de envio** — o Founder tem uma lista de ajustes finos ("várias coisinhas, para não deixar ponta solta"). **Precisam ser levantadas e escritas antes do primeiro envio** | 🧑 dita · 🤖 escreve |
| 5 | **Rotina de cobrança** para as duas corretoras, com as seis seguradoras — hoje há **zero rotinas ativas** | 🤖 · horário é decisão do Founder |
| 6 | **O primeiro envio real**, com o WhatsApp da AMANDUS, um caso só, avisando o Founder antes | 🧑 autoriza · 🤖 executa |
| 7 | **Rotação de chaves** — as credenciais compartilhadas na execução (incluindo `PORTAL_VAULT_KEY` e as chaves de serviço) precisam ser trocadas antes de haver cliente real | 🧑 |

**O que custa esquecer:** o item 4 é o mais perigoso, porque é o único que só existe
na cabeça do Founder. Se o primeiro envio acontecer antes de essas regras estarem
escritas, elas viram correção depois de a mensagem ter saído — e mensagem enviada
não volta.

---

# ZURICH — a sexta seguradora, e o palmo que falta

📊 13/08/2026. Journey escrita, **111 testes verdes**, gate com o inadimplente
identificado corretamente nas duas corretoras e Allianz 10/10 como linha de
controle. Ver [`PORTAL-zurich.md`](portais/PORTAL-zurich.md).

## P-155 · 🟡 O parser de valor da Yelum e da MAPFRE zera em "1,287,99"

**Aberta em:** 13/08/2026 · **Dono:** 🤖 execução, quando houver folga

📊 `_valor("1,287,99")` devolve **None** nos dois. A Zurich produz esse formato
(vírgula de milhar E de decimal na mesma string) e ganhou parser próprio, que é
um **superconjunto** do antigo.

📊 **Latente, não ativo:** a MAPFRE manda `294.35` e a Yelum `1.672,62` —
nenhuma das duas produz o formato hoje.

**O que destrava:** trocar os dois pelo `valor_brasileiro` da Zurich e rodar as
suítes das duas. Não foi feito agora para não mexer em journey em produção sem
gate próprio.

**O que custa esquecer:** se algum dia um daqueles portais mandar milhar com
vírgula, a cobrança sai **sem valor** — e `None` não estoura.

---

## P-156 · 🟡 A carteira da Resulta na Zurich não pôde ser estabelecida

**Aberta em:** 13/08/2026 · **Dono:** 🤖 nova leitura

📊 A credencial **entra** (`RESULTA CORRETORA DE SEGUROS LTDA` na tela), mas a
lista devolveu **200 com zero linhas, duas vezes seguidas**. O guarda do §3.5 do
runbook fez o certo: terminou em `needs_human` em vez de afirmar carteira em dia.

❓ Não sei se a Resulta tem mesmo zero parcelas na Zurich (é a corretora de
outros ramos) ou se foi o aquecimento do portal.

**O que custa esquecer:** se for carteira genuinamente vazia, o guarda vai
disparar em toda varredura da Resulta — e um alerta que sempre toca é um alerta
que ninguém lê.

---

## P-157 · 🟡 O teto da janela da Zurich é de DIAS ou de LINHAS?

**Aberta em:** 13/08/2026 · **Dono:** 🤖 quando houver folga

📊 90 dias / 53 linhas passaram; 120 dias deram 404. Não dá para separar as duas
causas com uma medição só. A journey contorna estreitando a janela a cada 404.

📊 E o achado que importa mais que o teto: **pedir demais derruba a sessão**.
Depois do pedido de 365 dias, nem a janela de 30 — que funcionava no início da
mesma sessão — voltou a responder. Só a linha de controle no fim revelou isso.

---

## P-158 · 🟡 Acompanhamento: o segurado que não pagou continua na lista

**Aberta em:** 14/08/2026 · **Dono:** 🧑 Founder decide · 🤖 executa · **3ª etapa**

Registrada a pedido do Founder. É a etapa DEPOIS do envio, e não se resolve
agora.

O que a Saionara (suporte da corretora) respondeu quando perguntada como faz:

> *"Eu envio o boleto e fico acompanhando se pagou. Se não pagou eu reenvio e
> sempre lembro a data limite, para não cancelar por falta de pagamento."*

Isso já dá três regras: **reenvia** · **acompanha** · **sempre cita a data
limite**. O que falta decidir, e que hoje não existe em lugar nenhum do sistema:

| # | A decisão | Por que importa |
|---|---|---|
| 1 | De quantos em quantos dias reenvia | a Saionara faz por sensibilidade; o robô precisa de número |
| 2 | Quantas vezes, antes de virar tarefa humana | senão vira perseguição |
| 3 | Horário e dias em que pode falar | comercial? sábado? |
| 4 | Se o segurado responder, o robô para? | quase certamente sim |
| 5 | Quem nunca recebe automático | cliente que só a atendente fala |
| 6 | Teto por dia por corretora | para não parecer disparo em massa |
| 7 | O texto, e o que muda quando o cancelamento está perto | é o que a Saionara faz à mão hoje |

**O que falta no sistema:** não há nada que saiba *"já falei com esta pessoa,
sobre esta parcela, há N dias, pela Kª vez"*. O `billing_sent_log` existe para
retomada, não para cadência.

> 🔴 **As regras valem para TODAS as seguradoras, não por portal.** A colheita é
> específica de cada uma; a conversa com o segurado é do Auxiliar, e é uma só.

**O que custa esquecer:** o primeiro envio real acontece sem regra escrita, e a
correção vem depois de a mensagem ter saído. Mensagem enviada não volta.

---

## P-159 · 🟡 O sync do espelho rasteja: perde ~90% de cada passada num erro de rede

**Aberta em:** 14/08/2026 · **Corrigida a leitura em:** 15/08/2026 00:46 · **Dono:** 🤖 execução

> 🔴 **A primeira versão desta pendência estava ERRADA em três pontos.** Fica
> registrada a correção, e não o texto original, porque quem ler depois precisa
> do que é verdade — mas o erro fica dito, porque ele ensina o método.

| Eu escrevi | O que a medição mostrou |
|---|---|
| "o cursor parou" | **anda** — 1.121 linhas em 25 min |
| "não consigo ler `/health`" | a URL **está** no repo (`RUNBOOKS.md:135`); usei o nome curto do serviço |
| "não sei se o sync está ligado" | `espelho_sync_ligado: true` |

📊 O erro de leitura tem causa e ela é banal: medi o cursor **duas vezes com 8
minutos de intervalo** e vi o mesmo valor. Concluí "parado" de duas amostras
próximas demais para o fenômeno. Uma terceira, 25 minutos depois, derrubou a
conclusão. **Duas medições não são uma série.**

### O que está medido (15/08/2026 00:46 UTC)

```
espelho_sync_ligado : true
janela agora        : sync_ciclo 1 · 499 lidas · 0 novas · erro:RemoteProtocolError 13
desde sempre        : 161 ciclos · 19.217 lidas · 1.910 novas
Resulta             : cursor andou 1.121 linhas em 25 min (~45/min)
                      28.180 ainda atrás → drena em ~10 h
```

> ⚠️ `erro:ImportError: 4510` e `erro:APIError: 23854` são contadores
> **acumulados**, não da janela atual. O ImportError é o de 06/08, já corrigido.
> Quase caí nele como se fosse defeito de hoje.

### O defeito que sobra — real, e não é o que eu disse

Cada passada lê **500** linhas e avança **~45**. As outras 455 são relidas na
passada seguinte. A causa provável — 💭 **inferida**, não medida — é o `break` de
`espelho_chat.py:1065`: um `RemoteProtocolError` numa linha derruba **a passada
inteira**, não só aquela linha. O erro é transitório (conexão que o Supabase
fechou), mas o preço é o resto do lote.

A recusa em ultrapassar a linha com erro está **certa** — é o que impede perder
mensagem. O que está errado é ela derrubar as 455 seguintes junto.

**O que destrava:** tentar a linha de novo (2 ou 3 vezes) antes de desistir da
passada. Não mexer na regra de não ultrapassar.

**O que custa esquecer:** não é perda de dado e não é o Egress de agosto — relê
500, não 100 mil. É **lentidão**: uma descarga nova de acervo demora ~10 h para
chegar à mesa, e o que chegar depois espera atrás dela.

---

## P-160 · 🟡 A mesa da AutoFleet pode ter buraco anterior ao cursor

**Aberta em:** 14/08/2026 · **Dono:** 🧑 Founder libera · 🤖 executa

📊 AutoFleet, janela de 30 dias: **9.602** linhas no acervo, das quais **8.168**
são de cliente e têm texto, em **330** contrapartes. Na mesa: **6.287** mensagens
em **190** conversas. A primeira espelhada é de **06/08** — e o cursor nasceu
`now()` na migration de 13/08, por decisão deliberada.

Então o que falta **não está atrás do cursor** (só 6 linhas estão): está **antes**
dele, no trecho que a recuperação inicial nunca varreu. A AutoFleet é a corretora
da Regina — a que assiste à demonstração.

⚠️ Os dois números não são diretamente comparáveis: 8.168 conta linhas do acervo
(a mesma mensagem pode aparecer duas vezes) e 6.287 conta mensagens já
deduplicadas na mesa. A lacuna é **direcional, não medida**.

**O que destrava:** autorização para rodar o mesmo one-shot que rodou na Resulta
(`espelho/trazer-conversas`), que é leitura do acervo e escrita na mesa — **não
toca no WhatsApp da AutoFleet** e não fere a R2. Não rodei sozinho porque muda o
que uma pessoa real vê na tela na segunda-feira, e essa é uma decisão sua.

**O que custa esquecer:** a Regina abre a mesa na demonstração e encontra
conversas começando no dia 06/08, sem o histórico que ela sabe que existe.

---

## P-162 · 🔴 CPF, CNPJ e placa de segurado gravados DENTRO dos mapas do Atlas

**Aberta em:** 15/08/2026 · **Dono:** 🧑 Founder autoriza · 🤖 executa · **P1 de segurança (CLAUDE.md §10(4))**

Achado por um subagente auditor no BLOCO 5, e confirmado por medição própria em
escala maior do que ele viu: **não é só a Allianz. São os 10 mapas ativos.**

📊 Medido em 15/08/2026 sobre `ura_maps` com `status IN ('active','observed')`:

| seguradora | arestas | CPF | CNPJ | placa | telefone |
|---|---:|---:|---:|---:|---:|
| allianz | 2.019 | 53 | 14 | 20 | 5 |
| porto | 1.028 | 36 | 6 | 5 | 12 |
| yelum | 952 | 17 | 9 | 42 | 18 |
| hdi | 724 | 8 | 2 | 17 | 7 |
| zurich | 272 | 3 | 0 | 11 | 8 |
| azul | 204 | 7 | 0 | 0 | 2 |
| bradesco | 135 | 2 | 0 | 9 | 0 |
| tokio | 70 | 9 | 3 | 0 | 0 |
| alfa | 76 | 5 | 0 | 0 | 0 |
| mapfre | 67 | 1 | 0 | 1 | 0 |
| **TOTAL** | **5.547** | **141** | **34** | **105** | **52** |

### A causa

O mapa guarda a navegação como `{nó de origem}|{o que foi digitado} -> {nó de destino}`.
Quando a URA pede o CPF, **o que foi digitado é o CPF** — e ele vira o rótulo da
aresta. Exemplo literal do mapa ativo da Allianz:

```
5b7ca670e1f1|111.111.111-11 -> 2bd9b17f842c
```

📊 Os **nós** já são mascarados (`{TELEFONE}`, `{PLACA}`, `{CAMINHO}`). **As
arestas não.** A sanitização foi escrita e aplicada num lado só.

### O tamanho real — medido, e menor do que eu suspeitei no meio da apuração

Eu cheguei a suspeitar que isso chegava a um LLM de terceiro, porque
`webhook.py:394` e `dispatch_watchdog.py:218` passam `ura_map=` para
`build_human_phase_messages`, cujo resultado vai para a OpenAI (`gpt-4o`).

**Fui até a fonte e estava errado.** `insurer_dispatch_service.py:1684` faz
`_ = ura_map  # ignorado de propósito`, com justificativa documentada acima da
linha. **O mapa não entra em prompt nenhum.**

Então o alcance é:

| onde | alcança |
|---|---|
| `admin_atlas.py:235` e `:295` | devolvem o `map` INTEIRO ao painel admin |
| `route_sentinel`, `operational_view` | leem para diff e rótulo, internos |
| LLM / RAG / Qdrant | **não** — verificado, não estava |

Não é vazamento para terceiro. **É dado pessoal de segurado real guardado num
artefato derivado, visível no painel, e replicado em toda versão do mapa** — e
`ura_maps` tem 238 versões `superseded`, o que multiplica o mesmo CPF.

### O que destrava

1. Mascarar na ORIGEM — o construtor (`atlas/weaver.py`), no mesmo ponto em que
   já mascara os nós. Sem isso, a limpeza volta a sujar na próxima passada.
2. Só depois, limpar o histórico. ⚠️ **T2 da SPEC-071: nunca editar mapa no
   lugar.** Gera versão nova; a `active` só cai quando aprovada.

**O que custa esquecer:** o CPF de um segurado da Resulta está num mapa GLOBAL
por seguradora, que a AutoFleet também lê. Não é vazamento entre corretoras
hoje porque ninguém renderiza a aresta na tela — mas a distância entre "está
guardado no lugar errado" e "apareceu na tela errada" é uma feature de UI.

---

## P-163 · 🟡 O backfill histórico da Resulta rodou duas vezes — 91,7% de linhas em duplicata

**Aberta em:** 15/08/2026 · **Dono:** 🤖 execução

📊 Medido em `observed_events`, `insurer_key='allianz'`:

```
Resulta   10.515 linhas ·  9.644 duplicadas · 91,7%
AutoFleet  2.537 linhas ·      0 duplicadas ·  0,0%   <- a linha de CONTROLE
```

**A AutoFleet limpa é o que dá direito à conclusão:** não é defeito do coletor
ao vivo, é o importador de histórico da Resulta.

E a dedup por `message_id` não pegou porque **o ID mudou de algoritmo entre as
duas rodadas** — mesmo telefone, mesmo epoch, sufixos diferentes:

```
hist-551140901444-1779992641-33f60f8a9215   (12 hex)
hist-551140901444-1779992641-9007086        (7 dígitos)
```

📊 Todos os 13.052 `message_id` são únicos. A duplicata é de LINHA, não de id.

**O efeito no Atlas:** as contagens de amostra dos nós estão infladas ~1,9× no
que veio da Resulta. **A topologia não é afetada** — aresta duplicada é a mesma
aresta —, mas os números de `samples` **não são citáveis** e a ordenação
relativa entre nós favorece o que a Resulta percorreu mais.

**O que custa esquecer:** alguém vai citar "esta tela foi vista 171 vezes" como
evidência de que uma rota é a principal. Metade disso não aconteceu.

---

## P-164 · 🔴 O mapa do Atlas perde justamente a opção que aciona o GUINCHO

**Aberta em:** 15/08/2026 · **Dono:** 🤖 execução · **destrava:** ler quem monta `options[]` a partir de `interactive`

Achado pelo auditor da Frente A. Verifiquei nó a nó: **procede, e o padrão é
sempre o mesmo — a opção perdida é a PRIMEIRA da lista.**

📊 Medido em `ura_maps` com `status='active'`, comparando o `text` do nó (que
mostra o menu como a URA o emitiu) contra o `options[]` do MESMO nó:

| nó | o texto do nó mostra | o `options[]` começa em |
|---|---|---|
| `zurich/a8087cb9567d` | `Assistência {VALOR}` | *Assistência a vidros* |
| `mapfre/e3bc3dfdca75` | `Assistência {VALOR}` | *Sinistro* |
| `tokio/b1b457af6ca6` | `Assistência {VALOR}` | *Informações de sinistro* |
| `yelum/f372a91db870` | `Botão 1: ASSISTENCIA 24H` | *ACOMPANHAR SINISTRO* (2 de 3) |

📊 Ocorrências observadas na URA real contra ocorrências no mapa:
`Assistência 24h` — **52 vezes emitida, 0 vezes no `options[]` desses nós.**

### Por que isto é o achado mais caro do BLOCO 5

**Um corredor que leia `options[1]` desse nó aperta "Assistência a vidros"
achando que apertou "Assistência 24h".** É o erro que só aparece com um segurado
parado na estrada esperando guincho.

E são quatro seguradoras com **um** defeito, não quatro achados: consertar o
pipeline conserta as quatro de uma vez.

### O que eu NÃO sei, e não vou fingir que sei

💭 A hipótese é que o mascaramento de PII transforma `24h` em `{VALOR}` e o
`options[]` descarta a linha que contém o marcador. `cartographer.py:639` chama
`parse_options(text)` sobre o texto **já mascarado**, o que torna a hipótese
plausível.

**Mas ela não fecha.** Dois contraexemplos derrubam a versão simples:
`tokio/"Guincho/Assist.24h"` e `zurich/"Acionar assistência 24h"` **sobreviveram**
no `options[]`. E o caso da Yelum não tem mascaramento nenhum no texto — são três
botões literais e o mapa gravou dois.

⚠️ Registro isto porque quase o publiquei como causa. O efeito está **medido**;
a causa está **inferida** e os contraexemplos são meus, não de outra pessoa.

**O que destrava:** ler o código que monta `options[]` para mensagem
`interactive` — `weaver.py:520` diz explicitamente que esse caminho *"não passa
por `parse_options`"*, então há um segundo construtor que eu não li. A diferença
entre os casos que sobrevivem e os que somem está lá, não no banco.

**O que custa esquecer:** o mapa parece completo. Ele tem o texto certo do menu,
tem o número certo de nós, e a única coisa errada é a linha que importa.

---

## P-165 · 🔴 Nome de corretora e de atendente dentro do mapa GLOBAL

**Aberta em:** 15/08/2026 · **Reescrita no mesmo dia** · **Dono:** 🤖 execução

> 🔴 **A primeira versão desta pendência fazia a PERGUNTA ERRADA.**
>
> Eu a abri como *"P1 cross-tenant: `ura_maps` não tem `company_id`, duas
> corretoras alimentam o mesmo mapa"* e pedi ao Founder decidir entre **mapa
> global** e **mapa por corretora**.
>
> **A agregação é o produto.** Founder, 15/08: *"não é mapa da Resulta ou da
> AutoFleet. É mapa AutoBrokers que usa inteligência de todas as corretoras que
> parearem os celulares para irem juntas completando o mapa."*
>
> Como eu errei: apliquei a regra de isolamento entre corretoras (CLAUDE.md §7)
> a um artefato que **não é dado de corretora** — é conhecimento sobre a URA de
> uma seguradora, que é a mesma para todo mundo. A regra estava certa; o objeto
> era outro. Parece rigor e não é: é rigor mirado no lugar errado.
>
> Doutrina inteira em [`O-ATLAS-E-UM-SO-E-E-DE-TODAS.md`](O-ATLAS-E-UM-SO-E-E-DE-TODAS.md).

### O defeito que SOBRA, e é real

Não é juntar. É **nome próprio dentro de um artefato que tem de ser neutro**.

📊 Medido: **14 nós** de mapas ativos carregam identidade de corretora ou
atendente, sem redação — porto 4 · yelum 4 · tokio 3 · hdi 2 · azul 1.

```
"*Saionara - Resulta*, por ser um item essencial, vou te transferir…"
"Olá RESULTA CORRETORA DE SEGUROS LTDA, Nos ajude a continuar resolvendo!"
"Olá CONDOMINIO DO CONJUNTO RESIDENCIAL RECANTO DOS PASSAROS…"
"Olá INDYANA COMERCIO DE VEICULOS LTDA…"
```

⚠️ E o redator é **inconsistente**, o que é a causa:
`"Maria Regina - Autofleet Seguros"` → `"Maria {NOME} - {CORRETORA}"` — **o
primeiro nome escapa** — enquanto `"Saionara - Resulta"` passa inteiro.

### Por que importa, e não é privacidade

O agente de atendimento é **global**. Quem personaliza é o dashboard, com dados
de configuração, em tempo de execução. Um nó que já traz "Resulta" escrito
dentro faz **o agente da próxima corretora se apresentar com o nome de outra
empresa** — e o mesmo vale para playbook, corredor e prompt.

**O que destrava:** consertar o redator na origem (`weaver`/`cartographer`), e
só depois limpar o histórico. ⚠️ T2 da SPEC-071: nunca editar mapa no lugar —
gera versão nova; a `active` só cai quando aprovada.

**O que custa esquecer:** não é o nome que vaza. É o agente errando de quem ele
é.


---

## P-166 · 🟡 Re-tecer os 4 mapas para a opção do guincho voltar ao histórico

**Aberta em:** 15/08/2026 · **Dono:** 🤖 execução, depois do deploy de `6f8316f`

O conserto do `options[]` (P-164) e o da redação (P-162, P-165) valem para o que
for tecido **de agora em diante**. O que já está gravado precisa de duas coisas
diferentes, e elas não são a mesma:

| o quê | quem faz | quando |
|---|---|---|
| tirar CPF e nome de corretora do mapa já gravado | `higienizar_e_promover` | ✅ **sozinho, de hora em hora** (`buffer_processor.py:214`) |
| **devolver** a opção "Assistência 24h" que sumiu | `weave_insurer` | ⚠️ **precisa de gatilho** |

⚠️ **A higiene NÃO devolve a opção.** Ela só remascara o que existe — e o que
existe é um `options[]` de 9 onde a URA emitiu 10. A décima só volta relendo
`observed_events`, que é o que `weave_insurer` faz.

**O que destrava:** `POST /api/admin/atlas/tecer` (`admin_atlas.py:104`) para
`zurich`, `mapfre`, `tokio` e `yelum` — ou a passada do `route_sentinel`.

⚠️ **T2 da SPEC-071:** re-tecer gera versão nova; a `active` só cai quando
aprovada. Não editar no lugar.

📊 **Como verificar que funcionou** — a query que hoje devolve 4 linhas e depois
deve devolver 0:

```sql
SELECT m.insurer_key, n.k,
       (SELECT string_agg(op->>'label', ' / ')
          FROM jsonb_array_elements(n.v->'options') op) AS opcoes
  FROM ura_maps m, jsonb_each(m.map->'nodes') n(k,v)
 WHERE m.status='active'
   AND n.v->>'text' ILIKE '%ssist%'
   AND NOT EXISTS (SELECT 1 FROM jsonb_array_elements(n.v->'options') o
                    WHERE o->>'label' ILIKE '%ssist%24%');
```

**O que custa esquecer:** o mapa continua parecendo completo — texto certo,
número de nós certo — e sem a linha que aciona o guincho. É o defeito que não
se anuncia.

---

## P-167 · 🔴 A higiene do mapa não alcança o `active` — e eu disse ao Founder que alcançava

**Aberta em:** 15/08/2026 · **Dono:** 🤖 execução

> 🔴 **Correção de uma afirmação minha.** Eu disse ao Founder: *"a higiene roda
> de hora em hora sozinha; dentro de 1h os 141 CPF saem dos mapas já gravados"*.
> **Medi depois e não saem.**

📊 Medido em 15/08 04:11 UTC, **depois** do deploy de `6f8316f`:

| status | mapas | CPF nas arestas |
|---|---:|---:|
| `active` | 10 | 141 |
| `retired` | 4 | 144 |
| `superseded` | **276** | **2.287** |
| **`observed`** | **0** | — |
| | | **2.572 no total** |

**A causa:** `higienizar_e_promover` remascara os mapas **`observed`** e promove
os que ficarem limpos. 📊 **Não existe nenhum mapa `observed`.** A função roda de
hora em hora, não encontra nada, e não toca no `active`.

⚠️ E o número que eu vinha citando — 141 — era só o `active`. **O total é
2.572**, e as 276 versões `superseded` não entram em higiene nenhuma, nem hoje
nem depois: nada no produto as relê.

### A cadeia que REALMENTE limpa, e o tempo dela

```
sentinela (1×/dia) re-tece  →  nasce mapa `observed`
higiene (1×/hora) remascara →  promove a `active`
```

Ou seja: **a limpeza depende do re-tecer**, não o contrário. O que eu descrevi
como "automático em 1h" é automático em **até 24h**, e só para o que for tecido
de novo.

**O que destrava:**
1. Confirmar que a sentinela rodou depois do deploy (📊 o mapa mais novo é de
   14/08 18:37 — anterior à correção).
2. Para o `superseded`: decidir se limpa ou se **apaga**. 2.287 CPF em 276
   versões que ninguém lê é passivo sem contrapartida — mas apagar histórico
   pede decisão do Founder (CLAUDE.md §13.4).

**O que custa esquecer:** eu já dei este assunto por resolvido uma vez, em voz
alta. Um problema de segurança fechado por suposição continua aberto, e ninguém
volta a olhar porque acha que foi feito.

---

## P-168 · 🔴 `INSURER_DISPATCH_LIVE=true` no ambiente contradiz a regra R1

> 🔴 **ATUALIZADA em 25/08/2026 pela SPEC-093, BLOCO E** — agora com DONO e com a medição que faltava.

📊 **O estado, lido no `/health` da `smith-api` em 25/08 20:32:**

```
acionamento_env_aberta        false      ← hoje fechado
freio_de_emergencia_armado    true       ← e é SÓ o freio que fecha
finalize_modo                 "test"
finalize_abre_de_verdade      []         ← nenhum corredor abre chamado
```

⚠️ **A armadilha continua:** o piloto começa **desarmando o freio**, e no instante em que ele sai, `INSURER_DISPATCH_LIVE` volta ao que o ambiente disser. Com `DISPATCH_FINALIZE_MODE=test` escrito, os dois juntos são o **meio aberto**: o segurado ouve *"estou acionando"* e ninguém vem.

🔴 **A decisão do Founder está registrada** em `FOUNDER-DECISIONS.md` como **D-093**: opção (A), `finalize` aberto, cancelamento por pessoa depois do fato. 📊 E a execução mediu a premissa dela: **12 cancelamentos após confirmação no acervo, mediana 34 min, 5 deles abaixo de 5 min.**

- **Destrava:** 🧑 Founder — (a) decidir se abre em TODOS os corredores ou só nos completos (`DISPATCH_FINALIZE_LIVE_PLAYBOOKS`), e (b) alinhar `INSURER_DISPATCH_LIVE` no EasyPanel com a decisão.
- **Custa se esquecer:** o freio de emergência é hoje a **única** coisa que separa o produto do meio aberto. Desarmá-lo sem alinhar o ambiente abre envio real E finalização de mentira no mesmo instante.
- ⚠️ **O prazo continua sem medição:** o acervo diz quando alguém cancelou, nunca quando ficou tarde demais. São perguntas diferentes.

**Aberta em:** 15/08/2026 · **Dono:** 🧑 Founder decide

📊 Lido no bloco de variáveis de `autobrokers-smith-api` / `smith-worker`:

```
INSURER_DISPATCH_LIVE=true
```

Em 14/08 eu fechei o **padrão** dessa variável no código (`2abe35b`), citando o
Founder: *"não pode ser enviado nada até eu liberar"*. Mas **padrão de código não
vence variável de ambiente** — e o ambiente diz `true`.

⚠️ Registro sem afirmar a consequência: **não medi** o que exatamente esse `true`
libera hoje, nem se algum caminho vivo chega a enviar. O que sei é que a intenção
escrita e o estado do ambiente **discordam**, e discordância entre os dois é
precisamente o tipo de coisa que ninguém descobre até sair uma mensagem.

**O que destrava:** decidir qual dos dois é a verdade. Se a regra vale, a
variável sai do EasyPanel. Se o envio já pode acontecer, o comentário no código
está vencido e vira mentira para o próximo leitor (CLAUDE.md §9.3).

**O que custa esquecer:** o freio que eu descrevi ao Founder como "fechado por
construção" não está fechado no ambiente onde ele importa.

---

## P-167 (atualização) · A limpeza dos CPF foi DESTRAVADA — falta a promoção

**15/08/2026 04:46 UTC.** Executei o re-tecer das **10 seguradoras** pelo
endpoint `/api/admin/atlas/weave`. Resultado medido:

| status | mapas | CPF | nomes de corretora |
|---|---:|---:|---:|
| **`observed`** (tecidos agora) | **10** | **0** | **0** |
| `active` (os antigos) | 10 | 141 | 12 |
| `retired` | 4 | 144 | 20 |
| `superseded` | 276 | 2.287 | 234 |

📊 **A correção funciona ponta a ponta em produção:** o tecido novo sai com zero
CPF, zero nomes, e com os placeholders no lugar (`{CPF}`, `{TELEFONE}`).

E a opção do guincho voltou:

| | antes | depois |
|---|---:|---:|
| zurich | 1 | **4** |
| tokio | 2 | **5** |
| mapfre | 0 | **1** |
| yelum | 0 | **1** |

**O que falta, e é automático:** `higienizar_e_promover` roda de hora em hora,
encontra os 10 `observed` limpos e os promove a `active`. Não há endpoint para
antecipar — e não inventei um, porque o job existe e funciona.

⚠️ **O que NÃO se resolve sozinho:** as **276 versões `superseded`** com 2.287
CPF. Nada no produto as relê e nada as limpa. São passivo puro. **Decisão do
Founder:** limpar (custa 276 reescritas de jsonb) ou apagar (§13.4 exige decisão
explícita — não apago histórico sem ela).

---

## P-169 · 🔐 Senhas circulando no WhatsApp — o mascarador não as vê

**Aberta em:** 15/08/2026 · **Dono:** 🧑 Founder decide · **P1**

📊 Três destiladores independentes acharam credenciais em texto claro dentro de
transcripts **já mascarados**:

| onde | o que é |
|---|---|
| `lote_021` `63d8e8cb` | senha de portal de seguradora |
| `lote_047` `3b3436b1` | pedido de senha de portal **entre colegas** |
| `lote_050` `63e92ce5` | **a segurada** enviando a senha do PDF do boleto no chat |

**A causa:** o mascarador conhece CPF, CNPJ, telefone, placa, e-mail, endereço e
valor — todos têm **forma reconhecível**. Senha não tem. `Youmba2013@@` e
`resulta123` não casam com padrão nenhum, então atravessam inteiras.

⚠️ **O alcance é o acervo todo.** `attendance_transcripts` tem 150.734 linhas
que passaram pelo mesmo mascarador, e **uma varredura por credencial nunca foi
feita**. Os três casos acima saíram de ~1.400 conversas destiladas — a taxa
sugere dezenas no acervo inteiro.

E o terceiro caso é de outra natureza: **é a segurada mandando a senha dela**,
não a equipe. Isso não se resolve com treinamento interno.

**O que destrava:** uma varredura por CONTEXTO, não por forma — procurar
`senha`, `login`, `acesso`, `credencial`, `usuário` a até ~40 caracteres de uma
sequência sem espaços. Nenhum destilador reproduziu as senhas; todos
registraram em `flags`, e isso é o comportamento certo.

**O que custa esquecer:** senha de portal de seguradora dá acesso à carteira
inteira de uma corretora. E ela está hoje num campo `text` de uma tabela que 
alimenta destilação, RAG e Atlas.

---

## P-170 · 🔴 As 24 melhores cartas morrem em silêncio no limite de 400 caracteres

**Aberta em:** 15/08/2026 · **Dono:** 🤖 execução · **destrava:** partir em duas, não encurtar

Achado pelo juiz das ondas 2 e 3, simulando o **pipeline real** de aplicação
(`curadoria_cartas.escolher_representantes`), não uma reimplementação.

📊 De 1.078 fatos da leva, **24 serão descartados por passar de 400 caracteres**
— e são justamente as melhores:

| o que se perde | onde |
|---|---|
| listas completas de documentos de sinistro | `L023 5e62bd66` · `L031 5f65897a` · `L025 e617d971` |
| checklist do guincho de veículo **pesado** (14 campos) | `L040 e3f5231f` · `L071 8ce62d8e` |
| bloco de abertura de para-brisa | `L055 0f365742` |

⚠️ **O modo de falha é o pior possível: elas somem SEM LOG e SEM CONTAGEM.**
Ninguém vê que sumiram. O acervo parece completo e a carta que resolveria o
caso nunca chegou.

E o padrão é perverso: **quanto mais completa a carta, maior a chance de ela
morrer.** Uma lista de documentos é longa porque é completa — é o que a torna
útil e é o que a mata.

**O que destrava:** partir em duas cartas, **não encurtar**. Encurtar uma lista
de documentos é entregar meia lista, que é pior que nenhuma. E acrescentar
contagem no descarte: um filtro que joga fora sem contar não pode ser auditado.

### 📊 15/08/2026 — a conta fechada da leva inteira, com o instrumento ligado

A contagem que faltava existe desde `aplicar.py:147`. Rodada sobre os **72
lotes** (1.780 conversas, 1.527 fatos), ela mede o que antes era estimativa:

```
fatos vistos                    1.527
descartados por tamanho            23   (1,5%)
  por passar de 400 chars          23   ← TODOS. nenhum por ser curto demais
  sobre lista de documentos         8
```

⚠️ **O piso é 15 e não descartou nada.** Em 1.527 fatos, zero ficaram abaixo
dele — o limite inferior não está protegendo de nada que exista. Todo o
descarte vem do teto, e a faixa "15–400" é, na prática, só o 400.

E o recorte que importa para o acervo: das 23, **3 eram inéditas** — nenhuma
outra carta das 18.400 chega perto delas (Jaccard < 0,22). Não é redundância
que morreu no teto; é conhecimento que o acervo não tem por nenhuma outra via:

| ineditismo | o que se perdeu |
|---|---|
| 0,22 | a sequência inteira do atendimento por mensagem automática da prestadora de vidros — número da solicitação, link de vistoria, pré-agendamento, agenda própria |
| 0,17 | **quais seguradoras cobrem a calibração do ADAS** depois da troca do para-brisa (Zurich, Mapfre e HDI cobriam em março/2026; nas demais entra como custo à parte) |
| 0,20 | caminhão que a empresa opera todo dia pode estar **em nome da locadora** e ficar fora da apólice de frota — conferir o proprietário no documento antes de abrir |

As outras 20 têm equivalente no acervo (mediana de Jaccard 0,285), então o custo
real do teto nesta leva são **3 cartas**, não 23. ⚠️ Isso não absolve o limite:
absolve **esta** leva. As 20 cobertas continuam sendo as versões mais completas
do mesmo fato, e é a versão pobre que ficou no RAG.

---

## P-171 · 🟡 Três respostas incompatíveis para "o link de vistoria expirou"

**Aberta em:** 15/08/2026 · **Dono:** 🧑 Founder confirma com a prestadora

📊 O acervo tem **três** respostas diferentes, todas sem seguradora, todas no
fundo comum do RAG:

```
L003 42d16362  pede-se reenvio, novo link, SEM reabrir
L057 9fef2995  NÃO há reemissão — abre-se atendimento novo
L044 4da5b2a6  liga-se no 0800 da companhia para nova disponibilidade
```

**O RAG vai servir uma das três no sorteio.** Duas em cada três vezes o agente
manda o segurado fazer a coisa errada — e a errada custa um atendimento inteiro
(abrir de novo quando bastava pedir reenvio, ou pedir reenvio quando o link
morreu de vez).

Não é contradição de destilação: as três conversas são reais e provavelmente as
três estão certas **para prestadoras diferentes**. O acervo é que não distingue.

**O que destrava:** confirmar com a Maxpar/Autoglass qual é o caminho de cada
uma, e transformar em **uma** carta que ensine a olhar na mensagem qual é o
caso — em vez de três que se contradizem.

---

## P-172 · 🟡 Duas regras do mascarador comem conhecimento por vocabulário

**Aberta em:** 15/08/2026 · **Dono:** 🤖 execução · **Achada** ao recalibrar o
`pii_check` (as 320 `rejected_pii`), **não consertada** — está fora do escopo
das duas tarefas da leva 5, e o dano deixou de ser fatal.

Enquanto a rejeição era `templatize(t) != t`, estas duas regras **derrubavam a
carta inteira**. Agora elas só mascaram e a carta segue para `pending_review`,
então o custo caiu de "some do acervo" para "sai danificada". Continua sendo
conhecimento destruído, e continua invisível para quem lê a carta depois.

📊 As 5 ocorrências medidas nas 320, com o `templatize` de 15/08/2026:

```
templater.py PII[04]  "nome de quem (está|estará)…"  → {NOME}
    "celular com DDD confirmado por botão"      → "celular com {NOME}"
    "ou do WhatsApp que pediu a assistência"    → "ou do {NOME} que pediu"
    "o telefone de quem está no local ANTES do" → "no local {NOME} do"

templater.py PII[32]  "SEGREDO LONGE DO RÓTULO"      → {SEGREDO}
    "o atendimento tem de ser feito pelo 0800." → "feito pelo {SEGREDO}."
```

`DDD`, `WhatsApp`, `ANTES` e um **0800** — nenhum é dado de pessoa. O caso do
`{SEGREDO}` é o mais claro: a regra marca **qualquer número de 4+ dígitos numa
linha que fale "código de acesso"**, e comeu o telefone da central, que é
exatamente o que aquela carta existia para informar.

É a mesma família de `"Ola, quero abrir um sinistro" → "Ola, {NOME} um
sinistro"` e de `das 8h00 → {PLACA}`, ambas já consertadas no mesmo arquivo: a
cura é **estreitar o que a regra tem direito de ver**.

**O que destrava:** medir as duas regras contra o acervo inteiro (18.621
cartas), não só contra as 320 — a amostra de 5 diz que erram, não quanto.
⚠️ E com linha de controle (§9.2): as duas existem por PII real observada, e
estreitá-las sem medir troca conhecimento comido por nome vazado.

**Custa se esquecer:** a carta danificada **parece boa**. Ninguém lê "celular
com {NOME}" e desconfia — parece mascaramento legítimo, e o que sumiu foi a
instrução (`DDD`) que fazia a carta valer.

## P-173 · 🟡 343 cartas em `pending_review` sem ninguém para publicá-las

**Aberta em:** 15/08/2026 · **Dono:** 🤖 execução

📊 Depois da leva 5, o banco tem **343** cartas em `pending_review`: as 320 que
voltaram de `rejected_pii` e as 23 que o teto de 400 tinha matado. Nenhuma está
no RAG — `pending_review` não é indexado.

```
published        17.635
pending_review      343   ← nenhuma no índice
superseded          617
rejected_*           26
```

**O que destrava:** rodar `curadoria_cartas.publicar_lote_sync` sobre elas. Não
foi feito nesta leva **de propósito** — o pedido era recalibrar o portão e
devolver as cartas à fila, não publicar. Publicar 343 cartas de uma vez muda o
que o agente responde e merece uma passada de olho antes.

**Custa se esquecer:** o trabalho das duas tarefas fica meio feito. As cartas
existem, estão limpas, estão etiquetadas — e continuam não respondendo nada.

### 📊 15/08/2026 — ela FECHOU SOZINHA, e não do jeito que a pendência pedia

Medido na auditoria da SPEC-072, com `Prefer: count=exact`:

```
GET /rest/v1/knowledge_cards?select=id&status=eq.pending_review   →      0
GET /rest/v1/knowledge_cards?select=id&status=eq.published        → 17.928  (era 17.635)
GET /rest/v1/knowledge_cards?select=id&status=eq.superseded       →    653  (era 617)
GET /rest/v1/knowledge_cards?select=id&status=like.rejected*      →     40  (era 26)
```

**As 343 entraram no RAG.** Não por decisão de ninguém: `publicar_lote_sync`
roda sozinho a cada rodada do Destilador, e levou `pending_review → published`
sem humano nenhum — que é exatamente o que `curadoria_cartas.py:299` já
documentava e o que esta pendência queria evitar.

> **A pendência pedia "uma passada de olho antes". O sistema não tem onde
> encaixar essa passada de olho, e por isso ela não aconteceu.**

⚠️ **Isto não é uma pendência resolvida — é uma pendência atropelada.** O que
ficou aberto mudou de forma:

- ✅ as 343 respondem, que era o objetivo
- ❌ ninguém olhou, e não há registro de quem publicou nem quando
- ❌ **o mecanismo continua de pé**: a próxima leva que cair em `pending_review`
  será publicada do mesmo jeito, sem revisão e sem aviso

**O que destrava agora:** decidir se `publicar_lote_sync` automático é o desenho
certo. Se for, a pendência morre e a P-67 (filtro de pertinência) fica sendo a
única guarda. Se não for, precisa de um portão — e ele não existe hoje.

**Dono:** 🧑 Founder decide o desenho · 🤖 execução implementa.

---

## P-174 · 🟡 `published_at` é nulo em 5.364 cartas publicadas

**Aberta em:** 15/08/2026 · **Dono:** 🤖 execução
**Achada** na auditoria da SPEC-072, **não consertada** — está fora do escopo
dela.

📊 Medido em 15/08/2026:

```
status='published'                          17.928
published_at não nulo                       12.564
                                            ------
publicadas sem data de publicação            5.364   (29,9%)
```

O número quase coincide com as 5.394 cartas de acervo, e a causa é essa:
`backend/scripts/acervo/publicar_cartas.py:326` grava `status="published"` e
**nunca preenche `published_at`**. Os dois caminhos que preenchem são
`admin_atlas.py:752` e `curadoria_cartas.py:1086` — e o acervo não passa por
nenhum dos dois.

**O que custa esquecer:** toda pergunta com recorte de tempo sobre o RAG
responde errado e **em silêncio**. "Quantas cartas entraram desde a leva 5",
"o que foi publicado antes da correção do portão de PII", qualquer ordenação por
data de publicação — todas descartam ou ignoram 30% do acervo, e nenhuma acusa.
Uma coluna nula não dá erro: dá resposta menor.

**O que destrava:** uma linha em `publicar_cartas.py` para as próximas, e um
backfill para as 5.364 usando `created_at` como aproximação **declarada** — ou a
decisão de que `created_at` já basta e a coluna sai. As duas servem; ter as duas
sem escolher é o que não serve.

---

## P-175 · 🟡 `faceta` e `acervo` não existem no GLOSSÁRIO — e `faceta` já é coluna

**Aberta em:** 15/08/2026 · **Dono:** 🤖 execução

O `GLOSSARIO.md` abre dizendo: *"Um termo tem UMA definição. Se dois documentos
discordarem, **este vence** e o outro se corrige."* Sobre `faceta`, ele está mudo
— e o termo já tem, em produção:

```
escritor           insurance_corpus.py:908 · attendance_distiller.py:659
índice de payload  qdrant_service.py:96  (KEYWORD)
valores válidos    publicar_cartas.py:86  (8 facetas)
portador no banco  pii_check['faceta']    (porque não há coluna)
pendências         P-142 (falta o leitor) · P-145 (teste medido e recusado)
coluna proposta    SPEC-072 Bloco 6
```

**`acervo` está no mesmo caso:** dá nome a 3 SPECs e a 6 pendências, sem
definição. `destilador` idem.

⚠️ **O risco não é estético, é de colisão.** `20260815_02_a_carta_ganha_tema.sql`
já precisou escrever no `COMMENT` que `temas` *"difere de `ramo` e de
`category`"* — e nada diz como `faceta` difere de `temas`. 📊 A prova de que a
confusão já existe: das 380 cartas com `faceta='documento'`, só **201 (53%)**
têm o tema `documentacao`, e **673** cartas de acervo têm o tema sem ter a
faceta. Dois rótulos para perguntas diferentes, discordando em quase metade dos
casos, e nenhum dos dois definido.

**O que destrava:** três entradas no `GLOSSARIO.md`, escritas junto com o Bloco 6
da SPEC-072 — que é quando a coluna nasce e é a última hora de acertar o nome
antes de ele virar schema.

**O que custa esquecer:** o próximo a ler vai inferir a definição do código, e o
código tem duas. Foi assim que `insurer_key` passou a guardar "apareceu numa
conversa sobre a Allianz" prometendo "é regra da Allianz" — 📊 e custou uma
correção de 3.760 para 1.158 cartas.

---

## P-176 · 🟡 `corrigir.py` apaga `pii_check` — e a carta substituta nasce sem procedência

**Aberta em:** 15/08/2026 · **Dono:** 🤖 execução
**Achada** pelo juiz crítico do BLOCO 0 da SPEC-072. **Não consertada de
propósito** — é a mesma família do defeito do bloco, mas em arquivo e mecanismo
diferentes, e o Founder pediu para anotar e seguir em vez de alargar o escopo.

`backend/scripts/destilacao_max/corrigir.py:85` faz
`.select("id, card_text, ramo, insurer_key, status")` — **sem `pii_check`**. E
em `:114`:

```python
marca = {**(c.get("pii_check") or {}), "superseded_por": MARCA, "motivo": motivo}
```

`c` nunca traz `pii_check`, então o spread é **sempre vazio**, e o `update` de
`:118-120` substitui a coluna inteira por duas ou três chaves.

**Duas metades, e elas não têm a mesma gravidade — a distinção importa:**

🟢 **A metade menor.** A carta cujo `pii_check` é apagado está sendo
**aposentada** no mesmo `update` (`status='superseded'`). Ela sai do índice de
qualquer jeito. O que se perde é o rastro de auditoria — `faceta`, `origem`,
`reindexado_em` — de uma carta que já morreu. Ruim, não urgente.

🔴 **A metade grave, e é outra.** A carta **substituta**, inserida em `:124-132`,
nasce **sem `source_unit_id` e sem `faceta` no `pii_check`**. Ela é a versão
corrigida de uma carta de condição geral — e passa a existir sem nenhum caminho
de volta ao contrato de onde a original veio. Duas consequências:

1. **o lastro é o produto** (`attendance_distiller.py:639-652`): sem `unit_id`
   ela vira "acho que a Porto não cobre" onde antes era "a cláusula 4.4.2.d das
   Condições Gerais vigentes desde 01/07/2026 diz que não cobre";
2. ela entra em `publicar_lote_sync` com `documento_publico=False` — **o caso
   exato que o BLOCO 0 fechou**, reaberto por outra porta.

**O que destrava:** acrescentar `pii_check, source_unit_id` ao select de `:85`, e
propagar `source_unit_id` (e a `faceta`) para o `upsert` de `:124`. Uma linha e
duas chaves. ⚠️ Precisa de teste com **linha de controle**: a carta corrigida tem
de manter o mesmo `source_unit_id` da original, e a mutação que remove a
propagação tem de derrubar o teste.

**O que custa esquecer:** `corrigir.py` é rodado à mão, então isto não acontece
sozinho — mas quando acontecer, a carta *melhor* é a que perde a procedência.
O conserto de conteúdo destrói a prova. Ninguém vai desconfiar: a carta nova
está mais certa que a velha.

---

## P-178 · 🔴 O leitor de faceta existe, está testado e está DESLIGADO — falta a forma certa

**Aberta em:** 15/08/2026 · **Dono:** 🧑 **Founder decide** · 🤖 execução implementa
**Origem:** juiz crítico do SPEC-072 Bloco 1. Conflito canônico — CLAUDE.md §10.3.

O filtro de faceta e o de temas foram construídos, testados com mutação, e a
**fiação foi revertida antes de qualquer deploy**. O motivo:

**SPEC-070 §5.1:304** — *"`null` passa em todo filtro, **nunca elimina**. Rótulo
dá **cota e prioridade**; só fato verificável elimina candidato."*

Um `must` faz o rótulo eliminar. E 📊 **0 de 5.396 cartas do acervo têm faceta
ausente** — o braço "OU ausente" protege quem não tem rótulo, e no acervo todo
mundo tem. Lá o filtro esconde 5.016 cartas, incluindo a da Porto que diz *"não
há cobertura se quem dirigia estava com a CNH suspensa, cassada ou vencida"* —
exatamente o que o segurado precisa ouvir ao perguntar sobre documentos.

**A forma certa, já proposta:** uma terceira linha de `ORCAMENTO_GLOBAL` com cota
própria, que **acrescenta** cartas de documento sem **remover** nenhuma. O
detalhe está no addendo de CA-040 em `CHANGE-ADDENDA.md`.

**O que destrava:** decisão de arquitetura de busca. Custa um `search_similar` a
mais por pergunta documental (mesmo embedding) e um balde novo em `COTA_FINAL`.

⚠️ **E ela tem um pré-requisito medido:** 📊 `faceta` e `temas` discordam em
**47%** (só 201 das 380 cartas com `faceta='documento'` têm o tema
`documentacao`). Ligar os dois juntos, de qualquer forma, antes de reconciliar,
acha 53% do que deveria. A reconciliação é o primeiro item do Bloco 6.

**O que custa esquecer:** a infraestrutura fica pronta e inerte. Não quebra nada
— e não entrega nada. As 380 cartas de documento continuam dependendo do BM25
casar a palavra por sorte, que é o problema que a SPEC-072 existe para resolver.

---

## P-180 · 🧑 As 27 URLs de Delegacia Virtual — o que falta no "onde pegar"

**Aberta em:** 16/08/2026 · **Dono:** 🧑 Founder confirma · 🤖 execução aplica

O Bloco 3 da SPEC-072 entregou as 10 cartas de "onde pegar", e o **B.O. é o
único documento cujo endereço muda por ESTADO** — é o que o Founder nomeou:
*"o agente deve enviar na lista o link do boletim de ocorrência online pra fazer
na hora, igual a Regina sempre faz."*

⚠️ **Não inventei nenhuma URL.** Cada Polícia Civil tem endereço próprio, e um
link errado é pior que nenhum: manda o segurado a uma página que não existe e
ele volta sem o B.O. e sem confiança. A carta entregue diz o **caminho** — o
nome oficial do serviço ("Delegacia Virtual" + sigla do estado), o login gov.br,
quais ocorrências são aceitas online e que o protocolo já serve para abrir o
aviso. Isso é verdadeiro nos 26 estados e no DF, e resolve.

**O que destrava:** as 27 URLs verificadas, uma por UF. Com elas o agente manda o
link e resolve mais rápido; sem elas manda o caminho e resolve. **Nenhum dos dois
mente** — e essa é a diferença que fez a carta sair assim.

⚠️ E o gate original da SPEC (*"pedir a lista para um sinistro em SC e em SP
devolve links diferentes"*) **não pode ser declarado verde** enquanto as URLs não
existirem. Está declarado aqui em vez de contornado.

**O que custa esquecer:** o B.O. é a maior objeção medida do acervo — *"precisa
de BO mesmo assim?"*, *"nem dão andamento"*. A conduta certa é a da atendente:
não argumentar, mandar o link do estado certo.

---

## P-182 · 🟠 `PORTAL_VAULT_KEY` é uma chave única e global, sem rotação

**Aberta em:** 16/08/2026 · **Dono:** 🧑 Founder decide, 🤖 execução implementa

📊 `portal_vault.py:13-19` e `portal_worker/vault.py:8-14` fazem
`Fernet(os.getenv("PORTAL_VAULT_KEY"))`. **Uma** chave, compartilhada entre
smith-api e portal-worker, sem key-id no ciphertext e sem caminho de rotação no
repositório. Comprometer essa env decifra as senhas de **todas** as corretoras.

Fernet carrega timestamp mas não identificador de chave, então hoje não há como
saber com qual chave um segredo foi cifrado — o que é exatamente o que uma
rotação precisa saber.

**O que destrava:** 🤖 `MultiFernet` com lista de chaves (decifra com qualquer
uma, cifra sempre com a primeira) + recifragem em lote + procedimento escrito.
**O que custa esquecer:** nada hoje. No dia de um vazamento de env, a
alternativa a ter rotação é pedir a 16 contas que troquem a senha no portal.

Fora do escopo da SPEC-073 por decisão do Founder (CA-041).

---

## P-183 · 🟠 `portal_jobs.evidence` acumula PII de segurado sem retenção

**Aberta em:** 16/08/2026 · **Dono:** 🤖 execução, na SPEC de segurança/LGPD

📊 `worker.py` funde `result.captured` dentro de `evidence`, e a lista de
inadimplentes carrega nome, CPF/CNPJ, apólice, vencimento e valor. `grep` por
retenção/purga em `portal_jobs`: **zero**. `routine_runs` tem 90 dias;
`portal_jobs` acumula indefinidamente.

A SPEC-073 acrescentou o redator único, e ele **passa em todo o caminho novo** —
profiler, trace, envelope, log. Mas a PII que a journey grava como **dado de
trabalho** (o serviço a lê de volta em `_extract_items`) é legítima enquanto o
job está vivo, e vira passivo depois.

**O que destrava:** 🧑 Founder — definir a janela (30/60/90 dias). 🤖 depois:
job de purga que zera `evidence` de job terminal, preservando status e contadores.
**O que custa esquecer:** o volume só cresce, e a conversa com a LGPD fica mais
cara a cada mês.

---

## P-184 · 🟡 A pilha TypeScript de portal tem guardas que nada chama

**Aberta em:** 16/08/2026 · **Dono:** 🤖 execução, provavelmente na SPEC-075

📊 `portal-company-scope.ts`, `portal-tenant-canary-authorization.ts`,
`portal-session-vault.ts` e `portal-supabase-vault.ts` têm **zero call sites de
produção** — só `scripts/*.test.mjs` e `package.json`. As rotas que os aplicariam
(`app/api/admin/portal-browser/`) **não existem**.

São funções puras corretas, com boa cobertura de teste, e nenhuma delas está no
caminho de execução. O pior dos mundos: a suíte verde sugere uma proteção que o
runtime não tem.

Elas também contêm disciplina que o caminho vivo Python **não** tem: TTL de
sessão, `revoked`/`expired`/`challenge_required`.

**O que destrava:** 🤖 decidir entre cabear no caminho real ou remover — e, se
remover, portar o TTL de sessão para o Python antes.
**O que custa esquecer:** alguém lê a cobertura e conclui que o escopo está
protegido.

---

## P-185 · 🟡 `backend/app/api/portal.py` aceita `company_id` livre atrás de um segredo estático

**Aberta em:** 16/08/2026 · **Dono:** 🤖 execução

📊 Os quatro endpoints exigem `X-AutoBrokers-Internal-Key` e falham fechado sem
ela — isso está certo. Mas o `company_id` vem do corpo/query, não de um token
que o carregue. Com a chave em mãos,
`GET /api/portal/credentials?company_id=<qualquer>` devolve `username` e
`has_password` de qualquer corretora.

Não é alcançável hoje: o único chamador é o proxy Next, que injeta
`ctx.companyId` da sessão. É defesa em profundidade que falta, não porta aberta.

**O que destrava:** 🤖 token que carregue o tenant, ou assinatura por requisição.
Sem rate-limit nem log de auditoria hoje.
**O que custa esquecer:** o dia em que a chave interna vazar, o raio do estrago
é a plataforma inteira em vez de uma corretora.

---

## P-186 · 🟡 O canário live read-only da SPEC-073 não foi executado

**Aberta em:** 16/08/2026 · **Dono:** 🧑 Founder (liberar a janela)

A SPEC-073 §K2 pede um canário somente-leitura por classe de portal — Allianz
(controle histórico), HDI (anti-bot), Yelum ou Tokio (SPA/API), MAPFRE
(multiempresa), Zurich (journey nova).

**Não foi executado nesta SPEC**, por dois motivos legítimos e nenhum técnico:

1. havia uma reindexação de 17.928 cartas rodando dentro do `smith-api`, e o
   Founder determinou não implantar nem reiniciar nada até ela terminar;
2. 📊 a MAPFRE continua na P-149 — a journey existe no código e não na imagem,
   então o canário dela terminaria em *"journey desconhecida"* e mediria o
   deploy, não a SPEC.

Tudo que **não** depende de rede real foi provado offline: 363 asserções novas,
211 verdes no backend inteiro e 17 vermelhos individualmente medidos como
já-vermelhos na baseline.

**O que destrava:** 🧑 reindexação terminada + Implantar o `portal-worker` +
janela autorizada. Depois: deploy com `PORTAL_DISCOVERY_MODE=false`,
`PORTAL_VISION_ENABLED=false`, `PORTAL_PROFILER_ENABLED=true`, conferir
`/health` e rodar cobrança read-only sem enviar WhatsApp.
**O que custa esquecer:** declarar a SPEC-073 "provada em produção" sem ter
tocado em produção — exatamente o defeito que a CLAUDE.md §9.1 registra.

### ✅ 16/08/2026 — EXECUTADO. E achou um defeito que o offline não acharia

O Founder implantou, a janela abriu e o canário rodou na Yelum, read-only, sem
enviar WhatsApp. 📊 104 requests relevantes observados pelo profiler.

**O canário pagou o próprio custo na primeira execução.** Ele encontrou o
redator comendo o campo `recibo`: eu havia embrulhado o `evidence` inteiro em
`redigir()`, e `recibo` virava `<redacted:cartao>-3`. Como `recibo` é a chave
anti-duplicação do `billing_sent_log`, **toda execução concluiria que nada foi
enviado** — e o segurado receberia o mesmo WhatsApp de novo, indefinidamente.
Nenhum dano ocorreu porque a rotina estava inativa. Corrigido com
`redigir_envelope()`, que sanitiza só as superfícies de diagnóstico e deixa o
trabalho passar intacto.

Esse defeito **não era achável offline**: as fixtures não tinham `recibo`, e o
teste do redator provava que ele mascara — que era exatamente o problema.

Achado secundário: zero candidatos de API nomeados → virou a [P-187](#p-187).

---

## P-187 · 🟡 O profiler não nomeia candidatos de API fora do portal de vidros

**Aberta em:** 16/08/2026 · **Dono:** 🤖 execução, quando cada portal for medido

📊 Medido no canário P-186 (Yelum, 16/08): o profiler observou **104 requests
relevantes** e nomeou **zero candidatos de API**.

Não é defeito de captura — é calibração. `_HOSTS_DE_PORTAL` no `worker.py` mapeia
`yelum_corretor → yelumseguradora.com.br`, e a API real do Novo MEC responde em
outro host. Sem bater o host, `classificar_origem()` marca tudo como
`third_party`, e o nomeador de candidatos só considera `first_party`.

**Por que não corrigi agora:** adivinhar o host de cada um dos sete portais é
exatamente o que este projeto proíbe. O host certo sai de uma medição — e a
medição sai de graça, do próprio profiler, na primeira execução de cada portal.

**O que destrava:** 🤖 ler `evidence.profiler` de um job real por portal e
preencher o mapa com o host observado. Sete linhas, uma medição cada.
**O que custa esquecer:** o profiler continua registrando trajetória e drift
normalmente; só a sugestão de "esta chamada parece a fonte estruturada desta
tela" fica silenciosa fora de vidros. É perda de aceleração futura, não de
proteção.

📊 Em vidros o mapa está correto (`abraseuatendimento.com.br`), que é onde a
SPEC-074 precisa dele.

---

## P-188 · 🔴 Não existe teto de entradas por portal por janela de tempo

**Aberta em:** 16/08/2026 · **Dono:** 🤖 execução (SPEC-075) · **Origem:** preocupação explícita do Founder

> *"o cuidado com o número de entradas dentro dos portais das seguradoras para
> não sermos bloqueados"*

A SPEC-074 pôs tetos, e eles são reais — mas são **por sessão**:

| Teto | Onde | Escopo |
|---|---|---|
| `MAX_CHAMADAS = 150` | `vidros_sessao.py` | uma sessão |
| `MAX_RODADAS = 12` | `vidros_questionario.py` | um questionário |
| idempotência `v2` | `portal_params.py` | impede o pedido repetido |

**O que falta:** nenhum deles conta entradas **por portal, por corretora, por
hora**. Dez jobs simultâneos da mesma corretora são dez sessões, cada uma com
seu teto de 150 — 1.500 requisições que nenhum contador vê. Também não há
backoff coordenado: se o portal começar a responder 429, cada job descobre
sozinho, e os outros nove continuam batendo.

📊 O risco não é hipotético neste projeto: o bloqueio Akamai medido em 10/08 é o
que obrigou o `--headless=new`, e o User-Agent com `HeadlessChrome` medido em
12/08 é a mesma família de problema. Bloqueio de portal é a falha que tira **a
corretora inteira** do ar, não um job.

**O que destrava:** 🤖 um contador em Redis com chave `(portal, company_id,
janela)` e um lease que o worker precisa adquirir antes de abrir sessão — a
infraestrutura de lock/lease já existe no Redis, não é motor novo. Mais backoff
exponencial compartilhado ao ver 429/403.
**O que custa esquecer:** ser bloqueado numa seguradora derruba todo o
acionamento daquela corretora naquele portal, e a religação depende da
seguradora, não de nós. É o único item da 074 que pode causar dano sem bug.

---

## P-189 · 🟠 Nenhum serviço injeta o SHA do build — deploy não é verificável

**Aberta em:** 16/08/2026 · **Dono:** 🤖 execução

📊 Medido em 16/08, depois de disparar os três deploys da SPEC-074:

```
portal-worker /health  ->  "build_sha": "unknown"
smith-api     /health  ->  "git_commit": "nao-injetado"
```

O `Dockerfile` do portal-worker tem o estágio `gitinfo` e copia
`build_sha.txt` — mas o valor chega `unknown`, então o estágio não enxerga o
`.git` no contexto de build do EasyPanel.

**Por que isso importa mais do que parece:** a SPEC-073 pediu explicitamente
"build/git SHA real e verificável" no `/health`, e o que existe hoje **não é
verificável**. Sem SHA, a única prova de que o deploy trocou é o `build_time`
do portal-worker — e o `smith-api` não tem nem isso. A CLAUDE.md §9.1 nasceu de
1h40 fora do ar porque um gate parou antes de ligar o servidor; não saber qual
código está no ar é a mesma classe de cegueira.

**O que destrava:** 🤖 passar o SHA como build-arg (`--build-arg
GIT_SHA=$(git rev-parse HEAD)`) em vez de depender do `.git` no contexto, e
acrescentar `build_time` ao `/health` do `smith-api`. Se o EasyPanel não
permitir build-arg, gravar o SHA num arquivo versionado no próprio commit.
**O que custa esquecer:** todo relatório futuro que disser "implantado e
verificado" estará afirmando algo que ninguém pode conferir.

---

## P-190 · 🧑 O canário real do portal de vidros — não há como fazê-lo read-only

**Aberta em:** 16/08/2026 · **Dono:** 🧑 Founder

A SPEC-074 foi provada por **replay offline** contra fixtures extraídas de 58 MB
de HAR real (`SessaoDeQuestionarioFalsa` roda a sequência medida da Porto até o
`204`), mais 6 mutações dirigidas. Isso prova o contrato.

**O que não prova:** que o portal hoje responde como respondia na captura.

E aqui a 074 é diferente de todas as SPECs anteriores: **não existe canário
read-only da fronteira material**. O preflight de apólice é read-only e já roda,
mas ele não exercita o que precisa de prova. Exercitar de verdade significa
`POST /atendimentos` — abrir um atendimento de vidro **no nome de um segurado**,
num portal que **cobra por atendimento**. Não existe homologação do Maxpar
disponível.

**O que destrava:** 🧑 uma de duas coisas — (a) um caso real que o segurado
realmente queira abrir, acompanhado ao vivo, comparando o `CodigoAtendimento`
devolvido com o que a tela mostra; ou (b) credencial de homologação obtida junto
à Maxpar/Autoglass.
**O que custa esquecer:** o caminho DOM continua funcionando e é o que roda hoje,
então o custo é de **confiança**, não de operação: sem isso, o caminho API-first
não pode ser ligado com honestidade. Ver [P-191](#p-191).

---

## P-191 · 🟡 O caminho API-first nunca tocou o portal real, e por isso nasce desligado

**Aberta em:** 16/08/2026 · **Dono:** 🧑 Founder (autorizar a janela) + 🤖 execução

`PORTAL_VIDROS_API_FIRST` **nasce desligada** e foi testada em 10 valores de
entrada: só `1|true|yes|on` ligam; `false`, `0`, vazio, `nao` e `maybe` deixam
desligado. Com a flag off, `abrir_atendimento` é o mesmo código de sempre — o
bloco novo é um `if` que não entra, e um `except` largo garante que erro no
caminho novo nunca custe o acionamento.

📊 O que o caminho API-first oferece, medido no HAR: descobrir a **ausência de
cobertura num 400, antes de escrever qualquer coisa**, e uma chamada REST no
lugar de uma navegação de tela inteira com todos os assets — o que ataca
diretamente a [P-188](#p-188).

**O que destrava:** o canário da [P-190](#p-190). Depois: ligar em **uma**
corretora só, um caso acompanhado, e conferir se o `CodigoAtendimento` devolvido
bate com o que a tela do portal mostra.
**O que custa esquecer:** 258 linhas prontas e inertes. Não quebra nada parado —
só não entrega o ganho.

---

## P-192 · 🟡 `tipo_atendimento_para()` só conhece a Porto, e isso é o que a evidência suporta

**Aberta em:** 16/08/2026 · **Dono:** 🤖 execução, quando houver HAR de outra seguradora

Eu havia relatado que `TipoAtendimento` era null em 100% dos casos — "fato
negativo". 📊 Era generalização de dado parcial: o HAR da Yelum tinha só null, e o
da Porto mostrou `1` e `2`. A SPEC estava certa e eu estava errado.

A função hoje só devolve valor para a Porto, que é o alcance da medição. Para as
demais seguradoras devolve `None`, que é o comportamento observado — mas
"observado em uma captura" não é o mesmo que "é assim".

**O que destrava:** 🤖 uma captura de HAR por seguradora no fluxo de vidros, lida
com o mesmo método. O profiler já registra o suficiente.
**O que custa esquecer:** se outra seguradora exigir `TipoAtendimento` e
recebermos `None`, o pedido é recusado na fronteira 1 — falha limpa e visível, não
silenciosa. Risco baixo, mas é dívida de medição, não decisão de projeto.

---

## P-193 · 🟡 O caminho API-first nasceu MORTO, e nenhum teste de texto viu

**Aberta e FECHADA em:** 16/08/2026 · **Dono:** 🤖 execução · registro de lição

Fica aqui não porque esteja pendente, mas porque a **causa** é reutilizável.

`abrir_atendimento_api` lia `params["_seguradora_slug"]` e `params["_data_iso"]`.
📊 `grep` em todo o repositório: **ninguém escrevia esses campos**. A função
devolvia `None` em 100% das chamadas. Um caminho inteiro — 258 linhas, duas
fronteiras materiais, guard, checkpoint — inerte por construção.

**Nenhum teste podia ver**, porque todos os testes daquele caminho eram
`inspect.getsource()` + substring: *"a palavra `guard.before` aparece antes da
palavra `criar_atendimento`"*. Estava tudo lá, na ordem certa. O código era
perfeito e não fazia nada.

Quem viu foi o **primeiro teste executável** — na primeira execução, no primeiro
bloco: `buscar_apolice` nunca era chamado.

**O que isso ensina, e vale para toda SPEC futura:** teste de inspeção de fonte
prova que um texto existe num arquivo. Ele nunca prova que o código roda, e nunca
prova que roda com os dados que a produção entrega. Onde houver fronteira
material, tem de haver pelo menos um teste que EXECUTA e conta quantas vezes o
POST saiu.

**Consertado:** a função deriva `slug_da_seguradora(insurer_name)` e
`data_iso(data_dano)` do que a journey de fato recebe. Lista de slugs FECHADA —
seguradora não medida devolve `""`, o preflight desiste e o DOM assume.

---

## P-194 · 🔴 `failed` deixou de significar "nada aconteceu" — e o dedup dependia disso

**Aberta e FECHADA em:** 16/08/2026 · **Dono:** 🤖 execução · achado por juiz crítico

O defeito mais perigoso da SPEC-074, e ele não estava em código novo.

A SPEC-065 §7.2 estabeleceu `failed` como a válvula de escape do dedup:
`portal_tool._buscar_pedido_vivo` filtrava com `.neq("status","failed")`, e o
índice único parcial `idx_portal_jobs_pedido_vivo` usava o **mesmo** predicado.
Era correto — enquanto `failed` só acontecesse **antes** de qualquer escrita.

A SPEC-074 quebrou a premissa. O `worker.py` gravava `status="failed"` no handler
de exceção **mesmo sabendo** que houve efeito material — o bloco logo acima já
rebaixava a fase para `unknown` justamente porque sabia. Resultado: um job que
criou o atendimento e caiu depois virava `failed`, sumia do dedup, e o próximo
`portal_action` com a mesma chave abria **o segundo atendimento, pago, no nome do
mesmo segurado**.

Três consertos, em profundidade:

| Camada | O que mudou |
|---|---|
| `worker.py` | com prova de efeito, grava `needs_human`, não `failed` |
| `portal_tool.py` | `failed` **com** prova de efeito é tratado como pedido VIVO |
| `vidros_apifirst.py` | grava `evidence["protocolo"]` já na fronteira A |

O terceiro é o que fecha de verdade: `tem_prova_de_efeito` procura
`evidence["protocolo"]`, e o caminho API só escrevia essa chave **depois** da
fronteira B. Entre A e B havia uma janela em que o pedido **já existia na
seguradora** e a evidência dizia que não havia prova de nada.

**O teste que guardava a regra antiga foi MIGRADO, não apagado** (CLAUDE.md §9.3):
ele agora exige a regra mais forte — a exclusão olha a evidência, não o rótulo —
e ganhou o par executável que prova que os dois casos conseguem diferir.

**O que custa esquecer:** nada, está fechado. Mas a lição fica: quando uma SPEC
introduz efeito material num fluxo, **todo lugar que trata status como prova de
ausência de efeito vira um defeito** — mesmo os que ela não tocou.

---

## P-195 · 🟢 Deploy verificável entrou; o `build_sha` continua `unknown`

**Aberta em:** 16/08/2026 · **Dono:** 🤖 execução, quando alguém puder mexer no EasyPanel

A [P-189](#p-189) foi resolvida por outro caminho: `code_fingerprint` no
`/health`, o hash dos `.py` que o processo tem em disco. Não depende de git nem
de build-arg, e `backend/scripts/conferir_o_que_esta_no_ar.py` responde em duas
linhas se o deploy trocou o código.

📊 Já provou o próprio valor na estreia: com três deploys respondendo HTTP 200
`Deploying...`, o script disse `VEREDITO: a versao no ar e ANTERIOR` — e estava
certo.

**O que continua faltando:** `build_sha` segue `"unknown"` e `git_commit` segue
`"nao-injetado"`. A digital diz *"é o mesmo código"*; ela não diz *"é o commit
`abc1234`"*. Para auditoria histórica — "o que estava no ar no dia X?" — o SHA
ainda seria melhor.

**O que destrava:** 🤖 build-arg `GIT_SHA` no EasyPanel, ou gravar o SHA num
arquivo versionado. Baixa prioridade: a pergunta operacional já tem resposta.
**O que custa esquecer:** pouco. É conforto de auditoria, não segurança.

---

## P-196 · 🧑 As duas migrations da SPEC-075 estão escritas e NÃO aplicadas

**Aberta em:** 16/08/2026 · **Dono:** 🧑 Founder (janela)

```
20260816_02_spec075_portal_job_lineage_priority.sql   6 colunas + 3 índices
20260816_03_spec075_tools_de_portal.sql               3 tools + 3 releases
```

As duas são **expand-only**, idempotentes, com APPLY / VERIFY / ROLLBACK
escritos antes. Nenhuma toca coluna existente. Nenhuma toca o índice único
parcial `idx_portal_jobs_pedido_vivo`, que é a proteção anti-duplicidade da
SPEC-065.

**O código funciona sem elas.** `billing_collection` e `portal_tool` tentam o
insert com `operation_key` e repetem sem a coluna se o banco recusar; o worker
tenta ordenar por prioridade e cai para a ordenação de sempre. Isso não é
gentileza: o `smith-api` sobe com a imagem nova assim que o deploy roda, e a
migration é aplicada por outra mão, em outro momento.

**O que destrava:** 🧑 janela + `MIGRATIONS-AUTHORITY` §9 (registrar commit,
aplicar, rodar o VERIFY, guardar a saída).
**O que custa esquecer:** a linhagem não é gravada, e `portal_jobs` continua
órfão. Nada quebra — só não melhora.

### ✅ 17/08/2026 — APLICADAS. E o banco corrigiu duas coisas que eu supunha

Aplicadas por acesso direto ao Supabase (`dcajcvlzcjbmyapmklil`), em janela com
**zero jobs na fila**. 📊 VERIFY completo:

```
colunas novas ............. 6 de 6      indices novos ......... 3 de 3
jobs fora do default ...... 0           idx_portal_jobs_queued  preservado
idx_portal_jobs_pedido_vivo INTOCADO    total de jobs ......... 109
```

🔴 **A segunda migration estava errada, e só o banco vivo mostrou.** Duas coisas:

1. Eu supunha que as tools de portal **não existiam**, porque `grep` no
   repositório não as achava. Elas existiam — `portal.billing_read`,
   `portal.policy_read` e `portal.execute`, com release `1.0.0` publicada,
   `input_schema = {}` e provider antigo. São das 9 versões aplicadas sem
   arquivo que a §4 desta mesma autoridade registra. **Eu li o repositório como
   se fosse a fonte do schema, e ela abre dizendo que não é.**

2. Eu inventei `side_effect_class = 'write_external'`. O constraint
   `ck_tool_side_effect` recusou; o valor certo é `external_commitment` — que é
   melhor nome, porque descreve um compromisso com terceiro.

A migration foi reescrita como `20260817_01_..._schemas_reais.sql`: em vez de
criar, **publica a release `1.1.0`** com schema real (release publicada é
imutável, SPEC-056). A `20260816_03` ficou no repositório marcada SUPERADA.

⚠️ E uma lição operacional: `apply_migration` **não foi transacional**. Duas
linhas do INSERT entraram e a terceira falhou. Migration que conta com rollback
automático não pode ser escrita assim.

---

## P-197 · 🟡 A ponte está em `legacy` e a sombra ainda não acumulou diffs

**Aberta em:** 16/08/2026 · **Dono:** 🤖 execução, depois de 🧑 ligar `shadow`

`PORTAL_EXECUTION_GATEWAY_MODE` nasce `legacy`. Em `shadow` a ponte resolve em
paralelo e grava o diff em `portal_jobs.evidence.gateway_sombra`; em `on` ela
executa.

📊 O desenho é o mesmo do `TOOL_GATEWAY_MODE`, que já pagou por si nesta casa:
51 diffs em sombra na madrugada de 15→16/08 sem afetar nenhuma execução.

**O que destrava:** 🧑 `PORTAL_EXECUTION_GATEWAY_MODE=shadow` no EasyPanel.
Depois: 🤖 ler os diffs de alguns dias de cobrança real e conferir que
`concorda=true` em 100% deles. **Só então** `on`, e só para
`billing.overdue.list`, que é read-only.
**O que custa esquecer:** a ponte inteira fica inerte. Não quebra nada parada.

---

## P-198 · 🟠 O lease foi provado contra um Redis FALSO, não contra um real

**Aberta em:** 16/08/2026 · **Dono:** 🤖 execução, quando houver Redis no worker

📊 As asserções do Bloco N rodam contra um duplo em memória que implementa
`SET NX EX`, `GET` e `EVAL`. Elas provam a LÓGICA: só o dono renova, só o dono
libera, contas diferentes rodam em paralelo, Redis fora rebaixa para 1.

🔴 O que elas **não** provam: que o `redis-py` real se comporta como o duplo, que
o `EVAL` roda no Redis do EasyPanel, que a latência cabe no heartbeat de 30s, e
que `REDIS_URL` está sequer definida no ambiente do portal-worker.

E há um detalhe que só um Redis real revela: `redis>=5.0` acabou de entrar no
`requirements.txt` do worker. **A biblioteca não está na imagem que está no ar.**
Enquanto não houver deploy, `redis_disponivel()` devolve `False` e a
concorrência fica em 1 — que é o comportamento seguro, mas não é o pretendido.

**O que destrava:** 🤖 deploy do portal-worker (traz a biblioteca) +
🧑 confirmar `REDIS_URL` no ambiente dele. Depois conferir em `/health`:
`redis_para_lease: true`.

### 📊 17/08/2026 — a URL EXISTE, e o valor está achado

O `smith-api` tem, no ambiente dele:

```
REDIS_URL=redis://default:<senha>@autobrokers_intelligence_os_autobrokers-smith-redis:6379
```

É o mesmo Redis que o Work OS usa. O `portal-worker` simplesmente **não tem a
variável** — o ambiente dele tem cinco linhas. Colar a mesma URL lá resolve.

🔴 E a biblioteca já subiu: o deploy da SPEC-075 levou `redis>=5.0` para a
imagem. Falta só a variável. Depois dela, `/health` deve mostrar
`redis_para_lease: true`, e só então `PORTAL_WORKER_CONCURRENCY` maior que 1
passa a ter efeito.
**O que custa esquecer:** `PORTAL_WORKER_CONCURRENCY` maior que 1 não terá
efeito nenhum — e `/health` diz isso na cara, com `concurrency: 1` ao lado de
`concurrency_configurada: 4`.

---

## P-199 · 🟡 Seis portais declaram host como constante, sem allowlist fechada

**Aberta em:** 16/08/2026 · **Dono:** 🤖 execução · achado pelo `portal_factory audit`

📊 Medido em 16/08: Allianz, HDI, MAPFRE, Tokio, Yelum e Zurich declaram o
endereço do portal como constante (`ZURICH_BASE = "https://..."`). Isso
**documenta** para onde se pretende ir; não **impede** ir a outro lugar.

Só o portal de vidros tem `HOSTS_PERMITIDOS` com recusa por chamada — e ele só
tem porque a SPEC-074 encontrou um buraco de substring lá (`api.autoglass.com.br`
casava com `api.autoglass.com.br.evil.com`).

**O que destrava:** 🤖 uma função `host_permitido()` por portal, no modelo do
`vidros_api.host_permitido` — extração real de hostname, comparação por sufixo
de ponto, lista fechada.
**O que custa esquecer:** hoje nenhuma journey é redirecionada, então o risco é
teórico. Ele deixa de ser teórico no dia em que um portal responder um `302`
para outro domínio, ou em que uma URL vier de dado.

---

## P-200 · 🟡 A Allianz é o único portal sem fixture nenhuma

**Aberta em:** 16/08/2026 · **Dono:** 🤖 execução · achado pelo `portal_factory audit`

📊 Os outros seis têm: `zurich_parcelas.py`, `hdi_parcelas.py`,
`mapfre_parcelas.py`, `tokio_inadimplentes.py`, `yelum_parcelas.py`,
`fixtures/vidros/*`. As duas journeys da Allianz só podem ser conferidas contra
o portal real, com credencial e rede.

🔴 A Allianz é a **primeira** seguradora que a Cobrança Feita atendeu. É a que
tem mais histórico em produção e a única sem rede de segurança offline.

**O que destrava:** 🤖 capturar uma resposta real da tela de inadimplentes e
sanitizá-la no padrão das irmãs (📊 0 CPF, 0 CNPJ, nomes trocados).
**O que custa esquecer:** qualquer mudança na journey da Allianz só é conferida
em produção, contra dinheiro de corretora.

---

## P-201 · 🟡 9 das 30 mutações da SPEC-075 foram executadas

**Aberta em:** 16/08/2026 · **Dono:** 🤖 execução, quando houver infraestrutura

A §34 pede 30 mutações. Foram rodadas **9**, e as 9 foram detectadas.

As 21 restantes cobrem caminhos que **não existem sem infraestrutura real**:
lease contra Redis de verdade, corrida entre dois workers, `23505` do índice
único vindo do Postgres, `tool_invocation` real, Work Run real ponta a ponta.
Simulá-las com duplo provaria o duplo, não o sistema.

**O que destrava:** 🤖 as migrations aplicadas ([P-196](#p-196)) + Redis no
worker ([P-198](#p-198)) + um ambiente onde dois workers possam subir.
**O que custa esquecer:** as proteções de concorrência e de corrida de banco
estão escritas e não estão provadas contra o que elas protegem.

---

## P-202 · 🟢 Divergência de vocabulário entre a SPEC-075 §16.1 e o código

**Aberta em:** 16/08/2026 · **Dono:** 🧑 Founder (decisão de canon) · achada pelo Bloco J

A §16.1 escreve os estados como `success | business_blocked | needs_connection`.
O `contracts.py` implementou `ok | portal_blocked | no_connection`.

O `replay.py` aceita os dois e traduz. Quatro estados da SPEC não têm
equivalente implementado — `auth_expired`, `rate_limited`, `portal_changed`,
`transient_failure` — e o módulo deixa `""` para eles em vez de inventar um par.

**O que destrava:** 🧑 escolher um vocabulário e registrar em
`FOUNDER-DECISIONS.md`; depois 🤖 alinhar o código ou a SPEC.
**O que custa esquecer:** uma tabela de tradução que ninguém sabe que existe.
Baixo risco hoje, confusão garantida no primeiro leitor novo.

---

## P-203 · 🟢 AutoBrowse fica fora da 077, com gatilho nomeado

**Aberta em:** 17/08/2026 · **Dono:** 🤖 execução, quando o gatilho disparar

A SPEC-077 §13 propõe um laço de auto-melhoria: executa → lê trace → uma
hipótese → repete → juiz decide manter ou reverter.

**Por que ficou fora:** ele exige `ANTHROPIC_API_KEY`, o `browse` CLI (fonte não
auditável — ver [P-205](#p-205)) e scaffolds Stagehand. E, mais importante: 📊 o
loop **já é o que fazemos** nesta operação, com subagentes e juízes críticos, e
com julgamento humano no meio. O gargalo medido não é iterar rápido; é descobrir
o contrato — e isso o `browser-to-api` resolveu.

**O gatilho:** quando existir uma journey que quebre repetidamente por drift de
DOM e o `lab api-infer` **não** resolver — aí o laço passa a valer. Antes disso é
automatizar o que já não é o gargalo.
**O que custa esquecer:** nada hoje. A capacidade de descoberta, que era o
objetivo, já entrou.

---

## P-204 · 🟢 Browserbase Remote: nenhum portal medido exige browser remoto

**Aberta em:** 17/08/2026 · **Dono:** 🧑 Founder, se o gatilho disparar

A 077 §17 propõe `BrowserProvider` com `LocalPlaywright` e `BrowserbaseRemote`.

🔴 **Não há um único portal medido que precise disso.** O bloqueio anti-bot da
Allianz foi resolvido com `--headless=new` (📊 10/08) e User-Agent limpo (📊
12/08). Construir a abstração "para o caso de" é arquitetura especulativa — e
envolveria PII de segurado indo para terceiro, com DPA, retenção e custo.

**O gatilho:** um portal que o Chromium local não consiga acessar **depois** de
esgotados `--headless=new`, User-Agent e proxy. Aí a decisão terá evidência.
**O que custa esquecer:** nada. A abstração custa pouco para adiar e muito para
desfazer errada.

---

## P-205 · 🟠 O `browse` CLI do Browserbase tem fonte inauditável

**Aberta em:** 17/08/2026 · **Dono:** 🤖 registro permanente

📊 Medido em 16/08/2026: `browse@0.9.6` no npm declara MIT, mas o `repository`
do `package.json` aponta para `github.com/browserbase/stagehand/packages/cli` →
**404**, e o ponteiro anterior `github.com/browserbase/cli` → **404**. O
`packages/` do Stagehand não contém `cli`.

Cinco das oito skills do upstream dependem dele, e justamente as duas
capacidades interessantes — abrir CDP e capturar corpos — moram nele.

**Decisão tomada e registrada:** o AutoBrokers **não usa** o `browse` CLI, nem
em laboratório com dado real. O Playwright já faz tudo (📊 confirmado:
`new_cdp_session`, `context.route`, `CDPSession.send`).

**O que destrava:** nada — é registro de decisão, não pendência de trabalho.
**O que custa esquecer:** alguém tentar `npx skills add browserbase/skills` no
futuro achando que é atalho.

---

## P-206 · 🟡 O redator canônico não conhece chassi

**Aberta em:** 17/08/2026 · **Dono:** 🤖 execução, com medição antes

📊 Medido na 077: `redaction.redigir_texto` (SPEC-073) mascara boleto, JWT,
cartão, CNPJ, CPF, e-mail, telefone, placa e CEP — **não chassi**. Dois VIN
reais atravessaram o primeiro conserto do inferidor e só foram pegos pelo
`varredura_de_pii` da SPEC-075, que valida a estrutura do VIN.

O Lab já usa o detector estrito. **Mas `portal_jobs.evidence` continua sendo
redigido pelo redator canônico** — e chassi é dado de segurado que fica no banco.

**Por que não consertei agora:** acrescentar um padrão ao redator de runtime
muda a redação de **toda** evidência de **todos** os portais. Um padrão de 17
caracteres alfanuméricos pode ter falso positivo em id de protocolo ou hash.
Mudança dessas se faz com medição sobre evidência real, não no fim de uma SPEC.

**O que destrava:** 🤖 rodar o padrão do `varredura_de_pii` sobre uma amostra de
`portal_jobs.evidence` real e medir a taxa de falso positivo. Se for zero,
acrescentar.
**O que custa esquecer:** chassi de segurado permanece legível na evidência.
Risco moderado: a tabela é de acesso controlado, não vai para o Git.

---

## P-207 · 🔴 O freio de emergência significa coisas opostas em dois processos

**Aberta em:** 17/08/2026 · **Dono:** 🧑 Founder (uma variável) → 🤖 execução (uma linha)

📊 Medido em 17/08/2026, lendo os dois códigos:

| Processo | `GLOBAL_KILL_SWITCH` ausente | Efeito |
|---|---|---|
| `lib/security/production-gates.ts:27` | **ATIVO** | falha fechado |
| `backend/portal_worker/runtime.py:86` | **INATIVO** | falha aberto |

A mesma variável, dois significados opostos. Pior do que qualquer uma das duas
escolhas isoladas: quem aperta o freio não sabe o que acontece.

E a docstring do Python **afirmava** falhar fechado enquanto o código falhava
aberto — mentira minha, escrita na SPEC-073 e corrigida em 17/08/2026. O teste
`test_spec073_runtime.py` repetia a mesma frase e **nunca testava o caso
ausente**. Ambos consertados.

**Por que não unifiquei já:** se a variável não existir no ambiente do
portal-worker, fechar por padrão faria o worker parar de pegar job no próximo
deploy — derrubando a Cobrança em silêncio. Trocar freio solto por parada muda
não é ganho.

**O que destrava:**
1. 🤖 (feito) `/health` do portal-worker agora expõe `kill_switch_presente`, e
   o worker avisa no boot quando a variável falta.
2. 🧑 Founder: definir `GLOBAL_KILL_SWITCH=false` **explicitamente** no serviço
   `portal-worker` do EasyPanel — mesmo valor de hoje, só que existindo.
3. 🤖 com `kill_switch_presente: true` medido, trocar `return False` por
   `return True` no caso ausente. Uma linha, sem susto.

**O que custa esquecer:** o freio de emergência do produto continua sendo um
botão que pode não estar ligado na roda, sem ninguém saber qual dos dois casos
está vendo.

---

## P-208 · 🟡 Nada no banco liga um Auxiliar ao modelo de Rotina dele

**Aberta em:** 17/08/2026 · **Dono:** 🤖 execução

📊 Medido: `auxiliary_templates` não tem coluna apontando para
`routine_templates`. Pior, os dois usam **nomes diferentes para os mesmos
campos**:

| `auxiliary_templates.default_config` | `routines.config` (o que o motor lê) |
|---|---|
| `portais` | `portal_keys` |
| `exige_aprovacao_para_enviar` | `approval_required` |

Copiar um no outro faz a seleção de seguradoras cair no default **em silêncio**
— `billing_collection.py:385,394` lê os nomes da direita.

Por isso o mapa `ROTINA_DO_AUXILIAR` vive em TypeScript
(`app/dashboard/auxiliares/rotinas/page.tsx`). Enquanto ele existir, **um
Auxiliar novo com rotina própria precisa de uma linha lá**.

**O que destrava:** 🤖 coluna `routine_template_id` em `auxiliary_templates`
(expand-first, idempotente), e unificar os nomes dos campos numa das duas
direções — com backfill, porque há linha semeada em produção usando os nomes
antigos.
**O que custa esquecer:** o próximo Auxiliar com rotina nasce sem porta, do
mesmo jeito que a Cobrança Feita ficou entre 02/08 e 17/08/2026.

---

## P-209 · 🟡 AMANDUS SEGUROS não tem nenhuma conta de portal

**Aberta em:** 17/08/2026 · **Dono:** 🧑 Founder

📊 Medido em 17/08/2026:

| Corretora | Portais saudáveis | WhatsApp | Cobrança Feita | Rotinas |
|---|---|---|---|---|
| AMANDUS SEGUROS | **0** | evolution-go | — | 0 |
| AutoFleet | 8 | evolution-go | — | 0 |
| Resulta Seguros | 8 | evolution-go | `inactive` | 1 |
| AutoBrokers Blueprint Studio | 0 | — | — | 0 |
| AutoBrokers Global Knowledge | 0 | — | — | 0 |

A AMANDUS é a corretora de teste do Founder, e é a única das três "de verdade"
que **não pode** instalar a Cobrança Feita — o conector `insurance_portal` é
satisfeito por ter conta de portal saudável, e ela não tem nenhuma.

**O que destrava:** 🧑 ou cadastrar credencial de seguradora na AMANDUS, ou
fazer os testes na **Resulta**, que já tem os 8 portais, a Cobrança instalada e
a rotina com número de teste e mensagem gravados.
**O que custa esquecer:** o Founder tenta testar na corretora errada e conclui
que o produto não funciona — foi exatamente o que aconteceu com a AutoFleet.

---

## P-211 · 🟡 `live` e `approval` existem no banco e não no seletor

**Aberta em:** 17/08/2026 · **Dono:** 🤖 execução (SPEC-079)

📊 Medido: nenhum dos dois tem motor.

- `approval` — a string `send_billing_whatsapp` aparece **uma vez** em todo o
  repositório: no próprio `insert` que cria o pedido. O endpoint de execução
  (`app/api/vault/approvals/[id]/execute`) tem allowlist e ela não está nela; e
  ele lê `to_number`/`message` escalares, não o array `items` de N segurados.
- `live` — `billing_collection.py:1206-1213` tem dois ramos e os dois só
  acrescentam texto ao relatório. Não existe `else` que envie.

A SPEC-078 tirou os dois do seletor (E.1). Os **valores continuam válidos** no
banco e no normalizador — nada quebra se uma linha antiga os tiver.

**O que destrava:** 🤖 SPEC-079 — o fio entre `billing_collection` e
`platform_outbound.send_to_client_guarded`, que já existe e já é governado
(espaçamento 4–8 min, teto 12/h e **20/dia** para canal novo, janela 08:00–20:00,
domingo bloqueado, freio por corretora, Redis mudo = não envia). 📊 Os 5
inadimplentes/dia da Resulta cabem com folga.
**O que custa esquecer:** a corretora continua sem poder cobrar de verdade — e
é o que ela compra.

---

## P-212 · 🟡 `get_platform_whatsapp_integration` escolhe sem ranquear

**Aberta em:** 17/08/2026 · **Dono:** 🤖 execução

📊 Achado durante o Bloco B: entre duas integrações elegíveis, ela devolve
`valid[0]` — a ordem que o PostgREST entregar. `routine_engine` e
`billing_collection` ranqueiam (`{"auxiliary": 0, "attendance": 1}`); esta não.

Hoje não morde porque nenhuma corretora tem duas elegíveis ao mesmo tempo. Vai
morder quando alguém autorizar o canal `auxiliary` numa corretora que também
tenha `attendance` ativo: o alerta do Vigia pode sair pelo número de cobrança.

**O que destrava:** 🤖 uma linha de `sort` com o mesmo rank.
**O que custa esquecer:** alerta de plataforma saindo pelo número errado, sem
erro nenhum no log — o pior tipo de defeito.

---

## P-213 · 🟢 `notFound()` devolve 200 em página dinâmica

**Aberta em:** 17/08/2026 · **Dono:** 🤖 execução, sem pressa

📊 Medido com `next start` real: `/dashboard/entregas/<id-invalido>` devolve
**200** com o corpo da página 404, em vez de status 404. Controle rodado antes
de atribuir a culpa: `/dashboard/auxiliares/<invalido>`, página que já existia,
se comporta **igual**. É o streaming de Server Component com `force-dynamic` no
Next 15.5.9 — quando o corpo já começou a sair, o status não muda mais.

**Não é vazamento:** o corpo é a página 404, sem título, sem conteúdo, sem link.
E a rota que entrega os **bytes** do artifact não é streamed — devolve 404 de
verdade.

**O que custa esquecer:** confunde monitoração e SEO. Afeta a app inteira, não
só as rotas novas.

---

## P-214 · 🟠 Os boletos no Storage estão prontos para purgar, e a purga está DESLIGADA

**Aberta em:** 17/08/2026 · **Dono:** 🧑 Founder (o prazo é decisão dele)

📊 Medido em 17/08/2026 (`storage.objects`, projeto dcajcvlzcjbmyapmklil):

```text
portal-evidence   62 objetos · 5977 kB · mais antigo 11/07/2026
                  5 com mais de 30 dias · 0 com mais de 60 · 0 com 90
chat-docs         30 objetos · 26 com mais de 30 dias    (fora do escopo desta SPEC)
chat-media        26 objetos · 24 com mais de 30 dias    (idem)
```

São **boletos de terceiros** — dado financeiro de segurado — guardados desde
julho **sem nenhuma rotina de descarte**. A migration `20260708_01` criou o
bucket privado e parou ali: privado resolve *quem lê*, não resolve *por quanto
tempo existe*.

A SPEC-078 F.7 **não apagou nada** (§15). Ficou pronto e desligado:

| Peça | Onde | Estado |
|---|---|---|
| Política escrita | `billing_collection.py`, cabeçalho da seção F.7 | ✅ |
| Contagem por idade, por corretora | `public.portal_evidence_por_idade(dias)` — migration `20260817_04` | ✅ (só leitura) |
| Leitor em Python | `billing_collection.contar_evidencias_por_idade()` | ✅ |
| Purga | `billing_collection.purgar_evidencias_antigas()` | ✅ escrita, **DESLIGADA** |

Três travas, e as três precisam ceder ao mesmo tempo para um único byte sair:
`PORTAL_EVIDENCE_PURGE_ENABLED` ligado (padrão: ausente = não) · `dry_run=False`
explícito (padrão: `True`) · prazo positivo. Sem as três, a função devolve
**o que apagaria** e não toca em nada.

**O que destrava:** 🧑 duas decisões do Founder, nesta ordem:
1. **o prazo.** A sugestão escrita é 90 dias — o boleto vence em ~30 e a
   discussão sobre uma cobrança morre em ~60; 90 dá folga sem virar arquivo
   morto. Ajustável por `PORTAL_EVIDENCE_RETENTION_DAYS`.
2. **ligar**, com `PORTAL_EVIDENCE_PURGE_ENABLED=true`, e chamar a purga de
   algum lugar — 📊 hoje **ninguém a chama**, nem desligada. Ela não tem
   agendador: é função, não rotina. Pendura-se no tick de retenção que já existe
   em `routine_engine.routine_scheduler_loop` (o mesmo que apaga `routine_runs`
   com mais de 90 dias, 1x/dia) ou numa rotina de plataforma.

**O que custa esquecer:** dado financeiro de terceiro acumulando sem prazo de
descarte, num bucket que só cresce. Não é um risco de vazamento — é um risco de
**guarda indevida**: quando alguém perguntar por que a corretora ainda tem o
boleto de um segurado que saiu da carteira em julho, a resposta hoje é "porque
ninguém apagou".

---

## P-215 · 🔴 `editar()` grava uma paleta que DERRUBA o render, e ninguém viu

**Aberta em:** 18/08/2026 (SPEC-081 §Bloco E) · **Dono:** 🤖 execução
**Contornada no dado, NÃO corrigida no código.**

📊 Medido nesta máquina, antes de qualquer escrita em produção:

```text
render_html(brand=<paleta como capture.editar() a grava>)
    -> KeyError: 'typography'
```

A cadeia, arquivo por arquivo:

```text
capture.py:508-513   editar() grava a paleta com SEIS chaves:
                     primary · accent · scales · themes · audit · origin
render.py:41-42      if paleta.get("themes"): return paleta   <- verbatim
system.py:298        for chave, valor in sistema["typography"].items()
```

`_sistema_da_marca` documenta o contrato: *"o snapshot já traz o sistema
pronto"*. Quem o descumpre é `editar()` — e `_propor_visual` (capture.py:335),
que monta a mesma paleta de seis chaves na captura automática.

**Por que nunca apareceu:** 📊 até 18/08 os 40 artifacts em produção eram
`is_fallback=true`, e o ramo de fallback (`capture.py:556`) devolve
`"palette": sistema` — a saída INTEIRA de `build_design_system`, com
`typography`. **O defeito só é alcançável por uma corretora que tem marca, e
não havia nenhuma.** A primeira a ter foi a Resulta, na véspera de uma
apresentação do Auxiliar de Cobrança.

**O contorno aplicado:** `backend/scripts/instalar_marca_resulta.py` grava a
paleta com as SETE chaves. O dado no banco está correto hoje.

**Por que continua pendente:** o contorno é do dado, não do código. 🔴 **Uma
chamada a `capture.editar()` ou a `capture.capturar()` pela tela da corretora
regrava a paleta de seis chaves e volta a derrubar o render de todas as peças
daquela corretora.** `capture.py` está congelado pela SPEC-081 §G.1 até a
apresentação; depois dela, o conserto é de uma linha em `capture.py:508-513`
(acrescentar `"typography": sistema["typography"]`), com o mesmo acréscimo em
`_propor_visual`.

**O que destrava:** 🤖 passada a apresentação, descongelar `capture.py` e pôr a
sétima chave nos dois lugares. Guardado por
`npm run test:resulta-tem-marca` (asserção "_paleta_completa inclui
'typography'" + o CONTROLE que prova o `KeyError`).

**O que custa esquecer:** a próxima corretora que montar a identidade pela tela
recebe todas as peças quebradas, com exceção, e o defeito parecerá vir do
Artifact Hub — que está certo.

---

## P-216 · 🟡 O painel de marca salvou seis campos VAZIOS e os congelou

**Aberta em:** 18/08/2026 · **Dono:** 🤖 execução

📊 Medido em 18/08/2026 (produção, Resulta):

```sql
select field_path, human_edited, source_detail from brand_field_provenance
 where company_id = '04b5cdbc-04cd-4ddf-8e4b-f43efb062fab';
-- 11 linhas human_edited=true, "editado no painel da corretora", 17/08
-- entre elas: tagline · legal_name · susep_code · mission · about_md ·
--             service_area
```

E os valores desses seis campos em `brand_profiles` são **NULL ou vazios**.

A corretora abriu a tela em 17/08 e salvou o formulário em branco.
`capture.editar()` (capture.py:521-533) grava procedência `human_edited=true`
para **todo** campo do patch, sem olhar se veio valor — e `_protegidos`
(capture.py:118) faz a recaptura **pular** todo campo assim marcado.

**Resultado:** aqueles seis campos estão permanentemente invisíveis para a
captura automática. O site da Resulta pode ter tagline e SUSEP; o robô nunca
mais vai buscá-los.

**O que destrava:** 🤖 `editar()` só deve marcar `human_edited` para campo com
valor não vazio — "apaguei de propósito" é uma decisão diferente de "não
preenchi", e hoje as duas gravam a mesma linha. Enquanto não, dá para soltar
caso a caso apagando a linha de procedência.

**O que custa esquecer:** a corretora nunca entende por que a captura "não acha
nada" justamente nos campos que ela deixou em branco esperando que o robô
preenchesse.

---

## P-217 · 🟢 A logo mora em `storage_ref`, que promete um caminho de bucket

**Aberta em:** 18/08/2026 (SPEC-081 §E.2, D9) · **Dono:** 🤖 execução, sem pressa

📊 `brand_assets.storage_ref` é `text NOT NULL` e o comentário da migration
(`20260725_05:43`) diz *"caminho canônico bucket/path (SPEC-054)"*. O que está
gravado lá para a Resulta é um data URI de 6.282 caracteres.

**A coluna já não guardava o que o nome promete antes desta SPEC:** 📊 nenhum
código do repositório sobe logo para o MinIO, e `capture.py:300` grava ali a
URL externa do site com o comentário *"reescrito ao subir p/ storage"* — uma
reescrita nunca implementada. `render.py:70` aceita os três formatos
(`data_uri` → `public_url` → `storage_ref`), então tudo funciona.

**O que destrava:** 🤖 subir o asset ao bucket e passar a gravar
`bucket/path`, OU renomear a coluna para o que ela de fato guarda. O
CLAUDE.md §12.1 manda consertar o campo, não o texto.

**O que custa esquecer:** 4,6 KB por corretora dentro de uma coluna de texto
que entra em todo `select *` de perfil de marca. Hoje é irrelevante; com
centenas de corretoras, não.

---

## P-218 · 🟡 SUSEP, razão social e tagline da Resulta seguem em branco de propósito

**Aberta em:** 18/08/2026 (SPEC-081 §Bloco E) · **Dono:** 🧑 Founder

📊 `backend/tools/gerar_visual_acceptance_pack.py:62-96` traz
`susep_code="20.2185.4"`, `legal_name="Resulta Corretora de Seguros Ltda."` e
uma tagline. 💭 São valores de um pack de **aceite visual** — nunca foram
conferidos com a corretora.

O §Bloco E **não os gravou**. 📊 `blocks.py:382-383` imprime o SUSEP no rodapé
de **toda** peça: um número de registro não conferido, impresso num documento
que vai ao cliente, é pior que rodapé sem SUSEP. O bloco é guardado por `if`,
então o rodapé simplesmente omite.

**O que destrava:** 🧑 o Founder confirmar os três valores com a Resulta. Depois
disso é uma chamada de `editar()` ou três linhas no painel.

**O que custa esquecer:** as peças saem com a marca certa e sem o registro
profissional que dá autoridade ao documento.

---

## P-219 · 🟡 A dedup de entrega existe e está DESLIGADA no modo teste

**Aberta em:** 19/08/2026 (SPEC-078, T3) · **Dono:** 🧑 Founder

📊 Até hoje `billing_sent_log` estava vazia e `_record_sent` /
`_already_sent_recibos` estavam **definidas e nunca chamadas**
(`backend/app/services/billing_collection.py`). A regra *"cada parcela em atraso
é enviada 1x"* não existia na prática.

Agora as duas metades estão ligadas no caminho de entrega e a decisão mora num
lugar só: `dedup_de_envio_ativa(send_mode)`. `live` e `approval` deduplicam
sempre. **`test` não deduplica por padrão** — é a decisão de 17/08/2026 (nota
88, registrada no próprio código): em teste o destino é o número da própria
corretora e o que se quer é repetir. 📊 E a chave do índice único
(`company_id, recibo, send_mode`) não inclui o destino, então trocar o número de
teste não destravaria os mesmos boletos.

⚠️ Hoje o **único** caminho de entrega que roda é o do modo teste — `live` está
barrado por `customer_send_allowed` e por blocker explícito. Enquanto isso não
mudar, `billing_sent_log` continua vazia com o padrão atual.

**O que destrava:** 🧑 o Founder decidir se o modo teste passa a deduplicar.
`BILLING_DEDUP_TEST_ENABLED=1` liga sem tocar em código, e há teste dos dois
lados (`backend/tests/test_a_sessao_caida_volta_e_o_aviso_diz_a_verdade.py`,
bloco [4]).

**O que custa esquecer:** com a flag **ligada**, uma segunda execução no mesmo
dia não entrega nada — o que quebra uma demonstração feita depois da execução
agendada. Com ela **desligada**, a corretora recebe os mesmos boletos todo dia,
e no dia em que `live` for homologado o segurado passa a receber também.

---

## P-220 · A idade do aparelho saiu da coleta, e a cobertura depende dela
**Quem:** 🤖 execução · **Aberta em:** 19/08/2026

📊 Até 18/08 o subserviço `eletrodomesticos` da Allianz residencial exigia
`aparelho_marca_modelo` e `aparelho_idade`. Ao mapear a URA real da máquina de
lavar, o slot único virou dois (`aparelho_marca` + `aparelho_modelo`, porque a
URA pergunta em duas telas) — e **a idade saiu da lista**, porque a URA
observada nunca a pergunta.

🔴 Mas a idade não deixou de importar: a própria Allianz declara na tela que o
serviço vale para *"aparelhos/equipamentos com até 10 anos de fabricação"*. Sem
coletá-la, a atendente não tem como avisar o segurado de que o chamado pode ser
recusado no local — e quem descobre é o técnico, na casa dele.

**O que destrava:** 🤖 decidir se `aparelho_idade` volta como slot **de aviso**
(coletado e mostrado, sem bloquear) em vez de slot obrigatório. Obrigatório
bloquearia acionamentos por um dado que a URA não pede.

**O que custa esquecer:** um chamado aberto para um aparelho de 12 anos, técnico
deslocado, recusa no local, e a corretora explicando o que o sistema sabia.

---

## P-221 · `unknown_step_policy` é configuração morta em 14 corredores
**Quem:** 🤖 execução · **Aberta em:** 19/08/2026

📊 A chave está declarada em 14 playbooks (`pause_and_handoff` nos residenciais,
`adaptive_then_handoff` nos de auto) e **nenhuma linha de código a lê** —
`grep -rn unknown_step_policy app/` só acha as declarações.

Ela enganou a própria investigação de 19/08: a divisão limpa entre auto e
residencial parecia explicar por que os corredores residenciais travavam. Não
era ela. E **dois testes a abençoavam** (`test_corredor_residencial_yelum`,
`test_golden_do_eletricista`), dando a quem lesse a impressão de uma proteção
que não existia. As duas asserções já foram migradas para o que o produto
realmente lê (`finalize_anchors` → `detect_finalize_anchor`).

**O que destrava:** 🤖 remover a chave dos 14 playbooks, ou dar-lhe leitor. A
remoção é mecânica; foi adiada para não misturar diff cosmético com os consertos
de 19/08 no mesmo commit.

**O que custa esquecer:** o próximo a ler o arquivo confia nela de novo.

---

## P-222 · Tela de confirmação não mapeada não é pega pelo filtro de reversível
**Quem:** 🤖 execução · **Aberta em:** 19/08/2026

O conserto de 19/08 faz o cérebro assumir toda tela **reversível** cujo dado
falta, e parar nas **irreversíveis**. O discriminador é `detect_finalize_anchor`,
que lê os `finalize_anchors` do próprio corredor.

⚠️ Consequência: uma tela de confirmação que aquele corredor **ainda não mapeou**
não é reconhecida como irreversível, e o cérebro assume. A segunda camada existe
— o `finalize_rule` do prompt manda responder `NAO_SEI` diante de qualquer
confirmação quando o modo é teste — mas ela é do modelo, não determinística.

📊 Exemplo real já visível: o RESUMO do fluxo de eletrodoméstico da Allianz
termina em *"Podemos confirmar?"*, e a âncora daquele corredor é
`podemos confirmar o atendimento` — mais específica. Ela **não casa**.

**O que destrava:** 🤖 acrescentar `podemos confirmar\??$` (ou equivalente) aos
`finalize_anchors` da família Allianz, medindo contra o acervo antes.

**O que custa esquecer:** o freio de finalização também depende dessa mesma
âncora — se ela não casa, quem segura o "abrir de verdade" é só o prompt.

---

## SPEC-083 — A RÉGUA DO CORREDOR · pendências abertas em 21/08/2026

> Cada entrada diz **o que destrava**, **de quem é** (🧑 Founder ou 🤖 execução) e
> **o que custa esquecer**. Nada sai desta lista sem estar feito ou sem uma
> decisão registrada.

### 🔴 P-083-1 · O corpus de 5 sessões não cobre 4–6 serviços por corredor · 🤖

📊 **Este é o número que governa o inventário inteiro.** Rodada a régua nas 62
rotas em 21/08/2026: **4 pontuam · 12 `SEM_CORPUS` · 46 `NAO_RESPONDE`**.

A causa não é qualidade de corredor. É amostra: o corpus guarda **5 sessões por
`(seguradora, ramo)`** e cada corredor tem **4 a 6 serviços**. Depois do filtro
por serviço (SPEC-084 §5.1①), a maioria das rotas fica com **0 ou 1 sessão** — e
com uma sessão não há telas suficientes para o eixo B passar do portão (8).

📊 Exemplo medido: `allianz × residencial × maquina_de_lavar` tira **64/96** com
`AMOSTRA: 1 de 140 sessões`. Os 2 pontos de *"≥2 sessões distintas"* e os 3 de
*"o handoff casa tela real"* são perdidos **por amostragem**, não por defeito.

**O que destrava:** subir o teto de sessões por `(seguradora, ramo)` até que cada
serviço com evidência no acervo tenha ≥2 sessões próprias, respeitando o teto de
500 KB por arquivo. 🔴 **É decisão da SPEC-084**, porque muda o denominador de
todas as notas — e a 084 é quem precisa das rotas medidas.

**O que custa esquecer:** a 084 leria 46 `NAO_RESPONDE` como *"46 corredores a
reescrever"* quando boa parte é *"46 rotas sem amostra"*. São trabalhos opostos.

### 🔴 P-083-2 · 937 respostas de botão estão vazias e são irrecuperáveis · 🤖

📊 Medido: `msg_type='button_reply'` com `text` vazio — yelum 370 · hdi 263 ·
porto 167 · bradesco 62 · azul 54 · mapfre 8 · zurich 8 · tokio 5.
`interactive` guardou só as **chaves** (`selectedButtonID` entre elas), sem os
valores: **`recuperavel_por_title` = 0 em todas as dez.**

**A escolha do segurado não está no banco.** É a maior causa isolada de perda do
nível 1 das duas cascatas (ramo e serviço).

**O que destrava:** corrigir o ingestor para gravar `selectedButtonID`.
🔴 **E o controle que prova o conserto:** a yelum tem 13 sessões longas
indefinidas hoje — o número tem de cair depois dele.

**O que custa esquecer:** toda medição de demanda e de ramo roda sobre uma URA
cujas respostas foram apagadas na ingestão.

### 🔴 P-083-3 · `templatize` mata a captura, e o conserto mora no corpus · 🤖

📊 Medido com o CONTROLE verde (`marcas_de_corretora()` = 8):

```
"...o numero de protocolo e 52955490"   ->  {CEP}       a captura MORRE
"...os 4 ultimos digitos ... *4743*"    ->  {SEGREDO}   a captura MORRE
```

O gerador de corpus reinjeta o valor **verificando pelo motor** (CA-062). Mas o
`templatize` continua matando a captura para **todos os outros consumidores** —
o Tecelão entre eles, que escreve `ura_maps`.

**O que destrava:** o terceiro modo `templatize(..., corpus_de_ura=True)` pelo
`_vale_neste_modo` que já existe (SPEC-084 §2.5.1.3). 🔴 **Não foi feito nesta
SPEC** porque `templatize` tem 📊 8 consumidores de produção e ~140 asserções, e
a SPEC-083 não altera o mascarador do Atlas.

**O que custa esquecer:** `ura_maps` pode estar gravando `{CEP}` onde havia
protocolo, e ninguém veria — vira só um mapa com menos informação.

### 🔴 P-083-4 · O `_norm` do motor não remove caracteres invisíveis · 🤖

📊 `combustí<U+00AD>vel` (soft hyphen) faz `combust[íi]vel` **falhar**. 3 eventos /
2 sessões / 1 seguradora (zurich); mais 4 eventos com `U+200B`.

O gerador de corpus os limpa **antes** de chamar o `_norm`. O motor, não.

**O que destrava:** acrescentar `U+00AD`, `U+200B`, `U+200C`, `U+200D`, `U+FEFF`
e `U+2060` ao `_norm` de `corridor_playbooks.py`. 🔴 **Fora do escopo da SPEC-083**
— ela não altera corredor. Entrega da SPEC-084.

**O que custa esquecer:** uma âncora de pane seca perde 2 das 14 sessões da
zurich em silêncio, e a perda vira só um número menor.

### ⚠️ P-083-5 · Três padrões de ramo da allianz casavam ZERO · 🤖 (CORRIGIDO, registrado)

📊 `placa do seu ve[íi]culo`, `identifiquei em seu cadastro a placa` e
`guincho consegue acessar` → **0 sessões cada**. Os textos reais são
`placa do veículo` e `o REBOQUE consegue acessar`.

Substituídos por `confirme o ve[ii]culo para atendimento` — 📊 39 sessões, **36 de
38** de recall em auto, **0 de 76** de falso positivo em residencial.

**Fica registrado** porque é a terceira geração do defeito `numero_residencia`:
âncora escrita de cabeça, três vezes na mesma linha.

### ⚠️ P-083-6 · A tokio tem um TERCEIRO ramo: CONDOMÍNIO · 🧑 Founder

📊 `menu de serviços do seguro CONDOMÍNIO 🏘️` — 2 sessões. Não há playbook
`tokio-condominio`; o corpus foi gerado (16 telas) e **não tem consumidor**.

**O que destrava:** decisão do Founder — vira ramo do produto, ou fica fora?
🔴 Não construído: é ramo novo, fora do escopo das duas SPECs.

**O que custa esquecer:** 2 sessões caem em `indefinido` por tabela incompleta,
e ninguém sabe se é defeito ou escopo.

### ⚠️ P-083-7 · Serviços que a URA nomeia e o código não tem · 🧑 Founder

📊 Achados pelo padrão-ouro, com o rótulo literal da seguradora:
`consulta veterinária` · `pet assistance` · `limpeza de caixa d'água` · `limpeza`
· `dedetização` · `ar condicionado` · `telhado` · `chuveiro`.

E o maior de todos: 📊 **socorro mecânico em 38 sessões** (yelum 21 · zurich 9 ·
hdi 8) e `subservice_supported()` devolve **False**.

**O que destrava:** decisão de escopo — quais viram subserviço.
**O que custa esquecer:** o produto recusa um serviço que os clientes pedem e a
URA atende.

### ⚠️ P-083-8 · As 8 rotas indistinguíveis — 2 resolvidas, 6 em aberto · 🤖

```
bradesco  guincho × bateria   ✅ RESOLVIDA  "me conta o que aconteceu:
                                 1 - estacionado e nao liga (BATERIA)
                                 2 - andando e parou (GUINCHO)"   📊 4 sessoes
zurich    guincho × bateria   ⚠️ IDENTIFICADA, NAO ESTABELECIDA — a tela
                                 "O que houve? *1* - Problema de Bateria" existe
                                 em 📊 **1 sessao**. Precisa de >=1 acionamento
                                 observado para confirmar.
mapfre    4 rotas             🔴 SEM SINAL NA URA — 📊 ninguem escolheu
                                 "Assistencia 24H" em 13 sessoes. A tela
                                 posterior a escolha NAO EXISTE no acervo.
```

**O que destrava:** coleta dirigida — 1 acionamento de bateria na zurich, 1 de
Assistência 24H na mapfre.
**O que custa esquecer:** escrever a rota do guincho nessas 6 **abre o chamado
errado**. O corredor não trava: responde com confiança a coisa errada.

### ⚠️ P-083-9 · Duplicatas exatas na ingestão · 🤖

📊 tokio: **36,3% dos eventos são duplicatas exatas** (144 excedentes em 397, 27
sessões). E `90951801` (allianz) tem **100%** dos eventos duplicados;
`eade0321` (allianz) idem.

O corpus deduplica por `(session_id, _norm(text))`, então o `.jsonl` está limpo.
🔴 **Mas o corte "≥20 eventos `in`" que separa `SESSOES_CURTAS` de
`RAMO_NAO_CLASSIFICA` roda sobre a contagem BRUTA** — e ela está inflada ~2× em
boa parte do acervo.

**O que destrava:** achar a causa (reingestão? webhook duplo? a tabela
`observed_events_copias_removidas_20260728` mal aplicada?).
**O que custa esquecer:** o corte peneira sessões de 10 telas reais como se
fossem de 20.

### ⚠️ P-083-10 · 7 sessões da hdi com `direction` invertida · 🤖

📊 7 sessões / 16 eventos com `direction='in'` começando por
`{NOME} - resulta seguros` ou `{NOME} - autofleet seguros` — mensagem assinada
**pela corretora**, rotulada como vinda **da seguradora**.

Excluídas do corpus por `Z.direcao_invertida()`. 🔴 **Não é a zona `CORRETORA`**
(que foi eliminada por medição) — é **dado errado**.

⚠️ E o cuidado que a regra carrega: a URA da tokio **saúda a corretora pelo nome**
(`"olá, {NOME} - {CORRETORA} seguros! digite o cpf"`) e aquilo **É tela de URA** —
📊 a tela do CPF de 8 sessões. O que distingue é a mensagem ser **só** a
assinatura, sem tela em volta.

### ⚠️ P-083-11 · 493 eventos `in` sem `session_id` · 🤖

📊 3,0% do acervo `in` (allianz 296 · porto 116 · hdi 72 · zurich 1) — mais 359
eventos `out`. **Sem sessão não há "antes/depois da transferência"**, então eles
ficam fora de toda classificação.

📊 E há fala humana entre eles: uma marca de fronteira da porto tem `session_id`
nulo. Sem a zona `ORFAO`, ela entraria como URA.

**O que custa esquecer:** os 520 eventos órfãos da allianz explicam o
off-by-one sistemático que apareceu em seis números da SPEC-083 (16→15, 38→37,
77→76, 39→38).

### ⚠️ P-083-12 · O GLOSSÁRIO não define `rota` · 🧑 Founder

📊 `grep -ci "rota" docs/canon/GLOSSARIO.md` → **0**. E `subcorredor`, `âncora` e
`subserviço` também não estão lá. A SPEC-083 §0 manda conferir os sete termo a
termo, com o glossário vencendo.

**O que destrava:** a escrita canônica — e ela é do Founder, não da execução
(CA-061: *"um glossário é autoridade justamente porque não é escrito de passagem
por quem precisa do termo"*).

### ⚠️ P-083-13 · A fronteira não é monotônica · 🤖

📊 Achado pelo JUIZ DE TRIAGEM: em **4 de 9** sessões sujas a URA **volta** depois
do humano — a pesquisa NPS da porto, o `Termo de Privacidade` da allianz.

A regra atual (*"tudo depois da fronteira é HUMANO"*) é conservadora e **joga
fora telas de URA legítimas** — inclusive as duas telas de NPS da porto, que não
estão mapeadas em lugar nenhum.

**O que destrava:** uma marca de RETORNO à URA, minerada com controle.
**O que custa esquecer:** perde-se amostra de URA sem que ninguém veja — e o
custo aparece como nota mais baixa, não como defeito.

### 🔴 P-083-14 · A órfã funcional de `7ac3c101` pode ser DUAS, não uma · 🤖

📊 O JUIZ DE TRIAGEM, lendo o `ura_maps` ativo (mapa `80b6a5d6`, `status=active`),
achou **dois** nós com 100% das opções em `gap` na sessão da régua:

```
c650769dae3f   2 de 2 opcoes sem destino   "Agendamento para: *Quinta-feira {DATA}*…"
addf8cfd3605  15 de 15 opcoes sem destino   "Selecione o eletrodomestico que precisa
                                             de conserto? *1 -* Geladeira … *15 -* Outros"
```

A SPEC-083 §4.2 nomeia só o primeiro. O replay desta SPEC também acha só um —
porque o segundo **casa um passo** (`match_ura_step` responde), e o critério do
`ura_maps` é outro (opções sem destino).

⚠️ **São dois critérios diferentes de "órfã", e os dois são legítimos.**
**O que destrava:** a SPEC-084 decidir qual dos dois governa o mapeamento.
**O que custa esquecer:** mapear só `c650769dae3f` deixa a rota quebrada no passo
seguinte — 15 opções de eletrodoméstico sem destino.

---

## SPEC-084 BLOCO 1 — o que ficou pronto e desligado, e o que ficou aberto

> Escritas em 22/08/2026, ao fim do BLOCO 1. Cada uma diz **o que destrava**,
> **de quem é** e **o que custa esquecer**.

### P-084-1 🔴 `azul × pneu` e `azul × vidros` — teclas mortas desde 26/12/2025 · 🧑

📊 O menu da azul migrou em **07/04/2026** (o corte é o mesmo dia em três telas
independentes — é migração de bot, não ambiguidade). Na variante viva as opções
são `Guincho (reboque) · Bateria · Chaveiro para veículo · Técnico · Táxi`.
**Não existe "Troca de pneu" e não existe "vidro".**

- `pneu` mandava `"3"` numa lista de rótulos → rejeitado.
- `_ativar_vidros(azul, menu_value="5")` apontava para tecla morta.

Os dois foram **desligados**: `subservice_supported` devolve `False` e o caso vai
a handoff. 🔴 **O total de rotas caiu de 62 para 61** — não é redução silenciosa
de escopo: é uma rota que a seguradora deixou de oferecer neste menu.

**O que destrava:** uma captura de onde pneu e vidro entram na azul de 2026.
Candidato medido para pneu: a tecla `Técnico`. **Zero evidência** — não se declara.
**O que custa esquecer:** o segurado pede troca de pneu na azul e recebe handoff
sem ninguém saber que existia uma tecla certa.

### P-084-2 🔴 MAPFRE — são DOIS bots, e o rótulo da tecla é diferente · 🧑

```
BOT DO SEGURADO  ->  a tecla se chama "Assistência 24H"
BOT DO CORRETOR  ->  a tecla se chama "Assistência"   (entra por código de corretor)
```

📊 `subservice_menu_map` declara o primeiro para as 4 rotas. **Para qual dos dois
a corretora escreve não está no acervo.** E 📊 **0 de 6 sessões** da mapfre
abriram assistência: todas foram sinistro, carro reserva ou timeout.

E falta a tela que separa guincho de bateria/pneu/chaveiro — 📊 ela **não existe
no acervo**, e sem ela as 4 rotas mapeiam para um rótulo só.

**O que destrava:** 1 acionamento real no bot que a corretora usa, escolhendo
"Assistência 24H" e seguindo até o fim. Destrava 4 rotas de uma vez.
**O que custa esquecer:** 4 rotas indistinguíveis, e `regras_para_o_cliente` /
`expectativa_do_desfecho` vazios (não escritos de propósito — 💭 seria inventar).

### P-084-3 🔴 MAPFRE — `codigo_corretor` é slot de CONFIGURAÇÃO, não de coleta · 🧑

📊 "Para continuar, digite o seu *código de corretor*. *Lembrando:* … 2 até 6
números." Sem ele o canal do corretor não abre. **Não é dado do segurado** — é da
corretora, e precisa de um lugar na configuração do tenant.

### P-084-4 `nao_entendi` da porto — noop é o menos pior, não o certo · 🤖

📊 10 msgs / 6 sessões. Na porto, "Não entendi a sua resposta" é a URA
**esperando**: silêncio vira timeout. O certo é **reenviar a última resposta**, e
isso é comportamento de **MOTOR**, não de âncora — não existe hoje.
Mesma família: `resposta_recusada` da yelum/hdi ("Sua resposta está diferente do
que solicitamos" = a NOSSA resposta foi recusada) precisa de **contador**: duas
seguidas → `needs_human`.
**O que custa esquecer:** o corredor espera calado até o timeout, e o run fica
aberto para sempre.

### P-084-5 🔴 `encerrada_por_inatividade` precisa de ESTADO, não de `noop` · 🤖

📊 yelum 2 telas / 7 sessões · hdi 1 / 2. **A URA DESLIGOU.** Um corredor que
trata isso como "mensagem informativa" fica *monitorando* uma conversa que não
existe mais — é a família dos `corridor_runs` abandonados.
**O que destrava:** um `terminal: True` no contrato de `ura_steps`, ou entrada em
`handoff_triggers`. É **mudança de contrato**, e não se faz de passagem.

### P-084-6 `escolher_veiculo` / `escolher_endereco` — a lista com entradas duplicadas · 🤖

📊 porto: 3 telas, e **as três têm entradas duplicadas** (mesmo modelo, ano e
placa MASCARADA em posições diferentes). Posição fixa é impossível; casar por
placa é ambíguo com máscara. Ficou `fallback_adaptive` + handoff.
📊 Mesmo problema no endereço: 6 telas, uma com dois endereços quase idênticos
(`SL 330 CAMP A` × `Sl 330 Camp A`).
**O que destrava:** uma captura NÃO mascarada dessa tela, ou uma regra do produto
sobre placas repetidas na apólice.

### P-084-7 🔴 A régua chama `ANCORA_SUSPEITA` o que é MÁSCARA DE CORPUS · 🤖

**Dois coletores independentes acharam o mesmo, medindo de formas diferentes.**

📊 A azul: `--conferir-ancoras-de-desfecho` diz `0 c/ protocolo · 0/9 · 🟠`.
A MESMA âncora, sobre o acervo CRU: **11 msgs · 10 de 19 sessões ✅**.
O desfecho é `"Aqui está seu protocolo de atendimento 👇 1-128312189741"`, e o
gerador de corpus mascara o número → sobra `1-{NUMERO}`, que não tem dígitos para
capturar. 📊 Idem porto: o grupo exige 6+ caracteres e sobra só o `1-`.

🔴 **Atinge as CINCO linhas 🟠 de uma vez** (azul, hdi-residencial, mapfre,
porto-auto, porto-residencial). Enquanto durar, `ANCORA_SUSPEITA` não separa
"âncora quebrada" de "número mascarado".
**O que destrava:** ou o mascarador preserva um protocolo sintético com o mesmo
formato, ou `conferir_ancoras_de_desfecho` reporta um quarto estado —
🔵 `DESFECHO_MASCARADO`.
**O que custa esquecer:** cinco "defeitos de âncora" na fila que são defeito do
MEDIDOR, e trabalho de coleta pedido sem necessidade.

### P-084-8 🔴 O AGENDAMENTO DA PORTO NUNCA É CAPTURADO · 🤖

Este **não** é artefato de máscara. Testado com texto real, pelo motor:

```
"...deve chegar ao seu endereço no dia 25/08/2026, entre 13h00 e 14h00..."  -> {} 🔴
"...previsto para ser realizado no dia 25/08/2026, entre 14h00 e 14h30..."  -> {} 🔴
"...previsto para ser realizado *hoje*, em até 60 minutos."   -> {eta_minutes: 60} ✅
```

`capture_anchors.schedule` exige a data **colada** em "para"; a porto escreve três
palavras no meio. 📊 5 telas residenciais (4 sessões) + 1 auto — **todas são a
última mensagem útil do acionamento**. Hoje o segurado recebe o protocolo **sem
saber quando o prestador vem**, que é a única coisa que ele quer saber.
É literalmente o defeito que o comentário de `schedule_agendado` diz ter
consertado na Allianz, aberto na porto.
⚠️ E `extract_capture_anchors` roda **sem DOTALL**: a âncora nova precisa de
`[^\n]{0,20}`, nunca `.{0,20}`.

### P-084-9 A LISTA DE OPÇÕES CHEGA EM BOLHAS SEPARADAS · 🤖

📊 yelum: `"Encontramos mais de uma apólice…"` seguida, **em mensagens separadas**,
de `"*Automóvel* 1 - {PLACA}"` e `"*Residencial* 2 - …"`.
📊 azul: `endereco_digite` (a MESMA bolha) serve ORIGEM e DESTINO na mesma sessão;
a única marca que separa é a bolha `"Agora, vamos falar sobre o *endereço de
destino*"` que precede a segunda — **e isso exige ESTADO**, enquanto
`match_ura_step` decide por mensagem.
**O que destrava:** o motor saber montar a lista a partir de bolhas separadas, e
saber que um passo já foi visto. Nenhum dos dois existe.

### P-084-10 Os SERVIÇOS que a URA oferece e o código não tem · 🧑

📊 Medidos, com rótulo capturado e **zero** fluxo observado depois dele:

| seguradora | serviço | evidência |
|---|---|---|
| porto auto | **Táxi** | rótulo em 13/13 menus · 37 msgs · 13 ses · fluxo completo em 2 |
| porto auto | **Técnico** | rótulo em 10/13 · **2 sessões inteiras até o protocolo** |
| porto auto | **Bateria nova** | submenu em 5 ses · 1 completa · 🔴 tem PREÇO ao cliente |
| porto resid | **Chaveiro residencial** | 4/4 menus · **1 sessão COMPLETA até o protocolo** |
| porto resid | Chuveiro · Kit instalação · Reparo em telha · Limpeza de calhas | rótulo em 4/4, **0 entradas** |
| allianz resid | Dedetização · Limpeza do Imóvel · Caixa de água · Telhas · Cobertura provisória · Consulta veterinária | 📊 2 telas / **21 sessões** |
| yelum/hdi | **socorro_mecanico** | 📊 7 escolhido / 70 no cardápio · 6 sessões com protocolo |

🔴 **`porto × residencial × chaveiro` é o mais gritante:** existe uma rota-ouro
inteira, com dois submenus mapeados, regra de cobertura própria e desfecho com
protocolo — e `subservice_supported()` devolve **False**. É o caso do
`desentupimento` da Allianz outra vez: *"um mesmo trabalho existir num corredor e
não no outro não é escopo: é esquecimento."*

⚠️ E `socorro_mecanico` **não é botão de menu** — é o nome que a URA dá ao
DESFECHO quando decide mandar mecânico em vez de reboque. Ligar exige uma função
por seguradora (molde do `_ativar_vidros`), nunca em `_AUTO_SUBSERVICES`, que
copia para as **onze**.

**O que custa esquecer:** trabalho que a seguradora faz, o cliente pede, e o
produto recusa por não ter uma linha declarada.

### P-084-11 `bateria` e `socorro_mecanico` são o mesmo trabalho? · 🧑

📊 Nas 6 sessões medidas os dois chegam pelo MESMO caminho
(`Pane ou Defeito` → `pane_detalhe` → `descreva_situacao`) e recebem a MESMA tela
("recarga da sua bateria"). O que os separa é o rótulo que a URA escreve no
resumo. **Ou são um só subserviço com dois desfechos, ou `bateria` é caso
particular de `socorro_mecanico`.** Decisão de produto.

### P-084-12 🔴 A TELA QUE PEDE DINHEIRO precisa de trava própria · 🧑🤖

Medidas, e a maioria é `noop` hoje porque não tem botão:

- yelum/hdi auto: *"Caso seja necessário a compra de uma nova bateria, o segurado
  será responsável pela negociação diretamente com o prestador."*
- yelum/hdi resid: *"Custos acima do limite de cobertura serão pagos pelo cliente…
  Caso o técnico constate que o equipamento tem mais de 10 anos, o reparo será
  negado **e a visita contará como utilizada**."* 🔴 duas penalidades numa frase.
- azul: *"a distância é superior ao limite… o prestador poderá cobrar pelo
  excedente"* + **"Gostaria de continuar o agendamento? 1: Sim 2: Não"** <- BOTÃO
- zurich: *"Franquia: R$ 18.189,16"* + **"Podemos continuar com o serviço?"** <- BOTÃO

🔴 **As duas últimas TÊM botão, e foram para `handoff_triggers`.** A regra:
**tela que pede DINHEIRO nunca é respondida por passo, nem pelo adaptativo.**
Aceitar um custo em nome do segurado é decisão comercial **dele**.

⚠️ E um gatilho genérico de custo (`valor excedente|será pago pelo segurado|R\$\s?\d`)
foi proposto e **NÃO ligado**: 📊 ele casa **ZERO** telas nos 4 corpora da família
yelum/hdi. É âncora viva contra o banco e morta contra o corpus — precisa ser
conferida contra `observed_events` antes de entrar.
💭 Contexto útil do acervo: numa conversa a corretora escreve *"a cláusula é sem
limites — 37E Assist. sem Limite de KM"*. **O limite depende da apólice, e a URA
nem sempre conhece o certo.** Mais uma razão para não responder sozinho.

### P-084-13 A árvore conta como órfã toda tela que JÁ é handoff · 🤖

⚠️ Viés do medidor, dito em voz alta: `arvore.py` só consulta `match_ura_step`,
nunca `detect_handoff_trigger`. 📊 Na allianz a órfã **nº 1 das duas rotas** é
*"Vou transferir seu caso para um especialista"* — retorno **496** no residencial.
Ela é FRONTEIRA, já tem destino, e a `arvore` a exclui; a bancada de controle não.
**O que custa esquecer:** a fila de trabalho manda escrever um corredor para a
tela que ENTREGA o atendimento ao humano.

### P-084-14 O comparador de respondidas não vê resposta ERRADA · 🤖

🔴 **Limite estrutural, e ele escondeu sete defeitos nesta SPEC.** `--comparar-com`
conta CASAMENTOS: um passo que responde errado conta igual a um que responde
certo. O laço da porto, o condomínio da allianz, o cardápio da zurich e o carimbo
da tokio **não aparecem como ganho** — e eram os piores defeitos do bloco.
**O que destrava:** uma coluna de "resposta mudou" no comparador, além de
"casou/não casou". A bancada de controle desta SPEC já tem a metade disso
(a coluna ROUBOU).

### P-084-15 937 respostas de botão vazias, e a lista de opções em `text` vazio · 🤖

📊 Herdada da SPEC-083 e reconfirmada: o ingestor não grava `selectedButtonID`.
Em várias sessões a tecla apertada não está no banco — o caminho só se prova pela
tela SEGUINTE. **O que destrava:** gravar `selectedButtonID` no ingestor.

---

## SPEC-084 BLOCOS 2 a 5 — o que ficou aberto

> Escritas em 22/08/2026. Continuam a numeração de P-084-1..15.

### P-084-16 🔴 `carro_reserva` — 8 sessões, e não é assistência · 🧑

📊 O terceiro serviço mais presente no acervo entre os não-declarados:
**yelum 5 sessões (84 linhas) · tokio 2 (21) · mapfre 1 (14)**. E o Founder o
listou 5º em demanda medida (16 escolhas).

🔴 **Mas ele não é assistência 24h.** 📊 Na yelum, as 16 telas pertencem a
**outro bot** — o canal de sinistro/carro reserva, que atende três marcas
(YELUM/ALIRO/INDIANA), tem menu numerado em vez de botões, horário comercial
(09–17h) e **redireciona para o canal de assistência por link**.

Hoje essas sessões **inflam a contagem de órfãs da `yelum-auto` em 13%** e
puxam a régua para baixo por trabalho que o produto não faz.

**As opções, e nenhuma é executável sem decisão:**
1. corredor próprio `yelum-sinistro-whatsapp`
2. excluir essas sessões do corpus de `yelum-auto`
3. deixar como está e aceitar o viés

**O que destrava:** decisão comercial — a corretora atende carro reserva?
**O que custa esquecer:** a régua da yelum-auto mede um bot que não é o dela.

### P-084-17 Os serviços do menu `Outros serviços` que ficaram de fora · 🧑

📊 O menu tem **2 telas / 21 sessões** e nomeia oito trabalhos. Dois foram
ligados (limpeza de caixa d'água, consulta veterinária, os que têm fluxo até o
protocolo). Os outros:

| serviço | evidência | por que não entrou |
|---|---|---|
| Substituição de Telhas | 1 sessão, **0 chegam ao protocolo** | fluxo incompleto |
| Cobertura Provisória de Telhado | rótulo, 0 sessões | sem fluxo |
| Dedetização | rótulo, 0 sessões | sem fluxo |
| Limpeza do Imóvel | 1 sessão, 0 protocolo | fluxo incompleto |
| Pet Assistance | 1 sessão, 1 protocolo | 🔴 **outra linha de produto** — não é assistência residencial |

**O que destrava:** 1 acionamento completo de cada, ou a decisão de que
`pet assistance` é produto separado.

### P-084-18 `tecnico` da azul — identificada, não estabelecida · 🧑

📊 1 sessão (`d70ced75`), **33 telas**, e **não chega ao protocolo**. Os quatro
passos do galho existem e o subserviço foi declarado — com o desfecho AGENDADO
por faixa de 30 minutos, que é diferente de todo o resto do auto.

⚠️ E ele é o candidato medido para onde o **pneu** da azul entrou em 2026
(ver P-084-1). **Zero evidência** — não se declara por dedução.

### P-084-19 O `?` do classificador escondia rota com acervo cheio · 🤖 ✅ feito

📊 `?tecnico` tinha **109 linhas** (azul 33 + porto 76) e as rotas apareciam
`SEM_CORPUS`. O `?` é o balde de não-classificado: o rótulo era LIDO da tela e
não tinha para onde ir.

🔴 Mandar essas rotas para coleta é o erro que a SPEC-084 §7.2 nomeia —
**coletar o que já está coletado**. Consertado: o classificador aprendeu
`tecnico`, `bateria_nova`, `limpeza_caixa_dagua` e `consulta_veterinaria`.

⚠️ E a primeira versão do padrão de `tecnico` custou um falso positivo:
`assistência de um técnico` casava no NÍVEL 2, que lê **o que a corretora
escreveu**, e uma sessão de encanador da allianz virou `tecnico` porque a
atendente usou a palavra. **A palavra da corretora não é o nome do serviço.**
O padrão agora exige o início da string — é rótulo de menu, não prosa.

**Fica como regra:** todo padrão novo em `PADROES_DE_SERVICO_TEXTO` precisa ser
testado contra o NÍVEL 2 antes de entrar, porque ali ele lê texto livre.

### P-084-20 O corpus tem de ser REGERADO quando o classificador muda · 🤖

⚠️ Os `.jsonl` versionados carregam a classificação de serviço do dia em que
foram gerados. Mudar `padroes_de_servico.py` sem rodar
`gerar_corpus_de_telas.py --todas` deixa a régua medindo com o rótulo velho —
e nada avisa.
**O que destrava:** um guarda que compare o `servico` gravado no corpus com o
que o classificador devolveria hoje. Não existe.

### P-084-21 O conferidor de respostas tem 69 achados AMARELOS · 🤖

📊 Slots sem origem que **não travam** porque o passo tem `fallback_adaptive` —
o cérebro lê a tela e responde. Não é o defeito dos 2min22, mas também não é o
corredor sabendo a resposta.

Os maiores: `condominio_hora_inicial`/`final` (3+3) · `destino_logradouro` (2) ·
`veiculo_cor_rotulo` (2) · `meio_transporte_opcao` (2) · `periodo_preferido` (2)
· `titular_cpf_3_ultimos` (2) · `servico_texto` (2).

⚠️ E há 13 achados `B` que **não dá para confirmar daqui**: a tela não expõe
opção nenhuma no `text`, porque o ingestor não grava `selectedButtonID`
(P-084-15). Acusar ali seria acusar o corpus, não o corredor.

### P-084-22 `_PLAYBOOKS_AUTO_COM_PNEU` é uma lista escrita à mão · 🤖

⚠️ Ela enumera os 10 playbooks de auto para acrescentar os slots de cobertura.
**É exatamente o tipo de lista paralela que já mentiu três vezes neste
repositório** (`DERIVADOS`, `TETO_DE_INDEFINIDO`, `schedule_agendado`). Uma
seguradora de auto nova não entra nela sozinha.
**O que destrava:** derivá-la de `_PLAYBOOKS` filtrando por `line_kind == auto`,
depois que `_PLAYBOOKS` passar a ser montado antes dos ajustes.

### P-084-23 🔴 A ZURICH NÃO É 89% VAZIA — 129 das 137 órfãs são de OUTRAS URAs · 🤖

📊 Medido de forma independente em 22/08/2026, atribuindo cada tela órfã à
sessão em que ela aparece **exclusivamente**:

```
963f4097   105 telas exclusivas   -> SINISTRO DE COLISÃO
4118ba36    15 telas exclusivas   -> CONSULTAR PAGAMENTOS
d5ce1862     9 telas exclusivas   -> ACOMPANHAR PROCESSO
                                     ─────
                                     129 de 137
```

🔴 **A dívida real do corredor de assistência da zurich é de 8 telas**, não 137.
E `sinistro` e `colisão` já são `handoff_triggers` — o corredor nem deveria
chegar lá.

⚠️ **O efeito na régua é real e não é da zurich sozinha:** a rota
`zurich × auto × guincho` pontua 23/96, e boa parte do que a puxa para baixo é
trabalho que o produto **não faz**. O mesmo vale para `yelum × auto`, onde
📊 16 telas de `carro_reserva` são de outro bot (P-084-16).

**O que destrava:** a régua saber separar "tela de outra URA" de "tela órfã do
corredor". Hoje ela conta as duas juntas, e o número de órfãs mede o acervo, não
o corredor.
**O que custa esquecer:** trabalho de coleta e de corredor pedido para telas que
ninguém vai responder — e uma nota baixa que não diz o que parece dizer.

### P-084-24 A coluna ROUBOU não distingue "tomou e responde CERTO" de "tomou e responde ERRADO" · 🤖

📊 Ao fim da SPEC-084, três passos aparecem como "roubo" na bancada de
controle — e os três são conserto deliberado de uma resposta ERRADA:

```
servico_ja_aberto_menu    <- menu_raiz             (porto respondia "Informar outro CPF/CNPJ"
                                                    à tela de serviço já aberto)
ar_condicionado_servico   <- aviso_fora_da_garantia (o OITAVO defeito: digitava
                                                    "Conserto do ar condicionado"
                                                    para máquina de lavar)
confirmar_solicitacao_sim <- confirmar_solicitacao  (mandava um rótulo que não está
                                                    entre as três opções da tela)
```

⚠️ A bancada acusa os três igualmente, e está certa em acusar — **especialização
e usurpação têm a mesma forma**. O que separa uma da outra é se a resposta NOVA
está certa, e isso quem prova é `conferir_respostas.py`, não a bancada.

**O que destrava:** a bancada consultar o conferidor antes de chamar de roubo —
se o passo antigo tinha achado grave naquela tela e o novo não tem, é conserto.
**O que custa esquecer:** ou se ignora a coluna (e o próximo roubo de verdade
passa), ou se trata todo conserto como regressão.

### P-084-25 🔴 Doze constantes DECIDEM em nome do segurado, e nenhuma é justificada · 🧑 + 🤖

📊 Medido em 22/08/2026 pela FASE 1 da SPEC-084.1, depois de a regra B do
`conferir_respostas.py` deixar de tratar dígito e rótulo de formas diferentes:
**55 achados** — dos quais 40 eram identidade da rota (já justificados) e
**15 são o corredor afirmando um fato sobre a situação do segurado.**

Quatro famílias, e as duas primeiras têm consequência física:

```
🔴 situacao_risco     → "Nenhuma das anteriores"   hdi, yelum        (2)
     a tela oferece "Via com pouca iluminação" e "Via com pouco movimento".
     O corredor jura que o segurado NÃO está em nenhuma das duas.

🔴 via_local_rodovia  → "Via local"                bradesco          (3)
     e a própria tela avisa: "se você está em uma Rodovia pedagiada, contate
     a concessionária". Responder "Via local" por quem está na rodovia manda
     guincho para onde ele não pode entrar.

🔴 bateria_submenu    → "Recarga de bateria"       azul, porto       (2)
     recarga ≠ bateria nova ≠ troca ≠ na garantia. Quatro trabalhos.
   taxi_passageiros   → "1 a 4"                    porto             (1)
     cinco pessoas ficam na estrada.

⚠️ quando_agora/menu_quando/agendamento_dia → "Agora"/"Hoje"/"urgência"  (7)
     e para esta o dado JÁ EXISTE: `quando` é slot de `_AUTO_SLOTS_COMMON`,
     e o C2 desta mesma SPEC ligou `schedule["periodo"]` no resumo do cliente.
```

**O que destrava:** as sete do `quando` são derivação — mesmo padrão dos 10
`_opcao` já escritos. 🧑 As oito primeiras precisam de decisão: o atendimento
passa a PERGUNTAR (via/rodovia, situação de risco, tipo de bateria, passageiros)?
Isso muda o chat, não só o corredor — por isso não foi feito sozinho.
**O que custa esquecer:** é exatamente a forma dos oito defeitos da §9.5 —
*"apareciam verdes em toda medição"*.

### P-084-26 🔴 A régua NÃO LÊ `constante_justificada` — decidir se o eixo C penaliza · 🧑

📊 `grep -c constante_justificada backend/scripts/rubrica.py` → **0**.

A régua consulta `conferir_respostas` só para a **origem do slot** (eixo A).
A regra B — o corredor decidindo pelo cliente — **não vale ponto nenhum**.

🔴 Uma rota com as 12 constantes de P-084-25 intactas pode tirar 95/100.
É literalmente *"uma rota em 95 com furo invisível"*, que a regra do Founder
diz **não ser entrega**.

**O que destrava:** 🧑 decidir se o item entra no eixo C agora. ⚠️ **Este é o
momento mais barato**: as ONDAS ainda não começaram, então nenhum delta fica
incomparável. Depois da ONDA A, mudar a régua invalida a base que o JUIZ 0
certificou na FASE 0.
**O que custa esquecer:** a régua continua assinando embaixo do furo que a
varredura já sabe nomear.

### P-084-27 Setenta e oito telas com `noop` sobre pedido, nenhuma justificada (E13) · 🤖

📊 A linha de base gravada em [`reports/BASE-DO-E13.md`](reports/BASE-DO-E13.md):
**78 telas distintas · 95 ocorrências · 73 rotas · 33 em A–E · 45 na ONDA F** —
e as 78 sem `noop_justificado`.

⚠️ Os números declarados na SPEC (122 telas / 257 ocorrências / 39 rotas /
63 A–E) foram medidos antes dos BLOCOS 1–5, que mataram 315 telas órfãs e
escreveram tronco/galho/folha para 10 seguradoras. A direção bate; o alcance
declarado, não.

📊 E duas correções de instrumento entraram na medição:
- a heurística *"a tela pede"* aceitava `"por favor"` e `"quando"` soltos, e
  trazia 61 telas que são **avisos** (`"Por favor, aguarde"`, `"Verifique se o
  disjuntor está ligado"`). Em aviso o `noop` é CERTO.
- a unidade era `rota × tela`, e multiplicava a mesma tela pelas 9 rotas do
  mesmo corredor: **2.030**. A unidade honesta é a linha de corpus: **95**.

**O que destrava:** cada onda justifica ou responde as telas da coluna dela.
**O que custa esquecer:** o corredor calado na hora do pedido — a URA espera,
o segurado espera, e nenhuma medição mostra.

### P-084-28 O item de MUTAÇÃO do eixo E não sobrevive à cirurgia de arquivo · 🤖

⚠️ Limitação de protocolo do JUIZ 0, medida na FASE 0. `MUTACOES` faz parte da
régua (eixo E, 6 pontos). Quando o isolamento troca arquivos para medir um
conserto sozinho e **não restaura o arquivo de teste**, o item zera — e o
resultado é um fantasma de −6 em toda medição isolada, com um +6 falso
creditado ao conserto seguinte. Foi o que aconteceu com o C2 antes de a base
ser recapturada de `0f54761`.

**O que destrava:** o isolamento restaurar TAMBÉM o arquivo de teste, e a base
`C0` de patch-identidade medida pela mesma maquinaria continuar obrigatória.
**O que custa esquecer:** um conserto ganha crédito pelo defeito do instrumento.

### P-084-29 O alcance declarado de C3 e C4 não bate com o medido · 🤖

📊 FASE 0, isolamento um conserto por vez (SPEC §7.0):

| conserto | a SPEC declara | 📊 medido |
|---|---|---|
| C3 | 16 rotas | **27** |
| C4 | "9 recebem, 2 têm regra, −3 em 7 rotas" | 9 recebem, **ZERO** têm regra própria, −3 em **6** |

Direção e magnitude batem nos dois; só o alcance declarado não.
**O que destrava:** nada — é registro. **O que custa esquecer:** alguém
usa o número da SPEC como medição e a §12.1 é violada de novo.

### P-084-30 🔴 A régua PUNE o escopo `only_subservices` — o réplay não sabe o que a rota alcança · 🤖

📊 Medido em 22/08/2026, decisão 2. `bateria_submenu` ganhou
`only_subservices: ["bateria", "bateria_nova"]` — a regra 1 do Founder
(*"pergunta só o que aquela rota precisa"*). Efeito em `azul/auto/tecnico`:

```
eixo C  +6   o C7 pagou: nenhuma constante decide pelo cliente
eixo B  −4   `>=85% determinístico` caiu — a tela do submenu de bateria
             virou ÓRFÃ FUNCIONAL para a rota de `tecnico`
        ────
        +2   em vez de +6
```

🔴 **A rota de `tecnico` nunca vê aquela tela ao vivo.** O submenu só aparece
depois de escolher "Bateria" no menu anterior. Mas o corpus é por
`(seguradora, ramo)`, e `replay()` alimenta TODA rota com TODAS as telas do
corredor — então "tela que esta rota não alcança" e "tela que esta rota falha
em responder" contam igual.

⚠️ O efeito é perverso: **escopar corretamente derruba a nota.** Um executor
que otimizasse pela régua removeria `only_subservices` e ganharia 4 pontos —
recriando exatamente o defeito que a regra 1 conserta.

**O que destrava:** `replay()` filtrar por ALCANCE, não só por casamento —
uma tela cujo passo tem `only_subservices` que não inclui a rota não deveria
entrar em `orfas_funcionais` dela. ⚠️ Não foi feito agora porque muda
`determinismo` em todas as 41 rotas pontuadas, e mereceria o mesmo protocolo
de declaração + JUIZ 0 do C7.
**O que custa esquecer:** a régua ensina o contrário do que a SPEC manda.

### P-084-31 Mutação por string crua ganha ponto cego a cada linha nova · 🤖

📊 22/08/2026, terceira lição do mesmo bloco. `_mut_a` fazia
`fonte.replace('"idade_aparelho_opcao"', '')` no arquivo inteiro. Quando
`_COMO_PERGUNTAR` ganhou a chave `"idade_aparelho_opcao": "a idade do
aparelho..."`, o replace arrancou a **chave**, deixando `: "texto"` solto:

```
SyntaxError: invalid syntax, corridor_playbooks.py:7053
```

🔴 O guarda não ficou vermelho — ele **derrubou o import**, e o próximo leitor
veria um traceback em vez de um defeito. Corrigido com lookahead
`(?!\s*:)`: a mutação agora diz ONDE, e nunca toca chave de dicionário.

**O que destrava:** nada — está feito. **O que custa esquecer:** as outras
mutações por string crua têm o mesmo risco, e ele cresce com o arquivo.

### P-084-32 `azul/auto/quando` continua constante, com justificativa que pede a própria conversão · 🤖

A constante diz, na própria justificativa: *"⚠️ Se um dia existir rota de
AGENDAMENTO, esta constante vira slot."* A decisão 2 fez exatamente isso para
`quando_agora` (hdi/yelum), `menu_quando` (porto) e `agendamento_dia`
(bradesco) — e deixou `azul` de fora, porque a varredura não a acusa: ela
**tem** justificativa.

**O que destrava:** ONDA F (azul), aplicando `{quando_agora_opcao}`, que já
existe e já é derivado. **O que custa esquecer:** um corredor decide o "quando"
pelo cliente enquanto os outros quatro perguntam.

### P-084-33 🔴 Medir uma rota ESCREVE no corredor — e quase mandou uma âncora morta para produção · 🤖

📊 22/08/2026. `medir_rota.py` chama `verificar_mutacoes` em **toda** medição, e
cada mutação grava em `corridor_playbooks.py` e restaura. Sozinha é segura.
Quatro subagentes medindo em paralelo, não:

```
- "anchor": r"(?:informe|confirme) o n[úu]mero da residência"
+ "anchor": r"informe o n[úu]mero da residência"
```

⚠️ `confirme` é a redação que a URA **usa** — 📊 *"Agora, me confirme o número
da residência"*, 180x em 72 sessões. **O produto ficou com a âncora morta**, e
só foi pego por um `git status` de rotina.

📊 E um subagente viu o sintoma sem saber a causa: *"esta listagem mostra 5
telas órfãs, mas a chamada anterior mostrou 3"*.

**Consertado** pela trava exclusiva de arquivo (C11), com o guarda que roda duas
medições de verdade em paralelo e exige o corredor idêntico byte a byte.

**O que fica pendente:** ⚠️ o desenho ainda é *"medir muta o produto"*. A trava
torna seguro, não torna certo. Uma medição que precisa escrever no arquivo que
mede é frágil por construção — CI, cron e sessão paralela vão esbarrar nela.
**O que destrava:** o eixo E medir a mutação numa CÓPIA da árvore, não in-place.
**O que custa esquecer:** a próxima vez pode não ter `git status` por perto.

### P-084-34 A régua tinha três pontos cegos da mesma família, e todos punham o certo em desvantagem · 🤖

📊 Achados ao abrir a ONDA A. `replay()` só perguntava `match_ura_step` — então
**tudo que o corredor trata por outro meio contava como buraco**:

| conserto | o que contava como defeito | efeito |
|---|---|---|
| **C8** | tela que dispara `detect_handoff_trigger` | apagar gatilho GANHAVA ponto |
| **C9** | tela que `extract_capture_anchors` lê (o RESUMO com protocolo) | a tela que PROVA o fim da rota era "o defeito" |
| **P-084-30** | tela fora do alcance da rota, por `only_subservices` | escopar certo DERRUBAVA a nota |

🔴 Os três invertiam o incentivo na mesma direção: **o executor que otimizasse
pela régua desfaria o conserto.** C8 e C9 estão feitos e julgados; o terceiro
(P-084-30) continua aberto.

**O que destrava o que falta:** `replay()` filtrar por ALCANCE — tela cujo passo
tem `only_subservices` que não inclui a rota não é órfã dela.
**O que custa esquecer:** a régua ensina o contrário do que a SPEC manda.

### P-084-35 O item das `notes` era impossível: 0/2 em 73 de 73, e foram quatro voltas até a pergunta ficar certa · 🤖

📊 Nenhuma rota ganhava um ponto em `notes com contagem que RECONTA`. Um item
que ninguém pode ganhar não mede nada — só tampa toda rota em 100/102.

⚠️ **Cada uma das quatro correções foi de MEDIÇÃO minha, não das notes:**

1. **população** — o número da note vem do acervo; a régua recontava no corpus
   versionado, filtrado pela rota (`menu_tipo_servico`: declara 64, rota vê 4)
2. **frase** — `r"(\d+)\s*ocorr"` solto pegava número de outra frase
3. **passo compartilhado** — `avisos_informativos_familia` vive em dois
   corredores; "5 telas" é verdade num e o outro tem 23
4. 🔴 **unidade** — a note escreve `N telas / M sessões` e eu contava
   OCORRÊNCIAS. Doze notes **certas** acusadas de mentir. Com telas distintas:
   20 das 21 recontam

**E a 21ª era defeito de verdade:** `servico_aberto_ver_ou_abrir` declarava 4
telas e há 6. Corrigida.

⚠️ **Ainda nenhuma rota tira 2/2** — sempre sobra alguma note desalinhada.
**O que destrava:** varrer as notes numeradas dos 14 corredores e corrigir os
números na unidade certa. **O que custa esquecer:** um item que paga no máximo
1 de 2 vira teto invisível de novo.

### P-084-36 Criar worktree neste repo no Windows leva >1min e falha pela metade · 🤖

📊 22/08/2026: `git worktree add` levou mais de 2 minutos e um dos worktrees
nasceu **sem os arquivos** (`backend/app/services/corridor_playbooks.py`
ausente, com a branch criada).

⚠️ O método da SPEC-084.1 pede *"subagente por rota, worktree próprio, merge
serial"*. A serialização foi mantida — os subagentes **analisam** e devolvem as
edições, e a integração é serial com `conferir_respostas` após cada uma — mas
sem worktree.

**O que destrava:** medir por que o `add` é lento aqui (antivírus? tamanho?), ou
aceitar o método sem worktree quando os agentes não escrevem.
**O que custa esquecer:** alguém tenta 8 worktrees, espera 20 min e recebe 3
árvores quebradas.

### P-084-37 🔴 `_fonte_do_bloco` recorta uma janela que depende do código do VIZINHO · 🤖

📊 22/08/2026, ONDA A. `rubrica._fonte_do_bloco(servico)` recorta do **último
parágrafo em branco ANTES** do bloco do subserviço até o primeiro `\n        },`.

Consequência medida, e ela é absurda quando dita em voz alta:

```
escrevi `regras_para_o_cliente` no bloco do ELETRICISTA
   (com linhas em branco entre as frases, como em qualquer texto)
        ↓
a fronteira da janela do bloco VIZINHO andou
        ↓
🔴 `maquina_de_lavar` caiu de 106/106 para 102/106 — sem ninguém tocá-la
```

O item `transcrita no bloco do subserviço` vale 4 pontos e procura
`sess[ãa]o\s+([0-9a-f]{8})` dentro da janela. A referência estava ganhando esses
4 pontos porque a janela **alcançava o comentário do vizinho**.

**Consertado por fora** — a citação da sessão foi para dentro do próprio bloco,
onde não depende de ninguém. ⚠️ Mas a régua continua com a janela frágil: a
próxima rota que ganhar um parágrafo em branco pode derrubar a nota da vizinha.

**O que destrava:** `_fonte_do_bloco` recortar de `"<servico>": {` até o `},`
que o fecha — o bloco, não o bloco mais o que vier antes. ⚠️ Isso tira dos
blocos a possibilidade de ter comentário-cabeçalho ACIMA da chave, então as
rotas que hoje citam sessão lá fora precisam mover a citação para dentro antes.
**O que custa esquecer:** uma rota cai de nota por causa de um parágrafo em
branco escrito na rota do lado, e quem medir vai procurar o defeito no lugar
errado.

### P-084-38 🔴 O observador JOGA FORA o schema do formulário nativo no caminho `history_sync` · 🤖 + 🧑

📊 Medido em 23/08/2026, investigando por que porto e azul não têm
`native_flows` declarado.

```
📊 eventos `flow_reply` no acervo, por origem:
   porto   27  ·  100% source=history_sync
   azul    10  ·  100% source=history_sync
   yelum   14  ·  7 history_sync + 7 LIVE
   hdi     11  ·  10 history_sync + 1 LIVE
```

🔴 **Os dois que têm `native_flows` declarado são exatamente os dois que
tiveram evento LIVE.** Não é coincidência — são dois caminhos de código:

| caminho | o que grava |
|---|---|
| **live** (`observer_intake.py:827`) | `extra: data.get("extraData")` → passa por `_parse_native_form`, que extrai `flow_id`, `flow_name` e os campos de `paramsJSON` |
| 🔴 **history_sync** (`observer_intake.py:311`) | `{"kind": kind, "raw_keys": sorted(m.keys())}` |

⚠️ **E o payload ESTAVA na mão.** A linha faz `m = msg.get(...)` e reduz `m` a
`sorted(m.keys())`. 📊 Para o porto isso guardou
`["InteractiveResponseMessage", "body", "contextInfo"]` — e é dentro de
`InteractiveResponseMessage` que vive o `paramsJSON` com o schema. O
observador tinha a resposta e guardou o nome das gavetas.

**Consequências, e são duas:**

1. Os 37 eventos de porto e azul **não podem ser recuperados**: `observed_events`
   não tem coluna de raw, então o conteúdo se perdeu na ingestão.
2. 🔴 **O próximo `history_sync` vai perder também**, enquanto a linha 311 for a
   que atende esse caminho.

**O que destrava:**
- 🤖 a linha 311 procurar `paramsJSON` nos níveis de `m` (o `_niveis_de` já
  existe) e chamar `_parse_native_form`. ⚠️ **Não foi feito agora porque não há
  como TESTAR**: sem um raw de `history_sync` guardado, a correção seria escrita
  às cegas contra uma estrutura suposta. Escrever ingestão sem poder medir é o
  que esta SPEC combate.
- 🧑 OU um acionamento LIVE de porto e de azul que passe pelo formulário — aí o
  caminho `live`, que funciona, captura o schema como capturou o da HDI.

⚠️ E há uma decisão de privacidade junto: `_parse_native_form` guarda `answers`
(as respostas do humano). No caminho live isso já acontece e os campos são
situacionais (`rb_EmGaragemOuEstacionamento`). Num `txt_` de endereço, não
seria. Se a linha 311 for consertada, **grave o SCHEMA e não as respostas**.

**O que custa esquecer:** porto (ONDA E, 8 rotas) e azul (ONDA F, 5 rotas) têm
app dentro do WhatsApp, e o corredor não sabe respondê-lo. 🔴 **O acionamento
para no formulário** — e é exatamente a surpresa que a SPEC-084.1 existe para
eliminar.

### P-084-39 A rota de referência perde os 4 pontos de apelido — e eles nunca foram dela · 🧑

📊 23/08/2026. `allianz/residencial/maquina_de_lavar` caiu de **106/106 para
102/106** quando o filtro de eco do Espelho ficou completo. Os apelidos
conferidos foram de **5 para 2**, e as três que saíram são:

```
🔴 "selecione o eletrodomestico que precisa de conserto? 1-geladeira 2-freezer…"   menu da URA
🔴 "qual eletrodomestico precisa de conserto? 1-linha branca (microondas; fogao…"  menu da URA
🔴 "resumo\n\nservico: conserto de eletrodomestico\nproblema: maquina de lavar…"   RESUMO da URA
```

⚠️ **As três são a seguradora falando, coladas no chat pelo corretor.** Os 4
pontos estavam sendo pagos por tela de URA — exatamente o falso positivo que o
item da E8 existe para impedir (`lavadora` × "Lavadora de louças").

🔴 **A nota honesta é 102/106.** Não é regressão: é um ponto que nunca foi real
deixando de ser contado.

**O que destrava:** 🧑 palavras de segurado de verdade sobre máquina de lavar.
📊 Hoje o Espelho tem duas — `maquina de lavar` (3 mensagens) e
`maquina de lavar roupa` (1). O item pede três apelidos vivos.
⚠️ E o Espelho é o chat da CORRETORA com o AutoBrokers: quem escreve é o
corretor, relatando. O vocabulário do segurado chega de segunda mão, e isso
limita o item por construção — vale registrar antes que alguém tente "resolver"
declarando apelido que ninguém escreveu.
**O que custa esquecer:** alguém vê 102, procura o que quebrou, e conserta uma
coisa que está certa.

### P-084-40 `allianz/auto/chaveiro` não tem corpus — e a tecla 7 nunca foi apertada · 🧑

📊 23/08/2026, ONDA B. A rota é `SEM_CORPUS`, e a conferência mostra que é
**coleta legítima, não bug de nomenclatura**. Duas linhas de controle:

```
as OUTRAS teclas do MESMO menu decodificam certo
   1 → bateria   47 telas      3/4 → guincho  149 telas      6 → pneu  85 telas
`chaveiro` EXISTE como rótulo noutro corredor
   allianz/residencial/chaveiro ....... 50 telas
```

🔴 Se fosse erro de nome, as outras teclas do mesmo menu também errariam, e o
rótulo não apareceria em lugar nenhum. **A tecla 7 foi apresentada 25 vezes e
pressionada ZERO.** Ninguém pediu chaveiro de carro à Allianz pelo WhatsApp no
período do acervo.

**O que destrava:** 🧑 uma coleta dirigida — abrir uma sessão real de chaveiro
de auto na Allianz. ⚠️ E ela precisa de uma **linha de CONTROLE na mesma
rodada**: pressionar a tecla `1` (bateria), cujo desfecho é conhecido
(protocolo 52459590 na sessão cea36de4). Sem o controle, uma coleta que falha
não distingue "a tecla 7 não abre" de "o WhatsApp não respondeu hoje".
**O que custa esquecer:** a rota fica em branco e alguém a conta como defeito
do corredor, indo escrever passos para uma URA que ninguém percorreu.

### P-084-41 Não há vocabulário de segurado para as rotas de AUTO — os 4 pontos de apelido são recusados · 🧑

📊 23/08/2026. As três rotas de `allianz/auto` fecham em **102/106**, e os 4
que faltam são o mesmo item nas três: `apelidos do jeito que o cliente fala`.
A recusa é medida, termo a termo, no Espelho **depois** do filtro de eco:

```
guincho   `reboque` 2 textos distintos  →  os DOIS são portal colado (C15)
          `remocao de veiculo` 1        →  o mesmo menu de portal
          `socorro` 22                  →  colide com o subserviço socorro_mecanico
          `fundiu` 3                    →  as três são "ela se CONFUNDIU"
pneu      `troca de pneu` 2             →  1 é portal, 1 é cliente ("prrcisa de…")
          `estourou` 5 distintos        →  transmissão, vidro, balão, piso. Nenhum é pneu
bateria   `pane eletrica` 1 (cliente)   →  🔴 já é apelido de `socorro_mecanico`
          `sem bateria`/`perdeu a bateria`/`carro nao pega` → 1 texto cada
```

🔴 O item pede **três** apelidos vivos. Existe **um** texto de cliente por
candidato, e vários dos candidatos são echo ou colisão. Declarar três para
fechar a conta seria comprar ponto com fato que não existe.

⚠️ E há um achado de produto no meio: **`pane eletrica` e `nao pega` apontam
para `socorro_mecanico` na tabela global**, mas na Allianz essas palavras são
literalmente o rótulo da tecla de BATERIA ("Profissional para *pane elétrica,
recarga de bateria, motor não funciona*"). A tabela é uma só para as dez
seguradoras; mudar o destino mexeria no roteamento de hdi e yelum, que têm
`socorro_mecanico` como subserviço próprio. **Não foi mexido.**

**O que destrava:** 🧑 mensagens de segurado sobre pane de carro — e a mesma
limitação estrutural do [P-084-39] vale aqui: o Espelho é o chat da CORRETORA,
e o vocabulário do segurado chega de segunda mão.
**O que custa esquecer:** alguém "resolve" o 102 declarando apelido que ninguém
escreveu, e o item passa a medir strings no código outra vez.

### P-084-42 O corpus é indexado por CANAL, e canal não é ramo · 🤖

📊 23/08/2026. `allianz-auto.jsonl` tem 377 telas, e entre elas:

```
encanador ......... 12 telas (sessão b60d9359)
eletricista ....... 24 telas (sessão d2edf0dd)
taxi ............... 6 telas
socorro_mecanico ... 7 telas
None .............. 47 telas
```

🔴 São serviços **residenciais** num arquivo chamado `auto`. Não é erro de
coleta: o segurado escreveu para o número da assistência 24h e escolheu
"2 - Residência" no primeiro menu. O arquivo é o **CANAL**, e a URA pergunta o
ramo depois.

⚠️ Não cria rota fantasma — o replay filtra por serviço e nenhuma rota
`allianz/auto/encanador` existe no inventário. O que muda é a POPULAÇÃO das
recontagens do C16: essas 36 telas entram no corpus do corredor de auto.

**O que destrava:** 🤖 decidir se `carregar_corpus` deve segregar por ramo
declarado na sessão, ou se o nome do arquivo passa a dizer CANAL.
**O que custa esquecer:** uma medição futura conta tela residencial como
evidência de auto e ninguém percebe, porque o nome do arquivo mente.

### P-084-43 `desambiguacao_veiculo_ou_residencial` declara 23 telas e o corpus não tem NENHUMA · 🤖

📊 23/08/2026, achado ao consertar o C16. Depois de recontar na população certa
(hdi/residencial + yelum/residencial, os dois corredores que carregam o passo),
o resultado é **zero**:

```
declarado 23 telas  ·  real 0  ·  corredores [(hdi, residencial), (yelum, residencial)]
```

🔴 As outras notes sub-declaradas do C16 erram para menos (7 contra 8, 5 contra
7). Esta erra para **tudo**: a âncora não casa uma única tela em nenhum dos dois
corredores que a carregam. Ou a redação da URA mudou, ou o número foi medido no
acervo com outra frase.

**O que destrava:** 🤖 ONDA D (yelum) e a onda da hdi — recontar a âncora contra
o corpus e reescrevê-la, ou remover o passo se a tela não existir mais.
**O que custa esquecer:** um passo que nunca casa é peso morto que parece
proteção — e a note de 23 faz parecer que é o passo mais usado do corredor.

### P-084-44 Seis notes ainda sub-declaradas, em quatro corredores · 🤖

📊 23/08/2026, medido depois do C16. As de `allianz`/`alfa` foram corrigidas
nesta onda; estas ficam para as ondas dos donos delas:

```
porto/residencial  menu_raiz ..................... declara 13 · corpus 15
porto/residencial  resumo_confira .................. declara  5 · corpus  8
hdi+yelum          notificacao_do_prestador ........ declara  7 · corpus  8
hdi+yelum          encerrada_por_inatividade ....... declara  2 · corpus  3
hdi+yelum          chegada_prevista ................ declara  1 · corpus  2
hdi+yelum          senha_e_orientacoes ............. declara  5 · corpus  7
```

⚠️ Cada uma vale **1 ponto** por rota do corredor: 5 rotas na porto/residencial
e 20 nas quatro de hdi/yelum. São 25 pontos que dependem só de escrever o
número certo.
**O que destrava:** 🤖 ONDA D (yelum), ONDA E (porto) e a onda da hdi.
**O que custa esquecer:** o item volta a parecer inganhável e alguém propõe
afrouxá-lo — que foi como ele chegou à v3.

### P-084-45 `hdi/auto/chaveiro` tem UMA sessão e ela não chegou ao fim · 🧑

📊 23/08/2026, ONDA C. A rota fecha em **83/106**, e os 19 que faltam são três
itens que dependem do mesmo fato ausente:

```
a ROTA foi percorrida ate o fim ...... 12   nenhuma sessão com protocolo
o cliente recebe protocolo+dia+periodo  5   não há protocolo para capturar
>=2 sessoes distintas ................  2   há uma
```

🔴 A única sessão (`697abd09`) terminou em *"vamos te encaminhar para um de
nossos analistas"* — porque a resposta foi dada em TEXTO onde a URA esperava
BOTÃO. As regras de cobertura de chaveiro da HDI **não estão no acervo**, e o
`expectativa_do_desfecho` da rota diz isso com todas as letras em vez de copiar
o desfecho da Allianz.

⚠️ E há um dado que falta junto: os RÓTULOS DOS BOTÕES da tela
*"Deseja continuar o seu atendimento para a placa X?"*. O corpus guardou o
texto e não as opções. O passo responde `"Não"` (re-identificar) porque essa é
a decisão segura — a placa exibida é a do atendimento ANTERIOR, e o WhatsApp é
da corretora — mas o rótulo exato não foi medido.

**O que destrava:** 🧑 uma coleta de chaveiro de auto na HDI que chegue ao
número da assistência, com print dos botões da tela de abertura.
**O que custa esquecer:** 19 pontos que parecem dívida de código e são coleta —
e alguém escreve um desfecho inventado para preencher a lacuna.

### P-084-46 `hdi/auto/bateria` é SEM_CORPUS porque na HDI a bateria não tem tecla própria · 🤖

📊 O menu da HDI oferece "Recarga de bateria" como opção de
*"Pode me dizer o que aconteceu?"*, mas a sessão real de recarga (`71caf82f`)
entrou por **"Pane ou Defeito" → "Problemas elétricos"** e foi classificada
como `socorro_mecanico`. Por isso `bateria` fica sem uma tela sequer.

⚠️ Não é o mesmo caso de `allianz/auto/chaveiro` (P-084-40, tecla apresentada e
nunca apertada): aqui a tecla existe **e o caminho real passa por outra**.
**O que destrava:** 🤖 decidir se `hdi/auto/bateria` e `hdi/auto/socorro_mecanico`
são a mesma rota com dois nomes. Se forem, uma delas sai do denominador como
`ROTA_INDISTINGUIVEL`, que é o que a régua já faz com `socorro_mecanico`.
**O que custa esquecer:** a tabela mostra uma rota vazia que ninguém consegue
preencher, e a coleta é mandada atrás de uma sessão que não existe.

### P-084-47 `hdi/auto/pneu`: uma sessão, e ela tem 323 dias · 🧑

📊 `886066e5`, de 03/10/2025 — a mais recente da rota. A régua tira 2 pontos por
`>=2 sessoes distintas` e 2 por `a mais recente tem <180 dias`, e os dois são
**avisos de validade**, não defeitos: a rota fecha em 98/106 e responde todas as
telas que tem.

⚠️ O risco real não é a nota: é a URA ter mudado desde outubro e o corpus não
saber. 📊 Na mesma rota, a URA já anunciou *Guincho* na tela 19 e corrigiu para
*Troca de Pneus* na 25 — um fluxo que muda de serviço no meio é exatamente o que
uma redação nova quebra em silêncio.
**O que destrava:** 🧑 uma coleta nova de troca de pneu na HDI.

### P-084-48 A tecla certa na FORMA errada — duas achadas, e a classe fechada · ✅🤖

📊 23/08/2026. Auditoria das 25 teclas que `_derivar_teclas_do_caso` preenche,
cruzando a FORMA do valor com a convenção do corredor dono:

```
pane_detalhe_opcao      hdi + yelum   devolvia "5"  → a tela é LISTA, sem número
pneus_quantidade_opcao  hdi + yelum   devolvia "1"  → a tela é BOTÃO, sem número
```

🔴 As duas foram consertadas nesta onda, e a **classe inteira** ficou fechada por
`test_a_tecla_tem_a_forma_da_seguradora.py`, que reprova qualquer derivação
futura cuja forma não bata com a do dono.

⚠️ Fica registrado porque a auditoria só cobre o que a DERIVAÇÃO escreve. As
outras três origens — constante-por-subserviço, coleta e padrão-do-motor — não
passam por ela. 📊 Hoje elas são declaradas dentro do playbook da própria
seguradora, então a forma tende a estar certa por construção; mas isso é uma
tendência, não um guarda.
**O que destrava:** 🤖 estender a auditoria às constantes por subserviço.
**O que custa esquecer:** o defeito é invisível para todos os outros guardas —
a decisão está CERTA, só a forma está errada, e a URA responde *"Não entendi"* e
manda para um analista. Formato errado não é resposta ruim: é atendimento
perdido.

### P-084-49 `desambiguacao_veiculo_ou_residencial`: âncora que não casa nada — ver P-084-43 · 🤖

📊 Confirmado na ONDA C com a população certa do C16: `declarado 23 · real 0`
nos dois corredores que carregam o passo. Continua aberto para a onda da HDI e
da yelum.

### P-084-50 `yelum/auto/bateria`: a única sessão foi encerrada pelo RELÓGIO da URA · 🧑

📊 23/08/2026, ONDA D. A rota fecha em **73/106**, e 27 dos 33 que faltam
dependem do mesmo fato: a sessão `69816f6b` **nunca chegou ao "agora ou
agendar"**. Foi encerrada por *"o tempo máximo de espera para este atendimento
foi excedido"*.

```
a ROTA foi percorrida ate o fim ......  12
o freio casa >=1 tela REAL ...........   8   não há UMA tela de freio no acervo
o cliente recebe protocolo+dia+periodo   5
>=2 sessoes distintas ................   2
```

🔴 E a própria URA da yelum diz o prazo, nas *Dicas rápidas* da abertura:
**"Depois de 12 minutos sem resposta, a conversa será encerrada
automaticamente"**. Doze minutos é o orçamento inteiro do acionamento — e a
regra agora está escrita em `regras_para_o_cliente` do pneu, onde foi medida.

⚠️ Na prática a recarga de bateria da yelum é aberta pelo galho de
`socorro_mecanico` ("Pane ou Defeito" → "Problemas elétricos"), que fecha em
**88/88**. É a mesma dúvida do [P-084-46] na HDI: `bateria` e
`socorro_mecanico` podem ser a mesma rota com dois nomes.

**O que destrava:** 🧑 uma coleta de recarga de bateria na yelum que chegue ao
número da assistência · 🤖 ou a decisão de fundir as duas rotas.
**O que custa esquecer:** 27 pontos que parecem dívida de corredor e são o
relógio de uma URA que desligou.

### P-084-51 O galho do CAMINHÃO é handoff — e é uma decisão, não uma lacuna · ✅

📊 Oito telas de `yelum/auto/guincho` perguntam sobre o veículo pesado:
descarregado · tipo do caminhão · carroceria · eixos · para-choque ·
acessórios · altura · comprimento. Seis já eram `handoff_trigger`; **duas
estavam órfãs** e entraram nesta onda.

🔴 A decisão é deliberada e continua: **reboque de caminhão não se decide no
automático.** Carga a bordo e acessório de teto mudam o equipamento que precisa
ir, e errar manda um guincho que não consegue levar o veículo.

⚠️ E as duas sessões de caminhão do acervo terminaram, elas mesmas, em *"será
necessário falar com um de nossos especialistas"* — a própria URA não conclui.

**O que destrava:** 🧑 uma decisão comercial sobre atender frota pesada
ponta a ponta, que exigiria coletar altura, comprimento e carroceria no
cadastro do veículo — não no meio da conversa com a URA.
**O que custa esquecer:** alguém lê "handoff" como buraco e escreve passos que
escolhem equipamento de reboque por palpite.

### P-084-52 `porto/auto/vidros` não pode ganhar 25 pontos — e o motivo é o MODELO da régua · 🤖

📊 23/08/2026, ONDA E. A rota fecha em **71/100** e quatro itens estão fora de
alcance por construção, não por qualidade:

```
a ROTA foi percorrida ate o fim ......  12   exige PROTOCOLO capturado
o cliente recebe protocolo+dia+periodo   5   idem
o freio casa >=1 tela REAL ...........   8   exige tela de CONFIRMAÇÃO
```

🔴 **Vidros na Porto é `OUTCOME_ENCAMINHA`.** A URA entrega um formulário
(`porto.vc/reparovidros`) e avisa que *"esse acionamento para vidros não irá
afetar a sua classe de bônus"*. Não há protocolo porque não há chamado aberto;
não há freio porque não há confirmação a segurar.

⚠️ A régua já conhece `OUTCOME_ENCAMINHA` — o corredor o declara — mas os três
itens acima só sabem medir o desfecho `abre`. Uma rota que faz exatamente o que
deve fazer perde 25 pontos por isso.
**O que destrava:** 🤖 um item de eixo A/B que aceite `referral`/`tracking_link`
como desfecho quando o subserviço é `OUTCOME_ENCAMINHA` — com o mesmo rigor:
tem de haver o LINK real capturado por `extract_capture_anchors`, não uma
dispensa.
**O que custa esquecer:** alguém lê 71 e vai "consertar" um corredor que está
certo, escrevendo um protocolo que a Porto nunca dá.

### P-084-53 A escolha do veículo pela PLACA nunca funcionou na tela real · ✅

📊 23/08/2026. `pick_option_by_plate` exigia `(\d+)\s*-` — dígito colado no
hífen. A URA manda o número **em negrito**:

```
"*1* - X1, placa EP#-###1   *2* - Outro veículo   *0* - Sair"      allianz
"*1* - JEEP, ano 2025, placa TB#-##44  *2* - FIAT, placa QQ#-##11" porto
```

🔴 Medido: a função devolvia `''` nas telas reais das DUAS seguradoras. Só
acertava a string do próprio docstring, escrita à mão sem asteriscos.

⚠️ **É a §9.5 na forma pura**: casar o texto do teste não é responder a tela. O
comentário do passo dizia, desde julho, *"'1' fixo pegou o carro ERRADO numa
apólice com 2 veículos"* — a lição estava escrita, o guarda existia, e ele não
alcançava a tela que a URA manda.

Consertado nesta onda, com CONTROLE nos dois sentidos (duas placas dão teclas
diferentes; placa ausente não escolhe nada) e mutação no harness.
**O que fica:** 🤖 a mesma pergunta vale para as outras funções que leem a tela
CRUA em vez do texto normalizado. `pick_option_by_plate` era a única com
`dynamic:` no produto; se nascer outra, ela precisa do mesmo teste contra a
tela do corpus, não contra uma string escrita à mão.

### P-084-54 A cortesia no fim da tela silenciava o ABANDONO no começo dela · ✅

📊 23/08/2026. Ao remover o passo `central_sem_atendimento` (ONDA B), a tela de
abandono da alfa **continuou muda** — caiu num `noop` mais largo:

```
"Poxa! No momento eu nao consigo te ajudar. Por favor, entre em contato com a
 nossa Central de atendimento nos telefones: Capitais 4003-2532 ...
 Obrigado por entrar em contato!"
```

🔴 `avisos_informativos_familia` tinha `obrigado por entrar em contato!` na
alternação. O motor casa o passo ANTES do gatilho, e o `noop` retorna na hora —
então o gatilho `n[ãa]o consigo te ajudar`, declarado na própria alfa, nunca
disparava. **Consertar o passo dedicado não bastou: o defeito mudou de dono e
ficou igualmente invisível.**

📊 A frase aparece em 4 telas do corpus inteiro, e as QUATRO são a mesma tela de
abandono. Nenhuma tela de cortesia fica órfã com a remoção.

⚠️ **E a correção geral foi medida e RECUSADA.** Fazer o motor conferir o
handoff antes de retornar num `noop` parece a resposta certa e não é:
📊 **287 telas em 12 pares (corredor, passo)** passariam a chamar humano — entre
elas as 63 do link de acompanhamento da allianz (*"caso deseje alterar o
atendimento acesse..."*) e 96 menus da porto que apenas LISTAM "sinistro" como
opção. O comentário do motor já avisa disso. A ordem está certa.

**O que fica:** 🤖 a mesma pergunta vale para os outros `noop` largos. Um passo
`noop` cujo texto casa um gatilho de handoff é sempre suspeito — a lista de 12
pares está no comentário do passo e é o ponto de partida.

### P-084-55 `ar_condicionado` e `limpeza_caixa_dagua` não podem provar o handoff — e não é defeito · 🧑

📊 As duas fecham em 99/106 e 89/96, e o item que falta nas duas é
`o handoff casa >=1 tela REAL` (+3). Nenhuma tela do corpus DELAS dispara um
gatilho — e os gatilhos existem, estão declarados no corredor e são provados por
`chaveiro` (3 telas), `eletricista` (2), `encanador` (1), `eletrodomesticos` (1)
e `maquina_de_lavar` (2).

🔴 É propriedade da AMOSTRA, não do corredor: nas 2 sessões de ar-condicionado e
nas 3 de caixa d'água nada deu errado. Inventar um gatilho para ganhar 3 pontos
seria comprar ponto — e um gatilho a mais é um caminho a menos para o segurado.
**O que destrava:** 🧑 coleta — qualquer sessão dessas rotas em que a apólice não
cubra, o CPF seja recusado ou a URA transfira.
**O que custa esquecer:** alguém "conserta" declarando um gatilho largo, e aí
sim quebra o produto.

### P-084-56 `desentupimento` e `eletrodomesticos` não chegam ao protocolo em NENHUMA sessão · 🧑

📊 3 sessões cada, e as seis terminam sem número: cinco em *"Vou transferir seu
caso para um especialista"* e uma no CPF recusado. As duas rotas **respondem
100% das telas que pedem algo** (27 de 27 e 29 de 29) — o que falta não é
condução, é desfecho no acervo.

```
a ROTA foi percorrida ate o fim ......  12
o cliente recebe protocolo+dia+periodo   5
o freio casa >=1 tela REAL ...........   8
```

🔴 E o que a Allianz promete nesses dois serviços — prazo, limite de metragem no
desentupimento, quem paga a quebra de alvenaria — **não está no acervo**. Por
isso a `expectativa_do_desfecho` das duas diz "NÃO MEDIDO" em vez de copiar a do
encanador: são serviços diferentes, com regras de cobertura diferentes.
**O que destrava:** 🧑 uma coleta de cada uma que chegue ao protocolo.

### P-084-57 🔴 P1 — o FREIO da porto residencial não armava em UMA tela sequer · ✅

📊 23/08/2026, ONDA F. Nas 210 telas de `porto-residencial`,
`detect_finalize_anchor` casava **ZERO**. Os `finalize_anchors` herdados eram os
do corredor de AUTO — *"como você quer prosseguir"*, *"posso confirmar"* — e
nenhuma dessas frases existe no residencial.

🔴 **E a tela de confirmação existe, e o corredor a respondia:**

```
"Gostaria de alterar alguma informação?
 Não, está tudo correto | Localização | Quem estará no local
 Sair e não agendar | Voltar"          ⟶ o passo respondia "Não, está tudo correto"
```

Isso **CONFIRMA a solicitação**. Sem o freio, o corredor abria o chamado sem
passar pela aprovação humana e sem o cancelamento do modo de teste — e o
`finalize_abort_reply` deste playbook já era, literalmente, `"Sair e não
agendar"`, uma opção DESSA tela. A intenção estava escrita; a âncora faltava.

📊 CONTROLE da mesma rodada: em `porto-auto` as âncoras herdadas armam 14 telas,
então o mecanismo funcionava. Depois do conserto: **5 telas armam** no
residencial.

⚠️ E a auditoria correu nos 14 corredores: os outros dois com freio cego são
`mapfre/auto` (o corpus é 100% deflexão de sinistro, não há confirmação) e
`tokio/auto` (é `OUTCOME_ENCAMINHA`, não se confirma nada). **Só a porto
residencial era buraco.**

**O que fica:** 🤖 rodar essa auditoria de novo sempre que um corredor novo
nascer. Um `finalize_anchors` herdado de outro ramo é o padrão do defeito.

### P-084-58 🔴 `DESEMPATE` estava DECLARADO e NUNCA LIDO — 4 rotas da bradesco somiam · ✅

📊 23/08/2026, ONDA G. `grep -n DESEMPATE scripts/padroes_de_servico.py`
devolvia **só a própria declaração**. A constante foi escrita, documentada
(*"a tela que separa é a seguinte, e ela existe: ver DESEMPATE abaixo"*) e
nunca consultada por `servico_da_sessao`.

🔴 O efeito: na bradesco, a tecla `1` de *"qual o problema com o seu carro"* é
PANE, e PANE não distingue bateria de guincho — por isso ela mapeia para `None`,
de propósito. Sem ler o desempate, a sessão inteira ficava sem serviço, e **as
QUATRO rotas de `bradesco/auto` saíam SEM_CORPUS com o acervo cheio**:

```
a10d095d  24 telas  guincho inteiro, ate "sua assistencia ja sera acionada"
0d5284f3  33 telas  guincho AGENDADO
bc2cfead  45 telas  guincho AGENDADO
2c05415b  15 telas  bateria
```

📊 Com o desempate ligado: corpus de **127 → 159 telas**, e nasceram
`bradesco/auto/guincho` (79/106) e `bradesco/auto/bateria` (69/106).

⚠️ **É exatamente a diferença que a ONDA G existe para separar**: `SEM_CORPUS`
por coleta legítima (ninguém pediu) × `SEM_CORPUS` por BUG (pediram, e o produto
não soube ler). Fundir as duas manda para coleta uma rota cujo acervo está
cheio — e foi o que aconteceu com a bradesco por meses.

**O que fica:** 🤖 `chaveiro` e `pneu` da bradesco continuam SEM_CORPUS, e agora
isso é afirmação MEDIDA: as teclas 3 e 4 do mesmo menu decodificam e ninguém as
pressionou.

### P-084-59 O bloco da atendente passou de 7.595 para 6.165 caracteres — e ensina 10 slots a mais · ✅

📊 As dez teclas que viraram COLETA na ONDA F (estepe, alavanca travada, tipo de
câmbio, porta principal, geladeira com medicamento, e-mail do segurado…)
levaram o bloco de ~6.900 para **7.595**, acima do teto de 7.000.

🔴 **A saída não foi subir o teto** — o comentário do próprio arquivo já dizia
por quê: o prompt tem orçamento, e instrução importante compete com repetição.
A repetição estava medida: *"a placa do veículo; onde o veículo está agora; se
precisa agora ou prefere agendar"* aparecia nas OITO linhas de auto.

O bloco ganhou um SEGUNDO nível de compressão, por RAMO, com **uma exceção
nomeada**: hoista o que 8 das 9 rotas do ramo pedem, e escreve na linha da rota
*"— e aqui NÃO se pergunta X"*. Hoistar calado faria a atendente pedir à dona do
cachorro o número de uma residência que a URA nunca pergunta.

📊 Resultado: **6.165 caracteres**, 430 a menos que antes das dez teclas novas.

**O que fica:** ⚠️ toda tecla que entra em `required_slots` precisa de redação em
`_COMO_PERGUNTAR`. O guarda existe e pegou as seis primeiras — mas ele só acusa
depois que a tecla entrou.

### P-084-60 `hdi/residencial/eletricista`: três órfãs que não são da rota · 🤖

📊 A sessão `13379965` é EXPLORATÓRIA: o operador abriu o menu de Eletricista,
voltou, abriu o de Encanador, voltou, abriu o de Linha Branca, e saiu **sem
abrir nada**. A cascata classificou a sessão inteira como `eletricista`, e as
telas dos outros dois ofícios contam como órfãs DESTA rota.

🔴 O `only_subservices` de `detalhe_do_vazamento` e de `menu_item_linha_branca`
está CERTO — uma rota de eletricista não deve responder tela de encanador.
**Enquanto a sessão estiver classificada como `eletricista`, esta rota não pode
ganhar os 20 pontos de "zero órfãs funcionais"** — nem escrevendo passo nenhum.

**O que destrava:** 🤖 uma regra de classificação para a sessão que visita vários
menus e **não abre nada**: ela é não-classificada (`servico=None`), como a
`af3b817e` da yelum já é. É decisão de corpus, não de corredor — e por isso não
foi executada aqui.

### P-084-61 `zurich`: os passos exigem `*_opcao` e o produto coleta outro nome · 🤖

📊 `origens_do_slot(zurich, ...)`, medido:

```
estepe_opcao        <- o que o passo EXIGE      estepe_situacao   <- o que o gemeo usa
local_seguro_opcao  <- o que o passo EXIGE      local_seguro      <- o que o produto ja tinha
```

O corredor gêmeo da família hdi/yelum faz certo: `"reply": "{estepe_situacao}"`.
A zurich escreveu `{estepe_opcao}`. É a §12.1 do CLAUDE.md — o nome mente sobre
o que guarda.

⚠️ Nesta onda as seis teclas ganharam ORIGEM (coleta), o que tira o passo do
silêncio. **A renomeação NÃO foi feita**, e é de propósito: 📊 medido, renomear
muda o que o motor exige e trava o guincho da zurich por dois slots que ninguém
coleta hoje.

**O que destrava:** 🤖 uma mudança separada e medida — renomear o `requires` para
o slot coletado E acrescentá-lo ao `required_slots` do subserviço, na mesma
edição.

### P-084-62 O que sobrou, rota a rota — e é quase tudo COLETA · 🧑

📊 Estado final medido (23/08/2026, 43 rotas com corpus, 19 em AAA, média
ponderada **88,1%**). O que falta se concentra em cinco famílias:

```
apelidos do jeito que o cliente fala .. 20 rotas  🧑 vocabulario de segurado no Espelho
a ROTA foi percorrida ate o fim ........ 9 rotas  🧑 uma sessao que chegue ao protocolo
o cliente recebe protocolo+dia+periodo . 9 rotas  idem
>=2 sessoes distintas ................. 11 rotas  🧑 +1 sessao da rota
a mais recente tem <180 dias ........... 8 rotas  🧑 coleta nova (a URA muda)
```

🔴 **Nenhuma delas é dívida de corredor.** As 43 rotas com corpus respondem
100% das telas que pedem algo, exceto `hdi/residencial/eletricista` (ver
[P-084-60]). O que trava é o ACERVO, e cada linha do
[`ROTEIRO-DE-COLETA.md`](reports/ROTEIRO-DE-COLETA.md) diz o que pedir e com que
CONTROLE.

### P-084-63 As duas listas de vocabulário eram declaradas IGUAIS — e divergiram · ✅

📊 23/08/2026. `infer_ramo_servico` (atlas) diz no próprio docstring:

> *"Os termos abaixo são os MESMOS de `corridor_playbooks._SUBSERVICE_ALIASES` —
> de propósito. (…) inventar um vocabulário próprio aqui seria um segundo
> classificador para divergir do primeiro com o tempo."*

🔴 **Conferido termo a termo: não eram os mesmos.** O classificador declarava
`reboque`, `remocao`, `chave`, `carga`, `estepe`, `linha branca` e
`troca de pneu`; a tabela de apelidos não tinha NENHUM dos sete. A divergência
que o parágrafo temia já tinha acontecido — e o parágrafo continuava afirmando
que não, que é o pior dos dois mundos: quem lê para de conferir.

⚠️ Importa porque as duas pontas atendem caminhos diferentes:
`infer_ramo_servico` traduz o texto do SEGURADO e já devolve a chave canônica;
`canonical_subservice` traduz a palavra que a ATENDENTE escreve na chamada da
ferramenta. Se ela disser "reboque" ou "chave", o corredor precisa saber que
trabalho é esse — e não sabia.

📊 **E esta edição não move a nota de nenhuma rota, o que foi declarado antes de
escrever.** O item conta apelidos VIVOS no Espelho, e somando os sete nenhum
serviço chega aos três: `reboque` e `estepe` têm ZERO ocorrências de cliente
(`reboque` só aparecia em portal colado, e o filtro do C15 o removeu).

🔴 Escrever `"guincho": "guincho"` faria a conta fechar em três serviços — e
seria **comprar ponto**: `canonical_subservice("guincho")` já devolve "guincho"
sem alias nenhum. Tautologia não é vocabulário, e a régua estaria medindo
strings no código outra vez.

**O que destrava os 36 pontos que faltam:** 🧑 vocabulário de segurado no
Espelho. ⚠️ E há um limite estrutural que vale escrever: **o Espelho é o chat da
CORRETORA com o AutoBrokers** — quem digita é o corretor, relatando. A palavra
do segurado chega de segunda mão, e por isso este item vai ficar difícil por
construção, não por descuido.

### P-084-64 🔴 C21 — o veredito mais grave da ONDA G não tinha controle · ✅

📊 23/08/2026. O roteiro de coleta acusava 🔴 **SUSPEITO DE BUG** nas quatro
rotas de `mapfre/auto`. A regra era: *"nenhuma ROTA deste corredor tem telas e o
corredor TEM corpus → o decodificador é o suspeito"*.

🔴 **A tabela de rotas não é o corpus.** Medido: o decodificador funciona na
mapfre — nomeia `carro_reserva` em 14 linhas, em `nivel-2-texto`. As 6 sessões
do acervo são deflexão de sinistro (3), carro reserva (1), abandono por
inatividade (1) e canal do CORRETOR (1). **Ninguém pediu assistência à mapfre no
período.** Não há bug para caçar.

⚠️ E o erro tinha as duas direções: mandaria alguém procurar um bug inexistente
e — pior — quem lesse *"suspeito de bug"* arquivaria a linha como dívida técnica
em vez de PEDIR a coleta. É exatamente a confusão que a ONDA G existe para
desfazer.

📊 Depois do C21: `30 SEM_CORPUS = 15 COLETA LEGÍTIMA + 11 RÓTULO NÃO VISTO +
4 NINGUÉM PEDIU ASSISTÊNCIA`, e **zero** suspeitas de bug. O veredito de bug
continua conseguindo disparar — o guarda cega o decodificador de propósito e
confere que as mesmas quatro rotas voltam a ser acusadas.

**O que fica:** 🧑 a mapfre entra na coleta com uma ressalva escrita: nenhuma
irmã dela tem desfecho no acervo, então a coleta precisa de DUAS tentativas.

### P-084-65 A varredura de mutação commitada olhava para UM arquivo · ✅

📊 O guarda do C12 — que existe porque uma mutação **foi commitada** e ninguém
viu — lia as mutações só de `test_a_regua_nao_tem_furo.py`. A 12ª mutação nasceu
noutro arquivo de teste e sobre outro arquivo de produto
(`scripts/roteiro_de_coleta.py`): passaria batido.

Agora a varredura é de `tests/` inteiro, **por `ast`, sem importar módulo** —
⚠️ `VM._carregar_mutacoes` afirma no docstring que lê o `MUTACOES` *"sem
executar as asserções"* e 📊 executa (`exec_module`, com `stdout` e `SystemExit`
engolidos). Serve para um arquivo; varrer a pasta com ele roda a suíte e pendura.

🔴 **E a varredura ampliada achou um defeito na estreia — meu.** A primeira
redação da mutação nova trocava `elif not vivas and not decodificou:` por
`elif not vivas:`, e essa segunda linha **existe no código saudável**, logo
abaixo. O guarda pergunta *"o `texto_para` está no commit?"* e responderia SIM
para sempre: uma acusação permanente de mutação que nunca houve.

**Regra que fica:** ⚠️ o `texto_para` de uma mutação tem de ser texto que **não
pode existir** no produto saudável. E: o `print` de falha de um guarda precisa
COMEÇAR com `FALHA`/`FALHOU` — um 🔴 na frente faz a bateria reportar *"a
mutação é enfeite"*, apontando o diagnóstico para o teste quando a causa está no
`print`.

### P-084-66 🔴 A PII escrita à mão no CÓDIGO — 89 em 117 arquivos · 🧑

📊 23/08/2026. O mascarador cobre o CORPUS. **Comentário e fixture não.** Uma
tela real transcrita para explicar um passo traz o dado do segurado junto.

```
166  primeira varredura, sem filtro estrutural
 85  com o filtro — 🔴 e ele engolia placa REAL
101  com o filtro corrigido: a medida honesta
 89  restantes, em 117 arquivos, depois da limpeza desta SPEC
```

⚠️ Boa parte dos 89 **não é dado de pessoa** — `0800` e central de atendimento
têm forma de telefone e são endereço comercial publicado. A triagem é o primeiro
trabalho.

🔴 **O que destrava:** autorização do Founder ([`CHANGE-ADDENDA`](CHANGE-ADDENDA.md),
ESSENCIAL). A varredura cruza dez SPECs e mexe em fixture que guardas diferentes
comparam entre si: a placa mascarada e a placa do caso mudam JUNTAS ou o guarda
vira enfeite — aconteceu três vezes na limpeza parcial, e foi achado medindo.

**O que custa esquecer:** dado de segurado real fica versionado para sempre no
histórico do git, onde nenhuma limpeza futura o alcança.

**A ferramenta existe:** `python scripts/auditar_pii_no_codigo.py [--em <prefixo>]`
— ⚠️ ela nunca imprime o valor, só a forma e uma sombra.

---

## SPEC-084.2 — O CONTRATO

### P-084-67 🔴 O `flow_id` NUNCA CHEGA — `galaxy_message` não é parseado · 🤖

📊 23/08/2026, varredura dos 28.096 eventos de `observed_events`: o marcador
`[FORMULARIO NATIVO]` aparece **0 vezes**. As telas de abertura de formulário da
família HDI/Yelum chegam como `{"kind":"buttons","options":[]}` — **sem
`flow_id`, sem `flow_token`, sem marcador**.

🔴 A causa está medida: `evolution_inbound._interactive_from_message` reconhece
`("flow", "mpm", "wa_payment_details", "review_and_pay")`, e o bot da HDI/Yelum
usa o rótulo **legado `galaxy_message`**. ⚠️ `evolution_go.py` já documenta esse
mesmo fato do lado do ENVIO; ninguém cruzou com o lado da LEITURA.

**Consequência:** mesmo com o C2 e o C4 aplicados, o produto monta a resposta do
formulário e **pausa** — sem `flow_token` o envio é recusado
(`formulario_pronto_sem_flow_token`). O que os dois consertos entregam é
*"resposta pronta no dossiê, com motivo"* em vez de *"órfã silenciosa"*. É ganho
real, e **não é acionamento automático**.

**O que destrava:** 🤖 uma linha (`elif name in ("flow", "galaxy_message", …)`)
— mas ela mexe no parser de TODA interativa de entrada e merece bloco próprio
com controle. **O que custa esquecer:** o formulário é o último portão antes do
protocolo; 📊 na sessão `8ac461dc` o clique humano foi seguido do desfecho em 40
segundos.

### P-084-68 O QUARTO formulário da yelum não foi transcrito · 🤖

📊 `1579547063352571` — *"Automóvel - Informar endereço V2"*, yelum, 03/08/2026,
sessão `8a0d25a4`. O `response_message` dele está no acervo e não foi lido.

⚠️ E há um agravante medido: o passo `destino_como` responde **texto** a uma tela
que é esse formulário — a âncora `para onde devemos levar o ve[íi]culo` casa as
duas, e `match_ura_step` roda antes de `_responder_formulario_nativo`. O corredor
envia `"Digitar endereço"` como texto para uma tela que só aceita clique.

### P-084-69 Qual `flow_id` ecoar de volta não é decidível offline · 🤖

📊 O mesmo formulário V2 tem id `857030507196739` na HDI e `3206000179602236` na
yelum. `montar_resposta_de_flow` devolve `flow_schema["flow_id"]`, então
responder à yelum ecoaria o id da HDI. `evolution_go` diz que esse campo é *"o
que diz à seguradora QUAL formulário está sendo respondido"*.

⚠️ **Se a yelum validar, a resposta é descartada em silêncio e a janela queima.**
O C4 registrou os dois ids apontando para o mesmo objeto, o que resolve a
LEITURA. Qual ecoar depende de medição no ar — 🧑 e só o Founder libera envio.

### P-084-70 A regra dos "18 anos" é afirmada onde o acervo não a mostra · 🤖

📊 Varrido o acervo por corredor: `"18 anos"` não aparece em **nenhuma** tela de
`hdi-auto` (375), `yelum-auto` (607), `zurich-auto` (253), `bradesco-auto` (159),
`mapfre-auto` (75) e `tokio-auto` (70) — **0 de 1.539** — e os seis afirmam a
regra ao cliente. Ela é texto de alfa/allianz/azul/porto que `_auto_playbook`
copiou para os onze corredores.

⚠️ O C5 tirou a regra apenas do texto NOVO do `socorro_mecanico`, onde havia de
escrever de qualquer forma. Tirá-la dos seis é decisão de escopo maior, **e a
assimetria pesa nos dois sentidos**: afirmar sem base pode fazer o segurado
adiar o atendimento; remover uma regra verdadeira faz o prestador chegar e não
poder trabalhar. Precisa de coleta, não de escolha.

### P-084-71 `hdi/residencial` e `porto/residencial` não dão instrução nenhuma · 🤖

📊 Os dois declaram `client_instructions: []` com a nota de que *"copiar seria
inventar"* — e o corpus falsifica a nota: `"18 anos"` aparece em
`hdi-residencial` (1 tela) e em `porto-residencial` (7). O texto EXISTE medido
nesses corredores. São **10 pares** em que o cliente hoje não recebe instrução
alguma por uma decisão que já venceu (§9.3).

### P-084-72 `eletrodomestico_opcao` está em duas listas que se contradizem · 🤖

📊 Ele está em `_NAO_SE_PERGUNTA` (*"o motor preenche"*) **e** em
`required_slots` de hdi/yelum (*"a corretora informa antes de acionar"*). A
Allianz tem default (`"15"`); hdi e yelum não. O C5 deu redação ao slot, o que
tapa o sintoma — a contradição entre as duas listas fica.

### P-084-73 O sufixo `_opcao` vale em metade dos caminhos do portão · 🤖

📊 A regra *"o que o MOTOR preenche não se cobra do cliente"* vale no laço dos
`requires` de passo e **não** no de `required_slots`. É por isso que
`idade_aparelho_opcao` e `eletrodomestico_opcao` chegam ao portão. Não é defeito
hoje — os dois SÃO coleta legítima —, mas uma regra por sufixo aplicada em
metade dos caminhos é armadilha para quem escrever a próxima tecla.

### P-084-74 🔴 A mutação foi commitada OUTRA VEZ · ✅ (o guarda pegou)

📊 O commit `8a3ebf3` (C6) levou `flow = None  # DESLIGADO PELA MUTACAO` dentro
de `scripts/replay.py`. A árvore de trabalho tinha o código real; o commit, não.
Mesma causa do C12: `git commit` rodado enquanto a bateria de mutações tinha o
arquivo mutado.

✅ Corrigido no commit seguinte, e quem pegou foi
`test_nenhuma_mutacao_foi_commitada`, que pergunta ao OBJETO COMMITADO.

⚠️ **Segunda vez que isto acontece, e o guarda só ACUSA DEPOIS.** 🔴 E o risco
aumentou nesta SPEC: os JUÍZES rodam a bateria na MESMA árvore de trabalho em que
o executor escreve — 📊 durante esta sessão, `git status` mostrou
`scripts/replay.py` e depois `corridor_playbooks.py` modificados por processo de
juiz, sem que o executor tivesse tocado neles.

🤖 **O que destrava:** um `pre-commit` que recuse commit enquanto houver mutação
aplicada, ou um lock que a bateria segure — a trava do C11 impede duas mutações
simultâneas e **não** impede um commit no meio de uma. **O que custa esquecer:**
entre o commit sujo e a próxima rodada do guarda, qualquer clone mede com o
instrumento cego.

### P-084-75 `tudo_que_sera_pedido` é declarada e nunca chamada · 🤖

📊 `grep -rn` no repo: uma definição, e uso só em teste. Ela já sabe ler
`native_flows` — se estivesse ligada ao bloco da atendente, o C2 não teria
existido. É a mesma família de `schedule_agendado` e `ticket_de_entrada`.

### P-084-76 `resolve_insurer_contact` recebe `line_kind` e o descarta · 🤖

📊 `insurer_contact_env_var` monta `INSURER_CONTACT_{KEY}_ASSISTENCIA`, sem a
linha. Um parâmetro que existe, é passado com cuidado em dois lugares e não faz
nada — §12.1: **o nome mente sobre o que guarda**. E há quatro seguradoras com
corredor auto E residencial, que provavelmente não atendem no mesmo número.
⚠️ O C3 fez a linha passar a ser derivada ali, para que o dia em que o parâmetro
voltar a ter função não comece errado.

### P-084-77 `confirm_first` roda ANTES da validação de subserviço · 🤖

📊 `subservice="banho_de_gato"`, `insurer_key="hdi"`, `line_kind="auto"` devolve
`confirm_first`. O produto manda o atendente **confirmar dados com o cliente**
para um serviço que não existe; o `sem_corredor` só aparece na segunda chamada,
depois de o segurado já ter confirmado. Handoff atrasado de uma volta inteira.

### P-084-78 Rotas sem apelido: `tecnico`, `bateria_nova` e `taxi` · 🤖

📊 `_SUBSERVICE_ALIASES` não tem nenhum apelido para os três. Quatro rotas do
produto só são alcançáveis se o modelo escrever o nome canônico exato. ⚠️ O C3
pelo menos as fez aparecer no `description` do contrato.

### P-084-79 O corpus não guarda `msg_type` nem `interactive` · 🤖

📊 As chaves do `.jsonl` são `company_id, servico, servico_nivel, session_id,
text, wa_timestamp`. O replay só enxerga o caminho por TEXTO; o caminho por
metadado, o `flow_token` e a guarda de formulário desconhecido são **invisíveis
à régua**, para sempre, com este corpus. 🤖 `gerar_corpus_de_telas.py` já lê as
duas colunas de `observed_events` — carregá-las no `.jsonl` é barato.

### P-084-80 🔴 A BATERIA DE MUTAÇÕES REVERTEU EDIÇÕES EM SILÊNCIO · 🤖

📊 23/08/2026, durante a rodada dos juízes da SPEC-084.2. Dois consertos já
aplicados e verificados **sumiram do arquivo sem que ninguém os desfizesse**:

```
_COMO_PERGUNTAR["encanador_instalacao_opcao"]   voltou ao texto inventado
as regras medidas de porto/taxi e porto/vidros  sumiram do corredor
```

🔴 **A causa é a mecânica da própria bateria.** `verificar_mutacoes` COPIA o
arquivo, aplica a mutação, roda o teste e **restaura a partir da cópia**. Os
juízes rodaram a bateria na MESMA árvore de trabalho em que o executor
escrevia: um deles copiou `corridor_playbooks.py` **antes** de uma edição e
restaurou **depois** — apagando-a, sem erro, sem diff, sem aviso.

⚠️ É a família da P-084-74 (a mutação commitada), um nível pior: ali o guarda
acusava DEPOIS; aqui **não há guarda nenhum**, porque o arquivo restaurado é
sintaticamente válido e todos os testes passam — eles só medem uma verdade
antiga.

📊 E o modo de descobrir foi um juiz reprovando duas vezes o mesmo defeito:
*"consertou onde eu apontei o dedo e deixou intacta a superfície ao lado"*. A
segunda reprovação não era teimosia do juiz — era o arquivo tendo voltado.

🔴 **E ela também explica por que grep não bastou:** conferir por texto acusou
o P1 de segurança como revertido quando ele estava vivo (o padrão tinha acento
diferente). **Conserto se confere MEDINDO no motor, não procurando string.**

**O que destrava:** 🤖 (a) um lock de arquivo que a bateria segure e que
qualquer escrita respeite; ou (b) a bateria rodar SEMPRE em `git worktree`
próprio — o que já é a prática para medir régua, e vale igual para mutar. ⚠️ E,
enquanto não houver, **juiz e executor não podem trabalhar na mesma árvore**.

**O que custa esquecer:** um conserto que some sem deixar rastro volta como
defeito na produção, e o relatório da SPEC afirma que ele foi feito.

### P-084-81 O medidor mediu a própria generosidade · ✅ (registrado)

📊 O JUIZ 4 rodou a linha de controle que eu não rodei: com **apenas os slots que
o portão COBRA** e um relato realista, o número de capturas é **o mesmo antes e
depois da SPEC**. As +9 que eu atribuí ao produto vinham do `_PREENCHIMENTO` do
medidor — eu declarei os sete campos e os acrescentei ao caso do medidor no
mesmo commit, e as derivações que produzem aqueles valores já existiam.

⚠️ **É a §9.2 virada contra mim.** Rodei o controle do PORTÃO (tirar o CPF) e
não o do INSTRUMENTO. O valor real dos sete campos é um SEGUNDO caminho para
dados que a derivação por relato já produzia — 💭 robustez plausível, **não
medida**.

**O que fica:** 🤖 o `acionamento_pelo_contrato` deveria ter DOIS modos — o caso
cheio (mede o contrato) e o caso mínimo (mede o produto). Hoje só tem o
primeiro, e ele é generoso por construção.

### P-084-82 `confirm_first` roda antes da validação de subserviço · 🤖

📊 Reconfirmado nesta SPEC: `subservice="banho_de_gato"` devolve `confirm_first`.
O produto manda o atendente **confirmar dados com o cliente** para um serviço
que não existe. É a P-084-77, e ela apareceu de novo ao testar o caminho do
valor recusado — o `confirm_first` come qualquer diagnóstico melhor que venha
depois.

### P-084-83 4 dos 10 corredores nunca disparam o repasse de ETA · 🧑

📊 Achado do JUIZ 1 na 3ª volta. A frase nova *"assim que a seguradora me passar
a previsão de chegada, eu te aviso por aqui"* tem transporte real — o
`dispatch_router` repassa telas que casam `previs[ãa]o de chegada`, e há
follow-up de 45 min. ⚠️ Mas em **alfa, bradesco, mapfre e tokio** nada no acervo
dispararia o repasse. Não é mentira (a frase é condicional), é promessa que
naqueles quatro não se cumpre. **O que destrava:** 🧑 medir em produção.

---

# 🔴 SPEC-085 — FASE 0 (24/08/2026)

## P-228 · 🤖 As 5 asserções vermelhas da régua — **BLOCKER, e é da SPEC-089**

📊 `pytest tests/test_a_rubrica_e_honesta.py` — invisível até 24/08/2026, porque
`pytest tests/` abortava a sessão antes de chegar nele:

```
:72   assert 102 == 96        "o denominador mudou; a nota passou a medir outra coisa"
:133  assert []               "o replay não acha NENHUMA órfã funcional. Ou o corredor
                               ficou perfeito — e aí esta asserção precisa ser reescrita
                               com a prova disso — ou a MEDIDA AFROUXOU e ninguém viu"
:199  "o subserviço já tem regra própria — a mutação precisa mudar de lugar"
:253  assert 9 == 15          "o eixo E deixou de fechar"
:371  assert 102 == (100 - 4)
```

🔴 **A régua da SPEC-083 está devolvendo 102 numa escala de 100, e parou de achar
órfã.** Uma régua assim **aprova o que deveria reprovar**, e o que ela aprova é
uma rota que chega em segurado. **Passa no TESTE DO PRODUTO: é BLOCKER.**

⚠️ **Mas não é desta SPEC.** Decisão do Founder, 24/08: é da SPEC-089. Consertar
durante a 085 seria mexer na régua no meio da execução que ela vai medir.

- **Destrava:** 🤖 SPEC-089 · **Onde está:** `xfail(strict=True)` com
  `QUARENTENA_SPEC089`, visível no CI a partir de agora.

## P-229 · 🤖 `test_o_corredor_residencial_nao_trava` — a tela some, e o CONTROLE some junto

📊 Rodado em 24/08/2026: 25 verdes, **2 vermelhas**, e as duas são a mesma tela:

```
[FALHOU] a redacao NOVA de `Qual seguro deseja utilizar?` volta a casar
[FALHOU] CONTROLE: a redacao ANTIGA do `qual O seguro QUE deseja` ainda casa
```

🔴 **A nova E o controle da antiga falham juntos** — o casador não perdeu uma
redação, perdeu a **tela**. E é o `allianz-residencial`, o corredor do
`work_run e5279497`, a única travessia ponta a ponta da história do produto.
A SPEC-085 §2.2 é literal: *"NÃO SE REGRIDE DISSO"*.

- **Destrava:** 🤖 triagem — defeito de produto ou fixture vencida pela
  SPEC-084.1? As outras duas quarentenas com `local_seguro`
  (`test_spec031_auto_dispatch`, `test_spec017_dispatch`) são fixture vencida
  com alta confiança; **esta não**, porque o controle cai junto.
- **Custa se esquecer:** o único corredor com prova de funcionamento pode ter
  parado de casar uma tela, e ninguém saberia até um segurado ligar.

## P-230 · 🤖 `test_o_handoff_nao_e_um_buraco` está na quarentena e **passa**

📊 Rodado em 24/08/2026: **8 asserções verdes, 0 vermelhas.** Ele está listado em
`QUARENTENA` como `xfail(strict=True)`, e `strict` corta dos dois lados: um
guarda da quarentena que volte a passar **quebra a suíte**, obrigando a tirá-lo.

- **Destrava:** 🤖 confirmar o exit code num ambiente limpo e removê-lo da lista.
- **Custa se esquecer:** quarentena que não esvazia vira aterro
  (`PROTOCOLO-AUTOBROKERS-AAA` §1), e um `xfail(strict)` que passa derruba o
  gate por um motivo que não é o defeito de ninguém.

---

## ✅ O que a SPEC-085 FECHOU ou RE-JUSTIFICOU (§11.1 do CLAUDE.md)

| # | estado | a prova |
|---|---|---|
| **P-34** | ✅ **MORREU** | *"varredura de órfão dispara 1× por processo; falta uma linha no laço de manutenção"*. 📊 Falso: `reconciliar_acionamentos_orfaos` está registrada em `buffer_processor.py:370`, id `dispatch_reconcile_check`, com intervalo por env. |
| **P-102 / P-116** | ✅ **FECHADA** | *"`human_support_destinations` tem 2 linhas, ambas da AMANDUS"*. 📊 Hoje 3 linhas, 2 corretoras — a **Resulta tem** destino ativo (`whatsapp_group`/`evolution`). Só a AutoFleet está sem, **e isso não é defeito**: nada está em produção ainda, e a Resulta é a referência (decisão do Founder, 24/08). |
| **P-30** | ✅ **MORREU** | *"Resulta e AutoFleet dividem o mesmo grupo; o handoff está RECUSADO nas duas"*. 📊 Os `md5` dos `destination_ref` mostram **zero compartilhamento**. A Resulta tem ref própria; a AutoFleet **não tem linha** — o estado dela é *ausente*, não *recusado*, e são caminhos de código diferentes (`dispatch_router.py:1629` vs. a recusa de `_destino_e_compartilhado`). |
| **P-31 / P-91** | ⚠️ **CONTINUA, com o texto invertido** | Ambas dizem que o padrão de `INSURER_DISPATCH_LIVE` é **ABERTO** e que `DISPATCH_FINALIZE_MODE=test` é o que segura. 📊 Os dois são falsos desde 14/08/2026: o padrão do código é FECHADO (`insurer_dispatch_service.py:345`) e o de `finalize` é `live` (`:375`). **O que continua é a pendência real — agora reescrita como P-227.** Seguir a instrução antiga ("apague a linha `=false`") hoje não liga nada. |
| **P-225** | ⚠️ **RE-JUSTIFICADA** | *"`human_review_tasks` tem schema completo e nenhum escritor"*. 📊 **Tem escritor**: `app/services/evals/juiz_llm.py:196`. Zero linhas porque nunca disparou. Por isso a FASE 0 **não** a usou: `veredito boolean` e `amostra NOT NULL` são forma de eval, e travamento não tem veredito booleano. |
| **P-226** | ⚠️ **CONTINUA, e cresceu** | 📊 O cabeçalho do meta-guarda dizia 151/14 e a `QUARENTENA` dele listava 273/42 — **duas contagens divergentes dentro do arquivo que existe para impedir divergência.** Corrigido. E `pytest tests/` entrou no `gate.yml` como job próprio (`guardas`), fechando o lado B: 📊 6 asserções de arquivos pytest-nativos estavam vermelhas e **nenhum executor as tocava**. |

## P-231 · 🔴 Uma mutação de teste VAZOU para o corredor — e desligou a âncora do único acionamento que deu certo

📊 Achado ao vivo em 24/08/2026, durante a FASE 0 da SPEC-085.

### O sintoma, e por que ele engana

Quatro rodadas de `pytest tests/` na mesma árvore, sem alterar uma linha entre elas:

```
rodada A  15m12   2 vermelhos
rodada B  07m34   2 vermelhos   os MESMOS dois
rodada C  13m57   7 vermelhos   conjunto DIFERENTE
rodada D  13m08  11 vermelhos   conjunto DIFERENTE de novo

📊 TODOS os acusados, rodados SOZINHOS: exit 0.
```

⚠️ Vítima que muda de rodada para rodada parece corrida, e eu escrevi que era.
**Não era.** Nem corrida, nem `.pyc` (rodada D já estava com
`PYTHONDONTWRITEBYTECODE=1` e o `__pycache__` apagado), nem timeout
(📊 zero ocorrências de `passou de 120s` no log).

### A causa, no disco

```diff
  ALLIANZ_RESIDENCIAL_WHATSAPP_V1
- "schedule_agendado": (
+ "schedule_agendado_DESLIGADO": (
```

🔴 **Uma mutação de teste que vazou e ficou.** Um processo de medição foi morto
no meio da janela e o `finally` da restauração nunca rodou. A âncora que captura
**quando o prestador vem** ficou desligada — no corredor `allianz-residencial`,
que é o do `work_run e5279497`, **o único acionamento ponta a ponta da história
do produto.**

📊 **A prova, restaurando a linha:** `test_a_maquina_de_lavar_vai_ate_o_fim` foi
de **107 verdes / 3 vermelhas** para **112 verdes / 0 vermelhas**, duas vezes
seguidas. As três vermelhas eram *"o QUANDO é capturado do RESUMO"* e o controle
dele — exatamente o que a âncora desligada deixa de fazer.

🔴 **E o conjunto de vítimas muda porque depende de QUAL âncora ficou
desligada.** Cada vazamento diferente derruba um grupo diferente de guardas,
todos inocentes. Quem investigar vai procurar defeito onde não há — foi o que
eu fiz por meia investigação.

### ⚠️ Parte disso fui eu, e o registro fica

Eu matei duas rodadas de `pytest` com um `kill` de tarefa em segundo plano. **É
um gesto normal**, e é justamente por isso que ele importa: qualquer `Ctrl-C`,
timeout de CI ou desligamento de máquina no instante errado produz o mesmo
estrago, e **ninguém fica sabendo**. O `git status` de rotina que pegou o
quase-acidente de 22/08 é sorte, não controle.

### O que já foi fechado nesta SPEC

✅ **A árvore é conferida ANTES de medir** — `test_a_arvore_nao_tem_mutacao_vazada`
procura os marcadores do arnês (`DESLIGADO PELA MUTACAO`, `_DESLIGADO`,
`# MUTACAO`) em `corridor_playbooks.py` e `scripts/replay.py`, e reprova a
rodada inteira com o `arquivo:linha`. Ciclo vermelho→verde provado com a
mutação REAL que vazou.

✅ **Quem vaza fica vermelho no próprio nome** — o meta-guarda tira o sha256 dos
dois arquivos antes e depois de CADA guarda. Antes, o vermelho aparecia no
guarda seguinte.

⚠️ **Sem `git`, de propósito:** 📊 59 dos 456 commits de agosto tocam
`corridor_playbooks.py`. Reprovar toda árvore com edição legítima seria um
guarda que ninguém aguenta.

⚠️ **E isto NÃO é o `test_nenhuma_mutacao_foi_commitada`:** aquele pergunta ao
objeto commitado e o docstring dele avisa que *"`git status` limpo não prova
nada aqui"* — ele fecha a porta do **commit sujo com árvore limpa**. Este fecha
a **oposta**. Os dois são necessários.

### 📊 E a prova final: são OITO janelas, e o vazamento continua depois do pytest sair

Rodada completa com o conserto desta SPEC — restaurar no meio + acusar a sessão:

```
antes:  6 vermelhos (inocentes)   árvore SUJA, com a âncora morta
agora:  1 vermelho — o da SESSÃO  305 passed, 45 xfailed em 12m45
        árvore limpa antes: 0  ·  árvore limpa depois: 0
```

As **8 janelas** registradas não têm nada em comum:

```
durante test_nenhuma_mutacao_foi_commitada.py   corridor_playbooks.py
durante test_o_atendimento_tem_memoria.py       corridor_playbooks.py
durante test_o_eco_nao_inventa_escolha.py       replay.py
durante test_o_espelho_nao_aprende_com_a_amandus.py  corridor_playbooks.py
durante test_rotulo_nao_come_a_frase.py         replay.py
durante test_spec062_prontidao_e_sli.py         corridor_playbooks.py
```

🔴 Guardas de assuntos completamente diferentes. **A única coisa que eles têm em
comum é estarem rodando na hora.** E o fecho: segundos DEPOIS de o pytest sair,
`git status` acusou `corridor_playbooks.py` modificado; no comando seguinte o
`git diff` voltou **vazio**, com 📊 **2 processos python ainda vivos**. Um
processo solto terminando o ciclo mutar-restaurar **fora da sessão de teste**.

⚠️ **Consequência operacional imediata:** `git add -A` neste repositório pode
commitar uma mutação a qualquer momento, mesmo com a suíte parada. Adicione
arquivo por nome. É a P-084.1 C12 com uma janela maior do que ela supunha.

### O que continua aberto

🔴 `test_duas_medicoes_nao_se_atropelam` — o guarda que prova que duas medições
concorrentes **não** corrompem o corredor — **está vermelho e em quarentena.**
A trava do C11 não segura hoje, e o `xfail` esconde isso.

- **Destrava:** 🤖 triagem da P-226 para esse guarda. **Fura a fila**: é o único
  da quarentena cujo vermelho tem efeito colateral no código do produto.
- **Custa se esquecer:** 🔴 o arquivo em risco é o dos **73 corredores**. Uma
  âncora morta ali é uma tela de URA que o corredor deixa de reconhecer — um
  segurado parado na estrada sem socorro. **Não é dívida de teste.**
- ⚠️ **A não-determinismo já estava no CI:** o `gate.yml` anterior já rodava
  `test_todos_os_guardas_script_rodam.py`. A SPEC-085 não o introduziu — ela o
  tornou visível, e agora ele grita o motivo certo.

## P-232 · 🧑 O ensaio LIVE da SPEC-085 não foi feito — ele escreve, e a trava é SELECT

📊 A SPEC-085 §G.1 pede o ensaio seco ponta a ponta **com a AMANDUS SEGUROS**.
Ele foi feito como **travessia pura** (`test_o_ensaio_do_destravamento`), que
percorre os dez pontos e a linha de controle sem banco, sem Redis e sem rede.

🔴 **O que falta é o ensaio contra o tenant de verdade** — um acionamento
entrando em `needs_human` na AMANDUS, a linha nascendo em `work_runs`, a Fila
mostrando, uma pessoa assumindo. Isso **escreve**, e a trava da execução é
*"somente SELECT fora das migrations desta SPEC"*.

Os pontos que dependem de banco não ficaram sem prova: `test_acionamento_sobrevive`
os exercita com o dublê completo (a linha nasce, sobrevive ao cache limpo, e a
varredura não a atropela). O que o dublê não prova é o **ambiente**.

- **Destrava:** 🧑 Founder — autorizar a escrita de teste no tenant AMANDUS, ou
  pedir que ela entre como migration desta SPEC.
- **Custa se esquecer:** os itens 1, 4 e 5 do §F0.3 (a linha aparece no banco ·
  dois tenants com mutação · sobrevive ao TTL de 6h) ficam provados só por
  construção e por dublê. **Nenhum deles está marcado verde no relatório.**

## P-233 · 🤖 `suporte_indisponivel_motivo` fica mascarado, e a corretora perde o porquê

O BLOCO B grava dois campos quando não há destino: `suporte_indisponivel`
(`ausente` | `recusado` | `envio_falhou`) e `suporte_indisponivel_motivo`, o
texto. O primeiro está entre as chaves seguras do mascarador; **o segundo não**,
de propósito — texto livre é mascarado por padrão (fail-closed).

⚠️ Hoje o motivo da recusa não carrega PII (*"destino de suporte compartilhado
com N outra(s) corretora(s)"*), então mascará-lo é conservador demais. Mas
abrir texto livre por exceção é como PII volta a passar.

- **Destrava:** 🤖 transformar o motivo num ENUM, em vez de frase — aí ele é
  seguro por construção e a corretora lê o porquê na tela.
- **Custa se esquecer:** a tela do BLOCO E diz *"recusado"* sem dizer com quem
  o destino é compartilhado, e a corretora não sabe o que consertar.

## P-234 · 🤖 O `mirror_conversation_id` pode faltar, e aí o aviso sai sem marcador

`entregar_dossie_uma_vez` usa `session["mirror_conversation_id"]` como chave do
marcador. Ele vem de `dispatch_mirror`, e **pode não existir**: com
`DISPATCH_MIRROR=0`, sem entradas novas no transcript, ou se a conversa não
puder ser criada.

🔴 Nesse caso o dossiê **sai sem marcador** — de propósito: o defeito grave é o
silêncio, e a repetição é só incômodo. Mas ele pode repetir a cada varredura.

⚠️ **Inventar uma segunda chave é proibido** (§8 da SPEC: "nenhum segundo
marcador de aviso"), e `reivindicar_o_aviso(None)` gravaria
`handoff_realerta:None`, uma chave GLOBAL que calaria TODAS as corretoras.

- **Destrava:** 🤖 garantir o `mirror_conversation_id` antes do handoff, ou
  decidir uma chave canônica alternativa **no mesmo formato**.
- **Custa se esquecer:** com `DISPATCH_MIRROR=0` o grupo da corretora pode
  receber o mesmo dossiê a cada passada do Vigia.

---

# 🔴 O QUE O PAINEL DA SPEC-085 DEIXOU ABERTO (25/08/2026)

> Cinco lentes cegas entre si: 78 · 78 · 88 · 88 e o red team. **Zero
> aprovações na primeira volta.** Treze achados passaram no TESTE DO PRODUTO e
> foram consertados; estes ficaram.

## P-235 · 🤖 A QUARTA cadeia — o vigia do portal promete sem carimbo

📊 A varredura nova (`test_a_promessa_antiga_nao_sobrou_em_lugar_nenhum`, que
agora percorre `backend/app/` inteiro com o fiscal `afirma_transferencia`)
achou **quatro** mensagens ao segurado em `app/tasks/vigia_do_portal.py`:

```
:142  "…no sistema da seguradora agora — o canal automático não respondeu.
       Já chamei alguém da nossa equipe…"
:160  "…Não vou te deixar no vácuo: já passei pra alguém da nossa equipe
       acompanhar e te retornar…"
:217  "…Só não consegui concluir a última etapa por aqui. Já passei para nossa
       equipe finalizar."
:270  "…Já passei pra nossa equipe concluir — não some não…"
```

🔴 **É a mesma família que a SPEC-085 matou nos caminhos B e C**: a frase afirma,
no passado, que alguém foi chamado — sem o carimbo que prova. E o portal é a
cadeia com **mais** casos: 📊 33 dos 39 acionamentos de vidros caem em
`needs_human` (o próprio comentário do arquivo diz).

⚠️ **Fora do escopo da SPEC-085 de propósito** (§9): ela cobre B e C. A quarta
cadeia precisa de um sinal de "o dossiê saiu?" que hoje ela não tem, e isso é
desenho, não conserto de 30 minutos.

- **Destrava:** 🤖 dar ao `vigia_do_portal` o mesmo `aviso_de_handoff(saiu)` —
  a função já existe no motor e é pura.
- **Custa se esquecer:** é a cadeia com mais volume, e o segurado de vidros
  ouve uma promessa que ninguém garante.
- **Onde está registrado:** no `JUSTIFICADOS` do guarda, com esta P ao lado.
  **Promessa nova em qualquer arquivo de `backend/app/` quebra a suíte.**

## P-236 · 🔴🧑 Conserto de DADO não sobrevive ao código antigo em produção

📊 Medido pelo JUIZ 1, e confirmado por mim: a migration `20260824_02` corrigiu
as duas linhas defeituosas, e **produção as reescreveu de volta**.

```
cb6478f5   status = completed              ← a migration gravou waiting_input
           finished_at = 2026-08-25 00:05  ← a migration gravou NULL
           progress_percent = 100          ← a migration gravou 95
           result_summary = "Caso entregue à equipe…"
           unblock_state = travado         ← 🔴 ESTE sobreviveu
```

🔴 **A causa é de SEQUÊNCIA, não de código.** O único escritor daquele
`result_summary` é o ramo `final == "completed"` da reconciliação — o **código
antigo**. Produção constrói a `main`; o conserto está numa feature branch. A
varredura desfaz o `UPDATE` a cada boot.

> **Corrigir dado enquanto o código antigo roda em produção é corrida perdida.
> O conserto de dado só cola depois que o código sobe.**

⚠️ E há um lado que VALIDA o desenho: `unblock_state` sobreviveu, porque o
código antigo não conhece a coluna. **A coluna que esta SPEC criou é hoje o
único campo de `work_runs` que diz a verdade sobre esse caso** — e a Fila do
BLOCO E lê ela, não o `status`.

- **Destrava:** 🧑 merge na `main` + deploy; **depois** rodar de novo o segundo
  bloco da migration (os dois `UPDATE`s são idempotentes por construção).
- **Custa se esquecer:** quem consultar `work_runs.status` antes do deploy vê o
  travamento como sucesso, e o relatório afirmava o contrário. **Afirmação
  corrigida.**

## P-237 · 🤖 Duas retomadas simultâneas: não há lock

📊 Achado do red team. `try_route_insurer_inbound` faz load → mutate → save sem
lock; `grep lock` no arquivo devolve **zero**. Dois webhooks concorrentes
carregam a MESMA sessão, ambos passam por `pode_retomar`, ambos chamam
`start_live_dispatch` — **as duas aberturas já saíram para a URA** antes de o
segundo `save` sobrescrever a chave.

⚠️ **A SPEC-085 não alargou isto**: depois do painel, a única família em
`RETOMA` é `insurer_closed`, que já retomava antes. Mas o BLOCO D chegou a
admitir `formulario_envio_falhou`, e teria dobrado a exposição.

- **Destrava:** 🤖 um lock por `dispatch:active:{company}:{digits}` no Redis,
  ou um `attempt` idempotente no `work_runs`.
- **Custa se esquecer:** dois prestadores na porta de alguém.

## P-238 · 🔴 O Vigia inteiro morre sem Redis — e o produto CALA

📊 Achado do red team. `check_dispatch_watchdog` começa em
`redis.scan_iter("dispatch:active:*")`. Sem Redis, a varredura morre no `try` e
devolve 0. As sessões caem em `_memory_store` (`dispatch_router.py:92`), que o
`scan_iter` **não enxerga**.

🔴 Resultado: nenhum Sentinela, nenhum dossiê, nenhum aviso. **O produto cala** —
que é exatamente o que esta SPEC existe para impedir, por uma porta que ela não
cobre.

⚠️ O marcador e o contador falham ABERTO (repetem, não calam) e estão certos. O
defeito está **antes** deles.

- **Destrava:** 🤖 a varredura ler também o `_memory_store`, ou a lista durável
  de `work_runs` com `unblock_state IS NULL` e fase em voo.
- **Custa se esquecer:** uma queda de Redis vira silêncio total do acionamento,
  e nada no produto acusa.

## P-239 · 🤖 O dossiê das cadeias novas chega picotado em balões

📊 Achado do JUIZ 2. Nem `dispatch_router` nem `dispatch_watchdog._support_alert`
passam `bloco_unico=True` — só `human_handoff.py:549` passa. O dossiê das duas
cadeias que a SPEC-085 acrescentou chega quebrado, que é o defeito de 18/08
reaberto para quem tem de cumprir a promessa.

- **Destrava:** 🤖 passar a bandeira nos dois transportes.
- **Custa se esquecer:** quem recebe o dossiê no celular lê seis balões fora de
  ordem em vez de um.

## P-240 · 🤖 Três dívidas menores, medidas e nomeadas

| # | o que é | medido por |
|---|---|---|
| a | `error_code` é cortado em `[:180]`; uma lista longa de slots perde o fim **em silêncio**, e nenhum teste cobre | JUIZ 1 |
| b | o guarda de famílias lê **3 arquivos**; `dispatch_followup.py` já chama `save_active_dispatch` e hoje tem 0 `reason` — premissa de pé, nada a guarda | JUIZ 1 |
| c | `test_o_segurado_nao_fica_no_escuro` sai **exit 1 por cp1252** no `print(__doc__)`, não por asserção. Com `PYTHONIOENCODING=utf-8`: exit 0 | JUIZ 3 |
| d | o dossiê do caminho B é montado **antes** do aviso, então o ramo *"ele JÁ foi avisado"* é inalcançável ali. Erra para o lado seguro | JUIZ 2 |
| e | a RLS usa `users_v2.company_id`; o app resolve por `company_members` (SPEC-047). Divergência na direção **segura** | JUIZ 4 |

---

# 🔴 O QUE O JUIZ DE CONFIRMAÇÃO DEIXOU ABERTO (25/08/2026)

> Veredito **NÃO CONFIRMADO**: 2 blockers e 11 pendências. Os dois blockers e
> seis pendências foram consertados na mesma rodada. Estas ficaram.

## P-241 · 🤖 O marcador de aviso é por CONVERSA, não por acionamento

📊 Achado do juiz de confirmação. `entregar_dossie_uma_vez` reivindica o aviso
com `mirror_conversation_id`. Um **segundo** travamento na mesma conversa dentro
de 6h devolve `True` — o segurado ouve *"já passei seu caso para um colega"* com
o dossiê **deste** caso nunca enviado.

⚠️ **Não foi mexido de propósito.** Devolver `session["dossier_sent"]` no lugar
reintroduziria o defeito que o red team mediu: numa sessão nova a equipe FOI
avisada há menos de 6h e o segurado ouviria *"não consegui avisar a equipe"* —
falso. E a §8 da SPEC proíbe inventar um segundo marcador.

- **Destrava:** 🤖 uma chave canônica por acionamento **no mesmo formato** do
  marcador que já existe — desenho, não conserto de 30 minutos.
- **Custa se esquecer:** o segundo travamento da mesma conversa promete uma
  pessoa que não foi chamada para ele.

## P-242 · 🤖 O fiscal do handoff acusa uma frase VERDADEIRA num turno seguinte

📊 Medido nesta sessão, executando `afirma_transferencia` na fonte real:

```
True   "um atendente da corretora vai assumir seu caso"          <- deve acusar
True   "Ja passei pra nossa equipe finalizar."                   <- deve acusar
True   "um colega ja esta com seu caso e vai continuar por aqui" <- 🔴 falso positivo
False  "Posso assumir que voce quer o guincho?"                  <- certo
False  "Sou eu mesmo que vou continuar te ajudando por aqui."    <- certo
```

`_houve_handoff_confirmado` é por **turno**. Se o handoff aconteceu num turno
anterior, a frase verdadeira do turno seguinte vira *"Ainda não consegui
confirmar com a equipe"* — mentira na direção oposta.

⚠️ **Fica assim de propósito, e a assimetria é a razão:** o falso negativo
(promessa sem carimbo) é o defeito que esta SPEC existe para matar; o falso
positivo entrega ao segurado a assistência 24h da própria apólice, que nunca
faz mal. **Erra para o lado seguro.**

- **Destrava:** 🤖 `_houve_handoff_confirmado` por CONVERSA em vez de por turno.
- **Custa se esquecer:** o segurado ouve uma dúvida onde havia certeza.

## P-243 · 🤖 O `retry_count` não sobrevive à tentativa que falha

📊 Achado do juiz, confirmado na fonte: no fall-through de `insurer_closed` o
código chama `clear_active_dispatch` e **nunca** `save_active_dispatch`, então
`retry_count` morre na memória. O laço é impedido pela sessão deixar de existir,
não pela marca.

⚠️ O comentário foi **corrigido** para dizer isso. Persistir a marca exigiria
regravar uma sessão que acabou de ser limpa — e sessão limpa é o que impede a
"sessão zumbi" de 12/07 de voltar a falar com a seguradora.

- **Destrava:** 🤖 um `attempt` idempotente no `work_runs`, que é durável e não
  ressuscita sessão. Casa com a P-237.
- **Custa se esquecer:** hoje, nada — é dívida de precisão, não de efeito.

## P-244 · 🤖 Dois caminhos em que o travamento nunca é marcado

📊 Achado do juiz. Além do B1 (fechado):

1. A família `insurer_closed` não chega a `save_active_dispatch` no turno do
   `needs_human`, então `registrar_checkpoint` não roda e a marca **nunca
   nasce**. Com o B1 fechado ela deixa de ser arquivada — mas continua nascendo
   invisível.
2. O `_marcar_travamento` da reconciliação está num ramo que a varredura
   **exclui hoje** pelo `.or_("error_code.is.null,error_code.not.like…")`. O
   próprio comentário admite: *"estava fechado HOJE por acidente"*. É guarda de
   string sem cobertura de comportamento.

- **Destrava:** 🤖 marcar no ponto de estrangulamento também quando a família
  encerra a sessão no mesmo turno.
- **Custa se esquecer:** a causa **mais comum** de travamento é a que menos
  aparece na Fila.

## P-245 · 🤖 `insurer_phone` passou a ser mascarado no gêmeo

📊 Colateral medido da reordenação do `_classificar`: o marcador `_TELEFONE`
agora vence a lista segura, e `insurer_phone` — que é telefone de **empresa**,
não de pessoa — sai como `...4725` no gêmeo mascarado.

⚠️ Os campos que a tela de destravamento lê (`playbook_ref`, `subservice`,
`missing_slots`, `suporte_indisponivel`) **não** são afetados.

- **Destrava:** 🤖 uma exceção nomeada para telefone de seguradora, escrita como
  ENUM e não como string solta (casa com a P-233).
- **Custa se esquecer:** quem lê o gêmeo não vê para qual URA o caso foi.

---

# 🔴 O QUE A SPEC-092 DEIXOU ABERTO (25/08/2026)

## P-092-01 · 🤖 A definição do formulário viaja como **repr de Python**, não JSON

📊 Medido em 25/08/2026. O schema completo — `data-source`, `required`,
`visible` — está dentro do `response_message`, mas **não como JSON**:

```
'data-source':[{'id':'1','title':'Sim'},{'id':'0','title':'Não'}]
```

Aspas simples, escapadas dentro de uma string que já está dentro de outra. 🔴
**Nenhum caminhante de JSON o encontra** — foi por isso que o extrator devolveu
18 componentes **sem opção nenhuma**, e o CONTROLE (o formulário da HDI, que já
está transcrito e portanto É extraível) foi o que apontou que o culpado era o
extrator.

⚠️ **E `data-source` tem DUAS formas**, o que dobra o trabalho:

```
inline    'data-source': [{'id':'1','title':'Sim'}, …]        (HDI)
ligação   'data-source': '${data.dt_TiposEndereco}'           (Yelum endereço)
          resolve em 'screenState':{'data':{'dt_TiposEndereco': …}}
```

Um transcritor que só entenda a primeira produz componente **sem opção** — e
componente sem opção não pode ser respondido.

- **Destrava:** 🤖 um decodificador de repr embutido, com o formulário da HDI
  como **linha de controle** (ele já está transcrito, então o extrator certo
  tem de reproduzi-lo).
- **Custa se esquecer:** cada formulário novo continua exigindo transcrição
  manual, e a SPEC-092 §8 item 5 (*"cada família com o próprio formulário
  mapeado"*) fica impossível de escalar.

## P-092-02 · 🤖 A 4ª tela da Yelum: 6 telas e 18 campos recuperados, **zero ids**

📊 `1579547063352571` — *"Automóvel - Informar endereço V2"*, Yelum, 03/08/2026,
`source=live`. Mora dentro de `interactive.raw_out`, um blob de 11.940
caracteres — a **terceira** forma de armazenamento do acervo, que nenhum leitor
conhece.

```
📊 recuperado:  6 telas · 18 campos · nome e rótulo · 0 ocorrências de PII
🔴 faltando:    os `id` das opções (depende da P-092-01)
```

🔴 **Este é o formulário cuja resposta é PARA ONDE O GUINCHO VAI.** Entregar meio
schema seria pior que nenhum: `montar_resposta_de_flow` trataria o campo como
respondível e o produto mandaria um id inventado.

- **Destrava:** 🤖 a P-092-01.
- **Custa se esquecer:** o segurado é atendido, mas por uma pessoa — o
  acionamento não fecha sozinho nessa tela.
- **O que JÁ protege:** `test_a_tela_sem_schema_nao_e_chutada` — tela sem schema
  vira `needs_human` com motivo, e id nunca é inventado a partir do título.

## P-092-03 · 🧑 O `format` do envio exige patch 0007 do GO e rebuild de imagem

📊 O patch 0005 fixa `Format: waE2E.InteractiveResponseMessage_Body_DEFAULT`
(**0**) em código, e a captura real traz `body.format = 1` = `EXTENSIONS`.
O Python **não controla isso**: o campo nem sai do achatador.

⚠️ **Nenhuma medição diz que isso quebra** — a prova de 03/08 teve 200 com
`DEFAULT`. O que se sabe é que **não é o que o cliente humano manda**.

- **Destrava:** 🤖 escrever o patch 0007 (o GO lê `format` do corpo) · 🧑 rebuild
  da imagem e deploy.
- **Custa se esquecer:** se a seguradora validar o campo, a resposta é descartada
  em silêncio — e o sintoma é indistinguível de tudo o mais que esta SPEC mata.
- **O que JÁ protege:** `test_o_formato_do_envio_e_honesto` fixa a lista fechada
  de chaves do fio e **quebra** no dia em que o GO mudar, obrigando a reescrever
  a história em vez de deixá-la vencida.

## P-092-04 · 🤖 O fixture "exemplar de ouro" é uma cópia TRUNCADA da captura

📊 `backend/tests/fixtures/clique_humano_no_formulario_18_07.json` tem
`wa_flow_response_params.response_message` com **46 caracteres**. A linha real no
banco tem **4.854**.

🔴 **O Gate D da SPEC exige `paramsJSON` "byte a byte igual ao exemplar de
ouro".** Contra este fixture, isso consagraria a truncagem.

- **Destrava:** 🤖 regerar o fixture a partir da linha real, mascarado — e
  **conferir o `sha256` contra o banco**, senão o próximo truncamento passa igual.
- **Custa se esquecer:** um gate que compara contra um exemplar errado aprova o
  errado com toda a confiança de quem compara byte a byte.

## P-092-05 · 🤖 `app.services.__init__` importa `fastembed`, e o CI não instala

📊 `ura_simulator.simulate` faz `from app.services import insurer_dispatch_service`
**dentro da função**. O `app/services/__init__.py` importa `fastembed`, e o
`gate.yml` **não roda `pip install`**.

🔴 **O ensaio inteiro é irrodável em CI por uma dependência de embeddings que ele
não usa.** E o mesmo vale para qualquer caminho que faça `from app.services
import X`.

- **Destrava:** 🤖 importar por módulo (`from app.services.insurer_dispatch_service
  import …`) ou tornar o `__init__` preguiçoso.
- **Custa se esquecer:** todo guarda que exercite o simulador tem de montar o
  pacote à mão — como o desta SPEC teve de fazer — e um dia alguém não vai fazer.

## P-092-06 · 🤖 A TERCEIRA régua com o mesmo ponto cego

📊 Achado do investigador, fora do escopo. `conversation_auditor.detect_drift`
(`:56-67`) chama **só** `match_ura_step`, nunca `detect_native_flow` — o mesmo
furo que o `replay.py` tinha antes do C6.

🔴 **Toda tela de formulário com `expected` é contada como drift/regressão hoje.**

- **Destrava:** 🤖 a mesma inversão da D.2, no auditor.
- **Custa se esquecer:** a régua acusa regressão onde o produto acertou, e quem
  olhar o painel aprende a ignorá-lo.

## P-092-07 · 🤖 Um QUINTO `flow_id` que ninguém contou

📊 `hdi-auto`, 2026-07-15T16:35:46Z, sessão `68f511d9` — *"…preencha o formulário
para informar **onde o veículo está**"*. É o gêmeo de ORIGEM do formulário de
DESTINO da P-084-68.

Hoje não casa flow nem passo, e cai em `formulario_nativo_desconhecido` pelo
marcador — **comportamento correto**. Mas o `flow_id` dele não está entre os
quatro que o `corridor_playbooks.py` lista.

- **Destrava:** 🤖 extrair o id do `raw_out` daquela sessão (depende da P-092-01).
- **Custa se esquecer:** a contagem de formulários conhecidos está errada, e
  planejamento em cima dela também.

## P-092-08 · 🤖 Dois corredores residenciais com resíduo do gatilho antigo

📊 `hdi-residencial-whatsapp@v1` (`:3972`) e `yelum-residencial-whatsapp@v1`
(`:4570`) ainda carregam o `handoff_trigger` `r"formulario nativo"`, removido dos
de auto em 03/08. Os dois **não declaram `native_flows`**.

⚠️ **Não é defeito hoje** — o gatilho é lido depois de
`_responder_formulario_nativo`, então o motor já pausa antes. É assimetria.

- **Destrava:** 🤖 remover, junto com a próxima revisão dos residenciais.
- **Custa se esquecer:** o próximo leitor conclui que residencial trata
  formulário de outro jeito, e não trata.

## P-092-09 · 🤖 59 telas de corpus sem playbook, fora de toda medição

📊 `tokio-residencial.jsonl` e `tokio-condominio.jsonl` — `list_playbooks()`
devolve 14 refs e nenhuma cobre esses dois arquivos. **Ficaram fora de toda
medição de corpus, em silêncio.**

- **Destrava:** 🤖 declarar os dois playbooks, ou tirar os arquivos do corpus com
  o motivo escrito.
- **Custa se esquecer:** toda medição sobre "o corpus inteiro" exclui 59 telas
  sem dizer.

## P-092-10 · 🤖 O formulário não tem trava de laço: 8 telas iguais = 8 envios

📊 Achado do red team, com linha de controle — **e não é desta SPEC**:

```
volta 1..8: state=ura envios=1..8
BASE 8b49fdb envios=8  ·  HEAD envios=8
_would_loop diria laço? True   ← existe, responde certo, e NUNCA é chamado
step_counts = None   retry_count = None
```

🔴 O formulário nativo **é** o passo de confirmação da família HDI/Yelum — a
própria `_POLITICA_DE_RETOMADA` escreve isso para justificar `DIRETO_AO_HUMANO`.
Uma URA que reapresenta a tela recebe N confirmações. **A duplicação que a
política fecha entre sessões está aberta dentro de uma.**

⚠️ A guarda por bolha (painel) fecha o caso da RAJADA; não fecha o caso da URA
reapresentando a mesma tela em turnos diferentes.

- **Destrava:** 🤖 chamar `_would_loop` em `_responder_formulario_nativo`, ou
  contar o formulário em `step_counts`.
- **Custa se esquecer:** N prestadores confirmados para um acionamento só.

## P-092-11 · 🤖 `formulario_envio_falhou` cobre um caso em que se SABE que nada saiu

📊 Achado do red team. `raise ValueError("envelope_do_flow ausente")` mora
**dentro do mesmo `try`** cujo `except` grava `formulario_envio_falhou`:

```
OK  flow_id-dict   state=needs_human  reason=formulario_envio_falhou  envios=0
OK  flow_id-lista  state=needs_human  reason=formulario_envio_falhou  envios=0
```

Zero chamadas ao transporte, e o motivo é o único da lista que significa *"pode
ter chegado, não dá para saber"*. Quem tria lê "envio falhou" e evita reenviar —
quando nada foi enviado.

- **Destrava:** 🤖 um motivo próprio (`formulario_sem_envelope`), classificado
  em `_POLITICA_DE_RETOMADA` com o porquê.
- **Custa se esquecer:** o humano não reenvia uma resposta que nunca saiu.

## P-092-12 · 🤖 `params` sobrescreve o `flow_token` no `paramsJSON`

📊 `corpo = {"flow_token": token, **params}` — se `params` trouxer a chave
`flow_token`, ela vence. E o comentário três linhas abaixo raciocina
**exatamente ao contrário** para `wa_flow_response_params` (*"vai por ÚLTIMO de
propósito"*).

💭 Latente: hoje `params` vem do nosso schema. Mas a assimetria entre duas linhas
vizinhas é o tipo de coisa que o próximo leitor resolve para o lado errado.

- **Destrava:** 🤖 pôr o `flow_token` por último, ou recusar `params` que o traga.

## P-092-13 · 🤖 Comentário vencido sobre `version`, no arquivo que decide o envio

📊 `evolution_go.py:189` afirma *"as QUATRO capturas trazem version=3 (4 de 4)"*.
Cinco linhas acima do valor, `:283-286` ainda diz 💭 *"**1** é o que o fork do
Baileys usa … a captura de 18/07 **não traz este campo**"*.

🔴 `CLAUDE.md` §9.3 e §12.1: **texto vencido reinfecta o leitor seguinte.** O
próximo a ler o 💭 reverte para 1.

⚠️ E o mesmo vale para o patch Go 0005, cujo comentário *"a única instância
capturada não traz version nenhum"* foi declarado falsificado e **não corrigido**
— mas mexer no patch exige rebuild de imagem (P-092-03).

- **Destrava:** 🤖 apagar o 💭 vencido do Python; 🧑 o do Go junto do patch 0007.

## P-092-14 · 🤖 O corpus não exercita a guarda que ele atesta

📊 Achado da lente da medida. A varredura que prova que a inversão D.2 é estreita
roda sobre 4.220 telas — e `a_tela_e_formulario()` devolve **True em zero
delas**, porque o corpus foi colhido **antes** do conserto do `galaxy_message` e
não tem marcador nem `interactive`.

> **O controle mede a população que a mudança não alcança.**

E a projeção correta não é "uma tela": 📊 **25 telas mencionam formulário e casam
passo de URA**; 21 (9 azul + 12 porto) dizem *"Ou, se preferir, preencha o
formulário abaixo"*. A guarda de `options` (painel) as protege — mas isso vale
para a forma que o parser vê, e a de azul/porto **não foi medida**.

- **Destrava:** 🤖 recolher o corpus depois do BLOCO B, com `interactive`.
- **Custa se esquecer:** a régua continua medindo um produto diferente do que roda.

## P-092-15 · 🤖 Números do relatório que a lente da medida corrigiu

📊 Três afirmações minhas não reproduzem, e ficam corrigidas aqui:

| eu escrevi | 📊 o número certo |
|---|---|
| *"50 das 62, de 13 a 20 s antes"* | **57–59** conforme a definição; intervalo **10–296 s**, mediana **64 s**. 💭 O `50` veio da tabela de controle da B.2 (que são `button_reply`) e migrou para uma frase sobre `flow_reply` |
| *"`response_message` tem 4.854 caracteres"* | 4.854 é **um** exemplar. Os outros: 6.388 · 1.933 · 1.933 · 3.908 |
| *"id opaco `pd-dc-…`, não reconstruível do título"* | 📊 **8 linhas** de 1.602 cliques com id; **1.112 têm `id == title`**. A conclusão continua certa; a **razão** generalizava 0,5% do acervo |

- **Custa se esquecer:** número sem marca, em documento novo, é defeito de
  revisão — e número **com** marca que não reproduz é pior.


---

## P-246 · 🔴 O vazamento de mutação está CONTIDO, não fechado

**Aberta em:** 25/08/2026 · **Dono:** 🤖 execução

📊 Duas rodadas completas depois dos consertos de hoje:

```
13m25    557 passed · 0 falhas · árvore limpa
11m57    557 passed · 1 falha  · árvore limpa
         └─ test_a_arvore_ficou_limpa_no_fim
```

**O que foi consertado hoje:** o estouro de tempo passou a matar a **árvore** de
processos (`taskkill /F /T`), a trava virou **do kernel** (`msvcrt.locking`), a
espera dela caiu de 900s para 90s (contra um teto de 120s), e a rede de segurança
passou a **restaurar** em vez de só acusar.

🔴 **O que NÃO foi:** alguma mutação ainda escapa do `finally` de quem a fez, de
forma intermitente. A árvore termina limpa — a rede restaura — **mas o gate fica
vermelho sem que haja defeito de produto.**

⚠️ **E isso tem custo próprio:** um gate que fica vermelho às vezes, por motivo
que não é defeito, **ensina todo mundo a ignorá-lo.** É o `CLAUDE.md` §9.3 pelo
avesso, e é exatamente o que o docstring do arquivo diz estar evitando.

**O que destrava:** medir *qual* processo ainda escapa. A hipótese que sobra é a
mutação que roda **dentro** do próprio pytest (in-process, `exec_module`), que
nenhum `taskkill` alcança porque não é processo separado.

**O que custa esquecer:** a suíte cresce a cada SPEC (322 → 463 → 601 em três
dias). Um vermelho intermitente numa suíte de 601 testes vira ruído de fundo, e
o próximo vermelho de verdade morre junto com ele.

---

### 📊 TERCEIRA OCORRÊNCIA — 26/08/2026, SPEC-093

`git status` da SPEC-093 mostrou `backend/scripts/rubrica.py` **modificado**, com
a marca literal:

```diff
-    melhor = max(candidatos, key=lambda c: (c[1] >= 3, c[2], c[1]), default=None)
+    melhor = max(candidatos, key=lambda c: (c[1], c[2]), default=None)  # MUTACAO
```

⚠️ **E o meu próprio grep de verificação não a pegou:** eu varri
`backend/app lib app scripts` — e `scripts` resolveu para o `scripts/` da RAIZ,
não para `backend/scripts/`. Quem a encontrou foi o `git status`.

🔴 **Duas lições, e as duas são de método:**

1. **Quem vigia a árvore é o `git status`, não um `grep` com lista de pastas.**
   Toda lista de alvos escrita à mão tem um buraco, e o buraco é sempre a pasta
   em que o defeito está.
### ✅ E ESTA OCORRÊNCIA FECHOU A CAUSA — 26/08/2026

📊 **O diagnóstico, com linha de controle:**

```
rodando `test_a_regua_nao_tem_furo.py` SOZINHO ...  52 verdes, ÁRVORE LIMPA
                                                    (ele restaura quando TERMINA)
o guarda leva sozinho .........................  14 s
TETO_SEGUNDOS do harness ......................  120 s
```

🔴 **Então o vazamento exige INTERRUPÇÃO** — e o harness a produz de propósito:
no estouro do teto ele chama `_matar_a_arvore`, que mata junto o processo que ia
restaurar no `finally`. *"Contenção e restauração são objetivos opostos: quem
morre não limpa"* — está escrito no próprio arquivo.

⚠️ **A limpeza já morava no lugar certo** (`test_a_arvore_ficou_limpa_no_fim`,
que restaura a partir de `_RETRATO_DA_SESSAO`). O que faltava era o alvo:

```
ARQUIVOS_COMPARTILHADOS era uma tupla de DOIS nomes, escrita à mão
  · app/services/corridor_playbooks.py
  · scripts/replay.py
e `scripts/rubrica.py` — que a entrada C17 muta — nunca esteve nela.
```

✅ **Consertado:** a lista deixou de ser escrita à mão e passou a ser **derivada
dos próprios `MUTACOES` dos guardas**, lidos por `ast`. 📊 De **2 para 6** alvos,
e `rubrica.py` entrou. Dois guardas novos impedem a volta: um exige que todo
arquivo declarado em qualquer `MUTACOES` esteja coberto, o outro **muta
`rubrica.py` de verdade** e prova que o restaurador o alcança.

⚠️ **E o conserto criou um falso positivo, que também foi consertado.** Com a
lista mais larga, `insurer_dispatch_service.py` entrou no escopo — e a marca
`_DESLIGADO`, solta, casava a constante legítima
`_DESLIGADO = ("0","false","no","off","nao","não")`. A marca foi estreitada para
as formas do arnês (`_DESLIGADO"` e `_DESLIGADO'`, sufixo de chave). 📊 Provado
que ela **ainda pega** as três formas reais — `# MUTACAO`,
`DESLIGADO PELA MUTACAO` e `"schedule_agendado_DESLIGADO"`, que é o vazamento
original da SPEC-085 — e que o código legítimo passa.

> 🔴 **Um guarda que acusa código legítimo ensina a ignorar o guarda.**

### 📊 E O CULPADO FOI ESTREITADO — mas não nomeado

```
guardas que o harness roda ...........................  273
dos quais TOCAM `scripts/rubrica.py` .................    2
  · test_a_regua_nao_tem_furo.py ..... 14 s sozinho, árvore LIMPA
  · test_nenhuma_mutacao_foi_commitada.py ..  2 s, árvore LIMPA
TETO_SEGUNDOS do harness .............................  120 s
```

🔴 **Os dois restauram corretamente quando TERMINAM.** O vazamento só reproduz
na bateria inteira — o que confirma o mecanismo (interrupção mata o `finally`) e
**refuta** "um dos dois está simplesmente quebrado".

⚠️ **E o vermelho cai em quem estiver rodando na hora.** Na bateria de 26/08 quem
apareceu vermelho foi `test_o_passo_compartilhado_ainda_e_conferido` — que 📊
passa sozinho em 6 s com a árvore limpa. Ele era **vítima**, não culpado. É a
P-231 literal, e é por isso que o nome no vermelho não serve de acusação.

### 📊 E A EVIDÊNCIA QUE ESTREITA MAIS — duas baterias, 26/08

```
bateria 3 ....  718 coletados · 2 falhas  (o restaurador + uma VÍTIMA)
bateria 4 ....  672 passed   · 1 falha    (só o restaurador)
```

🔴 **`_JANELAS_SUJAS` NÃO acusou nenhum guarda.** O harness compara os arquivos
vigiados **antes e depois de cada subprocesso** e registra a janela suja com o
nome de quem a sujou (`_devolver_o_que_foi_sujado`). Em nenhuma das duas
rodadas ele registrou alguma — **e mesmo assim a sessão terminou suja.**

> ⚠️ Isso **elimina** a hipótese mais óbvia: a sujeira não é de um guarda-
> subprocesso que terminou. Ele seria pego na janela dele.

📊 E não é de um teste coletado pelo pytest: dos que mexem em `rubrica.py`, o
único é o próprio harness.

**A hipótese que sobra, e o repositório já a documenta:** um **neto órfão** —
processo que sobrevive ao pai morto e escreve DEPOIS, fora de qualquer janela.
É o defeito que `_matar_a_arvore` e `test_o_timeout_nao_deixa_neto_vivo`
existem para fechar, e o comentário do harness diz exatamente isso: *"o pai
morre, o neto continua mutando o corredor, e o vermelho cai em quem estiver
rodando na hora"*.

**O que CONTINUA aberto:** (1) **qual** processo sobrevive — a janela por
subprocesso não o alcança, então o instrumento tem de ser outro (um `watcher`
de mtime durante a sessão, ou o `finally` da restauração escrevendo o PID);
(2) o `pre-commit` hook. O harness restaura no fim da sessão de pytest; ele não
cobre alguém que commite no meio.

---

2. 🔴 **O guarda por marca PASSOU na mesma bateria que terminou suja.**
   📊 `test_nenhuma_mutacao_ficou_na_arvore` roda `git ls-files "*.py"` e varre
   todos por marca — não depende de lista de alvos, e é bom. Mas ele roda **na
   posição em que o pytest o coleta**, e a bateria de 862s que deixou a árvore
   suja o reportou VERDE.

   > ⚠️ **Um guarda que roda no meio não certifica o fim.** Ele responde *"a
   > árvore estava limpa quando eu rodei"*, e a pergunta é *"a árvore está limpa
   > agora"*.

   Restaurada por cópia; `MUTACAO: 0` conferido depois.

**O que destrava, então, são DUAS coisas:** o `pre-commit` hook já registrado
acima, **e** mover a checagem de árvore-limpa para um `pytest_sessionfinish` no
`conftest.py` — o único ponto que roda depois de todo o resto. Como teste, ela
nunca vai poder afirmar o que promete.

---

## P-247 · 🔴 Um guarda que olha o `HEAD` não protege o commit que está nascendo

**Aberta em:** 25/08/2026 · **Dono:** 🤖 execução

📊 Hoje, 25/08, um `git add -A` levou para o commit:

```
backend/scripts/rubrica.py
-    decidem = CR.constantes_sem_justificativa(pb, rota.servico, ...)
+    decidem = []  # DESLIGADO PELA MUTACAO
```

**Havia dois guardas. Os dois falharam, e por motivos diferentes:**

1. `_RETRATO_DA_SESSAO` vigiava `ARQUIVOS_COMPARTILHADOS` — uma lista de **dois
   nomes**. `rubrica.py` não estava nela. ✅ **Consertado hoje:**
   `test_nenhuma_mutacao_ficou_na_arvore` varre todo `.py` rastreado pela
   **marca**, sem lista de alvos.

2. 🔴 `test_nenhuma_mutacao_foi_commitada.py` pergunta ao objeto commitado
   (`git show HEAD:...`). **Quando a bateria roda, o `HEAD` ainda é o commit
   anterior.** Ele pega uma rodada tarde — e uma rodada tarde é depois do push.
   ⛔ **Este continua aberto.**

**O que destrava:** um `pre-commit` hook versionado (`core.hooksPath`), que é o
único ponto entre `git add` e `git commit`. Um teste não roda ali.

**O que custa esquecer:** 📊 é a **segunda vez** que uma mutação de `rubrica.py`
entra num commit — a primeira em 22/08 (SPEC-084.1 C12). O guarda foi escrito
depois da primeira e não impediu a segunda.

---

## P-248 · O `/health` não expõe o estado do Smith Worker

**Aberta em:** 25/08/2026 · **Dono:** 🤖 execução

📊 Lido no `/health` da `smith-api` em 25/08 20:32: os 37 sinais de `codigo`
**não incluem** o estado do worker. Duas lentes independentes discordaram sobre
ele — uma disse "vivo" (📊 2.728 `run.succeeded` no banco), outra "nada o liga"
(📊 `WORK_WORKER_IN_PROCESS` padrão OFF, sem serviço no compose, `CMD` só
`uvicorn`). **As duas podem estar certas** se a env estiver ligada só no
EasyPanel.

⚠️ E `conferir_o_que_esta_no_ar.py` cobre **2 dos 4 serviços** — `smith-worker`
e `smith-web` não têm digital. Não dá para responder "o deploy do Worker entrou?"

**O que destrava:** acrescentar `worker_ligado` aos sinais, e uma digital para
o Web.

**O que custa esquecer:** uma pergunta de operação que hoje só se responde
abrindo o painel do EasyPanel e lendo variável na mão — exatamente o que o
bloco de sinais foi criado para eliminar.

---

## P-249 · `work_effects` existe no banco, sem DDL no repositório e sem escritor

**Aberta em:** 25/08/2026 · **Dono:** 🤖 execução · **SPEC-093 BLOCO D**

📊 Medido: a tabela existe em produção, **não tem DDL em nenhuma das 68
migrations do repositório** (foi aplicada direto no Supabase — a família das 9
versões órfãs do `MIGRATIONS-AUTHORITY.md` §4), tem **0 linhas** e **nenhum
chamador de produção**.

⚠️ O BLOCO D precisava de uma chave de idempotência que não pode falhar, e
`work_effects` era a candidata óbvia. **Usá-la seria escolher uma tabela sem
escritor para a primeira coisa que não pode falhar.** Foi criada
`saudacoes_enviadas`, mínima, com o DDL no repositório.

**O que destrava:** decidir se `work_effects` ganha DDL versionado e um dono, ou
se é apagada. Enquanto ninguém decide, ela é schema que ninguém sabe explicar.

**O que custa esquecer:** a próxima pessoa que precisar de um registro de efeito
vai encontrá-la, achar que é o lugar certo, e construir em cima de uma tabela
que nenhuma migration descreve.

---

## P-250 · 🔴 `dispatch_watchdog.py` envia sem consultar `dispatch_live_enabled`

**Aberta em:** 25/08/2026 · **Dono:** 🤖 execução · **SPEC-093 BLOCO F**

📊 `dispatch_watchdog.py:379` (o Sentinela) chama `wa.send_message(...)` direto.
Todos os outros pontos de saída passam por um portão; este não.

⚠️ Hoje não morde porque os quatro agentes estão desligados e
`INSURER_DISPATCH_LIVE` não está no ambiente (P-168). **Não é trava: é sorte** —
o mesmo critério que `webhook.py:578` usa para julgar a si mesmo.

**O que destrava:** o Sentinela consultar `dispatch_live_enabled(company_id)`
antes de enviar, como os outros.

**O que custa esquecer:** no dia em que o piloto ligar, o Sentinela é o único
caminho que fala com a seguradora sem perguntar se pode.

---

## P-251 · 🔴 A rota que credita o humano não tem nenhum consumidor de UI

**Aberta em:** 25/08/2026 · **Dono:** 🤖 execução · **SPEC-093 BLOCO C**

📊 `app/api/dashboard/acionamentos-travados/route.ts` é a **única** rota que
grava `assumido_por_humano` pelo painel — e **0 matches** em `*.tsx`: nenhuma
tela a chama.

✅ O BLOCO C consertou o que dava para consertar sem tela: o `actor_type: 'human'`
que o CHECK do banco recusava, e o canal no payload. E abriu o **outro** caminho,
que não precisa de tela nenhuma: a atendente respondendo pelo WhatsApp dela
(`note_manual_outbound`) agora grava a coluna e a linha do tempo.

**O que destrava:** a Fila de travados ganhar tela, ou a rota ser removida.

**O que custa esquecer:** duas metades de um recurso, uma sem consumidor e outra
sem produtor, envelhecendo em direções diferentes.

---

## P-252 · `whatsapp/service.py` tem um `send_message` paralelo com zero importadores

**Aberta em:** 25/08/2026 · **Dono:** 🤖 execução · **SPEC-093 BLOCO F**

📊 `backend/app/services/whatsapp/service.py:129-176` define um `send_message`
que **ninguém importa**. É motor paralelo morto — `CLAUDE.md` §5.

**O que destrava:** apagar, depois de conferir que nenhum caminho dinâmico o
alcança.

**O que custa esquecer:** a próxima pessoa que procurar "como se manda mensagem"
acha dois, e escolhe o errado 50% das vezes.

---

## P-253 · `conversations.resolvido_em` e `resolucao_motivo` não têm escritor

**Aberta em:** 25/08/2026 · **Dono:** 🤖 execução · **SPEC-093 BLOCO F**

📊 As duas colunas existem e têm **0 linhas preenchidas**. Uma conversa nunca é
marcada como resolvida — o que significa que "quantos atendimentos foram
resolvidos hoje" não tem resposta.

**O que destrava:** decidir quem escreve (o agente ao encerrar? a atendente pelo
painel?) e ligar.

**O que custa esquecer:** o piloto vai gerar duas semanas de atendimento e a
pergunta mais óbvia sobre ele continua sem fonte.

---

## P-254 · A corrida do epoch: o eco `fromMe` chega DEPOIS do envio dela

**Aberta em:** 25/08/2026 · **Dono:** 🤖 execução · **SPEC-093 BLOCO C**

⚠️ Quando a atendente responde pelo WhatsApp dela, o webhook recebe o eco
`fromMe` **depois** que a mensagem já saiu. Entre o envio e o eco, o robô pode
ter falado por cima.

✅ O BLOCO C fecha a metade do REGISTRO: quando o eco chega, a coluna e a linha
do tempo passam a dizer que foi uma pessoa. ⛔ **Não fecha a metade da POSSE** —
isso é a arquitetura de epoch/fencing, que é a SPEC-086 e vem calibrada pelo
piloto, por decisão registrada.

**O que destrava:** a SPEC-086.

**O que custa esquecer:** duas vozes na mesma conversa com a seguradora, e o
segurado do outro lado.

---

## P-255 · O CHECK de `work_events.actor_type` não tem DDL no repositório

**Aberta em:** 26/08/2026 · **Dono:** 🤖 execução · **SPEC-093 BLOCO C**

📊 `ck_work_events_actor` existe no banco e aceita exatamente
`system | worker | user | agent | admin | provider`. 📊 `grep -rn "actor_type"
backend/supabase/migrations/` → **vazio**: é uma das 9 versões aplicadas sem
arquivo (`MIGRATIONS-AUTHORITY.md` §4).

⚠️ Consequência medida pelo painel: o gate `test_GATE_8` compara a constante
Python com a cópia dela mesma — **não há como comparar os dois lados**. Se o
CHECK real mudar, o teste continua verde e o INSERT continua recusado.

✅ O que dava para fazer foi feito: a lista medida e a data estão escritas no
guarda como referência inspecionável, com a query que a produziu.

**O que destrava:** trazer o CHECK para uma migration versionada (aditiva,
`ALTER TABLE ... DROP CONSTRAINT IF EXISTS` + `ADD CONSTRAINT ... NOT VALID` +
`VALIDATE`), ou um teste de contrato que rode contra uma branch Supabase.

**O que custa esquecer:** foi exatamente esta classe de defeito que fez o painel
escrever `actor_type: 'human'` — um valor que o banco recusa — e ninguém
descobrir por semanas.

---

## P-256 · A rota da saudação recebe `company_id` do chamador

**Aberta em:** 26/08/2026 · **Dono:** 🤖 execução · **SPEC-093 BLOCO D**

`GET /api/saudacao-religamento/previa?company_id=` e o `POST` de envio resolvem
a corretora pelo **parâmetro**, com a chave interna única da plataforma como
única fronteira. É o padrão da casa (`dispatch_monitor.py` faz igual), mas a
resposta desta rota carrega **identidade mascarada de segurados**.

⚠️ Hoje o único chamador é `previaDaSaudacao` no Next, que passa
`auth.ctx.companyId` — vindo da sessão. **A fronteira está de pé pelo chamador,
não pela rota.**

**O que destrava:** quando a tela de confirmação for construída, o envio tem de
resolver a corretora por sessão (`requireCompanyMember`), nunca por parâmetro.

**O que custa esquecer:** um segundo chamador, escrito por outra pessoa, passando
um `company_id` que veio do cliente.

---

## P-257 · 🔴 `git checkout --` apagou trabalho não commitado, de novo

**Aberta em:** 26/08/2026 · **Dono:** 🤖 execução

📊 Aconteceu nesta SPEC, em 26/08: uma bateria de mutação deixou o arquivo sujo,
e `git checkout -- <arquivo>` foi usado para "limpar" — **apagando três
consertos de painel não commitados** do mesmo arquivo. Recuperado da cópia de
segurança que a própria bateria tinha feito.

⚠️ É a mesma família da P-231 e a segunda vez que a lição aparece: **restaurar
mutação por `git checkout` é seguro só quando o arquivo não tem trabalho novo —
e é justamente durante um conserto que ele tem.**

**O que destrava:** um hábito, não um teste: toda bateria de mutação copia o
arquivo ANTES e restaura POR CÓPIA. O script `mut_*.py` desta SPEC faz isso e
confere o sha256 dos dois lados.

**O que custa esquecer:** trabalho de uma hora, sem aviso, com a suíte verde.

---

## P-258 · O envio da saudação continua sem tela de confirmação

**Aberta em:** 26/08/2026 · **Dono:** 🧑 Founder + 🤖 execução · **SPEC-093 BLOCO D.5**

✅ O caminho está pronto e **desligado**: ao religar o atendimento, a rota do
botão devolve `saudacao: {total, conversas, primeiro_religamento}` — a prévia,
sem mandar nada. `POST /api/saudacao-religamento/enviar` só envia com
`confirmado: true` no corpo.

⛔ **O que falta é a tela** que mostra essa prévia e tem o botão de confirmar.
Enquanto ela não existir, nenhuma saudação sai — que é o desfecho seguro.

📊 O porquê do cuidado: o robô teve **4 conversas de WhatsApp em toda a história
do produto**. A primeira vez que isto rodar será a maior coisa que ele já mandou
sozinho.

**O que destrava:** a tela, e a decisão do Founder de apertar o botão.

**O que custa esquecer:** um recurso inteiro pronto que ninguém sabe que existe —
e gente esperando. 📊 Medido em 26/08/2026, com esta query:

```sql
with ult as (
  select conversation_id,
         max(created_at) filter (where role='user')      ultimo_user,
         max(created_at) filter (where role='assistant')  ultimo_assist
    from messages group by 1)
select count(*) filter (where u.ultimo_user >= now() - interval '24 hours'
                          and (u.ultimo_assist is null or u.ultimo_assist < u.ultimo_user)
                          and c.claimed_by is null and c.claimed_by_name is null
                          and coalesce(upper(c.status),'') <> 'HUMAN_REQUESTED') elegiveis,
       count(*) filter (where u.ultimo_user < now() - interval '24 hours'
                          and (u.ultimo_assist is null or u.ultimo_assist < u.ultimo_user)) velhas
  from conversations c join ult u on u.conversation_id = c.id;
```

```
elegíveis (≤24h, sem dono, sem handoff, sem resposta) ....  25
sem resposta há MAIS de 24h ..............................  214
```

⚠️ As 214 **não recebem saudação** — é a decisão do BLOCO D.2, e o motivo está
escrito no código: acima de 24h a janela da Meta já exige template, e a saudação
vira exumação. Elas continuam na tela de Conversas, que é onde a corretora já
olha.

---

## P-259 · O destrave pelo PAINEL sai creditado ao robô — e é uma escolha

**Aberta em:** 26/08/2026 · **Dono:** 🤖 execução · **SPEC-093 BLOCO C**

O botão *assumir* de `acionamentos-travados` grava `assumido_por_humano` no
**banco** e não toca na sessão do Redis. Como o crédito do
`travamento.destravado` vem da sessão, esse destrave sai `por: robo`.

🔴 **Foi consertado e o conserto foi DESFEITO, por medição.** A versão que lia
`work_runs.unblock_state` para creditar o humano criava um defeito maior:

📊 `assumido_por_humano` é **grudento** — a escrita de `travado` filtra por
`IS NULL`, a de `retomado_pelo_robo` por `== 'travado'`, a de `resolvido` por
`IN ('travado','retomado_pelo_robo')`. **Nenhuma escrita posterior o tira.**
Creditar a partir dele fazia **todo destrave seguinte daquele run** virar
trabalho de pessoa — e a oscilação `ura ↔ needs_human` *"acontece toda hora"*
(está na docstring de `registrar_checkpoint`). A conta que o BLOCO C existe
para produzir sairia inflada para sempre.

> 🔴 O crédito mora na SESSÃO, que é por travamento. A coluna é por RUN, e um
> valor por run não sabe atribuir N travamentos.

✅ **O que continua funcionando:** o `travamento.assumido` que a própria rota
grava, com `canal: dashboard`, fica na linha do tempo. A pergunta *"uma pessoa
assumiu este caso?"* tem resposta; a pergunta *"quem destravou?"* responde
`robo` nesse caminho.

📊 **E o caminho não é alcançável hoje:** `acionamentos-travados` tem **zero
consumidores** em `*.tsx` (P-251).

**O que destrava:** ou a rota do painel escreve a marca na sessão do Redis junto
com a coluna (é uma chamada, no mesmo handler), ou a Fila ganha tela e o
caminho passa a existir — e aí vale escrever a marca.

**O que custa esquecer:** o número de trabalho humano fica **subestimado** no
canal `dashboard`. É o erro na direção segura — melhor que o inverso, que foi
medido e recusado.


---

## P-260 · 🔴 O G.3 da SPEC-093 não foi entregue, e o gate dele não sabe falhar

**Aberta em:** 26/08/2026 · **Dono:** 🤖 execução

O BLOCO G.3 pedia: **corredor desligado vira handoff**.

📊 **Não foi feito.** Nenhum arquivo de `backend/app/services/` lê
`tenant_corridors` — **o motor não sabe que um corredor está pausado.**

🔴 **E o gate ⑤ é tautológico.** `test_um_clique_liga_os_corredores.py:233-242`
assere que as strings `"needs_human"` e `"human_phase"` existem no fonte
**pré-existente**:

> **Passa hoje, e passaria com o pause inteiramente ignorado.**

⚠️ É o "sucesso silencioso" que a SPEC existe para matar — `CLAUDE.md` §9.3.

**O que destrava:** o dispatch consultar `tenant_corridors` antes de abrir o
corredor, e o gate provar isso **desligando um corredor e exigindo handoff**.

**O que custa esquecer:** a corretora desliga um corredor no dashboard, acha que
desligou, e o robô continua atendendo por ele. 🔴 **A tela mente** — e no piloto
ela é a única forma de a corretora recusar um serviço.

---

## P-261 · ⚠️ Duas sessões na mesma árvore contaminam a medição — e desta vez fui eu

**Aberta em:** 26/08/2026 · **Dono:** 🤖 execução

📊 Durante a auditoria da SPEC-093 a branch passou de **8 para 18 commits**: eu
escrevia SPECs na mesma árvore enquanto o auditor rodava a bateria.

```
o executor mediu   1 vermelho
o auditor mediu    3 vermelhos
```

🔴 **Nenhuma das duas medidas teve árvore exclusiva.** É a lição
`duas-suites-na-mesma-arvore-mentem`, violada por quem a escreveu.

⚠️ Os três vermelhos **passam sozinhos** (`6 passed`, `2 passed`) e o terceiro é
a P-246 literal — mas a atribuição não é confiável.

**O que destrava:** quem for medir a bateria toma a árvore ou mede em worktree
próprio. É a mesma trava do `PROTOCOLO-AUTOBROKERS-AAA` §10, aplicada também a
quem só escreve documento.

**O que custa esquecer:** um vermelho atribuído à SPEC errada manda a próxima
pessoa procurar o defeito no lugar certo pelo motivo errado.

---

## P-262 · 🔴 Uma linha de `route_drift` tem a `signature` CORROMPIDA — foi meu backfill

**Aberta em:** 26/08/2026 · **Dono:** 🤖 execução · **SPEC-087 BLOCO C**

📊 Medido em produção: `route_drift` id `2ab5352e…` tem
`detail.signature` com **58 caracteres** e uma marca de máscara dentro. As
outras 15 têm 64.

🔴 **A causa fui eu.** O backfill do BLOCO C passou o `detail` inteiro pelo
mascarador, e o padrão de telefone — `(?:\+?55\s*)?\(?\d{2}\)?[\s.\-]?\d{4,5}[\s.\-]?\d{4}`
— **não tem `\b` em nenhuma ponta**, então casa qualquer corrida de 10–11
dígitos dentro de um hexadecimal.

📊 Duas revisões independentes mediram o mesmo: **~17,9% de 50.000 sha256
seriam destruídos**.

⚠️ **E `signature` é a chave de dedupe do drift.** Mutilada,
`_same_unresolved_drift` nunca mais casa: a linha duplica e o Founder recebe o
mesmo alerta por WhatsApp a cada varredura.

✅ **Consertado para o futuro:** `_mascarar_fundo` agora ignora as chaves que não
são texto (`signature`, `hash`, `digest`, `fingerprint`, `id`, `message_id`,
`checksum`), e o guarda passou a usar um sha256 **que casa o padrão de
telefone** — antes ele usava `"abc123"`, um valor que nenhum padrão alcança, e
por isso a asserção era tautologia (§9.3).

⛔ **O valor original está perdido** — não existe desmascarar.

**O que destrava:** nada precisa ser feito com urgência. Aquele drift vai
duplicar **uma vez**, e a linha nova nascerá com `signature` correta; a partir
daí deduplica. Se o Founder receber um alerta repetido de deriva, é esta linha.

**O que custa esquecer:** a próxima pessoa que investigar um alerta duplicado
vai procurar o defeito no Sentinela, e ele está no passado.

---

## P-263 · `ALFAIATE_AUTO_APPLY` não está documentada em lugar nenhum

**Aberta em:** 26/08/2026 · **Dono:** 🧑 Founder · **SPEC-087 BLOCO B**

O BLOCO B religou o Alfaiate e o deixou **descarregado**: `apply_auto_overlays`
só escreve com `ALFAIATE_AUTO_APPLY` ligada, e o padrão é desligado.

⚠️ 📊 Mas o nome da variável só existe em dois arquivos — `playbook_tailor.py` e
o teste dele. Não está no `.env`, nem em documento, nem aqui.

```
valores que LIGAM ....  1 · true · yes · on · sim   (lista fechada)
qualquer outro .......  DESLIGADO, inclusive ausente e "false"
onde setar ...........  serviço `smith-api` no EasyPanel
```

🔴 **Antes de ligar, meça:** o BLOCO B entrega a capacidade de MEDIR. Rode uma
varredura e olhe `route_drift.simulator_passed` e
`detail.vereditos_por_corredor` — se ainda houver NULL, o Alfaiate não está
medindo, e ligar a escrita seria armar o que não se sabe apontar.

**O que destrava:** a decisão do Founder, depois de ler o número.

**O que custa esquecer:** o Alfaiate volta a ser um caminho morto — o defeito
que a SPEC-087 mediu e consertou.

---

## P-264 · A fila `tela_cega` não tem leitor

**Aberta em:** 26/08/2026 · **Dono:** 🤖 execução · **SPEC-087 BLOCO A**

A tabela é chamada de *"fila de trabalho, não tabela de log"* na migration e no
módulo — mas 📊 `grep -rn "tela_cega"` fora do escritor e dos testes devolve
**zero**: sem rota de API, sem tela, sem consulta.

⚠️ E o `status` aceita três valores (`aberta`, `virou_passo`, `ignorada`); só o
primeiro tem escritor.

📊 **Volume estimado, medido:** `observed_events` (`direction='in'`) nos últimos
45 dias tem 16.275 eventos e 4.894 tuplas distintas `(corretora, seguradora,
hash)` — o teto absoluto se 100% das telas fossem cegas. À taxa medida de
22,3%, **~1.100 linhas por 45 dias**, ~9k/ano. **Não há problema de volume.**

**O que destrava:** a tela da fila, ordenada por `visto_quantas_vezes desc` e
filtrada por `e_menu` — 📊 27 das 378 cegas são menu, e são as que mais doem.

**O que custa esquecer:** duas semanas de piloto enchem a fila e ninguém vê uma
linha. É o mesmo formato da P-251.

---

## P-265 · O contador da fila é read-modify-write

**Aberta em:** 26/08/2026 · **Dono:** 🤖 execução · **SPEC-087 BLOCO A**

`registrar_tela_cega` lê `visto_quantas_vezes`, soma 1 e grava. ⚠️ Duas réplicas
que leem 5 gravam 6 as duas — o UNIQUE guarda a LINHA, **nada guarda o
CONTADOR**. E é o contador que a SPEC diz ordenar a fila.

**O que destrava:** um `rpc` de incremento atômico no Postgres, ou uma coluna
`bigserial` de eventos com `count(*)` na leitura.

**O que custa esquecer:** a prioridade da fila fica subestimada exatamente nas
telas mais frequentes — que são as que mais importam.

---

## P-266 · Nome próprio em saudação solta passa pelos dois mascaradores

**Aberta em:** 26/08/2026 · **Dono:** 🤖 execução · **SPEC-087 BLOCO C**

📊 Medido com entradas sintéticas: `"Ola JOAO CARLOS DA SILVEIRA, sua
solicitacao foi registrada"` passa **intacto** por `templatize` e por `redigir`.

✅ `templatize` pega nome **com rótulo** (`"Segurado: X"` → `"Segurado: {NOME}"`),
e a regra dele **nunca atravessa quebra de linha** — de propósito. 📊 Quando
atravessava, apagava opção de menu (`"Botão 2: Falar com atendente"` →
`"{NOME} 3: Encerrar"`) em quatro mapas: é a P-164.

> ⚠️ **Preservar o menu vale mais que pegar o vocativo** — e para esta fila
> especialmente: 📊 27 das 378 telas cegas são menu.

⛔ **Não está escondido:** está aqui, e está na docstring de `mascara_de_tela`.

**O que destrava:** uma regra de vocativo ancorada em saudação
(`^(Olá|Bom dia|Prezad[oa])\s+[A-ZÀ-Ú][\w]+`) — estreita o suficiente para não
alcançar rótulo de opção. Precisa de contraprova contra o corpus de menus antes
de entrar.

**O que custa esquecer:** o campo se chama `texto_mascarado`, e quem confia no
nome vai tratar a linha como não-sensível.

---

## P-267 · 🔴 A âncora do Alfaiate casa o texto CRU, e a produção casa o NORMALIZADO

**Aberta em:** 26/08/2026 · **Dono:** 🤖 execução · **achado do juiz da SPEC-087**

📊 **Medido pelo juiz de confirmação, com LINHA DE CONTROLE** — as 1.421 telas
reais do corpus, contra a implementação de ANTES e a de agora:

```
CONTROLE [antes: re.escape(cru[:60])]   vazia=0    CASA=128   NÃO CASA=1.293
HEAD     [depois: mascarada]            vazia=28   CASA=120   NÃO CASA=1.273
```

⚠️ **A SPEC-087 não causou isto e praticamente não mexeu no número.** A causa é
anterior: `match_ura_step` casa a âncora contra `_norm(mensagem)` — que tira
**acento** e o marcador de **negrito** do WhatsApp —, e a âncora é construída a
partir do texto **cru**, que tem os dois.

🔴 **Mas ele esvazia o propósito do BLOCO B:** quando o Founder puxar o gatilho
do `ALFAIATE_AUTO_APPLY`, **~90% do que o Alfaiate escrever nasce inerte**.

⚠️ E toda asserção de âncora da SPEC-087 mede contra o texto CRU — que **não é o
alvo que a produção usa**. Os guardas estão certos sobre o que afirmam; o que
falta é um que afirme o alvo real.

**O que destrava:** construir a âncora a partir de `_norm(texto)` em vez do cru,
com um guarda que case contra `_norm(mensagem)` — o mesmo alvo do casador. ⚠️ E
com contraprova no corpus: 📊 se o número não subir muito acima de 128, a causa
é outra e vale medir antes de mexer.

**O que custa esquecer:** ligar o auto-apply e concluir, do silêncio, que o
Alfaiate não funciona — quando o que não funciona é o casamento da âncora.

---

## P-268 · A máscara da fila roda no texto inteiro antes de cortar

**Aberta em:** 26/08/2026 · **Dono:** 🤖 execução · **SPEC-087 BLOCO A**

✅ Consertado o essencial: `linha_da_fila` passou a cortar em `2 × 1.200` **antes**
de mascarar, então o pior caso ficou limitado.

📊 O juiz mediu por que isso importa: `templatize` é **super-linear** — 6,8 s
para 400 quebras de linha, 21,7 s para 600, 17,4 s para 50.000 caracteres. E o
gancho roda no laço de eventos, via `create_task`, para toda tela que não casa
passo.

📊 **E mediu que não dói hoje:** o corpus real tem mediana de 122 caracteres, p95
de 399 e máximo de 1.359 — e `linha_da_fila` custa **2,64 ms por tela**.

**O que destrava:** se algum dia a fila passar a receber texto longo (replay,
documento colado), medir de novo e considerar `asyncio.to_thread`.

**O que custa esquecer:** um worker congelado por uma tela, e o sintoma
aparecendo em qualquer lugar menos aqui.

---

# SPEC-090 · o atendimento de ontem vira conserto de hoje

## 🧑 P-090-A · ONDE a Regina e a Saionara escrevem a nota — decisão do Founder

**Aberta em:** 26/08/2026 · **Dono:** 🧑 **Founder** · **🔴 antes do piloto**

📊 **A SPEC pede o impossível num dos dois caminhos, e a medição é curta:**

```
evolution_go_events.py:47   force_from_me = ev in ("sendmessage", "send.message")
evolution_inbound.py:847    if from_me: return {**out, "skip": True,
                                                "skip_reason": "from_me"}
```

⛔ **`fromMe` é o ECO de uma mensagem que o WhatsApp JÁ ENTREGOU.** Quando o
webhook chega, o segurado já leu. O gate ② da SPEC — *"🔴 ZERO chance de o
`#nota` chegar ao segurado"* — **não tem como ser cumprido** se ela escrever
`#nota` na conversa do segurado. A SPEC trata isso como o risco *"se o prefixo
escapar uma vez"*; medido, **é o comportamento padrão desse caminho.**

✅ **O que foi entregue cobre os dois, e diz a verdade sobre cada um:**

| onde ela escreve | o que acontece | `origem` |
|---|---|---|
| **chat do painel** | ⛔ o produto INTERCEPTA antes de enviar. Nunca sai. | `painel` |
| WhatsApp dela | capturada, ⛔ não pausa a IA — mas já foi entregue | `whatsapp` |

E o resumo de terça-feira avisa: *"⚠️ N destas foram escritas na própria conversa
do WhatsApp — o produto só as viu DEPOIS de o WhatsApp entregar."*

**O que destrava:** 🧑 **dizer às duas, na segunda de manhã, onde anotar.** A
recomendação medida é **o chat do painel** — é o único lugar onde o produto pode
garantir que a nota não sai. Se elas anotarem no WhatsApp mesmo assim, nada
quebra; o segurado é que lê o bastidor.

**O que custa esquecer:** um segurado lendo *"#nota o robô perguntou a placa
duas vezes"* no meio do próprio atendimento.

---

## 🧑 P-090-B · A nota do WhatsApp precisa saber quem é da equipe

**Aberta em:** 26/08/2026 · **Dono:** 🧑 Founder · **desejável, não bloqueia**

📊 Medido em 26/08: `integrations.alert_target` existe nas três integrações
conectadas e tem a chave **`internal_numbers` VAZIA** nas três.

💭 Com ela preenchida, o produto poderia recusar tratar como nota uma mensagem
vinda de um número que não é da equipe — hoje qualquer `fromMe` com o prefixo
vira nota, e `fromMe` é sempre a corretora, então o risco é baixo.

**O que destrava:** 🧑 preencher `internal_numbers` com os telefones da Regina e
da Saionara. **O que custa esquecer:** pouco hoje; vira relevante quando a
corretora tiver mais gente com acesso ao mesmo WhatsApp.

---

## P-090-C · `operational_view` tem o mesmo teto silencioso da P-090-03

**Aberta em:** 26/08/2026 · **Dono:** 🤖 execução

📊 `operational_view.py` lê `agent_activities` e `conversation_scorecards` com
`.limit(200)` e **nada no texto diz que houve corte** — exatamente o defeito que
a P-090-03 registra em `conversation_auditor.py`.

✅ A seção NOVA (travamentos e notas) declara o próprio corte em `truncado`. ⚠️
As duas seções antigas, não.

**O que destrava:** paginar as duas com o mesmo `_paginar` do BLOCO D, ou pelo
menos comparar `len(dados)` com o limite e escrever a linha de aviso.
**O que custa esquecer:** num dia de 250 atividades, o resumo conta 200 e parece
completo.

---

## P-090-D · `attendance_sessions` e `observed_sessions` têm as MESMAS colunas

**Aberta em:** 26/08/2026 · **Dono:** 🤖 execução · **cheiro de §5**

📊 Medido em 26/08 — as duas têm exatamente
`company_id · counterparty · created_at · id · insurer_key · last_event_at ·
observer_number · ramo · servico · started_at · status · summary`:

```
attendance_sessions ... 12.586 linhas   (só a Resulta na amostra)
observed_sessions .....    579 linhas   (Resulta e AutoFleet)
```

⚠️ **Não é defeito conhecido — é uma pergunta sem resposta.** Duas tabelas com a
mesma forma e populações diferentes ou são duas coisas com nome ruim, ou são a
mesma coisa duplicada (§5). 🔴 E a SPEC-090 testou o `session_id` dos transcripts
contra `observed_sessions` e concluiu *"não casa com nada"* — quando ele casa
`attendance_sessions` em **95 de 95 (100%)**. **A confusão entre as duas já
custou a premissa central de uma SPEC.**

**O que destrava:** descobrir quem escreve em cada uma e decidir se consolida.
**O que custa esquecer:** a próxima SPEC repete a mesma conclusão errada.

---

## P-090-E · O dia do relatório é UTC, e o piloto é UTC−3

**Aberta em:** 26/08/2026 · **Dono:** 🧑 Founder decide · 💭 impacto pequeno

⚠️ `periodo='ontem'` usa o dia de calendário **em UTC**. O piloto é em
Florianópolis (UTC−3): *"ontem"* para a Regina termina às **03h00 UTC de hoje**,
então três horas do fim do dia dela caem no "hoje" do relatório.

✅ **A escolha está declarada no código e no rótulo** — o resumo diz
`período: ontem (2026-08-25, UTC)`. ⛔ Escolher um fuso sem o Founder decidir
seria trocar um erro conhecido por um escondido.

**O que destrava:** 🧑 dizer se o dia do relatório é UTC ou `America/Sao_Paulo`.
**O que custa esquecer:** um atendimento das 22h de segunda aparecer no relatório
de quarta.

---

## P-090-F · A fila `notas_da_atendente` não tem tela

**Aberta em:** 26/08/2026 · **Dono:** 🤖 execução

✅ As notas entram, ficam mascaradas, ligam-se à conversa e saem no resumo de
terça-feira pelo chat. ⛔ **Não há tela** — quem quiser reler as notas de uma
semana precisa da query.

⚠️ Isto é escolha da SPEC (*"sem tela nova"*), não esquecimento. Registrado
porque a SPEC-058 pode querer a fila junto com a `tela_cega` (P-264), que está
na mesma situação.

**O que destrava:** uma aba na tela `app/dashboard/atendimentos/fila`, que já
existe. **O que custa esquecer:** as duas filas viram tabelas que só o Claude
Code lê.

---

# SPEC-086 · o atendimento termina e o produto sabe

## 🔴 P-086-A · `resolvido_pelo_segurado` está no CHECK e **não tem escritor**

**Aberta em:** 26/08/2026 · **Dono:** 🤖 execução

O motivo é um dos cinco valores aceitos, e nenhum caminho do produto o grava
hoje. Quatro dos cinco têm escritor:

```
acionamento_concluido    ✅ o dispatch, ao chegar em `resolvido`
encaminhado              ✅ o dispatch, ao chegar em `encaminhado`
fechado_por_humano       ✅ o botão de encerrar do painel
expirou                  ✅ o vigia, depois de 3 avisos ignorados
resolvido_pelo_segurado  🔴 NINGUÉM
```

⚠️ **E foi decisão, não esquecimento.** O sinal seria o segurado dizer *"já
resolvi"* — e a única forma de detectar isso hoje é o modelo interpretar texto
livre. ⛔ Um LLM decidindo sozinho que o atendimento acabou fecharia conversas
vivas, e o §12.1 vale aqui: um motivo inventado é pior que motivo nenhum.

**O que destrava:** uma ferramenta que o próprio agente chame — como
`request_human_agent` já é — em vez de inferência sobre texto. 💭 O piloto vai
mostrar com que frequência isso acontece de verdade.

**O que custa esquecer:** pouco. Estas conversas hoje ficam NULAS, que é a
verdade; o risco seria o contrário.

---

## 🔴 P-086-B · `abrir_espera` existe e **ninguém chama**

**Aberta em:** 26/08/2026 · **Dono:** 🤖 execução · **🔴 antes do piloto**

✅ A tabela existe, o repositório existe, o vigia varre, o contador expira, e os
guardas cobrem tudo. ⛔ **Nenhum caminho do produto abre uma espera.**

⚠️ **Isto é o BLOCO B honesto:** a SPEC pede *"a espera vira objeto"*, e o
objeto existe. Quem decide **quando** começar a esperar é o atendimento, e essa
decisão precisa dos tempos que ninguém mediu ainda — que é literalmente o que a
§6 da SPEC diz sobre os *perfis de follow-up*: *"depende de tempos que ninguém
mediu; volta quando o piloto medir os tempos"*.

📊 E a consequência é visível: `work_waits` = **0 linhas**, então o vigia varre
uma tabela vazia e o contador da sexta-feira mostra `ainda_esperam: 0`.

**O que destrava:** decidir três prazos — quanto o produto espera o segurado, a
seguradora e a corretora antes de considerar que a espera venceu. 💭 O piloto
dá os três números na primeira semana.

**O que custa esquecer:** a metade mais cara da SPEC-086 fica de enfeite.

---

## P-086-C · O contador de lembretes vive só no Redis

**Aberta em:** 26/08/2026 · **Dono:** 🤖 execução · gate ③ do BLOCO C.1

⚠️ `reivindicar_o_aviso` e `contar_lembrete` guardam estado no Redis com TTL.
**Ele não sobrevive a um Redis vazio** — reinício sem persistência, troca de
instância, `FLUSHALL`.

📊 A consequência é limitada e mensurável: o contador zera, e o grupo recebe
**um ciclo extra de lembretes** por conversa que ainda estava aberta.

✅ **E o BLOCO C.1 tornou isso detectável:** `handoff.teto_de_lembretes` agora é
evento contável em `work_events`. Um Redis que zerou aparece como o teto sendo
atingido duas vezes para a mesma conversa.

**O que destrava:** ou confirmar que o Redis desta instalação tem persistência,
ou mover o contador para `work_events` (que é durável e já guarda o evento).
**O que custa esquecer:** ruído no grupo depois de um deploy — o defeito que o
conserto de 21/08 existe para evitar.

---

## P-086-D · Os 5 `work_runs` presos continuam presos

**Aberta em:** 26/08/2026 · **Dono:** 🧑 operação

📊 Medido em 26/08: **5** runs em `queued`, o mais velho há **29 dias**, todos
`intelligence.detect_signals`.

⚠️ **Esta SPEC os torna VISÍVEIS, não os desatola** — é o que a própria SPEC diz
em P-086-02. ⛔ E desatolar é decisão de operação: um run de 29 dias que volta a
rodar processa um dia que já passou.

⚠️ **E eles não são atendimento.** A SPEC os usa como prova de que o atendimento
apodrece; medido, são jobs de background. O buraco é real — ninguém foi avisado
em 29 dias — mas é outro buraco.

**O que destrava:** 🧑 decidir entre cancelar os cinco ou deixá-los rodar.
**O que custa esquecer:** a fila de inteligência tem cinco trabalhos que nunca
vão acontecer, e ninguém sabe.

---

## P-086-E · `work_effects` continua sem DDL no repositório e sem escritor

**Aberta em:** 26/08/2026 · **Dono:** 🤖 execução · **herdada (P-086-01)**

📊 Medido: a tabela **existe no banco** e tem **0 linhas**. ⚠️ E ela tem **RLS
ligada com ZERO policies** — o precedente que a SPEC cita para exigir o teste de
dois tenants em `work_waits`.

**O que destrava:** achar o manifesto que a criou, ou escrever o DDL faltante
(`MIGRATIONS-AUTHORITY.md` — 9 versões aplicadas sem arquivo).
**O que custa esquecer:** o `ROLLBACK` de qualquer SPEC futura que a toque não
tem como ser escrito.

---

# SPEC-089 · a régua não sobe quando deixa de medir

## P-089-A · 🔴 A régua ainda não vê o corpo do atendimento

**Aberta em:** 26/08/2026 · **Dono:** 🤖 execução

✅ O eixo F passou a ler `work_steps` e `work_events` — a régua **vê o
travamento**. ⛔ Ela continua sem ver a conversa: o turno do agente, o do
atendente e o do segurado.

📊 A causa é a mesma que a SPEC nomeia e que este bloco **não** consertou: o
corpus (`backend/tests/corpus/telas_reais/*.jsonl`, 16 arquivos, 4.279 linhas)
**não tem campo `direction`** — só tem tela de seguradora.

⚠️ **Reconstruir o corpus não era escopo desta SPEC** (a §C diz literalmente
*"não é reconstruir o corpus"*), e continua não sendo. Mas a régua mede a rota
do robô, não o atendimento.

**O que destrava:** um corpus com `direction`, alimentado pelo Espelho — que já
guarda os dois lados. **O que custa esquecer:** a régua diz `AAA` sobre uma rota
cujo segurado ficou sem resposta, porque ela nunca olhou para essa metade.

---

## P-089-B · ⚠️ O eixo F cobre 4 acionamentos, não 43 rotas

**Aberta em:** 26/08/2026 · **Dono:** 🤖 execução · **destrava sozinha**

📊 Medido: existem **4** `work_runs` de acionamento na história, todos
`allianz-residencial-whatsapp@v1` (3 `eletricista`, 1 `maquina_de_lavar`).

⚠️ Então o eixo F hoje tem dado para **duas** das 43 rotas. As outras 41 tiram
nota cheia por *"não travou"* — que é a resposta **correta** (elas realmente não
travaram: não houve acionamento nenhum nelas).

🔴 **Mas é uma verdade fraca**, e a diferença importa: *"não travou porque é
boa"* e *"não travou porque ninguém a usou"* dão a mesma nota hoje.

**O que destrava:** o piloto. Na segunda-feira o número muda sozinho.
**O que custa esquecer:** ler o eixo F de setembro como se fosse o de hoje.

---

## 🔴 P-089-C · O nome do item `>=85% deterministico` mente sobre o corte

**Aberta em:** 26/08/2026 · **Dono:** 🤖 execução · **cosmético, mas §12.1**

O corte subiu para **100%** e a chave interna do item virou
`100% deterministico`. ⚠️ Mas o **rótulo em relatórios antigos** e a referência
em `INVENTARIO-DE-ROTAS.md` ainda dizem `>=85%`.

📊 §12.1: *"se o nome de um campo mente sobre o que ele guarda, conserte o
campo — não só o texto"*. Aqui o campo já foi consertado; falta o rastro.

**O que destrava:** regerar `INVENTARIO-DE-ROTAS.md` com a régua nova.
**O que custa esquecer:** alguém comparar uma nota de hoje com uma de ontem
como se fossem a mesma escala. ⚠️ Elas **não são** — o denominador mudou três
vezes nesta SPEC.

---

## P-089-D · 📊 A P-089-04 estava errada por 30× — e isso muda o que dá para medir

**Aberta em:** 26/08/2026 · **Dono:** 🤖 execução · **boa notícia**

A SPEC registra: *"medir uma rota custa 4m14; as 73 custariam ~5h"*, e a §E
manda *"medir uma amostra e dizer qual"*.

📊 **Medido: as 73 custam 9m59.** O 4m14 é custo **fixo** —
`VM.verificar(TESTE_DA_REGUA)` roda **uma vez**, antes de tudo, e é ele que
domina. Medir 1 rota e medir 73 custam quase o mesmo.

✅ **Consequência prática:** não há motivo para medir amostra. Esta execução
mediu as 73, quatro vezes.

**O que destrava:** nada — já está medido. Fica registrado para a próxima
pessoa não orçar 5 horas.
**O que custa esquecer:** planejar uma SPEC inteira em torno de um custo que
não existe.

---

## P-089-E · `travamentos_por_rota` lê 2.000 linhas sem paginar

**Aberta em:** 26/08/2026 · **Dono:** 🤖 execução

⚠️ O leitor do eixo F usa `.limit(2000)` em três consultas. 📊 O PostgREST
devolve no máximo **1.000** por chamada — então o teto real é 1.000, e ele é
**silencioso**.

📊 Hoje não dói: são 4 runs, 2 etapas e 0 eventos. 🔴 Depois do piloto pode
doer, e a régua passaria a medir uma fatia dizendo que mediu tudo — que é
exatamente o defeito que a SPEC-090 P-090-03 registra e que o BLOCO D dela
conserta com `_paginar`.

**O que destrava:** reusar o `_paginar` de `o_dia_de_ontem.py` (§5 — a função
existe). **O que custa esquecer:** uma rota que travou 1.500 vezes contar como
1.000, e o eixo F dar nota melhor do que a verdade.


---

## P-269 · O crash do Node sob carga da bateria — intermitente e não atribuível

**Aberta em:** 26/08/2026 · **Dono:** 🤖 execução

📊 Na bateria completa de 26/08 (árvore exclusiva, `3 failed · 921 passed ·
22m30`), um dos três vermelhos foi:

```
test_a_atendente_aperta_o_botao_e_so_o_botao::test_a_politica_de_autorizacao_passa

Assertion failed: !(handle->flags & UV_HANDLE_CLOSING), file src\win\async.c, line 76
returncode 3221226505  =  0xC0000409
```

🔴 **Não é a política: é o processo do Node morrendo.** É uma asserção interna
do `libuv`, no Windows, e o código de saída é crash de processo — não asserção
reprovada.

📊 **3 de 3 passam quando rodado sozinho.** Só cai sob a carga da bateria
completa.

⚠️ **E ele é da mesma FAMÍLIA da P-246, com causa diferente:** um gate que fica
vermelho às vezes, por motivo que não é defeito de produto. **Dois desses e o
vermelho vira ruído de fundo** — e o próximo vermelho de verdade morre junto.

**O que destrava:** medir se é contenção de processo (a bateria roda os guardas
em paralelo desde 25/08) ou se é o `MODULE_TYPELESS_PACKAGE_JSON` do
`admin-auth-policy.ts` sendo reparseado como ES module a cada chamada.
💭 A segunda hipótese tem conserto barato: `"type": "module"` no `package.json`.

**O que custa esquecer:** com a P-246 aberta, a bateria já tem **dois** motivos
de vermelho que ninguém precisa consertar. **Vermelho que não exige ação ensina
a não olhar.**

---

## P-270 · Os quatro consumidores de `messages` ainda não filtram a anotação

**Aberta em:** 26/08/2026 · **Dono:** 🤖 execução

✅ **Metade está feita:** a nota agora carrega a marca no `content`
(`📝 [nota interna] …`), então quem lê `content` **vê** que é nota, e a atendente
distingue a própria anotação de uma fala enviada.

🔴 **A outra metade não:** os quatro continuam ingerindo a linha.

```
conversation_auditor.py:90   → conversation_scorecards
garimpo_v3.py:78             → sinais e pedidos
memory_fabric.py:217         → memória da empresa
broker_insights.py:186       → insights comerciais
```

📊 `payload.nota_interna` existe e continua com **zero leitores**.

⚠️ **Por que ficou assim:** marcar o `content` foi **um arquivo** e resolve o
dano principal — a nota deixa de passar por fala ao cliente. Filtrar nos quatro
é quatro arquivos, e **qualquer consumidor futuro esquece de novo**.

**O que destrava:** um único ponto de leitura de `messages` que os quatro
passem a usar, com o filtro dentro. ⛔ Filtrar nos quatro é o conserto que
envelhece.

**O que custa esquecer:** as notas entram no aprendizado como texto marcado —
melhor que antes, e ainda assim ruído numa fonte que deveria ser só conversa.

---

# SPEC-088 · A Central de Agentes diz a verdade — 03/09/2026

## P-088-CUSTO · Custo por trabalhador não existe: `usage_events` não liga a run

📊 03/09: `usage_events` 30d = 400 linhas, **0** com `work_run_id`; `correlation_id` não casa com
`work_runs` (0 de 394); `work_runs.cost_actual_brl` = 0 em 100% de 3.494 runs. O custo de LLM que
existe vem do CHAT (`source` chat 199 · memory 193 · tool 6 · vision 2); os workflows não geram uso.
A Central mostra `custo: não instrumentado` em vez de fingir zero.
**Destrava:** `backend/app/core/callbacks/cost_callback.py:252-274` passa `work_run_id`/`work_step_id`
do contexto de run; o worker grava `cost_actual_brl`. 💭 1–2h. **Dono:** 🤖.
**Custa se esquecer:** o Founder nunca saberá quanto cada trabalhador digital custa.

## P-088-APROVACOES · `approval_requests` sem `work_run_id` no 2º escritor

📊 8 linhas, 0 com `work_run_id`, 0 pending. `work/approvals.py:98` passa o id; `billing_collection.py:789-800`
não. O join por trabalhador dá zero estrutural; a Central mostra `aprovações: não instrumentado`.
**Destrava:** o 2º escritor passa `work_run_id`. 💭 30 min. **Dono:** 🤖.

## P-088-ARTIFACTS · 33 de 118 entregas (30d) sem `work_run_id`

📊 Seis chamadores de `ArtifactService` não passam o id: `relatorios_comerciais.py:178`, `report_tool.py:263`,
`billing_collection.py:1439`, `research/adapters.py:348`, `research/radar.py:389`, `api/artifacts.py:64,70`.
Entregas órfãs não aparecem no card do trabalhador. **Destrava:** passar o id nos seis. 💭 1h. **Dono:** 🤖.

## P-088-E3 · Destilador, Lapidador e Relatório de Sábado rodam e não têm card

O BLOCO E removeu os pulsos cruzados que esses três davam em nome de outros agentes. Ficaram invisíveis
na Central — troca honesta (antes eram visíveis mentindo), mas é buraco de cobertura.
**Destrava:** três entradas em `AGENT_TASKS` com fonte própria (`attendance_distiller` → ?,
`prompt_optimizer` → drafts, `weekly_report` → artifacts do sábado) e um `beat()` em cada casa. 💭 1h. **Dono:** 🤖.

## P-088-E4 · `conversation_auditor.py:180` pulsa depois do `except` da própria função

Não é `finally`, então o gate E3 não pega — mas é a mesma doença: se a varredura estourar, `audited`
fica parcial e o card acende igual. **Destrava:** mover o pulso para o ramo de sucesso. 💭 15 min. **Dono:** 🤖.

## P-088-KEYS · `test.wf` (1 run) é lixo em `work_runs`

📊 Existe em `work_runs` sem `@registrar_workflow` no repo. Está em `SEM_CARD_POR_DECISAO`. Apagar é
escrita fora de migration. **Dono:** 🧑 decide; 🤖 executa com o comando escrito.

## P-088-CADENCIA · As cadências dos agentes de pulso Redis são declaradas, não medidas

As de `work_runs` (detector, medidor, garimpo, briefing, agrupador) foram medidas por `lag(created_at)`.
As dos 13 de pulso Redis vieram do agendador e da SPEC. Com o piloto ligado, medir e recalibrar.
**Destrava:** 14 dias de piloto + a mesma consulta. **Dono:** 🤖.

## P-088-MUT · Mutação vazou para `replay.py` durante uma rodada parcial de pytest

📊 03/09 ~00:20: `backend/scripts/replay.py` apareceu com `flow = None  # DESLIGADO PELA MUTACAO`
enquanto um builder rodava `pytest -k "... sentinel ..."` na árvore compartilhada. Restaurado do HEAD.
Na bateria completa da mesma noite, `rubrica.py` vazou também (o guarda `test_a_arvore_ficou_limpa_no_fim` pegou e
restaurou). É a P-246/P-231 outra vez: **o harness de mutação roda na árvore em que outros escrevem.**
**Destrava:** a bateria de mutação em worktree próprio, ou lock exclusivo da árvore que os builders respeitem
(protocolo v11 §10). **Dono:** 🤖. **Custa se esquecer:** um builder commita a mutação sem saber.

## P-088-AUTH · `require_master_admin` compara a chave com `!=`, não em tempo constante

📊 `backend/app/core/auth.py:54`. Pré-existente; agora é a barreira de uma rota que agrega as 4 corretoras.
**Destrava:** `hmac.compare_digest`. 💭 10 min. **Dono:** 🤖.

## P-088-TECELAO · O Tecelão sai 🟢 com produção de 8 dias porque a cadência declarada é semanal

📊 03/09, A/B do juiz de confirmação: com a nova ordem de decisão o Tecelão foi 🔴→🟢 — última produção
26/08, sem pulso registrado, cadência 7d × k=2 = 14d. O canal está morto desde 26/08 e o Observador, na
mesma tubulação, sai 🔴. O `weaver` não tem agendador próprio (`grep weaver backend/app/tasks` → 0): é
dirigido por observação, então `cadencia_pulso_s` criaria alarme falso. **Destrava:** medir o intervalo
real de `ura_maps source='observed'` com o canal de pé e declarar a cadência de produção por medição
(hoje é 💭 da SPEC). **Dono:** 🤖.

## P-088-VIGIA · O Vigia pulsa incondicional com o atendimento desligado

📊 `dispatch_watchdog.py:622` `beat("vigia_sentinela", actions)` no fim da varredura, a cada 20s, mesmo com
os 4 agentes de atendimento inativos. Hoje o card sai ⚪ pelo `desligado_quando`; se o registro tirar essa
declaração, ele sai 🟢 sem ter o que vigiar — a mesma classe do C2, um degrau adiante. E o guarda B7d prova o
🔴 da Sentinela com `desligado_quando=None`, que não é a configuração embarcada (CLAUDE.md §9.4).
**Destrava:** o pulso do Vigia só quando há atendimento ativo, e o guarda rodando a linha real do registro.
**Dono:** 🤖. 💭 30 min.

## P-088-REDIGIR · O `redaction_service` canônico come protocolo de 11 dígitos

📊 `'Seu protocolo e 000123456789'` → `'Seu protocolo e [TELEFONE]9'`. Não é regressão da 088 (o mascarador
antigo matava toda sequência de 10–14 dígitos), é dívida do serviço canônico usado por todo o produto.
**Destrava:** o padrão de telefone exige DDD válido ou separador. **Dono:** 🤖.

## P-088-FLAGS · Uma segunda lista de valores verdadeiros de env sobrou

📊 `feature_flags.env_ligada()` aceita `("1","true","yes","on","sim")`; `app/agents/nodes.py:112` tem lista própria
sem `"sim"`, num `except ImportError` que quase nunca dispara. **Destrava:** `nodes.py` importa `env_ligada`.
**Dono:** 🤖. 💭 10 min.


---

# SPEC-093-B · O sinistro deixa rastro — 03/09/2026

## P-093B-LGPD · A base legal brasileira não foi lida
🧑 planalto.gov.br devolveu ECONNRESET duas vezes em 03/09; a ANPD não tem guia final de anonimização (estudos
de 2023, consulta encerrada em 02/2024). A SPEC cita a FORMA da salvaguarda (GDPR Art. 89(1)) e minimiza por
construção (a sombra não guarda texto). **Destrava:** leitura da LGPD art. 5º, 7º, 11 e 12 com jurista antes de
qualquer uso cross-tenant ou global do corpus. **Dono:** 🧑.

## P-093B-CLASSIF · `infer_ramo_servico`: assistência vence sinistro
📊 `templater.py:1726` `servico = servico or "sinistro"`: "bati o carro, preciso de guincho" sai `auto/guincho`.
Muda a conduta do robô — decisão F-093B-01 (depois da primeira semana de piloto). **Dono:** 🧑 decide · 🤖 executa.

## P-093B-SEGURADORA · `claims.seguradora_respondeu` sem escritor; espera de seguradora sem escritor
📊 `grep -rn "abrir_espera("` → um chamador (`dispatch_router.py:1200`), sempre `ESPERANDO_HUMANO`; zero escritores
de `esperando_seguradora`; `work_waits` vazia. O evento saiu do vocabulário (versão 2) e os contadores de espera de
seguradora e prazo saem `não instrumentado`. **Destrava:** emitir o evento e a espera onde a URA responde
(`attendance_capture`/`dispatch_router`) — caminho quente do atendimento, para depois do piloto. **Dono:** 🤖.

## P-093B-RAMO · `ramo` e `seguradora_slug` nunca são preenchidos
📊 `abrir_sombra` é chamada sem os dois (`webhook.py`), e nenhum evento posterior os grava: toda variante nasce
`desconhecido × desconhecida` e o agrupamento degenera em (corretora, sequência). **Destrava:** ler a ficha/apólice no
gancho quando existir, ou um evento que os preencha. **Dono:** 🤖. 💭 1h.

## P-093B-CANDIDATO · `knowledge_candidates` nunca foi escrita em produção
📊 0 linhas; o adapter existe. A sombra escreve só `intelligence_signals` até o adapter ser exercido. **Dono:** 🤖.

## P-093B-SAUDE · `redaction_service` sem padrão de saúde (CID, laudo) nem nome/endereço por extenso
📊 10 padrões, todos ancorados em dígito. A sombra não guarda texto, então não vaza por ela; o serviço canônico
continua incompleto para quem guarda. **Dono:** 🤖. 💭 30 min.

## P-093B-RLS · `work_waits` e `intelligence_signals` com RLS ligado e 0 policies
Herda P-090-01. O isolamento é o filtro no código, testado por fixture com dois tenants (bloco [12] do guarda).
**Dono:** 🤖.

## P-093B-CORPUS · O gold corpus (4 perguntas da ref. agentevals) só existe com 20+ trajetórias reais
Medir em 14 dias de piloto. **Dono:** 🤖.

## P-093B-TERCEIRO · 2.187 sessões históricas com palavras de sinistro não viraram sombra
Sem retroativo nesta SPEC. Backfill é dado antigo de segurado virando corpus — F-093B-04. **Dono:** 🧑.

## P-093B-TELA · A atendente não vê a sombra; a nota `#nota` continua sem tela que a exiba
📊 0 leitores de `notas_da_atendente` em `app/`. A Central mostra o trabalhador; o admin tem o JSON. **Destrava:**
tela de casos da sombra (~2h) — F-093B-02. **Dono:** 🤖.

## P-093B-GOLD · `test_golden_do_eletricista.py` vermelho antes da SPEC, e o pytest carimba
📊 03/09: 1 caso explodiu (gold_007, KeyError 'live'), 14 asserções vermelhas; o pytest coleta só o teste de
existência dos 10 casos (CLAUDE.md §9.4). Linha de base idêntica antes e depois da 093-B. **Dono:** 🤖.

## P-093B-MAQUINA · `test_a_maquina_de_lavar_vai_ate_o_fim.py` crasha a coleta do pytest
📊 `sys.exit` no nível do módulo (:665); como script, 112 ok. Fora da suíte por acidente. **Dono:** 🤖. 💭 10 min.

## P-093B-NOTA-2SEDES · A nota da atendente tem duas sedes e zero leitores
`notas_da_atendente` (WhatsApp) e `messages.payload.nota_interna` (painel). A sombra emite o evento uma vez por
gesto (o painel pelo Next; o celular pelo Python). Consolidar a sede é outra SPEC. **Dono:** 🤖.

## P-093B-REQS · Este ambiente não tem os requirements do backend
📊 faltam `slowapi`, `redis`, `presidio`, `qdrant_client`, `fastembed`…: guardas que importam `app.api.webhook` só rodam
por casca de pacote, e os ganchos da sombra em `o_fim_do_atendimento`/`a_nota_da_atendente`/`human_handoff` são no-op
silencioso NESTA máquina (no contêiner rodam). **Destrava:** CI com `backend/requirements.txt`. **Dono:** 🧑/🤖.

## P-093B-HARNESS · `test_todos_os_guardas_script_rodam.py` se atropela e deixa mutação na árvore
📊 Vítimas diferentes a cada rodada (formulario, handoff, ontologia, regua), todas verdes isoladas; `replay.py`,
`rubrica.py`, `higiene_do_corpus.py`, `corridor_playbooks.py` apareceram mutados em disco em 3 momentos. Diff vazio
contra a `main` nos arquivos exercidos: pré-existente. Irmão de P-088-MUT. **Destrava:** serializar as mutações ou
uma cópia por guarda. **Dono:** 🤖.

## P-093B-JANELA · A janela de 3.000 chars de `test_quem_fala_primeiro_cala_o_outro` ficou com 174 de folga
📊 `i_espelho=709 · i_gate=2826`. A próxima edição no ramo `fromMe` derruba o guarda por CRESCIMENTO, não por defeito.
**Destrava:** ancorar o guarda no bloco, não em contagem de caracteres. **Dono:** 🤖.

## P-093B-CUSTO-INBOUND · +1 round-trip por mensagem de segurado no modo observação
📊 2 → 3 idas ao banco por mensagem não-sinistro (SELECT da ficha). A rodada de conserto memoriza a ausência de ficha
por conversa; medir a latência real do PostgREST no contêiner. **Dono:** 🤖.

## P-093B-TEMPLATES · `message_human` diverge entre Python e Next para o mesmo evento
"Uma atendente assumiu o atendimento." × "a atendente assumiu o caso". Duas vozes na mesma linha do tempo.
**Destrava:** os templates no vocabulário, lidos pelos dois. **Dono:** 🤖. 💭 30 min.

## P-093B-ESPELHO · O espelho que alimenta a sombra ficou parado de 27/08 a 01/09
📊 `attendance_transcripts` por dia: 26/08 473 · 27/08–01/09 **0** · 02/09 3 · 03/09 1. Coincide com a API no chão
(`4c8a718`) e com o atendimento desligado. Sem inbound não há sombra. **Dono:** 🤖 medir depois do piloto.

## P-093B-FICHA-TTL · A memória de ausência da ficha não expira na escala de hoje
📊 `TETO_DA_MEMORIA=5000` FIFO por cliente e 683 conversas no banco: um worker que leu `ficha=None` continua vendo
`None` até reiniciar. Consequência: `confianca` MEDIA em vez de ALTA quando o grafo (ligado) gravar a ficha depois —
a sombra abre igual. **Destrava:** TTL, ou invalidação no ponto que grava a ficha (`nodes.py:860`). **Dono:** 🤖. 💭 20 min.

## P-093B-NOTA-GATE · O gate da nota do painel é de texto-fonte, não de motor
`scripts/claims-shadow-eventos-do-painel.test.mjs` bloco [9] prova que `route.ts` CHAMA o registrador (grep), não que a
chamada grava em runtime. Se `route.ts` deixar de chamar, a nota do painel some do ledger em silêncio (o Python não a emite
mais pelo painel, de propósito). **Destrava:** teste de rota com cliente falso. **Dono:** 🤖. 💭 30 min.


---

# SPEC-094 · O Pulso 360 não pertence à InfoCap — 03/09/2026 (abertas durante a conversão e o censo)

## P-094-CONTA-COMPARTILHADA · 🔴 P1 · Amandus e Resulta descriptografam para a MESMA conta CorpAPI
📊 Censo 03/09 (`docs/canon/providers/infocap/INFOCAP-CORPAPI-CENSUS-v2.md`): mesmo `user_sha`, mesmo `pass_sha`, mesmo
perfil, 1.680 apólices e R$ 1.863.830,79 nas duas. Os ciphertexts diferem (IV do Fernet) — só a descriptografia denuncia.
**Custo de esquecer:** qualquer leitura "da Amandus" mostra a carteira da Resulta. **Destrava:** decisão F-094-07. **Dono:** 🧑.
⚠️ **Conserto parcial em 03/09/2026 (rodada única):** a regra em vigor é *"o primeiro que chega ganha"* — se a Amandus
ler primeiro, a **Resulta** é recusada até o processo reiniciar, e a recusa não dizia por quê. Agora o log estruturado
e o texto da recusa nomeiam **as duas corretoras** e a impressão truncada da conta (`registrar_conta`, `PAR` no bloco
[13] do guarda). 🔴 Isso torna o incidente diagnosticável; **não** resolve a ordem de chegada nem o caso de dois
contêineres. A resolução definitiva continua sendo a decisão **F-094-07**.

## P-094-SINISTROS · `/sinistros` (plural) existe, tem 5.729 registros e nenhum leitor
📊 200 em 26,3 s; campos `numsin/situacao/datoco/datavi/datenc/valind/franquia/nosnum`. O MAPA testava o singular (403).
O `ClaimSignalFact` da 094 ficou como contrato por tempo; o gatilho está atingido. Casa com a 093-B (sombra de sinistro
poderia ganhar `ramo`/`seguradora` daqui). **Dono:** 🤖. 💭 2h.

## P-094-PRODUCAO-500 · `/producao` devolve 500 porque é chamada com o parâmetro ERRADO
📊 A doc oficial exige `dt_ini`/`dt_fim`; o censo usou `datini`/`datfim` e `infocap_connector.py:3115` e `:3126` mandam só `texto`. Uma
linha conserta uma rota do código de produção do ATENDIMENTO — fora da 094 por trava (não regredir atendimento antes do piloto).
**Destrava:** trocar o parâmetro e medir UMA chamada. **Dono:** 🤖. 💭 15 min.

## P-094-RAG-MAPA · O MAPA antigo (18 rotas "negadas", 2.355 atendimentos) está no RAG global dos agentes
📊 Censo §8 item 10. O CENSUS supera o MAPA no repo; o conhecimento ingerido continua errado até reingestão. **Dono:** 🤖.

## P-094-COBERTURA-POR-CORRETORA · a receita de cobertura de produtor da 081 não vale para a AutoFleet
📊 BI∩renov 2025: Resulta 100 · AutoFleet **0**. A 094 remede por corretora (BLOCO D). **Dono:** 🤖.
🔴 **Corrigido o número em 03/09/2026:** `BI∩renov` é um **artefato de janela**, não a cobertura do produto. Ele mede
`2025 × 2025`, e apólice anual que **começa** em 2025 **termina** em 2026 — as duas rotas filtram pontas opostas da
vigência. 📊 O produto pede `2024–2027` e mede **80,6%**. O canário afirmava 5,95% porque a fonte de fixture ignorava
`dt_ini/dt_fim` e devolvia o mesmo lote nas quatro fatias de ano; agora ela respeita a fatia e o guarda afirma a
paridade de 80,6% ± 2 p.p., com o CONTROLE de que ela é muito maior que o artefato.

## P-094-GIT-PII · nome completo de um produtor real no histórico do git (`test_a_fonte_comercial…py:283-294`, desde a 081)
O BLOCO H tira do HEAD; o histórico não se reescreve sem decisão. **Dono:** 🧑.

---

### Abertas pela RODADA ÚNICA DE CONSERTO — 03/09/2026 (painel: red team · lente do dado · L1)

## P-094-DECIMAL-NAS-FORMULAS · o CBIM soma em `Decimal`; as fórmulas de `metricas/` somam em `float`
O docstring de `cbim.py` prometia *"dinheiro é `Decimal`, nunca `float`"* e o motor não cumpria: `registry._float`
projeta o `Money` em `float` e as fórmulas somam ali, porque a matemática que elas chamam é a de `calculos.py`,
que a **SPEC-081 usa em produção** sobre `float` e que a 094 não reescreveu (CLAUDE.md §5).
📊 O resíduo medido sobre o controle-ouro de 2025 (1.680 apólices, R$ 1.863.830,79) é menor que R$ 0,01, e a
serialização arredonda em duas casas antes de o número chegar ao modelo. O **texto** foi consertado em 03/09 —
o docstring agora diz onde o `Decimal` vale e onde não vale (CLAUDE.md §12.1).
**Custo de esquecer:** nenhum hoje; vira dívida se a carteira crescer uma ordem de grandeza ou se alguém
comparar centavo a centavo com o extrato. **Destrava:** `VisaoDeApolice.premio/comissao` em `Decimal`, o que
obriga a passar por `calculos.py` e portanto pela 081. **Dono:** 🤖. 💭 4h, e uma rodada de paridade da 081.

## P-094-NUM-PTBR · `fonte_infocap._num(None)` continua devolvendo `0.0`, e a 081 depende disso
📊 `fonte_infocap.py:592-608`. Ausente, vazio e ilegível viram `0.0` — o defeito da SPEC-094 §1.5. Ele **não foi
consertado de propósito**: oito somas de listas cruas do Raio-X e do Radar (SPEC-081, em produção) dependem daquele
zero, e trocá-lo por um sentinela quebraria as duas tools.
🔴 O caminho NOVO não passa por ali: a fronteira do dinheiro é `cbim.interpretar_dinheiro`, que devolve `None` para
ilegível, e o adapter o traduz em `UNAVAILABLE` **mais um warning com o `correlation_id`**. A mutação **M12** do
guarda prova que ninguém fora do adapter importa `fonte_infocap`.
⚠️ E o GATE ZERO (ii) do guarda **mudou de alvo** em 03/09: ele media `_num`, que não pode ser consertado, e ficaria
vermelho para sempre; agora mede a FRONTEIRA, com quatro pares (português, negativo, zero de verdade, ilegível) e a
mutação que devolve zero. O `_num` legado continua MEDIDO no guarda, sem promessa.
**Custo de esquecer:** enquanto a 081 viver, um `0,00` da fonte é indistinguível de "não ganhou nada" **naquelas duas
tools**. **Destrava:** aposentar o Raio-X e o Radar, ou migrá-los para o registry. **Dono:** 🤖.

## P-094-LEGADO · `relatorios_comerciais.py` fala o dialeto da InfoCap em 24 linhas
📊 Medido em 03/09/2026 pelo grep do M1. São o resolver legado da SPEC-081 dentro da tool de relatório comercial.
Elas estão na **allowlist explícita** do gate M1, com o número escrito: o guarda reprova se um arquivo NOVO de
`agents/tools/` passar a falar InfoCap, ou se um da lista CRESCER.
⚠️ O escopo do M1 foi estreitado no mesmo dia, e por medição: o grep sobre a pasta inteira acusa **87** linhas, e
**63** são das tools de ATENDIMENTO da SPEC-016 (`infocap_tool.py` 39, `portal_tool.py` 8, `portal_params.py` 7,
`insurer_dispatch_tool.py` 5, `vehicle_tool.py` 3, `report_tool.py` 1) — que falam com a InfoCap porque é esse o
trabalho delas. Um gate inalcançável nunca fica verde, e um gate que nunca fica verde ninguém olha (CLAUDE.md §9.3).
**Custo de esquecer:** trocar de provider volta a significar mexer na tool de relatório. **Dono:** 🤖. 💭 2h.

## P-094-CUSTO-API · uma pergunta do Pulso 360 custa 10 chamadas GET
📊 Medido no censo de 03/09/2026: `/documentos_bi` de um ano = **3,9 s**; `/renovacoes` 2025 = **11,4 s**; `/renovacoes`
2026 = **6,0 s**. Uma pergunta de um ano lê 1 fatia de produção + 4 fatias de vencimento (`anos_de_vencimento_para`
varre N−1..N+2, e é isso que dá os 📊 80,6% de cobertura de produtor contra 2,8% de um ano só) — e, quando há
comparação com o período anterior, tudo isso **duas vezes**.
⚠️ Mitigado em parte: o cache de pacote da tool responde o follow-up sem reconsultar, agora com TTL de 15 min.
**Custo de esquecer:** a primeira pergunta do dia pode passar de 40 s, e uma janela grande não completa — por isso o
teto de 2 anos com recusa escrita. **Destrava:** medir se `/renovacoes` aceita janela plurianual sem 502, ou guardar
o lote em Redis por corretora. **Dono:** 🤖. 💭 4h.

## P-094-ARTIFACT-DUPLICADO · toda pergunta não-cacheada publica um Artifact NOVO
📊 Medido pelo juiz em 03/09/2026 e confirmado nas duas provas vivas desta rodada: a mesma pergunta
(*"como estamos?"*, Resulta, período padrão) publicou **duas** peças, com `pack_id` `d2111dfd…` e `00a7dbda…` e
números idênticos ao centavo (972 apólices · R$ 1.472.165,72 de comissão apropriada).
🔴 **O conserto mínimo sugerido pelo painel não existe:** *"reusar o artifact do mesmo `pack_id`"* não tem alvo —
`EvidencePack.pack_id` é um `uuid4()` novo a cada montagem (`evidence_pack.py`, `field(default_factory=…)`), então
um `SELECT` por `pack_id` nunca encontra nada. A chave real de deduplicação é **(company_id, período, janela de
frescor)**, e escolher essa janela é decisão de PRODUTO: reusar a peça de 20 minutos atrás economiza uma leitura de
~85 s e 10 GET, e entrega ao dono números que não são os de agora. O cache de pacote da tool já responde ao
follow-up dentro de 15 min; o que falta é o que acontece **depois** dele.
**Custo de esquecer:** a lista de entregas do corretor enche de peças idênticas, e a que ele abrir pode não ser a
mais recente. **Destrava:** o Founder decide se uma repergunta fora da janela de frescor REUSA a peça (e diz a
idade) ou publica uma nova. **Dono:** 🧑 decide · 🤖 implementa. 💭 3h.

## P-094-SEED-NAO-APLICADO · `report_templates` tem ZERO linhas em produção
📊 Medido em 03/09/2026: a migration de seed dos templates de relatório **não foi aplicada** no banco de produção.
⛔ **Deliberadamente NÃO aplicada nesta rodada** (§2 das travas: nenhuma escrita fora de `artifacts*` e
`tenant_connections.last_used_at`). O Pulso 360 publica hoje porque o `ArtifactService` compõe os blocos no payload;
o que falta é a linha de catálogo. **Custo de esquecer:** quem for listar os templates disponíveis vê um catálogo
vazio, e a próxima SPEC que dependa dele nasce achando que o template não existe. **Destrava:** F-094-04 — o Founder
autoriza o APPLY, com VERIFY e ROLLBACK escritos antes. **Dono:** 🧑.

## P-094-SEED-023 · `financial.billing_collection` é seed de outra SPEC e ficou fora desta rodada
Apontado pelo painel e **deliberadamente não tocado**: mexer no seed de outra SPEC nesta rodada seria escopo por
conta própria (CLAUDE.md §11). Registrado para não virar dívida silenciosa. **Dono:** 🤖.


## P-094.1-SIGLA-SEGURADORA · o mapa `seguradora → coenti` tem 14 de 15, e `sulamerica` é UNKNOWN
📊 Medido em 03/09/2026 (`docs/canon/providers/susep/seguradora-coenti.json`): 15 seguradoras no repositório,
**14 casaram** com uma entidade do censo público e **1** (`sulamerica`) saiu `UNKNOWN`. Duas das que casaram
(`sompo`, `seguros_unimed`) não têm prêmio de auto ativo no trimestre 202604–06.
🔴 A consequência é **desenhada e correta**: uma seguradora sem entidade fica FORA do cruzamento carteira × mercado
e a métrica sai INDISPONÍVEL, nunca zero — *"a sua seguradora sinistra 0% acima do mercado"* é uma frase que o dono
levaria a uma negociação de reajuste, e ela seria falsa (mutação M2, guarda [3]).
**Custo de esquecer:** a corretora que trabalhe com a SulAmérica não recebe a comparação com o mercado, e a peça
diz que não recebe — mas ninguém revisa o mapa. **Destrava:** revisão humana do casamento por nome (o critério
medido é token do nome canônico dentro de `Noenti` + desempate por prêmio de auto no trimestre). **Dono:** 🧑 revisa
· 🤖 aplica. 💭 1h.
✅ **Parcialmente fechada em 04/09/2026:** o elo que faltava não era o `sulamerica` — era que a carteira traz a
**SIGLA** (`PORT`, `ALLI`, `TMAR`) e o mapa era indexado pelo nome. O arquivo ganhou a seção `siglas` e a cobertura
de prêmio subiu de 12,35% para 83,86%. O que resta está em **P-094.1-SIGLAS-SEM-ENTIDADE** e
**P-094.1-SIGLAS-POR-CORRETORA**. `sulamerica` continua `UNKNOWN`, e continua sendo a resposta certa.

## P-094.1-SIGLAS-SEM-ENTIDADE · 47 das 61 siglas do sistema de gestão ainda saem `UNKNOWN`
📊 Medido em 04/09/2026, na rodada única de conserto (`docs/canon/providers/susep/seguradora-coenti.json`,
seção `siglas`): das **61** siglas do censo `/seguradoras` da corretora piloto, **14** casaram com uma entidade —
**1** por igualdade de nome COMPLETO com o censo público (`HDI`) e **13** por decisão explícita revisada. As
outras **47** ficam `UNKNOWN`, com o nome listado no arquivo.
🔴 O efeito medido é bom e parcial: a cobertura de PRÊMIO da carteira viva subiu de **12,35%** para **83,86%**
(R$ 21.814.941,56 em 3.861 linhas de 2025). O que falta são as seguradoras de cauda — `MAP` (capitalização, que é
outra entidade de propósito), `AXA`, `MAG`, `JUNT`, `AIG`, `ESSO`, `ITAU`, `BERK`, `CHUB`, `FATO`, `JNS`, `MITS`.
⛔ E o casamento por PALAVRAS foi REMOVIDO nesta rodada: `"PORTO SEGURO SAUDE"` herdava a entidade **05886**, que é
a Porto de AUTO. Publicar a sinistralidade de outra empresa num argumento de reajuste é o defeito, não a cobertura
baixa. **Custo de esquecer:** a comparação com o mercado fica indisponível para ~16% do prêmio da carteira piloto,
e a peça diz que fica — mas ninguém revisa. **Destrava:** uma pessoa decide, sigla a sigla, contra o `Noenti` do
censo público, e a decisão entra no arquivo com o critério escrito ao lado. **Dono:** 🧑 decide · 🤖 aplica. 💭 1h.

## P-094.1-SIGLAS-POR-CORRETORA · o mapa de siglas é o da corretora PILOTO, e sigla é por instalação
🔴 A seção `siglas` nasceu do censo `/seguradoras` de **uma** corretora. A abreviatura é escolhida no cadastro de
cada instalação: `PORT` pode ser outra empresa na próxima casa. Hoje o mapa é único e versionado no repositório, e
uma sigla que colidisse publicaria o número de outra seguradora — o mesmo defeito que o casamento parcial causava.
⚠️ Enquanto só a piloto usa o cruzamento com o mercado, o risco é teórico. **Custo de esquecer:** a segunda
corretora com o Pulso de mercado ligado recebe a sinistralidade errada, com confiança alta. **Destrava:** ler
`/seguradoras` por corretora e casar a sigla ao NOME antes de consultar o mapa — a rota já está medida no censo, o
que falta é o leitor. **Dono:** 🤖. 💭 3h.

## P-094.1-PROMOCAO-SEM-DECISAO-REAL · o gate de aprovação já RECUSA contra o banco real; falta ver ele APROVAR
🔴 **Atualizada em 04/09/2026 (rodada 3), e a atualização é a pendência:** o título antigo dizia *"nunca rodou
contra o banco real"*, e isso deixou de ser verdade — mas só metade.

📊 Medido ao vivo na Resulta: a proposta `proposta.teste_builder_0941` nasceu pelo chat
(`work_run ba26117a…` + `approval_request e47a4a5c…` `pending`, `subject_id` = o uuid do run + 2 `work_events`), e
`promover()` sobre ela devolveu a RECUSA legivél *"a decisão humana é pending, e não uma aprovação"* — com
`work_events` antes=2 e depois=2 e o run intacto em `waiting_approval`. **Nada foi escrito.**

⚠️ O que continua sem medição é o caminho FELIZ: nenhuma `approval_request` real chegou a `approved`, então o
`UPDATE` final (`status='completed'`, corrigido nesta rodada porque `succeeded` **não existe** no enum
`work_run_status`) e a gravação de `metric.promovida` nunca tocaram o banco de verdade.
**Custo de esquecer:** a primeira promoção legítima estoura no `UPDATE`, DEPOIS de o evento de promoção já estar
gravado — a linha do tempo diz "promovida" e o run fica esperando para sempre. **Destrava:** decidir a proposta
`ba26117a…` pela API admin (`POST /work-runs/approvals/{id}/decide`) e rodar o CLI uma vez. **Dono:** 🤖 (depende
de F-094.1-02). 💭 20 min.

## P-094.1-RAMO-COGRUPO · 8 dos 50 ramos da corretora piloto não têm grupo de ramo na SUSEP
📊 Medido em 04/09/2026, construindo `docs/canon/providers/susep/ramo-cogrupo.json` a partir do `GET /ramos` da
Resulta (50 ramos) contra `Ses_ramos.csv` e `ses_gruposramos.csv` (22 grupos): **90,43%** das 3.272 linhas de 2025
casaram. Ficaram `UNKNOWN`, com o critério escrito ao lado de cada um: **ASSI · CAPI · CONS · DENT · FINA · MOB ·
PREV · VIAG** (313 linhas). Três famílias de motivo, e nenhuma delas é preguiça:

```
nao e seguro do SES     CAPI (capitalizacao) · CONS (consorcio) · PREV (previdencia aberta) · DENT (ANS)
empate entre DOIS grupos  VIAG e ASSI (0969 no grupo 09 e 1369 no 13) — a carteira nao diz qual
rotulo de negocio         MOB (imobiliaria) e FINA (financiamento) nao nomeiam objeto de risco
```
⚠️ E o mapa é o da corretora PILOTO: abreviatura é por INSTALAÇÃO, como já vale para
**P-094.1-SIGLAS-POR-CORRETORA**. Outra corretora com outra abreviatura sai `UNKNOWN` inteira — o que é a resposta
certa, e não um número errado. **Custo de esquecer:** ~9,6% do prêmio da carteira nunca entra na comparação com o
mercado, e a segunda corretora entra com 0%. **Destrava:** decidir os dois empates (VIAG/ASSI) com gente, e medir
`/ramos` de cada corretora nova. **Dono:** 🤖 + 🧑 (os empates). 💭 1h.

## P-094.1-LATENCIA · "como estamos?" leva 162 s, e 89% disso são TRÊS leituras da fonte
📊 Medido ao vivo em 04/09/2026 na Resulta, pelo relógio por fonte que esta rodada acrescentou
(`executive_intelligence._anotar_o_relogio`, teto 60 s):

```
como estamos? (7 visoes)   156 s   carteira 54,7 · customers 51,4 · cancellations 37,7 · claims 4,3 · quotes 4,3 · issuance 1,8 · mercado 1,4 · calculo 0,2
mercado + sinistros         65 s   carteira 52,7 · mercado 7,1 · claims 4,7 · calculo 0,3
```
🔴 O cálculo custa **0,2 s**: o custo inteiro é de I/O na fonte, e três rotas respondem por 144 dos 156 s. O
aviso já sai escrito no envelope acima do teto — o que ainda não existe é leitura em PARALELO (as populações são
independentes e são lidas em série) nem cache por janela. **Custo de esquecer:** dois minutos e meio é tempo de
sobra para o dono trocar de tela, e aí o relatório chega para ninguém. **Destrava:** `asyncio.gather` sobre
`_buscar_as_populacoes` (elas já são `async` e independentes) e medir de novo. **Dono:** 🤖. 💭 2h.

## P-094.1-SES-SO-TEM-2026 · o agregado do mercado existe só para 2026, e perguntar 2025 devolve INDISPONÍVEL
📊 Medido ao vivo em 04/09/2026: `"como estamos?"` sobre **2025** tentou `susep/ses/2025.csv` e recebeu
`NoSuchKey` do MinIO real — o feixe do mercado não veio, e `market.loss_ratio@1` e
`claims.loss_ratio_vs_market@1` saíram UNAVAILABLE com o motivo certo (*"a Rotina semanal ainda não rodou"* — uma
afirmação sobre NÓS). Sobre **2026** as duas responderam com número. ⚠️ Isto **não é defeito**: é a Rotina que só
ingeriu um ano. **Custo de esquecer:** toda pergunta histórica perde a comparação com o mercado, e ninguém sabe
por quê sem ler o log. **Destrava:** rodar a ingestão para os anos anteriores (ver
**P-094.1-SES-SEM-ROTINA-EM-PRODUCAO**). **Dono:** 🤖. 💭 1h.

## P-094.1-FUNIL-SEM-FINGERPRINT · o funil sai INDISPONÍVEL por censo, e não por acervo
📊 Medido ao vivo em 04/09/2026: `quotes.funnel@1` e `quotes.lost_reasons@1` saíram UNAVAILABLE com
*"o censo não registrou o fingerprint de `/negocios_finalizados`"* — o bloqueio é do MANIFESTO, e não do dado.
🔴 O que esta rodada consertou é outra coisa, e vale registrar a diferença: até hoje esse mesmo caminho
**derrubava o Pulso inteiro** (`RELATORIO_FALHOU`, zero artifact). Agora as duas saem INDISPONÍVEL com o motivo e as
outras 24 métricas continuam de pé. **Custo de esquecer:** a visao `funil` nunca responde, e o dono não sabe se é
porque não há cotação ou porque ninguém mediu a rota. **Destrava:** rodar o censo de `/negocios_finalizados` e
gravar o fingerprint em `infocap-schema-fingerprints.json`. **Dono:** 🤖. 💭 40 min.

## P-094.1-SINISTRO-X-CARTEIRA · a junção sinistro × carteira dá ZERO, e o produto parou de depender dela
📊 Medido em 04/09/2026: os **40** documentos citados pelos sinistros do período não aparecem entre as **3.861**
linhas de carteira de 2025 — as apólices sinistradas são de outros exercícios, o que é o normal de um sinistro. A
regra antiga (*"conta só o que junta"*) fazia TODA métrica de sinistro sair INDISPONÍVEL na pergunta real. O
conserto tirou a junção do denominador e a transformou numa linha informativa do detalhe.
⚠️ O que continua em aberto é a pergunta que a junção respondia: *"deste sinistro, qual é a apólice, o produtor e a
comissão?"*. Ela exige ler a carteira numa janela mais larga que a do período. **Custo de esquecer:** o dono vê
quantos sinistros tem e não consegue amarrá-los a quem vendeu. **Destrava:** ler a carteira dos N anos anteriores
para o join, ou ler a apólice do sinistro individualmente. **Dono:** 🤖. 💭 3h.

## P-094.1-MOTIVO-DE-PERDA · `quotes.lost_reasons@1` nasce INDISPONÍVEL por CAPACIDADE
📊 Censo v2.1 §A4: `motivo_perda` **não vem no GET** das três rotas do funil — não está entre as 30 chaves medidas.
A métrica existe, está registrada, aparece na visão `funil` e na seção 10 do Pulso 360, e escreve no envelope que a
fonte expõe a CONVERSÃO e não a CAUSA. ⚠️ Ela existe justamente para dizer isso: uma métrica ausente deixa o leitor
supor que ninguém pensou nela.
**Custo de esquecer:** o dono vê onde perde e nunca por quê — a pergunta mais cara do funil fica sem dono.
**Destrava:** confirmar com o fornecedor se há rota (ou parâmetro) que devolva o motivo; se houver, é só a fórmula.
**Dono:** 🧑 pergunta ao fornecedor · 🤖 implementa. 💭 2h depois da resposta.

## P-094.1-EMISSAO-PENDENTE · `issuance.pending@1` idem: a fonte não expõe estado de emissão
📊 Mesma origem: o censo não verificou capacidade de estado de emissão na fonte piloto — o que é diferente de
"não existe". A métrica está registrada, entra na visão `pendencias` e na seção 11 da peça, e sai UNAVAILABLE com o
motivo escrito ao lado do número que não veio. **Custo de esquecer:** "o que já vendi e ainda não virou apólice" é
dinheiro parado que ninguém consegue contar. **Destrava:** medir a capacidade na fonte. **Dono:** 🤖. 💭 2h.

## P-094.1-SES-SEM-ROTINA-EM-PRODUCAO · a ingestão do censo existe e nunca rodou no ambiente real
📊 Medido em 04/09/2026 pela prova B.5 (`backend/scripts/prova_b5_ses_ponta_a_ponta.py`), com **MinIO FAKE em
memória** — `MINIO_ENDPOINT` não está no ambiente desta máquina: 1.801.731 linhas lidas, 33.504 células agregadas
(só 2026), 26,6 s de latência, 17,3 MB de pico (`tracemalloc`), 1.069.071 bytes gravados. O golden da Porto
(05886 · grupo 05 · 202604–06 = **0,5712**) sai do registry e bate com a conta feita à mão sobre o CSV agregado.
🔴 **Nada disso rodou contra o MinIO de produção**, e a Rotina semanal nunca foi disparada lá. Enquanto isso,
`market.loss_ratio@1` responde INDISPONÍVEL para toda corretora — o que é uma afirmação sobre NÓS, e não sobre a
sinistralidade de seguradora nenhuma (é o que o envelope diz, com essas letras).
**Custo de esquecer:** a seção "mercado" do Pulso 360 fica permanentemente indisponível, e a única coisa que o
produto faz e ninguém mais faz não chega ao dono. **Destrava:** rodar a Rotina uma vez no ambiente real e conferir
o objeto `susep/ses/<ano>.csv` no bucket. **Dono:** 🤖 (precisa de `MINIO_ENDPOINT` no ambiente). 💭 30 min.

---

# SPEC-095 · Relatórios que o corretor entende — o que ficou (04/09/2026)

## P-095-NARRATIVA-DO-FABRIC · `commercial_opportunity` não tem Narrativa própria no Fabric
📊 Medido em 04/09/2026: o sinal da 094 sai com `signal_type = "commercial_opportunity"` para os três detectores
(`evidence_pack.py:596`); `finding_engine.py:200` escolhe a narrativa por tipo e cai em `NARRATIVA_PADRAO` — o finding
nasce "Ponto de atenção / observacao" (`intelligence_findings` da Resulta, 4 dias: **3/3**). A 095 contorna no briefing
(a 1ª frase do sumário humano vira manchete quando o tipo é `observacao`); a Central e o admin continuam vendo "Ponto de
atenção". **Custo de esquecer:** o achado mais valioso do produto (concentração, renovação vencendo, produtor em queda)
aparece com título genérico fora do briefing. **Destrava:** 3 `signal_type` + 3 `Narrativa` no Fabric (SPEC-059, taxonomia
de `schemas.py`). **Dono:** 🤖. 💭 1h30.

## P-095-DATA-AS-OF-LEGADO · 136 versões antigas carregam `data_as_of` = carimbo de escrita
📊 Medido em 04/09/2026: `service.py:159` gravava `_agora()`; 136/136 versões, 30 delas no FUTURO do próprio `created_at`
(desvio por processo: worker −0,1 s, API +50…+70 s). A 095 corrige o escritor (NULL quando ninguém sabe a data) e a tela
chama as antigas de "gerado em", nunca "dados de". As versões publicadas são imutáveis: o valor velho fica. **Custo de
esquecer:** nenhum — desde que a tela continue distinguindo. **Destrava:** nada; registro para quem ler o banco cru.
**Dono:** 🤖.

## P-095-TRABALHO-PRONTO · o briefing só conhece `work_runs` como "trabalho pronto"
📊 Medido em 04/09/2026 (aquecimento): dos 41 itens de trabalho dos 5 últimos briefings da Resulta, **40** vinham de Work
Runs `system` (`intelligence.detect_signals` etc.). Com o relógio da plataforma fora (D.5 da 095), sobram 0 em 5/5 dias, e
a frase "M trabalho(s) pronto(s)" some. Execuções de rotina/auxiliar ("Cobrança Feita rodou") não entram como pronto.
**Custo de esquecer:** o briefing não conta o trabalho que os Auxiliares fizeram. **Destrava:** `_trabalhos`
(`briefing_service.py:566`) ler `routine_runs`/`auxiliary_runs` além de `work_runs` chat/routine. **Dono:** 🤖 (SPEC-097).
💭 1h.

## P-095-TICK-OLHA-953-VEZES · `intelligence.detect_signals` rodou 953× para produzir 32 sinais
📊 Medido em 04/09/2026: `work_runs` da Resulta = 1.228, `source_type='system'` = 1.214 (98,86%); `detect_signals` 953,
`measure_outcomes` 160, `garimpo` 41. As três corretoras têm ~1.210 cada — o número é do relógio. **Custo de esquecer:**
custo de banco e de fila por nada; qualquer contador ingênuo de "trabalho" mente por 87×. **Destrava:** cadência do tick
por corretora com dado novo, não por relógio (SPEC-097). **Dono:** 🤖. 💭 2h.

## P-095-SEARCH · busca no servidor e paginação por cursor, por gatilho
📊 Medido em 04/09/2026: 400 linhas no máximo por lista, 130 peças por corretora, 1,2 ms por consulta. A busca continua no
navegador sobre título/detalhe/origem. **Custo de esquecer:** uma peça antiga fora das 120 mais recentes por fonte não é
encontrável. **Destrava:** > 1.000 linhas por corretora ou uma busca que não achou (medida). **Dono:** 🤖. 💭 3h.

## P-095-PDF · não há renderizador de PDF no contêiner
📊 `grep -in "playwright\|chromium\|weasyprint" backend/requirements*.txt backend/Dockerfile*` → 0. "Abrir em nova aba" +
imprimir já gera PDF pelo CSS de impressão da peça. **Custo de esquecer:** o botão "Baixar" entrega `.html`. **Destrava:**
o Founder ou uma corretora pedir arquivo; Playwright entra no worker, não na API. **Dono:** 🧑 decide · 🤖 implementa. 💭 4h.

## P-095-DATA-SOURCES-TRES-FORMAS · `data_sources` tem três formas no backend
📊 Medido em 04/09/2026 pelo builder da tela: `{rotulo, detalhe, data}` (`workflows.py:257-264`, 96/136 versões — os briefings),
`{label, detail, …}` (`report_tool.py:271`) e `{kind, …}` (`radar.py:399`). A tela "De onde veio" lê as três; a SPEC-095 cita só a
inglesa. **Custo de esquecer:** uma quarta forma nasce na próxima peça e a tela mostra "fonte sem nome". **Destrava:** convergir
numa forma em `ArtifactService.criar` (normalizar na entrada) e um guarda que reprova chave fora do vocabulário. **Dono:** 🤖. 💭 1h.

## P-095-BRIEFING-POR-CANAL · o briefing sai só no painel; WhatsApp e e-mail esperam o Founder (F-095-02)
📊 `delivery_detail` dos briefings das 3 corretoras (04/09/2026): `canais: [{canal:"dashboard"}]`, `push: true`, nenhum envio externo.
**O que existe pronto:** o briefing composto (`briefing_service.py`, manchete + itens com `why_now/next_step` desde a 095) · o Artifact
com versões · o link autenticado do detalhe · o governador de envio do WhatsApp (P-14) · a chave SendGrid VAZIA (P-13).
**O que um chat futuro faz, nesta ordem (piso CRÍTICO da §3.2 — qualquer coisa que ENVIA):** (1) o Founder responde: para QUEM
(dono da corretora? cada membro?), em QUAL canal (WhatsApp/e-mail), a QUE HORA (📊 hoje 08:00 local) e o que vai no corpo (manchete +
3 itens + link, nunca o relatório inteiro); (2) SPEC própria, PADRÃO/CRÍTICO, com Approval da 055 na 1ª execução por corretora;
(3) template de WhatsApp categoria Utility ANTES de 01/10/2026 (F-094-10: Marketing custa 9,2×); (4) o livro de entregas que saiu
da 095 (§5 linha 2) volta aqui — `delivery_status` real por canal; (5) canário: Amandus → Resulta, nunca Resulta primeiro.
**Custo de esquecer:** a corretora só vê o briefing se abrir o painel. **Dono:** 🧑 decide · 🤖 executa. 💭 4–6h.

## P-095-LEITURA-DO-MODELO · a leitura em prosa por cima do Pulso 360 (F-095-01, AUTORIZADA em 04/09/2026)
**O que fazer (unidade LEVE, 💭 3h):** um bloco `prose` no Pulso (`executive_intelligence.py::_compor`, depois de "O que importa agora")
escrito por modelo a partir do pack selado (`pack_id`), marcado "leitura do AutoBrokers" (💭) — nunca 📊; guarda: **todo número que
aparecer na leitura existe no pack** (regex de números × `MetricResult` do pack; um número fora → a leitura é descartada e o bloco não
entra); a leitura some quando o pack não tem achado; nada de nome de pessoa (o pack já é opaco). **Custo de esquecer:** o Founder
autorizou e nada acontece. **Dono:** 🤖.

## P-094-CONTA-COMPARTILHADA · ✅ FECHADA em 04/09/2026 pela F-094-07 (opção B)
A conexão InfoCap da Amandus foi arquivada (escritor espelhado + auditoria; VERIFY em `FOUNDER-DECISIONS.md` F-096-00). Só a Resulta
resolve para a conta CorpAPI. Se um dia a Amandus precisar de InfoCap, é cadastro NOVO com conta própria (ação física do Founder).

## P-096-WIDGET-SEM-DOMINIO · 🧑 0 de 3 agentes ativos têm `allowedDomains` — o widget é público por omissão
📊 05/09/2026 (red team + lente do DADO): `select count(*) filter (where widget_config->'allowedDomains' <> '[]') from agents where is_active` → 0 de 3;
`widget_security.py:18-19`: `if not allowed_domains: return True`. A 096 conteve o estrago (em modo widget a corretora é DERIVADA do agente,
o corpo não escolhe mais), mas a porta continua aberta: qualquer site que conheça o `agentId` conversa como aquele widget e gasta o crédito da
corretora do agente. **O que fazer:** configurar `allowedDomains` por agente com widget (ação sua, na tela do agente) e, depois, trocar o
`return True` por recusa (fail-closed) numa SPEC LEVE com canário. **Custo de esquecer:** crédito gasto por terceiros. **Dono:** 🧑 configura · 🤖 fecha.

## P-096-CHAVE-INTERNA-NO-NEXT · 🧑 sem `BACKEND_INTERNAL_API_KEY`/`ADMIN_API_KEY` no contêiner do Next, o painel cai no legado EM SILÊNCIO
📊 o BFF manda `X-Internal-Key` e o backend decide o modo por ela; sem a chave no smith-web, todo turno vira modo widget (`{"token"}`), a tela
descarta 100% dos eventos com `console.warn` e o corretor vê "Reconectando…" + recarga. 📊 o `.env` local do backend não tem a chave; o `.env.local`
do Next tem `ADMIN_API_KEY`. **O que fazer:** confirmar no EasyPanel que smith-web E smith-api têm a MESMA chave; o canário E.2 prova ao vivo.
**Custo de esquecer:** deploy verde, chat mudo. **Dono:** 🧑.

## P-096-STOP-MULTIPROCESSO · o "Parar" só acha o turno no MESMO processo
`TURNOS_ATIVOS` é memória de processo (📊 `backend/Dockerfile:27` sem `--workers`: 1 processo hoje). Com réplicas, o POST /chat/stop cai noutro
worker → 404 e o turno segue até o fim (o parcial fica na tela; a resposta inteira é gravada). `payload.turn.stopped_by` deixa o sintoma visível.
**Destrava:** registro em Redis (transporte, nunca verdade) quando houver 2+ réplicas. **Dono:** 🤖. 💭 2h.

## P-096-REPLAY-AO-VIVO · reconectar não retoma o parcial AO VIVO — recarrega a conversa gravada
Saiu da proposta com gatilho (SPEC §5): gravar até o fim (A.4) resolve o refresh; o replay por Redis (`after_sequence`) é para ver o texto
escorrendo de novo depois de reconectar. **Volta quando** uma corretora reclamar de resposta longa (> 30 s) — medido. **Dono:** 🤖. 💭 4h.

## P-096-MOTOR-DE-EVENTOS · o estágio sai das `tool_calls`; `on_tool_start` e `custom` não existem neste grafo
📊 `nodes.py:1089` chama `tool._arun` direto (pula o CallbackManager); `astream_events(version="v1")` não entrega `custom`; `langgraph==1.0.3`
pinado (o event streaming v3 exige ≥ 1.1). **Volta quando** uma tool precisar emitir progresso PRÓPRIO ("3 fontes encontradas"). **Dono:** 🤖.

## P-096-ARTIFACT-SEM-CONVERSA · a peça nasce sem `conversation_id`
O `artifact.ready` liga o turno à peça por ContextVar (`pecas_do_turno`), mas `artifacts` continua sem o elo durável; `subject_ref` é identidade.
A 097 (casos) / 098 (de quem é) decidem a coluna. **Dono:** 🤖.

## P-096-COMPANY-DATA-IGNORA-ATIVA · `/api/user/company-data` ignora `activeCompanyId`
📊 `route.ts:40` usa `users_v2.company_id`; o chat (096) passou a usar `resolveSessionCompany` (valida a filiação; honra o seletor da 047) — a
tela do topo e o cérebro do chat podem discordar de empresa. **Destrava:** a rota usar o mesmo helper. **Dono:** 🤖. 💭 30 min.

## P-096-LEGADO-ERRO-COMO-TEXTO · o wrapper legado ainda injeta "[Erro interno…]" como conteúdo no widget
📊 `graph.py` (wrapper `stream_agent`): em `kind=="error"` devolve o texto — é o contrato legado do widget (§5). No painel, o erro é tipado.
**Destrava:** o widget consumir o protocolo v1 (subset). **Dono:** 🤖.

## P-096-SESSION-FAIL-OPEN · `DELETE /session` (`chat.py`) continua fail-open se a checagem de dono falhar
Não tocado pela 096 (só o `str(e)` ao cliente virou erro seguro). **Destrava:** dono derivado + mutação, junto com a 098. **Dono:** 🤖.

## P-096-MEMORIA-LE-ERRO · a memória guardou "[Erro interno…]" como resposta em conversas antigas
📊 até a 096, o texto de erro entrava no stream de conteúdo e virava memória/resumo. As linhas antigas continuam lá. **Decisão sua:** limpar
(`update messages set …` nas mensagens `assistant` cujo content é só o texto de erro) ou deixar. **Dono:** 🧑 decide · 🤖 executa.

## P-096-WORK-RUNS-CHAVE-SO-ENV · `work_runs.py:26` valida a chave só por `os.getenv`
pydantic-settings não exporta o `.env` para o `os.environ`; onde a chave só existe no arquivo, a checagem falha. O chat (096) olha `settings` E
`os.getenv`. **Destrava:** o mesmo helper (`_chaves_internas`) nas rotas de work/artifacts/authority. **Dono:** 🤖. 💭 30 min.

## P-096-VOZ-N8N · a voz do painel ainda passa pelo n8n
A 096 só fez a rota derivar a corretora da sessão (S.4). O runtime de voz é da SPEC-112. **Dono:** 🤖 (112).

## P-096-GUARDA-MEMORIAS-VERMELHO · `test_memorias_nao_vaza_inteligencia.py` está vermelho e a 096 não o tocou
📊 05/09/2026 (lente de verdade da 096): 4 problemas; o guarda mede só `app/dashboard/personalizacao/memorias/page.tsx`, arquivo INTOCADO por
`e1494ab..HEAD` — vermelho PRÉ-EXISTENTE, não regressão. A árvore não tem baseline verde para ele. **Destrava:** rodar o guarda em `e1494ab`,
achar o commit que o quebrou (`git bisect`) e decidir: migrar o guarda (verdade vencida) ou consertar a tela. **Dono:** 🤖. 💭 45 min.

## P-097-ESPERA-COM-ESCRITOR · `work_waits` tem esquema completo e ZERO linhas — a espera saiu da 097 até ter escritor
📊 05/09/2026: `select count(*) from work_waits` → 0 na vida; os 3 chamadores de `abrir_espera` (`services/dispatch_router.py:1194,1252`, `tasks/handoff_watchdog.py:480`)
só chamam com o espelho do WhatsApp ligado; 📊 4 acionamentos em 30 dias; a FK `(conversation_id, company_id)` barra o episódio órfão. A 097 LÊ `work_waits` se houver
linha e não deduz espera de texto. **Destrava:** o corredor chamar `abrir_espera(attendance_session_id=…)` quando entra em espera (seguradora/cliente), com `due_at`
quando há prazo, e a FK aceitar o episódio. Entram com ele: as views "Aguardando seguradora/cliente", `espera_vencida` com prazo e o gate G7 da proposta. **Dono:** 🤖. 💭 3h.

## P-097-TIMELINE-CURSOR · a timeline da Ficha corta em 500 mensagens SEM aviso
📊 `ficha/[id]/route.ts`: `messages … .limit(500)` contra conversas de até 1.326 mensagens; não há `has_more`. A 097 entrega `has_more` verdadeiro; a paginação por cursor
saiu por orçamento (E18). **Dono:** 🤖. 💭 1h30.

## P-097-SESSOES-ORFAS · 42,2% das `attendance_sessions` não casam 1:1 com uma conversa por telefone
📊 05/09/2026 (aquecimento): 57,8% casam; o resto é ambíguo (mesmo telefone, várias conversas/empresas) ou sem conversa. Ficam como casos "sem conversa vinculada".
**Destrava:** o espelho do WhatsApp ligado (o Atlas passa a conhecer a conversa) e uma normalização única de telefone no produto. **Dono:** 🧑 liga o espelho · 🤖.

## P-097-DOCUMENTOS-DO-ATENDIMENTO · não existe autoridade de documento de atendimento
📊 `documents` é a base de conhecimento (RAG); a evidência do atendimento é coluna de mensagem (`image_url` NOT NULL = 13, `audio_url` = 0 em 25.061); `artifacts` sem conversa
(P-096-ARTIFACT-SEM-CONVERSA); 📊 9.002 mídias do history sync inalcançáveis (sem `waE2E.Message`). D-097-07 da proposta vira pendência. **Dono:** 🤖 quando houver acervo.

## P-097-APPROVAL-SEM-CONVERSA · `approval_requests` não volta ao atendimento
📊 sem `conversation_id`; ponte run→conversa com 4 linhas em 3.708. A razão `aprovacao_pendente` saiu de R6. **Destrava:** a 055/098 gravarem a conversa/episódio na aprovação. **Dono:** 🤖.

## P-097-POLLING-10S · a Fila consulta a cada 10 s (≈ 30 mil consultas/operador/dia)
📊 5 consultas em série + 1 HTTP, p50 ≈ 1,0 s, `setInterval` 10 s. Realtime/SSE só depois de medir com a projeção nova. **Dono:** 🤖. 💭 2h.

## P-097-DRAG · arrastar cards não existe e não entra até haver comando de negócio por coluna
Proposta §16: drag = comando, nunca estado. Não há drag hoje; construir para governar é o risco. **Volta** quando uma corretora pedir. **Dono:** 🧑 decide.

## P-097-REABRIR-ATENDIMENTO · encerrado é encerrado: claim/release/send devolvem 409 e não existe o gesto de REABRIR
Red team P1-1 (05/09): assumir, devolver ou escrever numa conversa com `resolvido_em` sobrescrevia/apagava o autor e reabria o status. Os três caminhos agora devolvem 409 "o atendimento já terminou" — e nenhum caminho reabre. **Destrava:** decidir quem pode reabrir e o que acontece com o desfecho anterior (novo episódio? mesmo?). **Dono:** 🧑 decide · 🤖 implementa. **Custo de esquecer:** a atendente que precisa voltar a um caso encerrado fica sem porta.

## P-097-PROTOCOLO-SEM-CASA · o protocolo do acionamento só vive no Redis do corredor vivo
📊 05/09: `column_name ilike '%protocol%'` no schema `public` → ZERO colunas; `summary->'distilled'` de 9.196 sessões não tem a chave. A Fila mostra o protocolo só enquanto o acionamento vivo o entrega; Casos não busca por protocolo. **Destrava:** o corredor gravar o protocolo no episódio (coluna na `attendance_sessions` ou no `summary`) — candidato à 097.1/098. **Dono:** 🤖. **Custo de esquecer:** "cadê o protocolo de 60 dias atrás?" continua sem resposta.

## P-097-RECONFERE-TENANT · a projeção confia nos filtros e não reconfere `company_id` nas linhas lidas
Red team P3-5: os 11 `.eq('company_id')` existem, mas uma fonte suja (ou uma mutação que tira um `.eq`) entra inteira no payload de outra corretora — não há rede embaixo. **Destrava:** `projetarCasos` descartar (e contar) linha cuja `company_id` ≠ a da sessão. **Dono:** 🤖. **Custo:** §7 fica com uma camada só.

## P-097-TELEFONE-BR-DUPLICADO · a regra do 9º dígito ainda tem duas cópias
A 097 criou `backend/app/telefone_br.py` (`so_digitos`, `variantes_br`) e migrou o Atlas e o backfill para ele; `whatsapp/channel_security.py::_variants` e `platform_outbound.py::_phone_variants` continuam copiando a regra. **Destrava:** os dois importarem de `telefone_br`. **Dono:** 🤖. **Custo:** um par (com 9/sem 9) tratado diferente por canal.

## P-097-DOIS-RELOGIOS · `ordem_em` lê `last_message_at`/`created_at` sem guarda de coerência
Lente de verdade (P3 L2): a mutação "semana lê `last_message_at` e a Fila lê `last_event_at`" fica verde — não há asserção que prove que os dois relógios da lista e da semana são o MESMO. **Destrava:** asserção de coerência no guarda `test:casa`. **Dono:** 🤖.
