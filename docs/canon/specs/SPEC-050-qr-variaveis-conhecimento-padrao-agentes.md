# SPEC-050 — QR que sempre nasce, variáveis que nunca congelam, Conhecimento humano e o Padrão de Agentes

> Executada em 21/07/2026 (pedidos do founder pós-testes da SPEC-049 +
> auditoria completa da Central de Agentes que ele exigiu).

## 1. QR code não gerava — causa-raiz e fix definitivo

A instância GO da Resulta ainda estava REGISTRADA no número antigo de teste
(jid 554796274743, "Reconnecting") — com sessão registrada o WhatsApp NUNCA
emite QR novo, e o logout do GO não limpa a sessão. Fix em 3 camadas:
- **Manual (feito agora):** instância zumbi `autobrokers-go-teste` apagada no
  GO (`DELETE /instance/delete/{uuid}`, chave global — endpoint confirmado na
  doc oficial) e linha aposentada (`retired`). O próximo "Gerar QR" da Resulta
  cria a instância definitiva `ab-04b5cdbc04cd` limpa → QR na hora.
- **Desconectar nuclear (código):** logout; se a sessão registrada persistir
  (jid no `/instance/all`), apaga a instância no GO e aposenta a linha —
  trocar de número NUNCA mais trava.
- **Auto-cura no setup (código):** connect 401/404 (linha aponta p/ instância
  inexistente) → recria com token novo; create 409/422 (instância fantasma no
  GO sem linha) → apaga e recria. Sem becos sem saída.

## 2. Nome congelava DE NOVO — segunda raiz encontrada e morta

`computeAgentConfigUpdate` gravava `eff.variables_used` — os valores PÓS
render aninhado. O 1º save funcionava na tela, mas fossilizava a abertura com
o nome literal ("Sou FERNANDA..."); o 2º rename só mudava o nome. Fix:
persistir o valor CRU (input do form > valor salvo anterior), nunca o
renderizado. Abertura das duas corretoras normalizada no banco de novo.
Com as duas raízes mortas (SPEC-049 whitelist + esta), o ciclo completo
renomear→salvar→renomear→salvar fica estável.

## 3. Conhecimento — humano e sem seleção

- "Qual assistente vai usar?" REMOVIDO (o conhecimento é da corretora; todos
  os assistentes usam automaticamente; o vínculo técnico de agente é resolvido
  no servidor via Core).
- Lista humanizada: `infocap-policy-<hash>.pdf` → "Apólice do sistema da
  corretora (…hash)" com origem ("Importada automaticamente da InfoCap durante
  um atendimento"); status em português (Pronto para uso / Processando… /
  Falhou); data; ícones. Zero jargão.

## 4. Auditoria da Central de Agentes (15 agentes, 3 auditores independentes)

Checklist de 10 itens (1 ponto cada): missão clara · gatilho registrado ·
entradas explícitas · saídas explícitas · guardrails fail-safe · custo/modelo
declarado · observabilidade (beat+Atividades+log) · idempotência/dedup ·
teste cobrindo · isolamento multi-tenant.

| Agente | Nota | Pior gap encontrado |
|---|---|---|
| Espelho (dispatch) | 10 | — |
| Observador | 9 | PII crua em repouso em observed_events (máscara só downstream) |
| Espelho de Atendimento | 9 | destilação cross-tenant protegida SÓ pela máscara |
| Vigia+Sentinela | 9 | invisível nas Atividades → **CORRIGIDO hoje** |
| Garimpo | 9 | pulso sem contagem; docstring desatualizada → **CORRIGIDOS hoje** |
| Lapidador | 9 | sem heartbeat próprio; marcador semanal antes do loop |
| Cérebro v2 | 9 | mapa da URA degrada em silêncio; prompt/guard triplicado |
| Sentinela de Rotas | 8 | run_all sem guarda por-seguradora → **CORRIGIDO hoje** |
| Auditor | 8 | **duplicava scorecards sem Redis** → dedup estrutural **CORRIGIDO hoje**; docstring anunciava cascata LLM inexistente → **corrigida** |
| Follow-up | 8 | invisível nas Atividades → **CORRIGIDO hoje**; teste raso |
| IA de Sugestões | 8 | idempotência global grosseira (falha parcial pula a semana) |
| Cartógrafo | 8 | sem arranque autônomo (por design até 2ª ordem) |
| Conselho | 8 | sem cache/dedup de convocação (re-paga em retries) |
| Memória por agente | 8 | pulsa no heartbeat do Espelho (não aparece como agente próprio) |
| Alfaiate | 7 | **GRAVE: overlay era gravado ANTES do gate do Simulador** → **CORRIGIDO hoje** (gate fail-closed antes da escrita) |

**Corrigido nesta SPEC (7 quick-wins):** gate do Alfaiate antes da escrita;
guarda por-seguradora no run_all; dedup estrutural do Auditor (+docstring
honesta); pulso com contagem + docstring do Garimpo; Vigia e Follow-up no
feed de Atividades.

**Backlog proposto (aguarda liberação, em ordem):**
P1 — Sugestões: marcador por corretora após envio (retry justo);
P2 — Observador: mascarar PII na borda de captura (não só no Tecelão);
P3 — Tecelão: fail-safe de topo + teste do weave_insurer;
P4 — Lapidador: heartbeat próprio + marcador pós-loop;
P5 — Cérebro v2: unificar prompt/guard num módulo único (3 cópias hoje);
P6 — Conselho: cache de convocação por decisão;
P7 — Auditor: implementar de fato a camada LLM por amostragem (ou não anunciar).

## 5. PADRÃO AUTOBROKERS DE AGENTE (obrigatório daqui em diante)

Todo agente da Central — novo ou alterado — DEVE preencher os 10 itens do
checklist acima, com evidência. Regra prática (estilo skill/plugin premium):
- docstring padronizada no topo do arquivo: MISSÃO (1 frase) · GATILHO ·
  ENTRADAS · SAÍDAS · CUSTO/MODELO · GUARDRAILS · O QUE NUNCA FAZ;
- job registrado (ou piggyback documentado) + `beat(<nome próprio>, contagem)`;
- ação relevante → `log_activity` (o corretor vê o agente trabalhar);
- dedup estrutural no banco (nunca só marcador Redis);
- teste house-style cobrindo o caminho principal;
- docstring NUNCA anuncia capacidade não implementada (auditável);
- gates de qualidade rodam ANTES de qualquer escrita (fail-closed).
O teste `test_spec050_*` fixa os quick-wins; specs futuras devem citar o item
do padrão que cada agente novo cumpre.

## Invioláveis
- Simulador gateia a ESCRITA do overlay (nunca só o relato).
- Desconectar de verdade: sessão registrada nunca sobrevive ao botão.
- Valor CRU das variáveis é o que persiste; renderizado é só exibição.
