# ==============================================================================
# LÓGICA DE NEGOCIO Y CARGA DE DATOS CORREGIDA
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

    # Cargar movimientos si existe
    try:
        df_movimientos_init = pd.read_excel('movimientos.xlsx')
    except Exception:
        pass

    # Cargar stock (busca primero un archivo dedicado de stock, si no existe usa el consolidado)
    for archivo_stock in ['stock_actualizado.xlsx', 'stock_2.xlsx', 'GITE - EG 2026 (SEP) 2026 (1)-PARA SEGUIMIENTO -30-06-2026.xlsx']:
        try:
            xls_s = pd.ExcelFile(archivo_stock)
            sheet_s = xls_s.sheet_names[0]
            for s in xls_s.sheet_names:
                if 'biene' in s.lower() or 'stock' in s.lower():
                    sheet_s = s
                    break
            df_stock = pd.read_excel(archivo_stock, sheet_name=sheet_s)
            if not df_stock.empty:
                break
        except Exception:
            pass

    return dict_seguimiento, df_movimientos_init, df_stock

dict_seguimiento_global, df_movimientos_init_global, df_stock_global = cargar_datos_sistema()

# Función auxiliar robusta para mapear columnas del Excel de stock
def obtener_columna_flexible(row, posibles_nombres, valor_por_defecto=""):
    for col in posibles_nombres:
        for c in row.index:
            if str(c).strip().lower() == col.lower():
                val = row[c]
                if pd.notna(val) and str(val).strip() != "":
                    return val
    return valor_por_defecto

if 'inventario_bienes' not in st.session_state:
    inventario_temp = []
    if not df_stock_global.empty:
        for idx, r in df_stock_global.iterrows():
            # Buscar campos clave con múltiples variantes de nombres de columnas
            prod = str(obtener_columna_flexible(r, ['Producto', 'Descripción', 'Descripcion', 'Descripción del Producto', 'Bien', 'Item', 'Artículo', 'PRODUCCION'], '')).strip().upper()
            cat = str(obtener_columna_flexible(r, ['Categoría', 'Categoria', 'Cat.', 'CATEGORÍA PRESUPUESTAL'], 'GENERAL')).strip().upper()
            prov = str(obtener_columna_flexible(r, ['Proveedor', 'Proveedor / Marca', 'Marca', 'PROVEEDOR'], '')).strip().upper()
            unid = str(obtener_columna_flexible(r, ['Unidad Medida', 'Unidad de Medida', 'Unidad', 'UM', 'UNIDAD DE MEDIDA'], 'UNIDAD')).strip().upper()
            
            try:
                stock_ini = float(obtener_columna_flexible(r, ['Inventario Inicial', 'Inventario_Inicial', 'Stock Inicial', 'Stock_Inicial', 'CANTIDAD', 'STOCK'], 0.0) or 0.0)
            except:
                stock_ini = 0.0
                
            try:
                stock_act = float(obtener_columna_flexible(r, ['Stock Actual', 'Stock_Actual', 'Stock'], stock_ini) or stock_ini)
            except:
                stock_act = stock_ini

            if prod and prod != 'NAN':
                item = {
                    "id_fila": idx + 1,
                    "categoria": cat,
                    "producto": prod,
                    "proveedor": prov,
                    "unidad": unid,
                    "stock_inicial": stock_ini,
                    "stock_actual": stock_act
                }
                inventario_temp.append(item)
    st.session_state.inventario_bienes = inventario_temp