# Architecture

Last updated: 2026-07-07

## Guiding Shape

The assistant is a hybrid local system:

- Vision recognizer: fast, deterministic perception from webcam frames.
- Local LLM: natural language, structured decisions, and explanations.
- Action executor: small, allowlisted system actions.

The LLM should receive structured observations, not raw video frames, for normal finger-count and command work.

## High-Level Flow

```text
User
  -> webcam hand input
  -> optional typed or spoken question

Camera
  -> OpenCV frame capture
  -> MediaPipe hand landmarks / gestures
  -> finger count or gesture classifier
  -> temporal smoothing
  -> stable observation

Assistant loop
  -> user question + latest stable observation
  -> LM Studio local model
  -> answer or structured action request

Safety layer
  -> validate action registry
  -> apply confidence, stability, cooldown, and confirmation rules
  -> execute allowed action
  -> log result
```

## Low-Level Flow

```text
camera.py
  opens webcam
  reads frames
  releases camera cleanly

mediapipe_hands.py
  converts frame format
  runs hand landmarker or recognizer
  returns raw landmarks, handedness, and confidence

landmarks.py
  normalizes landmarks
  computes angles, distances, palm scale, and orientation

finger_count.py
  detects extended fingers
  returns count and per-finger state

temporal_smoothing.py
  accepts raw frame observations
  emits stable observations only

lmstudio_client.py
  sends user text and stable observation to LM Studio
  requests structured output where needed

action_registry.py
  loads allowlisted actions from config
  validates names, URLs, paths, and command targets

config_loader.py
  loads settings.yaml and actions.yaml
  validates allowlisted action names, action fields, URLs, and local paths
  returns plain immutable config data for later modules

action_executor.py
  opens websites, folders, or apps through safe APIs
  never executes arbitrary LLM-provided shell commands

event_log.py
  records observations, decisions, actions, failures, and confirmations
```

## Data Contracts

### Frame Observation

```json
{
  "timestamp_ms": 0,
  "hands": [
    {
      "handedness": "Right",
      "landmarks": "21 normalized points",
      "world_landmarks": "optional 21 world points",
      "finger_count": 3,
      "gesture": "three",
      "confidence": 0.91
    }
  ]
}
```

### Stable Observation

```json
{
  "timestamp_ms": 0,
  "kind": "finger_count",
  "value": 3,
  "duration_ms": 420,
  "confidence": 0.9
}
```

### Action Request

```json
{
  "action": "open_test_page",
  "reason": "Stable open palm gesture detected",
  "requires_confirmation": false
}
```

## Safety Boundaries

- No arbitrary command execution from the LLM.
- Only configured actions can run.
- URLs must be validated before opening.
- Local paths must be absolute, expected, and allowlisted.
- Held gestures must not trigger repeated actions.
- Add a cooldown to every action.
- Destructive or sensitive actions require confirmation.

## First Runnable Architecture

The first build should include only:

1. Webcam capture.
2. MediaPipe hand landmarks.
3. Finger count from landmarks.
4. Temporal smoothing.
5. Typed question loop.
6. LM Studio answer from latest stable observation.
7. One safe action: open a harmless test website.
