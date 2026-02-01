import streamlit as st
import pandas as pd
from fpdf import FPDF
from supabase import create_client
from datetime import datetime

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Registro Docente | Ángela Ortíz", layout="wide")

@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_connection()

# --- 2. CLASE PDF PROFESIONAL (Sin rastro de "None") ---
class EvaluacionPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)
        self.add_page()

    def header(self):
        self.set_font("Arial", "B", 14)
        self.set_text_color(40, 40, 40)
        self.cell(0, 10, "INFORME DE EVALUACIÓN DOCENTE", ln=True, align="C")
        self.set_font("Arial", "I", 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, "Maestra Especialista: Ángela Ortíz Ordónez", ln=True, align="C")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Página {self.page_no()}/{{nb}}", align="C")

    def tabla_maestra(self, items):
        if not items: return
        self.set_font("Arial", "B", 8)
        self.set_fill_color(230, 230, 230)
        w = [10, 35, 36.25, 36.25, 36.25, 36.25] 
        headers = ["L.", "Descripción", "Nivel 1", "Nivel 2", "Nivel 3", "Nivel 4"]
        for i, h in enumerate(headers):
            self.cell(w[i], 8, h, 1, 0, "C", True)
        self.ln()
        
        self.set_font("Arial", "", 7)
        for it in items:
            textos = [it['letra'], it['descripcion'], it['nivel_1'], it['nivel_2'], it['nivel_3'], it['nivel_4']]
            alturas = [len(self.multi_cell(w[i], 4, str(t), split_only=True)) * 4 for i, t in enumerate(textos)]
            h_fila = max(alturas) + 2
            if h_fila < 8: h_fila = 8

            if self.get_y() + h_fila > 270:
                self.add_page()
                self.set_font("Arial", "B", 8)
                self.set_fill_color(230, 230, 230)
                for i, h in enumerate(headers): self.cell(w[i], 8, h, 1, 0, "C", True)
                self.ln()

            x_ini, y_ini = self.get_x(), self.get_y()
            for i, t in enumerate(textos):
                # Corrección del "None": Usamos IF clásico
                if i < 2:
                    self.set_fill_color(245, 245, 245)
                    style = 'FD'
                else:
                    style = 'D'
                
                self.rect(x_ini, y_ini, w[i], h_fila, style=style)
                self.set_xy(x_ini, y_ini)
                self.multi_cell(w[i], 4, str(t), 0, 'L')
                x_ini += w[i]
            self.set_xy(10, y_ini + h_fila)

    def bloque_alumnos(self, evaluaciones):
        if not evaluaciones: return
        self.set_font("Arial", "B", 10)
        self.set_fill_color(240, 240, 240)
        self.cell(190, 8, "EVALUACIÓN ALUMNADO", 1, 1, "C", True)
        self.ln(5)
        
        w_col, gap = 60, 5
        num_items = len(evaluaciones[0]['puntos']) if evaluaciones else 0
        h_alumno = 7 + (num_items * 6) + 5 
        
        for i in range(0, len(evaluaciones), 3):
            if self.get_y() + h_alumno > 275:
                self.add_page()

            y_inicio_fila = self.get_y()
            for j in range(3):
                idx = i + j
                if idx < len(evaluaciones):
                    e = evaluaciones[idx]
                    x_pos = 10 + (j * (w_col + gap))
                    self.set_xy(x_pos, y_inicio_fila)
                    
                    self.set_font("Arial", "B", 8)
                    self.set_fill_color(240, 240, 240)
                    nombre_completo = e['nombre_alumno'][:35]
                    self.cell(w_col, 7, f" {nombre_completo}", 1, 1, "L", True)
                    
                    y_item = self.get_y()
                    for letra, nivel in e['puntos'].items():
                        self.set_xy(x_pos, y_item)
                        self.set_font("Arial", "", 8)
                        self.cell(8, 6, f"{letra}:", "L", 0)
                        for n in range(1, 5):
                            if n == int(nivel):
                                self.set_fill_color(200, 200, 200)
                                self.ellipse(self.get_x() + 4.5, self.get_y() + 1, 4, 4, 'F')
                                self.set_font("Arial", "B", 8)
                            else:
                                self.set_font("Arial", "", 8)
                            self.cell(13, 6, str(n), 0, 0, "C")
                        self.cell(0.1, 6, "", "R", 1)
                        y_item += 6
                    self.line(x_pos, y_item, x_pos + w_col, y_item)
            self.set_y(y_inicio_fila + h_alumno)

