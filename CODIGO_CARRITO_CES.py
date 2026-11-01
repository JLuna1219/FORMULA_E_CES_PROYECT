import network
import socket
import time
from machine import Pin, PWM, Timer, ADC

# ============================================================
# CONFIGURACIÓN DE RED WIFI
# ============================================================
SSID = "S25 Ultra de jonathan"
PASSWORD = "Millon19"
PORT = 8080

# ============================================================
# CONFIGURACIÓN DE PINES - MOTORES
# ============================================================
IN1 = Pin(0, Pin.OUT)
IN2 = Pin(3, Pin.OUT)
IN3 = Pin(5, Pin.OUT)
IN4 = Pin(6, Pin.OUT)
ENB = PWM(Pin(8))
ENB.freq(1000)

# ============================================================
# CONFIGURACIÓN DE PINES - LUCES (74LS164)
# ============================================================
PIN_DATOS = Pin(16, Pin.OUT)
PIN_RELOJ = Pin(17, Pin.OUT)

# --- MAPEO DEFINITIVO DE LUCES ---
LUZ_DELANTERAS     = 0   # Qa
LUZ_DIR_DERECHA    = 1   # Qb
LUZ_DIR_IZQUIERDA  = 2   # Qc
LUZ_TRASERAS       = 3   # Qd

# ============================================================
# CONFIGURACIÓN DEL SENSOR DE LUZ (LDR) CON HISTÉRESIS
# ============================================================
LDR = ADC(Pin(26))          # GPIO 26 = ADC0
UMBRAL_BAJO = 270           # Por debajo de esto → ENCIENDE
UMBRAL_ALTO = 350           # Por encima de esto → APAGA
modo_automatico = False
luces_encendidas_por_ldr = False

# ============================================================
# ESTADO GLOBAL
# ============================================================
VELOCIDADES = {1: 30, 2: 50, 3: 80, 4: 100}
velocidad_B = 60
direccion_B = 0
estado_luces = 0

dir_derecha_activa = False
dir_izquierda_activa = False
parpadeo_encendido = False
timer_parpadeo = None

# --- Bandera de parada de emergencia ---
parada_emergencia = False

# ============================================================
# FUNCIONES DE MOTORES (con doble reenvío de luces en Motor A)
# ============================================================
def aplicar_pwm_B():
    if direccion_B == 0:
        ENB.duty_u16(0)
    else:
        valor_pwm = int((velocidad_B / 100) * 65535)
        ENB.duty_u16(valor_pwm)
    if direccion_B == 1:
        IN3.high(); IN4.low()
    elif direccion_B == -1:
        IN3.low(); IN4.high()
    else:
        IN3.low(); IN4.low()

def reenviar_luces_con_espera():
    actualizar_luces()
    time.sleep_ms(150)
    actualizar_luces()

def motorA_derecha():
    IN1.high()
    IN2.low()
    reenviar_luces_con_espera()
    print("Motor A (Giro): DERECHA")

def motorA_izquierda():
    IN1.low()
    IN2.high()
    reenviar_luces_con_espera()
    print("Motor A (Giro): IZQUIERDA")

def motorA_detener():
    IN1.low()
    IN2.low()
    reenviar_luces_con_espera()
    print("Motor A (Giro): CENTRADO")

# --- Versiones SILENCIOSAS para los trucos (sin reenvío de luces) ---
def motorA_derecha_silencioso():
    IN1.high()
    IN2.low()

def motorA_izquierda_silencioso():
    IN1.low()
    IN2.high()

def motorA_detener_silencioso():
    IN1.low()
    IN2.low()

def motorB_adelante():
    global direccion_B
    direccion_B = 1
    aplicar_pwm_B()
    print(f"Motor B (Tracción): ADELANTE al {velocidad_B}%")

def motorB_atras():
    global direccion_B
    direccion_B = -1
    aplicar_pwm_B()
    print(f"Motor B (Tracción): ATRÁS al {velocidad_B}%")

def motorB_detener():
    global direccion_B
    direccion_B = 0
    aplicar_pwm_B()
    print("Motor B (Tracción): DETENIDO")

def set_velocidad_B(opcion):
    global velocidad_B
    if opcion in VELOCIDADES:
        velocidad_B = VELOCIDADES[opcion]
        aplicar_pwm_B()
        print(f"Velocidad del Motor B cambiada al {velocidad_B}%")

