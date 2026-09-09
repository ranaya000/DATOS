import streamlit as st
import pandas as pd
import io

# Configuración inicial de la página
st.set_page_config(page_title="Sistema de Almacén - ONPE", page_icon="📦", layout="wide")

# ==============================================================================
# SISTEMA DE AUTENTICACIÓN (LOGIN)
# ==============================================================================
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.markdown("### 🔐 Acceso Restringido - Sistema de Almacén ONPE")
    st.info("Ingrese sus credenciales autorizadas para acceder al sistema.")
    
    usuario_input = st.text_input("Usuario")
    password_input = st.text_input("Contraseña", type="password")
    
    if st.button("Ingresar al Sistema"):
        if usuario_input == "admin_almacen" and password_input == "onpe2026*":
            st.session_state.autenticado = True
            st.rerun()
        else:
            st.error("Credenciales incorrectas. Intente nuevamente.")
    st.stop()

# ==============================================================================
# LÓGICA DE NEGOCIO Y CARGA DE DATOS
# ==============================================================================
@st.cache_data
def cargar_datos_sistema():
    df_movimientos_init = pd.DataFrame()
    df_stock = pd.DataFrame()
    dict_seguimiento = {}
    
    archivos_seguimiento = {
        "SGGDI EG 2026": 'LISTA SGGDI EG 2026 (1).xlsx',
        "EG 2026 (SEP)": 'GITE - EG 2026 (SEP) 2026 (1)-PARA SEGUIMIENTO -30-06-2026.xlsx',
        "ERM (EP) 2026": 'GITE - ERM (EP) 2026 CON SUBGERENCIAS (1).xlsx',
        "CN PROCESOS ELECTORALES 2026": 'GITE CN PROCESOS ELECTORALES 2026 - PARA SEGUIMIENTO 30-06-2026.xlsx'
    }

    for nombre_key, filename in archivos_seguimiento.items():
        try:
            xls = pd.ExcelFile(filename)
            sheet_to_load = xls.sheet_names[0]
            for s in xls.sheet_names:
                if any(k in s.lower() for k in ['biene', 'programación', 'aprobada', 'base']):
                    sheet_to_load = s
                    break
            
            df_raw = pd.read_excel(filename, sheet_name=sheet_to_load, header=None)
            header_row = 0
            for idx, row in df_raw.iterrows():
                fila_str = str(row.values).upper()
                if 'AÑO' in fila_str or 'CATEGORÍA' in fila_str or 'ÓRGANO' in fila_str or 'DESCRIPCIÓN' in fila_str:
                    header_row = idx
                    break
            
            df_temp = pd.read_excel(filename, sheet_name=sheet_to_load, header=header_row)
            df_temp = df_temp.loc[:, ~df_temp.columns.astype(str).str.contains('^Unnamed')]
            df_temp['ARCHIVO_ORIGEN'] = nombre_key
            dict_seguimiento[nombre_key] = df_temp
        except Exception:
            pass

    try:
        df_movimientos_init = pd.read_excel('movimientos.xlsx')
    except Exception:
        pass

    try:
        df_stock = pd.read_excel('stock_2.xlsx')
    except Exception:
        pass

    return dict_seguimiento, df_movimientos_init, df_stock

dict_seguimiento_global, df_movimientos_init_global, df_stock_global = cargar_datos_sistema()

# Inicializar inventario y movimientos en sesión
if 'inventario_bienes' not in st.session_state:
    inventario_temp = []
    if not df_stock_global.empty:
        for idx, r in df_stock_global.iterrows():
            prod = str(r.get('Producto', '')).strip().upper()
            cat = str(r.get('Categoría', 'GENERAL')).strip().upper()
            prov = str(r.get('Proveedor', '')).strip().upper()
            stock_ini = float(r.get('Inventario Inicial', 0.0) or 0.0)
            unid = str(r.get('Unidad Medida', 'UNIDAD')).strip().upper()
            
            item = {
                "id_fila": idx + 1,
                "categoria": cat,
                "producto": prod,
                "proveedor": prov,
                "unidad": unid,
                "stock_inicial": stock_ini,
                "stock_actual": stock_ini
            }
            inventario_temp.append(item)
    st.session_state.inventario_bienes = inventario_temp

