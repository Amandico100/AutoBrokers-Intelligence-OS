'use client';

// SPEC-022/036 (founder 14/07): Seguradoras como HUB PREMIUM — grade de cards
// estilo "plugins" (monograma da marca, status do corredor), e o clique abre o
// detalhe da seguradora com ABAS (Canais · Portais & Vidros · Corredores).
// Antes era uma lista densa; o founder pediu cards com a cara da marca.

import { useEffect, useMemo, useState } from 'react';

type Channel = { label: string; kind: 'whatsapp' | 'phone'; available: boolean; number: string | null };
type Item = {
  insurer_key: string;
  display_name: string;
  active_corridors: number;
  has_active_corridor: boolean;
  channels: Channel[];
  glass_service_portal_url: string | null;
  notes: string | null;
};

/** Cores oficiais aproximadas das marcas — dá identidade sem depender de logo hospedado. */
const BRAND: Record<string, { bg: string; fg: string; mono: string }> = {
  porto: { bg: '#00A1FC', fg: '#ffffff', mono: 'P' },
  allianz: { bg: '#003781', fg: '#ffffff', mono: 'A' },
  azul: { bg: '#0072CE', fg: '#ffffff', mono: 'Az' },
  bradesco: { bg: '#CC092F', fg: '#ffffff', mono: 'B' },
  hdi: { bg: '#00714B', fg: '#ffffff', mono: 'H' },
  itau: { bg: '#EC7000', fg: '#ffffff', mono: 'It' },
  mapfre: { bg: '#D81E05', fg: '#ffffff', mono: 'M' },
  tokio: { bg: '#00A650', fg: '#ffffff', mono: 'TM' },
  yelum: { bg: '#5B2D90', fg: '#ffffff', mono: 'Y' },
  youse: { bg: '#F65C78', fg: '#ffffff', mono: 'Yo' },
  zurich: { bg: '#2167AE', fg: '#ffffff', mono: 'Z' },
  alfa: { bg: '#004B8D', fg: '#ffffff', mono: 'Al' },
  sulamerica: { bg: '#F36F21', fg: '#ffffff', mono: 'S' },
  sompo: { bg: '#CE0E2D', fg: '#ffffff', mono: 'So' },
  suhai: { bg: '#111111', fg: '#ffffff', mono: 'Su' },
};

function brandOf(key: string, name: string) {
  return BRAND[key] || { bg: '#334155', fg: '#ffffff', mono: (name || '?').slice(0, 1).toUpperCase() };
}

type Tab = 'canais' | 'portais' | 'corredores';

