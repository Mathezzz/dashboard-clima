# -*- coding: utf-8 -*-
"""
Created on Tue Jul 29 17:51:47 2025

@author: ander
"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import streamlit as st
import plotly.express as px
import logging


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.debug("Inicializando código")

@st.cache_data(ttl=600)
def carregar_dados_sheet():
    # Carregar JSON a partir dos secrets
    service_account_info = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scopes=[
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ])
    
    client = gspread.authorize(creds)
    sheet = client.open("registro_tempo").worksheet("Clima")
    df = pd.DataFrame(sheet.get_all_records())
    return df

# ------------------- STREAMLIT DASH -------------------
st.set_page_config(
    page_title="Dashboard Clima",
    page_icon="🌡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)
st.title("🌡️ Dashboard de Clima - Capitais do Brasil")

logger.debug("Consulta dos dados na API GCP")
df = carregar_dados_sheet()
logger.debug("Dados carregados, tabela: {}".format(df.shape))

logger.debug("Tratamento dos dados")
# -------------- ETL rápido de quebra galho -----------------------------------
df['Data/Hora'] = pd.to_datetime(df['Data/Hora'], format="%d/%m/%Y %H:%M:%S")
# Criar a coluna de data e a de hora separadamente
df['Data'] = df['Data/Hora'].dt.date
df['Hora'] = df['Data/Hora'].dt.time
df['Hora_Str'] = df['Data/Hora'].dt.strftime('%H:%M')
df['Hora_Somente'] = df['Data/Hora'].dt.hour.astype(str) + 'h'

def corrigir_escala(col):
    # Se a média for maior que 100, provavelmente está sem a vírgula
    if df[col].mean() > 100:
        df[col] = df[col] / 100
    return df[col]

for col in ['Temperatura (ºc)', 'Sensação Térmica', 'Vento (m/s)']:
    df[col] = corrigir_escala(col)

# -----------------------------------------------------------------------------

# -------------------- Aplicação de filtros do Dashboard ----------------------
logger.debug("Gerando visualizações")
col1, col2 = st.columns(2)
# Filtro de cidade
cidades = ["Todas"] + sorted(df["Cidade"].unique().tolist())
with col1:
    cidade_selecionada = st.selectbox("Selecione uma cidade:", cidades)
# Filtro de data
df["Data"] = pd.to_datetime(df["Data"])
data_min = df["Data"].min().date()
data_max = df["Data"].max().date()
with col2:
    data_selecionada = st.date_input("Selecione a data", value=data_max, min_value=data_min, max_value=data_max)

# Filtrar todo o Dashboard pela data selecionada
df_filtrado = df[df["Data"].dt.date == data_selecionada]
if cidade_selecionada != "Todas":
    df_filtrado = df[df["Cidade"] == cidade_selecionada]

# Filtra último horário disponível
hora_mais_recente = df['Hora_Str'].max()
df_ultima_hora = df[df['Hora_Str'] == hora_mais_recente]

# ------------------------- Cards superiores ----------------------------------
st.markdown("# Métricas pelo Brasil:")
temp_media = df_filtrado['Temperatura (ºc)'].mean()
cidade_mais_quente = df.loc[df['Temperatura (ºc)'].idxmax()]
cidade_mais_fria = df.loc[df['Temperatura (ºc)'].idxmin()]
umidade_media = df_filtrado['Umidade (%)'].mean()
vento_medio = df_filtrado['Vento (m/s)'].mean()
clima_comum = df_filtrado['Descrição'].mode()[0]

with st.container(border=True):
    # Métricas da cidade selecionada:
    if cidade_selecionada == "Todas":
        st.markdown("# Geral")
    else:
        st.markdown("# {}".format(cidade_selecionada))
    # Layout em 3 colunas
    # col1, col2, col3 = st.columns(3)
    col1, col2, col3 = st.columns([1,1,2])
    
    
    with col1:
        st.metric("🌡️ Temp. Média (ºC)", f"{temp_media:.1f}")
        st.metric("🌬️ Vento Médio (m/s)", f"{vento_medio:.1f}")
    
    with col2:
        st.metric("🌥️ Clima Frequente", clima_comum)
        st.metric("💧 Umidade Média (%)", f"{umidade_media:.0f}%")

with col3:
    with st.container(border=True):
        st.metric("🔥 Maior Temperatura do Dia", f"{cidade_mais_quente['Cidade']} ({cidade_mais_quente['Temperatura (ºc)']}ºC - {cidade_mais_quente['Hora_Str']})")
        st.metric("❄️ Menor Temperatura do Dia", f"{cidade_mais_fria['Cidade']} ({cidade_mais_fria['Temperatura (ºc)']}ºC - {cidade_mais_fria['Hora_Str']})")
# -----------------------------------------------------------------------------




# --------------------------- Top Cidades -------------------------------------
col1, col2 = st.columns(2)
with col1:
    # ----------------------- Gráfico de temperatura por hora ---------------------
    with st.container(border=True):
        st.subheader("📈 Variação da Temperatura por Hora")
        # Filtra apenas os dados do dia mais recente
        dia_mais_recente = df["Data"].max()
        df_dia_recente = df[df["Data"] == dia_mais_recente]
        if cidade_selecionada == "Todas":
            df_media = df_dia_recente.groupby("Hora_Str")["Temperatura (ºc)"].mean().reset_index()
            fig = px.line(df_media, x="Hora_Str", y="Temperatura (ºc)",
                          markers=True, title="Temperatura Média por Hora (Todas as Cidades)")
            
            fig.update_layout(xaxis_title="Horas", yaxis_title="Temperatura (°C)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            df_cidade = df_dia_recente[df_dia_recente["Cidade"] == cidade_selecionada].sort_values("Hora")
            fig = px.line(df_cidade, x="Hora_Str", y="Temperatura (ºc)",
                          markers=True, title=f"Temperatura por Hora - {cidade_selecionada}")
            
            fig.update_layout(xaxis_title="Horas", yaxis_title="Temperatura (°C)")
            st.plotly_chart(fig, use_container_width=True)
    
# Top 5 cidades mais frias
with col2:
    with st.container(border=True):
        # Cidades mais quentes
        st.subheader("🔥 Top 5 Cidades Mais Quentes da Última Hora")
        top_quentes = df_ultima_hora.sort_values("Temperatura (ºc)", ascending=False).head(5)
        st.table(top_quentes[["Cidade", "Temperatura (ºc)", "Hora"]].reset_index(drop=True))
        
        # Cidades mais frias 
        st.subheader("❄️ Top 5 Cidades Mais Frias em Média")
        top_frias = df_ultima_hora.sort_values("Temperatura (ºc)", ascending=True).head(5)
        st.table(top_frias[["Cidade", "Temperatura (ºc)", "Hora"]].reset_index(drop=True))
        
# -----------------------------------------------------------------------------

# ----------------- Gráfico de Temperatura por Cidade decrescente -------------
with st.container(border=True):
    st.subheader("Tempetarura Mais Recente por Cidade")
    fig = px.bar(
        df_ultima_hora.sort_values("Temperatura (ºc)", ascending=False),
        x="Cidade",
        y="Temperatura (ºc)",
        title="Temperatura Atual por Cidade",
        labels={"Temperatura (ºc)": "Temperatura (°C)"},
        text="Temperatura (ºc)"
    )
    fig.update_traces(textposition='outside')

    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.dataframe(df)