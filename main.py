#Generador de Frecuencias para Bienestar Mental
#Desarrollado con Python + Kivy + NumPy
#"""

import numpy as np
import threading
import time
import os

# Kivy config antes de importar
from kivy.config import Config
Config.set('graphics', 'width', '420')
Config.set('graphics', 'height', '820')
Config.set('graphics', 'resizable', True)

from kivy.app import App
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.graphics import Color, Ellipse, Rectangle, RoundedRectangle, Line
from kivy.graphics.texture import Texture
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import (NumericProperty, StringProperty,
                              BooleanProperty, ListProperty, ObjectProperty)
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.slider import Slider
from kivy.uix.widget import Widget
from kivy.animation import Animation
from kivy.core.window import Window
from kivy.utils import platform

# ─── DETECCIÓN DE BACKEND DE AUDIO ────────────────────────────────────────────
# En Android no existe ALSA/PortAudio, así que pyaudio y sounddevice no
# funcionan ahí (por eso el bucle/crash al importar en Termux). En el APK
# usamos AudioTrack nativo de Android vía pyjnius; en escritorio (para
# probar antes de compilar) usamos pyaudio o sounddevice como antes.
AUDIO_BACKEND = 'none'

if platform == 'android':
    try:
        from jnius import autoclass
        AUDIO_BACKEND = 'android'
    except ImportError:
        AUDIO_BACKEND = 'none'
        print("⚠️  pyjnius no disponible. Agrega 'pyjnius' a requirements en buildozer.spec")
else:
    try:
        import pyaudio
        AUDIO_BACKEND = 'pyaudio'
    except ImportError:
        try:
            import sounddevice as sd
            AUDIO_BACKEND = 'sounddevice'
        except ImportError:
            AUDIO_BACKEND = 'none'
            print("⚠️  Sin backend de audio de escritorio. Instala: pip install sounddevice")

Window.clearcolor = (0.05, 0.06, 0.12, 1)


# ─── DATOS DE FRECUENCIAS ─────────────────────────────────────────────────────
FRECUENCIAS = {
    "Delta": {
        "rango": "0.5 – 4 Hz",
        "hz": 2.0,
        "color": [0.3, 0.15, 0.6, 1],
        "color_hex": "#4B1F99",
        "icono": "🌊",
        "descripcion": "Sueño profundo y regeneración celular",
        "beneficios": ["Sueño reparador", "Regeneración celular", "Reducción del cortisol", "Sanación profunda"],
        "categoria": "Sueño"
    },
    "Theta": {
        "rango": "4 – 8 Hz",
        "hz": 6.0,
        "color": [0.15, 0.3, 0.7, 1],
        "color_hex": "#2649B3",
        "icono": "🧘",
        "descripcion": "Meditación profunda y creatividad",
        "beneficios": ["Meditación profunda", "Acceso al subconsciente", "Creatividad elevada", "Reducción de ansiedad"],
        "categoria": "Meditación"
    },
    "Alpha": {
        "rango": "8 – 14 Hz",
        "hz": 10.0,
        "color": [0.1, 0.5, 0.5, 1],
        "color_hex": "#1A8080",
        "icono": "☯️",
        "descripcion": "Relajación consciente y claridad mental",
        "beneficios": ["Relajación consciente", "Reducción del estrés", "Mejora del foco", "Estado de flujo"],
        "categoria": "Relajación"
    },
    "Beta": {
        "rango": "14 – 30 Hz",
        "hz": 20.0,
        "color": [0.1, 0.6, 0.3, 1],
        "color_hex": "#1A994D",
        "icono": "⚡",
        "descripcion": "Alerta, concentración y cognición activa",
        "beneficios": ["Mayor concentración", "Pensamiento lógico", "Productividad", "Aprendizaje activo"],
        "categoria": "Enfoque"
    },
    "Gamma": {
        "rango": "30 – 100 Hz",
        "hz": 40.0,
        "color": [0.7, 0.4, 0.1, 1],
        "color_hex": "#B36619",
        "icono": "✨",
        "descripcion": "Alta cognición, percepción e insight",
        "beneficios": ["Procesamiento rápido", "Insight y revelación", "Memoria unificada", "Alta percepción"],
        "categoria": "Cognición"
    },
    "Solfeggio 528": {
        "rango": "528 Hz",
        "hz": 528.0,
        "color": [0.6, 0.1, 0.4, 1],
        "color_hex": "#991A66",
        "icono": "💚",
        "descripcion": "Frecuencia del amor y reparación del ADN",
        "beneficios": ["Frecuencia del amor", "Reparación celular", "Transformación", "Reducción de estrés"],
        "categoria": "Solfeggio"
    },
    "Solfeggio 432": {
        "rango": "432 Hz",
        "hz": 432.0,
        "color": [0.5, 0.2, 0.1, 1],
        "color_hex": "#80331A",
        "icono": "🎵",
        "descripcion": "Afinación natural y armonía universal",
        "beneficios": ["Armonía natural", "Coherencia cardíaca", "Paz interior", "Conexión cósmica"],
        "categoria": "Solfeggio"
    },
    "Schumann": {
        "rango": "7.83 Hz",
        "hz": 7.83,
        "color": [0.2, 0.45, 0.15, 1],
        "color_hex": "#337326",
        "icono": "🌍",
        "descripcion": "Resonancia de la Tierra — sincronización global",
        "beneficios": ["Grounding terrestre", "Bienestar general", "Sincronización circadiana", "Equilibrio del sistema nervioso"],
        "categoria": "Tierra"
    },
}

