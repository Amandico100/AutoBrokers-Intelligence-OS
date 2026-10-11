'use client';

import { useCallback, useEffect, useState } from 'react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

/** A cor de cada situação (a do Agger da corretora, `tomDaSituacao`, mais `conectado` e `nao_conectado`). */
function corDaSituacao(situacao: string): string {
  if (situacao === 'conectado' || situacao === 'calculando') return 'text-success';
  if (situacao === 'senha_recusada') return 'text-danger';
  if (situacao === 'pausado' || situacao === 'ocupada') return 'text-amber-600';
  return 'text-muted-foreground';
}

/**
 * SPEC-131-0 parte A · F3 — "Aggers da equipe" (D-131-0-05/06/29): o Agger de cada pessoa da equipe, ao lado do Agger
 * da corretora. Mora DENTRO do modal do Agger da corretora (uma conexão, duas partes).
 *
 * O estado e o texto de cada pessoa vêm prontos do backend (`conta_do_robo.aggers_da_equipe`) — a tela não traduz
 * estado cru. A senha nunca volta: só "senha guardada". O admin mexe no Agger de qualquer pessoa; a pessoa, no dela —
 * a tela só esconde botões, quem decide é o servidor.
 */
type AggerDaPessoa = {
  situacao: string;
  rotulo: string;
  acoes: string[];
  conectado: boolean;
  id?: string;
  usuario?: string;
  tem_senha?: boolean;
  ultimo_uso?: string | null;
  ocupada_ate?: string | null;
};

type Pessoa = { user_id: string; nome: string; papel?: string | null; funcoes?: string[]; agger: AggerDaPessoa };

const FUNCAO: Record<string, string> = { comercial: 'Comercial', calculista: 'Calculista', negociador: 'Negociador' };
const quando = (iso?: string | null) => (iso ? new Date(iso).toLocaleString('pt-BR') : '');

