'use client';

// SPEC-131-B · conserto K2 (juiz de design, conserto 10) — a confirmação DA CASA (o AlertDialog do produto, o mesmo do
// "Ligar"), no lugar do `confirm()` do navegador, que destoa e não segue o tema. O gatilho é o filho (asChild).

import type { ReactNode } from 'react';

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { cn } from '@/lib/utils';

import { BOTAO_PRIMARIO } from './CardDoAplicativo';

export function Confirmar({
  titulo, descricao, acao, cancelar = 'Agora não', perigo = false, onConfirmar, children,
}: {
  titulo: string;
  descricao?: ReactNode;
  /** o rótulo do botão que confirma ("Apagar", "Tirar") */
  acao: string;
  cancelar?: string;
  /** ação que tira/apaga algo: o botão de confirmar vai em `danger` */
  perigo?: boolean;
  onConfirmar: () => void;
  /** o gatilho (um botão) */
  children: ReactNode;
}) {
  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>{children}</AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{titulo}</AlertDialogTitle>
          {descricao && <AlertDialogDescription className="text-sm text-muted-foreground">{descricao}</AlertDialogDescription>}
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel className="h-11">{cancelar}</AlertDialogCancel>
          <AlertDialogAction
            className={cn('h-11', perigo ? 'bg-danger text-danger-foreground hover:bg-danger/90' : BOTAO_PRIMARIO)}
            onClick={onConfirmar}
          >
            {acao}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

export default Confirmar;