TIPOS_ONDA = ["Senoidal", "Binaural", "Isocronica", "Ruido Rosa", "Ruido Blanco"]


# ─── GENERADOR DE AUDIO ───────────────────────────────────────────────────────
class GeneradorAudio:
    SAMPLE_RATE = 44100
    CHUNK = 1024

    def __init__(self):
        self.activo = False
        self.frecuencia = 10.0
        self.volumen = 0.3
        self.tipo_onda = "Senoidal"
        self.fase = 0.0
        self.hilo = None
        self.stream = None

    def generar_chunk(self):
        n = self.CHUNK
        t = (np.arange(n) + self.fase) / self.SAMPLE_RATE

        if self.tipo_onda == "Senoidal":
            data = np.sin(2 * np.pi * self.frecuencia * t)

        elif self.tipo_onda == "Binaural":
            # Frecuencia portadora 200 Hz + diferencia binaural
            portadora = 200.0
            izq = np.sin(2 * np.pi * portadora * t)
            der = np.sin(2 * np.pi * (portadora + self.frecuencia) * t)
            data = (izq + der) * 0.5

        elif self.tipo_onda == "Isocronica":
            # Pulsos rectangulares a la frecuencia objetivo
            portadora = 200.0
            carrier = np.sin(2 * np.pi * portadora * t)
            if self.frecuencia > 0:
                pulso = (np.sin(2 * np.pi * self.frecuencia * t) > 0).astype(float)
            else:
                pulso = np.ones(n)
            data = carrier * pulso

        elif self.tipo_onda == "Ruido Rosa":
            blanco = np.random.randn(n)
            # Aproximación simple de ruido rosa (filtro 1/f)
            rosa = np.zeros(n)
            b = [0.049922, -0.095993, 0.050612, -0.004374]
            a = [1, -2.494956, 2.017265, -0.522629]
            from scipy.signal import lfilter
            try:
                rosa = lfilter(b, a, blanco)
            except Exception:
                rosa = blanco
            data = rosa / (np.max(np.abs(rosa)) + 1e-9)

        elif self.tipo_onda == "Ruido Blanco":
            data = np.random.randn(n)
            data = data / (np.max(np.abs(data)) + 1e-9)

        else:
            data = np.sin(2 * np.pi * self.frecuencia * t)

        self.fase += n
        if self.fase > self.SAMPLE_RATE * 1000:
            self.fase = 0

        data = np.clip(data * self.volumen, -1.0, 1.0)
        return (data * 32767).astype(np.int16).tobytes()

    def iniciar(self):
        if self.activo:
            return
        self.activo = True
        if AUDIO_BACKEND == 'android':
            self.hilo = threading.Thread(target=self._loop_android, daemon=True)
            self.hilo.start()
        elif AUDIO_BACKEND == 'pyaudio':
            self.hilo = threading.Thread(target=self._loop_pyaudio, daemon=True)
            self.hilo.start()
        elif AUDIO_BACKEND == 'sounddevice':
            self.hilo = threading.Thread(target=self._loop_sounddevice, daemon=True)
            self.hilo.start()

    def detener(self):
        self.activo = False
        time.sleep(0.1)

    def _loop_pyaudio(self):
        pa = pyaudio.PyAudio()
        stream = pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.SAMPLE_RATE,
            output=True,
            frames_per_buffer=self.CHUNK
        )
        while self.activo:
            try:
                stream.write(self.generar_chunk())
            except Exception:
                break
        stream.stop_stream()
        stream.close()
        pa.terminate()

    def _loop_sounddevice(self):
        def callback(outdata, frames, time_info, status):
            if not self.activo:
                raise sd.CallbackStop()
            chunk = self.generar_chunk()
            arr = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32767.0
            outdata[:, 0] = arr[:frames]

        with sd.OutputStream(
            samplerate=self.SAMPLE_RATE,
            channels=1,
            dtype='float32',
            blocksize=self.CHUNK,
            callback=callback
        ):
            while self.activo:
                time.sleep(0.05)

    def _loop_android(self):
        """Streaming continuo hacia el hardware de audio de Android usando
        AudioTrack en modo MODE_STREAM (equivalente nativo al callback de
        sounddevice/pyaudio en escritorio)."""
        import array

        AudioTrack = autoclass('android.media.AudioTrack')
        AudioFormat = autoclass('android.media.AudioFormat')
        AudioManager = autoclass('android.media.AudioManager')

        channel_config = AudioFormat.CHANNEL_OUT_MONO
        encoding = AudioFormat.ENCODING_PCM_16BIT

        min_buffer = AudioTrack.getMinBufferSize(
            self.SAMPLE_RATE, channel_config, encoding
        )
        buffer_size = max(min_buffer, self.CHUNK * 2)

        track = AudioTrack(
            AudioManager.STREAM_MUSIC,
            self.SAMPLE_RATE,
            channel_config,
            encoding,
            buffer_size,
            AudioTrack.MODE_STREAM
        )

        try:
            track.play()
            while self.activo:
                chunk = self.generar_chunk()
                # 'h' = short con signo (16 bits), lo que espera el AudioTrack
                muestras = array.array('h')
                muestras.frombytes(chunk)
                track.write(muestras, 0, len(muestras))
        except Exception as e:
            print(f"⚠️  Error en stream de audio Android: {e}")
        finally:
            try:
                track.stop()
                track.release()
            except Exception:
                pass


