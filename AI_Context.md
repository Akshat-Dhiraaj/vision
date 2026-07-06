# AI Context

Last updated: 2026-07-07

## Project

Local vision + audio gesture assistant.

The system should watch a webcam, answer questions like "how many fingers am I showing?", learn assigned hand symbols, and safely map confirmed symbols to actions such as opening websites, local folders, or applications. The assistant should use local LM Studio models where useful, but the first reliable signal should come from a deterministic hand landmark and gesture pipeline.

## Standing Instructions

- Keep this file updated whenever project context, decisions, status, or next steps change.
- Keep `Architecture.md` updated whenever high-level or low-level flow changes.
- Prefer no code when configuration, documentation, or simpler structure solves the problem.
- Keep code simple, modular, and easy to test.
- Avoid duplicated logic.
- Make minimal code changes.
- Build in small steps.
- Each step must have explicit tests before moving forward.
- Do not give the LLM arbitrary shell or system access.
- Use allowlisted actions only.
- Prefer reliable landmark geometry for finger counting over VLM guessing.

## Current Decisions

- Primary vision engine: OpenCV webcam capture plus MediaPipe Hand Landmarker or Gesture Recognizer.
- Primary finger-count approach: 21 hand landmarks, normalized geometry, confidence checks, and temporal smoothing.
- Primary LLM role: local LM Studio conversation, structured responses, tool routing, and confirmation logic.
- Optional VLM role: still-image fallback/debugging only, not continuous per-frame command recognition.
- First interface: typed CLI before audio.
- First action executor: safe test website only.
- Safety model: action registry, validation, cooldowns, and confirmation for sensitive actions.

## Current Files

- `VISION_GESTURE_ASSISTANT_PIPELINE.md`: researched pipeline, references, quotes, and major phased architecture.
- `AI_Context.md`: durable project memory and current state.
- `Architecture.md`: high-level and low-level system flow.
- `Implementation_Steps.md`: small implementation steps with rigorous test gates.
- `README.md`: setup notes, Python version, and Step 1 verification commands.
- `.python-version`: exact Python version used by the current workspace venv.
- `requirements.txt`: installable Python dependencies for the implemented code and tests.
- `vision_assistant/`: Python package skeleton, config files, config loader, CLI smoke path, and tests.

## Current Status

- Research plan exists and has been verified against official docs, papers, and model cards.
- Step 0 project skeleton is in place as a prerequisite for Step 1.
- Step 1 configuration foundation is implemented with YAML loading, action-name allowlist checks, URL/path validation helpers, and tests.
- The workspace `.venv` uses CPython 3.13.14 with pip 26.0.1.

## Immediate Next Goal

Move to Step 2: add a camera smoke test with clean capture release behavior.

## Open Questions

- Whether LM Studio server is already installed and running.
- Webcam device index to use first, usually `0`.
- Which local LM Studio text model to use for the first non-vision chat loop.
- Whether audio should use push-to-talk, wake word, or VAD when implemented later.
