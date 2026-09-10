import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Sistema de Almacén - ONPE", page_icon="📦", layout="wide")

@st.cache_resource
def conectar_gsheets():
    try:
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        
        spreadsheet = client.open("BD_Movimientos")
        return spreadsheet
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

spreadsheet = conectar_gsheets()

if not spreadsheet:
    st.stop()

try:
    ws_movimientos = spreadsheet.worksheet("Movimientos")
    ws_stock = spreadsheet.worksheet("Stock")
    
    data_stock = pd.DataFrame(ws_stock.get_all_records())
    data_movimientos = pd.DataFrame(ws_movimientos.get_all_records())
except Exception as e:
    st.error(f"Error al leer las hojas: {e}")
    st.stop()

st.title("📦 Sistema de Control de Almacén - ONPE")
st.markdown("---")

menu = st.sidebar.selectbox("Menú", ["Registrar Movimiento", "Ver Stock Actual", "Historial de Movimientos"])

if menu == "Registrar Movimiento":
    st.subheader("Registro Automático en la Nube")
    
    if not data_stock.empty:
        productos = data_stock["Producto"].tolist() if "Producto" in data_stock.columns else []
        
        tipo = st.selectbox("Tipo de Movimiento", ["Entrada", "Salida"])
        producto_sel = st.selectbox("Seleccione el Producto", productos)
        cantidad = st.number_input("Cantidad", min_value=1, value=1)
        
        if st.button("Guardar Operación Automáticamente"):
            try:
                nuevo_movimiento = [tipo, producto_sel, cantidad, str(pd.Timestamp.now())]
                ws_movimientos.append_row(nuevo_movimiento)
                
                cell = ws_stock.find(producto_sel)
                if cell:
                    fila = cell.row
                    stock_actual_col = 6 
                    val_actual = ws_stock.cell(fila, stock_actual_col).value
                    stock_actual = int(val_actual) if val_actual and str(val_actual).isdigit() else 0
                    
                    if tipo == "Entrada":
                        nuevo_stock = stock_actual + cantidad
                    else:
                        nuevo_stock = stock_actual - cantidad
                        if nuevo_stock < 0:
                            nuevo_stock = 0
                            
                    ws_stock.update_cell(fila, stock_actual_col, nuevo_stock)
                    st.success("¡Operación guardada y sincronizada en tu Google Sheets! 🎉")
                    st.rerun()
                else:
                    st.error("No se encontró el producto en la hoja de stock.")
            except Exception as e:
                st.error(f"Error al guardar: {e}")
    else:
        st.error("La tabla de stock está vacía.")

elif menu == "Ver Stock Actual":
    st.subheader("Inventario Actual en Tiempo Real")
    if not data_stock.empty:
        st.dataframe(data_stock, use_container_width=True)
    else:
        st.info("No hay datos en stock.")

elif menu == "Historial de Movimientos":
    st.subheader("Historial de Operaciones")
    if not data_movimientos.empty:
        st.dataframe(data_movimientos, use_container_width=True)
    else:
        st.info("Aún no hay movimientos.")
