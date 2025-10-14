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

## Requirements

- Python 3.8 or later  
- FFmpeg installed and available in your system PATH  
  - Download FFmpeg: https://ffmpeg.org/download.html  

## Installation

Clone this repository and install dependencies:

```bash
git clone https://github.com/yourusername/batch-silence-trimmer.git
cd batch-silence-trimmer
pip install -r requirements.txt
```

Note: FFmpeg must be installed separately and accessible via the command line (ffmpeg -version should work).

## Usage
Run the script with your input and output folders:

```bash
python batch_silence_trimmer.py /path/to/input /path/to/output
```

You can also specify custom silence thresholds and duration (optional):

```bash
python batch_silence_trimmer.py /input /output --silence-threshold -25 --min-silence 0.4
```

## Example Output

Input: `/Recordings/Session Takes/`
Output: `/Desktop/Trimmed Takes/`

Files:

```python-repl
Take_01_trimmed.wav
Take_02_trimmed.wav
...
```

## Example Use Cases

Podcasts: trim dead air and pauses from dialogue tracks for multiple recordings at a time

Audiobooks: maintain consistent pacing between multiple chapters or takes without individually editing files

Music production: clean up exported stems or live takes before mixing or sharing


## Tips

If FFmpeg errors mention `Option not found`, make sure your FFmpeg build supports `silenceremove`.

Experiment with different `--silence-threshold` values depending on background noise levels.

Keep a backup of your raw recordings because the script overwrites nothing by default!

## Build as Executable

To make Batch Silence Trimmer installable and runnable without Python, you can package it into an executable for Windows or macOS using PyInstaller.

1. Install PyInstaller
 
```bash
pip install pyinstaller
```

2. Build the Executable

From the project directory, run:

```bash
pyinstaller --onefile batch_silence_trimmer.py
```

This creates a standalone executable inside the dist folder:

Windows: `dist\batch_silence_trimmer.exe`

macOS: `dist/batch_silence_trimmer`

3. Run the Executable
You can now double-click or run it directly from a terminal:

```bash
./dist/batch_silence_trimmer /path/to/input /path/to/output
```

---

## For Developers

The project is designed for easy packaging into a CLI tool or standalone installer for Windows and macOS.
A simple GUI wrapper using PyInstaller or Electron + Python backend is also planned.

## License

MIT License — feel free to modify and redistribute.


## Contributing

Pull requests, feature requests, complaints, bug reports, and ideas are welcome.
If you do use this tool in your audio workflow, please share your experience or feature suggestions at connor@connorlafitte.com
