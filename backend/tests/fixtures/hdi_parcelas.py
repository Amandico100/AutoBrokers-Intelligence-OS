# -*- coding: ascii -*-
"""Fixtures da tela Parcela da HDI -- ESTRUTURA real, DADOS inventados.

De onde vieram
==============
Do HTML que o founder capturou em 12/08/2026 (F12 > Network > filtro `dsp_` >
aba Response). A estrutura aqui e byte a byte a do portal: as mesmas tags, as
mesmas classes, o mesmo `onclick`, o mesmo HTML malformado.

O que NAO esta aqui
-------------------
Nome, CPF, apolice e valor de segurado real. SPEC-023A section 4 e explicita:
evidencia com dado de segurado nao vai para o git. Trocamos os valores e
mantivemos o formato -- o parser nao sabe a diferenca, e o repositorio nao
carrega o CPF de ninguem.

As tres armadilhas que estas fixtures seguram
---------------------------------------------
1. A BUSCA E ASSINCRONA. O primeiro POST devolve "Por favor aguarde" com um
   formulario `f_requisicao` que se reenvia sozinho em 5s. Quem parar no
   primeiro POST le ZERO linhas e conclui "nenhum inadimplente" -- que foi
   exatamente o que aconteceu na primeira tentativa.

2. UMA TABELA POR DOCUMENTO. Nao e uma tabela com N linhas: sao N tabelas de
   uma linha cada, e a primeira nem fecha o <tbody>. Parser que exige HTML bem
   formado quebra aqui.

3. O BOLETO NAO E UM LINK. Nao existe <a href>. O alvo mora dentro de um
   `onclick="...window.open('dsp_boleto.htm?p=<hash>',...)"`.
"""

# ---------------------------------------------------------------------------
# 1) A resposta do PRIMEIRO POST: "aguarde, estamos processando"
#    Repare no `m_num_requisicao` preenchido e `m_num_requisicao2` zerado --
#    no reenvio eles trocam de lugar.
# ---------------------------------------------------------------------------
AGUARDE = """
<form name="f_requisicao" id="f_requisicao" action="dsp_parcelas_view_2008.htm" method="post">
    <input name="isRevamp" type="hidden" value="true" />
    <input name="m_t_corretor" type="hidden" value="C" />
    <input name="t_prd" id="t_prd" type="hidden" value="C" />
    <input name="c_pc" id="c_pc" type="hidden" value="X605000297115_4620" />
    <input name="t_prd_orig" id="t_prd_orig" type="hidden" value="C" />
    <input name="c_pc_orig" id="c_pc_orig" type="hidden" value="X605000297115_4620" />
    <input name="m_cpf_prdtor" type="hidden" value="00000000000" />
    <input name="cpf_usuario" type="hidden" value="00000000000" />
    <input name="m_pesquisa" id="m_pesquisa" type="hidden" value="inicial" />
    <input name="m_num_requisicao" type="Hidden" value="1331319740" />
    <input name="m_num_requisicao2" type="Hidden" value="0" />
    <input name="m_indice" id="m_indice" type="hidden" value="0" />
    <input name="m_today" id="m_today" type="hidden" value="?" />
    <input name="m_time" id="m_time" type="hidden" value="0" />
    <input name="m_total" id="m_total" type="hidden" value="0" />
    <input name="m_pagina" id="m_pagina" type="hidden" value="0" />
    <input name="m_mostra_pagina" id="m_mostra_pagina" type="hidden" value="1" />
    <input name="l_s" type="hidden" value="008" />
    <input name="n_s" type="hidden" value="FLORIANOPOLIS" />
    <input name="s_cod_sucursal" type="hidden" value="008" />
    <input name="data_ini" id="data_ini" type="hidden" value="02/08/2026" />
    <input name="data_fim" id="data_fim" type="hidden" value="12/08/2026" />
    <input name="m_pag_anterior" id="m_pag_anterior" type="Hidden" value="hdidigital/dsp_parcelas_busca_2008.htm" />
    <input name="m_frame_hdidigital" type="Hidden" value="1" />
    <input name="tokenSec" type="Hidden" value="TOKEN_FICTICIO" />
</form>
<div class="geral-box">
<div class="no-border box-admin">
<div class="alerta-form alerta-full"><i class="icone icone-alerta vermelho"></i>
   <p class="txt" title="Req:1331319740-Processando:1331272048"> Por favor aguarde. Estamos processando a requisi&ccedil;&atilde;o...</p>
</div>
</div>
</div>
<script language="JavaScript">
tempo = setTimeout("document.f_requisicao.submit();",5000);
</script>
"""

