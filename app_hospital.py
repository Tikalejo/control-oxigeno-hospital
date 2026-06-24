import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Configuración de la página
st.set_page_config(page_title="Control de Oxígeno - Hospital San Martín", page_icon="🩺", layout="wide")

# Estilos CSS personalizados
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .titulo-contenedor {
        display: flex;
        align-items: center;
        justify-content: center;
        background-color: #004b87; /* Azul Institucional */
        color: white;
        padding: 30px;
        border-radius: 8px;
        margin-bottom: 25px;
        font-family: Arial, sans-serif;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .tarjeta-stock {
        padding: 22px;
        border-radius: 12px;
        color: white;
        margin-bottom: 18px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.08);
        font-family: Arial, sans-serif;
    }
    .stock-seguro { background-color: #2ea44f; }
    .stock-medio { background-color: #f39c12; }
    .stock-critico { background-color: #d9383a; }
    
    .numero-stock {
        font-size: 42px;
        font-weight: bold;
        margin: 5px 0;
    }
    .desglose-stock {
        font-size: 15px;
        background-color: rgba(255, 255, 255, 0.2);
        padding: 10px;
        border-radius: 6px;
        margin-top: 10px;
        line-height: 1.5;
    }
    .detalle-tarjeta {
        font-size: 13px;
        opacity: 0.9;
        margin-top: 5px;
    }
    </style>
""", unsafe_allow_html=True)

DB_FILE = "movimientos_oxigeno.csv"

# Configuración de Activos del Hospital
TIPOS_TUBOS = ["10,7m3", "Compact", "Tackeo"]
ACCIONES = ["Entrega al Servicio", "Retira del Servicio", "Recarga"]
SERVICIOS = ["Guardia", "UCO", "UDE", "UTI", "Stock"]
AGENTES = ["Rivero", "Ruben Arrua"]

TOTALES_PROPIOS = {
    "10,7m3": 28,
    "Compact": 36,
    "Tackeo": 6
}

# Inicializar la base de datos si no existe
if not os.path.exists(DB_FILE):
    df_inicial = pd.DataFrame(columns=["Fecha y Hora", "Tipo de Tubo", "Acción Realizada", "Cantidad", "Servicio/Destino", "Agente / Operario"])
    df_inicial.to_csv(DB_FILE, index=False, encoding='utf-8')

def cargar_movimientos():
    try:
        df = pd.read_csv(DB_FILE, encoding='utf-8')
        return df
    except:
        return pd.DataFrame(columns=["Fecha y Hora", "Tipo de Tubo", "Acción Realizada", "Cantidad", "Servicio/Destino", "Agente / Operario"])

def registrar_movimiento(tipo, accion, cantidad, servicio, agente):
    df = cargar_movimientos()
    nueva_fila = {
        "Fecha y Hora": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "Tipo de Tubo": tipo,
        "Acción Realizada": accion,
        "Cantidad": int(cantidad),
        "Servicio/Destino": servicio,
        "Agente / Operario": agente
    }
    df = pd.concat([df, pd.DataFrame([nueva_fila])], ignore_index=True)
    df.to_csv(DB_FILE, index=False, encoding='utf-8')

# --- PROCESAMIENTO MATEMÁTICO INTEGRAL (CON DESGLOSE DE SERVICIOS) ---
# Partimos con todos los envases llenos en la Jaula y cero en las salas
stock_detallado = {
    "10,7m3": {"jaula": TOTALES_PROPIOS["10,7m3"], "en_uso": 0, "vacios": 0},
    "Compact": {"jaula": TOTALES_PROPIOS["Compact"], "en_uso": 0, "vacios": 0},
    "Tackeo": {"jaula": TOTALES_PROPIOS["Tackeo"], "en_uso": 0, "vacios": 0}
}

# Diccionario para controlar el stock exacto dentro de cada servicio por separado
stock_por_servicio = {
    tipo: {srv: 0 for srv in SERVICIOS} for tipo in TIPOS_TUBOS
}

df_movimientos = cargar_movimientos()

for _, row in df_movimientos.iterrows():
    tipo = row["Tipo de Tubo"]
    acc = row["Acción Realizada"]
    cant = int(row["Cantidad"])
    srv = row["Servicio/Destino"]
    
    if tipo in stock_detallado:
        if acc == "Entrega al Servicio":
            stock_detallado[tipo]["jaula"] -= cant
            stock_detallado[tipo]["en_uso"] += cant
            stock_por_servicio[tipo][srv] += cant  # Suma al servicio específico
            
        elif acc == "Retira del Servicio":
            stock_detallado[tipo]["en_uso"] -= cant
            stock_detallado[tipo]["vacios"] += cant
            stock_por_servicio[tipo][srv] -= cant  # Resta del servicio específico
            
        elif acc == "Recarga":
            stock_detallado[tipo]["jaula"] += cant
            stock_detallado[tipo]["vacios"] = max(0, stock_detallado[tipo]["vacios"] - cant)

# --- CABECERA ---
col_logo, col_titulo = st.columns([3, 5])
with col_logo:
    if os.path.exists("logo_hospital.png"):
        st.image("logo_hospital.png", width=340)
    else:
        st.markdown("<h1 style='text-align: center; margin-top: 15px; font-size: 90px;'>🏥</h1>", unsafe_allow_html=True)

with col_titulo:
    st.markdown('<div class="titulo-contenedor"><h1 style="margin:0; text-align:center; font-size: 28px;">CONTROL DE STOCK Y MOVIMIENTOS DE OXÍGENO</h1></div>', unsafe_allow_html=True)

# --- CUERPO DEL PROGRAMA ---
col_izq, col_der = st.columns([1, 1], gap="large")

with col_izq:
    st.markdown("### 📊 ESTADO ACTUAL DE ENVASES")
    
    for tipo in TIPOS_TUBOS:
        jaula = stock_detallado[tipo]["jaula"]
        uso = stock_detallado[tipo]["en_uso"]
        vacios = stock_detallado[tipo]["vacios"]
        total_envases = TOTALES_PROPIOS[tipo]
        
        if jaula <= (total_envases * 0.25):
            clase_color = "stock-critico"
            status_texto = "🚨 ¡ALERTA: PEDIR RECARGA URGENTE!"
        elif jaula <= (total_envases * 0.50):
            clase_color = "stock-medio"
            status_texto = "⚠ STOCK MEDIO - CONTROLAR"
        else:
            clase_color = "stock-seguro"
            status_texto = "✔ DEPOSITOS SEGUROS"
            
        nombre_tarjeta = "TUBO 10,7m³" if tipo == "10,7m3" else f"TUBO {tipo.upper()}"
        
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
        
        # Consultar cuántos tubos de este tipo tiene la sala seleccionada actualmente
        tubos_en_esta_sala = stock_por_servicio[tipo_sel][servicio_sel]
        
        st.write("")
        bot_guardar = st.button("💾 GUARDAR REGISTRO", use_container_width=True, type="primary")
        
        if bot_guardar:
            # --- CANDADOS DE SEGURIDAD ABSOLUTOS ---
            if accion_sel == "Entrega al Servicio" and cantidad > stock_detallado[tipo_sel]["jaula"]:
                st.error(f"❌ Error físico: No podés entregar {cantidad} tubos. Solo quedan {stock_detallado[tipo_sel]['jaula']} llenos en la jaula.")
                
            elif accion_sel == "Retira del Servicio" and cantidad > tubos_en_esta_sala:
                # NUEVO CANDADO SOLICITADO: Bloqueo estricto por sala específica
                st.error(f"❌ Bloqueo por Servicio: No podés retirar {cantidad} tubo(s) de {servicio_sel} porque el sistema registra que actualmente esa sala tiene solo {tubos_en_esta_sala} tubo(s) en uso.")
                
            elif accion_sel == "Recarga" and cantidad > stock_detallado[tipo_sel]["vacios"]:
                st.error(f"❌ Bloqueo de Seguridad: No podés registrar una recarga de {cantidad} tubos porque en la jaula solo hay {stock_detallado[tipo_sel]['vacios']} envases vacíos disponibles para cambiar.")
                
            else:
                registrar_movimiento(tipo_sel, accion_sel, cantidad, servicio_sel, agente_nombre)
                st.success("¡Movimiento asentado y stock actualizado en tiempo real!")
                st.balloons() 
                st.rerun()

st.write("")
st.divider()
st.markdown("### 📋 HISTORIAL COMPLETO DE MOVIMIENTOS")
if not df_movimientos.empty: 
    st.dataframe(df_movimientos.iloc[::-1], use_container_width=True)
else: 
    st.info("El historial está limpio. El sistema asume que los 28, 36 y 6 envases están llenos en la jaula esperando su primera entrega.")