# SPEC-048 — Isolamento real entre corretoras, variáveis vivas e Equipe no dashboard

> Executada em 21/07/2026 após o founder reportar: dados de uma corretora
> vazando na outra ao editar, "Joana" congelada na mensagem de abertura, e a
> impossibilidade de gerir a equipe pelo dashboard. Também é a execução do
> plano da SPEC-047 §5 (liberado: "PODE EXECUTAR").

## 1. Causa-raiz do vazamento (bug GRAVE, corrigido)

Existiam DOIS seams de autorização tenant: `resolveSessionCompany`
(multi-empresa desde a SPEC-047) e `requireCompanyMember` (lib/admin/
admin-auth.ts) — este segundo resolvia a empresa por `users_v2.company_id`
(primária) e IGNORAVA o seletor. As 15 rotas que passam por ele (dados da
corretora, agente, conhecimento, equipe, uso, corredores, auxiliares…)
liam/gravavam SEMPRE na primária: com a AutoFleet ativa, editar "Dados da
corretora" sobrescreveu a Resulta com os dados da AutoFleet.

**Fix:** `requireCompanyMember` agora honra `session.activeCompanyId`,
validando o vínculo em `company_members` A CADA request e usando papel/
is_owner DO VÍNCULO daquela empresa (o mesmo usuário pode ser dono numa e
membro na outra). Sem vínculo → 403. `/api/user/profile` também passou a
mostrar a empresa ATIVA. **Dados da Resulta restaurados no banco** (CNPJ
12.542.146/0001-48, Square SC, contatos oficiais).

## 2. Variáveis vivas (nunca mais nome congelado)

O formulário do agente recebia o texto RENDERIZADO (ex.: "Sou Joana...") e o
salvava de volta literal — congelando o nome. Agora:
- `sanitizeAgentConfigForDashboard` entrega aos campos o valor **CRU** salvo
  (com `{{attendant_name}}`/`{{company_name}}`) + um objeto `preview` com as
  versões renderizadas SÓ para exibição;
- a "Apresentação" usa o preview; os campos editam o template; dica de
  variáveis visível sob abertura/encerramento;
- aberturas das duas corretoras normalizadas no banco para a forma variável
  (attendant_name da Resulta mantido "Saionara", escolha do founder).

## 3. Equipe no dashboard (plano §5.1 executado)

- `getTeam` lista pelos **vínculos** (`company_members`): donos aparecem nas
  duas corretoras; atendentes só na própria; papel exibido é o do vínculo.
- `/api/dashboard/team` ganhou POST/PATCH/DELETE: adicionar pessoa (usuário
  novo com senha provisória, sem confirmação de e-mail — ou só o vínculo, se
  o e-mail já existe), editar nome/celular/papel/senha, remover **o vínculo**
  (a conta continua existindo para a outra corretora). Escritas exigem papel
  administrativo DA empresa ativa; dono não é rebaixado por gestor nem
  removido por aqui; ninguém remove a si mesmo.
- TeamClient: botão "Adicionar pessoa" + clique no membro abre modal com
  dados (e-mail, celular, papel, último acesso) e ações de admin. Membro
  comum só visualiza.

## 4. O que já estava certo (verificado)

- Pareamento WhatsApp usa `resolveSessionCompany` → já era por empresa ativa;
  com o GO multi-instância (SPEC-047), Saionara pareia a Resulta e Regina a
  AutoFleet sem se tocarem.
- Portal admin (master) lê `companies`/`users_v2` direto — os dados corrigidos
  aparecem lá; a listagem "Todos os usuários" mostra cada um na sua empresa
  primária (donos multi-empresa aparecem 1x — evolução futura, não bug).

## Invioláveis
- Papel e empresa NUNCA vêm do client; vínculo validado por request.
- Remover da equipe remove o vínculo, nunca a conta global.
- Novos usuários criados pela Equipe nascem SEM is_owner.
