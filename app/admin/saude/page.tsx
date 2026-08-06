'use client';

/**
 * Saúde do sistema — a tela que responde "o deploy entrou?".
 *
 * 06/08/2026: depois de um conserto, não havia como confirmar de fora se ele
 * tinha subido. A resposta existia no `/health` do backend, mas exigia montar
 * uma URL à mão e ler JSON cru. Informação que só o autor consegue ler não é
 * observabilidade.
 *
 * Cada linha é uma PEÇA de código que nasceu num commit datado, com a frase que
 * explica o que ela protege. Verde = a peça está no ar.
 */

import { useCallback, useEffect, useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertCircle, CheckCircle2, RefreshCw, XCircle } from 'lucide-react';

interface Saude {
  ok: boolean;
  status?: string | null;
  infra?: Record<string, unknown>;
  sinais?: Record<string, unknown>;
  consultado_em?: string;
  error?: string;
}

/**
 * O que cada sinal PROTEGE, em português.
 *
 * Sinal sem explicação vira enfeite: quem lê "pii_cartao: true" às duas da manhã
 * não sabe se aquilo é bom. A frase é o que transforma um booleano em resposta.
 */
const EXPLICACAO: Record<string, string> = {
  qr_espera_nao_e_socorro:
    'Quando o WhatsApp pede "espere um momento", a tela diz para esperar — e não "chame o suporte".',
  create_repetido_nao_e_indisponivel:
    'Uma corretora que já tem canal não recebe mais "serviço indisponível" ao tentar parear.',
  connect_sem_webhook_recusado:
    'O sistema recusa religar um canal sem dizer para onde entregar as mensagens. Era isso que deixava a captura muda.',
  um_pareamento_por_corretora:
    'Um QR code serve o observador e o atendimento. Cobrança tem número separado.',
  alarme_de_canal_mudo:
    'Se uma corretora aparece conectada e passa 6 horas sem gravar conversa, abre um aviso sozinho.',
  espelho_no_chat:
    'A conversa capturada no WhatsApp chega ao chat da corretora, no dashboard.',
  acionamento_env_aberta:
    'O canal de acionamento das seguradoras está liberado por configuração.',
  midia_recuperavel: 'Áudios e imagens são gravados com o que é preciso para baixá-los depois.',
  midia_chave_escondida: 'E a chave de descriptografia da mídia nunca sai numa resposta de API.',
  conhecimento_sobrevive: 'O mascarador de dados pessoais não come o conhecimento das cartas.',
  pii_telefone_nao_vira_cpf: 'Um telefone anunciado como telefone não é mascarado como CPF.',
};

/**
 * Sinais em que `false` é o estado NORMAL, não um defeito.
 *
 * O freio de emergência existe para ser puxado num incidente; desarmado é o
 * dia a dia. Um painel que pinta isso de vermelho treina quem o lê a ignorar
 * vermelho — e aí o vermelho que importa passa despercebido.
 */
const FALSE_EH_NORMAL = new Set(['freio_de_emergencia_armado']);

const ROTULO_INFRA: Record<string, string> = {
  database_sync: 'Banco de dados',
  database_async: 'Banco de dados (assíncrono)',
  redis: 'Fila e cache (Redis)',
  qdrant: 'Busca semântica (Qdrant)',
  storage: 'Arquivos (MinIO)',
};

function Estado({ valor, falseEhBom = false }: { valor: unknown; falseEhBom?: boolean }) {
  // A infra não devolve string: vem `{conectado: true, host: "..."}`. Sem esta
  // leitura o painel mostrava `[object Object]` em Redis, Qdrant e MinIO —
  // três peças que estavam FUNCIONANDO e pareciam quebradas.
  if (valor && typeof valor === 'object') {
    const obj = valor as Record<string, unknown>;
    if ('conectado' in obj) return <Estado valor={Boolean(obj.conectado)} />;
  }
  // Nem todo `false` é defeito. O freio de emergência DESARMADO é o estado
  // normal — pintá-lo de vermelho ensina a pessoa a ignorar vermelho, que é
  // exatamente o que um painel de saúde não pode fazer.
  if (falseEhBom && valor === false) {
    return (
      <Badge className="gap-1 bg-emerald-600/15 text-emerald-500 hover:bg-emerald-600/15">
        <CheckCircle2 className="h-3 w-3" /> normal
      </Badge>
    );
  }
  if (valor === true || valor === 'ok' || valor === 'healthy' || valor === 'connected') {
    return (
      <Badge className="gap-1 bg-emerald-600/15 text-emerald-500 hover:bg-emerald-600/15">
        <CheckCircle2 className="h-3 w-3" /> ok
      </Badge>
    );
  }
  if (valor === false) {
    return (
      <Badge className="gap-1 bg-red-600/15 text-red-500 hover:bg-red-600/15">
        <XCircle className="h-3 w-3" /> não
      </Badge>
    );
  }
  if (valor === null || valor === undefined) {
    return (
      <Badge variant="outline" className="gap-1">
        <AlertCircle className="h-3 w-3" /> sem resposta
      </Badge>
    );
  }
  return <Badge variant="outline">{String(valor)}</Badge>;
}

