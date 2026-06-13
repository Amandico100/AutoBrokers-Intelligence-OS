'use client';

import { useEffect, useState } from 'react';

import { DetailHeader, StatusPill } from '@/components/patterns';
import { Icon } from '@/components/ui/Icon';
import { icons } from '@/lib/icons';
import {
  CHANNEL_PROVIDER_OPTIONS,
  DESTINATION_REF_PLACEHOLDER,
  DESTINATION_TYPE_OPTIONS,
  channelProviderLabel,
  destinationTypeLabel,
} from '@/lib/attendance/support-destination-labels';

type Destination = {
  id: string;
  name: string;
  destination_type: string;
  channel_provider: string;
  tenant_connection_id: string | null;
  display_ref: string | null;
  is_primary: boolean;
  priority_order: number;
  fallback_enabled: boolean;
  silence_minutes: number;
  active_hours: Record<string, unknown>;
  escalation_rules: unknown[];
  metadata: Record<string, unknown>;
  is_active: boolean;
  has_destination_ref?: boolean;
  created_at: string | null;
  updated_at: string | null;
};

const EMPTY_FORM = {
  name: '',
  destination_type: 'whatsapp_group',
  channel_provider: 'manual',
  destination_ref: '',
  is_primary: false,
  priority_order: 100,
  fallback_enabled: false,
  silence_minutes: 0,
  is_active: true,
};
type FormState = typeof EMPTY_FORM;

const EXAMPLE: Partial<FormState> = {
  name: 'Suporte humano principal',
  destination_type: 'whatsapp_group',
  channel_provider: 'manual',
  destination_ref: '120363422850006552@g.us',
  is_primary: true,
  priority_order: 1,
  fallback_enabled: true,
  silence_minutes: 15,
};

