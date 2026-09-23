# RELATÓRIO — EXTRA-002 · parte 1 · a perícia do Agger (MODO INVESTIGAÇÃO)

**22/09/2026** · branch `docs/extra-002-investigacao-agger` · commit inicial `d8510df` (= `origin/main`, 📊 `git rev-list --count HEAD..origin/main` → 0) · executor: Opus 5.5 (escolha do Founder para esta sessão; o protocolo §10 prevê Fable como gerente — registrado)

## EXECUTION CARD

```text
OUTCOME .............. o Founder sabe, com evidência, se dá para cotar e renovar pelo Agger, como
                       encaixar no AutoBrokers sem motor paralelo, e em que ordem construir
RISCO / SUPERFÍCIE ... não se aplica — MODO INVESTIGAÇÃO (§3.3). Zero código de produto, zero escrita
                       no banco, zero acesso ao vivo a sistema de terceiro
NÍVEL ................ investigação: medidor ×2 (código · banco) · cético · juiz do risco · confirmação
O FIO ................ intake (HAR/HTML/PDF) → perícia de rede → laudos internos → propostas → cético ‖ juiz
                       → conserto único → confirmação
PARALELISMO REAL ..... F1a ∥ F1b (read-only, arquivos distintos); cético ∥ escritor 004/007
REFERÊNCIA ........... interna: PolicyDataProvider, LeaseDePortal, laboratório SPEC-077; observada: o PDF de
                       3 colunas da corretora; externas: RP §9 (incompleta — P-E002-06)
GATES ................ G1–G20 da proposta §7
O ELO ................ "o formulário do ano anterior alimenta a renovação": medido que `negocio/{id}` devolve
                       o formulário (📊 2/2); QUANTAS renovações têm esse histórico → E2 (não medido)
FAIXA DE RELÓGIO ..... 💭 1–2 h · real 📊 ~1 h de executor + agentes em paralelo (telemetria abaixo)
```

## 1. O que foi feito

| fase | resultado |
|---|---|
| preflight | 📊 0 atrás · 0 à frente · árvore com arquivos locais do Founder (não tocados) |
| a EXTRA-002 já existia? | 📊 não — só a linha da fila (`ESTADO-DAS-SPECS.md:117`) |
| perícia dos 3 HARs | 📊 API JSON com token de 8 h, sessão única, cálculo assíncrono (disparo + 28 pollings), resultado padronizado com PDF, 6 famílias de erro, ~45 campos |
| laudo F1a (código) | zero código de cotação; Work OS sem espera durável nem retomada real; laboratório SPEC-077 aprende o Agger (nota 82) |
| laudo F1b (banco) | não há tabela de apólices; lista de renovações vem ao vivo da InfoCap; 📊 Resulta ≈3,3 renovações/dia (todos os ramos); `renovacao-maxima` só catálogo |
| propostas | 002 (+RP), 003, 004, 007 em `docs/canon/specs-propostas/` |
| cético (Fable) | 002 **71** · 003 **58** — 7 blockers |
| juiz do risco (Fable, cego ao cético) | 002 **84** · 003 **74** — 4 blockers |
| conserto único | builder Opus; 18 itens; nenhum blocker rebaixado |
| confirmação | ✅ CONFIRMADO — 002 **88** · 003 **90** |

## 2. Arquivos

| arquivo | bytes (📊 `wc -c`) |
|---|---:|
| `specs-propostas/SPEC-EXTRA-002-investigacao-prova-agger.md` | ~29 k |
| `specs-propostas/SPEC-EXTRA-002-investigacao-prova-agger-RESEARCH-PACK.md` | ~27 k |
| `specs-propostas/SPEC-EXTRA-003-renovacao-feita.md` | ~30 k |
| `specs-propostas/SPEC-EXTRA-004-cotacao-pelo-chat.md` | 20.449 |
| `specs-propostas/SPEC-EXTRA-007-comparador-da-corretora.md` | 17.600 |
| este relatório | — |
| ESTADO-DAS-SPECS · FOUNDER-DECISIONS (D-E002-01..08 como PROPOSTAS) · PENDENCIAS · TAREFAS-DO-FOUNDER · painel (fonte + `montar.py`; **não republicado**) | +121 / −5 |

Migrations: **nenhuma**. Testes: **não se aplica** (nenhum código). Canário: **não se aplica**.

## 3. Achados — FATO · INFERÊNCIA · RECOMENDAÇÃO

**FATO (📊)**
1. O Aggilizador é uma interface sobre uma API JSON (`api-prod.aggilizador.com.br`, `api.multicalculo.net`); token no cabeçalho `Authorization`, 8 h; sessão única (`derrubaSessao`).
2. O cálculo é disparado em ~2 s e coletado por polling; ofertas válidas completas em 30 s e 229 s; conjunto fechado em 420 s e 413 s (n = 2).
3. O resultado já vem padronizado por seguradora, com prêmio, franquia, coberturas, parcelamentos, nº do cálculo e PDF.
4. 🔴 As senhas dos portais das seguradoras (`login/senha/loginWs/senhaWs`) vêm em 5 tipos de resposta, em **todas** as 28 respostas de polling e no corpo do disparo.
5. O formulário do ano anterior volta inteiro por `negocio/{id}` — inclusive o questionário de risco, que a InfoCap não tem.
6. A cotação da corretora vale 5 dias (PDF-modelo e cálculo Bradesco do intake).
7. O AutoBrokers não tem código de cotação; tem a lista de renovações, o Artifact Hub, a marca e o link público; não tem espera durável.

