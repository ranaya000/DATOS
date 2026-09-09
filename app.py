import streamlit as st
import pandas as pd
import re

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
# LÓGICA DE NEGOCIO Y CARGA DE DATOS CON CABECERAS LIMPIAS
# ==============================================================================
@st.cache_data
def cargar_datos_sistema():
    df_movimientos = pd.DataFrame()
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
            
            # Leer sin cabecera primero para ubicar exactamente en qué fila están los títulos reales
            df_raw = pd.read_excel(filename, sheet_name=sheet_to_load, header=None)
            header_row = 0
            for idx, row in df_raw.iterrows():
                fila_str = str(row.values).upper()
                if 'AÑO' in fila_str or 'CATEGORÍA' in fila_str or 'ÓRGANO' in fila_str or 'DESCRIPCIÓN' in fila_str:
                    header_row = idx
                    break
            
            # Recargar el DataFrame usando la fila correcta como cabecera (adiós Unnamed)
            df_temp = pd.read_excel(filename, sheet_name=sheet_to_load, header=header_row)
            # Limpiar nombres de columnas nulos o vacíos
            df_temp = df_temp.loc[:, ~df_temp.columns.astype(str).str.contains('^Unnamed')]
            dict_seguimiento[nombre_key] = df_temp
        except Exception as e:
            pass

    try:
        df_movimientos = pd.read_excel('movimientos.xlsx')
        df_movimientos['Guía de remisión'] = df_movimientos['Guía de remisión'].fillna('').astype(str)
        df_movimientos['Descripción del Producto'] = df_movimientos['Descripción del Producto'].fillna('').astype(str)
    except Exception:
        pass

    try:
        df_stock = pd.read_excel('stock_2.xlsx')
    except Exception:
        pass

    return dict_seguimiento, df_movimientos, df_stock

dict_seguimiento_global, df_movimientos_global, df_stock_global = cargar_datos_sistema()

# Inicializar inventario en sesión basado estrictamente en 'stock_2.xlsx'
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
                "stock": stock_ini,
                "movimientos": [{
                    "tipo": "INVENTARIO INICIAL",
                    "cantidad": stock_ini,
                    "saldo": stock_ini,
                    "detalle": "Carga inicial desde stock_2.xlsx"
                }]
            }
            inventario_temp.append(item)
            
        # Descontar salidas si existen en movimientos
        if not df_movimientos_global.empty:
            for _, m in df_movimientos_global.iterrows():
                p_nombre = str(m['Descripción del Producto']).strip().upper()
                cant_salida = float(m['Cantidad'] or 0)
                for item in inventario_temp:
                    if item['producto'] == p_nombre:
                        item['stock'] -= cant_salida
                        item['movimientos'].append({
                            "tipo": "SALIDA",
                            "cantidad": cant_salida,
                            "saldo": item['stock'],
                            "detalle": f"Guía/Personal: {m['Guía de remisión']} | O/C: {m['Orden de compra']}"
                        })
                        break
                        
    st.session_state.inventario_bienes = inventario_temp

# ==============================================================================
# INTERFAZ PRINCIPAL CON PESTAÑAS EN STREAMLIT
# ==============================================================================
st.title("📦 SISTEMA INTEGRAL DE ALMACÉN Y KARDEX - ONPE")
st.markdown("---")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📝 Registrar", 
    "📊 Stock y Guardado", 
    "📤 Salidas (Fraccionado)", 
    "🔍 Gerencia, Subgerencia y Seguimiento", 
    "📋 Kardex (Fraccionado)"
])