# --- 3. INTERFAZ STREAMLIT ESTILIZADA ---

# Cabecera con Estilo
st.markdown("""
    <div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px; border-left: 8px solid #4f64af; margin-bottom: 20px;">
        <h1 style="margin: 0; color: #1e3d59; font-family: 'Helvetica Neue', sans-serif;">🎓 Registro Aula P.T.</h1>
        <p style="margin: 0; color: #4f64af; font-size: 1.2rem; font-weight: bold;">Maestra Especialista: <span style="color: #ff6e40;">Ángela Ortíz Ordónez</span></p>
    </div>
    """, unsafe_allow_html=True)

tab_alu, tab_conf, tab_eval, tab_hist = st.tabs(["👥 Alumnos", "⚙️ Ítems", "📝 Evaluación", "📅 Histórico"])

# --- CARGA DE DATOS ---
res_a_raw = supabase.table("alumnos").select("*").execute().data
orden_cursos = ["INF 3", "INF 4", "INF 5", "1º", "2º", "3º", "4º", "5º", "6º"]
res_a = sorted(res_a_raw, key=lambda x: (orden_cursos.index(x["curso"]) if x["curso"] in orden_cursos else 999, x["nombre"]))
res_i = supabase.table("configuracion_items").select("*").order("letra").execute().data

# --- TAB ALUMNOS ---
with tab_alu:
    c_sel, c_del = st.columns([3, 1])
    sel_a = c_sel.selectbox("Seleccionar Alumno", ["+ Nuevo"] + [f"{a['nombre']} ({a['curso']})" for a in res_a])
    v_id, v_nom, v_cur = 0, "", ""
    if sel_a != "+ Nuevo":
        d = next(a for a in res_a if f"{a['nombre']} ({a['curso']})" == sel_a)
        v_id, v_nom, v_cur = d['id'], d['nombre'], d['curso']
        if c_del.button("🗑️ Eliminar Alumno", use_container_width=True):
            supabase.table("alumnos").delete().eq("id", v_id).execute()
            st.rerun()
    with st.form("f_alu"):
        c1, c2 = st.columns(2)
        n_in = c1.text_input("Nombre Completo", value=v_nom)
        cur_in = c2.text_input("Curso (Ej: 1º, INF 5)", value=v_cur)
        if st.form_submit_button("💾 Guardar Datos Alumno"):
            if v_id == 0: supabase.table("alumnos").insert({"nombre": n_in, "curso": cur_in}).execute()
            else: supabase.table("alumnos").update({"nombre": n_in, "curso": cur_in}).eq("id", v_id).execute()
            st.rerun()

