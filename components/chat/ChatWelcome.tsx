import { BrandMark } from '@/components/BrandMark';

/**
 * A saudação da conversa vazia (SPEC-132-A §4): "Olá, {primeiro nome}" e uma linha. Logo abaixo, a caixa — no
 * notebook as duas ficam no meio da tela; no celular a caixa fica embaixo. Os atalhos que moravam aqui
 * ("Ver atendimentos", "Novo auxiliar") saíram (D-132A-03): quem cota escreve.
 */
export function ChatWelcome({ nome }: { nome?: string | null }) {
  const bruto = (nome || '').trim().split(/\s+/)[0] || '';
  const primeiro = bruto ? bruto.charAt(0).toLocaleUpperCase('pt-BR') + bruto.slice(1) : '';
  return (
    <div className="flex flex-col items-center px-2 text-center">
      <BrandMark size={32} />
      <h1 className="mt-5 text-[26px] font-semibold leading-tight tracking-tight text-foreground sm:text-3xl">
        {primeiro ? `Olá, ${primeiro}` : 'Olá'}
      </h1>
      <p className="mt-2 max-w-md text-[15px] leading-relaxed text-muted-foreground">O que vamos resolver hoje?</p>
    </div>
  );
}

export default ChatWelcome;
