# RUNBOOK — Migração para Evolution GO (SPEC-034 §6.6, staged)

Decisão do founder 13/07: GO vira o provider principal (mais rápido; botões/listas
nativos; protobuf completo). Migração em estágios, sempre com rollback simples.

## Estágio 1 — Instância do CARTÓGRAFO (número exclusivo de exploração)
1. Founder providencia chip/número novo (NUNCA produção).
2. Na Evolution GO (mesma VPS, `GLOBAL_API_KEY=ab_evgo_test_2026_autobrokers`):
   `POST /instance/create` com `instanceName: cartografo`, integração baileys.
3. Parear o número novo pelo QR (`GET /instance/connect/cartografo`).
4. Configurar o webhook da instância para `https://<smith-api>/api/webhook/evolution`
   (mesmo endpoint; o roteamento por número isola o tráfego).
5. Registrar envs no smith-api: `CARTOGRAPHER_INSTANCE=cartografo`,
   `CARTOGRAPHER_PHONE=<numero>`.
6. Smoke: enviar "Oi" para o número da Allianz e conferir o espelho no dashboard.

## Estágio 2 — Número do ATENDENTE DE TESTE (5547996274743) — ANTES dos retestes
1. Criar instância GO `atendente-teste` e parear o MESMO número (desconecta da
   Evolution API antiga primeiro — 1 número = 1 instância).
2. Repontar a integração da corretora de teste (tabela `integrations`) para a
   nova instância/base URL do GO.
3. Rodar 1 atendimento de teste ponta a ponta (Even + acionamento + espelho).
4. Rollback: reparear na Evolution API antiga e repontar a integração (5 min).

## Estágio 3 — Números de PRODUÇÃO das corretoras — DEPOIS dos testes aprovados
- Um por vez, na madrugada, com aviso à corretora; mesmo processo do estágio 2.
- A Evolution API antiga permanece como fallback até o último cliente migrar.

## Regras
- NUNCA parear número de produção na instância do Cartógrafo.
- Cada estágio só começa com o anterior verde.
- Toda migração registrada (data, número, instância) neste arquivo.