# --- TAB ÍTEMS ---
with tab_conf:
    c_sel_i, c_del_i = st.columns([3, 1])
    sel_i = c_sel_i.selectbox("Seleccionar Ítem", ["+ Nuevo"] + [f"{i['letra']} - {i['descripcion'][:30]}" for i in res_i])
    v_let, v_des, v_n = "", "", [""]*4
    if sel_i != "+ Nuevo":
        d = next(i for i in res_i if f"{i['letra']} - {i['descripcion'][:30]}" == sel_i)
        v_let, v_des, v_n = d['letra'], d['descripcion'], [d['nivel_1'], d['nivel_2'], d['nivel_3'], d['nivel_4']]
        if c_del_i.button("🗑️ Eliminar Ítem", use_container_width=True):
            supabase.table("configuracion_items").delete().eq("letra", v_let).execute()
            st.rerun()
    with st.form("f_item"):
        c1, c2 = st.columns([1, 4])
        l_in = c1.text_input("Letra", value=v_let).upper()
        d_in = c2.text_input("Descripción del ítem", value=v_des)
        ca, cb = st.columns(2)
        n1, n2 = ca.text_area("Nivel 1", value=v_n[0]), cb.text_area("Nivel 2", value=v_n[1])
        n3, n4 = ca.text_area("Nivel 3", value=v_n[2]), cb.text_area("Nivel 4", value=v_n[3])
        if st.form_submit_button("💾 Guardar Configuración de Ítem"):
            supabase.table("configuracion_items").upsert({"letra": l_in, "descripcion": d_in, "nivel_1": n1, "nivel_2": n2, "nivel_3": n3, "nivel_4": n4}).execute()
            st.rerun()

# --- TAB EVALUACIÓN ---
with tab_eval:
    if not res_a: st.warning("⚠️ No hay alumnos registrados.")
    else:
        c1, c2 = st.columns(2)
        fe_ev = c2.date_input("Fecha de Sesión", datetime.now())
        evals_hoy = supabase.table("evaluaciones_alumnos").select("nombre_alumno").eq("fecha", fe_ev.isoformat()).execute().data
        set_ev = {ev['nombre_alumno'] for ev in evals_hoy}
        pend, comp = [], []
        for a in res_a:
            nom = f"{a['nombre']} ({a['curso']})"
            if nom in set_ev: comp.append(f"✅ {nom}")
            else: pend.append(nom)
        al_sel = c1.selectbox("Elegir Alumno", pend + comp)
        is_done = al_sel.startswith("✅")
        if is_done: st.error("Este alumno ya tiene una evaluación hoy.")
        with st.form("f_ev", clear_on_submit=True):
            pts = {}
            for it in res_i:
                st.write(f"**{it['letra']} - {it['descripcion']}**")
                pts[it['letra']] = st.radio(f"Nivel {it['letra']}", [1,2,3,4], format_func=lambda x, it=it: f"N{x}: {it[f'nivel_{x}']}", key=f"e_{it['letra']}", horizontal=True)
            if st.form_submit_button("📝 Registrar Evaluación", disabled=is_done):
                supabase.table("evaluaciones_alumnos").insert({"nombre_alumno": al_sel, "puntos": pts, "fecha": fe_ev.isoformat()}).execute()
                st.rerun()

# --- TAB HISTÓRICO ---
with tab_hist:
    evals = supabase.table("evaluaciones_alumnos").select("*").order("fecha", desc=True).execute().data
    if evals:
        df = pd.DataFrame(evals)
        df['f_corta'] = df['fecha'].map(lambda x: x[:10])
        dias = df['f_corta'].unique()
        c_dia, c_pdf = st.columns([3, 1])
        sel_d = c_dia.selectbox("Filtrar por Fecha", ["Ver todos"] + list(dias))
        if c_pdf.button("🖨️ Generar Informe PDF", use_container_width=True):
            pdf = EvaluacionPDF()
            pdf.tabla_maestra(res_i)
            pdf.add_page()
            ev_f = evals if sel_d == "Ver todos" else [e for e in evals if e['fecha'][:10] == sel_d]
            pdf.bloque_alumnos(ev_f)
            st.download_button("⬇️ Descargar PDF", bytes(pdf.output()), f"Informe_{sel_d}.pdf", use_container_width=True)
        for d in dias:
            with st.expander(f"📅 Sesiones del día {d}"):
                for _, r in df[df['f_corta'] == d].iterrows():
                    c1, c2 = st.columns([5, 1])
                    c1.write(f"👤 **{r['nombre_alumno']}**")
                    if c2.button("🗑️", key=f"h_{r['id']}"):
                        supabase.table("evaluaciones_alumnos").delete().eq("id", r['id']).execute()
                        st.rerun()