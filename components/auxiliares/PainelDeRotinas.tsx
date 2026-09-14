'use client';

// F2 — Rotinas agendadas da corretora: lista, pausa/ativa, exclui e mostra as
// últimas execuções. Criação acontece pelo Chat Principal ("todo dia às 8h...").

import { useCallback, useEffect, useState } from 'react';
import { Loader2, Pause, Pencil, Play, Plus, Trash2 } from 'lucide-react';

import { StatusPill } from '@/components/patterns/StatusPill';

interface Routine {
  id: string;
  name: string;
  instructions: string;
  knowledge?: string | null;
  schedule: { kind?: string; time?: string; minutes?: number; weekdays?: number[] };
  delivery: { channel?: string; number?: string };
  config?: Record<string, unknown> | null;
  is_active: boolean;
  last_run_at: string | null;
  next_run_at: string | null;
  consecutive_failures: number;
}

interface Run {
  id: string;
  routine_id: string;
  started_at: string;
  status: string;
  output_preview: string | null;
  error: string | null;
}

/**
 * Uma parcela da cobrança REAL que ainda espera alguém — SPEC-EXTRA-001 §6.
 *
 * Os campos são exatamente os que a rota `pendencias` devolve. Note o que NÃO
 * está aqui: telefone. Só `to_last4`, os últimos 4 dígitos (CLAUDE.md §7).
 */
interface PendenciaDaCobranca {
  id: string;
  status: string;
  modalidade: string | null;
  portal_key: string | null;
  recibo: string | null;
  cliente_nome: string | null;
  apolice_susep: string | null;
  to_last4: string | null;
  sent_at: string | null;
  updated_at: string | null;
  retorno_do_cliente: string | null;
  retorno_em: string | null;
  encaminhado_ao_cliente_em: string | null;
  motivo: string | null;
}

const DIAS = ['seg', 'ter', 'qua', 'qui', 'sex', 'sáb', 'dom'];
const BILLING_KIND = 'billing_collection';

/**
 * Qual modelo de rotina cada Auxiliar configura.
 *
 * 📊 Medido em 17/08/2026: em 02/08/2026 os commits `2ef6750` e `965efff`
 * (SPEC-064) removeram os DOIS únicos links que chegavam nesta tela. A tela
 * nunca foi apagada — ficou sem porta. E o único link que sobrou
 * (`AuxiliarDetalheClient.tsx`) só aparece quando o Auxiliar já tem rotina,
 * o que é impossível se não há como criar a primeira. Beco sem saída fechado
 * dos dois lados.
 *
 * Este mapa é a porta de volta. Ele existe em TypeScript porque **não há
 * coluna no banco ligando `auxiliary_templates` a `routine_templates`** —
 * `auxiliary_templates.default_config` nem sequer tem `kind`, e usa nomes
 * DIFERENTES para os mesmos campos (`portais` vs `portal_keys`,
 * `exige_aprovacao_para_enviar` vs `approval_required`). Copiar um no outro
 * faria a seleção de seguradoras cair no default sem avisar ninguém.
 *
 * ⚠️ Enquanto essa coluna não existir, um Auxiliar novo com rotina própria
 * precisa de uma linha aqui. Registrado em PENDENCIAS.md.
 */
const ROTINA_DO_AUXILIAR: Record<string, string> = {
  'cobranca-feita': BILLING_KIND,
};

type ModeloDeRotina = {
  id?: string;
  name: string;
  instructions: string;
  schedule_default?: { kind?: string; time?: string; minutes?: number; weekdays?: number[] };
  delivery_default?: { channel?: string };
  config_default?: Record<string, unknown>;
};

/**
 * Os dias da semana, do jeito que gente lê.
 *
 * 🔴 SPEC-078 D.6. Aqui era uma caixa de texto onde o corretor digitava
 * `0,1,2,3,4` com a legenda "0=seg … 6=dom". A legenda estava CERTA — a
 * convenção é a do `datetime.weekday()` do Python, confirmada em três lugares
 * do motor — mas pedir que alguém decore isso para agendar uma cobrança é
 * transferir para o corretor um detalhe que é nosso.
 */
const DIAS_DA_SEMANA: { valor: number; curto: string; longo: string }[] = [
  { valor: 0, curto: 'seg', longo: 'segunda' },
  { valor: 1, curto: 'ter', longo: 'terça' },
  { valor: 2, curto: 'qua', longo: 'quarta' },
  { valor: 3, curto: 'qui', longo: 'quinta' },
  { valor: 4, curto: 'sex', longo: 'sexta' },
  { valor: 5, curto: 'sáb', longo: 'sábado' },
  { valor: 6, curto: 'dom', longo: 'domingo' },
];

/**
 * Os modos de envio que TÊM MOTOR — SPEC-078 E.1.
 *
 * 📊 Medido em 17/08/2026, lendo `billing_collection.py`:
 *
 *   test      ✅ funciona. É o único que envia. Destino: só o `test_number`.
 *   none      ✅ funciona por não fazer nada, que é o comportamento correto.
 *   approval  ❌ cria a linha em `approval_requests` e ninguém a consome. A
 *               string `send_billing_whatsapp` aparece UMA vez no repositório
 *               inteiro: no próprio insert. O endpoint de execução tem
 *               allowlist e ela não está nela.
 *   live      ❌ `billing_collection.py:1206-1213` tem dois ramos e os dois só
 *               acrescentam uma frase ao relatório. Não há `else` que envie.
 *
 * Tirar os dois do seletor não apaga funcionalidade — apaga a PROMESSA de
 * funcionalidade. Um seletor que oferece "Ao cliente" e não manda ao cliente é
 * pior que a ausência da opção: ensina o corretor a confiar num controle que
 * não existe. Os valores continuam válidos no banco; a SPEC-079 os devolve
 * quando tiverem motor.
 *
 * ─────────────────────────────────────────────────────────────────────────
 * SPEC-EXTRA-001 (📊 07/09/2026) — DOIS MODOS NOVOS ENTRAM, E ENTRAM PORQUE
 * AGORA TÊM MOTOR: `_entregar_cobranca_real` em
 * `backend/app/services/billing_collection.py` reserva a obrigação, chama a
 * porta de saída e marca o ledger.
 *
 *   equipe   ✅ a atendente recebe o pacote pronto (nota interna + texto +
 *              boleto) e repassa. Envio interno: um número só, o da corretora.
 *   cliente  ✅ o segurado recebe o texto e o boleto. Exige confirmação
 *              explícita nesta tela (`confirmacao_cliente`) — o motor recusa
 *              sem ela.
 *
 * `approval` e `live` NÃO voltam: eles continuam sem motor, e agora têm nome
 * para o que são — `retido_legado`. Uma config que ainda os carregue não
 * envia nada, e a tela pede que a pessoa escolha uma das quatro modalidades.
 * A regra continua a mesma de 17/08: nenhum controle sem motor por trás.
 */
const MODOS_COM_MOTOR = [
  { valor: 'test', rotulo: 'Teste — envia para o meu número de teste' },
  { valor: 'none', rotulo: 'Somente relatório — não envia nada' },
  { valor: 'equipe', rotulo: 'Encaminhar para minha equipe — a atendente recebe o pacote pronto e repassa' },
  { valor: 'cliente', rotulo: 'Enviar diretamente ao cliente — o segurado recebe texto e boleto' },
] as const;

/**
 * O nome que a corretora lê no lugar da chave do portal.
 *
 * 📊 Cópia de `NOME_DA_SEGURADORA` (`billing_collection.py:458-473`), com o
 * mesmo fallback: portal novo sem entrada vira o prefixo em maiúsculas
 * (`sancor_corretor` → "SANCOR"), que ainda é reconhecível — nunca a palavra
 * genérica "seguradora", que parece defeito de sistema para quem lê.
 *
 * ⚠️ Cópia envelhece. Ela está aqui porque a lista de pendências não tem por
 * que fazer uma chamada ao backend só para traduzir seis chaves; e o custo de
 * envelhecer é baixo justamente por causa do fallback — uma seguradora nova
 * aparece com o nome derivado, não some nem vira "seguradora".
 */
const NOME_DA_SEGURADORA: Record<string, string> = {
  allianz_corretor: 'ALLIANZ',
  hdi_corretor: 'HDI SEGUROS',
  porto_corretor: 'PORTO SEGURO',
  yelum_corretor: 'YELUM',
  tokiomarine_corretor: 'TOKIO MARINE',
  bradesco_corretor: 'BRADESCO SEGUROS',
  mapfre_corretor: 'MAPFRE',
  azul_corretor: 'AZUL SEGUROS',
  alfa_corretor: 'ALFA SEGURADORA',
  sulamerica_corretor: 'SULAMERICA',
  sompo_corretor: 'SOMPO SEGUROS',
  suhai_corretor: 'SUHAI',
  sura_corretor: 'SURA',
  zurich_corretor: 'ZURICH',
  segurosunimed_corretor: 'SEGUROS UNIMED',
};

