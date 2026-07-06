# Local Vision + Audio Gesture Assistant Pipeline

Last researched and verified: 2026-07-07, using current official docs, model pages, and research papers.

## 1. Goal

Build a local assistant that can:

1. Watch your hand through a webcam.
2. Answer questions such as "how many fingers am I showing?"
3. Learn assigned hand symbols.
4. Map confirmed symbols to safe actions such as opening websites, folders, or applications.
5. Use a local LM Studio model for conversation, routing, structured tool choices, and explanations.

The recommended architecture is hybrid:

- Computer vision component: fast, deterministic hand tracking, finger counting, gesture recognition.
- Local LLM component: conversation, command interpretation, action selection, confirmations.
- Optional vision-language model: fallback for scene description or ambiguous visual questions, not the primary per-frame finger counter.

This keeps the system fast and reliable while still letting the chatbot feel natural.

## 2. Research Anchors

### Official documentation

- MediaPipe Hand Landmarker: detects hand landmarks, world landmarks, and handedness from image, video, or live stream input. Docs: https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker
- MediaPipe Hand Landmarker Python: live stream mode uses `detect_async`, timestamps, and result callbacks; current docs mark MediaPipe Solutions Preview as an early release. Docs: https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker/python
- MediaPipe Gesture Recognizer: recognizes real-time hand gestures and returns gesture categories plus landmarks. Docs: https://developers.google.com/edge/mediapipe/solutions/vision/gesture_recognizer
- MediaPipe Gesture Recognizer Python: live stream mode uses `recognize_async`; if the recognizer is busy, new frames may be ignored, so the app must tolerate skipped frames; current docs mark MediaPipe Solutions Preview as an early release. Docs: https://developers.google.com/edge/mediapipe/solutions/vision/gesture_recognizer/python
- OpenCV VideoCapture: standard webcam capture loop, `isOpened`, `read`, `release`, and window cleanup behavior. Docs: https://docs.opencv.org/4.x/dd/d43/tutorial_py_video_display.html and https://docs.opencv.org/4.x/d8/dfe/classcv_1_1VideoCapture.html
- LM Studio OpenAI-compatible API: local server can be used by changing the client base URL to `http://localhost:1234/v1`. Docs: https://lmstudio.ai/docs/developer/openai-compat
- LM Studio developer docs: local APIs, REST, SDKs, OpenAI-compatible endpoints, structured output, and tool calling. Docs: https://lmstudio.ai/docs/developer
- LM Studio Python image input: VLMs can accept images through the Python SDK when a compatible vision-language model is loaded; the current Python SDK docs list JPEG, PNG, and WebP image support. Docs: https://lmstudio.ai/docs/python/llm-prediction/image-input
- Python `webbrowser`: opens URLs through the system browser. Docs: https://docs.python.org/3/library/webbrowser.html
- Python `os.startfile`: Windows-style "open like double click" for associated files and folders. Use `webbrowser` for URLs. Docs: https://docs.python.org/3/library/os.html
- Python `subprocess`: spawn and manage local processes. Docs: https://docs.python.org/3/library/subprocess.html
- Microsoft ShellExecute: native Windows API for opening files, folders, applications, and object verbs. Use `webbrowser` for URLs. Docs: https://learn.microsoft.com/en-us/windows/win32/shell/launch
- PyAutoGUI: controls mouse and keyboard for GUI fallback automation. Docs: https://pyautogui.readthedocs.io/
- faster-whisper: local Whisper inference using CTranslate2, designed for speed and lower memory use. Docs: https://github.com/SYSTRAN/faster-whisper

### Research papers and model reports

