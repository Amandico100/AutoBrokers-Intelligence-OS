'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import Link from 'next/link';

import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Icon } from '@/components/ui/Icon';
import { icons } from '@/lib/icons';

/**
 * SPEC-133-A.1 F3 — o "Agger da corretora" (D-133A1-03/04): o login DEDICADO do robô que faz os cálculos do
 * Quem Cobra Menos (e de quem não tem Agger próprio). O mesmo jeito da InfoCap: clicar → login + senha → salvar.
 *
 * Já conectado, esta tela ABRE A CONEXÃO (estado, trocar senha, pausar/religar, desconectar) — nunca um
 * formulário de "nova". SPEC-129-C F0 · D-129C-01 (Founder, 11/10): SEM horário — o Agger da corretora fica ligado
 * o tempo todo; o conector é só a conexão, e horário/regras moram em cada auxiliar. A senha nunca volta do servidor: só "senha guardada". O estado e o texto vêm prontos do
 * backend (`portal_worker/multicalculo/conta_do_robo.retrato`) — a tela não traduz estado cru.
 */
export type ContaDoAgger = {
  nome: string;
  conectado: boolean;
  situacao: string;
  rotulo: string;
  acoes: string[];
  id?: string;
  usuario?: string;
  tem_senha?: boolean;
  ultimo_uso?: string | null;
  ocupada_ate?: string | null;
  sempre_ligado?: boolean;
  teto_por_hora?: number;
};

const quando = (iso?: string | null) => (iso ? new Date(iso).toLocaleString('pt-BR') : '');

export function tomDaSituacao(situacao?: string): 'success' | 'warning' | 'danger' | 'neutral' {
  if (situacao === 'funcionando' || situacao === 'calculando' || situacao === 'aguardando') return 'success';
  if (situacao === 'senha_recusada') return 'danger';
  if (situacao === 'pausado' || situacao === 'ocupada' || situacao === 'teste') return 'warning';
  return 'neutral';
}

