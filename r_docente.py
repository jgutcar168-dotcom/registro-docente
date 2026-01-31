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

# --- TÍTULO Y ESTILO ---
st.markdown("<h1 style='text-align: center; color: #2E5A88;'>🎓 Registro Docente - Aula P.T.</h1>", unsafe_allow_html=True)
# Aquí puedes cambiar el nombre de la maestra
st.markdown("<p style='text-align: center; font-family: \"Brush Script MT\", cursive; font-size: 35px; color: #5DADE2;'>Maestra Especialista: Ángela Ortíz Ordóñez</p>", unsafe_allow_html=True)
st.divider()

tab_alu, tab_conf, tab_eval, tab_hist = st.tabs([
    "👥 Alumnos", "⚙️ Configuración Ítems", "📝 Evaluación", "📅 Histórico"
])

# --- TAB: ALUMNOS (Carga y Edición automática) ---
with tab_alu:
    st.subheader("Registro y Gestión de Alumnos")
    
    # Obtener alumnos para el selector
    res_alu = supabase.table("alumnos").select("*").order("nombre").execute()
    alumnos_db = res_alu.data
    
    sel_alu_edit = st.selectbox(
        "🔍 Selecciona un alumno para modificarlo o elige 'Nuevo Alumno'",
        options=["+ Nuevo Alumno"] + [f"{a['nombre']} ({a['curso']})" for a in alumnos_db]
    )

    # Valores por defecto
    v_id, v_nom, v_cur = 0, "", ""

    if sel_alu_edit != "+ Nuevo Alumno":
        # Extraer nombre del string "Nombre (Curso)"
        nombre_extraido = sel_alu_edit.split(" (")[0]
        datos_a = next(a for a in alumnos_db if a['nombre'] == nombre_extraido)
        v_id, v_nom, v_cur = datos_a['id'], datos_a['nombre'], datos_a['curso']

    with st.form("form_alumnos_dinamico"):
        col_n, col_c = st.columns([3, 2])
        nom_in = col_n.text_input("Nombre del Alumno", value=v_nom)
        cur_in = col_c.text_input("Curso Escolar", value=v_cur, placeholder="Ej: 2024/25")
        
        btn_alu = st.form_submit_button("💾 Guardar Alumno")
        if btn_alu:
            if nom_in and cur_in:
                data_a = {"nombre": nom_in, "curso": cur_in}
                if v_id == 0:
                    supabase.table("alumnos").insert(data_a).execute()
                else:
                    supabase.table("alumnos").update(data_a).eq("id", v_id).execute()
                st.success(f"Alumno {nom_in} guardado.")
                st.rerun()

    if alumnos_db:
        with st.expander("🗑️ Zona de borrado de alumnos"):
            for a in alumnos_db:
                c1, c2 = st.columns([4, 1])
                c1.write(f"{a['nombre']} ({a['curso']})")
                if c2.button("Eliminar", key=f"del_a_{a['id']}"):
                    supabase.table("alumnos").delete().eq("id", a['id']).execute()
                    st.rerun()

# --- TAB: CONFIGURACIÓN ÍTEMS (Carga y Edición automática) ---
with tab_conf:
    st.subheader("Configuración de Ítems")
    
    res_items = supabase.table("configuracion_items").select("*").order("letra").execute()
    items_db = res_items.data
    
    sel_it_edit = st.selectbox(
        "🔍 Selecciona un ítem para modificar o elige 'Nuevo Ítem'",
        options=["+ Nuevo Ítem"] + [it['letra'] for it in items_db]
    )

    vi_let, vi_des, vi_n1, vi_n2, vi_n3, vi_n4 = "", "", "", "", "", ""

    if sel_it_edit != "+ Nuevo Ítem":
        d_it = next(it for it in items_db if it['letra'] == sel_it_edit)
        vi_let, vi_des, vi_n1, vi_n2, vi_n3, vi_n4 = d_it['letra'], d_it['descripcion'], d_it['nivel_1'], d_it['nivel_2'], d_it['nivel_3'], d_it['nivel_4']

    with st.form("form_items_dinamico"):
        c_let, c_des = st.columns([1, 4])
        let_in = c_let.text_input("Letra", value=vi_let, max_chars=2).upper()
        des_in = c_des.text_input("Descripción", value=vi_des)
        
        col1, col2 = st.columns(2)
        n1_in = col1.text_area("Nivel 1", value=vi_n1, height=100)
        n2_in = col2.text_area("Nivel 2", value=vi_n2, height=100)
        n3_in = col1.text_area("Nivel 3", value=vi_n3, height=100)
        n4_in = col2.text_area("Nivel 4", value=vi_n4, height=100)
        
        if st.form_submit_button("💾 Guardar Ítem"):
            d_save = {"letra": let_in, "descripcion": des_in, "nivel_1": n1_in, "nivel_2": n2_in, "nivel_3": n3_in, "nivel_4": n4_in}
            supabase.table("configuracion_items").upsert(d_save).execute()
            st.success(f"Ítem {let_in} actualizado.")
            st.rerun()

    if items_db:
        with st.expander("🗑️ Zona de borrado de ítems"):
            for it in items_db:
                c1, c2 = st.columns([4, 1])
                c1.write(f"Ítem {it['letra']}: {it['descripcion']}")
                if c2.button("Eliminar", key=f"del_it_{it['letra']}"):
                    supabase.table("configuracion_items").delete().eq("letra", it['letra']).execute()
                    st.rerun()

