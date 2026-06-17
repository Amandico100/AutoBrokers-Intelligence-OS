'use client';

import { useCallback, useEffect, useState } from 'react';
import { Radio, ShieldAlert } from 'lucide-react';

interface ChannelConfig {
  config_id: string;
  insurer_key: string;
  corridor_key: string | null;
  subcorridor_key: string | null;
  channel: string;
  provider_key: string;
  mode: string;
  destination_ref_masked: string | null;
  destination_kind: string;
  homologation_status: string;
  priority: number;
  is_active: boolean;
  send_real_allowed: boolean;
}

const PROVIDERS = ['zapi', 'evolution_go', 'meta_cloud', 'manual', 'future_custom'];

export default function InsurerActionChannelsPage() {
  const [configs, setConfigs] = useState<ChannelConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState('');
  const [form, setForm] = useState({ insurer_key: '', corridor_key: '', subcorridor_key: '', provider_key: 'zapi', destination_ref: '' });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/admin/insurer-action-channels');
      const json = await res.json().catch(() => ({}));
      if (json?.ok) setConfigs(json.configs || []);
      else setNotice(json?.error || 'Falha ao carregar.');
    } catch {
      setNotice('Falha ao carregar.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const create = async () => {
    if (!form.insurer_key.trim()) { setNotice('Informe a seguradora.'); return; }
    setNotice('');
    try {
      const res = await fetch('/api/admin/insurer-action-channels', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          insurer_key: form.insurer_key.trim(),
          corridor_key: form.corridor_key.trim() || null,
          subcorridor_key: form.subcorridor_key.trim() || null,
          provider_key: form.provider_key,
          destination_ref: form.destination_ref.trim() || null,
        }),
      });
      const json = await res.json().catch(() => ({}));
      if (json?.ok) { setForm({ insurer_key: '', corridor_key: '', subcorridor_key: '', provider_key: 'zapi', destination_ref: '' }); await load(); }
      else setNotice(json?.error || 'Falha ao criar.');
    } catch {
      setNotice('Falha ao criar.');
    }
  };

  const remove = async (id: string) => {
    try {
      await fetch(`/api/admin/insurer-action-channels/${id}`, { method: 'DELETE' });
      await load();
    } catch { setNotice('Falha ao remover.'); }
  };

  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="mb-2 flex items-center gap-3 text-3xl font-bold text-foreground">
          <Radio className="h-7 w-7" /> Canais de acionamento (seguradora)
        </h1>
        <p className="text-sm text-muted-foreground">
          Configuração global, provider-agnostic (Z-API, Evolution Go, Meta Cloud, manual). Por seguradora/corredor/subcorredor.
        </p>
      </div>

      <div className="mb-6 flex items-center gap-2 rounded-lg border border-amber-500/40 bg-amber-500/5 px-4 py-2 text-sm text-amber-600">
        <ShieldAlert className="h-4 w-4" /> Envio real bloqueado — esta tela apenas configura o sandbox (send_real_allowed=false).
      </div>

      {notice && <p className="mb-4 text-sm text-muted-foreground">{notice}</p>}

      <div className="mb-6 rounded-lg border border-border bg-card p-4">
        <p className="mb-3 text-sm font-medium text-foreground">Adicionar canal</p>
        <div className="grid grid-cols-1 gap-2 md:grid-cols-5">
          <input value={form.insurer_key} onChange={(e) => setForm({ ...form, insurer_key: e.target.value })} placeholder="seguradora (ex: allianz)" className="rounded-lg border border-border bg-background px-3 py-2 text-sm" />
          <input value={form.corridor_key} onChange={(e) => setForm({ ...form, corridor_key: e.target.value })} placeholder="corredor (opcional)" className="rounded-lg border border-border bg-background px-3 py-2 text-sm" />
          <input value={form.subcorridor_key} onChange={(e) => setForm({ ...form, subcorridor_key: e.target.value })} placeholder="subcorredor (opcional)" className="rounded-lg border border-border bg-background px-3 py-2 text-sm" />
          <select value={form.provider_key} onChange={(e) => setForm({ ...form, provider_key: e.target.value })} className="rounded-lg border border-border bg-background px-3 py-2 text-sm">
            {PROVIDERS.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
          <input value={form.destination_ref} onChange={(e) => setForm({ ...form, destination_ref: e.target.value })} placeholder="destino (mascarado ao salvar)" className="rounded-lg border border-border bg-background px-3 py-2 text-sm" />
        </div>
        <button onClick={create} className="mt-3 rounded-lg border border-primary/40 bg-primary/5 px-3 py-1.5 text-sm font-medium text-primary hover:bg-primary/10">
          Adicionar (sandbox)
        </button>
      </div>

      {loading ? (
        <p className="text-sm text-muted-foreground">Carregando…</p>
      ) : configs.length === 0 ? (
        <p className="text-sm text-muted-foreground">Nenhum canal configurado. Sem config, o acionamento cai em handoff manual.</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="w-full text-sm">
            <thead className="bg-surface-2 text-left text-xs uppercase tracking-wide text-faint">
              <tr>
                <th className="px-3 py-2">Seguradora</th>
                <th className="px-3 py-2">Corredor / Sub</th>
                <th className="px-3 py-2">Provider</th>
                <th className="px-3 py-2">Canal</th>
                <th className="px-3 py-2">Destino</th>
                <th className="px-3 py-2">Homologação</th>
                <th className="px-3 py-2">Envio real</th>
                <th className="px-3 py-2"></th>
              </tr>
            </thead>
            <tbody>
              {configs.map((c) => (
                <tr key={c.config_id} className="border-t border-border">
                  <td className="px-3 py-2 text-foreground">{c.insurer_key}</td>
                  <td className="px-3 py-2 text-muted-foreground">{c.corridor_key ?? '—'}{c.subcorridor_key ? ` / ${c.subcorridor_key}` : ''}</td>
                  <td className="px-3 py-2 text-foreground">{c.provider_key}</td>
                  <td className="px-3 py-2 text-muted-foreground">{c.channel}</td>
                  <td className="px-3 py-2 text-muted-foreground">{c.destination_ref_masked ?? '—'}</td>
                  <td className="px-3 py-2 text-muted-foreground">{c.homologation_status}</td>
                  <td className="px-3 py-2"><span className="font-medium text-amber-600">bloqueado</span></td>
                  <td className="px-3 py-2"><button onClick={() => remove(c.config_id)} className="text-xs text-red-500 hover:underline">remover</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
