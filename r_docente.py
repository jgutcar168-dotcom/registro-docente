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

# --- APP ---
st.title("🎓 Gestión de Evaluación Docente")

tab_alu, tab_conf, tab_eval, tab_hist = st.tabs([
    "👥 Alumnos", "⚙️ Configuración Ítems", "📝 Evaluación", "📅 Histórico"
])

# --- TAB: ALUMNOS (Registro, Edición y Borrado) ---
with tab_alu:
    st.subheader("Registro de Alumnos")
    with st.expander("➕ Registrar / Editar Alumno", expanded=True):
        with st.form("form_alumno"):
            id_alu = st.number_input("ID (Dejar en 0 para nuevo)", value=0, help="Si pones el ID de un alumno existente, se actualizarán sus datos.")
            nombre_alu = st.text_input("Nombre completo")
            curso_alu = st.text_input("Curso Escolar (ej. 2025/26)")
            if st.form_submit_button("Guardar Alumno"):
                data = {"nombre": nombre_alu, "curso": curso_alu}
                if id_alu == 0:
                    supabase.table("alumnos").insert(data).execute()
                else:
                    supabase.table("alumnos").update(data).eq("id", id_alu).execute()
                st.success("Alumno procesado.")
                st.rerun()

    st.write("### Lista de Alumnos")
    res_alu = supabase.table("alumnos").select("*").order("nombre").execute()
    for a in res_alu.data:
        col1, col2, col3 = st.columns([3, 1, 1])
        col1.write(f"**{a['nombre']}** - {a['curso']} (ID: {a['id']})")
        # El botón de editar solo rellena el ID arriba para simplificar
        if col2.button("✏️ Editar", key=f"edit_a_{a['id']}"):
            st.info(f"Copia el ID **{a['id']}** en el formulario superior para editar.")
        if col3.button("🗑️", key=f"del_a_{a['id']}"):
            supabase.table("alumnos").delete().eq("id", a['id']).execute()
            st.rerun()

# --- TAB: CONFIGURACIÓN ÍTEMS (Con Edición) ---
with tab_conf:
    st.subheader("Configuración de Ítems")
    # Formulario de entrada/edición
    with st.expander("🛠️ Crear o Modificar Ítem", expanded=True):
        letra_ed = st.text_input("Letra del Ítem (Ej: A)", max_chars=2).upper()
        desc_ed = st.text_input("Descripción")
        c1, c2 = st.columns(2)
        txt_n1 = c1.text_area("Nivel 1", height=70)
        txt_n2 = c2.text_area("Nivel 2", height=70)
        txt_n3 = c1.text_area("Nivel 3", height=70)
        txt_n4 = c2.text_area("Nivel 4", height=70)
        
        if st.button("💾 Guardar Ítem"):
            d_item = {
                "letra": letra_ed, "descripcion": desc_ed,
                "nivel_1": txt_n1, "nivel_2": txt_n2, "nivel_3": txt_n3, "nivel_4": txt_n4
            }
            supabase.table("configuracion_items").upsert(d_item).execute()
            st.success(f"Ítem {letra_ed} guardado/actualizado.")
            st.rerun()

    # Listado para ver y borrar
    res_items = supabase.table("configuracion_items").select("*").order("letra").execute()
    for it in res_items.data:
        with st.expander(f"Ítem {it['letra']}: {it['descripcion']}"):
            st.write(f"**Nivel 1:** {it['nivel_1']}\n\n**Nivel 2:** {it['nivel_2']}\n\n**Nivel 3:** {it['nivel_3']}\n\n**Nivel 4:** {it['nivel_4']}")
            if st.button(f"🗑️ Eliminar {it['letra']}", key=f"del_it_{it['letra']}"):
                supabase.table("configuracion_items").delete().eq("letra", it['letra']).execute()
                st.rerun()

# --- TAB: EVALUACIÓN (Con Desplegable de Alumnos) ---
with tab_eval:
    st.subheader("Nueva Evaluación")
    # Obtenemos alumnos para el desplegable
    lista_alumnos = supabase.table("alumnos").select("*").order("nombre").execute().data
    opciones_alumnos = {a['id']: f"{a['nombre']} ({a['curso']})" for a in lista_alumnos}
    
    if not lista_alumnos:
        st.warning("No hay alumnos registrados. Ve a la pestaña de Alumnos.")
    elif not res_items.data:
        st.warning("No hay ítems configurados.")
    else:
        with st.form("eval_form"):
            id_alu_sel = st.selectbox("Selecciona Alumno", options=opciones_alumnos.keys(), format_func=lambda x: opciones_alumnos[x])
            fecha_sel = st.date_input("Fecha", datetime.now())
            
            puntos_eval = {}
            for row in res_items.data:
                st.markdown(f"#### 🔵 Ítem {row['letra']}")
                st.caption(row['descripcion'])
                # Mostramos texto completo en el radio
                opcs = {1: row['nivel_1'], 2: row['nivel_2'], 3: row['nivel_3'], 4: row['nivel_4']}
                puntos_eval[row['letra']] = st.radio(
                    f"Nivel para {row['letra']}", options=[1, 2, 3, 4],
                    format_func=lambda x: f"{x}: {opcs[x]}", key=f"ev_rad_{row['letra']}"
                )
            
            if st.form_submit_button("Guardar Evaluación"):
                nombre_final = opciones_alumnos[id_alu_sel]
                supabase.table("evaluaciones_alumnos").insert({
                    "nombre_alumno": nombre_final,
                    "puntos": puntos_eval,
                    "fecha": fecha_sel.isoformat()
                }).execute()
                st.success("Evaluación guardada.")

# --- TAB: HISTÓRICO ---
with tab_hist:
    evals = supabase.table("evaluaciones_alumnos").select("*").order("fecha", desc=True).execute().data
    if evals:
        for e in evals:
            with st.container(border=True):
                c1, c2 = st.columns([4, 1])
                c1.write(f"**{e['nombre_alumno']}** - {e['fecha']}")
                if c2.button("🗑️", key=f"del_hist_{e['id']}"):
                    supabase.table("evaluaciones_alumnos").delete().eq("id", e['id']).execute()
                    st.rerun()