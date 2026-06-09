'use client';

import { useEffect, useState } from 'react';
import { Plus, Edit2, X, Power, Download, Building2, Check } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

type Template = {
  id: string;
  slug: string;
  name: string;
  [key: string]: unknown;
};

type Company = { id: string; company_name?: string };
type Installation = { id: string; company_id: string; company_name: string; status?: string; created_at?: string | null };

const emptyForm = {
  name: '',
  slug: '',
  category: '',
  short_description: '',
  description: '',
  icon: '',
  status: 'active',
  execution_mode: 'manual',
  trigger_type: 'manual',
  requires_human_approval: true,
  uses_external_actions: false,
  is_active: true,
  system_prompt: '',
  default_config: '',
  permissions: '',
  input_schema: '',
  output_schema: '',
};
type FormData = typeof emptyForm;

function str(v: unknown): string {
  return typeof v === 'string' ? v : '';
}
function jsonStr(v: unknown): string {
  return v && typeof v === 'object' ? JSON.stringify(v, null, 2) : '';
}
function isActive(t: Template): boolean {
  return t.is_active !== false;
}

export default function AdminAuxiliaresPage() {
  const [templates, setTemplates] = useState<Template[] | null>(null);
  const [error, setError] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Template | null>(null);
  const [form, setForm] = useState<FormData>(emptyForm);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState('');
  const [notice, setNotice] = useState('');

  const [installFor, setInstallFor] = useState<Template | null>(null);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [installCompanyId, setInstallCompanyId] = useState('');
  const [installStatus, setInstallStatus] = useState('active');
  const [installing, setInstalling] = useState(false);
  const [installError, setInstallError] = useState('');

  const [installationsFor, setInstallationsFor] = useState<Template | null>(null);
  const [installations, setInstallations] = useState<Installation[] | null>(null);

  const load = () => {
    setError('');
    fetch('/api/admin/auxiliaries/templates')
      .then((r) => r.json())
      .then((d) => setTemplates(d.templates || []))
      .catch(() => setError('Não foi possível carregar os templates.'));
  };
  useEffect(load, []);

  const openCreate = () => {
    setEditing(null);
    setForm(emptyForm);
    setFormError('');
    setShowForm(true);
  };

  const openEdit = (t: Template) => {
    setEditing(t);
    setForm({
      name: t.name,
      slug: t.slug,
      category: str(t.category),
      short_description: str(t.short_description),
      description: str(t.description),
      icon: str(t.icon),
      status: str(t.status) || 'active',
      execution_mode: str(t.execution_mode) || 'manual',
      trigger_type: str(t.trigger_type) || 'manual',
      requires_human_approval: t.requires_human_approval !== false,
      uses_external_actions: t.uses_external_actions === true,
      is_active: isActive(t),
      system_prompt: str(t.system_prompt),
      default_config: jsonStr(t.default_config),
      permissions: jsonStr(t.permissions),
      input_schema: jsonStr(t.input_schema),
      output_schema: jsonStr(t.output_schema),
    });
    setFormError('');
    setShowForm(true);
  };

  const save = async () => {
    setSaving(true);
    setFormError('');
    try {
      const url = editing
        ? `/api/admin/auxiliaries/templates/${editing.id}`
        : '/api/admin/auxiliaries/templates';
      const method = editing ? 'PATCH' : 'POST';
      const payload: Record<string, unknown> = { ...form };
      if (editing) delete payload.slug;
      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok && data.template) {
        setShowForm(false);
        setNotice(editing ? 'Template atualizado.' : 'Template criado.');
        load();
      } else {
        setFormError(data.error || 'Não foi possível salvar.');
      }
    } catch {
      setFormError('Erro ao salvar o template.');
    } finally {
      setSaving(false);
    }
  };

  const toggleActive = async (t: Template) => {
    setNotice('');
    try {
      const res = await fetch(`/api/admin/auxiliaries/templates/${t.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_active: !isActive(t) }),
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok) load();
      else setNotice(data.error || 'Não foi possível alterar o status.');
    } catch {
      setNotice('Erro ao alterar status.');
    }
  };

  const openInstall = (t: Template) => {
    setInstallFor(t);
    setInstallCompanyId('');
    setInstallStatus('active');
    setInstallError('');
    if (companies.length === 0) {
      fetch('/api/admin/companies')
        .then((r) => r.json())
        .then((d) => setCompanies(d.companies || []))
        .catch(() => setInstallError('Não foi possível carregar as corretoras.'));
    }
  };

  const submitInstall = async () => {
    if (!installFor) return;
    if (!installCompanyId) {
      setInstallError('Selecione uma corretora.');
      return;
    }
    setInstalling(true);
    setInstallError('');
    try {
      const res = await fetch(`/api/admin/auxiliaries/templates/${installFor.id}/install`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ companyId: installCompanyId, status: installStatus }),
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok) {
        setInstallFor(null);
        setNotice(data.already ? 'Este Auxiliar já estava instalado nesta corretora.' : 'Auxiliar instalado na corretora.');
      } else {
        setInstallError(data.error || 'Não foi possível instalar.');
      }
    } catch {
      setInstallError('Erro ao instalar.');
    } finally {
      setInstalling(false);
    }
  };

  const openInstallations = (t: Template) => {
    setInstallationsFor(t);
    setInstallations(null);
    fetch(`/api/admin/auxiliaries/templates/${t.id}/installations`)
      .then((r) => r.json())
      .then((d) => setInstallations(d.installations || []))
      .catch(() => setInstallations([]));
  };

  const setF = (patch: Partial<FormData>) => setForm((f) => ({ ...f, ...patch }));

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-1">
        <h1 className="text-2xl font-bold text-foreground">Auxiliares Globais</h1>
        <Button onClick={openCreate}>
          <Plus className="w-4 h-4 mr-2" /> Novo template
        </Button>
      </div>
      <p className="text-sm text-muted-foreground mb-6">Crie e publique Auxiliares disponíveis para as corretoras.</p>

      {notice && (
        <div className="mb-4 flex items-center justify-between gap-2 rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground">
          <span>{notice}</span>
          <button onClick={() => setNotice('')} className="text-muted-foreground hover:text-foreground">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}
      {error && <div className="mb-4 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</div>}

      <div className="rounded-xl border border-border bg-card overflow-hidden">
        {templates === null ? (
          <div className="p-8 text-center text-sm text-muted-foreground">Carregando…</div>
        ) : templates.length === 0 ? (
          <div className="p-8 text-center text-sm text-muted-foreground">Nenhum template ainda. Crie o primeiro.</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-accent/50 text-muted-foreground">
              <tr>
                <th className="px-4 py-3 text-left font-medium">Nome</th>
                <th className="px-4 py-3 text-left font-medium">Slug</th>
                <th className="px-4 py-3 text-left font-medium">Categoria</th>
                <th className="px-4 py-3 text-left font-medium">Status</th>
                <th className="px-4 py-3 text-right font-medium">Ações</th>
              </tr>
            </thead>
            <tbody>
              {templates.map((t) => (
                <tr key={t.id} className="border-t border-border">
                  <td className="px-4 py-3 text-foreground font-medium">{t.name}</td>
                  <td className="px-4 py-3 font-mono text-xs text-muted-foreground">{t.slug}</td>
                  <td className="px-4 py-3 text-muted-foreground">{str(t.category) || '—'}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs ${isActive(t) ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400' : 'bg-muted text-muted-foreground'}`}
                    >
                      {isActive(t) ? 'Ativo' : 'Inativo'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap items-center justify-end gap-1.5">
                      <Button size="sm" variant="outline" onClick={() => openEdit(t)} title="Editar">
                        <Edit2 className="w-3.5 h-3.5" />
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => toggleActive(t)} title={isActive(t) ? 'Desativar' : 'Ativar'}>
                        <Power className="w-3.5 h-3.5" />
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => openInstall(t)} title="Instalar em corretora">
                        <Download className="w-3.5 h-3.5" />
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => openInstallations(t)} title="Instalações">
                        <Building2 className="w-3.5 h-3.5" />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Modal criar/editar */}
      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={() => !saving && setShowForm(false)}>
          <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-xl border border-border bg-card p-6" onClick={(e) => e.stopPropagation()}>
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-foreground">{editing ? 'Editar template' : 'Novo template'}</h2>
              <button onClick={() => setShowForm(false)} className="text-muted-foreground hover:text-foreground"><X className="w-5 h-5" /></button>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <label className="space-y-1 text-sm">
                <span className="text-foreground">Nome</span>
                <Input value={form.name} onChange={(e) => setF({ name: e.target.value })} />
              </label>
              <label className="space-y-1 text-sm">
                <span className="text-foreground">Slug {editing && <span className="text-muted-foreground">(imutável)</span>}</span>
                <Input value={form.slug} disabled={!!editing} onChange={(e) => setF({ slug: e.target.value })} placeholder="meu-auxiliar" />
              </label>
              <label className="space-y-1 text-sm">
                <span className="text-foreground">Categoria</span>
                <Input value={form.category} onChange={(e) => setF({ category: e.target.value })} placeholder="Comunicação" />
              </label>
              <label className="space-y-1 text-sm">
                <span className="text-foreground">Ícone (opcional)</span>
                <Input value={form.icon} onChange={(e) => setF({ icon: e.target.value })} />
              </label>
              <label className="space-y-1 text-sm sm:col-span-2">
                <span className="text-foreground">Descrição curta</span>
                <Input value={form.short_description} onChange={(e) => setF({ short_description: e.target.value })} />
              </label>
              <label className="space-y-1 text-sm sm:col-span-2">
                <span className="text-foreground">Descrição</span>
                <textarea className="w-full rounded-md border border-border bg-background p-2 text-sm" rows={2} value={form.description} onChange={(e) => setF({ description: e.target.value })} />
              </label>

              <label className="space-y-1 text-sm">
                <span className="text-foreground">Modo de execução</span>
                <select className="w-full rounded-md border border-border bg-background p-2 text-sm" value={form.execution_mode} onChange={(e) => setF({ execution_mode: e.target.value })}>
                  <option value="manual">manual</option>
                  <option value="scheduled">scheduled</option>
                  <option value="event">event</option>
                </select>
              </label>
              <label className="space-y-1 text-sm">
                <span className="text-foreground">Gatilho</span>
                <select className="w-full rounded-md border border-border bg-background p-2 text-sm" value={form.trigger_type} onChange={(e) => setF({ trigger_type: e.target.value })}>
                  <option value="manual">manual</option>
                  <option value="inbound">inbound</option>
                  <option value="schedule">schedule</option>
                </select>
              </label>

              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={form.requires_human_approval} onChange={(e) => setF({ requires_human_approval: e.target.checked })} className="h-4 w-4 accent-[hsl(var(--primary))]" />
                <span className="text-foreground">Exige aprovação humana</span>
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={form.uses_external_actions} onChange={(e) => setF({ uses_external_actions: e.target.checked })} className="h-4 w-4 accent-[hsl(var(--primary))]" />
                <span className="text-foreground">Usa ações externas</span>
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={form.is_active} onChange={(e) => setF({ is_active: e.target.checked })} className="h-4 w-4 accent-[hsl(var(--primary))]" />
                <span className="text-foreground">Ativo (visível na Galeria)</span>
              </label>

              <label className="space-y-1 text-sm sm:col-span-2">
                <span className="text-foreground">System prompt</span>
                <textarea className="w-full rounded-md border border-border bg-background p-2 text-sm" rows={3} value={form.system_prompt} onChange={(e) => setF({ system_prompt: e.target.value })} />
              </label>
              {(['default_config', 'permissions', 'input_schema', 'output_schema'] as const).map((f) => (
                <label key={f} className="space-y-1 text-sm">
                  <span className="text-foreground">{f} (JSON)</span>
                  <textarea className="w-full rounded-md border border-border bg-background p-2 font-mono text-xs" rows={3} value={form[f]} onChange={(e) => setF({ [f]: e.target.value } as Partial<FormData>)} placeholder="{}" />
                </label>
              ))}
            </div>

            {formError && <p className="mt-3 text-sm text-destructive">{formError}</p>}
            <p className="mt-3 text-xs text-muted-foreground">
              Campos sem coluna correspondente no banco são ignorados com segurança (sem alterar schema).
            </p>

            <div className="mt-5 flex justify-end gap-2">
              <Button variant="outline" onClick={() => setShowForm(false)} disabled={saving}>Cancelar</Button>
              <Button onClick={save} disabled={saving}>{saving ? 'Salvando…' : editing ? 'Salvar' : 'Criar'}</Button>
            </div>
          </div>
        </div>
      )}

      {/* Modal instalar */}
      {installFor && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={() => !installing && setInstallFor(null)}>
          <div className="w-full max-w-md rounded-xl border border-border bg-card p-6" onClick={(e) => e.stopPropagation()}>
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-foreground">Instalar “{installFor.name}”</h2>
              <button onClick={() => setInstallFor(null)} className="text-muted-foreground hover:text-foreground"><X className="w-5 h-5" /></button>
            </div>
            <div className="space-y-3">
              <label className="space-y-1 text-sm">
                <span className="text-foreground">Corretora</span>
                <select className="w-full rounded-md border border-border bg-background p-2 text-sm" value={installCompanyId} onChange={(e) => setInstallCompanyId(e.target.value)}>
                  <option value="">Selecione…</option>
                  {companies.map((c) => (
                    <option key={c.id} value={c.id}>{c.company_name || c.id}</option>
                  ))}
                </select>
              </label>
              <label className="space-y-1 text-sm">
                <span className="text-foreground">Status</span>
                <select className="w-full rounded-md border border-border bg-background p-2 text-sm" value={installStatus} onChange={(e) => setInstallStatus(e.target.value)}>
                  <option value="active">active</option>
                  <option value="paused">paused</option>
                </select>
              </label>
            </div>
            {installError && <p className="mt-3 text-sm text-destructive">{installError}</p>}
            <div className="mt-5 flex justify-end gap-2">
              <Button variant="outline" onClick={() => setInstallFor(null)} disabled={installing}>Cancelar</Button>
              <Button onClick={submitInstall} disabled={installing}>{installing ? 'Instalando…' : 'Instalar'}</Button>
            </div>
          </div>
        </div>
      )}

      {/* Modal instalações */}
      {installationsFor && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={() => setInstallationsFor(null)}>
          <div className="w-full max-w-md rounded-xl border border-border bg-card p-6" onClick={(e) => e.stopPropagation()}>
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-foreground">Instalações de “{installationsFor.name}”</h2>
              <button onClick={() => setInstallationsFor(null)} className="text-muted-foreground hover:text-foreground"><X className="w-5 h-5" /></button>
            </div>
            {installations === null ? (
              <p className="py-6 text-center text-sm text-muted-foreground">Carregando…</p>
            ) : installations.length === 0 ? (
              <p className="py-6 text-center text-sm text-muted-foreground">Ainda não instalado em nenhuma corretora.</p>
            ) : (
              <ul className="space-y-2">
                {installations.map((i) => (
                  <li key={i.id} className="flex items-center justify-between gap-2 rounded-lg border border-border px-3 py-2 text-sm">
                    <span className="text-foreground">{i.company_name}</span>
                    <span className="flex items-center gap-1 text-xs text-muted-foreground">
                      <Check className="w-3.5 h-3.5 text-emerald-500" /> {i.status || 'active'}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
