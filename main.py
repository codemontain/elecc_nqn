import pandas as pd
import plotly.express as px
import plotly.io as pio
import folium
import branca.colormap as cm
import re
import os
import json

# --- Configuración de Rutas y Directorios ---
# Obtiene el directorio base donde se ejecuta el script.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = BASE_DIR  # Asume que los CSV y GeoJSON están en el mismo directorio que el script.
MAPS_DIR = os.path.join(BASE_DIR, 'mapas')
IMAGES_DIR = os.path.join(BASE_DIR, 'image')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output') # Directorio para el HTML final y el mapa de Folium.

# Asegúrate de que estos directorios existan.
for directory in [DATA_DIR, MAPS_DIR, IMAGES_DIR, OUTPUT_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"Directorio '{directory}' creado.")

# Rutas completas a los archivos CSV.
csv_file_path = os.path.join(DATA_DIR, 'Datos_Norte_NQN - departamentos.csv')
localidades_csv_file_path = os.path.join(DATA_DIR, 'Datos_Norte_NQN - localidades.csv')
presidente_csv_file_path = os.path.join(DATA_DIR, 'Datos_Norte_NQN - Copia de presidente.csv')

# Rutas para los archivos de salida.
output_html_path = os.path.join(OUTPUT_DIR, 'informe_elecciones_nqn.html')
mapa_output_path = os.path.join(OUTPUT_DIR, 'mapa_departamentos_nqn.html')

# --- Mapeo de Candidatos a Imágenes ---
# Diccionarios que asocian el nombre de un candidato con el nombre de archivo de su imagen.
CANDIDATE_IMAGES_GOBERNADOR = {
    'Rolando Figueroa': 'rolando figueroa.png',
    'Marcos Koopmann': 'marcos koopmann.png',
    'Ramon Rioseco': 'ramon rioseco.png',
    'Mario Pablo Cervi': 'mario pablo cervi.png',
    'Carlos Eguia': 'carlos eguia.png',
    'Patricia Jure': 'patricia jure.png'
}

CANDIDATE_IMAGES_PRESIDENTE = {
    'Sergio Massa': 'sergio massa.png',
    'Javier Milei': 'javier milei.png',
    'Patricia Bullrich': 'patricia.png',
    'Juan Schiaretti': 'juan.png',
    'Myriam Bregman': 'miryam.png'
}

# --- Configuración común para los gráficos Plotly ---
# Diccionario para configurar el diseño de todos los gráficos de Plotly,
# asegurando consistencia y buena visualización.
PLOTLY_LAYOUT_CONFIG = dict(
    autosize=True,
    height=500,
    margin=dict(l=50, r=50, t=50, b=150), # Aumentado el margen inferior para la leyenda
    legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5),
    xaxis=dict(tickangle=0, tickfont=dict(size=10), title=None, automargin=True),
    yaxis=dict(automargin=True),
    bargap=0.15 # Espacio entre barras para claridad
)

# --- Funciones Auxiliares ---

def load_csv(file_path, **kwargs):
    """
    Carga un archivo CSV de forma segura, manejando errores comunes.

    Args:
        file_path (str): La ruta al archivo CSV.
        **kwargs: Argumentos adicionales para pd.read_csv (ej. decimal, thousands).

    Returns:
        pd.DataFrame or None: El DataFrame cargado o None si ocurre un error.
    """
    try:
        df = pd.read_csv(file_path, **kwargs)
        return df
    except FileNotFoundError:
        print(f"Error: Archivo no encontrado en: {file_path}")
        return None
    except pd.errors.EmptyDataError:
        print(f"Error: El archivo CSV está vacío: {file_path}")
        return None
    except pd.errors.ParserError as e:
        print(f"Error al analizar el CSV {file_path}: {e}")
        return None
    except Exception as e:
        print(f"Ocurrió un error inesperado al cargar {file_path}: {e}")
        return None

