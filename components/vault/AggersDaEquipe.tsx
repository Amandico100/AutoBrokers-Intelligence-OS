'use client';

import { useCallback, useEffect, useState } from 'react';

import { Confirmar } from '@/components/aplicativos/casca/Confirmar';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

/**
 * O tom de cada situação (a do Agger da corretora, `tomDaSituacao`, mais `conectado` e `nao_conectado`).
 * SPEC-131-B K3: no claro, `text-success` sobre a superfície dá 4,16:1 (reprova AA) — o TEXTO vai escuro e a cor fica
 * no PONTO ao lado (nunca só cor: o rótulo diz a situação); no escuro, o texto leva a cor.
 */
function tomDaSituacao(situacao: string): { texto: string; ponto: string } {
  if (situacao === 'conectado' || situacao === 'calculando') return { texto: 'text-foreground dark:text-success', ponto: 'bg-success' };
  if (situacao === 'senha_recusada') return { texto: 'text-foreground dark:text-danger', ponto: 'bg-danger' };
  if (situacao === 'pausado' || situacao === 'ocupada') return { texto: 'text-foreground dark:text-warning', ponto: 'bg-warning' };
  return { texto: 'text-muted-foreground', ponto: 'bg-muted-foreground/50' };
}

/** os botões da linha: 44 px no celular (alvo de toque), 36 px a partir de 640 */
const ALVO = 'h-11 sm:h-9';

