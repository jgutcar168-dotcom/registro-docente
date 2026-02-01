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

# --- 2. CLASE PDF OPTIMIZADA ---
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
        # Ajuste fino del ancho para evitar saltos innecesarios
        ancho_util = w - 1.5 
        # Cálculo basado en el ancho real del texto para evitar palabras huérfanas
        w_texto = self.get_string_width(str(txt))
        return max(1, int(w_texto / ancho_util) + (1 if (w_texto % ancho_util) > 0.5 else 0))

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
            h_fila = max(n_lineas) * 4.2 
            if h_fila < 8: h_fila = 8

            if self.get_y() + h_fila > 270:
                self.add_page()
                self.set_font("Arial", "B", 8)
                for i, h in enumerate(headers): self.cell(w[i], 8, h, 1, 0, "C", True)
                self.ln()
                self.set_font("Arial", "", 7)

            x_ini, y_ini = self.get_x(), self.get_y()
            for i, t in enumerate(textos):
                self.rect(x_ini, y_ini, w[i], h_fila)
                self.set_xy(x_ini, y_ini)
                self.multi_cell(w[i], 4, str(t), 0, 'L')
                x_ini += w[i]
            self.set_xy(10, y_ini + h_fila)

    def bloque_alumnos(self, evaluaciones):
        if not evaluaciones: return
        self.ln(5)
        self.set_font("Arial", "B", 10)
        self.set_fill_color(240, 240, 240)
        self.cell(190, 8, "EVALUACIÓN POR ALUMNO", 1, 1, "C", True)
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
            self.set_font("Arial", "B", 8)
            nombre = e['nombre_alumno'].split(" (")[0][:22]
            self.cell(w_col, 7, f" {nombre}", 1, 1, "L", True)
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
            max_y_fila = max(max_y_fila, y_item)
            if (i+1) % 3 != 0: self.set_y(y_fila)

# --- 3. INTERFAZ STREAMLIT ---
tab_alu, tab_conf, tab_eval, tab_hist = st.tabs(["👥 Alumnos", "⚙️ Ítems", "📝 Evaluación", "📅 Histórico"])

# --- TAB ALUMNOS E ÍTEMS ---
# (Se asumen cargados de Supabase res_a y res_i)
res_a = supabase.table("alumnos").select("*").execute().data
res_i = supabase.table("configuracion_items").select("*").order("letra").execute().data

# --- LÓGICA DE EVALUACIÓN (CON MARCAS ✅) ---
with tab_eval:
    if not res_a:
        st.warning("Crea alumnos primero.")
    else:
        c1, c2 = st.columns(2)
        fe_ev = c2.date_input("Fecha de hoy", datetime.now())
        
        # Consultar quiénes ya están evaluados en esta fecha
        evals_ya_hechas = supabase.table("evaluaciones_alumnos").select("nombre_alumno").eq("fecha", fe_ev.isoformat()).execute().data
        set_evaluados = {ev['nombre_alumno'] for ev in evals_ya_hechas}
        
        # Clasificar alumnos
        pendientes = []
        completados = []
        for a in res_a:
            nombre_full = f"{a['nombre']} ({a['curso']})"
            if nombre_full in set_evaluados:
                completados.append(f"✅ {nombre_full}")
            else:
                pendientes.append(nombre_full)
        
        # Desplegable inteligente
        al_ev_display = c1.selectbox("Seleccionar Alumno", pendientes + completados)
        ya_esta_hecho = al_ev_display.startswith("✅")

        if ya_esta_hecho:
            st.error(f"El alumno **{al_ev_display[2:]}** ya tiene una evaluación registrada para este día.")
            st.info("Si necesitas corregirla, elimínala primero en la pestaña 'Histórico'.")
        
        with st.form("f_registro", clear_on_submit=True):
            pts = {}
            for it in res_i:
                st.write(f"**{it['letra']} - {it['descripcion']}**")
                pts[it['letra']] = st.radio(f"Nivel {it['letra']}", [1, 2, 3, 4], 
                                            format_func=lambda x, it=it: f"N{x}: {it[f'nivel_{x}']}", 
                                            key=f"ev_{it['letra']}", horizontal=True)
            
            # Botón deshabilitado si ya está evaluado
            btn_save = st.form_submit_button("Guardar Evaluación", disabled=ya_esta_hecho)
            
            if btn_save:
                supabase.table("evaluaciones_alumnos").insert({
                    "nombre_alumno": al_ev_display,
                    "puntos": pts,
                    "fecha": fe_ev.isoformat()
                }).execute()
                st.success(f"Evaluación de {al_ev_display} guardada.")
                st.rerun()

# --- TAB HISTÓRICO ---
with tab_hist:
    evals = supabase.table("evaluaciones_alumnos").select("*").order("fecha", desc=True).execute().data
    if evals:
        df_ev = pd.DataFrame(evals)
        df_ev['fecha_corta'] = df_ev['fecha'].map(lambda x: x[:10])
        dias = df_ev['fecha_corta'].unique()
        
        col_d, col_p = st.columns([3, 1])
        sel_dia = col_d.selectbox("Día", ["Ver todos"] + list(dias))
        
        if col_p.button("🖨️ Crear PDF"):
            pdf = EvaluacionPDF()
            pdf.tabla_maestra(res_i)
            pdf.add_page()
            ev_final = evals if sel_dia == "Ver todos" else [e for e in evals if e['fecha'][:10] == sel_dia]
            pdf.bloque_alumnos(ev_final)
            st.download_button("Descargar Informe", bytes(pdf.output()), f"Informe_{sel_dia}.pdf")

        for d in dias:
            with st.expander(f"📅 Registros del {d}"):
                regs = df_ev[df_ev['fecha_corta'] == d]
                for _, r in regs.iterrows():
                    c1, c2 = st.columns([5, 1])
                    c1.write(f"👤 {r['nombre_alumno']}")
                    if c2.button("🗑️", key=f"del_{r['id']}"):
                        supabase.table("evaluaciones_alumnos").delete().eq("id", r['id']).execute()
                        st.rerun()