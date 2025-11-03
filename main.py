import io
import json
import re
from pathlib import Path
from typing import Optional
from html import escape
from fastapi import FastAPI, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Image, PageBreak, Table, TableStyle, Flowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.lib.utils import ImageReader
import math
from reportlab.graphics.shapes import Drawing, Line, Circle, Wedge, String, Polygon
from reportlab.graphics.charts.barcharts import HorizontalBarChart
from reportlab.graphics.charts.axes import XValueAxis
from reportlab.graphics.charts.spider import SpiderChart
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.rl_config import defaultEncoding

# Configurar encoding por defecto para soportar caracteres especiales
defaultEncoding = 'utf-8'

# Registrar fuentes con soporte Unicode
try:
    # Intentar usar fuentes del paquete reportlab que soporten Unicode
    import os
    import sys
    
    # Buscar fuentes en diferentes ubicaciones posibles
    font_paths = []
    
    # Ubicación de fuentes de reportlab
    try:
        import reportlab
        rl_dir = os.path.dirname(reportlab.__file__)
        font_paths.append(os.path.join(rl_dir, 'fonts', 'DejaVuSans.ttf'))
    except:
        pass
    
    # Otras ubicaciones comunes
    font_paths.extend([
        'DejaVuSans.ttf',  # Ruta relativa
        os.path.join(os.path.dirname(__file__), 'fonts', 'DejaVuSans.ttf'),  # Carpeta fonts local
        'C:/Windows/Fonts/DejaVuSans.ttf',  # Windows
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',  # Linux
    ])
    
    font_found = False
    for font_path in font_paths:
        try:
            if os.path.exists(font_path):
                bold_path = font_path.replace('DejaVuSans.ttf', 'DejaVuSans-Bold.ttf')
                pdfmetrics.registerFont(TTFont('DejaVuSans', font_path))
                if os.path.exists(bold_path):
                    pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', bold_path))
                else:
                    pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', font_path))  # Usar regular si no hay bold
                USE_CUSTOM_FONTS = True
                font_found = True
                print(f"✅ Fuentes Unicode cargadas desde: {font_path}")
                break
        except Exception as e:
            continue
    
    if not font_found:
        raise Exception("No se encontraron fuentes")
        
except Exception as e:
    # Si no se encuentran las fuentes personalizadas, usar las estándar
    USE_CUSTOM_FONTS = False
    print("⚠️  No se pudieron cargar fuentes personalizadas, usando fuentes estándar")

app = FastAPI()

# Configurar CORS para permitir peticiones desde el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000", "http://127.0.0.1:3001", "https://*.vercel.app", "*"],  # Ajusta según tu frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Paths ---
script_dir = Path(__file__).parent
LOGO_PATH = script_dir / "assets" / "digei_logo.png"
INTRO_PATH = script_dir / "content" / "01_introduccion.md"
MARCO_PATH = script_dir / "content" / "02_marco_dimensiones.md"
TABLE_DATA_PATH = script_dir / "data" / "tabla_subdimensiones.json"
CHART_DATA_PATH = script_dir / "data" / "grafica_dimensiones.json"
DIMENSION_DATA_PATH = script_dir / "data" / "data_dimensiones.json" # --- Reusable Markdown Parser ---
def parse_markdown_to_flowables(filepath, styles):
    '''Reads a markdown file with simple conventions and returns a list of flowables.'''
    flowables = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Si la línea está vacía, agregar un espaciador
            if not line:
                flowables.append(Spacer(1, 0.3*cm))
                continue

            # Handle inline styles first
            line = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line)
            line = re.sub(r'\*(.*?)\*', r'<i>\1</i>', line)

            if line.startswith('# '):
                flowables.append(Paragraph(line[2:], styles['h1']))
            elif line.startswith('## '):
                flowables.append(Paragraph(line[3:], styles['h2']))
            elif line.startswith('* '):
                flowables.append(Paragraph(line[2:], styles['li']))
            else:
                flowables.append(Paragraph(line, styles['p']))
    except FileNotFoundError:
        error_message = f"<b>Error:</b> Archivo de contenido no encontrado en <u>{filepath}</u>."
        flowables.append(Paragraph(error_message, styles['p']))

    return flowables

# --- Chart Generation Function ---
def create_dimensiones_chart(data, styles):
    """Creates a horizontal bar chart from the dimension data."""
    chart_title_text = "<b>PORCENTAJE DE INDICADORES ATENDIDOS POR DIMENSIÓN</b><br/><font size='-2'>(GRÁFICA 01)</font>"
    chart_title = Paragraph(chart_title_text, styles['chart_title'])
    
    # 1. Extract data and create labels
    chart_data = [item['pct_vs_100'] for item in data]
    
    short_names = [
        "Formación", "Investigación", "Comunicación", "Participación",
        "Condiciones Lab.", "Acoso/Violencia", "Corresponsabilidad",
        "Institucionalidad", "Infraestructura"
    ]
    
    # Create labels in the format "Dim 1 - Name"
    category_names = [f"Dim {i+1} - {name}" for i, name in enumerate(short_names[:len(chart_data)])]

    # 2. Create the chart object
    drawing = Drawing(width=17*cm, height=11*cm)
    
    bc = HorizontalBarChart()
    bc.x = 70
    bc.y = 50
    bc.height = 9*cm
    bc.width = 10*cm
    bc.data = [chart_data]

    # 3. Style the chart bars
    bc.barSpacing = 2
    bc.barWidth = 7
    bc.groupSpacing = 8
    bc.bars[0].fillColor = colors.HexColor("#6A1B9A")
    bc.bars[0].strokeColor = colors.transparent

    # 4. Add and style bar labels (percentages)
    bc.barLabelFormat = '%.1f%%'  # Format as "62.0%"
    bc.barLabels.nudge = 7      # Distance from the end of the bar
    bc.barLabels.fontName = 'Helvetica'
    bc.barLabels.fontSize = 7
    bc.barLabels.boxAnchor = 'w' # Anchor to the west (left) of the text

    # 5. Style Axes
    # Style X-axis (value axis)
    bc.valueAxis = XValueAxis()
    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 110 # Max value slightly larger to fit labels
    bc.valueAxis.valueStep = 10
    bc.valueAxis.labels.fontName = 'Helvetica'
    bc.valueAxis.labels.fontSize = 8
    
    # Style Y-axis (category axis)
    bc.categoryAxis.categoryNames = category_names
    bc.categoryAxis.labels.fontName = 'Helvetica'
    bc.categoryAxis.labels.fontSize = 8
    bc.categoryAxis.labels.boxAnchor = 'e'
    bc.categoryAxis.labels.dx = -5

    drawing.add(bc)

    # 6. Manually draw the 80% target line
    x_start = bc.x
    plot_width = bc.width
    value_range = bc.valueAxis.valueMax - bc.valueAxis.valueMin
    x_80 = x_start + (80 / value_range) * plot_width
    
    y_start = bc.y
    y_end = bc.y + bc.height

    target_line = Line(x_80, y_start, x_80, y_end)
    target_line.strokeColor = colors.red
    target_line.strokeWidth = 1
    target_line.strokeDashArray = [3, 1]
    drawing.add(target_line)

    # Return flowables
    return [
        chart_title,
        Spacer(1, 0.5*cm),
        drawing,
        PageBreak()
    ]