# ============================================================
# FUNCIONES DE LUCES
# ============================================================
def enviar_bits(bits):
    PIN_RELOJ.low()
    time.sleep_us(5)
    for i in range(7, -1, -1):
        if (bits >> i) & 1:
            PIN_DATOS.high()
        else:
            PIN_DATOS.low()
        time.sleep_us(5)
        PIN_RELOJ.high()
        time.sleep_us(10)
        PIN_RELOJ.low()
        time.sleep_us(5)
    time.sleep_ms(2)

def actualizar_luces():
    enviar_bits(estado_luces)

def apagar_todas_luces():
    global estado_luces, dir_derecha_activa, dir_izquierda_activa
    estado_luces = 0
    dir_derecha_activa = False
    dir_izquierda_activa = False
    detener_parpadeo()
    for _ in range(3):
        enviar_bits(0x00)
    print("Todas las luces APAGADAS")

def encender_luz(posicion, nombre):
    global estado_luces
    estado_luces |= (1 << posicion)
    actualizar_luces()
    print(f"{nombre}: ENCENDIDA")

# ============================================================
# PARPADEO CON TIMER
# ============================================================
def callback_parpadeo(t):
    global parpadeo_encendido, estado_luces
    parpadeo_encendido = not parpadeo_encendido
    if dir_derecha_activa:
        if parpadeo_encendido:
            estado_luces |= (1 << LUZ_DIR_DERECHA)
        else:
            estado_luces &= ~(1 << LUZ_DIR_DERECHA)
    if dir_izquierda_activa:
        if parpadeo_encendido:
            estado_luces |= (1 << LUZ_DIR_IZQUIERDA)
        else:
            estado_luces &= ~(1 << LUZ_DIR_IZQUIERDA)
    actualizar_luces()

def iniciar_parpadeo():
    global timer_parpadeo
    if timer_parpadeo is None:
        timer_parpadeo = Timer()
        timer_parpadeo.init(period=500, mode=Timer.PERIODIC, callback=callback_parpadeo)

def detener_parpadeo():
    global timer_parpadeo
    if timer_parpadeo:
        timer_parpadeo.deinit()
        timer_parpadeo = None

def toggle_direccional_derecha():
    global dir_derecha_activa, dir_izquierda_activa, estado_luces
    dir_derecha_activa = not dir_derecha_activa
    if dir_derecha_activa:
        dir_izquierda_activa = False
        estado_luces &= ~(1 << LUZ_DIR_IZQUIERDA)
        iniciar_parpadeo()
        print("Direccional Derecha: PARPADEANDO")
    else:
        estado_luces &= ~(1 << LUZ_DIR_DERECHA)
        actualizar_luces()
        if not dir_izquierda_activa:
            detener_parpadeo()
        print("Direccional Derecha: APAGADA")

def toggle_direccional_izquierda():
    global dir_derecha_activa, dir_izquierda_activa, estado_luces
    dir_izquierda_activa = not dir_izquierda_activa
    if dir_izquierda_activa:
        dir_derecha_activa = False
        estado_luces &= ~(1 << LUZ_DIR_DERECHA)
        iniciar_parpadeo()
        print("Direccional Izquierda: PARPADEANDO")
    else:
        estado_luces &= ~(1 << LUZ_DIR_IZQUIERDA)
        actualizar_luces()
        if not dir_derecha_activa:
            detener_parpadeo()
        print("Direccional Izquierda: APAGADA")

# ============================================================
# FUNCIONES DEL LDR (CON HISTÉRESIS)
# ============================================================
def leer_luz():
    return LDR.read_u16()

def control_automatico_luces():
    global estado_luces, luces_encendidas_por_ldr
    if not modo_automatico:
        return
    valor = leer_luz()
    print(f"[LDR] Valor: {valor} | Bajo: {UMBRAL_BAJO} | Alto: {UMBRAL_ALTO}")
    if valor < UMBRAL_BAJO and not luces_encendidas_por_ldr:
        estado_luces |= (1 << LUZ_DELANTERAS)
        estado_luces |= (1 << LUZ_TRASERAS)
        luces_encendidas_por_ldr = True
        print("  → OSCURO: Encendiendo luces")
        actualizar_luces()
    elif valor > UMBRAL_ALTO and luces_encendidas_por_ldr:
        estado_luces &= ~(1 << LUZ_DELANTERAS)
        estado_luces &= ~(1 << LUZ_TRASERAS)
        luces_encendidas_por_ldr = False
        print("  → CLARO: Apagando luces")
        actualizar_luces()

