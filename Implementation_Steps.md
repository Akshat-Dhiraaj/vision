# Implementation Steps

Last updated: 2026-07-07

## Rules For Every Step

- Keep the change small.
- Update `AI_Context.md` with status and next step.
- Update `Architecture.md` if the flow or module boundary changes.
- Prefer simple functions over classes unless state management clearly needs a class.
- Avoid duplicate logic.
- Add tests before expanding behavior.
- A step is done only when its exit criteria pass.

## Step 0: Project Skeleton

Goal: Create a minimal Python project structure without implementing behavior.

Build:

- `vision_assistant/`
- `vision_assistant/src/`
- `vision_assistant/config/`
- `vision_assistant/tests/`
- `vision_assistant/app.py`
- dependency file, likely `requirements.txt`

Tests:

- Import smoke test for package modules.
- Basic command that prints version/help without opening camera.

Exit criteria:

- Project imports cleanly.
- Test runner works.
- No camera, model, or OS action is required yet.

## Step 1: Configuration Foundation

Goal: Add simple config loading for settings and action registry.

Build:

- `settings.yaml`
- `actions.yaml`
- small config loader
- URL/path/action validation helpers

Tests:

- Loads valid config.
- Rejects missing action fields.
- Rejects non-allowlisted action names.
- Rejects invalid URLs.

Exit criteria:

- Config behavior is deterministic and tested.
- No action is executed yet.

## Step 2: Camera Smoke Test

Goal: Open webcam and read frames safely.

Build:

- `camera.py`
- CLI command to capture one frame or run a preview.
- Clean release logic.

Tests:

- Unit tests for camera wrapper using a fake capture object.
- Manual test: open camera index `0`, read one frame, release.

Exit criteria:

- Camera errors are handled clearly.
- Camera releases on success and failure.

## Step 3: MediaPipe Hand Landmarks

Goal: Convert camera frames into hand landmark observations.

Build:

- `mediapipe_hands.py`
- model path config
- result adapter that returns a plain dictionary

Tests:

- Unit test result adapter with sample/fake MediaPipe result.
- Manual test: webcam frame returns hand landmarks when a hand is visible.

Exit criteria:

- Raw MediaPipe objects do not leak through the rest of the app.
- Missing hand returns an empty observation, not an exception.

## Step 4: Landmark Normalization

Goal: Make landmarks usable for counting and classification.

Build:

- `landmarks.py`
- wrist-origin normalization
- palm-scale normalization
- helper functions for distances and angles

Tests:

- Known points produce expected distances.
- Scale normalization is stable.
- Empty or malformed landmark lists are rejected clearly.

Exit criteria:

- Geometry helpers are pure, simple, and independently tested.

## Step 5: Finger Counter

Goal: Count 0 to 5 fingers on one hand.

Build:

- `finger_count.py`
- per-finger extended state
- handedness-aware thumb logic

Tests:

- Unit tests using saved landmark fixtures.
- Manual validation clips or snapshots for 0, 1, 2, 3, 4, 5 fingers.

Exit criteria:

- Count result includes confidence or reason for uncertainty.
- Low-confidence or malformed input does not produce a confident guess.

## Step 6: Temporal Smoothing

Goal: Prevent flicker and repeated triggers.

Build:

- `temporal_smoothing.py`
- rolling window
- stable observation output
- action cooldown primitive

Tests:

- Stable sequence emits one stable observation.
- Flickering sequence emits no stable observation.
- Held gesture does not repeatedly trigger without release/cooldown.

Exit criteria:

- Stability duration and cooldown are configurable.

## Step 7: Typed Question Loop

Goal: Answer "how many fingers?" from latest stable observation without LM Studio.

Build:

- simple CLI loop in `app.py`
- in-memory latest stable observation
- deterministic answer function

Tests:

- Question parser recognizes the first supported question.
- If no stable observation exists, answer says so.

Exit criteria:

- Full path from webcam to typed answer works locally.

## Step 8: LM Studio Text Integration

Goal: Use local LM Studio for response wording while preserving structured observation truth.

Build:

- `lmstudio_client.py`
- health check or model list check
- prompt that passes latest stable observation
- fallback deterministic answer if LM Studio is unavailable

Tests:

- Unit test request payload construction.
- Mock LM Studio response parsing.
- Manual test against local server.

Exit criteria:

- LM Studio cannot invent a different finger count than the observation.
- App still works if LM Studio is off.

## Step 9: Safe Action Registry

Goal: Define actions but do not trigger them from gestures yet.

Build:

- `action_registry.py`
- `action_executor.py`
- test action: `open_test_page`

Tests:

- Valid action loads.
- Invalid URL/path is rejected.
- Unknown action is rejected.
- Dry-run mode reports what would happen.

Exit criteria:

- Dry-run is default for tests.
- Execution path is small and allowlisted.

## Step 10: First Gesture Action

Goal: Trigger one harmless action from one stable gesture.

Build:

- map `Open_Palm` or chosen stable symbol to `open_test_page`
- cooldown
- event log entry

Tests:

- Unit test gesture-to-action mapping.
- Unit test cooldown.
- Manual test opens only one tab per intentional gesture.

Exit criteria:

- No repeated tab spam.
- Unknown gestures do nothing.

## Step 11: Custom Static Gesture Collection

Goal: Collect user-specific gesture samples as landmarks.

Build:

- recording command
- sample storage format
- label validation

Tests:

- Saves sample with expected schema.
- Rejects unknown labels unless explicitly created.
- Can replay stored samples into classifier code.

Exit criteria:

- Dataset is reproducible and inspectable.

## Step 12: Custom Static Gesture Classifier

Goal: Classify a small set of custom static gestures.

Build:

- simple classifier first, likely k-nearest neighbors or logistic regression
- train/evaluate command
- confusion matrix output

Tests:

- Unit test training on tiny synthetic fixture.
- Evaluation split by recording session.
- Manual test with at least 5 gestures.

Exit criteria:

- Accuracy target agreed before using gestures for real actions.
- False positives measured.

## Step 13: Audio Input

Goal: Add local speech-to-text after typed flow is stable.

Build:

- push-to-talk first
- faster-whisper transcription wrapper
- speech command parser

Tests:

- Mock audio file transcribes through wrapper.
- Parser handles "how many fingers" and "cancel".
- Manual push-to-talk test.

Exit criteria:

- Voice cannot trigger actions accidentally without configured confirmation.

## Step 14: Confirmation Flow

Goal: Require confirmation for sensitive actions.

Build:

- pending action state
- confirm/cancel commands
- timeout

Tests:

- Sensitive action waits.
- Confirm executes.
- Cancel clears.
- Timeout clears.

Exit criteria:

- Sensitive actions cannot run from one accidental gesture.

## Step 15: Optional VLM Fallback

Goal: Add still-image VLM fallback only after core pipeline is stable.

Build:

- capture still frame
- send to local VLM if available
- compare answer to landmark answer for debugging

Tests:

- VLM disabled path works.
- Image payload construction is tested.
- Manual benchmark on saved images.

Exit criteria:

- VLM is optional and never blocks core finger counting.