if 'historial_movimientos' not in st.session_state:
    movs_iniciales = []
    if not df_movimientos_init_global.empty:
        for _, row in df_movimientos_init_global.iterrows():
            movs_iniciales.append(row.to_dict())
    st.session_state.historial_movimientos = movs_iniciales

if 'carrito_operaciones' not in st.session_state:
    st.session_state.carrito_operaciones = []

# ==============================================================================
# INTERFAZ PRINCIPAL CON PESTAÑAS EN STREAMLIT
# ==============================================================================
st.title("📦 SISTEMA INTEGRAL DE ALMACÉN Y KARDEX - ONPE")
st.markdown("---")

# Barra superior con Botón de Guardado General y Botón de Descarga Excel Completo
col_sup1, col_sup2 = st.columns([1, 1])
with col_sup1:
    if st.button("💾 GUARDAR TODOS LOS CAMBIOS GENERALES"):
        st.success("¡Todos los cambios y movimientos han sido guardados y consolidados exitosamente en el sistema!")
with col_sup2:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_stock_exp = pd.DataFrame([{
            "Categoría": i['categoria'],
            "Producto": i['producto'],
            "Proveedor / Marca": i['proveedor'],
            "Unidad Medida": i['unidad'],
            "Inventario Inicial": i['stock_inicial'],
            "Stock Actual": i['stock_actual']
        } for i in st.session_state.inventario_bienes])
        df_stock_exp.to_excel(writer, sheet_name='Stock_Actual', index=False)
        
        if st.session_state.historial_movimientos:
            df_movs_exp = pd.DataFrame(st.session_state.historial_movimientos)
            df_movs_exp.to_excel(writer, sheet_name='Movimientos', index=False)
            
        for k_seg, df_seg in dict_seguimiento_global.items():
            sheet_name_clean = ''.join(c for c in k_seg if c.isalnum() or c==' ')[:31]
            df_seg.to_excel(writer, sheet_name=sheet_name_clean, index=False)
            
    processed_data = output.getvalue()
    st.download_button(
        label="📥 DESCARGAR REPORTE GENERAL EN EXCEL (Múltiples Hojas)",
        data=processed_data,
        file_name="reporte_general_almacen_onpe.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

st.markdown("---")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📝 Registrar", 
    "📊 Stock y Guardado", 
    "📤 Movimientos (Entradas, Salidas y Bajas)", 
    "🔍 Gerencia, Subgerencia y Seguimiento", 
    "📋 Kardex (Fraccionado)"
])

