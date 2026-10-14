// SPEC-133-A F4 (D-133A-10) — o QR do Quem Cobra Menos no portal ADMIN.
//
// O MESMO contrato da rota do hub das corretoras (`app/api/dashboard/whatsapp-channel`):
//   GET  ?action=status | qr | pairing&attempt_id= | diagnostics
//   POST {action: pairing (method qr|phone) | retry | cancel | disconnect | set-alert}
// e o MESMO caminho até o provedor: `lib/vault/whatsapp-channel-proxy.ts` →
// `backend/app/api/whatsapp_channel.py` → `pairing_orchestrator.py`. Nenhum
// cliente do Evolution nasce aqui.
//
// O que muda são DUAS coisas, e só elas:
//   QUEM pode   → só administrador da PLATAFORMA (`requireMasterAdmin`, a mesma
//                 trava de provisionamento — confere a sessão E a linha viva em
//                 `admin_users`). Corretora nenhuma pareia o canal.
//   QUAL empresa → a do canal, achada no banco pelo tipo `platform_canal`
//                 (`lib/admin/canal-da-plataforma.ts`). ⛔ Nunca um `company_id`
//                 vindo do corpo ou da query: é assim que um IDOR entra.
//
// O `purpose` é `observer` porque é o que o pareamento grava para tudo que não
// é auxiliar (`channel_identity.purpose_canonico`). Quem tira o canal do caminho
// do observador é o desvio por `company_kind` no webhook (F1), não esta rota.
//
// SPEC-132-C C3 — a implementação mudou-se para `lib/admin/rota-do-canal-whatsapp.ts`
// SEM mudar um byte do que esta rota manda ao backend: o segundo número da
// plataforma (o assistente dos corretores, `app/api/admin/canais/assistente/whatsapp`)
// usa a MESMA rota com outro `purpose`, em vez de uma cópia dela.
import { rotaDoCanalWhatsApp } from '@/lib/admin/rota-do-canal-whatsapp';

export const dynamic = 'force-dynamic';

const ROTA = rotaDoCanalWhatsApp('observer', 'admin_canal');

export const GET = ROTA.GET;
export const POST = ROTA.POST;
