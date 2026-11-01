import pygame
import socket
import sys
import time

# ============================================================
# CONFIGURACIÓN
# ============================================================
ANCHO, ALTO = 900, 800
FPS = 30

# Colores
FONDO = (30, 30, 40)
PANEL = (50, 50, 70)
BOTON = (70, 130, 180)
BOTON_HOVER = (100, 160, 210)
BOTON_ACTIVO = (50, 200, 100)
TEXTO = (255, 255, 255)
TEXTO_GRIS = (180, 180, 180)
ROJO = (200, 60, 60)
AMARILLO = (220, 200, 50)
VERDE = (50, 200, 100)
MORADO = (150, 80, 200)

# ============================================================
# CLASE BOTÓN
# ============================================================
class Boton:
    def __init__(self, x, y, ancho, alto, texto, comando, color_base=BOTON):
        self.rect = pygame.Rect(x, y, ancho, alto)
        self.texto = texto
        self.comando = comando
        self.color_base = color_base
        self.hover = False

    def dibujar(self, pantalla, fuente):
        color = self.color_base
        if self.hover:
            color = BOTON_HOVER
        pygame.draw.rect(pantalla, color, self.rect, border_radius=8)
        pygame.draw.rect(pantalla, (20, 20, 30), self.rect, 2, border_radius=8)
        texto_render = fuente.render(self.texto, True, TEXTO)
        texto_rect = texto_render.get_rect(center=self.rect.center)
        pantalla.blit(texto_render, texto_rect)

    def verificar_hover(self, pos):
        self.hover = self.rect.collidepoint(pos)

    def clic(self, pos):
        return self.rect.collidepoint(pos)

# ============================================================
# CLASE CLIENTE WIFI
# ============================================================
class ClienteWiFi:
    def __init__(self):
        self.socket = None
        self.conectado = False
        self.ip = "192.168.1.50"
        self.puerto = 8080
        self.ultimo_mensaje = ""

    def conectar(self, ip, puerto):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(3)
            self.socket.connect((ip, puerto))
            self.socket.settimeout(None)
            self.conectado = True
            self.ip = ip
            self.puerto = puerto
            self.ultimo_mensaje = f"Conectado a {ip}:{puerto}"
            return True
        except Exception as e:
            self.conectado = False
            self.ultimo_mensaje = f"Error: {e}"
            return False

    def desconectar(self):
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        self.socket = None
        self.conectado = False
        self.ultimo_mensaje = "Desconectado"

    def enviar(self, comando):
        if not self.conectado or not self.socket:
            return False, "No conectado"
        try:
            self.socket.send((comando + "\n").encode('utf-8'))
            self.socket.settimeout(0.1)
            try:
                self.socket.recv(1024)
            except:
                pass
            self.socket.settimeout(None)
            self.ultimo_mensaje = f"Enviado: {comando}"
            return True, ""
        except Exception as e:
            self.conectado = False
            self.ultimo_mensaje = f"Error al enviar: {e}"
            return False, str(e)

