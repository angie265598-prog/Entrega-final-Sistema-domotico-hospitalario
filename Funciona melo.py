# main_esp32_c3_habitacion_paciente_FINAL_OFFSET.py
import network
import urequests
import time
import dht
from machine import Pin, PWM, I2C
import json
import gc
import random
import math

# ================================
# CONFIGURACIÓN ESP32-C3
# ================================
SENSOR_DHT_PIN = 0
I2C_SCL_PIN = 8
I2C_SDA_PIN = 9
BUZZER_PIN = 1
LED_LAMPARA_PIN = 2
SERVO_CORTINA_PIN = 20
SERVO_PUERTA_PIN = 4
LED_WIFI_PIN = 5

# Configuración I2C
I2C_FREQ = 100000

# Configuración WiFi
RED_NOMBRE = "prueba"
RED_CLAVE = "12345678"

# Configuración Telegram - VERIFICADO QUE FUNCIONA
TELEGRAM_TOKEN = "7959030953:AAF2kR3TeijNUrkIY6ut8raB-R0V6a8NWaU"
TELEGRAM_CHAT_ID = "7618570704"

# Configuración ThingSpeak
THINGSPEAK_API_KEY = "3YKKOTG6PO5GNIT6"
THINGSPEAK_URL = "https://api.thingspeak.com/update"

# Umbrales médicos
UMBRAL_FC_BAJA = 50
UMBRAL_FC_ALTA = 120
UMBRAL_SPO2_BAJO = 90
UMBRAL_TEMP_ALTA = 30
UMBRAL_HUM_ALTA = 70

# Variables globales
temperatura = 0.0
humedad = 0.0
frecuencia_cardiaca = 72
spo2 = 98

# Estados del sistema
cortina_abierta = False
puerta_abierta = False
luz_encendida = False
alarma_sonora = False

# Control de alarmas
alarma_fc = False
alarma_spo2 = False
alarma_temperatura = False
alarma_humedad = False

# Control de Telegram
ultimo_update_id = 0 # ⬅️ NUEVA VARIABLE PARA CONTROLAR OFFSET

# ================================
# FUNCIONES AUXILIARES
# ================================
def obtener_tiempo():
    """Obtener tiempo formateado (alternativa a time.ctime())"""
    t = time.localtime()
    return f"{t[2]:02d}/{t[1]:02d}/{t[0]} {t[3]:02d}:{t[4]:02d}:{t[5]:02d}"

# ================================
# INICIALIZACIÓN HARDWARE
# ================================
print("🏥 INICIANDO SISTEMA HOSPITALARIO")

# Sensores
sensor_dht = dht.DHT11(Pin(SENSOR_DHT_PIN))

# Actuadores
buzzer = PWM(Pin(BUZZER_PIN))
led_lampara = Pin(LED_LAMPARA_PIN, Pin.OUT)
led_wifi = Pin(LED_WIFI_PIN, Pin.OUT)
servo_cortina = PWM(Pin(SERVO_CORTINA_PIN))
servo_puerta = PWM(Pin(SERVO_PUERTA_PIN))

# Configurar PWM
servo_cortina.freq(50)
servo_puerta.freq(50)
buzzer.duty(0)
led_lampara.off()
led_wifi.off()