- MediaPipe Hands, 2020: palm detector plus hand landmark model for real-time on-device tracking from RGB camera. Paper: https://arxiv.org/abs/2006.10214
- On-device Real-time Hand Gesture Recognition, 2021: hand skeleton tracker plus heuristic or neural gesture classifier, directly matching this project shape. Paper: https://arxiv.org/abs/2111.00038
- Whisper, 2022/ICML 2023: robust speech recognition trained on large-scale weak supervision. Paper: https://arxiv.org/abs/2212.04356 and https://proceedings.mlr.press/v202/radford23a.html
- Qwen2.5-VL, 2025: strong open vision-language model family with image/video understanding and visual agent capabilities. Paper: https://arxiv.org/abs/2502.13923 and model card: https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct
- Gemma 3, 2025: open multimodal model family with image understanding and long context. Report: https://arxiv.org/html/2503.19786v1 and model card: https://huggingface.co/google/gemma-3-27b-it
- LLaVA-OneVision, 2024: open multimodal model covering single-image, multi-image, and video tasks. Paper: https://arxiv.org/abs/2408.03326
- InternVL3.5, 2025: open-source multimodal model family with reasoning, efficiency, GUI interaction, and agentic capabilities. Paper: https://arxiv.org/abs/2508.18265
- Visual hand gesture recognition survey, 2025: useful for broader method/dataset choices beyond the initial build. Paper: https://arxiv.org/abs/2507.04465

## 3. Core Design Decision

Do not make the LLM stare at every webcam frame and guess the number of fingers. A VLM can answer image questions, but for commands and repeated hand-symbol recognition it is slower, more expensive computationally, and less stable than a dedicated hand landmark pipeline.

Use this split:

- MediaPipe or similar hand tracker: "What is the hand doing right now?"
- Finger/gesture module: "This is 3 fingers" or "this is symbol: OPEN_BROWSER."
- Temporal smoother: "This has been stable for 400 ms."
- LM Studio model: "The user asked how many fingers; answer plainly" or "the user made OPEN_DOCS, should I call the open_website tool?"
- Action executor: "Only run an allowlisted action with validated arguments."

## 4. System Architecture

```text
Camera
  -> OpenCV frame capture
  -> MediaPipe Hand Landmarker or Gesture Recognizer
  -> Landmark normalization and feature extraction
  -> Finger counter / gesture classifier
  -> Temporal smoothing and confidence gating
  -> Event bus
  -> Local assistant loop
      -> Speech-to-text or typed question
      -> LM Studio chat model
      -> Structured tool/action decision
  -> Safe action executor
      -> open URL
      -> open folder
      -> launch app
      -> optional GUI automation
  -> Voice/text response and audit log
```

## 5. Data Flow

Each camera frame becomes a compact observation:

```json
{
  "timestamp_ms": 123456,
  "hands": [
    {
      "handedness": "Right",
      "landmarks_2d": "21 normalized points",
      "landmarks_3d_world": "21 metric-space points if available",
      "finger_count": 4,
      "gesture": "four",
      "confidence": 0.94
    }
  ],
  "stable_observation": {
    "gesture": "four",
    "duration_ms": 480,
    "confidence": 0.91
  }
}
```

The LLM should receive this structured observation instead of raw frames for normal finger-count and command tasks.

## 6. Finger Counting Plan

Start with MediaPipe Hand Landmarker because it returns 21 hand keypoints and handedness.

Algorithm:

1. Capture webcam frames with OpenCV.
2. Send frames to MediaPipe in live stream or video mode.
3. Normalize landmarks:
   - Wrist becomes origin.
   - Palm size becomes scale.
   - Optional: rotate into hand-local coordinates so hand tilt matters less.
4. Determine finger extension:
   - Index, middle, ring, pinky: use tip, DIP, PIP, MCP angles and distances.
   - Thumb: use handedness-aware angle and distance from palm, not just y-position.
5. Count extended fingers.
6. Reject frames with low detection/tracking confidence.
7. Smooth over time:
   - Keep a rolling window, for example 10 to 20 frames.
   - Accept a count only when the same result is stable for 250 to 500 ms.
8. Answer questions from the last stable observation.

First success target:

- Single hand, frontal webcam, normal lighting.
- Counts 0 to 5.
- Response latency under 500 ms after the question.
- Accuracy above 95 percent on your own validation clips.

## 7. Gesture Recognition Plan

Use three levels, growing only when needed.

Level 1: Built-in gestures

- Use MediaPipe Gesture Recognizer for canned gestures such as `Open_Palm`, `Closed_Fist`, `Pointing_Up`, `Thumb_Down`, `Thumb_Up`, `Victory`, and `ILoveYou`.
- Good for immediate prototypes.

Level 2: Custom static symbols

- Use normalized hand landmarks as features.
- Start with simple models:
  - rules for obvious shapes,
  - k-nearest neighbors,
  - logistic regression,
  - random forest,
  - small MLP.
