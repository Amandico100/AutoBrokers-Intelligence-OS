# SPEC-047 — Multi-empresa, WhatsApp por corretora e organização dos acessos

> Executada em 21/07/2026 sob pedido direto do founder (prompt "se organize e
> resolva tudo"). Itens liberados para execução imediata: unificação do
> pareamento WhatsApp, RLS das 6 tabelas, criação da AutoFleet + usuários e o
> acesso do mesmo e-mail a duas corretoras. O redesenho completo de
> equipe/permissões/aprovações ficou como PLANO para validação (seção 5).

## 1. WhatsApp — uma casa, uma instância POR corretora

**Problema real encontrado:** com `WHATSAPP_CHANNEL_PROVIDER=evolution-go`,
setup/QR/status/desconectar falavam com UMA instância global definida por env
(`EVOLUTION_GO_INSTANCE_TOKEN`) — qualquer corretora que pareasse derrubaria o
número da outra. Bloqueava Resulta + AutoFleet no mesmo dia.

**Solução (backend `whatsapp_channel.py`):**
- Instância GO **por corretora** (`ab-<company>`), criada via
  `EVOLUTION_GO_GLOBAL_KEY` com token próprio (mesmo padrão do onboarding do
  Atlas), **modo cofre** (readMessages/alwaysOnline/rejectCall off, ignora
  grupos/status) e persistida em `integrations` (o webhook já roteia por token
  de instância; o envio já usa o token da linha).
- QR/status/desconectar resolvem a instância **da corretora** pela linha do
  banco; a instância única por env virou fallback legado (Resulta atual).
- `HISTORY_SYNC` assinado no connect: pareamento fresco → histórico alimenta o
  Espelho de Atendimento/Atlas (matéria-prima dos 15-30 dias de observação).
- Uma função = um canal ativo: setup desativa instâncias GO antigas da mesma
  função (nunca dois números roteando a mesma coisa).

**Superfícies (frontend):**
- O modal do canal perdeu a escolha falsa "GO × clássico" (os dois abriam o
  MESMO fluxo — o provedor real é decidido pelo backend). Agora vai direto ao
  QR; a API Oficial da Meta segue anunciada como "em preparação". O provedor
  Evolution clássico continua vivo no backend (rollback/n8n), só saiu da tela.
- O card WhatsApp em Conectores deixou de abrir um segundo fluxo: é um atalho
  para a casa única — Personalização → Corretora → WhatsApp.

## 2. RLS — 6 tabelas internas blindadas (migração 20260721_01, APLICADA)

`billing_sent_log`, `ura_maps`, `broker_insights`, `playbook_overlays`,
`conversation_scorecards`, `agent_activities` → RLS ON sem policies =
anon/authenticated bloqueados; backend/Next admin usam service key (bypassa).

## 3. Multi-empresa — o mesmo e-mail em mais de uma corretora

- Tabela `company_members` (user ↔ company, role, is_owner, status, UNIQUE
  par) + seed de todos os usuários reais. `users_v2.company_id` segue sendo a
  empresa primária — nada legado quebra.
- Sessão ganhou `activeCompanyId`; `resolveSessionCompany` (o seam único de
  escopo do dashboard) valida o vínculo em `company_members` **a cada
  request** — revogou, caiu. Login sempre começa na empresa primária.
- `GET/POST /api/auth/companies` lista/troca; seletor de empresa no rodapé do
  dashboard (só aparece para quem tem 2+ vínculos). Mesma URL para todos —
  sem subdomínio por corretora (padrão Slack/Notion de workspace switcher).

## 4. Corretoras e usuários criados (dados de 21/07)

- **AutoFleet** criada (CNPJ 55.744.776/0001-08, Av. Trompowsky 354 Sala 501,
  Centro, Floripa, CEP 88015-300, site autofleetseguros.com.br) com agentes
  clonados dos canônicos: Core ATIVO, Atendimento **desligado** (modo
  observação SPEC-045), nome neutro "Atendente", abertura v2 por variáveis.
- **Resulta** atualizada (Sala 330/Saco Grande, contatos oficiais, site,
  Instagram, LinkedIn em notes; abertura da Joana alinhada ao padrão v2).
- Usuários (senha inicial `mudar123`, bcrypt): Rafael (owner 2x), André
  (admin 2x), Saionara (member Resulta), Regina (member AutoFleet).
  `rafael@gmail.com` → **amandus@autobrokers.digital** (senha intacta),
  owner nas duas corretoras.

## 5. PLANO para validação (não executado)

1. **Equipe no dashboard:** página Equipe da corretora com "Adicionar
   pessoa" (nome, e-mail, função, senha provisória) feita pelo owner/admin —
   sem passar pelo portal admin, sem confirmação de e-mail (opcional depois);
   página "Meu perfil" para o usuário trocar nome/senha/avatar.
2. **Funções e permissões:** 3 papéis simples — Dono (tudo), Gestor (tudo
   menos plano/faturamento), Atendente (Atendimentos + Chat Principal;
   sem Personalização/Custos). `company_members.role` já comporta; aplicar
   como gates nas rotas quando aprovado.
3. **Aprovações pendentes:** hoje o fluxo invite+aprovação é burocrático.
   Proposta: quem o owner adiciona pela Equipe entra direto (já está
   "aprovado por construção"); a página de aprovações do admin fica só para
   cadastros espontâneos (signup público) quando existirem.
4. **Pagamentos:** Stripe segue sandbox; estrutura pronta (plans/subscriptions/
   billing por company). Quando o founder ativar Stripe real: criar planos,
   ligar webhook, e o auto-provisionamento pós-assinatura destrava. Sem
   pendência estrutural.
5. **Admin × Dashboard:** manter o portal admin como visão master; espelhar
   gestão de equipe no dashboard (item 1) e aposentar as telas duplicadas de
   team do admin para company_admin.

## Invioláveis
- company_id NUNCA vem do client — a troca de empresa é validada no servidor.
- Instância GO de uma corretora nunca é tocada pelo setup de outra.
- Observador continua ligado sempre; o toggle só governa respostas do agente.
