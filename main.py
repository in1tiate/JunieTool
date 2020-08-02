import os
import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
import ffmpeg
from subprocess import check_output
import re
from PIL import ImageTk, Image
import sys


def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def sort_human(l):
    def convert(text): return float(text) if text.isdigit() else text
    def alphanum(key): return [convert(c)
                               for c in re.split('([-+]?[0-9]*\.?[0-9]*)', key)]
    l.sort(key=alphanum)
    return l


def calculate_aspect(width: int, height: int) -> str:
    temp = 0

    def gcd(a, b):
        """The GCD (greatest common divisor) is the highest number that evenly divides both width and height."""
        return a if b == 0 else gcd(b, a % b)

    if width == height:
        return "1:1"

    if width < height:
        temp = width
        width = height
        height = temp

    divisor = gcd(width, height)

    x = int(width / divisor) if not temp else int(height / divisor)
    y = int(height / divisor) if not temp else int(width / divisor)

    return f"{x}:{y}"


root = tk.Tk()
root.title('JunieTool')
root.iconbitmap(resource_path('icon.ico'))

frame_select = tk.Frame(root, bd=1, padx=12,
                        pady=3, relief="raised", width=480)
frame_select.grid(row=0, column=0, sticky="nesw")

selected_seq_info = tk.Message(
    frame_select, text="No images selected", width=480)
selected_seq_info.grid(row=1, sticky="ew")

selected_img_info = tk.Message(frame_select, text="", width=480)
selected_img_info.grid(row=2, sticky="ew")

sel_w, sel_h = (1, 1)
files = []
file_open = False


def browseFirstImage():
    global sel_w
    global sel_h
    global files
    global file_open
    file = filedialog.askopenfile(
        parent=root, mode='rb', title='Choose any image in the sequence', filetypes=[('PNG Images', ['.png'])])
    if not file:
        return None
    dir_ = os.path.dirname(file.name)
    filetype = os.path.splitext(file.name)
    files = [os.path.abspath(os.path.join(dir_, f))
             for f in os.listdir(dir_)
             if f.endswith(filetype)]
    files = sort_human(files)
    selected_seq_info.config(
        text="Selected " + os.path.basename(file.name) + " (" + str(len(files)) + " total images)")
    im = Image.open(files[0])
    sel_w, sel_h = im.size
    selected_img_info.config(
        text=str(sel_w)+"x"+str(sel_h)+", "+calculate_aspect(sel_w, sel_h))
    file_open = True
    if entry_h.get() != "" and entry_w.get() != "":
        button_ffmpeg.config(state="normal")


button_browse = tk.Button(
    frame_select, text='Browse...', command=browseFirstImage, width=15)
button_browse.grid(row=0, sticky="ew")


def calculate_ratio():
    disp_temp = "Ratio: " + \
        str(calculate_aspect(int(entry_w.get()), int(entry_h.get())))
    ratio_display.config(text=disp_temp)


crop_h = tk.IntVar()
crop_h.set(1)
overwrite_og = tk.IntVar()
overwrite_og.set(0)

frame_options = tk.Frame(root, bd=1, relief="raised",
                         padx=12, pady=3)
frame_options.grid(row=2, column=0, sticky="nesw")
check_overwrite_og = tk.Checkbutton(
    frame_options, text='Overwrite source images', variable=overwrite_og, onvalue=True, offvalue=False)
check_overwrite_og.pack(anchor="w")
radio_crop_h = tk.Radiobutton(
    frame_options, text="Crop by height", variable=crop_h, value=1).pack(anchor="w")
radio_crop_w = tk.Radiobutton(
    frame_options, text="Crop by width", variable=crop_h, value=0).pack(anchor="w")


def ffmpeg_export():
    des_w = int(entry_w.get())
    des_h = int(entry_h.get())
    if (des_w > sel_w) or (des_h > sel_h):
        messagebox.showerror(
            title="Error", message="Desired size is larger than source size!")
        return
    sel_ratio = sel_w / sel_h
    des_ratio = des_w / des_h
    x_offset = 0
    y_offset = 0
    adj_w = sel_w
    adj_h = sel_h
    if (crop_h.get() == 1) and (sel_ratio != des_ratio):
        adj_w = des_ratio * sel_h  # get the new width for the desired aspect ratio
        x_offset = (sel_w - adj_w) / 2  # centering math
    elif (crop_h.get() == 0) and (sel_ratio != des_ratio):
        adj_h = des_ratio * sel_w
        y_offset = (sel_h - adj_h) / 2
    for x in files:
        progress_ffmpeg.config(text='Rendering: ' + os.path.split(x)[1])
        frame_ffmpeg.update()
        # ffmpeg complains if we try to output to the same file as our input...
        outdir = x + '~.png'
        if overwrite_og.get() == 0:
            newdir = os.path.dirname(str(x)) + '_' + \
                str(des_w) + 'x' + str(des_h)
            outdir = newdir + os.sep + str(os.path.split(x)[1])
            if not os.path.isdir(newdir):
                os.mkdir(newdir)
        stream = ffmpeg.input(str(x), nostdin=None)
        stream = ffmpeg.crop(stream, x_offset, y_offset, adj_w, adj_h)
        stream = ffmpeg.filter(stream, "scale", des_w,
                               des_h, sws_flags="bilinear")
        stream = ffmpeg.output(
            stream, outdir, hide_banner=None)
        stream = ffmpeg.overwrite_output(stream)
        ffmpeg.run_async(stream)
        # ...so we output to a different file, then replace the original with ours afterwards.
        if overwrite_og.get() == 1:
            os.remove(x)
            os.rename(x + '~.png', x)
    progress_ffmpeg.config(text='Rendering: Done!')


frame_ffmpeg = tk.Frame(root, bd=1, padx=12, pady=3,
                        relief="raised")
frame_ffmpeg.grid(row=3, column=0, sticky="nesw")

button_ffmpeg = tk.Button(
    frame_ffmpeg, text='Render', command=ffmpeg_export, state="disabled", width=15, height=3)
button_ffmpeg.grid(row=0, sticky="ew")
progress_ffmpeg = tk.Message(frame_ffmpeg, text='Rendering: N/A', width=400)
progress_ffmpeg.grid(row=1, sticky="ew")

frame_entry = tk.Frame(root, bd=1, relief="raised",
                       padx=12, pady=3, width=1400)
frame_entry.grid(row=1, column=0, sticky="nesw")

tk.Label(frame_entry, text='Enter desired size:').grid(row=0, column=0)
tk.Label(frame_entry, text='Width').grid(row=1, column=0, sticky="e")
tk.Label(frame_entry, text='Height').grid(row=2, column=0, sticky="e")

sv_w = tk.StringVar()
sv_h = tk.StringVar()


def sv_edited(var, indx, mode):
    if entry_h.get() == "" or entry_w.get() == "":
        button_ffmpeg.config(state="disabled")
        return
    else:
        if file_open:
            button_ffmpeg.config(state="normal")
        calculate_ratio()


sv_w.trace_add("write", sv_edited)
sv_h.trace_add("write", sv_edited)

entry_w = tk.Entry(frame_entry, textvariable=sv_w)
entry_h = tk.Entry(frame_entry, textvariable=sv_h)
entry_w.grid(row=1, column=1, padx=1, pady=1, sticky="w")
entry_h.grid(row=2, column=1, padx=1, pady=1, sticky="w")


ratio_display = tk.Message(frame_entry, text="Ratio: N/A", width=500)
ratio_display.grid(row=0, column=1, sticky="e")
root.mainloop()
