import streamlit as st
import pandas as pd
from fpdf import FPDF
from supabase import create_client
from datetime import datetime

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Registro Docente", layout="wide")

@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_connection()

# --- 2. CLASE PDF PROFESIONAL ---
class EvaluacionPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)
        self.add_page()
        self.set_font("Arial", "", 10) # Fuente inicial obligatoria

    def header(self):
        self.set_font("Arial", "B", 14)
        self.cell(0, 10, "INFORME DE EVALUACIÓN DOCENTE", ln=True, align="C")
        self.set_font("Arial", "I", 9)
        self.cell(0, 5, "Maestra Especialista: Ángela Ortíz Ordónez", ln=True, align="C")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Página {self.page_no()}/{{nb}}", align="C")

    def get_nb_lines(self, w, txt):
        """Calcula cuántas líneas ocupará un texto en un ancho dado."""
        self.set_font("Arial", "", 7)
        cw = self.current_font['cw']
        if w == 0: w = self.w - self.r_margin - self.x
        wmax = (w - 2 * self.c_margin) * 1000 / self.font_size_pt
        s = str(txt).replace("\r", '')
        nb = len(s)
        l = 0
        nl = 1
        for char in s:
            if char == "\n":
                nl += 1
                l = 0
                continue
            l += cw.get(char, 600)
            if l > wmax:
                nl += 1
                l = cw.get(char, 600)
        return nl

    def tabla_maestra(self, items):
        self.set_font("Arial", "B", 8)
        self.set_fill_color(230, 230, 230)
        w = [8, 32, 37.5, 37.5, 37.5, 37.5] 
        headers = ["L.", "Descripción", "Nivel 1", "Nivel 2", "Nivel 3", "Nivel 4"]
        
        for i, h in enumerate(headers):
            self.cell(w[i], 8, h, 1, 0, "C", True)
        self.ln()

        for it in items:
            textos = [it['letra'], it['descripcion'], it['nivel_1'], it['nivel_2'], it['nivel_3'], it['nivel_4']]
            # Calculamos la altura máxima de la fila
            lineas = [self.get_nb_lines(w[i], t) for i, t in enumerate(textos)]
            h_fila = max(lineas) * 4.5
            if h_fila < 8: h_fila = 8

            if self.get_y() + h_fila > 275:
                self.add_page()

            x_ini, y_ini = self.get_x(), self.get_y()
            for i, t in enumerate(textos):
                # Dibujamos el borde de la celda con la altura máxima calculada
                self.rect(x_ini, y_ini, w[i], h_fila)
                self.set_xy(x_ini, y_ini)
                self.multi_cell(w[i], 4.5, str(t), 0, 'L')
                x_ini += w[i]
            self.set_xy(self.l_margin, y_ini + h_fila)

    def bloque_alumnos(self, evaluaciones):
        self.ln(5)
        self.set_fill_color(245, 245, 245)
        self.set_font("Arial", "B", 10)
        self.cell(190, 8, "REGISTRO DE EVALUACIÓN POR ALUMNO", 1, 1, "C", True)
        self.ln(4)

        ancho_col = 60
        gap = 5
        
        for i, e in enumerate(evaluaciones):
            # Control de salto de página y posición en 3 columnas
            if i % 3 == 0 and i != 0: self.ln(10)
            if self.get_y() > 240: self.add_page()
            
            x_pos = 10 + ((i % 3) * (ancho_col + gap))
            y_base = self.get_y()
            
            # Cabecera Alumno
            self.set_xy(x_pos, y_base)
            self.set_font("Arial", "B", 8)
            nombre = e['nombre_alumno'].split(" (")[0][:22]
            self.cell(ancho_col, 6, f" {nombre}", 1, 1, "L", True)
            
            y_item = self.get_y()
            for letra, nivel in e['puntos'].items():
                self.set_xy(x_pos, y_item)
                self.set_font("Arial", "", 8)
                self.cell(8, 6, f"{letra}:", "L", 0)
                
                for n in range(1, 5):
                    if n == int(nivel):
                        self.set_fill_color(200, 200, 200) # Sombreado gris
                        self.ellipse(self.get_x() + 1.5, self.get_y() + 1, 4, 4, 'F')
                        self.set_font("Arial", "B", 8)
                    else:
                        self.set_font("Arial", "", 8)
                    self.cell(13, 6, str(n), 0, 0, "C")
                
                self.cell(0.1, 6, "", "R", 1) # Cierre visual derecho
                y_item += 6
            
            self.line(x_pos, y_item, x_pos + ancho_col, y_item) # Línea base
            # Mantener la Y para que los de la misma fila no se desplacen
            if (i + 1) % 3 != 0: self.set_y(y_base)
            else: self.set_y(y_item)

# --- 3. INTERFAZ STREAMLIT ---
st.title("🎓 Registro Docente Aula P.T.")

tab_alu, tab_conf, tab_eval, tab_hist = st.tabs(["👥 Alumnos", "⚙️ Ítems", "📝 Evaluación", "📅 Histórico"])

