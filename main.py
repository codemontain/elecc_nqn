# -*- coding: utf-8 -*-
import pandas as pd
import plotly.express as px
import plotly.io as pio
import folium
import branca.colormap as cm
import re

# Rutas a los archivos CSV
csv_file_path = 'Datos_Norte_NQN - departamentos.csv'
output_html_path = 'grafico_elecciones.html'
mapa_minas_path = 'mapa_minas.html'
localidades_csv_file_path = 'Datos_Norte_NQN - localidades.csv'
presidente_csv_file_path = 'Datos_Norte_NQN - Copia de presidente.csv'

# Asegúrate de que estos directorios existan en el mismo lugar que tu script Python
# o ajusta las rutas según sea necesario.
MAPS_DIR = 'mapas'
IMAGES_DIR = 'image'

try:
    # --- Procesamiento de datos de Departamentos ---
    df = pd.read_csv(csv_file_path)
    df_long = df.melt(id_vars=['Candidato'], var_name='Departamento', value_name='Votos')
    df_long['Departamento'] = df_long['Departamento'].str.capitalize()

    df_total_votos_depto = df_long.groupby('Departamento')['Votos'].sum().reset_index()
    df_total_votos_depto.rename(columns={'Votos': 'TotalVotosDepartamento'}, inplace=True)

    departamento_data = {}
    for depto in df_long['Departamento'].unique():
        # Asegurarse de que el departamento existe en df_total_votos_depto antes de acceder
        if depto in df_total_votos_depto['Departamento'].values:
            total_votos = \
            df_total_votos_depto[df_total_votos_depto['Departamento'] == depto]['TotalVotosDepartamento'].iloc[0]
        else:
            total_votos = 0  # Si el departamento no tiene votos, asigna 0
        votos_candidatos = df_long[df_long['Departamento'] == depto].set_index('Candidato')['Votos'].to_dict()
        departamento_data[depto] = {
            'TotalVotos': total_votos,
            'Candidatos': votos_candidatos
        }


    def create_popup_content(depto_name):
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


    # Configuración común para los gráficos Plotly (leyenda, responsividad y altura mínima)
    # AJUSTE CLAVE AQUÍ: Reducimos el margen inferior (b) para eliminar espacio en blanco.
    plotly_layout_config = dict(
        autosize=True,
        height=500,  # Altura predeterminada para dar espacio al texto
        margin=dict(l=50, r=50, t=50, b=100),  # <--- MARGEN INFERIOR REDUCIDO (de 250 a 100)
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),  # Leyenda un poco más arriba
        xaxis=dict(tickangle=0, tickfont=dict(size=6), automargin=True)
    )

    # --- Gráfico 1: Resultados Electorales por Departamento y Candidato (Gobernador Provincial) ---
    fig = px.bar(df_long,
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
    fig.update_traces(textposition='outside', textangle=0, textfont=dict(color='black', size=12))
    fig.update_layout(**plotly_layout_config)

    df_total_votos = df.set_index('Candidato').sum(axis=1).reset_index(name='TotalVotos')
    df_total_votos.rename(columns={0: 'Candidato'}, inplace=True)

    # --- Gráfico 2: Resultados Electorales Totales en la Zona Norte (Gobernador Provincial) ---
    fig2 = px.bar(df_total_votos,
                  x='Candidato',
                  y='TotalVotos',
                  color='Candidato',
                  title='Resultados Electorales Totales en la Zona Norte (Gobernador Provincial)',
                  labels={'TotalVotos': 'Cantidad de Votos', 'Candidato': ''},
                  text='TotalVotos',
                  opacity=0.7,
                  color_discrete_sequence=px.colors.qualitative.D3)
    fig2.update_traces(textposition='outside', textangle=0, textfont=dict(color='black', size=12))
    fig2.update_layout(**plotly_layout_config)

    # --- Generar el mapa con Folium ---
    map_center = [-37.37, -70.56]
    m = folium.Map(location=map_center, zoom_start=9)

    geojson_files = [
        ("minasg.geojson", "Minas"),
        ("chosmalal.geojson", "Chos Malal"),
        ("pehuenches.geojson", "Pehuenches"),
        ("ñorquin.geojson", "Ñorquin"),
        ("loncopue.geojson", "Loncopue")
    ]

    # Calcular min/max votos para la leyenda del mapa
    if departamento_data:
        # Filtrar solo los departamentos que realmente tienen votos para min/max
        votos_existentes = [data['TotalVotos'] for data in departamento_data.values() if data['TotalVotos'] is not None]
        if votos_existentes:  # Solo si hay votos reales
            min_votos = min(votos_existentes)
            max_votos = max(votos_existentes)
        else:
            min_votos = 0
            max_votos = 1  # Por si no hay datos de votos
    else:
        min_votos = 0
        max_votos = 1

    colormap = cm.LinearColormap(colors=['#f0f0f0', '#e31a1c', '#800026'],
                                 index=[min_votos, max_votos],
                                 caption='Votos Totales')


    def style_function(feature):
        depto_name_raw = feature['properties'].get('nombre', '').strip()
        depto_name = depto_name_raw.capitalize()

        total_votos = departamento_data.get(depto_name, {}).get('TotalVotos', 0)
        return {
            'fillColor': colormap(total_votos),
            'color': 'black',
            'weight': 1,
            'fillOpacity': 0.6
        }


    for geojson_file, depto_name in geojson_files:
        geojson_path = f'{MAPS_DIR}/{geojson_file}'
        try:
            popup_content = create_popup_content(depto_name)
            folium.GeoJson(
                geojson_path,
                style_function=style_function,
                popup=folium.Popup(popup_content, max_width=300)
            ).add_to(m)
        except FileNotFoundError:
            print(f"Advertencia: Archivo GeoJSON no encontrado: {geojson_path}. No se añadirá al mapa.")
        except Exception as e:
            print(f"Error al procesar {geojson_file}: {e}")

    try:
        m.fit_bounds(m.get_bounds())
    except Exception as e:
        print(
            f"Advertencia: No se pudieron ajustar los límites del mapa, puede que no haya GeoJSONs válidos cargados. Error: {e}")

    # Construir el HTML de la leyenda manualmente
    legend_html = f'''
    <div style="position: fixed;
                bottom: 20px;
                right: 10px;
                z-index:9999; font-size:14px;
                background-color:rgba(255, 255, 255, 0.9);
                padding: 10px;
                border: 1px solid #ced4da;
                border-radius: 5px;
                height: 120px;
                width: 100px;
                overflow: hidden;
                color: #343a40;
                box-shadow: 0 2px 5px rgba(0,0,0,0.2);
                ">
      &nbsp; <b>Votos Totales</b> <br>
      <div style="display: flex; align-items: center; height: 100%;">
        <i style="background:linear-gradient(to top, #800026, #e31a1c, #f0f0f0);
                    display:inline-block; width:20px; height:80px;
                    vertical-align:middle; margin-right: 5px;"></i>
        <span style="vertical-align:middle; line-height: 1.2;">
          <b>{max_votos:.0f}</b><br>
          <span style="font-size: 0.8em;">{(min_votos + max_votos) / 2:.0f}</span><br>
          <b>{min_votos:.0f}</b>
        </span>
      </div>
    </div>
    '''

    m.get_root().html.add_child(folium.Element(legend_html))

    m.save(mapa_minas_path)
    print(f"Mapa interactivo guardado en: {mapa_minas_path}")

    # Add a new directory for graphs
    GRAPHS_DIR = 'graphs'
    import os
    if not os.path.exists(GRAPHS_DIR):
        os.makedirs(GRAPHS_DIR)

    # --- Generar contenido para la Pestaña 1 (Gobernador Provincial) ---
    graph1_path = f'{GRAPHS_DIR}/gobernador_depto_candidato.html'
    pio.write_html(fig, file=graph1_path, auto_open=False, full_html=True, include_plotlyjs=True, config={"responsive": True})
    tab1_content = f'<div class="plotly-graph-container"><iframe src="{graph1_path}" width="100%" height="500px" frameborder="0"></iframe></div>'

    # Mapeo de candidatos a imágenes para Gobernador
    candidate_images_gobernador = {
        'Rolando Figueroa': 'rolando figueroa.png',
        'Marcos Koopmann': 'marcos koopmann.png',
        'Ramon Rioseco': 'ramon rioseco.png',
        'Mario Pablo Cervi': 'mario pablo cervi.png',
        'Carlos Eguia': 'carlos eguia.png',
        'Patricia Jure': 'patricia jure.png'
    }

    # Generar HTML para las imágenes de los candidatos a Gobernador
    gobernador_images_html = '<div class="candidate-images-container">';
    for candidate, image_filename in candidate_images_gobernador.items():
        image_path = f'{IMAGES_DIR}/{image_filename}'
        gobernador_images_html += f'''
            <div class="candidate-image-item">
                <img src="{image_path}" alt="{candidate}" class="candidate-image">
                <p class="candidate-name">{candidate}</p>
            </div>
        '''
    gobernador_images_html += '</div>';
    tab1_content += gobernador_images_html
    graph2_path = f'{GRAPHS_DIR}/gobernador_total_zona_norte.html'
    pio.write_html(fig2, file=graph2_path, auto_open=False, full_html=True, include_plotlyjs=True, config={"responsive": True})
    tab1_content += f'<div class="plotly-graph-container"><iframe src="{graph2_path}" width="100%" height="500px" frameborder="0"></iframe></div>'
    tab1_content += '<h3 align="center" style="font-size:16px; color: #0056b3;"><b>Votos por Departamento en la Zona Norte Neuquino</b></h3>'
    tab1_content += '<div style="text-align: center;"><iframe src="mapa_minas.html" width="100%" height="400px" frameborder="0" style="display: inline-block;"></iframe></div>'

    # --- Generar gráficos por localidad ---
    try:
        df_localidades = pd.read_csv(localidades_csv_file_path)
        voto_cols = [col for col in df_localidades.columns if col not in ['Localidad', 'Departamento']]
        for col in voto_cols:
            df_localidades[col] = df_localidades[col].replace('-', '0').astype(int)

        all_localities_from_data = df_localidades['Localidad'].unique().tolist()

        tab1_content += '<hr><h2 style="color: #0056b3;">Resultados Electorales por Localidad (Gobernador Provincial)</h2>'
        for localidad_name in all_localities_from_data:
            df_current_locality = df_localidades[df_localidades['Localidad'] == localidad_name]
            if not df_current_locality.empty:
                df_current_locality_long = df_current_locality.melt(id_vars=['Localidad', 'Departamento'],
                                                                    var_name='Candidato',
                                                                    value_name='Votos')
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

                    fig_locality.update_layout(**plotly_layout_config)
                    locality_graph_path = f'{GRAPHS_DIR}/localidad_{localidad_name.replace(" ", "_")}.html'
                    pio.write_html(fig_locality, file=locality_graph_path, auto_open=False, full_html=True, include_plotlyjs=True, config={"responsive": True})
                    tab1_content += f'<div class="plotly-graph-container"><iframe src="{locality_graph_path}" width="100%" height="500px" frameborder="0"></iframe></div>'
                else:
                    tab1_content += f"<p>Advertencia: No hay datos de votos válidos para {localidad_name}.</p>"
                    # print(f"Advertencia: No hay datos de votos válidos para {localidad_name}.") # Comentado para evitar spam en consola
            else:
                print(f"Advertencia: Datos para la localidad '{localidad_name}' no encontrados en el archivo.")

    except FileNotFoundError:
        tab1_content += "<p>Error: El archivo de datos de localidades no se encontró. No se pudieron generar los gráficos por localidad.</p>"
        print("Error: El archivo de localidades no se encontró en la ruta: {}".format(localidades_csv_file_path))
    except Exception as e:
        tab1_content += f"<p>Ocurrió un error al procesar el archivo de localidades: {e}</p>"
        print("Ocurrió un error al procesar el archivo de localidades: {}".format(e))

    # --- Procesamiento de datos de Presidente y generación de gráfico ---
    try:
        df_presidente = pd.read_csv(presidente_csv_file_path, decimal=',', thousands='.')
        candidatos_presidente = ['Sergio Massa', 'Javier Milei', 'Patricia Bullrich', 'Juan Schiaretti',
                                 'Myriam Bregman']
        existing_president_cols = [col for col in candidatos_presidente if col in df_presidente.columns]
        if not existing_president_cols:
            tab_presidente_content = "<p>Advertencia: No se encontraron datos de candidatos presidenciales en el archivo.</p>"
            print(
                "Advertencia: Ninguna columna de candidato presidencial reconocida encontrada en el CSV de presidente.")
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
                                    text='Votos',
                                    opacity=0.7,
                                    color_discrete_sequence=px.colors.qualitative.D3)
            fig_presidente.update_traces(textposition='outside', textangle=0, textfont=dict(color='black', size=12))

            fig_presidente.update_layout(**plotly_layout_config)

            president_graph_path = f'{GRAPHS_DIR}/presidente_depto.html'
            pio.write_html(fig_presidente, file=president_graph_path, auto_open=False, full_html=True, include_plotlyjs=True, config={"responsive": True})
            tab_presidente_content = f'<div class="plotly-graph-container"><iframe src="{president_graph_path}" width="100%" height="500px" frameborder="0"></iframe></div>'

            candidate_images_presidente = {
                'Sergio Massa': 'sergio massa.png',
                'Javier Milei': 'javier milei.png',
                'Patricia Bullrich': 'patricia.png',
                'Juan Schiaretti': 'juan.png',
                'Myriam Bregman': 'miryam.png'
            }

            presidente_images_html = '<div class="candidate-images-container">';
            for candidate in candidatos_presidente:
                image_filename = candidate_images_presidente.get(candidate)
                if image_filename:
                    image_path = f'{IMAGES_DIR}/{image_filename}'
                    presidente_images_html += f'''
                    <div class="candidate-image-item">
                        <img src="{image_path}" alt="{candidate}" class="candidate-image">
                        <p class="candidate-name">{candidate}</p>
                    </div>
                    '''
            presidente_images_html += '</div>';
            tab_presidente_content += presidente_images_html

    except FileNotFoundError:
        tab_presidente_content = "<p>Error: El archivo de datos de presidente no se encontró. No se pudieron generar los gráficos presidenciales.</p>"
        print("Error: El archivo de presidente no se encontró en la ruta: {}".format(presidente_csv_file_path))
    except Exception as e:
        tab_presidente_content = f"<p>Ocurrió un error al procesar los datos de presidente: {e}</p>"
        print("Ocurrió un error al procesar el archivo de presidente: {}".format(e))

    # --- Resumen de resultados para Rolando Figueroa ---
    try:
        df_localidades_summary = pd.read_csv(localidades_csv_file_path)
        voto_cols_summary = [col for col in df_localidades_summary.columns if col not in ['Localidad', 'Departamento']]
        for col in voto_cols_summary:
            df_localidades_summary[col] = df_localidades_summary[col].replace('-', '0').astype(int)

        localidades_ganadas_rf = []
        localidades_perdidas_rf = []

        if 'Rolando Figueroa' in voto_cols_summary:
            for index, row in df_localidades_summary.iterrows():
                localidad = row['Localidad']
                votos_rf = row['Rolando Figueroa']

                max_votos_localidad = 0
                ganador_localidad = ""
                # Primero, encontrar el valor máximo de votos en la localidad
                for candidato in voto_cols_summary:
                    if row[candidato] > max_votos_localidad:
                        max_votos_localidad = row[candidato]
                        ganador_localidad = candidato

                # Ahora, determinar si Rolando Figueroa ganó o perdió
                # Consideramos que gana si tiene el máximo de votos y no es 0 (para evitar "ganar" con 0 votos)
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
                tab1_content += '<p style="color: #343a40;">No ganó en ninguna localidad.</p>'

            tab1_content += '<h3 style="color: #0056b3;">Localidades donde Rolando Figueroa perdió:</h3>'
            if localidades_perdidas_rf:
                tab1_content += '<ul style="color: #343a40;">'
                for loc in sorted(localidades_perdidas_rf):
                    tab1_content += f'<li>{loc}</li>'
                tab1_content += '</ul>'
            else:
                tab1_content += '<p style="color: #343a40;">Ganó en todas las localidades donde tuvo votos.</p>'
        else:
            tab1_content += '<p style="color: #dc3545;">Advertencia: La columna "Rolando Figueroa" no se encontró en el archivo de localidades para el resumen.</p>'

    except FileNotFoundError:
        tab1_content += "<p>Error: El archivo de localidades no se encontró para generar el resumen de Rolando Figueroa.</p>"
        print("Error: El archivo de localidades no se encontró para el resumen: {}".format(localidades_csv_file_path))
    except Exception as e:
        tab1_content += f"<p>Ocurrió un error al generar el resumen de Rolando Figueroa: {e}</p>"
        print("Ocurrió un error al generar el resumen: {}".format(e))

    # --- Estructura HTML con pestañas ---
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
            border-top-right-radius: 88px;
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
        .plotly-graph-container {{
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
            min-height: 500px;
        }}
        .plotly-graph-container .js-plotly-plot {{
            width: 100% !important;
            height: 100% !important;
            min-width: unset !important;
            min-height: unset !important;
        }}
        .plotly-graph-container .plotly .main-svg {{
            width: 100% !important;
            height: 100% !important;
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
        iframe {{
            border-radius: 10px;
            box-shadow: 0 6px 12px rgba(0,0,0,0.1);
            border: 1px solid #e0e0e0;
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
            .plotly-graph-container {{
                margin: 15px auto;
                border-radius: 0;
                box-shadow: none;
                padding: 5px;
                min-height: 350px;
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
    function openTab(evt, tabName) {{
        var i, tabcontent, tablinks;
        tabcontent = document.getElementsByClassName("tabcontent");
        for (i = 0; i < tabcontent.length; i++) {{
            tabcontent[i].style.display = "none";
        }}
        tablinks = document.getElementsByClassName("tablinks");
        for (i = 0; i < tablinks.length; i++) {{
            tablinks[i].className = tablinks[i].className.replace(" active", "");
        }}
        document.getElementById(tabName).style.display = "block";
        evt.currentTarget.className += " active";

        setTimeout(() => {{
            const activeTabContent = document.getElementById(tabName);
            const plotlyDivs = activeTabContent.querySelectorAll('.plotly-graph-container > div');

            plotlyDivs.forEach(div => {{
                if (typeof Plotly !== 'undefined' && div.data) {{
                    Plotly.relayout(div, {{
                        autosize: true,
                        height: 500,
                        margin: {{b: 100}}, // Asegurar margen inferior en el relayout (AJUSTADO AQUÍ TAMBIÉN)
                        legend: {{
                            orientation: "h",
                            yanchor: "bottom",
                            y: -0.2, // Leyenda un poco más arriba (AJUSTADO AQUÍ TAMBIÉN)
                            xanchor: "center",
                            x: 0.5
                        }},
                        xaxis: {{tickangle: 0, tickfont: {{size: 6}}}}
                    }}).catch(err => console.error("Error al redimensionar gráfico Plotly:", err));
                }}
            }});
            window.dispatchEvent(new Event('resize'));
        }}, 150);
    }}

    document.addEventListener('DOMContentLoaded', (event) => {{
        const gobernadorButton = document.querySelector('.tablinks.active');
        if (gobernadorButton) {{
            gobernadorButton.click();
        }}
    }});
</script>

</body>
</html>
"""
    # Guardar el archivo HTML final
    with open(output_html_path, 'w', encoding='utf-8') as f:
        f.write(full_html_content)
    print(f"Informe HTML generado exitosamente en: {output_html_path}")

except FileNotFoundError as e:
    print(
        f"Error: Uno de los archivos CSV no se encontró: {e}. Asegúrate de que los archivos estén en la ruta correcta.")
except pd.errors.EmptyDataError as e:
    print(f"Error: Uno de los archivos CSV está vacío: {e}. Asegúrate de que los archivos contengan datos.")
except pd.errors.ParserError as e:
    print(f"Error: Problema al analizar uno de los archivos CSV: {e}. Revisa el formato del archivo.")
except Exception as e:
    print(f"Ocurrió un error inesperado durante la ejecución del script: {e}")