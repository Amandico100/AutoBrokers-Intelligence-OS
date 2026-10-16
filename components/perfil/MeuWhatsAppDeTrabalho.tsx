'use client';

import { useEffect, useState } from 'react';
import { CheckCircle2, ChevronDown, Info, MessageCircle, Smartphone } from 'lucide-react';

import { BOTAO_PRIMARIO } from '@/components/aplicativos/casca/CardDoAplicativo';
import { Confirmar } from '@/components/aplicativos/casca/Confirmar';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';

import { MinhaLinhaDoWhatsApp, type Reserva } from './MinhaLinhaDoWhatsApp';
import {
  fraseDoErro,
  lerEfetivo,
  mascararNumero,
  mesmoNumero,
  useLinhaDoWhatsApp,
  type MeuPerfil,
} from './useMeuPerfil';

/**
 * A aba "WhatsApp de trabalho" de Meu perfil.
 *
 * SPEC-131-0-B3 (D-1310B3-01) — UM número só por pessoa. Quando a pessoa pode conectar o próprio WhatsApp
 * (`MinhaLinhaDoWhatsApp`), o PAREAMENTO é o principal: conectado, ele É o WhatsApp de trabalho, e o número que ela
 * digitou fica como RESERVA (usado se o WhatsApp desconectar). Quem não quer conectar informa só o número, no bloco
 * recolhido "Não quer conectar? Informe só o número" — aberto por padrão quando já há número digitado e nenhuma
 * conexão. Sem a conexão disponível para esta pessoa, o número digitado volta a ser o principal (como na 131-B).
 * O "Quero renovar" só é atribuído ao pareado quando o servidor diz (`whatsapp_trabalho.efetivo.origem === 'linha'`);
 * backend antigo, sem `efetivo`, a tela não afirma o que não sabe (CLAUDE.md §9.3).
 * Conserto K2 (BLOCKER do juiz) — conversa PAUSADA (`desligada`: a chave não liga esta pessoa) com o WhatsApp dela
 * ainda conectado no banco: o servidor manda o cliente para o PAREADO (`efetivo.origem === 'linha'`, D-1310B3-04 — a
 * chave governa a conversa, não a posse). A aba diz isso: "Este é o seu WhatsApp de trabalho", a conversa pausada e o
 * "Quero renovar" chegando NESTE número; o digitado (se diferente) fica como reserva recolhida. Antes, o formulário
 * afirmava "chega aqui" e "não se conecta a ele" — as duas falsas.
 * ⛔ Nada é enviado daqui. O número de atendimento da corretora e o do Quem Cobra Menos são outros e não mudam.
 *
 * SPEC-132-C C1 (D-132C-02, D-1310B3-05) — "Usar pelo WhatsApp": a pessoa prova que o número DIGITADO é dela mandando,
 * do próprio celular, o código "ATIVAR 123456" ao número do AutoBrokers. A identidade do atalho continua no número
 * digitado e verificado (o pareado é outra porta). Trocar o número apaga a verificação. Com o atalho desligado, a tela
 * diz "Em breve" em vez de oferecer um código que ficaria sem resposta.
 */
type PerfilComAtalho = MeuPerfil & { atalho_whatsapp?: { disponivel?: boolean } };
type Codigo = {
  codigo: string;
  texto: string;
  expira_em: string;
  validade_minutos: number;
  wa_me_url: string | null;
  numero_assistente: string | null;
};

/** o PRÓPRIO número da pessoa, legível, no formulário dela (o de outra pessoa nunca passa por aqui) */
function exibir(e164: string): string {
  const d = e164.replace(/\D/g, '');
  if (d.startsWith('55') && (d.length === 12 || d.length === 13)) {
    const ddd = d.slice(2, 4);
    const n = d.slice(4);
    return `(${ddd}) ${n.length === 9 ? `${n.slice(0, 1)} ${n.slice(1, 5)}-${n.slice(5)}` : `${n.slice(0, 4)}-${n.slice(4)}`}`;
  }
  return e164;
}

const FOCO = 'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring';
const BOTAO_SECUNDARIO =
  'inline-flex h-11 items-center justify-center rounded-lg border border-border px-4 text-sm font-medium text-foreground hover:bg-surface-2 disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring';