with tab_alu:
    res = supabase.table("alumnos").select("*").order("nombre").execute().data
    col_s, col_d = st.columns([3, 1])
    sel = col_s.selectbox("Seleccionar Alumno", ["+ Nuevo"] + [f"{a['nombre']} ({a['curso']})" for a in res])
    
    v_id, v_nom, v_cur = 0, "", ""
    if sel != "+ Nuevo":
        d = next(a for a in res if f"{a['nombre']} ({a['curso']})" == sel)
        v_id, v_nom, v_cur = d['id'], d['nombre'], d['curso']
        if col_d.button("🗑️ Eliminar"):
            supabase.table("alumnos").delete().eq("id", v_id).execute()
            st.rerun()

    with st.form("f_alu"):
        c1, c2 = st.columns(2)
        n_in = c1.text_input("Nombre", value=v_nom)
        c_in = c2.text_input("Curso", value=v_cur)
        if st.form_submit_button("Guardar"):
            if v_id == 0: supabase.table("alumnos").insert({"nombre": n_in, "curso": c_in}).execute()
            else: supabase.table("alumnos").update({"nombre": n_in, "curso": c_in}).eq("id", v_id).execute()
            st.rerun()

with tab_conf:
    res_i = supabase.table("configuracion_items").select("*").order("letra").execute().data
    col_s, col_d = st.columns([3, 1])
    sel_i = col_s.selectbox("Seleccionar Ítem", ["+ Nuevo"] + [f"{i['letra']} - {i['descripcion'][:30]}" for i in res_i])
    
    v_let, v_des, v_n = "", "", [""]*4
    if sel_i != "+ Nuevo":
        d = next(i for i in res_i if f"{i['letra']} - {i['descripcion'][:30]}" == sel_i)
        v_let, v_des, v_n = d['letra'], d['descripcion'], [d['nivel_1'], d['nivel_2'], d['nivel_3'], d['nivel_4']]
        if col_d.button("🗑️ Borrar Ítem"):
            supabase.table("configuracion_items").delete().eq("letra", v_let).execute()
            st.rerun()

    with st.form("f_item"):
        c1, c2 = st.columns([1, 4])
        l_in = c1.text_input("Letra", value=v_let).upper()
        d_in = c2.text_input("Descripción", value=v_des)
        ca, cb = st.columns(2)
        n1 = ca.text_area("Nivel 1", value=v_n[0], height=70)
        n2 = cb.text_area("Nivel 2", value=v_n[1], height=70)
        n3 = ca.text_area("Nivel 3", value=v_n[2], height=70)
        n4 = cb.text_area("Nivel 4", value=v_n[3], height=70)
        if st.form_submit_button("Guardar Ítem"):
            supabase.table("configuracion_items").upsert({"letra": l_in, "descripcion": d_in, "nivel_1": n1, "nivel_2": n2, "nivel_3": n3, "nivel_4": n4}).execute()
            st.rerun()

with tab_eval:
    items = supabase.table("configuracion_items").select("*").order("letra").execute().data
    alumnos = supabase.table("alumnos").select("*").order("nombre").execute().data
    if not alumnos: st.warning("Crea alumnos primero")
    else:
        with st.form("f_ev"):
            c1, c2 = st.columns(2)
            al_ev = c1.selectbox("Alumno", [f"{a['nombre']} ({a['curso']})" for a in alumnos])
            fe_ev = c2.date_input("Fecha", datetime.now())
            pts = {}
            for it in items:
                st.write(f"**{it['letra']} - {it['descripcion']}**")
                pts[it['letra']] = st.radio(f"Nivel {it['letra']}", [1,2,3,4], format_func=lambda x: f"N{x}: {it[f'nivel_{x}']}", key=f"ev_{it['letra']}", horizontal=True)
            if st.form_submit_button("Registrar Evaluación"):
                supabase.table("evaluaciones_alumnos").insert({"nombre_alumno": al_ev, "puntos": pts, "fecha": fe_ev.isoformat()}).execute()
                st.success("Registrado")

with tab_hist:
    evals = supabase.table("evaluaciones_alumnos").select("*").order("fecha", desc=True).execute().data
    if evals:
        df = pd.DataFrame(evals)
        dias = df['fecha'].apply(lambda x: x[:10]).unique()
        sel_dia = st.selectbox("Día", ["Todos"] + list(dias))
        
        if st.button("🖨️ Generar PDF Profesional"):
            pdf = EvaluacionPDF()
            pdf.tabla_maestra(res_i)
            pdf.add_page()
            ev_sel = evals if sel_dia == "Todos" else [e for e in evals if e['fecha'][:10] == sel_dia]
            pdf.bloque_alumnos(ev_sel)
            st.download_button("Descargar PDF", bytes(pdf.output()), f"Informe_{sel_dia}.pdf")
        
        for d in dias:
            with st.expander(f"Día {d}"):
                for _, r in df[df['fecha'].str.startswith(d)].iterrows():
                    c1, c2 = st.columns([5, 1])
                    c1.write(f"👤 {r['nombre_alumno']}")
                    if c2.button("🗑️", key=f"del_{r['id']}"):
                        supabase.table("evaluaciones_alumnos").delete().eq("id", r['id']).execute()
                        st.rerun()