function nomeDaSeguradora(portalKey: string): string {
  const chave = String(portalKey || '').trim().toLowerCase();
  if (!chave) return 'seguradora não identificada';
  if (NOME_DA_SEGURADORA[chave]) return NOME_DA_SEGURADORA[chave];
  if (chave.endsWith('_corretor')) return chave.slice(0, -'_corretor'.length).replace(/_/g, ' ').toUpperCase();
  return chave.toUpperCase();
}

/**
 * O que a corretora vê no lugar do estado do ledger — SPEC-EXTRA-001 §2.
 *
 * 🔴 A tradução não é enfeite. `parcial` e `incerto` são estados que só
 * significam alguma coisa para quem escreveu o motor; para quem trabalha na
 * corretora, um diz "o texto foi e o PDF não" e o outro diz "não sei se saiu".
 * A diferença entre os dois decide se alguém reenvia ou se alguém confere
 * antes — e essa decisão chega ao segurado.
 *
 * `contestado` é o único que precisa do que o cliente respondeu junto, então
 * ele é uma função e não uma string.
 */
const RETORNO_DO_CLIENTE: Record<string, string> = {
  ja_paguei: 'já paguei',
  nao_sou: 'não sou essa pessoa',
  nao_quero: 'não quer receber',
  segunda_via: 'pediu segunda via',
  duvida: 'ficou com dúvida',
  outro: 'respondeu algo fora do previsto',
};

const SITUACAO_HUMANA: Record<string, string> = {
  entregue_equipe: 'Entregue à equipe — falta encaminhar ao cliente',
  parcial: 'Texto foi, PDF não',
  incerto: 'Não sei se saiu — precisa de conferência',
  suprimido: 'Cliente pediu para não receber',
  falhou: 'Não saiu',
  adiado: 'Adiado — tenta na próxima execução',
  liberado: 'Liberada — sai na próxima execução da rotina, pela modalidade configurada',
};

function situacaoEmPortugues(item: PendenciaDaCobranca): string {
  if (item.status === 'contestado') {
    const retorno = RETORNO_DO_CLIENTE[String(item.retorno_do_cliente || '')] || 'respondeu';
    return `Cliente respondeu: ${retorno}`;
  }
  return SITUACAO_HUMANA[item.status] || item.status;
}

/**
 * Estados de onde NÃO se libera reenvio, e o porquê ao lado.
 *
 * ⛔ `suprimido` é terminal: o cliente pediu para não receber, e essa decisão
 * é dele. A rota responde 409 de qualquer jeito — desabilitar aqui é para a
 * pessoa não tentar, e ler o motivo em vez de um erro.
 */
const NAO_LIBERA: Record<string, string> = {
  suprimido: 'O cliente pediu para não receber. Essa decisão é dele.',
  incerto: 'Confira antes: liberar sem saber se saiu pode cobrar o cliente duas vezes.',
  // Já está liberada: o botão de novo só devolveria 409 (juiz fresco 07/09, P-J1).
  liberado: 'Já liberada — sai na próxima execução da rotina.',
};

/**
 * As chaves que `build_customer_message` de fato substitui.
 *
 * 📊 Lidas de `billing_collection.py:503-518`. Precisam ser as mesmas: uma
 * chave que não está lá **some da frase** em vez de aparecer como texto —
 * `_MessageData.__missing__` devolve string vazia. Um `{nome_cliente}` digitado
 * errado vira um buraco no meio da mensagem que o segurado recebe, e ninguém é
 * avisado.
 *
 * ⚠️ Esta lista é uma CÓPIA do Python e cópia envelhece. Ela está aqui porque a
 * alternativa — pedir a lista ao backend a cada digitação — custa uma chamada
 * por tecla. O guarda contra o envelhecimento é o teste
 * `scripts/mensagem-da-cobranca-bate-com-o-motor.test.mjs`, que lê o Python.
 */
const CHAVES_DA_MENSAGEM = [
  '{primeiro_nome}', '{nome_segurado}', '{cliente_nome}', '{nome_atendente}',
  '{nome_corretora}', '{nome_seguradora}', '{numero_parcela}', '{item_segurado}',
  '{numero_apolice}', '{vencimento}', '{valor}', '{apolice}', '{recibo}', '{portal}',
];

/** 📊 `DEFAULT_MESSAGE_TEMPLATE` de `billing_collection.py:81-88`, sem cortar. */
const MENSAGEM_PADRAO = [
  'Olá {primeiro_nome},',
  '',
  'Aqui é a {nome_atendente}, da {nome_corretora}, tudo bem?',
  '',
  'A Seguradora {nome_seguradora} informou que a parcela {numero_parcela} do seguro do {item_segurado} ainda está pendente.',
  '',
  'Desta forma, a seguradora gerou um novo boleto para pagamento pra você não ficar sem cobertura, ok!?',
  '',
  'Qualquer dúvida estou à disposição.',
  '',
  'Segue o boleto abaixo.',
  'Apólice: {numero_apolice}',
].join('\n');

/** Dados fictícios só para a pré-visualização. Nenhum segurado real aqui. */
const EXEMPLO_DA_PREVIA: Record<string, string> = {
  '{primeiro_nome}': 'Ana', '{nome_segurado}': 'Ana Ribeiro', '{cliente_nome}': 'Ana Ribeiro',
  '{nome_atendente}': 'Maria', '{nome_corretora}': 'sua corretora',
  '{nome_seguradora}': 'ALLIANZ', '{numero_parcela}': '3/12',
  '{item_segurado}': 'HONDA CIVIC ABC1D23', '{numero_apolice}': '0000123456',
  '{vencimento}': '25/08/2026', '{valor}': 'R$ 412,90',
  '{apolice}': '0000123456', '{recibo}': '987654', '{portal}': 'ALLIANZ',
};

/**
 * SPEC-069 — os portais que a Cobrança varre vêm da CONEXÃO, não do código.
 *
 * Aqui existia uma caixinha só, escrita à mão, com `allianz_corretor` fixo — e
 * marcá-la SUBSTITUÍA a lista inteira (`portal_keys: ['allianz_corretor']`).
 * Ou seja: não havia como a corretora varrer duas seguradoras. Uma corretora
 * que fosse forte em Bradesco simplesmente não tinha o produto.
 *
 * Agora a lista é a das seguradoras que a própria corretora conectou. Os que
 * ainda não têm automação aparecem desligados e DITOS — some da tela é como
 * seguradora cai sem ninguém perceber.
 */
type PortalOpcao = {
  key: string;
  name: string;
  category: string;
  conectado: boolean;
  automatizado: boolean;
};

// 🔴 SPEC-073 (Q3) — aqui existia um array literal espelhando
// `portais_com_cobranca()`. A intenção era boa e o resultado, não: o registry
// cresceu para SEIS portais e esta cópia ficou em DOIS. Tokio, Yelum, MAPFRE e
// Zurich tinham journey completa e testada, e a corretora via "não
// automatizado". Capacidade construída, paga e invisível — e nenhum teste
// guardava a sincronia, porque ninguém compara um array TS com uma função
// Python.
//
// A correção não foi acrescentar quatro nomes. Foi **apagar a lista** e derivar
// de `/api/dashboard/portal-credentials`, que devolve a interseção entre o que
// o registry sabe fazer e o que a imagem no ar realmente carrega.
//
// Duas listas que precisam concordar sempre acabam discordando um dia. Uma só
// não tem com quem discordar.

function scheduleLabel(s: Routine['schedule']) {
  if (s?.kind === 'interval') return `a cada ${s.minutes} min`;
  const days = s?.weekdays?.length ? ` (${s.weekdays.map((d) => DIAS[d] ?? d).join(', ')})` : '';
  return `diária às ${s?.time || '?'}${days}`;
}

function fmt(iso: string | null) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
}

/**
 * SPEC-078 C.4 — este painel MUDOU DE CASA.
 *
 * Ele era `app/dashboard/auxiliares/rotinas/page.tsx`, uma página autônoma com
 * botão "Nova rotina", listando as rotinas de TODA a corretora.
 *
 * 📊 O achado que motivou a mudança: a SPEC-064 §B.3 mandou absorver QUATRO
 * rotas. Três viraram stub de redirect com a frase "O CONTEUDO FOI ABSORVIDO"
 * (`galeria`, `meus`, `execucoes`). Esta é a quarta, e a única que não foi.
 *
 * E o preço apareceu: `ONTOLOGIA-DO-TRABALHO.md:51` diz "Rotina nunca existe
 * sozinha", mas o botão "Nova rotina" numa lista sem dono criava exatamente
 * isso — a rotina órfã de 17/08 às 13:01 saiu dele.
 *
 * Agora o painel vive DENTRO da tela do Auxiliar, mostra só as rotinas DELE, e
 * a criação sempre sabe de quem é. O possessivo do título ("Rotinas deste
 * Auxiliar") faz o trabalho que o cânone pede: diz que é Rotina e diz de quem.
 */
