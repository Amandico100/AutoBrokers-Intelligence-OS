# Runbook — passkey no pareamento do WhatsApp

## Quando usar

Use este procedimento somente quando, depois da leitura do QR, a tela informar
**“O WhatsApp pediu uma confirmação de segurança”**. O fluxo normal de QR não
precisa da extensão.

O AutoBrokers não solicita senha, PIN, código de desbloqueio nem o valor da
passkey. A atendente confirma diretamente no navegador, celular ou sistema
operacional. Compartilhamento de tela também não é obrigatório.

## Preparação

1. Mantenha o celular do número pareado por perto.
2. Baixe `passkey-helper-autobrokers-0.7.2-ab1.zip` pela própria tela.
3. Descompacte o ZIP em uma pasta que não será removida depois da instalação.

O pacote roda apenas em `https://web.whatsapp.com` e aceita cerimônias apenas do
servidor Evolution Go fixado pela AutoBrokers. Ele não possui permissão para
outros sites e não lê conversas.

## Instalar no Google Chrome

1. Abra `chrome://extensions`.
2. Ative **Modo do desenvolvedor**.
3. Clique em **Carregar sem compactação**.
4. Selecione a pasta que contém `manifest.json`.
5. Volte ao AutoBrokers e clique em **Abrir WhatsApp Web**.

## Instalar no Microsoft Edge

1. Abra `edge://extensions`.
2. Ative **Modo de desenvolvedor**.
3. Clique em **Carregar sem pacote**.
4. Selecione a pasta que contém `manifest.json`.
5. Volte ao AutoBrokers e clique em **Abrir WhatsApp Web**.

## Confirmar

1. No painel aberto sobre o WhatsApp Web, clique em **Autenticar com chave de
   acesso**.
2. Confirme pela biometria, bloqueio do computador ou celular, conforme o
   navegador orientar.
3. Se aparecer um código, compare com o celular e só então clique em
   **Confirmar código**.
4. Volte ao AutoBrokers. A tela continuará acompanhando a tentativa.

## Expiração ou falha

- A confirmação é curta. Se expirar, volte à tela e use **Gerar novo QR**.
- Se a conexão do provedor reiniciar, a tentativa anterior é invalidada; nunca
  confirme um código antigo.
- Se houver falha, informe ao suporte apenas a referência exibida na tela. Não
  envie biometria, PIN, passkey, QR ou token.
