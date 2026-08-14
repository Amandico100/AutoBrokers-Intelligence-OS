# SPEC-070 — Cobrança multi-seguradora: como se abre um portal novo

**Autor**: líder técnico · 12/08/2026 · **Status**: em execução (Allianz ✅ · HDI ✅ · Tokio próxima)

> **Esta SPEC não substitui a [SPEC-033](SPEC-033-portal-api-automation-playbook.md).**
> A 033 responde **COMO** falar com um portal — e continua valendo inteira. Esta
> responde **EM QUE ORDEM**, **com que prova** e **quantas vezes se pode bater na
> porta**. Ela nasceu porque duas seguradoras nos bloquearam quando eu explorei
> sem plano.

---

## 0. Por que esta SPEC existe

📊 Em 10–12/08/2026, explorando HDI e Tokio sem checklist escrito:

```
HDI ..... ~15 visitas em 30 min  ->  Akamai bloqueou o IP por horas
Tokio ...  ~4 visitas em 30 min  ->  o SSO passou a travar em "Carregando..."
```

Nenhum dos dois era problema de método. **Era problema de ritmo, e de não haver
plano.** O Fable levou dias na Allianz, com o Founder mandando print e ele
testando — ~40 tentativas espalhadas ao longo de dias, não em meia hora.

> **A regra que fecha essa porta: o portal da corretora não é ambiente de teste.**

---

## 1. O que se herda da SPEC-033 (e não se discute)

| Regra do Fable | Continua valendo? | Ajuste desta SPEC |
|---|---|---|
| **LER e BAIXAR → chamada direta; nunca clicar** | ✅ inteira | a resposta pode ser **HTML**, não só JSON — ver §2 |
| **AÇÕES transacionais → parar antes de finalizar** | ✅ inteira | vira lista **testada** de botões proibidos por portal |
| Navegação visual como **fallback** | ✅ | só depois da cadeia funcionar |
| Captura por F12 → Headers + Payload + **Response** | ✅ | 📊 o **Response** é o que mais falta, e é o que resolve |
| Encadear pela resposta (o id do passo 1 é o input do 2) | ✅ | idem |
| Sessão restaurada envelhece → login limpo | ✅ | idem |
| Nunca logar token, senha ou PII | ✅ | fixture no repo é **anonimizada** |

### 1.1 O que esta SPEC ACRESCENTA à 033

**(a) A resposta pode ser HTML — e isso não é exceção.**
📊 A Allianz é um BFF moderno e devolve JSON. A HDI é um sistema legado de 2008
e devolve HTML iso-8859-1. **O princípio é o mesmo:** chamar por dentro da
página, com a sessão do corretor, sem clicar. Muda só como se lê a resposta.

> **Regra:** a leitura acontece em **Python, fora do navegador**. É o que permite
> teste com fixture. 📊 As 143 linhas do coração da Allianz não têm um teste
> sequer, justamente porque a leitura mora dentro de um `evaluate`.

**(b) A busca pode ser assíncrona.**
📊 Na HDI, o primeiro POST devolve *"aguarde, estamos processando"* + um
formulário que se reenvia sozinho em 5 s. **É o reenvio que traz a tabela.**
Quem parar no primeiro POST lê zero linhas e conclui "nenhum inadimplente" —
falhando com status `done`, que é o pior desfecho possível.

> **Regra:** antes de concluir "não há inadimplentes", provar que a **tela foi
> lida**. Corpo com bytes e zero linhas extraídas ≠ carteira em dia.

**(c) O portal impõe limites de janela e de frequência.**
📊 HDI: máximo 30 dias por busca (validação do próprio botão). Akamai bloqueia
por volume. **Varredura em blocos, e o mínimo de visitas possível.**

**(d) Nem toda parcela em atraso tem boleto.**
📊 Débito automático e cartão recusados **não geram 2ª via** — e convertê-los
exige um botão que escreve no contrato. Esses casos viram **tarefa para a
atendente**, e o robô **não fala com o segurado**.

