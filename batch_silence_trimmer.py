import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess, os, csv
import shlex
import wave
import numpy as np
import matplotlib.pyplot as plt

# -----------------------
# Detect silences with ffmpeg
# -----------------------
def detect_silence_ffmpeg(input_file, threshold="-35dB", min_silence=0.7):
    cmd = [
        "ffmpeg",
        "-i", input_file,
        "-af", f"silencedetect=noise={threshold}:d={min_silence}",
        "-f", "null",
        "-"
    ]
    result = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    stderr = result.stderr.splitlines()
    
    silences = []
    current_start = None
    for line in stderr:
        if "silence_start:" in line:
            current_start = float(line.split("silence_start:")[1])
        if "silence_end:" in line:
            parts = line.split("silence_end:")[1].split("|")
            end_time = float(parts[0])
            if current_start is not None:
                silences.append((current_start, end_time))
                current_start = None
    return silences

# -----------------------
# Preview waveform
# -----------------------
def preview_waveform():
    file_path = filedialog.askopenfilename(filetypes=[("WAV files", "*.wav")])
    if not file_path:
        return

    threshold = threshold_entry.get()
    min_silence = float(min_silence_entry.get())

    with wave.open(file_path, 'rb') as wf:
        frames = wf.readframes(wf.getnframes())
        audio = np.frombuffer(frames, dtype=np.int16)
        rate = wf.getframerate()
        duration = len(audio) / rate
        time = np.linspace(0, duration, num=len(audio))

    silences = detect_silence_ffmpeg(file_path, threshold, min_silence)

    plt.figure(figsize=(12,4))
    plt.plot(time, audio, color='blue')
    for start, end in silences:
        plt.axvspan(start, end, color='red', alpha=0.3)
    plt.title(f"Waveform Preview: {os.path.basename(file_path)}\nRed = detected silence")
    plt.xlabel("Time (s)")
    plt.ylabel("Amplitude")
    plt.show()

