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

# --- 2. CLASE PDF AVANZADA ---
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
        w = [8, 32, 37.5, 37.5, 37.5, 37.5] 
        titulos = ["L.", "Descripción", "Nivel 1", "Nivel 2", "Nivel 3", "Nivel 4"]
        
        for i, h in enumerate(titulos):
            self.cell(w[i], 8, h, 1, 0, "C", True)
        self.ln()

        self.set_font("Arial", "", 7)
        for it in items:
            textos = [it['letra'], it['descripcion'], it['nivel_1'], it['nivel_2'], it['nivel_3'], it['nivel_4']]
            
            # 1. Calcular la altura máxima necesaria para esta fila
            alturas = []
            for i, txt in enumerate(textos):
                # Calculamos cuántas líneas ocupará el texto en ese ancho
                lineas = self.get_nb_lines(w[i], str(txt))
                alturas.append(lineas * 4.5)
            h_fila = max(alturas)

            # Salto de página si no cabe
            if self.get_y() + h_fila > 270:
                self.add_page()

            # 2. Dibujar las celdas manualmente para que todas tengan la misma altura
            x_ini = self.get_x()
            y_ini = self.get_y()

            for i, txt in enumerate(textos):
                # Dibujamos el recuadro de la celda con la altura máxima
                self.rect(x_ini, y_ini, w[i], h_fila)
                # Escribimos el texto (multi_cell no pone borde aquí para no duplicar)
                self.set_xy(x_ini, y_ini)
                self.multi_cell(w[i], 4.5, str(txt), 0, 'L')
                x_ini += w[i]
            
            self.set_xy(self.l_margin, y_ini + h_fila)

    def get_nb_lines(self, w, txt):
        # Función para calcular líneas reales que ocupará el texto
        cw = self.current_font['cw']
        if w == 0: w = self.w - self.r_margin - self.x
        wmax = (w - 2 * self.c_margin) * 1000 / self.font_size_pt
        s = str(txt).replace("\r", '')
        nb = len(s)
        if nb > 0 and s[nb-1] == "\n": nb -= 1
        sep = -1
        i = j = l = nl = 0
        while i < nb:
            c = s[i]
            if c == "\n":
                i += 1
                sep = -1
                j = i
                l = 0
                nl += 1
                continue
            if c == ' ': sep = i
            l += cw[c]
            if l > wmax:
                if sep == -1:
                    if i == j: i += 1
                else:
                    i = sep + 1
                sep = -1
                j = i
                l = 0
                nl += 1
            else:
                i += 1
        return nl + 1

    def bloque_alumnos(self, lista_evaluaciones, y_start):
        self.set_xy(10, y_start)
        self.set_font("Arial", "B", 10)
        self.set_fill_color(200, 220, 255)
        self.cell(190, 8, "EVALUACIÓN DEL ALUMNADO (REGISTROS SELECCIONADOS)", 1, 1, "C", True)
        
        y_cuerpo = self.get_y()
        max_y_alcanzado = y_cuerpo
        
        ancho_col = 63.3 # 190 / 3 columnas
        
        for i, e in enumerate(lista_evaluaciones):
            col = i % 3
            if col == 0 and i > 0:
                y_cuerpo = max_y_alcanzado + 5
                if y_cuerpo > 250:
                    self.add_page()
                    y_cuerpo = 20
            
            x_pos = 10 + (col * ancho_col)
            
            # Nombre Alumno
            self.set_xy(x_pos, y_cuerpo)
            self.set_font("Arial", "B", 8)
            nombre = e['nombre_alumno'].split(" (")[0][:25]
            self.cell(ancho_col, 6, nombre, "LRB", 1, "C")
            
            curr_y = self.get_y()
            for letra, nivel in e['puntos'].items():
                self.set_xy(x_pos, curr_y)
                self.set_font("Arial", "", 8)
                self.cell(8, 5, f"{letra}:", "L", 0) # Borde izquierdo
                
                # Pintar niveles
                for n in range(1, 5):
                    if n == int(nivel):
                        # Dibujar círculo de sombreado
                        self.set_fill_color(200, 200, 200)
                        self.ellipse(self.get_x()+1, self.get_y()+0.5, 4, 4, 'F')
                        self.set_font("Arial", "B", 8)
                    else:
                        self.set_font("Arial", "", 8)
                    
                    self.cell(11.3, 5, str(n), 0, 0, "C")
                
                self.cell(0.1, 5, "", "R", 1) # Borde derecho
                curr_y += 5
            
            # Línea de cierre del alumno
            self.line(x_pos, curr_y, x_pos + ancho_col, curr_y)
            max_y_alcanzado = max(max_y_alcanzado, curr_y)
            
        return max_y_alcanzado

