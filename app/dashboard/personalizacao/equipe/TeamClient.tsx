'use client';

// SPEC-048 — Equipe da corretora ATIVA, gerida pelo dono/admin direto aqui:
// adicionar pessoa (senha provisória, sem confirmação de e-mail), clicar no
// membro abre o modal com os dados (editar/excluir — só admin). Membros
// comuns só visualizam. Quem pertence a 2 corretoras aparece nas duas.

import { useCallback, useEffect, useState } from 'react';
import { Loader2, Plus, X } from 'lucide-react';

type Member = {
  user_id: string; name: string; first_name: string; last_name: string;
  email: string | null; phone: string | null; role: string; role_label: string;
  is_owner: boolean; status: string | null; last_login_at: string | null;
};

const inputCls = 'mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground';

function fmtWhen(iso: string | null): string {
  if (!iso) return 'nunca entrou';
  return new Date(iso).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: '2-digit' });
}

export function TeamClient() {
  const [members, setMembers] = useState<Member[] | null>(null);
  const [canManage, setCanManage] = useState(false);
  const [me, setMe] = useState('');
  const [selected, setSelected] = useState<Member | null>(null);
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');

  const load = useCallback(async () => {
    try {
      const j = await fetch('/api/dashboard/team', { cache: 'no-store' }).then((r) => r.json());
      if (j?.ok) {
        setMembers(j.members);
        setCanManage(Boolean(j.can_manage));
        setMe(String(j.me || ''));
      }
    } catch {
      /* mantém a lista atual */
    }
  }, []);
  useEffect(() => { load(); }, [load]);

  const openMember = (m: Member) => {
    setSelected(m);
    setAdding(false);
    setNotice('');
    setForm({
      first_name: m.first_name, last_name: m.last_name,
      phone: m.phone || '', role: m.role, password: '',
    });
  };

  const openAdd = () => {
    setSelected(null);
    setAdding(true);
    setNotice('');
    setForm({ first_name: '', last_name: '', email: '', phone: '', role: 'member', password: 'mudar123' });
  };

  const close = () => { setSelected(null); setAdding(false); };

  const save = async () => {
    setBusy(true); setNotice('');
    try {
      const res = await fetch('/api/dashboard/team', {
        method: adding ? 'POST' : 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(adding
          ? { first_name: form.first_name, last_name: form.last_name, email: form.email, phone: form.phone, role: form.role, password: form.password }
          : { user_id: selected?.user_id, first_name: form.first_name, last_name: form.last_name, phone: form.phone, role: form.role, ...(form.password ? { password: form.password } : {}) }),
      });
      const j = await res.json().catch(() => ({}));
      if (j?.ok) { close(); await load(); return; }
      setNotice(j?.error || 'Não foi possível salvar.');
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    if (!selected) return;
    if (!window.confirm(`Remover ${selected.name} desta empresa? A conta continua existindo — só o acesso a ESTA corretora é removido.`)) return;
    setBusy(true); setNotice('');
    try {
      const res = await fetch('/api/dashboard/team', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: selected.user_id }),
      });
      const j = await res.json().catch(() => ({}));
      if (j?.ok) { close(); await load(); return; }
      setNotice(j?.error || 'Não foi possível remover.');
    } finally {
      setBusy(false);
    }
  };

  if (!members) return <p className="text-sm text-muted-foreground">Carregando…</p>;

  const modalOpen = adding || Boolean(selected);

  return (
    <div className="space-y-3">
      {canManage && (
        <button
          onClick={openAdd}
          className="inline-flex items-center gap-1.5 rounded-lg border border-primary/40 bg-brand-soft px-3 py-2 text-sm font-medium text-primary transition-colors hover:border-primary/70"
        >
          <Plus className="h-4 w-4" /> Adicionar pessoa
        </button>
      )}

      {members.length === 0 ? (
        <p className="text-sm text-muted-foreground">Nenhum membro cadastrado.</p>
      ) : (
        <div className="rounded-lg border border-border bg-card divide-y divide-border">
          {members.map((m) => (
            <button
              key={m.user_id}
              onClick={() => openMember(m)}
              className="flex w-full items-center justify-between gap-3 p-3 text-left transition-colors hover:bg-surface-2"
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-foreground">
                  {m.name}
                  {m.is_owner && <span className="ml-1 rounded-full border border-border px-1.5 py-0.5 text-[9px] uppercase tracking-wide text-faint">dono</span>}
                  {m.user_id === me && <span className="ml-1 text-[10px] text-muted-foreground">(você)</span>}
                </p>
                {m.email && <p className="truncate text-[11px] text-faint">{m.email}</p>}
              </div>
              <div className="shrink-0 text-right">
                <p className="text-[12px] text-muted-foreground">{m.role_label}</p>
                <p className="text-[10px] text-faint">último acesso: {fmtWhen(m.last_login_at)}</p>
              </div>
            </button>
          ))}
        </div>
      )}
      <p className="text-[10px] text-faint">
        Quem você adiciona entra na hora com a senha provisória — sem confirmação de e-mail.
        Donos aparecem em todas as corretoras deles; atendentes só na própria.
      </p>

      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={close}>
          <div
            className="w-full max-w-md rounded-xl border border-border bg-card p-5 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-foreground">
                {adding ? 'Adicionar pessoa' : selected?.name}
              </h2>
              <button onClick={close} className="rounded-md p-1 text-muted-foreground hover:text-foreground" aria-label="Fechar">
                <X className="h-4 w-4" />
              </button>
            </div>

            {!adding && selected && (
              <div className="mb-3 space-y-1 rounded-lg border border-border bg-surface-2 p-3 text-xs text-muted-foreground">
                <p><span className="text-faint">E-mail:</span> {selected.email}</p>
                {selected.phone && <p><span className="text-faint">Celular:</span> {selected.phone}</p>}
                <p><span className="text-faint">Papel:</span> {selected.role_label}{selected.is_owner ? ' · Dono' : ''}</p>
                <p><span className="text-faint">Último acesso:</span> {fmtWhen(selected.last_login_at)}</p>
              </div>
            )}

            {canManage ? (
              <div className="space-y-2">
                <div className="grid grid-cols-2 gap-2">
                  <label className="block text-[12px]">
                    <span className="text-muted-foreground">Nome</span>
                    <input value={form.first_name || ''} onChange={(e) => setForm((p) => ({ ...p, first_name: e.target.value }))} className={inputCls} />
                  </label>
                  <label className="block text-[12px]">
                    <span className="text-muted-foreground">Sobrenome</span>
                    <input value={form.last_name || ''} onChange={(e) => setForm((p) => ({ ...p, last_name: e.target.value }))} className={inputCls} />
                  </label>
                </div>
                {adding && (
                  <label className="block text-[12px]">
                    <span className="text-muted-foreground">E-mail (será o login)</span>
                    <input type="email" value={form.email || ''} onChange={(e) => setForm((p) => ({ ...p, email: e.target.value }))} className={inputCls} />
                  </label>
                )}
                <div className="grid grid-cols-2 gap-2">
                  <label className="block text-[12px]">
                    <span className="text-muted-foreground">Celular</span>
                    <input value={form.phone || ''} onChange={(e) => setForm((p) => ({ ...p, phone: e.target.value }))} className={inputCls} />
                  </label>
                  <label className="block text-[12px]">
                    <span className="text-muted-foreground">Papel</span>
                    <select
                      value={form.role || 'member'}
                      onChange={(e) => setForm((p) => ({ ...p, role: e.target.value }))}
                      disabled={Boolean(selected?.is_owner)}
                      className={inputCls}
                    >
                      <option value="member">Atendente / Membro</option>
                      <option value="admin_company">Administrador</option>
                    </select>
                  </label>
                </div>
                <label className="block text-[12px]">
                  <span className="text-muted-foreground">{adding ? 'Senha provisória' : 'Nova senha (deixe vazio para manter)'}</span>
                  <input value={form.password || ''} onChange={(e) => setForm((p) => ({ ...p, password: e.target.value }))} className={inputCls} />
                </label>

                {notice && <p className="text-xs text-red-500">{notice}</p>}

                <div className="mt-2 flex items-center gap-2">
                  <button
                    onClick={save}
                    disabled={busy}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-primary/40 bg-brand-soft px-3 py-2 text-sm font-medium text-primary disabled:opacity-50"
                  >
                    {busy && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                    {adding ? 'Adicionar' : 'Salvar'}
                  </button>
                  {!adding && selected && !selected.is_owner && selected.user_id !== me && (
                    <button
                      onClick={remove}
                      disabled={busy}
                      className="rounded-lg border border-red-500/40 px-3 py-2 text-sm text-red-500 transition-colors hover:bg-red-500/10 disabled:opacity-50"
                    >
                      Remover da empresa
                    </button>
                  )}
                </div>
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">
                Só administradores da corretora podem editar a equipe.
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
