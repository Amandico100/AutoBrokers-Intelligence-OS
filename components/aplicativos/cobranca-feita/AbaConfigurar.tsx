'use client';

// SPEC-139 · L2 — a aba Configurar da Cobrança: o formulário que morava no MODAL do `PainelDeRotinas`, agora na casa do
// aplicativo (D-139-04, laudo de design §4). O MESMO formulário extraído (`FormularioDaRotina`), o MESMO estado e a
// MESMA gravação (`useFormularioDaRotina().salvar` → POST /api/dashboard/rotinas) — o teste dourado
// (`scripts/a-cobranca-na-casca.test.mjs`) prova que os mesmos cliques gravam o mesmo corpo. 🔴 Nenhuma regra de envio
// muda aqui: quem decide o que sai é o backend (`billing_collection.py`), intocado.
//
// O que ela acrescenta é só a CASA: a barra "Alterações não salvas" que aparece com alteração, o 409 em português, a
// situação da rotina (ativa/pausada) e o Avançado recolhido (limites, reenvio de teste, apagar).

import { useCallback, useEffect, useMemo, useState } from 'react';
import { AlertTriangle, Loader2 } from 'lucide-react';

import { Confirmar } from '@/components/aplicativos/casca/Confirmar';
import { Selo } from '@/components/aplicativos/casca/Selo';
import { BarraSalvar, Grupo, Linha, Segmentado } from '@/components/aplicativos/configurar/pecas';
import { Skeleton } from '@/components/ui/skeleton';
import type { PropsDaAba } from '@/lib/auxiliaries/catalog';

import { FormularioDaRotina } from './FormularioDaRotina';
import { LiberarReenvioDeTeste } from './LiberarReenvioDeTeste';
import { ROTA_DAS_ROTINAS, corpoDaAcao, rotuloDaAgenda, type FormDaRotina, type Routine } from './formulario';
import { useFormularioDaRotina } from './useFormularioDaRotina';

const SLUG_PADRAO = 'cobranca-feita';

