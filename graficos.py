# graficos.py
import streamlit as st
import pandas as pd
import locale
import plotly.express as px
import plotly.graph_objects as go

# Estilização de KPIs
def aplicar_estilo_kpi():
    st.markdown("""<style>
        .kpi-container {
            background-color: #004E64;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 20px;
            box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.1);
            width: 220px;
            height: 130px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        }
        .kpi-title {
            font-size: 16px;
            font-weight: bold;
            color: #ffffff;
        }
        .kpi-value {
            font-size: 18px;
            font-weight: bold;
            color: #ffffff;
        }
        .kpi-delta-positive {
            font-size: 14px;
            color: #9FFFCB;
        }
        .kpi-delta-negative {
            font-size: 14px;
            color: #FCB9B2;
        }
        </style>
    """, unsafe_allow_html=True)

# Formatar moeda
def formatar_moeda(valor):
    try:
        # Revisar
        if isinstance(valor, str):
            valor = valor.replace('R$', '').strip()
            valor = valor.replace('.', '').replace(',', '')
        return float(valor)
    except:
        return 0.0 

# Exibir um KPI individual
def mostrar_kpi(coluna, titulo, valor, delta=None, sufixo="", valor_monetario=False, e_taxa_conversao=False):
    if valor_monetario and isinstance(valor, (float, int)):
        valor_formatado = formatar_moeda(valor)
    else:
        # Aplica sufixo "%" apenas se for taxa de conversão ou se o sufixo não for "%"
        if sufixo == "%" and not e_taxa_conversao:
            valor_formatado = str(valor)
        else:
            valor_formatado = f"{valor}{sufixo}" if sufixo else str(valor)

    html = f'<div class="kpi-container"><div class="kpi-title">{titulo}</div><div class="kpi-value">{valor_formatado}</div>'

    if delta is not None:
        classe_delta = 'kpi-delta-positive' if delta >= 0 else 'kpi-delta-negative'
        sinal = "+" if delta >= 0 else ""
        sufixo_delta = "%" if sufixo == "%" else ""
        html += f'<div class="{classe_delta}">Variação: {sinal}{round(delta, 2)}{sufixo_delta}</div>'
    
    html += '</div>'
    coluna.markdown(html, unsafe_allow_html=True)

