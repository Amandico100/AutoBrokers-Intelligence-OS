// SPEC-064 Bloco B — redirecionamento permanente.
//
// O Briefing nunca foi um pilar: e um AUXILIAR. Ele ja tinha tudo o que
// define um — agenda, configuracao por empresa (briefing_profiles),
// execucao duravel (work_runs) e saida (briefing_publications). Faltava
// reconhece-lo como tal em vez de promove-lo a item de menu.
//
// A TELA NAO SUMIU: ela mudou de casa, inteira, e agora e a tela de
// execucao do "Checklist das 6h". Apagar o conteudo e redirecionar para
// a ficha do Auxiliar teria deixado o corretor sem o briefing do dia.
//
// O arquivo continua existindo, e so redireciona, porque link salvo nao some
// quando a rota muda: favorito, e-mail antigo, documentacao velha, uma LLM
// lendo uma SPEC de tres semanas atras. Apagar transformaria cada um deles
// num 404.
import { redirect } from 'next/navigation';

export default function Redireciona() {
  redirect('/dashboard/auxiliares/checklist-6h/hoje');
}
