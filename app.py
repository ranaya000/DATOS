import streamlit as st
import pandas as pd
from datetime import datetime

# Configuración de la página
st.set_page_config(page_title="Sistema de Almacén - ONPE", page_icon="📦", layout="wide")

# ==========================================
# 1. CONTROL DE ACCESO (LOGIN SEGURO)
# ==========================================
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False
    st.session_state['usuario'] = ""

def verificar_credenciales(user, password):
    # Credenciales autorizadas para la oficina
    usuarios_autorizados = {
        "admin_almacen": "onpe2026*",
        "asistente1": "clave123"
    }
    if user in usuarios_autorizados and usuarios_autorizados[user] == password:
        return True
    return False

if not st.session_state['autenticado']:
    st.markdown("## 🔐 Acceso Restringido - Sistema de Almacén ONPE")
    st.info("Ingrese sus credenciales autorizadas para acceder al sistema.")
    
    with st.form("form_login"):
        input_user = st.text_input("Usuario")
        input_pass = st.text_input("Contraseña", type="password")
        btn_login = st.form_submit_button("Ingresar al Sistema")
        
        if btn_login:
            if verificar_credenciales(input_user, input_pass):
                st.session_state['autenticado'] = True
                st.session_state['usuario'] = input_user
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")
    st.stop() # Detiene la ejecución si no está logueado

# ==========================================
# 2. CARGA DE DATOS Y BASE DE DATOS EN TIEMPO REAL
# ==========================================
if 'stock_db' not in st.session_state:
    try:
        # Intenta cargar tus Excel si están subidos en el repositorio
        df_mov = pd.read_excel('movimientos.xlsx')
        st.session_state['stock_db'] = df_mov
    except:
        # Datos de respaldo si los Excel no cargan directo
        st.session_state['stock_db'] = pd.DataFrame([
            {"CODIGO": "PROD-001", "CATEGORIA": "CÓMPUTO Y TECNOLOGÍA", "PRODUCTO": "ADAPTADOR DE HDMI MACHO VGA HEMBRA", "STOCK": 45, "COSTO": 25.50},
            {"CODIGO": "PROD-002", "CATEGORIA": "ÚTILES Y OFICINA", "PRODUCTO": "BOLIGRAFO TINTA SECA NEGRO", "STOCK": 200, "COSTO": 1.20},
            {"CODIGO": "PROD-003", "CATEGORIA": "FERRETERÍA Y MANTENIMIENTO", "PRODUCTO": "CINTA AISLANTE 3M", "STOCK": 80, "COSTO": 4.50}
        ])

if 'historial_movimientos' not in st.session_state:
    st.session_state['historial_movimientos'] = []

# ==========================================
# 3. INTERFAZ PRINCIPAL DEL SISTEMA
# ==========================================
st.sidebar.title(f"👤 Bienvenido, {st.session_state['usuario']}")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state['autenticado'] = False
    st.rerun()

st.title("📦 Sistema Integral de Almacén y Kardex - ONPE")
st.markdown("---")

pestana1, pestana2, pestana3 = st.tabs(["📝 Registrar Operación", "📊 Stock y Exportar a Excel", "📋 Historial en Tiempo Real"])

# PESTAÑA 1: REGISTRAR
with pestana1:
    st.subheader("Registro de Entradas / Salidas en Tiempo Real")
    
    df_actual = st.session_state['stock_db']
    tipo_op = st.selectbox("Tipo de Operación", ["ENTREGA (SALIDA A ÁREA)", "INGRESO (COMPRA)"])
    
    # Detecta dinámicamente la columna del producto según el Excel
    col_prod = 'PRODUCTO' if 'PRODUCTO' in df_actual.columns else 'Descripción del Producto'
    col_stock = 'STOCK' if 'STOCK' in df_actual.columns else 'Cantidad'
    
    prod_sel = st.selectbox("Seleccionar Producto", df_actual[col_prod].tolist())
    cantidad = st.number_input("Cantidad", min_value=1, value=1)
    responsable = st.text_input("Personal / Área Solicitante o Proveedor")
    
    if st.button("Procesar Transacción", type="primary"):
        idx = df_actual[df_actual[col_prod] == prod_sel].index[0]
        
        # Validación rápida si existe columna stock
        if col_stock in df_actual.columns:
            stock_actual = df_actual.at[idx, col_stock]
            if "ENTREGA" in tipo_op and cantidad > stock_actual:
                st.error(f"¡Stock insuficiente! Stock disponible: {stock_actual}")
            else:
                if "ENTREGA" in tipo_op:
                    df_actual.at[idx, col_stock] -= cantidad
                else:
                    df_actual.at[idx, col_stock] += cantidad
                
                st.success(f"Transacción procesada con éxito para {prod_sel}.")
                st.session_state['historial_movimientos'].append({
                    "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Tipo": tipo_op,
                    "Producto": prod_sel,
                    "Cantidad": cantidad,
                    "Responsable": responsable,
                    "Usuario Sistema": st.session_state['usuario']
                })

# PESTAÑA 2: STOCK Y EXPORTAR A EXCEL
with pestana2:
    st.subheader("Inventario Actualizado")
    st.dataframe(st.session_state['stock_db'], use_container_width=True)
    
    @st.cache_data
    def convertir_df_a_excel(df):
        from io import BytesIO
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Stock_Actual')
        return output.getvalue()

    excel_data = convertir_df_a_excel(st.session_state['stock_db'])
    
    st.download_button(
        label="📥 Exportar Stock Actual a Excel (.xlsx)",
        data=excel_data,
        file_name=f"stock_onpe_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# PESTAÑA 3: HISTORIAL
with pestana3:
    st.subheader("Auditoría de Movimientos")
    if len(st.session_state['historial_movimientos']) > 0:
        df_hist = pd.DataFrame(st.session_state['historial_movimientos'])
        st.dataframe(df_hist, use_container_width=True)
    else:
        st.info("Aún no se han registrado movimientos en esta sesión.")