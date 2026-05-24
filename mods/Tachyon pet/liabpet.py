import tkinter as tk
import random
import math
import time
import winsound
import webbrowser
import os

# ---------------- PATH FIX (LOAD ALL FILES FROM SCRIPT FOLDER) ---------------- #

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------- SAFE SOUND PLAYER ---------------- #

last_sound_time = 0

def play_bounce():
    global last_sound_time
    now = time.time()

    # Prevent sound spam (50ms cooldown)
    if now - last_sound_time < 0.05:
        return

    last_sound_time = now

    # Stop any currently playing sound
    winsound.PlaySound(None, winsound.SND_PURGE)

    # Play new bounce sound
    winsound.PlaySound(os.path.join(SCRIPT_DIR, "boing.wav"),
                       winsound.SND_ASYNC)

# ---------------- SETTINGS ---------------- #

NUM_WINDOWS = 1
WINDOW_SCALE = 0.3

GRAVITY = 200
BOUNCE = 0.85
FRICTION = 0.995
MAX_SPEED = 1200
START_SPEED = 600
UPDATE_DELAY = 16

CHROMA_COLOR = "#00ff00"

# ---------------- HUNGER SYSTEM ---------------- #

HUNGER_MAX = 100
hunger = HUNGER_MAX
game_over = False
feed_count = 0

drag_start_time = {}
FEED_HOLD_TIME = 5  # seconds

# ---------------- TK SETUP ---------------- #

root = tk.Tk()
root.withdraw()

# ASCII Hunger Bar Window
hunger_bar = tk.Toplevel()
hunger_bar.overrideredirect(True)
hunger_bar.attributes("-topmost", True)
hunger_bar.configure(bg="black")

hunger_label = tk.Label(hunger_bar, text="", font=("Consolas", 14),
                        fg="lime", bg="black")
hunger_label.pack()

def update_hunger_bar():
    bar_len = 20
    filled = int((hunger / HUNGER_MAX) * bar_len)
    bar = "[" + "#" * filled + "-" * (bar_len - filled) + "]"
    hunger_label.config(text=f"HUNGER {bar}")
    hunger_bar.geometry("+10+10")

# ---------------- TOP-RIGHT TEAMS BOX ---------------- #

def open_teams():
    webbrowser.open("https://teams.cloud.microsoft/l/team/19%3AMYJwYBsPpFz5D9lsuLrLElSvXK6bsrooJInph-IH5bQ1%40thread.tacv2/conversations?groupId=b578df46-b5f0-4216-b5e7-4514c0c562db&tenantId=2a3722c9-194c-47d1-91c2-e338e9ec737f")

top_box = tk.Toplevel()
top_box.overrideredirect(True)
top_box.attributes("-topmost", True)
top_box.configure(bg="black")

top_label = tk.Label(
    top_box,
    text="Press P to open Teams",
    font=("Consolas", 14),
    fg="lime",
    bg="black"
)
top_label.pack()

def update_top_box():
    sw = root.winfo_screenwidth()
    box_w = 220
    box_h = 30
    x = sw - box_w - 10
    y = 10
    top_box.geometry(f"{box_w}x{box_h}+{x}+{y}")

# ---------------- LOAD IMAGES (FROM SCRIPT FOLDER) ---------------- #

alex_img_1 = tk.PhotoImage(file=os.path.join(SCRIPT_DIR, "helloalex.png"))
alex_img_2 = tk.PhotoImage(file=os.path.join(SCRIPT_DIR, "helloalexalt.png"))
alex_img_3 = tk.PhotoImage(file=os.path.join(SCRIPT_DIR, "helloalex1year.png"))
tag_original = tk.PhotoImage(file=os.path.join(SCRIPT_DIR, "nametag.png"))

def scale(img, s):
    w = max(1, int(img.width() * s))
    h = max(1, int(img.height() * s))
    return img.subsample(
        max(1, int(img.width() / w)),
        max(1, int(img.height() / h))
    )

alex = scale(alex_img_1, WINDOW_SCALE)
tag = scale(tag_original, WINDOW_SCALE)