# Exibir todos os KPIs
def exibir_kpis(df, df_filtrado, gastos, df_gasto_original, data_inicio, data_fim, considerar_dias_uteis, colunas):
    col1, col2, col3, col4, col5, col6 = colunas

    # Verificar se um período específico foi selecionado
    periodo_selecionado = data_inicio != df['data'].min() or data_fim != df['data'].max()
    
    # Calcular o período anterior equivalente
    periodo_atual = (data_fim - data_inicio).days + 1
    data_fim_anterior = data_inicio - pd.Timedelta(days=1)
    data_inicio_anterior = data_inicio - pd.Timedelta(days=periodo_atual)
    
    # Filtrar dados do período anterior (usando mesmos filtros do período atual)
    filtros_atuais = {
        'equipe': df_filtrado['equipe'].unique(),
        'produto': df_filtrado['produto'].unique(),
        'convenio_acronimo': df_filtrado['convenio_acronimo'].unique(),
        'etapa': df_filtrado['etapa'].unique(),
        'origem': df_filtrado['origem'].unique()
    }
    
    df_periodo_anterior = df[
        (df['data'] >= data_inicio_anterior) & 
        (df['data'] <= data_fim_anterior) &
        df['equipe'].isin(filtros_atuais['equipe']) &
        df['produto'].isin(filtros_atuais['produto']) &
        df['convenio_acronimo'].isin(filtros_atuais['convenio_acronimo']) &
        df['etapa'].isin(filtros_atuais['etapa']) &
        df['origem'].isin(filtros_atuais['origem'])
    ]
    
    # Aplicar filtro de dias úteis se necessário
    if considerar_dias_uteis:
        # Importar a função filtrar_dias_uteis do módulo limpeza
        from limpeza import filtrar_dias_uteis
        df_periodo_anterior = filtrar_dias_uteis(df_periodo_anterior, data_inicio_anterior, data_fim_anterior, True)
    
    # Total do período anterior
    total_periodo_anterior = df_periodo_anterior.shape[0]
    
    # Dados do período atual
    total_filtrado = df_filtrado.shape[0]

    with col1:
        # Calcular delta do total de leads
        delta_leads = None
        if periodo_selecionado and total_periodo_anterior > 0:
            delta_leads = ((total_filtrado - total_periodo_anterior) / total_periodo_anterior) * 100
        mostrar_kpi(col1, "Total de Leads Gerados", total_filtrado, delta=delta_leads, sufixo="%")

    with col2:
        dias = pd.bdate_range(start=data_inicio, end=data_fim) if considerar_dias_uteis else pd.date_range(start=data_inicio, end=data_fim)
        media_leads = int(total_filtrado / len(dias) if len(dias) > 0 else 0)
        
        # Média do período anterior
        dias_anterior = pd.bdate_range(start=data_inicio_anterior, end=data_fim_anterior) if considerar_dias_uteis else pd.date_range(start=data_inicio_anterior, end=data_fim_anterior)
        media_leads_anterior = total_periodo_anterior / len(dias_anterior) if len(dias_anterior) > 0 else 0
        
        # Calcular delta da média
        delta_media = None
        if periodo_selecionado and media_leads_anterior > 0:
            delta_media = ((media_leads - media_leads_anterior) / media_leads_anterior) * 100
        
        mostrar_kpi(col2, "Média de Leads Gerados", round(media_leads, 2), delta=delta_media, sufixo="%")

    with col3:
        # Taxa de conversão atual
        taxa_filtro = df_filtrado.query('etapa == "PAGO"').shape[0] / total_filtrado if total_filtrado > 0 else 0
        
        # Taxa de conversão do período anterior
        taxa_anterior = df_periodo_anterior.query('etapa == "PAGO"').shape[0] / total_periodo_anterior if total_periodo_anterior > 0 else 0
        
        # Calcular delta da taxa
        delta_taxa = None
        if periodo_selecionado and taxa_anterior > 0:
            delta_taxa = ((taxa_filtro - taxa_anterior) / taxa_anterior) * 100
            
        mostrar_kpi(col3, "Taxa de Conversão", round(taxa_filtro * 100, 2), delta=delta_taxa, sufixo="%", e_taxa_conversao=True)

    with col4:
        valor_gerado = df_filtrado.query('etapa == "PAGO"')['comissao_paga'].sum()
        
        # Valor gerado no período anterior
        valor_anterior = df_periodo_anterior.query('etapa == "PAGO"')['comissao_paga'].sum()
        
        # Calcular delta do valor gerado
        delta_valor = None
        if periodo_selecionado and valor_anterior > 0:
            delta_valor = ((valor_gerado - valor_anterior) / valor_anterior) * 100
            
        mostrar_kpi(col4, "Valor Total Gerado", valor_gerado, delta=delta_valor, valor_monetario=True, sufixo="%")

    with col5:
        valor_gasto = gastos['valor_pago'].sum()
        valor_gasto_anterior = 0
        
        try:
            if df_gasto_original is not None and not df_gasto_original.empty:
                # Filtrar gastos do período anterior
                gastos_periodo_anterior = df_gasto_original[
                    (df_gasto_original['data'] >= data_inicio_anterior) & 
                    (df_gasto_original['data'] <= data_fim_anterior)
                ]
                
                # Aplicar os mesmos filtros do período atual
                gastos_periodo_anterior = gastos_periodo_anterior[
                    gastos_periodo_anterior['Convênio'].isin(filtros_atuais['convenio_acronimo']) &
                    gastos_periodo_anterior['Produto'].isin(filtros_atuais['produto']) &
                    gastos_periodo_anterior['Equipe'].isin(filtros_atuais['equipe']) &
                    gastos_periodo_anterior['Canal'].isin(filtros_atuais['origem'])
                ]
                
                # Aplicar custos unitários
                custos_unitarios = {'SMS': 0.048, 'RCS': 0.105, 'HYPERFLOW': 0.047, 'Whatsapp': 0.046}
                gastos_anterior = gastos_periodo_anterior.groupby(['Equipe', 'Convênio', 'Produto', 'Canal'])['Quantidade'].sum().reset_index()
                gastos_anterior['valor_pago'] = gastos_anterior['Canal'].map(custos_unitarios) * gastos_anterior['Quantidade']
                valor_gasto_anterior = gastos_anterior['valor_pago'].sum()
                
        except Exception as e:
            st.write(f"Erro no cálculo: {e}")
            valor_gasto_anterior = 0
        
        # Calcular delta do valor gasto
        delta_gasto = None
        if periodo_selecionado and valor_gasto_anterior > 0:
            delta_gasto = ((valor_gasto - valor_gasto_anterior) / valor_gasto_anterior) * 100
            
        mostrar_kpi(col5, "Valor Total Gasto", valor_gasto, delta=delta_gasto, valor_monetario=True, sufixo="%")

    with col6:
        lucro = valor_gerado - valor_gasto
        
        # Cálculo do lucro do período anterior
        lucro_anterior = None
        if periodo_selecionado and valor_anterior is not None and valor_gasto_anterior is not None:
            lucro_anterior = valor_anterior - valor_gasto_anterior
            
        # Cálculo da variação percentual do lucro
        delta_lucro = None
        if lucro_anterior is not None and lucro_anterior != 0:
            delta_lucro = ((lucro - lucro_anterior) / abs(lucro_anterior)) * 100
            
        mostrar_kpi(col6, "Lucro Bruto", lucro, delta=delta_lucro, valor_monetario=True, sufixo="%")

