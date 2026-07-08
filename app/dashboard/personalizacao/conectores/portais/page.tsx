'use client';

// SPEC-020 — Portais das seguradoras: cada corretora coloca o SEU login/senha
// (escopado à conta dela, cifrado). Os endereços dos portais são iguais para
// todas; o que muda é a credencial. O atendente/rotinas usam isso p/ entrar nos
// portais (ex.: cobrança de boletos) quando o founder ligar o gate.

import { useCallback, useEffect, useState } from 'react';
import { Archive, Loader2, ExternalLink, Trash2, Check, Lock, AlertTriangle, RefreshCw } from 'lucide-react';

import { DetailHeader } from '@/components/patterns/DetailHeader';
import { icons } from '@/lib/icons';

type Portal = {
  id: string; key: string; name: string; login_url: string; category: string; insurer_key: string | null; cred_kind?: string | null;
};
type Cred = {
  portal_key: string; username: string | null; has_password: boolean; health: string; updated_at: string | null;
};
type PortalJob = {
  id: string;
  portal_key: string;
  portal_name: string;
  journey: string;
  status: string;
  message: string;
  evidence: Record<string, any>;
  screenshot: string | null;
  attempts: number;
  created_at: string | null;
};

const CAT_LABEL: Record<string, string> = { vidros: 'Vidros', corretor: 'Corretor', sinistro: 'Sinistro' };

