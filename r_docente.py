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

# --- 2. CLASE PDF CORREGIDA ---
class EvaluacionPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)
        self.add_page()
        self.set_font("Arial", "", 10)

    def header(self):
        # Solo dibujamos si estamos en una página que ya tiene contenido o es la 1
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
        if not txt:
            return 1

        # 🔒 Aseguramos que hay una fuente activa
        if not hasattr(self, "current_font"):
            self.set_font("Arial", "", 7)

        cw = self.current_font['cw']
        wmax = (w - 2 * self.c_margin) * 1000 / self.font_size
        s = str(txt).replace('\r', '')
        nb = len(s)
        sep = -1
        i = j = l = 0
        nl = 1

        while i < nb:
            c = s[i]
            if c == '\n':
                i += 1
                sep = -1
                j = i
                l = 0
                nl += 1
                continue
            if c == ' ':
                sep = i
            l += cw.get(c, 0)
            if l > wmax:
                if sep == -1:
                    if i == j:
                        i += 1
                else:
                    i = sep + 1
                sep = -1
                j = i
                l = 0
                nl += 1
            else:
                i += 1

        return nl


    def tabla_maestra(self, items):
        if not items: return
        self.set_font("Arial", "B", 8)
        self.set_fill_color(230, 230, 230)
        
        # L = 10, Desc = 35, Niveles = 36.25 cada uno (Total 190)
        w = [10, 35, 36.25, 36.25, 36.25, 36.25] 
        headers = ["L.", "Descripción", "Nivel 1", "Nivel 2", "Nivel 3", "Nivel 4"]
        
        for i, h in enumerate(headers):
            self.cell(w[i], 8, h, 1, 0, "C", True)
        self.ln()

        self.set_font("Arial", "", 7)
        for it in items:
            textos = [it['letra'], it['descripcion'], it['nivel_1'], it['nivel_2'], it['nivel_3'], it['nivel_4']]
            
            # Calculamos altura máxima
            n_lineas = [self.get_nb_lines(w[i], t) for i, t in enumerate(textos)]
            h_fila = max(n_lineas) * 4.5
            if h_fila < 8: h_fila = 8

            # Control de salto de página
            if self.get_y() + h_fila > 270:
                self.add_page()
                # Repetir cabecera en nueva página si es necesario
                self.set_font("Arial", "B", 8)
                for i, h in enumerate(headers): self.cell(w[i], 8, h, 1, 0, "C", True)
                self.ln()
                self.set_font("Arial", "", 7)

            x_ini, y_ini = self.get_x(), self.get_y()

            # Dibujo de celdas uniformes
            for i, t in enumerate(textos):
                # Dibujamos el rectángulo de fondo para que todas las columnas midan igual
                self.rect(x_ini, y_ini, w[i], h_fila)
                self.set_xy(x_ini, y_ini)
                self.multi_cell(w[i], 4.5, str(t), 0, 'L')
                x_ini += w[i]
            
            self.set_xy(10, y_ini + h_fila)

    def bloque_alumnos(self, evaluaciones):
        if not evaluaciones: return
        self.ln(10)
        self.set_font("Arial", "B", 10)
        self.set_fill_color(240, 240, 240)
        self.cell(190, 8, "REGISTROS INDIVIDUALES DE EVALUACIÓN", 1, 1, "C", True)
        self.ln(5)

        # Usamos 3 columnas
        w_col = 60
        gap = 5
        
        # Para controlar las filas de alumnos
        y_antes_de_fila = self.get_y()
        max_y_en_fila = y_antes_de_fila

        for i, e in enumerate(evaluaciones):
            col = i % 3
            if col == 0 and i != 0:
                self.set_y(max_y_en_fila + 5)
                y_antes_de_fila = self.get_y()
            
            if self.get_y() > 240:
                self.add_page()
                y_antes_de_fila = self.get_y()
            
            x_pos = 10 + (col * (w_col + gap))
            self.set_xy(x_pos, y_antes_de_fila)
            
            # Cabecera Alumno
            self.set_font("Arial", "B", 8)
            nombre = e['nombre_alumno'].split(" (")[0][:22]
            self.cell(w_col, 6, f" {nombre}", 1, 1, "L", True)
            
            # Items
            y_item = self.get_y()
            for letra, nivel in e['puntos'].items():
                self.set_xy(x_pos, y_item)
                self.set_font("Arial", "", 8)
                self.cell(8, 6, f"{letra}:", "L", 0)
                
                for n in range(1, 5):
                    if n == int(nivel):
                        self.set_fill_color(210, 210, 210)
                        self.ellipse(self.get_x() + 1.5, self.get_y() + 1, 4, 4, 'F')
                        self.set_font("Arial", "B", 8)
                    else:
                        self.set_font("Arial", "", 8)
                    self.cell(13, 6, str(n), 0, 0, "C")
                
                self.cell(0.1, 6, "", "R", 1)
                y_item += 6
            
            self.line(x_pos, y_item, x_pos + w_col, y_item)
            max_y_en_fila = max(max_y_en_fila, y_item)
            
            # Si no es el último de la fila, reseteamos Y para el siguiente alumno
            if (i + 1) % 3 != 0:
                self.set_y(y_antes_de_fila)