# GRAFICO 1 - Gastos por convênio/Produto
def grafico_gasto_convenio_produto(df_filtrado, df_gasto, top_n=5, df_gasto_tag=None, analisar_campanha=False, filtros=None, data_inicio=None, data_fim=None):
    df_pago = df_filtrado[df_filtrado['etapa'] == 'PAGO']

    if analisar_campanha and df_gasto_tag is not None:
        # Opção para aplicar ou não os filtros
        col1, col2 = st.columns(2)
        with col1:
            aplicar_filtro_equipe = st.checkbox("Aplicar filtro de equipe", value=True, key="filtro_equipe_gasto") # Redundante. Mapear dependências para remover
        with col2:
            incluir_fora_periodo = st.checkbox("Incluir tags fora do período", value=False, key="incluir_fora_periodo_gasto")
        
        # Criar cópia de trabalho para não alterar o original
        df_gasto_tag_work = df_gasto_tag.copy()
        
        
        
        # Garantir que valoers na coluna 'Custo Convertido' sejam numéricos
        if 'Custo Convertido' in df_gasto_tag_work.columns:
            # Remover possíveis caracteres não numéricos e converter vírgula para ponto (revisar essa conversão)
            df_gasto_tag_work['Custo Convertido'] = df_gasto_tag_work['Custo Convertido'].astype(str)
            df_gasto_tag_work['Custo Convertido'] = df_gasto_tag_work['Custo Convertido'].str.replace(',', '.').str.replace('R$', '').str.strip()
            df_gasto_tag_work['Custo Convertido'] = pd.to_numeric(df_gasto_tag_work['Custo Convertido'], errors='coerce').fillna(0)
            
        
        # Aplicar os filtros conforme as opções selecionadas
        if aplicar_filtro_equipe and 'equipe_da_tag' in df_gasto_tag_work.columns and filtros is not None:            
            # Filtrar
            df_gasto_tag_filtered = df_gasto_tag_work[df_gasto_tag_work['equipe_da_tag'].isin(filtros['equipe'])]
            
            # Se o filtro deixou o dataframe vazio, não aplicar
            if not df_gasto_tag_filtered.empty:
                df_gasto_tag_work = df_gasto_tag_filtered
        
        if not incluir_fora_periodo and 'data_da_tag' in df_gasto_tag_work.columns and data_inicio is not None and data_fim is not None:
            
            # Filtrar
            df_gasto_tag_filtered = df_gasto_tag_work[
                (df_gasto_tag_work['data_da_tag'] >= data_inicio) & 
                (df_gasto_tag_work['data_da_tag'] <= data_fim)
            ]
            
            # Se o filtro deixou o dataframe vazio, não aplicar
            if not df_gasto_tag_filtered.empty:
                df_gasto_tag_work = df_gasto_tag_filtered
        
        # Verificar se df_gasto_tag ainda tem dados após os filtros
        if df_gasto_tag_work.empty:
            st.warning("O arquivo de campanhas não tem dados após a aplicação dos filtros. Experimente desmarcar algumas opções de filtro.")
            # Usar dados originais como fallback, sem filtros
            df_gasto_tag_work = df_gasto_tag.copy()
            
            # Garantir que Custo Convertido seja numérico
            if 'Custo Convertido' in df_gasto_tag_work.columns:
                df_gasto_tag_work['Custo Convertido'] = df_gasto_tag_work['Custo Convertido'].astype(str)
                df_gasto_tag_work['Custo Convertido'] = df_gasto_tag_work['Custo Convertido'].str.replace(',', '.').str.replace('R$', '').str.strip()
                df_gasto_tag_work['Custo Convertido'] = pd.to_numeric(df_gasto_tag_work['Custo Convertido'], errors='coerce').fillna(0)
        
            
        # Pegar só dados de custo
        gasto_convenios = df_gasto_tag_work.groupby(['Tag'])['Custo Convertido'].sum().reset_index(name='gasto_total')

        
        # Para comissões, pegamos do df_pago
        df_pago_work = df_pago.copy()
        
        # Aplicar os mesmos filtros para df_pago
        if aplicar_filtro_equipe and 'equipe_da_tag' in df_pago_work.columns and filtros is not None:
            df_pago_filtered = df_pago_work[df_pago_work['equipe_da_tag'].isin(filtros['equipe'])]
            if not df_pago_filtered.empty:
                df_pago_work = df_pago_filtered
        
        if not incluir_fora_periodo and 'data_da_tag' in df_pago_work.columns and data_inicio is not None and data_fim is not None:
            df_pago_filtered = df_pago_work[
                (df_pago_work['data_da_tag'] >= data_inicio) & 
                (df_pago_work['data_da_tag'] <= data_fim)
            ]
            if not df_pago_filtered.empty:
                df_pago_work = df_pago_filtered
        
        gerado_convenios = df_pago_work.groupby(['tag_campanha'])['comissao_paga'].sum().reset_index(name='comissao_paga')
        
        # Renomear coluna para compatibilidade com o merge (correspondência exata)
        gasto_convenios.rename(columns={'Tag': 'tag_campanha'}, inplace=True)
        
        # Mesclagem com correspondência exata
        convenios_completo = pd.merge(
            gasto_convenios,
            gerado_convenios,
            on='tag_campanha',
            how='outer'
        ).fillna(0)
        
        # Ordenar e limitar ao top_n
        convenios_completo = convenios_completo.sort_values(by='gasto_total', ascending=False).head(top_n)
        
        # IMPORTANTE: Garantir que o eixo Y mostre as tags
        convenios_completo['conv_prod'] = convenios_completo['tag_campanha']
    else:
        
        # Garante que as colunas existem antes de agrupar/renomear
        if 'Convênio' in df_gasto.columns and 'Produto' in df_gasto.columns and 'Valor Gasto' in df_gasto.columns:
            gasto_convenios = df_gasto.groupby(['Convênio', 'Produto'])['Valor Gasto'].sum().reset_index(name='gasto_total')
        else:
            st.error("Colunas necessárias não encontradas em df_gasto.")
            return go.Figure()
        
        if 'convenio_acronimo' in df_pago.columns and 'produto' in df_pago.columns and 'comissao_paga' in df_pago.columns:
            gerado_convenios = df_pago.groupby(['convenio_acronimo', 'produto'])['comissao_paga'].sum().reset_index(name='comissao_paga')
        else:
            st.error("Colunas necessárias não encontradas em df_pago.")
            return go.Figure()

        gasto_convenios.rename(columns={
            'Convênio': 'convenio_acronimo',
            'Produto': 'produto',
        }, inplace=True)

        # Só faz o merge se as colunas existirem
        if 'convenio_acronimo' in gasto_convenios.columns and 'convenio_acronimo' in gerado_convenios.columns:
            convenios_completo = pd.merge(
                gasto_convenios,
                gerado_convenios,
                on=['convenio_acronimo', 'produto'],
                how='outer'
            ).fillna(0)
        else:
            st.error("Colunas 'convenio_acronimo' ou 'produto' não encontradas para o merge.")
            return go.Figure()

        convenios_completo = convenios_completo.sort_values(by='comissao_paga', ascending=False).head(top_n)
        convenios_completo['conv_prod'] = convenios_completo['convenio_acronimo'] + ' - ' + convenios_completo['produto']

    # Verificar se convenios_completo foi definido e tem dados
    if 'convenios_completo' not in locals() or convenios_completo.empty:
        st.error("Não há dados disponíveis para gerar o gráfico")
        fig = go.Figure()
        fig.update_layout(title="Sem dados disponíveis")
        return fig

    # Transformação dos dados para plotagem
    df_long = pd.melt(
        convenios_completo,
        id_vars='conv_prod',
        value_vars=['comissao_paga', 'gasto_total'],
        var_name='Tipo',
        value_name='Valor'
    )

    # Título baseado no tipo de análise
    titulo = "Gasto e Comissão por Campanha" if analisar_campanha else "Gasto e Comissão por Convênio-Produto"
    y_label = "Campanha" if analisar_campanha else "Convênio - Produto"

    fig = px.bar(
        df_long,
        x='Valor',
        y='conv_prod',
        color='Tipo',
        barmode='group',
        labels={'conv_prod': y_label, 'Valor': 'Valor (R$)', 'Tipo': 'Tipo de Valor'},
        text='Valor',
        title=titulo
    )

    fig.update_traces(
        texttemplate='R$ %{x:,.2f}',
        textposition='outside',
        textfont=dict(size=18, color='white')
    )

    fig.update_layout(
        height=800,
        width=1560,
        xaxis_tickangle=-50,
        bargap=0.2,
        bargroupgap=0.2,
        xaxis=dict(
            tickfont=dict(size=18),
            title='Valor (R$)'
        ),
        yaxis=dict(
            tickfont=dict(size=20),
            title=''
        )
    )

    return fig