/**
 * SPEC-131-0 parte A · F3 — o Agger de cada PESSOA (D-131-0-05/29).
 *
 * 🔴 SPEC-131-B G3 (D-131-07, revê D-131-0-06): saiu do modal do Agger da corretora. Mora em Meu perfil → Minhas
 * conexões e mostra SÓ o Agger de quem está logado — cada pessoa conecta o dela. O admin vê a situação de cada um em
 * Personalização → Equipe e pede para conectar; nunca digita o login de outra pessoa (a rota recusa).
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

export function AggersDaEquipe({ apenasEu = true }: { apenasEu?: boolean } = {}) {
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
      const todas: Pessoa[] = Array.isArray(j.pessoas) ? j.pessoas : [];
      const quem = String(j.eu || '');
      setPessoas(apenasEu ? todas.filter((p) => p.user_id === quem) : todas);
      setEu(quem);
      setPodeTodos(!apenasEu && Boolean(j.pode_gerir_todos));
    } catch {
      setErro('Não consegui ler os Aggers da equipe agora.');
    } finally {
      setCarregando(false);
    }
  }, [apenasEu]);

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
        setErro(res.status === 403 ? (j.error || 'Só a própria pessoa conecta o Agger dela.')
          : (j.detail || j.error || 'Não consegui salvar agora.'));
        return;
      }
      if (Array.isArray(j.pessoas)) setPessoas(apenasEu ? j.pessoas.filter((p: Pessoa) => p.user_id === eu) : j.pessoas);
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
    <section className="space-y-3" aria-labelledby="aggers-da-equipe">
      <div className="space-y-1">
        <h3 id="aggers-da-equipe" className="text-base font-semibold text-foreground">{apenasEu ? 'Seu Agger' : 'Aggers da equipe'}</h3>
        <p className="text-sm text-muted-foreground">
          As cotações que você pedir e as renovações da sua carteira são calculadas no seu Agger — o negócio fica com
          você. Sem ele, vão pelo Agger da corretora. A senha fica guardada no cofre e nunca volta para a tela.
        </p>
      </div>

      {carregando && pessoas.length === 0 ? (
        <p className="py-2 text-sm text-muted-foreground">Carregando…</p>
      ) : pessoas.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          {apenasEu ? 'Você não está ativo na equipe desta corretora.' : 'Ninguém na equipe ainda.'}
        </p>
      ) : (
        <ul className="space-y-2">
          {pessoas.map((p) => {
            const meu = p.user_id === eu;
            const pode = (a: string) => (podeTodos || meu) && p.agger.acoes.includes(a);
            const tom = tomDaSituacao(p.agger.situacao);
            const formAberto = aberta?.id === p.user_id;
            return (
              <li key={p.user_id} className="space-y-2 rounded-lg border border-border bg-surface-2 p-3"
                data-situacao={p.agger.situacao}>
                <div className="flex flex-wrap items-baseline justify-between gap-x-2">
                  <p className="text-sm font-medium text-foreground">{p.nome}{meu ? ' (você)' : ''}</p>
                  {p.funcoes && p.funcoes.length > 0 && (
                    <p className="text-xs text-muted-foreground">
                      {p.funcoes.map((f) => FUNCAO[f] || f).join(' · ')}
                    </p>
                  )}
                </div>
                <p className={`flex items-center gap-2 text-sm ${tom.texto}`}>
                  <span aria-hidden className={`h-2 w-2 shrink-0 rounded-full ${tom.ponto}`} />
                  {p.agger.rotulo}
                </p>
                {p.agger.usuario && (
                  <p className="text-xs text-muted-foreground">
                    Login {p.agger.usuario} · {p.agger.tem_senha ? 'senha guardada' : 'sem senha'}
                    {p.agger.ultimo_uso ? ` · último cálculo ${quando(p.agger.ultimo_uso)}` : ''}
                  </p>
                )}
                {p.agger.ocupada_ate && (
                  <p className="text-xs text-muted-foreground">Tenta de novo por volta de {quando(p.agger.ocupada_ate)}</p>
                )}

                {formAberto ? (
                  <div className="space-y-2">
                    <div className="space-y-1">
                      <Label htmlFor={`ag-user-${p.user_id}`} className="text-xs text-foreground">
                        {aberta?.acao === 'conectar' ? (meu ? 'Seu login do Agger' : 'Login do Agger desta pessoa')
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
                      <Button size="sm" variant="outline" className={ALVO} onClick={fecharFormulario} disabled={ocupado}>Voltar</Button>
                      <Button
                        size="sm"
                        className={ALVO}
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
                      <Button size="sm" className={ALVO} disabled={ocupado}
                        onClick={() => { setAberta({ id: p.user_id, acao: 'conectar' }); setErro(''); setAviso(''); }}>
                        {meu ? 'Conectar o meu Agger' : 'Conectar o Agger desta pessoa'}
                      </Button>
                    )}
                    {pode('trocar_senha') && (
                      <Button size="sm" variant="outline" className={ALVO} disabled={ocupado}
                        onClick={() => { setAberta({ id: p.user_id, acao: 'trocar_senha' }); setErro(''); setAviso(''); }}>
                        Trocar senha
                      </Button>
                    )}
                    {pode('religar') && (
                      <Button size="sm" variant="outline" className={ALVO} disabled={ocupado}
                        onClick={() => agir(p.user_id, 'religar', {}, 'Agger religado.')}>Religar</Button>
                    )}
                    {pode('pausar') && (
                      <Button size="sm" variant="outline" className={ALVO} disabled={ocupado}
                        onClick={() => agir(p.user_id, 'pausar', {}, 'Agger pausado.')}>Pausar</Button>
                    )}
                    {pode('desconectar') && (
                      <Confirmar
                        titulo={meu ? 'Desconectar o seu Agger?' : `Desconectar o Agger de ${p.nome}?`}
                        descricao={meu
                          ? 'A senha é apagada e as suas cotações e renovações passam a ir pelo Agger da corretora.'
                          : 'A senha é apagada e as cotações desta pessoa passam a ir pelo Agger da corretora.'}
                        acao="Desconectar"
                        perigo
                        onConfirmar={() => agir(p.user_id, 'desconectar', {}, 'Agger desconectado. A senha foi apagada.')}
                      >
                        <Button size="sm" variant="outline" className={`${ALVO} text-danger`} disabled={ocupado}>
                          Desconectar
                        </Button>
                      </Confirmar>
                    )}
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}

      {erro && <p className="text-sm text-danger" role="alert">{erro}</p>}
      {aviso && <p className="text-sm text-foreground dark:text-success" role="status">{aviso}</p>}
    </section>
  );
}

export default AggersDaEquipe;
