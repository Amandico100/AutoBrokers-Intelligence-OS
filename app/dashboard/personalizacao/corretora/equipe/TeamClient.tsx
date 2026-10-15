'use client';

// SPEC-048 — Equipe da corretora ATIVA, gerida pelo dono/admin direto aqui:
// adicionar pessoa (senha provisória, sem confirmação de e-mail), clicar no
// membro abre o modal com os dados (editar/excluir — só admin). Membros
// comuns só visualizam. Quem pertence a 2 corretoras aparece nas duas.
//
// SPEC-131-0 A · F1 — cada pessoa tem um PAPEL de acesso (Administrador · Membro · Atendente) e FUNÇÕES de trabalho
// (Comercial · Calculista · Negociador), que são outra coisa: dizem o que ela faz, não o que ela pode. As listas, os
// rótulos e a ajuda vêm da política (`lib/admin/admin-auth-policy.ts`) — a mesma lista do CHECK do banco.

import { useCallback, useEffect, useState } from 'react';
import { Check, Copy, Loader2, Plus, X } from 'lucide-react';

// 🔴 SPEC-EXTRA-001.3 BLOCO B — D-PILOTO-09: a lista de números da casa
// mora AQUI, no card Equipe, e não em card próprio.
import { NumerosDaCasa } from './NumerosDaCasa';
import {
  AJUDA_DAS_FUNCOES, FUNCOES_DE_TRABALHO, O_QUE_O_PAPEL_PODE, PAPEIS_QUE_A_EQUIPE_DA, ROTULO_DA_FUNCAO, ROTULO_DO_PAPEL,
  type FuncaoDeTrabalho,
} from '@/lib/admin/admin-auth-policy';

// 🔴 SPEC-133-A.1 (achado do planejador, 10/10): a senha provisória era sempre "mudar123" — quem soubesse o e-mail de um
// membro novo entrava. Agora cada pessoa nasce com uma senha aleatória, que o admin vê (e pode trocar) antes de salvar.
function senhaProvisoria(): string {
  const letras = 'abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789';
  const bytes = new Uint32Array(12);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => letras[b % letras.length]).join('');
}

type Member = {
  user_id: string; name: string; first_name: string; last_name: string;
  email: string | null; phone: string | null; role: string; role_label: string;
  is_owner: boolean; status: string | null; last_login_at: string | null;
  funcoes?: string[];
};

const rotuloDaFuncao = (f: string) => ROTULO_DA_FUNCAO[f as FuncaoDeTrabalho] ?? f;

