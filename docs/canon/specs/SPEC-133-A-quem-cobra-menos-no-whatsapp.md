# SPEC-133-A — Quem Cobra Menos no WhatsApp, piloto fechado

> v1.0 · 07/10/2026 · gerente Opus 5.5 · branch `spec/133-A-qcm-whatsapp` · base `de66449` (main) · rito AAA v13 · 🔴 CRÍTICO por piso
> Leitura obrigatória antes de qualquer fatia: `docs/canon/programa-multicalculo/BLOCO0-DA-133-A.md` (o BLOCO 0 medido, com arquivo:linha)
> e `programa-multicalculo/PRONTIDAO-DA-133-A.md`. Decisões de origem: D-MC-51…61, D-130A1-01…16 (a D-130A1-15 é a copy do Founder).

## 1. EXECUTION CARD
```
OUTCOME ..............  um número CONVIDADO manda "oi" para o Quem Cobra Menos (temporário 47 98808-7463, Evolution) e chega ao
                        resultado na mesma conversa: consentimento, perguntas uma por vez (com "quanto você paga hoje?"), o pedido
                        ao motor nas corretoras parceiras em paralelo, a proposta publicada com a PÁGINA DA MARCA QCM, a mensagem
                        do canal na copy do Founder, a pergunta final, até 2 lembretes, a passagem à corretora vencedora. O QR se lê
                        no portal ADMIN. Nenhum envio a número não convidado, a número de corretora, a grupo ou a si mesmo.
RISCO ................  8 — ALCANCE 3 (pessoas reais no WhatsApp) · REVERSIBILIDADE 3 (mensagem enviada não volta; CPF ao Agger) ·
                        FREQUÊNCIA 2
SUPERFÍCIE ...........  3 — o webhook de entrada de TODAS as corretoras é tocado (o desvio)
PISO APLICADO ........  §3.2 — envia mensagem a pessoa real · migration nova com dado pessoal (telefone, consentimento) · toca o
                        caminho de entrada do atendimento das corretoras
NÍVEL ................  🔴 CRÍTICO · gerente Opus 5.5 · builders Opus 5.5 · juiz ‖ red team · conserto · confirmação
O FIO ................  BLOCO0 §11: webhook Evolution Go → desvio do canal (antes do observer_tap) → buffer → canal.entrada.turno
                        (anti-laço, convidado, limite, consentimento, estado) → canal.conversa.responder → envio.enviar → … perfil
                        completo → canal.cotacao.disparar → porta.calcular(origem='canal', OPCOES_DO_CANAL) → Work Run canal.cotacao
                        → motor (corretoras ‖) → consultar → publicar_proposta (renderizador do canal) → mensagem_para → enviar →
                        dormir → lembretes → passagem
                        · teste do fio (F-COSTURA): payload REAL do Evolution Go no webhook de uma integração `platform_canal` até os
                        balões com /r/<token>; controles com ZERO envio (não convidado, acima do limite, número de corretora, fromMe,
                        grupo); não-regressão (o observer das corretoras continua consumindo)
PARALELISMO REAL .....  F1 (entrada) ‖ F2 (conversa+cotação) — contrato §3, arquivos disjuntos ‖ F3 (página QCM) ‖ F4 (QR no admin)
                        → F-COSTURA (o teste do fio inteiro) · F0 (a copy) e FM (a marca) já em curso na abertura
UNIDADES .............  U1 desvio + anti-laço · U2 convidados/limite/consentimento/lead/estado (migration) · U3 envio · U4 a conversa
                        (estado + papel canal_cotacao) · U5 a regra da placa · U6 o Work Run canal.cotacao (narração, publicar,
                        mensagem, lembretes, passagem) · U7 a página QCM · U8 o QR no admin · U9 a copy (F0) · U10 a marca (FM)
COESÃO ...............  U1+U2+U3 (F1) · U4+U5+U6 (F2) · U7 (F3) · U8 (F4)
TIME .................  gerente · investigador (BLOCO 0) · F0 · FM · F1 · F2 · F3 · F4 · costura · juiz ‖ red team · conserto ·
                        confirmação
REFERÊNCIA ...........  interna: webhook.py, whatsapp_service.py, pairing/hub, Work OS runs (dormir/despertar), Model Router
                        (llm_papeis), porta/motor (129-B), proposta/mensagem (130-A/130-A.1) · externa: o logo do QCM (o "Q"
                        azul-marinho com a cauda verde-limão), o logo da AutoFleet
GATES ................  §5
O ELO ................  "o canal só fala com quem foi convidado PORQUE o filtro roda antes de qualquer envio": o teste do fio afirma
                        ZERO chamadas a send_message nos 5 controles, pelo webhook real
FAIXA DE RELÓGIO .....  💭 6–9 h
```

