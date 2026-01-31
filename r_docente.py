import streamlit as st
import pandas as pd
from fpdf import FPDF
from supabase import create_client

# --- CONEXIÓN ---
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_connection()

# --- CLASE PDF ---
class EvaluacionPDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 15)
        self.cell(0, 10, "INFORME DE EVALUACIÓN CONTINUA", ln=True, align="C")
        self.ln(5)

    def tabla_referencia(self, df_config):
        self.set_font("Arial", "B", 10)
        self.set_fill_color(230, 230, 230)
        self.cell(10, 8, "It.", 1, 0, "C", True)
        self.cell(180, 8, "Descripción de Niveles", 1, 1, "C", True)
        
        self.set_font("Arial", "", 8)
        for _, r in df_config.iterrows():
            # Fila de descripción
            self.set_font("Arial", "B", 8)
            self.cell(10, 6, r['letra'], 1, 0, "C")
            self.cell(180, 6, f"Item: {r['descripcion']}", 1, 1, "L", True)
            # Fila de niveles
            self.set_font("Arial", "", 7)
            self.cell(10, 6, "", 1)
            for i in range(1, 5):
                txt = f"N{i}: {r[f'nivel_{i}']}"
                self.cell(45, 6, txt[:30], 1)
            self.ln()
        self.ln(10)

# --- APP ---
st.title("🚀 Sistema de Evaluación con Supabase")

tab1, tab2, tab3 = st.tabs(["⚙️ Configuración", "📝 Evaluar Alumno", "📊 Histórico y PDF"])

# --- TAB 1: GESTIÓN DE ITEMS ---
with tab1:
    st.subheader("Configuración de Ítems y Niveles")
    res = supabase.table("configuracion_items").select("*").order("letra").execute()
    df_config = pd.DataFrame(res.data)
    
    if df_config.empty:
        df_config = pd.DataFrame([{"letra": "A", "descripcion": "", "nivel_1": "", "nivel_2": "", "nivel_3": "", "nivel_4": ""}])

    editado = st.data_editor(df_config, num_rows="dynamic", use_container_width=True)
    
    if st.button("Guardar Cambios en la Nube"):
        # Limpieza simple para el ejemplo
        supabase.table("configuracion_items").delete().neq("letra", "Z_temp").execute()
        supabase.table("configuracion_items").insert(editado.to_dict(orient="records")).execute()
        st.success("¡Configuración actualizada!")
        st.rerun()

# --- TAB 2: EVALUACIÓN ---
with tab2:
    if not df_config.empty:
        with st.form("eval_form"):
            nombre = st.text_input("Nombre del Alumno")
            st.write("Selecciona el nivel (1-4):")
            
            resultados = {}
            # Presentamos una fila por ítem
            for _, row in df_config.iterrows():
                col1, col2 = st.columns([1, 3])
                col1.write(f"**Item {row['letra']}**")
                resultados[row['letra']] = col2.radio(
                    f"Nivel para {row['descripcion']}", 
                    options=[1, 2, 3, 4], 
                    horizontal=True, 
                    label_visibility="collapsed"
                )
            
            if st.form_submit_button("Registrar Evaluación"):
                if nombre:
                    supabase.table("evaluaciones_alumnos").insert({
                        "nombre_alumno": nombre,
                        "puntos": resultados
                    }).execute()
                    st.success(f"Evaluación de {nombre} guardada.")
                else:
                    st.error("Falta el nombre.")

# --- TAB 3: PDF ---
with tab3:
    evals = supabase.table("evaluaciones_alumnos").select("*").order("fecha").execute().data
    
    if evals:
        st.write(f"Hay {len(evals)} registros.")
        if st.button("Generar PDF"):
            pdf = EvaluacionPDF()
            pdf.add_page()
            
            # 1. Tabla Estándar
            pdf.tabla_referencia(df_config)
            
            # 2. Listado de Alumnos
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, "RESULTADOS INDIVIDUALES", ln=True)
            pdf.ln(5)

            for ev in evals:
                pdf.set_font("Arial", "B", 11)
                pdf.cell(50, 10, f"Alumno: {ev['nombre_alumno']}", ln=0)
                pdf.set_font("Arial", "", 10)
                
                # Dibujar items seguidos
                for letra, nivel_sel in ev['puntos'].items():
                    pdf.cell(15, 10, f"{letra}:", ln=0, align="R")
                    for n in range(1, 5):
                        if n == nivel_sel:
                            # Círculo sombreado
                            pdf.set_fill_color(200, 200, 200)
                            pdf.ellipse(pdf.get_x()+1, pdf.get_y()+2, 6, 6, 'F')
                            pdf.set_font("Arial", "B", 10)
                            pdf.cell(8, 10, str(n), align="C")
                        else:
                            pdf.set_font("Arial", "", 10)
                            pdf.cell(8, 10, str(n), align="C")
                pdf.ln(10)

            st.download_button("Descargar PDF", data=bytes(pdf.output()), file_name="evaluaciones.pdf")