/** As funções de uma pessoa como etiquetas pequenas (só leitura). */
function EtiquetasDeFuncao({ funcoes }: { funcoes?: string[] }) {
  if (!funcoes?.length) return null;
  return (
    <span className="mt-1 flex flex-wrap gap-1" data-funcoes-do-membro>
      {funcoes.map((f) => (
        <span key={f} className="rounded-full border border-primary/30 bg-brand-soft px-2 py-0.5 text-[10px] font-medium text-primary">
          {rotuloDaFuncao(f)}
        </span>
      ))}
    </span>
  );
}

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
  // 🔴 conserto 133-A.1 (juiz P3-4): a senha com que a pessoa nasce aparece UMA vez, depois de salvar, com o botão
  // copiar — a que o servidor gerou (`senha_provisoria`, quando o campo foi apagado) ou a que o admin enviou. Antes, o
  // servidor devolvia a gerada e a tela a jogava fora: o membro nascia com uma senha que ninguém sabia.
  const [criada, setCriada] = useState<{ nome: string; email: string; senha: string } | null>(null);
  const [copiada, setCopiada] = useState(false);
  // as funções em edição no modal (comercial · calculista · negociador)
  const [funcoes, setFuncoes] = useState<string[]>([]);
  // aviso que fica na tela depois de fechar o modal (ex.: o Agger pessoal de quem saiu não foi desligado agora)
  const [aviso, setAviso] = useState('');

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
    setFuncoes(m.funcoes ?? []);
  };

  const openAdd = () => {
    setSelected(null);
    setAdding(true);
    setNotice('');
    setForm({ first_name: '', last_name: '', email: '', phone: '', role: 'member', password: senhaProvisoria() });
    setFuncoes([]);
  };

  // marca/desmarca uma função, mantendo a ordem da lista oficial
  const alternarFuncao = (f: string) =>
    setFuncoes((atual) => (atual.includes(f)
      ? atual.filter((x) => x !== f)
      : FUNCOES_DE_TRABALHO.filter((x) => x === f || atual.includes(x))));

  const close = () => { setSelected(null); setAdding(false); setCriada(null); setCopiada(false); };

  const copiar = async () => {
    if (!criada) return;
    try { await navigator.clipboard.writeText(criada.senha); setCopiada(true); } catch { setCopiada(false); }
  };

  const save = async () => {
    setBusy(true); setNotice('');
    try {
      const res = await fetch('/api/dashboard/team', {
        method: adding ? 'POST' : 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(adding
          ? { first_name: form.first_name, last_name: form.last_name, email: form.email, phone: form.phone, role: form.role, funcoes, password: form.password }
          : { user_id: selected?.user_id, first_name: form.first_name, last_name: form.last_name, phone: form.phone, role: form.role, funcoes, ...(form.password ? { password: form.password } : {}) }),
      });
      const j = await res.json().catch(() => ({}));
      if (j?.ok && adding && !j.existed) {
        const senha = String(j.senha_provisoria || form.password || '');
        setAdding(false);
        setCriada({ nome: `${form.first_name} ${form.last_name || ''}`.trim(), email: form.email || '', senha });
        setForm({});
        await load();
        return;
      }
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
      if (j?.ok) {
        const nome = selected.name;
        close();
        setAviso(j.agger_pendente
          ? `${nome} saiu da equipe. O Agger pessoal dessa pessoa não foi desligado agora — ele já não é usado em nenhum cálculo, mas a senha dele ainda está guardada. Avise o suporte para apagar.`
          : '');
        await load();
        return;
      }
      setNotice(j?.error || 'Não foi possível remover.');
    } finally {
      setBusy(false);
    }
  };

  if (!members) return <p className="text-sm text-muted-foreground">Carregando…</p>;

  const modalOpen = adding || Boolean(selected) || Boolean(criada);

  return (
    <div className="space-y-3">
      {aviso && (
        <p className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-3 text-xs text-foreground" role="status" data-aviso-agger-pendente>
          {aviso}
        </p>
      )}
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
                <EtiquetasDeFuncao funcoes={m.funcoes} />
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
            className="max-h-[90vh] w-full max-w-md overflow-y-auto rounded-xl border border-border bg-card p-4 shadow-xl sm:p-5"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-foreground">
                {criada ? 'Pessoa adicionada' : adding ? 'Adicionar pessoa' : selected?.name}
              </h2>
              <button onClick={close} className="rounded-md p-1 text-muted-foreground hover:text-foreground" aria-label="Fechar">
                <X className="h-4 w-4" />
              </button>
            </div>

            {criada && (
              <div className="space-y-3 text-sm">
                <p className="text-muted-foreground">
                  {criada.nome || 'A pessoa'} já pode entrar com o e-mail <span className="text-foreground">{criada.email}</span> e
                  a senha abaixo. Copie e envie para ela agora — esta senha <b>não aparece de novo</b>. Ela pode trocá-la
                  depois em Configurações.
                </p>
                <div className="flex items-center gap-2 rounded-lg border border-border bg-surface-2 p-3">
                  <code className="min-w-0 flex-1 break-all font-mono text-sm text-foreground" data-senha-provisoria>{criada.senha}</code>
                  <button
                    onClick={copiar}
                    className="inline-flex shrink-0 items-center gap-1 rounded-md border border-border px-2 py-1 text-xs text-foreground hover:bg-card"
                    aria-label="Copiar a senha"
                  >
                    {copiada ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
                    {copiada ? 'Copiada' : 'Copiar'}
                  </button>
                </div>
                <button onClick={close} className="rounded-lg border border-border px-3 py-2 text-sm text-foreground">Fechar</button>
              </div>
            )}

            {!adding && selected && (
              <div className="mb-3 space-y-1 rounded-lg border border-border bg-surface-2 p-3 text-xs text-muted-foreground">
                <p><span className="text-faint">E-mail:</span> {selected.email}</p>
                {selected.phone && <p><span className="text-faint">Celular:</span> {selected.phone}</p>}
                <p><span className="text-faint">Papel:</span> {selected.role_label}{selected.is_owner ? ' · Dono' : ''}</p>
                <p>
                  <span className="text-faint">Funções:</span>{' '}
                  {selected.funcoes?.length ? selected.funcoes.map(rotuloDaFuncao).join(' · ') : 'nenhuma marcada'}
                </p>
                <p><span className="text-faint">Último acesso:</span> {fmtWhen(selected.last_login_at)}</p>
              </div>
            )}

            {criada ? null : canManage ? (
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
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
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
                      {/* 🔴 O nome diz QUEM a pessoa é; o que o papel PODE aparece logo abaixo, e as duas coisas
                          vêm da política (uma fonte). 📊 Histórico: `member` já se chamou "Atendente / Membro" e
                          depois "só consulta" — rótulos que mentiam sobre a permissão. Um rótulo que mente sobre a
                          permissão é o defeito que este comentário existe para não repetir. */}
                      {selected?.is_owner && !(PAPEIS_QUE_A_EQUIPE_DA as readonly string[]).includes(form.role || '') && (
                        <option value={form.role}>{ROTULO_DO_PAPEL[form.role] ?? 'Dono'}</option>
                      )}
                      {PAPEIS_QUE_A_EQUIPE_DA.map((p) => (
                        <option key={p} value={p}>{ROTULO_DO_PAPEL[p]}</option>
                      ))}
                    </select>
                    {O_QUE_O_PAPEL_PODE[form.role || 'member'] && (
                      <span className="mt-1 block text-[11px] text-faint" data-o-que-o-papel-pode>
                        {O_QUE_O_PAPEL_PODE[form.role || 'member']}.
                      </span>
                    )}
                  </label>
                </div>
                <fieldset className="block text-[12px]">
                  <legend className="text-muted-foreground">Funções na corretora</legend>
                  <div className="mt-1 flex flex-wrap gap-2" data-funcoes-editaveis>
                    {FUNCOES_DE_TRABALHO.map((f) => {
                      const marcada = funcoes.includes(f);
                      return (
                        <button
                          key={f}
                          type="button"
                          onClick={() => alternarFuncao(f)}
                          aria-pressed={marcada}
                          className={`min-h-[36px] rounded-full border px-3 py-1.5 text-xs font-medium transition-colors ${
                            marcada
                              ? 'border-primary bg-primary text-primary-foreground'
                              : 'border-border bg-background text-muted-foreground hover:border-primary/60 hover:text-foreground'
                          }`}
                        >
                          {marcada && <Check className="mr-1 inline h-3 w-3" aria-hidden />}
                          {ROTULO_DA_FUNCAO[f]}
                        </button>
                      );
                    })}
                  </div>
                  <span className="mt-1 block text-[11px] text-faint" data-ajuda-das-funcoes>
                    {AJUDA_DAS_FUNCOES} Pode marcar mais de uma, ou nenhuma. A função não muda o que a pessoa pode
                    acessar — isso é o papel.
                  </span>
                </fieldset>
                <label className="block text-[12px]">
                  <span className="text-muted-foreground">{adding ? 'Senha provisória (mínimo 10 — você a vê de novo ao salvar)' : 'Nova senha (mínimo 10; deixe vazio para manter)'}</span>
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

      <NumerosDaCasa />
    </div>
  );
}
