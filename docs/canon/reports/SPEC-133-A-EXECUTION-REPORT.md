# SPEC-133-A — Quem Cobra Menos no WhatsApp, piloto fechado · relatório de execução

> 07/10/2026 · branch `spec/133-A-qcm-whatsapp` · base `de66449` · rito AAA v13, 🔴 CRÍTICO · SPEC
> `specs/SPEC-133-A-quem-cobra-menos-no-whatsapp.md` · BLOCO 0 `programa-multicalculo/BLOCO0-DA-133-A.md` · laudos no rascunho do
> gerente (`laudos/133a-juiz.md`, `133a-red.md`, `133a-confirmacao.md`)

**Nota da execução: 88/100** (confirmação 84 → 88 com o conserto do B3; juiz 74 · red team 68 antes do conserto).

## EXECUTION CARD
```
OUTCOME ..............  um número CONVIDADO manda "oi" ao Quem Cobra Menos e chega ao resultado na mesma conversa: consentimento,
                        11 perguntas uma por vez (com "quanto você paga hoje?"), o pedido ao motor nas corretoras parceiras, a
                        proposta com a PÁGINA DA MARCA QCM, a mensagem na copy do Founder (D-130A1-15), a pergunta final, até 2
                        lembretes, a passagem. QR no portal admin. Ninguém fora do convite recebe nada. 📊 provado pelo fio
                        (webhook real → balões → página → passagem); o envio ao vivo espera T-132…T-135
RISCO ................  8 — ALCANCE 3 · REVERSIBILIDADE 3 · FREQUÊNCIA 2
SUPERFÍCIE ...........  3 — o webhook de entrada de todas as corretoras ganhou o desvio
PISO APLICADO ........  §3.2 — envia a pessoa real · migration com dado pessoal · toca a entrada do atendimento
NÍVEL ................  🔴 CRÍTICO · gerente Opus 5.5 · builders Opus 5.5 · juiz ‖ red team · conserto · confirmação
O FIO ................  BLOCO0 §11 · teste `backend/tests/test_spec133a_o_fio.py` (17 casos: o caminho feliz + 4 controles com
                        ZERO envio + não-regressão do observer + lembretes + passagem) — nasceu VERMELHO ({'status': 'observed'})
PARALELISMO REAL .....  F0 ‖ FM ‖ BLOCO 0 → F1 ‖ F2 ‖ F4 → F3 → COSTURA (arquivos disjuntos; contrato §3)
UNIDADES .............  U1–U10 (SPEC §1)
COESÃO ...............  F1 (entrada) · F2 (conversa+cotação) · F3 (página) · F4 (QR) · F0 (copy) · FM (marca)
TIME .................  gerente · investigador · F0 · FM · F1 · F2 · F3 · F4 · aplicador · costura · juiz ‖ red team · conserto ·
                        confirmação · conserto B3 · investigador dos guardas · prévia visual
REFERÊNCIA ...........  SPEC §7.3
GATES ................  G1–G11 (SPEC §5)
O ELO ................  "o canal só fala com quem foi convidado PORQUE o filtro roda antes de qualquer envio": 0 send_message nos 4
                        controles pelo webhook real; e "nenhum CPF vai ao modelo": 17 formatos de CPF vazam 0 (máscara + só regra
                        no consentimento)
FAIXA DE RELÓGIO .....  💭 6–9 h · 📊 ~10 h (o julgamento achou 3 blockers)
```

## 1. O que mudou
- **F0 — a copy do Founder (D-130A1-15):** "Prontinho, <nome>! Descobrimos Quem Cobra Menos no Seguro do seu <carro> / Fiz <N>
  Cotações entre Corretoras de Nível 5 e <M> Seguradoras[ em <tempo>]." · N = `canal.volume.base` (100) + preços + tentativas com erro
  (📊 canário 189) · M = seguradoras consultadas (📊 16) · nunca o número de corretoras (mensagem e página) · economia = seguro atual
  (apólice ou declarado) − o menor de todos (sem atual: maior − menor) · a menor parcela em destaque (número em negrito).
- **FM — a marca:** a tela de identidade ganhou "Trocar o logo" e "Ano de fundação"; a captura presa vira "falhou" em 10 min; a causa
  raiz da captura que nunca terminava (o upsert do logo dava 42P10 no banco — 📊 EXPLAIN) consertada; a AutoFleet gravada pelo serviço
  (logo do Founder, 2011, publicada) → 📊 ensaio: "marca publicada: sim", "SUSEP: 242159031", "15 anos de mercado".
- **F1 — a porta de entrada:** desvio do canal no webhook (Evolution GO) antes do observer; convidados, limite por dia, anti-laço
  (linha/agente de corretora, fromMe, grupo, teto de mensagens), estado cifrado, envio pela integração do canal, comando dos convidados;
  migration `20261007_01` (4 tabelas, RLS sem policy + REVOKE + filtro no código, dois tenants no VERIFY).
- **F2 — a conversa e a cotação:** estado + o modelo só para entender resposta livre (papel `canal_cotacao`, gpt-6-luna medium, reserva
  Sonnet 5.5 low — migration `20261007_02`); a placa supre FIPE/ano/combustível no canal; Work Run `canal.cotacao` (acompanhar →
  publicar → mensagem → 2 lembretes → passagem).