export function AggerDaCorretoraModal({
  open, onOpenChange, onChanged,
}: {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  onChanged?: (conta: ContaDoAgger | null) => void;
}) {
  const [conta, setConta] = useState<ContaDoAgger | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [modo, setModo] = useState<'ver' | 'senha'>('ver');
  const [usuario, setUsuario] = useState('');
  const [senha, setSenha] = useState('');
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState('');
  const [aviso, setAviso] = useState('');
  // ref: o pai costuma passar uma função nova a cada render — como dependência, ela relançaria a carga sem fim
  const avisarPai = useRef(onChanged);
  avisarPai.current = onChanged;

  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      const res = await fetch('/api/dashboard/agger-da-corretora', { cache: 'no-store' });
      const j = await res.json().catch(() => ({}));
      if (!res.ok) { setErro(j.detail || j.error || 'Não consegui ler o Agger agora.'); return; }
      setConta(j.conta || null);
      avisarPai.current?.(j.conta || null);
    } catch {
      setErro('Não consegui ler o Agger agora.');
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    if (open) { setModo('ver'); setUsuario(''); setSenha(''); setErro(''); setAviso(''); carregar(); }
  }, [open, carregar]);

  const close = (o: boolean) => { if (!o) setSenha(''); onOpenChange(o); };

  const agir = async (acao: string, extra: Record<string, unknown> = {}, ok = '') => {
    setOcupado(true); setErro(''); setAviso('');
    try {
      const res = await fetch('/api/dashboard/agger-da-corretora', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ acao, ...extra }),
      });
      const j = await res.json().catch(() => ({}));
      if (!res.ok) { setErro(j.detail || j.error || 'Não consegui salvar agora.'); return false; }
      setConta(j.conta || null);
      avisarPai.current?.(j.conta || null);
      setSenha(''); setUsuario(''); setModo('ver'); setAviso(ok);
      return true;
    } catch {
      setErro('Não consegui salvar agora. Tente de novo.');
      return false;
    } finally {
      setOcupado(false);
    }
  };

  const semConta = !conta || !conta.tem_senha;   // nunca conectado, ou desconectado (senha apagada)
  const jaExiste = Boolean(conta?.id);
  const pode = (a: string) => Boolean(conta?.acoes?.includes(a));
  const tom = tomDaSituacao(conta?.situacao);
  const corTom = tom === 'success' ? 'text-success' : tom === 'danger' ? 'text-danger' : tom === 'warning' ? 'text-warning' : 'text-muted-foreground';

  const formulario = (titulo: string, pedeLogin: boolean, acao: 'conectar' | 'trocar_senha') => (
    <div className="space-y-3">
      {pedeLogin ? (
        <div className="space-y-1.5">
          <Label htmlFor="ag-user" className="text-foreground">Login do Agger (o do robô)</Label>
          <Input id="ag-user" value={usuario} onChange={(e) => setUsuario(e.target.value)} placeholder="cotador@suacorretora.com.br" autoComplete="off" className="bg-background" />
        </div>
      ) : (
        <div className="space-y-1.5">
          <Label htmlFor="ag-user2" className="text-foreground">Login <span className="text-faint">(deixe em branco para manter {conta?.usuario})</span></Label>
          <Input id="ag-user2" value={usuario} onChange={(e) => setUsuario(e.target.value)} autoComplete="off" className="bg-background" />
        </div>
      )}
      <div className="space-y-1.5">
        <Label htmlFor="ag-pass" className="text-foreground">{titulo}</Label>
        <Input id="ag-pass" type="password" autoComplete="new-password" value={senha} onChange={(e) => setSenha(e.target.value)} className="bg-background" />
      </div>
      {acao === 'conectar' && !jaExiste && (
        <p className="text-[11px] text-muted-foreground">
          Depois de conectado, o robô fica ligado o tempo todo.
        </p>
      )}
      <div className="flex justify-end gap-2">
        {jaExiste && !semConta && <Button variant="outline" onClick={() => { setModo('ver'); setSenha(''); }} disabled={ocupado}>Voltar</Button>}
        <Button
          onClick={() => agir(acao, { usuario: usuario.trim() || undefined, senha },
            acao === 'conectar' ? 'Agger conectado. O robô já pode calcular.' : 'Senha trocada. O robô voltou a funcionar.')}
          disabled={ocupado || !senha || (pedeLogin && !usuario.trim())}
        >
          {ocupado ? 'Salvando…' : acao === 'conectar' ? 'Conectar' : 'Salvar a senha nova'}
        </Button>
      </div>
    </div>
  );

  return (
    <Dialog open={open} onOpenChange={close}>
      <DialogContent className="max-h-[90vh] overflow-y-auto border-border bg-surface sm:max-w-md">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-lg border border-border bg-surface-2 text-primary">
              <Icon icon={icons.seguradoras} size={18} />
            </span>
            <DialogTitle className="text-base">{conta?.nome || 'Agger da corretora'}</DialogTitle>
          </div>
          <DialogDescription className="pt-1">
            O login do Agger que o robô usa para calcular as cotações do Quem Cobra Menos. Use um login
            <span className="font-medium text-foreground"> só do robô</span> (ex.: cotador@), nunca o de uma pessoa —
            o Agger derruba a sessão de quem estiver usando o mesmo login.
          </DialogDescription>
        </DialogHeader>

        {carregando && !conta ? (
          <p className="py-4 text-center text-sm text-muted-foreground">Carregando…</p>
        ) : (
          <>
            {conta && jaExiste && (
              <div className="space-y-1 rounded-lg border border-border bg-surface-2 p-3" data-situacao={conta.situacao}>
                <p className={`text-sm font-medium ${corTom}`}>{conta.rotulo}</p>
                <p className="text-xs text-muted-foreground">
                  Login {conta.usuario || '—'} · {conta.tem_senha ? 'senha guardada' : 'sem senha'}
                </p>
                {conta.ultimo_uso && <p className="text-xs text-muted-foreground">Último cálculo: {quando(conta.ultimo_uso)}</p>}
                {conta.ocupada_ate && <p className="text-xs text-muted-foreground">Volta sozinho por volta de {quando(conta.ocupada_ate)}</p>}
                {conta.tem_senha && conta.sempre_ligado !== false && (
                  <p className="text-xs text-muted-foreground">Ligado o tempo todo.</p>
                )}
              </div>
            )}

            {semConta && formulario('Senha', true, 'conectar')}

            {!semConta && modo === 'senha' && formulario('Senha nova', false, 'trocar_senha')}

            {!semConta && modo === 'ver' && (
              <div className="flex flex-wrap gap-2">
                {pode('trocar_senha') && (
                  <Button size="sm" onClick={() => { setModo('senha'); setErro(''); }} disabled={ocupado}>
                    <Icon icon={icons.cadeado} size={14} className="mr-2" />Trocar senha
                  </Button>
                )}
                {pode('religar') && (
                  <Button size="sm" variant="outline" onClick={() => agir('religar', {}, 'Robô religado.')} disabled={ocupado}>Religar</Button>
                )}
                {pode('pausar') && (
                  <Button size="sm" variant="outline" onClick={() => agir('pausar', {}, 'Robô pausado.')} disabled={ocupado}>Pausar</Button>
                )}
                {pode('desconectar') && (
                  <Button
                    size="sm"
                    variant="outline"
                    className="text-danger"
                    disabled={ocupado}
                    onClick={() => {
                      if (!confirm('Desconectar o Agger? A senha é apagada e o robô para de calcular. O histórico de cálculos fica.')) return;
                      agir('desconectar', {}, 'Agger desconectado. A senha foi apagada.');
                    }}
                  >
                    Desconectar
                  </Button>
                )}
              </div>
            )}
          </>
        )}

        {erro && <p className="text-xs text-danger">{erro}</p>}
        {aviso && <p className="text-xs text-success">{aviso}</p>}

        {/* SPEC-131-B G3 (D-131-07, revê D-131-0-06): o Agger de cada PESSOA saiu deste modal. Cada um conecta o seu
            em Meu perfil → Minhas conexões; o admin vê quem falta em Equipe e pede para conectar. */}
        <p className="border-t border-border pt-4 text-sm text-muted-foreground" data-aggers-das-pessoas-sairam>
          O Agger de cada pessoa da equipe fica em{' '}
          <Link href="/dashboard/configuracoes?aba=conexoes" className="font-medium text-primary underline-offset-4 hover:underline">
            Meu perfil → Minhas conexões
          </Link>
          : cada um conecta o seu. Quem ainda não conectou aparece em{' '}
          <Link href="/dashboard/personalizacao/equipe" className="font-medium text-primary underline-offset-4 hover:underline">
            Equipe
          </Link>
          .
        </p>

        <DialogFooter className="gap-2 sm:gap-2">
          <Button variant="outline" onClick={() => close(false)} disabled={ocupado}>Fechar</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default AggerDaCorretoraModal;
