# O relatório das constantes — SPEC-084.1 FASE 1

> **Navegar e decidir têm a mesma forma no código.** Este relatório
> separa as duas, e nomeia a terceira população: a que ninguém julga.

```
   227  constantes no produto
   143  NAVEGAM        Continuar / Voltar / Sim / Não ...
    63  DECIDEM        escolhem entre alternativas de CONTEÚDO
    21  🔴 CEGAS       a tela NÃO está no corpus
```

## 1 · As que DECIDEM — cobertas pela varredura

📊 **63 constantes decidem**, e **50 têm `constante_justificada`**.

🔴 **E estas decidem SEM justificativa — a varredura devia tê-las
pego, e o relatório existe para conferir que ela pegou:**

- `porto-auto-whatsapp@v1` · **bateria_submenu** → `Recarga de bateria` — o rotulo 'Recarga de bateria' escolhe entre 4 ALTERNATIVAS DE CONTEUDO
- `porto-auto-whatsapp@v1` · **menu_quando** → `Tenho urgência` — o rotulo 'Tenho urgência' escolhe entre 2 ALTERNATIVAS DE CONTEUDO
- `porto-auto-whatsapp@v1` · **taxi_passageiros** → `1 a 4` — o rotulo '1 a 4' escolhe entre 2 ALTERNATIVAS DE CONTEUDO
- `hdi-auto-whatsapp@v1` · **situacao_risco** → `Nenhuma das anteriores` — o rotulo 'Nenhuma das anteriores' escolhe entre 3 ALTERNATIVAS DE CONTEUDO
- `hdi-auto-whatsapp@v1` · **quando_agora** → `Agora` — o rotulo 'Agora' escolhe entre 2 ALTERNATIVAS DE CONTEUDO
- `yelum-auto-whatsapp@v3` · **situacao_risco** → `Nenhuma das anteriores` — o rotulo 'Nenhuma das anteriores' escolhe entre 3 ALTERNATIVAS DE CONTEUDO
- `yelum-auto-whatsapp@v3` · **quando_agora** → `Agora` — o rotulo 'Agora' escolhe entre 2 ALTERNATIVAS DE CONTEUDO
- `azul-auto-whatsapp@v1` · **bateria_submenu** → `Recarga de bateria` — o rotulo 'Recarga de bateria' escolhe entre 4 ALTERNATIVAS DE CONTEUDO
- `bradesco-auto-whatsapp@v1` · **via_local_rodovia** → `Via local` — o rotulo 'Via local' escolhe entre 2 ALTERNATIVAS DE CONTEUDO
- `bradesco-auto-whatsapp@v1` · **agendamento_dia** → `Hoje` — o rotulo 'Hoje' escolhe entre 3 ALTERNATIVAS DE CONTEUDO
- `hdi-residencial-whatsapp@v1` · **quando_agora** → `Agora` — o rotulo 'Agora' escolhe entre 2 ALTERNATIVAS DE CONTEUDO
- `hdi-residencial-whatsapp@v1` · **quando_agora** → `Agora` — o rotulo 'Agora' escolhe entre 2 ALTERNATIVAS DE CONTEUDO
- `yelum-residencial-whatsapp@v1` · **quando_agora** → `Agora` — o rotulo 'Agora' escolhe entre 2 ALTERNATIVAS DE CONTEUDO

## 2 · 🔴 As CEGAS — o buraco que nenhuma medição mostra

📊 **21 constantes respondem uma tela que o corpus NÃO TEM.**
A varredura não as julga; a régua não as vê; o comparador não as conta.
**São exatamente a forma dos oito defeitos da §9.5:** *apareciam
verdes em toda medição*.

⚠️ Isto **não** quer dizer que estejam erradas — quer dizer que
**ninguém sabe**. Cada uma precisa da tela para ser julgada, e a
tela vem de coleta ou de uma sessão nova.

📊 Destas, **2 têm `constante_justificada`** escrita mesmo sem a
tela, e **19 não têm**.

**Onde elas se concentram:**

| corredor | constantes cegas sem justificativa |
|---|---:|
| `yelum-auto-whatsapp@v3` | 7 |
| `hdi-residencial-whatsapp@v1` | 4 |
| `yelum-residencial-whatsapp@v1` | 3 |
| `hdi-auto-whatsapp@v1` | 1 |
| `alfa-auto-whatsapp@v1` | 1 |
| `azul-auto-whatsapp@v1` | 1 |
| `bradesco-auto-whatsapp@v1` | 1 |
| `porto-residencial-whatsapp@v1` | 1 |

