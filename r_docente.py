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
st.title("🚀 Registro Docente P.T.")

tab1, tab2, tab3 = st.tabs(["⚙️ Configuración", "📝 Evaluar Alumno", "📊 Histórico y PDF"])

# --- TAB 1: CONFIGURACIÓN DE ITEMS ---
with tab1:
    st.subheader("Configuración de Ítems y Niveles")
    res = supabase.table("configuracion_items").select("*").order("letra").execute()
    df_config = pd.DataFrame(res.data)
    
    if df_config.empty:
        df_config = pd.DataFrame([{"letra": "A", "descripcion": "", "nivel_1": "", "nivel_2": "", "nivel_3": "", "nivel_4": ""}])

    # CONFIGURACIÓN DE COLUMNAS PARA VER TODO EL TEXTO
    configuracion_visual = {
        "letra": st.column_config.TextColumn("🆔 Ítem", width="small", help="Identificador único"),
        "descripcion": st.column_config.TextColumn("📝 Descripción del Ítem", width="large", help="Escribe aquí qué se evalúa"),
        "nivel_1": st.column_config.TextColumn("1️⃣ Nivel 1", width="medium"),
        "nivel_2": st.column_config.TextColumn("2️⃣ Nivel 2", width="medium"),
        "nivel_3": st.column_config.TextColumn("3️⃣ Nivel 3", width="medium"),
        "nivel_4": st.column_config.TextColumn("4️⃣ Nivel 4", width="medium"),
    }

    st.write("💡 *Puedes arrastrar el ancho de las columnas o hacer doble clic en ellas para leer textos largos.*")
    editado = st.data_editor(
        df_config, 
        num_rows="dynamic", 
        use_container_width=True,
        column_config=configuracion_visual
    )
    
    if st.button("Guardar Cambios en la Nube"):
        # Limpieza y guardado
        supabase.table("configuracion_items").delete().neq("letra", "Z_temp").execute()
        supabase.table("configuracion_items").insert(editado.to_dict(orient="records")).execute()
        st.success("¡Configuración actualizada!")
        st.rerun()

# --- TAB 2: EVALUACIÓN (Más visual y legible) ---
with tab2:
    if not df_config.empty:
        st.subheader("Registro de Evaluación")
        nombre = st.text_input("Nombre del Alumno")
        
        st.markdown("---")
        st.write("### Panel de Evaluación")
        
        resultados = {}
        for _, row in df_config.iterrows():
            # Usamos un contenedor con color para diferenciar el ítem
            with st.container():
                # Título del ítem con color (usando Markdown)
                st.markdown(f"#### 🔵 Ítem {row['letra']}: {row['descripcion']}")
                
                # Mostramos los niveles en 4 columnas para que se lea el texto de cada uno
                cols = st.columns(4)
                for i in range(1, 5):
                    texto_nivel = row[f'nivel_{i}']
                    with cols[i-1]:
                        # Si el usuario selecciona este nivel
                        if st.checkbox(f"Nivel {i}", key=f"{row['letra']}_{i}"):
                            resultados[row['letra']] = i
                        # Mostramos el texto del nivel debajo del check para que sea legible
                        st.caption(f"{texto_nivel}")
                st.markdown("---")
        
        if st.button("Registrar Evaluación"):
            if nombre and len(resultados) == len(df_config):
                supabase.table("evaluaciones_alumnos").insert({
                    "nombre_alumno": nombre,
                    "puntos": resultados
                }).execute()
                st.success(f"Evaluación de {nombre} guardada correctamente.")
            elif not nombre:
                st.error("Por favor, introduce el nombre del alumno.")
            else:
                st.warning("Asegúrate de haber marcado un nivel para cada ítem.")

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