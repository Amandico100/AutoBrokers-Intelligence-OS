// SPEC-132-C C3 — o QR do número "AutoBrokers — assistente dos corretores" no portal ADMIN.
//
// A MESMA rota do QR do Quem Cobra Menos (`lib/admin/rota-do-canal-whatsapp.ts`): só administrador da PLATAFORMA,
// a empresa da plataforma achada no banco pelo tipo `platform_canal`, o mesmo caminho até o pareamento. O que muda é
// o `purpose`, FIXO aqui: 'assistente' — o backend dá a ele linha, nome de instância e QR PRÓPRIOS
// (`channel_identity.escopo_de('assistente') == 'plataforma:assistente'`), e o webhook desvia a linha para o atalho
// do chat (`atalho.entrada`), antes do QCM e do observer. Ler este QR não toca no número do Quem Cobra Menos.
import { rotaDoCanalWhatsApp } from '@/lib/admin/rota-do-canal-whatsapp';

export const dynamic = 'force-dynamic';

const ROTA = rotaDoCanalWhatsApp('assistente', 'admin_canal_assistente');

export const GET = ROTA.GET;
export const POST = ROTA.POST;