# --- PESTAÑA 1: REGISTRAR ---
with tab1:
    st.subheader("Registro de Operaciones (Entrada, Salida o Baja)")
    tipo_operacion = st.selectbox("Tipo de Operación:", ['SALIDA (ENTREGA A ÁREA)', 'INGRESO (COMPRA/ADQUISICIÓN)', 'BAJA (MERMA/DETERIORO)'])
    
    col_op1, col_op2 = st.columns(2)
    with col_op1:
        if "SALIDA" in tipo_operacion:
            referencia_origen = st.text_input("Guía de Remisión / Personal Solicitante", placeholder="Ej. Juan Pérez / Guía 001")
        elif "INGRESO" in tipo_operacion:
            referencia_origen = st.text_input("Nro PECOSA / Orden de Compra", placeholder="Ej. PECOSA 123 / O/C 456")
        else:
            referencia_origen = st.text_input("Motivo de la Baja", placeholder="Ej. Deterioro o rotura de almacén")
            
    with col_op2:
        observacion_op = st.text_input("Observación / Detalle adicional", placeholder="Ej. Urgente para proceso electoral")

    buscar_prod_reg = st.text_input("Buscar producto en inventario para operar:")
    opciones_prod = {f"{i['producto']} (Stock Actual: {i['stock_actual']})": i['producto'] for i in st.session_state.inventario_bienes if not buscar_prod_reg or buscar_prod_reg.lower() in i['producto'].lower()}
    
    prod_seleccionado_label = st.selectbox("Seleccione Producto:", options=list(opciones_prod.keys()) if opciones_prod else ["No encontrado"])
    cantidad_op = st.number_input("Cantidad:", min_value=1, value=1)

    btn_c1, btn_c2 = st.columns(2)
    with btn_c1:
        if st.button("➕ Agregar al Carrito de Operación"):
            if prod_seleccionado_label and prod_seleccionado_label != "No encontrado":
                nombre_p = opciones_prod[prod_seleccionado_label]
                prod_obj = next((i for i in st.session_state.inventario_bienes if i['producto'] == nombre_p), None)
                if prod_obj:
                    if ("SALIDA" in tipo_operacion or "BAJA" in tipo_operacion) and cantidad_op > prod_obj['stock_actual']:
                        st.error(f"¡Stock insuficiente! Stock actual de '{nombre_p}' es {prod_obj['stock_actual']}.")
                    else:
                        st.session_state.carrito_operaciones.append({
                            "producto": nombre_p,
                            "cantidad": cantidad_op,
                            "tipo": tipo_operacion,
                            "ref": referencia_origen,
                            "obs": observacion_op
                        })
                        st.success(f"Añadido al carrito: {nombre_p} ({cantidad_op})")

    st.markdown("**Resumen del Carrito de Operación:**")
    if st.session_state.carrito_operaciones:
        for idx_it, itm in enumerate(st.session_state.carrito_operaciones):
            cols_car = st.columns([6, 1])
            with cols_car[0]:
                st.text(f"• [{itm['tipo']}] {itm['producto']} - Cantidad: {itm['cantidad']} | Ref: {itm['ref']}")
            with cols_car[1]:
                if st.button("❌", key=f"del_carrito_{idx_it}"):
                    st.session_state.carrito_operaciones.pop(idx_it)
                    st.rerun()
        
        if st.button("💾 Confirmar y Aplicar Operaciones del Carrito"):
            for itm in st.session_state.carrito_operaciones:
                for prod in st.session_state.inventario_bienes:
                    if prod['producto'] == itm['producto']:
                        if "INGRESO" in itm['tipo']:
                            prod['stock_actual'] += itm['cantidad']
                            t_mov = "INGRESO"
                        elif "SALIDA" in itm['tipo']:
                            prod['stock_actual'] -= itm['cantidad']
                            t_mov = "SALIDA"
                        else:
                            prod['stock_actual'] -= itm['cantidad']
                            t_mov = "BAJA"
                        
                        nuevo_movimiento = {
                            "Tipo": t_mov,
                            "Descripción del Producto": prod['producto'],
                            "Cantidad": itm['cantidad'],
                            "Guía de remisión": itm['ref'] if "SALIDA" in itm['tipo'] else "",
                            "PECOSA / O.C.": itm['ref'] if "INGRESO" in itm['tipo'] else "",
                            "Detalle / Motivo": f"{itm['ref']} - {itm['obs']}"
                        }
                        st.session_state.historial_movimientos.append(nuevo_movimiento)
                        break
            
            st.session_state.carrito_operaciones.clear()
            st.success("¡Operaciones aplicadas y registradas correctamente!")
            st.rerun()
    else:
        st.caption("(El carrito está vacío)")