# --- 3. INTERFAZ DE STREAMLIT (SECCIONES MEJORADAS) ---
st.markdown("<h1 style='text-align: center; color: #2E5A88;'>🎓 Gestión PT: Ángela Ortiz</h1>", unsafe_allow_html=True)

tab_alu, tab_conf, tab_eval, tab_hist = st.tabs(["👥 Alumnos", "⚙️ Ítems", "📝 Evaluación", "📅 Histórico"])

# --- TAB 1: ALUMNOS (CAMPOS PEQUEÑOS Y ELIMINAR) ---
with tab_alu:
    res_alu = supabase.table("alumnos").select("*").order("nombre").execute()
    alumnos_db = res_alu.data
    
    col1, col2 = st.columns([3, 1])
    sel_alu = col1.selectbox("Seleccionar Alumno", ["+ Nuevo"] + [f"{a['nombre']} ({a['curso']})" for a in alumnos_db])
    
    v_id, v_nom, v_cur = 0, "", ""
    if sel_alu != "+ Nuevo":
        datos = next(a for a in alumnos_db if f"{a['nombre']} ({a['curso']})" == sel_alu)
        v_id, v_nom, v_cur = datos['id'], datos['nombre'], datos['curso']
        if col2.button("🗑️ Eliminar Alumno", use_container_width=True):
            supabase.table("alumnos").delete().eq("id", v_id).execute()
            st.rerun()

    with st.form("form_alumno"):
        c1, c2 = st.columns(2)
        n_in = c1.text_input("Nombre y Apellidos", value=v_nom)
        c_in = c2.text_input("Etapa/Curso", value=v_cur)
        if st.form_submit_button("💾 Guardar Datos"):
            if v_id == 0: supabase.table("alumnos").insert({"nombre": n_in, "curso": c_in}).execute()
            else: supabase.table("alumnos").update({"nombre": n_in, "curso": c_in}).eq("id", v_id).execute()
            st.rerun()

# --- TAB 2: ÍTEMS (CAMPOS PEQUEÑOS Y ELIMINAR) ---
with tab_conf:
    res_it = supabase.table("configuracion_items").select("*").order("letra").execute()
    items_db = res_it.data
    
    col1, col2 = st.columns([3, 1])
    sel_it = col1.selectbox("Seleccionar Ítem", ["+ Nuevo"] + [f"{i['letra']} - {i['descripcion'][:40]}" for i in items_db])
    
    vi_let, vi_des, vi_n1, vi_n2, vi_n3, vi_n4 = "", "", "", "", "", ""
    if sel_it != "+ Nuevo":
        d = next(i for i in items_db if f"{i['letra']} - {i['descripcion'][:40]}" == sel_it)
        vi_let, vi_des, vi_n1, vi_n2, vi_n3, vi_n4 = d['letra'], d['descripcion'], d['nivel_1'], d['nivel_2'], d['nivel_3'], d['nivel_4']
        if col2.button("🗑️ Eliminar Ítem", use_container_width=True):
            supabase.table("configuracion_items").delete().eq("letra", vi_let).execute()
            st.rerun()

    with st.form("form_item"):
        c1, c2 = st.columns([1, 4])
        l_in = c1.text_input("Letra", value=vi_let, max_chars=2).upper()
        d_in = c2.text_input("Concepto/Descripción", value=vi_des)
        
        st.write("#### Definición de Niveles")
        ca, cb = st.columns(2)
        n1 = ca.text_area("Nivel 1", value=vi_n1, height=80)
        n2 = cb.text_area("Nivel 2", value=vi_n2, height=80)
        n3 = ca.text_area("Nivel 3", value=vi_n3, height=80)
        n4 = cb.text_area("Nivel 4", value=vi_n4, height=80)
        
        if st.form_submit_button("💾 Actualizar Ítem"):
            supabase.table("configuracion_items").upsert({"letra": l_in, "descripcion": d_in, "nivel_1": n1, "nivel_2": n2, "nivel_3": n3, "nivel_4": n4}).execute()
            st.rerun()