alex_w, alex_h = alex.width(), alex.height()
tag_w, tag_h = tag.width(), tag.height()

screen_w = root.winfo_screenwidth()
screen_h = root.winfo_screenheight()

center_x = screen_w // 2 - alex_w // 2
center_y = screen_h // 2 - alex_h // 2

windows = []
nametag_windows = []
vel = []
speech_labels = []
speech_texts = []

dragging = {}
drag_offset = {}
drag_last = {}
throw_vel = {}

# ---------------- IMAGE SWITCHING ---------------- #

def switch_alex(img):
    global alex, alex_w, alex_h

    alex = scale(img, WINDOW_SCALE)
    alex_w, alex_h = alex.width(), alex.height()

    for i, win in enumerate(windows):
        for w in win.winfo_children():
            w.destroy()

        tk.Label(win, image=alex, bg="white").pack()
        lbl = tk.Label(win, text=speech_texts[i], bg="white", fg="black")
        lbl.pack()
        speech_labels[i] = lbl

        x = win.winfo_x()
        y = win.winfo_y()
        tag_win = nametag_windows[i]
        tag_x = int(x + (alex_w // 2) - (tag_w // 2))
        tag_y = int(y - tag_h - 5)
        tag_win.geometry(f"+{tag_x}+{tag_y}")

root.bind_all("1", lambda e: switch_alex(alex_img_1))
root.bind_all("2", lambda e: switch_alex(alex_img_2))
root.bind_all("3", lambda e: switch_alex(alex_img_3))

# ---------------- AUTO-SPAWN LOGIC ---------------- #

def check_spawn():
    if feed_count > 0 and feed_count % 100 == 0:
        add_window()
        if windows:
            spawn_bubble(windows[-1], "A new Alex has appeared!!")

# ---------------- DRAGGING + FEEDING ---------------- #

def start_drag(event, win):
    global hunger, feed_count

    hunger = min(HUNGER_MAX, hunger + 1)
    feed_count += 1
    update_hunger_bar()
    spawn_bubble(win, f"You've fed me {feed_count} times!!")
    check_spawn()

    dragging[win] = True
    drag_offset[win] = (event.x_root - win.winfo_x(),
                        event.y_root - win.winfo_y())
    drag_last[win] = (event.x_root, event.y_root, time.time())
    throw_vel[win] = (0, 0)

    drag_start_time[win] = time.time()

def do_drag(event, win):
    if dragging.get(win, False):
        ox, oy = drag_offset[win]
        nx = event.x_root - ox
        ny = event.y_root - oy
        win.geometry(f"+{nx}+{ny}")

        idx = windows.index(win)
        tag_win = nametag_windows[idx]
        tag_x = int(nx + (alex_w // 2) - (tag_w // 2))
        tag_y = int(ny - tag_h - 5)
        tag_win.geometry(f"+{tag_x}+{tag_y}")

        ox2, oy2, ot = drag_last[win]
        nt = time.time()
        dt = nt - ot
        if dt > 0:
            throw_vel[win] = ((event.x_root - ox2) / dt,
                              (event.y_root - oy2) / dt)
        drag_last[win] = (event.x_root, event.y_root, nt)

        if time.time() - drag_start_time[win] >= FEED_HOLD_TIME:
            feed_full(win)

def stop_drag(event, win):
    dragging[win] = False

# ---------------- FEEDING FUNCTIONS ---------------- #

def feed_full(win):
    global hunger, feed_count
    hunger = HUNGER_MAX
    feed_count += 1
    update_hunger_bar()
    spawn_bubble(win, f"You've fed me {feed_count} times!!")
    check_spawn()

    drag_start_time[win] = time.time() + 9999

def feed_key(event=None):
    global hunger, feed_count
    hunger = min(HUNGER_MAX, hunger + 20)
    feed_count += 1
    update_hunger_bar()

    if windows:
        spawn_bubble(windows[0], f"You've fed me {feed_count} times!!")

    check_spawn()

root.bind_all("e", feed_key)

# ---------------- THOUGHTS ---------------- #

THOUGHTS = [
    "BANANA", "why am i bouncing??", "help!!", "SO TICHE!", "LINKIN PARK BUS!",
    "i live!!", "ow!", "bro..", "what happened???", "KAIDEN SAYS NO!!", "bonk"
]

def random_thought():
    return random.choice(THOUGHTS)

# ---------------- FLOATING BUBBLES ---------------- #

def spawn_bubble(win, text):
    b = tk.Toplevel()
    b.overrideredirect(True)
    b.attributes("-topmost", True)
    b.attributes("-alpha", 1.0)

    lbl = tk.Label(b, text=text, bg="white", fg="black",
                   font=("impact", 15), bd=1, relief="solid")
    lbl.pack()

    x = win.winfo_x() + random.randint(-20, 40)
    y = win.winfo_y() - 20
    b.geometry(f"+{x}+{y}")

    dx = random.uniform(-0.4, 0.4)
    dy = -0.8
    fade = 1.0

    def animate():
        nonlocal x, y, fade
        fade -= 0.02
        if fade <= 0:
            b.destroy()
            return
        x += dx
        y += dy
        b.attributes("-alpha", fade)
        b.geometry(f"+{int(x)}+{int(y)}")
        b.after(40, animate)

    animate()

# ---------------- RESIZE ---------------- #

def resize_all(delta):
    global WINDOW_SCALE, alex, tag, alex_w, alex_h, tag_w, tag_h

    WINDOW_SCALE = max(0.1, min(1.5, WINDOW_SCALE + delta))

    alex = scale(alex, WINDOW_SCALE)
    tag = scale(tag_original, WINDOW_SCALE)

    alex_w, alex_h = alex.width(), alex.height()
    tag_w, tag_h = tag.width(), tag.height()

    for i, win in enumerate(windows):
        for w in win.winfo_children():
            w.destroy()

        tk.Label(win, image=alex, bg="white").pack()
        lbl = tk.Label(win, text=speech_texts[i], bg="white", fg="black")
        lbl.pack()
        speech_labels[i] = lbl

        tag_win = nametag_windows[i]
        for w in tag_win.winfo_children():
            w.destroy()
        tk.Label(tag_win, image=tag, bg=CHROMA_COLOR).pack()

        x = win.winfo_x()
        y = win.winfo_y()
        tag_x = int(x + (alex_w // 2) - (tag_w // 2))
        tag_y = int(y - tag_h - 5)
        tag_win.geometry(f"{tag_w}x{tag_h}+{tag_x}+{tag_y}")

root.bind_all("<KeyPress-Up>", lambda e: resize_all(+0.05))
root.bind_all("<KeyPress-Down>", lambda e: resize_all(-0.05))

# ---------------- ADD WINDOW ---------------- #

def add_window():
    win = tk.Toplevel()
    win.overrideredirect(True)
    win.attributes("-topmost", True)
    win.configure(bg="white")

    tk.Label(win, image=alex, bg="white").pack()

    text = random_thought()
    lbl = tk.Label(win, text=text, bg="white", fg="black")
    lbl.pack()

    win.geometry(f"{alex_w}x{alex_h}+{center_x}+{center_y}")

    tag_win = tk.Toplevel()
    tag_win.overrideredirect(True)
    tag_win.attributes("-topmost", True)
    tag_win.configure(bg=CHROMA_COLOR)
    tag_win.wm_attributes("-transparentcolor", CHROMA_COLOR)

    tk.Label(tag_win, image=tag, bg=CHROMA_COLOR).pack()

    tag_x = int(center_x + (alex_w // 2) - (tag_w // 2))
    tag_y = int(center_y - tag_h - 5)
    tag_win.geometry(f"{tag_w}x{tag_h}+{tag_x}+{tag_y}")

    win.bind("<Button-1>", lambda e, w=win: start_drag(e, w))
    win.bind("<B1-Motion>", lambda e, w=win: do_drag(e, w))
    win.bind("<ButtonRelease-1>", lambda e, w=win: stop_drag(e, w))

    angle = random.uniform(0, 2 * math.pi)
    speed = random.uniform(START_SPEED * 0.5, START_SPEED)
    vx = math.cos(angle) * speed
    vy = math.sin(angle) * speed

    windows.append(win)
    nametag_windows.append(tag_win)
    vel.append([vx, vy])
    speech_labels.append(lbl)
    speech_texts.append(text)

def remove_window():
    if windows:
        win = windows.pop()
        tag_win = nametag_windows.pop()
        vel.pop()
        speech_labels.pop()
        speech_texts.pop()
        win.destroy()
        tag_win.destroy()

root.bind_all("<KeyPress-Right>", lambda e: add_window())
root.bind_all("<KeyPress-Left>", lambda e: remove_window())

# ---------------- EXIT ---------------- #

root.bind_all("<KeyPress-x>", lambda e: root.destroy())

# ---------------- GAME OVER ---------------- #

def trigger_game_over():
    global game_over
    game_over = True

    winsound.PlaySound(None, winsound.SND_PURGE)

    end = tk.Toplevel()
    end.attributes("-fullscreen", True)
    end.configure(bg="black")

    lbl = tk.Label(end, text="THE END!", fg="red", bg="black",
                   font=("Impact", 80))
    lbl.pack(expand=True)

    def close_all():
        root.destroy()

    end.after(5000, close_all)

# ---------------- HUNGER TICK ---------------- #

def hunger_tick():
    global hunger
    if game_over:
        return

    hunger -= 1
    if hunger < 0:
        hunger = 0

    update_hunger_bar()

    if hunger == 0:
        trigger_game_over()
        return

    root.after(8000, hunger_tick)

# ---------------- PERIODIC THOUGHTS ---------------- #

def periodic_thoughts():
    if game_over:
        return
    for i, lbl in enumerate(speech_labels):
        t = random_thought()
        speech_texts[i] = t
        lbl.config(text=t)
        spawn_bubble(windows[i], t)
    root.after(10000, periodic_thoughts)

# ---------------- INITIAL WINDOWS ---------------- #

for _ in range(NUM_WINDOWS):
    add_window()

# ---------------- PHYSICS ---------------- #

last_time = time.time()

def update():
    global last_time
    if game_over:
        return

    now = time.time()
    dt = now - last_time
    if dt > 0.05:
        dt = 0.05
    last_time = now

    for i, win in enumerate(windows):

        if dragging.get(win, False):
            continue

        vx, vy = vel[i]

        tvx, tvy = throw_vel.get(win, (0, 0))
        if abs(tvx) > 20 or abs(tvy) > 20:
            vx, vy = tvx, tvy
        throw_vel[win] = (0, 0)

        vy += GRAVITY * dt

        speed = math.sqrt(vx * vx + vy * vy)
        if speed > MAX_SPEED:
            scale = MAX_SPEED / speed
            vx *= scale
            vy *= scale

        x = win.winfo_x()
        y = win.winfo_y()

        x += vx * dt
        y += vy * dt

        if x < 0:
            x = 0
            vx = abs(vx) * BOUNCE
            play_bounce()

        if x + alex_w > screen_w:
            x = screen_w - alex_w
            vx = -abs(vx) * BOUNCE
            play_bounce()

        if y < 0:
            y = 0
            vy = abs(vy) * BOUNCE
            play_bounce()

        if y + alex_h > screen_h:
            y = screen_h - alex_h
            vy = -abs(vy) * BOUNCE
            play_bounce()

        vx *= FRICTION
        vy *= FRICTION

        win.geometry(f"+{int(x)}+{int(y)}")

        tag_win = nametag_windows[i]
        tag_x = int(x + (alex_w // 2) - (tag_w // 2))
        tag_y = int(y - tag_h - 5)
        tag_win.geometry(f"+{tag_x}+{tag_y}")

        vel[i] = [vx, vy]

    root.after(UPDATE_DELAY, update)

# ---------------- START ---------------- #

update_hunger_bar()
update_top_box()
root.bind_all("p", lambda e: open_teams())
hunger_tick()
periodic_thoughts()
update()
root.mainloop()
