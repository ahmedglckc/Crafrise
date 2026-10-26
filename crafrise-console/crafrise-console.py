# kol_klavye.py  —  Kolu klavye/fareye çevirir (Minecraft için)
# pip install pygame pynput
import pygame, sys, time
from pynput.keyboard import Controller as KC, Key
from pynput.mouse import Controller as MC, Button

pygame.init()
pygame.joystick.init()

kb = KC()
ms = MC()

if pygame.joystick.get_count() == 0:
    print("[!] Kol bulunamadi. Kolu tak ve tekrar dene.")
    input("ENTER...")
    sys.exit(1)

js = pygame.joystick.Joystick(0)
js.init()

print("=" * 64)
print(f"KOL: {js.get_name()}")
print(f"Eksen: {js.get_numaxes()} | Buton: {js.get_numbuttons()} | Hat: {js.get_numhats()}")
print("=" * 64)
print(" YUZ TUSLARI -> FARE IMLECI:")
print("   Kare  (2) = fare UST")
print("   Ucgen (3) = fare ALT")
print("   X     (0) = fare SOL")
print("   Daire (1) = fare SAG")
print(" L2   (6) -> SAG TIK (kullan/koy)")
print(" R2   (7) -> SOL TIK (kir/saddir)")
print(" L1   (5) -> SPACE (zipla)")
print(" R1   (4) -> LSHIFT (kos)")
print(" START(8) -> ESC (duraklat)")
print(" SELECT(9)-> E (envanter)")
print(" Sol cubuk / D-pad -> W A S D")
print(" Sag cubuk -> fare etrafa bakma")
print(" Cikis: bu konsolda Ctrl+C")
print("=" * 64)
time.sleep(1.5)

DEADZONE       = 0.35
MOUSE_SENS     = 15    # sag cubuk hassasiyeti
MOUSE_BTN_SPD  = 14    # yuz tuslariyla imlec hizi (piksel/kare)

active_keys = set()
active_mouse = set()
prev_buttons = {}
move_keys = set()

def K(key):
    if isinstance(key, str):
        return key.upper()
    m = {Key.space: "SPACE", Key.shift: "SHIFT", Key.shift_l: "LSHIFT",
         Key.shift_r: "RSHIFT", Key.esc: "ESC", Key.enter: "ENTER",
         Key.tab: "TAB", Key.backspace: "BACKSPACE"}
    return m.get(key, str(key).split('.')[-1].upper())

def press(key):
    if key in active_keys:
        return
    active_keys.add(key)
    try:
        kb.press(key)
        print(f"[+] {K(key)}")
    except Exception as e:
        print(f"[X] {e}")

def release(key):
    if key not in active_keys:
        return
    active_keys.discard(key)
    try:
        kb.release(key)
        print(f"[-] {K(key)}")
    except Exception as e:
        print(f"[X] {e}")

# Kol butonlari -> klavye tusu
BTN_KEYS = {
    5: Key.space,     # L1 = zipla
    4: Key.shift_l,   # R1 = kos
    9: 'e',           # SELECT = E (envanter)
    8: Key.esc,       # START  = ESC
}

# Kol butonlari -> fare tik
BTN_MOUSE = {
    6: Button.right,  # L2 = sag tik
    7: Button.left,   # R2 = sol tik
}

# YUZ TUSLARI -> fare imlec yonu (dx, dy)
# dx: -1 SOL, +1 SAG | dy: -1 UST, +1 ALT
BTN_MOUSE_DIR = {
    2: ( 0,  1),   # Kare  (Square)   -> fare UST 3
    3: (-1,  0),   # Ucgen (Triangle) -> fare ALT 4
    0: ( 0, -1),   # X     (Cross)    -> fare SOL 1
    1: ( 1,  0),   # Daire (Circle)   -> fare SAG 2
}

print("[OK] Dinleniyor... Minecraft'a gec, kol calisir.\n")

try:
    while True:
        pygame.event.pump()

        # ---------- Butonlar ----------
        for b in range(js.get_numbuttons()):
            now = bool(js.get_button(b))
            was = prev_buttons.get(b, False)

            if now and not was:            # basildi
                if b in BTN_KEYS:
                    press(BTN_KEYS[b])
                elif b in BTN_MOUSE:
                    btn = BTN_MOUSE[b]
                    try:
                        ms.press(btn)
                        active_mouse.add(btn)
                        print(f"[+] MOUSE_{btn.name.upper()}")
                    except Exception as e:
                        print(f"[X] {e}")
                elif b in BTN_MOUSE_DIR:
                    dx, dy = BTN_MOUSE_DIR[b]
                    yon = "SOL" if dx < 0 else "SAG" if dx > 0 else \
                           "UST" if dy < 0 else "ALT"
                    print(f"[+] FARE_{yon}")

            elif not now and was:          # birakildi
                if b in BTN_KEYS:
                    release(BTN_KEYS[b])
                elif b in BTN_MOUSE:
                    btn = BTN_MOUSE[b]
                    try:
                        ms.release(btn)
                        active_mouse.discard(btn)
                        print(f"[-] MOUSE_{btn.name.upper()}")
                    except Exception:
                        pass
                elif b in BTN_MOUSE_DIR:
                    dx, dy = BTN_MOUSE_DIR[b]
                    yon = "SOL" if dx < 0 else "SAG" if dx > 0 else \
                           "UST" if dy < 0 else "ALT"
                    print(f"[-] FARE_{yon}")

            prev_buttons[b] = now

        # ---------- Sol cubuk + D-pad -> WASD ----------
        new_move = set()
        if js.get_numaxes() >= 2:
            ax = js.get_axis(0)
            ay = js.get_axis(1)
            if ax < -DEADZONE: new_move.add('a')
            if ax >  DEADZONE: new_move.add('d')
            if ay < -DEADZONE: new_move.add('w')
            if ay >  DEADZONE: new_move.add('s')

        if js.get_numhats() > 0:
            hx, hy = js.get_hat(0)
            if hx < 0: new_move.add('a')
            if hx > 0: new_move.add('d')
            if hy > 0: new_move.add('w')
            if hy < 0: new_move.add('s')

        for k in move_keys - new_move:
            release(k)
        for k in new_move - move_keys:
            press(k)
        move_keys = new_move

        # ---------- Yuz tuslari -> fare imlec hareketi ----------
        ddx = ddy = 0
        for b, (dx, dy) in BTN_MOUSE_DIR.items():
            if prev_buttons.get(b, False):
                ddx += dx * MOUSE_BTN_SPD
                ddy += dy * MOUSE_BTN_SPD

        # ---------- Sag cubuk -> fare etrafa bakma ----------
        if js.get_numaxes() >= 4:
            rx = js.get_axis(2)
            ry = js.get_axis(3)
            if abs(rx) > DEADZONE:
                ddx += int((rx - (DEADZONE if rx > 0 else -DEADZONE)) * MOUSE_SENS)
            if abs(ry) > DEADZONE:
                ddy += int((ry - (DEADZONE if ry > 0 else -DEADZONE)) * MOUSE_SENS)

        if ddx or ddy:
            ms.move(ddx, ddy)

        time.sleep(0.005)

except KeyboardInterrupt:
    print("\n[!] Durduruldu.")
finally:
    for k in list(active_keys):
        try: kb.release(k)
        except: pass
    for b in list(active_mouse):
        try: ms.release(b)
        except: pass
    pygame.quit()
    print("[OK] Cikis.")