- **F3 — a página do Quem Cobra Menos:** renderizador próprio com a marca QCM (o "Q" em SVG), a corretora vencedora dentro, o bloco
  "Só cotamos com Corretoras Nível 5", o melhor preço por seguradora, o "Quero fechar" de volta à conversa do canal; o mesmo script/hash;
  a carteira byte a byte igual.
- **F4 — o QR no admin:** Conexões → Canais: Quem Cobra Menos (WhatsApp); só master admin; empresa do canal pelo tipo.
- **COSTURA:** o número do canal no modelo, as chaves de limite/teto na config, fechar pela página, lembretes no teto, a passagem com
  evento + card no Inbox do operador (D-133A-16).

## 2. Julgamento
| papel | nota | o que pegou |
|---|---|---|
| juiz | 74 | B1 mídia/apólice como resposta e CPF ao modelo; B2 preso em "calculando" |
| red team | 68 QUEBREI | os mesmos B1/B2 + 10 pendências (lembrete 0→2, convidado removido recebe lembrete, domingo, mídia de não convidado baixada, sem palavra de saída, corrida, nome do canal à mão…) |
| conserto único | — | B1, B2 e 7 pendências; 56 testes novos; 17 mutações vermelhas |
| confirmação | 84 → **88** | B1/B2 CONFIRMADOS; B3 novo ("não quero mais" no meio da frase apagava a conversa) → consertado + a máscara de CPF com qualquer separador |

## 3. Testes (saída real)
- costura: `17 passed` (fio) · bateria das fatias `316 passed`
- conserto: `361 passed in 123.86s` · B3: `166 passed in 66.52s`
- §9.1 (juiz): `next build` exit 0 · `next start` · `GET /api/admin/canais/whatsapp` → 401 · POST de outra origem → 403 · a página → 307

## 4. Bateria (2 metades em paralelo, worktrees no commit `2398175`)
- metade 1: `29 failed, 3448 passed, 3 skipped, 31 xfailed, 1 xpassed in 2897.37s` — 24 da linha de base; 5 novas → `test_spec116_reserva_p0`
  (o papel novo declarado no mapa, §9.3 → 23 passed) · `test_o_grupo_so_fala_de_quem_precisa` e `test_spec061_colunas_reais` (guardas que
  não conheciam o canal, §9.3 com mutação → 2 passed) · `test_o_conhecimento_global_sai_anonimo` e `test_spec040_onda3_distiller`
  (falham IGUAL na base `de66449` — estouram 120 s no runner; direto passam 112/0 e 25/0: pré-existentes)
- metade 2: `15 failed, 2334 passed, 6 skipped in 2474.33s` — 14 da linha de base; 1 nova → `test_spec051_pairing_passkey` (a ponte mudou
  de arquivo na F4, §9.3 → 5 passed)
- **0 regressão de produto.**

## 5. Migrations (APLICADAS em produção, psycopg numa transação, `lock_timeout 5s`, registradas em `schema_migrations`)
`20261007_01_spec133a_canal` · versão `20261007091841` · VERIFY `0·0·0·0·0·0·0` → `4·0·0·3·1·4·4` · comportamental OK (dois tenants) ·
`20261007_02_spec133a_papel_canal_cotacao` · versão `20261007091910` · comportamental OK · snapshot de modelos regenerado.

## 6. O que ficou fora (com dono)
P-133A-01…08 em `PENDENCIAS.md` (fixture real do "oi" · nenhuma corretora com destino de aviso · garagem/uso/estado civil assumidos ·
portão de mídia só na rota GO · expurgo de mídia/retenção · a corrida turno×run · o motor no contêiner (F5) · botão "Publicar" e logo
SVG). Riscos para o Founder: a D-130A1-15 é configuração (`canal.volume.base`) — desligar antes do público.

## 7. Canário Amandus → Resulta → AutoFleet
Sem envio real nesta SPEC: o envio ao vivo depende de T-132 (Implantar), T-133 (QR), T-134 (convidados) e T-135 (robô do Agger). Prévia
visual com os dados reais do canário: https://claude.ai/artifact/Js8TDvChAtdxhQiuVFidwZ.

## 8. Declaração
Nenhum motor paralelo: o webhook, o envio, o pareamento, o roteador de modelos, o Work OS (runs, despertador), a porta/motor, o Artifact
Hub e a marca são os que já existiam; o canal é um desvio por tipo de empresa e um módulo `services/canal/`. Nenhum nome de corretora ou
telefone em código.

## 9. Entrega
O código, os testes e o relatório (07/10):
```
To https://github.com/Amandico100/AutoBrokers-Intelligence-OS.git
   de66449..6926b8d  HEAD -> main
```
O estado do programa, a fila e o painel (`docs(133-A): estado do programa, fila e painel`, 07/10):
```
$ git push origin HEAD:main
To https://github.com/Amandico100/AutoBrokers-Intelligence-OS.git
   6926b8d..563f7c9  HEAD -> main
$ git push origin HEAD:spec/133-A-qcm-whatsapp
To https://github.com/Amandico100/AutoBrokers-Intelligence-OS.git
   6926b8d..563f7c9  HEAD -> spec/133-A-qcm-whatsapp
$ git rev-list --count origin/main..HEAD
0
```
Painel do Founder republicado (versão 32): https://claude.ai/code/artifact/defe331c-9399-4584-9d1c-2126a527cea0 — abas início, tarefas
(T-132…T-135 na ordem), specs e pendências (P-133A-01…08).