export default function HumanSupportSettingsClient() {
  const [items, setItems] = useState<Destination[] | null>(null);
  const [error, setError] = useState(false);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [notice, setNotice] = useState('');
  const [formError, setFormError] = useState('');

  const load = async () => {
    setError(false);
    try {
      const res = await fetch('/api/attendance/support-destinations?active=all');
      if (!res.ok) throw new Error('fetch failed');
      const data = await res.json();
      setItems(data.destinations || []);
    } catch {
      setError(true);
      setItems(null);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const setF = (patch: Partial<FormState>) => setForm((f) => ({ ...f, ...patch }));

  const resetForm = () => {
    setForm(EMPTY_FORM);
    setEditingId(null);
    setFormError('');
  };

  const startEdit = (d: Destination) => {
    setEditingId(d.id);
    setFormError('');
    setForm({
      name: d.name,
      destination_type: d.destination_type,
      channel_provider: d.channel_provider,
      destination_ref: '', // API não retorna o valor cru; ref em branco = manter
      is_primary: d.is_primary,
      priority_order: d.priority_order,
      fallback_enabled: d.fallback_enabled,
      silence_minutes: d.silence_minutes,
      is_active: d.is_active,
    });
  };

  const submit = async () => {
    setFormError('');
    if (!form.name.trim()) {
      setFormError('Informe um nome para o destino.');
      return;
    }
    if (!editingId && !form.destination_ref.trim()) {
      setFormError('Informe o destino (número, grupo, e-mail ou URL).');
      return;
    }
    setSaving(true);
    try {
      const url = editingId
        ? `/api/attendance/support-destinations/${editingId}`
        : '/api/attendance/support-destinations';
      const method = editingId ? 'PATCH' : 'POST';

      const base: Record<string, unknown> = {
        name: form.name.trim(),
        destination_type: form.destination_type,
        channel_provider: form.channel_provider,
        is_primary: form.is_primary,
        priority_order: Number.isFinite(form.priority_order) ? form.priority_order : 100,
        fallback_enabled: form.fallback_enabled,
        silence_minutes: Number.isFinite(form.silence_minutes) ? form.silence_minutes : 0,
        is_active: form.is_active,
      };
      if (form.destination_ref.trim()) base.destination_ref = form.destination_ref.trim();
      if (!editingId) {
        base.active_hours = {};
        base.escalation_rules = [];
        base.metadata = { source: 'dashboard' };
      }

      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(base),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setFormError(data.error || 'Não foi possível salvar.');
        return;
      }
      setNotice(editingId ? 'Destino atualizado.' : 'Destino criado.');
      resetForm();
      await load();
    } catch {
      setFormError('Erro ao salvar o destino.');
    } finally {
      setSaving(false);
    }
  };

  const disable = async (d: Destination) => {
    if (!window.confirm(`Desativar o destino "${d.name}"?`)) return;
    setDeletingId(d.id);
    setNotice('');
    try {
      const res = await fetch(`/api/attendance/support-destinations/${d.id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('delete failed');
      setNotice('Destino desativado.');
      if (editingId === d.id) resetForm();
      await load();
    } catch {
      setNotice('Não foi possível desativar o destino.');
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-3xl space-y-5 px-4 py-8 sm:px-6">
        <DetailHeader
          icon={icons.atendimentos}
          title="Suporte humano"
          subtitle="Configure para onde o agente deve transferir o dossiê quando não conseguir resolver um atendimento."
          breadcrumb={[
            { label: 'Personalização', href: '/dashboard/personalizacao' },
            { label: 'Corretora', href: '/dashboard/personalizacao/corretora' },
            { label: 'Suporte humano' },
          ]}
          status={{ tone: 'info', label: 'MVP ativo · sem envio real' }}
          actions={
            <button
              onClick={load}
              className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface-2 px-3 py-1.5 text-xs font-medium text-foreground hover:bg-surface-2/70"
            >
              <Icon icon={icons.renovacao} size={14} /> Atualizar
            </button>
          }
        />

        <div className="rounded-lg border border-warning/30 bg-warning/5 px-3 py-2 text-xs text-warning">
          Neste MVP, o destino humano será usado para preparar e copiar dossiês. Nenhuma mensagem é enviada
          automaticamente.
        </div>

        {notice && (
          <div className="flex items-center justify-between gap-2 rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground">
            <span>{notice}</span>
            <button onClick={() => setNotice('')} className="text-muted-foreground hover:text-foreground">
              <Icon icon={icons.negado} size={14} />
            </button>
          </div>
        )}

        {/* Formulário criar/editar */}
        <section className="rounded-xl border border-border bg-card p-4">
          <div className="mb-3 flex items-center justify-between">
            <p className="text-sm font-medium text-foreground">
              {editingId ? 'Editar destino' : 'Novo destino'}
            </p>
            <div className="flex items-center gap-2">
              {!editingId && (
                <button
                  onClick={() => setForm((f) => ({ ...EMPTY_FORM, ...EXAMPLE } as FormState))}
                  className="text-xs text-primary hover:underline"
                >
                  Preencher exemplo
                </button>
              )}
              {editingId && (
                <button onClick={resetForm} className="text-xs text-muted-foreground hover:text-foreground">
                  Cancelar edição
                </button>
              )}
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <label className="space-y-1 text-sm sm:col-span-2">
              <span className="text-foreground">Nome</span>
              <input
                value={form.name}
                onChange={(e) => setF({ name: e.target.value })}
                placeholder="Suporte humano principal"
                className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-primary/50 focus:outline-none"
              />
            </label>

            <label className="space-y-1 text-sm">
              <span className="text-foreground">Tipo de destino</span>
              <select
                value={form.destination_type}
                onChange={(e) => setF({ destination_type: e.target.value })}
                className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-primary/50 focus:outline-none"
              >
                {DESTINATION_TYPE_OPTIONS.map((t) => (
                  <option key={t} value={t}>
                    {destinationTypeLabel(t)}
                  </option>
                ))}
              </select>
            </label>

            <label className="space-y-1 text-sm">
              <span className="text-foreground">Provider</span>
              <select
                value={form.channel_provider}
                onChange={(e) => setF({ channel_provider: e.target.value })}
                className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-primary/50 focus:outline-none"
              >
                {CHANNEL_PROVIDER_OPTIONS.map((p) => (
                  <option key={p} value={p}>
                    {channelProviderLabel(p)}
                  </option>
                ))}
              </select>
            </label>

            <label className="space-y-1 text-sm sm:col-span-2">
              <span className="text-foreground">
                {editingId ? 'Novo destino / ref (opcional)' : 'Destino / ref'}
              </span>
              <input
                value={form.destination_ref}
                onChange={(e) => setF({ destination_ref: e.target.value })}
                placeholder={DESTINATION_REF_PLACEHOLDER[form.destination_type] || ''}
                className="w-full rounded-md border border-border bg-background px-3 py-2 font-mono text-xs text-foreground focus:border-primary/50 focus:outline-none"
              />
              {editingId && (
                <span className="text-[11px] text-muted-foreground">
                  Deixe em branco para manter o destino atual (o valor não é exibido por segurança).
                </span>
              )}
            </label>

            <label className="space-y-1 text-sm">
              <span className="text-foreground">Ordem de prioridade</span>
              <input
                type="number"
                min={0}
                value={form.priority_order}
                onChange={(e) => setF({ priority_order: parseInt(e.target.value || '0', 10) })}
                className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-primary/50 focus:outline-none"
              />
            </label>

            <label className="space-y-1 text-sm">
              <span className="text-foreground">Silêncio entre alertas (min)</span>
              <input
                type="number"
                min={0}
                value={form.silence_minutes}
                onChange={(e) => setF({ silence_minutes: parseInt(e.target.value || '0', 10) })}
                className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-primary/50 focus:outline-none"
              />
            </label>

            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={form.is_primary}
                onChange={(e) => setF({ is_primary: e.target.checked })}
                className="h-4 w-4 accent-[hsl(var(--primary))]"
              />
              <span className="text-foreground">Destino principal</span>
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={form.fallback_enabled}
                onChange={(e) => setF({ fallback_enabled: e.target.checked })}
                className="h-4 w-4 accent-[hsl(var(--primary))]"
              />
              <span className="text-foreground">Usar como fallback</span>
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(e) => setF({ is_active: e.target.checked })}
                className="h-4 w-4 accent-[hsl(var(--primary))]"
              />
              <span className="text-foreground">Ativo</span>
            </label>
          </div>

          {formError && <p className="mt-3 text-sm text-destructive">{formError}</p>}

          <div className="mt-4 flex justify-end gap-2">
            {editingId && (
              <button
                onClick={resetForm}
                className="rounded-lg border border-border bg-surface-2 px-4 py-2 text-sm font-medium text-foreground hover:bg-surface-2/70"
              >
                Cancelar
              </button>
            )}
            <button
              onClick={submit}
              disabled={saving}
              className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-60"
            >
              {saving ? 'Salvando…' : editingId ? 'Salvar' : 'Criar destino'}
            </button>
          </div>
        </section>

        {/* Lista de destinos */}
        <section className="space-y-2">
          <p className="text-sm font-medium text-foreground">Destinos cadastrados</p>
          {error ? (
            <div className="rounded-xl border border-border bg-card p-8 text-center text-sm text-muted-foreground">
              Não foi possível carregar os destinos.{' '}
              <button onClick={load} className="text-primary hover:underline">
                Tentar novamente
              </button>
              .
            </div>
          ) : items === null ? (
            <div className="flex items-center justify-center gap-2 rounded-xl border border-border bg-card p-8 text-sm text-muted-foreground">
              <Icon icon={icons.renovacao} size={16} className="animate-spin" /> Carregando…
            </div>
          ) : items.length === 0 ? (
            <div className="rounded-xl border border-border bg-card p-8 text-center text-sm text-muted-foreground">
              Nenhum destino configurado ainda. Crie o primeiro acima.
            </div>
          ) : (
            <ul className="space-y-2">
              {items.map((d) => (
                <li key={d.id} className="rounded-xl border border-border bg-card p-3">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <p className="text-sm font-medium text-foreground">{d.name}</p>
                      <p className="mt-0.5 font-mono text-[11px] text-muted-foreground">
                        {d.display_ref || (d.has_destination_ref ? 'destino configurado' : '—')}
                      </p>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <button
                        onClick={() => startEdit(d)}
                        className="rounded-lg border border-border bg-surface-2 px-2.5 py-1 text-xs font-medium text-foreground hover:bg-surface-2/70"
                      >
                        Editar
                      </button>
                      <button
                        onClick={() => disable(d)}
                        disabled={deletingId === d.id || !d.is_active}
                        className="rounded-lg border border-danger/40 bg-danger/5 px-2.5 py-1 text-xs font-medium text-danger hover:bg-danger/10 disabled:opacity-50"
                      >
                        {deletingId === d.id ? 'Desativando…' : 'Desativar'}
                      </button>
                    </div>
                  </div>
                  <div className="mt-2 flex flex-wrap items-center gap-1.5">
                    <StatusPill tone="neutral" label={destinationTypeLabel(d.destination_type)} />
                    <StatusPill tone="neutral" label={channelProviderLabel(d.channel_provider)} />
                    {d.is_primary && <StatusPill tone="info" label="Principal" />}
                    {d.fallback_enabled && <StatusPill tone="neutral" label="Fallback" />}
                    <StatusPill tone={d.is_active ? 'success' : 'neutral'} label={d.is_active ? 'Ativo' : 'Inativo'} />
                    {d.silence_minutes > 0 && (
                      <span className="rounded-full border border-border px-2 py-0.5 text-[10px] text-muted-foreground">
                        silêncio {d.silence_minutes} min
                      </span>
                    )}
                    <span className="rounded-full border border-border px-2 py-0.5 text-[10px] text-muted-foreground">
                      prioridade {d.priority_order}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}
