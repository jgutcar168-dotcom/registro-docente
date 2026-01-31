import streamlit as st
import pandas as pd
from fpdf import FPDF
from supabase import create_client
from datetime import datetime

# --- 1. CONFIGURACIÓN Y CONEXIÓN ---
st.set_page_config(page_title="Gestión Docente", layout="wide")

@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_connection()

# --- 2. CLASE PDF (Debe estar aquí, antes de cualquier uso) ---
class EvaluacionPDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 16)
        self.cell(0, 10, "INFORME DE EVALUACIÓN", ln=True, align="C")
        self.set_font("Arial", "I", 10)
        self.cell(0, 10, "Maestra Especialista", ln=True, align="C")
        self.ln(5)

    def tabla_maestra(self, items):
        self.set_font("Arial", "B", 11)
        self.set_fill_color(230, 230, 230)
        self.cell(0, 10, "1. REFERENCIA DE ITEMS Y NIVELES", ln=True)
        self.set_font("Arial", "B", 8)
        self.cell(10, 8, "It.", 1, 0, "C", True)
        self.cell(40, 8, "Descripcion", 1, 0, "C", True)
        for i in range(1, 5):
            self.cell(35, 8, f"Nivel {i}", 1, 0, "C", True)
        self.ln()
        self.set_font("Arial", "", 7)
        for it in items:
            self.cell(10, 8, it['letra'], 1, 0, "C")
            self.cell(40, 8, it['descripcion'][:25], 1, 0, "L")
            self.cell(35, 8, it['nivel_1'][:25], 1, 0, "L")
            self.cell(35, 8, it['nivel_2'][:25], 1, 0, "L")
            self.cell(35, 8, it['nivel_3'][:25], 1, 0, "L")
            self.cell(35, 8, it['nivel_4'][:25], 1, 1, "L")
        self.ln(5)

    def ficha_alumno(self, nombre_curso, puntos):
        self.set_font("Arial", "B", 12)
        self.set_fill_color(245, 245, 245)
        self.cell(0, 10, f"Alumno: {nombre_curso}", 1, 1, "L", True)
        self.ln(2)
        for letra, nivel_sel in puntos.items():
            self.set_font("Arial", "", 11)
            self.cell(30, 8, f"Item {letra}:", 0, 0)
            for n in range(1, 5):
                if n == int(nivel_sel):
                    self.set_fill_color(200, 200, 200)
                    self.ellipse(self.get_x() + 2, self.get_y() + 1, 6, 6, 'F')
                    self.set_font("Arial", "B", 11)
                    self.cell(10, 8, str(n), 0, 0, "C")
                else:
                    self.set_font("Arial", "", 11)
                    self.cell(10, 8, str(n), 0, 0, "C")
            self.ln(8)
        self.ln(4)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

# --- 3. TÍTULO ---
st.markdown("<h1 style='text-align: center; color: #2E5A88;'>🎓 Gestión de Evaluación Docente</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; font-family: \"Brush Script MT\", cursive; font-size: 25px; color: #5DADE2;'>Maestra Especialista: [Tu Nombre Aquí]</p>", unsafe_allow_html=True)

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
        
        if st.button("Generar PDF"):
            pdf = EvaluacionPDF()
            pdf.add_page()
            pdf.tabla_maestra(items_db)
            ev_print = evals if dia_pdf == "Completo" else [e for e in evals if e['fecha'][:10] == dia_pdf]
            for e in ev_print:
                pdf.ficha_alumno(e['nombre_alumno'], e['puntos'])
            st.download_button("Descargar", bytes(pdf.output()), "informe.pdf")

        for d in dias:
            with st.expander(f"📅 {d}"):
                for _, r in df[df['fecha_dia'] == d].iterrows():
                    c1, c2 = st.columns([5,1])
                    c1.write(r['nombre_alumno'])
                    if c2.button("🗑️", key=f"del_{r['id']}"):
                        supabase.table("evaluaciones_alumnos").delete().eq("id", r['id']).execute()
                        st.rerun()