- Store training data as landmarks first, not images, unless you need image debugging.
- Collect roughly 50 to 200 samples per gesture across lighting, distance, hand angle, and speed.
- Split by recording session so validation is not accidentally too easy.

Level 3: Dynamic gestures

- Use 0.5 to 2 second landmark sequences.
- Features:
  - normalized landmarks,
  - velocity,
  - finger angles,
  - palm orientation,
  - left/right hand flag.
- Model choices:
  - temporal convolution network,
  - LSTM/GRU,
  - small Transformer encoder.
- Add start/end detection so a wave or swipe does not trigger repeatedly.

## 8. Local LM Studio Role

LM Studio is best used as the local reasoning and conversation layer.

Use cases:

- Convert user speech/text into intent:
  - "How many fingers?"
  - "What symbol did I just make?"
  - "Assign this sign to open YouTube."
- Produce responses:
  - "You are showing four fingers."
  - "I saw the Docs gesture. Opening your Documents folder."
- Choose from tools with structured output:
  - `answer_finger_count`
  - `register_gesture`
  - `open_website`
  - `open_folder`
  - `launch_app`
  - `ask_confirmation`
- Keep a short memory of mappings:
  - gesture name,
  - action,
  - confidence threshold,
  - confirmation requirement.

LM Studio configuration:

- Start local server on the default port, usually `1234`.
- Use OpenAI-compatible client with `base_url="http://localhost:1234/v1"`.
- Prefer structured output or tool calling for action decisions.
- Keep the model away from arbitrary shell execution.

Optional VLM use:

- Ask a local VLM to inspect a still image only when the landmark system is uncertain.
- Use VLMs for natural visual Q&A, scene description, or debugging.
- Candidate local VLM families to benchmark if supported by LM Studio or another local VLM runtime: Qwen2.5-VL, Gemma 3 or newer Gemma vision models, LLaVA-OneVision, InternVL, SmolVLM, and Moondream.
- Always benchmark on your own webcam examples; general VQA scores do not guarantee finger-count reliability.

## 9. Audio Plan

Start with typed questions, then add speech once the vision loop works.

Speech-to-text:

- Use faster-whisper for local transcription.
- Add voice activity detection or push-to-talk to avoid accidental command triggers.
- Keep command phrases short:
  - "How many fingers?"
  - "Assign this gesture."
  - "Open mapped action."
  - "Cancel."

Text-to-speech:

- Optional at first.
- Use Windows built-in voices, pyttsx3, Piper, or another local TTS engine later.

Important design rule:

- Speech can ask questions.
- Stable gestures can propose actions.
- Destructive or sensitive actions should require confirmation by speech, keyboard, or a second gesture.

## 10. Action Execution Plan

Never let the LLM execute arbitrary commands. Give it a small action registry.

Example action registry:

```yaml
actions:
  open_youtube:
    type: website
    url: "https://www.youtube.com"
    confirm: false

  open_documents:
    type: folder
    path: "C:\\Users\\<you>\\Documents"
    confirm: false

  open_lm_studio:
    type: app
    command: "C:\\Path\\To\\LM Studio.exe"
    confirm: true
```

Executor choices:

- Websites: Python `webbrowser.open`.
- Folders and files on Windows: `os.startfile` or ShellExecute.
- Applications: configured absolute paths, Start Menu shortcuts, or `subprocess.Popen` with validation.
- GUI-only fallback: PyAutoGUI, used sparingly and only for known workflows.

Safety gates:

- Allowlist every action.
- Validate URLs and local paths.
- Require a stable gesture for at least 300 to 800 ms.
- Add cooldowns so one held gesture does not open the same thing repeatedly.
- Add a global "pause listening" and "cancel" gesture.
- Log every proposed and executed action.

## 11. Proposed File/Module Layout

```text
vision_assistant/
  app.py
  config/
    actions.yaml
    gestures.yaml
    settings.yaml
  src/
    camera.py
    mediapipe_hands.py
    landmarks.py
    finger_count.py
    gesture_builtin.py
    gesture_custom.py
    temporal_smoothing.py
    audio_stt.py
    lmstudio_client.py
    intent_router.py
    action_registry.py
    action_executor.py
    safety.py
    event_log.py
  data/
    gesture_samples/
    validation_clips/
  tests/
    test_finger_count.py
    test_action_validation.py
    test_temporal_smoothing.py
```

