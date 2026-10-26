#!/usr/bin/env python3
"""Reproduce o descarga canciones de YouTube usando yt-dlp.

Uso:
    yt_music.py play "nombre de la canción o URL"
    yt_music.py download "nombre de la canción o URL" [-o carpeta] [-f mp3]

Las descargas se guardan por defecto en ./canciones, dentro del directorio
desde donde se ejecuta el comando.

Requiere: yt-dlp (pip install yt-dlp), ffmpeg (para convertir audio)
y mpv (para reproducir).
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

import yt_dlp


def resolve(query: str) -> str:
    """Devuelve la URL tal cual o el primer resultado de búsqueda en YouTube."""
    if query.startswith(("http://", "https://")):
        return query
    return f"ytsearch1:{query}"


def get_info(query: str) -> dict:
    opts = {"quiet": True, "no_warnings": True, "format": "bestaudio/best", "noplaylist": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(resolve(query), download=False)
    # Las búsquedas devuelven una "playlist" con un solo resultado
    if "entries" in info:
        entries = list(info["entries"])
        if not entries:
            sys.exit(f"No se encontraron resultados para: {query}")
        info = entries[0]
    return info


def play(query: str) -> None:
    if not shutil.which("mpv"):
        sys.exit("mpv no está instalado (sudo dnf install mpv)")
    info = get_info(query)
    print(f"▶ Reproduciendo: {info.get('title')} [{info.get('duration_string', '?')}]")
    print("  (q para salir, espacio para pausar, ←/→ para adelantar)")
    # mpv usa yt-dlp internamente, así que basta con pasarle la URL del video
    subprocess.run(["mpv", "--no-video", "--ytdl-format=bestaudio", info["webpage_url"]])


def download(query: str, out_dir: Path, codec: str) -> None:
    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg no está instalado (sudo dnf install ffmpeg)")
    out_dir.mkdir(parents=True, exist_ok=True)
    opts = {
        "format": "bestaudio/best",
        "noplaylist": True,
        "outtmpl": str(out_dir / "%(title)s.%(ext)s"),
        "postprocessors": [
            {"key": "FFmpegExtractAudio", "preferredcodec": codec, "preferredquality": "192"},
            {"key": "FFmpegMetadata"},
            {"key": "EmbedThumbnail"},
        ],
        "writethumbnail": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([resolve(query)])
    print(f"✔ Guardado en {out_dir.resolve()}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Reproduce o descarga canciones de YouTube")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_play = sub.add_parser("play", help="Reproducir audio en streaming")
    p_play.add_argument("query", help="Búsqueda o URL")

    p_dl = sub.add_parser("download", help="Descargar como audio")
    p_dl.add_argument("query", help="Búsqueda o URL")
    p_dl.add_argument("-o", "--output", type=Path, default=Path.cwd() / "canciones",
                      help="Carpeta destino (por defecto ./canciones en el directorio actual)")
    p_dl.add_argument("-f", "--format", default="mp3", choices=["mp3", "m4a", "opus", "flac"], help="Formato")

    args = parser.parse_args()
    try:
        if args.cmd == "play":
            play(args.query)
        else:
            download(args.query, args.output, args.format)
    except KeyboardInterrupt:
        print("\nCancelado.")


if __name__ == "__main__":
    main()
