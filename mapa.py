import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import unicodedata
import plotly.express as px

# ------------------------
# FUNCIONES
# ------------------------

def normalizar(texto):
    texto = str(texto).strip().lower()
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8')
    return texto

def cargar_datos(ruta):
    df = pd.read_excel(ruta, sheet_name=1)
    df = df.dropna(subset=['_start-geopoint_latitude', '_start-geopoint_longitude'])
    df['_start-geopoint_latitude'] = df['_start-geopoint_latitude'].astype(float)
    df['_start-geopoint_longitude'] = df['_start-geopoint_longitude'].astype(float)
    return df

def generar_mapa(df, columna):
    df = df.dropna(subset=[columna]).copy()
    df[columna] = df[columna].astype(str).apply(normalizar)

    valores = df[columna].unique()
    colores = px.colors.qualitative.Plotly + px.colors.qualitative.Dark24
    mapa_colores = dict(zip(valores, colores * 5))

    mapa = folium.Map(location=[17.0257, -96.7353], zoom_start=15)

    for _, row in df.iterrows():
        valor = row[columna]
        color = mapa_colores.get(valor, 'gray')
        tooltip = f"{columna}: {valor}"

        folium.CircleMarker(
            location=[row['_start-geopoint_latitude'], row['_start-geopoint_longitude']],
            radius=6,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.9,
            tooltip=tooltip
        ).add_to(mapa)

    return mapa, mapa_colores, df

# ------------------------
# STREAMLIT APP
# ------------------------

st.set_page_config(layout="wide")
st.title("📍 Mapa y análisis interactivo de variables del cuestionario")

ruta_local = '/home/lando/Documentos/REU 2025/Encuesta DHA.xlsx'

try:
    df = cargar_datos(ruta_local)

    columnas_excluir = [
        'start', 'end', 'start-geopoint', '_start-geopoint_latitude', '_start-geopoint_longitude',
        '_start-geopoint_altitude', '_start-geopoint_precision',
        'Esta encuesta es con fines de investigación y académica de parte del CIIDIR Oaxaca del Instituto Politécnico Nacional, que tiene el objetivo de diagnosticar los factores sociales, políticos y económicos que afectan el cumplimiento al derecho humano al agua y que aumentan su impacto en épocas de sequía. Con ello, se realizara una evaluación de sectores más vulnerables. No se piden datos personales y toda la información individual recabada será usada de manera confidencial.',
        'Fecha:'
    ]

    columnas_opciones = [col for col in df.columns if df[col].dtype == 'object' and col not in columnas_excluir]

    variable = st.selectbox("📌 Selecciona una variable para visualizar:", columnas_opciones)

    if variable:
        mapa, mapa_colores, df_filtrado = generar_mapa(df, variable)
        st.subheader("🗺️ Mapa georreferenciado")
        st_folium(mapa, width=1200, height=700)

        # 📊 Gráfico y tabla
        st.subheader("📊 Gráfico interactivo de frecuencias")
        df_filtrado[variable] = df_filtrado[variable].astype(str).apply(normalizar)
        frecuencia = df_filtrado[variable].value_counts().reset_index()
        frecuencia.columns = ['Respuesta', 'Frecuencia']
        total = frecuencia['Frecuencia'].sum()
        frecuencia['Porcentaje (%)'] = (frecuencia['Frecuencia'] / total * 100).round(1)

        fig = px.bar(
            frecuencia,
            x='Respuesta',
            y='Frecuencia',
            color='Respuesta',
            color_discrete_map=mapa_colores,
            title=f'Distribución de respuestas para: {variable}',
            labels={'Frecuencia': 'Número de viviendas'}
        )
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

        # 📄 Tabla de frecuencia
        st.subheader("📄 Tabla de frecuencia con porcentaje")
        st.dataframe(
            frecuencia.style.format({'Frecuencia': '{:.0f}', 'Porcentaje (%)': '{:.1f}'}),
            use_container_width=True
        )

        # ⬇️ Descargar CSV
        csv = frecuencia.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="⬇️ Descargar tabla como CSV",
            data=csv,
            file_name=f'frecuencia_{variable.replace(" ", "_")}.csv',
            mime='text/csv'
        )

except Exception as e:
    st.error(f"❌ Error al cargar el archivo: {e}")
