"""SPEC-131-0-B2 — A LINHA DO USUÁRIO: o corretor conecta o PRÓPRIO WhatsApp e fala com o AutoBrokers na conversa
consigo mesmo ("Mensagem para você").

Uma instância do Evolution GO por PESSOA (`integrations.purpose='linha_do_usuario'` + `owner_user_id`), pareada no
Meu perfil pelo `pairing_orchestrator` que já existe (o dono entra no escopo e no nome — `channel_identity`).

    estado.py      a leitura e a escrita da linha no banco: `linha_da_instancia`, `linha_do_dono`, o teto, as chaves,
                   `registrar_conexao` / `registrar_desconexao` (o evento de conexão que o webhook — L2 — chama) e o
                   cálculo PURO do estado que a tela mostra.
    pareamento.py  as ações da pessoa: `conectar`, `qr` (renova depois do QRTimeout), `estado`, `desconectar`.

⛔ Nenhum cliente HTTP novo de WhatsApp: tudo que fala com o provedor passa pelo `PairingOrchestrator` (CLAUDE.md §5).
⛔ Toda leitura/escrita filtra `company_id` E `owner_user_id` no CÓDIGO — o backend usa service role (CLAUDE.md §7).
⛔ Nenhum telefone em claro em log; para a tela, só mascarado (CLAUDE.md §13.3).
"""
from app.services.linha_do_usuario.estado import (  # noqa: F401
    ESTADOS,
    PURPOSE,
    Recusa,
    linha_da_instancia,
    linha_do_dono,
    registrar_conexao,
    registrar_desconexao,
)
