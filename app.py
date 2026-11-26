import os, re, uuid, time, shutil, subprocess
from pathlib import Path
from flask import Flask, request, jsonify, send_file, send_from_directory
import yt_dlp

app = Flask(__name__, static_folder="static")

DOWNLOAD_DIR = Path(os.environ.get("DOWNLOAD_DIR", "/tmp/igdl"))
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
PASSWORD = os.environ.get("APP_PASSWORD", "")      # boşsa şifre istemez
COOKIES = os.environ.get("COOKIES_FILE", "")        # Instagram giriş isterse (cookies.txt)
MAX_AGE = 60 * 60                                   # dosyalar 1 saat sonra silinir
URL_RE = re.compile(r"^https?://(www\.)?instagram\.com/(p|reel|reels|tv|stories)/\S+$", re.I)


def cleanup():
    now = time.time()
    for f in DOWNLOAD_DIR.iterdir():
        if now - f.stat().st_mtime > MAX_AGE:
            f.unlink(missing_ok=True)


def authorized():
    if not PASSWORD:
        return True
    given = request.headers.get("X-Key") or request.args.get("k", "")
    return given == PASSWORD


def fit_to_story(src: Path) -> Path:
    """1080x1920 (9:16), H.264 + AAC. ffmpeg yoksa orijinali döndürür."""
    if not shutil.which("ffmpeg"):
        return src
    out = src.with_name(src.stem + "_story.mp4")
    cmd = [
        "ffmpeg", "-y", "-i", str(src),
        "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,"
               "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,fps=30",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out),
    ]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0 or not out.exists():
        return src
    src.unlink(missing_ok=True)
    return out


@app.get("/")
def index():
    return send_from_directory("static", "index.html")


@app.post("/api/download")
def download():
    if not authorized():
        return jsonify(error="Şifre yanlış."), 401
    cleanup()
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip().split("?")[0]
    if not URL_RE.match(url):
        return jsonify(error="Geçerli bir Instagram gönderi, reel veya hikaye linki yapıştır."), 400

    vid = uuid.uuid4().hex[:12]
    has_session = False
    opts = {
        "outtmpl": str(DOWNLOAD_DIR / f"{vid}.%(ext)s"),
        "format": "best[ext=mp4]/best",
        "noplaylist": True,
        "playlist_items": "1",
        "quiet": True,
        "no_warnings": True,
    }
    if COOKIES and Path(COOKIES).exists():
        # Secret File salt okunur; yt-dlp cookies'i geri yazmak ister, o yüzden kopyalıyoruz
        tmp_cookies = DOWNLOAD_DIR / f"cookies_{vid}.txt"
        shutil.copyfile(COOKIES, tmp_cookies)
        has_session = "sessionid" in tmp_cookies.read_text(errors="ignore")
        opts["cookiefile"] = str(tmp_cookies)

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            path = Path(ydl.prepare_filename(info))
    except yt_dlp.utils.DownloadError as e:
        raw = str(e).replace("\n", " ")[-300:]
        ck = ("cookies yüklü, sessionid " + ("VAR" if has_session else "YOK")) if (COOKIES and Path(COOKIES).exists()) else "cookies DOSYASI BULUNAMADI"
        return jsonify(error=f"[{ck}] {raw}"), 502
    except Exception as e:
        ck = "cookies yüklü" if (COOKIES and Path(COOKIES).exists()) else "cookies DOSYASI YOK"
        return jsonify(error=f"[{ck}] {type(e).__name__}: {str(e)[-300:]}"), 500

    finally:
        (DOWNLOAD_DIR / f"cookies_{vid}.txt").unlink(missing_ok=True)

    if not path.exists():
        return jsonify(error="Dosya bulunamadı."), 500

    if data.get("story"):
        path = fit_to_story(path)

    return jsonify(id=path.name, size=path.stat().st_size)


@app.get("/file/<name>")
def file(name):
    if not authorized():
        return "Yetkisiz", 401
    p = (DOWNLOAD_DIR / name).resolve()
    if p.parent != DOWNLOAD_DIR.resolve() or not p.exists():
        return "Bulunamadı", 404
    return send_file(p, mimetype="video/mp4", as_attachment=request.args.get("dl") == "1",
                     download_name="autoglym-video.mp4")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
