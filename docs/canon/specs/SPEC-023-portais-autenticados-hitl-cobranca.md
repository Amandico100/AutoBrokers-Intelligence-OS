# SPEC-023 — Portais autenticados (login/CAPTCHA/2FA com HITL) + Auxiliar de Cobrança multi-portal

**Autor original**: chat anterior (Opus). **Reescrita completa**: Opus 4.8 (2026-07-07), depois de validar
o código real e acessar os portais ao vivo. **Status**: pronta para execução por um chat novo (GPT-5.5),
que deve **entender tudo, perguntar e só então executar** — nunca executar de cara.

> Esta SPEC **constrói SOBRE** o motor já pronto (SPEC-020: `portal_worker` + Camada 2 `adaptive.py` +
> vault Fernet + `portal_jobs`). **É PROIBIDO criar estrutura paralela.** Tudo aqui reusa o que existe:
> o mesmo worker, a mesma tabela de jobs, o mesmo cérebro adaptativo, o mesmo vault, a mesma galeria de
> Auxiliares/Rotinas (SPEC-019) e o mesmo seam de WhatsApp do atendente. Quem propuser um "novo motor",
> uma "nova fila", um "novo browser service" está ERRADO — leia a seção 2 e o §9 (anti-paralelo).

---

## 0. Glossário rápido (pra não haver confusão de nomes)

- **Motor de portais** = `backend/portal_worker/` (serviço no EasyPanel: FastAPI + Playwright + poll de `portal_jobs`).
- **Camada 2 / cérebro adaptativo** = `backend/portal_worker/adaptive.py`. LLM-visão que ENXERGA a tela e
  decide a próxima ação. É o que dá INTELIGÊNCIA (não engessa). Reusar como está; estender, nunca duplicar.
- **Journey** = fluxo determinístico por portal em `backend/portal_worker/journeys/`. Faz o que é ESTÁVEL
  (login, ir até uma página) e delega o resto ao cérebro adaptativo.
- **Auxiliar / Rotina** = automação da galeria (SPEC-019, `routine_templates` + executor). O **Auxiliar de
  Cobrança** é uma rotina agendada que orquestra o motor.
- **Vault** = `PORTAL_VAULT_KEY` (Fernet). Guarda login/senha dos portais por corretora, cifrados.

> Atualizacao de continuidade (2026-07-09): antes de continuar a implementacao, leia tambem
> `SPEC-023A-allianz-cobranca-runbook-operacional.md` e
> `SPEC-023B-pendencias-portais-cobranca-atendimento.md`. Esses documentos registram o estado real apos
> a correcao do fluxo Allianz: varredura real de 4 inadimplentes, download real de 1 PDF pelo worker,
> evidencias locais, dificuldades encontradas e pendencias para fechar a rotina ponta a ponta. Nao use
> credenciais coladas em docs como fonte de verdade; credenciais de portal devem vir do vault/dashboard.

## 1. Objetivo

Hoje o motor dirige o portal **público** de vidros ponta a ponta (SPEC-025, funcionando). Falta habilitar os
portais **com login**, que destravam os Auxiliares de verdade — o primeiro é **Cobrança**:

> Todo dia, num horário definido, o Auxiliar entra em **cada portal de seguradora que a corretora conectou
> e selecionou**, lista os **segurados com parcela ATRASADA**, baixa o **boleto (PDF)**, e **envia no
> WhatsApp do cliente** com uma mensagem pronta — depois entrega um **relatório ao corretor**. Se o cliente
> responder com dúvida, o atendente responde; se não souber, passa pra humano.

Os portais autenticados têm 3 obstáculos que o público não tem: **login (usuário/senha), CAPTCHA e 2FA**.
A LLM precisa entrar, com ajuda do humano SÓ quando o portal exigir (CAPTCHA/2FA), e executar **sem errar e
sem travar** — com a mesma disciplina que resolveu o vidros (instrumentar o DOM, nunca chutar, cérebro livre).

## 2. O que JÁ existe (REUSAR — é proibido reinventar)

