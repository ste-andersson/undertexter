# KortSubs
Webbapp (FastAPI) som låter dig **ladda upp en video/ljudfil** och få **korta undertexter** (SRT eller WebVTT) för import i Kdenlive. Ord-tidsstämplar hämtas från OpenAI Whisper via API och segmenteras till korta enradiga cues.

> Obs: För **ordnivå** krävs `whisper-1` + `response_format=verbose_json` + `timestamp_granularities=["word"]`. De nya `gpt-4o(-mini)-transcribe` stöder i dagsläget inte denna parameter, så välj `whisper-1` som modell/deployment.

## Kom igång

### 1) Miljövariabler
Skapa `.env` i projektroten (se `.env.example`). Stöd för både **OpenAI** och **Azure OpenAI**.

**OpenAI:**
```
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_TRANSCRIBE_MODEL=whisper-1
```

**Azure OpenAI:**
```
LLM_PROVIDER=azure
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_API_VERSION=2025-01-01-preview
AZURE_OPENAI_MODEL=whisper-1   # deployment-namnet
```

> Spara aldrig nycklar i Git. Använd `.env` och håll den privat.

### 2) Installera
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3) Kör
```bash
uvicorn app.main:app --reload
```
Öppna `http://127.0.0.1:8000` och ladda upp din fil. Välj SRT/VTT. Ladda ner resultatet.

### Docker (valfritt)
```bash
docker build -t kortsubs .
docker run --env-file .env -p 8000:8000 kortsubs
```

## Hur det funkar
1. Laddar upp video/ljud → skickas till OpenAI/Azure OpenAI **Whisper** med ord-tidsstämplar.
2. Ordlistan segmenteras till **korta, läsbara** cues (max tecken/ord/tid är konfigurerbart).
3. Genererar SRT eller WebVTT för import till **Kdenlive** (stöder SRT/VTT/SBV/ASS).

## Kända begränsningar
- Ord-tidsstämplar kräver `whisper-1` (OpenAI eller Azure deployment). 
- Stora filer: kör servern bakom en proxy eller justera `uvicorn`/`nginx` för större uppladdningar.

## Licens
MIT