# --- Table Generation Function ---
def create_subdimensiones_table(data, styles):
    '''Creates a styled ReportLab Table from the JSON data.'''
    table_title = "SUBDIMENSIONES POR DIMENSIÓN <font size='-2'>(TABLA 01)</font>"
    table_description = data.get("descripcion", "")
    dimensiones = data.get("dimensiones", [])

    table_data = []
    headers = [
        Paragraph("<b>ID</b>", styles['table_header_small']),
        Paragraph("<b>Subdimensión</b>", styles['table_header_small']),
        Paragraph("<b>Indicadores<br/>(Total)</b>", styles['table_header_small']),
        Paragraph("<b>Indicadores<br/>(Atendidos)</b>", styles['table_header_small']),
        Paragraph("<b>% vs<br/>100</b>", styles['table_header_small']),
        Paragraph("<b>% vs<br/>80</b>", styles['table_header_small']),
        Paragraph("<b>Semáforo</b>", styles['table_header_small'])
    ]
    table_data.append(headers)

    table_styles = [
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_COLOR),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, MEDIUM_GRAY),
        ('ALIGN', (6, 0), (6, -1), 'CENTER'),  # Asegurar que columna Semáforo esté centrada
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]
    
    semaforo_colors = {
        "alto": colors.HexColor("#4CAF50"),
        "medio": colors.HexColor("#FFC107"),
        "bajo": colors.HexColor("#F44336")
    }

    row_index = 1
    for dimension in dimensiones:
        dim_name = f"<b>{dimension['id']}. {dimension['nombre']}</b>"
        table_data.append([Paragraph(dim_name, styles['table_text'])])
        
        # Calcular el rango de filas para esta dimensión (título + subdimensiones)
        dimension_start_row = row_index
        dimension_end_row = row_index + len(dimension['subdimensiones'])
        
        table_styles.extend([
            ('SPAN', (0, row_index), (-1, row_index)),
            ('BACKGROUND', (0, row_index), (-1, row_index), colors.HexColor("#F0F0F0")),
            ('ALIGN', (0, row_index), (0, row_index), 'LEFT'),
            # Evitar separación de página entre título y subdimensiones
            ('KEEPWITHNEXT', (0, row_index), (-1, row_index), True)
        ])
        
        # Si hay más de 3 subdimensiones, aplicar keep together al grupo
        if len(dimension['subdimensiones']) > 0:
            table_styles.append(('KEEPTOGETHER', (0, dimension_start_row), (-1, dimension_end_row), True))
        
        row_index += 1

        for i, sub in enumerate(dimension['subdimensiones']):
            table_data.append([
                Paragraph(str(sub['id']), styles['table_text']),
                Paragraph(sub['nombre'], styles['table_text']),
                str(sub['indicadores_total']),
                str(sub['indicadores_atendidos']),
                f"{sub['porcentaje_vs_100']:.1f}%",
                f"{sub['porcentaje_vs_80']:.1f}%",
                Paragraph(sub['semaforo'].capitalize(), styles['table_text_centered'])
            ])
            table_styles.append(('ALIGN', (1, row_index), (1, row_index), 'LEFT'))
            table_styles.append(('ALIGN', (6, row_index), (6, row_index), 'CENTER'))  # Centrar columna Semáforo
            
            # Para la primera subdimensión, mantener con el título
            if i == 0:
                table_styles.append(('KEEPWITHPREV', (0, row_index), (-1, row_index), True))
            
            # Zebra striping - filas alternadas
            if row_index % 2 == 0:
                table_styles.append(('BACKGROUND', (0, row_index), (5, row_index), LIGHT_GRAY))
            
            semaforo_color = semaforo_colors.get(sub['semaforo'], colors.white)
            table_styles.append(('BACKGROUND', (6, row_index), (6, row_index), semaforo_color))
            row_index += 1

    col_widths = [1.5*cm, 6*cm, 2*cm, 2*cm, 1.5*cm, 1.5*cm, 2*cm]
    gen_table = Table(table_data, colWidths=col_widths, hAlign='LEFT')
    gen_table.setStyle(TableStyle(table_styles))

    flowables = [
        Spacer(1, 1*cm),
        Paragraph(table_title, styles['h2_centered']),
    ]
    if table_description:
        flowables.append(Paragraph(table_description, styles['p']))
        flowables.append(Spacer(1, 0.25*cm))

    flowables.append(gen_table)
    flowables.append(PageBreak())
    return flowables


# --- Gauge Chart Generation ---
def create_gauge_chart(data, styles):
    """Creates a gauge chart showing the overall average progress."""
    
    # 1. Calculate the average value
    values = [item['pct_vs_100'] for item in data]
    avg_value = sum(values) / len(values) if values else 0
    
    # 2. Setup geometry
    d = Drawing(width=10*cm, height=6.5*cm)
    cx, cy = 5*cm, 1.5*cm # Center of the gauge
    radius = 4*cm

    # 3. Draw background wedges
    d.add(Wedge(cx, cy, radius, 180, 90, fillColor=colors.HexColor("#F44336"))) # Red 0-50
    d.add(Wedge(cx, cy, radius, 90, 36, fillColor=colors.HexColor("#FFC107"))) # Yellow 50-80
    d.add(Wedge(cx, cy, radius, 36, 0, fillColor=colors.HexColor("#4CAF50"))) # Green 80-100
    
    # Add a white inner circle to make it a donut
    d.add(Circle(cx, cy, radius * 0.7, fillColor=colors.white, strokeColor=colors.lightgrey))

    # 4. Draw the needle
    value_angle_rad = math.radians(180 - (avg_value / 100.0) * 180)
    needle_end_x = cx + (radius * 0.9) * math.cos(value_angle_rad)
    needle_end_y = cy + (radius * 0.9) * math.sin(value_angle_rad)
    
    d.add(Line(cx, cy, needle_end_x, needle_end_y, strokeColor=colors.black, strokeWidth=2))
    d.add(Circle(cx, cy, 5, fillColor=colors.black))

    # 5. Add labels
    d.add(String(cx - radius - 10, cy, "0%", textAnchor="end", fillColor=colors.grey))
    d.add(String(cx + radius + 10, cy, "100%", textAnchor="start", fillColor=colors.grey))
    
    value_str = f"{avg_value:.1f}%"
    d.add(String(cx, cy, value_str, textAnchor="middle", fontSize=18, fontName="Helvetica-Bold"))

    return [
        Spacer(1, 1*cm),
        d,
        PageBreak()
    ]


