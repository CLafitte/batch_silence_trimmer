# Batch Silence Trimmer

Fast, accurate batch silence removal and pause compression for WAV files — built for audio engineers, podcasters, and audiobook producers.

Batch Silence Trimmer automates silence detection and trimming across large batches of WAV files using FFmpeg. It creates clean, consistently timed audio clips ideal for mastering, dialogue editing, or post-production workflows.

---

## Features

- Batch processing: automatically trims silence across entire folders of WAV files  
- Customizable thresholds: adjust silence sensitivity and duration  
- Smart detection: uses FFmpeg’s `silenceremove` filter for precise silence trimming  
- Safe output: writes processed files to a separate output directory  
- Optional CSV logs (coming soon): export silence interval data for analysis or QC  

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
git clone https://github.com/yourusername/batch-silence-trimmer.git
cd batch-silence-trimmer
pip install -r requirements.txt
```

Note: FFmpeg must be installed separately and accessible via the command line (ffmpeg -version should work).

## Example Use Cases

Podcasts: trim dead air and pauses from dialogue tracks for multiple recordings at a time

Audiobooks: maintain consistent pacing between multiple chapters or takes without individually editing files

Music production: clean up exported stems or live takes before mixing or sharing


## Running the GUI

There are multiple ways to launch the Batch Silence Trimmer GUI:

Option 1: Python launcher (cross-platform)

```bash
python run.py
```

Option 2: Platform-specific scripts

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

4. Click Start Batch Trim & Shrink to process all WAV files in the input folder.

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

## Tips

If FFmpeg errors mention `Option not found`, make sure your FFmpeg build supports `silenceremove`.

Experiment with different `--silence-threshold` values depending on background noise levels.

Keep a backup of your raw recordings because the script overwrites nothing by default!

---

## For Developers

The project is designed for easy packaging into a CLI tool or standalone installer for Windows and macOS.
A simple GUI wrapper using PyInstaller or Electron + Python backend is also planned.

## License

MIT License — feel free to modify and redistribute.


## Contributing

Pull requests, feature requests, complaints, bug reports, and ideas are welcome.
If you do use this tool in your audio workflow, please share your experience or feature suggestions at connor@connorlafitte.com
