// ===========================================================================
// O HISTÓRICO DO BOTÃO — quem ligou, quem desligou, e quando
// ===========================================================================
//
// 🔴 POR QUE ESTE ARQUIVO EXISTE (09/09/2026)
//
// 📊 Hoje o único vestígio de um liga/desliga é `agents.desligado_em` — **a
// última vez**, e só quando o estado é "desligado" (religar LIMPA a coluna).
// Investigar um dia de piloto com isso é inferência: não dá para saber se o
// agente passou a manhã fora, quem o desligou, nem quantas vezes.
//
// ⚠️ E a pergunta que vai ser feita é a mais simples de todas: *"o agente
// estava ligado às 14h?"*. Uma linha por clique responde; uma coluna com a
// última data, não.
//
// ⛔ NENHUMA TABELA NOVA. `agent_activities` já é o feed durável e legível da
// corretora (SPEC-036) — company_id, category, title, detail, created_at — e já
// tem tela (`/dashboard/atividades`) e RLS. Criar um `agent_toggle_log` ao lado
// seria motor paralelo (CLAUDE.md §5).
//
// 🔴 BEST-EFFORT, E É DELIBERADO: falhar em registrar **não pode** desfazer um
// toggle que já aconteceu. Mas sai no `console.error`, porque um histórico que
// silenciosamente não grava é pior que histórico nenhum.
import type { SupabaseClient } from '@supabase/supabase-js';

/** O feed é comercial; esta linha é de atendimento. Ver `CATEGORIES` em
 *  `backend/app/services/activity_log.py`. */
export const CATEGORIA_DO_BOTAO = 'atendimentos';

/**
 * A frase que a corretora lê no feed. PURA — é ela que o gate testa.
 *
 * ⚠️ Linguagem humana, e com NOME PRÓPRIO de propósito: o feed de Atividades
 * fala em papéis ("o agente", "a equipe") porque descreve trabalho do robô.
 * Esta linha descreve uma decisão de UMA PESSOA da corretora, e *"alguém
 * desligou o agente às 9h"* não responde a pergunta que vai ser feita.
 * ⛔ O escopo continua sendo o da própria corretora (`company_id`) — nenhum
 * nome atravessa tenant.
 */
export function fraseDoBotao(p: { nome: string; ligou: boolean; corretora: string }): {
  title: string; detail: string;
} {
  const nome = (p.nome || '').trim() || 'Alguém da equipe';
  const corretora = (p.corretora || '').trim() || 'corretora';
  return p.ligou
    ? {
        title: `${nome} ligou o agente de atendimento`,
        detail: `O agente voltou a responder os segurados no WhatsApp da ${corretora}.`,
      }
    : {
        title: `${nome} desligou o agente de atendimento`,
        detail: `O agente parou de responder na ${corretora}: a equipe humana atende `
          + 'pelo celular e o sistema segue observando e aprendendo.',
      };
}

/** Nome legível de quem clicou. Nunca lança: sem nome, a linha ainda vale. */
async function nomeDeQuemClicou(supabase: SupabaseClient, userId: string): Promise<string> {
  if (!userId) return '';
  try {
    const { data } = await supabase.from('users_v2')
      .select('first_name, last_name').eq('id', userId).maybeSingle();
    const nome = [data?.first_name, data?.last_name].filter(Boolean).join(' ').trim();
    return nome;
  } catch { return ''; }
}

async function nomeDaCorretora(supabase: SupabaseClient, companyId: string): Promise<string> {
  try {
    const { data } = await supabase.from('companies')
      .select('company_name').eq('id', companyId).maybeSingle();
    return (data?.company_name as string | null) ?? '';
  } catch { return ''; }
}

/**
 * Grava UMA linha durável de liga/desliga em `agent_activities`.
 *
 * 🔴 Só na TRANSIÇÃO. Um clique em `ligar` num agente já ligado não é evento —
 * é a mesma regra que governa `agents.desligado_em`, e registrar mesmo assim
 * encheria o feed de linhas que não aconteceram.
 */
export async function registrarBotaoDoAgente(
  supabase: SupabaseClient,
  p: { companyId: string; userId: string; ligou: boolean },
): Promise<{ ok: boolean; title?: string; error?: string }> {
  try {
    const [nome, corretora] = await Promise.all([
      nomeDeQuemClicou(supabase, p.userId),
      nomeDaCorretora(supabase, p.companyId),
    ]);
    const { title, detail } = fraseDoBotao({ nome, ligou: p.ligou, corretora });
    const { error } = await supabase.from('agent_activities').insert({
      company_id: p.companyId,
      category: CATEGORIA_DO_BOTAO,
      title: title.slice(0, 180),
      detail: detail.slice(0, 400),
    });
    if (error) {
      console.error('[AGENTS] historico do botao NAO gravado:', error.message);
      return { ok: false, error: 'insert_failed' };
    }
    return { ok: true, title };
  } catch (e) {
    console.error('[AGENTS] historico do botao NAO gravado:', e);
    return { ok: false, error: 'excecao' };
  }
}