# ─── WIDGETS PERSONALIZADOS ───────────────────────────────────────────────────
class OndaWidget(Widget):
    """Visualizador de onda animada"""
    freq_display = NumericProperty(10.0)
    wave_color = ListProperty([0.1, 0.5, 0.5, 1])
    activo = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._t = 0.0
        self._event = Clock.schedule_interval(self._update, 1/30)

    def _update(self, dt):
        if self.activo:
            self._t += dt * min(self.freq_display * 0.5, 8.0)
        self.canvas.clear()
        self._dibujar()

    def _dibujar(self):
        w, h = self.width, self.height
        if w < 2 or h < 2:
            return

        with self.canvas:
            # Fondo
            Color(0.08, 0.09, 0.16, 1)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(12)])

            puntos = []
            n = 120
            amp = h * 0.32 if self.activo else h * 0.08
            freq_visual = max(0.5, min(self.freq_display / 20.0, 4.0))

            for i in range(n + 1):
                x = self.x + (i / n) * w
                y = self.y + h / 2 + amp * np.sin(
                    2 * np.pi * freq_visual * (i / n) - self._t
                ) * (0.5 + 0.5 * np.sin(self._t * 0.3))
                puntos.extend([x, y])

            if len(puntos) >= 4:
                r, g, b, a = self.wave_color
                Color(r, g, b, 0.9 if self.activo else 0.35)
                Line(points=puntos, width=dp(2.2))

                # Segunda onda superpuesta (armónico)
                if self.activo:
                    puntos2 = []
                    for i in range(n + 1):
                        x = self.x + (i / n) * w
                        y = self.y + h / 2 + (amp * 0.4) * np.sin(
                            2 * np.pi * freq_visual * 2 * (i / n) - self._t * 1.3
                        )
                        puntos2.extend([x, y])
                    Color(r, g, b, 0.3)
                    Line(points=puntos2, width=dp(1.2))


