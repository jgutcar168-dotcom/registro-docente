import streamlit as st
import pandas as pd
from fpdf import FPDF
from supabase import create_client
from datetime import datetime

# --- 1. CONFIGURACIÓN Y CONEXIÓN ---
st.set_page_config(page_title="Registro Docente", layout="wide")

@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_connection()

# --- 2. CLASE PDF PROFESIONAL ---
class EvaluacionPDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 14)
        self.cell(0, 10, "INFORME DE EVALUACIÓN DOCENTE", ln=True, align="C")
        self.set_font("Arial", "I", 10)
        self.cell(0, 5, "Maestra Especialista: Ángela Ortíz Ordónez", ln=True, align="C")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Página {self.page_no()}/{{nb}}", align="C")

    def tabla_maestra(self, items):
        self.set_font("Arial", "B", 9)
        self.set_fill_color(230, 230, 230)
        
        # Definición de anchos (Total ~190mm)
        w_letra, w_desc, w_niv = 10, 35, 36.25 
        
        # Cabecera
        self.cell(w_letra, 10, "L.", 1, 0, "C", True)
        self.cell(w_desc, 10, "Descripción", 1, 0, "C", True)
        for i in range(1, 5):
            self.cell(w_niv, 10, f"Nivel {i}", 1, 0, "C", True)
        self.ln()

        self.set_font("Arial", "", 7)
        for it in items:
            # --- CÁLCULO DE ALTURA DE FILA ---
            # Estimamos cuántas líneas ocupará el texto en cada celda
            # (Ancho celda / aprox 2.2mm por carácter en fuente 7)
            lineas_desc = self.get_string_width(str(it['descripcion'])) / w_desc
            lineas_n1 = self.get_string_width(str(it['nivel_1'])) / w_niv
            lineas_n2 = self.get_string_width(str(it['nivel_2'])) / w_niv
            lineas_n3 = self.get_string_width(str(it['nivel_3'])) / w_niv
            lineas_n4 = self.get_string_width(str(it['nivel_4'])) / w_niv
            
            max_lineas = max(lineas_desc, lineas_n1, lineas_n2, lineas_n3, lineas_n4, 1)
            h_fila = (int(max_lineas) + 1) * 4 # Altura uniforme para toda la fila

            # Salto de página preventivo
            if self.get_y() + h_fila > 270:
                self.add_page()

            x, y = self.get_x(), self.get_y()

            # Dibujamos las celdas una a una manteniendo la misma Y
            self.rect(x, y, w_letra, h_fila)
            self.cell(w_letra, h_fila, it['letra'], 0, 0, "C")
            
            # Para las celdas con texto largo usamos multi_cell en un área controlada
            pos_x = x + w_letra
            for ancho, texto in zip([w_desc, w_niv, w_niv, w_niv, w_niv], 
                                   [it['descripcion'], it['nivel_1'], it['nivel_2'], it['nivel_3'], it['nivel_4']]):
                self.set_xy(pos_x, y)
                self.multi_cell(ancho, 4, str(texto), border=1, align='L')
                pos_x += ancho
            
            self.set_xy(x, y + h_fila) # Bajamos a la siguiente fila real

    def ficha_alumno_triple(self, nombre, puntos, x_offset, y_start):
        self.set_xy(x_offset, y_start)
        w_box = 62
        
        # Cabecera de alumno más pequeña
        self.set_font("Arial", "B", 8)
        self.set_fill_color(240, 240, 240)
        nombre_f = nombre.split(" (")[0][:22] # Cortamos nombre si es muy largo
        self.cell(w_box, 5, f"Alumno: {nombre_f}", 1, 1, "L", True)
        
        y_int = self.get_y()
        self.set_font("Arial", "", 8)
        
        # Ítems en formato compacto
        for letra, nivel in puntos.items():
            self.set_xy(x_offset, y_int)
            self.cell(12, 4.5, f"{letra}:", 0, 0)
            
            for n in range(1, 5):
                if n == int(nivel):
                    self.set_fill_color(180, 180, 180)
                    self.ellipse(self.get_x() + 1, self.get_y() + 0.5, 3.5, 3.5, 'F')
                    self.set_font("Arial", "B", 8)
                else:
                    self.set_font("Arial", "", 8)
                self.cell(6, 4.5, str(n), 0, 0, "C")
            y_int += 4.5
        return y_int

# --- 3. TÍTULO APP ---
st.markdown("<h1 style='text-align: center; color: #2E5A88;'>🎓 Registro Evaluación Docente - Aula P.T.</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align: center; font-family: \"Brush Script MT\", cursive; font-size: 35px; color: #5DADE2;'>Maestra Especialista: Ángela Ortíz Ordónez</p>", unsafe_allow_html=True)

tab_alu, tab_conf, tab_eval, tab_hist = st.tabs(["👥 Alumnos", "⚙️ Ítems", "📝 Evaluación", "📅 Histórico"])

# --- [LAS TABS DE ALUMNOS, ITEMS Y EVALUACIÓN SE MANTIENEN IGUAL QUE TU CÓDIGO ANTERIOR] ---
# (Copia aquí tus bloques de código de Tab 1, 2 y 3 para que funcione la base de datos)

# --- TAB 4: HISTÓRICO Y PDF ---
with tab_hist:
    evals = supabase.table("evaluaciones_alumnos").select("*").order("fecha", desc=True).execute().data
    items_db = supabase.table("configuracion_items").select("*").order("letra").execute().data
    
    if evals:
        df = pd.DataFrame(evals)
        df['fecha_dia'] = df['fecha'].apply(lambda x: x[:10])
        dias = df['fecha_dia'].unique()
        dia_pdf = st.selectbox("Día para PDF", ["Completo"] + list(dias))
        
        if st.button("Generar PDF"):
            pdf = EvaluacionPDF()
            pdf.alias_nb_pages()
            pdf.add_page()
            
            # 1. Tabla Maestra
            pdf.tabla_maestra(items_db)
            pdf.ln(5)
            
            # 2. Título Sección Alumnos
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 10, "EVALUACIÓN ALUMNADO", ln=True)
            
            ev_print = evals if dia_pdf == "Completo" else [e for e in evals if e['fecha'][:10] == dia_pdf]
            
            columna = 0 
            x_pos = [10, 74, 138] # Posiciones para 3 columnas
            y_fila_inicio = pdf.get_y()
            y_max_en_fila = y_fila_inicio

            for e in ev_print:
                # Control de salto de página para los alumnos
                if y_fila_inicio > 250:
                    pdf.add_page()
                    y_fila_inicio = 20
                    y_max_en_fila = 20

                y_fin_alu = pdf.ficha_alumno_triple(e['nombre_alumno'], e['puntos'], x_pos[columna], y_fila_inicio)
                y_max_en_fila = max(y_max_en_fila, y_fin_alu)

                if columna < 2:
                    columna += 1
                else:
                    columna = 0
                    y_fila_inicio = y_max_en_fila + 5 # Espacio entre filas
                    y_max_en_fila = y_fila_inicio

            st.download_button("Descargar Informe PDF", bytes(pdf.output()), f"Informe_{dia_pdf}.pdf")

        # Vista en web (Expander por días)
        for d in dias:
            with st.expander(f"📅 {d}"):
                for _, r in df[df['fecha_dia'] == d].iterrows():
                    c1, c2 = st.columns([5,1])
                    c1.write(r['nombre_alumno'])
                    if c2.button("🗑️", key=f"del_{r['id']}"):
                        supabase.table("evaluaciones_alumnos").delete().eq("id", r['id']).execute()
                        st.rerun()