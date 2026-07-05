# GUIA DE EXECUÇÃO — para o Opus 4.8 executar as SPECs (019/020/021)

**Autor**: Fable 5 (líder técnico) · 2026-07-05. Fable revisa TUDO no final — seu trabalho
será auditado; siga o guia à risca e marque desvios explicitamente no commit.

## 0) Contexto obrigatório antes de codar
1. LEIA a memória automática do projeto (é carregada no seu contexto): especialmente
   `onda2-discovery-2026-07.md` RODADAS 13→18 (URLs de deploy, credenciais de DEBUG,
   decisões, bugs já resolvidos e COMO). NUNCA recoloque credenciais em código/commit.
2. LEIA a SPEC que for executar INTEIRA + este guia. Em conflito: SPEC > guia > seu critério.
3. Worktrees: código em `AutoBrokers-Fable-Exec-SPEC016` (branch `feat/spec-017-attendant`);
   merges na main em `AutoBrokers-Intelligence-OS`. **SEMPRE `git branch --show-current`
   antes de merge/push** (já houve acidente com branch errada checked out).

## 1) Regras invioláveis (quebrar = retrabalho garantido)
- **Cérebro ÚNICO**: toda execução de agente passa por `create_agent_graph`/
  `LangChainService.process_message`. PROIBIDO criar runtime/motor paralelo.
- **P0 identidade InfoCap**: numapo = número humano, SEMPRE visível ao titular;
  nosnum/locator = técnico. Nunca reverter máscara de nome/CPF no atendimento.
- **PII**: dados reais do sócio (Rafael/CPF/telefones) NUNCA em fixture, commit, log, doc.
- **Migrations expand-only**, header APPLY/VERIFY/ROLLBACK; quem roda é o FOUNDER (avise
  no relatório final o arquivo exato).
- **Gates**: `INSURER_DISPATCH_LIVE` e `PORTAL_REAL_ENABLED` ficam OFF; nada externo real.
- **WhatsApp seam**: resultado de envio usa campo **`.ok`** (NÃO `.success`) — bug histórico.
- Front: componentes Radix com portal (Select/Dialog) DENTRO do /admin renderizam fora do
  tema → usar elementos nativos estilizados no /admin (no /dashboard, shadcn ok).
- `<select>`/`<input time>` nativos em tema escuro: adicionar `[color-scheme:dark]`.

## 2) Ciclo de trabalho (por fatia PEQUENA — 1 a 3 arquivos)
1. **TDD house-style**: teste standalone em `backend/tests/test_<spec>_<tema>.py`
   (padrão dos existentes: importlib para carregar módulo isolado, stubs de pacote via
   `types.ModuleType`, função `check()`, SEM pytest, só ASCII "->" em nomes).
   RED (rode e veja falhar) → implementa → GREEN.
2. Rode a bateria completa (todas passam HOJE — se quebrar, foi você):
   `for t in backend/tests/test_*.py; python "$t"` (individualmente).
3. Frontend: `npx tsc --noEmit` SEMPRE antes de commit.
4. Commit na branch exec (mensagem em inglês, escopo tipo `feat(spec019-c): ...`,
   rodapé `Co-Authored-By:` do modelo que executou) → merge `--no-ff` na main → push.
5. **Deploy**: gatilhos EasyPanel via curl POST (URLs na memória RODADA-13; API para
   mudanças backend/, WEB para app/ components/ lib/). Depois smoke:
   API `GET /health` contém "healthy"; WEB `GET /` = 200 (URLs na memória RODADA-13/22).
6. Relatório ao founder em PT-BR simples: o que mudou, o que ELE testa (passo a passo),
   o que ELE precisa rodar (SQL) ou configurar (env EasyPanel).

## 3) Mapa REAL vs LEGADO/MOCK (não construa sobre mock)
- REAL (usar): whatsapp seam (`backend/app/services/whatsapp/*`), dispatch engine+router,
  `routine_engine.py` + tools em `routine_tools.py`, `vision_service.py`, capability
  Registry (`capability_resolver`, strict mode), Central de Conversas
  (`/dashboard/atendimentos/conversas` + `/api/dashboard/conversas*`), rotinas UI
  (`/dashboard/auxiliares/rotinas` + `/api/dashboard/rotinas`), buffer (piso 8s/25s).
- LEGADO/MOCK (não estender): `lib/mock/tenant-modules.ts`, fluxo do Portal Lab (admin),
  bridge TS de atendimento, provider z-api legado (compat apenas).
- Bucket storage: imagens → `chat-media` (SÓ aceita imagem); docs/áudio → `chat-docs`.

## 4) Debug permitido (com parcimônia)
- Supabase REST com service key (memória) p/ VERIFICAR dados; nunca gravar chaves em repo.
- Evolution API direta (base URL + apikey na memória) p/ instância/webhook/mensagens.
- Sonda e2e do canal: POST no webhook token da integração (URL completa na memória
  RODADA-13) com payload Evolution sintético — telefone TEM que estar na
  `ATTENDANT_INBOUND_ALLOWLIST` (5547988087463). Use ids de mensagem ÚNICOS (dedup!).

## 5) Ordem recomendada de execução
1. **Sonda imagem WhatsApp** (pendência): injete imageMessage sintética com base64 de
   um PNG 1x1 + caption; verifique em `messages` (REST) se image_url foi salvo e se a
   resposta menciona a imagem. Se falhar: logar hipóteses (describe_image exception?
   base64 ausente no payload real?) e corrigir. Aceite: atendente comenta a imagem.
2. SPEC-019 fase C (galeria routine_templates) e D (robustez executor) — A e B JÁ FEITAS.
3. SPEC-020 (portal-worker) — janela própria, começar pelo P1.
4. SPEC-021 (learning_notes → metering → Firecrawl → PLAYBOOK-AUTHORING).
