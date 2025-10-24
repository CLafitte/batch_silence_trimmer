import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import os
import csv
import wave
import numpy as np
import matplotlib.pyplot as plt
import concurrent.futures
import threading
import queue
import json
import time
import math

# -----------------------
# Check ffmpeg installation
# -----------------------
def check_ffmpeg():
    try:
        result = subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            raise FileNotFoundError
    except FileNotFoundError:
        messagebox.showerror(
            "Error",
            "ffmpeg not found.\n\nPlease install ffmpeg and ensure it's available in your system PATH."
        )
        root.destroy()

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
            try:
                current_start = float(line.split("silence_start:")[1])
            except ValueError:
                current_start = None
        if "silence_end:" in line:
            parts = line.split("silence_end:")[1].split("|")
            try:
                end_time = float(parts[0])
            except ValueError:
                continue
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
        time_axis = np.linspace(0, duration, num=len(audio))

    silences = detect_silence_ffmpeg(file_path, threshold, min_silence)

    plt.figure(figsize=(12,4))
    plt.plot(time_axis, audio)
    for start, end in silences:
        plt.axvspan(start, end, color='red', alpha=0.3)
    plt.title(f"Waveform Preview: {os.path.basename(file_path)}\nRed = detected silence")
    plt.xlabel("Time (s)")
    plt.ylabel("Amplitude")
    plt.show()