def activar_modo_automatico(activar):
    global modo_automatico, luces_encendidas_por_ldr
    modo_automatico = activar
    if activar:
        print("Modo LDR: ACTIVADO")
        control_automatico_luces()
    else:
        luces_encendidas_por_ldr = False
        print("Modo LDR: DESACTIVADO")

def callback_ldr(t):
    if modo_automatico:
        control_automatico_luces()

timer_ldr = Timer()
timer_ldr.init(period=500, mode=Timer.PERIODIC, callback=callback_ldr)

# ============================================================
# MOVIMIENTOS AUTÓNOMOS CON PARADA DE EMERGENCIA
# ============================================================
def detener_todo():
    motorA_detener_silencioso()
    motorB_detener()
    actualizar_luces()

def fijar_velocidad_trucos():
    """Fija la velocidad del Motor B al 80% para todos los trucos."""
    global velocidad_B
    velocidad_B = 80
    aplicar_pwm_B()

def movimiento_circulo():
    """Vuelta completa: avanza y gira en círculo (hacia la IZQUIERDA) al 80%."""
    global parada_emergencia, velocidad_B
    parada_emergencia = False
    print("Movimiento: CÍRCULO")
    velocidad_B = 80
    motorB_adelante()
    motorA_derecha_silencioso()
    
    pasos = 31
    for _ in range(pasos):
        if parada_emergencia:
            print("¡Parada de emergencia durante CÍRCULO!")
            detener_todo()
            return
        time.sleep_ms(100)
    
    for v in [30, 15, 5, 0]:
        if parada_emergencia:
            break
        velocidad_B = v
        aplicar_pwm_B()
        time.sleep_ms(100)
    
    detener_todo()
    print("Círculo completado")

def movimiento_infinito():
    """Recorrido en forma de ∞ (8) con reenvío de PWM tras el pico de corriente."""
    global parada_emergencia, velocidad_B
    parada_emergencia = False
    print("Movimiento: INFINITO")
    
    # ============================================================
    # FASE 1: Primer lóbulo (giro a la DERECHA) - más tiempo
    # ============================================================
    velocidad_B = 60
    motorB_adelante()
    motorA_derecha_silencioso()
    for _ in range(40):  # 4000ms (antes 3000ms)
        if parada_emergencia:
            detener_todo(); return
        time.sleep_ms(100)
    
    # ============================================================
    # FASE 2: Pausa de enfriamiento (motor detenido)
    # ============================================================
    motorA_detener_silencioso()
    motorB_detener()
    for _ in range(2):  # 200ms
        if parada_emergencia:
            detener_todo(); return
        time.sleep_ms(100)
    
    # ============================================================
    # FASE 3: Segundo lóbulo (giro a la IZQUIERDA) - MUY lento
    # ============================================================
    velocidad_B = 35
    motorB_adelante()
    motorA_izquierda_silencioso()
    
    # Reenviar PWM después del pico de corriente (200ms)
    for _ in range(2):  # 200ms
        if parada_emergencia:
            detener_todo(); return
        time.sleep_ms(100)
    aplicar_pwm_B()  # Recordar la velocidad al Motor B
    
    # Continuar el segundo lóbulo
    for _ in range(50):  # 4800ms restantes (5000ms totales)
        if parada_emergencia:
            detener_todo(); return
        time.sleep_ms(100)
    
    # ============================================================
    # FASE 4: Acomodo final con giro leve a la IZQUIERDA
    # ============================================================
    motorA_derecha_silencioso()
    for _ in range(8):  # 500ms de giro a la izquierda
        if parada_emergencia:
            detener_todo(); return
        time.sleep_ms(100)
    
    motorA_detener_silencioso()
    detener_todo()
    print("Infinito completado")

def movimiento_zigzag():
    """Recorrido en zigzag al 60%: der → izq → der → izq → der → izq → centrar."""
    global parada_emergencia, velocidad_B
    parada_emergencia = False
    print("Movimiento: ZIGZAG")
    velocidad_B = 60
    motorB_adelante()
    
    giros = [
        motorA_derecha_silencioso,
        motorA_izquierda_silencioso,
        motorA_derecha_silencioso,
        motorA_izquierda_silencioso,
        motorA_derecha_silencioso,
        motorA_izquierda_silencioso,
    ]
    
    for accion in giros:
        if parada_emergencia:
            print("¡Parada de emergencia durante ZIGZAG!")
            detener_todo()
            return
        accion()
        for _ in range(6):
            if parada_emergencia: break
            time.sleep_ms(100)
    
    detener_todo()
    if parada_emergencia:
        print("¡Parada de emergencia durante ZIGZAG!")
    else:
        print("Zigzag completado")

