import streamlit as st
import pandas as pd
import os
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# =========================================================================================
# CONFIGURACIÓN DE LA PÁGINA WEB Y ESTILOS VISUALES (AZUL INSTITUTIONAL)
# =========================================================================================
st.set_page_config(page_title="Control de Oxígeno - Hospital San Martín", page_icon="🩺", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .titulo-contenedor {
        display: flex; align-items: center; justify-content: center;
        background-color: #004b87; color: white; padding: 30px;
        border-radius: 8px; margin-bottom: 25px; font-family: Arial, sans-serif;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .tarjeta-stock {
        padding: 22px; border-radius: 12px; color: white;
        margin-bottom: 18px; box-shadow: 0 4px 6px rgba(0,0,0,0.08); font-family: Arial, sans-serif;
    }
    .stock-seguro { background-color: #2ea44f; }
    .stock-medio { background-color: #f39c12; }
    .stock-critico { background-color: #d9383a; }
    .numero-stock { font-size: 42px; font-weight: bold; margin: 5px 0; }
    .desglose-stock {
        font-size: 15px; background-color: rgba(255, 255, 255, 0.2);
        padding: 10px; border-radius: 6px; margin-top: 10px; line-height: 1.5;
    }
    .detalle-tarjeta { font-size: 13px; opacity: 0.9; margin-top: 5px; }
    
    /* Estilos para las alertas de tiempo de rotación */
    .alerta-tiempo-ok { background-color: #e6f4ea; color: #137333; padding: 6px; border-radius: 4px; font-weight: bold; }
    .alerta-tiempo-warn { background-color: #fef7e0; color: #b06000; padding: 6px; border-radius: 4px; font-weight: bold; }
    .alerta-tiempo-crit { background-color: #fce8e6; color: #c5221f; padding: 6px; border-radius: 4px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# =========================================================================================
# CONFIGURACIÓN DE ACTIVOS FIJOS Y NÓMINA DE SERVICIOS DEL HOSPITAL
# =========================================================================================
TIPOS_TUBOS = ["10,6m3", "Compact", "Tackeo"]
ACCIONES = ["Entrega al Servicio", "Retira del Servicio", "Recarga"]
SERVICIOS = [
    "1er Piso", "2do Piso", "3er Piso", "Alergia", "Cardiovascular", "Cardiología (consultorio)", "Cirugía Const.", 
    "Clínica nueva", "Dermatología", "Ecografía", "Gastroenterología", "Guardia", 
    "Guardia Covid", "Hemodiálisis", "Hemodinamia", "Hemoterapia", "Hospital de día", 
    "Odontología", "Oftalmología", "Otorrino", "Quirófano", "Rayos", "Resonador", 
    "Sala 5", "Stock", "Traumatología (9)", "Traumatología (10)", "Tomógrafo", "UCO", "UDE", 
    "Urología","UTI", "Vacunación"
]
AGENTES = ["Aquino, Héctor", "Arrúa, Rubén", "Barrios, Ignacio", "Castañeda, Roberto",
    "Martinez, Eduardo", "Obispo, Fabián", "Posdeley, Cesar", "Ramos, Alejandro", 
    "Rivero, Javier", "Soto, Nelson", "Tika, Alejo", "Veloz, Antonio"]

# Inventario físico inamovible (Activos netos del Hospital San Martín)
TOTALES_PROPIOS = {
    "10,6m3": 28,
    "Compact": 36,
    "Tackeo": 6
}

# =========================================================================================
# CONEXIÓN DIRECTA CON GOOGLE SHEETS (GOOGLE DRIVE)
# =========================================================================================
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_movimientos_web():
    try:
        # ttl="0s" evita la memoria caché para forzar la lectura del dato real al instante
        df = conn.read(ttl="0s")
        return df
    except:
        return pd.DataFrame(columns=["Fecha y Hora", "Tipo de Tubo", "Acción Realizada", "Cantidad", "Servicio/Destino", "Agente / Operario"])

def registrar_movimiento_web(tipo, accion, cantidad, servicio, agente):
    df_actual = cargar_movimientos_web()
    nueva_fila = {
        "Fecha y Hora": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "Tipo de Tubo": tipo,
        "Acción Realizada": accion,
        "Cantidad": int(cantidad),
        "Servicio/Destino": servicio,
        "Agente / Operario": agente
    }
    df_actual = pd.concat([df_actual, pd.DataFrame([nueva_fila])], ignore_index=True)
    conn.update(data=df_actual)

# =========================================================================================
# MOTOR MATEMÁTICO DE VASOS COMUNICANTES CERRADOS
# =========================================================================================
# Inicializamos el sistema asumiendo que los envases totales están originalmente llenos en la jaula
stock_detallado = {tipo: {"jaula": TOTALES_PROPIOS[tipo], "en_uso": 0, "vacios": 0} for tipo in TIPOS_TUBOS}
stock_por_servicio = {tipo: {srv: 0 for srv in SERVICIOS} for tipo in TIPOS_TUBOS}
fechas_ultimo_movimiento = {tipo: {srv: None for srv in SERVICIOS} for tipo in TIPOS_TUBOS}

df_movimientos = cargar_movimientos_web()

if not df_movimientos.empty:
    for _, row in df_movimientos.iterrows():
        tipo = str(row["Tipo de Tubo"]).strip()
        
        # Unificación histórica: Mapea registros viejos de "10,7m3" hacia el nuevo "10,6m3"
        if tipo == "10,7m3":
            tipo = "10,6m3"
            
        acc = str(row["Acción Realizada"]).strip()
        srv = str(row["Servicio/Destino"]).strip()
        fecha_str = str(row["Fecha y Hora"]).strip()
        
        # Blindaje contra celdas corruptas o vacías en la planilla
        if pd.isna(row["Tipo de Tubo"]) or tipo not in stock_detallado:
            continue
        try:
            cant = int(row["Cantidad"])
        except:
            continue
            
        try:
            fecha_dt = datetime.strptime(fecha_str, "%d/%m/%Y %H:%M")
        except:
            fecha_dt = datetime.now()
        
        # Ejecución de transiciones de estado cerradas
        if acc == "Entrega al Servicio":
            stock_detallado[tipo]["jaula"] -= cant
            stock_detallado[tipo]["en_uso"] += cant
            if srv in stock_por_servicio[tipo]:
                stock_por_servicio[tipo][srv] += cant
                fechas_ultimo_movimiento[tipo][srv] = fecha_dt
                
        elif acc == "Retira del Servicio":
            stock_detallado[tipo]["en_uso"] -= cant
            stock_detallado[tipo]["vacios"] += cant
            if srv in stock_por_servicio[tipo]:
                stock_por_servicio[tipo][srv] -= cant
                if stock_por_servicio[tipo][srv] <= 0:
                    fechas_ultimo_movimiento[tipo][srv] = None
                else:
                    fechas_ultimo_movimiento[tipo][srv] = fecha_dt
                    
        elif acc == "Recarga":
            stock_detallado[tipo]["jaula"] += cant
            stock_detallado[tipo]["vacios"] = max(0, stock_detallado[tipo]["vacios"] - cant)

# =========================================================================================
# ESTRUCTURA VISUAL DE LA INTERFAZ
# =========================================================================================
col_logo, col_titulo = st.columns([3, 5])
with col_logo:
    if os.path.exists("logo_hospital.png"):
        st.image("logo_hospital.png", width=340)
    else:
        st.markdown("<h1 style='text-align: center; margin-top: 15px; font-size: 90px;'>🏥</h1>", unsafe_allow_html=True)

with col_titulo:
    st.markdown('<div class="titulo-contenedor"><h1 style="margin:0; text-align:center; font-size: 28px;">CONTROL DE STOCK Y MOVIMIENTOS DE OXÍGENO</h1></div>', unsafe_allow_html=True)

col_izq, col_der = st.columns([1, 1], gap="large")

# --- BLOQUE IZQUIERDO: TARJETAS DE ESTADO ACTUAL ---
with col_izq:
    st.markdown("### 📊 ESTADO ACTUAL DE ENVASES")
    
    for tipo in TIPOS_TUBOS:
        jaula = stock_detallado[tipo]["jaula"]
        uso = stock_detallado[tipo]["en_uso"]
        vacios = stock_detallado[tipo]["vacios"]
        total_envases = TOTALES_PROPIOS[tipo]
        
        # Alertas basadas exclusivamente en la disponibilidad de tubos llenos listos en la Jaula
        if jaula <= (total_envases * 0.25):
            clase_color = "stock-critico"
            status_texto = "🚨 ¡ALERTA: PEDIR RECARGA URGENTE!"
        elif jaula <= (total_envases * 0.50):
            clase_color = "stock-medio"
            status_texto = "⚠ STOCK MEDIO - CONTROLAR"
        else:
            clase_color = "stock-seguro"
            status_texto = "✔ DEPOSITOS SEGUROS"
            
        nombre_tarjeta = "TUBO 10,6m³" if tipo == "10,6m3" else f"TUBO {tipo.upper()}"
        
        st.markdown(f"""
            <div class="tarjeta-stock {clase_color}">
                <h4 style="margin:0;">{nombre_tarjeta} (Total: {total_envases} envases)</h4>
                <div class="numero-stock">{jaula} <span style="font-size:22px;">Llenos en Jaula</span></div>
                <div class="desglose-stock">
                    📦 <b>En Jaula (Listos):</b> {jaula} uds.<br>
                    🏥 <b>En Uso (Distribuidos):</b> {uso} uds.<br>
                    🔄 <b>Vacíos acumulados:</b> {vacios} uds.
                </div>
                <div class="detalle-tarjeta">{status_texto}</div>
            </div>
        """, unsafe_allow_html=True)

# --- BLOQUE DERECHO: FORMULARIO DE REGISTRO CON CANDADOS ---
with col_der:
    st.markdown("### 📝 REGISTRAR MOVIMIENTO")
    with st.container(border=True):
        tipo_sel = st.selectbox("1. SELECCIONE TIPO DE TUBO:", TIPOS_TUBOS)
        accion_sel = st.radio("2. ACCIÓN QUE SE REALIZA:", ACCIONES)
        cantidad = st.number_input("3. CANTIDAD DE TUBOS:", min_value=1, value=1, step=1)
        
        if accion_sel == "Recarga":
            indice_servicio = SERVICIOS.index("Stock")
            servicio_sel = st.selectbox("4. SERVICIO / DESTINO:", SERVICIOS, index=indice_servicio)
        else:
            servicio_sel = st.selectbox("4. SERVICIO / DESTINO:", SERVICIOS)
        
        agente_nombre = st.selectbox("5. SELECCIONE EL AGENTE RESPONSABLE:", AGENTES)
        
        # Lectura de la cantidad retenida en la sala específica elegida
        tubos_en_esta_sala = stock_por_servicio[tipo_sel][servicio_sel]
        
        st.write("")
        bot_guardar = st.button("💾 GUARDAR EN LA NUBE", use_container_width=True, type="primary")
        
        if bot_guardar:
            # Validación Candado 1: Entrega física
            if accion_sel == "Entrega al Servicio" and cantidad > stock_detallado[tipo_sel]["jaula"]:
                st.error(f"❌ Error físico: No podés entregar {cantidad} tubos. Solo quedan {stock_detallado[tipo_sel]['jaula']} llenos en la jaula.")
                
            # Validación Candado 2: Retiro físico específico por sala
            elif accion_sel == "Retira del Servicio" and cantidad > tubos_en_esta_sala:
                st.error(f"❌ Bloqueo por Servicio: No podés retirar {cantidad} tubo(s) de {servicio_sel} porque el sistema registra que actualmente esa sala tiene solo {tubos_en_esta_sala} tubo(s) en uso.")
                
            # Validación Candado 3: Recarga del proveedor cerrado
            elif accion_sel == "Recarga" and cantidad > stock_detallado[tipo_sel]["vacios"]:
                st.error(f"❌ Bloqueo de Seguridad: No podés registrar una recarga de {cantidad} tubos porque en la jaula solo hay {stock_detallado[tipo_sel]['vacios']} envases vacíos disponibles para cambiar.")
                
            else:
                with st.spinner("Sincronizando con Google Drive..."):
                    registrar_movimiento_web(tipo_sel, accion_sel, cantidad, servicio_sel, agente_nombre)
                st.success("¡Movimiento asentado y stock actualizado en tiempo real!")
                st.balloons() 
                st.rerun()

st.write("")
st.divider()

# =========================================================================================
# LOCALIZADOR EN TIEMPO REAL Y ALERTAS DE ROTACIÓN POR ANTIGÜEDAD
# =========================================================================================
st.markdown("### 🔍 LOCALIZADOR DE ENVASES Y ALERTAS DE ROTACIÓN")
st.markdown("A continuación se detallan únicamente las salas que **tienen tubos físicamente retenidos** y el tiempo transcurrido desde su última interacción.")

ubicaciones_reales = []
fecha_hoy = datetime.now()

for tipo in TIPOS_TUBOS:
    for srv in SERVICIOS:
        cantidad_en_sala = stock_por_servicio[tipo][srv]
        
        # Filtramos solo lo que está distribuido en pabellones (excluyendo el depósito/jaula central)
        if cantidad_en_sala > 0 and srv != "Stock":
            fecha_ult = fechas_ultimo_movimiento[tipo][srv]
            
            if fecha_ult is not None:
                dias_quieto = (fecha_hoy - fecha_ult).days
                fecha_pantalla = fecha_ult.strftime("%d/%m/%Y")
            else:
                dias_quieto = 0
                fecha_pantalla = "Sin datos"
            
            # Semáforo de tiempos para control de obsolescencia / rotación
            if dias_quieto >= 60:
                alerta_html = f'<span class="alerta-tiempo-crit">🚨 CRÍTICO: {dias_quieto} días sin rotar</span>'
            elif dias_quieto >= 45:
                alerta_html = f'<span class="alerta-tiempo-warn">⚠ REVISAR: {dias_quieto} días quieto</span>'
            else:
                alerta_html = f'<span class="alerta-tiempo-ok">✔ OK: {dias_quieto} días</span>'
                
            ubicaciones_reales.append({
                "Tipo de Tubo": "10,6m³" if tipo == "10,6m3" else tipo,
                "Servicio / Ubicación": srv,
                "Cantidad en Sala": f"{cantidad_en_sala} unidades",
                "Último Ingreso": fecha_pantalla,
                "Estado de Rotación": alerta_html
            })

if ubicaciones_reales:
    df_ubicaciones = pd.DataFrame(ubicaciones_reales)
    st.write(df_ubicaciones.to_html(escape=False, index=False), unsafe_allow_html=True)
else:
    st.info("Todos los tubos del hospital están concentrados en la jaula de Stock (Llenos o Vacíos). No hay consumos activos en las salas.")

st.write("")
st.divider()

# =========================================================================================
# VISUALIZACIÓN DEL HISTORIAL DE MOVIMIENTOS
# =========================================================================================
st.markdown("### 📋 HISTORIAL COMPLETO DE MOVIMIENTOS")
if not df_movimientos.empty: 
    st.dataframe(df_movimientos.iloc[::-1], use_container_width=True)
else: 
    st.info("La planilla de Google Sheets está vacía en este momento. Registrá los primeros movimientos para iniciar el historial.")