def create_candidate_images_html(candidate_images_map, image_dir, output_dir_for_relative_path):
    """
    Genera el fragmento HTML para mostrar las imágenes de los candidatos.

    Args:
        candidate_images_map (dict): Un diccionario de nombre de candidato a nombre de archivo de imagen.
        image_dir (str): El directorio donde se encuentran las imágenes.
        output_dir_for_relative_path (str): El directorio de salida para calcular la ruta relativa.

    Returns:
        str: Un string HTML que contiene las imágenes de los candidatos.
    """
    images_html = '<div class="candidate-images-container">'
    for candidate, image_filename in candidate_images_map.items():
        image_path_full = os.path.join(image_dir, image_filename)
        # Genera la ruta relativa para el HTML, usando barras inclinadas para compatibilidad con URL.
        display_path = os.path.relpath(image_path_full, output_dir_for_relative_path).replace('\\', '/')

        if not os.path.exists(image_path_full):
            print(f"Advertencia: Imagen no encontrada para '{candidate}': {image_path_full}")
            # Si la imagen no existe, usa un placeholder para evitar enlaces rotos.
            display_path = 'https://via.placeholder.com/100?text=No+Image'
        images_html += f'''
            <div class="candidate-image-item">
                <img src="{display_path}" alt="{candidate}" class="candidate-image">
                <p class="candidate-name">{candidate}</p>
            </div>
        '''
    images_html += '</div>'
    return images_html

def clean_filename(name):
    """
    Limpia un string para que pueda ser usado como parte de un nombre de archivo
    o como un ID HTML, eliminando caracteres no válidos.

    Args:
        name (str): El string a limpiar.

    Returns:
        str: El string limpio.
    """
    return re.sub(r"[^a-zA-Z0-9_]", "", name.replace(" ", "_"))

# --- Procesamiento Principal ---