# ============================================================
# INTERFAZ PRINCIPAL
# ============================================================
def main():
    pygame.init()
    pantalla = pygame.display.set_mode((ANCHO, ALTO))
    pygame.display.set_caption("Control Carrito WiFi - Fórmula E CES")
    reloj = pygame.time.Clock()

    fuente_titulo = pygame.font.SysFont("consolas", 26, bold=True)
    fuente_boton = pygame.font.SysFont("consolas", 16, bold=True)
    fuente_texto = pygame.font.SysFont("consolas", 16)
    fuente_pequena = pygame.font.SysFont("consolas", 14)

    cliente = ClienteWiFi()

    ip_texto = "192.168.1.50"
    campo_activo = False
    campo_rect = pygame.Rect(250, 60, 300, 35)

    # ============================================================
    # BOTONES
    # ============================================================
    botones = []
    
    # Conexión
    botones.append(Boton(600, 60, 120, 35, "CONECTAR", "__CONECTAR__", (40, 140, 90)))
    botones.append(Boton(730, 60, 120, 35, "DESCONECTAR", "__DESCONECTAR__", (140, 60, 60)))
    
    # Dirección (Motor A)
    y_dir = 140
    botones.append(Boton(80, y_dir, 150, 50, "A: DERECHA", "1"))
    botones.append(Boton(250, y_dir, 150, 50, "X: CENTRAR", "0", (140, 60, 60)))
    botones.append(Boton(420, y_dir, 150, 50, "D: IZQUIERDA", "-1"))
    
    # Tracción (Motor B)
    y_trac = 230
    botones.append(Boton(80, y_trac, 150, 50, "W: ADELANTE", "2"))
    botones.append(Boton(250, y_trac, 150, 50, "X: DETENER", "-2", (140, 60, 60)))
    botones.append(Boton(420, y_trac, 150, 50, "S: ATRÁS", "3"))
    
    # Velocidades
    y_vel = 320
    botones.append(Boton(80, y_vel, 110, 50, "1: 20%", "v1"))
    botones.append(Boton(200, y_vel, 110, 50, "2: 50%", "v2"))
    botones.append(Boton(320, y_vel, 110, 50, "3: 80%", "v3"))
    botones.append(Boton(440, y_vel, 110, 50, "4: 100%", "v4"))
    
    # Luces
    y_luces = 410
    botones.append(Boton(80, y_luces, 130, 50, "5: Delanteras", "4", (180, 140, 40)))
    botones.append(Boton(220, y_luces, 130, 50, "6: Traseras", "5", (180, 140, 40)))
    botones.append(Boton(360, y_luces, 130, 50, "7: Dir. Der", "6", (180, 140, 40)))
    botones.append(Boton(500, y_luces, 130, 50, "8: Dir. Izq", "7", (180, 140, 40)))
    botones.append(Boton(640, y_luces, 150, 50, "9: APAGAR", "-3", (140, 60, 60)))
    
    # Control automático LDR
    y_ldr = 490
    botones.append(Boton(80, y_ldr, 200, 50, "L: Activar LDR (Idr1)", "Idr1", (40, 140, 90)))
    botones.append(Boton(300, y_ldr, 200, 50, "K: Desactivar LDR (Idr0)", "Idr0", (140, 60, 60)))
    
    # Trucos / Movimientos autónomos
    y_trucos = 580
    botones.append(Boton(80, y_trucos, 160, 55, "CÍRCULO", "Circle", MORADO))
    botones.append(Boton(260, y_trucos, 160, 55, "INFINITO", "Infinite", MORADO))
    botones.append(Boton(440, y_trucos, 160, 55, "ZIGZAG", "ZigZag", MORADO))
    botones.append(Boton(620, y_trucos, 160, 55, "ESPECIAL", "Special", MORADO))
    
    # Parada de emergencia (ahora envía "PARADA")
    y_emergencia = 660
    botones.append(Boton(80, y_emergencia, 300, 60, "X: PARADA TOTAL", "__PARADA_TOTAL__", (180, 30, 30)))

    historial = []
    
    teclas_anteriores = {
        'w': False, 's': False, 'a': False, 'd': False
    }

    ejecutando = True
    while ejecutando:
        pos_mouse = pygame.mouse.get_pos()
        
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                ejecutando = False
            
            elif evento.type == pygame.MOUSEBUTTONDOWN:
                if evento.button == 1:
                    if campo_rect.collidepoint(pos_mouse):
                        campo_activo = True
                    else:
                        campo_activo = False
                    
                    for boton in botones:
                        if boton.clic(pos_mouse):
                            if boton.comando == "__CONECTAR__":
                                cliente.conectar(ip_texto, 8080)
                                historial.append(f"CONECTAR a {ip_texto}")
                            elif boton.comando == "__DESCONECTAR__":
                                cliente.desconectar()
                                historial.append("DESCONECTAR")
                            elif boton.comando == "__PARADA_TOTAL__":
                                cliente.enviar("PARADA")  # <-- CAMBIO: parada de emergencia
                                historial.append("PARADA TOTAL")
                            else:
                                cliente.enviar(boton.comando)
                                historial.append(f"Enviado: {boton.comando}")
                            if len(historial) > 8:
                                historial.pop(0)
            
            elif evento.type == pygame.KEYDOWN:
                if campo_activo:
                    if evento.key == pygame.K_BACKSPACE:
                        ip_texto = ip_texto[:-1]
                    elif evento.key == pygame.K_RETURN:
                        campo_activo = False
                    elif len(ip_texto) < 15:
                        if evento.unicode in "0123456789.":
                            ip_texto += evento.unicode
                else:
                    comando = None
                    if evento.key == pygame.K_1: comando = "v1"
                    elif evento.key == pygame.K_2: comando = "v2"
                    elif evento.key == pygame.K_3: comando = "v3"
                    elif evento.key == pygame.K_4: comando = "v4"
                    elif evento.key == pygame.K_5: comando = "4"
                    elif evento.key == pygame.K_6: comando = "5"
                    elif evento.key == pygame.K_7: comando = "6"
                    elif evento.key == pygame.K_8: comando = "7"
                    elif evento.key == pygame.K_9: comando = "-3"
                    elif evento.key == pygame.K_l: comando = "Idr1"
                    elif evento.key == pygame.K_k: comando = "Idr0"
                    elif evento.key == pygame.K_x:
                        cliente.enviar("PARADA")  # <-- CAMBIO: parada de emergencia
                        historial.append("PARADA TOTAL (X)")
                        if len(historial) > 8: historial.pop(0)
                        continue
                    
                    if comando:
                        cliente.enviar(comando)
                        historial.append(f"Tecla: {comando}")
                        if len(historial) > 8:
                            historial.pop(0)

        # CONTROL CONTINUO (MANTENER TECLA)
        if not campo_activo:
            teclas = pygame.key.get_pressed()
            
            w_presionada = teclas[pygame.K_w]
            s_presionada = teclas[pygame.K_s]
            
            if w_presionada and not teclas_anteriores['w']:
                cliente.enviar("2")
                historial.append("W: ADELANTE")
                if len(historial) > 8: historial.pop(0)
            elif not w_presionada and teclas_anteriores['w']:
                cliente.enviar("-2")
                historial.append("W soltada: DETENER")
                if len(historial) > 8: historial.pop(0)
            
            if s_presionada and not teclas_anteriores['s']:
                cliente.enviar("3")
                historial.append("S: ATRÁS")
                if len(historial) > 8: historial.pop(0)
            elif not s_presionada and teclas_anteriores['s']:
                cliente.enviar("-2")
                historial.append("S soltada: DETENER")
                if len(historial) > 8: historial.pop(0)
            
            a_presionada = teclas[pygame.K_a]
            d_presionada = teclas[pygame.K_d]
            
            if a_presionada and not teclas_anteriores['a']:
                cliente.enviar("1")
                historial.append("A: DERECHA")
                if len(historial) > 8: historial.pop(0)
            elif not a_presionada and teclas_anteriores['a']:
                cliente.enviar("0")
                historial.append("A soltada: CENTRAR")
                if len(historial) > 8: historial.pop(0)
            
            if d_presionada and not teclas_anteriores['d']:
                cliente.enviar("-1")
                historial.append("D: IZQUIERDA")
                if len(historial) > 8: historial.pop(0)
            elif not d_presionada and teclas_anteriores['d']:
                cliente.enviar("0")
                historial.append("D soltada: CENTRAR")
                if len(historial) > 8: historial.pop(0)
            
            teclas_anteriores['w'] = w_presionada
            teclas_anteriores['s'] = s_presionada
            teclas_anteriores['a'] = a_presionada
            teclas_anteriores['d'] = d_presionada

        # --- Dibujar ---
        pantalla.fill(FONDO)
        
        titulo = fuente_titulo.render("CONTROL CARRITO WIFI - FÓRMULA E CES", True, AMARILLO)
        pantalla.blit(titulo, (ANCHO // 2 - titulo.get_width() // 2, 15))
        
        # Campo IP
        pygame.draw.rect(pantalla, PANEL, campo_rect, border_radius=5)
        pygame.draw.rect(pantalla, (100, 100, 140) if campo_activo else (70, 70, 90), campo_rect, 2, border_radius=5)
        etiqueta_ip = fuente_texto.render("IP:", True, TEXTO)
        pantalla.blit(etiqueta_ip, (200, 68))
        ip_render = fuente_texto.render(ip_texto, True, TEXTO)
        pantalla.blit(ip_render, (campo_rect.x + 10, campo_rect.y + 8))
        
        # Estado conexión
        estado_color = (50, 200, 100) if cliente.conectado else ROJO
        estado_texto = "CONECTADO" if cliente.conectado else "DESCONECTADO"
        estado_render = fuente_texto.render(estado_texto, True, estado_color)
        pantalla.blit(estado_render, (560, 68))
        
        # Secciones
        seccion = fuente_boton.render("DIRECCIÓN (Motor A) - A/D", True, AMARILLO)
        pantalla.blit(seccion, (80, y_dir - 30))
        seccion = fuente_boton.render("TRACCIÓN (Motor B) - W/S", True, AMARILLO)
        pantalla.blit(seccion, (80, y_trac - 30))
        seccion = fuente_boton.render("VELOCIDADES - 1/2/3/4", True, AMARILLO)
        pantalla.blit(seccion, (80, y_vel - 30))
        seccion = fuente_boton.render("LUCES - 5/6/7/8/9", True, AMARILLO)
        pantalla.blit(seccion, (80, y_luces - 30))
        seccion = fuente_boton.render("CONTROL AUTOMÁTICO (LDR) - L/K", True, AMARILLO)
        pantalla.blit(seccion, (80, y_ldr - 30))
        seccion = fuente_boton.render("TRUCOS / MOVIMIENTOS AUTÓNOMOS", True, MORADO)
        pantalla.blit(seccion, (80, y_trucos - 30))
        
        # Botones
        for boton in botones:
            boton.verificar_hover(pos_mouse)
            boton.dibujar(pantalla, fuente_boton)
        
        # Historial
        y_hist = 740
        hist_titulo = fuente_boton.render("ÚLTIMOS COMANDOS:", True, TEXTO_GRIS)
        pantalla.blit(hist_titulo, (80, y_hist - 20))
        for i, linea in enumerate(historial[-4:]):
            color = TEXTO_GRIS if "Error" not in linea else ROJO
            render = fuente_pequena.render(linea, True, color)
            pantalla.blit(render, (80, y_hist + i * 18))
        
        # Mensaje de estado
        if cliente.ultimo_mensaje:
            mensaje_render = fuente_pequena.render(cliente.ultimo_mensaje, True, TEXTO_GRIS)
            pantalla.blit(mensaje_render, (ANCHO - 400, ALTO - 25))
        
        pygame.display.flip()
        reloj.tick(FPS)

    cliente.desconectar()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()