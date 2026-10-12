# SPEC-131 — O aplicativo de Renovação: a madrugada que calcula tudo antes das 7h (131-A) e o aplicativo onde o comercial confere e envia (131-B)

> **PROPOSTA · v0.1 · 12/10/2026** · agente de síntese do gerente (Opus 5.5) · branch `investigacao/2026-10-12-renovacao`, base `db87ad5`.
> **Não executa nada.** Um chat NOVO escreve e executa 131-A e depois 131-B, em série. Fonte: o
> [PEDIDO](../programa-multicalculo/131/PEDIDO-DO-FOUNDER-2026-10-12.md) e os laudos da mesma pasta — **I1** (motor e madrugada), **I2** (loja e
> telas), **I3** (apresentação e envio); o detalhe mora neles, citado por §. 📊 medido · 💭 ilustrativo · arquivo:linha em `db87ad5`.

---

## 0. Em uma página

**O pedido (Founder, 12/10):** a renovação como **aplicativo**: todo dia, **antes das 7h**, cada comercial encontra no Agger DELE todas as
renovações do dia calculadas (padrão **10 dias** antes do vencimento), sem esquecer nenhuma; no AutoBrokers, a **apresentação** pronta e um
painel para conferir e enviar pelo celular. Depois: negociar, fechar, emitir, registrar.

**O que existe (I1 §1):** as peças, prontas e testadas SEPARADAS — `fonte_infocap.renovacoes_cruas`, o dono (📊 99/99 e 217/217), a ficha
130-B (📊 24/28), `de_apolice`, a porta, `qual_agger`, o motor (📊 canário RE ao vivo 11/10). **Nenhum elo as liga:** 📊 0 pedidos
`servico='renovacao'`; não há lista congelada, estado por apólice, conferência nem aviso. Defeito latente: 📊 ramo desconhecido vira **AUTO**.

**A decisão do gerente:** o chat atual não comporta a execução (📊 contexto do gerente ~640 k > teto 600 k, protocolo §10) → **duas SPECs
executáveis, no MESMO chat novo, em série:**

- **131-A · A madrugada da renovação** (CRÍTICO): o motor diário por corretora — 00:30 · 02:00 · 05:30 · 06:45 —, a tabela `renovacoes`, o
  Agger de quem, o recomendado pela ficha, a recusa explícita do ramo que não cotamos (§1, §4.1–4.5).
- **131-B · O aplicativo de Renovação** (CRÍTICO): o PADRÃO de aplicativo aplicado com conteúdo completo à Renovação, a aba Renovações, a
  página de apresentação de renovação e o envio pelo `wa.me` do próprio comercial (§1, §4.6–4.10).

**Pronto quando — 131-A:** numa madrugada REAL na corretora de ensaio, **completude = (calculadas + pendentes com motivo) ÷ esperadas =
100 %**, e a mutação "um item some" deixa a conferência **VERMELHA**. **131-B:** no celular, Aplicativos → Renovação → Renovações mostra a
madrugada; a apresentação passa no juiz de design (DS-001 §5); "Enviar pelo WhatsApp" abre o WhatsApp DO COMERCIAL com a mensagem pronta,
o card vai a "enviada" e o evento fica gravado. Nada sai sozinho.

---

## 1. O contrato

**131-A muda:** um trabalho diário por corretora sobre o Work OS existente (tick + `work_runs` com chave `company:dia` + espera durável
da 129-A) · 4 tabelas novas (expand-only, §4.2) · desconhecido → `RamoIndisponivel` · o recomendado "ano anterior" e as 3 opções ·
`antecedencia_dias` **15 → 10** · a política de sessão da madrugada · teto de sessões, prioridade 7 · substituto e desvio · CPF barrado.
**131-A não pode mudar:** QCM e cotação do chat (prioridade 5, nunca Prosseguir) · `dono_da_apolice` e a regra do dono (D-131-0-03/31) · o
leitor da 130-B (só consumido) · o motor nunca cai CALADO no Agger da corretora · nada enviado a cliente · nenhum scheduler, executor ou
ledger paralelo (CLAUDE.md §5) · `comercial/metricas/renovacao.py` (BI) segue leitor.

**131-B muda:** a CASCA genérica dos aplicativos (só a Renovação ganha conteúdo) · "Aplicativos" no menu · slug `renovacao` (📊
`renovacao-maxima` instalada em 0, I2 F4) e catálogo de Cotação/QCM · a aba Renovações · Configurar no lugar de Serviços · Meu perfil ·
Equipe · a variante de renovação da "carteira" e a sua ordem · "Quero renovar" ao dono · o `wa.me` (arquivos no §5.2).
**131-B não pode mudar:** o modal da Cobrança (`PainelDeRotinas.tsx`, piloto) · o backend de Serviços (📊 0 linhas gravadas, I2 F5) · a
página do canal QCM (D-130A1-01/08) · código e banco seguem `auxiliary` · o produto não envia: o `wa.me` abre no aparelho de quem clica.

---

## 2. O FIO

**131-A**
```
services/intelligence/tick.py → Work Run "renovacao.preparar" (chave company:dia) → fonte_infocap.renovacoes_cruas(hoje, hoje+antecedência+margem)
  [CPF/CNPJ inválido barrado antes] → upsert renovacoes(company_id, sistema, codfil, nosnum, fimvig) [endosso: item novo, o velho "substituida"]
→ por item, EM SÉRIE: dono.dono_da_apolice → a ficha (policy_document_evidence_service) → pedido.de_apolice(…, ficha=, config=)
→ pronta | pendente(ramo_nao_cotado · falta_dado · sem_conexao · sem_pdf)
→ 02:00 "renovacao.calcular": porta.calcular(servico='renovacao', prioridade=7, politica_de_sessao, renovacao_id) se fimvig−antecedência ≤ hoje
→ qual_agger.decidir (dono · substituto · corretora+aviso) → motor._reservar (teto) → agger_sessao (Prosseguir 1×/conta/noite) → calcularV2 ×3
→ renovacoes: calculada | falhou(motivo) | aguardando_agger
→ 05:30 "renovacao.conferir" (OUTRO módulo): renovacoes_cruas DE NOVO → esperadas × itens → renovacao_dias; falta = criado + "esquecida" + VERMELHO
→ 06:15 desvio → 06:45 "renovacao.avisar" pelo canal de aviso que JÁ existe (A8)
```
Teste do fio (1ª entrega, VERMELHO): `test_spec131a_o_fio.py`, motor REAL, dublê só na borda.