# --- PESTAÑA 1: REGISTRAR ---
with tab1:
    st.subheader("Registro de Operaciones Dinámico")
    tipo_pedido = st.selectbox("Tipo de Operación:", ['ENTREGA (SALIDA A ÁREA)', 'INGRESO (COMPRA/ADQUISICIÓN)', 'BAJA (BAJA PATRIMONIAL / MERMA)'])
    
    col1, col2 = st.columns(2)
    if "ENTREGA" in tipo_pedido:
        with col1: portador = st.text_input("Portador", placeholder="Ej. Juan Pérez")
        with col2: area = st.text_input("Área", placeholder="Ej. Subgerencia")
    elif "INGRESO" in tipo_pedido:
        with col1: pecosa_val = st.text_input("Nro PECOSA")
        with col2: orden_compra_val = st.text_input("Nro O/C")
    else:
        with col1: motivo_baja = st.text_input("Motivo de Baja", placeholder="Ej. Deterioro, rotura, merma")
        with col2: st.empty()

    buscar_prod = st.text_input("Filtrar producto para registrar:")
    opciones_prod = {f"{i['producto']} (Stock: {i['stock']})": i['producto'] for i in st.session_state.inventario_bienes if not buscar_prod or buscar_prod.lower() in i['producto'].lower()}
    
    prod_seleccionado_label = st.selectbox("Producto:", options=list(opciones_prod.keys()) if opciones_prod else ["No encontrado"])
    cantidad_op = st.number_input("Cantidad:", min_value=1, value=1)
    
    if 'carrito_items' not in st.session_state:
        st.session_state.carrito_items = []

    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        if st.button("➕ Agregar al Carrito"):
            if prod_seleccionado_label and prod_seleccionado_label != "No encontrado":
                nombre_prod = opciones_prod[prod_seleccionado_label]
                prod_obj = next((i for i in st.session_state.inventario_bienes if i['producto'] == nombre_prod), None)
                if prod_obj:
                    st.session_state.carrito_items.append({"nombre": prod_obj['producto'], "cant": cantidad_op})
                    st.success(f"Agregado: {prod_obj['producto']}")

    st.markdown("**Resumen del Carrito:**")
    if st.session_state.carrito_items:
        for idx_c, itm in enumerate(st.session_state.carrito_items):
            st.text(f"• {itm['nombre']} x {itm['cant']}")
        
        if st.button("💾 Procesar Transacción"):
            for itm in st.session_state.carrito_items:
                for prod in st.session_state.inventario_bienes:
                    if prod['producto'] == itm['nombre']:
                        if "INGRESO" in tipo_pedido:
                            prod['stock'] += itm['cant']
                        else:
                            prod['stock'] -= itm['cant']
                        prod['movimientos'].append({
                            "tipo": tipo_pedido,
                            "cantidad": itm['cant'],
                            "saldo": prod['stock'],
                            "detalle": "Transacción web Streamlit"
                        })
            st.session_state.carrito_items.clear()
            st.success("¡Transacción procesada con éxito!")
            st.rerun()
    else:
        st.caption("(Vacío)")

# --- PESTAÑA 2: STOCK Y GUARDADO ---
with tab2:
    st.subheader("Stock Actual y Guardado en Excel")
    if st.button("💾 Guardar Stock Actualizado a Excel"):
        data_export = [{
            "Categoría": i['categoria'],
            "Producto": i['producto'],
            "Proveedor": i['proveedor'],
            "Inventario Inicial": i['stock'],
            "Unidad Medida": i['unidad']
        } for i in st.session_state.inventario_bienes]
        df_export = pd.DataFrame(data_export)
        df_export.to_excel('stock_actualizado.xlsx', index=False)
        st.success("¡Archivo 'stock_actualizado.xlsx' guardado exitosamente!")

    df_stock_view = pd.DataFrame([{
        "Categoría": i['categoria'],
        "Producto": i['producto'],
        "Proveedor": i['proveedor'],
        "Inventario Inicial": i['stock'],
        "Unidad Medida": i['unidad']
    } for i in st.session_state.inventario_bienes])
    st.dataframe(df_stock_view, use_container_width=True)