---

## 2. AS CINCO FASES

Nenhuma fase começa sem a anterior fechar. Cada uma tem teto de visitas.

### FASE 0 — RECONHECIMENTO · máx. **2 visitas**
```
0.1  🧑  credencial cadastrada em Conectores > Portais, e o Founder
         confirma que entra na mão
0.2  🤖  medir a porta: tem captcha ativo? tem WAF? o formulário monta?
0.3  🧑  print do menu do topo + print da tela dos atrasados
PORTÃO:  sei o nome da tela e se a porta abre para um navegador automatizado
```

### FASE 1 — CAPTURA · **0 visitas minhas** (o Founder captura)
```
1.1  🧑  a chamada que LISTA os atrasados   (Headers + Payload + RESPONSE)
1.2  🧑  a chamada que BAIXA o boleto       (Headers + Payload + RESPONSE)
PORTÃO:  as duas chamadas em mãos, COM O RESPONSE
```
> 📊 O **Response** é o item que mais falta e o que mais resolve. Sem ele eu
> adivinho a estrutura; com ele eu leio. Na HDI, o Response fechou 4 defeitos
> de uma vez.
>
> **Filtro do F12 por portal:** `dsp_` na HDI. Nunca `api` — 📊 a HDI não usa
> essa palavra em endereço nenhum, e o filtro trouxe só extensão do Chrome.

### FASE 2 — REPLICAR FORA DO ROBÔ · máx. **1 visita**
```
2.1  🤖  refazer a cadeia num script isolado, com a sessão do corretor
PORTÃO:  sai um arquivo que começa com %PDF-
```

### FASE 3 — A JOURNEY · **0 visitas**
```
3.1  🤖  journeys/<portal>.py — parsers PUROS, testáveis offline
3.2  🤖  fixture ANONIMIZADA do HTML/JSON real em tests/fixtures/
3.3  🤖  lista testada de botões proibidos daquele portal
3.4  🤖  uma linha no mapa `JOURNEYS`
PORTÃO:  testes verdes contra a fixture, sem tocar no portal
```
> **Fixture no repo: estrutura real, dados inventados.** SPEC-023A §4 —
> evidência com dado de segurado não vai para o git.

### FASE 4 — LIGAR · **1 rodada**
```
4.1  🤖  a caixinha da seguradora aparece na tela da corretora
4.2  🤖  rodada em modo teste COM A ALLIANZ JUNTO como LINHA DE CONTROLE
4.3  🧑  Founder avisado ANTES, porque envia WhatsApp
PORTÃO:  job `done` com PDF no bucket, E a Allianz continua 4 de 4
```
> **A linha de controle é o que dá direito à conclusão** (CLAUDE.md §9.2). Sem
> ela, um sucesso do portal novo pode ser mérito de outra mudança.

### FASE 5 — REGISTRAR · **0 visitas**
```
5.1  runbook do portal (mapa das telas e da cadeia)
5.2  pendências no PENDENCIAS.md, com dono e o que destrava
```

---

## 3. Onde cada seguradora está

| Seguradora | Fase | Porta | Falta |
|---|---|---|---|
| **Allianz** | ✅ 5 | senha, sem captcha | nada. 📊 4 de 4 boletos em 12/08 |
| **HDI** | ✅ 3 | senha, **Akamai** | rodar pelo worker (depende do deploy) |
| **Tokio** | 0 | senha via SSO OpenAM, **sem captcha** | prints do menu + captura |
| Yelum | 0 | 🔴 WAF barra até o headless novo | investigar a porta |
| Bradesco | 0 | 🔴 reCAPTCHA ativo | HITL de captcha |
| SulAmérica | 0 | 🔴 reCAPTCHA ativo | HITL + credencial |
| **Porto · Azul** | 0 | 🔴 captcha (mesmo grupo) | **o HITL de captcha, peça própria** |
| MAPFRE | 0 | ✅ a porta mais limpa medida | 🧑 **a credencial** |