export function AggersDaEquipe() {
  const [pessoas, setPessoas] = useState<Pessoa[]>([]);
  const [eu, setEu] = useState('');
  const [podeTodos, setPodeTodos] = useState(false);
  const [carregando, setCarregando] = useState(true);
  const [aberta, setAberta] = useState<{ id: string; acao: 'conectar' | 'trocar_senha' } | null>(null);
  const [usuario, setUsuario] = useState('');
  const [senha, setSenha] = useState('');
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState('');
  const [aviso, setAviso] = useState('');

  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      const res = await fetch('/api/dashboard/aggers-da-equipe', { cache: 'no-store' });
      const j = await res.json().catch(() => ({}));
      if (!res.ok) { setErro(j.detail || j.error || 'Não consegui ler os Aggers da equipe agora.'); return; }
      setPessoas(Array.isArray(j.pessoas) ? j.pessoas : []);
      setEu(String(j.eu || ''));
      setPodeTodos(Boolean(j.pode_gerir_todos));
    } catch {
      setErro('Não consegui ler os Aggers da equipe agora.');
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => { carregar(); }, [carregar]);

  const fecharFormulario = () => { setAberta(null); setUsuario(''); setSenha(''); };

  const agir = async (dono: string, acao: string, extra: Record<string, unknown> = {}, ok = '') => {
    setOcupado(true); setErro(''); setAviso('');
    try {
      const res = await fetch('/api/dashboard/aggers-da-equipe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ acao, dono_user_id: dono, ...extra }),
      });
      const j = await res.json().catch(() => ({}));
      if (!res.ok) {
        setErro(res.status === 403 ? 'Só um administrador da corretora, ou a própria pessoa, mexe neste Agger.'
          : (j.detail || j.error || 'Não consegui salvar agora.'));
        return;
      }
      if (Array.isArray(j.pessoas)) setPessoas(j.pessoas);
      fecharFormulario();
      setAviso(ok);
    } catch {
      setErro('Não consegui salvar agora. Tente de novo.');
    } finally {
      setSenha('');
      setOcupado(false);
    }
  };

  return (
    <section className="space-y-3 border-t border-border pt-4" aria-labelledby="aggers-da-equipe">
      <div className="space-y-1">
        <h3 id="aggers-da-equipe" className="text-sm font-semibold text-foreground">Aggers da equipe</h3>
        <p className="text-xs text-muted-foreground">
          O Agger da corretora atende o Quem Cobra Menos e quem não tem Agger próprio. Cada comercial pode ter o seu:
          as cotações que ela pedir e as renovações da carteira dela serão calculadas no Agger dela.
        </p>
      </div>

      {carregando && pessoas.length === 0 ? (
        <p className="py-2 text-center text-xs text-muted-foreground">Carregando…</p>
      ) : pessoas.length === 0 ? (
        <p className="text-xs text-muted-foreground">Ninguém na equipe ainda.</p>
      ) : (
        <ul className="space-y-2">
          {pessoas.map((p) => {
            const meu = p.user_id === eu;
            const pode = (a: string) => (podeTodos || meu) && p.agger.acoes.includes(a);
            const cor = corDaSituacao(p.agger.situacao);
            const formAberto = aberta?.id === p.user_id;
            return (
              <li key={p.user_id} className="space-y-2 rounded-lg border border-border bg-surface-2 p-3"
                data-situacao={p.agger.situacao}>
                <div className="flex flex-wrap items-baseline justify-between gap-x-2">
                  <p className="text-sm font-medium text-foreground">{p.nome}{meu ? ' (você)' : ''}</p>
                  {p.funcoes && p.funcoes.length > 0 && (
                    <p className="text-[11px] text-muted-foreground">
                      {p.funcoes.map((f) => FUNCAO[f] || f).join(' · ')}
                    </p>
                  )}
                </div>
                <p className={`text-xs ${cor}`}>{p.agger.rotulo}</p>
                {p.agger.usuario && (
                  <p className="text-[11px] text-muted-foreground">
                    Login {p.agger.usuario} · {p.agger.tem_senha ? 'senha guardada' : 'sem senha'}
                    {p.agger.ultimo_uso ? ` · último cálculo ${quando(p.agger.ultimo_uso)}` : ''}
                  </p>
                )}
                {p.agger.ocupada_ate && (
                  <p className="text-[11px] text-muted-foreground">Tenta de novo por volta de {quando(p.agger.ocupada_ate)}</p>
                )}

                {formAberto ? (
                  <div className="space-y-2">
                    <div className="space-y-1">
                      <Label htmlFor={`ag-user-${p.user_id}`} className="text-xs text-foreground">
                        {aberta?.acao === 'conectar' ? 'Login do Agger desta pessoa'
                          : `Login (deixe em branco para manter ${p.agger.usuario || 'o atual'})`}
                      </Label>
                      <Input id={`ag-user-${p.user_id}`} value={usuario} onChange={(e) => setUsuario(e.target.value)}
                        autoComplete="off" className="bg-background" />
                    </div>
                    <div className="space-y-1">
                      <Label htmlFor={`ag-pass-${p.user_id}`} className="text-xs text-foreground">
                        {aberta?.acao === 'conectar' ? 'Senha' : 'Senha nova'}
                      </Label>
                      <Input id={`ag-pass-${p.user_id}`} type="password" autoComplete="new-password" value={senha}
                        onChange={(e) => setSenha(e.target.value)} className="bg-background" />
                    </div>
                    <div className="flex flex-wrap justify-end gap-2">
                      <Button size="sm" variant="outline" onClick={fecharFormulario} disabled={ocupado}>Voltar</Button>
                      <Button
                        size="sm"
                        disabled={ocupado || !senha || (aberta?.acao === 'conectar' && !usuario.trim())}
                        onClick={() => agir(p.user_id, aberta!.acao, { usuario: usuario.trim() || undefined, senha },
                          aberta?.acao === 'conectar' ? `Agger de ${p.nome} conectado.` : 'Senha trocada.')}
                      >
                        {ocupado ? 'Salvando…' : aberta?.acao === 'conectar' ? 'Conectar' : 'Salvar a senha nova'}
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {pode('conectar') && (
                      <Button size="sm" disabled={ocupado}
                        onClick={() => { setAberta({ id: p.user_id, acao: 'conectar' }); setErro(''); setAviso(''); }}>
                        Conectar o Agger desta pessoa
                      </Button>
                    )}
                    {pode('trocar_senha') && (
                      <Button size="sm" variant="outline" disabled={ocupado}
                        onClick={() => { setAberta({ id: p.user_id, acao: 'trocar_senha' }); setErro(''); setAviso(''); }}>
                        Trocar senha
                      </Button>
                    )}
                    {pode('religar') && (
                      <Button size="sm" variant="outline" disabled={ocupado}
                        onClick={() => agir(p.user_id, 'religar', {}, 'Agger religado.')}>Religar</Button>
                    )}
                    {pode('pausar') && (
                      <Button size="sm" variant="outline" disabled={ocupado}
                        onClick={() => agir(p.user_id, 'pausar', {}, 'Agger pausado.')}>Pausar</Button>
                    )}
                    {pode('desconectar') && (
                      <Button size="sm" variant="outline" className="text-danger" disabled={ocupado}
                        onClick={() => {
                          if (!confirm(`Desconectar o Agger de ${p.nome}? A senha é apagada e as cotações dela passam a ir pelo Agger da corretora.`)) return;
                          agir(p.user_id, 'desconectar', {}, 'Agger desconectado. A senha foi apagada.');
                        }}>
                        Desconectar
                      </Button>
                    )}
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}

      {erro && <p className="text-xs text-danger">{erro}</p>}
      {aviso && <p className="text-xs text-success">{aviso}</p>}
    </section>
  );
}

export default AggersDaEquipe;