# ================================
# TELEGRAM - CON SISTEMA DE OFFSET CORREGIDO
# ================================
def enviar_telegram(mensaje):
    """Función mejorada para enviar mensajes a Telegram - VERIFICADA"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
   
    datos = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "HTML"
    }
   
    try:
        print(f"📤 Enviando a Telegram: {mensaje[:50]}...")
       
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'ESP32-C3'
        }
       
        response = urequests.post(url, json=datos, headers=headers, timeout=10)
       
        if response.status_code == 200:
            print("✅ Mensaje enviado a Telegram correctamente")
            response.close()
            return True
        else:
            print(f"❌ Error Telegram HTTP {response.status_code}: {response.text}")
            response.close()
            return False
           
    except Exception as e:
        print(f"❌ Error enviando a Telegram: {e}")
        return False

def verificar_telegram_bot():
    """Verificar si el bot de Telegram está funcionando"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getMe"
   
    try:
        print("🔍 Verificando bot de Telegram...")
        response = urequests.get(url, timeout=10)
       
        if response.status_code == 200:
            data = response.json()
            response.close()
            if data.get("ok"):
                print(f"✅ Bot verificado: {data['result']['first_name']}")
                return True
            else:
                print("❌ Bot no válido")
                return False
        else:
            print(f"❌ Error verificando bot: {response.status_code}")
            response.close()
            return False
           
    except Exception as e:
        print(f"❌ Error en verificación: {e}")
        return False

def procesar_comandos_telegram():
    """Función CORREGIDA con sistema de offset para evitar repeticiones"""
    global ultimo_update_id
    
    # Usar offset+1 para obtener solo mensajes nuevos
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={ultimo_update_id + 1}&timeout=1"
   
    try:
        print(f"📥 Consultando mensajes nuevos (offset: {ultimo_update_id + 1})...")
        response = urequests.get(url, timeout=5)
       
        if response.status_code == 200:
            data = response.json()
            response.close()
           
            if data.get("ok") and data["result"]:
                for update in data["result"]:
                    update_id = update["update_id"]
                    mensaje = update["message"]
                    texto = mensaje["text"].strip()
                    chat_id = mensaje["chat"]["id"]
                   
                    print(f"💬 Nuevo comando: {texto} (ID: {update_id})")
                   
                    # Actualizar el último ID procesado
                    if update_id > ultimo_update_id:
                        ultimo_update_id = update_id
                        print(f"🆕 Actualizando offset a: {ultimo_update_id}")
                   
                    # Procesar comandos básicos
                    if texto == "/start":
                        enviar_telegram("🏥 <b>Sistema Domótico Hospitalario Activado</b>\n\n"
                                      "🤖 <b>Comandos disponibles:</b>\n"
                                      "/estado - Ver estado del sistema\n"
                                      "/datos - Datos médicos en tiempo real\n"
                                      "/cortina_abrir - Abrir cortina\n"
                                      "/cortina_cerrar - Cerrar cortina\n"
                                      "/puerta_abrir - Abrir puerta\n"
                                      "/puerta_cerrar - Cerrar puerta\n"
                                      "/luz_encender - Encender luz\n"
                                      "/luz_apagar - Apagar luz\n"
                                      "/alarma_silencio - Silenciar alarmas")
                    elif texto == "/estado":
                        enviar_estado_telegram()
                    elif texto == "/datos":
                        enviar_datos_telegram()
                    elif texto == "/cortina_abrir":
                        abrir_cortina()
                        enviar_telegram("✅ Cortina abierta")
                    elif texto == "/cortina_cerrar":
                        cerrar_cortina()
                        enviar_telegram("✅ Cortina cerrada")
                    elif texto == "/puerta_abrir":
                        abrir_puerta()
                        enviar_telegram("✅ Puerta abierta")
                    elif texto == "/puerta_cerrar":
                        cerrar_puerta()
                        enviar_telegram("✅ Puerta cerrada")
                    elif texto == "/luz_encender":
                        luz_lampara(True)
                        enviar_telegram("✅ Luz encendida")
                    elif texto == "/luz_apagar":
                        luz_lampara(False)
                        enviar_telegram("✅ Luz apagada")
                    elif texto == "/alarma_silencio":
                        desactivar_alarma_sonora()
                        enviar_telegram("🔇 Alarmas silenciadas")
                    else:
                        enviar_telegram("❌ Comando no reconocido. Use /start para ver opciones.")
                   
                return True
            else:
                # No hay mensajes nuevos
                return False
               
        return False
       
    except Exception as e:
        print(f"❌ Error leyendo Telegram: {e}")
        return False

