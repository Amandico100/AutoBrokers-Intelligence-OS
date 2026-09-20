# SPEC-EXTRA-001.7 · O piloto medido — RELATÓRIO DE EXECUÇÃO

> 20/09/2026 · segunda SPEC sob o **núcleo do AAA v13 em teste** (D-PROTO-10). Base `3ae6af8`.
> Branch `feat/extra-001-7-o-piloto-medido`. Proposta: `DIAGNOSTICO-PILOTOS-E-PLANO-EXTRA-2026-09-12.md` §0, bloco 001.7, §12.

## 0.0 🔴 EXECUTION CARD (protocolo §0.2) — recontado no BLOCO 0 sobre `3ae6af8`
```
OUTCOME ..............  o Founder roda UM comando e sabe se dá para ligar o agente hoje (com o motivo de cada trava); e roda
                        OUTRO e recebe, por dia × corretora, os números do piloto e a nota 0–100 de cada dimensão do §0 do
                        diagnóstico — ou "NÃO AVALIADA" quando o dado não existe. As notas deixam de ser palpite
RISCO ................  3   (a corretora/Founder lê e decide 2 · nada fica depois de desfazer 0 · todo dia de piloto 1)
SUPERFÍCIE ...........  2   (uma peça nova: a medição + régua; e a extensão do checklist)
PISO APLICADO ........  nenhum: nada envia, nenhuma migration, só SELECT. O /health ganha 1 sinal de CONTAGEM (sem número)
NÍVEL ................  PADRÃO · builders Opus 5 xhigh · juiz generalista Fable 5.1 ‖ red team Fable 5.1
UNIDADES .............  3 em 2 fatias paralelas: ① A checklist de ligar ‖ ② B medição diária + C régua por dimensão
COESÃO ...............  B e C juntas: a régua consome o contrato que a medição define. A é disjunta (outro arquivo)
PARALELISMO REAL .....  fatias ① e ② ao mesmo tempo (arquivos disjuntos, sem commit); juiz ‖ red team; investigador read-only: sim (1)
TIME .................  gerente Fable · 1 investigador Opus · 2 builders Opus · juiz + red team Fable · confirmação por gatilho (blocker material)
REFERÊNCIA ...........  interna: `backend/app/services/os_modelos_do_grupo.py` (`contagens_do_dia`/`eficiencia_do_dia`: o motor
                        que o produto já usa às 19h, com "sem escritor = não medido") e `backend/scripts/regua_0971.py` (régua que
                        IMPORTA o motor) · externa: a da proposta (§7.3: na execução não se repesquisa)
GATES ................  G1 checklist REPROVA com trava fechada e PASSA com todas abertas (par) · G2 medição sobre o banco real,
                        dia × corretora, 2 rodadas idênticas · G3 zero PII na saída · G4 isolamento com as DUAS corretoras reais ·
                        G5 dimensão sem dado sai "NÃO AVALIADA" (mutação) · G6 menos dado NUNCA melhora a nota
O ELO ................  "a nota da dimensão é X PORQUE o banco tem Y": o teste do fio afirma a NOTA FINAL a partir das linhas do
                        banco (dublê gerado do schema real), atravessando o motor importado — não a função da régua solta
FAIXA DE RELÓGIO .....  150 min (teto 1,5× = 225) · início 20/09 07:44 UTC · tetos: 24 agentes · 2 simultâneos
```

### O FIO
```
ENTRA  banco de produção: messages(role, payload.origem/direcao/wa_message_ids) · conversations(company_id, status,
       resolvido_em, resolucao_motivo) · work_events(grupo.enviado/calado, vigia.*, handoff.*) · agent_activities
       (handoff entregue/falhou; silêncios) · platform_sends(kind) · work_runs(runtime_kind='acionamento')
  →    backend/scripts/medir_o_piloto.py:ler_o_dia        SELECT paginado, filtro company_id, dia no fuso da corretora
  →    MOTOR importado: os_modelos_do_grupo.contagens_do_dia · eficiencia_do_dia · o_fim_do_atendimento.classe_do_silencio ·
       e_origem_humana · human_handoff.TITULO_HANDOFF_* · platform_outbound.fuso_da_corretora
  →    medir_o_piloto.py:medir_o_dia                      o número por métrica × dia × corretora (só contagens)
  →    medir_o_piloto.py:regua_por_dimensao               nota 0–100 com o critério ao lado, ou NÃO AVALIADA
SAI    JSON + markdown em linguagem de gente → relatório em docs/canon/reports/ e a aba "O piloto" do artefato do Founder

CHECKLIST  /health (main.py:_sinais_do_codigo) + banco (agents · human_support_destinations · integrations ·
           company_internal_numbers) → scripts/conferir_o_que_esta_no_ar.py --ligar → motor: porteiro_do_agente.
           pode_ligar_o_atendimento · dispatch_router.resolver_destino_de_suporte · o_grupo_so_o_que_importa.numeros_da_casa
           → PODE LIGAR / NÃO PODE, com o motivo legível por trava · exit 0/1
```
