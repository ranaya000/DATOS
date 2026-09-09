def obtener_columna_flexible(row, posibles_nombres, valor_por_defecto=""):
    import unicodedata
    def limpiar_texto(txt):
        if not isinstance(txt, str):
            txt = str(txt)
        return ''.join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn').strip().lower()

    # Mapear columnas limpias del row
    row_cleaned_keys = {limpiar_texto(c): c for c in row.index}
    
    for nombre in posibles_nombres:
        nombre_limpio = limpiar_texto(nombre)
        # 1. Búsqueda exacta limpia
        for k_limpio, k_real in row_cleaned_keys.items():
            if nombre_limpio == k_limpio:
                val = row[k_real]
                if pd.notna(val) and str(val).strip() != "":
                    return val
        # 2. Búsqueda parcial (contiene)
        for k_limpio, k_real in row_cleaned_keys.items():
            if nombre_limpio in k_limpio or k_limpio in nombre_limpio:
                val = row[k_real]
                if pd.notna(val) and str(val).strip() != "":
                    return val
    return valor_por_defecto

if 'inventario_bienes' not in st.session_state:
    inventario_temp = []
    if not df_stock_global.empty:
        # Mostrar las columnas detectadas en la consola de Streamlit para diagnóstico si gustas
        st.write("Columnas detectadas en el Excel de Stock:", list(df_stock_global.columns))
        
        for idx, r in df_stock_global.iterrows():
            prod = str(obtener_columna_flexible(r, ['producto', 'descripcion', 'bien', 'item', 'articulo', 'detalle'], '')).strip().upper()
            cat = str(obtener_columna_flexible(r, ['categoria', 'cat', 'clasificacion'], 'GENERAL')).strip().upper()
            prov = str(obtener_columna_flexible(r, ['proveedor', 'marca', 'fabricante'], '')).strip().upper()
            unid = str(obtener_columna_flexible(r, ['unidad', 'medida', 'um', 'unid'], 'UNIDAD')).strip().upper()
            
            try:
                stock_ini = float(obtener_columna_flexible(r, ['inventario inicial', 'stock inicial', 'inicial', 'cantidad', 'stock_inicial'], 0.0) or 0.0)
            except:
                stock_ini = 0.0
                
            try:
                stock_act = float(obtener_columna_flexible(r, ['stock actual', 'stock_actual', 'actual', 'stock', 'saldo'], stock_ini) or stock_ini)
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