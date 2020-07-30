import os
import tkinter as tk
from tkinter import filedialog
import ffmpeg
from subprocess import check_output
import re
from PIL import ImageTk, Image


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


crop_h = True
overwrite_og = False

root = tk.Tk()
root.title('JunieTool')

frame_main = tk.Frame(root, padx=12, pady=3)
frame_main.grid(column=0, row=0)

root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=1)

frame_select = tk.Frame(frame_main, bd=1, padx=12,
                        pady=3, bg="green2", width=480)
frame_select.grid(column=0, row=0)

selected_seq_info = tk.Message(
    frame_select, text="No images selected", width=480)
selected_seq_info.grid(row=1, column=0)

selected_img_info = tk.Message(frame_select, text="", width=480)
selected_img_info.grid(row=2, column=0)

imgw, imgh = (1, 1)
files = []


def browseFirstImage():
    global imgw
    global imgh
    global files
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
    imgw, imgh = im.size
    selected_img_info.config(
        text=str(imgw)+"x"+str(imgh)+", "+calculate_aspect(imgw, imgh))


button_browse = tk.Button(
    frame_select, text='Browse...', command=browseFirstImage)
button_browse.grid(row=0, column=0, padx=12, pady=3)

frame_entry = tk.Frame(frame_main, bd=1, relief="sunken",
                       padx=12, pady=3, bg="red", width=1400)
frame_entry.grid(column=1, row=0)

tk.Label(frame_entry, text='Enter desired size:').grid(row=0)
tk.Label(frame_entry, text='Width').grid(row=1)
tk.Label(frame_entry, text='Height').grid(row=2)

sv_w = tk.StringVar()
sv_h = tk.StringVar()


def sv_edited(var, indx, mode):
    if entry_h.get() == "" or entry_w.get() == "":
        return
    else:
        calculate_ratio()


sv_w.trace_add("write", sv_edited)
sv_h.trace_add("write", sv_edited)

entry_w = tk.Entry(frame_entry, textvariable=sv_w)
entry_h = tk.Entry(frame_entry, textvariable=sv_h)
entry_w.grid(row=1, column=1)
entry_h.grid(row=2, column=1)


ratio_display = tk.Message(frame_entry, text="Ratio: N/A", width=500)
ratio_display.grid(row=3, column=1)


def calculate_ratio():
    disp_temp = "Ratio: " + \
        str(calculate_aspect(int(entry_w.get()), int(entry_h.get())))
    ratio_display.config(text=disp_temp)


def ffmpeg_export():
    des_w = int(entry_w.get())
    des_h = int(entry_h.get())
    if (des_w > imgw) or (des_h > imgh):
        tk.messagebox.showerror(
            title=None, message="Desired size is larger than source size!")
        return
    old_ratio = imgw / imgh
    new_ratio = des_w / des_h
    x_offset = 0
    y_offset = 0
    new_w = imgw
    new_h = imgh
    if crop_h and old_ratio != new_ratio:
        new_w = new_ratio * imgh  # get the new width for the desired aspect ratio
        x_offset = (imgw - new_w) / 2  # centering math
    elif not (crop_h) and (old_ratio != new_ratio):
        new_h = new_ratio * imgw
        y_offset = (imgh - new_h) / 2
    for x in files:
        newdir = os.path.dirname(str(x)) + '_' + \
            str(des_w) + 'x' + str(des_h)
        if not overwrite_og:
            outdir = os.path.dirname(
                str(x)) + '_' + str(des_w) + 'x' + str(des_h) + os.sep + str(os.path.split(x)[1])
        if not os.path.isdir(newdir):
            os.mkdir(newdir)
        elif overwrite_og:
            outdir = str(x)
        stream = ffmpeg.input(str(x))
        stream = ffmpeg.crop(stream, x_offset, y_offset, new_w, new_h)
        stream = ffmpeg.filter(stream, "scale", des_w, des_h)
        stream = ffmpeg.output(stream, outdir)
        stream = ffmpeg.overwrite_output(stream)
        ffmpeg.run(stream)


frame_ffmpeg = tk.Frame(frame_main, bd=1, padx=12, pady=3, bg="blue")
frame_ffmpeg.grid(column=1, row=1)

button_ffmpeg = tk.Button(
    frame_ffmpeg, text='TEST FFMPEG OUTPUT', command=ffmpeg_export)
button_ffmpeg.grid(row=0, column=0, padx=12)

root.mainloop()
