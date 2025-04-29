import streamlit as st
import pandas as pd
import locale
import limpeza
import plotly.express as px
import plotly.graph_objects as go
from datetime import timedelta
from graficos import aplicar_estilo_kpi, exibir_kpis
import re

# Configurações iniciais
st.set_page_config(layout="wide")
st.title('Analisar Geração de Leads')

# Localidade para moeda
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    locale.setlocale(locale.LC_ALL, 'C.UTF-8')

# Função de cache para o carregamento de arquivos
def carregar_arquivos(arquivos):
    df, df_gasto, df_gasto_tag = None, None, None
    for arquivo in arquivos:
        nome_arquivo = arquivo.name.lower()
        
        # Dá pra melhorar essa identificação dos arquivos 
        if "hubspot" in nome_arquivo:
            df = pd.read_csv(arquivo)
            df = limpeza.tratar_arquivo_hubspot(df)
        elif "gasto_tag" in nome_arquivo:
            df_gasto_tag = pd.read_csv(arquivo)
            
            # Verificar se contém as colunas necessárias
            colunas_necessarias = ['Tag', 'Custo Convertido']
            for coluna in colunas_necessarias:
                if coluna not in df_gasto_tag.columns:
                    st.warning(f"Coluna '{coluna}' não encontrada no arquivo gasto_tag")            
            
        elif "gasto" in nome_arquivo and "gasto_tag" not in nome_arquivo:
            df_gasto = pd.read_csv(arquivo)
            df_gasto = limpeza.tratar_arquivo_pagos(df_gasto)
        
    return df, df_gasto, df_gasto_tag

# Uploads
st.sidebar.header("Upload dos Arquivos")
arquivos = st.sidebar.file_uploader("Envie os arquivos CSV", type="csv", accept_multiple_files=True)
considerar_dias_uteis = st.sidebar.checkbox("Considerar apenas dias úteis", value=False)

df, df_gasto, df_gasto_tag = None, None, None

if arquivos:
    df, df_gasto, df_gasto_tag = carregar_arquivos(arquivos)

