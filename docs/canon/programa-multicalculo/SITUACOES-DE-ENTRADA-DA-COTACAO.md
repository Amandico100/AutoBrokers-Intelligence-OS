# As situações de entrada — como a pessoa chega com os dados, e o que já sabemos fazer

> 10/10/2026 · planejador da fatia F5 da SPEC-133-A.1 · arquivo vivo do programa (atualizar ao fechar cada SPEC que mexer numa linha).
> Pergunta do Founder (10/10): *"SE A PESSOA TIVER UMA APOLICE, ELA PODE ENVIAR E O AGENTE CONSEGUE CALCULAR SEM FAZER PERGUTAS OU AIDA
> NAO TEMOS ISSO? … NOSSO AGENTE PRECISA CALCULAR O SEGURO COM APOLICE DO CLIENTE, COM UMA COTAÇÃO QUE ELE JA TENHA EM MAOS OU SE ELE
> NAO TIVER NADA OU SE ELE QUISER SO PASSAR O PREÇO E TALVE MAIS ALGUMA SITUAÇÃO QUE EU NAO CITEI"*.
> Legenda: ✅ PRONTO (no código, com o arquivo) · 🟡 PLANEJADO (em qual SPEC) · ⛔ NÃO PLANEJADO (com a recomendação) · 📊 medido · 💭 estimado.

## 0. A resposta curta

**Não: hoje, se a pessoa manda a apólice, o agente NÃO lê e NÃO calcula a partir dela.** No Quem Cobra Menos, foto, PDF e áudio são
guardados só como referência e o agente agradece e repete a pergunta da etapa (`backend/app/services/canal/conversa.py:766-830`,
"MÍDIA NUNCA É RESPOSTA", conserto B1 da 133-A — de propósito, porque o texto do PDF trazia nome, CPF e endereço para o modelo). No
chat principal, o PDF é extraído e vai ao modelo como texto (`backend/app/api/chat.py:829-841`), mas o chat ainda não tem a
ferramenta de cotar (a 132). A leitura da apólice está **PLANEJADA** na **130-B** (o leitor: foto ou PDF → ficha com origem e
confiança por campo) e é usada pela **132** (chat) e pela **133-B** (QCM).

**E "sem nenhuma pergunta" não existe nem com a apólice.** 📊 A apólice/InfoCap traz veículo, placa, chassi, FIPE, bônus,
nascimento, sexo e CEP, mas **não** traz estado civil, condutor principal, tempo de habilitação nem o questionário (garagem, uso, km,
jovem condutor) (`A-PROVA-DO-AGGER.md` §E2, n = 1 por conta); e o questionário é DECLARAÇÃO do segurado — resposta errada pode negar
sinistro, por isso o agente PERGUNTA e nunca assume (D-MC-59). A meta certa é **"só as perguntas que a apólice não responde"**: 💭 de
11 perguntas hoje para 3–5.

## 1. O mapa (QCM = Quem Cobra Menos no WhatsApp · Chat = cotação no chat principal/WhatsApp do membro · Renov. = Auxiliar de Renovação)