| Peça | Onde | Como reusar na Cobrança |
|---|---|---|
| Motor de portais | `backend/portal_worker/` | Enfileira `portal_jobs` com `journey` de cobrança; o worker executa. |
| Camada 2 (cérebro) | `adaptive.py` | Dirige as telas do portal de cobrança que não forem determinísticas. **Já robusto p/ Angular Material** (md-select via JS-click, autocomplete, `_find_input` por id+label, `pending_required`, similaridade de tokens, para por não-progresso, `debug_dom`). |
| Journey de login | `journeys/vidros_lanternas.py::login_check` + `interpret_login` | Ponto de partida do login autenticado (já classifica OK / falha / CAPTCHA-2FA→needs_human). |
| Vault Fernet | `PORTAL_VAULT_KEY` | Credenciais por corretora, cifradas; o worker lê pelo id da conta, nunca do LLM. |
| Tabelas | `portal_jobs`, `portal_accounts`, `portal_sessions`, `portals` | `portal_sessions.storage_state` = sessão persistida (cookies) p/ não relogar toda vez. |
| Tool no graph | `portal_action` (`portal_tool.py`) | O padrão de tool que enfileira job e aguarda; a rotina de Cobrança usa o MESMO padrão. |
| Ponte de dados InfoCap | `infocap_vehicle_item` / provider `vehicle` (SPEC-025) | O padrão de buscar dados reais do cliente (CPF→telefone/apólice) server-side. Reusar p/ resolver o WhatsApp do inadimplente. |
| Galeria de Rotinas | SPEC-019 (`routine_templates`, executor em loop) | O Auxiliar de Cobrança é uma ROTINA agendada aqui — não um serviço novo. |
| Envio WhatsApp | seam do atendente (`whatsapp_service` + `get_whatsapp_integration(company_id, agent_id)`) | Manda o boleto ao cliente pela MESMA integração da corretora. **Atenção**: resolver o agente atendente antes (o lookup sem agent_id é estrito e volta None — bug já corrigido no vidros/residencial; reusar `_attendance_agent_id`). |

## 3. Decisão de portal piloto (validado ao vivo em 2026-07-07)

| | **Allianz** (recomendado 1º) | **Porto Seguro** (fase 2) |
|---|---|---|
| Login | `Usuário` / `Senha`, **sem reCAPTCHA, sem 2FA** | CPF/Senha **com reCAPTCHA** (site-key confirmado) |
| Base técnica | Angular (`ngx-epac`) — o cérebro já domina | SPA/JS-heavy |
| Risco de bloqueio | médio | alto |
| Jornada de cobrança | sim | sim |
| Credencial (Resulta) | `BA068610` / `Resulta2029@` | `00342430971` / `Bee1812!` |
| Portal | `https://www.allianznet.com.br/ngx-epac/public/home` | `https://corretor.portoseguro.com.br/corretoronline/` |

**Piloto = Allianz.** Login limpo destrava o fluxo inteiro sem depender do humano no loop. Porto entra na
fase 2, junto com o HITL de CAPTCHA (P2), porque exige resolver o reCAPTCHA todo login.

## 4. Arquitetura MULTI-PORTAL (o founder pediu explicitamente)

A corretora conecta **vários** portais; o Auxiliar varre **todos os que ela selecionar**, todo dia.

```
Personalização → Conectores → Portais (multi-tenant, vault)
   portal_accounts:  (company_id, portal_key, account_label, credential_ref, status, health)
   ex.: Resulta → [allianz(ok), porto(pendente-captcha), hdi, tokio, bradesco...]

Auxiliar de Cobrança (Rotina agendada — SPEC-019):
   config: { portais_selecionados: [allianz, ...], horario: "09:00", dias: [seg..sex],
             mensagem_template, aprovacao_antes_de_enviar: true }
   a cada execução, PARA CADA portal selecionado:
     enfileira portal_job(journey="cobranca_sweep", portal_key, account_ref)
     → worker: login(sessão) → página de inadimplência → lista parcelas atrasadas
        → baixa boleto (PDF → bucket privado) → devolve [{cliente, cpf, apolice, venc, valor, boleto_url}]
   consolida todos os portais → dossiê → (aprovação) → envia no WhatsApp de cada cliente → relatório ao corretor
```

Pontos-chave da arquitetura:
- **Um `portal_job` por portal por execução** (não um gigante). Falha num portal não derruba os outros.
- **Sessão persistida por conta** (`portal_sessions.storage_state`): loga 1x, reusa cookies; expirou → reloga.
- **Seleção de portais fica no config da Rotina** (a corretora liga/desliga quais varrer). Endereço do
  portal é global (`portals`); credencial é por corretora (`portal_accounts` + vault).
