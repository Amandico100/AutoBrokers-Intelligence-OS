'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

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
 * Já conectado, esta tela ABRE A CONEXÃO (estado, trocar senha, pausar/religar, desconectar, horário) — nunca um
 * formulário de "nova". A senha nunca volta do servidor: só "senha guardada". O estado e o texto vêm prontos do
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
  janela?: { dias: string; inicio: string; fim: string } | null;
  janela_padrao: { dias: string; inicio: string; fim: string };
  dias_possiveis: string[];
  dentro_da_janela?: boolean;
  teto_por_hora?: number;
};

const DIAS_LABEL: Record<string, string> = {
  'seg-sex': 'Segunda a sexta', 'seg-sab': 'Segunda a sábado', 'seg-dom': 'Todos os dias',
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
  const [modo, setModo] = useState<'ver' | 'senha' | 'horario'>('ver');
  const [usuario, setUsuario] = useState('');
  const [senha, setSenha] = useState('');
  const [janela, setJanela] = useState({ dias: 'seg-sab', inicio: '07:00', fim: '22:00' });
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
      if (j.conta) setJanela(j.conta.janela || j.conta.janela_padrao);
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
  const corTom = tom === 'success' ? 'text-success' : tom === 'danger' ? 'text-danger' : tom === 'warning' ? 'text-amber-600' : 'text-muted-foreground';

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
          O robô trabalha de {DIAS_LABEL[janela.dias]?.toLowerCase() || janela.dias}, das {janela.inicio} às {janela.fim}. Você muda depois, em “Horário”.
        </p>
      )}
      <div className="flex justify-end gap-2">
        {jaExiste && !semConta && <Button variant="outline" onClick={() => { setModo('ver'); setSenha(''); }} disabled={ocupado}>Voltar</Button>}
        <Button
          onClick={() => agir(acao, { usuario: usuario.trim() || undefined, senha, janela: jaExiste ? undefined : janela },
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
      <DialogContent className="border-border bg-surface sm:max-w-md">
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
                {conta.janela && (
                  <p className="text-xs text-muted-foreground">
                    Horário: {DIAS_LABEL[conta.janela.dias] || conta.janela.dias}, das {conta.janela.inicio} às {conta.janela.fim}
                    {conta.tem_senha && conta.dentro_da_janela === false ? ' · agora está fora do horário' : ''}
                  </p>
                )}
              </div>
            )}

            {semConta && formulario('Senha', true, 'conectar')}

            {!semConta && modo === 'senha' && formulario('Senha nova', false, 'trocar_senha')}

            {!semConta && modo === 'horario' && (
              <div className="space-y-3">
                <div className="space-y-1.5">
                  <Label htmlFor="ag-dias" className="text-foreground">Dias</Label>
                  <select
                    id="ag-dias"
                    value={janela.dias}
                    onChange={(e) => setJanela((j) => ({ ...j, dias: e.target.value }))}
                    className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground"
                  >
                    {(conta?.dias_possiveis || ['seg-sex', 'seg-sab', 'seg-dom']).map((d) => (
                      <option key={d} value={d}>{DIAS_LABEL[d] || d}</option>
                    ))}
                  </select>
                </div>
                <div className="flex gap-2">
                  <div className="flex-1 space-y-1.5">
                    <Label htmlFor="ag-ini" className="text-foreground">Das</Label>
                    <Input id="ag-ini" type="time" value={janela.inicio} onChange={(e) => setJanela((j) => ({ ...j, inicio: e.target.value }))} className="bg-background" />
                  </div>
                  <div className="flex-1 space-y-1.5">
                    <Label htmlFor="ag-fim" className="text-foreground">Até</Label>
                    <Input id="ag-fim" type="time" value={janela.fim} onChange={(e) => setJanela((j) => ({ ...j, fim: e.target.value }))} className="bg-background" />
                  </div>
                </div>
                <div className="flex justify-end gap-2">
                  <Button variant="outline" onClick={() => setModo('ver')} disabled={ocupado}>Voltar</Button>
                  <Button onClick={() => agir('janela', { janela }, 'Horário salvo.')} disabled={ocupado}>Salvar horário</Button>
                </div>
              </div>
            )}

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
                {pode('janela') && (
                  <Button size="sm" variant="outline" onClick={() => setModo('horario')} disabled={ocupado}>Horário</Button>
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

        <DialogFooter className="gap-2 sm:gap-2">
          <Button variant="outline" onClick={() => close(false)} disabled={ocupado}>Fechar</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default AggerDaCorretoraModal;
