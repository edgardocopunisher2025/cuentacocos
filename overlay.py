import sys, subprocess, importlib, signal

def ensure(p, n=None):
    try: importlib.import_module(n or p)
    except: subprocess.check_call([sys.executable,"-m","pip","install",p])

ensure("ultralytics"); ensure("opencv-python","cv2"); ensure("mss"); ensure("numpy")

import cv2, numpy as np, mss, tkinter as tk, threading, time
from ultralytics import YOLO

# ================= CONFIG =================
model = YOLO("yolov8m.pt")

monitor = {"top":50,"left":250,"width":900,"height":500}

ZONE_RED   = [200,300,400,450]
ZONE_GREEN = [450,300,650,450]

CELL_SIZE = 40        # tamaño de celda (ajusta si quieres más precisión)
COOLDOWN  = 15        # frames antes de volver a contar en misma celda

# ================= ESTADO =================
count_red = 0
count_green = 0

grid_red = {}
grid_green = {}

hit_red = 0
hit_green = 0

running = True
current_zone = "red"

# ================= UI =================
root = tk.Tk()
root.attributes("-topmost",True)
root.overrideredirect(True)
root.attributes("-alpha",0.9)

canvas = tk.Canvas(root,width=monitor["width"],height=monitor["height"],bg="black")
canvas.pack()
root.geometry(f"{monitor['width']}x{monitor['height']}+{monitor['left']}+{monitor['top']}")

def salir(event=None):
    global running
    running=False
    root.destroy()
    sys.exit()

root.bind("<Escape>", salir)
signal.signal(signal.SIGINT, lambda s,f: salir())

# ================= MOVER ZONAS =================
dragging=False

def norm(z):
    x1,y1,x2,y2=z
    return [min(x1,x2),min(y1,y2),max(x1,x2),max(y1,y2)]

def md(e):
    global dragging,sx,sy
    dragging=True; sx,sy=e.x,e.y

def mm(e):
    global ZONE_RED,ZONE_GREEN
    if not dragging: return
    if current_zone=="red":
        ZONE_RED=norm([sx,sy,e.x,e.y])
    else:
        ZONE_GREEN=norm([sx,sy,e.x,e.y])

def mu(e):
    global dragging
    dragging=False

def ks(e):
    global current_zone
    if e.char=="r": current_zone="red"
    if e.char=="g": current_zone="green"

canvas.bind("<ButtonPress-1>",md)
canvas.bind("<B1-Motion>",mm)
canvas.bind("<ButtonRelease-1>",mu)
root.bind("<Key>",ks)

# ================= IA =================
def ai():
    global count_red, count_green, hit_red, hit_green

    sct=mss.mss()

    while running:
        try:
            img=np.array(sct.grab(monitor))
            frame=cv2.cvtColor(img,cv2.COLOR_BGRA2BGR)

            results=model(frame,classes=[0],conf=0.3,imgsz=960)

            red_detected = False
            green_detected = False

            # reducir cooldown
            for k in list(grid_red.keys()):
                grid_red[k]-=1
                if grid_red[k]<=0: del grid_red[k]

            for k in list(grid_green.keys()):
                grid_green[k]-=1
                if grid_green[k]<=0: del grid_green[k]

            if results and results[0].boxes is not None:
                for box in results[0].boxes.xyxy:
                    x1,y1,x2,y2=map(int,box)
                    cx=(x1+x2)//2
                    cy=(y1+y2)//2

                    cell = (cx//CELL_SIZE, cy//CELL_SIZE)

                    # ===== ROJO =====
                    if (ZONE_RED[0]<=cx<=ZONE_RED[2] and ZONE_RED[1]<=cy<=ZONE_RED[3]):
                        red_detected = True
                        if cell not in grid_red:
                            count_red += 1
                            grid_red[cell] = COOLDOWN

                    # ===== VERDE =====
                    if (ZONE_GREEN[0]<=cx<=ZONE_GREEN[2] and ZONE_GREEN[1]<=cy<=ZONE_GREEN[3]):
                        green_detected = True
                        if cell not in grid_green:
                            count_green += 1
                            grid_green[cell] = COOLDOWN

            hit_red = 5 if red_detected else max(0,hit_red-1)
            hit_green = 5 if green_detected else max(0,hit_green-1)

        except Exception as e:
            print("Error:",e)

        time.sleep(0.01)

# ================= DRAW =================
def draw():
    if not running: return

    canvas.delete("all")

    canvas.create_rectangle(*ZONE_RED,outline="red",fill="red" if hit_red else "")
    canvas.create_rectangle(*ZONE_GREEN,outline="lime",fill="lime" if hit_green else "")

    canvas.create_text(120,60,text=f"RED: {count_red}",fill="red",font=("Arial",20,"bold"))
    canvas.create_text(120,100,text=f"GREEN: {count_green}",fill="lime",font=("Arial",20,"bold"))

    canvas.create_text(300,20,text=f"EDIT: {current_zone.upper()} (R/G) | ESC salir",fill="white")

    root.after(30,draw)

# ================= START =================
print("🔥 CONTEO POR ZONA (ANTI-SATURACIÓN REAL)")
print("R=ROJO | G=VERDE | ESC=SALIR")

threading.Thread(target=ai,daemon=True).start()
draw()
root.mainloop()