**131-B**
```
/dashboard/auxiliares → card Renovação → auxiliares/renovacao?aba=renovacoes → AbaRenovacoes (QuadroOuLista) → /api/renovacoes →
backend api/renovacoes.py (company_id; "minhas" × "todas") → renovacoes + eventos → ?item=<id> → "Ver apresentação":
proposta.publicar_renovacao → render_proposta(situacao="renovacao") → /r/<token> (share.viewed) → "Quero renovar" → wa.me do DONO
(share.clicked) · "Enviar pelo WhatsApp": telefone do cliente buscado NA HORA → mensagem_de_renovacao → wa.me no aparelho de quem
clicou → evento aberto_para_envio → estado enviada
```
Teste do fio: `test_spec131b_o_fio.py` (de `calculada` a `aberto_para_envio`, HTML SERVIDO) + os gates do CLAUDE.md §9.1.

---

## 3. BLOCO 0 — o que mudaria o DESENHO (medir antes da 1ª linha; do "ficou por medir" de I1 §8 e I3 §6)

| # | premissa | comando | se der errado |
|---|---|---|---|
| A1 | **o que o "Prosseguir" envia** (nunca clicado, I1 §5.2) | Playwright de rascunho: o `cotador@` em DOIS contextos; no 2º, Prosseguir; `page.on("request")`; quem caiu? | derruba além do mesmo login → a exceção NÃO liga (Cancelar-esperar + desvio) |
| A2 | **pico diário por dono** | `renovacoes_cruas(hoje, hoje+90)` na corretora de ensaio, por `fimvig` e dono | pico > 💭 3× a média → início 01:30 / teto maior |
| A3 | **3 opções simultâneas na mesma sessão** (📊 2: 16/16) | canário 1 AUTO + 1 RE com 3 opções | falha → disparo e leitura em série |
| A4 | **2 logins da mesma corretora juntos** (E7 PARCIAL) | `cotador@` + conta `teste`, mesmo minuto | um derruba o outro → teto 1 por corretora |
| A5 | **`per_c` preenchido** e de quem é o % | `/documento` em ~20 renovações (contagem) | < 50 % ou % do produtor → D-131-16 vira pendência |
| A6 | **`MULTICALCULO_MOTOR_LIGADO` em produção** | `/health` do `portal-worker` ou 🧑 `printenv` no console | desligado → canário com o motor local; ligar é do Founder |
| A7 | **o comercial vê o negócio do `cotador@`?** (📊 o robô vê 0 das pessoas) | conta `teste` lista negócios após cálculo do `cotador@` | não vê → o aviso do desvio diz "no Agger da corretora" por extenso |
| A8 | **onde o tick registra workflow; o canal de aviso in-app** | `Grep "workflow_key\|idempotency_key"` em `services/intelligence/tick.py` · `Grep "notification\|inbox" backend/app/services` | sem canal → painel + `daily_briefing`; nunca publisher novo |
| A9 | **ficha → códigos do Agger (AUTO)** nas 📊 6/6 AUTO | ficha das 6 → preset `anterior` (I3 §6.3) | campo falta → para CIMA + "não conferido" |
| A10 | **3ª versão de RE** no mesmo negócio | canário 1 condomínio | recusa → RE com 2 opções (a + c) |
| A11 | **memória por contexto Chromium** | `docker stats` durante A4 | dimensiona o teto (💭 6/processo, 3/corretora) |
| B1 | **`wa.me` com 500–700 caracteres** (Bird diz 140; o produto usa 500, `proposta_html.py:1152`) | 3 links (140/500/700) em Android, iOS, Web, Desktop | corta → texto curto + "Copiar a mensagem" |
| B2 | **"cliente desde"**: `/cliente_ligacoes` × cadeia `nosnum_ren` | ~10 renovações, sem PII | incoerente/caro → a frase não aparece |
| B3 | **`?aba=` monta** ao lado de `auxiliares/checklist-6h/` | `test:rotas-montam` + `next start` + 1 requisição | não monta → abas por estado no cliente |
| B4 | **link direto para um cálculo no Agger** | uma tela, sem escrita | não há → "Abrir no Agger" abre a lista |
| B5 | **telefone do cliente** | `/renovacoes.fone` (📊 71/99) × `/cliente.telefones` | falta → só "Copiar a mensagem" |
| B6 | **0 config de Serviços e 0 `renovacao-maxima`** ainda | `select count(*)` em `multicalculo_config` e em `tenant_auxiliaries` por slug | > 0 → migrar antes do redirect |
| B7 | **telefone verificado do comercial** (V37) | contagem em `company_members` | 0 → à corretora (📊 `contact.whatsapp` 0/3 → T-125) |

---

## 4. O desenho

### 4.1 131-A — a madrugada (I1 §2.5; 88 · 86)
- **Horários** (Brasília, por corretora): 00:30 · 02:00 · 05:30 · 06:15 · 06:45; **7 dias por semana**. 💭 o pior caso do login mais carregado
  é 3 h 29 (I1 §2.4): 5 h cobrem isso + 1 retentativa.
- **Fila inteira de uma vez**, ordem (ramo, vencimento); o motor serializa por LOGIN e paraleliza ENTRE logins; **teto de sessões** (💭 6 por
  processo, 3 por corretora; hoje 📊 não existe); **prioridade 7** (cotação segue 5, `porta.py:63,73`; ordem `prioridade, criado_em`,
  `motor.py:514`); **sessão da pessoa mantida** entre os pedidos DELA, logout no fim da fila dela e sempre até 06:30 (hoje por pedido,
  `motor.py:742-750`).
