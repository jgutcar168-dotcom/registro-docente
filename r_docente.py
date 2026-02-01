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

# --- 2. CLASE PDF CORREGIDA (Uniformidad y Círculos) ---
class EvaluacionPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)
        self.add_page()
        self.set_font("Arial", "", 10)

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
        if not txt: return 1
        self.set_font("Arial", "", 7)
        max_width = w - 4 
        lines = 0
        for paragraph in str(txt).split("\n"):
            words = paragraph.split(" ")
            current_line = ""
            for word in words:
                test_line = current_line + (" " if current_line else "") + word
                if self.get_string_width(test_line) <= max_width:
                    current_line = test_line
                else:
                    lines += 1
                    current_line = word
            lines += 1
        return lines

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
            n_lineas = [self.get_nb_lines(w[i], t) for i, t in enumerate(textos)]
            h_fila = max(n_lineas) * 4.5
            if h_fila < 8: h_fila = 8

            if self.get_y() + h_fila > 270:
                self.add_page()
                # Re-imprimir cabeceras
                self.set_font("Arial", "B", 8)
                for i, h in enumerate(headers): self.cell(w[i], 8, h, 1, 0, "C", True)
                self.ln()
                self.set_font("Arial", "", 7)

            x_ini, y_ini = self.get_x(), self.get_y()
            for i, t in enumerate(textos):
                # Marco uniforme
                self.rect(x_ini, y_ini, w[i], h_fila)
                self.set_xy(x_ini, y_ini)
                self.multi_cell(w[i], 4.5, str(t), 0, 'L')
                x_ini += w[i]
            self.set_xy(10, y_ini + h_fila)

    def bloque_alumnos(self, evaluaciones):
        if not evaluaciones: return
        self.ln(5)
        self.set_font("Arial", "B", 10)
        self.set_fill_color(240, 240, 240)
        self.cell(190, 8, "EVALUACIÓN ALUMNADO", 1, 1, "C", True)
        self.ln(5)

        w_col, gap = 60, 5
        y_fila = self.get_y()
        max_y_fila = y_fila

        for i, e in enumerate(evaluaciones):
            col = i % 3
            if col == 0 and i != 0:
                y_fila = max_y_fila + 8
                max_y_fila = y_fila
            
            if y_fila > 240:
                self.add_page()
                y_fila = self.get_y()
            
            x_pos = 10 + (col * (w_col + gap))
            self.set_xy(x_pos, y_fila)
            
            # Cabecera Alumno
            self.set_font("Arial", "B", 8)
            nombre = e['nombre_alumno'].split(" (")[0][:22]
            self.cell(w_col, 7, f" {nombre}", 1, 1, "L", True)
            
            y_item = self.get_y()
            for letra, nivel in e['puntos'].items():
                self.set_xy(x_pos, y_item)
                self.set_font("Arial", "", 8)
                self.cell(8, 6, f"{letra}:", "L", 0) # Borde izquierdo
                
                for n in range(1, 5):
                    if n == int(nivel):
                        self.set_fill_color(200, 200, 200)
                        # Dibujamos círculo (elipse)
                        self.ellipse(self.get_x() + 4.5, self.get_y() + 1, 4, 4, 'F')
                        self.set_font("Arial", "B", 8)
                    else:
                        self.set_font("Arial", "", 8)
                    self.cell(13, 6, str(n), 0, 0, "C")
                
                self.cell(0.1, 6, "", "R", 1) # Borde derecho
                y_item += 6
            
            self.line(x_pos, y_item, x_pos + w_col, y_item) # Línea inferior
            max_y_fila = max(max_y_fila, y_item)
            if (i+1) % 3 != 0: self.set_y(y_fila) # Mantener altura para el siguiente en la fila

# --- 3. INTERFAZ STREAMLIT ---

st.markdown("<h1 style='text-align: center;'>🎓 Registro Aula P.T.</h1>", unsafe_allow_html=True)
tab_alu, tab_conf, tab_eval, tab_hist = st.tabs(["👥 Alumnos", "⚙️ Ítems", "📝 Evaluación", "📅 Histórico"])

# --- LÓGICA DE ALUMNOS ---
with tab_alu:
    res_a = supabase.table("alumnos").select("*").execute().data
    orden_cursos = ["INF 3", "INF 4", "INF 5", "1º", "2º", "3º", "4º", "5º", "6º"]
    res_a = sorted(res_a, key=lambda x: (orden_cursos.index(x["curso"]) if x["curso"] in orden_cursos else 999, x["nombre"]))

    c_sel, c_del = st.columns([3, 1])
    sel_a = c_sel.selectbox("Editar Alumno", ["+ Nuevo"] + [f"{a['nombre']} ({a['curso']})" for a in res_a])
    
    v_id, v_nom, v_cur = 0, "", ""
    if sel_a != "+ Nuevo":
        d = next(a for a in res_a if f"{a['nombre']} ({a['curso']})" == sel_a)
        v_id, v_nom, v_cur = d['id'], d['nombre'], d['curso']
        if c_del.button("🗑️ Eliminar Alumno"):
            supabase.table("alumnos").delete().eq("id", v_id).execute()
            st.rerun()
            
    with st.form("f_alu"):
        c1, c2 = st.columns(2)
        n_in = c1.text_input("Nombre", value=v_nom)
        cur_in = c2.text_input("Curso", value=v_cur)
        if st.form_submit_button("Guardar"):
            if v_id == 0: supabase.table("alumnos").insert({"nombre": n_in, "curso": cur_in}).execute()
            else: supabase.table("alumnos").update({"nombre": n_in, "curso": cur_in}).eq("id", v_id).execute()
            st.rerun()

