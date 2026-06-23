'use client';

import { useEffect, useState } from 'react';

import { Button } from '@/components/ui/button';
import { Icon } from '@/components/ui/Icon';
import { cn } from '@/lib/utils';
import { icons } from '@/lib/icons';
import { StatusPill } from '@/components/patterns';
import { fetchPermissions, createPermission, deletePermission } from '@/lib/vault/api';
import { actionLabel, actionHelp, actionIsSensitive, subjectLabel } from '@/components/vault/labels';
import type { PermissionGrant } from '@/lib/vault/types';

// Atores que podem usar uma conexão (linguagem humana).
const SUBJECTS = ['autobrokers', 'atendimento', 'tenant_auxiliary'] as const;
// Ações comuns de conector (humanizadas em labels.ts).
const ACTIONS = ['read', 'draft_message', 'test_connection'];

function asActions(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((a): a is string => typeof a === 'string') : [];
}

export function PermissionGrantPanel({ connectionId }: { connectionId: string }) {
  const [items, setItems] = useState<PermissionGrant[] | null>(null);
  const [error, setError] = useState(false);
  const [showForm, setShowForm] = useState(false);
  // Multi-ator: por padrão libera para todos (o que o Founder quer no caso InfoCap).
  const [subjects, setSubjects] = useState<Set<string>>(new Set(SUBJECTS));
  const [actions, setActions] = useState<string[]>(['read']);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState('');

  const load = () => {
    setError(false);
    fetchPermissions(connectionId)
      .then((d) => setItems((d.permissions || []).filter((p) => p.status !== 'revoked')))
      .catch(() => setError(true));
  };

  useEffect(load, [connectionId]);

  const toggleSubject = (s: string) =>
    setSubjects((prev) => { const n = new Set(prev); n.has(s) ? n.delete(s) : n.add(s); return n; });
  const toggleAction = (a: string) =>
    setActions((prev) => (prev.includes(a) ? prev.filter((x) => x !== a) : [...prev, a]));

  // Aprovação humana só é exigida quando há ação sensível selecionada (enviar/alterar).
  const needsApproval = actions.some((a) => actionIsSensitive(a));

  const submit = async () => {
    setSaving(true);
    setFormError('');
    try {
      const chosen = Array.from(subjects);
      if (chosen.length === 0) { setFormError('Escolha quem pode usar.'); setSaving(false); return; }
      // Uma permissão por ator (reusa a API atual), mas o corretor configura tudo de uma vez.
      const results = await Promise.all(
        chosen.map((subject_type) =>
          createPermission(connectionId, {
            subject_type,
            allowed_actions: actions,
            requires_approval: needsApproval,
            risk_level: needsApproval ? 'medium' : 'low',
          }),
        ),
      );
      const failed = results.find((r) => !r.permission);
      if (failed) { setFormError(failed.error || 'Não foi possível salvar.'); }
      else { setShowForm(false); setActions(['read']); setSubjects(new Set(SUBJECTS)); load(); }
    } catch {
      setFormError('Erro ao salvar permissões.');
    } finally {
      setSaving(false);
    }
  };

  // C-FIX-2: revoga todas as grants de um ator de uma vez (limpa a poluição).
  const revokeMany = async (ids: string[]) => {
    await Promise.all(ids.map((id) => deletePermission(connectionId, id)));
    load();
  };

  // Agrega por ator: uma linha por Chat Principal / Atendimento / Auxiliares (sem 7 linhas técnicas).
  const grouped = (() => {
    const map = new Map<string, { actions: Set<string>; ids: string[]; approval: boolean }>();
    for (const p of items ?? []) {
      const g = map.get(p.subject_type) ?? { actions: new Set<string>(), ids: [], approval: false };
      asActions(p.allowed_actions).forEach((a) => g.actions.add(a));
      g.ids.push(p.id);
      if (p.requires_approval) g.approval = true;
      map.set(p.subject_type, g);
    }
    return Array.from(map.entries());
  })();

  return (
    <div className="space-y-3">
      <p className="text-xs text-muted-foreground">
        Defina quem pode usar esta conexão. Conectar não precisa de aprovação — só ações que enviam ou alteram algo pedem confirmação.
      </p>

      {error ? (
        <p className="text-xs text-muted-foreground">Não foi possível carregar as permissões.</p>
      ) : items === null ? (
        <p className="flex items-center gap-2 text-xs text-muted-foreground">
          <Icon icon={icons.renovacao} size={14} className="animate-spin" /> Carregando…
        </p>
      ) : grouped.length === 0 ? (
        <p className="text-xs text-muted-foreground">Ninguém liberado ainda.</p>
      ) : (
        <ul className="space-y-1.5">
          {grouped.map(([subj, g]) => (
            <li key={subj} className="flex flex-wrap items-center gap-2 rounded-lg border border-border-soft px-3 py-2 text-xs">
              <span className="font-medium text-foreground-2">{subjectLabel(subj)}</span>
              {Array.from(g.actions).map((a) => (
                <span key={a} title={actionHelp(a)} className="rounded-full border border-border-soft px-2 py-0.5 text-[11px] text-muted-foreground">
                  {actionLabel(a)}
                </span>
              ))}
              {g.approval && <StatusPill tone="approval" label="confirma antes de agir" />}
              <button onClick={() => revokeMany(g.ids)} className="ml-auto rounded-md border border-border px-2 py-0.5 text-[11px] text-muted-foreground hover:border-danger/40 hover:text-danger">
                Remover acesso
              </button>
            </li>
          ))}
        </ul>
      )}

      {showForm ? (
        <div className="space-y-3 rounded-lg border border-border bg-surface-2 p-3">
          <div className="space-y-1.5">
            <p className="text-[11px] font-medium text-foreground-2">Quem pode usar (pode marcar mais de um)</p>
            <div className="flex flex-wrap gap-1.5">
              {SUBJECTS.map((s) => (
                <button key={s} type="button" onClick={() => toggleSubject(s)}
                  className={cn('rounded-full border px-3 py-1 text-xs transition-colors',
                    subjects.has(s) ? 'border-primary/40 bg-brand-soft text-primary' : 'border-border text-muted-foreground hover:text-foreground')}>
                  {subjectLabel(s)}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-1.5">
            <p className="text-[11px] font-medium text-foreground-2">O que poderão fazer</p>
            <div className="flex flex-col gap-1.5">
              {ACTIONS.map((a) => (
                <button key={a} type="button" onClick={() => toggleAction(a)}
                  className={cn('flex flex-col items-start rounded-lg border px-3 py-1.5 text-left transition-colors',
                    actions.includes(a) ? 'border-primary/40 bg-brand-soft' : 'border-border hover:border-border-strong')}>
                  <span className={cn('text-xs', actions.includes(a) ? 'text-primary' : 'text-foreground-2')}>{actionLabel(a)}</span>
                  <span className="text-[10px] text-faint">{actionHelp(a)}</span>
                </button>
              ))}
            </div>
          </div>

          <p className="text-[11px] text-muted-foreground">
            {needsApproval
              ? 'Inclui uma ação que envia/altera algo: pediremos sua confirmação antes de executar.'
              : 'Apenas leitura/preparação: nenhuma confirmação extra necessária.'}
          </p>

          {formError && <p className="text-xs text-danger">{formError}</p>}

          <div className="flex items-center gap-2">
            <Button size="sm" onClick={submit} disabled={saving || actions.length === 0 || subjects.size === 0}>
              {saving ? 'Salvando…' : 'Salvar'}
            </Button>
            <Button size="sm" variant="outline" onClick={() => setShowForm(false)} disabled={saving}>
              Cancelar
            </Button>
          </div>
        </div>
      ) : (
        <Button size="sm" variant="outline" onClick={() => setShowForm(true)}>
          <Icon icon={icons.novaConversa} size={14} className="mr-2" />
          Liberar acesso
        </Button>
      )}
    </div>
  );
}

export default PermissionGrantPanel;
