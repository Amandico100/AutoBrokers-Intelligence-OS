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

  const [skills, setSkills] = useState<any[]>([]);
  const [skillRun, setSkillRun] = useState<any>(null);
  useEffect(() => { fetch('/api/admin/portal-browser/skills').then((r) => r.json()).then((j) => { if (j?.ok) setSkills(j.skills || []); }).catch(() => {}); }, []);
  const runSkillDryRun = async (sk: any) => {
    const res = await fetch('/api/admin/portal-browser/skills/dry-run', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ portal_id: sk.portal_id, skill_key: sk.skill_key, provider: 'browserbase' }),
    });
    const j = await res.json().catch(() => ({}));
    if (j?.ok) { setSkillRun(j.run); setNotice('Skill dry-run executada. Nenhum portal real acessado.'); } else setNotice(`Falha skill dry-run: ${j?.error || ''}`);
  };

  const [loginSetup, setLoginSetup] = useState<any>(null);
  const [bbReadiness, setBbReadiness] = useState<any>(null);
  useEffect(() => { fetch('/api/admin/portal-browser/login-setup/browserbase/readiness').then((r) => r.json()).then((j) => { if (j?.ok) setBbReadiness(j.readiness); }).catch(() => {}); }, []);

  // 43P-FINAL-1 — status de canaries (read-only, gated).
  const [canaryStatus, setCanaryStatus] = useState<any>(null);
  const loadCanaryStatus = useCallback(async () => {
    const j = await fetch('/api/admin/portal-browser/real-execution/status').then((r) => r.json()).catch(() => ({}));
    if (j?.ok) setCanaryStatus(j);
  }, []);
  useEffect(() => { loadCanaryStatus(); }, [loadCanaryStatus]);

  // 43P4.2A — escopo de corretora (multi-tenant). O master admin escolhe a company;
  // gravamos um cookie aj_company que vai em toda chamada às rotas de portal.
  const [companyScope, setCompanyScope] = useState<{ is_master?: boolean; current_company_id?: string | null; company_scope_required?: boolean; companies?: any[] }>({});
  const loadCompanies = useCallback(async () => {
    const j = await fetch('/api/admin/portal-browser/companies').then((r) => r.json()).catch(() => ({}));
    if (j?.ok) setCompanyScope({ is_master: j.is_master, current_company_id: j.current_company_id, company_scope_required: j.company_scope_required, companies: j.companies || [] });
  }, []);
  useEffect(() => { loadCompanies(); }, [loadCompanies]);
  const selectCompany = async (id: string) => {
    // Seleção server-side (cookie HttpOnly): mais robusto que document.cookie.
    await fetch('/api/admin/portal-browser/select-company', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ company_id: id }),
    }).catch(() => {});
    window.location.reload();
  };
  const startLoginAssisted = async (portalId: string, accountId: string) => {
    const res = await fetch('/api/admin/portal-browser/login-setup/start', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ portal_id: portalId, portal_account_id: accountId, provider: 'browserbase' }),
    });
    const j = await res.json().catch(() => ({}));
    if (j?.ok) { setLoginSetup({ ...j.login_setup, production_gate: j.production_gate }); setNotice('Login assistido iniciado (gated). Nenhum browser real aberto.'); }
    else setNotice(`Falha login assistido: ${j?.error || ''}`);
  };

  const [candidates, setCandidates] = useState<any[]>([]);
  const [candFilter, setCandFilter] = useState({ exclude: true });
  const loadCandidates = useCallback(async () => {
    const qs = new URLSearchParams({ audience: 'corretor', status: 'sandbox_ready', confidence: 'confirmed', limit: '40' });
    if (candFilter.exclude) qs.set('exclude_mfa_captcha', 'true');
    const res = await fetch(`/api/admin/portal-browser/skill-factory/candidates?${qs.toString()}`);
    const j = await res.json().catch(() => ({}));
    if (j?.ok) setCandidates(j.candidates || []);
  }, [candFilter]);
  useEffect(() => { loadCandidates(); }, [loadCandidates]);

  return (
    <div className="p-8">
      <div className="mb-6">
        <p className="mb-1 text-xs uppercase tracking-wide text-faint">Conectores → Portais</p>
        <h1 className="mb-2 flex items-center gap-3 text-3xl font-bold text-foreground"><Globe className="h-7 w-7" /> Portal Browser — Registry & Contas</h1>
        <p className="text-sm text-muted-foreground">Cadastro global de portais + contas privadas da corretora. CredentialRef/SessionRef são referências opacas (sem segredo). Conector próprio <code>portal_browser</code>.</p>
      </div>

      {/* 43P4.2A.1 — Seletor de corretora: SÓ master admin enumera/troca tenant. */}
      {companyScope.is_master === true && (
        <div className="mb-6 rounded-lg border border-border bg-card p-4">
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-sm font-medium text-foreground">Corretora (tenant)</span>
            <select
              value={companyScope.current_company_id || ''}
              onChange={(e) => e.target.value && selectCompany(e.target.value)}
              className="rounded-lg border border-border bg-background px-3 py-1.5 text-sm text-foreground"
            >
              <option value="">— selecione a corretora —</option>
              {(companyScope.companies || []).map((c: any) => (
                <option key={c.id} value={c.id}>{c.name || c.id}{c.status ? ` (${c.status})` : ''}</option>
              ))}
            </select>
            {companyScope.current_company_id
              ? <span className="text-[11px] text-emerald-600">Operando: {companyScope.current_company_id}</span>
              : <span className="text-[11px] text-amber-600">Selecione uma corretora para operar os portais.</span>}
          </div>
          {companyScope.company_scope_required && !companyScope.current_company_id && (
            <p className="mt-1 text-[11px] text-amber-600">Escolha qual corretora você vai operar (escopo obrigatório para master admin).</p>
          )}
        </div>
      )}
      {companyScope.is_master === false && companyScope.current_company_id && (
        <div className="mb-6 rounded-lg border border-border bg-card px-4 py-2 text-[11px] text-muted-foreground">
          Corretora: <span className="text-foreground">{companyScope.current_company_id}</span>
        </div>
      )}

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
                      <button onClick={() => startLoginAssisted(a.portal_id, a.portal_account_id)} className="rounded border border-amber-500/40 bg-amber-500/5 px-2 py-0.5 text-[10px] text-amber-600 hover:bg-amber-500/10">Iniciar login assistido</button>
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

      {/* Portal Skills (dry-run) — 43P3 */}
      <div className="mt-6 rounded-lg border border-border bg-card p-4">
        <div className="mb-2 flex flex-wrap items-center gap-2">
          <p className="text-sm font-medium text-foreground">Portal Skills (dry-run)</p>
          <span className="text-[11px] text-amber-600">Skill não acessa portal real nesta fase.</span>
        </div>
        {skills.length === 0 ? <p className="text-[11px] text-muted-foreground">Nenhuma skill disponível.</p> : (
          <div className="flex flex-wrap gap-2">
            {skills.map((sk) => (
              <div key={sk.portal_skill_id} className="rounded-lg border border-border bg-surface-2 p-2 text-[11px]">
                <p className="text-foreground">{sk.skill_key} · {sk.journey}</p>
                <p className="text-muted-foreground">{sk.portal_id}</p>
                <button onClick={() => runSkillDryRun(sk)} className="mt-1 rounded border border-primary/40 bg-primary/5 px-2 py-0.5 text-[10px] font-medium text-primary hover:bg-primary/10">Rodar dry-run {sk.skill_key}</button>
              </div>
            ))}
          </div>
        )}
        {skillRun && (
          <div className="mt-2 rounded-lg border border-border bg-surface-2 p-3 text-[11px]">
            <p className="text-muted-foreground">status: <span className="text-foreground">{skillRun.status}</span> · next: {skillRun.next_step} · outputs: {(skillRun.outputs || []).join(', ') || '—'}</p>
            {skillRun.eval && <p className="mt-1 text-muted-foreground">eval: passed={String(skillRun.eval.passed)} · score={skillRun.eval.score} · promote={String(skillRun.eval.safe_to_promote_to_sandbox_validated)} · real_action_allowed=false</p>}
          </div>
        )}
      </div>

      {/* Skill Factory — 43P3.1 */}
      <div className="mt-6 rounded-lg border border-border bg-card p-4">
        <div className="mb-2 flex flex-wrap items-center gap-2">
          <p className="text-sm font-medium text-foreground">Skill Factory — candidatos do catálogo</p>
          <span className="text-[11px] text-amber-600">Skills são candidatas; nenhuma ação real.</span>
          <label className="ml-auto flex items-center gap-1 text-[11px] text-muted-foreground">
            <input type="checkbox" checked={candFilter.exclude} onChange={(e) => setCandFilter({ exclude: e.target.checked })} /> excluir MFA/captcha
          </label>
        </div>
        <div className="max-h-72 overflow-auto rounded-lg border border-border">
          <table className="w-full text-xs">
            <thead className="sticky top-0 bg-surface-2 text-left uppercase tracking-wide text-faint">
              <tr><th className="px-2 py-1.5">Owner</th><th className="px-2 py-1.5">Portal</th><th className="px-2 py-1.5">Jornada</th><th className="px-2 py-1.5">Blueprint</th><th className="px-2 py-1.5">Risco</th><th className="px-2 py-1.5">Evid.</th><th className="px-2 py-1.5">Próximo passo</th></tr>
            </thead>
            <tbody>
              {candidates.length === 0 ? <tr><td className="px-2 py-1.5 text-muted-foreground" colSpan={7}>Sem candidatos.</td></tr> :
                candidates.map((c, i) => (
                  <tr key={`${c.portal_id}-${c.journey}-${i}`} className="border-t border-border">
                    <td className="px-2 py-1.5 text-foreground">{c.owner_key}</td>
                    <td className="px-2 py-1.5 text-muted-foreground">{c.portal_id}</td>
                    <td className="px-2 py-1.5 text-muted-foreground">{c.journey}</td>
                    <td className="px-2 py-1.5 text-muted-foreground">{c.blueprint_key}</td>
                    <td className="px-2 py-1.5 text-muted-foreground">{c.risk_level}</td>
                    <td className="px-2 py-1.5 text-muted-foreground">{c.evidence_score}</td>
                    <td className="px-2 py-1.5 text-muted-foreground">{c.suggested_next_step}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
        <p className="mt-2 text-[10px] text-faint">Cada candidato deriva de evidência do catálogo oficial. Promoção máxima nesta fase: sandbox_validated.</p>
      </div>

      {/* Browserbase readiness (43P4.1) */}
      {bbReadiness && (
        <div className="mt-6 rounded-lg border border-border bg-card p-4">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <p className="text-sm font-medium text-foreground">Browserbase — readiness (canary real)</p>
            <span className="text-[11px] text-amber-600">Custo/segurança: abre browser real só com flags + aprovação + kill switch off.</span>
          </div>
          <p className="text-[11px] text-muted-foreground">
            can_open_real_browser: <span className="font-medium text-foreground">{String(bbReadiness.can_open_real_browser)}</span>
            {' '}· env: api_key={String(bbReadiness.env_present?.api_key_present)} / project_id={String(bbReadiness.env_present?.project_id_present)}
          </p>
          {Array.isArray(bbReadiness.blockers) && bbReadiness.blockers.length > 0 && (
            <p className="mt-1 text-[10px] text-muted-foreground">Bloqueios: {bbReadiness.blockers.join(', ')}</p>
          )}
          <button disabled={!bbReadiness.can_open_real_browser} className="mt-2 rounded-lg border border-border px-3 py-1 text-[11px] text-muted-foreground disabled:opacity-50">
            Iniciar canary real {bbReadiness.can_open_real_browser ? '' : '(bloqueado)'}
          </button>
          <p className="mt-1 text-[10px] text-faint">Nenhum segredo é exposto. Docs: docs.browserbase.com</p>
        </div>
      )}

      {/* 43P-FINAL-1 — Canary real: checklist go/no-go (read-only) */}
      {bbReadiness && (() => {
        const accountsForTenant = accounts.length;
        const approvals = canaryStatus?.approvals || [];
        const hasApproval = approvals.some((a: any) => !a.revoked && a.expires_at && Date.parse(a.expires_at) > Date.now());
        const item = (ok: boolean, label: string) => (
          <li className="flex items-center gap-2 text-[11px]"><span className={ok ? 'text-emerald-600' : 'text-muted-foreground'}>{ok ? '✓' : '○'}</span><span className={ok ? 'text-foreground' : 'text-muted-foreground'}>{label}</span></li>
        );
        const canStart = Boolean(companyScope.current_company_id) && accountsForTenant > 0 && hasApproval && bbReadiness.can_open_real_browser;
        return (
          <div className="mt-6 rounded-lg border border-border bg-card p-4">
            <p className="mb-2 text-sm font-medium text-foreground">Canary real de login — checklist (go/no-go)</p>
            <ul className="grid grid-cols-1 gap-1 md:grid-cols-2">
              {item(Boolean(companyScope.current_company_id), 'Corretora (tenant) selecionada')}
              {item(accountsForTenant > 0, 'Conta de portal criada para a corretora')}
              {item(hasApproval, 'Approval de canary válida (não expirada)')}
              {item(bbReadiness.env_present?.api_key_present && bbReadiness.env_present?.project_id_present, 'Browserbase configurado (envs)')}
              {item(bbReadiness.can_open_real_browser, 'Gates habilitados + kill switch off')}
              {item(false, 'Live view disponível (operador abre no console Browserbase — Batch 2)')}
              {item(false, 'Login humano (Batch 2)')}
              {item(false, 'SessionRef capturada (Batch 2)')}
              {item(false, 'SessionRef verificada (Batch 2)')}
              {item(true, 'Skill read-only session_login_verify pronta')}
            </ul>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <button disabled={!canStart} className="rounded-lg border border-border px-3 py-1 text-[11px] text-muted-foreground disabled:opacity-50">
                Iniciar canary {canStart ? '' : '(bloqueado)'}
              </button>
              <button onClick={loadCanaryStatus} className="rounded-lg border border-border px-3 py-1 text-[11px] text-muted-foreground">Atualizar status</button>
            </div>
            <div className="mt-2 rounded-md border border-amber-500/30 bg-amber-500/5 px-3 py-2 text-[10px] text-amber-600">
              O humano digita as credenciais e resolve CAPTCHA/2FA. O sistema não envia, não submete e não executa ação de negócio. connectUrl/signingKey/cookies/storageState nunca chegam ao frontend. Kill switch encerra tudo.
            </div>
            {canaryStatus?.canaries?.length > 0 && (
              <p className="mt-2 text-[10px] text-muted-foreground">Canaries: {canaryStatus.canaries.map((c: any) => `${c.canary_id.slice(0, 10)}…=${c.state}`).join(' · ')}</p>
            )}
          </div>
        );
      })()}

      {/* Login assistido (43P4) */}
      {loginSetup && (
        <div className="mt-6 rounded-lg border border-border bg-card p-4">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <p className="text-sm font-medium text-foreground">Login assistido (gated)</p>
            <span className="text-[11px] text-amber-600">Nenhum browser/login real é aberto nesta fase. Exige flags + aprovação + kill switch off.</span>
          </div>
          <p className="text-[11px] text-muted-foreground">setup: {loginSetup.setup_id} · status: <span className="text-foreground">{loginSetup.status}</span> · próximo: {loginSetup.next_step} · real_browser_opened: false</p>
          {Array.isArray(loginSetup.blockers) && loginSetup.blockers.length > 0 && (
            <p className="mt-1 text-[10px] text-muted-foreground">Bloqueios: {loginSetup.blockers.join(', ')}</p>
          )}
          {loginSetup.production_gate && (
            <p className="mt-1 text-[10px] text-muted-foreground">Gate de produção: allowed={String(loginSetup.production_gate.allowed)} · {(loginSetup.production_gate.blockers || []).join(', ')}</p>
          )}
        </div>
      )}
    </div>
  );
}