## 12. Milestones

### Phase 0: Baseline setup

Deliverables:

- Confirm webcam works through OpenCV.
- Confirm MediaPipe can return landmarks.
- Confirm LM Studio local server responds to a chat request.
- Confirm a safe test URL can open through Python.

Exit criteria:

- Camera preview works.
- Landmarks draw on the hand.
- Local LLM says hello.
- `open_test_page` opens a harmless website.

### Phase 1: Finger-count MVP

Deliverables:

- Count 0 to 5 fingers on one hand.
- Show overlay with landmarks, count, confidence, and stable count.
- Answer typed question: "How many fingers am I showing?"

Exit criteria:

- Works across at least 5 short validation clips per count.
- Stable result latency is acceptable.
- Low-confidence frames are rejected instead of guessed.

### Phase 2: Safe action registry

Deliverables:

- YAML action registry.
- Website, folder, and app actions.
- Cooldown and confirmation policy.
- Audit log.

Exit criteria:

- The LLM can only choose registered actions.
- Unknown actions are rejected.
- Test actions work on Windows.

### Phase 3: Custom static gestures

Deliverables:

- Gesture recording tool.
- Landmark dataset.
- Simple classifier.
- Confusion matrix report.

Exit criteria:

- At least 5 custom gestures.
- Accuracy above 90 to 95 percent on held-out sessions.
- False triggers are rare during normal hand movement.

### Phase 4: Audio chatbot loop

Deliverables:

- Push-to-talk or VAD.
- Local STT.
- LM Studio intent routing.
- Spoken or text response.

Exit criteria:

- You can ask the assistant about finger count by voice.
- Commands require confirmation when configured.
- "Cancel" reliably stops pending actions.

### Phase 5: Dynamic gestures

Deliverables:

- Sequence recorder.
- Temporal classifier.
- Start/end gesture segmentation.
- Per-gesture cooldown.

Exit criteria:

- Dynamic gestures trigger once per intentional movement.
- Static and dynamic recognizers do not fight each other.

### Phase 6: VLM fallback

Deliverables:

- Capture still frame on demand.
- Send image to local LM Studio VLM if available.
- Compare VLM answer against landmark answer for debugging.

Exit criteria:

- VLM is optional.
- If no VLM is loaded, the core assistant still works.

### Phase 7: Packaging

Deliverables:

- One command to start the assistant.
- Config editor or simple CLI for mapping gestures.
- Startup checks for camera, model server, and action registry.

Exit criteria:

- Non-developer daily use is possible.
- Failures are explained clearly.

## 13. Evaluation Metrics

Track these from day one:

- Finger count accuracy per number.
- Gesture classifier accuracy and confusion matrix.
- False activations per hour.
- Missed intentional gestures per 100 attempts.
- Time from gesture to recognized event.
- Time from question to answer.
- Action execution success rate.
- Number of unsafe action attempts blocked.

Suggested targets:

- Finger count: 95 percent or better in your normal setup.
- Custom static gestures: 90 to 95 percent before mapping to real actions.
- False activation: fewer than 1 per hour for action gestures.
- End-to-end action latency: under 1 second after a stable gesture.

## 14. Key Risks and Mitigations

Risk: VLM miscounts fingers.

- Mitigation: use landmarks and geometry for counting; VLM only as optional fallback.

Risk: Same gesture fires repeatedly.

- Mitigation: stability window, action cooldown, "gesture released" requirement.

Risk: Background hands or partial hands cause false positives.

- Mitigation: confidence thresholds, active hand zone, one-user calibration, optional "arming" gesture.

Risk: LLM opens something unintended.

- Mitigation: action allowlist, structured tool output, path validation, confirmations.

Risk: Lighting/camera angle hurts tracking.

- Mitigation: collect validation clips in your real environment and add personalized calibration.

Risk: Voice activates accidentally.

- Mitigation: push-to-talk first, then wake word or VAD only after the base system is stable.

## 15. Recommended First Build

Build this exact first version:

1. Python app with OpenCV camera loop.
2. MediaPipe Hand Landmarker.
3. Landmark overlay window.
4. Finger counter with temporal smoothing.
5. Typed CLI prompt:
   - user types: "how many fingers?"
   - app answers from latest stable count.