# GRAFICO 2 - QUANTIDADE DE LEADS POR DIA (POR CADA ORIGEM)
def leads_por_origem(df_filtrado, df_gasto, top_n=5):
    # Agrupar por data e origem
    gerado_convenios = df_filtrado.groupby(['data', 'origem'])['id'].size().reset_index()

    # Top N origens por dia
    top_origem = gerado_convenios.groupby('data').apply(
        lambda x: x.nlargest(top_n, 'id')
    ).reset_index(drop=True)

    # Total por dia
    total_diario = gerado_convenios.groupby('data')['id'].sum().reset_index()
    total_diario['origem'] = 'Total Geral'

    # Junta os dados
    dados_com_total = pd.concat([top_origem, total_diario], ignore_index=True)

    # Dicionário com cores fixas
    cores_personalizadas = {
        'HYPERFLOW': '#3454D1',    # azul mais forte e vibrante
        'App': '#27AE60',          # verde esmeralda intenso
        'SMS': '#9B59B6',          # roxo mais suave e bem visível no fundo escuro
        'RCS': '#33658A',          # azul claro vibrante
        'URA': '#E4FDE1',          # dourado intenso, contraste bom no fundo escuro
        'Intercom': '#E67E22',     # laranja vibrante
        'Resgate': '#55DDE0',      # vermelho forte, destaca bem no fundo escuro
        'Total Geral': '#D32F2F',  # dourado para destaque
        'Duplicacao': '#D1345B',   # cor suave, mas visível no fundo escuro
        'BASE CLIENTES': '#7F8C8D', # cinza mais escuro para um contraste suave
        'Whatsapp Grow': '#16A085' # verde suave e claro, mas visível no fundo escuro
    }


    # Gráfico de linha
    fig = px.line(
        dados_com_total,
        x='data',
        y='id',
        color='origem',
        title=f'',
        labels={'id': 'Quantidade', 'data': 'Data'},
        markers=True,
        text='id',
        color_discrete_map=cores_personalizadas
    )

    # Estilo das linhas
    fig.for_each_trace(
        lambda t: t.update(line=dict(width=4)) if t.name == 'Total Geral'
        else t.update(line=dict(width=2, dash='dot'))
    )

    # Posiciona os textos
    fig.update_traces(textposition='top center', textfont_size=16)

    fig.update_layout(
        height=650,
        width=1300,
        xaxis_tickangle=-45,
        legend_title='Origem',
        xaxis=dict(title='Data'),
        yaxis=dict(title='Quantidade de Convênios'),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )

    return fig