export default function SaudePage() {
  const [dados, setDados] = useState<Saude | null>(null);
  const [carregando, setCarregando] = useState(true);

  const buscar = useCallback(async () => {
    setCarregando(true);
    try {
      const res = await fetch('/api/admin/saude', { cache: 'no-store' });
      setDados((await res.json()) as Saude);
    } catch {
      setDados({ ok: false, error: 'nao_consegui_consultar' });
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    void buscar();
  }, [buscar]);

  const sinais = (dados?.sinais ?? {}) as Record<string, unknown>;
  // Os sinais COM explicação vêm primeiro e na ordem da lista — são os que
  // respondem a uma pergunta que alguém realmente faz. O resto vem depois,
  // porque esconder um sinal seria decidir por quem lê.
  const explicados = Object.keys(EXPLICACAO).filter((k) => k in sinais);
  const demais = Object.keys(sinais)
    .filter((k) => !(k in EXPLICACAO) && k !== 'git_commit')
    .sort();

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">Saúde do sistema</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Cada linha é uma peça de código. Verde quer dizer que ela está no ar agora — é assim
            que se confirma se um deploy entrou, sem precisar acreditar em ninguém.
          </p>
        </div>
        <Button variant="outline" onClick={() => void buscar()} disabled={carregando}>
          <RefreshCw className={`mr-2 h-4 w-4 ${carregando ? 'animate-spin' : ''}`} />
          Atualizar
        </Button>
      </div>

      {dados && !dados.ok ? (
        <Card className="border-red-500/40">
          <CardContent className="flex items-center gap-3 p-4 text-sm">
            <XCircle className="h-5 w-5 text-red-500" />
            <span>
              Não consegui falar com o servidor ({dados.error ?? 'motivo desconhecido'}). Se isto
              persistir, o backend pode estar fora do ar.
            </span>
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Consertos e proteções no ar</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {explicados.length === 0 && !carregando ? (
            <p className="text-sm text-muted-foreground">
              Nenhum sinal conhecido chegou. Isso costuma significar que o backend está rodando uma
              versão anterior a estas proteções.
            </p>
          ) : null}
          {explicados.map((chave) => (
            <div
              key={chave}
              className="flex items-start justify-between gap-4 border-b border-border/50 pb-3 last:border-0 last:pb-0"
            >
              <p className="text-sm text-foreground-2">{EXPLICACAO[chave]}</p>
              <Estado valor={sinais[chave]} falseEhBom={FALSE_EH_NORMAL.has(chave)} />
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Infraestrutura</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {Object.entries(dados?.infra ?? {}).map(([chave, valor]) => (
            <div key={chave} className="flex items-center justify-between gap-4">
              <span className="text-sm text-foreground-2">{ROTULO_INFRA[chave] ?? chave}</span>
              <Estado valor={valor} />
            </div>
          ))}
        </CardContent>
      </Card>

      {demais.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Outros sinais</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-2 sm:grid-cols-2">
            {demais.map((chave) => (
              <div key={chave} className="flex items-center justify-between gap-3">
                <span className="font-mono text-xs text-muted-foreground">{chave}</span>
                <Estado valor={sinais[chave]} falseEhBom={FALSE_EH_NORMAL.has(chave)} />
              </div>
            ))}
          </CardContent>
        </Card>
      ) : null}

      {dados?.consultado_em ? (
        <p className="text-xs text-muted-foreground">
          Consultado em {new Date(dados.consultado_em).toLocaleString('pt-BR')}
        </p>
      ) : null}
    </div>
  );
}
