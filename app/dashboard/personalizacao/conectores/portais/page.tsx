'use client';

// SPEC-020 — Portais das seguradoras: cada corretora coloca o SEU login/senha
// (escopado à conta dela, cifrado). Os endereços dos portais são iguais para
// todas; o que muda é a credencial. O atendente/rotinas usam isso p/ entrar nos
// portais (ex.: cobrança de boletos) quando o founder ligar o gate.

import { useCallback, useEffect, useState } from 'react';
import { Archive, Loader2, ExternalLink, Trash2, Check, Lock, AlertTriangle, RefreshCw, Activity, Image as ImageIcon } from 'lucide-react';

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
  started_at?: string | null;
  finished_at?: string | null;
  protocolo?: string | null;
  resumo?: string | null;
  prova?: string | null;
  tem_screenshot?: boolean;
  passos?: number;
};

const CAT_LABEL: Record<string, string> = { vidros: 'Vidros', corretor: 'Corretor', sinistro: 'Sinistro' };

// O corretor nunca le chave nem status cru (R11). Estes dois mapas sao a unica
// porta pela qual `journey` e `status` chegam a tela.
const JORNADA_LABEL: Record<string, string> = {
  abrir_atendimento: 'Abrir atendimento de vidro',
  login_check: 'Conferir acesso',
  cobranca_sweep: 'Buscar boletos',
};