# GRAFICO 3: FUNIL
def funil_de_etapas(df_filtrado, df_gasto):
    etapas = {
        'LEAD': df_filtrado['data'].notna().sum(),
        'NEGOCIAÇÃO': df_filtrado['data_negociacao'].notna().sum(),
        'CONTRATAÇÃO': df_filtrado['data_contratacao'].notna().sum(),
        'PAGO': df_filtrado.query('etapa == "PAGO"').shape[0],
        'PERDA': df_filtrado['data_perda'].notna().sum()
    }

    df_funil = pd.DataFrame({
        'etapa': list(etapas.keys()),
        'quantidade': list(etapas.values())
    })

    # % em relação ao início
    total_inicio = df_funil.loc[0, 'quantidade'] if df_funil.loc[0, 'quantidade'] > 0 else 1
    df_funil['pct_inicio'] = df_funil['quantidade'] / total_inicio * 100

    # % em relação à etapa anterior (exceto para perda)
    pct_anterior = [None]  # primeira etapa não tem anterior
    for i in range(1, len(df_funil) - 1):  # Excluímos a última etapa (PERDA)
        anterior = df_funil.loc[i - 1, 'quantidade']
        atual = df_funil.loc[i, 'quantidade']
        pct = (atual / anterior * 100) if anterior > 0 else 0
        pct_anterior.append(pct)
    
    # A etapa PERDA usa o total (LEAD) como referência
    pct_perda = (df_funil.loc[4, 'quantidade'] / total_inicio * 100) if total_inicio > 0 else 0
    pct_anterior.append(pct_perda)
    
    df_funil['pct_anterior'] = pct_anterior

    # Texto visível no gráfico
    df_funil['texto'] = df_funil.apply(
        lambda row: f"{row['quantidade']}\n({row['pct_anterior']:.1f}%)" if pd.notna(row['pct_anterior']) else str(row['quantidade']),
        axis=1
    )
    
    # Alterando especificamente o texto para PERDA para indicar que é em relação ao total
    perda_idx = df_funil[df_funil['etapa'] == 'PERDA'].index[0]
    df_funil.loc[perda_idx, 'texto'] = f"{df_funil.loc[perda_idx, 'quantidade']}\n({df_funil.loc[perda_idx, 'pct_anterior']:.1f}% do total)"

    # Criar o gráfico
    fig = px.funnel(
        df_funil,
        x='quantidade',
        y='etapa',
        text='texto',
        labels={'etapa': 'Etapa do Funil', 'quantidade': 'Leads'},
        color_discrete_sequence=["#00BFFF", "#1E90FF", "#6495ED", "#7B68EE", "#8A2BE2"],
        hover_data={
            'quantidade': True,
            'pct_inicio': ':.1f',
            'pct_anterior': ':.1f',
            'etapa': False,
            'texto': False
        }
    )

    # Atualiza estilo
    fig.update_traces(
        textposition='auto',
        textfont_size=28,
        marker_line_width=1,
        marker_line_color='white'
    )

    fig.update_layout(
        title='5. Funil de Etapas do Hubspot',
        xaxis_title='',
        yaxis_title='Quantidade',
        legend_orientation='h',
        legend_y=1.0,
        xaxis_tickfont_size=14,
        height=800,
        width=1300,
        margin=dict(l=30, r=10, t=40, b=0)
    )

    return fig

# GRAFICO 4: COHORT DINAMICO
def preprocessar_datas(df, colunas_data):
    for col in colunas_data:
        df[col] = pd.to_datetime(df[col], errors='coerce')
    return df

def calcular_cohort(df, coluna_evento):
    df['cohort'] = df['data'].dt.date
    df['dias_ate_evento'] = (df[coluna_evento] - df['data']).dt.days
    return df.dropna(subset=['dias_ate_evento'])

def calcular_metricas_cohort(df_cohort, df_eventos):
    cohort_counts = df_eventos.groupby(['cohort', 'dias_ate_evento']).size().reset_index(name='quantidade')
    cohort_sizes = df_cohort.groupby('cohort').size().to_dict()
    cohort_counts['tamanho_cohort'] = cohort_counts['cohort'].map(cohort_sizes)
    cohort_counts['taxa'] = (cohort_counts['quantidade'] / cohort_counts['tamanho_cohort']) * 100
    cohort_counts['cohort_str'] = (
        cohort_counts['cohort'].astype(str) +
        " (n=" + cohort_counts['tamanho_cohort'].astype(str) + ")"
    )
    return cohort_counts

def gerar_heatmap(cohort_counts, evento_escolhido):
    heatmap_data = cohort_counts.pivot(
        index='cohort_str',
        columns='dias_ate_evento',
        values='taxa'
    ).fillna(0)

    heatmap_data = heatmap_data.sort_index(ascending=False)
    heatmap_data = heatmap_data[sorted(heatmap_data.columns)]

    fig = px.imshow(
        heatmap_data,
        labels=dict(
            x=f"Dias até {evento_escolhido.lower()}",
            y="Data de entrada (cohort)",
            color="Conversão (%)"
        ),
        color_continuous_scale="Cividis",
        aspect="auto",
        text_auto=".1f"
    )

    fig.update_layout(
        title=f"Cohort por {evento_escolhido}",
        title_font_size=22,
        height=600,
        font=dict(size=22),
        xaxis=dict(
            title=f"Dias até {evento_escolhido.lower()}",
            title_font=dict(size=16),
            tickfont=dict(size=12)
        ),
        yaxis=dict(
            title="Data de entrada (cohort)",
            title_font=dict(size=16),
            tickfont=dict(size=12)
        ),
        coloraxis_colorbar=dict(
            title=dict(
                text="Conversão (%)",
                font=dict(size=14)
            ),
            tickfont=dict(size=12),
            ticksuffix="%"
        )
    )


    return fig