- **"Hoje" = `fimvig − antecedência ≤ hoje`**: o que falhou ontem entra hoje.

### 4.2 131-A — a tabela e a máquina (I1 §6; 86)
```
renovacoes(id, company_id, sistema, codfil, nosnum, fimvig UNIQUE(company_id,sistema,codfil,nosnum,fimvig), ramo_sigla, ramo_agger,
  seguradora_atual, premio_atual, cliente_nome, documento_mascarado, documento_hmac, dono_user_id, dono_motivo, responsavel_user_id,
  estado, motivo, pedido_id, conta_agger_id, conta_motivo, proposta_ref, calcular_em, criado_em, atualizado_em, versao)   ⛔ telefone/CPF em claro
renovacao_eventos(id, company_id, renovacao_id, de, para, por, motivo, dados, criado_em)
renovacao_dias(company_id, dia, estado, esperadas, calculadas, pendentes, falharam, faltaram, completude_pct, detalhes)  PK(company_id, dia)
membro_ausencias(id, company_id, user_id, substituto_user_id, de, ate)  FK (user_id, company_id) → company_members ON DELETE CASCADE
LIGADOS:    listada → pronta | pendente → calculando → calculada | falhou | aguardando_agger → apresentada → enviada · substituida
RESERVADOS: vista · em_negociacao · recalculo · aceita · emissao_pendente · emitida · registrada · recusada · perdida
CHECK:      estado ∈ todos · estado ∈ (pendente, falhou, perdida) ⇒ motivo NOT NULL
```
Guarda: nenhum escritor grava estado reservado. RLS + filtro `company_id` no repositório + teste com DUAS corretoras (CLAUDE.md §7).
Migration `20261013_01_spec131a_renovacoes.sql`, APPLY/VERIFY/ROLLBACK antes.

### 4.3 131-A — o pedido certo (I1 §1, §4; I3 §1)
- `_ramo_do_agger` (`pedido.py:687`): `None` → `RamoIndisponivel` (95); o item vira `pendente(ramo_nao_cotado)` com "renove
  manualmente" e conta na completude (92). 📊 numa corretora real, 30 dias: 68 de 99 cotáveis (I1 §4).
- **As 3 opções** (`servicos.renovacao.opcoes`, 1–3, padrão 3): **(a) "Sua renovação"** = coberturas do ano anterior IGUAIS OU MELHORES
  (AUTO: preset novo `anterior` da ficha, sempre para cima; RE: `coberturas_re(extras=ficha)` + Básica reajustada — P-130B-12) · **(b)
  franquia reduzida** (AUTO `tipoFranquia 1`; já reduzida → `_repete` cede o lugar; RE sem toggle medido → a "típica do ramo") · **(c) o
  que os clientes pedem** = completa+ (pequenos reparos; D-MC-69; ESTRATEGIA-COMERCIAL §1.4). ⛔ nunca econômica nem mínima (guarda).
- **Comissão** = `per_c` anterior + `comissao_a_mais_pp` (1–2; 📊 hoje só texto, `manual_de_negociacao.py:201`) na (a); nas que ignoram
  (`config.py:85`), o desconto. **Só se A5 provar.**
- **CPF/CNPJ** com dígito inválido barrado antes da InfoCap, no ponto único (P-1310-02: 📊 `00000000000` devolve um cliente REAL).

### 4.4 131-A — o Agger de quem e a madrugada (I1 §5; Founder 12/10)
- **Renovação:** o Agger do DONO · dono ausente → o cálculo segue no Agger dele, o aviso vai ao **substituto** · sem dono/conta → o da
  corretora **com aviso nomeado** · senha recusada → recusa. Chat e QCM: como hoje (`qual_agger.py:175-201`).
- **A madrugada (revê D-131-0-05):** "Prosseguir" sobre sessão aberta SÓ se **todas**: janela da corretora (💭 01:00–06:30) · `servico=
  'renovacao'` · conta `uso='membro'` da pessoa dona · **1× por conta por noite** (evento `prosseguiu_sessao` em `multicalculo_eventos`,
  conferido por SELECT) · **A1 medido**. A pessoa voltou → não prossegue de novo: Cancelar, espera de 20–30 min, tenta até 06:15;
  depois, o Agger da corretora com aviso.
- A exceção da guarda (`agger_guarda.py:47,183`) é um sinal no `EstadoDaGuarda` que só a política da madrugada liga. A **T-141** muda de texto.

### 4.5 131-A — conferência e aviso (I1 §3; 92)
`conferencia_da_renovacao.py` **não importa** o montador da lista (guarda por AST) e relê `/renovacoes`. Toda esperada num estado terminal
do dia; falta → criada + `esquecida_pela_preparacao` + dia VERMELHO; InfoCap fora → `sem_conexao` + alerta ao admin (nunca "0").
Gravado por dia: completude (meta 100 %) e calculadas ÷ cotáveis. Aviso 06:45: "N prontas no seu Agger · M pendentes (porquê) · K falharam".

### 4.6 131-B — o padrão de aplicativo (I2 §4 opção A; 88)
- **Card:** ícone LINEAR (a coluna `icon`, que `catalog.ts:258` hoje não lê), nome, frase, estado; sem emoji (DS-001 §14); estrela só com
  avaliação real; prova por número medido, ou nada.
- **Página** (`[slug]`, rota ÚNICA — erro nº 3 da ONTOLOGIA), abas por `?aba=`: **Início** (o que é → o que a corretora ganha → **Como
  começar**, passo a passo das conexões exigidas e do Meu perfil, cada passo com estado e link → funciona com [conexões, ícone e nome
  humano] → dúvidas) · **Configurar** · **o trabalho feito** ("Renovações") · **Dúvidas**. Saem "De onde ele tira a informação" e os
  slugs crus (`AuxiliarDetalheClient.tsx:162-195`); o Histórico lê a fonte real (📊 hoje mente, I2 F7).