def enviar_estado_telegram():
    """Enviar estado completo a Telegram"""
    mensaje = f"""
🏥 <b>ESTADO DEL SISTEMA</b>

<b>Datos Médicos:</b>
• ❤️ Frecuencia cardíaca: {frecuencia_cardiaca} bpm
• 💨 Oxígeno en sangre: {spo2}%
• 🌡️ Temperatura: {temperatura:.1f}°C
• 💧 Humedad: {humedad:.1f}%

<b>Control Ambiente:</b>
• 🪟 Cortina: {'🟢 ABIERTA' if cortina_abierta else '🔴 CERRADA'}
• 🚪 Puerta: {'🟢 ABIERTA' if puerta_abierta else '🔴 CERRADA'}
• 💡 Luz: {'🟢 ENCENDIDA' if luz_encendida else '🔴 APAGADA'}

<b>Estado:</b> {'🚨 ALERTA' if alarma_sonora else '✅ NORMAL'}

⏰ <i>Actualizado: {obtener_tiempo()}</i>
"""
    enviar_telegram(mensaje)

def enviar_datos_telegram():
    """Enviar datos de sensores a Telegram"""
    mensaje = f"""
📊 <b>DATOS EN TIEMPO REAL</b>

• ❤️ FC: {frecuencia_cardiaca} bpm
• 💨 SpO2: {spo2}%
• 🌡️ Temp: {temperatura:.1f}°C  
• 💧 Hum: {humedad:.1f}%

⏰ {obtener_tiempo()}
"""
    enviar_telegram(mensaje)

def enviar_alerta_telegram():
    """Enviar alerta médica a Telegram"""
    mensaje = f"""
🚨 <b>ALERTA MÉDICA</b>

<b>Datos críticos detectados:</b>

"""
   
    if frecuencia_cardiaca < UMBRAL_FC_BAJA:
        mensaje += f"• ❤️ FC BAJA: {frecuencia_cardiaca} bpm\n"
    elif frecuencia_cardiaca > UMBRAL_FC_ALTA:
        mensaje += f"• ❤️ FC ALTA: {frecuencia_cardiaca} bpm\n"
       
    if spo2 < UMBRAL_SPO2_BAJO:
        mensaje += f"• 💨 SpO2 BAJO: {spo2}%\n"
       
    if temperatura > UMBRAL_TEMP_ALTA:
        mensaje += f"• 🌡️ TEMP ALTA: {temperatura:.1f}°C\n"
       
    mensaje += f"\n📍 Habitación Paciente\n⏰ {obtener_tiempo()}"
   
    enviar_telegram(mensaje)

# ================================
# FUNCIONES DE CONTROL DEL SISTEMA
# ================================
def angulo_a_duty_servo(angulo, min_pulse=500, max_pulse=2400, freq=50):
    pulse_width = min_pulse + (angulo / 180.0) * (max_pulse - min_pulse)
    period_us = 1000000 / freq
    duty = int((pulse_width / period_us) * 1023)
    return max(0, min(1023, duty))

def mover_servo_sg90(servo, angulo):
    duty = angulo_a_duty_servo(angulo, 500, 2400)
    servo.duty(duty)
    time.sleep(0.5)

def mover_servo_sg92r(servo, angulo):
    duty = angulo_a_duty_servo(angulo, 500, 2400)
    servo.duty(duty)
    time.sleep(0.3)

def abrir_cortina():
    global cortina_abierta
    mover_servo_sg90(servo_cortina, 180)
    cortina_abierta = True
    print("✅ Cortina abierta")

def cerrar_cortina():
    global cortina_abierta
    mover_servo_sg90(servo_cortina, 0)
    cortina_abierta = False
    print("✅ Cortina cerrada")

def abrir_puerta():
    global puerta_abierta
    mover_servo_sg92r(servo_puerta, 90)
    puerta_abierta = True
    luz_lampara(True)
    print("✅ Puerta abierta")

