import os
from io import BytesIO
from typing import Any

from fastapi import FastAPI, UploadFile, Form, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from dotenv import load_dotenv

# Lokala moduler (relativa importer)
from .segmenter import segment_words
from .converters import to_srt, to_vtt


# --- Miljö & klientval -------------------------------------------------------
load_dotenv()  # läs .env från projektroten

LLM_PROVIDER = (os.getenv("LLM_PROVIDER") or "openai").lower()

if LLM_PROVIDER == "azure":
    # Azure OpenAI
    from openai import AzureOpenAI as OpenAIClient
    client = OpenAIClient(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    )
    # OBS: för Azure ska detta vara DITT "Deployment name" för Whisper
    DEFAULT_MODEL = os.getenv("AZURE_OPENAI_MODEL", "whisper-1")
else:
    # OpenAI direkt
    from openai import OpenAI as OpenAIClient
    client = OpenAIClient(api_key=os.getenv("OPENAI_API_KEY"))
    DEFAULT_MODEL = os.getenv("OPENAI_TRANSCRIBE_MODEL", "whisper-1")

print(f"[KortSubs] Provider={LLM_PROVIDER} Model={DEFAULT_MODEL}")


# --- FastAPI setup ------------------------------------------------------------
app = FastAPI(title="KortSubs", version="1.1.0")

APP_DIR = os.path.dirname(__file__)
app.mount("/static", StaticFiles(directory=os.path.join(APP_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(APP_DIR, "templates"))


# --- Hjälpfunktioner ----------------------------------------------------------
def parse_words_from_verbose_json(data: Any) -> list[dict]:
    """
    Returnerar list[{w: str, s: float, e: float}] från ett "verbose_json"-svar.
    Stödjer flera varianter:
    - {"segments":[{"words":[{"word","start","end"}, ...]}, ...]}
    - {"words":[{"word","start","end"}, ...]}
    """
    out: list[dict] = []

    if not isinstance(data, dict):
        return out

    # 1) segments -> words
    segments = data.get("segments") or []
    if isinstance(segments, list):
        for seg in segments:
            seg_words = (seg or {}).get("words") or []
            if isinstance(seg_words, list):
                for w in seg_words:
                    word = str((w or {}).get("word", "")).strip()
                    if not word:
                        continue
                    s = float((w or {}).get("start", 0.0))
                    e = float((w or {}).get("end", s))
                    out.append({"w": word.replace("\n", " ").strip(), "s": s, "e": e})

    # 2) top-level words
    top_words = data.get("words") or []
    if isinstance(top_words, list):
        for w in top_words:
            word = str((w or {}).get("word", "")).strip()
            if not word:
                continue
            s = float((w or {}).get("start", 0.0))
            e = float((w or {}).get("end", s))
            out.append({"w": word.replace("\n", " ").strip(), "s": s, "e": e})

    return sorted(out, key=lambda x: (x["s"], x["e"]))


# --- Routes -------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/transcribe")
async def transcribe(
    request: Request,
    file: UploadFile,
    outfmt: str = Form("srt"),
    language: str = Form("sv"),
    max_chars: int = Form(38),
    max_words: int = Form(9),
    max_dur: float = Form(2.5),
    min_dur: float = Form(0.8),
):
    """
    Tar en uppladdad video/ljudfil, anropar Whisper med ord-tidsstämplar, segmenterar kort,
    och returnerar SRT eller VTT för nedladdning.
    """

    # --- 1) Anropa API för transkribering med ordnivå ------------------------
    try:
        audio_bytes = await file.read()

        # Viktigt: verbose_json + timestamp_granularities=["word"] för ordnivå
        resp = client.audio.transcriptions.create(
            model=DEFAULT_MODEL,                  # OpenAI: "whisper-1"; Azure: DITT deployment-namn
            file=(file.filename, audio_bytes),    # (filnamn, bytes) stöds i openai>=1.x
            response_format="verbose_json",
            timestamp_granularities=["word"],
            language=language,
        )
    except Exception as e:
        # Visa tydligt i terminal + skicka tillbaka fel till klienten
        import traceback, sys
        print("=== Transcription error (API call) ===", file=sys.stderr)
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "provider": LLM_PROVIDER, "model": DEFAULT_MODEL},
        )

    # --- 2) Normalisera svaret till dict -------------------------------------
    import json as _json

    data = None
    try:
        if hasattr(resp, "model_dump"):
            data = resp.model_dump()
        elif hasattr(resp, "to_dict"):
            data = resp.to_dict()
        elif isinstance(resp, dict):
            data = resp
        elif isinstance(resp, (str, bytes)):
            s = resp.decode() if isinstance(resp, bytes) else resp
            data = _json.loads(s)
        else:
            data = getattr(resp, "__dict__", None)
    except Exception:
        data = None

    if not isinstance(data, dict):
        return JSONResponse(
            status_code=500,
            content={
                "error": "Transkribering gav oväntat format från leverantören.",
                "provider": LLM_PROVIDER,
                "model": DEFAULT_MODEL,
                "debug_type": str(type(resp)),
            },
        )

    # --- 3) Extrahera ord-tidsstämplar ---------------------------------------
    words = parse_words_from_verbose_json(data)

    if not words:
        # Vanliga orsaker:
        # - Fel modell (som ignorerar timestamp_granularities)
        # - Leverantörs-svar utan segments/words
        # - Felaktig konfiguration
        return JSONResponse(
            status_code=500,
            content={
                "error": "Inga ord-tidsstämplar i svaret. Kontrollera att modellen stödjer 'timestamp_granularities=[\"word\"]'.",
                "provider": LLM_PROVIDER,
                "model": DEFAULT_MODEL,
                "raw_keys": list(data.keys()),
            },
        )

    # --- 4) Segmentera kort ---------------------------------------------------
    cues = segment_words(
        words,
        max_chars=max_chars,
        max_words=max_words,
        max_dur=max_dur,
        min_dur=min_dur,
    )

    # --- 5) Skriv utdata ------------------------------------------------------
    if outfmt.lower() == "vtt":
        text = to_vtt(cues)
        ext = "vtt"
        mime = "text/vtt"
    else:
        text = to_srt(cues)
        ext = "srt"
        mime = "application/x-subrip"

    out_name = os.path.splitext(file.filename or "audio")[0] + f".kort.{ext}"
    return StreamingResponse(
        BytesIO(text.encode("utf-8")),
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{out_name}"'},
    )


# (Valfritt) egen favicon för att slippa 404-spam i loggarna.
# Lägg en fil "app/static/favicon.ico" för att aktivera nedan:
# from fastapi.responses import FileResponse
# @app.get("/favicon.ico")
# async def favicon():
#     path = os.path.join(APP_DIR, "static", "favicon.ico")
#     if os.path.exists(path):
#         return FileResponse(path)
#     return JSONResponse(status_code=404, content={"detail": "No favicon"})
