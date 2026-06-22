'use client';

// SPEC-013 Fase B P2 — Blueprint Center (master). Inicializa o Studio (Source Agents)
// e publica as releases globais reais. Disparo manual; nada automático no load.
import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Loader2, Bot, Headphones, PackageCheck, ShieldCheck } from 'lucide-react';

type SourceAgent = { id: string; name: string; role: string; audience: string; is_active: boolean; blueprint_key: string };
type Release = { id: string; blueprint_key: string; version: string; status: string; hash: string; risk: string; published_at: string | null };
type Status = { ok: boolean; studio_present: boolean; studio_company_id?: string; source_agents: SourceAgent[]; releases: Release[]; core_published?: boolean; even_published?: boolean; has_draft?: boolean };

const GLOBAL_BLUEPRINTS = [
  { key: 'autobrokers-core-v1', label: 'AutoBrokers Global' },
  { key: 'even-attendance-v1', label: 'Even Global' },
];

export default function BlueprintCenterPage() {
  const [status, setStatus] = useState<Status | null>(null);
  const [busy, setBusy] = useState('');
  const [notice, setNotice] = useState('');
  const [err, setErr] = useState('');

  const load = useCallback(async () => {
    const j = await fetch('/api/admin/blueprint-center').then((r) => r.json()).catch(() => ({}));
    if (j?.ok) setStatus(j); else setErr(j?.error || 'Falha ao carregar');
  }, []);
  useEffect(() => { load(); }, [load]);

  const run = async (path: string, label: string, body?: Record<string, unknown>) => {
    setBusy(label); setNotice(''); setErr('');
    const r = await fetch(`/api/admin/blueprint-center/${path}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: body ? JSON.stringify(body) : undefined,
    });
    const j = await r.json().catch(() => ({}));
    if (j?.ok) { setNotice(`${label}: concluído.`); await load(); }
    else setErr(`${label}: ${j?.error || r.status}${Array.isArray(j?.details) ? ' — ' + j.details.join(', ') : ''}`);
    setBusy('');
  };

  if (err && !status) return <div className="p-6 text-sm text-red-600">Erro: {err} (acesso master necessário)</div>;
  if (!status) return <div className="flex items-center gap-2 p-6 text-sm text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin" /> Carregando…</div>;

  const hasCore = status.source_agents.some((a) => a.role === 'core');
  const hasEven = status.source_agents.some((a) => a.role === 'attendance');
  const studioReady = status.studio_present && hasCore && hasEven;
  const releasesReady = status.releases.length >= 2;

  return (
    <div className="mx-auto w-full max-w-4xl space-y-4 p-6">
      <div>
        <h1 className="text-xl font-semibold">Blueprint Center</h1>
        <p className="text-sm text-muted-foreground">Autoria global do AutoBrokers, da Even e dos Auxiliares no AutoBrokers Blueprint Studio. As versões publicadas são distribuídas às corretoras.</p>
      </div>

      {/* Passo 1 — Inicializar Studio */}
      <Card><CardContent className="p-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="flex items-center gap-2 font-medium"><ShieldCheck className="h-4 w-4" /> 1. Inicializar o Studio</p>
            <p className="mt-1 text-sm text-muted-foreground">Cria os Source Agents globais (AutoBrokers Core + Even) dentro do Studio, usando o motor do Smith. Idempotente.</p>
          </div>
          {studioReady
            ? <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[11px] font-medium text-emerald-600">Pronto</span>
            : <button onClick={() => run('initialize', 'Inicializar Studio')} disabled={!!busy} className="rounded-lg border border-primary/40 bg-primary/5 px-4 py-1.5 text-sm font-medium text-primary hover:bg-primary/10 disabled:opacity-50">{busy === 'Inicializar Studio' ? 'Criando…' : 'Inicializar'}</button>}
        </div>
        <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
          <div className="rounded-md border border-border bg-background px-3 py-2 text-[12px]"><Bot className="mr-1 inline h-3.5 w-3.5" /> AutoBrokers Global Core — {hasCore ? 'criado' : 'pendente'}</div>
          <div className="rounded-md border border-border bg-background px-3 py-2 text-[12px]"><Headphones className="mr-1 inline h-3.5 w-3.5" /> Even Global Attendance — {hasEven ? 'criado' : 'pendente'}</div>
        </div>
      </CardContent></Card>

      {/* Passo 2 — Publicar releases */}
      <Card><CardContent className="p-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="flex items-center gap-2 font-medium"><PackageCheck className="h-4 w-4" /> 2. Publicar releases v1.0.0</p>
            <p className="mt-1 text-sm text-muted-foreground">Gera as releases globais imutáveis (artefato sanitizado + SHA-256). Bloqueia segredos e tools/MCP livres. Idempotente.</p>
          </div>
          {releasesReady
            ? <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[11px] font-medium text-emerald-600">Publicadas</span>
            : <button onClick={() => run('publish-seed', 'Publicar releases')} disabled={!!busy || !studioReady} className="rounded-lg border border-primary/40 bg-primary/5 px-4 py-1.5 text-sm font-medium text-primary hover:bg-primary/10 disabled:opacity-50">{busy === 'Publicar releases' ? 'Publicando…' : 'Publicar'}</button>}
        </div>
        {!studioReady && <p className="mt-2 text-[11px] text-amber-600">Inicialize o Studio antes de publicar.</p>}
        <div className="mt-3 divide-y divide-border">
          {status.releases.length === 0 && <p className="py-2 text-[12px] text-muted-foreground">Nenhuma release publicada ainda.</p>}
          {status.releases.map((r) => (
            <div key={`${r.blueprint_key}@${r.version}`} className="flex items-center justify-between py-2 text-[12px]">
              <span className="text-foreground">{r.blueprint_key} <span className="text-faint">v{r.version}</span></span>
              <span className="flex items-center gap-2">
                <span className="text-emerald-600">{r.status}</span>
                <span className="font-mono text-faint" title={r.hash}>{r.hash.slice(0, 18)}…</span>
              </span>
            </div>
          ))}
        </div>
      </CardContent></Card>

      {/* Passo 3 — Evolução (editar Source Agent no Studio → nova versão) */}
      {releasesReady && (
        <Card><CardContent className="p-4">
          <p className="flex items-center gap-2 font-medium"><PackageCheck className="h-4 w-4" /> 3. Evolução do padrão global</p>
          <p className="mt-1 text-sm text-muted-foreground">Edite o Source Agent no Studio (abas do Smith) e gere uma nova versão a partir dele. A nova versão nasce como rascunho; publicar a torna imutável. Releases já publicadas nunca mudam.</p>
          {GLOBAL_BLUEPRINTS.map((g) => {
            const versions = status.releases.filter((r) => r.blueprint_key === g.key);
            return (
              <div key={g.key} className="mt-3 rounded-md border border-border bg-background p-3">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium text-foreground">{g.label} <span className="text-faint">({g.key})</span></p>
                  <button onClick={() => run('create-draft', `Nova versão ${g.label}`, { blueprint_key: g.key, bump: 'minor' })} disabled={!!busy} className="rounded-lg border border-border px-3 py-1 text-[12px] text-muted-foreground hover:bg-surface-2 disabled:opacity-50">Criar nova versão (draft)</button>
                </div>
                <div className="mt-2 divide-y divide-border">
                  {versions.map((r) => (
                    <div key={r.id} className="flex items-center justify-between py-1.5 text-[12px]">
                      <span>v{r.version} · <span className={r.status === 'published' ? 'text-emerald-600' : r.status === 'draft' ? 'text-amber-600' : 'text-faint'}>{r.status}</span></span>
                      {r.status === 'draft' && (
                        <button onClick={() => run('publish-draft', `Publicar v${r.version}`, { release_id: r.id })} disabled={!!busy} className="rounded-lg border border-primary/40 bg-primary/5 px-3 py-0.5 text-[12px] font-medium text-primary hover:bg-primary/10 disabled:opacity-50">Publicar</button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </CardContent></Card>
      )}

      {notice && <p className="text-[12px] text-emerald-600">{notice}</p>}
      {err && <p className="text-[12px] text-red-600">{err}</p>}
      <p className="text-[10px] text-muted-foreground">O Studio é uma empresa técnica da plataforma (não-cliente). Releases publicadas são imutáveis. Nada aqui liga WhatsApp, portal ou provider externo.</p>
    </div>
  );
}