# -----------------------
# Trim & shrink long silences
# (unchanged except for logging via prints)
# -----------------------
def shrink_silence(input_file, output_file, threshold="-35dB", min_silence=0.7, max_gap=4.0, pad=0.2):
    print(f"Processing: {input_file}")

    temp_file = output_file.replace(".wav", "_temp.wav")

    # Step 1: Trim leading/trailing silence
    cmd_trim = [
        "ffmpeg",
        "-y",
        "-i", input_file,
        "-af", f"silenceremove=start_periods=1:start_threshold={threshold}:stop_threshold={threshold}:stop_duration={min_silence}",
        temp_file
    ]
    result = subprocess.run(cmd_trim, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if not os.path.isfile(temp_file) or os.path.getsize(temp_file) == 0:
        print(f"Error: temp file not created: {temp_file}")
        print(result.stderr)
        return False, f"Temp file missing: {temp_file}"

    # Step 2: Detect silences
    silences = detect_silence_ffmpeg(temp_file, threshold, min_silence)

    # Step 3: Build segments
    segments = []
    labels = []
    last_end = 0.0
    for start, end in silences:
        if start > last_end:
            segments.append((last_end, start))
        duration = end - start
        if duration > max_gap:
            segments.append((start, start + max_gap))
            labels.append((start, end, "LONG SILENCE SHRUNK"))
            last_end = start + max_gap
        else:
            segments.append((start, end))
            labels.append((start, end, "SHORT SILENCE"))
            last_end = end

    with wave.open(temp_file, "rb") as wf:
        total_duration = wf.getnframes() / wf.getframerate()
    if last_end < total_duration:
        segments.append((last_end, total_duration))

    # Step 4: Extract segments
    temp_dir = os.path.dirname(temp_file)
    part_files = []
    for i, (s, e) in enumerate(segments):
        # apply small padding if desired, but ensure bounds [0, total_duration]
        s_p = max(0.0, s - pad)
        e_p = min(total_duration, e + pad)
        part_path = os.path.join(temp_dir, f"part_{i}.wav")
        cmd_extract = [
            "ffmpeg",
            "-y",
            "-i", temp_file,
            "-ss", str(s_p),
            "-to", str(e_p),
            "-c:a", "pcm_s16le",
            part_path
        ]
        subprocess.run(cmd_extract, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if os.path.isfile(part_path) and os.path.getsize(part_path) > 0:
            part_files.append(part_path)

    if not part_files:
        print(f"Error: no segments extracted for {input_file}")
        return False, "No segments extracted"

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
    subprocess.run(cmd_concat, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Step 6: Clean up
    for p in part_files + [temp_file, list_file]:
        if os.path.isfile(p):
            try:
                os.remove(p)
            except Exception:
                pass

    # Step 7: Export CSV labels in MM:SS.mmm format
    label_file = os.path.splitext(output_file)[0] + "_labels.csv"
    with open(label_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Start", "End", "Type"])
        for start, end, typ in labels:
            start_mmss = f"{int(start//60):02d}:{start%60:06.3f}"
            end_mmss = f"{int(end//60):02d}:{end%60:06.3f}"
            writer.writerow([start_mmss, end_mmss, typ])

    print(f"Done: {output_file} (+ labels: {label_file})")
    return True, None

# -----------------------
# Worker wrapper for concurrent execution
# -----------------------
def worker_process(in_path, out_path, threshold, min_silence, max_gap, pad):
    start_ts = time.time()
    try:
        ok, err = shrink_silence(in_path, out_path, threshold, min_silence, max_gap, pad)
        elapsed = time.time() - start_ts
        if ok:
            return {"status": "ok", "file": os.path.basename(in_path), "out": out_path, "elapsed": elapsed}
        else:
            return {"status": "error", "file": os.path.basename(in_path), "error": err}
    except Exception as e:
        return {"status": "error", "file": os.path.basename(in_path), "error": str(e)}

# -----------------------
# Batch process with ThreadPoolExecutor and resumable state
# -----------------------
def run_batch():
    input_dir = input_entry.get()
    output_dir = output_entry.get()
    threshold = threshold_entry.get()
    min_silence = float(min_silence_entry.get())
    max_gap = float(max_gap_entry.get())
    pad = float(pad_entry.get())
    try:
        workers = int(workers_entry.get())
        if workers < 1:
            workers = 1
    except Exception:
        workers = max(1, min(4, os.cpu_count() or 2))

    if not os.path.isdir(input_dir):
        messagebox.showerror("Error", "Input folder is invalid.")
        return

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # load or init state file
    state_file = os.path.join(output_dir, "batch_state.json")
    if os.path.isfile(state_file):
        try:
            with open(state_file, "r") as sf:
                state = json.load(sf)
        except Exception:
            state = {"processed": {}}
    else:
        state = {"processed": {}}

    wav_files = [f for f in os.listdir(input_dir) if f.lower().endswith(".wav")]
    if not wav_files:
        messagebox.showinfo("No files", "No WAV files found in input folder.")
        return

    # Filter out already processed files (resumable)
    to_process = [f for f in wav_files if f not in state.get("processed", {})]
    total = len(wav_files)
    if not to_process:
        messagebox.showinfo("Nothing to do", "All files appear to have been processed already.")
        return

    # prepare UI + queue
    progress["maximum"] = total
    queue_msgs.queue.clear() if hasattr(queue_msgs, 'queue') else None  # ensure empty if first run
    progress["value"] = sum(1 for name in wav_files if name in state.get("processed", {}))
    status_label.config(text=f"Queued {len(to_process)} files (resuming).")
    root.update_idletasks()

    # prepare executor
    stop_event.clear()
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=workers)
    futures = []

    # submit tasks
    for fname in to_process:
        if stop_event.is_set():
            break
        in_path = os.path.join(input_dir, fname)
        out_name = fname.replace(".wav", "_trimmed.wav")
        out_path = os.path.join(output_dir, out_name)
        future = executor.submit(worker_process, in_path, out_path, threshold, min_silence, max_gap, pad)
        future.file_name = fname
        futures.append(future)

    # monitor in background: as futures complete, push messages to the queue
    def monitor_futures():
        completed = 0
        for fut in concurrent.futures.as_completed(futures):
            if stop_event.is_set():
                # we still collect results but won't submit new jobs
                pass
            try:
                res = fut.result()
            except Exception as e:
                res = {"status": "error", "file": getattr(fut, "file_name", "unknown"), "error": str(e)}
            # write state for resume
            fname = res.get("file")
            if fname:
                state.setdefault("processed", {})[fname] = {"status": res.get("status"), "time": time.time()}
                try:
                    with open(state_file, "w") as sf:
                        json.dump(state, sf, indent=2)
                except Exception:
                    pass
            # push UI message
            queue_msgs.put(res)
            completed += 1
        # all done
        queue_msgs.put({"status": "all_done"})

    monitor_thread = threading.Thread(target=monitor_futures, daemon=True)
    monitor_thread.start()

    # ensure the executor will be cleaned up when monitor finishes
    def shutdown_monitor():
        executor.shutdown(wait=False)

    # schedule executor shutdown later to ensure tasks finish cleanly
    threading.Thread(target=lambda: (monitor_thread.join(), shutdown_monitor()), daemon=True).start()

# -----------------------
# Poll queue and update GUI
# -----------------------
def poll_queue():
    try:
        while True:
            msg = queue_msgs.get_nowait()
            if msg.get("status") == "ok":
                # increment progress (we count by filename unique)
                progress["value"] = min(progress["maximum"], progress["value"] + 1)
                status_label.config(text=f"Processed: {msg.get('file')} ({progress['value']}/{progress['maximum']})")
            elif msg.get("status") == "error":
                progress["value"] = min(progress["maximum"], progress["value"] + 1)
                status_label.config(text=f"Error processing {msg.get('file')}: {msg.get('error')}")
            elif msg.get("status") == "all_done":
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
    status_label.config(text="Cancel requested — waiting for running jobs to finish...")
    # processed items will be updated when running jobs finish

# -----------------------
# TKinter GUI. This is the simple controller where as user can input a threshold and set input/output (in institutional grey!)
# -----------------------
root = tk.Tk()
root.title("Narration Silence Trimmer (Shrink Long Pauses)")

check_ffmpeg()  # ensure ffmpeg installed

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

tk.Label(root, text="Workers").grid(row=6, column=0)
workers_entry = tk.Entry(root)
default_workers = min(4, os.cpu_count() or 2)
workers_entry.insert(0, str(default_workers))
workers_entry.grid(row=6, column=1)

tk.Button(root, text="Preview Waveform", command=preview_waveform, bg="orange").grid(row=7, column=0)
tk.Button(root, text="Start Batch Trim & Shrink", command=run_batch, bg="green", fg="white").grid(row=7, column=1)
tk.Button(root, text="Cancel", command=cancel_batch, bg="red", fg="white").grid(row=7, column=2)

status_label = tk.Label(root, text="")
status_label.grid(row=8, column=0, columnspan=3)

progress = ttk.Progressbar(root, length=300, mode="determinate")
progress.grid(row=9, column=0, columnspan=3, pady=5)

# concurrency primitives
queue_msgs = queue.Queue()
stop_event = threading.Event()

# start polling loop for queue messages
root.after(200, poll_queue)

root.mainloop()
