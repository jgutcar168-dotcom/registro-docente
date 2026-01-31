import streamlit as st
import pandas as pd
from fpdf import FPDF
from supabase import create_client
from datetime import datetime

# --- CONEXIÓN ---
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_connection()

# --- FUNCIONES DE APOYO ---
def format_fecha(iso_string):
    dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
    return dt.strftime("%d/%m/%Y %H:%M")

# --- APP ---
st.title("🚀 Gestión Docente Avanzada")

tab1, tab2, tab3 = st.tabs(["⚙️ Configuración Ítems", "📝 Evaluación", "📅 Histórico y Gestión"])

# --- TAB 1: CONFIGURACIÓN (SIN CORTES DE TEXTO) ---
with tab1:
    st.subheader("Configuración de Ítems")
    res = supabase.table("configuracion_items").select("*").order("letra").execute()
    items_actuales = res.data
    
    with st.expander("➕ Añadir Nuevo Ítem / Editar Existentes", expanded=True):
        col_id, col_desc = st.columns([1, 4])
        letra_input = col_id.text_input("Letra/ID", placeholder="A")
        desc_input = col_desc.text_input("Descripción del Ítem", placeholder="Ej: Comprensión Lectora")
        
        c1, c2 = st.columns(2)
        n1 = c1.text_area("Texto Nivel 1", height=100)
        n2 = c2.text_area("Texto Nivel 2", height=100)
        n3 = c1.text_area("Texto Nivel 3", height=100)
        n4 = c2.text_area("Texto Nivel 4", height=100)
        
        if st.button("💾 Guardar/Actualizar Ítem"):
            data = {
                "letra": letra_input.upper(),
                "descripcion": desc_input,
                "nivel_1": n1, "nivel_2": n2, "nivel_3": n3, "nivel_4": n4
            }
            supabase.table("configuracion_items").upsert(data).execute()
            st.success(f"Ítem {letra_input} guardado.")
            st.rerun()

    if items_actuales:
        st.write("### Ítems Registrados")
        for it in items_actuales:
            with st.expander(f"Ítem {it['letra']}: {it['descripcion']}"):
                st.write(f"**1:** {it['nivel_1']}")
                st.write(f"**2:** {it['nivel_2']}")
                st.write(f"**3:** {it['nivel_3']}")
                st.write(f"**4:** {it['nivel_4']}")
                if st.button(f"🗑️ Eliminar Ítem {it['letra']}", key=f"del_{it['letra']}"):
                    supabase.table("configuracion_items").delete().eq("letra", it['letra']).execute()
                    st.rerun()

# --- TAB 2: EVALUACIÓN ---
with tab2:
    res_config = supabase.table("configuracion_items").select("*").order("letra").execute()
    if res_config.data:
        with st.form("eval_form"):
            nombre = st.text_input("Nombre del Alumno")
            fecha_eval = st.date_input("Fecha de evaluación", datetime.now())
            
            puntos = {}
            for row in res_config.data:
                st.markdown(f"#### 🔵 {row['letra']} - {row['descripcion']}")
                # Usamos radio pero con los textos completos para que se vea TODO
                opciones = {
                    1: f"1: {row['nivel_1']}",
                    2: f"2: {row['nivel_2']}",
                    3: f"3: {row['nivel_3']}",
                    4: f"4: {row['nivel_4']}"
                }
                puntos[row['letra']] = st.radio(
                    f"Selecciona nivel para {row['letra']}",
                    options=[1, 2, 3, 4],
                    format_func=lambda x: opciones[x],
                    key=f"eval_{row['letra']}"
                )
                st.divider()
            
            if st.form_submit_button("Registrar"):
                supabase.table("evaluaciones_alumnos").insert({
                    "nombre_alumno": nombre,
                    "puntos": puntos,
                    "fecha": fecha_eval.isoformat()
                }).execute()
                st.success("Registro guardado.")
    else:
        st.warning("Configura los ítems primero.")

# --- TAB 3: HISTÓRICO, EDITAR Y BORRAR ---
with tab3:
    evals = supabase.table("evaluaciones_alumnos").select("*").order("fecha", desc=True).execute().data
    
    if evals:
        for e in evals:
            with st.container(border=True):
                col1, col2, col3 = st.columns([3, 1, 1])
                col1.write(f"**{e['nombre_alumno']}** ({format_fecha(e['fecha'])})")
                
                # Botón de borrar
                if col3.button("🗑️ Borrar", key=f"del_ev_{e['id']}"):
                    supabase.table("evaluaciones_alumnos").delete().eq("id", e['id']).execute()
                    st.rerun()
                
                # Botón de editar (abre un editor rápido)
                with col2.popover("✏️ Editar"):
                    nuevo_nombre = st.text_input("Nombre", value=e['nombre_alumno'], key=f"edit_n_{e['id']}")
                    st.write("Puntos actuales:", e['puntos'])
                    if st.button("Guardar cambios", key=f"save_ed_{e['id']}"):
                        supabase.table("evaluaciones_alumnos").update({"nombre_alumno": nuevo_nombre}).eq("id", e['id']).execute()
                        st.success("Actualizado")
                        st.rerun()
        
        # # --- BOTÓN PDF (Igual al anterior) ---
        # # ... (Aquí iría el código del PDF que ya tenemos)
# # --- TAB 3: PDF ---
# with tab3:
    # evals = supabase.table("evaluaciones_alumnos").select("*").order("fecha").execute().data
    
    # if evals:
        # st.write(f"Hay {len(evals)} registros.")
        # if st.button("Generar PDF"):
            # pdf = EvaluacionPDF()
            # pdf.add_page()
            
            # # 1. Tabla Estándar
            # pdf.tabla_referencia(df_config)
            
            # # 2. Listado de Alumnos
            # pdf.set_font("Arial", "B", 12)
            # pdf.cell(0, 10, "RESULTADOS INDIVIDUALES", ln=True)
            # pdf.ln(5)

            # for ev in evals:
                # pdf.set_font("Arial", "B", 11)
                # pdf.cell(50, 10, f"Alumno: {ev['nombre_alumno']}", ln=0)
                # pdf.set_font("Arial", "", 10)
                
                # # Dibujar items seguidos
                # for letra, nivel_sel in ev['puntos'].items():
                    # pdf.cell(15, 10, f"{letra}:", ln=0, align="R")
                    # for n in range(1, 5):
                        # if n == nivel_sel:
                            # # Círculo sombreado
                            # pdf.set_fill_color(200, 200, 200)
                            # pdf.ellipse(pdf.get_x()+1, pdf.get_y()+2, 6, 6, 'F')
                            # pdf.set_font("Arial", "B", 10)
                            # pdf.cell(8, 10, str(n), align="C")
                        # else:
                            # pdf.set_font("Arial", "", 10)
                            # pdf.cell(8, 10, str(n), align="C")
                # pdf.ln(10)

            # st.download_button("Descargar PDF", data=bytes(pdf.output()), file_name="evaluaciones.pdf")