## 2. As decisões (pela maior nota; o Founder lê no fim)
| id | decisão | notas |
|---|---|---|
| D-133A-01 | **O agente do canal é uma conversa guiada por ESTADO** (uma pergunta por vez, a ordem fixa), com o modelo só para ENTENDER resposta livre, pelo papel novo `canal_cotacao` (o mais barato aprovado: 📊 `gpt-6-luna`, US$ 0,10/0,50 por milhão) | estado + papel 86 · grafo LangGraph novo 60 · agente de atendimento no canal 30 |
| D-133A-02 | **Desvio por tipo de empresa no webhook** (`company_kind = platform_canal`): o canal pula o observer e entra em `canal.entrada.turno`; nenhum agente "attendance" no canal | 90 × 30 |
| D-133A-03 | **No canal a PLACA supre FIPE, ano de fabricação e combustível** (o robô preenche pela placa — `agger_robo.py:310`, `montador.js:121`) | 85 × perguntar os três 55 |
| D-133A-04 | **Convidados, limite por número, consentimento e lead numa migration nova** (tabelas do canal, RLS sem policy + REVOKE + filtro no código), os números entram por comando/admin, nunca no código | 90 |
| D-133A-05 | **O consentimento diz a verdade do paralelo:** "o seu CPF e o seu carro vão às seguradoras pelas corretoras parceiras do Quem Cobra Menos, para cotar; ninguém é obrigado a fechar" | 92 × "só a vencedora" 20 (falso) |
| D-133A-06 | **Anti-laço:** nunca responder a número de linha/agente de corretora, a `fromMe`, a grupo; teto de mensagens por conversa | 95 |
| D-133A-07 | **O 47 98808-7463 fica na allowlist do atendimento** (continua cliente de teste das corretoras); o canal ignora mensagens vindas de linhas de corretora | 85 × tirar 60 |
| D-133A-08 | **A pergunta "quanto você paga hoje no seu seguro?"** entra na conversa (opcional) e alimenta a economia da copy (D-130A1-15) | 88 |
| D-133A-09 | **A página do canal é um renderizador próprio** (`proposta_canal_html.py`) com a marca do Quem Cobra Menos e a corretora vencedora dentro, reusando o MESMO script (o hash da CSP não muda); a página da carteira não muda | 88 |
| D-133A-10 | **O QR no admin** reusa `WhatsAppChannelCard`/`WhatsAppPairingFlow` com um `endpoint` apontado para a empresa do canal | 90 × tela nova 40 |
| D-133A-11 | **P-130A1-08 corrigida pelo BLOCO 0:** o motor já roda as corretoras em paralelo (mesmo `disparado_em`); o `concurrency: 1` é da fila de cobrança/vidros; os 85 s são o atraso de nova tentativa depois da morte proposital do canário. Prova: um pedido do canal SEM `--matar`, no contêiner (F5, depois do Implantar + robôs) | 88 |
| D-133A-12 | **Contas do Agger para os testadores:** o caminho certo é o usuário-robô por corretora (T-120). Enquanto não existir, o Founder pode autorizar o login da Ellen como `ativo` SÓ na janela da noite (20h–23h59, fora do horário dela) — decisão dele no fim, não trava a construção | robô 90 × Ellen à noite 70 |