class SemaforoDIGEI_Lite(Flowable):
    """
    Semáforo vertical (arriba VERDE, medio AMARILLO, abajo ROJO)
    - Resalta el 'current' con aro morado (#6A1B9A)
    - Muestra valor grande (%)
    - Leyenda 'Niveles' en vertical (Alto / Medio / Bajo)
    - Sin título interno (gestiónalo fuera)
    - Sin meta
    """
    def __init__(self, current, thresholds=(40, 70), unit="%",
                 width=10*cm, height=6*cm, no_border=False):
        super().__init__()
        self.current = current
        self.t_red, self.t_yellow = thresholds
        self.unit = unit
        self.width = width
        self.height = height
        self.no_border = no_border
        # Colores
        self.c_red     = colors.HexColor("#E53935")
        self.c_yellow  = colors.HexColor("#FDD835")
        self.c_green   = colors.HexColor("#43A047")
        self.c_current = colors.HexColor("#6A1B9A")
        self.c_value   = colors.HexColor("#111111")
        self.c_muted   = colors.HexColor("#666666")
        self.c_border  = colors.HexColor("#E0E0E0")

    def wrap(self, aw, ah):
        return self.width, self.height

    def _state_for(self, v):
        if v < self.t_red:      return "red"
        elif v < self.t_yellow: return "yellow"
        else:                   return "green"

    def draw(self):
        c = self.canv
        W, H = self.width, self.height

        # Card base
        if not self.no_border:
            c.setFillColor(colors.white)
            c.setStrokeColor(self.c_border)
            c.rect(0, 0, W, H, fill=1, stroke=1)

        pad = 0.8*cm
        col_w = 3.0*cm
        left_x, left_y = pad, pad
        left_h = H - 2*pad

        # Focos pequeños + espacio
        r = min(0.40*cm, left_h/9.0)
        gap = max(0.35*cm, (left_h - 6*r)/2.0)
        cx = left_x + 0.9*cm
        lab_x = cx + r + 0.30*cm

        cy_top    = left_y + left_h - r
        cy_middle = cy_top - (2*r + gap)
        cy_bottom = cy_middle - (2*r + gap)

        centers = {"green":(cx,cy_top), "yellow":(cx,cy_middle), "red":(cx,cy_bottom)}

        # 3 focos
        c.setStrokeColor(colors.transparent)
        c.setFillColor(self.c_green);  c.circle(*centers["green"],  r, fill=1, stroke=0)
        c.setFillColor(self.c_yellow); c.circle(*centers["yellow"], r, fill=1, stroke=0)
        c.setFillColor(self.c_red);    c.circle(*centers["red"],    r, fill=1, stroke=0)

        # Etiquetas sutiles
        c.setFont("Helvetica", 8); c.setFillColor(self.c_muted)
        c.drawString(lab_x, cy_top-3,    "Alto")
        c.drawString(lab_x, cy_middle-3, "Medio")
        c.drawString(lab_x, cy_bottom-3, "Bajo")

        # Aro del estado actual
        st = self._state_for(self.current)
        ccx, ccy = centers[st]
        c.setStrokeColor(self.c_current); c.setLineWidth(3)
        c.circle(ccx, ccy, r + 0.16*cm, fill=0, stroke=1)

        # Columna derecha (valor + leyenda)
        right_x = left_x + col_w + 0.8*cm

        # Valor grande
        c.setFont("Helvetica-Bold", 30); c.setFillColor(self.c_value)
        val = f"{int(self.current)}{self.unit}" if self.unit else f"{int(self.current)}"
        c.drawString(right_x, H - 1.4*cm, val)

        # Leyenda "Niveles" vertical (con reglas)
        base_y = H - 2.4*cm
        c.setFont("Helvetica-Bold", 8); c.setFillColor(self.c_muted)
        c.drawString(right_x, base_y, "Niveles:")
        c.setFont("Helvetica", 8)
        c.drawString(right_x, base_y - 0.45*cm, "• Alto  ≥ 70")
        c.drawString(right_x, base_y - 0.90*cm, "• Medio 40–69")
        c.drawString(right_x, base_y - 1.35*cm, "• Bajo  < 40")

def create_semaforo_flowables(doc, styles, pct_vs_100=0, pct_vs_80=0):
    '''Creates the two-column semaforo layout.'''
    
    card_width = doc.width * 0.45
    space_width = doc.width * 0.1
    
    # Titles for the cards
    title_a_text = "<b>PORCENTAJE DE INDICADORES ATENDIDOS RESPECTO AL 100% DE INDICADORES</b>"
    title_b_text = "<b>PORCENTAJE DE INDICADORES ATENDIDOS RESPECTO AL 80% DE INDICADORES</b>"
    title_a = Paragraph(title_a_text, styles['card_title'])
    title_b = Paragraph(title_b_text, styles['card_title'])

    # Use dynamic data from parameters
    card_a = SemaforoDIGEI_Lite(current=pct_vs_100, unit="%", width=card_width, height=6*cm)
    card_b = SemaforoDIGEI_Lite(current=pct_vs_80, unit="%", width=card_width, height=6*cm)
    
    # Create a table with titles and cards
    data = [[title_a, None, title_b],
            [card_a, None, card_b]]

    tbl = Table(data,
                colWidths=[card_width, space_width, card_width],
                rowHeights=[None, None], # Let reportlab calculate row heights
                hAlign='LEFT',
                style=TableStyle([
                    ("VALIGN", (0,0), (-1,-1), "TOP"),
                    # Add some space between title and card
                    ("BOTTOMPADDING", (0, 0), (0, 0), 6),
                    ("BOTTOMPADDING", (2, 0), (2, 0), 6),
                ]))
    
    return [
        Spacer(1, 1*cm),
        Paragraph("INDICADORES DE NIVEL DE CUMPLIMIENTO", styles['h2_centered']),
        Spacer(1, 0.5*cm),
        tbl,
        PageBreak()
    ]

def create_dimension_detail_flowables(dimension_data, styles, doc_width):
    flowables = []

    # Title for the dimension
    dimension_name = dimension_data["dimension_nombre"].upper()
    flowables.append(Paragraph(f"<b>{dimension_name}</b>", styles['h2']))
    flowables.append(Spacer(1, 0.2*cm))

    # Title for the SemaforoDIGEI_Lite card
    dimension_id_match = re.match(r'(\d+)\.', dimension_data["dimension_nombre"])
    dimension_id = dimension_id_match.group(1) if dimension_id_match else "N/A"
    
    card_title_text = f"PORCENTAJE DE INDICADORES ATENDIDOS EN LA DIMENSIÓN"
    flowables.append(Paragraph(card_title_text, styles['chart_title'])) # Título alineado a la izquierda
    flowables.append(Spacer(1, 0.2*cm))

    # Percentage attended as a SemaforoDIGEI_Lite card
    porcentaje_atendido = dimension_data["porcentaje_atendido"]
    
    # Define thresholds for this specific semaforo
    thresholds = (50, 80) # Red below 50, Yellow 50-80, Green above 80

    # Create the semaforo card centered and without border for individual dimensions
    from reportlab.platypus import Table, TableStyle
    semaforo_card = SemaforoDIGEI_Lite(current=porcentaje_atendido, thresholds=thresholds, unit="%", width=7*cm, height=4*cm, no_border=True)
    
    # Center the semaforo using a table with explicit width control
    centered_semaforo = Table([[semaforo_card]], colWidths=[doc_width], hAlign='CENTER')
    centered_semaforo.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
    ]))
    flowables.append(centered_semaforo)
    flowables.append(Spacer(1, 0.5*cm))

    # Unattended points table
    unattended_points = dimension_data["puntos_no_atendidos"]
    if unattended_points:
        flowables.append(Paragraph("Las siguientes preguntas han sido identificadas como áreas de oportunidad porque sus respuestas indican que aún no se han cumplido completamente (por ejemplo, fueron respondidas como \"No\" o \"Parcialmente\"). Estas representan puntos clave para fortalecer el compromiso institucional con la igualdad de género.", styles['p']))
        flowables.append(Spacer(1, 0.2*cm))

        # Title for the unattended questions table
        dimension_id_match = re.match(r'(\d+)\.', dimension_data["dimension_nombre"])
        dimension_id = dimension_id_match.group(1) if dimension_id_match else "N/A"
        table_title_text = f"PREGUNTAS NO ATENDIDAS POR SUBDIMENSIÓN <font size='-2'>(TABLA {dimension_id})</font>"
        flowables.append(Paragraph(table_title_text, styles['chart_title'])) # Using chart_title style for consistency
        flowables.append(Spacer(1, 0.2*cm))

        table_data = []
        table_styles_list = []
        current_row_index = 0
        question_number = 1  # Numeración continua para todas las preguntas

        for item in unattended_points:
            # Subdimension as a header row (solo si hay preguntas)
            if 'preguntas' in item and item['preguntas']:
                table_data.append([Paragraph(f"<b>{item['subdimension']}</b>", styles['table_header']), ''])
                table_styles_list.append(('SPAN', (0, current_row_index), (1, current_row_index)))
                table_styles_list.append(('BACKGROUND', (0, current_row_index), (1, current_row_index), LIGHT_GRAY))
                table_styles_list.append(('LEFTPADDING', (0, current_row_index), (1, current_row_index), 8))
                current_row_index += 1
                
                # Agregar preguntas
                for pregunta in item['preguntas']:
                    # Asegurar que el texto sea una cadena Unicode válida
                    pregunta_text = str(pregunta) if pregunta else ""
                    # Saltar si es un texto muy largo (probablemente descripción)
                    if len(pregunta_text) > 300:
                        continue
                    table_data.append([str(question_number), Paragraph(pregunta_text, styles['table_text'])])
                    current_row_index += 1
                    question_number += 1

        # General table styles
        table_styles_list.extend([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 5),
            ('RIGHTPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('GRID', (0,0), (-1,-1), 1, colors.lightgrey),
        ])
        
        col_widths = [doc_width * 0.05, doc_width * 0.95 - 1*cm] # Small first column for bullet, large second for text
        unattended_table = Table(table_data, colWidths=col_widths, hAlign='LEFT')
        unattended_table.setStyle(TableStyle(table_styles_list))
        flowables.append(unattended_table)
    else:
        flowables.append(Paragraph("No hay puntos no atendidos para esta dimensión.", styles['p']))

    flowables.append(PageBreak())
    return flowables

    flowables.append(PageBreak())
    return flowables

