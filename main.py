# -*- coding: utf-8 -*-
import pandas as pd
import plotly.express as px
import plotly.io as pio
import folium
import branca.colormap as cm
import re

# Ruta al archivo CSV
csv_file_path = 'Datos_Norte_NQN - departamentos.csv'
output_html_path = 'grafico_elecciones.html'
mapa_minas_path = 'mapa_minas.html'
localidades_csv_file_path = 'Datos_Norte_NQN - localidades.csv'
presidente_csv_file_path = 'Datos_Norte_NQN - Copia de presidente.csv'


try:
    # --- Procesamiento de datos de Departamentos ---
    df = pd.read_csv(csv_file_path)
    df_long = df.melt(id_vars=['Candidato'], var_name='Departamento', value_name='Votos')
    df_long['Departamento'] = df_long['Departamento'].str.capitalize()

    df_total_votos_depto = df_long.groupby('Departamento')['Votos'].sum().reset_index()
    df_total_votos_depto.rename(columns={'Votos': 'TotalVotosDepartamento'}, inplace=True)

    departamento_data = {}
    for depto in df_long['Departamento'].unique():
        total_votos = df_total_votos_depto[df_total_votos_depto['Departamento'] == depto]['TotalVotosDepartamento'].iloc[0]
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


    fig = px.bar(df_long,
                 x='Departamento',
                 y='Votos',
                 color='Candidato',
                 barmode='group',
                 title='Resultados Electorales por Departamento y Candidato',
                 labels={'Votos': 'Cantidad de Votos', 'Departamento': 'Departamento'},
                 hover_data={'Candidato': True, 'Departamento': True, 'Votos': True},
                 text='Votos',
                 opacity=0.7,
                 color_discrete_sequence=px.colors.qualitative.D3)
    fig.update_traces(textposition='outside', textangle=0)
    fig.update_xaxes(tickangle=90)
    fig.update_layout(autosize=True)

    df_total_votos = df.set_index('Candidato').sum(axis=1).reset_index(name='TotalVotos')
    df_total_votos.rename(columns={0: 'Candidato'}, inplace=True)

    fig2 = px.bar(df_total_votos,
                  x='Candidato',
                  y='TotalVotos',
                  color='Candidato',
                  title='Resultados electorales en la zona norte',
                  labels={'TotalVotos': 'Cantidad de Votos', 'Candidato': 'Candidato'},
                  text='TotalVotos',
                  opacity=0.7,
                  color_discrete_sequence=px.colors.qualitative.D3)
    fig2.update_traces(textposition='outside', textangle=0)
    fig2.update_layout(autosize=True)

    # --- Generar el mapa con Folium ---
    map_center = [-37.37, -70.56]
    m = folium.Map(location=map_center, zoom_start=9)

    geojson_files = [
        ("minasg.geojson", "Minas"),
        ("chosmalal.geojson", "Chos malal"),
        ("pehuenches.geojson", "Pehuenches"),
        ("ñorquin.geojson", "Ñorquin"),
        ("loncopue.geojson", "Loncopue")
    ]

    min_votos = min(data['TotalVotos'] for data in departamento_data.values())
    max_votos = max(data['TotalVotos'] for data in departamento_data.values())

    colormap = cm.LinearColormap(colors=['#f0f0f0', '#e31a1c', '#800026'],
                                 index=[min_votos, max_votos],
                                 caption='Votos Totales')


    def style_function(feature):
        depto_name = feature['properties']['nombre'].capitalize()
        total_votos = departamento_data.get(depto_name, {}).get('TotalVotos', 0)
        return {
            'fillColor': colormap(total_votos),
            'color': 'black',
            'weight': 1,
            'fillOpacity': 0.6
        }


    for geojson_file, depto_name in geojson_files:
        geojson_path = f'/Users/macbookair/Desktop/norte_ele/mapas/{geojson_file}'
        popup_content = create_popup_content(depto_name)
        folium.GeoJson(
            geojson_path,
            style_function=style_function,
            popup=folium.Popup(popup_content, max_width=300)
        ).add_to(m)

    m.fit_bounds(m.get_bounds())

    # Construir el HTML de la leyenda manualmente
    legend_html = f'''
    <div style="position: fixed;
                bottom: 50%;
                right: 10px;
                transform: translateY(50%);
                z-index:9999; font-size:14px;
                background-color:rgba(255, 255, 255, 0.8);
                padding: 10px;
                border: 1px solid #ced4da;
                border-radius: 5px;
                height: 100px;
                width: 100px;
                overflow: hidden;
                color: #343a40;
                ">
      &nbsp; <b>Votos Totales</b> <br>
      &nbsp; <i style="background:linear-gradient(to top, #800026, #e31a1c, #f0f0f0);
                    display:inline-block; width:20px; height:80px;
                    vertical-align:middle;"></i>
      <span style="vertical-align:middle;">
        {max_votos:.0f}<br>
        {(min_votos + max_votos) / 2:.0f}<br>
        {min_votos:.0f}
      </span>
    </div>
    '''

    m.get_root().html.add_child(folium.Element(legend_html))

    m.save(mapa_minas_path)

    # --- Generar contenido para la Pestaña 1 (Gobernador Provincial) ---
    tab1_content = f'<div class="plotly-graph-container">{pio.to_html(fig, full_html=False, include_plotlyjs="cdn", config={"responsive": True}, auto_play=False)}</div>'

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
        image_path = f'image/{image_filename}'
        gobernador_images_html += f'''
            <div class="candidate-image-item">
                <img src="{image_path}" alt="{candidate}" class="candidate-image">
                <p class="candidate-name">{candidate}</p>
            </div>
        '''
    gobernador_images_html += '</div>';
    tab1_content += gobernador_images_html
    tab1_content += f'<div class="plotly-graph-container">{pio.to_html(fig2, full_html=False, include_plotlyjs="cdn", config={"responsive": True}, auto_play=False)}</div>'
    tab1_content += '<h3 align="center" style="font-size:16px; color: #0056b3;"><b>Votos por departamento Norte Neuquino</b></h3>'
    tab1_content += '<div style="text-align: center;"><iframe src="mapa_minas.html" width="100%" height="400px" frameborder="0" style="display: inline-block;"></iframe></div>'

    # --- Generar gráficos por localidad ---
    try:
        df_localidades = pd.read_csv(localidades_csv_file_path)
        voto_cols = [col for col in df_localidades.columns if col not in ['Localidad', 'Departamento']]
        for col in voto_cols:
            df_localidades[col] = df_localidades[col].replace('-', '0').astype(int)

        all_localities = [
            "Huinganco", "Andacollo", "Los Miches", "Villa del Nahueve", "Las Ovejas",
            "Manzano Amargo", "Varvarco-Invernada Vieja", "Guañacos", "Colipilli", "El Huecu",
            "El Cholar", "Taquimilán", "Naunauco", "Tralaitue", "Caviahue-Copahue",
            "Coyuco-Cochico", "Cajón del Curí Leuvú", "Villa Curí Leuvú", "Chapua",
            "Chos Malal Fuera de Radio", "Chos Malal", "Chorriaca", "Huncal", "Quintuco",
            "Huarenchenque", "Cajón De Almaza", "Loncopué", "Buta Ranquil", "Barrancas",
            "Huantraico", "Rincón De Los Sauces", "Octavio Pico"
        ]

        for localidad_name in all_localities:
            df_current_locality = df_localidades[df_localidades['Localidad'] == localidad_name]
            if not df_current_locality.empty:
                df_current_locality_long = df_current_locality.melt(id_vars=['Localidad', 'Departamento'],
                                                                    var_name='Candidato',
                                                                    value_name='Votos')
                fig_locality = px.bar(df_current_locality_long,
                                      x='Candidato',
                                      y='Votos',
                                      color='Candidato',
                                      title=f'Resultados Electorales en {localidad_name}',
                                      labels={'Votos': 'Cantidad de Votos', 'Candidato': 'Candidato'},
                                      text='Votos',
                                      opacity=0.7,
                                      color_discrete_sequence=px.colors.qualitative.D3)
                fig_locality.update_traces(textposition='outside', textangle=0)
                fig_locality.update_layout(autosize=True)
                tab1_content += f'<div class="plotly-graph-container">{pio.to_html(fig_locality, full_html=False, include_plotlyjs="cdn", config={"responsive": True}, auto_play=False)}</div>'
                print(f"Gráfico de {localidad_name} generado exitosamente.")
            else:
                print(f"Localidad {localidad_name} no encontrada en el archivo de localidades.")

    except FileNotFoundError:
        print("Error: El archivo de localidades no se encontró en la ruta: {}".format(localidades_csv_file_path))
    except Exception as e:
        print("Ocurrió un error al procesar el archivo de localidades: {}".format(e))

    # --- Procesamiento de datos de Presidente y generación de gráfico ---
    try:
        df_presidente = pd.read_csv(presidente_csv_file_path, decimal=',', thousands='.')
        # Seleccionar solo las columnas de interés para los candidatos
        candidatos_presidente = ['Sergio Massa', 'Javier Milei', 'Patricia Bullrich', 'Juan Schiaretti',
                                 'Myriam Bregman']
        df_presidente_long = df_presidente.melt(id_vars=['Departamento'], value_vars=candidatos_presidente,
                                                var_name='Candidato', value_name='Votos')

        fig_presidente = px.bar(df_presidente_long,
                                x='Departamento',
                                y='Votos',
                                color='Candidato',
                                barmode='group',
                                title='Resultados Electorales Presidenciales por Departamento',
                                labels={'Votos': 'Cantidad de Votos', 'Departamento': 'Departamento'},
                                hover_data={'Candidato': True, 'Departamento': True, 'Votos': True},
                                text='Votos',
                                opacity=0.7,
                                color_discrete_sequence=px.colors.qualitative.D3)
        fig_presidente.update_traces(textposition='outside', textangle=0)
        fig_presidente.update_xaxes(tickangle=90)
        fig_presidente.update_layout(autosize=True)

        tab_presidente_content = f'<div class="plotly-graph-container">{pio.to_html(fig_presidente, full_html=False, include_plotlyjs="cdn", config={"responsive": True}, auto_play=False)}</div>'

        # Mapeo de candidatos a imágenes
        candidate_images = {
            'Sergio Massa': 'sergio massa.png',
            'Javier Milei': 'javier milei.png',
            'Patricia Bullrich': 'patricia.png',
            'Juan Schiaretti': 'juan.png',
            'Myriam Bregman': 'miryam.png'
        }

        # Generar HTML para las imágenes de los candidatos
        images_html = '<div class="candidate-images-container">';
        for candidate in candidatos_presidente:
            image_filename = candidate_images.get(candidate)
            if image_filename:
                image_path = f'image/{image_filename}'
                images_html += f'''
                <div class="candidate-image-item">
                    <img src="{image_path}" alt="{candidate}" class="candidate-image">
                    <p class="candidate-name">{candidate}</p>
                </div>
                '''
        images_html += '</div>';
        tab_presidente_content += images_html

    except FileNotFoundError:
        tab_presidente_content = "<p>Error: El archivo de datos de presidente no se encontró.</p>"
        print("Error: El archivo de presidente no se encontró en la ruta: {}".format(presidente_csv_file_path))
    except Exception as e:
        tab_presidente_content = f"<p>Ocurrió un error al procesar los datos de presidente: {e}</p>"
        print("Ocurrió un error al procesar el archivo de presidente: {}".format(e))

    # --- Resumen de resultados para Rolando Figueroa ---
    try:
        df_localidades = pd.read_csv(localidades_csv_file_path)
        voto_cols = [col for col in df_localidades.columns if col not in ['Localidad', 'Departamento']]
        for col in voto_cols:
            df_localidades[col] = df_localidades[col].replace('-', '0').astype(int)

        localidades_ganadas_rf = []
        localidades_perdidas_rf = []

        for index, row in df_localidades.iterrows():
            localidad = row['Localidad']
            votos_rf = row['Rolando Figueroa']

            max_votos_localidad = 0
            ganador_localidad = ""
            for candidato in voto_cols:
                if row[candidato] > max_votos_localidad:
                    max_votos_localidad = row[candidato]
                    ganador_localidad = candidato

            if ganador_localidad == 'Rolando Figueroa':
                localidades_ganadas_rf.append(localidad)
            else:
                localidades_perdidas_rf.append(localidad)

        tab1_content += '<hr><h2 style="color: #0056b3;">Resumen de Resultados para Rolando Figueroa por Localidad</h2>'
        tab1_content += '<h3 style="color: #0056b3;">Localidades donde Rolando Figueroa ganó:</h3>'
        if localidades_ganadas_rf:
            tab1_content += '<ul style="color: #343a40;">'
            for loc in localidades_ganadas_rf:
                tab1_content += f'<li>{loc}</li>'
            tab1_content += '</ul>'
        else:
            tab1_content += '<p style="color: #343a40;">No ganó en ninguna localidad.</p>'

        tab1_content += '<h3 style="color: #0056b3;">Localidades donde Rolando Figueroa perdió:</h3>'
        if localidades_perdidas_rf:
            tab1_content += '<ul style="color: #343a40;">'
            for loc in localidades_perdidas_rf:
                tab1_content += f'<li>{loc}</li>'
            tab1_content += '</ul>'
        else:
            tab1_content += '<p style="color: #343a40;">Ganó en todas las localidades.</p>'

    except FileNotFoundError:
        print("Error: El archivo de localidades no se encontró para el resumen: {}".format(localidades_csv_file_path))
    except Exception as e:
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
        }}
        /* Nuevas reglas para asegurar la responsividad de los gráficos Plotly */
        .plotly-graph-container .js-plotly-plot {{
            width: 100% !important;
            height: auto !important;
            min-width: unset !important;
            min-height: unset !important;
        }}
        .plotly-graph-container .plotly .main-svg {{
            width: 100% !important;
            height: auto !important;
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
            width: 100%; /* Permite que el item ocupe todo el ancho disponible */
            max-width: 120px; /* Pero no más de 120px */
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
        <button class="tablinks active" onclick="openTab(event, 'Gobernador')">Resultados elecciones 2023-Gobernador Provincial</button>
        <button class="tablinks" onclick="openTab(event, 'Presidente')">Resultados elecciones Presidente</button>
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
        window.dispatchEvent(new Event('resize'));
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
