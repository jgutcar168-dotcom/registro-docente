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
        self.set_font("Arial", "B", 14)
        self.cell(0, 10, "INFORME DE EVALUACIÓN DOCENTE", ln=True, align="C")
        self.set_font("Arial", "I", 9)
        self.cell(0, 5, "Maestra Especialista", ln=True, align="C")
        self.ln(5)

    def footer(self):
        # Numeración de páginas
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Página {self.page_no()}/{{nb}}", align="C")

    def tabla_maestra(self, items):
        self.set_font("Arial", "B", 10)
        self.set_fill_color(230, 230, 230)
        
        # Anchos de columna fijos
        w_letra = 10
        w_desc = 35
        w_niv = 36 # (36*4 + 35 + 10 = 189mm aprox)

        # Cabecera
        self.cell(w_letra, 8, "L.", 1, 0, "C", True)
        self.cell(w_desc, 8, "Descripción", 1, 0, "C", True)
        for i in range(1, 5):
            self.cell(w_niv, 8, f"Nivel {i}", 1, 0, "C", True)
        self.ln()

        self.set_font("Arial", "", 7)
        for it in items:
            # Calculamos cuántas líneas ocupa cada celda para saber la altura de la fila
            # Dividimos la longitud del texto por un factor aproximado de caracteres por línea
            textos = [it['descripcion'], it['nivel_1'], it['nivel_2'], it['nivel_3'], it['nivel_4']]
            # Estimación: w_desc(35) caben ~25 caracteres, w_niv(36) caben ~25
            lineas = [len(str(t))/25 for t in textos]
            num_lineas = max(max(lineas), 1)
            h_fila = (int(num_lineas) + 1) * 3.5 # Altura dinámica corregida

            # Guardar posición actual
            x, y = self.get_x(), self.get_y()

            # Si la fila va a salirse de la página, saltamos antes de pintar
            if y + h_fila > 270:
                self.add_page()
                y = self.get_y()

            # Pintar celdas de la fila
            self.multi_cell(w_letra, h_fila, it['letra'], border=1, align='C')
            self.set_xy(x + w_letra, y)
            self.multi_cell(w_desc, 3.5, it['descripcion'], border=1)
            for i in range(1, 5):
                self.set_xy(x + w_letra + w_desc + (w_niv*(i-1)), y)
                self.multi_cell(w_niv, 3.5, it[f'nivel_{i}'], border=1)
            
            self.set_xy(x, y + h_fila) # Posicionar para la siguiente fila

    def ficha_alumno_triple(self, nombre_curso, puntos, x_offset, y_start):
        """Dibuja la ficha en un tercio del ancho de página"""
        self.set_xy(x_offset, y_start)
        self.set_font("Arial", "B", 8)
        self.set_fill_color(245, 245, 245)
        
        w_box = 62 # 62 * 3 = 186mm (cabe perfecto en A4)
        nombre_limpio = nombre_curso.split(" (")[0] # Solo nombre para ahorrar espacio
        
        self.cell(w_box, 6, nombre_limpio[:25], 1, 1, "L", True)
        
        y_int = self.get_y()
        for letra, nivel_sel in puntos.items():
            self.set_xy(x_offset, y_int)
            self.set_font("Arial", "", 8)
            self.cell(10, 5, f"{letra}:", 0, 0) # Solo la letra como pediste
            
            for n in range(1, 5):
                if n == int(nivel_sel):
                    self.set_fill_color(200, 200, 200)
                    self.ellipse(self.get_x() + 1, self.get_y() + 0.5, 4, 4, 'F')
                    self.set_font("Arial", "B", 8)
                else:
                    self.set_font("Arial", "", 8)
                self.cell(6, 5, str(n), 0, 0, "C")
            y_int += 5
        return y_int


# --- 3. TÍTULO ---
st.markdown("<h1 style='text-align: center; color: #2E5A88;'>🎓 Registro Evaluación Docente - Aula P.T.</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; font-family: \"Brush Script MT\", cursive; font-size: 35px; color: #5DADE2;'>Maestra Especialista: Ángela Ortíz Ordónez</p>", unsafe_allow_html=True)

tab_alu, tab_conf, tab_eval, tab_hist = st.tabs(["👥 Alumnos", "⚙️ Ítems", "📝 Evaluación", "📅 Histórico"])

# --- TAB 1: ALUMNOS ---
with tab_alu:
    res_alu = supabase.table("elecciona para editar", ["+ Nuevo Alumno"] + [f"{a['nombre']} ({a['curso']})" for a in alumnos_db])
    v_id, v_nom, v_cur = 0, "", ""
    if sel_alu != "+ Nuevo Alumno":
        datos_a = next(a foralumnos").select("*").order("nombre").execute()
    alumnos_db = res_alu.data
    sel_alu = st.selectbox("S a in alumnos_db if f"{a['nombre']} ({a['curso']})" == sel_alu)
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
                    pdf.alias_nb_pages() # Necesario para el footer {nb}
                    pdf.add_page()
                    pdf.tabla_maestra(items_db)
            
                    pdf.set_font("Arial", "B", 12)
                    pdf.cell(0, 10, "RESULTADOS INDIVIDUALES", ln=True)
            
                    ev_print = evals if dia_pdf == "Completo" else [e for e in evals if e['fecha'][:10] == dia_pdf]
            
                    columna = 0 
                    x_posiciones = [10, 75, 140] # Posiciones X para 3 columnas
                    y_inicial = pdf.get_y()
                    y_max_fila = y_inicial

                    for e in ev_print:
                        # Comprobar si necesitamos saltar de página antes de dibujar el siguiente alumno
                        if y_inicial > 250:
                            pdf.add_page()
                            y_inicial = 20
                            y_max_fila = 20

                        x_actual = x_posiciones[columna]
                        y_final_alu = pdf.ficha_alumno_triple(e['nombre_alumno'], e['puntos'], x_actual, y_inicial)
                        y_max_fila = max(y_max_fila, y_final_alu)

                            if columna < 2:
                            columna += 1
                        else:
                            columna = 0
                            y_inicial = y_max_fila + 8 # Espacio entre filas de alumnos
                            y_max_fila = y_inicial

                    st.download_button("Descargar Informe", bytes(pdf.output()), f"Informe_{dia_pdf}.pdf")