#!/usr/bin/env python3


import argparse
import shutil
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import yt_dlp
from yt_dlp.extractor.youtube import YoutubeIE
from yt_dlp.plugins import load_all_plugins

ARCHIVE_NAME = ".descargadas.txt"
FAILED_NAME = "fallidas.txt"

print_lock = threading.Lock()


def log(msg: str) -> None:
    with print_lock:
        print(msg, flush=True)


class SilentLogger:
    """Evita que los mensajes de yt-dlp de varios hilos se mezclen en la consola."""

    def debug(self, msg):
        pass

    def info(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        pass


def read_urls(path: Path) -> list[str]:
    urls = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and line not in urls:
            urls.append(line)
    return urls


def expand(url: str) -> list[tuple[str, str]]:
    """Convierte una URL en una lista de (url_video, id_archivo).

    Los videos sueltos de YouTube se resuelven sin hacer peticiones; las
    playlists (y otros sitios) se consultan en modo "flat", que solo lista
    los videos sin extraer cada uno.
    """
    if YoutubeIE.suitable(url):
        return [(url, f"youtube {YoutubeIE.get_temp_id(url)}")]

    opts = {"quiet": True, "extract_flat": "in_playlist", "logger": SilentLogger()}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    def walk(entry):
        if entry.get("_type") == "playlist":
            for sub in entry.get("entries") or []:
                if sub:
                    yield from walk(sub)
        else:
            key = (entry.get("ie_key") or entry.get("extractor_key") or "generic").lower()
            yield entry.get("url") or entry.get("webpage_url"), f"{key} {entry['id']}"

    return list(walk(info))


def load_archive(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}


def download_one(url: str, out_dir: Path, codec: str, archive: Path) -> str:
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
        # yt-dlp escribe el archivo de registro con bloqueo, así que es seguro entre hilos
        "download_archive": str(archive),
        "retries": 10,
        "fragment_retries": 10,
        "quiet": True,
        "noprogress": True,
        "logger": SilentLogger(),
    }
    # Cada hilo usa su propia instancia: YoutubeDL no es seguro para compartir
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
    return (info or {}).get("title", url)


def main() -> None:
    parser = argparse.ArgumentParser(description="Descarga en paralelo las canciones de un txt")
    parser.add_argument("lista", type=Path, help="Archivo .txt con una URL por línea")
    parser.add_argument("-o", "--output", type=Path, default=Path.cwd() / "canciones",
                        help="Carpeta destino (por defecto ./canciones en el directorio actual)")
    parser.add_argument("-f", "--format", default="mp3", choices=["mp3", "m4a", "opus", "flac"], help="Formato")
    parser.add_argument("-j", "--jobs", type=int, default=4, help="Descargas simultáneas (por defecto 4)")
    args = parser.parse_args()

    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg no está instalado (sudo dnf install ffmpeg)")
    if not args.lista.is_file():
        sys.exit(f"No existe el archivo: {args.lista}")

    # Cargar los plugins de yt-dlp antes de crear hilos: si varios hilos
    # los cargan a la vez, se registran dos veces y yt-dlp lanza errores
    load_all_plugins()

    urls = read_urls(args.lista)
    if not urls:
        sys.exit("El archivo no contiene URLs.")

    args.output.mkdir(parents=True, exist_ok=True)
    archive = args.output / ARCHIVE_NAME
    failed_path = args.output / FAILED_NAME
    failed: list[str] = []

    # 1. Expandir playlists en paralelo
    log(f"Leyendo {len(urls)} URL(s)...")
    tracks: dict[str, str] = {}  # id_archivo -> url (también elimina duplicados)
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = {pool.submit(expand, u): u for u in urls}
        for fut in as_completed(futures):
            try:
                for track_url, archive_id in fut.result():
                    tracks.setdefault(archive_id, track_url)
            except Exception as e:
                log(f"✘ No se pudo leer {futures[fut]}: {e}")
                failed.append(futures[fut])

    # 2. Saltar las ya descargadas
    done = load_archive(archive)
    pending = [(aid, u) for aid, u in tracks.items() if aid not in done]
    skipped = len(tracks) - len(pending)
    log(f"{len(tracks)} canción(es): {skipped} ya descargada(s), {len(pending)} pendiente(s)\n")

    # 3. Descargar en paralelo
    start = time.monotonic()
    ok = 0
    total = len(pending)
    pool = ThreadPoolExecutor(max_workers=args.jobs)
    try:
        futures = {pool.submit(download_one, u, args.output, args.format, archive): u for _, u in pending}
        for i, fut in enumerate(as_completed(futures), 1):
            url = futures[fut]
            try:
                title = fut.result()
                ok += 1
                log(f"[{i}/{total}] ✔ {title}")
            except Exception as e:
                failed.append(url)
                reason = str(e).removeprefix("ERROR: ").splitlines()[0]
                log(f"[{i}/{total}] ✘ {url} — {reason}")
    except KeyboardInterrupt:
        log("\nCancelando... se terminan las descargas en curso (Ctrl+C otra vez para forzar).")
        pool.shutdown(wait=True, cancel_futures=True)
        log("Lo descargado quedó registrado; vuelve a correr el comando para continuar.")
        sys.exit(130)
    pool.shutdown()

    # 4. Resumen
    elapsed = time.monotonic() - start
    log(f"\nListo en {elapsed:.0f}s: {ok} descargada(s), {skipped} saltada(s), {len(failed)} fallida(s)")
    if failed:
        failed_path.write_text("\n".join(failed) + "\n", encoding="utf-8")
        log(f"Las fallidas se guardaron en {failed_path} — reintenta con:")
        log(f"  python3 {Path(__file__).resolve()} {failed_path}")
    elif failed_path.exists():
        failed_path.unlink()
    log(f"Canciones en {args.output.resolve()}")


if __name__ == "__main__":
    main()
