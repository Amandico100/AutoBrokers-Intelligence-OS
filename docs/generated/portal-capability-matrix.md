# Portal Capability Matrix

> **GERADO — NÃO EDITAR MANUALMENTE**  
> fonte: registry + test manifests + canary evidence
> gerado em: 2026-08-16

Uma linha por `(portal, journey)`. `score` já é o score **operacional**: hard blocker do §21.3 não desconta pontos, ele **anula** — uma journey bloqueada aparece com 0 e a medição bruta fica em `score_bruto`, no JSON.

| portal | journey | business operation | effect class | requires account | supports resume | API-first / DOM / adaptive / vision | fixture count | negative cases | readiness state | score | last canary | live eligible | blocking reason |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| vidros_lanternas<br><code>vidros_lanternas.abrir_atendimento</code> | abrir_atendimento | assistance.glass.request | material_side_effect | sim | sim | api | 1 | 0 | DRAFT | 0 | — | nao | cross_tenant_possible |
| allianz_corretor<br><code>allianz_corretor.cobranca_sweep</code> | cobranca_sweep | billing.overdue.list | read_only | sim | nao | dom | 0 | 0 | DRAFT | 0 | — | nao | cross_tenant_possible |
| hdi_corretor<br><code>hdi_corretor.cobranca_sweep</code> | cobranca_sweep | billing.overdue.list | read_only | sim | nao | dom | 1 | 0 | DRAFT | 0 | — | nao | cross_tenant_possible |
| mapfre_corretor<br><code>mapfre_corretor.cobranca_sweep</code> | cobranca_sweep | billing.overdue.list | read_only | sim | nao | api | 1 | 0 | DRAFT | 0 | — | nao | cross_tenant_possible |
| tokiomarine_corretor<br><code>tokiomarine_corretor.cobranca_sweep</code> | cobranca_sweep | billing.overdue.list | read_only | sim | nao | api | 1 | 0 | DRAFT | 0 | — | nao | cross_tenant_possible |
| yelum_corretor<br><code>yelum_corretor.cobranca_sweep</code> | cobranca_sweep | billing.overdue.list | read_only | sim | nao | api | 1 | 0 | DRAFT | 0 | — | nao | cross_tenant_possible |
| zurich_corretor<br><code>zurich_corretor.cobranca_sweep</code> | cobranca_sweep | billing.overdue.list | read_only | sim | nao | api | 1 | 0 | DRAFT | 0 | — | nao | cross_tenant_possible |
| allianz_corretor<br><code>allianz_corretor.login_check</code> | login_check | portal.login.check | read_only | sim | nao | dom | 0 | 0 | DRAFT | 0 | — | nao | cross_tenant_possible |
| hdi_corretor<br><code>hdi_corretor.login_check</code> | login_check | portal.login.check | read_only | sim | nao | dom | 1 | 0 | DRAFT | 0 | — | nao | cross_tenant_possible |
| mapfre_corretor<br><code>mapfre_corretor.login_check</code> | login_check | portal.login.check | read_only | sim | nao | api | 1 | 0 | DRAFT | 0 | — | nao | cross_tenant_possible |
| tokiomarine_corretor<br><code>tokiomarine_corretor.login_check</code> | login_check | portal.login.check | read_only | sim | nao | api | 1 | 0 | DRAFT | 0 | — | nao | cross_tenant_possible |
| vidros_lanternas<br><code>vidros_lanternas.login_check</code> | login_check | portal.login.check | read_only | sim | nao | api | 1 | 0 | DRAFT | 0 | — | nao | cross_tenant_possible |
| yelum_corretor<br><code>yelum_corretor.login_check</code> | login_check | portal.login.check | read_only | sim | nao | api | 1 | 0 | DRAFT | 0 | — | nao | cross_tenant_possible |
| zurich_corretor<br><code>zurich_corretor.login_check</code> | login_check | portal.login.check | read_only | sim | nao | api | 1 | 0 | DRAFT | 0 | — | nao | cross_tenant_possible |

14 journey(s) · 0 elegivel(is) a live · 14 com hard blocker aberto.

**Sobre o 100 (§21.4).** Score 100 significa que *todos os gates que definimos medir foram medidos e passaram*. Não significa que a journey nunca falha: o portal externo continua podendo cair, mudar de HTML ou recusar login. O sistema excelente é o que falha com segurança, diagnóstico e retomada — não o que promete um mundo externo infalível.
