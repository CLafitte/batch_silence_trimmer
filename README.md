# Batch Silence Trimmer

Batch tool for narration WAV files: trims leading and trailing silence and shrinks long pauses to a maximum length. Tkinter GUI, ffmpeg under the hood.

## Requirements

- Python 3 with Tkinter (Linux: `sudo apt install python3-tk`)
- ffmpeg on your PATH
- `pip install -r requirements.txt`

## Usage

```
python batch_silence_trimmer.py
```

Choose input and output folders, adjust settings, and click **Start Batch Trim & Shrink**. **Preview Waveform** shows detected silences in red so you can tune the settings first.

## Settings

- **Threshold:** level below which audio counts as silence (default -35dB)
- **Min Silence:** shortest gap treated as silence (0.7 s)
- **Max Gap:** longest internal pause kept (4.0 s)
- **Padding:** silence kept beside speech at the start and end (0.2 s)
- **Workers:** files processed in parallel

## Output

For each `name.wav`, the output folder gets `name_trimmed.wav` and `name_trimmed_labels.csv`. Label times match the trimmed audio.

Progress is saved in `batch_state.json`, so an interrupted batch resumes where it left off.

Only `.wav` files are batch-processed.
