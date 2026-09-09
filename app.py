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
# LÓGICA DE NEGOCIO Y CARGA DE DATOS
# ==============================================================================
@st.cache_data
def cargar_datos_sistema():
    df_pecosas = pd.DataFrame()
    df_movimientos = pd.DataFrame()
    
    try:
        df_pecosas = pd.read_excel('ORDENES DE COMPRA.xlsx', header=2)
        df_pecosas['PECOSA'] = df_pecosas['PECOSA'].fillna('').astype(str).str.replace('.0', '', regex=False)
        df_pecosas['SUBGERENCIA'] = df_pecosas['SUBGERENCIA'].fillna('GENERAL').astype(str)
        df_pecosas['Tipo de PPTO'] = df_pecosas['Tipo de PPTO'].fillna('GENERAL').astype(str)
        df_pecosas['DESCRIPCION'] = df_pecosas['DESCRIPCION'].fillna('').astype(str)
    except Exception:
        pass

    try:
        df_movimientos = pd.read_excel('movimientos.xlsx')
        df_movimientos['Guía de remisión'] = df_movimientos['Guía de remisión'].fillna('').astype(str)
        df_movimientos['Descripción del Producto'] = df_movimientos['Descripción del Producto'].fillna('').astype(str)
    except Exception:
        pass

    return df_pecosas, df_movimientos

df_pecosas_global, df_movimientos_global = cargar_datos_sistema()

def extraer_factor(unidad_str):
    unidad_str = str(unidad_str).upper()
    if "UNIDAD" in unidad_str and not any(char.isdigit() for char in unidad_str):
        return 1
    match = re.search(r'(\d+)', unidad_str)
    if match:
        return int(match.group(1))
    return 1

def determinar_categoria(texto):
    texto = str(texto).upper()
    if any(k in texto for k in ['CABLE', 'USB', 'IMPRESORA', 'DISCO', 'KVM', 'PANTALLA', 'LAPTOP', 'COMPUT', 'RED', 'ROUTER', 'TECLADO', 'MOUSE', 'MONITOR', 'TONER', 'TINTA', 'RESINA']):
        return 'CÓMPUTO Y TECNOLOGÍA'
    elif any(k in texto for k in ['CLIP', 'PLUMON', 'BOLIGRAFO', 'LAPICERO', 'CUADERNO', 'PAPEL', 'FOLDER', 'SOBRE', 'TICKETERA', 'ETIQUETA', 'GOMA', 'CINTA ADHESIVA', 'SELLO']):
        return 'ÚTILES Y OFICINA'
    elif any(k in texto for k in ['CINTA', 'METAL', 'TALADRO', 'MARTILLO', 'LLAVE', 'DESTORNILLADOR', 'CABLE ELECTRICO', 'FOCO', 'INTERRUPTOR', 'TUBERIA', 'VALVULA']):
        return 'FERRETERÍA Y MANTENIMIENTO'
    elif any(k in texto for k in ['ESCOBA', 'LEJIA', 'DETERGENTE', 'PAPEL HIGIENICO', 'DISPENSER', 'ALCOHOL', 'TOALLA']):
        return 'LIMPIEZA E HIGIENE'
    else:
        return 'GENERAL / OTROS'

