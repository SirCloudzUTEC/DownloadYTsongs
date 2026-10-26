# Descargador de música de YouTube

Scripts en Python basados en [yt-dlp](https://github.com/yt-dlp/yt-dlp) para reproducir y descargar canciones de YouTube como audio.

```
usefulStuff/
├── yt_music.py          # Una canción: reproducir o descargar
├── batch/
│   ├── yt_batch.py      # Muchas canciones desde un .txt, en paralelo
│   └── lista_ejemplo.txt
└── README.md
```

## Requisitos

Instala las dependencias:

```bash
pip install -U yt-dlp
sudo dnf install ffmpeg mpv
```

- **yt-dlp**: la librería que habla con YouTube.
- **ffmpeg**: convierte el audio a mp3/m4a/etc. Lo necesitan las descargas.
- **mpv**: el reproductor. Solo hace falta para `play`.

## Atajo recomendado

Agrega esto a `~/.zshrc` (cambiando `/ruta/a/usefulStuff` por donde clonaste el repo) y abre una terminal nueva:

```bash
alias ytm='python3 /ruta/a/usefulStuff/yt_music.py'
alias ytb='python3 /ruta/a/usefulStuff/batch/yt_batch.py'
```

Los ejemplos de abajo usan estos alias. Sin ellos, reemplaza `ytm` / `ytb` por la ruta completa con `python3`.

---

## `yt_music.py`: una canción

### Reproducir (sin descargar)

```bash
ytm play "nombre de la canción artista"
ytm play "https://www.youtube.com/watch?v=XXXX"
```

Solo reproduce el audio. Controles de mpv: `espacio` pausa, `←` / `→` retrocede y adelanta, `q` sale.

### Descargar

```bash
ytm download "nombre de la canción artista"
ytm download "https://www.youtube.com/watch?v=XXXX"
ytm download "URL" -o ./otra_carpeta -f m4a
```

| Opción | Qué hace | Por defecto |
|---|---|---|
| `-o`, `--output` | Carpeta destino | `./canciones` en el directorio actual |
| `-f`, `--format` | `mp3`, `m4a`, `opus` o `flac` | `mp3` |

Si escribes un nombre en vez de una URL, se usa el primer resultado de la búsqueda en YouTube. El archivo incluye los datos del video (título, etc.) y la miniatura como portada.

---

## `batch/yt_batch.py`: muchas canciones desde un txt

### 1. Crea la lista

Un archivo `.txt` con una URL por línea. Se pueden mezclar videos y playlists:

```text
# Las líneas con # y las vacías se ignoran
https://www.youtube.com/watch?v=AAAA
https://youtu.be/BBBB
https://www.youtube.com/playlist?list=CCCC
```

### 2. Ejecuta

```bash
cd ~/Music              # las canciones irán a ~/Music/canciones/
ytb mis_canciones.txt
```

| Opción | Qué hace | Por defecto |
|---|---|---|
| `-o`, `--output` | Carpeta destino | `./canciones` en el directorio actual |
| `-f`, `--format` | `mp3`, `m4a`, `opus` o `flac` | `mp3` |
| `-j`, `--jobs` | Descargas simultáneas | `4` |

Ejemplo con todas las opciones:

```bash
ytb mis_canciones.txt -o ./rock -f m4a -j 6
```

### Qué hace

1. **Expande las playlists**: cada canción de una playlist se descarga por separado y en paralelo.
2. **Quita duplicados**: si una canción aparece dos veces (en el txt o en varias playlists), se descarga una sola vez.
3. **Salta lo ya descargado**: cada canción terminada se anota en `canciones/.descargadas.txt`. Si vuelves a correr el script con el mismo txt, solo baja lo que falta.
4. **Guarda las fallidas** en `canciones/fallidas.txt`.

### Reintentar las que fallaron

Al final, el script muestra el comando exacto. Es este:

```bash
ytb canciones/fallidas.txt
```

### Cancelar y continuar después

`Ctrl+C` espera a que terminen las descargas en curso y cancela el resto. Para continuar, vuelve a correr el mismo comando: lo ya descargado se salta.

### Volver a descargar algo

Borra su línea de `canciones/.descargadas.txt`, o el archivo entero para empezar de cero.

---

## Problemas comunes

| Síntoma | Solución |
|---|---|
| Errores de descarga o "Sign in to confirm" de repente | Actualiza yt-dlp: `pip install -U yt-dlp` |
| Error `429` / demasiadas peticiones | Baja los hilos: `ytb lista.txt -j 2` |
| `ffmpeg no está instalado` | `sudo dnf install ffmpeg` |
| `mpv no está instalado` | `sudo dnf install mpv` |
| El nombre o la URL se cortan | Escríbelos siempre entre comillas `"..."` |
| Aparece `enumerate_adapters: Initialization of an object has failed` | Es un mensaje del sistema y no afecta: ignóralo |

> Úsalo para contenido que tengas derecho a descargar. Descargar de YouTube puede ir contra sus términos de servicio.