def movimiento_especial():
    """Movimiento especial: PARQUEO EN PARALELO al 80%."""
    global parada_emergencia, velocidad_B
    parada_emergencia = False
    print("Movimiento: PARQUEO")
    velocidad_B = 80
    
    motorA_detener_silencioso()
    motorB_adelante()
    for _ in range(12):
        if parada_emergencia: break
        time.sleep_ms(100)
    if parada_emergencia: detener_todo(); return
    
    motorA_derecha_silencioso()
    for _ in range(7):
        if parada_emergencia: break
        time.sleep_ms(100)
    if parada_emergencia: detener_todo(); return
    
    motorB_detener()
    motorA_detener_silencioso()
    for _ in range(4):
        if parada_emergencia: break
        time.sleep_ms(100)
    if parada_emergencia: detener_todo(); return
    
    motorA_izquierda_silencioso()
    motorB_atras()
    for _ in range(10):
        if parada_emergencia: break
        time.sleep_ms(100)
    if parada_emergencia: detener_todo(); return
    
    motorB_detener()
    motorA_detener_silencioso()
    detener_todo()
    print("Parqueo completado")

# ============================================================
# CONEXIÓN WIFI
# ============================================================
def conectar_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)
    print("Conectando a WiFi...")
    timeout = 10
    while not wlan.isconnected() and timeout > 0:
        print(".", end="")
        time.sleep(1)
        timeout -= 1
    if wlan.isconnected():
        print("\nWiFi conectado!")
        print("Dirección IP:", wlan.ifconfig()[0])
        return wlan.ifconfig()[0]
    else:
        print("\nError: No se pudo conectar a WiFi")
        return None

# ============================================================
# SERVIDOR TCP
# ============================================================
def iniciar_servidor(ip):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((ip, PORT))
    s.listen(1)
    print(f"Servidor escuchando en {ip}:{PORT}")
    return s

def procesar_comando(comando):
    global parada_emergencia
    comando = comando.strip()
    
    if comando == 'PARADA':
        print("¡PARADA DE EMERGENCIA!")
        parada_emergencia = True
        return
    
    if comando == '1':
        motorA_derecha()
    elif comando == '-1':
        motorA_izquierda()
    elif comando == '0':
        motorA_detener()
    elif comando == '2':
        motorB_adelante()
    elif comando == '3':
        motorB_atras()
    elif comando == '-2':
        motorB_detener()
    elif comando in ('v1', 'v2', 'v3', 'v4'):
        set_velocidad_B(int(comando[1]))
    elif comando == '4':
        encender_luz(LUZ_DELANTERAS, "Delanteras")
    elif comando == '5':
        encender_luz(LUZ_TRASERAS, "Traseras")
    elif comando == '6':
        toggle_direccional_derecha()
    elif comando == '7':
        toggle_direccional_izquierda()
    elif comando == '-3':
        apagar_todas_luces()
    elif comando == 'Idr1':
        activar_modo_automatico(True)
    elif comando == 'Idr0':
        activar_modo_automatico(False)
    elif comando == 'Circle':
        movimiento_circulo()
    elif comando == 'Infinite':
        movimiento_infinito()
    elif comando == 'ZigZag':
        movimiento_zigzag()
    elif comando == 'Special':
        movimiento_especial()
    else:
        print(f"Comando no reconocido: {comando}")

# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================
def main():
    motorA_detener_silencioso()
    motorB_detener()
    apagar_todas_luces()
    
    ip = conectar_wifi()
    if ip is None:
        return
    
    servidor = iniciar_servidor(ip)
    
    while True:
        try:
            cliente, direccion = servidor.accept()
            print(f"\nCliente conectado desde {direccion}")
            cliente.send(b"Conectado al carro. Envia comandos.\n")
            
            while True:
                datos = cliente.recv(1024)
                if not datos:
                    print("Cliente desconectado")
                    break
                
                mensaje = datos.decode('utf-8').strip()
                print(f"Recibido: {mensaje}")
                
                for linea in mensaje.split('\n'):
                    if linea.strip():
                        procesar_comando(linea)
                
                cliente.send(b"OK\n")
        
        except Exception as e:
            print(f"Error: {e}")
            try:
                cliente.close()
            except:
                pass

if __name__ == "__main__":
    main()
