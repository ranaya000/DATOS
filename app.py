import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- CONFIGURACIÓN DE LA CONEXIÓN A GOOGLE SHEETS ---
@st.cache_resource
def conectar_gsheets():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    # Carga las credenciales desde los secretos de Streamlit Cloud
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    return client

# Conectarse y abrir la hoja (Asegúrate de que el nombre del Google Sheet sea exactamente "BD_Movimientos")
try:
    client = conectar_gsheets()
    sheet_name = "BD_Movimientos" # Cambia esto si tu Google Sheet tiene otro nombre exacto
    spreadsheet = client.open(sheet_name)
    
    # Hojas de trabajo (Pestañas)
    ws_movimientos = spreadsheet.worksheet("Movimientos")
    ws_stock = spreadsheet.worksheet("Stock")
except Exception as e:
    st.error(f"Error al conectar con Google Sheets: {e}")
    st.stop()

# --- INTERFAZ DE STREAMLIT ---
st.title("📦 Sistema de Control de Almacén - ONPE")

# 1. CARGAR DATOS DESDE GOOGLE SHEETS
try:
    data_stock = pd.DataFrame(ws_stock.get_all_records())
    data_movimientos = pd.DataFrame(ws_movimientos.get_all_records())
except Exception as e:
    st.warning("Las pestañas 'Movimientos' o 'Stock' están vacías o tienen nombres diferentes.")
    data_stock = pd.DataFrame()
    data_movimientos = pd.DataFrame()

# Menú lateral
menu = st.sidebar.selectbox("Menú", ["Registrar Movimiento", "Ver Stock Actual", "Historial de Movimientos"])

if menu == "Registrar Movimiento":
    st.subheader("Registro de Entradas y Salidas")
    
    if not data_stock.empty:
        # Asegúrate de que las columnas coincidan con las de tu Google Sheet
        productos = data_stock["Producto"].tolist() if "Producto" in data_stock.columns else []
        
        tipo = st.selectbox("Tipo de Movimiento", ["Entrada", "Salida"])
        producto_sel = st.selectbox("Seleccione el Producto", productos)
        cantidad = st.number_input("Cantidad", min_value=1, value=1)
        
        if st.button("Guardar Operación"):
            # Registrar en la pestaña Movimientos
            nuevo_movimiento = [tipo, producto_sel, cantidad, str(pd.Timestamp.now())]
            ws_movimientos.append_row(nuevo_movimiento)
            
            # Actualizar el stock actual en la pestaña Stock
            # (Buscamos la fila del producto y sumamos/restamos según corresponda)
            cell = ws_stock.find(producto_sel)
            if cell:
                fila = cell.row
                # Asumiendo que la columna de Stock Actual es la 6 (columna F)
                stock_actual_col = 6 
                stock_actual = int(ws_stock.cell(fila, stock_actual_col).value or 0)
                
                if tipo == "Entrada":
                    nuevo_stock = stock_actual + cantidad
                else:
                    nuevo_stock = stock_actual - cantidad
                    if nuevo_stock < 0:
                        nuevo_stock = 0 # Evitar negativos
                
                ws_stock.update_cell(fila, stock_actual_col, nuevo_stock)
                st.success(f"¡Movimiento registrado y Stock actualizado automáticamente en la nube!")
            else:
                st.error("No se encontró el producto en la hoja de stock.")
    else:
        st.error("La tabla de stock está vacía. Verifica tu Google Sheet.")

elif menu == "Ver Stock Actual":
    st.subheader("Inventario Actual en la Nube")
    if not data_stock.empty:
        st.dataframe(data_stock, use_container_width=True)
    else:
        st.info("No hay datos en la pestaña Stock.")

elif menu == "Historial de Movimientos":
    st.subheader("Historial de Entradas y Salidas")
    if not data_movimientos.empty:
        st.dataframe(data_movimientos, use_container_width=True)
    else:
        st.info("Aún no hay movimientos registrados.")