- **Configurar** (no lugar de modal, DS-001 §8.6): **O que fazer** · **Quando** (padrão 10 dias; "pronto antes das 7h") · **Com qual conta**
  ("do responsável" (padrão) ou "da corretora"; o decidido vira "✓ conectado · mudar") · **Avançado** recolhido (exceções por ramo/valor,
  reajuste, 1–3 opções, seguradoras "da corretora" ou "própria", de LISTA). Tooltips no lugar dos `text-[11px]`.
- Os outros ganham a casca com o conteúdo que têm; Cotação e QCM, Início + Configurar.

### 4.7 131-B — a aba Renovações (I2 §6)
- **QuadroOuLista** extraído de `AttendanceQueueClient.tsx` (alternância salva `:96,:233`, `snap` `:310`, 50 por coluna `:101`, **sem
  arrastar** `:29-30`), usado pelas duas telas; o vocabulário de `caso-visual.tsx`.
- **Colunas:** Vai calcular · Calculada · Enviada · Em negociação · Fechada · Emitida e registrada · Perdida; as quatro últimas ESCONDIDAS até
  um estado alcançá-las. **"Precisa de você" é SELO** (ramo não cotado, Agger recusou, sem comercial, falhou).
- **Lista, filtros, atalhos, detalhe e celular:** exatamente I2 §6 (colunas, "minhas"/"todas", atalhos-filtro no topo, a linha que expande
  nos 3 cálculos, cartões com 1 botão "Enviar" e barra fixa [Enviar pelo WhatsApp] [Ver apresentação]).

### 4.8 131-B — Meu perfil, Equipe, Ausência (I2 §5)
**Meu perfil** = Dados · **Minhas conexões** (o MEU Agger; a senha nunca volta) · **Ausência** (período + OUTRA pessoa, de lista) · Segurança ·
Aparência; "Uso e custos" sai do perfil. "Aggers da equipe" sai do modal do Agger da corretora; em **Equipe**, a coluna SITUAÇÃO e "pedir
para conectar", sem login de outra pessoa (revê D-131-0-06). `personalizacao/servicos` → `auxiliares/renovacao?aba=configurar`; sai `lib/mock/tenant-modules.ts:81`.

