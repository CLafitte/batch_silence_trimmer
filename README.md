# Batch Silence Trimmer

A cross-platform tool that removes silences from a batch of WAV files. Detects silences in waveforms, trims to a user-defined threshold, and (coming soon) exports trim labels with timestamps to .CSV. Built for audio engineers, podcasters, and audiobook producers.

## Requirements

---

## Features

- Batch processing: automatically trims silence across entire folders of WAV files  
- Customizable thresholds: adjust silence sensitivity and duration  
- Smart detection: uses FFmpeg’s `silenceremove` filter for precise silence trimming  
- Safe output: writes processed files to a separate output directory  
- Optional CSV logs (coming soon): export silence interval data for analysis or QC

## Example Use Cases

Podcasts: trim dead air and pauses from dialogue tracks for multiple recordings at a time

Audiobooks: maintain consistent pacing between multiple chapters or takes without individually editing files

Music production: clean up exported stems or live takes before mixing or sharing

## Dependencies

- Python 3.8+ (tested with 3.10)
- numpy – for audio array processing
- matplotlib – for waveform previews
- tkinter – standard with Python, used for GUI
- ttk – included with tkinter, for progress bar
- ffmpeg – must be installed separately and available in system PATH
  
## Installation

Clone this repository and install dependencies:

```bash
git clone https://github.com/CLafitte/batch_silence_trimmer.git
cd batch_silence_trimmer
pip install -r requirements.txt
```

Note: FFmpeg must be installed separately and accessible via the command line (ffmpeg -version should work).

## Running the GUI

There are multiple ways to launch the Batch Silence Trimmer GUI:

**Option 1:** Python launcher (cross-platform)

```bash
python run.py
```

**Option 2:** Platform-specific scripts

Windows: double-click `run.bat` or run it from the command prompt.

macOS/Linux: run `./run.sh` in a terminal.

The GUI will open, allowing you to select input/output folders and configure silence detection and trimming parameters.

## Usage

1. Select an Input Folder containing WAV files.
2. Select an Output Folder for trimmed files.
3. Adjust parameters:
   
    Threshold (dB): silence detection threshold

    Min Silence (s): minimum duration to be considered silence

    Max Gap (s): maximum allowed pause in final audio

    Padding (s): optional silence padding

  A waveform preview should generate for the first file selected in the batch

4. Click Start to process all WAV files in the input folder.

  Processed files will appear in the selected output folder.

## Example Output

Input: `/Recordings/Session Takes/`
Output: `/Desktop/Trimmed Takes/`

Files:

```python-repl
Take_01_trimmed.wav
Take_02_trimmed.wav
...
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