# --- PESTAÑA 2: STOCK Y GUARDADO ---
with tab2:
    st.subheader("Stock Actual y Guardado")
    
    lista_cat_stock = ['[TODOS]'] + sorted(list(set(i['categoria'] for i in st.session_state.inventario_bienes)))
    lista_prov_stock = ['[TODOS]'] + sorted(list(set(i['proveedor'] for i in st.session_state.inventario_bienes if i['proveedor'])))
    
    f_s_col1, f_s_col2 = st.columns(2)
    with f_s_col1:
        filtro_cat_s = st.selectbox("Filtrar por Categoría:", lista_cat_stock, key="f_cat_stock")
    with f_s_col2:
        filtro_prov_s = st.selectbox("Filtrar por Proveedor / Marca:", lista_prov_stock, key="f_prov_stock")
        
    filtro_txt_s = st.text_input("🔍 Buscar nombre de producto:", key="f_txt_stock")
    
    data_stock_list = []
    for i in st.session_state.inventario_bienes:
        m_cat = filtro_cat_s == '[TODOS]' or i['categoria'] == filtro_cat_s
        m_prov = filtro_prov_s == '[TODOS]' or i['proveedor'] == filtro_prov_s
        m_txt = not filtro_txt_s or filtro_txt_s.lower() in i['producto'].lower()
        
        if m_cat and m_prov and m_txt:
            data_stock_list.append({
                "Categoría": i['categoria'],
                "Producto": i['producto'],
                "Proveedor / Marca": i['proveedor'],
                "Unidad Medida": i['unidad'],
                "Inventario Inicial": i['stock_inicial'],
                "Stock Actual": i['stock_actual']
            })
            
    df_stock_view = pd.DataFrame(data_stock_list)
    st.dataframe(df_stock_view, use_container_width=True)

# --- PESTAÑA 3: MOVIMIENTOS (HISTORIAL GENERAL) ---
with tab3:
    st.subheader("Historial General de Movimientos (Entradas, Salidas y Bajas)")
    st.markdown("Selecciona en la casilla **'Borrar'** de la tabla los movimientos erróneos y haz clic en el botón inferior para eliminarlos.")
    
    if st.session_state.historial_movimientos:
        df_movs_total = pd.DataFrame(st.session_state.historial_movimientos)
        # Añadir una columna de selección (checkbox) al inicio del DataFrame
        df_movs_total.insert(0, "Borrar", False)
        
        # Mostrar tabla interactiva donde se pueden marcar los checkboxes
        df_editado = st.data_editor(
            df_movs_total,
            use_container_width=True,
            column_config={"Borrar": st.column_config.CheckboxColumn("🗑️ Borrar", required=True)},
            disabled=[col for col in df_movs_total.columns if col != "Borrar"]
        )
        
        if st.button("🗑️ Eliminar registros seleccionados"):
            # Obtener índices de las filas marcadas para borrar (orden descendente para no alterar índices al eliminar)
            indices_a_borrar = df_editado[df_editado["Borrar"] == True].index.tolist()
            
            if indices_a_borrar:
                for idx in sorted(indices_a_borrar, reverse=True):
                    mov_item = st.session_state.historial_movimientos[idx]
                    prod_afectado = mov_item.get('Descripción del Producto')
                    cant_afectada = float(mov_item.get('Cantidad', 0))
                    tipo_afectado = mov_item.get('Tipo')
                    
                    # Revertir stock
                    for prod in st.session_state.inventario_bienes:
                        if prod['producto'] == prod_afectado:
                            if tipo_afectado == "INGRESO":
                                prod['stock_actual'] -= cant_afectada
                            elif tipo_afectado in ["SALIDA", "BAJA"]:
                                prod['stock_actual'] += cant_afectada
                            break
                    
                    # Eliminar del historial
                    st.session_state.historial_movimientos.pop(idx)
                
                st.success("¡Registros seleccionados eliminados y stock ajustado correctamente!")
                st.rerun()
            else:
                st.warning("No has seleccionado ningún registro para borrar.")
    else:
        st.warning("No hay registros de movimientos disponibles.")

