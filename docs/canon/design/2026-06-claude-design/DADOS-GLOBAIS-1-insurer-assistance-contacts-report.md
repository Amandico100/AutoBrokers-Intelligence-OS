# DADOS GLOBAIS 1 — Contatos globais de sinistro/assistência das seguradoras

> Grava os contatos oficiais de sinistro/assistência das seguradoras como **dados GLOBAIS e ATIVOS** (o segurado não muda; a corretora não preenche). Fonte: `docs/intake/sinistro e assistencias - contatos.xlsx`. Sem segredo (linhas públicas de assistência). Sem mudança de schema.
> **Data:** 2026-06-21 · **Modelo:** Claude Opus 4.8 · base: `d6643cb`

## O que foi feito
1. **Extraí a planilha célula a célula** (parse XML do xlsx) para não errar nenhum número — 12 seguradoras: Allianz, Alfa, Azul, Bradesco, HDI, Itaú, Mapfre, Porto, Tokio Marine, Yelum, Youse, Zurich.
2. **Seed global ativo** `lib/attendance/insurer-contacts-global-seed.ts` (self-contained), 6 canais por seguradora: `sinistro_auto`, `sinistro_re`, `assistencia_whatsapp`, `assistencia_24h_auto`, `assistencia_24h_re`, `vidros`, + `glass_service_portal_url` (portal do prestador de vidros) + `notes`. `scope: 'global'`, `is_active: true`.
3. **Registry/resolver puro** no mesmo módulo:
   - `parsePrimaryNumber(raw)` — extrai o **número principal sem o menu/URA** (ex.: `40901110 - 1-1-2` → `40901110`; compactos `40042757-2-1` → `40042757`), **preservando WhatsApp** (`11 4090-1444` → `1140901444`). O `raw` continua **autoritativo** (menus preservados para uso futuro).
   - `getInsurerContactsGlobal()`, `getInsurerContact(key)`, `normalizeInsurerKey` (acento-insensível, `Itaú`→`itau`).
   - `resolveInsurerDispatchTarget(insurer, serviceType, tenantOverride?)` — escolhe o destino certo: residencial/eletricista → **WhatsApp da assistência** (fallback assistência 24h RE); auto → assistência 24h auto; etc. **Override por tenant tem precedência** (gancho para personalização da corretora).
   - `getSharedServiceProviderPortals()` — agrupa por portal de prestador.
4. **Rota read-only** `GET /api/admin/insurer-contacts` — surface dos contatos globais + portais de prestador compartilhados (para o dashboard exibir/editar depois). Sem segredo.
5. **Testes** `scripts/attendance-insurer-contacts.test.mjs` — **22/22** (seed completo, parser de menu/WhatsApp, resolver por serviço, fallback Youse, override de tenant, portal compartilhado).

## Descobertas importantes (confirmam o que você falou)
- **Portal de prestador compartilhado:** a coluna "LINK VIDROS" é **`abraseuatendimento.com.br`** para a maioria das seguradoras (Bradesco usa `agendeseuservico.com`). Ou seja, é um **portal de prestador (não-seguradora) que serve várias seguradoras** — exatamente o seu ponto. Recomendação de modelo: a corretora conecta **uma vez** uma Portal Account do prestador (`abraseuatendimento`) e ela vale para todas as seguradoras que usam esse prestador (não uma conta por seguradora). Registrado em `getSharedServiceProviderPortals()`; a implementação do "1 login serve todas" entra no batch de Portais/Skills.
- **Menus/URA:** vários números têm opções (`- 1-1-2`, `cpf + 2`). Guardei o `raw` (autoritativo) + o principal derivado. Conforme você disse, uso o **número principal**; o menu fica preservado para quando as Skills precisarem navegar a URA.
- **Youse** não tem WhatsApp de assistência ("não tem") → o resolver cai para a central 24h.

## Arquitetura (sem estrutura paralela)
Espelha o padrão de Portais: **seed global** (ativo agora) + **override por tenant** (a corretora ajusta só se precisar). A camada de override por tenant já existe (`insurer-channel-store` em `tenant_connections.connection_config`); o resolver aceita `tenantOverride`. Edição dos defaults globais pelo master admin = próximo passo (dashboard).

## Sobre links de portais (você pediu para gravar)
Os **links dos portais das seguradoras já são globais** no catálogo (`portal-global-catalog-seed`, campo `base_url`) — a corretora já não precisa digitar o link, só login/senha. Este batch adiciona os **contatos de assistência/sinistro** (que faltavam) e os **portais de prestador (vidros)**.

## Segurança
- Não são segredos (linhas públicas de assistência/sinistro). Sem PII de cliente. Sem credenciais.
- `real_action_allowed=false`; nada é acionado; só dados de referência globais.

## Testes/verificação
- `node scripts/attendance-insurer-contacts.test.mjs` → **22/22**.
- `npx tsc --noEmit` EXIT=0 · `npm run build` verde.

## Teste live (admin logado)
```js
await (await fetch('/api/admin/insurer-contacts')).json();
// → { ok:true, scope:'global', count:12, contacts:[...], shared_service_provider_portals:[{portal_url, insurers, shared}] }
```

## Próximos passos (recomendados)
1. **Dashboard da Corretora (Tenant Activation):** exibir esses contatos globais (read-only) + permitir **override** por corretora; ativar corredor por toggle; conectar portais (login/senha) e o **portal de prestador compartilhado** uma única vez.
2. **Wiring no dispatch:** usar `resolveInsurerDispatchTarget` no builder de dispatch packet (hoje dry-run) para o destino global por seguradora/serviço. (Pequeno, gated.)
3. **42X5C** quando a Z-API for paga (canary inbound → 1 outbound HITL).
4. **Skills de portal de prestador** (abraseuatendimento) — 1 conexão por corretora servindo várias seguradoras.