class PulsoWidget(Widget):
    """Círculos pulsantes de meditación"""
    wave_color = ListProperty([0.1, 0.5, 0.5, 1])
    activo = BooleanProperty(False)
    freq_hz = NumericProperty(10.0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._t = 0.0
        Clock.schedule_interval(self._update, 1/30)

    def _update(self, dt):
        self._t += dt
        self.canvas.clear()
        self._dibujar()

    def _dibujar(self):
        cx = self.x + self.width / 2
        cy = self.y + self.height / 2
        r, g, b, a = self.wave_color

        with self.canvas:
            if self.activo:
                speed = max(0.3, min(self.freq_hz * 0.15, 3.0))
                for i in range(3):
                    phase = (self._t * speed + i * 0.33) % 1.0
                    radius = self.width * 0.15 + phase * self.width * 0.35
                    alpha = (1.0 - phase) * 0.4
                    Color(r, g, b, alpha)
                    d = radius * 2
                    Ellipse(pos=(cx - radius, cy - radius), size=(d, d))

            # Círculo central
            base_r = self.width * 0.12
            pulse = 1.0 + (0.12 * np.sin(self._t * 2.5) if self.activo else 0)
            cr = base_r * pulse
            Color(r, g, b, 0.9 if self.activo else 0.4)
            Ellipse(pos=(cx - cr, cy - cr), size=(cr * 2, cr * 2))

            # Punto interior
            Color(1, 1, 1, 0.85 if self.activo else 0.3)
            pr = cr * 0.28
            Ellipse(pos=(cx - pr, cy - pr), size=(pr * 2, pr * 2))


class TarjetaFrecuencia(BoxLayout):
    nombre = StringProperty("")
    rango = StringProperty("")
    icono = StringProperty("")
    descripcion = StringProperty("")
    seleccionada = BooleanProperty(False)
    card_color = ListProperty([0.1, 0.2, 0.35, 1])

    def __init__(self, data, callback, **kwargs):
        super().__init__(**kwargs)
        self.data = data
        self.callback = callback
        self.nombre = data['nombre']
        self.rango = data['rango']
        self.icono = data['icono']
        self.descripcion = data['descripcion']
        self.card_color = data['color'][:3] + [0.2]
        self.orientation = 'vertical'
        self.padding = dp(10)
        self.spacing = dp(4)
        self.size_hint_y = None
        self.height = dp(90)
        self._construir()

    def _construir(self):
        with self.canvas.before:
            self._bg_color = Color(*self.card_color)
            self._bg_rect = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[dp(14)]
            )
        self.bind(pos=self._actualizar_rect, size=self._actualizar_rect)

        # Fila superior: icono + nombre + rango
        fila = BoxLayout(size_hint_y=None, height=dp(32), spacing=dp(8))
        lbl_icono = Label(text=self.icono, font_size=dp(20), size_hint_x=None, width=dp(28))
        lbl_nombre = Label(
            text=self.nombre, font_size=dp(14), bold=True,
            color=(1, 1, 1, 1), halign='left', valign='middle'
        )
        lbl_nombre.bind(size=lambda s, v: setattr(s, 'text_size', v))
        lbl_rango = Label(
            text=self.rango, font_size=dp(11),
            color=(0.7, 0.85, 1, 0.8), halign='right', valign='middle',
            size_hint_x=None, width=dp(80)
        )
        fila.add_widget(lbl_icono)
        fila.add_widget(lbl_nombre)
        fila.add_widget(lbl_rango)
        self.add_widget(fila)

        # Descripción
        lbl_desc = Label(
            text=self.descripcion, font_size=dp(11),
            color=(0.75, 0.85, 0.95, 0.75), halign='left', valign='top'
        )
        lbl_desc.bind(size=lambda s, v: setattr(s, 'text_size', v))
        self.add_widget(lbl_desc)

    def _actualizar_rect(self, *args):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.callback(self.nombre)
            return True
        return super().on_touch_down(touch)

    def marcar(self, activa):
        self.seleccionada = activa
        r, g, b = self.data['color'][:3]
        if activa:
            self._bg_color.rgba = [r, g, b, 0.45]
        else:
            self._bg_color.rgba = [r * 0.4, g * 0.4, b * 0.4, 0.25]