if df is not None and df_gasto is not None:
    df_filtrado = df.copy()
    df_gasto_original = df_gasto.copy()
    
    st.sidebar.title("Filtros")

    def multiselect_com_default(label, opcoes):
        with st.sidebar.expander(label):
            selecionadas = st.multiselect(label, opcoes)
            return selecionadas if selecionadas else list(opcoes)

    filtros = {
        'equipe': multiselect_com_default("Equipe", df['equipe'].unique()),
        'produto': multiselect_com_default("Produto", df['produto'].unique()),
        'convenio_acronimo': multiselect_com_default("Convênio", df['convenio_acronimo'].unique()),
        'etapa': multiselect_com_default("Etapa", df['etapa'].unique()),
        'origem': multiselect_com_default("Canal", df['origem'].unique())
    }

    with st.sidebar.expander('Filtro Data'):
        data_inicio = st.date_input('Data de início', df['data'].min())
        data_fim = st.date_input('Data de fim', df['data'].max())

    df_filtrado = df[
        (df['data'] >= data_inicio) & (df['data'] <= data_fim) &
        (df['equipe'].isin(filtros['equipe'])) &
        (df['produto'].isin(filtros['produto'])) &
        (df['convenio_acronimo'].isin(filtros['convenio_acronimo'])) &
        (df['etapa'].isin(filtros['etapa'])) &
        (df['origem'].isin(filtros['origem']))
    ]


    df_gasto = df_gasto[
        (df_gasto['data'] >= data_inicio) & (df_gasto['data'] <= data_fim) &
        (df_gasto['Convênio'].isin(filtros['convenio_acronimo'])) &
        (df_gasto['Produto'].isin(filtros['produto'])) &
        (df_gasto['Equipe'].isin(filtros['equipe'])) &
        (df_gasto['Canal'].isin(filtros['origem']))
    ]

    if df_gasto_tag is not None:
        # Melhorar
        if 'data' not in df_gasto_tag.columns:
            try:
                df_gasto_tag['data'] = pd.to_datetime(df_gasto_tag['Data Formatada'], errors='coerce', dayfirst=True).dt.date
            except Exception as e:
                st.error(f"Erro ao converter Data Formatada: {e}")
            
        # Extrair a data da própria tag usando regex
        def extract_date_from_tag(tag):
            match = re.search(r'(\d{2})(\d{2})(\d{4})', str(tag)) 
            if match:
                dia, mes, ano = match.groups()
                try:
                    return pd.Timestamp(f"{ano}-{mes}-{dia}").date()
                except:
                    return None
            return None

        
        # Adicionar coluna com a data extraída da tag
        df_gasto_tag['data_da_tag'] = df_gasto_tag['Tag'].apply(extract_date_from_tag)
        
        # Converter coluna 'Custo Convertido' para numérico
        if 'Custo Convertido' in df_gasto_tag.columns:
            # Converter para string primeiro para garantir uniformidade
            df_gasto_tag['Custo Convertido'] = df_gasto_tag['Custo Convertido'].astype(str)
            
            # Remover caracteres não numéricos exceto ponto e vírgula
            df_gasto_tag['Custo Convertido'] = df_gasto_tag['Custo Convertido'].str.replace(r'[^\d,.]', '', regex=True)
            
            # Substituir vírgula por ponto para usar no formato numérico
            df_gasto_tag['Custo Convertido'] = df_gasto_tag['Custo Convertido'].str.replace(',', '.') # Formatação final na plotagem ainda está com problemas. Plotly está forçando a formatação?
            
            # Converter para float
            df_gasto_tag['Custo Convertido'] = pd.to_numeric(df_gasto_tag['Custo Convertido'], errors='coerce').fillna(0)
            
        
        # Adicionar também a mesma extração de data para df_filtrado
        if 'tag_campanha' in df_filtrado.columns:
            df_filtrado['data_da_tag'] = df_filtrado['tag_campanha'].apply(extract_date_from_tag)
        
        # Extrair a equipe da tag com mapeamento
        equipe_mapping = {
            'csativacao': 'Cs Ativacao',
            'csapp': 'Cs App', 
            'cscdx': 'Cs Cdx', 
            'cscp': 'Cs Cp', 
            'outbound': 'Sales',
            'csport': 'Cs Port'
        }
        
        # Função para extrair equipe da tag
        def extract_team(tag):
            tag = str(tag).lower()
            parts = tag.split('_')
            if len(parts) > 1:
                team_code = parts[-1]
                for code, team in equipe_mapping.items():
                    if code in team_code:
                        return team
            return None

        
        # Aplicar a extração de equipe
        df_gasto_tag['equipe_da_tag'] = df_gasto_tag['Tag'].apply(extract_team)
        if 'tag_campanha' in df_filtrado.columns:
            df_filtrado['equipe_da_tag'] = df_filtrado['tag_campanha'].apply(extract_team)
        
        
        # Aplicar filtro de equipe baseado na equipe extraída da tag
        if filtros['equipe']:
            equipe_filter = df_gasto_tag['equipe_da_tag'].isin(filtros['equipe'])
            df_gasto_tag = df_gasto_tag[equipe_filter]
        
        # Verificar se ainda há dados -- manter por enquanto
        if df_gasto_tag.empty:
            st.warning("Todos os dados do arquivo gasto_tag foram filtrados! Verificar compatibilidade de valores.")

    df_filtrado = limpeza.filtrar_dias_uteis(df_filtrado, data_inicio, data_fim, considerar_dias_uteis)
    df_gasto = limpeza.filtrar_dias_uteis(df_gasto, data_inicio, data_fim, considerar_dias_uteis)
    if df_gasto_tag is not None:
        df_gasto_tag = limpeza.filtrar_dias_uteis(df_gasto_tag, data_inicio, data_fim, considerar_dias_uteis)

    
    custos_unitarios = {'SMS': 0.048, 'RCS': 0.105, 'HYPERFLOW': 0.047, 'Whatsapp': 0.046}
    gastos = (
        df_gasto.groupby(['Equipe', 'Convênio', 'Produto', 'Canal'])['Quantidade']
        .sum()
        .reset_index()
    )
    gastos['valor_pago'] = gastos['Canal'].map(custos_unitarios) * gastos['Quantidade']
    gastos['valor_pago'] = gastos['valor_pago'].round(2)

    # Exibir os KPIs
    aplicar_estilo_kpi()
    colunas = st.columns(6)
    exibir_kpis(df, df_filtrado, gastos, df_gasto_original, data_inicio, data_fim, considerar_dias_uteis, colunas)



    # GRAFICO 1 - GASTOS POR CADA CONVENIO/PRODUTO
    from graficos import grafico_gasto_convenio_produto
    with st.expander("Gasto por Convênio e Produto"):
        col1, col2 = st.columns([3, 2])
        with col1:
            top_n = st.slider("Quantos convênios deseja visualizar?", min_value=5, max_value=40, value=5, step=1, key=1)
        with col2:
            tipo_analise = st.radio("Tipo de análise:", ["Analisar por Produto", "Analisar por Campanha"], key="graf1_analise", horizontal=True)
        
        analisar_campanha = tipo_analise == "Analisar por Campanha"
        fig = grafico_gasto_convenio_produto(df_filtrado, df_gasto, top_n, df_gasto_tag, analisar_campanha, filtros, data_inicio, data_fim)
        st.plotly_chart(fig, key=f'graf1')
    
    

    # GRAFICO 2 - QUANTIDADE DE LEADS POR ORIGEM
    from graficos import leads_por_origem
    with st.expander("Quantidade de Leads por Origem"):
        top_n = st.slider("Quantos convênios deseja visualizar?", min_value=5, max_value=40, value=5, step=1, key=2)
        fig = leads_por_origem(df_filtrado, df_gasto, top_n)
        st.plotly_chart(fig, key=f'graf2')

    # GRAFICO 3 - FUNIL DE ETAPAS
    from graficos import funil_de_etapas
    with st.expander("Funil de Geração de leads por Etapa"):
        fig = funil_de_etapas(df_filtrado, df_gasto)
        st.plotly_chart(fig, key=f'graf3')

    # GRAFICO 4 - COHORT DINAMICO
    from graficos import cohort_dinamico
    with st.expander("Cohort dinâmico para Etapas"):
        top_n = st.slider("Quantos convênios deseja visualizar?", min_value=5, max_value=40, value=5, step=1, key=3)
        fig = cohort_dinamico(df_filtrado, df_gasto)
        st.plotly_chart(fig, use_container_width=True)

    # GRAFICO 5 - CPL por Convênio/Produto
    from graficos import cpl_convenios_produto
    with st.expander("Custo por Lead (Convenio-Produto)"):
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            top_n = st.slider("Quantos convênios deseja visualizar?", min_value=5, max_value=40, value=5, step=1, key=4)
        with col2:
            tipo_cpl = st.selectbox("Tipo de CPL que deseja visualizar:", ["Maiores CPLs", "Menores CPLs"], key="cpl_tipo")
        with col3:
            tipo_analise = st.radio("Tipo de análise:", ["Analisar por Produto", "Analisar por Campanha"], key="cpl_analise", horizontal=True)

        maiores = tipo_cpl == "Maiores CPLs"
        analisar_campanha = tipo_analise == "Analisar por Campanha"
        fig = cpl_convenios_produto(df_filtrado, df_gasto, top_n=top_n, maiores=maiores, df_gasto_tag=df_gasto_tag, analisar_campanha=analisar_campanha, filtros=filtros, data_inicio=data_inicio, data_fim=data_fim)
        st.plotly_chart(fig)

    # GRAFICO 6 - ROI por Convênio/Produto
    from graficos import roi_por_convenio_produto
    with st.expander("ROI por Convênio/Produto"):
        top_n = st.slider("Quantos convênios deseja visualizar?", min_value=5, max_value=40, value=5, step=1, key=5)
        tipo_roi = st.selectbox("Tipo de ROI que deseja visualizar:", ["Melhores ROIs", "Piores ROIs"], key="roi_tipo")
        
        melhores = tipo_roi == "Melhores ROIs"
        fig = roi_por_convenio_produto(df_filtrado, df_gasto, top_n=top_n, melhores=melhores)
        st.plotly_chart(fig)

    from graficos import quantidade_leads_por_convenio
    with st.expander("Quantidade de Leads por Convênio"):
        col1, col2 = st.columns([2, 1])
        with col1:
            top_n = st.slider("Quantos convênios deseja visualizar?", min_value=5, max_value=40, value=5, step=1, key=6)
        with col2:
            ordem = st.selectbox("Ordenar por:", options=["maiores", "menores"], index=0, key=61)
        
        fig = quantidade_leads_por_convenio(df_filtrado, df_gasto, top_n=top_n, ordem=ordem)
        st.plotly_chart(fig)


    from graficos import roi_por_canal, gasto_vs_comissao_por_canal
    with st.expander("Análise de ROI e Gasto por Canal"):
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Gasto x Comissão por Canal")
            fig_comparativo = gasto_vs_comissao_por_canal(df_filtrado, df_gasto)
            st.plotly_chart(fig_comparativo, use_container_width=True)
        
        with col2:
            st.subheader("ROI por Canal")
            fig_roi = roi_por_canal(df_filtrado, df_gasto)
            st.plotly_chart(fig_roi, use_container_width=True)
        

    from graficos import perdas_por_etapa
    with st.expander("Perdas por Etapa"):
        fig = perdas_por_etapa(df_filtrado)
        st.plotly_chart(fig)