def generate_election_report():
    """
    Genera el informe HTML completo con los gráficos y mapas electorales.
    """
    tab1_content = "" # Contenido HTML para la pestaña de Gobernador.
    tab_presidente_content = "" # Contenido HTML para la pestaña de Presidente.
    plotly_graph_data = {} # Diccionario para almacenar los JSON de los gráficos de Plotly.

    # --- Procesamiento de datos de Departamentos (Gobernador Provincial) ---
    df = load_csv(csv_file_path)
    if df is not None:
        try:
            # Transforma el DataFrame a formato largo para Plotly.
            df_long = df.melt(id_vars=['Candidato'], var_name='Departamento', value_name='Votos')
            df_long['Departamento'] = df_long['Departamento'].str.capitalize()

            # Calcula el total de votos por departamento.
            df_total_votos_depto = df_long.groupby('Departamento')['Votos'].sum().reset_index()
            df_total_votos_depto.rename(columns={'Votos': 'TotalVotosDepartamento'}, inplace=True)

            # Prepara los datos para los popups del mapa de Folium.
            departamento_data = {}
            for depto in df_long['Departamento'].unique():
                total_votos = df_total_votos_depto[df_total_votos_depto['Departamento'] == depto]['TotalVotosDepartamento'].iloc[0] if depto in df_total_votos_depto['Departamento'].values else 0
                votos_candidatos = df_long[df_long['Departamento'] == depto].set_index('Candidato')['Votos'].to_dict()
                departamento_data[depto] = {
                    'TotalVotos': total_votos,
                    'Candidatos': votos_candidatos
                }

            def create_popup_content(depto_name):
                """Crea el contenido HTML para el popup de un departamento en el mapa."""
                data = departamento_data.get(depto_name)
                if not data:
                    return f"<h3>{depto_name}</h3><p>Datos no disponibles.</p>"
                content = f"<h3>Departamento: {depto_name}</h3>"
                content += f"<p><b>Votos Totales:</b> {data['TotalVotos']}</p>"
                content += "<p><b>Votos por Candidato:</b></p><ul>"
                for candidato, votos in data['Candidatos'].items():
                    content += f"<li>{candidato}: {votos}</li>"
                content += "</ul>"
                return content

            # --- Gráfico 1: Resultados Electorales por Departamento y Candidato (Gobernador Provincial) ---
            fig_depto_candidato = px.bar(df_long,
                                         x='Departamento',
                                         y='Votos',
                                         color='Candidato',
                                         barmode='group',
                                         title='Resultados Electorales por Departamento y Candidato (Gobernador Provincial)',
                                         labels={'Votos': 'Cantidad de Votos', 'Departamento': ''},
                                         hover_data={'Candidato': True, 'Departamento': True, 'Votos': True},
                                         text='Votos',
                                         opacity=0.7,
                                         color_discrete_sequence=px.colors.qualitative.D3)
            fig_depto_candidato.update_traces(textposition='outside', textangle=0, textfont=dict(color='black', size=12))
            fig_depto_candidato.update_layout(**PLOTLY_LAYOUT_CONFIG)
            # Guarda el gráfico como JSON para ser incrustado en el HTML.
            plotly_graph_data['graph_gobernador_depto_candidato'] = pio.to_json(fig_depto_candidato)

            # --- Gráfico 2: Resultados Electorales Totales en la Zona Norte (Gobernador Provincial) ---
            df_total_votos = df.set_index('Candidato').sum(axis=1).reset_index(name='TotalVotos')
            df_total_votos.rename(columns={'index': 'Candidato'}, inplace=True)

            fig_total_zona_norte = px.bar(df_total_votos,
                                          x='Candidato',
                                          y='TotalVotos',
                                          color='Candidato',
                                          title='Resultados Electorales Totales en la Zona Norte (Gobernador Provincial)',
                                          labels={'TotalVotos': 'Cantidad de Votos', 'Candidato': ''},
                                          text='TotalVotos',
                                          opacity=0.7,
                                          color_discrete_sequence=px.colors.qualitative.D3)
            fig_total_zona_norte.update_traces(textposition='outside', textangle=0, textfont=dict(color='black', size=12))
            fig_total_zona_norte.update_layout(**PLOTLY_LAYOUT_CONFIG)
            # Guarda el gráfico como JSON para ser incrustado en el HTML.
            plotly_graph_data['graph_gobernador_total_zona_norte'] = pio.to_json(fig_total_zona_norte)

            # --- Generar el mapa con Folium ---
            map_center = [-37.37, -70.56] # Coordenadas para centrar el mapa en la zona norte de Neuquén.
            m = folium.Map(location=map_center, zoom_start=9)

            geojson_files = [
                ("minasg.geojson", "Minas"),
                ("chosmalal.geojson", "Chos Malal"),
                ("pehuenches.geojson", "Pehuenches"),
                ("ñorquin.geojson", "Ñorquin"),
                ("loncopue.geojson", "Loncopue")
            ]

            min_votos, max_votos = 0, 1 # Valores por defecto para la leyenda del mapa.
            votos_existentes = [data['TotalVotos'] for data in departamento_data.values() if data['TotalVotos'] is not None]
            if votos_existentes:
                min_votos = min(votos_existentes)
                # Asegura que max_votos sea mayor que min_votos para evitar errores en el colormap.
                max_votos = max(votos_existentes) if max(votos_existentes) > min_votos else min_votos + 1

            # Define un mapa de colores lineal para el mapa de coropletas.
            colormap = cm.LinearColormap(colors=['#f0f0f0', '#e31a1c', '#800026'],
                                         index=[min_votos, (min_votos + max_votos) / 2, max_votos],
                                         caption='Votos Totales por Departamento')

            def style_function(feature):
                """Función de estilo para el GeoJSON, colorea según los votos totales."""
                depto_name_raw = feature['properties'].get('nombre', '').strip()
                depto_name = depto_name_raw.capitalize()
                total_votos = departamento_data.get(depto_name, {}).get('TotalVotos', 0)
                return {
                    'fillColor': colormap(total_votos),
                    'color': 'black',
                    'weight': 1,
                    'fillOpacity': 0.6
                }

            # Añade las capas GeoJSON al mapa.
            for geojson_file, depto_name in geojson_files:
                geojson_path = os.path.join(MAPS_DIR, geojson_file)
                try:
                    if os.path.exists(geojson_path):
                        popup_content = create_popup_content(depto_name)
                        folium.GeoJson(
                            geojson_path,
                            style_function=style_function,
                            popup=folium.Popup(popup_content, max_width=300)
                        ).add_to(m)
                    else:
                        print(f"Advertencia: Archivo GeoJSON no encontrado: {geojson_path}. No se añadirá al mapa.")
                except Exception as e:
                    print(f"Error al procesar {geojson_file}: {e}")

            # Ajusta los límites del mapa para que se adapten a las capas GeoJSON añadidas.
            try:
                m.fit_bounds(m.get_bounds())
            except Exception as e:
                print(f"Advertencia: No se pudieron ajustar los límites del mapa. Error: {e}")

            # Añade la leyenda del mapa de colores.
            colormap.add_to(m)

            # Guarda el mapa de Folium como un archivo HTML separado.
            m.save(mapa_output_path)
            print(f"Mapa interactivo de departamentos guardado en: {mapa_output_path}")

            # Añade el iframe del mapa al contenido de la pestaña.
            tab1_content += '<h3 align="center" style="font-size:16px; color: #0056b3;"><b>Votos por Departamento en la Zona Norte Neuquino</b></h3>'
            # Calcula la ruta relativa para el iframe del mapa en el HTML final.
            map_display_path = os.path.relpath(mapa_output_path, OUTPUT_DIR).replace('\\', '/')
            tab1_content += f'<div class="map-container"><iframe src="{map_display_path}" width="100%" height="400px" frameborder="0"></iframe></div>'

        except Exception as e:
            tab1_content += f"<p>Ocurrió un error al procesar los datos de departamentos: {e}</p>"
            print(f"Error al procesar datos de departamentos: {e}")

    # Añade las imágenes de los candidatos a Gobernador al contenido de la pestaña.
    tab1_content += create_candidate_images_html(CANDIDATE_IMAGES_GOBERNADOR, IMAGES_DIR, OUTPUT_DIR)
    # Añade los contenedores (divs) donde Plotly renderizará los gráficos.
    tab1_content += f'<div class="plotly-graph-container" id="graph_gobernador_depto_candidato"></div>'
    tab1_content += f'<div class="plotly-graph-container" id="graph_gobernador_total_zona_norte"></div>'

    # --- Generar gráficos por localidad ---
    df_localidades = load_csv(localidades_csv_file_path)
    if df_localidades is not None:
        try:
            # Convierte las columnas de votos a entero, manejando valores nulos o guiones.
            voto_cols_localidades = [col for col in df_localidades.columns if col not in ['Localidad', 'Departamento']]
            for col in voto_cols_localidades:
                df_localidades[col] = df_localidades[col].replace('-', '0').astype(int)

            all_localities_from_data = df_localidades['Localidad'].unique().tolist()

            tab1_content += '<hr><h2 style="color: #0056b3;">Resultados Electorales por Localidad (Gobernador Provincial)</h2>'
            for localidad_name in all_localities_from_data:
                df_current_locality = df_localidades[df_localidades['Localidad'] == localidad_name].copy()
                if not df_current_locality.empty:
                    df_current_locality_long = df_current_locality.melt(id_vars=['Localidad', 'Departamento'],
                                                                        var_name='Candidato',
                                                                        value_name='Votos')
                    # Solo genera el gráfico si hay votos válidos.
                    if not df_current_locality_long.empty and df_current_locality_long['Votos'].sum() > 0:
                        fig_locality = px.bar(df_current_locality_long,
                                              x='Candidato',
                                              y='Votos',
                                              color='Candidato',
                                              title=f'Resultados Electorales en {localidad_name}',
                                              labels={'Votos': 'Cantidad de Votos', 'Candidato': ''},
                                              text='Votos',
                                              opacity=0.7,
                                              color_discrete_sequence=px.colors.qualitative.D3)
                        fig_locality.update_traces(textposition='outside', textangle=0,
                                                   textfont=dict(color='black', size=12))
                        fig_locality.update_layout(**PLOTLY_LAYOUT_CONFIG)

                        # Genera un ID único y limpio para el div del gráfico.
                        graph_id = f'localidad_graph_{clean_filename(localidad_name)}'
                        plotly_graph_data[graph_id] = pio.to_json(fig_locality)
                        tab1_content += f'<div class="plotly-graph-container" id="{graph_id}"></div>'
                    else:
                        tab1_content += f"<p>Advertencia: No hay datos de votos válidos para {localidad_name}.</p>"
                else:
                    print(f"Advertencia: Datos para la localidad '{localidad_name}' no encontrados en el archivo.")

        except Exception as e:
            tab1_content += f"<p>Ocurrió un error al procesar el archivo de localidades: {e}</p>"
            print(f"Error al procesar datos de localidades: {e}")

    # --- Resumen de resultados para Rolando Figueroa ---
    if df_localidades is not None:
        try:
            voto_cols_summary = [col for col in df_localidades.columns if col not in ['Localidad', 'Departamento']]
            # Verifica si la columna de Rolando Figueroa existe para el resumen.
            if 'Rolando Figueroa' in voto_cols_summary:
                # Encuentra al ganador por localidad.
                df_localidades['Ganador_Localidad'] = df_localidades[voto_cols_summary].idxmax(axis=1)
                df_localidades['Max_Votos_Localidad'] = df_localidades[voto_cols_summary].max(axis=1)

                localidades_ganadas_rf = []
                localidades_perdidas_rf = []

                for index, row in df_localidades.iterrows():
                    localidad = row['Localidad']
                    votos_rf = row.get('Rolando Figueroa', 0)

                    ganador_localidad = row['Ganador_Localidad']
                    max_votos_localidad = row['Max_Votos_Localidad']

                    # Se considera que ganó si sus votos son los máximos y hay al menos un voto.
                    if votos_rf == max_votos_localidad and votos_rf > 0:
                        localidades_ganadas_rf.append(localidad)
                    else:
                        localidades_perdidas_rf.append(localidad)

                tab1_content += '<hr><h2 style="color: #0056b3;">Resumen de Resultados para Rolando Figueroa por Localidad</h2>'
                tab1_content += '<h3 style="color: #0056b3;">Localidades donde Rolando Figueroa ganó:</h3>'
                if localidades_ganadas_rf:
                    tab1_content += '<ul style="color: #343a40;">'
                    for loc in sorted(localidades_ganadas_rf):
                        tab1_content += f'<li>{loc}</li>'
                    tab1_content += '</ul>'
                else:
                    tab1_content += '<p style="color: #343a40;">No ganó en ninguna localidad donde se disponga de datos de votación válida para todos los candidatos.</p>'

                tab1_content += '<h3 style="color: #0056b3;">Localidades donde Rolando Figueroa no fue el más votado:</h3>'
                if localidades_perdidas_rf:
                    tab1_content += '<ul style="color: #343a40;">'
                    for loc in sorted(localidades_perdidas_rf):
                        tab1_content += f'<li>{loc}</li>'
                    tab1_content += '</ul>'
                else:
                    tab1_content += '<p style="color: #343a40;">Ganó en todas las localidades donde tuvo votos y donde se pudo determinar un ganador.</p>'
            else:
                tab1_content += '<p style="color: #dc3545;">Advertencia: La columna "Rolando Figueroa" no se encontró en el archivo de localidades para el resumen. Verifique el nombre de la columna.</p>'

        except Exception as e:
            tab1_content += f"<p>Ocurrió un error al generar el resumen de Rolando Figueroa: {e}</p>"
            print(f"Error al generar resumen de Rolando Figueroa: {e}")

    # --- Procesamiento de datos de Presidente y generación de gráfico ---
    # `decimal=','` y `thousands='.'` son cruciales para CSVs con formato numérico europeo.
    df_presidente = load_csv(presidente_csv_file_path, decimal=',', thousands='.')
    if df_presidente is not None:
        try:
            candidatos_presidente = ['Sergio Massa', 'Javier Milei', 'Patricia Bullrich', 'Juan Schiaretti', 'Myriam Bregman']
            existing_president_cols = [col for col in candidatos_presidente if col in df_presidente.columns]
            if not existing_president_cols:
                tab_presidente_content = "<p>Advertencia: No se encontraron datos de candidatos presidenciales en el archivo.</p>"
                print("Advertencia: Ninguna columna de candidato presidencial reconocida encontrada en el CSV de presidente.")
            else:
                df_presidente_long = df_presidente.melt(id_vars=['Departamento'], value_vars=existing_president_cols,
                                                        var_name='Candidato', value_name='Votos')

                fig_presidente = px.bar(df_presidente_long,
                                        x='Departamento',
                                        y='Votos',
                                        color='Candidato',
                                        barmode='group',
                                        title='Resultados Electorales Presidenciales por Departamento',
                                        labels={'Votos': 'Cantidad de Votos', 'Departamento': ''},
                                        hover_data={'Candidato': True, 'Departamento': True, 'Votos': True},
                                        opacity=0.7,
                                        color_discrete_sequence=px.colors.qualitative.D3,
                                        text_auto=True) # Muestra los valores de texto automáticamente.
                fig_presidente.update_layout(**PLOTLY_LAYOUT_CONFIG, xaxis_title_text='')

                # Guarda el gráfico como JSON para ser incrustado en el HTML.
                plotly_graph_data['graph_presidente_depto'] = pio.to_json(fig_presidente)
                # Añade el contenedor (div) para el gráfico de presidente.
                tab_presidente_content = f'<div class="plotly-graph-container" id="graph_presidente_depto"></div>'
                # Añade las imágenes de los candidatos a Presidente.
                tab_presidente_content += create_candidate_images_html(CANDIDATE_IMAGES_PRESIDENTE, IMAGES_DIR, OUTPUT_DIR)

        except Exception as e:
            tab_presidente_content = f"<p>Ocurrió un error al procesar los datos de presidente: {e}</p>"
            print(f"Error al procesar datos de presidente: {e}")
    else:
        tab_presidente_content = "<p>No se pudo cargar el archivo de datos de Presidente.</p>"

    # --- Estructura HTML Final con JavaScript Dinámico ---
    full_html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Resultados Electorales</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <script src="https://cdn.plot.ly/plotly-2.30.0.min.js"></script>
    <style>
        body {{
            font-family: 'Inter', sans-serif;
            margin: 0;
            background-color: #f0f2f5;
            background-image: radial-gradient(circle at center, rgba(0,0,0,0.03) 0%, rgba(0,0,0,0) 70%);
            color: #343a40;
        }}
        h2 {{
            text-align: center;
            color: #000000;
            padding: 20px 0;
            margin-bottom: 0;
        }}
        .main-content-wrapper {{
            max-width: 1200px;
            margin: 20px auto;
            background-color: #ffffff;
            border-radius: 12px;
            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }}
        .tab-container {{
            display: flex;
            border-bottom: 2px solid #dee2e6;
            background-color: #f8f9fa;
            padding: 0 20px;
            flex-wrap: wrap;
        }}
        .tab-container button {{
            background-color: transparent;
            border: none;
            outline: none;
            cursor: pointer;
            padding: 15px 25px;
            font-size: 16px;
            font-weight: bold;
            color: #6c757d;
            transition: all 0.3s ease;
            border-bottom: 3px solid transparent;
            margin-right: 5px;
            flex-grow: 1;
            min-width: fit-content;
        }}
        .tab-container button:hover {{
            background-color: #e2e6ea;
            color: #0056b3;
        }}
        .tab-container button.active {{
            background-color: #ffffff;
            color: #007bff;
            border-bottom: 3px solid #007bff;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            margin-bottom: -2px;
        }}
        .tabcontent {{
            display: none;
            padding: 20px;
            border: none;
            border-top: none;
            width: 100%;
            box-sizing: border-box;
        }}
        .plotly-graph-container, .map-container {{
            width: 100%;
            margin: 30px auto;
            box-shadow: 0 6px 12px rgba(0,0,0,0.1);
            border-radius: 10px;
            overflow: hidden;
            border: 1px solid #e0e0e0;
            background-color: #ffffff;
            padding: 5px;
            box-sizing: border-box;
            color: #343a40;
            min-height: 500px; /* Altura predeterminada para gráficos Plotly */
        }}
        .map-container {{
            min-height: 400px; /* Altura específica para el mapa */
        }}
        .plotly-graph-container div {{ /* Estilo para el div interno que Plotly crea */
            width: 100%;
            height: 100%;
        }}
        .plotly-graph-container .modebar-container {{
            background-color: #f8f9fa;
            border-radius: 5px;
        }}
        .plotly-graph-container .modebar-btn {{
            color: #6c757d !important;
        }}
        .plotly-graph-container .modebar-btn:hover {{
            background-color: #e2e6ea !important;
        }}
        .tabcontent h3, .tabcontent p, .tabcontent ul, .tabcontent li {{
            color: #343a40;
        }}
        .tabcontent hr {{
            border-color: #ced4da;
        }}

        .candidate-images-container {{
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 20px;
            margin-top: 30px;
            padding: 20px;
            background-color: #f8f9fa;
            border-radius: 10px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.05);
        }}
        .candidate-image-item {{
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            width: 100%;
            max-width: 120px;
        }}
        .candidate-image {{
            width: 100px;
            height: 100px;
            border-radius: 50%;
            object-fit: cover;
            border: 3px solid #007bff;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: transform 0.2s ease-in-out;
        }}
        .candidate-image:hover {{
            transform: scale(1.05);
        }}
        .candidate-name {{
            margin-top: 10px;
            font-weight: bold;
            color: #343a40;
            font-size: 0.9em;
        }}

        @media (max-width: 768px) {{
            .tab-container {{
                flex-direction: column;
                padding: 0;
            }}
            .tab-container button {{
                margin-right: 0;
                border-bottom: none;
                border-radius: 0;
                text-align: center;
                width: 100%;
            }}
            .tab-container button.active {{
                border-bottom: none;
                border-radius: 0;
            }}
            .main-content-wrapper {{
                margin: 10px;
                border-radius: 0;
                box-shadow: none;
            }}
            .plotly-graph-container, .map-container {{
                margin: 15px auto;
                border-radius: 0;
                box-shadow: none;
                padding: 5px;
                min-height: 350px; /* Ajustar para móviles */
            }}
            h2 {{
                padding: 15px 0;
            }}
        }}
    </style>