export default function PainelDeRotinas({
  auxiliarSlug,
  auxiliarNome,
  auxiliarLigado,
}: {
  auxiliarSlug: string;
  auxiliarNome: string;
  /** `tenant_auxiliaries.status === 'active'`. Ver o aviso em D.9. */
  auxiliarLigado: boolean;
}) {
  const [routines, setRoutines] = useState<Routine[] | null>(null);
  const [runs, setRuns] = useState<Run[]>([]);
  const [notice, setNotice] = useState('');
  const [portais, setPortais] = useState<PortalOpcao[]>([]);
  // O backend não conseguiu confirmar contra o runtime implantado. A tela avisa
  // em vez de fingir que sabe.
  const [cobrancaDegradada, setCobrancaDegradada] = useState(false);
  // SPEC-019 B — modal de criação/edição manual (paridade Claude Rotinas)
  const [editing, setEditing] = useState<Routine | 'new' | null>(null);
  const [saving, setSaving] = useState(false);
  // SPEC-078 D.5 — separado do `notice` da lista, porque o `notice` é
  // renderizado ATRÁS do overlay do modal e o corretor não o vê.
  const [erroDoModal, setErroDoModal] = useState('');
  const [liberando, setLiberando] = useState(false);

  // 🔴 SPEC-EXTRA-001 §6 — a FILA da cobrança real.
  //
  // Sem esta lista, `entregue_equipe` (a atendente recebeu, o cliente ainda
  // não) e `parcial` (o texto foi, o PDF não) ficariam pendurados no banco sem
  // ninguém para vê-los: o relatório da rotina é uma foto do dia, não uma fila
  // de trabalho. `null` = ainda carregando; `[]` = carregou e não há nada.
  const [pendencias, setPendencias] = useState<PendenciaDaCobranca[] | null>(null);
  const [erroPendencias, setErroPendencias] = useState('');
  const [agindoNaPendencia, setAgindoNaPendencia] = useState<string>('');
  const [motivoDaLiberacao, setMotivoDaLiberacao] = useState<Record<string, string>>({});
  const ehAuxiliarDeCobranca = ROTINA_DO_AUXILIAR[auxiliarSlug] === BILLING_KIND;

  /** SPEC-078 E.4 — ver o comentário no botão e na rota. */
  const liberarReenvioDeTeste = async () => {
    if (!confirm(
      'Liberar o reenvio dos boletos que já foram enviados EM TESTE?\n\n'
      + 'A próxima execução vai mandá-los de novo para o seu número de teste.\n'
      + 'Envios reais a segurados NÃO são afetados.',
    )) return;
    setLiberando(true);
    setNotice('');
    try {
      const r = await fetch('/api/dashboard/auxiliaries/cobranca/liberar-reenvio', { method: 'POST' });
      const j = await r.json().catch(() => ({}));
      setNotice(j?.ok ? j.mensagem : (j?.error || 'Não foi possível liberar o reenvio.'));
    } catch {
      setNotice('Falha de conexão.');
    }
    setLiberando(false);
  };
  const [form, setForm] = useState({
    name: '', instructions: '', knowledge: '', kind: 'daily', time: '08:00', weekdays: '' as string,
    minutes: 60, channel: 'whatsapp', number: '', config: {} as Record<string, unknown>,
  });

  // Carrega as seguradoras que ESTA corretora conectou. Uma chamada só, na
  // montagem: a lista muda em Conectores, não aqui.
  useEffect(() => {
    let vivo = true;
    (async () => {
      try {
        const res = await fetch('/api/dashboard/portal-credentials', { cache: 'no-store' });
        const j = await res.json();
        if (!vivo || !res.ok) return;
        const comCredencial = new Set(
          ((j.credentials || []) as { portal_key: string; has_password?: boolean }[])
            .filter((c) => c.has_password)
            .map((c) => c.portal_key),
        );
        // A capacidade vem do backend já resolvida contra o runtime implantado.
        // Se o backend não conseguiu confirmar (`degraded`), nenhum portal é
        // marcado como automatizado: dizer "não consegui confirmar" custa uma
        // tentativa, dizer "está pronto" sem estar custa um job que morre.
        const operacional = new Set<string>(
          Array.isArray(j.cobranca?.operacional) ? j.cobranca.operacional.map(String) : [],
        );
        setCobrancaDegradada(Boolean(j.cobranca?.degraded));
        setPortais(
          ((j.portals || []) as { key: string; name: string; category: string; cred_kind?: string }[])
            .filter((p) => p.category === 'corretor')
            .map((p) => ({
              key: p.key,
              name: p.name,
              category: p.category,
              conectado: comCredencial.has(p.key) || p.cred_kind === 'public',
              automatizado: operacional.has(p.key),
            })),
        );
      } catch {
        if (vivo) setPortais([]);
      }
    })();
    return () => { vivo = false; };
  }, []);

  const openEditor = async (r: Routine | 'new') => {
    if (r === 'new') {
      // 🔴 SPEC-078 D — "Nova rotina" NASCE PREENCHIDA pelo modelo do Auxiliar.
      //
      // 📊 Antes ela abria com `config: {}`, e a linha
      // `billingConfig = form.config?.kind === BILLING_KIND ? ... : null` fazia
      // TODOS os campos de cobrança sumirem. Eles só apareciam via `?template=`
      // — parâmetro cujo único emissor era o botão "Usar modelo" de uma galeria
      // que virou redirect em 02/08. Ou seja: dentro do Auxiliar de Cobrança, o
      // botão de criar rotina abria um formulário sem cobrança nenhuma.
      const modelo = await carregarModelo();
      if (modelo) {
        openEditorFromTemplate(modelo);
        return;
      }
      setForm({ name: auxiliarNome, instructions: '', knowledge: '', kind: 'daily', time: '08:00', weekdays: '0,1,2,3,4', minutes: 60, channel: 'none', number: '', config: {} });
    } else {
      setForm({
        name: r.name,
        instructions: r.instructions,
        knowledge: r.knowledge || '',
        kind: r.schedule?.kind === 'interval' ? 'interval' : 'daily',
        time: r.schedule?.time || '08:00',
        weekdays: (r.schedule?.weekdays || []).join(','),
        minutes: r.schedule?.minutes || 60,
        channel: r.delivery?.channel || 'whatsapp',
        number: r.delivery?.number || '',
        config: (r.config || {}) as Record<string, unknown>,
      });
    }
    setEditing(r);
  };

  // SPEC-019 C — "Usar modelo": abre a Nova rotina já preenchida pelo template.
  const openEditorFromTemplate = (t: ModeloDeRotina) => {
    const s = t.schedule_default || {};
    setForm({
      // 🔴 SPEC-078 D.1 — o nome é o do AUXILIAR, não o do modelo.
      // "Cobranca de boletos atrasados" era o nome do `routine_template`, e ver
      // um nome diferente do Auxiliar que se está configurando é a confusão
      // Auxiliar × Rotina aparecendo na primeira linha do formulário.
      name: auxiliarNome,
      instructions: t.instructions,
      knowledge: '',
      kind: s.kind === 'interval' ? 'interval' : 'daily',
      time: s.time || '08:00',
      // Seg–sex por padrão quando o modelo não diz nada. Cobrança em fim de
      // semana não é o que a corretora espera.
      weekdays: (s.weekdays && s.weekdays.length ? s.weekdays : [0, 1, 2, 3, 4]).join(','),
      minutes: s.minutes || 60,
      channel: t.delivery_default?.channel === 'none' ? 'none' : 'whatsapp',
      number: '',
      config: t.config_default || {},
    });
    setEditing('new');
  };

  const billingConfig = form.config?.kind === BILLING_KIND ? form.config : null;
  // Rotina nova nasce marcando o que é operacional HOJE — derivado, não
  // decorado. Rotina existente mantém exatamente o que a corretora escolheu:
  // uma seguradora nova entrando no registry não pode ligar sozinha a cobrança
  // de ninguém.
  const billingPortalKeys = billingConfig && Array.isArray(billingConfig.portal_keys)
    ? billingConfig.portal_keys.map((v) => String(v))
    : portais.filter((p) => p.automatizado && p.conectado).map((p) => p.key);

  // Liga/desliga UM portal sem mexer nos outros. A versão anterior trocava o
  // array inteiro a cada clique — era isso que impedia marcar dois.
  const alternarPortal = (key: string, marcado: boolean) => {
    const semEle = billingPortalKeys.filter((k) => k !== key);
    setBillingConfig({ portal_keys: (marcado ? [...semEle, key] : semEle).sort() });
  };
  const billingSendMode = String(billingConfig?.send_mode || 'test');
  // 🔴 SPEC-EXTRA-001 — config que ainda carrega `approval`/`live`.
  //
  // Ela não é convertida em silêncio para `cliente`: promover uma escolha
  // antiga, feita quando nada saía, em autorização para cobrar segurados de
  // verdade seria decidir pela corretora a coisa mais cara desta tela. O
  // seletor fica SEM valor até alguém escolher, e o aviso diz o que está
  // acontecendo enquanto isso: nada sai.
  const billingModoLegado = !!billingConfig
    && !MODOS_COM_MOTOR.some((m) => m.valor === billingSendMode);
  const billingTeamNumber = String(billingConfig?.team_number || '');
  const billingTeamDigitos = billingTeamNumber.replace(/\D/g, '');
  const billingConfirmacaoCliente = billingConfig?.confirmacao_cliente === true;

  // 🔴 SPEC-078 D.7 — o textarea abria VAZIO quando não havia template salvo.
  // O corretor nunca via a mensagem que o segurado receberia; ele via um campo
  // em branco e concluía que não havia mensagem nenhuma.
  const textoDaMensagem = String(billingConfig?.message_template || '') || MENSAGEM_PADRAO;

  // Chaves escritas que o motor não conhece. Elas não aparecem como texto na
  // mensagem — elas SOMEM, deixando um buraco na frase. Avisar antes de salvar
  // é mais barato que descobrir pelo segurado.
  const chavesDesconhecidas = Array.from(
    new Set((textoDaMensagem.match(/\{[a-z_]+\}/g) || []).filter((c) => !CHAVES_DA_MENSAGEM.includes(c))),
  );

  const previaDaMensagem = CHAVES_DA_MENSAGEM.reduce(
    (txt, chave) => txt.split(chave).join(EXEMPLO_DA_PREVIA[chave] ?? ''),
    textoDaMensagem,
  ).replace(/\{[a-z_]+\}/g, '');
  const billingMaxBoletos = Number(billingConfig?.max_boletos_por_execucao || 10);
  const billingTestNumber = String(billingConfig?.test_number || '');
  // 🔴 SPEC-EXTRA-001.6 P0.4 — quem assina a mensagem. 📊 10/09: o campo não
  // existia na tela, o config não tinha a chave, e o segurado leria "Aqui é a
  // nossa equipe, da Resulta". Nos modos reais o motor RETÉM a rotina sem ele.
  const billingAttendantName = String(billingConfig?.attendant_name || '');
  const setBillingConfig = (patch: Record<string, unknown>) => {
    setForm({
      ...form,
      config: {
        ...(form.config || {}),
        kind: BILLING_KIND,
        ...patch,
      },
    });
  };

  const saveRoutine = async () => {
    setSaving(true);
    setNotice('');
    const schedule: Record<string, unknown> = form.kind === 'interval'
      ? { kind: 'interval', minutes: Number(form.minutes) }
      : {
          kind: 'daily', time: form.time,
          ...(form.weekdays.trim()
            ? { weekdays: form.weekdays.split(',').map((d) => parseInt(d.trim(), 10)).filter((n) => !isNaN(n)) }
            : {}),
        };
    const delivery = form.channel === 'whatsapp' ? { channel: 'whatsapp', number: form.number } : { channel: 'none' };
    const outgoingConfig = billingConfig && billingSendMode === 'test' && !billingTestNumber.trim() && form.channel === 'whatsapp'
      ? { ...(form.config || {}), test_number: form.number }
      : form.config;
    const res = await fetch('/api/dashboard/rotinas', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        action: editing === 'new' ? 'create' : 'update',
        id: editing !== 'new' && editing ? editing.id : undefined,
        // 🔴 SPEC-078 C.3 — o dono vai JUNTO. `ONTOLOGIA:51`: "Rotina nunca
        // existe sozinha". O componente sabe de quem é porque vive dentro da
        // tela dele; antes esta chamada saía sem dono nenhum e o banco aceitava.
        auxiliar: auxiliarSlug,
        name: form.name, instructions: form.instructions, knowledge: form.knowledge, schedule, delivery, config: outgoingConfig,
      }),
    });
    const j = await res.json().catch(() => ({}));
    setSaving(false);
    if (!res.ok) {
      // 🔴 SPEC-078 D.5 — o erro vai para DENTRO do modal.
      //
      // 📊 O modal nunca fechava no erro (há um `return` antes do
      // `setEditing(null)`); o que acontecia é que a mensagem era renderizada
      // no corpo da PÁGINA, atrás do overlay `bg-black/60`. O Founder clicou
      // "Criar rotina", não viu nada acontecer, fechou o modal — e só então
      // leu "Número WhatsApp inválido". Duas telas de distância entre a causa
      // e quem precisava dela.
      //
      // `details[0]` carrega a mensagem crua do banco quando o erro não tem
      // texto próprio. Descartá-la é o mesmo defeito do `install_failed`.
      const tecnico = Array.isArray(j?.details) ? String(j.details[0] || '').trim() : '';
      setErroDoModal(
        (j.error || 'Erro ao salvar rotina.') + (tecnico ? ` — ${tecnico}` : ''),
      );
      return;
    }
    setEditing(null);
    setErroDoModal('');
    load();
  };

  const load = useCallback(async () => {
    try {
      // O `?auxiliar=` vai para a API, que filtra pelo dono. Filtrar aqui no
      // navegador funcionaria e seria pior: a corretora baixaria a lista das
      // rotinas de todos os Auxiliares para mostrar as de um.
      const res = await fetch(`/api/dashboard/rotinas?auxiliar=${encodeURIComponent(auxiliarSlug)}`,
        { cache: 'no-store' });
      const j = await res.json();
      if (!res.ok) {
        setNotice(j.error || 'Erro ao carregar rotinas.');
        setRoutines([]);
        return;
      }
      setRoutines(j.routines || []);
      setRuns(j.runs || []);
    } catch {
      setNotice('Falha de conexão.');
      setRoutines([]);
    }
  }, [auxiliarSlug]);

  useEffect(() => {
    load();
    const t = setInterval(load, 15000);
    return () => clearInterval(t);
  }, [load]);

  /** As pendências da cobrança real. Só existe no Auxiliar de Cobrança. */
  const carregarPendencias = useCallback(async () => {
    if (!ehAuxiliarDeCobranca) return;
    try {
      const res = await fetch('/api/dashboard/auxiliaries/cobranca/pendencias', { cache: 'no-store' });
      const j = await res.json().catch(() => ({}));
      if (!res.ok || !j?.ok) {
        // Dizer "não consegui carregar" é diferente de mostrar lista vazia. Uma
        // fila vazia por engano é uma fila que ninguém trabalha.
        setErroPendencias(j?.error || 'Não consegui carregar as pendências.');
        setPendencias([]);
        return;
      }
      setErroPendencias('');
      setPendencias((j.itens || []) as PendenciaDaCobranca[]);
    } catch {
      setErroPendencias('Não consegui carregar as pendências.');
      setPendencias([]);
    }
  }, [ehAuxiliarDeCobranca]);

  useEffect(() => { carregarPendencias(); }, [carregarPendencias]);

  /**
   * As duas decisões humanas da fila.
   *
   * Elas não enviam nada: `encaminhado` carimba quem repassou e quando;
   * `liberar` devolve a parcela ao estado que a próxima execução pode
   * reclamar, e por isso exige motivo escrito.
   */
  const decidirPendencia = async (
    item: PendenciaDaCobranca,
    acao: 'encaminhado' | 'liberar',
  ) => {
    const motivo = (motivoDaLiberacao[item.id] || '').trim();
    if (acao === 'liberar' && !motivo) {
      setErroPendencias('Escreva o motivo da liberação — ele fica registrado junto com a parcela.');
      return;
    }
    if (acao === 'liberar' && !confirm(
      'Liberar esta parcela para ser cobrada de novo?\n\n'
      + 'A próxima execução da rotina vai tentar entregá-la outra vez.',
    )) return;
    setAgindoNaPendencia(item.id);
    setErroPendencias('');
    try {
      const res = await fetch(`/api/dashboard/auxiliaries/cobranca/${acao}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: item.id, ...(motivo ? { motivo } : {}) }),
      });
      const j = await res.json().catch(() => ({}));
      if (!res.ok || !j?.ok) {
        setErroPendencias(j?.error || 'Não foi possível concluir a ação.');
      } else {
        setMotivoDaLiberacao((m) => ({ ...m, [item.id]: '' }));
      }
    } catch {
      setErroPendencias('Falha de conexão.');
    }
    setAgindoNaPendencia('');
    carregarPendencias();
  };

  /**
   * O modelo de rotina deste Auxiliar, carregado uma vez.
   *
   * 🔴 SPEC-078 C.4 — o `?auxiliar=` da URL sumiu, e é uma boa notícia: o
   * componente vive DENTRO da tela do Auxiliar, então ele já sabe de quem é.
   * A pergunta que a URL respondia ("de qual Auxiliar é esta tela?") deixou de
   * existir junto com a lista solta.
   *
   * Resolver o modelo pelo `kind` e não pelo uuid é o que faz isto sobreviver a
   * um reseed do template — uuid novo, mesmo `kind`.
   */
  const carregarModelo = useCallback(async (): Promise<ModeloDeRotina | null> => {
    const kind = ROTINA_DO_AUXILIAR[auxiliarSlug];
    if (!kind) return null;
    try {
      const res = await fetch('/api/dashboard/routine-templates', { cache: 'no-store' });
      const j = await res.json();
      const lista = (j.templates || []) as ModeloDeRotina[];
      return lista.find((x) => String(x.config_default?.kind || '') === kind) || null;
    } catch {
      return null; // o corretor ainda pode criar do zero
    }
  }, [auxiliarSlug]);

  const act = async (id: string, action: 'pause' | 'activate' | 'delete') => {
    if (action === 'delete' && !confirm('Excluir esta rotina? O histórico de execuções também será removido.')) return;
    setNotice('');
    const res = await fetch('/api/dashboard/rotinas', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id, action }),
    });
    if (!res.ok) {
      const j = await res.json().catch(() => ({}));
      setNotice(j.error || 'Não foi possível concluir a ação.');
    }
    load();
  };

  return (
    <div>
      <div className="space-y-4">
        {/* 🔴 SPEC-078 A.3 — o aviso que fecha o buraco que o Founder viu.
            Rotina ativa com Auxiliar desligado NÃO roda mais (o motor consulta
            `tenant_auxiliaries.status`). Antes disso rodava, e a tela não dizia
            nada — ele criou a rotina, desligou o Auxiliar e a varredura de
            portal aconteceria mesmo assim. Dizer isso aqui é o que impede o
            corretor de achar que configurou e esperar sentado. */}
        {!auxiliarLigado && (routines?.length ?? 0) > 0 && (
          <p className="rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-600 dark:text-amber-400">
            Este Auxiliar está <strong>desligado</strong>. Enquanto estiver, nenhuma
            rotina dele roda — nem as que aparecem como ativas abaixo. Ligue o Auxiliar
            para que ele volte a trabalhar.
          </p>
        )}

        <div className="flex flex-wrap items-center justify-between gap-3">
          {notice ? <p className="text-sm text-danger">{notice}</p> : <span />}
          <div className="flex shrink-0 flex-wrap items-center gap-2">
            {/* 🔴 SPEC-078 E.4 — a dedup é PERMANENTE e não tinha desfazer.
                📊 Chave `(company_id, recibo, send_mode)`, sem janela, sem
                expurgo. É o comportamento certo em produção — o segurado não
                pode receber o mesmo boleto duas vezes — e tornava o teste um
                tiro só: para repetir, era preciso apagar linha à mão no banco.
                O botão limpa APENAS `send_mode='test'`. Nunca `live`. */}
            {ROTINA_DO_AUXILIAR[auxiliarSlug] === BILLING_KIND && (
              <button
                onClick={liberarReenvioDeTeste}
                disabled={liberando}
                className="inline-flex items-center gap-1.5 rounded-md border border-border bg-surface-2 px-3 py-2 text-xs text-muted-foreground transition-colors hover:border-primary/40 disabled:opacity-50"
                title="Permite que os boletos já enviados em teste sejam enviados de novo. Não afeta envios reais."
              >
                {liberando && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                Liberar reenvio dos boletos de teste
              </button>
            )}
            <button
              onClick={() => openEditor('new')}
              className="inline-flex shrink-0 items-center gap-1.5 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
            >
              <Plus className="h-4 w-4" /> Nova rotina deste Auxiliar
            </button>
          </div>
        </div>

        {routines === null ? (
          <div className="flex items-center gap-2 py-8 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Carregando rotinas…
          </div>
        ) : routines.length === 0 ? (
          <div className="rounded-xl border border-border bg-surface p-8 text-center">
            <p className="text-sm font-medium text-foreground">Nenhuma rotina ainda</p>
            <p className="mx-auto mt-1 max-w-md text-xs text-muted-foreground">
              Abra o chat AutoBrokers e peça, por exemplo: &quot;Crie uma rotina que todo dia às 8h
              me mande no WhatsApp um resumo das notícias de seguros&quot;. Ela aparece aqui.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {routines.map((r) => {
              const rRuns = runs.filter((x) => x.routine_id === r.id).slice(0, 3);
              return (
                <div key={r.id} className="rounded-xl border border-border bg-surface p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="text-sm font-semibold text-foreground">{r.name}</p>
                        <StatusPill
                          tone={r.is_active ? 'success' : 'neutral'}
                          label={r.is_active ? 'ativa' : 'pausada'}
                        />
                        {r.consecutive_failures >= 5 && (
                          <StatusPill tone="danger" label="desativada por falhas" />
                        )}
                      </div>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {scheduleLabel(r.schedule)} · entrega: {r.delivery?.channel || 'histórico'}
                        {r.delivery?.number ? ` (${r.delivery.number})` : ''} · próxima: {fmt(r.next_run_at)} · última: {fmt(r.last_run_at)}
                      </p>
                      <p className="mt-2 line-clamp-2 text-xs text-muted-foreground">{r.instructions}</p>
                    </div>
                    <div className="flex shrink-0 items-center gap-1.5">
                      <button
                        onClick={() => openEditor(r)}
                        className="rounded-md border border-border bg-surface-2 p-2 text-muted-foreground transition-colors hover:text-foreground"
                        title="Editar rotina"
                      >
                        <Pencil className="h-3.5 w-3.5" />
                      </button>
                      {r.is_active ? (
                        <button
                          onClick={() => act(r.id, 'pause')}
                          className="rounded-md border border-border bg-surface-2 p-2 text-muted-foreground transition-colors hover:text-foreground"
                          title="Pausar rotina"
                        >
                          <Pause className="h-3.5 w-3.5" />
                        </button>
                      ) : (
                        <button
                          onClick={() => act(r.id, 'activate')}
                          className="rounded-md border border-border bg-surface-2 p-2 text-muted-foreground transition-colors hover:text-foreground"
                          title="Reativar rotina"
                        >
                          <Play className="h-3.5 w-3.5" />
                        </button>
                      )}
                      <button
                        onClick={() => act(r.id, 'delete')}
                        className="rounded-md border border-border bg-surface-2 p-2 text-muted-foreground transition-colors hover:text-danger"
                        title="Excluir rotina"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                  {rRuns.length > 0 && (
                    <div className="mt-3 space-y-1 border-t border-border pt-2">
                      {rRuns.map((run) => (
                        <p key={run.id} className="truncate text-[11px] text-muted-foreground">
                          <span className={run.status === 'ok' ? 'text-success' : run.status === 'error' ? 'text-danger' : ''}>
                            {run.status === 'ok' ? '✓' : run.status === 'error' ? '✗' : '…'}
                          </span>{' '}
                          {fmt(run.started_at)} · {run.error || run.output_preview || 'executando…'}
                        </p>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* 🔴 SPEC-EXTRA-001 §6 — PENDÊNCIAS DA COBRANÇA.
            A fila do que a cobrança real deixou esperando decisão de gente.
            Ela vive FORA do modal de propósito: o modal é onde se configura, e
            isto é trabalho do dia. Só aparece no Auxiliar de Cobrança — em
            qualquer outro não existe ledger para ler. */}
        {ehAuxiliarDeCobranca && (
          <div className="rounded-xl border border-border bg-surface p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-sm font-semibold text-foreground">Pendências da cobrança</p>
              <p className="text-[11px] text-faint">
                O que já saiu e ainda espera alguém. Envios em teste não aparecem aqui.
              </p>
            </div>

            {erroPendencias && (
              <p className="mt-3 rounded-md border border-danger/40 bg-danger/10 px-3 py-2 text-xs text-danger">
                {erroPendencias}
              </p>
            )}

            {pendencias === null ? (
              <div className="flex items-center gap-2 py-6 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" /> Carregando pendências…
              </div>
            ) : pendencias.length === 0 ? (
              <p className="mt-3 text-xs text-muted-foreground">
                Nenhuma pendência. Tudo que saiu já foi resolvido.
              </p>
            ) : (
              <div className="mt-3 space-y-2">
                {pendencias.map((p) => {
                  const bloqueio = NAO_LIBERA[p.status];
                  const ocupado = agindoNaPendencia === p.id;
                  return (
                    <div key={p.id} className="rounded-lg border border-border bg-surface-2 p-3">
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <div className="min-w-0">
                          <p className="text-[13px] font-medium text-foreground">
                            {p.cliente_nome || 'Cliente sem nome no portal'}
                          </p>
                          <p className="mt-0.5 text-[11px] text-muted-foreground">
                            {nomeDaSeguradora(String(p.portal_key || ''))}
                            {p.recibo ? ` · parcela/recibo ${p.recibo}` : ''}
                            {/* ⛔ O telefone NUNCA aparece inteiro — só os
                                últimos 4 dígitos (CLAUDE.md §7). Eles bastam
                                para a atendente reconhecer o contato que ela
                                já tem na mão. */}
                            {p.to_last4 ? ` · para …${p.to_last4}` : ''}
                            {' · '}{fmt(p.sent_at || p.updated_at)}
                          </p>
                        </div>
                        <StatusPill
                          tone={
                            p.status === 'entregue_equipe' ? 'warning'
                              : p.status === 'suprimido' || p.status === 'falhou' ? 'danger'
                                : 'neutral'
                          }
                          label={situacaoEmPortugues(p)}
                        />
                      </div>

                      {p.motivo && (
                        <p className="mt-1.5 text-[11px] text-muted-foreground">Observação: {p.motivo}</p>
                      )}

                      <div className="mt-2 flex flex-wrap items-center gap-2">
                        {p.status === 'entregue_equipe' && (
                          <button
                            onClick={() => decidirPendencia(p, 'encaminhado')}
                            disabled={ocupado}
                            className="inline-flex items-center gap-1.5 rounded-md border border-border bg-surface px-2.5 py-1.5 text-[11px] text-foreground transition-colors hover:border-primary/40 disabled:opacity-50"
                          >
                            {ocupado && <Loader2 className="h-3 w-3 animate-spin" />}
                            Marcar como encaminhado ao cliente
                          </button>
                        )}
                        <input
                          value={motivoDaLiberacao[p.id] || ''}
                          onChange={(e) => setMotivoDaLiberacao((m) => ({ ...m, [p.id]: e.target.value }))}
                          disabled={!!bloqueio || ocupado}
                          placeholder="Motivo da liberação"
                          className="min-w-[10rem] flex-1 rounded-md border border-border bg-surface px-2.5 py-1.5 text-[11px] text-foreground outline-none disabled:opacity-50"
                        />
                        <button
                          onClick={() => decidirPendencia(p, 'liberar')}
                          disabled={!!bloqueio || ocupado || !(motivoDaLiberacao[p.id] || '').trim()}
                          className="inline-flex items-center gap-1.5 rounded-md border border-border bg-surface px-2.5 py-1.5 text-[11px] text-foreground transition-colors hover:border-primary/40 disabled:opacity-50"
                        >
                          {ocupado && <Loader2 className="h-3 w-3 animate-spin" />}
                          Liberar reenvio
                        </button>
                        {/* O porquê fica AO LADO do botão desabilitado. Um
                            controle apagado sem explicação é um controle que a
                            pessoa tenta de novo amanhã. */}
                        {bloqueio && <span className="text-[11px] text-muted-foreground">{bloqueio}</span>}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {editing !== null && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={() => !saving && setEditing(null)}>
            <div
              className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-xl border border-border bg-surface p-5"
              onClick={(e) => e.stopPropagation()}
            >
              <h2 className="text-base font-semibold text-foreground">
                {editing === 'new' ? `Nova rotina · ${auxiliarNome}` : `Editar rotina · ${auxiliarNome}`}
              </h2>

              {/* 🔴 SPEC-078 D.5 — o erro mora DENTRO do modal. */}
              {erroDoModal && (
                <p className="mt-3 rounded-md border border-danger/40 bg-danger/10 px-3 py-2 text-xs text-danger">
                  {erroDoModal}
                </p>
              )}

              <div className="mt-4 space-y-3 text-sm">
                {/* 🔴 SPEC-078 D.1 — o NOME é o do Auxiliar, e é fixo.
                    📊 `routines.name` é rótulo em runtime (só aparece no título
                    do relatório); nenhum código casa por ele. Deixá-lo editável
                    convidava a chamar a rotina de outra coisa que não o Auxiliar
                    dono — a confusão Auxiliar × Rotina na primeira linha do
                    formulário. */}
                <div>
                  <label className="mb-1 block text-xs font-medium text-muted-foreground">Rotina de</label>
                  <p className="rounded-md border border-border bg-surface-3 px-3 py-2 text-foreground">
                    {auxiliarNome}
                  </p>
                </div>

                {/* 🔴 SPEC-078 D.2 — "O que fazer" vira LEITURA quando o
                    Auxiliar tem motor próprio.

                    📊 Medido: em rotina de cobrança este texto é INERTE.
                    `routine_engine.py:224` desvia para o motor determinístico
                    ANTES de chegar ao prompt, e `instructions` tem ZERO
                    ocorrências em `billing_collection.py`. O campo era
                    obrigatório (mínimo 10 caracteres) e não fazia nada — o pior
                    tipo de campo, porque ensina o corretor a acreditar que
                    instruiu o robô.

                    Em rotina genérica (que roda por LLM) ele funciona de
                    verdade e continua editável. */}
                <div>
                  <label className="mb-1 block text-xs font-medium text-muted-foreground">
                    O que este Auxiliar faz em cada execução
                  </label>
                  {billingConfig ? (
                    <>
                      <p className="whitespace-pre-wrap rounded-md border border-border bg-surface-3 px-3 py-2 text-[13px] leading-relaxed text-muted-foreground">
                        {form.instructions || 'Varre os portais das seguradoras selecionadas, encontra os inadimplentes, baixa os boletos disponíveis e monta o relatório.'}
                      </p>
                      <p className="mt-1 text-[11px] text-faint">
                        Isto é o que o Auxiliar faz, e não muda. O que você
                        personaliza abaixo é <strong>quando</strong> ele roda e{' '}
                        <strong>como</strong> ele fala.
                      </p>
                    </>
                  ) : (
                    <textarea
                      value={form.instructions}
                      onChange={(e) => setForm({ ...form, instructions: e.target.value })}
                      rows={4}
                      placeholder="Descreva a tarefa completa, como se instruísse um assistente…"
                      className="w-full resize-y rounded-md border border-border bg-surface-2 px-3 py-2 text-foreground outline-none focus:ring-2 focus:ring-ring"
                    />
                  )}
                </div>

                {/* 🔴 SPEC-078 D.3 — "Conhecimento" SOME da cobrança.
                    📊 Ele só é lido em `render_task_prompt`, que rotina de
                    cobrança nunca alcança. Em cobrança não existe LLM onde
                    injetar conhecimento: o motor enfileira job de portal, faz
                    polling e formata relatório determinístico. Em rotina
                    genérica ele tem função real e continua aqui. */}
                {!billingConfig && (
                  <div>
                    <label className="mb-1 block text-xs font-medium text-muted-foreground">Conhecimento (opcional) — usado em toda execução (argumentos, FAQ, tom de voz)</label>
                    <textarea
                      value={form.knowledge}
                      onChange={(e) => setForm({ ...form, knowledge: e.target.value })}
                      rows={3}
                      placeholder="Ex.: argumentos de venda, objeções comuns, FAQ do produto, tom de voz do outreach…"
                      className="w-full resize-y rounded-md border border-border bg-surface-2 px-3 py-2 text-foreground outline-none focus:ring-2 focus:ring-ring"
                    />
                  </div>
                )}
                {billingConfig && (
                  <div className="space-y-3 rounded-lg border border-border bg-surface-2 p-3">
                    <div>
                      <label className="mb-1 block text-xs font-medium text-muted-foreground">
                        Seguradoras varridas
                      </label>
                      {cobrancaDegradada && (
                        <p className="mb-2 rounded-md border border-amber-500/40 bg-amber-500/10 px-2 py-1.5 text-[11px] text-amber-600 dark:text-amber-400">
                          Não foi possível confirmar quais seguradoras estão automatizadas
                          no serviço em execução. Nenhuma aparece como pronta até a
                          confirmação — isto é proposital: marcar como pronta sem conferir
                          é o que faz um job morrer em produção.
                        </p>
                      )}
                      {portais.length === 0 ? (
                        <p className="text-[11px] text-muted-foreground">
                          Nenhum portal conectado ainda. Conecte em Personalização → Conectores → Portais.
                        </p>
                      ) : (
                        <div className="grid gap-1.5 sm:grid-cols-2">
                          {portais.map((p) => {
                            const disponivel = p.conectado && p.automatizado;
                            return (
                              <label
                                key={p.key}
                                className={`inline-flex items-start gap-2 text-xs ${disponivel ? 'text-foreground' : 'text-faint'}`}
                                title={
                                  !p.conectado
                                    ? 'Sem login e senha desta corretora neste portal'
                                    : !p.automatizado
                                      ? 'A cobrança automática desta seguradora ainda não foi construída'
                                      : undefined
                                }
                              >
                                <input
                                  type="checkbox"
                                  className="mt-0.5"
                                  disabled={!disponivel}
                                  checked={disponivel && billingPortalKeys.includes(p.key)}
                                  onChange={(e) => alternarPortal(p.key, e.target.checked)}
                                />
                                <span>
                                  {p.name}
                                  {!p.conectado && <span className="block text-[10px]">sem credencial</span>}
                                  {p.conectado && !p.automatizado && (
                                    <span className="block text-[10px]">em breve</span>
                                  )}
                                </span>
                              </label>
                            );
                          })}
                        </div>
                      )}
                      <p className="mt-1.5 text-[11px] text-muted-foreground">
                        Marque quantas quiser. A rotina varre uma por vez e junta tudo num relatório só.
                      </p>
                    </div>
                    {/* 🔴 SPEC-078 E.1 e E.2 — o seletor para de prometer.
                        "Aprovação" saiu inteiro: 📊 é enfeite nos QUATRO modos
                        (em `live`, seu único efeito é decidir se nasce um
                        pedido que ninguém lê). E o modo de envio ficou com os
                        dois que têm motor. Ver `MODOS_COM_MOTOR`. */}
                    <div className="grid gap-3 sm:grid-cols-2">
                      <div>
                        <label className="mb-1 block text-xs font-medium text-muted-foreground">Modo de envio</label>
                        {/* 🔴 SPEC-EXTRA-001 — o seletor fica SEM valor quando a
                            config é legada. Pré-selecionar "Teste" esconderia o
                            problema (a pessoa salvaria sem escolher e acharia
                            que estava em teste); pré-selecionar "cliente"
                            ligaria envio real por conta própria. */}
                        <select
                          value={billingModoLegado ? '' : billingSendMode}
                          onChange={(e) => setBillingConfig({ send_mode: e.target.value })}
                          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-foreground outline-none"
                        >
                          {billingModoLegado && <option value="">Escolha uma modalidade…</option>}
                          {MODOS_COM_MOTOR.map((m) => (
                            <option key={m.valor} value={m.valor}>{m.rotulo}</option>
                          ))}
                        </select>
                        {billingModoLegado && (
                          <p className="mt-1 rounded-md border border-amber-500/40 bg-amber-500/10 px-2 py-1.5 text-[11px] text-amber-600 dark:text-amber-400">
                            Esta configuração é antiga e <strong>não envia nada</strong>.
                            Escolha uma modalidade.
                          </p>
                        )}
                      </div>
                      <div>
                        <label className="mb-1 block text-xs font-medium text-muted-foreground">
                          Máximo de boletos por execução
                        </label>
                        <input
                          type="number"
                          min={1}
                          max={50}
                          value={billingMaxBoletos}
                          onChange={(e) => setBillingConfig({ max_boletos_por_execucao: parseInt(e.target.value || '10', 10) })}
                          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-foreground outline-none"
                        />
                        <p className="mt-1 text-[11px] text-faint">
                          Para o primeiro teste, 1 ou 2. Quem não couber hoje volta
                          amanhã de onde parou.
                        </p>
                      </div>
                    </div>
                    {/* 🔴 SPEC-EXTRA-001.6 P0.4 — o nome que o segurado vai ler.
                        Sem ele, em Encaminhar/Enviar a rotina fica RETIDA (o motor
                        recusa — não é só a tela). Em Teste o default continua
                        "nossa equipe", porque o destino é a própria corretora. */}
                    <div>
                      <label className="mb-1 block text-xs font-medium text-muted-foreground">
                        Quem assina a mensagem
                      </label>
                      <input
                        value={billingAttendantName}
                        onChange={(e) => setBillingConfig({ attendant_name: e.target.value })}
                        placeholder="o primeiro nome de quem atende"
                        className="w-full rounded-md border border-border bg-surface px-3 py-2 text-foreground outline-none"
                      />
                      <p className="mt-1 text-[11px] leading-relaxed text-muted-foreground">
                        É o nome que o segurado vai ler: <em>"Aqui é a {billingAttendantName || '…'}, da sua corretora"</em>.
                        Use o nome de quem atende. Nos modos <strong>Encaminhar</strong> e{' '}
                        <strong>Enviar ao cliente</strong>, sem este nome nada sai.
                      </p>
                    </div>
                    {billingSendMode === 'test' && (
                      <div>
                        <label className="mb-1 block text-xs font-medium text-muted-foreground">
                          Número que recebe a simulação
                        </label>
                        {/* ⛔ Nunca um telefone real como placeholder. 📊 Aqui
                            havia um número de celular verdadeiro, e um exemplo
                            copiado sem pensar é gente recebendo cobrança de uma
                            corretora que não é a dela. A máscara mostra o
                            FORMATO, que é o que o campo precisa ensinar. */}
                        <input
                          value={billingTestNumber}
                          onChange={(e) => setBillingConfig({ test_number: e.target.value })}
                          placeholder="55 47 9XXXX-XXXX"
                          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-foreground outline-none"
                        />
                        <p className="mt-1 text-[11px] leading-relaxed text-muted-foreground">
                          Em Teste, o segurado <strong>nunca</strong> recebe nada. A mensagem e
                          o boleto vão só para este número.
                        </p>
                      </div>
                    )}

                    {/* 🔴 SPEC-EXTRA-001 §1 — o WhatsApp de quem recebe o pacote.
                        Em `equipe` nada sai para o segurado: o envio é interno,
                        para um número só, o da própria corretora. Quem repassa
                        é a atendente — e é por isso que existe a fila de
                        pendências abaixo. */}
                    {billingSendMode === 'equipe' && (
                      <div>
                        <label className="mb-1 block text-xs font-medium text-muted-foreground">
                          WhatsApp de quem recebe o pacote (sua equipe)
                        </label>
                        <input
                          value={billingTeamNumber}
                          onChange={(e) => setBillingConfig({ team_number: e.target.value })}
                          placeholder="55 47 9XXXX-XXXX"
                          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-foreground outline-none"
                        />
                        <p className="mt-1 text-[11px] leading-relaxed text-muted-foreground">
                          A atendente recebe a mensagem pronta e o boleto, e repassa ao
                          cliente. Depois de repassar, marque em <strong>Pendências da
                          cobrança</strong> — é assim que a parcela sai da fila.
                        </p>
                      </div>
                    )}

                    {/* 🔴 SPEC-EXTRA-001 §1 — a confirmação do envio direto.
                        Este é o único controle desta tela que faz um segurado
                        receber uma mensagem sem ninguém no meio. Um `<select>`
                        é fácil demais para uma decisão desse tamanho: a
                        confirmação é um ato separado, e o motor recusa sem ela
                        (`confirmacao_cliente`), não só a tela. */}
                    {billingSendMode === 'cliente' && (
                      <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-3">
                        <p className="text-[12px] leading-relaxed text-amber-700 dark:text-amber-300">
                          O cliente vai receber diretamente pelo WhatsApp da corretora.
                          Cada parcela é cobrada uma vez; a resposta dele chega ao
                          atendimento.
                        </p>
                        <label className="mt-2 inline-flex items-start gap-2 text-[12px] text-foreground">
                          <input
                            type="checkbox"
                            className="mt-0.5"
                            checked={billingConfirmacaoCliente}
                            onChange={(e) => setBillingConfig({ confirmacao_cliente: e.target.checked })}
                          />
                          <span>Entendi e confirmo o envio direto ao cliente.</span>
                        </label>
                      </div>
                    )}
                    <div>
                      <label className="mb-1 block text-xs font-medium text-muted-foreground">Mensagem ao cliente</label>
                      <textarea
                        value={textoDaMensagem}
                        onChange={(e) => setBillingConfig({ message_template: e.target.value })}
                        rows={5}
                        className="w-full resize-y rounded-md border border-border bg-surface px-3 py-2 font-mono text-[12px] text-foreground outline-none"
                      />
                      {/* 🔴 SPEC-078 D.7 — o campo abria VAZIO quando não havia
                          template salvo, então o corretor nunca via a mensagem
                          que ia sair. Agora ele começa com o padrão. */}
                      <p className="mt-1 text-[11px] text-faint">
                        Campos disponíveis: {CHAVES_DA_MENSAGEM.join(' · ')}
                      </p>
                      {chavesDesconhecidas.length > 0 && (
                        <p className="mt-1 rounded-md border border-amber-500/40 bg-amber-500/10 px-2 py-1.5 text-[11px] text-amber-600 dark:text-amber-400">
                          Estes campos não existem e vão sair <strong>em branco</strong> na
                          mensagem: {chavesDesconhecidas.join(', ')}
                        </p>
                      )}
                    </div>

                    {/* 🔴 SPEC-078 E.3 — a mensagem EXATA que o segurado leria.
                        Em modo teste o que chega no celular leva prefixo
                        "[TESTE AutoBrokers…]" e duas linhas de aviso — e isso
                        FICA, porque mandar em teste algo indistinguível do real
                        é como o produto acaba mandando o real achando que é
                        teste. A pré-visualização resolve o outro lado: o
                        corretor confere o texto verdadeiro sem que a mensagem
                        de teste minta sobre o que é. */}
                    <details className="rounded-lg border border-border bg-surface p-3">
                      <summary className="cursor-pointer text-xs font-medium text-foreground">
                        Ver como o segurado vai ler
                      </summary>
                      <p className="mt-2 whitespace-pre-wrap rounded-md bg-surface-3 px-3 py-2 text-[13px] leading-relaxed text-foreground">
                        {previaDaMensagem}
                      </p>
                      <p className="mt-1 text-[11px] text-faint">
                        Exemplo com dados fictícios. Em modo Teste a mensagem chega ao
                        seu número com um cabeçalho identificando que é simulação.
                      </p>
                    </details>
                  </div>
                )}
                <div className="flex gap-2">
                  {(['daily', 'interval'] as const).map((k) => (
                    <button
                      key={k}
                      onClick={() => setForm({ ...form, kind: k })}
                      className={`rounded-md border px-3 py-1.5 text-xs font-medium transition-colors ${form.kind === k ? 'border-primary/60 bg-brand-soft text-foreground' : 'border-border bg-surface-2 text-muted-foreground'}`}
                    >
                      {k === 'daily' ? 'Diária (horário fixo)' : 'A cada N minutos'}
                    </button>
                  ))}
                </div>
                {form.kind === 'daily' ? (
                  <div className="flex gap-3">
                    <div>
                      <label className="mb-1 block text-xs font-medium text-muted-foreground">Horário (Brasília)</label>
                      <input
                        type="time"
                        value={form.time}
                        onChange={(e) => setForm({ ...form, time: e.target.value })}
                        className="rounded-md border border-border bg-surface-2 px-3 py-2 text-foreground outline-none [color-scheme:dark]"
                      />
                    </div>
                    {/* 🔴 SPEC-078 D.6 — caixa de texto vira seletor.
                        A legenda "0=seg … 6=dom" estava CERTA (convenção do
                        `datetime.weekday()`, confirmada em três lugares do
                        motor). Mas decorar isso para agendar uma cobrança é um
                        detalhe nosso empurrado para o corretor. */}
                    <div className="flex-1">
                      <label className="mb-1 block text-xs font-medium text-muted-foreground">Dias da semana</label>
                      <div className="flex flex-wrap gap-1.5">
                        {DIAS_DA_SEMANA.map((d) => {
                          const marcados = form.weekdays.split(',').map((x) => x.trim()).filter(Boolean);
                          const ativo = marcados.includes(String(d.valor));
                          return (
                            <button
                              key={d.valor}
                              type="button"
                              title={d.longo}
                              onClick={() => {
                                const sem = marcados.filter((x) => x !== String(d.valor));
                                const novos = ativo ? sem : [...sem, String(d.valor)];
                                setForm({
                                  ...form,
                                  weekdays: novos.sort((a, b) => Number(a) - Number(b)).join(','),
                                });
                              }}
                              className={`rounded-md border px-2.5 py-1.5 text-xs font-medium transition-colors ${
                                ativo
                                  ? 'border-primary/60 bg-brand-soft text-foreground'
                                  : 'border-border bg-surface-2 text-muted-foreground hover:border-primary/40'
                              }`}
                            >
                              {d.curto}
                            </button>
                          );
                        })}
                      </div>
                      <p className="mt-1 text-[11px] text-faint">
                        {form.weekdays.trim()
                          ? 'Roda só nos dias marcados.'
                          : 'Nenhum dia marcado — vai rodar TODOS os dias, inclusive sábado e domingo.'}
                      </p>
                    </div>
                  </div>
                ) : (
                  <div>
                    <label className="mb-1 block text-xs font-medium text-muted-foreground">Intervalo (minutos, mín. 5)</label>
                    <input
                      type="number"
                      min={5}
                      value={form.minutes}
                      onChange={(e) => setForm({ ...form, minutes: parseInt(e.target.value || '5', 10) })}
                      className="w-32 rounded-md border border-border bg-surface-2 px-3 py-2 text-foreground outline-none"
                    />
                  </div>
                )}
                <div className="flex gap-3">
                  <div>
                    <label className="mb-1 block text-xs font-medium text-muted-foreground">{billingConfig ? 'Relatorio da rotina' : 'Entrega'}</label>
                    <div className="flex gap-2">
                      {(['whatsapp', 'none'] as const).map((c) => (
                        <button
                          key={c}
                          onClick={() => setForm({ ...form, channel: c })}
                          className={`rounded-md border px-3 py-1.5 text-xs font-medium transition-colors ${form.channel === c ? 'border-primary/60 bg-brand-soft text-foreground' : 'border-border bg-surface-2 text-muted-foreground'}`}
                        >
                          {c === 'whatsapp' ? 'WhatsApp' : 'Só histórico'}
                        </button>
                      ))}
                    </div>
                  </div>
                  {form.channel === 'whatsapp' && (
                    <div className="flex-1">
                      <label className="mb-1 block text-xs font-medium text-muted-foreground">{billingConfig ? 'Numero que recebe o relatorio' : 'Numero (DDI+DDD+numero)'}</label>
                      <input
                        value={form.number}
                        onChange={(e) => setForm({ ...form, number: e.target.value })}
                        placeholder="55 47 9XXXX-XXXX"
                        className="w-full rounded-md border border-border bg-surface-2 px-3 py-2 text-foreground outline-none"
                      />
                    </div>
                  )}
                </div>
              </div>
              <div className="mt-5 flex justify-end gap-2">
                <button
                  onClick={() => { setEditing(null); setErroDoModal(''); }}
                  disabled={saving}
                  className="rounded-md border border-border bg-surface-2 px-4 py-2 text-sm text-foreground"
                >
                  Cancelar
                </button>
                <button
                  onClick={saveRoutine}
                  // 🔴 SPEC-078 D.5 — o botão passa a exigir o que o servidor
                  // exige. 📊 Ele ficava clicável com o número de WhatsApp
                  // vazio, e a única barreira era um 400 que o corretor não via
                  // (renderizado atrás do overlay). Travar aqui evita a viagem.
                  //
                  // E `instructions` deixa de ser exigido em Auxiliar com motor
                  // próprio: 📊 o campo é inerte lá (D.2), então exigir 10
                  // caracteres de um texto que ninguém lê era pedágio.
                  disabled={!!(
                    saving
                    || form.name.trim().length < 3
                    || (!billingConfig && form.instructions.trim().length < 10)
                    || (form.channel === 'whatsapp' && form.number.replace(/\D/g, '').length < 10)
                    || (billingConfig && billingSendMode === 'test'
                        && billingTestNumber.replace(/\D/g, '').length < 10
                        && form.number.replace(/\D/g, '').length < 10)
                    // 🔴 SPEC-EXTRA-001 — as condições dos modos REAIS.
                    // A rota confere as mesmas (o botão é cortesia, a rota é a
                    // barreira); travar aqui evita a viagem até o 400.
                    || (billingConfig && billingModoLegado)
                    || (billingConfig && billingSendMode === 'equipe'
                        && (billingTeamDigitos.length < 10 || billingTeamDigitos.length > 13))
                    || (billingConfig && billingSendMode === 'cliente' && !billingConfirmacaoCliente)
                  )}
                  className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50"
                >
                  {saving && <Loader2 className="h-4 w-4 animate-spin" />}
                  {editing === 'new' ? 'Criar rotina' : 'Salvar alterações'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