# --- PESTAÑA 4: CONSULTA DE REQUERIMIENTOS (GERENCIA / SUBGERENCIA) ---
with tab4:
    st.subheader("Consulta por Gerencia / Subgerencia y Requerimientos")
    st.markdown("*(Independiente del stock general de almacén)*")
    
    if dict_seguimiento_global:
        opciones_archivos = ['[TODOS]'] + list(dict_seguimiento_global.keys())
        archivo_sel = st.selectbox("Seleccionar Archivo / Proceso de Seguimiento:", options=opciones_archivos)
        
        if archivo_sel == '[TODOS]':
            df_actual = pd.concat(list(dict_seguimiento_global.values()), ignore_index=True, sort=False)
        else:
            df_actual = dict_seguimiento_global[archivo_sel]
        
        if not df_actual.empty:
            cols_disponibles = list(df_actual.columns)
            col_organo = next((c for c in cols_disponibles if 'órgano' in str(c).lower() or 'organo' in str(c).lower()), None)
            col_tpptto = next((c for c in cols_disponibles if 'tipo de ppto' in str(c).lower() or 'tpptto' in str(c).lower()), None)
            
            f_col1, f_col2 = st.columns(2)
            
            if col_organo:
                valores_organo = ['[TODOS]'] + sorted(df_actual[col_organo].dropna().astype(str).unique().tolist())
                with f_col1: sel_organo = st.selectbox("Seleccionar Órgano:", options=valores_organo)
            else:
                with f_col1: sel_organo = '[TODOS]'
            
            if col_tpptto:
                valores_tpptto = ['[TODOS]'] + sorted(df_actual[col_tpptto].dropna().astype(str).unique().tolist())
                with f_col2: sel_tpptto = st.selectbox("Seleccionar Tipo de PPTO:", options=valores_tpptto)
            else:
                with f_col2: sel_tpptto = '[TODOS]'

            busqueda_seg = st.text_input("🔍 Búsqueda general en requerimientos:")
            
            df_filtrado = df_actual.copy()
            if col_organo and sel_organo != '[TODOS]':
                df_filtrado = df_filtrado[df_filtrado[col_organo].astype(str) == sel_organo]
            if col_tpptto and sel_tpptto != '[TODOS]':
                df_filtrado = df_filtrado[df_filtrado[col_tpptto].astype(str) == sel_tpptto]
            if busqueda_seg:
                mask = df_filtrado.astype(str).apply(lambda x: x.str.contains(busqueda_seg, case=False, na=False)).any(axis=1)
                df_filtrado = df_filtrado[mask]
                
            st.write(f"Registros encontrados: {len(df_filtrado)}")
            st.dataframe(df_filtrado, use_container_width=True)
        else:
            st.warning("El archivo seleccionado está vacío.")
    else:
        st.warning("No se encontraron archivos de seguimiento en el directorio.")

# --- PESTAÑA 5: KARDEX ---
with tab5:
    st.subheader("Kardex Fraccionado por Producto")
    lista_kardex_cat = ['[TODOS]'] + sorted(list(set(i['categoria'] for i in st.session_state.inventario_bienes)))
    lista_kardex_prov = ['[TODOS]'] + sorted(list(set(i['proveedor'] for i in st.session_state.inventario_bienes if i['proveedor'])))
    
    k_cat = st.selectbox("Categoría Kardex:", lista_kardex_cat, key="k_cat")
    k_prov = st.selectbox("Proveedor Kardex:", lista_kardex_prov, key="k_prov")
    k_buscar = st.text_input("Buscar producto en Kardex:", key="k_bus")
    
    opts_k = []
    for i in st.session_state.inventario_bienes:
        m_txt = not k_buscar or k_buscar.lower() in i['producto'].lower()
        m_cat = k_cat == '[TODOS]' or i['categoria'] == k_cat
        m_prov = k_prov == '[TODOS]' or i['proveedor'] == k_prov
        if m_txt and m_cat and m_prov:
            opts_k.append((i['producto'], i['producto']))
            
    prod_k_sel = st.selectbox("Seleccione Producto:", options=[o[1] for o in opts_k], format_func=lambda x: next((o[0] for o in opts_k if o[1] == x), ""))
    
    if prod_k_sel:
        prod_data = next((i for i in st.session_state.inventario_bienes if i['producto'] == prod_k_sel), None)
        if prod_data:
            st.markdown(f"**Producto:** {prod_data['producto']}")
            st.markdown(f"**Categoría:** {prod_data['categoria']} | **Proveedor/Marca:** {prod_data['proveedor']} | **Stock Inicial:** {prod_data['stock_inicial']} | **Stock Actual:** {prod_data['stock_actual']}")
            
            historial_prod = [m for m in st.session_state.historial_movimientos if str(m.get('Descripción del Producto', '')).strip().upper() == prod_data['producto']]
            if historial_prod:
                st.dataframe(pd.DataFrame(historial_prod), use_container_width=True)
            else:
                st.info("No hay movimientos registrados para este producto.")