def cohort_dinamico(df_filtrado, df_gasto=None):
    df_cohort = df_filtrado.copy()
    colunas_data = ['data', 'data_negociacao', 'data_contratacao', 'data_pago', 'data_perda']
    df_cohort = preprocessar_datas(df_cohort, colunas_data)

    opcoes_evento = {
        "Pagamento": "data_pago",
        "Perda": "data_perda",
        "Negociação": "data_negociacao",
        "Contratação": "data_contratacao"
    }

    evento_escolhido = st.selectbox("Selecione o evento para análise de cohort:", list(opcoes_evento.keys()))
    coluna_evento = opcoes_evento[evento_escolhido]

    df_eventos = calcular_cohort(df_cohort, coluna_evento)
    cohort_counts = calcular_metricas_cohort(df_cohort, df_eventos)
    fig = gerar_heatmap(cohort_counts, evento_escolhido)

    return fig


# GRAFICO 5: CPL
def cpl_convenios_produto(df_filtrado, df_gasto=None, top_n=5, maiores=True, df_gasto_tag=None, analisar_campanha=False, filtros=None, data_inicio=None, data_fim=None):
    if analisar_campanha and df_gasto_tag is not None:
        # Opção para aplicar ou não os filtros
        col1, col2 = st.columns(2)
        with col2:
            incluir_fora_periodo = st.checkbox("Incluir tags fora do período", value=False, key="incluir_fora_periodo_cpl")
        
        # Criar cópia de trabalho
        df_gasto_tag_work = df_gasto_tag.copy()
        df_filtrado_work = df_filtrado.copy()
        
        if not incluir_fora_periodo and 'data_da_tag' in df_gasto_tag_work.columns and data_inicio is not None and data_fim is not None:
            df_gasto_tag_work = df_gasto_tag_work[
                (df_gasto_tag_work['data_da_tag'] >= data_inicio) & 
                (df_gasto_tag_work['data_da_tag'] <= data_fim)
            ]
        
        # Verificar se ainda temos dados
        if df_gasto_tag_work.empty:
            st.warning("O arquivo de campanhas não tem dados após a aplicação dos filtros. Experimente desmarcar algumas opções de filtro.")
            # Usar todos os dados como fallback
            df_gasto_tag_work = df_gasto_tag.copy()
        
        
        
        if not incluir_fora_periodo and 'data_da_tag' in df_filtrado_work.columns and data_inicio is not None and data_fim is not None:
            df_filtrado_work = df_filtrado_work[
                (df_filtrado_work['data_da_tag'] >= data_inicio) & 
                (df_filtrado_work['data_da_tag'] <= data_fim)
            ]
        
        # Análise por campanha
        gasto_campanhas = df_gasto_tag_work.groupby(['Tag'])['Custo Convertido'].sum().reset_index(name='gasto_total')
        clientes_campanha = df_filtrado_work.groupby(['tag_campanha']).size().reset_index(name='clientes')
        
        # Renomear para correspondência exata
        gasto_campanhas.rename(columns={'Tag': 'tag_campanha'}, inplace=True)
        
        # Mesclagem exata
        campanhas_cpl = pd.merge(
            gasto_campanhas,
            clientes_campanha,
            on='tag_campanha',
            how='left'
        )
        
        # Tratar NaNs
        campanhas_cpl['clientes'] = campanhas_cpl['clientes'].fillna(1)  # Usar 1 como mínimo para evitar divisão por zero
        
        # Calcular CPL
        campanhas_cpl['CPL'] = campanhas_cpl['gasto_total'] / campanhas_cpl['clientes']
        
        # Remove CPLs zero ou negativos
        campanhas_cpl = campanhas_cpl[campanhas_cpl['CPL'] > 0]
        
        # Ordenar e limitar
        campanhas_cpl = campanhas_cpl.sort_values(by='CPL', ascending=not maiores).head(top_n)
        
        # Preparar para exibição - IMPORTANTE: usar tag_campanha para o eixo Y
        df_cpl = campanhas_cpl
        df_cpl['identificador'] = df_cpl['tag_campanha']
            
        titulo = "CPL por Campanha"
        y_label = "Campanha"
    else:
        # Análise original por Convênio/Produto
        gasto_convenios = df_gasto.groupby(['Convênio', 'Produto'])['Valor Gasto'].sum().reset_index(name='gasto_total')
        clientes_convenio = df_filtrado.groupby(['convenio_acronimo', 'produto']).size().reset_index(name='clientes')

        gasto_convenios.rename(columns={
            'Convênio': 'convenio_acronimo',
            'Produto': 'produto',
        }, inplace=True)

        convenios_cac = pd.merge(
            gasto_convenios,
            clientes_convenio,
            on=['convenio_acronimo', 'produto'],
            how='outer'
        )

        convenios_cac[['gasto_total', 'clientes']] = convenios_cac[['gasto_total', 'clientes']].fillna(0)
        convenios_cac = convenios_cac[convenios_cac['clientes'] > 0]

        convenios_cac['CPL'] = convenios_cac['gasto_total'] / convenios_cac['clientes']

            # Remove CPLs zero ou negativos
        convenios_cac = convenios_cac[convenios_cac['CPL'] > 0]

        convenios_cac = convenios_cac.sort_values(by='CPL', ascending=not maiores).head(top_n)
        convenios_cac['identificador'] = convenios_cac['convenio_acronimo'] + ' - ' + convenios_cac['produto']
            
        df_cpl = convenios_cac
        titulo = "CPL por Convênio e Produto"
        y_label = "Convênio - Produto"

        # Verificar se temos dados
        if 'df_cpl' not in locals() or df_cpl.empty:
            st.error("Não há dados para exibir o CPL")
            fig = go.Figure()
            fig.update_layout(
                title="Sem dados disponíveis para exibição de CPL",
                height=400
            )
            return fig

    fig = px.bar(
        df_cpl,
        x='CPL',
        y='identificador',
        orientation='h',
        text='CPL',
        labels={'CPL': 'CPL (R$)', 'identificador': y_label},
        title=titulo
    )

    fig.update_traces(
        texttemplate='R$ %{text:.2f}',
        textposition='outside'
    )

    fig.update_layout(
        height=600,
        xaxis_title="CPL (R$)",
        yaxis_title="",
        font=dict(size=14),
        xaxis_tickprefix='R$ '
    )

    return fig

    