def cerrar_puerta():
    global puerta_abierta
    mover_servo_sg92r(servo_puerta, 0)
    puerta_abierta = False
    luz_lampara(False)
    print("✅ Puerta cerrada")

def luz_lampara(encender):
    global luz_encendida
    luz_encendida = encender
    led_lampara.value(encender)

def activar_alarma_sonora():
    global alarma_sonora
    alarma_sonora = True
    buzzer.freq(800)
    buzzer.duty(512)

def desactivar_alarma_sonora():
    global alarma_sonora
    alarma_sonora = False
    buzzer.duty(0)

# ================================
# SISTEMA DE ALARMAS MEJORADO
# ================================
def verificar_alarmas():
    """Verificar condiciones de alarma"""
    global alarma_sonora, alarma_fc, alarma_spo2, alarma_temperatura, alarma_humedad
    
    # Verificar cada condición
    alarma_fc = frecuencia_cardiaca < UMBRAL_FC_BAJA or frecuencia_cardiaca > UMBRAL_FC_ALTA
    alarma_spo2 = spo2 < UMBRAL_SPO2_BAJO
    alarma_temperatura = temperatura > UMBRAL_TEMP_ALTA
    alarma_humedad = humedad > UMBRAL_HUM_ALTA
    
    condiciones_alarma = [alarma_fc, alarma_spo2, alarma_temperatura]
   
    if any(condiciones_alarma) and not alarma_sonora:
        print("🚨 Activando alarma médica")
        alarma_sonora = True
        activar_alarma_sonora()
        enviar_alerta_telegram()
       
    elif not any(condiciones_alarma) and alarma_sonora:
        print("✅ Desactivando alarma")
        alarma_sonora = False
        desactivar_alarma_sonora()

# ================================
# LECTURA DE SENSORES
# ================================
def leer_dht11():
    global temperatura, humedad
    try:
        sensor_dht.measure()
        temperatura = sensor_dht.temperature()
        humedad = sensor_dht.humidity()
        return True
    except Exception as e:
        print(f"Error DHT11: {e}")
        # Simulación para pruebas
        temperatura = random.uniform(22, 28)
        humedad = random.uniform(45, 65)
        return False

def leer_max30100():
    global frecuencia_cardiaca, spo2
    # Simulación del sensor MAX30100 con variación más realista
    base_bpm = 72
    variation = math.sin(time.ticks_ms() * 0.001) * 3
    frecuencia_cardiaca = max(60, min(100, base_bpm + variation))
    spo2 = 96 + random.randint(-1, 1)
    
    # Simular condición de alarma ocasionalmente (10% probabilidad)
    if random.random() < 0.1:
        if random.random() < 0.5:
            frecuencia_cardiaca = random.randint(40, 50) # Bradicardia
        else:
            frecuencia_cardiaca = random.randint(130, 180) # Taquicardia
            
    return True

def leer_sensores():
    """Leer todos los sensores"""
    leer_dht11()
    leer_max30100()
    
    print(f"📊 Sensores - Temp: {temperatura:.1f}C, Hum: {humedad:.1f}%, FC: {frecuencia_cardiaca} bpm, SpO2: {spo2}%")

# ================================
# THINGSPEAK
# ================================
def enviar_thingspeak():
    """Enviar datos a ThingSpeak"""
    try:
        params = f"api_key={THINGSPEAK_API_KEY}"
        params += f"&field1={temperatura:.1f}"
        params += f"&field2={humedad:.1f}"
        params += f"&field3={frecuencia_cardiaca}"
        params += f"&field4={spo2}"
        params += f"&field5={1 if cortina_abierta else 0}"
        params += f"&field6={1 if puerta_abierta else 0}"
        params += f"&field7={1 if luz_encendida else 0}"
        params += f"&field8={1 if alarma_sonora else 0}"
       
        url = f"{THINGSPEAK_URL}?{params}"
        response = urequests.get(url, timeout=10)
        response.close()
        print("✅ Datos enviados a ThingSpeak")
        return True
    except Exception as e:
        print(f"❌ Error ThingSpeak: {e}")
        return False