# --- TAB: EVALUACIÓN ---
with tab_eval:
    st.subheader("Nueva Evaluación")
    # Cargar lista fresca de alumnos e ítems
    alu_data = supabase.table("alumnos").select("*").order("nombre").execute().data
    item_data = supabase.table("configuracion_items").select("*").order("letra").execute().data
    
    if not alu_data or not item_data:
        st.warning("Asegúrate de tener alumnos e ítems registrados.")
    else:
        with st.form("form_eval"):
            nom_sel = st.selectbox("Alumno a evaluar", options=[f"{a['nombre']} ({a['curso']})" for a in alu_data])
            f_eval = st.date_input("Fecha", datetime.now())
            
            puntos = {}
            for r in item_data:
                st.markdown(f"#### 🔵 {r['letra']} - {r['descripcion']}")
                opcs = {1: r['nivel_1'], 2: r['nivel_2'], 3: r['nivel_3'], 4: r['nivel_4']}
                puntos[r['letra']] = st.radio(
                    f"Selección para {r['letra']}", options=[1, 2, 3, 4],
                    format_func=lambda x: f"{x}: {opcs[x]}", key=f"eval_radio_{r['letra']}"
                )
                st.divider()
            
            if st.form_submit_button("✅ Registrar Evaluación"):
                supabase.table("evaluaciones_alumnos").insert({
                    "nombre_alumno": nom_sel, "puntos": puntos, "fecha": f_eval.isoformat()
                }).execute()
                st.success("Evaluación guardada con éxito.")

# --- TAB 4: HISTÓRICO AGRUPADO Y PDF ---
with tab_hist:
    st.subheader("Histórico de Evaluaciones")
    evals = supabase.table("evaluaciones_alumnos").select("*").order("fecha", desc=True).execute().data
    items_ref = supabase.table("configuracion_items").select("*").order("letra").execute().data

    if evals:
        df_evals = pd.DataFrame(evals)
        df_evals['fecha_dia'] = df_evals['fecha'].apply(lambda x: x[:10])
        dias_disponibles = df_evals['fecha_dia'].unique()

        # Selector de PDF
        st.write("### 📄 Exportar a PDF")
        col_p1, col_p2 = st.columns([2, 1])
        dia_pdf = col_p1.selectbox("Seleccionar periodo:", ["Histórico Completo"] + list(dias_disponibles))
        
        if col_p2.button("Generar Informe"):
            pdf = EvaluacionPDF() # Ahora sí encontrará la clase arriba
            pdf.add_page()
            pdf.tabla_maestra(items_ref)
            
            evals_print = evals if dia_pdf == "Histórico Completo" else [e for e in evals if e['fecha'][:10] == dia_pdf]
            
            for ev in evals_print:
                pdf.ficha_alumno(ev['nombre_alumno'], ev['puntos'])
            
            st.download_button("⬇️ Descargar PDF", data=bytes(pdf.output()), file_name=f"Evaluacion_{dia_pdf}.pdf")

        st.divider()
        # Mostrar agrupado
        for dia in dias_disponibles:
            with st.expander(f"📅 Registros del día: {dia}"):
                alumnos_dia = df_evals[df_evals['fecha_dia'] == dia]
                for _, row in alumnos_dia.iterrows():
                    c1, c2 = st.columns([5, 1])
                    c1.write(f"👤 **{row['nombre_alumno']}**")
                    if c2.button("🗑️", key=f"del_{row['id']}"):
                        supabase.table("evaluaciones_alumnos").delete().eq("id", row['id']).execute()
                        st.rerun()
    else:
        st.info("No hay evaluaciones.")