### 4.9 131-B — a página de RENOVAÇÃO (I3 §2; 88)
UM template, a "carteira" da 130-A (`render_proposta`), variante `situacao="renovacao"`. **Obrigatórias:** hero com o vencimento (nunca "a
melhor das N") · **o seu seguro hoje × a renovação** (o que mudou em R$ e %, o reajuste da Básica por extenso) · os 3 cartões com "por que
recomendamos" · "Mostrar só o que muda" · **a relação** ("N anos juntos" SÓ com prova, B2) + "quem cuida de você" = o **comercial dono** ·
sinistro · FAQ de renovação · dock **"Quero renovar" / "Tirar uma dúvida"** → o dono (senão a corretora; sem nenhum, a recusa de hoje).
**Recolhida:** "todas as seguradoras que cotamos". **Nunca:** duelo entre corretoras, "O que é o QCM?". **A ordem** (`comparacao.py:925-1003`):
na renovação a (a) em 1º — 📊 `:938` hoje põe "a menor completa SEMPRE em 1º" e a econômica como "Mais em conta" (contradiz o Founder, I3 §0).
Guarda no HTML SERVIDO. Entrega: `/r/` rastreado + "Salvar PDF" = imprimir.

### 4.10 131-B — o envio (I3 §3; 90)
"Enviar pelo WhatsApp" abre `https://wa.me/<cliente>?text=<mensagem + link /r/>` **no aparelho de quem clica**; par obrigatório: "Copiar a
mensagem". Grava `aberto_para_envio` (quem, versão) → "enviada"; `share.viewed/clicked` na linha do tempo. Telefone buscado na hora, nunca
guardado nem logado. `calcular_entregar` automático: pronto e DESLIGADO. Pareamento por pessoa = B2 com a 135.

---

## 5. Unidades e FATIAS (cada arquivo, UM dono; paralelo só com arquivos DISJUNTOS)

### 5.1 131-A — F1 ‖ F2 ‖ F3 → F4 (costura)
| fatia | entrega | arquivos (só estes; `backend/` implícito) |
|---|---|---|
| **F1 · lista, tabela, conferência** | fio vermelho · migration · máquina · os 4 passos no tick | `supabase/migrations/20261013_01_spec131a_renovacoes.sql` · `app/services/multicalculo/renovacao.py` (NOVO) · `…/multicalculo/madrugada.py` (NOVO) · `…/multicalculo/conferencia_da_renovacao.py` (NOVO) · `app/services/intelligence/tick.py` · `tests/test_spec131a_o_fio.py` · `tests/test_spec131a_a_lista_e_a_conferencia.py` |
| **F2 · o pedido e a consulta certos** | ramo · `anterior` · `extras` · opções · comissão · config · CPF | `app/services/multicalculo/pedido.py` · `portal_worker/multicalculo/presets.py` · `app/services/multicalculo/config.py` · `app/comercial/fonte_infocap.py` (+ o ponto único da consulta por CPF que o BLOCO 0 apontar) · `tests/test_spec131a_o_pedido_da_renovacao.py` |
| **F3 · a madrugada no Agger** | sessão · guarda · teto · prioridade · substituto · desvio | `portal_worker/multicalculo/motor.py` · `…/agger_sessao.py` · `…/agger_guarda.py` · `…/robos.py` · `app/services/multicalculo/qual_agger.py` · `…/porta.py` · `tests/test_spec131a_a_madrugada_no_agger.py` |
| **F4 · costura + canário** | fio VERDE · 7 mutações · canário | consertos nos arquivos acima (F4 é o dono depois que F1–F3 fecham) · `scripts/canario_madrugada_renovacao.py` |

**Contrato (fixado antes do paralelo):**
```python
porta.calcular(..., servico, dono_user_id=None, vence_em_dias=None, prioridade: int | None = None,   # None = 5; renovação passa 7
               politica_de_sessao: str | None = None, renovacao_id: str | None = None)             # "madrugada" só madrugada.py, na janela
qual_agger.decidir(..., servico, dono_user_id, substituto_user_id=None, forcar_corretora_motivo: str | None = None) -> Decisao
pedido.de_apolice(apolice, perfil=None, *, ficha=None, config=None, exigir_completo=...)  # assinatura igual; opcoes da config
RamoIndisponivel(motivo="ramo_nao_cotado" | "ramo_desconhecido")
config: renovacao.antecedencia_dias=10 · renovacao.janela={preparar 00:30, calcular 02:00, conferir 05:30, desvio 06:15, avisar 06:45,
        prosseguir_de 01:00, prosseguir_ate 06:30} · servicos.renovacao.opcoes=["anterior","franquia_reduzida","completa_mais"]
```

### 5.2 131-B — G1 ‖ G2 ‖ G3 ‖ G4 → G5 (costura + design)
| fatia | entrega | arquivos (só estes) |
|---|---|---|
| **G1 · a casca** | card, abas, Como começar, Histórico real, menu, catálogo | `app/dashboard/auxiliares/AuxiliaresClient.tsx` · `…/[slug]/page.tsx` · `…/[slug]/AuxiliarDetalheClient.tsx` · `lib/auxiliaries/catalog.ts` · `lib/navigation.ts` · `backend/supabase/migrations/20261014_01_spec131b_catalogo.sql` · `docs/canon/GLOSSARIO.md` (1 linha) |
| **G2 · a aba Renovações** | quadro/lista, filtros, detalhe, celular, API | `components/aplicativos/QuadroOuLista.tsx` (NOVO) · `app/dashboard/atendimentos/fila/AttendanceQueueClient.tsx` · `components/aplicativos/renovacao/*` (NOVOS) · `app/api/renovacoes/**` · `backend/app/api/renovacoes.py` (NOVO) · `backend/tests/test_spec131b_api_renovacoes.py` |
| **G3 · Configurar, Meu perfil, Equipe** | Configurar · redirect · conexões · Ausência · Situação | `components/aplicativos/configurar/*` (NOVOS) · `app/dashboard/personalizacao/servicos/**` · `lib/mock/tenant-modules.ts` · `app/dashboard/configuracoes/**` · `components/perfil/*` (NOVOS) · `components/vault/AggersDaEquipe.tsx` · `components/vault/AggerDaCorretoraModal.tsx` · `app/dashboard/personalizacao/equipe/**` · a API de ausência (o arquivo de membros que o BLOCO 0 apontar) |
| **G4 · a página e a mensagem** | variante, ordem, relação com prova, dono, `wa.me` | `backend/app/services/artifacts/proposta_html.py` · `backend/app/services/multicalculo/comparacao.py` · `…/proposta.py` · `…/mensagem.py` · `backend/tests/test_spec131b_a_pagina_de_renovacao.py` |
| **G5 · costura + design** | fio VERDE · rotas · `next start` · design · mutações | consertos de costura · `backend/tests/test_spec131b_o_fio.py` |

**Contrato:** G1 exporta `ABAS_DO_APLICATIVO: Record<slug, {id, rotulo, componente}[]>` em `catalog.ts` e carrega
`components/aplicativos/<slug>/Aba<Nome>.tsx` por import dinâmico — G2/G3 escrevem esses componentes, G1 nunca. G4 exporta
`mensagem_de_renovacao(renovacao, proposta, *, pessoa) -> {texto, texto_curto, link}` e `publicar_renovacao(company_id, renovacao_id, *,
pessoa) -> {token, url}`, chamados por `api/renovacoes.py` (G2).

---

## 6. A régua e a prova

**131-A** · **Canário de UMA madrugada real** na corretora de ensaio (InfoCap e Agger dela, ≤ 5 itens): completude 100 % · ≥ 1 cotável
calculada · ≥ 1 não cotado como pendência · 0 `calculando` sem batida às 05:30 · 0 linha em outra corretora. **Mutações (VERMELHAS):**
(1) um item some · (2) a conferência lê a lista congelada · (3) desconhecido → AUTO · (4) Prosseguir fora da janela ou em conta `global` ·
(5) prioridade 5 · (6) estado reservado gravado · (7) econômica/mínima. **Isolamento:** duas corretoras na mesma madrugada. **Lente do
dado:** a completude reconferida por um 3º caminho (SELECT × nova leitura de `/renovacoes`).

**131-B** · **Juiz de design** abre a página SERVIDA (`/r/`) e a do aplicativo, celular e notebook, item a item contra o **DS-001 §5** e o §10.
**Mutações:** (1) "menor completa em 1º" volta na renovação (guarda no HTML servido) · (2) "N anos juntos" sem prova · (3) "Quero renovar"
à corretora com dono verificado · (4) card arrastável muda o banco · (5) telefone do cliente num log. **Gates de `app/`** (§9.1).

**Verba** (ESTADO §3, saldo 💭 3,83): 131-A 💭 ≤ US$ 1,00 (fichas não lidas, 💭 ~316 × 0,002) · 131-B 💭 ≤ US$ 0,30.

---

## 7. Nível e risco

| | 131-A | 131-B |
|---|---|---|
| ALCANCE · REVERSIB. · FREQ. | corretora 2 · saiu do prédio 3 (`calcularV2`; **entra na conta de uma PESSOA**) · todo dia 1–2 → **RISCO 6–7** | segurado 3 (a página) · 2 · semanal 1 → **RISCO 6** |
| SUPERFÍCIE · PISO §3.2 | 2 · migration de estrutura, sessão de terceiro, `company_id` | 2 · migration que altera DADO, `company_id`, `app/` |
| NÍVEL | **CRÍTICO** · builders Opus 5.5 xhigh · juiz ‖ red team Opus 5.5 · lente do dado | **CRÍTICO** · idem · juiz de design |
| ENVIA mensagem? | não | não pelo produto: abre o `wa.me` do PRÓPRIO comercial |
| FAIXA | 💭 4–6 h | 💭 4–6 h |

---

## 8. Decisões — **F** = o Founder decidiu em 12/10 · **G** = o gerente, pela nota dos laudos

| # | decisão | nota | contra | de |
|---|---|---|---|---|
| D-131-01 | Antecedência padrão **10 dias**, por corretora (`config.py:57` 15 → 10) | F | 15 | F |
| D-131-02 | **Tudo calculado antes das 7h** | F | — | F |
| D-131-03 | De madrugada, entra no Agger do comercial **mesmo com sessão aberta**, com as travas do §4.4. **Revê D-131-0-05** | 88 | nunca 40 · sempre 30 | F · G |
| D-131-04 | Qual Agger: renovação = dono · chat = usuário · admin sem Agger = corretora · QCM = corretora | F | — | F |
| D-131-05 | 3 cálculos: recomendado (= ano anterior) · franquia reduzida · o que os clientes pedem; **nunca** econômica/mínima (revê D-MC-69 na renovação) | 88·85·82 | menor completa 55 | F |
| D-131-06 | **Serviços sai de Personalização** para dentro de cada aplicativo (revê o lugar da D-131-0-07) | 88 | 55 | F |
| D-131-07 | Conexões do usuário no **Meu perfil**; o aplicativo escolhe "do usuário ou da corretora"; cada um só o SEU Agger; admin vê a situação. **Revê D-131-0-06** | 86 | admin cadastra todos 55 | F · G |
| D-131-08 | Substituto = **OUTRA pessoa**; cálculo no Agger do dono, aviso ao substituto | 82 | Agger do substituto 65 · login novo 15 | F · G |
| D-131-09 | **131-A + 131-B, mesmo chat novo, em série** | 90 | uma SPEC 60 · chat atual 10 | G |
| D-131-10 | Horários 00:30 · 02:00 · 05:30 · 06:15 · 06:45, 7 dias/semana | 88 | 03:00 78 · 04:00 55 | G |
| D-131-11 | Fila inteira, serial por login, teto de sessões, prioridade 7, sessão mantida (§4.1) | 86 | lotes de 5 55 | G |
| D-131-12 | Completude: lista congelada + conferência INDEPENDENTE + dia VERMELHO | 92 | Work Runs filhos 70 · "juiz" modelo 20 | G |
| D-131-13 | Desconhecido → `RamoIndisponivel`, nunca AUTO; não cotado = pendência visível | 95·92 | manter AUTO 40 | G |
| D-131-14 | `renovacoes` com a máquina INTEIRA + eventos, ligada até "enviada" | 86 | sem eventos 60 | G |
| D-131-15 | Recomendado = ano anterior pela ficha (P-130B-11/12), sempre para cima | 88 | padrão do produto 60 | G |
| D-131-16 | Comissão anterior + 1–2 pp (desconto nas que ignoram) — **só se A5 provar** | 80 | não mexer 60 | G |
| D-131-17 | CPF/CNPJ inválido barrado antes da InfoCap, em todo chamador (P-1310-02) | 92 | só na renovação 55 | G |
| D-131-18 | **"Aplicativo" só na TELA** (+1 linha no GLOSSARIO) | 84 | App 62 · Auxiliar 55 · em tudo 25 | G |
| D-131-19 | Padrão novo, conteúdo completo SÓ na Renovação; modal da Cobrança intocado | 88 | loja inteira agora 50 | G |
| D-131-20 | QuadroOuLista extraído · selo "precisa de você" · `?aba=` · slug `renovacao` | 82·84·85·80 | copiar 40 · subrota 65 | G |
| D-131-21 | Cotação e QCM com linha de catálogo, sem rotina | 80 | 55 | G |
| D-131-22 | Página de renovação = variante da "carteira", ordem corrigida | 88 | temas 72 · 3 templates 45 | G |
| D-131-23 | Relação com o cliente só com prova (CDC art. 37) | 92 | inferir 30 | G |
| D-131-24 | Envio = `wa.me` do comercial + "Copiar"; "Quero renovar" ao dono; automático DESLIGADO | 90·80·62 | parear já 40 | G |
| D-131-25 | Entrega = `/r/` rastreado + "Salvar PDF" = imprimir | 90·70 | PDF no servidor 40 | G |
| D-131-26 | Avaliações fictícias: **NÃO**; números reais medidos | 85 | 10 | G |
| D-131-27 | 1, 2 ou 3 opções, configurável (padrão 3) | 86 | fixo 60 | G |
| D-131-28 | Depois, com SPEC própria: o §11 | 80 | tudo agora 50 | G |

---

## 9. Riscos

- o Prosseguir derruba mais que o mesmo login → A1 antes; 1×/conta/noite; mutação (4) · a madrugada transborda → prioridade 7, teto, desvio
- N logins na MESMA credencial da seguradora (📊 `compartilhada` 15/15) → teto 3 por corretora (A4, A11)
- InfoCap instável (📊 502 em janela grande, `fonte_infocap.py:639`) → a conferência relê; `sem_conexao` é alerta, nunca "0"
- 📊 0 vínculos produtor↔pessoa → tudo no Agger da corretora com aviso até T-140/T-141 · licença do Agger com data 📊 13/10/2026 → T-136; `falhou(licenca)`
- extrair o quadro quebra a fila → G2 dono dos dois · dado pessoal → telefone na hora (mutação 5)

---

## 10. O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS

1. **https://int.ezlynx.com/solutions/renewals-client-retention** · faz: resume as mudanças de prêmio entre a apólice atual e a renovação,
   lado a lado · modelamos: **"o seu seguro hoje × a renovação"** · rejeitamos: o portal do agente (o painel é o nosso) · juiz: abre a página
   servida e acha o bloco com R$ e %.
2. **https://www.nngroup.com/articles/comparison-tables/** · faz: comparação até 5 itens, atributos consistentes, cabeçalho preso ·
   modelamos: 3 cartões + "Mostrar só o que muda" · rejeitamos: > 5 colunas · juiz: conta colunas e rola no celular.
3. **https://bird.com/explained/whatsapp/what-is-a-whatsapp-click-to-chat-link** · faz: `wa.me/<número>?text=`; afirma 140 caracteres ·
   modelamos: o botão no aparelho do comercial · rejeitamos: crer no limite sem medir (B1) · juiz: abre o link do canário.
4. **https://linear.app/docs/board-layout** · faz: lista ↔ quadro, colunas por estado, esconder coluna · modelamos: QuadroOuLista e as
   colunas escondidas · rejeitamos: arrastar (estágio derivado) · juiz: arrasta um card e confere que o banco não muda.
5. **https://knowledge.hubspot.com/object-settings/set-up-and-customize-pipelines** · faz: ganho/perdido e campo exigido no estágio ·
   modelamos: "perdida" exige motivo (CHECK) e a máquina inteira desde já · rejeitamos: valor ponderado · juiz: grava `perdida` sem motivo → recusa.
6. **https://apps.shopify.com/shopify-forms** · faz: página de app B2B (cabeçalho → descrição → "funciona com" → avaliações → suporte) ·
   modelamos: a ORDEM da aba Início · rejeitamos: "apps parecidos" e preço (SPEC-062) · juiz: compara a ordem das seções.
7. **https://developer.apple.com/app-store/review/guidelines/** (§3, *"fake feedback"*) · faz: expulsa quem inventa avaliação · modelamos:
   estrela só real, prova por número medido · rejeitamos: as 30 fictícias · juiz: nenhum card com estrela sem dado.

**Interna (vence):** DS-001 §5/§8.6/§8.7/§14 e `docs/intake/TELAS AUXILIARES/` (fora do git).

---

## 11. O QUE SAIU (com o porquê)

- **"A loja de aplicativos"** (depois da 132): galeria com imagens, os outros aplicativos, o modal da Cobrança, P-16 e **EXTRA-001.9** (mesmas
  rotas). A 131 já é CRÍTICA e a Cobrança está em piloto (I2 §4, 88 × 50).
- **WhatsApp PAREADO + envio automático + negociação** = **131-0 B2 com a 135** (o PEDIDO diz B1; a B1 é PEDIR, I3 §3.1): conversas pessoais, bloqueio, aceite.
- **"Emissão e registro"** (D-1311-06): a InfoCap não tem homologação (T-150; D-1311-04).
- **Vida e moto** (80, I1 §4): SPEC por ramo depois da 132; fora do Agger (náutico, RC prof., garantia): portal, se o volume pedir (💭 60).
- **3 templates** (45) · **PDF no servidor** (40, D-130A-07) · **"vou entrar no seu Agger" na cotação do chat** (82): da 132.

---

## 12. AS RESPOSTAS AO FOUNDER

| pergunta (PEDIDO) | resposta | nota | quando |
|---|---|---|---|
| A · "Auxiliar" → "Aplicativo"? | **"Aplicativo"**, só na tela. App 62 · Auxiliar 55 · Serviço 30 (confunde com guincho) · Assistente 30 ("agente de IA") · no código 25 | 84 | 131-B |
| A · 30 avaliações fictícias? | **Não** (Apple expulsa; CDC art. 37; mata a confiança nas reais). No lugar: números reais medidos | 85 × 10 | 131-B |
| A · galeria, ícones premium | ícones lineares em todos os cards já; galeria com imagens na "A loja" | 88 | 131-B / loja |
| A · página do aplicativo (nota 50) | abas Início · Configurar · o trabalho feito · Dúvidas; "Como começar" passo a passo; conexões com nome de gente | 88 | 131-B |
| A · modal confuso | vira a aba Configurar (O que fazer · Quando · Com qual conta + Avançado); o decidido vira "✓ conectado · mudar" | 85 | 131-B |
| A · Serviços no lugar errado | vai para dentro de Renovação, Cotação e QCM; o endereço antigo redireciona | 88 | 131-B |
| A · "o trabalho feito" + Kanban + celular | lista + quadro (o da fila de atendimentos), filtros, atalhos, botão "Enviar" no celular; o agente move os cards | 82 | 131-B |
| A · visual agora ou depois? | o PADRÃO agora, na Renovação; os outros na "A loja" | 88 | 131-B / loja |
| B1 · quando calcular | 10 dias antes, mudável por corretora | F | 131-A |
| B2 · 7h, horário, lotes | começa 02:00 (lista 00:30, conferência 05:30, aviso 06:45), todo dia; tudo na fila, um por vez por login, vários logins juntos, com teto | 88 · 86 | 131-A |
| B3 · nunca esquecer | às 05:30 um conferente SEPARADO relê a InfoCap; faltou uma → dia vermelho e ela é criada; meta 100 % | 92 | 131-A |
| B3/B4 · sem comercial; de quem é | o dono no CORP (📊 99/99, 217/217), no Agger dele; sem dono → Agger da corretora + aviso ao admin | 96 · 85 | 131-A |
| B5 · Agger "conectado" de madrugada | entra mesmo assim, só de madrugada, só renovação, só no Agger da própria pessoa, 1× por noite, depois de medir o botão; se ela voltar, espera até 06:15 e usa o da corretora avisando; o aceite (T-141) muda | 88 | 131-A |
| B5 · chat, admin, QCM | chat: de quem pediu · admin sem Agger: corretora · QCM: corretora | F | 132 / já |
| B6 · ramos que não cotamos | hoje viraria CARRO (defeito, consertado); viram "renove manualmente" visível; vida e moto, SPEC própria | 95·92·80 | 131-A / depois |
| B7 · Agger = cálculo, AutoBrokers = apresentação | confirmado | — | — |
| B8 · página, 3 cálculos, 3 templates | uma página ótima (a "carteira", 📊 91) para quem já é cliente: "o seu seguro hoje × a renovação", relação só com prova; igual ao ano passado · franquia reduzida · o que os clientes pedem; nunca o mínimo; 3 templates não (45) | 88 | 131-A/B |
| B8 · link ou PDF | link rastreado + "Salvar PDF" pelo navegador | 90 · 70 | 131-B |
| B9 · enviar | o comercial toca "Enviar pelo WhatsApp" e abre o WhatsApp DELE pronto; "Quero renovar" vai a ele; automático pronto e desligado | 90·80·62 | 131-B |
| B9 · WhatsApp pareado | com a negociação (135): ler o WhatsApp pessoal pede aceite e arrisca bloqueio | 40 agora | 135 |
| B10 · negociar, fechar, emitir | a 131 deixa pronto: estados, link rastreado, pedido no mesmo Agger, "o que o cliente respondeu" em 1 toque; negociar = 135; emitir = SPEC própria | 85 | depois |
| C · usuário × corretora; Agger por usuário | da corretora em Personalização; da pessoa em Meu perfil → Minhas conexões, cada um o seu; o admin vê quem falta em Equipe | 86 | 131-B |
| C · férias | Meu perfil → Ausência: OUTRA pessoa; o cálculo segue no Agger do dono, o aviso vai ao substituto | 82 | 131-A/B |

---

## 13. PROMPT DE ABERTURA (cole num chat NOVO do Claude Code, modelo Opus 5.5)

```
Você é o GERENTE das SPECs 131-A ("A madrugada da renovação") e 131-B ("O aplicativo de Renovação") do AutoBrokers Intelligence OS.
Responda em pt-BR, em linguagem de gente. Árvore: C:\Users\amand\Projetos\AUTOBROKERS RESULTA\AutoBrokers-FIX. Python de dentro de
backend/, PYTHONIOENCODING=utf-8. Execute a 131-A INTEIRA (card → push) e DEPOIS a 131-B INTEIRA, neste chat, em série. Se o seu
contexto passar de 600 k antes da 131-B, entregue a 131-A e escreva o prompt da 131-B para um chat novo (protocolo §10).

0. PREFLIGHT (CLAUDE.md §2): git fetch origin · git rev-list --count HEAD..origin/main (TEM de ser 0; senão pare e pergunte) ·
   git rev-list --count origin/main..HEAD · confira que docs/canon/specs-propostas/SPEC-131-O-APLICATIVO-DE-RENOVACAO.md está na
   origin/main (senão pare e pergunte) · git switch -c spec/131-A-a-madrugada origin/main · git rev-parse --short HEAD · git status
   --short. A 131-B nasce em spec/131-B-o-aplicativo da origin/main DEPOIS do push da 131-A. Arquivos .TXT soltos em docs/canon/ e as
   pastas app/app/ e app/backend/ são do Founder: não commite, não apague.

1. LEITURA, nesta ordem e nada mais: CLAUDE.md inteiro · docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md inteiro (UMA vez) ·
   docs/canon/GLOSSARIO.md · a proposta SPEC-131-O-APLICATIVO-DE-RENOVACAO.md INTEIRA (você a converte em DUAS SPECs executáveis) ·
   os laudos de docs/canon/programa-multicalculo/131/ SÓ pela seção que a unidade citar (131-A: I1 §1–§5; 131-B: I2 §4–§6, I3 §1–§3) ·
   PENDENCIAS.md SÓ por número: P-130B-11, P-130B-12, P-1310-02, P-1310-04, P-1310-06, P-128-01, P-129C-04, P-130A-01, P-16 ·
   FOUNDER-DECISIONS.md SÓ D-131-01…28, D-131-0-03/05/06/16, D-MC-66/69, D-130A-07 · MIGRATIONS-AUTHORITY.md antes de QUALQUER SQL ·
   DS-001-design-brief.md §5, §8.6, §8.7, §14 (só na 131-B).

2. O OBJETIVO e o "pronto quando": proposta §0–§2. 131-A = a madrugada (lista, cálculos, conferência que fica VERMELHA, aviso);
   131-B = o aplicativo (padrão, aba Renovações, página de renovação, wa.me do comercial). O Prosseguir de madrugada SÓ com as travas
   da §4.4 e DEPOIS de medir (BLOCO 0 A1). Nenhum motor paralelo (CLAUDE.md §5).

3. O RITO (protocolo v13 §5, CRÍTICO as duas), para CADA SPEC: card + fio + BLOCO 0 (proposta §3) → a SPEC executável em
   docs/canon/specs/ (≤ 15 KB) → builders Opus 5.5 xhigh frescos, um por fatia, em paralelo só como a proposta §5 prova (F1‖F2‖F3 → F4;
   G1‖G2‖G3‖G4 → G5), contrato da §5 fixado antes → teste do fio VERMELHO primeiro → verificador com as mutações da §6 (worktree
   próprio) → juiz ‖ red team Opus 5.5 UMA vez (131-A + lente do dado; 131-B + a página SERVIDA contra o DS-001 §5) → conserto único →
   confirmação se houve blocker → bateria contra BATERIA-LINHA-DE-BASE.txt → relatório → git push origin HEAD:main com a saída colada →
   agente atualizador de documentos. app/: test:rotas-montam + next start + /api/renovacoes. SQL: APPLY/VERIFY/ROLLBACK antes.

4. VERBA de modelo (livro-caixa do ESTADO-DO-PROGRAMA §3, estimativa escrita ANTES de cada rodada): 131-A ≤ US$ 1,00 · 131-B ≤ US$ 0,30.

5. DADOS E CONTAS: nenhum CPF, nome, telefone, placa ou nº de apólice em código, teste, relatório ou chat (locator com hash); o telefone
   do cliente é buscado na hora, nunca guardado nem logado; nenhum nome de corretora ou pessoa em regra de produto (CLAUDE.md §13.9).
   O canário de madrugada roda na corretora de ENSAIO. NUNCA entre no Agger de uma PESSOA sem o aceite novo registrado (T-141); o
   BLOCO 0 do Prosseguir usa só o cotador@ da própria corretora, em dois contextos. Nada é enviado a cliente.

6. Pare SÓ pelas 8 condições do CLAUDE.md §10. Decida o resto com nota 0–100 e registre. A última mensagem é o relatório completo ao
   Founder (CLAUDE.md §12.2), em linguagem de gente, cobrindo as DUAS SPECs.
```
