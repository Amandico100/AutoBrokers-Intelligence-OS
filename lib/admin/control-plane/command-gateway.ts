// SPEC-061 §5.2 — Admin Command Gateway. Server-only.
//
// Toda escrita administrativa passa por aqui.
//
// Por que um portão único
// -----------------------
// Hoje existem 114 rotas de API no Admin. Cada uma decide sozinha se autentica,
// se verifica papel, se audita. O resultado previsível é que algumas não fazem
// alguma dessas coisas — e ninguém sabe quais, porque descobrir exigiria ler
// 114 arquivos.
//
// Com um portão, a pergunta muda de "esta rota audita?" para "esta rota passa
// pelo Gateway?" — que é verificável por busca de texto e por teste.
//
// O que ele NÃO faz — §5.4
// ------------------------
// Não executa a lógica do domínio. Ele autentica, autoriza, classifica risco,
// chama o serviço canônico e registra o que aconteceu. Suspender uma corretora
// continua sendo função do serviço de corretoras; publicar uma Skill continua
// sendo do Skill Registry. O Gateway é a portaria, não o trabalho.
import 'server-only';
import { esquecerAutoridade, exigirPermissao, type Autoridade } from './authority';

export type Comando<T> = {
  /** Chave estável da ação. Vai para a trilha e é o que se filtra depois. */
  actionKey: string;
  permissionKey: string;
  targetType: string;
  targetId?: string;
  companyId?: string;
  /** Obrigatório em ação crítica — o banco recusa sem ele. */
  reason?: string;
  /** Estado antes, para o diff da trilha. Só o que muda é gravado. */
  antes?: Record<string, unknown>;
  /** O trabalho de verdade. Devolve o novo estado quando houver. */
  executar: (autoridade: Autoridade) => Promise<{ ok: boolean; depois?: Record<string, unknown>; erro?: string; dados?: T }>;
};

export type Recibo<T> = {
  ok: boolean;
  /** Frase que o operador lê. §5.2 item 12: "receipt humano e técnico". */
  mensagem: string;
  dados?: T;
  erro?: string;
  status: number;
  auditoria?: { registrada: boolean; risco: string };
};

function backend(): { url: string; key: string } | null {
  const url = (
    process.env.NEXT_PUBLIC_API_URL ||
    process.env.BACKEND_URL ||
    process.env.NEXT_PUBLIC_BACKEND_URL ||
    ''
  ).replace(/\/+$/, '');
  const key = process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY || '';
  if (!url || !key) return null;
  return { url, key };
}

async function auditar(corpo: Record<string, unknown>): Promise<boolean> {
  const b = backend();
  if (!b) return false;
  try {
    const r = await fetch(`${b.url}/api/admin/control-plane/audit`, {
      method: 'POST',
      headers: { 'X-Internal-Key': b.key, 'Content-Type': 'application/json' },
      body: JSON.stringify(corpo),
      cache: 'no-store',
    });
    return r.ok;
  } catch {
    return false;
  }
}

// As mesmas de `rbac.py`. Duplicadas aqui SÓ para decidir se o motivo é
// obrigatório antes de gastar a chamada — a autoridade continua sendo o
// backend, que recusa de qualquer jeito pelo CHECK do banco. Um teste cobra
// que as duas listas não divirjam.
export const EXIGEM_MOTIVO = new Set([
  'companies.suspend',
  'system.manage',
  'legal.manage',
  'connections.rotate',
  'memory.sensitive.read',
]);

/**
 * Executa uma ação administrativa: autoriza, faz, audita, devolve recibo.
 *
 * A ordem importa. A autorização vem antes de tudo; a auditoria vem depois do
 * resultado — inclusive quando ele é falha. Registrar só o sucesso produziria
 * uma trilha que responde "o que deu certo" e não "o que foi tentado", e a
 * segunda pergunta é a que interessa numa investigação.
 */
export async function executarComando<T>(cmd: Comando<T>): Promise<Recibo<T>> {
  const auth = await exigirPermissao(cmd.permissionKey);
  if (!auth.ok) {
    // Tentativa negada também é evento. É assim que se descobre que alguém
    // está batendo numa porta que não deveria — ou que um papel está apertado
    // demais para o trabalho real.
    await auditar({
      actor_user_id: 'desconhecido',
      action_key: cmd.actionKey,
      permission_key: cmd.permissionKey,
      target_type: cmd.targetType,
      target_id: cmd.targetId ?? null,
      company_id: cmd.companyId ?? null,
      result_status: 'denied',
      result_code: auth.error,
      reason: cmd.reason ?? null,
    });
    return { ok: false, mensagem: auth.motivo, erro: auth.error, status: auth.status };
  }

  const precisaMotivo = EXIGEM_MOTIVO.has(cmd.permissionKey);
  if (precisaMotivo && (cmd.reason ?? '').trim().length < 10) {
    return {
      ok: false,
      status: 400,
      erro: 'reason_required',
      mensagem:
        'Esta ação exige um motivo escrito. Quem ler isto em seis meses precisa entender por que foi feito.',
    };
  }

  let resultado: { ok: boolean; depois?: Record<string, unknown>; erro?: string; dados?: T };
  try {
    resultado = await cmd.executar(auth.autoridade);
  } catch (e) {
    resultado = { ok: false, erro: e instanceof Error ? e.name : 'erro_desconhecido' };
  }

  const registrada = await auditar({
    actor_user_id: auth.autoridade.userId,
    action_key: cmd.actionKey,
    permission_key: cmd.permissionKey,
    target_type: cmd.targetType,
    target_id: cmd.targetId ?? null,
    company_id: cmd.companyId ?? null,
    result_status: resultado.ok ? 'succeeded' : 'failed',
    result_code: resultado.erro ?? null,
    reason: cmd.reason ?? null,
    before: cmd.antes ?? null,
    after: resultado.depois ?? null,
  });

  // Conceder ou revogar papel muda a autoridade da própria pessoa alvo. Sem
  // isto, ela continuaria com o acesso antigo por até 30s — e "revoguei e ele
  // continua entrando" é o tipo de coisa que destrói a confiança no controle.
  if (cmd.actionKey.startsWith('roles.') && cmd.targetId) {
    esquecerAutoridade(cmd.targetId);
  }

  return {
    ok: resultado.ok,
    dados: resultado.dados,
    erro: resultado.erro,
    status: resultado.ok ? 200 : 400,
    mensagem: resultado.ok
      ? 'Feito.'
      : resultado.erro || 'Não foi possível concluir a ação.',
    auditoria: { registrada, risco: precisaMotivo ? 'critical' : 'normal' },
  };
}