| # | a pessoa chega com… | QCM | Chat | Renov. | o que existe / o que falta |
|---|---|---|---|---|---|
| E1 | **nada** (responde perguntas) | ✅ 133-A | 🟡 132 | — | 11 perguntas uma por vez (`conversa.py:283-299`): placa, CEP, aplicativo, km, jovem, CPF, nome, nascimento, sexo, habilitação, quanto paga. O sexo só para nome ambíguo: 133-A.1 F2 |
| E2 | **só a placa** | ✅ parcial (133-A) | 🟡 132 | — | a placa supre FIPE/ano/combustível no robô (`multicalculo/pedido.py:52`, D-133A-03); o resto continua sendo perguntado |
| E3 | **só o preço que paga hoje** | ✅ como pergunta (pode pular) | 🟡 132 | — | entra como `atual` e a economia é contra ele (`comando_proposta.py`, `--atual`); 🔴 sozinho NÃO calcula nada — é a régua da comparação, não dado do risco |
| E4 | **a apólice (foto ou PDF)** | ⛔ hoje (só a referência) · 🟡 133-B | 🟡 132 (com a 130-B) | — | **o leitor é a 130-B** (fila: depois da 131-0 parte A); a apresentação "novo com apólice" já existe na proposta (`comparacao.py:46`, situação `novo_com_apolice`, a opção "igual à sua atual") mas hoje recebe a apólice por ARQUIVO JSON digitado (`comando_proposta.py:58`) |
| E5 | **uma cotação de outra corretora em mãos** (PDF/foto do orçamento) | ⛔ | ⛔ | — | **NÃO PLANEJADO.** O motor já sabe procurar um preço-alvo (`cotacao_alvo`, D-MC-72, 130-A); falta LER o documento (é outro layout que a apólice) e usar o preço/coberturas dele como alvo e como "igual ao que te ofereceram" → **RECOMENDAÇÃO: a 130-B classifica o documento** (apólice · proposta · cotação/orçamento · CRLV) e extrai os campos de cada tipo; a 132 e a 133-B usam a cotação como alvo |
| E6 | **o documento do carro (CRLV)** | ⛔ | ⛔ | — | **NÃO PLANEJADO.** Dá placa, chassi, RENAVAM, ano/modelo e o proprietário (nome e CPF/CNPJ — dado pessoal, mesmo cuidado do CPF) → **RECOMENDAÇÃO: na 130-B**, mesma bancada, custo marginal baixo; supre ainda o "veículo exato" quando a placa não basta |
| E7 | **áudio** ("calcule esse seguro pra mim") | ⛔ hoje (não é resposta) | 🟡 parcial | — | a transcrição EXISTE (`backend/app/services/audio_service.py:195`; o chat aceita `audioData`, `chat.py:78`); no QCM o áudio é descartado como resposta → **RECOMENDAÇÃO: QCM na 133-B** (transcrever e tratar como texto, com o mesmo mascaramento do CPF antes do modelo); Chat na 132 |
| E8 | **tudo numa mensagem só** ("Gol 2020, placa…, CEP…, 35 anos") | ⛔ (o roteiro entende UMA etapa por vez, `conversa.py:375` `entender(tipo, …)`) | 🟡 132 | — | **NÃO PLANEJADO** no QCM → **RECOMENDAÇÃO: 133-B** (extrair várias respostas da mesma fala, pela regra antes do modelo, e perguntar só o que faltou) |
| E9 | **a renovação a partir do sistema de gestão** | — | — | 🟡 131 | a apólice estruturada já se lê da InfoCap (`infocap_policy_provider.py:380` `apolice_do_pack`); o DONO da renovação vem do `/prod_docs` avulso, `indireto = "F"` (📊 228/228, 10/10) — **a 131-0 entra antes** (SPEC-131-0 §2.3); faltam ao robô os mesmos campos de E4 (questionário) → o manual da renovação decide "repetir o do ano anterior com aviso ao comercial" × "perguntar ao cliente" |
| E10 | **renovação de corretora sem sistema de gestão** | — | — | ⛔ | **NÃO PLANEJADO** → SPEC-131-0 D-131-0-13 (planilha) |
| E11 | **cliente da carteira pedindo cotação NOVA** (outro carro, outro ramo) | — | ⛔ | — | **NÃO PLANEJADO.** O cadastro dele já está no sistema de gestão (`/cliente`): preencher o que já se sabe e perguntar o resto → **RECOMENDAÇÃO: 132** (com a regra de qual Agger da 131-0) |
| E12 | **o membro pelo WhatsApp pessoal** (áudio + apólice, R13 do Founder) | — | ⛔ | — | **NÃO PLANEJADO** → SPEC-131-0 parte B1, **junto com a 132** (exige 130-B para a apólice e E7 para o áudio) |
| E13 | **ajuste depois do resultado** ("e sem carro reserva?") | 🟡 133-B/135 | 🟡 132 | 🟡 131 | ✅ no motor: recálculo com ajuste vira nova versão (129-B, D-128-03); falta a conversa pedir |
| E14 | **outros ramos** (condomínio, residencial, empresarial) com a apólice anterior | — | 🟡 132 | 🟡 131 | o montador por ramo é a **129-C** (próxima); a regra "+15 % na cobertura básica na renovação" (Founder 10/10) é config do manual de RENOVAÇÃO por ramo (D-133A1-06), e o leitor de apólice desses ramos é a 130-B estendida (a InfoCap já tem o PDF oficial e o extrator de evidência: `policy_document_evidence_service.py`) |
| E15 | **o lead do QCM que já é cliente de uma corretora** | ✅ por regra (nunca sinaliza "já é cliente", D-MC-46) | — | — | cruzar com a carteira é LGPD → SPEC-131-0 D-131-0-19 (não cruzar no piloto) |
| E16 | **o CPF de outra pessoa** (o filho cotando o carro do pai) | 🟡 133-B | 🟡 132 | — | declaração "sou o segurado ou tenho autorização" + nome da apólice × nome que o Agger devolve pelo CPF, sem mostrar (D-MC-46, §6.3 do plano) |

## 2. O que fazer, em ordem (sem mudar a fila; só encaixando)

1. **130-B — o leitor passa a ser um leitor de DOCUMENTO DE SEGURO, não só de apólice:** classifica (apólice · proposta · cotação de
   outra corretora · CRLV) e extrai por tipo, com origem e confiança por campo; bancada com 20–30 apólices **+ 5–10 cotações e 5–10
   CRLVs** autorizados (o Founder liberou baixar até 15 apólices por ramo da InfoCap, 10/10). Cobre E4, E5, E6 e a base de E14.
2. **132 — a cotação no chat usa o que a 130-B lê** e o cadastro do sistema de gestão (E11); áudio (E7); a regra de qual Agger
   (131-0); a parte B1 da 131-0 (E12) entra junto.
3. **133-B — o QCM aceita a apólice/cotação/CRLV (E4–E6), o áudio (E7) e várias respostas numa fala (E8)**, e pergunta só o que faltou;
   o "Eureka, X % abaixo do que você paga" só com o prêmio da apólice ou o informado (§6.6 do plano).
4. **131 — a renovação** (E9) com o dono da 131-0 e o manual de renovação por ramo (E14).

## 3. O que este mapa NÃO resolve
- Quanto a leitura acerta: só a bancada da 130-B mede (crédito de API, T-04).
- Se o questionário da apólice anterior pode ser reaproveitado na renovação sem perguntar: é decisão do manual de renovação de cada
  corretora (o risco de negativa de sinistro é do segurado) — registrar na abertura da 131.
