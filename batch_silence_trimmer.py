import concurrent.futures
import json
import os
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from silence_core import detect_silence_ffmpeg, shrink_silence

# -----------------------
# Shared state
# -----------------------
queue_msgs = queue.Queue()
stop_event = threading.Event()
active_futures = []

root = tk.Tk()
root.title("Narration Silence Trimmer (Shrink Long Pauses)")


# -----------------------
# Check ffmpeg installation
# -----------------------
def check_ffmpeg():
    try:
        result = subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        ok = result.returncode == 0
    except FileNotFoundError:
        ok = False
    if not ok:
        messagebox.showerror(
            "Error",
            "ffmpeg not found.\n\nPlease install ffmpeg and ensure it's available in your system PATH.",
        )
        root.destroy()
        sys.exit(1)


# -----------------------
# Helpers
# -----------------------
def browse_into(entry):
    """Replace the entry's contents with a chosen folder (no-op if cancelled)."""
    d = filedialog.askdirectory()
    if d:
        entry.delete(0, tk.END)
        entry.insert(0, d)


def read_params():
    """Validate the numeric fields. Returns (threshold, min_silence, max_gap, pad, workers) or None."""
    try:
        threshold = threshold_entry.get().strip()
        if threshold and not threshold.lower().endswith("db"):
            threshold += "dB"  # allow typing just "-35"
        min_silence = float(min_silence_entry.get())
        max_gap = float(max_gap_entry.get())
        pad = float(pad_entry.get())
        if not threshold or min_silence <= 0 or max_gap <= 0 or pad < 0:
            raise ValueError
    except ValueError:
        messagebox.showerror(
            "Invalid settings",
            "Threshold must be a dB value; Min Silence and Max Gap must be > 0; Padding must be >= 0.",
        )
        return None
    try:
        workers = max(1, int(workers_entry.get()))
    except ValueError:
        workers = max(1, min(4, os.cpu_count() or 2))
    return threshold, min_silence, max_gap, pad, workers


# -----------------------
# Preview waveform (any format ffmpeg can read, embedded in a Tk window)
# -----------------------
PREVIEW_RATE = 8000