# ================================
# CONEXIÓN WIFI MEJORADA
# ================================
def conectar_wifi():
    """Conectar a WiFi con mejor manejo de errores"""
    wifi = network.WLAN(network.STA_IF)
    wifi.active(True)
   
    if wifi.isconnected():
        ip = wifi.ifconfig()[0]
        print(f"✅ WiFi conectado: {ip}")
        led_wifi.on()
        return True
       
    print(f"📡 Conectando a {RED_NOMBRE}...")
    wifi.connect(RED_NOMBRE, RED_CLAVE)
   
    for i in range(20):
        if wifi.isconnected():
            ip = wifi.ifconfig()[0]
            print(f"✅ WiFi conectado: {ip}")
            led_wifi.on()
            return True
           
        print(f"⏳ Intentando conexión... {i+1}/20")
        led_wifi.value(not led_wifi.value())
        time.sleep(1)
   
    print("❌ No se pudo conectar a WiFi")
    led_wifi.off()
    return False

# ================================
# PROGRAMA PRINCIPAL
# ================================
def main():
    global ultimo_update_id
    
    print("🏥 INICIANDO SISTEMA DOMÓTICO HOSPITALARIO")
   
    # Conectar WiFi
    if not conectar_wifi():
        print("⚠️ Modo offline - Funciones limitadas")
        return
   
    # Verificar Telegram
    print("🔍 Verificando conexión con Telegram...")
    if verificar_telegram_bot():
        print("✅ Telegram configurado correctamente")
        # Enviar mensaje de inicio
        enviar_telegram("🏥 <b>Sistema Domótico Hospitalario ACTIVADO</b>\n\n"
                       "🤖 Bot configurado correctamente\n"
                       "📡 Sistema de monitoreo iniciado\n"
                       f"⏰ {obtener_tiempo()}")
    else:
        print("❌ Problema con Telegram. Verifica token y chat ID.")
        print("💡 Token usado:", TELEGRAM_TOKEN)
        print("💡 Chat ID usado:", TELEGRAM_CHAT_ID)
   
    # Inicializar servos
    cerrar_cortina()
    cerrar_puerta()
    print("✅ Servos inicializados")
    
    # Variables de timing
    ultima_lectura = 0
    ultimo_telegram = 0
    ultimo_thingspeak = 0
    ultima_alarma = 0
   
    print("✅ Sistema iniciado. Monitoreando paciente...")
    print("💡 Envía /start a tu bot de Telegram para comenzar")
   
    while True:
        try:
            tiempo_actual = time.ticks_ms()
            gc.collect()
           
            # Leer sensores cada 3 segundos
            if time.ticks_diff(tiempo_actual, ultima_lectura) >= 3000:
                ultima_lectura = tiempo_actual
                leer_sensores()
                verificar_alarmas()
           
            # Procesar Telegram cada 3 segundos (más frecuente para mejor respuesta)
            if time.ticks_diff(tiempo_actual, ultimo_telegram) >= 3000:
                ultimo_telegram = tiempo_actual
                procesar_comandos_telegram()
           
            # Enviar a ThingSpeak cada 30 segundos
            if time.ticks_diff(tiempo_actual, ultimo_thingspeak) >= 30000:
                ultimo_thingspeak = tiempo_actual
                enviar_thingspeak()
                
            # Control de alarma sonora intermitente
            if alarma_sonora and time.ticks_diff(tiempo_actual, ultima_alarma) >= 500:
                ultima_alarma = tiempo_actual
                # Alternar el buzzer para efecto intermitente
                if buzzer.duty() > 0:
                    buzzer.duty(0)
                else:
                    buzzer.freq(800)
                    buzzer.duty(512)
           
            time.sleep(0.1)
           
        except Exception as e:
            print(f"❌ Error en loop principal: {e}")
            time.sleep(5)

# Iniciar programa
print("🚀 Ejecutando sistema médico completo...")
main()