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

# --- 2. CLASE PDF OPTIMIZADA ---
class EvaluacionPDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 16)
        self.cell(0, 10, "Registro de Evaluación Docente - Aula P.T.", ln=True, align="C")
        self.set_font("Arial", "I", 10)
        self.cell(0, 10, "Ángela Ortíz Ordónez", ln=True, align="C")
        self.ln(5)

    def tabla_maestra(self, items):
        self.set_font("Arial", "B", 11)
        self.set_fill_color(230, 230, 230)
        self.cell(0, 10, "1. REFERENCIA DE ITEMS Y NIVELES", ln=True)
        
        # Cabecera
        self.set_font("Arial", "B", 8)
        self.cell(10, 8, "It.", 1, 0, "C", True)
        self.cell(40, 8, "Descripcion", 1, 0, "C", True)
        self.cell(35, 8, "Nivel 1", 1, 0, "C", True)
        self.cell(35, 8, "Nivel 2", 1, 0, "C", True)
        self.cell(35, 8, "Nivel 3", 1, 0, "C", True)
        self.cell(35, 8, "Nivel 4", 1, 1, "C", True)
        
        self.set_font("Arial", "", 7)
        for it in items:
            # Calculamos la altura necesaria para la fila basándonos en el texto más largo
            # Comparamos la descripción y los 4 niveles
            alturas = [self.get_string_width(str(it['descripcion'])), 
                       self.get_string_width(str(it['nivel_1'])),
                       self.get_string_width(str(it['nivel_2'])),
                       self.get_string_width(str(it['nivel_3'])),
                       self.get_string_width(str(it['nivel_4']))]
            
            # Estimación de líneas: ancho de celda es ~35-40. 
            lineas = max([len(str(it['descripcion']))/25] + [len(str(it[f'nivel_{i}']))/25 for i in range(1,5)])
            h = max(8, lineas * 3.5) # Altura dinámica de la fila

            x_start = self.get_x()
            y_start = self.get_y()

            # Dibujamos cada celda con MultiCell para que el texto envuelva
            self.multi_cell(10, h, it['letra'], border=1, align='C')
            self.set_xy(x_start + 10, y_start)
            self.multi_cell(40, h/max(1, (len(str(it['descripcion']))/25)), it['descripcion'], border=1)
            
            for i in range(1, 5):
                self.set_xy(x_start + 50 + (35*(i-1)), y_start)
                texto = str(it[f'nivel_{i}'])
                self.multi_cell(35, 3.5, texto, border=1) # Usamos 3.5 de alto de línea fijo para texto
            
            self.set_xy(x_start, y_start + h) # Bajamos a la siguiente fila real
        self.add_page()

    def ficha_alumno_columna(self, nombre_curso, puntos, x_offset, y_start):
        """Dibuja la ficha del alumno en una posición X específica para crear columnas"""
        self.set_xy(x_offset, y_start)
        self.set_font("Arial", "B", 10)
        self.set_fill_color(245, 245, 245)
        # Ancho de columna aproximado 90 (para que quepan 2 en un A4 con márgenes)
        self.cell(90, 8, f"Alumno: {nombre_curso[:35]}", 1, 1, "L", True)
        
        y_actual = self.get_y()
        for letra, nivel_sel in puntos.items():
            self.set_xy(x_offset, y_actual)
            self.set_font("Arial", "", 9)
            self.cell(20, 7, f"It {letra}:", 0, 0)
            
            # Dibujar números 1 a 4
            for n in range(1, 5):
                if n == int(nivel_sel):
                    self.set_fill_color(200, 200, 200)
                    self.ellipse(self.get_x() + 1.5, self.get_y() + 1, 5, 5, 'F')
                    self.set_font("Arial", "B", 9)
                    self.cell(8, 7, str(n), 0, 0, "C")
                else:
                    self.set_font("Arial", "", 9)
                    self.cell(8, 7, str(n), 0, 0, "C")
            y_actual += 6
            self.ln(6)
        return y_actual # Devolvemos donde terminó para controlar el salto de página

# --- 3. TÍTULO ---
st.markdown("<h1 style='text-align: center; color: #2E5A88;'>🎓 Registro Evaluación Docente - Aula P.T.</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; font-family: \"Brush Script MT\", cursive; font-size: 35px; color: #5DADE2;'>Maestra Especialista: Ángela Ortíz Ordónez</p>", unsafe_allow_html=True)

tab_alu, tab_conf, tab_eval, tab_hist = st.tabs(["👥 Alumnos", "⚙️ Ítems", "📝 Evaluación", "📅 Histórico"])

