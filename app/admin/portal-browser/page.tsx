'use client';

import { useCallback, useEffect, useState } from 'react';
import { Globe, ShieldAlert } from 'lucide-react';

interface PortalDef {
  portal_id: string;
  label: string;
  owner_kind: string;
  owner_key: string;
  base_url: string;
  supported_journeys: string[];
  auth_methods: string[];
  challenge_profile?: { requires_hitl?: boolean };
  status: string;
}
interface AccountRef { status?: string; vault_ref_masked?: string; storage_ref_masked?: string; provider?: string }
interface PortalAccount {
  portal_account_id: string;
  portal_id: string;
  label: string;
  status: string;
  credential_ref?: AccountRef | null;
  session_ref?: AccountRef | null;
  challenge_profile?: { requires_hitl?: boolean };
  last_health_check_at?: string | null;
}

const AUTH_METHODS = ['password', 'mfa', 'captcha', 'sso', 'certificate', 'otp'];

export default function PortalBrowserAdminPage() {
  const [portals, setPortals] = useState<PortalDef[]>([]);
  const [accounts, setAccounts] = useState<PortalAccount[]>([]);
  const [notice, setNotice] = useState('');
  const [loading, setLoading] = useState(true);
  const [portalForm, setPortalForm] = useState({ label: '', owner_key: '', base_url: 'https://', journeys: '', auth: [] as string[] });
  const [acctForm, setAcctForm] = useState({ portal_id: '', label: '' });
  const [globalCatalog, setGlobalCatalog] = useState<any[]>([]);
  const [globalStats, setGlobalStats] = useState<any>(null);
  const [catalogFilter, setCatalogFilter] = useState({ owner_key: '', status: '' });

  const loadGlobalCatalog = useCallback(async () => {
    const qs = new URLSearchParams();
    if (catalogFilter.owner_key) qs.set('owner_key', catalogFilter.owner_key);
    if (catalogFilter.status) qs.set('status', catalogFilter.status);
    const res = await fetch(`/api/admin/portal-browser/global-catalog?${qs.toString()}`);
    const j = await res.json().catch(() => ({}));
    if (j?.ok) { setGlobalCatalog(j.catalog || []); setGlobalStats(j.stats || null); }
  }, [catalogFilter]);
  useEffect(() => { loadGlobalCatalog(); }, [loadGlobalCatalog]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [p, a] = await Promise.all([
        fetch('/api/admin/portal-browser/portals').then((r) => r.json()).catch(() => ({})),
        fetch('/api/admin/portal-browser/accounts').then((r) => r.json()).catch(() => ({})),
      ]);
      if (p?.ok) setPortals(p.portals || []);
      if (a?.ok) setAccounts(a.accounts || []);
      if (p?.error && p.error !== undefined && !p.ok) setNotice(p.error);
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => { load(); }, [load]);

  const createPortal = async () => {
    if (!portalForm.label.trim() || !portalForm.owner_key.trim()) { setNotice('Informe label e owner_key.'); return; }
    const res = await fetch('/api/admin/portal-browser/portals', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        label: portalForm.label.trim(), owner_key: portalForm.owner_key.trim(), base_url: portalForm.base_url.trim(),
        supported_journeys: portalForm.journeys.split(',').map((s) => s.trim()).filter(Boolean), auth_methods: portalForm.auth,
      }),
    });
    const j = await res.json().catch(() => ({}));
    if (j?.ok) { setPortalForm({ label: '', owner_key: '', base_url: 'https://', journeys: '', auth: [] }); await load(); }
    else setNotice(`Falha ao criar portal: ${j?.error || ''} ${(j?.details || []).join(', ')}`);
  };

  const createAccount = async () => {
    if (!acctForm.portal_id || !acctForm.label.trim()) { setNotice('Selecione portal e informe label.'); return; }
    const res = await fetch('/api/admin/portal-browser/accounts', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ portal_id: acctForm.portal_id, label: acctForm.label.trim() }),
    });
    const j = await res.json().catch(() => ({}));
    if (j?.ok) { setAcctForm({ portal_id: '', label: '' }); await load(); } else setNotice(`Falha ao criar conta: ${j?.error || ''}`);
  };

  const addCredentialRef = async (id: string) => {
    const res = await fetch(`/api/admin/portal-browser/accounts/${id}/credential-ref`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ vault_ref: `vault://mock-${Date.now()}` }),
    });
    const j = await res.json().catch(() => ({}));
    if (j?.ok) await load(); else setNotice(`Falha credential-ref: ${j?.error || ''}`);
  };
  const addSessionRef = async (id: string) => {
    const res = await fetch(`/api/admin/portal-browser/accounts/${id}/session-ref`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ storage_ref: `store://mock-${Date.now()}`, provider: 'browserbase', status: 'healthy', expires_at: new Date(Date.now() + 7 * 864e5).toISOString() }),
    });
    const j = await res.json().catch(() => ({}));
    if (j?.ok) await load(); else setNotice(`Falha session-ref: ${j?.error || ''}`);
  };
  const healthCheck = async (id: string) => {
    const res = await fetch(`/api/admin/portal-browser/accounts/${id}/health-check`, { method: 'POST' });
    const j = await res.json().catch(() => ({}));
    if (j?.ok) await load(); else setNotice(`Falha health-check: ${j?.error || ''}`);
  };

  const [relay, setRelay] = useState<any>(null);
  const [relayForm, setRelayForm] = useState({ owner_key: '', journey: 'login', provider: 'browserbase' });
  const startRelay = async () => {
    const res = await fetch('/api/admin/portal-browser/relay/start', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ owner_key: relayForm.owner_key.trim() || null, journey: relayForm.journey, provider: relayForm.provider }),
    });
    const j = await res.json().catch(() => ({}));
    if (j?.ok) { setRelay(j.relay); setNotice('Relay sandbox iniciado. Nenhum browser real aberto.'); } else setNotice(`Falha relay: ${j?.error || ''}`);
  };
  const relayStep = async (type: string, extra: any = {}) => {
    if (!relay?.relay_id) return;
    const res = await fetch('/api/admin/portal-browser/relay/step', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ relay_id: relay.relay_id, type, ...extra }),
    });
    const j = await res.json().catch(() => ({}));
    if (j?.ok) setRelay(j.relay); else setNotice(`Falha step: ${j?.error || ''}`);
  };

  return (
    <div className="p-8">
      <div className="mb-6">
        <p className="mb-1 text-xs uppercase tracking-wide text-faint">Conectores → Portais</p>
        <h1 className="mb-2 flex items-center gap-3 text-3xl font-bold text-foreground"><Globe className="h-7 w-7" /> Portal Browser — Registry & Contas</h1>
        <p className="text-sm text-muted-foreground">Cadastro global de portais + contas privadas da corretora. CredentialRef/SessionRef são referências opacas (sem segredo). Conector próprio <code>portal_browser</code>.</p>
      </div>

      <div className="mb-6 flex items-center gap-2 rounded-lg border border-amber-500/40 bg-amber-500/5 px-4 py-2 text-sm text-amber-600">
        <ShieldAlert className="h-4 w-4" /> Nenhum portal real é acessado nesta fase (43P1). Tudo mock/dry-run; CAPTCHA/2FA = HITL.
      </div>
      {notice && <p className="mb-4 text-sm text-muted-foreground">{notice}</p>}

      {/* Catálogo Global (intake oficial) */}
      <div className="mb-6 rounded-lg border border-border bg-card p-4">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <p className="text-sm font-medium text-foreground">Catálogo Global de Portais</p>
          {globalStats && <span className="text-[11px] text-muted-foreground">{globalStats.deduped} portais · {globalStats.insurers?.length} seguradoras · {globalStats.seed_active} sandbox_ready · {globalStats.needs_review} needs_review</span>}
        </div>
        <div className="mb-2 flex flex-wrap gap-2">
          <input value={catalogFilter.owner_key} onChange={(e) => setCatalogFilter({ ...catalogFilter, owner_key: e.target.value })} placeholder="filtrar owner_key (ex: allianz)" className="rounded-lg border border-border bg-background px-3 py-1.5 text-xs" />
          <select value={catalogFilter.status} onChange={(e) => setCatalogFilter({ ...catalogFilter, status: e.target.value })} className="rounded-lg border border-border bg-background px-3 py-1.5 text-xs">
            <option value="">todos status</option>
            <option value="sandbox_ready">sandbox_ready</option>
            <option value="needs_review">needs_review</option>
          </select>
        </div>
        <div className="max-h-72 overflow-auto rounded-lg border border-border">
          <table className="w-full text-xs">
            <thead className="sticky top-0 bg-surface-2 text-left uppercase tracking-wide text-faint">
              <tr><th className="px-2 py-1.5">Portal</th><th className="px-2 py-1.5">Owner</th><th className="px-2 py-1.5">Jornada</th><th className="px-2 py-1.5">Audiência</th><th className="px-2 py-1.5">Challenge</th><th className="px-2 py-1.5">Status</th><th className="px-2 py-1.5">Confiança</th></tr>
            </thead>
            <tbody>
              {globalCatalog.length === 0 ? <tr><td className="px-2 py-1.5 text-muted-foreground" colSpan={7}>Catálogo vazio (verifique o intake).</td></tr> :
                globalCatalog.slice(0, 200).map((c) => (
                  <tr key={c.portal_id} className="border-t border-border">
                    <td className="px-2 py-1.5 text-foreground">{c.label}</td>
                    <td className="px-2 py-1.5 text-muted-foreground">{c.owner_key}</td>
                    <td className="px-2 py-1.5 text-muted-foreground">{(c.supported_journeys || []).join(', ')}</td>
                    <td className="px-2 py-1.5 text-muted-foreground">{c.metadata?.audience ?? '—'}</td>
                    <td className="px-2 py-1.5 text-muted-foreground">{c.challenge_profile?.requires_hitl ? 'HITL' : '—'}</td>
                    <td className="px-2 py-1.5 text-muted-foreground">{c.status}</td>
                    <td className="px-2 py-1.5 text-muted-foreground">{c.metadata?.confidence ?? '—'}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
        <p className="mt-2 text-[10px] text-faint">Fonte: intake oficial pesquisado. Sem credenciais. Contas da corretora são criadas separadamente abaixo.</p>
      </div>

      {/* Criar portal */}
      <div className="mb-6 rounded-lg border border-border bg-card p-4">
        <p className="mb-3 text-sm font-medium text-foreground">Portais da Corretora (tenant) — criar</p>
        <div className="grid grid-cols-1 gap-2 md:grid-cols-4">
          <input value={portalForm.label} onChange={(e) => setPortalForm({ ...portalForm, label: e.target.value })} placeholder="label (ex: Allianz Portal)" className="rounded-lg border border-border bg-background px-3 py-2 text-sm" />
          <input value={portalForm.owner_key} onChange={(e) => setPortalForm({ ...portalForm, owner_key: e.target.value })} placeholder="owner_key (ex: allianz)" className="rounded-lg border border-border bg-background px-3 py-2 text-sm" />
          <input value={portalForm.base_url} onChange={(e) => setPortalForm({ ...portalForm, base_url: e.target.value })} placeholder="https://portal..." className="rounded-lg border border-border bg-background px-3 py-2 text-sm" />
          <input value={portalForm.journeys} onChange={(e) => setPortalForm({ ...portalForm, journeys: e.target.value })} placeholder="jornadas (vírgula)" className="rounded-lg border border-border bg-background px-3 py-2 text-sm" />
        </div>
        <div className="mt-2 flex flex-wrap gap-2">
          {AUTH_METHODS.map((m) => (
            <label key={m} className="flex items-center gap-1 text-[11px] text-muted-foreground">
              <input type="checkbox" checked={portalForm.auth.includes(m)} onChange={(e) => setPortalForm({ ...portalForm, auth: e.target.checked ? [...portalForm.auth, m] : portalForm.auth.filter((x) => x !== m) })} /> {m}
            </label>
          ))}
        </div>
        <button onClick={createPortal} className="mt-3 rounded-lg border border-primary/40 bg-primary/5 px-3 py-1.5 text-sm font-medium text-primary hover:bg-primary/10">Adicionar portal</button>
      </div>

      {/* Portais */}
      {loading ? <p className="text-sm text-muted-foreground">Carregando…</p> : (
        <div className="mb-6 overflow-x-auto rounded-lg border border-border">
          <table className="w-full text-sm">
            <thead className="bg-surface-2 text-left text-xs uppercase tracking-wide text-faint">
              <tr><th className="px-3 py-2">Portal</th><th className="px-3 py-2">Owner</th><th className="px-3 py-2">URL</th><th className="px-3 py-2">Jornadas</th><th className="px-3 py-2">Challenge</th><th className="px-3 py-2">Status</th></tr>
            </thead>
            <tbody>
              {portals.length === 0 ? <tr><td className="px-3 py-2 text-muted-foreground" colSpan={6}>Nenhum portal cadastrado.</td></tr> :
                portals.map((p) => (
                  <tr key={p.portal_id} className="border-t border-border">
                    <td className="px-3 py-2 text-foreground">{p.label}</td>
                    <td className="px-3 py-2 text-muted-foreground">{p.owner_key}</td>
                    <td className="px-3 py-2 text-muted-foreground">{p.base_url}</td>
                    <td className="px-3 py-2 text-muted-foreground">{(p.supported_journeys || []).join(', ') || '—'}</td>
                    <td className="px-3 py-2 text-muted-foreground">{p.challenge_profile?.requires_hitl ? 'HITL' : '—'}</td>
                    <td className="px-3 py-2 text-muted-foreground">{p.status}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Criar conta */}
      <div className="mb-6 rounded-lg border border-border bg-card p-4">
        <p className="mb-3 text-sm font-medium text-foreground">Criar conta de portal (corretora)</p>
        <div className="grid grid-cols-1 gap-2 md:grid-cols-3">
          <select value={acctForm.portal_id} onChange={(e) => setAcctForm({ ...acctForm, portal_id: e.target.value })} className="rounded-lg border border-border bg-background px-3 py-2 text-sm">
            <option value="">selecione o portal</option>
            {portals.map((p) => <option key={p.portal_id} value={p.portal_id}>{p.label}</option>)}
          </select>
          <input value={acctForm.label} onChange={(e) => setAcctForm({ ...acctForm, label: e.target.value })} placeholder="label da conta" className="rounded-lg border border-border bg-background px-3 py-2 text-sm" />
          <button onClick={createAccount} className="rounded-lg border border-primary/40 bg-primary/5 px-3 py-1.5 text-sm font-medium text-primary hover:bg-primary/10">Adicionar conta</button>
        </div>
      </div>

      {/* Contas */}
      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-sm">
          <thead className="bg-surface-2 text-left text-xs uppercase tracking-wide text-faint">
            <tr><th className="px-3 py-2">Conta</th><th className="px-3 py-2">Portal</th><th className="px-3 py-2">Credencial</th><th className="px-3 py-2">Sessão</th><th className="px-3 py-2">Status</th><th className="px-3 py-2">Ações (mock)</th></tr>
          </thead>
          <tbody>
            {accounts.length === 0 ? <tr><td className="px-3 py-2 text-muted-foreground" colSpan={6}>Nenhuma conta.</td></tr> :
              accounts.map((a) => (
                <tr key={a.portal_account_id} className="border-t border-border">
                  <td className="px-3 py-2 text-foreground">{a.label}</td>
                  <td className="px-3 py-2 text-muted-foreground">{a.portal_id}</td>
                  <td className="px-3 py-2 text-muted-foreground">{a.credential_ref ? `${a.credential_ref.vault_ref_masked} (${a.credential_ref.status})` : '—'}</td>
                  <td className="px-3 py-2 text-muted-foreground">{a.session_ref ? `${a.session_ref.storage_ref_masked} (${a.session_ref.status})` : '—'}</td>
                  <td className="px-3 py-2 text-muted-foreground">{a.status}</td>
                  <td className="px-3 py-2">
                    <div className="flex flex-wrap gap-1.5">
                      <button onClick={() => addCredentialRef(a.portal_account_id)} className="rounded border border-border px-2 py-0.5 text-[10px] hover:bg-surface-2">+ CredentialRef</button>
                      <button onClick={() => addSessionRef(a.portal_account_id)} className="rounded border border-border px-2 py-0.5 text-[10px] hover:bg-surface-2">+ SessionRef</button>
                      <button onClick={() => healthCheck(a.portal_account_id)} className="rounded border border-border px-2 py-0.5 text-[10px] hover:bg-surface-2">Health check</button>
                    </div>
                  </td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>

      {/* Relay Sandbox (mock) — 43P2 */}
      <div className="mt-6 rounded-lg border border-border bg-card p-4">
        <div className="mb-2 flex flex-wrap items-center gap-2">
          <p className="text-sm font-medium text-foreground">Relay Sandbox (mock)</p>
          <span className="text-[11px] text-amber-600">Nenhum browser real é aberto nesta fase.</span>
        </div>
        <div className="mb-2 flex flex-wrap gap-2">
          <input value={relayForm.owner_key} onChange={(e) => setRelayForm({ ...relayForm, owner_key: e.target.value })} placeholder="owner_key (ex: allianz)" className="rounded-lg border border-border bg-background px-3 py-1.5 text-xs" />
          <input value={relayForm.journey} onChange={(e) => setRelayForm({ ...relayForm, journey: e.target.value })} placeholder="journey (ex: login)" className="rounded-lg border border-border bg-background px-3 py-1.5 text-xs" />
          <select value={relayForm.provider} onChange={(e) => setRelayForm({ ...relayForm, provider: e.target.value })} className="rounded-lg border border-border bg-background px-3 py-1.5 text-xs">
            {['browserbase', 'local_playwright', 'stagehand', 'skyvern_lab', 'mock'].map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
          <button onClick={startRelay} className="rounded-lg border border-primary/40 bg-primary/5 px-3 py-1.5 text-xs font-medium text-primary hover:bg-primary/10">Iniciar Relay Sandbox</button>
        </div>
        {relay && (
          <div className="rounded-lg border border-border bg-surface-2 p-3 text-[11px]">
            <p className="text-muted-foreground">status: <span className="text-foreground">{relay.status}</span> · provider: {relay.provider} · next: {relay.next_step} · real_action_allowed: false</p>
            <div className="mt-2 flex flex-wrap gap-1.5">
              <button onClick={() => relayStep('observe', { instruction: 'observar tela' })} className="rounded border border-border px-2 py-0.5 text-[10px] hover:bg-surface-2">observe</button>
              <button onClick={() => relayStep('act', { instruction: 'preencher/clicar' })} className="rounded border border-border px-2 py-0.5 text-[10px] hover:bg-surface-2">act</button>
              <button onClick={() => relayStep('extract', { query: 'status' })} className="rounded border border-border px-2 py-0.5 text-[10px] hover:bg-surface-2">extract</button>
              <button onClick={() => relayStep('challenge', { challenge_signal: 'recaptcha' })} className="rounded border border-border px-2 py-0.5 text-[10px] hover:bg-surface-2">simular challenge</button>
              <button onClick={() => relayStep('complete')} className="rounded border border-border px-2 py-0.5 text-[10px] hover:bg-surface-2">complete</button>
              <button onClick={() => relayStep('cancel')} className="rounded border border-border px-2 py-0.5 text-[10px] hover:bg-surface-2">cancel</button>
            </div>
            {Array.isArray(relay.events) && (
              <ul className="mt-2 space-y-0.5">
                {relay.events.slice(-8).map((e: any, i: number) => (
                  <li key={i} className="text-[10px] text-muted-foreground">{e.type}{e.note ? ` — ${e.note}` : ''}</li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