# GRAFICO 6: ROI DOS CONVENIOS
def roi_por_convenio_produto(df_filtrado, df_gasto, top_n=5, melhores=True):
    gasto_convenios = df_gasto.groupby(['Convênio', 'Produto'])['Valor Gasto'].sum().reset_index(name='gasto_total')
    comissao_convenios = df_filtrado.loc[df_filtrado['etapa'] == 'PAGO'].groupby(['convenio_acronimo', 'produto'])['comissao_paga'].sum().reset_index(name='comissao_paga')

    gasto_convenios.rename(columns={
        'Convênio': 'convenio_acronimo',
        'Produto': 'produto',
    }, inplace=True)

    convenios_roi = pd.merge(
        gasto_convenios,
        comissao_convenios,
        on=['convenio_acronimo', 'produto'],
        how='outer'
    )

    convenios_roi[['gasto_total', 'comissao_paga']] = convenios_roi[['gasto_total', 'comissao_paga']].fillna(0)
    convenios_roi = convenios_roi[convenios_roi['gasto_total'] > 0]

    convenios_roi['ROI (%)'] = ((convenios_roi['comissao_paga'] - convenios_roi['gasto_total']) / convenios_roi['gasto_total']) * 100

    # Define ordenação baseada no seletor
    convenios_roi = convenios_roi.sort_values(by='ROI (%)', ascending=not melhores).head(top_n)

    convenios_roi['conv_prod'] = convenios_roi['convenio_acronimo'] + ' - ' + convenios_roi['produto']

    fig = px.bar(
        convenios_roi,
        x='ROI (%)',
        y='conv_prod',
        orientation='h',
        text='ROI (%)',
        color='ROI (%)',
        color_continuous_scale='Viridis',
        labels={'ROI (%)': 'ROI (%)', 'conv_prod': 'Convênio - Produto'},
    )

    fig.update_traces(
        texttemplate='%{text:.2f}%',
        textposition='outside'
    )

    fig.update_layout(
        title="ROI por Convênio e Produto",
        height=600,
        xaxis_title="ROI (%)",
        yaxis_title="",
        font=dict(size=14),
        yaxis=dict(categoryorder='total ascending' if melhores else 'total descending')
    )

    return fig


# Grafico 7: Quantidade de leads gerados por convênio
def quantidade_leads_por_convenio(df_filtrado, df_gasto, top_n=5, ordem="maiores"):

    mapa_cores = {
        "Novo": "#00E1FF",
        "Cartão": "#FFB800",
        "Benefício": "#00FF85",
        "Benefício e Cartão": "#FF3D6A",
        "Port": "#C266FF",
        "CDX": "#FF6B00",
        "CP": "#66FF00",
    }

    # Total de leads por convênio
    quantidade = df_filtrado.groupby(['convenio_acronimo']).size().reset_index(name='quantidade_total')
    quantidade = quantidade[quantidade['quantidade_total'] > 0]  # Remove os que têm 0

    # Ordena pela ordem escolhida
    ascending = ordem == "menores"
    top_convenios = quantidade.sort_values(by='quantidade_total', ascending=ascending).head(top_n)['convenio_acronimo']

    # Leads por convênio + produto
    grouped = df_filtrado.groupby(['convenio_acronimo', 'produto']).size().reset_index(name='quantidade')
    grouped = pd.merge(quantidade, grouped, on='convenio_acronimo', how='left')

    # Filtra só os convênios desejados
    grouped = grouped[grouped['convenio_acronimo'].isin(top_convenios)]
    grouped = grouped.sort_values(by='quantidade_total', ascending=ascending)

    graf1 = px.bar(
        grouped,
        x='quantidade',
        y='convenio_acronimo',
        color='produto',
        title='Leads Gerados por Convênio',
        color_discrete_map=mapa_cores
    )

    graf1.update_layout(
        title='1. Leads Gerados por Convênio',
        xaxis_title='Quantidade',
        font=dict(size=16),
        yaxis_title='Convênio',
        legend_title='Produto',
        xaxis_tickfont_size=12,
        height=550,
        width=1300,
        margin=dict(l=0, r=0, t=30, b=0)
    )

    return graf1