- **Matching cliente→WhatsApp**: o CPF/telefone vem da InfoCap (mesma ponte do vidros — reusar o provider),
  não do portal. O portal dá o boleto; a InfoCap dá o telefone do cliente.

## 5. Fases

### P1 — Login autenticado + sessão persistida (Allianz)
- `journey allianz.login`: abre o portal, preenche usuário/senha do **vault**, submete; usa `interpret_login`
  + Camada 2 p/ telas novas. Sucesso → salva `storage_state` cifrado em `portal_sessions`.
- Reuso de sessão: antes de logar, tenta `storage_state`; se válido, pula o login.
- **Meta P1**: um `portal_job(journey="allianz.login")` loga e persiste a sessão, provado com a credencial real.

### P2 — HITL de CAPTCHA/2FA (humano no loop, sem gambiarra) — habilita Porto
- Quando o portal pede CAPTCHA/2FA: job vira `needs_human` **com screenshot + instrução**.
- **Dashboard**: card "🔐 Portal precisa de você" com o print + campo pra digitar o código / resolver.
  O worker **pausa** (mantém o browser vivo N min) e **retoma**. v1 = pausa/retomada por código; relay ao
  vivo é fase posterior.
- Nunca burlar CAPTCHA. Humano resolve; a LLM faz o resto.

### P3 — Journey de cobrança (Allianz) — a navegação inteligente
- `journey allianz.cobranca_sweep`: login(sessão) → navega até a área de **cobrança/inadimplência/2ª via**
  → lista parcelas atrasadas → para cada uma, baixa o boleto (PDF) pro bucket privado `portal-evidence`.
- **A navegação usa o cérebro adaptativo** (Camada 2) para as telas variáveis — NÃO seletores rígidos que
  quebram se a Allianz mudar um botão (ver §6 sobre não-engessar). A journey só fixa o que é 100% estável.
- Saída estruturada: `[{cliente_nome, cpf, apolice, parcela, vencimento, valor, boleto_path}]`.

### P4 — Auxiliar de Cobrança ponta a ponta (o caso de ouro)
- Rotina na galeria (SPEC-019), **agendada** (o executor de rotinas já roda em loop): dispara o sweep em
  cada portal selecionado, consolida, e para cada cliente inadimplente:
  - resolve o WhatsApp do cliente (InfoCap por CPF — reusar o provider da ponte de dados do vidros);
  - **aprovação humana** (o corretor revê a lista antes do envio em massa — configurável);
  - envia a mensagem pronta + o boleto (PDF) no WhatsApp do cliente (seam do atendente);
  - registra no relatório ao corretor (enviados / falhas / sem-telefone).
- Se o cliente responder com dúvida → o atendente (já existente) responde; se não souber → handoff humano.

## 6. Regras de ouro — INTELIGÊNCIA sem engessar (herdadas do vidros)

O founder é enfático: **o agente não pode ficar burro**. Se a Allianz mudar um botão, um texto, uma etapa,
o agente TEM que resolver sozinho. Como garantir isso:

1. **Cérebro primeiro, seletor depois.** A journey determinística cobre só o que é invariável (URL de login,
   os 2 campos de login). Todo o resto é dirigido pela Camada 2, que ENXERGA a tela (campos, botões, selects,
   `pending_required`) e decide — exatamente como no vidros. Nada de mapear a cobrança inteira em seletores
   fixos que quebram.
