import streamlit as st
import pandas as pd
import io
import unicodedata
from datetime import datetime

# ==============================================================================
# CONFIGURACIÓN INICIAL
# ==============================================================================
st.set_page_config(page_title="Sistema de Almacén - ONPE", page_icon="📦", layout="wide")

# ID de tu Google Sheet y URLs dinámicas para leer TODO el contenido actual
SPREADSHEET_ID = "1F8e71glxH_3FaMUzdkUkIW_17qw_INT74249qwarpQ"
URL_MOVIMIENTOS = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet=Movimientos"
URL_STOCK = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet=Stock"

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
# CARGA TOTAL Y DINÁMICA DESDE GOOGLE SHEETS (SIN CACHÉ ESTÁTICA)
# ==============================================================================
def cargar_todo_desde_excel():
    df_movs = pd.DataFrame()
    df_stk = pd.DataFrame()
    
    try:
        # Forzamos lectura fresca agregando un parámetro de tiempo aleatorio para evitar caché de Google/Streamlit
        import time
        timestamp = int(time.time())
        url_m = f"{URL_MOVIMIENTOS}&_t={timestamp}"
        url_s = f"{URL_STOCK}&_t={timestamp}"
        
        df_movs = pd.read_csv(url_m)
        df_stk = pd.read_csv(url_s)
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets: {e}")
        
    return df_movs, df_stk

df_movs_web, df_stock_web = cargar_todo_desde_excel()

def limpiar_texto(txt):
    if not isinstance(txt, str):
        txt = str(txt)
    return ''.join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn').strip().lower()

def obtener_columna_flexible(row, posibles_nombres, valor_por_defecto=""):
    row_cleaned_keys = {limpiar_texto(str(c)): c for c in row.index}
    for nombre in posibles_nombres:
        nombre_limpio = limpiar_texto(nombre)
        for k_limpio, k_real in row_cleaned_keys.items():
            if nombre_limpio == k_limpio or nombre_limpio in k_limpio or k_limpio in nombre_limpio:
                val = row[k_real]
                if pd.notna(val) and str(val).strip() != "" and str(val).lower() != "nan":
                    return val
    return valor_por_defecto

# Sincronizar siempre con TODO lo que venga de la pestaña Stock
inventario_temp = []
if not df_stock_web.empty:
    for idx, r in df_stock_web.iterrows():
        prod = str(obtener_columna_flexible(r, ['producto', 'descripcion', 'descripcion del producto', 'bien', 'item', 'articulo'], '')).strip().upper()
        if prod and prod != 'NAN':
            cat = str(obtener_columna_flexible(r, ['categoria', 'cat', 'clasificacion'], 'GENERAL')).strip().upper()
            prov = str(obtener_columna_flexible(r, ['proveedor', 'marca', 'fabricante'], '')).strip().upper()
            unid = str(obtener_columna_flexible(r, ['unidad', 'medida', 'um', 'unid', 'unidad medida'], 'UNIDAD')).strip().upper()
            
            try:
                stock_ini = float(obtener_columna_flexible(r, ['inventario inicial', 'stock inicial', 'inicial', 'cantidad'], 0.0) or 0.0)
            except:
                stock_ini = 0.0
                
            try:
                stock_act = float(obtener_columna_flexible(r, ['stock actual', 'stock_actual', 'actual', 'stock', 'saldo'], stock_ini) or stock_ini)
            except:
                stock_act = stock_ini

            inventario_temp.append({
                "id_fila": idx + 1,
                "categoria": cat,
                "producto": prod,
                "proveedor": prov,
                "unidad": unid,
                "stock_inicial": stock_ini,
                "stock_actual": stock_act
            })
st.session_state.inventario_bienes = inventario_temp

# Sincronizar siempre con TODO lo que venga de la pestaña Movimientos
movs_iniciales = []
if not df_movs_web.empty:
    for _, row in df_movs_web.iterrows():
        d_dict = {str(k).strip(): v for k, v in row.to_dict().items() if pd.notna(v) and str(v).lower() != "nan"}
        if d_dict:
            movs_iniciales.append(d_dict)
st.session_state.historial_movimientos = movs_iniciales

if 'carrito_operaciones' not in st.session_state:
    st.session_state.carrito_operaciones = []

