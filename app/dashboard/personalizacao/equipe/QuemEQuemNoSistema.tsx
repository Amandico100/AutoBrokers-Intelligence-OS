'use client';

// SPEC-131-0 F2 — "Quem é quem no sistema de gestão" (D-131-0-03/30/31).
//
// O que a corretora faz aqui: diz que código de produtor da InfoCap é de qual pessoa da equipe, e confere a regra
// que decide quem é o DONO de cada renovação. A tela SUGERE a pessoa pelo nome; quem confirma é a pessoa que
// configura (nada é ligado sozinho). Mobile-first: cada produtor é um cartão, os botões quebram linha.
//
// ⛔ Sem jargão: nada de "indireto=F", "codpro", "regra_origem". A frase que explica é o produto.

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Check, Loader2, Search, X } from 'lucide-react';

type Membro = { user_id: string; nome: string };
type Vinculo = {
  id: string;
  user_id: string;
  codfil: number;
  codigo_produtor: string;
  nome_produtor: string | null;
  papel_cru: string | null;
  membro_ativo: boolean;
  nome_do_membro: string | null;
};
type Regra = { campo: string; igual: string; origem: string } | null;
type Produtor = {
  codfil: number;
  codigo_produtor: string;
  nome_produtor: string;
  papel_cru: string | null;
  vinculo: { id: string; user_id: string; nome_do_membro: string | null; membro_ativo: boolean } | null;
  sugestao: { user_id: string; nome: string; nota: number } | null;
};
type Regua = {
  status: string;
  motivo?: string;
  apolices?: number;
  apolices_na_janela?: number;
  limite_atingido?: boolean;
  com_um_dono?: number;
  sem_dono?: number;
  ambiguas?: number;
  falhas?: number;
  apolices_sem_membro?: number;
  donos_sem_membro?: number;
  donos?: Array<{ codigo_produtor: string; papel_cru: string | null; apolices: number; tem_membro: boolean }>;
};

const PAPEL: Record<string, string> = {
  FECHADOR: 'Fechador',
  FECHADORA: 'Fechadora',
  INDICADOR: 'Indicador',
  INDICADORA: 'Indicadora',
  EXECUTIVO: 'Executivo',
  EXECUTIVA: 'Executiva',
  CORRETOR: 'Corretor',
  CORRETORA: 'Corretora',
};

const inputCls =
  'mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground';
const botao =
  'inline-flex items-center gap-1.5 rounded-lg border border-primary/40 bg-brand-soft px-3 py-1.5 text-xs font-medium text-primary disabled:opacity-50';

/** A regra em português de gente. */
function regraEmPortugues(regra: Regra): string {
  if (!regra) return 'Ainda não há uma regra para dizer quem é o dono.';
  if (regra.campo === 'indireto' && String(regra.igual).toUpperCase() === 'F') {
    return 'O dono de cada renovação é o produtor com a caixa “Ind.” desmarcada na apólice.';
  }
  if (regra.campo === 'ordem') {
    return `O dono de cada renovação é o produtor na posição ${regra.igual} da lista de produtores da apólice.`;
  }
  return `O dono de cada renovação é o produtor marcado com “${regra.igual}” no campo “${regra.campo}”.`;
}

function frasesDaRegua(r: Regua): string[] {
  if (r.status !== 'ok') return [r.motivo || 'Não consegui conferir agora.'];
  const total = r.apolices ?? 0;
  if (total === 0) return ['Nenhuma renovação nos próximos 30 dias.'];
  const f: string[] = [];
  const umDono = r.com_um_dono ?? 0;
  const extra: string[] = [];
  if (r.sem_dono) extra.push(`${r.sem_dono} sem dono`);
  if (r.ambiguas) extra.push(`${r.ambiguas} com mais de um dono`);
  if (r.falhas) extra.push(`${r.falhas} que a InfoCap não respondeu`);
  f.push(`${umDono} de ${total} renovações têm um dono${extra.length ? `; ${extra.join(', ')}` : ''}.`);
  if (r.apolices_sem_membro) {
    f.push(
      `${r.apolices_sem_membro} delas são de ${r.donos_sem_membro} código(s) de produtor que ainda não estão ligados a ninguém da equipe — ligue-os acima.`,
    );
  } else if (umDono > 0) {
    f.push('Todos os donos estão ligados a alguém da equipe.');
  }
  if (r.limite_atingido) {
    f.push(`Conferi as primeiras ${total} de ${r.apolices_na_janela} renovações.`);
  }
  return f;
}