export function InsurersClient() {
  const [items, setItems] = useState<Item[] | null>(null);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>('canais');

  useEffect(() => {
    fetch('/api/dashboard/insurers').then((r) => r.json()).then((j) => { if (j?.ok) setItems(j.items); }).catch(() => {});
  }, []);

  const selected = useMemo(
    () => (items || []).find((i) => i.insurer_key === selectedKey) || null,
    [items, selectedKey],
  );

  if (!items) return <p className="text-sm text-muted-foreground">Carregando…</p>;

  // ---------- Detalhe da seguradora (hub com abas) ----------
  if (selected) {
    const b = brandOf(selected.insurer_key, selected.display_name);
    const whats = selected.channels.filter((c) => c.kind === 'whatsapp');
    const phones = selected.channels.filter((c) => c.kind !== 'whatsapp');
    const tabBtn = (t: Tab, label: string) => (
      <button
        key={t}
        onClick={() => setTab(t)}
        className={`rounded-full px-3.5 py-1.5 text-xs font-medium transition-colors ${
          tab === t ? 'bg-foreground text-background' : 'bg-surface-2 text-muted-foreground hover:text-foreground'
        }`}
      >
        {label}
      </button>
    );
    return (
      <div className="space-y-4">
        <button onClick={() => setSelectedKey(null)} className="text-xs text-muted-foreground hover:text-foreground">
          ← Todas as seguradoras
        </button>
        <div className="overflow-hidden rounded-2xl border border-border bg-card">
          <div className="flex items-center gap-4 border-b border-border p-5" style={{ background: `linear-gradient(135deg, ${b.bg}22, transparent 60%)` }}>
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl text-lg font-bold shadow-sm" style={{ backgroundColor: b.bg, color: b.fg }}>
              {b.mono}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-base font-semibold text-foreground">{selected.display_name}</p>
              {selected.has_active_corridor ? (
                <span className="mt-1 inline-block rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-600">
                  {selected.active_corridors} corredor(es) ativo(s)
                </span>
              ) : (
                <span className="mt-1 inline-block rounded-full border border-border bg-surface-2 px-2 py-0.5 text-[10px] text-muted-foreground">
                  Sem corredor ativo
                </span>
              )}
            </div>
          </div>
          <div className="flex gap-2 border-b border-border px-5 py-3">
            {tabBtn('canais', `Canais (${selected.channels.length})`)}
            {tabBtn('portais', 'Portais & Vidros')}
            {tabBtn('corredores', 'Corredores')}
          </div>
          <div className="p-5">
            {tab === 'canais' && (
              <div className="space-y-4">
                {whats.length > 0 && (
                  <div>
                    <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">WhatsApp</p>
                    <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
                      {whats.map((c) => (
                        <div key={c.label} className="flex items-center justify-between rounded-lg border border-border bg-background px-3 py-2 text-xs">
                          <span className="text-muted-foreground">💬 {c.label}</span>
                          <span className="font-mono text-foreground">{c.number ?? '—'}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {phones.length > 0 && (
                  <div>
                    <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Telefone</p>
                    <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
                      {phones.map((c) => (
                        <div key={c.label} className="flex items-center justify-between rounded-lg border border-border bg-background px-3 py-2 text-xs">
                          <span className="text-muted-foreground">{c.label}</span>
                          <span className="font-mono text-foreground">{c.number ?? '—'}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {selected.channels.length === 0 && (
                  <p className="text-sm text-muted-foreground">Nenhum canal cadastrado para esta seguradora.</p>
                )}
              </div>
            )}
            {tab === 'portais' && (
              <div className="space-y-3">
                {selected.glass_service_portal_url ? (
                  <div className="rounded-lg border border-border bg-background px-3 py-2.5 text-xs">
                    <p className="mb-1 font-semibold text-foreground">Portal de vidros</p>
                    <a href={selected.glass_service_portal_url} target="_blank" rel="noreferrer" className="break-all text-primary hover:underline">
                      {selected.glass_service_portal_url}
                    </a>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">Sem portal de vidros cadastrado.</p>
                )}
                <a href="/dashboard/personalizacao/conectores/portais" className="inline-block rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs font-medium text-foreground hover:bg-muted">
                  Credenciais de portal da corretora →
                </a>
              </div>
            )}
            {tab === 'corredores' && (
              <div className="space-y-3">
                {/* SPEC-063 — esta tela dizia:
                   *   "…corredor(es) ativo(s) nesta seguradora — o atendente já
                   *    aciona por eles."
                   *   "Ative para o atendente acionar esta seguradora
                   *    automaticamente."
                   *
                   * As duas frases eram falsas. Quem aciona é a InsurerDispatchTool,
                   * e ela resolve o roteiro por (seguradora, ramo) contra dicionários
                   * EM MEMÓRIA — nunca abre o banco. Ativar ou pausar um corredor
                   * aqui não mudava absolutamente nada no que o atendente conseguia
                   * fazer. A regra que ligaria as duas pontas (isCorridorOperable)
                   * foi apagada em 20/07 junto com o runtime órfão.
                   *
                   * Uma tela que promete capacidade inexistente é pior que uma tela
                   * vazia: a corretora clica, acredita, e conta com isso. */}
                <p className="text-sm text-muted-foreground">
                  {selected.has_active_corridor
                    ? `Sua corretora marcou ${selected.active_corridors} corredor(es) como ativo(s) nesta seguradora.`
                    : 'Nenhum corredor marcado como ativo nesta seguradora.'}
                </p>
                <p className="text-xs text-muted-foreground">
                  Ativar aqui registra a intenção da corretora. Quem aciona de fato é o
                  roteiro de atendimento, e ele é o mesmo para todas — nenhuma ação
                  externa, envio ou portal é executado por esta tela.
                </p>
                <a href="/dashboard/personalizacao/corredores" className="inline-block rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs font-medium text-foreground hover:bg-muted">
                  Gerenciar corredores →
                </a>
              </div>
            )}
          </div>
        </div>
        {selected.notes && <p className="text-[11px] text-faint">{selected.notes}</p>}
      </div>
    );
  }

  // ---------- Grade premium ----------
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {items.map((it) => {
          const b = brandOf(it.insurer_key, it.display_name);
          const whatsCount = it.channels.filter((c) => c.kind === 'whatsapp').length;
          return (
            <button
              key={it.insurer_key}
              onClick={() => { setSelectedKey(it.insurer_key); setTab('canais'); }}
              className="group relative overflow-hidden rounded-2xl border border-border bg-card p-4 text-left transition-all hover:-translate-y-0.5 hover:border-foreground/20 hover:shadow-lg"
            >
              <div className="pointer-events-none absolute inset-x-0 top-0 h-16 opacity-[0.10] transition-opacity group-hover:opacity-[0.18]" style={{ background: `linear-gradient(135deg, ${b.bg}, transparent 70%)` }} />
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl text-sm font-bold shadow-sm" style={{ backgroundColor: b.bg, color: b.fg }}>
                  {b.mono}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold text-foreground">{it.display_name}</p>
                  <p className="text-[11px] text-muted-foreground">
                    {it.channels.length} canais{whatsCount > 0 ? ` · ${whatsCount} WhatsApp` : ''}
                  </p>
                </div>
              </div>
              <div className="mt-3 flex items-center justify-between">
                {it.has_active_corridor ? (
                  <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-600">
                    {it.active_corridors} corredor(es) ativo(s)
                  </span>
                ) : (
                  <span className="rounded-full border border-border bg-surface-2 px-2 py-0.5 text-[10px] text-muted-foreground">
                    Sem corredor ativo
                  </span>
                )}
                <span className="text-[11px] font-medium text-muted-foreground transition-colors group-hover:text-foreground">Abrir hub →</span>
              </div>
            </button>
          );
        })}
      </div>
      <p className="text-[10px] text-faint">
        Contatos globais curados pela plataforma (somente leitura). Seu atendente usa apenas os corredores que sua corretora ativar.
      </p>
    </div>
  );
}
