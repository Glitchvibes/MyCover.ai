# MyCover.ai

**MyCover.ai** is a consent-first voice lab for building authorized voice profiles, organizing recordings, tracking dataset versions, and running repeatable model experiments.

> Status: early application scaffold. This repository does not yet contain trained weights or a working cloning model. A compatible, properly licensed inference/training backend must be installed and configured before voice generation is available.

## Features in this starter
- Create voice profiles with a consent attestation.
- Upload and validate WAV recordings.
- Track dataset revisions and experiment history.
- FastAPI backend and a small Portuguese web interface.
- Clear adapter boundary for adding a real local TTS/voice-conversion engine.

## Run
```bash
python -m venv .venv
source .venv/bin/activate # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000

## Safety & privacy
Only process your own voice or recordings with explicit, informed permission. Do not impersonate others, deceive listeners, or bypass identity checks. Keep generated audio disclosed as synthetic. Record consent, protect recordings, and provide deletion/export workflows before public deployment.

## Roadmap
1. Profile and dataset management (scaffold).
2. Audio segmentation, transcription, and dataset-quality checks.
3. Integrate a licensed local synthesis/adaptation backend.
4. Evaluate improvements on held-out recordings before promoting a model version.
5. Add authentication, encrypted storage, quotas, audit logs, and deployment hardening.

Never commit private recordings, model weights, API keys, or secrets. Review code, model, and dataset licenses separately before commercial use.
