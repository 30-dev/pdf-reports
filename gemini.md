# Contexto del Proyecto: Generador de Reportes PDF

## Resumen del Proyecto

Este proyecto es un microservicio desarrollado en Python con FastAPI para generar reportes en formato PDF. El objetivo principal es tomar datos en formato JSON, que representan los resultados de un autodiagnóstico de igualdad de género, y producir un informe visualmente atractivo y bien estructurado.

El servicio está diseñado para evolucionar, comenzando como una aplicación local y con planes de migrar a un entorno de nube (Google Cloud) para ofrecer funcionalidades más robustas como el almacenamiento de archivos y la generación de URLs seguras.

## Tecnologías Clave

- **Backend:** Python 3.11 con FastAPI.
- **Generación de PDF:** Biblioteca `reportlab`.
- **Servidor de Desarrollo:** `uvicorn`.
- **Contenido:** Archivos Markdown (`.md`) para las secciones de texto del reporte.
- **Datos:** Archivos JSON (`.json`) para alimentar las tablas y gráficos.

## Estructura del Proyecto

- `main.py`: El archivo principal de la aplicación FastAPI. Contiene la lógica para:
    - Definir los endpoints de la API (`/` y `/pdf`).
    - Leer y procesar los archivos de contenido y datos.
    - Utilizar `reportlab` para construir el documento PDF elemento por elemento (texto, imágenes, tablas, gráficos).
    - Ensamblar el PDF final en memoria y devolverlo como una respuesta HTTP.
- `requirements.txt`: Lista las dependencias de Python necesarias para el proyecto.
- `README`: Contiene la descripción general del proyecto, objetivos y etapas futuras.
- `assets/`: Almacena recursos estáticos como el logo (`digei_logo.png`).
- `content/`: Contiene los archivos Markdown que forman las partes narrativas del reporte.
    - `01_introduccion.md`: Texto introductorio del reporte.
    - `02_marco_dimensiones.md`: Descripción de las dimensiones evaluadas.
- `data/`: Contiene los archivos JSON con los datos para las visualizaciones.
    - `grafica_dimensiones.json`: Datos para el gráfico de barras horizontales que muestra el avance por dimensión.
    - `tabla_subdimensiones.json`: Datos detallados para la tabla que desglosa cada dimensión en subdimensiones y su nivel de cumplimiento.

## Flujo de Generación del PDF

1.  **Endpoint `/pdf`:** Cuando se llama a este endpoint, se inicia la función `create_pdf_in_memory`.
2.  **Estructura del Documento:** Se define una plantilla de documento con encabezados y pies de página personalizados.
3.  **Páginas de Portada:** Se generan las primeras páginas estáticas (logo, título del reporte, datos de la institución).
4.  **Contenido Markdown:** Se leen los archivos de la carpeta `content/`, se convierten a objetos de `reportlab` (párrafos, títulos) y se añaden al "story" del PDF.
5.  **Contenido de Datos (JSON):**
    - Se lee `tabla_subdimensiones.json` y se genera una tabla compleja y estilizada.
    - Se lee `grafica_dimensiones.json` para crear dos gráficos:
        - Un gráfico de barras horizontales que compara el desempeño de cada dimensión.
        - Un "velocímetro" (gauge chart) que muestra el promedio general de avance.
6.  **Construcción del PDF:** `reportlab` ensambla todos los elementos en un documento PDF en un buffer en memoria.
7.  **Respuesta:** El buffer del PDF se devuelve como una respuesta `application/pdf`, que el navegador puede mostrar directamente.

## Cómo Ejecutar Localmente

Para poner en marcha el servicio en un entorno de desarrollo local:

1.  Crear y activar un entorno virtual.
2.  Instalar las dependencias: `pip install -r requirements.txt`
3.  Iniciar el servidor: `uvicorn main:app --reload --port 8000`
4.  Acceder a `http://localhost:8000/pdf` en un navegador para ver el PDF generado.