6. LM Studio chat call receives:
   - the user question,
   - latest stable observation,
   - instruction to answer without inventing visual facts.
7. Add only one safe action:
   - gesture: open palm for 700 ms,
   - action: open a harmless test website,
   - cooldown: 5 seconds.

This is the smallest version that proves all important parts: live vision, stable symbol detection, local LLM reasoning, and safe system action.

## 16. What Not To Do First

- Do not train a big model before trying MediaPipe landmarks.
- Do not give the LLM shell access.
- Do not map gestures to sensitive actions until false positives are measured.
- Do not rely on one perfect demo lighting setup.
- Do not start with dynamic gestures; static finger counts will teach the system shape.

## 17. Immediate Next Checklist

1. Install Python dependencies: OpenCV, MediaPipe, NumPy, OpenAI client, PyYAML or Pydantic, and optionally faster-whisper.
2. Start LM Studio local server.
3. Verify `GET /v1/models` or a simple chat completion.
4. Run webcam capture.
5. Run MediaPipe hand landmarks.
6. Implement and tune finger counter.
7. Create validation clips.
8. Add LM Studio answer layer.
9. Add safe action registry.
10. Add custom gesture collection.

## 18. Reference Links Used

These are the retained references used to build and verify this plan. Search-result-only pages that were not used as supporting evidence are intentionally excluded.

### Official documentation and API references

- MediaPipe Hand Landmarker overview: https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker
- MediaPipe Hand Landmarker Python guide: https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker/python
- MediaPipe Gesture Recognizer overview: https://developers.google.com/edge/mediapipe/solutions/vision/gesture_recognizer
- MediaPipe Gesture Recognizer Python guide: https://developers.google.com/edge/mediapipe/solutions/vision/gesture_recognizer/python
- OpenCV Python video tutorial: https://docs.opencv.org/4.x/dd/d43/tutorial_py_video_display.html
- OpenCV `VideoCapture` API reference: https://docs.opencv.org/4.x/d8/dfe/classcv_1_1VideoCapture.html
- LM Studio developer docs: https://lmstudio.ai/docs/developer
- LM Studio OpenAI-compatible endpoints: https://lmstudio.ai/docs/developer/openai-compat
- LM Studio tool use: https://lmstudio.ai/docs/developer/openai-compat/tools
- LM Studio structured output: https://lmstudio.ai/docs/developer/openai-compat/structured-output
- LM Studio REST API overview: https://lmstudio.ai/docs/developer/rest
- LM Studio Python SDK image input: https://lmstudio.ai/docs/python/llm-prediction/image-input
- Python `webbrowser`: https://docs.python.org/3/library/webbrowser.html
- Python `os.startfile`: https://docs.python.org/3/library/os.html#os.startfile
- Python `subprocess`: https://docs.python.org/3/library/subprocess.html
- Microsoft ShellExecute launching guide: https://learn.microsoft.com/en-us/windows/win32/shell/launch
- Microsoft ShellExecuteA reference: https://learn.microsoft.com/en-us/windows/win32/api/shellapi/nf-shellapi-shellexecutea
- PyAutoGUI documentation: https://pyautogui.readthedocs.io/
- faster-whisper repository: https://github.com/SYSTRAN/faster-whisper

### Papers, model reports, and model cards

- MediaPipe Hands paper: https://arxiv.org/abs/2006.10214
- Google Research MediaPipe Hands listing: https://research.google/pubs/mediapipe-hands-on-device-real-time-hand-tracking/
- On-device Real-time Hand Gesture Recognition paper: https://arxiv.org/abs/2111.00038
- Google Research hand gesture recognition listing: https://research.google/pubs/on-device-real-time-hand-gesture-recognition/
- Whisper paper: https://arxiv.org/abs/2212.04356
- Whisper ICML/PMLR page: https://proceedings.mlr.press/v202/radford23a.html
- Qwen2.5-VL technical report: https://arxiv.org/abs/2502.13923
- Qwen2.5-VL 7B Instruct model card: https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct
- Gemma 3 technical report: https://arxiv.org/abs/2503.19786
- Gemma 3 27B IT model card: https://huggingface.co/google/gemma-3-27b-it
- LLaVA-OneVision paper: https://arxiv.org/abs/2408.03326
- InternVL3.5 paper: https://arxiv.org/abs/2508.18265
- Visual Hand Gesture Recognition survey: https://arxiv.org/abs/2507.04465
- SmolVLM overview: https://huggingface.co/blog/smolvlm
- SmolVLM-256M model card: https://huggingface.co/HuggingFaceTB/SmolVLM-256M-Instruct
- Moondream official site: https://moondream.ai/
- Moondream repository: https://github.com/m87-labs/moondream