# ─── PANTALLA PRINCIPAL ───────────────────────────────────────────────────────
KV = """
<RoundButton@Button>:
    background_color: 0, 0, 0, 0
    background_normal: ''
    canvas.before:
        Color:
            rgba: self.btn_color if not self.state == 'down' else [c*0.7 for c in self.btn_color]
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(22)]
    btn_color: [0.15, 0.55, 0.85, 1]
    color: 1, 1, 1, 1
    bold: True
    font_size: dp(14)

<SliderStyled@Slider>:
    cursor_size: dp(22), dp(22)
    cursor_image: ''
    background_width: dp(4)
    canvas.before:
        Color:
            rgba: 0.15, 0.2, 0.32, 1
        RoundedRectangle:
            pos: self.pos[0], self.center_y - dp(3)
            size: self.width, dp(6)
            radius: [dp(3)]
        Color:
            rgba: 0.3, 0.7, 0.95, 1
        RoundedRectangle:
            pos: self.pos[0], self.center_y - dp(3)
            size: (self.value_normalized * self.width), dp(6)
            radius: [dp(3)]
        Color:
            rgba: 0.9, 0.95, 1, 1
        Ellipse:
            pos: self.value_pos[0] - dp(10), self.center_y - dp(10)
            size: dp(20), dp(20)
"""

Builder.load_string(KV)