# --- TAB 3: EVALUACIÓN ---
with tab_eval:
    if not alumnos_db: st.error("No hay alumnos creados.")
    else:
        with st.form("f_eval"):
            c1, c2 = st.columns(2)
            al_sel = c1.selectbox("Alumno a evaluar", [f"{a['nombre']} ({a['curso']})" for a in alumnos_db])
            f_sel = c2.date_input("Fecha de registro", datetime.now())
            
            st.divider()
            res_puntos = {}
            for it in items_db:
                st.write(f"**{it['letra']} - {it['descripcion']}**")
                res_puntos[it['letra']] = st.radio(f"Seleccion {it['letra']}", [1,2,3,4], 
                                                format_func=lambda x: f"Nivel {x}: {it[f'nivel_{x}']}", 
                                                key=f"eval_{it['letra']}", horizontal=True)
            
            if st.form_submit_button("🚀 Registrar Evaluación"):
                supabase.table("evaluaciones_alumnos").insert({"nombre_alumno": al_sel, "puntos": res_puntos, "fecha": f_sel.isoformat()}).execute()
                st.success("¡Registro completado!")

# --- TAB 4: HISTÓRICO Y PDF ---
with tab_hist:
    evals = supabase.table("evaluaciones_alumnos").select("*").order("fecha", desc=True).execute().data
    if evals:
        df = pd.DataFrame(evals)
        df['fecha_dia'] = df['fecha'].apply(lambda x: x[:10])
        dias = df['fecha_dia'].unique()
        
        c1, c2 = st.columns([2,1])
        dia_pdf = c1.selectbox("Generar Informe del día", ["Todos los registros"] + list(dias))
        
        if c2.button("📑 Generar Informe Profesional", use_container_width=True):
            pdf = EvaluacionPDF()
            pdf.alias_nb_pages()
            pdf.add_page()
            
            # 1. Tabla Maestra
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 10, "1. RÚBRICA DE EVALUACIÓN", ln=True)
            pdf.tabla_maestra(items_db)
            
            # 2. Registros de alumnos
            pdf.add_page()
            ev_print = evals if dia_pdf == "Todos los registros" else [e for e in evals if e['fecha'][:10] == dia_pdf]
            pdf.bloque_alumnos(ev_print, pdf.get_y())
            
            st.download_button("⬇️ Descargar PDF", bytes(pdf.output()), f"Informe_{dia_pdf}.pdf")

        for d in dias:
            with st.expander(f"📅 Registros del día {d}"):
                for _, r in df[df['fecha_dia'] == d].iterrows():
                    col_t, col_b = st.columns([5, 1])
                    col_t.write(f"**{r['nombre_alumno']}**")
                    if col_b.button("🗑️", key=f"del_h_{r['id']}"):
                        supabase.table("evaluaciones_alumnos").delete().eq("id", r['id']).execute()
                        st.rerun()