---

## 4. O navegador — e por que ele mudou

📊 Medido em 10/08/2026 contra a HDI, um fator por vez, com CONTROLE repetido
no início e no fim:

```
headless clássico ...........  BLOQUEADO  "Access Denied" (Akamai)
+ args anti-automação .......  BLOQUEADO
+ script de stealth .........  BLOQUEADO
+ args E stealth ............  BLOQUEADO
navegador COM janela ........  PASSOU
--headless=new ..............  PASSOU     ← e roda sem tela
```

**Cinco variações, o mesmo bloqueio → nenhuma delas era a causa.** O fator é o
*modo* headless: o clássico é um binário separado, com impressão digital
própria. O `--headless=new` é o mesmo Chrome de janela sem desenhar.

📊 **Linha de controle:** a Allianz baixou **4 de 4 boletos** com o modo novo.
Sem regressão — e é isso que dá direito de creditar o ganho ao modo, e não a
outra coisa.

Vive em `portal_worker.worker._launch_kwargs()`, configurável por
`PORTAL_HEADLESS_MODE` (`new` · `classic` · `headed`).

---

## 5. Arquitetura: COLHER ≠ ENTREGAR

```
sessão do portal HDI ....... 30 min      (medido)
espaçamento entre envios ... 4 a 8 min   (governador, SPEC-063 C)
20 inadimplentes ........... ~2 horas
```

**Um-a-um ponta a ponta é impossível:** a sessão morre no minuto 30 com 1h30 de
envios pela frente. E entraria no portal 20 vezes por rodada — o gatilho exato
do bloqueio.

```
COLHER    uma entrada por portal. Baixa TODOS os boletos. Não envia.
          Não depende de WhatsApp, de InfoCap nem do governador.

ENTREGAR  independente, ordenada, governada, em horário comercial.
          Pode parar no meio e continuar amanhã de onde parou.
```

**A fila** (`billing_collection.fila_de_cobranca`):
- carência de **48 h** aplicada duas vezes — na janela do portal e de novo aqui
- ordem: **dívida mais velha primeiro** (é a mais perto do cancelamento)
- **sem data legível → não envia.** Não saber nunca vira permissão para cobrar
- **sem boleto por regra da seguradora → não envia.** Vira tarefa da equipe
- retomada segura pelo `billing_sent_log`, que já existia

---

## 6. As três regras que não se negociam

1. **O portal da corretora não é ambiente de teste.** Teto de visitas por fase;
   toda leitura repetida sai de fixture.
2. **Nenhum robô aperta botão que escreve no contrato do segurado.** Por portal,
   a lista é explícita e **testada** — na HDI: `REPROGRAMAÇÃO DE PARCELA`,
   `TERMO DE ADIMPLÊNCIA`, `ANTECIPAÇÃO DE PARCELAS`, `ALTERAÇÕES FINANCEIRAS`.
3. **Teste de cobrança nunca manda mensagem para cliente inadimplente.** Usa o
   WhatsApp da AMANDUS SEGUROS, e o Founder é avisado antes.

---

## 7. Critérios de aceite por seguradora

- [ ] credencial em `portal_accounts`, cifrada, para **cada** corretora
- [ ] journey com parsers puros + fixture anonimizada + testes verdes
- [ ] lista de botões proibidos, com teste que **consegue falhar**
- [ ] um job local terminando `done` com PDF válido (`%PDF`)
- [ ] a caixinha aparece na tela, e marcar uma **não desmarca** as outras
- [ ] rodada em modo teste com a **Allianz junto** como controle
- [ ] runbook + pendências registradas

---

*Autoridade: CLAUDE.md · SPEC-020 (motor) · SPEC-023/023A/023B (cobrança) ·
SPEC-033 (método) · SPEC-063 Bloco C (governador de vazão).*
