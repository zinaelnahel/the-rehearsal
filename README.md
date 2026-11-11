# The Rehearsal

Practise real-life conversations in **English, German or Spanish**: apartment viewings, job interviews, course enquiries and difficult conversations.

**[Open the app](https://the-rehearsal-lab.vercel.app)** · The backend may need a moment to wake up.

## What it does

- Builds editable goals from your situation, pasted text, PDF/DOCX or reviewed media transcript.
- Offers AI role-play, optional voice, feedback and replay of a missed goal.
- Links source-backed answers to document passages or video timestamps; missing facts stay unconfirmed.
- Includes three samples: a Madrid listing PDF, a Spanish interview video with a prepared transcript, and a fictional boundary-setting voice message. Review transcripts before practising; edited text does not retain excerpt timestamps. See [sample provenance](samples/README.md).
- Reads image-based PDFs with server-side OCR and asks you to review the text first.
- Saves rehearsals in your browser when you explicitly choose to save them.

## How it works

**Next.js/React → FastAPI → LangChain/OpenAI.** A bounded agent can retrieve passages, check quotes, inspect goals and request practice guidance. Session memory holds the source, conversation and goal progress. The deployed retrieval method is multilingual lexical matching, without semantic embeddings. Exact-quote checks and a separate model review validate source claims. Voice uses OpenAI transcription and speech generation; PDF OCR uses offline Tesseract.

## Run locally

Requires **Python 3.12** and **Node.js 22**. In PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --require-hashes -r backend/requirements.lock
Copy-Item .env.example .env
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

In a second terminal:

```powershell
npm install
npm run dev
```

Open **http://localhost:3000**. Demo chat needs no API key. For live chat, set `REHEARSAL_MODE=live` and `OPENAI_API_KEY` in `.env`, then restart the backend. Voice additionally requires `SPEECH_ENABLED=true` and FFmpeg. PDF OCR requires Tesseract with English, German and Spanish data; the deployment Docker image includes it.

## Limits and privacy

Uploads are limited to **4 MB**; OCR supports up to **8 image-based pages**. Automated listing-link import is not offered: paste the listing text or upload its PDF. OCR and captions can contain mistakes, and AI feedback still needs human judgment.

Live mode sends source text and conversation to OpenAI after consent. Voice sends audio separately after consent; OCR sends no PDF images to OpenAI. Server sessions expire and do not survive backend restarts. Browser-saved rehearsals remain until you delete them. There are no accounts or cross-device sync.

## Technical details

- [Architecture and project evidence](CAPSTONE.md)
- [Evaluation methods and results](EVALUATION.md)
- [Deployment](DEPLOYMENT.md) · [Security](SECURITY.md)
- [Voice and media](docs/MULTIMODAL.md) · [Browser storage](docs/REHEARSAL_LIBRARY.md)

Independent project inspired by *The Rehearsal*. No affiliation or endorsement.
