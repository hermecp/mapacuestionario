import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import unicodedata
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.ticker as mtick
from io import BytesIO
import requests
import os

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
    colores = sns.color_palette("tab20", len(valores)).as_hex()
    mapa_colores = dict(zip(valores, colores))

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
st.title("📍 Mapa y análisis de variables del cuestionario")

# URL del Excel en GitHub
url_excel = "https://raw.githubusercontent.com/hermecp/mapacuestionario/main/Encuesta%20DHA.xlsx"

try:
    response = requests.get(url_excel)
    response.raise_for_status()
    df = cargar_datos(BytesIO(response.content))

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

        # ================================
        # FRECUENCIA + GRAFICO ESTÁTICO
        # ================================
        st.subheader("📊 Gráfico de frecuencias (estático)")

        df_filtrado[variable] = df_filtrado[variable].astype(str).apply(normalizar)
        frecuencia = df_filtrado[variable].value_counts().sort_index().reset_index()
        frecuencia.columns = ['Respuesta', 'Frecuencia']
        frecuencia['Porcentaje (%)'] = (frecuencia['Frecuencia'] / frecuencia['Frecuencia'].sum() * 100).round(1)

        # Crear carpeta si no existe
        os.makedirs("graficos_exportados", exist_ok=True)
        filename_base = f'graficos_exportados/frecuencia_{variable.replace(" ", "_")}'

        fig, ax = plt.subplots(figsize=(max(10, len(frecuencia) * 0.6), 6))
        sns.set_theme(style="whitegrid", font_scale=1.1)
        sns.barplot(data=frecuencia, x='Respuesta', y='Frecuencia', ax=ax, palette="colorblind")

        for i, row in frecuencia.iterrows():
            ax.text(i, row['Frecuencia'] + 0.5, f"{int(row['Frecuencia'])}", ha='center', va='bottom', fontsize=10)

        ax.set_title(f'Distribución de respuestas: {variable}', fontsize=16, weight='bold')
        ax.set_xlabel('')
        ax.set_ylabel('Número de viviendas', fontsize=12)
        ax.set_xticklabels(frecuencia['Respuesta'], rotation=45, ha='right')
        ax.yaxis.set_major_locator(mtick.MaxNLocator(integer=True))
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        plt.tight_layout()
        st.pyplot(fig)

        # Guardar como imagen y PDF
        fig.savefig(f"{filename_base}.png", dpi=300, bbox_inches='tight')
        fig.savefig(f"{filename_base}.pdf", dpi=300, bbox_inches='tight')

        # ================================
        # DESCARGAS
        # ================================
        st.subheader("📤 Descargas")

        with open(f"{filename_base}.png", "rb") as fimg:
            st.download_button(
                label="📸 Descargar gráfico como PNG",
                data=fimg,
                file_name=os.path.basename(f"{filename_base}.png"),
                mime="image/png"
            )

        with open(f"{filename_base}.pdf", "rb") as fpdf:
            st.download_button(
                label="📄 Descargar gráfico como PDF",
                data=fpdf,
                file_name=os.path.basename(f"{filename_base}.pdf"),
                mime="application/pdf"
            )

        # ================================
        # TABLA DE FRECUENCIA
        # ================================
        st.subheader("📄 Tabla de frecuencia con porcentaje")
        st.dataframe(
            frecuencia.style
                .format({'Frecuencia': '{:.0f}', 'Porcentaje (%)': '{:.1f}'})
                .set_table_styles([
                    {'selector': 'th', 'props': [('font-size', '12pt'), ('text-align', 'center')]},
                    {'selector': 'td', 'props': [('font-size', '11pt')]},
                ]),
            use_container_width=True
        )

        # Descargar CSV
        csv = frecuencia.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="⬇️ Descargar tabla como CSV",
            data=csv,
            file_name=f'frecuencia_{variable.replace(" ", "_")}.csv',
            mime='text/csv'
        )

except Exception as e:
    st.error(f"❌ Error al cargar el archivo: {e}")