# --- PESTAÑA 3: SALIDAS FRACCIONADAS ---
with tab3:
    st.subheader("Filtros Fraccionados de Salidas")
    if not df_movimientos_global.empty:
        lista_personal = ['[TODOS]'] + sorted(df_movimientos_global['Guía de remisión'].dropna().unique().tolist())
        lista_prod_salida = ['[TODOS]'] + sorted(df_movimientos_global['Descripción del Producto'].dropna().unique().tolist())
        
        f_pers = st.selectbox("Personal / Guía:", lista_personal)
        f_prod = st.selectbox("Producto de Salida:", lista_prod_salida)
        
        df_f = df_movimientos_global.copy()
        if f_pers != '[TODOS]':
            df_f = df_f[df_f['Guía de remisión'] == f_pers]
        if f_prod != '[TODOS]':
            df_f = df_f[df_f['Descripción del Producto'] == f_prod]
            
        st.write(f"Resultados encontrados: {len(df_f)}")
        st.dataframe(df_f, use_container_width=True)
    else:
        st.warning("No hay datos de movimientos cargados.")

# --- PESTAÑA 4: CONSULTA AVANZADA POR ARCHIVOS DE SEGUIMIENTO Y GERENCIAS ---
with tab4:
    st.subheader("Consulta por Gerencia / Subgerencia y Requerimientos")
    st.markdown("Seleccione el archivo de seguimiento y busque lo solicitado por cada órgano, gerencia o subgerencia con sus cabeceras limpias y correctas.")
    
    if dict_seguimiento_global:
        archivo_sel = st.selectbox("Seleccionar Archivo / Proceso:", options=list(dict_seguimiento_global.keys()))
        df_actual = dict_seguimiento_global[archivo_sel]
        
        if not df_actual.empty:
            busqueda_seg = st.text_input("🔍 Buscar órgano, subgerencia, producto, descripción o detalle:")
            
            df_filtrado = df_actual.copy()
            if busqueda_seg:
                mask = df_filtrado.astype(str).apply(lambda x: x.str.contains(busqueda_seg, case=False, na=False)).any(axis=1)
                df_filtrado = df_filtrado[mask]
                
            st.write(f"Registros encontrados: {len(df_filtrado)}")
            st.dataframe(df_filtrado, use_container_width=True)
            
            # Botón de descarga
            csv_data = df_filtrado.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Descargar este resultado en CSV",
                data=csv_data,
                file_name=f"reporte_{archivo_sel.lower().replace(' ', '_')}.csv",
                mime="text/csv"
            )
        else:
            st.warning("El archivo seleccionado está vacío.")
    else:
        st.warning("No se encontraron los nuevos archivos de seguimiento en el directorio.")

# --- PESTAÑA 5: KARDEX FRACCIONADO ---
with tab5:
    st.subheader("Kardex con Filtros Fraccionados")
    lista_kardex_categorias = ['[TODOS]'] + sorted(list(set(i['categoria'] for i in st.session_state.inventario_bienes)))
    lista_kardex_proveedores = ['[TODOS]'] + sorted(list(set(i['proveedor'] for i in st.session_state.inventario_bienes if i['proveedor'])))
    
    k_cat = st.selectbox("Categoría Kardex:", lista_kardex_categorias)
    k_prov = st.selectbox("Proveedor Kardex:", lista_kardex_proveedores)
    k_buscar = st.text_input("Buscar producto en Kardex:")
    
    opts_k = []
    for i in st.session_state.inventario_bienes:
        m_txt = not k_buscar or k_buscar.lower() in i['producto'].lower()
        m_cat = k_cat == '[TODOS]' or i['categoria'] == k_cat
        m_prov = k_prov == '[TODOS]' or i['proveedor'] == k_prov
        if m_txt and m_cat and m_prov:
            opts_k.append((i['producto'], i['producto']))
            
    prod_k_sel = st.selectbox("Seleccione Producto para ver Kardex:", options=[o[1] for o in opts_k], format_func=lambda x: next((o[0] for o in opts_k if o[1] == x), ""))
    
    if prod_k_sel:
        prod_data = next((i for i in st.session_state.inventario_bienes if i['producto'] == prod_k_sel), None)
        if prod_data:
            st.markdown(f"**Producto:** {prod_data['producto']}")
            st.markdown(f"**Categoría:** {prod_data['categoria']} | **Proveedor:** {prod_data['proveedor']} | **Stock Actual:** {prod_data['stock']}")
            df_movs = pd.DataFrame(prod_data['movimientos'])
            st.dataframe(df_movs, use_container_width=True)