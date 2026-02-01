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
        # Fecha arriba a la derecha
        self.set_font("Arial", "", 9)
        fecha_hoy = datetime.now().strftime("%d/%m/%Y")
        self.cell(0, 5, f"Fecha del informe: {fecha_hoy}", ln=True, align="R")
        
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
        
        # Anchos ajustados para cubrir ~190mm
        w_letra, w_desc, w_niv = 10, 35, 36.2
        
        self.cell(w_letra, 10, "L.", 1, 0, "C", True)
        self.cell(w_desc, 10, "Descripción", 1, 0, "C", True)
        for i in range(1, 5):
            self.cell(w_niv, 10, f"Nivel {i}", 1, 0, "C", True)
        self.ln()

        self.set_font("Arial", "", 7)
        for it in items:
            # Cálculo de altura de fila para evitar solapamientos
            # 25 es el aprox de caracteres que caben por línea en estas celdas
            lineas = [len(str(it['descripcion']))/25, len(str(it['nivel_1']))/25, 
                      len(str(it['nivel_2']))/25, len(str(it['nivel_3']))/25, len(str(it['nivel_4']))/25]
            h_fila = max(int(max(lineas)) + 1, 1) * 4 

            if self.get_y() + h_fila > 270:
                self.add_page()

            x, y = self.get_x(), self.get_y()
            
            # Dibujamos cada celda con el mismo alto calculado
            self.multi_cell(w_letra, h_fila, it['letra'], border=1, align='C')
            self.set_xy(x + w_letra, y)
            self.multi_cell(w_desc, 4, it['descripcion'], border=1)
            for i in range(1, 5):
                self.set_xy(x + w_letra + w_desc + (w_niv*(i-1)), y)
                self.multi_cell(w_niv, 4, it[f'nivel_{i}'], border=1)
            self.set_xy(x, y + h_fila)
        self.add_page()

    def ficha_alumno_triple(self, nombre, puntos, x_offset, y_start):
        self.set_xy(x_offset, y_start)
        # Ancho reducido para que coincida exactamente con la fila de números (aprox 45-50mm)
        w_box = 50 
        
        self.set_font("Arial", "B", 8)
        self.set_fill_color(240, 240, 240)
        nombre_f = nombre.split(" (")[0][:20]
        # La cabecera ahora solo llega hasta el número 4
        self.cell(w_box, 5, nombre_f, 1, 1, "L", True)
        
        y_int = self.get_y()
        for letra, nivel in puntos.items():
            self.set_xy(x_offset, y_int)
            self.set_font("Arial", "", 8)
            self.cell(8, 4.5, f"{letra}:", 0, 0) # Solo letra
            
            for n in range(1, 5):
                if n == int(nivel):
                    self.set_fill_color(180, 180, 180)
                    self.ellipse(self.get_x() + 1.2, self.get_y() + 0.5, 3.5, 3.5, 'F')
                    self.set_font("Arial", "B", 8)
                else:
                    self.set_font("Arial", "", 8)
                self.cell(6, 4.5, str(n), 0, 0, "C")
            y_int += 4.5
        return y_int

# --- 3. LOGICA DE LA APP (Mantenemos tus Tabs) ---
# ... (Aquí irían los bloques de Alumnos, Items y Evaluación que ya funcionan) ...

# --- TAB 4: HISTÓRICO Y GENERACIÓN PDF ---
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
            # Posiciones X para 3 columnas (aprovechando el ancho de página de 210mm)
            x_pos = [15, 75, 135] 
            y_fila_inicio = pdf.get_y()
            y_max_en_fila = y_fila_inicio

            for e in ev_print:
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
                    y_fila_inicio = y_max_en_fila + 8 # Espacio entre filas
                    y_max_en_fila = y_fila_inicio

            st.download_button("Descargar Informe PDF", bytes(pdf.output()), f"Informe_{dia_pdf}.pdf")

        # Vista histórico en web
        for d in dias:
            with st.expander(f"📅 {d}"):
                for _, r in df[df['fecha_dia'] == d].iterrows():
                    c1, c2 = st.columns([5,1])
                    c1.write(r['nombre_alumno'])
                    if c2.button("🗑️", key=f"del_{r['id']}"):
                        supabase.table("evaluaciones_alumnos").delete().eq("id", r['id']).execute()
                        st.rerun()