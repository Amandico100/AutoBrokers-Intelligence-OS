// SPEC-061 §6.3 → SPEC-064 Bloco B — redirecionamento permanente.
//
// Esta tela ("Conversas") era da CORRETORA e morava em /admin. A SPEC-061 §6
// exigiu a separação das superfícies e a mudou para `/dashboard/conversas`.
//
// A SPEC-064 mediu o resultado e encontrou o efeito colateral: passaram a
// existir DUAS telas de conversa da corretora.
//
//     /dashboard/conversas                1.195 linhas, chamando
//                                         /api/admin/conversations
//     /dashboard/atendimentos/conversas   SPEC-043, chamando
//                                         /api/dashboard/conversas
//
// A primeira era a tela do admin com endereço novo: continuou falando com a
// API de administração de dentro da casa da corretora — exatamente a mistura
// que a §6 mandou desfazer. A segunda é a implementação de tenant, com
// assumir, enviar, devolver e áudio.
//
// A duplicata foi removida, junto com as três rotas de API que só ela usava.
// O destino agora é a tela canônica.
//
// O arquivo continua existindo, e só redireciona, porque link salvo não some
// quando a rota muda. Apagar transformaria cada um deles num 404.
import { redirect } from 'next/navigation';

export default function RedirecionaParaConversas() {
  redirect('/dashboard/atendimentos/conversas');
}
