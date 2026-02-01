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

# --- 2. CLASE PDF MEJORADA ---
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
        self.set_font("Arial", "B", 8)
        self.set_fill_color(230, 230, 230)
        
        # Anchos ajustados para A4 (Total 190mm)
        w = [8, 32, 37.5, 37.5, 37.5, 37.5] 
        headers = ["L.", "Descripción", "Nivel 1", "Nivel 2", "Nivel 3", "Nivel 4"]
        
        for i, h in enumerate(headers):
            self.cell(w[i], 10, h, 1, 0, "C", True)
        self.ln()

        self.set_font("Arial", "", 7)
        for it in items:
            # Lógica para calcular altura de fila uniforme
            alturas = [self.get_nb_lines(w[1], it['descripcion']),
                       self.get_nb_lines(w[2], it['nivel_1']),
                       self.get_nb_lines(w[3], it['nivel_2']),
                       self.get_nb_lines(w[4], it['nivel_3']),
                       self.get_nb_lines(w[5], it['nivel_4'])]
            h_fila = max(alturas) * 4.5
            if h_fila < 8: h_fila = 8 # Mínimo de altura

            if self.get_y() + h_fila > 260:
                self.add_page()
            
            x, y = self.get_x(), self.get_y()
            
            # Celda Letra
            self.cell(w[0], h_fila, it['letra'], 1, 0, "C")
            
            # Celdas Multi-linea con control de posición
            textos = [it['descripcion'], it['nivel_1'], it['nivel_2'], it['nivel_3'], it['nivel_4']]
            cur_x = x + w[0]
            for i, txt in enumerate(textos):
                self.set_xy(cur_x, y)
                self.multi_cell(w[i+1], 4.5, str(txt), border=1, align='L')
                cur_x += w[i+1]
            
            self.set_xy(x, y + h_fila)

    def get_nb_lines(self, w, txt):
        # Función auxiliar para calcular líneas de texto
        return self.get_string_width(str(txt)) // w + 1

    def ficha_alumno_triple(self, nombre, puntos, x_offset, y_start):
        self.set_xy(x_offset, y_start)
        w_box = 55
        self.set_font("Arial", "B", 8)
        self.set_fill_color(245, 245, 245)
        nombre_f = nombre.split(" (")[0][:25]
        self.cell(w_box, 6, f" {nombre_f}", 1, 1, "L", True)
        
        y_int = self.get_y()
        for letra, nivel in puntos.items():
            self.set_xy(x_offset, y_int)
            self.set_font("Arial", "", 8)
            self.cell(10, 5, f"{letra}:", "L", 0) # Borde izquierdo
            
            for n in range(1, 5):
                self.set_font("Arial", "B" if n == int(nivel) else "", 8)
                txt = f"({n})" if n == int(nivel) else f" {n} "
                self.cell(10, 5, txt, 0, 0, "C")
            
            self.cell(0.1, 5, "", "R", 1) # Borde derecho
            y_int += 5
        self.line(x_offset, y_int, x_offset + w_box, y_int) # Línea inferior
        return y_int

# --- 3. TÍTULO APP ---
st.markdown("<h1 style='text-align: center; color: #2E5A88;'>🎓 Registro Docente</h1>", unsafe_allow_html=True)

tab_alu, tab_conf, tab_eval, tab_hist = st.tabs(["👥 Alumnos", "⚙️ Ítems", "📝 Evaluación", "📅 Histórico"])

# --- TAB 1: ALUMNOS ---
with tab_alu:
    res_alu = supabase.table("alumnos").select("*").order("nombre").execute()
    alumnos_db = res_alu.data
    
    col_sel, col_del = st.columns([3, 1])
    sel_alu = col_sel.selectbox("Seleccionar Alumno", ["+ Nuevo"] + [f"{a['nombre']} ({a['curso']})" for a in alumnos_db])
    
    v_id, v_nom, v_cur = 0, "", ""
    if sel_alu != "+ Nuevo":
        datos_a = next(a for a in alumnos_db if f"{a['nombre']} ({a['curso']})" == sel_alu)
        v_id, v_nom, v_cur = datos_a['id'], datos_a['nombre'], datos_a['curso']
        if col_del.button("🗑️ Eliminar Alumno", use_container_width=True):
            supabase.table("alumnos").delete().eq("id", v_id).execute()
            st.rerun()

    with st.form("f_alu"):
        c1, c2 = st.columns(2) # Campos más pequeños
        n_in = c1.text_input("Nombre completo", value=v_nom)
        c_in = c2.text_input("Curso", value=v_cur)
        if st.form_submit_button("Guardar Cambios"):
            if v_id == 0: supabase.table("alumnos").insert({"nombre": n_in, "curso": c_in}).execute()
            else: supabase.table("alumnos").update({"nombre": n_in, "curso": c_in}).eq("id", v_id).execute()
            st.rerun()