# ==============================================================================
# INTERFAZ PRINCIPAL
# ==============================================================================
st.title("📦 SISTEMA INTEGRAL DE ALMACÉN Y KARDEX - ONPE")
st.markdown("---")

col_sup1, col_sup2 = st.columns([1, 1])
with col_sup1:
    if st.button("🔄 ACTUALIZAR Y LEER TODO EL EXCEL AHORA"):
        st.success("¡Datos actualizados directamente desde Google Sheets!")
        st.rerun()

with col_sup2:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_stock_exp = pd.DataFrame([{
            "Categoría": i['categoria'],
            "Producto": i['producto'],
            "Proveedor": i['proveedor'],
            "Unidad Medida": i['unidad'],
            "Inventario Inicial": i['stock_inicial'],
            "Stock Actual": i['stock_actual']
        } for i in st.session_state.inventario_bienes])
        df_stock_exp.to_excel(writer, sheet_name='Stock', index=False)
        
        if st.session_state.historial_movimientos:
            df_movs_exp = pd.DataFrame(st.session_state.historial_movimientos)
            df_movs_exp.to_excel(writer, sheet_name='Movimientos', index=False)
            
    processed_data = output.getvalue()
    st.download_button(
        label="📥 DESCARGAR REPORTE GENERAL EN EXCEL",
        data=processed_data,
        file_name="reporte_general_almacen_onpe.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

st.markdown("---")

tab1, tab2, tab3 = st.tabs([
    "📝 Registrar", 
    "📊 Stock y Guardado", 
    "📤 Movimientos (Entradas, Salidas y Bajas)"
])

# --- PESTAÑA 1: REGISTRAR ---
with tab1:
    st.subheader("Registro de Operaciones (Entrada, Salida o Baja)")
    tipo_operacion = st.selectbox("Tipo de Operación:", ['SALIDA (ENTREGA A ÁREA)', 'INGRESO (COMPRA/ADQUISICIÓN)', 'BAJA (MERMA/DETERIORO)'])
    
    personal_solicitante = ""
    fecha_operacion = datetime.now().date()
    orden_compra = ""
    
    if "SALIDA" in tipo_operacion:
        col_op1, col_op2 = st.columns(2)
        with col_op1:
            personal_solicitante = st.text_input("Personal Solicitante", placeholder="Ej. Jorge Huamán")
        with col_op2:
            fecha_operacion = st.date_input("Fecha de salida", value=datetime.now().date())
            
    elif "INGRESO" in tipo_operacion:
        col_op1, col_op2 = st.columns(2)
        with col_op1:
            orden_compra = st.text_input("Orden de Compra", placeholder="Ej. O/C 456")
        with col_op2:
            fecha_operacion = st.date_input("Fecha de ingreso", value=datetime.now().date())
            
    else:  # BAJA
        col_op1, col_op2 = st.columns(2)
        with col_op1:
            motivo_baja = st.text_input("Motivo de la Baja", placeholder="Ej. Deterioro")
        with col_op2:
            fecha_operacion = st.date_input("Fecha de baja", value=datetime.now().date())

    buscar_prod_reg = st.text_input("Buscar palabra clave:")
    opciones_prod = {f"{i['producto']} (Stock Actual: {i['stock_actual']})": i['producto'] for i in st.session_state.inventario_bienes if not buscar_prod_reg or buscar_prod_reg.lower() in i['producto'].lower()}
    
    prod_seleccionado_label = st.selectbox("Seleccione Producto:", options=list(opciones_prod.keys()) if opciones_prod else ["No encontrado"])
    cantidad_op = st.number_input("Cantidad:", min_value=1, value=1)

    if st.button("➕ Agregar operación"):
        if prod_seleccionado_label and prod_seleccionado_label != "No encontrado":
            nombre_p = opciones_prod[prod_seleccionado_label]
            prod_obj = next((i for i in st.session_state.inventario_bienes if i['producto'] == nombre_p), None)
            if prod_obj:
                if ("SALIDA" in tipo_operacion or "BAJA" in tipo_operacion) and cantidad_op > prod_obj['stock_actual']:
                    st.error(f"¡Stock insuficiente! Stock actual de '{nombre_p}' es {prod_obj['stock_actual']}.")
                else:
                    st.session_state.carrito_operaciones.append({
                        "tipo_operacion": tipo_operacion,
                        "producto": nombre_p,
                        "cantidad": cantidad_op,
                        "personal_solicitante": personal_solicitante if "SALIDA" in tipo_operacion else "",
                        "orden_compra": orden_compra if "INGRESO" in tipo_operacion else "",
                        "fecha_operacion": str(fecha_operacion)
                    })
                    st.success(f"Añadido a operaciones: {nombre_p} ({cantidad_op})")

    st.markdown("**Resumen de operaciones:**")
    if st.session_state.carrito_operaciones:
        for idx_it, itm in enumerate(st.session_state.carrito_operaciones):
            cols_car = st.columns([6, 1])
            with cols_car[0]:
                st.text(f"• [{itm['tipo_operacion']}] {itm['producto']} - Cantidad: {itm['cantidad']} | Fecha: {itm['fecha_operacion']}")
            with cols_car[1]:
                if st.button("❌", key=f"del_carrito_{idx_it}"):
                    st.session_state.carrito_operaciones.pop(idx_it)
                    st.rerun()
        
        if st.button("💾 Confirmar y Aplicar Operaciones"):
            fecha_registro_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for itm in st.session_state.carrito_operaciones:
                for prod in st.session_state.inventario_bienes:
                    if prod['producto'] == itm['producto']:
                        if "INGRESO" in itm['tipo_operacion']:
                            prod['stock_actual'] += itm['cantidad']
                            t_reg = "Ingreso"
                        elif "SALIDA" in itm['tipo_operacion']:
                            prod['stock_actual'] -= itm['cantidad']
                            t_reg = "Salida"
                        else:
                            prod['stock_actual'] -= itm['cantidad']
                            t_reg = "Baja"
                        
                        nuevo_movimiento = {
                            "Fecha registro": fecha_registro_actual,
                            "Fecha operación": itm['fecha_operacion'],
                            "Personal solicitante": itm['personal_solicitante'] if t_reg == "Salida" else "",
                            "Orden de compra": itm['orden_compra'] if t_reg == "Ingreso" else "",
                            "Categoría": prod['categoria'],
                            "Descripción del Producto": prod['producto'],
                            "Proveedor": prod['proveedor'],
                            "Unidad Medida": prod['unidad'],
                            "Cantidad": itm['cantidad'],
                            "Tipo de registro": t_reg
                        }
                        st.session_state.historial_movimientos.append(nuevo_movimiento)
                        break
            
            st.session_state.carrito_operaciones.clear()
            st.success("¡Operaciones aplicadas correctamente!")
            st.rerun()
    else:
        st.caption("(Registro de operaciones vacío)")

# --- PESTAÑA 2: STOCK Y GUARDADO ---
with tab2:
    st.subheader("Stock Actual y Guardado (Todo el contenido del Excel)")
    
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
                "Proveedor": i['proveedor'],
                "Unidad Medida": i['unidad'],
                "Inventario Inicial": i['stock_inicial'],
                "Stock Actual": i['stock_actual']
            })
            
    df_stock_view = pd.DataFrame(data_stock_list)
    st.dataframe(df_stock_view, use_container_width=True)