def create_special_section_flowables(styles, doc_width):
    flowables = []

    # Main section title
    flowables.append(Paragraph("INFORMACIÓN AMPLIADA POR DIMENSIÓN", styles['h1']))
    flowables.append(Spacer(1, 1*cm))

    # Process detalles_dim_4.json
    try:
        with open(script_dir / "data" / "detalles_dim_4.json", 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        dimension_name = data.get("dimension_nombre", "Dimensión Desconocida")
        table_title_text = f"BRECHA POR GÉNERO EN {dimension_name.upper()} <font size='-2'>(TABLA 01)</font>"
        flowables.append(Paragraph(table_title_text, styles['chart_title']))
        flowables.append(Spacer(1, 0.2*cm))

        table_data = []
        # Headers
        table_data.append([
            Paragraph("Pregunta", styles['p']),
            Paragraph("Grupo/Categoría", styles['p']),
            Paragraph("Mujeres", styles['p']),
            Paragraph("Hombres", styles['p']),
            Paragraph("Brecha", styles['p'])
        ])
        for item in data["brecha_por_genero"]:
            table_data.append([
                Paragraph(item["pregunta"], styles['p']),
                Paragraph(item["grupo_o_categoria"], styles['p']),
                str(item["mujeres"]),
                str(item["hombres"]),
                str(item["brecha"])
            ])
        
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#E0E0E0")), # Header background
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
        ])
        
        table = Table(table_data, colWidths=[doc_width*0.3, doc_width*0.2, doc_width*0.15, doc_width*0.15, doc_width*0.1], hAlign='LEFT')
        table.setStyle(table_style)
        flowables.append(table)
        flowables.append(Spacer(1, 1*cm)) # Space after table

    except FileNotFoundError:
        flowables.append(Paragraph("Error: detalles_dim_4.json no encontrado.", styles['p']))
    except Exception as e:
        flowables.append(Paragraph(f"Error al procesar detalles_dim_4.json: {e}", styles['p']))

    # Process detalles_dim_5.json
    try:
        with open(script_dir / "data" / "detalles_dim_5.json", 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        table_title_text = f"SALARIO PROMEDIO POR CATEGORÍA <font size='-2'>(TABLA 02)</font>"
        flowables.append(Paragraph(table_title_text, styles['chart_title']))
        flowables.append(Spacer(1, 0.2*cm))

        table_data = []
        # Headers
        table_data.append([
            Paragraph("Categoría", styles['p']),
            Paragraph("Hombres", styles['p']),
            Paragraph("Mujeres", styles['p']),
            Paragraph("Brecha Salarial", styles['p'])
        ])
        for item in data["salario_promedio_por_categoria"]:
            table_data.append([
                Paragraph(item["categoría"], styles['p']),
                item["hombres"],
                item["mujeres"],
                item["brecha_salarial"]
            ])
        
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#E0E0E0")), # Header background
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
        ])
        
        table = Table(table_data, colWidths=[doc_width*0.3, doc_width*0.2, doc_width*0.2, doc_width*0.2], hAlign='LEFT')
        table.setStyle(table_style)
        flowables.append(table)
        flowables.append(Spacer(1, 1*cm)) # Space after table

    except FileNotFoundError:
        flowables.append(Paragraph("Error: detalles_dim_5.json no encontrado.", styles['p']))
    except Exception as e:
        flowables.append(Paragraph(f"Error al procesar detalles_dim_5.json: {e}", styles['p']))

    # Process detalles_dim_6_1.json
    try:
        with open(script_dir / "data" / "detalles_dim_6_1.json", 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        table_title_text = f"QUEJAS DE ACOSO <font size='-2'>(TABLA 03)</font>"
        flowables.append(Paragraph(table_title_text, styles['chart_title']))
        flowables.append(Spacer(1, 0.2*cm))

        table_data = []
        # Headers
        table_data.append([
            Paragraph("Tipo de Queja", styles['p']),
            Paragraph("Mujeres", styles['p']),
            Paragraph("Hombres", styles['p'])
        ])
        for item in data["resumen_de_quejas"]:
            table_data.append([
                Paragraph(item["tipo_de_queja"], styles['p']),
                str(item["mujeres"]),
                str(item["hombres"])
            ])
        
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#E0E0E0")), # Header background
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
        ])
        
        table = Table(table_data, colWidths=[doc_width*0.5, doc_width*0.2, doc_width*0.2], hAlign='LEFT')
        table.setStyle(table_style)
        flowables.append(table)
        flowables.append(Spacer(1, 1*cm)) # Space after table

    except FileNotFoundError:
        flowables.append(Paragraph("Error: detalles_dim_6_1.json no encontrado.", styles['p']))
    except Exception as e:
        flowables.append(Paragraph(f"Error al procesar detalles_dim_6_1.json: {e}", styles['p']))

    # Process detalles_dim_6_2.json
    try:
        with open(script_dir / "data" / "detalles_dim_6_2.json", 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        table_title_text = f"ATENCIONES POR DIMENSIÓN DE ACOSO <font size='-2'>(TABLA 04)</font>"
        flowables.append(Paragraph(table_title_text, styles['chart_title']))
        flowables.append(Spacer(1, 0.2*cm))

        table_data = []
        # Headers
        table_data.append([
            Paragraph("Tipo de Atención", styles['p']),
            Paragraph("Mujeres", styles['p'])
        ])
        for item in data["atenciones_dimension_acoso"]:
            table_data.append([
                Paragraph(item["tipo_de_atención"], styles['p']),
                str(item["mujeres"])
            ])
        
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#E0E0E0")), # Header background
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
        ])
        
        table = Table(table_data, colWidths=[doc_width*0.7, doc_width*0.2], hAlign='LEFT')
        table.setStyle(table_style)
        flowables.append(table)
        flowables.append(Spacer(1, 1*cm)) # Space after table

    except FileNotFoundError:
        flowables.append(Paragraph("Error: detalles_dim_6_2.json no encontrado.", styles['p']))
    except Exception as e:
        flowables.append(Paragraph(f"Error al procesar detalles_dim_6_2.json: {e}", styles['p']))

    flowables.append(PageBreak())
    return flowables