# --- TAB 1: ALUMNOS ---
with tab_alu:
    res_alu = supabase.table("alumnos").select("*").order("nombre").execute()
    alumnos_db = res_alu.data
    sel_alu = st.selectbox("Selecciona para editar", ["+ Nuevo Alumno"] + [f"{a['nombre']} ({a['curso']})" for a in alumnos_db])
    v_id, v_nom, v_cur = 0, "", ""
    if sel_alu != "+ Nuevo Alumno":
        datos_a = next(a for a in alumnos_db if f"{a['nombre']} ({a['curso']})" == sel_alu)
        v_id, v_nom, v_cur = datos_a['id'], datos_a['nombre'], datos_a['curso']
    with st.form("f_alu"):
        n_in = st.text_input("Nombre", value=v_nom)
        c_in = st.text_input("Curso", value=v_cur)
        if st.form_submit_button("Guardar Alumno"):
            if v_id == 0: supabase.table("alumnos").insert({"nombre": n_in, "curso": c_in}).execute()
            else: supabase.table("alumnos").update({"nombre": n_in, "curso": c_in}).eq("id", v_id).execute()
            st.rerun()

# --- TAB 2: ÍTEMS ---
with tab_conf:
    res_it = supabase.table("configuracion_items").select("*").order("letra").execute()
    items_db = res_it.data
    sel_it = st.selectbox("Selecciona Ítem", ["+ Nuevo Ítem"] + [it['letra'] for it in items_db])
    vi_let, vi_des, vi_n1, vi_n2, vi_n3, vi_n4 = "", "", "", "", "", ""
    if sel_it != "+ Nuevo Ítem":
        d = next(i for i in items_db if i['letra'] == sel_it)
        vi_let, vi_des, vi_n1, vi_n2, vi_n3, vi_n4 = d['letra'], d['descripcion'], d['nivel_1'], d['nivel_2'], d['nivel_3'], d['nivel_4']
    with st.form("f_it"):
        l_in = st.text_input("Letra", value=vi_let).upper()
        d_in = st.text_input("Descripción", value=vi_des)
        col1, col2 = st.columns(2)
        n1 = col1.text_area("Nivel 1", value=vi_n1)
        n2 = col2.text_area("Nivel 2", value=vi_n2)
        n3 = col1.text_area("Nivel 3", value=vi_n3)
        n4 = col2.text_area("Nivel 4", value=vi_n4)
        if st.form_submit_button("Guardar Ítem"):
            supabase.table("configuracion_items").upsert({"letra": l_in, "descripcion": d_in, "nivel_1": n1, "nivel_2": n2, "nivel_3": n3, "nivel_4": n4}).execute()
            st.rerun()

# --- TAB 3: EVALUACIÓN ---
with tab_eval:
    if not alumnos_db or not items_db:
        st.warning("Faltan alumnos o ítems.")
    else:
        with st.form("f_ev"):
            al_sel = st.selectbox("Alumno", [f"{a['nombre']} ({a['curso']})" for a in alumnos_db])
            f_sel = st.date_input("Fecha", datetime.now())
            res_eval = {}
            for it in items_db:
                st.write(f"### {it['letra']} - {it['descripcion']}")
                res_eval[it['letra']] = st.radio(f"Nivel {it['letra']}", [1,2,3,4], format_func=lambda x: f"{x}: {it[f'nivel_{x}']}", key=f"r_{it['letra']}")
            if st.form_submit_button("Registrar"):
                supabase.table("evaluaciones_alumnos").insert({"nombre_alumno": al_sel, "puntos": res_eval, "fecha": f_sel.isoformat()}).execute()
                st.success("Guardado")

# --- TAB 4: HISTÓRICO Y PDF ---
with tab_hist:
    evals = supabase.table("evaluaciones_alumnos").select("*").order("fecha", desc=True).execute().data
    if evals:
        df = pd.DataFrame(evals)
        df['fecha_dia'] = df['fecha'].apply(lambda x: x[:10])
        dias = df['fecha_dia'].unique()
        dia_pdf = st.selectbox("Día para PDF", ["Completo"] + list(dias))
        
        # --- DENTRO DE TAB 4: HISTÓRICO ---
        if st.button("Generar PDF"):
            pdf = EvaluacionPDF()
            pdf.add_page()
            pdf.tabla_maestra(items_db)
            
            ev_print = evals if dia_pdf == "Completo" else [e for e in evals if e['fecha'][:10] == dia_pdf]
            
            columna = 0 # 0 para izquierda, 1 para derecha
            y_inicial = pdf.get_y()
            y_max_en_fila = y_inicial

            for e in ev_print:
                x_pos = 10 if columna == 0 else 105 # Posición X según columna
                
                # Dibujamos la ficha y obtenemos dónde termina
                y_final = pdf.ficha_alumno_columna(e['nombre_alumno'], e['puntos'], x_pos, y_inicial)
                y_max_en_fila = max(y_max_en_fila, y_final)

                if columna == 0:
                    columna = 1 # El siguiente va a la derecha
                else:
                    columna = 0 # Volvemos a la izquierda
                    y_inicial = y_max_en_fila + 10 # Bajamos la fila
                    y_max_en_fila = y_inicial
                
                # Control de salto de página
                if y_inicial > 250:
                    pdf.add_page()
                    y_inicial = 20
                    y_max_en_fila = 20

            st.download_button("Descargar Informe PDF", bytes(pdf.output()), "informe_docente.pdf")