# --- PESTAÑA 3: MOVIMIENTOS ---
with tab3:
    st.subheader("Historial General de Movimientos (Todo el contenido del Excel)")
    
    if st.session_state.historial_movimientos:
        lista_movs_limpia = [{str(k): v for k, v in m.items()} for m in st.session_state.historial_movimientos]
        df_movs_total = pd.DataFrame(lista_movs_limpia)
        if "Borrar" not in df_movs_total.columns:
            df_movs_total.insert(0, "Borrar", False)
        
        df_editado = st.data_editor(
            df_movs_total,
            use_container_width=True,
            column_config={"Borrar": st.column_config.CheckboxColumn("🗑️ Borrar", required=True)},
            disabled=[col for col in df_movs_total.columns if col != "Borrar"]
        )
        
        if st.button("🗑️ Eliminar registros seleccionados"):
            indices_a_borrar = df_editado[df_editado["Borrar"] == True].index.tolist()
            if indices_a_borrar:
                for idx in sorted(indices_a_borrar, reverse=True):
                    st.session_state.historial_movimientos.pop(idx)
                st.success("¡Registros eliminados correctamente!")
                st.rerun()
            else:
                st.warning("No has seleccionado ningún registro para borrar.")
    else:
        st.warning("No hay registros de movimientos disponibles en la hoja de cálculo.")