2. **Dê olhos, não amarras.** Antes de qualquer fix, instrumente o DOM real (`debug_dom`, `capture_state`,
   screenshots). Se travou, VEJA o HTML; nunca adivinhe. Foi o que resolveu o vidros (o campo "tipo de
   telefone" era invisível pro cérebro → demos visão → destravou).
3. **Não podar o agente.** Se o cérebro decidiu certo e não funcionou, o bug é do EXECUTOR (achar campo,
   clicar widget) — conserte a mecânica, não adicione regra que deixa o agente burro.
4. **Falha = pausa honesta, não loop.** Passo desconhecido/insuperável → `needs_human` com evidência
   (screenshot + o que viu), nunca "tentar de novo às cegas" nem responder o que não sabe.
5. **Nada sensível sem aprovação.** Baixar boleto = ok (leitura). **Enviar boleto ao cliente / qualquer
   escrita no portal = passo de aprovação.** Gate `PORTAL_REAL_ENABLED` respeitado.

## 7. Modelo de dados (expand-only — reusar o que existe)

- `portals` (registro global): `portal_key`, `nome`, `base_url`, `login_kind`, `has_captcha`, `journeys[]`.
  Seeds: `allianz` (login user/senha, has_captcha=false), `porto` (has_captcha=true).
- `portal_accounts` (por corretora): `company_id`, `portal_key`, `account_label`, `credential_ref` (vault),
  `status`, `health`, `last_login_at`.
- `portal_sessions`: `company_id`, `portal_key`, `account_label`, `storage_state_encrypted`, `verified_at`, `health`.
- `portal_jobs`: reusar; `journey` novo `cobranca_sweep`/`allianz.login`; `params` = `{portal_key, account_ref, ...}`;
  `evidence` = lista de inadimplentes + paths dos boletos; `status` inclui `needs_human` (CAPTCHA).
- Config da Rotina de Cobrança (na estrutura de `routine_templates`/instâncias — SPEC-019): portais
  selecionados, horário, template de mensagem, flag de aprovação.

Migrations **expand-only**. Boletos/screenshots só em bucket privado (`portal-evidence`), retenção 30 dias (LGPD).

## 8. Infra / envs (já provisionado no worker)
`SUPABASE_*`, `PORTAL_VAULT_KEY`, `OPENAI_API_KEY` (Camada 2), `PORTAL_REAL_ENABLED` (gate).
Dockerfile: `backend/portal_worker/Dockerfile`. Base Playwright `v1.47.0-jammy` (pinar `playwright==1.47.0`).
Download de PDF: usar o contexto do Playwright (`accept_downloads=True`) → subir pro bucket privado.

## 9. Anti-paralelo (leia antes de escrever qualquer linha)

**É PROIBIDO**: criar um novo serviço/worker; uma nova fila/tabela de jobs; um novo "browser engine"; um
segundo cérebro de decisão; uma nova UI de conectores; um novo seam de WhatsApp. Se você sentir vontade de
criar qualquer um desses, PARE — já existe e você deve reusar/estender. O valor desta SPEC é **ligar peças
prontas**, não construir de novo. Toda decisão de negócio fica no Smith/na Rotina; o worker só executa
journey + cérebro adaptativo. Cérebro ÚNICO (regra inviolável da SPEC-020).

## 10. Disciplina de execução (TDD house-style)
- Testes: importlib + stubs + `check()`, ASCII, sem pytest (ver `backend/tests/test_spec020_*`). Journeys
  testadas contra HTML fixture local (Playwright `file://`). Frontend (se tocar): `npx tsc --noEmit`.
- Deploy: commit em `feat/spec-017-attendant` → merge `--no-ff` na main → push → trigger EasyPanel
  (API p/ tool/rotina; worker p/ journeys/adaptive). Gate liga o founder.
- **Validar como no vidros**: instrumentar, comparar job bom vs ruim no `portal_jobs`, provar ao vivo.

## 11. O que o founder precisa fornecer (pré-requisitos)
1. **Prints do fluxo de cobrança da Allianz** (login → área de inadimplência → onde baixa o boleto). São o
   mapa do P3. (O founder vai tirar após esta recomendação.)
2. Confirmar as credenciais Allianz no vault (Resulta `BA068610` / AutoFleet `BA267182`).
3. Qual corretora piloto de cobrança (Resulta tem os ramos com boleto; AutoFleet é auto).
4. Ligar `PORTAL_REAL_ENABLED` quando for testar login real.

## 12. Fora de escopo (v1)
Relay VNC ao vivo do CAPTCHA (fase posterior); resolução automática de CAPTCHA (nunca — sempre humano);
portais que proíbem automação por ToS (checar caso a caso). Porto só depois do HITL de CAPTCHA (P2).

## 13. Critérios de aceite
- [ ] Allianz: login real + sessão persistida (não reloga toda vez).
- [ ] `cobranca_sweep` Allianz lista inadimplentes reais e baixa os boletos (PDF no bucket).
- [ ] Auxiliar consolida, resolve WhatsApp por CPF (InfoCap), pede aprovação, envia boleto + msg, relata.
- [ ] Nada é enviado ao cliente sem aprovação; CAPTCHA/2FA → card HITL, nunca burla.
- [ ] Se a Allianz mudar uma tela, o cérebro adapta ou pausa com evidência — nunca loop, nunca chute.