class PantallaMain(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = [dp(16), dp(8), dp(16), dp(16)]
        self.spacing = dp(10)

        self.generador = GeneradorAudio()
        self.freq_actual = FRECUENCIAS["Alpha"]
        self.nombre_actual = "Alpha"
        self.reproduciendo = False
        self.tarjetas = {}
        self.timer_seg = 0
        self.timer_activo = False

        self._construir_ui()
        Clock.schedule_interval(self._actualizar_timer, 1)

    def _construir_ui(self):
        # ── HEADER ──
        header = BoxLayout(size_hint_y=None, height=dp(60), spacing=dp(10))

        lbl_titulo = Label(
            text="[b]Hz Bienestar[/b]",
            markup=True,
            font_size=dp(22),
            color=(0.7, 0.9, 1, 1),
            halign='left', valign='middle'
        )
        lbl_titulo.bind(size=lambda s, v: setattr(s, 'text_size', v))

        self.lbl_estado = Label(
            text="⏸ Detenido",
            font_size=dp(13),
            color=(0.5, 0.7, 0.6, 1),
            halign='right', valign='middle',
            size_hint_x=None, width=dp(120)
        )
        header.add_widget(lbl_titulo)
        header.add_widget(self.lbl_estado)
        self.add_widget(header)

        # ── VISUALIZADOR PRINCIPAL ──
        viz_row = BoxLayout(size_hint_y=None, height=dp(130), spacing=dp(10))

        self.onda = OndaWidget(
            size_hint_x=0.65,
            wave_color=self.freq_actual['color'],
            freq_display=self.freq_actual['hz']
        )
        self.pulso = PulsoWidget(
            size_hint_x=0.35,
            wave_color=self.freq_actual['color'],
            freq_hz=self.freq_actual['hz']
        )
        viz_row.add_widget(self.onda)
        viz_row.add_widget(self.pulso)
        self.add_widget(viz_row)

        # ── INFO FRECUENCIA ACTUAL ──
        info_box = BoxLayout(
            size_hint_y=None, height=dp(70),
            orientation='vertical', spacing=dp(4)
        )
        with info_box.canvas.before:
            self._info_color = Color(0.1, 0.4, 0.5, 0.2)
            self._info_rect = RoundedRectangle(
                pos=info_box.pos, size=info_box.size, radius=[dp(14)]
            )
        info_box.bind(
            pos=lambda s, v: setattr(self._info_rect, 'pos', v),
            size=lambda s, v: setattr(self._info_rect, 'size', v)
        )

        fila_hz = BoxLayout(size_hint_y=None, height=dp(36))
        self.lbl_nombre_freq = Label(
            text=f"{self.freq_actual['icono']}  Alpha – Relajación",
            font_size=dp(16), bold=True, color=(0.85, 0.95, 1, 1),
            halign='left', valign='middle'
        )
        self.lbl_nombre_freq.bind(size=lambda s, v: setattr(s, 'text_size', v))
        self.lbl_hz_valor = Label(
            text="10.0 Hz",
            font_size=dp(20), bold=True, color=(0.4, 0.9, 0.8, 1),
            size_hint_x=None, width=dp(90), halign='right', valign='middle'
        )
        fila_hz.add_widget(self.lbl_nombre_freq)
        fila_hz.add_widget(self.lbl_hz_valor)
        info_box.add_widget(fila_hz)

        self.lbl_desc_freq = Label(
            text=self.freq_actual['descripcion'],
            font_size=dp(12), color=(0.7, 0.85, 0.9, 0.8),
            halign='left', valign='top', size_hint_y=None, height=dp(28)
        )
        self.lbl_desc_freq.bind(size=lambda s, v: setattr(s, 'text_size', v))
        info_box.add_widget(self.lbl_desc_freq)
        self.add_widget(info_box)

        # ── CONTROLES DE FRECUENCIA MANUAL ──
        ctrl_freq = BoxLayout(size_hint_y=None, height=dp(52), orientation='vertical')
        lbl_freq_ctrl = Label(
            text="Frecuencia personalizada",
            font_size=dp(11), color=(0.6, 0.75, 0.85, 0.7),
            size_hint_y=None, height=dp(18), halign='left'
        )
        lbl_freq_ctrl.bind(size=lambda s, v: setattr(s, 'text_size', v))
        self.slider_freq = Slider(
            min=0.5, max=1000.0, value=10.0, step=0.5,
            size_hint_y=None, height=dp(34)
        )
        self.slider_freq.bind(value=self._on_slider_freq)
        ctrl_freq.add_widget(lbl_freq_ctrl)
        ctrl_freq.add_widget(self.slider_freq)
        self.add_widget(ctrl_freq)

        # ── VOLUMEN ──
        ctrl_vol = BoxLayout(size_hint_y=None, height=dp(52), orientation='vertical')
        fila_vol_lbl = BoxLayout(size_hint_y=None, height=dp(18))
        lbl_vol = Label(
            text="Volumen", font_size=dp(11), color=(0.6, 0.75, 0.85, 0.7),
            halign='left'
        )
        lbl_vol.bind(size=lambda s, v: setattr(s, 'text_size', v))
        self.lbl_vol_val = Label(
            text="30%", font_size=dp(11), color=(0.7, 0.9, 0.8, 1),
            size_hint_x=None, width=dp(40), halign='right'
        )
        fila_vol_lbl.add_widget(lbl_vol)
        fila_vol_lbl.add_widget(self.lbl_vol_val)
        self.slider_vol = Slider(
            min=0.0, max=1.0, value=0.3,
            size_hint_y=None, height=dp(34)
        )
        self.slider_vol.bind(value=self._on_slider_vol)
        ctrl_vol.add_widget(fila_vol_lbl)
        ctrl_vol.add_widget(self.slider_vol)
        self.add_widget(ctrl_vol)

        # ── TIPO DE ONDA ──
        tipo_lbl = Label(
            text="Tipo de onda",
            font_size=dp(11), color=(0.6, 0.75, 0.85, 0.7),
            size_hint_y=None, height=dp(18), halign='left'
        )
        tipo_lbl.bind(size=lambda s, v: setattr(s, 'text_size', v))
        self.add_widget(tipo_lbl)

        tipo_grid = GridLayout(
            cols=5, size_hint_y=None, height=dp(38), spacing=dp(4)
        )
        self.btns_tipo = {}
        for tipo in TIPOS_ONDA:
            btn = Button(
                text=tipo[:6], font_size=dp(10),
                background_normal='', background_color=(0.12, 0.18, 0.3, 1),
                color=(0.75, 0.9, 1, 1)
            )
            btn.bind(on_press=lambda b, t=tipo: self._seleccionar_tipo(t))
            with btn.canvas.before:
                pass
            self.btns_tipo[tipo] = btn
            tipo_grid.add_widget(btn)
        self._marcar_tipo("Senoidal")
        self.add_widget(tipo_grid)

        # ── BOTONES PRINCIPALES ──
        btn_row = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(10))

        self.btn_play = Button(
            text="▶  INICIAR", font_size=dp(15), bold=True,
            background_normal='', background_color=(0.15, 0.55, 0.35, 1),
            color=(1, 1, 1, 1)
        )
        with self.btn_play.canvas.before:
            Color(0.15, 0.55, 0.35, 1)
            self._play_rect = RoundedRectangle(
                pos=self.btn_play.pos, size=self.btn_play.size, radius=[dp(22)]
            )
        self.btn_play.canvas.before.clear()

        self.btn_play.bind(on_press=self._toggle_play)
        btn_row.add_widget(self.btn_play)

        btn_timer = Button(
            text="⏱ Timer", font_size=dp(13),
            background_normal='', background_color=(0.18, 0.25, 0.45, 1),
            color=(0.8, 0.9, 1, 1), size_hint_x=None, width=dp(80)
        )
        btn_timer.bind(on_press=self._toggle_timer)
        self.btn_timer = btn_timer
        btn_row.add_widget(btn_timer)
        self.add_widget(btn_row)

        # Timer label
        self.lbl_timer = Label(
            text="", font_size=dp(13), color=(0.5, 0.8, 0.7, 0.8),
            size_hint_y=None, height=dp(20), halign='center'
        )
        self.add_widget(self.lbl_timer)

        # ── LISTA DE FRECUENCIAS ──
        sep = Label(
            text="Frecuencias de Bienestar",
            font_size=dp(12), color=(0.5, 0.7, 0.85, 0.7),
            size_hint_y=None, height=dp(22), halign='left'
        )
        sep.bind(size=lambda s, v: setattr(s, 'text_size', v))
        self.add_widget(sep)

        scroll = ScrollView(do_scroll_x=False)
        lista = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=dp(8), padding=[0, dp(4), 0, dp(4)]
        )
        lista.bind(minimum_height=lista.setter('height'))

        for nombre, data in FRECUENCIAS.items():
            d = dict(data, nombre=nombre)
            tarjeta = TarjetaFrecuencia(d, self._seleccionar_frecuencia)
            self.tarjetas[nombre] = tarjeta
            lista.add_widget(tarjeta)

        self.tarjetas["Alpha"].marcar(True)
        scroll.add_widget(lista)
        self.add_widget(scroll)

    # ── LÓGICA ──────────────────────────────────────────────────────────────

    def _seleccionar_frecuencia(self, nombre):
        if nombre not in FRECUENCIAS:
            return
        self.nombre_actual = nombre
        self.freq_actual = FRECUENCIAS[nombre]
        hz = self.freq_actual['hz']
        col = self.freq_actual['color']

        # Actualizar generador
        self.generador.frecuencia = hz
        self.onda.freq_display = hz
        self.onda.wave_color = col
        self.pulso.wave_color = col
        self.pulso.freq_hz = hz

        # Actualizar slider (sin disparar callback recursivo)
        self.slider_freq.unbind(value=self._on_slider_freq)
        self.slider_freq.value = min(hz, 1000.0)
        self.slider_freq.bind(value=self._on_slider_freq)

        # Actualizar labels
        self.lbl_nombre_freq.text = f"{self.freq_actual['icono']}  {nombre} – {self.freq_actual['categoria']}"
        self.lbl_hz_valor.text = f"{hz:.1f} Hz"
        self.lbl_desc_freq.text = self.freq_actual['descripcion']

        # Actualizar color info
        r, g, b = col[:3]
        self._info_color.rgba = [r * 0.5, g * 0.5, b * 0.5, 0.25]

        # Marcar tarjeta
        for n, t in self.tarjetas.items():
            t.marcar(n == nombre)

    def _on_slider_freq(self, slider, value):
        self.generador.frecuencia = value
        self.onda.freq_display = value
        self.pulso.freq_hz = value
        self.lbl_hz_valor.text = f"{value:.1f} Hz"

    def _on_slider_vol(self, slider, value):
        self.generador.volumen = value
        self.lbl_vol_val.text = f"{int(value*100)}%"

    def _seleccionar_tipo(self, tipo):
        self.generador.tipo_onda = tipo
        self._marcar_tipo(tipo)

    def _marcar_tipo(self, tipo_sel):
        for tipo, btn in self.btns_tipo.items():
            if tipo == tipo_sel:
                btn.background_color = (0.2, 0.55, 0.75, 1)
                btn.color = (1, 1, 1, 1)
            else:
                btn.background_color = (0.12, 0.18, 0.3, 1)
                btn.color = (0.65, 0.8, 0.9, 0.7)

    def _toggle_play(self, *args):
        self.reproduciendo = not self.reproduciendo
        if self.reproduciendo:
            self.generador.frecuencia = self.slider_freq.value
            self.generador.volumen = self.slider_vol.value
            self.generador.iniciar()
            self.btn_play.text = "⏹  DETENER"
            self.btn_play.background_color = (0.65, 0.2, 0.2, 1)
            self.lbl_estado.text = "▶ Reproduciendo"
            self.lbl_estado.color = (0.4, 0.95, 0.6, 1)
            self.onda.activo = True
            self.pulso.activo = True
            if AUDIO_BACKEND == 'none':
                self.lbl_estado.text = "⚠ Sin audio instalado"
        else:
            self.generador.detener()
            self.btn_play.text = "▶  INICIAR"
            self.btn_play.background_color = (0.15, 0.55, 0.35, 1)
            self.lbl_estado.text = "⏸ Detenido"
            self.lbl_estado.color = (0.5, 0.7, 0.6, 1)
            self.onda.activo = False
            self.pulso.activo = False
            self.timer_activo = False
            self.lbl_timer.text = ""

    def _toggle_timer(self, *args):
        if not self.reproduciendo:
            return
        if self.timer_activo:
            self.timer_activo = False
            self.timer_seg = 0
            self.lbl_timer.text = ""
            self.btn_timer.text = "⏱ Timer"
        else:
            self.timer_activo = True
            self.timer_seg = 0
            self.btn_timer.text = "⏹ Parar"

    def _actualizar_timer(self, dt):
        if self.timer_activo and self.reproduciendo:
            self.timer_seg += 1
            m = self.timer_seg // 60
            s = self.timer_seg % 60
            self.lbl_timer.text = f"⏱  {m:02d}:{s:02d} en sesión"


# ─── APP ──────────────────────────────────────────────────────────────────────
class FreqBienestarApp(App):
    def build(self):
        self.title = "Hz Bienestar Mental"
        return PantallaMain()

    def on_stop(self):
        # Detener audio al cerrar
        screen = self.root
        if hasattr(screen, 'generador'):
            screen.generador.detener()


if __name__ == "__main__":
    FreqBienestarApp().run()