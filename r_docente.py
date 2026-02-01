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

# --- 2. CLASE PDF CORREGIDA ---
class EvaluacionPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)
        # Seteamos fuente por defecto desde el inicio
        self.add_page()
        self.set_font("Arial", "", 10)

    def header(self):
        # Evitamos repetir add_page en el header
        self.set_font("Arial", "B", 14)
        self.cell(0, 10, "INFORME DE EVALUACIÓN DOCENTE", ln=True, align="C")
        self.set_font("Arial", "I", 10)
        self.cell(0, 5, "Maestra Especialista: Ángela Ortíz Ordónez", ln=True, align="C")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Página {self.page_no()}/{{nb}}", align="C")

    def get_nb_lines(self, w, txt):
        # Método robusto para calcular líneas
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
            l += cw.get(char, 600) # 600 es un ancho medio por defecto
            if l > wmax:
                nl += 1
                l = cw.get(char, 600)
        return nl

    def tabla_maestra(self, items):
        self.set_font("Arial", "B", 8)
        self.set_fill_color(230, 230, 230)
        w = [8, 32, 37.5, 37.5, 37.5, 37.5] 
        titulos = ["L.", "Descripción", "Nivel 1", "Nivel 2", "Nivel 3", "Nivel 4"]
        
        for i, h in enumerate(titulos):
            self.cell(w[i], 8, h, 1, 0, "C", True)
        self.ln()

        for it in items:
            textos = [it['letra'], it['descripcion'], it['nivel_1'], it['nivel_2'], it['nivel_3'], it['nivel_4']]
            
            # Calculamos la altura máxima
            lineas_por_celda = [self.get_nb_lines(w[i], txt) for i, txt in enumerate(textos)]
            h_fila = max(lineas_por_celda) * 5 
            if h_fila < 10: h_fila = 10

            if self.get_y() + h_fila > 270:
                self.add_page()

            x_ini, y_ini = self.get_x(), self.get_y()

            # Dibujamos cada celda
            for i, txt in enumerate(textos):
                self.set_xy(x_ini, y_ini)
                self.multi_cell(w[i], 5, str(txt), border=1, align='L')
                # Forzamos que el borde de la celda llegue hasta la altura máxima
                self.rect(x_ini, y_ini, w[i], h_fila)
                x_ini += w[i]
            
            self.set_xy(self.l_margin, y_ini + h_fila)

    def bloque_alumnos(self, lista_evaluaciones):
        self.ln(10)
        self.set_font("Arial", "B", 10)
        self.set_fill_color(240, 240, 240)
        self.cell(190, 8, "DETALLE DE EVALUACIÓN POR ALUMNO", 1, 1, "C", True)
        self.ln(2)

        ancho_col = 63.3
        for i, e in enumerate(lista_evaluaciones):
            if i % 3 == 0 and i != 0: self.ln(5)
            if self.get_y() > 250: self.add_page()
            
            x_pos = 10 + ((i % 3) * ancho_col)
            y_bloque = self.get_y()
            
            # Cabecera Alumno
            self.set_xy(x_pos, y_bloque)
            self.set_font("Arial", "B", 8)
            nombre = e['nombre_alumno'].split(" (")[0][:22]
            self.cell(ancho_col, 7, f" {nombre}", 1, 1, "L", True)
            
            y_item = self.get_y()
            for letra, nivel in e['puntos'].items():
                self.set_xy(x_pos, y_item)
                self.set_font("Arial", "", 8)
                self.cell(10, 6, f"{letra}:", "L", 0)
                
                # Niveles con sombreado circular
                for n in range(1, 5):
                    if n == int(nivel):
                        self.set_fill_color(210, 210, 210)
                        self.ellipse(self.get_x() + 2, self.get_y() + 1, 4, 4, 'F')
                        self.set_font("Arial", "B", 8)
                    else:
                        self.set_font("Arial", "", 8)
                    self.cell(13.3, 6, str(n), 0, 0, "C")
                
                self.cell(0.1, 6, "", "R", 1)
                y_item += 6
            
            self.line(x_pos, y_item, x_pos + ancho_col, y_item)
            # Para que el siguiente alumno no empiece arriba si es de la misma fila
            if (i+1) % 3 != 0: self.set_y(y_bloque)
            else: self.set_y(y_item)

# --- 3. INTERFAZ STREAMLIT ---
# (Se mantiene igual a la anterior pero llamando a la clase corregida)
st.markdown("<h1 style='text-align: center; color: #2E5A88;'>🎓 Gestión PT: Ángela Ortiz</h1>", unsafe_allow_html=True)
tab_alu, tab_conf, tab_eval, tab_hist = st.tabs(["👥 Alumnos", "⚙️ Ítems", "📝 Evaluación", "📅 Histórico"])