export function MeuWhatsAppDeTrabalho({ perfil, onMudou }: { perfil: MeuPerfil | null; onMudou: () => void }) {
  const atual = perfil?.whatsapp_trabalho;
  const atalhoDisponivel = (perfil as PerfilComAtalho | null)?.atalho_whatsapp?.disponivel === true;
  const [editando, setEditando] = useState(() => !atual?.confirmado);
  const [numero, setNumero] = useState(() => (atual?.numero ? exibir(atual.numero) : ''));
  const [confirmo, setConfirmo] = useState(false);
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState('');
  const [aviso, setAviso] = useState('');
  const [codigo, setCodigo] = useState<Codigo | null>(null);
  const [pedindo, setPedindo] = useState(false);
  const [erroDoCodigo, setErroDoCodigo] = useState('');
  // o bloco recolhido do número digitado: `null` = a pessoa ainda não mexeu (vale o padrão do estado)
  const [reservaAberta, setReservaAberta] = useState<boolean | null>(null);
  const { linha, carregada, setLinha, carregar: recarregarLinha } = useLinhaDoWhatsApp();

  useEffect(() => {
    if (atual) { setEditando(!atual.confirmado); setNumero(atual.numero ? exibir(atual.numero) : ''); setConfirmo(false); }
    if (atual?.verificado) setCodigo(null);
  }, [atual]);

  if (!perfil || !carregada) return <Skeleton className="h-40 w-full rounded-xl" />;

  const verificado = Boolean(atual?.verificado && atual?.numero);
  // conserto P1 (SPEC-132-C): o código amarra o número DECLARADO — sem número salvo e confirmado, não há código
  const numeroConfirmado = Boolean(atual?.confirmado && atual?.numero && !editando);
  const temDigitado = Boolean(atual?.confirmado && atual?.numero);
  // a conexão do WhatsApp é oferecida a esta pessoa? (`desligada` ou sem leitura → o número digitado é o principal)
  const linhaOfertada = Boolean(linha && linha.estado !== 'desligada');
  const linhaConectada = linha?.estado === 'conectada';
  const efetivo = lerEfetivo(atual?.efetivo);
  // só o SERVIDOR diz que o "Quero renovar" usa o pareado; sem `efetivo` (backend antigo), a tela não afirma
  const queroRenovarNoPareado = linhaConectada && efetivo?.origem === 'linha';
  // a conversa está pausada para esta pessoa, mas o WhatsApp dela segue conectado e o cliente vai para ELE (K2)
  const pareadoPausado = linha?.estado === 'desligada' && efetivo?.origem === 'linha';
  const mascarado = temDigitado ? mascararNumero(atual?.numero) : null;
  const reserva: Reserva | null = mascarado
    ? {
      mascarado,
      diferente: efetivo?.numero
        ? !mesmoNumero(atual?.numero, efetivo.numero)
        : !(linha?.numero_mascarado && mascararNumero(linha.numero_mascarado) === mascarado),
    }
    : null;
  const comoReserva = linhaConectada || pareadoPausado || (linha?.estado === 'desconectada' && temDigitado);
  const reservaAbertaPorPadrao = !linhaConectada && !pareadoPausado && temDigitado;
  const abrirReserva = reservaAberta ?? reservaAbertaPorPadrao;

  const gravar = async (corpo: Record<string, unknown>, ok: string) => {
    setOcupado(true); setErro(''); setAviso('');
    try {
      const res = await fetch('/api/dashboard/meu-perfil', {
        method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(corpo),
      });
      if (!res.ok) { setErro(await fraseDoErro(res, 'Não conseguimos salvar agora.')); return; }
      setAviso(ok);
      setCodigo(null);
      onMudou();
    } catch {
      setErro('Não conseguimos salvar agora.');
    } finally {
      setOcupado(false);
    }
  };

  const pedirCodigo = async () => {
    setPedindo(true); setErroDoCodigo('');
    try {
      const res = await fetch('/api/dashboard/meu-perfil/whatsapp/codigo', { method: 'POST', cache: 'no-store' });
      if (!res.ok) { setErroDoCodigo(await fraseDoErro(res, 'Não conseguimos gerar o código agora.')); return; }
      setCodigo((await res.json()) as Codigo);
    } catch {
      setErroDoCodigo('Não conseguimos gerar o código agora.');
    } finally {
      setPedindo(false);
    }
  };

  const aoTirar = queroRenovarNoPareado || pareadoPausado
    ? 'O "Quero renovar" continua no seu WhatsApp conectado; você só fica sem número de reserva.'
    : 'O "Quero renovar" passa a ir para o número da corretora.';

  const blocoDoNumero = atual?.disponivel === false ? (
    <p className="rounded-lg border border-border-soft bg-surface p-3 text-sm text-muted-foreground">
      Este campo ainda não está disponível na sua corretora. Tente de novo mais tarde.
    </p>
  ) : !editando && atual?.confirmado && atual.numero ? (
    <div className="flex flex-col gap-3 rounded-xl border border-border bg-surface p-4 sm:flex-row sm:items-center sm:justify-between">
      <p className="flex flex-wrap items-center gap-2 text-sm text-foreground">
        <CheckCircle2 size={16} strokeWidth={1.6} className="text-success" aria-hidden />
        <span className="tabular-nums">{exibir(atual.numero)}</span>
        <span className="text-muted-foreground">· {verificado ? 'verificado' : 'confirmado'}</span>
      </p>
      <div className="flex gap-2">
        <button type="button" onClick={() => { setEditando(true); setAviso(''); }} className={BOTAO_SECUNDARIO}>
          Mudar
        </button>
        <Confirmar titulo={comoReserva ? 'Tirar o número de reserva?' : 'Tirar o seu WhatsApp de trabalho?'}
          descricao={verificado
            ? `${aoTirar} E você deixa de falar com o AutoBrokers pelo número dele no WhatsApp.`
            : aoTirar}
          acao="Tirar" perigo onConfirmar={() => gravar({ numero: null }, 'Número tirado.')}>
          <button type="button" disabled={ocupado} className={cn(BOTAO_SECUNDARIO, 'text-danger')}>
            Tirar
          </button>
        </Confirmar>
      </div>
    </div>
  ) : (
    <form className="space-y-3 rounded-xl border border-border bg-surface p-4"
      onSubmit={(e) => { e.preventDefault(); gravar({ numero, confirmo }, 'Número salvo e confirmado.'); }}>
      <div className="space-y-1">
        <label htmlFor="zap-trabalho" className="text-sm font-medium text-foreground">Número com DDD</label>
        <input id="zap-trabalho" type="tel" inputMode="tel" autoComplete="tel" placeholder="(11) 9 1234-5678"
          value={numero} onChange={(e) => setNumero(e.target.value)}
          className="h-11 w-full max-w-xs rounded-lg border border-border bg-background px-3 text-sm tabular-nums text-foreground" />
      </div>
      <label className="flex items-start gap-3 text-sm text-foreground">
        <input type="checkbox" checked={confirmo} onChange={(e) => setConfirmo(e.target.checked)}
          className="mt-0.5 h-5 w-5 shrink-0 accent-[hsl(var(--primary))]" />
        Confirmo que este é o WhatsApp em que eu atendo os clientes.
      </label>
      {verificado && (
        <p className="text-sm text-muted-foreground">
          Se você trocar o número, vai precisar verificar de novo para falar com o AutoBrokers pelo WhatsApp.
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        <button type="submit" disabled={ocupado || !numero.trim() || !confirmo}
          className={cn('h-11 rounded-lg px-5 text-sm font-medium disabled:opacity-60', BOTAO_PRIMARIO, FOCO)}>
          {ocupado ? 'Salvando…' : 'Salvar'}
        </button>
        {atual?.confirmado && (
          <button type="button" onClick={() => { setEditando(false); setErro(''); }} className={BOTAO_SECUNDARIO}>
            Cancelar
          </button>
        )}
      </div>
    </form>
  );

  // o número digitado, recolhido: o `<details>` nativo anuncia aberto/fechado ao leitor de tela
  const blocoRecolhido = (
    <details open={abrirReserva} onToggle={(e) => setReservaAberta(e.currentTarget.open)}
      className="group rounded-xl border border-border-soft">
      <summary className={cn('flex min-h-11 cursor-pointer list-none items-center justify-between gap-3 rounded-xl px-4 py-2 text-sm font-medium text-foreground hover:bg-surface-2 [&::-webkit-details-marker]:hidden', FOCO)}>
        {comoReserva ? 'Número de reserva' : 'Não quer conectar? Informe só o número'}
        <ChevronDown size={18} strokeWidth={1.6} aria-hidden
          className="shrink-0 text-muted-foreground transition-transform group-open:rotate-180" />
      </summary>
      <div className="space-y-3 border-t border-border-soft p-4">
        <p className="text-sm text-muted-foreground">
          {pareadoPausado
            ? 'Se o seu WhatsApp desconectar, o "Quero renovar" do cliente passa a usar este número.'
            : comoReserva
              ? 'Se o seu WhatsApp desconectar, o "Quero renovar" do cliente usa este número até você conectar de novo.'
              : 'Informe o número em que você atende. O "Quero renovar" do cliente chega nele, direto para você. É só o número: nada é enviado por ele.'}
        </p>
        {blocoDoNumero}
      </div>
    </details>
  );
  const numeroDoPareado = mascararNumero(efetivo?.numero);

  return (
    <div className="space-y-4">
      {pareadoPausado ? (
        <>
          <section aria-labelledby="zap-pareado-titulo" className="space-y-3 rounded-xl border border-border bg-surface p-4">
            <h3 id="zap-pareado-titulo" className="flex items-center gap-2 text-base font-semibold text-foreground">
              <Smartphone size={18} strokeWidth={1.6} aria-hidden />
              Seu WhatsApp de trabalho
            </h3>
            <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-foreground">
              <CheckCircle2 size={16} strokeWidth={1.6} className="shrink-0 text-success" aria-hidden />
              <span className="font-medium">Este é o seu WhatsApp de trabalho</span>
              {numeroDoPareado && <span className="tabular-nums">· {numeroDoPareado}</span>}
            </p>
            <p className="text-sm text-foreground">O &quot;Quero renovar&quot; do cliente chega neste número.</p>
            <p className="text-sm text-muted-foreground">A conversa com o AutoBrokers por este WhatsApp está pausada no momento.</p>
          </section>
          {/* o digitado só vira reserva quando é OUTRO número (sem digitado, o bloco fechado deixa informar um) */}
          {!(reserva && !reserva.diferente) && blocoRecolhido}
        </>
      ) : linhaOfertada ? (
        <>
          <MinhaLinhaDoWhatsApp linha={linha} aoMudar={setLinha} recarregar={recarregarLinha}
            queroRenovarNoPareado={queroRenovarNoPareado} reserva={reserva} />
          {blocoRecolhido}
        </>
      ) : (
        <>
          <div className="space-y-1">
            <h3 className="text-base font-semibold text-foreground">Seu WhatsApp de trabalho</h3>
            <p className="text-sm text-muted-foreground">
              O número em que você atende os clientes. O &quot;Quero renovar&quot; do cliente chega aqui, direto para você.
            </p>
          </div>
          {blocoDoNumero}
        </>
      )}

      {atual?.disponivel !== false && (atalhoDisponivel || verificado || !linhaOfertada) && (
        <section aria-labelledby="atalho-whatsapp-titulo" className="space-y-3 rounded-xl border border-border bg-surface p-4">
          <h4 id="atalho-whatsapp-titulo" className="flex items-start gap-2 text-sm font-semibold text-foreground">
            <MessageCircle size={16} strokeWidth={1.6} className="mt-0.5 shrink-0" aria-hidden />
            Falar com o AutoBrokers pelo número dele no WhatsApp
          </h4>

          {verificado ? (
            <p className="flex items-start gap-2 text-sm text-foreground" role="status">
              <CheckCircle2 size={16} strokeWidth={1.6} className="mt-0.5 shrink-0 text-success" aria-hidden />
              <span>Verificado — você pode falar com o AutoBrokers pelo WhatsApp, do número que você informou.</span>
            </p>
          ) : !atalhoDisponivel ? (
            <p className="text-sm text-muted-foreground">
              Em breve: você vai poder conversar com o AutoBrokers pelo seu WhatsApp de trabalho, como no chat.
            </p>
          ) : !numeroConfirmado ? (
            <p className="text-sm text-muted-foreground">
              Primeiro informe e confirme o número em que você atende, acima. Depois, você manda um código desse número
              para o AutoBrokers.
            </p>
          ) : !codigo ? (
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground">
                Escreva, mande áudio, foto ou o PDF da apólice pelo seu WhatsApp, como no chat. Antes, prove que o
                número é seu: você manda um código do seu celular para o AutoBrokers.
              </p>
              <button type="button" onClick={pedirCodigo} disabled={pedindo}
                className={cn('h-11 rounded-lg px-5 text-sm font-medium disabled:opacity-60', BOTAO_PRIMARIO, FOCO)}>
                {pedindo ? 'Gerando o código…' : 'Usar pelo WhatsApp'}
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              <ol className="list-decimal space-y-2 pl-5 text-sm text-foreground">
                <li>
                  Salve o contato <strong>AutoBrokers</strong>
                  {codigo.numero_assistente ? (
                    <> com o número <span className="tabular-nums">{exibir(codigo.numero_assistente)}</span></>
                  ) : null}
                  .
                </li>
                <li>
                  Mande a mensagem abaixo do celular com o número{' '}
                  <strong className="tabular-nums">{atual?.numero ? exibir(atual.numero) : 'que você salvou'}</strong>.
                  De outro número, ela não vale.
                </li>
              </ol>
              <p className="w-fit rounded-lg border border-border bg-background px-4 py-3 font-mono text-lg font-semibold tracking-wider text-foreground tabular-nums"
                aria-label={`Mensagem: ${codigo.texto}`}>
                {codigo.texto}
              </p>
              <p className="text-sm text-muted-foreground">Expira em {codigo.validade_minutos || 15} minutos. Vale uma vez só.</p>
              <div className="flex flex-wrap gap-2">
                {codigo.wa_me_url && (
                  <a href={codigo.wa_me_url} target="_blank" rel="noopener noreferrer"
                    className={cn('inline-flex h-11 items-center justify-center rounded-lg px-5 text-sm font-medium', BOTAO_PRIMARIO, FOCO)}>
                    Abrir no WhatsApp
                  </a>
                )}
                <button type="button" onClick={() => { setAviso(''); onMudou(); }} className={BOTAO_SECUNDARIO}>
                  Já mandei
                </button>
                <button type="button" onClick={pedirCodigo} disabled={pedindo} className={BOTAO_SECUNDARIO}>
                  {pedindo ? 'Gerando…' : 'Gerar outro código'}
                </button>
              </div>
              <p className="text-sm text-muted-foreground">
                Depois de mandar, toque em &quot;Já mandei&quot;. O AutoBrokers responde no WhatsApp quando o número for verificado.
              </p>
            </div>
          )}
          {erroDoCodigo && <p className="text-sm text-danger" role="alert">{erroDoCodigo}</p>}
        </section>
      )}

      {/* sem a conexão oferecida, o digitado é SÓ um número; com ela (ou com o pareado pausado), não é (§9.3) */}
      {!linhaOfertada && !pareadoPausado && (
        <p className="flex items-start gap-2 rounded-lg border border-border-soft p-3 text-sm text-muted-foreground">
          <Info size={16} strokeWidth={1.6} className="mt-0.5 shrink-0" aria-hidden />
          <span>
            É só o número: o AutoBrokers não se conecta a ele nem envia nada por ele, e nada vai para os seus clientes.
            {verificado ? ' Quando você escreve para o número do AutoBrokers, ele responde a você, pelo número dele.' : ''}
          </span>
        </p>
      )}
      {erro && <p className="text-sm text-danger" role="alert">{erro}</p>}
      {aviso && <p className="text-sm text-foreground dark:text-success" role="status">{aviso}</p>}
    </div>
  );
}

export default MeuWhatsAppDeTrabalho;