# Inicializar inventario en sesión
if 'inventario_bienes' not in st.session_state:
    productos_unicos = set()
    if not df_movimientos_global.empty:
        for _, r in df_movimientos_global.iterrows():
            productos_unicos.add((str(r['Descripción del Producto']).strip().upper(), str(r['Proveedor']).strip().upper(), str(r['Unidad Medida']).strip().upper(), float(r['Costo unitario'])))
    
    if not df_pecosas_global.empty:
        for _, r in df_pecosas_global.iterrows():
            desc = str(r.get('DESCRIPCION', '')).strip().upper()
            if desc and desc != 'NAN':
                marca = str(r.get('MARCA', 'GENERICO')).strip().upper()
                unid = str(r.get('UNIDAD DE MEDIDA', 'UNIDAD')).strip().upper()
                precio = float(r.get('PRECIO UNITARIO', 0.0) or 0.0)
                productos_unicos.add((desc, marca, unid, precio))

    inventario_temp = []
    idx = 1
    for prod, prov, unid, costo in sorted(productos_unicos):
        factor = extraer_factor(unid)
        categoria = determinar_categoria(prod)
        item = {
            "id_fila": idx,
            "codigo": f"PROD-{idx:03d}",
            "categoria": categoria,
            "producto": prod,
            "proveedor": prov,
            "costo": costo,
            "unidad": unid,
            "factor": factor,
            "stock": 1000.0,
            "movimientos": [{
                "tipo": "INVENTARIO INICIAL",
                "cantidad": 1000.0,
                "saldo": 1000.0,
                "detalle": "Carga inicial automática"
            }]
        }
        inventario_temp.append(item)
        idx += 1
        
    if not df_movimientos_global.empty:
        for _, m in df_movimientos_global.iterrows():
            p_nombre = str(m['Descripción del Producto']).strip().upper()
            cant_salida = float(m['Cantidad'])
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
    "🔍 PECOSAS (Fraccionado)", 
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
    else:
        with col1: pecosa_val = st.text_input("Nro PECOSA")
        with col2: orden_compra_val = st.text_input("Nro O/C")

    buscar_prod = st.text_input("Filtrar producto para registrar:")
    opciones_prod = {f"[{i['codigo']}] {i['producto']} (Stock: {i['stock']})": i['codigo'] for i in st.session_state.inventario_bienes if not buscar_prod or buscar_prod.lower() in i['producto'].lower()}
    
    prod_seleccionado_label = st.selectbox("Producto:", options=list(opciones_prod.keys()) if opciones_prod else ["No encontrado"])
    cantidad_op = st.number_input("Cantidad:", min_value=1, value=1)
    
    if 'carrito_items' not in st.session_state:
        st.session_state.carrito_items = []

    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        if st.button("➕ Agregar al Carrito"):
            if prod_seleccionado_label and prod_seleccionado_label != "No encontrado":
                cod = opciones_prod[prod_seleccionado_label]
                prod_obj = next((i for i in st.session_state.inventario_bienes if i['codigo'] == cod), None)
                if prod_obj:
                    st.session_state.carrito_items.append({"codigo": cod, "nombre": prod_obj['producto'], "cant": cantidad_op})
                    st.success(f"Agregado: {prod_obj['producto']}")

    st.markdown("**Resumen del Carrito:**")
    if st.session_state.carrito_items:
        for idx_c, itm in enumerate(st.session_state.carrito_items):
            st.text(f"• [{itm['codigo']}] {itm['nombre']} x {itm['cant']}")
        
        if st.button("💾 Procesar Transacción"):
            for itm in st.session_state.carrito_items:
                for prod in st.session_state.inventario_bienes:
                    if prod['codigo'] == itm['codigo']:
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
            "CODIGO": i['codigo'],
            "CATEGORIA": i['categoria'],
            "PRODUCTO": i['producto'],
            "PROVEEDOR": i['proveedor'],
            "COSTO": i['costo'],
            "UNIDAD": i['unidad'],
            "STOCK_ACTUAL": i['stock']
        } for i in st.session_state.inventario_bienes]
        df_export = pd.DataFrame(data_export)
        df_export.to_excel('stock_actualizado.xlsx', index=False)
        st.success("¡Archivo 'stock_actualizado.xlsx' guardado exitosamente!")

    df_stock_view = pd.DataFrame([{
        "CÓDIGO": i['codigo'],
        "CATEGORÍA": i['categoria'],
        "PRODUCTO": i['producto'],
        "PROVEEDOR": i['proveedor'],
        "STOCK": i['stock']
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

# --- PESTAÑA 4: PECOSAS Y COMPRAS ---
with tab4:
    st.subheader("Filtros Fraccionados de PECOSAS y Compras")
    if not df_pecosas_global.empty:
        lista_subg = ['[TODOS]'] + sorted(df_pecosas_global['SUBGERENCIA'].dropna().unique().tolist())
        lista_pecosas = ['[TODOS]'] + sorted(df_pecosas_global['PECOSA'].dropna().unique().tolist(), key=lambda x: str(x))
        lista_ppto = ['[TODOS]'] + sorted(df_pecosas_global['Tipo de PPTO'].dropna().unique().tolist())
        
        c_p1, c_p2, c_p3 = st.columns(3)
        with c_p1: f_subg = st.selectbox("Subgerencia:", lista_subg)
        with c_p2: f_pec = st.selectbox("N° PECOSA:", lista_pecosas)
        with c_p3: f_ppto = st.selectbox("Tipo PPTO:", lista_ppto)
        
        df_f_p = df_pecosas_global.copy()
        if f_subg != '[TODOS]': df_f_p = df_f_p[df_f_p['SUBGERENCIA'] == f_subg]
        if f_pec != '[TODOS]': df_f_p = df_f_p[df_f_p['PECOSA'] == str(f_pec)]
        if f_ppto != '[TODOS]': df_f_p = df_f_p[df_f_p['Tipo de PPTO'] == f_ppto]
        
        st.write(f"Resultados encontrados: {len(df_f_p)}")
        st.dataframe(df_f_p, use_container_width=True)
    else:
        st.warning("No hay datos de PECOSAS cargados.")

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
            opts_k.append((f"[{i['codigo']}] {i['producto']}", i['codigo']))
            
    prod_k_sel = st.selectbox("Seleccione Producto para ver Kardex:", options=[o[1] for o in opts_k], format_func=lambda x: next((o[0] for o in opts_k if o[1] == x), ""))
    
    if prod_k_sel:
        prod_data = next((i for i in st.session_state.inventario_bienes if i['codigo'] == prod_k_sel), None)
        if prod_data:
            st.markdown(f"**Producto:** {prod_data['producto']}")
            st.markdown(f"**Categoría:** {prod_data['categoria']} | **Proveedor:** {prod_data['proveedor']} | **Stock Actual:** {prod_data['stock']}")
            df_movs = pd.DataFrame(prod_data['movimientos'])
            st.dataframe(df_movs, use_container_width=True)