## 3. O contrato entre F1 e F2 (os dois escrevem em paralelo contra ele)
```python
# backend/app/services/canal/repositorio.py  (F1)
def eh_canal(db, company_id: str) -> bool
def convidado(db, company_id: str, telefone_e164: str) -> dict | None          # {"id", "apelido"?, "limite_dia"?}
def dentro_do_limite(db, company_id: str, telefone_e164: str, config) -> bool   # pedidos de cotação por número/dia (config canal)
def numero_de_corretora(db, telefone_e164: str) -> bool                          # anti-laço: paired_phone de integração de corretora
def registrar_consentimento(db, company_id, telefone_e164, *, aceito: bool, versao_do_texto: str) -> None
def registrar_lead(db, company_id, telefone_e164, *, primeiro_nome=None, pedido_id=None) -> None
def carregar_estado(db, company_id, telefone_e164) -> dict                       # {} na 1ª vez; cifrado em repouso
def salvar_estado(db, company_id, telefone_e164, estado: dict) -> None
# backend/app/services/canal/envio.py  (F1)
async def enviar(db, company_id: str, telefone_e164: str, baloes: list[str]) -> int   # quantos saíram; pela integração do canal
# backend/app/services/canal/entrada.py  (F1)
async def turno(db, integration: dict, telefone_e164: str, itens: list[dict]) -> None
#   filtros → estado = carregar_estado → r = await conversa.responder(...) → salvar_estado(r.estado) → enviar(r.baloes)
#   → se r.disparar: await cotacao.disparar(db, company_id, telefone_e164, r.disparar, r.estado)
# backend/app/services/canal/conversa.py  (F2)
@dataclass class Resposta: baloes: list[str]; estado: dict; disparar: dict | None = None   # disparar = o perfil completo
async def responder(db, company_id: str, telefone_e164: str, texto: str, midia: dict | None, estado: dict, *, config) -> Resposta
# backend/app/services/canal/cotacao.py  (F2)
async def disparar(db, company_id: str, telefone_e164: str, perfil: dict, estado: dict) -> str   # o id do Work Run canal.cotacao
```
F1 dona da migration das tabelas do canal; F2 dona da migration de dado do papel `canal_cotacao` em `llm_papeis`.

## 4. A conversa (o roteiro — F2 escreve o texto, curto e humano)
oi → apresentação + consentimento (D-133A-05) → "sim" → placa → CEP de onde o carro dorme → CPF do principal condutor → data de
nascimento (se o Agger pedir além do CPF) → estado civil (só o que tem código medido; sem código → o padrão medido) → garagem em casa/
trabalho → uso (particular/aplicativo/trabalho) → condutor de 18–25 anos? → "quanto você paga hoje? (pode pular)" → "calculando…" (uma
narração curta) → a mensagem do canal (D-130A1-15) com o link → a pergunta final → até 2 lembretes → "quero fechar" → a passagem.
Apólice/foto: recebe, guarda com o consentimento, agradece e segue pelas perguntas (a leitura é da 130-B). Fora do escopo → "vou te
passar para a corretora" com o resumo.

## 5. Gates
G1 o teste do fio (§1) pelo webhook real · G2 os 5 controles com ZERO envio · G3 o observer das corretoras intacto · G4 consentimento
registrado antes de qualquer pergunta de dado pessoal; "não" encerra sem guardar dado · G5 a porta recebe `origem='canal'`, as adesões
ativas e `OPCOES_DO_CANAL`, e nunca `PerfilIncompleto` com a placa · G6 a página do canal com a marca QCM e o hash da CSP igual; a da
carteira byte a byte igual · G7 o QR no admin: `npm run test:rotas-montam` + `next start` + 1 requisição na rota nova · G8 os lembretes
param na resposta da pessoa e nunca passam de 2 · G9 migration com APPLY/VERIFY/ROLLBACK e teste com dois tenants · G10 bateria sem
regressão · G11 nada de nome de corretora/número como constante.

## 6. Fora
A leitura da apólice (130-B) · as regras entre corretoras (133-B) · a API oficial (134) · o login de robô (T-120, Founder) · a medição do
motor no contêiner (F5, depois do Implantar + robôs).