const ESTADO: Record<string, { label: string; classe: string }> = {
  queued: { label: 'Na fila', classe: 'border-border bg-surface-2 text-muted-foreground' },
  running: { label: 'Em andamento', classe: 'border-sky-500/30 bg-sky-500/10 text-sky-600' },
  done: { label: 'Concluído', classe: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-600' },
  needs_human: { label: 'Precisa de uma pessoa', classe: 'border-amber-500/30 bg-amber-500/10 text-amber-600' },
  failed: { label: 'Falhou', classe: 'border-danger/30 bg-danger/10 text-danger' },
  archived: { label: 'Arquivado', classe: 'border-border bg-surface-2 text-faint' },
};

const EM_CURSO = ['queued', 'running'];

const jornadaLabel = (j: string) => JORNADA_LABEL[j] || 'Trabalho no portal';
const estadoDe = (s: string) => ESTADO[s] || { label: 'Em análise', classe: 'border-border bg-surface-2 text-muted-foreground' };
const hora = (iso?: string | null) => (iso ? new Date(iso).toLocaleString('pt-BR') : null);

export default function PortaisPage() {
  const [portals, setPortals] = useState<Portal[] | null>(null);
  const [creds, setCreds] = useState<Record<string, Cred>>({});
  const [forms, setForms] = useState<Record<string, { username: string; password: string }>>({});
  const [hitlJobs, setHitlJobs] = useState<PortalJob[]>([]);
  const [allJobs, setAllJobs] = useState<PortalJob[] | null>(null);
  const [loadingJobs, setLoadingJobs] = useState(false);
  const [provas, setProvas] = useState<Record<string, string>>({});
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

  const loadAllJobs = useCallback(async () => {
    setLoadingJobs(true);
    try {
      const res = await fetch('/api/dashboard/portal-jobs?status=all&limit=20', { cache: 'no-store', credentials: 'same-origin' });
      const j = await res.json().catch(() => ({}));
      setAllJobs(res.ok ? (j.jobs || []) : []);
    } catch {
      setAllJobs([]);
    } finally {
      setLoadingJobs(false);
    }
  }, []);

  // A imagem so viaja quando alguem pede: a listagem manda `tem_screenshot`, e a
  // linha unica (`job_id=`) e que traz o base64. 20 provas de uma vez seriam MBs
  // que quase ninguem abre.
  const verProva = useCallback(async (job: PortalJob) => {
    if (job.prova) { window.open(job.prova, '_blank', 'noreferrer'); return; }
    if (provas[job.id]) { setProvas((p) => ({ ...p, [job.id]: '' })); return; }
    setBusy(job.id);
    try {
      const res = await fetch(`/api/dashboard/portal-jobs?job_id=${encodeURIComponent(job.id)}`, { cache: 'no-store', credentials: 'same-origin' });
      const j = await res.json().catch(() => ({}));
      const img = res.ok ? String(j.job?.screenshot || '') : '';
      if (!img) { setNotice('Este acionamento não guardou uma imagem da tela.'); return; }
      setProvas((p) => ({ ...p, [job.id]: img }));
    } catch {
      setNotice('Não consegui abrir a prova agora.');
    } finally {
      setBusy('');
    }
  }, [provas]);

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
      loadAllJobs();
    } catch { setNotice('Falha de conexão.'); setPortals([]); }
  }, [loadHitlJobs, loadAllJobs]);
  useEffect(() => { load(); }, [load]);

  // Enquanto houver trabalho na fila ou em andamento, a tela se atualiza sozinha
  // a cada 30 s. Quando tudo termina, o timer para — nao adianta bater no banco
  // de 30 em 30 segundos para ver a mesma lista parada.
  const temTrabalhoVivo = (allJobs || []).some((j) => EM_CURSO.includes(j.status));
  useEffect(() => {
    if (!temTrabalhoVivo) return;
    const t = setInterval(() => { loadAllJobs(); loadHitlJobs(); }, 30000);
    return () => clearInterval(t);
  }, [temTrabalhoVivo, loadAllJobs, loadHitlJobs]);

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
    await loadAllJobs();
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
    await loadAllJobs();
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

        <section className="space-y-3">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
              <Activity className="h-4 w-4 text-muted-foreground" />
              Acionamentos no portal
            </div>
            <button
              onClick={() => loadAllJobs()}
              disabled={loadingJobs}
              className="inline-flex items-center gap-1 rounded-md border border-border bg-surface px-3 py-1.5 text-xs font-medium text-foreground hover:bg-surface-2 disabled:opacity-50"
            >
              {loadingJobs ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
              Atualizar
            </button>
          </div>
          <p className="text-[11px] text-faint">
            O que os agentes fizeram nos portais da sua corretora — do mais recente para o mais antigo.
            {temTrabalhoVivo && ' Tem trabalho acontecendo agora: esta lista se atualiza sozinha a cada 30 segundos.'}
          </p>

          {allJobs === null ? (
            <div className="flex items-center gap-2 py-4 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" /> Carregando acionamentos…
            </div>
          ) : allJobs.length === 0 ? (
            <p className="rounded-xl border border-border bg-surface px-4 py-6 text-center text-sm text-muted-foreground">
              Nenhum acionamento ainda. Quando um agente entrar num portal pela sua corretora, ele aparece aqui.
            </p>
          ) : (
            <div className="space-y-3">
              {allJobs.map((job) => {
                const estado = estadoDe(job.status);
                const inicio = hora(job.started_at || job.created_at);
                const fim = hora(job.finished_at);
                const temProva = !!job.prova || !!job.tem_screenshot;
                return (
                  <div key={job.id} className="rounded-xl border border-border bg-surface p-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-sm font-semibold text-foreground">{job.portal_name}</p>
                      <span className={`rounded-full border px-2 py-0.5 text-[10px] font-medium ${estado.classe}`}>
                        {estado.label}
                      </span>
                      <span className="rounded-full border border-border bg-surface-2 px-2 py-0.5 text-[10px] text-muted-foreground">
                        {jornadaLabel(job.journey)}
                      </span>
                    </div>

                    {job.protocolo && (
                      <p className="mt-2 inline-flex items-center gap-2 rounded-md border border-emerald-500/30 bg-emerald-500/10 px-3 py-1.5 text-sm font-semibold text-emerald-600">
                        Protocolo {job.protocolo}
                      </p>
                    )}

                    {(job.resumo || job.message) && (
                      <p className="mt-2 text-xs text-muted-foreground">{job.resumo || job.message}</p>
                    )}

                    <p className="mt-2 text-[11px] text-faint">
                      {inicio ? `Começou em ${inicio}` : 'Ainda não começou'}
                      {fim ? ` · terminou em ${fim}` : ''}
                      {job.passos ? ` · ${job.passos} passos no portal` : ''}
                      {job.attempts > 1 ? ` · ${job.attempts}ª tentativa` : ''}
                    </p>

                    {temProva && (
                      <button
                        onClick={() => verProva(job)}
                        disabled={busy === job.id}
                        className="mt-3 inline-flex items-center gap-1 rounded-md border border-border bg-surface-2 px-3 py-1.5 text-xs font-medium text-foreground hover:bg-surface disabled:opacity-50"
                      >
                        {busy === job.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          : job.prova ? <ExternalLink className="h-3.5 w-3.5" /> : <ImageIcon className="h-3.5 w-3.5" />}
                        {provas[job.id] ? 'Esconder a prova' : 'Ver prova'}
                      </button>
                    )}

                    {provas[job.id] && (
                      <a href={provas[job.id]} target="_blank" rel="noreferrer">
                        <img
                          src={provas[job.id]}
                          alt={`Tela do ${job.portal_name} no fim do acionamento`}
                          className="mt-3 max-h-96 w-full rounded-md border border-border object-contain"
                        />
                      </a>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </section>

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