def create_special_section_with_data(data, styles, doc_width):
    """Crea la sección especial usando datos reales del request"""
    flowables = []
    
    # Título de la sección
    flowables.append(Spacer(1, 1*cm))
    flowables.append(Paragraph("<b>DATOS COMPLEMENTARIOS</b>", styles['h1']))
    flowables.append(Spacer(1, 0.5*cm))
    
    # --- Tabla de Composición por Sexo (Dimensión 4) ---
    if data.composicion_sexo and len(data.composicion_sexo) > 0:
        table_title_text = "COMPOSICIÓN POR SEXO <font size='-2'>(TABLA 02)</font>"
        flowables.append(Paragraph(table_title_text, styles['chart_title']))
        flowables.append(Spacer(1, 0.2*cm))
        
        table_data = []
        table_data.append([
            Paragraph("<b>Pregunta</b>", styles['table_header']),
            Paragraph("<b>Descripción</b>", styles['table_header']),
            Paragraph("<b>Mujeres</b>", styles['table_header']),
            Paragraph("<b>Hombres</b>", styles['table_header']),
            Paragraph("<b>Diferencia</b>", styles['table_header'])
        ])
        
        for item in data.composicion_sexo:
            item_dict = item if isinstance(item, dict) else item.__dict__
            descripcion = item_dict.get('descripcion', '') or 'N/A'
            
            table_data.append([
                Paragraph(item_dict.get('pregunta_texto', 'N/A'), styles['table_text']),
                Paragraph(descripcion, styles['table_text']),
                str(item_dict.get('cantidad_mujeres', 0)),
                str(item_dict.get('cantidad_hombres', 0)),
                str(item_dict.get('diferencia', 0))
            ])
        
        table_style_commands = [
            ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_COLOR),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 1), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.5, MEDIUM_GRAY),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]
        
        # Zebra striping
        for i in range(1, len(table_data)):
            if i % 2 == 0:
                table_style_commands.append(('BACKGROUND', (0, i), (-1, i), LIGHT_GRAY))
        
        table_style = TableStyle(table_style_commands)
        
        table = Table(table_data, colWidths=[doc_width*0.25, doc_width*0.25, doc_width*0.15, doc_width*0.15, doc_width*0.1], hAlign='LEFT')
        table.setStyle(table_style)
        flowables.append(table)
        flowables.append(PageBreak())  # Separar en página diferente
    
    # --- Tabla de Salarios (Dimensión 5) ---
    if data.salarios and len(data.salarios) > 0:
        table_title_text = "BRECHA SALARIAL POR CATEGORÍA <font size='-2'>(TABLA 03)</font>"
        flowables.append(Paragraph(table_title_text, styles['chart_title']))
        flowables.append(Spacer(1, 0.2*cm))
        
        table_data = []
        table_data.append([
            Paragraph("<b>Categoría</b>", styles['table_header']),
            Paragraph("<b>Hombres</b>", styles['table_header']),
            Paragraph("<b>Mujeres</b>", styles['table_header']),
            Paragraph("<b>Diferencia</b>", styles['table_header'])
        ])
        
        for item in data.salarios:
            item_dict = item if isinstance(item, dict) else item.__dict__
            
            # Formatear valores como moneda mexicana
            hombres = item_dict.get('cantidad_hombres', 0)
            mujeres = item_dict.get('cantidad_mujeres', 0)
            diferencia = item_dict.get('diferencia', 0)
            
            table_data.append([
                Paragraph(item_dict.get('categoria_nombre', 'N/A'), styles['table_text']),
                f"${hombres:,.2f}",
                f"${mujeres:,.2f}",
                f"${diferencia:,.2f}"
            ])
        
        table_style_commands = [
            ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_COLOR),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, MEDIUM_GRAY),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]
        
        # Zebra striping
        for i in range(1, len(table_data)):
            if i % 2 == 0:
                table_style_commands.append(('BACKGROUND', (0, i), (-1, i), LIGHT_GRAY))
        
        table = Table(table_data, colWidths=[doc_width*0.4, doc_width*0.2, doc_width*0.2, doc_width*0.15], hAlign='LEFT')
        table.setStyle(TableStyle(table_style_commands))
        flowables.append(table)
        flowables.append(PageBreak())  # Separar en página diferente
    
    # --- Tabla de Quejas (Dimensión 6) ---
    if data.quejas:
        quejas_dict = data.quejas if isinstance(data.quejas, dict) else data.quejas.__dict__
        
        table_title_text = "QUEJAS DE ACOSO Y HOSTIGAMIENTO <font size='-2'>(TABLA 04)</font>"
        flowables.append(Paragraph(table_title_text, styles['chart_title']))
        flowables.append(Spacer(1, 0.2*cm))
        
        table_data = []
        table_data.append([
            Paragraph("<b>Tipo de Queja</b>", styles['table_header']),
            Paragraph("<b>Mujeres</b>", styles['table_header']),
            Paragraph("<b>Hombres</b>", styles['table_header'])
        ])
        
        # Quejas de personal
        table_data.append([
            Paragraph("Quejas Personal - Recibidas", styles['table_text']),
            str(quejas_dict.get('quejas_personal_recibidas_mujeres', 0)),
            str(quejas_dict.get('quejas_personal_recibidas_hombres', 0))
        ])
        table_data.append([
            Paragraph("Quejas Personal - Resueltas", styles['table_text']),
            str(quejas_dict.get('quejas_personal_resueltas_mujeres', 0)),
            str(quejas_dict.get('quejas_personal_resueltas_hombres', 0))
        ])
        
        # Quejas de estudiantes
        table_data.append([
            Paragraph("Quejas Estudiantes - Recibidas", styles['table_text']),
            str(quejas_dict.get('quejas_estudiantes_recibidas_mujeres', 0)),
            str(quejas_dict.get('quejas_estudiantes_recibidas_hombres', 0))
        ])
        table_data.append([
            Paragraph("Quejas Estudiantes - Resueltas", styles['table_text']),
            str(quejas_dict.get('quejas_estudiantes_resueltas_mujeres', 0)),
            str(quejas_dict.get('quejas_estudiantes_resueltas_hombres', 0))
        ])
        
        table_style_commands = [
            ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_COLOR),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, MEDIUM_GRAY),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]
        
        # Zebra striping
        for i in range(1, len(table_data)):
            if i % 2 == 0:
                table_style_commands.append(('BACKGROUND', (0, i), (-1, i), LIGHT_GRAY))
        
        table = Table(table_data, colWidths=[doc_width*0.5, doc_width*0.2, doc_width*0.2], hAlign='LEFT')
        table.setStyle(TableStyle(table_style_commands))
        flowables.append(table)
        flowables.append(Spacer(1, 0.5*cm))  # Espacio pequeño entre quejas y atenciones
    
    # --- Tabla de Atenciones (Dimensión 6) ---
    if data.atenciones:
        atenciones_dict = data.atenciones if isinstance(data.atenciones, dict) else data.atenciones.__dict__
        
        table_title_text = "ATENCIONES A MUJERES <font size='-2'>(TABLA 05)</font>"
        flowables.append(Paragraph(table_title_text, styles['chart_title']))
        flowables.append(Spacer(1, 0.2*cm))
        
        table_data = []
        table_data.append([
            Paragraph("<b>Tipo de Atención</b>", styles['table_header']),
            Paragraph("<b>Cantidad</b>", styles['table_header'])
        ])
        
        table_data.append([
            Paragraph("Atención en Reclutamiento", styles['table_text']),
            str(atenciones_dict.get('atencion_reclutamiento', 0))
        ])
        table_data.append([
            Paragraph("Atención en Procesos Laborales", styles['table_text']),
            str(atenciones_dict.get('atencion_procesos_laborales', 0))
        ])
        table_data.append([
            Paragraph("Atención a Estudiantes", styles['table_text']),
            str(atenciones_dict.get('atencion_estudiantes', 0))
        ])
        
        table_style_commands = [
            ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_COLOR),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, MEDIUM_GRAY),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]
        
        # Zebra striping
        for i in range(1, len(table_data)):
            if i % 2 == 0:
                table_style_commands.append(('BACKGROUND', (0, i), (-1, i), LIGHT_GRAY))
        
        table = Table(table_data, colWidths=[doc_width*0.6, doc_width*0.3], hAlign='LEFT')
        table.setStyle(TableStyle(table_style_commands))
        flowables.append(table)
        flowables.append(Spacer(1, 1*cm))
    
    flowables.append(PageBreak())
    return flowables

# Función removida - autodiagnóstico ya no se incluye en el reporte

# Funciones removidas - encuestas ya no se incluyen en el reporte

# --- Pydantic Models ---
class ReporteData(BaseModel):
    organizacion: dict
    metadata: dict
    dimensiones: list
    grafica_dimensiones: list
    composicion_sexo: Optional[list] = None
    salarios: Optional[list] = None
    quejas: Optional[dict] = None
    atenciones: Optional[dict] = None

