# Painel do Founder — como se atualiza

O painel vive em **um link só**: `https://claude.ai/code/artifact/defe331c-9399-4584-9d1c-2126a527cea0`
(título "Régua dos Corredores"; o título e o ícone **não mudam**).

1. **Uma SPEC atualiza UMA aba.** Edite só `aba-<id>.html` — as outras ficam intactas.
   As abas são: `inicio · tarefas · specs · piloto · vidros · corredores · conhecimento · pendencias · historico`.
2. Rode `python montar.py`. Ele junta `base.html` + os nove fragmentos em `painel.html` e reprova
   fragmento com `<div>` desbalanceado, id errado ou sem botão no menu.
3. Publique: ferramenta **Artifact**, `action: "publish"`, `file_path` = `painel.html`, `url` = o link acima.
4. ⚠️ **A ferramenta exige ler a versão viva INTEIRA antes de republicar de outro chat**
   (`action: "read"` com a url → ela salva um arquivo local → `Read` esse arquivo até a última linha).
   Se outra sessão publicou no meio, a publicação é recusada e você recebe a versão nova para mesclar.
5. **Aba nova:** crie `aba-<id>.html` começando por `<div id="tab-<id>" class="tab" hidden>`,
   acrescente o `<id>` à lista `ABAS` do `montar.py` **e** um botão `data-tab="<id>"` em `base.html`.
6. O arquivo publicado **não leva moldura de plataforma**: `base.html` começa em `<title>`, sem
   `<!doctype>`, `<html>`, `<head>` ou `<body>`. Não acrescente.
7. `base.html` guarda o CSS e os três scripts (filtro da tabela de corredores, seletor de abas,
   filtro da matriz de conhecimento). **Nenhum script novo** — estender o objeto `panes` basta.
8. Ids são globais: não repita `id=` entre abas (hoje só `tb`, `cnt`, `tb-rag`, `cnt-rag`, `q-rag`).
9. Os números marcados **📊** precisam de data e da fonte ao lado; os **💭** nunca podem ser citados como fato.
10. O mapa antigo das SPECs (`https://claude.ai/artifact/NifoHsGNtiVSEzA6upRRAF`) está **aposentado**:
    ele só carrega uma faixa apontando para a aba **AS SPECS** daqui. Não o atualize mais.