# --- 3. INTERFAZ STREAMLIT ---
# (Secciones de Alumnos e Items con el botón de borrar y campos pequeños)

st.markdown("<h1 style='text-align: center;'>🎓 Registro Aula P.T.</h1>", unsafe_allow_html=True)
tab_alu, tab_conf, tab_eval, tab_hist = st.tabs(["👥 Alumnos", "⚙️ Ítems", "📝 Evaluación", "📅 Histórico"])

with tab_alu:
    res_a = supabase.table("alumnos").select("*").order("nombre").execute().data
    c_sel, c_del = st.columns([3, 1])
    sel_a = c_sel.selectbox("Editar Alumno", ["+ Nuevo"] + [f"{a['nombre']} ({a['curso']})" for a in res_a])
    
    v_id, v_nom, v_cur = 0, "", ""
    if sel_a != "+ Nuevo":
        d = next(a for a in res_a if f"{a['nombre']} ({a['curso']})" == sel_a)
        v_id, v_nom, v_cur = d['id'], d['nombre'], d['curso']
        if c_del.button("🗑️ Eliminar Alumno", use_container_width=True):
            supabase.table("alumnos").delete().eq("id", v_id).execute()
            st.rerun()
            
    with st.form("f_alu"):
        c1, c2 = st.columns(2)
        n_in = c1.text_input("Nombre", value=v_nom)
        cur_in = c2.text_input("Curso", value=v_cur)
        if st.form_submit_button("Guardar Alumno"):
            if v_id == 0: supabase.table("alumnos").insert({"nombre": n_in, "curso": cur_in}).execute()
            else: supabase.table("alumnos").update({"nombre": n_in, "curso": cur_in}).eq("id", v_id).execute()
            st.rerun()

with tab_conf:
    res_i = supabase.table("configuracion_items").select("*").order("letra").execute().data
    c_sel_i, c_del_i = st.columns([3, 1])
    sel_i = c_sel_i.selectbox("Editar Ítem", ["+ Nuevo"] + [f"{i['letra']} - {i['descripcion'][:30]}" for i in res_i])
    
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
        d_in = c2.text_input("Descripción", value=v_des)
        ca, cb = st.columns(2)
        n1 = ca.text_area("Nivel 1", value=v_n[0], height=70)
        n2 = cb.text_area("Nivel 2", value=v_n[1], height=70)
        n3 = ca.text_area("Nivel 3", value=v_n[2], height=70)
        n4 = cb.text_area("Nivel 4", value=v_n[3], height=70)
        if st.form_submit_button("Guardar Ítem"):
            supabase.table("configuracion_items").upsert({"letra": l_in, "descripcion": d_in, "nivel_1": n1, "nivel_2": n2, "nivel_3": n3, "nivel_4": n4}).execute()
            st.rerun()

# --- EVALUACIÓN Y HISTÓRICO ---
# (Se mantienen con la llamada a la clase corregida)

with tab_eval:
    if not res_a: st.warning("Crea alumnos primero")
    else:
        with st.form("f_ev"):
            c1, c2 = st.columns(2)
            al_ev = c1.selectbox("Alumno", [f"{a['nombre']} ({a['curso']})" for a in res_a])
            fe_ev = c2.date_input("Fecha", datetime.now())
            pts = {}
            for it in res_i:
                st.write(f"**{it['letra']} - {it['descripcion']}**")
                pts[it['letra']] = st.radio(f"Nivel {it['letra']}", [1,2,3,4], format_func=lambda x: f"N{x}: {it[f'nivel_{x}']}", key=f"ev_{it['letra']}", horizontal=True)
            if st.form_submit_button("Registrar Evaluación"):
                supabase.table("evaluaciones_alumnos").insert({"nombre_alumno": al_ev, "puntos": pts, "fecha": fe_ev.isoformat()}).execute()
                st.success("Registrado con éxito")

with tab_hist:
    evals = supabase.table("evaluaciones_alumnos").select("*").order("fecha", desc=True).execute().data
    if evals:
        df = pd.DataFrame(evals)
        dias = df['fecha'].apply(lambda x: x[:10]).unique()
        sel_dia = st.selectbox("Filtrar día", ["Ver todos"] + list(dias))
        
        if st.button("🖨️ Generar PDF"):
            pdf = EvaluacionPDF()
            pdf.tabla_maestra(res_i)
            ev_sel = evals if sel_dia == "Ver todos" else [e for e in evals if e['fecha'][:10] == sel_dia]
            pdf.bloque_alumnos(ev_sel)
            st.download_button("Descargar Informe", bytes(pdf.output()), f"Informe_{sel_dia}.pdf")
        
        for d in dias:
            with st.expander(f"Registros del {d}"):
                for _, r in df[df['fecha'].str.startswith(d)].iterrows():
                    c1, c2 = st.columns([5, 1])
                    c1.write(f"👤 {r['nombre_alumno']}")
                    if c2.button("🗑️", key=f"del_h_{r['id']}"):
                        supabase.table("evaluaciones_alumnos").delete().eq("id", r['id']).execute()
                        st.rerun()