'use client';

// SPEC-133-A F4 (D-133A-10) — Canais → Quem Cobra Menos → WhatsApp.
//
// O MESMO cartão do hub das corretoras (`WhatsAppChannelCard` + pareamento),
// apontado para `/api/admin/canais/whatsapp`: a rota descobre a empresa do canal
// no banco pelo tipo `platform_canal` e só abre para administrador da plataforma.

import { useEffect, useState } from 'react';
import { MessageCircle, ShieldAlert } from 'lucide-react';

import { WhatsAppChannelCard } from '@/components/vault/WhatsAppChannelCard';

const ENDPOINT_DO_CANAL = '/api/admin/canais/whatsapp';

// O que a rota pode devolver ANTES de falar com o WhatsApp, em português de gente.
const MOTIVOS: Record<string, string> = {
  canal_nao_cadastrado:
    'A empresa do Quem Cobra Menos ainda não existe no banco (nenhuma empresa do tipo "canal da plataforma"). Cadastre-a antes de ler o QR.',
  canal_ambiguo:
    'Há mais de uma empresa do tipo "canal da plataforma" no banco. Deixe só uma — o QR não é gerado enquanto houver dúvida de onde ele vai parar.',
  canal_indisponivel: 'Não consegui consultar o banco agora. Tente de novo em alguns segundos.',
  no_admin_session: 'Sua sessão de administrador expirou. Entre de novo.',
  master_required: 'Só o administrador da plataforma pode conectar o número do Quem Cobra Menos.',
  admin_revoked: 'Seu acesso de administrador foi retirado.',
};

export default function QuemCobraMenosWhatsAppPage() {
  const [motivo, setMotivo] = useState('');

  useEffect(() => {
    let vivo = true;
    fetch(`${ENDPOINT_DO_CANAL}?action=status`, { cache: 'no-store' })
      .then((res) => res.json().catch(() => ({})))
      .then((json: { detail?: string }) => {
        if (vivo && json?.detail && MOTIVOS[json.detail]) setMotivo(MOTIVOS[json.detail]);
      })
      .catch(() => {});
    return () => {
      vivo = false;
    };
  }, []);

  return (
    <div className="mx-auto max-w-3xl p-4 sm:p-8">
      <div className="mb-6">
        <p className="mb-1 text-xs uppercase tracking-wide text-muted-foreground">Canais · Quem Cobra Menos</p>
        <h1 className="mb-2 flex items-center gap-3 text-2xl font-bold text-foreground sm:text-3xl">
          <MessageCircle className="h-7 w-7" /> WhatsApp do Quem Cobra Menos
        </h1>
        <p className="text-sm text-muted-foreground">
          Leia este QR com o WhatsApp do número do Quem Cobra Menos (WhatsApp → Aparelhos conectados → Conectar
          aparelho).
        </p>
      </div>

      <div className="mb-6 flex items-start gap-2 rounded-lg border border-amber-500/40 bg-amber-500/5 px-4 py-3 text-sm text-amber-700 dark:text-amber-400">
        <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />
        <span>
          Este número só responde a números convidados. Quem não estiver na lista de convidados manda mensagem e não
          recebe resposta nenhuma.
        </span>
      </div>

      {motivo && (
        <p className="mb-4 rounded-lg border border-destructive/40 bg-surface-2 px-4 py-3 text-sm text-foreground">{motivo}</p>
      )}

      <WhatsAppChannelCard
        endpoint={ENDPOINT_DO_CANAL}
        titulo="WhatsApp do Quem Cobra Menos"
        descricao="O número que conversa com os convidados e devolve a cotação das corretoras parceiras."
        comAutorizacaoDeAuxiliar={false}
      />
    </div>
  );
}
