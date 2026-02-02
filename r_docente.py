import streamlit as st
import pandas as pd
from fpdf import FPDF
from supabase import create_client
from datetime import datetime

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Suite Docente | Ángela Ortiz", layout="wide")

@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_connection()

# --- 2. CLASES PDF ---
class EvaluacionPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)
        self.add_page()

    def header(self):
        self.set_font("Arial", "B", 14)
        self.cell(0, 10, "INFORME DE EVALUACIÓN DOCENTE", ln=True, align="C")
        self.set_font("Arial", "I", 10)
        self.set_text_color(255, 110, 64) 
        self.cell(0, 5, "Especialista: Ángela Ortiz Ordóñez", ln=True, align="C")
        self.set_text_color(0, 0, 0)
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Página {self.page_no()}/{{nb}}", align="C")

    def tabla_maestra(self, items):
        if not items: return
        self.set_font("Arial", "B", 8)
        self.set_fill_color(230, 230, 230)
        w = [10, 35, 36.25, 36.25, 36.25, 36.25] 
        headers = ["L.", "Descripción", "Nivel 1", "Nivel 2", "Nivel 3", "Nivel 4"]
        for i, h in enumerate(headers): self.cell(w[i], 8, h, 1, 0, "C", True)
        self.ln()
        self.set_font("Arial", "", 7)
        for it in items:
            textos = [
                str(it.get('letra', '')), 
                str(it.get('descripcion', '')), 
                str(it.get('nivel_1') or ""), 
                str(it.get('nivel_2') or ""), 
                str(it.get('nivel_3') or ""), 
                str(it.get('nivel_4') or "")
            ]
            alturas = [len(self.multi_cell(w[i], 4, t, split_only=True)) * 4 for i, t in enumerate(textos)]
            h_fila = max(alturas) + 2
            if h_fila < 8: h_fila = 8
            if self.get_y() + h_fila > 270: self.add_page()
            x_ini, y_ini = self.get_x(), self.get_y()
            for i, t in enumerate(textos):
                style = 'FD' if i < 2 else 'D'
                self.set_fill_color(245, 245, 245) if i < 2 else None
                self.rect(x_ini, y_ini, w[i], h_fila, style=style)
                self.set_xy(x_ini, y_ini)
                self.multi_cell(w[i], 4, t, 0, 'L')
                x_ini += w[i]
            self.set_xy(10, y_ini + h_fila)

    def bloque_alumnos(self, evaluaciones):
        if not evaluaciones: return
        self.set_font("Arial", "B", 10)
        self.set_fill_color(240, 240, 240)
        self.cell(190, 8, "EVALUACIÓN ALUMNADO", 1, 1, "C", True)
        self.ln(5)
        w_col, gap = 60, 5
        for i in range(0, len(evaluaciones), 3):
            y_inicio_fila = self.get_y()
            for j in range(3):
                idx = i + j
                if idx < len(evaluaciones):
                    e = evaluaciones[idx]
                    x_pos = 10 + (j * (w_col + gap))
                    self.set_xy(x_pos, y_inicio_fila)
                    self.set_font("Arial", "B", 8)
                    self.cell(w_col, 7, f" {e['nombre_alumno'][:30]}", 1, 1, "L", True)
                    y_item = self.get_y()
                    for letra, nivel in e['puntos'].items():
                        self.set_xy(x_pos, y_item)
                        self.set_font("Arial", "", 8)
                        self.cell(8, 6, f"{letra}:", "L", 0)
                        for n in range(1, 5):
                            if n == int(nivel):
                                self.set_fill_color(200, 200, 200)
                                self.ellipse(self.get_x() + 4.5, self.get_y() + 1, 4, 4, 'F')
                            self.cell(13, 6, str(n), 0, 0, "C")
                        self.cell(0.1, 6, "", "R", 1)
                        y_item += 6
                    self.line(x_pos, y_item, x_pos + w_col, y_item)
            self.ln(10)

class AutoevaluacionPDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 14)
        self.cell(0, 10, "AUTOEVALUACIÓN DE LA PRÁCTICA DOCENTE", ln=True, align="C")
        self.set_font("Arial", "I", 10)
        self.set_text_color(255, 110, 64)
        self.cell(0, 5, "Especialista: Ángela Ortiz Ordóñez", ln=True, align="C")
        self.set_text_color(0, 0, 0)
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Página {self.page_no()}/{{nb}}", align="C")

    def tabla_items(self, sda_num, fecha, datos_items):
        self.set_font("Arial", "B", 10)
        self.set_fill_color(240, 240, 240)
        self.cell(95, 10, f" SDA: {sda_num}", 1, 0, "L", True)
        self.cell(95, 10, f" Fecha: {fecha}", 1, 1, "R", True)
        self.ln()
        w = [80, 15, 15, 80]
        self.set_font("Arial", "B", 9)
        headers = ["Ítem", "Sí", "No", "Observaciones"]
        for i, h in enumerate(headers): self.cell(w[i], 8, h, 1, 0, "C", True)
        self.ln()
        self.set_font("Arial", "", 8)
        for item in datos_items:
            obs_txt = str(item.get('obs') or "")
            nom_txt = str(item.get('nombre') or "")
            l_obs = self.multi_cell(w[3], 4, obs_txt, split_only=True)
            l_nom = self.multi_cell(w[0], 4, nom_txt, split_only=True)
            h_fila = max(len(l_obs), len(l_nom)) * 4.5
            h_fila = max(h_fila, 8)
            if self.get_y() + h_fila > 260: self.add_page()
            x, y = self.get_x(), self.get_y()
            self.rect(x, y, w[0], h_fila)
            self.multi_cell(w[0], 4.5, nom_txt, 0, 'L')
            self.set_xy(x + w[0], y)
            self.rect(x + w[0], y, w[1], h_fila)
            if item['valor'] == "Sí":
                self.set_font("ZapfDingbats", "", 10)
                self.cell(w[1], h_fila, "4", 0, 0, "C")
            self.set_xy(x + w[0] + w[1], y)
            self.rect(x + w[0] + w[1], y, w[2], h_fila)
            if item['valor'] == "No":
                self.set_font("ZapfDingbats", "", 10)
                self.cell(w[2], h_fila, "4", 0, 0, "C")
            self.set_font("Arial", "", 8)
            self.set_xy(x + w[0] + w[1] + w[2], y)
            self.rect(x + w[0] + w[1] + w[2], y, w[3], h_fila)
            self.multi_cell(w[3], 4.5, obs_txt, 0, 'L')
            self.set_xy(10, y + h_fila)

    def reflexion(self, ref):
        self.ln(5)
        self.set_font("Arial", "B", 10)
        self.set_fill_color(245, 245, 245)
        self.cell(0, 8, " REFLEXIÓN FINAL", 1, 1, "L", True)
        tits = {"funciona": "Lo que ha funcionado:", "dificultades": "Dificultades:", "mejoras": "Mejoras:"}
        for k, v in ref.items():
            self.set_font("Arial", "B", 9); self.ln(2)
            self.cell(0, 5, tits.get(k, k), ln=True)
            self.set_font("Arial", "", 9)
            self.multi_cell(0, 5, str(v or "---"), 0, 'L')

# --- 3. FUNCIONES DE INTERFAZ ---
def cabecera_estilizada(titulo):
    st.markdown(f"""
        <div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px; border-left: 8px solid #4f64af; margin-bottom: 20px;">
            <h1 style="margin: 0; color: #1e3d59; font-family: 'Helvetica Neue', sans-serif; font-size: 24px;">{titulo}</h1>
            <p style="margin: 0; color: #4f64af; font-size: 1.2rem; font-weight: bold;">Maestra Especialista: <span style="color: #ff6e40;">Ángela Ortiz Ordóñez</span></p>
        </div>
        """, unsafe_allow_html=True)

# --- 4. LÓGICA DE APLICACIÓN ---
with st.sidebar:
    st.title("🛠️ Menú")
    opcion = st.radio("Herramienta:", ["👥 Registro de Alumnos", "📝 Autoevaluación Práctica"])