# Grafico 8: ROI por Canal
def roi_por_canal(df_filtrado, df_gasto):
    df_pago = df_filtrado[df_filtrado['etapa'] == 'PAGO']
    
    # Gasto por canal
    gasto_canal = df_gasto.groupby(['Canal'])['Valor Gasto'].sum().reset_index(name='gasto_canal')
    gasto_canal.rename(columns={'Canal': 'origem'}, inplace=True)
    
    # Comissão gerada por canal
    gerado_canal = df_pago.groupby(['origem'])['comissao_paga'].sum().reset_index(name='comissao_paga')
    
    # Merge
    df_roi = pd.merge(gasto_canal, gerado_canal, on='origem', how='outer')
    
    # Preencher NaNs
    df_roi[['gasto_canal', 'comissao_paga']] = df_roi[['gasto_canal', 'comissao_paga']].fillna(0)
    
    # Filtrar canais com gasto > 0
    df_roi = df_roi[df_roi['gasto_canal'] > 0]
    
    # Calcular ROI
    df_roi['ROI (%)'] = ((df_roi['comissao_paga'] - df_roi['gasto_canal']) / df_roi['gasto_canal']) * 100
    
    # Gráfico
    fig = px.bar(
        df_roi,
        x='ROI (%)',
        y='origem',
        orientation='h',
        text='ROI (%)',
        color='ROI (%)',
        color_continuous_scale='Viridis',
        labels={'ROI (%)': 'ROI (%)', 'origem': 'Canal'}
    )

    fig.update_traces(texttemplate='%{text:.2f}%', textposition='outside', textfont_size=18)
    
    fig.update_layout(
        title='ROI por Canal (Origem)',
        height=600,
        width=400,
        xaxis_title='ROI (%)',
        yaxis_title='',
        font=dict(size=14)
    )

    return fig


def gasto_vs_comissao_por_canal(df_filtrado, df_gasto):
    df_pago = df_filtrado[df_filtrado['etapa'] == 'PAGO']

    # Gasto por canal
    gasto_canal = df_gasto.groupby(['Canal'])['Valor Gasto'].sum().reset_index(name='gasto')
    gasto_canal.rename(columns={'Canal': 'origem'}, inplace=True)

    # Comissão gerada por canal
    comissao_canal = df_pago.groupby('origem')['comissao_paga'].sum().reset_index(name='comissao')

    # Merge
    df_comparativo = pd.merge(gasto_canal, comissao_canal, on='origem', how='outer').fillna(0)
    df_comparativo = df_comparativo[df_comparativo['gasto'] > 0]

    # Dados para gráfico de barras agrupadas
    df_melt = df_comparativo.melt(id_vars='origem', value_vars=['gasto', 'comissao'],
                                  var_name='Tipo', value_name='Valor')

    fig = px.bar(
        df_melt,
        x='origem',
        y='Valor',
        color='Tipo',
        barmode='group',
        text='Valor',
        color_discrete_map={'gasto': '#FF5733', 'comissao': '#33FF57'},
        labels={'Valor': 'R$', 'origem': 'Canal'}
    )

    fig.update_traces(texttemplate='R$ %{text:.2f}', textposition='outside', textfont_size=18)

    fig.update_layout(
        title='Gasto x Comissão por Canal',
        height=600,
        width=450,
        font=dict(size=14),
        xaxis_title='Valor (R$)',
        yaxis_title='',
    )

    return fig

# Vazamento do funil
def perdas_por_etapa(df_filtrado):
    df_perdidos = df_filtrado[df_filtrado['data_perda'].notna()].copy()

    def classificar_etapa_perda(row):
        if pd.isna(row['data_negociacao']):
            return 'LEAD'
        elif pd.isna(row['data_contratacao']):
            return 'NEGOCIAÇÃO'
        elif pd.isna(row['data_pago']):
            return 'CONTRATAÇÃO'
        else:
            return 'PAGO'

    df_perdidos['etapa_origem'] = df_perdidos.apply(classificar_etapa_perda, axis=1)

    perdas = df_perdidos['etapa_origem'].value_counts().reset_index()
    perdas.columns = ['etapa_origem', 'quantidade']

    # Gráfico
    fig = px.bar(
        perdas,
        x='quantidade',
        y='etapa_origem',
        orientation='h',
        text='quantidade',
        labels={'quantidade': 'Leads Perdidos', 'etapa_origem': 'Etapa em que saíram'},
        color='etapa_origem',
        color_discrete_sequence=px.colors.sequential.Reds
    )

    fig.update_traces(textposition='outside', textfont_size=16)
    fig.update_layout(
        title='Perdas por Etapa de Origem',
        height=500,
        xaxis_title='Quantidade de Leads Perdidos',
        yaxis_title='',
        font=dict(size=14),
        showlegend=False
    )

    return fig