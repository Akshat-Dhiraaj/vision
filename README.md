# Vision Gesture Assistant

Local vision + audio gesture assistant built in small, tested steps.

## Python

This workspace venv was inspected on 2026-07-07 and is using:

- CPython 3.13.14
- pip 26.0.1
- virtualenv isolated from system site packages

The same version is recorded in `.python-version`.

## Setup

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Step 1 Check

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m vision_assistant.app --check-config
```
