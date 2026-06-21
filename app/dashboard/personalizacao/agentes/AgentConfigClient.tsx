'use client';

import { useCallback, useEffect, useState } from 'react';

type Variable = { key: string; label: string; value: string };
type Config = {
  blueprint_version: string;
  role: string;
  brand_locked_name: string | null;
  display_name: string;
  editable_variables: Variable[];
  editable_override_fields: string[];
  current_overrides: Record<string, unknown>;
};

// Campos de override que NÃO são variáveis (entram como inputs próprios).
const OVERRIDE_INPUTS: Record<string, { label: string; type: 'url' | 'text' | 'number' }> = {
  avatar_url: { label: 'Avatar (URL da imagem)', type: 'url' },
  voice: { label: 'Voz (perfil)', type: 'text' },
  llm_temperature: { label: 'Criatividade (0.0–1.0)', type: 'number' },
};

export function AgentConfigClient({ agentKey }: { agentKey: 'autobrokers' | 'even' }) {
  const [config, setConfig] = useState<Config | null>(null);
  const [provisioned, setProvisioned] = useState(true);
  const [vars, setVars] = useState<Record<string, string>>({});
  const [overrides, setOverrides] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');

  const load = useCallback(async () => {
    const j = await fetch(`/api/dashboard/agents/${agentKey}`).then((r) => r.json()).catch(() => ({}));
    if (j?.ok) {
      setProvisioned(Boolean(j.provisioned));
      const c: Config = j.config;
      setConfig(c);
      const v: Record<string, string> = {};
      for (const it of c.editable_variables) v[it.key] = it.value;
      setVars(v);
      const o: Record<string, string> = {};
      for (const f of c.editable_override_fields) {
        if (OVERRIDE_INPUTS[f]) o[f] = c.current_overrides?.[f] != null ? String(c.current_overrides[f]) : '';
      }
      setOverrides(o);
    } else setNotice(j?.error || 'Falha ao carregar.');
  }, [agentKey]);
  useEffect(() => { load(); }, [load]);

  const save = async () => {
    setBusy(true); setNotice('');
    const overridesPayload: Record<string, unknown> = {};
    for (const [k, val] of Object.entries(overrides)) {
      if (val === '' || val == null) continue;
      overridesPayload[k] = OVERRIDE_INPUTS[k]?.type === 'number' ? Number(val) : val;
    }
    const r = await fetch(`/api/dashboard/agents/${agentKey}`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ variables: vars, overrides: overridesPayload }),
    });
    const j = await r.json().catch(() => ({}));
    if (j?.ok) { setNotice('Alterações salvas.'); await load(); }
    else setNotice(`Falha ao salvar: ${j?.error || r.status}`);
    setBusy(false);
  };
  const reset = async () => {
    setBusy(true); setNotice('');
    const r = await fetch(`/api/dashboard/agents/${agentKey}/reset`, { method: 'POST' });
    const j = await r.json().catch(() => ({}));
    if (j?.ok) { setNotice('Restaurado ao padrão.'); await load(); }
    else setNotice(`Falha ao restaurar: ${j?.error || r.status}`);
    setBusy(false);
  };

  if (!config) return <p className="text-sm text-muted-foreground">Carregando…</p>;

  const opening = vars.opening_message;
  const overrideOnly = config.editable_override_fields.filter((f) => OVERRIDE_INPUTS[f]);

  return (
    <div className="space-y-6">
      {/* Identidade / prévia */}
      <div className="rounded-lg border border-border bg-card p-4">
        <p className="text-[11px] uppercase tracking-wide text-faint">Apresentação</p>
        <p className="mt-1 text-lg font-semibold text-foreground">{config.display_name}</p>
        {config.brand_locked_name && <p className="mt-1 text-[11px] text-amber-600">A marca “AutoBrokers” é fixa e não pode ser renomeada.</p>}
        {opening && <p className="mt-2 rounded-md border border-border bg-background px-3 py-2 text-sm text-muted-foreground">“{opening}”</p>}
        {!provisioned && <p className="mt-2 text-[11px] text-amber-600">Agente ainda não provisionado para esta corretora.</p>}
      </div>

      {/* Variáveis editáveis */}
      <div className="rounded-lg border border-border bg-card p-4">
        <p className="mb-3 text-sm font-medium text-foreground">Personalização</p>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {config.editable_variables.map((v) => (
            <label key={v.key} className="block text-[12px]">
              <span className="text-muted-foreground">{v.label}</span>
              <input
                value={vars[v.key] ?? ''}
                onChange={(e) => setVars((p) => ({ ...p, [v.key]: e.target.value }))}
                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground"
              />
            </label>
          ))}
          {overrideOnly.map((f) => (
            <label key={f} className="block text-[12px]">
              <span className="text-muted-foreground">{OVERRIDE_INPUTS[f].label}</span>
              <input
                type={OVERRIDE_INPUTS[f].type === 'number' ? 'number' : 'text'}
                step={OVERRIDE_INPUTS[f].type === 'number' ? '0.1' : undefined}
                min={OVERRIDE_INPUTS[f].type === 'number' ? '0' : undefined}
                max={OVERRIDE_INPUTS[f].type === 'number' ? '1' : undefined}
                value={overrides[f] ?? ''}
                onChange={(e) => setOverrides((p) => ({ ...p, [f]: e.target.value }))}
                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground"
              />
            </label>
          ))}
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <button onClick={save} disabled={busy} className="rounded-lg border border-primary/40 bg-primary/5 px-4 py-1.5 text-sm font-medium text-primary hover:bg-primary/10 disabled:opacity-50">{busy ? 'Salvando…' : 'Salvar alterações'}</button>
          <button onClick={reset} disabled={busy} className="rounded-lg border border-border px-4 py-1.5 text-sm text-muted-foreground hover:bg-surface-2 disabled:opacity-50">Restaurar padrão</button>
          {notice && <span className="text-[12px] text-muted-foreground">{notice}</span>}
        </div>
        <p className="mt-2 text-[10px] text-faint">As instruções protegidas, regras de segurança e o modelo não são editáveis — garantem qualidade e segurança em todas as corretoras.</p>
      </div>
    </div>
  );
}
