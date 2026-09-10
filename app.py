import streamlit as st
import pandas as pd
import requests

# Pega aquí la URL que te dio Google Apps Script
WEB_APP_URL = "PEGA_AQUÍ_TU_URL_DE_APPS_SCRIPT"

st.set_page_config(page_title="Sistema de Almacén - ONPE", page_icon="📦", layout="wide")

@st.cache_data(ttl=5)
def cargar_datos():
    try:
        response = requests.get(WEB_APP_URL)
        data = response.json()
        
        # Procesar Stock
        stock_rows = data["stock"]
        df_stock = pd.DataFrame(stock_rows[1:], columns=stock_rows[0])
        
        # Procesar Movimientos
        mov_rows = data["movimientos"]
        if len(mov_rows) > 1:
            df_mov = pd.DataFrame(mov_rows[1:], columns=mov_rows[0])
        else:
            df_mov = pd.DataFrame(columns=["Tipo", "Producto", "Cantidad", "Fecha"])
            
        return df_stock, df_mov
    except Exception as e:
        st.error(f"Error al conectar con la API de Google Sheets: {e}")
        return pd.DataFrame(), pd.DataFrame()

data_stock, data_movimientos = cargar_datos()

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
            payload = {
                "tipo": tipo,
                "producto": producto_sel,
                "cantidad": cantidad,
                "fecha": str(pd.Timestamp.now())
            }
            try:
                res = requests.post(WEB_APP_URL, json=payload)
                if res.status_code == 200:
                    st.success("¡Operación guardada y sincronizada en Google Sheets! 🎉")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Error al registrar en el servidor de Google.")
            except Exception as e:
                st.error(f"Error de conexión: {e}")
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
        st.info("Aún no hay movimientos registrados.")