function quando(iso: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (!Number.isFinite(d.getTime())) return '—';
  return d.toLocaleString('pt-BR', { timeZone: 'America/Sao_Paulo', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
}

const BOTAO_SECUNDARIO =
  'inline-flex min-h-[44px] items-center gap-1.5 rounded-lg border border-border px-3 text-sm font-medium text-foreground hover:bg-surface-2 disabled:opacity-50 sm:min-h-[40px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring';

export function AbaConfigurar({ item }: Partial<PropsDaAba> = {}) {
  const slug = item?.slug ?? SLUG_PADRAO;
  const nome = item?.nome ?? 'Cobrança';
  const instalado = Boolean(item?.instalado);
  const ligado = item?.estado === 'ligado';

  const f = useFormularioDaRotina({ auxiliarSlug: slug, auxiliarNome: nome });
  const { abrir } = f;

  const [rotinas, setRotinas] = useState<Routine[] | null>(null);
  const [erroDaLista, setErroDaLista] = useState('');
  const [escolhida, setEscolhida] = useState<string | 'new' | null>(null);
  const [base, setBase] = useState<FormDaRotina | null>(null);
  const [mostrarMotivo, setMostrarMotivo] = useState(false);
  const [erroDoSalvar, setErroDoSalvar] = useState('');
  const [salvo, setSalvo] = useState(false);
  const [conflito, setConflito] = useState(false);
  const [agindo, setAgindo] = useState(false);
  const [avisoDaRotina, setAvisoDaRotina] = useState('');

  /** Lê as rotinas DESTE aplicativo (a API filtra pelo dono e pela corretora) e abre a escolhida. */
  const carregar = useCallback(async (manter?: string | 'new' | null) => {
    setErroDaLista('');
    try {
      const res = await fetch(`${ROTA_DAS_ROTINAS}?auxiliar=${encodeURIComponent(slug)}`, { cache: 'no-store' });
      const j = await res.json().catch(() => ({}));
      if (!res.ok) {
        setErroDaLista(j?.error || 'Não conseguimos carregar a configuração agora.');
        setRotinas([]);
        return;
      }
      const lista = (j.routines || []) as Routine[];
      setRotinas(lista);
      const alvo = manter && (manter === 'new' || lista.some((r) => r.id === manter)) ? manter : (lista[0]?.id ?? 'new');
      const r = alvo === 'new' ? 'new' : (lista.find((x) => x.id === alvo) ?? 'new');
      const aberto = await abrir(r);
      setBase(aberto);
      setEscolhida(r === 'new' ? 'new' : r.id);
    } catch {
      setErroDaLista('Sem conexão com o servidor agora. Tente de novo em instantes.');
      setRotinas([]);
    }
  }, [slug, abrir]);

  useEffect(() => { if (instalado) carregar(); }, [instalado, carregar]);

  const rotina = useMemo(
    () => (escolhida && escolhida !== 'new' ? (rotinas || []).find((r) => r.id === escolhida) ?? null : null),
    [rotinas, escolhida],
  );
  const nova = escolhida === 'new';
  const alterado = Boolean(base) && (nova || JSON.stringify(f.form) !== JSON.stringify(base));

  useEffect(() => { if (alterado) setSalvo(false); }, [alterado]);

  const enviar = async () => {
    setErroDoSalvar('');
    if (f.motivo) { setMostrarMotivo(true); return; }
    const r = await f.salvar();
    if (r.ok) {
      setMostrarMotivo(false);
      setConflito(false);
      // a rotina nova passa a existir: reabre a recém-criada (a primeira da lista, a mais nova)
      await carregar(nova ? null : escolhida);
      setSalvo(true);
      return;
    }
    if (r.status === 409) { setConflito(true); return; }
    setErroDoSalvar(r.erro || 'Não deu para salvar agora. Tente de novo em instantes.');
  };

  const descartar = () => {
    if (base) f.restaurar(base);
    setMostrarMotivo(false);
    setErroDoSalvar('');
  };

  /** Pausar, reativar ou apagar a rotina — a MESMA rota e o MESMO corpo das ações da lista do painel. */
  const agir = async (action: 'pause' | 'activate' | 'delete') => {
    if (!rotina) return;
    setAgindo(true);
    setAvisoDaRotina('');
    try {
      const res = await fetch(ROTA_DAS_ROTINAS, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(corpoDaAcao(rotina.id, action)),
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        setAvisoDaRotina(j?.error || 'Não foi possível concluir agora.');
      }
    } catch {
      setAvisoDaRotina('Sem conexão com o servidor agora.');
    }
    setAgindo(false);
    await carregar(action === 'delete' ? null : rotina.id);
  };

  const aviso = conflito
    ? 'Outra pessoa salvou antes. Recarregue para ver a versão nova.'
    : erroDoSalvar
      || (mostrarMotivo && f.motivo)
      || (!alterado && salvo ? 'Configuração salva.' : '')
      || (nova ? 'Esta agenda ainda não existe: confira e salve para criar.' : '');

  if (!item?.instalado) {
    return (
      <div className="mx-auto max-w-3xl rounded-xl border border-border bg-surface p-6">
        <p className="text-base font-medium text-foreground">Instale o aplicativo para configurar.</p>
        <p className="mt-1 text-sm text-muted-foreground">
          Use o botão lá em cima. Instalar não liga nada: ele só começa a cobrar quando você ligar, depois de configurar.
        </p>
      </div>
    );
  }

  if (erroDaLista) {
    return (
      <div className="mx-auto max-w-3xl space-y-3 py-6">
        <p className="text-sm text-foreground">{erroDaLista}</p>
        <button type="button" onClick={() => carregar(escolhida)} className={BOTAO_SECUNDARIO}>Tentar de novo</button>
      </div>
    );
  }

  if (rotinas === null || !base || !f.editing) {
    return (
      <div className="mx-auto max-w-3xl space-y-6 py-6" aria-busy="true">
        {[0, 1, 2].map((i) => <Skeleton key={i} className="h-32 w-full rounded-xl" />)}
      </div>
    );
  }

  const avancadoExtra = (
    <Grupo id="cobranca-rotina" titulo="Mais opções" descricao="O reenvio de teste, uma segunda agenda e apagar.">
      <Linha rotulo="Reenvio dos boletos de teste"
        info="Em Teste, cada boleto sai uma vez só para o seu número. Liberar faz os já enviados em teste saírem de novo na próxima execução. Envios reais a segurados não são afetados.">
        <LiberarReenvioDeTeste />
      </Linha>
      {!nova && (
        <Linha rotulo="Outra agenda"
          info="Uma segunda agenda deste aplicativo, com outro horário ou outras seguradoras. A maioria das corretoras usa uma só.">
          <button type="button" className={BOTAO_SECUNDARIO} onClick={() => carregar('new')}>Criar outra agenda</button>
        </Linha>
      )}
      {rotina && (
        <Linha rotulo="Apagar esta agenda" info="O histórico das execuções também é removido. A configuração não volta.">
          <Confirmar titulo="Apagar esta agenda?" descricao="O histórico das execuções também será removido." acao="Apagar" perigo
            onConfirmar={() => agir('delete')}>
            <button type="button" className={BOTAO_SECUNDARIO} disabled={agindo}>Apagar</button>
          </Confirmar>
        </Linha>
      )}
    </Grupo>
  );

  return (
    <div className="mx-auto max-w-3xl space-y-10 pb-6 pt-2">
      {/* 🔴 SPEC-078 A.3 — rotina ativa com o aplicativo desligado NÃO roda (o motor consulta o aplicativo). */}
      {!ligado && (rotinas.length > 0) && (
        <p className="flex items-start gap-2 rounded-lg border border-warning/40 bg-warning/10 px-3 py-2 text-sm text-foreground" role="note">
          <AlertTriangle size={16} strokeWidth={1.6} className="mt-0.5 shrink-0 text-warning" aria-hidden />
          <span>O aplicativo está <strong>desligado</strong>: nenhuma cobrança sai até você ligar. A configuração fica guardada.</span>
        </p>
      )}

      {(rotinas.length > 1 || (nova && rotinas.length > 0)) && (
        <Grupo id="cobranca-qual" titulo="Qual agenda" descricao="Este aplicativo tem mais de uma agenda.">
          <div className="p-4">
            <Segmentado<string> rotulo="Qual agenda" valor={escolhida ?? 'new'} onChange={(v) => carregar(v)}
              opcoes={[
                ...rotinas.map((r) => ({ valor: r.id, titulo: rotuloDaAgenda(r.schedule) })),
                ...(nova ? [{ valor: 'new', titulo: 'Nova' }] : []),
              ]} />
          </div>
        </Grupo>
      )}

      {rotina && (
        <Grupo id="cobranca-situacao" titulo="Situação" descricao={rotuloDaAgenda(rotina.schedule)}>
          {/* juiz de design 139 (Configurar §2): com o aplicativo DESLIGADO, "Ativa · Pausar" contradizia o "Desligado ·
              Ligar" do cabeçalho. Desligado, a agenda ativa fica NEUTRA ("vai rodar quando você ligar") e sem Pausar —
              quem decide se roda é o Ligar lá em cima. Nenhum estado gravado muda: é só o que a tela diz. */}
          <Linha rotulo="Esta agenda"
            info="Pausada, ela não roda mesmo com o aplicativo ligado. Reativar zera a contagem de falhas seguidas.">
            <div className="flex flex-wrap items-center gap-2">
              {rotina.is_active && !ligado ? (
                <Selo tom="neutral" rotulo="Vai rodar quando você ligar o aplicativo" />
              ) : (
                <Selo tom={rotina.is_active ? 'success' : 'neutral'} rotulo={rotina.is_active ? 'Ativa' : 'Pausada'} />
              )}
              {rotina.consecutive_failures >= 5 && <Selo tom="danger" rotulo="Parou por falhas seguidas" />}
              {(ligado || !rotina.is_active) && (
                <button type="button" className={BOTAO_SECUNDARIO} disabled={agindo}
                  onClick={() => agir(rotina.is_active ? 'pause' : 'activate')}>
                  {agindo && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
                  {rotina.is_active ? 'Pausar' : 'Reativar'}
                </button>
              )}
            </div>
            <p className="mt-2 text-sm text-muted-foreground">
              {ligado
                ? <>Próxima: {quando(rotina.next_run_at)} · última: {quando(rotina.last_run_at)}</>
                : <>Última: {quando(rotina.last_run_at)}</>}
            </p>
            {avisoDaRotina && <p className="mt-2 text-sm text-danger" role="alert">{avisoDaRotina}</p>}
          </Linha>
        </Grupo>
      )}

      <FormularioDaRotina f={f} auxiliarNome={nome} prefixo="cobranca" avancadoExtra={avancadoExtra} />

      <BarraSalvar visivel={alterado} salvando={f.saving} aviso={aviso || undefined} conflito={conflito}
        onDescartar={descartar} onSalvar={enviar} onRecarregar={() => { setConflito(false); carregar(escolhida); }} />
    </div>
  );
}

export default AbaConfigurar;