# --- TAB ALUMNOS (CAMPOS PEQUEÑOS) ---
with tab_alu:
    res_alu = supabase.table("alumnos").select("*").order("nombre").execute()
    alumnos_db = res_alu.data
    
    col1, col2 = st.columns([3, 1])
    sel_alu = col1.selectbox("Alumno", ["+ Nuevo"] + [f"{a['nombre']} ({a['curso']})" for a in alumnos_db])
    
    v_id, v_nom, v_cur = 0, "", ""
    if sel_alu != "+ Nuevo":
        datos = next(a for a in alumnos_db if f"{a['nombre']} ({a['curso']})" == sel_alu)
        v_id, v_nom, v_cur = datos['id'], datos['nombre'], datos['curso']
        if col2.button("🗑️ Eliminar"):
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

# --- TAB ÍTEMS ---
with tab_conf:
    res_it = supabase.table("configuracion_items").select("*").order("letra").execute()
    items_db = res_it.data
    col1, col2 = st.columns([3, 1])
    sel_it = col1.selectbox("Ítem", ["+ Nuevo"] + [f"{i['letra']} - {i['descripcion'][:30]}" for i in items_db])
    
    vi_let, vi_des, vi_n1, vi_n2, vi_n3, vi_n4 = "", "", "", "", "", ""
    if sel_it != "+ Nuevo":
        d = next(i for i in items_db if f"{i['letra']} - {i['descripcion'][:30]}" == sel_it)
        vi_let, vi_des, vi_n1, vi_n2, vi_n3, vi_n4 = d['letra'], d['descripcion'], d['nivel_1'], d['nivel_2'], d['nivel_3'], d['nivel_4']
        if col2.button("🗑️ Borrar"):
            supabase.table("configuracion_items").delete().eq("letra", vi_let).execute()
            st.rerun()

    with st.form("f_it"):
        c1, c2 = st.columns([1, 4])
        l_in = c1.text_input("Letra", value=vi_let).upper()
        d_in = c2.text_input("Descripción", value=vi_des)
        ca, cb = st.columns(2)
        n1, n2 = ca.text_area("N1", value=vi_n1, height=70), cb.text_area("N2", value=vi_n2, height=70)
        n3, n4 = ca.text_area("N3", value=vi_n3, height=70), cb.text_area("N4", value=vi_n4, height=70)
        if st.form_submit_button("Actualizar"):
            supabase.table("configuracion_items").upsert({"letra": l_in, "descripcion": d_in, "nivel_1": n1, "nivel_2": n2, "nivel_3": n3, "nivel_4": n4}).execute()
            st.rerun()

# --- TAB EVALUACIÓN ---
with tab_eval:
    if not alumnos_db: st.info("Crea alumnos primero.")
    else:
        with st.form("f_ev"):
            c1, c2 = st.columns(2)
            al_sel = c1.selectbox("Alumno", [f"{a['nombre']} ({a['curso']})" for a in alumnos_db])
            f_sel = c2.date_input("Fecha", datetime.now())
            res = {}
            for it in items_db:
                st.write(f"**{it['letra']}** - {it['descripcion']}")
                res[it['letra']] = st.radio(f"Nivel {it['letra']}", [1,2,3,4], format_func=lambda x: f"N{x}: {it[f'nivel_{x}']}", key=f"e_{it['letra']}", horizontal=True)
            if st.form_submit_button("Registrar"):
                supabase.table("evaluaciones_alumnos").insert({"nombre_alumno": al_sel, "puntos": res, "fecha": f_sel.isoformat()}).execute()
                st.success("¡Guardado!")

# --- TAB HISTÓRICO ---
with tab_hist:
    evals = supabase.table("evaluaciones_alumnos").select("*").order("fecha", desc=True).execute().data
    if evals:
        df = pd.DataFrame(evals)
        dias = df['fecha'].apply(lambda x: x[:10]).unique()
        dia_pdf = st.selectbox("Día para informe", ["Todos"] + list(dias))
        
        if st.button("🖨️ Generar PDF"):
            pdf = EvaluacionPDF()
            pdf.alias_nb_pages()
            pdf.tabla_maestra(items_db)
            pdf.add_page()
            ev_print = evals if dia_pdf == "Todos" else [e for e in evals if e['fecha'][:10] == dia_pdf]
            pdf.bloque_alumnos(ev_print)
            st.download_button("Descargar", bytes(pdf.output()), "Informe.pdf")
            
        for d in dias:
            with st.expander(f"Día {d}"):
                for _, r in df[df['fecha'].str.startswith(d)].iterrows():
                    c1, c2 = st.columns([5,1])
                    c1.write(r['nombre_alumno'])
                    if c2.button("🗑️", key=f"del_{r['id']}"):
                        supabase.table("evaluaciones_alumnos").delete().eq("id", r['id']).execute()
                        st.rerun()