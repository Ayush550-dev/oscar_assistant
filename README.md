# O.S.C.A.R. - Stage 1: Local Voice Loop

This is step 1 of building your assistant: a wake word + speech-to-text loop
that runs 100% on your PC. Nothing here needs the internet.

## What it does right now
- Listens for "Hey Jarvis" (placeholder wake word - we'll train a custom
  "Hey Oscar" one in a later stage)
- Records what you say next
- Converts it to text locally and prints it

That's it for Stage 1. No cloud brain yet, no app-opening yet - those come
in Stage 2 and Stage 3. We're building the foundation first so each piece
is easy to understand and test on its own.

## Setup (Windows)

1. **Install Python** (skip if you already have it)
   - Go to https://python.org/downloads
   - Download the latest version
   - During install, **check the box "Add Python to PATH"** - this matters

2. **Open Command Prompt in this folder**
   - Open the `oscar_assistant` folder in File Explorer
   - Click the address bar, type `cmd`, press Enter

3. **Install the required packages**
   ```
   pip install -r requirements.txt
   ```
   This may take a few minutes the first time (it downloads some AI model
   files too).

4. **Run it**
   ```
   python main.py
   ```

5. **Test it**
   - Wait for "Listening for 'Hey Jarvis'..." to appear
   - Say "Hey Jarvis"
   - Then say a short sentence, like "what time is it"
   - You should see it printed back as text

## If something goes wrong

- **"No module named ..." error** → the pip install step didn't finish
  correctly, run `pip install -r requirements.txt` again
- **No microphone detected / silence only** → check Windows Settings >
  Privacy > Microphone, make sure Command Prompt/Python is allowed to
  access it
- **Wake word never triggers** → try speaking a bit louder/closer to the
  mic, or lower `WAKE_THRESHOLD` in `main.py` (e.g., from 0.5 to 0.4)
- **It's slow to transcribe** → that's expected on your CPU with longer
  sentences; `tiny` model is already the fastest option, this is fine for
  Stage 1 testing

## What's next (once this works for you)

- **Stage 2**: send the transcribed text to a cloud AI (only the text -
  never your files or screen) and speak the reply out loud
- **Stage 3**: teach it to open/close specific apps and files using local
  Windows commands - no AI needed for the action itself
- **Stage 4**: rebuild the dashboard UI, lightweight this time, with your
  spider logo untouched

Let me know once you've got Stage 1 running (or if you hit an error) and
we'll move to Stage 2.
