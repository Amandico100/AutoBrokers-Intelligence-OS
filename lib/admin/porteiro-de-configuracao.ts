// SPEC-EXTRA-001.3 — BLOCO G · o porteiro das rotas que MUDAM a configuração
// da corretora.
//
// 📊 O DEFEITO, MEDIDO EM 16/09/2026. Seis mutações do painel — as três de
// `support-destinations`, as duas de `portal-credentials` e o POST de
// `whatsapp-channel` (que carrega SEIS ações num `body.action`) — não chamavam
// `requireCompanyMember`, não chamavam `assertSameOrigin` e não escreviam
// auditoria. Um `member` comum conseguia:
//
//   · redirecionar o dossiê (que leva CPF do segurado) para um destino próprio
//   · deixar a corretora SEM destino — e os handoffs param de chegar a alguém
//   · trocar ou apagar a credencial de portal da corretora
//   · desconectar o WhatsApp de atendimento
//
// 🔴 E NÃO ERA ESQUECIMENTO PONTUAL: nenhum dos dois resolvedores que essas
// rotas usavam devolve PAPEL. `resolveSessionCompany` devolve
// `{userId, companyId}`; `companyIdDoSeletor` devolve `string | null`. A rota
// não tinha o papel disponível NEM SE QUISESSE checá-lo — é causa estrutural.
// Por isso o conserto é trocar o resolvedor, não acrescentar um `if`.
//
// ⛔ Este arquivo NÃO é um motor de autorização novo (CLAUDE.md §5): ele é um
// adaptador de três linhas sobre `requireCompanyMember` + `assertSameOrigin` +
// `writeAudit`, que já são a autoridade. O padrão literal que ele embrulha
// está em `app/api/dashboard/team/route.ts:46-50`.
//
// ⚠️ `requireCompanyMember({ write: true })` exige `canWriteTenantConfig` =
// `owner | admin | admin_company | master_admin`. 📊 Medido em 16/09 sobre
// produção: `admin_company` 8 (4 com `is_owner`) · `member` 2. Quem hoje mexe
// nessas telas nas duas pilotos é `admin_company` — a trava NÃO tira o acesso
// de ninguém que já o usa. A linha está na Caixa do Founder mesmo assim.
import { NextResponse } from 'next/server';
import type { SupabaseClient } from '@supabase/supabase-js';

import { requireCompanyMember, assertSameOrigin } from '@/lib/admin/admin-auth';
import { writeAudit } from '@/lib/vault/server';

export type PorteiroOk = {
  companyId: string;
  userId: string;
  role: string | null;
  isOwner: boolean;
  supabase: SupabaseClient;
};

type ComHeaders = { headers: { get(name: string): string | null } };

/**
 * Origem + papel administrativo DA corretora ativa, nesta ordem.
 *
 * Devolve `NextResponse` quando barra (403/401) — o chamador só precisa de
 * `if (porteiro instanceof NextResponse) return porteiro;`.
 *
 * 🔴 `companyId` sai daqui e de mais lugar nenhum. ⛔ Nunca o `company_id` do
 * corpo da requisição: é exatamente assim que um IDOR entra.
 */
export async function porteiroDeConfiguracao(req: ComHeaders): Promise<PorteiroOk | NextResponse> {
  const xo = assertSameOrigin(req);
  if (xo) return NextResponse.json({ error: xo.error }, { status: xo.status });

  const auth = await requireCompanyMember({ write: true });
  if (!auth.ok) return NextResponse.json({ error: auth.error }, { status: auth.status });

  return {
    companyId: auth.ctx.companyId,
    userId: auth.ctx.userId,
    role: auth.ctx.role,
    isOwner: auth.ctx.isOwner,
    supabase: auth.supabase,
  };
}

/**
 * Uma linha em `vault_audit_log` com QUEM fez. Best-effort — auditoria que
 * falha não pode derrubar a operação, mas operação sem auditoria é mudança de
 * configuração sem dono.
 *
 * ⛔ `metadata` nunca leva senha, `destination_ref` cru nem telefone inteiro.
 */
export async function registrarNaAuditoria(
  porteiro: PorteiroOk,
  entrada: { evento: string; acao: string; status?: string; metadata?: Record<string, unknown> },
): Promise<void> {
  await writeAudit(porteiro.supabase, {
    company_id: porteiro.companyId,
    event_type: entrada.evento,
    action: entrada.acao,
    status: entrada.status ?? 'ok',
    actor_user_id: porteiro.userId,
    metadata: entrada.metadata ?? {},
  });
}