if opcion == "👥 Registro de Alumnos":
    cabecera_estilizada("🎓 Registro Aula P.T.")
    
    tab_alu, tab_conf, tab_eval, tab_hist = st.tabs(["👥 Alumnos", "⚙️ Ítems", "📝 Evaluación", "📅 Histórico"])
    
    # --- CARGA Y LIMPIEZA DE DATOS (LA SOLUCIÓN ESTÁ AQUÍ) ---
    res_a_raw = supabase.table("alumnos").select("*").execute().data
    orden_cursos = ["INF 3", "INF 4", "INF 5", "1º", "2º", "3º", "4º", "5º", "6º"]
    res_a = sorted(res_a_raw, key=lambda x: (orden_cursos.index(x["curso"]) if x["curso"] in orden_cursos else 999, x["nombre"]))
    
    # Cargamos ítems y forzamos la limpieza de los "None"
    res_i_raw = supabase.table("configuracion_items").select("*").order("letra").execute().data
    res_i = []
    for item in res_i_raw:
        for n in ['nivel_1', 'nivel_2', 'nivel_3', 'nivel_4']:
            if item.get(n) is None or str(item.get(n)).lower() == "none" or str(item.get(n)).strip() == "":
                item[n] = "No definido"
        res_i.append(item)

    with tab_alu:
        c_sel, c_del = st.columns([3, 1])
        sel_a = c_sel.selectbox("Seleccionar Alumno", ["+ Nuevo"] + [f"{a['nombre']} ({a['curso']})" for a in res_a])
        v_id, v_nom, v_cur = 0, "", ""
        if sel_a != "+ Nuevo":
            d = next(a for a in res_a if f"{a['nombre']} ({a['curso']})" == sel_a)
            v_id, v_nom, v_cur = d['id'], d['nombre'], d['curso']
            if c_del.button("🗑️ Eliminar Alumno", use_container_width=True):
                supabase.table("alumnos").delete().eq("id", v_id).execute(); st.rerun()
        
        with st.form("f_alu"):
            c1, c2 = st.columns(2)
            n_in = c1.text_input("Nombre Completo", value=v_nom)
            cur_in = c2.text_input("Curso", value=v_cur)
            if st.form_submit_button("💾 Guardar Datos"):
                if v_id == 0: supabase.table("alumnos").insert({"nombre": n_in, "curso": cur_in}).execute()
                else: supabase.table("alumnos").update({"nombre": n_in, "curso": cur_in}).eq("id", v_id).execute()
                st.rerun()

    with tab_conf:
        c_sel_i, c_del_i = st.columns([3, 1])
        sel_i = c_sel_i.selectbox("Seleccionar Ítem", ["+ Nuevo"] + [f"{i['letra']} - {i['descripcion'][:30]}" for i in res_i])
        v_let, v_des, v_n = "", "", [""]*4
        if sel_i != "+ Nuevo":
            d = next(i for i in res_i if f"{i['letra']} - {i['descripcion'][:30]}" == sel_i)
            v_let, v_des, v_n = d['letra'], d['descripcion'], [d['nivel_1'], d['nivel_2'], d['nivel_3'], d['nivel_4']]
            if c_del_i.button("🗑️ Eliminar Ítem", use_container_width=True):
                supabase.table("configuracion_items").delete().eq("letra", v_let).execute(); st.rerun()
        with st.form("f_item"):
            c1, c2 = st.columns([1, 4])
            l_in = c1.text_input("Letra", value=v_let).upper()
            d_in = c2.text_input("Descripción", value=v_des)
            ca, cb = st.columns(2)
            n1, n2, n3, n4 = ca.text_area("N1", v_n[0]), cb.text_area("N2", v_n[1]), ca.text_area("N3", v_n[2]), cb.text_area("N4", v_n[3])
            if st.form_submit_button("💾 Guardar Ítem"):
                supabase.table("configuracion_items").upsert({"letra": l_in, "descripcion": d_in, "nivel_1": n1, "nivel_2": n2, "nivel_3": n3, "nivel_4": n4}).execute(); st.rerun()

    with tab_eval:
        if not res_a: st.warning("No hay alumnos.")
        else:
            c1, c2 = st.columns(2)
            fe_ev = c2.date_input("Fecha", datetime.now())
            evals_h = supabase.table("evaluaciones_alumnos").select("nombre_alumno").eq("fecha", fe_ev.isoformat()).execute().data
            set_ev = {ev['nombre_alumno'] for ev in evals_h}
            pend, comp = [], []
            for a in res_a:
                nom = f"{a['nombre']} ({a['curso']})"
                comp.append(f"✅ {nom}") if nom in set_ev else pend.append(nom)
            al_sel = c1.selectbox("Elegir Alumno", pend + comp)
            is_done = al_sel.startswith("✅")
            
            with st.form("f_ev", clear_on_submit=True):
                pts = {}
                for it in res_i:
                    st.write(f"**{it['letra']} - {it['descripcion']}**")
                    pts[it['letra']] = st.radio(
                        f"Nivel {it['letra']}", 
                        [1, 2, 3, 4], 
                        format_func=lambda x, it=it: f"N{x}: {it.get(f'nivel_{x}')}", 
                        key=f"e_{it['letra']}", 
                        horizontal=True
                    )
                if st.form_submit_button("📝 Registrar", disabled=is_done):
                    supabase.table("evaluaciones_alumnos").insert({"nombre_alumno": al_sel, "puntos": pts, "fecha": fe_ev.isoformat()}).execute(); st.rerun()

    with tab_hist:
        evals = supabase.table("evaluaciones_alumnos").select("*").order("fecha", desc=True).execute().data
        if evals:
            df = pd.DataFrame(evals)
            df['f_corta'] = df['fecha'].map(lambda x: x[:10])
            dias = df['f_corta'].unique()
            c_dia, c_pdf = st.columns([3, 1])
            sel_d = c_dia.selectbox("Filtrar Fecha", ["Ver todos"] + list(dias))
            if c_pdf.button("🖨️ PDF Informe", use_container_width=True):
                pdf = EvaluacionPDF()
                pdf.tabla_maestra(res_i)
                pdf.add_page()
                ev_f = evals if sel_d == "Ver todos" else [e for e in evals if e['fecha'][:10] == sel_d]
                pdf.bloque_alumnos(ev_f)
                st.download_button("⬇️ Descargar", bytes(pdf.output()), f"Informe_{sel_d}.pdf")
            for d in dias:
                with st.expander(f"📅 Sesiones {d}"):
                    for _, r in df[df['f_corta'] == d].iterrows():
                        c1, c2 = st.columns([5, 1])
                        c1.write(f"👤 **{r['nombre_alumno']}**")
                        if c2.button("🗑️", key=f"h_{r['id']}"):
                            supabase.table("evaluaciones_alumnos").delete().eq("id", r['id']).execute(); st.rerun()