**INFERÊNCIA (💭)**
- O corte de ~7 min pode ser do Agger ou por seguradora (mesmo confundidor nos 2 casos).
- Os volumes dos pilotos cabem na madrugada com 1 cálculo por vez; corretoras grandes precisam de paralelismo ou de espalhar o cálculo pelo dia anterior.
- O maior risco do produto não é técnico: é a dependência de um fornecedor que é dono dos dois elos (InfoCap e Aggilizador).

**RECOMENDAÇÃO**
- Pedir à Agger, na mesma conversa, a API oficial **e** a anuência para acesso programático; sem anuência, **nenhuma** automação (nem por navegador).
- Construir por trás de uma porta `QuoteProvider`, irmã do `PolicyDataProvider`.
- A fundação (espera durável + porta + adaptador) antes do ciclo de renovação; 003 dividida em A/B; depois 004; o site público por último.

## 4. Confirmação (§6.1)

✅ **CONFIRMADO** (juiz Fable novo, só o diff do conserto): B1 senhas, B2 sessão única × workers, B3 espera durável em `work_runs` e B4 trocar senhas já — **fechados**, cada um com arquivo:linha conferido; 📊 o juiz **reproduziu no acervo** as senhas em 28/28 pollings. Contas da §5 refeitas — todas batem. **Notas finais: 002 → 88 · 003 → 90.**
4 defeitos de forma apontados e consertados no mesmo commit: "17" vs "~15" portais padronizado; "mesmo processo que a API" virou ❓ (`WORK_WORKER_IN_PROCESS`); o comando da varredura de chaves nomeado; VERIFY da migration alinhado ao APPLY condicional.

## 5. O que ficou fora, e por quê

| item | por quê | custa esquecer |
|---|---|---|
| prova ao vivo no Agger (E1–E4) | exige usuário robô e anuência da Agger — caixa do Founder | G1, G5, G13 ficam sem prova |
| E0 (volume AUTO por dia) | a conexão InfoCap da Resulta está hoje sob a corretora Amandus (P1 a confirmar) | a equação das 7h fica com N 💭 |
| pesquisa externa (documentação Agger, comparadores) | a subtarefa foi interrompida nesta sessão e não foi refeita | referências das propostas 002/003 incompletas (P-E002-06) |
| cotação nova com HAR | o intake não tem HAR de seguro novo | G7 parcial |

## 6. Pendências novas

- **P-E002-HAR** — os 3 HARs têm senhas de portal e o token de uma pessoa: apagar após a parte 2; **trocar as senhas agora**.
- **P-E002-LAB** — a saída de `portal_factory.py lab api-infer` sobre esses HARs guarda valores sem redação: nunca versionar.
- **P-E002-06** — referência externa incompleta nas propostas 002/003.
- **P-E002-X1** (fora do escopo, laudo F1b) — conexão "InfoCap RESULTA" criada dentro da Amandus em 21/09 20:29; Resulta sem conexão utilizável. ❓ intencional.
- **P-E002-X2** (laudo F1a) — `research_tool` cria run com `source_type` proibido → 📊 0 runs de pesquisa na vida.
- **P-E002-X3** (laudo F1a) — 11 runs `queued` eternos; `retry_scheduled` sem re-enfileirador (a 003-A cura).
- **P-E002-X4** (laudo F1a) — `smith_worker` sobrescreve `waiting_approval` com `completed` (a 003-A cura).

## 7. Riscos remanescentes

Anuência da Agger negada · API muda sem aviso · licença por usuário robô · senha do robô expira · renovações sem histórico no Agger (❓ E2) · seguradoras de madrugada (❓ E3) · concorrência por sessão (❓ E4).

## 8. Declaração

Nenhum motor paralelo foi criado. Nenhum código de produto, migration ou escrita em banco. Nenhum acesso ao vivo ao Agger, à InfoCap ou a portal de seguradora. Nenhuma credencial, token, CPF ou placa em arquivo versionado (📊 `grep -cE "eyJ…|CPF"` nos 5 documentos → 0).

## 9. Telemetria (§11) — `python backend/scripts/medir_execucao_claude_code.py --sessao atual`

```text
EXECUTOR                     58 min  turnos  48  pico 374k  ctx 12.6M  saída 103k  US$ 10.84  opus-5-5
F1a medidor código           17 min  turnos 123  pico 315k  ctx 24.5M  saída  10k  US$ 14.34  opus-5-5
F1b medidor banco             8 min  turnos  50  pico 219k  ctx  7.2M  saída  17k  US$  5.17  opus-5-5
escritor 004/007              9 min  turnos  39  pico 158k  ctx  4.4M  saída   2k  US$  3.02  opus-5-5
cético                        8 min  turnos   9  pico 133k  ctx  0.8M  saída   3k  US$  1.96  fable-5-1
juiz do risco                10 min  turnos   8  pico 165k  ctx  0.9M  saída   2k  US$  2.09  fable-5-1
conserto único                5 min  turnos  22  pico 163k  ctx  2.7M  saída   1k  US$  2.32  opus-5-5
TOTAL (antes da confirmação e do atualizador)  7 agentes · 300 turnos · ctx 53.1M · US$ 40.09
+ confirmação (Fable) e atualizador de documentos (Opus) — 9 agentes no total
achados por mecanismo: cético 7 blockers (3 exclusivos) · juiz 4 (2 exclusivos: sessão × workers; trocar senhas já)
· executor 1 (senhas também nas respostas, medido) · ⚠️ pico do executor 374k > teto 300k do protocolo — delegado o conserto
nota do executor: 86 (perícia completa e honesta; prova ao vivo e referência externa pendentes)
```