# -----------------------
# Trim & shrink long silences
# -----------------------
def shrink_silence(input_file, output_file, threshold="-35dB", min_silence=0.7, max_gap=4.0, pad=0.2):
    """
    Trim leading/trailing silence, shrink long silences, and export labels.
    """
    print(f"Processing: {input_file}")

    temp_file = output_file.replace(".wav", "_temp.wav")

    # Step 1: Trim leading/trailing silence
    cmd_trim = [
        "ffmpeg",
        "-y",  # overwrite
        "-i", input_file,
        "-af", f"silenceremove=start_periods=1:start_threshold={threshold}:stop_threshold={threshold}:stop_duration={min_silence}",
        temp_file
    ]
    print("Running trim command:", " ".join(shlex.quote(c) for c in cmd_trim))
    result = subprocess.run(cmd_trim, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if not os.path.isfile(temp_file) or os.path.getsize(temp_file) == 0:
        print(f"Error: temp file not created: {temp_file}")
        print(result.stderr)
        return

    # Step 2: Detect silences
    silences = detect_silence_ffmpeg(temp_file, threshold, min_silence)
    print("Detected silences:", silences)

    # Step 3: Build segments
    segments = []
    labels = []
    last_end = 0.0
    for start, end in silences:
        if start > last_end:
            segments.append((last_end, start))  # non-silence segment
        duration = end - start
        if duration > max_gap:
            # shrink long silence
            segments.append((start, start + max_gap))
            labels.append((start, end, "LONG SILENCE SHRUNK"))
            last_end = start + max_gap
        else:
            segments.append((start, end))
            labels.append((start, end, "SHORT SILENCE"))
            last_end = end

    # add final segment if any audio remains
    with wave.open(temp_file, "rb") as wf:
        total_duration = wf.getnframes() / wf.getframerate()
    if last_end < total_duration:
        segments.append((last_end, total_duration))

    print("Segments to extract:", segments)

    # Step 4: Extract segments as WAV
    temp_dir = os.path.dirname(temp_file)
    part_files = []
    for i, (s, e) in enumerate(segments):
        part_path = os.path.join(temp_dir, f"part_{i}.wav")
        cmd_extract = [
            "ffmpeg",
            "-y",
            "-i", temp_file,
            "-ss", str(s),
            "-to", str(e),
            "-c:a", "pcm_s16le",  # force uncompressed WAV
            part_path
        ]
        print("Extracting segment:", " ".join(shlex.quote(c) for c in cmd_extract))
        subprocess.run(cmd_extract, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if os.path.isfile(part_path) and os.path.getsize(part_path) > 0:
            part_files.append(part_path)
        else:
            print(f"Warning: segment file empty or not created: {part_path}")

    if not part_files:
        print(f"Error: no segments extracted for {input_file}")
        return

    # Step 5: Concatenate all parts
    list_file = os.path.join(temp_dir, "concat_list.txt")
    with open(list_file, "w") as f:
        for p in part_files:
            abs_path = os.path.abspath(p).replace("'", "'\\''")
            f.write(f"file '{abs_path}'\n")

    cmd_concat = [
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", list_file,
        "-c:a", "pcm_s16le",
        output_file
    ]
    print("Concatenating segments:", " ".join(shlex.quote(c) for c in cmd_concat))
    subprocess.run(cmd_concat, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Step 6: Clean up temp files
    for p in part_files + [temp_file, list_file]:
        if os.path.isfile(p):
            os.remove(p)

    # Step 7: Export CSV labels
    label_file = os.path.splitext(output_file)[0] + "_labels.csv"
    with open(label_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Start", "End", "Type"])
        writer.writerows(labels)

    print(f"Done: {output_file} (+ labels: {label_file})")

# -----------------------
# Batch process
# -----------------------
def run_batch():
    input_dir = input_entry.get()
    output_dir = output_entry.get()
    threshold = threshold_entry.get()
    min_silence = float(min_silence_entry.get())
    max_gap = float(max_gap_entry.get())
    pad = float(pad_entry.get())

    if not os.path.isdir(input_dir) or not os.path.isdir(output_dir):
        messagebox.showerror("Error", "Input and Output must be valid folders")
        return

    for fname in os.listdir(input_dir):
        if fname.lower().endswith(".wav"):
            in_path = os.path.join(input_dir, fname)
            out_path = os.path.join(output_dir, fname.replace(".wav", "_trimmed.wav"))
            shrink_silence(in_path, out_path, threshold, min_silence, max_gap, pad)
            status_label.config(text=f"Processed: {fname}")
            root.update()

    messagebox.showinfo("Done", "Batch trimming complete!")

# -----------------------
# GUI
# -----------------------
root = tk.Tk()
root.title("Narration Silence Trimmer (Shrink Long Pauses)")

tk.Label(root, text="Input Folder").grid(row=0, column=0)
input_entry = tk.Entry(root, width=40)
input_entry.grid(row=0, column=1)
tk.Button(root, text="Browse", command=lambda: input_entry.insert(0, filedialog.askdirectory())).grid(row=0, column=2)

tk.Label(root, text="Output Folder").grid(row=1, column=0)
output_entry = tk.Entry(root, width=40)
output_entry.grid(row=1, column=1)
tk.Button(root, text="Browse", command=lambda: output_entry.insert(0, filedialog.askdirectory())).grid(row=1, column=2)

tk.Label(root, text="Threshold (dB)").grid(row=2, column=0)
threshold_entry = tk.Entry(root)
threshold_entry.insert(0, "-35dB")
threshold_entry.grid(row=2, column=1)

tk.Label(root, text="Min Silence (s)").grid(row=3, column=0)
min_silence_entry = tk.Entry(root)
min_silence_entry.insert(0, "0.7")
min_silence_entry.grid(row=3, column=1)

tk.Label(root, text="Max Gap (s)").grid(row=4, column=0)
max_gap_entry = tk.Entry(root)
max_gap_entry.insert(0, "4.0")
max_gap_entry.grid(row=4, column=1)

tk.Label(root, text="Padding (s)").grid(row=5, column=0)
pad_entry = tk.Entry(root)
pad_entry.insert(0, "0.2")
pad_entry.grid(row=5, column=1)

tk.Button(root, text="Preview Waveform", command=preview_waveform, bg="orange").grid(row=6, column=0)
tk.Button(root, text="Start Batch Trim & Shrink", command=run_batch, bg="green", fg="white").grid(row=6, column=1)

status_label = tk.Label(root, text="")
status_label.grid(row=7, column=0, columnspan=3)

root.mainloop()