export default function PortaisPage() {
  const [portals, setPortals] = useState<Portal[] | null>(null);
  const [creds, setCreds] = useState<Record<string, Cred>>({});
  const [forms, setForms] = useState<Record<string, { username: string; password: string }>>({});
  const [hitlJobs, setHitlJobs] = useState<PortalJob[]>([]);
  const [busy, setBusy] = useState('');
  const [notice, setNotice] = useState('');

  const loadHitlJobs = useCallback(async () => {
    try {
      const res = await fetch('/api/dashboard/portal-jobs?status=needs_human&limit=8', { cache: 'no-store', credentials: 'same-origin' });
      const j = await res.json().catch(() => ({}));
      setHitlJobs(res.ok ? (j.jobs || []) : []);
    } catch {
      setHitlJobs([]);
    }
  }, []);

  const load = useCallback(async () => {
    try {
      const res = await fetch('/api/dashboard/portal-credentials', { cache: 'no-store' });
      const j = await res.json();
      if (!res.ok) { setNotice(j.error || 'Erro ao carregar portais.'); setPortals([]); return; }
      setPortals(j.portals || []);
      const map: Record<string, Cred> = {};
      (j.credentials || []).forEach((c: Cred) => { map[c.portal_key] = c; });
      setCreds(map);
      loadHitlJobs();
    } catch { setNotice('Falha de conexão.'); setPortals([]); }
  }, [loadHitlJobs]);
  useEffect(() => { load(); }, [load]);

  const patchForm = (k: string, patch: Partial<{ username: string; password: string }>) =>
    setForms((f) => {
      const cur = f[k] || { username: '', password: '' };
      return { ...f, [k]: { ...cur, ...patch } };
    });

  const save = async (portal: Portal) => {
    const form = forms[portal.key] || { username: '', password: '' };
    const username = (form.username || creds[portal.key]?.username || '').trim();
    if (!username) { setNotice(`Informe o login de ${portal.name}.`); return; }
    if (!creds[portal.key]?.has_password && !form.password) {
      setNotice(`Informe a senha de ${portal.name} (na primeira vez).`); return;
    }
    setBusy(portal.key); setNotice('');
    const res = await fetch('/api/dashboard/portal-credentials', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ portal_key: portal.key, username, password: form.password || undefined }),
    });
    const j = await res.json().catch(() => ({}));
    setBusy('');
    if (!res.ok) { setNotice(j.detail || j.error || 'Erro ao salvar.'); return; }
    setForms((f) => ({ ...f, [portal.key]: { username: '', password: '' } }));
    load();
  };

  const remove = async (portal: Portal) => {
    if (!confirm(`Remover a credencial de ${portal.name}?`)) return;
    setBusy(portal.key);
    await fetch(`/api/dashboard/portal-credentials?portal_key=${encodeURIComponent(portal.key)}`, { method: 'DELETE' });
    setBusy(''); load();
  };

  const retryJob = async (job: PortalJob) => {
    setBusy(job.id); setNotice('');
    const res = await fetch('/api/dashboard/portal-jobs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({ action: 'retry', job_id: job.id }),
    });
    const j = await res.json().catch(() => ({}));
    setBusy('');
    if (!res.ok) { setNotice(j.error || 'Nao consegui reenfileirar o portal.'); return; }
    await loadHitlJobs();
  };

  const archiveJob = async (job: PortalJob) => {
    setBusy(job.id); setNotice('');
    const res = await fetch('/api/dashboard/portal-jobs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({ action: 'archive', job_id: job.id }),
    });
    const j = await res.json().catch(() => ({}));
    setBusy('');
    if (!res.ok) { setNotice(j.error || 'Nao consegui arquivar a pendencia.'); return; }
    await loadHitlJobs();
  };

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-3xl space-y-6 px-4 py-10 sm:px-6">
        <DetailHeader
          icon={icons.seguradoras}
          title="Portais das seguradoras"
          subtitle="Coloque o login e a senha da SUA corretora em cada portal. Ficam só na sua conta, guardados de forma cifrada — usados para automações como a cobrança de boletos."
          breadcrumb={[
            { label: 'Personalização', href: '/dashboard/personalizacao' },
            { label: 'Conectores', href: '/dashboard/personalizacao/conectores' },
            { label: 'Portais' },
          ]}
        />

        {notice && <p className="text-sm text-danger">{notice}</p>}

        {hitlJobs.length > 0 && (
          <section className="space-y-3">
            <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
              <AlertTriangle className="h-4 w-4 text-amber-500" />
              Portais aguardando humano
            </div>
            {hitlJobs.map((job) => {
              const portal = portals?.find((p) => p.key === job.portal_key);
              const kind = String(job.evidence?.hitl?.kind || '');
              return (
                <div key={job.id} className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-4">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div className="min-w-0 space-y-1">
                      <p className="text-sm font-semibold text-foreground">{job.portal_name}</p>
                      <p className="text-xs text-muted-foreground">
                        {kind === 'captcha_2fa' ? 'CAPTCHA/2FA' : 'Revisao'} - {job.message || 'Aguardando revisao no portal'}
                      </p>
                      {job.created_at && (
                        <p className="text-[11px] text-faint">
                          Job {job.id.slice(0, 8)} - tentativa {job.attempts || 0} - {new Date(job.created_at).toLocaleString('pt-BR')}
                        </p>
                      )}
                    </div>
                    <div className="flex shrink-0 gap-2">
                      <button
                        onClick={() => archiveJob(job)}
                        disabled={busy === job.id}
                        className="inline-flex items-center justify-center gap-1 rounded-md border border-border bg-surface px-3 py-2 text-xs font-medium text-foreground hover:bg-surface-2 disabled:opacity-50"
                      >
                        {busy === job.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Archive className="h-3.5 w-3.5" />}
                        Arquivar
                      </button>
                      {portal?.login_url && (
                        <a
                          href={portal.login_url}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center justify-center gap-1 rounded-md border border-border bg-surface px-3 py-2 text-xs font-medium text-foreground hover:bg-surface-2"
                        >
                          <ExternalLink className="h-3.5 w-3.5" /> Abrir portal
                        </a>
                      )}
                      <button
                        onClick={() => retryJob(job)}
                        disabled={busy === job.id}
                        className="inline-flex items-center justify-center gap-1 rounded-md bg-primary px-3 py-2 text-xs font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
                      >
                        {busy === job.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
                        Tentar novamente
                      </button>
                    </div>
                  </div>
                  {job.screenshot && (
                    <img
                      src={job.screenshot}
                      alt={`Evidencia do portal ${job.portal_name}`}
                      className="mt-3 max-h-80 w-full rounded-md border border-border object-contain"
                    />
                  )}
                </div>
              );
            })}
          </section>
        )}

        {portals === null ? (
          <div className="flex items-center gap-2 py-8 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Carregando portais…
          </div>
        ) : portals.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted-foreground">Nenhum portal cadastrado ainda.</p>
        ) : (
          <div className="space-y-3">
            {portals.map((p) => {
              const cred = creds[p.key];
              const isPublic = String(p.cred_kind || '') === 'public';
              const connected = isPublic || !!cred?.has_password;
              const form = forms[p.key] || { username: '', password: '' };
              return (
                <div key={p.key} className="rounded-xl border border-border bg-surface p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="text-sm font-semibold text-foreground">{p.name}</p>
                        <span className="rounded-full border border-border bg-surface-2 px-2 py-0.5 text-[10px] text-muted-foreground">
                          {CAT_LABEL[p.category] || p.category}
                        </span>
                        {isPublic ? (
                          <span className="inline-flex items-center gap-1 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-600">
                            <Check className="h-3 w-3" /> Disponivel
                          </span>
                        ) : connected ? (
                          <span className="inline-flex items-center gap-1 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-600">
                            <Check className="h-3 w-3" /> Conectado
                          </span>
                        ) : (
                          <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-[10px] text-amber-600">
                            Sem credencial
                          </span>
                        )}
                      </div>
                      <a
                        href={p.login_url}
                        target="_blank"
                        rel="noreferrer"
                        className="mt-0.5 inline-flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground"
                      >
                        {p.login_url} <ExternalLink className="h-3 w-3" />
                      </a>
                    </div>
                    {connected && !isPublic && (
                      <button
                        onClick={() => remove(p)}
                        disabled={busy === p.key}
                        className="shrink-0 rounded-md border border-border bg-surface-2 p-2 text-muted-foreground hover:text-danger disabled:opacity-50"
                        title="Remover credencial"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    )}
                  </div>

                  {isPublic ? (
                    <div className="mt-3 rounded-md border border-border bg-surface-2 px-3 py-2 text-xs text-muted-foreground">
                      Portal publico: nao precisa de login e senha. Os agentes podem usar este portal quando a rotina/atendimento precisar.
                    </div>
                  ) : (
                  <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-end">
                    <div className="flex-1">
                      <label className="mb-1 block text-[11px] font-medium text-muted-foreground">Login</label>
                      <input
                        value={form.username}
                        onChange={(e) => patchForm(p.key, { username: e.target.value })}
                        placeholder={cred?.username || 'usuário do portal'}
                        className="w-full rounded-md border border-border bg-surface-2 px-3 py-2 text-sm text-foreground outline-none focus:ring-2 focus:ring-ring"
                      />
                    </div>
                    <div className="flex-1">
                      <label className="mb-1 block text-[11px] font-medium text-muted-foreground">
                        Senha {connected && <span className="text-faint">(preencha só para trocar)</span>}
                      </label>
                      <input
                        type="password"
                        value={form.password}
                        onChange={(e) => patchForm(p.key, { password: e.target.value })}
                        placeholder={connected ? '••••••••' : 'senha do portal'}
                        className="w-full rounded-md border border-border bg-surface-2 px-3 py-2 text-sm text-foreground outline-none focus:ring-2 focus:ring-ring"
                      />
                    </div>
                    <button
                      onClick={() => save(p)}
                      disabled={busy === p.key}
                      className="inline-flex items-center justify-center gap-1.5 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
                    >
                      {busy === p.key ? <Loader2 className="h-4 w-4 animate-spin" /> : <Lock className="h-3.5 w-3.5" />}
                      {connected ? 'Atualizar' : 'Salvar'}
                    </button>
                  </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        <p className="text-[11px] text-faint">
          🔒 As senhas são guardadas cifradas e usadas só pelas automações da sua corretora. O AutoBrokers nunca mostra a senha de volta nem executa ação sem o seu comando.
        </p>
      </div>
    </div>
  );
}