export function QuemEQuemNoSistema() {
  const [vinculos, setVinculos] = useState<Vinculo[] | null>(null);
  const [membros, setMembros] = useState<Membro[]>([]);
  const [regra, setRegra] = useState<Regra>(null);
  const [produtores, setProdutores] = useState<Produtor[] | null>(null);
  const [avisoProdutores, setAvisoProdutores] = useState('');
  const [busca, setBusca] = useState('');
  const [escolha, setEscolha] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<string>('');
  const [aviso, setAviso] = useState('');
  const [regua, setRegua] = useState<Regua | null>(null);

  const carregar = useCallback(async () => {
    try {
      const j = await fetch('/api/dashboard/equipe/sistema-de-gestao', { cache: 'no-store' }).then((r) =>
        r.json(),
      );
      setVinculos(Array.isArray(j?.vinculos) ? j.vinculos : []);
      setMembros(Array.isArray(j?.membros) ? j.membros : []);
      setRegra(j?.regra ?? null);
    } catch {
      setVinculos([]);
    }
  }, []);

  const carregarProdutores = useCallback(async () => {
    setAvisoProdutores('');
    try {
      const r = await fetch('/api/dashboard/equipe/sistema-de-gestao?o=sugestoes', { cache: 'no-store' });
      const j = await r.json().catch(() => ({}));
      if (j?.status !== 'ok') {
        setProdutores([]);
        setAvisoProdutores(
          'Não consegui ler os produtores da InfoCap agora. Confira se a InfoCap está conectada em Conectores.',
        );
        return;
      }
      setProdutores(j.produtores || []);
      if (Array.isArray(j.membros)) setMembros(j.membros);
    } catch {
      setProdutores([]);
      setAvisoProdutores('Não consegui ler os produtores da InfoCap agora.');
    }
  }, []);

  useEffect(() => {
    carregar();
  }, [carregar]);

  const enviar = async (corpo: Record<string, unknown>, chave: string) => {
    setBusy(chave);
    setAviso('');
    try {
      const r = await fetch('/api/dashboard/equipe/sistema-de-gestao', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(corpo),
      });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) {
        setAviso(String(j?.detail || j?.error || 'Não consegui salvar agora.'));
        return null;
      }
      return j;
    } finally {
      setBusy('');
    }
  };

  const vincular = async (p: Produtor, userId: string) => {
    if (!userId) return;
    const ok = await enviar(
      {
        acao: 'vincular',
        user_id: userId,
        codfil: p.codfil,
        codigo_produtor: p.codigo_produtor,
        nome_produtor: p.nome_produtor,
        papel_cru: p.papel_cru ?? undefined,
      },
      `v-${p.codigo_produtor}`,
    );
    if (ok) {
      await carregar();
      await carregarProdutores();
    }
  };

  const desvincular = async (id: string, chave: string) => {
    const ok = await enviar({ acao: 'desvincular', id }, chave);
    if (ok) {
      await carregar();
      if (produtores) await carregarProdutores();
    }
  };

  const conferir = async () => {
    setRegua(null);
    const j = await enviar({ acao: 'medir', dias: 30 }, 'medir');
    if (j) setRegua(j as Regua);
  };

  const filtrados = useMemo(() => {
    const q = busca.trim().toLowerCase();
    const lista = produtores || [];
    if (!q) return lista;
    return lista.filter(
      (p) =>
        p.codigo_produtor.includes(q) ||
        p.nome_produtor.toLowerCase().includes(q) ||
        (p.sugestao?.nome || '').toLowerCase().includes(q),
    );
  }, [produtores, busca]);

  return (
    <div className="mt-6 rounded-xl border border-border bg-card p-4">
      <h3 className="text-sm font-medium text-foreground">Quem é quem no sistema de gestão</h3>
      <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
        Na InfoCap, cada pessoa da equipe aparece como um ou mais códigos de produtor. Diga aqui de quem é cada
        código: é assim que cada renovação vai para a pessoa certa.
      </p>

      {aviso && <p className="mt-3 text-xs text-red-500">{aviso}</p>}

      {/* Os vínculos que já existem */}
      <div className="mt-4">
        <p className="text-[12px] font-medium text-foreground">Códigos já ligados</p>
        <ul className="mt-2 space-y-1.5">
          {(vinculos || []).map((v) => (
            <li
              key={v.id}
              className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border/60 px-3 py-2 text-sm"
            >
              <span className="min-w-0 text-foreground">
                <span className="font-medium">{v.codigo_produtor}</span>
                {v.nome_produtor ? <span className="text-muted-foreground"> · {v.nome_produtor}</span> : null}
                <span className="block text-xs text-muted-foreground">
                  {v.membro_ativo ? `é de ${v.nome_do_membro}` : 'a pessoa não está mais ativa na equipe'}
                </span>
              </span>
              <span className="flex items-center gap-2">
                {v.papel_cru && (
                  <span className="rounded-md border border-border/60 px-1.5 py-0.5 text-[11px] text-muted-foreground">
                    {PAPEL[v.papel_cru] || v.papel_cru}
                  </span>
                )}
                <button
                  onClick={() => desvincular(v.id, `d-${v.id}`)}
                  disabled={!!busy}
                  className="text-xs text-red-500 transition-colors hover:underline disabled:opacity-50"
                >
                  desfazer
                </button>
              </span>
            </li>
          ))}
          {vinculos !== null && vinculos.length === 0 && (
            <li className="rounded-lg border border-dashed border-border/60 px-3 py-3 text-xs text-muted-foreground">
              Nenhum código ligado ainda.
            </li>
          )}
        </ul>
      </div>

      {/* Os produtores da InfoCap, com a sugestão */}
      <div className="mt-4 border-t border-border/60 pt-3">
        {produtores === null ? (
          <button onClick={carregarProdutores} className={botao}>
            Ver os códigos de produtor da InfoCap
          </button>
        ) : (
          <>
            <p className="text-[12px] font-medium text-foreground">Códigos de produtor da InfoCap</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Quando o nome parece com o de alguém da equipe, sugerimos a pessoa. Confira e confirme — nada é ligado
              sozinho.
            </p>
            {avisoProdutores && <p className="mt-2 text-xs text-red-500">{avisoProdutores}</p>}
            {produtores.length > 0 && (
              <label className="mt-2 flex items-center gap-2 rounded-lg border border-border bg-background px-3 py-2">
                <Search className="h-3.5 w-3.5 text-muted-foreground" />
                <input
                  value={busca}
                  onChange={(e) => setBusca(e.target.value)}
                  placeholder="Buscar por código ou nome"
                  className="w-full bg-transparent text-sm text-foreground outline-none"
                />
              </label>
            )}
            <ul className="mt-2 space-y-1.5">
              {filtrados.map((p) => {
                const chave = `v-${p.codigo_produtor}`;
                const escolhido = escolha[p.codigo_produtor] ?? '';
                return (
                  <li key={p.codigo_produtor} className="rounded-lg border border-border/60 px-3 py-2 text-sm">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="min-w-0 text-foreground">
                        <span className="font-medium">{p.codigo_produtor}</span>
                        <span className="text-muted-foreground"> · {p.nome_produtor || 'sem nome'}</span>
                      </span>
                      {p.papel_cru && (
                        <span className="rounded-md border border-border/60 px-1.5 py-0.5 text-[11px] text-muted-foreground">
                          {PAPEL[p.papel_cru] || p.papel_cru}
                        </span>
                      )}
                    </div>
                    {p.vinculo ? (
                      <div className="mt-1.5 flex flex-wrap items-center justify-between gap-2 text-xs">
                        <span className="text-muted-foreground">
                          {p.vinculo.membro_ativo
                            ? `É de ${p.vinculo.nome_do_membro}.`
                            : 'Ligado a alguém que não está mais ativo.'}
                        </span>
                        <button
                          onClick={() => desvincular(p.vinculo!.id, chave)}
                          disabled={!!busy}
                          className="text-red-500 hover:underline disabled:opacity-50"
                        >
                          desfazer
                        </button>
                      </div>
                    ) : p.sugestao && !escolhido ? (
                      <div className="mt-1.5 flex flex-wrap items-center gap-2 text-xs">
                        <span className="text-muted-foreground">Parece ser de {p.sugestao.nome}.</span>
                        <button
                          onClick={() => vincular(p, p.sugestao!.user_id)}
                          disabled={!!busy}
                          className={botao}
                        >
                          {busy === chave ? (
                            <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          ) : (
                            <Check className="h-3.5 w-3.5" />
                          )}
                          Confirmar
                        </button>
                        <button
                          onClick={() => setEscolha((e) => ({ ...e, [p.codigo_produtor]: '-' }))}
                          className="text-muted-foreground hover:underline"
                        >
                          é de outra pessoa
                        </button>
                      </div>
                    ) : (
                      <div className="mt-1.5 flex flex-wrap items-center gap-2">
                        <select
                          value={escolhido === '-' ? '' : escolhido}
                          onChange={(e) => setEscolha((x) => ({ ...x, [p.codigo_produtor]: e.target.value }))}
                          className={`${inputCls} mt-0 w-auto min-w-[10rem] flex-1 py-1.5 text-xs`}
                          aria-label={`De quem é o código ${p.codigo_produtor}`}
                        >
                          <option value="">De quem é este código?</option>
                          {membros.map((m) => (
                            <option key={m.user_id} value={m.user_id}>
                              {m.nome}
                            </option>
                          ))}
                        </select>
                        <button
                          onClick={() => vincular(p, escolhido === '-' ? '' : escolhido)}
                          disabled={!!busy || !escolhido || escolhido === '-'}
                          className={botao}
                        >
                          {busy === chave && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                          Ligar
                        </button>
                      </div>
                    )}
                  </li>
                );
              })}
              {produtores.length === 0 && !avisoProdutores && (
                <li className="rounded-lg border border-dashed border-border/60 px-3 py-3 text-xs text-muted-foreground">
                  A InfoCap não devolveu nenhum código de produtor.
                </li>
              )}
            </ul>
          </>
        )}
      </div>

      {/* Quem é o dono de cada renovação */}
      <div className="mt-4 border-t border-border/60 pt-3">
        <p className="text-[12px] font-medium text-foreground">Quem é o dono de cada renovação</p>
        <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
          {regraEmPortugues(regra)}{' '}
          {regra?.origem === 'corretora' ? '(regra definida pela sua corretora)' : '(regra padrão da InfoCap)'}
        </p>
        <button onClick={conferir} disabled={!!busy} className={`${botao} mt-2`}>
          {busy === 'medir' && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
          Conferir nas renovações dos próximos 30 dias
        </button>
        {busy === 'medir' && (
          <p className="mt-2 text-xs text-muted-foreground">
            Lendo apólice por apólice na InfoCap — pode levar alguns minutos.
          </p>
        )}
        {regua && (
          <div className="mt-2 rounded-lg border border-border/60 bg-background/60 p-3 text-xs leading-relaxed">
            <div className="flex items-start justify-between gap-2">
              <div className="space-y-1 text-foreground">
                {frasesDaRegua(regua).map((f) => (
                  <p key={f}>{f}</p>
                ))}
              </div>
              <button onClick={() => setRegua(null)} aria-label="Fechar" className="text-muted-foreground">
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