# --- TAB 2: ÍTEMS ---
with tab_conf:
    res_it = supabase.table("configuracion_items").select("*").order("letra").execute()
    items_db = res_it.data
    
    col_sel_i, col_del_i = st.columns([3, 1])
    sel_it = col_sel_i.selectbox("Seleccionar Ítem", ["+ Nuevo"] + [f"{it['letra']} - {it['descripcion'][:30]}..." for it in items_db])
    
    vi_id, vi_let, vi_des, vi_n1, vi_n2, vi_n3, vi_n4 = 0, "", "", "", "", "", ""
    if sel_it != "+ Nuevo":
        d = next(i for i in items_db if f"{i['letra']} - {i['descripcion'][:30]}..." == sel_it)
        vi_let, vi_des, vi_n1, vi_n2, vi_n3, vi_n4 = d['letra'], d['descripcion'], d['nivel_1'], d['nivel_2'], d['nivel_3'], d['nivel_4']
        if col_del_i.button("🗑️ Eliminar Ítem", use_container_width=True):
            supabase.table("configuracion_items").delete().eq("letra", vi_let).execute()
            st.rerun()

    with st.form("f_it"):
        c1, c2 = st.columns([1, 4])
        l_in = c1.text_input("Letra", value=vi_let, max_chars=2).upper()
        d_in = c2.text_input("Descripción", value=vi_des)
        col_a, col_b = st.columns(2)
        n1 = col_a.text_area("Nivel 1 (Insuficiente)", value=vi_n1, height=100)
        n2 = col_b.text_area("Nivel 2 (Suficiente)", value=vi_n2, height=100)
        n3 = col_a.text_area("Nivel 3 (Bien)", value=vi_n3, height=100)
        n4 = col_b.text_area("Nivel 4 (Excelente)", value=vi_n4, height=100)
        if st.form_submit_button("Guardar Ítem"):
            supabase.table("configuracion_items").upsert({"letra": l_in, "descripcion": d_in, "nivel_1": n1, "nivel_2": n2, "nivel_3": n3, "nivel_4": n4}).execute()
            st.rerun()

# --- TAB 3: EVALUACIÓN ---
with tab_eval:
    if not alumnos_db or not items_db:
        st.warning("Configura primero alumnos e ítems.")
    else:
        with st.form("f_ev"):
            c1, c2 = st.columns(2)
            al_sel = c1.selectbox("Alumno", [f"{a['nombre']} ({a['curso']})" for a in alumnos_db])
            f_sel = c2.date_input("Fecha", datetime.now())
            
            st.divider()
            res_eval = {}
            for it in items_db:
                st.write(f"**{it['letra']} - {it['descripcion']}**")
                res_eval[it['letra']] = st.radio(f"Resultado {it['letra']}", [1,2,3,4], 
                                               format_func=lambda x: f"Nivel {x}: {it[f'nivel_{x}']}", 
                                               key=f"r_{it['letra']}", horizontal=True)
            
            if st.form_submit_button("✅ Registrar Evaluación"):
                supabase.table("evaluaciones_alumnos").insert({"nombre_alumno": al_sel, "puntos": res_eval, "fecha": f_sel.isoformat()}).execute()
                st.success("¡Evaluación guardada!")

# --- TAB 4: HISTÓRICO ---
with tab_hist:
    evals = supabase.table("evaluaciones_alumnos").select("*").order("fecha", desc=True).execute().data
    if evals:
        df = pd.DataFrame(evals)
        df['fecha_dia'] = df['fecha'].apply(lambda x: x[:10])
        dias = df['fecha_dia'].unique()
        
        c1, c2 = st.columns([2,1])
        dia_pdf = c1.selectbox("Filtrar por día para PDF", ["Completo"] + list(dias))
        
        if c2.button("🖨️ Generar PDF", use_container_width=True):
            pdf = EvaluacionPDF()
            pdf.add_page()
            pdf.tabla_maestra(items_db)
            pdf.add_page()
            
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, f"REGISTROS: {dia_pdf}", ln=True)
            
            ev_print = evals if dia_pdf == "Completo" else [e for e in evals if e['fecha'][:10] == dia_pdf]
            columna, x_pos = 0, [10, 75, 140]
            y_fila_inicio = pdf.get_y()
            y_max_en_fila = y_fila_inicio

            for e in ev_print:
                if y_fila_inicio > 230:
                    pdf.add_page()
                    y_fila_inicio, y_max_en_fila = 20, 20

                y_fin = pdf.ficha_alumno_triple(e['nombre_alumno'], e['puntos'], x_pos[columna], y_fila_inicio)
                y_max_en_fila = max(y_max_en_fila, y_fin)

                if columna < 2:
                    columna += 1
                else:
                    columna = 0
                    y_fila_inicio = y_max_en_fila + 10
                    y_max_en_fila = y_fila_inicio

            st.download_button("📩 Descargar PDF", bytes(pdf.output()), f"Evaluacion_{dia_pdf}.pdf")
            
        # Lista para borrar registros individuales
        for d in dias:
            with st.expander(f"📅 Registros del {d}"):
                for _, r in df[df['fecha_dia'] == d].iterrows():
                    col_t, col_b = st.columns([4, 1])
                    col_t.write(f"👤 {r['nombre_alumno']}")
                    if col_b.button("Eliminar", key=f"del_ev_{r['id']}"):
                        supabase.table("evaluaciones_alumnos").delete().eq("id", r['id']).execute()
                        st.rerun()
    else:
        st.info("Sin registros.")