# --- Paleta de colores profesional para impresión ---
PRIMARY_COLOR = colors.HexColor("#757575")  # Gris tenue oscuro para encabezados
SECONDARY_COLOR = colors.HexColor("#616161")  # Gris medio
ACCENT_COLOR = colors.HexColor("#9E9E9E")  # Gris claro
SUCCESS_COLOR = colors.HexColor("#4CAF50")  # Verde (mantener para semáforos)
WARNING_COLOR = colors.HexColor("#FFC107")  # Amarillo (mantener para semáforos)
DANGER_COLOR = colors.HexColor("#F44336")  # Rojo (mantener para semáforos)
LIGHT_GRAY = colors.HexColor("#FAFAFA")  # Gris muy claro para fondos alternados
MEDIUM_GRAY = colors.HexColor("#BDBDBD")  # Gris medio para bordes

# --- Índice de Contenidos ---
def create_table_of_contents(data, styles):
    """Crea un índice de contenidos del reporte en formato formal"""
    flowables = []
    
    flowables.append(Spacer(1, 2*cm))
    flowables.append(Paragraph("<b>ÍNDICE</b>", styles['h1']))
    flowables.append(Spacer(1, 0.5*cm))
    
    # Línea decorativa
    from reportlab.platypus import HRFlowable
    flowables.append(HRFlowable(width="100%", thickness=2, color=PRIMARY_COLOR, spaceBefore=0, spaceAfter=20))
    
    # Estilo para el índice
    toc_style = ParagraphStyle(
        name='TOC',
        parent=styles['p'],
        fontSize=11,
        leading=18,
        leftIndent=0,
        spaceAfter=8
    )
    
    toc_subsection_style = ParagraphStyle(
        name='TOCSubsection',
        parent=styles['p'],
        fontSize=10,
        leading=16,
        leftIndent=20,
        spaceAfter=6
    )
    
    # Secciones principales
    sections = [
        ("I.", "Introducción y Marco Conceptual"),
        ("II.", "Indicadores de Nivel de Cumplimiento"),
        ("III.", "Panorama General por Dimensión"),
        ("IV.", "Porcentaje de Indicadores Atendidos por Dimensión"),
        ("V.", "Subdimensiones por Dimensión"),
    ]
    
    # Agregar secciones principales
    for num, desc in sections:
        flowables.append(Paragraph(f"<b>{num}</b> {desc}", toc_style))
    
    # Agregar dimensiones como subsecciones
    flowables.append(Spacer(1, 0.3*cm))
    flowables.append(Paragraph("<b>VI. Análisis por Dimensión</b>", toc_style))
    
    for idx, dim in enumerate(data.dimensiones if hasattr(data, 'dimensiones') else [], start=1):
        dim_dict = dim if isinstance(dim, dict) else dim.__dict__
        dim_nombre = dim_dict.get('nombre', f'Dimensión {idx}')
        flowables.append(Paragraph(f"{idx}. {dim_nombre}", toc_subsection_style))
    
    # Agregar secciones finales
    flowables.append(Spacer(1, 0.3*cm))
    flowables.append(Paragraph("<b>VII.</b> Datos Complementarios", toc_style))
    flowables.append(Paragraph("• Composición por Sexo", toc_subsection_style))
    flowables.append(Paragraph("• Brecha Salarial por Categoría", toc_subsection_style))
    flowables.append(Paragraph("• Quejas de Acoso y Hostigamiento", toc_subsection_style))
    flowables.append(Paragraph("• Atenciones a Mujeres", toc_subsection_style))
    
    flowables.append(Spacer(1, 1*cm))
    flowables.append(HRFlowable(width="100%", thickness=1, color=MEDIUM_GRAY, spaceBefore=0, spaceAfter=0))
    flowables.append(PageBreak())
    
    return flowables

# --- Gráfica de Radar ---
def create_radar_chart(data, styles):
    """Crea una gráfica de radar/araña con las 9 dimensiones"""
    chart_title_text = "<b>PANORAMA GENERAL POR DIMENSIÓN</b><br/><font size='-2'>(GRÁFICA DE RADAR)</font>"
    chart_title = Paragraph(chart_title_text, styles['chart_title'])
    
    # Preparar datos
    dimension_names = [
        "Formación", "Investigación", "Comunicación", "Participación",
        "Condiciones Lab.", "Acoso/Violencia", "Corresponsabilidad",
        "Institucionalidad", "Infraestructura"
    ]
    
    # Limitar a 9 dimensiones
    values = [item.get('porcentaje', 0) if isinstance(item, dict) else getattr(item, 'porcentaje', 0) for item in data[:9]]
    
    # Asegurar que tengamos exactamente 9 valores
    while len(values) < 9:
        values.append(0)
    values = values[:9]
    
    # Crear el dibujo
    drawing = Drawing(width=15*cm, height=15*cm)
    
    # Crear el spider chart
    spider = SpiderChart()
    spider.x = 2*cm
    spider.y = 2*cm
    spider.width = 11*cm
    spider.height = 11*cm
    
    spider.data = [values]
    spider.labels = dimension_names
    
    spider.strands[0].fillColor = colors.HexColor("#6A1B9A40")  # Morado con transparencia
    spider.strands[0].strokeColor = PRIMARY_COLOR
    spider.strands[0].strokeWidth = 2
    
    spider.strandLabels.fontName = 'Helvetica'
    spider.strandLabels.fontSize = 8
    
    drawing.add(spider)
    
    return [
        Spacer(1, 1*cm),
        chart_title,
        Spacer(1, 0.2*cm),
        Paragraph("Esta gráfica muestra el porcentaje de cumplimiento en cada una de las 9 dimensiones evaluadas.", styles['p']),
        Spacer(1, 0.5*cm),
        drawing,
        PageBreak()
    ]