# --- LÓGICA DE ÍTEMS ---
with tab_conf:
    res_i = supabase.table("configuracion_items").select("*").order("letra").execute().data
    c_sel_i, c_del_i = st.columns([3, 1])
    sel_i = c_sel_i.selectbox("Editar Ítem", ["+ Nuevo"] + [f"{i['letra']} - {i['descripcion'][:30]}" for i in res_i])
    
    v_let, v_des, v_n = "", "", [""]*4
    if sel_i != "+ Nuevo":
        d = next(i for i in res_i if f"{i['letra']} - {i['descripcion'][:30]}" == sel_i)
        v_let, v_des, v_n = d['letra'], d['descripcion'], [d['nivel_1'], d['nivel_2'], d['nivel_3'], d['nivel_4']]
        if c_del_i.button("🗑️ Eliminar Ítem"):
            supabase.table("configuracion_items").delete().eq("letra", v_let).execute()
            st.rerun()

    with st.form("f_item"):
        c1, c2 = st.columns([1, 4])
        l_in = c1.text_input("Letra", value=v_let).upper()
        d_in = c2.text_input("Descripción", value=v_des)
        ca, cb = st.columns(2)
        n1, n2 = ca.text_area("N1", value=v_n[0]), cb.text_area("N2", value=v_n[1])
        n3, n4 = ca.text_area("N3", value=v_n[2]), cb.text_area("N4", value=v_n[3])
        if st.form_submit_button("Guardar Ítem"):
            supabase.table("configuracion_items").upsert({"letra": l_in, "descripcion": d_in, "nivel_1": n1, "nivel_2": n2, "nivel_3": n3, "nivel_4": n4}).execute()
            st.rerun()

# --- LÓGICA DE EVALUACIÓN ---
with tab_eval:
    if not res_a: st.warning("Crea alumnos")
    else:
        with st.form("f_ev"):
            c1, c2 = st.columns(2)
            lista_fmt = [f"{a['nombre']} ({a['curso']})" for a in res_a]
            al_ev = c1.selectbox("Alumno", lista_fmt)
            fe_ev = c2.date_input("Fecha", datetime.now())
            pts = {}
            for it in res_i:
                st.write(f"**{it['letra']} - {it['descripcion']}**")
                pts[it['letra']] = st.radio(f"Nivel {it['letra']}", [1, 2, 3, 4], 
                                            format_func=lambda x, it=it: f"N{x}: {it[f'nivel_{x}']}", 
                                            key=f"ev_{it['letra']}", horizontal=True)
            if st.form_submit_button("Registrar"):
                supabase.table("evaluaciones_alumnos").insert({"nombre_alumno": al_ev, "puntos": pts, "fecha": fe_ev.isoformat()}).execute()
                st.success("Guardado")

# --- LÓGICA DE HISTÓRICO (CORREGIDA) ---
with tab_hist:
    # Forzamos consulta fresca
    evals_query = supabase.table("evaluaciones_alumnos").select("*").order("fecha", desc=True).execute()
    evals = evals_query.data
    
    if not evals:
        st.info("No hay evaluaciones registradas todavía.")
    else:
        df_ev = pd.DataFrame(evals)
        # Extraer solo la parte de la fecha YYYY-MM-DD
        df_ev['fecha_corta'] = df_ev['fecha'].map(lambda x: x[:10])
        dias = df_ev['fecha_corta'].unique()
        
        c_dia, c_pdf = st.columns([3, 1])
        sel_dia = c_dia.selectbox("Seleccionar día", ["Ver todos"] + list(dias))
        
        if c_pdf.button("🖨️ PDF"):
            pdf = EvaluacionPDF()
            pdf.tabla_maestra(res_i)
            pdf.add_page()
            ev_final = evals if sel_dia == "Ver todos" else [e for e in evals if e['fecha'][:10] == sel_dia]
            pdf.bloque_alumnos(ev_final)
            st.download_button("Descargar", bytes(pdf.output()), "Informe.pdf")

        for d in dias:
            with st.expander(f"📅 Registros del día {d}"):
                # Filtrar el dataframe para este día
                registros_dia = df_ev[df_ev['fecha_corta'] == d]
                for _, r in registros_dia.iterrows():
                    col1, col2 = st.columns([5, 1])
                    col1.write(f"👤 **{r['nombre_alumno']}**")
                    if col2.button("🗑️", key=f"del_{r['id']}"):
                        supabase.table("evaluaciones_alumnos").delete().eq("id", r['id']).execute()
                        st.rerun()