def preview_waveform():
    file_path = filedialog.askopenfilename(
        filetypes=[("Audio files", "*.wav *.flac *.mp3 *.m4a *.ogg"), ("All files", "*.*")]
    )
    if not file_path:
        return
    params = read_params()
    if params is None:
        return
    threshold, min_silence, _, _, _ = params

    status_label.config(text="Analyzing preview...")
    root.update_idletasks()

    # Decode to mono 8 kHz 16-bit so stereo / 24-bit / long files all work and stay small.
    proc = subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-i", file_path,
         "-ac", "1", "-ar", str(PREVIEW_RATE), "-f", "s16le", "-"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    if proc.returncode != 0 or not proc.stdout:
        status_label.config(text="")
        messagebox.showerror("Error", "Could not decode that file.")
        return
    audio = np.frombuffer(proc.stdout, dtype=np.int16)
    duration = len(audio) / PREVIEW_RATE
    silences = detect_silence_ffmpeg(file_path, threshold, min_silence, duration)

    # Min/max envelope: ~4000 points no matter how long the file is.
    block = max(1, len(audio) // 4000)
    n = (len(audio) // block) * block
    blocks = audio[:n].reshape(-1, block)
    t = np.arange(blocks.shape[0]) * block / PREVIEW_RATE

    win = tk.Toplevel(root)
    win.title(f"Waveform Preview: {os.path.basename(file_path)}")
    fig = Figure(figsize=(12, 4))
    ax = fig.add_subplot(111)
    ax.fill_between(t, blocks.min(axis=1), blocks.max(axis=1), linewidth=0)
    for start, end in silences:
        ax.axvspan(start, end, color="red", alpha=0.3)
    ax.set_title("Red = detected silence")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Amplitude")
    canvas = FigureCanvasTkAgg(fig, master=win)
    canvas.draw()
    NavigationToolbar2Tk(canvas, win)
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    status_label.config(text="")


# -----------------------
# Worker wrapper for concurrent execution
# -----------------------
def worker_process(in_path, out_path, threshold, min_silence, max_gap, pad):
    name = os.path.basename(in_path)
    if stop_event.is_set():
        return {"status": "cancelled", "file": name}
    start_ts = time.time()
    try:
        ok, err = shrink_silence(in_path, out_path, threshold, min_silence, max_gap, pad)
        if ok:
            return {"status": "ok", "file": name, "out": out_path, "elapsed": time.time() - start_ts}
        return {"status": "error", "file": name, "error": err}
    except Exception as e:
        return {"status": "error", "file": name, "error": str(e)}


# -----------------------
# Batch process with ThreadPoolExecutor and resumable state
# -----------------------
def run_batch():
    global active_futures

    params = read_params()
    if params is None:
        return
    threshold, min_silence, max_gap, pad, workers = params

    input_dir = input_entry.get().strip()
    output_dir = output_entry.get().strip()
    if not os.path.isdir(input_dir):
        messagebox.showerror("Error", "Input folder is invalid.")
        return
    if not output_dir:
        messagebox.showerror("Error", "Choose an output folder.")
        return
    os.makedirs(output_dir, exist_ok=True)

    def out_path_for(fname):
        return os.path.join(output_dir, os.path.splitext(fname)[0] + "_trimmed.wav")

    # Skip our own outputs if input and output are the same folder.
    wav_files = sorted(
        f for f in os.listdir(input_dir)
        if f.lower().endswith(".wav") and not os.path.splitext(f)[0].endswith("_trimmed")
    )
    if not wav_files:
        messagebox.showinfo("No files", "No WAV files found in input folder.")
        return

    state_file = os.path.join(output_dir, "batch_state.json")
    try:
        with open(state_file, "r") as sf:
            state = json.load(sf)
    except Exception:
        state = {"processed": {}}
    processed = state.setdefault("processed", {})

    # Done = recorded as ok AND the output still exists.
    def is_done(fname):
        return processed.get(fname, {}).get("status") == "ok" and os.path.isfile(out_path_for(fname))

    to_process = [f for f in wav_files if not is_done(f)]
    if not to_process:
        messagebox.showinfo("Nothing to do", "All files appear to have been processed already.")
        return

    progress["maximum"] = len(wav_files)
    progress["value"] = len(wav_files) - len(to_process)
    status_label.config(text=f"Queued {len(to_process)} files.")
    start_btn.config(state="disabled")

    stop_event.clear()
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=workers)
    futures = []
    for fname in to_process:
        fut = executor.submit(
            worker_process, os.path.join(input_dir, fname), out_path_for(fname),
            threshold, min_silence, max_gap, pad,
        )
        fut.file_name = fname
        futures.append(fut)
    active_futures = futures

    def save_state():
        tmp = state_file + ".tmp"
        try:
            with open(tmp, "w") as sf:
                json.dump(state, sf, indent=2)
            os.replace(tmp, state_file)
        except Exception:
            pass

    def monitor_futures():
        for fut in concurrent.futures.as_completed(futures):
            if fut.cancelled():
                res = {"status": "cancelled", "file": fut.file_name}
            else:
                try:
                    res = fut.result()
                except Exception as e:
                    res = {"status": "error", "file": fut.file_name, "error": str(e)}
            # Only successes are recorded, so errors/cancels get retried on resume.
            if res.get("status") == "ok":
                processed[res["file"]] = {"status": "ok", "time": time.time()}
                save_state()
            queue_msgs.put(res)
        executor.shutdown(wait=False)
        queue_msgs.put({"status": "all_done", "cancelled": stop_event.is_set()})

    threading.Thread(target=monitor_futures, daemon=True).start()


# -----------------------
# Poll queue and update GUI
# -----------------------
def poll_queue():
    try:
        while True:
            msg = queue_msgs.get_nowait()
            status = msg.get("status")
            if status == "ok":
                progress["value"] = min(progress["maximum"], progress["value"] + 1)
                status_label.config(text=f"Processed: {msg['file']} ({int(progress['value'])}/{int(progress['maximum'])})")
            elif status == "error":
                progress["value"] = min(progress["maximum"], progress["value"] + 1)
                status_label.config(text=f"Error processing {msg['file']}: {msg.get('error')}")
            elif status == "cancelled":
                status_label.config(text=f"Skipped (cancelled): {msg['file']}")
            elif status == "all_done":
                start_btn.config(state="normal")
                if msg.get("cancelled"):
                    status_label.config(text="Batch cancelled. Run again to resume.")
                else:
                    status_label.config(text="Batch complete.")
                    messagebox.showinfo("Done", "Batch trimming complete!")
            queue_msgs.task_done()
    except queue.Empty:
        pass
    root.after(200, poll_queue)


# -----------------------
# Cancel / Stop
# -----------------------
def cancel_batch():
    stop_event.set()
    for fut in active_futures:
        fut.cancel()  # drops jobs that haven't started; running ones finish
    status_label.config(text="Cancel requested — waiting for running jobs to finish...")


# -----------------------
# Tkinter GUI
# -----------------------
check_ffmpeg()

tk.Label(root, text="Input Folder").grid(row=0, column=0)
input_entry = tk.Entry(root, width=40)
input_entry.grid(row=0, column=1)
tk.Button(root, text="Browse", command=lambda: browse_into(input_entry)).grid(row=0, column=2)

tk.Label(root, text="Output Folder").grid(row=1, column=0)
output_entry = tk.Entry(root, width=40)
output_entry.grid(row=1, column=1)
tk.Button(root, text="Browse", command=lambda: browse_into(output_entry)).grid(row=1, column=2)


def add_field(row, label, default):
    tk.Label(root, text=label).grid(row=row, column=0)
    entry = tk.Entry(root)
    entry.insert(0, default)
    entry.grid(row=row, column=1)
    return entry


threshold_entry = add_field(2, "Threshold (dB)", "-35dB")
min_silence_entry = add_field(3, "Min Silence (s)", "0.7")
max_gap_entry = add_field(4, "Max Gap (s)", "4.0")
pad_entry = add_field(5, "Padding (s)", "0.2")
workers_entry = add_field(6, "Workers", str(min(4, os.cpu_count() or 2)))

tk.Button(root, text="Preview Waveform", command=preview_waveform, bg="orange").grid(row=7, column=0)
start_btn = tk.Button(root, text="Start Batch Trim & Shrink", command=run_batch, bg="green", fg="white")
start_btn.grid(row=7, column=1)
tk.Button(root, text="Cancel", command=cancel_batch, bg="red", fg="white").grid(row=7, column=2)

status_label = tk.Label(root, text="")
status_label.grid(row=8, column=0, columnspan=3)

progress = ttk.Progressbar(root, length=300, mode="determinate")
progress.grid(row=9, column=0, columnspan=3, pady=5)

root.after(200, poll_queue)
root.mainloop()