# --- PDF Generation ---
def create_pdf_in_memory(data: ReporteData):
    '''
    Generates a complex PDF document in memory using Platypus and returns the buffer.
    '''
    buffer = io.BytesIO()
    
    W, H = A4
    base_styles = getSampleStyleSheet()
    
    # Configurar fuentes según disponibilidad
    font_name = 'DejaVuSans' if USE_CUSTOM_FONTS else 'Helvetica'
    font_name_bold = 'DejaVuSans-Bold' if USE_CUSTOM_FONTS else 'Helvetica-Bold'
    
    md_styles = {
        'h1': ParagraphStyle(name='MarkdownH1', parent=base_styles['h1'], fontSize=12, spaceBefore=12, spaceAfter=4, fontName=font_name_bold),
        'h2': ParagraphStyle(name='MarkdownH2', parent=base_styles['h2'], fontSize=11, spaceBefore=10, spaceAfter=3, alignment=TA_LEFT, fontName=font_name_bold),
        'p': ParagraphStyle(name='MarkdownP', parent=base_styles['BodyText'], alignment=TA_JUSTIFY, spaceAfter=6, fontSize=10, fontName=font_name),
        'li': ParagraphStyle(name='MarkdownLI', parent=base_styles['BodyText'], leftIndent=20, bulletIndent=10, spaceAfter=4, bulletText='•', fontSize=10, fontName=font_name),
    }
    md_styles['h3'] = ParagraphStyle(name='MarkdownH3', parent=base_styles['h3'], fontSize=10, spaceAfter=2, alignment=TA_LEFT, fontName=font_name_bold)
    md_styles['card_title'] = ParagraphStyle(name='CardTitle', parent=base_styles['Normal'], fontSize=11, spaceAfter=4, alignment=TA_LEFT, fontName=font_name)
    md_styles['chart_title'] = ParagraphStyle(name='ChartTitle', parent=base_styles['Normal'], fontSize=11, spaceAfter=4, alignment=TA_LEFT, fontName=font_name_bold)
    md_styles['h2_centered'] = ParagraphStyle(name='MarkdownH2Centered', parent=md_styles['h2'], alignment=TA_LEFT, fontName=font_name_bold)
    md_styles['dimension_title_centered'] = ParagraphStyle(name='DimensionTitleCentered', parent=base_styles['Normal'], fontSize=11, spaceAfter=4, alignment=TA_CENTER, fontName=font_name_bold)
    # Estilos específicos para tablas más pequeñas
    md_styles['table_text'] = ParagraphStyle(name='TableText', parent=base_styles['Normal'], fontSize=9, fontName=font_name)
    md_styles['table_header'] = ParagraphStyle(name='TableHeader', parent=base_styles['Normal'], fontSize=9, fontName=font_name_bold)
    md_styles['table_header_small'] = ParagraphStyle(name='TableHeaderSmall', parent=base_styles['Normal'], fontSize=8, fontName=font_name_bold)
    md_styles['table_text_centered'] = ParagraphStyle(name='TableTextCentered', parent=base_styles['Normal'], fontSize=9, fontName=font_name, alignment=TA_CENTER)
    TITLE_STYLE = base_styles['h1']; TITLE_STYLE.alignment=TA_LEFT; TITLE_STYLE.fontName=font_name_bold

    doc = BaseDocTemplate(
        buffer, 
        pagesize=A4, 
        leftMargin=2*cm, 
        rightMargin=2*cm, 
        topMargin=2.2*cm, 
        bottomMargin=2*cm,
        title=f"Reporte DIGEI - {data.organizacion.get('nombre', 'Organización')}",
        author="DIGEI - Distintivo Genera Igualdad",
        subject="Autodiagnóstico de Igualdad de Género",
        creator="Sistema DIGEI",
        keywords="género, igualdad, diagnóstico, DIGEI"
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='F1')

    def header(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(PRIMARY_COLOR)
        canvas.drawString(2*cm, H-1.5*cm, "DIGEI · Distintivo que Genera igualdad y Convivencia Pacífica")
        canvas.drawRightString(W-2*cm, H-1.5*cm, "AutodiagnósticoDIGEI")
        canvas.setStrokeColor(MEDIUM_GRAY)
        canvas.setLineWidth(0.5)
        canvas.line(2*cm, H-1.7*cm, W-2*cm, H-1.7*cm)
        canvas.restoreState()

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)
        
        # Información izquierda: Folio y fecha
        folio = data.organizacion.get('folio', 'N/A')
        fecha = data.organizacion.get('fecha_aplicacion', 'N/A')
        canvas.drawString(2*cm, 1.1*cm, f"Folio: {folio}")
        canvas.drawString(2*cm, 0.7*cm, f"Fecha: {fecha}")
        
        # Centro: Organización
        org_nombre = data.organizacion.get('nombre', '')[:40]  # Limitar longitud
        canvas.drawCentredString(W/2, 1.1*cm, org_nombre)
        
        # Derecha: Número de página
        canvas.setFont("Helvetica-Bold", 9)
        canvas.drawRightString(W-2*cm, 1.1*cm, f"Página {doc.page}")
        
        # Línea separadora
        canvas.setStrokeColor(PRIMARY_COLOR)
        canvas.setLineWidth(1)
        canvas.line(2*cm, 1.5*cm, W-2*cm, 1.5*cm)
        canvas.restoreState()

    doc.addPageTemplates([
        PageTemplate(id='PORTADA1', frames=[frame]),
        PageTemplate(id='TITULO', frames=[frame]),
        PageTemplate(id='PORTADA2', frames=[frame]),
        PageTemplate(id='BODY', frames=[frame], onPage=header, onPageEnd=footer)
    ])

    story = []

    # Page 1: Logo
    story.append(Spacer(1, 6*cm))
    try:
        target_width = 8*cm
        img_reader = ImageReader(LOGO_PATH)
        img_width, img_height = img_reader.getSize()
        aspect_ratio = img_height / float(img_width)
        new_height = target_width * aspect_ratio
        story.append(Image(LOGO_PATH, width=target_width, height=new_height, hAlign='CENTER'))
    except Exception as e:
        story.append(Paragraph(f"Error al cargar logo: {e}", md_styles['p']))
    story.append(PageBreak())
    doc.handle_nextPageTemplate('TITULO')

    # Page 2: Report Title
    story.append(Spacer(1, 6*cm))
    title_text = "Reporte de Resultados del Autodiagnóstico para el proceso de Transversalización e Institucionalización de la Perspectiva de Género y Convivencia Pacífica"
    story.append(Paragraph(title_text, TITLE_STYLE))
    story.append(PageBreak())
    doc.handle_nextPageTemplate('PORTADA2')

    # Page 3: Institution Data
    story.append(Spacer(1, 2*cm))
    story.append(Paragraph(data.organizacion.get('nombre', 'Sin nombre'), TITLE_STYLE))
    story.append(Spacer(1, 1*cm))
    inst_data = [
        [Paragraph('<b>Responsable:</b>', base_styles['BodyText']), Paragraph(data.organizacion.get('responsable', 'Sin responsable'), base_styles['BodyText'])],
        [Paragraph('<b>Cargo:</b>', base_styles['BodyText']), Paragraph(data.organizacion.get('cargo_responsable', ''), base_styles['BodyText'])],
        [Paragraph('<b>Fecha de aplicación:</b>', base_styles['BodyText']), Paragraph(data.organizacion.get('fecha_aplicacion', ''), base_styles['BodyText'])],
        [Paragraph('<b>Folio:</b>', base_styles['BodyText']), Paragraph(data.organizacion.get('folio', ''), base_styles['BodyText'])],
    ]
    inst_table = Table(inst_data, colWidths=[5*cm, 10*cm], hAlign='LEFT')
    inst_table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0)]))
    story.append(inst_table)
    story.append(PageBreak())
    doc.handle_nextPageTemplate('BODY')

    # Page 4: Índice de Contenidos
    story.extend(create_table_of_contents(data, md_styles))

    # Page 5+: Report Content
    story.extend(parse_markdown_to_flowables(INTRO_PATH, md_styles))
    story.append(Spacer(1, 1*cm))
    story.extend(parse_markdown_to_flowables(MARCO_PATH, md_styles))
    story.append(Spacer(1, 1*cm))

    # --- Add Semaforo cards with data from request ---
    # Calcular porcentajes de indicadores atendidos
    total_indicadores = 0
    indicadores_atendidos = 0
    
    if data.dimensiones:
        for dim in data.dimensiones:
            dim_dict = dim if isinstance(dim, dict) else dim.__dict__
            for sub in dim_dict.get('subdimensiones', []):
                sub_dict = sub if isinstance(sub, dict) else sub.__dict__
                total_indicadores += sub_dict.get('total_indicadores', 0)
                indicadores_atendidos += sub_dict.get('indicadores_atendidos', 0)
    
    # Calcular porcentajes
    pct_vs_100 = (indicadores_atendidos / total_indicadores * 100) if total_indicadores > 0 else 0
    pct_vs_80 = (indicadores_atendidos / (total_indicadores * 0.8) * 100) if total_indicadores > 0 else 0
    
    print(f"  📊 Semáforos: {indicadores_atendidos}/{total_indicadores} = {pct_vs_100:.1f}% vs 100%, {pct_vs_80:.1f}% vs 80%")
    
    story.extend(create_semaforo_flowables(doc, md_styles, pct_vs_100, pct_vs_80))

    # --- Add Chart from request data ---
    if data.grafica_dimensiones:
        # Convertir los datos al formato esperado por la función
        chart_data = []
        for dim in data.grafica_dimensiones:
            if isinstance(dim, dict):
                porcentaje = dim.get('porcentaje', 0)
                print(f"  📊 Dimensión (dict): {dim.get('dimensionNombre', 'N/A')} = {porcentaje}%")
                chart_data.append({'pct_vs_100': porcentaje})
            else:
                # Si es un objeto Pydantic, acceder como atributo
                porcentaje = getattr(dim, 'porcentaje', 0)
                print(f"  📊 Dimensión (obj): {getattr(dim, 'dimensionNombre', 'N/A')} = {porcentaje}%")
                chart_data.append({'pct_vs_100': porcentaje})
        
        print(f"  📊 Chart data final: {chart_data}")
        
        if chart_data:  # Solo agregar si hay datos
            story.extend(create_dimensiones_chart(chart_data, md_styles))
            
            # Agregar gráfica de radar después de la gráfica de barras
            print("  📊 Generando gráfica de radar")
            story.extend(create_radar_chart(data.grafica_dimensiones, md_styles))

    # --- Add Table from request data ---
    if data.dimensiones:
        # Convertir datos al formato esperado por create_subdimensiones_table
        table_data_converted = {
            "descripcion": "La siguiente tabla muestra el nivel de cumplimiento por dimensión y subdimensión",
            "dimensiones": []
        }
        
        for dim in data.dimensiones:
            dim_dict = dim if isinstance(dim, dict) else dim.__dict__
            
            dim_converted = {
                "id": dim_dict.get('orden', dim_dict.get('id')),
                "nombre": dim_dict.get('nombre', ''),
                "subdimensiones": []
            }
            
            for sub in dim_dict.get('subdimensiones', []):
                sub_dict = sub if isinstance(sub, dict) else sub.__dict__
                
                # Calcular porcentaje vs 80
                meta_80 = sub_dict.get('meta_80', 1)
                indicadores_atendidos = sub_dict.get('indicadores_atendidos', 0)
                porcentaje_vs_80 = (indicadores_atendidos / meta_80 * 100) if meta_80 > 0 else 0
                
                # Mapear semáforo
                semaforo_label = sub_dict.get('semaforo', 'N/A').lower()
                if semaforo_label == 'alto':
                    semaforo = 'alto'
                elif semaforo_label == 'medio':
                    semaforo = 'medio'
                elif semaforo_label == 'bajo':
                    semaforo = 'bajo'
                else:
                    semaforo = 'bajo'  # Default para N/A
                
                sub_converted = {
                    "id": f"{dim_dict.get('orden', dim_dict.get('id'))}.{len(dim_converted['subdimensiones']) + 1}",
                    "nombre": sub_dict.get('nombre', ''),
                    "indicadores_total": sub_dict.get('total_indicadores', 0),
                    "indicadores_atendidos": indicadores_atendidos,
                    "porcentaje_vs_100": sub_dict.get('porcentaje', 0),
                    "porcentaje_vs_80": porcentaje_vs_80,
                    "semaforo": semaforo
                }
                dim_converted['subdimensiones'].append(sub_converted)
            
            table_data_converted['dimensiones'].append(dim_converted)
        
        print(f"  📋 Generando tabla con {len(table_data_converted['dimensiones'])} dimensiones")
        story.extend(create_subdimensiones_table(table_data_converted, md_styles))

    # --- Add Dimension Details from request data ---
    if data.dimensiones:
        print(f"  📄 Generando detalles de {len(data.dimensiones)} dimensiones")
        for dim in data.dimensiones:
            dim_dict = dim if isinstance(dim, dict) else dim.__dict__
            
            # Convertir al formato esperado por create_dimension_detail_flowables
            dim_orden = dim_dict.get('orden', dim_dict.get('id'))
            dim_nombre = dim_dict.get('nombre', '')
            
            # Calcular porcentaje atendido de la dimensión
            total_indicadores_dim = sum(sub.get('total_indicadores', 0) if isinstance(sub, dict) else sub.__dict__.get('total_indicadores', 0) for sub in dim_dict.get('subdimensiones', []))
            indicadores_atendidos_dim = sum(sub.get('indicadores_atendidos', 0) if isinstance(sub, dict) else sub.__dict__.get('indicadores_atendidos', 0) for sub in dim_dict.get('subdimensiones', []))
            porcentaje_atendido = (indicadores_atendidos_dim / total_indicadores_dim * 100) if total_indicadores_dim > 0 else 0
            
            dim_detail = {
                "dimension_nombre": f"{dim_orden}. {dim_nombre}",
                "porcentaje_atendido": porcentaje_atendido,
                "puntos_no_atendidos": []
            }
            
            # Agrupar preguntas por subdimensión
            subdimensiones_dict = {}
            for sub in dim_dict.get('subdimensiones', []):
                sub_dict = sub if isinstance(sub, dict) else sub.__dict__
                sub_nombre = sub_dict.get('nombre', '')
                
                # Extraer indicadores no atendidos
                for ind in sub_dict.get('indicadores_no_atendidos', []):
                    ind_dict = ind if isinstance(ind, dict) else ind.__dict__
                    
                    # Agrupar por subdimensión
                    if sub_nombre not in subdimensiones_dict:
                        subdimensiones_dict[sub_nombre] = []
                    subdimensiones_dict[sub_nombre].append(ind_dict.get('texto', ''))
            
            # Convertir el diccionario a la estructura esperada
            for sub_nombre, preguntas in subdimensiones_dict.items():
                dim_detail['puntos_no_atendidos'].append({
                    "subdimension": sub_nombre,
                    "preguntas": preguntas
                })
            
            story.extend(create_dimension_detail_flowables(dim_detail, md_styles, doc.width))

    # --- Add Special Section with real data ---
    # Preparar datos de composición por sexo, salarios, quejas y atenciones
    print("  📊 Generando sección especial (composición, salarios, quejas)")
    story.extend(create_special_section_with_data(data, md_styles, doc.width))

    # --- Secciones de encuestas y autodiagnóstico removidas ---

    doc.build(story)
    
    buffer.seek(0)
    return buffer

