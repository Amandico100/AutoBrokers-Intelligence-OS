'use client';

import { useEffect, useState } from 'react';

import { Button } from '@/components/ui/button';
import { Icon } from '@/components/ui/Icon';
import { cn } from '@/lib/utils';
import { icons } from '@/lib/icons';
import { StatusPill } from '@/components/patterns';
import { fetchPermissions, createPermission } from '@/lib/vault/api';
import type { PermissionGrant } from '@/lib/vault/types';

const SUBJECTS: { value: string; label: string }[] = [
  { value: 'autobrokers', label: 'AutoBrokers' },
  { value: 'tenant_auxiliary', label: 'Auxiliar' },
  { value: 'atendimento', label: 'Atendimento' },
];
const ACTIONS = ['read', 'draft_message', 'test_connection'];

function asActions(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((a): a is string => typeof a === 'string') : [];
}

export function PermissionGrantPanel({ connectionId }: { connectionId: string }) {
  const [items, setItems] = useState<PermissionGrant[] | null>(null);
  const [error, setError] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [subject, setSubject] = useState('tenant_auxiliary');
  const [actions, setActions] = useState<string[]>(['read']);
  const [requiresApproval, setRequiresApproval] = useState(true);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState('');

  const load = () => {
    setError(false);
    fetchPermissions(connectionId)
      .then((d) => setItems(d.permissions || []))
      .catch(() => setError(true));
  };

  useEffect(load, [connectionId]);

  const toggle = (a: string) =>
    setActions((prev) => (prev.includes(a) ? prev.filter((x) => x !== a) : [...prev, a]));

  const submit = async () => {
    setSaving(true);
    setFormError('');
    try {
      const res = await createPermission(connectionId, {
        subject_type: subject,
        allowed_actions: actions,
        requires_approval: requiresApproval,
        risk_level: 'medium',
      });
      if (res.permission) {
        setShowForm(false);
        setActions(['read']);
        load();
      } else {
        setFormError(res.error || 'Não foi possível criar a permissão.');
      }
    } catch {
      setFormError('Erro ao criar permissão.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-3">
      <p className="text-xs text-muted-foreground">
        Permissões definem quem pode usar esta conexão. Ações sensíveis continuam exigindo aprovação humana.
      </p>

      {error ? (
        <p className="text-xs text-muted-foreground">Não foi possível carregar as permissões.</p>
      ) : items === null ? (
        <p className="flex items-center gap-2 text-xs text-muted-foreground">
          <Icon icon={icons.renovacao} size={14} className="animate-spin" /> Carregando…
        </p>
      ) : items.length === 0 ? (
        <p className="text-xs text-muted-foreground">Nenhuma permissão ainda.</p>
      ) : (
        <ul className="space-y-1.5">
          {items.map((p) => (
            <li key={p.id} className="flex flex-wrap items-center gap-2 rounded-lg border border-border-soft px-3 py-2 text-xs">
              <span className="font-medium text-foreground-2">{p.subject_type}</span>
              {asActions(p.allowed_actions).map((a) => (
                <span key={a} className="rounded-full border border-border-soft px-2 py-0.5 font-mono text-[10px] text-faint">
                  {a}
                </span>
              ))}
              {p.requires_approval && <StatusPill tone="approval" label="aprovação" />}
            </li>
          ))}
        </ul>
      )}

      {showForm ? (
        <div className="space-y-3 rounded-lg border border-border bg-surface-2 p-3">
          <div className="space-y-1.5">
            <p className="font-mono text-[10px] uppercase tracking-[0.06em] text-faint">Quem pode usar</p>
            <div className="flex flex-wrap gap-1.5">
              {SUBJECTS.map((s) => (
                <button
                  key={s.value}
                  type="button"
                  onClick={() => setSubject(s.value)}
                  className={cn(
                    'rounded-full border px-3 py-1 text-xs transition-colors',
                    subject === s.value ? 'border-primary/40 bg-brand-soft text-primary' : 'border-border text-muted-foreground hover:text-foreground',
                  )}
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-1.5">
            <p className="font-mono text-[10px] uppercase tracking-[0.06em] text-faint">Ações permitidas</p>
            <div className="flex flex-wrap gap-1.5">
              {ACTIONS.map((a) => (
                <button
                  key={a}
                  type="button"
                  onClick={() => toggle(a)}
                  className={cn(
                    'rounded-full border px-3 py-1 font-mono text-[11px] transition-colors',
                    actions.includes(a) ? 'border-primary/40 bg-brand-soft text-primary' : 'border-border text-muted-foreground hover:text-foreground',
                  )}
                >
                  {a}
                </button>
              ))}
            </div>
          </div>

          <label className="flex items-center gap-2 text-xs text-foreground-2">
            <input
              type="checkbox"
              checked={requiresApproval}
              onChange={(e) => setRequiresApproval(e.target.checked)}
              className="h-3.5 w-3.5 accent-[hsl(var(--primary))]"
            />
            Exigir aprovação humana para ações sensíveis
          </label>

          {formError && <p className="text-xs text-danger">{formError}</p>}

          <div className="flex items-center gap-2">
            <Button size="sm" onClick={submit} disabled={saving || actions.length === 0}>
              {saving ? 'Salvando…' : 'Salvar permissão'}
            </Button>
            <Button size="sm" variant="outline" onClick={() => setShowForm(false)} disabled={saving}>
              Cancelar
            </Button>
          </div>
        </div>
      ) : (
        <Button size="sm" variant="outline" onClick={() => setShowForm(true)}>
          <Icon icon={icons.novaConversa} size={14} className="mr-2" />
          Adicionar permissão segura
        </Button>
      )}
    </div>
  );
}

export default PermissionGrantPanel;