</head>
<body>

<h2>Análisis de elecciones en el Norte de la Provincia de Neuquén</h2>

<div class="main-content-wrapper">
    <div class="tab-container">
        <button class="tablinks active" onclick="openTab(event, 'Gobernador')">Resultados Elecciones 2023 - Gobernador Provincial</button>
        <button class="tablinks" onclick="openTab(event, 'Presidente')">Resultados Elecciones Presidente</button>
    </div>

    <div id="Gobernador" class="tabcontent" style="display: block;">
        {tab1_content}
    </div>

    <div id="Presidente" class="tabcontent">
        {tab_presidente_content}
    </div>
</div>

<script>
    // Almacena los datos JSON de los gráficos de Plotly.
    // Usamos json.dumps con indent para que el JSON sea legible en el HTML si se inspecciona.
    const PLOTLY_GRAPHS = {json.dumps(plotly_graph_data, indent=4)};

    function plotGraph(graphId) {{
        const graphDiv = document.getElementById(graphId);
        // Verifica que el div exista y que tengamos datos para ese gráfico.
        if (graphDiv && PLOTLY_GRAPHS[graphId]) {{
            try {{
                // Parsea el string JSON a un objeto JavaScript.
                const data = JSON.parse(PLOTLY_GRAPHS[graphId]);
                // Renderiza el gráfico usando Plotly.newPlot.
                Plotly.newPlot(graphId, data.data, data.layout, {{responsive: true, displayModeBar: false}});
            }} catch (e) {{
                // Captura y muestra errores si el gráfico no se puede plotear.
                // IMPORTANTE: Se escapa el $ con otro $ para que Python lo pase literalmente al JS.
                console.error(`Error al plotear el gráfico ${{graphId}}:`, e);
                graphDiv.innerHTML = `<p style="color: red;">Error al cargar el gráfico: ${{e.message}}</p>`;
            }}
        }} else if (graphDiv) {{
             // Advertencia si el div existe pero no hay datos Plotly asociados.
             console.warn(`No se encontraron datos Plotly para el ID: ${{graphId}}`);
             graphDiv.innerHTML = `<p style="color: orange;">Datos del gráfico no disponibles.</p>`;
        }}
    }}

    function openTab(evt, tabName) {{
        var i, tabcontent, tablinks;
        // Oculta todos los contenidos de las pestañas.
        tabcontent = document.getElementsByClassName("tabcontent");
        for (i = 0; i < tabcontent.length; i++) {{
            tabcontent[i].style.display = "none";
        }}
        // Desactiva la clase 'active' de todos los botones de pestaña.
        tablinks = document.getElementsByClassName("tablinks");
        for (i = 0; i < tablinks.length; i++) {{
            tablinks[i].className = tablinks[i].className.replace(" active", "");
        }}
        // Muestra el contenido de la pestaña seleccionada y activa el botón.
        document.getElementById(tabName).style.display = "block";
        evt.currentTarget.className += " active";

        // Re-plotear los gráficos de Plotly cuando la pestaña se hace visible.
        // Un pequeño retraso para asegurar que los elementos del DOM estén completamente renderizados
        // y el navegador les asigne dimensiones correctas antes de que Plotly intente dibujarlos.
        setTimeout(() => {{
            const activeTabContent = document.getElementById(tabName);
            // Busca todos los divs con la clase 'plotly-graph-container' y un 'id' dentro de la pestaña activa.
            const graphDivs = activeTabContent.querySelectorAll('.plotly-graph-container[id]');
            graphDivs.forEach(div => {{
                plotGraph(div.id); // Llama a la función para plotear cada gráfico.
            }});
            // Dispara un evento de redimensionamiento global, útil si hay otros componentes que necesiten reaccionar
            window.dispatchEvent(new Event('resize'));
        }}, 200); // Retraso de 200ms.
    }}

    document.addEventListener('DOMContentLoaded', (event) => {{
        // Activa la primera pestaña al cargar la página y asegura que sus gráficos se ploteen.
        const gobernadorButton = document.querySelector('.tablinks.active');
        if (gobernadorButton) {{
            gobernadorButton.click();
        }}
    }});
</script>

</body>
</html>
    """

    # Guarda el archivo HTML final en el directorio de salida.
    with open(output_html_path, 'w', encoding='utf-8') as f:
        f.write(full_html_content)
    print(f"Informe HTML generado exitosamente en: {output_html_path}")

# --- Ejecución del script ---
if __name__ == "__main__":
    generate_election_report()