# ---------------------------------------------------------------------------
# 2) A resposta do REENVIO: a tabela de verdade.
#    Duas parcelas, de proposito diferentes entre si:
#      - a 1a  "Parcela a Vencer" + Credito + SEM 2a via
#      - a 2a  "Parcela em Atraso" + Boleto + COM 2a via (onclick)
#    Um guarda que so tem linhas iguais nao prova nada.
# ---------------------------------------------------------------------------
RESULTADO = """
<form name="f_requisicao" id="f_requisicao" action="dsp_parcelas_view_2008.htm" method="post">
    <input name="m_num_requisicao" type="Hidden" value="0" />
    <input name="m_num_requisicao2" type="Hidden" value="1331319740" />
    <input name="m_indice" id="m_indice" type="hidden" value="530703753" />
    <input name="m_today" id="m_today" type="hidden" value="12/08/26" />
    <input name="m_time" id="m_time" type="hidden" value="21686" />
    <input name="m_total" id="m_total" type="hidden" value="2" />
    <input name="m_pagina" id="m_pagina" type="hidden" value="1" />
</form>
<div class="geral-box">
     <h3 class="left">Resultado da busca</h3>
<div class="box left resultado-parcelas">
                <div id="legenda" class="legenda left">
                    <p class="primeiro"><strong>Legenda:</strong></p>
                    <p><i class="icone icone-estrela uma"></i> Parcela de documento com atraso acima do limite </p>
                    <p><i class="icone icone-estrela duas"></i> Faturamento Mensal </p>
                    <p><i class="icone icone-estrela tres"></i> Pagamento diferente de Boleto Banc&aacute;rio </p>
                    <p><i class="icone icone-estrela quatro"></i> Parcela anterior pendente </p>
                </div>
<table border="0" cellpadding="0" cellspacing="0" class="table-format">
                    <thead>
                    <tr>
                       <th>Documento/Parcela      </th>
                       <th>Vencto.                </th>
                       <th>Limite<br>sem Vistoria </th>
                       <th>Nome cliente           </th>
                       <th>Valor (R$)             </th>
                       <th>Posi&ccedil;&atilde;o                </th>
                       <th>Data de<br>Pagamento   </th>
                       <th>Data Prev.<br>Receb.   </th>
                       <th>Forma de Pagamento     </th>
                       <th>Gerar                  </th>
                    </tr>
                    </thead>
<tbody class="">
<tr id="tr_01008005A065191000000004" >
   <td class="grande140" align="center" height="25" nowrap style="cursor:pointer" title="Clique sobre o documento para consult&aacute;-lo" onclick="mostra_proposta('01','008','005','A','065191','000000','000000','C','500027665','TOKEN_FICTICIO')"   >01.008.005.065191.000000 - 04 de 04</td>
<td class="pequena" align="center">12/08/26</td>
<td class="pequena" align="center"></td>
<td class="grande110"  align="center" nowrap>FULANO DE TAL</td>
<td class="media" align="right">          82,29</td>
<td class="pequena" align="center">Parcela a Vencer</td>
<td class="pequena" align="center"></td>
<td class="pequena" align="center"></td>
<td class="media" align="center">Cr&eacute;dito</td>
<td class="media" align="center"  style="cursor:default">Parcela diferente de Boleto Banc&aacute;rio.</td>
</tr>
</table>
<div class="opc-parcela">
   <p class="periodo-apolice">Cobertura Proporcional at&eacute;: 03/12/2026.</p>
</div>
<div class="opc-parcela" style="display:flex; justify-content: flex-end">
 <a class="btn btn-normal btn-cinza right btn-formas-pagamento" href="#" onclick="reprogParcela('01.008.005.065191.000000', 'false')">Reprograma&ccedil;&atilde;o de Parcela</a>
 <a class="btn btn-normal btn-cinza right btn-formas-pagamento" href="#" onclick="termoAdimplencia('01.008.005.065191.000000')">Termo de Adimpl&ecirc;ncia</a>
 <a class="btn btn-normal btn-cinza right btn-formas-pagamento" href="#" onclick="checkAntecipa('01.008.005.065191.000000','false','false', 'C', 'false')">Antecipa&ccedil;&atilde;o de Parcelas</a>
 <a class="btn btn-normal btn-cinza right btn-formas-pagamento" href="#" onclick="checkAlterar('01.008.005.065191.000000','R','false','false', 'C', '0', 'false', 'false', 'false')">Altera&ccedil;&otilde;es Financeiras</a>
</div>
<table width="755" border="0" cellpadding="0" cellspacing="0" class="table-format" align="center">
<tbody class="">
<tr id="tr_01008119A003755000000002" >
     <td class="grande140" align="center" height="25" nowrap style="cursor:pointer" title="Clique sobre o documento para consult&aacute;-lo" onclick="mostra_proposta('01','008','119','A','003755','000000','000000','C','500027665','TOKEN_FICTICIO')"   >01.008.119.003755.000000 - 02 de 06</td>
<td class="pequena" align="center">09/08/26</td>
<td class="pequena" align="center">04/09/26</td>
<td class="grande110"  align="center" nowrap>CONDOMINIO EXEMPLO RESIDENCIAL</td>
<td class="media" align="right">       1.006,02</td>
<td class="pequena" align="center">Parcela em Atraso</td>
<td class="pequena" align="center"></td>
<td class="pequena" align="center"></td>
<td class="media" align="center">Boleto</td>
<td class="media" align="center"  title="Gerar boleto." style="cursor:pointer" onclick="alerta_conjugado('');window.open('dsp_boleto.htm?p=3abbeb98e4c4b34f921e49432285c69b17f68ae15fd0df216891HASHFICTICIO6ef4be701a6d332f8ce74230f55855fb997aabaa4a4c2dafdeaeeafa06a527','boleto','toolbar=no,location=no,status=yes,menubar=yes,scrollbars=yes,resizable=yes,top=50,left=50,width=700,height=450')" >2&ordf; via</td>
</tr>
</tbody>
</table>
<div class="opc-parcela">
   <p class="periodo-apolice">Cobertura Proporcional at&eacute;: 09/07/2026.</p>
</div>
<div class="desc-pagamento">
   <p>Total Pago no per&iacute;odo:      <span>           0,00</span></p>
   <p>Total em Aberto no per&iacute;odo: <span>       1.088,31</span></p>
</div>
</div>
<p class="clearBoth">Listando de 1 a 2 de 2 documentos. P&aacute;g:1&nbsp;&nbsp;</p>
</div>
"""

