// SPEC-013 B1 (PURO, testável) — regras de publicação de Auxiliar Global a partir de
// Source Agent do Studio + lifecycle de instalação por tenant. Reusa o motor existente
// (SPEC-002: auxiliary_templates.default_config.runtime + tenant_auxiliaries.config.runtime).

/** Só Source Agent do Blueprint Studio marcado como global_auxiliary pode virar Auxiliar Global.
 *  Core/Even (global_core/global_attendance) e source_subagent NUNCA podem. */
export function canPublishAgentAsGlobalAuxiliary(p: { companyKind: string | null; studioSourceKind: string | null }): boolean {
  return p.companyKind === 'platform_blueprint_studio' && p.studioSourceKind === 'global_auxiliary';
}

/** Motivo legível do bloqueio (para UI/erros). */
export function publishBlockReason(p: { companyKind: string | null; studioSourceKind: string | null }): string | null {
  if (p.companyKind !== 'platform_blueprint_studio') return 'fonte_precisa_ser_studio';
  if (p.studioSourceKind === 'global_core' || p.studioSourceKind === 'global_attendance') return 'core_ou_even_nao_publicavel';
  if (p.studioSourceKind === 'source_subagent') return 'subagent_nao_publicavel';
  if (p.studioSourceKind !== 'global_auxiliary') return 'fonte_precisa_ser_global_auxiliary';
  return null;
}

// --- Lifecycle de tenant_auxiliaries (status honesto) --------------------------
/**
 * 🔴 CORRIGIDO EM 17/08/2026, depois que o botão "Ligar este Auxiliar" devolveu
 * `acao_invalida` na tela do Founder. O defeito era meu, e é a MESMA doença uma
 * camada acima.
 *
 * 📊 O que acontecia: a Cobrança Feita da Resulta está `inactive` no banco. O
 * botão manda `resume`. A regra dizia `resume` só a partir de `paused` — e
 * `inactive` não estava em lugar nenhum desta máquina de estados. Resultado:
 * `null` → `acao_invalida` → um Auxiliar instalado que não podia ser ligado.
 *
 * A origem é rastreável: o vocabulário abaixo era o do TYPESCRIPT
 * (`awaiting_runtime`, `uninstalled`, `error`), e o CHECK do banco fala outro
 * (`inactive`, `active`, `paused`, `disabled`, `archived`). Eu fiz
 * `statusValidoNoBanco()` traduzir na hora de ESCREVER — e esqueci que quem LÊ
 * o status de volta é esta função, que continuou falando a língua antiga.
 *
 *     escrita  →  traduzida para o banco       ✅ (feito antes)
 *     leitura  →  interpretada na língua velha ❌ (o defeito)
 *
 * Agora a máquina fala a língua do BANCO, que é a autoridade, e aceita os
 * termos antigos apenas na ENTRADA — para não quebrar chamador que ainda os
 * use. Uma tradução só, num lugar só.
 */
export type TenantAuxStatus = 'inactive' | 'active' | 'paused' | 'disabled' | 'archived';

/** 📊 O CHECK `tenant_auxiliaries_status_check`, lido do banco em 17/08/2026. */
export const TENANT_AUX_STATES: TenantAuxStatus[] = ['inactive', 'active', 'paused', 'disabled', 'archived'];

/** O vocabulário histórico do TypeScript, aceito na entrada e traduzido. */
const TERMOS_ANTIGOS: Record<string, TenantAuxStatus> = {
  awaiting_runtime: 'inactive',   // instalado, ainda não pode trabalhar
  uninstalled: 'archived',        // saiu de cena, sem apagar histórico
  error: 'disabled',              // não deve rodar até alguém olhar
};

/** Normaliza qualquer status para a língua do banco. */
export function statusCanonico(bruto: string | null | undefined): TenantAuxStatus {
  const s = String(bruto || '').trim().toLowerCase();
  if ((TENANT_AUX_STATES as string[]).includes(s)) return s as TenantAuxStatus;
  return TERMOS_ANTIGOS[s] ?? 'inactive';   // desconhecido nunca nasce ligado
}

export type TenantAuxAction = 'pause' | 'resume' | 'uninstall';

/** Estados de onde LIGAR faz sentido: instalado e parado, por qualquer motivo. */
const PODE_LIGAR: TenantAuxStatus[] = ['inactive', 'paused', 'disabled'];
/** Estados de onde PAUSAR faz sentido: só de quem está trabalhando. */
const PODE_PAUSAR: TenantAuxStatus[] = ['active'];

/** Próximo status a partir da ação (puro). null = ação inválida para o status atual. */
export function nextTenantAuxStatus(
  current: TenantAuxStatus | string | null | undefined,
  action: TenantAuxAction,
): TenantAuxStatus | null {
  const atual = statusCanonico(current);
  // Arquivado saiu de cena: não pausa, não liga, não desinstala de novo.
  if (atual === 'archived') return null;
  if (action === 'pause') return PODE_PAUSAR.includes(atual) ? 'paused' : null;
  if (action === 'resume') return PODE_LIGAR.includes(atual) ? 'active' : null;
  if (action === 'uninstall') return 'archived';
  return null;
}

/** Rótulo honesto para a UI tenant. */
export function tenantAuxStatusLabel(status: string | null | undefined): string {
  switch (statusCanonico(status)) {
    case 'active': return 'Pronto';
    case 'paused': return 'Pausado';
    case 'inactive': return 'Instalado, desligado';
    case 'disabled': return 'Desativado — precisa de atenção';
    case 'archived': return 'Removido';
    default: return 'Instalado';
  }
}