## 19. Direct Source Quotes

Short direct quotes from official documentation, papers, and model cards. These are included only as provenance anchors; the main plan uses paraphrased design guidance.

- MediaPipe Hand Landmarker overview: "detect the landmarks of the hands in an image"
  Source: https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker
- MediaPipe Hand Landmarker Python guide: "provide the Hand Landmarker task the timestamp"
  Source: https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker/python
- MediaPipe Gesture Recognizer overview: "recognize hand gestures in real time"
  Source: https://developers.google.com/edge/mediapipe/solutions/vision/gesture_recognizer
- MediaPipe Gesture Recognizer Python guide: "ignore the new input frame"
  Source: https://developers.google.com/edge/mediapipe/solutions/vision/gesture_recognizer/python
- OpenCV video tutorial: "capture live stream with a camera"
  Source: https://docs.opencv.org/4.x/dd/d43/tutorial_py_video_display.html
- OpenCV `VideoCapture` API reference: "Closes video file or capturing device"
  Source: https://docs.opencv.org/4.x/d8/dfe/classcv_1_1VideoCapture.html
- LM Studio OpenAI compatibility: "reuse existing OpenAI clients"
  Source: https://lmstudio.ai/docs/developer/openai-compat
- LM Studio tool use: "LLMs cannot directly execute code"
  Source: https://lmstudio.ai/docs/developer/openai-compat/tools
- LM Studio structured output: "valid JSON conforming to the schema"
  Source: https://lmstudio.ai/docs/developer/openai-compat/structured-output
- LM Studio image input: "can accept images as input"
  Source: https://lmstudio.ai/docs/python/llm-prediction/image-input
- Python `webbrowser`: "displaying web-based documents to users"
  Source: https://docs.python.org/3/library/webbrowser.html
- Python `os.startfile`: "Start a file with its associated application"
  Source: https://docs.python.org/3/library/os.html#os.startfile
- Python `subprocess`: "spawn new processes"
  Source: https://docs.python.org/3/library/subprocess.html
- Microsoft ShellExecuteA: "Performs an operation on a specified file"
  Source: https://learn.microsoft.com/en-us/windows/win32/api/shellapi/nf-shellapi-shellexecutea
- PyAutoGUI: "control the mouse and keyboard"
  Source: https://pyautogui.readthedocs.io/
- faster-whisper: "reimplementation of OpenAI's Whisper model"
  Source: https://github.com/SYSTRAN/faster-whisper
- MediaPipe Hands paper: "palm detector, 2) a hand landmark model"
  Source: https://arxiv.org/abs/2006.10214
- On-device HGR paper: "hand skeleton tracker and a gesture classifier"
  Source: https://arxiv.org/abs/2111.00038
- Whisper paper: "680,000 hours of multilingual and multitask supervision"
  Source: https://arxiv.org/abs/2212.04356
- Qwen2.5-VL technical report: "interactive visual agent capable of reasoning"
  Source: https://arxiv.org/abs/2502.13923
- Qwen2.5-VL model card: "Browse Quantizations to use this model in  llama.cpp,  Ollama,  LM Studio"
  Source: https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct
- Gemma 3 technical report: "multimodal addition to the Gemma family"
  Source: https://arxiv.org/abs/2503.19786
- Gemma 3 model card: "handling text and image input and generating text output"
  Source: https://huggingface.co/google/gemma-3-27b-it
- LLaVA-OneVision paper: "single-image, multi-image, and video scenarios"
  Source: https://arxiv.org/abs/2408.03326
- InternVL3.5 paper: "versatility, reasoning capability, and inference efficiency"
  Source: https://arxiv.org/abs/2508.18265
- Visual Hand Gesture Recognition survey: "static, isolated dynamic and continuous gesture recognition"
  Source: https://arxiv.org/abs/2507.04465
