# LifeOS Campus

LifeOS Campus is a hackathon demo project for a context-aware student assistant.
It simulates adaptive modes (sleep, commute, class, focus), notification filtering,
exam-week detection, and digital-twin style behavior summaries.

## Features

- Context-driven mode switching
- Smart notification scoring and digesting
- Telegram integration for alerts and digests
- Exam/crunch week detection
- Pattern memory and behavior summary
- Demo dashboard at `http://localhost:5000`

## Project Structure

- `demo_runner.py` - end-to-end hackathon demo flow
- `dashboard.py` - local dashboard
- `telegram_bot.py` - Telegram bot integration
- `notification_scorer.py` - scoring logic
- `notification_queue.py` - queue and digest behavior
- `exam_detector.py` - academic load detection
- `digital_twin.py` - behavior synthesis metrics

## Setup

```powershell
cd "C:\Users\jyoti\OneDrive\Desktop\lifeos-campus"
python -m pip install -r requirements.txt
```

## Run

Interactive run:

```powershell
python demo_runner.py
```

Auto-continue run (auto-press ENTER):

```powershell
"" | python demo_runner.py
```

## Notes

- Keep local secrets in `.env` (already gitignored).
- Use `.env.example` as a reference for environment variables.