else:
    cabecera_estilizada("📝 Registro de Autoevaluación")
    tab1, tab2, tab3 = st.tabs(["📝 Formulario", "📅 Historial", "⚙️ Configurar Ítems"])
    
    if "edit_id" not in st.session_state: st.session_state.edit_id = None
    if "datos_edicion" not in st.session_state: st.session_state.datos_edicion = {}

    with tab3:
        it_ae = supabase.table("items_autoevaluacion").select("*").order("id").execute().data
        with st.form("n_ae"):
            n = st.text_input("Nuevo Ítem")
            if st.form_submit_button("Añadir"):
                supabase.table("items_autoevaluacion").insert({"nombre": n}).execute(); st.rerun()
        for i in it_ae:
            c1, c2 = st.columns([5,1])
            c1.write(f"• {i['nombre']}")
            if c2.button("🗑️", key=f"dae_{i['id']}"):
                supabase.table("items_autoevaluacion").delete().eq("id", i['id']).execute(); st.rerun()

    with tab1:
        if st.session_state.edit_id:
            st.warning("⚠️ Modo Edición Activo")
            if st.button("❌ Cancelar"):
                st.session_state.edit_id = None; st.session_state.datos_edicion = {}; st.rerun()
        
        d = st.session_state.datos_edicion
        f_v = datetime.fromisoformat(d.get('fecha')) if d.get('fecha') else datetime.now()
        s_v = d.get('sda', 1)
        r_v = d.get('reflexion_final', {})
        it_e_v = {x['nombre']: x for x in d.get('items_evaluados', [])}

        c1, c2 = st.columns(2)
        f_s = c1.date_input("Fecha de Registro", f_v)
        s_s = c2.number_input("SDA", 1, 20, int(s_v))

        eval_ae = []
        for i in it_ae:
            st.write(f"**{i['nombre']}**")
            ca, cb = st.columns([1,4])
            idx = 0 if it_e_v.get(i['nombre'], {}).get('valor') == "Sí" else 1
            v = ca.radio("Cumplido", ["Sí", "No"], index=idx, key=f"rae_{i['id']}", horizontal=True)
            o = cb.text_input("Observaciones", value=it_e_v.get(i['nombre'], {}).get('obs', ""), key=f"oae_{i['id']}")
            eval_ae.append({"nombre": i['nombre'], "valor": v, "obs": o})

        st.divider()
        ref1 = st.text_area("Funcionamiento", value=r_v.get('funciona', ""))
        ref2 = st.text_area("Dificultades", value=r_v.get('dificultades', ""))
        ref3 = st.text_area("Propuestas de mejora", value=r_v.get('mejoras', ""))

        if st.button("💾 Guardar Autoevaluación"):
            payload = {"fecha": f_s.isoformat(), "sda": s_s, "items_evaluados": eval_ae, "reflexion_final": {"funciona": ref1, "dificultades": ref2, "mejoras": ref3}}
            if st.session_state.edit_id:
                supabase.table("autoevaluaciones").update(payload).eq("id", st.session_state.edit_id).execute()
                st.session_state.edit_id = None
            else:
                supabase.table("autoevaluaciones").insert(payload).execute()
            st.success("¡Guardado correctamente!"); st.rerun()

    with tab2:
        regs = supabase.table("autoevaluaciones").select("*").order("fecha", desc=True).execute().data
        for r in regs:
            with st.expander(f"📅 {r['fecha']} - SDA {r['sda']}"):
                c1, c2, c3 = st.columns(3)
                if c1.button("🖨️ PDF", key=f"pae_{r['id']}"):
                    pdf = AutoevaluacionPDF()
                    pdf.add_page()
                    pdf.tabla_items(r['sda'], r['fecha'], r['items_evaluados'])
                    pdf.reflexion(r['reflexion_final'])
                    st.download_button("Descargar", bytes(pdf.output()), f"Auto_{r['fecha']}.pdf")
                if c2.button("✏️", key=f"eae_{r['id']}"):
                    st.session_state.edit_id = r['id']; st.session_state.datos_edicion = r; st.rerun()
                if c3.button("🗑️", key=f"bae_{r['id']}"):
                    supabase.table("autoevaluaciones").delete().eq("id", r['id']).execute(); st.rerun()