# ---------------------------------------------------------------------------
# 3) A ponte do shell novo para o app legado (passo 1 da cadeia).
# ---------------------------------------------------------------------------
PONTE = """
<form id="formCarregarLegado" action="https://www.hdi.com.br/web/hdidigital/dsp_parcelas_busca_2008.htm" method="POST">
	<input type="hidden" name="m_cod_sucursal" value="008" />
	<input type="hidden" name="m_cod_corretor" value="500027665" />
	<input type="hidden" name="m_c_sucursais" value="008" />
	<input type="hidden" name="m_site_2008" value="true" />
	<input type="hidden" name="t_prd" value="C" />
	<input type="hidden" name="m_nome_user_web" value="00000000000" />
	<input type="hidden" name="m_cod_opcao_menu_2008" value="9" />
	<input type="hidden" name="t_prd_orig" value="C" />
	<input type="hidden" name="c_pc" value="X605000297115_4620" />
	<input type="hidden" name="l_s" value="008" />
	<input type="hidden" name="n_s" value="FLORIANOPOLIS" />
	<input type="hidden" name="c_pc_grupo" value="X605000297115_4620" />
	<input type="hidden" name="tokenSec" value="TOKEN_FICTICIO" />
	<input type="hidden" name="c_pc_orig" value="X605000297115_4620" />
	<input type="hidden" name="m_t_corretor" value="C" />
	<input type="hidden" name="m_cpf_prdtor" value="00000000000" />
	<input type="hidden" name="m_n_sucursais" value="FLORIANOPOLIS" />
	<input type="hidden" name="chaveUsuario" value="CHAVE_FICTICIA" />
	</form>
<script type="text/javascript">document.getElementById("formCarregarLegado").submit();</script>
"""

# O <select> real da tela de busca -- a fonte dos valores de `s_tipo`.
SELECT_TIPO = """
<select id="s_tipo" name="s_tipo">
   <option value="0">Todas</option>
   <option value="1" selected="selected">A vencer</option>
   <option value="2">Quitadas</option>
   <option value="3">Atrasadas</option>
   <option value="4">Canceladas</option>
</select>
"""