# --- FastAPI Endpoints ---
@app.post("/generar-pdf", summary="Generate PDF from JSON data")
def generate_pdf_from_json(data: ReporteData):
    try:
        # Log para depuración
        print(f"📊 Datos recibidos:")
        print(f"  - Organización: {data.organizacion.get('nombre', 'N/A')}")
        print(f"  - Total dimensiones: {len(data.dimensiones)}")
        print(f"  - Gráfica dimensiones: {len(data.grafica_dimensiones)}")
        if data.grafica_dimensiones:
            print(f"  - Primer dato gráfica: {data.grafica_dimensiones[0]}")
        
        pdf_buffer = create_pdf_in_memory(data)
        filename = f"reporte-{data.organizacion.get('folio', 'DIGEI')}.pdf"
        headers = {'Content-Disposition': f'inline; filename="{filename}"'}
        return Response(content=pdf_buffer.getvalue(), media_type="application/pdf", headers=headers)
    except Exception as e:
        print(f"❌ Error generando PDF: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error generando PDF: {str(e)}")

@app.get("/pdf", summary="Generate a test PDF (deprecated)")
def generate_test_pdf():
    # Endpoint de prueba con datos hardcoded
    test_data = ReporteData(
        organizacion={
            "nombre": "Universidad de Prueba",
            "responsable": "Nombre Apellido",
            "cargo_responsable": "Director",
            "fecha_aplicacion": "2025-10-25",
            "folio": "DIGEI-TEST001"
        },
        metadata={
            "total_indicadores": 100,
            "indicadores_atendidos": 75,
            "porcentaje_cumplimiento_100": 75.0,
            "porcentaje_cumplimiento_80": 93.75,
            "meta_80": 80
        },
        dimensiones=[],
        grafica_dimensiones=[]
    )
    pdf_buffer = create_pdf_in_memory(test_data)
    headers = {'Content-Disposition': 'inline; filename="reporte-test.pdf"'}
    return Response(content=pdf_buffer.getvalue(), media_type="application/pdf", headers=headers)

@app.get("/")
def read_root():
    return {
        "message": "Servicio de reportes PDF funcionando.",
        "endpoints": {
            "POST /generar-pdf": "Genera PDF desde JSON (principal)",
            "GET /pdf": "Genera PDF de prueba"
        }
    }


