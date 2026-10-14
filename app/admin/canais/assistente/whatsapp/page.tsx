'use client';

// SPEC-132-C C3 — Canais → AutoBrokers (assistente dos corretores) → WhatsApp.
//
// O MESMO cartão do QR do Quem Cobra Menos (`WhatsAppChannelCard` + pareamento),
// apontado para `/api/admin/canais/assistente/whatsapp`: a rota acha a empresa da
// plataforma no banco pelo tipo `platform_canal`, só abre para administrador da
// plataforma e pareia com o `purpose='assistente'` — outro número, outro QR,
// outra instância. O número do Quem Cobra Menos não muda.

import { useEffect, useState } from 'react';
import { MessageCircle, ShieldAlert } from 'lucide-react';

import { WhatsAppChannelCard } from '@/components/vault/WhatsAppChannelCard';

const ENDPOINT_DO_ASSISTENTE = '/api/admin/canais/assistente/whatsapp';

// O que a rota pode devolver ANTES de falar com o WhatsApp, em português de gente.
const MOTIVOS: Record<string, string> = {
  canal_nao_cadastrado:
    'A empresa da plataforma ainda não existe no banco (nenhuma empresa do tipo "canal da plataforma"). Cadastre-a antes de ler o QR.',
  canal_ambiguo:
    'Há mais de uma empresa do tipo "canal da plataforma" no banco. Deixe só uma — o QR não é gerado enquanto houver dúvida de onde ele vai parar.',
  canal_indisponivel: 'Não consegui consultar o banco agora. Tente de novo em alguns segundos.',
  no_admin_session: 'Sua sessão de administrador expirou. Entre de novo.',
  master_required: 'Só o administrador da plataforma pode conectar o número do assistente dos corretores.',
  admin_revoked: 'Seu acesso de administrador foi retirado.',
};

export default function AssistenteDosCorretoresWhatsAppPage() {
  const [motivo, setMotivo] = useState('');

  useEffect(() => {
    let vivo = true;
    fetch(`${ENDPOINT_DO_ASSISTENTE}?action=status`, { cache: 'no-store' })
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
        <p className="mb-1 text-xs uppercase tracking-wide text-muted-foreground">Canais · AutoBrokers</p>
        <h1 className="mb-2 flex items-center gap-3 text-2xl font-bold text-foreground sm:text-3xl">
          <MessageCircle className="h-7 w-7" /> AutoBrokers — assistente dos corretores
        </h1>
        <p className="text-sm text-muted-foreground">
          Leia este QR com o WhatsApp do número do AutoBrokers (WhatsApp → Aparelhos conectados → Conectar aparelho).
          Use um número só para isto: não o do Quem Cobra Menos nem o de atendimento de uma corretora.
        </p>
      </div>

      <div className="mb-6 flex items-start gap-2 rounded-lg border border-amber-500/40 bg-amber-500/5 px-4 py-3 text-sm text-amber-700 dark:text-amber-400">
        <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />
        <span>
          Este número só conversa com corretores que confirmaram o próprio WhatsApp em Meu perfil. Quem não confirmou
          manda mensagem e não recebe resposta nenhuma.
        </span>
      </div>

      {motivo && (
        <p className="mb-4 rounded-lg border border-destructive/40 bg-surface-2 px-4 py-3 text-sm text-foreground">{motivo}</p>
      )}

      <WhatsAppChannelCard
        endpoint={ENDPOINT_DO_ASSISTENTE}
        titulo="WhatsApp do AutoBrokers (assistente dos corretores)"
        descricao="O número com que cada corretor conversa pelo celular dele, como conversa com o chat do painel."
        comAutorizacaoDeAuxiliar={false}
      />
    </div>
  );
}
